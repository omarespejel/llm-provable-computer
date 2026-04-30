#!/usr/bin/env python3
"""Stwo-native relabeling benchmark for a statement-bound transformer block.

This benchmark deliberately separates raw Stwo proof validity from statement
validity for a bounded transformer-shaped block. The raw verifier checks a transparent proof object. The statement
receipt additionally binds that proof to model/input/output/config/setup/domain
claims that a zkAI integration would display or settle.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import copy
import csv
import gzip
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
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from zkai_stwo_transformer_block_constants import (  # noqa: E402
    REQUIRED_TRANSFORMER_BLOCK_OPERATION_IDS,
    TRANSFORMER_BLOCK_MODEL_ID,
    TRANSFORMER_BLOCK_PROFILE_VERSION,
)

ARTIFACT_DIR = ROOT / "docs" / "engineering" / "evidence" / "zkai-stwo-statement-bound-transformer-block-2026-05"
BENCHMARK_SCHEMA = "zkai-stwo-statement-envelope-benchmark-v1"
ENVELOPE_SCHEMA = "zkai-stwo-statement-envelope-v1"
STATEMENT_SCHEMA = "zkai-statement-receipt-v1"
# The delegated proof object is still the checked Stwo linear-block-with-lookup
# execution proof. The stronger block claim below comes from additionally
# verifying and binding a static transformer-block profile over that program.
STWO_PROOF_SYSTEM_VERSION = "stwo-phase10-linear-block-v4-with-lookup"
STWO_VERIFIER_DOMAIN = f"ptvm-stwo-verify-stark-reexecute-{STWO_PROOF_SYSTEM_VERSION}"
STWO_PROOF_SYSTEM = "stwo-transparent-stark"
STWO_STATEMENT_KIND = "transformer-block"
STWO_MODEL_ID = TRANSFORMER_BLOCK_MODEL_ID
STWO_PROGRAM_PATH = "programs/linear_block_v4_with_lookup.tvm"
STWO_PROOF_PATH = "linear_block_v4_with_lookup.proof.json.gz"
BLOCK_PROFILE_VERSION = TRANSFORMER_BLOCK_PROFILE_VERSION
BLOCK_LOGICAL_WIDTH = 4
BLOCK_INTEGER_DOMAIN = "signed fixed-width quantized M31-compatible integers"
REQUIRED_BLOCK_OPERATION_IDS = REQUIRED_TRANSFORMER_BLOCK_OPERATION_IDS

EXPECTED_STATEMENT = {
    "receipt_version": STATEMENT_SCHEMA,
    "verifier_domain": STWO_VERIFIER_DOMAIN,
    "proof_system": STWO_PROOF_SYSTEM,
    "proof_system_version": STWO_PROOF_SYSTEM_VERSION,
    "statement_kind": STWO_STATEMENT_KIND,
    "model_id": STWO_MODEL_ID,
}

TSV_COLUMNS = [
    "adapter",
    "mutation",
    "category",
    "baseline_accepted",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
]
EXPECTED_ADAPTERS = ("stwo-proof-only", "stwo-statement-envelope")
EXPECTED_MUTATION_NAMES = (
    "config_commitment_relabeling",
    "evidence_manifest_commitment_relabeling",
    "input_commitment_relabeling",
    "model_artifact_commitment_relabeling",
    "model_id_relabeling",
    "output_commitment_relabeling",
    "proof_commitment_relabeling",
    "proof_public_claim_relabeling",
    "proof_system_version_relabeling",
    "public_instance_commitment_relabeling",
    "setup_commitment_relabeling",
    "statement_commitment_relabeling",
    "verifier_domain_relabeling",
    "verifying_key_commitment_relabeling",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)
EXPECTED_MUTATION_SET = frozenset(EXPECTED_MUTATION_NAMES)
EXPECTED_CASE_PAIRS = frozenset(
    (adapter, mutation) for adapter in EXPECTED_ADAPTERS for mutation in EXPECTED_MUTATION_NAMES
)


class StwoEnvelopeError(ValueError):
    pass


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


def _program_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        raise StwoEnvelopeError(f"failed to read program artifact {path}: {err}") from err


def _instruction_op_ids(proof: dict[str, Any]) -> list[str]:
    program = _required_dict(stwo_claim(proof).get("program"), "claim.program")
    instructions = program.get("instructions")
    if not isinstance(instructions, list):
        raise StwoEnvelopeError("claim.program.instructions must be a list")
    op_ids: list[str] = []
    for index, instruction in enumerate(instructions):
        if isinstance(instruction, str):
            op_ids.append(instruction)
            continue
        if not isinstance(instruction, dict) or len(instruction) != 1:
            raise StwoEnvelopeError(f"claim.program.instructions[{index}] must be a singleton object")
        op_ids.append(next(iter(instruction)))
    return op_ids


def _contains_subsequence(haystack: list[str], needle: list[str]) -> bool:
    if not needle:
        return True
    limit = len(haystack) - len(needle) + 1
    return any(haystack[index : index + len(needle)] == needle for index in range(max(limit, 0)))


def block_profile(proof: dict[str, Any], program_path: pathlib.Path, metadata: dict[str, Any]) -> dict[str, Any]:
    """Return the checked static block profile bound into config_commitment.

    This is deliberately a structural profile over the small checked program,
    not a claim that the repo can prove arbitrary d=64/d=128 transformer MLPs.
    """

    final_state = _required_dict(stwo_claim(proof).get("final_state"), "claim.final_state")
    memory = final_state.get("memory")
    if not isinstance(memory, list) or len(memory) < 21:
        raise StwoEnvelopeError("claim.final_state.memory must expose the checked block witness cells")
    op_ids = _instruction_op_ids(proof)
    profile = {
        "profile_version": BLOCK_PROFILE_VERSION,
        "statement_kind": STWO_STATEMENT_KIND,
        "logical_width": BLOCK_LOGICAL_WIDTH,
        "integer_domain": BLOCK_INTEGER_DOMAIN,
        "operation_ids": list(REQUIRED_BLOCK_OPERATION_IDS),
        "operation_graph": [
            {
                "id": "quantized_affine_projection",
                "witness_cells": {"local_score": 10, "global_score": 11},
                "required_subsequences": [
                    ["Load", "MulMemory", "Store", "Load", "MulMemory", "AddMemory", "Store"],
                ],
            },
            {
                "id": "gated_value_mix",
                "witness_cells": {"mixed_value": 12},
                "required_subsequences": [
                    ["Load", "MulMemory", "Store", "Load", "MulMemory", "AddMemory", "Store"],
                ],
            },
            {
                "id": "residual_add",
                "witness_cells": {"residual_bias": 7, "block_output": 8},
                "required_subsequences": [["Load", "AddMemory", "Store"]],
            },
            {
                "id": "rmsnorm_scale_lookup",
                "witness_cells": {"primary_norm_sq": 13, "primary_inv_sqrt_q8": 14},
                "expected_rows": [[16, 64], [4, 128]],
            },
            {
                "id": "bounded_activation_lookup",
                "witness_cells": {"primary_input": 15, "primary_output": 16},
                "expected_rows": [[1, 1], [0, 1]],
            },
        ],
        "witness": {
            "local_score": memory[10],
            "global_score": memory[11],
            "mixed_value": memory[12],
            "block_output": memory[8],
            "primary_norm_sq": memory[13],
            "primary_inv_sqrt_q8": memory[14],
            "primary_activation_input": memory[15],
            "primary_activation_output": memory[16],
            "secondary_norm_sq": memory[17],
            "secondary_inv_sqrt_q8": memory[18],
            "secondary_activation_input": memory[19],
            "secondary_activation_output": memory[20],
        },
        "program_sha256": sha256_file(program_path),
        "program_comment_markers": [
            "grouped-query style weighted value mix",
            "residual projection",
            "primary normalization row",
            "primary activation row",
            "secondary canonical normalization row",
            "secondary canonical activation row",
        ],
        "metadata_profile": metadata.get("transformer_block_profile"),
    }
    return profile


def verify_block_profile(proof: dict[str, Any], program_path: pathlib.Path, metadata: dict[str, Any]) -> dict[str, Any]:
    profile = block_profile(proof, program_path, metadata)
    program_text = _program_text(program_path)
    for marker in profile["program_comment_markers"]:
        if marker not in program_text:
            raise StwoEnvelopeError(f"program artifact is missing block marker: {marker}")
    metadata_profile = profile.get("metadata_profile")
    if not isinstance(metadata_profile, dict):
        raise StwoEnvelopeError("metadata.transformer_block_profile must be an object")
    if metadata_profile.get("profile_version") != BLOCK_PROFILE_VERSION:
        raise StwoEnvelopeError("metadata transformer block profile version mismatch")
    if metadata_profile.get("logical_width") != BLOCK_LOGICAL_WIDTH:
        raise StwoEnvelopeError("metadata transformer block logical width mismatch")
    if tuple(metadata_profile.get("operation_ids", [])) != REQUIRED_BLOCK_OPERATION_IDS:
        raise StwoEnvelopeError("metadata transformer block operation IDs mismatch")

    op_ids = _instruction_op_ids(proof)
    required_patterns = [
        ["Load", "MulMemory", "Store", "Load", "MulMemory", "AddMemory", "Store"],
        ["Load", "AddMemory", "Store"],
        ["Load", "MulMemory", "Store", "LoadImmediate", "Store"],
    ]
    for pattern in required_patterns:
        if not _contains_subsequence(op_ids, pattern):
            raise StwoEnvelopeError(f"proof public program is missing required block operation pattern: {pattern}")

    witness = profile["witness"]
    expected = {
        "local_score": 2,
        "global_score": 2,
        "mixed_value": 8,
        "block_output": 4,
        "primary_norm_sq": 16,
        "primary_inv_sqrt_q8": 64,
        "primary_activation_input": 1,
        "primary_activation_output": 1,
        "secondary_norm_sq": 4,
        "secondary_inv_sqrt_q8": 128,
        "secondary_activation_input": 0,
        "secondary_activation_output": 1,
    }
    for field, value in expected.items():
        if witness.get(field) != value:
            raise StwoEnvelopeError(f"block witness field {field} mismatch")
    return profile


def block_profile_commitment(proof: dict[str, Any], program_path: pathlib.Path, metadata: dict[str, Any]) -> str:
    return blake2b_commitment(
        verify_block_profile(proof, program_path, metadata),
        "ptvm:zkai:stwo-transformer-block-profile:v1",
    )


def _load_json(path: pathlib.Path) -> Any:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                return json.load(handle)
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, gzip.BadGzipFile) as err:
        raise StwoEnvelopeError(f"failed to load JSON artifact {path}: {err}") from err


def _required_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StwoEnvelopeError(f"{label} must be an object")
    return value


def _required_artifact_reference(artifacts: dict[str, Any], key: str) -> str:
    value = artifacts.get(key)
    if not isinstance(value, str) or not value:
        raise StwoEnvelopeError(f"artifacts.{key} must be a non-empty string")
    return value


def _repo_path(relative_path: str) -> pathlib.Path:
    path = (ROOT / relative_path).resolve()
    root = ROOT.resolve()
    if root not in path.parents and path != root:
        raise StwoEnvelopeError(f"artifact path escapes repository: {relative_path}")
    if not path.is_file():
        raise StwoEnvelopeError(f"artifact path is missing: {relative_path}")
    return path


def _artifact_dir_path(relative_path: str) -> pathlib.Path:
    path = (ARTIFACT_DIR / relative_path).resolve()
    artifact_root = ARTIFACT_DIR.resolve()
    if artifact_root not in path.parents and path != artifact_root:
        raise StwoEnvelopeError(f"artifact path escapes evidence directory: {relative_path}")
    if not path.is_file():
        raise StwoEnvelopeError(f"artifact path is missing: {relative_path}")
    return path


def stwo_proof_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    return _required_dict(envelope.get("stwo_proof"), "stwo_proof")


def stwo_claim(proof: dict[str, Any]) -> dict[str, Any]:
    return _required_dict(proof.get("claim"), "claim")


def proof_sha256(proof: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(proof))


def public_instance_commitment(proof: dict[str, Any]) -> str:
    return blake2b_commitment(stwo_claim(proof), "ptvm:zkai:stwo-public-instance:v1")


def model_artifact_commitment(proof: dict[str, Any], program_path: pathlib.Path) -> str:
    claim = stwo_claim(proof)
    commitments = _required_dict(claim.get("commitments"), "claim.commitments")
    payload = {
        "program_file_sha256": sha256_file(program_path),
        "program_hash": commitments.get("program_hash"),
        "deterministic_model_hash": commitments.get("deterministic_model_hash"),
        "hash_function": commitments.get("hash_function"),
        "scheme_version": commitments.get("scheme_version"),
    }
    return blake2b_commitment(payload, "ptvm:zkai:stwo-model-artifact:v1")


def input_commitment(proof: dict[str, Any]) -> str:
    program = _required_dict(stwo_claim(proof).get("program"), "claim.program")
    return blake2b_commitment(
        {"initial_memory": program.get("initial_memory")}, "ptvm:zkai:stwo-input:v1"
    )


def output_commitment(proof: dict[str, Any]) -> str:
    return blake2b_commitment(
        stwo_claim(proof).get("final_state"), "ptvm:zkai:stwo-output:v1"
    )


def config_commitment(
    proof: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    program_path: pathlib.Path | None = None,
) -> str:
    claim = stwo_claim(proof)
    if metadata is None:
        metadata = _required_dict(_load_json(ARTIFACT_DIR / "metadata.json"), "metadata")
    if program_path is None:
        program_path = _repo_path(STWO_PROGRAM_PATH)
    payload = {
        "attention_mode": claim.get("attention_mode"),
        "transformer_config": claim.get("transformer_config"),
        "options": claim.get("options"),
        "equivalence": claim.get("equivalence"),
        "steps": claim.get("steps"),
        "statement_bound_transformer_block_profile_commitment": block_profile_commitment(
            proof,
            program_path,
            metadata,
        ),
    }
    return blake2b_commitment(payload, "ptvm:zkai:stwo-config:v1")


def verifying_key_commitment(proof: dict[str, Any]) -> str:
    claim = stwo_claim(proof)
    payload = {
        "proof_backend": proof.get("proof_backend"),
        "proof_backend_version": proof.get("proof_backend_version"),
        "statement_version": claim.get("statement_version"),
        "semantic_scope": claim.get("semantic_scope"),
        "commitment_hash_function": _required_dict(claim.get("commitments"), "claim.commitments").get(
            "hash_function"
        ),
    }
    return blake2b_commitment(payload, "ptvm:zkai:stwo-verifier-identity:v1")


def setup_commitment(proof: dict[str, Any]) -> str:
    claim = stwo_claim(proof)
    payload = {
        "transparent_setup": True,
        "fri_or_stark_options": claim.get("options"),
        "proof_backend_version": proof.get("proof_backend_version"),
    }
    return blake2b_commitment(payload, "ptvm:zkai:stwo-transparent-setup:v1")


def evidence_manifest_commitment(proof: dict[str, Any], metadata: dict[str, Any]) -> str:
    payload = {
        "schema": metadata.get("schema"),
        "program_path": metadata.get("program_path"),
        "proof_path": metadata.get("proof_path"),
        "artifacts": metadata.get("artifacts"),
        "generation_command": metadata.get("generation_command"),
        "verification_command": metadata.get("verification_command"),
        "proof_sha256": proof_sha256(proof),
        "public_instance_commitment": public_instance_commitment(proof),
    }
    return blake2b_commitment(payload, "ptvm:zkai:stwo-evidence-manifest:v1")


def statement_commitment(statement: dict[str, Any]) -> str:
    return blake2b_commitment(statement, "ptvm:zkai:stwo-statement:v1")


def statement_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    statement = envelope.get("statement", {})
    return copy.deepcopy(statement) if isinstance(statement, dict) else {}


def statement_payload_sha256(envelope: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(statement_payload(envelope)))


def baseline_envelope() -> dict[str, Any]:
    metadata = _load_json(ARTIFACT_DIR / "metadata.json")
    proof = _load_json(ARTIFACT_DIR / STWO_PROOF_PATH)
    program_path = _repo_path(STWO_PROGRAM_PATH)
    statement = {
        **EXPECTED_STATEMENT,
        "model_artifact_commitment": model_artifact_commitment(proof, program_path),
        "input_commitment": input_commitment(proof),
        "output_commitment": output_commitment(proof),
        "config_commitment": config_commitment(proof, metadata, program_path),
        "public_instance_commitment": public_instance_commitment(proof),
        "proof_commitment": proof_sha256(proof),
        "verifying_key_commitment": verifying_key_commitment(proof),
        "setup_commitment": setup_commitment(proof),
        "evidence_manifest_commitment": evidence_manifest_commitment(proof, metadata),
    }
    return {
        "schema": ENVELOPE_SCHEMA,
        "statement": statement,
        "statement_commitment": statement_commitment(statement),
        "artifacts": {
            "program_path": STWO_PROGRAM_PATH,
            "proof_path": STWO_PROOF_PATH,
            "metadata_path": "metadata.json",
        },
        "stwo_proof": proof,
        "non_claims": [
            "not_a_performance_benchmark",
            "not_full_transformer_inference",
            "not_backend_independence",
            "not_a_stwo_security_audit",
        ],
    }


def _refresh_statement_commitment(envelope: dict[str, Any]) -> None:
    envelope["statement_commitment"] = statement_commitment(envelope["statement"])


def _mutate_final_state_acc(proof: dict[str, Any]) -> None:
    claim = stwo_claim(proof)
    final_state = _required_dict(claim.get("final_state"), "claim.final_state")
    acc = final_state.get("acc")
    if not isinstance(acc, int):
        raise StwoEnvelopeError("baseline Stwo proof must contain integer final_state.acc")
    final_state["acc"] = acc + 1 if acc != 0 else 1


def mutated_envelopes() -> dict[str, tuple[str, dict[str, Any]]]:
    baseline = baseline_envelope()

    def mutate_statement(field: str, value: Any, category: str) -> tuple[str, dict[str, Any]]:
        env = copy.deepcopy(baseline)
        env["statement"][field] = value
        _refresh_statement_commitment(env)
        return category, env

    wrong_commitment = "blake2b-256:" + "00" * 32
    out: dict[str, tuple[str, dict[str, Any]]] = {
        "model_id_relabeling": mutate_statement(
            "model_id", "urn:zkai:ptvm:different-transformer-block-v1", "statement_policy"
        ),
        "model_artifact_commitment_relabeling": mutate_statement(
            "model_artifact_commitment", wrong_commitment, "artifact_binding"
        ),
        "input_commitment_relabeling": mutate_statement(
            "input_commitment", wrong_commitment, "artifact_binding"
        ),
        "output_commitment_relabeling": mutate_statement(
            "output_commitment", wrong_commitment, "artifact_binding"
        ),
        "config_commitment_relabeling": mutate_statement(
            "config_commitment", wrong_commitment, "artifact_binding"
        ),
        "public_instance_commitment_relabeling": mutate_statement(
            "public_instance_commitment", wrong_commitment, "public_instance_binding"
        ),
        "proof_commitment_relabeling": mutate_statement(
            "proof_commitment", "11" * 32, "artifact_binding"
        ),
        "verifying_key_commitment_relabeling": mutate_statement(
            "verifying_key_commitment", wrong_commitment, "domain_or_version_allowlist"
        ),
        "verifier_domain_relabeling": mutate_statement(
            "verifier_domain", "ptvm-stwo-verify-stark-reexecute-v999", "domain_or_version_allowlist"
        ),
        "proof_system_version_relabeling": mutate_statement(
            "proof_system_version", "stwo-phase999-invalid", "domain_or_version_allowlist"
        ),
        "setup_commitment_relabeling": mutate_statement(
            "setup_commitment", wrong_commitment, "setup_binding"
        ),
        "evidence_manifest_commitment_relabeling": mutate_statement(
            "evidence_manifest_commitment", wrong_commitment, "evidence_manifest"
        ),
    }

    commitment_env = copy.deepcopy(baseline)
    commitment_env["statement_commitment"] = "blake2b-256:" + "66" * 32
    out["statement_commitment_relabeling"] = ("statement_commitment", commitment_env)

    proof_env = copy.deepcopy(baseline)
    _mutate_final_state_acc(proof_env["stwo_proof"])
    metadata = _load_json(ARTIFACT_DIR / "metadata.json")
    program_path = _repo_path(STWO_PROGRAM_PATH)
    proof_env["statement"]["model_artifact_commitment"] = model_artifact_commitment(
        proof_env["stwo_proof"], program_path
    )
    proof_env["statement"]["input_commitment"] = input_commitment(proof_env["stwo_proof"])
    proof_env["statement"]["output_commitment"] = output_commitment(proof_env["stwo_proof"])
    proof_env["statement"]["config_commitment"] = config_commitment(
        proof_env["stwo_proof"],
        metadata,
        program_path,
    )
    proof_env["statement"]["public_instance_commitment"] = public_instance_commitment(
        proof_env["stwo_proof"]
    )
    proof_env["statement"]["proof_commitment"] = proof_sha256(proof_env["stwo_proof"])
    proof_env["statement"]["verifying_key_commitment"] = verifying_key_commitment(
        proof_env["stwo_proof"]
    )
    proof_env["statement"]["setup_commitment"] = setup_commitment(proof_env["stwo_proof"])
    proof_env["statement"]["evidence_manifest_commitment"] = evidence_manifest_commitment(
        proof_env["stwo_proof"], metadata
    )
    _refresh_statement_commitment(proof_env)
    out["proof_public_claim_relabeling"] = ("external_proof_verifier", proof_env)
    return out


def _check_statement_policy(statement: dict[str, Any]) -> None:
    for key, expected in EXPECTED_STATEMENT.items():
        if statement.get(key) != expected:
            raise StwoEnvelopeError(f"statement policy mismatch for {key}")


def _check_artifact_bindings(envelope: dict[str, Any], proof: dict[str, Any]) -> None:
    artifacts = _required_dict(envelope.get("artifacts"), "artifacts")
    program_path = _repo_path(_required_artifact_reference(artifacts, "program_path"))
    metadata_path = _artifact_dir_path(_required_artifact_reference(artifacts, "metadata_path"))
    proof_reference = _required_artifact_reference(artifacts, "proof_path")
    proof_path = _artifact_dir_path(proof_reference)
    metadata = _required_dict(_load_json(metadata_path), "metadata")
    statement = _required_dict(envelope.get("statement"), "statement")
    metadata_artifacts = _required_dict(metadata.get("artifacts"), "metadata.artifacts")
    expected_program_hash = metadata_artifacts.get(STWO_PROGRAM_PATH)
    if sha256_file(program_path) != expected_program_hash:
        raise StwoEnvelopeError("program artifact hash does not match metadata")
    expected_proof_hash = metadata_artifacts.get(proof_reference)
    if sha256_file(proof_path) != expected_proof_hash:
        raise StwoEnvelopeError("proof artifact hash does not match metadata")
    if _load_json(proof_path) != proof:
        raise StwoEnvelopeError("proof artifact does not match envelope proof")
    checks = [
        (model_artifact_commitment(proof, program_path), statement.get("model_artifact_commitment"), "model artifact commitment"),
        (input_commitment(proof), statement.get("input_commitment"), "input commitment"),
        (output_commitment(proof), statement.get("output_commitment"), "output commitment"),
        (
            config_commitment(proof, metadata, program_path),
            statement.get("config_commitment"),
            "config commitment",
        ),
        (
            public_instance_commitment(proof),
            statement.get("public_instance_commitment"),
            "public-instance commitment",
        ),
        (proof_sha256(proof), statement.get("proof_commitment"), "proof commitment"),
        (
            verifying_key_commitment(proof),
            statement.get("verifying_key_commitment"),
            "verifying-key commitment",
        ),
        (setup_commitment(proof), statement.get("setup_commitment"), "setup commitment"),
        (
            evidence_manifest_commitment(proof, metadata),
            statement.get("evidence_manifest_commitment"),
            "evidence manifest commitment",
        ),
    ]
    for actual, expected, label in checks:
        if actual != expected:
            raise StwoEnvelopeError(f"{label} mismatch")


def stwo_verify(proof: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        proof_path = tmp / "proof.json"
        proof_path.write_text(json.dumps(proof, sort_keys=True), encoding="utf-8")
        cmd = [
            "cargo",
            "+nightly-2025-07-14",
            "run",
            "--features",
            "stwo-backend",
            "--bin",
            "tvm",
            "--",
            "verify-stark",
            str(proof_path),
            "--reexecute",
        ]
        try:
            result = subprocess.run(
                cmd,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=90,
            )
        except subprocess.TimeoutExpired as err:
            raise StwoEnvelopeError("Stwo verify-stark verifier timed out") from err
        except OSError as err:
            raise StwoEnvelopeError(f"Stwo verify-stark verifier failed to execute cargo: {err}") from err
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if result.returncode != 0:
        raise StwoEnvelopeError(f"Stwo verify-stark verifier rejected: {output}")
    if "verified_stark: true" not in output:
        raise StwoEnvelopeError(f"Stwo verify-stark did not report verified_stark: true: {output}")


def verify_statement_envelope(
    envelope: dict[str, Any],
    *,
    external_verify: Callable[[dict[str, Any]], None] = stwo_verify,
) -> None:
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        raise StwoEnvelopeError("unsupported envelope schema")
    statement = _required_dict(envelope.get("statement"), "statement")
    proof = stwo_proof_payload(envelope)
    if proof.get("proof_backend_version") != statement.get("proof_system_version"):
        raise StwoEnvelopeError("proof backend version does not match statement policy")
    if envelope.get("statement_commitment") != statement_commitment(statement):
        raise StwoEnvelopeError("statement_commitment mismatch")
    _check_statement_policy(statement)
    _check_artifact_bindings(envelope, proof)
    external_verify(proof)


def verify_proof_only(
    envelope: dict[str, Any],
    external_verify: Callable[[dict[str, Any]], None] = stwo_verify,
) -> None:
    external_verify(stwo_proof_payload(envelope))


def classify_error(message: str) -> str:
    # Keep these phrase checks aligned with StwoEnvelopeError messages above.
    # Examples: "policy mismatch", "proof artifact", "setup commitment", and
    # "verify-stark verifier rejected" drive evidence rejection-layer labels.
    # If those errors change, update this classifier and its evidence tests.
    lowered = message.lower()
    if "verify-stark verifier rejected" in lowered or "timed out" in lowered:
        return "external_proof_verifier"
    if "public-instance" in lowered:
        return "public_instance_binding"
    if "setup" in lowered:
        return "setup_binding"
    if "evidence manifest" in lowered:
        return "evidence_manifest"
    if (
        "program artifact" in lowered
        or "proof artifact" in lowered
        or "proof commitment" in lowered
        or "model artifact" in lowered
    ):
        return "artifact_binding"
    if "input commitment" in lowered or "output commitment" in lowered or "config commitment" in lowered:
        return "artifact_binding"
    if "verifying-key" in lowered or "domain" in lowered or "version" in lowered:
        return "domain_or_version_allowlist"
    if "policy mismatch" in lowered:
        return "statement_policy"
    if "statement_commitment" in lowered or "commitment" in lowered:
        return "statement_commitment"
    if "must be" in lowered or "unsupported" in lowered:
        return "parser_or_schema"
    return "parser_or_schema"


def _case_result(
    adapter: str,
    envelope: dict[str, Any],
    external_verify: Callable[[dict[str, Any]], None],
) -> tuple[bool, str]:
    try:
        if adapter == "stwo-proof-only":
            verify_proof_only(envelope, external_verify=external_verify)
        elif adapter == "stwo-statement-envelope":
            verify_statement_envelope(envelope, external_verify=external_verify)
        else:
            raise StwoEnvelopeError(f"unsupported adapter {adapter!r}")
    except StwoEnvelopeError as err:
        return False, str(err)
    return True, ""


def run_benchmark(
    command: list[str] | None = None,
    external_verify: Callable[[dict[str, Any]], None] = stwo_verify,
) -> dict[str, Any]:
    baseline = baseline_envelope()
    mutations = mutated_envelopes()
    if set(mutations) != EXPECTED_MUTATION_SET:
        raise RuntimeError("mutation corpus does not match expected Stwo relabeling suite")
    cases = []
    for adapter in EXPECTED_ADAPTERS:
        baseline_accepted, baseline_error = _case_result(adapter, baseline, external_verify)
        for mutation, (category, envelope) in sorted(mutations.items()):
            accepted, error = _case_result(adapter, envelope, external_verify)
            cases.append(
                {
                    "adapter": adapter,
                    "mutation": mutation,
                    "category": category,
                    "baseline_statement": statement_payload(baseline),
                    "mutated_statement": statement_payload(envelope),
                    "baseline_statement_sha256": statement_payload_sha256(baseline),
                    "mutated_statement_sha256": statement_payload_sha256(envelope),
                    "baseline_statement_commitment": baseline.get("statement_commitment", ""),
                    "mutated_statement_commitment": envelope.get("statement_commitment", ""),
                    "baseline_public_instance_commitment": public_instance_commitment(baseline["stwo_proof"]),
                    "mutated_public_instance_commitment": public_instance_commitment(envelope["stwo_proof"]),
                    "baseline_accepted": baseline_accepted,
                    "baseline_error": baseline_error,
                    "mutated_accepted": accepted,
                    "rejected": not accepted,
                    "rejection_layer": classify_error(error) if not accepted else "accepted",
                    "error": error,
                }
            )
    summary = summarize_cases(cases)
    if summary is None:
        raise RuntimeError("benchmark case corpus does not match expected Stwo relabeling suite")
    metadata = _load_json(ARTIFACT_DIR / "metadata.json")
    return {
        "schema": BENCHMARK_SCHEMA,
        "suite_kind": "native_stwo_statement_relabeling",
        "external_system": {
            "name": "ptvm-stwo-backend",
            "version": STWO_PROOF_SYSTEM_VERSION,
            "verification_api": "cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- verify-stark <proof> --reexecute",
            "proof_system": STWO_PROOF_SYSTEM,
        },
        "non_claims": [
            "not_a_performance_benchmark",
            "not_full_transformer_inference",
            "not_backend_independence",
            "not_a_d64_or_d128_matched_benchmark",
            "not_full_swiglu_mlp",
            "delegated_proof_is_the_checked_width4_linear_block_with_lookup_execution_proof",
            "proof_only_no_go_is_limited_to_metadata_outside_the_stwo_proof_acceptance_path",
        ],
        "repro": {
            "git_commit": os.environ.get("ZKAI_STWO_BENCHMARK_GIT_COMMIT", _git_commit()),
            "command": _canonical_command(command),
            "artifact_dir": str(ARTIFACT_DIR.relative_to(ROOT)),
            "artifact_metadata_sha256": sha256_file(ARTIFACT_DIR / "metadata.json"),
        },
        "artifact_metadata": metadata,
        "block_profile": verify_block_profile(
            baseline["stwo_proof"],
            _repo_path(STWO_PROGRAM_PATH),
            metadata,
        ),
        "cases": cases,
        "summary": summary,
    }


def _git_commit() -> str:
    git = shutil.which("git")
    if git is None:
        return "unknown"
    try:
        return subprocess.check_output(
            [git, "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _canonical_command(command: list[str] | None) -> list[str]:
    override_json = os.environ.get("ZKAI_STWO_BENCHMARK_COMMAND_JSON")
    if override_json:
        try:
            parsed = json.loads(override_json)
        except json.JSONDecodeError as err:
            raise RuntimeError(
                "ZKAI_STWO_BENCHMARK_COMMAND_JSON must be a valid JSON array of strings"
            ) from err
        if not isinstance(parsed, list) or not all(isinstance(part, str) for part in parsed):
            raise RuntimeError("ZKAI_STWO_BENCHMARK_COMMAND_JSON must be a JSON array of strings")
        return parsed
    return command or []


def summarize_cases(cases: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(cases, list):
        return None
    pairs = []
    for case in cases:
        if not isinstance(case, dict):
            return None
        adapter = case.get("adapter")
        mutation = case.get("mutation")
        if adapter not in EXPECTED_ADAPTERS or mutation not in EXPECTED_MUTATION_SET:
            return None
        pairs.append((adapter, mutation))
    if len(pairs) != len(EXPECTED_CASE_PAIRS) or set(pairs) != EXPECTED_CASE_PAIRS:
        return None
    return {
        adapter: {
            "baseline_accepted": all(
                bool(case.get("baseline_accepted")) for case in cases if case["adapter"] == adapter
            ),
            "mutations_rejected": sum(
                1 for case in cases if case["adapter"] == adapter and bool(case.get("rejected"))
            ),
            "mutation_count": sum(1 for case in cases if case["adapter"] == adapter),
            "all_mutations_rejected": all(
                bool(case.get("rejected")) for case in cases if case["adapter"] == adapter
            ),
        }
        for adapter in EXPECTED_ADAPTERS
    }


def benchmark_passed(payload: dict[str, Any]) -> bool:
    summary = summarize_cases(payload.get("cases"))
    if summary is None:
        return False
    if payload.get("summary") != summary:
        return False
    proof_only = summary["stwo-proof-only"]
    statement_envelope = summary["stwo-statement-envelope"]
    proof_cases = {
        case["mutation"]: case for case in payload["cases"] if case["adapter"] == "stwo-proof-only"
    }
    return (
        proof_only["baseline_accepted"]
        and statement_envelope["baseline_accepted"]
        and proof_only["mutations_rejected"] == 1
        and bool(proof_cases["proof_public_claim_relabeling"].get("rejected"))
        and statement_envelope["all_mutations_rejected"]
    )


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for case in payload["cases"]:
        row = {column: case[column] for column in TSV_COLUMNS}
        if row["error"] == "":
            row["error"] = "none"
        writer.writerow(row)
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON result")
    parser.add_argument("--tsv", action="store_true", help="print TSV result")
    parser.add_argument("--write-json", type=pathlib.Path, help="write JSON result to this path")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write TSV result to this path")
    args = parser.parse_args(argv)

    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    script_path = str(pathlib.Path(__file__).resolve().relative_to(ROOT))
    payload = run_benchmark(
        command=[os.environ.get("PYTHON", "python3"), script_path, *effective_argv]
    )
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
    passed = benchmark_passed(payload)
    if not (args.json or args.tsv or args.write_json or args.write_tsv):
        summary = payload["summary"]
        print(
            f"{'PASS' if passed else 'FAIL'}: "
            f"proof-only rejected {summary['stwo-proof-only']['mutations_rejected']}/"
            f"{summary['stwo-proof-only']['mutation_count']} mutations; "
            f"statement-envelope rejected {summary['stwo-statement-envelope']['mutations_rejected']}/"
            f"{summary['stwo-statement-envelope']['mutation_count']} mutations"
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
