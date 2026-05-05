#!/usr/bin/env python3
"""Generate or verify a RISC Zero receipt for a carried attention/KV sequence.

This gate answers issue #442 for the sequence route. It extends the earlier
one-transition RISC Zero result into a three-transition carried KV-cache
sequence. The guest computes every integer-argmax attention step and commits a
journal containing every intermediate cache row, so deletion, reordering, or
relabeling of intermediate state is rejected by the checked artifact gate.

The claim is intentionally narrow: RISC Zero proves a tiny integer-argmax
attention/KV sequence. It is not native Stwo, not Softmax, not full inference,
and not recursion or PCD.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
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
PROGRAM_DIR = ROOT / "programs" / "risc0-attention-kv-sequence-receipt"
PROGRAM_MANIFEST = PROGRAM_DIR / "Cargo.toml"
RECEIPT_OUT = EVIDENCE_DIR / "zkai-attention-kv-risc0-sequence-receipt-2026-05.bincode"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-risc0-sequence-receipt-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-risc0-sequence-receipt-2026-05.tsv"

SCHEMA = "zkai-attention-kv-risc0-sequence-receipt-gate-v1"
ISSUE = 442
SOURCE_ISSUE = 441
RESULT = "GO"
DECISION = "GO_ATTENTION_KV_RISC0_SEQUENCE_RECEIPT_FOR_CARRIED_KV_STATE"
CLAIM_BOUNDARY = "RISC0_RECEIPT_PROVES_THREE_STEP_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_NOT_STWO_OR_SOFTMAX"
ROUTE_ID = "risc0_attention_kv_sequence_semantics_receipt"
SYSTEM = "RISC Zero"
JOURNAL_SCHEMA = "zkai-attention-kv-risc0-sequence-journal-v1"
SEMANTICS = "tiny-single-head-integer-argmax-attention-sequence-v1"
MASKING_POLICY = "none"
TIE_BREAK = "lowest_position"
KEY_WIDTH = 2
VALUE_WIDTH = 2
SEQUENCE_LENGTH = 3
RISC0_ZKVM_VERSION = "3.0.5"
MAX_RECEIPT_BYTES = 2_500_000
REQUIRED_COMMANDS = ("rzup", "cargo-risczero", "cargo", "rustc")

GO_CRITERION = (
    "RISC Zero host proves or verifies a receipt whose guest-computed journal binds a three-step "
    "carried integer-argmax attention/KV sequence and rejects deletion, reordering, or relabeling of intermediate state"
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
    "PATH=\"$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH\" python3 scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py --verify-existing --write-json target/zkai-attention-kv-risc0-sequence-receipt-verify.json --write-tsv target/zkai-attention-kv-risc0-sequence-receipt-verify.tsv",
    "PATH=\"$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH\" python3 -m unittest scripts.tests.test_zkai_attention_kv_risc0_sequence_receipt_gate",
    "python3 -m py_compile scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py scripts/tests/test_zkai_attention_kv_risc0_sequence_receipt_gate.py",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
]
TSV_COLUMNS = (
    "route_id",
    "system",
    "decision",
    "sequence_length",
    "transition_rows",
    "receipt_size_bytes",
    "proof_generation_time_ms",
    "verifier_time_ms",
    "final_kv_items",
    "journal_commitment",
    "receipt_commitment",
    "image_id_hex",
)
EXPECTED_MUTATION_INVENTORY = (
    ("transition_deleted", "sequence_journal"),
    ("transition_reordered", "sequence_journal"),
    ("intermediate_prior_kv_relabeling", "sequence_journal"),
    ("intermediate_next_kv_relabeling", "sequence_journal"),
    ("intermediate_input_query_relabeling", "sequence_journal"),
    ("intermediate_attention_output_relabeling", "sequence_journal"),
    ("intermediate_score_trace_relabeling", "sequence_journal"),
    ("initial_kv_cache_relabeling", "sequence_journal"),
    ("final_kv_cache_relabeling", "sequence_journal"),
    ("input_steps_reordered", "sequence_journal"),
    ("sequence_length_relabeling", "sequence_journal"),
    ("transition_commitment_relabeling", "statement_contract"),
    ("statement_commitment_relabeling", "statement_contract"),
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
    ("recursion_claim_smuggling", "parser_or_schema"),
    ("non_claim_removed", "parser_or_schema"),
    ("validation_command_removed", "parser_or_schema"),
    ("unknown_field_added", "parser_or_schema"),
)
EXPECTED_MUTATION_SET = {name for name, _surface in EXPECTED_MUTATION_INVENTORY}


class AttentionKvRisc0SequenceReceiptError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


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
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def require_object(value: Any, label: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionKvRisc0SequenceReceiptError(f"{label} must be an object", layer=layer)
    return value


def require_list(value: Any, label: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise AttentionKvRisc0SequenceReceiptError(f"{label} must be a list", layer=layer)
    return value


def expect_equal(actual: Any, expected: Any, label: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise AttentionKvRisc0SequenceReceiptError(f"{label} mismatch", layer=layer)


def expect_keys(value: dict[str, Any], expected: set[str], label: str, *, layer: str = "parser_or_schema") -> None:
    keys = set(value)
    if keys != expected:
        raise AttentionKvRisc0SequenceReceiptError(
            f"{label} keys mismatch: missing={sorted(expected - keys)} extra={sorted(keys - expected)}",
            layer=layer,
        )


def _resolved_under_root(path: pathlib.Path, *, label: str, layer: str) -> pathlib.Path:
    resolved = path.resolve(strict=False)
    root = ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as err:
        raise AttentionKvRisc0SequenceReceiptError(f"{label} path escapes repository root", layer=layer) from err
    return resolved


def load_json(path: pathlib.Path, *, layer: str = "parser_or_schema") -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvRisc0SequenceReceiptError(f"failed to load JSON {path}: {err}", layer=layer) from err


def sequence_fixture() -> dict[str, Any]:
    return {
        "case_id": "tiny_single_head_argmax_kv_sequence_v1",
        "model_config": {
            "attention_mode": "integer_argmax_attention",
            "head_count": 1,
            "key_width": KEY_WIDTH,
            "value_width": VALUE_WIDTH,
            "tie_break": TIE_BREAK,
            "masking_policy": MASKING_POLICY,
        },
        "initial_kv_cache": [
            {"position": 0, "key": [1, 0], "value": [2, 1]},
            {"position": 1, "key": [0, 1], "value": [-1, 3]},
        ],
        "input_steps": [
            {"token_position": 2, "query": [1, 1], "new_key": [1, -1], "new_value": [4, 2]},
            {"token_position": 3, "query": [2, -1], "new_key": [0, 2], "new_value": [5, -2]},
            {"token_position": 4, "query": [-1, 2], "new_key": [2, 1], "new_value": [0, 6]},
        ],
    }


def expected_input() -> dict[str, Any]:
    fixture = sequence_fixture()
    return {
        "initial_kv_cache": fixture["initial_kv_cache"],
        "input_steps": fixture["input_steps"],
    }


def dot(lhs: list[int], rhs: list[int]) -> int:
    if len(lhs) != len(rhs):
        raise AttentionKvRisc0SequenceReceiptError("dot-product width mismatch", layer="sequence_journal")
    return sum(left * right for left, right in zip(lhs, rhs, strict=True))


def apply_step(step_index: int, prior_kv_cache: list[dict[str, Any]], input_step: dict[str, Any]) -> dict[str, Any]:
    next_item = {
        "position": input_step["token_position"],
        "key": input_step["new_key"],
        "value": input_step["new_value"],
    }
    next_kv_cache = copy.deepcopy(prior_kv_cache) + [next_item]
    scores = [
        {"position": item["position"], "score": dot(input_step["query"], item["key"]), "value": item["value"]}
        for item in next_kv_cache
    ]
    selected = max(scores, key=lambda item: (item["score"], -item["position"]))
    return {
        "step_index": step_index,
        "prior_kv_cache": copy.deepcopy(prior_kv_cache),
        "input_step": copy.deepcopy(input_step),
        "scores": scores,
        "selected_position": selected["position"],
        "attention_output": selected["value"],
        "next_kv_cache": next_kv_cache,
    }


def expected_journal() -> dict[str, Any]:
    fixture = sequence_fixture()
    current_kv_cache = copy.deepcopy(fixture["initial_kv_cache"])
    transitions = []
    for step_index, input_step in enumerate(fixture["input_steps"]):
        row = apply_step(step_index, current_kv_cache, input_step)
        current_kv_cache = copy.deepcopy(row["next_kv_cache"])
        transitions.append(row)
    return {
        "schema": JOURNAL_SCHEMA,
        "semantics": SEMANTICS,
        "masking_policy": MASKING_POLICY,
        "tie_break": TIE_BREAK,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "sequence_length": len(fixture["input_steps"]),
        "initial_kv_cache": fixture["initial_kv_cache"],
        "input_steps": fixture["input_steps"],
        "transitions": transitions,
        "final_kv_cache": current_kv_cache,
    }


def transition_commitments(journal: dict[str, Any] | None = None) -> list[str]:
    journal = expected_journal() if journal is None else journal
    return [
        blake2b_commitment(row, f"ptvm:zkai:attention-kv-sequence-transition:{row['step_index']}:v1")
        for row in journal["transitions"]
    ]


def journal_commitment(journal: dict[str, Any] | None = None) -> str:
    return blake2b_commitment(journal or expected_journal(), "ptvm:zkai:attention-kv-risc0-sequence-journal:v1")


def statement_fields(journal: dict[str, Any], receipt_commitment: str, image_id_hex: str) -> dict[str, Any]:
    fixture = sequence_fixture()
    fields = {
        "verifier_domain": "ptvm:zkai:attention-kv-sequence:risc0:v1",
        "statement_kind": "attention-kv-cache-sequence",
        "model_config_commitment": blake2b_commitment(fixture["model_config"], "ptvm:zkai:attention-kv-model-config:v1"),
        "initial_kv_cache_commitment": blake2b_commitment(journal["initial_kv_cache"], "ptvm:zkai:attention-initial-kv-cache:v1"),
        "input_steps_commitment": blake2b_commitment(journal["input_steps"], "ptvm:zkai:attention-input-steps:v1"),
        "transition_rows_commitment": blake2b_commitment(journal["transitions"], "ptvm:zkai:attention-kv-transition-rows:v1"),
        "transition_commitments": transition_commitments(journal),
        "final_kv_cache_commitment": blake2b_commitment(journal["final_kv_cache"], "ptvm:zkai:attention-final-kv-cache:v1"),
        "outputs_commitment": blake2b_commitment(
            [row["attention_output"] for row in journal["transitions"]], "ptvm:zkai:attention-sequence-outputs:v1"
        ),
        "journal_commitment": journal_commitment(journal),
        "proof_commitment": receipt_commitment,
        "proof_status": "PROVEN_BY_RISC_ZERO_SEMANTICS_RECEIPT",
        "image_id_hex": image_id_hex,
        "route_id": ROUTE_ID,
    }
    fields["public_instance_commitment"] = blake2b_commitment(
        {key: value for key, value in fields.items() if key not in {"statement_commitment"}},
        "ptvm:zkai:attention-kv-sequence-public-instance:v1",
    )
    fields["statement_commitment"] = blake2b_commitment(
        {key: value for key, value in fields.items() if key not in {"statement_commitment"}},
        "ptvm:zkai:attention-kv-sequence-statement:v1",
    )
    return fields


def command_entry(command_id: str, command: tuple[str, ...]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    entry = {"command_id": command_id, "command": list(command), "available": executable is not None, "returncode": None, "stdout": "", "stderr": ""}
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
        "probe_scope": "local_risc0_attention_kv_sequence_receipt_generation_and_verification",
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
        raise AttentionKvRisc0SequenceReceiptError(
            f"required RISC Zero toolchain commands unavailable before host run: {', '.join(missing)}",
            layer="toolchain_probe",
        )
    components = require_object(probe.get("rzup_components"), "rzup components", layer="toolchain_probe")
    mismatched_components = [component for component in ("cargo-risczero", "r0vm") if components.get(component) != RISC0_ZKVM_VERSION]
    if mismatched_components:
        raise AttentionKvRisc0SequenceReceiptError(
            "required RISC Zero components have unexpected versions: " + ", ".join(mismatched_components),
            layer="toolchain_probe",
        )
    return probe


def local_risc0_toolchain_available() -> tuple[bool, str]:
    try:
        require_available_toolchain()
    except AttentionKvRisc0SequenceReceiptError as err:
        return False, str(err)
    return True, ""


def run_host(mode: str, input_path: pathlib.Path, receipt_path: pathlib.Path, summary_path: pathlib.Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PATH"] = f"{os.environ.get('HOME', '')}/.risc0/bin:{os.environ.get('HOME', '')}/.cargo/bin:" + env.get("PATH", "")
    env.setdefault("CARGO_TARGET_DIR", str(ROOT / "target" / "risc0-attention-kv-sequence-receipt"))
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
        raise AttentionKvRisc0SequenceReceiptError(
            f"RISC Zero host {mode} failed: stdout={result.stdout[-2000:]} stderr={result.stderr[-4000:]}",
            layer="risc0_host",
        )
    return require_object(load_json(summary_path, layer="risc0_host"), "RISC Zero host summary", layer="risc0_host")


def generate_or_verify_receipt(*, prove: bool, receipt_path: pathlib.Path) -> dict[str, Any]:
    target_root = ROOT / "target"
    target_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_root) as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        input_path = tmp / "attention-sequence-input.json"
        summary_path = tmp / "summary.json"
        input_path.write_text(json.dumps(expected_input(), sort_keys=True) + "\n", encoding="utf-8")
        if prove:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            return run_host("prove", input_path, receipt_path, summary_path)
        if not receipt_path.is_file():
            raise AttentionKvRisc0SequenceReceiptError(f"receipt artifact is missing: {receipt_path}", layer="receipt_artifact")
        return run_host("verify", input_path, receipt_path, summary_path)


def reverify_receipt_artifact(receipt_path: pathlib.Path) -> dict[str, Any]:
    target_root = ROOT / "target"
    target_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_root) as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        input_path = tmp / "attention-sequence-input.json"
        summary_path = tmp / "summary.json"
        input_path.write_text(json.dumps(expected_input(), sort_keys=True) + "\n", encoding="utf-8")
        return run_host("verify", input_path, receipt_path, summary_path)


def build_payload(*, prove: bool = False, receipt_path: pathlib.Path = RECEIPT_OUT, previous_proof_generation_time_ms: float | None = None) -> dict[str, Any]:
    journal = expected_journal()
    receipt_path = _resolved_under_root(receipt_path, label="receipt", layer="output_path")
    toolchain = require_available_toolchain()
    host_summary = generate_or_verify_receipt(prove=prove, receipt_path=receipt_path)
    receipt_bytes = receipt_path.read_bytes()
    if not receipt_bytes or len(receipt_bytes) > MAX_RECEIPT_BYTES:
        raise AttentionKvRisc0SequenceReceiptError("receipt artifact size outside allowed bound", layer="receipt_artifact")
    receipt_commitment = blake2b_commitment_bytes(receipt_bytes)
    proof_generation_time_ms = host_summary.get("prove_time_ms")
    proof_generation_time_source = "current_prove_run"
    if proof_generation_time_ms is None:
        proof_generation_time_ms = previous_proof_generation_time_ms
        proof_generation_time_source = "carried_from_existing_evidence_not_remeasured" if proof_generation_time_ms is not None else "not_remeasured_in_verify_existing"
    verification_summary = host_summary
    if host_summary["mode"] == "prove":
        verification_summary = reverify_receipt_artifact(receipt_path)
    verifier_time_ms = verification_summary["verify_time_ms"]
    statement = statement_fields(journal, receipt_commitment, verification_summary["image_id_hex"])
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
        "sequence_fixture": sequence_fixture(),
        "journal": journal,
        "transition_commitments": transition_commitments(journal),
        "journal_commitment": journal_commitment(journal),
        "statement_fields": statement,
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
            "sequence_length": journal["sequence_length"],
            "transition_rows": len(journal["transitions"]),
            "selected_positions": [row["selected_position"] for row in journal["transitions"]],
            "attention_outputs": [row["attention_output"] for row in journal["transitions"]],
            "final_kv_items": len(journal["final_kv_cache"]),
            "image_id_hex": verification_summary["image_id_hex"],
            "receipt_size_bytes": len(receipt_bytes),
            "proof_generation_time_ms": proof_generation_time_ms,
            "proof_generation_time_source": proof_generation_time_source,
            "verifier_time_ms": verifier_time_ms,
            "verifier_time_source": "current_verify_run",
            "journal_commitment": journal_commitment(journal),
            "receipt_commitment": receipt_commitment,
            "statement_commitment": statement["statement_commitment"],
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
    return {key: copy.deepcopy(value) for key, value in payload.items() if key not in {"cases", "case_count", "all_mutations_rejected", "mutation_inventory"}}


def mutation_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = _core_payload(payload)

    def add(name: str, surface: str, mutate: Any) -> dict[str, Any]:
        mutated = copy.deepcopy(baseline)
        mutate(mutated)
        try:
            validate_core_payload(mutated)
        except AttentionKvRisc0SequenceReceiptError as err:
            return {"mutation": name, "surface": surface, "rejected": True, "rejection_layer": err.layer, "error": str(err)}
        return {"mutation": name, "surface": surface, "rejected": False, "rejection_layer": "accepted", "error": ""}

    fake_commitment = "blake2b-256:" + "66" * 32
    return [
        add("transition_deleted", "sequence_journal", lambda p: p["journal"]["transitions"].pop(1)),
        add("transition_reordered", "sequence_journal", lambda p: p["journal"]["transitions"].reverse()),
        add("intermediate_prior_kv_relabeling", "sequence_journal", lambda p: p["journal"]["transitions"][1]["prior_kv_cache"][0].__setitem__("value", [99, 99])),
        add("intermediate_next_kv_relabeling", "sequence_journal", lambda p: p["journal"]["transitions"][1]["next_kv_cache"][2].__setitem__("key", [9, 9])),
        add("intermediate_input_query_relabeling", "sequence_journal", lambda p: p["journal"]["transitions"][1]["input_step"].__setitem__("query", [9, 9])),
        add("intermediate_attention_output_relabeling", "sequence_journal", lambda p: p["journal"]["transitions"][1].__setitem__("attention_output", [0, 0])),
        add("intermediate_score_trace_relabeling", "sequence_journal", lambda p: p["journal"]["transitions"][1]["scores"][0].__setitem__("score", 999)),
        add("initial_kv_cache_relabeling", "sequence_journal", lambda p: p["journal"]["initial_kv_cache"][0].__setitem__("key", [7, 7])),
        add("final_kv_cache_relabeling", "sequence_journal", lambda p: p["journal"]["final_kv_cache"][3].__setitem__("value", [8, 8])),
        add("input_steps_reordered", "sequence_journal", lambda p: p["journal"]["input_steps"].reverse()),
        add("sequence_length_relabeling", "sequence_journal", lambda p: p["journal"].__setitem__("sequence_length", 2)),
        add("transition_commitment_relabeling", "statement_contract", lambda p: p["transition_commitments"].__setitem__(1, fake_commitment)),
        add("statement_commitment_relabeling", "statement_contract", lambda p: p["statement_fields"].__setitem__("statement_commitment", fake_commitment)),
        add("route_id_relabeling", "receipt_metadata", lambda p: p.__setitem__("route_id", "sp1_attention_kv_sequence_receipt")),
        add("system_relabeling", "receipt_metadata", lambda p: p.__setitem__("system", "SP1")),
        add("image_id_relabeling", "receipt_metadata", lambda p: p["receipt_verification"].__setitem__("image_id_hex", "00" * 32)),
        add("receipt_commitment_relabeling", "receipt_metadata", lambda p: p.__setitem__("receipt_commitment", fake_commitment)),
        add("strict_reverification_relabeling", "receipt_metadata", lambda p: p["receipt_verification"].__setitem__("strict_receipt_reverified", False)),
        add("receipt_size_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("proof_size_bytes", p["proof_metrics"]["proof_size_bytes"] + 1)),
        add("proof_generation_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("proof_generation_time_ms", 1.0)),
        add("verifier_time_metric_smuggling", "proof_metrics", lambda p: p["proof_metrics"].__setitem__("verifier_time_ms", 1.0)),
        add("native_stwo_claim_smuggling", "parser_or_schema", lambda p: p.__setitem__("claim_boundary", "NATIVE_STWO_ATTENTION_KV_SEQUENCE_PROOF")),
        add("softmax_claim_smuggling", "parser_or_schema", lambda p: p["journal"].__setitem__("semantics", "softmax-attention-sequence")),
        add("recursion_claim_smuggling", "parser_or_schema", lambda p: p["non_claims"].remove("not recursive verification or PCD")),
        add("non_claim_removed", "parser_or_schema", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1])),
        add("validation_command_removed", "parser_or_schema", lambda p: p.__setitem__("validation_commands", p["validation_commands"][:-1])),
        add("unknown_field_added", "parser_or_schema", lambda p: p.__setitem__("unknown", True)),
    ]


def validate_sequence_carry(journal: dict[str, Any]) -> None:
    transitions = require_list(journal.get("transitions"), "transitions", layer="sequence_journal")
    expect_equal(len(transitions), SEQUENCE_LENGTH, "transition length", layer="sequence_journal")
    current = journal["initial_kv_cache"]
    for expected_index, row in enumerate(transitions):
        row = require_object(row, f"transition[{expected_index}]", layer="sequence_journal")
        expect_equal(row["step_index"], expected_index, f"transition[{expected_index}] index", layer="sequence_journal")
        expect_equal(row["prior_kv_cache"], current, f"transition[{expected_index}] prior KV", layer="sequence_journal")
        expect_equal(row["input_step"], journal["input_steps"][expected_index], f"transition[{expected_index}] input", layer="sequence_journal")
        expected_row = apply_step(expected_index, current, journal["input_steps"][expected_index])
        expect_equal(row, expected_row, f"transition[{expected_index}] semantics", layer="sequence_journal")
        current = row["next_kv_cache"]
    expect_equal(journal["final_kv_cache"], current, "final KV cache", layer="sequence_journal")


def validate_statement_fields(fields: dict[str, Any], journal: dict[str, Any], receipt_commitment: str, image_id_hex: str) -> None:
    expected = statement_fields(journal, receipt_commitment, image_id_hex)
    expect_equal(fields, expected, "statement fields", layer="statement_contract")
    expect_equal(fields["transition_commitments"], transition_commitments(journal), "transition commitments", layer="statement_contract")
    expect_equal(fields["journal_commitment"], journal_commitment(journal), "statement journal commitment", layer="statement_contract")
    expect_equal(fields["proof_commitment"], receipt_commitment, "statement proof commitment", layer="statement_contract")


def validate_core_payload(payload: dict[str, Any], *, strict_receipt: bool = False) -> None:
    expected_keys = {
        "schema", "issue", "source_issue", "result", "decision", "claim_boundary", "route_id", "system",
        "sequence_fixture", "journal", "transition_commitments", "journal_commitment", "statement_fields",
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
    expect_equal(payload["sequence_fixture"], sequence_fixture(), "sequence fixture", layer="sequence_journal")
    journal = require_object(payload["journal"], "journal", layer="sequence_journal")
    expect_equal(journal, expected_journal(), "journal", layer="sequence_journal")
    validate_sequence_carry(journal)
    expect_equal(payload["transition_commitments"], transition_commitments(journal), "transition commitments", layer="statement_contract")
    expect_equal(payload["journal_commitment"], journal_commitment(journal), "journal commitment", layer="sequence_journal")
    artifact = require_object(payload["receipt_artifact"], "receipt artifact", layer="receipt_metadata")
    expect_keys(artifact, {"path", "size_bytes", "sha256", "commitment"}, "receipt artifact", layer="receipt_metadata")
    if not isinstance(artifact["path"], str):
        raise AttentionKvRisc0SequenceReceiptError("receipt artifact path must be a string", layer="receipt_artifact")
    receipt_path = _resolved_under_root(ROOT / artifact["path"], label="receipt artifact", layer="receipt_artifact")
    if not receipt_path.is_file():
        raise AttentionKvRisc0SequenceReceiptError("receipt artifact missing", layer="receipt_artifact")
    receipt_bytes = receipt_path.read_bytes()
    if not receipt_bytes or len(receipt_bytes) > MAX_RECEIPT_BYTES:
        raise AttentionKvRisc0SequenceReceiptError("receipt artifact size outside allowed bound", layer="receipt_artifact")
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
    expect_equal(verification["host_summary_schema"], "zkai-attention-kv-risc0-sequence-host-summary-v1", "host summary schema", layer="receipt_metadata")
    expect_equal(verification["host_summary_mode"], "verify", "host summary mode", layer="receipt_metadata")
    expect_equal(verification["strict_receipt_reverified"], True, "strict receipt reverified", layer="receipt_metadata")
    expect_equal(verification["verifier_executed"], True, "verifier executed", layer="receipt_metadata")
    expect_equal(verification["receipt_verified"], True, "receipt verified", layer="receipt_metadata")
    expect_equal(verification["decoded_journal_matches_expected"], True, "journal match", layer="receipt_metadata")
    expect_equal(verification["journal_sha256"], sha256_bytes(host_json_bytes(expected_journal())), "journal sha256", layer="receipt_metadata")
    expect_equal(verification["receipt_sha256"], sha256_bytes(receipt_bytes), "verification receipt sha256", layer="receipt_metadata")
    expect_equal(verification["risc0_zkvm_version"], RISC0_ZKVM_VERSION, "RISC Zero version", layer="receipt_metadata")
    if not isinstance(verification["image_id_hex"], str) or len(verification["image_id_hex"]) != 64:
        raise AttentionKvRisc0SequenceReceiptError("image id must be 32-byte hex", layer="receipt_metadata")
    validate_statement_fields(require_object(payload["statement_fields"], "statement fields", layer="statement_contract"), journal, payload["receipt_commitment"], verification["image_id_hex"])
    if strict_receipt:
        strict_summary = reverify_receipt_artifact(receipt_path)
        expect_equal(strict_summary["schema"], "zkai-attention-kv-risc0-sequence-host-summary-v1", "strict host schema", layer="risc0_host")
        expect_equal(strict_summary["mode"], "verify", "strict host mode", layer="risc0_host")
        expect_equal(strict_summary["journal"], journal, "strict host journal", layer="risc0_host")
        expect_equal(strict_summary["image_id_hex"], verification["image_id_hex"], "strict image id", layer="risc0_host")
        expect_equal(strict_summary["journal_sha256"], sha256_bytes(host_json_bytes(expected_journal())), "strict journal sha256", layer="risc0_host")
        expect_equal(strict_summary["receipt_sha256"], sha256_bytes(receipt_bytes), "strict receipt sha256", layer="risc0_host")
        expect_equal(strict_summary["risc0_zkvm_version"], verification["risc0_zkvm_version"], "strict RISC Zero version", layer="risc0_host")
    probe = require_object(payload["toolchain_probe"], "toolchain probe", layer="toolchain_probe")
    expect_keys(probe, {"probe_scope", "host_os", "commands", "rzup_components"}, "toolchain probe", layer="toolchain_probe")
    expect_equal(probe["probe_scope"], "local_risc0_attention_kv_sequence_receipt_generation_and_verification", "probe scope", layer="toolchain_probe")
    commands = require_object(probe["commands"], "toolchain commands", layer="toolchain_probe")
    for command_id in REQUIRED_COMMANDS:
        entry = require_object(commands.get(command_id), f"command {command_id}", layer="toolchain_probe")
        if entry.get("available") is not True:
            raise AttentionKvRisc0SequenceReceiptError(f"required command {command_id} unavailable", layer="toolchain_probe")
    components = require_object(probe["rzup_components"], "rzup components", layer="toolchain_probe")
    expect_equal(components.get("cargo-risczero"), RISC0_ZKVM_VERSION, "cargo-risczero component", layer="toolchain_probe")
    expect_equal(components.get("r0vm"), RISC0_ZKVM_VERSION, "r0vm component", layer="toolchain_probe")
    metrics = require_object(payload["proof_metrics"], "proof metrics", layer="proof_metrics")
    expect_keys(
        metrics,
        {"metrics_enabled", "timing_policy", "proof_size_bytes", "proof_generation_time_ms", "proof_generation_time_source", "verifier_time_ms", "verifier_time_source"},
        "proof metrics",
        layer="proof_metrics",
    )
    expect_equal(metrics["metrics_enabled"], True, "metrics enabled", layer="proof_metrics")
    expect_equal(metrics["timing_policy"], "single_local_run_engineering_only", "timing policy", layer="proof_metrics")
    expect_equal(metrics["proof_size_bytes"], len(receipt_bytes), "proof size", layer="proof_metrics")
    if metrics["proof_generation_time_source"] not in {"current_prove_run", "carried_from_existing_evidence_not_remeasured", "not_remeasured_in_verify_existing"}:
        raise AttentionKvRisc0SequenceReceiptError("proof_generation_time_source mismatch", layer="proof_metrics")
    if metrics["proof_generation_time_source"] == "not_remeasured_in_verify_existing":
        expect_equal(metrics["proof_generation_time_ms"], None, "proof generation time unavailable", layer="proof_metrics")
    elif not isinstance(metrics["proof_generation_time_ms"], (int, float)) or metrics["proof_generation_time_ms"] <= 0:
        raise AttentionKvRisc0SequenceReceiptError("proof_generation_time_ms must be positive", layer="proof_metrics")
    if not isinstance(metrics["verifier_time_ms"], (int, float)) or metrics["verifier_time_ms"] <= 0:
        raise AttentionKvRisc0SequenceReceiptError("verifier_time_ms must be positive", layer="proof_metrics")
    expect_equal(metrics["verifier_time_source"], "current_verify_run", "verifier time source", layer="proof_metrics")
    expect_equal(payload["go_criterion"], GO_CRITERION, "go criterion")
    expect_equal(payload["non_claims"], NON_CLAIMS, "non claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation commands")
    summary = require_object(payload["summary"], "summary")
    expect_keys(
        summary,
        {"sequence_length", "transition_rows", "selected_positions", "attention_outputs", "final_kv_items", "image_id_hex", "receipt_size_bytes", "proof_generation_time_ms", "proof_generation_time_source", "verifier_time_ms", "verifier_time_source", "journal_commitment", "receipt_commitment", "statement_commitment"},
        "summary",
    )
    expect_equal(summary["sequence_length"], journal["sequence_length"], "summary sequence length")
    expect_equal(summary["transition_rows"], len(journal["transitions"]), "summary transitions")
    expect_equal(summary["selected_positions"], [row["selected_position"] for row in journal["transitions"]], "summary selected positions")
    expect_equal(summary["attention_outputs"], [row["attention_output"] for row in journal["transitions"]], "summary outputs")
    expect_equal(summary["final_kv_items"], len(journal["final_kv_cache"]), "summary final KV")
    expect_equal(summary["image_id_hex"], verification["image_id_hex"], "summary image id")
    expect_equal(summary["receipt_size_bytes"], len(receipt_bytes), "summary receipt size")
    expect_equal(summary["proof_generation_time_ms"], metrics["proof_generation_time_ms"], "summary proof time", layer="proof_metrics")
    expect_equal(summary["proof_generation_time_source"], metrics["proof_generation_time_source"], "summary proof time source", layer="proof_metrics")
    expect_equal(summary["verifier_time_ms"], metrics["verifier_time_ms"], "summary verify time", layer="proof_metrics")
    expect_equal(summary["verifier_time_source"], metrics["verifier_time_source"], "summary verify time source", layer="proof_metrics")
    expect_equal(summary["journal_commitment"], payload["journal_commitment"], "summary journal")
    expect_equal(summary["receipt_commitment"], payload["receipt_commitment"], "summary receipt")
    expect_equal(summary["statement_commitment"], payload["statement_fields"]["statement_commitment"], "summary statement")


def validate_payload(payload: Any, *, strict_receipt: bool = False) -> None:
    payload = require_object(payload, "payload")
    expected_keys = {
        "schema", "issue", "source_issue", "result", "decision", "claim_boundary", "route_id", "system",
        "sequence_fixture", "journal", "transition_commitments", "journal_commitment", "statement_fields",
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
        raise AttentionKvRisc0SequenceReceiptError("not all attention/KV sequence receipt mutations rejected", layer="mutation_suite")


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "route_id": payload["route_id"],
            "system": payload["system"],
            "decision": payload["decision"],
            "sequence_length": payload["journal"]["sequence_length"],
            "transition_rows": len(payload["journal"]["transitions"]),
            "receipt_size_bytes": payload["proof_metrics"]["proof_size_bytes"],
            "proof_generation_time_ms": "" if payload["proof_metrics"]["proof_generation_time_ms"] is None else f"{payload['proof_metrics']['proof_generation_time_ms']:.3f}",
            "verifier_time_ms": f"{payload['proof_metrics']['verifier_time_ms']:.3f}",
            "final_kv_items": len(payload["journal"]["final_kv_cache"]),
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
        raise AttentionKvRisc0SequenceReceiptError(
            f"output path must stay under {EVIDENCE_DIR} or {ROOT / 'target'}",
            layer="output_path",
        )
    if resolved.exists() and resolved.is_dir():
        raise AttentionKvRisc0SequenceReceiptError("output path must be a file, not a directory", layer="output_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def resolve_output_path(path: pathlib.Path | None) -> pathlib.Path | None:
    if path is None:
        return None
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    if resolved.exists() and resolved.is_dir():
        raise AttentionKvRisc0SequenceReceiptError("output path must be a file, not a directory", layer="output_path")
    return resolved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prove", action="store_true", help="generate a fresh sequence receipt and verify it")
    mode.add_argument("--verify-existing", action="store_true", help="verify the existing sequence receipt artifact")
    parser.add_argument("--receipt", type=pathlib.Path, default=RECEIPT_OUT)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt_path = resolve_output_path(args.receipt)
    if receipt_path is None:
        raise AttentionKvRisc0SequenceReceiptError("receipt path is required", layer="output_path")
    receipt_path = _resolved_under_root(receipt_path, label="receipt", layer="output_path")
    json_path = resolve_output_path(args.write_json)
    tsv_path = resolve_output_path(args.write_tsv)
    previous_proof_generation_time_ms = None
    if args.verify_existing:
        if json_path is None:
            raise AttentionKvRisc0SequenceReceiptError(
                "--verify-existing requires --write-json pointing at existing sequence evidence",
                layer="output_path",
            )
        previous_json_path = json_path if json_path.is_file() else JSON_OUT
        if not previous_json_path.is_file():
            raise AttentionKvRisc0SequenceReceiptError(
                "--verify-existing requires existing checked attention/KV sequence RISC Zero evidence JSON; use --prove first",
                layer="output_path",
            )
        previous = require_object(load_json(previous_json_path), "previous attention/KV sequence RISC Zero evidence")
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
