#!/usr/bin/env python3
"""Attribute the exact derived d128 RMSNorm-MLP fusion saving."""

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
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

ACCOUNTING_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json"
ROUTE_GATE_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.tsv"

SCHEMA = "zkai-attention-derived-d128-mlp-fusion-attribution-gate-v1"
DECISION = "NARROW_CLAIM_EXACT_DERIVED_MLP_FUSION_SAVING_IS_SHARED_OPENING_PLUMBING"
RESULT = "NO_GO_SAFE_INTERNAL_COMPRESSION_BEFORE_NEW_ATTENTION_PLUS_MLP_OBJECT"
ROUTE_ID = "attention_derived_d128_rmsnorm_mlp_exact_six_envelope_fusion_attribution"
QUESTION = (
    "Is the exact six-envelope derived d128 RMSNorm-MLP fusion saving mostly removable internal "
    "fat, or mostly verifier-required STARK opening/decommitment plumbing?"
)
CLAIM_BOUNDARY = (
    "ATTRIBUTES_EXACT_DERIVED_D128_MLP_SIDE_FUSION_SAVING_TO_TYPED_STWO_PROOF_FIELDS_"
    "NOT_A_NEW_PROOF_OBJECT_NOT_A_NANOZK_BENCHMARK"
)
FIRST_BLOCKER = (
    "The largest saved buckets are verifier opening/decommitment witnesses; reducing them safely "
    "requires a new shared native proof object boundary, with attention-plus-MLP as the next frontier."
)
NEXT_RESEARCH_STEP = (
    "attempt a value-connected attention-plus-RMSNorm-MLP native proof object, or record a typed "
    "handoff boundary if attention should stay separate"
)

FUSED_ROLE = "fused_rmsnorm_mlp"
SEPARATE_ROLES = (
    "separate_rmsnorm_public_rows",
    "separate_rmsnorm_projection_bridge",
    "separate_gate_value_projection",
    "separate_activation_swiglu",
    "separate_down_projection",
    "separate_residual_add",
)
GROUP_KEYS = (
    "fixed_overhead",
    "fri_decommitments",
    "fri_samples",
    "oods_samples",
    "queries_values",
    "trace_decommitments",
)

EXPECTED_ROWS = {
    "zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json": {
        "role": FUSED_ROLE,
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
    "zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json": {
        "role": "separate_rmsnorm_public_rows",
        "proof_backend_version": "stwo-d128-rmsnorm-public-row-air-proof-v3",
        "statement_version": "zkai-d128-rmsnorm-public-row-statement-v2",
        "proof_json_size_bytes": 21_632,
        "local_typed_bytes": 9_128,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 1_856,
            "fri_samples": 320,
            "oods_samples": 2_848,
            "queries_values": 2_136,
            "trace_decommitments": 1_920,
        },
    },
    "zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json": {
        "role": "separate_rmsnorm_projection_bridge",
        "proof_backend_version": "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1",
        "statement_version": "zkai-d128-rmsnorm-to-projection-bridge-statement-v1",
        "proof_json_size_bytes": 14_006,
        "local_typed_bytes": 4_008,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 1_568,
            "fri_samples": 272,
            "oods_samples": 224,
            "queries_values": 168,
            "trace_decommitments": 1_728,
        },
    },
    "zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json": {
        "role": "separate_gate_value_projection",
        "proof_backend_version": "stwo-d128-gate-value-projection-air-proof-v1",
        "statement_version": "zkai-d128-gate-value-projection-statement-v1",
        "proof_json_size_bytes": 64_651,
        "local_typed_bytes": 18_280,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 12_128,
            "fri_samples": 784,
            "oods_samples": 352,
            "queries_values": 264,
            "trace_decommitments": 4_704,
        },
    },
    "zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json": {
        "role": "separate_activation_swiglu",
        "proof_backend_version": "stwo-d128-activation-swiglu-air-proof-v1",
        "statement_version": "zkai-d128-activation-swiglu-statement-v1",
        "proof_json_size_bytes": 24_455,
        "local_typed_bytes": 6_920,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 3_232,
            "fri_samples": 416,
            "oods_samples": 416,
            "queries_values": 312,
            "trace_decommitments": 2_496,
        },
    },
    "zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json": {
        "role": "separate_down_projection",
        "proof_backend_version": "stwo-d128-down-projection-air-proof-v1",
        "statement_version": "zkai-d128-down-projection-statement-v1",
        "proof_json_size_bytes": 58_151,
        "local_typed_bytes": 16_416,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 10_656,
            "fri_samples": 736,
            "oods_samples": 320,
            "queries_values": 240,
            "trace_decommitments": 4_416,
        },
    },
    "zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json": {
        "role": "separate_residual_add",
        "proof_backend_version": "stwo-d128-residual-add-air-proof-v1",
        "statement_version": "zkai-d128-residual-add-statement-v1",
        "proof_json_size_bytes": 16_042,
        "local_typed_bytes": 4_592,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 1_856,
            "fri_samples": 320,
            "oods_samples": 256,
            "queries_values": 192,
            "trace_decommitments": 1_920,
        },
    },
}

EXPECTED_AGGREGATE = {
    "available_separate_component_count": 6,
    "available_separate_proof_bytes": 198_937,
    "available_separate_typed_bytes": 59_344,
    "derived_fused_proof_bytes": 68_560,
    "derived_fused_typed_bytes": 22_576,
    "json_saving_vs_separate_bytes": 130_377,
    "json_ratio_vs_separate": 0.344632,
    "typed_saving_vs_separate_bytes": 36_768,
    "typed_ratio_vs_separate": 0.380426,
    "matched_six_separate_derived_baseline_status": "COMPLETE_EXACT_SIX_DERIVED_SEPARATE_ENVELOPES",
}

EXPECTED_GROUP_ATTRIBUTION = {
    "fixed_overhead": {
        "separate_typed_bytes": 288,
        "fused_typed_bytes": 48,
        "saved_typed_bytes": 240,
        "saved_share_of_total": 0.006527,
    },
    "fri_decommitments": {
        "separate_typed_bytes": 31_296,
        "fused_typed_bytes": 10_784,
        "saved_typed_bytes": 20_512,
        "saved_share_of_total": 0.557876,
    },
    "fri_samples": {
        "separate_typed_bytes": 2_848,
        "fused_typed_bytes": 720,
        "saved_typed_bytes": 2_128,
        "saved_share_of_total": 0.057876,
    },
    "oods_samples": {
        "separate_typed_bytes": 4_416,
        "fused_typed_bytes": 3_776,
        "saved_typed_bytes": 640,
        "saved_share_of_total": 0.017406,
    },
    "queries_values": {
        "separate_typed_bytes": 3_312,
        "fused_typed_bytes": 2_832,
        "saved_typed_bytes": 480,
        "saved_share_of_total": 0.013055,
    },
    "trace_decommitments": {
        "separate_typed_bytes": 17_184,
        "fused_typed_bytes": 4_416,
        "saved_typed_bytes": 12_768,
        "saved_share_of_total": 0.347258,
    },
}

EXPECTED_SUMMARY = {
    "largest_saved_group": "fri_decommitments",
    "largest_saved_group_bytes": 20_512,
    "largest_saved_group_share": 0.557876,
    "opening_plumbing_saved_bytes": 33_280,
    "opening_plumbing_share": 0.905135,
    "fri_plus_trace_plus_fri_sample_saved_bytes": 35_408,
    "fri_plus_trace_plus_fri_sample_share": 0.963011,
    "sample_and_query_saved_bytes": 3_248,
    "sample_and_query_share": 0.088338,
    "compression_probe_result": "NO_GO_DROP_FRI_DECOMMITMENTS_WOULD_DROP_VERIFIER_OPENING_WITNESS",
    "safe_compression_status": "NO_SAFE_INTERNAL_BUCKET_REMOVED_WITHOUT_CHANGING_PROOF_OBJECT_CLASS",
}

MECHANISM = (
    "the fused proof pays one FRI/decommitment surface for six adjacent MLP-side relations",
    "the six separate proof objects repeat FRI and trace Merkle path material",
    "90.5135% of the typed saving comes from FRI plus trace decommitment groups",
    "the largest saved group is FRI decommitments at 20,512 typed bytes",
    "dropping that group inside the same proof object would remove verifier opening witness material",
    "the honest next frontier is a larger native object boundary, especially attention plus RMSNorm-MLP",
)

NON_CLAIMS = (
    "not attention plus MLP in one native proof object",
    "not a new proof object",
    "not a smaller fused MLP proof",
    "not a NANOZK benchmark win",
    "not a matched external zkML benchmark",
    "not upstream Stwo serialization",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json",
    "python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv",
    "python3 scripts/zkai_attention_derived_d128_mlp_fusion_attribution_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_mlp_fusion_attribution_gate.py scripts/tests/test_zkai_attention_derived_d128_mlp_fusion_attribution_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_mlp_fusion_attribution_gate",
    "git diff --check",
    "just gate-fast",
)

EXPECTED_EVIDENCE = {
    "accounting_json": "docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json",
    "route_gate_json": "docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json",
    "attribution_json": "docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.json",
    "attribution_tsv": "docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.tsv",
}

TSV_COLUMNS = (
    "decision",
    "result",
    "available_separate_typed_bytes",
    "derived_fused_typed_bytes",
    "typed_saving_vs_separate_bytes",
    "typed_ratio_vs_separate",
    "opening_plumbing_saved_bytes",
    "opening_plumbing_share",
    "largest_saved_group",
    "largest_saved_group_bytes",
    "largest_saved_group_share",
    "compression_probe_result",
)

MUTATION_NAMES = (
    "schema_relabeling",
    "decision_overclaim",
    "result_overclaim",
    "claim_boundary_overclaim",
    "fused_typed_metric_smuggling",
    "separate_typed_metric_smuggling",
    "typed_saving_metric_smuggling",
    "group_saved_metric_smuggling",
    "largest_group_relabeling",
    "opening_share_smuggling",
    "compression_probe_overclaim",
    "mechanism_removed",
    "non_claim_removed",
    "validation_command_drift",
    "evidence_path_drift",
    "component_role_removed",
    "matched_baseline_status_drift",
    "payload_commitment_relabeling",
    "unknown_field_injection",
)


class MlpFusionAttributionError(ValueError):
    pass


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        raise MlpFusionAttributionError("ratio denominator must be non-zero")
    return round(numerator / denominator, 6)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def reject_json_constant(value: str) -> None:
    raise MlpFusionAttributionError(f"non-finite JSON constant rejected: {value}")


def payload_commitment(payload: dict[str, Any]) -> str:
    canonical = copy.deepcopy(payload)
    canonical.pop("payload_commitment", None)
    return "sha256:" + hashlib.sha256(canonical_bytes(canonical)).hexdigest()


def read_json_with_size(path: pathlib.Path, max_bytes: int, label: str) -> tuple[Any, int]:
    if path.is_symlink():
        raise MlpFusionAttributionError(f"{label} must not be a symlink: {path}")
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise MlpFusionAttributionError(f"{label} escapes evidence directory: {path}") from err
    try:
        pre = resolved.lstat()
    except OSError as err:
        raise MlpFusionAttributionError(f"failed to stat {label}: {err}") from err
    if not stat.S_ISREG(pre.st_mode):
        raise MlpFusionAttributionError(f"{label} is not a regular file: {path}")
    try:
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as err:
        raise MlpFusionAttributionError(f"failed to open {label}: {err}") from err
    try:
        post = os.fstat(fd)
        if (pre.st_dev, pre.st_ino) != (post.st_dev, post.st_ino):
            raise MlpFusionAttributionError(f"{label} changed while opening: {path}")
        if post.st_size > max_bytes:
            raise MlpFusionAttributionError(f"{label} exceeds max size: got {post.st_size} bytes")
        raw = os.read(fd, max_bytes + 1)
    finally:
        if fd is not None:
            os.close(fd)
    if len(raw) > max_bytes:
        raise MlpFusionAttributionError(f"{label} exceeds max size: got at least {len(raw)} bytes")
    if len(raw) != post.st_size:
        raise MlpFusionAttributionError(f"{label} changed while reading: {path}")
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=reject_json_constant), int(post.st_size)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise MlpFusionAttributionError(f"{label} is not JSON: {err}") from err


def read_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    payload, _size = read_json_with_size(path, max_bytes, label)
    return payload


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MlpFusionAttributionError(f"{label} must be object")
    return value


def rows_by_role(accounting: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = accounting.get("rows")
    if not isinstance(rows, list) or len(rows) != 7:
        raise MlpFusionAttributionError("accounting rows must contain one fused row plus six separate rows")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        row = require_dict(row, "accounting row")
        relative = row.get("evidence_relative_path")
        expected = EXPECTED_ROWS.get(relative)
        if expected is None:
            raise MlpFusionAttributionError(f"unexpected accounting row path: {relative}")
        result[expected["role"]] = row
    expected_roles = {FUSED_ROLE, *SEPARATE_ROLES}
    if set(result) != expected_roles:
        raise MlpFusionAttributionError("accounting roles are incomplete")
    return result


def validate_accounting_row(row: dict[str, Any], expected: dict[str, Any]) -> None:
    metadata = require_dict(row.get("envelope_metadata"), "row envelope metadata")
    for field in ("proof_backend_version", "statement_version"):
        if metadata.get(field) != expected[field]:
            raise MlpFusionAttributionError(f"{expected['role']} {field} drift")
    if row.get("proof_json_size_bytes") != expected["proof_json_size_bytes"]:
        raise MlpFusionAttributionError(f"{expected['role']} proof JSON byte drift")
    accounting = require_dict(row.get("local_binary_accounting"), "local binary accounting")
    if accounting.get("typed_size_estimate_bytes") != expected["local_typed_bytes"]:
        raise MlpFusionAttributionError(f"{expected['role']} typed byte drift")
    grouped = require_dict(accounting.get("grouped_reconstruction"), "grouped reconstruction")
    if grouped != expected["grouped"]:
        raise MlpFusionAttributionError(f"{expected['role']} grouped reconstruction drift")


def group_attribution() -> dict[str, dict[str, int | float]]:
    result: dict[str, dict[str, int | float]] = {}
    total_saving = EXPECTED_AGGREGATE["typed_saving_vs_separate_bytes"]
    fused_grouped = EXPECTED_ROWS["zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json"]["grouped"]
    for group in GROUP_KEYS:
        separate = sum(
            int(expected["grouped"][group])
            for expected in EXPECTED_ROWS.values()
            if expected["role"] in SEPARATE_ROLES
        )
        fused = int(fused_grouped[group])
        saved = separate - fused
        result[group] = {
            "separate_typed_bytes": separate,
            "fused_typed_bytes": fused,
            "saved_typed_bytes": saved,
            "saved_share_of_total": rounded_ratio(saved, total_saving),
        }
    if result != EXPECTED_GROUP_ATTRIBUTION:
        raise MlpFusionAttributionError("group attribution drift")
    return result


def ranked_groups(groups: dict[str, dict[str, int | float]]) -> list[dict[str, int | float | str]]:
    return [
        {"group": group, **values}
        for group, values in sorted(
            groups.items(),
            key=lambda item: (-int(item[1]["saved_typed_bytes"]), item[0]),
        )
    ]


def summary_from_groups(groups: dict[str, dict[str, int | float]]) -> dict[str, int | float | str]:
    opening = int(groups["fri_decommitments"]["saved_typed_bytes"]) + int(groups["trace_decommitments"]["saved_typed_bytes"])
    fri_trace_samples = opening + int(groups["fri_samples"]["saved_typed_bytes"])
    sample_query = (
        int(groups["fri_samples"]["saved_typed_bytes"])
        + int(groups["oods_samples"]["saved_typed_bytes"])
        + int(groups["queries_values"]["saved_typed_bytes"])
    )
    total = EXPECTED_AGGREGATE["typed_saving_vs_separate_bytes"]
    largest = ranked_groups(groups)[0]
    summary = {
        "largest_saved_group": str(largest["group"]),
        "largest_saved_group_bytes": int(largest["saved_typed_bytes"]),
        "largest_saved_group_share": float(largest["saved_share_of_total"]),
        "opening_plumbing_saved_bytes": opening,
        "opening_plumbing_share": rounded_ratio(opening, total),
        "fri_plus_trace_plus_fri_sample_saved_bytes": fri_trace_samples,
        "fri_plus_trace_plus_fri_sample_share": rounded_ratio(fri_trace_samples, total),
        "sample_and_query_saved_bytes": sample_query,
        "sample_and_query_share": rounded_ratio(sample_query, total),
        "compression_probe_result": EXPECTED_SUMMARY["compression_probe_result"],
        "safe_compression_status": EXPECTED_SUMMARY["safe_compression_status"],
    }
    if summary != EXPECTED_SUMMARY:
        raise MlpFusionAttributionError("summary drift")
    return summary


def validate_route_gate(route_gate: dict[str, Any]) -> None:
    comparison = require_dict(route_gate.get("comparison"), "route gate comparison")
    route_key_map = {
        "available_separate_component_count": "available_separate_component_count",
        "available_separate_proof_bytes": "available_separate_proof_bytes",
        "available_separate_typed_bytes": "available_separate_typed_bytes",
        "derived_fused_proof_bytes": "derived_fused_proof_bytes",
        "derived_fused_typed_bytes": "derived_fused_typed_bytes",
        "typed_saving_vs_separate_bytes": "typed_saving_vs_available_separate_bytes",
        "typed_ratio_vs_separate": "typed_ratio_vs_available_separate",
        "matched_six_separate_derived_baseline_status": "matched_six_separate_derived_baseline_status",
    }
    for expected_key, route_key in route_key_map.items():
        if comparison.get(route_key) != EXPECTED_AGGREGATE[expected_key]:
            raise MlpFusionAttributionError(f"route gate {route_key} drift")
    route_json_saving = comparison["available_separate_proof_bytes"] - comparison["derived_fused_proof_bytes"]
    if route_json_saving != EXPECTED_AGGREGATE["json_saving_vs_separate_bytes"]:
        raise MlpFusionAttributionError("route gate JSON saving drift")
    if rounded_ratio(comparison["derived_fused_proof_bytes"], comparison["available_separate_proof_bytes"]) != EXPECTED_AGGREGATE["json_ratio_vs_separate"]:
        raise MlpFusionAttributionError("route gate JSON ratio drift")
    if route_gate.get("result") != "GO_DERIVED_NATIVE_RMSNORM_MLP_FUSED_PROOF_EXISTS_WITH_EXACT_SIX_BASELINE_SAVING":
        raise MlpFusionAttributionError("route gate result drift")
    if route_gate.get("first_blocker") != (
        "the attention-derived RMSNorm-MLP fused proof now exists, but attention arithmetic is not yet "
        "inside the same native proof object"
    ):
        raise MlpFusionAttributionError("route gate first blocker drift")


def build_payload() -> dict[str, Any]:
    accounting = require_dict(read_json(ACCOUNTING_PATH, 16 * 1024 * 1024, "accounting JSON"), "accounting JSON")
    route_gate = require_dict(read_json(ROUTE_GATE_PATH, 4 * 1024 * 1024, "route gate JSON"), "route gate JSON")
    validate_route_gate(route_gate)
    role_rows = rows_by_role(accounting)
    for expected in EXPECTED_ROWS.values():
        validate_accounting_row(role_rows[expected["role"]], expected)

    groups = group_attribution()
    summary = summary_from_groups(groups)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
        "aggregate": copy.deepcopy(EXPECTED_AGGREGATE),
        "component_roles": copy.deepcopy(EXPECTED_ROWS),
        "group_attribution": groups,
        "ranked_saved_groups": ranked_groups(groups),
        "summary": summary,
        "mechanism": list(MECHANISM),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "evidence": copy.deepcopy(EXPECTED_EVIDENCE),
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
        "aggregate",
        "component_roles",
        "group_attribution",
        "ranked_saved_groups",
        "summary",
        "mechanism",
        "non_claims",
        "validation_commands",
        "evidence",
        "mutation_inventory",
        "payload_commitment",
    }
    allowed_top = expected_top | {"mutation_result"}
    if not expected_top.issubset(payload) or not set(payload).issubset(allowed_top):
        raise MlpFusionAttributionError(f"payload keys drift: {sorted(set(payload) ^ allowed_top)}")
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
            raise MlpFusionAttributionError(f"{key} drift")
    if payload.get("aggregate") != EXPECTED_AGGREGATE:
        raise MlpFusionAttributionError("aggregate mismatch")
    if payload.get("component_roles") != EXPECTED_ROWS:
        raise MlpFusionAttributionError("component roles mismatch")
    if payload.get("group_attribution") != EXPECTED_GROUP_ATTRIBUTION:
        raise MlpFusionAttributionError("group attribution mismatch")
    if payload.get("ranked_saved_groups") != ranked_groups(EXPECTED_GROUP_ATTRIBUTION):
        raise MlpFusionAttributionError("ranked groups mismatch")
    if payload.get("summary") != EXPECTED_SUMMARY:
        raise MlpFusionAttributionError("summary mismatch")
    if payload.get("mechanism") != list(MECHANISM):
        raise MlpFusionAttributionError("mechanism mismatch")
    if payload.get("non_claims") != list(NON_CLAIMS):
        raise MlpFusionAttributionError("non-claims mismatch")
    if payload.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise MlpFusionAttributionError("validation commands mismatch")
    if payload.get("evidence") != EXPECTED_EVIDENCE:
        raise MlpFusionAttributionError("evidence mismatch")
    inventory = require_dict(payload.get("mutation_inventory"), "mutation inventory")
    if inventory.get("case_count") != len(MUTATION_NAMES) or inventory.get("cases") != list(MUTATION_NAMES):
        raise MlpFusionAttributionError("mutation inventory mismatch")
    if "all_mutations_rejected" in inventory and inventory["all_mutations_rejected"] is not True:
        raise MlpFusionAttributionError("mutation inventory rejection status mismatch")
    if "mutation_result" in payload:
        result = require_dict(payload["mutation_result"], "mutation result")
        if result.get("case_count") != len(MUTATION_NAMES) or result.get("all_mutations_rejected") is not True:
            raise MlpFusionAttributionError("mutation result mismatch")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise MlpFusionAttributionError("payload commitment mismatch")


def mutation_cases() -> list[tuple[str, Callable[[dict[str, Any]], None]]]:
    return [
        ("schema_relabeling", lambda p: p.__setitem__("schema", "v2")),
        ("decision_overclaim", lambda p: p.__setitem__("decision", "BREAKTHROUGH_FULL_BLOCK")),
        ("result_overclaim", lambda p: p.__setitem__("result", "GO_SAFE_INTERNAL_COMPRESSION_FOUND")),
        ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "NANOZK_MATCHED_WIN")),
        ("fused_typed_metric_smuggling", lambda p: p["aggregate"].__setitem__("derived_fused_typed_bytes", 22_575)),
        ("separate_typed_metric_smuggling", lambda p: p["aggregate"].__setitem__("available_separate_typed_bytes", 59_345)),
        ("typed_saving_metric_smuggling", lambda p: p["aggregate"].__setitem__("typed_saving_vs_separate_bytes", 36_769)),
        ("group_saved_metric_smuggling", lambda p: p["group_attribution"]["fri_decommitments"].__setitem__("saved_typed_bytes", 20_511)),
        ("largest_group_relabeling", lambda p: p["summary"].__setitem__("largest_saved_group", "trace_decommitments")),
        ("opening_share_smuggling", lambda p: p["summary"].__setitem__("opening_plumbing_share", 0.95)),
        ("compression_probe_overclaim", lambda p: p["summary"].__setitem__("safe_compression_status", "SAFE_INTERNAL_BUCKET_REMOVED")),
        ("mechanism_removed", lambda p: p.__setitem__("mechanism", p["mechanism"][:-1])),
        ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1])),
        ("validation_command_drift", lambda p: p["validation_commands"].__setitem__(0, "python3 fake.py")),
        ("evidence_path_drift", lambda p: p["evidence"].__setitem__("accounting_json", "docs/engineering/evidence/other.json")),
        ("component_role_removed", lambda p: p["component_roles"].pop("zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json")),
        ("matched_baseline_status_drift", lambda p: p["aggregate"].__setitem__("matched_six_separate_derived_baseline_status", "PARTIAL")),
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
        except MlpFusionAttributionError as err:
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
        raise MlpFusionAttributionError(f"{label} output must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise MlpFusionAttributionError(f"{label} output escapes evidence directory: {path}") from err
    parent = resolved.parent
    try:
        parent_stat = parent.lstat()
    except OSError as err:
        raise MlpFusionAttributionError(f"{label} output parent must already exist: {err}") from err
    if parent.is_symlink() or not stat.S_ISDIR(parent_stat.st_mode):
        raise MlpFusionAttributionError(f"{label} output parent is not a regular directory: {parent}")
    try:
        existing = resolved.lstat()
    except FileNotFoundError:
        return resolved
    except OSError as err:
        raise MlpFusionAttributionError(f"failed to stat {label} output: {err}") from err
    if not stat.S_ISREG(existing.st_mode):
        raise MlpFusionAttributionError(f"{label} output is not a regular file: {path}")
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
        raise MlpFusionAttributionError(f"failed to atomically write {label}: {err}") from err
    finally:
        if fd is not None:
            os.close(fd)
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    write_bytes_atomic(path, data, "attribution JSON")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    row = {column: payload["aggregate"].get(column, payload["summary"].get(column, payload.get(column))) for column in TSV_COLUMNS}
    row["decision"] = payload["decision"]
    row["result"] = payload["result"]
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
    write_bytes_atomic(path, handle.getvalue().encode("utf-8"), "attribution TSV")


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
        raise MlpFusionAttributionError("not all mutations rejected")
    validate_payload(payload)

    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload)
    if not args.write_json and not args.write_tsv:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
