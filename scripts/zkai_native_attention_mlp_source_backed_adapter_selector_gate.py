#!/usr/bin/env python3
"""Gate source-backed duplicate/compact adapter selector artifacts."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import copy
import csv
import hashlib
import io
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_native_attention_mlp_single_proof_route_gate as route_gate  # noqa: E402


EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
DUPLICATE_INPUT_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.input.json"
)
DUPLICATE_ENVELOPE_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json"
)
COMPACT_INPUT_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.input.json"
)
COMPACT_ENVELOPE_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json"
)
ACCOUNTING_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-source-backed-adapter-selector-binary-accounting-2026-05.json"
)

JSON_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-source-backed-adapter-selector-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-source-backed-adapter-selector-2026-05.tsv"

SCHEMA = "zkai-native-attention-mlp-source-backed-adapter-selector-gate-v1"
DECISION = "NARROW_CLAIM_SOURCE_BACKED_COMPACT_ADAPTER_SELECTOR_VERIFIES"
RESULT = "GO_SOURCE_BACKED_COMPACT_ARTIFACT_NO_GO_TWO_PROOF_FRONTIER_BEAT"
ISSUE = "https://github.com/omarespejel/provable-transformer-vm/issues/637"
PAYLOAD_DOMAIN = "ptvm:zkai:native-attention-mlp-source-backed-adapter-selector:v1"
CLAIM_BOUNDARY = (
    "SOURCE_BACKED_DUPLICATE_AND_COMPACT_NATIVE_ADAPTER_PROOF_ARTIFACTS_WITHOUT_CLAIMING_"
    "A_TRANSCRIPT_STABLE_FRONTIER_WIN_OR_NANOZK_COMPARABILITY"
)

TWO_PROOF_FRONTIER_TYPED_BYTES = 40_700
TWO_PROOF_FRONTIER_JSON_BYTES = 116_258
CURRENT_NATIVE_ADAPTER_AIR_TYPED_BYTES = 41_932
NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900

EXPECTED_VARIANTS = {
    "duplicate_selector": {
        "input_path": DUPLICATE_INPUT_PATH,
        "envelope_path": DUPLICATE_ENVELOPE_PATH,
        "accounting_relative_path": "zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json",
        "adapter_mode": "duplicate_base_preprocessed_selector_v1",
        "adapter_status": "NATIVE_AIR_PROVEN_ATTENTION_OUTPUT_TO_D128_INPUT_ADAPTER",
        "adapter_value_columns": 9,
        "adapter_trace_cells": 1_536,
        "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-duplicate-adapter-selector-v1",
        "proof_json_size_bytes": 124_585,
        "typed_size_estimate_bytes": 43_228,
        "envelope_size_bytes": 1_292_617,
        "record_stream_sha256": "d5e901818d55d538f03adfefb910e3e52f34a13eb1465dfd3af76d746f141154",
    },
    "compact_selector": {
        "input_path": COMPACT_INPUT_PATH,
        "envelope_path": COMPACT_ENVELOPE_PATH,
        "accounting_relative_path": "zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json",
        "adapter_mode": "compact_base_referenced_fixed_v1",
        "adapter_status": "NATIVE_AIR_PROVEN_ATTENTION_OUTPUT_TO_D128_INPUT_ADAPTER_COMPACT_BASE_REFERENCED_FIXED_COLUMNS",
        "adapter_value_columns": 5,
        "adapter_trace_cells": 1_024,
        "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-compact-adapter-selector-v1",
        "proof_json_size_bytes": 116_091,
        "typed_size_estimate_bytes": 40_812,
        "envelope_size_bytes": 1_224_675,
        "record_stream_sha256": "8ed8db52bfb240a2b742df9877aa8d01ece09334616540771812e28081c5d996",
    },
}

EXPECTED_GROUP_DELTAS = {
    "fixed_overhead": 0,
    "fri_decommitments": 1_728,
    "fri_samples": 64,
    "oods_samples": 64,
    "queries_values": 48,
    "trace_decommitments": 512,
}

NON_CLAIMS = (
    "not a transcript-stable compact-adapter frontier win",
    "not a two-proof frontier beat under typed accounting",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not timing evidence",
    "not a full transformer block proof",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- build-input-duplicate-selector docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- build-input-compact docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- prove docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- prove docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- verify docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- verify docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json > docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-binary-accounting-2026-05.json",
    "python3 scripts/zkai_native_attention_mlp_source_backed_adapter_selector_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_source_backed_adapter_selector_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend native_attention_mlp_single_proof --lib",
    "git diff --check",
    "just gate-fast",
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "claim_boundary",
    "source_artifacts",
    "variants",
    "comparisons",
    "summary",
    "interpretation",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "mutation_result"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

MUTATION_NAMES = (
    "compact_typed_bytes_drift",
    "duplicate_typed_bytes_drift",
    "compact_mode_relabeling",
    "compact_frontier_overclaim",
    "nanozk_overclaim",
    "query_fingerprint_drift",
    "source_artifact_hash_drift",
    "payload_commitment_drift",
)

TSV_COLUMNS = (
    "decision",
    "result",
    "duplicate_typed_bytes",
    "compact_typed_bytes",
    "compact_typed_saving_vs_duplicate_bytes",
    "compact_typed_ratio_vs_duplicate",
    "compact_typed_delta_vs_two_proof_bytes",
    "compact_typed_delta_vs_current_native_adapter_air_bytes",
    "compact_json_saving_vs_duplicate_bytes",
    "compact_json_delta_vs_two_proof_bytes",
    "direct_opening_value_saving_bytes",
    "path_sensitive_saving_bytes",
    "compact_trace_cells",
    "duplicate_trace_cells",
)


class SourceBackedAdapterSelectorError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise SourceBackedAdapterSelectorError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    digest = hashlib.blake2b(digest_size=32)
    digest.update(PAYLOAD_DOMAIN.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(material))
    return "blake2b-256:" + digest.hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise SourceBackedAdapterSelectorError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceBackedAdapterSelectorError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SourceBackedAdapterSelectorError(f"{label} must be list")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SourceBackedAdapterSelectorError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SourceBackedAdapterSelectorError(f"{label} must be integer")
    return value


def read_json_and_raw(path: pathlib.Path, label: str) -> tuple[Any, bytes]:
    try:
        return route_gate.read_json_and_raw_bytes(path, label)
    except route_gate.NativeAttentionMlpSingleProofRouteError as err:
        raise SourceBackedAdapterSelectorError(str(err)) from err


def build_context() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, path in (
        ("duplicate_input", DUPLICATE_INPUT_PATH),
        ("duplicate_envelope", DUPLICATE_ENVELOPE_PATH),
        ("compact_input", COMPACT_INPUT_PATH),
        ("compact_envelope", COMPACT_ENVELOPE_PATH),
        ("accounting", ACCOUNTING_PATH),
    ):
        payload, raw = read_json_and_raw(path, key)
        values[key] = _dict(payload, key)
        values[f"{key}_raw"] = raw
    return values


def source_artifacts(context: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = []
    for artifact_id, path, raw_key in (
        ("duplicate_input", DUPLICATE_INPUT_PATH, "duplicate_input_raw"),
        ("duplicate_envelope", DUPLICATE_ENVELOPE_PATH, "duplicate_envelope_raw"),
        ("compact_input", COMPACT_INPUT_PATH, "compact_input_raw"),
        ("compact_envelope", COMPACT_ENVELOPE_PATH, "compact_envelope_raw"),
        ("selector_binary_accounting", ACCOUNTING_PATH, "accounting_raw"),
    ):
        raw = context[raw_key]
        artifacts.append(
            {
                "id": artifact_id,
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return artifacts


def accounting_rows_by_path(accounting: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {}
    for row in _list(accounting.get("rows"), "accounting rows"):
        row_dict = _dict(row, "accounting row")
        path = _str(row_dict.get("evidence_relative_path"), "accounting relative path")
        rows[path] = row_dict
    if len(rows) != 2:
        raise SourceBackedAdapterSelectorError(f"expected 2 accounting rows, got {len(rows)}")
    return rows


def variant_payload(role: str, context: dict[str, Any], rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    expected = EXPECTED_VARIANTS[role]
    envelope_key = "duplicate_envelope" if role == "duplicate_selector" else "compact_envelope"
    input_key = "duplicate_input" if role == "duplicate_selector" else "compact_input"
    raw_key = f"{envelope_key}_raw"
    envelope = _dict(context[envelope_key], f"{role} envelope")
    input_payload = _dict(envelope.get("input"), f"{role} envelope input")
    standalone_input = _dict(context[input_key], f"{role} input")
    row = rows[expected["accounting_relative_path"]]
    local = _dict(row.get("local_binary_accounting"), f"{role} local accounting")
    metadata = _dict(row.get("envelope_metadata"), f"{role} envelope metadata")

    checks = {
        "adapter_mode": input_payload.get("adapter_mode"),
        "adapter_status": input_payload.get("adapter_status"),
        "adapter_value_columns": input_payload.get("adapter_value_columns"),
        "adapter_trace_cells": input_payload.get("adapter_trace_cells"),
        "proof_backend_version": envelope.get("proof_backend_version"),
        "proof_json_size_bytes": row.get("proof_json_size_bytes"),
        "typed_size_estimate_bytes": local.get("typed_size_estimate_bytes"),
        "envelope_size_bytes": len(context[raw_key]),
        "record_stream_sha256": local.get("record_stream_sha256"),
    }
    for key, expected_value in expected.items():
        if key in {"input_path", "envelope_path", "accounting_relative_path"}:
            continue
        if checks.get(key) != expected_value:
            raise SourceBackedAdapterSelectorError(
                f"{role} {key} drift: got {checks.get(key)!r}, expected {expected_value!r}"
            )
    if standalone_input != input_payload:
        raise SourceBackedAdapterSelectorError(f"{role} standalone input does not match envelope input")
    if metadata.get("proof_backend_version") != expected["proof_backend_version"]:
        raise SourceBackedAdapterSelectorError(f"{role} accounting backend version drift")
    if local.get("component_sum_bytes") != expected["typed_size_estimate_bytes"]:
        raise SourceBackedAdapterSelectorError(f"{role} component sum drift")
    return {
        "adapter_mode": checks["adapter_mode"],
        "adapter_status": checks["adapter_status"],
        "adapter_row_count": input_payload["adapter_row_count"],
        "adapter_value_columns": checks["adapter_value_columns"],
        "adapter_remainder_bit_columns": input_payload["adapter_remainder_bit_columns"],
        "adapter_trace_cells": checks["adapter_trace_cells"],
        "proof_backend_version": checks["proof_backend_version"],
        "statement_commitment": input_payload["statement_commitment"],
        "public_instance_commitment": input_payload["public_instance_commitment"],
        "proof_json_size_bytes": checks["proof_json_size_bytes"],
        "typed_size_estimate_bytes": checks["typed_size_estimate_bytes"],
        "envelope_size_bytes": checks["envelope_size_bytes"],
        "record_stream_sha256": checks["record_stream_sha256"],
        "grouped_reconstruction": local["grouped_reconstruction"],
    }


def build_payload_no_mutations(context: dict[str, Any]) -> dict[str, Any]:
    accounting = _dict(context["accounting"], "accounting")
    rows = accounting_rows_by_path(accounting)
    duplicate = variant_payload("duplicate_selector", context, rows)
    compact = variant_payload("compact_selector", context, rows)

    duplicate_groups = _dict(duplicate["grouped_reconstruction"], "duplicate groups")
    compact_groups = _dict(compact["grouped_reconstruction"], "compact groups")
    group_deltas = {
        key: _int(duplicate_groups.get(key), f"duplicate {key}")
        - _int(compact_groups.get(key), f"compact {key}")
        for key in EXPECTED_GROUP_DELTAS
    }
    if group_deltas != EXPECTED_GROUP_DELTAS:
        raise SourceBackedAdapterSelectorError(f"group deltas drift: {group_deltas}")

    typed_saving = duplicate["typed_size_estimate_bytes"] - compact["typed_size_estimate_bytes"]
    json_saving = duplicate["proof_json_size_bytes"] - compact["proof_json_size_bytes"]
    direct_opening_saving = group_deltas["oods_samples"] + group_deltas["queries_values"]
    path_sensitive_saving = typed_saving - direct_opening_saving
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": source_artifacts(context),
        "variants": {
            "duplicate_selector": duplicate,
            "compact_selector": compact,
        },
        "comparisons": {
            "compact_vs_source_backed_duplicate": {
                "status": "GO_COMPACT_SMALLER_THAN_SOURCE_BACKED_DUPLICATE",
                "typed_saving_bytes": typed_saving,
                "typed_ratio": ratio(compact["typed_size_estimate_bytes"], duplicate["typed_size_estimate_bytes"]),
                "json_saving_bytes": json_saving,
                "json_ratio": ratio(compact["proof_json_size_bytes"], duplicate["proof_json_size_bytes"]),
                "direct_opening_value_saving_bytes": direct_opening_saving,
                "path_sensitive_saving_bytes": path_sensitive_saving,
                "path_sensitive_saving_share": ratio(path_sensitive_saving, typed_saving),
                "group_deltas_bytes": group_deltas,
            },
            "compact_vs_two_proof_frontier": {
                "status": "NO_GO_TYPED_TWO_PROOF_FRONTIER_NOT_BEATEN",
                "two_proof_frontier_typed_bytes": TWO_PROOF_FRONTIER_TYPED_BYTES,
                "typed_delta_bytes": compact["typed_size_estimate_bytes"] - TWO_PROOF_FRONTIER_TYPED_BYTES,
                "typed_ratio": ratio(compact["typed_size_estimate_bytes"], TWO_PROOF_FRONTIER_TYPED_BYTES),
                "two_proof_frontier_json_bytes": TWO_PROOF_FRONTIER_JSON_BYTES,
                "json_delta_bytes": compact["proof_json_size_bytes"] - TWO_PROOF_FRONTIER_JSON_BYTES,
                "json_ratio": ratio(compact["proof_json_size_bytes"], TWO_PROOF_FRONTIER_JSON_BYTES),
                "frontier_win_claimed": False,
            },
            "compact_vs_current_native_adapter_air": {
                "status": "NARROW_CLAIM_SOURCE_BACKED_COMPACT_RECOVERS_MOST_PRIOR_ADAPTER_OVERHEAD",
                "current_native_adapter_air_typed_bytes": CURRENT_NATIVE_ADAPTER_AIR_TYPED_BYTES,
                "typed_saving_bytes": CURRENT_NATIVE_ADAPTER_AIR_TYPED_BYTES - compact["typed_size_estimate_bytes"],
                "remaining_gap_to_two_proof_frontier_bytes": compact["typed_size_estimate_bytes"]
                - TWO_PROOF_FRONTIER_TYPED_BYTES,
            },
            "nanozk_boundary": {
                "status": "NO_GO_NOT_NANOZK_COMPARABLE",
                "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
                "compact_typed_gap_to_nanozk_reported_bytes": compact["typed_size_estimate_bytes"]
                - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
                "matched_workload_or_object_class": False,
                "proof_size_win_claimed": False,
            },
        },
        "summary": {
            "duplicate_typed_bytes": duplicate["typed_size_estimate_bytes"],
            "compact_typed_bytes": compact["typed_size_estimate_bytes"],
            "compact_typed_saving_vs_duplicate_bytes": typed_saving,
            "compact_typed_ratio_vs_duplicate": ratio(
                compact["typed_size_estimate_bytes"], duplicate["typed_size_estimate_bytes"]
            ),
            "compact_typed_delta_vs_two_proof_bytes": compact["typed_size_estimate_bytes"]
            - TWO_PROOF_FRONTIER_TYPED_BYTES,
            "compact_typed_delta_vs_current_native_adapter_air_bytes": compact["typed_size_estimate_bytes"]
            - CURRENT_NATIVE_ADAPTER_AIR_TYPED_BYTES,
            "duplicate_json_bytes": duplicate["proof_json_size_bytes"],
            "compact_json_bytes": compact["proof_json_size_bytes"],
            "compact_json_saving_vs_duplicate_bytes": json_saving,
            "compact_json_delta_vs_two_proof_bytes": compact["proof_json_size_bytes"]
            - TWO_PROOF_FRONTIER_JSON_BYTES,
            "direct_opening_value_saving_bytes": direct_opening_saving,
            "path_sensitive_saving_bytes": path_sensitive_saving,
            "compact_trace_cells": compact["adapter_trace_cells"],
            "duplicate_trace_cells": duplicate["adapter_trace_cells"],
        },
        "interpretation": {
            "human_read": (
                "compact adapter AIR now has a real source-backed proof artifact and saves 2416 typed bytes "
                "versus the matching duplicate selector, but it remains 112 typed bytes above the current "
                "two-proof frontier"
            ),
            "promotion_status": "NARROW_GO_FOR_MECHANISM_NO_GO_FOR_FRONTIER_REPLACEMENT",
            "next_attack": "remove the final 112 typed bytes without relying on path-sensitive transcript churn",
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "payload_commitment": "",
    }
    refresh_payload_commitment(payload)
    return payload


def build_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    payload = build_payload_no_mutations(context)
    payload["mutation_inventory"] = {"cases": list(MUTATION_NAMES)}
    payload["mutation_result"] = mutation_result_placeholder()
    refresh_payload_commitment(payload)
    validate_payload(payload, context=context)
    payload["mutation_result"] = mutation_result(payload, context)
    refresh_payload_commitment(payload)
    validate_payload(payload, context=context)
    return payload


def validate_payload(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> None:
    context = build_context() if context is None else context
    if set(payload) != FINAL_KEYS:
        raise SourceBackedAdapterSelectorError("top-level key drift")
    expected = build_payload_no_mutations(context)
    for key in CORE_KEYS - {"payload_commitment"}:
        if payload.get(key) != expected.get(key):
            raise SourceBackedAdapterSelectorError(f"{key} drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise SourceBackedAdapterSelectorError("payload_commitment drift")
    mutation = _dict(payload.get("mutation_result"), "mutation result")
    cases = _list(mutation.get("cases"), "mutation cases")
    if [case.get("name") for case in cases] != list(MUTATION_NAMES):
        raise SourceBackedAdapterSelectorError("mutation inventory drift")
    if not all(case.get("rejected") is True for case in cases):
        raise SourceBackedAdapterSelectorError("mutation rejection drift")
    if payload.get("mutation_inventory") != {"cases": list(MUTATION_NAMES)}:
        raise SourceBackedAdapterSelectorError("mutation inventory drift")


def mutation_result_placeholder() -> dict[str, Any]:
    return {"cases": [{"name": name, "rejected": True, "reason": "placeholder"} for name in MUTATION_NAMES]}


def mutation_result(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for name, mutator in mutation_cases():
        candidate = copy.deepcopy(payload)
        mutator(candidate)
        try:
            validate_payload(candidate, context=context)
        except SourceBackedAdapterSelectorError as err:
            cases.append({"name": name, "rejected": True, "reason": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "reason": "mutation accepted"})
    return {"cases": cases}


def mutation_cases() -> list[tuple[str, Callable[[dict[str, Any]], None]]]:
    return [
        ("compact_typed_bytes_drift", lambda p: p["summary"].__setitem__("compact_typed_bytes", 40_700)),
        ("duplicate_typed_bytes_drift", lambda p: p["summary"].__setitem__("duplicate_typed_bytes", 43_227)),
        (
            "compact_mode_relabeling",
            lambda p: p["variants"]["compact_selector"].__setitem__(
                "adapter_mode", "duplicate_base_preprocessed_selector_v1"
            ),
        ),
        (
            "compact_frontier_overclaim",
            lambda p: p["comparisons"]["compact_vs_two_proof_frontier"].__setitem__(
                "frontier_win_claimed", True
            ),
        ),
        (
            "nanozk_overclaim",
            lambda p: p["comparisons"]["nanozk_boundary"].__setitem__("proof_size_win_claimed", True),
        ),
        (
            "query_fingerprint_drift",
            lambda p: p["variants"]["compact_selector"].__setitem__("record_stream_sha256", "0" * 64),
        ),
        (
            "source_artifact_hash_drift",
            lambda p: p["source_artifacts"][0].__setitem__("sha256", "1" * 64),
        ),
        ("payload_commitment_drift", lambda p: p.__setitem__("payload_commitment", "blake2b-256:" + "2" * 64)),
    ]


def to_tsv(payload: dict[str, Any], context: dict[str, Any]) -> str:
    validate_payload(payload, context=context)
    row = {
        "decision": payload["decision"],
        "result": payload["result"],
        **payload["summary"],
    }
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, extrasaction="ignore", delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue()


def write_bytes_atomic(path: pathlib.Path, data: bytes, label: str) -> None:
    try:
        route_gate.attribution_gate.write_bytes_atomic(path, data, label)
    except route_gate.attribution_gate.MlpFusionAttributionError as err:
        raise SourceBackedAdapterSelectorError(str(err)) from err


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    context = build_context()
    payload = build_payload(context)
    if args.write_json:
        write_bytes_atomic(
            args.write_json,
            (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"),
            "source-backed adapter selector JSON",
        )
    if args.write_tsv:
        write_bytes_atomic(args.write_tsv, to_tsv(payload, context).encode("utf-8"), "source-backed adapter selector TSV")
    print(json.dumps({"schema": SCHEMA, "result": RESULT, "compact_typed_bytes": payload["summary"]["compact_typed_bytes"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
