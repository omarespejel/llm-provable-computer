//! Visual counter execution through the TUI.
//!
//! Compiles a counter program (count from 0 to 5) into transformer weights
//! and runs it with a live terminal visualization showing machine state,
//! memory contents, execution trace, and throughput.
//!
//! Falls back to headless execution when no terminal is available.
//!
//! Usage:
//!   cargo run --example counter
//!   cargo run --example counter -- --tick-ms 30
//!   cargo run --example counter -- --headless

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
        .unwrap_or(60);

    let headless =
        std::env::args().any(|arg| arg == "--headless") || !std::io::stdout().is_terminal();

    let source = std::fs::read_to_string("programs/counter.tvm").expect("programs/counter.tvm");

    let config = TransformerVmConfig {
        num_layers: 2,
        ..TransformerVmConfig::default()
    };
    let model = ProgramCompiler
        .compile_source(&source, config)
        .expect("compile");

    let mut runtime = ExecutionRuntime::new(model, 512);

    if headless {
        let result = runtime.run().expect("run");
        println!("program: programs/counter.tvm");
        println!("steps: {}", result.steps);
        println!("halted: {}", result.halted);
        println!("acc: {}", result.final_state.acc);
        println!("memory: {:?}", result.final_state.memory);
        println!("throughput_steps_per_sec: {:.2}", result.tokens_per_sec);
    } else {
        let path = std::path::Path::new("programs/counter.tvm");
        run_execution_tui(path, &mut runtime, Duration::from_millis(tick_ms)).expect("tui");

        let state = runtime.state();
        println!("\nFinal state:");
        println!("  acc: {}", state.acc);
        println!("  memory: {:?}", state.memory);
        println!("  steps: {}", runtime.step_count());
    }
}
