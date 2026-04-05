use ark_ff::Zero;
use serde_json;
use stwo::core::air::Component;
use stwo::core::channel::Blake2sM31Channel;
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
use stwo::prover::poly::BitReversedOrder;
use stwo::prover::{prove, CommitmentSchemeProver};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::{
    EvalAtRow, FrameworkComponent, FrameworkEval, TraceLocationAllocator,
};

use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};
use crate::proof::{PreparedExecutionWitness, StarkProofBackend, VanillaStarkExecutionProof};
use crate::state::MachineState;

pub const STWO_BACKEND_VERSION_PHASE4: &str = "stwo-phase4-addition-v1";

const LOG_SIZE: u32 = 2;
const ROW_COUNT: usize = 1 << LOG_SIZE;
const ADDITION_TRACE_LENGTH: usize = 4;
const FINAL_PC: u32 = 2;
const FINAL_ACC: u32 = 8;

const SELECTOR_LOADI: &str = "phase4/addition/selector_loadi";
const SELECTOR_ADDI: &str = "phase4/addition/selector_addi";
const SELECTOR_HALT: &str = "phase4/addition/selector_halt";
const IMMEDIATE: &str = "phase4/addition/immediate";
const PC_PLUS_ONE_WRAPPED: &str = "phase4/addition/pc_plus_one_wrapped";
const FIRST_ROW: &str = "phase4/addition/first_row";
const LAST_ROW: &str = "phase4/addition/last_row";

#[derive(Clone, Copy, Debug)]
struct Phase4AdditionEval;

impl FrameworkEval for Phase4AdditionEval {
    fn log_size(&self) -> u32 {
        LOG_SIZE
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        LOG_SIZE.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let pc = eval.next_trace_mask();
        let acc = eval.next_trace_mask();
        let next_pc = eval.next_trace_mask();
        let next_acc = eval.next_trace_mask();
        let halted = eval.next_trace_mask();
        let next_halted = eval.next_trace_mask();

        let is_loadi = eval.get_preprocessed_column(column_id(SELECTOR_LOADI));
        let is_addi = eval.get_preprocessed_column(column_id(SELECTOR_ADDI));
        let is_halt = eval.get_preprocessed_column(column_id(SELECTOR_HALT));
        let immediate = eval.get_preprocessed_column(column_id(IMMEDIATE));
        let pc_plus_one_wrapped = eval.get_preprocessed_column(column_id(PC_PLUS_ONE_WRAPPED));
        let is_first_row = eval.get_preprocessed_column(column_id(FIRST_ROW));
        let is_last_row = eval.get_preprocessed_column(column_id(LAST_ROW));

        let one = E::F::from(BaseField::from_u32_unchecked(1));
        let two = E::F::from(BaseField::from_u32_unchecked(FINAL_PC));
        let eight = E::F::from(BaseField::from_u32_unchecked(FINAL_ACC));

        for selector in [
            is_loadi.clone(),
            is_addi.clone(),
            is_halt.clone(),
            is_first_row.clone(),
            is_last_row.clone(),
        ] {
            eval.add_constraint(selector.clone() * (selector - one.clone()));
        }

        eval.add_constraint(is_loadi.clone() + is_addi.clone() + is_halt.clone() - one.clone());
        eval.add_constraint(halted.clone() * (halted.clone() - one.clone()));
        eval.add_constraint(next_halted.clone() * (next_halted.clone() - one.clone()));

        let expected_next_pc = is_halt.clone() * pc.clone()
            + (is_loadi.clone() + is_addi.clone()) * pc_plus_one_wrapped;
        let expected_next_acc = is_loadi.clone() * immediate.clone()
            + is_addi.clone() * (acc.clone() + immediate)
            + is_halt.clone() * acc.clone();
        let expected_next_halted = halted.clone() + (one.clone() - halted.clone()) * is_halt;

        eval.add_constraint(next_pc - expected_next_pc);
        eval.add_constraint(next_acc - expected_next_acc);
        eval.add_constraint(next_halted - expected_next_halted);

        eval.add_constraint(is_first_row.clone() * pc.clone());
        eval.add_constraint(is_first_row.clone() * acc.clone());
        eval.add_constraint(is_first_row * halted.clone());

        eval.add_constraint(is_last_row.clone() * (pc - two));
        eval.add_constraint(is_last_row.clone() * (acc - eight));
        eval.add_constraint(is_last_row * (halted - one));
        eval
    }
}

pub(crate) fn prove_phase4_addition_fixture(
    witness: PreparedExecutionWitness,
) -> Result<VanillaStarkExecutionProof> {
    validate_exact_addition_fixture(&witness.claim.program)?;
    validate_addition_state_trace(&witness.state_trace, witness.claim.steps)?;

    let config = PcsConfig::default();
    let component = addition_component();
    let twiddles = CpuBackend::precompute_twiddles(
        CanonicCoset::new(
            component.max_constraint_log_degree_bound() + config.fri_config.log_blowup_factor,
        )
        .circle_domain()
        .half_coset,
    );

    let prover_channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<CpuBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(preprocessed_trace());
    tree_builder.commit(prover_channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(trace_from_states(&witness.state_trace));
    tree_builder.commit(prover_channel);

    let stark_proof = prove::<CpuBackend, Blake2sM31MerkleChannel>(
        &[&component],
        prover_channel,
        commitment_scheme,
    )
    .map_err(|error| {
        VmError::UnsupportedProof(format!("S-two addition proving failed: {error}"))
    })?;

    let proof_bytes = serde_json::to_vec(&stark_proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;

    Ok(VanillaStarkExecutionProof {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_BACKEND_VERSION_PHASE4.to_string(),
        claim: witness.claim,
        proof: proof_bytes,
    })
}

pub(crate) fn verify_phase4_addition_fixture(proof: &VanillaStarkExecutionProof) -> Result<bool> {
    validate_exact_addition_fixture(&proof.claim.program)?;
    let stark_proof: StarkProof<Blake2sM31MerkleHasher> = serde_json::from_slice(&proof.proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;

    let config = stark_proof.config;
    let component = addition_component();
    let verifier_channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    let sizes = component.trace_log_degree_bounds();
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], verifier_channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], verifier_channel);

    Ok(verify(
        &[&component],
        verifier_channel,
        commitment_scheme,
        stark_proof,
    )
    .is_ok())
}

fn addition_component() -> FrameworkComponent<Phase4AdditionEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        Phase4AdditionEval,
        SecureField::zero(),
    )
}

fn preprocessed_trace() -> Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(LOG_SIZE).circle_domain();
    let rows = [
        [1u32, 0, 0, 5, 1, 1, 0],
        [0, 1, 0, 3, 2, 0, 0],
        [0, 0, 1, 0, 3, 0, 0],
        [0, 0, 1, 0, 3, 0, 1],
    ];
    (0..preprocessed_column_ids().len())
        .map(|column_index| {
            let mut column = Col::<CpuBackend, BaseField>::zeros(ROW_COUNT);
            for (row_index, row) in rows.iter().enumerate() {
                column.set(row_index, BaseField::from_u32_unchecked(row[column_index]));
            }
            CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, column)
        })
        .collect()
}

fn trace_from_states(
    states: &[MachineState],
) -> Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(LOG_SIZE).circle_domain();
    let transitions = [
        (&states[0], &states[1]),
        (&states[1], &states[2]),
        (&states[2], &states[3]),
        (&states[3], &states[3]),
    ];

    let mut columns = (0..6)
        .map(|_| Col::<CpuBackend, BaseField>::zeros(ROW_COUNT))
        .collect::<Vec<_>>();

    for (row_index, (current, next)) in transitions.into_iter().enumerate() {
        let row = [
            base(current.pc.into()),
            base(current.acc as u32),
            base(next.pc.into()),
            base(next.acc as u32),
            bool_base(current.halted),
            bool_base(next.halted),
        ];
        for (column_index, value) in row.into_iter().enumerate() {
            columns[column_index].set(row_index, value);
        }
    }

    columns
        .into_iter()
        .map(|column| {
            CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, column)
        })
        .collect()
}

fn preprocessed_column_ids() -> Vec<PreProcessedColumnId> {
    [
        SELECTOR_LOADI,
        SELECTOR_ADDI,
        SELECTOR_HALT,
        IMMEDIATE,
        PC_PLUS_ONE_WRAPPED,
        FIRST_ROW,
        LAST_ROW,
    ]
    .into_iter()
    .map(column_id)
    .collect()
}

fn column_id(id: &str) -> PreProcessedColumnId {
    PreProcessedColumnId { id: id.to_string() }
}

fn validate_exact_addition_fixture(program: &Program) -> Result<()> {
    let expected = [
        Instruction::LoadImmediate(5),
        Instruction::AddImmediate(3),
        Instruction::Halt,
    ];
    if program.memory_size() != 4
        || program.initial_memory() != [0, 0, 0, 0]
        || program.instructions() != expected
    {
        return Err(VmError::UnsupportedProof(
            "S-two backend Phase 4 currently proves only the exact `programs/addition.tvm` fixture"
                .to_string(),
        ));
    }
    Ok(())
}

fn validate_addition_state_trace(states: &[MachineState], steps: usize) -> Result<()> {
    if steps != 3 {
        return Err(VmError::UnsupportedProof(format!(
            "S-two addition pilot expects exactly 3 executed steps, got {steps}"
        )));
    }
    if states.len() != ADDITION_TRACE_LENGTH {
        return Err(VmError::UnsupportedProof(format!(
            "S-two addition pilot expects {ADDITION_TRACE_LENGTH} machine states, got {}",
            states.len()
        )));
    }

    let expected = [
        (0u8, 0i16, false),
        (1u8, 5i16, false),
        (2u8, 8i16, false),
        (2u8, 8i16, true),
    ];
    for (index, (state, (pc, acc, halted))) in states.iter().zip(expected).enumerate() {
        if state.pc != pc || state.acc != acc || state.halted != halted {
            return Err(VmError::UnsupportedProof(format!(
                "S-two addition pilot expected state {index} to be pc={pc}, acc={acc}, halted={halted}, got pc={}, acc={}, halted={}",
                state.pc, state.acc, state.halted
            )));
        }
        if state.sp != 4
            || state.zero_flag != (state.acc == 0)
            || state.carry_flag
            || state.memory != [0, 0, 0, 0]
        {
            return Err(VmError::UnsupportedProof(format!(
                "S-two addition pilot expected canonical zero-memory state shape at row {index}"
            )));
        }
    }
    Ok(())
}

fn base(value: u32) -> BaseField {
    BaseField::from_u32_unchecked(value)
}

fn bool_base(value: bool) -> BaseField {
    BaseField::from_u32_unchecked(u32::from(value))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ProgramCompiler, TransformerVmConfig};

    fn compile_program(path: &str) -> Program {
        let source = std::fs::read_to_string(path).expect("program source");
        ProgramCompiler
            .compile_source(&source, TransformerVmConfig::default())
            .expect("compile")
            .program()
            .clone()
    }

    #[test]
    fn phase4_exact_fixture_accepts_only_addition_program() {
        validate_exact_addition_fixture(&compile_program("programs/addition.tvm")).unwrap();
        let err = validate_exact_addition_fixture(&compile_program("programs/dot_product.tvm"))
            .expect_err("dot_product should stay unsupported");
        assert!(err
            .to_string()
            .contains("exact `programs/addition.tvm` fixture"));
    }

    #[test]
    fn phase4_addition_trace_builder_uses_four_rows() {
        let states = vec![
            MachineState::with_memory(vec![0, 0, 0, 0]),
            MachineState {
                pc: 1,
                acc: 5,
                sp: 4,
                zero_flag: false,
                carry_flag: false,
                halted: false,
                memory: vec![0, 0, 0, 0],
            },
            MachineState {
                pc: 2,
                acc: 8,
                sp: 4,
                zero_flag: false,
                carry_flag: false,
                halted: false,
                memory: vec![0, 0, 0, 0],
            },
            MachineState {
                pc: 2,
                acc: 8,
                sp: 4,
                zero_flag: false,
                carry_flag: false,
                halted: true,
                memory: vec![0, 0, 0, 0],
            },
        ];
        let trace = trace_from_states(&states);
        assert_eq!(trace.len(), 6);
        assert_eq!(trace[0].domain.log_size(), LOG_SIZE);
    }
}
