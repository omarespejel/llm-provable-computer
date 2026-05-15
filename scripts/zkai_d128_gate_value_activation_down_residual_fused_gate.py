#!/usr/bin/env python3
"""Gate the d128 four-component fused native Stwo proof result."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import stat
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

ACCOUNTING_PATH = EVIDENCE_DIR / "zkai-d128-gate-value-activation-down-residual-fused-binary-accounting-2026-05.json"
FUSED_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.envelope.json"
GATE_VALUE_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-gate-value-projection-proof-2026-05.envelope.json"
ACTIVATION_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-activation-swiglu-proof-2026-05.envelope.json"
DOWN_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-down-projection-proof-2026-05.envelope.json"
RESIDUAL_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-residual-add-proof-2026-05.envelope.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-gate-value-activation-down-residual-fused-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-gate-value-activation-down-residual-fused-gate-2026-05.tsv"

SCHEMA = "zkai-d128-gate-value-activation-down-residual-fused-gate-v1"
DECISION = "GO_D128_GATE_VALUE_ACTIVATION_DOWN_RESIDUAL_FUSED_TYPED_PROOF_SAVING"
RESULT = "GO_FOUR_COMPONENT_D128_FUSION_SAVES_24944_TYPED_BYTES"
ROUTE_ID = "native_stwo_d128_gate_value_projection_plus_activation_swiglu_plus_down_projection_plus_residual_add_fused"
CLAIM_BOUNDARY = (
    "FUSED_D128_GATE_VALUE_PLUS_ACTIVATION_PLUS_DOWN_PROJECTION_PLUS_RESIDUAL_ADD_SAVES_TYPED_"
    "PROOF_BYTES_VS_FOUR_SEPARATE_NATIVE_OBJECTS_NOT_A_FULL_TRANSFORMER_BLOCK_NOT_A_NANOZK_BENCHMARK"
)
FIRST_BLOCKER = (
    "The fused proof covers gate/value, activation/SwiGLU, down-projection, and residual-add, "
    "but still does not fuse RMSNorm or attention into the same native block object."
)
NEXT_RESEARCH_STEP = (
    "test whether adding RMSNorm or a lookup-heavy attention sidecar preserves the shared proof-plumbing saving"
)

FUSED_ROLE = "fused_gate_value_activation_down_residual"
GATE_VALUE_ROLE = "separate_gate_value"
ACTIVATION_ROLE = "separate_activation_swiglu"
DOWN_ROLE = "separate_down_projection"
RESIDUAL_ROLE = "separate_residual_add"


def rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


EXPECTED_EVIDENCE = {
    "accounting_json": rel(ACCOUNTING_PATH),
    "fused_envelope": rel(FUSED_ENVELOPE_PATH),
    "gate_value_envelope": rel(GATE_VALUE_ENVELOPE_PATH),
    "activation_envelope": rel(ACTIVATION_ENVELOPE_PATH),
    "down_projection_envelope": rel(DOWN_ENVELOPE_PATH),
    "residual_add_envelope": rel(RESIDUAL_ENVELOPE_PATH),
}

EXPECTED_ROLES = {
    "zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.envelope.json": {
        "role": FUSED_ROLE,
        "proof_backend_version": "stwo-d128-gate-value-activation-down-residual-fused-air-proof-v1",
        "statement_version": "zkai-d128-gate-value-activation-down-residual-fused-statement-v1",
        "proof_json_size_bytes": 67_979,
        "local_typed_bytes": 19_344,
        "envelope_json_size_bytes": 653_007,
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
    "zkai-d128-down-projection-proof-2026-05.envelope.json": {
        "role": DOWN_ROLE,
        "proof_backend_version": "stwo-d128-down-projection-air-proof-v1",
        "statement_version": "zkai-d128-down-projection-statement-v1",
        "proof_json_size_bytes": 58_136,
        "local_typed_bytes": 16_416,
        "envelope_json_size_bytes": 480_007,
    },
    "zkai-d128-residual-add-proof-2026-05.envelope.json": {
        "role": RESIDUAL_ROLE,
        "proof_backend_version": "stwo-d128-residual-add-air-proof-v1",
        "statement_version": "zkai-d128-residual-add-statement-v1",
        "proof_json_size_bytes": 15_980,
        "local_typed_bytes": 4_592,
        "envelope_json_size_bytes": 155_482,
    },
}

EXPECTED_GROUPED = {
    FUSED_ROLE: {
        "fixed_overhead": 48,
        "fri_decommitments": 12_128,
        "fri_samples": 784,
        "oods_samples": 960,
        "queries_values": 720,
        "trace_decommitments": 4_704,
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
    DOWN_ROLE: {
        "fixed_overhead": 48,
        "fri_decommitments": 10_656,
        "fri_samples": 736,
        "oods_samples": 320,
        "queries_values": 240,
        "trace_decommitments": 4_416,
    },
    RESIDUAL_ROLE: {
        "fixed_overhead": 48,
        "fri_decommitments": 1_856,
        "fri_samples": 320,
        "oods_samples": 256,
        "queries_values": 192,
        "trace_decommitments": 1_920,
    },
}

EXPECTED_GROUPED_DELTA_BYTES = {
    "fixed_overhead": -144,
    "fri_decommitments": -14_272,
    "fri_samples": -1_408,
    "oods_samples": -384,
    "queries_values": -288,
    "trace_decommitments": -8_448,
}

EXPECTED_AGGREGATE = {
    "profiles_checked": 1,
    "gate_value_row_count": 131_072,
    "activation_row_count": 512,
    "down_projection_row_count": 65_536,
    "residual_add_row_count": 128,
    "fused_total_row_count": 197_248,
    "separate_proof_json_size_bytes": 156_495,
    "fused_proof_json_size_bytes": 67_979,
    "json_saving_vs_separate_bytes": 88_516,
    "json_saving_ratio_vs_separate": 0.565616,
    "json_ratio_vs_separate": 0.434384,
    "separate_local_typed_bytes": 44_288,
    "fused_local_typed_bytes": 19_344,
    "typed_saving_vs_separate_bytes": 24_944,
    "typed_saving_ratio_vs_separate": 0.563223,
    "typed_ratio_vs_separate": 0.436777,
    "comparison_status": "fused_four_component_native_proof_saves_typed_bytes_vs_separate_objects",
}

MECHANISM = (
    "gate/value, activation/SwiGLU, down-projection, and residual-add are proved as four components inside one native Stwo proof",
    "the fused proof shares one preprocessed tree and one base tree across all four adjacent components",
    "the source handoff is explicit from gate/value outputs to activation inputs and from activation hidden output to down-projection input",
    "the residual-add handoff is explicit from down-projection residual deltas and remainders to residual-add inputs",
    "the saving is dominated by shared FRI and trace Merkle opening/decommitment plumbing",
    "the same publication-v1 PCS profile is used; no verifier query weakening is claimed",
)

NON_CLAIMS = (
    "not a full transformer block with RMSNorm native fusion",
    "not attention plus MLP in one proof object",
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
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_residual_add_proof -- prove docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_residual_fused_proof -- build-input docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_residual_fused_proof -- prove docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_residual_fused_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-binary-accounting-2026-05.json",
    "python3 scripts/zkai_d128_gate_value_activation_down_residual_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_gate_value_activation_down_residual_fused_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_gate_value_activation_fused_proof --lib",
    "git diff --check",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "route_id",
    "fused_total_row_count",
    "residual_add_row_count",
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
    "evidence_path_drift",
    "payload_commitment_relabeling",
    "residual_row_metric_smuggling",
    "residual_role_removed",
    "unknown_field_injection",
)


class FusedResidualGateError(ValueError):
    pass


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        raise FusedResidualGateError("ratio denominator must be non-zero")
    return round(numerator / denominator, 6)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def reject_json_constant(value: str) -> None:
    raise FusedResidualGateError(f"non-finite JSON constant rejected: {value}")


def payload_commitment(payload: dict[str, Any]) -> str:
    canonical = copy.deepcopy(payload)
    canonical.pop("payload_commitment", None)
    return "sha256:" + hashlib.sha256(canonical_bytes(canonical)).hexdigest()


def read_json_with_size(path: pathlib.Path, max_bytes: int, label: str) -> tuple[Any, int]:
    if path.is_symlink():
        raise FusedResidualGateError(f"{label} must not be a symlink: {path}")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise FusedResidualGateError(f"{label} must be a regular file: {path}")
        if st.st_size > max_bytes:
            raise FusedResidualGateError(f"{label} exceeds max size: {st.st_size} > {max_bytes}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(65_536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise FusedResidualGateError(f"{label} exceeds max size while reading")
        raw = b"".join(chunks)
    finally:
        os.close(fd)
    return json.loads(raw.decode("utf-8"), parse_constant=reject_json_constant), len(raw)


def accounting_rows() -> list[dict[str, Any]]:
    accounting, _ = read_json_with_size(ACCOUNTING_PATH, 8_388_608, "binary accounting")
    rows = accounting.get("rows")
    if not isinstance(rows, list):
        raise FusedResidualGateError("accounting rows must be a list")
    return rows


def role_for_row(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    rel_path = row.get("evidence_relative_path")
    if not isinstance(rel_path, str):
        raise FusedResidualGateError("accounting row is missing evidence_relative_path")
    expected = EXPECTED_ROLES.get(rel_path)
    if expected is None:
        raise FusedResidualGateError(f"unexpected evidence row: {rel_path}")
    return expected["role"], expected


def build_payload() -> dict[str, Any]:
    rows = accounting_rows()
    if len(rows) != len(EXPECTED_ROLES):
        raise FusedResidualGateError(f"expected {len(EXPECTED_ROLES)} accounting rows, got {len(rows)}")

    role_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        role, expected = role_for_row(row)
        metadata = row.get("envelope_metadata") or {}
        typed = (row.get("local_binary_accounting") or {}).get("typed_size_estimate_bytes")
        grouped = (row.get("local_binary_accounting") or {}).get("grouped_reconstruction")
        if metadata.get("proof_backend_version") != expected["proof_backend_version"]:
            raise FusedResidualGateError(f"{role} proof backend version drift")
        if metadata.get("statement_version") != expected["statement_version"]:
            raise FusedResidualGateError(f"{role} statement version drift")
        if row.get("proof_json_size_bytes") != expected["proof_json_size_bytes"]:
            raise FusedResidualGateError(f"{role} proof JSON size drift")
        if typed != expected["local_typed_bytes"]:
            raise FusedResidualGateError(f"{role} local typed size drift")
        if grouped != EXPECTED_GROUPED[role]:
            raise FusedResidualGateError(f"{role} grouped typed breakdown drift")
        role_rows[role] = {
            "role": role,
            "path": row["path"],
            "proof_backend_version": metadata["proof_backend_version"],
            "statement_version": metadata["statement_version"],
            "proof_json_size_bytes": row["proof_json_size_bytes"],
            "local_typed_bytes": typed,
            "grouped_typed_bytes": grouped,
            "envelope_sha256": row["envelope_sha256"],
            "proof_sha256": row["proof_sha256"],
        }

    missing = set(EXPECTED_GROUPED) - set(role_rows)
    if missing:
        raise FusedResidualGateError(f"missing expected roles: {sorted(missing)}")

    fused = role_rows[FUSED_ROLE]
    separate_roles = [GATE_VALUE_ROLE, ACTIVATION_ROLE, DOWN_ROLE, RESIDUAL_ROLE]
    separate_json = sum(role_rows[role]["proof_json_size_bytes"] for role in separate_roles)
    separate_typed = sum(role_rows[role]["local_typed_bytes"] for role in separate_roles)
    aggregate = {
        "profiles_checked": 1,
        "gate_value_row_count": 131_072,
        "activation_row_count": 512,
        "down_projection_row_count": 65_536,
        "residual_add_row_count": 128,
        "fused_total_row_count": 197_248,
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
        raise FusedResidualGateError(f"aggregate drift: got {aggregate}, expected {EXPECTED_AGGREGATE}")

    grouped_delta = {}
    for key in EXPECTED_GROUPED[FUSED_ROLE]:
        separate_value = sum(role_rows[role]["grouped_typed_bytes"][key] for role in separate_roles)
        grouped_delta[key] = fused["grouped_typed_bytes"][key] - separate_value
    if grouped_delta != EXPECTED_GROUPED_DELTA_BYTES:
        raise FusedResidualGateError("grouped delta drift")

    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": "Does the adjacent native Stwo fusion saving survive through residual-add?",
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
        "aggregate": aggregate,
        "grouped_delta_bytes": grouped_delta,
        "roles": [role_rows[role] for role in [FUSED_ROLE, *separate_roles]],
        "mechanism": list(MECHANISM),
        "non_claims": list(NON_CLAIMS),
        "evidence_paths": EXPECTED_EVIDENCE,
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_rejections": {},
    }
    payload["payload_commitment"] = payload_commitment(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    allowed = {
        "schema",
        "decision",
        "result",
        "route_id",
        "question",
        "claim_boundary",
        "first_blocker",
        "next_research_step",
        "aggregate",
        "grouped_delta_bytes",
        "roles",
        "mechanism",
        "non_claims",
        "evidence_paths",
        "validation_commands",
        "mutation_rejections",
        "payload_commitment",
    }
    extra = set(payload) - allowed
    if extra:
        raise FusedResidualGateError(f"unknown payload field(s): {sorted(extra)}")
    expected_scalars = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            raise FusedResidualGateError(f"{key} drift")
    if payload.get("aggregate") != EXPECTED_AGGREGATE:
        raise FusedResidualGateError("aggregate drift")
    if payload.get("grouped_delta_bytes") != EXPECTED_GROUPED_DELTA_BYTES:
        raise FusedResidualGateError("grouped delta drift")
    if payload.get("mechanism") != list(MECHANISM):
        raise FusedResidualGateError("mechanism drift")
    if payload.get("non_claims") != list(NON_CLAIMS):
        raise FusedResidualGateError("non-claims drift")
    if payload.get("evidence_paths") != EXPECTED_EVIDENCE:
        raise FusedResidualGateError("evidence path drift")
    if payload.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise FusedResidualGateError("validation command drift")
    role_names = [role.get("role") for role in payload.get("roles", [])]
    if role_names != [FUSED_ROLE, GATE_VALUE_ROLE, ACTIVATION_ROLE, DOWN_ROLE, RESIDUAL_ROLE]:
        raise FusedResidualGateError("role ordering drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise FusedResidualGateError("payload commitment drift")


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if name == "schema_relabeling":
        mutated["schema"] = "wrong"
    elif name == "decision_overclaim":
        mutated["decision"] = "GO_FULL_BLOCK"
    elif name == "result_overclaim":
        mutated["result"] = "GO_NANOZK_WIN"
    elif name == "claim_boundary_overclaim":
        mutated["claim_boundary"] = "FULL_D128_TRANSFORMER_BLOCK_PROOF"
    elif name == "fused_typed_metric_smuggling":
        mutated["aggregate"]["fused_local_typed_bytes"] -= 1
    elif name == "separate_typed_metric_smuggling":
        mutated["aggregate"]["separate_local_typed_bytes"] += 1
    elif name == "typed_saving_metric_smuggling":
        mutated["aggregate"]["typed_saving_vs_separate_bytes"] += 1
    elif name == "typed_ratio_metric_smuggling":
        mutated["aggregate"]["typed_ratio_vs_separate"] = 0.1
    elif name == "json_saving_metric_smuggling":
        mutated["aggregate"]["json_saving_vs_separate_bytes"] += 1
    elif name == "comparison_status_overclaim":
        mutated["aggregate"]["comparison_status"] = "beats_nanozk"
    elif name == "grouped_delta_smuggling":
        mutated["grouped_delta_bytes"]["fri_decommitments"] += 1
    elif name == "role_backend_version_relabeling":
        mutated["roles"][0]["proof_backend_version"] = "wrong"
    elif name == "non_claim_removed":
        mutated["non_claims"].pop()
    elif name == "mechanism_removed":
        mutated["mechanism"].pop()
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "validation_command_drift":
        mutated["validation_commands"][0] = "true"
    elif name == "evidence_path_drift":
        mutated["evidence_paths"]["fused_envelope"] = "wrong.json"
    elif name == "payload_commitment_relabeling":
        mutated["payload_commitment"] = "sha256:" + "00" * 32
    elif name == "residual_row_metric_smuggling":
        mutated["aggregate"]["residual_add_row_count"] = 0
    elif name == "residual_role_removed":
        mutated["roles"].pop()
    elif name == "unknown_field_injection":
        mutated["unexpected"] = True
    else:
        raise AssertionError(f"unhandled mutation: {name}")
    return mutated


def run_mutations(payload: dict[str, Any]) -> dict[str, str]:
    results: dict[str, str] = {}
    for name in MUTATION_NAMES:
        try:
            validate_payload(mutate_payload(payload, name))
        except FusedResidualGateError:
            results[name] = "rejected"
        else:
            raise FusedResidualGateError(f"mutation was accepted: {name}")
    return results


def assert_output_path(path: pathlib.Path) -> pathlib.Path:
    parent = path.parent if path.parent != pathlib.Path("") else pathlib.Path(".")
    if path.exists() and path.is_symlink():
        raise FusedResidualGateError(f"output path must not be a symlink: {path}")
    resolved_parent = parent.resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    try:
        resolved_parent.relative_to(evidence_root)
    except ValueError as exc:
        raise FusedResidualGateError(f"output parent escapes evidence dir: {path}") from exc
    return resolved_parent


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    parent = assert_output_path(path)
    parent.mkdir(parents=True, exist_ok=True)
    tmp = parent / f".{path.name}.{os.getpid()}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, 0o644)
    try:
        written = 0
        while written < len(data):
            written += os.write(fd, data[written:])
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink()
        finally:
            raise


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    row = {column: payload["aggregate"].get(column, payload.get(column)) for column in TSV_COLUMNS}
    row["route_id"] = payload["route_id"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    atomic_write(path, out.getvalue().encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()

    payload = build_payload()
    validate_payload(payload)
    payload["mutation_rejections"] = run_mutations(payload)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload)

    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload)
    print(json.dumps(payload["aggregate"], sort_keys=True, allow_nan=False))
    print(f"mutations_rejected={len(payload['mutation_rejections'])}/{len(MUTATION_NAMES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
