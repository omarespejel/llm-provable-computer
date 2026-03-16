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
