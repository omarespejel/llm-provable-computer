#!/usr/bin/env python3
"""Fuller width/head/sequence crossing grid for fused Softmax-table routes.

This gate is intentionally derived from the checked route matrix. It does not
generate new proofs. Its job is to make the missing width/head/sequence
crossings explicit, so the evidence frontier is auditable without promoting the
current 11 proved rows into a full factorial proof claim.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import pathlib
import sys
import tempfile
from itertools import product
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_fused_softmax_table_route_matrix_gate as matrix

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-fuller-crossing-grid-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-fuller-crossing-grid-2026-05.tsv"

SCHEMA = "zkai-attention-kv-fuller-width-head-sequence-crossing-grid-v1"
ISSUE = 7
SOURCE_ISSUE = matrix.ISSUE
DECISION = "GO_CHECKED_FULLER_CROSSING_GRID_WITH_FULL_PROOF_GRID_NO_GO"
ROUTE_ID = "local_stwo_attention_kv_fuller_width_head_sequence_crossing_grid"
GRID_STATUS = "GO_45_CELL_WIDTH_HEAD_SEQUENCE_STATUS_GRID_FROM_CHECKED_ROUTE_MATRIX"
FULL_PROOF_GRID_STATUS = "NO_GO_34_OF_45_GRID_CELLS_DO_NOT_HAVE_NATIVE_FUSED_PROOFS"
CLAIM_BOUNDARY = (
    "ENGINEERING_STATUS_GRID_FOR_CHECKED_NATIVE_STWO_FUSED_BOUNDED_SOFTMAX_TABLE_ROUTES_"
    "MAPS_PROVED_AND_MISSING_WIDTH_HEAD_SEQUENCE_CELLS_NOT_A_FULL_FACTORIAL_PROOF_GRID_"
    "NOT_TIMING_NOT_REAL_VALUED_SOFTMAX_NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD"
)
TIMING_POLICY = "status_grid_only_not_timing_not_public_benchmark"
PROVED_STATUS = "PROVED_NATIVE_FUSED_WITH_MATCHED_SOURCE_PLUS_LOGUP_SIDECAR_COMPARATOR"
MISSING_STATUS = "MISSING_NATIVE_FUSED_PROOF_AND_MATCHED_COMPARATOR"
WIDTHS = (8, 16, 32)
HEAD_COUNTS = (1, 2, 4, 8, 16)
STEPS_PER_HEAD = (8, 16, 32)
GRID_CELL_COUNT = len(WIDTHS) * len(HEAD_COUNTS) * len(STEPS_PER_HEAD)
EXPECTED_PROVED_KEYS = (
    (8, 1, 8),
    (16, 1, 8),
    (32, 1, 8),
    (8, 2, 8),
    (8, 4, 8),
    (8, 8, 8),
    (8, 16, 8),
    (8, 2, 16),
    (8, 2, 32),
    (16, 2, 8),
    (16, 2, 16),
)
EXPECTED_PROVED_PROFILE_IDS = (
    "d8_single_head_seq8",
    "d16_single_head_seq8",
    "d32_single_head_seq8",
    "d8_two_head_seq8",
    "d8_four_head_seq8",
    "d8_eight_head_seq8",
    "d8_sixteen_head_seq8",
    "d8_two_head_seq16",
    "d8_two_head_seq32",
    "d16_two_head_seq8",
    "d16_two_head_seq16",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_fuller_crossing_grid_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-fuller-crossing-grid-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-fuller-crossing-grid-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_fuller_crossing_grid_gate",
    "python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_route_matrix_gate",
)
GO_CRITERIA = (
    "the upstream fused Softmax-table route matrix validates locally",
    "exactly 11 checked route cells are marked proved and exactly 34 cells are marked missing",
    "every proved cell has matched source-plus-LogUp-sidecar comparator evidence from the route matrix",
    "missing cells carry no proof-byte, ratio, or evidence-path claims",
)
NO_GO_CRITERIA = (
    "full factorial proof-grid claim: 34 of 45 grid cells are missing native fused proofs",
    "new crossing proof claim: this PR7 slice adds no new proof profile",
    "timing or public benchmark claim: this gate records status only",
    "real-valued Softmax or full-inference claim: the upstream kernel is bounded integer Softmax-table/floor division",
)
NEXT_LOW_RISK_PROFILES = (
    {
        "profile_id": "d32_two_head_seq8",
        "key_width": 32,
        "head_count": 2,
        "steps_per_head": 8,
        "reason": "smallest missing d32 width/head crossing at the shortest checked sequence length",
        "go_condition": "source, sidecar, fused proof, verifier, and gate all validate with matched comparator evidence",
    },
    {
        "profile_id": "d16_two_head_seq32",
        "key_width": 16,
        "head_count": 2,
        "steps_per_head": 32,
        "reason": "extends the existing d16/two-head all-axis row along sequence only",
        "go_condition": "seq32 proof envelope remains bounded and the matched source-plus-sidecar comparator validates",
    },
    {
        "profile_id": "d32_two_head_seq16",
        "key_width": 32,
        "head_count": 2,
        "steps_per_head": 16,
        "reason": "first d32 row with all three pressure axes crossed, after d32/two-head/seq8 is stable",
        "go_condition": "only after the shorter d32/two-head crossing is checked",
    },
)
NON_CLAIMS = (
    "not a full factorial proved grid",
    "not a new native Stwo proof profile",
    "not timing evidence",
    "not exact real-valued Softmax",
    "not implementation-exact model Softmax",
    "not full transformer inference",
    "not recursion or PCD",
)
TSV_COLUMNS = (
    "cell_id",
    "status",
    "axis_role",
    "key_width",
    "head_count",
    "steps_per_head",
    "pressure_axes",
    "profile_id",
    "lookup_claims",
    "trace_rows",
    "fused_proof_size_bytes",
    "source_plus_sidecar_raw_proof_bytes",
    "fused_to_source_plus_sidecar_ratio",
    "evidence_json",
    "missing_reason",
)
EXPECTED_MUTATION_NAMES = (
    "decision_overclaim",
    "grid_status_overclaim",
    "full_proof_grid_status_overclaim",
    "claim_boundary_overclaim",
    "proved_count_smuggling",
    "missing_count_smuggling",
    "grid_cell_count_smuggling",
    "proved_cell_status_relabeling",
    "missing_cell_status_relabeling",
    "missing_cell_metric_injection",
    "missing_cell_evidence_injection",
    "proved_cell_metric_smuggling",
    "proved_profile_relabeling",
    "go_criteria_removed",
    "no_go_criteria_removed",
    "next_profile_overclaim",
    "non_claim_removed",
    "unknown_field_injection",
)


class FullerCrossingGridGateError(ValueError):
    pass


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise FullerCrossingGridGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def cell_id(key_width: int, head_count: int, steps_per_head: int) -> str:
    return f"d{key_width}_h{head_count}_seq{steps_per_head}"


def pressure_axes(key_width: int, head_count: int, steps_per_head: int) -> list[str]:
    axes = []
    if key_width > 8:
        axes.append("width")
    if head_count > 1:
        axes.append("head")
    if steps_per_head > 8:
        axes.append("sequence")
    return axes or ["baseline"]


def axis_role(axes: list[str]) -> str:
    if axes == ["baseline"]:
        return "baseline"
    if len(axes) == 1:
        return f"{axes[0]}_axis"
    return "_".join(axes) + "_crossing"


def read_checked_route_matrix() -> dict[str, Any]:
    result = matrix.build_result()
    matrix.validate_result(result)
    if result["profile_ids"] != list(EXPECTED_PROVED_PROFILE_IDS):
        raise FullerCrossingGridGateError("upstream route matrix profile order drift")
    return result


def route_by_key(route_result: dict[str, Any]) -> dict[tuple[int, int, int], dict[str, Any]]:
    routes = {}
    for row in route_result["route_rows"]:
        key = (row["key_width"], row["head_count"], row["steps_per_head"])
        if key in routes:
            raise FullerCrossingGridGateError("duplicate route matrix dimensions")
        if row["matched_source_sidecar_status"] != matrix.MATCHED_COMPARATOR_STATUS:
            raise FullerCrossingGridGateError(f"{row['profile_id']} missing matched comparator")
        routes[key] = row
    if tuple(routes) != EXPECTED_PROVED_KEYS:
        raise FullerCrossingGridGateError("proved key order drift")
    return routes


def proved_cell(row: dict[str, Any]) -> dict[str, Any]:
    axes = pressure_axes(row["key_width"], row["head_count"], row["steps_per_head"])
    return {
        "cell_id": cell_id(row["key_width"], row["head_count"], row["steps_per_head"]),
        "status": PROVED_STATUS,
        "axis_role": axis_role(axes),
        "key_width": row["key_width"],
        "value_width": row["value_width"],
        "head_count": row["head_count"],
        "steps_per_head": row["steps_per_head"],
        "pressure_axes": axes,
        "profile_id": row["profile_id"],
        "lookup_claims": row["lookup_claims"],
        "trace_rows": row["trace_rows"],
        "fused_proof_size_bytes": row["fused_proof_size_bytes"],
        "source_plus_sidecar_raw_proof_bytes": row["source_plus_sidecar_raw_proof_bytes"],
        "fused_to_source_plus_sidecar_ratio": row["fused_to_source_plus_sidecar_ratio"],
        "evidence_json": row["evidence_json"],
        "missing_reason": None,
    }


def missing_cell(key_width: int, head_count: int, steps_per_head: int) -> dict[str, Any]:
    axes = pressure_axes(key_width, head_count, steps_per_head)
    return {
        "cell_id": cell_id(key_width, head_count, steps_per_head),
        "status": MISSING_STATUS,
        "axis_role": axis_role(axes),
        "key_width": key_width,
        "value_width": key_width,
        "head_count": head_count,
        "steps_per_head": steps_per_head,
        "pressure_axes": axes,
        "profile_id": None,
        "lookup_claims": None,
        "trace_rows": None,
        "fused_proof_size_bytes": None,
        "source_plus_sidecar_raw_proof_bytes": None,
        "fused_to_source_plus_sidecar_ratio": None,
        "evidence_json": None,
        "missing_reason": "no checked native fused proof plus matched source-plus-LogUp-sidecar comparator for this cell",
    }


def build_grid_rows(route_result: dict[str, Any]) -> list[dict[str, Any]]:
    routes = route_by_key(route_result)
    rows = []
    for key_width, head_count, steps_per_head in product(WIDTHS, HEAD_COUNTS, STEPS_PER_HEAD):
        route = routes.get((key_width, head_count, steps_per_head))
        rows.append(proved_cell(route) if route is not None else missing_cell(key_width, head_count, steps_per_head))
    validate_grid_rows(rows)
    return rows


def count_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row[key]
        if isinstance(value, list):
            value = "+".join(value)
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    proved = [row for row in rows if row["status"] == PROVED_STATUS]
    missing = [row for row in rows if row["status"] == MISSING_STATUS]
    crossing_proved = [row for row in proved if len(row["pressure_axes"]) >= 2]
    all_axis_proved = [row for row in proved if row["pressure_axes"] == ["width", "head", "sequence"]]
    all_axis_missing = [row for row in missing if row["pressure_axes"] == ["width", "head", "sequence"]]
    return {
        "grid_cell_count": len(rows),
        "proved_cell_count": len(proved),
        "missing_cell_count": len(missing),
        "coverage_share": ratio(len(proved), len(rows)),
        "proved_profile_ids": [row["profile_id"] for row in proved],
        "proved_cell_ids": [row["cell_id"] for row in proved],
        "missing_cell_ids": [row["cell_id"] for row in missing],
        "proved_crossing_cell_count": len(crossing_proved),
        "proved_all_axis_cell_count": len(all_axis_proved),
        "missing_all_axis_cell_count": len(all_axis_missing),
        "status_counts": count_by_key(rows, "status"),
        "axis_role_counts": count_by_key(rows, "axis_role"),
        "width_counts": count_by_key(rows, "key_width"),
        "head_counts": count_by_key(rows, "head_count"),
        "steps_per_head_counts": count_by_key(rows, "steps_per_head"),
        "proved_counts_by_width": count_by_key(proved, "key_width"),
        "proved_counts_by_head_count": count_by_key(proved, "head_count"),
        "proved_counts_by_steps_per_head": count_by_key(proved, "steps_per_head"),
    }


def build_base_result() -> dict[str, Any]:
    route_result = read_checked_route_matrix()
    rows = build_grid_rows(route_result)
    result = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "grid_status": GRID_STATUS,
        "full_proof_grid_status": FULL_PROOF_GRID_STATUS,
        "claim_boundary": CLAIM_BOUNDARY,
        "timing_policy": TIMING_POLICY,
        "grid_axes": {
            "key_widths": list(WIDTHS),
            "head_counts": list(HEAD_COUNTS),
            "steps_per_head": list(STEPS_PER_HEAD),
        },
        "upstream_route_matrix": {
            "schema": route_result["schema"],
            "decision": route_result["decision"],
            "evidence_json": str(matrix.JSON_OUT.relative_to(ROOT)),
            "profiles_checked": route_result["profiles_checked"],
            "matched_comparator_profiles": route_result["matched_comparator_profiles"],
        },
        "summary": build_summary(rows),
        "grid_rows": rows,
        "go_criteria": list(GO_CRITERIA),
        "no_go_criteria": list(NO_GO_CRITERIA),
        "next_low_risk_profiles": list(NEXT_LOW_RISK_PROFILES),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_core(result)
    return result


def first_grid_row_with_status(rows: list[dict[str, Any]], status: str) -> dict[str, Any]:
    for row in rows:
        if row["status"] == status:
            return row
    raise FullerCrossingGridGateError(f"mutation target missing for status {status}")


def first_proved_grid_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return first_grid_row_with_status(rows, PROVED_STATUS)


def first_missing_grid_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return first_grid_row_with_status(rows, MISSING_STATUS)


def mutation_cases() -> tuple[tuple[str, Any], ...]:
    return (
        ("decision_overclaim", lambda v: v.__setitem__("decision", "GO_FULL_PROOF_GRID")),
        ("grid_status_overclaim", lambda v: v.__setitem__("grid_status", "GO_ALL_CELLS_PROVED")),
        ("full_proof_grid_status_overclaim", lambda v: v.__setitem__("full_proof_grid_status", "GO_45_OF_45_PROVED")),
        ("claim_boundary_overclaim", lambda v: v.__setitem__("claim_boundary", "GO_REAL_VALUED_SOFTMAX_PUBLIC_BENCHMARK")),
        ("proved_count_smuggling", lambda v: v["summary"].__setitem__("proved_cell_count", 45)),
        ("missing_count_smuggling", lambda v: v["summary"].__setitem__("missing_cell_count", 0)),
        ("grid_cell_count_smuggling", lambda v: v["summary"].__setitem__("grid_cell_count", 46)),
        ("proved_cell_status_relabeling", lambda v: first_proved_grid_row(v["grid_rows"]).__setitem__("status", MISSING_STATUS)),
        ("missing_cell_status_relabeling", lambda v: first_missing_grid_row(v["grid_rows"]).__setitem__("status", PROVED_STATUS)),
        ("missing_cell_metric_injection", lambda v: first_missing_grid_row(v["grid_rows"]).__setitem__("fused_proof_size_bytes", 1)),
        ("missing_cell_evidence_injection", lambda v: first_missing_grid_row(v["grid_rows"]).__setitem__("evidence_json", "docs/fake.json")),
        ("proved_cell_metric_smuggling", lambda v: first_proved_grid_row(v["grid_rows"]).__setitem__("lookup_claims", 1)),
        ("proved_profile_relabeling", lambda v: first_proved_grid_row(v["grid_rows"]).__setitem__("profile_id", "different_profile")),
        ("go_criteria_removed", lambda v: v.__setitem__("go_criteria", v["go_criteria"][:-1])),
        ("no_go_criteria_removed", lambda v: v.__setitem__("no_go_criteria", v["no_go_criteria"][:-1])),
        ("next_profile_overclaim", lambda v: v["next_low_risk_profiles"][0].__setitem__("go_condition", "already proved")),
        ("non_claim_removed", lambda v: v.__setitem__("non_claims", v["non_claims"][:-1])),
        ("unknown_field_injection", lambda v: v.__setitem__("extra", "field")),
    )


def run_declared_mutations(base: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for name, mutate in mutation_cases():
        candidate = copy.deepcopy(base)
        try:
            mutate(candidate)
        except Exception as err:  # pragma: no cover - defensive branch
            raise FullerCrossingGridGateError(f"mutation mutator failed: {name}: {err}") from err
        try:
            validate_result(candidate)
        except FullerCrossingGridGateError as err:
            results.append({"name": name, "rejected": True, "error": str(err)})
        else:
            raise FullerCrossingGridGateError(f"mutation was not rejected: {name}")
    return results


def build_result() -> dict[str, Any]:
    base = build_base_result()
    result = copy.deepcopy(base)
    result["mutation_results"] = run_declared_mutations(base)
    result["mutations_checked"] = len(result["mutation_results"])
    result["mutations_rejected"] = sum(1 for item in result["mutation_results"] if item["rejected"])
    validate_result(result)
    return result


def validate_grid_rows(rows: Any) -> None:
    if not isinstance(rows, list) or len(rows) != GRID_CELL_COUNT:
        raise FullerCrossingGridGateError("grid row count drift")
    expected_cell_ids = [
        cell_id(key_width, head_count, steps_per_head)
        for key_width, head_count, steps_per_head in product(WIDTHS, HEAD_COUNTS, STEPS_PER_HEAD)
    ]
    if [row.get("cell_id") if isinstance(row, dict) else None for row in rows] != expected_cell_ids:
        raise FullerCrossingGridGateError("grid cell order drift")
    for row in rows:
        validate_grid_row(row)


def validate_grid_row(row: Any) -> None:
    expected_fields = {
        "cell_id",
        "status",
        "axis_role",
        "key_width",
        "value_width",
        "head_count",
        "steps_per_head",
        "pressure_axes",
        "profile_id",
        "lookup_claims",
        "trace_rows",
        "fused_proof_size_bytes",
        "source_plus_sidecar_raw_proof_bytes",
        "fused_to_source_plus_sidecar_ratio",
        "evidence_json",
        "missing_reason",
    }
    if not isinstance(row, dict) or set(row) != expected_fields:
        raise FullerCrossingGridGateError("grid row field drift")
    expected_axes = pressure_axes(row["key_width"], row["head_count"], row["steps_per_head"])
    if row["cell_id"] != cell_id(row["key_width"], row["head_count"], row["steps_per_head"]):
        raise FullerCrossingGridGateError("cell id drift")
    if row["value_width"] != row["key_width"]:
        raise FullerCrossingGridGateError("value width drift")
    if row["pressure_axes"] != expected_axes or row["axis_role"] != axis_role(expected_axes):
        raise FullerCrossingGridGateError("axis role drift")
    key = (row["key_width"], row["head_count"], row["steps_per_head"])
    if key in EXPECTED_PROVED_KEYS:
        if row["status"] != PROVED_STATUS:
            raise FullerCrossingGridGateError("proved cell status drift")
        if row["profile_id"] is None or row["evidence_json"] is None:
            raise FullerCrossingGridGateError("proved cell evidence drift")
        for field in (
            "lookup_claims",
            "trace_rows",
            "fused_proof_size_bytes",
            "source_plus_sidecar_raw_proof_bytes",
            "fused_to_source_plus_sidecar_ratio",
        ):
            if row[field] is None:
                raise FullerCrossingGridGateError("proved cell metric drift")
        if row["missing_reason"] is not None:
            raise FullerCrossingGridGateError("proved cell missing reason drift")
    else:
        if row["status"] != MISSING_STATUS:
            raise FullerCrossingGridGateError("missing cell status drift")
        if row["profile_id"] is not None or row["evidence_json"] is not None:
            raise FullerCrossingGridGateError("missing cell evidence drift")
        for field in (
            "lookup_claims",
            "trace_rows",
            "fused_proof_size_bytes",
            "source_plus_sidecar_raw_proof_bytes",
            "fused_to_source_plus_sidecar_ratio",
        ):
            if row[field] is not None:
                raise FullerCrossingGridGateError("missing cell metric drift")
        if not row["missing_reason"]:
            raise FullerCrossingGridGateError("missing cell reason drift")


def validate_core(result: Any) -> None:
    expected_fields = {
        "schema",
        "issue",
        "source_issue",
        "decision",
        "route_id",
        "grid_status",
        "full_proof_grid_status",
        "claim_boundary",
        "timing_policy",
        "grid_axes",
        "upstream_route_matrix",
        "summary",
        "grid_rows",
        "go_criteria",
        "no_go_criteria",
        "next_low_risk_profiles",
        "non_claims",
        "validation_commands",
    }
    if not isinstance(result, dict) or set(result) != expected_fields:
        raise FullerCrossingGridGateError("result field drift")
    expected_scalars = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "grid_status": GRID_STATUS,
        "full_proof_grid_status": FULL_PROOF_GRID_STATUS,
        "claim_boundary": CLAIM_BOUNDARY,
        "timing_policy": TIMING_POLICY,
        "go_criteria": list(GO_CRITERIA),
        "no_go_criteria": list(NO_GO_CRITERIA),
        "next_low_risk_profiles": list(NEXT_LOW_RISK_PROFILES),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    for key, expected in expected_scalars.items():
        if result[key] != expected:
            raise FullerCrossingGridGateError(f"result drift for {key}")
    if result["grid_axes"] != {
        "key_widths": list(WIDTHS),
        "head_counts": list(HEAD_COUNTS),
        "steps_per_head": list(STEPS_PER_HEAD),
    }:
        raise FullerCrossingGridGateError("grid axes drift")
    validate_grid_rows(result["grid_rows"])
    expected_summary = build_summary(result["grid_rows"])
    if result["summary"] != expected_summary:
        raise FullerCrossingGridGateError("summary drift")
    upstream = result["upstream_route_matrix"]
    if upstream != {
        "schema": matrix.SCHEMA,
        "decision": matrix.DECISION,
        "evidence_json": str(matrix.JSON_OUT.relative_to(ROOT)),
        "profiles_checked": len(EXPECTED_PROVED_KEYS),
        "matched_comparator_profiles": len(EXPECTED_PROVED_KEYS),
    }:
        raise FullerCrossingGridGateError("upstream route matrix summary drift")


def validate_result(result: Any) -> None:
    if not isinstance(result, dict):
        raise FullerCrossingGridGateError("result must be an object")
    mutation_results = result.get("mutation_results")
    mutations_checked = result.get("mutations_checked")
    mutations_rejected = result.get("mutations_rejected")
    core = {
        key: value
        for key, value in result.items()
        if key not in {"mutation_results", "mutations_checked", "mutations_rejected"}
    }
    validate_core(core)
    expected = build_base_result()
    if core != expected:
        raise FullerCrossingGridGateError("checked result drift")
    if mutation_results is None and mutations_checked is None and mutations_rejected is None:
        return
    if mutation_results is None or mutations_checked is None or mutations_rejected is None:
        raise FullerCrossingGridGateError("mutation field presence drift")
    if isinstance(mutations_checked, bool) or not isinstance(mutations_checked, int):
        raise FullerCrossingGridGateError("mutations_checked drift")
    if isinstance(mutations_rejected, bool) or not isinstance(mutations_rejected, int):
        raise FullerCrossingGridGateError("mutations_rejected drift")
    if not isinstance(mutation_results, list) or len(mutation_results) != len(EXPECTED_MUTATION_NAMES):
        raise FullerCrossingGridGateError("mutation results shape drift")
    for item in mutation_results:
        if not isinstance(item, dict) or set(item) != {"name", "rejected", "error"}:
            raise FullerCrossingGridGateError("mutation result item drift")
        if not isinstance(item["error"], str) or not item["error"]:
            raise FullerCrossingGridGateError("mutation error drift")
    if [item.get("name") for item in mutation_results] != list(EXPECTED_MUTATION_NAMES):
        raise FullerCrossingGridGateError("mutation name drift")
    if not all(item.get("rejected") is True for item in mutation_results):
        raise FullerCrossingGridGateError("mutation rejection drift")
    if mutations_checked != len(EXPECTED_MUTATION_NAMES) or mutations_rejected != len(EXPECTED_MUTATION_NAMES):
        raise FullerCrossingGridGateError("mutation count drift")


def write_json(path: pathlib.Path, result: dict[str, Any]) -> None:
    if path.is_symlink():
        raise FullerCrossingGridGateError(f"refusing to overwrite symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_result(result)
    tmp: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            tmp = pathlib.Path(handle.name)
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        validate_result(json.loads(tmp.read_text(encoding="utf-8")))
        tmp.replace(path)
    except Exception:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise


def tsv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, list):
        return "+".join(value)
    return value


def write_tsv(path: pathlib.Path, result: dict[str, Any]) -> None:
    if path.is_symlink():
        raise FullerCrossingGridGateError(f"refusing to overwrite symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_result(result)
    rows = []
    for row in result["grid_rows"]:
        payload = {column: tsv_value(row[column]) for column in TSV_COLUMNS}
        if payload["missing_reason"] == "":
            payload["missing_reason"] = "proved"
        rows.append(payload)
    expected_rows = [{column: str(value) for column, value in row.items()} for row in rows]
    tmp: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            tmp = pathlib.Path(handle.name)
            writer = csv.DictWriter(
                handle,
                fieldnames=TSV_COLUMNS,
                delimiter="\t",
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        with tmp.open("r", encoding="utf-8", newline="") as handle:
            loaded_rows = list(csv.DictReader(handle, delimiter="\t"))
        if loaded_rows != expected_rows:
            raise FullerCrossingGridGateError("TSV round-trip drift")
        tmp.replace(path)
    except Exception:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    result = build_result()
    if not args.no_write:
        write_json(args.write_json or JSON_OUT, result)
        write_tsv(args.write_tsv or TSV_OUT, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
