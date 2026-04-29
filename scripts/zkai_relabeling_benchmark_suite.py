#!/usr/bin/env python3
"""Public relabeling benchmark suite for statement-bound zkAI receipts.

The suite asks one narrow question: after a verifier accepts a baseline proof or
receipt object, does it reject the same object when the user-facing statement is
relabelled without matching evidence?  It is not a performance benchmark and it
is not a soundness proof for the underlying proof system.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import tomllib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts" / "agent_step_receipt_relabeling_harness.py"
SPEC = importlib.util.spec_from_file_location("agent_step_receipt_harness", HARNESS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load agent receipt harness from {HARNESS_PATH}")
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


SUITE_SCHEMA = "zkai-relabeling-benchmark-suite-v1"
RUST_ADAPTER_SCHEMA = "agent-step-receipt-rust-verifier-adapter-v1"
BINDING_REJECTION_MARKERS = (
    "does not bind",
    "dependency_drop_manifest_commitment mismatch",
    "evidence_manifest_commitment mismatch",
)
DOMAIN_OR_VERSION_REJECTION_MARKERS = ("unsupported", "domain", "version")
TRUST_POLICY_REJECTION_MARKERS = ("trust", "evidence kind", "insufficient evidence")
PARSER_OR_SCHEMA_REJECTION_MARKERS = (
    "omitted",
    "unexpected",
    "unknown",
    "invalid",
    "malformed",
    "parse",
    "schema",
    "syntax",
)

MUTATION_CATALOG: dict[str, dict[str, str]] = {
    "receipt_version": {
        "category": "receipt_schema_version_relabeling",
        "target_field": "/receipt_version",
        "claim_axis": "receipt schema/version",
    },
    "model_id": {
        "category": "model_identity_relabeling",
        "target_field": "/model_identity",
        "claim_axis": "model identity",
    },
    "runtime_domain": {
        "category": "runtime_domain_relabeling",
        "target_field": "/runtime_domain",
        "claim_axis": "runtime domain",
    },
    "proof_backend": {
        "category": "proof_backend_relabeling",
        "target_field": "/proof_backend",
        "claim_axis": "proof backend",
    },
    "receipt_parser_version": {
        "category": "parser_version_relabeling",
        "target_field": "/receipt_parser_version",
        "claim_axis": "receipt parser version",
    },
    "weights_commitment": {
        "category": "model_weights_relabeling",
        "target_field": "/model_commitment",
        "claim_axis": "model weights",
    },
    "model_receipt_commitment": {
        "category": "model_receipt_relabeling",
        "target_field": "/model_receipt_commitment",
        "claim_axis": "model receipt/proof",
    },
    "input_commitment": {
        "category": "input_context_relabeling",
        "target_field": "/observation_commitment",
        "claim_axis": "input/context",
    },
    "output_action_commitment": {
        "category": "output_action_relabeling",
        "target_field": "/action_commitment",
        "claim_axis": "output/action",
    },
    "quantization_config_commitment": {
        "category": "model_config_relabeling",
        "target_field": "/model_config_commitment",
        "claim_axis": "quantization/config",
    },
    "policy_hash": {
        "category": "policy_relabeling",
        "target_field": "/policy_commitment",
        "claim_axis": "policy/tool policy",
    },
    "tool_output_hash": {
        "category": "tool_output_relabeling",
        "target_field": "/tool_receipts_root",
        "claim_axis": "tool output",
    },
    "prior_state_commitment": {
        "category": "prior_state_relabeling",
        "target_field": "/prior_state_commitment",
        "claim_axis": "prior agent state",
    },
    "next_state_commitment": {
        "category": "next_state_relabeling",
        "target_field": "/next_state_commitment",
        "claim_axis": "next agent state",
    },
    "backend_proof_system_version": {
        "category": "proof_system_version_relabeling",
        "target_field": "/proof_backend_version",
        "claim_axis": "proof-system version",
    },
    "verifier_domain_separator": {
        "category": "verifier_domain_relabeling",
        "target_field": "/verifier_domain",
        "claim_axis": "verifier domain separator",
    },
    "transcript_hash": {
        "category": "transcript_relabeling",
        "target_field": "/transcript_commitment",
        "claim_axis": "agent transcript",
    },
    "dependency_drop_manifest": {
        "category": "dependency_manifest_relabeling",
        "target_field": "/dependency_drop_manifest_commitment",
        "claim_axis": "dependency-drop manifest",
    },
    "evidence_manifest": {
        "category": "evidence_manifest_relabeling",
        "target_field": "/evidence_manifest_commitment",
        "claim_axis": "evidence manifest",
    },
    "trust_class_upgrade_without_proof": {
        "category": "trust_class_upgrade_relabeling",
        "target_field": "/model_identity",
        "claim_axis": "trust-class upgrade",
    },
}

TSV_COLUMNS = [
    "adapter",
    "system_under_test",
    "git_commit",
    "mutation",
    "category",
    "claim_axis",
    "target_field",
    "baseline_artifact_sha256",
    "mutated_artifact_sha256",
    "baseline_accepted",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
]


def _case_catalog() -> dict[str, Callable[[dict[str, Any]], None]]:
    cases = HARNESS.mutation_cases()
    missing = set(cases) - set(MUTATION_CATALOG)
    stale = set(MUTATION_CATALOG) - set(cases)
    if missing or stale:
        raise RuntimeError(
            f"mutation catalog mismatch: missing_metadata={sorted(missing)} stale_metadata={sorted(stale)}"
        )
    return cases


def _canonical_bundle_bytes(bundle: dict[str, Any]) -> bytes:
    return HARNESS.canonical_json_bytes(bundle)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact_hashes() -> dict[str, str]:
    bundles = {"baseline": HARNESS.build_valid_bundle(), **_mutated_bundles()}
    return {case_id: _sha256_hex(_canonical_bundle_bytes(bundle)) for case_id, bundle in bundles.items()}


def _git_commit() -> str:
    override = os.environ.get("ZKAI_RELABELING_BENCHMARK_GIT_COMMIT")
    if override:
        return override
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _canonical_command(command: list[str] | None) -> list[str]:
    override = os.environ.get("ZKAI_RELABELING_BENCHMARK_COMMAND")
    if override:
        return [override]
    if command is None:
        return []
    return command


def _verifier_metadata(adapter: str) -> dict[str, str]:
    cargo = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))
    package = cargo["package"]
    return {
        "adapter": adapter,
        "suite_schema": SUITE_SCHEMA,
        "rust_adapter_schema": RUST_ADAPTER_SCHEMA,
        "crate_name": package["name"],
        "crate_version": package["version"],
        "receipt_version": HARNESS.RECEIPT_VERSION,
        "receipt_parser_version": HARNESS.RECEIPT_PARSER_VERSION,
        "verifier_domain": HARNESS.VERIFIER_DOMAIN,
        "proof_backend": HARNESS.PROOF_BACKEND,
        "proof_backend_version": HARNESS.PROOF_BACKEND_VERSION,
    }


def _classify_rejection(error: str) -> str:
    lowered = error.lower()
    if any(marker in lowered for marker in BINDING_REJECTION_MARKERS):
        return "cryptographic_binding"
    if any(marker in lowered for marker in DOMAIN_OR_VERSION_REJECTION_MARKERS):
        return "domain_or_version_allowlist"
    if any(marker in lowered for marker in TRUST_POLICY_REJECTION_MARKERS):
        return "trust_policy"
    if any(marker in lowered for marker in PARSER_OR_SCHEMA_REJECTION_MARKERS):
        return "parser_or_schema_validation"
    return "verifier_policy"


def _python_verify(bundle: dict[str, Any]) -> tuple[bool, str]:
    try:
        HARNESS.verify_bundle(bundle)
    except HARNESS.AgentReceiptError as err:
        return False, str(err)
    return True, ""


def _mutated_bundles() -> dict[str, dict[str, Any]]:
    bundles = {}
    for mutation, mutate in _case_catalog().items():
        bundle = HARNESS.build_valid_bundle()
        mutate(bundle)
        bundles[mutation] = bundle
    return bundles


def _run_python_reference() -> tuple[bool, str, dict[str, tuple[bool, str]]]:
    baseline_accepted, baseline_error = _python_verify(HARNESS.build_valid_bundle())
    results = {mutation: _python_verify(bundle) for mutation, bundle in _mutated_bundles().items()}
    return baseline_accepted, baseline_error, results


def _run_rust_production() -> tuple[bool, str, dict[str, tuple[bool, str]]]:
    bundles = {"baseline": HARNESS.build_valid_bundle(), **_mutated_bundles()}
    with tempfile.TemporaryDirectory(prefix="zkai-relabeling-suite-") as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        args = []
        for case_id, bundle in bundles.items():
            path = tmp / f"{case_id}.json"
            path.write_bytes(_canonical_bundle_bytes(bundle))
            args.append(f"{case_id}={path}")
        cmd = ["cargo", "run", "--quiet", "--example", "agent_step_receipt_verify", "--", *args]
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "rust production adapter failed:\n"
                f"command: {' '.join(cmd)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        payload = json.loads(completed.stdout)
    if payload.get("schema") != RUST_ADAPTER_SCHEMA:
        raise RuntimeError(f"unexpected rust adapter schema: {payload.get('schema')!r}")
    results = payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError("rust adapter returned malformed results: expected list")
    expected = {"baseline", *_case_catalog().keys()}
    case_ids = []
    raw_results = {}
    for item in results:
        if not isinstance(item, dict):
            raise RuntimeError("rust adapter returned malformed result row: expected object")
        case_id = item.get("case_id")
        accepted = item.get("accepted")
        error = item.get("error")
        if not isinstance(case_id, str) or not isinstance(accepted, bool) or not isinstance(error, str):
            raise RuntimeError("rust adapter returned malformed result row")
        case_ids.append(case_id)
        raw_results[case_id] = (accepted, error)
    duplicate_case_ids = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicate_case_ids:
        raise RuntimeError(f"rust adapter returned duplicate case_id rows: {duplicate_case_ids}")
    actual = set(raw_results)
    if actual != expected:
        raise RuntimeError(
            "rust adapter returned incomplete case coverage: "
            f"missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )
    baseline_accepted, baseline_error = raw_results.pop("baseline")
    return baseline_accepted, baseline_error, raw_results


def run_suite(adapter: str, command: list[str] | None = None) -> dict[str, Any]:
    if adapter == "python-reference":
        baseline_accepted, baseline_error, raw_results = _run_python_reference()
        system_under_test = "reference AgentStepReceiptV1 mutation oracle"
    elif adapter == "rust-production":
        baseline_accepted, baseline_error, raw_results = _run_rust_production()
        system_under_test = "llm-provable-computer AgentStepReceiptV1 production verifier"
    else:
        raise ValueError(f"unsupported adapter {adapter!r}")

    expected_mutations = set(_case_catalog())
    actual_mutations = set(raw_results)
    if actual_mutations != expected_mutations or len(raw_results) != len(expected_mutations):
        raise RuntimeError(
            "adapter result coverage mismatch: "
            f"missing={sorted(expected_mutations - actual_mutations)} "
            f"extra={sorted(actual_mutations - expected_mutations)}"
        )

    artifact_hashes = _artifact_hashes()
    git_commit = _git_commit()
    cases = []
    for mutation in sorted(raw_results):
        accepted, error = raw_results[mutation]
        metadata = MUTATION_CATALOG[mutation]
        cases.append(
            {
                "adapter": adapter,
                "system_under_test": system_under_test,
                "git_commit": git_commit,
                "mutation": mutation,
                "category": metadata["category"],
                "claim_axis": metadata["claim_axis"],
                "target_field": metadata["target_field"],
                "baseline_artifact_sha256": artifact_hashes["baseline"],
                "mutated_artifact_sha256": artifact_hashes[mutation],
                "baseline_accepted": baseline_accepted,
                "mutated_accepted": accepted,
                "rejected": not accepted,
                "rejection_layer": _classify_rejection(error) if not accepted else "accepted",
                "error": error,
            }
        )

    return {
        "schema": SUITE_SCHEMA,
        "suite_kind": "statement_relabeling_conformance",
        "non_claims": [
            "not_a_performance_benchmark",
            "not_a_proof_system_soundness_proof",
            "not_a_ranking_of_external_systems",
        ],
        "adapter": adapter,
        "system_under_test": system_under_test,
        "repro": {
            "git_commit": git_commit,
            "command": _canonical_command(command),
            "verifier": _verifier_metadata(adapter),
            "artifacts": {
                "baseline": {
                    "case_id": "baseline",
                    "sha256": artifact_hashes["baseline"],
                },
                "mutations": {
                    mutation: {
                        "case_id": mutation,
                        "sha256": artifact_hashes[mutation],
                    }
                    for mutation in sorted(raw_results)
                },
            },
        },
        "baseline_accepted": baseline_accepted,
        "baseline_error": baseline_error,
        "all_mutations_rejected": all(case["rejected"] for case in cases),
        "case_count": len(cases),
        "cases": cases,
    }


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for case in payload["cases"]:
        writer.writerow({column: case[column] for column in TSV_COLUMNS})
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adapter",
        choices=("python-reference", "rust-production"),
        default="python-reference",
        help="verifier adapter to run",
    )
    parser.add_argument("--json", action="store_true", help="print JSON result")
    parser.add_argument("--tsv", action="store_true", help="print TSV result")
    parser.add_argument("--write-json", type=pathlib.Path, help="write JSON result to this path")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write TSV result to this path")
    args = parser.parse_args(argv)

    payload = run_suite(args.adapter, command=[sys.executable, *sys.argv])
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tsv_text = to_tsv(payload)

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json_text, encoding="utf-8")
    if args.write_tsv:
        args.write_tsv.parent.mkdir(parents=True, exist_ok=True)
        args.write_tsv.write_text(tsv_text, encoding="utf-8")
    if args.json:
        print(json_text, end="")
    if args.tsv:
        print(tsv_text, end="")
    if not (args.json or args.tsv or args.write_json or args.write_tsv):
        status = "PASS" if payload["baseline_accepted"] and payload["all_mutations_rejected"] else "FAIL"
        print(
            f"{status}: {payload['adapter']} rejected "
            f"{sum(1 for case in payload['cases'] if case['rejected'])}/{payload['case_count']} mutations"
        )

    return 0 if payload["baseline_accepted"] and payload["all_mutations_rejected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
