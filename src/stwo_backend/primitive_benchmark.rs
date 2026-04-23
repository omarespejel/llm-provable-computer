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

use super::lookup_component::{phase3_lookup_table_rows, Phase3LookupTableRow};
use super::lookup_prover::{
    prove_phase10_shared_binary_step_lookup_envelope,
    verify_phase10_shared_binary_step_lookup_envelope,
};
use super::normalization_component::phase5_normalization_table_rows;
use super::normalization_prover::{
    prepare_phase92_shared_normalization_primitive_artifact,
    prove_phase10_shared_normalization_lookup_envelope,
    verify_phase10_shared_normalization_lookup_envelope,
    verify_phase92_shared_normalization_primitive_artifact,
    Phase92SharedNormalizationPrimitiveStep,
};
use crate::error::{Result, VmError};

pub const STWO_PRIMITIVE_BENCHMARK_VERSION: &str = "stwo-primitive-lookup-vs-naive-benchmark-v1";
pub const STWO_PRIMITIVE_BENCHMARK_SCOPE: &str =
    "matched_stwo_lookup_vs_naive_transformer_primitive_measurement";
pub const STWO_SHARED_TABLE_REUSE_BENCHMARK_VERSION: &str = "stwo-shared-table-reuse-benchmark-v1";
pub const STWO_SHARED_TABLE_REUSE_BENCHMARK_SCOPE: &str =
    "shared_table_reuse_calibration_over_transformer_primitives";

relation!(SoftmaxExpLookupRelation, 2);
type SoftmaxExpLookupElements = SoftmaxExpLookupRelation;

const RMSNORM_ROWS: [(u16, u16); 2] = [(4, 128), (16, 64)];
const RMSNORM_REUSE_ROWS: [(u16, u16); 5] = [(1, 256), (2, 181), (4, 128), (8, 91), (16, 64)];
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
const RMSNORM_REUSE_STEP_COUNTS: [usize; 4] = [1, 2, 4, 5];
const SOFTMAX_REUSE_STEP_COUNTS: [usize; 4] = [1, 2, 4, 8];
const ACTIVATION_REUSE_STEP_COUNTS: [usize; 3] = [1, 2, 3];

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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StwoSharedTableReuseBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub relation: String,
    pub claimed_rows: Vec<[i16; 2]>,
    pub proof_bytes: usize,
    pub serialized_bytes: usize,
    pub prove_ms: u128,
    pub verify_ms: u128,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StwoSharedTableReuseBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub rows: Vec<StwoSharedTableReuseBenchmarkMeasurement>,
}

#[derive(Serialize, Deserialize)]
struct PrimitiveBenchmarkProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_rows: Vec<(u16, u16)>,
}

#[derive(Serialize, Deserialize)]
struct SharedNormalizationProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_table_rows: Vec<(u16, u16)>,
}

#[derive(Serialize, Deserialize)]
struct SharedActivationProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_table_rows: Vec<Phase3LookupTableRow>,
}

#[derive(Serialize, Deserialize)]
struct SignedPrimitiveBenchmarkProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_rows: Vec<[i16; 2]>,
}

#[derive(Clone)]
struct Row2Bundle {
    log_size: u32,
    canonical_rows: Vec<(u16, u16)>,
    claimed_rows: Vec<(u16, u16)>,
    selected_positions: Vec<usize>,
}

#[derive(Clone)]
struct ActivationBundle {
    log_size: u32,
    canonical_rows: Vec<Phase3LookupTableRow>,
    claimed_rows: Vec<Phase3LookupTableRow>,
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
        let table_exp_q8 =
            eval.get_preprocessed_column(column_id("primitive/softmax_exp/table_exp_q8"));
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
struct SoftmaxSelectorArithmeticEval {
    log_size: u32,
}

impl FrameworkEval for SoftmaxSelectorArithmeticEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let score_delta_q4 = eval.next_trace_mask();
        let exp_q8 = eval.next_trace_mask();
        let selectors: Vec<_> = (0..SOFTMAX_EXP_TABLE.len())
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

        let mut expected_score = selectors[0].clone() * const_f::<E>(SOFTMAX_EXP_TABLE[0].0 as u32);
        let mut expected_exp = selectors[0].clone() * const_f::<E>(SOFTMAX_EXP_TABLE[0].1 as u32);
        for (selector, row) in selectors.iter().zip(SOFTMAX_EXP_TABLE.iter()).skip(1) {
            expected_score = expected_score + selector.clone() * const_f::<E>(row.0 as u32);
            expected_exp = expected_exp + selector.clone() * const_f::<E>(row.1 as u32);
        }
        eval.add_constraint(score_delta_q4 - expected_score);
        eval.add_constraint(exp_q8 - expected_exp);
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

#[derive(Clone)]
struct ActivationSelectorArithmeticEval {
    log_size: u32,
}

impl FrameworkEval for ActivationSelectorArithmeticEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let activation_input = eval.next_trace_mask();
        let activation_output = eval.next_trace_mask();
        let selectors: Vec<_> = (0..phase3_lookup_table_rows().len())
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

        let table = phase3_lookup_table_rows();
        let mut expected_input = selectors[0].clone() * const_signed_f::<E>(table[0].input);
        let mut expected_output =
            selectors[0].clone() * const_signed_f::<E>(table[0].output as i16);
        for (selector, row) in selectors.iter().zip(table.iter()).skip(1) {
            expected_input = expected_input + selector.clone() * const_signed_f::<E>(row.input);
            expected_output =
                expected_output + selector.clone() * const_signed_f::<E>(row.output as i16);
        }
        eval.add_constraint(activation_input - expected_input);
        eval.add_constraint(activation_output - expected_output);
        eval
    }
}

pub fn run_stwo_primitive_lookup_vs_naive_benchmark() -> Result<StwoPrimitiveBenchmarkReport> {
    let mut rows = Vec::new();
    rows.push(measure_rmsnorm_lookup()?);
    rows.push(measure_rmsnorm_selector_arithmetic()?);
    rows.push(measure_softmax_exp_lookup()?);
    rows.push(measure_softmax_exp_polynomial()?);
    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "primitive benchmark row {} / {} did not verify",
            failed.primitive, failed.backend_variant
        )));
    }
    Ok(StwoPrimitiveBenchmarkReport {
        benchmark_version: STWO_PRIMITIVE_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PRIMITIVE_BENCHMARK_SCOPE.to_string(),
        rows,
    })
}

pub fn run_stwo_shared_table_reuse_benchmark() -> Result<StwoSharedTableReuseBenchmarkReport> {
    run_stwo_shared_table_reuse_benchmark_for_step_counts(
        &RMSNORM_REUSE_STEP_COUNTS,
        &SOFTMAX_REUSE_STEP_COUNTS,
        &ACTIVATION_REUSE_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_shared_table_reuse_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkReport> {
    run_stwo_shared_table_reuse_benchmark_for_step_counts(
        &RMSNORM_REUSE_STEP_COUNTS,
        &SOFTMAX_REUSE_STEP_COUNTS,
        &ACTIVATION_REUSE_STEP_COUNTS,
        capture_timings,
    )
}

fn run_stwo_shared_table_reuse_benchmark_for_step_counts(
    rmsnorm_step_counts: &[usize],
    softmax_step_counts: &[usize],
    activation_step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkReport> {
    let mut rows = Vec::new();

    let rmsnorm_rows = rmsnorm_canonical_rows();
    for &steps in rmsnorm_step_counts {
        let claimed_rows = claimed_row_prefix(&rmsnorm_rows, steps, "rmsnorm_q8_inv_sqrt")?;
        rows.push(measure_rmsnorm_shared_lookup_reuse(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_rmsnorm_independent_lookup(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_rmsnorm_independent_naive(
            &claimed_rows,
            capture_timings,
        )?);
    }

    let softmax_rows = softmax_canonical_rows();
    for &steps in softmax_step_counts {
        let claimed_rows = claimed_row_prefix(&softmax_rows, steps, "softmax_exp_q8")?;
        rows.push(measure_softmax_shared_lookup_reuse(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_softmax_independent_lookup(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_softmax_independent_naive(
            &claimed_rows,
            capture_timings,
        )?);
    }

    let activation_rows = activation_canonical_rows();
    for &steps in activation_step_counts {
        let claimed_rows = activation_claimed_row_prefix(&activation_rows, steps)?;
        rows.push(measure_activation_shared_lookup_reuse(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_activation_independent_lookup(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_activation_independent_naive(
            &claimed_rows,
            capture_timings,
        )?);
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "shared-table reuse benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    Ok(StwoSharedTableReuseBenchmarkReport {
        benchmark_version: STWO_SHARED_TABLE_REUSE_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_SHARED_TABLE_REUSE_BENCHMARK_SCOPE.to_string(),
        rows,
    })
}

fn measure_elapsed_ms<T, F>(capture_timings: bool, op: F) -> Result<(T, u128)>
where
    F: FnOnce() -> Result<T>,
{
    if capture_timings {
        let start = Instant::now();
        let value = op()?;
        Ok((value, start.elapsed().as_millis()))
    } else {
        Ok((op()?, 0))
    }
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

pub fn save_stwo_shared_table_reuse_benchmark_report_json(
    report: &StwoSharedTableReuseBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_shared_table_reuse_benchmark_report_tsv(
    report: &StwoSharedTableReuseBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "primitive\tbackend_variant\tsteps\trelation\tclaimed_rows\tproof_bytes\tserialized_bytes\tprove_ms\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        let claimed_rows = row
            .claimed_rows
            .iter()
            .map(|pair| format!("{}:{}", pair[0], pair[1]))
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            row.primitive,
            row.backend_variant,
            row.steps,
            row.relation,
            claimed_rows,
            row.proof_bytes,
            row.serialized_bytes,
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
    let proof_bytes = shared_normalization_stark_proof_size(&envelope.proof)?;
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
    let proof_bytes = primitive_benchmark_stark_proof_size(&proof)?;
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
        note: "actual S-two arithmetic proof; no LogUp relation, no lookup table argument"
            .to_string(),
    })
}

fn measure_softmax_exp_lookup() -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = SOFTMAX_EXP_ROWS.to_vec();
    let prove_start = Instant::now();
    let proof = prove_softmax_exp_lookup(&claimed_rows)?;
    let prove_ms = prove_start.elapsed().as_millis();
    let proof_bytes = primitive_benchmark_stark_proof_size(&proof)?;
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
        note: "actual S-two LogUp proof for the exp-table part of softmax, not full softmax"
            .to_string(),
    })
}

fn measure_softmax_exp_polynomial() -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = SOFTMAX_EXP_ROWS.to_vec();
    let prove_start = Instant::now();
    let proof = prove_softmax_exp_polynomial(&claimed_rows)?;
    let prove_ms = prove_start.elapsed().as_millis();
    let proof_bytes = primitive_benchmark_stark_proof_size(&proof)?;
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
        note: "actual S-two arithmetic proof for a sampled exp-table slice, not full softmax"
            .to_string(),
    })
}

fn measure_rmsnorm_shared_lookup_reuse(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let steps = shared_normalization_steps_from_rows(claimed_rows);
    let (artifact, prove_ms) = measure_elapsed_ms(capture_timings, || {
        prepare_phase92_shared_normalization_primitive_artifact(&steps)
    })?;
    let proof_bytes = shared_normalization_stark_proof_size(&artifact.proof_envelope.proof)?;
    let serialized_bytes = serde_json::to_vec(&artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len();
    let (_verified_unit, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase92_shared_normalization_primitive_artifact(&artifact)
    })?;
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "shared_table_lookup_reuse".to_string(),
        steps: claimed_rows.len(),
        relation: "Phase92 shared-normalization primitive artifact".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one shared proof artifact binds all claimed rows to one canonical normalization table identity".to_string(),
    })
}

fn measure_rmsnorm_independent_lookup(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0;
    let mut verify_ms = 0;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [*row];
        let (envelope, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_phase10_shared_normalization_lookup_envelope(&step_rows)
        })?;
        prove_ms += elapsed_ms;
        proof_bytes += shared_normalization_stark_proof_size(&envelope.proof)?;
        serialized_bytes += serde_json::to_vec(&envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?
            .len();
        proofs.push(envelope);
    }
    for envelope in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_phase10_shared_normalization_lookup_envelope(envelope)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent shared-normalization lookup proof did not verify".to_string(),
            ));
        }
        verify_ms += elapsed_ms;
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "independent_lookup".to_string(),
        steps: claimed_rows.len(),
        relation: "independent Phase10 shared-normalization lookup proofs".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one lookup proof envelope per step over the same canonical normalization table"
            .to_string(),
    })
}

fn measure_rmsnorm_independent_naive(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0;
    let mut verify_ms = 0;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [*row];
        let (proof, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_rmsnorm_selector_arithmetic(&step_rows)
        })?;
        prove_ms += elapsed_ms;
        proof_bytes += primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        proofs.push((step_rows, proof));
    }
    for (step_rows, proof) in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_rmsnorm_selector_arithmetic(step_rows, proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent RMSNorm arithmetic proof did not verify".to_string(),
            ));
        }
        verify_ms += elapsed_ms;
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "independent_selector_arithmetic".to_string(),
        steps: claimed_rows.len(),
        relation: "independent selector-arithmetic proofs".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one arithmetic proof per step without shared lookup reuse".to_string(),
    })
}

fn measure_softmax_shared_lookup_reuse(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let (proof, prove_ms) =
        measure_elapsed_ms(capture_timings, || prove_softmax_exp_lookup(claimed_rows))?;
    let proof_bytes = primitive_benchmark_stark_proof_size(&proof)?;
    let serialized_bytes = proof.len();
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_softmax_exp_lookup(claimed_rows, &proof)
    })?;
    if !verified {
        return Err(VmError::UnsupportedProof(
            "shared softmax lookup proof did not verify".to_string(),
        ));
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "shared_table_lookup_reuse".to_string(),
        steps: claimed_rows.len(),
        relation: "single proof over multiple canonical exp-table rows".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one lookup proof binds multiple selected rows to the canonical softmax exp table"
            .to_string(),
    })
}

fn measure_softmax_independent_lookup(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0;
    let mut verify_ms = 0;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [*row];
        let (proof, elapsed_ms) =
            measure_elapsed_ms(capture_timings, || prove_softmax_exp_lookup(&step_rows))?;
        prove_ms += elapsed_ms;
        proof_bytes += primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        proofs.push((step_rows, proof));
    }
    for (step_rows, proof) in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_softmax_exp_lookup(step_rows, proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent softmax lookup proof did not verify".to_string(),
            ));
        }
        verify_ms += elapsed_ms;
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "independent_lookup".to_string(),
        steps: claimed_rows.len(),
        relation: "independent softmax-exp table lookup proofs".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one lookup proof per step against the canonical softmax exp table".to_string(),
    })
}

fn measure_softmax_independent_naive(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0;
    let mut verify_ms = 0;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [*row];
        let (proof, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_softmax_selector_arithmetic(&step_rows)
        })?;
        prove_ms += elapsed_ms;
        proof_bytes += primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        proofs.push((step_rows, proof));
    }
    for (step_rows, proof) in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_softmax_selector_arithmetic(step_rows, proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent softmax arithmetic proof did not verify".to_string(),
            ));
        }
        verify_ms += elapsed_ms;
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "independent_selector_arithmetic".to_string(),
        steps: claimed_rows.len(),
        relation: "independent selector-arithmetic proofs".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one selector-arithmetic proof per step without shared lookup reuse".to_string(),
    })
}

fn measure_activation_shared_lookup_reuse(
    claimed_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let (envelope, prove_ms) = measure_elapsed_ms(capture_timings, || {
        prove_phase10_shared_binary_step_lookup_envelope(claimed_rows)
    })?;
    let proof_bytes = shared_activation_stark_proof_size(&envelope.proof)?;
    let serialized_bytes = serde_json::to_vec(&envelope)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len();
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase10_shared_binary_step_lookup_envelope(&envelope)
    })?;
    if !verified {
        return Err(VmError::UnsupportedProof(
            "shared activation lookup proof did not verify".to_string(),
        ));
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "binary_step_activation".to_string(),
        backend_variant: "shared_table_lookup_reuse".to_string(),
        steps: claimed_rows.len(),
        relation: "single proof over multiple canonical activation rows".to_string(),
        claimed_rows: activation_rows_to_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one lookup proof binds multiple selected rows to the canonical binary-step activation table".to_string(),
    })
}

fn measure_activation_independent_lookup(
    claimed_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0;
    let mut verify_ms = 0;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [row.clone()];
        let (envelope, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_phase10_shared_binary_step_lookup_envelope(&step_rows)
        })?;
        prove_ms += elapsed_ms;
        proof_bytes += shared_activation_stark_proof_size(&envelope.proof)?;
        serialized_bytes += serde_json::to_vec(&envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?
            .len();
        proofs.push(envelope);
    }
    for envelope in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_phase10_shared_binary_step_lookup_envelope(envelope)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent activation lookup proof did not verify".to_string(),
            ));
        }
        verify_ms += elapsed_ms;
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "binary_step_activation".to_string(),
        backend_variant: "independent_lookup".to_string(),
        steps: claimed_rows.len(),
        relation: "independent binary-step activation lookup proofs".to_string(),
        claimed_rows: activation_rows_to_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note:
            "one lookup proof envelope per step against the canonical binary-step activation table"
                .to_string(),
    })
}

fn measure_activation_independent_naive(
    claimed_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0;
    let mut verify_ms = 0;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [row.clone()];
        let (proof, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_activation_selector_arithmetic(&step_rows)
        })?;
        prove_ms += elapsed_ms;
        proof_bytes += signed_primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        proofs.push((step_rows, proof));
    }
    for (step_rows, proof) in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_activation_selector_arithmetic(step_rows, proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent activation arithmetic proof did not verify".to_string(),
            ));
        }
        verify_ms += elapsed_ms;
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "binary_step_activation".to_string(),
        backend_variant: "independent_selector_arithmetic".to_string(),
        steps: claimed_rows.len(),
        relation: "independent selector-arithmetic proofs".to_string(),
        claimed_rows: activation_rows_to_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one selector-arithmetic proof per step without shared lookup reuse".to_string(),
    })
}

fn rmsnorm_canonical_rows() -> Vec<(u16, u16)> {
    RMSNORM_REUSE_ROWS.to_vec()
}

fn softmax_canonical_rows() -> Vec<(u16, u16)> {
    SOFTMAX_EXP_TABLE.to_vec()
}

fn activation_canonical_rows() -> Vec<Phase3LookupTableRow> {
    phase3_lookup_table_rows()
}

fn claimed_row_prefix(
    canonical_rows: &[(u16, u16)],
    step_count: usize,
    primitive: &str,
) -> Result<Vec<(u16, u16)>> {
    if step_count == 0 || step_count > canonical_rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "{primitive} shared-table reuse benchmark requested {step_count} steps but only {} canonical rows are available",
            canonical_rows.len()
        )));
    }
    Ok(canonical_rows.iter().copied().take(step_count).collect())
}

fn activation_claimed_row_prefix(
    canonical_rows: &[Phase3LookupTableRow],
    step_count: usize,
) -> Result<Vec<Phase3LookupTableRow>> {
    if step_count == 0 || step_count > canonical_rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "binary_step_activation shared-table reuse benchmark requested {step_count} steps but only {} canonical rows are available",
            canonical_rows.len()
        )));
    }
    Ok(canonical_rows.iter().take(step_count).cloned().collect())
}

fn shared_normalization_steps_from_rows(
    claimed_rows: &[(u16, u16)],
) -> Vec<Phase92SharedNormalizationPrimitiveStep> {
    claimed_rows
        .iter()
        .enumerate()
        .map(|(index, row)| Phase92SharedNormalizationPrimitiveStep {
            step_index: index,
            step_label: format!("benchmark-step-{index}.norm"),
            claimed_rows: vec![*row],
        })
        .collect()
}

fn prove_rmsnorm_selector_arithmetic(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_rmsnorm_bundle(claimed_rows)?;
    let component = rmsnorm_selector_arithmetic_component(bundle.log_size);
    prove_base_only(
        component,
        rmsnorm_selector_base_trace(&bundle),
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn verify_rmsnorm_selector_arithmetic(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_rmsnorm_bundle(claimed_rows)?;
    let component = rmsnorm_selector_arithmetic_component(bundle.log_size);
    verify_base_only(
        component,
        proof,
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn prove_softmax_selector_arithmetic(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_selector_arithmetic_component(bundle.log_size);
    prove_base_only(
        component,
        softmax_selector_base_trace(&bundle),
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn verify_softmax_selector_arithmetic(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_selector_arithmetic_component(bundle.log_size);
    verify_base_only(
        component,
        proof,
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn prove_softmax_exp_polynomial(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_exp_polynomial_component(bundle.log_size);
    prove_base_only(
        component,
        polynomial_base_trace(&bundle),
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn verify_softmax_exp_polynomial(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_exp_polynomial_component(bundle.log_size);
    verify_base_only(
        component,
        proof,
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
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
    tree_builder.extend_evals(row2_preprocessed_trace(
        bundle.log_size,
        &bundle.canonical_rows,
    ));
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
    if stark_proof.commitments.len() < sizes.len() {
        return Err(VmError::UnsupportedProof(
            "softmax-exp lookup proof uses a malformed or tampered commitment payload".to_string(),
        ));
    }
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_claimed_rows(channel, &bundle.claimed_rows);
    let lookup_elements = SoftmaxExpLookupElements::draw(channel);
    let component =
        softmax_exp_lookup_component(bundle.log_size, lookup_elements, SecureField::zero());
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            VmError::UnsupportedProof(format!(
                "S-two softmax-exp lookup verification failed: {error}"
            ))
        })
}

fn prove_activation_selector_arithmetic(claimed_rows: &[Phase3LookupTableRow]) -> Result<Vec<u8>> {
    let bundle = build_activation_bundle(claimed_rows)?;
    let component = activation_selector_arithmetic_component(bundle.log_size);
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
    tree_builder.extend_evals(activation_selector_base_trace(&bundle));
    tree_builder.commit(channel);
    mix_activation_claimed_rows(channel, &bundle.claimed_rows);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "S-two activation arithmetic proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&SignedPrimitiveBenchmarkProofPayload {
        stark_proof,
        canonical_rows: activation_rows_to_arrays(&bundle.canonical_rows),
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_activation_selector_arithmetic(
    claimed_rows: &[Phase3LookupTableRow],
    proof: &[u8],
) -> Result<bool> {
    let bundle = build_activation_bundle(claimed_rows)?;
    let payload: SignedPrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_rows != activation_rows_to_arrays(&bundle.canonical_rows) {
        return Err(VmError::UnsupportedProof(
            "activation arithmetic proof uses non-canonical rows".to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;
    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let component = activation_selector_arithmetic_component(bundle.log_size);
    let sizes = component.trace_log_degree_bounds();
    if stark_proof.commitments.len() < sizes.len() {
        return Err(VmError::UnsupportedProof(
            "activation arithmetic proof uses a malformed or tampered commitment payload"
                .to_string(),
        ));
    }
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_activation_claimed_rows(channel, &bundle.claimed_rows);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            VmError::UnsupportedProof(format!(
                "S-two activation arithmetic verification failed: {error}"
            ))
        })
}

fn prove_base_only<E>(
    component: FrameworkComponent<E>,
    base_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    canonical_rows: &[(u16, u16)],
    claimed_rows: &[(u16, u16)],
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
    mix_claimed_rows(channel, claimed_rows);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!("S-two primitive proving failed: {error}"))
            })?;
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
    claimed_rows: &[(u16, u16)],
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
    if stark_proof.commitments.len() < sizes.len() {
        return Err(VmError::UnsupportedProof(
            "primitive arithmetic proof uses a malformed or tampered commitment payload"
                .to_string(),
        ));
    }
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_claimed_rows(channel, claimed_rows);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            VmError::UnsupportedProof(format!("S-two primitive verification failed: {error}"))
        })
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

fn build_activation_bundle(claimed_rows: &[Phase3LookupTableRow]) -> Result<ActivationBundle> {
    if claimed_rows.is_empty() {
        return Err(VmError::InvalidConfig(
            "binary-step activation benchmark requires at least one claimed row".to_string(),
        ));
    }
    let canonical_rows = phase3_lookup_table_rows();
    let mut selected_positions = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let Some(position) = canonical_rows.iter().position(|candidate| candidate == row) else {
            return Err(VmError::InvalidConfig(format!(
                "binary-step activation benchmark received non-canonical row ({}, {})",
                row.input, row.output
            )));
        };
        if selected_positions.contains(&position) {
            return Err(VmError::InvalidConfig(format!(
                "binary-step activation benchmark received duplicate row ({}, {})",
                row.input, row.output
            )));
        }
        selected_positions.push(position);
    }
    let required_log_size = canonical_rows
        .len()
        .next_power_of_two()
        .trailing_zeros()
        .max(LOG_N_LANES)
        .max(4);
    Ok(ActivationBundle {
        log_size: required_log_size,
        canonical_rows,
        claimed_rows: claimed_rows.to_vec(),
    })
}

fn build_row2_bundle(
    canonical_rows: Vec<(u16, u16)>,
    claimed_rows: &[(u16, u16)],
) -> Result<Row2Bundle> {
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
    let required_log_size = canonical_rows
        .len()
        .next_power_of_two()
        .trailing_zeros()
        .max(LOG_N_LANES)
        .max(4);
    Ok(Row2Bundle {
        log_size: required_log_size,
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
    let selector =
        BaseColumn::from_iter(padded.iter().enumerate().map(|(index, _)| {
            BaseField::from(u32::from(bundle.selected_positions.contains(&index)))
        }));
    vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, lhs).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, rhs).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, selector)
            .bit_reverse(),
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

fn softmax_selector_base_trace(
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

fn activation_selector_base_trace(
    bundle: &ActivationBundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_activation_rows(bundle.log_size, &bundle.claimed_rows);
    let table = bundle.canonical_rows.clone();
    let domain = CanonicCoset::new(bundle.log_size).circle_domain();
    let input = BaseColumn::from_iter(
        padded
            .iter()
            .map(|row| BaseField::from((row.input as i32).rem_euclid(1 << 31) as u32)),
    );
    let output = BaseColumn::from_iter(padded.iter().map(|row| BaseField::from(row.output as u32)));
    let mut columns = vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, input).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, output).bit_reverse(),
    ];
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

fn softmax_selector_arithmetic_component(
    log_size: u32,
) -> FrameworkComponent<SoftmaxSelectorArithmeticEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        SoftmaxSelectorArithmeticEval { log_size },
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

fn activation_selector_arithmetic_component(
    log_size: u32,
) -> FrameworkComponent<ActivationSelectorArithmeticEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        ActivationSelectorArithmeticEval { log_size },
        SecureField::zero(),
    )
}

fn mix_claimed_rows(channel: &mut Blake2sM31Channel, claimed_rows: &[(u16, u16)]) {
    channel.mix_u64(claimed_rows.len() as u64);
    for row in claimed_rows {
        channel.mix_u64(row.0 as u64);
        channel.mix_u64(row.1 as u64);
    }
}

fn mix_activation_claimed_rows(
    channel: &mut Blake2sM31Channel,
    claimed_rows: &[Phase3LookupTableRow],
) {
    channel.mix_u64(claimed_rows.len() as u64);
    for row in claimed_rows {
        channel.mix_u64((row.input as i32).rem_euclid(1 << 31) as u64);
        channel.mix_u64(row.output as u64);
    }
}

fn claimed_rows_to_arrays(rows: &[(u16, u16)]) -> Vec<[u16; 2]> {
    rows.iter().map(|row| [row.0, row.1]).collect()
}

fn claimed_rows_to_signed_arrays(rows: &[(u16, u16)]) -> Vec<[i16; 2]> {
    rows.iter()
        .map(|row| [row.0 as i16, row.1 as i16])
        .collect()
}

fn activation_rows_to_arrays(rows: &[Phase3LookupTableRow]) -> Vec<[i16; 2]> {
    rows.iter()
        .map(|row| [row.input, row.output as i16])
        .collect()
}

fn primitive_benchmark_stark_proof_size(proof: &[u8]) -> Result<usize> {
    let payload: PrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(payload.stark_proof.size_estimate())
}

fn shared_normalization_stark_proof_size(proof: &[u8]) -> Result<usize> {
    let payload: SharedNormalizationProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(payload.stark_proof.size_estimate())
}

fn shared_activation_stark_proof_size(proof: &[u8]) -> Result<usize> {
    let payload: SharedActivationProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(payload.stark_proof.size_estimate())
}

fn signed_primitive_benchmark_stark_proof_size(proof: &[u8]) -> Result<usize> {
    let payload: SignedPrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(payload.stark_proof.size_estimate())
}

fn column_id(id: &str) -> stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId {
    stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId { id: id.to_string() }
}

fn const_f<E: EvalAtRow>(value: u32) -> E::F {
    E::F::from(BaseField::from(value))
}

fn const_signed_f<E: EvalAtRow>(value: i16) -> E::F {
    E::F::from(BaseField::from((value as i32).rem_euclid(1 << 31) as u32))
}

fn padded_activation_rows(
    log_size: u32,
    rows: &[Phase3LookupTableRow],
) -> Vec<Phase3LookupTableRow> {
    let row_count = 1usize << log_size;
    let mut padded = rows.to_vec();
    let pad = padded.last().cloned().expect("non-empty activation rows");
    padded.resize(row_count, pad);
    padded
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn primitive_benchmark_runs_all_matched_paths() {
        let report =
            run_stwo_primitive_lookup_vs_naive_benchmark().expect("primitive benchmark should run");
        assert_eq!(report.rows.len(), 4);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report
            .rows
            .iter()
            .any(|row| row.backend_variant == "lookup_logup"
                && row.primitive == "rmsnorm_q8_inv_sqrt"));
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

    #[test]
    fn primitive_benchmark_rejects_duplicate_rows() {
        let error = prove_softmax_exp_lookup(&[(0, 256), (0, 256)])
            .expect_err("duplicate rows must be rejected");
        assert!(error.to_string().contains("duplicate row"));
    }

    #[test]
    fn primitive_benchmark_rejects_malformed_softmax_lookup_proof() {
        let error = verify_softmax_exp_lookup(&SOFTMAX_EXP_ROWS, b"{")
            .expect_err("malformed proof JSON must fail");
        assert!(matches!(error, VmError::Serialization(_)));
    }

    #[test]
    fn primitive_benchmark_rejects_tampered_softmax_lookup_rows() {
        let proof = prove_softmax_exp_lookup(&SOFTMAX_EXP_ROWS).expect("softmax proof");
        let mut payload: PrimitiveBenchmarkProofPayload =
            serde_json::from_slice(&proof).expect("deserialize proof payload");
        payload.canonical_rows.reverse();
        let tampered = serde_json::to_vec(&payload).expect("serialize tampered payload");

        let error = verify_softmax_exp_lookup(&SOFTMAX_EXP_ROWS, &tampered)
            .expect_err("tampered canonical rows must be rejected");
        assert!(error
            .to_string()
            .contains("softmax-exp lookup proof uses non-canonical table rows"));
    }

    #[test]
    fn primitive_benchmark_rejects_tampered_softmax_lookup_shape() {
        let proof = prove_softmax_exp_lookup(&SOFTMAX_EXP_ROWS).expect("softmax proof");
        let mut payload: PrimitiveBenchmarkProofPayload =
            serde_json::from_slice(&proof).expect("deserialize proof payload");
        payload.stark_proof.0.commitments.clear();
        let tampered = serde_json::to_vec(&payload).expect("serialize tampered payload");

        let error = verify_softmax_exp_lookup(&SOFTMAX_EXP_ROWS, &tampered)
            .expect_err("shortened commitment payload must be rejected");
        assert!(error
            .to_string()
            .contains("softmax-exp lookup proof uses a malformed or tampered commitment payload"));
    }

    #[test]
    fn primitive_benchmark_rejects_tampered_arithmetic_rows() {
        let proof =
            prove_rmsnorm_selector_arithmetic(&RMSNORM_ROWS).expect("arithmetic benchmark proof");
        let mut payload: PrimitiveBenchmarkProofPayload =
            serde_json::from_slice(&proof).expect("deserialize proof payload");
        payload.canonical_rows.reverse();
        let tampered = serde_json::to_vec(&payload).expect("serialize tampered payload");

        let error = verify_rmsnorm_selector_arithmetic(&RMSNORM_ROWS, &tampered)
            .expect_err("tampered arithmetic proof must be rejected");
        assert!(error
            .to_string()
            .contains("primitive arithmetic proof uses non-canonical rows"));
    }

    #[test]
    fn primitive_benchmark_rejects_tampered_arithmetic_shape() {
        let proof =
            prove_rmsnorm_selector_arithmetic(&RMSNORM_ROWS).expect("arithmetic benchmark proof");
        let mut payload: PrimitiveBenchmarkProofPayload =
            serde_json::from_slice(&proof).expect("deserialize proof payload");
        payload.stark_proof.0.commitments.clear();
        let tampered = serde_json::to_vec(&payload).expect("serialize tampered payload");

        let error = verify_rmsnorm_selector_arithmetic(&RMSNORM_ROWS, &tampered)
            .expect_err("shortened arithmetic commitment payload must be rejected");
        assert!(error.to_string().contains(
            "primitive arithmetic proof uses a malformed or tampered commitment payload"
        ));
    }

    #[test]
    fn primitive_benchmark_rejects_arithmetic_proof_for_different_claimed_rows() {
        let proof =
            prove_rmsnorm_selector_arithmetic(&[(4, 128)]).expect("arithmetic benchmark proof");
        let error = verify_rmsnorm_selector_arithmetic(&[(16, 64)], &proof)
            .expect_err("claimed_rows mismatch must fail verification");
        assert!(error
            .to_string()
            .contains("S-two primitive verification failed"));
    }

    #[test]
    fn primitive_benchmark_rejects_polynomial_proof_for_different_claimed_rows() {
        let proof = prove_softmax_exp_polynomial(&[(0, 256), (2, 94)]).expect("polynomial proof");
        let error = verify_softmax_exp_polynomial(&[(0, 256), (4, 35)], &proof)
            .expect_err("polynomial claimed_rows mismatch must fail verification");
        assert!(error
            .to_string()
            .contains("S-two primitive verification failed"));
    }

    #[test]
    fn primitive_benchmark_rejects_lookup_proof_for_different_claimed_rows() {
        let proof = prove_softmax_exp_lookup(&[(0, 256), (2, 94)]).expect("lookup proof");
        let error = verify_softmax_exp_lookup(&[(0, 256), (4, 35)], &proof)
            .expect_err("lookup claimed_rows mismatch must fail verification");
        assert!(error
            .to_string()
            .contains("S-two softmax-exp lookup verification failed"));
    }

    #[test]
    fn shared_table_reuse_softmax_selector_arithmetic_rejects_different_claimed_rows() {
        let proof =
            prove_softmax_selector_arithmetic(&[(0, 256), (2, 94)]).expect("selector proof");
        let error = verify_softmax_selector_arithmetic(&[(0, 256), (4, 35)], &proof)
            .expect_err("selector claimed_rows mismatch must fail verification");
        assert!(error
            .to_string()
            .contains("S-two primitive verification failed"));
    }

    #[test]
    #[ignore = "expensive shared-table reuse benchmark"]
    fn shared_table_reuse_benchmark_runs_all_modes() {
        let report = run_stwo_shared_table_reuse_benchmark_with_options(false)
            .expect("shared-table reuse benchmark should run");
        assert_eq!(report.rows.len(), 33);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report
            .rows
            .iter()
            .all(|row| row.serialized_bytes >= row.proof_bytes));
        assert!(report.rows.iter().any(|row| {
            row.primitive == "rmsnorm_q8_inv_sqrt"
                && row.backend_variant == "shared_table_lookup_reuse"
                && row.steps == 5
        }));
        assert!(report.rows.iter().any(|row| {
            row.primitive == "softmax_exp_q8"
                && row.backend_variant == "shared_table_lookup_reuse"
                && row.steps == 8
        }));
        assert!(report.rows.iter().any(|row| {
            row.primitive == "binary_step_activation"
                && row.backend_variant == "shared_table_lookup_reuse"
                && row.steps == 3
        }));
    }

    #[test]
    fn shared_table_reuse_benchmark_smoke_paths_verify_without_timings() {
        let report = run_stwo_shared_table_reuse_benchmark_for_step_counts(&[1], &[1], &[1], false)
            .expect("shared-table reuse smoke benchmark should run");
        assert_eq!(report.rows.len(), 9);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report.rows.iter().all(|row| row.prove_ms == 0));
        assert!(report.rows.iter().all(|row| row.verify_ms == 0));
    }

    #[test]
    fn shared_table_reuse_benchmark_rejects_out_of_range_step_count() {
        let err = claimed_row_prefix(&softmax_canonical_rows(), 9, "softmax_exp_q8")
            .expect_err("step count beyond canonical table must fail");
        assert!(err
            .to_string()
            .contains("only 8 canonical rows are available"));
    }

    #[test]
    fn shared_table_reuse_activation_rejects_out_of_range_step_count() {
        let err = activation_claimed_row_prefix(&activation_canonical_rows(), 4)
            .expect_err("activation step count beyond canonical table must fail");
        assert!(err
            .to_string()
            .contains("only 3 canonical rows are available"));
    }

    #[test]
    fn shared_table_reuse_rmsnorm_rows_remain_in_phase5_table() {
        let live_rows: std::collections::BTreeSet<_> = phase5_normalization_table_rows()
            .into_iter()
            .map(|row| (row.norm_sq, row.inv_sqrt_q8))
            .collect();
        for row in RMSNORM_REUSE_ROWS {
            assert!(
                live_rows.contains(&row),
                "pinned shared-table RMSNorm row {:?} must remain in the Phase 5 table",
                row
            );
        }
    }
}
