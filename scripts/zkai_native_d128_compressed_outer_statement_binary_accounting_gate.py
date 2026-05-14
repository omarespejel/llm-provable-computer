#!/usr/bin/env python3
"""Local binary/typed accounting gate for the compressed d128 outer proof.

This gate gives the compressed d128 native Stwo outer-statement proof a
repo-owned typed accounting view.  It intentionally does not claim upstream
Stwo proof serialization or a matched NANOZK proof-size win.
"""

from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import math
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_stwo_binary_typed_proof_accounting_gate as accounting_base

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = (
    EVIDENCE_DIR / "zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json"
)
TSV_OUT = EVIDENCE_DIR / "zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.tsv"

SCHEMA = "zkai-native-d128-compressed-outer-statement-binary-typed-accounting-gate-v1"
CLI_SCHEMA = accounting_base.CLI_SCHEMA
ACCOUNTING_DOMAIN = accounting_base.ACCOUNTING_DOMAIN
ACCOUNTING_FORMAT_VERSION = accounting_base.ACCOUNTING_FORMAT_VERSION
UPSTREAM_SERIALIZATION_STATUS = accounting_base.UPSTREAM_SERIALIZATION_STATUS
PROOF_PAYLOAD_KIND = accounting_base.PROOF_PAYLOAD_KIND
EXPECTED_SIZE_CONSTANTS = accounting_base.EXPECTED_SIZE_CONSTANTS
EXPECTED_SAFETY = accounting_base.EXPECTED_SAFETY
EXPECTED_RECORD_PATHS = accounting_base.EXPECTED_RECORD_PATHS
NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900

DECISION = "GO_LOCAL_BINARY_TYPED_ACCOUNTING_FOR_COMPRESSED_D128_OUTER_STATEMENT_PROOF"
ROUTE_ID = "native_stwo_d128_compressed_outer_statement_binary_typed_accounting"
CLAIM_BOUNDARY = (
    "LOCAL_BINARY_TYPED_ACCOUNTING_FOR_COMPRESSED_D128_NATIVE_STWO_OUTER_STATEMENT_PROOF_"
    "NOT_UPSTREAM_STWO_SERIALIZATION_NOT_NATIVE_VERIFIER_EXECUTION_NOT_MATCHED_NANOZK_WIN"
)
TIMING_POLICY = "proof_accounting_only_no_new_timing"
ACCOUNTING_STATUS = "GO_REPO_OWNED_TYPED_FIELD_ACCOUNTING_FOR_COMPRESSED_D128_PROOF"
BINARY_SERIALIZATION_STATUS = "NO_GO_NOT_UPSTREAM_STWO_PROOF_SERIALIZATION"
COMPARISON_STATUS = "INTERESTING_RANGE_SIGNAL_ONLY_NOT_MATCHED_NANOZK_BENCHMARK"
FIRST_BLOCKER = (
    "The typed accounting is compact, but the object is still a compressed outer statement proof over "
    "host-verified d128 slices, not a native d128 transformer-block proof executing inner verifier checks."
)
EXPECTED_ROLE = {
    "role": "compressed_outer_statement",
    "path": "zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "proof_backend_version": "stwo-d128-two-slice-outer-statement-air-proof-v2-compressed-digest",
    "statement_version": "zkai-d128-two-slice-outer-statement-v1",
    "verifier_domain": None,
    "proof_schema_version": None,
    "target_id": None,
}
NON_CLAIMS = (
    "not upstream Stwo proof serialization",
    "not binary PCS/FRI wire-format accounting",
    "not native verifier execution of the selected inner Stwo proofs",
    "not recursion or proof-carrying data",
    "not a native d128 transformer-block proof",
    "not a matched NANOZK proof-size win",
    "not a public benchmark",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
)
VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "python3 scripts/zkai_native_d128_compressed_outer_statement_binary_accounting_gate.py --write-json docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_d128_compressed_outer_statement_binary_accounting_gate.py scripts/tests/test_zkai_native_d128_compressed_outer_statement_binary_accounting_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_d128_compressed_outer_statement_binary_accounting_gate",
    "cargo +nightly-2025-07-14 fmt --check",
    "git diff --check",
    "just gate-fast",
)
TSV_COLUMNS = (
    "role",
    "proof_backend_version",
    "proof_json_size_bytes",
    "local_typed_bytes",
    "json_minus_local_typed_bytes",
    "json_over_local_typed_ratio",
    "typed_ratio_vs_nanozk_paper_row",
    "json_ratio_vs_nanozk_paper_row",
    "record_stream_sha256",
    "proof_sha256",
)
BINARY_ACCOUNTING_TIMEOUT_SECONDS = 900
MUTATION_NAMES = (
    "schema_relabeling",
    "decision_overclaim",
    "claim_boundary_overclaim",
    "comparison_status_overclaim",
    "upstream_serialization_overclaim",
    "first_blocker_removed",
    "non_claim_removed",
    "role_relabeling",
    "proof_backend_version_relabeling",
    "statement_version_relabeling",
    "local_typed_metric_smuggling",
    "json_metric_smuggling",
    "record_total_metric_smuggling",
    "record_stream_commitment_relabeling",
    "proof_sha256_relabeling",
    "nanozk_baseline_smuggling",
    "aggregate_metric_smuggling",
    "cli_summary_commitment_relabeling",
    "payload_commitment_relabeling",
    "unknown_field_injection",
)

BinaryTypedProofAccountingGateError = accounting_base.BinaryTypedProofAccountingGateError


def output_tail(value: str | None, limit: int = 1600) -> str:
    return accounting_base.output_tail(value, limit)


def require_exact_int(value: Any, label: str) -> int:
    return accounting_base.require_exact_int(value, label)


def require_number(value: Any, label: str) -> float:
    return accounting_base.require_number(value, label)


def require_sha256_hex(value: Any, label: str) -> str:
    return accounting_base.require_sha256_hex(value, label)


def sha256_json(value: Any) -> str:
    return accounting_base.sha256_json(value)


def blake2b_commitment(value: Any, domain: str) -> str:
    return accounting_base.blake2b_commitment(value, domain)


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise BinaryTypedProofAccountingGateError("ratio denominator must be positive")
    return math.floor((numerator / denominator) * 1_000_000 + 0.5) / 1_000_000


def expected_envelope_paths() -> list[pathlib.Path]:
    return [EVIDENCE_DIR / EXPECTED_ROLE["path"]]


def run_binary_accounting_cli() -> dict[str, Any]:
    command = [
        "cargo",
        "+nightly-2025-07-14",
        "run",
        "--locked",
        "--features",
        "stwo-backend",
        "--bin",
        "zkai_stwo_proof_binary_accounting",
        "--",
        "--evidence-dir",
        str(EVIDENCE_DIR),
        *[str(path) for path in expected_envelope_paths()],
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=BINARY_ACCOUNTING_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as err:
        stderr = output_tail(err.stderr if isinstance(err.stderr, str) else None)
        stdout = output_tail(err.stdout if isinstance(err.stdout, str) else None)
        detail = stderr or stdout or "<no output>"
        raise BinaryTypedProofAccountingGateError(
            "binary accounting CLI timed out after "
            f"{BINARY_ACCOUNTING_TIMEOUT_SECONDS}s: {' '.join(command)}: {detail}"
        ) from err
    except OSError as err:
        raise BinaryTypedProofAccountingGateError(f"failed to run binary accounting CLI: {err}") from err
    if completed.returncode != 0:
        stderr = output_tail(completed.stderr)
        stdout = output_tail(completed.stdout)
        detail = stderr or stdout or "<no output>"
        raise BinaryTypedProofAccountingGateError(
            f"binary accounting CLI failed with exit {completed.returncode}: {detail}"
        )
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise BinaryTypedProofAccountingGateError(f"binary accounting CLI emitted invalid JSON: {err}") from err
    validate_cli_summary(summary)
    return summary


def validate_cli_summary(summary: Any) -> None:
    if not isinstance(summary, dict):
        raise BinaryTypedProofAccountingGateError("CLI summary must be an object")
    expected_keys = {
        "schema",
        "accounting_domain",
        "accounting_format_version",
        "accounting_source",
        "upstream_stwo_serialization_status",
        "proof_payload_kind",
        "safety",
        "size_constants",
        "rows",
    }
    if set(summary) != expected_keys:
        raise BinaryTypedProofAccountingGateError("CLI summary field drift")
    if summary["schema"] != CLI_SCHEMA:
        raise BinaryTypedProofAccountingGateError("CLI schema drift")
    if summary["accounting_domain"] != ACCOUNTING_DOMAIN:
        raise BinaryTypedProofAccountingGateError("CLI accounting domain drift")
    if summary["accounting_format_version"] != ACCOUNTING_FORMAT_VERSION:
        raise BinaryTypedProofAccountingGateError("CLI accounting format version drift")
    if summary["upstream_stwo_serialization_status"] != UPSTREAM_SERIALIZATION_STATUS:
        raise BinaryTypedProofAccountingGateError("CLI upstream serialization status drift")
    if summary["proof_payload_kind"] != PROOF_PAYLOAD_KIND:
        raise BinaryTypedProofAccountingGateError("CLI proof payload kind drift")
    accounting_base.validate_safety(summary["safety"])
    accounting_base.validate_size_constants(summary["size_constants"])
    rows = summary.get("rows")
    if not isinstance(rows, list) or len(rows) != 1:
        raise BinaryTypedProofAccountingGateError("CLI row count drift")
    validate_cli_row(rows[0], EXPECTED_ROLE)


def validate_cli_row(row: Any, expected: dict[str, Any]) -> None:
    if not isinstance(row, dict):
        raise BinaryTypedProofAccountingGateError("CLI row must be an object")
    expected_keys = {
        "path",
        "evidence_relative_path",
        "envelope_sha256",
        "proof_sha256",
        "proof_json_size_bytes",
        "envelope_metadata",
        "local_binary_accounting",
    }
    if set(row) != expected_keys:
        raise BinaryTypedProofAccountingGateError("CLI row field drift")
    if row["evidence_relative_path"] != expected["path"]:
        raise BinaryTypedProofAccountingGateError("evidence path drift")
    require_sha256_hex(row["envelope_sha256"], "envelope_sha256")
    require_sha256_hex(row["proof_sha256"], "proof_sha256")
    metadata = row["envelope_metadata"]
    if not isinstance(metadata, dict) or set(metadata) != {
        "proof_backend",
        "proof_backend_version",
        "statement_version",
        "verifier_domain",
        "proof_schema_version",
        "target_id",
    }:
        raise BinaryTypedProofAccountingGateError("metadata field drift")
    if metadata["proof_backend"] != "stwo":
        raise BinaryTypedProofAccountingGateError("proof backend drift")
    for key in ("proof_backend_version", "statement_version", "verifier_domain", "proof_schema_version", "target_id"):
        if metadata[key] != expected[key]:
            raise BinaryTypedProofAccountingGateError(f"{key} drift")
    proof_json_size = require_exact_int(row["proof_json_size_bytes"], "proof_json_size_bytes")
    accounting_base.validate_local_accounting(row["local_binary_accounting"], expected["role"], proof_json_size)
    if (
        row["local_binary_accounting"]["json_minus_local_typed_bytes"]
        != proof_json_size - row["local_binary_accounting"]["typed_size_estimate_bytes"]
    ):
        raise BinaryTypedProofAccountingGateError("JSON/local typed delta drift")


def build_payload(cli_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = cli_summary if cli_summary is not None else run_binary_accounting_cli()
    validate_cli_summary(summary)
    cli_row = summary["rows"][0]
    row = {
        "role": EXPECTED_ROLE["role"],
        "evidence_relative_path": cli_row["evidence_relative_path"],
        "envelope_metadata": cli_row["envelope_metadata"],
        "envelope_sha256": cli_row["envelope_sha256"],
        "proof_sha256": cli_row["proof_sha256"],
        "proof_json_size_bytes": cli_row["proof_json_size_bytes"],
        "local_binary_accounting": cli_row["local_binary_accounting"],
    }
    aggregate = build_aggregate(row)
    base = {
        "schema": SCHEMA,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "timing_policy": TIMING_POLICY,
        "accounting_status": ACCOUNTING_STATUS,
        "binary_serialization_status": BINARY_SERIALIZATION_STATUS,
        "comparison_status": COMPARISON_STATUS,
        "first_blocker": FIRST_BLOCKER,
        "nanozk_paper_reported_d128_block_proof_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        "non_claims": list(NON_CLAIMS),
        "cli_summary_commitment": "sha256:" + sha256_json(summary),
        "cli_schema": summary["schema"],
        "cli_accounting_domain": summary["accounting_domain"],
        "cli_accounting_format_version": summary["accounting_format_version"],
        "cli_upstream_stwo_serialization_status": summary["upstream_stwo_serialization_status"],
        "proof_payload_kind": summary["proof_payload_kind"],
        "size_constants": summary["size_constants"],
        "profile_row": row,
        "aggregate": aggregate,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    mutation_cases = mutation_cases_for(base, summary)
    payload = {
        **base,
        "mutation_cases": mutation_cases,
        "mutations_checked": len(mutation_cases),
        "mutations_rejected": sum(1 for case in mutation_cases if case["rejected"]),
        "all_mutations_rejected": all(case["rejected"] for case in mutation_cases),
    }
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload, summary)
    return payload


def build_aggregate(row: dict[str, Any]) -> dict[str, Any]:
    proof_json_size = row["proof_json_size_bytes"]
    typed_bytes = row["local_binary_accounting"]["typed_size_estimate_bytes"]
    return {
        "profiles_checked": 1,
        "role_checked": row["role"],
        "proof_json_size_bytes": proof_json_size,
        "local_typed_bytes": typed_bytes,
        "json_minus_local_typed_bytes": proof_json_size - typed_bytes,
        "json_over_local_typed_ratio": rounded_ratio(proof_json_size, typed_bytes),
        "json_ratio_vs_nanozk_paper_row": rounded_ratio(
            proof_json_size,
            NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        ),
        "typed_ratio_vs_nanozk_paper_row": rounded_ratio(
            typed_bytes,
            NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        ),
        "typed_saves_vs_nanozk_paper_row_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES - typed_bytes,
        "proof_json_saves_vs_nanozk_paper_row_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES
        - proof_json_size,
        "record_stream_sha256": row["local_binary_accounting"]["record_stream_sha256"],
        "proof_sha256": row["proof_sha256"],
        "profile_commitment": blake2b_commitment(
            row,
            "zkai:stwo:d128:compressed-outer-statement:binary-typed-accounting:profile:v1",
        ),
    }


def validate_payload(
    payload: Any,
    cli_summary: dict[str, Any],
    *,
    allow_missing_mutation_summary: bool = False,
) -> None:
    validate_cli_summary(cli_summary)
    if not isinstance(payload, dict):
        raise BinaryTypedProofAccountingGateError("payload must be object")
    expected_keys = {
        "schema",
        "decision",
        "route_id",
        "claim_boundary",
        "timing_policy",
        "accounting_status",
        "binary_serialization_status",
        "comparison_status",
        "first_blocker",
        "nanozk_paper_reported_d128_block_proof_bytes",
        "non_claims",
        "cli_summary_commitment",
        "cli_schema",
        "cli_accounting_domain",
        "cli_accounting_format_version",
        "cli_upstream_stwo_serialization_status",
        "proof_payload_kind",
        "size_constants",
        "profile_row",
        "aggregate",
        "validation_commands",
        "payload_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if allow_missing_mutation_summary:
        allowed_keys = expected_keys | mutation_keys
        if not set(payload).issubset(allowed_keys) or not expected_keys.issubset(payload):
            raise BinaryTypedProofAccountingGateError("payload field drift")
    elif set(payload) != expected_keys | mutation_keys:
        raise BinaryTypedProofAccountingGateError("payload field drift")
    expected_values = {
        "schema": SCHEMA,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "timing_policy": TIMING_POLICY,
        "accounting_status": ACCOUNTING_STATUS,
        "binary_serialization_status": BINARY_SERIALIZATION_STATUS,
        "comparison_status": COMPARISON_STATUS,
        "first_blocker": FIRST_BLOCKER,
        "nanozk_paper_reported_d128_block_proof_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        "cli_schema": CLI_SCHEMA,
        "cli_accounting_domain": ACCOUNTING_DOMAIN,
        "cli_accounting_format_version": ACCOUNTING_FORMAT_VERSION,
        "cli_upstream_stwo_serialization_status": UPSTREAM_SERIALIZATION_STATUS,
        "proof_payload_kind": PROOF_PAYLOAD_KIND,
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            raise BinaryTypedProofAccountingGateError(f"{key} drift")
    if payload["non_claims"] != list(NON_CLAIMS):
        raise BinaryTypedProofAccountingGateError("non_claims drift")
    if payload["validation_commands"] != list(VALIDATION_COMMANDS):
        raise BinaryTypedProofAccountingGateError("validation_commands drift")
    if payload["size_constants"] != cli_summary["size_constants"]:
        raise BinaryTypedProofAccountingGateError("size constants drift")
    if payload["cli_summary_commitment"] != "sha256:" + sha256_json(cli_summary):
        raise BinaryTypedProofAccountingGateError("CLI summary commitment drift")
    row = payload["profile_row"]
    validate_profile_row(row, cli_summary["rows"][0])
    if payload["aggregate"] != build_aggregate(row):
        raise BinaryTypedProofAccountingGateError("aggregate drift")
    if payload["payload_commitment"] != payload_commitment(payload):
        raise BinaryTypedProofAccountingGateError("payload commitment drift")
    if not allow_missing_mutation_summary or "mutation_cases" in payload:
        validate_mutation_summary(payload)


def validate_profile_row(profile_row: Any, cli_row: dict[str, Any]) -> None:
    if not isinstance(profile_row, dict) or set(profile_row) != {
        "role",
        "evidence_relative_path",
        "envelope_metadata",
        "envelope_sha256",
        "proof_sha256",
        "proof_json_size_bytes",
        "local_binary_accounting",
    }:
        raise BinaryTypedProofAccountingGateError("profile row field drift")
    if profile_row["role"] != EXPECTED_ROLE["role"]:
        raise BinaryTypedProofAccountingGateError("role drift")
    for key in (
        "evidence_relative_path",
        "envelope_metadata",
        "envelope_sha256",
        "proof_sha256",
        "proof_json_size_bytes",
        "local_binary_accounting",
    ):
        if profile_row[key] != cli_row[key]:
            raise BinaryTypedProofAccountingGateError(f"{key} drift")
    validate_cli_row(cli_row, EXPECTED_ROLE)


def validate_mutation_summary(payload: dict[str, Any]) -> None:
    mutation_cases = payload.get("mutation_cases")
    if not isinstance(mutation_cases, list) or len(mutation_cases) != len(MUTATION_NAMES):
        raise BinaryTypedProofAccountingGateError("mutation case count drift")
    names = [case.get("name") if isinstance(case, dict) else None for case in mutation_cases]
    if names != list(MUTATION_NAMES):
        raise BinaryTypedProofAccountingGateError("mutation case order drift")
    rejected = 0
    for case in mutation_cases:
        if not isinstance(case, dict) or set(case) != {"name", "rejected", "error"}:
            raise BinaryTypedProofAccountingGateError("mutation case field drift")
        if case["rejected"] is not True or not isinstance(case["error"], str) or not case["error"]:
            raise BinaryTypedProofAccountingGateError("mutation rejection drift")
        rejected += 1
    if payload.get("mutations_checked") != len(MUTATION_NAMES):
        raise BinaryTypedProofAccountingGateError("mutations_checked drift")
    if payload.get("mutations_rejected") != rejected:
        raise BinaryTypedProofAccountingGateError("mutations_rejected drift")
    if payload.get("all_mutations_rejected") is not True:
        raise BinaryTypedProofAccountingGateError("all_mutations_rejected drift")


def payload_commitment(payload: dict[str, Any]) -> str:
    value = copy.deepcopy(payload)
    value.pop("payload_commitment", None)
    return blake2b_commitment(
        value,
        "zkai:stwo:d128:compressed-outer-statement:binary-typed-accounting:payload:v1",
    )


def mutation_cases_for(base_payload: dict[str, Any], cli_summary: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name in MUTATION_NAMES:
        mutated = mutate_payload(base_payload, name)
        try:
            validate_payload(mutated, cli_summary, allow_missing_mutation_summary=True)
        except BinaryTypedProofAccountingGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": ""})
    return cases


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if name == "schema_relabeling":
        mutated["schema"] = "zkai-native-d128-compressed-outer-statement-binary-typed-accounting-gate-v2"
    elif name == "decision_overclaim":
        mutated["decision"] = "GO_MATCHED_NANOZK_PROOF_SIZE_WIN"
    elif name == "claim_boundary_overclaim":
        mutated["claim_boundary"] = "MATCHED_NANOZK_D128_TRANSFORMER_BLOCK_PROOF_SIZE_WIN"
    elif name == "comparison_status_overclaim":
        mutated["comparison_status"] = "GO_MATCHED_PUBLIC_BENCHMARK_WIN"
    elif name == "upstream_serialization_overclaim":
        mutated["binary_serialization_status"] = "GO_UPSTREAM_STWO_PROOF_SERIALIZATION"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "non_claim_removed":
        mutated["non_claims"] = list(mutated["non_claims"][:-1])
    elif name == "role_relabeling":
        mutated["profile_row"]["role"] = "native_d128_transformer_block"
    elif name == "proof_backend_version_relabeling":
        mutated["profile_row"]["envelope_metadata"]["proof_backend_version"] += "-mutated"
    elif name == "statement_version_relabeling":
        mutated["profile_row"]["envelope_metadata"]["statement_version"] += "-mutated"
    elif name == "local_typed_metric_smuggling":
        mutated["profile_row"]["local_binary_accounting"]["typed_size_estimate_bytes"] += 1
    elif name == "json_metric_smuggling":
        mutated["profile_row"]["proof_json_size_bytes"] += 1
    elif name == "record_total_metric_smuggling":
        mutated["profile_row"]["local_binary_accounting"]["records"][0]["total_bytes"] += 1
    elif name == "record_stream_commitment_relabeling":
        mutated["profile_row"]["local_binary_accounting"]["record_stream_sha256"] = "00" * 32
    elif name == "proof_sha256_relabeling":
        mutated["profile_row"]["proof_sha256"] = "11" * 32
    elif name == "nanozk_baseline_smuggling":
        mutated["nanozk_paper_reported_d128_block_proof_bytes"] = 3_000
    elif name == "aggregate_metric_smuggling":
        mutated["aggregate"]["typed_ratio_vs_nanozk_paper_row"] = 0.1
    elif name == "cli_summary_commitment_relabeling":
        mutated["cli_summary_commitment"] = "sha256:" + "22" * 32
    elif name == "payload_commitment_relabeling":
        mutated["payload_commitment"] = "blake2b-256:" + "33" * 32
    elif name == "unknown_field_injection":
        mutated["unexpected"] = True
    else:
        raise BinaryTypedProofAccountingGateError(f"unknown mutation {name}")
    if name != "payload_commitment_relabeling":
        mutated["payload_commitment"] = payload_commitment(mutated)
    return mutated


def to_tsv(payload: dict[str, Any]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    row = payload["profile_row"]
    accounting = row["local_binary_accounting"]
    aggregate = payload["aggregate"]
    writer.writerow(
        {
            "role": row["role"],
            "proof_backend_version": row["envelope_metadata"]["proof_backend_version"],
            "proof_json_size_bytes": row["proof_json_size_bytes"],
            "local_typed_bytes": accounting["typed_size_estimate_bytes"],
            "json_minus_local_typed_bytes": accounting["json_minus_local_typed_bytes"],
            "json_over_local_typed_ratio": accounting["json_over_local_typed_ratio"],
            "typed_ratio_vs_nanozk_paper_row": aggregate["typed_ratio_vs_nanozk_paper_row"],
            "json_ratio_vs_nanozk_paper_row": aggregate["json_ratio_vs_nanozk_paper_row"],
            "record_stream_sha256": accounting["record_stream_sha256"],
            "proof_sha256": row["proof_sha256"],
        }
    )
    return out.getvalue()


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    raw_path = path if path.is_absolute() else ROOT / path
    if raw_path.is_symlink():
        raise BinaryTypedProofAccountingGateError(f"output path must not be a symlink: {raw_path}")
    path = raw_path.resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    if not path.parent.exists():
        raise BinaryTypedProofAccountingGateError(f"output parent does not exist: {path.parent}")
    if path.exists() and path.is_dir():
        raise BinaryTypedProofAccountingGateError(f"output path must be a file: {path}")
    if evidence_root not in (path, *path.parents):
        raise BinaryTypedProofAccountingGateError(f"output path escapes evidence dir: {path}")
    return path


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    path = validate_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
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
    cli_summary = run_binary_accounting_cli()
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
