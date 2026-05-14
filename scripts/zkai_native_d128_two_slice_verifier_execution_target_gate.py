#!/usr/bin/env python3
"""Pin the concrete d128 two-slice native verifier-execution target.

This gate is deliberately not a recursion claim.  It materializes the two
selected inner Stwo proof envelopes and records their typed proof-field
accounting next to the compact native outer-statement proof.  The result is the
next executable target for a future native Stwo verifier-execution AIR.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

RMSNORM_INPUT = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
BRIDGE_INPUT = EVIDENCE_DIR / "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json"
RMSNORM_ENVELOPE = (
    EVIDENCE_DIR / "zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json"
)
BRIDGE_ENVELOPE = (
    EVIDENCE_DIR
    / "zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json"
)
OUTER_STATEMENT_ENVELOPE = (
    EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json"
)

JSON_OUT = EVIDENCE_DIR / "zkai-native-d128-two-slice-verifier-execution-target-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-d128-two-slice-verifier-execution-target-2026-05.tsv"

SCHEMA = "zkai-native-d128-two-slice-verifier-execution-target-gate-v1"
DECISION = "GO_SELECTED_INNER_PROOF_OBJECTS_PINNED_NATIVE_VERIFIER_EXECUTION_TARGET"
RESULT = "TARGET_PINNED_NOT_NATIVE_VERIFIER_EXECUTION_YET"
ISSUE = 581
CLAIM_BOUNDARY = (
    "SELECTED_INNER_STWO_PROOF_OBJECTS_PINNED_FOR_FUTURE_NATIVE_VERIFIER_EXECUTION_"
    "NOT_RECURSION_NOT_NANOZK_PROOF_SIZE_WIN"
)
QUESTION = (
    "What exact proof objects and typed proof-field surface must the next native "
    "Stwo two-slice verifier-execution AIR consume?"
)
FIRST_BLOCKER = (
    "the target proof envelopes are now concrete, but the repo still lacks a native "
    "Stwo AIR that executes the two selected inner Stwo verifier checks"
)
NEXT_BACKEND_STEP = (
    "replace the compact host-verified outer statement binding with native Stwo "
    "verifier-execution constraints for the pinned rmsnorm_public_rows and "
    "rmsnorm_projection_bridge proof envelopes"
)

NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES = 6_900
EXPECTED_SELECTED_SLICE_COUNT = 2
EXPECTED_SELECTED_ROWS = 256

EXPECTED_ROWS = {
    "rmsnorm_public_rows_inner_stwo_proof": {
        "role": "rmsnorm_public_rows_inner_stwo_proof",
        "path": "zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json",
        "input_path": "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json",
        "proof_backend_version": "stwo-d128-rmsnorm-public-row-air-proof-v3",
        "statement_version": "zkai-d128-rmsnorm-public-row-statement-v2",
        "proof_json_size_bytes": 22_425,
        "local_typed_bytes": 9_128,
        "envelope_size_bytes": 217_347,
        "proof_backend": "stwo",
        "input": {
            "path": "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json",
            "file_sha256": "d80f9f16e5f8aef3a8ec49271bb0616483cb6906731539aea2f73ba4678123ec",
            "payload_sha256": "19688310ba6001e16b80c15532f74b59097222a1aa9be132ea66b11a116ded05",
            "schema": "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3",
            "decision": "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF",
            "statement_commitment": "blake2b-256:de944915f2664ac7a893f4ba9a029323f7408eac58bf39170a0935d7832ccbd8",
            "public_instance_commitment": "blake2b-256:2dfa2ceffd67f95059b3d6cd639a82577f2bbd7be43e99c25814feb703a8fd72",
            "proof_native_parameter_commitment": "blake2b-256:8d8bded756f3290980eaab322ba986b02c5584bc8348c2ffcfa4e4860a80944c",
        },
        "record_stream_bytes": 1_084,
        "grouped_reconstruction": {
            "fixed_overhead": 48,
            "fri_decommitments": 1_856,
            "fri_samples": 320,
            "oods_samples": 2_848,
            "queries_values": 2_136,
            "trace_decommitments": 1_920,
        },
        "record_stream_sha256": "29ea9b1ed4f4a076eadabb0d79bd25a179bc4ce130b902a62c7a31e80f56f049",
        "proof_sha256": "4cd3640021387e11367c3567a13033130451e4f6ce578b8fdd8a666002e97109",
        "envelope_sha256": "a8d8aca5db1adc1d6a187d3e30ccd3f3c8d9f26b3dd97cbd56ebe2d460c477f2",
        "object_class": "selected_inner_stwo_proof_envelope",
        "native_verifier_execution_status": "target_input_only_not_executed_in_native_outer_proof",
    },
    "rmsnorm_projection_bridge_inner_stwo_proof": {
        "role": "rmsnorm_projection_bridge_inner_stwo_proof",
        "path": "zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
        "input_path": "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json",
        "proof_backend_version": "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1",
        "statement_version": "zkai-d128-rmsnorm-to-projection-bridge-statement-v1",
        "proof_json_size_bytes": 12_441,
        "local_typed_bytes": 3_560,
        "envelope_size_bytes": 117_771,
        "proof_backend": "stwo",
        "input": {
            "path": "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json",
            "file_sha256": "11f93a3ecee19c40ff14d154e054dab56a1b9c1a2dbb1d609a918e201e6fd849",
            "payload_sha256": "e6e46f2e35df3177790c7dbdc5c519f4a7d62e8ed6cba0501ffac94db73975f3",
            "schema": "zkai-d128-rmsnorm-to-projection-bridge-air-proof-input-v1",
            "decision": "GO_INPUT_FOR_D128_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF",
            "statement_commitment": "blake2b-256:fe0a9e59560611ed5220fd25b082806977a66a7032f457fce2cd5c3a41856728",
            "public_instance_commitment": "blake2b-256:ca94d85cb0ed5e9001cd3def00817060745fa015bd8dda5f08732944f7418383",
            "proof_native_parameter_commitment": "blake2b-256:ff31d2b502dac1e7d9f9cca69c4bd31e93e068dab49884e61a300a99389d58c1",
        },
        "record_stream_bytes": 1_084,
        "grouped_reconstruction": {
            "fixed_overhead": 48,
            "fri_decommitments": 1_344,
            "fri_samples": 240,
            "oods_samples": 224,
            "queries_values": 168,
            "trace_decommitments": 1_536,
        },
        "record_stream_sha256": "a2eb1ac88df052adc5291c8ef87265812f66230300a426d7a18eaa9650a3ec1f",
        "proof_sha256": "08a33aff4f55ab30c6a8d419be571c8fe08855ddf1e3f122b635e1aa0befdd0e",
        "envelope_sha256": "1597c803881a3e57b63d2461abbc46f187361026c55f872722335219d7e4c5ef",
        "object_class": "selected_inner_stwo_proof_envelope",
        "native_verifier_execution_status": "target_input_only_not_executed_in_native_outer_proof",
    },
    "compressed_outer_statement_binding_proof": {
        "role": "compressed_outer_statement_binding_proof",
        "path": "zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
        "input_path": "zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json",
        "proof_backend_version": "stwo-d128-two-slice-outer-statement-air-proof-v2-compressed-digest",
        "statement_version": "zkai-d128-two-slice-outer-statement-v1",
        "proof_json_size_bytes": 3_516,
        "local_typed_bytes": 1_792,
        "envelope_size_bytes": 34_471,
        "proof_backend": "stwo",
        "input": {
            "path": "zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json",
            "file_sha256": "3e8526da8ae9e9491ddd225873c5e03a6128c957a18d5a43e3793e5c08133b07",
            "payload_sha256": "29c8be2ff5189b0e5c34762cb68e86d41426792d63b42da7cf1e27ef9608443a",
            "schema": "zkai-native-d128-two-slice-outer-statement-air-proof-input-v1",
            "decision": "NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_INPUT",
            "statement_commitment": "blake2b-256:ab06c13b3bd24aad37285c4b6c759b9c30faf747af3248c2e45a2c245e7f8dc8",
            "public_instance_commitment": "blake2b-256:dbb25a1e94bb38c2aeedfcf38b2cebd401427c633860577893e46389f3565beb",
            "proof_native_parameter_commitment": "blake2b-256:9528113a0e62dc8565c2c5974d47c9859494a16fed307ef91881a2a2705fbf80",
        },
        "record_stream_bytes": 1_084,
        "grouped_reconstruction": {
            "fixed_overhead": 48,
            "fri_decommitments": 32,
            "fri_samples": 48,
            "oods_samples": 960,
            "queries_values": 480,
            "trace_decommitments": 224,
        },
        "record_stream_sha256": "3764bc286e5dffee3d9186861a5c2faeb44eff4add7a5c9613bb302e80197fad",
        "proof_sha256": "9977aeefe8021845a46a382be143824f10605b3ec676eaf0ed25e46f2d90e5f1",
        "envelope_sha256": "07254ada114c68ba129f90ccfa0d9a7aacbba2bc1ae64388e5a1bd12fe944aca",
        "object_class": "native_outer_statement_binding_proof_not_verifier_execution",
        "native_verifier_execution_status": "target_input_only_not_executed_in_native_outer_proof",
    },
}

EXPECTED_AGGREGATE = {
    "selected_inner_proof_json_bytes": 34_866,
    "selected_inner_local_typed_bytes": 12_688,
    "compressed_outer_statement_json_bytes": 3_516,
    "compressed_outer_statement_local_typed_bytes": 1_792,
    "inner_json_over_outer_statement_json_ratio": 9.916382,
    "inner_typed_over_outer_statement_typed_ratio": 7.080357,
    "outer_statement_json_share_of_inner_json": 0.100843,
    "outer_statement_typed_share_of_inner_typed": 0.141236,
    "selected_inner_json_ratio_vs_nanozk_paper_row": 5.053043,
    "selected_inner_typed_ratio_vs_nanozk_paper_row": 1.838841,
    "outer_statement_json_ratio_vs_nanozk_paper_row": 0.509565,
    "outer_statement_typed_ratio_vs_nanozk_paper_row": 0.25971,
    "selected_inner_typed_bytes_above_nanozk_paper_row": 5_788,
    "nanozk_paper_row_share_of_selected_inner_typed_bytes": 0.543821,
}

NATIVE_VERIFIER_EXECUTION_REQUIREMENTS = [
    "consume the pinned rmsnorm_public_rows proof envelope as verifier input",
    "consume the pinned rmsnorm_projection_bridge proof envelope as verifier input",
    "recompute or bind each selected inner proof commitment root in native Stwo constraints",
    "bind selected slice IDs, statement commitments, source hashes, and backend-version labels as public inputs",
    "execute the selected inner verifier checks instead of trusting host-verified booleans",
    "emit native outer proof bytes from that verifier-execution object, not package bytes",
    "reject relabeling, proof-byte, public-input-order, source-hash, and backend-version mutations",
]

NON_CLAIMS = [
    "not native verifier execution of the selected inner Stwo proofs",
    "not recursion or proof-carrying data",
    "not a native d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not verifier-time or prover-time evidence",
    "not full transformer inference",
    "not production-ready zkML",
]

VALIDATION_COMMANDS = [
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_selected_two_slice_proof_envelopes -- prove docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_selected_two_slice_proof_envelopes -- verify docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "python3 scripts/zkai_native_d128_two_slice_verifier_execution_target_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_d128_two_slice_verifier_execution_target_gate.py scripts/tests/test_zkai_native_d128_two_slice_verifier_execution_target_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_d128_two_slice_verifier_execution_target_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend --test zkai_d128_selected_two_slice_proof_envelopes_cli",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend --bin zkai_d128_selected_two_slice_proof_envelopes",
    "cargo +nightly-2025-07-14 fmt --check",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "role",
    "object_class",
    "proof_backend_version",
    "proof_json_size_bytes",
    "local_typed_bytes",
    "record_stream_sha256",
    "proof_sha256",
)

MUTATION_NAMES = (
    "rmsnorm_path_drift",
    "bridge_path_drift",
    "outer_statement_path_drift",
    "rmsnorm_backend_version_drift",
    "bridge_statement_version_drift",
    "rmsnorm_typed_bytes_drift",
    "bridge_json_bytes_drift",
    "outer_statement_typed_bytes_drift",
    "record_stream_sha_drift",
    "proof_sha_drift",
    "envelope_sha_drift",
    "selected_inner_sum_drift",
    "inner_outer_ratio_drift",
    "nanozk_ratio_drift",
    "outer_statement_promoted_to_verifier_execution",
    "native_verifier_execution_claim_enabled",
    "matched_nanozk_claim_enabled",
    "first_blocker_removed",
    "next_backend_step_weakened",
    "requirement_removed",
    "non_claim_removed",
    "validation_command_drift",
    "decision_changed_to_native_execution",
    "proof_backend_drift",
    "input_descriptor_hash_drift",
    "record_stream_bytes_drift",
    "grouped_reconstruction_drift",
    "native_verifier_execution_status_drift",
    "unknown_top_level_field_added",
)


class VerifierExecutionTargetGateError(ValueError):
    pass


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise VerifierExecutionTargetGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise VerifierExecutionTargetGateError(f"invalid JSON value: {err}") from err


def pretty_json(value: dict[str, Any]) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise VerifierExecutionTargetGateError(f"invalid JSON value: {err}") from err


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + sha256_hex(canonical_json_bytes(material))


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _reject_duplicate_json_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in items:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VerifierExecutionTargetGateError(f"{field} must be object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise VerifierExecutionTargetGateError(f"{field} must be list")
    return value


def require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerifierExecutionTargetGateError(f"{field} must be non-empty string")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VerifierExecutionTargetGateError(f"{field} must be integer")
    return value


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except Exception as err:
        raise VerifierExecutionTargetGateError(f"failed to parse JSON {path}: {err}") from err
    return require_dict(payload, str(path)), raw


def run_accounting_cli() -> dict[str, Any]:
    command = [
        "cargo",
        "+nightly-2025-07-14",
        "run",
        "--locked",
        "--features",
        "stwo-backend",
        "--bin",
        "zkai_stwo_proof_binary_accounting",
        "--",
        "--evidence-dir",
        str(EVIDENCE_DIR.relative_to(ROOT)),
        str(RMSNORM_ENVELOPE.relative_to(ROOT)),
        str(BRIDGE_ENVELOPE.relative_to(ROOT)),
        str(OUTER_STATEMENT_ENVELOPE.relative_to(ROOT)),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except subprocess.CalledProcessError as err:
        raise VerifierExecutionTargetGateError(
            f"binary accounting CLI failed: {err.stderr[-2000:]}"
        ) from err
    except subprocess.TimeoutExpired as err:
        raise VerifierExecutionTargetGateError("binary accounting CLI timed out") from err
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise VerifierExecutionTargetGateError(f"binary accounting CLI emitted invalid JSON: {err}") from err


def envelope_size(path: str) -> int:
    return (EVIDENCE_DIR / path).stat().st_size


def envelope_input_descriptor(path: str) -> dict[str, Any]:
    payload, raw = load_json(EVIDENCE_DIR / path)
    return {
        "path": path,
        "file_sha256": sha256_hex(raw),
        "payload_sha256": sha256_hex(canonical_json_bytes(payload)),
        "schema": payload.get("schema"),
        "decision": payload.get("decision"),
        "statement_commitment": payload.get("statement_commitment"),
        "public_instance_commitment": payload.get("public_instance_commitment"),
        "proof_native_parameter_commitment": payload.get("proof_native_parameter_commitment"),
    }


def row_from_cli(role: str, cli_row: dict[str, Any]) -> dict[str, Any]:
    expected = EXPECTED_ROWS[role]
    metadata = require_dict(cli_row.get("envelope_metadata"), f"{role}.envelope_metadata")
    accounting = require_dict(cli_row.get("local_binary_accounting"), f"{role}.local_binary_accounting")
    path = require_str(cli_row.get("evidence_relative_path"), f"{role}.evidence_relative_path")
    if path != expected["path"]:
        raise VerifierExecutionTargetGateError(f"{role} path drift: {path}")
    if require_str(metadata.get("proof_backend_version"), f"{role}.proof_backend_version") != expected[
        "proof_backend_version"
    ]:
        raise VerifierExecutionTargetGateError(f"{role} proof backend version drift")
    if require_str(metadata.get("statement_version"), f"{role}.statement_version") != expected["statement_version"]:
        raise VerifierExecutionTargetGateError(f"{role} statement version drift")
    proof_json_size_bytes = require_int(cli_row.get("proof_json_size_bytes"), f"{role}.proof_json_size_bytes")
    local_typed_bytes = require_int(accounting.get("typed_size_estimate_bytes"), f"{role}.local_typed_bytes")
    record_stream_sha256 = require_str(accounting.get("record_stream_sha256"), f"{role}.record_stream_sha256")
    proof_sha256 = require_str(cli_row.get("proof_sha256"), f"{role}.proof_sha256")
    envelope_sha256 = require_str(cli_row.get("envelope_sha256"), f"{role}.envelope_sha256")
    observed = {
        "proof_json_size_bytes": proof_json_size_bytes,
        "local_typed_bytes": local_typed_bytes,
        "proof_backend": require_str(metadata.get("proof_backend"), f"{role}.proof_backend"),
        "input": envelope_input_descriptor(expected["input_path"]),
        "record_stream_bytes": require_int(accounting.get("record_stream_bytes"), f"{role}.record_stream_bytes"),
        "grouped_reconstruction": require_dict(
            accounting.get("grouped_reconstruction"), f"{role}.grouped_reconstruction"
        ),
        "record_stream_sha256": record_stream_sha256,
        "proof_sha256": proof_sha256,
        "envelope_sha256": envelope_sha256,
        "envelope_size_bytes": envelope_size(expected["path"]),
        "native_verifier_execution_status": expected["native_verifier_execution_status"],
    }
    for key, value in observed.items():
        if value != expected[key]:
            raise VerifierExecutionTargetGateError(f"{role} {key} drift: got {value}, expected {expected[key]}")
    return {
        "role": role,
        "object_class": expected["object_class"],
        "path": path,
        "input": observed["input"],
        "proof_backend": observed["proof_backend"],
        "proof_backend_version": expected["proof_backend_version"],
        "statement_version": expected["statement_version"],
        "proof_json_size_bytes": proof_json_size_bytes,
        "local_typed_bytes": local_typed_bytes,
        "envelope_size_bytes": observed["envelope_size_bytes"],
        "record_stream_bytes": observed["record_stream_bytes"],
        "record_stream_sha256": record_stream_sha256,
        "proof_sha256": proof_sha256,
        "envelope_sha256": envelope_sha256,
        "grouped_reconstruction": observed["grouped_reconstruction"],
        "native_verifier_execution_status": observed["native_verifier_execution_status"],
    }


def rows_from_cli(summary: dict[str, Any]) -> list[dict[str, Any]]:
    if summary.get("schema") != "zkai-stwo-local-binary-proof-accounting-cli-v1":
        raise VerifierExecutionTargetGateError("binary accounting schema drift")
    rows = require_list(summary.get("rows"), "binary accounting rows")
    by_path = {require_str(row.get("evidence_relative_path"), "row.evidence_relative_path"): row for row in rows}
    if len(by_path) != 3:
        raise VerifierExecutionTargetGateError("binary accounting row count drift")
    for expected in EXPECTED_ROWS.values():
        if expected["path"] not in by_path:
            raise VerifierExecutionTargetGateError(f"binary accounting missing expected path: {expected['path']}")
    return [
        row_from_cli("rmsnorm_public_rows_inner_stwo_proof", by_path[EXPECTED_ROWS["rmsnorm_public_rows_inner_stwo_proof"]["path"]]),
        row_from_cli(
            "rmsnorm_projection_bridge_inner_stwo_proof",
            by_path[EXPECTED_ROWS["rmsnorm_projection_bridge_inner_stwo_proof"]["path"]],
        ),
        row_from_cli(
            "compressed_outer_statement_binding_proof",
            by_path[EXPECTED_ROWS["compressed_outer_statement_binding_proof"]["path"]],
        ),
    ]


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    inner_rows = rows[:2]
    outer = rows[2]
    selected_inner_json = sum(require_int(row["proof_json_size_bytes"], "inner proof_json_size_bytes") for row in inner_rows)
    selected_inner_typed = sum(require_int(row["local_typed_bytes"], "inner local_typed_bytes") for row in inner_rows)
    outer_json = require_int(outer["proof_json_size_bytes"], "outer proof_json_size_bytes")
    outer_typed = require_int(outer["local_typed_bytes"], "outer local_typed_bytes")
    computed = {
        "selected_inner_proof_json_bytes": selected_inner_json,
        "selected_inner_local_typed_bytes": selected_inner_typed,
        "compressed_outer_statement_json_bytes": outer_json,
        "compressed_outer_statement_local_typed_bytes": outer_typed,
        "inner_json_over_outer_statement_json_ratio": ratio(selected_inner_json, outer_json),
        "inner_typed_over_outer_statement_typed_ratio": ratio(selected_inner_typed, outer_typed),
        "outer_statement_json_share_of_inner_json": ratio(outer_json, selected_inner_json),
        "outer_statement_typed_share_of_inner_typed": ratio(outer_typed, selected_inner_typed),
        "selected_inner_json_ratio_vs_nanozk_paper_row": ratio(
            selected_inner_json, NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES
        ),
        "selected_inner_typed_ratio_vs_nanozk_paper_row": ratio(
            selected_inner_typed, NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES
        ),
        "outer_statement_json_ratio_vs_nanozk_paper_row": ratio(
            outer_json, NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES
        ),
        "outer_statement_typed_ratio_vs_nanozk_paper_row": ratio(
            outer_typed, NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES
        ),
        "selected_inner_typed_bytes_above_nanozk_paper_row": selected_inner_typed
        - NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES,
        "nanozk_paper_row_share_of_selected_inner_typed_bytes": ratio(
            NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES, selected_inner_typed
        ),
    }
    if computed != EXPECTED_AGGREGATE:
        raise VerifierExecutionTargetGateError(f"aggregate drift: got {computed}, expected {EXPECTED_AGGREGATE}")
    return computed


def build_payload(accounting_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = accounting_summary if accounting_summary is not None else run_accounting_cli()
    rows = rows_from_cli(summary)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "selected_slice_count": EXPECTED_SELECTED_SLICE_COUNT,
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "comparison_baseline": {
            "nanozk_paper_reported_block_proof_bytes": NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES,
            "status": "paper_reported_not_locally_reproduced_not_matched_object_class",
        },
        "proof_objects": rows,
        "aggregate": aggregate(rows),
        "first_blocker": FIRST_BLOCKER,
        "next_backend_step": NEXT_BACKEND_STEP,
        "native_verifier_execution_requirements": NATIVE_VERIFIER_EXECUTION_REQUIREMENTS,
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }
    cases = mutation_cases(payload)
    rejected = collect_mutation_rejections(payload, cases)
    payload["mutation_cases"] = rejected
    payload["mutations_checked"] = len(rejected)
    payload["mutations_rejected"] = sum(1 for case in rejected if case["rejected"])
    payload["all_mutations_rejected"] = all(case["rejected"] for case in rejected)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any], *, allow_missing_mutation_summary: bool = False) -> None:
    expected_keys = {
        "schema",
        "decision",
        "result",
        "issue",
        "question",
        "claim_boundary",
        "selected_slice_count",
        "selected_checked_rows",
        "comparison_baseline",
        "proof_objects",
        "aggregate",
        "first_blocker",
        "next_backend_step",
        "native_verifier_execution_requirements",
        "non_claims",
        "validation_commands",
        "payload_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    keys = set(payload)
    if allow_missing_mutation_summary:
        if not keys.issubset(expected_keys | mutation_keys) or not expected_keys.issubset(keys):
            raise VerifierExecutionTargetGateError("payload field drift")
        present_mutation_keys = keys & mutation_keys
        if present_mutation_keys and present_mutation_keys != mutation_keys:
            raise VerifierExecutionTargetGateError("partial mutation summary drift")
    elif keys != expected_keys | mutation_keys:
        raise VerifierExecutionTargetGateError("payload field drift")
    if payload.get("schema") != SCHEMA:
        raise VerifierExecutionTargetGateError("schema drift")
    if payload.get("decision") != DECISION:
        raise VerifierExecutionTargetGateError("decision drift")
    if payload.get("result") != RESULT:
        raise VerifierExecutionTargetGateError("result drift")
    if payload.get("issue") != ISSUE:
        raise VerifierExecutionTargetGateError("issue drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise VerifierExecutionTargetGateError("claim boundary drift")
    if payload.get("selected_slice_count") != EXPECTED_SELECTED_SLICE_COUNT:
        raise VerifierExecutionTargetGateError("selected slice count drift")
    if payload.get("selected_checked_rows") != EXPECTED_SELECTED_ROWS:
        raise VerifierExecutionTargetGateError("selected checked rows drift")
    baseline = require_dict(payload.get("comparison_baseline"), "comparison baseline")
    if baseline.get("nanozk_paper_reported_block_proof_bytes") != NANOZK_PAPER_REPORTED_BLOCK_PROOF_BYTES:
        raise VerifierExecutionTargetGateError("NANOZK baseline drift")
    if "not_matched_object_class" not in require_str(baseline.get("status"), "comparison baseline status"):
        raise VerifierExecutionTargetGateError("comparison baseline status drift")
    rows = require_list(payload.get("proof_objects"), "proof objects")
    if len(rows) != 3:
        raise VerifierExecutionTargetGateError("proof object row count drift")
    for row in rows:
        role = require_str(require_dict(row, "proof object").get("role"), "proof object role")
        expected = EXPECTED_ROWS.get(role)
        if expected is None:
            raise VerifierExecutionTargetGateError(f"unknown proof object role: {role}")
        for key in (
            "path",
            "proof_backend_version",
            "statement_version",
            "proof_json_size_bytes",
            "local_typed_bytes",
            "envelope_size_bytes",
            "record_stream_sha256",
            "proof_sha256",
            "envelope_sha256",
            "object_class",
            "proof_backend",
            "input",
            "record_stream_bytes",
            "grouped_reconstruction",
            "native_verifier_execution_status",
        ):
            if row.get(key) != expected[key]:
                raise VerifierExecutionTargetGateError(f"{role} {key} drift")
    if payload.get("aggregate") != EXPECTED_AGGREGATE:
        raise VerifierExecutionTargetGateError("aggregate drift")
    if payload.get("first_blocker") != FIRST_BLOCKER:
        raise VerifierExecutionTargetGateError("first blocker drift")
    if payload.get("next_backend_step") != NEXT_BACKEND_STEP:
        raise VerifierExecutionTargetGateError("next backend step drift")
    if payload.get("native_verifier_execution_requirements") != NATIVE_VERIFIER_EXECUTION_REQUIREMENTS:
        raise VerifierExecutionTargetGateError("native verifier execution requirements drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise VerifierExecutionTargetGateError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise VerifierExecutionTargetGateError("validation commands drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise VerifierExecutionTargetGateError("payload commitment drift")
    if not allow_missing_mutation_summary or (set(payload) & mutation_keys):
        validate_mutation_summary(payload)


def validate_mutation_summary(payload: dict[str, Any]) -> None:
    cases = require_list(payload.get("mutation_cases"), "mutation cases")
    names = tuple(require_str(require_dict(case, "mutation case").get("name"), "mutation case name") for case in cases)
    if names != MUTATION_NAMES:
        raise VerifierExecutionTargetGateError("mutation inventory drift")
    checked = require_int(payload.get("mutations_checked"), "mutations checked")
    rejected = require_int(payload.get("mutations_rejected"), "mutations rejected")
    if checked != len(MUTATION_NAMES) or rejected != len(MUTATION_NAMES):
        raise VerifierExecutionTargetGateError("mutation count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise VerifierExecutionTargetGateError("mutation rejection summary drift")
    for case in cases:
        case = require_dict(case, "mutation case")
        if case.get("rejected") is not True:
            raise VerifierExecutionTargetGateError("mutation was not rejected")
        require_str(case.get("error"), "mutation error")


def mutation_cases(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple({"name": name, "payload": mutate_payload(payload, name)} for name in MUTATION_NAMES)


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    rows = mutated["proof_objects"]
    if name == "rmsnorm_path_drift":
        rows[0]["path"] = rows[0]["path"].replace("public-row", "public-row-tampered")
    elif name == "bridge_path_drift":
        rows[1]["path"] = rows[1]["path"].replace("projection-bridge", "projection-bridge-tampered")
    elif name == "outer_statement_path_drift":
        rows[2]["path"] = rows[2]["path"].replace("outer-statement", "outer-statement-tampered")
    elif name == "rmsnorm_backend_version_drift":
        rows[0]["proof_backend_version"] += "-tampered"
    elif name == "bridge_statement_version_drift":
        rows[1]["statement_version"] += "-tampered"
    elif name == "rmsnorm_typed_bytes_drift":
        rows[0]["local_typed_bytes"] += 1
    elif name == "bridge_json_bytes_drift":
        rows[1]["proof_json_size_bytes"] += 1
    elif name == "outer_statement_typed_bytes_drift":
        rows[2]["local_typed_bytes"] += 1
    elif name == "record_stream_sha_drift":
        rows[0]["record_stream_sha256"] = "0" * 64
    elif name == "proof_sha_drift":
        rows[1]["proof_sha256"] = "0" * 64
    elif name == "envelope_sha_drift":
        rows[2]["envelope_sha256"] = "0" * 64
    elif name == "selected_inner_sum_drift":
        mutated["aggregate"]["selected_inner_local_typed_bytes"] += 1
    elif name == "inner_outer_ratio_drift":
        mutated["aggregate"]["inner_typed_over_outer_statement_typed_ratio"] += 0.000001
    elif name == "nanozk_ratio_drift":
        mutated["aggregate"]["selected_inner_typed_ratio_vs_nanozk_paper_row"] += 0.000001
    elif name == "outer_statement_promoted_to_verifier_execution":
        rows[2]["object_class"] = "native_outer_verifier_execution_proof"
    elif name == "native_verifier_execution_claim_enabled":
        mutated["decision"] = "GO_NATIVE_VERIFIER_EXECUTION"
    elif name == "matched_nanozk_claim_enabled":
        mutated["comparison_baseline"]["status"] = "matched_nanozk_proof_size_win"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "next_backend_step_weakened":
        mutated["next_backend_step"] = "claim comparison now"
    elif name == "requirement_removed":
        mutated["native_verifier_execution_requirements"] = mutated["native_verifier_execution_requirements"][:-1]
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif name == "validation_command_drift":
        mutated["validation_commands"] = mutated["validation_commands"][:-1]
    elif name == "decision_changed_to_native_execution":
        mutated["result"] = "NATIVE_VERIFIER_EXECUTION_READY"
    elif name == "proof_backend_drift":
        rows[0]["proof_backend"] = "mock"
    elif name == "input_descriptor_hash_drift":
        rows[0]["input"]["payload_sha256"] = "0" * 64
    elif name == "record_stream_bytes_drift":
        rows[1]["record_stream_bytes"] += 1
    elif name == "grouped_reconstruction_drift":
        rows[1]["grouped_reconstruction"]["fri_samples"] += 1
    elif name == "native_verifier_execution_status_drift":
        rows[2]["native_verifier_execution_status"] = "native_outer_verifier_execution_ready"
    elif name == "unknown_top_level_field_added":
        mutated["unexpected"] = True
    else:
        raise AssertionError(f"unhandled mutation {name}")
    mutated["payload_commitment"] = payload_commitment(mutated)
    return mutated


def collect_mutation_rejections(payload: dict[str, Any], cases: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    rejected = []
    for case in cases:
        try:
            validate_payload(case["payload"], allow_missing_mutation_summary=True)
        except Exception as err:
            rejected.append({"name": case["name"], "rejected": True, "error": str(err)})
        else:
            rejected.append({"name": case["name"], "rejected": False, "error": ""})
    return rejected


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in payload["proof_objects"]:
        writer.writerow({key: row.get(key, "") for key in TSV_COLUMNS})
    return output.getvalue()


def reject_symlinked_path_components(path: pathlib.Path) -> None:
    root = ROOT.resolve()
    resolved = path.resolve()
    try:
        relative_parts = resolved.relative_to(root).parts
    except ValueError as err:
        raise VerifierExecutionTargetGateError(f"output path escapes repository: {path}") from err
    current = root
    for part in relative_parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise VerifierExecutionTargetGateError(f"output parent component is symlink: {current}")


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    raw_path = path if path.is_absolute() else ROOT / path
    reject_symlinked_path_components(raw_path)
    if raw_path.exists() and raw_path.is_symlink():
        raise VerifierExecutionTargetGateError(f"refusing to write symlink output: {raw_path}")
    resolved = raw_path.resolve()
    evidence = EVIDENCE_DIR.resolve()
    try:
        resolved.relative_to(evidence)
    except ValueError as err:
        raise VerifierExecutionTargetGateError(f"output path must be under evidence dir: {raw_path}") from err
    return resolved


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    path = validate_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp_path.replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    validate_payload(payload)
    write_text_atomic(path, pretty_json(payload) + "\n")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    validate_payload(payload)
    write_text_atomic(path, to_tsv(payload))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    payload = build_payload()
    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload)
    if not args.write_json and not args.write_tsv:
        print(pretty_json(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
