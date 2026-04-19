use ark_ff::Zero;
use blake2::{
    digest::{Update, VariableOutput},
    Blake2bVar,
};
use serde::{Deserialize, Serialize};
use stwo::core::air::Component;
use stwo::core::channel::{Blake2sM31Channel, Channel};
use stwo::core::fields::m31::BaseField;
use stwo::core::fields::qm31::SecureField;
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig};
use stwo::core::poly::circle::CanonicCoset;
use stwo::core::proof::StarkProof;
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sM31MerkleChannel, Blake2sM31MerkleHasher};
use stwo::core::verifier::verify;
use stwo::prover::backend::cpu::CpuBackend;
use stwo::prover::backend::{Col, Column};
use stwo::prover::poly::circle::{CircleEvaluation, PolyOps};
use stwo::prover::poly::{BitReversedOrder, NaturalOrder};
use stwo::prover::{prove, CommitmentSchemeProver};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::{
    EvalAtRow, FrameworkComponent, FrameworkEval, TraceLocationAllocator,
};

use super::recursion::{
    commit_phase43_history_replay_trace, verify_phase43_history_replay_trace,
    Phase43HistoryReplayTrace,
};
use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

pub const STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43: &str =
    "stwo-phase43-history-replay-projection-air-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43: &str =
    "phase43-history-replay-field-projection-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43: &str =
    "phase43_field_native_history_replay_projection_no_blake2b_compression";

const PHASE43_PROJECTION_ONE_COLUMN: &str = "phase43/history_replay_projection/one";
const PHASE43_PROJECTION_HASH_LIMBS: usize = 16;
const PHASE43_PROJECTION_PREFIX_WIDTH: usize = 13;
const PHASE43_PROJECTION_MAX_STEPS: usize = 64;
const M31_MODULUS: u32 = (1u32 << 31) - 1;

const STEP_INDEX_COL: usize = 0;
const PHASE12_FROM_STEP_COL: usize = 1;
const PHASE12_TO_STEP_COL: usize = 2;
const PHASE14_FROM_STEP_COL: usize = 3;
const PHASE14_TO_STEP_COL: usize = 4;
const PHASE12_FROM_POSITION_COL: usize = 5;
const PHASE12_TO_POSITION_COL: usize = 6;
const PHASE14_FROM_POSITION_COL: usize = 7;
const PHASE14_TO_POSITION_COL: usize = 8;
const PHASE12_FROM_HISTORY_LEN_COL: usize = 9;
const PHASE12_TO_HISTORY_LEN_COL: usize = 10;
const PHASE14_FROM_HISTORY_LEN_COL: usize = 11;
const PHASE14_TO_HISTORY_LEN_COL: usize = 12;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProjectionProofEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub phase43_trace_commitment: String,
    pub phase43_trace_version: String,
    pub total_steps: usize,
    pub pair_width: usize,
    pub projection_version: String,
    pub projection_row_count: usize,
    pub projection_column_count: usize,
    pub projection_commitment: String,
    pub projection_air_proof_claimed: bool,
    pub full_trace_commitment_proven: bool,
    pub cryptographic_compression_claimed: bool,
    pub blake2b_preimage_proven: bool,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
struct Phase43ProjectionProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

#[derive(Debug, Clone)]
struct Phase43ProjectionLayout {
    pair_width: usize,
}

impl Phase43ProjectionLayout {
    fn appended_pair_start(&self) -> usize {
        PHASE43_PROJECTION_PREFIX_WIDTH
    }

    fn input_lookup_start(&self) -> usize {
        self.appended_pair_start() + self.pair_width
    }

    fn output_lookup_start(&self) -> usize {
        self.input_lookup_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn phase12_from_public_start(&self) -> usize {
        self.output_lookup_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn phase12_to_public_start(&self) -> usize {
        self.phase12_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn phase14_from_public_start(&self) -> usize {
        self.phase12_to_public_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn phase14_to_public_start(&self) -> usize {
        self.phase14_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn column_count(&self) -> usize {
        self.phase14_to_public_start() + PHASE43_PROJECTION_HASH_LIMBS
    }
}

#[derive(Debug, Clone)]
struct Phase43Projection {
    layout: Phase43ProjectionLayout,
    rows: Vec<Vec<BaseField>>,
    commitment: String,
}

#[derive(Clone)]
struct Phase43ProjectionBundle {
    log_size: u32,
    projection: Phase43Projection,
    preprocessed_trace: Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>>,
    base_trace: Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>>,
}

#[derive(Debug, Clone)]
struct Phase43ProjectionEval {
    log_size: u32,
    layout: Phase43ProjectionLayout,
    expected_rows: Vec<Vec<BaseField>>,
}

impl FrameworkEval for Phase43ProjectionEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        let selector_degree_log = ceil_log2(self.expected_rows.len().max(2));
        self.log_size
            .saturating_add(selector_degree_log)
            .saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let one = E::F::from(base_u32(1));
        let preprocessed_one =
            eval.get_preprocessed_column(column_id(PHASE43_PROJECTION_ONE_COLUMN));
        add_base_constraint(&mut eval, preprocessed_one - one.clone());

        let column_count = self.layout.column_count();
        let mut columns = Vec::with_capacity(column_count);
        for _ in 0..column_count {
            columns.push(eval.next_trace_mask());
        }

        let step: E::F = current::<E>(&columns, STEP_INDEX_COL);
        let total_steps = self.expected_rows.len();
        let valid_step = step_set_polynomial::<E>(&step, total_steps);
        add_base_constraint(&mut eval, valid_step);

        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_FROM_STEP_COL) - step.clone(),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE14_FROM_STEP_COL) - step.clone(),
        );
        let expected_to_step = step.clone() + one;
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_TO_STEP_COL) - expected_to_step.clone(),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE14_TO_STEP_COL) - expected_to_step,
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_FROM_POSITION_COL)
                - current::<E>(&columns, PHASE14_FROM_POSITION_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_TO_POSITION_COL)
                - current::<E>(&columns, PHASE14_TO_POSITION_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_FROM_HISTORY_LEN_COL)
                - current::<E>(&columns, PHASE14_FROM_HISTORY_LEN_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_TO_HISTORY_LEN_COL)
                - current::<E>(&columns, PHASE14_TO_HISTORY_LEN_COL),
        );

        for (row_index, next_expected_row) in self.expected_rows.iter().enumerate().skip(1) {
            let previous_selector = lagrange_step_selector::<E>(&step, row_index - 1, total_steps);
            link_column_to_expected(
                &mut eval,
                &columns,
                PHASE12_TO_POSITION_COL,
                next_expected_row[PHASE12_FROM_POSITION_COL],
                &previous_selector,
            );
            link_column_to_expected(
                &mut eval,
                &columns,
                PHASE14_TO_POSITION_COL,
                next_expected_row[PHASE14_FROM_POSITION_COL],
                &previous_selector,
            );
            link_column_to_expected(
                &mut eval,
                &columns,
                PHASE12_TO_HISTORY_LEN_COL,
                next_expected_row[PHASE12_FROM_HISTORY_LEN_COL],
                &previous_selector,
            );
            link_column_to_expected(
                &mut eval,
                &columns,
                PHASE14_TO_HISTORY_LEN_COL,
                next_expected_row[PHASE14_FROM_HISTORY_LEN_COL],
                &previous_selector,
            );
            link_column_range_to_expected(
                &mut eval,
                &columns,
                self.layout.phase12_to_public_start(),
                &next_expected_row[self.layout.phase12_from_public_start()
                    ..self.layout.phase12_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS],
                &previous_selector,
            );
            link_column_range_to_expected(
                &mut eval,
                &columns,
                self.layout.phase14_to_public_start(),
                &next_expected_row[self.layout.phase14_from_public_start()
                    ..self.layout.phase14_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS],
                &previous_selector,
            );
        }

        for (row_index, expected_row) in self.expected_rows.iter().enumerate() {
            let selector = lagrange_step_selector::<E>(
                &current::<E>(&columns, STEP_INDEX_COL),
                row_index,
                total_steps,
            );
            for (column_index, expected_value) in expected_row.iter().enumerate() {
                add_base_constraint(
                    &mut eval,
                    selector.clone()
                        * (current::<E>(&columns, column_index) - E::F::from(*expected_value)),
                );
            }
        }

        eval
    }
}

pub fn prove_phase43_history_replay_projection_envelope(
    trace: &Phase43HistoryReplayTrace,
) -> Result<Phase43HistoryReplayProjectionProofEnvelope> {
    let bundle = build_phase43_projection_bundle(trace)?;
    let proof = prove_phase43_projection(&bundle)?;
    Ok(Phase43HistoryReplayProjectionProofEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43.to_string(),
        statement_version: STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43.to_string(),
        semantic_scope: STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43.to_string(),
        phase43_trace_commitment: trace.trace_commitment.clone(),
        phase43_trace_version: trace.trace_version.clone(),
        total_steps: trace.total_steps,
        pair_width: trace.pair_width,
        projection_version: STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43.to_string(),
        projection_row_count: bundle.projection.rows.len(),
        projection_column_count: bundle.projection.layout.column_count(),
        projection_commitment: bundle.projection.commitment,
        projection_air_proof_claimed: true,
        full_trace_commitment_proven: false,
        cryptographic_compression_claimed: false,
        blake2b_preimage_proven: false,
        proof,
    })
}

pub fn verify_phase43_history_replay_projection_envelope(
    trace: &Phase43HistoryReplayTrace,
    envelope: &Phase43HistoryReplayProjectionProofEnvelope,
) -> Result<bool> {
    let bundle = build_phase43_projection_bundle(trace)?;
    validate_phase43_projection_envelope(trace, envelope, &bundle.projection)?;

    let payload: Phase43ProjectionProofPayload = serde_json::from_slice(&envelope.proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    if stark_proof.commitments.len() < 2 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection proof expected at least 2 trace commitments, got {}",
            stark_proof.commitments.len()
        )));
    }

    let component = phase43_projection_component(&bundle);
    let pcs_config = stark_proof.config;
    let verifier_channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let sizes = component.trace_log_degree_bounds();
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], verifier_channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], verifier_channel);
    mix_phase43_projection_claim(verifier_channel, &bundle.projection)?;

    Ok(verify(
        &[&component],
        verifier_channel,
        commitment_scheme,
        stark_proof,
    )
    .is_ok())
}

fn prove_phase43_projection(bundle: &Phase43ProjectionBundle) -> Result<Vec<u8>> {
    let component = phase43_projection_component(bundle);
    let config = PcsConfig::default();
    let twiddles = CpuBackend::precompute_twiddles(
        CanonicCoset::new(
            component.max_constraint_log_degree_bound() + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );

    let prover_channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<CpuBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.preprocessed_trace.clone());
    tree_builder.commit(prover_channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.base_trace.clone());
    tree_builder.commit(prover_channel);
    mix_phase43_projection_claim(prover_channel, &bundle.projection)?;

    let stark_proof = prove::<CpuBackend, Blake2sM31MerkleChannel>(
        &[&component],
        prover_channel,
        commitment_scheme,
    )
    .map_err(|error| {
        VmError::UnsupportedProof(format!(
            "S-two Phase43 history replay projection proving failed: {error}"
        ))
    })?;

    serde_json::to_vec(&Phase43ProjectionProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn build_phase43_projection_bundle(
    trace: &Phase43HistoryReplayTrace,
) -> Result<Phase43ProjectionBundle> {
    verify_phase43_history_replay_trace(trace)?;
    let projection = build_phase43_projection(trace)?;
    let row_count = projection.rows.len();
    let log_size = row_count.ilog2();
    let preprocessed_trace = phase43_projection_preprocessed_trace(log_size);
    let base_trace = phase43_projection_base_trace(log_size, &projection)?;
    Ok(Phase43ProjectionBundle {
        log_size,
        projection,
        preprocessed_trace,
        base_trace,
    })
}

fn build_phase43_projection(trace: &Phase43HistoryReplayTrace) -> Result<Phase43Projection> {
    if trace.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof requires at least one replay row".to_string(),
        ));
    }
    if trace.total_steps < 2 {
        return Err(VmError::UnsupportedProof(
            "Phase 43 projection proof prototype currently requires at least 2 replay rows"
                .to_string(),
        ));
    }
    if trace.total_steps > PHASE43_PROJECTION_MAX_STEPS {
        return Err(VmError::UnsupportedProof(format!(
            "Phase 43 projection proof prototype caps total_steps at {}, got {}",
            PHASE43_PROJECTION_MAX_STEPS, trace.total_steps
        )));
    }
    if !trace.total_steps.is_power_of_two() {
        return Err(VmError::UnsupportedProof(format!(
            "Phase 43 projection proof prototype currently requires power-of-two total_steps, got {}",
            trace.total_steps
        )));
    }
    if trace.pair_width == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof requires pair_width > 0".to_string(),
        ));
    }

    let layout = Phase43ProjectionLayout {
        pair_width: trace.pair_width,
    };
    let mut rows = Vec::with_capacity(trace.rows.len());
    for (row_index, row) in trace.rows.iter().enumerate() {
        let mut values = Vec::with_capacity(layout.column_count());
        values.push(usize_base("row.step_index", row.step_index)?);
        values.push(usize_base(
            "row.phase12_from_state.step_index",
            row.phase12_from_state.step_index,
        )?);
        values.push(usize_base(
            "row.phase12_to_state.step_index",
            row.phase12_to_state.step_index,
        )?);
        values.push(usize_base(
            "row.phase14_from_state.step_index",
            row.phase14_from_state.step_index,
        )?);
        values.push(usize_base(
            "row.phase14_to_state.step_index",
            row.phase14_to_state.step_index,
        )?);
        values.push(i16_base(row.phase12_from_state.position));
        values.push(i16_base(row.phase12_to_state.position));
        values.push(i16_base(row.phase14_from_state.position));
        values.push(i16_base(row.phase14_to_state.position));
        values.push(usize_base(
            "row.phase12_from_state.kv_history_length",
            row.phase12_from_state.kv_history_length,
        )?);
        values.push(usize_base(
            "row.phase12_to_state.kv_history_length",
            row.phase12_to_state.kv_history_length,
        )?);
        values.push(usize_base(
            "row.phase14_from_state.kv_history_length",
            row.phase14_from_state.kv_history_length,
        )?);
        values.push(usize_base(
            "row.phase14_to_state.kv_history_length",
            row.phase14_to_state.kv_history_length,
        )?);
        for (pair_index, value) in row.appended_pair.iter().enumerate() {
            values.push(i16_base_with_label(
                &format!("row[{row_index}].appended_pair[{pair_index}]"),
                *value,
            )?);
        }
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].input_lookup_rows_commitment"),
            &row.input_lookup_rows_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].output_lookup_rows_commitment"),
            &row.output_lookup_rows_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].phase12_from_state.public_state_commitment"),
            &row.phase12_from_state.public_state_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].phase12_to_state.public_state_commitment"),
            &row.phase12_to_state.public_state_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].phase14_from_state.public_state_commitment"),
            &row.phase14_from_state.public_state_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].phase14_to_state.public_state_commitment"),
            &row.phase14_to_state.public_state_commitment,
        )?);
        if values.len() != layout.column_count() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 projection row {row_index} produced {} columns, expected {}",
                values.len(),
                layout.column_count()
            )));
        }
        rows.push(values);
    }
    let mut projection = Phase43Projection {
        layout,
        rows,
        commitment: String::new(),
    };
    projection.commitment = commit_phase43_projection(&projection)?;
    Ok(projection)
}

fn phase43_projection_component(
    bundle: &Phase43ProjectionBundle,
) -> FrameworkComponent<Phase43ProjectionEval> {
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&[column_id(
        PHASE43_PROJECTION_ONE_COLUMN,
    )]);
    FrameworkComponent::new(
        &mut allocator,
        Phase43ProjectionEval {
            log_size: bundle.log_size,
            layout: bundle.projection.layout.clone(),
            expected_rows: bundle.projection.rows.clone(),
        },
        SecureField::zero(),
    )
}

fn phase43_projection_preprocessed_trace(
    log_size: u32,
) -> Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>> {
    let row_count = 1usize << log_size;
    let domain = CanonicCoset::new(log_size).circle_domain();
    let mut column = Col::<CpuBackend, BaseField>::zeros(row_count);
    for row_index in 0..row_count {
        column.set(row_index, base_u32(1));
    }
    vec![CircleEvaluation::<CpuBackend, BaseField, NaturalOrder>::new(domain, column).bit_reverse()]
}

fn phase43_projection_base_trace(
    log_size: u32,
    projection: &Phase43Projection,
) -> Result<Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>>> {
    let row_count = 1usize << log_size;
    if row_count != projection.rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection row_count {row_count} does not match rows.len()={}",
            projection.rows.len()
        )));
    }
    let domain = CanonicCoset::new(log_size).circle_domain();
    let mut columns = (0..projection.layout.column_count())
        .map(|_| Col::<CpuBackend, BaseField>::zeros(row_count))
        .collect::<Vec<_>>();
    for (row_index, row) in projection.rows.iter().enumerate() {
        for (column_index, value) in row.iter().enumerate() {
            columns[column_index].set(row_index, *value);
        }
    }
    Ok(columns
        .into_iter()
        .map(|column| {
            CircleEvaluation::<CpuBackend, BaseField, NaturalOrder>::new(domain, column)
                .bit_reverse()
        })
        .collect())
}

fn validate_phase43_projection_envelope(
    trace: &Phase43HistoryReplayTrace,
    envelope: &Phase43HistoryReplayProjectionProofEnvelope,
    projection: &Phase43Projection,
) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection proof backend `{}` is not `stwo`",
            envelope.proof_backend
        )));
    }
    if envelope.proof_backend_version != STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 43 projection proof backend version `{}` (expected `{}`)",
            envelope.proof_backend_version, STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43
        )));
    }
    if envelope.statement_version != STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 43 projection statement version `{}` (expected `{}`)",
            envelope.statement_version, STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43
        )));
    }
    if envelope.semantic_scope != STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 43 projection semantic scope `{}` (expected `{}`)",
            envelope.semantic_scope, STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43
        )));
    }
    let expected_trace_commitment = commit_phase43_history_replay_trace(trace)?;
    if envelope.phase43_trace_commitment != expected_trace_commitment
        || envelope.phase43_trace_commitment != trace.trace_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope does not bind the supplied Phase43 trace commitment"
                .to_string(),
        ));
    }
    if envelope.phase43_trace_version != trace.trace_version {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope trace version does not match the supplied trace"
                .to_string(),
        ));
    }
    if envelope.total_steps != trace.total_steps
        || envelope.projection_row_count != trace.total_steps
    {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope row counts do not match the supplied trace"
                .to_string(),
        ));
    }
    if envelope.pair_width != trace.pair_width {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope pair_width does not match the supplied trace"
                .to_string(),
        ));
    }
    if envelope.projection_version != STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 43 projection version `{}`",
            envelope.projection_version
        )));
    }
    if envelope.projection_column_count != projection.layout.column_count() {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope column count does not match recomputed projection"
                .to_string(),
        ));
    }
    if envelope.projection_commitment != projection.commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope commitment does not match recomputed projection"
                .to_string(),
        ));
    }
    if !envelope.projection_air_proof_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope must claim the projection AIR proof".to_string(),
        ));
    }
    if envelope.full_trace_commitment_proven {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof must not claim the full trace commitment is proven"
                .to_string(),
        ));
    }
    if envelope.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof must not claim cryptographic compression".to_string(),
        ));
    }
    if envelope.blake2b_preimage_proven {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof must not claim Blake2b preimage constraints".to_string(),
        ));
    }
    Ok(())
}

fn mix_phase43_projection_claim(
    channel: &mut Blake2sM31Channel,
    projection: &Phase43Projection,
) -> Result<()> {
    channel.mix_u64(projection.rows.len() as u64);
    channel.mix_u64(projection.layout.pair_width as u64);
    channel.mix_u64(projection.layout.column_count() as u64);
    channel.mix_u32s(&ascii_u32_words(
        STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43,
    ));
    channel.mix_u32s(&ascii_u32_words(&projection.commitment));
    Ok(())
}

fn commit_phase43_projection(projection: &Phase43Projection) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 43 projection commitment hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase43-history-replay-field-projection");
    update_usize(&mut hasher, projection.rows.len());
    update_usize(&mut hasher, projection.layout.pair_width);
    update_usize(&mut hasher, projection.layout.column_count());
    for (row_index, row) in projection.rows.iter().enumerate() {
        update_usize(&mut hasher, row_index);
        update_usize(&mut hasher, row.len());
        for value in row {
            hasher.update(&value.0.to_le_bytes());
        }
    }
    finalize_hash32(hasher, "Phase 43 projection commitment")
}

fn current<E: EvalAtRow>(columns: &[E::F], index: usize) -> E::F {
    columns[index].clone()
}

fn add_base_constraint<E: EvalAtRow>(eval: &mut E, constraint: E::F) {
    eval.add_constraint(constraint);
}

fn link_column_to_expected<E: EvalAtRow>(
    eval: &mut E,
    columns: &[E::F],
    current_column: usize,
    expected_value: BaseField,
    selector: &E::F,
) {
    let diff: E::F = current::<E>(columns, current_column) - E::F::from(expected_value);
    let constraint: E::F = selector.clone() * diff;
    add_base_constraint(eval, constraint);
}

fn link_column_range_to_expected<E: EvalAtRow>(
    eval: &mut E,
    columns: &[E::F],
    current_start: usize,
    expected_values: &[BaseField],
    selector: &E::F,
) {
    for (offset, expected_value) in expected_values.iter().enumerate() {
        link_column_to_expected(
            eval,
            columns,
            current_start + offset,
            *expected_value,
            selector,
        );
    }
}

fn step_set_polynomial<E: EvalAtRow>(step: &E::F, total_steps: usize) -> E::F {
    let mut acc = E::F::from(base_u32(1));
    for candidate in 0..total_steps {
        acc *= step.clone() - field_const::<E>(candidate);
    }
    acc
}

fn lagrange_step_selector<E: EvalAtRow>(step: &E::F, target: usize, total_steps: usize) -> E::F {
    let mut numerator = E::F::from(base_u32(1));
    let mut denominator = base_u32(1);
    for other in 0..total_steps {
        if other == target {
            continue;
        }
        numerator *= step.clone() - field_const::<E>(other);
        denominator *= base_i64(target as i64 - other as i64);
    }
    numerator * denominator.inverse()
}

fn field_const<E: EvalAtRow>(value: usize) -> E::F {
    E::F::from(usize_base("constraint constant", value).expect("small Phase43 projection constant"))
}

fn usize_base(label: &str, value: usize) -> Result<BaseField> {
    if value as u128 >= M31_MODULUS as u128 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection value `{label}`={value} exceeds M31 capacity"
        )));
    }
    Ok(base_u32(value as u32))
}

fn i16_base_with_label(label: &str, value: i16) -> Result<BaseField> {
    let encoded = i16_base(value);
    if encoded.0 >= M31_MODULUS {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection i16 value `{label}` encoded outside M31"
        )));
    }
    Ok(encoded)
}

fn i16_base(value: i16) -> BaseField {
    if value >= 0 {
        base_u32(value as u32)
    } else {
        base_u32((M31_MODULUS as i64 + value as i64) as u32)
    }
}

fn base_i64(value: i64) -> BaseField {
    base_u32(value.rem_euclid(M31_MODULUS as i64) as u32)
}

fn base_u32(value: u32) -> BaseField {
    BaseField::from_u32_unchecked(value)
}

fn hash32_u16_limbs(label: &str, value: &str) -> Result<Vec<BaseField>> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection `{label}` must be a 32-byte lowercase hex commitment"
        )));
    }
    let mut limbs = Vec::with_capacity(PHASE43_PROJECTION_HASH_LIMBS);
    for chunk in value.as_bytes().chunks_exact(4) {
        let text = std::str::from_utf8(chunk)
            .map_err(|error| VmError::InvalidConfig(error.to_string()))?;
        let limb = u16::from_str_radix(text, 16).map_err(|error| {
            VmError::InvalidConfig(format!(
                "Phase 43 projection `{label}` has invalid hex limb `{text}`: {error}"
            ))
        })?;
        limbs.push(base_u32(u32::from(limb)));
    }
    Ok(limbs)
}

fn update_len_prefixed(hasher: &mut Blake2bVar, bytes: &[u8]) {
    update_usize(hasher, bytes.len());
    hasher.update(bytes);
}

fn update_usize(hasher: &mut Blake2bVar, value: usize) {
    hasher.update(&(value as u128).to_le_bytes());
}

fn finalize_hash32(hasher: Blake2bVar, label: &str) -> Result<String> {
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .map_err(|err| VmError::InvalidConfig(format!("failed to finalize {label} hash: {err}")))?;
    Ok(lower_hex(&out))
}

fn lower_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn ascii_u32_words(value: &str) -> Vec<u32> {
    value
        .as_bytes()
        .chunks(4)
        .map(|chunk| {
            let mut word = [0u8; 4];
            word[..chunk.len()].copy_from_slice(chunk);
            u32::from_le_bytes(word)
        })
        .collect()
}

fn ceil_log2(value: usize) -> u32 {
    if value <= 1 {
        0
    } else {
        (value - 1).next_power_of_two().ilog2()
    }
}

fn column_id(id: &str) -> PreProcessedColumnId {
    PreProcessedColumnId { id: id.to_string() }
}

#[cfg(test)]
mod tests {
    use super::super::decoding::{
        commit_phase23_boundary_state, phase14_prepare_decoding_chain,
        phase30_prepare_decoding_step_proof_envelope_manifest,
        prove_phase12_decoding_demo_for_layout_steps, Phase12DecodingLayout,
        STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
    };
    use super::super::STWO_BACKEND_VERSION_PHASE12;
    use super::*;
    use crate::proof::CLAIM_STATEMENT_VERSION_V1;
    use stwo::core::pcs::TreeVec;
    use stwo_constraint_framework::assert_constraints_on_trace;

    fn hash32(hex: char) -> String {
        hex.to_string().repeat(64)
    }

    fn sample_trace() -> Phase43HistoryReplayTrace {
        let layout = Phase12DecodingLayout::new(2, 2).expect("valid layout");
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 2)
            .expect("generate Phase12 sample chain");
        let phase30 = phase30_prepare_decoding_step_proof_envelope_manifest(&chain)
            .expect("derive Phase30 sample manifest");
        let phase14 = phase14_prepare_decoding_chain(&chain).expect("derive Phase14 replay");
        let latest_cached_pair_range = chain
            .layout
            .latest_cached_pair_range()
            .expect("latest cached pair range");
        let rows = chain
            .steps
            .iter()
            .zip(phase14.steps.iter())
            .zip(phase30.envelopes.iter())
            .enumerate()
            .map(
                |(step_index, ((phase12_step, phase14_step), phase30_envelope))| {
                    super::super::Phase43HistoryReplayTraceRow {
                        step_index,
                        appended_pair: phase12_step.proof.claim.final_state.memory
                            [latest_cached_pair_range.clone()]
                        .to_vec(),
                        input_lookup_rows_commitment: phase12_step
                            .from_state
                            .lookup_rows_commitment
                            .clone(),
                        output_lookup_rows_commitment: phase12_step
                            .to_state
                            .lookup_rows_commitment
                            .clone(),
                        phase30_step_envelope_commitment: phase30_envelope
                            .envelope_commitment
                            .clone(),
                        phase12_from_state: phase12_step.from_state.clone(),
                        phase12_to_state: phase12_step.to_state.clone(),
                        phase14_from_state: phase14_step.from_state.clone(),
                        phase14_to_state: phase14_step.to_state.clone(),
                    }
                },
            )
            .collect::<Vec<_>>();
        let first = rows.first().expect("sample first row");
        let last = rows.last().expect("sample last row");
        let mut trace = Phase43HistoryReplayTrace {
            issue: super::super::STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
            trace_version: super::super::STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43.to_string(),
            relation_outcome: super::super::STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43.to_string(),
            transform_rule: super::super::STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43.to_string(),
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: STWO_BACKEND_VERSION_PHASE12.to_string(),
            statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
            phase42_witness_commitment: hash32('1'),
            phase29_contract_commitment: hash32('2'),
            phase28_aggregate_commitment: hash32('3'),
            phase30_source_chain_commitment: phase30.source_chain_commitment,
            phase30_step_envelopes_commitment: phase30.step_envelopes_commitment,
            total_steps: rows.len(),
            layout_commitment: first.phase12_from_state.layout_commitment.clone(),
            rolling_kv_pairs: chain.layout.rolling_kv_pairs,
            pair_width: chain.layout.pair_width,
            phase12_start_public_state_commitment: first
                .phase12_from_state
                .public_state_commitment
                .clone(),
            phase12_end_public_state_commitment: last
                .phase12_to_state
                .public_state_commitment
                .clone(),
            phase14_start_boundary_commitment: commit_phase23_boundary_state(
                &first.phase14_from_state,
            ),
            phase14_end_boundary_commitment: commit_phase23_boundary_state(&last.phase14_to_state),
            phase12_start_history_commitment: first
                .phase12_from_state
                .kv_history_commitment
                .clone(),
            phase12_end_history_commitment: last.phase12_to_state.kv_history_commitment.clone(),
            phase14_start_history_commitment: first
                .phase14_from_state
                .kv_history_commitment
                .clone(),
            phase14_end_history_commitment: last.phase14_to_state.kv_history_commitment.clone(),
            initial_kv_cache_commitment: first.phase12_from_state.kv_cache_commitment.clone(),
            appended_pairs_commitment: String::new(),
            lookup_rows_commitments_commitment: String::new(),
            rows,
            full_history_replay_required: true,
            cryptographic_compression_claimed: false,
            stwo_air_proof_claimed: false,
            trace_commitment: String::new(),
        };
        trace.appended_pairs_commitment = test_commit_appended_pairs(&trace);
        trace.lookup_rows_commitments_commitment = test_commit_lookup_rows(&trace);
        trace.trace_commitment = commit_phase43_history_replay_trace(&trace).expect("commit trace");
        verify_phase43_history_replay_trace(&trace).expect("sample trace verifies");
        trace
    }

    fn recommit_trace(trace: &mut Phase43HistoryReplayTrace) {
        trace.appended_pairs_commitment = test_commit_appended_pairs(trace);
        trace.lookup_rows_commitments_commitment = test_commit_lookup_rows(trace);
        trace.phase30_step_envelopes_commitment = test_commit_step_envelopes(trace);
        trace.trace_commitment =
            commit_phase43_history_replay_trace(trace).expect("recommit trace");
    }

    fn test_commit_appended_pairs(trace: &Phase43HistoryReplayTrace) -> String {
        let mut hasher = Blake2bVar::new(32).expect("hash init");
        update_len_prefixed(&mut hasher, b"phase42-source-appended-pairs");
        update_len_prefixed(&mut hasher, trace.layout_commitment.as_bytes());
        update_usize(&mut hasher, trace.pair_width);
        update_usize(&mut hasher, trace.rows.len());
        for (step_index, row) in trace.rows.iter().enumerate() {
            update_usize(&mut hasher, step_index);
            for value in &row.appended_pair {
                hasher.update(&value.to_le_bytes());
            }
        }
        finalize_hash32(hasher, "test appended pairs").expect("finalize hash")
    }

    fn test_commit_lookup_rows(trace: &Phase43HistoryReplayTrace) -> String {
        let mut hasher = Blake2bVar::new(32).expect("hash init");
        update_len_prefixed(&mut hasher, b"phase42-source-lookup-rows");
        update_len_prefixed(&mut hasher, trace.layout_commitment.as_bytes());
        update_usize(&mut hasher, trace.rows.len() + 1);
        update_usize(&mut hasher, 0);
        update_len_prefixed(
            &mut hasher,
            trace.rows[0].input_lookup_rows_commitment.as_bytes(),
        );
        for (index, row) in trace.rows.iter().enumerate() {
            update_usize(&mut hasher, index + 1);
            update_len_prefixed(&mut hasher, row.output_lookup_rows_commitment.as_bytes());
        }
        finalize_hash32(hasher, "test lookup rows").expect("finalize hash")
    }

    fn test_commit_step_envelopes(trace: &Phase43HistoryReplayTrace) -> String {
        let mut hasher = Blake2bVar::new(32).expect("hash init");
        hasher.update(STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30.as_bytes());
        hasher.update(b"step-envelope-list");
        hasher.update(&(trace.rows.len() as u64).to_le_bytes());
        for row in &trace.rows {
            hasher.update(row.phase30_step_envelope_commitment.as_bytes());
        }
        finalize_hash32(hasher, "test step envelopes").expect("finalize hash")
    }

    #[test]
    fn phase43_history_replay_projection_constraints_hold_on_sample_trace() {
        let trace = sample_trace();
        let bundle = build_phase43_projection_bundle(&trace).expect("build projection bundle");
        let preprocessed_columns = bundle
            .preprocessed_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let base_columns = bundle
            .base_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let preprocessed_refs = preprocessed_columns.iter().collect::<Vec<_>>();
        let base_refs = base_columns.iter().collect::<Vec<_>>();
        let trace_refs = TreeVec::new(vec![preprocessed_refs, base_refs]);
        let eval = Phase43ProjectionEval {
            log_size: bundle.log_size,
            layout: bundle.projection.layout.clone(),
            expected_rows: bundle.projection.rows.clone(),
        };
        assert_constraints_on_trace(
            &trace_refs,
            bundle.log_size,
            |row_eval| {
                eval.evaluate(row_eval);
            },
            SecureField::zero(),
        );
    }

    #[test]
    fn phase43_history_replay_projection_envelope_round_trips() {
        let trace = sample_trace();
        let envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        assert_eq!(envelope.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            envelope.proof_backend_version,
            STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43
        );
        assert!(envelope.projection_air_proof_claimed);
        assert!(!envelope.full_trace_commitment_proven);
        assert!(!envelope.cryptographic_compression_claimed);
        assert!(!envelope.blake2b_preimage_proven);
        assert!(
            verify_phase43_history_replay_projection_envelope(&trace, &envelope)
                .expect("verify Phase43 projection")
        );
    }

    #[test]
    fn phase43_history_replay_projection_rejects_tampered_metadata_flags() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        envelope.cryptographic_compression_claimed = true;
        let error = verify_phase43_history_replay_projection_envelope(&trace, &envelope)
            .expect_err("compression claim must be rejected");
        assert!(error.to_string().contains("cryptographic compression"));

        envelope.cryptographic_compression_claimed = false;
        envelope.full_trace_commitment_proven = true;
        let error = verify_phase43_history_replay_projection_envelope(&trace, &envelope)
            .expect_err("full trace proof claim must be rejected");
        assert!(error.to_string().contains("full trace commitment"));
    }

    #[test]
    fn phase43_history_replay_projection_rejects_single_row_without_panic() {
        let mut trace = sample_trace();
        trace.rows.truncate(1);
        trace.total_steps = 1;
        let last = trace.rows[0].clone();
        trace.phase12_end_public_state_commitment =
            last.phase12_to_state.public_state_commitment.clone();
        trace.phase14_end_boundary_commitment =
            commit_phase23_boundary_state(&last.phase14_to_state);
        trace.phase12_end_history_commitment = last.phase12_to_state.kv_history_commitment.clone();
        trace.phase14_end_history_commitment = last.phase14_to_state.kv_history_commitment.clone();
        recommit_trace(&mut trace);
        verify_phase43_history_replay_trace(&trace).expect("single-row trace verifies");

        let error = prove_phase43_history_replay_projection_envelope(&trace)
            .expect_err("single-row projection proof is explicitly unsupported");
        assert!(error.to_string().contains("at least 2 replay rows"));
    }

    #[test]
    fn phase43_history_replay_projection_rejects_trace_drift_against_envelope() {
        let trace = sample_trace();
        let envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        let mut drifted = trace.clone();
        drifted.rows[0].appended_pair[0] = drifted.rows[0].appended_pair[0].wrapping_add(1);
        recommit_trace(&mut drifted);
        verify_phase43_history_replay_trace(&drifted)
            .expect("drifted standalone trace still verifies");
        let error = verify_phase43_history_replay_projection_envelope(&drifted, &envelope)
            .expect_err("projection commitment drift must be rejected");
        assert!(error.to_string().contains("trace commitment"));
    }

    #[test]
    fn phase43_history_replay_projection_rejects_tampered_proof_bytes() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        let first = envelope.proof.first_mut().expect("proof bytes");
        *first ^= 0x01;
        let verification = verify_phase43_history_replay_projection_envelope(&trace, &envelope);
        assert!(verification.map(|ok| !ok).unwrap_or(true));
    }
}
