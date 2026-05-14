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

fn write_tampered_proof(source: PathBuf, target: &Path) {
    let mut envelope: serde_json::Value =
        serde_json::from_slice(&std::fs::read(source).expect("read source envelope"))
            .expect("parse source envelope");
    let proof_bytes: Vec<u8> = envelope["proof"]
        .as_array()
        .expect("proof array")
        .iter()
        .map(|byte| byte.as_u64().expect("proof byte") as u8)
        .collect();
    let mut proof_payload: serde_json::Value =
        serde_json::from_slice(&proof_bytes).expect("parse inner proof payload");
    let proof_of_work = proof_payload["stark_proof"]["proof_of_work"]
        .as_u64()
        .expect("proof_of_work");
    proof_payload["stark_proof"]["proof_of_work"] = serde_json::Value::from(proof_of_work + 1);
    let tampered_proof = serde_json::to_vec(&proof_payload).expect("serialize inner proof payload");
    envelope["proof"] = serde_json::Value::Array(
        tampered_proof
            .into_iter()
            .map(serde_json::Value::from)
            .collect(),
    );
    std::fs::write(
        target,
        serde_json::to_vec_pretty(&envelope).expect("serialize tampered envelope"),
    )
    .expect("write tampered envelope");
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
fn verify_rejects_oversized_rmsnorm_json_before_parsing() {
    let dir = tempfile::tempdir().expect("temp dir");
    let oversized = dir.path().join("oversized-rmsnorm.json");
    std::fs::write(&oversized, vec![b' '; 4 * 1024 * 1024 + 1]).expect("write oversized envelope");
    let bridge = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    );

    verifier_cli()
        .arg("verify")
        .arg(oversized)
        .arg(bridge)
        .assert()
        .failure()
        .stderr(predicate::str::contains("exceeds max size"));
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
    write_tampered_proof(original, &tampered);

    verifier_cli()
        .arg("verify")
        .arg(tampered)
        .arg(bridge)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "rmsnorm envelope proof verification returned false",
        ));
}

#[test]
fn verify_rejects_tampered_bridge_proof_bytes() {
    let dir = tempfile::tempdir().expect("temp dir");
    let rmsnorm = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json",
    );
    let original_bridge = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    );
    let tampered_bridge = dir.path().join("tampered-bridge.json");
    write_tampered_proof(original_bridge, &tampered_bridge);

    verifier_cli()
        .arg("verify")
        .arg(rmsnorm)
        .arg(tampered_bridge)
        .assert()
        .failure()
        .stderr(
            predicate::str::contains("bridge envelope proof verification errored")
                .and(predicate::str::contains("STARK verification failed")),
        );
}

#[test]
fn verify_rejects_tampered_rmsnorm_and_bridge_proof_bytes() {
    let dir = tempfile::tempdir().expect("temp dir");
    let original_rmsnorm = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json",
    );
    let original_bridge = fixture_path(
        "docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    );
    let tampered_rmsnorm = dir.path().join("tampered-rmsnorm.json");
    let tampered_bridge = dir.path().join("tampered-bridge.json");
    write_tampered_proof(original_rmsnorm, &tampered_rmsnorm);
    write_tampered_proof(original_bridge, &tampered_bridge);

    verifier_cli()
        .arg("verify")
        .arg(tampered_rmsnorm)
        .arg(tampered_bridge)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "rmsnorm envelope proof verification returned false",
        ));
}
