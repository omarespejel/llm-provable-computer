use std::fs;
use std::path::Path;

use blake2::{Blake2b512, Digest};
use serde::{Deserialize, Serialize};

use crate::config::Attention2DMode;
use crate::engine::ExecutionResult;
use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};
use crate::interpreter::NativeInterpreter;
use crate::model::TransformerVm;
use crate::state::MachineState;
use crate::vanillastark::{FieldElement, MPolynomial, Stark};
use crate::verification::verify_model_against_native;

const PC: usize = 0;
const ACC: usize = 1;
const SP: usize = 2;
const ZERO: usize = 3;
const CARRY: usize = 4;
const HALTED: usize = 5;
const MACHINE_STATE_PREFIX: usize = 6;

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

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VanillaStarkExecutionClaim {
    pub program: Program,
    pub attention_mode: Attention2DMode,
    pub steps: usize,
    pub final_state: MachineState,
    pub options: VanillaStarkProofOptions,
    #[serde(default)]
    pub equivalence: Option<ExecutionEquivalenceMetadata>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VanillaStarkExecutionProof {
    pub claim: VanillaStarkExecutionClaim,
    pub proof: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionEquivalenceMetadata {
    pub checked_steps: usize,
    pub transformer_fingerprint: String,
    pub native_fingerprint: String,
}

#[derive(Debug, Clone, Copy)]
struct ColumnLayout {
    memory_size: usize,
}

impl ColumnLayout {
    fn new(memory_size: usize) -> Self {
        Self { memory_size }
    }

    fn mem(&self, index: usize) -> usize {
        MACHINE_STATE_PREFIX + index
    }

    fn acc_inv(&self) -> usize {
        MACHINE_STATE_PREFIX + self.memory_size
    }

    fn sp_nonzero_inv(&self) -> usize {
        self.acc_inv() + 1
    }

    fn sp_not_top_inv(&self) -> usize {
        self.acc_inv() + 2
    }

    fn machine_state_register_count(&self) -> usize {
        MACHINE_STATE_PREFIX + self.memory_size
    }

    fn register_count(&self) -> usize {
        self.machine_state_register_count() + 3
    }
}

#[derive(Debug, Clone)]
struct VmAir {
    program: Program,
    layout: ColumnLayout,
}

impl VmAir {
    fn new(program: Program) -> Self {
        let layout = ColumnLayout::new(program.memory_size());
        Self { program, layout }
    }

    fn register_count(&self) -> usize {
        self.layout.register_count()
    }

    fn transition_degree_bound(&self) -> usize {
        self.transition_constraints()
            .iter()
            .flat_map(|constraint| constraint.dictionary.keys())
            .map(|powers| powers.iter().sum())
            .max()
            .unwrap_or(1)
            .max(2)
    }

    fn boundary_constraints(
        &self,
        steps: usize,
        final_state: &MachineState,
    ) -> Vec<(usize, usize, FieldElement)> {
        let mut boundary = Vec::new();
        let initial = MachineState::with_memory(self.program.initial_memory().to_vec());

        for (register, value) in state_public_registers(&self.layout, &initial)
            .into_iter()
            .enumerate()
        {
            boundary.push((0, register, value));
        }

        for (register, value) in state_public_registers(&self.layout, final_state)
            .into_iter()
            .enumerate()
        {
            boundary.push((steps, register, value));
        }

        boundary
    }

    fn transition_constraints(&self) -> Vec<MPolynomial> {
        let register_count = self.layout.register_count();
        let variables = MPolynomial::variables(1 + 2 * register_count);
        let current = variables[1..1 + register_count].to_vec();
        let next = variables[1 + register_count..].to_vec();

        let current_pc = current[PC].clone();
        let current_acc = current[ACC].clone();
        let current_sp = current[SP].clone();
        let current_zero = current[ZERO].clone();
        let current_memory: Vec<MPolynomial> = (0..self.layout.memory_size)
            .map(|index| current[self.layout.mem(index)].clone())
            .collect();

        let next_pc = next[PC].clone();
        let next_acc = next[ACC].clone();
        let next_sp = next[SP].clone();
        let next_zero = next[ZERO].clone();
        let next_carry = next[CARRY].clone();
        let next_halted = next[HALTED].clone();
        let next_memory: Vec<MPolynomial> = (0..self.layout.memory_size)
            .map(|index| next[self.layout.mem(index)].clone())
            .collect();
        let next_acc_inv = next[self.layout.acc_inv()].clone();
        let current_sp_nonzero_inv = current[self.layout.sp_nonzero_inv()].clone();
        let current_sp_not_top_inv = current[self.layout.sp_not_top_inv()].clone();

        let one = mp_constant(1);
        let zero = MPolynomial::zero();
        let current_stack_read = self.stack_read_expression(&current_sp, &current_memory);
        let current_stack_write_selectors = self.stack_write_selectors(&current_sp);
        let valid_pc = self.domain_zerofier(&current_pc, self.program.len());
        let valid_sp = self.domain_zerofier(&current_sp, self.layout.memory_size + 1);
        let mut expected_next_pc = MPolynomial::zero();
        let mut expected_next_acc = MPolynomial::zero();
        let mut expected_next_sp = MPolynomial::zero();
        let mut expected_next_halted = MPolynomial::zero();
        let mut expected_next_memory = vec![MPolynomial::zero(); self.layout.memory_size];
        let mut push_or_call_selector = MPolynomial::zero();
        let mut pop_or_ret_selector = MPolynomial::zero();

        let pc_selectors = self.pc_selectors(&current_pc);

        for (pc, instruction) in self.program.instructions().iter().enumerate() {
            let selector = pc_selectors[pc].clone();
            let next_pc_constant = mp_constant(i128::from((pc as u8).wrapping_add(1)));

            match *instruction {
                Instruction::Nop => {
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::LoadImmediate(value) => {
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc =
                        expected_next_acc + selector.clone() * mp_constant(i128::from(value));
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::Load(address) => {
                    let loaded = current_memory[address as usize].clone();
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc = expected_next_acc + selector.clone() * loaded;
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::Store(address) => {
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        let value = if index == address as usize {
                            current_acc.clone()
                        } else {
                            current_memory[index].clone()
                        };
                        *expected = expected.clone() + pc_selectors[pc].clone() * value;
                    }
                }
                Instruction::Push => {
                    push_or_call_selector = push_or_call_selector + selector.clone();
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp =
                        expected_next_sp + selector.clone() * (current_sp.clone() - one.clone());
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        let write_selector = current_stack_write_selectors[index].clone();
                        let value = write_selector.clone() * current_acc.clone()
                            + (one.clone() - write_selector) * current_memory[index].clone();
                        *expected = expected.clone() + pc_selectors[pc].clone() * value;
                    }
                }
                Instruction::Pop => {
                    pop_or_ret_selector = pop_or_ret_selector + selector.clone();
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc =
                        expected_next_acc + selector.clone() * current_stack_read.clone();
                    expected_next_sp =
                        expected_next_sp + selector.clone() * (current_sp.clone() + one.clone());
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::AddImmediate(value) => {
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc = expected_next_acc
                        + selector.clone() * (current_acc.clone() + mp_constant(i128::from(value)));
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::AddMemory(address) => {
                    let rhs = current_memory[address as usize].clone();
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc =
                        expected_next_acc + selector.clone() * (current_acc.clone() + rhs);
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::SubImmediate(value) => {
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc = expected_next_acc
                        + selector.clone() * (current_acc.clone() - mp_constant(i128::from(value)));
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::SubMemory(address) => {
                    let rhs = current_memory[address as usize].clone();
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc =
                        expected_next_acc + selector.clone() * (current_acc.clone() - rhs);
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::MulImmediate(value) => {
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc = expected_next_acc
                        + selector.clone() * (current_acc.clone() * mp_constant(i128::from(value)));
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::MulMemory(address) => {
                    let rhs = current_memory[address as usize].clone();
                    expected_next_pc = expected_next_pc + selector.clone() * next_pc_constant;
                    expected_next_acc =
                        expected_next_acc + selector.clone() * (current_acc.clone() * rhs);
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::Call(target) => {
                    push_or_call_selector = push_or_call_selector + selector.clone();
                    expected_next_pc =
                        expected_next_pc + selector.clone() * mp_constant(i128::from(target));
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp =
                        expected_next_sp + selector.clone() * (current_sp.clone() - one.clone());
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        let write_selector = current_stack_write_selectors[index].clone();
                        let return_address = mp_constant(i128::from((pc as u8).wrapping_add(1)));
                        let value = write_selector.clone() * return_address
                            + (one.clone() - write_selector) * current_memory[index].clone();
                        *expected = expected.clone() + pc_selectors[pc].clone() * value;
                    }
                }
                Instruction::Ret => {
                    pop_or_ret_selector = pop_or_ret_selector + selector.clone();
                    expected_next_pc =
                        expected_next_pc + selector.clone() * current_stack_read.clone();
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp =
                        expected_next_sp + selector.clone() * (current_sp.clone() + one.clone());
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::Jump(target) => {
                    expected_next_pc =
                        expected_next_pc + selector.clone() * mp_constant(i128::from(target));
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::JumpIfZero(target) => {
                    let target_expr = current_zero.clone() * mp_constant(i128::from(target))
                        + (one.clone() - current_zero.clone()) * next_pc_constant;
                    expected_next_pc = expected_next_pc + selector.clone() * target_expr;
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::JumpIfNotZero(target) => {
                    let target_expr = current_zero.clone() * next_pc_constant
                        + (one.clone() - current_zero.clone()) * mp_constant(i128::from(target));
                    expected_next_pc = expected_next_pc + selector.clone() * target_expr;
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * zero.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::Halt => {
                    expected_next_pc =
                        expected_next_pc + selector.clone() * mp_constant(i128::from(pc as i16));
                    expected_next_acc = expected_next_acc + selector.clone() * current_acc.clone();
                    expected_next_sp = expected_next_sp + selector.clone() * current_sp.clone();
                    expected_next_halted = expected_next_halted + selector * one.clone();
                    for (index, expected) in expected_next_memory.iter_mut().enumerate() {
                        *expected = expected.clone()
                            + pc_selectors[pc].clone() * current_memory[index].clone();
                    }
                }
                Instruction::AndImmediate(_)
                | Instruction::AndMemory(_)
                | Instruction::OrImmediate(_)
                | Instruction::OrMemory(_)
                | Instruction::XorImmediate(_)
                | Instruction::XorMemory(_)
                | Instruction::CmpImmediate(_)
                | Instruction::CmpMemory(_) => {
                    unreachable!("unsupported instructions are filtered before AIR construction")
                }
            }
        }

        let mut constraints = vec![
            valid_pc,
            valid_sp,
            current_zero.clone() * (current_zero.clone() - one.clone()),
            current[HALTED].clone(),
            current[CARRY].clone(),
            next_pc - expected_next_pc,
            next_acc.clone() - expected_next_acc,
            next_sp - expected_next_sp,
            next_halted - expected_next_halted,
            next_carry,
            next_acc.clone() * next_acc_inv - (one.clone() - next_zero.clone()),
            next_zero * next_acc,
        ];

        if !self.layout.memory_size.is_zero() {
            constraints.push(
                push_or_call_selector * (current_sp.clone() * current_sp_nonzero_inv - one.clone()),
            );
            constraints.push(
                pop_or_ret_selector
                    * ((current_sp - mp_constant(self.layout.memory_size as i128))
                        * current_sp_not_top_inv
                        - one.clone()),
            );
        }

        for (index, expected) in expected_next_memory.into_iter().enumerate() {
            constraints.push(next_memory[index].clone() - expected);
        }

        constraints
    }

    fn pc_selectors(&self, pc: &MPolynomial) -> Vec<MPolynomial> {
        let domain: Vec<i128> = (0..self.program.len()).map(|value| value as i128).collect();
        domain
            .iter()
            .map(|&point| lagrange_selector(pc, &domain, point))
            .collect()
    }

    fn stack_write_selectors(&self, sp: &MPolynomial) -> Vec<MPolynomial> {
        let domain: Vec<i128> = (0..=self.layout.memory_size)
            .map(|value| value as i128)
            .collect();
        (0..self.layout.memory_size)
            .map(|index| lagrange_selector(sp, &domain, index as i128 + 1))
            .collect()
    }

    fn stack_read_expression(&self, sp: &MPolynomial, memory: &[MPolynomial]) -> MPolynomial {
        let domain: Vec<i128> = (0..=self.layout.memory_size)
            .map(|value| value as i128)
            .collect();
        let mut expression = MPolynomial::zero();
        for (index, cell) in memory.iter().enumerate() {
            expression = expression + lagrange_selector(sp, &domain, index as i128) * cell.clone();
        }
        expression
    }

    fn domain_zerofier(&self, variable: &MPolynomial, size: usize) -> MPolynomial {
        let mut polynomial = mp_constant(1);
        for point in 0..size {
            polynomial = polynomial * (variable.clone() - mp_constant(point as i128));
        }
        polynomial
    }
}

pub fn prove_execution_stark(
    model: &TransformerVm,
    max_steps: usize,
) -> Result<VanillaStarkExecutionProof> {
    prove_execution_stark_with_options(model, max_steps, VanillaStarkProofOptions::default())
}

pub fn prove_execution_stark_with_options(
    model: &TransformerVm,
    max_steps: usize,
    options: VanillaStarkProofOptions,
) -> Result<VanillaStarkExecutionProof> {
    validate_proof_inputs(model.program(), &model.config().attention_mode)?;
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

    let mut interpreter = NativeInterpreter::new(
        model.program().clone(),
        model.config().attention_mode.clone(),
        max_steps,
    );
    let result = interpreter.run()?;
    if !result.halted {
        return Err(VmError::UnsupportedProof(format!(
            "execution must halt before proving; stopped after {} steps without HALT",
            result.steps
        )));
    }
    if interpreter.trace().iter().any(|state| state.carry_flag) {
        return Err(VmError::UnsupportedProof(
            "overflowing arithmetic is not supported by the vanilla STARK AIR".to_string(),
        ));
    }

    let air = VmAir::new(model.program().clone());
    let trace = execution_trace_rows(&air.layout, interpreter.trace());
    let claim = VanillaStarkExecutionClaim {
        program: model.program().clone(),
        attention_mode: model.config().attention_mode.clone(),
        steps: result.steps,
        final_state: result.final_state.clone(),
        options: options.clone(),
        equivalence: Some(equivalence),
    };
    let stark = Stark::new(
        options.expansion_factor,
        options.num_colinearity_checks,
        options.security_level,
        air.register_count(),
        claim.steps + 1,
        air.transition_degree_bound(),
    );
    let proof = stark.prove(
        &trace,
        &air.transition_constraints(),
        &air.boundary_constraints(claim.steps, &claim.final_state),
    );

    Ok(VanillaStarkExecutionProof { claim, proof })
}

pub fn verify_execution_stark(proof: &VanillaStarkExecutionProof) -> Result<bool> {
    validate_proof_inputs(&proof.claim.program, &proof.claim.attention_mode)?;
    validate_public_state(&proof.claim.program, &proof.claim.final_state)?;
    validate_equivalence_metadata(&proof.claim)?;

    if !proof.claim.final_state.halted {
        return Err(VmError::UnsupportedProof(
            "the public claim must end in a halted state".to_string(),
        ));
    }
    if proof.claim.final_state.carry_flag {
        return Err(VmError::UnsupportedProof(
            "carry-flag claims are not supported by the vanilla STARK AIR".to_string(),
        ));
    }

    let air = VmAir::new(proof.claim.program.clone());
    let stark = Stark::new(
        proof.claim.options.expansion_factor,
        proof.claim.options.num_colinearity_checks,
        proof.claim.options.security_level,
        air.register_count(),
        proof.claim.steps + 1,
        air.transition_degree_bound(),
    );

    Ok(stark.verify(
        &proof.proof,
        &air.transition_constraints(),
        &air.boundary_constraints(proof.claim.steps, &proof.claim.final_state),
    ))
}

pub(crate) fn validate_execution_stark_support(
    program: &Program,
    attention_mode: &Attention2DMode,
) -> Result<()> {
    validate_proof_inputs(program, attention_mode)
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

fn validate_proof_inputs(program: &Program, attention_mode: &Attention2DMode) -> Result<()> {
    if program.is_empty() {
        return Err(VmError::UnsupportedProof(
            "cannot prove an empty program".to_string(),
        ));
    }

    if !matches!(attention_mode, Attention2DMode::AverageHard) {
        return Err(VmError::UnsupportedProof(format!(
            "vanilla STARK proofs currently support only `average-hard` attention, got `{attention_mode}`"
        )));
    }

    for instruction in program.instructions() {
        match instruction {
            Instruction::AndImmediate(_)
            | Instruction::AndMemory(_)
            | Instruction::OrImmediate(_)
            | Instruction::OrMemory(_)
            | Instruction::XorImmediate(_)
            | Instruction::XorMemory(_)
            | Instruction::CmpImmediate(_)
            | Instruction::CmpMemory(_) => {
                return Err(VmError::UnsupportedProof(format!(
                    "instruction `{instruction}` is not yet supported by the vanilla STARK AIR"
                )));
            }
            _ => {}
        }
    }

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

fn validate_equivalence_metadata(claim: &VanillaStarkExecutionClaim) -> Result<()> {
    let Some(metadata) = &claim.equivalence else {
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

fn execution_trace_rows(layout: &ColumnLayout, trace: &[MachineState]) -> Vec<Vec<FieldElement>> {
    trace
        .iter()
        .map(|state| {
            let acc = field_from_i128(i128::from(state.acc));
            let sp = field_from_i128(i128::from(state.sp));
            let sp_minus_top = field_from_i128(i128::from(state.sp) - layout.memory_size as i128);
            let mut row = Vec::with_capacity(layout.register_count());
            row.push(field_from_i128(i128::from(state.pc)));
            row.push(acc);
            row.push(sp);
            row.push(field_from_bool(state.zero_flag));
            row.push(field_from_bool(state.carry_flag));
            row.push(field_from_bool(state.halted));
            row.extend(
                state
                    .memory
                    .iter()
                    .copied()
                    .map(|value| field_from_i128(i128::from(value))),
            );
            row.push(inverse_or_zero(acc));
            row.push(inverse_or_zero(sp));
            row.push(inverse_or_zero(sp_minus_top));
            row
        })
        .collect()
}

fn state_public_registers(layout: &ColumnLayout, state: &MachineState) -> Vec<FieldElement> {
    let mut registers = Vec::with_capacity(layout.machine_state_register_count());
    registers.push(field_from_i128(i128::from(state.pc)));
    registers.push(field_from_i128(i128::from(state.acc)));
    registers.push(field_from_i128(i128::from(state.sp)));
    registers.push(field_from_bool(state.zero_flag));
    registers.push(field_from_bool(state.carry_flag));
    registers.push(field_from_bool(state.halted));
    registers.extend(
        state
            .memory
            .iter()
            .copied()
            .map(|value| field_from_i128(i128::from(value))),
    );
    registers
}

fn lagrange_selector(variable: &MPolynomial, domain: &[i128], point: i128) -> MPolynomial {
    let mut selector = mp_constant(1);
    for &other in domain {
        if other == point {
            continue;
        }
        let denominator = field_from_i128(point - other).inverse();
        selector =
            selector * (variable.clone() - mp_constant(other)) * MPolynomial::constant(denominator);
    }
    selector
}

fn mp_constant(value: i128) -> MPolynomial {
    MPolynomial::constant(field_from_i128(value))
}

fn field_from_bool(value: bool) -> FieldElement {
    field_from_i128(if value { 1 } else { 0 })
}

fn field_from_i128(value: i128) -> FieldElement {
    if value >= 0 {
        FieldElement::new(value as u128)
    } else {
        -FieldElement::new(value.unsigned_abs())
    }
}

fn inverse_or_zero(value: FieldElement) -> FieldElement {
    if value.is_zero() {
        FieldElement::zero()
    } else {
        value.inverse()
    }
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

trait IsZeroExt {
    fn is_zero(&self) -> bool;
}

impl IsZeroExt for usize {
    fn is_zero(&self) -> bool {
        *self == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ProgramCompiler, TransformerVmConfig};

    fn prove_program(path: &str, max_steps: usize) -> VanillaStarkExecutionProof {
        let source = std::fs::read_to_string(path).expect("program source");
        let model = ProgramCompiler
            .compile_source(&source, TransformerVmConfig::default())
            .expect("compile");
        prove_execution_stark(&model, max_steps).expect("prove")
    }

    #[test]
    fn addition_round_trips_through_stark_proof() {
        let proof = prove_program("programs/addition.tvm", 32);
        assert!(verify_execution_stark(&proof).expect("verify"));
        assert_eq!(proof.claim.final_state.acc, 8);
    }

    #[test]
    fn small_loop_round_trips_through_stark_proof() {
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
        let proof = prove_execution_stark(&model, 128).expect("prove");
        assert!(verify_execution_stark(&proof).expect("verify"));
        assert_eq!(proof.claim.final_state.acc, 2);
    }

    #[test]
    fn stack_and_subroutine_round_trip_through_stark_proof() {
        for (path, max_steps, expected_acc) in [
            ("programs/stack_roundtrip.tvm", 32, 42),
            ("programs/subroutine_addition.tvm", 64, 42),
        ] {
            let proof = prove_program(path, max_steps);
            assert!(verify_execution_stark(&proof).expect("verify"), "{path}");
            assert_eq!(proof.claim.final_state.acc, expected_acc, "{path}");
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
    fn proof_claim_includes_equivalence_metadata() {
        let proof = prove_program("programs/addition.tvm", 32);
        let metadata = proof.claim.equivalence.expect("equivalence metadata");
        assert_eq!(metadata.checked_steps, proof.claim.steps);
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
}
