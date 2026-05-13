#!/usr/bin/env python3
"""Validate a SNARK statement receipt for the attention-derived d128 contract.

This gate consumes the checked attention-derived d128 outer-proof input
contract and a real verifier-facing snarkjs/Groth16 receipt whose public
signals are derived from that contract. The receipt is only a statement-binding
adapter: it does not prove the underlying Stwo slice verifiers inside Groth16
and it is not the missing native outer proof object.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
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
import subprocess
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_EVIDENCE = EVIDENCE_DIR / "zkai-attention-derived-d128-outer-proof-route-2026-05.json"
SOURCE_GATE_SCRIPT = ROOT / "scripts" / "zkai_attention_derived_d128_outer_proof_route_gate.py"
CONTROL_TWO_SLICE_PUBLIC = EVIDENCE_DIR / "zkai-d128-snark-ivc-statement-receipt-2026-05" / "public.json"
ARTIFACT_DIR = EVIDENCE_DIR / "zkai-attention-derived-d128-snark-statement-receipt-2026-05"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-snark-statement-receipt-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-snark-statement-receipt-2026-05.tsv"

SCHEMA = "zkai-attention-derived-d128-snark-statement-receipt-gate-v1"
RECEIPT_SCHEMA = "zkai-attention-derived-d128-snark-statement-receipt-v1"
STATEMENT_SCHEMA = "zkai-attention-derived-d128-snark-statement-v1"
ARTIFACT_METADATA_SCHEMA = "zkai-attention-derived-d128-snark-statement-receipt-artifact-metadata-v1"
SOURCE_SCHEMA = "zkai-attention-derived-d128-outer-proof-route-gate-v1"
SOURCE_DECISION = "NO_GO_ATTENTION_DERIVED_D128_OUTER_PROOF_OBJECT_MISSING"
SOURCE_RESULT = "BOUNDED_NO_GO"
SOURCE_INPUT_CONTRACT_RESULT = "GO_ATTENTION_DERIVED_D128_OUTER_PROOF_INPUT_CONTRACT"
SOURCE_OUTER_PROOF_RESULT = "NO_GO_EXECUTABLE_ATTENTION_DERIVED_D128_OUTER_PROOF_BACKEND_MISSING"
DECISION = "GO_ATTENTION_DERIVED_D128_SNARK_STATEMENT_RECEIPT_FOR_OUTER_PROOF_INPUT_CONTRACT"
RESULT = "GO"

SNARKJS_VERSION = "0.7.6"
CIRCOM_VERSION = "2.0.9"
PROOF_SYSTEM = "snarkjs/Groth16/BN128"
VERIFIER_DOMAIN = f"snarkjs-groth16-verify-v{SNARKJS_VERSION}:attention-derived-d128-statement-receipt-v1"
SNARKJS_BINARY = ROOT / "scripts" / "node_modules" / ".bin" / "snarkjs"
SNARKJS_ENV = "SNARKJS_PATH"
PUBLIC_FIELD_DOMAIN = "ptvm:zkai:attention-derived-d128:snark-public-field:v1"
STATEMENT_DOMAIN = "ptvm:zkai:attention-derived-d128:snark-statement-receipt:v1"
RECEIPT_DOMAIN = "ptvm:zkai:attention-derived-d128:snark-receipt:v1"
CLAIM_BOUNDARY = "SNARK_STATEMENT_RECEIPT_BINDS_ATTENTION_DERIVED_D128_OUTER_PROOF_INPUT_CONTRACT_NOT_OUTER_PROOF"
SUMMARY = (
    "A real snarkjs/Groth16 verifier-facing receipt accepts the attention-derived d128 "
    "outer-proof input contract as 16 public fields. This is an executable statement "
    "receipt and an external control, not proof of the six Stwo verifier checks."
)
EXTERNAL_SYSTEM = {
    "name": "snarkjs",
    "version": SNARKJS_VERSION,
    "proof_system": PROOF_SYSTEM,
    "verification_api": "snarkjs groth16 verify verification_key.json public.json proof.json",
}
TIMING_POLICY = "not_measured_in_this_gate"
BN128_FIELD_MODULUS = int("21888242871839275222246405745257275088548364400416034343698204186575808495617")
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SNARKJS_OK_LINE_RE = re.compile(r"(?:\[[A-Z]+\]\s+)?snarkJS\s*:\s*OK!?|OK!?")
SNARKJS_VERSION_LINE_RE = re.compile(r"^(?:snarkjs@)?(?P<version>\d+\.\d+\.\d+)$")
DECIMAL_FIELD_RE = re.compile(r"^(0|[1-9][0-9]*)$")
GIT_COMMIT_RE = re.compile(r"^(unknown|[0-9a-f]{40}|[0-9a-f]{64})$")
TSV_COLUMNS = ("mutation", "surface", "baseline_accepted", "mutated_accepted", "rejected", "rejection_layer", "error")
CASE_KEYS = frozenset(
    set(TSV_COLUMNS)
    | {
        "baseline_statement_sha256",
        "mutated_statement_sha256",
        "baseline_statement_commitment",
        "mutated_statement_commitment",
        "baseline_public_signals_sha256",
        "mutated_public_signals_sha256",
    }
)

ARTIFACTS = {
    "circuit": "attention_derived_d128_statement_receipt.circom",
    "input": "input.json",
    "proof": "proof.json",
    "public_signals": "public.json",
    "verification_key": "verification_key.json",
    "metadata": "metadata.json",
}
SNARKJS_VERIFIED_CACHE: set[tuple[tuple[str, ...], str]] = set()
CIRCUIT_TEXT = """pragma circom 2.0.0;

template AttentionDerivedD128StatementReceipt() {
    signal input contract[16];
    signal output digest;
    var acc = 0;
    for (var i = 0; i < 16; i++) {
        contract[i] * 1 === contract[i];
        acc += contract[i];
    }
    digest <== acc;
}

component main { public [contract] } = AttentionDerivedD128StatementReceipt();
"""

GATE_COMMAND = (
    "python3 scripts/zkai_attention_derived_d128_snark_statement_receipt_gate.py "
    "--write-json docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05.json "
    "--write-tsv docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05.tsv"
)
VALIDATION_COMMANDS = [
    "npm ci --prefix scripts",
    GATE_COMMAND,
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_snark_statement_receipt_gate",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_snark_statement_receipt_gate.py scripts/tests/test_zkai_attention_derived_d128_snark_statement_receipt_gate.py",
    "git diff --check",
    "just gate-fast",
    "just gate",
]
ARTIFACT_REGENERATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_snark_statement_receipt_gate.py --write-artifact-inputs",
    "circom docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/attention_derived_d128_statement_receipt.circom --r1cs --wasm --sym -o /tmp/zkai-attention-derived-d128-snark-receipt-build",
    "scripts/node_modules/.bin/snarkjs powersoftau new bn128 12 /tmp/zkai-attention-derived-d128-snark-receipt-build/pot12_0000.ptau -v",
    "scripts/node_modules/.bin/snarkjs powersoftau contribute /tmp/zkai-attention-derived-d128-snark-receipt-build/pot12_0000.ptau /tmp/zkai-attention-derived-d128-snark-receipt-build/pot12_0001.ptau --name=\"attention-derived-d128 local throwaway\" -v -e=\"attention-derived-d128-local-throwaway\"",
    "scripts/node_modules/.bin/snarkjs powersoftau prepare phase2 /tmp/zkai-attention-derived-d128-snark-receipt-build/pot12_0001.ptau /tmp/zkai-attention-derived-d128-snark-receipt-build/pot12_final.ptau -v",
    "scripts/node_modules/.bin/snarkjs groth16 setup /tmp/zkai-attention-derived-d128-snark-receipt-build/attention_derived_d128_statement_receipt.r1cs /tmp/zkai-attention-derived-d128-snark-receipt-build/pot12_final.ptau /tmp/zkai-attention-derived-d128-snark-receipt-build/attention_derived_d128_statement_receipt_0000.zkey",
    "scripts/node_modules/.bin/snarkjs zkey contribute /tmp/zkai-attention-derived-d128-snark-receipt-build/attention_derived_d128_statement_receipt_0000.zkey /tmp/zkai-attention-derived-d128-snark-receipt-build/attention_derived_d128_statement_receipt_final.zkey --name=\"attention-derived-d128 local zkey\" -v -e=\"attention-derived-d128-local-zkey\"",
    "scripts/node_modules/.bin/snarkjs zkey export verificationkey /tmp/zkai-attention-derived-d128-snark-receipt-build/attention_derived_d128_statement_receipt_final.zkey docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/verification_key.json",
    "node /tmp/zkai-attention-derived-d128-snark-receipt-build/attention_derived_d128_statement_receipt_js/generate_witness.js /tmp/zkai-attention-derived-d128-snark-receipt-build/attention_derived_d128_statement_receipt_js/attention_derived_d128_statement_receipt.wasm docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/input.json /tmp/zkai-attention-derived-d128-snark-receipt-build/witness.wtns",
    "scripts/node_modules/.bin/snarkjs groth16 prove /tmp/zkai-attention-derived-d128-snark-receipt-build/attention_derived_d128_statement_receipt_final.zkey /tmp/zkai-attention-derived-d128-snark-receipt-build/witness.wtns docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/proof.json docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/public.json",
    "scripts/node_modules/.bin/snarkjs groth16 verify docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/verification_key.json docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/public.json docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/proof.json",
    "python3 scripts/zkai_attention_derived_d128_snark_statement_receipt_gate.py --write-artifact-metadata",
]

NON_CLAIMS = [
    "not one composed d128 transformer-block proof",
    "not recursive aggregation",
    "not proof-carrying data",
    "not verification of the underlying Stwo slice proofs inside Groth16",
    "not the missing STARK-native outer proof backend",
    "not proof-size evidence for a native fused route",
    "not verifier-time evidence",
    "not proof-generation-time evidence",
    "not a production trusted setup",
    "not a claim that snarkjs or Groth16 is the preferred production backend",
]

PUBLIC_SIGNAL_FIELDS = (
    ("input_contract_commitment", ("input_contract_commitment",)),
    ("block_statement_commitment", ("preimage", "block_statement_commitment")),
    ("compressed_artifact_commitment", ("preimage", "compressed_artifact_commitment")),
    ("verifier_handle_commitment", ("preimage", "verifier_handle_commitment")),
    ("compression_payload_commitment", ("preimage", "compression_payload_commitment")),
    ("source_payload_commitment", ("preimage", "required_public_inputs", "source_payload_commitment")),
    ("derived_input_activation_commitment", ("preimage", "required_public_inputs", "derived_input_activation_commitment")),
    ("source_attention_outputs_commitment", ("preimage", "required_public_inputs", "source_attention_outputs_commitment")),
    ("derived_hidden_activation_commitment", ("preimage", "required_public_inputs", "derived_hidden_activation_commitment")),
    ("derived_output_activation_commitment", ("preimage", "required_public_inputs", "derived_output_activation_commitment")),
    ("derived_residual_delta_commitment", ("preimage", "required_public_inputs", "derived_residual_delta_commitment")),
    ("projection_mul_rows", ("preimage", "required_public_inputs", "projection_mul_rows")),
    ("activation_lookup_rows", ("preimage", "required_public_inputs", "activation_lookup_rows")),
    ("down_projection_mul_rows", ("preimage", "required_public_inputs", "down_projection_mul_rows")),
    ("residual_add_rows", ("preimage", "required_public_inputs", "residual_add_rows")),
    ("accounted_relation_rows", ("preimage", "required_public_inputs", "accounted_relation_rows")),
)

EXPECTED_MUTATION_INVENTORY = (
    ("input_contract_commitment_relabeling", "statement_policy"),
    ("block_statement_commitment_relabeling", "statement_policy"),
    ("compressed_artifact_commitment_relabeling", "statement_policy"),
    ("verifier_handle_commitment_relabeling", "statement_policy"),
    ("compression_payload_commitment_relabeling", "statement_policy"),
    ("source_payload_commitment_relabeling", "statement_policy"),
    ("derived_input_activation_commitment_relabeling", "statement_policy"),
    ("source_attention_outputs_commitment_relabeling", "statement_policy"),
    ("derived_hidden_activation_commitment_relabeling", "statement_policy"),
    ("derived_output_activation_commitment_relabeling", "statement_policy"),
    ("derived_residual_delta_commitment_relabeling", "statement_policy"),
    ("projection_mul_rows_relabeling", "statement_policy"),
    ("activation_lookup_rows_relabeling", "statement_policy"),
    ("down_projection_mul_rows_relabeling", "statement_policy"),
    ("residual_add_rows_relabeling", "statement_policy"),
    ("accounted_relation_rows_relabeling", "statement_policy"),
    ("public_signal_relabeling", "public_signal_binding"),
    ("public_signal_hash_relabeling", "public_signal_binding"),
    ("field_entry_value_relabeling", "public_signal_binding"),
    ("field_entry_label_relabeling", "public_signal_binding"),
    ("proof_hash_relabeling", "artifact_binding"),
    ("verification_key_hash_relabeling", "artifact_binding"),
    ("verification_key_file_hash_relabeling", "artifact_binding"),
    ("circuit_artifact_hash_relabeling", "artifact_binding"),
    ("input_artifact_hash_relabeling", "artifact_binding"),
    ("artifacts_map_drift", "artifact_binding"),
    ("input_payload_drift", "artifact_binding"),
    ("embedded_proof_relabeling", "artifact_binding"),
    ("embedded_vk_relabeling", "artifact_binding"),
    ("embedded_public_signals_relabeling", "artifact_binding"),
    ("setup_commitment_relabeling", "setup_binding"),
    ("proof_size_metric_smuggled", "receipt_metrics"),
    ("verifier_time_metric_smuggled", "receipt_metrics"),
    ("proof_generation_time_metric_smuggled", "receipt_metrics"),
    ("statement_commitment_relabeling", "statement_commitment"),
    ("receipt_commitment_relabeling", "receipt_commitment"),
    ("non_claims_removed", "parser_or_schema"),
    ("unknown_statement_field_added", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
    ("unknown_top_level_field_added", "parser_or_schema"),
)
EXPECTED_MUTATION_NAMES = tuple(name for name, _surface in EXPECTED_MUTATION_INVENTORY)
EXPECTED_MUTATION_SET = frozenset(EXPECTED_MUTATION_NAMES)

class AttentionDerivedD128SnarkReceiptError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def load_json(path: pathlib.Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionDerivedD128SnarkReceiptError(f"failed to load JSON {path}: {err}", layer="artifact_loading") from err


def require_object(value: Any, label: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128SnarkReceiptError(f"{label} must be an object", layer=layer)
    return value


def require_list(value: Any, label: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128SnarkReceiptError(f"{label} must be a list", layer=layer)
    return value


def expect_equal(actual: Any, expected: Any, label: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise AttentionDerivedD128SnarkReceiptError(f"{label} mismatch", layer=layer)


def expect_keys(value: dict[str, Any], expected: set[str], label: str, *, layer: str = "parser_or_schema") -> None:
    keys = set(value)
    if keys != expected:
        raise AttentionDerivedD128SnarkReceiptError(
            f"{label} keys mismatch: missing={sorted(expected - keys)} extra={sorted(keys - expected)}",
            layer=layer,
        )


def artifact_path(key: str) -> pathlib.Path:
    relative = ARTIFACTS[key]
    path = (ARTIFACT_DIR / relative).resolve()
    root = ARTIFACT_DIR.resolve()
    if path != root and root not in path.parents:
        raise AttentionDerivedD128SnarkReceiptError(f"artifact path escapes artifact dir: {relative}", layer="artifact_binding")
    if not path.is_file():
        raise AttentionDerivedD128SnarkReceiptError(f"artifact missing: {relative}", layer="artifact_binding")
    return path


@functools.lru_cache(maxsize=1)
def source_gate_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_attention_derived_d128_outer_proof_route_gate_for_snark_receipt", SOURCE_GATE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionDerivedD128SnarkReceiptError(f"failed to load source gate: {SOURCE_GATE_SCRIPT}", layer="source_contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def source_payload() -> dict[str, Any]:
    payload = require_object(load_json(SOURCE_EVIDENCE), "source evidence", layer="source_contract")
    expect_equal(payload.get("schema"), SOURCE_SCHEMA, "source schema", layer="source_contract")
    expect_equal(payload.get("decision"), SOURCE_DECISION, "source decision", layer="source_contract")
    expect_equal(payload.get("result"), SOURCE_RESULT, "source result", layer="source_contract")
    summary = require_object(payload.get("summary"), "source summary", layer="source_contract")
    expect_equal(summary.get("input_contract_status"), SOURCE_INPUT_CONTRACT_RESULT, "source input contract status", layer="source_contract")
    expect_equal(summary.get("outer_proof_status"), SOURCE_OUTER_PROOF_RESULT, "source outer proof status", layer="source_contract")
    try:
        source_gate_module().validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize source-gate validation failures.
        raise AttentionDerivedD128SnarkReceiptError(f"source route gate validation failed: {err}", layer="source_contract") from err
    return copy.deepcopy(payload)


def source_contract() -> dict[str, Any]:
    payload = source_payload()
    input_contract = require_object(payload.get("input_contract"), "source input_contract", layer="source_contract")
    summary = require_object(payload.get("summary"), "source summary", layer="source_contract")
    return {
        "schema": payload["schema"],
        "decision": payload["decision"],
        "result": payload["result"],
        "input_contract": copy.deepcopy(input_contract),
        "source_summary": copy.deepcopy(summary),
        "source_file_sha256": sha256_file(SOURCE_EVIDENCE),
        "source_payload_sha256": sha256_bytes(canonical_json_bytes(payload)),
    }


def _path_get(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for item in path:
        if not isinstance(current, dict) or item not in current:
            raise AttentionDerivedD128SnarkReceiptError(f"missing contract field: {'.'.join(path)}", layer="source_contract")
        current = current[item]
    return current


def contract_field_entries(contract: dict[str, Any] | None = None) -> list[dict[str, str]]:
    contract = source_contract() if contract is None else copy.deepcopy(contract)
    input_contract = require_object(contract["input_contract"], "input_contract", layer="source_contract")
    entries: list[dict[str, str]] = []
    seen_labels: set[str] = set()

    def add(label: str, value: Any) -> None:
        if label in seen_labels:
            raise AttentionDerivedD128SnarkReceiptError(f"duplicate public signal label: {label}", layer="source_contract")
        seen_labels.add(label)
        if isinstance(value, bool) or value is None:
            raise AttentionDerivedD128SnarkReceiptError(f"{label} must be string or integer", layer="source_contract")
        if not isinstance(value, (str, int)):
            raise AttentionDerivedD128SnarkReceiptError(f"{label} must be string or integer", layer="source_contract")
        text = str(value)
        if not text:
            raise AttentionDerivedD128SnarkReceiptError(f"{label} must be non-empty", layer="source_contract")
        preimage = {"label": label, "value": text}
        digest = hashlib.sha256(PUBLIC_FIELD_DOMAIN.encode("utf-8") + b"\0" + canonical_json_bytes(preimage)).digest()
        field = str(int.from_bytes(digest, "big") % BN128_FIELD_MODULUS)
        entries.append({"label": label, "value": text, "public_signal": field})

    for label, path in PUBLIC_SIGNAL_FIELDS:
        add(label, _path_get(input_contract, path))
    if len(entries) != 16:
        raise AttentionDerivedD128SnarkReceiptError("public signal field count drift", layer="source_contract")
    return entries


def expected_public_signals(entries: list[dict[str, str]] | None = None) -> list[str]:
    entries = contract_field_entries() if entries is None else entries
    fields = [entry["public_signal"] for entry in entries]
    digest = str(sum(int(field) for field in fields) % BN128_FIELD_MODULUS)
    # snarkjs orders public outputs before public inputs.
    return [digest, *fields]


def require_bn128_decimal_field(value: Any, label: str, *, layer: str) -> str:
    if isinstance(value, bool) or value is None:
        raise AttentionDerivedD128SnarkReceiptError(f"{label} must be a decimal BN128 field", layer=layer)
    if isinstance(value, int):
        number = value
        text = str(value)
    elif isinstance(value, str) and DECIMAL_FIELD_RE.fullmatch(value):
        number = int(value)
        text = value
    else:
        raise AttentionDerivedD128SnarkReceiptError(f"{label} must be a decimal BN128 field", layer=layer)
    if number < 0 or number >= BN128_FIELD_MODULUS:
        raise AttentionDerivedD128SnarkReceiptError(f"{label} outside BN128 field", layer=layer)
    return text


def validate_input_artifact(input_json: dict[str, Any], public_signals: list[Any], entries: list[dict[str, str]]) -> None:
    expect_keys(input_json, {"contract"}, "input artifact", layer="artifact_binding")
    contract = require_list(input_json.get("contract"), "input contract", layer="artifact_binding")
    if len(contract) != len(entries):
        raise AttentionDerivedD128SnarkReceiptError("input contract field count mismatch", layer="artifact_binding")
    if len(public_signals) != len(entries) + 1:
        raise AttentionDerivedD128SnarkReceiptError("public signal count mismatch for input artifact", layer="artifact_binding")
    normalized = [
        require_bn128_decimal_field(value, f"input contract[{index}]", layer="artifact_binding")
        for index, value in enumerate(contract)
    ]
    normalized_public_signals = [
        require_bn128_decimal_field(value, f"public_signals[{index}]", layer="artifact_binding")
        for index, value in enumerate(public_signals)
    ]
    expect_equal(normalized, [entry["public_signal"] for entry in entries], "input contract fields", layer="artifact_binding")
    expect_equal(normalized_public_signals[1:], normalized, "input public fields", layer="artifact_binding")
    digest = str(sum(int(value) for value in normalized) % BN128_FIELD_MODULUS)
    expect_equal(normalized_public_signals[0], digest, "input public digest", layer="artifact_binding")


def proof_sha256(proof: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(proof))


def public_signals_sha256(public_signals: list[Any]) -> str:
    return sha256_bytes(canonical_json_bytes(public_signals))


def verification_key_sha256(vk: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(vk))


def statement_commitment(statement: dict[str, Any]) -> str:
    return blake2b_commitment(statement, STATEMENT_DOMAIN)


def receipt_commitment(receipt: dict[str, Any]) -> str:
    preimage = {key: copy.deepcopy(receipt[key]) for key in ("schema", "statement_commitment", "public_signals")}
    return blake2b_commitment(preimage, RECEIPT_DOMAIN)


def statement_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    statement = receipt.get("statement")
    return copy.deepcopy(statement) if isinstance(statement, dict) else {}


def statement_payload_sha256(receipt: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(statement_payload(receipt)))


def expected_artifact_metadata() -> dict[str, Any]:
    artifact_hashes = {}
    for key, relative in ARTIFACTS.items():
        if key == "metadata":
            continue
        artifact_hashes[relative] = sha256_file(artifact_path(key))
    return {
        "schema": ARTIFACT_METADATA_SCHEMA,
        "source_gate": str(SOURCE_GATE_SCRIPT.relative_to(ROOT)),
        "source_evidence": str(SOURCE_EVIDENCE.relative_to(ROOT)),
        "circuit_id": "urn:ptvm:zkai:attention-derived-d128-statement-receipt:v1",
        "proof_system": PROOF_SYSTEM,
        "snarkjs_version": SNARKJS_VERSION,
        "circom_version": CIRCOM_VERSION,
        "generation_note": "Generated locally with circom 2.0.9 and snarkjs 0.7.6; verifier-facing artifacts are checked in, proving key and ceremony transcript are intentionally not checked in.",
        "trusted_setup_note": "Local throwaway Groth16 setup for statement-receipt research only; not a production trusted setup or security endorsement.",
        "artifacts": artifact_hashes,
    }


def artifact_metadata() -> dict[str, Any]:
    metadata = require_object(load_json(artifact_path("metadata")), "metadata", layer="artifact_binding")
    expected = expected_artifact_metadata()
    expect_equal(metadata, expected, "artifact metadata", layer="artifact_binding")
    return copy.deepcopy(metadata)


def baseline_receipt() -> dict[str, Any]:
    metadata = artifact_metadata()
    proof = require_object(load_json(artifact_path("proof")), "proof", layer="artifact_binding")
    public_signals = require_list(load_json(artifact_path("public_signals")), "public signals", layer="artifact_binding")
    verification_key = require_object(load_json(artifact_path("verification_key")), "verification key", layer="artifact_binding")
    input_json = require_object(load_json(artifact_path("input")), "input", layer="artifact_binding")
    contract = source_contract()
    entries = contract_field_entries(contract)
    validate_input_artifact(input_json, public_signals, entries)
    statement = {
        "schema": STATEMENT_SCHEMA,
        "source_contract": contract,
        "proof_system": PROOF_SYSTEM,
        "proof_system_version": SNARKJS_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "public_signal_field_domain": PUBLIC_FIELD_DOMAIN,
        "public_signal_field_entries": entries,
        "expected_public_signals_sha256": public_signals_sha256(expected_public_signals(entries)),
        "circuit_artifact_sha256": sha256_file(artifact_path("circuit")),
        "input_artifact_sha256": sha256_file(artifact_path("input")),
        "verification_key_file_sha256": sha256_file(artifact_path("verification_key")),
        "verification_key_sha256": verification_key_sha256(verification_key),
        "proof_sha256": proof_sha256(proof),
        "public_signals_sha256": public_signals_sha256(public_signals),
        "setup_commitment": metadata["artifacts"]["verification_key.json"],
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "statement": statement,
        "statement_commitment": statement_commitment(statement),
        "artifacts": copy.deepcopy(ARTIFACTS),
        "artifact_metadata": metadata,
        "snarkjs_proof": proof,
        "public_signals": public_signals,
        "verification_key": verification_key,
        "input": input_json,
        "non_claims": list(NON_CLAIMS),
    }
    receipt["receipt_commitment"] = receipt_commitment(receipt)
    return receipt


def _refresh_statement_commitment(receipt: dict[str, Any]) -> None:
    receipt["statement_commitment"] = statement_commitment(receipt["statement"])
    receipt["receipt_commitment"] = receipt_commitment(receipt)


def snarkjs_command() -> tuple[str, ...]:
    configured = os.environ.get(SNARKJS_ENV)
    if configured:
        candidate = pathlib.Path(configured).expanduser().resolve()
        pinned = SNARKJS_BINARY.resolve()
        if candidate != pinned:
            raise AttentionDerivedD128SnarkReceiptError(
                f"{SNARKJS_ENV} override is not allowed for gate evidence; expected {pinned}",
                layer="external_proof_verifier",
            )
        return (str(candidate),)
    return (str(SNARKJS_BINARY),)


def snarkjs_version_reported(output: str) -> bool:
    lines = [line.strip() for line in ANSI_ESCAPE_RE.sub("", output).splitlines() if line.strip()]
    if not lines:
        return False
    match = SNARKJS_VERSION_LINE_RE.fullmatch(lines[0])
    return match is not None and match.group("version") == SNARKJS_VERSION


@functools.lru_cache(maxsize=8)
def assert_snarkjs_version(command: tuple[str, ...]) -> None:
    try:
        result = subprocess.run(
            [*command, "--version"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except subprocess.TimeoutExpired as err:
        raise AttentionDerivedD128SnarkReceiptError("snarkjs version check timed out", layer="external_proof_verifier") from err
    except OSError as err:
        command_text = " ".join(command)
        raise AttentionDerivedD128SnarkReceiptError(
            f"failed to launch snarkjs command `{command_text}`; run `npm ci --prefix scripts` or set {SNARKJS_ENV} to snarkjs {SNARKJS_VERSION}: {err}",
            layer="external_proof_verifier",
        ) from err
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if not snarkjs_version_reported(output):
        if result.returncode != 0:
            clean_output = ANSI_ESCAPE_RE.sub("", output)
            raise AttentionDerivedD128SnarkReceiptError(f"snarkjs version check failed: {clean_output}", layer="external_proof_verifier")
        raise AttentionDerivedD128SnarkReceiptError(
            f"snarkjs version mismatch: expected {SNARKJS_VERSION}, got {ANSI_ESCAPE_RE.sub('', output) or '<empty>'}",
            layer="external_proof_verifier",
        )


def snarkjs_verify(proof: dict[str, Any], public_signals: list[Any], verification_key: dict[str, Any]) -> None:
    command = snarkjs_command()
    proof_bytes = canonical_json_bytes(proof)
    public_bytes = canonical_json_bytes(public_signals)
    vk_bytes = canonical_json_bytes(verification_key)
    cache_key = sha256_bytes(canonical_json_bytes([proof, public_signals, verification_key]))
    _snarkjs_verify_cached(cache_key, proof_bytes, public_bytes, vk_bytes, command)


def snarkjs_verify_reported_ok(output: str) -> bool:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return False
    return SNARKJS_OK_LINE_RE.fullmatch(lines[-1]) is not None


def _snarkjs_verify_cached(cache_key: str, proof_bytes: bytes, public_bytes: bytes, vk_bytes: bytes, command: tuple[str, ...]) -> None:
    cache_token = (command, cache_key)
    if cache_token in SNARKJS_VERIFIED_CACHE:
        return
    assert_snarkjs_version(command)
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        proof_path = tmp / "proof.json"
        public_path = tmp / "public.json"
        vk_path = tmp / "verification_key.json"
        proof_path.write_bytes(proof_bytes)
        public_path.write_bytes(public_bytes)
        vk_path.write_bytes(vk_bytes)
        try:
            result = subprocess.run(
                [*command, "groth16", "verify", str(vk_path), str(public_path), str(proof_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=60,
            )
        except subprocess.TimeoutExpired as err:
            raise AttentionDerivedD128SnarkReceiptError("snarkjs groth16 verifier timed out", layer="external_proof_verifier") from err
        except OSError as err:
            command_text = " ".join([*command, "groth16", "verify"])
            raise AttentionDerivedD128SnarkReceiptError(
                f"failed to launch snarkjs verifier command `{command_text}`; run `npm ci --prefix scripts` or set {SNARKJS_ENV} to snarkjs {SNARKJS_VERSION}: {err}",
                layer="external_proof_verifier",
            ) from err
    output = ANSI_ESCAPE_RE.sub("", "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part))
    if result.returncode != 0:
        raise AttentionDerivedD128SnarkReceiptError(f"snarkjs groth16 verifier rejected: {output}", layer="external_proof_verifier")
    if not snarkjs_verify_reported_ok(output):
        raise AttentionDerivedD128SnarkReceiptError(f"snarkjs groth16 verifier did not report OK: {output}", layer="external_proof_verifier")
    SNARKJS_VERIFIED_CACHE.add(cache_token)


def _snarkjs_payloads(receipt: dict[str, Any]) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    proof = require_object(receipt.get("snarkjs_proof"), "snarkjs_proof")
    public_signals = require_list(receipt.get("public_signals"), "public_signals")
    verification_key = require_object(receipt.get("verification_key"), "verification_key")
    return proof, public_signals, verification_key


def verify_proof_only(receipt: dict[str, Any], *, external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify) -> None:
    proof, public_signals, verification_key = _snarkjs_payloads(receipt)
    external_verify(proof, public_signals, verification_key)


def verify_statement_receipt(
    receipt: dict[str, Any],
    *,
    external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify,
    baseline_snapshot: dict[str, Any] | None = None,
) -> None:
    expected_receipt = baseline_receipt() if baseline_snapshot is None else copy.deepcopy(baseline_snapshot)
    expect_keys(
        receipt,
        {
            "artifacts",
            "artifact_metadata",
            "input",
            "non_claims",
            "public_signals",
            "receipt_commitment",
            "schema",
            "snarkjs_proof",
            "statement",
            "statement_commitment",
            "verification_key",
        },
        "receipt",
    )
    expect_equal(receipt.get("schema"), RECEIPT_SCHEMA, "receipt schema")
    expect_equal(receipt.get("non_claims"), NON_CLAIMS, "non claims")
    expect_equal(receipt.get("artifacts"), ARTIFACTS, "receipt artifacts map", layer="artifact_binding")
    expected_input_payload = require_object(expected_receipt["input"], "expected input payload", layer="artifact_binding")
    expect_equal(receipt.get("input"), expected_input_payload, "receipt input payload", layer="artifact_binding")
    proof, public_signals, verification_key = _snarkjs_payloads(receipt)
    expect_equal(proof, expected_receipt["snarkjs_proof"], "embedded proof artifact", layer="artifact_binding")
    expect_equal(public_signals, expected_receipt["public_signals"], "embedded public signals artifact", layer="artifact_binding")
    expect_equal(verification_key, expected_receipt["verification_key"], "embedded verification key artifact", layer="artifact_binding")
    statement = require_object(receipt.get("statement"), "statement")
    if receipt.get("statement_commitment") != statement_commitment(statement):
        raise AttentionDerivedD128SnarkReceiptError("statement_commitment mismatch", layer="statement_commitment")
    if receipt.get("receipt_commitment") != receipt_commitment(receipt):
        raise AttentionDerivedD128SnarkReceiptError("receipt_commitment mismatch", layer="receipt_commitment")
    expected_statement = expected_receipt["statement"]
    expect_keys(statement, set(expected_statement), "statement", layer="parser_or_schema")
    for key in (
        "schema",
        "source_contract",
        "proof_system",
        "proof_system_version",
        "verifier_domain",
        "public_signal_field_domain",
        "public_signal_field_entries",
        "expected_public_signals_sha256",
    ):
        expect_equal(statement.get(key), expected_statement[key], key, layer="statement_policy" if key != "verifier_domain" else "domain_or_version_allowlist")
    expect_equal(receipt.get("artifact_metadata"), expected_receipt["artifact_metadata"], "receipt artifact metadata", layer="artifact_binding")
    artifact_hashes = expected_receipt["artifact_metadata"]["artifacts"]
    artifact_checks = {
        "circuit_artifact_sha256": "attention_derived_d128_statement_receipt.circom",
        "input_artifact_sha256": "input.json",
        "verification_key_file_sha256": "verification_key.json",
    }
    for statement_key, metadata_name in artifact_checks.items():
        expect_equal(statement.get(statement_key), artifact_hashes.get(metadata_name), statement_key, layer="artifact_binding")
    expect_equal(verification_key_sha256(verification_key), statement.get("verification_key_sha256"), "verification key canonical hash", layer="artifact_binding")
    expect_equal(proof_sha256(proof), statement.get("proof_sha256"), "proof hash", layer="artifact_binding")
    expect_equal(public_signals_sha256(public_signals), statement.get("public_signals_sha256"), "public signals hash", layer="public_signal_binding")
    expect_equal(public_signals, expected_public_signals(statement["public_signal_field_entries"]), "public signals", layer="public_signal_binding")
    expect_equal(public_signals_sha256(public_signals), statement.get("expected_public_signals_sha256"), "expected public signals digest", layer="public_signal_binding")
    expect_equal(statement.get("setup_commitment"), artifact_hashes.get("verification_key.json"), "setup commitment", layer="setup_binding")
    external_verify(proof, public_signals, verification_key)


def mutated_receipts(baseline_snapshot: dict[str, Any] | None = None) -> dict[str, tuple[str, dict[str, Any]]]:
    baseline = baseline_receipt() if baseline_snapshot is None else copy.deepcopy(baseline_snapshot)

    def set_path(root: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
        current: Any = root
        for item in path[:-1]:
            current = current[item]
        current[path[-1]] = value

    def mutate(name: str, surface: str, fn: Callable[[dict[str, Any]], None], *, refresh: bool = True) -> None:
        receipt = copy.deepcopy(baseline)
        fn(receipt)
        if refresh:
            _refresh_statement_commitment(receipt)
        out[name] = (surface, receipt)

    input_root = ("statement", "source_contract", "input_contract")
    preimage_root = (*input_root, "preimage")
    required_root = (*preimage_root, "required_public_inputs")
    out: dict[str, tuple[str, dict[str, Any]]] = {}
    mutate("input_contract_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*input_root, "input_contract_commitment"), "blake2b-256:" + "00" * 32))
    mutate("block_statement_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*preimage_root, "block_statement_commitment"), "blake2b-256:" + "11" * 32))
    mutate("compressed_artifact_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*preimage_root, "compressed_artifact_commitment"), "blake2b-256:" + "22" * 32))
    mutate("verifier_handle_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*preimage_root, "verifier_handle_commitment"), "blake2b-256:" + "33" * 32))
    mutate("compression_payload_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*preimage_root, "compression_payload_commitment"), "sha256:" + "44" * 32))
    mutate("source_payload_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "source_payload_commitment"), "sha256:" + "55" * 32))
    mutate("derived_input_activation_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "derived_input_activation_commitment"), "blake2b-256:" + "66" * 32))
    mutate("source_attention_outputs_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "source_attention_outputs_commitment"), "blake2b-256:" + "77" * 32))
    mutate("derived_hidden_activation_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "derived_hidden_activation_commitment"), "blake2b-256:" + "88" * 32))
    mutate("derived_output_activation_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "derived_output_activation_commitment"), "blake2b-256:" + "99" * 32))
    mutate("derived_residual_delta_commitment_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "derived_residual_delta_commitment"), "blake2b-256:" + "aa" * 32))
    mutate("projection_mul_rows_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "projection_mul_rows"), 1))
    mutate("activation_lookup_rows_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "activation_lookup_rows"), 1))
    mutate("down_projection_mul_rows_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "down_projection_mul_rows"), 1))
    mutate("residual_add_rows_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "residual_add_rows"), 1))
    mutate("accounted_relation_rows_relabeling", "statement_policy", lambda r: set_path(r, (*required_root, "accounted_relation_rows"), 1))
    mutate("public_signal_relabeling", "public_signal_binding", lambda r: r["public_signals"].__setitem__(0, "12345"))
    mutate("public_signal_hash_relabeling", "public_signal_binding", lambda r: r["statement"].__setitem__("public_signals_sha256", "bb" * 32))
    mutate("field_entry_value_relabeling", "public_signal_binding", lambda r: r["statement"]["public_signal_field_entries"][0].__setitem__("value", "blake2b-256:" + "cc" * 32))
    mutate("field_entry_label_relabeling", "public_signal_binding", lambda r: r["statement"]["public_signal_field_entries"][0].__setitem__("label", "wrong-label"))
    mutate("proof_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("proof_sha256", "dd" * 32))
    mutate("verification_key_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("verification_key_sha256", "ee" * 32))
    mutate("verification_key_file_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("verification_key_file_sha256", "ff" * 32))
    mutate("circuit_artifact_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("circuit_artifact_sha256", "00" * 32))
    mutate("input_artifact_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("input_artifact_sha256", "11" * 32))
    mutate("artifacts_map_drift", "artifact_binding", lambda r: r["artifacts"].__setitem__("proof", "other-proof.json"))
    mutate("input_payload_drift", "artifact_binding", lambda r: r["input"].__setitem__("contract", r["input"]["contract"][:-1]))
    mutate("embedded_proof_relabeling", "artifact_binding", lambda r: (r["snarkjs_proof"].__setitem__("protocol", "tampered"), r["statement"].__setitem__("proof_sha256", proof_sha256(r["snarkjs_proof"]))))
    mutate("embedded_vk_relabeling", "artifact_binding", lambda r: (r["verification_key"].__setitem__("protocol", "tampered"), r["statement"].__setitem__("verification_key_sha256", verification_key_sha256(r["verification_key"]))))
    mutate("embedded_public_signals_relabeling", "artifact_binding", lambda r: (r["public_signals"].__setitem__(0, str((int(r["public_signals"][0]) + 1) % BN128_FIELD_MODULUS)), r["statement"].__setitem__("public_signals_sha256", public_signals_sha256(r["public_signals"]))))
    mutate("setup_commitment_relabeling", "setup_binding", lambda r: r["statement"].__setitem__("setup_commitment", "22" * 32))
    mutate("proof_size_metric_smuggled", "receipt_metrics", lambda r: r.setdefault("receipt_metrics", {}).__setitem__("proof_size_bytes", 1))
    mutate("verifier_time_metric_smuggled", "receipt_metrics", lambda r: r.setdefault("receipt_metrics", {}).__setitem__("verifier_time_ms", 0.001))
    mutate("proof_generation_time_metric_smuggled", "receipt_metrics", lambda r: r.setdefault("receipt_metrics", {}).__setitem__("proof_generation_time_ms", 0.001))
    mutate("statement_commitment_relabeling", "statement_commitment", lambda r: r.__setitem__("statement_commitment", "blake2b-256:" + "12" * 32), refresh=False)
    mutate("receipt_commitment_relabeling", "receipt_commitment", lambda r: r.__setitem__("receipt_commitment", "blake2b-256:" + "34" * 32), refresh=False)
    mutate("non_claims_removed", "parser_or_schema", lambda r: r.__setitem__("non_claims", r["non_claims"][:-1]))
    mutate("unknown_statement_field_added", "parser_or_schema", lambda r: r["statement"].__setitem__("unexpected", True))
    mutate("validation_command_drift", "parser_or_schema", lambda r: r.__setitem__("validation_commands", ["echo fake"]))
    mutate("unknown_top_level_field_added", "parser_or_schema", lambda r: r.__setitem__("unexpected", True))
    return out


def _case_result(
    receipt: dict[str, Any],
    external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None],
    baseline_snapshot: dict[str, Any] | None = None,
) -> tuple[bool, str, str]:
    try:
        verify_statement_receipt(receipt, external_verify=external_verify, baseline_snapshot=baseline_snapshot)
    except AttentionDerivedD128SnarkReceiptError as err:
        return False, str(err), err.layer
    return True, "", "accepted"


def proof_verifier_public_signal_check(
    baseline: dict[str, Any],
    external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None],
) -> dict[str, Any]:
    mutated = copy.deepcopy(baseline)
    mutated["public_signals"][0] = "12345" if mutated["public_signals"][0] != "12345" else "67890"
    try:
        verify_proof_only(mutated, external_verify=external_verify)
    except AttentionDerivedD128SnarkReceiptError as err:
        return {
            "baseline_accepted": True,
            "mutated_accepted": False,
            "rejected": True,
            "rejection_layer": err.layer,
            "error": str(err),
        }
    return {
        "baseline_accepted": True,
        "mutated_accepted": True,
        "rejected": False,
        "rejection_layer": "accepted",
        "error": "",
    }


def statement_receipt_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": receipt["schema"],
        "statement_commitment": receipt["statement_commitment"],
        "receipt_commitment": receipt["receipt_commitment"],
        "proof_system": PROOF_SYSTEM,
        "proof_system_version": SNARKJS_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "public_signal_count": len(receipt["public_signals"]),
        "public_signal_field_count": len(receipt["statement"]["public_signal_field_entries"]),
        "public_signals_sha256": public_signals_sha256(receipt["public_signals"]),
        "proof_sha256": receipt["statement"]["proof_sha256"],
        "verification_key_sha256": receipt["statement"]["verification_key_sha256"],
    }


def source_route_metrics(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = source_contract() if contract is None else contract
    summary = require_object(contract["source_summary"], "source summary", layer="source_contract")
    return {
        "source_chain_artifact_bytes": summary["source_chain_artifact_bytes"],
        "compressed_artifact_bytes": summary["compressed_artifact_bytes"],
        "byte_savings": summary["byte_savings"],
        "compressed_to_source_ratio": summary["compressed_to_source_ratio"],
        "source_relation_rows": summary["source_relation_rows"],
        "slice_count": summary["slice_count"],
        "edge_count": summary["edge_count"],
        "input_contract_commitment": contract["input_contract"]["input_contract_commitment"],
        "block_statement_commitment": summary["block_statement_commitment"],
    }


def expected_receipt_metrics() -> dict[str, Any]:
    public_signals = require_list(load_json(artifact_path("public_signals")), "public signals", layer="receipt_metrics")
    return {
        "proof_size_bytes": artifact_path("proof").stat().st_size,
        "public_signals_bytes": artifact_path("public_signals").stat().st_size,
        "verification_key_bytes": artifact_path("verification_key").stat().st_size,
        "public_signal_count": len(public_signals),
        "public_signal_field_count": len(public_signals) - 1,
        "verifier_time_ms": None,
        "proof_generation_time_ms": None,
        "timing_policy": TIMING_POLICY,
    }


def control_public_signal_comparison() -> dict[str, Any]:
    control = require_list(load_json(CONTROL_TWO_SLICE_PUBLIC), "control two-slice public signals", layer="source_contract")
    current = expected_public_signals()
    return {
        "control": "zkai-d128-snark-ivc-statement-receipt-2026-05",
        "control_public_signal_count": len(control),
        "attention_public_signal_count": len(current),
        "same_public_signals": control == current,
        "matching_positions": sum(1 for left, right in zip(control, current, strict=False) if left == right),
        "message": "the existing two-slice SNARK receipt public signals do not bind this attention-derived contract",
    }


def run_gate(external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify) -> dict[str, Any]:
    baseline = baseline_receipt()
    source = copy.deepcopy(baseline["statement"]["source_contract"])
    verify_proof_only(baseline, external_verify=external_verify)
    verify_statement_receipt(baseline, external_verify=external_verify, baseline_snapshot=baseline)
    proof_verifier_check = proof_verifier_public_signal_check(baseline, external_verify)
    mutations = mutated_receipts(baseline)
    if set(mutations) != EXPECTED_MUTATION_SET:
        raise RuntimeError("mutation corpus does not match expected attention-derived d128 SNARK receipt suite")
    cases = []
    for mutation, (surface, receipt) in sorted(mutations.items()):
        accepted, error, layer = _case_result(receipt, external_verify, baseline)
        cases.append(
            {
                "mutation": mutation,
                "surface": surface,
                "baseline_accepted": True,
                "mutated_accepted": accepted,
                "rejected": not accepted,
                "rejection_layer": layer,
                "error": error,
                "baseline_statement_sha256": statement_payload_sha256(baseline),
                "mutated_statement_sha256": statement_payload_sha256(receipt),
                "baseline_statement_commitment": baseline.get("statement_commitment", ""),
                "mutated_statement_commitment": receipt.get("statement_commitment", ""),
                "baseline_public_signals_sha256": public_signals_sha256(baseline["public_signals"]),
                "mutated_public_signals_sha256": public_signals_sha256(receipt.get("public_signals", [])),
            }
        )
    all_rejected = all(case["rejected"] for case in cases)
    receipt = baseline
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_route_decision": SOURCE_DECISION,
        "source_route_result": SOURCE_RESULT,
        "source_contract": source,
        "source_route_metrics": source_route_metrics(source),
        "statement_receipt": statement_receipt_summary(receipt),
        "proof_verifier_checks": {
            "public_signal_relabeling": proof_verifier_check,
        },
        "control_receipt_comparison": control_public_signal_comparison(),
        "receipt_metrics": expected_receipt_metrics(),
        "external_system": copy.deepcopy(EXTERNAL_SYSTEM),
        "artifact_metadata": artifact_metadata(),
        "artifact_paths": {key: str(artifact_path(key).relative_to(ROOT)) for key in ARTIFACTS},
        "mutation_inventory": [{"mutation": name, "surface": surface} for name, surface in EXPECTED_MUTATION_INVENTORY],
        "case_count": len(cases),
        "all_mutations_rejected": all_rejected,
        "cases": cases,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "artifact_regeneration_commands": list(ARTIFACT_REGENERATION_COMMANDS),
        "repro": {
            "git_commit": _git_commit(),
            "command": GATE_COMMAND,
        },
        "summary": SUMMARY,
    }
    validate_payload(payload, source_snapshot=source, baseline_snapshot=baseline)
    return payload


def validate_payload(
    payload: dict[str, Any],
    *,
    source_snapshot: dict[str, Any] | None = None,
    baseline_snapshot: dict[str, Any] | None = None,
) -> None:
    expected_keys = {
        "schema", "decision", "result", "claim_boundary", "source_route_decision", "source_route_result",
        "source_contract", "source_route_metrics", "statement_receipt", "proof_verifier_checks",
        "control_receipt_comparison", "receipt_metrics", "external_system", "artifact_metadata", "artifact_paths",
        "mutation_inventory", "case_count", "all_mutations_rejected", "cases", "non_claims",
        "validation_commands", "artifact_regeneration_commands", "repro", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    expect_equal(payload["schema"], SCHEMA, "schema")
    expect_equal(payload["decision"], DECISION, "decision")
    expect_equal(payload["result"], RESULT, "result")
    expect_equal(payload["claim_boundary"], CLAIM_BOUNDARY, "claim boundary")
    expect_equal(payload["source_route_decision"], SOURCE_DECISION, "source route decision")
    expect_equal(payload["source_route_result"], SOURCE_RESULT, "source route result")
    source = source_contract() if source_snapshot is None else copy.deepcopy(source_snapshot)
    expect_equal(payload["source_contract"], source, "source contract", layer="source_contract")
    expect_equal(payload["source_route_metrics"], source_route_metrics(source), "source route metrics", layer="source_contract")
    receipt = baseline_receipt() if baseline_snapshot is None else copy.deepcopy(baseline_snapshot)
    expect_equal(payload["statement_receipt"], statement_receipt_summary(receipt), "statement receipt", layer="statement_policy")
    expect_equal(payload["external_system"], EXTERNAL_SYSTEM, "external system", layer="external_proof_verifier")
    expect_equal(payload["artifact_metadata"], receipt["artifact_metadata"], "artifact metadata", layer="artifact_binding")
    expect_equal(payload["artifact_paths"], {key: str(artifact_path(key).relative_to(ROOT)) for key in ARTIFACTS}, "artifact paths", layer="artifact_binding")
    expect_equal(payload["non_claims"], NON_CLAIMS, "non claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation commands")
    expect_equal(payload["artifact_regeneration_commands"], ARTIFACT_REGENERATION_COMMANDS, "artifact regeneration commands")
    expect_equal(payload["summary"], SUMMARY, "summary")
    expect_equal(payload["control_receipt_comparison"], control_public_signal_comparison(), "control receipt comparison", layer="source_contract")
    repro = require_object(payload["repro"], "repro")
    expect_keys(repro, {"git_commit", "command"}, "repro")
    expect_equal(repro.get("command"), GATE_COMMAND, "repro command")
    git_commit = repro.get("git_commit")
    if not isinstance(git_commit, str) or not GIT_COMMIT_RE.fullmatch(git_commit):
        raise AttentionDerivedD128SnarkReceiptError("repro git_commit must be unknown or a hex commit", layer="parser_or_schema")
    inventory = require_list(payload["mutation_inventory"], "mutation inventory")
    inventory_entries = []
    for index, item in enumerate(inventory):
        entry = require_object(item, f"mutation inventory[{index}]")
        expect_keys(entry, {"mutation", "surface"}, f"mutation inventory[{index}]")
        inventory_entries.append((entry.get("mutation"), entry.get("surface")))
    expect_equal(tuple(inventory_entries), EXPECTED_MUTATION_INVENTORY, "mutation inventory")
    cases = require_list(payload["cases"], "cases")
    case_entries = []
    for index, item in enumerate(cases):
        case = require_object(item, f"case[{index}]")
        expect_keys(case, set(CASE_KEYS), f"case[{index}]")
        case_entries.append(case)
    expect_equal(len(case_entries), len(EXPECTED_MUTATION_INVENTORY), "case count")
    expect_equal(payload["case_count"], len(case_entries), "case_count")
    if not payload["all_mutations_rejected"] or not all(case.get("rejected") is True for case in case_entries):
        raise AttentionDerivedD128SnarkReceiptError("not all attention-derived SNARK receipt mutations rejected", layer="mutation_suite")
    by_name = {case.get("mutation"): case for case in case_entries}
    expect_equal(set(by_name), EXPECTED_MUTATION_SET, "case mutation set")
    for mutation, surface in EXPECTED_MUTATION_INVENTORY:
        case = by_name[mutation]
        expect_equal(case.get("surface"), surface, f"surface for {mutation}")
        if case.get("mutated_accepted") is True:
            raise AttentionDerivedD128SnarkReceiptError(f"mutation accepted: {mutation}", layer="mutation_suite")
    expect_equal(require_object(payload["receipt_metrics"], "receipt metrics"), expected_receipt_metrics(), "receipt metrics", layer="receipt_metrics")
    proof_checks = require_object(payload["proof_verifier_checks"], "proof verifier checks")
    public_signal_check = require_object(proof_checks.get("public_signal_relabeling"), "public signal proof verifier check")
    if public_signal_check.get("rejected") is not True or public_signal_check.get("rejection_layer") != "external_proof_verifier":
        raise AttentionDerivedD128SnarkReceiptError("raw proof verifier did not reject public signal relabeling", layer="external_proof_verifier")


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for index, item in enumerate(require_list(payload.get("cases"), "cases")):
        case = require_object(item, f"case[{index}]")
        missing = set(TSV_COLUMNS) - set(case)
        if missing:
            raise AttentionDerivedD128SnarkReceiptError(f"case[{index}] missing TSV keys: {sorted(missing)}", layer="parser_or_schema")
        row = {key: case[key] for key in TSV_COLUMNS}
        if row["error"] == "":
            row["error"] = "none"
        writer.writerow(row)
    return output.getvalue()


def write_text_checked(path: pathlib.Path, text: str, *, root: pathlib.Path = EVIDENCE_DIR) -> None:
    resolved = path.resolve()
    allowed = root.resolve()
    if allowed not in resolved.parents:
        raise AttentionDerivedD128SnarkReceiptError(f"output path must stay under {root}", layer="output_path")
    if resolved.exists() and resolved.is_dir():
        raise AttentionDerivedD128SnarkReceiptError(f"output path must be a file: {path}", layer="output_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_artifact_inputs() -> None:
    entries = contract_field_entries()
    write_text_checked(ARTIFACT_DIR / ARTIFACTS["circuit"], CIRCUIT_TEXT, root=ARTIFACT_DIR)
    input_text = json.dumps({"contract": [entry["public_signal"] for entry in entries]}, sort_keys=True, separators=(",", ":")) + "\n"
    write_text_checked(ARTIFACT_DIR / ARTIFACTS["input"], input_text, root=ARTIFACT_DIR)


def write_artifact_metadata() -> None:
    metadata = expected_artifact_metadata()
    text = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    write_text_checked(ARTIFACT_DIR / ARTIFACTS["metadata"], text, root=ARTIFACT_DIR)


def _git_commit() -> str:
    git = shutil.which("git")
    if git is None:
        return "unknown"
    try:
        return subprocess.check_output([git, "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON result")
    parser.add_argument("--tsv", action="store_true", help="print TSV result")
    parser.add_argument("--write-json", type=pathlib.Path, help="write JSON evidence under docs/engineering/evidence")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write TSV evidence under docs/engineering/evidence")
    parser.add_argument("--write-artifact-inputs", action="store_true", help="write the circuit and input.json artifacts")
    parser.add_argument("--write-artifact-metadata", action="store_true", help="write metadata.json after proof artifacts exist")
    args = parser.parse_args(argv)
    if args.write_artifact_inputs:
        write_artifact_inputs()
        if not any((args.json, args.tsv, args.write_json, args.write_tsv, args.write_artifact_metadata)):
            return 0
    if args.write_artifact_metadata:
        write_artifact_metadata()
        if not any((args.json, args.tsv, args.write_json, args.write_tsv)):
            return 0
    payload = run_gate()
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tsv_text = to_tsv(payload)
    if args.write_json:
        write_text_checked(args.write_json, json_text)
    if args.write_tsv:
        write_text_checked(args.write_tsv, tsv_text)
    if args.json:
        print(json_text, end="")
    if args.tsv:
        print(tsv_text, end="")
    if not (args.json or args.tsv or args.write_json or args.write_tsv or args.write_artifact_inputs or args.write_artifact_metadata):
        metrics = payload["receipt_metrics"]
        print(
            "PASS: attention-derived d128 SNARK statement receipt accepted; "
            f"proof={metrics['proof_size_bytes']} bytes; "
            f"public_signals={metrics['public_signal_count']}; "
            f"rejected {payload['case_count']}/{payload['case_count']} mutations"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
