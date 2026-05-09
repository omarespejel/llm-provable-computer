#!/usr/bin/env python3
"""Paired-source validation audit for Softmax-table sidecar/fused validators.

This gate answers issue #510 narrowly. It mutates a caller-provided source input
and mirrors the same malformed object into the proof envelope. Validators must
reject that paired malformed source/envelope object instead of accepting it just
because the two copies match.
"""

from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import os
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_air_private_softmax_table_lookup_gate as d8_sidecar
from scripts import zkai_attention_kv_d16_air_private_softmax_table_lookup_gate as d16_sidecar
from scripts import zkai_attention_kv_d16_fused_softmax_table_native_gate as d16_fused
from scripts import zkai_attention_kv_d8_fused_softmax_table_native_gate as d8_fused
from scripts import zkai_attention_kv_eight_head_fused_softmax_table_native_gate as eight_fused
from scripts import zkai_attention_kv_four_head_air_private_softmax_table_lookup_gate as four_sidecar
from scripts import zkai_attention_kv_four_head_fused_softmax_table_native_gate as four_fused
from scripts import zkai_attention_kv_two_head_air_private_softmax_table_lookup_gate as two_sidecar
from scripts import zkai_attention_kv_two_head_fused_softmax_table_native_gate as two_fused
from scripts import zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate as longseq_sidecar
from scripts import zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate as longseq_fused

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.tsv"

SCHEMA = "zkai-attention-kv-softmax-paired-source-validation-audit-v1"
ISSUE = 510
DECISION = "GO_SOFTMAX_TABLE_PAIRED_SOURCE_VALIDATION_AUDIT"
CLAIM_BOUNDARY = (
    "VALIDATOR_API_HARDENING_FOR_MATCHING_MALFORMED_SOFTMAX_TABLE_SOURCE_ENVELOPE_PAIRS_"
    "NOT_NEW_PROOF_NOT_BENCHMARK_NOT_REAL_VALUED_SOFTMAX_NOT_MODEL_ACCURACY_EVIDENCE"
)
MUTATION = "score_rows[0].output_remainder[0] += 1"
TIMING_POLICY = "not_timed_correctness_gate_only"

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_softmax_paired_source_validation_audit_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_softmax_paired_source_validation_audit_gate",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "decision",
    "targets_checked",
    "targets_rejected",
    "accepted_targets",
    "sidecar_targets_checked",
    "fused_targets_checked",
    "mutation",
)


class PairedSourceValidationAuditGateError(ValueError):
    pass


@dataclass(frozen=True)
class Target:
    target_id: str
    route: str
    module: Any
    expected_errors: tuple[type[BaseException], ...]

    @property
    def expected_error_names(self) -> set[str]:
        return {error.__name__ for error in self.expected_errors}


TARGETS = (
    Target(
        "d8_sidecar",
        "sidecar",
        d8_sidecar,
        (d8_sidecar.AttentionKvAirPrivateSoftmaxTableLookupGateError,),
    ),
    Target(
        "two_head_sidecar",
        "sidecar",
        two_sidecar,
        (two_sidecar.AttentionKvAirPrivateSoftmaxTableLookupGateError,),
    ),
    Target(
        "four_head_sidecar",
        "sidecar",
        four_sidecar,
        (four_sidecar.AttentionKvAirPrivateSoftmaxTableLookupGateError,),
    ),
    Target(
        "two_head_longseq_sidecar",
        "sidecar",
        longseq_sidecar,
        (longseq_sidecar.AttentionKvAirPrivateSoftmaxTableLookupGateError,),
    ),
    Target(
        "d16_sidecar",
        "sidecar",
        d16_sidecar,
        (d16_sidecar.AttentionKvAirPrivateSoftmaxTableLookupGateError,),
    ),
    Target("d8_fused", "fused", d8_fused, (d8_fused.AttentionKvD8FusedSoftmaxTableGateError,)),
    Target(
        "two_head_fused",
        "fused",
        two_fused,
        (two_fused.AttentionKvTwoHeadFusedSoftmaxTableGateError,),
    ),
    Target(
        "four_head_fused",
        "fused",
        four_fused,
        (four_fused.AttentionKvFourHeadFusedSoftmaxTableGateError,),
    ),
    Target(
        "eight_head_fused",
        "fused",
        eight_fused,
        (
            eight_fused.AttentionKvEightHeadFusedSoftmaxTableGateError,
            eight_fused.SOURCE_INPUT_MODULE.AttentionKvEightHeadBoundedSoftmaxTableInputError,
        ),
    ),
    Target(
        "two_head_longseq_fused",
        "fused",
        longseq_fused,
        (
            longseq_fused.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError,
            longseq_fused.SOURCE_INPUT_MODULE.AttentionKvTwoHeadLongseqBoundedSoftmaxTableInputError,
        ),
    ),
    Target("d16_fused", "fused", d16_fused, (d16_fused.AttentionKvD16FusedSoftmaxTableGateError,)),
)


def mutate_source(source_input: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(source_input)
    try:
        mutated["score_rows"][0]["output_remainder"][0] += 1
    except (KeyError, IndexError, TypeError) as err:
        raise PairedSourceValidationAuditGateError("source mutation target missing") from err
    return mutated


def run_sidecar_target(target: Target) -> dict[str, Any]:
    module = target.module
    source_input = module.read_bounded_json(module.SOURCE_INPUT_JSON, module.MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    envelope = module.read_bounded_json(
        module.LOOKUP_ENVELOPE_JSON, module.MAX_LOOKUP_ENVELOPE_JSON_BYTES, "lookup envelope"
    )
    mutated_source = mutate_source(source_input)
    mutated_envelope = copy.deepcopy(envelope)
    mutated_envelope["source_input"] = mutated_source
    try:
        module.validate_lookup_envelope(mutated_envelope, mutated_source, module.LOOKUP_ENVELOPE_SIZE_BYTES)
    except target.expected_errors as err:
        return {
            "target_id": target.target_id,
            "route": target.route,
            "rejected": True,
            "error": type(err).__name__,
        }
    except Exception as err:
        raise PairedSourceValidationAuditGateError(
            f"{target.target_id} unexpected exception: {type(err).__name__}: {err}"
        ) from err
    return {
        "target_id": target.target_id,
        "route": target.route,
        "rejected": False,
        "error": "paired malformed source/envelope accepted",
    }


def run_fused_target(target: Target) -> dict[str, Any]:
    module = target.module
    source_input = module.read_bounded_json(module.SOURCE_INPUT_JSON, module.MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    envelope = module.read_bounded_json(module.FUSED_ENVELOPE_JSON, module.MAX_FUSED_ENVELOPE_JSON_BYTES, "fused envelope")
    mutated_source = mutate_source(source_input)
    mutated_envelope = copy.deepcopy(envelope)
    mutated_envelope["source_input"] = mutated_source
    try:
        module.validate_fused_envelope(mutated_envelope, mutated_source, run_native=False)
    except target.expected_errors as err:
        return {
            "target_id": target.target_id,
            "route": target.route,
            "rejected": True,
            "error": type(err).__name__,
        }
    except Exception as err:
        raise PairedSourceValidationAuditGateError(
            f"{target.target_id} unexpected exception: {type(err).__name__}: {err}"
        ) from err
    return {
        "target_id": target.target_id,
        "route": target.route,
        "rejected": False,
        "error": "paired malformed source/envelope accepted",
    }


def run_target(target: Target) -> dict[str, Any]:
    if target.route == "sidecar":
        return run_sidecar_target(target)
    if target.route == "fused":
        return run_fused_target(target)
    raise PairedSourceValidationAuditGateError(f"unknown target route: {target.route}")


def build_result() -> dict[str, Any]:
    target_results = [run_target(target) for target in TARGETS]
    result = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "mutation": MUTATION,
        "timing_policy": TIMING_POLICY,
        "target_results": target_results,
        "targets_checked": len(target_results),
        "targets_rejected": sum(1 for row in target_results if row["rejected"] is True),
        "accepted_targets": [row["target_id"] for row in target_results if row["rejected"] is not True],
        "sidecar_targets_checked": sum(1 for row in target_results if row["route"] == "sidecar"),
        "fused_targets_checked": sum(1 for row in target_results if row["route"] == "fused"),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_result(result)
    return result


def validate_result(result: Any) -> None:
    if not isinstance(result, dict):
        raise PairedSourceValidationAuditGateError("result must be an object")
    expected_keys = {
        "schema",
        "issue",
        "decision",
        "claim_boundary",
        "mutation",
        "timing_policy",
        "target_results",
        "targets_checked",
        "targets_rejected",
        "accepted_targets",
        "sidecar_targets_checked",
        "fused_targets_checked",
        "validation_commands",
    }
    if set(result) != expected_keys:
        raise PairedSourceValidationAuditGateError("result schema drift")
    expected = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "mutation": MUTATION,
        "timing_policy": TIMING_POLICY,
        "targets_checked": len(TARGETS),
        "targets_rejected": len(TARGETS),
        "accepted_targets": [],
        "sidecar_targets_checked": 5,
        "fused_targets_checked": 6,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise PairedSourceValidationAuditGateError(f"result drift for {key}")
    expected_ids = [target.target_id for target in TARGETS]
    target_results = result.get("target_results")
    if not isinstance(target_results, list) or [row.get("target_id") for row in target_results] != expected_ids:
        raise PairedSourceValidationAuditGateError("target result order drift")
    for row, target in zip(target_results, TARGETS, strict=True):
        if set(row) != {"target_id", "route", "rejected", "error"}:
            raise PairedSourceValidationAuditGateError("target result schema drift")
        if row["route"] != target.route:
            raise PairedSourceValidationAuditGateError("target route drift")
        if row["rejected"] is not True:
            raise PairedSourceValidationAuditGateError("paired source mutation accepted")
        if row["error"] not in target.expected_error_names:
            raise PairedSourceValidationAuditGateError("target rejection code drift")


def write_json(path: pathlib.Path, result: dict[str, Any]) -> None:
    validate_result(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(result, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = pathlib.Path(tmp.name)
    os.replace(tmp_path, path)


def to_tsv(result: dict[str, Any]) -> str:
    validate_result(result)
    row = {key: result[key] for key in TSV_COLUMNS}
    row["accepted_targets"] = ",".join(result["accepted_targets"])
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return out.getvalue()


def write_tsv(path: pathlib.Path, result: dict[str, Any]) -> None:
    data = to_tsv(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = pathlib.Path(tmp.name)
    os.replace(tmp_path, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    result = build_result()
    if args.write_json:
        write_json(args.write_json, result)
    if args.write_tsv:
        write_tsv(args.write_tsv, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
