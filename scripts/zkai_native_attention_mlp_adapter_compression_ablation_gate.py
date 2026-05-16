#!/usr/bin/env python3
"""Gate the native attention+MLP adapter-compression ablation."""

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

CURRENT_GATE_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-2026-05.json"
CURRENT_ACCOUNTING_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json"
)
JSON_OUT = (
    EVIDENCE_DIR
    / "zkai-native-attention-mlp-adapter-compression-ablation-2026-05.json"
)
TSV_OUT = (
    EVIDENCE_DIR
    / "zkai-native-attention-mlp-adapter-compression-ablation-2026-05.tsv"
)

SCHEMA = "zkai-native-attention-mlp-adapter-compression-ablation-gate-v1"
DECISION = "NARROW_CLAIM_COMPACT_BASE_ADAPTER_ABLATION"
RESULT = "GO_STRUCTURAL_SAVING_NO_GO_FRONTIER_REPLACEMENT"
ISSUE = "https://github.com/omarespejel/provable-transformer-vm/issues/631"
PAYLOAD_DOMAIN = "ptvm:zkai:native-attention-mlp-adapter-compression-ablation:v1"
CLAIM_BOUNDARY = (
    "COMPACT_BASE_ADAPTER_ABLATION_FOR_THE_D8_ATTENTION_TO_D128_MLP_NATIVE_ROUTE_"
    "WITHOUT_REPLACING_THE_CURRENT_FRONTIER_OR_CLAIMING_NANOZK_COMPARABILITY"
)

WIDTH = 128
TWO_PROOF_TYPED_BYTES = 40_700
NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900
MAX_JSON_BYTES = 16 * 1024 * 1024

CURRENT_EXPECTED = {
    "schema": "zkai-native-attention-mlp-single-proof-object-gate-v1",
    "decision": "GO_NATIVE_ATTENTION_MLP_SINGLE_STWO_PROOF_OBJECT_VERIFIES",
    "result": "NARROW_CLAIM_NATIVE_ADAPTER_AIR_VERIFIES_WITH_TYPED_SIZE_COST",
    "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-native-adapter-v1",
    "statement_version": "zkai-native-attention-mlp-single-proof-object-native-adapter-statement-v1",
    "adapter_status": "NATIVE_AIR_PROVEN_ATTENTION_OUTPUT_TO_D128_INPUT_ADAPTER",
    "native_adapter_air_proven": True,
    "adapter_row_count": WIDTH,
    "adapter_value_columns": 9,
    "adapter_remainder_bit_columns": 3,
    "adapter_trace_cells": 1_536,
    "single_proof_json_bytes": 119_790,
    "single_proof_typed_bytes": 41_932,
    "single_envelope_bytes": 1_253_874,
    "two_proof_frontier_typed_bytes": TWO_PROOF_TYPED_BYTES,
}

EXPECTED_SOURCE_ARTIFACTS = {
    "current_single_proof_gate": {
        "path": "docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.json",
        "sha256": "7e68dac61d177b61b98468d1ad788756af7e06890585fa726fa3a5fdfbaade4c",
        "payload_sha256": "5d09a1afd4c6926932b7c9a4234dcd10c893ab11fff14f1d72188b381dcd5d34",
    },
    "current_single_proof_binary_accounting": {
        "path": "docs/engineering/evidence/zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json",
        "sha256": "96073160916177a2dad18aff8b85616774cac60bdc8734f50d59848c315bdb9a",
        "payload_sha256": "a8a6a23e3fb08223a8ca631095d89ccc26c69d8930ec77fde9d69e8b940f1189",
    },
}

GROUP_KEYS = (
    "fixed_overhead",
    "fri_decommitments",
    "fri_samples",
    "oods_samples",
    "queries_values",
    "trace_decommitments",
)

VARIANTS = (
    {
        "id": "current_duplicate_adapter_v1_frontier",
        "status": "CURRENT_FRONTIER_DO_NOT_REPLACE_IN_THIS_GATE",
        "proof_backend_version": CURRENT_EXPECTED["proof_backend_version"],
        "statement_version": CURRENT_EXPECTED["statement_version"],
        "adapter_base_trace_columns": 12,
        "adapter_preprocessed_columns": 12,
        "adapter_trace_cells": 1_536,
        "proof_json_bytes": 119_790,
        "envelope_bytes": 1_253_874,
        "typed_bytes": 41_932,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 13_184,
            "fri_samples": 800,
            "oods_samples": 12_240,
            "queries_values": 9_132,
            "trace_decommitments": 6_528,
        },
        "frontier_safe": True,
        "notes": "checked current route; native adapter is duplicated in base and preprocessed traces",
    },
    {
        "id": "compact_base_legacy_label_microprobe",
        "status": "LOCAL_ABLATION_GO_BUT_LABEL_NOT_BUMPED",
        "proof_backend_version": CURRENT_EXPECTED["proof_backend_version"],
        "statement_version": CURRENT_EXPECTED["statement_version"],
        "adapter_base_trace_columns": 8,
        "adapter_preprocessed_columns": 12,
        "adapter_trace_cells": 1_024,
        "proof_json_bytes": 117_416,
        "envelope_bytes": 1_234_882,
        "typed_bytes": 41_228,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 12_736,
            "fri_samples": 784,
            "oods_samples": 12_176,
            "queries_values": 9_084,
            "trace_decommitments": 6_400,
        },
        "frontier_safe": False,
        "notes": "local compact-base probe under legacy labels; useful for mechanism, not safe as a published frontier",
    },
    {
        "id": "duplicate_adapter_v2_label_control",
        "status": "LOCAL_LABEL_CONTROL",
        "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-duplicate-adapter-v2",
        "statement_version": "zkai-native-attention-mlp-single-proof-object-duplicate-adapter-statement-v2",
        "adapter_base_trace_columns": 12,
        "adapter_preprocessed_columns": 12,
        "adapter_trace_cells": 1_536,
        "proof_json_bytes": 124_492,
        "envelope_bytes": 1_291_514,
        "typed_bytes": 43_228,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 14_176,
            "fri_samples": 848,
            "oods_samples": 12_240,
            "queries_values": 9_132,
            "trace_decommitments": 6_784,
        },
        "frontier_safe": False,
        "notes": "duplicate adapter with bumped labels; controls for transcript-label drift",
    },
    {
        "id": "compact_base_v2_referenced_fixed_columns",
        "status": "LOCAL_ABLATION_GO_STRUCTURAL_SAVING_BUT_NOT_FRONTIER",
        "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-compact-adapter-v1",
        "statement_version": "zkai-native-attention-mlp-single-proof-object-compact-adapter-statement-v1",
        "adapter_base_trace_columns": 8,
        "adapter_preprocessed_columns": 12,
        "adapter_trace_cells": 1_024,
        "proof_json_bytes": 121_841,
        "envelope_bytes": 1_270_449,
        "typed_bytes": 42_492,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 13_696,
            "fri_samples": 832,
            "oods_samples": 12_176,
            "queries_values": 9_084,
            "trace_decommitments": 6_656,
        },
        "frontier_safe": False,
        "notes": "compact base with deterministic fixed columns still referenced by the AIR evaluator",
    },
    {
        "id": "compact_base_v2_unconstrained_fixed_columns",
        "status": "LOCAL_ABLATION_NO_GO_WEAKER_SAVING",
        "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-compact-adapter-v1",
        "statement_version": "zkai-native-attention-mlp-single-proof-object-compact-adapter-statement-v1",
        "adapter_base_trace_columns": 8,
        "adapter_preprocessed_columns": 12,
        "adapter_trace_cells": 1_024,
        "proof_json_bytes": 124_192,
        "envelope_bytes": 1_289_257,
        "typed_bytes": 43_116,
        "grouped": {
            "fixed_overhead": 48,
            "fri_decommitments": 14_176,
            "fri_samples": 848,
            "oods_samples": 12_176,
            "queries_values": 9_084,
            "trace_decommitments": 6_784,
        },
        "frontier_safe": False,
        "notes": "reading fixed columns without zero constraints verifies but gives weaker savings",
    },
)

NON_CLAIMS = (
    "not a replacement for the current native attention+MLP frontier",
    "not proof that compact-base adapter is always smaller after label changes",
    "not a NANOZK proof-size win",
    "not a matched NANOZK workload or benchmark",
    "not a full transformer block proof",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_native_attention_mlp_adapter_compression_ablation_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-adapter-compression-ablation-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-adapter-compression-ablation-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_attention_mlp_adapter_compression_ablation_gate.py scripts/tests/test_zkai_native_attention_mlp_adapter_compression_ablation_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_adapter_compression_ablation_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "claim_boundary",
    "source_artifacts",
    "variants",
    "deltas",
    "summary",
    "interpretation",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = (
    "variant_id",
    "status",
    "typed_bytes",
    "proof_json_bytes",
    "envelope_bytes",
    "adapter_base_trace_columns",
    "adapter_trace_cells",
    "typed_delta_vs_current_frontier",
    "typed_delta_vs_label_control",
    "gap_to_two_proof_typed_bytes",
    "gap_to_nanozk_reported_bytes",
    "frontier_safe",
)


class AdapterCompressionAblationError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AdapterCompressionAblationError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    digest = hashlib.blake2b(digest_size=32)
    digest.update(PAYLOAD_DOMAIN.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(material))
    return "blake2b-256:" + digest.hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdapterCompressionAblationError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AdapterCompressionAblationError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AdapterCompressionAblationError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AdapterCompressionAblationError(f"{label} must be boolean")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AdapterCompressionAblationError(f"{label} must be non-empty string")
    return value


def read_json(path: pathlib.Path, label: str) -> tuple[dict[str, Any], bytes]:
    resolved = path.resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    if evidence_root not in resolved.parents and resolved != evidence_root:
        raise AdapterCompressionAblationError(f"{label} path must stay under docs/engineering/evidence")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as err:
        raise AdapterCompressionAblationError(f"failed to open {label} {path}: {err}") from err
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise AdapterCompressionAblationError(f"{label} must be a regular file")
        if before.st_size > MAX_JSON_BYTES:
            raise AdapterCompressionAblationError(f"{label} exceeds max size")
        chunks: list[bytes] = []
        remaining = MAX_JSON_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_JSON_BYTES:
            raise AdapterCompressionAblationError(f"{label} exceeds max size")
        after = os.fstat(fd)
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise AdapterCompressionAblationError(f"{label} changed while reading")
    finally:
        os.close(fd)
    try:
        payload = json.loads(
            raw,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                AdapterCompressionAblationError(f"{label} contains non-finite JSON constant {constant}")
            ),
        )
    except json.JSONDecodeError as err:
        raise AdapterCompressionAblationError(f"failed to parse {label}: {err}") from err
    return _dict(payload, label), raw


def source_artifact(artifact_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def load_sources() -> dict[str, Any]:
    gate, gate_raw = read_json(CURRENT_GATE_PATH, "current single proof gate")
    accounting, accounting_raw = read_json(CURRENT_ACCOUNTING_PATH, "current single proof accounting")
    return {
        "gate": gate,
        "accounting": accounting,
        "source_artifacts": [
            source_artifact("current_single_proof_gate", CURRENT_GATE_PATH, gate, gate_raw),
            source_artifact(
                "current_single_proof_binary_accounting",
                CURRENT_ACCOUNTING_PATH,
                accounting,
                accounting_raw,
            ),
        ],
    }


def validate_current_sources(sources: dict[str, Any]) -> None:
    gate = _dict(sources["gate"], "current single proof gate")
    summary = _dict(gate.get("summary"), "current single proof summary")
    routes = _dict(gate.get("routes"), "current single proof routes")
    adapter_route = _dict(routes.get("adapter_boundary"), "adapter route")
    native_route = _dict(routes.get("native_single_proof_object"), "native single proof route")
    artifacts: dict[str, dict[str, Any]] = {}
    for index, artifact_value in enumerate(_list(sources.get("source_artifacts"), "source artifacts")):
        artifact = _dict(artifact_value, f"source artifact {index}")
        artifact_id = _str(artifact.get("id"), "source artifact id")
        if artifact_id in artifacts:
            raise AdapterCompressionAblationError(f"duplicate source artifact id {artifact_id}")
        artifacts[artifact_id] = artifact
    if set(artifacts) != set(EXPECTED_SOURCE_ARTIFACTS):
        raise AdapterCompressionAblationError("source artifact inventory drift")
    for artifact_id, expected_artifact in EXPECTED_SOURCE_ARTIFACTS.items():
        artifact = _dict(artifacts[artifact_id], f"{artifact_id} artifact")
        if artifact != {"id": artifact_id, **expected_artifact}:
            raise AdapterCompressionAblationError(f"{artifact_id} hash drift")
    for key, expected in CURRENT_EXPECTED.items():
        if key in {"schema", "decision", "result"}:
            actual = gate.get(key)
        elif key in {"proof_backend_version", "statement_version"}:
            actual = native_route.get(key)
        else:
            actual = summary.get(key)
        if actual != expected:
            raise AdapterCompressionAblationError(f"current source {key} drift")
    if adapter_route.get("native_adapter_air_proven") is not True:
        raise AdapterCompressionAblationError("adapter route native AIR proof drift")
    for key in (
        "adapter_status",
        "adapter_row_count",
        "adapter_value_columns",
        "adapter_remainder_bit_columns",
        "adapter_trace_cells",
    ):
        if adapter_route.get(key) != summary.get(key):
            raise AdapterCompressionAblationError(f"adapter route {key} mismatch")

    accounting = _dict(sources["accounting"], "current accounting")
    rows = _list(accounting.get("rows"), "current accounting rows")
    if len(rows) != 1:
        raise AdapterCompressionAblationError("current accounting row count drift")
    row = _dict(rows[0], "current accounting row")
    local = _dict(row.get("local_binary_accounting"), "current local accounting")
    grouped = _dict(local.get("grouped_reconstruction"), "current grouped accounting")
    current = VARIANTS[0]
    if row.get("proof_json_size_bytes") != current["proof_json_bytes"]:
        raise AdapterCompressionAblationError("current accounting proof JSON drift")
    if local.get("component_sum_bytes") != current["typed_bytes"]:
        raise AdapterCompressionAblationError("current accounting typed bytes drift")
    if grouped != current["grouped"]:
        raise AdapterCompressionAblationError("current grouped accounting drift")


def enrich_variants() -> list[dict[str, Any]]:
    current_typed = VARIANTS[0]["typed_bytes"]
    label_control_typed = VARIANTS[2]["typed_bytes"]
    result = []
    for variant in VARIANTS:
        grouped = _dict(variant["grouped"], f"{variant['id']} grouped")
        if sum(_int(grouped[key], f"{variant['id']} {key}") for key in GROUP_KEYS) != variant["typed_bytes"]:
            raise AdapterCompressionAblationError(f"{variant['id']} grouped bytes do not sum")
        item = copy.deepcopy(variant)
        typed = _int(item["typed_bytes"], f"{variant['id']} typed bytes")
        item["typed_delta_vs_current_frontier"] = typed - current_typed
        item["typed_delta_vs_label_control"] = typed - label_control_typed
        item["gap_to_two_proof_typed_bytes"] = typed - TWO_PROOF_TYPED_BYTES
        item["gap_to_nanozk_reported_bytes"] = typed - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES
        item["typed_ratio_vs_two_proof"] = round(typed / TWO_PROOF_TYPED_BYTES, 6)
        item["typed_ratio_vs_nanozk_reported"] = round(typed / NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES, 6)
        result.append(item)
    return result


def variant_by_id(variants: list[dict[str, Any]], variant_id: str) -> dict[str, Any]:
    for variant in variants:
        if variant["id"] == variant_id:
            return variant
    raise AdapterCompressionAblationError(f"missing variant {variant_id}")


def build_payload() -> dict[str, Any]:
    sources = load_sources()
    validate_current_sources(sources)
    variants = enrich_variants()
    current = variant_by_id(variants, "current_duplicate_adapter_v1_frontier")
    legacy = variant_by_id(variants, "compact_base_legacy_label_microprobe")
    label_control = variant_by_id(variants, "duplicate_adapter_v2_label_control")
    compact_v2 = variant_by_id(variants, "compact_base_v2_referenced_fixed_columns")
    weak_v2 = variant_by_id(variants, "compact_base_v2_unconstrained_fixed_columns")

    deltas = {
        "legacy_microprobe_typed_saving_vs_current_bytes": current["typed_bytes"] - legacy["typed_bytes"],
        "legacy_microprobe_json_saving_vs_current_bytes": current["proof_json_bytes"] - legacy["proof_json_bytes"],
        "legacy_microprobe_recovered_current_overhead_share": round(
            (current["typed_bytes"] - legacy["typed_bytes"])
            / (current["typed_bytes"] - TWO_PROOF_TYPED_BYTES),
            6,
        ),
        "legacy_microprobe_remaining_gap_to_two_proof_bytes": legacy["typed_bytes"] - TWO_PROOF_TYPED_BYTES,
        "v2_compact_typed_saving_vs_duplicate_label_control_bytes": (
            label_control["typed_bytes"] - compact_v2["typed_bytes"]
        ),
        "v2_compact_json_saving_vs_duplicate_label_control_bytes": (
            label_control["proof_json_bytes"] - compact_v2["proof_json_bytes"]
        ),
        "v2_compact_trace_cell_saving_vs_duplicate_label_control": (
            label_control["adapter_trace_cells"] - compact_v2["adapter_trace_cells"]
        ),
        "v2_unconstrained_fixed_column_typed_regression_vs_referenced_bytes": (
            weak_v2["typed_bytes"] - compact_v2["typed_bytes"]
        ),
        "current_frontier_gap_to_two_proof_bytes": current["typed_bytes"] - TWO_PROOF_TYPED_BYTES,
        "current_frontier_gap_to_nanozk_reported_bytes": (
            current["typed_bytes"] - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES
        ),
        "best_safe_frontier_replacement_typed_bytes": current["typed_bytes"],
        "best_local_ablation_typed_bytes": legacy["typed_bytes"],
    }
    summary = {
        "current_frontier_typed_bytes": current["typed_bytes"],
        "current_frontier_proof_json_bytes": current["proof_json_bytes"],
        "compact_base_legacy_microprobe_typed_bytes": legacy["typed_bytes"],
        "compact_base_legacy_microprobe_saving_bytes": (
            current["typed_bytes"] - legacy["typed_bytes"]
        ),
        "compact_base_v2_typed_bytes": compact_v2["typed_bytes"],
        "duplicate_adapter_v2_label_control_typed_bytes": label_control["typed_bytes"],
        "compact_base_v2_saving_vs_label_control_bytes": (
            label_control["typed_bytes"] - compact_v2["typed_bytes"]
        ),
        "compact_base_reduces_adapter_trace_cells": True,
        "frontier_replacement_status": "NO_GO_TRANSCRIPT_STABLE_FRONTIER_NOT_ESTABLISHED",
        "nanozk_win_claimed": False,
        "next_attack": "make proof-size measurement transcript-stable, then retry compact adapter or reduce query/opening pressure",
    }
    interpretation = {
        "human_result": (
            "Compact-base adapter representation is a real structural lead: it cuts adapter base trace cells "
            "from 1536 to 1024 and saved 736 typed bytes against the duplicate-adapter v2 label control. "
            "It is not yet a new frontier because the existing checked artifact remains 41932 typed bytes."
        ),
        "why_not_promoted": (
            "Changing statement/version labels changes Fiat-Shamir query positions and Merkle path overlap, "
            "so the ablation must be treated as mechanism evidence until a transcript-stable benchmark is added."
        ),
        "research_decision": (
            "Continue attacking adapter compression, but first add a stable comparison harness that prevents "
            "metadata churn from looking like proof-size progress."
        ),
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": sources["source_artifacts"],
        "variants": variants,
        "deltas": deltas,
        "summary": summary,
        "interpretation": interpretation,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_payload(payload: Any) -> None:
    data = _dict(payload, "payload")
    if set(data) not in (CORE_KEYS, FINAL_KEYS):
        raise AdapterCompressionAblationError("payload key set drift")
    if data.get("schema") != SCHEMA:
        raise AdapterCompressionAblationError("schema drift")
    if data.get("decision") != DECISION:
        raise AdapterCompressionAblationError("decision drift")
    if data.get("result") != RESULT:
        raise AdapterCompressionAblationError("result drift")
    if data.get("issue") != ISSUE:
        raise AdapterCompressionAblationError("issue drift")
    if data.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AdapterCompressionAblationError("claim boundary drift")
    if data.get("non_claims") != list(NON_CLAIMS):
        raise AdapterCompressionAblationError("non-claims drift")
    if data.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise AdapterCompressionAblationError("validation commands drift")
    variants = _list(data.get("variants"), "variants")
    if len(variants) != len(VARIANTS):
        raise AdapterCompressionAblationError("variant count drift")
    expected = build_payload()
    for key in CORE_KEYS - {"payload_commitment"}:
        if data.get(key) != expected.get(key):
            raise AdapterCompressionAblationError(f"{key} drift")
    summary = _dict(data.get("summary"), "summary")
    if _bool(summary.get("nanozk_win_claimed"), "NANOZK win claimed") is not False:
        raise AdapterCompressionAblationError("NANOZK overclaim")
    if summary.get("frontier_replacement_status") != "NO_GO_TRANSCRIPT_STABLE_FRONTIER_NOT_ESTABLISHED":
        raise AdapterCompressionAblationError("frontier replacement overclaim")
    deltas = _dict(data.get("deltas"), "deltas")
    if _int(deltas.get("legacy_microprobe_remaining_gap_to_two_proof_bytes"), "remaining gap") != 528:
        raise AdapterCompressionAblationError("remaining gap drift")
    if _int(deltas.get("v2_compact_typed_saving_vs_duplicate_label_control_bytes"), "v2 saving") != 736:
        raise AdapterCompressionAblationError("v2 compact saving drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise AdapterCompressionAblationError("payload commitment drift")
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(MUTATION_NAMES):
            raise AdapterCompressionAblationError("mutation inventory drift")
        if data.get("case_count") != len(MUTATION_NAMES) or len(cases) != len(MUTATION_NAMES):
            raise AdapterCompressionAblationError("mutation case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AdapterCompressionAblationError("not all mutations rejected")
        for expected_name, case_value in zip(MUTATION_NAMES, cases, strict=True):
            case = _dict(case_value, "mutation case")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AdapterCompressionAblationError("mutation case field drift")
            if case.get("name") != expected_name:
                raise AdapterCompressionAblationError("mutation case order drift")
            if case.get("accepted") is not False:
                raise AdapterCompressionAblationError("mutation accepted")
            if case.get("rejected") is not True:
                raise AdapterCompressionAblationError("mutation not rejected")


MutationFn = Callable[[dict[str, Any]], None]


def _payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "blake2b-256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("result_promoted_to_frontier", lambda p: p.__setitem__("result", "GO_NEW_FRONTIER"), True),
    (
        "frontier_replacement_promoted",
        lambda p: p["summary"].__setitem__("frontier_replacement_status", "GO_REPLACE_FRONTIER"),
        True,
    ),
    (
        "nanozk_win_promoted",
        lambda p: p["summary"].__setitem__("nanozk_win_claimed", True),
        True,
    ),
    (
        "remaining_gap_erased",
        lambda p: p["deltas"].__setitem__("legacy_microprobe_remaining_gap_to_two_proof_bytes", 0),
        True,
    ),
    (
        "v2_compact_saving_inflated",
        lambda p: p["deltas"].__setitem__("v2_compact_typed_saving_vs_duplicate_label_control_bytes", 4096),
        True,
    ),
    (
        "legacy_probe_marked_frontier_safe",
        lambda p: p["variants"][1].__setitem__("frontier_safe", True),
        True,
    ),
    (
        "label_control_removed",
        lambda p: p.__setitem__("variants", [variant for variant in p["variants"] if variant["id"] != "duplicate_adapter_v2_label_control"]),
        True,
    ),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "22" * 32), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", _payload_commitment_drift, False),
)

MUTATION_NAMES = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutations(core: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core)
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated)
        except AdapterCompressionAblationError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result() -> dict[str, Any]:
    core = build_payload()
    cases = run_mutations(core)
    final = copy.deepcopy(core)
    final["mutation_inventory"] = list(MUTATION_NAMES)
    final["cases"] = cases
    final["case_count"] = len(cases)
    final["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    refresh_payload_commitment(final)
    validate_payload(final)
    return final


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for variant in payload["variants"]:
        row = {key: variant[key] for key in TSV_COLUMNS if key != "variant_id"}
        row["variant_id"] = variant["id"]
        writer.writerow(row)
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    if path is None:
        return None
    candidate = ROOT / path if not path.is_absolute() else path
    resolved_parent = candidate.parent.resolve()
    resolved = resolved_parent / candidate.name
    evidence_root = EVIDENCE_DIR.resolve()
    if evidence_root not in resolved.parents:
        raise AdapterCompressionAblationError("output path must stay under docs/engineering/evidence")
    if resolved.suffix != suffix:
        raise AdapterCompressionAblationError(f"output path must end with {suffix}")
    return resolved


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    if path.exists() and path.is_symlink():
        raise AdapterCompressionAblationError("refusing to write through symlink")
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_path = parent / f".{path.name}.tmp-{os.getpid()}"
    try:
        with open(temp_path, "x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        parent_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    out_json = require_output_path(json_path, ".json")
    out_tsv = require_output_path(tsv_path, ".tsv")
    if out_json is not None:
        write_text_atomic(out_json, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    if out_tsv is not None:
        write_text_atomic(out_tsv, to_tsv(payload))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
