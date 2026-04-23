use ark_ff::Zero;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::time::Instant;
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
use stwo_constraint_framework::{
    relation, EvalAtRow, FrameworkComponent, FrameworkEval, LogupTraceGenerator, Relation,
    RelationEntry, TraceLocationAllocator,
};

use super::normalization_component::phase5_normalization_table_rows;
use super::normalization_prover::{
    prove_phase10_shared_normalization_lookup_envelope,
    verify_phase10_shared_normalization_lookup_envelope,
};
use crate::error::{Result, VmError};

pub const STWO_PRIMITIVE_BENCHMARK_VERSION: &str = "stwo-primitive-lookup-vs-naive-benchmark-v1";
pub const STWO_PRIMITIVE_BENCHMARK_SCOPE: &str =
    "matched_stwo_lookup_vs_naive_transformer_primitive_measurement";

relation!(SoftmaxExpLookupRelation, 2);
type SoftmaxExpLookupElements = SoftmaxExpLookupRelation;

const RMSNORM_ROWS: [(u16, u16); 2] = [(4, 128), (16, 64)];
const SOFTMAX_EXP_ROWS: [(u16, u16); 3] = [(0, 256), (2, 94), (4, 35)];
const SOFTMAX_EXP_TABLE: [(u16, u16); 8] = [
    (0, 256),
    (1, 155),
    (2, 94),
    (3, 57),
    (4, 35),
    (5, 21),
    (6, 13),
    (7, 8),
];
const SOFTMAX_EXP_POLY_COEFFS: [u32; 3] = [256, 536_870_805, 1_879_048_204];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StwoPrimitiveBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub relation: String,
    pub claimed_rows: Vec<[u16; 2]>,
    pub proof_bytes: usize,
    pub prove_ms: u128,
    pub verify_ms: u128,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StwoPrimitiveBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub rows: Vec<StwoPrimitiveBenchmarkMeasurement>,
}

#[derive(Serialize, Deserialize)]
struct PrimitiveBenchmarkProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_rows: Vec<(u16, u16)>,
}

#[derive(Clone)]
struct Row2Bundle {
    log_size: u32,
    canonical_rows: Vec<(u16, u16)>,
    claimed_rows: Vec<(u16, u16)>,
    selected_positions: Vec<usize>,
}

#[derive(Clone)]
struct SoftmaxExpLookupEval {
    log_size: u32,
    lookup_elements: SoftmaxExpLookupElements,
}

impl FrameworkEval for SoftmaxExpLookupEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let claimed_score_delta_q4 = eval.next_trace_mask();
        let claimed_exp_q8 = eval.next_trace_mask();
        let selector = eval.next_trace_mask();
        let table_score_delta_q4 =
            eval.get_preprocessed_column(column_id("primitive/softmax_exp/table_score_delta_q4"));
        let table_exp_q8 = eval.get_preprocessed_column(column_id("primitive/softmax_exp/table_exp_q8"));
        let one = E::F::from(BaseField::from(1u32));

        eval.add_constraint(selector.clone() * (selector.clone() - one));
        eval.add_constraint(
            selector.clone() * (claimed_score_delta_q4.clone() - table_score_delta_q4.clone()),
        );
        eval.add_constraint(selector.clone() * (claimed_exp_q8.clone() - table_exp_q8.clone()));
        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            selector.clone().into(),
            &[claimed_score_delta_q4, claimed_exp_q8],
        ));
        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            (-selector).into(),
            &[table_score_delta_q4, table_exp_q8],
        ));
        eval.finalize_logup_in_pairs();
        eval
    }
}

#[derive(Clone)]
struct RmsNormSelectorArithmeticEval {
    log_size: u32,
}

impl FrameworkEval for RmsNormSelectorArithmeticEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let norm_sq = eval.next_trace_mask();
        let inv_sqrt_q8 = eval.next_trace_mask();
        let selectors: Vec<_> = (0..phase5_normalization_table_rows().len())
            .map(|_| eval.next_trace_mask())
            .collect();
        let one = E::F::from(BaseField::from(1u32));

        let mut selector_sum = selectors[0].clone();
        for selector in &selectors {
            eval.add_constraint(selector.clone() * (selector.clone() - one.clone()));
        }
        for selector in selectors.iter().skip(1) {
            selector_sum = selector_sum + selector.clone();
        }
        eval.add_constraint(selector_sum - one);

        let table = phase5_normalization_table_rows();
        let mut expected_norm = selectors[0].clone() * const_f::<E>(table[0].norm_sq as u32);
        let mut expected_inv = selectors[0].clone() * const_f::<E>(table[0].inv_sqrt_q8 as u32);
        for (selector, row) in selectors.iter().zip(table.iter()).skip(1) {
            expected_norm = expected_norm + selector.clone() * const_f::<E>(row.norm_sq as u32);
            expected_inv = expected_inv + selector.clone() * const_f::<E>(row.inv_sqrt_q8 as u32);
        }
        eval.add_constraint(norm_sq - expected_norm);
        eval.add_constraint(inv_sqrt_q8 - expected_inv);
        eval
    }
}

#[derive(Clone)]
struct SoftmaxExpPolynomialEval {
    log_size: u32,
}

impl FrameworkEval for SoftmaxExpPolynomialEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let score_delta_q4 = eval.next_trace_mask();
        let exp_q8 = eval.next_trace_mask();

        let mut interpolated = const_f::<E>(*SOFTMAX_EXP_POLY_COEFFS.last().expect("coefficients"));
        for coeff in SOFTMAX_EXP_POLY_COEFFS.iter().rev().skip(1) {
            interpolated = interpolated * score_delta_q4.clone() + const_f::<E>(*coeff);
        }
        eval.add_constraint(exp_q8 - interpolated);

        eval
    }
}

pub fn run_stwo_primitive_lookup_vs_naive_benchmark() -> Result<StwoPrimitiveBenchmarkReport> {
    let mut rows = Vec::new();
    rows.push(measure_rmsnorm_lookup()?);
    rows.push(measure_rmsnorm_selector_arithmetic()?);
    rows.push(measure_softmax_exp_lookup()?);
    rows.push(measure_softmax_exp_polynomial()?);
    Ok(StwoPrimitiveBenchmarkReport {
        benchmark_version: STWO_PRIMITIVE_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PRIMITIVE_BENCHMARK_SCOPE.to_string(),
        rows,
    })
}

pub fn save_stwo_primitive_benchmark_report_json(
    report: &StwoPrimitiveBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_primitive_benchmark_report_tsv(
    report: &StwoPrimitiveBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "primitive\tbackend_variant\trelation\tclaimed_rows\tproof_bytes\tprove_ms\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        let claimed_rows = row
            .claimed_rows
            .iter()
            .map(|pair| format!("{}:{}", pair[0], pair[1]))
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            row.primitive,
            row.backend_variant,
            row.relation,
            claimed_rows,
            row.proof_bytes,
            row.prove_ms,
            row.verify_ms,
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

fn measure_rmsnorm_lookup() -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = RMSNORM_ROWS.to_vec();
    let prove_start = Instant::now();
    let envelope = prove_phase10_shared_normalization_lookup_envelope(&claimed_rows)?;
    let prove_ms = prove_start.elapsed().as_millis();
    let proof_bytes = envelope.proof.len();
    let verify_start = Instant::now();
    let verified = verify_phase10_shared_normalization_lookup_envelope(&envelope)?;
    let verify_ms = verify_start.elapsed().as_millis();
    Ok(StwoPrimitiveBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "lookup_logup".to_string(),
        relation: "Phase10 shared-normalization lookup".to_string(),
        claimed_rows: claimed_rows_to_arrays(&claimed_rows),
        proof_bytes,
        prove_ms,
        verify_ms,
        verified,
        note: "actual S-two LogUp proof over the canonical Phase 5 normalization table".to_string(),
    })
}

fn measure_rmsnorm_selector_arithmetic() -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = RMSNORM_ROWS.to_vec();
    let prove_start = Instant::now();
    let proof = prove_rmsnorm_selector_arithmetic(&claimed_rows)?;
    let prove_ms = prove_start.elapsed().as_millis();
    let proof_bytes = proof.len();
    let verify_start = Instant::now();
    let verified = verify_rmsnorm_selector_arithmetic(&claimed_rows, &proof)?;
    let verify_ms = verify_start.elapsed().as_millis();
    Ok(StwoPrimitiveBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "naive_selector_arithmetic".to_string(),
        relation: "one-hot arithmetized table selection".to_string(),
        claimed_rows: claimed_rows_to_arrays(&claimed_rows),
        proof_bytes,
        prove_ms,
        verify_ms,
        verified,
        note: "actual S-two arithmetic proof; no LogUp relation, no lookup table argument".to_string(),
    })
}

fn measure_softmax_exp_lookup() -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = SOFTMAX_EXP_ROWS.to_vec();
    let prove_start = Instant::now();
    let proof = prove_softmax_exp_lookup(&claimed_rows)?;
    let prove_ms = prove_start.elapsed().as_millis();
    let proof_bytes = proof.len();
    let verify_start = Instant::now();
    let verified = verify_softmax_exp_lookup(&claimed_rows, &proof)?;
    let verify_ms = verify_start.elapsed().as_millis();
    Ok(StwoPrimitiveBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "lookup_logup".to_string(),
        relation: "softmax-exp table lookup".to_string(),
        claimed_rows: claimed_rows_to_arrays(&claimed_rows),
        proof_bytes,
        prove_ms,
        verify_ms,
        verified,
        note: "actual S-two LogUp proof for the exp-table part of softmax, not full softmax".to_string(),
    })
}

fn measure_softmax_exp_polynomial() -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = SOFTMAX_EXP_ROWS.to_vec();
    let prove_start = Instant::now();
    let proof = prove_softmax_exp_polynomial(&claimed_rows)?;
    let prove_ms = prove_start.elapsed().as_millis();
    let proof_bytes = proof.len();
    let verify_start = Instant::now();
    let verified = verify_softmax_exp_polynomial(&claimed_rows, &proof)?;
    let verify_ms = verify_start.elapsed().as_millis();
    Ok(StwoPrimitiveBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "polynomial_interpolation".to_string(),
        relation: "degree-2 exp-table interpolation over sampled points".to_string(),
        claimed_rows: claimed_rows_to_arrays(&claimed_rows),
        proof_bytes,
        prove_ms,
        verify_ms,
        verified,
        note: "actual S-two arithmetic proof for a sampled exp-table slice, not full softmax".to_string(),
    })
}

fn prove_rmsnorm_selector_arithmetic(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_rmsnorm_bundle(claimed_rows)?;
    let component = rmsnorm_selector_arithmetic_component(bundle.log_size);
    prove_base_only(component, rmsnorm_selector_base_trace(&bundle), &bundle.canonical_rows)
}

fn verify_rmsnorm_selector_arithmetic(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_rmsnorm_bundle(claimed_rows)?;
    let component = rmsnorm_selector_arithmetic_component(bundle.log_size);
    verify_base_only(component, proof, &bundle.canonical_rows)
}

fn prove_softmax_exp_polynomial(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_exp_polynomial_component(bundle.log_size);
    prove_base_only(component, polynomial_base_trace(&bundle), &bundle.canonical_rows)
}

fn verify_softmax_exp_polynomial(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_exp_polynomial_component(bundle.log_size);
    verify_base_only(component, proof, &bundle.canonical_rows)
}

fn prove_softmax_exp_lookup(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let config = PcsConfig::default();
    let component = softmax_exp_lookup_component(
        bundle.log_size,
        SoftmaxExpLookupElements::dummy(),
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
    tree_builder.extend_evals(row2_preprocessed_trace(bundle.log_size, &bundle.canonical_rows));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(lookup_base_trace(&bundle));
    tree_builder.commit(channel);

    mix_claimed_rows(channel, &bundle.claimed_rows);
    let lookup_elements = SoftmaxExpLookupElements::draw(channel);
    let (interaction_trace, claimed_sum) = lookup_interaction_trace(
        bundle.log_size,
        &lookup_base_trace(&bundle),
        &row2_preprocessed_trace(bundle.log_size, &bundle.canonical_rows),
        &lookup_elements,
    );
    if claimed_sum != SecureField::zero() {
        return Err(VmError::UnsupportedProof(
            "softmax exp lookup expected zero claimed sum for selected canonical rows".to_string(),
        ));
    }
    let component = softmax_exp_lookup_component(bundle.log_size, lookup_elements, claimed_sum);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "S-two softmax-exp lookup proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&PrimitiveBenchmarkProofPayload {
        stark_proof,
        canonical_rows: bundle.canonical_rows,
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_softmax_exp_lookup(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let payload: PrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_rows != bundle.canonical_rows {
        return Err(VmError::UnsupportedProof(
            "softmax-exp lookup proof uses non-canonical table rows".to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;
    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let placeholder_component = softmax_exp_lookup_component(
        bundle.log_size,
        SoftmaxExpLookupElements::dummy(),
        SecureField::zero(),
    );
    let sizes = placeholder_component.trace_log_degree_bounds();
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_claimed_rows(channel, &bundle.claimed_rows);
    let lookup_elements = SoftmaxExpLookupElements::draw(channel);
    let component = softmax_exp_lookup_component(bundle.log_size, lookup_elements, SecureField::zero());
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);
    Ok(verify(&[&component], channel, commitment_scheme, stark_proof).is_ok())
}

fn prove_base_only<E>(
    component: FrameworkComponent<E>,
    base_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    canonical_rows: &[(u16, u16)],
) -> Result<Vec<u8>>
where
    E: FrameworkEval + Sync,
{
    let config = PcsConfig::default();
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

    let tree_builder = commitment_scheme.tree_builder();
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(base_trace);
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| VmError::UnsupportedProof(format!("S-two primitive proving failed: {error}")))?;
    serde_json::to_vec(&PrimitiveBenchmarkProofPayload {
        stark_proof,
        canonical_rows: canonical_rows.to_vec(),
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_base_only<E>(
    component: FrameworkComponent<E>,
    proof: &[u8],
    canonical_rows: &[(u16, u16)],
) -> Result<bool>
where
    E: FrameworkEval + Sync,
{
    let payload: PrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_rows != canonical_rows {
        return Err(VmError::UnsupportedProof(
            "primitive arithmetic proof uses non-canonical rows".to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;
    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let sizes = component.trace_log_degree_bounds();
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    Ok(verify(&[&component], channel, commitment_scheme, stark_proof).is_ok())
}

fn build_rmsnorm_bundle(claimed_rows: &[(u16, u16)]) -> Result<Row2Bundle> {
    let canonical_rows: Vec<_> = phase5_normalization_table_rows()
        .into_iter()
        .map(|row| (row.norm_sq, row.inv_sqrt_q8))
        .collect();
    build_row2_bundle(canonical_rows, claimed_rows)
}

fn build_softmax_bundle(claimed_rows: &[(u16, u16)]) -> Result<Row2Bundle> {
    build_row2_bundle(SOFTMAX_EXP_TABLE.to_vec(), claimed_rows)
}

fn build_row2_bundle(canonical_rows: Vec<(u16, u16)>, claimed_rows: &[(u16, u16)]) -> Result<Row2Bundle> {
    if claimed_rows.is_empty() {
        return Err(VmError::InvalidConfig(
            "primitive benchmark requires at least one claimed row".to_string(),
        ));
    }
    let mut selected_positions = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let Some(position) = canonical_rows.iter().position(|candidate| candidate == row) else {
            return Err(VmError::InvalidConfig(format!(
                "primitive benchmark received non-canonical row ({}, {})",
                row.0, row.1
            )));
        };
        if selected_positions.contains(&position) {
            return Err(VmError::InvalidConfig(format!(
                "primitive benchmark received duplicate row ({}, {})",
                row.0, row.1
            )));
        }
        selected_positions.push(position);
    }
    Ok(Row2Bundle {
        log_size: LOG_N_LANES.max(4),
        canonical_rows,
        claimed_rows: claimed_rows.to_vec(),
        selected_positions,
    })
}

fn padded_rows(log_size: u32, rows: &[(u16, u16)]) -> Vec<(u16, u16)> {
    let row_count = 1usize << log_size;
    let mut padded = rows.to_vec();
    let pad = *padded.last().expect("non-empty rows");
    padded.resize(row_count, pad);
    padded
}

fn row2_preprocessed_trace(
    log_size: u32,
    canonical_rows: &[(u16, u16)],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(log_size, canonical_rows);
    two_column_trace(log_size, &padded)
}

fn lookup_base_trace(
    bundle: &Row2Bundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(bundle.log_size, &bundle.canonical_rows);
    let domain = CanonicCoset::new(bundle.log_size).circle_domain();
    let lhs = BaseColumn::from_iter(padded.iter().map(|row| BaseField::from(row.0 as u32)));
    let rhs = BaseColumn::from_iter(padded.iter().map(|row| BaseField::from(row.1 as u32)));
    let selector = BaseColumn::from_iter(
        padded
            .iter()
            .enumerate()
            .map(|(index, _)| BaseField::from(u32::from(bundle.selected_positions.contains(&index)))),
    );
    vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, lhs).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, rhs).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, selector).bit_reverse(),
    ]
}

fn rmsnorm_selector_base_trace(
    bundle: &Row2Bundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(bundle.log_size, &bundle.claimed_rows);
    let table = bundle.canonical_rows.clone();
    let domain = CanonicCoset::new(bundle.log_size).circle_domain();
    let mut columns = two_column_trace(bundle.log_size, &padded);
    for table_row in &table {
        let selector = BaseColumn::from_iter(
            padded
                .iter()
                .map(|row| BaseField::from(u32::from(row == table_row))),
        );
        columns.push(
            CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, selector)
                .bit_reverse(),
        );
    }
    columns
}

fn polynomial_base_trace(
    bundle: &Row2Bundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(bundle.log_size, &bundle.claimed_rows);
    two_column_trace(bundle.log_size, &padded)
}

fn two_column_trace(
    log_size: u32,
    rows: &[(u16, u16)],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(log_size).circle_domain();
    let lhs = BaseColumn::from_iter(rows.iter().map(|row| BaseField::from(row.0 as u32)));
    let rhs = BaseColumn::from_iter(rows.iter().map(|row| BaseField::from(row.1 as u32)));
    vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, lhs).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, rhs).bit_reverse(),
    ]
}

fn lookup_interaction_trace(
    log_size: u32,
    base_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    preprocessed_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    lookup_elements: &SoftmaxExpLookupElements,
) -> (
    ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    SecureField,
) {
    let mut logup_gen = LogupTraceGenerator::new(log_size);
    let mut col_gen = logup_gen.new_col();
    for vec_row in 0..(1 << (log_size - LOG_N_LANES)) {
        let selector = PackedSecureField::from(base_trace[2].data[vec_row]);
        let witness_q: PackedSecureField =
            lookup_elements.combine(&[base_trace[0].data[vec_row], base_trace[1].data[vec_row]]);
        let table_q: PackedSecureField = lookup_elements.combine(&[
            preprocessed_trace[0].data[vec_row],
            preprocessed_trace[1].data[vec_row],
        ]);
        col_gen.write_frac(
            vec_row,
            selector * (table_q - witness_q),
            witness_q * table_q,
        );
    }
    col_gen.finalize_col();
    logup_gen.finalize_last()
}

fn rmsnorm_selector_arithmetic_component(
    log_size: u32,
) -> FrameworkComponent<RmsNormSelectorArithmeticEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        RmsNormSelectorArithmeticEval { log_size },
        SecureField::zero(),
    )
}

fn softmax_exp_polynomial_component(log_size: u32) -> FrameworkComponent<SoftmaxExpPolynomialEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        SoftmaxExpPolynomialEval { log_size },
        SecureField::zero(),
    )
}

fn softmax_exp_lookup_component(
    log_size: u32,
    lookup_elements: SoftmaxExpLookupElements,
    claimed_sum: SecureField,
) -> FrameworkComponent<SoftmaxExpLookupEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&[
            column_id("primitive/softmax_exp/table_score_delta_q4"),
            column_id("primitive/softmax_exp/table_exp_q8"),
        ]),
        SoftmaxExpLookupEval {
            log_size,
            lookup_elements,
        },
        claimed_sum,
    )
}

fn mix_claimed_rows(channel: &mut Blake2sM31Channel, claimed_rows: &[(u16, u16)]) {
    channel.mix_u64(claimed_rows.len() as u64);
    for row in claimed_rows {
        channel.mix_u64(row.0 as u64);
        channel.mix_u64(row.1 as u64);
    }
}

fn claimed_rows_to_arrays(rows: &[(u16, u16)]) -> Vec<[u16; 2]> {
    rows.iter().map(|row| [row.0, row.1]).collect()
}

fn column_id(id: &str) -> stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId {
    stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId { id: id.to_string() }
}

fn const_f<E: EvalAtRow>(value: u32) -> E::F {
    E::F::from(BaseField::from(value))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn primitive_benchmark_runs_all_matched_paths() {
        let report = run_stwo_primitive_lookup_vs_naive_benchmark()
            .expect("primitive benchmark should run");
        assert_eq!(report.rows.len(), 4);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report
            .rows
            .iter()
            .any(|row| row.backend_variant == "lookup_logup" && row.primitive == "rmsnorm_q8_inv_sqrt"));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "polynomial_interpolation" && row.primitive == "softmax_exp_q8"
        }));
    }

    #[test]
    fn primitive_benchmark_rejects_noncanonical_rows() {
        let error = prove_softmax_exp_lookup(&[(9, 3)])
            .expect_err("non-canonical softmax row must be rejected");
        assert!(error.to_string().contains("non-canonical row"));
    }
}
