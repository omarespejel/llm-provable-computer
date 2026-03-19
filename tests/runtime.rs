use std::collections::BTreeSet;

use llm_provable_computer::{
    decode_state, encode_state, parse_program, Attention2DMode, ExecutionResult, ExecutionRuntime,
    MachineState, ProgramCompiler, TransformerVmConfig, VmError,
};

/// Load a `.tvm` fixture, compile with default config, and run.
fn run_fixture(path: &str, max_steps: usize) -> ExecutionResult {
    let source = std::fs::read_to_string(path).expect("fixture");
    let program = parse_program(&source).expect("parse");
    let model = ProgramCompiler
        .compile_program(program, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, max_steps);
    runtime.run().expect("run")
}

#[test]
fn state_encoding_round_trips() {
    let state = MachineState {
        pc: 19,
        acc: -1234,
        sp: 2,
        zero_flag: false,
        carry_flag: true,
        halted: false,
        memory: vec![4, 8, 15, 16],
    };

    let token = encode_state(&state, 36).expect("encode");
    let decoded = decode_state(&token, state.memory.clone()).expect("decode");
    assert_eq!(decoded, state);
}

#[test]
fn addition_program_executes_to_completion() {
    let source = r#"
        .memory 4
        LOADI 5
        ADD 3
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 8);
    assert_eq!(result.steps, 3);
}

#[test]
fn memory_roundtrip_uses_latest_store() {
    let source = r#"
        .memory 4
        LOADI 41
        STORE 2
        LOADI 0
        LOAD 2
        ADD 1
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 42);
    assert_eq!(result.final_state.memory[2], 41);
}

#[test]
fn branch_program_takes_zero_path() {
    let source = r#"
        LOADI 0
        JZ zero
        LOADI 7
        HALT
    zero:
        LOADI 42
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 42);
}

#[test]
fn counter_program_halts_with_expected_value() {
    let result = run_fixture("programs/counter.tvm", 128);
    assert!(result.halted);
    assert_eq!(result.final_state.acc, 5);
    assert_eq!(result.final_state.memory[0], 5);
}

#[test]
fn overflow_sets_carry_flag() {
    let source = r#"
        LOADI 32767
        ADD 1
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, i16::MIN);
    assert!(result.final_state.carry_flag);
}

#[test]
fn fibonacci_program_computes_fib_8() {
    let result = run_fixture("programs/fibonacci.tvm", 512);
    assert!(result.halted);
    assert_eq!(result.final_state.acc, 21, "Fibonacci(8) = 21");
}

#[test]
fn factorial_recursive_program_computes_5_factorial() {
    let result = run_fixture("programs/factorial_recursive.tvm", 128);
    assert!(result.halted);
    assert_eq!(result.final_state.acc, 120, "5! = 120");
    assert_eq!(result.final_state.sp, 11, "stack pointer restored after recursion");
}

#[test]
fn multiply_program_computes_6_times_7() {
    let result = run_fixture("programs/multiply.tvm", 256);
    assert!(result.halted);
    assert_eq!(result.final_state.acc, 42, "6 * 7 = 42");
}

#[test]
fn jnz_instruction_branches_when_nonzero() {
    let source = r#"
        LOADI 3
        JNZ skip
        LOADI 99
    skip:
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(
        result.final_state.acc, 3,
        "JNZ should have skipped LOADI 99"
    );
}

#[test]
fn jnz_instruction_falls_through_when_zero() {
    let source = r#"
        LOADI 0
        JNZ skip
        LOADI 77
        HALT
    skip:
        LOADI 99
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(
        result.final_state.acc, 77,
        "JNZ should fall through when zero"
    );
}

#[test]
fn subtraction_produces_correct_zero_flag() {
    let source = r#"
        .memory 4
        LOADI 10
        SUB 10
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 0);
    assert!(result.final_state.zero_flag);
}

#[test]
fn subm_reads_from_memory() {
    let source = r#"
        .memory 4
        .init 0 15
        LOADI 50
        SUBM 0
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 35, "50 - 15 = 35");
}

#[test]
fn nop_only_advances_pc() {
    let source = r#"
        LOADI 42
        NOP
        NOP
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 42);
    assert_eq!(result.steps, 4);
}

#[test]
fn multiple_store_load_cycles() {
    let source = r#"
        .memory 4
        LOADI 10
        STORE 0
        LOADI 20
        STORE 1
        LOADI 30
        STORE 2
        LOAD 0
        ADDM 1
        ADDM 2
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 32);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 60, "10 + 20 + 30 = 60");
    assert_eq!(result.final_state.memory[0], 10);
    assert_eq!(result.final_state.memory[1], 20);
    assert_eq!(result.final_state.memory[2], 30);
}

#[test]
fn execution_respects_max_steps_limit() {
    let source = r#"
        loop:
        NOP
        JMP loop
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 50);
    let result = runtime.run().expect("run");

    assert!(!result.halted);
    assert_eq!(result.steps, 50);
}

#[test]
fn deterministic_execution_same_output() {
    let source = std::fs::read_to_string("programs/fibonacci.tvm").expect("fixture");

    let run = || {
        let program = parse_program(&source).expect("parse");
        let model = ProgramCompiler
            .compile_program(program, TransformerVmConfig::default())
            .expect("compile");
        let mut runtime = ExecutionRuntime::new(model, 512);
        runtime.run().expect("run")
    };

    let result1 = run();
    let result2 = run();

    assert_eq!(result1.final_state, result2.final_state);
    assert_eq!(result1.steps, result2.steps);
}

#[test]
fn push_and_pop_round_trip_value_and_restore_stack_pointer() {
    let source = std::fs::read_to_string("programs/stack_roundtrip.tvm").expect("fixture");
    let model = ProgramCompiler
        .compile_source(&source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 42);
    assert_eq!(result.final_state.sp, 8);
    assert_eq!(result.final_state.memory[7], 42);
}

#[test]
fn call_and_ret_execute_subroutine_and_restore_stack_pointer() {
    let source = std::fs::read_to_string("programs/subroutine_addition.tvm").expect("fixture");
    let model = ProgramCompiler
        .compile_source(&source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 42);
    assert_eq!(result.final_state.sp, 8);
    assert_eq!(
        result.final_state.memory[7], 2,
        "return address is pushed on call"
    );
}

#[test]
fn nested_calls_use_lifo_stack() {
    let source = r#"
        .memory 8
        LOADI 10
        CALL outer
        HALT
    outer:
        ADD 5
        CALL inner
        RET
    inner:
        ADD 27
        RET
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 32);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 42);
    assert_eq!(result.final_state.sp, 8);
    assert_eq!(result.final_state.memory[7], 2, "outer return address");
    assert_eq!(result.final_state.memory[6], 5, "inner return address");
}

#[test]
fn pop_on_empty_stack_returns_underflow() {
    let source = r#"
        .memory 4
        POP
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let error = runtime.run().expect_err("pop should underflow");

    match error {
        VmError::StackUnderflow { sp, size } => {
            assert_eq!(sp, 4);
            assert_eq!(size, 4);
        }
        other => panic!("expected stack underflow, got {other:?}"),
    }
}

#[test]
fn push_on_full_stack_returns_overflow() {
    let source = r#"
        .memory 1
        LOADI 7
        PUSH
        LOADI 9
        PUSH
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let error = runtime.run().expect_err("second push should overflow");

    match error {
        VmError::StackOverflow { sp, size } => {
            assert_eq!(sp, 0);
            assert_eq!(size, 1);
        }
        other => panic!("expected stack overflow, got {other:?}"),
    }
}

#[test]
fn multi_layer_dispatch_executes_across_multiple_blocks() {
    let source = r#"
        LOADI 5
        ADD 3
        MUL 2
        XOR 6
        HALT
    "#;
    let config = TransformerVmConfig {
        num_layers: 3,
        ..TransformerVmConfig::default()
    };
    let model = ProgramCompiler
        .compile_source(source, config)
        .expect("compile");

    let declared_layers = (0..model.program().len())
        .map(|pc| model.dispatch_info(pc as u8).expect("dispatch").layer_idx)
        .collect::<BTreeSet<_>>();
    assert!(
        declared_layers.len() > 1,
        "expected multiple compiled layers, got {declared_layers:?}"
    );

    let mut runtime = ExecutionRuntime::new(model, 32);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 22, "((5 + 3) * 2) xor 6 = 22");

    let executed_layers = runtime
        .events()
        .iter()
        .filter_map(|event| event.layer_idx)
        .collect::<BTreeSet<_>>();
    assert!(
        executed_layers.len() > 1,
        "expected execution to visit multiple blocks, got {executed_layers:?}"
    );
}

#[test]
fn mulm_instruction_multiplies_by_memory_operand() {
    let source = r#"
        .memory 2
        .init 0 7
        LOADI 6
        MULM 0
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 42);
    assert!(!result.final_state.zero_flag);
}

#[test]
fn and_immediate_masks_accumulator_bits() {
    let source = r#"
        LOADI 13
        AND 10
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 8, "0b1101 & 0b1010 = 0b1000");
}

#[test]
fn orm_instruction_reads_memory_for_bitwise_or() {
    let source = r#"
        .memory 2
        .init 1 12
        LOADI 3
        ORM 1
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 15, "0b0011 | 0b1100 = 0b1111");
}

#[test]
fn xorm_instruction_reads_memory_for_bitwise_xor() {
    let source = r#"
        .memory 2
        .init 0 9
        LOADI 15
        XORM 0
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 6, "0b1111 xor 0b1001 = 0b0110");
}

#[test]
fn cmp_instruction_sets_difference_and_less_than_carry() {
    let source = r#"
        LOADI 10
        CMP 12
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, -2);
    assert!(!result.final_state.zero_flag);
    assert!(result.final_state.carry_flag);
}

#[test]
fn cmpm_instruction_detects_equality() {
    let source = r#"
        .memory 1
        .init 0 12
        LOADI 12
        CMPM 0
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 16);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 0);
    assert!(result.final_state.zero_flag);
    assert!(!result.final_state.carry_flag);
}

#[test]
fn attention_modes_change_memory_read_semantics() {
    let source = std::fs::read_to_string("programs/soft_attention_memory.tvm").expect("fixture");

    let run = |attention_mode| {
        let model = ProgramCompiler
            .compile_source(
                &source,
                TransformerVmConfig {
                    attention_mode,
                    ..TransformerVmConfig::default()
                },
            )
            .expect("compile");
        let mut runtime = ExecutionRuntime::new(model, 16);
        runtime.run().expect("run")
    };

    let average_hard = run(Attention2DMode::AverageHard);
    let softmax = run(Attention2DMode::Softmax);
    let hard_softmax = run(Attention2DMode::HardSoftmax { temperature: 10.0 });

    assert_eq!(average_hard.final_state.acc, 10);
    assert_eq!(softmax.final_state.acc, 9);
    assert_eq!(hard_softmax.final_state.acc, 4);
}

#[test]
fn invalid_hard_softmax_temperature_is_rejected() {
    let error = ProgramCompiler
        .compile_source(
            "LOADI 1\nHALT\n",
            TransformerVmConfig {
                attention_mode: Attention2DMode::HardSoftmax { temperature: 0.0 },
                ..TransformerVmConfig::default()
            },
        )
        .expect_err("temperature=0 should be rejected");

    match error {
        VmError::InvalidConfig(message) => {
            assert!(
                message.contains("temperature"),
                "unexpected message: {message}"
            );
        }
        other => panic!("expected invalid config, got {other:?}"),
    }
}
