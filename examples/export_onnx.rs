//! Export a compiled program to ONNX models plus metadata.json.
//!
//! Usage:
//!   cargo run --features onnx-export --example export_onnx
//!   cargo run --features onnx-export --example export_onnx -- programs/addition.tvm compiled/addition

#[cfg(not(feature = "onnx-export"))]
fn main() {
    eprintln!("This example requires the `onnx-export` feature.");
    std::process::exit(1);
}

#[cfg(feature = "onnx-export")]
fn main() {
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};

    use llm_provable_computer::{export_program_onnx, ProgramCompiler, TransformerVmConfig};

    fn unique_temp_dir(prefix: &str) -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        std::env::temp_dir().join(format!("llm-provable-computer-{prefix}-{suffix}"))
    }

    let mut args = std::env::args().skip(1);
    let program = args
        .next()
        .unwrap_or_else(|| "programs/fibonacci.tvm".to_string());
    let output_dir = args
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| unique_temp_dir("export-onnx-example"));

    let source = std::fs::read_to_string(&program).expect("read source program");
    let model = ProgramCompiler
        .compile_source(&source, TransformerVmConfig::default())
        .expect("compile program");
    let metadata = export_program_onnx(&model, Path::new(&output_dir)).expect("export ONNX");

    println!("program: {program}");
    println!("output_dir: {}", output_dir.display());
    println!("instructions: {}", metadata.instructions.len());
    println!("metadata: {}", output_dir.join("metadata.json").display());
}
