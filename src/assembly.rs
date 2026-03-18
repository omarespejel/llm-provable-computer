use std::collections::HashMap;

use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};

#[derive(Debug)]
struct PendingInstruction {
    line: usize,
    mnemonic: String,
    operands: Vec<String>,
}

pub fn parse_program(source: &str) -> Result<Program> {
    let mut labels = HashMap::new();
    let mut pending = Vec::new();
    let mut memory_size = 16usize;
    let mut initial_memory = None::<Vec<i16>>;

    for (idx, raw_line) in source.lines().enumerate() {
        let line_no = idx + 1;
        let mut line = strip_comment(raw_line).trim().to_string();
        if line.is_empty() {
            continue;
        }

        if let Some((label, rest)) = split_label(&line, line_no)? {
            if labels.insert(label.clone(), pending.len() as u8).is_some() {
                return Err(VmError::Parse {
                    line: line_no,
                    message: format!("duplicate label `{label}`"),
                });
            }
            line = rest.trim().to_string();
            if line.is_empty() {
                continue;
            }
        }

        let tokens = line
            .split_whitespace()
            .map(|token| token.trim_end_matches(',').to_string())
            .collect::<Vec<_>>();
        if tokens.is_empty() {
            continue;
        }

        let mnemonic = tokens[0].to_uppercase();
        let operands = tokens[1..].to_vec();

        match mnemonic.as_str() {
            ".MEMORY" => {
                if operands.len() != 1 {
                    return Err(VmError::Parse {
                        line: line_no,
                        message: ".memory expects exactly one operand".to_string(),
                    });
                }
                memory_size = parse_usize(&operands[0], line_no, "memory size")?;
                initial_memory = Some(vec![0; memory_size]);
            }
            ".INIT" => {
                if operands.len() != 2 {
                    return Err(VmError::Parse {
                        line: line_no,
                        message: ".init expects <address> <value>".to_string(),
                    });
                }
                let address = parse_usize(&operands[0], line_no, "memory address")?;
                let value = parse_i16(&operands[1], line_no, "initial value")?;
                let memory = initial_memory.get_or_insert_with(|| vec![0; memory_size]);
                if address >= memory.len() {
                    return Err(VmError::Parse {
                        line: line_no,
                        message: format!(
                            "memory address {} is out of bounds for configured size {}",
                            address,
                            memory.len()
                        ),
                    });
                }
                memory[address] = value;
            }
            _ => pending.push(PendingInstruction {
                line: line_no,
                mnemonic,
                operands,
            }),
        }
    }

    let instructions = pending
        .into_iter()
        .map(|pending| parse_instruction(pending, &labels))
        .collect::<Result<Vec<_>>>()?;

    let program = Program::new(instructions, memory_size)
        .with_initial_memory(initial_memory.unwrap_or_else(|| vec![0; memory_size]))?;
    Ok(program)
}

fn strip_comment(line: &str) -> &str {
    let semicolon = line.find(';');
    let hash = line.find('#');
    match (semicolon, hash) {
        (Some(left), Some(right)) => &line[..left.min(right)],
        (Some(idx), None) | (None, Some(idx)) => &line[..idx],
        (None, None) => line,
    }
}

fn split_label(line: &str, line_no: usize) -> Result<Option<(String, &str)>> {
    if let Some((left, right)) = line.split_once(':') {
        let label = left.trim();
        if label.is_empty() {
            return Err(VmError::Parse {
                line: line_no,
                message: "empty label".to_string(),
            });
        }
        if !label
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || ch == '_' || ch == '-')
        {
            return Err(VmError::Parse {
                line: line_no,
                message: format!("invalid label `{label}`"),
            });
        }
        return Ok(Some((label.to_string(), right)));
    }
    Ok(None)
}

fn parse_instruction(
    pending: PendingInstruction,
    labels: &HashMap<String, u8>,
) -> Result<Instruction> {
    let operands = pending.operands.as_slice();
    let line = pending.line;
    let instruction = match pending.mnemonic.as_str() {
        "NOP" => expect_arity(line, operands, 0).map(|_| Instruction::Nop)?,
        "LOADI" => Instruction::LoadImmediate(parse_i16_operand(line, operands)?),
        "LOAD" => Instruction::Load(parse_u8_operand(line, operands)?),
        "STORE" => Instruction::Store(parse_u8_operand(line, operands)?),
        "PUSH" => expect_arity(line, operands, 0).map(|_| Instruction::Push)?,
        "POP" => expect_arity(line, operands, 0).map(|_| Instruction::Pop)?,
        "ADD" => Instruction::AddImmediate(parse_i16_operand(line, operands)?),
        "ADDM" => Instruction::AddMemory(parse_u8_operand(line, operands)?),
        "SUB" => Instruction::SubImmediate(parse_i16_operand(line, operands)?),
        "SUBM" => Instruction::SubMemory(parse_u8_operand(line, operands)?),
        "MUL" => Instruction::MulImmediate(parse_i16_operand(line, operands)?),
        "MULM" => Instruction::MulMemory(parse_u8_operand(line, operands)?),
        "AND" => Instruction::AndImmediate(parse_i16_operand(line, operands)?),
        "ANDM" => Instruction::AndMemory(parse_u8_operand(line, operands)?),
        "OR" => Instruction::OrImmediate(parse_i16_operand(line, operands)?),
        "ORM" => Instruction::OrMemory(parse_u8_operand(line, operands)?),
        "XOR" => Instruction::XorImmediate(parse_i16_operand(line, operands)?),
        "XORM" => Instruction::XorMemory(parse_u8_operand(line, operands)?),
        "CMP" => Instruction::CmpImmediate(parse_i16_operand(line, operands)?),
        "CMPM" => Instruction::CmpMemory(parse_u8_operand(line, operands)?),
        "CALL" => Instruction::Call(parse_target(line, operands, labels)?),
        "RET" => expect_arity(line, operands, 0).map(|_| Instruction::Ret)?,
        "JMP" => Instruction::Jump(parse_target(line, operands, labels)?),
        "JZ" => Instruction::JumpIfZero(parse_target(line, operands, labels)?),
        "JNZ" => Instruction::JumpIfNotZero(parse_target(line, operands, labels)?),
        "HALT" => expect_arity(line, operands, 0).map(|_| Instruction::Halt)?,
        _ => {
            return Err(VmError::Parse {
                line,
                message: format!("unknown instruction `{}`", pending.mnemonic),
            })
        }
    };
    Ok(instruction)
}

fn expect_arity(line: usize, operands: &[String], expected: usize) -> Result<()> {
    if operands.len() != expected {
        return Err(VmError::Parse {
            line,
            message: format!("expected {expected} operand(s), found {}", operands.len()),
        });
    }
    Ok(())
}

fn parse_i16_operand(line: usize, operands: &[String]) -> Result<i16> {
    expect_arity(line, operands, 1)?;
    parse_i16(&operands[0], line, "immediate")
}

fn parse_u8_operand(line: usize, operands: &[String]) -> Result<u8> {
    expect_arity(line, operands, 1)?;
    parse_u8(&operands[0], line, "address")
}

fn parse_target(line: usize, operands: &[String], labels: &HashMap<String, u8>) -> Result<u8> {
    expect_arity(line, operands, 1)?;
    if let Ok(value) = operands[0].parse::<u8>() {
        return Ok(value);
    }
    labels
        .get(&operands[0])
        .copied()
        .ok_or_else(|| VmError::UnknownLabel {
            line,
            label: operands[0].clone(),
        })
}

fn parse_u8(token: &str, line: usize, subject: &str) -> Result<u8> {
    token.parse::<u8>().map_err(|_| VmError::Parse {
        line,
        message: format!("invalid {subject} `{token}`"),
    })
}

fn parse_i16(token: &str, line: usize, subject: &str) -> Result<i16> {
    token.parse::<i16>().map_err(|_| VmError::Parse {
        line,
        message: format!("invalid {subject} `{token}`"),
    })
}

fn parse_usize(token: &str, line: usize, subject: &str) -> Result<usize> {
    token.parse::<usize>().map_err(|_| VmError::Parse {
        line,
        message: format!("invalid {subject} `{token}`"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::instruction::Instruction;

    #[test]
    fn strip_comment_removes_semicolon() {
        assert_eq!(strip_comment("LOADI 5 ; comment"), "LOADI 5 ");
    }

    #[test]
    fn strip_comment_removes_hash() {
        assert_eq!(strip_comment("HALT # done"), "HALT ");
    }

    #[test]
    fn strip_comment_handles_both() {
        assert_eq!(strip_comment("NOP ; comment # nested"), "NOP ");
        assert_eq!(strip_comment("NOP # comment ; nested"), "NOP ");
    }

    #[test]
    fn strip_comment_no_comment() {
        assert_eq!(strip_comment("LOADI 42"), "LOADI 42");
    }

    #[test]
    fn split_label_extracts_label() {
        let (label, rest) = split_label("loop: NOP", 1).unwrap().unwrap();
        assert_eq!(label, "loop");
        assert_eq!(rest, " NOP");
    }

    #[test]
    fn split_label_returns_none_for_no_label() {
        assert!(split_label("NOP", 1).unwrap().is_none());
    }

    #[test]
    fn split_label_rejects_empty_label() {
        let err = split_label(": NOP", 1).unwrap_err();
        assert!(err.to_string().contains("empty label"));
    }

    #[test]
    fn split_label_rejects_invalid_characters() {
        let err = split_label("foo bar: NOP", 1).unwrap_err();
        assert!(err.to_string().contains("invalid label"));
    }

    #[test]
    fn parse_empty_program() {
        let program = parse_program("").unwrap();
        assert!(program.is_empty());
    }

    #[test]
    fn parse_comment_only_lines() {
        let program = parse_program("; comment\n# another comment\n").unwrap();
        assert!(program.is_empty());
    }

    #[test]
    fn parse_all_instruction_mnemonics() {
        let source = r#"
            NOP
            LOADI 1
            LOAD 0
            STORE 0
            PUSH
            POP
            ADD 1
            ADDM 0
            SUB 1
            SUBM 0
            MUL 2
            MULM 0
            AND 1
            ANDM 0
            OR 1
            ORM 0
            XOR 1
            XORM 0
            CMP 1
            CMPM 0
            CALL 0
            RET
            JMP 0
            JZ 0
            JNZ 0
            HALT
        "#;
        let program = parse_program(source).unwrap();
        assert_eq!(program.len(), 26);
    }

    #[test]
    fn parse_memory_directive() {
        let program = parse_program(".memory 32\nHALT\n").unwrap();
        assert_eq!(program.memory_size(), 32);
    }

    #[test]
    fn parse_init_directive() {
        let program = parse_program(".memory 4\n.init 2 42\nHALT\n").unwrap();
        assert_eq!(program.initial_memory()[2], 42);
    }

    #[test]
    fn parse_init_out_of_bounds_rejected() {
        let err = parse_program(".memory 4\n.init 10 42\nHALT\n").unwrap_err();
        assert!(err.to_string().contains("out of bounds"));
    }

    #[test]
    fn parse_label_resolution() {
        let program = parse_program("JMP end\nNOP\nend: HALT\n").unwrap();
        assert_eq!(
            program.instruction_at(0).unwrap(),
            Instruction::Jump(2)
        );
    }

    #[test]
    fn parse_duplicate_label_rejected() {
        let err = parse_program("foo: NOP\nfoo: HALT\n").unwrap_err();
        assert!(err.to_string().contains("duplicate label"));
    }

    #[test]
    fn parse_unknown_label_rejected() {
        let err = parse_program("JMP nowhere\nHALT\n").unwrap_err();
        assert!(err.to_string().contains("unknown label"));
    }

    #[test]
    fn parse_unknown_instruction_rejected() {
        let err = parse_program("DANCE 5\n").unwrap_err();
        assert!(err.to_string().contains("unknown instruction"));
    }

    #[test]
    fn parse_wrong_arity_rejected() {
        let err = parse_program("HALT 1\n").unwrap_err();
        assert!(err.to_string().contains("expected 0 operand"));
    }

    #[test]
    fn parse_invalid_immediate_rejected() {
        let err = parse_program("LOADI abc\n").unwrap_err();
        assert!(err.to_string().contains("invalid"));
    }

    #[test]
    fn parse_memory_wrong_arity_rejected() {
        let err = parse_program(".memory\nHALT\n").unwrap_err();
        assert!(err.to_string().contains("expects exactly one"));
    }

    #[test]
    fn parse_init_wrong_arity_rejected() {
        let err = parse_program(".memory 4\n.init 0\nHALT\n").unwrap_err();
        assert!(err.to_string().contains("expects"));
    }

    #[test]
    fn parse_negative_immediate() {
        let program = parse_program("LOADI -100\nHALT\n").unwrap();
        assert_eq!(
            program.instruction_at(0).unwrap(),
            Instruction::LoadImmediate(-100)
        );
    }

    #[test]
    fn parse_comma_separated_operands_stripped() {
        // Comma at end of operand should be stripped
        let program = parse_program("LOADI 5,\nHALT\n").unwrap();
        assert_eq!(
            program.instruction_at(0).unwrap(),
            Instruction::LoadImmediate(5)
        );
    }

    #[test]
    fn parse_label_with_hyphens_and_underscores() {
        let program = parse_program("my-label_1: HALT\n").unwrap();
        assert_eq!(program.len(), 1);
    }

    #[test]
    fn parse_label_only_line_followed_by_instruction() {
        let program = parse_program("start:\nHALT\n").unwrap();
        assert_eq!(program.len(), 1);
    }
}
