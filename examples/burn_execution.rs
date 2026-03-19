//! Execute a compiled program through the Burn runtime.
//!
//! Usage:
//!   cargo run --features burn-model --example burn_execution
//!   cargo run --features burn-model --example burn_execution -- programs/fibonacci.tvm

#[cfg(not(feature = "burn-model"))]
fn main() {
    eprintln!("This example requires the `burn-model` feature.");
    std::process::exit(1);
}

#[cfg(feature = "burn-model")]
fn main() {
    use burn::backend::NdArray;
    use llm_provable_computer::{
        BurnExecutionRuntime, BurnTransformerVm, ProgramCompiler, TransformerVmConfig,
    };

    type ExampleBackend = NdArray<f64>;

    let program = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "programs/addition.tvm".to_string());

    let source = std::fs::read_to_string(&program).expect("read source program");
    let model = ProgramCompiler
        .compile_source(&source, TransformerVmConfig::default())
        .expect("compile program");

    let device = Default::default();
    let burn_model = BurnTransformerVm::<ExampleBackend>::from_compiled(&model, &device)
        .expect("build burn model");
    let mut runtime = BurnExecutionRuntime::new(burn_model, device, 512);
    let result = runtime.run().expect("execute burn runtime");

    println!("program: {program}");
    println!("steps: {}", result.steps);
    println!("halted: {}", result.halted);
    println!("acc: {}", result.final_state.acc);
    println!("memory: {:?}", result.final_state.memory);
}
