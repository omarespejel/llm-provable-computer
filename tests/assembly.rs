use llm_provable_computer::{parse_program, Instruction, VmError};

#[test]
fn parser_resolves_stack_and_subroutine_instructions() {
    let program = parse_program(
        r#"
        .memory 8
        PUSH
        CALL worker
        POP
        HALT
    worker:
        RET
    "#,
    )
    .expect("parse");

    assert_eq!(
        program.instructions(),
        &[
            Instruction::Push,
            Instruction::Call(4),
            Instruction::Pop,
            Instruction::Halt,
            Instruction::Ret,
        ]
    );
    assert_eq!(program.memory_size(), 8);
}

#[test]
fn parser_rejects_ret_operands() {
    let error = parse_program("RET 1").expect_err("RET should not accept operands");

    match error {
        VmError::Parse { line, message } => {
            assert_eq!(line, 1);
            assert!(message.contains("expected 0 operand(s)"));
        }
        other => panic!("expected parse error, got {other:?}"),
    }
}

#[test]
fn parser_rejects_memory_that_exceeds_stack_encoding_limit() {
    let error = parse_program(
        r#"
        .memory 256
        HALT
    "#,
    )
    .expect_err("256 cells exceed the encoded stack pointer range");

    match error {
        VmError::InvalidConfig(message) => {
            assert!(message.contains("encoded stack/address limit"));
        }
        other => panic!("expected invalid config error, got {other:?}"),
    }
}
