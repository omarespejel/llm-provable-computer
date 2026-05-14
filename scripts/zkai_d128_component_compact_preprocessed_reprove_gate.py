#!/usr/bin/env python3
"""Gate the d128 compact-preprocessed component reprove result.

This records a stronger but still scoped result than the prior component-native
two-slice reprove: because this surface is public-row RMSNorm plus a public
projection bridge, the arithmetic can be enforced directly over preprocessed
columns with only one anchor trace column per selected component.  The result is
below NANOZK's paper-reported d128 row under this repo's local typed accounting,
but it is not a matched NANOZK benchmark and not a full transformer-block proof.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
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
COMPACT_ENVELOPE_PATH = (
    EVIDENCE_DIR
    / "zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json"
)
BASELINE_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json"
PRIOR_BUDGET_PATH = EVIDENCE_DIR / "zkai-native-d128-verifier-execution-compression-budget-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.tsv"

SCHEMA = "zkai-d128-component-compact-preprocessed-reprove-gate-v1"
DECISION = "GO_D128_COMPONENT_NATIVE_COMPACT_PREPROCESSED_REPROVE"
RESULT = "GO_BELOW_NANOZK_REPORTED_ROW_UNDER_LOCAL_TYPED_ACCOUNTING_WITH_STRICT_NON_CLAIMS"
ROUTE_ID = "native_stwo_d128_component_compact_preprocessed_two_slice_reprove"
QUESTION = (
    "Can the selected public d128 RMSNorm and projection-bridge relations be reproven with "
    "preprocessed public columns instead of duplicated public trace columns, while preserving "
    "statement binding and local verification?"
)
CLAIM_BOUNDARY = (
    "COMPACT_PUBLIC_PREPROCESSED_TWO_SLICE_BELOW_NANOZK_REPORTED_ROW_UNDER_LOCAL_TYPED_ACCOUNTING_"
    "NOT_A_MATCHED_NANOZK_BENCHMARK"
)
FIRST_BLOCKER = (
    "The typed proof object is now below NANOZK's paper-reported 6.9 KB row, but the workload is "
    "only the selected public RMSNorm plus projection-bridge surface, not NANOZK's full d128 "
    "transformer block row and not locally reproduced NANOZK evidence."
)
NEXT_RESEARCH_STEP = (
    "extend the compact-preprocessed technique to the next d128 model-faithful block relations "
    "and prove where private witness or lookup-heavy surfaces stop admitting this compression"
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
PREVIOUS_TARGET_GAP_TO_NANOZK_TYPED_BYTES = 5_788
BASELINE_COMPONENT_TYPED_BYTES = 9_056
BASELINE_COMPONENT_JSON_BYTES = 22_139
COMPACT_PROOF_JSON_BYTES = 17_350
COMPACT_LOCAL_TYPED_BYTES = 6_264
COMPACT_ENVELOPE_BYTES = 203_441

EXPECTED_COMPACT_ROLE = {
    "role": "compact_preprocessed_component_native_two_slice_reprove",
    "path": "zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json",
    "proof_backend_version": "stwo-d128-component-native-two-slice-compact-preprocessed-reprove-v1",
    "statement_version": "zkai-d128-component-native-two-slice-compact-preprocessed-reprove-statement-v1",
    "verifier_domain": None,
    "proof_schema_version": None,
    "target_id": None,
}
EXPECTED_BASELINE_ROLE = {
    "role": "component_native_two_slice_reprove_baseline",
    "path": "zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "proof_backend_version": "stwo-d128-component-native-two-slice-reprove-v1",
    "statement_version": "zkai-d128-component-native-two-slice-reprove-statement-v1",
    "verifier_domain": None,
    "proof_schema_version": None,
    "target_id": None,
}

EXPECTED_COMPACT_RECORD_COUNTS = {
    "pcs.commitments": 3,
    "pcs.trace_decommitments.hash_witness": 48,
    "pcs.sampled_values": 98,
    "pcs.queried_values": 294,
    "pcs.fri.first_layer.fri_witness": 3,
    "pcs.fri.inner_layers.fri_witness": 13,
    "pcs.fri.last_layer_poly": 1,
    "pcs.fri.first_layer.commitment": 1,
    "pcs.fri.inner_layers.commitments": 6,
    "pcs.fri.first_layer.decommitment.hash_witness": 13,
    "pcs.fri.inner_layers.decommitment.hash_witness": 29,
    "pcs.proof_of_work": 1,
    "pcs.config": 1,
}
EXPECTED_BASELINE_RECORD_COUNTS = {
    "pcs.commitments": 3,
    "pcs.trace_decommitments.hash_witness": 54,
    "pcs.sampled_values": 184,
    "pcs.queried_values": 552,
    "pcs.fri.first_layer.fri_witness": 3,
    "pcs.fri.inner_layers.fri_witness": 15,
    "pcs.fri.last_layer_poly": 1,
    "pcs.fri.first_layer.commitment": 1,
    "pcs.fri.inner_layers.commitments": 6,
    "pcs.fri.first_layer.decommitment.hash_witness": 15,
    "pcs.fri.inner_layers.decommitment.hash_witness": 32,
    "pcs.proof_of_work": 1,
    "pcs.config": 1,
}

EXPECTED_AGGREGATE = {
    "profiles_checked": 1,
    "compact_proof_json_size_bytes": 17_350,
    "compact_local_typed_bytes": 6_264,
    "baseline_component_json_size_bytes": 22_139,
    "baseline_component_typed_bytes": 9_056,
    "previous_verifier_target_json_bytes": 34_866,
    "previous_verifier_target_typed_bytes": 12_688,
    "nanozk_paper_reported_d128_block_proof_bytes": 6_900,
    "typed_saving_vs_component_baseline_bytes": 2_792,
    "json_saving_vs_component_baseline_bytes": 4_789,
    "typed_saving_ratio_vs_component_baseline": 0.308304,
    "json_saving_ratio_vs_component_baseline": 0.216315,
    "typed_ratio_vs_component_baseline": 0.691696,
    "json_ratio_vs_component_baseline": 0.783685,
    "typed_saving_vs_previous_target_bytes": 6_424,
    "json_saving_vs_previous_target_bytes": 17_516,
    "typed_saving_ratio_vs_previous_target": 0.506305,
    "json_saving_ratio_vs_previous_target": 0.502381,
    "typed_ratio_vs_previous_target": 0.493695,
    "json_ratio_vs_previous_target": 0.497619,
    "typed_saving_vs_nanozk_paper_row_bytes": 636,
    "typed_saving_ratio_vs_nanozk_paper_row": 0.092174,
    "typed_ratio_vs_nanozk_paper_row": 0.907826,
    "json_ratio_vs_nanozk_paper_row": 2.514493,
    "typed_gap_closed_vs_prior_budget": 1.109883,
    "typed_gap_overclosed_vs_nanozk_paper_row_bytes": 636,
    "comparison_status": "below_nanozk_reported_row_under_local_typed_accounting_not_matched_benchmark",
}

MECHANISM = (
    "public-row RMSNorm and projection-bridge values are committed as preprocessed columns",
    "the compact AIR evaluates arithmetic directly over those preprocessed columns",
    "one anchor trace column per selected component keeps the framework trace shape explicit",
    "statement, public-instance, native-parameter, and row commitments are still recomputed before verification",
    "the same publication-v1 Stwo PCS profile is used; no query-count weakening is claimed",
)

NON_CLAIMS = (
    "not a matched NANOZK benchmark",
    "not locally reproduced NANOZK evidence",
    "not proof that STARKs beat NANOZK",
    "not a full d128 transformer-block proof",
    "not private witness privacy",
    "not a timing result",
    "not upstream Stwo proof serialization",
    "not full transformer inference",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- prove-compact docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- verify-compact docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "python3 scripts/zkai_d128_component_compact_preprocessed_reprove_gate.py --write-json docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_d128_component_compact_preprocessed_reprove_gate.py scripts/tests/test_zkai_d128_component_compact_preprocessed_reprove_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_d128_component_compact_preprocessed_reprove_gate",
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
    "compact_local_typed_bytes",
    "baseline_component_typed_bytes",
    "typed_saving_vs_component_baseline_bytes",
    "typed_ratio_vs_component_baseline",
    "typed_ratio_vs_nanozk_paper_row",
    "typed_saving_vs_nanozk_paper_row_bytes",
    "comparison_status",
)

MUTATION_NAMES = (
    "schema_relabeling",
    "decision_overclaim",
    "result_overclaim",
    "claim_boundary_overclaim",
    "compact_typed_metric_smuggling",
    "compact_json_metric_smuggling",
    "compact_envelope_metric_smuggling",
    "baseline_typed_metric_smuggling",
    "nanozk_baseline_smuggling",
    "comparison_status_overclaim",
    "non_claim_removed",
    "mechanism_removed",
    "proof_backend_version_relabeling",
    "record_count_smuggling",
    "validation_command_drift",
    "first_blocker_removed",
    "payload_commitment_relabeling",
    "unknown_field_injection",
)

BINARY_ACCOUNTING_TIMEOUT_SECONDS = 900


class CompactPreprocessedGateError(ValueError):
    pass


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        raise CompactPreprocessedGateError("ratio denominator must be non-zero")
    return round(numerator / denominator, 6)


def payload_commitment(payload: dict[str, Any]) -> str:
    canonical = copy.deepcopy(payload)
    canonical.pop("payload_commitment", None)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CompactPreprocessedGateError(f"{label} must be object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CompactPreprocessedGateError(f"{label} must be list")
    return value


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CompactPreprocessedGateError(f"{label} must be integer")
    return value


def require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CompactPreprocessedGateError(f"{label} must be non-empty string")
    return value


def load_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return require_dict(payload, str(path))


def checked_compact_envelope_size(actual_size: int) -> int:
    if actual_size != COMPACT_ENVELOPE_BYTES:
        raise CompactPreprocessedGateError(
            "compact envelope JSON size drift: "
            f"got {actual_size}, expected {COMPACT_ENVELOPE_BYTES}"
        )
    return actual_size


def parse_json_stdout(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    if start < 0:
        raise CompactPreprocessedGateError("binary accounting stdout did not contain JSON")
    return require_dict(json.loads(stdout[start:]), "binary accounting summary")


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
        "docs/engineering/evidence",
        str(COMPACT_ENVELOPE_PATH.relative_to(ROOT)),
        str(BASELINE_ENVELOPE_PATH.relative_to(ROOT)),
    ]
    env = os.environ.copy()
    env.setdefault("CARGO_TERM_COLOR", "never")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=BINARY_ACCOUNTING_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        raise CompactPreprocessedGateError(
            "binary accounting command failed:\n"
            f"stdout:\n{completed.stdout[-1600:]}\n"
            f"stderr:\n{completed.stderr[-1600:]}"
        )
    return parse_json_stdout(completed.stdout)


def row_by_relative_path(cli_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = require_list(cli_summary.get("rows"), "cli rows")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_dict = require_dict(row, "cli row")
        path = require_str(row_dict.get("evidence_relative_path"), "evidence_relative_path")
        if path in out:
            raise CompactPreprocessedGateError(f"duplicate accounting row for {path}")
        out[path] = row_dict
    return out


def record_counts(row: dict[str, Any]) -> dict[str, int]:
    accounting = require_dict(row.get("local_binary_accounting"), "local_binary_accounting")
    records = require_list(accounting.get("records"), "records")
    counts = {}
    for record in records:
        record_dict = require_dict(record, "record")
        path = require_str(record_dict.get("path"), "record.path")
        counts[path] = require_int(record_dict.get("item_count"), f"{path}.item_count")
    return counts


def validate_accounting_summary(cli_summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if cli_summary.get("schema") != CLI_SCHEMA:
        raise CompactPreprocessedGateError("binary accounting schema drift")
    if cli_summary.get("accounting_domain") != ACCOUNTING_DOMAIN:
        raise CompactPreprocessedGateError("binary accounting domain drift")
    if cli_summary.get("accounting_format_version") != ACCOUNTING_FORMAT_VERSION:
        raise CompactPreprocessedGateError("binary accounting format version drift")
    if cli_summary.get("upstream_stwo_serialization_status") != UPSTREAM_SERIALIZATION_STATUS:
        raise CompactPreprocessedGateError("upstream serialization status drift")
    if cli_summary.get("proof_payload_kind") != PROOF_PAYLOAD_KIND:
        raise CompactPreprocessedGateError("proof payload kind drift")
    if cli_summary.get("size_constants") != EXPECTED_SIZE_CONSTANTS:
        raise CompactPreprocessedGateError("size constants drift")
    if cli_summary.get("safety") != EXPECTED_SAFETY:
        raise CompactPreprocessedGateError("safety policy drift")

    by_path = row_by_relative_path(cli_summary)
    expected_paths = {EXPECTED_COMPACT_ROLE["path"], EXPECTED_BASELINE_ROLE["path"]}
    if set(by_path) != expected_paths:
        raise CompactPreprocessedGateError("accounting row set drift")
    compact = require_dict(by_path.get(EXPECTED_COMPACT_ROLE["path"]), "compact accounting row")
    baseline = require_dict(by_path.get(EXPECTED_BASELINE_ROLE["path"]), "baseline accounting row")
    validate_role(compact, EXPECTED_COMPACT_ROLE, COMPACT_PROOF_JSON_BYTES, COMPACT_LOCAL_TYPED_BYTES)
    validate_role(baseline, EXPECTED_BASELINE_ROLE, BASELINE_COMPONENT_JSON_BYTES, BASELINE_COMPONENT_TYPED_BYTES)
    if record_counts(compact) != EXPECTED_COMPACT_RECORD_COUNTS:
        raise CompactPreprocessedGateError("compact record counts drift")
    if record_counts(baseline) != EXPECTED_BASELINE_RECORD_COUNTS:
        raise CompactPreprocessedGateError("baseline record counts drift")
    return compact, baseline


def validate_role(row: dict[str, Any], expected: dict[str, Any], json_bytes: int, typed_bytes: int) -> None:
    if row.get("evidence_relative_path") != expected["path"]:
        raise CompactPreprocessedGateError(f"{expected['role']} path drift")
    metadata = require_dict(row.get("envelope_metadata"), f"{expected['role']} metadata")
    for key in ("proof_backend_version", "statement_version", "verifier_domain", "proof_schema_version", "target_id"):
        if metadata.get(key) != expected[key]:
            raise CompactPreprocessedGateError(f"{expected['role']} {key} drift")
    if metadata.get("proof_backend") != "stwo":
        raise CompactPreprocessedGateError(f"{expected['role']} backend drift")
    if require_int(row.get("proof_json_size_bytes"), f"{expected['role']} proof json bytes") != json_bytes:
        raise CompactPreprocessedGateError(f"{expected['role']} proof json bytes drift")
    accounting = require_dict(row.get("local_binary_accounting"), f"{expected['role']} accounting")
    if require_int(accounting.get("typed_size_estimate_bytes"), f"{expected['role']} typed bytes") != typed_bytes:
        raise CompactPreprocessedGateError(f"{expected['role']} typed bytes drift")


def validate_prior_budget(prior_budget: dict[str, Any]) -> None:
    budget = require_dict(prior_budget.get("compression_budget"), "compression budget")
    expected = {
        "current_verifier_target_typed_bytes": PREVIOUS_TARGET_TYPED_BYTES,
        "current_verifier_target_json_bytes": PREVIOUS_TARGET_JSON_BYTES,
        "nanozk_paper_reported_d128_block_proof_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        "typed_bytes_to_remove_to_equal_nanozk": PREVIOUS_TARGET_GAP_TO_NANOZK_TYPED_BYTES,
    }
    for key, value in expected.items():
        if budget.get(key) != value:
            raise CompactPreprocessedGateError(f"prior compression budget {key} drift")


def build_payload(
    cli_summary: dict[str, Any] | None = None,
    prior_budget: dict[str, Any] | None = None,
    *,
    include_mutations: bool = True,
    compact_envelope_size_bytes: int,
) -> dict[str, Any]:
    if cli_summary is None:
        cli_summary = run_binary_accounting_cli()
    if prior_budget is None:
        prior_budget = load_json(PRIOR_BUDGET_PATH)
    compact, baseline = validate_accounting_summary(cli_summary)
    validate_prior_budget(prior_budget)

    aggregate = dict(EXPECTED_AGGREGATE)
    aggregate["compact_envelope_json_size_bytes"] = checked_compact_envelope_size(
        compact_envelope_size_bytes
    )
    if aggregate["typed_saving_vs_component_baseline_bytes"] != BASELINE_COMPONENT_TYPED_BYTES - COMPACT_LOCAL_TYPED_BYTES:
        raise CompactPreprocessedGateError("internal typed component saving arithmetic drift")
    if aggregate["typed_saving_vs_nanozk_paper_row_bytes"] != NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES - COMPACT_LOCAL_TYPED_BYTES:
        raise CompactPreprocessedGateError("internal NANOZK comparison arithmetic drift")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": NEXT_RESEARCH_STEP,
        "compact_profile_row": compact,
        "baseline_profile_row": baseline,
        "aggregate": aggregate,
        "mechanism": list(MECHANISM),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["payload_commitment"] = payload_commitment(payload)
    if include_mutations:
        mutation_cases = run_mutations(payload, cli_summary, prior_budget)
        payload["mutation_cases"] = mutation_cases
        payload["mutations_checked"] = len(mutation_cases)
        payload["mutations_rejected"] = sum(1 for case in mutation_cases if case["rejected"])
        payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
        payload["payload_commitment"] = payload_commitment(payload)
        validate_payload(payload, cli_summary, prior_budget)
    return payload


def validate_payload(
    payload: dict[str, Any],
    cli_summary: dict[str, Any],
    prior_budget: dict[str, Any],
    *,
    allow_missing_mutation_summary: bool = False,
) -> None:
    require_dict(payload, "payload")
    validate_accounting_summary(cli_summary)
    validate_prior_budget(prior_budget)

    payload_aggregate = require_dict(payload.get("aggregate"), "aggregate")
    compact_envelope_size_bytes = require_int(
        payload_aggregate.get("compact_envelope_json_size_bytes"),
        "compact_envelope_json_size_bytes",
    )
    expected = build_payload(
        cli_summary,
        prior_budget,
        include_mutations=False,
        compact_envelope_size_bytes=compact_envelope_size_bytes,
    )
    comparable = copy.deepcopy(payload)
    mutation_fields = ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected")
    mutation_present = any(field in comparable for field in mutation_fields)
    for field in mutation_fields:
        comparable.pop(field, None)
    comparable.pop("payload_commitment", None)
    expected.pop("payload_commitment", None)
    if comparable != expected:
        raise CompactPreprocessedGateError("payload drift from checked accounting summary")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise CompactPreprocessedGateError("payload commitment mismatch")
    if not allow_missing_mutation_summary and not mutation_present:
        raise CompactPreprocessedGateError("mutation summary missing")
    if mutation_present:
        mutation_cases = require_list(payload.get("mutation_cases"), "mutation_cases")
        if mutation_cases != run_mutations(expected, cli_summary, prior_budget):
            raise CompactPreprocessedGateError("mutation case evidence drift")
        if payload.get("mutations_checked") != len(MUTATION_NAMES):
            raise CompactPreprocessedGateError("mutation count drift")
        if payload.get("mutations_rejected") != len(MUTATION_NAMES):
            raise CompactPreprocessedGateError("mutation rejection count drift")
        if payload.get("all_mutations_rejected") is not True:
            raise CompactPreprocessedGateError("not all mutations rejected")


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if name == "schema_relabeling":
        mutated["schema"] += "-tampered"
    elif name == "decision_overclaim":
        mutated["decision"] = "GO_D128_COMPONENT_NATIVE_COMPACT_PREPROCESSED_BEATS_NANOZK"
    elif name == "result_overclaim":
        mutated["result"] = "GO_MATCHED_NANOZK_PROOF_SIZE_WIN"
    elif name == "claim_boundary_overclaim":
        mutated["claim_boundary"] = "STARKS_BEAT_NANOZK_FOR_D128_BLOCKS"
    elif name == "compact_typed_metric_smuggling":
        mutated["aggregate"]["compact_local_typed_bytes"] -= 1
    elif name == "compact_json_metric_smuggling":
        mutated["aggregate"]["compact_proof_json_size_bytes"] -= 1
    elif name == "compact_envelope_metric_smuggling":
        mutated["aggregate"]["compact_envelope_json_size_bytes"] -= 1
    elif name == "baseline_typed_metric_smuggling":
        mutated["aggregate"]["baseline_component_typed_bytes"] += 1
    elif name == "nanozk_baseline_smuggling":
        mutated["aggregate"]["nanozk_paper_reported_d128_block_proof_bytes"] += 1
    elif name == "comparison_status_overclaim":
        mutated["aggregate"]["comparison_status"] = "matched_nanozk_benchmark_win"
    elif name == "non_claim_removed":
        mutated["non_claims"].remove("not a matched NANOZK benchmark")
    elif name == "mechanism_removed":
        mutated["mechanism"].remove("one anchor trace column per selected component keeps the framework trace shape explicit")
    elif name == "proof_backend_version_relabeling":
        mutated["compact_profile_row"]["envelope_metadata"]["proof_backend_version"] = "stwo-d128-full-block-v1"
    elif name == "record_count_smuggling":
        records = mutated["compact_profile_row"]["local_binary_accounting"]["records"]
        records[2]["item_count"] -= 1
    elif name == "validation_command_drift":
        mutated["validation_commands"] = mutated["validation_commands"][:-1]
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = "matched proof-size win"
    elif name == "payload_commitment_relabeling":
        mutated["payload_commitment"] = "sha256:" + ("00" * 32)
        return mutated
    elif name == "unknown_field_injection":
        mutated["matched_nanozk_win"] = True
    else:
        raise CompactPreprocessedGateError(f"unknown mutation: {name}")
    mutated["payload_commitment"] = payload_commitment(mutated)
    return mutated


def run_mutations(
    payload: dict[str, Any], cli_summary: dict[str, Any], prior_budget: dict[str, Any]
) -> list[dict[str, Any]]:
    base = copy.deepcopy(payload)
    for field in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        base.pop(field, None)
    cases = []
    for name in MUTATION_NAMES:
        mutated = mutate_payload(base, name)
        try:
            validate_payload(mutated, cli_summary, prior_budget, allow_missing_mutation_summary=True)
        except CompactPreprocessedGateError as error:
            cases.append({"name": name, "rejected": True, "error": str(error)})
        else:
            cases.append({"name": name, "rejected": False, "error": ""})
    return cases


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as tmp:
        tmp.write(data)
        tmp_path = pathlib.Path(tmp.name)
    tmp_path.replace(path)


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    row = {
        "object_id": ROUTE_ID,
        "compact_local_typed_bytes": payload["aggregate"]["compact_local_typed_bytes"],
        "baseline_component_typed_bytes": payload["aggregate"]["baseline_component_typed_bytes"],
        "typed_saving_vs_component_baseline_bytes": payload["aggregate"][
            "typed_saving_vs_component_baseline_bytes"
        ],
        "typed_ratio_vs_component_baseline": payload["aggregate"]["typed_ratio_vs_component_baseline"],
        "typed_ratio_vs_nanozk_paper_row": payload["aggregate"]["typed_ratio_vs_nanozk_paper_row"],
        "typed_saving_vs_nanozk_paper_row_bytes": payload["aggregate"][
            "typed_saving_vs_nanozk_paper_row_bytes"
        ],
        "comparison_status": payload["aggregate"]["comparison_status"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, newline="", encoding="utf-8") as tmp:
        writer = csv.DictWriter(tmp, fieldnames=TSV_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
        tmp_path = pathlib.Path(tmp.name)
    tmp_path.replace(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    parser.add_argument("--skip-mutations", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    cli_summary = run_binary_accounting_cli()
    prior_budget = load_json(PRIOR_BUDGET_PATH)
    payload = build_payload(
        cli_summary,
        prior_budget,
        include_mutations=not args.skip_mutations,
        compact_envelope_size_bytes=COMPACT_ENVELOPE_PATH.stat().st_size,
    )
    if args.skip_mutations:
        validate_payload(payload, cli_summary, prior_budget, allow_missing_mutation_summary=True)
    write_json(args.write_json, payload)
    write_tsv(args.write_tsv, payload)
    print(
        json.dumps(
            {
                "schema": "zkai-d128-component-compact-preprocessed-reprove-gate-summary-v1",
                "json_out": str(args.write_json),
                "tsv_out": str(args.write_tsv),
                "compact_local_typed_bytes": payload["aggregate"]["compact_local_typed_bytes"],
                "typed_ratio_vs_nanozk_paper_row": payload["aggregate"][
                    "typed_ratio_vs_nanozk_paper_row"
                ],
                "mutations_checked": payload.get("mutations_checked", 0),
                "all_mutations_rejected": payload.get("all_mutations_rejected", False),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
