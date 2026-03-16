use std::fs;
use std::path::PathBuf;

use clap::{Parser, Subcommand};
use transformer_vm_rs::{ExecutionRuntime, ProgramCompiler, TransformerVmConfig};

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
        } => {
            let source = fs::read_to_string(&program).map_err(|io_error| {
                transformer_vm_rs::VmError::InvalidConfig(format!(
                    "failed to read program {}: {io_error}",
                    program.display()
                ))
            })?;

            let model = ProgramCompiler.compile_source(&source, TransformerVmConfig::default())?;
            let mut runtime = ExecutionRuntime::new(model, max_steps);
            let result = runtime.run()?;

            println!("program: {}", program.display());
            println!("steps: {}", result.steps);
            println!("halted: {}", result.halted);
            println!("pc: {}", result.final_state.pc);
            println!("acc: {}", result.final_state.acc);
            println!("zero_flag: {}", result.final_state.zero_flag);
            println!("carry_flag: {}", result.final_state.carry_flag);
            println!("memory: {:?}", result.final_state.memory);
            println!("elapsed_ms: {:.3}", result.elapsed.as_secs_f64() * 1000.0);
            println!("throughput_steps_per_sec: {:.2}", result.tokens_per_sec);

            if trace {
                for (idx, state) in runtime.trace().iter().enumerate() {
                    println!(
                        "trace[{idx:03}] pc={} acc={} zero={} carry={} halted={} memory={:?}",
                        state.pc,
                        state.acc,
                        state.zero_flag,
                        state.carry_flag,
                        state.halted,
                        state.memory
                    );
                }
            }
        }
    }

    Ok(())
}
