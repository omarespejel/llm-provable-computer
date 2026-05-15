#!/usr/bin/env python3
"""Gate the d128 gate/value compact-preprocessed proof-size probe.

The compact-preprocessed trick that helped the selected public RMSNorm and
projection-bridge two-slice surface does not automatically win on the dense
d128 gate/value projection surface.  This gate records the checked no-go: a
real compact Stwo proof verifies for 131,072 multiplication rows, but its typed
proof-field accounting is larger than the baseline native gate/value proof.
"""

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
import subprocess
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
COMPACT_ENVELOPE_PATH = (
    EVIDENCE_DIR / "zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json"
)
BASELINE_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-gate-value-projection-proof-2026-05.envelope.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-gate-value-compact-preprocessed-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-gate-value-compact-preprocessed-gate-2026-05.tsv"

SCHEMA = "zkai-d128-gate-value-compact-preprocessed-gate-v1"
DECISION = "NO_GO_D128_GATE_VALUE_COMPACT_PREPROCESSED_SIZE_WIN"
RESULT = "NO_GO_COMPACT_PREPROCESSED_DENSE_GATE_VALUE_IS_LARGER_THAN_BASELINE"
ROUTE_ID = "native_stwo_d128_gate_value_compact_preprocessed_probe"
QUESTION = (
    "Does the compact-preprocessed proof architecture that helped the public two-slice d128 "
    "surface also reduce proof-field bytes on the dense d128 gate/value projection relation?"
)
CLAIM_BOUNDARY = (
    "COMPACT_PREPROCESSED_D128_GATE_VALUE_VERIFIES_BUT_IS_LARGER_THAN_BASELINE_"
    "NOT_A_FULL_BLOCK_PROOF_NOT_A_NANOZK_BENCHMARK"
)
FIRST_BLOCKER = (
    "The compact route saves some queried/opened values, but the extra row-order/anchor shape "
    "raises FRI and Merkle decommitment bytes enough to make the proof 2,312 typed bytes larger."
)
NEXT_RESEARCH_STEP = (
    "do not push compact-preprocessed as the dense-arithmetic path; instead test fusion or "
    "component aggregation across adjacent dense and lookup-heavy relations"
)

COMPACT_ROLE = "compact_preprocessed_gate_value_projection"
BASELINE_ROLE = "baseline_gate_value_projection"
COMPACT_RELATIVE_PATH = "zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json"
BASELINE_RELATIVE_PATH = "zkai-d128-gate-value-projection-proof-2026-05.envelope.json"
COMPACT_PROOF_BACKEND_VERSION = "stwo-d128-gate-value-projection-compact-preprocessed-air-proof-v1"
BASELINE_PROOF_BACKEND_VERSION = "stwo-d128-gate-value-projection-air-proof-v1"
COMPACT_STATEMENT_VERSION = "zkai-d128-gate-value-projection-compact-preprocessed-statement-v1"
BASELINE_STATEMENT_VERSION = "zkai-d128-gate-value-projection-statement-v1"

ROW_COUNT = 131_072
GATE_ROWS = 65_536
VALUE_ROWS = 65_536
NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900

COMPACT_PROOF_JSON_BYTES = 66_218
BASELINE_PROOF_JSON_BYTES = 57_930
COMPACT_LOCAL_TYPED_BYTES = 18_672
BASELINE_LOCAL_TYPED_BYTES = 16_360
COMPACT_ENVELOPE_BYTES = 549_922
BASELINE_ENVELOPE_BYTES = 483_523

EXPECTED_SIZE_CONSTANTS = {
    "base_field_bytes": 4,
    "secure_field_bytes": 16,
    "blake2s_hash_bytes": 32,
    "proof_of_work_bytes": 8,
    "pcs_config_bytes": 40,
}
EXPECTED_SAFETY = {
    "max_envelope_json_bytes": 16 * 1024 * 1024,
    "max_proof_json_bytes": 2 * 1024 * 1024,
    "path_policy": "inputs_must_be_regular_non_symlink_files_inside_canonical_evidence_dir",
    "commitment": "sha256_over_repo_owned_canonical_local_binary_accounting_record_stream",
}
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
EXPECTED_RECORD_SCALAR_KINDS = {
    "pcs.commitments": "blake2s_hash",
    "pcs.trace_decommitments.hash_witness": "blake2s_hash",
    "pcs.sampled_values": "secure_field",
    "pcs.queried_values": "base_field",
    "pcs.fri.first_layer.fri_witness": "secure_field",
    "pcs.fri.inner_layers.fri_witness": "secure_field",
    "pcs.fri.last_layer_poly": "secure_field",
    "pcs.fri.first_layer.commitment": "blake2s_hash",
    "pcs.fri.inner_layers.commitments": "blake2s_hash",
    "pcs.fri.first_layer.decommitment.hash_witness": "blake2s_hash",
    "pcs.fri.inner_layers.decommitment.hash_witness": "blake2s_hash",
    "pcs.proof_of_work": "u64_le",
    "pcs.config": "pcs_config",
}
EXPECTED_RECORD_SIZE_KEYS = {
    "base_field": "base_field_bytes",
    "secure_field": "secure_field_bytes",
    "blake2s_hash": "blake2s_hash_bytes",
    "u64_le": "proof_of_work_bytes",
    "pcs_config": "pcs_config_bytes",
}
EXPECTED_COMPACT_RECORD_COUNTS = {
    "pcs.commitments": 3,
    "pcs.trace_decommitments.hash_witness": 147,
    "pcs.sampled_values": 16,
    "pcs.queried_values": 48,
    "pcs.fri.first_layer.fri_witness": 3,
    "pcs.fri.inner_layers.fri_witness": 46,
    "pcs.fri.last_layer_poly": 1,
    "pcs.fri.first_layer.commitment": 1,
    "pcs.fri.inner_layers.commitments": 16,
    "pcs.fri.first_layer.decommitment.hash_witness": 46,
    "pcs.fri.inner_layers.decommitment.hash_witness": 330,
    "pcs.proof_of_work": 1,
    "pcs.config": 1,
}
EXPECTED_BASELINE_RECORD_COUNTS = {
    "pcs.commitments": 3,
    "pcs.trace_decommitments.hash_witness": 132,
    "pcs.sampled_values": 22,
    "pcs.queried_values": 66,
    "pcs.fri.first_layer.fri_witness": 3,
    "pcs.fri.inner_layers.fri_witness": 41,
    "pcs.fri.last_layer_poly": 1,
    "pcs.fri.first_layer.commitment": 1,
    "pcs.fri.inner_layers.commitments": 16,
    "pcs.fri.first_layer.decommitment.hash_witness": 41,
    "pcs.fri.inner_layers.decommitment.hash_witness": 275,
    "pcs.proof_of_work": 1,
    "pcs.config": 1,
}
EXPECTED_AGGREGATE = {
    "row_count": ROW_COUNT,
    "gate_projection_mul_rows": GATE_ROWS,
    "value_projection_mul_rows": VALUE_ROWS,
    "compact_proof_json_size_bytes": COMPACT_PROOF_JSON_BYTES,
    "baseline_proof_json_size_bytes": BASELINE_PROOF_JSON_BYTES,
    "compact_local_typed_bytes": COMPACT_LOCAL_TYPED_BYTES,
    "baseline_local_typed_bytes": BASELINE_LOCAL_TYPED_BYTES,
    "compact_envelope_json_size_bytes": COMPACT_ENVELOPE_BYTES,
    "baseline_envelope_json_size_bytes": BASELINE_ENVELOPE_BYTES,
    "typed_increase_vs_baseline_bytes": 2_312,
    "json_increase_vs_baseline_bytes": 8_288,
    "typed_increase_ratio_vs_baseline": 0.14132,
    "json_increase_ratio_vs_baseline": 0.143069,
    "typed_ratio_vs_baseline": 1.14132,
    "json_ratio_vs_baseline": 1.143069,
    "compact_typed_ratio_vs_nanozk_paper_row": 2.706087,
    "baseline_typed_ratio_vs_nanozk_paper_row": 2.371014,
    "comparison_status": "compact_preprocessed_dense_gate_value_larger_than_baseline_no_go",
}
EXPECTED_GROUPED_DELTA_BYTES = {
    "fixed_overhead": 0,
    "fri_decommitments": 1_920,
    "fri_samples": 80,
    "oods_samples": -96,
    "queries_values": -72,
    "trace_decommitments": 480,
}

MECHANISM = (
    "the compact proof moves all seven gate/value row columns into the preprocessed tree",
    "one base anchor column pins the row index so the trace shape remains explicit",
    "row-order constraints keep matrix selector, output index, and input index bound to the row index",
    "the dense multiplication relation still verifies for all 131072 rows",
    "proof-field bytes increase because FRI and Merkle decommitments grow more than queried/opened values shrink",
)

NON_CLAIMS = (
    "not a full d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not evidence that compact-preprocessed is the right dense-arithmetic path",
    "not private parameter-opening proof",
    "not upstream Stwo proof serialization",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- prove docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- prove-compact docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- verify-compact docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json",
    "python3 scripts/zkai_d128_gate_value_compact_preprocessed_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_gate_value_compact_preprocessed_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_gate_value_projection_proof --lib",
    "git diff --check",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "route_id",
    "row_count",
    "compact_local_typed_bytes",
    "baseline_local_typed_bytes",
    "typed_increase_vs_baseline_bytes",
    "typed_ratio_vs_baseline",
    "comparison_status",
)

MUTATION_NAMES = (
    "schema_relabeling",
    "decision_overclaim",
    "result_overclaim",
    "route_id_relabeling",
    "question_relabeling",
    "claim_boundary_overclaim",
    "next_research_step_relabeling",
    "compact_typed_metric_smuggling",
    "baseline_typed_metric_smuggling",
    "comparison_status_overclaim",
    "grouped_delta_smuggling",
    "record_count_smuggling",
    "non_claim_removed",
    "mechanism_removed",
    "first_blocker_removed",
    "validation_command_drift",
    "payload_commitment_relabeling",
    "unknown_field_injection",
)

BINARY_ACCOUNTING_TIMEOUT_SECONDS = 900


class GateValueCompactGateError(ValueError):
    pass


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        raise GateValueCompactGateError("ratio denominator must be non-zero")
    return round(numerator / denominator, 6)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_commitment(payload: dict[str, Any]) -> str:
    canonical = copy.deepcopy(payload)
    canonical.pop("payload_commitment", None)
    return "sha256:" + hashlib.sha256(canonical_json_bytes(canonical)).hexdigest()


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateValueCompactGateError(f"{label} must be object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateValueCompactGateError(f"{label} must be list")
    return value


def require_exact_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GateValueCompactGateError(f"{label} must be integer")
    return value


def require_exact_number(value: Any, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GateValueCompactGateError(f"{label} must be number")
    return value


def role_for_row(row: dict[str, Any]) -> str:
    metadata = require_dict(row.get("envelope_metadata"), "envelope metadata")
    version = metadata.get("proof_backend_version")
    if version == COMPACT_PROOF_BACKEND_VERSION:
        return COMPACT_ROLE
    if version == BASELINE_PROOF_BACKEND_VERSION:
        return BASELINE_ROLE
    raise GateValueCompactGateError(f"unexpected proof backend version: {version!r}")


def rows_by_role(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = require_list(summary.get("rows"), "accounting rows")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_dict = require_dict(row, "accounting row")
        role = role_for_row(row_dict)
        if role in out:
            raise GateValueCompactGateError(f"duplicate accounting row for {role}")
        out[role] = row_dict
    if set(out) != {COMPACT_ROLE, BASELINE_ROLE}:
        raise GateValueCompactGateError(f"accounting row set drift: {sorted(out)}")
    return out


def validate_cli_summary(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if summary.get("schema") != "zkai-stwo-local-binary-proof-accounting-cli-v1":
        raise GateValueCompactGateError("accounting CLI schema drift")
    if summary.get("upstream_stwo_serialization_status") != "NOT_UPSTREAM_STWO_SERIALIZATION_LOCAL_ACCOUNTING_RECORD_STREAM_ONLY":
        raise GateValueCompactGateError("upstream serialization status drift")
    if require_dict(summary.get("size_constants"), "size constants") != EXPECTED_SIZE_CONSTANTS:
        raise GateValueCompactGateError("size constants drift")
    if require_dict(summary.get("safety"), "safety") != EXPECTED_SAFETY:
        raise GateValueCompactGateError("safety policy drift")
    rows = rows_by_role(summary)
    validate_accounting_row(
        rows[COMPACT_ROLE],
        COMPACT_RELATIVE_PATH,
        COMPACT_PROOF_JSON_BYTES,
        COMPACT_LOCAL_TYPED_BYTES,
        COMPACT_STATEMENT_VERSION,
        EXPECTED_COMPACT_RECORD_COUNTS,
    )
    validate_accounting_row(
        rows[BASELINE_ROLE],
        BASELINE_RELATIVE_PATH,
        BASELINE_PROOF_JSON_BYTES,
        BASELINE_LOCAL_TYPED_BYTES,
        BASELINE_STATEMENT_VERSION,
        EXPECTED_BASELINE_RECORD_COUNTS,
    )
    return rows


def expected_record_item_size(path: str) -> int:
    scalar_kind = EXPECTED_RECORD_SCALAR_KINDS.get(path)
    if scalar_kind is None:
        raise GateValueCompactGateError(f"unexpected record path: {path!r}")
    size_key = EXPECTED_RECORD_SIZE_KEYS[scalar_kind]
    return EXPECTED_SIZE_CONSTANTS[size_key]


def validate_accounting_row(
    row: dict[str, Any],
    relative_path: str,
    proof_json_size: int,
    local_typed_bytes: int,
    expected_statement_version: str,
    expected_counts: dict[str, int],
) -> None:
    if row.get("evidence_relative_path") != relative_path:
        raise GateValueCompactGateError("evidence relative path drift")
    if require_exact_int(row.get("proof_json_size_bytes"), "proof JSON bytes") != proof_json_size:
        raise GateValueCompactGateError("proof JSON byte drift")
    metadata = require_dict(row.get("envelope_metadata"), "envelope metadata")
    if metadata.get("statement_version") != expected_statement_version:
        raise GateValueCompactGateError("statement version drift")
    accounting = require_dict(row.get("local_binary_accounting"), "local binary accounting")
    if require_exact_int(accounting.get("typed_size_estimate_bytes"), "typed size") != local_typed_bytes:
        raise GateValueCompactGateError("typed size drift")
    if require_exact_int(accounting.get("component_sum_bytes"), "component sum") != local_typed_bytes:
        raise GateValueCompactGateError("component sum drift")
    records = require_list(accounting.get("records"), "records")
    if require_exact_int(accounting.get("record_count"), "accounting record count") != len(records):
        raise GateValueCompactGateError("accounting record count drift")
    if len(records) != len(expected_counts):
        raise GateValueCompactGateError("record path set drift")
    counts: dict[str, int] = {}
    paths = []
    recomputed_total = 0
    for item in records:
        record = require_dict(item, "record")
        path = record.get("path")
        if not isinstance(path, str):
            raise GateValueCompactGateError("record path must be string")
        if path in counts:
            raise GateValueCompactGateError(f"duplicate record path: {path}")
        if path not in expected_counts:
            raise GateValueCompactGateError(f"unexpected record path: {path}")
        paths.append(path)
        count = require_exact_int(record.get("item_count"), f"{path} item count")
        scalar_kind = EXPECTED_RECORD_SCALAR_KINDS[path]
        if record.get("scalar_kind") != scalar_kind:
            raise GateValueCompactGateError(f"record scalar kind drift: {path}")
        item_size = expected_record_item_size(path)
        if require_exact_int(record.get("item_size_bytes"), f"{path} item size") != item_size:
            raise GateValueCompactGateError(f"record item size drift: {path}")
        total_bytes = require_exact_int(record.get("total_bytes"), f"{path} total bytes")
        if total_bytes != count * item_size:
            raise GateValueCompactGateError(f"record total bytes drift: {path}")
        counts[path] = count
        recomputed_total += total_bytes
    if tuple(paths) != EXPECTED_RECORD_PATHS:
        raise GateValueCompactGateError("record path order drift")
    if counts != expected_counts:
        raise GateValueCompactGateError("record counts drift")
    if recomputed_total != local_typed_bytes:
        raise GateValueCompactGateError("record byte total drift")


def grouped_delta(rows: dict[str, dict[str, Any]]) -> dict[str, int]:
    compact = require_dict(rows[COMPACT_ROLE]["local_binary_accounting"], "compact accounting")
    baseline = require_dict(rows[BASELINE_ROLE]["local_binary_accounting"], "baseline accounting")
    compact_grouped = require_dict(compact.get("grouped_reconstruction"), "compact grouped")
    baseline_grouped = require_dict(baseline.get("grouped_reconstruction"), "baseline grouped")
    keys = sorted(EXPECTED_GROUPED_DELTA_BYTES)
    return {
        key: require_exact_int(compact_grouped.get(key), f"compact {key}")
        - require_exact_int(baseline_grouped.get(key), f"baseline {key}")
        for key in keys
    }


def build_payload(
    summary: dict[str, Any],
    *,
    compact_envelope_size_bytes: int,
    baseline_envelope_size_bytes: int,
    include_mutations: bool = True,
) -> dict[str, Any]:
    rows = validate_cli_summary(summary)
    if compact_envelope_size_bytes != COMPACT_ENVELOPE_BYTES:
        raise GateValueCompactGateError("compact envelope JSON size drift")
    if baseline_envelope_size_bytes != BASELINE_ENVELOPE_BYTES:
        raise GateValueCompactGateError("baseline envelope JSON size drift")
    delta = grouped_delta(rows)
    if delta != EXPECTED_GROUPED_DELTA_BYTES:
        raise GateValueCompactGateError("grouped delta drift")
    aggregate = dict(EXPECTED_AGGREGATE)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
        "aggregate": aggregate,
        "grouped_delta_bytes": delta,
        "mechanism": list(MECHANISM),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "compact_profile_row": profile_row(rows[COMPACT_ROLE], COMPACT_ROLE),
        "baseline_profile_row": profile_row(rows[BASELINE_ROLE], BASELINE_ROLE),
        "mutations_checked": len(MUTATION_NAMES),
        "mutations_rejected": len(MUTATION_NAMES),
        "all_mutations_rejected": True,
    }
    if include_mutations:
        payload["mutation_cases"] = mutation_cases(payload, summary)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload, summary, allow_missing_mutation_summary=not include_mutations)
    return payload


def profile_row(row: dict[str, Any], role: str) -> dict[str, Any]:
    accounting = require_dict(row.get("local_binary_accounting"), f"{role} accounting")
    metadata = require_dict(row.get("envelope_metadata"), f"{role} metadata")
    return {
        "role": role,
        "evidence_relative_path": row["evidence_relative_path"],
        "proof_backend_version": metadata["proof_backend_version"],
        "statement_version": metadata["statement_version"],
        "proof_json_size_bytes": row["proof_json_size_bytes"],
        "local_typed_bytes": accounting["typed_size_estimate_bytes"],
        "record_stream_sha256": accounting["record_stream_sha256"],
        "proof_sha256": row["proof_sha256"],
    }


def validate_payload(
    payload: dict[str, Any],
    summary: dict[str, Any],
    *,
    allow_missing_mutation_summary: bool = False,
) -> None:
    rows = validate_cli_summary(summary)
    expected_fields = {
        "schema",
        "decision",
        "result",
        "route_id",
        "question",
        "claim_boundary",
        "first_blocker",
        "next_research_step",
        "aggregate",
        "grouped_delta_bytes",
        "mechanism",
        "non_claims",
        "validation_commands",
        "compact_profile_row",
        "baseline_profile_row",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
        "payload_commitment",
    }
    if not allow_missing_mutation_summary:
        expected_fields.add("mutation_cases")
    if set(payload) != expected_fields:
        raise GateValueCompactGateError(f"payload field drift: {sorted(set(payload) ^ expected_fields)}")
    if payload["schema"] != SCHEMA:
        raise GateValueCompactGateError("schema drift")
    if payload["decision"] != DECISION:
        raise GateValueCompactGateError("decision drift")
    if payload["result"] != RESULT:
        raise GateValueCompactGateError("result drift")
    if payload["route_id"] != ROUTE_ID:
        raise GateValueCompactGateError("route id drift")
    if payload["question"] != QUESTION:
        raise GateValueCompactGateError("question drift")
    if payload["claim_boundary"] != CLAIM_BOUNDARY:
        raise GateValueCompactGateError("claim boundary drift")
    if payload["first_blocker"] != FIRST_BLOCKER:
        raise GateValueCompactGateError("first blocker drift")
    if payload["next_research_step"] != NEXT_RESEARCH_STEP:
        raise GateValueCompactGateError("next research step drift")
    aggregate = require_dict(payload["aggregate"], "aggregate")
    if aggregate != EXPECTED_AGGREGATE:
        raise GateValueCompactGateError("aggregate drift")
    for key, value in aggregate.items():
        if key == "comparison_status":
            if value != EXPECTED_AGGREGATE["comparison_status"]:
                raise GateValueCompactGateError("comparison status drift")
            continue
        require_exact_number(value, f"aggregate {key}")
    if require_dict(payload["grouped_delta_bytes"], "grouped delta") != EXPECTED_GROUPED_DELTA_BYTES:
        raise GateValueCompactGateError("grouped delta drift")
    if require_dict(payload["grouped_delta_bytes"], "grouped delta") != grouped_delta(rows):
        raise GateValueCompactGateError("grouped delta no longer matches accounting rows")
    if tuple(require_list(payload["mechanism"], "mechanism")) != MECHANISM:
        raise GateValueCompactGateError("mechanism drift")
    if tuple(require_list(payload["non_claims"], "non claims")) != NON_CLAIMS:
        raise GateValueCompactGateError("non-claims drift")
    if tuple(require_list(payload["validation_commands"], "validation commands")) != VALIDATION_COMMANDS:
        raise GateValueCompactGateError("validation command drift")
    if profile_row(rows[COMPACT_ROLE], COMPACT_ROLE) != require_dict(payload["compact_profile_row"], "compact profile"):
        raise GateValueCompactGateError("compact profile drift")
    if profile_row(rows[BASELINE_ROLE], BASELINE_ROLE) != require_dict(payload["baseline_profile_row"], "baseline profile"):
        raise GateValueCompactGateError("baseline profile drift")
    if require_exact_int(payload["mutations_checked"], "mutations checked") != len(MUTATION_NAMES):
        raise GateValueCompactGateError("mutation checked count drift")
    if require_exact_int(payload["mutations_rejected"], "mutations rejected") != len(MUTATION_NAMES):
        raise GateValueCompactGateError("mutation rejected count drift")
    if payload["all_mutations_rejected"] is not True:
        raise GateValueCompactGateError("all mutations rejected drift")
    if payload["payload_commitment"] != payload_commitment(payload):
        raise GateValueCompactGateError("payload commitment drift")
    if not allow_missing_mutation_summary:
        cases = require_list(payload.get("mutation_cases"), "mutation cases")
        if [case.get("name") for case in cases] != list(MUTATION_NAMES):
            raise GateValueCompactGateError("mutation case order drift")
        for case in cases:
            if case.get("rejected") is not True or not case.get("error"):
                raise GateValueCompactGateError("mutation case evidence drift")


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    mutated.pop("mutation_cases", None)
    if name == "schema_relabeling":
        mutated["schema"] = "v0"
    elif name == "decision_overclaim":
        mutated["decision"] = "GO_D128_GATE_VALUE_COMPACT_PREPROCESSED_SIZE_WIN"
    elif name == "result_overclaim":
        mutated["result"] = "GO_COMPACT_PREPROCESSED_DENSE_GATE_VALUE_SMALLER_THAN_BASELINE"
    elif name == "route_id_relabeling":
        mutated["route_id"] = "native_stwo_d128_gate_value_compact_preprocessed_size_win"
    elif name == "question_relabeling":
        mutated["question"] = "Did compact-preprocessed beat the dense d128 baseline?"
    elif name == "claim_boundary_overclaim":
        mutated["claim_boundary"] = "COMPACT_DENSE_GATE_VALUE_BEATS_BASELINE_AND_NANOZK"
    elif name == "next_research_step_relabeling":
        mutated["next_research_step"] = "promote compact-preprocessed as the dense-arithmetic path"
    elif name == "compact_typed_metric_smuggling":
        mutated["aggregate"]["compact_local_typed_bytes"] -= 1
    elif name == "baseline_typed_metric_smuggling":
        mutated["aggregate"]["baseline_local_typed_bytes"] += 1
    elif name == "comparison_status_overclaim":
        mutated["aggregate"]["comparison_status"] = "compact_preprocessed_dense_gate_value_size_win"
    elif name == "grouped_delta_smuggling":
        mutated["grouped_delta_bytes"]["fri_decommitments"] -= 32
    elif name == "record_count_smuggling":
        mutated["compact_profile_row"]["local_typed_bytes"] -= 1
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif name == "mechanism_removed":
        mutated["mechanism"] = mutated["mechanism"][:-1]
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "validation_command_drift":
        mutated["validation_commands"] = mutated["validation_commands"][:-1]
    elif name == "payload_commitment_relabeling":
        mutated["payload_commitment"] = "sha256:" + "00" * 32
        return mutated
    elif name == "unknown_field_injection":
        mutated["unexpected"] = True
    else:
        raise GateValueCompactGateError(f"unknown mutation: {name}")
    mutated["payload_commitment"] = payload_commitment(mutated)
    return mutated


def mutation_cases(payload: dict[str, Any], summary: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name in MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, summary, allow_missing_mutation_summary=True)
        except GateValueCompactGateError as error:
            cases.append({"name": name, "rejected": True, "error": str(error)})
        else:
            raise GateValueCompactGateError(f"mutation survived: {name}")
    return cases


def run_accounting_cli() -> dict[str, Any]:
    cmd = [
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
        "docs/engineering/evidence",
        str(COMPACT_ENVELOPE_PATH.relative_to(ROOT)),
        str(BASELINE_ENVELOPE_PATH.relative_to(ROOT)),
    ]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=BINARY_ACCOUNTING_TIMEOUT_SECONDS,
    )
    return json.loads(result.stdout)


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    write_bytes_atomic(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t")
    writer.writeheader()
    row = {column: payload["aggregate"].get(column, payload.get(column)) for column in TSV_COLUMNS}
    row["route_id"] = payload["route_id"]
    writer.writerow(row)
    write_bytes_atomic(path, handle.getvalue().encode("utf-8"))


def write_bytes_atomic(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        metadata = None
    if metadata is not None and stat.S_ISLNK(metadata.st_mode):
        raise GateValueCompactGateError(f"refusing to overwrite symlink: {path}")
    tmp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as tmp:
            tmp_name = tmp.name
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()

    compact_size = COMPACT_ENVELOPE_PATH.stat().st_size
    baseline_size = BASELINE_ENVELOPE_PATH.stat().st_size
    payload = build_payload(
        run_accounting_cli(),
        compact_envelope_size_bytes=compact_size,
        baseline_envelope_size_bytes=baseline_size,
    )
    write_json(args.write_json, payload)
    write_tsv(args.write_tsv, payload)
    print(json.dumps({"schema": SCHEMA, "decision": DECISION, "result": RESULT, "aggregate": payload["aggregate"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
