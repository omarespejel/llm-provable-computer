#!/usr/bin/env python3
"""Typed Stwo proof-size estimate gate for issue #476.

This gate uses Stwo's own `StarkProof::size_estimate()` and
`size_breakdown_estimate()` hook through the local `zkai_stwo_proof_size_estimate`
binary. It upgrades the earlier JSON-section accounting without pretending that
Stwo exposes a stable canonical binary proof serializer.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import pathlib
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
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-typed-size-estimate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-typed-size-estimate-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-typed-size-estimate-gate-v1"
ISSUE = 476
SOURCE_ISSUES = (469, 531)
DECISION = "GO_STWO_TYPED_SIZE_ESTIMATE_BREAKDOWN_WITH_STABLE_BINARY_SERIALIZER_NO_GO"
CLAIM_BOUNDARY = (
    "STWO_TYPED_PROOF_SIZE_ESTIMATE_FOR_MATCHED_SOURCE_SIDECAR_AND_FUSED_SOFTMAX_TABLE_ROUTES_"
    "NOT_STABLE_BINARY_SERIALIZATION_NOT_SOURCE_VS_LOOKUP_COLUMN_ATTRIBUTION_NOT_TIMING"
)
ACCOUNTING_SOURCE = "stwo::core::proof::StarkProof::size_estimate_and_size_breakdown_estimate"
PROOF_PAYLOAD_KIND = "utf8_json_object_with_single_stark_proof_field"
TYPED_ESTIMATE_STATUS = "GO_STWO_TYPED_SIZE_ESTIMATE_BREAKDOWN"
STABLE_BINARY_SERIALIZER_STATUS = "NO_GO_STABLE_BINARY_STWO_PROOF_SERIALIZER_NOT_EXPOSED"
BREAKDOWN_STATUS = "GO_GROUPED_STWO_TYPED_BREAKDOWN_FINE_GRAINED_BINARY_SPLITS_NO_GO"
TIMING_POLICY = "proof_size_estimate_only_not_timing_not_public_benchmark"
UNEXPOSED_FINE_GRAINED_CATEGORIES = (
    "binary_commitment_bytes",
    "binary_sampled_opened_value_bytes",
    "binary_decommitment_merkle_path_bytes",
    "binary_fri_witness_bytes",
    "binary_fri_commitment_bytes",
    "proof_of_work_bytes",
    "config_bytes",
)
NON_CLAIMS = (
    "not stable canonical binary Stwo proof serialization",
    "not fine-grained binary commitment, FRI witness, or FRI commitment attribution",
    "not backend-internal source arithmetic versus LogUp lookup column attribution",
    "not exact public benchmark proof bytes",
    "not timing evidence",
    "not exact real-valued Softmax",
    "not full inference",
    "not recursion or PCD",
)
STWO_SIZE_ESTIMATE_TIMEOUT_SECONDS = 900
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_stwo_typed_size_estimate_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_typed_size_estimate_gate",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_size_estimate -- <envelope.json>...",
    "just gate-fast",
    "just gate",
)
TYPED_BUCKETS = (
    "oods_samples",
    "queries_values",
    "fri_samples",
    "fri_decommitments",
    "trace_decommitments",
    "fixed_unclassified_overhead",
)
ROLES = ("source", "sidecar", "fused")
TSV_COLUMNS = (
    "role",
    "json_proof_size_bytes",
    "typed_size_estimate_bytes",
    "json_over_typed_size_ratio",
    "json_minus_typed_size_bytes",
    "oods_samples",
    "queries_values",
    "fri_samples",
    "fri_decommitments",
    "trace_decommitments",
    "fixed_unclassified_overhead",
)
EXPECTED_ROLE_TOTALS = {
    "source": {
        "json_proof_size_bytes": 528_303,
        "typed_size_estimate_bytes": 201_256,
        "json_minus_typed_size_bytes": 327_047,
        "oods_samples": 90_656,
        "queries_values": 67_992,
        "fri_samples": 3_040,
        "fri_decommitments": 20_800,
        "trace_decommitments": 18_336,
        "fixed_unclassified_overhead": 432,
    },
    "sidecar": {
        "json_proof_size_bytes": 187_827,
        "typed_size_estimate_bytes": 52_616,
        "json_minus_typed_size_bytes": 135_211,
        "oods_samples": 3_168,
        "queries_values": 1_944,
        "fri_samples": 2_976,
        "fri_decommitments": 20_160,
        "trace_decommitments": 23_936,
        "fixed_unclassified_overhead": 432,
    },
    "fused": {
        "json_proof_size_bytes": 563_139,
        "typed_size_estimate_bytes": 211_380,
        "json_minus_typed_size_bytes": 351_759,
        "oods_samples": 92_528,
        "queries_values": 68_964,
        "fri_samples": 3_120,
        "fri_decommitments": 21_376,
        "trace_decommitments": 24_960,
        "fixed_unclassified_overhead": 432,
    },
}
EXPECTED_DELTA_TOTALS = {
    "json_proof_size_bytes": 152_991,
    "typed_size_estimate_bytes": 42_492,
    "json_minus_typed_size_bytes": 110_499,
    "oods_samples": 1_296,
    "queries_values": 972,
    "fri_samples": 2_896,
    "fri_decommitments": 19_584,
    "trace_decommitments": 17_312,
    "fixed_unclassified_overhead": 432,
}
EXPECTED_JSON_OVER_TYPED_RATIO_BY_ROLE = {
    "source": 2.62503,
    "sidecar": 3.56977,
    "fused": 2.664107,
}
EXPECTED_TYPED_SAVING_SHARE = 0.167376
EXPECTED_JSON_SAVING_SHARE = 0.213636
EXPECTED_MUTATION_NAMES = (
    "decision_overclaim",
    "binary_serializer_overclaim",
    "fine_grained_breakdown_overclaim",
    "unexposed_categories_removed",
    "typed_estimate_smuggling",
    "json_size_smuggling",
    "typed_bucket_smuggling",
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
    "typed_breakdown",
    "typed_breakdown_sum_bytes",
    "json_over_typed_size_ratio",
    "json_minus_typed_size_bytes",
}


class StwoTypedSizeEstimateGateError(ValueError):
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
        raise StwoTypedSizeEstimateGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StwoTypedSizeEstimateGateError(f"{label} must be an integer")
    return value


def require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise StwoTypedSizeEstimateGateError(f"{label} must be a non-empty string")
    return value


def output_tail(value: str, limit: int = 1600) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[-limit:]


def section_delta_rows() -> list[dict[str, Any]]:
    payload = section_delta.build_payload()
    return payload["profile_rows"]


def artifact_specs(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    specs = []
    for row in rows:
        for role in ROLES:
            specs.append({"profile_id": row["profile_id"], "role": role, "path": row["artifacts"][role]["path"]})
    return specs


def run_stwo_size_estimate(paths: list[str]) -> dict[str, Any]:
    command = [
        "cargo",
        "+nightly-2025-07-14",
        "run",
        "--quiet",
        "--locked",
        "--features",
        "stwo-backend",
        "--bin",
        "zkai_stwo_proof_size_estimate",
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
            timeout=STWO_SIZE_ESTIMATE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as err:
        raise StwoTypedSizeEstimateGateError(
            f"Stwo size estimate CLI timed out after {STWO_SIZE_ESTIMATE_TIMEOUT_SECONDS}s"
        ) from err
    except OSError as err:
        raise StwoTypedSizeEstimateGateError(f"failed to run Stwo size estimate CLI: {err}") from err
    if completed.returncode != 0:
        stderr = output_tail(completed.stderr)
        stdout = output_tail(completed.stdout)
        detail = stderr or stdout or "<no output>"
        raise StwoTypedSizeEstimateGateError(
            f"Stwo size estimate CLI failed with exit code {completed.returncode}: {detail}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise StwoTypedSizeEstimateGateError(f"Stwo size estimate CLI did not emit JSON: {err}") from err


def build_rows() -> list[dict[str, Any]]:
    specs = artifact_specs(section_delta_rows())
    cli = run_stwo_size_estimate([spec["path"] for spec in specs])
    if cli.get("schema") != "zkai-stwo-proof-size-estimate-cli-v1":
        raise StwoTypedSizeEstimateGateError("CLI schema drift")
    if cli.get("accounting_source") != ACCOUNTING_SOURCE:
        raise StwoTypedSizeEstimateGateError("CLI accounting source drift")
    if cli.get("proof_payload_kind") != PROOF_PAYLOAD_KIND:
        raise StwoTypedSizeEstimateGateError("CLI proof payload kind drift")
    if cli.get("stable_binary_serializer_status") != STABLE_BINARY_SERIALIZER_STATUS:
        raise StwoTypedSizeEstimateGateError("CLI binary serializer status drift")
    if cli.get("breakdown_status") != BREAKDOWN_STATUS:
        raise StwoTypedSizeEstimateGateError("CLI breakdown status drift")
    if cli.get("unexposed_fine_grained_categories") != list(UNEXPOSED_FINE_GRAINED_CATEGORIES):
        raise StwoTypedSizeEstimateGateError("CLI unexposed category drift")
    cli_rows = cli.get("rows")
    if not isinstance(cli_rows, list) or len(cli_rows) != len(specs):
        raise StwoTypedSizeEstimateGateError("CLI row count drift")
    rows = []
    for spec, cli_row in zip(specs, cli_rows):
        if not isinstance(cli_row, dict) or set(cli_row) != CLI_ROW_KEYS:
            raise StwoTypedSizeEstimateGateError("CLI row field drift")
        if cli_row["path"] != spec["path"]:
            raise StwoTypedSizeEstimateGateError("CLI row path drift")
        try:
            row = {
                "profile_id": spec["profile_id"],
                "role": spec["role"],
                "path": spec["path"],
                "proof_sha256": cli_row["proof_sha256"],
                "json_proof_size_bytes": cli_row["json_proof_size_bytes"],
                "typed_size_estimate_bytes": cli_row["typed_size_estimate_bytes"],
                "typed_breakdown": cli_row["typed_breakdown"],
                "typed_breakdown_sum_bytes": cli_row["typed_breakdown_sum_bytes"],
                "json_over_typed_size_ratio": cli_row["json_over_typed_size_ratio"],
                "json_minus_typed_size_bytes": cli_row["json_minus_typed_size_bytes"],
            }
        except (KeyError, TypeError) as err:
            raise StwoTypedSizeEstimateGateError("CLI row field drift") from err
        validate_row(row)
        rows.append(row)
    return rows


def validate_row(row: Any) -> None:
    expected = {
        "profile_id",
        "role",
        "path",
        "proof_sha256",
        "json_proof_size_bytes",
        "typed_size_estimate_bytes",
        "typed_breakdown",
        "typed_breakdown_sum_bytes",
        "json_over_typed_size_ratio",
        "json_minus_typed_size_bytes",
    }
    if not isinstance(row, dict) or set(row) != expected:
        raise StwoTypedSizeEstimateGateError("row field drift")
    if row["profile_id"] not in section_delta.EXPECTED_PROFILE_IDS:
        raise StwoTypedSizeEstimateGateError("profile_id drift")
    if row["role"] not in ROLES:
        raise StwoTypedSizeEstimateGateError("role drift")
    require_str(row["path"], "path")
    require_str(row["proof_sha256"], "proof_sha256")
    json_size = require_int(row["json_proof_size_bytes"], "json_proof_size_bytes")
    typed_size = require_int(row["typed_size_estimate_bytes"], "typed_size_estimate_bytes")
    if json_size <= 0 or typed_size <= 0:
        raise StwoTypedSizeEstimateGateError("proof sizes must be positive")
    breakdown = row["typed_breakdown"]
    if not isinstance(breakdown, dict) or set(breakdown) != set(TYPED_BUCKETS):
        raise StwoTypedSizeEstimateGateError("typed breakdown field drift")
    for key in TYPED_BUCKETS:
        if require_int(breakdown[key], key) < 0:
            raise StwoTypedSizeEstimateGateError("typed breakdown bucket must be non-negative")
    if sum(breakdown.values()) != typed_size:
        raise StwoTypedSizeEstimateGateError("typed estimate breakdown sum drift")
    typed_breakdown_sum = require_int(row["typed_breakdown_sum_bytes"], "typed_breakdown_sum_bytes")
    json_minus_typed = require_int(row["json_minus_typed_size_bytes"], "json_minus_typed_size_bytes")
    if typed_breakdown_sum != typed_size - breakdown["fixed_unclassified_overhead"]:
        raise StwoTypedSizeEstimateGateError("typed exposed breakdown sum drift")
    if json_minus_typed != json_size - typed_size:
        raise StwoTypedSizeEstimateGateError("json-minus-typed drift")
    ratio_value = row["json_over_typed_size_ratio"]
    if isinstance(ratio_value, bool) or not isinstance(ratio_value, (int, float)):
        raise StwoTypedSizeEstimateGateError("json-over-typed ratio must be numeric")
    if not math.isclose(
        float(ratio_value),
        ratio(json_size, typed_size),
        rel_tol=0.0,
        abs_tol=0.000001,
    ):
        raise StwoTypedSizeEstimateGateError("json-over-typed ratio drift")


def build_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    role_totals = {}
    for role in ROLES:
        role_rows = [row for row in rows if row["role"] == role]
        role_totals[role] = {
            "json_proof_size_bytes": sum(row["json_proof_size_bytes"] for row in role_rows),
            "typed_size_estimate_bytes": sum(row["typed_size_estimate_bytes"] for row in role_rows),
            "json_minus_typed_size_bytes": sum(row["json_minus_typed_size_bytes"] for row in role_rows),
            **{key: sum(row["typed_breakdown"][key] for row in role_rows) for key in TYPED_BUCKETS},
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
        "largest_typed_saving_bucket": max(TYPED_BUCKETS, key=lambda key: delta[key]),
        "largest_typed_saving_bucket_bytes": max(delta[key] for key in TYPED_BUCKETS),
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
        "largest_typed_saving_bucket",
        "largest_typed_saving_bucket_bytes",
    }
    if not isinstance(aggregate, dict) or set(aggregate) != expected:
        raise StwoTypedSizeEstimateGateError("aggregate field drift")
    if aggregate["profiles_checked"] != len(section_delta.EXPECTED_PROFILE_IDS):
        raise StwoTypedSizeEstimateGateError("profile count drift")
    if aggregate["artifacts_checked"] != len(section_delta.EXPECTED_PROFILE_IDS) * len(ROLES):
        raise StwoTypedSizeEstimateGateError("artifact count drift")
    if aggregate["role_totals"] != EXPECTED_ROLE_TOTALS:
        raise StwoTypedSizeEstimateGateError("role totals drift")
    if aggregate["source_plus_sidecar_minus_fused_delta"] != EXPECTED_DELTA_TOTALS:
        raise StwoTypedSizeEstimateGateError("delta totals drift")
    expected_source_plus_sidecar = {
        key: EXPECTED_ROLE_TOTALS["source"][key] + EXPECTED_ROLE_TOTALS["sidecar"][key]
        for key in EXPECTED_ROLE_TOTALS["source"]
    }
    if aggregate["source_plus_sidecar_totals"] != expected_source_plus_sidecar:
        raise StwoTypedSizeEstimateGateError("source-plus-sidecar totals drift")
    if aggregate["json_over_typed_ratio_by_role"] != EXPECTED_JSON_OVER_TYPED_RATIO_BY_ROLE:
        raise StwoTypedSizeEstimateGateError("json-over-typed role ratio drift")
    if aggregate["typed_saving_share_vs_source_plus_sidecar"] != EXPECTED_TYPED_SAVING_SHARE:
        raise StwoTypedSizeEstimateGateError("typed saving share drift")
    if aggregate["json_saving_share_vs_source_plus_sidecar"] != EXPECTED_JSON_SAVING_SHARE:
        raise StwoTypedSizeEstimateGateError("json saving share drift")
    if aggregate["largest_typed_saving_bucket"] != "fri_decommitments":
        raise StwoTypedSizeEstimateGateError("largest typed saving bucket drift")
    if aggregate["largest_typed_saving_bucket_bytes"] != 19_584:
        raise StwoTypedSizeEstimateGateError("largest typed saving bucket bytes drift")


def payload_commitment(payload: dict[str, Any]) -> str:
    payload_for_commitment = copy.deepcopy(payload)
    payload_for_commitment.pop("typed_size_estimate_commitment", None)
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
        "typed_estimate_status": TYPED_ESTIMATE_STATUS,
        "stable_binary_serializer_status": STABLE_BINARY_SERIALIZER_STATUS,
        "breakdown_status": BREAKDOWN_STATUS,
        "unexposed_fine_grained_categories": list(UNEXPOSED_FINE_GRAINED_CATEGORIES),
        "timing_policy": TIMING_POLICY,
        "profile_ids": list(section_delta.EXPECTED_PROFILE_IDS),
        "rows": rows,
        "aggregate": build_aggregate(rows),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["typed_size_estimate_commitment"] = payload_commitment(payload)
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
        "typed_estimate_status",
        "stable_binary_serializer_status",
        "breakdown_status",
        "unexposed_fine_grained_categories",
        "timing_policy",
        "profile_ids",
        "rows",
        "aggregate",
        "non_claims",
        "validation_commands",
        "typed_size_estimate_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if not isinstance(payload, dict) or set(payload) - (expected | mutation_keys):
        raise StwoTypedSizeEstimateGateError("payload field drift")
    if expected - set(payload):
        raise StwoTypedSizeEstimateGateError("payload field drift")
    for key, expected_value in (
        ("schema", SCHEMA),
        ("issue", ISSUE),
        ("source_issues", list(SOURCE_ISSUES)),
        ("decision", DECISION),
        ("claim_boundary", CLAIM_BOUNDARY),
        ("accounting_source", ACCOUNTING_SOURCE),
        ("proof_payload_kind", PROOF_PAYLOAD_KIND),
        ("typed_estimate_status", TYPED_ESTIMATE_STATUS),
        ("stable_binary_serializer_status", STABLE_BINARY_SERIALIZER_STATUS),
        ("breakdown_status", BREAKDOWN_STATUS),
        ("unexposed_fine_grained_categories", list(UNEXPOSED_FINE_GRAINED_CATEGORIES)),
        ("timing_policy", TIMING_POLICY),
        ("profile_ids", list(section_delta.EXPECTED_PROFILE_IDS)),
        ("non_claims", list(NON_CLAIMS)),
        ("validation_commands", list(VALIDATION_COMMANDS)),
    ):
        if payload[key] != expected_value:
            raise StwoTypedSizeEstimateGateError(f"{key} drift")
    rows = payload["rows"]
    if not isinstance(rows, list) or len(rows) != len(section_delta.EXPECTED_PROFILE_IDS) * len(ROLES):
        raise StwoTypedSizeEstimateGateError("row count drift")
    for row in rows:
        validate_row(row)
    expected_pairs = [
        (profile_id, role)
        for profile_id in section_delta.EXPECTED_PROFILE_IDS
        for role in ROLES
    ]
    observed_pairs = [(row["profile_id"], row["role"]) for row in rows]
    if observed_pairs != expected_pairs:
        raise StwoTypedSizeEstimateGateError("row order drift")
    if expected_rows is None:
        expected_rows = rows
    elif rows != expected_rows:
        raise StwoTypedSizeEstimateGateError("row drift")
    expected_aggregate = build_aggregate(expected_rows)
    if payload["aggregate"] != expected_aggregate:
        raise StwoTypedSizeEstimateGateError("aggregate drift")
    validate_aggregate(payload["aggregate"])
    if payload_commitment(payload) != payload["typed_size_estimate_commitment"]:
        raise StwoTypedSizeEstimateGateError("commitment drift")
    if not allow_missing_mutation_summary or any(key in payload for key in mutation_keys):
        if not mutation_keys <= set(payload):
            raise StwoTypedSizeEstimateGateError("mutation summary missing")
        if payload["mutations_checked"] != EXPECTED_MUTATION_COUNT:
            raise StwoTypedSizeEstimateGateError("mutation count drift")
        if payload["mutations_rejected"] != EXPECTED_MUTATION_COUNT:
            raise StwoTypedSizeEstimateGateError("mutation rejection drift")
        if payload["all_mutations_rejected"] is not True:
            raise StwoTypedSizeEstimateGateError("mutation rejection flag drift")
        cases = payload["mutation_cases"]
        if not isinstance(cases, list) or len(cases) != EXPECTED_MUTATION_COUNT:
            raise StwoTypedSizeEstimateGateError("mutation case count drift")
        if [case.get("name") if isinstance(case, dict) else None for case in cases] != list(EXPECTED_MUTATION_NAMES):
            raise StwoTypedSizeEstimateGateError("mutation case name drift")
        for case in cases:
            if not isinstance(case, dict) or set(case) != {"name", "rejected", "error"}:
                raise StwoTypedSizeEstimateGateError("mutation case field drift")
            if case["rejected"] is not True:
                raise StwoTypedSizeEstimateGateError("mutation survived")
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
    add("fine_grained_breakdown_overclaim", lambda p: p.__setitem__("breakdown_status", "GO_FINE_GRAINED_BINARY_BREAKDOWN"))
    add("unexposed_categories_removed", lambda p: p["unexposed_fine_grained_categories"].pop())
    add("typed_estimate_smuggling", lambda p: p["rows"][0].__setitem__("typed_size_estimate_bytes", p["rows"][0]["typed_size_estimate_bytes"] + 1))
    add("json_size_smuggling", lambda p: p["rows"][0].__setitem__("json_proof_size_bytes", p["rows"][0]["json_proof_size_bytes"] + 1))
    add("typed_bucket_smuggling", lambda p: p["rows"][0]["typed_breakdown"].__setitem__("fri_decommitments", p["rows"][0]["typed_breakdown"]["fri_decommitments"] + 1))
    add("aggregate_delta_smuggling", lambda p: p["aggregate"]["source_plus_sidecar_minus_fused_delta"].__setitem__("typed_size_estimate_bytes", p["aggregate"]["source_plus_sidecar_minus_fused_delta"]["typed_size_estimate_bytes"] + 1))
    add("role_total_smuggling", lambda p: p["aggregate"]["role_totals"]["fused"].__setitem__("typed_size_estimate_bytes", p["aggregate"]["role_totals"]["fused"]["typed_size_estimate_bytes"] + 1))
    add("row_order_drift", lambda p: p["rows"].reverse())
    add("profile_relabeling", lambda p: p["rows"][0].__setitem__("profile_id", "different"))
    add("role_relabeling", lambda p: p["rows"][0].__setitem__("role", "different"))
    add("non_claim_removed", lambda p: p["non_claims"].pop(0))
    add("unknown_field_injection", lambda p: p.__setitem__("unexpected", True))
    if [name for name, _fn in mutations] != list(EXPECTED_MUTATION_NAMES):
        raise StwoTypedSizeEstimateGateError("mutation spec drift")
    cases = []
    for name, fn in mutations:
        candidate = copy.deepcopy(base)
        fn(candidate)
        try:
            validate_payload(candidate, allow_missing_mutation_summary=True, expected_rows=expected_rows)
        except StwoTypedSizeEstimateGateError as err:
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
    payload["typed_size_estimate_commitment"] = payload_commitment(payload)
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
        raise StwoTypedSizeEstimateGateError("output path must be under docs/engineering/evidence")
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
                    aggregate["largest_typed_saving_bucket"],
                    str(aggregate["largest_typed_saving_bucket_bytes"]),
                    payload["typed_size_estimate_commitment"],
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
