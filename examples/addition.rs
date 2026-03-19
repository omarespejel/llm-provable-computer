//! Visual addition execution through the TUI.
//!
//! Compiles a simple addition program (LOADI 5, ADD 3 → ACC=8) into
//! transformer weights and runs it with a live terminal visualization.
//!
//! Falls back to headless execution when no terminal is available.
//!
//! Usage:
//!   cargo run --example addition
//!   cargo run --example addition -- --tick-ms 100
//!   cargo run --example addition -- --headless

use std::io::IsTerminal;
use std::time::Duration;

use llm_provable_computer::{
    run_execution_tui, ExecutionRuntime, ProgramCompiler, TransformerVmConfig,
};

fn main() {
    let tick_ms: u64 = std::env::args()
        .skip_while(|arg| arg != "--tick-ms")
        .nth(1)
        .and_then(|val| val.parse().ok())
        .unwrap_or(80);

    let headless =
        std::env::args().any(|arg| arg == "--headless") || !std::io::stdout().is_terminal();

    let source = std::fs::read_to_string("programs/addition.tvm").expect("programs/addition.tvm");

    let model = ProgramCompiler
        .compile_source(&source, TransformerVmConfig::default())
        .expect("compile");

    let mut runtime = ExecutionRuntime::new(model, 64);

    if headless {
        let result = runtime.run().expect("run");
        println!("program: programs/addition.tvm");
        println!("steps: {}", result.steps);
        println!("halted: {}", result.halted);
        println!("acc: {} (expected: 8)", result.final_state.acc);
        println!("memory: {:?}", result.final_state.memory);
        println!("throughput_steps_per_sec: {:.2}", result.tokens_per_sec);
    } else {
        let path = std::path::Path::new("programs/addition.tvm");
        run_execution_tui(path, &mut runtime, Duration::from_millis(tick_ms)).expect("tui");

        let state = runtime.state();
        println!("\nFinal state:");
        println!("  acc: {} (expected: 8)", state.acc);
        println!("  halted: {}", state.halted);
        println!("  steps: {}", runtime.step_count());
    }
}
