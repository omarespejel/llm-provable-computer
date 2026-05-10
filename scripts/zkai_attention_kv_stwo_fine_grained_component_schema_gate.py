#!/usr/bin/env python3
"""Fine-grained typed Stwo proof-component schema gate for issue #534.

This gate traverses public Stwo `StarkProof` fields through the local
`zkai_stwo_proof_component_schema` binary. It upgrades the grouped typed
proof-size estimate without pretending that Stwo exposes stable canonical
verifier-facing binary proof bytes.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import pathlib
import re
import subprocess
import sys
import tempfile
from io import StringIO
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_fused_softmax_table_section_delta_gate as section_delta

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-fine-grained-component-schema-gate-v1"
ISSUE = 534
SOURCE_ISSUES = (469, 476, 531)
DECISION = "GO_FINE_GRAINED_TYPED_COMPONENT_SCHEMA_WITH_STABLE_BINARY_SERIALIZER_NO_GO"
CLAIM_BOUNDARY = (
    "FINE_GRAINED_TYPED_STWO_PROOF_COMPONENT_SCHEMA_FOR_MATCHED_SOURCE_SIDECAR_AND_FUSED_"
    "SOFTMAX_TABLE_ROUTES_NOT_STABLE_BINARY_SERIALIZATION_NOT_SOURCE_VS_LOOKUP_COLUMN_ATTRIBUTION_NOT_TIMING"
)
ACCOUNTING_SOURCE = "public_stwo_2_2_0_stark_proof_field_traversal_and_mem_size_estimates"
PROOF_PAYLOAD_KIND = "utf8_json_object_with_single_stark_proof_field"
COMPONENT_SCHEMA_STATUS = "GO_FINE_GRAINED_TYPED_COMPONENT_SCHEMA_WITH_STABLE_BINARY_SERIALIZER_NO_GO"
STABLE_BINARY_SERIALIZER_STATUS = "NO_GO_STABLE_BINARY_STWO_PROOF_SERIALIZER_NOT_EXPOSED"
GROUPED_RECONSTRUCTION_STATUS = "GO_GROUPED_STWO_TYPED_BREAKDOWN_RECONSTRUCTED_FROM_FINE_GRAINED_COMPONENTS"
TIMING_POLICY = "proof_size_estimate_only_not_timing_not_public_benchmark"
SIZE_CONSTANTS = {
    "base_field_bytes": 4,
    "secure_field_bytes": 16,
    "blake2s_hash_bytes": 32,
    "proof_of_work_bytes": 8,
    "pcs_config_bytes": 40,
}
OPEN_COMPONENT_QUESTIONS = (
    "stable canonical binary Stwo proof serialization",
    "verifier-facing binary byte encoding for every component",
    "backend-internal source arithmetic versus LogUp lookup column attribution",
)
NON_CLAIMS = (
    "not stable canonical binary Stwo proof serialization",
    "not verifier-facing binary proof bytes",
    "not backend-internal source arithmetic versus LogUp lookup column attribution",
    "not exact public benchmark proof bytes",
    "not timing evidence",
    "not exact real-valued Softmax",
    "not full inference",
    "not recursion or PCD",
)
STWO_COMPONENT_SCHEMA_TIMEOUT_SECONDS = 900
MAX_ENVELOPE_JSON_BYTES = 16 * 1024 * 1024
MAX_PROOF_JSON_BYTES = 2 * 1024 * 1024
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_stwo_fine_grained_component_schema_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_fine_grained_component_schema_gate",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_component_schema -- <envelope.json>...",
    "just gate-fast",
    "just gate",
)
COMPONENT_BUCKETS = (
    "sampled_opened_value_bytes",
    "queried_value_bytes",
    "fri_layer_witness_bytes",
    "fri_last_layer_poly_bytes",
    "fri_commitment_bytes",
    "fri_decommitment_merkle_path_bytes",
    "trace_commitment_bytes",
    "trace_decommitment_merkle_path_bytes",
    "proof_of_work_bytes",
    "config_bytes",
)
GROUPED_BUCKETS = (
    "oods_samples",
    "queries_values",
    "fri_samples",
    "fri_decommitments",
    "trace_decommitments",
    "fixed_overhead",
)
ROLES = ("source", "sidecar", "fused")
TSV_COLUMNS = (
    "role",
    "json_proof_size_bytes",
    "typed_size_estimate_bytes",
    "json_over_typed_size_ratio",
    "json_minus_typed_size_bytes",
    *COMPONENT_BUCKETS,
)
EXPECTED_ROLE_TOTALS = {
    "source": {
        "json_proof_size_bytes": 528_303,
        "typed_size_estimate_bytes": 201_256,
        "json_minus_typed_size_bytes": 327_047,
        "sampled_opened_value_bytes": 90_656,
        "queried_value_bytes": 67_992,
        "fri_layer_witness_bytes": 2_896,
        "fri_last_layer_poly_bytes": 144,
        "fri_commitment_bytes": 2_272,
        "fri_decommitment_merkle_path_bytes": 18_528,
        "trace_commitment_bytes": 864,
        "trace_decommitment_merkle_path_bytes": 17_472,
        "proof_of_work_bytes": 72,
        "config_bytes": 360,
    },
    "sidecar": {
        "json_proof_size_bytes": 187_827,
        "typed_size_estimate_bytes": 52_616,
        "json_minus_typed_size_bytes": 135_211,
        "sampled_opened_value_bytes": 3_168,
        "queried_value_bytes": 1_944,
        "fri_layer_witness_bytes": 2_832,
        "fri_last_layer_poly_bytes": 144,
        "fri_commitment_bytes": 2_272,
        "fri_decommitment_merkle_path_bytes": 17_888,
        "trace_commitment_bytes": 1_152,
        "trace_decommitment_merkle_path_bytes": 22_784,
        "proof_of_work_bytes": 72,
        "config_bytes": 360,
    },
    "fused": {
        "json_proof_size_bytes": 563_139,
        "typed_size_estimate_bytes": 211_380,
        "json_minus_typed_size_bytes": 351_759,
        "sampled_opened_value_bytes": 92_528,
        "queried_value_bytes": 68_964,
        "fri_layer_witness_bytes": 2_976,
        "fri_last_layer_poly_bytes": 144,
        "fri_commitment_bytes": 2_272,
        "fri_decommitment_merkle_path_bytes": 19_104,
        "trace_commitment_bytes": 1_152,
        "trace_decommitment_merkle_path_bytes": 23_808,
        "proof_of_work_bytes": 72,
        "config_bytes": 360,
    },
}
EXPECTED_DELTA_TOTALS = {
    "json_proof_size_bytes": 152_991,
    "typed_size_estimate_bytes": 42_492,
    "json_minus_typed_size_bytes": 110_499,
    "sampled_opened_value_bytes": 1_296,
    "queried_value_bytes": 972,
    "fri_layer_witness_bytes": 2_752,
    "fri_last_layer_poly_bytes": 144,
    "fri_commitment_bytes": 2_272,
    "fri_decommitment_merkle_path_bytes": 17_312,
    "trace_commitment_bytes": 864,
    "trace_decommitment_merkle_path_bytes": 16_448,
    "proof_of_work_bytes": 72,
    "config_bytes": 360,
}
EXPECTED_JSON_OVER_TYPED_RATIO_BY_ROLE = {
    "source": 2.62503,
    "sidecar": 3.56977,
    "fused": 2.664107,
}
EXPECTED_TYPED_SAVING_SHARE = 0.167376
EXPECTED_JSON_SAVING_SHARE = 0.213636
EXPECTED_FINE_GRAINED_COMPONENT_SCHEMA_COMMITMENT = (
    "blake2b-256:77920e7954ede483264329abf5f11b7312f5a1825bb27470630418c743a636f1"
)
EXPECTED_MUTATION_NAMES = (
    "decision_overclaim",
    "binary_serializer_overclaim",
    "component_schema_overclaim",
    "grouped_reconstruction_overclaim",
    "open_component_questions_removed",
    "size_constants_smuggling",
    "typed_estimate_smuggling",
    "json_size_smuggling",
    "proof_sha256_smuggling",
    "malformed_proof_sha256",
    "component_bucket_smuggling",
    "grouped_reconstruction_smuggling",
    "aggregate_delta_smuggling",
    "role_total_smuggling",
    "row_order_drift",
    "profile_relabeling",
    "role_relabeling",
    "non_claim_removed",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)
CLI_ROW_KEYS = {
    "path",
    "proof_sha256",
    "json_proof_size_bytes",
    "typed_size_estimate_bytes",
    "component_bytes",
    "component_sum_bytes",
    "grouped_reconstruction",
    "stwo_grouped_breakdown",
    "json_over_typed_size_ratio",
    "json_minus_typed_size_bytes",
}


class StwoFineGrainedComponentSchemaGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise StwoFineGrainedComponentSchemaGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StwoFineGrainedComponentSchemaGateError(f"{label} must be an integer")
    return value


def require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise StwoFineGrainedComponentSchemaGateError(f"{label} must be a non-empty string")
    return value


def output_tail(value: str, limit: int = 1600) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[-limit:]


def section_delta_rows() -> list[dict[str, Any]]:
    payload = section_delta.build_payload()
    return payload["profile_rows"]


def evidence_relative_path(raw_path: Any, profile_id: str, role: str) -> str:
    path = pathlib.Path(require_str(raw_path, f"{profile_id}/{role} artifact path"))
    resolved = (path if path.is_absolute() else ROOT / path).resolve()
    try:
        relative = resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise StwoFineGrainedComponentSchemaGateError(
            f"artifact path for {profile_id}/{role} escapes docs/engineering/evidence: {path}"
        ) from err
    return (pathlib.Path("docs") / "engineering" / "evidence" / relative).as_posix()


def artifact_specs(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    specs = []
    for row in rows:
        profile_id = require_str(row.get("profile_id"), "profile_id")
        for role in ROLES:
            try:
                raw_path = row["artifacts"][role]["path"]
            except (KeyError, TypeError) as err:
                raise StwoFineGrainedComponentSchemaGateError(
                    f"artifact path missing for {profile_id}/{role}"
                ) from err
            specs.append(
                {
                    "profile_id": profile_id,
                    "role": role,
                    "path": evidence_relative_path(raw_path, profile_id, role),
                }
            )
    return specs


def run_stwo_component_schema(paths: list[str]) -> dict[str, Any]:
    command = [
        "cargo",
        "+nightly-2025-07-14",
        "run",
        "--quiet",
        "--locked",
        "--features",
        "stwo-backend",
        "--bin",
        "zkai_stwo_proof_component_schema",
        "--",
        *paths,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=STWO_COMPONENT_SCHEMA_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as err:
        raise StwoFineGrainedComponentSchemaGateError(
            f"Stwo proof component schema CLI timed out after {STWO_COMPONENT_SCHEMA_TIMEOUT_SECONDS}s"
        ) from err
    except OSError as err:
        raise StwoFineGrainedComponentSchemaGateError(f"failed to run Stwo proof component schema CLI: {err}") from err
    if completed.returncode != 0:
        stderr = output_tail(completed.stderr)
        stdout = output_tail(completed.stdout)
        detail = stderr or stdout or "<no output>"
        raise StwoFineGrainedComponentSchemaGateError(
            f"Stwo proof component schema CLI failed with exit code {completed.returncode}: {detail}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise StwoFineGrainedComponentSchemaGateError(f"Stwo proof component schema CLI did not emit JSON: {err}") from err


def read_bounded_utf8(path: pathlib.Path, label: str, max_bytes: int) -> str:
    try:
        with path.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except OSError as err:
        raise StwoFineGrainedComponentSchemaGateError(f"failed to read {label} {path}: {err}") from err
    if len(data) > max_bytes:
        raise StwoFineGrainedComponentSchemaGateError(f"{label} exceeds {max_bytes} byte cap: {path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as err:
        raise StwoFineGrainedComponentSchemaGateError(f"{label} is not valid UTF-8: {path}") from err


def artifact_proof_metadata(path: str) -> tuple[str, int]:
    resolved = (ROOT / path).resolve()
    try:
        envelope = json.loads(read_bounded_utf8(resolved, "artifact envelope", MAX_ENVELOPE_JSON_BYTES))
    except json.JSONDecodeError as err:
        raise StwoFineGrainedComponentSchemaGateError(f"failed to parse artifact envelope {path}: {err}") from err
    proof = envelope.get("proof") if isinstance(envelope, dict) else None
    if not isinstance(proof, list) or not proof:
        raise StwoFineGrainedComponentSchemaGateError(f"artifact envelope {path} missing proof byte array")
    if len(proof) > MAX_PROOF_JSON_BYTES:
        raise StwoFineGrainedComponentSchemaGateError(f"artifact envelope {path} proof byte array exceeds cap")
    try:
        proof_bytes = bytes(require_int(value, f"{path} proof byte") for value in proof)
    except ValueError as err:
        raise StwoFineGrainedComponentSchemaGateError(f"artifact envelope {path} has non-byte proof value") from err
    return hashlib.sha256(proof_bytes).hexdigest(), len(proof_bytes)


def build_rows() -> list[dict[str, Any]]:
    specs = artifact_specs(section_delta_rows())
    cli = run_stwo_component_schema([spec["path"] for spec in specs])
    if cli.get("schema") != "zkai-stwo-proof-component-schema-cli-v1":
        raise StwoFineGrainedComponentSchemaGateError("CLI schema drift")
    for key, expected in (
        ("accounting_source", ACCOUNTING_SOURCE),
        ("proof_payload_kind", PROOF_PAYLOAD_KIND),
        ("stable_binary_serializer_status", STABLE_BINARY_SERIALIZER_STATUS),
        ("component_schema_status", COMPONENT_SCHEMA_STATUS),
        ("size_constants", SIZE_CONSTANTS),
    ):
        if cli.get(key) != expected:
            raise StwoFineGrainedComponentSchemaGateError(f"CLI {key} drift")
    cli_rows = cli.get("rows")
    if not isinstance(cli_rows, list) or len(cli_rows) != len(specs):
        raise StwoFineGrainedComponentSchemaGateError("CLI row count drift")
    rows = []
    for spec, cli_row in zip(specs, cli_rows):
        if not isinstance(cli_row, dict) or set(cli_row) != CLI_ROW_KEYS:
            raise StwoFineGrainedComponentSchemaGateError("CLI row field drift")
        if cli_row["path"] != spec["path"]:
            raise StwoFineGrainedComponentSchemaGateError("CLI row path drift")
        proof_sha256, json_proof_size = artifact_proof_metadata(spec["path"])
        if cli_row["proof_sha256"] != proof_sha256:
            raise StwoFineGrainedComponentSchemaGateError("CLI proof_sha256 drift")
        if cli_row["json_proof_size_bytes"] != json_proof_size:
            raise StwoFineGrainedComponentSchemaGateError("CLI json_proof_size_bytes drift")
        row = {
            "profile_id": spec["profile_id"],
            "role": spec["role"],
            "path": spec["path"],
            "proof_sha256": proof_sha256,
            "json_proof_size_bytes": json_proof_size,
            "typed_size_estimate_bytes": cli_row["typed_size_estimate_bytes"],
            "component_bytes": cli_row["component_bytes"],
            "component_sum_bytes": cli_row["component_sum_bytes"],
            "grouped_reconstruction": cli_row["grouped_reconstruction"],
            "stwo_grouped_breakdown": cli_row["stwo_grouped_breakdown"],
            "json_over_typed_size_ratio": cli_row["json_over_typed_size_ratio"],
            "json_minus_typed_size_bytes": cli_row["json_minus_typed_size_bytes"],
        }
        validate_row(row)
        rows.append(row)
    return rows


def validate_component_map(component: Any, typed_size: int) -> None:
    if not isinstance(component, dict) or set(component) != set(COMPONENT_BUCKETS):
        raise StwoFineGrainedComponentSchemaGateError("component field drift")
    for key in COMPONENT_BUCKETS:
        if require_int(component[key], key) < 0:
            raise StwoFineGrainedComponentSchemaGateError("component bucket must be non-negative")
    if sum(component.values()) != typed_size:
        raise StwoFineGrainedComponentSchemaGateError("component sum drift")


def validate_grouped_map(grouped: Any, component: dict[str, int]) -> None:
    if not isinstance(grouped, dict) or set(grouped) != set(GROUPED_BUCKETS):
        raise StwoFineGrainedComponentSchemaGateError("grouped breakdown field drift")
    for key in GROUPED_BUCKETS:
        if require_int(grouped[key], key) < 0:
            raise StwoFineGrainedComponentSchemaGateError("grouped bucket must be non-negative")
    expected = {
        "oods_samples": component["sampled_opened_value_bytes"],
        "queries_values": component["queried_value_bytes"],
        "fri_samples": component["fri_layer_witness_bytes"] + component["fri_last_layer_poly_bytes"],
        "fri_decommitments": component["fri_commitment_bytes"] + component["fri_decommitment_merkle_path_bytes"],
        "trace_decommitments": component["trace_commitment_bytes"] + component["trace_decommitment_merkle_path_bytes"],
        "fixed_overhead": component["proof_of_work_bytes"] + component["config_bytes"],
    }
    if grouped != expected:
        raise StwoFineGrainedComponentSchemaGateError("grouped reconstruction drift")


def validate_row(row: Any) -> None:
    expected = {
        "profile_id",
        "role",
        "path",
        "proof_sha256",
        "json_proof_size_bytes",
        "typed_size_estimate_bytes",
        "component_bytes",
        "component_sum_bytes",
        "grouped_reconstruction",
        "stwo_grouped_breakdown",
        "json_over_typed_size_ratio",
        "json_minus_typed_size_bytes",
    }
    if not isinstance(row, dict) or set(row) != expected:
        raise StwoFineGrainedComponentSchemaGateError("row field drift")
    if row["profile_id"] not in section_delta.EXPECTED_PROFILE_IDS:
        raise StwoFineGrainedComponentSchemaGateError("profile_id drift")
    if row["role"] not in ROLES:
        raise StwoFineGrainedComponentSchemaGateError("role drift")
    require_str(row["path"], "path")
    proof_sha256 = require_str(row["proof_sha256"], "proof_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", proof_sha256):
        raise StwoFineGrainedComponentSchemaGateError(
            "proof_sha256 must be a 64-char lowercase hex SHA-256 digest"
        )
    json_size = require_int(row["json_proof_size_bytes"], "json_proof_size_bytes")
    typed_size = require_int(row["typed_size_estimate_bytes"], "typed_size_estimate_bytes")
    component_sum = require_int(row["component_sum_bytes"], "component_sum_bytes")
    json_minus_typed = require_int(row["json_minus_typed_size_bytes"], "json_minus_typed_size_bytes")
    if json_size <= 0 or typed_size <= 0:
        raise StwoFineGrainedComponentSchemaGateError("proof sizes must be positive")
    component = row["component_bytes"]
    validate_component_map(component, typed_size)
    if component_sum != typed_size:
        raise StwoFineGrainedComponentSchemaGateError("component_sum_bytes drift")
    validate_grouped_map(row["grouped_reconstruction"], component)
    if row["stwo_grouped_breakdown"] != row["grouped_reconstruction"]:
        raise StwoFineGrainedComponentSchemaGateError("Stwo grouped breakdown drift")
    if json_minus_typed != json_size - typed_size:
        raise StwoFineGrainedComponentSchemaGateError("json-minus-typed drift")
    ratio_value = row["json_over_typed_size_ratio"]
    if isinstance(ratio_value, bool) or not isinstance(ratio_value, (int, float)):
        raise StwoFineGrainedComponentSchemaGateError("json-over-typed ratio must be numeric")
    if not math.isclose(float(ratio_value), ratio(json_size, typed_size), rel_tol=0.0, abs_tol=0.000001):
        raise StwoFineGrainedComponentSchemaGateError("json-over-typed ratio drift")


def build_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    role_totals = {}
    for role in ROLES:
        role_rows = [row for row in rows if row["role"] == role]
        role_totals[role] = {
            "json_proof_size_bytes": sum(row["json_proof_size_bytes"] for row in role_rows),
            "typed_size_estimate_bytes": sum(row["typed_size_estimate_bytes"] for row in role_rows),
            "json_minus_typed_size_bytes": sum(row["json_minus_typed_size_bytes"] for row in role_rows),
            **{key: sum(row["component_bytes"][key] for row in role_rows) for key in COMPONENT_BUCKETS},
        }
    source_plus_sidecar = {
        key: role_totals["source"][key] + role_totals["sidecar"][key]
        for key in role_totals["source"]
    }
    delta = {key: source_plus_sidecar[key] - role_totals["fused"][key] for key in source_plus_sidecar}
    aggregate = {
        "profiles_checked": len(section_delta.EXPECTED_PROFILE_IDS),
        "artifacts_checked": len(rows),
        "role_totals": role_totals,
        "source_plus_sidecar_totals": source_plus_sidecar,
        "source_plus_sidecar_minus_fused_delta": delta,
        "typed_saving_share_vs_source_plus_sidecar": ratio(delta["typed_size_estimate_bytes"], source_plus_sidecar["typed_size_estimate_bytes"]),
        "json_saving_share_vs_source_plus_sidecar": ratio(delta["json_proof_size_bytes"], source_plus_sidecar["json_proof_size_bytes"]),
        "json_over_typed_ratio_by_role": {
            role: ratio(role_totals[role]["json_proof_size_bytes"], role_totals[role]["typed_size_estimate_bytes"])
            for role in ROLES
        },
        "largest_component_saving_bucket": max(COMPONENT_BUCKETS, key=lambda key: delta[key]),
        "largest_component_saving_bucket_bytes": max(delta[key] for key in COMPONENT_BUCKETS),
    }
    validate_aggregate(aggregate)
    return aggregate


def validate_aggregate(aggregate: Any) -> None:
    expected = {
        "profiles_checked",
        "artifacts_checked",
        "role_totals",
        "source_plus_sidecar_totals",
        "source_plus_sidecar_minus_fused_delta",
        "typed_saving_share_vs_source_plus_sidecar",
        "json_saving_share_vs_source_plus_sidecar",
        "json_over_typed_ratio_by_role",
        "largest_component_saving_bucket",
        "largest_component_saving_bucket_bytes",
    }
    if not isinstance(aggregate, dict) or set(aggregate) != expected:
        raise StwoFineGrainedComponentSchemaGateError("aggregate field drift")
    if aggregate["profiles_checked"] != len(section_delta.EXPECTED_PROFILE_IDS):
        raise StwoFineGrainedComponentSchemaGateError("profile count drift")
    if aggregate["artifacts_checked"] != len(section_delta.EXPECTED_PROFILE_IDS) * len(ROLES):
        raise StwoFineGrainedComponentSchemaGateError("artifact count drift")
    if aggregate["role_totals"] != EXPECTED_ROLE_TOTALS:
        raise StwoFineGrainedComponentSchemaGateError("role totals drift")
    if aggregate["source_plus_sidecar_minus_fused_delta"] != EXPECTED_DELTA_TOTALS:
        raise StwoFineGrainedComponentSchemaGateError("delta totals drift")
    expected_source_plus_sidecar = {
        key: EXPECTED_ROLE_TOTALS["source"][key] + EXPECTED_ROLE_TOTALS["sidecar"][key]
        for key in EXPECTED_ROLE_TOTALS["source"]
    }
    if aggregate["source_plus_sidecar_totals"] != expected_source_plus_sidecar:
        raise StwoFineGrainedComponentSchemaGateError("source-plus-sidecar totals drift")
    if aggregate["json_over_typed_ratio_by_role"] != EXPECTED_JSON_OVER_TYPED_RATIO_BY_ROLE:
        raise StwoFineGrainedComponentSchemaGateError("json-over-typed role ratio drift")
    if aggregate["typed_saving_share_vs_source_plus_sidecar"] != EXPECTED_TYPED_SAVING_SHARE:
        raise StwoFineGrainedComponentSchemaGateError("typed saving share drift")
    if aggregate["json_saving_share_vs_source_plus_sidecar"] != EXPECTED_JSON_SAVING_SHARE:
        raise StwoFineGrainedComponentSchemaGateError("json saving share drift")
    if aggregate["largest_component_saving_bucket"] != "fri_decommitment_merkle_path_bytes":
        raise StwoFineGrainedComponentSchemaGateError("largest component saving bucket drift")
    if aggregate["largest_component_saving_bucket_bytes"] != 17_312:
        raise StwoFineGrainedComponentSchemaGateError("largest component saving bucket bytes drift")


def payload_commitment(payload: dict[str, Any]) -> str:
    payload_for_commitment = copy.deepcopy(payload)
    payload_for_commitment.pop("fine_grained_component_schema_commitment", None)
    return blake2b_commitment(payload_for_commitment, SCHEMA)


def build_base_payload() -> dict[str, Any]:
    rows = build_rows()
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issues": list(SOURCE_ISSUES),
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "accounting_source": ACCOUNTING_SOURCE,
        "proof_payload_kind": PROOF_PAYLOAD_KIND,
        "component_schema_status": COMPONENT_SCHEMA_STATUS,
        "stable_binary_serializer_status": STABLE_BINARY_SERIALIZER_STATUS,
        "grouped_reconstruction_status": GROUPED_RECONSTRUCTION_STATUS,
        "size_constants": dict(SIZE_CONSTANTS),
        "open_component_questions": list(OPEN_COMPONENT_QUESTIONS),
        "timing_policy": TIMING_POLICY,
        "profile_ids": list(section_delta.EXPECTED_PROFILE_IDS),
        "rows": rows,
        "aggregate": build_aggregate(rows),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["fine_grained_component_schema_commitment"] = payload_commitment(payload)
    validate_payload(payload, allow_missing_mutation_summary=True, expected_rows=rows)
    return payload


def validate_payload(
    payload: Any,
    *,
    allow_missing_mutation_summary: bool = False,
    expected_rows: list[dict[str, Any]] | None = None,
) -> None:
    expected = {
        "schema",
        "issue",
        "source_issues",
        "decision",
        "claim_boundary",
        "accounting_source",
        "proof_payload_kind",
        "component_schema_status",
        "stable_binary_serializer_status",
        "grouped_reconstruction_status",
        "size_constants",
        "open_component_questions",
        "timing_policy",
        "profile_ids",
        "rows",
        "aggregate",
        "non_claims",
        "validation_commands",
        "fine_grained_component_schema_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if not isinstance(payload, dict) or set(payload) - (expected | mutation_keys):
        raise StwoFineGrainedComponentSchemaGateError("payload field drift")
    if expected - set(payload):
        raise StwoFineGrainedComponentSchemaGateError("payload field drift")
    for key, expected_value in (
        ("schema", SCHEMA),
        ("issue", ISSUE),
        ("source_issues", list(SOURCE_ISSUES)),
        ("decision", DECISION),
        ("claim_boundary", CLAIM_BOUNDARY),
        ("accounting_source", ACCOUNTING_SOURCE),
        ("proof_payload_kind", PROOF_PAYLOAD_KIND),
        ("component_schema_status", COMPONENT_SCHEMA_STATUS),
        ("stable_binary_serializer_status", STABLE_BINARY_SERIALIZER_STATUS),
        ("grouped_reconstruction_status", GROUPED_RECONSTRUCTION_STATUS),
        ("size_constants", SIZE_CONSTANTS),
        ("open_component_questions", list(OPEN_COMPONENT_QUESTIONS)),
        ("timing_policy", TIMING_POLICY),
        ("profile_ids", list(section_delta.EXPECTED_PROFILE_IDS)),
        ("non_claims", list(NON_CLAIMS)),
        ("validation_commands", list(VALIDATION_COMMANDS)),
    ):
        if payload[key] != expected_value:
            raise StwoFineGrainedComponentSchemaGateError(f"{key} drift")
    rows = payload["rows"]
    if not isinstance(rows, list) or len(rows) != len(section_delta.EXPECTED_PROFILE_IDS) * len(ROLES):
        raise StwoFineGrainedComponentSchemaGateError("row count drift")
    for row in rows:
        validate_row(row)
    expected_pairs = [
        (profile_id, role)
        for profile_id in section_delta.EXPECTED_PROFILE_IDS
        for role in ROLES
    ]
    observed_pairs = [(row["profile_id"], row["role"]) for row in rows]
    if observed_pairs != expected_pairs:
        raise StwoFineGrainedComponentSchemaGateError("row order drift")
    if expected_rows is None:
        expected_rows = rows
    elif rows != expected_rows:
        raise StwoFineGrainedComponentSchemaGateError("row drift")
    expected_aggregate = build_aggregate(expected_rows)
    if payload["aggregate"] != expected_aggregate:
        raise StwoFineGrainedComponentSchemaGateError("aggregate drift")
    validate_aggregate(payload["aggregate"])
    if payload_commitment(payload) != payload["fine_grained_component_schema_commitment"]:
        raise StwoFineGrainedComponentSchemaGateError("commitment drift")
    if (
        not allow_missing_mutation_summary
        and payload["fine_grained_component_schema_commitment"] != EXPECTED_FINE_GRAINED_COMPONENT_SCHEMA_COMMITMENT
    ):
        raise StwoFineGrainedComponentSchemaGateError(
            "published commitment drift: "
            f"got {payload['fine_grained_component_schema_commitment']} "
            f"expected {EXPECTED_FINE_GRAINED_COMPONENT_SCHEMA_COMMITMENT}"
        )
    if not allow_missing_mutation_summary or any(key in payload for key in mutation_keys):
        if not mutation_keys <= set(payload):
            raise StwoFineGrainedComponentSchemaGateError("mutation summary missing")
        if payload["mutations_checked"] != EXPECTED_MUTATION_COUNT:
            raise StwoFineGrainedComponentSchemaGateError("mutation count drift")
        if payload["mutations_rejected"] != EXPECTED_MUTATION_COUNT:
            raise StwoFineGrainedComponentSchemaGateError("mutation rejection drift")
        if payload["all_mutations_rejected"] is not True:
            raise StwoFineGrainedComponentSchemaGateError("mutation rejection flag drift")
        cases = payload["mutation_cases"]
        if not isinstance(cases, list) or len(cases) != EXPECTED_MUTATION_COUNT:
            raise StwoFineGrainedComponentSchemaGateError("mutation case count drift")
        if [case.get("name") if isinstance(case, dict) else None for case in cases] != list(EXPECTED_MUTATION_NAMES):
            raise StwoFineGrainedComponentSchemaGateError("mutation case name drift")
        for case in cases:
            if not isinstance(case, dict) or set(case) != {"name", "rejected", "error"}:
                raise StwoFineGrainedComponentSchemaGateError("mutation case field drift")
            if case["rejected"] is not True:
                raise StwoFineGrainedComponentSchemaGateError("mutation survived")
            require_str(case["error"], "mutation error")


def mutation_cases_for(payload: dict[str, Any], *, expected_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    base = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        base.pop(key, None)
    mutations = []

    def add(name: str, fn: Any) -> None:
        mutations.append((name, fn))

    add("decision_overclaim", lambda p: p.__setitem__("decision", "GO_STABLE_BINARY_SERIALIZER"))
    add("binary_serializer_overclaim", lambda p: p.__setitem__("stable_binary_serializer_status", "GO_STABLE_BINARY_STWO_SERIALIZER"))
    add("component_schema_overclaim", lambda p: p.__setitem__("component_schema_status", "GO_STABLE_BINARY_COMPONENT_SCHEMA"))
    add("grouped_reconstruction_overclaim", lambda p: p.__setitem__("grouped_reconstruction_status", "GO_VERIFIER_FACING_BINARY_BREAKDOWN"))
    add("open_component_questions_removed", lambda p: p["open_component_questions"].pop())
    add("size_constants_smuggling", lambda p: p["size_constants"].__setitem__("secure_field_bytes", 15))
    add("typed_estimate_smuggling", lambda p: p["rows"][0].__setitem__("typed_size_estimate_bytes", p["rows"][0]["typed_size_estimate_bytes"] + 1))
    add("json_size_smuggling", lambda p: p["rows"][0].__setitem__("json_proof_size_bytes", p["rows"][0]["json_proof_size_bytes"] + 1))
    add("proof_sha256_smuggling", lambda p: p["rows"][0].__setitem__("proof_sha256", "0" * 64))
    add("malformed_proof_sha256", lambda p: p["rows"][0].__setitem__("proof_sha256", "A" * 64))
    add("component_bucket_smuggling", lambda p: p["rows"][0]["component_bytes"].__setitem__("fri_decommitment_merkle_path_bytes", p["rows"][0]["component_bytes"]["fri_decommitment_merkle_path_bytes"] + 1))
    add("grouped_reconstruction_smuggling", lambda p: p["rows"][0]["grouped_reconstruction"].__setitem__("fri_decommitments", p["rows"][0]["grouped_reconstruction"]["fri_decommitments"] + 1))
    add("aggregate_delta_smuggling", lambda p: p["aggregate"]["source_plus_sidecar_minus_fused_delta"].__setitem__("typed_size_estimate_bytes", p["aggregate"]["source_plus_sidecar_minus_fused_delta"]["typed_size_estimate_bytes"] + 1))
    add("role_total_smuggling", lambda p: p["aggregate"]["role_totals"]["fused"].__setitem__("typed_size_estimate_bytes", p["aggregate"]["role_totals"]["fused"]["typed_size_estimate_bytes"] + 1))
    add("row_order_drift", lambda p: p["rows"].reverse())
    add("profile_relabeling", lambda p: p["rows"][0].__setitem__("profile_id", "different"))
    add("role_relabeling", lambda p: p["rows"][0].__setitem__("role", "different"))
    add("non_claim_removed", lambda p: p["non_claims"].pop(0))
    add("unknown_field_injection", lambda p: p.__setitem__("unexpected", True))
    if [name for name, _fn in mutations] != list(EXPECTED_MUTATION_NAMES):
        raise StwoFineGrainedComponentSchemaGateError("mutation spec drift")
    cases = []
    for name, fn in mutations:
        candidate = copy.deepcopy(base)
        fn(candidate)
        try:
            validate_payload(candidate, allow_missing_mutation_summary=True, expected_rows=expected_rows)
        except StwoFineGrainedComponentSchemaGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "mutation survived"})
    return cases


def build_payload() -> dict[str, Any]:
    payload = build_base_payload()
    cases = mutation_cases_for(payload, expected_rows=payload["rows"])
    payload["mutation_cases"] = cases
    payload["mutations_checked"] = len(cases)
    payload["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    payload["fine_grained_component_schema_commitment"] = payload_commitment(payload)
    validate_payload(payload, expected_rows=payload["rows"])
    return payload


def to_tsv(payload: dict[str, Any], *, validate: bool = True, expected_rows: list[dict[str, Any]] | None = None) -> str:
    if validate:
        validate_payload(payload, expected_rows=expected_rows)
    rows = []
    for role in ROLES:
        totals = payload["aggregate"]["role_totals"][role]
        row = {"role": role}
        for key in TSV_COLUMNS:
            if key == "role":
                continue
            if key == "json_over_typed_size_ratio":
                row[key] = payload["aggregate"]["json_over_typed_ratio_by_role"][role]
            else:
                row[key] = totals[key]
        rows.append(row)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def require_output_path(path: pathlib.Path) -> pathlib.Path:
    resolved = (path if path.is_absolute() else ROOT / path).resolve()
    if resolved.parent != EVIDENCE_DIR.resolve():
        raise StwoFineGrainedComponentSchemaGateError("output path must be under docs/engineering/evidence")
    return resolved


def write_atomic_resolved(resolved: pathlib.Path, content: str) -> None:
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
    json_resolved = require_output_path(json_path)
    tsv_resolved = require_output_path(tsv_path)
    validate_payload(payload, expected_rows=payload["rows"])
    write_atomic_resolved(json_resolved, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_atomic_resolved(tsv_resolved, to_tsv(payload, expected_rows=payload["rows"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = build_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.no_write:
        write_outputs(payload, args.write_json or JSON_OUT, args.write_tsv or TSV_OUT)
    else:
        validate_payload(payload, expected_rows=payload["rows"])
    if not args.json:
        aggregate = payload["aggregate"]
        print(
            " ".join(
                [
                    payload["decision"],
                    str(aggregate["source_plus_sidecar_minus_fused_delta"]["typed_size_estimate_bytes"]),
                    aggregate["largest_component_saving_bucket"],
                    str(aggregate["largest_component_saving_bucket_bytes"]),
                    payload["fine_grained_component_schema_commitment"],
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
