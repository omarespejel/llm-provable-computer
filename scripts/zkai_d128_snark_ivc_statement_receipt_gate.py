#!/usr/bin/env python3
"""Validate a SNARK statement receipt for the d128 two-slice contract.

This gate answers issue #428. It consumes the checked proof-native d128
#424 two-slice public-input contract and a real verifier-facing snarkjs/Groth16
receipt whose public signals are derived from that contract. The receipt is
only a statement-binding adapter: it does not prove the underlying Stwo slice
relations inside Groth16 and it is not recursion/PCD.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import copy
import csv
import functools
import hashlib
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
SOURCE_EVIDENCE = EVIDENCE_DIR / "zkai-d128-proof-native-two-slice-compression-2026-05.json"
ARTIFACT_DIR = EVIDENCE_DIR / "zkai-d128-snark-ivc-statement-receipt-2026-05"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-snark-ivc-statement-receipt-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-snark-ivc-statement-receipt-2026-05.tsv"

SCHEMA = "zkai-d128-snark-ivc-statement-receipt-gate-v1"
RECEIPT_SCHEMA = "zkai-d128-snark-ivc-statement-receipt-v1"
STATEMENT_SCHEMA = "zkai-d128-two-slice-snark-statement-v1"
DECISION = "GO_D128_SNARK_STATEMENT_RECEIPT_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT"
RESULT = "GO"
ISSUE = 428
SOURCE_ISSUE = 424
SOURCE_SCHEMA = "zkai-d128-proof-native-two-slice-compression-gate-v1"
SOURCE_DECISION = "GO_D128_PROOF_NATIVE_TWO_SLICE_TRANSCRIPT_COMPRESSION"
SOURCE_RESULT = "GO"
SOURCE_COMPRESSED_RESULT = "GO_PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION"
SOURCE_RECURSIVE_RESULT = "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING"

SNARKJS_VERSION = "0.7.6"
PROOF_SYSTEM = "snarkjs/Groth16/BN128"
VERIFIER_DOMAIN = f"snarkjs-groth16-verify-v{SNARKJS_VERSION}:d128-two-slice-statement-receipt-v1"
SNARKJS_COMMAND = ("npx", "-y", f"snarkjs@{SNARKJS_VERSION}")
PUBLIC_FIELD_DOMAIN = "ptvm:zkai:d128:snark-public-field:v1"
STATEMENT_DOMAIN = "ptvm:zkai:d128:snark-statement-receipt:v1"
RECEIPT_DOMAIN = "ptvm:zkai:d128:snark-receipt:v1"
BN128_FIELD_MODULUS = int("21888242871839275222246405745257275088548364400416034343698204186575808495617")
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

ARTIFACTS = {
    "circuit": "d128_statement_receipt.circom",
    "input": "input.json",
    "proof": "proof.json",
    "public_signals": "public.json",
    "verification_key": "verification_key.json",
    "metadata": "metadata.json",
}

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_snark_ivc_statement_receipt_gate.py --write-json docs/engineering/evidence/zkai-d128-snark-ivc-statement-receipt-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-snark-ivc-statement-receipt-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_snark_ivc_statement_receipt_gate",
    "python3 -m py_compile scripts/zkai_d128_snark_ivc_statement_receipt_gate.py scripts/tests/test_zkai_d128_snark_ivc_statement_receipt_gate.py",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

NON_CLAIMS = [
    "not recursive aggregation",
    "not proof-carrying data",
    "not STARK-in-SNARK verification",
    "not verification of the underlying Stwo slice proofs inside Groth16",
    "not a production trusted setup",
    "not a prover-performance benchmark",
    "not a zkVM receipt",
    "not onchain deployment evidence",
    "not a claim that snarkjs or Groth16 is the preferred production backend",
]

EXPECTED_MUTATION_INVENTORY = (
    ("target_commitment_relabeling", "statement_policy"),
    ("selected_statement_commitment_relabeling", "statement_policy"),
    ("selected_source_file_hash_relabeling", "statement_policy"),
    ("selected_source_payload_hash_relabeling", "statement_policy"),
    ("selected_public_instance_commitment_relabeling", "statement_policy"),
    ("selected_parameter_commitment_relabeling", "statement_policy"),
    ("verifier_domain_relabeling", "domain_or_version_allowlist"),
    ("required_backend_version_relabeling", "statement_policy"),
    ("source_accumulator_commitment_relabeling", "statement_policy"),
    ("source_verifier_handle_commitment_relabeling", "statement_policy"),
    ("compressed_artifact_commitment_relabeling", "statement_policy"),
    ("public_signal_relabeling", "public_signal_binding"),
    ("public_signal_hash_relabeling", "public_signal_binding"),
    ("field_entry_value_relabeling", "public_signal_binding"),
    ("field_entry_label_relabeling", "public_signal_binding"),
    ("proof_hash_relabeling", "artifact_binding"),
    ("verification_key_hash_relabeling", "artifact_binding"),
    ("verification_key_file_hash_relabeling", "artifact_binding"),
    ("circuit_artifact_hash_relabeling", "artifact_binding"),
    ("input_artifact_hash_relabeling", "artifact_binding"),
    ("setup_commitment_relabeling", "setup_binding"),
    ("proof_size_metric_smuggled", "receipt_metrics"),
    ("verifier_time_metric_smuggled", "receipt_metrics"),
    ("proof_generation_time_metric_smuggled", "receipt_metrics"),
    ("statement_commitment_relabeling", "statement_commitment"),
    ("receipt_commitment_relabeling", "receipt_commitment"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
    ("unknown_top_level_field_added", "parser_or_schema"),
)
EXPECTED_MUTATION_NAMES = tuple(name for name, _surface in EXPECTED_MUTATION_INVENTORY)
EXPECTED_MUTATION_SET = frozenset(EXPECTED_MUTATION_NAMES)
TSV_COLUMNS = ("mutation", "surface", "baseline_accepted", "mutated_accepted", "rejected", "rejection_layer", "error")


class D128SnarkReceiptError(ValueError):
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
        raise D128SnarkReceiptError(f"failed to load JSON {path}: {err}", layer="artifact_loading") from err


def require_object(value: Any, label: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128SnarkReceiptError(f"{label} must be an object", layer=layer)
    return value


def require_list(value: Any, label: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise D128SnarkReceiptError(f"{label} must be a list", layer=layer)
    return value


def expect_equal(actual: Any, expected: Any, label: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise D128SnarkReceiptError(f"{label} mismatch", layer=layer)


def expect_keys(value: dict[str, Any], expected: set[str], label: str, *, layer: str = "parser_or_schema") -> None:
    keys = set(value)
    if keys != expected:
        raise D128SnarkReceiptError(
            f"{label} keys mismatch: missing={sorted(expected - keys)} extra={sorted(keys - expected)}",
            layer=layer,
        )


def artifact_path(key: str) -> pathlib.Path:
    relative = ARTIFACTS[key]
    path = (ARTIFACT_DIR / relative).resolve()
    root = ARTIFACT_DIR.resolve()
    if path != root and root not in path.parents:
        raise D128SnarkReceiptError(f"artifact path escapes artifact dir: {relative}", layer="artifact_binding")
    if not path.is_file():
        raise D128SnarkReceiptError(f"artifact missing: {relative}", layer="artifact_binding")
    return path


@functools.lru_cache(maxsize=1)
def source_payload() -> dict[str, Any]:
    payload = require_object(load_json(SOURCE_EVIDENCE), "source evidence", layer="source_contract")
    expect_equal(payload.get("schema"), SOURCE_SCHEMA, "source schema", layer="source_contract")
    expect_equal(payload.get("issue"), SOURCE_ISSUE, "source issue", layer="source_contract")
    expect_equal(payload.get("decision"), SOURCE_DECISION, "source decision", layer="source_contract")
    expect_equal(payload.get("result"), SOURCE_RESULT, "source result", layer="source_contract")
    expect_equal(payload.get("compression_result"), SOURCE_COMPRESSED_RESULT, "source compression result", layer="source_contract")
    expect_equal(payload.get("recursive_or_pcd_result"), SOURCE_RECURSIVE_RESULT, "source recursive result", layer="source_contract")
    return copy.deepcopy(payload)


def source_contract() -> dict[str, Any]:
    payload = source_payload()
    compressed_artifact = require_object(payload.get("compressed_artifact"), "source compressed_artifact", layer="source_contract")
    preimage = require_object(compressed_artifact.get("preimage"), "source compressed artifact preimage", layer="source_contract")
    contract = require_object(preimage.get("proof_native_public_input_contract"), "source public-input contract", layer="source_contract")
    return {
        "schema": payload["schema"],
        "issue": payload["issue"],
        "decision": payload["decision"],
        "result": payload["result"],
        "compression_result": payload["compression_result"],
        "recursive_or_pcd_result": payload["recursive_or_pcd_result"],
        "compressed_artifact_commitment": compressed_artifact["compressed_artifact_commitment"],
        "source_payload_sha256": sha256_bytes(canonical_json_bytes(payload)),
        "source_file_sha256": sha256_file(SOURCE_EVIDENCE),
        "public_input_contract": copy.deepcopy(contract),
    }


def contract_field_entries(contract: dict[str, Any] | None = None) -> list[dict[str, str]]:
    contract = source_contract() if contract is None else copy.deepcopy(contract)
    public_input = require_object(contract["public_input_contract"], "public_input_contract", layer="source_contract")
    entries: list[dict[str, str]] = []

    def add(label: str, value: str) -> None:
        if not isinstance(value, str) or not value:
            raise D128SnarkReceiptError(f"{label} must be a non-empty string", layer="source_contract")
        preimage = {"label": label, "value": value}
        digest = hashlib.sha256(PUBLIC_FIELD_DOMAIN.encode("utf-8") + b"\0" + canonical_json_bytes(preimage)).digest()
        field = str(int.from_bytes(digest, "big") % BN128_FIELD_MODULUS)
        entries.append({"label": label, "value": value, "public_signal": field})

    add("two_slice_target_commitment", public_input["two_slice_target_commitment"])
    for item in public_input["selected_slice_statement_commitments"]:
        add(f"selected_slice_statement_commitment:{item['slice_id']}", item["statement_commitment"])
    for item in public_input["selected_source_evidence_hashes"]:
        add(f"selected_source_file_sha256:{item['slice_id']}", item["source_file_sha256"])
        add(f"selected_source_payload_sha256:{item['slice_id']}", item["source_payload_sha256"])
    for item in public_input["selected_slice_public_instance_commitments"]:
        add(f"selected_public_instance_commitment:{item['slice_id']}", item["public_instance_commitment"])
    for item in public_input["selected_slice_proof_native_parameter_commitments"]:
        add(f"selected_parameter_commitment:{item['slice_id']}", item["proof_native_parameter_commitment"])
    add("verifier_domain", public_input["verifier_domain"])
    add("required_backend_version", public_input["required_backend_version"])
    add("source_accumulator_commitment", public_input["source_accumulator_commitment"])
    add("source_verifier_handle_commitment", public_input["source_verifier_handle_commitment"])
    add("compressed_artifact_commitment", contract["compressed_artifact_commitment"])
    return entries


def expected_public_signals(entries: list[dict[str, str]] | None = None) -> list[str]:
    entries = contract_field_entries() if entries is None else entries
    fields = [entry["public_signal"] for entry in entries]
    digest = str(sum(int(field) for field in fields) % BN128_FIELD_MODULUS)
    # snarkjs orders public outputs before public inputs.
    return [digest, *fields]


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


def baseline_receipt() -> dict[str, Any]:
    metadata = require_object(load_json(artifact_path("metadata")), "metadata", layer="artifact_binding")
    proof = require_object(load_json(artifact_path("proof")), "proof", layer="artifact_binding")
    public_signals = require_list(load_json(artifact_path("public_signals")), "public signals", layer="artifact_binding")
    verification_key = require_object(load_json(artifact_path("verification_key")), "verification key", layer="artifact_binding")
    input_json = require_object(load_json(artifact_path("input")), "input", layer="artifact_binding")
    contract = source_contract()
    entries = contract_field_entries(contract)
    statement = {
        "schema": STATEMENT_SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
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
        "setup_commitment": metadata.get("artifacts", {}).get("verification_key.json"),
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "statement": statement,
        "statement_commitment": statement_commitment(statement),
        "artifacts": copy.deepcopy(ARTIFACTS),
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


def snarkjs_verify(proof: dict[str, Any], public_signals: list[Any], verification_key: dict[str, Any]) -> None:
    cache_key = sha256_bytes(canonical_json_bytes([proof, public_signals, verification_key]))
    _snarkjs_verify_cached(cache_key, canonical_json_bytes(proof), canonical_json_bytes(public_signals), canonical_json_bytes(verification_key))


@functools.lru_cache(maxsize=64)
def _snarkjs_verify_cached(cache_key: str, proof_bytes: bytes, public_bytes: bytes, vk_bytes: bytes) -> None:  # noqa: ARG001
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
                [*SNARKJS_COMMAND, "groth16", "verify", str(vk_path), str(public_path), str(proof_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=60,
            )
        except subprocess.TimeoutExpired as err:
            raise D128SnarkReceiptError("snarkjs groth16 verifier timed out", layer="external_proof_verifier") from err
        except OSError as err:
            command = " ".join([*SNARKJS_COMMAND, "groth16", "verify"])
            raise D128SnarkReceiptError(
                f"failed to launch snarkjs verifier command `{command}`; ensure node/npx is installed and executable: {err}",
                layer="external_proof_verifier",
            ) from err
    output = ANSI_ESCAPE_RE.sub("", "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part))
    if result.returncode != 0:
        raise D128SnarkReceiptError(f"snarkjs groth16 verifier rejected: {output}", layer="external_proof_verifier")
    if "OK" not in output:
        raise D128SnarkReceiptError(f"snarkjs groth16 verifier did not report OK: {output}", layer="external_proof_verifier")


def _snarkjs_payloads(receipt: dict[str, Any]) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    proof = require_object(receipt.get("snarkjs_proof"), "snarkjs_proof")
    public_signals = require_list(receipt.get("public_signals"), "public_signals")
    verification_key = require_object(receipt.get("verification_key"), "verification_key")
    return proof, public_signals, verification_key


def verify_proof_only(receipt: dict[str, Any], *, external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify) -> None:
    proof, public_signals, verification_key = _snarkjs_payloads(receipt)
    external_verify(proof, public_signals, verification_key)


def verify_statement_receipt(receipt: dict[str, Any], *, external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify) -> None:
    expect_keys(
        receipt,
        {
            "artifacts",
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
    proof, public_signals, verification_key = _snarkjs_payloads(receipt)
    statement = require_object(receipt.get("statement"), "statement")
    if receipt.get("statement_commitment") != statement_commitment(statement):
        raise D128SnarkReceiptError("statement_commitment mismatch", layer="statement_commitment")
    if receipt.get("receipt_commitment") != receipt_commitment(receipt):
        raise D128SnarkReceiptError("receipt_commitment mismatch", layer="receipt_commitment")
    expected_statement = baseline_receipt()["statement"]
    for key in (
        "schema",
        "issue",
        "source_issue",
        "source_contract",
        "proof_system",
        "proof_system_version",
        "verifier_domain",
        "public_signal_field_domain",
        "public_signal_field_entries",
        "expected_public_signals_sha256",
    ):
        expect_equal(statement.get(key), expected_statement[key], key, layer="statement_policy" if key != "verifier_domain" else "domain_or_version_allowlist")
    metadata = require_object(load_json(artifact_path("metadata")), "metadata", layer="artifact_binding")
    artifact_hashes = require_object(metadata.get("artifacts"), "metadata artifacts", layer="artifact_binding")
    artifact_checks = {
        "circuit_artifact_sha256": ("circuit", "d128_statement_receipt.circom"),
        "input_artifact_sha256": ("input", "input.json"),
        "verification_key_file_sha256": ("verification_key", "verification_key.json"),
    }
    for statement_key, (artifact_key, metadata_name) in artifact_checks.items():
        actual = sha256_file(artifact_path(artifact_key))
        expect_equal(actual, statement.get(statement_key), statement_key, layer="artifact_binding")
        expect_equal(actual, artifact_hashes.get(metadata_name), f"metadata {metadata_name}", layer="artifact_binding")
    expect_equal(verification_key_sha256(verification_key), statement.get("verification_key_sha256"), "verification key canonical hash", layer="artifact_binding")
    expect_equal(proof_sha256(proof), statement.get("proof_sha256"), "proof hash", layer="artifact_binding")
    expect_equal(public_signals_sha256(public_signals), statement.get("public_signals_sha256"), "public signals hash", layer="public_signal_binding")
    expect_equal(public_signals, expected_public_signals(statement["public_signal_field_entries"]), "public signals", layer="public_signal_binding")
    expect_equal(public_signals_sha256(public_signals), statement.get("expected_public_signals_sha256"), "expected public signals digest", layer="public_signal_binding")
    expect_equal(statement.get("setup_commitment"), artifact_hashes.get("verification_key.json"), "setup commitment", layer="setup_binding")
    external_verify(proof, public_signals, verification_key)


def mutated_receipts() -> dict[str, tuple[str, dict[str, Any]]]:
    baseline = baseline_receipt()

    def mutate(name: str, surface: str, fn: Callable[[dict[str, Any]], None], *, refresh: bool = True) -> None:
        receipt = copy.deepcopy(baseline)
        fn(receipt)
        if refresh:
            _refresh_statement_commitment(receipt)
        out[name] = (surface, receipt)

    out: dict[str, tuple[str, dict[str, Any]]] = {}
    mutate("target_commitment_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"].__setitem__("two_slice_target_commitment", "blake2b-256:" + "00" * 32))
    mutate("selected_statement_commitment_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"]["selected_slice_statement_commitments"][0].__setitem__("statement_commitment", "blake2b-256:" + "11" * 32))
    mutate("selected_source_file_hash_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"]["selected_source_evidence_hashes"][0].__setitem__("source_file_sha256", "22" * 32))
    mutate("selected_source_payload_hash_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"]["selected_source_evidence_hashes"][0].__setitem__("source_payload_sha256", "33" * 32))
    mutate("selected_public_instance_commitment_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"]["selected_slice_public_instance_commitments"][0].__setitem__("public_instance_commitment", "blake2b-256:" + "44" * 32))
    mutate("selected_parameter_commitment_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"]["selected_slice_proof_native_parameter_commitments"][0].__setitem__("proof_native_parameter_commitment", "blake2b-256:" + "55" * 32))
    mutate("verifier_domain_relabeling", "domain_or_version_allowlist", lambda r: r["statement"].__setitem__("verifier_domain", "snarkjs-groth16-verify-v999:d128"))
    mutate("required_backend_version_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"].__setitem__("required_backend_version", "different-backend-v999"))
    mutate("source_accumulator_commitment_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"].__setitem__("source_accumulator_commitment", "blake2b-256:" + "66" * 32))
    mutate("source_verifier_handle_commitment_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"]["public_input_contract"].__setitem__("source_verifier_handle_commitment", "blake2b-256:" + "77" * 32))
    mutate("compressed_artifact_commitment_relabeling", "statement_policy", lambda r: r["statement"]["source_contract"].__setitem__("compressed_artifact_commitment", "blake2b-256:" + "88" * 32))
    mutate("public_signal_relabeling", "public_signal_binding", lambda r: r["public_signals"].__setitem__(0, "12345"))
    mutate("public_signal_hash_relabeling", "public_signal_binding", lambda r: r["statement"].__setitem__("public_signals_sha256", "99" * 32))
    mutate("field_entry_value_relabeling", "public_signal_binding", lambda r: r["statement"]["public_signal_field_entries"][0].__setitem__("value", "blake2b-256:" + "aa" * 32))
    mutate("field_entry_label_relabeling", "public_signal_binding", lambda r: r["statement"]["public_signal_field_entries"][0].__setitem__("label", "wrong-label"))
    mutate("proof_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("proof_sha256", "bb" * 32))
    mutate("verification_key_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("verification_key_sha256", "cc" * 32))
    mutate("verification_key_file_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("verification_key_file_sha256", "dd" * 32))
    mutate("circuit_artifact_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("circuit_artifact_sha256", "ee" * 32))
    mutate("input_artifact_hash_relabeling", "artifact_binding", lambda r: r["statement"].__setitem__("input_artifact_sha256", "ff" * 32))
    mutate("setup_commitment_relabeling", "setup_binding", lambda r: r["statement"].__setitem__("setup_commitment", "00" * 32))
    mutate("proof_size_metric_smuggled", "receipt_metrics", lambda r: r.setdefault("receipt_metrics", {}).__setitem__("proof_size_bytes", 1))
    mutate("verifier_time_metric_smuggled", "receipt_metrics", lambda r: r.setdefault("receipt_metrics", {}).__setitem__("verifier_time_ms", 0.001))
    mutate("proof_generation_time_metric_smuggled", "receipt_metrics", lambda r: r.setdefault("receipt_metrics", {}).__setitem__("proof_generation_time_ms", 0.001))
    mutate(
        "statement_commitment_relabeling",
        "statement_commitment",
        lambda r: r.__setitem__("statement_commitment", "blake2b-256:" + "12" * 32),
        refresh=False,
    )
    mutate(
        "receipt_commitment_relabeling",
        "receipt_commitment",
        lambda r: r.__setitem__("receipt_commitment", "blake2b-256:" + "34" * 32),
        refresh=False,
    )
    mutate("non_claims_removed", "parser_or_schema", lambda r: r.__setitem__("non_claims", r["non_claims"][:-1]))
    mutate("validation_command_drift", "parser_or_schema", lambda r: r.__setitem__("validation_commands", ["echo fake"]))
    mutate("unknown_top_level_field_added", "parser_or_schema", lambda r: r.__setitem__("unexpected", True))
    return out


def classify_error(err: D128SnarkReceiptError | Exception) -> str:
    if isinstance(err, D128SnarkReceiptError):
        return err.layer
    return "parser_or_schema"


def _case_result(receipt: dict[str, Any], external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None]) -> tuple[bool, str, str]:
    try:
        verify_statement_receipt(receipt, external_verify=external_verify)
    except D128SnarkReceiptError as err:
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
    except D128SnarkReceiptError as err:
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


def run_gate(external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify) -> dict[str, Any]:
    baseline = baseline_receipt()
    verify_proof_only(baseline, external_verify=external_verify)
    verify_statement_receipt(baseline, external_verify=external_verify)
    proof_verifier_check = proof_verifier_public_signal_check(baseline, external_verify)
    mutations = mutated_receipts()
    if set(mutations) != EXPECTED_MUTATION_SET:
        raise RuntimeError("mutation corpus does not match expected d128 SNARK receipt suite")
    cases = []
    for mutation, (surface, receipt) in sorted(mutations.items()):
        accepted, error, layer = _case_result(receipt, external_verify)
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
    source = source_contract()
    receipt = baseline_receipt()
    proof_size = artifact_path("proof").stat().st_size
    public_size = artifact_path("public_signals").stat().st_size
    vk_size = artifact_path("verification_key").stat().st_size
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": "SNARK_STATEMENT_RECEIPT_BINDS_D128_TWO_SLICE_PUBLIC_INPUT_CONTRACT_NOT_RECURSION",
        "source_contract": source,
        "statement_receipt": {
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
        },
        "proof_verifier_checks": {
            "public_signal_relabeling": proof_verifier_check,
        },
        "receipt_metrics": {
            "proof_size_bytes": proof_size,
            "public_signals_bytes": public_size,
            "verification_key_bytes": vk_size,
            "public_signal_count": len(receipt["public_signals"]),
            "verifier_time_ms": None,
            "proof_generation_time_ms": None,
            "timing_policy": "not_measured_in_this_gate",
        },
        "external_system": {
            "name": "snarkjs",
            "version": SNARKJS_VERSION,
            "proof_system": PROOF_SYSTEM,
            "verification_api": "snarkjs groth16 verify verification_key.json public.json proof.json",
        },
        "artifact_metadata": load_json(artifact_path("metadata")),
        "artifact_paths": {key: str(artifact_path(key).relative_to(ROOT)) for key in ARTIFACTS},
        "mutation_inventory": [{"mutation": name, "surface": surface} for name, surface in EXPECTED_MUTATION_INVENTORY],
        "case_count": len(cases),
        "all_mutations_rejected": all_rejected,
        "cases": cases,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "repro": {
            "git_commit": _git_commit(),
            "command": VALIDATION_COMMANDS[0],
        },
        "summary": (
            "A real snarkjs/Groth16 verifier-facing receipt accepts the d128 #424 two-slice public-input contract. "
            "Its public signals bind the contract-derived field elements, and the statement envelope rejects all tested relabeling. "
            "This is a SNARK statement receipt, not recursive verification of the underlying Stwo proofs."
        ),
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    expected_keys = {
        "schema", "issue", "source_issue", "decision", "result", "claim_boundary", "source_contract",
        "statement_receipt", "proof_verifier_checks", "receipt_metrics", "external_system", "artifact_metadata", "artifact_paths",
        "mutation_inventory", "case_count", "all_mutations_rejected", "cases", "non_claims",
        "validation_commands", "repro", "summary",
    }
    expect_keys(payload, expected_keys, "payload")
    expect_equal(payload["schema"], SCHEMA, "schema")
    expect_equal(payload["issue"], ISSUE, "issue")
    expect_equal(payload["source_issue"], SOURCE_ISSUE, "source issue")
    expect_equal(payload["decision"], DECISION, "decision")
    expect_equal(payload["result"], RESULT, "result")
    expect_equal(payload["source_contract"], source_contract(), "source contract", layer="source_contract")
    expect_equal(payload["non_claims"], NON_CLAIMS, "non claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation commands")
    require_object(payload["repro"], "repro")
    inventory = require_list(payload["mutation_inventory"], "mutation inventory")
    expect_equal(tuple((item.get("mutation"), item.get("surface")) for item in inventory), EXPECTED_MUTATION_INVENTORY, "mutation inventory")
    cases = require_list(payload["cases"], "cases")
    expect_equal(len(cases), len(EXPECTED_MUTATION_INVENTORY), "case count")
    expect_equal(payload["case_count"], len(cases), "case_count")
    if not payload["all_mutations_rejected"] or not all(case.get("rejected") is True for case in cases):
        raise D128SnarkReceiptError("not all SNARK receipt mutations rejected", layer="mutation_suite")
    by_name = {case.get("mutation"): case for case in cases}
    expect_equal(set(by_name), EXPECTED_MUTATION_SET, "case mutation set")
    for mutation, surface in EXPECTED_MUTATION_INVENTORY:
        case = by_name[mutation]
        expect_equal(case.get("surface"), surface, f"surface for {mutation}")
        if case.get("mutated_accepted") is True:
            raise D128SnarkReceiptError(f"mutation accepted: {mutation}", layer="mutation_suite")
    metrics = require_object(payload["receipt_metrics"], "receipt metrics")
    if metrics.get("proof_size_bytes") != artifact_path("proof").stat().st_size:
        raise D128SnarkReceiptError("proof size metric mismatch", layer="receipt_metrics")
    if metrics.get("verifier_time_ms") is not None or metrics.get("proof_generation_time_ms") is not None:
        raise D128SnarkReceiptError("timing metrics must remain null in this gate", layer="receipt_metrics")
    proof_checks = require_object(payload["proof_verifier_checks"], "proof verifier checks")
    public_signal_check = require_object(proof_checks.get("public_signal_relabeling"), "public signal proof verifier check")
    if public_signal_check.get("rejected") is not True or public_signal_check.get("rejection_layer") != "external_proof_verifier":
        raise D128SnarkReceiptError("raw proof verifier did not reject public signal relabeling", layer="external_proof_verifier")


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for case in payload["cases"]:
        row = {key: case[key] for key in TSV_COLUMNS}
        if row["error"] == "":
            row["error"] = "none"
        writer.writerow(row)
    return output.getvalue()


def write_text_checked(path: pathlib.Path, text: str) -> None:
    resolved = path.resolve()
    root = EVIDENCE_DIR.resolve()
    if root not in resolved.parents and resolved != root:
        raise D128SnarkReceiptError(f"output path must stay under {EVIDENCE_DIR}", layer="output_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


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
    args = parser.parse_args(argv)
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
    if not (args.json or args.tsv or args.write_json or args.write_tsv):
        print(f"PASS: d128 SNARK statement receipt accepted; rejected {payload['case_count']}/{payload['case_count']} mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
