#!/usr/bin/env python3
"""Gate the d128 component-native two-slice reprove result.

This gate records the first component-native replacement for the selected
two-inner-proof verifier-execution target.  It is intentionally strict about
the comparison: the component-native proof is smaller than the 12,688 typed-byte
target, but it is still above NANOZK's paper-reported 6,900-byte d128 row and is
not a matched benchmark win.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
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
ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json"
PRIOR_BUDGET_PATH = (
    EVIDENCE_DIR / "zkai-native-d128-verifier-execution-compression-budget-2026-05.json"
)
JSON_OUT = EVIDENCE_DIR / "zkai-d128-component-native-two-slice-reprove-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-component-native-two-slice-reprove-gate-2026-05.tsv"

SCHEMA = "zkai-d128-component-native-two-slice-reprove-gate-v1"
DECISION = "GO_D128_COMPONENT_NATIVE_TWO_SLICE_REPROVE_PROOF_OBJECT"
RESULT = "GO_STRUCTURAL_SAVING_STILL_ABOVE_NANOZK_REPORTED_ROW"
ROUTE_ID = "native_stwo_d128_component_native_two_slice_reprove"
QUESTION = (
    "Can the selected d128 RMSNorm public-row and projection-bridge relations be reproven "
    "as native Stwo components with one shared proof object smaller than the selected "
    "inner-proof verifier-execution target?"
)
CLAIM_BOUNDARY = (
    "D128_COMPONENT_NATIVE_TWO_SLICE_REPROVE_REDUCES_THE_COMPARABLE_TYPED_TARGET_"
    "NOT_A_MATCHED_NANOZK_PROOF_SIZE_WIN"
)
FIRST_BLOCKER = (
    "component-native reproving closes most of the 12,688-to-6,900 typed-byte gap, "
    "but the checked proof is still 9,056 local typed bytes, 2,156 bytes above "
    "NANOZK's paper-reported d128 block-proof row"
)
NEXT_RESEARCH_STEP = (
    "attack the remaining 2,156 typed bytes by reducing query/decommitment footprint "
    "or by fusing additional model-faithful d128 block relations under the same "
    "native proof plumbing without dropping statement commitments"
)

CLI_SCHEMA = accounting_base.CLI_SCHEMA
ACCOUNTING_DOMAIN = accounting_base.ACCOUNTING_DOMAIN
ACCOUNTING_FORMAT_VERSION = accounting_base.ACCOUNTING_FORMAT_VERSION
UPSTREAM_SERIALIZATION_STATUS = accounting_base.UPSTREAM_SERIALIZATION_STATUS
PROOF_PAYLOAD_KIND = accounting_base.PROOF_PAYLOAD_KIND
EXPECTED_SIZE_CONSTANTS = accounting_base.EXPECTED_SIZE_CONSTANTS
EXPECTED_SAFETY = accounting_base.EXPECTED_SAFETY
EXPECTED_RECORD_PATHS = accounting_base.EXPECTED_RECORD_PATHS

NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900
PREVIOUS_TARGET_TYPED_BYTES = 12_688
PREVIOUS_TARGET_JSON_BYTES = 34_866
EXPECTED_PROOF_JSON_BYTES = 22_139
EXPECTED_LOCAL_TYPED_BYTES = 9_056
EXPECTED_ENVELOPE_BYTES = 241_499

EXPECTED_ROLE = {
    "role": "component_native_two_slice_reprove",
    "path": "zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "proof_backend_version": "stwo-d128-component-native-two-slice-reprove-v1",
    "statement_version": "zkai-d128-component-native-two-slice-reprove-statement-v1",
    "verifier_domain": None,
    "proof_schema_version": None,
    "target_id": None,
}

EXPECTED_PRIOR_BUDGET_DESCRIPTOR = {
    "source_id": "verifier_execution_compression_budget",
    "path": "docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.json",
    "file_sha256": "cbb8068b7339571b8f2141fea6390813566c48e919d13c86cfb1f605f0a661b5",
    "payload_sha256": "dbcdfbb65165b7bdc4bfb325bebd94dc3ec639414aeb6361f45ffd3e62b67709",
    "schema": "zkai-native-d128-verifier-execution-compression-budget-gate-v1",
    "decision": "GO_D128_VERIFIER_EXECUTION_COMPRESSION_BUDGET_PINNED",
    "payload_commitment": "sha256:21e5df1f455e22b2587be69093b3bfda3d4ff1235a5dd8524b96a4c2c713679b",
}

EXPECTED_AGGREGATE = {
    "profiles_checked": 1,
    "role_checked": "component_native_two_slice_reprove",
    "previous_verifier_target_typed_bytes": 12_688,
    "previous_verifier_target_json_bytes": 34_866,
    "proof_json_size_bytes": 22_139,
    "local_typed_bytes": 9_056,
    "envelope_json_size_bytes": 241_499,
    "json_minus_local_typed_bytes": 13_083,
    "json_over_local_typed_ratio": 2.444678,
    "typed_saving_vs_previous_target_bytes": 3_632,
    "json_saving_vs_previous_target_bytes": 12_727,
    "typed_saving_ratio_vs_previous_target": 0.286255,
    "json_saving_ratio_vs_previous_target": 0.365026,
    "typed_ratio_vs_previous_target": 0.713745,
    "json_ratio_vs_previous_target": 0.634974,
    "typed_gap_closed_vs_prior_budget": 0.627505,
    "typed_remaining_gap_to_nanozk_paper_row_bytes": 2_156,
    "typed_remaining_reduction_ratio_to_equal_nanozk": 0.238074,
    "typed_ratio_vs_nanozk_paper_row": 1.312464,
    "json_ratio_vs_nanozk_paper_row": 3.208551,
    "comparison_status": "smaller_than_previous_typed_target_still_above_nanozk_paper_row",
}

NON_CLAIMS = (
    "not a NANOZK proof-size win",
    "not a matched NANOZK benchmark",
    "not locally reproduced NANOZK evidence",
    "not native verifier execution of the selected inner Stwo proofs",
    "not recursion or proof-carrying data",
    "not a native full d128 transformer-block proof",
    "not upstream Stwo proof serialization",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- build-input docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- prove docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- verify docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "python3 scripts/zkai_d128_component_native_two_slice_reprove_gate.py --write-json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-gate-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_d128_component_native_two_slice_reprove_gate.py scripts/tests/test_zkai_d128_component_native_two_slice_reprove_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_d128_component_native_two_slice_reprove_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_component_two_slice_reprove --lib",
    "cargo +nightly-2025-07-14 fmt --check",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "object_id",
    "proof_json_size_bytes",
    "local_typed_bytes",
    "typed_ratio_vs_previous_target",
    "typed_saving_ratio_vs_previous_target",
    "typed_gap_closed_vs_prior_budget",
    "typed_ratio_vs_nanozk_paper_row",
    "typed_remaining_gap_to_nanozk_paper_row_bytes",
    "comparison_status",
)

BINARY_ACCOUNTING_TIMEOUT_SECONDS = 900

MUTATION_NAMES = (
    "schema_relabeling",
    "decision_overclaim",
    "result_overclaim",
    "claim_boundary_overclaim",
    "prior_budget_source_hash_drift",
    "role_relabeling",
    "proof_backend_version_relabeling",
    "proof_json_metric_smuggling",
    "local_typed_metric_smuggling",
    "previous_target_metric_smuggling",
    "nanozk_baseline_smuggling",
    "gap_closed_metric_smuggling",
    "comparison_status_overclaim",
    "first_blocker_removed",
    "non_claim_removed",
    "record_stream_commitment_relabeling",
    "validation_command_drift",
    "payload_commitment_relabeling",
    "unknown_field_injection",
)


class ComponentNativeReproveGateError(ValueError):
    pass


def output_tail(value: str | None, limit: int = 1600) -> str:
    return accounting_base.output_tail(value, limit)


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ComponentNativeReproveGateError(f"{label} must be object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ComponentNativeReproveGateError(f"{label} must be list")
    return value


def require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ComponentNativeReproveGateError(f"{label} must be non-empty string")
    return value


def require_exact_int(value: Any, label: str) -> int:
    try:
        return accounting_base.require_exact_int(value, label)
    except accounting_base.BinaryTypedProofAccountingGateError as err:
        raise ComponentNativeReproveGateError(str(err)) from err


def require_sha256_hex(value: Any, label: str) -> str:
    try:
        return accounting_base.require_sha256_hex(value, label)
    except accounting_base.BinaryTypedProofAccountingGateError as err:
        raise ComponentNativeReproveGateError(str(err)) from err


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise ComponentNativeReproveGateError("ratio denominator must be positive")
    return math.floor((numerator / denominator) * 1_000_000 + 0.5) / 1_000_000


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise ComponentNativeReproveGateError(f"invalid JSON value: {err}") from err


def sha256_json(value: Any) -> str:
    return accounting_base.sha256_json(value)


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + sha256_json(material)


def blake2b_commitment(value: Any, domain: str) -> str:
    return accounting_base.blake2b_commitment(value, domain)


def pretty_json(value: dict[str, Any]) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise ComponentNativeReproveGateError(f"invalid JSON value: {err}") from err


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _reject_duplicate_json_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in items:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ComponentNativeReproveGateError(f"source evidence is not a regular file: {path}")
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise ComponentNativeReproveGateError(f"source evidence escapes repository: {path}") from err
    raw = resolved.read_bytes()
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise ComponentNativeReproveGateError(f"failed to parse JSON {path}: {err}") from err
    return require_dict(payload, str(path)), raw


def source_descriptor(path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    descriptor = {
        "source_id": "verifier_execution_compression_budget",
        "path": str(path.resolve().relative_to(ROOT.resolve())),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest(),
        "schema": payload.get("schema"),
        "decision": payload.get("decision"),
        "payload_commitment": payload.get("payload_commitment"),
    }
    if descriptor != EXPECTED_PRIOR_BUDGET_DESCRIPTOR:
        raise ComponentNativeReproveGateError("prior budget source descriptor drift")
    return descriptor


def load_prior_budget() -> tuple[dict[str, Any], dict[str, Any]]:
    budget, raw = load_json(PRIOR_BUDGET_PATH)
    descriptor = source_descriptor(PRIOR_BUDGET_PATH, budget, raw)
    compression_budget = require_dict(budget.get("compression_budget"), "prior compression budget")
    if compression_budget.get("current_verifier_target_typed_bytes") != PREVIOUS_TARGET_TYPED_BYTES:
        raise ComponentNativeReproveGateError("prior typed target drift")
    if compression_budget.get("current_verifier_target_json_bytes") != PREVIOUS_TARGET_JSON_BYTES:
        raise ComponentNativeReproveGateError("prior JSON target drift")
    if (
        compression_budget.get("nanozk_paper_reported_d128_block_proof_bytes")
        != NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES
    ):
        raise ComponentNativeReproveGateError("prior NANOZK baseline drift")
    return budget, descriptor


def expected_envelope_paths() -> list[pathlib.Path]:
    return [ENVELOPE_PATH]


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
        raise ComponentNativeReproveGateError(
            "binary accounting CLI timed out after "
            f"{BINARY_ACCOUNTING_TIMEOUT_SECONDS}s: {' '.join(command)}: {detail}"
        ) from err
    except OSError as err:
        raise ComponentNativeReproveGateError(f"failed to run binary accounting CLI: {err}") from err
    if completed.returncode != 0:
        stderr = output_tail(completed.stderr)
        stdout = output_tail(completed.stdout)
        detail = stderr or stdout or "<no output>"
        raise ComponentNativeReproveGateError(
            f"binary accounting CLI failed with exit {completed.returncode}: {detail}"
        )
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise ComponentNativeReproveGateError(f"binary accounting CLI emitted invalid JSON: {err}") from err
    validate_cli_summary(summary)
    return summary


def validate_cli_summary(summary: Any) -> None:
    if not isinstance(summary, dict):
        raise ComponentNativeReproveGateError("CLI summary must be object")
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
        raise ComponentNativeReproveGateError("CLI summary field drift")
    expected_values = {
        "schema": CLI_SCHEMA,
        "accounting_domain": ACCOUNTING_DOMAIN,
        "accounting_format_version": ACCOUNTING_FORMAT_VERSION,
        "upstream_stwo_serialization_status": UPSTREAM_SERIALIZATION_STATUS,
        "proof_payload_kind": PROOF_PAYLOAD_KIND,
    }
    for key, expected in expected_values.items():
        if summary[key] != expected:
            raise ComponentNativeReproveGateError(f"CLI {key} drift")
    try:
        accounting_base.validate_safety(summary["safety"])
        accounting_base.validate_size_constants(summary["size_constants"])
    except accounting_base.BinaryTypedProofAccountingGateError as err:
        raise ComponentNativeReproveGateError(str(err)) from err
    rows = summary.get("rows")
    if not isinstance(rows, list) or len(rows) != 1:
        raise ComponentNativeReproveGateError("CLI row count drift")
    validate_cli_row(rows[0])


def validate_cli_row(row: Any) -> None:
    if not isinstance(row, dict):
        raise ComponentNativeReproveGateError("CLI row must be object")
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
        raise ComponentNativeReproveGateError("CLI row field drift")
    if row["evidence_relative_path"] != EXPECTED_ROLE["path"]:
        raise ComponentNativeReproveGateError("CLI evidence path drift")
    metadata = require_dict(row["envelope_metadata"], "CLI envelope metadata")
    expected_metadata = {
        "proof_backend": "stwo",
        "proof_backend_version": EXPECTED_ROLE["proof_backend_version"],
        "statement_version": EXPECTED_ROLE["statement_version"],
        "verifier_domain": EXPECTED_ROLE["verifier_domain"],
        "proof_schema_version": EXPECTED_ROLE["proof_schema_version"],
        "target_id": EXPECTED_ROLE["target_id"],
    }
    if metadata != expected_metadata:
        raise ComponentNativeReproveGateError("CLI envelope metadata drift")
    if require_exact_int(row["proof_json_size_bytes"], "CLI proof_json_size_bytes") != EXPECTED_PROOF_JSON_BYTES:
        raise ComponentNativeReproveGateError("CLI proof_json_size_bytes drift")
    require_sha256_hex(row["envelope_sha256"], "CLI envelope_sha256")
    require_sha256_hex(row["proof_sha256"], "CLI proof_sha256")
    try:
        accounting_base.validate_local_accounting(
            row["local_binary_accounting"], EXPECTED_ROLE["role"], EXPECTED_PROOF_JSON_BYTES
        )
    except accounting_base.BinaryTypedProofAccountingGateError as err:
        raise ComponentNativeReproveGateError(str(err)) from err
    typed_bytes = row["local_binary_accounting"]["typed_size_estimate_bytes"]
    if typed_bytes != EXPECTED_LOCAL_TYPED_BYTES:
        raise ComponentNativeReproveGateError("CLI local typed bytes drift")


def build_payload(
    cli_summary: dict[str, Any] | None = None,
    prior_budget: dict[str, Any] | None = None,
    prior_descriptor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = cli_summary if cli_summary is not None else run_binary_accounting_cli()
    validate_cli_summary(summary)
    if prior_budget is None or prior_descriptor is None:
        prior_budget, prior_descriptor = load_prior_budget()
    else:
        validate_prior_budget_fixture(prior_budget, prior_descriptor)
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
    aggregate = build_aggregate(row, prior_budget)
    base = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
        "nanozk_paper_reported_d128_block_proof_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        "source_evidence": [prior_descriptor],
        "cli_summary_commitment": "sha256:" + sha256_json(summary),
        "cli_schema": summary["schema"],
        "cli_accounting_domain": summary["accounting_domain"],
        "cli_accounting_format_version": summary["accounting_format_version"],
        "cli_upstream_stwo_serialization_status": summary["upstream_stwo_serialization_status"],
        "proof_payload_kind": summary["proof_payload_kind"],
        "size_constants": summary["size_constants"],
        "profile_row": row,
        "aggregate": aggregate,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    mutation_cases = mutation_cases_for(base, summary, prior_budget, prior_descriptor)
    payload = {
        **base,
        "mutation_cases": mutation_cases,
        "mutations_checked": len(mutation_cases),
        "mutations_rejected": sum(1 for case in mutation_cases if case["rejected"]),
        "all_mutations_rejected": all(case["rejected"] for case in mutation_cases),
    }
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload, summary, prior_budget, prior_descriptor)
    return payload


def validate_prior_budget_fixture(prior_budget: dict[str, Any], prior_descriptor: dict[str, Any]) -> None:
    if prior_descriptor != EXPECTED_PRIOR_BUDGET_DESCRIPTOR:
        raise ComponentNativeReproveGateError("prior budget descriptor drift")
    compression_budget = require_dict(prior_budget.get("compression_budget"), "prior compression budget")
    if compression_budget.get("current_verifier_target_typed_bytes") != PREVIOUS_TARGET_TYPED_BYTES:
        raise ComponentNativeReproveGateError("prior typed target drift")
    if compression_budget.get("current_verifier_target_json_bytes") != PREVIOUS_TARGET_JSON_BYTES:
        raise ComponentNativeReproveGateError("prior JSON target drift")


def build_aggregate(row: dict[str, Any], prior_budget: dict[str, Any]) -> dict[str, Any]:
    compression_budget = require_dict(prior_budget.get("compression_budget"), "prior compression budget")
    previous_typed = require_exact_int(
        compression_budget.get("current_verifier_target_typed_bytes"), "prior typed target"
    )
    previous_json = require_exact_int(
        compression_budget.get("current_verifier_target_json_bytes"), "prior JSON target"
    )
    proof_json_size = require_exact_int(row["proof_json_size_bytes"], "proof_json_size_bytes")
    typed_bytes = require_exact_int(
        row["local_binary_accounting"]["typed_size_estimate_bytes"], "typed_size_estimate_bytes"
    )
    envelope_size = ENVELOPE_PATH.stat().st_size if ENVELOPE_PATH.exists() else EXPECTED_ENVELOPE_BYTES
    typed_saving = previous_typed - typed_bytes
    json_saving = previous_json - proof_json_size
    gap_before = previous_typed - NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES
    remaining_gap = typed_bytes - NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES
    aggregate = {
        "profiles_checked": 1,
        "role_checked": row["role"],
        "previous_verifier_target_typed_bytes": previous_typed,
        "previous_verifier_target_json_bytes": previous_json,
        "proof_json_size_bytes": proof_json_size,
        "local_typed_bytes": typed_bytes,
        "envelope_json_size_bytes": envelope_size,
        "json_minus_local_typed_bytes": proof_json_size - typed_bytes,
        "json_over_local_typed_ratio": rounded_ratio(proof_json_size, typed_bytes),
        "typed_saving_vs_previous_target_bytes": typed_saving,
        "json_saving_vs_previous_target_bytes": json_saving,
        "typed_saving_ratio_vs_previous_target": rounded_ratio(typed_saving, previous_typed),
        "json_saving_ratio_vs_previous_target": rounded_ratio(json_saving, previous_json),
        "typed_ratio_vs_previous_target": rounded_ratio(typed_bytes, previous_typed),
        "json_ratio_vs_previous_target": rounded_ratio(proof_json_size, previous_json),
        "typed_gap_closed_vs_prior_budget": rounded_ratio(typed_saving, gap_before),
        "typed_remaining_gap_to_nanozk_paper_row_bytes": remaining_gap,
        "typed_remaining_reduction_ratio_to_equal_nanozk": rounded_ratio(remaining_gap, typed_bytes),
        "typed_ratio_vs_nanozk_paper_row": rounded_ratio(
            typed_bytes, NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES
        ),
        "json_ratio_vs_nanozk_paper_row": rounded_ratio(
            proof_json_size, NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES
        ),
        "comparison_status": "smaller_than_previous_typed_target_still_above_nanozk_paper_row",
    }
    if aggregate != EXPECTED_AGGREGATE:
        raise ComponentNativeReproveGateError(f"aggregate drift: {aggregate}")
    return aggregate


def expected_values() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
        "nanozk_paper_reported_d128_block_proof_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        "cli_schema": CLI_SCHEMA,
        "cli_accounting_domain": ACCOUNTING_DOMAIN,
        "cli_accounting_format_version": ACCOUNTING_FORMAT_VERSION,
        "cli_upstream_stwo_serialization_status": UPSTREAM_SERIALIZATION_STATUS,
        "proof_payload_kind": PROOF_PAYLOAD_KIND,
    }


def validate_payload(
    payload: Any,
    cli_summary: dict[str, Any],
    prior_budget: dict[str, Any],
    prior_descriptor: dict[str, Any],
    *,
    allow_missing_mutation_summary: bool = False,
) -> None:
    validate_cli_summary(cli_summary)
    validate_prior_budget_fixture(prior_budget, prior_descriptor)
    if not isinstance(payload, dict):
        raise ComponentNativeReproveGateError("payload must be object")
    expected_keys = {
        "schema",
        "decision",
        "result",
        "route_id",
        "question",
        "claim_boundary",
        "first_blocker",
        "next_research_step",
        "nanozk_paper_reported_d128_block_proof_bytes",
        "source_evidence",
        "cli_summary_commitment",
        "cli_schema",
        "cli_accounting_domain",
        "cli_accounting_format_version",
        "cli_upstream_stwo_serialization_status",
        "proof_payload_kind",
        "size_constants",
        "profile_row",
        "aggregate",
        "non_claims",
        "validation_commands",
        "payload_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if allow_missing_mutation_summary:
        allowed_keys = expected_keys | mutation_keys
        if not set(payload).issubset(allowed_keys) or not expected_keys.issubset(payload):
            raise ComponentNativeReproveGateError("payload field drift")
        present_mutation_keys = mutation_keys & set(payload)
        if present_mutation_keys and present_mutation_keys != mutation_keys:
            raise ComponentNativeReproveGateError("payload field drift")
    elif set(payload) != expected_keys | mutation_keys:
        raise ComponentNativeReproveGateError("payload field drift")
    for key, expected in expected_values().items():
        if payload.get(key) != expected:
            raise ComponentNativeReproveGateError(f"{key} drift")
    if payload.get("source_evidence") != [EXPECTED_PRIOR_BUDGET_DESCRIPTOR]:
        raise ComponentNativeReproveGateError("source evidence drift")
    if payload.get("cli_summary_commitment") != "sha256:" + sha256_json(cli_summary):
        raise ComponentNativeReproveGateError("CLI summary commitment drift")
    if payload.get("size_constants") != EXPECTED_SIZE_CONSTANTS:
        raise ComponentNativeReproveGateError("size constants drift")
    row = require_dict(payload.get("profile_row"), "profile row")
    validate_profile_row(row, cli_summary)
    if payload.get("aggregate") != build_aggregate(row, prior_budget):
        raise ComponentNativeReproveGateError("aggregate drift")
    if payload.get("non_claims") != list(NON_CLAIMS):
        raise ComponentNativeReproveGateError("non-claims drift")
    if payload.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise ComponentNativeReproveGateError("validation commands drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise ComponentNativeReproveGateError("payload commitment drift")
    if not allow_missing_mutation_summary or (set(payload) & mutation_keys):
        validate_mutation_summary(payload)


def validate_profile_row(row: dict[str, Any], cli_summary: dict[str, Any]) -> None:
    expected_cli_row = cli_summary["rows"][0]
    expected_row = {
        "role": EXPECTED_ROLE["role"],
        "evidence_relative_path": expected_cli_row["evidence_relative_path"],
        "envelope_metadata": expected_cli_row["envelope_metadata"],
        "envelope_sha256": expected_cli_row["envelope_sha256"],
        "proof_sha256": expected_cli_row["proof_sha256"],
        "proof_json_size_bytes": expected_cli_row["proof_json_size_bytes"],
        "local_binary_accounting": expected_cli_row["local_binary_accounting"],
    }
    if row != expected_row:
        raise ComponentNativeReproveGateError("profile row drift")
    if row["role"] != EXPECTED_ROLE["role"]:
        raise ComponentNativeReproveGateError("profile role drift")
    try:
        accounting_base.validate_local_accounting(
            row["local_binary_accounting"], EXPECTED_ROLE["role"], EXPECTED_PROOF_JSON_BYTES
        )
    except accounting_base.BinaryTypedProofAccountingGateError as err:
        raise ComponentNativeReproveGateError(str(err)) from err


def validate_mutation_summary(payload: dict[str, Any]) -> None:
    cases = require_list(payload.get("mutation_cases"), "mutation cases")
    names = tuple(require_str(require_dict(case, "mutation case").get("name"), "mutation case name") for case in cases)
    if names != MUTATION_NAMES:
        raise ComponentNativeReproveGateError("mutation inventory drift")
    checked = require_exact_int(payload.get("mutations_checked"), "mutations_checked")
    rejected = require_exact_int(payload.get("mutations_rejected"), "mutations_rejected")
    if checked != len(MUTATION_NAMES) or rejected != len(MUTATION_NAMES):
        raise ComponentNativeReproveGateError("mutation count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise ComponentNativeReproveGateError("mutation rejection summary drift")
    for case in cases:
        case_dict = require_dict(case, "mutation case")
        if case_dict.get("rejected") is not True:
            raise ComponentNativeReproveGateError("mutation was not rejected")
        require_str(case_dict.get("error"), "mutation error")


def mutation_cases_for(
    base: dict[str, Any],
    cli_summary: dict[str, Any],
    prior_budget: dict[str, Any],
    prior_descriptor: dict[str, Any],
) -> list[dict[str, Any]]:
    cases = []
    for name in MUTATION_NAMES:
        mutated = mutate_payload(base, name)
        try:
            validate_payload(
                mutated,
                cli_summary,
                prior_budget,
                prior_descriptor,
                allow_missing_mutation_summary=True,
            )
        except ComponentNativeReproveGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": ""})
    return cases


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if name == "schema_relabeling":
        mutated["schema"] += "-mutated"
    elif name == "decision_overclaim":
        mutated["decision"] = "WIN_D128_COMPONENT_NATIVE_TWO_SLICE_REPROVE"
    elif name == "result_overclaim":
        mutated["result"] = "MATCHED_NANOZK_PROOF_SIZE_WIN"
    elif name == "claim_boundary_overclaim":
        mutated["claim_boundary"] = "D128_COMPONENT_NATIVE_TWO_SLICE_REPROVE_BEATS_NANOZK"
    elif name == "prior_budget_source_hash_drift":
        mutated["source_evidence"][0]["file_sha256"] = "0" * 64
    elif name == "role_relabeling":
        mutated["profile_row"]["role"] = "native_d128_full_block_proof"
    elif name == "proof_backend_version_relabeling":
        mutated["profile_row"]["envelope_metadata"]["proof_backend_version"] += "-mutated"
    elif name == "proof_json_metric_smuggling":
        mutated["profile_row"]["proof_json_size_bytes"] -= 1
    elif name == "local_typed_metric_smuggling":
        mutated["profile_row"]["local_binary_accounting"]["typed_size_estimate_bytes"] -= 1
    elif name == "previous_target_metric_smuggling":
        mutated["aggregate"]["previous_verifier_target_typed_bytes"] -= 1
    elif name == "nanozk_baseline_smuggling":
        mutated["nanozk_paper_reported_d128_block_proof_bytes"] = 5_000
    elif name == "gap_closed_metric_smuggling":
        mutated["aggregate"]["typed_gap_closed_vs_prior_budget"] = 1.0
    elif name == "comparison_status_overclaim":
        mutated["aggregate"]["comparison_status"] = "matched_nanozk_win"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif name == "record_stream_commitment_relabeling":
        mutated["profile_row"]["local_binary_accounting"]["record_stream_sha256"] = "1" * 64
    elif name == "validation_command_drift":
        mutated["validation_commands"] = mutated["validation_commands"][:-1]
    elif name == "payload_commitment_relabeling":
        mutated["payload_commitment"] = "sha256:" + ("0" * 64)
        return mutated
    elif name == "unknown_field_injection":
        mutated["unexpected"] = True
    else:
        raise AssertionError(f"unhandled mutation {name}")
    mutated["payload_commitment"] = payload_commitment(mutated)
    return mutated


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=TSV_COLUMNS, delimiter="\t", extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerow({"object_id": "component_native_two_slice_reprove", **payload["aggregate"]})
    return output.getvalue()


def reject_symlinked_path_components(path: pathlib.Path, label: str) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as err:
        raise ComponentNativeReproveGateError(f"{label} is not under repo root: {path}") from err
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ComponentNativeReproveGateError(f"{label} component must not be a symlink: {current}")


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    raw_path = path if path.is_absolute() else ROOT / path
    reject_symlinked_path_components(EVIDENCE_DIR, "evidence dir")
    reject_symlinked_path_components(raw_path, "output path")
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise ComponentNativeReproveGateError(f"output path must be under evidence dir: {raw_path}") from err
    if not resolved.parent.exists() or not resolved.parent.is_dir():
        raise ComponentNativeReproveGateError(f"output parent must be an existing directory: {resolved.parent}")
    if resolved.exists() and resolved.is_dir():
        raise ComponentNativeReproveGateError(f"output path must be a file: {resolved}")
    return resolved


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    path = validate_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp_path.replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise


def write_json(path: pathlib.Path, payload: dict[str, Any], cli_summary: dict[str, Any], prior_budget: dict[str, Any], prior_descriptor: dict[str, Any]) -> None:
    validate_payload(payload, cli_summary, prior_budget, prior_descriptor)
    write_text_atomic(path, pretty_json(payload) + "\n")


def write_tsv(path: pathlib.Path, payload: dict[str, Any], cli_summary: dict[str, Any], prior_budget: dict[str, Any], prior_descriptor: dict[str, Any]) -> None:
    validate_payload(payload, cli_summary, prior_budget, prior_descriptor)
    write_text_atomic(path, to_tsv(payload))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    cli_summary = run_binary_accounting_cli()
    prior_budget, prior_descriptor = load_prior_budget()
    payload = build_payload(cli_summary, prior_budget, prior_descriptor)
    if args.write_json:
        write_json(args.write_json, payload, cli_summary, prior_budget, prior_descriptor)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload, cli_summary, prior_budget, prior_descriptor)
    if not args.write_json and not args.write_tsv:
        print(pretty_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
