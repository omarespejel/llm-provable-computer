#!/usr/bin/env python3
"""Median-of-5 verifier timing gate for existing Stwo Softmax-table envelopes.

This gate is engineering-local.  It times already checked source arithmetic,
LogUp sidecar, and fused envelopes with the repo-owned Rust timing binary.  It
does not generate proofs and does not make public benchmark claims.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-softmax-table-median-timing-gate-v1"
CLI_SCHEMA = "zkai-attention-kv-stwo-softmax-table-median-timing-cli-v1"
DECISION = "GO_ENGINEERING_LOCAL_MEDIAN_OF_5_VERIFY_TIMING_HARNESS"
ROUTE_FAMILY = "stwo_softmax_table_source_sidecar_fused_route_family"
TIMING_POLICY = "median_of_5_existing_typed_envelope_verifier_runs_microsecond_capture_engineering_only"
TIMING_SCOPE = "existing_envelope_loaded_once_then_typed_stwo_verify_function_timed_in_process"
CLAIM_BOUNDARY = (
    "ENGINEERING_LOCAL_VERIFY_EXISTING_ENVELOPE_TIMING_FOR_STWO_SOFTMAX_TABLE_ROUTE_FAMILY_"
    "NOT_PUBLIC_BENCHMARK_NOT_PROVER_TIMING_NOT_CARGO_OR_BUILD_TIMING_NOT_REAL_SOFTMAX_"
    "NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD"
)
MEASUREMENT_STATUS = "ENGINEERING_LOCAL_OBSERVATION_ONLY_NOT_PUBLIC_BENCHMARK"
RUNS_PER_ENVELOPE = 5
TIMING_CLI_TIMEOUT_SECONDS = 1800
NON_CLAIMS = (
    "not prover timing",
    "not cargo or build timing",
    "not subprocess timing",
    "not a public benchmark",
    "not exact real-valued Softmax",
    "not full inference",
    "not recursion or PCD",
)
VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --release --features stwo-backend --bin zkai_attention_kv_stwo_softmax_table_timing -- --evidence-dir docs/engineering/evidence --runs 5",
    "python3 scripts/zkai_attention_kv_stwo_median_timing_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_median_timing_gate",
    "cargo +nightly-2025-07-14 test --locked --release --features stwo-backend --bin zkai_attention_kv_stwo_softmax_table_timing",
    "cargo +nightly-2025-07-14 fmt --check",
    "git diff --check",
)
CLI_VALIDATION_COMMANDS = VALIDATION_COMMANDS[:4]
EXPECTED_SAFETY = {
    "max_envelope_json_bytes": 16 * 1024 * 1024,
    "path_policy": "relative_paths_must_be_regular_non_symlink_files_inside_canonical_evidence_dir",
    "timed_window_excludes_cargo_build_subprocess_startup_file_read_and_json_deserialize": True,
}
TSV_COLUMNS = (
    "profile_id",
    "axis_role",
    "role",
    "key_width",
    "value_width",
    "head_count",
    "steps_per_head",
    "proof_size_bytes",
    "envelope_size_bytes",
    "verify_median_us",
    "verify_min_us",
    "verify_max_us",
    "verify_runs_us",
    "source_plus_sidecar_verify_median_us",
    "fused_verify_median_us",
    "fused_to_source_plus_sidecar_verify_median_ratio",
    "timing_status",
)
MUTATION_NAMES = (
    "decision_relabeling",
    "timing_policy_public_benchmark_overclaim",
    "claim_boundary_prover_timing_overclaim",
    "run_count_metric_smuggling",
    "route_row_order_drift",
    "route_row_role_relabeling",
    "route_row_median_metric_smuggling",
    "route_row_runs_metric_smuggling",
    "profile_source_plus_sidecar_metric_smuggling",
    "profile_ratio_metric_smuggling",
    "non_claim_removed",
    "validation_command_removed",
    "unknown_field_injection",
)


class StwoMedianTimingGateError(ValueError):
    pass


def expected_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(profile_id: str, axis_role: str, key_width: int, value_width: int, head_count: int, steps: int, suffix: str) -> None:
        rows.extend(
            [
                {
                    "profile_id": profile_id,
                    "axis_role": axis_role,
                    "key_width": key_width,
                    "value_width": value_width,
                    "head_count": head_count,
                    "steps_per_head": steps,
                    "role": "source_arithmetic",
                    "evidence_relative_path": f"zkai-attention-kv-stwo-native-{suffix}-bounded-softmax-table-proof-2026-05.envelope.json",
                },
                {
                    "profile_id": profile_id,
                    "axis_role": axis_role,
                    "key_width": key_width,
                    "value_width": value_width,
                    "head_count": head_count,
                    "steps_per_head": steps,
                    "role": "logup_sidecar",
                    "evidence_relative_path": f"zkai-attention-kv-stwo-native-{suffix}-softmax-table-logup-sidecar-proof-2026-05.envelope.json",
                },
                {
                    "profile_id": profile_id,
                    "axis_role": axis_role,
                    "key_width": key_width,
                    "value_width": value_width,
                    "head_count": head_count,
                    "steps_per_head": steps,
                    "role": "fused",
                    "evidence_relative_path": f"zkai-attention-kv-stwo-native-{suffix}-fused-softmax-table-proof-2026-05.envelope.json",
                },
            ]
        )

    add("d8_single_head_seq8", "baseline", 8, 8, 1, 8, "d8")
    add("d16_single_head_seq8", "width_axis", 16, 16, 1, 8, "d16")
    add("d32_single_head_seq8", "width_axis_extension", 32, 32, 1, 8, "d32")
    add("d8_two_head_seq8", "head_axis", 8, 8, 2, 8, "two-head")
    add("d8_four_head_seq8", "head_axis_extension", 8, 8, 4, 8, "four-head")
    add("d8_eight_head_seq8", "head_axis_extension", 8, 8, 8, 8, "eight-head")
    add("d8_sixteen_head_seq8", "head_axis_extension", 8, 8, 16, 8, "sixteen-head")
    add("d8_two_head_seq16", "sequence_axis", 8, 8, 2, 16, "two-head-longseq")
    add("d8_two_head_seq32", "sequence_axis_extension", 8, 8, 2, 32, "two-head-seq32")
    add("d16_two_head_seq8", "combined_width_head_axis", 16, 16, 2, 8, "d16-two-head")
    add("d16_two_head_seq16", "combined_width_head_sequence_axis", 16, 16, 2, 16, "d16-two-head-longseq")
    return rows


EXPECTED_ROWS = tuple(expected_rows())
EXPECTED_PROFILE_IDS = tuple(row["profile_id"] for row in EXPECTED_ROWS[::3])


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def round6(value: float) -> float:
    rounded = math.floor(abs(value) * 1_000_000 + 0.5) / 1_000_000
    return math.copysign(rounded, value)


def require_exact_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StwoMedianTimingGateError(f"{label} must be an integer")
    return value


def require_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, float):
        raise StwoMedianTimingGateError(f"{label} must be a float")
    return value


def require_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StwoMedianTimingGateError(f"{label} must be a number")
    return float(value)


def require_sha256_hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise StwoMedianTimingGateError(f"{label} digest invalid")
    try:
        bytes.fromhex(value)
    except ValueError as err:
        raise StwoMedianTimingGateError(f"{label} digest invalid") from err
    return value


def output_tail(value: str | None, limit: int = 1600) -> str:
    if value is None:
        return ""
    value = value.strip()
    return value if len(value) <= limit else value[-limit:]


def run_timing_cli() -> dict[str, Any]:
    command = [
        "cargo",
        "+nightly-2025-07-14",
        "run",
        "--locked",
        "--release",
        "--features",
        "stwo-backend",
        "--bin",
        "zkai_attention_kv_stwo_softmax_table_timing",
        "--",
        "--evidence-dir",
        str(EVIDENCE_DIR),
        "--runs",
        str(RUNS_PER_ENVELOPE),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=TIMING_CLI_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as err:
        stderr = output_tail(err.stderr if isinstance(err.stderr, str) else None)
        stdout = output_tail(err.stdout if isinstance(err.stdout, str) else None)
        detail = stderr or stdout or "<no output>"
        raise StwoMedianTimingGateError(
            f"timing CLI timed out after {TIMING_CLI_TIMEOUT_SECONDS}s: {detail}"
        ) from err
    except OSError as err:
        raise StwoMedianTimingGateError(f"failed to run timing CLI: {err}") from err
    if completed.returncode != 0:
        detail = output_tail(completed.stderr) or output_tail(completed.stdout) or "<no output>"
        raise StwoMedianTimingGateError(f"timing CLI failed with exit {completed.returncode}: {detail}")
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise StwoMedianTimingGateError(f"timing CLI emitted invalid JSON: {err}") from err
    validate_cli_summary(summary)
    return summary


def validate_cli_summary(summary: Any) -> None:
    if not isinstance(summary, dict):
        raise StwoMedianTimingGateError("CLI summary must be an object")
    expected_keys = {
        "schema",
        "decision",
        "route_family",
        "timing_policy",
        "timing_scope",
        "claim_boundary",
        "runs_per_envelope",
        "clock",
        "safety",
        "non_claims",
        "validation_commands",
        "rows",
        "profile_summaries",
    }
    if set(summary) != expected_keys:
        raise StwoMedianTimingGateError("CLI summary field drift")
    if summary["schema"] != CLI_SCHEMA:
        raise StwoMedianTimingGateError("CLI schema drift")
    for key, expected in (
        ("decision", DECISION),
        ("route_family", ROUTE_FAMILY),
        ("timing_policy", TIMING_POLICY),
        ("timing_scope", TIMING_SCOPE),
        ("claim_boundary", CLAIM_BOUNDARY),
    ):
        if summary[key] != expected:
            raise StwoMedianTimingGateError(f"CLI {key} drift")
    if require_exact_int(summary["runs_per_envelope"], "runs_per_envelope") != RUNS_PER_ENVELOPE:
        raise StwoMedianTimingGateError("CLI run count drift")
    if summary["clock"] != "std_time_instant_elapsed_as_micros":
        raise StwoMedianTimingGateError("CLI clock drift")
    if summary["safety"] != EXPECTED_SAFETY:
        raise StwoMedianTimingGateError("CLI safety drift")
    if tuple(summary["non_claims"]) != NON_CLAIMS:
        raise StwoMedianTimingGateError("CLI non-claims drift")
    if not isinstance(summary["validation_commands"], list) or tuple(summary["validation_commands"]) != CLI_VALIDATION_COMMANDS:
        raise StwoMedianTimingGateError("CLI validation command drift")
    rows = summary["rows"]
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_ROWS):
        raise StwoMedianTimingGateError("CLI route row count drift")
    for row, expected in zip(rows, EXPECTED_ROWS, strict=True):
        validate_cli_row(row, expected)
    summaries = summary["profile_summaries"]
    if not isinstance(summaries, list) or len(summaries) != len(EXPECTED_PROFILE_IDS):
        raise StwoMedianTimingGateError("CLI profile summary count drift")
    for profile_summary, chunk in zip(summaries, chunks(rows, 3), strict=True):
        validate_profile_summary(profile_summary, chunk)


def validate_cli_row(row: Any, expected: dict[str, Any]) -> None:
    if not isinstance(row, dict):
        raise StwoMedianTimingGateError("CLI row must be an object")
    expected_keys = {
        "profile_id",
        "axis_role",
        "key_width",
        "value_width",
        "head_count",
        "steps_per_head",
        "role",
        "evidence_relative_path",
        "envelope_sha256",
        "proof_backend",
        "proof_backend_version",
        "statement_version",
        "proof_schema_version",
        "target_id",
        "verifier_domain",
        "proof_size_bytes",
        "envelope_size_bytes",
        "verify_runs_us",
        "verify_median_us",
        "verify_min_us",
        "verify_max_us",
        "verified",
    }
    if set(row) != expected_keys:
        raise StwoMedianTimingGateError("CLI row field drift")
    for key, value in expected.items():
        if row[key] != value:
            raise StwoMedianTimingGateError(f"{expected['profile_id']} {expected['role']} {key} drift")
    require_sha256_hex(row["envelope_sha256"], "envelope_sha256")
    if row["proof_backend"] != "stwo":
        raise StwoMedianTimingGateError("proof_backend drift")
    for key in ("proof_backend_version", "statement_version"):
        if not isinstance(row[key], str) or not row[key]:
            raise StwoMedianTimingGateError(f"{key} must be a non-empty string")
    for key in ("proof_schema_version", "target_id", "verifier_domain"):
        if row[key] is not None and (not isinstance(row[key], str) or not row[key]):
            raise StwoMedianTimingGateError(f"{key} must be string or null")
    proof_size = require_exact_int(row["proof_size_bytes"], "proof_size_bytes")
    envelope_size = require_exact_int(row["envelope_size_bytes"], "envelope_size_bytes")
    if proof_size <= 0 or envelope_size <= proof_size:
        raise StwoMedianTimingGateError("proof/envelope size invariant drift")
    runs = row["verify_runs_us"]
    if not isinstance(runs, list) or len(runs) != RUNS_PER_ENVELOPE:
        raise StwoMedianTimingGateError("verify run count drift")
    run_values = [require_exact_int(value, "verify_runs_us") for value in runs]
    if any(value <= 0 for value in run_values):
        raise StwoMedianTimingGateError("verify runs must be positive")
    median = require_exact_int(row["verify_median_us"], "verify_median_us")
    if median != sorted(run_values)[len(run_values) // 2]:
        raise StwoMedianTimingGateError("verify median drift")
    if require_exact_int(row["verify_min_us"], "verify_min_us") != min(run_values):
        raise StwoMedianTimingGateError("verify min drift")
    if require_exact_int(row["verify_max_us"], "verify_max_us") != max(run_values):
        raise StwoMedianTimingGateError("verify max drift")
    if row["verified"] is not True:
        raise StwoMedianTimingGateError("verified flag drift")


def validate_profile_summary(summary: Any, rows: list[dict[str, Any]]) -> None:
    if not isinstance(summary, dict):
        raise StwoMedianTimingGateError("profile summary must be an object")
    expected_keys = {
        "profile_id",
        "axis_role",
        "key_width",
        "value_width",
        "head_count",
        "steps_per_head",
        "source_plus_sidecar_verify_median_us",
        "fused_verify_median_us",
        "fused_minus_source_plus_sidecar_verify_median_us",
        "fused_to_source_plus_sidecar_verify_median_ratio",
        "timing_status",
    }
    if set(summary) != expected_keys:
        raise StwoMedianTimingGateError("profile summary field drift")
    source, sidecar, fused = rows
    for key in ("profile_id", "axis_role", "key_width", "value_width", "head_count", "steps_per_head"):
        if summary[key] != source[key]:
            raise StwoMedianTimingGateError(f"profile summary {key} drift")
    source_plus_sidecar = source["verify_median_us"] + sidecar["verify_median_us"]
    fused_median = fused["verify_median_us"]
    if require_exact_int(summary["source_plus_sidecar_verify_median_us"], "source_plus_sidecar_verify_median_us") != source_plus_sidecar:
        raise StwoMedianTimingGateError("source+sidecar median drift")
    if require_exact_int(summary["fused_verify_median_us"], "fused_verify_median_us") != fused_median:
        raise StwoMedianTimingGateError("fused median drift")
    expected_delta = fused_median - source_plus_sidecar
    if require_exact_int(summary["fused_minus_source_plus_sidecar_verify_median_us"], "fused delta") != expected_delta:
        raise StwoMedianTimingGateError("fused delta drift")
    ratio = require_number(summary["fused_to_source_plus_sidecar_verify_median_ratio"], "fused ratio")
    expected_ratio = round6(fused_median / source_plus_sidecar)
    if not math.isclose(ratio, expected_ratio, rel_tol=0.0, abs_tol=1e-12):
        raise StwoMedianTimingGateError("fused ratio drift")
    if summary["timing_status"] != MEASUREMENT_STATUS:
        raise StwoMedianTimingGateError("timing status drift")


def chunks(values: list[Any], size: int) -> list[list[Any]]:
    if len(values) % size != 0:
        raise StwoMedianTimingGateError("chunk size drift")
    return [values[index : index + size] for index in range(0, len(values), size)]


def payload_commitment(payload: dict[str, Any]) -> str:
    without_commitment = copy.deepcopy(payload)
    without_commitment.pop("payload_commitment", None)
    return blake2b_commitment(without_commitment, "zkai:stwo:softmax-table:median-timing:payload:v1")


def build_payload(cli_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = cli_summary if cli_summary is not None else run_timing_cli()
    validate_cli_summary(summary)
    rows = copy.deepcopy(summary["rows"])
    profile_summaries = copy.deepcopy(summary["profile_summaries"])
    aggregate = {
        "profiles_checked": len(profile_summaries),
        "route_rows_checked": len(rows),
        "verifier_runs_captured": len(rows) * RUNS_PER_ENVELOPE,
        "max_fused_verify_median_us": max(item["fused_verify_median_us"] for item in profile_summaries),
        "min_fused_verify_median_us": min(item["fused_verify_median_us"] for item in profile_summaries),
        "max_source_plus_sidecar_verify_median_us": max(
            item["source_plus_sidecar_verify_median_us"] for item in profile_summaries
        ),
        "min_source_plus_sidecar_verify_median_us": min(
            item["source_plus_sidecar_verify_median_us"] for item in profile_summaries
        ),
    }
    payload = {
        "schema": SCHEMA,
        "source_cli_schema": CLI_SCHEMA,
        "decision": DECISION,
        "route_family": ROUTE_FAMILY,
        "timing_policy": TIMING_POLICY,
        "timing_scope": TIMING_SCOPE,
        "claim_boundary": CLAIM_BOUNDARY,
        "measurement_status": MEASUREMENT_STATUS,
        "runs_per_envelope": RUNS_PER_ENVELOPE,
        "rows": rows,
        "profile_summaries": profile_summaries,
        "aggregate": aggregate,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["payload_commitment"] = payload_commitment(payload)
    mutation_results = evaluate_mutations(payload, summary)
    payload["mutation_cases"] = mutation_results
    payload["mutations_checked"] = len(mutation_results)
    payload["mutations_rejected"] = sum(1 for result in mutation_results if result["rejected"])
    payload["all_mutations_rejected"] = all(result["rejected"] for result in mutation_results)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload, summary)
    return payload


def validate_payload(payload: Any, cli_summary: dict[str, Any], *, allow_missing_mutation_summary: bool = False) -> None:
    validate_cli_summary(cli_summary)
    if not isinstance(payload, dict):
        raise StwoMedianTimingGateError("payload must be an object")
    expected_keys = {
        "schema",
        "source_cli_schema",
        "decision",
        "route_family",
        "timing_policy",
        "timing_scope",
        "claim_boundary",
        "measurement_status",
        "runs_per_envelope",
        "rows",
        "profile_summaries",
        "aggregate",
        "non_claims",
        "validation_commands",
        "payload_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if allow_missing_mutation_summary:
        allowed = expected_keys | mutation_keys
        if not expected_keys.issubset(payload) or set(payload) - allowed:
            raise StwoMedianTimingGateError("payload field drift")
    elif set(payload) != expected_keys | mutation_keys:
        raise StwoMedianTimingGateError("payload field drift")
    for key, expected in (
        ("schema", SCHEMA),
        ("source_cli_schema", CLI_SCHEMA),
        ("decision", DECISION),
        ("route_family", ROUTE_FAMILY),
        ("timing_policy", TIMING_POLICY),
        ("timing_scope", TIMING_SCOPE),
        ("claim_boundary", CLAIM_BOUNDARY),
        ("measurement_status", MEASUREMENT_STATUS),
    ):
        if payload[key] != expected:
            raise StwoMedianTimingGateError(f"{key} drift")
    if require_exact_int(payload["runs_per_envelope"], "runs_per_envelope") != RUNS_PER_ENVELOPE:
        raise StwoMedianTimingGateError("run count drift")
    if payload["rows"] != cli_summary["rows"]:
        raise StwoMedianTimingGateError("payload rows drift from CLI summary")
    if payload["profile_summaries"] != cli_summary["profile_summaries"]:
        raise StwoMedianTimingGateError("payload profile summaries drift from CLI summary")
    validate_aggregate(payload["aggregate"], payload["rows"], payload["profile_summaries"])
    if tuple(payload["non_claims"]) != NON_CLAIMS:
        raise StwoMedianTimingGateError("non-claims drift")
    if tuple(payload["validation_commands"]) != VALIDATION_COMMANDS:
        raise StwoMedianTimingGateError("validation command drift")
    if payload["payload_commitment"] != payload_commitment(payload):
        raise StwoMedianTimingGateError("payload commitment drift")
    if not allow_missing_mutation_summary or "mutation_cases" in payload:
        validate_mutation_summary(payload)


def validate_aggregate(aggregate: Any, rows: list[dict[str, Any]], profile_summaries: list[dict[str, Any]]) -> None:
    if not isinstance(aggregate, dict):
        raise StwoMedianTimingGateError("aggregate must be an object")
    expected = {
        "profiles_checked": len(profile_summaries),
        "route_rows_checked": len(rows),
        "verifier_runs_captured": len(rows) * RUNS_PER_ENVELOPE,
        "max_fused_verify_median_us": max(item["fused_verify_median_us"] for item in profile_summaries),
        "min_fused_verify_median_us": min(item["fused_verify_median_us"] for item in profile_summaries),
        "max_source_plus_sidecar_verify_median_us": max(
            item["source_plus_sidecar_verify_median_us"] for item in profile_summaries
        ),
        "min_source_plus_sidecar_verify_median_us": min(
            item["source_plus_sidecar_verify_median_us"] for item in profile_summaries
        ),
    }
    if aggregate != expected:
        raise StwoMedianTimingGateError("aggregate drift")


def validate_mutation_summary(payload: dict[str, Any]) -> None:
    cases = payload.get("mutation_cases")
    if not isinstance(cases, list) or [case.get("name") for case in cases] != list(MUTATION_NAMES):
        raise StwoMedianTimingGateError("mutation case drift")
    checked = require_exact_int(payload.get("mutations_checked"), "mutations_checked")
    rejected = require_exact_int(payload.get("mutations_rejected"), "mutations_rejected")
    if checked != len(MUTATION_NAMES) or rejected != len(MUTATION_NAMES):
        raise StwoMedianTimingGateError("mutation rejection drift")
    if payload.get("all_mutations_rejected") is not True:
        raise StwoMedianTimingGateError("mutation summary drift")
    for case in cases:
        if set(case) != {"name", "rejected"} or case["rejected"] is not True:
            raise StwoMedianTimingGateError("mutation result drift")


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        mutated.pop(key, None)
    if name == "decision_relabeling":
        mutated["decision"] = "GO_PUBLIC_BENCHMARK"
    elif name == "timing_policy_public_benchmark_overclaim":
        mutated["timing_policy"] = "public_benchmark"
    elif name == "claim_boundary_prover_timing_overclaim":
        mutated["claim_boundary"] = "PROVER_AND_VERIFIER_TIMING_FOR_FULL_SOFTMAX"
    elif name == "run_count_metric_smuggling":
        mutated["runs_per_envelope"] = 7
    elif name == "route_row_order_drift":
        mutated["rows"] = [mutated["rows"][1], mutated["rows"][0], *mutated["rows"][2:]]
    elif name == "route_row_role_relabeling":
        mutated["rows"][0]["role"] = "fused"
    elif name == "route_row_median_metric_smuggling":
        mutated["rows"][0]["verify_median_us"] += 1
    elif name == "route_row_runs_metric_smuggling":
        mutated["rows"][0]["verify_runs_us"][0] += 1
    elif name == "profile_source_plus_sidecar_metric_smuggling":
        mutated["profile_summaries"][0]["source_plus_sidecar_verify_median_us"] += 1
    elif name == "profile_ratio_metric_smuggling":
        mutated["profile_summaries"][0]["fused_to_source_plus_sidecar_verify_median_ratio"] += 0.1
    elif name == "non_claim_removed":
        mutated["non_claims"].pop()
    elif name == "validation_command_removed":
        mutated["validation_commands"].pop()
    elif name == "unknown_field_injection":
        mutated["unexpected"] = "claim smuggling"
    else:
        raise StwoMedianTimingGateError(f"unknown mutation: {name}")
    mutated["payload_commitment"] = payload_commitment(mutated)
    return mutated


def evaluate_mutations(payload: dict[str, Any], cli_summary: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for name in MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, cli_summary, allow_missing_mutation_summary=True)
        except StwoMedianTimingGateError:
            results.append({"name": name, "rejected": True})
        else:
            results.append({"name": name, "rejected": False})
    return results


def to_tsv(payload: dict[str, Any]) -> str:
    summaries = {summary["profile_id"]: summary for summary in payload["profile_summaries"]}
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in payload["rows"]:
        summary = summaries[row["profile_id"]]
        writer.writerow(
            {
                "profile_id": row["profile_id"],
                "axis_role": row["axis_role"],
                "role": row["role"],
                "key_width": row["key_width"],
                "value_width": row["value_width"],
                "head_count": row["head_count"],
                "steps_per_head": row["steps_per_head"],
                "proof_size_bytes": row["proof_size_bytes"],
                "envelope_size_bytes": row["envelope_size_bytes"],
                "verify_median_us": row["verify_median_us"],
                "verify_min_us": row["verify_min_us"],
                "verify_max_us": row["verify_max_us"],
                "verify_runs_us": ",".join(str(value) for value in row["verify_runs_us"]),
                "source_plus_sidecar_verify_median_us": summary["source_plus_sidecar_verify_median_us"],
                "fused_verify_median_us": summary["fused_verify_median_us"],
                "fused_to_source_plus_sidecar_verify_median_ratio": summary[
                    "fused_to_source_plus_sidecar_verify_median_ratio"
                ],
                "timing_status": summary["timing_status"],
            }
        )
    return buffer.getvalue()


def validate_output_path(raw_path: pathlib.Path) -> pathlib.Path:
    if raw_path.exists() and raw_path.is_symlink():
        raise StwoMedianTimingGateError(f"output path must not be a symlink: {raw_path}")
    path = raw_path.resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    if not path.parent.exists():
        raise StwoMedianTimingGateError(f"output parent does not exist: {path.parent}")
    if evidence_root not in (path, *path.parents):
        raise StwoMedianTimingGateError(f"output path escapes evidence dir: {path}")
    return path


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    path = validate_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
    tmp_path.replace(path)


def write_json(payload: dict[str, Any], cli_summary: dict[str, Any], path: pathlib.Path) -> None:
    validate_payload(payload, cli_summary)
    write_text_atomic(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_tsv(payload: dict[str, Any], cli_summary: dict[str, Any], path: pathlib.Path) -> None:
    validate_payload(payload, cli_summary)
    write_text_atomic(path, to_tsv(payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    cli_summary = run_timing_cli()
    payload = build_payload(cli_summary)
    if args.write_json:
        write_json(payload, cli_summary, args.write_json)
    if args.write_tsv:
        write_tsv(payload, cli_summary, args.write_tsv)
    if not args.write_json and not args.write_tsv:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
