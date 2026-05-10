#!/usr/bin/env python3
"""Matched source/sidecar vs fused proof-section delta gate for issue #531.

This gate extends the fused Softmax-table microprofile without overclaiming. It
parses the source, LogUp sidecar, and fused Stwo proof envelopes for the checked
route matrix and reports where the serialized proof-byte savings appear at the
exposed proof-object section boundary.

It is not backend-internal attribution: the current serialized proofs do not
label columns or proof bytes as source-arithmetic versus LogUp lookup. The useful
result here is narrower and checked: fusion primarily removes a second opening
surface (FRI proof + decommitments) rather than producing a semantic column split.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import pathlib
import sys
import tempfile
import uuid
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_fused_softmax_table_route_matrix_gate as matrix

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-fused-softmax-table-section-delta-2026-05.tsv"

SCHEMA = "zkai-attention-kv-fused-softmax-table-section-delta-v1"
ISSUE = 531
SOURCE_ISSUE = matrix.ISSUE
MICROPROFILE_ISSUE = 526
DECISION = "GO_MATCHED_SOURCE_SIDECAR_VS_FUSED_STARK_PROOF_SECTION_DELTA_WITH_BACKEND_INTERNAL_SPLIT_NO_GO"
ROUTE_ID = "local_stwo_attention_kv_fused_softmax_table_section_delta"
CLAIM_BOUNDARY = (
    "ENGINEERING_PROOF_SECTION_DELTA_FOR_MATCHED_SOURCE_PLUS_LOGUP_SIDECAR_VS_FUSED_NATIVE_STWO_"
    "BOUNDED_SOFTMAX_TABLE_ROUTES_NOT_BACKEND_INTERNAL_SOURCE_VS_LOOKUP_ATTRIBUTION_NOT_TIMING"
)
SECTION_DELTA_STATUS = "GO_MATCHED_SERIALIZED_STARK_PROOF_SECTION_DELTA"
BACKEND_INTERNAL_SPLIT_STATUS = "NO_GO_SERIALIZED_STARK_PROOF_DOES_NOT_LABEL_SOURCE_ARITHMETIC_VS_LOGUP_LOOKUP_COLUMNS_OR_BYTES"
ATTRIBUTION_BLOCKER = (
    "The checked envelopes expose serialized STARK proof sections, but not semantic column labels or byte spans for "
    "source arithmetic versus LogUp lookup. Only source/sidecar/fused section deltas are claimed."
)
TIMING_POLICY = "proof_bytes_only_not_timing_not_public_benchmark"
PROOF_OBJECT_SCOPE = "matched_serialized_stark_proof_json_sections_for_source_sidecar_and_fused_envelopes"
NON_CLAIMS = (
    "not backend-internal source arithmetic versus lookup byte attribution",
    "not binary PCS/FRI internal accounting",
    "not timing evidence",
    "not a public benchmark",
    "not exact real-valued Softmax",
    "not full inference",
    "not recursion or PCD",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_fused_softmax_table_section_delta_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_section_delta_gate",
    "just gate-fast",
    "just gate",
)
PROOF_SECTION_KEYS = (
    "config",
    "commitments",
    "sampled_values",
    "decommitments",
    "queried_values",
    "proof_of_work",
    "fri_proof",
)
PROOF_BUCKET_KEYS = (
    "commitment_bucket_bytes",
    "query_bucket_bytes",
    "opening_bucket_bytes",
    "config_and_pow_bytes",
    "json_wrapper_bytes",
)
TSV_COLUMNS = (
    "profile_id",
    "axis_role",
    "source_proof_size_bytes",
    "sidecar_proof_size_bytes",
    "source_plus_sidecar_raw_proof_bytes",
    "fused_proof_size_bytes",
    "fused_saves_vs_source_plus_sidecar_bytes",
    "opening_bucket_savings_bytes",
    "fri_proof_savings_bytes",
    "decommitments_savings_bytes",
    "query_bucket_savings_bytes",
    "commitment_bucket_savings_bytes",
    "backend_internal_split_status",
)
EXPECTED_PROFILE_IDS = matrix.PROFILE_IDS
EXPECTED_TOTALS = {
    "source_proof_size_bytes": 528_303,
    "sidecar_proof_size_bytes": 187_827,
    "source_plus_sidecar_raw_proof_bytes": 716_130,
    "fused_proof_size_bytes": 563_139,
    "fused_saves_vs_source_plus_sidecar_bytes": 152_991,
}
EXPECTED_WRAPPER_TOTALS = {
    "source": 1_125,
    "sidecar": 1_125,
    "source_plus_sidecar": 2_250,
    "fused": 1_125,
    "delta": 1_125,
}
EXPECTED_SECTION_DELTA_TOTALS = {
    "config": 1_224,
    "commitments": 3_083,
    "sampled_values": 3_764,
    "decommitments": 58_243,
    "queried_values": 2_644,
    "proof_of_work": 26,
    "fri_proof": 82_882,
}
EXPECTED_BUCKET_DELTA_TOTALS = {
    "commitment_bucket_bytes": 3_083,
    "query_bucket_bytes": 6_408,
    "opening_bucket_bytes": 141_125,
    "config_and_pow_bytes": 1_250,
    "json_wrapper_bytes": 1_125,
}
EXPECTED_LARGEST_SAVINGS_PROFILE_ID = "d8_sixteen_head_seq8"
EXPECTED_LARGEST_SAVINGS_BYTES = 23_705
EXPECTED_LARGEST_DELTA_SECTION = "fri_proof"
EXPECTED_LARGEST_DELTA_SECTION_BYTES = 82_882
EXPECTED_OPENING_BUCKET_SAVINGS_SHARE = 0.92244
EXPECTED_MUTATION_NAMES = (
    "decision_relabeling",
    "claim_boundary_overclaim",
    "section_delta_status_overclaim",
    "backend_internal_split_overclaim",
    "route_row_order_drift",
    "profile_id_relabeling",
    "source_proof_size_smuggling",
    "sidecar_proof_size_smuggling",
    "fused_proof_size_smuggling",
    "section_delta_smuggling",
    "opening_bucket_delta_smuggling",
    "wrapper_delta_smuggling",
    "aggregate_savings_smuggling",
    "largest_delta_section_smuggling",
    "non_claim_removed",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)


class FusedSoftmaxTableSectionDeltaGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} must be an integer")
    return value


def require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} must be a non-empty string")
    return value


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise FusedSoftmaxTableSectionDeltaGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def derive_source_envelope_path(module: Any) -> pathlib.Path:
    declared = getattr(module, "SOURCE_ENVELOPE_JSON", None)
    if declared is not None:
        return declared
    source_input = getattr(module, "SOURCE_INPUT_JSON", None)
    if source_input is None:
        raise FusedSoftmaxTableSectionDeltaGateError("source envelope path unavailable")
    return source_input.with_name(source_input.name.removesuffix(".json") + ".envelope.json")


def derive_sidecar_envelope_path(module: Any) -> pathlib.Path:
    declared = getattr(module, "SIDECAR_ENVELOPE_JSON", None)
    if declared is not None:
        return declared
    fused = getattr(module, "FUSED_ENVELOPE_JSON", None)
    if fused is None:
        raise FusedSoftmaxTableSectionDeltaGateError("sidecar envelope path unavailable")
    sidecar_name = fused.name.replace("-fused-softmax-table-proof-", "-softmax-table-logup-sidecar-proof-")
    if sidecar_name == fused.name:
        raise FusedSoftmaxTableSectionDeltaGateError("sidecar envelope path cannot be derived")
    return fused.with_name(sidecar_name)


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    if not path.is_file():
        raise FusedSoftmaxTableSectionDeltaGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} size drift: got {size}, max {max_bytes}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} is not JSON: {err}") from err


def proof_section_profile(path: pathlib.Path, max_bytes: int, label: str) -> dict[str, Any]:
    envelope = read_bounded_json(path, max_bytes, label)
    if not isinstance(envelope, dict):
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} envelope must be object")
    proof_bytes_raw = envelope.get("proof")
    if not isinstance(proof_bytes_raw, list) or not proof_bytes_raw:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} proof byte array missing")
    proof_bytes = bytearray()
    for index, value in enumerate(proof_bytes_raw):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 255:
            raise FusedSoftmaxTableSectionDeltaGateError(f"{label} proof byte[{index}] invalid")
        proof_bytes.append(value)
    try:
        proof_json = json.loads(bytes(proof_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} proof is not JSON: {err}") from err
    if not isinstance(proof_json, dict) or set(proof_json) != {"stark_proof"}:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} proof payload schema drift")
    stark_proof = proof_json["stark_proof"]
    if not isinstance(stark_proof, dict) or set(stark_proof) != set(PROOF_SECTION_KEYS):
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} stark_proof section drift")
    section_bytes = {key: len(canonical_json_bytes(stark_proof[key])) for key in PROOF_SECTION_KEYS}
    section_total = sum(section_bytes.values())
    wrapper_bytes = len(proof_bytes) - section_total
    if wrapper_bytes <= 0:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{label} wrapper byte accounting drift")
    return {
        "path": str(path.relative_to(ROOT)),
        "proof_size_bytes": len(proof_bytes),
        "envelope_size_bytes": path.stat().st_size,
        "section_bytes": section_bytes,
        "section_payload_bytes_total": section_total,
        "json_wrapper_bytes": wrapper_bytes,
        "proof_backend": require_str(envelope.get("proof_backend"), f"{label} proof_backend"),
        "proof_backend_version": require_str(envelope.get("proof_backend_version"), f"{label} proof_backend_version"),
        "statement_version": require_str(envelope.get("statement_version"), f"{label} statement_version"),
        "proof_schema_version": envelope.get("proof_schema_version"),
    }


def bucket_bytes(section_bytes: dict[str, int], wrapper_bytes: int) -> dict[str, int]:
    return {
        "commitment_bucket_bytes": section_bytes["commitments"],
        "query_bucket_bytes": section_bytes["sampled_values"] + section_bytes["queried_values"],
        "opening_bucket_bytes": section_bytes["decommitments"] + section_bytes["fri_proof"],
        "config_and_pow_bytes": section_bytes["config"] + section_bytes["proof_of_work"],
        "json_wrapper_bytes": wrapper_bytes,
    }


def subtract_sections(source: dict[str, int], sidecar: dict[str, int], fused: dict[str, int]) -> dict[str, int]:
    return {key: source[key] + sidecar[key] - fused[key] for key in PROOF_SECTION_KEYS}


def subtract_buckets(source: dict[str, int], sidecar: dict[str, int], fused: dict[str, int]) -> dict[str, int]:
    return {key: source[key] + sidecar[key] - fused[key] for key in PROOF_BUCKET_KEYS}


def build_section_delta_row(profile: matrix.Profile) -> dict[str, Any]:
    route_row = matrix.build_route_row(profile)
    module = profile.gate_module
    source = proof_section_profile(
        derive_source_envelope_path(module),
        getattr(module, "MAX_SOURCE_ENVELOPE_JSON_BYTES", 2_097_152),
        f"{profile.profile_id} source envelope",
    )
    sidecar = proof_section_profile(
        derive_sidecar_envelope_path(module),
        getattr(module, "MAX_SIDECAR_ENVELOPE_JSON_BYTES", 2_097_152),
        f"{profile.profile_id} sidecar envelope",
    )
    fused = proof_section_profile(
        module.FUSED_ENVELOPE_JSON,
        module.MAX_FUSED_ENVELOPE_JSON_BYTES,
        f"{profile.profile_id} fused envelope",
    )
    if source["proof_size_bytes"] != route_row["source_proof_size_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{profile.profile_id} source proof size drift")
    if sidecar["proof_size_bytes"] != route_row["sidecar_proof_size_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{profile.profile_id} sidecar proof size drift")
    if fused["proof_size_bytes"] != route_row["fused_proof_size_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{profile.profile_id} fused proof size drift")
    source_plus_sidecar = source["proof_size_bytes"] + sidecar["proof_size_bytes"]
    savings = source_plus_sidecar - fused["proof_size_bytes"]
    if source_plus_sidecar != route_row["source_plus_sidecar_raw_proof_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{profile.profile_id} source-plus-sidecar proof size drift")
    if savings != route_row["fused_saves_vs_source_plus_sidecar_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{profile.profile_id} fused savings drift")
    section_delta = subtract_sections(source["section_bytes"], sidecar["section_bytes"], fused["section_bytes"])
    source_buckets = bucket_bytes(source["section_bytes"], source["json_wrapper_bytes"])
    sidecar_buckets = bucket_bytes(sidecar["section_bytes"], sidecar["json_wrapper_bytes"])
    fused_buckets = bucket_bytes(fused["section_bytes"], fused["json_wrapper_bytes"])
    bucket_delta = subtract_buckets(source_buckets, sidecar_buckets, fused_buckets)
    wrapper_delta = source["json_wrapper_bytes"] + sidecar["json_wrapper_bytes"] - fused["json_wrapper_bytes"]
    if sum(section_delta.values()) + wrapper_delta != savings:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{profile.profile_id} section delta sum drift")
    if sum(bucket_delta.values()) != savings:
        raise FusedSoftmaxTableSectionDeltaGateError(f"{profile.profile_id} bucket delta sum drift")
    row = {
        "profile_id": route_row["profile_id"],
        "axis_role": route_row["axis_role"],
        "key_width": route_row["key_width"],
        "value_width": route_row["value_width"],
        "head_count": route_row["head_count"],
        "steps_per_head": route_row["steps_per_head"],
        "lookup_claims": route_row["lookup_claims"],
        "trace_rows": route_row["trace_rows"],
        "table_rows": route_row["table_rows"],
        "artifacts": {"source": source, "sidecar": sidecar, "fused": fused},
        "proof_size_bytes": {
            "source": source["proof_size_bytes"],
            "sidecar": sidecar["proof_size_bytes"],
            "source_plus_sidecar": source_plus_sidecar,
            "fused": fused["proof_size_bytes"],
            "delta": savings,
        },
        "section_delta_bytes": section_delta,
        "bucket_delta_bytes": bucket_delta,
        "json_wrapper_delta_bytes": wrapper_delta,
        "largest_delta_section": max(section_delta, key=section_delta.get),
        "largest_delta_section_bytes": max(section_delta.values()),
        "backend_internal_attribution": {
            "source_arithmetic_bytes": None,
            "logup_lookup_bytes": None,
            "shared_pcs_fri_bytes": None,
            "status": BACKEND_INTERNAL_SPLIT_STATUS,
            "blocker": ATTRIBUTION_BLOCKER,
        },
        "backend_internal_split_status": BACKEND_INTERNAL_SPLIT_STATUS,
    }
    validate_section_delta_row(row)
    return row


def validate_section_delta_row(row: Any) -> None:
    if not isinstance(row, dict):
        raise FusedSoftmaxTableSectionDeltaGateError("section delta row must be object")
    expected = {
        "profile_id",
        "axis_role",
        "key_width",
        "value_width",
        "head_count",
        "steps_per_head",
        "lookup_claims",
        "trace_rows",
        "table_rows",
        "artifacts",
        "proof_size_bytes",
        "section_delta_bytes",
        "bucket_delta_bytes",
        "json_wrapper_delta_bytes",
        "largest_delta_section",
        "largest_delta_section_bytes",
        "backend_internal_attribution",
        "backend_internal_split_status",
    }
    if set(row) != expected:
        raise FusedSoftmaxTableSectionDeltaGateError("section delta row field drift")
    if row["profile_id"] not in EXPECTED_PROFILE_IDS:
        raise FusedSoftmaxTableSectionDeltaGateError("profile_id drift")
    for key in ("key_width", "value_width", "head_count", "steps_per_head", "lookup_claims", "trace_rows", "table_rows"):
        if require_int(row[key], f"{row['profile_id']} {key}") <= 0:
            raise FusedSoftmaxTableSectionDeltaGateError(f"{row['profile_id']} {key} must be positive")
    artifacts = row["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != {"source", "sidecar", "fused"}:
        raise FusedSoftmaxTableSectionDeltaGateError("artifact role field drift")
    for role, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise FusedSoftmaxTableSectionDeltaGateError("artifact profile must be object")
        expected_artifact = {
            "path",
            "proof_size_bytes",
            "envelope_size_bytes",
            "section_bytes",
            "section_payload_bytes_total",
            "json_wrapper_bytes",
            "proof_backend",
            "proof_backend_version",
            "statement_version",
            "proof_schema_version",
        }
        if set(artifact) != expected_artifact:
            raise FusedSoftmaxTableSectionDeltaGateError("artifact profile field drift")
        require_str(artifact["path"], f"{role} path")
        if artifact["proof_backend"] != "stwo":
            raise FusedSoftmaxTableSectionDeltaGateError("artifact backend drift")
        require_str(artifact["proof_backend_version"], f"{role} proof_backend_version")
        require_str(artifact["statement_version"], f"{role} statement_version")
        for key in ("proof_size_bytes", "envelope_size_bytes", "section_payload_bytes_total", "json_wrapper_bytes"):
            if require_int(artifact[key], f"{role} {key}") <= 0:
                raise FusedSoftmaxTableSectionDeltaGateError(f"{role} {key} must be positive")
        sections = artifact["section_bytes"]
        if not isinstance(sections, dict) or set(sections) != set(PROOF_SECTION_KEYS):
            raise FusedSoftmaxTableSectionDeltaGateError("artifact section field drift")
        if sum(sections.values()) != artifact["section_payload_bytes_total"]:
            raise FusedSoftmaxTableSectionDeltaGateError("artifact section sum drift")
        if artifact["section_payload_bytes_total"] + artifact["json_wrapper_bytes"] != artifact["proof_size_bytes"]:
            raise FusedSoftmaxTableSectionDeltaGateError("artifact proof byte accounting drift")
    sizes = row["proof_size_bytes"]
    expected_sizes = {"source", "sidecar", "source_plus_sidecar", "fused", "delta"}
    if not isinstance(sizes, dict) or set(sizes) != expected_sizes:
        raise FusedSoftmaxTableSectionDeltaGateError("proof size field drift")
    if sizes["source"] != artifacts["source"]["proof_size_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError("source proof size drift")
    if sizes["sidecar"] != artifacts["sidecar"]["proof_size_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError("sidecar proof size drift")
    if sizes["fused"] != artifacts["fused"]["proof_size_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError("fused proof size drift")
    if sizes["source"] + sizes["sidecar"] != sizes["source_plus_sidecar"]:
        raise FusedSoftmaxTableSectionDeltaGateError("source-plus-sidecar proof size drift")
    if sizes["source_plus_sidecar"] - sizes["fused"] != sizes["delta"]:
        raise FusedSoftmaxTableSectionDeltaGateError("proof savings drift")
    sections = row["section_delta_bytes"]
    if not isinstance(sections, dict) or set(sections) != set(PROOF_SECTION_KEYS):
        raise FusedSoftmaxTableSectionDeltaGateError("section delta field drift")
    for key in PROOF_SECTION_KEYS:
        expected_delta = (
            artifacts["source"]["section_bytes"][key]
            + artifacts["sidecar"]["section_bytes"][key]
            - artifacts["fused"]["section_bytes"][key]
        )
        if sections[key] != expected_delta:
            raise FusedSoftmaxTableSectionDeltaGateError("section delta drift")
    buckets = row["bucket_delta_bytes"]
    if not isinstance(buckets, dict) or set(buckets) != set(PROOF_BUCKET_KEYS):
        raise FusedSoftmaxTableSectionDeltaGateError("bucket delta field drift")
    if buckets["commitment_bucket_bytes"] != sections["commitments"]:
        raise FusedSoftmaxTableSectionDeltaGateError("commitment bucket delta drift")
    if buckets["query_bucket_bytes"] != sections["sampled_values"] + sections["queried_values"]:
        raise FusedSoftmaxTableSectionDeltaGateError("query bucket delta drift")
    if buckets["opening_bucket_bytes"] != sections["decommitments"] + sections["fri_proof"]:
        raise FusedSoftmaxTableSectionDeltaGateError("opening bucket delta drift")
    if buckets["config_and_pow_bytes"] != sections["config"] + sections["proof_of_work"]:
        raise FusedSoftmaxTableSectionDeltaGateError("config-and-pow bucket delta drift")
    wrapper_delta = (
        artifacts["source"]["json_wrapper_bytes"]
        + artifacts["sidecar"]["json_wrapper_bytes"]
        - artifacts["fused"]["json_wrapper_bytes"]
    )
    if row["json_wrapper_delta_bytes"] != wrapper_delta:
        raise FusedSoftmaxTableSectionDeltaGateError("JSON wrapper delta drift")
    if buckets["json_wrapper_bytes"] != wrapper_delta:
        raise FusedSoftmaxTableSectionDeltaGateError("JSON wrapper bucket delta drift")
    if sum(sections.values()) + wrapper_delta != sizes["delta"]:
        raise FusedSoftmaxTableSectionDeltaGateError("row savings sum drift")
    if sum(buckets.values()) != sizes["delta"]:
        raise FusedSoftmaxTableSectionDeltaGateError("bucket savings sum drift")
    if row["largest_delta_section"] != max(sections, key=sections.get):
        raise FusedSoftmaxTableSectionDeltaGateError("largest delta section drift")
    if row["largest_delta_section_bytes"] != sections[row["largest_delta_section"]]:
        raise FusedSoftmaxTableSectionDeltaGateError("largest delta section bytes drift")
    attribution = row["backend_internal_attribution"]
    expected_attribution = {"source_arithmetic_bytes", "logup_lookup_bytes", "shared_pcs_fri_bytes", "status", "blocker"}
    if not isinstance(attribution, dict) or set(attribution) != expected_attribution:
        raise FusedSoftmaxTableSectionDeltaGateError("backend attribution field drift")
    for key in ("source_arithmetic_bytes", "logup_lookup_bytes", "shared_pcs_fri_bytes"):
        if attribution[key] is not None:
            raise FusedSoftmaxTableSectionDeltaGateError("backend attribution overclaim")
    if attribution["status"] != BACKEND_INTERNAL_SPLIT_STATUS:
        raise FusedSoftmaxTableSectionDeltaGateError("backend attribution status drift")
    if attribution["blocker"] != ATTRIBUTION_BLOCKER:
        raise FusedSoftmaxTableSectionDeltaGateError("backend attribution blocker drift")
    if row["backend_internal_split_status"] != BACKEND_INTERNAL_SPLIT_STATUS:
        raise FusedSoftmaxTableSectionDeltaGateError("backend_internal_split_status drift")


def build_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    role_totals = {
        "source_proof_size_bytes": sum(row["proof_size_bytes"]["source"] for row in rows),
        "sidecar_proof_size_bytes": sum(row["proof_size_bytes"]["sidecar"] for row in rows),
        "source_plus_sidecar_raw_proof_bytes": sum(row["proof_size_bytes"]["source_plus_sidecar"] for row in rows),
        "fused_proof_size_bytes": sum(row["proof_size_bytes"]["fused"] for row in rows),
        "fused_saves_vs_source_plus_sidecar_bytes": sum(row["proof_size_bytes"]["delta"] for row in rows),
    }
    section_totals = {
        role: {key: sum(row["artifacts"][role]["section_bytes"][key] for row in rows) for key in PROOF_SECTION_KEYS}
        for role in ("source", "sidecar", "fused")
    }
    section_totals["source_plus_sidecar"] = {
        key: section_totals["source"][key] + section_totals["sidecar"][key] for key in PROOF_SECTION_KEYS
    }
    section_totals["delta"] = {
        key: section_totals["source_plus_sidecar"][key] - section_totals["fused"][key] for key in PROOF_SECTION_KEYS
    }
    wrapper_totals = {
        "source": sum(row["artifacts"]["source"]["json_wrapper_bytes"] for row in rows),
        "sidecar": sum(row["artifacts"]["sidecar"]["json_wrapper_bytes"] for row in rows),
        "fused": sum(row["artifacts"]["fused"]["json_wrapper_bytes"] for row in rows),
    }
    wrapper_totals["source_plus_sidecar"] = wrapper_totals["source"] + wrapper_totals["sidecar"]
    wrapper_totals["delta"] = wrapper_totals["source_plus_sidecar"] - wrapper_totals["fused"]
    bucket_totals = {
        "source": bucket_bytes(section_totals["source"], wrapper_totals["source"]),
        "sidecar": bucket_bytes(section_totals["sidecar"], wrapper_totals["sidecar"]),
        "source_plus_sidecar": bucket_bytes(section_totals["source_plus_sidecar"], wrapper_totals["source_plus_sidecar"]),
        "fused": bucket_bytes(section_totals["fused"], wrapper_totals["fused"]),
    }
    bucket_totals["delta"] = subtract_buckets(bucket_totals["source"], bucket_totals["sidecar"], bucket_totals["fused"])
    largest_row = max(rows, key=lambda row: row["proof_size_bytes"]["delta"])
    largest_section = max(section_totals["delta"], key=section_totals["delta"].get)
    aggregate = {
        "profiles_checked": len(rows),
        "role_totals": role_totals,
        "section_totals_by_role": section_totals,
        "json_wrapper_totals_by_role": wrapper_totals,
        "bucket_totals_by_role": bucket_totals,
        "largest_savings_profile_id": largest_row["profile_id"],
        "largest_savings_profile_bytes": largest_row["proof_size_bytes"]["delta"],
        "largest_delta_section": largest_section,
        "largest_delta_section_bytes": section_totals["delta"][largest_section],
        "opening_bucket_savings_share": ratio(
            bucket_totals["delta"]["opening_bucket_bytes"],
            role_totals["fused_saves_vs_source_plus_sidecar_bytes"],
        ),
        "proof_backend_versions": sorted(
            {
                row["artifacts"][role]["proof_backend_version"]
                for row in rows
                for role in ("source", "sidecar", "fused")
            }
        ),
    }
    validate_aggregate(aggregate)
    return aggregate


def validate_aggregate(aggregate: Any) -> None:
    if not isinstance(aggregate, dict):
        raise FusedSoftmaxTableSectionDeltaGateError("aggregate must be object")
    expected = {
        "profiles_checked",
        "role_totals",
        "section_totals_by_role",
        "json_wrapper_totals_by_role",
        "bucket_totals_by_role",
        "largest_savings_profile_id",
        "largest_savings_profile_bytes",
        "largest_delta_section",
        "largest_delta_section_bytes",
        "opening_bucket_savings_share",
        "proof_backend_versions",
    }
    if set(aggregate) != expected:
        raise FusedSoftmaxTableSectionDeltaGateError("aggregate field drift")
    if aggregate["profiles_checked"] != len(EXPECTED_PROFILE_IDS):
        raise FusedSoftmaxTableSectionDeltaGateError("profile count drift")
    if aggregate["role_totals"] != EXPECTED_TOTALS:
        raise FusedSoftmaxTableSectionDeltaGateError("role totals drift")
    roles = {"source", "sidecar", "source_plus_sidecar", "fused", "delta"}
    sections = aggregate["section_totals_by_role"]
    if not isinstance(sections, dict) or set(sections) != roles:
        raise FusedSoftmaxTableSectionDeltaGateError("section total role drift")
    for role in roles:
        if not isinstance(sections[role], dict) or set(sections[role]) != set(PROOF_SECTION_KEYS):
            raise FusedSoftmaxTableSectionDeltaGateError("section total field drift")
    if sections["delta"] != EXPECTED_SECTION_DELTA_TOTALS:
        raise FusedSoftmaxTableSectionDeltaGateError("section delta total drift")
    wrappers = aggregate["json_wrapper_totals_by_role"]
    if wrappers != EXPECTED_WRAPPER_TOTALS:
        raise FusedSoftmaxTableSectionDeltaGateError("wrapper totals drift")
    buckets = aggregate["bucket_totals_by_role"]
    if not isinstance(buckets, dict) or set(buckets) != roles:
        raise FusedSoftmaxTableSectionDeltaGateError("bucket total role drift")
    for role in roles:
        if not isinstance(buckets[role], dict) or set(buckets[role]) != set(PROOF_BUCKET_KEYS):
            raise FusedSoftmaxTableSectionDeltaGateError("bucket total field drift")
    if buckets["delta"] != EXPECTED_BUCKET_DELTA_TOTALS:
        raise FusedSoftmaxTableSectionDeltaGateError("bucket delta total drift")
    if aggregate["largest_savings_profile_id"] != EXPECTED_LARGEST_SAVINGS_PROFILE_ID:
        raise FusedSoftmaxTableSectionDeltaGateError("largest savings profile drift")
    if aggregate["largest_savings_profile_bytes"] != EXPECTED_LARGEST_SAVINGS_BYTES:
        raise FusedSoftmaxTableSectionDeltaGateError("largest savings bytes drift")
    if aggregate["largest_delta_section"] != EXPECTED_LARGEST_DELTA_SECTION:
        raise FusedSoftmaxTableSectionDeltaGateError("largest delta section drift")
    if aggregate["largest_delta_section_bytes"] != EXPECTED_LARGEST_DELTA_SECTION_BYTES:
        raise FusedSoftmaxTableSectionDeltaGateError("largest delta section bytes drift")
    if aggregate["opening_bucket_savings_share"] != EXPECTED_OPENING_BUCKET_SAVINGS_SHARE:
        raise FusedSoftmaxTableSectionDeltaGateError("opening bucket savings share drift")
    if not isinstance(aggregate["proof_backend_versions"], list) or len(aggregate["proof_backend_versions"]) < 3:
        raise FusedSoftmaxTableSectionDeltaGateError("proof backend version inventory drift")
    if sum(sections["delta"].values()) + wrappers["delta"] != aggregate["role_totals"]["fused_saves_vs_source_plus_sidecar_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError("aggregate section savings sum drift")
    if sum(buckets["delta"].values()) != aggregate["role_totals"]["fused_saves_vs_source_plus_sidecar_bytes"]:
        raise FusedSoftmaxTableSectionDeltaGateError("aggregate bucket savings sum drift")


def section_delta_commitment(payload: dict[str, Any]) -> str:
    payload_for_commitment = copy.deepcopy(payload)
    payload_for_commitment.pop("section_delta_commitment", None)
    return blake2b_commitment(payload_for_commitment, SCHEMA)


def build_base_payload() -> dict[str, Any]:
    rows = [build_section_delta_row(profile) for profile in matrix.PROFILES]
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "microprofile_issue": MICROPROFILE_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "proof_object_scope": PROOF_OBJECT_SCOPE,
        "section_delta_status": SECTION_DELTA_STATUS,
        "backend_internal_split_status": BACKEND_INTERNAL_SPLIT_STATUS,
        "attribution_blocker": ATTRIBUTION_BLOCKER,
        "timing_policy": TIMING_POLICY,
        "profile_ids": list(EXPECTED_PROFILE_IDS),
        "profile_rows": rows,
        "aggregate": build_aggregate(rows),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["section_delta_commitment"] = section_delta_commitment(payload)
    validate_payload(payload, allow_missing_mutation_summary=True, expected_rows=rows)
    return payload


def validate_payload(
    payload: Any,
    *,
    allow_missing_mutation_summary: bool = False,
    expected_rows: list[dict[str, Any]] | None = None,
) -> None:
    if not isinstance(payload, dict):
        raise FusedSoftmaxTableSectionDeltaGateError("payload must be object")
    expected = {
        "schema",
        "issue",
        "source_issue",
        "microprofile_issue",
        "decision",
        "route_id",
        "claim_boundary",
        "proof_object_scope",
        "section_delta_status",
        "backend_internal_split_status",
        "attribution_blocker",
        "timing_policy",
        "profile_ids",
        "profile_rows",
        "aggregate",
        "non_claims",
        "validation_commands",
        "section_delta_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    allowed = expected | mutation_keys
    if set(payload) - allowed:
        raise FusedSoftmaxTableSectionDeltaGateError("payload field drift")
    missing = expected - set(payload)
    if missing:
        raise FusedSoftmaxTableSectionDeltaGateError("payload field drift")
    for key, expected_value in (
        ("schema", SCHEMA),
        ("issue", ISSUE),
        ("source_issue", SOURCE_ISSUE),
        ("microprofile_issue", MICROPROFILE_ISSUE),
        ("decision", DECISION),
        ("route_id", ROUTE_ID),
        ("claim_boundary", CLAIM_BOUNDARY),
        ("proof_object_scope", PROOF_OBJECT_SCOPE),
        ("section_delta_status", SECTION_DELTA_STATUS),
        ("backend_internal_split_status", BACKEND_INTERNAL_SPLIT_STATUS),
        ("attribution_blocker", ATTRIBUTION_BLOCKER),
        ("timing_policy", TIMING_POLICY),
        ("profile_ids", list(EXPECTED_PROFILE_IDS)),
        ("non_claims", list(NON_CLAIMS)),
        ("validation_commands", list(VALIDATION_COMMANDS)),
    ):
        if payload[key] != expected_value:
            raise FusedSoftmaxTableSectionDeltaGateError(f"{key} drift")
    rows = payload["profile_rows"]
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_PROFILE_IDS):
        raise FusedSoftmaxTableSectionDeltaGateError("profile row count drift")
    if [row.get("profile_id") if isinstance(row, dict) else None for row in rows] != list(EXPECTED_PROFILE_IDS):
        raise FusedSoftmaxTableSectionDeltaGateError("profile row order drift")
    for row in rows:
        validate_section_delta_row(row)
    if expected_rows is None:
        expected_rows = [build_section_delta_row(profile) for profile in matrix.PROFILES]
    if rows != expected_rows:
        raise FusedSoftmaxTableSectionDeltaGateError("section delta row drift")
    expected_aggregate = build_aggregate(expected_rows)
    if payload["aggregate"] != expected_aggregate:
        raise FusedSoftmaxTableSectionDeltaGateError("aggregate drift")
    validate_aggregate(payload["aggregate"])
    if section_delta_commitment(payload) != payload["section_delta_commitment"]:
        raise FusedSoftmaxTableSectionDeltaGateError("section delta commitment drift")
    if not allow_missing_mutation_summary or any(key in payload for key in mutation_keys):
        if not mutation_keys <= set(payload):
            raise FusedSoftmaxTableSectionDeltaGateError("mutation summary missing")
        if payload["mutations_checked"] != EXPECTED_MUTATION_COUNT:
            raise FusedSoftmaxTableSectionDeltaGateError("mutation count drift")
        if payload["mutations_rejected"] != EXPECTED_MUTATION_COUNT:
            raise FusedSoftmaxTableSectionDeltaGateError("mutation rejection drift")
        if payload["all_mutations_rejected"] is not True:
            raise FusedSoftmaxTableSectionDeltaGateError("mutation rejection flag drift")
        cases = payload["mutation_cases"]
        if not isinstance(cases, list) or len(cases) != EXPECTED_MUTATION_COUNT:
            raise FusedSoftmaxTableSectionDeltaGateError("mutation case count drift")
        if [case.get("name") if isinstance(case, dict) else None for case in cases] != list(EXPECTED_MUTATION_NAMES):
            raise FusedSoftmaxTableSectionDeltaGateError("mutation case name drift")
        for case in cases:
            if not isinstance(case, dict):
                raise FusedSoftmaxTableSectionDeltaGateError("mutation case must be object")
            if set(case) != {"name", "rejected", "error"}:
                raise FusedSoftmaxTableSectionDeltaGateError("mutation case field drift")
            if case["rejected"] is not True:
                raise FusedSoftmaxTableSectionDeltaGateError("mutation survived")
            require_str(case["error"], "mutation error")


def mutation_cases_for(payload: dict[str, Any], *, expected_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    base = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        base.pop(key, None)
    mutations: list[tuple[str, Any]] = []

    def add(name: str, fn: Any) -> None:
        mutations.append((name, fn))

    add("decision_relabeling", lambda p: p.__setitem__("decision", "GO_BACKEND_INTERNAL_SPLIT"))
    add("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "GO_SOURCE_VS_LOOKUP_ATTRIBUTION"))
    add("section_delta_status_overclaim", lambda p: p.__setitem__("section_delta_status", "GO_BINARY_FRI_INTERNAL_ACCOUNTING"))
    add("backend_internal_split_overclaim", lambda p: p.__setitem__("backend_internal_split_status", "GO_SOURCE_LOOKUP_SPLIT"))
    add("route_row_order_drift", lambda p: p["profile_rows"].reverse())
    add("profile_id_relabeling", lambda p: p["profile_rows"][0].__setitem__("profile_id", "different"))
    add("source_proof_size_smuggling", lambda p: p["profile_rows"][0]["proof_size_bytes"].__setitem__("source", p["profile_rows"][0]["proof_size_bytes"]["source"] + 1))
    add("sidecar_proof_size_smuggling", lambda p: p["profile_rows"][0]["proof_size_bytes"].__setitem__("sidecar", p["profile_rows"][0]["proof_size_bytes"]["sidecar"] + 1))
    add("fused_proof_size_smuggling", lambda p: p["profile_rows"][0]["proof_size_bytes"].__setitem__("fused", p["profile_rows"][0]["proof_size_bytes"]["fused"] + 1))
    add("section_delta_smuggling", lambda p: p["profile_rows"][0]["section_delta_bytes"].__setitem__("fri_proof", p["profile_rows"][0]["section_delta_bytes"]["fri_proof"] + 1))
    add("opening_bucket_delta_smuggling", lambda p: p["profile_rows"][0]["bucket_delta_bytes"].__setitem__("opening_bucket_bytes", p["profile_rows"][0]["bucket_delta_bytes"]["opening_bucket_bytes"] + 1))
    add("wrapper_delta_smuggling", lambda p: p["profile_rows"][0].__setitem__("json_wrapper_delta_bytes", p["profile_rows"][0]["json_wrapper_delta_bytes"] + 1))
    add("aggregate_savings_smuggling", lambda p: p["aggregate"]["role_totals"].__setitem__("fused_saves_vs_source_plus_sidecar_bytes", p["aggregate"]["role_totals"]["fused_saves_vs_source_plus_sidecar_bytes"] + 1))
    add("largest_delta_section_smuggling", lambda p: p["aggregate"].__setitem__("largest_delta_section", "decommitments"))
    add("non_claim_removed", lambda p: p["non_claims"].pop(0))
    add("unknown_field_injection", lambda p: p.__setitem__("unexpected", True))

    if [name for name, _fn in mutations] != list(EXPECTED_MUTATION_NAMES):
        raise FusedSoftmaxTableSectionDeltaGateError("mutation spec drift")
    cases = []
    for name, fn in mutations:
        candidate = copy.deepcopy(base)
        fn(candidate)
        try:
            validate_payload(candidate, allow_missing_mutation_summary=True, expected_rows=expected_rows)
        except FusedSoftmaxTableSectionDeltaGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "mutation survived"})
    return cases


def build_payload() -> dict[str, Any]:
    payload = build_base_payload()
    cases = mutation_cases_for(payload, expected_rows=payload["profile_rows"])
    payload["mutation_cases"] = cases
    payload["mutations_checked"] = len(cases)
    payload["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    payload["all_mutations_rejected"] = payload["mutations_rejected"] == payload["mutations_checked"]
    payload["section_delta_commitment"] = section_delta_commitment(payload)
    validate_payload(payload, expected_rows=payload["profile_rows"])
    return payload


def to_tsv(payload: dict[str, Any], *, validate: bool = True, expected_rows: list[dict[str, Any]] | None = None) -> str:
    if validate:
        validate_payload(payload, expected_rows=expected_rows)
    rows = []
    for row in payload["profile_rows"]:
        rows.append(
            {
                "profile_id": row["profile_id"],
                "axis_role": row["axis_role"],
                "source_proof_size_bytes": row["proof_size_bytes"]["source"],
                "sidecar_proof_size_bytes": row["proof_size_bytes"]["sidecar"],
                "source_plus_sidecar_raw_proof_bytes": row["proof_size_bytes"]["source_plus_sidecar"],
                "fused_proof_size_bytes": row["proof_size_bytes"]["fused"],
                "fused_saves_vs_source_plus_sidecar_bytes": row["proof_size_bytes"]["delta"],
                "opening_bucket_savings_bytes": row["bucket_delta_bytes"]["opening_bucket_bytes"],
                "fri_proof_savings_bytes": row["section_delta_bytes"]["fri_proof"],
                "decommitments_savings_bytes": row["section_delta_bytes"]["decommitments"],
                "query_bucket_savings_bytes": row["bucket_delta_bytes"]["query_bucket_bytes"],
                "commitment_bucket_savings_bytes": row["bucket_delta_bytes"]["commitment_bucket_bytes"],
                "backend_internal_split_status": row["backend_internal_split_status"],
            }
        )
    from io import StringIO

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def require_output_path(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    if resolved.parent != EVIDENCE_DIR.resolve():
        raise FusedSoftmaxTableSectionDeltaGateError("output path must be under docs/engineering/evidence")
    return resolved


def write_atomic(path: pathlib.Path, content: str) -> None:
    resolved = require_output_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temp_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=resolved.parent, prefix=f".{resolved.name}.", suffix=".tmp", delete=False) as tmp:
            tmp.write(content)
            temp_path = pathlib.Path(tmp.name)
        temp_path.replace(resolved)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path, tsv_path: pathlib.Path) -> None:
    validate_payload(payload, expected_rows=payload["profile_rows"])
    json_content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tsv_content = to_tsv(payload, expected_rows=payload["profile_rows"])
    write_atomic(json_path, json_content)
    write_atomic(tsv_path, tsv_content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true", help="print payload JSON to stdout")
    args = parser.parse_args(argv)

    payload = build_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.no_write:
        write_outputs(payload, args.write_json or JSON_OUT, args.write_tsv or TSV_OUT)
    else:
        validate_payload(payload, expected_rows=payload["profile_rows"])
    if not args.json:
        aggregate = payload["aggregate"]
        print(
            " ".join(
                [
                    payload["decision"],
                    str(aggregate["role_totals"]["fused_saves_vs_source_plus_sidecar_bytes"]),
                    aggregate["largest_delta_section"],
                    str(aggregate["bucket_totals_by_role"]["delta"]["opening_bucket_bytes"]),
                    payload["section_delta_commitment"],
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
