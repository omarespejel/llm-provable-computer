pub mod assembly;
#[cfg(feature = "burn-model")]
pub mod burn_model;
#[cfg(feature = "burn-model")]
pub mod burn_runtime;
pub mod compiler;
pub mod config;
pub mod engine;
pub mod error;
pub mod geometry;
pub mod instruction;
pub mod interpreter;
pub mod memory;
pub mod model;
#[cfg(feature = "onnx-export")]
pub mod onnx_export;
#[cfg(feature = "onnx-export")]
pub mod onnx_runtime;
pub mod proof;
pub mod runtime;
pub mod state;
pub mod stwo_backend;
pub mod tui;
pub mod vanillastark;
pub mod verification;

pub use assembly::parse_program;
#[cfg(feature = "burn-model")]
pub use burn_model::{
    load_burn_model, load_burn_model_on_device, save_burn_model, BurnTransformerVm,
};
#[cfg(feature = "burn-model")]
pub use burn_runtime::BurnExecutionRuntime;
pub use compiler::ProgramCompiler;
pub use config::{Attention2DMode, TransformerVmConfig};
pub use engine::{
    ExecutionEngine, ExecutionResult, ExecutionTraceEntry, VerificationResult, VerifiedEngine,
};
pub use error::{Result, VmError};
pub use geometry::{HullKvCache, Point2D};
pub use instruction::{Instruction, Program};
pub use interpreter::{NativeExecutionResult, NativeInterpreter, NativeTraceEntry};
pub use memory::AddressedMemory;
pub use model::{DispatchInfo, TransformerVm};
#[cfg(feature = "onnx-export")]
pub use onnx_export::{
    export_program_onnx, load_onnx_program_metadata, OnnxInputLayoutEntry, OnnxInstructionMetadata,
    OnnxInstructionRead, OnnxProgramMetadata, ONNX_OUTPUT_DIM,
};
#[cfg(feature = "onnx-export")]
pub use onnx_runtime::OnnxExecutionRuntime;
pub use proof::{
    conjectured_security_bits, load_execution_stark_proof, production_v1_stark_options,
    prove_execution_stark, prove_execution_stark_with_backend_and_options,
    prove_execution_stark_with_options, save_execution_stark_proof, verify_execution_stark,
    verify_execution_stark_with_backend_and_policy, verify_execution_stark_with_policy,
    verify_execution_stark_with_reexecution, verify_execution_stark_with_reexecution_and_policy,
    ExecutionClaimCommitments, ExecutionEquivalenceMetadata, StarkProofBackend,
    StarkVerificationPolicy, VanillaStarkExecutionClaim, VanillaStarkExecutionProof,
    VanillaStarkProofOptions, CLAIM_COMMITMENT_HASH_FUNCTION_V1,
    CLAIM_COMMITMENT_SCHEME_VERSION_V1, CLAIM_SEMANTIC_SCOPE_V1, CLAIM_STATEMENT_VERSION_V1,
    PRODUCTION_V1_MIN_CONJECTURED_SECURITY_BITS, PRODUCTION_V1_TARGET_MAX_PROVING_SECONDS,
};
pub use runtime::ExecutionRuntime;
pub use state::{decode_state, encode_state, MachineState, MIN_D_MODEL};
pub use stwo_backend::{
    is_enabled as stwo_backend_enabled, phase2_dependency_seam, phase2_fixture_matrix,
    phase2_module_layout, phase2_supported_mnemonics, StwoBackendModuleLayout, StwoDependencySeam,
    STWO_BACKEND_FEATURE_NAME, STWO_BACKEND_VERSION_PHASE2,
    STWO_CONSTRAINT_FRAMEWORK_VERSION_PHASE2, STWO_CRATE_VERSION_PHASE2,
};
pub use tui::run_execution_tui;
pub use verification::{verify_engines, verify_model_against_native, ExecutionComparison};
