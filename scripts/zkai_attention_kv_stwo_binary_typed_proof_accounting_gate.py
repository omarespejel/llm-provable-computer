#!/usr/bin/env python3
"""Stable local binary/typed proof-accounting gate for the d32 Stwo envelopes.

This is a bounded first slice: it accounts for the existing d32 source,
LogUp-sidecar, and fused proof envelopes using the repo-owned Rust accounting
CLI.  The local binary format is an accounting record stream over typed Stwo
fields.  It is intentionally not an upstream Stwo proof serialization.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-binary-typed-proof-accounting-gate-v1"
CLI_SCHEMA = "zkai-stwo-local-binary-proof-accounting-cli-v1"
ACCOUNTING_DOMAIN = "zkai:stwo:local-binary-proof-accounting"
ACCOUNTING_FORMAT_VERSION = "v1"
UPSTREAM_SERIALIZATION_STATUS = "NOT_UPSTREAM_STWO_SERIALIZATION_LOCAL_ACCOUNTING_RECORD_STREAM_ONLY"
PROOF_PAYLOAD_KIND = "utf8_json_object_with_single_stark_proof_field"
DECISION = "GO_REPO_OWNED_LOCAL_BINARY_TYPED_ACCOUNTING_FOR_D32_MATCHED_ENVELOPES"
CLAIM_BOUNDARY = (
    "LOCAL_BINARY_TYPED_STWO_PROOF_ACCOUNTING_RECORD_STREAM_FOR_D32_SOURCE_SIDECAR_FUSED_ENVELOPES_"
    "NOT_UPSTREAM_STWO_SERIALIZATION_NOT_BINARY_PCS_FRI_WIRE_FORMAT_NOT_TIMING_NOT_PUBLIC_BENCHMARK"
)
TIMING_POLICY = "proof_accounting_only_no_new_timing"
ACCOUNTING_STATUS = "GO_CANONICAL_LOCAL_BINARY_TYPED_ACCOUNTING_RECORD_STREAM"
BINARY_SERIALIZATION_STATUS = "NO_GO_NOT_UPSTREAM_STWO_PROOF_SERIALIZATION"
ROUTE_ID = "local_stwo_attention_kv_d32_binary_typed_proof_accounting"
FIRST_BLOCKER = (
    "Upstream Stwo does not expose a stable proof wire serializer here; this gate records a repo-owned "
    "deterministic accounting record stream over typed proof fields instead."
)
NON_CLAIMS = (
    "not upstream Stwo proof serialization",
    "not binary PCS/FRI wire-format accounting",
    "not backend-internal source arithmetic versus lookup attribution",
    "not timing evidence",
    "not a public benchmark",
    "not exact real-valued Softmax",
    "not full inference",
    "not recursion or PCD",
)
VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence <envelope.json>...",
    "python3 scripts/zkai_attention_kv_stwo_binary_typed_proof_accounting_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_binary_typed_proof_accounting_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting",
    "git diff --check",
)
TSV_COLUMNS = (
    "role",
    "proof_backend_version",
    "proof_json_size_bytes",
    "local_typed_bytes",
    "json_minus_local_typed_bytes",
    "json_over_local_typed_ratio",
    "record_stream_sha256",
    "proof_sha256",
)
EXPECTED_ROLES = (
    {
        "role": "source_arithmetic",
        "path": "zkai-attention-kv-stwo-native-d32-bounded-softmax-table-proof-2026-05.envelope.json",
        "proof_backend_version": "stwo-attention-kv-d32-causal-mask-bounded-softmax-table-v1",
        "statement_version": "zkai-attention-kv-stwo-native-d32-bounded-softmax-table-statement-v1",
        "verifier_domain": None,
        "proof_schema_version": None,
        "target_id": None,
    },
    {
        "role": "logup_sidecar",
        "path": "zkai-attention-kv-stwo-native-d32-softmax-table-logup-sidecar-proof-2026-05.envelope.json",
        "proof_backend_version": "stwo-attention-kv-d32-softmax-table-logup-sidecar-proof-v1",
        "statement_version": "zkai-attention-kv-stwo-native-d32-softmax-table-logup-sidecar-statement-v1",
        "verifier_domain": "ptvm:zkai:attention-kv-stwo-native-d32-softmax-table-logup-sidecar:v1",
        "proof_schema_version": None,
        "target_id": "attention-kv-d32-causal-mask-bounded-softmax-table-logup-sidecar-v1",
    },
    {
        "role": "fused",
        "path": "zkai-attention-kv-stwo-native-d32-fused-softmax-table-proof-2026-05.envelope.json",
        "proof_backend_version": "stwo-attention-kv-d32-fused-bounded-softmax-table-logup-v1",
        "statement_version": "zkai-attention-kv-stwo-native-d32-fused-softmax-table-logup-statement-v1",
        "verifier_domain": "ptvm:zkai:attention-kv-stwo-native-d32-fused-bounded-softmax-table-logup:v1",
        "proof_schema_version": "stwo-attention-kv-d32-fused-bounded-softmax-table-logup-proof-v1",
        "target_id": "attention-kv-d32-causal-mask-fused-bounded-softmax-table-logup-v1",
    },
)
EXPECTED_RECORD_PATHS = (
    "pcs.commitments",
    "pcs.trace_decommitments.hash_witness",
    "pcs.sampled_values",
    "pcs.queried_values",
    "pcs.fri.first_layer.fri_witness",
    "pcs.fri.inner_layers.fri_witness",
    "pcs.fri.last_layer_poly",
    "pcs.fri.first_layer.commitment",
    "pcs.fri.inner_layers.commitments",
    "pcs.fri.first_layer.decommitment.hash_witness",
    "pcs.fri.inner_layers.decommitment.hash_witness",
    "pcs.proof_of_work",
    "pcs.config",
)
MUTATION_NAMES = (
    "schema_relabeling",
    "decision_overclaim",
    "claim_boundary_overclaim",
    "accounting_status_overclaim",
    "upstream_serialization_overclaim",
    "first_blocker_removed",
    "non_claim_removed",
    "role_order_drift",
    "role_relabeling",
    "proof_backend_version_relabeling",
    "verifier_domain_relabeling",
    "proof_schema_version_relabeling",
    "local_typed_metric_smuggling",
    "record_total_metric_smuggling",
    "record_stream_commitment_relabeling",
    "proof_sha256_relabeling",
    "aggregate_metric_smuggling",
    "cli_summary_commitment_relabeling",
    "payload_commitment_relabeling",
    "unknown_field_injection",
)


class BinaryTypedProofAccountingGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def require_exact_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BinaryTypedProofAccountingGateError(f"{label} must be an integer")
    return value


def require_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, float):
        raise BinaryTypedProofAccountingGateError(f"{label} must be a float")
    return value


def expected_envelope_paths() -> list[pathlib.Path]:
    return [EVIDENCE_DIR / role["path"] for role in EXPECTED_ROLES]


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
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)
    if completed.returncode != 0:
        raise BinaryTypedProofAccountingGateError(
            f"binary accounting CLI failed with exit {completed.returncode}: {completed.stderr.strip()}"
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
    rows = summary.get("rows")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_ROLES):
        raise BinaryTypedProofAccountingGateError("CLI row count drift")
    for row, expected in zip(rows, EXPECTED_ROLES, strict=True):
        validate_cli_row(row, expected)


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
        raise BinaryTypedProofAccountingGateError(f"{expected['role']} evidence path drift")
    metadata = row["envelope_metadata"]
    if not isinstance(metadata, dict) or set(metadata) != {
        "proof_backend",
        "proof_backend_version",
        "statement_version",
        "verifier_domain",
        "proof_schema_version",
        "target_id",
    }:
        raise BinaryTypedProofAccountingGateError(f"{expected['role']} metadata field drift")
    if metadata["proof_backend"] != "stwo":
        raise BinaryTypedProofAccountingGateError(f"{expected['role']} proof backend drift")
    for key in ("proof_backend_version", "statement_version", "verifier_domain", "proof_schema_version", "target_id"):
        if metadata[key] != expected[key]:
            raise BinaryTypedProofAccountingGateError(f"{expected['role']} {key} drift")
    accounting = row["local_binary_accounting"]
    validate_local_accounting(accounting, expected["role"])
    require_exact_int(row["proof_json_size_bytes"], f"{expected['role']} proof_json_size_bytes")
    if accounting["json_minus_local_typed_bytes"] != row["proof_json_size_bytes"] - accounting["typed_size_estimate_bytes"]:
        raise BinaryTypedProofAccountingGateError(f"{expected['role']} JSON/local typed delta drift")


def validate_local_accounting(accounting: Any, role: str) -> None:
    if not isinstance(accounting, dict):
        raise BinaryTypedProofAccountingGateError(f"{role} local accounting must be an object")
    expected_keys = {
        "format_domain",
        "format_version",
        "upstream_stwo_serialization_status",
        "records",
        "record_count",
        "component_sum_bytes",
        "typed_size_estimate_bytes",
        "grouped_reconstruction",
        "stwo_grouped_breakdown",
        "record_stream_bytes",
        "record_stream_sha256",
        "json_over_local_typed_ratio",
        "json_minus_local_typed_bytes",
    }
    if set(accounting) != expected_keys:
        raise BinaryTypedProofAccountingGateError(f"{role} local accounting field drift")
    if accounting["format_domain"] != ACCOUNTING_DOMAIN:
        raise BinaryTypedProofAccountingGateError(f"{role} accounting domain drift")
    if accounting["format_version"] != ACCOUNTING_FORMAT_VERSION:
        raise BinaryTypedProofAccountingGateError(f"{role} accounting format version drift")
    if accounting["upstream_stwo_serialization_status"] != UPSTREAM_SERIALIZATION_STATUS:
        raise BinaryTypedProofAccountingGateError(f"{role} upstream serialization status drift")
    records = accounting["records"]
    if not isinstance(records, list) or len(records) != len(EXPECTED_RECORD_PATHS):
        raise BinaryTypedProofAccountingGateError(f"{role} accounting record count drift")
    if accounting["record_count"] != len(records):
        raise BinaryTypedProofAccountingGateError(f"{role} record_count drift")
    total = 0
    for record, expected_path in zip(records, EXPECTED_RECORD_PATHS, strict=True):
        validate_record(record, expected_path, role)
        total += record["total_bytes"]
    if require_exact_int(accounting["component_sum_bytes"], f"{role} component_sum_bytes") != total:
        raise BinaryTypedProofAccountingGateError(f"{role} component sum drift")
    if accounting["typed_size_estimate_bytes"] != total:
        raise BinaryTypedProofAccountingGateError(f"{role} typed size estimate drift")
    if accounting["grouped_reconstruction"] != accounting["stwo_grouped_breakdown"]:
        raise BinaryTypedProofAccountingGateError(f"{role} grouped reconstruction drift")
    require_exact_int(accounting["record_stream_bytes"], f"{role} record_stream_bytes")
    require_float(accounting["json_over_local_typed_ratio"], f"{role} json_over_local_typed_ratio")
    require_exact_int(accounting["json_minus_local_typed_bytes"], f"{role} json_minus_local_typed_bytes")
    if not isinstance(accounting["record_stream_sha256"], str) or len(accounting["record_stream_sha256"]) != 64:
        raise BinaryTypedProofAccountingGateError(f"{role} record stream commitment drift")


def validate_record(record: Any, expected_path: str, role: str) -> None:
    if not isinstance(record, dict) or set(record) != {
        "path",
        "scalar_kind",
        "item_count",
        "item_size_bytes",
        "total_bytes",
    }:
        raise BinaryTypedProofAccountingGateError(f"{role} accounting record field drift")
    if record["path"] != expected_path:
        raise BinaryTypedProofAccountingGateError(f"{role} accounting record path drift")
    count = require_exact_int(record["item_count"], f"{role} {expected_path} item_count")
    size = require_exact_int(record["item_size_bytes"], f"{role} {expected_path} item_size_bytes")
    total = require_exact_int(record["total_bytes"], f"{role} {expected_path} total_bytes")
    if count < 0 or size <= 0 or total != count * size:
        raise BinaryTypedProofAccountingGateError(f"{role} accounting record total drift")


def build_payload(cli_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = cli_summary if cli_summary is not None else run_binary_accounting_cli()
    validate_cli_summary(summary)
    rows = []
    for row, expected in zip(summary["rows"], EXPECTED_ROLES, strict=True):
        accounting = row["local_binary_accounting"]
        rows.append(
            {
                "role": expected["role"],
                "evidence_relative_path": row["evidence_relative_path"],
                "envelope_metadata": row["envelope_metadata"],
                "envelope_sha256": row["envelope_sha256"],
                "proof_sha256": row["proof_sha256"],
                "proof_json_size_bytes": row["proof_json_size_bytes"],
                "local_binary_accounting": accounting,
            }
        )
    aggregate = build_aggregate(rows)
    base = {
        "schema": SCHEMA,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "timing_policy": TIMING_POLICY,
        "accounting_status": ACCOUNTING_STATUS,
        "binary_serialization_status": BINARY_SERIALIZATION_STATUS,
        "first_blocker": FIRST_BLOCKER,
        "non_claims": list(NON_CLAIMS),
        "cli_summary_commitment": "sha256:" + sha256_json(summary),
        "cli_schema": summary["schema"],
        "cli_accounting_domain": summary["accounting_domain"],
        "cli_accounting_format_version": summary["accounting_format_version"],
        "cli_upstream_stwo_serialization_status": summary["upstream_stwo_serialization_status"],
        "proof_payload_kind": summary["proof_payload_kind"],
        "size_constants": summary["size_constants"],
        "profile_rows": rows,
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


def build_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source, sidecar, fused = rows
    source_bytes = source["proof_json_size_bytes"]
    sidecar_bytes = sidecar["proof_json_size_bytes"]
    fused_bytes = fused["proof_json_size_bytes"]
    source_plus_sidecar = source_bytes + sidecar_bytes
    local_source = source["local_binary_accounting"]["typed_size_estimate_bytes"]
    local_sidecar = sidecar["local_binary_accounting"]["typed_size_estimate_bytes"]
    local_fused = fused["local_binary_accounting"]["typed_size_estimate_bytes"]
    return {
        "profiles_checked": len(rows),
        "roles_checked": [row["role"] for row in rows],
        "source_plus_sidecar_json_proof_bytes": source_plus_sidecar,
        "fused_json_proof_bytes": fused_bytes,
        "fused_saves_vs_source_plus_sidecar_json_bytes": source_plus_sidecar - fused_bytes,
        "source_plus_sidecar_local_typed_bytes": local_source + local_sidecar,
        "fused_local_typed_bytes": local_fused,
        "fused_saves_vs_source_plus_sidecar_local_typed_bytes": local_source + local_sidecar - local_fused,
        "record_stream_commitments": {
            row["role"]: row["local_binary_accounting"]["record_stream_sha256"] for row in rows
        },
        "profile_commitment": blake2b_commitment(rows, "zkai:stwo:d32:binary-typed-proof-accounting:profiles:v1"),
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
        "first_blocker",
        "non_claims",
        "cli_summary_commitment",
        "cli_schema",
        "cli_accounting_domain",
        "cli_accounting_format_version",
        "cli_upstream_stwo_serialization_status",
        "proof_payload_kind",
        "size_constants",
        "profile_rows",
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
        "first_blocker": FIRST_BLOCKER,
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
    rows = payload["profile_rows"]
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_ROLES):
        raise BinaryTypedProofAccountingGateError("profile row count drift")
    for profile_row, cli_row, expected in zip(rows, cli_summary["rows"], EXPECTED_ROLES, strict=True):
        validate_profile_row(profile_row, cli_row, expected)
    if payload["aggregate"] != build_aggregate(rows):
        raise BinaryTypedProofAccountingGateError("aggregate drift")
    if payload["payload_commitment"] != payload_commitment(payload):
        raise BinaryTypedProofAccountingGateError("payload commitment drift")
    if not allow_missing_mutation_summary or "mutation_cases" in payload:
        validate_mutation_summary(payload)


def validate_profile_row(profile_row: Any, cli_row: dict[str, Any], expected: dict[str, Any]) -> None:
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
    if profile_row["role"] != expected["role"]:
        raise BinaryTypedProofAccountingGateError(f"{expected['role']} role drift")
    for key in (
        "evidence_relative_path",
        "envelope_metadata",
        "envelope_sha256",
        "proof_sha256",
        "proof_json_size_bytes",
        "local_binary_accounting",
    ):
        if profile_row[key] != cli_row[key]:
            raise BinaryTypedProofAccountingGateError(f"{expected['role']} {key} drift")
    validate_cli_row(cli_row, expected)


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
    payload = copy.deepcopy(payload)
    payload.pop("payload_commitment", None)
    return blake2b_commitment(payload, "zkai:stwo:d32:binary-typed-proof-accounting:payload:v1")


def mutation_cases_for(base_payload: dict[str, Any], cli_summary: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name in MUTATION_NAMES:
        mutated = mutate_payload(base_payload, name)
        try:
            validate_payload(mutated, cli_summary, allow_missing_mutation_summary=True)
        except BinaryTypedProofAccountingGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        except Exception:
            raise
        else:
            cases.append({"name": name, "rejected": False, "error": ""})
    return cases


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if name == "schema_relabeling":
        mutated["schema"] = "zkai-attention-kv-stwo-binary-typed-proof-accounting-gate-v2"
    elif name == "decision_overclaim":
        mutated["decision"] = "GO_UPSTREAM_STWO_BINARY_SERIALIZATION"
    elif name == "claim_boundary_overclaim":
        mutated["claim_boundary"] = "UPSTREAM_STWO_BINARY_SERIALIZATION_AND_TIMING_BENCHMARK"
    elif name == "accounting_status_overclaim":
        mutated["accounting_status"] = "GO_UPSTREAM_BINARY_PROOF_ACCOUNTING"
    elif name == "upstream_serialization_overclaim":
        mutated["binary_serialization_status"] = "GO_UPSTREAM_STWO_PROOF_SERIALIZATION"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "non_claim_removed":
        mutated["non_claims"] = list(mutated["non_claims"][:-1])
    elif name == "role_order_drift":
        mutated["profile_rows"] = [mutated["profile_rows"][1], mutated["profile_rows"][0], mutated["profile_rows"][2]]
    elif name == "role_relabeling":
        mutated["profile_rows"][0]["role"] = "fused"
    elif name == "proof_backend_version_relabeling":
        mutated["profile_rows"][0]["envelope_metadata"]["proof_backend_version"] += "-mutated"
    elif name == "verifier_domain_relabeling":
        mutated["profile_rows"][1]["envelope_metadata"]["verifier_domain"] += ":mutated"
    elif name == "proof_schema_version_relabeling":
        mutated["profile_rows"][2]["envelope_metadata"]["proof_schema_version"] += "-mutated"
    elif name == "local_typed_metric_smuggling":
        mutated["profile_rows"][2]["local_binary_accounting"]["typed_size_estimate_bytes"] += 1
    elif name == "record_total_metric_smuggling":
        mutated["profile_rows"][2]["local_binary_accounting"]["records"][0]["total_bytes"] += 1
    elif name == "record_stream_commitment_relabeling":
        mutated["profile_rows"][2]["local_binary_accounting"]["record_stream_sha256"] = "00" * 32
    elif name == "proof_sha256_relabeling":
        mutated["profile_rows"][2]["proof_sha256"] = "11" * 32
    elif name == "aggregate_metric_smuggling":
        mutated["aggregate"]["fused_saves_vs_source_plus_sidecar_local_typed_bytes"] += 1
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
    for row in payload["profile_rows"]:
        accounting = row["local_binary_accounting"]
        writer.writerow(
            {
                "role": row["role"],
                "proof_backend_version": row["envelope_metadata"]["proof_backend_version"],
                "proof_json_size_bytes": row["proof_json_size_bytes"],
                "local_typed_bytes": accounting["typed_size_estimate_bytes"],
                "json_minus_local_typed_bytes": accounting["json_minus_local_typed_bytes"],
                "json_over_local_typed_ratio": accounting["json_over_local_typed_ratio"],
                "record_stream_sha256": accounting["record_stream_sha256"],
                "proof_sha256": row["proof_sha256"],
            }
        )
    return out.getvalue()


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    path = path.resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    if not path.parent.exists():
        raise BinaryTypedProofAccountingGateError(f"output parent does not exist: {path.parent}")
    if path.exists() and path.is_symlink():
        raise BinaryTypedProofAccountingGateError(f"output path must not be a symlink: {path}")
    if evidence_root not in (path, *path.parents):
        raise BinaryTypedProofAccountingGateError(f"output path escapes evidence dir: {path}")
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
