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
    let (transformer, peers) = verification
        .engines
        .split_first()
        .expect("verify_engines always returns at least one result");
    let native = peers
        .first()
        .expect("verify_engines returned fewer than two engine results");

    Ok(ExecutionComparison {
        checked_steps: verification.checked_steps,
        transformer: transformer.result.clone(),
        native: native.result.clone(),
    })
}

pub fn verify_engines(engines: &mut [&mut dyn ExecutionEngine]) -> Result<VerificationResult> {
    if engines.len() < 2 {
        return Err(VmError::InvalidConfig(
            "verify_engines requires at least two engines".to_string(),
        ));
    }

    let (reference, peers) = engines
        .split_first_mut()
        .expect("verified at least one reference engine");
    let reference_name = reference.name().to_string();
    let reference_state = reference.state().clone();
    compare_state(0, "initial state", &reference_name, &reference_state, peers)?;

    let mut checked_steps = 0usize;

    loop {
        let reference_halted = reference.is_halted();
        for engine in peers.iter() {
            if engine.is_halted() != reference_halted {
                return Err(mismatch(
                    max_step_count(&**reference, peers),
                    format_completion_mismatch(&**reference, peers),
                ));
            }
        }

        if reference_halted {
            break;
        }

        let expected_instruction = reference.next_instruction()?;
        let reference_step = reference.step_count();
        let reference_name = reference.name().to_string();
        for engine in peers.iter() {
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

        reference.step()?;
        for engine in peers.iter_mut() {
            engine.step()?;
        }

        checked_steps = reference.step_count();
        compare_last_event(checked_steps, &**reference, peers)?;
    }

    let mut results = Vec::with_capacity(peers.len() + 1);
    results.push(VerifiedEngine {
        name: reference.name().to_string(),
        result: reference.run()?,
    });
    for engine in peers.iter_mut() {
        results.push(VerifiedEngine {
            name: engine.name().to_string(),
            result: engine.run()?,
        });
    }

    let (reference_result, peers) = results
        .split_first()
        .expect("reference result should always be present");
    for engine in peers {
        if engine.result.steps != reference_result.result.steps {
            return Err(mismatch(
                reference_result.result.steps.max(engine.result.steps),
                format!(
                    "step count mismatch: {}={}, {}={}",
                    reference_result.name,
                    reference_result.result.steps,
                    engine.name,
                    engine.result.steps
                ),
            ));
        }
        if engine.result.halted != reference_result.result.halted {
            return Err(mismatch(
                reference_result.result.steps.max(engine.result.steps),
                format!(
                    "halt flag mismatch: {}={}, {}={}",
                    reference_result.name,
                    reference_result.result.halted,
                    engine.name,
                    engine.result.halted
                ),
            ));
        }
        compare_result_state(
            &reference_result.result,
            &reference_result.name,
            &engine.result,
            &engine.name,
        )?;
    }

    Ok(VerificationResult {
        checked_steps,
        engines: results,
    })
}

fn compare_last_event(
    step: usize,
    reference: &dyn ExecutionEngine,
    peers: &[&mut dyn ExecutionEngine],
) -> Result<()> {
    let reference_name = reference.name().to_string();
    let reference = reference
        .events()
        .last()
        .cloned()
        .ok_or_else(|| mismatch(step, format!("{reference_name} produced no trace event")))?;

    for engine in peers {
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

fn format_completion_mismatch(
    reference: &dyn ExecutionEngine,
    peers: &[&mut dyn ExecutionEngine],
) -> String {
    let mut summary = Vec::with_capacity(peers.len() + 1);
    summary.push(format!("{}={}", reference.name(), reference.is_halted()));
    summary.extend(
        peers
            .iter()
            .map(|engine| format!("{}={}", engine.name(), engine.is_halted())),
    );
    let summary = summary.join(", ");
    format!("engine completion diverged: {summary}")
}

fn max_step_count(reference: &dyn ExecutionEngine, peers: &[&mut dyn ExecutionEngine]) -> usize {
    peers
        .iter()
        .fold(reference.step_count(), |max_steps, engine| {
            max_steps.max(engine.step_count())
        })
}

fn mismatch(step: usize, message: impl Into<String>) -> VmError {
    VmError::ExecutionMismatch {
        step,
        message: message.into(),
    }
}
