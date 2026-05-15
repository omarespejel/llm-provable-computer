#!/usr/bin/env python3
"""Gate the fused d128 gate/value plus activation proof-size result.

This is the adjacent-component experiment opened after the dense
compact-preprocessed no-go.  It records a real native Stwo fused proof over the
d128 gate/value projection relation plus the activation/SwiGLU relation, then
compares it with the two separate native proof objects under local typed
proof-field accounting.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import pathlib
import stat
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
ACCOUNTING_PATH = EVIDENCE_DIR / "zkai-d128-gate-value-activation-fused-binary-accounting-2026-05.json"
FUSED_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json"
GATE_VALUE_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-gate-value-projection-proof-2026-05.envelope.json"
ACTIVATION_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-activation-swiglu-proof-2026-05.envelope.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-gate-value-activation-fused-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-gate-value-activation-fused-gate-2026-05.tsv"

SCHEMA = "zkai-d128-gate-value-activation-fused-gate-v1"
DECISION = "GO_D128_GATE_VALUE_ACTIVATION_FUSED_TYPED_PROOF_SAVING"
RESULT = "GO_FUSED_ADJACENT_DENSE_ACTIVATION_SAVES_5520_TYPED_BYTES"
ROUTE_ID = "native_stwo_d128_gate_value_projection_plus_activation_swiglu_fused"
QUESTION = (
    "Can a native Stwo proof over adjacent d128 gate/value and activation/SwiGLU "
    "components share proof plumbing and beat the two separate native proof objects?"
)
CLAIM_BOUNDARY = (
    "FUSED_D128_GATE_VALUE_PLUS_ACTIVATION_SAVES_TYPED_PROOF_BYTES_VS_SEPARATE_NATIVE_OBJECTS_"
    "NOT_A_FULL_BLOCK_PROOF_NOT_A_NANOZK_BENCHMARK"
)
FIRST_BLOCKER = (
    "The fused proof saves typed bytes against the two separate native proof objects, but it still "
    "covers only gate/value plus activation/SwiGLU, not the full d128 transformer block and not a "
    "matched NANOZK workload."
)
NEXT_RESEARCH_STEP = (
    "extend the fusion probe to include down-projection or a lookup-heavy sidecar, then check "
    "whether the saving persists across the fuller block surface"
)

FUSED_ROLE = "fused_gate_value_activation"
GATE_VALUE_ROLE = "separate_gate_value"
ACTIVATION_ROLE = "separate_activation_swiglu"

EXPECTED_ROLES = {
    "zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json": {
        "role": FUSED_ROLE,
        "proof_backend_version": "stwo-d128-gate-value-activation-fused-air-proof-v1",
        "statement_version": "zkai-d128-gate-value-activation-fused-statement-v1",
        "proof_json_size_bytes": 62_865,
        "local_typed_bytes": 17_760,
        "envelope_json_size_bytes": 565_378,
    },
    "zkai-d128-gate-value-projection-proof-2026-05.envelope.json": {
        "role": GATE_VALUE_ROLE,
        "proof_backend_version": "stwo-d128-gate-value-projection-air-proof-v1",
        "statement_version": "zkai-d128-gate-value-projection-statement-v1",
        "proof_json_size_bytes": 57_930,
        "local_typed_bytes": 16_360,
        "envelope_json_size_bytes": 483_523,
    },
    "zkai-d128-activation-swiglu-proof-2026-05.envelope.json": {
        "role": ACTIVATION_ROLE,
        "proof_backend_version": "stwo-d128-activation-swiglu-air-proof-v1",
        "statement_version": "zkai-d128-activation-swiglu-statement-v1",
        "proof_json_size_bytes": 24_449,
        "local_typed_bytes": 6_920,
        "envelope_json_size_bytes": 226_819,
    },
}

EXPECTED_GROUPED = {
    FUSED_ROLE: {
        "fixed_overhead": 48,
        "fri_decommitments": 11_328,
        "fri_samples": 752,
        "oods_samples": 640,
        "queries_values": 480,
        "trace_decommitments": 4_512,
    },
    GATE_VALUE_ROLE: {
        "fixed_overhead": 48,
        "fri_decommitments": 10_656,
        "fri_samples": 720,
        "oods_samples": 352,
        "queries_values": 264,
        "trace_decommitments": 4_320,
    },
    ACTIVATION_ROLE: {
        "fixed_overhead": 48,
        "fri_decommitments": 3_232,
        "fri_samples": 416,
        "oods_samples": 416,
        "queries_values": 312,
        "trace_decommitments": 2_496,
    },
}

EXPECTED_GROUPED_DELTA_BYTES = {
    "fixed_overhead": -48,
    "fri_decommitments": -2_560,
    "fri_samples": -384,
    "oods_samples": -128,
    "queries_values": -96,
    "trace_decommitments": -2_304,
}

EXPECTED_AGGREGATE = {
    "profiles_checked": 1,
    "gate_value_row_count": 131_072,
    "activation_row_count": 512,
    "separate_proof_json_size_bytes": 82_379,
    "fused_proof_json_size_bytes": 62_865,
    "json_saving_vs_separate_bytes": 19_514,
    "json_saving_ratio_vs_separate": 0.236881,
    "json_ratio_vs_separate": 0.763119,
    "separate_local_typed_bytes": 23_280,
    "fused_local_typed_bytes": 17_760,
    "typed_saving_vs_separate_bytes": 5_520,
    "typed_saving_ratio_vs_separate": 0.237113,
    "typed_ratio_vs_separate": 0.762887,
    "comparison_status": "fused_adjacent_native_proof_saves_typed_bytes_vs_separate_objects",
}

MECHANISM = (
    "gate/value projection and activation/SwiGLU are proved as two components inside one native Stwo proof",
    "the fused proof commits one shared preprocessed tree and one shared base tree for both adjacent components",
    "the source handoff is explicit: activation source commitments and vectors must match the gate/value output",
    "the saving is mostly shared FRI and Merkle decommitment plumbing, not a JSON formatting effect",
    "the same publication-v1 PCS profile is used; no verifier query weakening is claimed",
)

NON_CLAIMS = (
    "not a full d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not recursion or proof-carrying data",
    "not private parameter-opening proof",
    "not upstream Stwo proof serialization",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- prove docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- build-input docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- prove docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-d128-gate-value-activation-fused-binary-accounting-2026-05.json",
    "python3 scripts/zkai_d128_gate_value_activation_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_gate_value_activation_fused_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_gate_value_activation_fused_proof --lib",
    "git diff --check",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "route_id",
    "fused_local_typed_bytes",
    "separate_local_typed_bytes",
    "typed_saving_vs_separate_bytes",
    "typed_ratio_vs_separate",
    "fused_proof_json_size_bytes",
    "separate_proof_json_size_bytes",
    "json_saving_vs_separate_bytes",
    "comparison_status",
)

MUTATION_NAMES = (
    "schema_relabeling",
    "decision_overclaim",
    "result_overclaim",
    "claim_boundary_overclaim",
    "fused_typed_metric_smuggling",
    "separate_typed_metric_smuggling",
    "typed_saving_metric_smuggling",
    "typed_ratio_metric_smuggling",
    "json_saving_metric_smuggling",
    "comparison_status_overclaim",
    "grouped_delta_smuggling",
    "role_backend_version_relabeling",
    "non_claim_removed",
    "mechanism_removed",
    "first_blocker_removed",
    "validation_command_drift",
    "payload_commitment_relabeling",
    "unknown_field_injection",
)


class FusedGateError(ValueError):
    pass


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        raise FusedGateError("ratio denominator must be non-zero")
    return round(numerator / denominator, 6)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def payload_commitment(payload: dict[str, Any]) -> str:
    canonical = copy.deepcopy(payload)
    canonical.pop("payload_commitment", None)
    return "sha256:" + hashlib.sha256(canonical_bytes(canonical)).hexdigest()


def read_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    if path.is_symlink():
        raise FusedGateError(f"{label} must not be a symlink: {path}")
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise FusedGateError(f"{label} escapes evidence directory: {path}") from err
    try:
        pre = resolved.lstat()
    except OSError as err:
        raise FusedGateError(f"failed to stat {label}: {err}") from err
    if not stat.S_ISREG(pre.st_mode):
        raise FusedGateError(f"{label} is not a regular file: {path}")
    try:
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as err:
        raise FusedGateError(f"failed to open {label}: {err}") from err
    try:
        post = os.fstat(fd)
        if (pre.st_dev, pre.st_ino) != (post.st_dev, post.st_ino):
            raise FusedGateError(f"{label} changed while opening: {path}")
        raw = os.read(fd, max_bytes + 1)
    finally:
        if fd is not None:
            os.close(fd)
    if len(raw) > max_bytes:
        raise FusedGateError(f"{label} exceeds max size: got at least {len(raw)} bytes")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise FusedGateError(f"{label} is not JSON: {err}") from err


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FusedGateError(f"{label} must be object")
    return value


def rows_by_role(accounting: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = accounting.get("rows")
    if not isinstance(rows, list) or len(rows) != 3:
        raise FusedGateError("accounting rows must contain exactly fused, gate/value, activation")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        row = require_dict(row, "accounting row")
        relative = row.get("evidence_relative_path")
        expected = EXPECTED_ROLES.get(relative)
        if expected is None:
            raise FusedGateError(f"unexpected accounting row path: {relative}")
        role = expected["role"]
        result[role] = row
    if set(result) != {FUSED_ROLE, GATE_VALUE_ROLE, ACTIVATION_ROLE}:
        raise FusedGateError("accounting roles are incomplete")
    return result


def validate_accounting_row(row: dict[str, Any], expected: dict[str, Any]) -> None:
    metadata = require_dict(row.get("envelope_metadata"), "row envelope metadata")
    for field in ("proof_backend_version", "statement_version"):
        if metadata.get(field) != expected[field]:
            raise FusedGateError(f"{expected['role']} {field} drift")
    if row.get("proof_json_size_bytes") != expected["proof_json_size_bytes"]:
        raise FusedGateError(f"{expected['role']} proof JSON byte drift")
    accounting = require_dict(row.get("local_binary_accounting"), "local binary accounting")
    if accounting.get("typed_size_estimate_bytes") != expected["local_typed_bytes"]:
        raise FusedGateError(f"{expected['role']} typed byte drift")
    if accounting.get("component_sum_bytes") != expected["local_typed_bytes"]:
        raise FusedGateError(f"{expected['role']} component sum drift")
    grouped = require_dict(accounting.get("grouped_reconstruction"), "grouped reconstruction")
    if grouped != EXPECTED_GROUPED[expected["role"]]:
        raise FusedGateError(f"{expected['role']} grouped reconstruction drift")


def validate_envelope(path: pathlib.Path, expected: dict[str, Any]) -> dict[str, Any]:
    try:
        envelope_size = path.stat().st_size
    except OSError as err:
        raise FusedGateError(f"failed to stat {expected['role']} envelope: {err}") from err
    if envelope_size != expected["envelope_json_size_bytes"]:
        raise FusedGateError(f"{expected['role']} envelope byte-size drift")
    envelope = require_dict(read_json(path, 16 * 1024 * 1024, expected["role"]), expected["role"])
    if envelope.get("proof_backend_version") != expected["proof_backend_version"]:
        raise FusedGateError(f"{expected['role']} envelope backend version drift")
    if envelope.get("statement_version") != expected["statement_version"]:
        raise FusedGateError(f"{expected['role']} envelope statement version drift")
    proof = envelope.get("proof")
    if not isinstance(proof, list) or len(proof) != expected["proof_json_size_bytes"]:
        raise FusedGateError(f"{expected['role']} proof payload size drift")
    return envelope


def build_payload() -> dict[str, Any]:
    accounting = require_dict(read_json(ACCOUNTING_PATH, 4 * 1024 * 1024, "accounting JSON"), "accounting JSON")
    role_rows = rows_by_role(accounting)
    for relative, expected in EXPECTED_ROLES.items():
        validate_accounting_row(role_rows[expected["role"]], expected)

    fused_envelope = validate_envelope(FUSED_ENVELOPE_PATH, EXPECTED_ROLES[FUSED_ENVELOPE_PATH.name])
    gate_envelope = validate_envelope(GATE_VALUE_ENVELOPE_PATH, EXPECTED_ROLES[GATE_VALUE_ENVELOPE_PATH.name])
    activation_envelope = validate_envelope(ACTIVATION_ENVELOPE_PATH, EXPECTED_ROLES[ACTIVATION_ENVELOPE_PATH.name])
    validate_fused_handoff(fused_envelope, gate_envelope, activation_envelope)

    fused = EXPECTED_ROLES[FUSED_ENVELOPE_PATH.name]
    gate = EXPECTED_ROLES[GATE_VALUE_ENVELOPE_PATH.name]
    activation = EXPECTED_ROLES[ACTIVATION_ENVELOPE_PATH.name]
    separate_typed = gate["local_typed_bytes"] + activation["local_typed_bytes"]
    separate_json = gate["proof_json_size_bytes"] + activation["proof_json_size_bytes"]
    try:
        fused_input = require_dict(fused_envelope["input"], "fused envelope input")
        gate_value_row_count = fused_input["gate_value_row_count"]
        activation_row_count = fused_input["activation_row_count"]
    except (KeyError, TypeError) as error:
        keys = sorted(fused_envelope.keys()) if isinstance(fused_envelope, dict) else type(fused_envelope).__name__
        raise FusedGateError(f"fused envelope row-count field drift: {error}; keys={keys}") from error
    aggregate = {
        "profiles_checked": 1,
        "gate_value_row_count": gate_value_row_count,
        "activation_row_count": activation_row_count,
        "separate_proof_json_size_bytes": separate_json,
        "fused_proof_json_size_bytes": fused["proof_json_size_bytes"],
        "json_saving_vs_separate_bytes": separate_json - fused["proof_json_size_bytes"],
        "json_saving_ratio_vs_separate": rounded_ratio(separate_json - fused["proof_json_size_bytes"], separate_json),
        "json_ratio_vs_separate": rounded_ratio(fused["proof_json_size_bytes"], separate_json),
        "separate_local_typed_bytes": separate_typed,
        "fused_local_typed_bytes": fused["local_typed_bytes"],
        "typed_saving_vs_separate_bytes": separate_typed - fused["local_typed_bytes"],
        "typed_saving_ratio_vs_separate": rounded_ratio(separate_typed - fused["local_typed_bytes"], separate_typed),
        "typed_ratio_vs_separate": rounded_ratio(fused["local_typed_bytes"], separate_typed),
        "comparison_status": EXPECTED_AGGREGATE["comparison_status"],
    }
    if aggregate != EXPECTED_AGGREGATE:
        raise FusedGateError(f"aggregate drift: {aggregate}")

    grouped_delta = {}
    for key, fused_value in EXPECTED_GROUPED[FUSED_ROLE].items():
        grouped_delta[key] = fused_value - EXPECTED_GROUPED[GATE_VALUE_ROLE][key] - EXPECTED_GROUPED[ACTIVATION_ROLE][key]
    if grouped_delta != EXPECTED_GROUPED_DELTA_BYTES:
        raise FusedGateError("grouped delta drift")

    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
        "aggregate": aggregate,
        "roles": copy.deepcopy(EXPECTED_ROLES),
        "grouped_breakdown": copy.deepcopy(EXPECTED_GROUPED),
        "grouped_delta_vs_separate_bytes": grouped_delta,
        "mechanism": list(MECHANISM),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "evidence": {
            "accounting_json": str(ACCOUNTING_PATH.relative_to(ROOT)),
            "fused_envelope": str(FUSED_ENVELOPE_PATH.relative_to(ROOT)),
            "gate_value_envelope": str(GATE_VALUE_ENVELOPE_PATH.relative_to(ROOT)),
            "activation_envelope": str(ACTIVATION_ENVELOPE_PATH.relative_to(ROOT)),
        },
        "mutation_inventory": {
            "case_count": len(MUTATION_NAMES),
            "cases": list(MUTATION_NAMES),
        },
    }
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload)
    return payload


def validate_fused_handoff(fused: dict[str, Any], gate: dict[str, Any], activation: dict[str, Any]) -> None:
    fused_input = require_dict(fused.get("input"), "fused input")
    gate_input = require_dict(gate.get("input"), "gate/value input")
    activation_input = require_dict(activation.get("input"), "activation input")
    checks = (
        ("gate_value_statement_commitment", gate_input.get("statement_commitment")),
        ("gate_value_public_instance_commitment", gate_input.get("public_instance_commitment")),
        ("activation_statement_commitment", activation_input.get("statement_commitment")),
        ("activation_public_instance_commitment", activation_input.get("public_instance_commitment")),
        ("gate_value_projection_output_commitment", gate_input.get("gate_value_projection_output_commitment")),
        ("hidden_activation_commitment", activation_input.get("hidden_activation_commitment")),
    )
    for field, expected in checks:
        if fused_input.get(field) != expected:
            raise FusedGateError(f"fused handoff field drift: {field}")
    if activation_input.get("source_gate_value_projection_output_commitment") != gate_input.get("gate_value_projection_output_commitment"):
        raise FusedGateError("activation source output does not match gate/value output")
    if activation_input.get("gate_projection_q8") != gate_input.get("gate_projection_q8"):
        raise FusedGateError("activation gate vector does not match gate/value output")
    if activation_input.get("value_projection_q8") != gate_input.get("value_projection_q8"):
        raise FusedGateError("activation value vector does not match gate/value output")


def validate_payload(payload: dict[str, Any]) -> None:
    expected_top = {
        "schema", "decision", "result", "route_id", "question", "claim_boundary",
        "first_blocker", "next_research_step", "aggregate", "roles", "grouped_breakdown",
        "grouped_delta_vs_separate_bytes", "mechanism", "non_claims", "validation_commands",
        "evidence", "mutation_inventory", "payload_commitment",
    }
    allowed_top = expected_top | {"mutation_result"}
    if not expected_top.issubset(payload) or not set(payload).issubset(allowed_top):
        raise FusedGateError(f"payload keys drift: {sorted(set(payload) ^ allowed_top)}")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
    }
    for key, expected in constants.items():
        if payload.get(key) != expected:
            raise FusedGateError(f"{key} drift")
    if payload.get("aggregate") != EXPECTED_AGGREGATE:
        raise FusedGateError("aggregate mismatch")
    if payload.get("roles") != EXPECTED_ROLES:
        raise FusedGateError("roles mismatch")
    if payload.get("grouped_breakdown") != EXPECTED_GROUPED:
        raise FusedGateError("grouped breakdown mismatch")
    if payload.get("grouped_delta_vs_separate_bytes") != EXPECTED_GROUPED_DELTA_BYTES:
        raise FusedGateError("grouped delta mismatch")
    if payload.get("mechanism") != list(MECHANISM):
        raise FusedGateError("mechanism mismatch")
    if payload.get("non_claims") != list(NON_CLAIMS):
        raise FusedGateError("non-claims mismatch")
    if payload.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise FusedGateError("validation commands mismatch")
    inventory = require_dict(payload.get("mutation_inventory"), "mutation inventory")
    if inventory.get("case_count") != len(MUTATION_NAMES) or inventory.get("cases") != list(MUTATION_NAMES):
        raise FusedGateError("mutation inventory mismatch")
    if "all_mutations_rejected" in inventory and inventory["all_mutations_rejected"] is not True:
        raise FusedGateError("mutation inventory rejection status mismatch")
    if "mutation_result" in payload:
        result = require_dict(payload["mutation_result"], "mutation result")
        if result.get("case_count") != len(MUTATION_NAMES) or result.get("all_mutations_rejected") is not True:
            raise FusedGateError("mutation result mismatch")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise FusedGateError("payload commitment mismatch")


def mutation_cases(payload: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        ("schema_relabeling", lambda p: p.__setitem__("schema", "v2")),
        ("decision_overclaim", lambda p: p.__setitem__("decision", "BREAKTHROUGH_FULL_BLOCK")),
        ("result_overclaim", lambda p: p.__setitem__("result", "NANOZK_WIN")),
        ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "FULL_D128_BLOCK_PROOF")),
        ("fused_typed_metric_smuggling", lambda p: p["aggregate"].__setitem__("fused_local_typed_bytes", 17_759)),
        ("separate_typed_metric_smuggling", lambda p: p["aggregate"].__setitem__("separate_local_typed_bytes", 23_281)),
        ("typed_saving_metric_smuggling", lambda p: p["aggregate"].__setitem__("typed_saving_vs_separate_bytes", 5_521)),
        ("typed_ratio_metric_smuggling", lambda p: p["aggregate"].__setitem__("typed_ratio_vs_separate", 0.7)),
        ("json_saving_metric_smuggling", lambda p: p["aggregate"].__setitem__("json_saving_vs_separate_bytes", 20_000)),
        ("comparison_status_overclaim", lambda p: p["aggregate"].__setitem__("comparison_status", "matched_nanozk_win")),
        ("grouped_delta_smuggling", lambda p: p["grouped_delta_vs_separate_bytes"].__setitem__("fri_decommitments", -2_559)),
        ("role_backend_version_relabeling", lambda p: p["roles"][FUSED_ENVELOPE_PATH.name].__setitem__("proof_backend_version", "stwo-d128-full-block-v1")),
        ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1])),
        ("mechanism_removed", lambda p: p.__setitem__("mechanism", p["mechanism"][:-1])),
        ("first_blocker_removed", lambda p: p.__setitem__("first_blocker", "")),
        ("validation_command_drift", lambda p: p["validation_commands"].__setitem__(0, "cargo test")),
        ("payload_commitment_relabeling", lambda p: p.__setitem__("payload_commitment", "sha256:" + "00" * 32)),
        ("unknown_field_injection", lambda p: p.__setitem__("unexpected", True)),
    ]


def run_mutations(payload: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for name, mutate in mutation_cases(payload):
        candidate = copy.deepcopy(payload)
        mutate(candidate)
        try:
            validate_payload(candidate)
        except FusedGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": None})
    return {
        "case_count": len(cases),
        "all_mutations_rejected": all(case["rejected"] for case in cases),
        "cases": cases,
    }


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {column: payload["aggregate"].get(column, payload.get(column)) for column in TSV_COLUMNS}
    row["route_id"] = payload["route_id"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args()

    payload = build_payload()
    mutation_result = run_mutations(payload)
    payload["mutation_result"] = mutation_result
    payload["mutation_inventory"] = {
        "case_count": len(MUTATION_NAMES),
        "all_mutations_rejected": mutation_result["all_mutations_rejected"],
        "cases": list(MUTATION_NAMES),
    }
    payload["payload_commitment"] = payload_commitment(payload)
    if not mutation_result["all_mutations_rejected"]:
        raise FusedGateError("not all mutations rejected")
    validate_payload(payload)

    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload)
    if not args.write_json and not args.write_tsv:
        print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
