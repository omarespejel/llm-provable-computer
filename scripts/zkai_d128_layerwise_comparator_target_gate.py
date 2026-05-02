#!/usr/bin/env python3
"""Gate a d128 layerwise receipt comparator target without claiming a d128 proof.

The gate consumes the existing matched d64/d128 target-shape probe, the
DeepProve/NANOZK public-adapter feasibility probe, and the source-backed
published zkML numbers table. It produces a target-spec GO plus a proof-artifact
NO-GO: the d128 receipt shape is ready to compare against public layerwise zkML
context, but this repository does not yet contain a local d128 proof artifact.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
PAPER_EVIDENCE_DIR = ROOT / "docs" / "paper" / "evidence"
MATCHED_SCRIPT = ROOT / "scripts" / "zkai_matched_rmsnorm_swiglu_block_feasibility.py"
EXTERNAL_SCRIPT = ROOT / "scripts" / "zkai_deepprove_nanozk_adapter_feasibility.py"
MATCHED_EVIDENCE = EVIDENCE_DIR / "zkai-matched-rmsnorm-swiglu-block-feasibility-2026-05.json"
EXTERNAL_EVIDENCE = EVIDENCE_DIR / "zkai-deepprove-nanozk-adapter-feasibility-2026-05.json"
PUBLISHED_ZKML_NUMBERS = PAPER_EVIDENCE_DIR / "published-zkml-numbers-2026-04.tsv"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.tsv"

SCHEMA = "zkai-d128-layerwise-comparator-target-v1"
DECISION = "NO_GO_D128_LAYERWISE_PROOF_ARTIFACT_MISSING"
RESULT = "BOUNDED_NO_GO"
TARGET_RESULT = "GO_D128_LAYERWISE_COMPARATOR_TARGET_SPEC"
LOCAL_PROOF_RESULT = "NO_GO_LOCAL_D128_PROOF_ARTIFACT_MISSING"
SOURCE_CONTEXT_RESULT = "GO_SOURCE_BACKED_PUBLIC_LAYERWISE_CONTEXT"
EXTERNAL_ADAPTER_RESULT = "NO_GO_PUBLIC_RELABELING_ADAPTER_BENCHMARK"
TARGET_WIDTH = 128
TARGET_DOMAIN = "ptvm:zkai:d128-layerwise-comparator-target:v1"
D128_SCALE_DECISION = "NO_GO_CURRENT_STWO_SURFACE_FOR_D128_PROOF_GO_TARGET_SPEC_ONLY"
FIRST_BLOCKER = (
    "the d128 RMSNorm-SwiGLU-residual receipt target is pinned, but the repository "
    "does not contain a local d128 proof artifact, verifier handle, or relabeling suite"
)

NON_CLAIMS = [
    "not a local d128 proof result",
    "not a matched NANOZK benchmark",
    "not a DeepProve-1 adapter benchmark",
    "not evidence that NANOZK or DeepProve-1 are insecure",
    "not full transformer inference",
    "not proof-size or verifier-time evidence for this repository",
]

VALIDATION_COMMANDS = [
    "just gate-fast",
    "python3 scripts/zkai_d128_layerwise_comparator_target_gate.py --write-json docs/engineering/evidence/zkai-d128-layerwise-comparator-target-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-layerwise-comparator-target-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_layerwise_comparator_target_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate",
]

TSV_COLUMNS = (
    "surface",
    "status",
    "width",
    "source",
    "prove_seconds",
    "verify_seconds",
    "proof_size_reported",
    "claim_boundary",
    "blocker",
)

MUTATION_TSV_COLUMNS = (
    "mutation",
    "surface",
    "baseline_result",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
)

EXPECTED_MUTATION_INVENTORY = (
    ("matched_source_file_hash_drift", "source_evidence"),
    ("external_source_payload_hash_drift", "source_evidence"),
    ("target_width_drift", "target_spec"),
    ("target_binding_removed", "target_spec"),
    ("target_linear_mul_estimate_drift", "target_spec"),
    ("target_residual_row_count_drift", "target_spec"),
    ("target_scale_decision_promoted_to_go", "target_spec"),
    ("target_d64_slice_generalization_overclaim", "target_spec"),
    ("target_commitment_drift", "target_spec"),
    ("local_proof_result_changed_to_go", "local_proof_status"),
    ("local_proof_size_metric_smuggled", "local_proof_status"),
    ("local_verify_time_metric_smuggled", "local_proof_status"),
    ("nanozk_source_row_verify_seconds_drift", "source_context"),
    ("nanozk_source_context_promoted_to_matched", "source_context"),
    ("external_adapter_result_changed_to_go", "external_adapter_status"),
    ("deepprove_public_artifact_overclaim", "external_adapter_status"),
    ("nanozk_public_verifier_overclaim", "external_adapter_status"),
    ("non_claim_removed", "claim_boundary"),
    ("result_changed_to_go", "parser_or_schema"),
)


class D128ComparatorTargetError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128ComparatorTargetError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


MATCHED = _load_module(MATCHED_SCRIPT, "zkai_matched_rmsnorm_swiglu_for_d128_target")
EXTERNAL = _load_module(EXTERNAL_SCRIPT, "zkai_deepprove_nanozk_for_d128_target")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_hex_json(value: Any) -> str:
    return sha256_hex_bytes(canonical_json_bytes(value))


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: pathlib.Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def expect_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise D128ComparatorTargetError(f"{field} mismatch")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128ComparatorTargetError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D128ComparatorTargetError(f"{field} must be a list")
    return value


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def load_json(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise D128ComparatorTargetError(f"source evidence is not a regular file: {path}")
    if ROOT.resolve() not in resolved.parents:
        raise D128ComparatorTargetError(f"source evidence path escapes repository: {path}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128ComparatorTargetError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D128ComparatorTargetError(f"source evidence must be a JSON object: {path}")
    return payload


def source_descriptor(path: pathlib.Path, payload: dict[str, Any], *, include_schema: bool = False, include_decision: bool = False) -> dict[str, Any]:
    descriptor = {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(payload),
    }
    if include_schema:
        descriptor["schema"] = payload.get("schema")
    if include_decision:
        descriptor["decision"] = payload.get("decision")
    return descriptor


def load_checked_matched() -> dict[str, Any]:
    payload = load_json(MATCHED_EVIDENCE)
    if payload.get("schema") != MATCHED.SCHEMA:
        raise D128ComparatorTargetError("matched feasibility schema mismatch")
    if payload.get("decision") != MATCHED.DECISION_NO_GO:
        raise D128ComparatorTargetError("matched feasibility decision mismatch")
    summary = require_object(payload.get("summary"), "matched feasibility summary")
    expect_equal(summary.get("target_count"), 2, "matched target count")
    expect_equal(summary.get("no_go_count"), 2, "matched no-go count")
    d128_rows = [row for row in require_list(payload.get("rows"), "matched feasibility rows") if row.get("target_width") == TARGET_WIDTH]
    if len(d128_rows) != 1:
        raise D128ComparatorTargetError("matched feasibility must contain exactly one d128 row")
    d128_row = d128_rows[0]
    expect_equal(d128_row.get("status"), "NO_GO_CURRENT_SURFACE", "matched d128 row status")
    expect_equal(d128_row.get("target_estimated_linear_muls"), 196_608, "matched d128 linear mul estimate")
    d128_targets = [target for target in require_list(payload.get("targets"), "matched feasibility targets") if target.get("width") == TARGET_WIDTH]
    if len(d128_targets) != 1:
        raise D128ComparatorTargetError("matched feasibility must contain exactly one d128 target")
    expect_equal(d128_targets[0], MATCHED.matched_target(TARGET_WIDTH), "matched d128 target")
    return payload


def load_checked_external() -> dict[str, Any]:
    payload = load_json(EXTERNAL_EVIDENCE)
    try:
        EXTERNAL.validate_probe(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128ComparatorTargetError(f"external adapter feasibility validation failed: {err}") from err
    if payload.get("decision") != EXTERNAL.DECISION:
        raise D128ComparatorTargetError("external adapter decision mismatch")
    return payload


def load_published_rows(path: pathlib.Path = PUBLISHED_ZKML_NUMBERS) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    except OSError as err:
        raise D128ComparatorTargetError(f"failed to load published zkML numbers: {err}") from err
    if not rows:
        raise D128ComparatorTargetError("published zkML numbers table is empty")
    return rows


def nanozk_layerwise_context(rows: list[dict[str, str]]) -> dict[str, Any]:
    matches = [
        row
        for row in rows
        if row.get("system") == "NANOZK"
        and row.get("source_kind") == "arxiv"
        and row.get("source_locator") == "Abstract"
        and "d=128" in row.get("model_or_dims", "")
    ]
    if len(matches) != 1:
        raise D128ComparatorTargetError("expected exactly one NANOZK d128 source-backed calibration row")
    row = matches[0]
    if row.get("verify_seconds") != "0.024":
        raise D128ComparatorTargetError("NANOZK d128 verify_seconds drift")
    if row.get("proof_size_reported") != "5.5 KB":
        raise D128ComparatorTargetError("NANOZK d128 proof_size_reported drift")
    if "not as a matched workload benchmark" not in row.get("notes", ""):
        raise D128ComparatorTargetError("NANOZK row must remain non-matched context")
    return {
        "system": row["system"],
        "source_kind": row["source_kind"],
        "source_url": row["source_url"],
        "source_locator": row["source_locator"],
        "backend_family": row["backend_family"],
        "workload_label": row["workload_label"],
        "workload_scope": row["workload_scope"],
        "model_or_dims": row["model_or_dims"],
        "verify_seconds": row["verify_seconds"],
        "proof_size_reported": row["proof_size_reported"],
        "claim_boundary": "source-backed compact/layerwise context only; not a matched local benchmark",
        "notes": row["notes"],
    }


def target_spec(matched_payload: dict[str, Any]) -> dict[str, Any]:
    target = copy.deepcopy(MATCHED.matched_target(TARGET_WIDTH))
    row = next(row for row in matched_payload["rows"] if row["target_width"] == TARGET_WIDTH)
    residual_rows = TARGET_WIDTH
    target["local_feasibility_status"] = row["status"]
    target["local_feasibility_blockers"] = copy.deepcopy(row["blockers"])
    target["comparator_target_kind"] = "d128-layerwise-rmsnorm-swiglu-residual-receipt"
    target["estimated_residual_rows"] = residual_rows
    target["row_operator_pressure"] = {
        "rmsnorm_rows": target["estimated_norm_rows"],
        "swiglu_activation_rows": target["estimated_activation_rows"],
        "residual_add_rows": residual_rows,
        "linear_projection_multiplications": target["estimated_linear_muls"],
    }
    target["d64_to_d128_scale_decision"] = D128_SCALE_DECISION
    target["d64_slice_generalization"] = [
        {
            "slice": "rmsnorm_public_rows",
            "decision": "GENERALIZES_STRUCTURALLY_WITH_WIDTH_PARAMETER",
            "d64_rows": 64,
            "d128_rows": 128,
            "blocked_on": "no local d128 RMSNorm proof artifact or verifier handle",
        },
        {
            "slice": "rmsnorm_projection_bridge",
            "decision": "GENERALIZES_STRUCTURALLY_AS_COMMITMENT_BRIDGE",
            "d64_rows": 1,
            "d128_rows": 1,
            "blocked_on": "needs a d128 RMSNorm output commitment to bridge",
        },
        {
            "slice": "gate_value_projection",
            "decision": "GENERALIZES_OPERATOR_FAMILY_BUT_NOT_CURRENT_PROOF_SURFACE",
            "d64_linear_muls": 32768,
            "d128_linear_muls": 131072,
            "blocked_on": "current proof generator is fixture-gated and not a parameterized vector-block AIR",
        },
        {
            "slice": "activation_swiglu",
            "decision": "GENERALIZES_OPERATOR_FAMILY_BUT_REQUIRES_D128_RANGE_LOOKUP_SURFACE",
            "d64_rows": 256,
            "d128_rows": 512,
            "blocked_on": "no d128 activation/range proof artifact or relabeling suite",
        },
        {
            "slice": "down_projection",
            "decision": "GENERALIZES_OPERATOR_FAMILY_BUT_NOT_CURRENT_PROOF_SURFACE",
            "d64_linear_muls": 16384,
            "d128_linear_muls": 65536,
            "blocked_on": "current proof generator is fixture-gated and not a parameterized vector-block AIR",
        },
        {
            "slice": "residual_add",
            "decision": "GENERALIZES_STRUCTURALLY_WITH_WIDTH_PARAMETER",
            "d64_rows": 64,
            "d128_rows": 128,
            "blocked_on": "no local d128 residual-add proof artifact or verifier handle",
        },
    ]
    target["target_commitment"] = blake2b_commitment(target, TARGET_DOMAIN)
    return target


def local_proof_status(matched_payload: dict[str, Any]) -> dict[str, Any]:
    row = next(row for row in matched_payload["rows"] if row["target_width"] == TARGET_WIDTH)
    return {
        "result": LOCAL_PROOF_RESULT,
        "proof_artifact_exists": False,
        "verifier_handle_exists": False,
        "statement_relabeling_suite_exists": False,
        "proof_size_bytes": None,
        "verifier_time_ms": None,
        "blocked_before_metrics": True,
        "first_blocker": "current checked Stwo proof surface is width-4, fixture-gated, and not a d128 RMSNorm-SwiGLU proof",
        "d64_to_d128_scale_decision": D128_SCALE_DECISION,
        "scale_decision_rationale": (
            "the d64 slice interfaces generalize structurally, but the current Stwo-native proof "
            "surface does not scale to a d128 proof because it is fixture-gated and lacks a "
            "parameterized vector-block AIR/verifier handle"
        ),
        "inherited_feasibility_row": copy.deepcopy(row),
    }


def external_adapter_status(external_payload: dict[str, Any]) -> dict[str, Any]:
    systems = {system["system"]: copy.deepcopy(system) for system in external_payload["systems"]}
    return {
        "result": EXTERNAL_ADAPTER_RESULT,
        "paper_usage": external_payload["conclusion"]["paper_usage"],
        "systems": systems,
    }


def build_payload() -> dict[str, Any]:
    matched = load_checked_matched()
    external = load_checked_external()
    published_rows = load_published_rows()
    source_context = nanozk_layerwise_context(published_rows)
    target = target_spec(matched)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "target_result": TARGET_RESULT,
        "local_proof_result": LOCAL_PROOF_RESULT,
        "source_context_result": SOURCE_CONTEXT_RESULT,
        "external_adapter_result": EXTERNAL_ADAPTER_RESULT,
        "source_evidence": {
            "matched_feasibility": source_descriptor(MATCHED_EVIDENCE, matched, include_schema=True, include_decision=True),
            "external_adapter_feasibility": source_descriptor(EXTERNAL_EVIDENCE, external, include_schema=True, include_decision=True),
            "published_zkml_numbers": {
                "path": relative_path(PUBLISHED_ZKML_NUMBERS),
                "file_sha256": file_sha256(PUBLISHED_ZKML_NUMBERS),
            },
        },
        "target_spec": target,
        "local_proof_status": local_proof_status(matched),
        "source_backed_context": {"NANOZK": source_context},
        "external_adapter_status": external_adapter_status(external),
        "summary": {
            "decision": DECISION,
            "result": RESULT,
            "target_result": TARGET_RESULT,
            "target_width": TARGET_WIDTH,
            "target_ff_dim": target["ff_dim"],
            "target_estimated_linear_muls": target["estimated_linear_muls"],
            "target_estimated_residual_rows": target["estimated_residual_rows"],
            "d64_to_d128_scale_decision": D128_SCALE_DECISION,
            "target_commitment": target["target_commitment"],
            "local_proof_result": LOCAL_PROOF_RESULT,
            "source_context_result": SOURCE_CONTEXT_RESULT,
            "external_adapter_result": EXTERNAL_ADAPTER_RESULT,
            "first_blocker": FIRST_BLOCKER,
        },
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }
    _validate_draft_payload(payload)
    return payload


def _validate_source_evidence(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = require_object(payload.get("source_evidence"), "source evidence")
    matched = load_checked_matched()
    external = load_checked_external()
    published_rows = load_published_rows()
    expect_equal(source.get("matched_feasibility"), source_descriptor(MATCHED_EVIDENCE, matched, include_schema=True, include_decision=True), "matched source evidence")
    expect_equal(source.get("external_adapter_feasibility"), source_descriptor(EXTERNAL_EVIDENCE, external, include_schema=True, include_decision=True), "external source evidence")
    expect_equal(source.get("published_zkml_numbers"), {"path": relative_path(PUBLISHED_ZKML_NUMBERS), "file_sha256": file_sha256(PUBLISHED_ZKML_NUMBERS)}, "published zkML source evidence")
    return matched, external, {"NANOZK": nanozk_layerwise_context(published_rows)}


def _validate_local_proof_status(status: dict[str, Any], matched: dict[str, Any]) -> None:
    expect_equal(status.get("result"), LOCAL_PROOF_RESULT, "local proof result")
    if status.get("proof_artifact_exists") is not False:
        raise D128ComparatorTargetError("local d128 proof artifact overclaim")
    if status.get("verifier_handle_exists") is not False:
        raise D128ComparatorTargetError("local d128 verifier handle overclaim")
    if status.get("statement_relabeling_suite_exists") is not False:
        raise D128ComparatorTargetError("local d128 relabeling suite overclaim")
    if status.get("proof_size_bytes") is not None:
        raise D128ComparatorTargetError("local d128 proof-size metric supplied before proof exists")
    if status.get("verifier_time_ms") is not None:
        raise D128ComparatorTargetError("local d128 verifier-time metric supplied before proof exists")
    if status.get("blocked_before_metrics") is not True:
        raise D128ComparatorTargetError("local d128 metrics must remain blocked before proof exists")
    expect_equal(status, local_proof_status(matched), "local proof status")


def _validate_external_adapter_status(status: dict[str, Any], external: dict[str, Any]) -> None:
    expect_equal(status, external_adapter_status(external), "external adapter status")
    systems = require_object(status.get("systems"), "external adapter systems")
    for name in ("DeepProve-1", "NANOZK"):
        system = require_object(systems.get(name), f"external adapter system {name}")
        if system.get("public_proof_artifact_available") is not False:
            raise D128ComparatorTargetError(f"{name} public proof artifact overclaim")
        if system.get("public_verifier_available") is not False:
            raise D128ComparatorTargetError(f"{name} public verifier overclaim")
        if system.get("relabeling_benchmark_run") is not False:
            raise D128ComparatorTargetError(f"{name} relabeling benchmark overclaim")


def _validate_common_payload(payload: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = require_object(payload, "d128 comparator target payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("target_result"), TARGET_RESULT, "target result")
    expect_equal(payload.get("local_proof_result"), LOCAL_PROOF_RESULT, "local proof result")
    expect_equal(payload.get("source_context_result"), SOURCE_CONTEXT_RESULT, "source context result")
    expect_equal(payload.get("external_adapter_result"), EXTERNAL_ADAPTER_RESULT, "external adapter result")
    matched, external, context = _validate_source_evidence(payload)
    target = target_spec(matched)
    expect_equal(payload.get("target_spec"), target, "target spec")
    _validate_local_proof_status(require_object(payload.get("local_proof_status"), "local proof status"), matched)
    expect_equal(payload.get("source_backed_context"), context, "source-backed context")
    if "not a matched local benchmark" not in context["NANOZK"]["claim_boundary"]:
        raise D128ComparatorTargetError("source context promoted to matched benchmark")
    _validate_external_adapter_status(require_object(payload.get("external_adapter_status"), "external adapter status"), external)
    expected_summary = {
        "decision": DECISION,
        "result": RESULT,
        "target_result": TARGET_RESULT,
        "target_width": TARGET_WIDTH,
        "target_ff_dim": target["ff_dim"],
        "target_estimated_linear_muls": target["estimated_linear_muls"],
        "target_estimated_residual_rows": target["estimated_residual_rows"],
        "d64_to_d128_scale_decision": D128_SCALE_DECISION,
        "target_commitment": target["target_commitment"],
        "local_proof_result": LOCAL_PROOF_RESULT,
        "source_context_result": SOURCE_CONTEXT_RESULT,
        "external_adapter_result": EXTERNAL_ADAPTER_RESULT,
        "first_blocker": FIRST_BLOCKER,
    }
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    return matched, external, expected_summary


def _validate_draft_payload(payload: Any) -> None:
    _, _, expected_summary = _validate_common_payload(payload)
    if any(field in payload for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected")):
        raise D128ComparatorTargetError("draft payload must not include mutation metadata")
    expect_equal(payload.get("summary"), expected_summary, "summary")


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    if not all(field in payload for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected")):
        raise D128ComparatorTargetError("mutation metadata must include inventory, cases, count, and all_mutations_rejected")
    expect_equal(require_list(payload.get("mutation_inventory"), "mutation inventory"), expected_mutation_inventory(), "mutation inventory")
    cases = require_list(payload.get("cases"), "mutation cases")
    case_pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    rejected = 0
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"mutation case {index}")
        for column in MUTATION_TSV_COLUMNS:
            if column not in case:
                raise D128ComparatorTargetError(f"mutation case {index} missing {column}")
        pair = (case["mutation"], case["surface"])
        if pair in seen:
            raise D128ComparatorTargetError(f"duplicate mutation case {index}")
        seen.add(pair)
        case_pairs.append(pair)
        if case["baseline_result"] != RESULT:
            raise D128ComparatorTargetError(f"mutation case {index} baseline_result mismatch")
        if not isinstance(case["mutated_accepted"], bool) or not isinstance(case["rejected"], bool):
            raise D128ComparatorTargetError(f"mutation case {index} boolean fields malformed")
        if case["mutated_accepted"] == case["rejected"]:
            raise D128ComparatorTargetError(f"mutation case {index} accepted/rejected fields inconsistent")
        if not isinstance(case["error"], str):
            raise D128ComparatorTargetError(f"mutation case {index} error must be a string")
        if case["rejected"] and not case["error"]:
            raise D128ComparatorTargetError(f"mutation case {index} rejected case error must be non-empty")
        if case["rejected"]:
            rejected += 1
    expect_equal(tuple(case_pairs), EXPECTED_MUTATION_INVENTORY, "mutation case inventory")
    expect_equal(payload.get("case_count"), len(cases), "mutation case_count")
    expect_equal(payload.get("all_mutations_rejected"), all(case["rejected"] for case in cases), "all_mutations_rejected")
    return len(cases), rejected


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "d128 comparator target payload")
    _, _, expected_summary = _validate_common_payload(payload)
    case_count, rejected = _validate_case_metadata(payload)
    if case_count != rejected:
        raise D128ComparatorTargetError("not all d128 comparator target mutations rejected")
    expected_summary["mutation_cases"] = case_count
    expected_summary["mutations_rejected"] = rejected
    expect_equal(payload.get("summary"), expected_summary, "summary")


def classify_error(error: Exception) -> str:
    text = str(error).lower()
    if "nanozk row" in text or "source context" in text or "source-backed context" in text or "matched benchmark" in text:
        return "source_context"
    if "source" in text or "evidence" in text or "file_sha" in text or "payload_sha" in text:
        return "source_evidence"
    if "target" in text or "commitment" in text or "binding" in text:
        return "target_spec"
    if "local d128" in text or "local proof" in text or "metric" in text:
        return "local_proof_status"
    if "external adapter" in text or "deepprove" in text or "public verifier" in text or "public proof" in text:
        return "external_adapter_status"
    if "non-claims" in text:
        return "claim_boundary"
    return "parser_or_schema"


def exception_message(error: Exception) -> str:
    text = str(error)
    if text:
        return text
    return f"{type(error).__name__} with empty message"


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any], Exception | None]]:
    cases: list[tuple[str, str, dict[str, Any], Exception | None]] = []

    def add(name: str, surface: str, mutator: Callable[[dict[str, Any]], None]) -> None:
        mutated = copy.deepcopy(baseline)
        generation_error = None
        try:
            mutator(mutated)
        except Exception as err:  # noqa: BLE001 - mutation failures are recorded as rejected cases.
            generation_error = err
        cases.append((name, surface, mutated, generation_error))

    add("matched_source_file_hash_drift", "source_evidence", lambda p: p["source_evidence"]["matched_feasibility"].__setitem__("file_sha256", "11" * 32))
    add("external_source_payload_hash_drift", "source_evidence", lambda p: p["source_evidence"]["external_adapter_feasibility"].__setitem__("payload_sha256", "22" * 32))
    add("target_width_drift", "target_spec", lambda p: p["target_spec"].__setitem__("width", 64))
    add("target_binding_removed", "target_spec", lambda p: p["target_spec"]["required_statement_bindings"].pop())
    add("target_linear_mul_estimate_drift", "target_spec", lambda p: p["target_spec"].__setitem__("estimated_linear_muls", 1))
    add("target_residual_row_count_drift", "target_spec", lambda p: p["target_spec"].__setitem__("estimated_residual_rows", 0))
    add("target_scale_decision_promoted_to_go", "target_spec", lambda p: p["target_spec"].__setitem__("d64_to_d128_scale_decision", "GO_CURRENT_STWO_SURFACE_SCALES_TO_D128"))
    add("target_d64_slice_generalization_overclaim", "target_spec", lambda p: p["target_spec"]["d64_slice_generalization"][2].__setitem__("decision", "GENERALIZES_DIRECTLY_TO_CURRENT_PROOF_SURFACE"))
    add("target_commitment_drift", "target_spec", lambda p: p["target_spec"].__setitem__("target_commitment", "blake2b-256:" + "33" * 32))
    add("local_proof_result_changed_to_go", "local_proof_status", lambda p: p["local_proof_status"].__setitem__("result", "GO_LOCAL_D128_PROOF"))
    add("local_proof_size_metric_smuggled", "local_proof_status", lambda p: p["local_proof_status"].__setitem__("proof_size_bytes", 5500))
    add("local_verify_time_metric_smuggled", "local_proof_status", lambda p: p["local_proof_status"].__setitem__("verifier_time_ms", 24.0))
    add("nanozk_source_row_verify_seconds_drift", "source_context", lambda p: p["source_backed_context"]["NANOZK"].__setitem__("verify_seconds", "0.001"))
    add("nanozk_source_context_promoted_to_matched", "source_context", lambda p: p["source_backed_context"]["NANOZK"].__setitem__("claim_boundary", "matched local benchmark"))
    add("external_adapter_result_changed_to_go", "external_adapter_status", lambda p: p["external_adapter_status"].__setitem__("result", "GO_PUBLIC_RELABELING_ADAPTER_BENCHMARK"))
    add("deepprove_public_artifact_overclaim", "external_adapter_status", lambda p: p["external_adapter_status"]["systems"]["DeepProve-1"].__setitem__("public_proof_artifact_available", True))
    add("nanozk_public_verifier_overclaim", "external_adapter_status", lambda p: p["external_adapter_status"]["systems"]["NANOZK"].__setitem__("public_verifier_available", True))
    add("non_claim_removed", "claim_boundary", lambda p: p["non_claims"].remove("not a matched NANOZK benchmark"))
    add("result_changed_to_go", "parser_or_schema", lambda p: p.__setitem__("result", "GO"))
    return cases


def mutation_cases(baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_payload())
    _validate_draft_payload(baseline)
    cases = []
    for mutation, surface, mutated, generation_error in _mutated_cases(baseline):
        if generation_error is not None:
            accepted = False
            error = exception_message(generation_error)
            layer = classify_error(generation_error)
        else:
            try:
                _validate_draft_payload(mutated)
                accepted = True
                error = ""
                layer = "accepted"
            except D128ComparatorTargetError as err:
                accepted = False
                error = str(err)
                layer = classify_error(err)
        cases.append(
            {
                "mutation": mutation,
                "surface": surface,
                "baseline_result": RESULT,
                "mutated_accepted": accepted,
                "rejected": not accepted,
                "rejection_layer": layer,
                "error": error,
            }
        )
    return cases


def build_gate_result() -> dict[str, Any]:
    payload = build_payload()
    cases = mutation_cases(payload)
    result = copy.deepcopy(payload)
    result["mutation_inventory"] = expected_mutation_inventory()
    result["case_count"] = len(cases)
    result["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    result["cases"] = cases
    result["summary"]["mutation_cases"] = len(cases)
    result["summary"]["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    validate_payload(result)
    if not result["all_mutations_rejected"]:
        raise D128ComparatorTargetError("not all d128 comparator target mutations rejected")
    return result


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, str]]:
    target = payload["target_spec"]
    local = payload["local_proof_status"]
    nanozk = payload["source_backed_context"]["NANOZK"]
    external = payload["external_adapter_status"]
    return [
        {
            "surface": "local_d128_target_spec",
            "status": payload["target_result"],
            "width": str(target["width"]),
            "source": "local target gate",
            "prove_seconds": "NA",
            "verify_seconds": "NA",
            "proof_size_reported": "NA",
            "claim_boundary": "statement target only",
            "blocker": "NA",
        },
        {
            "surface": "local_d128_proof_artifact",
            "status": local["result"],
            "width": str(target["width"]),
            "source": "local Stwo surface",
            "prove_seconds": "NA",
            "verify_seconds": "NA",
            "proof_size_reported": "NA",
            "claim_boundary": "no local d128 proof metrics before artifact exists",
            "blocker": local["first_blocker"],
        },
        {
            "surface": "nanozk_d128_source_context",
            "status": payload["source_context_result"],
            "width": str(target["width"]),
            "source": nanozk["source_url"],
            "prove_seconds": "NA",
            "verify_seconds": nanozk["verify_seconds"],
            "proof_size_reported": nanozk["proof_size_reported"],
            "claim_boundary": nanozk["claim_boundary"],
            "blocker": "not locally reproduced",
        },
        {
            "surface": "deepprove_nanozk_adapter_context",
            "status": external["result"],
            "width": str(target["width"]),
            "source": external["paper_usage"],
            "prove_seconds": "NA",
            "verify_seconds": "NA",
            "proof_size_reported": "NA",
            "claim_boundary": "source-backed context only, not empirical adapter row",
            "blocker": "public proof artifact plus verifier inputs unavailable for this adapter benchmark",
        },
    ]


def to_tsv(payload: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows_for_tsv(payload))
    return buffer.getvalue()


def to_mutation_tsv(payload: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=MUTATION_TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: case[key] for key in MUTATION_TSV_COLUMNS} for case in payload["cases"])
    return buffer.getvalue()


def _validated_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise D128ComparatorTargetError(f"output path must not be a symlink: {path}")
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise D128ComparatorTargetError(f"output path escapes repository: {path}")
    if resolved.exists() and resolved.is_dir():
        raise D128ComparatorTargetError(f"output path must be a file, not a directory: {path}")
    if resolved.parent.exists() and not resolved.parent.is_dir():
        raise D128ComparatorTargetError(f"output path parent is not a directory: {path}")
    return resolved


def _stage_text(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        return pathlib.Path(handle.name)


def _stage_bytes(path: pathlib.Path, data: bytes) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        return pathlib.Path(handle.name)


def _fsync_parent_directory(path: pathlib.Path) -> None:
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if directory_flag is None:
        return
    try:
        fd = os.open(str(path.parent), os.O_RDONLY | directory_flag)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_parent_directories(paths: list[pathlib.Path]) -> None:
    seen: set[pathlib.Path] = set()
    for path in paths:
        parent = path.parent
        if parent in seen:
            continue
        seen.add(parent)
        _fsync_parent_directory(path)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    json_output = _validated_output_path(json_path) if json_path is not None else None
    tsv_output = _validated_output_path(tsv_path) if tsv_path is not None else None
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n" if json_path is not None else None
    tsv_text = to_tsv(payload) if tsv_path is not None else None

    staged: list[tuple[pathlib.Path, pathlib.Path]] = []
    committed: list[tuple[pathlib.Path, bool, bytes | None]] = []
    try:
        if json_output is not None:
            staged.append((_stage_text(json_output, json_text), json_output))
        if tsv_output is not None:
            staged.append((_stage_text(tsv_output, tsv_text), tsv_output))
        for tmp_path, output_path in staged:
            existed = output_path.exists()
            previous = output_path.read_bytes() if existed else None
            tmp_path.replace(output_path)
            committed.append((output_path, existed, previous))
        _fsync_parent_directories([output_path for _, output_path in staged])
    except Exception as err:
        cleanup_errors: list[str] = []
        for tmp_path, _ in staged:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError as cleanup_err:
                cleanup_errors.append(f"cleanup failed for {tmp_path}: {cleanup_err}")
        for output_path, existed, previous in reversed(committed):
            try:
                if existed and previous is not None:
                    rollback_tmp = _stage_bytes(output_path, previous)
                    try:
                        rollback_tmp.replace(output_path)
                        _fsync_parent_directory(output_path)
                    finally:
                        rollback_tmp.unlink(missing_ok=True)
                else:
                    output_path.unlink(missing_ok=True)
                    _fsync_parent_directory(output_path)
            except OSError as rollback_err:
                cleanup_errors.append(f"rollback failed for {output_path}: {rollback_err}")
        if isinstance(err, OSError):
            detail = f"failed to write outputs: {err}"
            if cleanup_errors:
                detail += "; " + "; ".join(cleanup_errors)
            raise D128ComparatorTargetError(detail) from err
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--print-mutation-tsv", action="store_true")
    args = parser.parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    if args.print_mutation_tsv:
        print(to_mutation_tsv(payload), end="")
    else:
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
