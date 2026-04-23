use std::fs;
use std::io::Read;
use std::path::Path;

use blake2::digest::{Update, VariableOutput};
use blake2::{Blake2b512, Blake2bVar, Digest};
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::config::Attention2DMode;
use crate::config::TransformerVmConfig;
use crate::engine::ExecutionResult;
use crate::error::{Result, VmError};
#[cfg(test)]
use crate::instruction::Instruction;
use crate::instruction::Program;
use crate::model::TransformerVm;
use crate::runtime::ExecutionRuntime;
use crate::state::MachineState;
use crate::stwo_backend;
use crate::verification::verify_model_against_native;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "kebab-case")]
pub enum StarkProofBackend {
    #[default]
    Stwo,
}

impl std::fmt::Display for StarkProofBackend {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Stwo => f.write_str("stwo"),
        }
    }
}

fn default_stark_proof_backend() -> StarkProofBackend {
    StarkProofBackend::Stwo
}

fn default_stark_proof_backend_version() -> String {
    stwo_backend::STWO_BACKEND_VERSION_PHASE5.to_string()
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VanillaStarkProofOptions {
    pub expansion_factor: usize,
    pub num_colinearity_checks: usize,
    pub security_level: usize,
}

impl Default for VanillaStarkProofOptions {
    fn default() -> Self {
        Self {
            expansion_factor: 4,
            num_colinearity_checks: 2,
            security_level: 2,
        }
    }
}

/// Production STARK profile (v1) tuned for local proving throughput in release builds.
///
/// This profile targets ~32 conjectured security bits while keeping proving time under
/// roughly 45 seconds for the 103-step `programs/fibonacci.tvm` benchmark on a modern laptop.
pub fn production_v1_stark_options() -> VanillaStarkProofOptions {
    VanillaStarkProofOptions {
        expansion_factor: 4,
        num_colinearity_checks: 16,
        security_level: 32,
    }
}

/// Minimum conjectured security floor expected when verifying production-v1 proofs.
pub const PRODUCTION_V1_MIN_CONJECTURED_SECURITY_BITS: u32 = 32;

/// Target proving-time budget for production-v1 on local release builds.
pub const PRODUCTION_V1_TARGET_MAX_PROVING_SECONDS: u64 = 45;

/// Publication-grade STARK profile.
///
/// Targets >= 96 conjectured security bits under the optimistic per-query bound
/// `q * log2(rho^-1)` and >= 48 bits under the conservative Reed-Solomon list-decoding
/// bound `q * log2(rho^-1) / 2`. Intended for any proof that is cited as evidence
/// in a paper, public release, or third-party review. Not intended for routine CI.
///
/// Settings: expansion_factor = 16, num_colinearity_checks = 24, security_level = 48.
/// Conjectured bits = trailing_zeros(16) * 24 = 4 * 24 = 96.
///
/// Proving time is materially higher than `production-v1`; budget for ~5-10x.
/// Publication-cited artifacts must be generated under this profile (or stronger);
/// `production-v1` is a CI smoke profile and is not a cryptographic claim.
pub fn publication_v1_stark_options() -> VanillaStarkProofOptions {
    VanillaStarkProofOptions {
        expansion_factor: 16,
        num_colinearity_checks: 24,
        security_level: 48,
    }
}

/// Minimum conjectured security floor expected when verifying publication-v1 proofs.
pub const PUBLICATION_V1_MIN_CONJECTURED_SECURITY_BITS: u32 = 96;

/// Returns only the publication-v1 security-bit floor.
///
/// This helper does not encode the full CLI profile semantics. Callers that
/// need publication-v1 parity with the CLI must also enforce reexecution at
/// the command boundary.
pub fn publication_v1_security_floor_policy() -> StarkVerificationPolicy {
    StarkVerificationPolicy {
        min_conjectured_security_bits: PUBLICATION_V1_MIN_CONJECTURED_SECURITY_BITS,
    }
}

const STARK_FIELD_SECURITY_BITS: u32 = 128;
const MAX_STARK_EXPANSION_FACTOR: usize = 64;
const MAX_STARK_NUM_COLINEARITY_CHECKS: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct StarkVerificationPolicy {
    pub min_conjectured_security_bits: u32,
}

impl StarkVerificationPolicy {
    pub fn strict() -> Self {
        Self {
            min_conjectured_security_bits: 80,
        }
    }
}

pub fn production_v1_verification_policy() -> StarkVerificationPolicy {
    StarkVerificationPolicy {
        min_conjectured_security_bits: PRODUCTION_V1_MIN_CONJECTURED_SECURITY_BITS,
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum StarkVerificationExecutionMode {
    ClaimOnly,
    Reexecute,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VanillaStarkExecutionClaim {
    #[serde(default)]
    pub statement_version: String,
    #[serde(default)]
    pub semantic_scope: String,
    pub program: Program,
    pub attention_mode: Attention2DMode,
    #[serde(default)]
    pub transformer_config: Option<TransformerVmConfig>,
    pub steps: usize,
    pub final_state: MachineState,
    pub options: VanillaStarkProofOptions,
    #[serde(default)]
    pub equivalence: Option<ExecutionEquivalenceMetadata>,
    #[serde(default)]
    pub commitments: Option<ExecutionClaimCommitments>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VanillaStarkExecutionProof {
    #[serde(default = "default_stark_proof_backend")]
    pub proof_backend: StarkProofBackend,
    #[serde(default = "default_stark_proof_backend_version")]
    pub proof_backend_version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stwo_auxiliary: Option<StwoAuxiliaryProofs>,
    pub claim: VanillaStarkExecutionClaim,
    pub proof: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoAuxiliaryProofs {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub normalization_companion: Option<StwoNormalizationCompanion>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoNormalizationCompanion {
    pub statement_version: String,
    pub semantic_scope: String,
    pub norm_sq_memory_index: u8,
    pub inv_sqrt_q8_memory_index: u8,
    pub expected_norm_sq: i16,
    pub expected_inv_sqrt_q8: i16,
    pub proof_envelope: Value,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionEquivalenceMetadata {
    pub checked_steps: usize,
    pub transformer_fingerprint: String,
    pub native_fingerprint: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionClaimCommitments {
    pub scheme_version: String,
    pub hash_function: String,
    pub program_hash: String,
    pub transformer_config_hash: String,
    pub deterministic_model_hash: String,
    pub stark_options_hash: String,
    pub prover_build_info: String,
    pub prover_build_hash: String,
}

pub const CLAIM_COMMITMENT_SCHEME_VERSION_V1: &str = "v1";
pub const CLAIM_COMMITMENT_HASH_FUNCTION_V1: &str = "blake2b-256";
pub const CLAIM_STATEMENT_VERSION_V1: &str = "statement-v1";
pub const CLAIM_SEMANTIC_SCOPE_V1: &str =
    "native_isa_execution_with_transformer_native_equivalence_check";
const COMMITMENT_PAYLOAD_VERSION_V1: &str = "v1";

#[cfg_attr(not(feature = "stwo-backend"), allow(dead_code))]
pub(crate) struct PreparedExecutionWitness {
    pub(crate) state_trace: Vec<MachineState>,
    pub(crate) claim: VanillaStarkExecutionClaim,
}

#[cfg(feature = "stwo-backend")]
fn prove_execution_stark_backend(
    witness: PreparedExecutionWitness,
) -> Result<VanillaStarkExecutionProof> {
    stwo_backend::prove_phase5_arithmetic_subset(witness)
}

#[cfg(not(feature = "stwo-backend"))]
fn prove_execution_stark_backend(
    _witness: PreparedExecutionWitness,
) -> Result<VanillaStarkExecutionProof> {
    Err(stwo_backend::phase2_placeholder_prove_error())
}

#[cfg(feature = "stwo-backend")]
fn verify_execution_stark_backend(
    proof: &VanillaStarkExecutionProof,
    _backend: StarkProofBackend,
) -> Result<bool> {
    stwo_backend::verify_phase5_arithmetic_subset(proof)
}

#[cfg(not(feature = "stwo-backend"))]
fn verify_execution_stark_backend(
    _proof: &VanillaStarkExecutionProof,
    _backend: StarkProofBackend,
) -> Result<bool> {
    Err(stwo_backend::phase2_placeholder_verify_error())
}

pub fn prove_execution_stark(
    model: &TransformerVm,
    max_steps: usize,
) -> Result<VanillaStarkExecutionProof> {
    prove_execution_stark_with_backend_and_options(
        model,
        max_steps,
        StarkProofBackend::Stwo,
        production_v1_stark_options(),
    )
}

pub fn prove_execution_stark_with_options(
    model: &TransformerVm,
    max_steps: usize,
    options: VanillaStarkProofOptions,
) -> Result<VanillaStarkExecutionProof> {
    prove_execution_stark_with_backend_and_options(
        model,
        max_steps,
        StarkProofBackend::Stwo,
        options,
    )
}

pub fn prove_execution_stark_with_backend_and_options(
    model: &TransformerVm,
    max_steps: usize,
    backend: StarkProofBackend,
    options: VanillaStarkProofOptions,
) -> Result<VanillaStarkExecutionProof> {
    validate_proof_inputs(model.program(), &model.config().attention_mode, backend)?;
    validate_stark_options(&options)?;
    let witness = prepare_execution_witness(model, max_steps, options)?;
    prove_execution_stark_backend(witness)
}

pub fn verify_execution_stark(proof: &VanillaStarkExecutionProof) -> Result<bool> {
    verify_execution_stark_with_policy(proof, production_v1_verification_policy())
}

pub fn verify_execution_stark_with_policy(
    proof: &VanillaStarkExecutionProof,
    policy: StarkVerificationPolicy,
) -> Result<bool> {
    verify_execution_stark_with_backend_and_policy(proof, proof.proof_backend, policy)
}

pub fn verify_execution_stark_claim_only(proof: &VanillaStarkExecutionProof) -> Result<bool> {
    verify_execution_stark_claim_only_with_policy(proof, production_v1_verification_policy())
}

pub fn verify_execution_stark_claim_only_with_policy(
    proof: &VanillaStarkExecutionProof,
    policy: StarkVerificationPolicy,
) -> Result<bool> {
    verify_execution_stark_with_backend_and_policy(proof, proof.proof_backend, policy)
}

pub fn verify_execution_stark_with_backend_and_policy(
    proof: &VanillaStarkExecutionProof,
    backend: StarkProofBackend,
    policy: StarkVerificationPolicy,
) -> Result<bool> {
    verify_execution_stark_with_backend_policy_and_mode(
        proof,
        backend,
        policy,
        StarkVerificationExecutionMode::ClaimOnly,
    )
}

fn verify_execution_stark_with_backend_policy_and_mode(
    proof: &VanillaStarkExecutionProof,
    backend: StarkProofBackend,
    policy: StarkVerificationPolicy,
    execution_mode: StarkVerificationExecutionMode,
) -> Result<bool> {
    validate_backend_metadata(proof, backend)?;
    validate_statement_metadata(&proof.claim)?;
    validate_proof_inputs(&proof.claim.program, &proof.claim.attention_mode, backend)?;
    validate_stark_options(&proof.claim.options)?;
    validate_verification_policy(&proof.claim.options, &policy)?;
    validate_public_state(&proof.claim.program, &proof.claim.final_state)?;
    validate_transformer_config(&proof.claim)?;
    validate_equivalence_metadata(&proof.claim)?;
    validate_claim_commitments(&proof.claim)?;

    if !proof.claim.final_state.halted {
        return Err(VmError::UnsupportedProof(
            "the public claim must end in a halted state".to_string(),
        ));
    }
    if proof.claim.final_state.carry_flag {
        return Err(VmError::UnsupportedProof(
            "carry-flag claims are not supported by the current execution-proof surface"
                .to_string(),
        ));
    }

    let is_valid = verify_execution_stark_backend(proof, backend)?;
    if !is_valid {
        return Ok(false);
    }

    if matches!(execution_mode, StarkVerificationExecutionMode::Reexecute) {
        enforce_equivalence_scope(&proof.claim)?;
    }
    Ok(true)
}

pub fn verify_execution_stark_with_reexecution(proof: &VanillaStarkExecutionProof) -> Result<bool> {
    verify_execution_stark_with_reexecution_and_policy(proof, production_v1_verification_policy())
}

pub fn verify_execution_stark_with_reexecution_and_policy(
    proof: &VanillaStarkExecutionProof,
    policy: StarkVerificationPolicy,
) -> Result<bool> {
    verify_execution_stark_with_backend_policy_and_mode(
        proof,
        proof.proof_backend,
        policy,
        StarkVerificationExecutionMode::Reexecute,
    )
}

pub(crate) fn validate_execution_stark_support(
    program: &Program,
    attention_mode: &Attention2DMode,
) -> Result<()> {
    validate_proof_inputs(program, attention_mode, StarkProofBackend::Stwo)
}

pub fn save_execution_stark_proof(proof: &VanillaStarkExecutionProof, path: &Path) -> Result<()> {
    let bytes =
        serde_json::to_vec_pretty(proof).map_err(|err| VmError::Serialization(err.to_string()))?;
    fs::write(path, bytes)?;
    Ok(())
}

pub fn load_execution_stark_proof(path: &Path) -> Result<VanillaStarkExecutionProof> {
    let bytes = fs::read(path)?;
    serde_json::from_slice(&bytes).map_err(|err| VmError::Serialization(err.to_string()))
}

pub fn load_execution_stark_proof_with_limit(
    path: &Path,
    max_bytes: usize,
) -> Result<VanillaStarkExecutionProof> {
    let max_bytes_u64 = u64::try_from(max_bytes).map_err(|_| {
        VmError::InvalidConfig("execution proof byte limit does not fit in u64".to_string())
    })?;
    let file = fs::File::open(path)?;
    let metadata_len = file.metadata()?.len();
    if metadata_len > max_bytes_u64 {
        return Err(VmError::InvalidConfig(format!(
            "execution proof file `{}` exceeds the {} byte limit",
            path.display(),
            max_bytes
        )));
    }
    let mut bytes = Vec::with_capacity((metadata_len.min(max_bytes_u64)) as usize);
    let mut limited_reader = file.take(max_bytes_u64.saturating_add(1));
    limited_reader.read_to_end(&mut bytes)?;
    if bytes.len() > max_bytes {
        return Err(VmError::InvalidConfig(format!(
            "execution proof file `{}` exceeds the {} byte limit while reading",
            path.display(),
            max_bytes
        )));
    }
    serde_json::from_slice(&bytes).map_err(|err| VmError::Serialization(err.to_string()))
}

pub fn conjectured_security_bits(options: &VanillaStarkProofOptions) -> u32 {
    if options.expansion_factor == 0 || options.num_colinearity_checks == 0 {
        return 0;
    }
    let query_bits = (options.expansion_factor.trailing_zeros() as u64)
        .saturating_mul(options.num_colinearity_checks as u64);
    query_bits.min(STARK_FIELD_SECURITY_BITS as u64) as u32
}

fn validate_stark_options(options: &VanillaStarkProofOptions) -> Result<()> {
    if !options.expansion_factor.is_power_of_two() {
        return Err(VmError::InvalidConfig(format!(
            "stark expansion_factor must be a power of two, got {}",
            options.expansion_factor
        )));
    }
    if options.expansion_factor < 4 {
        return Err(VmError::InvalidConfig(format!(
            "stark expansion_factor must be at least 4, got {}",
            options.expansion_factor
        )));
    }
    if options.expansion_factor > MAX_STARK_EXPANSION_FACTOR {
        return Err(VmError::InvalidConfig(format!(
            "stark expansion_factor {} exceeds verifier cap {}",
            options.expansion_factor, MAX_STARK_EXPANSION_FACTOR
        )));
    }
    if options.num_colinearity_checks == 0 {
        return Err(VmError::InvalidConfig(
            "stark num_colinearity_checks must be greater than zero".to_string(),
        ));
    }
    if options.num_colinearity_checks > MAX_STARK_NUM_COLINEARITY_CHECKS {
        return Err(VmError::InvalidConfig(format!(
            "stark num_colinearity_checks {} exceeds verifier cap {}",
            options.num_colinearity_checks, MAX_STARK_NUM_COLINEARITY_CHECKS
        )));
    }
    if options.security_level == 0 {
        return Err(VmError::InvalidConfig(
            "stark security_level must be greater than zero".to_string(),
        ));
    }
    let lhs = options
        .num_colinearity_checks
        .checked_mul(2)
        .ok_or_else(|| {
            VmError::InvalidConfig("stark option multiplication overflow".to_string())
        })?;
    if lhs < options.security_level {
        return Err(VmError::InvalidConfig(format!(
            "stark num_colinearity_checks={} does not satisfy 2*q >= security_level={}",
            options.num_colinearity_checks, options.security_level
        )));
    }
    if options.security_level > STARK_FIELD_SECURITY_BITS as usize {
        return Err(VmError::InvalidConfig(format!(
            "stark security_level {} exceeds field bound {}",
            options.security_level, STARK_FIELD_SECURITY_BITS
        )));
    }
    Ok(())
}

fn validate_verification_policy(
    options: &VanillaStarkProofOptions,
    policy: &StarkVerificationPolicy,
) -> Result<()> {
    let bits = conjectured_security_bits(options);
    if bits < policy.min_conjectured_security_bits {
        return Err(VmError::InvalidConfig(format!(
            "conjectured security {} bits is below required {} bits",
            bits, policy.min_conjectured_security_bits
        )));
    }
    Ok(())
}

fn prepare_execution_witness(
    model: &TransformerVm,
    max_steps: usize,
    options: VanillaStarkProofOptions,
) -> Result<PreparedExecutionWitness> {
    let comparison = verify_model_against_native(model.clone(), max_steps)?;
    let equivalence = ExecutionEquivalenceMetadata {
        checked_steps: comparison.checked_steps,
        transformer_fingerprint: execution_fingerprint_from_result(
            "transformer",
            comparison.checked_steps,
            &comparison.transformer,
        ),
        native_fingerprint: execution_fingerprint_from_result(
            "native",
            comparison.checked_steps,
            &comparison.native,
        ),
    };

    let mut runtime = ExecutionRuntime::new(model.clone(), max_steps);
    let result = runtime.run()?;
    if !result.halted {
        return Err(VmError::UnsupportedProof(format!(
            "execution must halt before proving; stopped after {} steps without HALT",
            result.steps
        )));
    }
    if runtime.trace().iter().any(|state| state.carry_flag) {
        return Err(VmError::UnsupportedProof(
            "overflowing arithmetic is not supported by the current execution-proof surface"
                .to_string(),
        ));
    }

    let commitments = build_claim_commitments(model.program(), model.config(), &options)?;
    let claim = VanillaStarkExecutionClaim {
        statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
        semantic_scope: CLAIM_SEMANTIC_SCOPE_V1.to_string(),
        program: model.program().clone(),
        attention_mode: model.config().attention_mode.clone(),
        transformer_config: Some(model.config().clone()),
        steps: result.steps,
        final_state: result.final_state.clone(),
        options,
        equivalence: Some(equivalence),
        commitments: Some(commitments),
    };

    Ok(PreparedExecutionWitness {
        state_trace: runtime.trace().to_vec(),
        claim,
    })
}

fn validate_backend_metadata(
    proof: &VanillaStarkExecutionProof,
    requested_backend: StarkProofBackend,
) -> Result<()> {
    if proof.proof_backend != requested_backend {
        return Err(VmError::InvalidConfig(format!(
            "proof backend `{}` does not match requested backend `{}`",
            proof.proof_backend, requested_backend
        )));
    }

    let backend_version_matches = proof.proof_backend_version
        == stwo_backend::STWO_BACKEND_VERSION_PHASE2
        || proof.proof_backend_version == stwo_backend::STWO_BACKEND_VERSION_PHASE5
        || proof.proof_backend_version == stwo_backend::STWO_BACKEND_VERSION_PHASE5_LEGACY
        || proof.proof_backend_version == stwo_backend::STWO_BACKEND_VERSION_PHASE11
        || proof.proof_backend_version == stwo_backend::STWO_BACKEND_VERSION_PHASE12;
    if !backend_version_matches {
        let expected_versions = format!(
            "{}/{}/{}/{}/{}",
            stwo_backend::STWO_BACKEND_VERSION_PHASE2,
            stwo_backend::STWO_BACKEND_VERSION_PHASE5,
            stwo_backend::STWO_BACKEND_VERSION_PHASE5_LEGACY,
            stwo_backend::STWO_BACKEND_VERSION_PHASE11,
            stwo_backend::STWO_BACKEND_VERSION_PHASE12
        );
        return Err(VmError::InvalidConfig(format!(
            "proof backend version `{}` does not match expected `{}` for backend `{}`",
            proof.proof_backend_version, expected_versions, requested_backend
        )));
    }

    Ok(())
}

fn validate_proof_inputs(
    program: &Program,
    attention_mode: &Attention2DMode,
    backend: StarkProofBackend,
) -> Result<()> {
    if program.is_empty() {
        return Err(VmError::UnsupportedProof(
            "cannot prove an empty program".to_string(),
        ));
    }

    let _ = backend;
    stwo_backend::validate_phase2_proof_shape(program, attention_mode)?;

    Ok(())
}

fn validate_public_state(program: &Program, final_state: &MachineState) -> Result<()> {
    if final_state.memory.len() != program.memory_size() {
        return Err(VmError::InvalidConfig(format!(
            "proof final-state memory length {} does not match program memory size {}",
            final_state.memory.len(),
            program.memory_size()
        )));
    }
    Ok(())
}

fn validate_statement_metadata(claim: &VanillaStarkExecutionClaim) -> Result<()> {
    if claim.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported statement_version `{}` (expected `{}`)",
            claim.statement_version, CLAIM_STATEMENT_VERSION_V1
        )));
    }
    if claim.semantic_scope != CLAIM_SEMANTIC_SCOPE_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported semantic_scope `{}` (expected `{}`)",
            claim.semantic_scope, CLAIM_SEMANTIC_SCOPE_V1
        )));
    }
    let commitments = claim.commitments.as_ref().ok_or_else(|| {
        VmError::UnsupportedProof("proof claim is missing artifact commitments".to_string())
    })?;
    if commitments.scheme_version != CLAIM_COMMITMENT_SCHEME_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported commitment_scheme_version `{}` (expected `{}`)",
            commitments.scheme_version, CLAIM_COMMITMENT_SCHEME_VERSION_V1
        )));
    }
    if commitments.hash_function != CLAIM_COMMITMENT_HASH_FUNCTION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported commitment_hash_function `{}` (expected `{}`)",
            commitments.hash_function, CLAIM_COMMITMENT_HASH_FUNCTION_V1
        )));
    }
    Ok(())
}

fn enforce_equivalence_scope(claim: &VanillaStarkExecutionClaim) -> Result<()> {
    if claim.semantic_scope != CLAIM_SEMANTIC_SCOPE_V1 {
        return Ok(());
    }
    if claim.equivalence.is_none() {
        return Err(VmError::UnsupportedProof(
            "proof claim is missing equivalence metadata required for re-execution verification"
                .to_string(),
        ));
    }

    let config = claim.transformer_config.clone().ok_or_else(|| {
        VmError::UnsupportedProof(
            "proof claim is missing transformer configuration for equivalence re-execution"
                .to_string(),
        )
    })?;
    let model = TransformerVm::new(config, claim.program.clone())?;
    let comparison = verify_model_against_native(model, claim.steps)?;
    validate_reexecution_matches_claim(claim, &comparison)?;
    Ok(())
}

fn validate_transformer_config(claim: &VanillaStarkExecutionClaim) -> Result<()> {
    let Some(config) = &claim.transformer_config else {
        // Claim-drift guard: the `statement-v1` semantic scope requires a
        // transformer config so the verifier can re-execute the transformer side
        // and bind the equivalence fingerprint. Reject any v1-scoped claim that
        // drops it.
        if claim.semantic_scope == CLAIM_SEMANTIC_SCOPE_V1 {
            return Err(VmError::UnsupportedProof(
                "proof claim uses statement-v1 semantic scope but is missing the transformer \
                 configuration required by that scope; reject as claim-drift"
                    .to_string(),
            ));
        }
        return Ok(());
    };

    config.validate()?;
    if config.attention_mode != claim.attention_mode {
        return Err(VmError::InvalidConfig(format!(
            "proof transformer config attention mode `{}` does not match claim attention mode `{}`",
            config.attention_mode, claim.attention_mode
        )));
    }
    Ok(())
}

fn validate_reexecution_matches_claim(
    claim: &VanillaStarkExecutionClaim,
    comparison: &crate::verification::ExecutionComparison,
) -> Result<()> {
    if comparison.checked_steps != claim.steps {
        return Err(VmError::InvalidConfig(format!(
            "re-execution checked_steps {} does not match claim steps {}",
            comparison.checked_steps, claim.steps
        )));
    }

    for (engine, result) in [
        ("transformer", &comparison.transformer),
        ("native", &comparison.native),
    ] {
        if result.steps != claim.steps {
            return Err(VmError::InvalidConfig(format!(
                "re-executed {engine} steps {} does not match claim steps {}",
                result.steps, claim.steps
            )));
        }
        if result.halted != claim.final_state.halted {
            return Err(VmError::InvalidConfig(format!(
                "re-executed {engine} halted={} does not match claim halted={}",
                result.halted, claim.final_state.halted
            )));
        }
        if result.final_state != claim.final_state {
            return Err(VmError::InvalidConfig(format!(
                "re-executed {engine} final state does not match claim final state"
            )));
        }
    }

    if let Some(metadata) = &claim.equivalence {
        if metadata.checked_steps != comparison.checked_steps {
            return Err(VmError::InvalidConfig(format!(
                "equivalence checked_steps {} does not match re-execution checked_steps {}",
                metadata.checked_steps, comparison.checked_steps
            )));
        }

        let transformer_fingerprint = execution_fingerprint_from_result(
            "transformer",
            comparison.checked_steps,
            &comparison.transformer,
        );
        if metadata.transformer_fingerprint != transformer_fingerprint {
            return Err(VmError::InvalidConfig(
                "transformer fingerprint does not match re-execution".to_string(),
            ));
        }

        let native_fingerprint = execution_fingerprint_from_result(
            "native",
            comparison.checked_steps,
            &comparison.native,
        );
        if metadata.native_fingerprint != native_fingerprint {
            return Err(VmError::InvalidConfig(
                "native fingerprint does not match re-execution".to_string(),
            ));
        }
    }

    Ok(())
}

fn validate_equivalence_metadata(claim: &VanillaStarkExecutionClaim) -> Result<()> {
    // Claim-drift guard: the `statement-v1` semantic scope literally names a
    // transformer/native equivalence check, so any claim under that scope must
    // carry equivalence metadata. Without this guard, a JSON proof could keep
    // the scope label while dropping the metadata and pass the claim-only path.
    let Some(metadata) = &claim.equivalence else {
        if claim.semantic_scope == CLAIM_SEMANTIC_SCOPE_V1 {
            return Err(VmError::UnsupportedProof(
                "proof claim uses statement-v1 semantic scope but is missing the equivalence \
                 metadata required by that scope; reject as claim-drift"
                    .to_string(),
            ));
        }
        return Ok(());
    };

    if metadata.checked_steps != claim.steps {
        return Err(VmError::InvalidConfig(format!(
            "equivalence checked_steps {} does not match claim steps {}",
            metadata.checked_steps, claim.steps
        )));
    }

    let expected_transformer = execution_fingerprint(
        "transformer",
        metadata.checked_steps,
        claim.steps,
        claim.final_state.halted,
        &claim.final_state,
    );
    if metadata.transformer_fingerprint != expected_transformer {
        return Err(VmError::InvalidConfig(
            "invalid transformer equivalence fingerprint".to_string(),
        ));
    }

    let expected_native = execution_fingerprint(
        "native",
        metadata.checked_steps,
        claim.steps,
        claim.final_state.halted,
        &claim.final_state,
    );
    if metadata.native_fingerprint != expected_native {
        return Err(VmError::InvalidConfig(
            "invalid native equivalence fingerprint".to_string(),
        ));
    }

    Ok(())
}

fn validate_claim_commitments(claim: &VanillaStarkExecutionClaim) -> Result<()> {
    let commitments = claim.commitments.as_ref().ok_or_else(|| {
        VmError::UnsupportedProof("proof claim is missing artifact commitments".to_string())
    })?;
    let config = claim.transformer_config.as_ref().ok_or_else(|| {
        VmError::UnsupportedProof(
            "proof claim is missing transformer configuration required for commitment checks"
                .to_string(),
        )
    })?;

    if commitments.scheme_version != CLAIM_COMMITMENT_SCHEME_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported commitment scheme version `{}` (expected `{}`)",
            commitments.scheme_version, CLAIM_COMMITMENT_SCHEME_VERSION_V1
        )));
    }
    if commitments.hash_function != CLAIM_COMMITMENT_HASH_FUNCTION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported commitment hash function `{}` (expected `{}`)",
            commitments.hash_function, CLAIM_COMMITMENT_HASH_FUNCTION_V1
        )));
    }
    if commitments.prover_build_info.trim().is_empty() {
        return Err(VmError::InvalidConfig(
            "invalid prover_build_info commitment: value is empty".to_string(),
        ));
    }

    let expected_program_hash = hash_serialized_payload_hex(
        "program",
        &ProgramCommitmentPayloadV1 {
            version: COMMITMENT_PAYLOAD_VERSION_V1,
            program: &claim.program,
        },
    )?;
    let expected_config_hash = hash_serialized_payload_hex(
        "transformer config",
        &TransformerConfigCommitmentPayloadV1 {
            version: COMMITMENT_PAYLOAD_VERSION_V1,
            transformer_config: config,
        },
    )?;
    let expected_model_hash = hash_serialized_payload_hex(
        "deterministic model",
        &DeterministicModelCommitmentPayloadV1 {
            version: COMMITMENT_PAYLOAD_VERSION_V1,
            program: &claim.program,
            transformer_config: config,
        },
    )?;
    let expected_options_hash = hash_serialized_payload_hex(
        "stark options",
        &StarkOptionsCommitmentPayloadV1 {
            version: COMMITMENT_PAYLOAD_VERSION_V1,
            stark_options: &claim.options,
        },
    )?;
    let expected_build_hash = hash_bytes_hex(commitments.prover_build_info.as_bytes());

    validate_commitment_field(
        "program_hash",
        &commitments.program_hash,
        &expected_program_hash,
    )?;
    validate_commitment_field(
        "transformer_config_hash",
        &commitments.transformer_config_hash,
        &expected_config_hash,
    )?;
    validate_commitment_field(
        "deterministic_model_hash",
        &commitments.deterministic_model_hash,
        &expected_model_hash,
    )?;
    validate_commitment_field(
        "stark_options_hash",
        &commitments.stark_options_hash,
        &expected_options_hash,
    )?;
    validate_commitment_field(
        "prover_build_hash",
        &commitments.prover_build_hash,
        &expected_build_hash,
    )?;

    Ok(())
}

fn validate_commitment_field(name: &str, actual: &str, expected: &str) -> Result<()> {
    if actual != expected {
        return Err(VmError::InvalidConfig(format!(
            "invalid {name} commitment: expected {expected}, got {actual}"
        )));
    }
    Ok(())
}

fn build_claim_commitments(
    program: &Program,
    config: &TransformerVmConfig,
    options: &VanillaStarkProofOptions,
) -> Result<ExecutionClaimCommitments> {
    let prover_build_info = prover_build_info();
    let prover_build_hash = hash_bytes_hex(prover_build_info.as_bytes());

    let program_hash = hash_serialized_payload_hex(
        "program",
        &ProgramCommitmentPayloadV1 {
            version: COMMITMENT_PAYLOAD_VERSION_V1,
            program,
        },
    )?;
    let transformer_config_hash = hash_serialized_payload_hex(
        "transformer config",
        &TransformerConfigCommitmentPayloadV1 {
            version: COMMITMENT_PAYLOAD_VERSION_V1,
            transformer_config: config,
        },
    )?;
    let deterministic_model_hash = hash_serialized_payload_hex(
        "deterministic model",
        &DeterministicModelCommitmentPayloadV1 {
            version: COMMITMENT_PAYLOAD_VERSION_V1,
            program,
            transformer_config: config,
        },
    )?;
    let stark_options_hash = hash_serialized_payload_hex(
        "stark options",
        &StarkOptionsCommitmentPayloadV1 {
            version: COMMITMENT_PAYLOAD_VERSION_V1,
            stark_options: options,
        },
    )?;

    Ok(ExecutionClaimCommitments {
        scheme_version: CLAIM_COMMITMENT_SCHEME_VERSION_V1.to_string(),
        hash_function: CLAIM_COMMITMENT_HASH_FUNCTION_V1.to_string(),
        program_hash,
        transformer_config_hash,
        deterministic_model_hash,
        stark_options_hash,
        prover_build_info,
        prover_build_hash,
    })
}

fn prover_build_info() -> String {
    let version = env!("CARGO_PKG_VERSION");
    let git_commit = option_env!("LLM_PC_GIT_COMMIT").unwrap_or("unknown");
    format!("llm-provable-computer/{version}+{git_commit}")
}

fn hash_serialized_payload_hex<T: Serialize>(label: &str, value: &T) -> Result<String> {
    let payload = canonical_json_bytes(label, value)?;
    Ok(hash_bytes_hex(&payload))
}

fn canonical_json_bytes<T: Serialize>(label: &str, value: &T) -> Result<Vec<u8>> {
    let json = serde_json::to_value(value)
        .map_err(|err| VmError::Serialization(format!("{label}: {err}")))?;
    let mut out = Vec::new();
    write_canonical_json_value(&json, &mut out)
        .map_err(|err| VmError::Serialization(format!("{label}: {err}")))?;
    Ok(out)
}

fn write_canonical_json_value(
    value: &Value,
    out: &mut Vec<u8>,
) -> std::result::Result<(), serde_json::Error> {
    match value {
        Value::Null => out.extend_from_slice(b"null"),
        Value::Bool(v) => out.extend_from_slice(if *v { b"true" } else { b"false" }),
        Value::Number(v) => out.extend_from_slice(v.to_string().as_bytes()),
        Value::String(v) => out.extend_from_slice(serde_json::to_string(v)?.as_bytes()),
        Value::Array(values) => {
            out.push(b'[');
            for (index, item) in values.iter().enumerate() {
                if index > 0 {
                    out.push(b',');
                }
                write_canonical_json_value(item, out)?;
            }
            out.push(b']');
        }
        Value::Object(map) => {
            out.push(b'{');
            let mut entries: Vec<_> = map.iter().collect();
            entries.sort_by(|(left, _), (right, _)| left.cmp(right));
            for (index, (key, item)) in entries.iter().enumerate() {
                if index > 0 {
                    out.push(b',');
                }
                out.extend_from_slice(serde_json::to_string(key)?.as_bytes());
                out.push(b':');
                write_canonical_json_value(item, out)?;
            }
            out.push(b'}');
        }
    }
    Ok(())
}

fn hash_bytes_hex(bytes: &[u8]) -> String {
    let mut output = [0u8; 32];
    let mut hasher = Blake2bVar::new(output.len()).expect("blake2b-256 hasher");
    hasher.update(bytes);
    hasher
        .finalize_variable(&mut output)
        .expect("blake2b-256 finalization");
    output.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[derive(Serialize)]
struct ProgramCommitmentPayloadV1<'a> {
    version: &'static str,
    program: &'a Program,
}

#[derive(Serialize)]
struct TransformerConfigCommitmentPayloadV1<'a> {
    version: &'static str,
    transformer_config: &'a TransformerVmConfig,
}

#[derive(Serialize)]
struct DeterministicModelCommitmentPayloadV1<'a> {
    version: &'static str,
    program: &'a Program,
    transformer_config: &'a TransformerVmConfig,
}

#[derive(Serialize)]
struct StarkOptionsCommitmentPayloadV1<'a> {
    version: &'static str,
    stark_options: &'a VanillaStarkProofOptions,
}

fn execution_fingerprint_from_result(
    engine: &str,
    checked_steps: usize,
    result: &ExecutionResult,
) -> String {
    execution_fingerprint(
        engine,
        checked_steps,
        result.steps,
        result.halted,
        &result.final_state,
    )
}

fn execution_fingerprint(
    engine: &str,
    checked_steps: usize,
    steps: usize,
    halted: bool,
    final_state: &MachineState,
) -> String {
    #[derive(Serialize)]
    struct FingerprintPayload<'a> {
        engine: &'a str,
        checked_steps: usize,
        steps: usize,
        halted: bool,
        final_state: &'a MachineState,
    }

    let payload = FingerprintPayload {
        engine,
        checked_steps,
        steps,
        halted,
        final_state,
    };
    let encoded = serde_json::to_vec(&payload).expect("fingerprint payload serialization");
    let digest = Blake2b512::digest(encoded);
    digest
        .as_slice()
        .iter()
        .take(8)
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ProgramCompiler, TransformerVmConfig};
    use serde::Deserialize;

    #[derive(Debug, Deserialize)]
    struct StatementSpecFile {
        statement_version: String,
        semantic_scope: String,
        commitment_scheme_version: String,
        commitment_hash_function: String,
    }

    fn prove_program(path: &str, max_steps: usize) -> VanillaStarkExecutionProof {
        let source = std::fs::read_to_string(path).expect("program source");
        let model = ProgramCompiler
            .compile_source(&source, TransformerVmConfig::default())
            .expect("compile");
        prove_execution_stark_with_options(&model, max_steps, production_v1_stark_options())
            .expect("prove")
    }

    #[test]
    fn addition_round_trips_through_stark_proof() {
        let proof = prove_program("programs/addition.tvm", 32);
        assert!(verify_execution_stark(&proof).expect("verify"));
        assert_eq!(proof.claim.final_state.acc, 8);
    }

    #[test]
    fn small_loop_is_rejected_by_current_stark_surface() {
        let source = "\
.memory 2
.init 1 2

LOADI 0
STORE 0
loop:
LOAD 0
ADD 1
STORE 0
LOAD 0
SUBM 1
JZ done
JMP loop
done:
LOAD 0
HALT
";
        let model = ProgramCompiler
            .compile_source(source, TransformerVmConfig::default())
            .expect("compile");
        let err = prove_execution_stark_with_options(&model, 128, production_v1_stark_options())
            .unwrap_err();
        assert!(matches!(err, VmError::UnsupportedProof(_)));
    }

    #[test]
    fn stack_and_subroutine_programs_are_rejected_by_current_stark_surface() {
        for (path, max_steps) in [
            ("programs/stack_roundtrip.tvm", 32),
            ("programs/subroutine_addition.tvm", 64),
        ] {
            let source = std::fs::read_to_string(path).expect("program source");
            let model = ProgramCompiler
                .compile_source(&source, TransformerVmConfig::default())
                .expect("compile");
            let err = prove_execution_stark_with_options(
                &model,
                max_steps,
                production_v1_stark_options(),
            )
            .unwrap_err();
            assert!(matches!(err, VmError::UnsupportedProof(_)), "{path}");
        }
    }

    #[test]
    fn proof_rejects_softmax_attention() {
        let source = std::fs::read_to_string("programs/addition.tvm").expect("program source");
        let model = ProgramCompiler
            .compile_source(
                &source,
                TransformerVmConfig {
                    attention_mode: Attention2DMode::Softmax,
                    ..TransformerVmConfig::default()
                },
            )
            .expect("compile");

        let err = prove_execution_stark(&model, 32).unwrap_err();
        assert!(matches!(err, VmError::UnsupportedProof(_)));
    }

    #[test]
    fn proof_rejects_unsupported_instruction_set() {
        let program = Program::new(vec![Instruction::CmpImmediate(1), Instruction::Halt], 1);
        let model = TransformerVm::new(TransformerVmConfig::default(), program).expect("model");
        let err = prove_execution_stark(&model, 16).unwrap_err();
        assert!(matches!(err, VmError::UnsupportedProof(_)));
    }

    #[test]
    fn proof_serialization_round_trip() {
        let proof = prove_program("programs/addition.tvm", 32);
        let path = std::env::temp_dir().join(format!(
            "llm-provable-computer-proof-{}.json",
            std::process::id()
        ));

        save_execution_stark_proof(&proof, &path).expect("save");
        let loaded = load_execution_stark_proof(&path).expect("load");
        let _ = std::fs::remove_file(&path);

        assert_eq!(loaded, proof);
        assert!(verify_execution_stark(&loaded).expect("verify"));
    }

    #[test]
    fn proof_serialization_backfills_stwo_backend_for_legacy_json() {
        let proof = prove_program("programs/addition.tvm", 32);
        let mut json = serde_json::to_value(&proof).expect("proof json");
        let object = json.as_object_mut().expect("proof object");
        object.remove("proof_backend");
        object.remove("proof_backend_version");

        let loaded: VanillaStarkExecutionProof =
            serde_json::from_value(json).expect("deserialize legacy proof");
        assert_eq!(loaded.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            loaded.proof_backend_version,
            stwo_backend::STWO_BACKEND_VERSION_PHASE5
        );
    }

    #[test]
    fn proof_claim_includes_equivalence_metadata() {
        let proof = prove_program("programs/addition.tvm", 32);
        assert_eq!(proof.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            proof.proof_backend_version,
            stwo_backend::STWO_BACKEND_VERSION_PHASE5
        );
        let metadata = proof.claim.equivalence.expect("equivalence metadata");
        assert_eq!(proof.claim.statement_version, CLAIM_STATEMENT_VERSION_V1);
        assert_eq!(proof.claim.semantic_scope, CLAIM_SEMANTIC_SCOPE_V1);
        assert_eq!(metadata.checked_steps, proof.claim.steps);
        let config = proof
            .claim
            .transformer_config
            .as_ref()
            .expect("transformer config");
        assert_eq!(config.attention_mode, proof.claim.attention_mode);
        assert_eq!(
            metadata.transformer_fingerprint,
            execution_fingerprint(
                "transformer",
                metadata.checked_steps,
                proof.claim.steps,
                proof.claim.final_state.halted,
                &proof.claim.final_state,
            )
        );
        assert_eq!(
            metadata.native_fingerprint,
            execution_fingerprint(
                "native",
                metadata.checked_steps,
                proof.claim.steps,
                proof.claim.final_state.halted,
                &proof.claim.final_state,
            )
        );
    }

    #[test]
    fn proof_claim_includes_artifact_commitments() {
        let proof = prove_program("programs/addition.tvm", 32);
        let commitments = proof
            .claim
            .commitments
            .as_ref()
            .expect("artifact commitments");
        assert_eq!(
            commitments.scheme_version,
            CLAIM_COMMITMENT_SCHEME_VERSION_V1
        );
        assert_eq!(commitments.hash_function, CLAIM_COMMITMENT_HASH_FUNCTION_V1);
        assert!(!commitments.prover_build_info.trim().is_empty());
        assert_eq!(
            commitments.prover_build_hash,
            hash_bytes_hex(commitments.prover_build_info.as_bytes())
        );

        let config = proof
            .claim
            .transformer_config
            .as_ref()
            .expect("transformer config");
        let expected = build_claim_commitments(&proof.claim.program, config, &proof.claim.options)
            .expect("rebuild commitments");
        assert_eq!(commitments.program_hash, expected.program_hash);
        assert_eq!(
            commitments.transformer_config_hash,
            expected.transformer_config_hash
        );
        assert_eq!(
            commitments.deterministic_model_hash,
            expected.deterministic_model_hash
        );
        assert_eq!(commitments.stark_options_hash, expected.stark_options_hash);
    }

    #[test]
    fn reexecution_verification_round_trips() {
        let proof = prove_program("programs/addition.tvm", 32);
        assert!(verify_execution_stark_with_reexecution(&proof).expect("verify with reexecution"));
    }

    #[test]
    fn claim_only_verification_does_not_reexecute_equivalence_metadata() {
        // A v1-scoped proof carrying equivalence metadata must verify on every
        // claim-only entry point without triggering the re-execution path.
        let proof = prove_program("programs/addition.tvm", 32);
        assert!(proof.claim.equivalence.is_some());

        assert!(verify_execution_stark_claim_only(&proof).expect("claim-only verify"));
        assert!(verify_execution_stark_with_backend_and_policy(
            &proof,
            proof.proof_backend,
            production_v1_verification_policy()
        )
        .expect("backend/policy claim-only verify"));
        assert!(verify_execution_stark(&proof).expect("default claim-only verify"));
        assert!(
            verify_execution_stark_with_policy(&proof, production_v1_verification_policy())
                .expect("policy claim-only verify")
        );
    }

    #[test]
    fn claim_only_verification_rejects_v1_scope_without_equivalence_metadata() {
        // Claim-drift guard: under the v1 scope, claim-only verification must
        // refuse a proof whose claim drops the equivalence metadata. Otherwise
        // the scope label outpromises what the claim actually carries.
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof.claim.equivalence = None;

        for verdict in [
            verify_execution_stark_claim_only(&proof),
            verify_execution_stark(&proof),
            verify_execution_stark_with_policy(&proof, production_v1_verification_policy()),
            verify_execution_stark_with_backend_and_policy(
                &proof,
                proof.proof_backend,
                production_v1_verification_policy(),
            ),
        ] {
            let err = verdict.expect_err("claim-only verify must reject");
            assert!(
                err.to_string().contains("missing the equivalence metadata"),
                "expected claim-drift rejection, got: {err}"
            );
        }

        let err = verify_execution_stark_with_reexecution(&proof)
            .expect_err("re-execution path must also reject");
        assert!(err.to_string().contains("missing the equivalence metadata"));
    }

    #[test]
    fn policy_rejects_low_security_proof_options() {
        let source = std::fs::read_to_string("programs/addition.tvm").expect("program source");
        let model = ProgramCompiler
            .compile_source(&source, TransformerVmConfig::default())
            .expect("compile");
        let proof = prove_execution_stark_with_options(
            &model,
            32,
            VanillaStarkProofOptions {
                expansion_factor: 4,
                num_colinearity_checks: 2,
                security_level: 2,
            },
        )
        .expect("prove");
        let err = verify_execution_stark_with_policy(
            &proof,
            StarkVerificationPolicy {
                min_conjectured_security_bits: 8,
            },
        )
        .unwrap_err();
        assert!(err
            .to_string()
            .contains("conjectured security 4 bits is below required 8 bits"));
    }

    #[test]
    fn verify_rejects_invalid_stark_options_without_panic() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof.claim.options.expansion_factor = 3;
        let err = verify_execution_stark(&proof).unwrap_err();
        assert!(err.to_string().contains("power of two"));
    }

    #[test]
    fn verify_rejects_step_overflow_without_panic() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof.claim.steps = usize::MAX;
        let metadata = proof
            .claim
            .equivalence
            .as_mut()
            .expect("equivalence metadata");
        metadata.checked_steps = usize::MAX;
        metadata.transformer_fingerprint = execution_fingerprint(
            "transformer",
            usize::MAX,
            usize::MAX,
            proof.claim.final_state.halted,
            &proof.claim.final_state,
        );
        metadata.native_fingerprint = execution_fingerprint(
            "native",
            usize::MAX,
            usize::MAX,
            proof.claim.final_state.halted,
            &proof.claim.final_state,
        );
        let err = verify_execution_stark(&proof).unwrap_err();
        let msg = err.to_string();
        assert!(
            msg.contains("proof steps overflow")
                || msg.contains("does not match claim steps")
                || msg.contains("expected 18446744073709551615"),
            "expected overflow or step-mismatch rejection, got: {msg}"
        );
    }

    #[test]
    fn verify_rejects_randomizer_overflow_without_panic() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof.claim.options.num_colinearity_checks = usize::MAX / 4 + 1;
        proof.claim.options.security_level = 8;
        let config = proof
            .claim
            .transformer_config
            .as_ref()
            .expect("transformer config")
            .clone();
        proof.claim.commitments = Some(
            build_claim_commitments(&proof.claim.program, &config, &proof.claim.options)
                .expect("rebuild commitments"),
        );
        let err = verify_execution_stark(&proof).unwrap_err();
        assert!(
            err.to_string().contains("randomizers")
                || err.to_string().contains("num_colinearity_checks")
                    && err.to_string().contains("verifier cap"),
            "expected randomizer-overflow rejection, got: {err}"
        );
    }

    #[test]
    fn verify_rejects_excessive_colinearity_checks_without_panic() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof.claim.options.num_colinearity_checks = MAX_STARK_NUM_COLINEARITY_CHECKS + 1;
        proof.claim.options.security_level = 8;
        let config = proof
            .claim
            .transformer_config
            .as_ref()
            .expect("transformer config")
            .clone();
        proof.claim.commitments = Some(
            build_claim_commitments(&proof.claim.program, &config, &proof.claim.options)
                .expect("rebuild commitments"),
        );
        let err = verify_execution_stark(&proof).unwrap_err();
        assert!(
            err.to_string().contains("num_colinearity_checks")
                && err.to_string().contains("verifier cap"),
            "expected verifier-cap rejection, got: {err}"
        );
    }

    #[test]
    fn verify_rejects_commitment_mismatch() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        let commitments = proof
            .claim
            .commitments
            .as_mut()
            .expect("artifact commitments");
        commitments.stark_options_hash = "00".repeat(32);
        let err = verify_execution_stark(&proof).unwrap_err();
        assert!(err
            .to_string()
            .contains("invalid stark_options_hash commitment"));
    }

    #[test]
    fn verify_rejects_statement_scope_mismatch() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof.claim.semantic_scope = "native_isa_execution_only".to_string();
        let err = verify_execution_stark(&proof).unwrap_err();
        assert!(err.to_string().contains("unsupported semantic_scope"));
    }

    #[test]
    fn verify_rejects_commitment_scheme_version_mismatch() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof
            .claim
            .commitments
            .as_mut()
            .expect("artifact commitments")
            .scheme_version = "v2".to_string();
        let err = verify_execution_stark(&proof).unwrap_err();
        assert!(err
            .to_string()
            .contains("unsupported commitment_scheme_version"));
    }

    #[test]
    fn verify_rejects_commitment_hash_function_mismatch() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof
            .claim
            .commitments
            .as_mut()
            .expect("artifact commitments")
            .hash_function = "sha256".to_string();
        let err = verify_execution_stark(&proof).unwrap_err();
        assert!(err
            .to_string()
            .contains("unsupported commitment_hash_function"));
    }

    #[test]
    fn production_profile_v1_is_self_consistent() {
        let options = production_v1_stark_options();
        assert_eq!(
            conjectured_security_bits(&options),
            PRODUCTION_V1_MIN_CONJECTURED_SECURITY_BITS
        );
        assert!(options.num_colinearity_checks.saturating_mul(2) >= options.security_level);
        assert!(PRODUCTION_V1_TARGET_MAX_PROVING_SECONDS > 0);
    }

    #[test]
    fn publication_profile_v1_meets_min_conjectured_security_floor() {
        let options = publication_v1_stark_options();
        assert!(
            conjectured_security_bits(&options) >= PUBLICATION_V1_MIN_CONJECTURED_SECURITY_BITS,
            "publication-v1 must clear its declared conjectured-security floor"
        );
        assert!(options.num_colinearity_checks.saturating_mul(2) >= options.security_level);
        // Publication-grade is meaningfully stronger than the CI smoke profile.
        assert!(
            conjectured_security_bits(&options)
                >= conjectured_security_bits(&production_v1_stark_options()) + 32
        );
    }

    #[test]
    fn publication_profile_v1_is_validated_by_strict_policy() {
        let options = publication_v1_stark_options();
        validate_stark_options(&options).expect("publication-v1 options validate");
        validate_verification_policy(&options, &StarkVerificationPolicy::strict())
            .expect("publication-v1 clears strict-policy floor");
    }

    #[test]
    fn verify_rejects_v1_claim_missing_equivalence_metadata() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof.claim.equivalence = None;
        let err = verify_execution_stark(&proof).unwrap_err();
        let msg = err.to_string();
        assert!(
            msg.contains("missing the equivalence metadata"),
            "expected claim-drift rejection, got: {msg}"
        );
    }

    #[test]
    fn verify_rejects_v1_claim_missing_transformer_config() {
        let mut proof = prove_program("programs/addition.tvm", 32);
        proof.claim.transformer_config = None;
        let err = verify_execution_stark(&proof).unwrap_err();
        let msg = err.to_string();
        assert!(
            msg.contains("missing the transformer configuration"),
            "expected claim-drift rejection, got: {msg}"
        );
    }

    #[test]
    fn statement_spec_contract_is_synced_with_constants() {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("spec")
            .join("statement-v1.json");
        let bytes = std::fs::read(&path).expect("read statement spec");
        let spec: StatementSpecFile = serde_json::from_slice(&bytes).expect("parse statement spec");

        assert_eq!(spec.statement_version, CLAIM_STATEMENT_VERSION_V1);
        assert_eq!(spec.semantic_scope, CLAIM_SEMANTIC_SCOPE_V1);
        assert_eq!(
            spec.commitment_scheme_version,
            CLAIM_COMMITMENT_SCHEME_VERSION_V1
        );
        assert_eq!(
            spec.commitment_hash_function,
            CLAIM_COMMITMENT_HASH_FUNCTION_V1
        );
    }

    #[test]
    fn commitment_hash_matches_blake2b_256_test_vector() {
        assert_eq!(
            hash_bytes_hex(b""),
            "0e5751c026e543b2e8ab2eb06099daa1d1e5df47778f7787faab45cdf12fe3a8"
        );
    }

    #[test]
    fn conjectured_security_bits_handles_large_query_counts() {
        let options = VanillaStarkProofOptions {
            expansion_factor: 1 << 63,
            num_colinearity_checks: usize::MAX,
            security_level: 1,
        };
        assert_eq!(
            conjectured_security_bits(&options),
            STARK_FIELD_SECURITY_BITS
        );
    }

    #[test]
    fn canonical_json_hash_is_key_order_invariant() {
        let ordered = serde_json::json!({
            "a": 1,
            "b": {
                "x": true,
                "y": [2, 3]
            }
        });

        let mut inner = serde_json::Map::new();
        inner.insert("y".to_string(), serde_json::json!([2, 3]));
        inner.insert("x".to_string(), serde_json::json!(true));
        let mut outer = serde_json::Map::new();
        outer.insert("b".to_string(), Value::Object(inner));
        outer.insert("a".to_string(), serde_json::json!(1));
        let reordered = Value::Object(outer);

        let ordered_hash = hash_serialized_payload_hex("ordered", &ordered).expect("hash ordered");
        let reordered_hash =
            hash_serialized_payload_hex("reordered", &reordered).expect("hash reordered");
        assert_eq!(ordered_hash, reordered_hash);
    }
}
