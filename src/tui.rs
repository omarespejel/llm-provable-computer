use std::path::Path;
use std::time::{Duration, Instant};

use crossterm::event::{self, Event, KeyCode};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, Borders, Cell, List, ListItem, Paragraph, Row, Table, Wrap};
use ratatui::{Frame, Terminal};

use crate::{DispatchInfo, ExecutionRuntime, Result};

pub fn run_execution_tui(
    program_path: &Path,
    runtime: &mut ExecutionRuntime,
    tick_rate: Duration,
) -> Result<()> {
    enable_raw_mode()?;
    execute!(std::io::stdout(), EnterAlternateScreen)?;

    let backend = CrosstermBackend::new(std::io::stdout());
    let mut terminal = match Terminal::new(backend) {
        Ok(terminal) => terminal,
        Err(error) => {
            disable_raw_mode()?;
            execute!(std::io::stdout(), LeaveAlternateScreen)?;
            return Err(error.into());
        }
    };

    let result = run_loop(&mut terminal, program_path, runtime, tick_rate);

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    result
}

fn run_loop(
    terminal: &mut Terminal<CrosstermBackend<std::io::Stdout>>,
    program_path: &Path,
    runtime: &mut ExecutionRuntime,
    tick_rate: Duration,
) -> Result<()> {
    let started = Instant::now();
    let mut paused = false;

    loop {
        let next_dispatch = runtime.next_dispatch()?;
        terminal.draw(|frame| {
            draw_ui(
                frame,
                program_path,
                runtime,
                next_dispatch.as_ref(),
                paused,
                started.elapsed(),
            )
        })?;

        let finished = runtime.state().halted || runtime.step_count() >= runtime.max_steps();

        if event::poll(if paused || finished {
            Duration::from_millis(100)
        } else {
            tick_rate
        })? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Char('q') => return Ok(()),
                    KeyCode::Char(' ') => paused = !paused,
                    KeyCode::Char('n') if paused && !finished => {
                        runtime.step()?;
                    }
                    _ => {}
                }
            }
        } else if !paused && !finished {
            runtime.step()?;
        }
    }
}

fn draw_ui(
    frame: &mut Frame,
    program_path: &Path,
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    paused: bool,
    elapsed: Duration,
) {
    let root = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(7),
            Constraint::Min(10),
            Constraint::Length(3),
        ])
        .split(frame.area());
    let top = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(58), Constraint::Percentage(42)])
        .split(root[0]);
    let middle = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(45), Constraint::Percentage(55)])
        .split(root[1]);

    frame.render_widget(
        summary_panel(program_path, runtime, next_dispatch, paused, elapsed),
        top[0],
    );
    frame.render_widget(register_panel(runtime), top[1]);
    frame.render_widget(memory_panel(runtime), middle[0]);
    frame.render_widget(trace_panel(runtime), middle[1]);
    frame.render_widget(help_panel(runtime, paused), root[2]);
}

fn summary_panel(
    program_path: &Path,
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    paused: bool,
    elapsed: Duration,
) -> Paragraph<'static> {
    let status = if runtime.state().halted {
        "halted"
    } else if runtime.step_count() >= runtime.max_steps() {
        "max-steps"
    } else if paused {
        "paused"
    } else {
        "running"
    };
    let throughput = if elapsed.as_secs_f64() > 0.0 {
        runtime.step_count() as f64 / elapsed.as_secs_f64()
    } else {
        0.0
    };
    let next = next_dispatch
        .map(|dispatch| format!("L{} {}", dispatch.layer_idx, dispatch.instruction))
        .unwrap_or_else(|| "complete".to_string());

    Paragraph::new(vec![
        Line::from(format!("program: {}", program_path.display())),
        Line::from(format!("status: {status}")),
        Line::from(format!(
            "step: {}/{}",
            runtime.step_count(),
            runtime.max_steps()
        )),
        Line::from(format!("next: {next}")),
        Line::from(format!("throughput: {:.2} steps/s", throughput)),
    ])
    .block(Block::default().title("Execution").borders(Borders::ALL))
    .wrap(Wrap { trim: true })
}

fn register_panel(runtime: &ExecutionRuntime) -> Paragraph<'static> {
    let state = runtime.state();
    Paragraph::new(vec![
        Line::from(format!("pc: {}", state.pc)),
        Line::from(format!("acc: {}", state.acc)),
        Line::from(format!("sp: {}", state.sp)),
        Line::from(format!("zero: {}", state.zero_flag)),
        Line::from(format!("carry: {}", state.carry_flag)),
        Line::from(format!("halted: {}", state.halted)),
        Line::from(format!("memory cells: {}", state.memory.len())),
    ])
    .block(Block::default().title("Registers").borders(Borders::ALL))
}

fn memory_panel(runtime: &ExecutionRuntime) -> Table<'static> {
    let changed = runtime
        .events()
        .last()
        .map(|event| {
            event
                .state_before
                .memory
                .iter()
                .zip(event.state_after.memory.iter())
                .enumerate()
                .filter_map(|(idx, (before, after))| (before != after).then_some(idx))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let rows = runtime
        .state()
        .memory
        .iter()
        .enumerate()
        .map(|(idx, value)| {
            let marker = if changed.contains(&idx) {
                "last-write"
            } else {
                ""
            };
            let style = if changed.contains(&idx) {
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default()
            };
            Row::new(vec![
                Cell::from(idx.to_string()),
                Cell::from(value.to_string()),
                Cell::from(marker.to_string()),
            ])
            .style(style)
        })
        .collect::<Vec<_>>();

    Table::new(
        rows,
        [
            Constraint::Length(6),
            Constraint::Length(10),
            Constraint::Min(8),
        ],
    )
    .header(
        Row::new(vec!["addr", "value", "note"])
            .style(Style::default().add_modifier(Modifier::BOLD)),
    )
    .block(Block::default().title("Memory").borders(Borders::ALL))
}

fn trace_panel(runtime: &ExecutionRuntime) -> List<'static> {
    let items = runtime
        .events()
        .iter()
        .rev()
        .take(12)
        .map(|event| {
            ListItem::new(Line::from(format!(
                "#{:03} L{} {}  pc {}->{}  acc {}->{}",
                event.step,
                event.layer_idx,
                event.instruction,
                event.state_before.pc,
                event.state_after.pc,
                event.state_before.acc,
                event.state_after.acc
            )))
        })
        .collect::<Vec<_>>();

    List::new(items).block(Block::default().title("Trace").borders(Borders::ALL))
}

fn help_panel(runtime: &ExecutionRuntime, paused: bool) -> Paragraph<'static> {
    let status = if runtime.state().halted {
        "halted"
    } else if runtime.step_count() >= runtime.max_steps() {
        "max-steps"
    } else if paused {
        "paused"
    } else {
        "running"
    };

    Paragraph::new(vec![
        Line::from("q quit   space pause/resume   n single-step (while paused)"),
        Line::from(format!("viewer status: {status}")),
    ])
    .block(Block::default().title("Controls").borders(Borders::ALL))
}
