use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::str::FromStr;
use std::time::Duration;
#[cfg(feature = "onnx-export")]
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(feature = "onnx-export")]
use blake2::digest::{Update, VariableOutput};
#[cfg(feature = "onnx-export")]
use blake2::Blake2bVar;
#[cfg(feature = "burn-model")]
use burn::backend::NdArray;
use clap::{Parser, Subcommand, ValueEnum};
#[cfg(any(feature = "burn-model", feature = "onnx-export"))]
use llm_provable_computer::verify_engines;
use llm_provable_computer::{
    conjectured_security_bits, load_execution_stark_proof, phase6_prepare_recursion_batch,
    production_v1_stark_options, prove_execution_stark_with_backend_and_options, run_execution_tui,
    save_execution_stark_proof, verify_execution_stark_with_backend_and_policy,
    verify_execution_stark_with_reexecution_and_policy, verify_model_against_native,
    Attention2DMode, ExecutionResult, ExecutionRuntime, ExecutionTraceEntry, MachineState,
    NativeInterpreter, ProgramCompiler, StarkProofBackend, StarkVerificationPolicy, TransformerVm,
    TransformerVmConfig, VanillaStarkExecutionProof, VanillaStarkProofOptions, VmError,
    PRODUCTION_V1_MIN_CONJECTURED_SECURITY_BITS, PRODUCTION_V1_TARGET_MAX_PROVING_SECONDS,
    STWO_RECURSION_BATCH_SCOPE_PHASE6, STWO_RECURSION_BATCH_VERSION_PHASE6,
};
#[cfg(feature = "onnx-export")]
use llm_provable_computer::{export_program_onnx, OnnxExecutionRuntime};
#[cfg(feature = "stwo-backend")]
use llm_provable_computer::{
    load_phase10_shared_binary_step_lookup_proof, load_phase10_shared_normalization_lookup_proof,
    load_phase11_decoding_chain, load_phase12_decoding_chain, load_phase13_decoding_layout_matrix,
    load_phase14_decoding_chain, load_phase15_decoding_segment_bundle,
    load_phase16_decoding_segment_rollup, load_phase17_decoding_rollup_matrix,
    load_phase21_decoding_matrix_accumulator, load_phase22_decoding_lookup_accumulator,
    load_phase23_decoding_cross_step_lookup_accumulator,
    load_phase24_decoding_state_relation_accumulator,
    load_phase25_intervalized_decoding_state_relation,
    load_phase26_folded_intervalized_decoding_state_relation,
    load_phase27_chained_folded_intervalized_decoding_state_relation_with_proof_checks,
    load_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks,
    load_phase29_recursive_compression_input_contract, load_phase3_binary_step_lookup_proof,
    load_phase5_normalization_lookup_proof, phase29_prepare_recursive_compression_input_contract,
    prove_phase10_shared_binary_step_lookup_envelope,
    prove_phase10_shared_normalization_lookup_envelope, prove_phase11_decoding_demo,
    prove_phase12_decoding_demo, prove_phase13_decoding_layout_matrix_demo,
    prove_phase14_decoding_demo, prove_phase15_decoding_demo, prove_phase16_decoding_demo,
    prove_phase17_decoding_rollup_matrix_demo, prove_phase21_decoding_matrix_accumulator_demo,
    prove_phase22_decoding_lookup_accumulator_demo,
    prove_phase23_decoding_cross_step_lookup_accumulator_demo,
    prove_phase24_decoding_state_relation_accumulator_demo,
    prove_phase25_intervalized_decoding_state_relation_demo,
    prove_phase26_folded_intervalized_decoding_state_relation_demo,
    prove_phase27_chained_folded_intervalized_decoding_state_relation_demo,
    prove_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_demo,
    prove_phase3_binary_step_lookup_demo_envelope, prove_phase5_normalization_lookup_demo_envelope,
    save_phase10_shared_binary_step_lookup_proof, save_phase10_shared_normalization_lookup_proof,
    save_phase11_decoding_chain, save_phase12_decoding_chain, save_phase13_decoding_layout_matrix,
    save_phase14_decoding_chain, save_phase15_decoding_segment_bundle,
    save_phase16_decoding_segment_rollup, save_phase17_decoding_rollup_matrix,
    save_phase21_decoding_matrix_accumulator, save_phase22_decoding_lookup_accumulator,
    save_phase23_decoding_cross_step_lookup_accumulator,
    save_phase24_decoding_state_relation_accumulator,
    save_phase25_intervalized_decoding_state_relation,
    save_phase26_folded_intervalized_decoding_state_relation,
    save_phase27_chained_folded_intervalized_decoding_state_relation,
    save_phase28_aggregated_chained_folded_intervalized_decoding_state_relation,
    save_phase3_binary_step_lookup_proof, save_phase5_normalization_lookup_proof,
    stwo_backend_enabled, verify_phase10_shared_binary_step_lookup_envelope,
    verify_phase10_shared_normalization_lookup_envelope,
    verify_phase11_decoding_chain_with_proof_checks,
    verify_phase12_decoding_chain_with_proof_checks,
    verify_phase13_decoding_layout_matrix_with_proof_checks,
    verify_phase14_decoding_chain_with_proof_checks,
    verify_phase15_decoding_segment_bundle_with_proof_checks,
    verify_phase16_decoding_segment_rollup_with_proof_checks,
    verify_phase17_decoding_rollup_matrix_with_proof_checks,
    verify_phase21_decoding_matrix_accumulator_with_proof_checks,
    verify_phase22_decoding_lookup_accumulator_with_proof_checks,
    verify_phase23_decoding_cross_step_lookup_accumulator_with_proof_checks,
    verify_phase24_decoding_state_relation_accumulator_with_proof_checks,
    verify_phase25_intervalized_decoding_state_relation_with_proof_checks,
    verify_phase26_folded_intervalized_decoding_state_relation_with_proof_checks,
    verify_phase29_recursive_compression_input_contract,
    verify_phase3_binary_step_lookup_demo_envelope,
    verify_phase5_normalization_lookup_demo_envelope,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28,
    STWO_BACKEND_VERSION_PHASE12,
    STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE27,
    STWO_DECODING_CHAIN_SCOPE_PHASE11, STWO_DECODING_CHAIN_SCOPE_PHASE12,
    STWO_DECODING_CHAIN_SCOPE_PHASE14, STWO_DECODING_CHAIN_VERSION_PHASE11,
    STWO_DECODING_CHAIN_VERSION_PHASE12, STWO_DECODING_CHAIN_VERSION_PHASE14,
    STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_SCOPE_PHASE23,
    STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23,
    STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13, STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13,
    STWO_DECODING_LOOKUP_ACCUMULATOR_SCOPE_PHASE22,
    STWO_DECODING_LOOKUP_ACCUMULATOR_VERSION_PHASE22,
    STWO_DECODING_MATRIX_ACCUMULATOR_SCOPE_PHASE21,
    STWO_DECODING_MATRIX_ACCUMULATOR_VERSION_PHASE21, STWO_DECODING_ROLLUP_MATRIX_SCOPE_PHASE17,
    STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17, STWO_DECODING_SEGMENT_BUNDLE_SCOPE_PHASE15,
    STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15, STWO_DECODING_SEGMENT_ROLLUP_SCOPE_PHASE16,
    STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16,
    STWO_DECODING_STATE_RELATION_ACCUMULATOR_SCOPE_PHASE24,
    STWO_DECODING_STATE_RELATION_ACCUMULATOR_VERSION_PHASE24,
    STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26,
    STWO_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE25, STWO_LOOKUP_PROOF_VERSION_PHASE3,
    STWO_LOOKUP_SEMANTIC_SCOPE_PHASE3, STWO_LOOKUP_STATEMENT_VERSION_PHASE3,
    STWO_NORMALIZATION_PROOF_VERSION_PHASE5, STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5,
    STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5,
    STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29,
    STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29,
};
#[cfg(feature = "burn-model")]
use llm_provable_computer::{BurnExecutionRuntime, BurnTransformerVm};
#[cfg(feature = "onnx-export")]
use serde::{Deserialize, Serialize};

#[cfg(feature = "burn-model")]
type CliBurnBackend = NdArray<f64>;

#[derive(Debug, Parser)]
#[command(
    name = "tvm",
    about = "Run deterministic llm-provable-computer programs."
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Run a program and print the final machine state.
    Run {
        /// Path to the source `.tvm` program.
        program: PathBuf,
        /// Maximum number of execution steps before stopping.
        #[arg(long, default_value_t = 512)]
        max_steps: usize,
        /// Emit the full step-by-step execution trace.
        #[arg(long)]
        trace: bool,
        /// Number of transformer layers to distribute instructions across.
        #[arg(long, default_value_t = 1)]
        layers: usize,
        /// Execution backend to use for the run.
        #[arg(
            long,
            default_value = "transformer",
            value_parser = parse_execution_engine
        )]
        engine: CliExecutionEngine,
        /// Verify the transformer runtime against the native interpreter.
        #[arg(long)]
        verify_native: bool,
        /// Verify the transformer and native runtimes against Burn.
        #[arg(long)]
        verify_burn: bool,
        /// Verify the transformer and native runtimes against ONNX.
        #[arg(long)]
        verify_onnx: bool,
        /// Verify all available runtimes in lockstep.
        #[arg(long, conflicts_with_all = ["verify_native", "verify_burn", "verify_onnx"])]
        verify_all: bool,
        /// Attention mode to use for memory reads.
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
    },
    /// Run the interactive terminal viewer for a program.
    Tui {
        /// Path to the source `.tvm` program.
        program: PathBuf,
        /// Maximum number of execution steps before stopping.
        #[arg(long, default_value_t = 512)]
        max_steps: usize,
        /// Number of transformer layers to distribute instructions across.
        #[arg(long, default_value_t = 1)]
        layers: usize,
        /// UI refresh interval in milliseconds.
        #[arg(long, default_value_t = 60)]
        tick_ms: u64,
        /// Attention mode to use for memory reads.
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
    },
    /// Export the compiled program as per-instruction ONNX graphs.
    ExportOnnx {
        /// Path to the source `.tvm` program.
        program: PathBuf,
        /// Directory where ONNX models and metadata will be written.
        #[arg(short = 'o', long = "output-dir")]
        output_dir: PathBuf,
        /// Number of transformer layers to distribute instructions across.
        #[arg(long, default_value_t = 1)]
        layers: usize,
        /// Attention mode to use for memory reads.
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
    },
    /// Produce a STARK proof for a supported execution.
    ProveStark {
        /// Path to the source `.tvm` program.
        program: PathBuf,
        /// File where the serialized proof JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
        /// Maximum number of execution steps before stopping.
        #[arg(long, default_value_t = 512)]
        max_steps: usize,
        /// Number of transformer layers to distribute instructions across.
        #[arg(long, default_value_t = 1)]
        layers: usize,
        /// Attention mode to use for memory reads.
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
        /// Named STARK profile (recommended for repeatable proving policy).
        #[arg(long, value_enum, default_value_t = CliStarkProfile::ProductionV1)]
        stark_profile: CliStarkProfile,
        /// STARK blowup factor (must be power of two and >= 4).
        ///
        /// Overrides the selected profile.
        #[arg(long)]
        stark_expansion_factor: Option<usize>,
        /// Number of FRI colinearity checks.
        ///
        /// Overrides the selected profile.
        #[arg(long)]
        stark_num_colinearity_checks: Option<usize>,
        /// Requested STARK security level.
        ///
        /// Overrides the selected profile.
        #[arg(long)]
        stark_security_level: Option<usize>,
        /// Proof backend to use.
        #[arg(long, value_enum, default_value_t = CliProofBackend::Vanilla)]
        backend: CliProofBackend,
    },
    /// Verify a previously generated STARK proof.
    VerifyStark {
        /// Path to the serialized proof JSON file.
        proof: PathBuf,
        /// Verification policy profile.
        #[arg(long, value_enum, default_value_t = CliStarkProfile::ProductionV1)]
        verification_profile: CliStarkProfile,
        /// Re-execute transformer/native runtimes from claim data and check equivalence metadata.
        #[arg(long)]
        reexecute: bool,
        /// Minimum required conjectured security bits.
        #[arg(long, default_value_t = 0)]
        min_conjectured_security: u32,
        /// Apply strict verifier policy (enforces at least 80-bit conjectured security and reexecution).
        #[arg(long)]
        strict: bool,
        /// Optional backend override. When omitted, verification uses the backend encoded in the proof.
        #[arg(long, value_enum)]
        backend: Option<CliProofBackend>,
    },
    /// Produce a serialized S-two normalization lookup demo proof.
    ProveStwoLookupDemo {
        /// File where the serialized proof JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized S-two binary-step lookup demo proof.
    VerifyStwoLookupDemo {
        /// Path to the serialized proof JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized S-two normalization lookup demo proof.
    ProveStwoNormalizationDemo {
        /// File where the serialized proof JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized S-two normalization lookup demo proof.
    VerifyStwoNormalizationDemo {
        /// Path to the serialized proof JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized S-two shared binary-step lookup proof for two canonical rows.
    ProveStwoSharedLookupDemo {
        /// File where the serialized proof JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized S-two shared binary-step lookup proof.
    VerifyStwoSharedLookupDemo {
        /// Path to the serialized proof JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized S-two shared normalization lookup proof for two canonical rows.
    ProveStwoSharedNormalizationDemo {
        /// File where the serialized proof JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized S-two shared normalization lookup proof.
    VerifyStwoSharedNormalizationDemo {
        /// Path to the serialized proof JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized proof-carrying decoding chain over three fixed-shape S-two steps.
    ProveStwoDecodingDemo {
        /// File where the serialized chain JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized proof-carrying decoding chain.
    VerifyStwoDecodingDemo {
        /// Path to the serialized chain JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized proof-carrying decoding chain over a parameterized S-two step family.
    ProveStwoDecodingFamilyDemo {
        /// File where the serialized chain JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized parameterized proof-carrying decoding chain.
    VerifyStwoDecodingFamilyDemo {
        /// Path to the serialized chain JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized layout matrix over several parameterized proof-carrying decoding chains.
    ProveStwoDecodingLayoutMatrixDemo {
        /// File where the serialized matrix JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized layout matrix over parameterized proof-carrying decoding chains.
    VerifyStwoDecodingLayoutMatrixDemo {
        /// Path to the serialized matrix JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized chunked-history decoding chain over a parameterized S-two step family.
    ProveStwoDecodingChunkedHistoryDemo {
        /// File where the serialized chain JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized chunked-history decoding chain.
    VerifyStwoDecodingChunkedHistoryDemo {
        /// Path to the serialized chain JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized segment bundle over chunked-history decoding chains.
    ProveStwoDecodingHistorySegmentsDemo {
        /// File where the serialized bundle JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized segment bundle over chunked-history decoding chains.
    VerifyStwoDecodingHistorySegmentsDemo {
        /// Path to the serialized bundle JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized rollup over segmented chunked-history decoding bundles.
    ProveStwoDecodingHistoryRollupDemo {
        /// File where the serialized rollup JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized rollup over segmented chunked-history decoding bundles.
    VerifyStwoDecodingHistoryRollupDemo {
        /// Path to the serialized rollup JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized matrix over multiple Phase 16 decoding history rollups.
    ProveStwoDecodingHistoryRollupMatrixDemo {
        /// File where the serialized matrix JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized matrix over multiple Phase 16 decoding history rollups.
    VerifyStwoDecodingHistoryRollupMatrixDemo {
        /// Path to the serialized matrix JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized accumulator over multiple Phase 17 decoding history rollup matrices.
    ProveStwoDecodingMatrixAccumulatorDemo {
        /// File where the serialized accumulator JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized accumulator over multiple Phase 17 decoding history rollup matrices.
    VerifyStwoDecodingMatrixAccumulatorDemo {
        /// Path to the serialized accumulator JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized lookup-accumulator over a Phase 21 decoding matrix accumulator.
    ProveStwoDecodingLookupAccumulatorDemo {
        /// File where the serialized lookup-accumulator JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized lookup-accumulator over a Phase 21 decoding matrix accumulator.
    VerifyStwoDecodingLookupAccumulatorDemo {
        /// Path to the serialized lookup-accumulator JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized cross-step lookup accumulator over multiple Phase 22 decoding windows.
    ProveStwoDecodingCrossStepLookupAccumulatorDemo {
        /// File where the serialized cross-step lookup accumulator JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized cross-step lookup accumulator over multiple Phase 22 decoding windows.
    VerifyStwoDecodingCrossStepLookupAccumulatorDemo {
        /// Path to the serialized cross-step lookup accumulator JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized full carried-state relation accumulator over multiple Phase 23 members.
    ProveStwoDecodingStateRelationAccumulatorDemo {
        /// File where the serialized state relation accumulator JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized full carried-state relation accumulator over multiple Phase 23 members.
    VerifyStwoDecodingStateRelationAccumulatorDemo {
        /// Path to the serialized state relation accumulator JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized intervalized carried-state relation artifact over a Phase 24 source relation.
    ProveStwoIntervalizedDecodingStateRelationDemo {
        /// File where the serialized intervalized state relation JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized intervalized carried-state relation artifact over a Phase 24 source relation.
    VerifyStwoIntervalizedDecodingStateRelationDemo {
        /// Path to the serialized intervalized state relation JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized folded intervalized carried-state relation artifact over multiple Phase 25 intervals.
    ProveStwoFoldedIntervalizedDecodingStateRelationDemo {
        /// File where the serialized folded intervalized state relation JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized folded intervalized carried-state relation artifact over multiple Phase 25 intervals.
    VerifyStwoFoldedIntervalizedDecodingStateRelationDemo {
        /// Path to the serialized folded intervalized state relation JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized chained folded intervalized carried-state relation artifact over multiple Phase 26 folds.
    ProveStwoChainedFoldedIntervalizedDecodingStateRelationDemo {
        /// File where the serialized chained folded intervalized state relation JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized chained folded intervalized carried-state relation artifact over multiple Phase 26 folds.
    VerifyStwoChainedFoldedIntervalizedDecodingStateRelationDemo {
        /// Path to the serialized chained folded intervalized state relation JSON file.
        proof: PathBuf,
    },
    /// Produce a serialized proof-carrying aggregate over multiple Phase 27 chained folded artifacts.
    #[cfg(feature = "stwo-backend")]
    ProveStwoAggregatedChainedFoldedIntervalizedDecodingStateRelationDemo {
        /// File where the serialized aggregated chained folded intervalized state relation JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized proof-carrying aggregate over multiple Phase 27 chained folded artifacts.
    #[cfg(feature = "stwo-backend")]
    VerifyStwoAggregatedChainedFoldedIntervalizedDecodingStateRelationDemo {
        /// Path to the serialized aggregated chained folded intervalized state relation JSON file.
        proof: PathBuf,
    },
    /// Derive a Phase 29 recursive-compression input contract from a verified Phase 28 aggregate.
    #[cfg(feature = "stwo-backend")]
    PrepareStwoRecursiveCompressionInputContract {
        /// Path to the serialized Phase 28 aggregate JSON or JSON.gz file.
        #[arg(long = "phase28")]
        phase28: PathBuf,
        /// File where the serialized Phase 29 input contract JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Verify a serialized Phase 29 recursive-compression input contract.
    #[cfg(feature = "stwo-backend")]
    VerifyStwoRecursiveCompressionInputContract {
        /// Path to the serialized Phase 29 input contract JSON or JSON.gz file.
        #[arg(long = "input")]
        input: PathBuf,
    },
    /// Prepare a canonical multi-proof batch manifest for future S-two recursion.
    PrepareStwoRecursionBatch {
        /// Proof JSON paths to include in the batch (repeatable).
        #[arg(long = "proof")]
        proofs: Vec<PathBuf>,
        /// File where the serialized batch manifest JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
    },
    /// Generate a research v2 one-step semantic equivalence artifact (transformer vs ONNX).
    ResearchV2Step {
        /// Path to the source `.tvm` program.
        program: PathBuf,
        /// File where the semantic artifact JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
        /// Maximum number of execution steps before stopping (must be >= 1).
        #[arg(long, default_value_t = 1)]
        max_steps: usize,
        /// Number of transformer layers to distribute instructions across.
        #[arg(long, default_value_t = 1)]
        layers: usize,
        /// Attention mode to use for memory reads.
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
    },
    /// Generate a research v2 prefix-trace semantic equivalence artifact (transformer vs ONNX).
    ResearchV2Trace {
        /// Path to the source `.tvm` program.
        program: PathBuf,
        /// File where the semantic artifact JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
        /// Maximum number of execution steps to check in the prefix.
        #[arg(long, default_value_t = 32)]
        max_steps: usize,
        /// Number of transformer layers to distribute instructions across.
        #[arg(long, default_value_t = 1)]
        layers: usize,
        /// Attention mode to use for memory reads.
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
        /// When set, write artifact and exit success even if a mismatch is found.
        #[arg(long)]
        allow_mismatch: bool,
    },
    /// Generate a research v2 multi-program prefix-trace matrix artifact.
    ResearchV2Matrix {
        /// File where the matrix artifact JSON will be written.
        #[arg(short = 'o', long = "output")]
        output: PathBuf,
        /// Program paths to include in the matrix (repeatable).
        #[arg(long = "program")]
        programs: Vec<PathBuf>,
        /// Include the built-in default suite (addition, counter, fibonacci, multiply,
        /// factorial_recursive, dot_product, matmul_2x2, single_neuron).
        #[arg(long)]
        include_default_suite: bool,
        /// Maximum number of execution steps to check per program.
        #[arg(long, default_value_t = 32)]
        max_steps: usize,
        /// Number of transformer layers to distribute instructions across.
        #[arg(long, default_value_t = 1)]
        layers: usize,
        /// Attention mode to use for memory reads.
        #[arg(
            long,
            default_value = "average-hard",
            value_parser = parse_attention_mode
        )]
        attention_mode: Attention2DMode,
        /// When set, write artifact and exit success even if mismatches are found.
        #[arg(long)]
        allow_mismatch: bool,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CliExecutionEngine {
    Native,
    Transformer,
    Burn,
    Onnx,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
enum CliStarkProfile {
    Default,
    ProductionV1,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
enum CliProofBackend {
    Vanilla,
    Stwo,
}

impl CliProofBackend {
    fn backend(self) -> StarkProofBackend {
        match self {
            Self::Vanilla => StarkProofBackend::Vanilla,
            Self::Stwo => StarkProofBackend::Stwo,
        }
    }
}

impl std::fmt::Display for CliProofBackend {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Vanilla => f.write_str("vanilla"),
            Self::Stwo => f.write_str("stwo"),
        }
    }
}

impl CliStarkProfile {
    fn as_str(self) -> &'static str {
        match self {
            Self::Default => "default",
            Self::ProductionV1 => "production-v1",
        }
    }

    fn proof_options(self) -> VanillaStarkProofOptions {
        match self {
            Self::Default => VanillaStarkProofOptions::default(),
            Self::ProductionV1 => production_v1_stark_options(),
        }
    }

    fn min_conjectured_security_bits(self) -> u32 {
        match self {
            Self::Default => 0,
            Self::ProductionV1 => PRODUCTION_V1_MIN_CONJECTURED_SECURITY_BITS,
        }
    }

    fn target_max_proving_seconds(self) -> Option<u64> {
        match self {
            Self::Default => None,
            Self::ProductionV1 => Some(PRODUCTION_V1_TARGET_MAX_PROVING_SECONDS),
        }
    }

    fn enforces_reexecution(self) -> bool {
        matches!(self, Self::ProductionV1)
    }
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

impl std::fmt::Display for CliStarkProfile {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

#[derive(Debug, Clone)]
struct EngineRunOutput {
    result: ExecutionResult,
    trace: Vec<MachineState>,
    events: Vec<ExecutionTraceEntry>,
}

#[derive(Debug, Clone)]
struct RunCommandOptions {
    program: PathBuf,
    max_steps: usize,
    trace: bool,
    layers: usize,
    engine: CliExecutionEngine,
    verify_native: bool,
    verify_burn: bool,
    verify_onnx: bool,
    verify_all: bool,
    attention_mode: Attention2DMode,
}

#[cfg(feature = "onnx-export")]
const STATEMENT_V2_STEP_SPEC_PATH: &str = "spec/statement-v2-research.json";
#[cfg(feature = "onnx-export")]
const STATEMENT_V2_TRACE_SPEC_PATH: &str = "spec/statement-v2-trace-research.json";
#[cfg(feature = "onnx-export")]
const STATEMENT_V2_MATRIX_SPEC_PATH: &str = "spec/statement-v2-matrix-research.json";
#[cfg(feature = "onnx-export")]
const FIXED_POINT_SPEC_PATH: &str = "spec/fixed-point-semantics-v2.json";
#[cfg(feature = "onnx-export")]
const ONNX_OP_SUBSET_SPEC_PATH: &str = "spec/onnx-op-subset-v2.json";
#[cfg(feature = "onnx-export")]
const STATEMENT_V2_STEP_ARTIFACT_SCHEMA_PATH: &str =
    "spec/statement-v2-one-step-certificate.schema.json";
#[cfg(feature = "onnx-export")]
const STATEMENT_V2_TRACE_ARTIFACT_SCHEMA_PATH: &str =
    "spec/statement-v2-trace-certificate.schema.json";
#[cfg(feature = "onnx-export")]
const STATEMENT_V2_MATRIX_ARTIFACT_SCHEMA_PATH: &str =
    "spec/statement-v2-matrix-certificate.schema.json";
#[cfg(feature = "onnx-export")]
const RESEARCH_V2_HASH_FUNCTION: &str = "blake2b-256";

#[cfg(feature = "onnx-export")]
#[derive(Debug, Deserialize)]
struct StatementV2ResearchSpec {
    statement_version: String,
    semantic_scope: String,
    fixed_point_profile_ref: String,
    onnx_op_subset_ref: String,
    artifact_schema_ref: String,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Deserialize)]
struct FixedPointSemanticsSpec {
    profile_id: String,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Deserialize)]
struct OnnxOpSubsetSpec {
    version: String,
    operators: Vec<String>,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Clone)]
struct ResearchV2SpecBundle {
    statement_version: String,
    semantic_scope: String,
    fixed_point_profile: String,
    onnx_op_subset_version: String,
    onnx_op_subset_size: usize,
    statement_spec_hash: String,
    fixed_point_spec_hash: String,
    onnx_op_subset_hash: String,
    artifact_schema_hash: String,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Serialize)]
struct ResearchV2OneStepCommitments {
    hash_function: String,
    statement_spec_hash: String,
    fixed_point_spec_hash: String,
    onnx_op_subset_hash: String,
    artifact_schema_hash: String,
    program_hash: String,
    transformer_config_hash: String,
    onnx_metadata_hash: String,
    state_before_hash: String,
    transformer_state_after_hash: String,
    onnx_state_after_hash: String,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Serialize)]
struct ResearchV2OneStepArtifact {
    statement_version: String,
    semantic_scope: String,
    fixed_point_profile: String,
    onnx_op_subset_version: String,
    onnx_op_subset_size: usize,
    program_path: String,
    checked_steps: usize,
    instruction: String,
    layer_idx: Option<usize>,
    matched: bool,
    state_before: MachineState,
    transformer_state_after: MachineState,
    onnx_state_after: MachineState,
    commitments: ResearchV2OneStepCommitments,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Serialize)]
struct ResearchV2TraceCommitments {
    hash_function: String,
    statement_spec_hash: String,
    fixed_point_spec_hash: String,
    onnx_op_subset_hash: String,
    artifact_schema_hash: String,
    program_hash: String,
    transformer_config_hash: String,
    onnx_metadata_hash: String,
    transformer_trace_hash: String,
    onnx_trace_hash: String,
    transformer_final_state_hash: String,
    onnx_final_state_hash: String,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Serialize)]
struct ResearchV2TraceArtifact {
    statement_version: String,
    semantic_scope: String,
    fixed_point_profile: String,
    onnx_op_subset_version: String,
    onnx_op_subset_size: usize,
    program_path: String,
    requested_max_steps: usize,
    checked_steps: usize,
    matched: bool,
    first_mismatch_step: Option<usize>,
    mismatch_reason: Option<String>,
    transformer_final_state: MachineState,
    onnx_final_state: MachineState,
    commitments: ResearchV2TraceCommitments,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Serialize)]
struct ResearchV2MatrixEntry {
    program_path: String,
    checked_steps: usize,
    matched: bool,
    first_mismatch_step: Option<usize>,
    mismatch_reason: Option<String>,
    transformer_final_state: MachineState,
    onnx_final_state: MachineState,
    commitments: ResearchV2TraceCommitments,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Serialize)]
struct ResearchV2MatrixCommitments {
    hash_function: String,
    statement_spec_hash: String,
    fixed_point_spec_hash: String,
    onnx_op_subset_hash: String,
    artifact_schema_hash: String,
    matrix_entries_hash: String,
}

#[cfg(feature = "onnx-export")]
#[derive(Debug, Serialize)]
struct ResearchV2MatrixArtifact {
    statement_version: String,
    semantic_scope: String,
    fixed_point_profile: String,
    onnx_op_subset_version: String,
    onnx_op_subset_size: usize,
    requested_max_steps: usize,
    total_programs: usize,
    matched_programs: usize,
    mismatched_programs: usize,
    entries: Vec<ResearchV2MatrixEntry>,
    commitments: ResearchV2MatrixCommitments,
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
        } => run_program_command(RunCommandOptions {
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
        })?,
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
            stark_profile,
            stark_expansion_factor,
            stark_num_colinearity_checks,
            stark_security_level,
            backend,
        } => {
            let mut options = stark_profile.proof_options();
            if let Some(value) = stark_expansion_factor {
                options.expansion_factor = value;
            }
            if let Some(value) = stark_num_colinearity_checks {
                options.num_colinearity_checks = value;
            }
            if let Some(value) = stark_security_level {
                options.security_level = value;
            }
            prove_stark_command(
                &program,
                &output,
                max_steps,
                layers,
                attention_mode,
                stark_profile,
                backend,
                options,
            )?
        }
        Command::VerifyStark {
            proof,
            verification_profile,
            reexecute,
            min_conjectured_security,
            strict,
            backend,
        } => verify_stark_command(
            &proof,
            verification_profile,
            reexecute,
            min_conjectured_security,
            strict,
            backend,
        )?,
        Command::ProveStwoLookupDemo { output } => prove_stwo_lookup_demo_command(&output)?,
        Command::VerifyStwoLookupDemo { proof } => verify_stwo_lookup_demo_command(&proof)?,
        Command::ProveStwoNormalizationDemo { output } => {
            prove_stwo_normalization_demo_command(&output)?
        }
        Command::VerifyStwoNormalizationDemo { proof } => {
            verify_stwo_normalization_demo_command(&proof)?
        }
        Command::ProveStwoSharedLookupDemo { output } => {
            prove_stwo_shared_lookup_demo_command(&output)?
        }
        Command::VerifyStwoSharedLookupDemo { proof } => {
            verify_stwo_shared_lookup_demo_command(&proof)?
        }
        Command::ProveStwoSharedNormalizationDemo { output } => {
            prove_stwo_shared_normalization_demo_command(&output)?
        }
        Command::VerifyStwoSharedNormalizationDemo { proof } => {
            verify_stwo_shared_normalization_demo_command(&proof)?
        }
        Command::ProveStwoDecodingDemo { output } => prove_stwo_decoding_demo_command(&output)?,
        Command::VerifyStwoDecodingDemo { proof } => verify_stwo_decoding_demo_command(&proof)?,
        Command::ProveStwoDecodingFamilyDemo { output } => {
            prove_stwo_decoding_family_demo_command(&output)?
        }
        Command::VerifyStwoDecodingFamilyDemo { proof } => {
            verify_stwo_decoding_family_demo_command(&proof)?
        }
        Command::ProveStwoDecodingLayoutMatrixDemo { output } => {
            prove_stwo_decoding_layout_matrix_demo_command(&output)?
        }
        Command::VerifyStwoDecodingLayoutMatrixDemo { proof } => {
            verify_stwo_decoding_layout_matrix_demo_command(&proof)?
        }
        Command::ProveStwoDecodingChunkedHistoryDemo { output } => {
            prove_stwo_decoding_chunked_history_demo_command(&output)?
        }
        Command::VerifyStwoDecodingChunkedHistoryDemo { proof } => {
            verify_stwo_decoding_chunked_history_demo_command(&proof)?
        }
        Command::ProveStwoDecodingHistorySegmentsDemo { output } => {
            prove_stwo_decoding_history_segments_demo_command(&output)?
        }
        Command::VerifyStwoDecodingHistorySegmentsDemo { proof } => {
            verify_stwo_decoding_history_segments_demo_command(&proof)?
        }
        Command::ProveStwoDecodingHistoryRollupDemo { output } => {
            prove_stwo_decoding_history_rollup_demo_command(&output)?
        }
        Command::VerifyStwoDecodingHistoryRollupDemo { proof } => {
            verify_stwo_decoding_history_rollup_demo_command(&proof)?
        }
        Command::ProveStwoDecodingHistoryRollupMatrixDemo { output } => {
            prove_stwo_decoding_history_rollup_matrix_demo_command(&output)?
        }
        Command::VerifyStwoDecodingHistoryRollupMatrixDemo { proof } => {
            verify_stwo_decoding_history_rollup_matrix_demo_command(&proof)?
        }
        Command::ProveStwoDecodingMatrixAccumulatorDemo { output } => {
            prove_stwo_decoding_matrix_accumulator_demo_command(&output)?
        }
        Command::VerifyStwoDecodingMatrixAccumulatorDemo { proof } => {
            verify_stwo_decoding_matrix_accumulator_demo_command(&proof)?
        }
        Command::ProveStwoDecodingLookupAccumulatorDemo { output } => {
            prove_stwo_decoding_lookup_accumulator_demo_command(&output)?
        }
        Command::VerifyStwoDecodingLookupAccumulatorDemo { proof } => {
            verify_stwo_decoding_lookup_accumulator_demo_command(&proof)?
        }
        Command::ProveStwoDecodingCrossStepLookupAccumulatorDemo { output } => {
            prove_stwo_decoding_cross_step_lookup_accumulator_demo_command(&output)?
        }
        Command::VerifyStwoDecodingCrossStepLookupAccumulatorDemo { proof } => {
            verify_stwo_decoding_cross_step_lookup_accumulator_demo_command(&proof)?
        }
        Command::ProveStwoDecodingStateRelationAccumulatorDemo { output } => {
            prove_stwo_decoding_state_relation_accumulator_demo_command(&output)?
        }
        Command::VerifyStwoDecodingStateRelationAccumulatorDemo { proof } => {
            verify_stwo_decoding_state_relation_accumulator_demo_command(&proof)?
        }
        Command::ProveStwoIntervalizedDecodingStateRelationDemo { output } => {
            prove_stwo_intervalized_decoding_state_relation_demo_command(&output)?
        }
        Command::VerifyStwoIntervalizedDecodingStateRelationDemo { proof } => {
            verify_stwo_intervalized_decoding_state_relation_demo_command(&proof)?
        }
        Command::ProveStwoFoldedIntervalizedDecodingStateRelationDemo { output } => {
            prove_stwo_folded_intervalized_decoding_state_relation_demo_command(&output)?
        }
        Command::VerifyStwoFoldedIntervalizedDecodingStateRelationDemo { proof } => {
            verify_stwo_folded_intervalized_decoding_state_relation_demo_command(&proof)?
        }
        Command::ProveStwoChainedFoldedIntervalizedDecodingStateRelationDemo { output } => {
            prove_stwo_chained_folded_intervalized_decoding_state_relation_demo_command(&output)?
        }
        Command::VerifyStwoChainedFoldedIntervalizedDecodingStateRelationDemo { proof } => {
            verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_command(&proof)?
        }
        #[cfg(feature = "stwo-backend")]
        Command::ProveStwoAggregatedChainedFoldedIntervalizedDecodingStateRelationDemo {
            output,
        } => {
            prove_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_command(
                &output,
            )?
        }
        #[cfg(feature = "stwo-backend")]
        Command::VerifyStwoAggregatedChainedFoldedIntervalizedDecodingStateRelationDemo {
            proof,
        } => {
            verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_command(
                &proof,
            )?
        }
        #[cfg(feature = "stwo-backend")]
        Command::PrepareStwoRecursiveCompressionInputContract { phase28, output } => {
            prepare_stwo_recursive_compression_input_contract_command(&phase28, &output)?
        }
        #[cfg(feature = "stwo-backend")]
        Command::VerifyStwoRecursiveCompressionInputContract { input } => {
            verify_stwo_recursive_compression_input_contract_command(&input)?
        }
        Command::PrepareStwoRecursionBatch { proofs, output } => {
            prepare_stwo_recursion_batch_command(&proofs, &output)?
        }
        Command::ResearchV2Step {
            program,
            output,
            max_steps,
            layers,
            attention_mode,
        } => research_v2_step_command(&program, &output, max_steps, layers, attention_mode)?,
        Command::ResearchV2Trace {
            program,
            output,
            max_steps,
            layers,
            attention_mode,
            allow_mismatch,
        } => research_v2_trace_command(
            &program,
            &output,
            max_steps,
            layers,
            attention_mode,
            allow_mismatch,
        )?,
        Command::ResearchV2Matrix {
            output,
            programs,
            include_default_suite,
            max_steps,
            layers,
            attention_mode,
            allow_mismatch,
        } => research_v2_matrix_command(
            &output,
            &programs,
            include_default_suite,
            max_steps,
            layers,
            attention_mode,
            allow_mismatch,
        )?,
    }

    Ok(())
}

fn run_program_command(options: RunCommandOptions) -> llm_provable_computer::Result<()> {
    let model = compile_model(
        &options.program,
        options.layers,
        options.attention_mode.clone(),
    )?;
    let executed = execute_engine(&model, options.engine, options.max_steps)?;

    print_execution_summary(&options.program, options.engine, &model, &executed.result);

    if options.verify_native {
        let comparison = verify_model_against_native(model.clone(), options.max_steps)?;
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

    if options.verify_burn {
        let verification = verify_burn_engines(&model, options.max_steps)?;
        print_verification_summary(
            "verified_against_burn",
            "verified_burn",
            &verification.checked_steps.to_string(),
            &verification.engines,
        );
    }

    if options.verify_onnx {
        let verification = verify_onnx_engines(&model, options.max_steps)?;
        print_verification_summary(
            "verified_against_onnx",
            "verified_onnx",
            &verification.checked_steps.to_string(),
            &verification.engines,
        );
    }

    if options.verify_all {
        let verification = verify_all_engines(&model, options.max_steps)?;
        print_verification_summary(
            "verified_all",
            "verified_all",
            &verification.checked_steps.to_string(),
            &verification.engines,
        );
    }

    if options.trace {
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
    stark_profile: CliStarkProfile,
    backend: CliProofBackend,
    stark_options: VanillaStarkProofOptions,
) -> llm_provable_computer::Result<()> {
    let model = compile_model(program, layers, attention_mode)?;
    let profile_options = stark_profile.proof_options();
    let profile_overridden = stark_options != profile_options;
    let proof = prove_execution_stark_with_backend_and_options(
        &model,
        max_steps,
        backend.backend(),
        stark_options,
    )?;
    let equivalence = proof.claim.equivalence.as_ref().ok_or_else(|| {
        VmError::InvalidConfig(
            "prove-stark produced a claim without equivalence metadata".to_string(),
        )
    })?;
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
    println!("proof_backend: {}", proof.proof_backend);
    println!("proof_backend_version: {}", proof.proof_backend_version);
    println!("statement_version: {}", proof.claim.statement_version);
    println!("semantic_scope: {}", proof.claim.semantic_scope);
    print_stwo_normalization_companion(&proof);
    println!(
        "stark_expansion_factor: {}",
        proof.claim.options.expansion_factor
    );
    println!(
        "stark_num_colinearity_checks: {}",
        proof.claim.options.num_colinearity_checks
    );
    println!(
        "stark_security_level: {}",
        proof.claim.options.security_level
    );
    println!(
        "conjectured_security_bits: {}",
        conjectured_security_bits(&proof.claim.options)
    );
    if profile_overridden {
        println!("stark_profile: custom");
        println!("stark_profile_base: {stark_profile}");
    } else {
        println!("stark_profile: {stark_profile}");
        if let Some(target) = stark_profile.target_max_proving_seconds() {
            println!("profile_target_max_proving_seconds: {target}");
        }
        let profile_security_floor = stark_profile.min_conjectured_security_bits();
        if profile_security_floor > 0 {
            println!("profile_min_conjectured_security_bits: {profile_security_floor}");
        }
    }
    println!("equivalence_checked_steps: {}", equivalence.checked_steps);
    println!(
        "equivalence_transformer_fingerprint: {}",
        equivalence.transformer_fingerprint
    );
    println!(
        "equivalence_native_fingerprint: {}",
        equivalence.native_fingerprint
    );
    if let Some(commitments) = &proof.claim.commitments {
        println!("commitment_scheme_version: {}", commitments.scheme_version);
        println!("commitment_hash_function: {}", commitments.hash_function);
        println!("commitment_program_hash: {}", commitments.program_hash);
        println!(
            "commitment_transformer_config_hash: {}",
            commitments.transformer_config_hash
        );
        println!(
            "commitment_deterministic_model_hash: {}",
            commitments.deterministic_model_hash
        );
        println!(
            "commitment_stark_options_hash: {}",
            commitments.stark_options_hash
        );
        println!(
            "commitment_prover_build_info: {}",
            commitments.prover_build_info
        );
        println!(
            "commitment_prover_build_hash: {}",
            commitments.prover_build_hash
        );
    }
    println!("proof_bytes: {}", proof.proof.len());

    Ok(())
}

fn verify_stark_command(
    proof_path: &Path,
    verification_profile: CliStarkProfile,
    reexecute: bool,
    min_conjectured_security: u32,
    strict: bool,
    backend: Option<CliProofBackend>,
) -> llm_provable_computer::Result<()> {
    let proof = load_execution_stark_proof(proof_path)?;
    let policy = StarkVerificationPolicy {
        min_conjectured_security_bits: {
            let mut floor =
                min_conjectured_security.max(verification_profile.min_conjectured_security_bits());
            if strict {
                floor = floor.max(StarkVerificationPolicy::strict().min_conjectured_security_bits);
            }
            floor
        },
    };
    let effective_reexecute = reexecute || strict || verification_profile.enforces_reexecution();
    let backend = backend
        .map(CliProofBackend::backend)
        .unwrap_or(proof.proof_backend);
    let verified = if effective_reexecute {
        if backend != proof.proof_backend {
            return Err(VmError::InvalidConfig(format!(
                "proof backend override `{backend}` does not match encoded proof backend `{}`",
                proof.proof_backend
            )));
        }
        verify_execution_stark_with_reexecution_and_policy(&proof, policy)?
    } else {
        verify_execution_stark_with_backend_and_policy(&proof, backend, policy)?
    };
    if !verified {
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
    println!("proof_backend: {}", proof.proof_backend);
    println!("proof_backend_version: {}", proof.proof_backend_version);
    println!("statement_version: {}", proof.claim.statement_version);
    println!("semantic_scope: {}", proof.claim.semantic_scope);
    print_stwo_normalization_companion(&proof);
    println!(
        "stark_expansion_factor: {}",
        proof.claim.options.expansion_factor
    );
    println!(
        "stark_num_colinearity_checks: {}",
        proof.claim.options.num_colinearity_checks
    );
    println!(
        "stark_security_level: {}",
        proof.claim.options.security_level
    );
    println!(
        "conjectured_security_bits: {}",
        conjectured_security_bits(&proof.claim.options)
    );
    println!(
        "required_conjectured_security_bits: {}",
        policy.min_conjectured_security_bits
    );
    println!("verification_profile: {verification_profile}");
    println!("strict_policy: {}", strict);
    println!("reexecuted_equivalence: {}", effective_reexecute);
    let equivalence = proof.claim.equivalence.as_ref().ok_or_else(|| {
        VmError::InvalidConfig("verified claim is missing equivalence metadata".to_string())
    })?;
    println!("equivalence_checked_steps: {}", equivalence.checked_steps);
    println!(
        "equivalence_transformer_fingerprint: {}",
        equivalence.transformer_fingerprint
    );
    println!(
        "equivalence_native_fingerprint: {}",
        equivalence.native_fingerprint
    );
    if let Some(commitments) = &proof.claim.commitments {
        println!("commitment_scheme_version: {}", commitments.scheme_version);
        println!("commitment_hash_function: {}", commitments.hash_function);
        println!("commitment_program_hash: {}", commitments.program_hash);
        println!(
            "commitment_transformer_config_hash: {}",
            commitments.transformer_config_hash
        );
        println!(
            "commitment_deterministic_model_hash: {}",
            commitments.deterministic_model_hash
        );
        println!(
            "commitment_stark_options_hash: {}",
            commitments.stark_options_hash
        );
        println!(
            "commitment_prover_build_info: {}",
            commitments.prover_build_info
        );
        println!(
            "commitment_prover_build_hash: {}",
            commitments.prover_build_hash
        );
    }
    println!("instructions: {}", proof.claim.program.instructions().len());
    println!("proof_bytes: {}", proof.proof.len());

    Ok(())
}

fn prove_stwo_normalization_demo_command(output: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two normalization demo requires building with `--features stwo-backend`".to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two normalization demo requires building with `--features stwo-backend`".to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let proof = prove_phase5_normalization_lookup_demo_envelope()?;
        save_phase5_normalization_lookup_proof(&proof, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", proof.proof_backend);
        println!("proof_backend_version: {}", proof.proof_backend_version);
        println!("statement_version: {}", proof.statement_version);
        println!("semantic_scope: {}", proof.semantic_scope);
        println!("canonical_table_rows: {}", proof.canonical_table_rows.len());
        println!("proof_bytes: {}", proof.proof.len());

        Ok(())
    }
}

fn require_stwo_backend(context: &str) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        return Err(VmError::UnsupportedProof(format!(
            "{context} requires building with `--features stwo-backend`"
        )));
    }

    #[cfg(feature = "stwo-backend")]
    {
        if !stwo_backend_enabled() {
            return Err(VmError::UnsupportedProof(format!(
                "{context} requires building with `--features stwo-backend`"
            )));
        }
        Ok(())
    }
}

fn prove_stwo_lookup_demo_command(output: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two binary-step lookup demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two binary-step lookup demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let proof = prove_phase3_binary_step_lookup_demo_envelope()?;
        save_phase3_binary_step_lookup_proof(&proof, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", proof.proof_backend);
        println!("proof_backend_version: {}", proof.proof_backend_version);
        println!("statement_version: {}", proof.statement_version);
        println!("semantic_scope: {}", proof.semantic_scope);
        println!("canonical_table_rows: {}", proof.canonical_table_rows.len());
        println!("proof_bytes: {}", proof.proof.len());

        Ok(())
    }
}

fn prove_stwo_shared_lookup_demo_command(output: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two shared binary-step lookup demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two shared binary-step lookup demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let proof = prove_phase10_shared_binary_step_lookup_envelope(&[
            llm_provable_computer::Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
            llm_provable_computer::Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
        ])?;
        save_phase10_shared_binary_step_lookup_proof(&proof, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", proof.proof_backend);
        println!("proof_backend_version: {}", proof.proof_backend_version);
        println!("statement_version: {}", proof.statement_version);
        println!("semantic_scope: {}", proof.semantic_scope);
        println!("canonical_table_rows: {}", proof.canonical_table_rows.len());
        println!("claimed_rows: {}", proof.claimed_rows.len());
        println!("proof_bytes: {}", proof.proof.len());

        Ok(())
    }
}

fn prove_stwo_shared_normalization_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two shared normalization demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two shared normalization demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let proof = prove_phase10_shared_normalization_lookup_envelope(&[(4, 128), (16, 64)])?;
        save_phase10_shared_normalization_lookup_proof(&proof, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", proof.proof_backend);
        println!("proof_backend_version: {}", proof.proof_backend_version);
        println!("statement_version: {}", proof.statement_version);
        println!("semantic_scope: {}", proof.semantic_scope);
        println!("canonical_table_rows: {}", proof.canonical_table_rows.len());
        println!("claimed_rows: {}", proof.claimed_rows.len());
        println!("proof_bytes: {}", proof.proof.len());

        Ok(())
    }
}

fn verify_stwo_lookup_demo_command(proof_path: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two binary-step lookup demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two binary-step lookup demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let proof = load_phase3_binary_step_lookup_proof(proof_path)?;
        let verified = verify_phase3_binary_step_lookup_demo_envelope(&proof)?;
        if !verified {
            return Err(VmError::InvalidConfig(format!(
                "binary-step lookup demo proof verification failed for {}",
                proof_path.display()
            )));
        }

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", proof.proof_backend);
        println!("proof_backend_version: {}", proof.proof_backend_version);
        println!("statement_version: {}", proof.statement_version);
        println!("semantic_scope: {}", proof.semantic_scope);
        println!("canonical_table_rows: {}", proof.canonical_table_rows.len());
        println!("expected_statement_version: {STWO_LOOKUP_STATEMENT_VERSION_PHASE3}");
        println!("expected_semantic_scope: {STWO_LOOKUP_SEMANTIC_SCOPE_PHASE3}");
        println!("expected_proof_backend_version: {STWO_LOOKUP_PROOF_VERSION_PHASE3}");
        println!("proof_bytes: {}", proof.proof.len());

        Ok(())
    }
}

fn verify_stwo_shared_lookup_demo_command(proof_path: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two shared binary-step lookup demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two shared binary-step lookup demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let proof = load_phase10_shared_binary_step_lookup_proof(proof_path)?;
        if !verify_phase10_shared_binary_step_lookup_envelope(&proof)? {
            return Err(VmError::InvalidConfig(format!(
                "S-two shared binary-step lookup proof verification failed for {}",
                proof_path.display()
            )));
        }

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", proof.proof_backend);
        println!("proof_backend_version: {}", proof.proof_backend_version);
        println!("statement_version: {}", proof.statement_version);
        println!("semantic_scope: {}", proof.semantic_scope);
        println!("canonical_table_rows: {}", proof.canonical_table_rows.len());
        println!("claimed_rows: {}", proof.claimed_rows.len());
        println!("proof_bytes: {}", proof.proof.len());

        Ok(())
    }
}

fn verify_stwo_shared_normalization_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two shared normalization demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two shared normalization demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let proof = load_phase10_shared_normalization_lookup_proof(proof_path)?;
        if !verify_phase10_shared_normalization_lookup_envelope(&proof)? {
            return Err(VmError::InvalidConfig(format!(
                "S-two shared normalization proof verification failed for {}",
                proof_path.display()
            )));
        }

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", proof.proof_backend);
        println!("proof_backend_version: {}", proof.proof_backend_version);
        println!("statement_version: {}", proof.statement_version);
        println!("semantic_scope: {}", proof.semantic_scope);
        println!("canonical_table_rows: {}", proof.canonical_table_rows.len());
        println!("claimed_rows: {}", proof.claimed_rows.len());
        println!("proof_bytes: {}", proof.proof.len());

        Ok(())
    }
}

fn prove_stwo_decoding_demo_command(output: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two proof-carrying decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two proof-carrying decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase11_decoding_demo()?;
        save_phase11_decoding_chain(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("chain_version: {}", manifest.chain_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_steps: {}", manifest.total_steps);
        if let Some(first) = manifest.steps.first() {
            println!("start_position: {}", first.from_state.position);
        }
        if let Some(last) = manifest.steps.last() {
            println!("final_position: {}", last.to_state.position);
        }

        Ok(())
    }
}

fn verify_stwo_decoding_demo_command(proof_path: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two proof-carrying decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two proof-carrying decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase11_decoding_chain(proof_path)?;
        verify_phase11_decoding_chain_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("chain_version: {}", manifest.chain_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_steps: {}", manifest.total_steps);
        println!("expected_chain_version: {STWO_DECODING_CHAIN_VERSION_PHASE11}");
        println!("expected_semantic_scope: {STWO_DECODING_CHAIN_SCOPE_PHASE11}");

        Ok(())
    }
}

fn prove_stwo_decoding_family_demo_command(output: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two parameterized proof-carrying decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two parameterized proof-carrying decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase12_decoding_demo()?;
        save_phase12_decoding_chain(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("chain_version: {}", manifest.chain_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_steps: {}", manifest.total_steps);
        println!("rolling_kv_pairs: {}", manifest.layout.rolling_kv_pairs);
        println!("pair_width: {}", manifest.layout.pair_width);
        if let Some(first) = manifest.steps.first() {
            println!("start_position: {}", first.from_state.position);
            println!(
                "start_history_length: {}",
                first.from_state.kv_history_length
            );
        }
        if let Some(last) = manifest.steps.last() {
            println!("final_position: {}", last.to_state.position);
            println!("final_history_length: {}", last.to_state.kv_history_length);
        }

        Ok(())
    }
}

fn verify_stwo_decoding_family_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two parameterized proof-carrying decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two parameterized proof-carrying decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase12_decoding_chain(proof_path)?;
        verify_phase12_decoding_chain_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("chain_version: {}", manifest.chain_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_steps: {}", manifest.total_steps);
        println!("rolling_kv_pairs: {}", manifest.layout.rolling_kv_pairs);
        println!("pair_width: {}", manifest.layout.pair_width);
        if let Some(first) = manifest.steps.first() {
            println!(
                "start_history_length: {}",
                first.from_state.kv_history_length
            );
        }
        if let Some(last) = manifest.steps.last() {
            println!("final_history_length: {}", last.to_state.kv_history_length);
        }
        println!("expected_chain_version: {STWO_DECODING_CHAIN_VERSION_PHASE12}");
        println!("expected_semantic_scope: {STWO_DECODING_CHAIN_SCOPE_PHASE12}");
        println!("expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}");

        Ok(())
    }
}

fn prove_stwo_decoding_layout_matrix_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two decoding layout matrix demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two decoding layout matrix demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase13_decoding_layout_matrix_demo()?;
        save_phase13_decoding_layout_matrix(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("matrix_version: {}", manifest.matrix_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_steps: {}", manifest.total_steps);
        if let Some(first) = manifest.chains.first() {
            println!("first_layout_pairs: {}", first.layout.rolling_kv_pairs);
            println!("first_layout_width: {}", first.layout.pair_width);
        }
        if let Some(last) = manifest.chains.last() {
            println!("last_layout_pairs: {}", last.layout.rolling_kv_pairs);
            println!("last_layout_width: {}", last.layout.pair_width);
        }

        Ok(())
    }
}

fn verify_stwo_decoding_layout_matrix_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two decoding layout matrix demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two decoding layout matrix demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase13_decoding_layout_matrix(proof_path)?;
        verify_phase13_decoding_layout_matrix_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("matrix_version: {}", manifest.matrix_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_steps: {}", manifest.total_steps);
        println!("expected_matrix_version: {STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13}");
        println!("expected_semantic_scope: {STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13}");
        println!("expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}");

        Ok(())
    }
}

fn prove_stwo_decoding_chunked_history_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two chunked-history decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two chunked-history decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase14_decoding_demo()?;
        save_phase14_decoding_chain(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("chain_version: {}", manifest.chain_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_steps: {}", manifest.total_steps);
        println!("history_chunk_pairs: {}", manifest.history_chunk_pairs);
        println!("rolling_kv_pairs: {}", manifest.layout.rolling_kv_pairs);
        println!("pair_width: {}", manifest.layout.pair_width);
        if let Some(first) = manifest.steps.first() {
            println!(
                "start_history_length: {}",
                first.from_state.kv_history_length
            );
            println!(
                "start_sealed_chunks: {}",
                first.from_state.kv_history_sealed_chunks
            );
            println!(
                "start_open_chunk_pairs: {}",
                first.from_state.kv_history_open_chunk_pairs
            );
        }
        if let Some(last) = manifest.steps.last() {
            println!("final_history_length: {}", last.to_state.kv_history_length);
            println!(
                "final_sealed_chunks: {}",
                last.to_state.kv_history_sealed_chunks
            );
            println!(
                "final_open_chunk_pairs: {}",
                last.to_state.kv_history_open_chunk_pairs
            );
        }

        Ok(())
    }
}

fn verify_stwo_decoding_chunked_history_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two chunked-history decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two chunked-history decoding demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase14_decoding_chain(proof_path)?;
        verify_phase14_decoding_chain_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("chain_version: {}", manifest.chain_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_steps: {}", manifest.total_steps);
        println!("history_chunk_pairs: {}", manifest.history_chunk_pairs);
        println!("rolling_kv_pairs: {}", manifest.layout.rolling_kv_pairs);
        println!("pair_width: {}", manifest.layout.pair_width);
        if let Some(first) = manifest.steps.first() {
            println!(
                "start_history_length: {}",
                first.from_state.kv_history_length
            );
            println!(
                "start_sealed_chunks: {}",
                first.from_state.kv_history_sealed_chunks
            );
            println!(
                "start_open_chunk_pairs: {}",
                first.from_state.kv_history_open_chunk_pairs
            );
        }
        if let Some(last) = manifest.steps.last() {
            println!("final_history_length: {}", last.to_state.kv_history_length);
            println!(
                "final_sealed_chunks: {}",
                last.to_state.kv_history_sealed_chunks
            );
            println!(
                "final_open_chunk_pairs: {}",
                last.to_state.kv_history_open_chunk_pairs
            );
        }
        println!("expected_chain_version: {STWO_DECODING_CHAIN_VERSION_PHASE14}");
        println!("expected_semantic_scope: {STWO_DECODING_CHAIN_SCOPE_PHASE14}");
        println!("expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}");

        Ok(())
    }
}

fn prove_stwo_decoding_history_segments_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        return Err(VmError::UnsupportedProof(
            "S-two decoding history-segment demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two decoding history-segment demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase15_decoding_demo()?;
        save_phase15_decoding_segment_bundle(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("bundle_version: {}", manifest.bundle_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("max_segment_steps: {}", manifest.max_segment_steps);
        println!("history_chunk_pairs: {}", manifest.history_chunk_pairs);
        println!("rolling_kv_pairs: {}", manifest.layout.rolling_kv_pairs);
        println!("pair_width: {}", manifest.layout.pair_width);
        if let Some(first) = manifest.segments.first() {
            println!(
                "first_segment_start_step: {}",
                first.global_start_step_index
            );
            println!("first_segment_steps: {}", first.total_steps);
        }
        if let Some(last) = manifest.segments.last() {
            println!("last_segment_start_step: {}", last.global_start_step_index);
            println!("last_segment_steps: {}", last.total_steps);
            println!(
                "final_history_length: {}",
                last.global_to_state.kv_history_length
            );
            println!(
                "final_sealed_chunks: {}",
                last.global_to_state.kv_history_sealed_chunks
            );
            println!(
                "final_open_chunk_pairs: {}",
                last.global_to_state.kv_history_open_chunk_pairs
            );
        }

        Ok(())
    }
}

fn verify_stwo_decoding_history_segments_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two decoding history-segment demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two decoding history-segment demo requires building with `--features stwo-backend`"
                .to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase15_decoding_segment_bundle(proof_path)?;
        verify_phase15_decoding_segment_bundle_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("bundle_version: {}", manifest.bundle_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("max_segment_steps: {}", manifest.max_segment_steps);
        println!("history_chunk_pairs: {}", manifest.history_chunk_pairs);
        println!("rolling_kv_pairs: {}", manifest.layout.rolling_kv_pairs);
        println!("pair_width: {}", manifest.layout.pair_width);
        if let Some(first) = manifest.segments.first() {
            println!(
                "first_segment_start_step: {}",
                first.global_start_step_index
            );
            println!("first_segment_steps: {}", first.total_steps);
        }
        if let Some(last) = manifest.segments.last() {
            println!("last_segment_start_step: {}", last.global_start_step_index);
            println!("last_segment_steps: {}", last.total_steps);
            println!(
                "final_history_length: {}",
                last.global_to_state.kv_history_length
            );
            println!(
                "final_sealed_chunks: {}",
                last.global_to_state.kv_history_sealed_chunks
            );
            println!(
                "final_open_chunk_pairs: {}",
                last.global_to_state.kv_history_open_chunk_pairs
            );
        }
        println!("expected_bundle_version: {STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15}");
        println!("expected_semantic_scope: {STWO_DECODING_SEGMENT_BUNDLE_SCOPE_PHASE15}");
        println!("expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}");

        Ok(())
    }
}

fn prove_stwo_decoding_history_rollup_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding history-rollup demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase16_decoding_demo()?;
        save_phase16_decoding_segment_rollup(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("rollup_version: {}", manifest.rollup_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("max_rollup_segments: {}", manifest.max_rollup_segments);
        println!("history_chunk_pairs: {}", manifest.history_chunk_pairs);
        println!("rolling_kv_pairs: {}", manifest.layout.rolling_kv_pairs);
        println!("pair_width: {}", manifest.layout.pair_width);
        if let Some(first) = manifest.rollups.first() {
            println!("first_rollup_start_step: {}", first.global_start_step_index);
            println!("first_rollup_segments: {}", first.total_segments);
        }
        if let Some(last) = manifest.rollups.last() {
            println!("last_rollup_start_step: {}", last.global_start_step_index);
            println!("last_rollup_segments: {}", last.total_segments);
            println!(
                "final_history_length: {}",
                last.global_to_state.kv_history_length
            );
            println!(
                "final_sealed_chunks: {}",
                last.global_to_state.kv_history_sealed_chunks
            );
            println!(
                "final_open_chunk_pairs: {}",
                last.global_to_state.kv_history_open_chunk_pairs
            );
        }

        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_decoding_history_rollup_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding history-rollup demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase16_decoding_segment_rollup(proof_path)?;
        verify_phase16_decoding_segment_rollup_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("rollup_version: {}", manifest.rollup_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("max_rollup_segments: {}", manifest.max_rollup_segments);
        println!("history_chunk_pairs: {}", manifest.history_chunk_pairs);
        println!("rolling_kv_pairs: {}", manifest.layout.rolling_kv_pairs);
        println!("pair_width: {}", manifest.layout.pair_width);
        println!(
            "expected_rollup_version: {}",
            STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16
        );
        println!(
            "expected_semantic_scope: {}",
            STWO_DECODING_SEGMENT_ROLLUP_SCOPE_PHASE16
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        if let Some(first) = manifest.rollups.first() {
            println!("first_rollup_start_step: {}", first.global_start_step_index);
            println!("first_rollup_segments: {}", first.total_segments);
        }
        if let Some(last) = manifest.rollups.last() {
            println!("last_rollup_start_step: {}", last.global_start_step_index);
            println!("last_rollup_segments: {}", last.total_segments);
            println!(
                "final_history_length: {}",
                last.global_to_state.kv_history_length
            );
            println!(
                "final_sealed_chunks: {}",
                last.global_to_state.kv_history_sealed_chunks
            );
            println!(
                "final_open_chunk_pairs: {}",
                last.global_to_state.kv_history_open_chunk_pairs
            );
        }

        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn prove_stwo_decoding_history_rollup_matrix_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding history-rollup matrix demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase17_decoding_rollup_matrix_demo()?;
        save_phase17_decoding_rollup_matrix(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("matrix_version: {}", manifest.matrix_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        if let Some(first) = manifest.rollups.first() {
            println!("first_layout_rollups: {}", first.total_rollups);
            println!("first_layout_segments: {}", first.total_segments);
        }
        if let Some(last) = manifest.rollups.last() {
            println!("last_layout_rollups: {}", last.total_rollups);
            println!("last_layout_segments: {}", last.total_segments);
            if let Some(last_rollup) = last.rollups.last() {
                println!(
                    "final_history_length: {}",
                    last_rollup.global_to_state.kv_history_length
                );
            }
        }
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_decoding_history_rollup_matrix_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding history-rollup matrix demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase17_decoding_rollup_matrix(proof_path)?;
        verify_phase17_decoding_rollup_matrix_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("matrix_version: {}", manifest.matrix_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!(
            "expected_matrix_version: {}",
            STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17
        );
        println!(
            "expected_semantic_scope: {}",
            STWO_DECODING_ROLLUP_MATRIX_SCOPE_PHASE17
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        if let Some(first) = manifest.rollups.first() {
            println!("first_layout_rollups: {}", first.total_rollups);
            println!("first_layout_segments: {}", first.total_segments);
        }
        if let Some(last) = manifest.rollups.last() {
            println!("last_layout_rollups: {}", last.total_rollups);
            println!("last_layout_segments: {}", last.total_segments);
            if let Some(last_rollup) = last.rollups.last() {
                println!(
                    "final_history_length: {}",
                    last_rollup.global_to_state.kv_history_length
                );
            }
        }
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn prove_stwo_decoding_matrix_accumulator_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding matrix-accumulator demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase21_decoding_matrix_accumulator_demo()?;
        save_phase21_decoding_matrix_accumulator(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("accumulator_version: {}", manifest.accumulator_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        if let Some(first) = manifest.matrices.first() {
            println!("first_matrix_layouts: {}", first.total_layouts);
            println!("first_matrix_rollups: {}", first.total_rollups);
        }
        if let Some(last) = manifest.matrices.last() {
            println!("last_matrix_layouts: {}", last.total_layouts);
            println!("last_matrix_rollups: {}", last.total_rollups);
        }
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_decoding_matrix_accumulator_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding matrix-accumulator demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase21_decoding_matrix_accumulator(proof_path)?;
        verify_phase21_decoding_matrix_accumulator_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("accumulator_version: {}", manifest.accumulator_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!(
            "expected_accumulator_version: {}",
            STWO_DECODING_MATRIX_ACCUMULATOR_VERSION_PHASE21
        );
        println!(
            "expected_semantic_scope: {}",
            STWO_DECODING_MATRIX_ACCUMULATOR_SCOPE_PHASE21
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        if let Some(first) = manifest.matrices.first() {
            println!("first_matrix_layouts: {}", first.total_layouts);
            println!("first_matrix_rollups: {}", first.total_rollups);
        }
        if let Some(last) = manifest.matrices.last() {
            println!("last_matrix_layouts: {}", last.total_layouts);
            println!("last_matrix_rollups: {}", last.total_rollups);
        }
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn prove_stwo_decoding_lookup_accumulator_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding lookup-accumulator demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase22_decoding_lookup_accumulator_demo()?;
        save_phase22_decoding_lookup_accumulator(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("accumulator_version: {}", manifest.accumulator_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_decoding_lookup_accumulator_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding lookup-accumulator demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase22_decoding_lookup_accumulator(proof_path)?;
        verify_phase22_decoding_lookup_accumulator_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("accumulator_version: {}", manifest.accumulator_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        println!(
            "expected_accumulator_version: {}",
            STWO_DECODING_LOOKUP_ACCUMULATOR_VERSION_PHASE22
        );
        println!(
            "expected_semantic_scope: {}",
            STWO_DECODING_LOOKUP_ACCUMULATOR_SCOPE_PHASE22
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn prove_stwo_decoding_cross_step_lookup_accumulator_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding cross-step lookup accumulator demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase23_decoding_cross_step_lookup_accumulator_demo()?;
        save_phase23_decoding_cross_step_lookup_accumulator(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("accumulator_version: {}", manifest.accumulator_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("member_count: {}", manifest.member_count);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_decoding_cross_step_lookup_accumulator_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding cross-step lookup accumulator demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase23_decoding_cross_step_lookup_accumulator(proof_path)?;
        verify_phase23_decoding_cross_step_lookup_accumulator_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("accumulator_version: {}", manifest.accumulator_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("member_count: {}", manifest.member_count);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        println!(
            "expected_accumulator_version: {}",
            STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23
        );
        println!(
            "expected_semantic_scope: {}",
            STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_SCOPE_PHASE23
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn prove_stwo_decoding_state_relation_accumulator_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding state relation accumulator demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase24_decoding_state_relation_accumulator_demo()?;
        save_phase24_decoding_state_relation_accumulator(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("accumulator_version: {}", manifest.accumulator_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("member_count: {}", manifest.member_count);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_decoding_state_relation_accumulator_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two decoding state relation accumulator demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase24_decoding_state_relation_accumulator(proof_path)?;
        verify_phase24_decoding_state_relation_accumulator_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("accumulator_version: {}", manifest.accumulator_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("member_count: {}", manifest.member_count);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        println!(
            "expected_accumulator_version: {}",
            STWO_DECODING_STATE_RELATION_ACCUMULATOR_VERSION_PHASE24
        );
        println!(
            "expected_semantic_scope: {}",
            STWO_DECODING_STATE_RELATION_ACCUMULATOR_SCOPE_PHASE24
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn prove_stwo_intervalized_decoding_state_relation_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two intervalized decoding state relation demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase25_intervalized_decoding_state_relation_demo()?;
        save_phase25_intervalized_decoding_state_relation(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("artifact_version: {}", manifest.artifact_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("member_count: {}", manifest.member_count);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_intervalized_decoding_state_relation_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two intervalized decoding state relation demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase25_intervalized_decoding_state_relation(proof_path)?;
        verify_phase25_intervalized_decoding_state_relation_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("artifact_version: {}", manifest.artifact_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("member_count: {}", manifest.member_count);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        println!(
            "expected_artifact_version: {}",
            STWO_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE25
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn prove_stwo_folded_intervalized_decoding_state_relation_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two folded intervalized decoding state relation demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase26_folded_intervalized_decoding_state_relation_demo()?;
        save_phase26_folded_intervalized_decoding_state_relation(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("artifact_version: {}", manifest.artifact_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("bounded_fold_arity: {}", manifest.bounded_fold_arity);
        println!("member_count: {}", manifest.member_count);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_folded_intervalized_decoding_state_relation_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two folded intervalized decoding state relation demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = load_phase26_folded_intervalized_decoding_state_relation(proof_path)?;
        verify_phase26_folded_intervalized_decoding_state_relation_with_proof_checks(&manifest)?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("artifact_version: {}", manifest.artifact_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("bounded_fold_arity: {}", manifest.bounded_fold_arity);
        println!("member_count: {}", manifest.member_count);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        println!(
            "expected_artifact_version: {}",
            STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn prove_stwo_chained_folded_intervalized_decoding_state_relation_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two chained folded intervalized decoding state relation demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest = prove_phase27_chained_folded_intervalized_decoding_state_relation_demo()?;
        save_phase27_chained_folded_intervalized_decoding_state_relation(&manifest, output)?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("artifact_version: {}", manifest.artifact_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("bounded_chain_arity: {}", manifest.bounded_chain_arity);
        println!("member_count: {}", manifest.member_count);
        println!("total_phase25_members: {}", manifest.total_phase25_members);
        println!("max_nested_fold_arity: {}", manifest.max_nested_fold_arity);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

fn verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two chained folded intervalized decoding state relation demo")?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest =
            load_phase27_chained_folded_intervalized_decoding_state_relation_with_proof_checks(
                proof_path,
            )?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("artifact_version: {}", manifest.artifact_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!("bounded_chain_arity: {}", manifest.bounded_chain_arity);
        println!("member_count: {}", manifest.member_count);
        println!("total_phase25_members: {}", manifest.total_phase25_members);
        println!("max_nested_fold_arity: {}", manifest.max_nested_fold_arity);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        println!(
            "expected_artifact_version: {}",
            STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE27
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

#[cfg(feature = "stwo-backend")]
fn prove_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_command(
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend(
        "S-two aggregated chained folded intervalized decoding state relation demo",
    )?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest =
            prove_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_demo()?;
        save_phase28_aggregated_chained_folded_intervalized_decoding_state_relation(
            &manifest, output,
        )?;

        println!("proof: {}", output.display());
        println!("proof_backend: {}", manifest.proof_backend);
        println!("artifact_version: {}", manifest.artifact_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!(
            "bounded_aggregation_arity: {}",
            manifest.bounded_aggregation_arity
        );
        println!("member_count: {}", manifest.member_count);
        println!("total_phase26_members: {}", manifest.total_phase26_members);
        println!("total_phase25_members: {}", manifest.total_phase25_members);
        println!(
            "max_nested_chain_arity: {}",
            manifest.max_nested_chain_arity
        );
        println!("max_nested_fold_arity: {}", manifest.max_nested_fold_arity);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = output;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

#[cfg(feature = "stwo-backend")]
fn verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_command(
    proof_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend(
        "S-two aggregated chained folded intervalized decoding state relation demo",
    )?;

    #[cfg(feature = "stwo-backend")]
    {
        let manifest =
            load_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks(
                proof_path,
            )?;

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", manifest.proof_backend);
        println!("artifact_version: {}", manifest.artifact_version);
        println!("semantic_scope: {}", manifest.semantic_scope);
        println!("proof_backend_version: {}", manifest.proof_backend_version);
        println!("statement_version: {}", manifest.statement_version);
        println!(
            "bounded_aggregation_arity: {}",
            manifest.bounded_aggregation_arity
        );
        println!("member_count: {}", manifest.member_count);
        println!("total_phase26_members: {}", manifest.total_phase26_members);
        println!("total_phase25_members: {}", manifest.total_phase25_members);
        println!(
            "max_nested_chain_arity: {}",
            manifest.max_nested_chain_arity
        );
        println!("max_nested_fold_arity: {}", manifest.max_nested_fold_arity);
        println!("total_matrices: {}", manifest.total_matrices);
        println!("total_layouts: {}", manifest.total_layouts);
        println!("total_rollups: {}", manifest.total_rollups);
        println!("total_segments: {}", manifest.total_segments);
        println!("total_steps: {}", manifest.total_steps);
        println!("lookup_delta_entries: {}", manifest.lookup_delta_entries);
        println!(
            "max_lookup_frontier_entries: {}",
            manifest.max_lookup_frontier_entries
        );
        println!(
            "expected_artifact_version: {}",
            STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28
        );
        println!(
            "expected_proof_backend_version: {}",
            STWO_BACKEND_VERSION_PHASE12
        );
        Ok(())
    }

    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        unreachable!("require_stwo_backend must fail without `stwo-backend`");
    }
}

#[cfg(feature = "stwo-backend")]
fn prepare_stwo_recursive_compression_input_contract_command(
    phase28_path: &Path,
    output: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two Phase 29 recursive-compression input contract")?;

    let phase28 =
        load_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks(
            phase28_path,
        )?;
    let contract = phase29_prepare_recursive_compression_input_contract(&phase28)?;
    let json = serde_json::to_string_pretty(&contract)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(output, json)?;

    println!("output: {}", output.display());
    println!("phase28: {}", phase28_path.display());
    println!("verified_phase28: true");
    println!("proof_backend: {}", contract.proof_backend);
    println!("contract_version: {}", contract.contract_version);
    println!("semantic_scope: {}", contract.semantic_scope);
    println!(
        "phase28_artifact_version: {}",
        contract.phase28_artifact_version
    );
    println!(
        "phase28_proof_backend_version: {}",
        contract.phase28_proof_backend_version
    );
    println!("statement_version: {}", contract.statement_version);
    println!(
        "required_recursion_posture: {}",
        contract.required_recursion_posture
    );
    println!(
        "recursive_verification_claimed: {}",
        contract.recursive_verification_claimed
    );
    println!(
        "cryptographic_compression_claimed: {}",
        contract.cryptographic_compression_claimed
    );
    println!("phase28_member_count: {}", contract.phase28_member_count);
    println!("total_phase26_members: {}", contract.total_phase26_members);
    println!("total_phase25_members: {}", contract.total_phase25_members);
    println!("total_matrices: {}", contract.total_matrices);
    println!("total_layouts: {}", contract.total_layouts);
    println!("total_rollups: {}", contract.total_rollups);
    println!("total_segments: {}", contract.total_segments);
    println!("total_steps: {}", contract.total_steps);
    println!("lookup_delta_entries: {}", contract.lookup_delta_entries);
    println!(
        "max_lookup_frontier_entries: {}",
        contract.max_lookup_frontier_entries
    );
    println!(
        "input_contract_commitment: {}",
        contract.input_contract_commitment
    );
    println!(
        "expected_contract_version: {}",
        STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29
    );
    println!(
        "expected_semantic_scope: {}",
        STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29
    );

    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn verify_stwo_recursive_compression_input_contract_command(
    input_path: &Path,
) -> llm_provable_computer::Result<()> {
    require_stwo_backend("S-two Phase 29 recursive-compression input contract")?;

    let contract = load_phase29_recursive_compression_input_contract(input_path)?;
    verify_phase29_recursive_compression_input_contract(&contract)?;

    println!("input: {}", input_path.display());
    println!("verified_contract: true");
    println!("proof_backend: {}", contract.proof_backend);
    println!("contract_version: {}", contract.contract_version);
    println!("semantic_scope: {}", contract.semantic_scope);
    println!(
        "phase28_artifact_version: {}",
        contract.phase28_artifact_version
    );
    println!(
        "phase28_proof_backend_version: {}",
        contract.phase28_proof_backend_version
    );
    println!("statement_version: {}", contract.statement_version);
    println!(
        "required_recursion_posture: {}",
        contract.required_recursion_posture
    );
    println!(
        "recursive_verification_claimed: {}",
        contract.recursive_verification_claimed
    );
    println!(
        "cryptographic_compression_claimed: {}",
        contract.cryptographic_compression_claimed
    );
    println!("phase28_member_count: {}", contract.phase28_member_count);
    println!("total_phase26_members: {}", contract.total_phase26_members);
    println!("total_phase25_members: {}", contract.total_phase25_members);
    println!("total_matrices: {}", contract.total_matrices);
    println!("total_layouts: {}", contract.total_layouts);
    println!("total_rollups: {}", contract.total_rollups);
    println!("total_segments: {}", contract.total_segments);
    println!("total_steps: {}", contract.total_steps);
    println!("lookup_delta_entries: {}", contract.lookup_delta_entries);
    println!(
        "max_lookup_frontier_entries: {}",
        contract.max_lookup_frontier_entries
    );
    println!(
        "input_contract_commitment: {}",
        contract.input_contract_commitment
    );
    println!(
        "expected_contract_version: {}",
        STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29
    );
    println!(
        "expected_semantic_scope: {}",
        STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29
    );

    Ok(())
}

fn verify_stwo_normalization_demo_command(proof_path: &Path) -> llm_provable_computer::Result<()> {
    #[cfg(not(feature = "stwo-backend"))]
    {
        let _ = proof_path;
        return Err(VmError::UnsupportedProof(
            "S-two normalization demo requires building with `--features stwo-backend`".to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    if !stwo_backend_enabled() {
        return Err(VmError::UnsupportedProof(
            "S-two normalization demo requires building with `--features stwo-backend`".to_string(),
        ));
    }

    #[cfg(feature = "stwo-backend")]
    {
        let proof = load_phase5_normalization_lookup_proof(proof_path)?;
        let verified = verify_phase5_normalization_lookup_demo_envelope(&proof)?;
        if !verified {
            return Err(VmError::InvalidConfig(format!(
                "normalization demo proof verification failed for {}",
                proof_path.display()
            )));
        }

        println!("proof: {}", proof_path.display());
        println!("verified_stark: true");
        println!("proof_backend: {}", proof.proof_backend);
        println!("proof_backend_version: {}", proof.proof_backend_version);
        println!("statement_version: {}", proof.statement_version);
        println!("semantic_scope: {}", proof.semantic_scope);
        println!("canonical_table_rows: {}", proof.canonical_table_rows.len());
        println!("expected_statement_version: {STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5}");
        println!("expected_semantic_scope: {STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5}");
        println!("expected_proof_backend_version: {STWO_NORMALIZATION_PROOF_VERSION_PHASE5}");
        println!("proof_bytes: {}", proof.proof.len());

        Ok(())
    }
}

fn prepare_stwo_recursion_batch_command(
    proofs: &[PathBuf],
    output: &Path,
) -> llm_provable_computer::Result<()> {
    if proofs.is_empty() {
        return Err(VmError::InvalidConfig(
            "prepare-stwo-recursion-batch requires at least one `--proof` path".to_string(),
        ));
    }

    let loaded = proofs
        .iter()
        .map(|path| load_execution_stark_proof(path))
        .collect::<Result<Vec<_>, _>>()?;
    let manifest = phase6_prepare_recursion_batch(&loaded)?;
    let json = serde_json::to_string_pretty(&manifest)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(output, json)?;

    println!("output: {}", output.display());
    println!("proof_backend: {}", manifest.proof_backend);
    println!("batch_version: {}", manifest.batch_version);
    println!("semantic_scope: {}", manifest.semantic_scope);
    println!("proof_backend_version: {}", manifest.proof_backend_version);
    println!("statement_version: {}", manifest.statement_version);
    println!("total_proofs: {}", manifest.total_proofs);
    println!("total_steps: {}", manifest.total_steps);
    println!("total_proof_bytes: {}", manifest.total_proof_bytes);
    println!("expected_batch_version: {STWO_RECURSION_BATCH_VERSION_PHASE6}");
    println!("expected_semantic_scope: {STWO_RECURSION_BATCH_SCOPE_PHASE6}");

    Ok(())
}

fn research_v2_step_command(
    program: &Path,
    output: &Path,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
) -> llm_provable_computer::Result<()> {
    research_v2_step_command_impl(program, output, max_steps, layers, attention_mode)
}

fn research_v2_trace_command(
    program: &Path,
    output: &Path,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
    allow_mismatch: bool,
) -> llm_provable_computer::Result<()> {
    research_v2_trace_command_impl(
        program,
        output,
        max_steps,
        layers,
        attention_mode,
        allow_mismatch,
    )
}

fn research_v2_matrix_command(
    output: &Path,
    programs: &[PathBuf],
    include_default_suite: bool,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
    allow_mismatch: bool,
) -> llm_provable_computer::Result<()> {
    research_v2_matrix_command_impl(
        output,
        programs,
        include_default_suite,
        max_steps,
        layers,
        attention_mode,
        allow_mismatch,
    )
}

#[cfg(feature = "onnx-export")]
fn research_v2_step_command_impl(
    program: &Path,
    output: &Path,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
) -> llm_provable_computer::Result<()> {
    if max_steps < 1 {
        return Err(VmError::InvalidConfig(
            "research-v2-step requires max_steps >= 1".to_string(),
        ));
    }

    let statement_spec_bytes = read_repo_file(STATEMENT_V2_STEP_SPEC_PATH)?;
    let fixed_point_spec_bytes = read_repo_file(FIXED_POINT_SPEC_PATH)?;
    let onnx_op_subset_spec_bytes = read_repo_file(ONNX_OP_SUBSET_SPEC_PATH)?;
    let artifact_schema_bytes = read_repo_file(STATEMENT_V2_STEP_ARTIFACT_SCHEMA_PATH)?;

    let statement_spec: StatementV2ResearchSpec = serde_json::from_slice(&statement_spec_bytes)
        .map_err(|err| {
            VmError::Serialization(format!(
                "failed to parse {}: {err}",
                STATEMENT_V2_STEP_SPEC_PATH
            ))
        })?;
    let fixed_point_spec: FixedPointSemanticsSpec = serde_json::from_slice(&fixed_point_spec_bytes)
        .map_err(|err| {
            VmError::Serialization(format!("failed to parse {}: {err}", FIXED_POINT_SPEC_PATH))
        })?;
    let onnx_op_subset_spec: OnnxOpSubsetSpec = serde_json::from_slice(&onnx_op_subset_spec_bytes)
        .map_err(|err| {
            VmError::Serialization(format!(
                "failed to parse {}: {err}",
                ONNX_OP_SUBSET_SPEC_PATH
            ))
        })?;

    if statement_spec.fixed_point_profile_ref != FIXED_POINT_SPEC_PATH {
        return Err(VmError::InvalidConfig(format!(
            "{} references `{}` but expected `{}`",
            STATEMENT_V2_STEP_SPEC_PATH,
            statement_spec.fixed_point_profile_ref,
            FIXED_POINT_SPEC_PATH
        )));
    }
    if statement_spec.onnx_op_subset_ref != ONNX_OP_SUBSET_SPEC_PATH {
        return Err(VmError::InvalidConfig(format!(
            "{} references `{}` but expected `{}`",
            STATEMENT_V2_STEP_SPEC_PATH,
            statement_spec.onnx_op_subset_ref,
            ONNX_OP_SUBSET_SPEC_PATH
        )));
    }
    if statement_spec.artifact_schema_ref != STATEMENT_V2_STEP_ARTIFACT_SCHEMA_PATH {
        return Err(VmError::InvalidConfig(format!(
            "{} references `{}` but expected `{}`",
            STATEMENT_V2_STEP_SPEC_PATH,
            statement_spec.artifact_schema_ref,
            STATEMENT_V2_STEP_ARTIFACT_SCHEMA_PATH
        )));
    }

    let model = compile_model(program, layers, attention_mode)?;
    let export_dir = ScopedTempDir::new("research-v2-step")?;
    let onnx_metadata = export_program_onnx(&model, export_dir.path())?;

    let mut transformer = ExecutionRuntime::new(model.clone(), max_steps);
    let mut onnx = OnnxExecutionRuntime::from_export_dir(export_dir.path(), max_steps)?;

    let state_before = transformer.state().clone();
    if state_before != onnx.state().clone() {
        return Err(VmError::InvalidConfig(
            "research-v2-step initial state mismatch between transformer and ONNX runtimes"
                .to_string(),
        ));
    }
    if state_before.halted {
        return Err(VmError::InvalidConfig(
            "research-v2-step requires a non-halted initial state".to_string(),
        ));
    }

    transformer.step()?;
    onnx.step()?;

    let transformer_event = transformer
        .events()
        .last()
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "research-v2-step transformer runtime produced no execution event".to_string(),
            )
        })?
        .clone();
    let onnx_event = onnx
        .events()
        .last()
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "research-v2-step ONNX runtime produced no execution event".to_string(),
            )
        })?
        .clone();
    if transformer_event.instruction != onnx_event.instruction {
        return Err(VmError::InvalidConfig(format!(
            "research-v2-step instruction mismatch: transformer=`{}` onnx=`{}`",
            transformer_event.instruction, onnx_event.instruction
        )));
    }

    let transformer_state_after = transformer.state().clone();
    let onnx_state_after = onnx.state().clone();
    let matched = transformer_state_after == onnx_state_after;

    let commitments = ResearchV2OneStepCommitments {
        hash_function: RESEARCH_V2_HASH_FUNCTION.to_string(),
        statement_spec_hash: hash_bytes_hex(&statement_spec_bytes),
        fixed_point_spec_hash: hash_bytes_hex(&fixed_point_spec_bytes),
        onnx_op_subset_hash: hash_bytes_hex(&onnx_op_subset_spec_bytes),
        artifact_schema_hash: hash_bytes_hex(&artifact_schema_bytes),
        program_hash: hash_json_hex(model.program())?,
        transformer_config_hash: hash_json_hex(model.config())?,
        onnx_metadata_hash: hash_json_hex(&onnx_metadata)?,
        state_before_hash: hash_json_hex(&state_before)?,
        transformer_state_after_hash: hash_json_hex(&transformer_state_after)?,
        onnx_state_after_hash: hash_json_hex(&onnx_state_after)?,
    };

    let artifact = ResearchV2OneStepArtifact {
        statement_version: statement_spec.statement_version,
        semantic_scope: statement_spec.semantic_scope,
        fixed_point_profile: fixed_point_spec.profile_id,
        onnx_op_subset_version: onnx_op_subset_spec.version,
        onnx_op_subset_size: onnx_op_subset_spec.operators.len(),
        program_path: program.display().to_string(),
        checked_steps: transformer.step_count(),
        instruction: transformer_event.instruction.to_string(),
        layer_idx: transformer_event.layer_idx,
        matched,
        state_before,
        transformer_state_after,
        onnx_state_after,
        commitments,
    };

    if !matched {
        return Err(VmError::InvalidConfig(format!(
            "research-v2-step mismatch for instruction `{}`",
            artifact.instruction
        )));
    }

    let bytes = serde_json::to_vec_pretty(&artifact)
        .map_err(|err| VmError::Serialization(format!("failed to serialize artifact: {err}")))?;
    fs::write(output, bytes)?;

    println!("research_v2_artifact: {}", output.display());
    println!("statement_version: {}", artifact.statement_version);
    println!("semantic_scope: {}", artifact.semantic_scope);
    println!("fixed_point_profile: {}", artifact.fixed_point_profile);
    println!(
        "onnx_op_subset_version: {}",
        artifact.onnx_op_subset_version
    );
    println!("checked_steps: {}", artifact.checked_steps);
    println!("instruction: {}", artifact.instruction);
    println!("matched: {}", artifact.matched);
    println!(
        "commitment_program_hash: {}",
        artifact.commitments.program_hash
    );
    println!(
        "commitment_onnx_metadata_hash: {}",
        artifact.commitments.onnx_metadata_hash
    );

    Ok(())
}

#[cfg(feature = "onnx-export")]
fn research_v2_trace_command_impl(
    program: &Path,
    output: &Path,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
    allow_mismatch: bool,
) -> llm_provable_computer::Result<()> {
    let bundle = load_research_v2_spec_bundle(
        STATEMENT_V2_TRACE_SPEC_PATH,
        STATEMENT_V2_TRACE_ARTIFACT_SCHEMA_PATH,
    )?;
    let artifact = compute_research_v2_trace_artifact_for_program(
        program,
        max_steps,
        layers,
        &attention_mode,
        &bundle,
    )?;

    enforce_research_v2_trace_mismatch_policy(
        artifact.matched,
        allow_mismatch,
        artifact.first_mismatch_step,
        artifact.mismatch_reason.as_deref(),
    )?;

    let bytes = serde_json::to_vec_pretty(&artifact)
        .map_err(|err| VmError::Serialization(format!("failed to serialize artifact: {err}")))?;
    fs::write(output, bytes)?;

    println!("research_v2_trace_artifact: {}", output.display());
    println!("statement_version: {}", artifact.statement_version);
    println!("semantic_scope: {}", artifact.semantic_scope);
    println!("fixed_point_profile: {}", artifact.fixed_point_profile);
    println!(
        "onnx_op_subset_version: {}",
        artifact.onnx_op_subset_version
    );
    println!("requested_max_steps: {}", artifact.requested_max_steps);
    println!("checked_steps: {}", artifact.checked_steps);
    println!("matched: {}", artifact.matched);
    if let Some(step) = artifact.first_mismatch_step {
        println!("first_mismatch_step: {step}");
    }
    if let Some(reason) = artifact.mismatch_reason.as_ref() {
        println!("mismatch_reason: {reason}");
    }
    println!(
        "commitment_program_hash: {}",
        artifact.commitments.program_hash
    );
    println!(
        "commitment_onnx_metadata_hash: {}",
        artifact.commitments.onnx_metadata_hash
    );

    Ok(())
}

#[cfg(feature = "onnx-export")]
fn research_v2_matrix_command_impl(
    output: &Path,
    programs: &[PathBuf],
    include_default_suite: bool,
    max_steps: usize,
    layers: usize,
    attention_mode: Attention2DMode,
    allow_mismatch: bool,
) -> llm_provable_computer::Result<()> {
    let bundle = load_research_v2_spec_bundle(
        STATEMENT_V2_MATRIX_SPEC_PATH,
        STATEMENT_V2_MATRIX_ARTIFACT_SCHEMA_PATH,
    )?;

    let mut selected = Vec::<PathBuf>::new();
    if include_default_suite {
        selected.extend(research_v2_default_program_suite());
    }
    selected.extend(programs.iter().cloned());

    if selected.is_empty() {
        return Err(VmError::InvalidConfig(
            "research-v2-matrix requires at least one --program or --include-default-suite"
                .to_string(),
        ));
    }

    let mut deduped = Vec::<PathBuf>::new();
    for path in selected {
        if !deduped.iter().any(|existing| existing == &path) {
            deduped.push(path);
        }
    }

    let mut entries = Vec::<ResearchV2MatrixEntry>::with_capacity(deduped.len());
    for program in deduped {
        let trace = compute_research_v2_trace_artifact_for_program(
            &program,
            max_steps,
            layers,
            &attention_mode,
            &bundle,
        )?;
        entries.push(ResearchV2MatrixEntry {
            program_path: trace.program_path,
            checked_steps: trace.checked_steps,
            matched: trace.matched,
            first_mismatch_step: trace.first_mismatch_step,
            mismatch_reason: trace.mismatch_reason,
            transformer_final_state: trace.transformer_final_state,
            onnx_final_state: trace.onnx_final_state,
            commitments: trace.commitments,
        });
    }

    let matched_programs = entries.iter().filter(|entry| entry.matched).count();
    let mismatched_programs = entries.len() - matched_programs;
    let matrix_entries_hash = hash_json_hex(&entries)?;

    let artifact = ResearchV2MatrixArtifact {
        statement_version: bundle.statement_version.clone(),
        semantic_scope: bundle.semantic_scope.clone(),
        fixed_point_profile: bundle.fixed_point_profile.clone(),
        onnx_op_subset_version: bundle.onnx_op_subset_version.clone(),
        onnx_op_subset_size: bundle.onnx_op_subset_size,
        requested_max_steps: max_steps,
        total_programs: entries.len(),
        matched_programs,
        mismatched_programs,
        entries,
        commitments: ResearchV2MatrixCommitments {
            hash_function: RESEARCH_V2_HASH_FUNCTION.to_string(),
            statement_spec_hash: bundle.statement_spec_hash.clone(),
            fixed_point_spec_hash: bundle.fixed_point_spec_hash.clone(),
            onnx_op_subset_hash: bundle.onnx_op_subset_hash.clone(),
            artifact_schema_hash: bundle.artifact_schema_hash.clone(),
            matrix_entries_hash,
        },
    };

    enforce_research_v2_matrix_mismatch_policy(artifact.mismatched_programs, allow_mismatch)?;

    let bytes = serde_json::to_vec_pretty(&artifact)
        .map_err(|err| VmError::Serialization(format!("failed to serialize artifact: {err}")))?;
    fs::write(output, bytes)?;

    println!("research_v2_matrix_artifact: {}", output.display());
    println!("statement_version: {}", artifact.statement_version);
    println!("semantic_scope: {}", artifact.semantic_scope);
    println!("requested_max_steps: {}", artifact.requested_max_steps);
    println!("total_programs: {}", artifact.total_programs);
    println!("matched_programs: {}", artifact.matched_programs);
    println!("mismatched_programs: {}", artifact.mismatched_programs);
    println!(
        "commitment_matrix_entries_hash: {}",
        artifact.commitments.matrix_entries_hash
    );

    Ok(())
}

#[cfg(feature = "onnx-export")]
fn enforce_research_v2_trace_mismatch_policy(
    matched: bool,
    allow_mismatch: bool,
    first_mismatch_step: Option<usize>,
    mismatch_reason: Option<&str>,
) -> llm_provable_computer::Result<()> {
    if !matched && !allow_mismatch {
        return Err(VmError::InvalidConfig(format!(
            "research-v2-trace mismatch at step {:?}: {}",
            first_mismatch_step,
            mismatch_reason.unwrap_or("unspecified mismatch")
        )));
    }
    Ok(())
}

#[cfg(feature = "onnx-export")]
fn enforce_research_v2_matrix_mismatch_policy(
    mismatched_programs: usize,
    allow_mismatch: bool,
) -> llm_provable_computer::Result<()> {
    if mismatched_programs > 0 && !allow_mismatch {
        return Err(VmError::InvalidConfig(format!(
            "research-v2-matrix found {} mismatched program(s)",
            mismatched_programs
        )));
    }
    Ok(())
}

#[cfg(feature = "onnx-export")]
fn load_research_v2_spec_bundle(
    statement_spec_path: &str,
    artifact_schema_path: &str,
) -> llm_provable_computer::Result<ResearchV2SpecBundle> {
    let statement_spec_bytes = read_repo_file(statement_spec_path)?;
    let fixed_point_spec_bytes = read_repo_file(FIXED_POINT_SPEC_PATH)?;
    let onnx_op_subset_spec_bytes = read_repo_file(ONNX_OP_SUBSET_SPEC_PATH)?;
    let artifact_schema_bytes = read_repo_file(artifact_schema_path)?;

    let statement_spec: StatementV2ResearchSpec = serde_json::from_slice(&statement_spec_bytes)
        .map_err(|err| {
            VmError::Serialization(format!("failed to parse {}: {err}", statement_spec_path))
        })?;
    let fixed_point_spec: FixedPointSemanticsSpec = serde_json::from_slice(&fixed_point_spec_bytes)
        .map_err(|err| {
            VmError::Serialization(format!("failed to parse {}: {err}", FIXED_POINT_SPEC_PATH))
        })?;
    let onnx_op_subset_spec: OnnxOpSubsetSpec = serde_json::from_slice(&onnx_op_subset_spec_bytes)
        .map_err(|err| {
            VmError::Serialization(format!(
                "failed to parse {}: {err}",
                ONNX_OP_SUBSET_SPEC_PATH
            ))
        })?;

    if statement_spec.fixed_point_profile_ref != FIXED_POINT_SPEC_PATH {
        return Err(VmError::InvalidConfig(format!(
            "{} references `{}` but expected `{}`",
            statement_spec_path, statement_spec.fixed_point_profile_ref, FIXED_POINT_SPEC_PATH
        )));
    }
    if statement_spec.onnx_op_subset_ref != ONNX_OP_SUBSET_SPEC_PATH {
        return Err(VmError::InvalidConfig(format!(
            "{} references `{}` but expected `{}`",
            statement_spec_path, statement_spec.onnx_op_subset_ref, ONNX_OP_SUBSET_SPEC_PATH
        )));
    }
    if statement_spec.artifact_schema_ref != artifact_schema_path {
        return Err(VmError::InvalidConfig(format!(
            "{} references `{}` but expected `{}`",
            statement_spec_path, statement_spec.artifact_schema_ref, artifact_schema_path
        )));
    }

    Ok(ResearchV2SpecBundle {
        statement_version: statement_spec.statement_version,
        semantic_scope: statement_spec.semantic_scope,
        fixed_point_profile: fixed_point_spec.profile_id,
        onnx_op_subset_version: onnx_op_subset_spec.version,
        onnx_op_subset_size: onnx_op_subset_spec.operators.len(),
        statement_spec_hash: hash_bytes_hex(&statement_spec_bytes),
        fixed_point_spec_hash: hash_bytes_hex(&fixed_point_spec_bytes),
        onnx_op_subset_hash: hash_bytes_hex(&onnx_op_subset_spec_bytes),
        artifact_schema_hash: hash_bytes_hex(&artifact_schema_bytes),
    })
}

#[cfg(feature = "onnx-export")]
fn compute_research_v2_trace_artifact_for_program(
    program: &Path,
    max_steps: usize,
    layers: usize,
    attention_mode: &Attention2DMode,
    bundle: &ResearchV2SpecBundle,
) -> llm_provable_computer::Result<ResearchV2TraceArtifact> {
    if max_steps < 1 {
        return Err(VmError::InvalidConfig(
            "research-v2 trace computation requires max_steps >= 1".to_string(),
        ));
    }

    let model = compile_model(program, layers, attention_mode.clone())?;
    let export_dir = ScopedTempDir::new("research-v2-trace")?;
    let onnx_metadata = export_program_onnx(&model, export_dir.path())?;

    let mut transformer = ExecutionRuntime::new(model.clone(), max_steps);
    let mut onnx = OnnxExecutionRuntime::from_export_dir(export_dir.path(), max_steps)?;

    let mut matched = true;
    let mut first_mismatch_step: Option<usize> = None;
    let mut mismatch_reason: Option<String> = None;

    if transformer.state() != onnx.state() {
        matched = false;
        first_mismatch_step = Some(0);
        mismatch_reason =
            Some("initial state mismatch between transformer and ONNX runtimes".to_string());
    }

    while matched && transformer.step_count() < max_steps {
        let t_halted = transformer.state().halted;
        let o_halted = onnx.state().halted;
        if t_halted || o_halted {
            if t_halted != o_halted {
                matched = false;
                first_mismatch_step = Some(transformer.step_count());
                mismatch_reason = Some(format!(
                    "halted flag mismatch before step {}: transformer={}, onnx={}",
                    transformer.step_count() + 1,
                    t_halted,
                    o_halted
                ));
            }
            break;
        }

        transformer.step()?;
        onnx.step()?;
        let step = transformer.step_count();
        if step != onnx.step_count() {
            matched = false;
            first_mismatch_step = Some(step.min(onnx.step_count()));
            mismatch_reason = Some(format!(
                "step counter mismatch: transformer={}, onnx={}",
                step,
                onnx.step_count()
            ));
            break;
        }

        let transformer_event = transformer.events().last().ok_or_else(|| {
            VmError::InvalidConfig("transformer runtime produced no execution event".to_string())
        })?;
        let onnx_event = onnx.events().last().ok_or_else(|| {
            VmError::InvalidConfig("onnx runtime produced no execution event".to_string())
        })?;

        if transformer_event.instruction != onnx_event.instruction {
            matched = false;
            first_mismatch_step = Some(step);
            mismatch_reason = Some(format!(
                "instruction mismatch at step {}: transformer=`{}` onnx=`{}`",
                step, transformer_event.instruction, onnx_event.instruction
            ));
            break;
        }
        if transformer_event.state_before != onnx_event.state_before {
            matched = false;
            first_mismatch_step = Some(step);
            mismatch_reason = Some(format!("state_before mismatch at step {}", step));
            break;
        }
        if transformer_event.state_after != onnx_event.state_after {
            matched = false;
            first_mismatch_step = Some(step);
            mismatch_reason = Some(format!("state_after mismatch at step {}", step));
            break;
        }
    }

    let checked_steps = transformer.step_count().min(onnx.step_count());
    let transformer_final_state = transformer.state().clone();
    let onnx_final_state = onnx.state().clone();
    if matched && transformer_final_state != onnx_final_state {
        matched = false;
        first_mismatch_step = Some(checked_steps);
        mismatch_reason = Some("final state mismatch".to_string());
    }

    let commitments = ResearchV2TraceCommitments {
        hash_function: RESEARCH_V2_HASH_FUNCTION.to_string(),
        statement_spec_hash: bundle.statement_spec_hash.clone(),
        fixed_point_spec_hash: bundle.fixed_point_spec_hash.clone(),
        onnx_op_subset_hash: bundle.onnx_op_subset_hash.clone(),
        artifact_schema_hash: bundle.artifact_schema_hash.clone(),
        program_hash: hash_json_hex(model.program())?,
        transformer_config_hash: hash_json_hex(model.config())?,
        onnx_metadata_hash: hash_json_hex(&onnx_metadata)?,
        transformer_trace_hash: hash_json_hex(transformer.trace())?,
        onnx_trace_hash: hash_json_hex(onnx.trace())?,
        transformer_final_state_hash: hash_json_hex(&transformer_final_state)?,
        onnx_final_state_hash: hash_json_hex(&onnx_final_state)?,
    };

    Ok(ResearchV2TraceArtifact {
        statement_version: bundle.statement_version.clone(),
        semantic_scope: bundle.semantic_scope.clone(),
        fixed_point_profile: bundle.fixed_point_profile.clone(),
        onnx_op_subset_version: bundle.onnx_op_subset_version.clone(),
        onnx_op_subset_size: bundle.onnx_op_subset_size,
        program_path: program.display().to_string(),
        requested_max_steps: max_steps,
        checked_steps,
        matched,
        first_mismatch_step,
        mismatch_reason,
        transformer_final_state,
        onnx_final_state,
        commitments,
    })
}

#[cfg(feature = "onnx-export")]
fn research_v2_default_program_suite() -> Vec<PathBuf> {
    vec![
        PathBuf::from("programs/addition.tvm"),
        PathBuf::from("programs/counter.tvm"),
        PathBuf::from("programs/fibonacci.tvm"),
        PathBuf::from("programs/multiply.tvm"),
        PathBuf::from("programs/factorial_recursive.tvm"),
        PathBuf::from("programs/dot_product.tvm"),
        PathBuf::from("programs/matmul_2x2.tvm"),
        PathBuf::from("programs/single_neuron.tvm"),
    ]
}

#[cfg(not(feature = "onnx-export"))]
fn research_v2_step_command_impl(
    _program: &Path,
    _output: &Path,
    _max_steps: usize,
    _layers: usize,
    _attention_mode: Attention2DMode,
) -> llm_provable_computer::Result<()> {
    Err(feature_required_error(
        "`research-v2-step`",
        &["onnx-export"],
    ))
}

#[cfg(not(feature = "onnx-export"))]
fn research_v2_trace_command_impl(
    _program: &Path,
    _output: &Path,
    _max_steps: usize,
    _layers: usize,
    _attention_mode: Attention2DMode,
    _allow_mismatch: bool,
) -> llm_provable_computer::Result<()> {
    Err(feature_required_error(
        "`research-v2-trace`",
        &["onnx-export"],
    ))
}

#[cfg(not(feature = "onnx-export"))]
fn research_v2_matrix_command_impl(
    _output: &Path,
    _programs: &[PathBuf],
    _include_default_suite: bool,
    _max_steps: usize,
    _layers: usize,
    _attention_mode: Attention2DMode,
    _allow_mismatch: bool,
) -> llm_provable_computer::Result<()> {
    Err(feature_required_error(
        "`research-v2-matrix`",
        &["onnx-export"],
    ))
}

#[cfg(feature = "onnx-export")]
fn read_repo_file(relative_path: &str) -> llm_provable_computer::Result<Vec<u8>> {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join(relative_path);
    fs::read(&path).map_err(|io_error| {
        VmError::InvalidConfig(format!("failed to read {}: {io_error}", path.display()))
    })
}

#[cfg(feature = "onnx-export")]
fn hash_json_hex<T: Serialize + ?Sized>(value: &T) -> llm_provable_computer::Result<String> {
    let bytes = serde_json::to_vec(value).map_err(|err| {
        VmError::Serialization(format!("failed to serialize hash payload: {err}"))
    })?;
    Ok(hash_bytes_hex(&bytes))
}

#[cfg(feature = "onnx-export")]
fn hash_bytes_hex(bytes: &[u8]) -> String {
    let mut output = [0u8; 32];
    let mut hasher = Blake2bVar::new(output.len()).expect("blake2b-256 hasher");
    hasher.update(bytes);
    hasher
        .finalize_variable(&mut output)
        .expect("blake2b-256 finalization");
    output.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(all(test, feature = "onnx-export"))]
mod tests {
    use super::*;

    #[test]
    fn trace_mismatch_policy_rejects_without_allow_flag() {
        let err = enforce_research_v2_trace_mismatch_policy(
            false,
            false,
            Some(7),
            Some("state_after mismatch at step 7"),
        )
        .unwrap_err();
        let message = err.to_string();
        assert!(message.contains("research-v2-trace mismatch"));
        assert!(message.contains("Some(7)"));
        assert!(message.contains("state_after mismatch at step 7"));
    }

    #[test]
    fn trace_mismatch_policy_allows_with_allow_flag() {
        enforce_research_v2_trace_mismatch_policy(false, true, Some(3), Some("mismatch"))
            .expect("allow mismatch");
    }

    #[test]
    fn matrix_mismatch_policy_rejects_without_allow_flag() {
        let err = enforce_research_v2_matrix_mismatch_policy(2, false).unwrap_err();
        assert!(err
            .to_string()
            .contains("research-v2-matrix found 2 mismatched program(s)"));
    }

    #[test]
    fn matrix_mismatch_policy_allows_with_allow_flag() {
        enforce_research_v2_matrix_mismatch_policy(1, true).expect("allow mismatch");
    }

    #[test]
    fn default_matrix_suite_contains_neural_style_programs() {
        let suite = research_v2_default_program_suite();
        assert!(suite.contains(&PathBuf::from("programs/dot_product.tvm")));
        assert!(suite.contains(&PathBuf::from("programs/matmul_2x2.tvm")));
        assert!(suite.contains(&PathBuf::from("programs/single_neuron.tvm")));
    }
}

#[cfg(test)]
mod cli_dispatch_tests {
    use super::needs_run_subcommand;

    #[test]
    fn intervalized_phase25_commands_do_not_fall_back_to_run_shorthand() {
        assert!(!needs_run_subcommand(
            "prove-stwo-intervalized-decoding-state-relation-demo"
        ));
        assert!(!needs_run_subcommand(
            "verify-stwo-intervalized-decoding-state-relation-demo"
        ));
        assert!(!needs_run_subcommand(
            "prove-stwo-folded-intervalized-decoding-state-relation-demo"
        ));
        assert!(!needs_run_subcommand(
            "verify-stwo-folded-intervalized-decoding-state-relation-demo"
        ));
        assert!(!needs_run_subcommand(
            "prove-stwo-chained-folded-intervalized-decoding-state-relation-demo"
        ));
        assert!(!needs_run_subcommand(
            "verify-stwo-chained-folded-intervalized-decoding-state-relation-demo"
        ));
        assert!(!needs_run_subcommand(
            "prove-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo"
        ));
        assert!(!needs_run_subcommand(
            "verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo"
        ));
        assert!(!needs_run_subcommand(
            "prepare-stwo-recursive-compression-input-contract"
        ));
        assert!(!needs_run_subcommand(
            "verify-stwo-recursive-compression-input-contract"
        ));
    }
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
            "run"
                | "tui"
                | "export-onnx"
                | "prove-stark"
                | "verify-stark"
                | "prove-stwo-lookup-demo"
                | "verify-stwo-lookup-demo"
                | "prove-stwo-normalization-demo"
                | "verify-stwo-normalization-demo"
                | "prove-stwo-shared-lookup-demo"
                | "verify-stwo-shared-lookup-demo"
                | "prove-stwo-shared-normalization-demo"
                | "verify-stwo-shared-normalization-demo"
                | "prove-stwo-decoding-demo"
                | "verify-stwo-decoding-demo"
                | "prove-stwo-decoding-family-demo"
                | "verify-stwo-decoding-family-demo"
                | "prove-stwo-decoding-layout-matrix-demo"
                | "verify-stwo-decoding-layout-matrix-demo"
                | "prove-stwo-decoding-chunked-history-demo"
                | "verify-stwo-decoding-chunked-history-demo"
                | "prove-stwo-decoding-history-segments-demo"
                | "verify-stwo-decoding-history-segments-demo"
                | "prove-stwo-decoding-history-rollup-demo"
                | "verify-stwo-decoding-history-rollup-demo"
                | "prove-stwo-decoding-history-rollup-matrix-demo"
                | "verify-stwo-decoding-history-rollup-matrix-demo"
                | "prove-stwo-decoding-matrix-accumulator-demo"
                | "verify-stwo-decoding-matrix-accumulator-demo"
                | "prove-stwo-decoding-lookup-accumulator-demo"
                | "verify-stwo-decoding-lookup-accumulator-demo"
                | "prove-stwo-decoding-cross-step-lookup-accumulator-demo"
                | "verify-stwo-decoding-cross-step-lookup-accumulator-demo"
                | "prove-stwo-decoding-state-relation-accumulator-demo"
                | "verify-stwo-decoding-state-relation-accumulator-demo"
                | "prove-stwo-intervalized-decoding-state-relation-demo"
                | "verify-stwo-intervalized-decoding-state-relation-demo"
                | "prove-stwo-folded-intervalized-decoding-state-relation-demo"
                | "verify-stwo-folded-intervalized-decoding-state-relation-demo"
                | "prove-stwo-chained-folded-intervalized-decoding-state-relation-demo"
                | "verify-stwo-chained-folded-intervalized-decoding-state-relation-demo"
                | "prove-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo"
                | "verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo"
                | "prepare-stwo-recursive-compression-input-contract"
                | "verify-stwo-recursive-compression-input-contract"
                | "prepare-stwo-recursion-batch"
                | "research-v2-step"
                | "research-v2-trace"
                | "research-v2-matrix"
                | "help"
        )
}

fn print_stwo_normalization_companion(proof: &VanillaStarkExecutionProof) {
    if let Some(auxiliary) = &proof.stwo_auxiliary {
        if let Some(companion) = &auxiliary.normalization_companion {
            println!(
                "stwo_normalization_companion_scope: {}",
                companion.semantic_scope
            );
            println!(
                "stwo_normalization_companion_norm_sq_index: {}",
                companion.norm_sq_memory_index
            );
            println!(
                "stwo_normalization_companion_inv_sqrt_index: {}",
                companion.inv_sqrt_q8_memory_index
            );
            println!(
                "stwo_normalization_companion_expected_row: ({}, {})",
                companion.expected_norm_sq, companion.expected_inv_sqrt_q8
            );
        }
    }
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
