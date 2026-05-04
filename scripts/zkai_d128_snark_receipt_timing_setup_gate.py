#!/usr/bin/env python3
"""Measure the d128 SNARK statement receipt under an explicit setup policy.

This gate answers issue #430. It consumes the checked #428 snarkjs/Groth16
statement receipt and asks whether the same tiny statement-receipt circuit can
be regenerated, proved, and verified with timing evidence.

The result is deliberately scoped: setup is local/throwaway and not a
production trusted setup. The measured proof does not recursively verify the
underlying Stwo slice proofs; it only receipts the #424 public-input contract
through the #428 statement envelope.
"""

from __future__ import annotations

import argparse
import copy
import csv
import functools
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_d128_snark_ivc_statement_receipt_gate.py"
SOURCE_RECEIPT_EVIDENCE = EVIDENCE_DIR / "zkai-d128-snark-ivc-statement-receipt-2026-05.json"
SOURCE_ARTIFACT_DIR = EVIDENCE_DIR / "zkai-d128-snark-ivc-statement-receipt-2026-05"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-snark-receipt-timing-setup-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-snark-receipt-timing-setup-2026-05.tsv"

SCHEMA = "zkai-d128-snark-receipt-timing-setup-gate-v1"
DECISION = "GO_D128_SNARK_RECEIPT_TIMING_AND_THROWAWAY_SETUP_REGENERATION"
RESULT = "GO"
ISSUE = 430
SOURCE_ISSUE = 428
SOURCE_CONTRACT_ISSUE = 424
SOURCE_SCHEMA = "zkai-d128-snark-ivc-statement-receipt-gate-v1"
SOURCE_DECISION = "GO_D128_SNARK_STATEMENT_RECEIPT_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT"
SOURCE_RESULT = "GO"
SOURCE_CLAIM_BOUNDARY = "SNARK_STATEMENT_RECEIPT_BINDS_D128_TWO_SLICE_PUBLIC_INPUT_CONTRACT_NOT_RECURSION"
CLAIM_BOUNDARY = "SNARK_STATEMENT_RECEIPT_TIMED_UNDER_LOCAL_THROWAWAY_SETUP_NOT_RECURSION"
TIMING_POLICY = "median_of_5_runs_from_perf_counter_ns_on_local_host"
PROOF_SYSTEM = "snarkjs/Groth16/BN128"
SNARKJS_VERSION = "0.7.6"
CIRCOM_VERSION = "2.0.9"
NODE_VERSION = "v23.11.0"
NPM_VERSION = "10.9.2"
POT_POWER = 12
SAMPLE_COUNT = 5
SNARKJS = ROOT / "scripts" / "node_modules" / ".bin" / "snarkjs"
CIRCUIT = SOURCE_ARTIFACT_DIR / "d128_statement_receipt.circom"
INPUT = SOURCE_ARTIFACT_DIR / "input.json"
SOURCE_PUBLIC = SOURCE_ARTIFACT_DIR / "public.json"
SOURCE_PROOF = SOURCE_ARTIFACT_DIR / "proof.json"
SOURCE_VK = SOURCE_ARTIFACT_DIR / "verification_key.json"
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

GATE_COMMAND = (
    "python3 scripts/zkai_d128_snark_receipt_timing_setup_gate.py "
    "--write-json docs/engineering/evidence/zkai-d128-snark-receipt-timing-setup-2026-05.json "
    "--write-tsv docs/engineering/evidence/zkai-d128-snark-receipt-timing-setup-2026-05.tsv"
)
VALIDATION_COMMANDS = [
    "npm ci --prefix scripts",
    GATE_COMMAND,
    "python3 -m unittest scripts.tests.test_zkai_d128_snark_receipt_timing_setup_gate",
    "python3 -m py_compile scripts/zkai_d128_snark_receipt_timing_setup_gate.py scripts/tests/test_zkai_d128_snark_receipt_timing_setup_gate.py",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

SETUP_POLICY = {
    "setup_class": "local_throwaway_groth16_setup_for_statement_receipt_timing_only",
    "production_trusted_setup": False,
    "powers_of_tau_curve": "bn128",
    "powers_of_tau_power": POT_POWER,
    "powers_of_tau_entropy_label": "ptvm timing smoke entropy",
    "zkey_entropy_label": "ptvm timing zkey entropy",
    "proving_key_checked_in": False,
    "setup_artifacts_checked_in": False,
    "setup_artifact_scope": "temporary_directory_deleted_after_gate",
    "generated_artifact_sizes_may_differ_from_source": True,
}

NON_CLAIMS = [
    "not recursive aggregation",
    "not proof-carrying data",
    "not STARK-in-SNARK verification",
    "not verification of the underlying Stwo slice proofs inside Groth16",
    "not a production trusted setup",
    "not an onchain verifier benchmark",
    "not a public zkML throughput benchmark",
    "not a claim that Groth16 is the preferred production backend",
]

EXPECTED_MUTATION_INVENTORY = (
    ("source_receipt_decision_relabeling", "source_receipt"),
    ("source_receipt_claim_boundary_relabeling", "source_receipt"),
    ("source_receipt_metric_relabeling", "source_receipt"),
    ("setup_policy_promoted_to_production", "setup_policy"),
    ("setup_policy_proving_key_checked_in_relabeling", "setup_policy"),
    ("node_version_relabeling", "external_proof_tooling"),
    ("npm_version_relabeling", "external_proof_tooling"),
    ("timing_policy_relabeling", "timing_metrics"),
    ("proof_generation_metric_smuggled", "timing_metrics"),
    ("verifier_metric_smuggled", "timing_metrics"),
    ("public_signal_hash_relabeling", "artifact_binding"),
    ("generated_public_hash_relabeling", "artifact_binding"),
    ("generated_vk_hash_relabeling", "artifact_binding"),
    ("proof_size_relabeling", "artifact_binding"),
    ("generated_size_equivalence_relabeling", "setup_policy"),
    ("repro_command_relabeling", "parser_or_schema"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_removed", "parser_or_schema"),
    ("unknown_top_level_field_added", "parser_or_schema"),
)
EXPECTED_MUTATION_SET = {name for name, _surface in EXPECTED_MUTATION_INVENTORY}

TSV_COLUMNS = (
    "metric",
    "sample_count",
    "median_ms",
    "min_ms",
    "max_ms",
    "all_samples_ms",
    "timing_policy",
    "setup_policy",
)


class D128SnarkTimingSetupError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128SnarkTimingSetupError(f"failed to load {module_name} from {path}", layer="source_receipt")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


SOURCE_RECEIPT = _load_module(SOURCE_RECEIPT_SCRIPT, "zkai_d128_snark_receipt_for_timing_setup_gate")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_object(value: Any, label: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128SnarkTimingSetupError(f"{label} must be an object", layer=layer)
    return value


def require_list(value: Any, label: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise D128SnarkTimingSetupError(f"{label} must be a list", layer=layer)
    return value


def expect_equal(actual: Any, expected: Any, label: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise D128SnarkTimingSetupError(f"{label} mismatch", layer=layer)


def expect_keys(value: dict[str, Any], expected: set[str], label: str, *, layer: str = "parser_or_schema") -> None:
    keys = set(value)
    if keys != expected:
        raise D128SnarkTimingSetupError(
            f"{label} keys mismatch: missing={sorted(expected - keys)} extra={sorted(keys - expected)}",
            layer=layer,
        )


def load_json(path: pathlib.Path, *, layer: str = "artifact_binding") -> Any:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128SnarkTimingSetupError(f"path escapes repository: {path}", layer=layer) from err
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128SnarkTimingSetupError(f"failed to load JSON {path}: {err}", layer=layer) from err


@functools.lru_cache(maxsize=1)
def source_receipt_payload() -> dict[str, Any]:
    payload = require_object(load_json(SOURCE_RECEIPT_EVIDENCE, layer="source_receipt"), "source receipt", layer="source_receipt")
    try:
        SOURCE_RECEIPT.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator failures.
        raise D128SnarkTimingSetupError(f"source #428 receipt validation failed: {err}", layer="source_receipt") from err
    expect_equal(payload.get("schema"), SOURCE_SCHEMA, "source schema", layer="source_receipt")
    expect_equal(payload.get("issue"), SOURCE_ISSUE, "source issue", layer="source_receipt")
    expect_equal(payload.get("source_issue"), SOURCE_CONTRACT_ISSUE, "source contract issue", layer="source_receipt")
    expect_equal(payload.get("decision"), SOURCE_DECISION, "source decision", layer="source_receipt")
    expect_equal(payload.get("result"), SOURCE_RESULT, "source result", layer="source_receipt")
    expect_equal(payload.get("claim_boundary"), SOURCE_CLAIM_BOUNDARY, "source claim boundary", layer="source_receipt")
    expect_equal(payload.get("all_mutations_rejected"), True, "source mutation result", layer="source_receipt")
    return copy.deepcopy(payload)


def source_receipt_summary() -> dict[str, Any]:
    payload = source_receipt_payload()
    statement = require_object(payload.get("statement_receipt"), "source statement receipt", layer="source_receipt")
    metrics = require_object(payload.get("receipt_metrics"), "source receipt metrics", layer="source_receipt")
    return {
        "schema": payload["schema"],
        "issue": payload["issue"],
        "source_issue": payload["source_issue"],
        "decision": payload["decision"],
        "result": payload["result"],
        "claim_boundary": payload["claim_boundary"],
        "source_payload_sha256": sha256_bytes(canonical_json_bytes(payload)),
        "source_file_sha256": sha256_file(SOURCE_RECEIPT_EVIDENCE),
        "statement_commitment": statement["statement_commitment"],
        "receipt_commitment": statement["receipt_commitment"],
        "public_signals_sha256": statement["public_signals_sha256"],
        "proof_sha256": statement["proof_sha256"],
        "verification_key_sha256": statement["verification_key_sha256"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "public_signal_count": metrics["public_signal_count"],
    }


def command_text(command: list[str]) -> str:
    return " ".join(command)


def run_command(
    command: list[str],
    *,
    cwd: pathlib.Path | None = None,
    timeout_s: float = 120.0,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as err:
        output = (err.stdout or "") if isinstance(err.stdout, str) else ""
        stderr = (err.stderr or "") if isinstance(err.stderr, str) else ""
        detail = "\n".join(part for part in (output, stderr) if part).strip()
        raise D128SnarkTimingSetupError(
            f"command timed out after {timeout_s}s: {command_text(command)}: {detail}",
            layer="external_proof_tooling",
        ) from err
    except (OSError, subprocess.CalledProcessError) as err:
        detail = getattr(err, "stderr", "") or str(err)
        raise D128SnarkTimingSetupError(f"command failed: {command_text(command)}: {detail}", layer="external_proof_tooling") from err


def timed_command(command: list[str], *, cwd: pathlib.Path | None = None, timeout_s: float = 120.0) -> float:
    started = time.perf_counter_ns()
    run_command(command, cwd=cwd, timeout_s=timeout_s)
    elapsed = time.perf_counter_ns() - started
    return elapsed / 1_000_000


def tool_versions() -> dict[str, str]:
    if not SNARKJS.is_file():
        raise D128SnarkTimingSetupError("repo-local snarkjs missing; run `npm ci --prefix scripts`", layer="external_proof_tooling")
    snarkjs_result = subprocess.run(
        [str(SNARKJS), "--version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    snarkjs_output = ANSI_ESCAPE_RE.sub("", f"{snarkjs_result.stdout}\n{snarkjs_result.stderr}")
    if f"snarkjs@{SNARKJS_VERSION}" not in snarkjs_output and SNARKJS_VERSION not in snarkjs_output.split():
        raise D128SnarkTimingSetupError("snarkjs version mismatch", layer="external_proof_tooling")
    circom_output = ANSI_ESCAPE_RE.sub("", run_command(["circom", "--version"], timeout_s=10).stdout.strip())
    if f"circom compiler {CIRCOM_VERSION}" not in circom_output and CIRCOM_VERSION not in circom_output.split():
        raise D128SnarkTimingSetupError("circom version mismatch", layer="external_proof_tooling")
    node_output = run_command(["node", "--version"], timeout_s=10).stdout.strip()
    if node_output != NODE_VERSION:
        raise D128SnarkTimingSetupError("node version mismatch", layer="external_proof_tooling")
    npm_output = run_command(["npm", "--version"], timeout_s=10).stdout.strip()
    if npm_output != NPM_VERSION:
        raise D128SnarkTimingSetupError("npm version mismatch", layer="external_proof_tooling")
    return {
        "snarkjs": f"snarkjs@{SNARKJS_VERSION}",
        "circom": f"circom compiler {CIRCOM_VERSION}",
        "node": NODE_VERSION,
        "npm": NPM_VERSION,
    }


def metric_summary(samples: list[float]) -> dict[str, Any]:
    rounded = [round(value, 3) for value in samples]
    return {
        "sample_count": len(samples),
        "median_ms": round(statistics.median(samples), 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
        "all_samples_ms": rounded,
    }


def build_throwaway_setup(work: pathlib.Path) -> tuple[dict[str, Any], pathlib.Path, pathlib.Path, pathlib.Path]:
    build = work / "build"
    build.mkdir()
    shutil.copy2(CIRCUIT, work / CIRCUIT.name)
    shutil.copy2(INPUT, work / INPUT.name)
    setup_started = time.perf_counter_ns()
    run_command(["circom", str(work / CIRCUIT.name), "--r1cs", "--wasm", "--sym", "-o", str(build)], timeout_s=120)
    r1cs = build / "d128_statement_receipt.r1cs"
    wasm = build / "d128_statement_receipt_js" / "d128_statement_receipt.wasm"
    witness_js = build / "d128_statement_receipt_js" / "generate_witness.js"
    pot0 = work / "pot12_0000.ptau"
    pot1 = work / "pot12_0001.ptau"
    pot_final = work / "pot12_final.ptau"
    zkey0 = work / "statement_0000.zkey"
    zkey_final = work / "statement_final.zkey"
    verification_key = work / "verification_key.json"
    run_command([str(SNARKJS), "powersoftau", "new", "bn128", str(POT_POWER), str(pot0), "-v"], timeout_s=120)
    run_command([
        str(SNARKJS), "powersoftau", "contribute", str(pot0), str(pot1),
        "--name=ptvm timing smoke", "-e=ptvm timing smoke entropy", "-v",
    ], timeout_s=120)
    run_command([str(SNARKJS), "powersoftau", "prepare", "phase2", str(pot1), str(pot_final), "-v"], timeout_s=120)
    run_command([str(SNARKJS), "groth16", "setup", str(r1cs), str(pot_final), str(zkey0)], timeout_s=120)
    run_command([
        str(SNARKJS), "zkey", "contribute", str(zkey0), str(zkey_final),
        "--name=ptvm timing zkey", "-e=ptvm timing zkey entropy",
    ], timeout_s=120)
    run_command([str(SNARKJS), "zkey", "export", "verificationkey", str(zkey_final), str(verification_key)], timeout_s=120)
    setup_elapsed_ms = (time.perf_counter_ns() - setup_started) / 1_000_000
    metadata = {
        "setup_time_ms_single_run": round(setup_elapsed_ms, 3),
        "r1cs_sha256": sha256_file(r1cs),
        "wasm_sha256": sha256_file(wasm),
        "verification_key_sha256": sha256_bytes(canonical_json_bytes(load_json(verification_key))),
        "verification_key_file_sha256": sha256_file(verification_key),
        "verification_key_bytes": verification_key.stat().st_size,
    }
    return metadata, zkey_final, verification_key, witness_js


def run_proof_generation_sample(work: pathlib.Path, zkey: pathlib.Path, witness_js: pathlib.Path, index: int) -> tuple[float, pathlib.Path, pathlib.Path]:
    witness = work / f"witness_{index}.wtns"
    proof = work / f"proof_{index}.json"
    public = work / f"public_{index}.json"
    run_command(["node", str(witness_js), str(witness_js.parent / "d128_statement_receipt.wasm"), str(work / INPUT.name), str(witness)], timeout_s=60)
    started = time.perf_counter_ns()
    run_command([str(SNARKJS), "groth16", "prove", str(zkey), str(witness), str(proof), str(public)], timeout_s=60)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    expect_equal(load_json(public), load_json(SOURCE_PUBLIC), "generated public signals", layer="artifact_binding")
    return elapsed_ms, proof, public


def run_external_measurements() -> dict[str, Any]:
    versions = tool_versions()
    with tempfile.TemporaryDirectory(dir=EVIDENCE_DIR) as raw_tmp:
        work = pathlib.Path(raw_tmp)
        setup_metadata, zkey, verification_key, witness_js = build_throwaway_setup(work)
        proof_samples: list[float] = []
        verify_samples: list[float] = []
        proof_sizes: list[int] = []
        generated_public_hashes: list[str] = []
        generated_proof_hashes: list[str] = []
        for index in range(SAMPLE_COUNT):
            proof_ms, proof, public = run_proof_generation_sample(work, zkey, witness_js, index)
            proof_samples.append(proof_ms)
            proof_sizes.append(proof.stat().st_size)
            generated_public_hashes.append(sha256_bytes(canonical_json_bytes(load_json(public))))
            generated_proof_hashes.append(sha256_file(proof))
            verify_samples.append(timed_command([str(SNARKJS), "groth16", "verify", str(verification_key), str(public), str(proof)], timeout_s=60))
        return {
            "tool_versions": versions,
            "setup_metadata": setup_metadata,
            "proof_generation": metric_summary(proof_samples),
            "verification": metric_summary(verify_samples),
            "artifact_binding": {
                "source_public_sha256": sha256_file(SOURCE_PUBLIC),
                "source_public_payload_sha256": sha256_bytes(canonical_json_bytes(load_json(SOURCE_PUBLIC))),
                "source_proof_bytes": SOURCE_PROOF.stat().st_size,
                "source_verification_key_bytes": SOURCE_VK.stat().st_size,
                "generated_public_payload_sha256_values": sorted(set(generated_public_hashes)),
                "generated_proof_file_sha256_values": sorted(set(generated_proof_hashes)),
                "generated_proof_size_bytes_values": sorted(set(proof_sizes)),
                "generated_verification_key_file_sha256": setup_metadata["verification_key_file_sha256"],
            },
        }


def timing_metrics(measurements: dict[str, Any]) -> dict[str, Any]:
    proof = require_object(measurements.get("proof_generation"), "proof generation measurements", layer="timing_metrics")
    verify = require_object(measurements.get("verification"), "verification measurements", layer="timing_metrics")
    setup = require_object(measurements.get("setup_metadata"), "setup metadata", layer="setup_policy")
    artifact = require_object(measurements.get("artifact_binding"), "artifact binding", layer="artifact_binding")
    return {
        "timing_policy": TIMING_POLICY,
        "sample_count": SAMPLE_COUNT,
        "proof_generation_time_ms_median": proof["median_ms"],
        "proof_generation_time_ms_min": proof["min_ms"],
        "proof_generation_time_ms_max": proof["max_ms"],
        "proof_generation_time_ms_samples": proof["all_samples_ms"],
        "verifier_time_ms_median": verify["median_ms"],
        "verifier_time_ms_min": verify["min_ms"],
        "verifier_time_ms_max": verify["max_ms"],
        "verifier_time_ms_samples": verify["all_samples_ms"],
        "setup_time_ms_single_run": setup["setup_time_ms_single_run"],
        "proof_size_bytes_values": artifact["generated_proof_size_bytes_values"],
        "verification_key_bytes": setup["verification_key_bytes"],
    }


def build_payload(measurements: dict[str, Any] | None = None) -> dict[str, Any]:
    measurements = run_external_measurements() if measurements is None else copy.deepcopy(measurements)
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "source_contract_issue": SOURCE_CONTRACT_ISSUE,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_receipt": source_receipt_summary(),
        "setup_policy": copy.deepcopy(SETUP_POLICY),
        "tool_versions": copy.deepcopy(measurements["tool_versions"]),
        "timing_metrics": timing_metrics(measurements),
        "artifact_binding": copy.deepcopy(measurements["artifact_binding"]),
        "setup_metadata": copy.deepcopy(measurements["setup_metadata"]),
        "mutation_inventory": [{"mutation": name, "surface": surface} for name, surface in EXPECTED_MUTATION_INVENTORY],
        "case_count": len(EXPECTED_MUTATION_INVENTORY),
        "all_mutations_rejected": True,
        "cases": [],
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "repro": {"git_commit": _git_commit(), "command": GATE_COMMAND},
        "summary": (
            "The d128 #428 SNARK statement receipt can be regenerated under a local throwaway Groth16 setup, "
            "proved, and verified with median-of-5 timing evidence. The setup remains explicitly non-production."
        ),
    }
    payload["cases"] = mutation_cases(payload)
    payload["case_count"] = len(payload["cases"])
    payload["all_mutations_rejected"] = all(case["rejected"] for case in payload["cases"])
    validate_payload(payload)
    return payload


def _core_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in payload.items() if key not in {"cases", "case_count", "all_mutations_rejected", "mutation_inventory"}}


def mutation_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = _core_payload(payload)

    def add(name: str, surface: str, mutate: Any) -> dict[str, Any]:
        mutated = copy.deepcopy(baseline)
        mutate(mutated)
        try:
            validate_core_payload(mutated)
        except D128SnarkTimingSetupError as err:
            return {"mutation": name, "surface": surface, "rejected": True, "rejection_layer": err.layer, "error": str(err)}
        return {"mutation": name, "surface": surface, "rejected": False, "rejection_layer": "accepted", "error": ""}

    return [
        add("source_receipt_decision_relabeling", "source_receipt", lambda p: p["source_receipt"].__setitem__("decision", "GO_FAKE")),
        add("source_receipt_claim_boundary_relabeling", "source_receipt", lambda p: p["source_receipt"].__setitem__("claim_boundary", "RECURSION_PROVEN")),
        add("source_receipt_metric_relabeling", "source_receipt", lambda p: p["source_receipt"].__setitem__("proof_size_bytes", 1)),
        add("setup_policy_promoted_to_production", "setup_policy", lambda p: p["setup_policy"].__setitem__("production_trusted_setup", True)),
        add("setup_policy_proving_key_checked_in_relabeling", "setup_policy", lambda p: p["setup_policy"].__setitem__("proving_key_checked_in", True)),
        add("node_version_relabeling", "external_proof_tooling", lambda p: p["tool_versions"].__setitem__("node", "v0.0.0")),
        add("npm_version_relabeling", "external_proof_tooling", lambda p: p["tool_versions"].__setitem__("npm", "0.0.0")),
        add("timing_policy_relabeling", "timing_metrics", lambda p: p["timing_metrics"].__setitem__("timing_policy", "single_run")),
        add("proof_generation_metric_smuggled", "timing_metrics", lambda p: p["timing_metrics"].__setitem__("proof_generation_time_ms_median", 0.001)),
        add("verifier_metric_smuggled", "timing_metrics", lambda p: p["timing_metrics"].__setitem__("verifier_time_ms_median", 0.001)),
        add("public_signal_hash_relabeling", "artifact_binding", lambda p: p["artifact_binding"].__setitem__("source_public_sha256", "0" * 64)),
        add("generated_public_hash_relabeling", "artifact_binding", lambda p: p["artifact_binding"].__setitem__("generated_public_payload_sha256_values", ["1" * 64])),
        add("generated_vk_hash_relabeling", "artifact_binding", lambda p: p["setup_metadata"].__setitem__("verification_key_file_sha256", "2" * 64)),
        add("proof_size_relabeling", "artifact_binding", lambda p: p["artifact_binding"].__setitem__("generated_proof_size_bytes_values", [1])),
        add("generated_size_equivalence_relabeling", "setup_policy", lambda p: p["setup_policy"].__setitem__("generated_artifact_sizes_may_differ_from_source", False)),
        add("repro_command_relabeling", "parser_or_schema", lambda p: p["repro"].__setitem__("command", "python3 scripts/fake.py")),
        add("non_claims_removed", "parser_or_schema", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1])),
        add("validation_command_removed", "parser_or_schema", lambda p: p.__setitem__("validation_commands", p["validation_commands"][:-1])),
        add("unknown_top_level_field_added", "parser_or_schema", lambda p: p.__setitem__("unknown", True)),
    ]


def validate_core_payload(payload: dict[str, Any]) -> None:
    expected_keys = {
        "schema", "issue", "source_issue", "source_contract_issue", "decision", "result", "claim_boundary",
        "source_receipt", "setup_policy", "tool_versions", "timing_metrics", "artifact_binding", "setup_metadata",
        "non_claims", "validation_commands", "repro", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    expect_equal(payload["schema"], SCHEMA, "schema")
    expect_equal(payload["issue"], ISSUE, "issue")
    expect_equal(payload["source_issue"], SOURCE_ISSUE, "source issue")
    expect_equal(payload["source_contract_issue"], SOURCE_CONTRACT_ISSUE, "source contract issue")
    expect_equal(payload["decision"], DECISION, "decision")
    expect_equal(payload["result"], RESULT, "result")
    expect_equal(payload["claim_boundary"], CLAIM_BOUNDARY, "claim boundary")
    expect_equal(payload["source_receipt"], source_receipt_summary(), "source receipt", layer="source_receipt")
    expect_equal(payload["setup_policy"], SETUP_POLICY, "setup policy", layer="setup_policy")
    expect_equal(payload["non_claims"], NON_CLAIMS, "non claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation commands")
    tool_versions_value = require_object(payload["tool_versions"], "tool versions", layer="external_proof_tooling")
    expect_equal(tool_versions_value.get("snarkjs"), f"snarkjs@{SNARKJS_VERSION}", "snarkjs version", layer="external_proof_tooling")
    expect_equal(tool_versions_value.get("circom"), f"circom compiler {CIRCOM_VERSION}", "circom version", layer="external_proof_tooling")
    expect_equal(tool_versions_value.get("node"), NODE_VERSION, "node version", layer="external_proof_tooling")
    expect_equal(tool_versions_value.get("npm"), NPM_VERSION, "npm version", layer="external_proof_tooling")
    metrics = require_object(payload["timing_metrics"], "timing metrics", layer="timing_metrics")
    expect_equal(metrics.get("timing_policy"), TIMING_POLICY, "timing policy", layer="timing_metrics")
    expect_equal(metrics.get("sample_count"), SAMPLE_COUNT, "sample count", layer="timing_metrics")
    for field in (
        "proof_generation_time_ms_median", "proof_generation_time_ms_min", "proof_generation_time_ms_max",
        "verifier_time_ms_median", "verifier_time_ms_min", "verifier_time_ms_max", "setup_time_ms_single_run",
    ):
        value = metrics.get(field)
        if not isinstance(value, (int, float)) or value <= 0:
            raise D128SnarkTimingSetupError(f"{field} must be positive", layer="timing_metrics")
    if len(require_list(metrics.get("proof_generation_time_ms_samples"), "proof samples", layer="timing_metrics")) != SAMPLE_COUNT:
        raise D128SnarkTimingSetupError("proof sample count mismatch", layer="timing_metrics")
    if len(require_list(metrics.get("verifier_time_ms_samples"), "verify samples", layer="timing_metrics")) != SAMPLE_COUNT:
        raise D128SnarkTimingSetupError("verify sample count mismatch", layer="timing_metrics")
    proof_summary = metric_summary(metrics["proof_generation_time_ms_samples"])
    expect_equal(metrics["proof_generation_time_ms_median"], proof_summary["median_ms"], "proof generation median", layer="timing_metrics")
    expect_equal(metrics["proof_generation_time_ms_min"], proof_summary["min_ms"], "proof generation min", layer="timing_metrics")
    expect_equal(metrics["proof_generation_time_ms_max"], proof_summary["max_ms"], "proof generation max", layer="timing_metrics")
    verify_summary = metric_summary(metrics["verifier_time_ms_samples"])
    expect_equal(metrics["verifier_time_ms_median"], verify_summary["median_ms"], "verifier median", layer="timing_metrics")
    expect_equal(metrics["verifier_time_ms_min"], verify_summary["min_ms"], "verifier min", layer="timing_metrics")
    expect_equal(metrics["verifier_time_ms_max"], verify_summary["max_ms"], "verifier max", layer="timing_metrics")
    artifact = require_object(payload["artifact_binding"], "artifact binding", layer="artifact_binding")
    expect_equal(artifact.get("source_public_sha256"), sha256_file(SOURCE_PUBLIC), "source public file hash", layer="artifact_binding")
    expect_equal(
        artifact.get("source_public_payload_sha256"),
        sha256_bytes(canonical_json_bytes(load_json(SOURCE_PUBLIC))),
        "source public payload hash",
        layer="artifact_binding",
    )
    expect_equal(artifact.get("source_proof_bytes"), SOURCE_PROOF.stat().st_size, "source proof size", layer="artifact_binding")
    expect_equal(artifact.get("source_verification_key_bytes"), SOURCE_VK.stat().st_size, "source vk size", layer="artifact_binding")
    generated_public_hashes = require_list(artifact.get("generated_public_payload_sha256_values"), "generated public hashes", layer="artifact_binding")
    expect_equal(generated_public_hashes, [artifact["source_public_payload_sha256"]], "generated public hashes", layer="artifact_binding")
    proof_size_values = require_list(artifact.get("generated_proof_size_bytes_values"), "proof size values", layer="artifact_binding")
    if proof_size_values != metrics.get("proof_size_bytes_values") or any(not isinstance(value, int) or value <= 0 for value in proof_size_values):
        raise D128SnarkTimingSetupError("proof size values mismatch", layer="artifact_binding")
    generated_proof_hashes = require_list(artifact.get("generated_proof_file_sha256_values"), "generated proof hashes", layer="artifact_binding")
    if len(generated_proof_hashes) < 1 or any(not isinstance(value, str) or len(value) != 64 for value in generated_proof_hashes):
        raise D128SnarkTimingSetupError("generated proof hashes malformed", layer="artifact_binding")
    setup = require_object(payload["setup_metadata"], "setup metadata", layer="setup_policy")
    for field in ("r1cs_sha256", "wasm_sha256", "verification_key_sha256", "verification_key_file_sha256"):
        value = setup.get(field)
        if not isinstance(value, str) or len(value) != 64:
            raise D128SnarkTimingSetupError(f"{field} malformed", layer="setup_policy")
    expect_equal(setup.get("verification_key_bytes"), metrics.get("verification_key_bytes"), "setup vk bytes", layer="setup_policy")
    expect_equal(
        setup.get("verification_key_file_sha256"),
        artifact.get("generated_verification_key_file_sha256"),
        "generated verification key hash",
        layer="artifact_binding",
    )
    repro = require_object(payload["repro"], "repro")
    expect_keys(repro, {"git_commit", "command"}, "repro")
    expect_equal(repro.get("command"), GATE_COMMAND, "repro command")
    git_commit = repro.get("git_commit")
    if git_commit != "unknown":
        if not isinstance(git_commit, str) or len(git_commit) != 40:
            raise D128SnarkTimingSetupError("git commit malformed")
        try:
            int(git_commit, 16)
        except ValueError as err:
            raise D128SnarkTimingSetupError("git commit malformed") from err


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "payload")
    expected_keys = {
        "schema", "issue", "source_issue", "source_contract_issue", "decision", "result", "claim_boundary",
        "source_receipt", "setup_policy", "tool_versions", "timing_metrics", "artifact_binding", "setup_metadata",
        "mutation_inventory", "case_count", "all_mutations_rejected", "cases", "non_claims",
        "validation_commands", "repro", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    validate_core_payload(_core_payload(payload))
    inventory = require_list(payload["mutation_inventory"], "mutation inventory")
    expect_equal(tuple((item.get("mutation"), item.get("surface")) for item in inventory), EXPECTED_MUTATION_INVENTORY, "mutation inventory")
    cases = require_list(payload["cases"], "cases")
    expect_equal(payload["case_count"], len(cases), "case count")
    expect_equal(len(cases), len(EXPECTED_MUTATION_INVENTORY), "case length")
    by_name = {case.get("mutation"): case for case in cases}
    expect_equal(set(by_name), EXPECTED_MUTATION_SET, "case mutation set")
    for mutation, surface in EXPECTED_MUTATION_INVENTORY:
        case = by_name[mutation]
        expect_equal(case.get("surface"), surface, f"surface {mutation}")
        if case.get("rejected") is not True:
            raise D128SnarkTimingSetupError(f"mutation accepted: {mutation}", layer="mutation_suite")
    if payload["all_mutations_rejected"] is not True:
        raise D128SnarkTimingSetupError("not all mutations rejected", layer="mutation_suite")


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    rows = {
        "setup": [payload["timing_metrics"]["setup_time_ms_single_run"]],
        "proof_generation": payload["timing_metrics"]["proof_generation_time_ms_samples"],
        "verification": payload["timing_metrics"]["verifier_time_ms_samples"],
    }
    for metric, samples in rows.items():
        summary = metric_summary(samples)
        writer.writerow(
            {
                "metric": metric,
                "sample_count": summary["sample_count"],
                "median_ms": summary["median_ms"],
                "min_ms": summary["min_ms"],
                "max_ms": summary["max_ms"],
                "all_samples_ms": ",".join(f"{value:.3f}" for value in summary["all_samples_ms"]),
                "timing_policy": payload["timing_metrics"]["timing_policy"],
                "setup_policy": payload["setup_policy"]["setup_class"],
            }
        )
    return output.getvalue()


def write_text_checked(path: pathlib.Path, text: str) -> None:
    resolved = path.resolve()
    root = EVIDENCE_DIR.resolve()
    if resolved != root and root not in resolved.parents:
        raise D128SnarkTimingSetupError(f"output path must stay under {EVIDENCE_DIR}", layer="output_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def resolve_output_path(path: pathlib.Path | None) -> pathlib.Path | None:
    if path is None:
        return None
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    if resolved.exists() and resolved.is_dir():
        raise D128SnarkTimingSetupError("output path must be a file, not a directory", layer="output_path")
    return resolved


def resolve_output_paths(json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> tuple[pathlib.Path | None, pathlib.Path | None]:
    resolved_json = resolve_output_path(json_path)
    resolved_tsv = resolve_output_path(tsv_path)
    if resolved_json is not None and resolved_tsv is not None and resolved_json == resolved_tsv:
        raise D128SnarkTimingSetupError("JSON and TSV outputs must be distinct", layer="output_path")
    return resolved_json, resolved_tsv


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload()
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tsv_text = to_tsv(payload)
    json_path, tsv_path = resolve_output_paths(args.write_json, args.write_tsv)
    if json_path is not None:
        write_text_checked(json_path, json_text)
    else:
        print(json_text, end="")
    if tsv_path is not None:
        write_text_checked(tsv_path, tsv_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
