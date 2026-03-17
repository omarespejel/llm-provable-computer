use std::fs;
use std::path::{Path, PathBuf};
use std::str::FromStr;
use std::time::Duration;

use clap::{Parser, Subcommand};
use transformer_vm_rs::{
    run_execution_tui, Attention2DMode, ExecutionRuntime, ProgramCompiler, TransformerVmConfig,
    VmError,
};

#[derive(Debug, Parser)]
#[command(name = "tvm", about = "Run deterministic transformer-vm programs.")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    Run {
        program: PathBuf,
        #[arg(long, default_value_t = 512)]
        max_steps: usize,
        #[arg(long)]
        trace: bool,
        #[arg(long, default_value_t = 1)]
        layers: usize,
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
    },
    Tui {
        program: PathBuf,
        #[arg(long, default_value_t = 512)]
        max_steps: usize,
        #[arg(long, default_value_t = 1)]
        layers: usize,
        #[arg(long, default_value_t = 60)]
        tick_ms: u64,
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
    },
}

fn main() {
    if let Err(error) = run() {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}

fn run() -> transformer_vm_rs::Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Command::Run {
            program,
            max_steps,
            trace,
            layers,
            attention_mode,
        } => {
            let mut runtime = load_runtime(&program, max_steps, layers, attention_mode.clone())?;
            let result = runtime.run()?;

            println!("program: {}", program.display());
            println!("steps: {}", result.steps);
            println!("halted: {}", result.halted);
            println!("pc: {}", result.final_state.pc);
            println!("sp: {}", result.final_state.sp);
            println!("acc: {}", result.final_state.acc);
            println!("zero_flag: {}", result.final_state.zero_flag);
            println!("carry_flag: {}", result.final_state.carry_flag);
            println!("memory: {:?}", result.final_state.memory);
            println!("layers: {}", layers);
            println!("attention_mode: {}", attention_mode);
            println!("elapsed_ms: {:.3}", result.elapsed.as_secs_f64() * 1000.0);
            println!("throughput_steps_per_sec: {:.2}", result.tokens_per_sec);

            if trace {
                println!(
                    "trace[000] init pc={} sp={} acc={} zero={} carry={} halted={} memory={:?}",
                    runtime.trace()[0].pc,
                    runtime.trace()[0].sp,
                    runtime.trace()[0].acc,
                    runtime.trace()[0].zero_flag,
                    runtime.trace()[0].carry_flag,
                    runtime.trace()[0].halted,
                    runtime.trace()[0].memory
                );
                for event in runtime.events() {
                    println!(
                        "trace[{step:03}] layer={layer} instr=\"{instr}\" pc={pc} sp={sp} acc={acc} zero={zero} carry={carry} halted={halted} memory={memory:?}",
                        step = event.step,
                        layer = event.layer_idx,
                        instr = event.instruction,
                        pc = event.state_after.pc,
                        sp = event.state_after.sp,
                        acc = event.state_after.acc,
                        zero = event.state_after.zero_flag,
                        carry = event.state_after.carry_flag,
                        halted = event.state_after.halted,
                        memory = event.state_after.memory
                    );
                }
            }
        }
        Command::Tui {
            program,
            max_steps,
            layers,
            tick_ms,
            attention_mode,
        } => {
            let mut runtime = load_runtime(&program, max_steps, layers, attention_mode)?;
            run_execution_tui(&program, &mut runtime, Duration::from_millis(tick_ms))?;
        }
    }

    Ok(())
}

fn load_runtime(
    program: &Path,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
) -> transformer_vm_rs::Result<ExecutionRuntime> {
    let source = fs::read_to_string(program).map_err(|io_error| {
        VmError::InvalidConfig(format!(
            "failed to read program {}: {io_error}",
            program.display()
        ))
    })?;

    let config = TransformerVmConfig {
        num_layers: layers,
        attention_mode,
        ..TransformerVmConfig::default()
    };
    let model = ProgramCompiler.compile_source(&source, config)?;
    Ok(ExecutionRuntime::new(model, max_steps))
}

fn parse_attention_mode(input: &str) -> Result<Attention2DMode, String> {
    Attention2DMode::from_str(input)
}
