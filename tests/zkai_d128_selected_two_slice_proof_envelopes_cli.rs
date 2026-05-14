#![cfg(feature = "stwo-backend")]

use std::path::{Path, PathBuf};

use assert_cmd::Command;
use predicates::prelude::*;

fn fixture_path(relative: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(relative)
}

fn verifier_cli() -> Command {
    Command::cargo_bin("zkai_d128_selected_two_slice_proof_envelopes").expect("resolve CLI binary")
}

#[test]
fn verify_accepts_checked_evidence_envelopes() {
    let rmsnorm = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json",
    );
    let bridge = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    );

    verifier_cli()
        .arg("verify")
        .arg(rmsnorm)
        .arg(bridge)
        .assert()
        .success()
        .stdout(predicate::str::contains("\"verified\":true"));
}

#[test]
fn verify_rejects_malformed_rmsnorm_json() {
    let dir = tempfile::tempdir().expect("temp dir");
    let malformed = dir.path().join("malformed-rmsnorm.json");
    std::fs::write(&malformed, b"{not json").expect("write malformed envelope");
    let bridge = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    );

    verifier_cli()
        .arg("verify")
        .arg(malformed)
        .arg(bridge)
        .assert()
        .failure()
        .stderr(predicate::str::contains("failed to parse rmsnorm envelope"));
}

#[test]
fn verify_rejects_tampered_rmsnorm_proof_bytes() {
    let dir = tempfile::tempdir().expect("temp dir");
    let original = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json",
    );
    let bridge = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    );
    let tampered = dir.path().join("tampered-rmsnorm.json");
    let mut envelope: serde_json::Value =
        serde_json::from_slice(&std::fs::read(original).expect("read original envelope"))
            .expect("parse original envelope");
    let proof = envelope["proof"].as_array_mut().expect("proof array");
    let first = proof[0].as_u64().expect("proof byte");
    proof[0] = serde_json::Value::from((first + 1) % 256);
    std::fs::write(
        &tampered,
        serde_json::to_vec_pretty(&envelope).expect("serialize tampered envelope"),
    )
    .expect("write tampered envelope");

    verifier_cli()
        .arg("verify")
        .arg(tampered)
        .arg(bridge)
        .assert()
        .failure();
}
