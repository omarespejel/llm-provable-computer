#!/usr/bin/env python3
"""Generate or verify a RISC Zero receipt for attention/KV transition semantics.

This gate answers issue #441 for the zkVM route. Unlike the earlier external
SNARK adapter, the guest does not merely wrap a precomputed statement contract:
it reads the tiny attention/KV fixture privately, computes integer
argmax-attention scores, appends the new KV row, chooses the lowest-position
tie winner, and commits the resulting journal.

The claim is intentionally narrow. This is a RISC Zero receipt for one tiny
single-head integer-argmax attention/KV transition. It is not a native Stwo AIR,
not Softmax, not full transformer inference, and not recursion or PCD.
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
SOURCE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_transition_receipt_probe.py"
PROGRAM_DIR = ROOT / "programs" / "risc0-attention-kv-transition-receipt"
PROGRAM_MANIFEST = PROGRAM_DIR / "Cargo.toml"
RECEIPT_OUT = EVIDENCE_DIR / "zkai-attention-kv-risc0-semantics-receipt-2026-05.bincode"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-risc0-semantics-receipt-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-risc0-semantics-receipt-2026-05.tsv"

SCHEMA = "zkai-attention-kv-risc0-semantics-receipt-gate-v1"
ISSUE = 441
SOURCE_ISSUE = 336
RESULT = "GO"
DECISION = "GO_ATTENTION_KV_RISC0_SEMANTICS_RECEIPT_FOR_TINY_INTEGER_ARGMAX_TRANSITION"
CLAIM_BOUNDARY = "RISC0_RECEIPT_PROVES_TINY_INTEGER_ARGMAX_ATTENTION_KV_SEMANTICS_NOT_STWO_OR_SOFTMAX"
ROUTE_ID = "risc0_attention_kv_transition_semantics_receipt"
SYSTEM = "RISC Zero"
JOURNAL_SCHEMA = "zkai-attention-kv-risc0-semantics-journal-v1"
SEMANTICS = "tiny-single-head-integer-argmax-attention-v1"
MASKING_POLICY = "none"
RISC0_ZKVM_VERSION = "3.0.5"
MAX_RECEIPT_BYTES = 2_000_000
REQUIRED_COMMANDS = ("rzup", "cargo-risczero", "cargo", "rustc")
GO_CRITERION = (
    "RISC Zero host proves or verifies a receipt whose guest-computed journal matches the checked "
    "tiny integer-argmax attention/KV transition semantics and rejects relabeling of bound fields"
)
NON_CLAIMS = [
    "not a native Stwo attention/KV AIR or proof",
    "not a Softmax attention proof",
    "not full transformer inference",
    "not recursive verification or PCD",
    "not agent correctness",
    "not a public zkML benchmark row",
    "not a Starknet deployment result",
]

VALIDATION_COMMANDS = [
    "PATH=\"$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH\" python3 scripts/zkai_attention_kv_risc0_semantics_receipt_gate.py --verify-existing --write-json target/zkai-attention-kv-risc0-semantics-receipt-verify.json --write-tsv target/zkai-attention-kv-risc0-semantics-receipt-verify.tsv",
    "PATH=\"$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH\" python3 -m unittest scripts.tests.test_zkai_attention_kv_risc0_semantics_receipt_gate",
    "python3 -m py_compile scripts/zkai_attention_kv_risc0_semantics_receipt_gate.py scripts/tests/test_zkai_attention_kv_risc0_semantics_receipt_gate.py",
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
    "selected_position",
    "journal_commitment",
    "receipt_commitment",
    "image_id_hex",
)

EXPECTED_MUTATION_INVENTORY = (
    ("prior_kv_cache_relabeling", "journal_semantics"),
    ("input_query_relabeling", "journal_semantics"),
    ("attention_output_relabeling", "journal_semantics"),
    ("next_kv_cache_relabeling", "journal_semantics"),
    ("score_trace_relabeling", "journal_semantics"),
    ("selected_position_relabeling", "journal_semantics"),
    ("source_model_config_commitment_relabeling", "source_statement_contract"),
    ("source_public_instance_commitment_relabeling", "source_statement_contract"),
    ("source_statement_commitment_relabeling", "source_statement_contract"),
    ("route_id_relabeling", "receipt_metadata"),
    ("system_relabeling", "receipt_metadata"),
    ("image_id_relabeling", "receipt_metadata"),
    ("receipt_commitment_relabeling", "receipt_metadata"),
    ("strict_reverification_relabeling", "receipt_metadata"),
    ("receipt_size_metric_smuggling", "proof_metrics"),
    ("proof_generation_metric_smuggling", "proof_metrics"),
    ("verifier_time_metric_smuggling", "proof_metrics"),
    ("native_stwo_claim_smuggling", "parser_or_schema"),
    ("softmax_claim_smuggling", "parser_or_schema"),
    ("non_claim_removed", "parser_or_schema"),
    ("validation_command_removed", "parser_or_schema"),
    ("unknown_field_added", "parser_or_schema"),
)
EXPECTED_MUTATION_SET = {name for name, _surface in EXPECTED_MUTATION_INVENTORY}


class AttentionKvRisc0SemanticsReceiptError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def _load_source_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_attention_kv_transition_receipt_probe", SOURCE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRisc0SemanticsReceiptError(f"failed to load source script: {SOURCE_SCRIPT}", layer="source_contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SOURCE = _load_source_module()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def host_json_bytes(value: Any) -> bytes:
    """Match serde_json struct field order from the RISC Zero host summary."""

    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blake2b_commitment_bytes(data: bytes) -> str:
    return f"blake2b-256:{hashlib.blake2b(data, digest_size=32).hexdigest()}"


def blake2b_commitment(value: Any, domain: str) -> str:
    return SOURCE.blake2b_commitment(value, domain)


def require_object(value: Any, label: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionKvRisc0SemanticsReceiptError(f"{label} must be an object", layer=layer)
    return value


def require_list(value: Any, label: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise AttentionKvRisc0SemanticsReceiptError(f"{label} must be a list", layer=layer)
    return value


def expect_equal(actual: Any, expected: Any, label: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise AttentionKvRisc0SemanticsReceiptError(f"{label} mismatch", layer=layer)


def expect_keys(value: dict[str, Any], expected: set[str], label: str, *, layer: str = "parser_or_schema") -> None:
    keys = set(value)
    if keys != expected:
        raise AttentionKvRisc0SemanticsReceiptError(
            f"{label} keys mismatch: missing={sorted(expected - keys)} extra={sorted(keys - expected)}",
            layer=layer,
        )


def _resolved_under_root(path: pathlib.Path, *, label: str, layer: str) -> pathlib.Path:
    resolved = path.resolve(strict=False)
    root = ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as err:
        raise AttentionKvRisc0SemanticsReceiptError(f"{label} path escapes repository root", layer=layer) from err
    return resolved


def load_json(path: pathlib.Path, *, layer: str = "parser_or_schema") -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvRisc0SemanticsReceiptError(f"failed to load JSON {path}: {err}", layer=layer) from err


def source_fixture() -> dict[str, Any]:
    return SOURCE.canonical_transition_fixture()


def source_transition() -> dict[str, Any]:
    return SOURCE.evaluate_transition(source_fixture())


def source_receipt() -> dict[str, Any]:
    return SOURCE.build_receipt(source_fixture())


def expected_input() -> dict[str, Any]:
    fixture = source_fixture()
    return {
        "prior_kv_cache": fixture["prior_kv_cache"],
        "input_step": fixture["input_step"],
    }


def expected_journal() -> dict[str, Any]:
    fixture = source_fixture()
    transition = source_transition()
    return {
        "schema": JOURNAL_SCHEMA,
        "semantics": SEMANTICS,
        "masking_policy": MASKING_POLICY,
        "prior_kv_cache": fixture["prior_kv_cache"],
        "input_step": fixture["input_step"],
        "scores": transition["scores"],
        "selected_position": transition["selected_position"],
        "attention_output": transition["attention_output"],
        "next_kv_cache": transition["next_kv_cache"],
    }


def expected_source_statement_fields() -> dict[str, Any]:
    receipt = source_receipt()
    keys = (
        "model_config_commitment",
        "prior_kv_cache_commitment",
        "input_commitment",
        "attention_output_commitment",
        "next_kv_cache_commitment",
        "public_instance_commitment",
        "proof_commitment",
        "proof_status",
        "selected_position",
        "score_trace_commitment",
        "statement_commitment",
        "verifier_domain",
    )
    return {key: receipt[key] for key in keys}


def journal_commitment(journal: dict[str, Any] | None = None) -> str:
    return blake2b_commitment(journal or expected_journal(), "ptvm:zkai:attention-kv-risc0-journal:v1")


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


def rzup_components() -> dict[str, str]:
    if shutil.which("rzup") is None:
        return {}
    result = subprocess.run(["rzup", "show"], check=False, text=True, capture_output=True, timeout=20, cwd=ROOT)
    components: dict[str, str] = {}
    current_name: str | None = None
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("-", "Installed components", "rzup home")):
            continue
        if not line.startswith("*"):
            current_name = line
            continue
        if current_name is not None:
            components[current_name] = line.removeprefix("*").strip()
            current_name = None
    return components


def toolchain_probe() -> dict[str, Any]:
    commands = {
        "rzup": command_entry("rzup", ("rzup", "--version")),
        "cargo-risczero": command_entry("cargo-risczero", ("cargo", "risczero", "--version")),
        "cargo": command_entry("cargo", ("cargo", "--version")),
        "rustc": command_entry("rustc", ("rustc", "--version")),
    }
    return {
        "probe_scope": "local_risc0_attention_kv_semantics_receipt_generation_and_verification",
        "host_os": sys.platform,
        "commands": commands,
        "rzup_components": rzup_components(),
    }


def require_available_toolchain() -> dict[str, Any]:
    probe = toolchain_probe()
    commands = require_object(probe.get("commands"), "toolchain commands", layer="toolchain_probe")
    missing = []
    for command_id in REQUIRED_COMMANDS:
        entry = commands.get(command_id)
        if not isinstance(entry, dict) or entry.get("available") is not True:
            missing.append(command_id)
    if missing:
        raise AttentionKvRisc0SemanticsReceiptError(
            f"required RISC Zero toolchain commands unavailable before host run: {', '.join(missing)}",
            layer="toolchain_probe",
        )
    components = require_object(probe.get("rzup_components"), "rzup components", layer="toolchain_probe")
    mismatched_components = [
        component
        for component in ("cargo-risczero", "r0vm")
        if components.get(component) != RISC0_ZKVM_VERSION
    ]
    if mismatched_components:
        raise AttentionKvRisc0SemanticsReceiptError(
            "required RISC Zero components have unexpected versions: " + ", ".join(mismatched_components),
            layer="toolchain_probe",
        )
    return probe


def run_host(mode: str, input_path: pathlib.Path, receipt_path: pathlib.Path, summary_path: pathlib.Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PATH"] = f"{os.environ.get('HOME', '')}/.risc0/bin:{os.environ.get('HOME', '')}/.cargo/bin:" + env.get("PATH", "")
    env.setdefault("CARGO_TARGET_DIR", str(ROOT / "target" / "risc0-attention-kv-transition-receipt"))
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
        str(input_path),
        str(receipt_path),
        str(summary_path),
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True, timeout=900, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise AttentionKvRisc0SemanticsReceiptError(
            f"RISC Zero host {mode} failed: stdout={result.stdout[-2000:]} stderr={result.stderr[-4000:]}",
            layer="risc0_host",
        )
    return require_object(load_json(summary_path, layer="risc0_host"), "RISC Zero host summary", layer="risc0_host")


def generate_or_verify_receipt(*, prove: bool, receipt_path: pathlib.Path) -> dict[str, Any]:
    target_root = ROOT / "target"
    target_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_root) as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        input_path = tmp / "attention-input.json"
        summary_path = tmp / "summary.json"
        input_path.write_text(json.dumps(expected_input(), sort_keys=True) + "\n", encoding="utf-8")
        if prove:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            return run_host("prove", input_path, receipt_path, summary_path)
        if not receipt_path.is_file():
            raise AttentionKvRisc0SemanticsReceiptError(f"receipt artifact is missing: {receipt_path}", layer="receipt_artifact")
        return run_host("verify", input_path, receipt_path, summary_path)


def reverify_receipt_artifact(receipt_path: pathlib.Path) -> dict[str, Any]:
    target_root = ROOT / "target"
    target_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_root) as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        input_path = tmp / "attention-input.json"
        summary_path = tmp / "summary.json"
        input_path.write_text(json.dumps(expected_input(), sort_keys=True) + "\n", encoding="utf-8")
        return run_host("verify", input_path, receipt_path, summary_path)


def build_payload(
    *,
    prove: bool = False,
    receipt_path: pathlib.Path = RECEIPT_OUT,
    previous_proof_generation_time_ms: float | None = None,
) -> dict[str, Any]:
    journal = expected_journal()
    receipt_path = _resolved_under_root(receipt_path, label="receipt", layer="output_path")
    toolchain = require_available_toolchain()
    host_summary = generate_or_verify_receipt(prove=prove, receipt_path=receipt_path)
    receipt_bytes = receipt_path.read_bytes()
    if not receipt_bytes or len(receipt_bytes) > MAX_RECEIPT_BYTES:
        raise AttentionKvRisc0SemanticsReceiptError("receipt artifact size outside allowed bound", layer="receipt_artifact")
    receipt_commitment = blake2b_commitment_bytes(receipt_bytes)
    proof_generation_time_ms = host_summary.get("prove_time_ms")
    proof_generation_time_source = "current_prove_run"
    if proof_generation_time_ms is None:
        proof_generation_time_ms = previous_proof_generation_time_ms
        proof_generation_time_source = (
            "carried_from_existing_evidence_not_remeasured"
            if proof_generation_time_ms is not None
            else "not_remeasured_in_verify_existing"
        )
    verification_summary = host_summary
    if host_summary["mode"] == "prove":
        verification_summary = reverify_receipt_artifact(receipt_path)
    verifier_time_ms = verification_summary["verify_time_ms"]
    proof_metrics = {
        "metrics_enabled": True,
        "timing_policy": "single_local_run_engineering_only",
        "proof_size_bytes": len(receipt_bytes),
        "proof_generation_time_ms": proof_generation_time_ms,
        "proof_generation_time_source": proof_generation_time_source,
        "verifier_time_ms": verifier_time_ms,
        "verifier_time_source": "current_verify_run",
    }
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "result": RESULT,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "route_id": ROUTE_ID,
        "system": SYSTEM,
        "fixture": source_fixture(),
        "source_transition": source_transition(),
        "source_statement_fields": expected_source_statement_fields(),
        "journal": journal,
        "journal_commitment": journal_commitment(journal),
        "receipt_commitment": receipt_commitment,
        "receipt_artifact": {
            "path": str(receipt_path.relative_to(ROOT)),
            "size_bytes": len(receipt_bytes),
            "sha256": sha256_bytes(receipt_bytes),
            "commitment": receipt_commitment,
        },
        "receipt_verification": {
            "host_summary_schema": verification_summary["schema"],
            "host_summary_mode": verification_summary["mode"],
            "strict_receipt_reverified": True,
            "verifier_executed": True,
            "receipt_verified": True,
            "decoded_journal_matches_expected": True,
            "image_id_hex": verification_summary["image_id_hex"],
            "journal_sha256": verification_summary["journal_sha256"],
            "receipt_sha256": verification_summary["receipt_sha256"],
            "risc0_zkvm_version": verification_summary["risc0_zkvm_version"],
        },
        "toolchain_probe": toolchain,
        "proof_metrics": proof_metrics,
        "go_criterion": GO_CRITERION,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_inventory": [{"mutation": name, "surface": surface} for name, surface in EXPECTED_MUTATION_INVENTORY],
        "case_count": len(EXPECTED_MUTATION_INVENTORY),
        "all_mutations_rejected": True,
        "cases": [],
        "summary": {
            "selected_position": journal["selected_position"],
            "attention_output": journal["attention_output"],
            "next_kv_items": len(journal["next_kv_cache"]),
            "image_id_hex": verification_summary["image_id_hex"],
            "receipt_size_bytes": len(receipt_bytes),
            "proof_generation_time_ms": proof_generation_time_ms,
            "proof_generation_time_source": proof_generation_time_source,
            "verifier_time_ms": verifier_time_ms,
            "verifier_time_source": "current_verify_run",
            "journal_commitment": journal_commitment(journal),
            "receipt_commitment": receipt_commitment,
        },
    }
    expect_equal(host_summary["journal"], journal, "host journal", layer="risc0_host")
    expect_equal(host_summary["journal_sha256"], sha256_bytes(host_json_bytes(journal)), "host journal sha256", layer="risc0_host")
    expect_equal(host_summary["receipt_sha256"], sha256_bytes(receipt_bytes), "host receipt sha256", layer="risc0_host")
    expect_equal(verification_summary["mode"], "verify", "verification summary mode", layer="risc0_host")
    expect_equal(verification_summary["journal"], journal, "verification journal", layer="risc0_host")
    expect_equal(verification_summary["journal_sha256"], sha256_bytes(host_json_bytes(journal)), "verification journal sha256", layer="risc0_host")
    expect_equal(verification_summary["receipt_sha256"], sha256_bytes(receipt_bytes), "verification receipt sha256", layer="risc0_host")
    payload["cases"] = mutation_cases(payload)
    payload["case_count"] = len(payload["cases"])
    payload["all_mutations_rejected"] = all(case["rejected"] for case in payload["cases"])
    validate_payload(payload)
    return payload


def _core_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in payload.items()
        if key not in {"cases", "case_count", "all_mutations_rejected", "mutation_inventory"}
    }


def mutation_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = _core_payload(payload)

    def add(name: str, surface: str, mutate: Any) -> dict[str, Any]:
        mutated = copy.deepcopy(baseline)
        mutate(mutated)
        try:
            validate_core_payload(mutated)
        except AttentionKvRisc0SemanticsReceiptError as err:
            return {"mutation": name, "surface": surface, "rejected": True, "rejection_layer": err.layer, "error": str(err)}
        return {"mutation": name, "surface": surface, "rejected": False, "rejection_layer": "accepted", "error": ""}

    fake_commitment = "blake2b-256:" + "66" * 32
    return [
        add("prior_kv_cache_relabeling", "journal_semantics", lambda p: p["journal"].__setitem__("prior_kv_cache", [])),
        add("input_query_relabeling", "journal_semantics", lambda p: p["journal"]["input_step"].__setitem__("query", [9, 9])),
        add("attention_output_relabeling", "journal_semantics", lambda p: p["journal"].__setitem__("attention_output", [0, 0])),
        add("next_kv_cache_relabeling", "journal_semantics", lambda p: p["journal"]["next_kv_cache"][2].__setitem__("value", [0, 0])),
        add("score_trace_relabeling", "journal_semantics", lambda p: p["journal"]["scores"][0].__setitem__("score", 999)),
        add("selected_position_relabeling", "journal_semantics", lambda p: p["journal"].__setitem__("selected_position", 2)),
        add("source_model_config_commitment_relabeling", "source_statement_contract", lambda p: p["source_statement_fields"].__setitem__("model_config_commitment", fake_commitment)),
        add("source_public_instance_commitment_relabeling", "source_statement_contract", lambda p: p["source_statement_fields"].__setitem__("public_instance_commitment", fake_commitment)),
        add("source_statement_commitment_relabeling", "source_statement_contract", lambda p: p["source_statement_fields"].__setitem__("statement_commitment", fake_commitment)),
        add("route_id_relabeling", "receipt_metadata", lambda p: p.__setitem__("route_id", "sp1_attention_kv_transition_semantics_receipt")),
        add("system_relabeling", "receipt_metadata", lambda p: p.__setitem__("system", "SP1")),
        add("image_id_relabeling", "receipt_metadata", lambda p: p["receipt_verification"].__setitem__("image_id_hex", "00" * 32)),
        add("receipt_commitment_relabeling", "receipt_metadata", lambda p: p.__setitem__("receipt_commitment", fake_commitment)),
        add("strict_reverification_relabeling", "receipt_metadata", lambda p: p["receipt_verification"].__setitem__("strict_receipt_reverified", False)),
        add("receipt_size_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("proof_size_bytes", p["proof_metrics"]["proof_size_bytes"] + 1)),
        add("proof_generation_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("proof_generation_time_ms", 1.0)),
        add("verifier_time_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("verifier_time_ms", 1.0)),
        add("native_stwo_claim_smuggling", "parser_or_schema", lambda p: p.__setitem__("claim_boundary", "NATIVE_STWO_ATTENTION_KV_PROOF")),
        add("softmax_claim_smuggling", "parser_or_schema", lambda p: p["journal"].__setitem__("semantics", "softmax-attention")),
        add("non_claim_removed", "parser_or_schema", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1])),
        add("validation_command_removed", "parser_or_schema", lambda p: p.__setitem__("validation_commands", p["validation_commands"][:-1])),
        add("unknown_field_added", "parser_or_schema", lambda p: p.__setitem__("unknown", True)),
    ]


def validate_source_statement_fields(fields: dict[str, Any], journal: dict[str, Any]) -> None:
    expected = expected_source_statement_fields()
    expect_equal(fields, expected, "source statement fields", layer="source_statement_contract")
    fixture = source_fixture()
    expect_equal(
        fields["model_config_commitment"],
        blake2b_commitment(fixture["model_config"], "ptvm:zkai:attention-kv-model-config:v1"),
        "model config commitment",
        layer="source_statement_contract",
    )
    expect_equal(
        fields["prior_kv_cache_commitment"],
        blake2b_commitment(journal["prior_kv_cache"], "ptvm:zkai:attention-prior-kv-cache:v1"),
        "prior KV commitment",
        layer="source_statement_contract",
    )
    expect_equal(
        fields["input_commitment"],
        blake2b_commitment(journal["input_step"], "ptvm:zkai:attention-input-step:v1"),
        "input commitment",
        layer="source_statement_contract",
    )
    expect_equal(
        fields["attention_output_commitment"],
        blake2b_commitment(journal["attention_output"], "ptvm:zkai:attention-output:v1"),
        "attention output commitment",
        layer="source_statement_contract",
    )
    expect_equal(
        fields["next_kv_cache_commitment"],
        blake2b_commitment(journal["next_kv_cache"], "ptvm:zkai:attention-next-kv-cache:v1"),
        "next KV commitment",
        layer="source_statement_contract",
    )
    expect_equal(
        fields["score_trace_commitment"],
        blake2b_commitment(journal["scores"], "ptvm:zkai:attention-score-trace:v1"),
        "score trace commitment",
        layer="source_statement_contract",
    )
    expect_equal(fields["selected_position"], journal["selected_position"], "selected position", layer="source_statement_contract")


def validate_core_payload(payload: dict[str, Any], *, strict_receipt: bool = False) -> None:
    expected_keys = {
        "schema", "issue", "source_issue", "result", "decision", "claim_boundary", "route_id", "system",
        "fixture", "source_transition", "source_statement_fields", "journal", "journal_commitment",
        "receipt_commitment", "receipt_artifact", "receipt_verification", "toolchain_probe", "proof_metrics",
        "go_criterion", "non_claims", "validation_commands", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    expect_equal(payload["schema"], SCHEMA, "schema")
    expect_equal(payload["issue"], ISSUE, "issue")
    expect_equal(payload["source_issue"], SOURCE_ISSUE, "source issue")
    expect_equal(payload["result"], RESULT, "result")
    expect_equal(payload["decision"], DECISION, "decision")
    expect_equal(payload["claim_boundary"], CLAIM_BOUNDARY, "claim boundary")
    expect_equal(payload["route_id"], ROUTE_ID, "route id", layer="receipt_metadata")
    expect_equal(payload["system"], SYSTEM, "system", layer="receipt_metadata")
    expect_equal(payload["fixture"], source_fixture(), "fixture", layer="journal_semantics")
    expect_equal(payload["source_transition"], source_transition(), "source transition", layer="journal_semantics")
    journal = require_object(payload["journal"], "journal", layer="journal_semantics")
    expect_equal(journal, expected_journal(), "journal", layer="journal_semantics")
    validate_source_statement_fields(require_object(payload["source_statement_fields"], "source statement fields", layer="source_statement_contract"), journal)
    expect_equal(payload["journal_commitment"], journal_commitment(journal), "journal commitment", layer="journal_semantics")
    artifact = require_object(payload["receipt_artifact"], "receipt artifact", layer="receipt_metadata")
    expect_keys(artifact, {"path", "size_bytes", "sha256", "commitment"}, "receipt artifact", layer="receipt_metadata")
    if not isinstance(artifact["path"], str):
        raise AttentionKvRisc0SemanticsReceiptError("receipt artifact path must be a string", layer="receipt_artifact")
    receipt_path = _resolved_under_root(ROOT / artifact["path"], label="receipt artifact", layer="receipt_artifact")
    if not receipt_path.is_file():
        raise AttentionKvRisc0SemanticsReceiptError("receipt artifact missing", layer="receipt_artifact")
    receipt_bytes = receipt_path.read_bytes()
    if not receipt_bytes or len(receipt_bytes) > MAX_RECEIPT_BYTES:
        raise AttentionKvRisc0SemanticsReceiptError("receipt artifact size outside allowed bound", layer="receipt_artifact")
    expect_equal(artifact["size_bytes"], len(receipt_bytes), "receipt artifact size", layer="receipt_metadata")
    expect_equal(artifact["sha256"], sha256_bytes(receipt_bytes), "receipt artifact sha256", layer="receipt_metadata")
    expect_equal(artifact["commitment"], blake2b_commitment_bytes(receipt_bytes), "receipt artifact commitment", layer="receipt_metadata")
    expect_equal(payload["receipt_commitment"], artifact["commitment"], "receipt commitment", layer="receipt_metadata")
    verification = require_object(payload["receipt_verification"], "receipt verification", layer="receipt_metadata")
    expect_keys(
        verification,
        {
            "host_summary_schema", "host_summary_mode", "strict_receipt_reverified", "verifier_executed",
            "receipt_verified", "decoded_journal_matches_expected", "image_id_hex", "journal_sha256",
            "receipt_sha256", "risc0_zkvm_version",
        },
        "receipt verification",
        layer="receipt_metadata",
    )
    expect_equal(verification["host_summary_schema"], "zkai-attention-kv-risc0-host-summary-v1", "host summary schema", layer="receipt_metadata")
    if verification["host_summary_mode"] not in {"prove", "verify"}:
        raise AttentionKvRisc0SemanticsReceiptError("host summary mode mismatch", layer="receipt_metadata")
    expect_equal(verification["strict_receipt_reverified"], True, "strict receipt reverified", layer="receipt_metadata")
    expect_equal(verification["verifier_executed"], True, "verifier executed", layer="receipt_metadata")
    expect_equal(verification["receipt_verified"], True, "receipt verified", layer="receipt_metadata")
    expect_equal(verification["decoded_journal_matches_expected"], True, "journal match", layer="receipt_metadata")
    expect_equal(verification["journal_sha256"], sha256_bytes(host_json_bytes(expected_journal())), "journal sha256", layer="receipt_metadata")
    expect_equal(verification["receipt_sha256"], sha256_bytes(receipt_bytes), "verification receipt sha256", layer="receipt_metadata")
    expect_equal(verification["risc0_zkvm_version"], RISC0_ZKVM_VERSION, "RISC Zero version", layer="receipt_metadata")
    if not isinstance(verification["image_id_hex"], str) or len(verification["image_id_hex"]) != 64:
        raise AttentionKvRisc0SemanticsReceiptError("image id must be 32-byte hex", layer="receipt_metadata")
    if strict_receipt:
        strict_summary = reverify_receipt_artifact(receipt_path)
        expect_equal(strict_summary["schema"], "zkai-attention-kv-risc0-host-summary-v1", "strict host schema", layer="risc0_host")
        expect_equal(strict_summary["mode"], "verify", "strict host mode", layer="risc0_host")
        expect_equal(strict_summary["journal"], journal, "strict host journal", layer="risc0_host")
        expect_equal(strict_summary["image_id_hex"], verification["image_id_hex"], "strict image id", layer="risc0_host")
        expect_equal(strict_summary["journal_sha256"], sha256_bytes(host_json_bytes(expected_journal())), "strict journal sha256", layer="risc0_host")
        expect_equal(strict_summary["receipt_sha256"], sha256_bytes(receipt_bytes), "strict receipt sha256", layer="risc0_host")
        expect_equal(strict_summary["risc0_zkvm_version"], verification["risc0_zkvm_version"], "strict RISC Zero version", layer="risc0_host")
    probe = require_object(payload["toolchain_probe"], "toolchain probe", layer="toolchain_probe")
    expect_keys(probe, {"probe_scope", "host_os", "commands", "rzup_components"}, "toolchain probe", layer="toolchain_probe")
    expect_equal(probe["probe_scope"], "local_risc0_attention_kv_semantics_receipt_generation_and_verification", "probe scope", layer="toolchain_probe")
    commands = require_object(probe["commands"], "toolchain commands", layer="toolchain_probe")
    for command_id in REQUIRED_COMMANDS:
        entry = require_object(commands.get(command_id), f"command {command_id}", layer="toolchain_probe")
        if entry.get("available") is not True:
            raise AttentionKvRisc0SemanticsReceiptError(f"required command {command_id} unavailable", layer="toolchain_probe")
    components = require_object(probe["rzup_components"], "rzup components", layer="toolchain_probe")
    expect_equal(components.get("cargo-risczero"), RISC0_ZKVM_VERSION, "cargo-risczero component", layer="toolchain_probe")
    expect_equal(components.get("r0vm"), RISC0_ZKVM_VERSION, "r0vm component", layer="toolchain_probe")
    metrics = require_object(payload["proof_metrics"], "proof metrics", layer="proof_metrics")
    expect_keys(
        metrics,
        {
            "metrics_enabled", "timing_policy", "proof_size_bytes",
            "proof_generation_time_ms", "proof_generation_time_source",
            "verifier_time_ms", "verifier_time_source",
        },
        "proof metrics",
        layer="proof_metrics",
    )
    expect_equal(metrics["metrics_enabled"], True, "metrics enabled", layer="proof_metrics")
    expect_equal(metrics["timing_policy"], "single_local_run_engineering_only", "timing policy", layer="proof_metrics")
    expect_equal(metrics["proof_size_bytes"], len(receipt_bytes), "proof size", layer="proof_metrics")
    if metrics["proof_generation_time_source"] not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRisc0SemanticsReceiptError("proof_generation_time_source mismatch", layer="proof_metrics")
    if metrics["proof_generation_time_source"] == "not_remeasured_in_verify_existing":
        expect_equal(metrics["proof_generation_time_ms"], None, "proof generation time unavailable", layer="proof_metrics")
    elif not isinstance(metrics["proof_generation_time_ms"], (int, float)) or metrics["proof_generation_time_ms"] <= 0:
        raise AttentionKvRisc0SemanticsReceiptError("proof_generation_time_ms must be positive", layer="proof_metrics")
    if not isinstance(metrics["verifier_time_ms"], (int, float)) or metrics["verifier_time_ms"] <= 0:
        raise AttentionKvRisc0SemanticsReceiptError("verifier_time_ms must be positive", layer="proof_metrics")
    expect_equal(metrics["verifier_time_source"], "current_verify_run", "verifier time source", layer="proof_metrics")
    expect_equal(payload["go_criterion"], GO_CRITERION, "go criterion")
    expect_equal(payload["non_claims"], NON_CLAIMS, "non claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation commands")
    summary = require_object(payload["summary"], "summary")
    expect_keys(
        summary,
        {
            "selected_position", "attention_output", "next_kv_items", "image_id_hex",
            "receipt_size_bytes", "proof_generation_time_ms", "proof_generation_time_source",
            "verifier_time_ms", "verifier_time_source", "journal_commitment", "receipt_commitment",
        },
        "summary",
    )
    expect_equal(summary["selected_position"], journal["selected_position"], "summary selected position")
    expect_equal(summary["attention_output"], journal["attention_output"], "summary output")
    expect_equal(summary["next_kv_items"], len(journal["next_kv_cache"]), "summary next KV")
    expect_equal(summary["image_id_hex"], verification["image_id_hex"], "summary image id")
    expect_equal(summary["receipt_size_bytes"], len(receipt_bytes), "summary receipt size")
    expect_equal(summary["proof_generation_time_ms"], metrics["proof_generation_time_ms"], "summary proof time", layer="proof_metrics")
    expect_equal(summary["proof_generation_time_source"], metrics["proof_generation_time_source"], "summary proof time source", layer="proof_metrics")
    expect_equal(summary["verifier_time_ms"], metrics["verifier_time_ms"], "summary verify time", layer="proof_metrics")
    expect_equal(summary["verifier_time_source"], metrics["verifier_time_source"], "summary verify time source", layer="proof_metrics")
    expect_equal(summary["journal_commitment"], payload["journal_commitment"], "summary journal")
    expect_equal(summary["receipt_commitment"], payload["receipt_commitment"], "summary receipt")


def validate_payload(payload: Any, *, strict_receipt: bool = False) -> None:
    payload = require_object(payload, "payload")
    expected_keys = {
        "schema", "issue", "source_issue", "result", "decision", "claim_boundary", "route_id", "system",
        "fixture", "source_transition", "source_statement_fields", "journal", "journal_commitment",
        "receipt_commitment", "receipt_artifact", "receipt_verification", "toolchain_probe", "proof_metrics",
        "go_criterion", "non_claims", "validation_commands", "mutation_inventory", "case_count",
        "all_mutations_rejected", "cases", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    validate_core_payload(_core_payload(payload), strict_receipt=strict_receipt)
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
        raise AttentionKvRisc0SemanticsReceiptError("not all attention/KV RISC Zero receipt mutations rejected", layer="mutation_suite")


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
            "selected_position": payload["journal"]["selected_position"],
            "journal_commitment": payload["journal_commitment"],
            "receipt_commitment": payload["receipt_commitment"],
            "image_id_hex": payload["receipt_verification"]["image_id_hex"],
        }
    )
    return output.getvalue()


def write_text_checked(path: pathlib.Path, text: str) -> None:
    resolved = path.resolve()
    allowed_roots = (EVIDENCE_DIR.resolve(), (ROOT / "target").resolve())
    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        raise AttentionKvRisc0SemanticsReceiptError(
            f"output path must stay under {EVIDENCE_DIR} or {ROOT / 'target'}",
            layer="output_path",
        )
    if resolved.exists() and resolved.is_dir():
        raise AttentionKvRisc0SemanticsReceiptError("output path must be a file, not a directory", layer="output_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def resolve_output_path(path: pathlib.Path | None) -> pathlib.Path | None:
    if path is None:
        return None
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    if resolved.exists() and resolved.is_dir():
        raise AttentionKvRisc0SemanticsReceiptError("output path must be a file, not a directory", layer="output_path")
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
        raise AttentionKvRisc0SemanticsReceiptError("receipt path is required", layer="output_path")
    receipt_path = _resolved_under_root(receipt_path, label="receipt", layer="output_path")
    json_path = resolve_output_path(args.write_json)
    tsv_path = resolve_output_path(args.write_tsv)
    previous_proof_generation_time_ms = None
    if args.verify_existing:
        if json_path is None:
            raise AttentionKvRisc0SemanticsReceiptError(
                "--verify-existing requires --write-json pointing at existing RISC Zero evidence",
                layer="output_path",
            )
        previous_json_path = json_path if json_path.is_file() else JSON_OUT
        if not previous_json_path.is_file():
            raise AttentionKvRisc0SemanticsReceiptError(
                "--verify-existing requires existing checked attention/KV RISC Zero evidence JSON; use --prove first",
                layer="output_path",
            )
        previous = require_object(load_json(previous_json_path), "previous attention/KV RISC Zero evidence")
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
