#!/usr/bin/env python3
"""Cross-evidence mechanism ablation for the fused attention/Softmax-table route."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import os
import pathlib
import stat as stat_module
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-fusion-mechanism-ablation-v1"
DECISION = "GO_STARK_NATIVE_FUSION_MECHANISM_ABLATION_FOR_PAPER_ARCHITECTURE_CLAIM"
ROUTE_ID = "local_stwo_attention_kv_fusion_mechanism_ablation"
CLAIM_BOUNDARY = (
    "CROSS_EVIDENCE_MECHANISM_ABLATION_FOR_MATCHED_SOURCE_PLUS_LOGUP_SIDECAR_VS_FUSED_"
    "NATIVE_STWO_ATTENTION_SOFTMAX_TABLE_PROOFS_NOT_BACKEND_INTERNAL_BYTE_ATTRIBUTION_NOT_TIMING"
)
MECHANISM_STATUS = "GO_SHARED_OPENING_DECOMMITMENT_PLUMBING_DOMINATES_CHECKED_SAVINGS"
BACKEND_INTERNAL_SPLIT_STATUS = (
    "NO_GO_SERIALIZED_STARK_PROOF_DOES_NOT_LABEL_SOURCE_ARITHMETIC_VS_LOGUP_LOOKUP_COLUMNS_OR_BYTES"
)
TIMING_POLICY = "proof_bytes_and_local_typed_accounting_only_not_timing_not_public_benchmark"
MAX_EVIDENCE_JSON_BYTES = 16 * 1024 * 1024
MAX_OUTPUT_BACKUP_BYTES = 64 * 1024 * 1024
EXPECTED_STABLE_BINARY_SERIALIZER_STATUS = "NO_GO_STABLE_BINARY_STWO_PROOF_SERIALIZER_NOT_EXPOSED"
EXPECTED_BINARY_SERIALIZATION_STATUS = "NO_GO_NOT_UPSTREAM_STWO_PROOF_SERIALIZATION"
EXPECTED_CLI_UPSTREAM_STWO_SERIALIZATION_STATUS = "NOT_UPSTREAM_STWO_SERIALIZATION_LOCAL_ACCOUNTING_RECORD_STREAM_ONLY"
EXPECTED_BINARY_FIRST_BLOCKER = (
    "Upstream Stwo does not expose a stable proof wire serializer here; this gate records a repo-owned "
    "deterministic accounting record stream over typed proof fields instead."
)
MIN_MATCHED_ROUTE_SAVINGS_BYTES = 1

EVIDENCE_INPUTS = {
    "route_matrix": "docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json",
    "section_delta": "docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json",
    "typed_size_estimate": "docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.json",
    "controlled_component_grid": "docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json",
    "binary_typed_accounting": "docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json",
}

NON_CLAIMS = [
    "not backend-internal source arithmetic versus lookup byte attribution",
    "not upstream Stwo verifier-facing binary proof serialization",
    "not timing evidence",
    "not a public benchmark",
    "not exact real-valued Softmax",
    "not full inference",
    "not a d64 or d128 RMSNorm-SwiGLU transformer-block proof",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_kv_stwo_fusion_mechanism_ablation_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_fusion_mechanism_ablation_gate",
    "just gate-fast",
    "git diff --check",
    "just gate",
]

EXPECTED_MUTATION_NAMES = [
    "route_total_saving_drift",
    "opening_share_drift",
    "typed_decommitment_share_drift",
    "binary_accounting_overclaim",
    "non_claim_removed",
    "evidence_sha_drift",
    "unknown_field_injection",
]


class FusionMechanismAblationGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as err:
        raise FusionMechanismAblationGateError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise FusionMechanismAblationGateError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def _repo_relative_path(value: str | pathlib.Path, label: str) -> pathlib.PurePosixPath:
    raw = str(value).replace("\\", "/")
    path = pathlib.PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise FusionMechanismAblationGateError(f"{label} must be repo-relative")
    return path


def _full_repo_path(relative_path: pathlib.PurePosixPath) -> pathlib.Path:
    return ROOT.joinpath(*relative_path.parts)


def _assert_no_repo_symlink_components(path: pathlib.Path, label: str) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as err:
        raise FusionMechanismAblationGateError(f"{label} must stay within repository") from err
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise FusionMechanismAblationGateError(f"{label} must not include symlink components")


def _open_repo_regular_file(
    path: pathlib.Path,
    *,
    label: str = "evidence path",
    max_bytes: int = MAX_EVIDENCE_JSON_BYTES,
) -> bytes:
    root = ROOT.resolve()
    candidate = pathlib.Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as err:
        raise FusionMechanismAblationGateError(f"{label} escapes repository: {path}") from err

    current = root
    pre_stat = None
    try:
        for part in relative.parts:
            current = current / part
            part_stat = current.lstat()
            if stat_module.S_ISLNK(part_stat.st_mode):
                raise FusionMechanismAblationGateError(f"{label} must not traverse symlinks: {path}")
            pre_stat = part_stat
        if pre_stat is None or not stat_module.S_ISREG(pre_stat.st_mode):
            raise FusionMechanismAblationGateError(f"{label} is not a regular file: {path}")
        fd = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise FusionMechanismAblationGateError(f"{label} is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise FusionMechanismAblationGateError(f"{label} changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(max_bytes + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise FusionMechanismAblationGateError(f"failed to read {label} {path}: {err}") from err

    if len(raw) > max_bytes:
        raise FusionMechanismAblationGateError(
            f"{label} exceeds max size: got at least {len(raw)} bytes, limit {max_bytes}"
        )
    return raw


def _json_payload_from_bytes(relative_path: str, raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise FusionMechanismAblationGateError(f"invalid JSON in {relative_path}: {err}") from err
    if not isinstance(payload, dict):
        raise FusionMechanismAblationGateError(f"evidence payload must be object: {relative_path}")
    return payload


def _load_json_with_sha256(relative_path: str) -> tuple[dict[str, Any], str]:
    path = _full_repo_path(_repo_relative_path(relative_path, "evidence path"))
    raw = _open_repo_regular_file(path)
    return _json_payload_from_bytes(relative_path, raw), hashlib.sha256(raw).hexdigest()


def load_json(relative_path: str) -> dict[str, Any]:
    payload, _digest = _load_json_with_sha256(relative_path)
    return payload


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def sha256_file(relative_path: str) -> str:
    path = _full_repo_path(_repo_relative_path(relative_path, "evidence path"))
    return hashlib.sha256(_open_repo_regular_file(path)).hexdigest()


def _round(value: float) -> float:
    return round(value, 6)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FusionMechanismAblationGateError(f"{label} must be object")
    return value


def _non_negative_integer_mapping_field(payload: dict[str, Any], key: str, label: str) -> int:
    value = payload[key]
    if type(value) is not int:
        raise FusionMechanismAblationGateError(f"{label} must be integer bytes")
    if value < 0:
        raise FusionMechanismAblationGateError(f"{label} must be non-negative")
    return value


def _positive_integer_mapping_field(payload: dict[str, Any], key: str, label: str) -> int:
    value = _non_negative_integer_mapping_field(payload, key, label)
    if value <= 0:
        raise FusionMechanismAblationGateError(f"{label} must be positive")
    return value


def _positive_integer_count_mapping_field(payload: dict[str, Any], key: str, label: str) -> int:
    value = payload[key]
    if type(value) is not int:
        raise FusionMechanismAblationGateError(f"{label} must be integer")
    if value <= 0:
        raise FusionMechanismAblationGateError(f"{label} must be positive")
    return value


def _string_mapping_field(payload: dict[str, Any], key: str, label: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise FusionMechanismAblationGateError(f"{label} must be string")
    if not value:
        raise FusionMechanismAblationGateError(f"{label} must be non-empty")
    return value


def _route_metrics(route: dict[str, Any]) -> dict[str, Any]:
    rows = route["route_rows"]
    matched = [(index, row) for index, row in enumerate(rows) if "source_plus_sidecar_raw_proof_bytes" in row]
    if not matched:
        raise FusionMechanismAblationGateError("route matrix must contain matched source-plus-sidecar rows")
    savings = []
    ratios = []
    source_values = []
    fused_values = []
    for index, row in matched:
        for key in (
            "source_plus_sidecar_raw_proof_bytes",
            "fused_proof_size_bytes",
            "fused_saves_vs_source_plus_sidecar_bytes",
            "fused_to_source_plus_sidecar_ratio",
        ):
            if key not in row:
                raise FusionMechanismAblationGateError(f"route matrix row {index} missing {key}")
        source_bytes = _non_negative_integer_mapping_field(
            row, "source_plus_sidecar_raw_proof_bytes", f"route matrix row {index} source-plus-sidecar"
        )
        fused_bytes = _non_negative_integer_mapping_field(
            row, "fused_proof_size_bytes", f"route matrix row {index} fused proof"
        )
        saving_bytes = _non_negative_integer_mapping_field(
            row, "fused_saves_vs_source_plus_sidecar_bytes", f"route matrix row {index} fused saving"
        )
        if saving_bytes != source_bytes - fused_bytes:
            raise FusionMechanismAblationGateError(f"route matrix row {index} saving does not match byte totals")
        if source_bytes <= 0:
            raise FusionMechanismAblationGateError(f"route matrix row {index} source-plus-sidecar must be positive")
        reported_ratio = row["fused_to_source_plus_sidecar_ratio"]
        if type(reported_ratio) not in (int, float) or not math.isfinite(float(reported_ratio)):
            raise FusionMechanismAblationGateError(f"route matrix row {index} ratio must be finite")
        ratio = _round(fused_bytes / source_bytes)
        if _round(float(reported_ratio)) != ratio:
            raise FusionMechanismAblationGateError(f"route matrix row {index} ratio does not match byte totals")
        source_values.append(source_bytes)
        fused_values.append(fused_bytes)
        savings.append(saving_bytes)
        ratios.append(ratio)
    source_plus = sum(source_values)
    fused = sum(fused_values)
    if source_plus <= 0:
        raise FusionMechanismAblationGateError("route matrix source-plus-sidecar total must be positive")
    if not ratios:
        raise FusionMechanismAblationGateError("route matrix ratio inventory must be non-empty")
    aggregate = route["aggregate_metrics"]
    aggregate_source_plus = _non_negative_integer_mapping_field(
        aggregate, "matched_source_plus_sidecar_raw_proof_bytes_total", "route aggregate source-plus-sidecar"
    )
    aggregate_fused = _non_negative_integer_mapping_field(
        aggregate, "matched_fused_proof_size_bytes_total", "route aggregate fused proof"
    )
    aggregate_savings = _non_negative_integer_mapping_field(
        aggregate, "matched_fused_savings_bytes_total", "route aggregate fused saving"
    )
    return {
        "profiles_checked": len(rows),
        "matched_profiles_checked": len(matched),
        "all_matched_profiles_save_json_bytes": all(value > 0 for value in savings),
        "source_plus_sidecar_raw_proof_bytes_total": source_plus,
        "fused_proof_size_bytes_total": fused,
        "fused_savings_bytes_total": source_plus - fused,
        "fused_saving_share": _round((source_plus - fused) / source_plus),
        "min_fused_to_source_plus_sidecar_ratio": min(ratios),
        "max_fused_to_source_plus_sidecar_ratio": max(ratios),
        "aggregate_metrics_match": {
            "source_plus_sidecar_raw_proof_bytes_total": aggregate_source_plus,
            "fused_proof_size_bytes_total": aggregate_fused,
            "fused_savings_bytes_total": aggregate_savings,
        },
    }


def _section_delta_metrics(section: dict[str, Any]) -> dict[str, Any]:
    aggregate = section["aggregate"]
    profiles_checked = _positive_integer_count_mapping_field(
        aggregate, "profiles_checked", "section profiles checked"
    )
    delta = _mapping(aggregate["section_totals_by_role"]["delta"], "section delta totals")
    opening_bucket = _mapping(aggregate["bucket_totals_by_role"]["delta"], "section opening bucket totals")
    role_totals = _mapping(aggregate["role_totals"], "section role totals")
    opening = _non_negative_integer_mapping_field(
        opening_bucket, "opening_bucket_bytes", "section opening bucket"
    )
    total = _positive_integer_mapping_field(
        role_totals,
        "fused_saves_vs_source_plus_sidecar_bytes",
        "section delta savings total",
    )
    for key in ("fri_proof", "decommitments"):
        if key not in delta:
            raise FusionMechanismAblationGateError(f"section delta missing {key}")
    fri_proof = _non_negative_integer_mapping_field(delta, "fri_proof", "section fri_proof")
    decommitments = _non_negative_integer_mapping_field(delta, "decommitments", "section decommitments")
    fri_plus_decommitments = fri_proof + decommitments
    largest_delta_section_bytes = _non_negative_integer_mapping_field(
        aggregate, "largest_delta_section_bytes", "section largest delta"
    )
    largest_delta_section = _string_mapping_field(aggregate, "largest_delta_section", "section largest delta")
    reported_opening_share = _share_payload_field(
        section,
        ("aggregate", "opening_bucket_savings_share"),
        "section opening share",
    )
    recomputed_opening_share = _round(opening / total)
    if _round(reported_opening_share) != recomputed_opening_share:
        raise FusionMechanismAblationGateError("section opening share does not match byte totals")
    if section["backend_internal_split_status"] != BACKEND_INTERNAL_SPLIT_STATUS:
        raise FusionMechanismAblationGateError("section backend split status drift")
    return {
        "profiles_checked": profiles_checked,
        "json_savings_bytes_total": total,
        "opening_bucket_savings_bytes": opening,
        "opening_bucket_savings_share": recomputed_opening_share,
        "fri_plus_decommitments_savings_bytes": fri_plus_decommitments,
        "fri_plus_decommitments_savings_share": _round(fri_plus_decommitments / total),
        "largest_delta_section": largest_delta_section,
        "largest_delta_section_bytes": largest_delta_section_bytes,
        "backend_internal_split_status": BACKEND_INTERNAL_SPLIT_STATUS,
    }


def _typed_metrics(typed: dict[str, Any]) -> dict[str, Any]:
    aggregate = typed["aggregate"]
    profiles_checked = _positive_integer_count_mapping_field(
        aggregate, "profiles_checked", "typed profiles checked"
    )
    delta = _mapping(aggregate["source_plus_sidecar_minus_fused_delta"], "typed size delta")
    for key in ("fri_decommitments", "trace_decommitments", "typed_size_estimate_bytes"):
        if key not in delta:
            raise FusionMechanismAblationGateError(f"typed size delta missing {key}")
    fri_decommitments = _non_negative_integer_mapping_field(delta, "fri_decommitments", "typed fri decommitments")
    trace_decommitments = _non_negative_integer_mapping_field(
        delta, "trace_decommitments", "typed trace decommitments"
    )
    decommitment_total = fri_decommitments + trace_decommitments
    typed_savings = _positive_integer_mapping_field(delta, "typed_size_estimate_bytes", "typed size savings total")
    source_plus_sidecar = _mapping(aggregate["source_plus_sidecar_totals"], "typed source-plus-sidecar totals")
    source_plus_sidecar_typed = _positive_integer_mapping_field(
        source_plus_sidecar, "typed_size_estimate_bytes", "typed source-plus-sidecar total"
    )
    reported_typed_share = _share_payload_field(
        typed,
        ("aggregate", "typed_saving_share_vs_source_plus_sidecar"),
        "typed saving share",
    )
    recomputed_typed_share = _round(typed_savings / source_plus_sidecar_typed)
    if _round(reported_typed_share) != recomputed_typed_share:
        raise FusionMechanismAblationGateError("typed saving share does not match byte totals")
    largest_typed_saving_bucket_bytes = _non_negative_integer_mapping_field(
        aggregate, "largest_typed_saving_bucket_bytes", "typed largest saving bucket"
    )
    largest_typed_saving_bucket = _string_mapping_field(
        aggregate, "largest_typed_saving_bucket", "typed largest saving bucket"
    )
    stable_binary_status = _string_mapping_field(
        typed, "stable_binary_serializer_status", "typed stable binary serializer status"
    )
    if stable_binary_status != EXPECTED_STABLE_BINARY_SERIALIZER_STATUS:
        raise FusionMechanismAblationGateError("typed stable binary serializer status drift")
    return {
        "profiles_checked": profiles_checked,
        "typed_savings_bytes_total": typed_savings,
        "typed_saving_share_vs_source_plus_sidecar": recomputed_typed_share,
        "fri_trace_decommitment_savings_bytes": decommitment_total,
        "fri_trace_decommitment_savings_share": _round(decommitment_total / typed_savings),
        "largest_typed_saving_bucket": largest_typed_saving_bucket,
        "largest_typed_saving_bucket_bytes": largest_typed_saving_bucket_bytes,
        "stable_binary_serializer_status": stable_binary_status,
    }


def _controlled_metrics(controlled: dict[str, Any]) -> dict[str, Any]:
    aggregate = controlled["aggregate"]
    profiles_checked = _positive_integer_count_mapping_field(
        aggregate, "profiles_checked", "controlled profiles checked"
    )
    typed_total = _positive_integer_mapping_field(
        aggregate, "typed_savings_bytes_total", "controlled typed savings total"
    )
    opening_bytes = _positive_integer_mapping_field(
        aggregate, "opening_plumbing_savings_bytes_total", "controlled opening plumbing savings"
    )
    fri_trace_merkle_path_savings = _non_negative_integer_mapping_field(
        aggregate,
        "fri_trace_merkle_path_savings_bytes_total",
        "controlled FRI trace merkle path savings",
    )
    source_plus_sidecar_typed = _positive_integer_mapping_field(
        aggregate,
        "source_plus_sidecar_typed_size_bytes_total",
        "controlled source-plus-sidecar typed total",
    )
    largest_component_saving = _non_negative_integer_mapping_field(
        aggregate, "largest_component_saving_bucket_bytes", "controlled largest component saving"
    )
    largest_component_bucket = _string_mapping_field(
        aggregate, "largest_component_saving_bucket", "controlled largest component saving bucket"
    )
    reported_typed_share = _share_payload_field(
        controlled,
        ("aggregate", "typed_saving_share_total"),
        "controlled typed saving share",
    )
    recomputed_typed_share = _round(typed_total / source_plus_sidecar_typed)
    if _round(reported_typed_share) != recomputed_typed_share:
        raise FusionMechanismAblationGateError("controlled typed saving share does not match byte totals")
    reported_share = _share_payload_field(
        controlled,
        ("aggregate", "opening_plumbing_share_of_typed_savings"),
        "controlled opening plumbing share",
    )
    recomputed_share = _round(opening_bytes / typed_total)
    if _round(reported_share) != recomputed_share:
        raise FusionMechanismAblationGateError("controlled opening plumbing share does not match byte totals")
    reported_fri_trace_share = _share_payload_field(
        controlled,
        ("aggregate", "fri_trace_merkle_path_share_of_typed_savings"),
        "controlled FRI trace merkle path share",
    )
    recomputed_fri_trace_share = _round(fri_trace_merkle_path_savings / typed_total)
    if _round(reported_fri_trace_share) != recomputed_fri_trace_share:
        raise FusionMechanismAblationGateError(
            "controlled FRI trace merkle path share does not match byte totals"
        )
    stable_binary_status = _string_mapping_field(
        controlled, "stable_binary_serializer_status", "controlled stable binary serializer status"
    )
    if stable_binary_status != EXPECTED_STABLE_BINARY_SERIALIZER_STATUS:
        raise FusionMechanismAblationGateError("controlled stable binary serializer status drift")
    if aggregate["all_profiles_save_typed_components"] is not True:
        raise FusionMechanismAblationGateError("controlled all-profiles-save status drift")
    return {
        "profiles_checked": profiles_checked,
        "all_profiles_save_typed_components": aggregate["all_profiles_save_typed_components"],
        "typed_savings_bytes_total": typed_total,
        "typed_saving_share_total": recomputed_typed_share,
        "opening_plumbing_savings_bytes_total": opening_bytes,
        "opening_plumbing_share_of_typed_savings": recomputed_share,
        "fri_trace_merkle_path_savings_bytes_total": fri_trace_merkle_path_savings,
        "fri_trace_merkle_path_share_of_typed_savings": recomputed_fri_trace_share,
        "largest_component_saving_bucket": largest_component_bucket,
        "largest_component_saving_bucket_bytes": largest_component_saving,
        "stable_binary_serializer_status": stable_binary_status,
    }


def _binary_metrics(binary: dict[str, Any]) -> dict[str, Any]:
    aggregate = binary["aggregate"]
    profiles_checked = _positive_integer_count_mapping_field(
        aggregate, "profiles_checked", "binary profiles checked"
    )
    source_plus_sidecar_json = _non_negative_integer_mapping_field(
        aggregate, "source_plus_sidecar_json_proof_bytes", "binary source-plus-sidecar JSON proof"
    )
    fused_json = _non_negative_integer_mapping_field(
        aggregate, "fused_json_proof_bytes", "binary fused JSON proof"
    )
    json_saving = _non_negative_integer_mapping_field(
        aggregate,
        "fused_saves_vs_source_plus_sidecar_json_bytes",
        "binary JSON proof saving",
    )
    source_plus_sidecar_typed = _non_negative_integer_mapping_field(
        aggregate, "source_plus_sidecar_local_typed_bytes", "binary source-plus-sidecar local typed"
    )
    fused_typed = _non_negative_integer_mapping_field(
        aggregate, "fused_local_typed_bytes", "binary fused local typed"
    )
    local_typed_saving = _positive_integer_mapping_field(
        aggregate,
        "fused_saves_vs_source_plus_sidecar_local_typed_bytes",
        "d32 local typed saving",
    )
    if json_saving != source_plus_sidecar_json - fused_json:
        raise FusionMechanismAblationGateError("binary JSON proof saving does not match byte totals")
    if local_typed_saving != source_plus_sidecar_typed - fused_typed:
        raise FusionMechanismAblationGateError("binary local typed saving does not match byte totals")
    binary_status = _string_mapping_field(binary, "binary_serialization_status", "binary serialization status")
    cli_status = _string_mapping_field(
        binary, "cli_upstream_stwo_serialization_status", "binary upstream serialization status"
    )
    first_blocker = _string_mapping_field(binary, "first_blocker", "binary first blocker")
    if binary_status != EXPECTED_BINARY_SERIALIZATION_STATUS:
        raise FusionMechanismAblationGateError("binary serialization status drift")
    if cli_status != EXPECTED_CLI_UPSTREAM_STWO_SERIALIZATION_STATUS:
        raise FusionMechanismAblationGateError("binary upstream serialization status drift")
    if first_blocker != EXPECTED_BINARY_FIRST_BLOCKER:
        raise FusionMechanismAblationGateError("binary first blocker drift")
    return {
        "profiles_checked": profiles_checked,
        "source_plus_sidecar_json_proof_bytes": source_plus_sidecar_json,
        "fused_json_proof_bytes": fused_json,
        "fused_saves_vs_source_plus_sidecar_json_bytes": json_saving,
        "source_plus_sidecar_local_typed_bytes": source_plus_sidecar_typed,
        "fused_local_typed_bytes": fused_typed,
        "fused_saves_vs_source_plus_sidecar_local_typed_bytes": local_typed_saving,
        "binary_serialization_status": binary_status,
        "cli_upstream_stwo_serialization_status": cli_status,
        "first_blocker": first_blocker,
    }


def _base_payload() -> dict[str, Any]:
    try:
        loaded = {}
        source_artifacts = []
        for name, path in EVIDENCE_INPUTS.items():
            payload, digest = _load_json_with_sha256(path)
            loaded[name] = payload
            source_artifacts.append(
                {
                    "id": name,
                    "path": path,
                    "sha256": digest,
                }
            )
        route = _route_metrics(loaded["route_matrix"])
        section = _section_delta_metrics(loaded["section_delta"])
        typed = _typed_metrics(loaded["typed_size_estimate"])
        controlled = _controlled_metrics(loaded["controlled_component_grid"])
        binary = _binary_metrics(loaded["binary_typed_accounting"])
    except FusionMechanismAblationGateError:
        raise
    except (KeyError, TypeError, ValueError) as err:
        raise FusionMechanismAblationGateError(f"malformed source evidence: {err}") from err

    route_aggregate = route["aggregate_metrics_match"]
    evidence_consistency = {
        "route_matrix_aggregate_matches_recomputed_totals": route_aggregate
        == {
            "source_plus_sidecar_raw_proof_bytes_total": route[
                "source_plus_sidecar_raw_proof_bytes_total"
            ],
            "fused_proof_size_bytes_total": route["fused_proof_size_bytes_total"],
            "fused_savings_bytes_total": route["fused_savings_bytes_total"],
        },
        "section_delta_scope_is_ten_profile_slice": section["profiles_checked"] == 10,
        "route_matrix_scope_is_eleven_matched_profiles": route["matched_profiles_checked"] == 11,
        "typed_estimate_scope_is_nine_profile_slice": typed["profiles_checked"] == 9,
        "controlled_component_grid_scope_is_ten_profile_slice": controlled["profiles_checked"] == 10,
        "binary_accounting_scope_is_d32_matched_slice": binary["profiles_checked"] == 3,
    }
    failed_consistency = [key for key, value in evidence_consistency.items() if value is not True]
    if failed_consistency:
        raise FusionMechanismAblationGateError(
            "evidence consistency failed: " + ", ".join(failed_consistency)
        )

    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "mechanism_status": MECHANISM_STATUS,
        "backend_internal_split_status": BACKEND_INTERNAL_SPLIT_STATUS,
        "timing_policy": TIMING_POLICY,
        "source_artifacts": source_artifacts,
        "route_matrix": route,
        "section_delta": section,
        "typed_size_estimate": typed,
        "controlled_component_grid": controlled,
        "binary_typed_accounting": binary,
        "evidence_consistency": evidence_consistency,
        "findings": [
            {
                "id": "matched_route_savings_persist_across_checked_axes",
                "status": "GO",
                "value": (
                    f"{route['matched_profiles_checked']} matched profiles save "
                    f"{route['fused_savings_bytes_total']} JSON proof bytes"
                ),
            },
            {
                "id": "serialized_section_delta_points_to_opening_plumbing",
                "status": "GO",
                "value": (
                    f"{section['opening_bucket_savings_share']:.6f} of ten-profile JSON savings "
                    "come from the opening bucket"
                ),
            },
            {
                "id": "typed_accounting_independently_points_to_decommitments",
                "status": "GO",
                "value": (
                    f"{typed['fri_trace_decommitment_savings_share']:.6f} of nine-profile typed savings "
                    "come from FRI plus trace decommitments"
                ),
            },
            {
                "id": "controlled_component_grid_agrees_on_opening_plumbing",
                "status": "GO",
                "value": (
                    f"{controlled['opening_plumbing_share_of_typed_savings']:.6f} of controlled-grid typed savings "
                    "come from opening plumbing"
                ),
            },
            {
                "id": "d32_local_binary_accounting_is_positive_but_not_wire_format",
                "status": "GO_WITH_NO_GO_BOUNDARY",
                "value": (
                    f"d32 local typed fused saving is "
                    f"{binary['fused_saves_vs_source_plus_sidecar_local_typed_bytes']} bytes; "
                    "upstream Stwo wire format remains a non-claim"
                ),
            },
        ],
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }


def mutation_cases(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    cases: list[tuple[str, dict[str, Any]]] = []

    mutated = copy.deepcopy(payload)
    mutated["route_matrix"]["fused_savings_bytes_total"] += 1
    cases.append(("route_total_saving_drift", mutated))

    mutated = copy.deepcopy(payload)
    mutated["section_delta"]["opening_bucket_savings_share"] = 0.5
    cases.append(("opening_share_drift", mutated))

    mutated = copy.deepcopy(payload)
    mutated["typed_size_estimate"]["fri_trace_decommitment_savings_share"] = 0.1
    cases.append(("typed_decommitment_share_drift", mutated))

    mutated = copy.deepcopy(payload)
    mutated["binary_typed_accounting"]["cli_upstream_stwo_serialization_status"] = "UPSTREAM_STWO_WIRE_FORMAT"
    cases.append(("binary_accounting_overclaim", mutated))

    mutated = copy.deepcopy(payload)
    mutated["non_claims"] = mutated["non_claims"][1:]
    cases.append(("non_claim_removed", mutated))

    mutated = copy.deepcopy(payload)
    mutated["source_artifacts"][0]["sha256"] = "0" * 64
    cases.append(("evidence_sha_drift", mutated))

    mutated = copy.deepcopy(payload)
    mutated["unexpected"] = True
    cases.append(("unknown_field_injection", mutated))

    return cases


def _strip_mutation_fields(payload: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected", "payload_commitment"):
        payload.pop(key, None)
    return payload


def validate_payload(
    payload: dict[str, Any],
    *,
    require_mutation_summary: bool = True,
    expected: dict[str, Any] | None = None,
) -> None:
    if expected is None:
        expected = _base_payload()
    expected_keys = set(expected)
    if require_mutation_summary:
        expected_keys |= {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected", "payload_commitment"}
    if set(payload) != expected_keys:
        raise FusionMechanismAblationGateError("unknown or missing field")

    binary_status = _string_payload_field(
        payload,
        ("binary_typed_accounting", "cli_upstream_stwo_serialization_status"),
        "binary upstream serialization status",
    )
    if binary_status != EXPECTED_CLI_UPSTREAM_STWO_SERIALIZATION_STATUS:
        raise FusionMechanismAblationGateError("binary accounting overclaim")

    if _strip_mutation_fields(payload) != expected:
        if payload.get("schema") != SCHEMA:
            raise FusionMechanismAblationGateError("schema drift")
        if payload.get("decision") != DECISION:
            raise FusionMechanismAblationGateError("decision drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise FusionMechanismAblationGateError("claim boundary drift")
        if payload.get("backend_internal_split_status") != BACKEND_INTERNAL_SPLIT_STATUS:
            raise FusionMechanismAblationGateError("backend split status drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise FusionMechanismAblationGateError("non_claims drift")
        if payload.get("source_artifacts") != expected["source_artifacts"]:
            raise FusionMechanismAblationGateError("source artifact drift")
        if payload.get("route_matrix") != expected["route_matrix"]:
            raise FusionMechanismAblationGateError("route matrix drift")
        if payload.get("section_delta") != expected["section_delta"]:
            raise FusionMechanismAblationGateError("section delta drift")
        if payload.get("typed_size_estimate") != expected["typed_size_estimate"]:
            raise FusionMechanismAblationGateError("typed size estimate drift")
        if payload.get("controlled_component_grid") != expected["controlled_component_grid"]:
            raise FusionMechanismAblationGateError("controlled component grid drift")
        if payload.get("binary_typed_accounting") != expected["binary_typed_accounting"]:
            raise FusionMechanismAblationGateError("binary typed accounting drift")
        raise FusionMechanismAblationGateError("payload drift")

    if payload["route_matrix"]["matched_profiles_checked"] != 11:
        raise FusionMechanismAblationGateError("matched route count drift")
    route_savings = _numeric_payload_field(
        payload,
        ("route_matrix", "fused_savings_bytes_total"),
        "matched route savings",
    )
    if route_savings < MIN_MATCHED_ROUTE_SAVINGS_BYTES:
        raise FusionMechanismAblationGateError("matched route savings below claim threshold")
    if _payload_field(
        payload,
        ("route_matrix", "all_matched_profiles_save_json_bytes"),
        "matched route persistence",
    ) is not True:
        raise FusionMechanismAblationGateError("matched route savings persistence drift")
    binary_local_typed_saving = _numeric_payload_field(
        payload,
        ("binary_typed_accounting", "fused_saves_vs_source_plus_sidecar_local_typed_bytes"),
        "d32 local typed saving",
    )
    if binary_local_typed_saving <= 0:
        raise FusionMechanismAblationGateError("d32 local typed saving below claim threshold")
    section_opening_share = _share_payload_field(
        payload, ("section_delta", "opening_bucket_savings_share"), "section opening share"
    )
    typed_decommitment_share = _share_payload_field(
        payload, ("typed_size_estimate", "fri_trace_decommitment_savings_share"), "typed decommitment share"
    )
    controlled_opening_share = _share_payload_field(
        payload,
        ("controlled_component_grid", "opening_plumbing_share_of_typed_savings"),
        "controlled opening share",
    )
    if section_opening_share < 0.9:
        raise FusionMechanismAblationGateError("opening share below claim threshold")
    if typed_decommitment_share < 0.85:
        raise FusionMechanismAblationGateError("typed decommitment share below claim threshold")
    if controlled_opening_share < 0.85:
        raise FusionMechanismAblationGateError("controlled opening share below claim threshold")
    if require_mutation_summary:
        expected_mutation_cases = [{"name": name, "rejected": True} for name in EXPECTED_MUTATION_NAMES]
        if payload["mutation_cases"] != expected_mutation_cases:
            raise FusionMechanismAblationGateError("mutation case drift")
        if payload["mutations_checked"] != len(EXPECTED_MUTATION_NAMES):
            raise FusionMechanismAblationGateError("mutation count drift")
        if payload["mutations_rejected"] != len(EXPECTED_MUTATION_NAMES) or not payload["all_mutations_rejected"]:
            raise FusionMechanismAblationGateError("mutation rejection drift")
        if payload["payload_commitment"] != payload_commitment(payload):
            raise FusionMechanismAblationGateError("payload commitment drift")


def _payload_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> Any:
    current: Any = payload
    for part in path:
        if not isinstance(current, dict) or part not in current:
            raise FusionMechanismAblationGateError(f"{label} missing or malformed")
        current = current[part]
    return current


def _numeric_payload_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> float:
    value = _payload_field(payload, path, label)
    if type(value) not in (int, float):
        raise FusionMechanismAblationGateError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise FusionMechanismAblationGateError(f"{label} must be finite")
    return number


def _positive_numeric_payload_field(
    payload: dict[str, Any], path: tuple[str, ...], label: str
) -> int | float:
    value = _payload_field(payload, path, label)
    if type(value) not in (int, float):
        raise FusionMechanismAblationGateError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise FusionMechanismAblationGateError(f"{label} must be finite")
    if number <= 0.0:
        raise FusionMechanismAblationGateError(f"{label} must be positive")
    return value


def _share_payload_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> float:
    number = _numeric_payload_field(payload, path, label)
    if number < 0.0 or number > 1.0:
        raise FusionMechanismAblationGateError(f"{label} must be between 0 and 1")
    return number


def _string_payload_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> str:
    value = _payload_field(payload, path, label)
    if not isinstance(value, str):
        raise FusionMechanismAblationGateError(f"{label} must be string")
    return value


def build_payload() -> dict[str, Any]:
    payload = _base_payload()
    expected = copy.deepcopy(payload)
    mutation_results = []
    for name, mutated in mutation_cases(payload):
        try:
            validate_payload(mutated, require_mutation_summary=False, expected=expected)
        except FusionMechanismAblationGateError:
            mutation_results.append({"name": name, "rejected": True})
        else:
            mutation_results.append({"name": name, "rejected": False})
    payload["mutation_cases"] = mutation_results
    payload["mutations_checked"] = len(mutation_results)
    payload["mutations_rejected"] = sum(1 for result in mutation_results if result["rejected"])
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload, expected=expected)
    return payload


def to_tsv(payload: dict[str, Any]) -> str:
    columns = [
        "metric",
        "value",
        "claim_boundary",
    ]
    rows = [
        ("matched_profiles_checked", payload["route_matrix"]["matched_profiles_checked"], payload["claim_boundary"]),
        ("route_json_savings_bytes", payload["route_matrix"]["fused_savings_bytes_total"], payload["claim_boundary"]),
        ("section_opening_share", payload["section_delta"]["opening_bucket_savings_share"], payload["claim_boundary"]),
        (
            "typed_fri_trace_decommitment_share",
            payload["typed_size_estimate"]["fri_trace_decommitment_savings_share"],
            payload["claim_boundary"],
        ),
        (
            "controlled_opening_plumbing_share",
            payload["controlled_component_grid"]["opening_plumbing_share_of_typed_savings"],
            payload["claim_boundary"],
        ),
        (
            "d32_local_typed_saving_bytes",
            payload["binary_typed_accounting"]["fused_saves_vs_source_plus_sidecar_local_typed_bytes"],
            payload["claim_boundary"],
        ),
    ]
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return out.getvalue()


def _assert_output_path(path: pathlib.Path, label: str) -> pathlib.Path:
    if path.is_absolute():
        full = pathlib.Path(os.path.abspath(path))
        try:
            full.relative_to(EVIDENCE_DIR.resolve())
        except ValueError as err:
            raise FusionMechanismAblationGateError(
                f"{label} must stay under docs/engineering/evidence"
            ) from err
        _assert_no_repo_symlink_components(full.parent, label)
        if full.is_symlink():
            raise FusionMechanismAblationGateError(f"{label} must not include symlink components")
        return full

    relative = _repo_relative_path(path, label)
    if pathlib.PurePosixPath(*relative.parts[:3]) != pathlib.PurePosixPath("docs/engineering/evidence"):
        raise FusionMechanismAblationGateError(f"{label} must stay under docs/engineering/evidence")
    full = _full_repo_path(relative)
    _assert_no_repo_symlink_components(full.parent, label)
    if full.is_symlink():
        raise FusionMechanismAblationGateError(f"{label} must not include symlink components")
    return full


def write_outputs(
    payload: dict[str, Any],
    json_path: pathlib.Path | None,
    tsv_path: pathlib.Path | None,
) -> None:
    validate_payload(payload)
    json_text = pretty_json(payload) + "\n"

    outputs = []
    json_target = _assert_output_path(json_path, "json output path") if json_path is not None else None
    tsv_target = _assert_output_path(tsv_path, "tsv output path") if tsv_path is not None else None
    if json_target is not None:
        outputs.append((json_target, json_text))
    if tsv_target is not None:
        outputs.append((tsv_target, to_tsv(payload)))
    if not outputs:
        raise FusionMechanismAblationGateError("at least one explicit output path is required")
    if json_target is not None and tsv_target is not None and os.path.abspath(json_target) == os.path.abspath(tsv_target):
        raise FusionMechanismAblationGateError("json and tsv output paths must differ")

    temps: list[pathlib.Path] = []
    replaced: list[pathlib.Path] = []
    original_bytes: dict[pathlib.Path, bytes | None] = {}
    write_error: OSError | None = None

    def write_temp(path: pathlib.Path, text: str) -> pathlib.Path:
        _assert_no_repo_symlink_components(path.parent, "output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        _assert_no_repo_symlink_components(path.parent, "output path")
        if path.is_symlink():
            raise FusionMechanismAblationGateError("output path must not include symlink components")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            tmp_path = pathlib.Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        return tmp_path

    def write_temp_bytes(path: pathlib.Path, contents: bytes) -> pathlib.Path:
        _assert_no_repo_symlink_components(path.parent, "rollback output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        _assert_no_repo_symlink_components(path.parent, "rollback output path")
        if path.is_symlink():
            raise FusionMechanismAblationGateError("rollback output path must not include symlink components")
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
            tmp_path = pathlib.Path(handle.name)
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        return tmp_path

    def rollback_replace(path: pathlib.Path, contents: bytes) -> None:
        _assert_output_path(path, "rollback output path")
        tmp = write_temp_bytes(path, contents)
        temps.append(tmp)
        _assert_output_path(path, "rollback output path")
        os.replace(tmp, path)

    try:
        try:
            for path, text in outputs:
                original_bytes[path] = (
                    _open_repo_regular_file(
                        path,
                        label="existing output backup",
                        max_bytes=MAX_OUTPUT_BACKUP_BYTES,
                    )
                    if path.exists()
                    else None
                )
                tmp = write_temp(path, text)
                temps.append(tmp)
            for tmp, (path, _) in zip(temps, outputs, strict=True):
                os.replace(tmp, path)
                replaced.append(path)
        except OSError as err:
            write_error = err
            raise FusionMechanismAblationGateError(f"failed to write output path: {err}") from err
    finally:
        if write_error is not None:
            for path in reversed(replaced):
                original = original_bytes.get(path)
                try:
                    _assert_output_path(path, "rollback output path")
                    if original is None:
                        path.unlink(missing_ok=True)
                    else:
                        rollback_replace(path, original)
                except (FusionMechanismAblationGateError, OSError):
                    pass
        for tmp in temps:
            try:
                tmp.unlink(missing_ok=True)
            except OSError as err:
                if write_error is None:
                    raise FusionMechanismAblationGateError(f"failed to clean temporary output {tmp}: {err}") from err


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        payload = build_payload()
        if args.write_json or args.write_tsv:
            write_outputs(payload, args.write_json, args.write_tsv)
        else:
            print(pretty_json(payload))
    except FusionMechanismAblationGateError as err:
        print(f"fusion mechanism ablation gate failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
