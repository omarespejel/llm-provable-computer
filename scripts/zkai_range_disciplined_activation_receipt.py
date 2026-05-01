#!/usr/bin/env python3
"""Range-disciplined activation receipt probe for zkAI adapters.

This probe turns the JSTprove/Remainder ReLU magnitude finding into a portable
receipt rule: if a backend only clears an activation under a numeric scale/range
discipline, the scale and range contract must be part of the statement receipt.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
JSTPROVE_SHAPE_EVIDENCE = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-jstprove-shape-probe-2026-05.json"
)
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-range-disciplined-activation-receipt-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-range-disciplined-activation-receipt-2026-05.tsv"

SCHEMA = "zkai-range-disciplined-activation-receipt-v1"
RECEIPT_SCHEMA = "zkai-statement-receipt-v1"
DECISION = "GO_RANGE_DISCIPLINE_BOUND_IN_STATEMENT_RECEIPT"
SOURCE_SCHEMA = "zkai-jstprove-shape-probe-v1"
SOURCE_DECISION = "GO_OPERATOR_SUPPORT_SPLIT_NOT_TRANSFORMER_PROOF"
SOURCE_DATE_EPOCH_DEFAULT = 0
EXPECTED_SCALES = ("1", "0.25", "0.1", "0.01", "0.001")
EXPECTED_BASELINE_STATUS = "NO_GO"
EXPECTED_SCALED_STATUS = "GO"
EXPECTED_MUTATION_NAMES = (
    "scale_relabeling",
    "range_contract_relabeling",
    "backend_gate_relabeling",
    "proof_artifact_commitment_relabeling",
    "input_artifact_commitment_relabeling",
    "statement_commitment_relabeling",
    "source_evidence_commitment_relabeling",
)
TSV_COLUMNS = (
    "case_id",
    "scale",
    "backend_status",
    "failure_kind",
    "preactivation_min",
    "preactivation_max",
    "receipt_accepted",
    "mutations_checked",
    "mutations_rejected",
    "statement_commitment",
)


class RangeActivationReceiptError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def _generated_at() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(SOURCE_DATE_EPOCH_DEFAULT))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise RangeActivationReceiptError("SOURCE_DATE_EPOCH must be an integer") from err
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def load_source_evidence(path: pathlib.Path = JSTPROVE_SHAPE_EVIDENCE) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as err:
        raise RangeActivationReceiptError(f"failed to load source evidence {path}: {err}") from err
    validate_source_evidence(payload)
    return payload


def validate_source_evidence(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise RangeActivationReceiptError("source evidence must be an object")
    if payload.get("schema") != SOURCE_SCHEMA:
        raise RangeActivationReceiptError("source evidence schema drift")
    if payload.get("decision") != SOURCE_DECISION:
        raise RangeActivationReceiptError("source evidence decision drift")
    conclusion = payload.get("conclusion")
    if not isinstance(conclusion, dict):
        raise RangeActivationReceiptError("source evidence lacks conclusion")
    if conclusion.get("relu_scaling") != "MAGNITUDE_SENSITIVE_BASELINE_FAILS_SCALED_VARIANTS_CLEAR":
        raise RangeActivationReceiptError("source ReLU scaling conclusion drift")
    rows = payload.get("relu_scaling_probe")
    if not isinstance(rows, list):
        raise RangeActivationReceiptError("source evidence lacks ReLU scaling rows")
    scales = tuple(str(row.get("scale")) for row in rows if isinstance(row, dict))
    if scales != EXPECTED_SCALES:
        raise RangeActivationReceiptError(f"source ReLU scale drift: {scales}")
    for row in rows:
        if not isinstance(row, dict):
            raise RangeActivationReceiptError("source ReLU row must be an object")
        scale = str(row.get("scale"))
        status = row.get("status")
        if scale == "1":
            if status != EXPECTED_BASELINE_STATUS or row.get("failure_kind") != "range_check_capacity":
                raise RangeActivationReceiptError("baseline ReLU range-capacity status drift")
        elif status != EXPECTED_SCALED_STATUS:
            raise RangeActivationReceiptError(f"scaled ReLU status drift at scale {scale}")


def relu_preactivation_bounds(scale_label: str) -> dict[str, str]:
    scale = float(scale_label)
    # This mirrors scripts/zkai_jstprove_shape_probe.py::write_relu_scaled_fixture:
    # input=[1*s, 2*s], weights=[[0.5*s], [1.5*s]], bias=[0.25*s].
    preactivation = 3.5 * scale * scale + 0.25 * scale
    return {
        "min": f"{preactivation:.12g}",
        "max": f"{preactivation:.12g}",
        "derivation": "input=[1*s,2*s], weights=[0.5*s,1.5*s], bias=0.25*s, y=3.5*s^2+0.25*s",
    }


def source_evidence_commitment(source: dict[str, Any]) -> str:
    source_handle = {
        "schema": source["schema"],
        "decision": source["decision"],
        "git_commit": source.get("git_commit"),
        "results_commitment": source.get("results_commitment"),
        "conclusion": {
            "relu_scaling": source["conclusion"]["relu_scaling"],
            "softmax_source_check": source["conclusion"]["softmax_source_check"],
        },
    }
    return blake2b_commitment(source_handle, "ptvm:zkai:jstprove-shape-source-evidence:v1")


def build_receipt(source: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    scale = str(row["scale"])
    range_contract = {
        "operator": "Relu",
        "numeric_contract_version": "range-disciplined-relu-v1",
        "scale": scale,
        "scale_scope": "input_weights_and_bias_scaled_together",
        "preactivation_q": relu_preactivation_bounds(scale),
        "backend_gate": {
            "proof_stack": "JSTprove/Remainder",
            "status": row["status"],
            "failure_kind": row.get("failure_kind") or "",
            "proof_bytes": row.get("proof_bytes"),
        },
    }
    statement = {
        "receipt_version": RECEIPT_SCHEMA,
        "verifier_domain": "ptvm:zkai:range-disciplined-activation:v1",
        "proof_system": "jstprove-remainder",
        "proof_system_version": source["jstprove"]["remainder_dependency_commit"],
        "statement_kind": "range-disciplined-activation-fixture",
        "model_id": f"tiny-gemm-relu-scale-{scale}",
        "model_artifact_commitment": blake2b_commitment(
            {"fixture": "tiny_gemm_relu", "scale": scale, "model_bytes": row.get("model_bytes")},
            "ptvm:zkai:range-activation-model:v1",
        ),
        "input_commitment": blake2b_commitment(
            {"fixture": "tiny_gemm_relu", "scale": scale, "input": [scale, f"2*{scale}"]},
            "ptvm:zkai:range-activation-input:v1",
        ),
        "output_commitment": blake2b_commitment(
            {"fixture": "tiny_gemm_relu", "scale": scale, "relu_preactivation": range_contract["preactivation_q"]},
            "ptvm:zkai:range-activation-output:v1",
        ),
        "config_commitment": blake2b_commitment(
            {"range_contract": range_contract},
            "ptvm:zkai:range-activation-config:v1",
        ),
        "public_instance_commitment": blake2b_commitment(
            {"backend_status": row["status"], "failure_kind": row.get("failure_kind") or "", "scale": scale},
            "ptvm:zkai:range-activation-public-instance:v1",
        ),
        "proof_commitment": blake2b_commitment(
            {"proof_bytes": row.get("proof_bytes"), "backend_status": row["status"], "scale": scale},
            "ptvm:zkai:range-activation-proof:v1",
        ),
        "verifying_key_commitment": "not-applicable:jstprove-source-backed-shape-probe",
        "setup_commitment": "not-applicable:jstprove-source-backed-shape-probe",
        "evidence_manifest_commitment": source_evidence_commitment(source),
        "range_contract": range_contract,
    }
    statement["statement_commitment"] = blake2b_commitment(
        {key: value for key, value in statement.items() if key != "statement_commitment"},
        "ptvm:zkai:range-activation-statement:v1",
    )
    return statement


def verify_receipt(receipt: dict[str, Any], source: dict[str, Any]) -> bool:
    required = {
        "receipt_version",
        "verifier_domain",
        "proof_system",
        "proof_system_version",
        "statement_kind",
        "model_id",
        "model_artifact_commitment",
        "input_commitment",
        "output_commitment",
        "config_commitment",
        "public_instance_commitment",
        "proof_commitment",
        "verifying_key_commitment",
        "setup_commitment",
        "evidence_manifest_commitment",
        "range_contract",
        "statement_commitment",
    }
    if set(receipt) != required:
        raise RangeActivationReceiptError("receipt field set mismatch")
    if receipt["receipt_version"] != RECEIPT_SCHEMA:
        raise RangeActivationReceiptError("receipt version drift")
    if receipt["verifier_domain"] != "ptvm:zkai:range-disciplined-activation:v1":
        raise RangeActivationReceiptError("verifier domain drift")
    if receipt["proof_system_version"] != source["jstprove"]["remainder_dependency_commit"]:
        raise RangeActivationReceiptError("proof-system version drift")
    if receipt["evidence_manifest_commitment"] != source_evidence_commitment(source):
        raise RangeActivationReceiptError("source evidence commitment drift")
    scale = str(receipt["range_contract"].get("scale"))
    source_rows = {str(row["scale"]): row for row in source["relu_scaling_probe"]}
    if scale not in source_rows:
        raise RangeActivationReceiptError("range scale is not backed by source evidence")
    expected = build_receipt(source, source_rows[scale])
    if receipt != expected:
        for field in sorted(required):
            if receipt.get(field) != expected[field]:
                raise RangeActivationReceiptError(f"receipt field drift: {field}")
        raise RangeActivationReceiptError("receipt drift")
    return True


def mutate_path(value: dict[str, Any], path: tuple[str, ...], replacement: Any) -> dict[str, Any]:
    out = copy.deepcopy(value)
    cursor: Any = out
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement
    return out


def mutation_cases(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    wrong_commitment = "blake2b-256:" + "55" * 32
    cases = {
        "scale_relabeling": mutate_path(receipt, ("range_contract", "scale"), "0.333"),
        "range_contract_relabeling": mutate_path(
            receipt, ("range_contract", "preactivation_q", "max"), "999"
        ),
        "backend_gate_relabeling": mutate_path(
            receipt,
            ("range_contract", "backend_gate", "status"),
            "NO_GO" if receipt["range_contract"]["backend_gate"]["status"] == "GO" else "GO",
        ),
        "proof_artifact_commitment_relabeling": mutate_path(receipt, ("proof_commitment",), wrong_commitment),
        "input_artifact_commitment_relabeling": mutate_path(receipt, ("input_commitment",), wrong_commitment),
        "statement_commitment_relabeling": mutate_path(receipt, ("statement_commitment",), wrong_commitment),
        "source_evidence_commitment_relabeling": mutate_path(
            receipt, ("evidence_manifest_commitment",), wrong_commitment
        ),
    }
    if tuple(sorted(cases)) != tuple(sorted(EXPECTED_MUTATION_NAMES)):
        raise RangeActivationReceiptError("mutation corpus drift")
    return cases


def run_case(source: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    receipt = build_receipt(source, row)
    baseline_accepted = verify_receipt(receipt, source)
    mutations = []
    for name, mutated in mutation_cases(receipt).items():
        try:
            verify_receipt(mutated, source)
        except RangeActivationReceiptError as err:
            mutations.append({"name": name, "rejected": True, "reason": str(err)})
        else:
            mutations.append({"name": name, "rejected": False, "reason": "accepted"})
    rejected = sum(1 for item in mutations if item["rejected"])
    return {
        "case_id": f"tiny_gemm_relu_scale_{row['scale']}",
        "scale": str(row["scale"]),
        "backend_status": row["status"],
        "failure_kind": row.get("failure_kind") or "",
        "range_contract": receipt["range_contract"],
        "receipt": receipt,
        "receipt_accepted": baseline_accepted,
        "mutations_checked": len(mutations),
        "mutations_rejected": rejected,
        "all_mutations_rejected": rejected == len(mutations),
        "mutation_cases": mutations,
    }


def build_payload(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = load_source_evidence() if source is None else source
    validate_source_evidence(source)
    cases = [run_case(source, row) for row in source["relu_scaling_probe"]]
    if len(cases) != len(EXPECTED_SCALES):
        raise RangeActivationReceiptError("case count drift")
    if not all(case["receipt_accepted"] and case["all_mutations_rejected"] for case in cases):
        raise RangeActivationReceiptError("range receipt mutation suite did not pass")
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "generated_at": _generated_at(),
        "git_commit": os.environ.get("ZKAI_RANGE_ACTIVATION_GIT_COMMIT", _git_commit()),
        "question": (
            "Can the JSTprove ReLU magnitude-sensitivity result be carried as an explicit "
            "range contract in a statement receipt?"
        ),
        "source_evidence": {
            "path": str(JSTPROVE_SHAPE_EVIDENCE.relative_to(ROOT)),
            "schema": source["schema"],
            "decision": source["decision"],
            "git_commit": source.get("git_commit"),
            "results_commitment": source.get("results_commitment"),
            "evidence_manifest_commitment": source_evidence_commitment(source),
        },
        "cases": cases,
        "summary": {
            "baseline_scale_status": cases[0]["backend_status"],
            "scaled_go_count": sum(1 for case in cases[1:] if case["backend_status"] == "GO"),
            "case_count": len(cases),
            "mutations_checked": sum(case["mutations_checked"] for case in cases),
            "mutations_rejected": sum(case["mutations_rejected"] for case in cases),
            "all_receipts_fail_closed": all(case["all_mutations_rejected"] for case in cases),
            "interpretation": (
                "ReLU acceptance is magnitude-sensitive in the checked JSTprove probe, so scale/range "
                "assumptions are verifier-relevant statement data, not benchmark metadata."
            ),
        },
        "non_claims": [
            "not a new proof benchmark",
            "not a transformer proof",
            "not a JSTprove security finding",
            "not evidence that ReLU is solved at large model scale",
            "not a Stwo AIR result",
        ],
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise RangeActivationReceiptError("payload must be an object")
    if payload.get("schema") != SCHEMA:
        raise RangeActivationReceiptError("schema drift")
    if payload.get("decision") != DECISION:
        raise RangeActivationReceiptError("decision drift")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED_SCALES):
        raise RangeActivationReceiptError("case corpus drift")
    if tuple(str(case.get("scale")) for case in cases) != EXPECTED_SCALES:
        raise RangeActivationReceiptError("scale order drift")
    for case in cases:
        if not case.get("receipt_accepted"):
            raise RangeActivationReceiptError("baseline receipt was not accepted")
        if case.get("mutations_checked") != len(EXPECTED_MUTATION_NAMES):
            raise RangeActivationReceiptError("mutation count drift")
        if case.get("mutations_rejected") != len(EXPECTED_MUTATION_NAMES):
            raise RangeActivationReceiptError("mutation rejection drift")
    summary = payload.get("summary")
    if not isinstance(summary, dict) or not summary.get("all_receipts_fail_closed"):
        raise RangeActivationReceiptError("summary fail-closed bit drift")


def to_tsv(payload: dict[str, Any]) -> str:
    out = []
    writer = csv.DictWriter(_ListWriter(out), fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for case in payload["cases"]:
        writer.writerow(
            {
                "case_id": case["case_id"],
                "scale": case["scale"],
                "backend_status": case["backend_status"],
                "failure_kind": case["failure_kind"],
                "preactivation_min": case["range_contract"]["preactivation_q"]["min"],
                "preactivation_max": case["range_contract"]["preactivation_q"]["max"],
                "receipt_accepted": str(case["receipt_accepted"]).lower(),
                "mutations_checked": case["mutations_checked"],
                "mutations_rejected": case["mutations_rejected"],
                "statement_commitment": case["receipt"]["statement_commitment"],
            }
        )
    return "".join(out)


class _ListWriter:
    def __init__(self, rows: list[str]) -> None:
        self.rows = rows

    def write(self, value: str) -> int:
        self.rows.append(value)
        return len(value)


def write_outputs(payload: dict[str, Any], json_out: pathlib.Path, tsv_out: pathlib.Path) -> None:
    validate_payload(payload)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    tsv_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tsv_out.write_text(to_tsv(payload), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    parser.add_argument("--no-write", action="store_true", help="do not write checked outputs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.no_write:
        write_outputs(payload, args.write_json, args.write_tsv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
