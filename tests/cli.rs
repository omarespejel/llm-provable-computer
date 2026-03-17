use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn cli_runs_addition_program() {
    let mut command = Command::cargo_bin("tvm").expect("binary");
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .assert()
        .success()
        .stdout(predicate::str::contains("halted: true"))
        .stdout(predicate::str::contains("sp: 4"))
        .stdout(predicate::str::contains("acc: 8"));
}

#[test]
fn cli_supports_multi_layer_trace_output() {
    let mut command = Command::cargo_bin("tvm").expect("binary");
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .arg("--layers")
        .arg("2")
        .arg("--trace")
        .assert()
        .success()
        .stdout(predicate::str::contains("layers: 2"))
        .stdout(predicate::str::contains("trace[001]"))
        .stdout(predicate::str::contains("sp=4"))
        .stdout(predicate::str::contains("instr=\"LOADI 5\""));
}

#[test]
fn cli_runs_subroutine_program() {
    let mut command = Command::cargo_bin("tvm").expect("binary");
    command
        .arg("run")
        .arg("programs/subroutine_addition.tvm")
        .assert()
        .success()
        .stdout(predicate::str::contains("halted: true"))
        .stdout(predicate::str::contains("sp: 8"))
        .stdout(predicate::str::contains("acc: 42"))
        .stdout(predicate::str::contains("memory: [0, 0, 0, 0, 0, 0, 0, 2]"));
}
