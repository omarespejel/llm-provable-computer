#!/usr/bin/env python3
"""Quantify whether PCS lifting overhead explains the single-proof gap."""

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
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

SINGLE_ACCOUNTING_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json"
BOUNDARY_ACCOUNTING_PATH = EVIDENCE_DIR / "zkai-d128-attention-mlp-boundary-frontier-accounting-2026-05.json"
SINGLE_GATE_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-2026-05.json"
BOUNDARY_GATE_PATH = EVIDENCE_DIR / "zkai-d128-attention-mlp-boundary-frontier-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-lifting-ablation-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-lifting-ablation-2026-05.tsv"

SCHEMA = "zkai-native-attention-mlp-lifting-ablation-gate-v1"
DECISION = "NO_GO_LIFTING_ONLY_BREAKTHROUGH_FOR_NATIVE_ATTENTION_MLP_SINGLE_PROOF"
RESULT = "NARROW_CLAIM_FRI_DECOMMITMENT_OVERHANG_IS_REAL_BUT_TOO_SMALL"
ROUTE_ID = "native_attention_mlp_single_proof_pcs_lifting_ablation_v1"
QUESTION = (
    "Does the heterogeneous-tree PCS lifting overhang explain why the first native "
    "attention-plus-MLP single proof barely beats the two-proof frontier?"
)
CLAIM_BOUNDARY = (
    "ABLATES_TYPED_PROOF_FIELD_GROUPS_FOR_THE_CHECKED_SINGLE_PROOF_OBJECT_"
    "WITHOUT_REGENERATING_A_PROOF_OR_CLAIMING_NANOZK_COMPARABILITY"
)
FIRST_BLOCKER = (
    "Removing the whole positive FRI-decommitment overhang would still leave a "
    "40,028 typed-byte projected object, 33,128 bytes above NANOZK's paper-reported row."
)
NEXT_RESEARCH_STEP = (
    "attack native adapter AIR, query-value reduction, or a stronger component boundary; "
    "do not spend the next slice only shaving PCS lifting overhead"
)

GROUP_KEYS = (
    "fixed_overhead",
    "fri_decommitments",
    "fri_samples",
    "oods_samples",
    "queries_values",
    "trace_decommitments",
)

SINGLE_RELATIVE_PATH = "zkai-native-attention-mlp-single-proof-2026-05.envelope.json"
ATTENTION_RELATIVE_PATH = "zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json"
MLP_RELATIVE_PATH = "zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json"

NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900

EXPECTED_ROWS = {
    SINGLE_RELATIVE_PATH: {
        "role": "single_native_attention_mlp",
        "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-probe-v1",
        "statement_version": "zkai-native-attention-mlp-single-proof-object-statement-v1",
        "proof_json_size_bytes": 115_924,
        "local_typed_bytes": 40_668,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 12_736,
            "fri_samples": 784,
            "oods_samples": 11_856,
            "queries_values": 8_844,
            "trace_decommitments": 6_400,
        },
    },
    ATTENTION_RELATIVE_PATH: {
        "role": "two_proof_attention_fused",
        "proof_backend_version": "stwo-attention-kv-d8-fused-bounded-softmax-table-logup-v1",
        "statement_version": "zkai-attention-kv-stwo-native-d8-fused-softmax-table-logup-statement-v1",
        "proof_json_size_bytes": 47_698,
        "local_typed_bytes": 18_124,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 1_312,
            "fri_samples": 272,
            "oods_samples": 8_208,
            "queries_values": 6_108,
            "trace_decommitments": 2_176,
        },
    },
    MLP_RELATIVE_PATH: {
        "role": "two_proof_derived_mlp_fused",
        "proof_backend_version": "stwo-d128-rmsnorm-mlp-fused-air-proof-v1",
        "statement_version": "zkai-d128-rmsnorm-mlp-fused-statement-v1",
        "proof_json_size_bytes": 68_560,
        "local_typed_bytes": 22_576,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 10_784,
            "fri_samples": 720,
            "oods_samples": 3_776,
            "queries_values": 2_832,
            "trace_decommitments": 4_416,
        },
    },
}

EXPECTED_TWO_PROOF_GROUPED = {
    "fixed_overhead": 96,
    "fri_decommitments": 12_096,
    "fri_samples": 992,
    "oods_samples": 11_984,
    "queries_values": 8_940,
    "trace_decommitments": 6_592,
}

EXPECTED_GROUP_DELTAS = {
    "fixed_overhead": {
        "single_typed_bytes": 48,
        "two_proof_typed_bytes": 96,
        "single_minus_two_proof_delta_bytes": -48,
    },
    "fri_decommitments": {
        "single_typed_bytes": 12_736,
        "two_proof_typed_bytes": 12_096,
        "single_minus_two_proof_delta_bytes": 640,
    },
    "fri_samples": {
        "single_typed_bytes": 784,
        "two_proof_typed_bytes": 992,
        "single_minus_two_proof_delta_bytes": -208,
    },
    "oods_samples": {
        "single_typed_bytes": 11_856,
        "two_proof_typed_bytes": 11_984,
        "single_minus_two_proof_delta_bytes": -128,
    },
    "queries_values": {
        "single_typed_bytes": 8_844,
        "two_proof_typed_bytes": 8_940,
        "single_minus_two_proof_delta_bytes": -96,
    },
    "trace_decommitments": {
        "single_typed_bytes": 6_400,
        "two_proof_typed_bytes": 6_592,
        "single_minus_two_proof_delta_bytes": -192,
    },
}

EXPECTED_SUMMARY = {
    "single_proof_typed_bytes": 40_668,
    "two_proof_frontier_typed_bytes": 40_700,
    "current_typed_saving_vs_two_proof_bytes": 32,
    "current_typed_ratio_vs_two_proof": 0.999214,
    "positive_overhang_group": "fri_decommitments",
    "fri_decommitment_overhang_bytes": 640,
    "negative_delta_bytes": -672,
    "projected_typed_bytes_without_fri_overhang": 40_028,
    "projected_saving_vs_two_proof_bytes": 672,
    "projected_saving_vs_two_proof_share": 0.016511,
    "projected_ratio_vs_two_proof": 0.983489,
    "nanozk_reported_d128_block_proof_bytes": 6_900,
    "current_gap_to_nanozk_reported_bytes": 33_768,
    "current_reduction_needed_to_nanozk_share": 0.830333,
    "projected_gap_to_nanozk_reported_bytes": 33_128,
    "projected_reduction_needed_to_nanozk_share": 0.827621,
    "projected_ratio_vs_nanozk_reported": 5.801159,
    "lifting_only_breakthrough_status": "NO_GO",
    "next_attack": "native_adapter_air_or_query_value_reduction_or_boundary_restructure",
}

MECHANISM = (
    "the one-proof object saves fixed overhead, FRI samples, OODS samples, query values, and trace decommitments",
    "the only positive typed-field delta versus the two-proof frontier is FRI decommitments",
    "that positive delta is 640 typed bytes and is consistent with the heterogeneous-tree lifting cost",
    "removing all 640 bytes would improve the object, but only to 40,028 typed bytes",
    "40,028 typed bytes is still 5.801159x NANOZK's paper-reported 6,900 byte d128 row",
    "therefore the next serious attack must change the proved surface or query/opening economics, not only the lifting knob",
)

NON_CLAIMS = (
    "not a regenerated proof after removing lifting overhead",
    "not proof that the 640 bytes are removable without verifier changes",
    "not a NANOZK proof-size win",
    "not a matched NANOZK workload or benchmark",
    "not native AIR proof of the attention-output-to-d128-input adapter",
    "not a full transformer block proof",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_native_attention_mlp_lifting_ablation_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_attention_mlp_lifting_ablation_gate.py scripts/tests/test_zkai_native_attention_mlp_lifting_ablation_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_lifting_ablation_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
)

EXPECTED_EVIDENCE = {
    "single_accounting_json": "docs/engineering/evidence/zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json",
    "boundary_accounting_json": "docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-accounting-2026-05.json",
    "single_gate_json": "docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.json",
    "boundary_gate_json": "docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-2026-05.json",
    "ablation_json": "docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.json",
    "ablation_tsv": "docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.tsv",
}

TSV_COLUMNS = (
    "decision",
    "result",
    "single_proof_typed_bytes",
    "two_proof_frontier_typed_bytes",
    "current_typed_saving_vs_two_proof_bytes",
    "positive_overhang_group",
    "fri_decommitment_overhang_bytes",
    "projected_typed_bytes_without_fri_overhang",
    "projected_saving_vs_two_proof_bytes",
    "projected_gap_to_nanozk_reported_bytes",
    "projected_reduction_needed_to_nanozk_share",
    "lifting_only_breakthrough_status",
    "next_attack",
)

MUTATION_NAMES = (
    "schema_relabeling",
    "decision_overclaim",
    "result_overclaim",
    "claim_boundary_overclaim",
    "single_typed_metric_smuggling",
    "two_proof_metric_smuggling",
    "fri_overhang_metric_smuggling",
    "projected_metric_smuggling",
    "nanozk_gap_smuggling",
    "status_overclaim",
    "next_attack_erased",
    "group_delta_relabeling",
    "mechanism_removed",
    "non_claim_removed",
    "validation_command_drift",
    "evidence_path_drift",
    "source_artifact_hash_drift",
    "payload_commitment_relabeling",
    "unknown_field_injection",
)


class LiftingAblationError(ValueError):
    pass


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        raise LiftingAblationError("ratio denominator must be non-zero")
    return round(numerator / denominator, 6)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def reject_json_constant(value: str) -> None:
    raise LiftingAblationError(f"non-finite JSON constant rejected: {value}")


def payload_commitment(payload: dict[str, Any]) -> str:
    canonical = copy.deepcopy(payload)
    canonical.pop("payload_commitment", None)
    return "sha256:" + hashlib.sha256(canonical_bytes(canonical)).hexdigest()


def read_json_with_size(path: pathlib.Path, max_bytes: int, label: str) -> tuple[Any, int, bytes]:
    if path.is_symlink():
        raise LiftingAblationError(f"{label} must not be a symlink: {path}")
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise LiftingAblationError(f"{label} escapes evidence directory: {path}") from err
    try:
        pre = resolved.lstat()
    except OSError as err:
        raise LiftingAblationError(f"failed to stat {label}: {err}") from err
    if not stat.S_ISREG(pre.st_mode):
        raise LiftingAblationError(f"{label} is not a regular file: {path}")
    try:
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as err:
        raise LiftingAblationError(f"failed to open {label}: {err}") from err
    try:
        post = os.fstat(fd)
        if (pre.st_dev, pre.st_ino) != (post.st_dev, post.st_ino):
            raise LiftingAblationError(f"{label} changed while opening: {path}")
        if post.st_size > max_bytes:
            raise LiftingAblationError(f"{label} exceeds max size: got {post.st_size} bytes")
        chunks: list[bytes] = []
        total = 0
        while total < post.st_size:
            chunk = os.read(fd, min(65_536, int(post.st_size) - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise LiftingAblationError(f"{label} exceeds max size while reading")
        raw = b"".join(chunks)
        after = os.fstat(fd)
        if (post.st_dev, post.st_ino, post.st_size) != (after.st_dev, after.st_ino, after.st_size):
            raise LiftingAblationError(f"{label} changed while reading: {path}")
    finally:
        if fd is not None:
            os.close(fd)
    if len(raw) > max_bytes:
        raise LiftingAblationError(f"{label} exceeds max size: got at least {len(raw)} bytes")
    if len(raw) != post.st_size:
        raise LiftingAblationError(f"{label} changed while reading: {path}")
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=reject_json_constant), int(post.st_size), raw
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise LiftingAblationError(f"{label} is not JSON: {err}") from err


def read_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    payload, _size, _raw = read_json_with_size(path, max_bytes, label)
    return payload


def sha256_file(path: pathlib.Path, max_bytes: int, label: str) -> tuple[str, int]:
    _payload, size, raw = read_json_with_size(path, max_bytes, label)
    return hashlib.sha256(raw).hexdigest(), size


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LiftingAblationError(f"{label} must be object")
    return value


def rows_by_path(accounting: dict[str, Any], expected_paths: set[str], label: str) -> dict[str, dict[str, Any]]:
    rows = accounting.get("rows")
    if not isinstance(rows, list):
        raise LiftingAblationError(f"{label} rows must be a list")
    result: dict[str, dict[str, Any]] = {}
    for raw_row in rows:
        row = require_dict(raw_row, f"{label} row")
        relative = row.get("evidence_relative_path")
        if relative in expected_paths:
            result[str(relative)] = row
    if set(result) != expected_paths:
        raise LiftingAblationError(f"{label} expected paths missing: {sorted(expected_paths - set(result))}")
    return result


def validate_accounting_row(row: dict[str, Any], expected: dict[str, Any]) -> None:
    metadata = require_dict(row.get("envelope_metadata"), "row envelope metadata")
    for field in ("proof_backend_version", "statement_version"):
        if metadata.get(field) != expected[field]:
            raise LiftingAblationError(f"{expected['role']} {field} drift")
    if row.get("proof_json_size_bytes") != expected["proof_json_size_bytes"]:
        raise LiftingAblationError(f"{expected['role']} proof JSON byte drift")
    accounting = require_dict(row.get("local_binary_accounting"), "local binary accounting")
    if accounting.get("typed_size_estimate_bytes") != expected["local_typed_bytes"]:
        raise LiftingAblationError(f"{expected['role']} typed byte drift")
    grouped = require_dict(accounting.get("grouped_reconstruction"), "grouped reconstruction")
    if grouped != expected["grouped"]:
        raise LiftingAblationError(f"{expected['role']} grouped reconstruction drift")


def two_proof_grouped() -> dict[str, int]:
    grouped = {
        key: int(EXPECTED_ROWS[ATTENTION_RELATIVE_PATH]["grouped"][key])
        + int(EXPECTED_ROWS[MLP_RELATIVE_PATH]["grouped"][key])
        for key in GROUP_KEYS
    }
    if grouped != EXPECTED_TWO_PROOF_GROUPED:
        raise LiftingAblationError("two-proof grouped reconstruction drift")
    return grouped


def group_deltas() -> dict[str, dict[str, int]]:
    single = EXPECTED_ROWS[SINGLE_RELATIVE_PATH]["grouped"]
    two = two_proof_grouped()
    result = {
        key: {
            "single_typed_bytes": int(single[key]),
            "two_proof_typed_bytes": int(two[key]),
            "single_minus_two_proof_delta_bytes": int(single[key]) - int(two[key]),
        }
        for key in GROUP_KEYS
    }
    if result != EXPECTED_GROUP_DELTAS:
        raise LiftingAblationError("group delta drift")
    return result


def summary_from_groups(groups: dict[str, dict[str, int]]) -> dict[str, Any]:
    positive = [(name, values["single_minus_two_proof_delta_bytes"]) for name, values in groups.items() if values["single_minus_two_proof_delta_bytes"] > 0]
    if positive != [("fri_decommitments", 640)]:
        raise LiftingAblationError("positive overhang drift")
    negative_delta = sum(values["single_minus_two_proof_delta_bytes"] for values in groups.values() if values["single_minus_two_proof_delta_bytes"] < 0)
    single_typed = EXPECTED_ROWS[SINGLE_RELATIVE_PATH]["local_typed_bytes"]
    two_typed = EXPECTED_ROWS[ATTENTION_RELATIVE_PATH]["local_typed_bytes"] + EXPECTED_ROWS[MLP_RELATIVE_PATH]["local_typed_bytes"]
    projected = int(single_typed) - positive[0][1]
    summary = {
        "single_proof_typed_bytes": single_typed,
        "two_proof_frontier_typed_bytes": two_typed,
        "current_typed_saving_vs_two_proof_bytes": int(two_typed) - int(single_typed),
        "current_typed_ratio_vs_two_proof": rounded_ratio(int(single_typed), int(two_typed)),
        "positive_overhang_group": positive[0][0],
        "fri_decommitment_overhang_bytes": positive[0][1],
        "negative_delta_bytes": negative_delta,
        "projected_typed_bytes_without_fri_overhang": projected,
        "projected_saving_vs_two_proof_bytes": int(two_typed) - projected,
        "projected_saving_vs_two_proof_share": rounded_ratio(int(two_typed) - projected, int(two_typed)),
        "projected_ratio_vs_two_proof": rounded_ratio(projected, int(two_typed)),
        "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "current_gap_to_nanozk_reported_bytes": int(single_typed) - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "current_reduction_needed_to_nanozk_share": rounded_ratio(int(single_typed) - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES, int(single_typed)),
        "projected_gap_to_nanozk_reported_bytes": projected - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "projected_reduction_needed_to_nanozk_share": rounded_ratio(projected - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES, projected),
        "projected_ratio_vs_nanozk_reported": rounded_ratio(projected, NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES),
        "lifting_only_breakthrough_status": "NO_GO",
        "next_attack": "native_adapter_air_or_query_value_reduction_or_boundary_restructure",
    }
    if summary != EXPECTED_SUMMARY:
        raise LiftingAblationError("summary drift")
    return summary


def validate_single_gate(single_gate: dict[str, Any]) -> None:
    if single_gate.get("decision") != "GO_NATIVE_ATTENTION_MLP_SINGLE_STWO_PROOF_OBJECT_VERIFIES":
        raise LiftingAblationError("single gate decision drift")
    if single_gate.get("result") != "NARROW_CLAIM_SINGLE_PROOF_OBJECT_BARELY_BEATS_TWO_PROOF_FRONTIER":
        raise LiftingAblationError("single gate result drift")
    summary = require_dict(single_gate.get("summary"), "single gate summary")
    for key in (
        "single_proof_typed_bytes",
        "two_proof_frontier_typed_bytes",
        "typed_saving_vs_two_proof_bytes",
        "typed_gap_to_nanozk_reported_bytes",
        "typed_reduction_needed_to_nanozk_reported_share",
        "pcs_lifting_log_size",
    ):
        expected = {
            "single_proof_typed_bytes": 40_668,
            "two_proof_frontier_typed_bytes": 40_700,
            "typed_saving_vs_two_proof_bytes": 32,
            "typed_gap_to_nanozk_reported_bytes": 33_768,
            "typed_reduction_needed_to_nanozk_reported_share": 0.830333,
            "pcs_lifting_log_size": 19,
        }[key]
        if summary.get(key) != expected:
            raise LiftingAblationError(f"single gate {key} drift")


def validate_boundary_gate(boundary_gate: dict[str, Any]) -> None:
    if boundary_gate.get("decision") != "NARROW_CLAIM_ATTENTION_PLUS_DERIVED_MLP_BOUNDARY_FRONTIER_PINNED":
        raise LiftingAblationError("boundary gate decision drift")
    summary = require_dict(boundary_gate.get("summary"), "boundary gate summary")
    expected = {
        "attention_fused_typed_bytes": 18_124,
        "derived_mlp_fused_typed_bytes": 22_576,
        "two_proof_frontier_typed_bytes": 40_700,
        "two_proof_frontier_json_proof_bytes": 116_258,
        "typed_gap_to_nanozk_reported_bytes": 33_800,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise LiftingAblationError(f"boundary gate {key} drift")


def source_artifacts() -> list[dict[str, str | int]]:
    specs = (
        (SINGLE_ACCOUNTING_PATH, 16 * 1024 * 1024, "single accounting JSON"),
        (BOUNDARY_ACCOUNTING_PATH, 16 * 1024 * 1024, "boundary accounting JSON"),
        (SINGLE_GATE_PATH, 4 * 1024 * 1024, "single gate JSON"),
        (BOUNDARY_GATE_PATH, 4 * 1024 * 1024, "boundary gate JSON"),
    )
    artifacts: list[dict[str, str | int]] = []
    for path, max_bytes, label in specs:
        digest, size = sha256_file(path, max_bytes, label)
        artifacts.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "size_bytes": size,
            }
        )
    return artifacts


def build_payload() -> dict[str, Any]:
    single_accounting = require_dict(read_json(SINGLE_ACCOUNTING_PATH, 16 * 1024 * 1024, "single accounting JSON"), "single accounting JSON")
    boundary_accounting = require_dict(read_json(BOUNDARY_ACCOUNTING_PATH, 16 * 1024 * 1024, "boundary accounting JSON"), "boundary accounting JSON")
    single_gate = require_dict(read_json(SINGLE_GATE_PATH, 4 * 1024 * 1024, "single gate JSON"), "single gate JSON")
    boundary_gate = require_dict(read_json(BOUNDARY_GATE_PATH, 4 * 1024 * 1024, "boundary gate JSON"), "boundary gate JSON")

    validate_single_gate(single_gate)
    validate_boundary_gate(boundary_gate)

    single_rows = rows_by_path(single_accounting, {SINGLE_RELATIVE_PATH}, "single accounting")
    boundary_rows = rows_by_path(boundary_accounting, {ATTENTION_RELATIVE_PATH, MLP_RELATIVE_PATH}, "boundary accounting")
    validate_accounting_row(single_rows[SINGLE_RELATIVE_PATH], EXPECTED_ROWS[SINGLE_RELATIVE_PATH])
    validate_accounting_row(boundary_rows[ATTENTION_RELATIVE_PATH], EXPECTED_ROWS[ATTENTION_RELATIVE_PATH])
    validate_accounting_row(boundary_rows[MLP_RELATIVE_PATH], EXPECTED_ROWS[MLP_RELATIVE_PATH])

    groups = group_deltas()
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
        "summary": summary_from_groups(groups),
        "component_rows": copy.deepcopy(EXPECTED_ROWS),
        "two_proof_grouped": two_proof_grouped(),
        "group_deltas": groups,
        "mechanism": list(MECHANISM),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "evidence": copy.deepcopy(EXPECTED_EVIDENCE),
        "source_artifacts": source_artifacts(),
        "mutation_inventory": {
            "case_count": len(MUTATION_NAMES),
            "cases": list(MUTATION_NAMES),
        },
    }
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    expected_top = {
        "schema",
        "decision",
        "result",
        "route_id",
        "question",
        "claim_boundary",
        "first_blocker",
        "next_research_step",
        "summary",
        "component_rows",
        "two_proof_grouped",
        "group_deltas",
        "mechanism",
        "non_claims",
        "validation_commands",
        "evidence",
        "source_artifacts",
        "mutation_inventory",
        "payload_commitment",
    }
    allowed_top = expected_top | {"mutation_result"}
    if not expected_top.issubset(payload) or not set(payload).issubset(allowed_top):
        raise LiftingAblationError(f"payload keys drift: {sorted(set(payload) ^ allowed_top)}")
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
            raise LiftingAblationError(f"{key} drift")
    if payload.get("summary") != EXPECTED_SUMMARY:
        raise LiftingAblationError("summary mismatch")
    if payload.get("component_rows") != EXPECTED_ROWS:
        raise LiftingAblationError("component rows mismatch")
    if payload.get("two_proof_grouped") != EXPECTED_TWO_PROOF_GROUPED:
        raise LiftingAblationError("two-proof grouped mismatch")
    if payload.get("group_deltas") != EXPECTED_GROUP_DELTAS:
        raise LiftingAblationError("group deltas mismatch")
    if payload.get("mechanism") != list(MECHANISM):
        raise LiftingAblationError("mechanism mismatch")
    if payload.get("non_claims") != list(NON_CLAIMS):
        raise LiftingAblationError("non-claims mismatch")
    if payload.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise LiftingAblationError("validation commands mismatch")
    if payload.get("evidence") != EXPECTED_EVIDENCE:
        raise LiftingAblationError("evidence mismatch")
    if payload.get("source_artifacts") != source_artifacts():
        raise LiftingAblationError("source artifact hashes mismatch")
    inventory = require_dict(payload.get("mutation_inventory"), "mutation inventory")
    if inventory.get("case_count") != len(MUTATION_NAMES) or inventory.get("cases") != list(MUTATION_NAMES):
        raise LiftingAblationError("mutation inventory mismatch")
    if "all_mutations_rejected" in inventory and inventory["all_mutations_rejected"] is not True:
        raise LiftingAblationError("mutation inventory rejection status mismatch")
    if "mutation_result" in payload:
        result = require_dict(payload["mutation_result"], "mutation result")
        if result.get("case_count") != len(MUTATION_NAMES) or result.get("all_mutations_rejected") is not True:
            raise LiftingAblationError("mutation result mismatch")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise LiftingAblationError("payload commitment mismatch")


def mutation_cases() -> list[tuple[str, Callable[[dict[str, Any]], None]]]:
    return [
        ("schema_relabeling", lambda p: p.__setitem__("schema", "v2")),
        ("decision_overclaim", lambda p: p.__setitem__("decision", "GO_LIFTING_BREAKTHROUGH")),
        ("result_overclaim", lambda p: p.__setitem__("result", "GO_LIFTING_REMOVAL_MATCHES_NANOZK")),
        ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "MATCHED_NANOZK_PROOF_SIZE_WIN")),
        ("single_typed_metric_smuggling", lambda p: p["summary"].__setitem__("single_proof_typed_bytes", 40_000)),
        ("two_proof_metric_smuggling", lambda p: p["summary"].__setitem__("two_proof_frontier_typed_bytes", 41_000)),
        ("fri_overhang_metric_smuggling", lambda p: p["summary"].__setitem__("fri_decommitment_overhang_bytes", 1_024)),
        ("projected_metric_smuggling", lambda p: p["summary"].__setitem__("projected_typed_bytes_without_fri_overhang", 6_900)),
        ("nanozk_gap_smuggling", lambda p: p["summary"].__setitem__("projected_gap_to_nanozk_reported_bytes", 0)),
        ("status_overclaim", lambda p: p["summary"].__setitem__("lifting_only_breakthrough_status", "GO")),
        ("next_attack_erased", lambda p: p["summary"].__setitem__("next_attack", "none")),
        ("group_delta_relabeling", lambda p: p["group_deltas"]["fri_decommitments"].__setitem__("single_minus_two_proof_delta_bytes", -640)),
        ("mechanism_removed", lambda p: p.__setitem__("mechanism", p["mechanism"][:-1])),
        ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1])),
        ("validation_command_drift", lambda p: p["validation_commands"].__setitem__(0, "python3 fake.py")),
        ("evidence_path_drift", lambda p: p["evidence"].__setitem__("ablation_json", "docs/engineering/evidence/other.json")),
        ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "0" * 64)),
        ("payload_commitment_relabeling", lambda p: p.__setitem__("payload_commitment", "sha256:" + "00" * 32)),
        ("unknown_field_injection", lambda p: p.__setitem__("unexpected", True)),
    ]


def run_mutations(payload: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for name, mutate in mutation_cases():
        candidate = copy.deepcopy(payload)
        mutate(candidate)
        try:
            validate_payload(candidate)
        except LiftingAblationError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": None})
    return {
        "case_count": len(cases),
        "all_mutations_rejected": all(case["rejected"] for case in cases),
        "cases": cases,
    }


def resolve_evidence_output_path(path: pathlib.Path, label: str) -> pathlib.Path:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise LiftingAblationError(f"{label} output must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise LiftingAblationError(f"{label} output escapes evidence directory: {path}") from err
    parent = resolved.parent
    try:
        parent_stat = parent.lstat()
    except OSError as err:
        raise LiftingAblationError(f"{label} output parent must already exist: {err}") from err
    if parent.is_symlink() or not stat.S_ISDIR(parent_stat.st_mode):
        raise LiftingAblationError(f"{label} output parent is not a regular directory: {parent}")
    try:
        existing = resolved.lstat()
    except FileNotFoundError:
        return resolved
    except OSError as err:
        raise LiftingAblationError(f"failed to stat {label} output: {err}") from err
    if not stat.S_ISREG(existing.st_mode):
        raise LiftingAblationError(f"{label} output is not a regular file: {path}")
    return resolved


def write_bytes_atomic(path: pathlib.Path, data: bytes, label: str) -> None:
    resolved = resolve_evidence_output_path(path, label)
    tmp = resolved.parent / f".{resolved.name}.{os.getpid()}.tmp"
    fd: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(tmp, flags, 0o600)
        total_written = 0
        while total_written < len(data):
            total_written += os.write(fd, data[total_written:])
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.replace(tmp, resolved)
    except OSError as err:
        raise LiftingAblationError(f"failed to atomically write {label}: {err}") from err
    finally:
        if fd is not None:
            os.close(fd)
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    write_bytes_atomic(path, data, "lifting ablation JSON")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    row = {column: payload["summary"].get(column, payload.get(column)) for column in TSV_COLUMNS}
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
    write_bytes_atomic(path, handle.getvalue().encode("utf-8"), "lifting ablation TSV")


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
        raise LiftingAblationError("not all mutations rejected")
    validate_payload(payload)

    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload)
    if not args.write_json and not args.write_tsv:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
