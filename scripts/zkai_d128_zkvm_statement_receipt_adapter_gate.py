#!/usr/bin/env python3
"""Probe the d128 zkVM statement-receipt adapter route.

This gate answers issue #422. It consumes the checked #424 proof-native d128
 two-slice public-input contract and asks whether the same contract can be
bound today by a local zkVM receipt using public journal / public-values
semantics.

The result is allowed to be a bounded no-go. A GO requires a real RISC Zero or
SP1 receipt/proof artifact, a verifier handle that accepts it, and public
journal/public-values fields that bind the #424 statement contract. Toolchain
presence alone is not enough.
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
import shutil
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_SCRIPT = ROOT / "scripts" / "zkai_d128_proof_native_two_slice_compression_gate.py"
SOURCE_EVIDENCE = EVIDENCE_DIR / "zkai-d128-proof-native-two-slice-compression-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-zkvm-statement-receipt-adapter-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-zkvm-statement-receipt-adapter-2026-05.tsv"

SCHEMA = "zkai-d128-zkvm-statement-receipt-adapter-gate-v1"
DECISION = "NO_GO_D128_ZKVM_STATEMENT_RECEIPT_ADAPTER_INCOMPLETE"
RESULT = "NO_GO"
ISSUE = 422
SOURCE_ISSUE = 424
SOURCE_SCHEMA = "zkai-d128-proof-native-two-slice-compression-gate-v1"
SOURCE_DECISION = "GO_D128_PROOF_NATIVE_TWO_SLICE_TRANSCRIPT_COMPRESSION"
SOURCE_RESULT = "GO"
SOURCE_CLAIM_BOUNDARY = "PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION"
CLAIM_BOUNDARY = "ZKVM_STATEMENT_RECEIPT_ADAPTER_INCOMPLETE_NOT_A_RECEIPT_GO"
FIRST_BLOCKER = "MISSING_LOCAL_ZKVM_TOOLCHAIN_BOOTSTRAP"
RECEIPT_ARTIFACT_BLOCKER = "MISSING_ZKVM_RECEIPT_ARTIFACT"
UNREADABLE_RECEIPT_ARTIFACT_BLOCKER = "MISSING_OR_UNREADABLE_ZKVM_RECEIPT_ARTIFACT"
RECEIPT_VERIFICATION_BLOCKER = "MISSING_ZKVM_RECEIPT_VERIFICATION_AND_PUBLIC_VALUES_BINDING"
RECEIPT_CANDIDATE_SCHEMA = "zkai-d128-zkvm-statement-receipt-candidate-v1"
MAX_RECEIPT_CANDIDATE_BYTES = 1_048_576
GO_CRITERION = (
    "a real RISC Zero or SP1 receipt/proof artifact exists, its verifier accepts it, "
    "and its public journal/public-values bind the #424 d128 two-slice public-input contract"
)
NO_GO_CRITERION = (
    "record the exact blocker before metrics: missing local toolchain bootstrap, missing proof fixture, "
    "missing public-values binding route, prover cost too high for a small fixture, or verifier API blocker"
)
JOURNAL_SCHEMA = "zkai-d128-zkvm-statement-journal-contract-v1"
POLICY_LABEL = "statement-receipt-adapter-policy:d128-two-slice:no-metadata-relabeling:v1"
ACTION_LABEL = "verify_d128_two_slice_statement_receipt"

ZKVM_ROUTES = (
    {
        "route_id": "risc0_zkvm_statement_receipt",
        "system": "RISC Zero",
        "required_commands": ("rzup", "cargo-risczero"),
        "public_statement_surface": "receipt journal plus image id",
        "receipt_artifact": "docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.json",
    },
    {
        "route_id": "sp1_zkvm_statement_receipt",
        "system": "SP1",
        "required_commands": ("sp1up", "cargo-prove"),
        "public_statement_surface": "public values plus verifying key/program metadata",
        "receipt_artifact": "docs/engineering/evidence/zkai-d128-sp1-statement-receipt-2026-05.json",
    },
)

COMMAND_PROBES = (
    ("rustc", ("rustc", "--version")),
    ("cargo", ("cargo", "--version")),
    ("docker", ("docker", "--version")),
    ("protoc", ("protoc", "--version")),
    ("rzup", ("rzup", "--version")),
    ("cargo-risczero", ("cargo", "risczero", "--version")),
    ("sp1up", ("sp1up", "--version")),
    ("cargo-prove", ("cargo", "prove", "--version")),
)

NON_CLAIMS = [
    "not a zkVM receipt",
    "not a RISC Zero proof",
    "not an SP1 proof",
    "not a zkML performance benchmark",
    "not recursive verification of the underlying Stwo slice proofs inside a zkVM",
    "not a claim that RISC Zero or SP1 cannot implement this contract",
    "not a claim that RISC Zero or SP1 are missing statement binding internally",
    "not a Starknet deployment result",
    "not a replacement for the Stwo-native d128 transformer receipt track",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_zkvm_statement_receipt_adapter_gate.py --write-json docs/engineering/evidence/zkai-d128-zkvm-statement-receipt-adapter-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-zkvm-statement-receipt-adapter-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_zkvm_statement_receipt_adapter_gate",
    "python3 -m py_compile scripts/zkai_d128_zkvm_statement_receipt_adapter_gate.py scripts/tests/test_zkai_d128_zkvm_statement_receipt_adapter_gate.py",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

EXPECTED_MUTATION_INVENTORY = (
    ("source_decision_relabeling", "source_contract"),
    ("source_claim_boundary_relabeling", "source_contract"),
    ("source_target_commitment_relabeling", "source_contract"),
    ("journal_schema_relabeling", "journal_contract"),
    ("journal_policy_relabeling", "journal_contract"),
    ("journal_action_relabeling", "journal_contract"),
    ("journal_verifier_domain_relabeling", "journal_contract"),
    ("journal_statement_hash_relabeling", "journal_contract"),
    ("journal_commitment_relabeling", "journal_contract"),
    ("risc0_toolchain_relabeling", "toolchain_probe"),
    ("sp1_toolchain_relabeling", "toolchain_probe"),
    ("risc0_route_relabeling_to_go", "route_decisions"),
    ("sp1_route_relabeling_to_go", "route_decisions"),
    ("receipt_artifact_smuggled", "route_decisions"),
    ("receipt_probe_size_bound_removed", "route_decisions"),
    ("receipt_probe_size_limit_changed", "route_decisions"),
    ("proof_size_metric_smuggled", "backend_decision"),
    ("verifier_time_metric_smuggled", "backend_decision"),
    ("proof_generation_time_metric_smuggled", "backend_decision"),
    ("decision_relabeling_to_go", "parser_or_schema"),
    ("non_claim_removed", "parser_or_schema"),
    ("validation_command_removed", "parser_or_schema"),
    ("unknown_top_level_field_added", "parser_or_schema"),
)
EXPECTED_MUTATION_SET = {name for name, _surface in EXPECTED_MUTATION_INVENTORY}

TSV_COLUMNS = (
    "route_id",
    "system",
    "status",
    "usable_today",
    "first_blocker",
    "required_commands",
    "missing_commands",
    "receipt_artifact",
    "proof_size_bytes",
    "verifier_time_ms",
    "proof_generation_time_ms",
)

SUMMARY_PREFIX = "The #424 d128 two-slice statement can be mapped into a zkVM public journal/public-values contract, "
SUMMARY_BY_BLOCKER = {
    FIRST_BLOCKER: (
        SUMMARY_PREFIX
        + "but this local checkout has no complete RISC Zero or SP1 proving toolchain bootstrap."
    ),
    RECEIPT_ARTIFACT_BLOCKER: (
        SUMMARY_PREFIX
        + "and at least one zkVM route has its required commands, but no receipt artifact exists for verification."
    ),
    UNREADABLE_RECEIPT_ARTIFACT_BLOCKER: (
        SUMMARY_PREFIX
        + "and at least one zkVM route has a receipt path, but the artifact is empty, unreadable, or not bound to the current journal contract."
    ),
    RECEIPT_VERIFICATION_BLOCKER: (
        SUMMARY_PREFIX
        + "and a toolchain plus receipt-looking artifact can exist, but this gate does not yet verify the receipt or public-values binding."
    ),
}


class D128ZkvmStatementReceiptAdapterError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128ZkvmStatementReceiptAdapterError(f"failed to load {module_name} from {path}", layer="source_contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


SOURCE = _load_module(SOURCE_SCRIPT, "zkai_d128_proof_native_for_zkvm_statement_receipt_gate")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commitment(value: Any) -> str:
    digest = hashlib.blake2b(canonical_json_bytes(value), digest_size=32).hexdigest()
    return f"blake2b-256:{digest}"


def require_object(value: Any, label: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128ZkvmStatementReceiptAdapterError(f"{label} must be an object", layer=layer)
    return value


def require_list(value: Any, label: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise D128ZkvmStatementReceiptAdapterError(f"{label} must be a list", layer=layer)
    return value


def expect_equal(actual: Any, expected: Any, label: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise D128ZkvmStatementReceiptAdapterError(f"{label} mismatch", layer=layer)


def expect_keys(value: dict[str, Any], expected: set[str], label: str, *, layer: str = "parser_or_schema") -> None:
    keys = set(value)
    if keys != expected:
        raise D128ZkvmStatementReceiptAdapterError(
            f"{label} keys mismatch: missing={sorted(expected - keys)} extra={sorted(keys - expected)}",
            layer=layer,
        )


def load_json(path: pathlib.Path, *, layer: str = "source_contract") -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128ZkvmStatementReceiptAdapterError(f"failed to load JSON {path}: {err}", layer=layer) from err


@functools.lru_cache(maxsize=1)
def source_payload() -> dict[str, Any]:
    payload = require_object(load_json(SOURCE_EVIDENCE), "source proof-native payload", layer="source_contract")
    try:
        SOURCE.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator failures.
        raise D128ZkvmStatementReceiptAdapterError(f"source #424 validation failed: {err}", layer="source_contract") from err
    expect_equal(payload.get("schema"), SOURCE_SCHEMA, "source schema", layer="source_contract")
    expect_equal(payload.get("issue"), SOURCE_ISSUE, "source issue", layer="source_contract")
    expect_equal(payload.get("decision"), SOURCE_DECISION, "source decision", layer="source_contract")
    expect_equal(payload.get("result"), SOURCE_RESULT, "source result", layer="source_contract")
    expect_equal(payload.get("claim_boundary"), SOURCE_CLAIM_BOUNDARY, "source claim boundary", layer="source_contract")
    expect_equal(payload.get("all_mutations_rejected"), True, "source mutation result", layer="source_contract")
    return copy.deepcopy(payload)


def source_contract() -> dict[str, Any]:
    payload = source_payload()
    summary = require_object(payload.get("summary"), "source summary", layer="source_contract")
    compressed = require_object(payload.get("compressed_artifact"), "compressed artifact", layer="source_contract")
    preimage = require_object(compressed.get("preimage"), "compressed artifact preimage", layer="source_contract")
    public_contract = require_object(preimage.get("proof_native_public_input_contract"), "source public-input contract", layer="source_contract")
    return {
        "path": str(SOURCE_EVIDENCE.relative_to(ROOT)),
        "file_sha256": file_sha256(SOURCE_EVIDENCE),
        "payload_sha256": sha256_bytes(canonical_json_bytes(payload)),
        "schema": payload["schema"],
        "issue": payload["issue"],
        "decision": payload["decision"],
        "result": payload["result"],
        "claim_boundary": payload["claim_boundary"],
        "two_slice_target_commitment": summary["two_slice_target_commitment"],
        "selected_slice_ids": copy.deepcopy(summary["selected_slice_ids"]),
        "selected_checked_rows": summary["selected_checked_rows"],
        "compressed_artifact_commitment": summary["compressed_artifact_commitment"],
        "source_accumulator_commitment": summary["source_accumulator_commitment"],
        "verifier_handle_commitment": summary["verifier_handle_commitment"],
        "public_input_contract": copy.deepcopy(public_contract),
    }


def journal_contract(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source_contract() if source is None else copy.deepcopy(source)
    public_contract = copy.deepcopy(source["public_input_contract"])
    payload = {
        "schema": JOURNAL_SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "journal_kind": "zkvm-public-journal-or-public-values-contract",
        "action_label": ACTION_LABEL,
        "policy_label": POLICY_LABEL,
        "model_or_program_identity": {
            "statement_family": "d128-rmsnorm-swiglu-two-slice",
            "source_contract_schema": source["schema"],
            "required_backend_version": public_contract["required_backend_version"],
        },
        "input_commitment": source["two_slice_target_commitment"],
        "output_commitment": source["compressed_artifact_commitment"],
        "verifier_domain": public_contract["verifier_domain"],
        "public_values": public_contract,
        "source_file_sha256": source["file_sha256"],
        "source_payload_sha256": source["payload_sha256"],
        "source_verifier_handle_commitment": source["verifier_handle_commitment"],
    }
    payload["journal_payload_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    payload["journal_commitment"] = commitment(payload)
    return payload


@functools.lru_cache(maxsize=1)
def _command_probe_cached() -> str:
    commands: dict[str, Any] = {}
    for command_id, command in COMMAND_PROBES:
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
                result = subprocess.run(list(command), check=False, text=True, capture_output=True, timeout=15, cwd=ROOT)
                entry["returncode"] = result.returncode
                entry["stdout"] = result.stdout.strip()
                entry["stderr"] = result.stderr.strip()
                if result.returncode != 0:
                    entry["available"] = False
            except (OSError, subprocess.SubprocessError) as err:
                entry["available"] = False
                entry["stderr"] = str(err)
        commands[command_id] = entry
    probe = {
        "probe_scope": "local_cli_bootstrap_only_no_network_install",
        "host_os": sys.platform,
        "commands": commands,
    }
    return json.dumps(probe, sort_keys=True)


def command_probe() -> dict[str, Any]:
    return json.loads(_command_probe_cached())


def receipt_probe_result(
    *,
    exists: bool,
    candidate_valid: bool,
    reason: str,
    size_bound_exceeded: bool = False,
) -> dict[str, Any]:
    # Keep this probe stable across harmless receipt-evidence rewrites. The
    # exact artifact byte length is checked only for the cap decision; it is not
    # recorded because downstream timing-field churn can otherwise invalidate
    # this adapter gate without changing the statement boundary.
    return {
        "exists": exists,
        "candidate_valid": candidate_valid,
        "reason": reason,
        "max_size_bytes": MAX_RECEIPT_CANDIDATE_BYTES,
        "size_bound_exceeded": size_bound_exceeded,
    }


def read_receipt_candidate_text(path: pathlib.Path) -> tuple[str | None, dict[str, Any] | None]:
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_RECEIPT_CANDIDATE_BYTES + 1)
    except OSError:
        return None, receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="unreadable_receipt_artifact",
        )
    if not data:
        return None, receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="empty_receipt_artifact",
        )
    if len(data) > MAX_RECEIPT_CANDIDATE_BYTES:
        return None, receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="oversized_receipt_artifact",
            size_bound_exceeded=True,
        )
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="unparseable_receipt_artifact",
        )


def receipt_candidate_probe(path: pathlib.Path, route: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return receipt_probe_result(
            exists=False,
            candidate_valid=False,
            reason="missing_receipt_artifact",
        )
    text, error_probe = read_receipt_candidate_text(path)
    if error_probe is not None:
        return error_probe
    if text is None:
        return receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="unreadable_receipt_artifact",
        )
    try:
        candidate = json.loads(text)
    except json.JSONDecodeError:
        return receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="unparseable_receipt_artifact",
        )
    if not isinstance(candidate, dict):
        return receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="receipt_candidate_not_object",
        )
    if candidate.get("schema") != RECEIPT_CANDIDATE_SCHEMA:
        return receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="receipt_candidate_schema_mismatch",
        )
    if candidate.get("route_id") != route["route_id"]:
        return receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="receipt_candidate_route_mismatch",
        )
    if candidate.get("system") != route["system"]:
        return receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="receipt_candidate_system_mismatch",
        )
    if candidate.get("journal_commitment") != journal["journal_commitment"]:
        return receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="receipt_candidate_journal_mismatch",
        )
    receipt_commitment = candidate.get("receipt_commitment")
    if not isinstance(receipt_commitment, str) or not receipt_commitment.startswith("blake2b-256:"):
        return receipt_probe_result(
            exists=True,
            candidate_valid=False,
            reason="receipt_candidate_commitment_missing",
        )
    return receipt_probe_result(
        exists=True,
        candidate_valid=True,
        reason="receipt_candidate_parseable",
    )


def route_decisions(probe: dict[str, Any]) -> list[dict[str, Any]]:
    commands = require_object(probe.get("commands"), "probe commands", layer="toolchain_probe")
    journal = journal_contract()
    routes = []
    for route in ZKVM_ROUTES:
        required = list(route["required_commands"])
        missing = [command for command in required if not require_object(commands.get(command), f"command {command}", layer="toolchain_probe").get("available")]
        receipt_path = ROOT / route["receipt_artifact"]
        artifact_probe = receipt_candidate_probe(receipt_path, route, journal)
        # Fail closed: a command set plus a receipt-looking file is not a GO
        # until this gate verifies the receipt and its public journal binding.
        usable = False
        if missing:
            status = "NO_GO_ZKVM_TOOLCHAIN_OR_RECEIPT_ARTIFACT_MISSING"
            first_blocker = "missing_commands:" + ",".join(missing)
        elif not artifact_probe["exists"]:
            status = "NO_GO_ZKVM_TOOLCHAIN_OR_RECEIPT_ARTIFACT_MISSING"
            first_blocker = "missing_receipt_artifact"
        elif not artifact_probe["candidate_valid"]:
            status = "NO_GO_ZKVM_TOOLCHAIN_OR_RECEIPT_ARTIFACT_MISSING"
            first_blocker = "missing_or_unreadable_receipt_artifact"
        else:
            status = "NO_GO_ZKVM_RECEIPT_VERIFICATION_NOT_IMPLEMENTED"
            first_blocker = "missing_receipt_verification_and_public_values_binding"
        routes.append(
            {
                "route_id": route["route_id"],
                "system": route["system"],
                "status": status,
                "usable_today": usable,
                "first_blocker": first_blocker,
                "required_commands": required,
                "missing_commands": missing,
                "public_statement_surface": route["public_statement_surface"],
                "receipt_artifact": route["receipt_artifact"],
                "receipt_artifact_exists": artifact_probe["exists"],
                "receipt_artifact_candidate_valid": artifact_probe["candidate_valid"],
                "receipt_artifact_probe": artifact_probe,
                "proof_metrics": {
                    "proof_size_bytes": None,
                    "verifier_time_ms": None,
                    "proof_generation_time_ms": None,
                },
            }
        )
    return routes


def backend_decision(routes: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [route for route in routes if route["usable_today"]]
    first_blocker = backend_first_blocker(routes)
    return {
        "result": "GO" if usable else RESULT,
        "decision": "GO_D128_ZKVM_STATEMENT_RECEIPT_AVAILABLE" if usable else DECISION,
        "usable_route_ids": [route["route_id"] for route in usable],
        "candidate_route_ids": [route["route_id"] for route in routes],
        "first_blocker": first_blocker,
        "claim_boundary": CLAIM_BOUNDARY,
        "go_criterion": GO_CRITERION,
        "no_go_criterion": NO_GO_CRITERION,
        "proof_metrics": {
            "metrics_enabled": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "proof_generation_time_ms": None,
        },
    }


def backend_first_blocker(routes: list[dict[str, Any]]) -> str:
    if any(route["usable_today"] for route in routes):
        return "none"
    toolchain_ready = [route for route in routes if not route["missing_commands"]]
    if not toolchain_ready:
        return FIRST_BLOCKER
    if any(route["receipt_artifact_candidate_valid"] for route in toolchain_ready):
        return RECEIPT_VERIFICATION_BLOCKER
    if any(route["receipt_artifact_exists"] for route in toolchain_ready):
        return UNREADABLE_RECEIPT_ARTIFACT_BLOCKER
    return RECEIPT_ARTIFACT_BLOCKER


def summary_for_backend_decision(decision: dict[str, Any]) -> str:
    blocker = decision.get("first_blocker")
    if blocker == "none":
        return SUMMARY_PREFIX + "and at least one zkVM route verifies the receipt and public-values binding."
    summary = SUMMARY_BY_BLOCKER.get(blocker)
    if summary is None:
        raise D128ZkvmStatementReceiptAdapterError(f"unknown zkVM adapter blocker: {blocker}", layer="backend_decision")
    return summary


def build_payload(probe: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source_contract()
    journal = journal_contract(source)
    probe = command_probe() if probe is None else copy.deepcopy(probe)
    routes = route_decisions(probe)
    decision = backend_decision(routes)
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_contract": source,
        "journal_contract": journal,
        "toolchain_probe": probe,
        "route_decisions": routes,
        "backend_decision": decision,
        "mutation_inventory": [{"mutation": name, "surface": surface} for name, surface in EXPECTED_MUTATION_INVENTORY],
        "case_count": len(EXPECTED_MUTATION_INVENTORY),
        "all_mutations_rejected": True,
        "cases": [],
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "summary": summary_for_backend_decision(decision),
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
        except D128ZkvmStatementReceiptAdapterError as err:
            return {"mutation": name, "surface": surface, "rejected": True, "rejection_layer": err.layer, "error": str(err)}
        return {"mutation": name, "surface": surface, "rejected": False, "rejection_layer": "accepted", "error": ""}

    return [
        add("source_decision_relabeling", "source_contract", lambda p: p["source_contract"].__setitem__("decision", "GO_FAKE")),
        add("source_claim_boundary_relabeling", "source_contract", lambda p: p["source_contract"].__setitem__("claim_boundary", "RECURSION")),
        add("source_target_commitment_relabeling", "source_contract", lambda p: p["source_contract"].__setitem__("two_slice_target_commitment", "blake2b-256:" + "00" * 32)),
        add("journal_schema_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("schema", "fake")),
        add("journal_policy_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("policy_label", "fake-policy")),
        add("journal_action_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("action_label", "fake-action")),
        add("journal_verifier_domain_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("verifier_domain", "fake-domain")),
        add("journal_statement_hash_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("source_payload_sha256", "0" * 64)),
        add("journal_commitment_relabeling", "journal_contract", lambda p: p["journal_contract"].__setitem__("journal_commitment", "blake2b-256:" + "11" * 32)),
        add("risc0_toolchain_relabeling", "toolchain_probe", lambda p: p["toolchain_probe"]["commands"]["rzup"].__setitem__("available", not p["toolchain_probe"]["commands"]["rzup"]["available"])),
        add("sp1_toolchain_relabeling", "toolchain_probe", lambda p: p["toolchain_probe"]["commands"]["sp1up"].__setitem__("available", not p["toolchain_probe"]["commands"]["sp1up"]["available"])),
        add("risc0_route_relabeling_to_go", "route_decisions", lambda p: p["route_decisions"][0].update({"status": "GO_ZKVM_STATEMENT_RECEIPT_AVAILABLE", "usable_today": True, "first_blocker": "none"})),
        add("sp1_route_relabeling_to_go", "route_decisions", lambda p: p["route_decisions"][1].update({"status": "GO_ZKVM_STATEMENT_RECEIPT_AVAILABLE", "usable_today": True, "first_blocker": "none"})),
        add("receipt_artifact_smuggled", "route_decisions", lambda p: p["route_decisions"][0].__setitem__("receipt_artifact_exists", not p["route_decisions"][0]["receipt_artifact_exists"])),
        add("receipt_probe_size_bound_removed", "route_decisions", lambda p: p["route_decisions"][0]["receipt_artifact_probe"].pop("size_bound_exceeded", None)),
        add("receipt_probe_size_limit_changed", "route_decisions", lambda p: p["route_decisions"][0]["receipt_artifact_probe"].__setitem__("max_size_bytes", 1)),
        add("proof_size_metric_smuggled", "backend_decision", lambda p: p["backend_decision"]["proof_metrics"].__setitem__("proof_size_bytes", 1)),
        add("verifier_time_metric_smuggled", "backend_decision", lambda p: p["backend_decision"]["proof_metrics"].__setitem__("verifier_time_ms", 1.0)),
        add("proof_generation_time_metric_smuggled", "backend_decision", lambda p: p["backend_decision"]["proof_metrics"].__setitem__("proof_generation_time_ms", 1.0)),
        add("decision_relabeling_to_go", "parser_or_schema", lambda p: (p.__setitem__("decision", "GO_FAKE"), p.__setitem__("result", "GO"))),
        add("non_claim_removed", "parser_or_schema", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1])),
        add("validation_command_removed", "parser_or_schema", lambda p: p.__setitem__("validation_commands", p["validation_commands"][:-1])),
        add("unknown_top_level_field_added", "parser_or_schema", lambda p: p.__setitem__("unknown", True)),
    ]


def validate_source_contract(value: Any) -> dict[str, Any]:
    contract = require_object(value, "source contract", layer="source_contract")
    expected = source_contract()
    expect_equal(contract, expected, "source contract", layer="source_contract")
    return contract


def validate_journal_contract(value: Any, source: dict[str, Any]) -> dict[str, Any]:
    journal = require_object(value, "journal contract", layer="journal_contract")
    expected = journal_contract(source)
    expect_equal(journal, expected, "journal contract", layer="journal_contract")
    return journal


def validate_toolchain_probe(value: Any) -> dict[str, Any]:
    probe = require_object(value, "toolchain probe", layer="toolchain_probe")
    expect_keys(probe, {"probe_scope", "host_os", "commands"}, "toolchain probe", layer="toolchain_probe")
    expect_equal(probe["probe_scope"], "local_cli_bootstrap_only_no_network_install", "probe scope", layer="toolchain_probe")
    if not isinstance(probe["host_os"], str) or not probe["host_os"]:
        raise D128ZkvmStatementReceiptAdapterError("host_os must be a non-empty string", layer="toolchain_probe")
    commands = require_object(probe["commands"], "toolchain commands", layer="toolchain_probe")
    expect_equal(set(commands), {command_id for command_id, _cmd in COMMAND_PROBES}, "toolchain command set", layer="toolchain_probe")
    for command_id, command in COMMAND_PROBES:
        entry = require_object(commands.get(command_id), f"command {command_id}", layer="toolchain_probe")
        expect_keys(entry, {"command_id", "command", "available", "returncode", "stdout", "stderr"}, f"command {command_id}", layer="toolchain_probe")
        expect_equal(entry["command_id"], command_id, f"command id {command_id}", layer="toolchain_probe")
        expect_equal(entry["command"], list(command), f"command args {command_id}", layer="toolchain_probe")
        if not isinstance(entry["available"], bool):
            raise D128ZkvmStatementReceiptAdapterError(f"command {command_id} availability must be bool", layer="toolchain_probe")
    return probe


def validate_routes(value: Any, probe: dict[str, Any]) -> list[dict[str, Any]]:
    routes = require_list(value, "route decisions", layer="route_decisions")
    expected = route_decisions(probe)
    expect_equal(routes, expected, "route decisions", layer="route_decisions")
    return routes


def validate_backend_decision(value: Any, routes: list[dict[str, Any]]) -> dict[str, Any]:
    decision = require_object(value, "backend decision", layer="backend_decision")
    expected = backend_decision(routes)
    expect_equal(decision, expected, "backend decision", layer="backend_decision")
    if decision["proof_metrics"]["metrics_enabled"] is not False:
        raise D128ZkvmStatementReceiptAdapterError("zkVM metrics must stay disabled without a real receipt", layer="backend_decision")
    for metric in ("proof_size_bytes", "verifier_time_ms", "proof_generation_time_ms"):
        if decision["proof_metrics"][metric] is not None:
            raise D128ZkvmStatementReceiptAdapterError(f"{metric} must be absent before receipt GO", layer="backend_decision")
    return decision


def validate_core_payload(payload: dict[str, Any]) -> None:
    expected_keys = {
        "schema", "issue", "source_issue", "decision", "result", "claim_boundary", "source_contract",
        "journal_contract", "toolchain_probe", "route_decisions", "backend_decision", "non_claims",
        "validation_commands", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    expect_equal(payload["schema"], SCHEMA, "schema")
    expect_equal(payload["issue"], ISSUE, "issue")
    expect_equal(payload["source_issue"], SOURCE_ISSUE, "source issue")
    expect_equal(payload["decision"], DECISION, "decision")
    expect_equal(payload["result"], RESULT, "result")
    expect_equal(payload["claim_boundary"], CLAIM_BOUNDARY, "claim boundary")
    source = validate_source_contract(payload["source_contract"])
    validate_journal_contract(payload["journal_contract"], source)
    probe = validate_toolchain_probe(payload["toolchain_probe"])
    routes = validate_routes(payload["route_decisions"], probe)
    decision = validate_backend_decision(payload["backend_decision"], routes)
    expect_equal(payload["non_claims"], NON_CLAIMS, "non claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation commands")
    expect_equal(payload["summary"], summary_for_backend_decision(decision), "summary")


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "payload")
    expected_keys = {
        "schema", "issue", "source_issue", "decision", "result", "claim_boundary", "source_contract",
        "journal_contract", "toolchain_probe", "route_decisions", "backend_decision", "mutation_inventory",
        "case_count", "all_mutations_rejected", "cases", "non_claims", "validation_commands", "summary",
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
        if not isinstance(case["mutation"], str):
            raise D128ZkvmStatementReceiptAdapterError(f"case[{index}] mutation must be string", layer="mutation_suite")
        by_name[case["mutation"]] = case
    expect_equal(set(by_name), EXPECTED_MUTATION_SET, "case mutation set", layer="mutation_suite")
    for mutation, surface in EXPECTED_MUTATION_INVENTORY:
        case = by_name[mutation]
        expect_equal(case["surface"], surface, f"case surface {mutation}", layer="mutation_suite")
        expect_equal(case, expected_cases[mutation], f"case {mutation}", layer="mutation_suite")
    expect_equal(payload["all_mutations_rejected"], all(case["rejected"] for case in cases), "all mutations rejected", layer="mutation_suite")
    if payload["all_mutations_rejected"] is not True:
        raise D128ZkvmStatementReceiptAdapterError("not all zkVM adapter mutations rejected", layer="mutation_suite")


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for route in payload["route_decisions"]:
        writer.writerow(
            {
                "route_id": route["route_id"],
                "system": route["system"],
                "status": route["status"],
                "usable_today": str(route["usable_today"]).lower(),
                "first_blocker": route["first_blocker"],
                "required_commands": ",".join(route["required_commands"]),
                "missing_commands": ",".join(route["missing_commands"]) or "none",
                "receipt_artifact": route["receipt_artifact"],
                "proof_size_bytes": "not_measured",
                "verifier_time_ms": "not_measured",
                "proof_generation_time_ms": "not_measured",
            }
        )
    return output.getvalue()


def write_text_checked(path: pathlib.Path, text: str) -> None:
    resolved = path.resolve()
    root = EVIDENCE_DIR.resolve()
    if resolved != root and root not in resolved.parents:
        raise D128ZkvmStatementReceiptAdapterError(f"output path must stay under {EVIDENCE_DIR}", layer="output_path")
    if resolved.exists() and resolved.is_dir():
        raise D128ZkvmStatementReceiptAdapterError("output path must be a file, not a directory", layer="output_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{hashlib.sha256(os.urandom(16)).hexdigest()[:8]}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def resolve_output_path(path: pathlib.Path | None) -> pathlib.Path | None:
    if path is None:
        return None
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    if resolved.exists() and resolved.is_dir():
        raise D128ZkvmStatementReceiptAdapterError("output path must be a file, not a directory", layer="output_path")
    return resolved


def resolve_output_paths(json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> tuple[pathlib.Path | None, pathlib.Path | None]:
    resolved_json = resolve_output_path(json_path)
    resolved_tsv = resolve_output_path(tsv_path)
    if resolved_json is not None and resolved_tsv is not None and resolved_json == resolved_tsv:
        raise D128ZkvmStatementReceiptAdapterError("JSON and TSV outputs must be distinct", layer="output_path")
    return resolved_json, resolved_tsv


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
