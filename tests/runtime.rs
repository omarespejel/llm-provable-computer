use transformer_vm_rs::{
    decode_state, encode_state, parse_program, ExecutionRuntime, MachineState, ProgramCompiler,
    TransformerVmConfig,
};

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
    let source = std::fs::read_to_string("programs/counter.tvm").expect("fixture");
    let program = parse_program(&source).expect("parse");
    let model = ProgramCompiler
        .compile_program(program, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 128);
    let result = runtime.run().expect("run");

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
    let source = std::fs::read_to_string("programs/fibonacci.tvm").expect("fixture");
    let program = parse_program(&source).expect("parse");
    let model = ProgramCompiler
        .compile_program(program, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 512);
    let result = runtime.run().expect("run");

    assert!(result.halted);
    assert_eq!(result.final_state.acc, 21, "Fibonacci(8) = 21");
}

#[test]
fn multiply_program_computes_6_times_7() {
    let source = std::fs::read_to_string("programs/multiply.tvm").expect("fixture");
    let program = parse_program(&source).expect("parse");
    let model = ProgramCompiler
        .compile_program(program, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 256);
    let result = runtime.run().expect("run");

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
