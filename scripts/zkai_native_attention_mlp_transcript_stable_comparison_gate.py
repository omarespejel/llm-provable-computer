#!/usr/bin/env python3
"""Gate transcript-stable native attention+MLP proof-size comparisons."""

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
import tempfile
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

ABLATION_PATH = (
    EVIDENCE_DIR
    / "zkai-native-attention-mlp-adapter-compression-ablation-2026-05.json"
)
CURRENT_GATE_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-2026-05.json"
CURRENT_ENVELOPE_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-2026-05.envelope.json"
)
CURRENT_ACCOUNTING_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json"
)
JSON_OUT = (
    EVIDENCE_DIR
    / "zkai-native-attention-mlp-transcript-stable-comparison-2026-05.json"
)
TSV_OUT = (
    EVIDENCE_DIR
    / "zkai-native-attention-mlp-transcript-stable-comparison-2026-05.tsv"
)

SCHEMA = "zkai-native-attention-mlp-transcript-stable-comparison-gate-v1"
DECISION = "NO_GO_TRANSCRIPT_STABLE_FRONTIER_PROMOTION"
RESULT = "NARROW_CLAIM_ADAPTER_COMPRESSION_REQUIRES_TRANSCRIPT_STABLE_REPROVE"
ISSUE = "https://github.com/omarespejel/provable-transformer-vm/issues/633"
PAYLOAD_DOMAIN = "ptvm:zkai:native-attention-mlp-transcript-stable-comparison:v1"
CLAIM_BOUNDARY = (
    "TRANSCRIPT_STABLE_NATIVE_PROOF_SIZE_COMPARISON_FOR_D8_ATTENTION_TO_D128_MLP_"
    "ADAPTER_ABLATION_WITHOUT_PROMOTING_A_NEW_FRONTIER"
)

MAX_JSON_BYTES = 16 * 1024 * 1024
NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900
CURRENT_FRONTIER_TYPED_BYTES = 41_932
TWO_PROOF_FRONTIER_TYPED_BYTES = 40_700

GROUP_KEYS = (
    "fixed_overhead",
    "fri_decommitments",
    "fri_samples",
    "oods_samples",
    "queries_values",
    "trace_decommitments",
)
TRANSCRIPT_PATH_SENSITIVE_GROUPS = (
    "fri_decommitments",
    "fri_samples",
    "trace_decommitments",
)
DIRECT_OPENING_VALUE_GROUPS = ("oods_samples", "queries_values")

EXPECTED_SOURCE_ARTIFACTS = {
    "adapter_compression_ablation_gate": {
        "path": "docs/engineering/evidence/zkai-native-attention-mlp-adapter-compression-ablation-2026-05.json",
        "sha256": "0c32d160278a365f8a4b44e22109a0dfcf10e853782833c851258a2692a31edd",
        "payload_sha256": "2e327f8cf3bebc063249805d0e34a2e0674214fe5daaa3439174bcf22c99e33a",
    },
    "current_single_proof_gate": {
        "path": "docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.json",
        "sha256": "7e68dac61d177b61b98468d1ad788756af7e06890585fa726fa3a5fdfbaade4c",
        "payload_sha256": "5d09a1afd4c6926932b7c9a4234dcd10c893ab11fff14f1d72188b381dcd5d34",
    },
    "current_single_proof_envelope": {
        "path": "docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.envelope.json",
        "sha256": "f3391f213531957e1dc0522e2415b3783b9e0eb759c1a52f17b1415cfe4e7585",
        "payload_sha256": "ddc64327e48d99a161a9f1a7221ed21a5d425b886567ae33ab5b4fb39ee3990f",
    },
    "current_single_proof_binary_accounting": {
        "path": "docs/engineering/evidence/zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json",
        "sha256": "96073160916177a2dad18aff8b85616774cac60bdc8734f50d59848c315bdb9a",
        "payload_sha256": "a8a6a23e3fb08223a8ca631095d89ccc26c69d8930ec77fde9d69e8b940f1189",
    },
}

EXPECTED_ABLATION = {
    "schema": "zkai-native-attention-mlp-adapter-compression-ablation-gate-v1",
    "decision": "NARROW_CLAIM_COMPACT_BASE_ADAPTER_ABLATION",
    "result": "GO_STRUCTURAL_SAVING_NO_GO_FRONTIER_REPLACEMENT",
    "frontier_replacement_status": "NO_GO_TRANSCRIPT_STABLE_FRONTIER_NOT_ESTABLISHED",
    "current_frontier_typed_bytes": CURRENT_FRONTIER_TYPED_BYTES,
    "compact_base_legacy_microprobe_saving_bytes": 704,
    "compact_base_v2_saving_vs_label_control_bytes": 736,
    "nanozk_win_claimed": False,
}

EXPECTED_CURRENT = {
    "single_proof_typed_bytes": CURRENT_FRONTIER_TYPED_BYTES,
    "single_proof_json_bytes": 119_790,
    "single_envelope_bytes": 1_253_874,
    "two_proof_frontier_typed_bytes": TWO_PROOF_FRONTIER_TYPED_BYTES,
    "native_adapter_air_proven": True,
    "adapter_trace_cells": 1_536,
    "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-native-adapter-v1",
    "statement_version": "zkai-native-attention-mlp-single-proof-object-native-adapter-statement-v1",
    "statement_commitment": "blake2b-256:7f036766bfe353a4d307c0deb1ff79006ad8be9081c43a6dea40ceeaa9353252",
    "public_instance_commitment": "blake2b-256:9fe7df13461e44d2694e657d8e80b6cedda175b40029f45c5e92b86af18bfa50",
    "record_stream_sha256": "4f1b230afc4f7fec71ce632faa2b0b9512276467aa9dd05f48cd1fba4ba581f4",
}

PAIR_SPECS = (
    (
        "legacy_microprobe_vs_current_frontier",
        "current_duplicate_adapter_v1_frontier",
        "compact_base_legacy_label_microprobe",
    ),
    (
        "compact_base_v2_vs_duplicate_label_control",
        "duplicate_adapter_v2_label_control",
        "compact_base_v2_referenced_fixed_columns",
    ),
    (
        "unconstrained_compact_v2_vs_duplicate_label_control",
        "duplicate_adapter_v2_label_control",
        "compact_base_v2_unconstrained_fixed_columns",
    ),
    (
        "referenced_compact_v2_vs_unconstrained_compact_v2",
        "compact_base_v2_unconstrained_fixed_columns",
        "compact_base_v2_referenced_fixed_columns",
    ),
)

NON_CLAIMS = (
    "not a promoted native attention+MLP frontier",
    "not a transcript-stable compact-adapter proof-size win",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not timing evidence",
    "not a full transformer block proof",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_native_attention_mlp_transcript_stable_comparison_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-transcript-stable-comparison-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-transcript-stable-comparison-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_attention_mlp_transcript_stable_comparison_gate.py scripts/tests/test_zkai_native_attention_mlp_transcript_stable_comparison_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_transcript_stable_comparison_gate",
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
    "stability_policy",
    "variant_inventory",
    "comparisons",
    "summary",
    "interpretation",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = (
    "comparison_id",
    "baseline_variant_id",
    "candidate_variant_id",
    "typed_saving_bytes",
    "json_saving_bytes",
    "direct_opening_value_saving_bytes",
    "transcript_path_sensitive_saving_bytes",
    "transcript_path_sensitive_share",
    "proof_backend_versions_equal",
    "statement_versions_equal",
    "baseline_artifact_backed",
    "candidate_artifact_backed",
    "transcript_stable_for_promotion",
    "promotion_status",
)


class TranscriptStableComparisonError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise TranscriptStableComparisonError(f"invalid JSON value: {err}") from err


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
        raise TranscriptStableComparisonError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TranscriptStableComparisonError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TranscriptStableComparisonError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise TranscriptStableComparisonError(f"{label} must be boolean")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TranscriptStableComparisonError(f"{label} must be non-empty string")
    return value


def read_json(path: pathlib.Path, label: str) -> tuple[dict[str, Any], bytes]:
    resolved = path.resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    if evidence_root not in resolved.parents and resolved != evidence_root:
        raise TranscriptStableComparisonError(f"{label} path must stay under docs/engineering/evidence")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as err:
        raise TranscriptStableComparisonError(f"failed to open {label} {path}: {err}") from err
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise TranscriptStableComparisonError(f"{label} must be a regular file")
        if before.st_size > MAX_JSON_BYTES:
            raise TranscriptStableComparisonError(f"{label} exceeds max size")
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
            raise TranscriptStableComparisonError(f"{label} exceeds max size")
        after = os.fstat(fd)
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise TranscriptStableComparisonError(f"{label} changed while reading")
    finally:
        os.close(fd)
    try:
        payload = json.loads(
            raw,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                TranscriptStableComparisonError(f"{label} contains non-finite JSON constant {constant}")
            ),
        )
    except json.JSONDecodeError as err:
        raise TranscriptStableComparisonError(f"failed to parse {label}: {err}") from err
    return _dict(payload, label), raw


def source_artifact(artifact_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def load_sources() -> dict[str, Any]:
    ablation, ablation_raw = read_json(ABLATION_PATH, "adapter compression ablation")
    gate, gate_raw = read_json(CURRENT_GATE_PATH, "current single proof gate")
    envelope, envelope_raw = read_json(CURRENT_ENVELOPE_PATH, "current single proof envelope")
    accounting, accounting_raw = read_json(CURRENT_ACCOUNTING_PATH, "current single proof accounting")
    return {
        "ablation": ablation,
        "gate": gate,
        "envelope": envelope,
        "accounting": accounting,
        "source_artifacts": [
            source_artifact("adapter_compression_ablation_gate", ABLATION_PATH, ablation, ablation_raw),
            source_artifact("current_single_proof_gate", CURRENT_GATE_PATH, gate, gate_raw),
            source_artifact("current_single_proof_envelope", CURRENT_ENVELOPE_PATH, envelope, envelope_raw),
            source_artifact(
                "current_single_proof_binary_accounting",
                CURRENT_ACCOUNTING_PATH,
                accounting,
                accounting_raw,
            ),
        ],
    }


def validate_source_artifacts(sources: dict[str, Any]) -> None:
    artifacts: dict[str, dict[str, Any]] = {}
    for index, artifact_value in enumerate(_list(sources.get("source_artifacts"), "source artifacts")):
        artifact = _dict(artifact_value, f"source artifact {index}")
        artifact_id = _str(artifact.get("id"), "source artifact id")
        if artifact_id in artifacts:
            raise TranscriptStableComparisonError(f"duplicate source artifact id {artifact_id}")
        artifacts[artifact_id] = artifact
    if set(artifacts) != set(EXPECTED_SOURCE_ARTIFACTS):
        raise TranscriptStableComparisonError("source artifact inventory drift")
    for artifact_id, expected in EXPECTED_SOURCE_ARTIFACTS.items():
        if artifacts[artifact_id] != {"id": artifact_id, **expected}:
            raise TranscriptStableComparisonError(f"{artifact_id} hash drift")


def validate_sources(sources: dict[str, Any]) -> None:
    validate_source_artifacts(sources)

    ablation = _dict(sources.get("ablation"), "ablation")
    summary = _dict(ablation.get("summary"), "ablation summary")
    deltas = _dict(ablation.get("deltas"), "ablation deltas")
    for key in ("schema", "decision", "result"):
        if ablation.get(key) != EXPECTED_ABLATION[key]:
            raise TranscriptStableComparisonError(f"ablation {key} drift")
    if summary.get("frontier_replacement_status") != EXPECTED_ABLATION["frontier_replacement_status"]:
        raise TranscriptStableComparisonError("ablation frontier status drift")
    if summary.get("current_frontier_typed_bytes") != EXPECTED_ABLATION["current_frontier_typed_bytes"]:
        raise TranscriptStableComparisonError("ablation current frontier typed drift")
    if summary.get("compact_base_legacy_microprobe_saving_bytes") != EXPECTED_ABLATION["compact_base_legacy_microprobe_saving_bytes"]:
        raise TranscriptStableComparisonError("ablation legacy saving drift")
    if summary.get("compact_base_v2_saving_vs_label_control_bytes") != EXPECTED_ABLATION["compact_base_v2_saving_vs_label_control_bytes"]:
        raise TranscriptStableComparisonError("ablation label-control saving drift")
    if _bool(summary.get("nanozk_win_claimed"), "ablation nanozk win") is not False:
        raise TranscriptStableComparisonError("ablation NANOZK overclaim drift")
    if deltas.get("v2_compact_typed_saving_vs_duplicate_label_control_bytes") != 736:
        raise TranscriptStableComparisonError("ablation v2 saving delta drift")

    gate = _dict(sources.get("gate"), "current gate")
    gate_summary = _dict(gate.get("summary"), "current gate summary")
    envelope = _dict(sources.get("envelope"), "current envelope")
    envelope_input = _dict(envelope.get("input"), "current envelope input")
    accounting = _dict(sources.get("accounting"), "current accounting")
    rows = _list(accounting.get("rows"), "current accounting rows")
    if len(rows) != 1:
        raise TranscriptStableComparisonError("current accounting row count drift")
    row = _dict(rows[0], "current accounting row")
    local = _dict(row.get("local_binary_accounting"), "current local accounting")
    grouped = _dict(local.get("grouped_reconstruction"), "current grouped accounting")

    if gate_summary.get("single_proof_typed_bytes") != EXPECTED_CURRENT["single_proof_typed_bytes"]:
        raise TranscriptStableComparisonError("current typed bytes drift")
    if gate_summary.get("single_proof_json_bytes") != EXPECTED_CURRENT["single_proof_json_bytes"]:
        raise TranscriptStableComparisonError("current JSON bytes drift")
    if gate_summary.get("native_adapter_air_proven") is not True:
        raise TranscriptStableComparisonError("current adapter AIR proof drift")
    if gate_summary.get("adapter_trace_cells") != EXPECTED_CURRENT["adapter_trace_cells"]:
        raise TranscriptStableComparisonError("current adapter trace cells drift")
    if envelope.get("proof_backend_version") != EXPECTED_CURRENT["proof_backend_version"]:
        raise TranscriptStableComparisonError("current envelope backend version drift")
    if envelope.get("statement_version") != EXPECTED_CURRENT["statement_version"]:
        raise TranscriptStableComparisonError("current envelope statement version drift")
    if envelope_input.get("statement_commitment") != EXPECTED_CURRENT["statement_commitment"]:
        raise TranscriptStableComparisonError("current envelope statement commitment drift")
    if envelope_input.get("public_instance_commitment") != EXPECTED_CURRENT["public_instance_commitment"]:
        raise TranscriptStableComparisonError("current envelope public-instance commitment drift")
    if row.get("proof_json_size_bytes") != EXPECTED_CURRENT["single_proof_json_bytes"]:
        raise TranscriptStableComparisonError("current accounting proof JSON drift")
    if local.get("component_sum_bytes") != EXPECTED_CURRENT["single_proof_typed_bytes"]:
        raise TranscriptStableComparisonError("current accounting typed bytes drift")
    if local.get("record_stream_sha256") != EXPECTED_CURRENT["record_stream_sha256"]:
        raise TranscriptStableComparisonError("current accounting record-stream drift")
    if sum(_int(grouped.get(key), f"current grouped {key}") for key in GROUP_KEYS) != EXPECTED_CURRENT["single_proof_typed_bytes"]:
        raise TranscriptStableComparisonError("current grouped accounting sum drift")


def variant_by_id(variants: list[dict[str, Any]], variant_id: str) -> dict[str, Any]:
    for variant in variants:
        if variant.get("id") == variant_id:
            return variant
    raise TranscriptStableComparisonError(f"missing variant {variant_id}")


def grouped_saving(left: dict[str, Any], right: dict[str, Any], groups: tuple[str, ...]) -> int:
    left_grouped = _dict(left.get("grouped"), f"{left.get('id')} grouped")
    right_grouped = _dict(right.get("grouped"), f"{right.get('id')} grouped")
    return sum(_int(left_grouped.get(group), f"{left.get('id')} {group}") - _int(right_grouped.get(group), f"{right.get('id')} {group}") for group in groups)


def shape_fingerprint(variant: dict[str, Any]) -> str:
    material = {
        "id": variant["id"],
        "proof_backend_version": variant["proof_backend_version"],
        "statement_version": variant["statement_version"],
        "adapter_base_trace_columns": variant["adapter_base_trace_columns"],
        "adapter_preprocessed_columns": variant["adapter_preprocessed_columns"],
        "adapter_trace_cells": variant["adapter_trace_cells"],
        "typed_bytes": variant["typed_bytes"],
        "proof_json_bytes": variant["proof_json_bytes"],
        "grouped": variant["grouped"],
    }
    return "blake2b-256:" + hashlib.blake2b(canonical_json_bytes(material), digest_size=32).hexdigest()


def variant_inventory(sources: dict[str, Any]) -> list[dict[str, Any]]:
    ablation = _dict(sources["ablation"], "ablation")
    envelope = _dict(sources["envelope"], "current envelope")
    envelope_input = _dict(envelope.get("input"), "current envelope input")
    accounting = _dict(sources["accounting"], "current accounting")
    rows = _list(accounting.get("rows"), "current accounting rows")
    if len(rows) != 1:
        raise TranscriptStableComparisonError("current accounting row count drift")
    row = _dict(rows[0], "current accounting row")
    local_accounting = _dict(row.get("local_binary_accounting"), "current local accounting")
    result = []
    for variant in _list(ablation.get("variants"), "ablation variants"):
        item = copy.deepcopy(_dict(variant, "ablation variant"))
        grouped = _dict(item.get("grouped"), f"{item.get('id')} grouped")
        if sum(_int(grouped.get(key), f"{item.get('id')} {key}") for key in GROUP_KEYS) != item.get("typed_bytes"):
            raise TranscriptStableComparisonError(f"{item.get('id')} grouped bytes do not sum")
        is_current = item["id"] == "current_duplicate_adapter_v1_frontier"
        item["artifact_backed"] = is_current
        item["query_inventory_status"] = "PINNED_RECORD_STREAM" if is_current else "MISSING_VARIANT_PROOF_ARTIFACT"
        item["query_inventory_fingerprint"] = local_accounting.get("record_stream_sha256") if is_current else None
        item["statement_commitment"] = envelope_input.get("statement_commitment") if is_current else None
        item["public_instance_commitments"] = (
            {
                "attention_public_instance_commitment": envelope_input.get("attention_public_instance_commitment"),
                "mlp_public_instance_commitment": envelope_input.get("mlp_public_instance_commitment"),
            }
            if is_current
            else None
        )
        item["reported_shape_fingerprint"] = shape_fingerprint(item)
        result.append(item)
    return result


def promotion_status(left: dict[str, Any], right: dict[str, Any]) -> str:
    labels_equal = (
        left["proof_backend_version"] == right["proof_backend_version"]
        and left["statement_version"] == right["statement_version"]
    )
    if not left["artifact_backed"] or not right["artifact_backed"]:
        if not labels_equal:
            return "NO_GO_LABELS_DIFFER_AND_VARIANT_PROOF_ARTIFACTS_MISSING"
        return "NO_GO_VARIANT_PROOF_ARTIFACT_MISSING"
    if not labels_equal:
        return "NO_GO_TRANSCRIPT_LABELS_DIFFER"
    if left["query_inventory_status"] != "PINNED_RECORD_STREAM" or right["query_inventory_status"] != "PINNED_RECORD_STREAM":
        return "NO_GO_QUERY_INVENTORY_NOT_PINNED"
    return "GO_TRANSCRIPT_STABLE"


def build_comparisons(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparisons = []
    for comparison_id, baseline_id, candidate_id in PAIR_SPECS:
        baseline = variant_by_id(variants, baseline_id)
        candidate = variant_by_id(variants, candidate_id)
        typed_saving = _int(baseline.get("typed_bytes"), f"{baseline_id} typed") - _int(candidate.get("typed_bytes"), f"{candidate_id} typed")
        json_saving = _int(baseline.get("proof_json_bytes"), f"{baseline_id} json") - _int(candidate.get("proof_json_bytes"), f"{candidate_id} json")
        direct_saving = grouped_saving(baseline, candidate, DIRECT_OPENING_VALUE_GROUPS)
        path_saving = grouped_saving(baseline, candidate, TRANSCRIPT_PATH_SENSITIVE_GROUPS)
        labels_equal = (
            baseline["proof_backend_version"] == candidate["proof_backend_version"]
            and baseline["statement_version"] == candidate["statement_version"]
        )
        status = promotion_status(baseline, candidate)
        comparisons.append(
            {
                "comparison_id": comparison_id,
                "baseline_variant_id": baseline_id,
                "candidate_variant_id": candidate_id,
                "typed_saving_bytes": typed_saving,
                "json_saving_bytes": json_saving,
                "adapter_trace_cell_saving": baseline["adapter_trace_cells"] - candidate["adapter_trace_cells"],
                "direct_opening_value_saving_bytes": direct_saving,
                "transcript_path_sensitive_saving_bytes": path_saving,
                "transcript_path_sensitive_share": round(path_saving / typed_saving, 6) if typed_saving else 0.0,
                "proof_backend_versions_equal": baseline["proof_backend_version"] == candidate["proof_backend_version"],
                "statement_versions_equal": baseline["statement_version"] == candidate["statement_version"],
                "labels_equal": labels_equal,
                "baseline_artifact_backed": baseline["artifact_backed"],
                "candidate_artifact_backed": candidate["artifact_backed"],
                "baseline_query_inventory_status": baseline["query_inventory_status"],
                "candidate_query_inventory_status": candidate["query_inventory_status"],
                "transcript_stable_for_promotion": status == "GO_TRANSCRIPT_STABLE",
                "promotion_status": status,
            }
        )
    return comparisons


def build_payload() -> dict[str, Any]:
    sources = load_sources()
    validate_sources(sources)
    variants = variant_inventory(sources)
    comparisons = build_comparisons(variants)
    label_control = next(
        item for item in comparisons if item["comparison_id"] == "compact_base_v2_vs_duplicate_label_control"
    )
    legacy = next(item for item in comparisons if item["comparison_id"] == "legacy_microprobe_vs_current_frontier")
    weak = next(
        item for item in comparisons if item["comparison_id"] == "unconstrained_compact_v2_vs_duplicate_label_control"
    )
    compact_vs_weak = next(
        item for item in comparisons if item["comparison_id"] == "referenced_compact_v2_vs_unconstrained_compact_v2"
    )
    stability_policy = {
        "promotion_requires_source_artifact_per_variant": True,
        "promotion_requires_identical_transcript_labels_or_explicit_variant_invariant_policy": True,
        "promotion_requires_statement_and_public_instance_commitments": True,
        "promotion_requires_query_inventory_fingerprint": True,
        "promotion_requires_grouped_typed_accounting": True,
        "query_inventory_proxy_accepted_for_current_artifact": "local_binary_accounting.record_stream_sha256",
        "grouped_bytes_alone_are_not_a_query_inventory": True,
    }
    summary = {
        "stable_frontier_promotion": False,
        "stable_comparison_result": "NO_GO_VARIANT_PROOF_ARTIFACTS_AND_QUERY_INVENTORY_MISSING",
        "current_frontier_typed_bytes": CURRENT_FRONTIER_TYPED_BYTES,
        "two_proof_frontier_typed_bytes": TWO_PROOF_FRONTIER_TYPED_BYTES,
        "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "best_reported_label_control_saving_bytes": label_control["typed_saving_bytes"],
        "label_control_direct_opening_value_saving_bytes": label_control["direct_opening_value_saving_bytes"],
        "label_control_transcript_path_sensitive_saving_bytes": label_control[
            "transcript_path_sensitive_saving_bytes"
        ],
        "label_control_transcript_path_sensitive_share": label_control["transcript_path_sensitive_share"],
        "legacy_microprobe_typed_saving_bytes": legacy["typed_saving_bytes"],
        "legacy_microprobe_transcript_path_sensitive_saving_bytes": legacy[
            "transcript_path_sensitive_saving_bytes"
        ],
        "unconstrained_compact_direct_floor_bytes": weak["direct_opening_value_saving_bytes"],
        "referenced_compact_extra_path_sensitive_bytes": compact_vs_weak[
            "transcript_path_sensitive_saving_bytes"
        ],
        "stable_promotable_comparison_count": sum(
            1 for comparison in comparisons if comparison["transcript_stable_for_promotion"]
        ),
        "nanozk_win_claimed": False,
    }
    interpretation = {
        "human_result": (
            "The adapter-compression lead remains real, but the current evidence is not transcript-stable enough "
            "to promote. In the 736 typed-byte label-control saving, only 112 bytes are direct opened-value "
            "reduction; 624 bytes sit in FRI/Merkle path-sensitive groups."
        ),
        "why_this_matters": (
            "Small native proof-size deltas can be dominated by Fiat-Shamir query positions and Merkle path overlap. "
            "A compact adapter can look better or worse unless both variants carry proof artifacts, pinned labels, "
            "statement commitments, and query-inventory fingerprints."
        ),
        "next_attack": (
            "Re-run duplicate and compact adapter variants with variant-invariant transcript policy or multiple "
            "transcript seeds, emit per-variant binary accounting, then decide whether compact adapter can replace "
            "the 41932 typed-byte frontier."
        ),
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": sources["source_artifacts"],
        "stability_policy": stability_policy,
        "variant_inventory": variants,
        "comparisons": comparisons,
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
        raise TranscriptStableComparisonError("payload key set drift")
    for key, expected in {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
    }.items():
        if data.get(key) != expected:
            raise TranscriptStableComparisonError(f"{key} drift")
    if data.get("non_claims") != list(NON_CLAIMS):
        raise TranscriptStableComparisonError("non-claims drift")
    if data.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise TranscriptStableComparisonError("validation commands drift")
    expected = build_payload()
    for key in CORE_KEYS - {"payload_commitment"}:
        if data.get(key) != expected.get(key):
            raise TranscriptStableComparisonError(f"{key} drift")
    summary = _dict(data.get("summary"), "summary")
    if _bool(summary.get("stable_frontier_promotion"), "stable frontier promotion") is not False:
        raise TranscriptStableComparisonError("frontier overclaim")
    if _bool(summary.get("nanozk_win_claimed"), "nanozk win claimed") is not False:
        raise TranscriptStableComparisonError("NANOZK overclaim")
    if summary.get("label_control_transcript_path_sensitive_saving_bytes") != 624:
        raise TranscriptStableComparisonError("path-sensitive saving drift")
    if summary.get("label_control_direct_opening_value_saving_bytes") != 112:
        raise TranscriptStableComparisonError("direct saving drift")
    if summary.get("stable_promotable_comparison_count") != 0:
        raise TranscriptStableComparisonError("stable comparison promotion drift")
    comparisons = _list(data.get("comparisons"), "comparisons")
    if len(comparisons) != len(PAIR_SPECS):
        raise TranscriptStableComparisonError("comparison count drift")
    for comparison in comparisons:
        item = _dict(comparison, "comparison")
        if item.get("transcript_stable_for_promotion") is True:
            raise TranscriptStableComparisonError("comparison promoted without stable transcript")
    if data.get("payload_commitment") != payload_commitment(data):
        raise TranscriptStableComparisonError("payload commitment drift")
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(MUTATION_NAMES):
            raise TranscriptStableComparisonError("mutation inventory drift")
        if data.get("case_count") != len(MUTATION_NAMES) or len(cases) != len(MUTATION_NAMES):
            raise TranscriptStableComparisonError("mutation case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise TranscriptStableComparisonError("not all mutations rejected")
        for expected_name, case_value in zip(MUTATION_NAMES, cases, strict=True):
            case = _dict(case_value, "mutation case")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise TranscriptStableComparisonError("mutation case field drift")
            if case.get("name") != expected_name:
                raise TranscriptStableComparisonError("mutation case order drift")
            if case.get("accepted") is not False:
                raise TranscriptStableComparisonError("mutation accepted")
            if case.get("rejected") is not True:
                raise TranscriptStableComparisonError("mutation not rejected")


MutationFn = Callable[[dict[str, Any]], None]


def _source_artifact_hash_drift(payload: dict[str, Any]) -> None:
    for artifact_value in _list(payload.get("source_artifacts"), "source artifacts"):
        artifact = _dict(artifact_value, "source artifact")
        if artifact.get("id") == "adapter_compression_ablation_gate":
            artifact["sha256"] = "00" * 32
            return
    raise TranscriptStableComparisonError("missing adapter_compression_ablation_gate source artifact")


def _label_control_promoted(payload: dict[str, Any]) -> None:
    for comparison in payload["comparisons"]:
        if comparison["comparison_id"] == "compact_base_v2_vs_duplicate_label_control":
            comparison["transcript_stable_for_promotion"] = True
            comparison["promotion_status"] = "GO_TRANSCRIPT_STABLE"
            return
    raise TranscriptStableComparisonError("missing label-control comparison")


def _path_sensitive_saving_erased(payload: dict[str, Any]) -> None:
    payload["summary"]["label_control_transcript_path_sensitive_saving_bytes"] = 0


def _query_inventory_faked(payload: dict[str, Any]) -> None:
    for variant in payload["variant_inventory"]:
        if variant["id"] == "compact_base_v2_referenced_fixed_columns":
            variant["artifact_backed"] = True
            variant["query_inventory_status"] = "PINNED_RECORD_STREAM"
            variant["query_inventory_fingerprint"] = "blake2b-256:" + "11" * 32
            return
    raise TranscriptStableComparisonError("missing compact-base variant")


def _payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "blake2b-256:" + "22" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("result_promoted", lambda p: p.__setitem__("result", "GO_TRANSCRIPT_STABLE_FRONTIER"), True),
    ("frontier_promoted", lambda p: p["summary"].__setitem__("stable_frontier_promotion", True), True),
    ("nanozk_win_promoted", lambda p: p["summary"].__setitem__("nanozk_win_claimed", True), True),
    ("label_control_promoted", _label_control_promoted, True),
    ("path_sensitive_saving_erased", _path_sensitive_saving_erased, True),
    ("query_inventory_faked", _query_inventory_faked, True),
    ("source_artifact_hash_drift", _source_artifact_hash_drift, True),
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
        except TranscriptStableComparisonError as err:
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
    for comparison in payload["comparisons"]:
        writer.writerow({key: comparison[key] for key in TSV_COLUMNS})
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    if path is None:
        return None
    candidate = ROOT / path if not path.is_absolute() else path
    resolved_parent = candidate.parent.resolve()
    resolved = resolved_parent / candidate.name
    evidence_root = EVIDENCE_DIR.resolve()
    if evidence_root not in resolved.parents:
        raise TranscriptStableComparisonError("output path must stay under docs/engineering/evidence")
    if resolved.suffix != suffix:
        raise TranscriptStableComparisonError(f"output path must end with {suffix}")
    return resolved


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    if path.exists() and path.is_symlink():
        raise TranscriptStableComparisonError("refusing to write through symlink")
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_path: pathlib.Path | None = None
    fd = -1
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=parent)
        temp_path = pathlib.Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
        parent_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if fd != -1:
            os.close(fd)
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


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
