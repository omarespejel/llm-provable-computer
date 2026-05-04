#!/usr/bin/env python3
"""Generate or verify the d128 RISC Zero statement receipt.

This gate answers issue #433. It takes the #422 zkVM journal contract for the
#424 d128 proof-native two-slice public-input contract and proves that a RISC
Zero guest committed those exact journal bytes publicly.

The guest is intentionally small: it reads the canonical journal bytes and
commits them. This is a statement-binding receipt, not recursive verification of
the underlying Stwo slice proofs inside RISC Zero.
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
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
ADAPTER_SCRIPT = ROOT / "scripts" / "zkai_d128_zkvm_statement_receipt_adapter_gate.py"
PROGRAM_DIR = ROOT / "programs" / "risc0-d128-statement-receipt"
PROGRAM_MANIFEST = PROGRAM_DIR / "Cargo.toml"
RECEIPT_OUT = EVIDENCE_DIR / "zkai-d128-risc0-statement-receipt-2026-05.bincode"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-risc0-statement-receipt-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-risc0-statement-receipt-2026-05.tsv"

SCHEMA = "zkai-d128-zkvm-statement-receipt-candidate-v1"
EVIDENCE_SCHEMA = "zkai-d128-risc0-statement-receipt-gate-v1"
ISSUE = 433
SOURCE_ISSUE = 424
ADAPTER_ISSUE = 422
ROUTE_ID = "risc0_zkvm_statement_receipt"
SYSTEM = "RISC Zero"
RESULT = "GO"
DECISION = "GO_D128_RISC0_STATEMENT_RECEIPT_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT"
CLAIM_BOUNDARY = "RISC0_STATEMENT_RECEIPT_BINDS_D128_TWO_SLICE_JOURNAL_NOT_RECURSION"
RISC0_ZKVM_VERSION = "3.0.5"
RZUP_VERSION = "0.5.0"
REQUIRED_COMMANDS = ("rzup", "cargo-risczero", "cargo", "rustc")
MAX_RECEIPT_BYTES = 2_000_000
GO_CRITERION = (
    "RISC Zero host proves or verifies a receipt whose journal decodes to the exact #422 journal "
    "contract, and the checked evidence rejects relabeling of bound statement fields"
)
NON_CLAIMS = [
    "not recursive verification of the underlying Stwo slice proofs inside RISC Zero",
    "not end-to-end zkML inference proving",
    "not a public zkML benchmark row",
    "not a Starknet deployment result",
    "not a claim that RISC Zero is faster or slower than the native Stwo route",
]

VALIDATION_COMMANDS = [
    "PATH=\"$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH\" python3 scripts/zkai_d128_risc0_statement_receipt_gate.py --verify-existing --write-json docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.tsv",
    "PATH=\"$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH\" python3 -m unittest scripts.tests.test_zkai_d128_risc0_statement_receipt_gate",
    "python3 -m py_compile scripts/zkai_d128_risc0_statement_receipt_gate.py scripts/tests/test_zkai_d128_risc0_statement_receipt_gate.py",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
]

TSV_COLUMNS = (
    "route_id",
    "system",
    "decision",
    "receipt_size_bytes",
    "proof_generation_time_ms",
    "verifier_time_ms",
    "journal_commitment",
    "receipt_commitment",
    "image_id_hex",
)

EXPECTED_MUTATION_INVENTORY = (
    ("model_or_program_identity_relabeling", "journal_contract"),
    ("input_commitment_relabeling", "journal_contract"),
    ("output_commitment_relabeling", "journal_contract"),
    ("policy_label_relabeling", "journal_contract"),
    ("action_label_relabeling", "journal_contract"),
    ("verifier_domain_relabeling", "journal_contract"),
    ("source_file_hash_relabeling", "journal_contract"),
    ("source_payload_hash_relabeling", "journal_contract"),
    ("journal_commitment_relabeling", "journal_contract"),
    ("route_id_relabeling", "receipt_metadata"),
    ("system_relabeling", "receipt_metadata"),
    ("image_id_relabeling", "receipt_metadata"),
    ("receipt_commitment_relabeling", "receipt_metadata"),
    ("receipt_size_metric_smuggling", "proof_metrics"),
    ("proof_generation_metric_smuggling", "proof_metrics"),
    ("verifier_time_metric_smuggling", "proof_metrics"),
    ("decision_relabeling", "parser_or_schema"),
    ("non_claim_removed", "parser_or_schema"),
    ("validation_command_removed", "parser_or_schema"),
    ("unknown_field_added", "parser_or_schema"),
)
EXPECTED_MUTATION_SET = {name for name, _surface in EXPECTED_MUTATION_INVENTORY}


class D128Risc0StatementReceiptError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128Risc0StatementReceiptError(f"failed to load {module_name} from {path}", layer="source_contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ADAPTER = _load_module(ADAPTER_SCRIPT, "zkai_d128_zkvm_adapter_for_risc0_receipt")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blake2b_commitment_bytes(data: bytes) -> str:
    return f"blake2b-256:{hashlib.blake2b(data, digest_size=32).hexdigest()}"


def commitment(value: Any) -> str:
    return blake2b_commitment_bytes(canonical_json_bytes(value))


def require_object(value: Any, label: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128Risc0StatementReceiptError(f"{label} must be an object", layer=layer)
    return value


def require_list(value: Any, label: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise D128Risc0StatementReceiptError(f"{label} must be a list", layer=layer)
    return value


def expect_equal(actual: Any, expected: Any, label: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise D128Risc0StatementReceiptError(f"{label} mismatch", layer=layer)


def expect_keys(value: dict[str, Any], expected: set[str], label: str, *, layer: str = "parser_or_schema") -> None:
    keys = set(value)
    if keys != expected:
        raise D128Risc0StatementReceiptError(
            f"{label} keys mismatch: missing={sorted(expected - keys)} extra={sorted(keys - expected)}",
            layer=layer,
        )


def load_json(path: pathlib.Path, *, layer: str = "parser_or_schema") -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128Risc0StatementReceiptError(f"failed to load JSON {path}: {err}", layer=layer) from err


def command_entry(command_id: str, command: tuple[str, ...]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    entry = {
        "command_id": command_id,
        "command": list(command),
        "available": executable is not None,
        "returncode": None,
        "stdout": "",
        "stderr": "",
    }
    if executable is not None:
        try:
            result = subprocess.run(list(command), check=False, text=True, capture_output=True, timeout=20, cwd=ROOT)
            entry["returncode"] = result.returncode
            entry["stdout"] = result.stdout.strip()
            entry["stderr"] = result.stderr.strip()
            if result.returncode != 0:
                entry["available"] = False
        except (OSError, subprocess.SubprocessError) as err:
            entry["available"] = False
            entry["stderr"] = str(err)
    return entry


def toolchain_probe() -> dict[str, Any]:
    commands = {
        "rzup": command_entry("rzup", ("rzup", "--version")),
        "cargo-risczero": command_entry("cargo-risczero", ("cargo", "risczero", "--version")),
        "cargo": command_entry("cargo", ("cargo", "--version")),
        "rustc": command_entry("rustc", ("rustc", "--version")),
    }
    return {
        "probe_scope": "local_risc0_receipt_generation_and_verification",
        "host_os": sys.platform,
        "commands": commands,
        "rzup_components": rzup_components(),
    }


def rzup_components() -> dict[str, str]:
    if shutil.which("rzup") is None:
        return {}
    result = subprocess.run(["rzup", "show"], check=False, text=True, capture_output=True, timeout=20, cwd=ROOT)
    components: dict[str, str] = {}
    current_name: str | None = None
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("-") or line.startswith("Installed components") or line.startswith("rzup home"):
            continue
        if not line.startswith("*"):
            current_name = line
            continue
        if current_name is not None:
            components[current_name] = line.removeprefix("*").strip()
            current_name = None
    return components


def expected_journal_contract() -> dict[str, Any]:
    return ADAPTER.journal_contract()


def expected_journal_bytes() -> bytes:
    return canonical_json_bytes(expected_journal_contract()) + b"\n"


def run_host(mode: str, journal_path: pathlib.Path, receipt_path: pathlib.Path, summary_path: pathlib.Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PATH"] = f"{os.environ.get('HOME', '')}/.risc0/bin:{os.environ.get('HOME', '')}/.cargo/bin:" + env.get("PATH", "")
    env.setdefault("CARGO_TARGET_DIR", str(ROOT / "target" / "risc0-d128-statement-receipt"))
    env["RISC0_DEV_MODE"] = "0"
    command = [
        "cargo",
        "run",
        "--release",
        "--quiet",
        "--manifest-path",
        str(PROGRAM_MANIFEST),
        "-p",
        "host",
        "--",
        mode,
        str(journal_path),
        str(receipt_path),
        str(summary_path),
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True, timeout=900, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise D128Risc0StatementReceiptError(
            f"RISC Zero host {mode} failed: stdout={result.stdout[-2000:]} stderr={result.stderr[-4000:]}",
            layer="risc0_host",
        )
    return require_object(load_json(summary_path, layer="risc0_host"), "RISC Zero host summary", layer="risc0_host")


def generate_or_verify_receipt(*, prove: bool, receipt_path: pathlib.Path) -> dict[str, Any]:
    target_root = ROOT / "target"
    target_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_root) as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        journal_path = tmp / "journal.json"
        summary_path = tmp / "summary.json"
        journal_path.write_bytes(expected_journal_bytes())
        if prove:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            return run_host("prove", journal_path, receipt_path, summary_path)
        if not receipt_path.is_file():
            raise D128Risc0StatementReceiptError(f"receipt artifact is missing: {receipt_path}", layer="receipt_artifact")
        return run_host("verify", journal_path, receipt_path, summary_path)


def build_payload(
    *,
    prove: bool = False,
    receipt_path: pathlib.Path = RECEIPT_OUT,
    previous_proof_generation_time_ms: float | None = None,
) -> dict[str, Any]:
    journal = expected_journal_contract()
    journal_bytes = expected_journal_bytes()
    host_summary = generate_or_verify_receipt(prove=prove, receipt_path=receipt_path)
    receipt_bytes = receipt_path.read_bytes()
    if len(receipt_bytes) <= 0 or len(receipt_bytes) > MAX_RECEIPT_BYTES:
        raise D128Risc0StatementReceiptError("receipt artifact size outside allowed bound", layer="receipt_artifact")
    receipt_commitment = blake2b_commitment_bytes(receipt_bytes)
    proof_generation_time_ms = host_summary.get("prove_time_ms")
    if proof_generation_time_ms is None:
        proof_generation_time_ms = previous_proof_generation_time_ms
    proof_metrics = {
        "metrics_enabled": True,
        "timing_policy": "single_local_run_engineering_only",
        "proof_size_bytes": len(receipt_bytes),
        "proof_generation_time_ms": proof_generation_time_ms,
        "verifier_time_ms": host_summary["verify_time_ms"],
    }
    payload = {
        "schema": SCHEMA,
        "evidence_schema": EVIDENCE_SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "adapter_issue": ADAPTER_ISSUE,
        "result": RESULT,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "route_id": ROUTE_ID,
        "system": SYSTEM,
        "journal_commitment": journal["journal_commitment"],
        "receipt_commitment": receipt_commitment,
        "journal_contract": journal,
        "receipt_artifact": {
            "path": str(receipt_path.relative_to(ROOT)),
            "size_bytes": len(receipt_bytes),
            "sha256": sha256_bytes(receipt_bytes),
            "commitment": receipt_commitment,
        },
        "receipt_verification": {
            "host_summary_schema": host_summary["schema"],
            "host_summary_mode": host_summary["mode"],
            "verifier_executed": True,
            "receipt_verified": True,
            "decoded_journal_matches_expected": True,
            "image_id_hex": host_summary["image_id_hex"],
            "journal_sha256": host_summary["journal_sha256"],
            "receipt_sha256": host_summary["receipt_sha256"],
            "risc0_zkvm_version": host_summary["risc0_zkvm_version"],
        },
        "toolchain_probe": toolchain_probe(),
        "proof_metrics": proof_metrics,
        "go_criterion": GO_CRITERION,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_inventory": [{"mutation": name, "surface": surface} for name, surface in EXPECTED_MUTATION_INVENTORY],
        "case_count": len(EXPECTED_MUTATION_INVENTORY),
        "all_mutations_rejected": True,
        "cases": [],
        "summary": {
            "journal_commitment": journal["journal_commitment"],
            "image_id_hex": host_summary["image_id_hex"],
            "receipt_commitment": receipt_commitment,
            "receipt_size_bytes": len(receipt_bytes),
            "proof_generation_time_ms": proof_generation_time_ms,
            "verifier_time_ms": host_summary["verify_time_ms"],
        },
    }
    expected_journal_sha = sha256_bytes(journal_bytes)
    expect_equal(host_summary["journal_sha256"], expected_journal_sha, "host journal sha256", layer="risc0_host")
    expect_equal(host_summary["receipt_sha256"], sha256_bytes(receipt_bytes), "host receipt sha256", layer="risc0_host")
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
        except D128Risc0StatementReceiptError as err:
            return {"mutation": name, "surface": surface, "rejected": True, "rejection_layer": err.layer, "error": str(err)}
        return {"mutation": name, "surface": surface, "rejected": False, "rejection_layer": "accepted", "error": ""}

    return [
        add("model_or_program_identity_relabeling", "journal_contract", lambda p: p["journal_contract"]["model_or_program_identity"].__setitem__("statement_family", "fake")),
        add("input_commitment_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("input_commitment", "blake2b-256:" + "00" * 32)),
        add("output_commitment_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("output_commitment", "blake2b-256:" + "11" * 32)),
        add("policy_label_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("policy_label", "fake-policy")),
        add("action_label_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("action_label", "fake-action")),
        add("verifier_domain_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("verifier_domain", "fake-domain")),
        add("source_file_hash_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("source_file_sha256", "0" * 64)),
        add("source_payload_hash_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("source_payload_sha256", "1" * 64)),
        add("journal_commitment_relabeling", "journal_contract", lambda p: p.__setitem__("journal_commitment", "blake2b-256:" + "22" * 32)),
        add("route_id_relabeling", "receipt_metadata", lambda p: p.__setitem__("route_id", "sp1_zkvm_statement_receipt")),
        add("system_relabeling", "receipt_metadata", lambda p: p.__setitem__("system", "SP1")),
        add("image_id_relabeling", "receipt_metadata", lambda p: p["receipt_verification"].__setitem__("image_id_hex", "00" * 32)),
        add("receipt_commitment_relabeling", "receipt_metadata", lambda p: p.__setitem__("receipt_commitment", "blake2b-256:" + "33" * 32)),
        add("receipt_size_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("proof_size_bytes", p["proof_metrics"]["proof_size_bytes"] + 1)),
        add("proof_generation_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("proof_generation_time_ms", 1.0)),
        add("verifier_time_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("verifier_time_ms", 1.0)),
        add("decision_relabeling", "parser_or_schema", lambda p: p.__setitem__("decision", "GO_FAKE")),
        add("non_claim_removed", "parser_or_schema", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1])),
        add("validation_command_removed", "parser_or_schema", lambda p: p.__setitem__("validation_commands", p["validation_commands"][:-1])),
        add("unknown_field_added", "parser_or_schema", lambda p: p.__setitem__("unknown", True)),
    ]


def validate_core_payload(payload: dict[str, Any]) -> None:
    expected_keys = {
        "schema", "evidence_schema", "issue", "source_issue", "adapter_issue", "result", "decision",
        "claim_boundary", "route_id", "system", "journal_commitment", "receipt_commitment",
        "journal_contract", "receipt_artifact", "receipt_verification", "toolchain_probe", "proof_metrics",
        "go_criterion", "non_claims", "validation_commands", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    expect_equal(payload["schema"], SCHEMA, "schema")
    expect_equal(payload["evidence_schema"], EVIDENCE_SCHEMA, "evidence schema")
    expect_equal(payload["issue"], ISSUE, "issue")
    expect_equal(payload["source_issue"], SOURCE_ISSUE, "source issue")
    expect_equal(payload["adapter_issue"], ADAPTER_ISSUE, "adapter issue")
    expect_equal(payload["result"], RESULT, "result")
    expect_equal(payload["decision"], DECISION, "decision")
    expect_equal(payload["claim_boundary"], CLAIM_BOUNDARY, "claim boundary")
    expect_equal(payload["route_id"], ROUTE_ID, "route id", layer="receipt_metadata")
    expect_equal(payload["system"], SYSTEM, "system", layer="receipt_metadata")
    expected_journal = expected_journal_contract()
    expect_equal(payload["journal_contract"], expected_journal, "journal contract", layer="journal_contract")
    expect_equal(payload["journal_commitment"], expected_journal["journal_commitment"], "journal commitment", layer="journal_contract")
    artifact = require_object(payload["receipt_artifact"], "receipt artifact", layer="receipt_metadata")
    expect_keys(artifact, {"path", "size_bytes", "sha256", "commitment"}, "receipt artifact", layer="receipt_metadata")
    receipt_path = ROOT / artifact["path"]
    if not receipt_path.is_file():
        raise D128Risc0StatementReceiptError("receipt artifact missing", layer="receipt_artifact")
    receipt_bytes = receipt_path.read_bytes()
    if len(receipt_bytes) <= 0 or len(receipt_bytes) > MAX_RECEIPT_BYTES:
        raise D128Risc0StatementReceiptError("receipt artifact size outside allowed bound", layer="receipt_artifact")
    expect_equal(artifact["size_bytes"], len(receipt_bytes), "receipt artifact size", layer="receipt_metadata")
    expect_equal(artifact["sha256"], sha256_bytes(receipt_bytes), "receipt artifact sha256", layer="receipt_metadata")
    expect_equal(artifact["commitment"], blake2b_commitment_bytes(receipt_bytes), "receipt artifact commitment", layer="receipt_metadata")
    expect_equal(payload["receipt_commitment"], artifact["commitment"], "receipt commitment", layer="receipt_metadata")
    verification = require_object(payload["receipt_verification"], "receipt verification", layer="receipt_metadata")
    expect_keys(
        verification,
        {
            "host_summary_schema", "host_summary_mode", "verifier_executed", "receipt_verified",
            "decoded_journal_matches_expected", "image_id_hex", "journal_sha256", "receipt_sha256",
            "risc0_zkvm_version",
        },
        "receipt verification",
        layer="receipt_metadata",
    )
    expect_equal(verification["host_summary_schema"], "zkai-d128-risc0-host-summary-v1", "host summary schema", layer="receipt_metadata")
    if verification["host_summary_mode"] not in {"prove", "verify"}:
        raise D128Risc0StatementReceiptError("host summary mode mismatch", layer="receipt_metadata")
    expect_equal(verification["verifier_executed"], True, "verifier executed", layer="receipt_metadata")
    expect_equal(verification["receipt_verified"], True, "receipt verified", layer="receipt_metadata")
    expect_equal(verification["decoded_journal_matches_expected"], True, "journal match", layer="receipt_metadata")
    expect_equal(verification["journal_sha256"], sha256_bytes(expected_journal_bytes()), "journal sha256", layer="receipt_metadata")
    expect_equal(verification["receipt_sha256"], sha256_bytes(receipt_bytes), "verification receipt sha256", layer="receipt_metadata")
    expect_equal(verification["risc0_zkvm_version"], RISC0_ZKVM_VERSION, "RISC Zero version", layer="receipt_metadata")
    if not isinstance(verification["image_id_hex"], str) or len(verification["image_id_hex"]) != 64:
        raise D128Risc0StatementReceiptError("image id must be 32-byte hex", layer="receipt_metadata")
    probe = require_object(payload["toolchain_probe"], "toolchain probe", layer="toolchain_probe")
    expect_keys(probe, {"probe_scope", "host_os", "commands", "rzup_components"}, "toolchain probe", layer="toolchain_probe")
    expect_equal(probe["probe_scope"], "local_risc0_receipt_generation_and_verification", "probe scope", layer="toolchain_probe")
    commands = require_object(probe["commands"], "toolchain commands", layer="toolchain_probe")
    for command_id in REQUIRED_COMMANDS:
        entry = require_object(commands.get(command_id), f"command {command_id}", layer="toolchain_probe")
        if entry.get("available") is not True:
            raise D128Risc0StatementReceiptError(f"required command {command_id} unavailable", layer="toolchain_probe")
    components = require_object(probe["rzup_components"], "rzup components", layer="toolchain_probe")
    expect_equal(components.get("cargo-risczero"), RISC0_ZKVM_VERSION, "cargo-risczero component", layer="toolchain_probe")
    expect_equal(components.get("r0vm"), RISC0_ZKVM_VERSION, "r0vm component", layer="toolchain_probe")
    metrics = require_object(payload["proof_metrics"], "proof metrics", layer="proof_metrics")
    expect_keys(
        metrics,
        {"metrics_enabled", "timing_policy", "proof_size_bytes", "proof_generation_time_ms", "verifier_time_ms"},
        "proof metrics",
        layer="proof_metrics",
    )
    expect_equal(metrics["metrics_enabled"], True, "metrics enabled", layer="proof_metrics")
    expect_equal(metrics["timing_policy"], "single_local_run_engineering_only", "timing policy", layer="proof_metrics")
    expect_equal(metrics["proof_size_bytes"], len(receipt_bytes), "proof size", layer="proof_metrics")
    if metrics["proof_generation_time_ms"] is not None and (not isinstance(metrics["proof_generation_time_ms"], (int, float)) or metrics["proof_generation_time_ms"] <= 0):
        raise D128Risc0StatementReceiptError("proof_generation_time_ms must be positive or null", layer="proof_metrics")
    if not isinstance(metrics["verifier_time_ms"], (int, float)) or metrics["verifier_time_ms"] <= 0:
        raise D128Risc0StatementReceiptError("verifier_time_ms must be positive", layer="proof_metrics")
    expect_equal(payload["go_criterion"], GO_CRITERION, "go criterion")
    expect_equal(payload["non_claims"], NON_CLAIMS, "non claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation commands")
    summary = require_object(payload["summary"], "summary")
    expect_equal(summary["journal_commitment"], payload["journal_commitment"], "summary journal")
    expect_equal(summary["image_id_hex"], verification["image_id_hex"], "summary image id")
    expect_equal(summary["receipt_commitment"], payload["receipt_commitment"], "summary receipt")
    expect_equal(summary["receipt_size_bytes"], len(receipt_bytes), "summary receipt size")
    expect_equal(summary["proof_generation_time_ms"], metrics["proof_generation_time_ms"], "summary proof time", layer="proof_metrics")
    expect_equal(summary["verifier_time_ms"], metrics["verifier_time_ms"], "summary verify time", layer="proof_metrics")


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "payload")
    expected_keys = {
        "schema", "evidence_schema", "issue", "source_issue", "adapter_issue", "result", "decision",
        "claim_boundary", "route_id", "system", "journal_commitment", "receipt_commitment",
        "journal_contract", "receipt_artifact", "receipt_verification", "toolchain_probe", "proof_metrics",
        "go_criterion", "non_claims", "validation_commands", "mutation_inventory", "case_count",
        "all_mutations_rejected", "cases", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    validate_core_payload(_core_payload(payload))
    inventory = require_list(payload["mutation_inventory"], "mutation inventory")
    expect_equal(tuple((item.get("mutation"), item.get("surface")) for item in inventory), EXPECTED_MUTATION_INVENTORY, "mutation inventory")
    cases = require_list(payload["cases"], "cases")
    expect_equal(payload["case_count"], len(cases), "case count")
    expect_equal(len(cases), len(EXPECTED_MUTATION_INVENTORY), "case length")
    expected_cases = {case["mutation"]: case for case in mutation_cases(_core_payload(payload))}
    by_name: dict[str, dict[str, Any]] = {}
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"case[{index}]", layer="mutation_suite")
        expect_keys(case, {"mutation", "surface", "rejected", "rejection_layer", "error"}, f"case[{index}]", layer="mutation_suite")
        by_name[case["mutation"]] = case
    expect_equal(set(by_name), EXPECTED_MUTATION_SET, "case mutation set", layer="mutation_suite")
    for mutation, surface in EXPECTED_MUTATION_INVENTORY:
        case = by_name[mutation]
        expect_equal(case["surface"], surface, f"case surface {mutation}", layer="mutation_suite")
        expect_equal(case, expected_cases[mutation], f"case {mutation}", layer="mutation_suite")
    expect_equal(payload["all_mutations_rejected"], all(case["rejected"] for case in cases), "all mutations rejected", layer="mutation_suite")
    if payload["all_mutations_rejected"] is not True:
        raise D128Risc0StatementReceiptError("not all RISC Zero receipt mutations rejected", layer="mutation_suite")


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "route_id": payload["route_id"],
            "system": payload["system"],
            "decision": payload["decision"],
            "receipt_size_bytes": payload["proof_metrics"]["proof_size_bytes"],
            "proof_generation_time_ms": "" if payload["proof_metrics"]["proof_generation_time_ms"] is None else f"{payload['proof_metrics']['proof_generation_time_ms']:.3f}",
            "verifier_time_ms": f"{payload['proof_metrics']['verifier_time_ms']:.3f}",
            "journal_commitment": payload["journal_commitment"],
            "receipt_commitment": payload["receipt_commitment"],
            "image_id_hex": payload["receipt_verification"]["image_id_hex"],
        }
    )
    return output.getvalue()


def write_text_checked(path: pathlib.Path, text: str) -> None:
    resolved = path.resolve()
    root = EVIDENCE_DIR.resolve()
    if resolved != root and root not in resolved.parents:
        raise D128Risc0StatementReceiptError(f"output path must stay under {EVIDENCE_DIR}", layer="output_path")
    if resolved.exists() and resolved.is_dir():
        raise D128Risc0StatementReceiptError("output path must be a file, not a directory", layer="output_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{hashlib.sha256(os.urandom(16)).hexdigest()[:8]}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def resolve_output_path(path: pathlib.Path | None) -> pathlib.Path | None:
    if path is None:
        return None
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    if resolved.exists() and resolved.is_dir():
        raise D128Risc0StatementReceiptError("output path must be a file, not a directory", layer="output_path")
    return resolved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prove", action="store_true", help="generate a fresh receipt and verify it")
    mode.add_argument("--verify-existing", action="store_true", help="verify the existing receipt artifact")
    parser.add_argument("--receipt", type=pathlib.Path, default=RECEIPT_OUT)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt_path = resolve_output_path(args.receipt)
    if receipt_path is None:
        raise D128Risc0StatementReceiptError("receipt path is required", layer="output_path")
    json_path = resolve_output_path(args.write_json)
    tsv_path = resolve_output_path(args.write_tsv)
    previous_proof_generation_time_ms = None
    if args.verify_existing and json_path is not None and json_path.is_file():
        previous = require_object(load_json(json_path), "previous RISC Zero evidence")
        metrics = require_object(previous.get("proof_metrics"), "previous proof metrics")
        previous_proof_generation_time_ms = metrics.get("proof_generation_time_ms")
    payload = build_payload(
        prove=args.prove,
        receipt_path=receipt_path,
        previous_proof_generation_time_ms=previous_proof_generation_time_ms,
    )
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tsv_text = to_tsv(payload)
    if json_path is not None:
        write_text_checked(json_path, json_text)
    else:
        print(json_text, end="")
    if tsv_path is not None:
        write_text_checked(tsv_path, tsv_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
