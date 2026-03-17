use crate::error::{Result, VmError};
use crate::interpreter::{NativeExecutionResult, NativeInterpreter};
use crate::runtime::{ExecutionResult, ExecutionRuntime};
use crate::state::MachineState;
use crate::TransformerVm;

#[derive(Debug, Clone)]
pub struct ExecutionComparison {
    pub checked_steps: usize,
    pub transformer: ExecutionResult,
    pub native: NativeExecutionResult,
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

    compare_state(0, "initial state", transformer.state(), native.state())?;

    loop {
        let transformer_finished =
            transformer.state().halted || transformer.step_count() >= transformer.max_steps();
        let native_finished = native.state().halted || native.step_count() >= native.max_steps();

        if transformer_finished || native_finished {
            if transformer_finished != native_finished {
                return Err(VmError::ExecutionMismatch {
                    step: transformer.step_count().max(native.step_count()),
                    message: format!(
                        "engine completion diverged: transformer_finished={transformer_finished}, native_finished={native_finished}"
                    ),
                });
            }
            break;
        }

        transformer.step()?;
        native.step()?;

        let step = transformer.step_count();
        let transformer_event = transformer
            .events()
            .last()
            .ok_or_else(|| mismatch(step, "transformer runtime produced no trace event"))?;
        let native_event = native
            .events()
            .last()
            .ok_or_else(|| mismatch(step, "native interpreter produced no trace event"))?;

        if transformer_event.instruction != native_event.instruction {
            return Err(mismatch(
                step,
                format!(
                    "instruction mismatch: transformer=`{}`, native=`{}`",
                    transformer_event.instruction, native_event.instruction
                ),
            ));
        }

        compare_state(
            step,
            "state before instruction",
            &transformer_event.state_before,
            &native_event.state_before,
        )?;
        compare_state(
            step,
            "state after instruction",
            &transformer_event.state_after,
            &native_event.state_after,
        )?;
    }

    let transformer_result = transformer.run()?;
    let native_result = native.run()?;

    if transformer_result.steps != native_result.steps {
        return Err(mismatch(
            transformer_result.steps.max(native_result.steps),
            format!(
                "step count mismatch: transformer={}, native={}",
                transformer_result.steps, native_result.steps
            ),
        ));
    }
    if transformer_result.halted != native_result.halted {
        return Err(mismatch(
            transformer_result.steps.max(native_result.steps),
            format!(
                "halt flag mismatch: transformer={}, native={}",
                transformer_result.halted, native_result.halted
            ),
        ));
    }
    compare_state(
        transformer_result.steps.max(native_result.steps),
        "final state",
        &transformer_result.final_state,
        &native_result.final_state,
    )?;

    Ok(ExecutionComparison {
        checked_steps: transformer_result.steps,
        transformer: transformer_result,
        native: native_result,
    })
}

fn compare_state(
    step: usize,
    label: &str,
    left: &MachineState,
    right: &MachineState,
) -> Result<()> {
    if left == right {
        return Ok(());
    }

    Err(mismatch(
        step,
        format!(
            "{label} mismatch:\ntransformer={}\nnative={}",
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

fn mismatch(step: usize, message: impl Into<String>) -> VmError {
    VmError::ExecutionMismatch {
        step,
        message: message.into(),
    }
}
