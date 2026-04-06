use ark_ff::Zero;
use serde::{Deserialize, Serialize};
use serde_json;
use std::fs;
use std::path::Path;
use stwo::core::air::Component;
use stwo::core::channel::Blake2sM31Channel;
use stwo::core::channel::Channel;
use stwo::core::fields::m31::BaseField;
use stwo::core::fields::qm31::SecureField;
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig};
use stwo::core::poly::circle::CanonicCoset;
use stwo::core::proof::StarkProof;
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sM31MerkleChannel, Blake2sM31MerkleHasher};
use stwo::core::verifier::verify;
use stwo::core::ColumnVec;
use stwo::prover::backend::simd::column::BaseColumn;
use stwo::prover::backend::simd::m31::LOG_N_LANES;
use stwo::prover::backend::simd::qm31::PackedSecureField;
use stwo::prover::backend::simd::SimdBackend;
use stwo::prover::poly::circle::{CircleEvaluation, PolyOps};
use stwo::prover::poly::{BitReversedOrder, NaturalOrder};
use stwo::prover::{prove, CommitmentSchemeProver};
use stwo_constraint_framework::{LogupTraceGenerator, Relation};

use super::normalization_component::{
    phase5_normalization_component, phase5_normalization_table_rows,
    Phase5NormalizationLookupElements,
};
use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

pub const STWO_NORMALIZATION_PROOF_VERSION_PHASE5: &str = "stwo-phase5-normalization-demo-v1";
pub const STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5: &str = "stwo-normalization-demo-v1";
pub const STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5: &str =
    "stwo_normalization_lookup_demo_with_canonical_table";

#[derive(Serialize, Deserialize)]
struct Phase5NormalizationProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_table_rows: Vec<(u16, u16)>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase5NormalizationLookupProofEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub canonical_table_rows: Vec<(u16, u16)>,
    pub proof: Vec<u8>,
}

pub fn prove_phase5_normalization_lookup_demo_envelope(
) -> Result<Phase5NormalizationLookupProofEnvelope> {
    let bundle = build_normalization_demo_bundle();
    Ok(Phase5NormalizationLookupProofEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_NORMALIZATION_PROOF_VERSION_PHASE5.to_string(),
        statement_version: STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5.to_string(),
        semantic_scope: STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5.to_string(),
        canonical_table_rows: bundle.table_rows.clone(),
        proof: prove_phase5_normalization_lookup_demo()?,
    })
}

pub fn verify_phase5_normalization_lookup_demo_envelope(
    envelope: &Phase5NormalizationLookupProofEnvelope,
) -> Result<bool> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "normalization demo proof backend `{}` is not `stwo`",
            envelope.proof_backend
        )));
    }
    if envelope.proof_backend_version != STWO_NORMALIZATION_PROOF_VERSION_PHASE5 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported normalization demo proof backend version `{}` (expected `{}`)",
            envelope.proof_backend_version, STWO_NORMALIZATION_PROOF_VERSION_PHASE5
        )));
    }
    if envelope.statement_version != STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported normalization demo statement version `{}` (expected `{}`)",
            envelope.statement_version, STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5
        )));
    }
    if envelope.semantic_scope != STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported normalization demo semantic scope `{}` (expected `{}`)",
            envelope.semantic_scope, STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5
        )));
    }

    let bundle = build_normalization_demo_bundle();
    if envelope.canonical_table_rows != bundle.table_rows {
        return Err(VmError::UnsupportedProof(
            "normalization demo proof envelope does not match the canonical Phase 5 lookup table"
                .to_string(),
        ));
    }
    verify_phase5_normalization_lookup_demo(&envelope.proof)
}

pub fn save_phase5_normalization_lookup_proof(
    proof: &Phase5NormalizationLookupProofEnvelope,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn load_phase5_normalization_lookup_proof(
    path: &Path,
) -> Result<Phase5NormalizationLookupProofEnvelope> {
    let json = fs::read_to_string(path)?;
    serde_json::from_str(&json).map_err(|error| VmError::Serialization(error.to_string()))
}

pub fn prove_phase5_normalization_lookup_demo() -> Result<Vec<u8>> {
    let bundle = build_normalization_demo_bundle();
    let config = PcsConfig::default();
    let component = phase5_normalization_component(
        bundle.log_size,
        Phase5NormalizationLookupElements::dummy(),
        SecureField::zero(),
    );
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            component.max_constraint_log_degree_bound() + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );

    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.preprocessed_trace.clone());
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.base_trace.clone());
    tree_builder.commit(channel);

    channel.mix_u64(bundle.log_size as u64);
    let lookup_elements = Phase5NormalizationLookupElements::draw(channel);
    let (interaction_trace, claimed_sum) =
        normalization_interaction_trace(bundle.log_size, &bundle.base_trace, &lookup_elements);
    if claimed_sum != SecureField::zero() {
        return Err(VmError::UnsupportedProof(
            "normalization demo expected zero claimed sum for identical witness/table multisets"
                .to_string(),
        ));
    }

    let component = phase5_normalization_component(bundle.log_size, lookup_elements, claimed_sum);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "S-two normalization lookup proving failed: {error}"
                ))
            })?;

    serde_json::to_vec(&Phase5NormalizationProofPayload {
        stark_proof,
        canonical_table_rows: bundle.table_rows.clone(),
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

pub fn verify_phase5_normalization_lookup_demo(proof: &[u8]) -> Result<bool> {
    let bundle = build_normalization_demo_bundle();
    let payload: Phase5NormalizationProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_table_rows != bundle.table_rows {
        return Err(VmError::UnsupportedProof(
            "S-two normalization lookup verification rejected proof with non-canonical table rows"
                .to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;

    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let placeholder_component = phase5_normalization_component(
        bundle.log_size,
        Phase5NormalizationLookupElements::dummy(),
        SecureField::zero(),
    );
    let sizes = placeholder_component.trace_log_degree_bounds();
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    channel.mix_u64(bundle.log_size as u64);
    let lookup_elements = Phase5NormalizationLookupElements::draw(channel);
    let component =
        phase5_normalization_component(bundle.log_size, lookup_elements, SecureField::zero());
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);

    Ok(verify(&[&component], channel, commitment_scheme, stark_proof).is_ok())
}

#[derive(Clone)]
struct NormalizationDemoBundle {
    log_size: u32,
    table_rows: Vec<(u16, u16)>,
    preprocessed_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    base_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
}

fn build_normalization_demo_bundle() -> NormalizationDemoBundle {
    let log_size = LOG_N_LANES.max(4);
    let row_count = 1usize << log_size;
    let table_rows = padded_table_rows(row_count);
    let preprocessed_trace = normalization_preprocessed_trace(log_size, &table_rows);
    let base_trace = normalization_base_trace(log_size, &table_rows);
    NormalizationDemoBundle {
        log_size,
        table_rows,
        preprocessed_trace,
        base_trace,
    }
}

fn padded_table_rows(row_count: usize) -> Vec<(u16, u16)> {
    let base_rows: Vec<_> = phase5_normalization_table_rows()
        .into_iter()
        .map(|row| (row.norm_sq, row.inv_sqrt_q8))
        .collect();
    let pad = *base_rows.last().expect("normalization table rows");
    let mut rows = base_rows;
    rows.resize(row_count, pad);
    rows
}

fn normalization_preprocessed_trace(
    log_size: u32,
    rows: &[(u16, u16)],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(log_size).circle_domain();
    let norm_sq = BaseColumn::from_iter(
        rows.iter()
            .map(|(norm_sq, _)| BaseField::from(*norm_sq as u32)),
    );
    let inv_sqrt =
        BaseColumn::from_iter(rows.iter().map(|(_, value)| BaseField::from(*value as u32)));
    vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, norm_sq)
            .bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, inv_sqrt)
            .bit_reverse(),
    ]
}

fn normalization_base_trace(
    log_size: u32,
    rows: &[(u16, u16)],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    normalization_preprocessed_trace(log_size, rows)
}

fn normalization_interaction_trace(
    log_size: u32,
    trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    lookup_elements: &Phase5NormalizationLookupElements,
) -> (
    ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    SecureField,
) {
    let mut logup_gen = LogupTraceGenerator::new(log_size);
    let mut col_gen = logup_gen.new_col();
    for vec_row in 0..(1 << (log_size - LOG_N_LANES)) {
        let q: PackedSecureField =
            lookup_elements.combine(&[trace[0].data[vec_row], trace[1].data[vec_row]]);
        col_gen.write_frac(vec_row, PackedSecureField::zero(), q * q);
    }
    col_gen.finalize_col();
    logup_gen.finalize_last()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn phase5_normalization_demo_round_trips_real_proof() {
        let proof = prove_phase5_normalization_lookup_demo().expect("prove normalization demo");
        assert!(!proof.is_empty());
        assert!(verify_phase5_normalization_lookup_demo(&proof).expect("verify normalization demo"));
    }

    #[test]
    fn phase5_normalization_demo_envelope_round_trips() {
        let envelope = prove_phase5_normalization_lookup_demo_envelope()
            .expect("prove normalization demo envelope");
        assert_eq!(envelope.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            envelope.proof_backend_version,
            STWO_NORMALIZATION_PROOF_VERSION_PHASE5
        );
        assert_eq!(
            envelope.statement_version,
            STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5
        );
        assert_eq!(
            envelope.semantic_scope,
            STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5
        );
        assert!(verify_phase5_normalization_lookup_demo_envelope(&envelope)
            .expect("verify normalization demo envelope"));
    }
}
