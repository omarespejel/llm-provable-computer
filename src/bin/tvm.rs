use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::str::FromStr;
use std::time::Duration;
#[cfg(feature = "onnx-export")]
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(feature = "burn-model")]
use burn::backend::NdArray;
use clap::{Parser, Subcommand};
#[cfg(any(feature = "burn-model", feature = "onnx-export"))]
use llm_provable_computer::verify_engines;
#[cfg(feature = "onnx-export")]
use llm_provable_computer::{export_program_onnx, OnnxExecutionRuntime};
use llm_provable_computer::{
    load_execution_stark_proof, prove_execution_stark, run_execution_tui,
    save_execution_stark_proof, verify_execution_stark, verify_model_against_native,
    Attention2DMode, ExecutionResult, ExecutionRuntime, ExecutionTraceEntry, MachineState,
    NativeInterpreter, ProgramCompiler, TransformerVm, TransformerVmConfig, VmError,
};
#[cfg(feature = "burn-model")]
use llm_provable_computer::{BurnExecutionRuntime, BurnTransformerVm};

#[cfg(feature = "burn-model")]
type CliBurnBackend = NdArray<f64>;

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
            default_value = "transformer",
            value_parser = parse_execution_engine
        )]
        engine: CliExecutionEngine,
        #[arg(long)]
        verify_native: bool,
        #[arg(long)]
        verify_burn: bool,
        #[arg(long)]
        verify_onnx: bool,
        #[arg(long, conflicts_with_all = ["verify_native", "verify_burn", "verify_onnx"])]
        verify_all: bool,
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
    ExportOnnx {
        program: PathBuf,
        #[arg(short = 'o', long = "output-dir")]
        output_dir: PathBuf,
        #[arg(long, default_value_t = 1)]
        layers: usize,
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
    },
    ProveStark {
        program: PathBuf,
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
        #[arg(long, default_value_t = 512)]
        max_steps: usize,
        #[arg(long, default_value_t = 1)]
        layers: usize,
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
    },
    VerifyStark {
        proof: PathBuf,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CliExecutionEngine {
    Native,
    Transformer,
    Burn,
    Onnx,
}

impl std::fmt::Display for CliExecutionEngine {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Native => f.write_str("native"),
            Self::Transformer => f.write_str("transformer"),
            Self::Burn => f.write_str("burn"),
            Self::Onnx => f.write_str("onnx"),
        }
    }
}

#[derive(Debug, Clone)]
struct EngineRunOutput {
    result: ExecutionResult,
    trace: Vec<MachineState>,
    events: Vec<ExecutionTraceEntry>,
}

#[cfg(feature = "onnx-export")]
struct ScopedTempDir {
    path: PathBuf,
}

#[cfg(feature = "onnx-export")]
impl ScopedTempDir {
    fn new(prefix: &str) -> llm_provable_computer::Result<Self> {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|err| VmError::InvalidConfig(format!("system clock error: {err}")))?
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "llm-provable-computer-{prefix}-{}-{suffix}",
            std::process::id()
        ));
        fs::create_dir_all(&path)?;
        Ok(Self { path })
    }

    fn path(&self) -> &Path {
        &self.path
    }
}

#[cfg(feature = "onnx-export")]
impl Drop for ScopedTempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.path);
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}

fn run() -> llm_provable_computer::Result<()> {
    let cli = Cli::parse_from(normalize_args(std::env::args_os()));
    match cli.command {
        Command::Run {
            program,
            max_steps,
            trace,
            layers,
            engine,
            verify_native,
            verify_burn,
            verify_onnx,
            verify_all,
            attention_mode,
        } => run_program_command(
            &program,
            max_steps,
            trace,
            layers,
            engine,
            verify_native,
            verify_burn,
            verify_onnx,
            verify_all,
            attention_mode,
        )?,
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
        Command::ExportOnnx {
            program,
            output_dir,
            layers,
            attention_mode,
        } => export_onnx_command(&program, &output_dir, layers, attention_mode)?,
        Command::ProveStark {
            program,
            output,
            max_steps,
            layers,
            attention_mode,
        } => prove_stark_command(&program, &output, max_steps, layers, attention_mode)?,
        Command::VerifyStark { proof } => verify_stark_command(&proof)?,
    }

    Ok(())
}

fn run_program_command(
    program: &Path,
    max_steps: usize,
    trace: bool,
    layers: usize,
    engine: CliExecutionEngine,
    verify_native: bool,
    verify_burn: bool,
    verify_onnx: bool,
    verify_all: bool,
    attention_mode: Attention2DMode,
) -> llm_provable_computer::Result<()> {
    let model = compile_model(program, layers, attention_mode.clone())?;
    let executed = execute_engine(&model, engine, max_steps)?;

    print_execution_summary(program, engine, &model, &executed.result);

    if verify_native {
        let comparison = verify_model_against_native(model.clone(), max_steps)?;
        println!("verified_against_native: true");
        println!("verified_steps: {}", comparison.checked_steps);
        println!(
            "native_elapsed_ms: {:.3}",
            comparison.native.elapsed.as_secs_f64() * 1000.0
        );
        println!(
            "native_throughput_steps_per_sec: {:.2}",
            comparison.native.tokens_per_sec
        );
    }

    if verify_burn {
        let verification = verify_burn_engines(&model, max_steps)?;
        print_verification_summary(
            "verified_against_burn",
            "verified_burn",
            &verification.checked_steps.to_string(),
            &verification.engines,
        );
    }

    if verify_onnx {
        let verification = verify_onnx_engines(&model, max_steps)?;
        print_verification_summary(
            "verified_against_onnx",
            "verified_onnx",
            &verification.checked_steps.to_string(),
            &verification.engines,
        );
    }

    if verify_all {
        let verification = verify_all_engines(&model, max_steps)?;
        print_verification_summary(
            "verified_all",
            "verified_all",
            &verification.checked_steps.to_string(),
            &verification.engines,
        );
    }

    if trace {
        print_trace(&executed.trace, &executed.events);
    }

    Ok(())
}

fn export_onnx_command(
    program: &Path,
    output_dir: &Path,
    layers: usize,
    attention_mode: Attention2DMode,
) -> llm_provable_computer::Result<()> {
    let model = compile_model(program, layers, attention_mode)?;
    export_onnx_command_impl(program, output_dir, &model)
}

fn prove_stark_command(
    program: &Path,
    output: &Path,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
) -> llm_provable_computer::Result<()> {
    let model = compile_model(program, layers, attention_mode)?;
    let proof = prove_execution_stark(&model, max_steps)?;
    save_execution_stark_proof(&proof, output)?;

    println!("program: {}", program.display());
    println!("proof: {}", output.display());
    println!("steps: {}", proof.claim.steps);
    println!("halted: {}", proof.claim.final_state.halted);
    println!("pc: {}", proof.claim.final_state.pc);
    println!("sp: {}", proof.claim.final_state.sp);
    println!("acc: {}", proof.claim.final_state.acc);
    println!("zero_flag: {}", proof.claim.final_state.zero_flag);
    println!("carry_flag: {}", proof.claim.final_state.carry_flag);
    println!("memory: {:?}", proof.claim.final_state.memory);
    println!("attention_mode: {}", proof.claim.attention_mode);
    println!("proof_bytes: {}", proof.proof.len());

    Ok(())
}

fn verify_stark_command(proof_path: &Path) -> llm_provable_computer::Result<()> {
    let proof = load_execution_stark_proof(proof_path)?;
    if !verify_execution_stark(&proof)? {
        return Err(VmError::InvalidConfig(format!(
            "stark proof verification failed for {}",
            proof_path.display()
        )));
    }

    println!("proof: {}", proof_path.display());
    println!("verified_stark: true");
    println!("steps: {}", proof.claim.steps);
    println!("halted: {}", proof.claim.final_state.halted);
    println!("pc: {}", proof.claim.final_state.pc);
    println!("sp: {}", proof.claim.final_state.sp);
    println!("acc: {}", proof.claim.final_state.acc);
    println!("zero_flag: {}", proof.claim.final_state.zero_flag);
    println!("carry_flag: {}", proof.claim.final_state.carry_flag);
    println!("memory: {:?}", proof.claim.final_state.memory);
    println!("attention_mode: {}", proof.claim.attention_mode);
    println!("instructions: {}", proof.claim.program.instructions().len());
    println!("proof_bytes: {}", proof.proof.len());

    Ok(())
}

fn compile_model(
    program: &Path,
    layers: usize,
    attention_mode: Attention2DMode,
) -> llm_provable_computer::Result<TransformerVm> {
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
    ProgramCompiler.compile_source(&source, config)
}

fn load_runtime(
    program: &Path,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
) -> llm_provable_computer::Result<ExecutionRuntime> {
    Ok(ExecutionRuntime::new(
        compile_model(program, layers, attention_mode)?,
        max_steps,
    ))
}

fn execute_engine(
    model: &TransformerVm,
    engine: CliExecutionEngine,
    max_steps: usize,
) -> llm_provable_computer::Result<EngineRunOutput> {
    match engine {
        CliExecutionEngine::Transformer => {
            let mut runtime = ExecutionRuntime::new(model.clone(), max_steps);
            let result = runtime.run()?;
            Ok(EngineRunOutput {
                result,
                trace: runtime.trace().to_vec(),
                events: runtime.events().to_vec(),
            })
        }
        CliExecutionEngine::Native => {
            let mut runtime = NativeInterpreter::new(
                model.program().clone(),
                model.config().attention_mode.clone(),
                max_steps,
            );
            let result = runtime.run()?;
            Ok(EngineRunOutput {
                result,
                trace: runtime.trace().to_vec(),
                events: runtime.events().to_vec(),
            })
        }
        CliExecutionEngine::Burn => execute_burn_engine(model, max_steps),
        CliExecutionEngine::Onnx => execute_onnx_engine(model, max_steps),
    }
}

#[cfg(feature = "burn-model")]
fn execute_burn_engine(
    model: &TransformerVm,
    max_steps: usize,
) -> llm_provable_computer::Result<EngineRunOutput> {
    let device = Default::default();
    let burn_model = BurnTransformerVm::<CliBurnBackend>::from_compiled(model, &device)?;
    let mut runtime = BurnExecutionRuntime::new(burn_model, device, max_steps);
    let result = runtime.run()?;
    Ok(EngineRunOutput {
        result,
        trace: runtime.trace().to_vec(),
        events: runtime.events().to_vec(),
    })
}

#[cfg(not(feature = "burn-model"))]
fn execute_burn_engine(
    _model: &TransformerVm,
    _max_steps: usize,
) -> llm_provable_computer::Result<EngineRunOutput> {
    Err(feature_required_error("engine `burn`", &["burn-model"]))
}

#[cfg(feature = "onnx-export")]
fn execute_onnx_engine(
    model: &TransformerVm,
    max_steps: usize,
) -> llm_provable_computer::Result<EngineRunOutput> {
    let export_dir = ScopedTempDir::new("run-onnx")?;
    export_program_onnx(model, export_dir.path())?;
    let mut runtime = OnnxExecutionRuntime::from_export_dir(export_dir.path(), max_steps)?;
    let result = runtime.run()?;
    Ok(EngineRunOutput {
        result,
        trace: runtime.trace().to_vec(),
        events: runtime.events().to_vec(),
    })
}

#[cfg(not(feature = "onnx-export"))]
fn execute_onnx_engine(
    _model: &TransformerVm,
    _max_steps: usize,
) -> llm_provable_computer::Result<EngineRunOutput> {
    Err(feature_required_error("engine `onnx`", &["onnx-export"]))
}

fn verify_burn_engines(
    model: &TransformerVm,
    max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    verify_burn_engines_impl(model, max_steps)
}

#[cfg(feature = "burn-model")]
fn verify_burn_engines_impl(
    model: &TransformerVm,
    max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    let device = Default::default();
    let burn_model = BurnTransformerVm::<CliBurnBackend>::from_compiled(model, &device)?;
    let mut transformer = ExecutionRuntime::new(model.clone(), max_steps);
    let mut native = NativeInterpreter::new(
        model.program().clone(),
        model.config().attention_mode.clone(),
        max_steps,
    );
    let mut burn = BurnExecutionRuntime::new(burn_model, device, max_steps);
    verify_engines(&mut [&mut transformer, &mut native, &mut burn])
}

#[cfg(not(feature = "burn-model"))]
fn verify_burn_engines_impl(
    _model: &TransformerVm,
    _max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    Err(feature_required_error("`--verify-burn`", &["burn-model"]))
}

fn verify_onnx_engines(
    model: &TransformerVm,
    max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    verify_onnx_engines_impl(model, max_steps)
}

#[cfg(feature = "onnx-export")]
fn verify_onnx_engines_impl(
    model: &TransformerVm,
    max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    let export_dir = ScopedTempDir::new("verify-onnx")?;
    export_program_onnx(model, export_dir.path())?;
    let mut transformer = ExecutionRuntime::new(model.clone(), max_steps);
    let mut native = NativeInterpreter::new(
        model.program().clone(),
        model.config().attention_mode.clone(),
        max_steps,
    );
    let mut onnx = OnnxExecutionRuntime::from_export_dir(export_dir.path(), max_steps)?;
    verify_engines(&mut [&mut transformer, &mut native, &mut onnx])
}

#[cfg(not(feature = "onnx-export"))]
fn verify_onnx_engines_impl(
    _model: &TransformerVm,
    _max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    Err(feature_required_error("`--verify-onnx`", &["onnx-export"]))
}

fn verify_all_engines(
    model: &TransformerVm,
    max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    verify_all_engines_impl(model, max_steps)
}

#[cfg(all(feature = "burn-model", feature = "onnx-export"))]
fn verify_all_engines_impl(
    model: &TransformerVm,
    max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    let device = Default::default();
    let export_dir = ScopedTempDir::new("verify-all")?;
    export_program_onnx(model, export_dir.path())?;
    let burn_model = BurnTransformerVm::<CliBurnBackend>::from_compiled(model, &device)?;

    let mut transformer = ExecutionRuntime::new(model.clone(), max_steps);
    let mut native = NativeInterpreter::new(
        model.program().clone(),
        model.config().attention_mode.clone(),
        max_steps,
    );
    let mut burn = BurnExecutionRuntime::new(burn_model, device, max_steps);
    let mut onnx = OnnxExecutionRuntime::from_export_dir(export_dir.path(), max_steps)?;
    verify_engines(&mut [&mut transformer, &mut native, &mut burn, &mut onnx])
}

#[cfg(not(all(feature = "burn-model", feature = "onnx-export")))]
fn verify_all_engines_impl(
    _model: &TransformerVm,
    _max_steps: usize,
) -> llm_provable_computer::Result<llm_provable_computer::VerificationResult> {
    Err(feature_required_error(
        "`--verify-all`",
        &["burn-model", "onnx-export"],
    ))
}

#[cfg(feature = "onnx-export")]
fn export_onnx_command_impl(
    program: &Path,
    output_dir: &Path,
    model: &TransformerVm,
) -> llm_provable_computer::Result<()> {
    let metadata = export_program_onnx(model, output_dir)?;

    println!("program: {}", program.display());
    println!("output_dir: {}", output_dir.display());
    println!("instructions: {}", metadata.instructions.len());
    println!("layers: {}", metadata.config.num_layers);
    println!("attention_mode: {}", metadata.config.attention_mode);
    println!("onnx_ir_version: {}", metadata.ir_version);
    println!("onnx_opset_version: {}", metadata.opset_version);
    println!("metadata: {}", output_dir.join("metadata.json").display());

    Ok(())
}

#[cfg(not(feature = "onnx-export"))]
fn export_onnx_command_impl(
    _program: &Path,
    _output_dir: &Path,
    _model: &TransformerVm,
) -> llm_provable_computer::Result<()> {
    Err(feature_required_error("`export-onnx`", &["onnx-export"]))
}

fn print_execution_summary(
    program: &Path,
    engine: CliExecutionEngine,
    model: &TransformerVm,
    result: &ExecutionResult,
) {
    println!("program: {}", program.display());
    println!("engine: {engine}");
    println!("steps: {}", result.steps);
    println!("halted: {}", result.halted);
    println!("pc: {}", result.final_state.pc);
    println!("sp: {}", result.final_state.sp);
    println!("acc: {}", result.final_state.acc);
    println!("zero_flag: {}", result.final_state.zero_flag);
    println!("carry_flag: {}", result.final_state.carry_flag);
    println!("memory: {:?}", result.final_state.memory);
    println!("layers: {}", model.config().num_layers);
    println!("attention_mode: {}", model.config().attention_mode);
    println!("elapsed_ms: {:.3}", result.elapsed.as_secs_f64() * 1000.0);
    println!("throughput_steps_per_sec: {:.2}", result.tokens_per_sec);
}

fn print_verification_summary(
    status_key: &str,
    prefix: &str,
    checked_steps: &str,
    engines: &[llm_provable_computer::VerifiedEngine],
) {
    println!("{status_key}: true");
    println!("{prefix}_steps: {checked_steps}");
    println!(
        "{prefix}_engines: {}",
        engines
            .iter()
            .map(|engine| normalize_engine_name(&engine.name))
            .collect::<Vec<_>>()
            .join(",")
    );
}

fn print_trace(trace: &[MachineState], events: &[ExecutionTraceEntry]) {
    if let Some(initial) = trace.first() {
        println!(
            "trace[000] init pc={} sp={} acc={} zero={} carry={} halted={} memory={:?}",
            initial.pc,
            initial.sp,
            initial.acc,
            initial.zero_flag,
            initial.carry_flag,
            initial.halted,
            initial.memory
        );
    }

    for event in events {
        println!(
            "trace[{step:03}] layer={layer} instr=\"{instr}\" pc={pc} sp={sp} acc={acc} zero={zero} carry={carry} halted={halted} memory={memory:?}",
            step = event.step,
            layer = event.layer_idx.unwrap_or(0),
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

fn normalize_args<I>(args: I) -> Vec<OsString>
where
    I: IntoIterator<Item = OsString>,
{
    let mut args = args.into_iter().collect::<Vec<_>>();
    let should_insert_run = args
        .get(1)
        .and_then(|arg| arg.to_str())
        .map(needs_run_subcommand)
        .unwrap_or(false);

    if should_insert_run {
        args.insert(1, OsString::from("run"));
    }

    args
}

fn needs_run_subcommand(first_arg: &str) -> bool {
    !first_arg.starts_with('-')
        && !matches!(
            first_arg,
            "run" | "tui" | "export-onnx" | "prove-stark" | "verify-stark" | "help"
        )
}

fn parse_attention_mode(input: &str) -> Result<Attention2DMode, String> {
    Attention2DMode::from_str(input)
}

fn parse_execution_engine(input: &str) -> Result<CliExecutionEngine, String> {
    let normalized = input.trim().to_ascii_lowercase();
    match normalized.as_str() {
        "native" => Ok(CliExecutionEngine::Native),
        "transformer" => Ok(CliExecutionEngine::Transformer),
        "burn" => Ok(CliExecutionEngine::Burn),
        "onnx" | "onnx-tract" | "onnx/tract" => Ok(CliExecutionEngine::Onnx),
        _ => Err(format!(
            "unknown execution engine `{input}`; expected native, transformer, burn, or onnx"
        )),
    }
}

fn normalize_engine_name(name: &str) -> String {
    match name {
        "onnx/tract" => "onnx".to_string(),
        other => other.to_string(),
    }
}

#[cfg(not(all(feature = "burn-model", feature = "onnx-export")))]
fn feature_required_error(subject: &str, features: &[&str]) -> VmError {
    VmError::InvalidConfig(format!(
        "{subject} requires {}",
        required_features_message(features)
    ))
}

#[cfg(not(all(feature = "burn-model", feature = "onnx-export")))]
fn required_features_message(features: &[&str]) -> String {
    if features.len() == 1 {
        format!("the `{}` feature", features[0])
    } else {
        let joined = features
            .iter()
            .map(|feature| format!("`{feature}`"))
            .collect::<Vec<_>>()
            .join(" and ");
        format!("the {joined} features")
    }
}
