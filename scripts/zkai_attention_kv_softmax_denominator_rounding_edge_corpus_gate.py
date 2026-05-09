#!/usr/bin/env python3
"""Checked denominator/rounding edge corpus for bounded Softmax-table receipts.

This gate answers issue #507 narrowly.  It does not create a new Stwo proof and
does not widen the Softmax claim.  It records deterministic arithmetic fixtures
for denominator and floor-division edge behavior, then checks that the existing
d16 source, LogUp sidecar, and fused receipt validators reject denominator /
rounding drift even when the caller presents a matching mutated source object.
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
import sys
import tempfile
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_d16_air_private_softmax_table_lookup_gate as sidecar_gate
from scripts import zkai_attention_kv_d16_bounded_softmax_table_native_gate as source_gate
from scripts import zkai_attention_kv_d16_fused_softmax_table_native_gate as fused_gate
from scripts import zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input as source_input

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.tsv"

SCHEMA = "zkai-attention-kv-softmax-denominator-rounding-edge-corpus-v1"
ISSUE = 507
SOURCE_ISSUE = 501
DECISION = "GO_SOFTMAX_TABLE_DENOMINATOR_ROUNDING_EDGE_CORPUS"
CLAIM_BOUNDARY = (
    "DETERMINISTIC_CORPUS_FOR_BOUNDED_INTEGER_SOFTMAX_TABLE_DENOMINATORS_AND_FLOOR_DIVISION_"
    "NOT_REAL_VALUED_SOFTMAX_NOT_NEW_PROOF_NOT_MODEL_ACCURACY_EVIDENCE"
)
TIMING_POLICY = "not_timed_correctness_gate_only"
WEIGHT_POLICY = source_input.WEIGHT_POLICY
SCORE_GAP_CLIP = source_input.SCORE_GAP_CLIP
KEY_WIDTH = source_input.KEY_WIDTH
VALUE_WIDTH = source_input.VALUE_WIDTH

EDGE_CASE_NAMES = (
    "single_allowed_candidate_min_denominator",
    "all_scores_equal",
    "all_nonmax_scores_clipped",
    "one_dominant_key_all_others_clipped",
    "negative_numerator_floor_division",
    "mixed_remainder_extremes",
    "table_entry_multiplicity_extremes",
)

ROUTE_MUTATION_NAMES = (
    "source_denominator_zero",
    "source_remainder_equal_denominator",
    "source_negative_remainder",
    "sidecar_matching_source_denominator_zero",
    "sidecar_matching_source_remainder_equal_denominator",
    "sidecar_matching_source_negative_remainder",
    "fused_matching_source_denominator_zero",
    "fused_matching_source_remainder_equal_denominator",
    "fused_matching_source_negative_remainder",
)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate scripts.tests.test_zkai_attention_kv_d16_air_private_softmax_table_lookup_gate scripts.tests.test_zkai_attention_kv_d16_fused_softmax_table_native_gate",
    "python3 scripts/zkai_attention_kv_d16_quantized_softmax_receipt_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "decision",
    "edge_cases",
    "route_mutations",
    "route_mutations_rejected",
    "min_denominator",
    "max_denominator",
    "max_remainder_ratio",
    "negative_numerator_cases",
    "all_scores_equal_denominator",
    "all_clipped_denominator",
    "dominant_denominator",
)


class SoftmaxEdgeCorpusGateError(ValueError):
    pass


def vector(first: int, width: int = KEY_WIDTH) -> list[int]:
    return [first, *([0] * (width - 1))]


def value_vector(first: int, second: int = 0, width: int = VALUE_WIDTH) -> list[int]:
    return [first, second, *([0] * (width - 2))]


def kv(position: int, score: int, value_first: int, value_second: int = 0) -> dict[str, Any]:
    return {"position": position, "key": vector(score), "value": value_vector(value_first, value_second)}


def step(token_position: int, score: int, value_first: int, value_second: int = 0) -> dict[str, Any]:
    return {
        "token_position": token_position,
        "query": vector(1),
        "new_key": vector(score),
        "new_value": value_vector(value_first, value_second),
    }


def edge_fixture(name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if name == "single_allowed_candidate_min_denominator":
        return [], [step(0, 7, 5, -3)]
    if name == "all_scores_equal":
        return [kv(0, 3, 2), kv(1, 3, 5)], [step(2, 3, 8)]
    if name == "all_nonmax_scores_clipped":
        return [kv(0, 0, 20), kv(1, -8, -5), kv(2, -17, 4)], [step(3, -20, 1)]
    if name == "one_dominant_key_all_others_clipped":
        return [kv(0, 40, 9), kv(1, 0, -7), kv(2, -12, 3)], [step(3, -21, 5)]
    if name == "negative_numerator_floor_division":
        return [kv(0, 3, -5), kv(1, 3, -2)], [step(2, 3, 1)]
    if name == "mixed_remainder_extremes":
        return [kv(0, 5, 1, -7), kv(1, 1, 9, 4), kv(2, -3, -6, 11)], [step(3, 4, 5, -2)]
    if name == "table_entry_multiplicity_extremes":
        return [
            kv(0, 32, 1),
            kv(1, 31, 2),
            kv(2, 30, 3),
            kv(3, 29, 4),
            kv(4, 28, 5),
            kv(5, 27, 6),
            kv(6, 26, 7),
            kv(7, 25, 8),
            kv(8, 24, 9),
        ], [step(9, 24, 10)]
    raise SoftmaxEdgeCorpusGateError(f"unknown edge case: {name}")


def weight_table() -> dict[int, int]:
    return {entry["gap"]: entry["weight"] for entry in source_input.WEIGHT_TABLE}


def summarize_edge_case(name: str) -> dict[str, Any]:
    initial, steps = edge_fixture(name)
    rows, final_cache, outputs = source_input.build_score_rows(initial, steps)
    if len(steps) != 1:
        raise SoftmaxEdgeCorpusGateError("edge fixtures must use exactly one step")
    if not rows:
        raise SoftmaxEdgeCorpusGateError(f"{name} produced no score rows")
    table = weight_table()
    denominator = sum(row["attention_weight"] for row in rows)
    if denominator <= 0:
        raise SoftmaxEdgeCorpusGateError(f"{name} produced nonpositive denominator")
    numerators = [0] * VALUE_WIDTH
    for row in rows:
        expected_gap = row["selected_score"] - row["score"]
        if row["score_gap"] != expected_gap:
            raise SoftmaxEdgeCorpusGateError(f"{name} score-gap drift")
        clipped_gap = min(row["score_gap"], SCORE_GAP_CLIP)
        if row["attention_weight"] != table[clipped_gap]:
            raise SoftmaxEdgeCorpusGateError(f"{name} table weight drift")
        if row["weight_denominator"] != denominator:
            raise SoftmaxEdgeCorpusGateError(f"{name} denominator row drift")
        for dim, value in enumerate(row["value"]):
            numerators[dim] += row["attention_weight"] * value
    output = [numerator // denominator for numerator in numerators]
    remainders = [numerator - quotient * denominator for numerator, quotient in zip(numerators, output, strict=True)]
    if outputs != [output]:
        raise SoftmaxEdgeCorpusGateError(f"{name} output drift")
    if final_cache[-1]["position"] != steps[0]["token_position"]:
        raise SoftmaxEdgeCorpusGateError(f"{name} final KV append drift")
    for row in rows:
        if row["weighted_numerator"] != numerators:
            raise SoftmaxEdgeCorpusGateError(f"{name} weighted numerator drift")
        if row["attention_output"] != output:
            raise SoftmaxEdgeCorpusGateError(f"{name} row output drift")
        if row["output_remainder"] != remainders:
            raise SoftmaxEdgeCorpusGateError(f"{name} row remainder drift")
    for numerator, quotient, remainder in zip(numerators, output, remainders, strict=True):
        if numerator != quotient * denominator + remainder:
            raise SoftmaxEdgeCorpusGateError(f"{name} quotient/remainder identity drift")
        if not 0 <= remainder < denominator:
            raise SoftmaxEdgeCorpusGateError(f"{name} remainder outside Euclidean bound")
    clipped_gaps = [min(row["score_gap"], SCORE_GAP_CLIP) for row in rows]
    multiplicities = Counter(clipped_gaps)
    return {
        "name": name,
        "candidate_count": len(rows),
        "scores": [row["score"] for row in rows],
        "score_gaps": [row["score_gap"] for row in rows],
        "clipped_gaps": clipped_gaps,
        "weights": [row["attention_weight"] for row in rows],
        "denominator": denominator,
        "numerators": numerators,
        "outputs": output,
        "remainders": remainders,
        "negative_numerator_dimensions": sum(1 for numerator in numerators if numerator < 0),
        "max_remainder_ratio": max((remainder / denominator for remainder in remainders), default=0.0),
        "table_multiplicities": [
            {"gap": gap, "weight": table[gap], "multiplicity": multiplicities.get(gap, 0)}
            for gap in range(SCORE_GAP_CLIP + 1)
        ],
    }


def load_source_artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_payload = source_gate.read_bounded_json(
        source_gate.INPUT_JSON, source_gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input"
    )
    source_envelope = source_gate.read_bounded_json(
        source_gate.ENVELOPE_JSON, source_gate.MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope"
    )
    sidecar_envelope = sidecar_gate.read_bounded_json(
        sidecar_gate.LOOKUP_ENVELOPE_JSON,
        sidecar_gate.MAX_LOOKUP_ENVELOPE_JSON_BYTES,
        "lookup sidecar envelope",
    )
    fused_envelope = fused_gate.read_bounded_json(
        fused_gate.FUSED_ENVELOPE_JSON,
        fused_gate.MAX_FUSED_ENVELOPE_JSON_BYTES,
        "fused envelope",
    )
    return source_payload, source_envelope, sidecar_envelope, fused_envelope


def strip_route_error(error: Exception) -> str:
    message = str(error)
    return message if len(message) <= 240 else message[:237] + "..."


def mutate_source_denominator_zero(source_payload: dict[str, Any]) -> None:
    source_payload["score_rows"][0]["weight_denominator"] = 0


def mutate_source_remainder_equal_denominator(source_payload: dict[str, Any]) -> None:
    source_payload["score_rows"][0]["output_remainder"][0] = source_payload["score_rows"][0]["weight_denominator"]


def mutate_source_negative_remainder(source_payload: dict[str, Any]) -> None:
    source_payload["score_rows"][0]["output_remainder"][0] = -1


def route_rejection_results() -> list[dict[str, Any]]:
    try:
        source_payload, source_envelope, sidecar_envelope, fused_envelope = load_source_artifacts()
        source_gate.validate_source_pair(source_payload, source_envelope)
        sidecar_gate.validate_lookup_envelope(
            sidecar_envelope,
            source_payload,
            sidecar_gate.LOOKUP_ENVELOPE_SIZE_BYTES,
        )
        fused_gate.validate_fused_envelope(fused_envelope, source_payload, run_native=False)
    except Exception as err:
        raise SoftmaxEdgeCorpusGateError(f"pristine artifact validation drift: {err}") from err
    results: list[dict[str, Any]] = []

    def record(name: str, route: str, check) -> None:
        try:
            check()
        except (
            source_gate.AttentionKvBoundedSoftmaxTableNativeGateError,
            sidecar_gate.AttentionKvAirPrivateSoftmaxTableLookupGateError,
            fused_gate.AttentionKvD16FusedSoftmaxTableGateError,
        ) as err:
            results.append({"name": name, "route": route, "rejected": True, "error": type(err).__name__})
        else:
            results.append({"name": name, "route": route, "rejected": False, "error": "mutation accepted"})

    mutated_source = copy.deepcopy(source_payload)
    mutated_source_envelope = copy.deepcopy(source_envelope)
    mutate_source_denominator_zero(mutated_source)
    mutated_source_envelope["input"] = mutated_source
    record(
        "source_denominator_zero",
        "source",
        lambda: source_gate.validate_source_pair(mutated_source, mutated_source_envelope),
    )

    mutated_source = copy.deepcopy(source_payload)
    mutated_source_envelope = copy.deepcopy(source_envelope)
    mutate_source_remainder_equal_denominator(mutated_source)
    mutated_source_envelope["input"] = mutated_source
    record(
        "source_remainder_equal_denominator",
        "source",
        lambda: source_gate.validate_source_pair(mutated_source, mutated_source_envelope),
    )

    mutated_source = copy.deepcopy(source_payload)
    mutated_source_envelope = copy.deepcopy(source_envelope)
    mutate_source_negative_remainder(mutated_source)
    mutated_source_envelope["input"] = mutated_source
    record(
        "source_negative_remainder",
        "source",
        lambda: source_gate.validate_source_pair(mutated_source, mutated_source_envelope),
    )

    mutated_source = copy.deepcopy(source_payload)
    mutated_sidecar = copy.deepcopy(sidecar_envelope)
    mutate_source_denominator_zero(mutated_source)
    mutated_sidecar["source_input"] = mutated_source
    record(
        "sidecar_matching_source_denominator_zero",
        "sidecar",
        lambda: sidecar_gate.validate_lookup_envelope(
            mutated_sidecar, mutated_source, sidecar_gate.LOOKUP_ENVELOPE_SIZE_BYTES
        ),
    )

    mutated_source = copy.deepcopy(source_payload)
    mutated_sidecar = copy.deepcopy(sidecar_envelope)
    mutate_source_remainder_equal_denominator(mutated_source)
    mutated_sidecar["source_input"] = mutated_source
    record(
        "sidecar_matching_source_remainder_equal_denominator",
        "sidecar",
        lambda: sidecar_gate.validate_lookup_envelope(
            mutated_sidecar, mutated_source, sidecar_gate.LOOKUP_ENVELOPE_SIZE_BYTES
        ),
    )

    mutated_source = copy.deepcopy(source_payload)
    mutated_sidecar = copy.deepcopy(sidecar_envelope)
    mutate_source_negative_remainder(mutated_source)
    mutated_sidecar["source_input"] = mutated_source
    record(
        "sidecar_matching_source_negative_remainder",
        "sidecar",
        lambda: sidecar_gate.validate_lookup_envelope(
            mutated_sidecar, mutated_source, sidecar_gate.LOOKUP_ENVELOPE_SIZE_BYTES
        ),
    )

    mutated_source = copy.deepcopy(source_payload)
    mutated_fused = copy.deepcopy(fused_envelope)
    mutate_source_denominator_zero(mutated_source)
    mutated_fused["source_input"] = mutated_source
    record(
        "fused_matching_source_denominator_zero",
        "fused",
        lambda: fused_gate.validate_fused_envelope(mutated_fused, mutated_source, run_native=False),
    )

    mutated_source = copy.deepcopy(source_payload)
    mutated_fused = copy.deepcopy(fused_envelope)
    mutate_source_remainder_equal_denominator(mutated_source)
    mutated_fused["source_input"] = mutated_source
    record(
        "fused_matching_source_remainder_equal_denominator",
        "fused",
        lambda: fused_gate.validate_fused_envelope(mutated_fused, mutated_source, run_native=False),
    )

    mutated_source = copy.deepcopy(source_payload)
    mutated_fused = copy.deepcopy(fused_envelope)
    mutate_source_negative_remainder(mutated_source)
    mutated_fused["source_input"] = mutated_source
    record(
        "fused_matching_source_negative_remainder",
        "fused",
        lambda: fused_gate.validate_fused_envelope(mutated_fused, mutated_source, run_native=False),
    )

    if tuple(result["name"] for result in results) != ROUTE_MUTATION_NAMES:
        raise SoftmaxEdgeCorpusGateError("route mutation order drift")
    if not all(result["rejected"] is True for result in results):
        raise SoftmaxEdgeCorpusGateError("route mutation accepted")
    return results


def build_result() -> dict[str, Any]:
    cases = [summarize_edge_case(name) for name in EDGE_CASE_NAMES]
    route_results = route_rejection_results()
    denominators = [case["denominator"] for case in cases]
    max_remainder_ratio = max(case["max_remainder_ratio"] for case in cases)
    result = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "timing_policy": TIMING_POLICY,
        "weight_policy": WEIGHT_POLICY,
        "score_gap_clip": SCORE_GAP_CLIP,
        "edge_cases": cases,
        "route_mutation_results": route_results,
        "edge_case_count": len(cases),
        "route_mutations_checked": len(route_results),
        "route_mutations_rejected": sum(1 for result in route_results if result["rejected"]),
        "min_denominator": min(denominators),
        "max_denominator": max(denominators),
        "max_remainder_ratio": max_remainder_ratio,
        "negative_numerator_cases": [
            case["name"] for case in cases if case["negative_numerator_dimensions"] > 0
        ],
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_result(result)
    return result


def validate_result(result: Any) -> None:
    if not isinstance(result, dict):
        raise SoftmaxEdgeCorpusGateError("result must be an object")
    expected = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "timing_policy": TIMING_POLICY,
        "weight_policy": WEIGHT_POLICY,
        "score_gap_clip": SCORE_GAP_CLIP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    allowed = set(expected) | {
        "edge_cases",
        "route_mutation_results",
        "edge_case_count",
        "route_mutations_checked",
        "route_mutations_rejected",
        "min_denominator",
        "max_denominator",
        "max_remainder_ratio",
        "negative_numerator_cases",
    }
    if set(result) != allowed:
        raise SoftmaxEdgeCorpusGateError("result schema drift")
    for key, expected_value in expected.items():
        if result.get(key) != expected_value:
            raise SoftmaxEdgeCorpusGateError(f"result drift for {key}")
    expected_cases = [summarize_edge_case(name) for name in EDGE_CASE_NAMES]
    if result.get("edge_cases") != expected_cases:
        raise SoftmaxEdgeCorpusGateError("edge case corpus drift")
    expected_route_results = route_rejection_results()
    if result.get("route_mutation_results") != expected_route_results:
        raise SoftmaxEdgeCorpusGateError("route mutation result drift")
    if result.get("edge_case_count") != len(EDGE_CASE_NAMES):
        raise SoftmaxEdgeCorpusGateError("edge case count drift")
    if result.get("route_mutations_checked") != len(ROUTE_MUTATION_NAMES):
        raise SoftmaxEdgeCorpusGateError("route mutation count drift")
    if result.get("route_mutations_rejected") != len(ROUTE_MUTATION_NAMES):
        raise SoftmaxEdgeCorpusGateError("route mutation rejection drift")
    denominators = [case["denominator"] for case in expected_cases]
    expected_max_remainder_ratio = max(case["max_remainder_ratio"] for case in expected_cases)
    if result.get("min_denominator") != min(denominators):
        raise SoftmaxEdgeCorpusGateError("min denominator drift")
    if result.get("max_denominator") != max(denominators):
        raise SoftmaxEdgeCorpusGateError("max denominator drift")
    actual_max_remainder_ratio = result.get("max_remainder_ratio")
    if not isinstance(actual_max_remainder_ratio, (int, float)) or not math.isclose(
        float(actual_max_remainder_ratio),
        expected_max_remainder_ratio,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise SoftmaxEdgeCorpusGateError("max remainder ratio drift")
    if result.get("negative_numerator_cases") != [
        case["name"] for case in expected_cases if case["negative_numerator_dimensions"] > 0
    ]:
        raise SoftmaxEdgeCorpusGateError("negative numerator case drift")


def to_tsv(result: dict[str, Any]) -> str:
    validate_result(result)
    by_name = {case["name"]: case for case in result["edge_cases"]}
    row = {
        "decision": result["decision"],
        "edge_cases": result["edge_case_count"],
        "route_mutations": result["route_mutations_checked"],
        "route_mutations_rejected": result["route_mutations_rejected"],
        "min_denominator": result["min_denominator"],
        "max_denominator": result["max_denominator"],
        "max_remainder_ratio": f"{result['max_remainder_ratio']:.6f}",
        "negative_numerator_cases": ",".join(result["negative_numerator_cases"]),
        "all_scores_equal_denominator": by_name["all_scores_equal"]["denominator"],
        "all_clipped_denominator": by_name["all_nonmax_scores_clipped"]["denominator"],
        "dominant_denominator": by_name["one_dominant_key_all_others_clipped"]["denominator"],
    }
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return buf.getvalue()


def atomic_write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = pathlib.Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise


def write_json(path: pathlib.Path, result: dict[str, Any]) -> None:
    validate_result(result)
    atomic_write_text(path, json.dumps(result, indent=2, sort_keys=True) + "\n")


def write_tsv(path: pathlib.Path, result: dict[str, Any]) -> None:
    atomic_write_text(path, to_tsv(result))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    result = build_result()
    write_json(args.write_json, result)
    write_tsv(args.write_tsv, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
