use std::path::Path;
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::thread;
use std::time::{Duration, Instant};

use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Alignment, Constraint, Direction, Flex, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::symbols::{self, Marker};
use ratatui::text::{Line, Span};
use ratatui::widgets::{
    Axis, Bar, BarChart, BarGroup, Block, Borders, Cell, Chart, Clear, Dataset, GraphType, List,
    ListItem, Padding, Paragraph, Row, Table, Tabs, Wrap,
};
use ratatui::{Frame, Terminal};
use sha3::{Digest, Sha3_256};

use crate::proof::{validate_execution_stark_support, VanillaStarkExecutionProof};
use crate::{
    prove_execution_stark, verify_execution_stark, Attention2DMode, DispatchInfo, ExecutionRuntime,
    Instruction, Result,
};

const HISTORY_LIMIT: usize = 96;
const TRACE_LIMIT: usize = 18;

#[derive(Debug, Clone, Copy)]
struct Theme {
    name: &'static str,
    bg: Color,
    panel: Color,
    panel_alt: Color,
    border: Color,
    text: Color,
    muted: Color,
    accent: Color,
    accent_soft: Color,
    accent_alt: Color,
    success: Color,
    danger: Color,
}

const THEMES: [Theme; 3] = [
    Theme {
        name: "Velvet",
        bg: Color::Rgb(22, 18, 24),
        panel: Color::Rgb(40, 30, 41),
        panel_alt: Color::Rgb(56, 39, 49),
        border: Color::Rgb(121, 79, 91),
        text: Color::Rgb(248, 236, 228),
        muted: Color::Rgb(183, 154, 157),
        accent: Color::Rgb(255, 120, 96),
        accent_soft: Color::Rgb(255, 188, 112),
        accent_alt: Color::Rgb(113, 212, 185),
        success: Color::Rgb(138, 218, 161),
        danger: Color::Rgb(255, 104, 136),
    },
    Theme {
        name: "Cider",
        bg: Color::Rgb(30, 24, 18),
        panel: Color::Rgb(52, 41, 28),
        panel_alt: Color::Rgb(70, 54, 34),
        border: Color::Rgb(140, 103, 54),
        text: Color::Rgb(247, 238, 212),
        muted: Color::Rgb(194, 172, 133),
        accent: Color::Rgb(244, 141, 61),
        accent_soft: Color::Rgb(245, 203, 92),
        accent_alt: Color::Rgb(135, 205, 123),
        success: Color::Rgb(158, 216, 132),
        danger: Color::Rgb(235, 91, 82),
    },
    Theme {
        name: "Lagoon",
        bg: Color::Rgb(15, 28, 33),
        panel: Color::Rgb(23, 47, 53),
        panel_alt: Color::Rgb(35, 63, 70),
        border: Color::Rgb(79, 129, 136),
        text: Color::Rgb(226, 242, 239),
        muted: Color::Rgb(148, 183, 179),
        accent: Color::Rgb(76, 201, 190),
        accent_soft: Color::Rgb(255, 191, 122),
        accent_alt: Color::Rgb(245, 124, 103),
        success: Color::Rgb(147, 222, 166),
        danger: Color::Rgb(255, 116, 127),
    },
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ViewMode {
    Runway,
    Memory,
    Backtrace,
    Attestation,
}

impl ViewMode {
    fn all() -> [Self; 4] {
        [
            Self::Runway,
            Self::Memory,
            Self::Backtrace,
            Self::Attestation,
        ]
    }

    fn next(self) -> Self {
        match self {
            Self::Runway => Self::Memory,
            Self::Memory => Self::Backtrace,
            Self::Backtrace => Self::Attestation,
            Self::Attestation => Self::Runway,
        }
    }

    fn previous(self) -> Self {
        match self {
            Self::Runway => Self::Attestation,
            Self::Memory => Self::Runway,
            Self::Backtrace => Self::Memory,
            Self::Attestation => Self::Backtrace,
        }
    }

    fn title(self) -> &'static str {
        match self {
            Self::Runway => "Runway",
            Self::Memory => "Atelier",
            Self::Backtrace => "Backtrace",
            Self::Attestation => "Attestation",
        }
    }
}

enum ProofWorkerMessage {
    Proved(std::result::Result<VanillaStarkExecutionProof, String>),
    Verified {
        proof: VanillaStarkExecutionProof,
        result: std::result::Result<bool, String>,
    },
}

enum ProofPhase {
    Idle,
    Proving {
        started_at: Instant,
        proof_budget_steps: usize,
        auto_verify: bool,
    },
    Ready {
        proof: VanillaStarkExecutionProof,
        minted_at: Instant,
    },
    Verifying {
        proof: VanillaStarkExecutionProof,
        started_at: Instant,
    },
    Verified {
        proof: VanillaStarkExecutionProof,
        verified_at: Instant,
    },
    Failed {
        stage: &'static str,
        message: String,
        proof: Option<VanillaStarkExecutionProof>,
    },
}

struct ProofShowcase {
    phase: ProofPhase,
    receiver: Option<Receiver<ProofWorkerMessage>>,
}

impl ProofShowcase {
    fn new() -> Self {
        Self {
            phase: ProofPhase::Idle,
            receiver: None,
        }
    }

    fn is_busy(&self) -> bool {
        matches!(
            self.phase,
            ProofPhase::Proving { .. } | ProofPhase::Verifying { .. }
        )
    }

    fn current_proof(&self) -> Option<&VanillaStarkExecutionProof> {
        match &self.phase {
            ProofPhase::Ready { proof, .. }
            | ProofPhase::Verifying { proof, .. }
            | ProofPhase::Verified { proof, .. } => Some(proof),
            ProofPhase::Failed {
                proof: Some(proof), ..
            } => Some(proof),
            ProofPhase::Idle
            | ProofPhase::Proving { .. }
            | ProofPhase::Failed { proof: None, .. } => None,
        }
    }

    fn poll(&mut self) {
        let Some(receiver) = &self.receiver else {
            return;
        };

        match receiver.try_recv() {
            Ok(message) => {
                let auto_verify = matches!(
                    self.phase,
                    ProofPhase::Proving {
                        auto_verify: true,
                        ..
                    }
                );
                self.receiver = None;
                match message {
                    ProofWorkerMessage::Proved(result) => match result {
                        Ok(proof) => {
                            if auto_verify {
                                self.start_verifying_with_proof(proof);
                            } else {
                                self.phase = ProofPhase::Ready {
                                    proof,
                                    minted_at: Instant::now(),
                                };
                            }
                        }
                        Err(message) => {
                            self.phase = ProofPhase::Failed {
                                stage: "prove",
                                message,
                                proof: None,
                            };
                        }
                    },
                    ProofWorkerMessage::Verified { proof, result } => match result {
                        Ok(true) => {
                            self.phase = ProofPhase::Verified {
                                proof,
                                verified_at: Instant::now(),
                            };
                        }
                        Ok(false) => {
                            self.phase = ProofPhase::Failed {
                                stage: "verify",
                                message: "the verifier rejected the generated proof".to_string(),
                                proof: Some(proof),
                            };
                        }
                        Err(message) => {
                            self.phase = ProofPhase::Failed {
                                stage: "verify",
                                message,
                                proof: Some(proof),
                            };
                        }
                    },
                }
            }
            Err(TryRecvError::Empty) => {}
            Err(TryRecvError::Disconnected) => {
                self.receiver = None;
                let proof = match std::mem::replace(&mut self.phase, ProofPhase::Idle) {
                    ProofPhase::Verifying { proof, .. } => Some(proof),
                    ProofPhase::Ready { proof, minted_at } => {
                        self.phase = ProofPhase::Ready { proof, minted_at };
                        return;
                    }
                    ProofPhase::Verified { proof, verified_at } => {
                        self.phase = ProofPhase::Verified { proof, verified_at };
                        return;
                    }
                    ProofPhase::Failed {
                        stage,
                        message,
                        proof,
                    } => {
                        self.phase = ProofPhase::Failed {
                            stage,
                            message,
                            proof,
                        };
                        return;
                    }
                    ProofPhase::Idle | ProofPhase::Proving { .. } => None,
                };
                self.phase = ProofPhase::Failed {
                    stage: "worker",
                    message: "the proof worker disconnected before returning a result".to_string(),
                    proof,
                };
            }
        }
    }

    fn start_proving(
        &mut self,
        runtime: &ExecutionRuntime,
        proof_budget_steps: usize,
        auto_verify: bool,
    ) {
        let model = runtime.model().clone();
        let (sender, receiver) = mpsc::channel();
        self.receiver = Some(receiver);
        self.phase = ProofPhase::Proving {
            started_at: Instant::now(),
            proof_budget_steps,
            auto_verify,
        };

        thread::spawn(move || {
            let result = prove_execution_stark(&model, proof_budget_steps)
                .map_err(|error| error.to_string());
            let _ = sender.send(ProofWorkerMessage::Proved(result));
        });
    }

    fn start_verifying(&mut self) {
        let Some(proof) = self.current_proof().cloned() else {
            return;
        };
        self.start_verifying_with_proof(proof);
    }

    fn start_verifying_with_proof(&mut self, proof: VanillaStarkExecutionProof) {
        let (sender, receiver) = mpsc::channel();
        self.receiver = Some(receiver);
        self.phase = ProofPhase::Verifying {
            proof: proof.clone(),
            started_at: Instant::now(),
        };

        thread::spawn(move || {
            let result = verify_execution_stark(&proof).map_err(|error| error.to_string());
            let _ = sender.send(ProofWorkerMessage::Verified { proof, result });
        });
    }
}

struct ViewerState {
    paused: bool,
    mode: ViewMode,
    theme_idx: usize,
    tick_ms: u64,
    acc_history: Vec<i64>,
    pc_history: Vec<u64>,
    throughput_history: Vec<u64>,
    last_seen_step: usize,
    last_rate_at: Instant,
    last_rate_step: usize,
    proof_budget_steps: usize,
    proof: ProofShowcase,
}

impl ViewerState {
    fn new(tick_rate: Duration, runtime: &ExecutionRuntime) -> Self {
        Self {
            paused: false,
            mode: ViewMode::Runway,
            theme_idx: 0,
            tick_ms: tick_rate.as_millis().max(1) as u64,
            acc_history: vec![runtime.state().acc as i64],
            pc_history: vec![runtime.state().pc as u64],
            throughput_history: vec![0],
            last_seen_step: runtime.step_count(),
            last_rate_at: Instant::now(),
            last_rate_step: runtime.step_count(),
            proof_budget_steps: initial_proof_budget(runtime),
            proof: ProofShowcase::new(),
        }
    }

    fn theme(&self) -> Theme {
        THEMES[self.theme_idx % THEMES.len()]
    }

    fn tick_rate(&self) -> Duration {
        Duration::from_millis(self.tick_ms)
    }

    fn cycle_theme(&mut self) {
        self.theme_idx = (self.theme_idx + 1) % THEMES.len();
    }

    fn set_mode(&mut self, mode: ViewMode) {
        self.mode = mode;
    }

    fn next_mode(&mut self) {
        self.mode = self.mode.next();
    }

    fn previous_mode(&mut self) {
        self.mode = self.mode.previous();
    }

    fn speed_up(&mut self) {
        self.tick_ms = self.tick_ms.saturating_sub(10).max(10);
    }

    fn slow_down(&mut self) {
        self.tick_ms = self.tick_ms.saturating_add(10).min(500);
    }

    fn increase_proof_budget(&mut self) {
        self.proof_budget_steps = self.proof_budget_steps.saturating_mul(2).min(1_048_576);
    }

    fn decrease_proof_budget(&mut self) {
        self.proof_budget_steps = (self.proof_budget_steps / 2).max(32);
    }

    fn refresh(&mut self, runtime: &ExecutionRuntime, now: Instant) {
        if runtime.step_count() != self.last_seen_step {
            push_limited(&mut self.acc_history, runtime.state().acc as i64);
            push_limited(&mut self.pc_history, runtime.state().pc as u64);
            self.last_seen_step = runtime.step_count();
        }

        let elapsed = now.saturating_duration_since(self.last_rate_at);
        if elapsed >= Duration::from_millis(120) {
            let step_delta = runtime.step_count().saturating_sub(self.last_rate_step);
            let per_second = if elapsed.as_secs_f64() > 0.0 {
                (step_delta as f64 / elapsed.as_secs_f64()).round() as u64
            } else {
                0
            };
            push_limited(&mut self.throughput_history, per_second);
            self.last_rate_at = now;
            self.last_rate_step = runtime.step_count();
        }

        self.proof.poll();
    }

    fn try_start_proving(&mut self, runtime: &ExecutionRuntime) {
        self.mode = ViewMode::Attestation;
        if self.proof.is_busy() || !proof_can_start(runtime) {
            return;
        }
        self.proof
            .start_proving(runtime, self.proof_budget_steps, true);
    }

    fn try_start_verifying(&mut self) {
        self.mode = ViewMode::Attestation;
        if self.proof.is_busy() || self.proof.current_proof().is_none() {
            return;
        }
        self.proof.start_verifying();
    }
}

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
    let mut viewer = ViewerState::new(tick_rate, runtime);

    loop {
        let now = Instant::now();
        viewer.refresh(runtime, now);
        let next_dispatch = runtime.next_dispatch()?;
        terminal.draw(|frame| {
            draw_ui(
                frame,
                program_path,
                runtime,
                next_dispatch.as_ref(),
                &viewer,
                started.elapsed(),
            )
        })?;

        let finished = runtime.state().halted || runtime.step_count() >= runtime.max_steps();
        let wait = if viewer.paused || finished {
            Duration::from_millis(100)
        } else {
            viewer.tick_rate()
        };

        if event::poll(wait)? {
            if let Event::Key(key) = event::read()? {
                if matches!(key.kind, KeyEventKind::Press | KeyEventKind::Repeat) {
                    match key.code {
                        KeyCode::Char('q') => return Ok(()),
                        KeyCode::Char(' ') => viewer.paused = !viewer.paused,
                        KeyCode::Char('n') if viewer.paused && !finished => {
                            runtime.step()?;
                            viewer.refresh(runtime, Instant::now());
                        }
                        KeyCode::Char('t') => viewer.cycle_theme(),
                        KeyCode::Char('+') | KeyCode::Char('=') => viewer.speed_up(),
                        KeyCode::Char('-') | KeyCode::Char('_') => viewer.slow_down(),
                        KeyCode::Char('1') => viewer.set_mode(ViewMode::Runway),
                        KeyCode::Char('2') => viewer.set_mode(ViewMode::Memory),
                        KeyCode::Char('3') => viewer.set_mode(ViewMode::Backtrace),
                        KeyCode::Char('4') => viewer.set_mode(ViewMode::Attestation),
                        KeyCode::Enter | KeyCode::Char('a') | KeyCode::Char('p') => {
                            viewer.try_start_proving(runtime)
                        }
                        KeyCode::Char('[') | KeyCode::Char('{') => viewer.decrease_proof_budget(),
                        KeyCode::Char(']') | KeyCode::Char('}') => viewer.increase_proof_budget(),
                        KeyCode::Char('v') => viewer.try_start_verifying(),
                        KeyCode::Tab | KeyCode::Right | KeyCode::Char('l') => viewer.next_mode(),
                        KeyCode::BackTab | KeyCode::Left | KeyCode::Char('h') => {
                            viewer.previous_mode()
                        }
                        _ => {}
                    }
                }
            }
        } else if !viewer.paused && !finished {
            runtime.step()?;
        }
    }
}

fn draw_ui(
    frame: &mut Frame,
    program_path: &Path,
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    viewer: &ViewerState,
    elapsed: Duration,
) {
    let theme = viewer.theme();
    frame.render_widget(
        Block::default().style(Style::default().bg(theme.bg)),
        frame.area(),
    );

    let root = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(8),
            Constraint::Length(3),
            Constraint::Min(10),
            Constraint::Length(2),
        ])
        .split(frame.area());

    let hero = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
        .split(root[0]);

    frame.render_widget(
        hero_panel(program_path, runtime, next_dispatch, viewer, theme),
        hero[0],
    );
    frame.render_widget(
        status_panel(runtime, next_dispatch, viewer, elapsed, theme),
        hero[1],
    );
    frame.render_widget(tab_panel(viewer, theme), root[1]);

    match viewer.mode {
        ViewMode::Runway => render_runway(frame, root[2], runtime, next_dispatch, viewer, theme),
        ViewMode::Memory => render_memory(frame, root[2], runtime, next_dispatch, viewer, theme),
        ViewMode::Backtrace => {
            render_backtrace(frame, root[2], runtime, next_dispatch, viewer, theme)
        }
        ViewMode::Attestation => render_attestation(frame, root[2], runtime, viewer, theme),
    }

    frame.render_widget(footer_panel(runtime, viewer, theme), root[3]);

    if viewer.paused && !run_finished(runtime) {
        render_overlay(frame, runtime, viewer, theme);
    }
}

fn hero_panel(
    program_path: &Path,
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    viewer: &ViewerState,
    theme: Theme,
) -> Paragraph<'static> {
    let pulse = match runtime.step_count() % 4 {
        0 => "◢",
        1 => "◣",
        2 => "◤",
        _ => "◥",
    };
    let next_copy = next_dispatch
        .map(|dispatch| format!("L{} {}", dispatch.layer_idx, dispatch.instruction))
        .unwrap_or_else(|| "final pose".to_string());
    let mood = next_dispatch
        .map(|dispatch| instruction_mood(dispatch.instruction))
        .unwrap_or("all weights settled");
    let program_name = program_path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("program");

    Paragraph::new(vec![
        Line::from(vec![
            Span::styled(
                format!(" {} ", pulse),
                Style::default()
                    .bg(theme.accent)
                    .fg(theme.bg)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                " TRANSFORMER ",
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                "VM",
                Style::default()
                    .fg(theme.accent_soft)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled(
                "compiled-weight runway",
                Style::default()
                    .fg(theme.accent_alt)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("  •  ", Style::default().fg(theme.muted)),
            Span::styled(program_name.to_string(), Style::default().fg(theme.text)),
        ]),
        Line::from(vec![
            Span::styled(
                format!("{} ", viewer.mode.title().to_uppercase()),
                Style::default()
                    .fg(theme.bg)
                    .bg(theme.accent_soft)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(" next ", Style::default().fg(theme.muted)),
            Span::styled(next_copy, Style::default().fg(theme.text)),
        ]),
        Line::from(vec![
            Span::styled("mood ", Style::default().fg(theme.muted)),
            Span::styled(mood, Style::default().fg(theme.accent)),
            Span::styled("  •  ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{} layers active", runtime.model().config().num_layers),
                Style::default().fg(theme.text),
            ),
        ]),
        Line::from(vec![
            Span::styled("current state ", Style::default().fg(theme.muted)),
            Span::styled(
                format!(
                    "pc {}  acc {}  zero {}  carry {}",
                    runtime.state().pc,
                    runtime.state().acc,
                    runtime.state().zero_flag,
                    runtime.state().carry_flag
                ),
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ),
        ]),
    ])
    .block(panel_block("Couture Trace", theme))
    .wrap(Wrap { trim: true })
}

fn status_panel(
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    viewer: &ViewerState,
    elapsed: Duration,
    theme: Theme,
) -> Paragraph<'static> {
    let status = viewer_status(runtime, viewer);
    let progress = if runtime.max_steps() == 0 {
        0.0
    } else {
        runtime.step_count() as f64 / runtime.max_steps() as f64
    }
    .clamp(0.0, 1.0);
    let throughput = if elapsed.as_secs_f64() > 0.0 {
        runtime.step_count() as f64 / elapsed.as_secs_f64()
    } else {
        0.0
    };
    let dispatch = next_dispatch
        .map(|item| format!("L{} {}", item.layer_idx, item.instruction))
        .unwrap_or_else(|| "complete".to_string());
    let (proof_label, proof_color, proof_detail) = proof_status_summary(runtime, viewer, theme);

    Paragraph::new(vec![
        badge_line(
            &[
                (
                    format!(" {} ", status),
                    theme.bg,
                    status_color(runtime, viewer, theme),
                ),
                (
                    format!(" {} ", viewer.theme().name),
                    theme.bg,
                    theme.accent_soft,
                ),
                (
                    format!(" {}ms ", viewer.tick_ms),
                    theme.bg,
                    theme.accent_alt,
                ),
            ],
            theme,
        ),
        Line::from(vec![
            Span::styled("dispatch ", Style::default().fg(theme.muted)),
            Span::styled(dispatch, Style::default().fg(theme.text)),
        ]),
        Line::from(vec![
            Span::styled("progress ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{:>3.0}%", progress * 100.0),
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ),
            Span::styled("  •  ", Style::default().fg(theme.muted)),
            Span::styled("throughput ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{throughput:.0} steps/s"),
                Style::default().fg(theme.accent),
            ),
        ]),
        Line::from(vec![
            Span::styled("memory ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{} cells", runtime.state().memory.len()),
                Style::default().fg(theme.text),
            ),
            Span::styled("  •  ", Style::default().fg(theme.muted)),
            Span::styled("trace ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{} events", runtime.events().len()),
                Style::default().fg(theme.text),
            ),
        ]),
        Line::from(vec![
            Span::styled("proof ", Style::default().fg(theme.muted)),
            Span::styled(
                proof_label,
                Style::default()
                    .fg(proof_color)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("  •  ", Style::default().fg(theme.muted)),
            Span::styled(proof_detail, Style::default().fg(theme.text)),
        ]),
    ])
    .block(panel_block("Stage Monitor", theme))
    .alignment(Alignment::Left)
}

fn tab_panel(viewer: &ViewerState, theme: Theme) -> Tabs<'static> {
    let titles = ViewMode::all()
        .into_iter()
        .enumerate()
        .map(|(idx, mode)| {
            Line::from(format!("  {}:{}  ", idx + 1, mode.title()))
                .style(Style::default().fg(theme.text).bg(theme.panel_alt))
        })
        .collect::<Vec<_>>();

    Tabs::new(titles)
        .select(match viewer.mode {
            ViewMode::Runway => 0,
            ViewMode::Memory => 1,
            ViewMode::Backtrace => 2,
            ViewMode::Attestation => 3,
        })
        .block(panel_block("Modes", theme))
        .divider(" ")
        .highlight_style(
            Style::default()
                .fg(theme.bg)
                .bg(theme.accent)
                .add_modifier(Modifier::BOLD),
        )
}

fn render_runway(
    frame: &mut Frame,
    area: Rect,
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    viewer: &ViewerState,
    theme: Theme,
) {
    let vertical = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(8), Constraint::Min(0)])
        .split(area);
    let top = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(32),
            Constraint::Percentage(34),
            Constraint::Percentage(34),
        ])
        .split(vertical[0]);
    let bottom = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
        .split(vertical[1]);
    let bottom_left = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(70), Constraint::Percentage(30)])
        .split(bottom[0]);
    let bottom_right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(36), Constraint::Percentage(64)])
        .split(bottom[1]);

    frame.render_widget(
        dispatch_panel(runtime, next_dispatch, viewer, theme),
        top[0],
    );
    frame.render_widget(progress_panel(runtime, viewer, theme), top[1]);
    frame.render_widget(register_panel(runtime, theme), top[2]);
    render_history_chart(frame, bottom_left[0], runtime, viewer, theme);
    frame.render_widget(throughput_panel(viewer, theme), bottom_left[1]);
    frame.render_widget(layer_panel(runtime, theme), bottom_right[0]);
    frame.render_widget(trace_list(runtime, theme, TRACE_LIMIT), bottom_right[1]);
}

fn render_memory(
    frame: &mut Frame,
    area: Rect,
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    viewer: &ViewerState,
    theme: Theme,
) {
    let columns = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(58), Constraint::Percentage(42)])
        .split(area);
    let left = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(10), Constraint::Length(10)])
        .split(columns[0]);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(8),
            Constraint::Length(8),
            Constraint::Min(0),
        ])
        .split(columns[1]);

    frame.render_widget(memory_table(runtime, theme), left[0]);
    frame.render_widget(memory_hotspots(runtime, theme), left[1]);
    frame.render_widget(
        dispatch_panel(runtime, next_dispatch, viewer, theme),
        right[0],
    );
    frame.render_widget(memory_story(runtime, theme), right[1]);
    frame.render_widget(trace_list(runtime, theme, TRACE_LIMIT), right[2]);
}

fn render_backtrace(
    frame: &mut Frame,
    area: Rect,
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    viewer: &ViewerState,
    theme: Theme,
) {
    let columns = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(54), Constraint::Percentage(46)])
        .split(area);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(8),
            Constraint::Length(8),
            Constraint::Min(0),
        ])
        .split(columns[1]);

    frame.render_widget(trace_list(runtime, theme, TRACE_LIMIT + 6), columns[0]);
    frame.render_widget(
        dispatch_panel(runtime, next_dispatch, viewer, theme),
        right[0],
    );
    frame.render_widget(recent_event_panel(runtime, theme), right[1]);
    render_history_chart(frame, right[2], runtime, viewer, theme);
}

fn render_attestation(
    frame: &mut Frame,
    area: Rect,
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) {
    if area.width < 100 || area.height < 16 {
        let columns = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(54), Constraint::Percentage(46)])
            .split(area);
        frame.render_widget(attestation_deck_panel(runtime, viewer, theme), columns[0]);
        frame.render_widget(
            attestation_compact_panel(runtime, viewer, theme),
            columns[1],
        );
        return;
    }

    let columns = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(56), Constraint::Percentage(44)])
        .split(area);
    let left = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(8), Constraint::Min(0)])
        .split(columns[0]);
    let right = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(8), Constraint::Min(0)])
        .split(columns[1]);

    frame.render_widget(attestation_deck_panel(runtime, viewer, theme), left[0]);
    frame.render_widget(proof_eligibility_panel(runtime, viewer, theme), left[1]);
    frame.render_widget(proof_artifact_panel(viewer, theme), right[0]);
    frame.render_widget(public_claim_panel(runtime, viewer, theme), right[1]);
}

fn attestation_deck_panel(
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) -> Paragraph<'static> {
    let (label, color, detail) = proof_status_summary(runtime, viewer, theme);
    let action_hint = proof_action_hint(runtime, viewer);
    let status_line = match &viewer.proof.phase {
        ProofPhase::Proving {
            started_at,
            proof_budget_steps,
            ..
        } => format!(
            "worker status  replaying to HALT and constructing a proof  •  budget {}  •  {:.1}s elapsed",
            proof_budget_steps,
            started_at.elapsed().as_secs_f64()
        ),
        ProofPhase::Verifying { started_at, .. } => format!(
            "worker status  replaying the verifier  •  {:.1}s elapsed",
            started_at.elapsed().as_secs_f64()
        ),
        ProofPhase::Ready { minted_at, .. } => format!(
            "worker status  proof minted {:.1}s ago",
            minted_at.elapsed().as_secs_f64()
        ),
        ProofPhase::Verified { verified_at, .. } => format!(
            "worker status  verified {:.1}s ago",
            verified_at.elapsed().as_secs_f64()
        ),
        ProofPhase::Failed { stage, .. } => format!("worker status  last {stage} attempt failed"),
        ProofPhase::Idle => "worker status  standing by".to_string(),
    };

    Paragraph::new(vec![
        badge_line(
            &[
                (format!(" {} ", label), theme.bg, color),
                (
                    format!(" {} ", runtime.model().config().attention_mode),
                    theme.bg,
                    theme.accent_soft,
                ),
                (
                    format!(" budget {} ", viewer.proof_budget_steps),
                    theme.bg,
                    theme.accent_alt,
                ),
            ],
            theme,
        ),
        Line::from(vec![
            Span::styled("detail ", Style::default().fg(theme.muted)),
            Span::styled(detail, Style::default().fg(theme.text)),
        ]),
        workflow_step_line(viewer, theme),
        Line::from(vec![
            Span::styled("action ", Style::default().fg(theme.muted)),
            Span::styled(action_hint, Style::default().fg(theme.accent)),
        ]),
        Line::from(vec![
            Span::styled("claim ", Style::default().fg(theme.muted)),
            Span::styled(
                format!(
                    "{} instructions  •  {} layers  •  {} memory cells",
                    runtime.model().program().len(),
                    runtime.model().config().num_layers,
                    runtime.state().memory.len()
                ),
                Style::default().fg(theme.text),
            ),
        ]),
        Line::from(vec![
            Span::styled("flow ", Style::default().fg(theme.muted)),
            Span::styled(status_line, Style::default().fg(theme.accent_alt)),
        ]),
    ])
    .block(panel_block("Attestation Deck", theme))
    .wrap(Wrap { trim: true })
}

fn attestation_compact_panel(
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) -> Paragraph<'static> {
    let proof = viewer.proof.current_proof();
    let fingerprint = proof
        .map(|proof| proof_fingerprint(&proof.proof))
        .unwrap_or_else(|| "pending".to_string());
    let steps = proof
        .map(|proof| proof.claim.steps)
        .unwrap_or_else(|| runtime.step_count());
    let state = proof
        .map(|proof| &proof.claim.final_state)
        .unwrap_or_else(|| runtime.state());
    let verification = match &viewer.proof.phase {
        ProofPhase::Verified { .. } => "verified",
        ProofPhase::Verifying { .. } => "verifying",
        ProofPhase::Ready { .. } => "ready",
        ProofPhase::Failed {
            stage: "verify", ..
        } => "verify failed",
        _ => "not minted",
    };

    Paragraph::new(vec![
        Line::from(vec![
            Span::styled("proof id ", Style::default().fg(theme.muted)),
            Span::styled(
                fingerprint,
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("status ", Style::default().fg(theme.muted)),
            Span::styled(verification, Style::default().fg(theme.accent)),
            Span::styled("  •  steps ", Style::default().fg(theme.muted)),
            Span::styled(steps.to_string(), Style::default().fg(theme.text)),
        ]),
        Line::from(vec![
            Span::styled("final ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("pc {}  acc {}  sp {}", state.pc, state.acc, state.sp),
                Style::default().fg(theme.text),
            ),
        ]),
        Line::from(vec![
            Span::styled("flags ", Style::default().fg(theme.muted)),
            Span::styled(
                format!(
                    "halt {}  zero {}  carry {}",
                    on_off(state.halted),
                    on_off(state.zero_flag),
                    on_off(state.carry_flag)
                ),
                Style::default().fg(theme.text),
            ),
        ]),
        Line::from(vec![
            Span::styled("keys ", Style::default().fg(theme.muted)),
            Span::styled(
                "enter/p attest  •  v re-verify  •  [/] budget",
                Style::default().fg(theme.accent_soft),
            ),
        ]),
    ])
    .block(panel_block("Proof Snapshot", theme))
    .wrap(Wrap { trim: true })
}

fn proof_artifact_panel(viewer: &ViewerState, theme: Theme) -> Paragraph<'static> {
    if let Some(proof) = viewer.proof.current_proof() {
        let verification = match &viewer.proof.phase {
            ProofPhase::Verified { .. } => "verified",
            ProofPhase::Verifying { .. } => "verifying",
            ProofPhase::Failed {
                stage: "verify", ..
            } => "verify failed",
            _ => "ready",
        };

        Paragraph::new(vec![
            badge_line(
                &[
                    (
                        format!(" {} bytes ", proof.proof.len()),
                        theme.bg,
                        theme.accent,
                    ),
                    (
                        format!(" {} ", verification),
                        theme.bg,
                        if matches!(&viewer.proof.phase, ProofPhase::Verified { .. }) {
                            theme.success
                        } else {
                            theme.accent_alt
                        },
                    ),
                ],
                theme,
            ),
            Line::from(vec![
                Span::styled("fingerprint ", Style::default().fg(theme.muted)),
                Span::styled(
                    proof_fingerprint(&proof.proof),
                    Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(vec![
                Span::styled("fri ", Style::default().fg(theme.muted)),
                Span::styled(
                    format!(
                        "expansion {}  •  colinearity {}  •  security {}",
                        proof.claim.options.expansion_factor,
                        proof.claim.options.num_colinearity_checks,
                        proof.claim.options.security_level
                    ),
                    Style::default().fg(theme.text),
                ),
            ]),
            Line::from(vec![
                Span::styled("artifact ", Style::default().fg(theme.muted)),
                Span::styled(
                    "held in memory for instant re-verification",
                    Style::default().fg(theme.accent_soft),
                ),
            ]),
        ])
        .block(panel_block("Proof Artifact", theme))
        .wrap(Wrap { trim: true })
    } else {
        Paragraph::new(vec![
            Line::from(vec![
                Span::styled("artifact ", Style::default().fg(theme.muted)),
                Span::styled(
                    "none yet",
                    Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(vec![
                Span::styled("launch ", Style::default().fg(theme.muted)),
                Span::styled(
                    "press enter or p to run replay -> prove -> verify",
                    Style::default().fg(theme.accent),
                ),
            ]),
            Line::from(vec![
                Span::styled("budget ", Style::default().fg(theme.muted)),
                Span::styled(
                    format!(
                        "current worker budget is {} steps  •  adjust with [ or ]",
                        viewer.proof_budget_steps
                    ),
                    Style::default().fg(theme.accent_soft),
                ),
            ]),
        ])
        .block(panel_block("Proof Artifact", theme))
        .wrap(Wrap { trim: true })
    }
}

fn proof_eligibility_panel(
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) -> Paragraph<'static> {
    let attention_supported = matches!(
        runtime.model().config().attention_mode,
        Attention2DMode::AverageHard
    );
    let static_support = validate_execution_stark_support(
        runtime.model().program(),
        &runtime.model().config().attention_mode,
    );
    let carry_free = !trace_has_carry(runtime);

    Paragraph::new(vec![
        proof_state_line(
            "attention",
            if attention_supported { "PASS" } else { "FAIL" },
            if attention_supported {
                theme.success
            } else {
                theme.danger
            },
            if attention_supported {
                "average-hard"
            } else {
                "non-proof attention mode"
            },
            theme,
        ),
        proof_state_line(
            "air rules",
            if static_support.is_ok() {
                "PASS"
            } else {
                "FAIL"
            },
            if static_support.is_ok() {
                theme.success
            } else {
                theme.danger
            },
            static_support
                .as_ref()
                .map(|_| "instruction set supported")
                .unwrap_or("unsupported for current AIR"),
            theme,
        ),
        proof_state_line(
            "preview",
            if runtime.state().halted {
                "HALTED"
            } else if runtime.step_count() >= runtime.max_steps() {
                "LIMIT"
            } else {
                "LIVE"
            },
            if runtime.state().halted {
                theme.success
            } else if runtime.step_count() >= runtime.max_steps() {
                theme.accent_soft
            } else {
                theme.accent_alt
            },
            if runtime.state().halted {
                "the current preview already produced a halted claim"
            } else if runtime.step_count() >= runtime.max_steps() {
                "preview stopped early; the attestation worker can still rerun from scratch"
            } else {
                "preview is still live; attestation will replay independently"
            },
            theme,
        ),
        proof_state_line(
            "budget",
            "WORKER",
            theme.accent,
            &format!(
                "{} steps  •  enter/p launches the full attestation flow",
                viewer.proof_budget_steps
            ),
            theme,
        ),
        proof_state_line(
            "carry",
            if carry_free { "CLEAN" } else { "BLOCK" },
            if carry_free {
                theme.success
            } else {
                theme.danger
            },
            if carry_free {
                "no overflow seen in the preview trace so far"
            } else {
                "carry observed; proof blocked"
            },
            theme,
        ),
    ])
    .block(panel_block("Eligibility", theme))
    .wrap(Wrap { trim: true })
}

fn public_claim_panel(
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) -> Paragraph<'static> {
    let proof = viewer.proof.current_proof();
    let state = proof
        .map(|proof| &proof.claim.final_state)
        .unwrap_or_else(|| runtime.state());
    let steps = proof
        .map(|proof| proof.claim.steps)
        .unwrap_or_else(|| runtime.step_count());
    let attention = proof
        .map(|proof| proof.claim.attention_mode.to_string())
        .unwrap_or_else(|| runtime.model().config().attention_mode.to_string());
    let seal = if proof.is_some() {
        "sealed"
    } else {
        "candidate"
    };

    Paragraph::new(vec![
        Line::from(vec![
            Span::styled("claim ", Style::default().fg(theme.muted)),
            Span::styled(
                seal,
                Style::default()
                    .fg(theme.accent)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled("  •  steps ", Style::default().fg(theme.muted)),
            Span::styled(steps.to_string(), Style::default().fg(theme.text)),
        ]),
        Line::from(vec![
            Span::styled("state ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("pc {}  acc {}  sp {}", state.pc, state.acc, state.sp),
                Style::default().fg(theme.text),
            ),
        ]),
        Line::from(vec![
            Span::styled("flags ", Style::default().fg(theme.muted)),
            Span::styled(
                format!(
                    "halt {}  zero {}  carry {}",
                    on_off(state.halted),
                    on_off(state.zero_flag),
                    on_off(state.carry_flag)
                ),
                Style::default().fg(theme.text),
            ),
        ]),
        Line::from(vec![
            Span::styled("shape ", Style::default().fg(theme.muted)),
            Span::styled(
                format!(
                    "{} instructions  •  {} memory  •  {}",
                    runtime.model().program().len(),
                    state.memory.len(),
                    attention
                ),
                Style::default().fg(theme.text),
            ),
        ]),
    ])
    .block(panel_block("Public Claim", theme))
    .wrap(Wrap { trim: true })
}

fn dispatch_panel(
    runtime: &ExecutionRuntime,
    next_dispatch: Option<&DispatchInfo>,
    viewer: &ViewerState,
    theme: Theme,
) -> Paragraph<'static> {
    let latest = runtime.events().last();
    let latest_copy = latest
        .map(|event| {
            format!(
                "#{} L{} {}  pc {}->{}  acc {}->{}",
                event.step,
                event.layer_idx.unwrap_or(0),
                event.instruction,
                event.state_before.pc,
                event.state_after.pc,
                event.state_before.acc,
                event.state_after.acc
            )
        })
        .unwrap_or_else(|| "no steps yet".to_string());
    let next_copy = next_dispatch
        .map(|dispatch| format!("L{} {}", dispatch.layer_idx, dispatch.instruction))
        .unwrap_or_else(|| "complete".to_string());

    Paragraph::new(vec![
        Line::from(vec![
            Span::styled("next cue ", Style::default().fg(theme.muted)),
            Span::styled(
                next_copy,
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("viewer ", Style::default().fg(theme.muted)),
            Span::styled(viewer.mode.title(), Style::default().fg(theme.accent)),
        ]),
        Line::from(vec![
            Span::styled("latest ", Style::default().fg(theme.muted)),
            Span::styled(latest_copy, Style::default().fg(theme.text)),
        ]),
        Line::from(vec![
            Span::styled("copy ", Style::default().fg(theme.muted)),
            Span::styled(
                latest
                    .map(|event| instruction_mood(event.instruction))
                    .unwrap_or("warm-up frames"),
                Style::default().fg(theme.accent_soft),
            ),
        ]),
    ])
    .block(panel_block("Lead Instruction", theme))
    .wrap(Wrap { trim: true })
}

fn progress_panel(
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) -> Paragraph<'static> {
    let total = runtime.max_steps().max(1) as f64;
    let ratio = (runtime.step_count() as f64 / total).clamp(0.0, 1.0);
    let memory_pressure = memory_pressure(runtime);

    Paragraph::new(vec![
        Line::from(vec![
            Span::styled("steps ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{}/{}", runtime.step_count(), runtime.max_steps()),
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ),
        ]),
        gauge_line("progress", ratio, theme.accent, theme.panel_alt),
        Line::from(vec![
            Span::styled("tempo ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{}ms / frame", viewer.tick_ms),
                Style::default().fg(theme.text),
            ),
        ]),
        gauge_line(
            "memory heat",
            memory_pressure,
            theme.accent_alt,
            theme.panel_alt,
        ),
    ])
    .block(panel_block("Pulse", theme))
}

fn register_panel(runtime: &ExecutionRuntime, theme: Theme) -> Paragraph<'static> {
    let state = runtime.state();
    Paragraph::new(vec![
        badge_line(
            &[
                (format!(" PC {} ", state.pc), theme.bg, theme.accent_soft),
                (format!(" ACC {} ", state.acc), theme.bg, theme.accent),
                (format!(" SP {} ", state.sp), theme.bg, theme.accent_alt),
            ],
            theme,
        ),
        badge_line(
            &[
                (
                    format!(" ZERO {} ", on_off(state.zero_flag)),
                    theme.bg,
                    if state.zero_flag {
                        theme.success
                    } else {
                        theme.border
                    },
                ),
                (
                    format!(" CARRY {} ", on_off(state.carry_flag)),
                    theme.bg,
                    if state.carry_flag {
                        theme.accent_soft
                    } else {
                        theme.border
                    },
                ),
                (
                    format!(" HALT {} ", on_off(state.halted)),
                    theme.bg,
                    if state.halted {
                        theme.danger
                    } else {
                        theme.border
                    },
                ),
            ],
            theme,
        ),
        Line::from(vec![
            Span::styled("memory cells ", Style::default().fg(theme.muted)),
            Span::styled(
                state.memory.len().to_string(),
                Style::default().fg(theme.text),
            ),
            Span::styled("  •  ", Style::default().fg(theme.muted)),
            Span::styled("events ", Style::default().fg(theme.muted)),
            Span::styled(
                runtime.events().len().to_string(),
                Style::default().fg(theme.text),
            ),
        ]),
    ])
    .block(panel_block("Registers", theme))
    .wrap(Wrap { trim: true })
}

fn render_history_chart(
    frame: &mut Frame,
    area: Rect,
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) {
    let acc_points = viewer
        .acc_history
        .iter()
        .enumerate()
        .map(|(idx, value)| (idx as f64, *value as f64))
        .collect::<Vec<_>>();
    let pc_points = viewer
        .pc_history
        .iter()
        .enumerate()
        .map(|(idx, value)| (idx as f64, *value as f64))
        .collect::<Vec<_>>();
    let max_x = acc_points.len().max(pc_points.len()).max(2) as f64 - 1.0;
    let acc_max = viewer
        .acc_history
        .iter()
        .map(|value| value.abs())
        .max()
        .unwrap_or(1)
        .max(1) as f64;
    let y_max = acc_max.max(runtime.model().program().len().max(1) as f64);

    let datasets = vec![
        Dataset::default()
            .name("acc")
            .graph_type(GraphType::Line)
            .marker(Marker::Braille)
            .style(Style::default().fg(theme.accent))
            .data(&acc_points),
        Dataset::default()
            .name("pc")
            .graph_type(GraphType::Line)
            .marker(Marker::Dot)
            .style(Style::default().fg(theme.accent_alt))
            .data(&pc_points),
    ];

    let chart = Chart::new(datasets)
        .block(panel_block("Signal Drift", theme))
        .x_axis(Axis::default().bounds([0.0, max_x.max(1.0)]).labels([
            Span::styled("0", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{:.0}", max_x / 2.0),
                Style::default().fg(theme.muted),
            ),
            Span::styled(format!("{max_x:.0}"), Style::default().fg(theme.muted)),
        ]))
        .y_axis(Axis::default().bounds([-y_max, y_max]).labels([
            Span::styled(format!("-{y_max:.0}"), Style::default().fg(theme.muted)),
            Span::styled("0", Style::default().fg(theme.muted)),
            Span::styled(format!("{y_max:.0}"), Style::default().fg(theme.muted)),
        ]));

    frame.render_widget(chart, area);
}

fn throughput_panel(viewer: &ViewerState, theme: Theme) -> Paragraph<'static> {
    let peak = viewer.throughput_history.iter().copied().max().unwrap_or(0);
    let current = viewer.throughput_history.last().copied().unwrap_or(0);
    Paragraph::new(vec![
        Line::from(vec![
            Span::styled("current ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{current} steps/s"),
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("peak ", Style::default().fg(theme.muted)),
            Span::styled(format!("{peak}"), Style::default().fg(theme.accent_soft)),
        ]),
        Line::from(vec![Span::styled(
            sparkline_string(&viewer.throughput_history, 34),
            Style::default().fg(theme.accent_alt),
        )]),
    ])
    .block(panel_block("Tempo Trail", theme))
    .wrap(Wrap { trim: true })
}

fn layer_panel<'a>(runtime: &ExecutionRuntime, theme: Theme) -> BarChart<'a> {
    let bars = layer_bars(runtime, theme);
    BarChart::default()
        .block(panel_block("Layer Spotlight", theme))
        .data(BarGroup::default().bars(&bars))
        .bar_width(6)
        .bar_gap(1)
}

fn trace_list(runtime: &ExecutionRuntime, theme: Theme, limit: usize) -> List<'static> {
    let items = runtime
        .events()
        .iter()
        .rev()
        .take(limit)
        .map(|event| {
            ListItem::new(vec![
                Line::from(vec![
                    Span::styled(
                        format!("#{:03}", event.step),
                        Style::default().fg(theme.accent_soft),
                    ),
                    Span::styled("  ", Style::default().fg(theme.muted)),
                    Span::styled(
                        format!("L{}", event.layer_idx.unwrap_or(0)),
                        Style::default().fg(theme.accent_alt),
                    ),
                    Span::styled("  ", Style::default().fg(theme.muted)),
                    Span::styled(
                        event.instruction.to_string(),
                        Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
                    ),
                ]),
                Line::from(vec![
                    Span::styled("pc ", Style::default().fg(theme.muted)),
                    Span::styled(
                        format!("{}→{}", event.state_before.pc, event.state_after.pc),
                        Style::default().fg(theme.text),
                    ),
                    Span::styled("  •  acc ", Style::default().fg(theme.muted)),
                    Span::styled(
                        format!("{}→{}", event.state_before.acc, event.state_after.acc),
                        Style::default().fg(theme.text),
                    ),
                ]),
            ])
        })
        .collect::<Vec<_>>();

    List::new(items).block(panel_block("Live Trace", theme))
}

fn memory_table(runtime: &ExecutionRuntime, theme: Theme) -> Table<'static> {
    let write_counts = memory_write_counts(runtime);
    let max_writes = write_counts.iter().copied().max().unwrap_or(1).max(1);
    let rows = runtime
        .state()
        .memory
        .iter()
        .enumerate()
        .map(|(idx, value)| {
            let writes = write_counts[idx];
            let style = if latest_write_cell(runtime) == Some(idx) {
                Style::default()
                    .fg(theme.text)
                    .bg(theme.panel_alt)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(theme.text)
            };

            Row::new(vec![
                Cell::from(format!("{idx:02}")),
                Cell::from(value.to_string()),
                Cell::from(heat_bar(writes, max_writes, 8)),
                Cell::from(format!("{writes}")),
            ])
            .style(style)
        })
        .collect::<Vec<_>>();

    Table::new(
        rows,
        [
            Constraint::Length(5),
            Constraint::Length(10),
            Constraint::Length(10),
            Constraint::Length(8),
        ],
    )
    .header(
        Row::new(vec!["addr", "value", "heat", "writes"]).style(
            Style::default()
                .fg(theme.accent_soft)
                .add_modifier(Modifier::BOLD),
        ),
    )
    .block(panel_block("Memory Dressing Room", theme))
}

fn memory_hotspots<'a>(runtime: &ExecutionRuntime, theme: Theme) -> BarChart<'a> {
    let write_counts = memory_write_counts(runtime);
    let bars = write_counts
        .iter()
        .enumerate()
        .take(8)
        .map(|(idx, count)| {
            let style = if latest_write_cell(runtime) == Some(idx) {
                Style::default().fg(theme.accent).bg(theme.accent)
            } else {
                Style::default().fg(theme.accent_alt)
            };
            Bar::default()
                .value(*count)
                .label(Line::from(format!("{idx:02}")))
                .text_value(count.to_string())
                .style(style)
                .value_style(
                    Style::default()
                        .fg(theme.bg)
                        .bg(style.fg.unwrap_or(theme.accent)),
                )
        })
        .collect::<Vec<_>>();

    BarChart::default()
        .block(panel_block("Hot Cells", theme))
        .data(BarGroup::default().bars(&bars))
        .bar_width(5)
        .bar_gap(1)
}

fn memory_story(runtime: &ExecutionRuntime, theme: Theme) -> Paragraph<'static> {
    let latest_write = latest_write_cell(runtime);
    let write_counts = memory_write_counts(runtime);
    let hottest = write_counts
        .iter()
        .enumerate()
        .max_by_key(|(_, count)| **count)
        .map(|(idx, count)| format!("cell {idx:02} with {count} writes"))
        .unwrap_or_else(|| "quiet floor".to_string());
    let spotlight = latest_write
        .map(|idx| format!("latest write hit cell {idx:02}"))
        .unwrap_or_else(|| "no writes yet".to_string());

    Paragraph::new(vec![
        Line::from(vec![
            Span::styled("spotlight ", Style::default().fg(theme.muted)),
            Span::styled(spotlight, Style::default().fg(theme.text)),
        ]),
        Line::from(vec![
            Span::styled("hottest ", Style::default().fg(theme.muted)),
            Span::styled(hottest, Style::default().fg(theme.accent)),
        ]),
        Line::from(vec![
            Span::styled("pressure ", Style::default().fg(theme.muted)),
            Span::styled(
                format!("{:.0}%", memory_pressure(runtime) * 100.0),
                Style::default().fg(theme.accent_alt),
            ),
        ]),
        Line::from(vec![
            Span::styled("texture ", Style::default().fg(theme.muted)),
            Span::styled(
                "address history rendered straight from hull-backed memory",
                Style::default().fg(theme.text),
            ),
        ]),
    ])
    .block(panel_block("Memory Story", theme))
    .wrap(Wrap { trim: true })
}

fn recent_event_panel(runtime: &ExecutionRuntime, theme: Theme) -> Paragraph<'static> {
    let event = runtime.events().last();
    let changed = event.and_then(event_write_index);
    Paragraph::new(vec![
        Line::from(vec![
            Span::styled("latest event ", Style::default().fg(theme.muted)),
            Span::styled(
                event
                    .map(|entry| entry.instruction.to_string())
                    .unwrap_or_else(|| "idle".to_string()),
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("movement ", Style::default().fg(theme.muted)),
            Span::styled(
                event
                    .map(|entry| {
                        format!(
                            "pc {}→{}  acc {}→{}",
                            entry.state_before.pc,
                            entry.state_after.pc,
                            entry.state_before.acc,
                            entry.state_after.acc
                        )
                    })
                    .unwrap_or_else(|| "waiting for the first step".to_string()),
                Style::default().fg(theme.text),
            ),
        ]),
        Line::from(vec![
            Span::styled("memory ", Style::default().fg(theme.muted)),
            Span::styled(
                changed
                    .map(|idx| format!("cell {idx:02} took the write"))
                    .unwrap_or_else(|| "no memory mutation".to_string()),
                Style::default().fg(theme.accent_soft),
            ),
        ]),
        Line::from(vec![
            Span::styled("tone ", Style::default().fg(theme.muted)),
            Span::styled(
                event
                    .map(|entry| instruction_mood(entry.instruction))
                    .unwrap_or("stage lights warming up"),
                Style::default().fg(theme.accent),
            ),
        ]),
    ])
    .block(panel_block("Event Detail", theme))
    .wrap(Wrap { trim: true })
}

fn footer_panel(
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) -> Paragraph<'static> {
    let footer = Line::from(vec![
        Span::styled(
            "q",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" quit  ", Style::default().fg(theme.muted)),
        Span::styled(
            "space",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" pause  ", Style::default().fg(theme.muted)),
        Span::styled(
            "n",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" step  ", Style::default().fg(theme.muted)),
        Span::styled(
            "1-4",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" view  ", Style::default().fg(theme.muted)),
        Span::styled(
            "p",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" attest  ", Style::default().fg(theme.muted)),
        Span::styled(
            "v",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" verify  ", Style::default().fg(theme.muted)),
        Span::styled(
            "[/]",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" budget  ", Style::default().fg(theme.muted)),
        Span::styled(
            "t",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" theme  ", Style::default().fg(theme.muted)),
        Span::styled(
            "+/-",
            Style::default()
                .fg(theme.accent)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" tempo  ", Style::default().fg(theme.muted)),
        Span::styled(
            format!("status {}", viewer_status(runtime, viewer)),
            Style::default().fg(status_color(runtime, viewer, theme)),
        ),
    ]);

    Paragraph::new(footer)
        .block(
            Block::default()
                .borders(Borders::TOP)
                .border_style(Style::default().fg(theme.border))
                .style(Style::default().bg(theme.bg)),
        )
        .alignment(Alignment::Left)
}

fn render_overlay(
    frame: &mut Frame,
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) {
    let area = centered_rect(frame.area(), 58, 24);
    frame.render_widget(Clear, area);
    frame.render_widget(
        Paragraph::new(vec![
            Line::from(Span::styled(
                "INTERMISSION",
                Style::default()
                    .fg(theme.bg)
                    .bg(theme.accent)
                    .add_modifier(Modifier::BOLD),
            ))
            .centered(),
            Line::from(""),
            Line::from(Span::styled(
                "paused with the lights still on",
                Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
            ))
            .centered(),
            Line::from(""),
            Line::from(format!(
                "step {} of {}  •  pc {}  •  acc {}",
                runtime.step_count(),
                runtime.max_steps(),
                runtime.state().pc,
                runtime.state().acc
            ))
            .centered(),
            Line::from(format!(
                "theme {}  •  {}ms tempo",
                viewer.theme().name,
                viewer.tick_ms
            ))
            .centered(),
            Line::from(""),
            Line::from("space to resume  •  n to single-step  •  p to launch attestation").centered(),
            Line::from("4 for attestation view  •  v to re-verify  •  [/] adjust worker budget  •  q to quit")
                .centered(),
        ])
        .block(
            panel_block("Spotlight", theme)
                .style(Style::default().bg(theme.panel_alt))
                .padding(Padding::new(2, 2, 1, 1)),
        )
        .alignment(Alignment::Center),
        area,
    );
}

fn run_finished(runtime: &ExecutionRuntime) -> bool {
    runtime.state().halted || runtime.step_count() >= runtime.max_steps()
}

fn panel_block(title: &str, theme: Theme) -> Block<'static> {
    Block::default()
        .title(
            Line::from(vec![
                Span::styled(" ", Style::default().bg(theme.accent)),
                Span::styled(
                    format!(" {title} "),
                    Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
                ),
            ])
            .left_aligned(),
        )
        .borders(Borders::ALL)
        .border_set(symbols::border::PROPORTIONAL_TALL)
        .border_style(Style::default().fg(theme.border))
        .style(Style::default().bg(theme.panel))
        .padding(Padding::horizontal(1))
}

fn badge_line(specs: &[(String, Color, Color)], theme: Theme) -> Line<'static> {
    let mut spans = Vec::with_capacity(specs.len() * 2);
    for (idx, (label, fg, bg)) in specs.iter().enumerate() {
        if idx > 0 {
            spans.push(Span::styled(" ", Style::default().fg(theme.muted)));
        }
        spans.push(Span::styled(
            label.clone(),
            Style::default()
                .fg(*fg)
                .bg(*bg)
                .add_modifier(Modifier::BOLD),
        ));
    }
    Line::from(spans)
}

fn gauge_line(label: &str, ratio: f64, fill: Color, unfilled: Color) -> Line<'static> {
    let width = 18usize;
    let filled = (ratio.clamp(0.0, 1.0) * width as f64).round() as usize;
    let mut spans = vec![Span::raw(format!("{label:<11}"))];
    for idx in 0..width {
        let style = if idx < filled {
            Style::default().fg(fill)
        } else {
            Style::default().fg(unfilled)
        };
        spans.push(Span::styled(if idx < filled { "█" } else { "·" }, style));
    }
    spans.push(Span::raw(format!(" {:>3.0}%", ratio * 100.0)));
    Line::from(spans)
}

enum ProofAvailability {
    Ready,
    Blocked(String),
}

fn proof_status_summary(
    runtime: &ExecutionRuntime,
    viewer: &ViewerState,
    theme: Theme,
) -> (&'static str, Color, String) {
    match &viewer.proof.phase {
        ProofPhase::Proving {
            started_at,
            proof_budget_steps,
            auto_verify,
        } => (
            if *auto_verify { "ATTESTING" } else { "PROVING" },
            theme.accent,
            format!(
                "replaying up to {} steps, then constructing {} ({:.1}s)",
                proof_budget_steps,
                if *auto_verify {
                    "and verifying a proof"
                } else {
                    "a proof"
                },
                started_at.elapsed().as_secs_f64()
            ),
        ),
        ProofPhase::Verifying { started_at, .. } => (
            "VERIFYING",
            theme.accent_alt,
            format!(
                "checking the generated proof against its public claim ({:.1}s)",
                started_at.elapsed().as_secs_f64()
            ),
        ),
        ProofPhase::Ready { .. } => (
            "PROOF READY",
            theme.accent_soft,
            "press v to verify the in-memory artifact".to_string(),
        ),
        ProofPhase::Verified { .. } => (
            "VERIFIED",
            theme.success,
            "the worker completed replay, proving, and verification".to_string(),
        ),
        ProofPhase::Failed { message, .. } => ("ERROR", theme.danger, message.clone()),
        ProofPhase::Idle => match proof_availability(runtime) {
            ProofAvailability::Ready => (
                "READY",
                theme.accent_soft,
                if runtime.state().halted {
                    format!(
                        "preview is already halted; press p to attest with a {}-step worker budget",
                        viewer.proof_budget_steps
                    )
                } else if runtime.step_count() >= runtime.max_steps() {
                    format!(
                        "preview hit its {}-step limit; press p to rerun and attest with budget {}",
                        runtime.max_steps(),
                        viewer.proof_budget_steps
                    )
                } else {
                    format!(
                        "press p to run replay -> prove -> verify with a {}-step worker budget",
                        viewer.proof_budget_steps
                    )
                },
            ),
            ProofAvailability::Blocked(message) => ("BLOCKED", theme.danger, message),
        },
    }
}

fn proof_action_hint(runtime: &ExecutionRuntime, viewer: &ViewerState) -> &'static str {
    if viewer.proof.is_busy() {
        "the worker is driving the full flow; you can stay here or browse the other views"
    } else if viewer.proof.current_proof().is_some() {
        "press p to regenerate the full flow, or v to re-run verification only"
    } else if proof_can_start(runtime) {
        "press enter or p to launch the end-to-end attestation workflow"
    } else {
        "the current program shape is outside the supported proof surface"
    }
}

fn proof_can_start(runtime: &ExecutionRuntime) -> bool {
    matches!(proof_availability(runtime), ProofAvailability::Ready)
}

fn proof_availability(runtime: &ExecutionRuntime) -> ProofAvailability {
    if let Err(error) = validate_execution_stark_support(
        runtime.model().program(),
        &runtime.model().config().attention_mode,
    ) {
        return ProofAvailability::Blocked(error.to_string());
    }

    if trace_has_carry(runtime) {
        return ProofAvailability::Blocked(
            "carry_flag appeared in the trace; overflowing arithmetic is outside the current AIR"
                .to_string(),
        );
    }

    ProofAvailability::Ready
}

fn workflow_step_line(viewer: &ViewerState, theme: Theme) -> Line<'static> {
    let (replay_color, prove_color, verify_color) = match &viewer.proof.phase {
        ProofPhase::Idle => (theme.accent_soft, theme.border, theme.border),
        ProofPhase::Proving { .. } => (theme.accent, theme.accent, theme.border),
        ProofPhase::Ready { .. } => (theme.success, theme.success, theme.border),
        ProofPhase::Verifying { .. } => (theme.success, theme.success, theme.accent_alt),
        ProofPhase::Verified { .. } => (theme.success, theme.success, theme.success),
        ProofPhase::Failed { stage, .. } => match *stage {
            "prove" => (theme.success, theme.danger, theme.border),
            "verify" => (theme.success, theme.success, theme.danger),
            _ => (theme.accent_soft, theme.danger, theme.border),
        },
    };

    Line::from(vec![
        Span::styled("path ", Style::default().fg(theme.muted)),
        Span::styled(
            "[1 replay]",
            Style::default()
                .fg(replay_color)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" -> ", Style::default().fg(theme.muted)),
        Span::styled(
            "[2 prove]",
            Style::default()
                .fg(prove_color)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(" -> ", Style::default().fg(theme.muted)),
        Span::styled(
            "[3 verify]",
            Style::default()
                .fg(verify_color)
                .add_modifier(Modifier::BOLD),
        ),
    ])
}

fn proof_state_line(
    label: &str,
    status: &str,
    color: Color,
    detail: &str,
    theme: Theme,
) -> Line<'static> {
    Line::from(vec![
        Span::styled(
            format!("{label:<10}"),
            Style::default()
                .fg(theme.muted)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            status.to_string(),
            Style::default().fg(color).add_modifier(Modifier::BOLD),
        ),
        Span::styled("  ", Style::default().fg(theme.muted)),
        Span::styled(detail.to_string(), Style::default().fg(theme.text)),
    ])
}

fn viewer_status(runtime: &ExecutionRuntime, viewer: &ViewerState) -> &'static str {
    if runtime.state().halted {
        "HALTED"
    } else if runtime.step_count() >= runtime.max_steps() {
        "LIMIT"
    } else if viewer.paused {
        "PAUSED"
    } else {
        "RUNNING"
    }
}

fn status_color(runtime: &ExecutionRuntime, viewer: &ViewerState, theme: Theme) -> Color {
    if runtime.state().halted {
        theme.danger
    } else if runtime.step_count() >= runtime.max_steps() {
        theme.accent_soft
    } else if viewer.paused {
        theme.accent_alt
    } else {
        theme.accent
    }
}

fn instruction_mood(instruction: Instruction) -> &'static str {
    match instruction {
        Instruction::Load(_) | Instruction::LoadImmediate(_) => "lifting values into the spotlight",
        Instruction::Store(_) => "stitching a fresh write into memory",
        Instruction::Push | Instruction::Pop => "stack fabric folding through the frame",
        Instruction::AddImmediate(_)
        | Instruction::AddMemory(_)
        | Instruction::SubImmediate(_)
        | Instruction::SubMemory(_)
        | Instruction::MulImmediate(_)
        | Instruction::MulMemory(_) => "arithmetic tailored with sharp lines",
        Instruction::AndImmediate(_)
        | Instruction::AndMemory(_)
        | Instruction::OrImmediate(_)
        | Instruction::OrMemory(_)
        | Instruction::XorImmediate(_)
        | Instruction::XorMemory(_)
        | Instruction::CmpImmediate(_)
        | Instruction::CmpMemory(_) => "logic panels snapping into place",
        Instruction::Call(_) | Instruction::Ret => "subroutines looping through the catwalk",
        Instruction::Jump(_) | Instruction::JumpIfZero(_) | Instruction::JumpIfNotZero(_) => {
            "branch work with a dramatic turn"
        }
        Instruction::Halt => "the finale lands and holds",
        Instruction::Nop => "holding the pose without drift",
    }
}

fn on_off(value: bool) -> &'static str {
    if value {
        "ON"
    } else {
        "OFF"
    }
}

fn trace_has_carry(runtime: &ExecutionRuntime) -> bool {
    runtime.trace().iter().any(|state| state.carry_flag)
}

fn proof_fingerprint(bytes: &[u8]) -> String {
    let digest = Sha3_256::digest(bytes);
    digest
        .iter()
        .take(6)
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn latest_write_cell(runtime: &ExecutionRuntime) -> Option<usize> {
    runtime.events().last().and_then(event_write_index)
}

fn event_write_index(event: &crate::ExecutionTraceEntry) -> Option<usize> {
    event
        .state_before
        .memory
        .iter()
        .zip(event.state_after.memory.iter())
        .enumerate()
        .find_map(|(idx, (before, after))| (before != after).then_some(idx))
}

fn memory_write_counts(runtime: &ExecutionRuntime) -> Vec<u64> {
    (0..runtime.state().memory.len())
        .map(|idx| {
            runtime
                .memory()
                .history_len(idx as u8)
                .unwrap_or(0)
                .saturating_sub(1) as u64
        })
        .collect()
}

fn memory_pressure(runtime: &ExecutionRuntime) -> f64 {
    let write_counts = memory_write_counts(runtime);
    let total_writes = write_counts.iter().sum::<u64>();
    let cells = runtime.state().memory.len().max(1) as f64;
    (total_writes as f64 / (cells * 4.0)).clamp(0.0, 1.0)
}

fn layer_bars(runtime: &ExecutionRuntime, theme: Theme) -> Vec<Bar<'static>> {
    let mut hits = vec![0u64; runtime.model().config().num_layers];
    for event in runtime.events() {
        if let Some(layer_idx) = event.layer_idx {
            if let Some(slot) = hits.get_mut(layer_idx) {
                *slot += 1;
            }
        }
    }

    hits.into_iter()
        .enumerate()
        .map(|(idx, value)| {
            let color = match idx % 3 {
                0 => theme.accent,
                1 => theme.accent_soft,
                _ => theme.accent_alt,
            };
            Bar::default()
                .value(value)
                .label(Line::from(format!("L{idx}")))
                .text_value(value.to_string())
                .style(Style::default().fg(color))
                .value_style(Style::default().fg(theme.bg).bg(color))
        })
        .collect()
}

fn heat_bar(value: u64, max: u64, width: usize) -> String {
    if max == 0 || width == 0 {
        return String::new();
    }
    let filled = ((value as f64 / max as f64) * width as f64).round() as usize;
    let filled = filled.min(width);
    format!("{}{}", "█".repeat(filled), "·".repeat(width - filled))
}

fn sparkline_string(data: &[u64], width: usize) -> String {
    if data.is_empty() || width == 0 {
        return String::new();
    }

    let steps = data.len().min(width);
    let window = &data[data.len().saturating_sub(steps)..];
    let max_value = window.iter().copied().max().unwrap_or(1).max(1) as f64;
    let glyphs = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];

    window
        .iter()
        .map(|value| {
            let idx = (((*value as f64 / max_value) * (glyphs.len() - 1) as f64).round() as usize)
                .min(glyphs.len() - 1);
            glyphs[idx]
        })
        .collect()
}

fn initial_proof_budget(runtime: &ExecutionRuntime) -> usize {
    runtime.max_steps().max(256)
}

fn centered_rect(area: Rect, percent_x: u16, percent_y: u16) -> Rect {
    let [area] = Layout::vertical([Constraint::Percentage(percent_y)])
        .flex(Flex::Center)
        .areas(area);
    let [area] = Layout::horizontal([Constraint::Percentage(percent_x)])
        .flex(Flex::Center)
        .areas(area);
    area
}

fn push_limited<T>(items: &mut Vec<T>, value: T) {
    if items.len() == HISTORY_LIMIT {
        items.remove(0);
    }
    items.push(value);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Program, TransformerVm, TransformerVmConfig};

    fn runtime_for(
        program: Program,
        attention_mode: Attention2DMode,
        max_steps: usize,
    ) -> ExecutionRuntime {
        let config = TransformerVmConfig {
            attention_mode,
            ..TransformerVmConfig::default()
        };
        let model = TransformerVm::new(config, program).expect("model");
        ExecutionRuntime::new(model, max_steps)
    }

    #[test]
    fn proof_availability_is_ready_before_preview_halts() {
        let runtime = runtime_for(
            Program::new(vec![Instruction::LoadImmediate(1), Instruction::Halt], 4),
            Attention2DMode::AverageHard,
            8,
        );

        assert!(matches!(
            proof_availability(&runtime),
            ProofAvailability::Ready
        ));
    }

    #[test]
    fn proof_availability_is_ready_after_supported_halted_run() {
        let mut runtime = runtime_for(
            Program::new(vec![Instruction::LoadImmediate(1), Instruction::Halt], 4),
            Attention2DMode::AverageHard,
            8,
        );

        runtime.run().expect("run");

        assert!(matches!(
            proof_availability(&runtime),
            ProofAvailability::Ready
        ));
    }

    #[test]
    fn proof_availability_blocks_traces_that_raise_carry() {
        let mut runtime = runtime_for(
            Program::new(
                vec![
                    Instruction::LoadImmediate(i16::MAX),
                    Instruction::AddImmediate(1),
                    Instruction::Halt,
                ],
                4,
            ),
            Attention2DMode::AverageHard,
            8,
        );

        runtime.run().expect("run");

        match proof_availability(&runtime) {
            ProofAvailability::Blocked(message) => assert!(message.contains("carry_flag")),
            ProofAvailability::Ready => {
                panic!("expected carry-bearing trace to block proving")
            }
        }
    }

    #[test]
    fn proof_availability_blocks_unsupported_attention_modes() {
        let mut runtime = runtime_for(
            Program::new(vec![Instruction::LoadImmediate(1), Instruction::Halt], 4),
            Attention2DMode::Softmax,
            8,
        );

        runtime.run().expect("run");

        match proof_availability(&runtime) {
            ProofAvailability::Blocked(message) => assert!(message.contains("average-hard")),
            ProofAvailability::Ready => {
                panic!("expected unsupported attention mode to block proving")
            }
        }
    }

    #[test]
    fn initial_proof_budget_has_floor_above_small_preview_limits() {
        let runtime = runtime_for(
            Program::new(vec![Instruction::LoadImmediate(1), Instruction::Halt], 4),
            Attention2DMode::AverageHard,
            64,
        );

        assert_eq!(initial_proof_budget(&runtime), 256);
    }

    #[test]
    fn proof_fingerprint_is_short_hex() {
        let fingerprint = proof_fingerprint(&[1, 2, 3, 4]);
        assert_eq!(fingerprint.len(), 12);
        assert!(fingerprint.chars().all(|ch| ch.is_ascii_hexdigit()));
    }
}
