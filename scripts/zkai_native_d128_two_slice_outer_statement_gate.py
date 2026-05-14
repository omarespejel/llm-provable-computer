#!/usr/bin/env python3
"""Gate the native d128 two-slice outer statement proof artifact.

This is a narrow GO: the artifact is a real native Stwo proof that binds two
host-verified inner slice-result rows.  It is explicitly not recursive verifier
execution of the inner Stwo proofs, and it is not a NANOZK proof-size win.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import pathlib
import tempfile
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

INPUT_JSON = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json"
INPUT_TSV = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv"
ENVELOPE_JSON = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json"
JSON_OUT = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-statement-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-statement-gate-2026-05.tsv"

SCHEMA = "zkai-native-d128-two-slice-outer-statement-gate-v1"
DECISION = "NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_AIR_PROOF"
RESULT = "NARROW_GO_NATIVE_STWO_OUTER_STATEMENT_BINDING_NOT_VERIFIER_EXECUTION"
ISSUE = 583
CLAIM_BOUNDARY = "HOST_VERIFIED_OUTER_STATEMENT_BINDING_NOT_NATIVE_VERIFIER_EXECUTION"

EXPECTED_INPUT_BYTES = 5_485
EXPECTED_INPUT_SHA256 = "3e8526da8ae9e9491ddd225873c5e03a6128c957a18d5a43e3793e5c08133b07"
EXPECTED_INPUT_TSV_BYTES = 875
EXPECTED_INPUT_TSV_SHA256 = "9e409cfd67a83b999e87dc5888a6ea7d82d5bd27feea637f5b4966420da3e41c"
EXPECTED_ENVELOPE_BYTES = 34_471
EXPECTED_ENVELOPE_SHA256 = "07254ada114c68ba129f90ccfa0d9a7aacbba2bc1ae64388e5a1bd12fe944aca"
EXPECTED_PROOF_BYTES = 3_516
EXPECTED_PROOF_SHA256 = "9977aeefe8021845a46a382be143824f10605b3ec676eaf0ed25e46f2d90e5f1"

EXPECTED_INPUT_SCHEMA = "zkai-native-d128-two-slice-outer-statement-air-proof-input-v1"
EXPECTED_INPUT_DECISION = "NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_INPUT"
EXPECTED_PROOF_BACKEND = "stwo"
EXPECTED_PROOF_BACKEND_VERSION = "stwo-d128-two-slice-outer-statement-air-proof-v2-compressed-digest"
EXPECTED_STATEMENT_VERSION = "zkai-d128-two-slice-outer-statement-v1"
EXPECTED_SEMANTIC_SCOPE = "host_verified_two_slice_inner_stwo_results_bound_by_native_outer_statement_air"
EXPECTED_ENVELOPE_DECISION = "NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_AIR_PROOF"
EXPECTED_OPERATION = "d128_two_slice_outer_statement_binding"
EXPECTED_TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
EXPECTED_REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
EXPECTED_VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
EXPECTED_WIDTH = 128
EXPECTED_SELECTED_SLICE_COUNT = 2
EXPECTED_SELECTED_ROWS = 256
EXPECTED_TWO_SLICE_TARGET = "blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6"
EXPECTED_ACCUMULATOR = "blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d"
EXPECTED_VERIFIER_HANDLE = "blake2b-256:8dd18b7b5b8d0a5399535f0a02f9a1fe4128211bad8f3e69bb44c92cdf07a131"
EXPECTED_STATEMENT_COMMITMENT = "blake2b-256:ab06c13b3bd24aad37285c4b6c759b9c30faf747af3248c2e45a2c245e7f8dc8"
EXPECTED_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:dbb25a1e94bb38c2aeedfcf38b2cebd401427c633860577893e46389f3565beb"
EXPECTED_PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:9528113a0e62dc8565c2c5974d47c9859494a16fed307ef91881a2a2705fbf80"
EXPECTED_NANOZK_REPORTED_BYTES = 6_900
EXPECTED_COMPRESSED_STATEMENT_CHAIN_BYTES = 2_559
EXPECTED_SNARK_RECEIPT_PROOF_BYTES = 807
EXPECTED_PACKAGE_WITHOUT_VK_BYTES = 4_752
EXPECTED_PACKAGE_WITH_VK_BYTES = 10_608
EXPECTED_ENVELOPE_KEYS = {
    "decision",
    "input",
    "proof",
    "proof_backend",
    "proof_backend_version",
    "semantic_scope",
    "statement_version",
}
EXPECTED_INPUT_KEYS = {
    "accumulator_commitment",
    "accumulator_verifier_handle_commitment",
    "decision",
    "next_backend_step",
    "non_claims",
    "operation",
    "proof_native_parameter_commitment",
    "proof_verifier_hardening",
    "public_instance_commitment",
    "required_backend_version",
    "rows",
    "schema",
    "selected_checked_rows",
    "selected_slice_count",
    "selected_slice_ids",
    "statement_commitment",
    "target_id",
    "two_slice_target_commitment",
    "validation_commands",
    "verifier_domain",
    "width",
}
EXPECTED_ROW_KEYS = {
    "index",
    "proof_backend_version",
    "proof_native_parameter_commitment",
    "public_instance_commitment",
    "required_backend_version",
    "row_count",
    "slice_id",
    "slice_tag",
    "source_file_sha256",
    "source_payload_sha256",
    "statement_commitment",
    "verified",
    "verifier_domain",
}

EXPECTED_ROWS = [
    {
        "index": 0,
        "slice_id": "rmsnorm_public_rows",
        "slice_tag": 1,
        "row_count": 128,
        "verified": True,
        "proof_backend_version": "stwo-d128-rmsnorm-public-row-air-proof-v3",
        "statement_commitment": "blake2b-256:de944915f2664ac7a893f4ba9a029323f7408eac58bf39170a0935d7832ccbd8",
        "public_instance_commitment": "blake2b-256:2dfa2ceffd67f95059b3d6cd639a82577f2bbd7be43e99c25814feb703a8fd72",
        "proof_native_parameter_commitment": "blake2b-256:8d8bded756f3290980eaab322ba986b02c5584bc8348c2ffcfa4e4860a80944c",
        "source_file_sha256": "d80f9f16e5f8aef3a8ec49271bb0616483cb6906731539aea2f73ba4678123ec",
        "source_payload_sha256": "19688310ba6001e16b80c15532f74b59097222a1aa9be132ea66b11a116ded05",
    },
    {
        "index": 1,
        "slice_id": "rmsnorm_projection_bridge",
        "slice_tag": 2,
        "row_count": 128,
        "verified": True,
        "proof_backend_version": "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1",
        "statement_commitment": "blake2b-256:fe0a9e59560611ed5220fd25b082806977a66a7032f457fce2cd5c3a41856728",
        "public_instance_commitment": "blake2b-256:ca94d85cb0ed5e9001cd3def00817060745fa015bd8dda5f08732944f7418383",
        "proof_native_parameter_commitment": "blake2b-256:ff31d2b502dac1e7d9f9cca69c4bd31e93e068dab49884e61a300a99389d58c1",
        "source_file_sha256": "11f93a3ecee19c40ff14d154e054dab56a1b9c1a2dbb1d609a918e201e6fd849",
        "source_payload_sha256": "e6e46f2e35df3177790c7dbdc5c519f4a7d62e8ed6cba0501ffac94db73975f3",
    },
]

EXPECTED_NON_CLAIMS = [
    "not native verifier execution of the selected inner Stwo proofs",
    "not recursion or proof-carrying data",
    "not a native d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not full transformer inference",
    "not production-ready zkML",
]

EXPECTED_PROOF_VERIFIER_HARDENING = [
    "selected slice order checked before proof verification",
    "selected row count checked before proof verification",
    "statement commitment binds selected slice IDs, source hashes, commitments, and verifier domain",
    "public-instance commitment bound as compressed digest limbs",
    "proof-native parameter commitment bound as compressed digest limbs",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_native_d128_two_slice_outer_statement_input.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv",
    "cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- prove docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- verify docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 test d128_native_two_slice_outer_statement_proof --lib --features stwo-backend",
    "python3 scripts/zkai_native_d128_two_slice_outer_statement_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.tsv",
    "git diff --check",
    "just gate-fast",
]

NON_CLAIMS = EXPECTED_NON_CLAIMS + [
    "not a native d128 two-slice recursive outer proof",
    "not proof that Stwo verifies the selected inner Stwo proofs inside Stwo",
    "not a matched NANOZK proof-size win even though this payload is smaller than NANOZK's paper-reported row",
    "not stable binary proof-size accounting",
]

FOLLOWUP_ISSUES = [
    {
        "title": "Native Stwo verifier-execution constraints for selected d128 slice proofs",
        "why": "turn this host-verified binding proof into the real issue #583 target",
    },
    {
        "title": "Stable binary encoding for compressed native Stwo proof payloads",
        "why": "the 3,516-byte result is still JSON-serialized native Stwo proof material, not stable binary proof-size accounting",
    },
]

Mutation = tuple[str, Callable[[dict[str, Any]], None]]


class OuterStatementGateError(RuntimeError):
    pass


def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def synthetic_artifact_bytes(label: str, size: int) -> list[int]:
    seed = f"not-native-stwo-proof:{label}:".encode()
    repeated = seed * ((size // len(seed)) + 1)
    return list(repeated[:size])


def proof_bytes(envelope: dict[str, Any]) -> bytes:
    raw = envelope.get("proof")
    if not isinstance(raw, list):
        raise OuterStatementGateError("proof is not a byte array")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 255 for value in raw):
        raise OuterStatementGateError("proof byte array contains non-byte values")
    return bytes(raw)


def expect_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise OuterStatementGateError(f"{label} is not an object")
    actual = set(value)
    if actual != expected:
        raise OuterStatementGateError(
            f"{label} keys mismatch: extra={sorted(actual - expected)}, missing={sorted(expected - actual)}"
        )


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_artifact(envelope: dict[str, Any], input_obj: dict[str, Any]) -> None:
    expect_keys(envelope, EXPECTED_ENVELOPE_KEYS, "envelope")
    expect_keys(input_obj, EXPECTED_INPUT_KEYS, "input")
    if envelope.get("proof_backend") != EXPECTED_PROOF_BACKEND:
        raise OuterStatementGateError("proof backend mismatch")
    if envelope.get("proof_backend_version") != EXPECTED_PROOF_BACKEND_VERSION:
        raise OuterStatementGateError("proof backend version mismatch")
    if envelope.get("statement_version") != EXPECTED_STATEMENT_VERSION:
        raise OuterStatementGateError("statement version mismatch")
    if envelope.get("semantic_scope") != EXPECTED_SEMANTIC_SCOPE:
        raise OuterStatementGateError("semantic scope mismatch")
    if envelope.get("decision") != EXPECTED_ENVELOPE_DECISION:
        raise OuterStatementGateError("envelope decision mismatch")
    if envelope.get("input") != input_obj:
        raise OuterStatementGateError("envelope input does not match checked input artifact")

    proof = proof_bytes(envelope)
    if len(proof) != EXPECTED_PROOF_BYTES:
        raise OuterStatementGateError("proof byte length mismatch")
    if sha256_hex(proof) != EXPECTED_PROOF_SHA256:
        raise OuterStatementGateError("proof sha256 mismatch")

    if input_obj.get("schema") != EXPECTED_INPUT_SCHEMA:
        raise OuterStatementGateError("input schema mismatch")
    if input_obj.get("decision") != EXPECTED_INPUT_DECISION:
        raise OuterStatementGateError("input decision mismatch")
    if input_obj.get("operation") != EXPECTED_OPERATION:
        raise OuterStatementGateError("operation mismatch")
    if input_obj.get("target_id") != EXPECTED_TARGET_ID:
        raise OuterStatementGateError("target id mismatch")
    if input_obj.get("required_backend_version") != EXPECTED_REQUIRED_BACKEND_VERSION:
        raise OuterStatementGateError("required backend version mismatch")
    if input_obj.get("verifier_domain") != EXPECTED_VERIFIER_DOMAIN:
        raise OuterStatementGateError("verifier domain mismatch")
    if input_obj.get("width") != EXPECTED_WIDTH:
        raise OuterStatementGateError("width mismatch")
    if input_obj.get("selected_slice_count") != EXPECTED_SELECTED_SLICE_COUNT:
        raise OuterStatementGateError("selected slice count mismatch")
    if input_obj.get("selected_checked_rows") != EXPECTED_SELECTED_ROWS:
        raise OuterStatementGateError("selected checked rows mismatch")
    if input_obj.get("selected_slice_ids") != [row["slice_id"] for row in EXPECTED_ROWS]:
        raise OuterStatementGateError("selected slice ids mismatch")
    if input_obj.get("two_slice_target_commitment") != EXPECTED_TWO_SLICE_TARGET:
        raise OuterStatementGateError("two-slice target commitment mismatch")
    if input_obj.get("accumulator_commitment") != EXPECTED_ACCUMULATOR:
        raise OuterStatementGateError("accumulator commitment mismatch")
    if input_obj.get("accumulator_verifier_handle_commitment") != EXPECTED_VERIFIER_HANDLE:
        raise OuterStatementGateError("verifier handle commitment mismatch")
    if input_obj.get("statement_commitment") != EXPECTED_STATEMENT_COMMITMENT:
        raise OuterStatementGateError("statement commitment mismatch")
    if input_obj.get("public_instance_commitment") != EXPECTED_PUBLIC_INSTANCE_COMMITMENT:
        raise OuterStatementGateError("public instance commitment mismatch")
    if input_obj.get("proof_native_parameter_commitment") != EXPECTED_PROOF_NATIVE_PARAMETER_COMMITMENT:
        raise OuterStatementGateError("proof-native parameter commitment mismatch")
    if input_obj.get("non_claims") != EXPECTED_NON_CLAIMS:
        raise OuterStatementGateError("non-claims mismatch")
    if input_obj.get("proof_verifier_hardening") != EXPECTED_PROOF_VERIFIER_HARDENING:
        raise OuterStatementGateError("proof verifier hardening mismatch")
    if input_obj.get("validation_commands") != VALIDATION_COMMANDS:
        raise OuterStatementGateError("validation commands mismatch")
    rows = input_obj.get("rows")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_ROWS):
        raise OuterStatementGateError("row vector mismatch")
    for actual, expected in zip(rows, EXPECTED_ROWS):
        expect_keys(actual, EXPECTED_ROW_KEYS, f"row {expected['index']}")
        for key, expected_value in expected.items():
            if actual.get(key) != expected_value:
                raise OuterStatementGateError(f"row {expected['index']} {key} mismatch")
        if actual.get("verifier_domain") != EXPECTED_VERIFIER_DOMAIN:
            raise OuterStatementGateError(f"row {expected['index']} verifier domain mismatch")
        if actual.get("required_backend_version") != EXPECTED_REQUIRED_BACKEND_VERSION:
            raise OuterStatementGateError(f"row {expected['index']} required backend version mismatch")


def file_record(path: pathlib.Path, expected_bytes: int, expected_sha: str) -> dict[str, Any]:
    raw = path.read_bytes()
    actual_sha = sha256_hex(raw)
    if len(raw) != expected_bytes:
        raise OuterStatementGateError(f"{path} byte length mismatch")
    if actual_sha != expected_sha:
        raise OuterStatementGateError(f"{path} sha256 mismatch")
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": len(raw),
        "sha256": actual_sha,
    }


def build_result(envelope: dict[str, Any], input_obj: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    proof = proof_bytes(envelope)
    return {
        "schema": SCHEMA,
        "issue": ISSUE,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": {
            "input_json": file_record(INPUT_JSON, EXPECTED_INPUT_BYTES, EXPECTED_INPUT_SHA256),
            "input_tsv": file_record(INPUT_TSV, EXPECTED_INPUT_TSV_BYTES, EXPECTED_INPUT_TSV_SHA256),
            "envelope_json": file_record(ENVELOPE_JSON, EXPECTED_ENVELOPE_BYTES, EXPECTED_ENVELOPE_SHA256),
        },
        "metrics": {
            "selected_checked_rows": EXPECTED_SELECTED_ROWS,
            "selected_slice_ids": [row["slice_id"] for row in EXPECTED_ROWS],
            "native_outer_statement_proof_bytes": len(proof),
            "native_outer_statement_envelope_bytes": EXPECTED_ENVELOPE_BYTES,
            "native_outer_statement_proof_sha256": sha256_hex(proof),
            "prior_uncompressed_outer_statement_proof_bytes": 11_041,
            "prior_uncompressed_outer_statement_envelope_bytes": 94_864,
            "proof_saving_vs_prior_uncompressed_bytes": 11_041 - len(proof),
            "proof_saving_vs_prior_uncompressed_share": ratio(11_041 - len(proof), 11_041),
            "envelope_saving_vs_prior_uncompressed_bytes": 94_864 - EXPECTED_ENVELOPE_BYTES,
            "statement_commitment": input_obj["statement_commitment"],
            "public_instance_commitment": input_obj["public_instance_commitment"],
            "proof_native_parameter_commitment": input_obj["proof_native_parameter_commitment"],
            "nanozk_reported_transformer_block_proof_bytes": EXPECTED_NANOZK_REPORTED_BYTES,
            "proof_vs_nanozk_reported_row_ratio": ratio(len(proof), EXPECTED_NANOZK_REPORTED_BYTES),
            "package_without_vk_bytes_from_prior_gate": EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
            "package_with_vk_bytes_from_prior_gate": EXPECTED_PACKAGE_WITH_VK_BYTES,
        },
        "interpretation": {
            "human": (
                "A real native Stwo proof now binds the two selected d128 slice-result rows "
                "through the recomputed statement, public-instance, and proof-parameter commitments. "
                "The proof uses an empty preprocessed tree and a verifier-recomputed compressed base-trace root. "
                "This is useful progress toward an outer route, but it is not recursive verifier execution."
            ),
            "why_not_nanozk_win": (
                "The 3,516-byte native outer statement proof payload is smaller than the NANOZK "
                "paper-reported 6.9 KB row, but it is JSON-serialized native Stwo proof material "
                "for a host-verified outer statement object. The object class is different, so it "
                "must not be presented as a matched NANOZK proof-size win or as stable binary "
                "proof-size accounting."
            ),
            "next_backend_step": (
                "Replace host-verified result binding with native Stwo verifier-execution constraints "
                "for the selected inner proofs."
            ),
        },
        "non_claims": NON_CLAIMS,
        "followup_issues": FOLLOWUP_ISSUES,
        "mutation_inventory": [name for name, _ in mutations()],
        "case_count": len(cases),
        "cases": cases,
        "all_mutations_rejected": all(case["rejected"] for case in cases),
        "validation_commands": VALIDATION_COMMANDS,
    }


def mutations() -> list[Mutation]:
    return [
        ("proof_backend_relabelled", lambda e: e.update({"proof_backend": "Groth16"})),
        ("proof_backend_version_drift", lambda e: e.update({"proof_backend_version": "stwo-drift"})),
        ("statement_version_drift", lambda e: e.update({"statement_version": "zkai-drift"})),
        ("semantic_scope_drift", lambda e: e.update({"semantic_scope": "native_verifier_execution"})),
        ("envelope_unknown_top_level_key", lambda e: e.update({"unexpected_claim": "native verifier execution"})),
        ("proof_bytes_tampered", lambda e: e["proof"].__setitem__(0, (e["proof"][0] + 1) % 256)),
        (
            "proof_replaced_with_package_without_vk_bytes",
            lambda e: e.update({"proof": synthetic_artifact_bytes("package-without-vk", EXPECTED_PACKAGE_WITHOUT_VK_BYTES)}),
        ),
        (
            "proof_replaced_with_compressed_transcript_bytes",
            lambda e: e.update(
                {"proof": synthetic_artifact_bytes("compressed-statement-chain", EXPECTED_COMPRESSED_STATEMENT_CHAIN_BYTES)}
            ),
        ),
        (
            "proof_replaced_with_groth16_receipt_bytes",
            lambda e: e.update({"proof": synthetic_artifact_bytes("groth16-statement-receipt", EXPECTED_SNARK_RECEIPT_PROOF_BYTES)}),
        ),
        ("envelope_decision_changed_to_native_verifier_execution", lambda e: e.update({"decision": "GO_NATIVE_VERIFIER_EXECUTION"})),
        ("selected_slice_count_drift", lambda e: e["input"].update({"selected_slice_count": 3})),
        ("input_statement_commitment_drift", lambda e: e["input"].update({"statement_commitment": "blake2b-256:" + "aa" * 32})),
        ("target_commitment_drift", lambda e: e["input"].update({"two_slice_target_commitment": "blake2b-256:" + "bb" * 32})),
        ("accumulator_commitment_drift", lambda e: e["input"].update({"accumulator_commitment": "blake2b-256:" + "cc" * 32})),
        ("verifier_handle_commitment_drift", lambda e: e["input"].update({"accumulator_verifier_handle_commitment": "blake2b-256:" + "dd" * 32})),
        ("selected_slice_ids_reordered", lambda e: e["input"].update({"selected_slice_ids": list(reversed(e["input"]["selected_slice_ids"]))})),
        ("row_source_hash_drift", lambda e: e["input"]["rows"][0].update({"source_payload_sha256": "ee" * 32})),
        ("row_proof_backend_version_drift", lambda e: e["input"]["rows"][1].update({"proof_backend_version": "stwo-drift"})),
        ("row_verified_false", lambda e: e["input"]["rows"][0].update({"verified": False})),
        ("non_claims_reordered", lambda e: e["input"].update({"non_claims": list(reversed(e["input"]["non_claims"]))})),
        (
            "proof_verifier_hardening_reordered",
            lambda e: e["input"].update(
                {"proof_verifier_hardening": list(reversed(e["input"]["proof_verifier_hardening"]))}
            ),
        ),
        (
            "validation_commands_reordered",
            lambda e: e["input"].update({"validation_commands": list(reversed(e["input"]["validation_commands"]))}),
        ),
        ("non_claim_removed", lambda e: e["input"].update({"non_claims": e["input"]["non_claims"][:-1]})),
        ("validation_command_drift", lambda e: e["input"].update({"validation_commands": e["input"]["validation_commands"][:-1]})),
        ("proof_len_relabelled_as_nanozk_win", lambda e: e["input"].update({"nanozk_win": True})),
    ]


def run_mutations(envelope: dict[str, Any], input_obj: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for index, (name, mutate) in enumerate(mutations()):
        mutated = copy.deepcopy(envelope)
        mutate(mutated)
        try:
            validate_artifact(mutated, input_obj)
        except OuterStatementGateError as error:
            cases.append(
                {
                    "index": index,
                    "mutation": name,
                    "rejected": True,
                    "mutated_accepted": False,
                    "error": str(error),
                }
            )
        else:
            cases.append(
                {
                    "index": index,
                    "mutation": name,
                    "rejected": False,
                    "mutated_accepted": True,
                    "error": None,
                }
            )
    return cases


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp_path = pathlib.Path(tmp.name)
    tmp_path.replace(path)


def write_tsv(path: pathlib.Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as tmp:
        writer = csv.DictWriter(
            tmp,
            fieldnames=[
                "decision",
                "result",
                "claim_boundary",
                "selected_checked_rows",
                "native_outer_statement_proof_bytes",
                "native_outer_statement_envelope_bytes",
                "nanozk_reported_transformer_block_proof_bytes",
                "proof_vs_nanozk_reported_row_ratio",
                "all_mutations_rejected",
                "case_count",
            ],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        metrics = result["metrics"]
        writer.writerow(
            {
                "decision": result["decision"],
                "result": result["result"],
                "claim_boundary": result["claim_boundary"],
                "selected_checked_rows": metrics["selected_checked_rows"],
                "native_outer_statement_proof_bytes": metrics["native_outer_statement_proof_bytes"],
                "native_outer_statement_envelope_bytes": metrics["native_outer_statement_envelope_bytes"],
                "nanozk_reported_transformer_block_proof_bytes": metrics["nanozk_reported_transformer_block_proof_bytes"],
                "proof_vs_nanozk_reported_row_ratio": metrics["proof_vs_nanozk_reported_row_ratio"],
                "all_mutations_rejected": str(result["all_mutations_rejected"]).lower(),
                "case_count": result["case_count"],
            }
        )
        tmp_path = pathlib.Path(tmp.name)
    tmp_path.replace(path)


def same_output_path(left: pathlib.Path, right: pathlib.Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


def build_gate() -> dict[str, Any]:
    input_obj = load_json(INPUT_JSON)
    envelope = load_json(ENVELOPE_JSON)
    validate_artifact(envelope, input_obj)
    cases = run_mutations(envelope, input_obj)
    result = build_result(envelope, input_obj, cases)
    if not result["all_mutations_rejected"]:
        raise OuterStatementGateError("one or more mutations were accepted")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    if same_output_path(args.write_json, args.write_tsv):
        raise SystemExit("write-json and write-tsv output paths must be distinct")
    result = build_gate()
    write_json(args.write_json, result)
    write_tsv(args.write_tsv, result)
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "decision": result["decision"],
                "result": result["result"],
                "native_outer_statement_proof_bytes": result["metrics"]["native_outer_statement_proof_bytes"],
                "proof_vs_nanozk_reported_row_ratio": result["metrics"]["proof_vs_nanozk_reported_row_ratio"],
                "all_mutations_rejected": result["all_mutations_rejected"],
                "case_count": result["case_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
