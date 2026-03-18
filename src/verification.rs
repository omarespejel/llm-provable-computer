use crate::engine::{ExecutionEngine, ExecutionResult, VerificationResult, VerifiedEngine};
use crate::error::{Result, VmError};
use crate::interpreter::NativeInterpreter;
use crate::runtime::ExecutionRuntime;
use crate::state::MachineState;
use crate::TransformerVm;

#[derive(Debug, Clone)]
pub struct ExecutionComparison {
    pub checked_steps: usize,
    pub transformer: ExecutionResult,
    pub native: ExecutionResult,
}

pub fn verify_model_against_native(
    model: TransformerVm,
    max_steps: usize,
) -> Result<ExecutionComparison> {
    let mut transformer = ExecutionRuntime::new(model.clone(), max_steps);
    let mut native = NativeInterpreter::new(
        model.program().clone(),
        model.config().attention_mode.clone(),
        max_steps,
    );
    let verification = verify_engines(&mut [&mut transformer, &mut native])?;

    Ok(ExecutionComparison {
        checked_steps: verification.checked_steps,
        transformer: verification.engines[0].result.clone(),
        native: verification.engines[1].result.clone(),
    })
}

pub fn verify_engines(engines: &mut [&mut dyn ExecutionEngine]) -> Result<VerificationResult> {
    if engines.len() < 2 {
        return Err(VmError::InvalidConfig(
            "verify_engines requires at least two engines".to_string(),
        ));
    }

    let reference_name = engines[0].name().to_string();
    let reference_state = engines[0].state().clone();
    compare_state(
        0,
        "initial state",
        &reference_name,
        &reference_state,
        &engines[1..],
    )?;

    let mut checked_steps = 0usize;

    loop {
        let reference_halted = engines[0].is_halted();
        for engine in &engines[1..] {
            if engine.is_halted() != reference_halted {
                return Err(mismatch(
                    engines
                        .iter()
                        .map(|engine| engine.step_count())
                        .max()
                        .unwrap_or(0),
                    format_completion_mismatch(engines),
                ));
            }
        }

        if reference_halted {
            break;
        }

        let expected_instruction = engines[0].next_instruction()?;
        let reference_step = engines[0].step_count();
        let reference_name = engines[0].name().to_string();
        for engine in &engines[1..] {
            let actual_instruction = engine.next_instruction()?;
            if actual_instruction != expected_instruction {
                return Err(mismatch(
                    reference_step.max(engine.step_count()),
                    format!(
                        "next instruction mismatch: {}={:?}, {}={:?}",
                        reference_name,
                        expected_instruction,
                        engine.name(),
                        actual_instruction
                    ),
                ));
            }
        }

        for engine in engines.iter_mut() {
            engine.step()?;
        }

        checked_steps = engines[0].step_count();
        compare_last_event(checked_steps, engines)?;
    }

    let mut results = Vec::with_capacity(engines.len());
    for engine in engines.iter_mut() {
        results.push(VerifiedEngine {
            name: engine.name().to_string(),
            result: engine.run()?,
        });
    }

    let reference_result = results[0].result.clone();
    let reference_name = results[0].name.clone();
    for engine in &results[1..] {
        if engine.result.steps != reference_result.steps {
            return Err(mismatch(
                reference_result.steps.max(engine.result.steps),
                format!(
                    "step count mismatch: {}={}, {}={}",
                    reference_name, reference_result.steps, engine.name, engine.result.steps
                ),
            ));
        }
        if engine.result.halted != reference_result.halted {
            return Err(mismatch(
                reference_result.steps.max(engine.result.steps),
                format!(
                    "halt flag mismatch: {}={}, {}={}",
                    reference_name, reference_result.halted, engine.name, engine.result.halted
                ),
            ));
        }
        compare_result_state(
            &reference_result,
            &reference_name,
            &engine.result,
            &engine.name,
        )?;
    }

    Ok(VerificationResult {
        checked_steps,
        engines: results,
    })
}

fn compare_last_event(step: usize, engines: &[&mut dyn ExecutionEngine]) -> Result<()> {
    let reference_name = engines[0].name().to_string();
    let reference = engines[0]
        .events()
        .last()
        .cloned()
        .ok_or_else(|| mismatch(step, format!("{reference_name} produced no trace event")))?;

    for engine in &engines[1..] {
        let event = engine
            .events()
            .last()
            .ok_or_else(|| mismatch(step, format!("{} produced no trace event", engine.name())))?;

        if event.instruction != reference.instruction {
            return Err(mismatch(
                step,
                format!(
                    "instruction mismatch: {}=`{}`, {}=`{}`",
                    reference_name,
                    reference.instruction,
                    engine.name(),
                    event.instruction
                ),
            ));
        }

        compare_state_pair(
            step,
            "state before instruction",
            &reference_name,
            &reference.state_before,
            engine.name(),
            &event.state_before,
        )?;
        compare_state_pair(
            step,
            "state after instruction",
            &reference_name,
            &reference.state_after,
            engine.name(),
            &event.state_after,
        )?;
    }

    Ok(())
}

fn compare_state(
    step: usize,
    label: &str,
    reference_name: &str,
    reference_state: &MachineState,
    engines: &[&mut dyn ExecutionEngine],
) -> Result<()> {
    for engine in engines {
        compare_state_pair(
            step,
            label,
            reference_name,
            reference_state,
            engine.name(),
            engine.state(),
        )?;
    }
    Ok(())
}

fn compare_result_state(
    reference: &ExecutionResult,
    reference_name: &str,
    actual: &ExecutionResult,
    actual_name: &str,
) -> Result<()> {
    compare_state_pair(
        reference.steps.max(actual.steps),
        "final state",
        reference_name,
        &reference.final_state,
        actual_name,
        &actual.final_state,
    )
}

fn compare_state_pair(
    step: usize,
    label: &str,
    left_name: &str,
    left: &MachineState,
    right_name: &str,
    right: &MachineState,
) -> Result<()> {
    if left == right {
        return Ok(());
    }

    Err(mismatch(
        step,
        format!(
            "{label} mismatch:\n{left_name}={}\n{right_name}={}",
            describe_state(left),
            describe_state(right)
        ),
    ))
}

fn describe_state(state: &MachineState) -> String {
    format!(
        "pc={} acc={} sp={} zero={} carry={} halted={} memory={:?}",
        state.pc,
        state.acc,
        state.sp,
        state.zero_flag,
        state.carry_flag,
        state.halted,
        state.memory
    )
}

fn format_completion_mismatch(engines: &[&mut dyn ExecutionEngine]) -> String {
    let summary = engines
        .iter()
        .map(|engine| format!("{}={}", engine.name(), engine.is_halted()))
        .collect::<Vec<_>>()
        .join(", ");
    format!("engine completion diverged: {summary}")
}

fn mismatch(step: usize, message: impl Into<String>) -> VmError {
    VmError::ExecutionMismatch {
        step,
        message: message.into(),
    }
}
