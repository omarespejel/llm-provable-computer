#![cfg(feature = "onnx-export")]

use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Deserialize;
use transformer_vm_rs::{
    export_program_onnx, MachineState, NativeInterpreter, ProgramCompiler, TransformerVm,
    TransformerVmConfig,
};

#[derive(Debug, Deserialize)]
struct PythonValidationReport {
    steps: usize,
    halted: bool,
    final_state: MachineState,
    trace: Vec<MachineState>,
}

fn compile_model(source: &str, config: TransformerVmConfig) -> TransformerVm {
    ProgramCompiler
        .compile_source(source, config)
        .expect("compile model")
}

fn unique_temp_dir(name: &str) -> PathBuf {
    let suffix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("transformer-vm-rs-{name}-{suffix}"));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    dir
}

fn python_command() -> String {
    std::env::var("TVM_PYTHON").unwrap_or_else(|_| "python3".to_string())
}

fn python_validation_available() -> bool {
    Command::new(python_command())
        .arg("-B")
        .arg("-c")
        .arg("import numpy, onnxruntime")
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .output()
        .map(|output| output.status.success())
        .unwrap_or(false)
}

fn run_python_validation(
    export_dir: &Path,
    program_name: &str,
    expected_acc: i16,
    max_steps: usize,
) -> PythonValidationReport {
    let script = Path::new(env!("CARGO_MANIFEST_DIR")).join("scripts/validate_onnx.py");
    let output = Command::new(python_command())
        .arg("-B")
        .arg(script)
        .arg(export_dir)
        .arg("--json")
        .arg("--program-name")
        .arg(program_name)
        .arg("--expected-acc")
        .arg(expected_acc.to_string())
        .arg("--expected-halted")
        .arg("true")
        .arg("--max-steps")
        .arg(max_steps.to_string())
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .output()
        .expect("run python validator");

    if !output.status.success() {
        panic!(
            "python validator failed with status {:?}\nstdout:\n{}\nstderr:\n{}",
            output.status.code(),
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
    }

    serde_json::from_slice(&output.stdout).expect("parse python validator json")
}

#[test]
fn python_validator_matches_native_trace_for_shipped_programs() {
    if !python_validation_available() {
        eprintln!("skipping python validation test: numpy and onnxruntime are not installed");
        return;
    }

    for (path, expected_acc, max_steps) in [
        ("programs/addition.tvm", 8i16, 64usize),
        ("programs/counter.tvm", 5i16, 256usize),
        ("programs/fibonacci.tvm", 21i16, 512usize),
        ("programs/multiply.tvm", 42i16, 256usize),
        ("programs/subroutine_addition.tvm", 42i16, 128usize),
    ] {
        let source = std::fs::read_to_string(path).expect("fixture");
        let model = compile_model(&source, TransformerVmConfig::default());
        let export_dir = unique_temp_dir("python-validation");
        export_program_onnx(&model, &export_dir).expect("export program");

        let program_name = Path::new(path)
            .file_stem()
            .and_then(|stem| stem.to_str())
            .expect("program stem");
        let mut native = NativeInterpreter::new(
            model.program().clone(),
            model.config().attention_mode.clone(),
            max_steps,
        );
        let native_result = native.run().expect("run native interpreter");
        let python_report =
            run_python_validation(&export_dir, program_name, expected_acc, max_steps);

        assert_eq!(
            python_report.steps, native_result.steps,
            "steps mismatch for {path}"
        );
        assert_eq!(
            python_report.halted, native_result.halted,
            "halted mismatch for {path}"
        );
        assert_eq!(
            python_report.final_state, native_result.final_state,
            "final state mismatch for {path}"
        );
        assert_eq!(
            python_report.trace,
            native.trace(),
            "trace mismatch for {path}"
        );

        let _ = std::fs::remove_dir_all(export_dir);
    }
}
