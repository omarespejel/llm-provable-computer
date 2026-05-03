#!/usr/bin/env python3
"""Build and verify the d128 full-block verifier-facing accumulator backend.

This is the issue #413 follow-up to the d128 block receipt composition gate and
PR #412's two-slice accumulator. It constructs one real verifier-facing
accumulator over the full six-slice d128 block receipt and verifies that the
accumulator binds:

* the block receipt commitment;
* the statement commitment;
* the slice-chain and source-evidence manifest commitments;
* every slice statement commitment; and
* every source evidence hash.

The accumulator is deliberately non-recursive. It revalidates the checked block
receipt and accumulates verifier-visible public inputs into one commitment, but
it is not a STARK-in-STARK proof, PCD object, compressed verifier object, or
on-chain proof artifact.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
from functools import lru_cache
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
BLOCK_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_d128_block_receipt_composition_gate.py"
BLOCK_RECEIPT_EVIDENCE = EVIDENCE_DIR / "zkai-d128-block-receipt-composition-gate-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-full-block-accumulator-backend-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-full-block-accumulator-backend-2026-05.tsv"

SCHEMA = "zkai-d128-full-block-accumulator-backend-v1"
DECISION = "GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR_BACKEND"
RESULT = "GO"
ISSUE = 413
ACCUMULATOR_RESULT = "GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR"
RECURSIVE_OR_PCD_RESULT = "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING"
ACCUMULATOR_SCHEMA = "zkai-d128-full-block-verifier-accumulator-v1"
VERIFIER_HANDLE_SCHEMA = "zkai-d128-full-block-accumulator-verifier-handle-v1"
ACCUMULATOR_KIND = "non-recursive-full-block-verifier-accumulator"
CLAIM_BOUNDARY = "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF"
WIDTH = 128
EXPECTED_SLICE_COUNT = 6
EXPECTED_CHECKED_ROWS = 197_504

ACCUMULATOR_DOMAIN = "ptvm:zkai:d128-full-block:verifier-accumulator:v1"
VERIFIER_HANDLE_DOMAIN = "ptvm:zkai:d128-full-block:accumulator-verifier-handle:v1"

REQUIRED_PUBLIC_INPUTS = [
    "block_receipt_commitment",
    "statement_commitment",
    "slice_chain_commitment",
    "evidence_manifest_commitment",
    "slice_statement_commitments",
    "source_evidence_hashes",
]

GO_CRITERION = (
    "one verifier-facing full-block accumulator object exists, a local verifier handle accepts it, "
    "and the accumulator binds block_receipt_commitment, statement_commitment, slice-chain and "
    "evidence-manifest commitments, every slice statement commitment, and every source evidence hash"
)

RECURSIVE_BLOCKER = (
    "no executable recursive/PCD outer proof backend currently proves the six d128 slice-verifier "
    "checks inside one cryptographic outer proof"
)

NON_CLAIMS = [
    "not recursive aggregation of the six slice proofs",
    "not proof-carrying-data accumulation",
    "not a STARK-in-STARK verifier proof",
    "not one compressed cryptographic verifier object",
    "not proof-size evidence for a recursive outer proof",
    "not verifier-time evidence for a recursive outer proof",
    "not proof-generation-time evidence for a recursive outer proof",
    "not matched NANOZK, DeepProve, EZKL, snarkjs, or JSTprove comparison evidence",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_full_block_accumulator_backend_gate.py --write-json docs/engineering/evidence/zkai-d128-full-block-accumulator-backend-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-full-block-accumulator-backend-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_full_block_accumulator_backend_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "mutation",
    "surface",
    "baseline_result",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
)

EXPECTED_MUTATION_INVENTORY = (
    ("source_block_receipt_file_hash_drift", "source_block_receipt"),
    ("source_block_receipt_payload_hash_drift", "source_block_receipt"),
    ("source_block_receipt_result_drift", "source_block_receipt"),
    ("source_block_receipt_commitment_drift", "source_block_receipt"),
    ("source_statement_commitment_drift", "source_block_receipt"),
    ("source_slice_chain_commitment_drift", "source_block_receipt"),
    ("source_evidence_manifest_commitment_drift", "source_block_receipt"),
    ("accumulator_commitment_drift", "accumulator_artifact"),
    ("accumulator_claim_boundary_changed_to_recursive", "accumulator_artifact"),
    ("accumulator_block_receipt_commitment_drift", "accumulator_artifact"),
    ("accumulator_statement_commitment_drift", "accumulator_artifact"),
    ("accumulator_slice_chain_commitment_drift", "accumulator_artifact"),
    ("accumulator_evidence_manifest_commitment_drift", "accumulator_artifact"),
    ("public_input_block_receipt_commitment_drift", "public_inputs"),
    ("public_input_statement_commitment_drift", "public_inputs"),
    ("public_input_slice_chain_commitment_drift", "public_inputs"),
    ("public_input_evidence_manifest_commitment_drift", "public_inputs"),
    ("public_input_slice_statement_drift", "public_inputs"),
    ("public_input_source_hash_drift", "public_inputs"),
    ("slice_removed", "slice_transcript"),
    ("slice_duplicated", "slice_transcript"),
    ("slice_reordered", "slice_transcript"),
    ("slice_row_count_drift", "slice_transcript"),
    ("slice_source_commitment_drift", "slice_transcript"),
    ("slice_target_commitment_drift", "slice_transcript"),
    ("source_manifest_file_hash_drift", "source_evidence_manifest"),
    ("source_manifest_payload_hash_drift", "source_evidence_manifest"),
    ("transcript_statement_commitment_drift", "source_evidence_manifest"),
    ("transcript_public_instance_commitment_drift", "source_evidence_manifest"),
    ("verifier_domain_drift", "verifier_transcript"),
    ("validator_name_drift", "verifier_transcript"),
    ("validator_result_false", "verifier_transcript"),
    ("verifier_handle_commitment_drift", "verifier_handle"),
    ("verifier_handle_claim_boundary_changed_to_recursive", "verifier_handle"),
    ("verifier_handle_block_receipt_commitment_drift", "verifier_handle"),
    ("verifier_handle_statement_commitment_drift", "verifier_handle"),
    ("verifier_handle_accumulator_commitment_drift", "verifier_handle"),
    ("verifier_handle_missing_required_public_input", "verifier_handle"),
    ("recursive_outer_proof_claimed", "recursive_or_pcd_status"),
    ("pcd_outer_proof_claimed", "recursive_or_pcd_status"),
    ("recursive_proof_metric_smuggled", "recursive_or_pcd_status"),
    ("recursive_blocker_removed", "recursive_or_pcd_status"),
    ("decision_changed_to_no_go", "parser_or_schema"),
    ("result_changed_to_no_go", "parser_or_schema"),
    ("accumulator_result_changed_to_no_go", "parser_or_schema"),
    ("recursive_result_changed_to_go", "parser_or_schema"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
)


class D128FullBlockAccumulatorBackendError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128FullBlockAccumulatorBackendError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


BLOCK_RECEIPT = _load_module(BLOCK_RECEIPT_SCRIPT, "zkai_d128_block_receipt_for_full_block_accumulator")


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


def expect_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise D128FullBlockAccumulatorBackendError(f"{field} mismatch")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128FullBlockAccumulatorBackendError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D128FullBlockAccumulatorBackendError(f"{field} must be a list")
    return value


def require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise D128FullBlockAccumulatorBackendError(f"{field} must be a non-empty string")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128FullBlockAccumulatorBackendError(f"{field} must be an integer")
    return value


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise D128FullBlockAccumulatorBackendError(f"{field} must be a boolean")
    return value


def require_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise D128FullBlockAccumulatorBackendError(f"{field} must be a commitment string")
    if not value.startswith("blake2b-256:"):
        raise D128FullBlockAccumulatorBackendError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128FullBlockAccumulatorBackendError(f"{field} must be a 32-byte lowercase hex digest")
    return value


@lru_cache(maxsize=None)
def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


@lru_cache(maxsize=None)
def _load_json_cached(path: pathlib.Path) -> str:
    with path.open("rb") as handle:
        payload = json.loads(handle.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise D128FullBlockAccumulatorBackendError(f"JSON evidence must be an object: {path}")
    return canonical_json_bytes(payload).decode("utf-8")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(_load_json_cached(path.resolve()))


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def _validate_block_receipt_source(payload: dict[str, Any]) -> None:
    try:
        BLOCK_RECEIPT.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128FullBlockAccumulatorBackendError(f"block receipt source validation failed: {err}") from err
    if payload.get("all_mutations_rejected") is not True:
        raise D128FullBlockAccumulatorBackendError("block receipt source did not reject all checked mutations")


@lru_cache(maxsize=None)
def _checked_block_receipt_json(path: pathlib.Path) -> str:
    payload = load_json(path)
    _validate_block_receipt_source(payload)
    return canonical_json_bytes(payload).decode("utf-8")


def load_checked_block_receipt(path: pathlib.Path = BLOCK_RECEIPT_EVIDENCE) -> dict[str, Any]:
    payload = json.loads(_checked_block_receipt_json(path.resolve()))
    return payload


def block_receipt_source_descriptor(source: dict[str, Any], path: pathlib.Path = BLOCK_RECEIPT_EVIDENCE) -> dict[str, Any]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "result": source["result"],
        "block_receipt_commitment": receipt["block_receipt_commitment"],
        "statement_commitment": receipt["statement_commitment"],
        "slice_chain_commitment": source["slice_chain_commitment"],
        "evidence_manifest_commitment": source["evidence_manifest_commitment"],
    }


def _source_hashes(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "slice_id": item["slice_id"],
            "source_file_sha256": item["file_sha256"],
            "source_payload_sha256": item["payload_sha256"],
        }
        for item in require_list(source.get("source_evidence_manifest"), "source evidence manifest")
    ]


def _slice_statement_commitments(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"slice_id": item["slice_id"], "statement_commitment": item["statement_commitment"]}
        for item in require_list(source.get("slice_chain"), "slice chain")
    ]


def _validate_source_files_against_manifest(source: dict[str, Any]) -> None:
    manifest = require_list(source.get("source_evidence_manifest"), "source evidence manifest")
    for item in manifest:
        entry = require_object(item, "source evidence manifest item")
        source_path = ROOT / require_str(entry.get("path"), "source evidence path")
        actual = load_json(source_path)
        expect_equal(file_sha256(source_path), entry.get("file_sha256"), f"{entry.get('slice_id')} file hash")
        expect_equal(sha256_hex_json(actual), entry.get("payload_sha256"), f"{entry.get('slice_id')} payload hash")


def build_verifier_transcript(source: dict[str, Any]) -> list[dict[str, Any]]:
    _validate_source_files_against_manifest(source)
    chain = require_list(source.get("slice_chain"), "slice chain")
    manifest = require_list(source.get("source_evidence_manifest"), "source evidence manifest")
    if len(chain) != EXPECTED_SLICE_COUNT or len(manifest) != EXPECTED_SLICE_COUNT:
        raise D128FullBlockAccumulatorBackendError("full-block slice count mismatch")
    transcript: list[dict[str, Any]] = []
    for expected_index, (slice_item, manifest_item) in enumerate(zip(chain, manifest, strict=True)):
        slice_item = require_object(slice_item, f"slice chain item {expected_index}")
        manifest_item = require_object(manifest_item, f"source evidence item {expected_index}")
        slice_id = require_str(slice_item.get("slice_id"), f"slice {expected_index} id")
        expect_equal(manifest_item.get("slice_id"), slice_id, f"{slice_id} manifest id")
        expect_equal(slice_item.get("index"), expected_index, f"{slice_id} index")
        expect_equal(manifest_item.get("index"), expected_index, f"{slice_id} manifest index")
        row_count = require_int(slice_item.get("row_count"), f"{slice_id} row count")
        if row_count <= 0:
            raise D128FullBlockAccumulatorBackendError(f"{slice_id} row count must be positive")
        transcript.append(
            {
                "index": expected_index,
                "slice_id": slice_id,
                "schema": slice_item["schema"],
                "decision": slice_item["decision"],
                "proof_backend_version": slice_item["proof_backend_version"],
                "validator": f"validate_{slice_id}_source_evidence",
                "verified": True,
                "source_path": manifest_item["path"],
                "source_file_sha256": manifest_item["file_sha256"],
                "source_payload_sha256": manifest_item["payload_sha256"],
                "proof_native_parameter_commitment": slice_item["proof_native_parameter_commitment"],
                "public_instance_commitment": slice_item["public_instance_commitment"],
                "statement_commitment": slice_item["statement_commitment"],
                "source_commitments": copy.deepcopy(slice_item["source_commitments"]),
                "target_commitments": copy.deepcopy(slice_item["target_commitments"]),
                "row_count": row_count,
            }
        )
    total_rows = sum(item["row_count"] for item in transcript)
    if total_rows != EXPECTED_CHECKED_ROWS:
        raise D128FullBlockAccumulatorBackendError("full-block checked-row total mismatch")
    return transcript


def accumulator_preimage(source: dict[str, Any], transcript: list[dict[str, Any]]) -> dict[str, Any]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    public_inputs = {
        "required_public_inputs": list(REQUIRED_PUBLIC_INPUTS),
        "block_receipt_commitment": require_commitment(receipt.get("block_receipt_commitment"), "block receipt commitment"),
        "statement_commitment": require_commitment(receipt.get("statement_commitment"), "statement commitment"),
        "slice_chain_commitment": require_commitment(source.get("slice_chain_commitment"), "slice chain commitment"),
        "evidence_manifest_commitment": require_commitment(
            source.get("evidence_manifest_commitment"), "evidence manifest commitment"
        ),
        "slice_statement_commitments": _slice_statement_commitments(source),
        "source_evidence_hashes": _source_hashes(source),
    }
    expect_equal(
        public_inputs["slice_statement_commitments"],
        [{"slice_id": item["slice_id"], "statement_commitment": item["statement_commitment"]} for item in transcript],
        "public slice statements",
    )
    expect_equal(
        public_inputs["source_evidence_hashes"],
        [
            {
                "slice_id": item["slice_id"],
                "source_file_sha256": item["source_file_sha256"],
                "source_payload_sha256": item["source_payload_sha256"],
            }
            for item in transcript
        ],
        "public source hashes",
    )
    return {
        "accumulator_schema": ACCUMULATOR_SCHEMA,
        "accumulator_kind": ACCUMULATOR_KIND,
        "claim_boundary": CLAIM_BOUNDARY,
        "issue": ISSUE,
        "width": WIDTH,
        "slice_count": EXPECTED_SLICE_COUNT,
        "total_checked_rows": EXPECTED_CHECKED_ROWS,
        "public_inputs": public_inputs,
        "block_receipt": copy.deepcopy(receipt),
        "slice_chain": copy.deepcopy(source["slice_chain"]),
        "source_evidence_manifest": copy.deepcopy(source["source_evidence_manifest"]),
        "verifier_transcript": copy.deepcopy(transcript),
    }


def accumulator_artifact(source: dict[str, Any]) -> dict[str, Any]:
    transcript = build_verifier_transcript(source)
    preimage = accumulator_preimage(source, transcript)
    return {
        "schema": ACCUMULATOR_SCHEMA,
        "accumulator_kind": ACCUMULATOR_KIND,
        "claim_boundary": CLAIM_BOUNDARY,
        "issue": ISSUE,
        "accumulator_commitment": blake2b_commitment(preimage, ACCUMULATOR_DOMAIN),
        "preimage": preimage,
    }


def verifier_handle_preimage(artifact: dict[str, Any]) -> dict[str, Any]:
    preimage = require_object(artifact.get("preimage"), "accumulator preimage")
    public_inputs = require_object(preimage.get("public_inputs"), "accumulator public inputs")
    return {
        "schema": VERIFIER_HANDLE_SCHEMA,
        "accepted_accumulator_schema": artifact["schema"],
        "accepted_accumulator_kind": artifact["accumulator_kind"],
        "accepted_accumulator_commitment": artifact["accumulator_commitment"],
        "accepted_claim_boundary": CLAIM_BOUNDARY,
        "required_public_inputs": list(REQUIRED_PUBLIC_INPUTS),
        "block_receipt_commitment": public_inputs["block_receipt_commitment"],
        "statement_commitment": public_inputs["statement_commitment"],
        "slice_chain_commitment": public_inputs["slice_chain_commitment"],
        "evidence_manifest_commitment": public_inputs["evidence_manifest_commitment"],
        "slice_statement_commitments": copy.deepcopy(public_inputs["slice_statement_commitments"]),
        "source_evidence_hashes": copy.deepcopy(public_inputs["source_evidence_hashes"]),
        "verifier_steps": [
            "validate checked d128 block receipt evidence",
            "validate source slice evidence hashes and slice-chain edges",
            "compare block receipt, statement, slice-chain, and evidence-manifest commitments",
            "compare every slice statement commitment and source hash",
            "recompute accumulator commitment",
        ],
    }


def verifier_handle(artifact: dict[str, Any]) -> dict[str, Any]:
    preimage = verifier_handle_preimage(artifact)
    return {
        "schema": VERIFIER_HANDLE_SCHEMA,
        "claim_boundary": CLAIM_BOUNDARY,
        "verifier_handle_commitment": blake2b_commitment(preimage, VERIFIER_HANDLE_DOMAIN),
        "preimage": preimage,
        "accepted": True,
    }


def recursive_or_pcd_status() -> dict[str, Any]:
    return {
        "result": RECURSIVE_OR_PCD_RESULT,
        "recursive_outer_proof_claimed": False,
        "pcd_outer_proof_claimed": False,
        "outer_proof_artifacts": [],
        "proof_metrics": {
            "recursive_proof_size_bytes": None,
            "recursive_verifier_time_ms": None,
            "recursive_proof_generation_time_ms": None,
        },
        "first_blocker": RECURSIVE_BLOCKER,
    }


def build_payload() -> dict[str, Any]:
    source = load_checked_block_receipt()
    artifact = accumulator_artifact(source)
    handle = verifier_handle(artifact)
    descriptor = block_receipt_source_descriptor(source)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "accumulator_result": ACCUMULATOR_RESULT,
        "recursive_or_pcd_result": RECURSIVE_OR_PCD_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_block_receipt": descriptor,
        "accumulator_artifact": artifact,
        "verifier_handle": handle,
        "recursive_or_pcd_status": recursive_or_pcd_status(),
        "summary": {
            "accumulator_status": ACCUMULATOR_RESULT,
            "recursive_or_pcd_status": RECURSIVE_OR_PCD_RESULT,
            "claim_boundary": CLAIM_BOUNDARY,
            "slice_count": EXPECTED_SLICE_COUNT,
            "total_checked_rows": EXPECTED_CHECKED_ROWS,
            "block_receipt_commitment": descriptor["block_receipt_commitment"],
            "statement_commitment": descriptor["statement_commitment"],
            "accumulator_commitment": artifact["accumulator_commitment"],
            "verifier_handle_commitment": handle["verifier_handle_commitment"],
            "go_criterion": GO_CRITERION,
            "recursive_blocker": RECURSIVE_BLOCKER,
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    _validate_draft_payload(payload)
    return payload


def _validate_source_descriptor(payload: dict[str, Any]) -> dict[str, Any]:
    descriptor = require_object(payload.get("source_block_receipt"), "source block receipt")
    expect_equal(descriptor.get("path"), relative_path(BLOCK_RECEIPT_EVIDENCE), "source block receipt path")
    source = load_checked_block_receipt(ROOT / descriptor["path"])
    expected = block_receipt_source_descriptor(source)
    expect_equal(descriptor, expected, "source block receipt descriptor")
    return source


def verify_accumulator_artifact(artifact: Any, source: dict[str, Any] | None = None) -> None:
    artifact = require_object(artifact, "accumulator artifact")
    expect_equal(artifact.get("schema"), ACCUMULATOR_SCHEMA, "accumulator schema")
    expect_equal(artifact.get("accumulator_kind"), ACCUMULATOR_KIND, "accumulator kind")
    expect_equal(artifact.get("claim_boundary"), CLAIM_BOUNDARY, "accumulator claim boundary")
    expect_equal(artifact.get("issue"), ISSUE, "accumulator issue")
    source = copy.deepcopy(source) if source is not None else load_checked_block_receipt()
    expected_artifact = accumulator_artifact(source)
    preimage = require_object(artifact.get("preimage"), "accumulator preimage")
    expected_preimage = expected_artifact["preimage"]
    expect_equal(preimage.get("public_inputs"), expected_preimage["public_inputs"], "public inputs")
    receipt = require_object(preimage.get("block_receipt"), "accumulator block receipt")
    expected_receipt = expected_preimage["block_receipt"]
    expect_equal(receipt.get("verifier_domain"), expected_receipt["verifier_domain"], "verifier domain")
    expect_equal(preimage.get("block_receipt"), expected_preimage["block_receipt"], "accumulator block receipt")
    expect_equal(preimage.get("slice_chain"), expected_preimage["slice_chain"], "slice transcript")
    expect_equal(
        preimage.get("source_evidence_manifest"),
        expected_preimage["source_evidence_manifest"],
        "source evidence manifest",
    )
    expect_equal(preimage.get("verifier_transcript"), expected_preimage["verifier_transcript"], "verifier transcript")
    expect_equal(artifact, expected_artifact, "accumulator artifact")


def verify_verifier_handle(handle: Any, artifact: dict[str, Any]) -> None:
    handle = require_object(handle, "verifier handle")
    expect_equal(handle.get("schema"), VERIFIER_HANDLE_SCHEMA, "verifier handle schema")
    expect_equal(handle.get("claim_boundary"), CLAIM_BOUNDARY, "verifier handle claim boundary")
    expect_equal(handle.get("accepted"), True, "verifier handle accepted")
    expected = verifier_handle(artifact)
    expect_equal(handle, expected, "verifier handle")


def _validate_recursive_status(payload: dict[str, Any]) -> None:
    status = require_object(payload.get("recursive_or_pcd_status"), "recursive or PCD status")
    expect_equal(status, recursive_or_pcd_status(), "recursive or PCD status")


def _expected_summary(source: dict[str, Any], artifact: dict[str, Any], handle: dict[str, Any]) -> dict[str, Any]:
    descriptor = block_receipt_source_descriptor(source)
    return {
        "accumulator_status": ACCUMULATOR_RESULT,
        "recursive_or_pcd_status": RECURSIVE_OR_PCD_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "slice_count": EXPECTED_SLICE_COUNT,
        "total_checked_rows": EXPECTED_CHECKED_ROWS,
        "block_receipt_commitment": descriptor["block_receipt_commitment"],
        "statement_commitment": descriptor["statement_commitment"],
        "accumulator_commitment": artifact["accumulator_commitment"],
        "verifier_handle_commitment": handle["verifier_handle_commitment"],
        "go_criterion": GO_CRITERION,
        "recursive_blocker": RECURSIVE_BLOCKER,
    }


def _validate_common_payload(payload: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = require_object(payload, "full-block accumulator backend payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("issue"), ISSUE, "issue")
    expect_equal(payload.get("accumulator_result"), ACCUMULATOR_RESULT, "accumulator result")
    expect_equal(payload.get("recursive_or_pcd_result"), RECURSIVE_OR_PCD_RESULT, "recursive or PCD result")
    expect_equal(payload.get("claim_boundary"), CLAIM_BOUNDARY, "claim boundary")
    source = _validate_source_descriptor(payload)
    artifact = require_object(payload.get("accumulator_artifact"), "accumulator artifact")
    verify_accumulator_artifact(artifact, source)
    handle = require_object(payload.get("verifier_handle"), "verifier handle")
    verify_verifier_handle(handle, artifact)
    _validate_recursive_status(payload)
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    return source, artifact, handle, _expected_summary(source, artifact, handle)


def _validate_draft_payload(payload: Any) -> None:
    _source, _artifact, _handle, expected_summary = _validate_common_payload(payload)
    if (
        "mutation_inventory" in payload
        or "cases" in payload
        or "case_count" in payload
        or "all_mutations_rejected" in payload
    ):
        raise D128FullBlockAccumulatorBackendError("draft payload must not include mutation metadata")
    expect_equal(payload.get("summary"), expected_summary, "summary")


def _draft_payload_for_case_replay(payload: dict[str, Any]) -> dict[str, Any]:
    draft = copy.deepcopy(payload)
    for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected"):
        draft.pop(field, None)
    summary = require_object(draft.get("summary"), "summary")
    summary.pop("mutation_cases", None)
    summary.pop("mutations_rejected", None)
    return draft


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    has_cases = "cases" in payload
    has_case_count = "case_count" in payload
    has_all_mutations_rejected = "all_mutations_rejected" in payload
    has_mutation_inventory = "mutation_inventory" in payload
    if not (has_cases or has_case_count or has_all_mutations_rejected or has_mutation_inventory):
        raise D128FullBlockAccumulatorBackendError("mutation metadata missing")
    if not (has_mutation_inventory and has_cases and has_case_count and has_all_mutations_rejected):
        raise D128FullBlockAccumulatorBackendError(
            "mutation metadata must include mutation_inventory, cases, case_count, and all_mutations_rejected together"
        )
    inventory = require_list(payload.get("mutation_inventory"), "mutation inventory")
    expect_equal(inventory, expected_mutation_inventory(), "mutation inventory")
    cases = require_list(payload.get("cases"), "mutation cases")
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    rejected = 0
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"mutation case {index}")
        for column in TSV_COLUMNS:
            if column not in case:
                raise D128FullBlockAccumulatorBackendError(f"mutation case {index} missing {column}")
        pair = (
            require_str(case["mutation"], f"mutation case {index} mutation"),
            require_str(case["surface"], f"mutation case {index} surface"),
        )
        if pair in seen:
            raise D128FullBlockAccumulatorBackendError(f"duplicate mutation case {index}")
        seen.add(pair)
        pairs.append(pair)
        expect_equal(case["baseline_result"], RESULT, f"mutation case {index} baseline result")
        require_bool(case["mutated_accepted"], f"mutation case {index} mutated_accepted")
        require_bool(case["rejected"], f"mutation case {index} rejected")
        if case["rejected"] == case["mutated_accepted"]:
            raise D128FullBlockAccumulatorBackendError(f"mutation case {index} rejected/accepted mismatch")
        require_str(case["rejection_layer"], f"mutation case {index} rejection layer")
        if not isinstance(case["error"], str):
            raise D128FullBlockAccumulatorBackendError(f"mutation case {index} error must be a string")
        if case["rejected"]:
            rejected += 1
    expect_equal(tuple(pairs), EXPECTED_MUTATION_INVENTORY, "mutation case inventory")
    expect_equal(payload.get("case_count"), len(cases), "case_count")
    expect_equal(payload.get("all_mutations_rejected"), all(case["rejected"] for case in cases), "all_mutations_rejected")
    expected_by_pair = {
        (case["mutation"], case["surface"]): case
        for case in mutation_cases(_draft_payload_for_case_replay(payload))
    }
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"mutation case {index}")
        expected = expected_by_pair.get((case["mutation"], case["surface"]))
        if expected is None:
            raise D128FullBlockAccumulatorBackendError(f"missing recomputed mutation case {index}")
        for column in TSV_COLUMNS:
            expect_equal(case[column], expected[column], f"mutation case {index} {column}")
    return len(cases), rejected


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "full-block accumulator backend payload")
    _source, _artifact, _handle, expected_summary = _validate_common_payload(payload)
    case_count, rejected = _validate_case_metadata(payload)
    if rejected != case_count:
        raise D128FullBlockAccumulatorBackendError("not all full-block accumulator backend mutations rejected")
    expected_summary["mutation_cases"] = case_count
    expected_summary["mutations_rejected"] = rejected
    expect_equal(payload.get("summary"), expected_summary, "summary")


def classify_error(error: Exception) -> str:
    text = str(error).lower()
    if "source block receipt" in text:
        return "source_block_receipt"
    if "verifier handle" in text:
        return "verifier_handle"
    if "recursive" in text or "pcd" in text or "metric" in text or "blocker" in text:
        return "recursive_or_pcd_status"
    if "public" in text:
        return "public_inputs"
    if "verifier transcript" in text or "verifier domain" in text or "validator" in text:
        return "verifier_transcript"
    if "source" in text or "payload" in text or "file" in text or "statement" in text:
        return "source_evidence_manifest"
    if "slice" in text or "row" in text:
        return "slice_transcript"
    if "accumulator artifact" in text or "accumulator" in text:
        return "accumulator_artifact"
    return "parser_or_schema"


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []

    def add(name: str, surface: str, mutator: Callable[[dict[str, Any]], None]) -> None:
        mutated = copy.deepcopy(baseline)
        mutator(mutated)
        cases.append((name, surface, mutated))

    add("source_block_receipt_file_hash_drift", "source_block_receipt", lambda p: p["source_block_receipt"].__setitem__("file_sha256", "00" * 32))
    add("source_block_receipt_payload_hash_drift", "source_block_receipt", lambda p: p["source_block_receipt"].__setitem__("payload_sha256", "11" * 32))
    add("source_block_receipt_result_drift", "source_block_receipt", lambda p: p["source_block_receipt"].__setitem__("result", "NO_GO"))
    add("source_block_receipt_commitment_drift", "source_block_receipt", lambda p: p["source_block_receipt"].__setitem__("block_receipt_commitment", "blake2b-256:" + "22" * 32))
    add("source_statement_commitment_drift", "source_block_receipt", lambda p: p["source_block_receipt"].__setitem__("statement_commitment", "blake2b-256:" + "23" * 32))
    add("source_slice_chain_commitment_drift", "source_block_receipt", lambda p: p["source_block_receipt"].__setitem__("slice_chain_commitment", "blake2b-256:" + "24" * 32))
    add("source_evidence_manifest_commitment_drift", "source_block_receipt", lambda p: p["source_block_receipt"].__setitem__("evidence_manifest_commitment", "blake2b-256:" + "25" * 32))
    add("accumulator_commitment_drift", "accumulator_artifact", lambda p: p["accumulator_artifact"].__setitem__("accumulator_commitment", "blake2b-256:" + "33" * 32))
    add("accumulator_claim_boundary_changed_to_recursive", "accumulator_artifact", lambda p: p["accumulator_artifact"].__setitem__("claim_boundary", "RECURSIVE_OUTER_PROOF"))
    add("accumulator_block_receipt_commitment_drift", "accumulator_artifact", lambda p: p["accumulator_artifact"]["preimage"]["block_receipt"].__setitem__("block_receipt_commitment", "blake2b-256:" + "44" * 32))
    add("accumulator_statement_commitment_drift", "accumulator_artifact", lambda p: p["accumulator_artifact"]["preimage"]["block_receipt"].__setitem__("statement_commitment", "blake2b-256:" + "45" * 32))
    add("accumulator_slice_chain_commitment_drift", "accumulator_artifact", lambda p: p["accumulator_artifact"]["preimage"]["block_receipt"].__setitem__("slice_chain_commitment", "blake2b-256:" + "46" * 32))
    add("accumulator_evidence_manifest_commitment_drift", "accumulator_artifact", lambda p: p["accumulator_artifact"]["preimage"]["block_receipt"].__setitem__("evidence_manifest_commitment", "blake2b-256:" + "47" * 32))
    add("public_input_block_receipt_commitment_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"].__setitem__("block_receipt_commitment", "blake2b-256:" + "55" * 32))
    add("public_input_statement_commitment_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"].__setitem__("statement_commitment", "blake2b-256:" + "56" * 32))
    add("public_input_slice_chain_commitment_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"].__setitem__("slice_chain_commitment", "blake2b-256:" + "57" * 32))
    add("public_input_evidence_manifest_commitment_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"].__setitem__("evidence_manifest_commitment", "blake2b-256:" + "58" * 32))
    add("public_input_slice_statement_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"]["slice_statement_commitments"][0].__setitem__("statement_commitment", "blake2b-256:" + "66" * 32))
    add("public_input_source_hash_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"]["source_evidence_hashes"][0].__setitem__("source_payload_sha256", "77" * 32))
    add("slice_removed", "slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"].pop())
    add("slice_duplicated", "slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"].append(copy.deepcopy(p["accumulator_artifact"]["preimage"]["verifier_transcript"][0])))
    add("slice_reordered", "slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"].reverse())
    add("slice_row_count_drift", "slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][2].__setitem__("row_count", 1))
    add("slice_source_commitment_drift", "slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][1]["source_commitments"].__setitem__("source_rmsnorm_statement_commitment", "blake2b-256:" + "88" * 32))
    add("slice_target_commitment_drift", "slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][4]["target_commitments"].__setitem__("residual_delta_commitment", "blake2b-256:" + "89" * 32))
    add("source_manifest_file_hash_drift", "source_evidence_manifest", lambda p: p["accumulator_artifact"]["preimage"]["source_evidence_manifest"][0].__setitem__("file_sha256", "99" * 32))
    add("source_manifest_payload_hash_drift", "source_evidence_manifest", lambda p: p["accumulator_artifact"]["preimage"]["source_evidence_manifest"][0].__setitem__("payload_sha256", "aa" * 32))
    add("transcript_statement_commitment_drift", "source_evidence_manifest", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("statement_commitment", "blake2b-256:" + "ab" * 32))
    add("transcript_public_instance_commitment_drift", "source_evidence_manifest", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("public_instance_commitment", "blake2b-256:" + "ac" * 32))
    add("verifier_domain_drift", "verifier_transcript", lambda p: p["accumulator_artifact"]["preimage"]["block_receipt"].__setitem__("verifier_domain", "ptvm:zkai:d128:tampered-verifier-domain:v0"))
    add("validator_name_drift", "verifier_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("validator", "wrong_validator"))
    add("validator_result_false", "verifier_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("verified", False))
    add("verifier_handle_commitment_drift", "verifier_handle", lambda p: p["verifier_handle"].__setitem__("verifier_handle_commitment", "blake2b-256:" + "dd" * 32))
    add("verifier_handle_claim_boundary_changed_to_recursive", "verifier_handle", lambda p: p["verifier_handle"].__setitem__("claim_boundary", "RECURSIVE_OUTER_PROOF"))
    add("verifier_handle_block_receipt_commitment_drift", "verifier_handle", lambda p: p["verifier_handle"]["preimage"].__setitem__("block_receipt_commitment", "blake2b-256:" + "ee" * 32))
    add("verifier_handle_statement_commitment_drift", "verifier_handle", lambda p: p["verifier_handle"]["preimage"].__setitem__("statement_commitment", "blake2b-256:" + "ef" * 32))
    add("verifier_handle_accumulator_commitment_drift", "verifier_handle", lambda p: p["verifier_handle"]["preimage"].__setitem__("accepted_accumulator_commitment", "blake2b-256:" + "ff" * 32))
    add("verifier_handle_missing_required_public_input", "verifier_handle", lambda p: p["verifier_handle"]["preimage"]["required_public_inputs"].pop())
    add("recursive_outer_proof_claimed", "recursive_or_pcd_status", lambda p: p["recursive_or_pcd_status"].__setitem__("recursive_outer_proof_claimed", True))
    add("pcd_outer_proof_claimed", "recursive_or_pcd_status", lambda p: p["recursive_or_pcd_status"].__setitem__("pcd_outer_proof_claimed", True))
    add("recursive_proof_metric_smuggled", "recursive_or_pcd_status", lambda p: p["recursive_or_pcd_status"]["proof_metrics"].__setitem__("recursive_verifier_time_ms", 1.0))
    add("recursive_blocker_removed", "recursive_or_pcd_status", lambda p: p["recursive_or_pcd_status"].__setitem__("first_blocker", ""))
    add("decision_changed_to_no_go", "parser_or_schema", lambda p: p.__setitem__("decision", "NO_GO"))
    add("result_changed_to_no_go", "parser_or_schema", lambda p: p.__setitem__("result", "BOUNDED_NO_GO"))
    add("accumulator_result_changed_to_no_go", "parser_or_schema", lambda p: p.__setitem__("accumulator_result", "NO_GO"))
    add("recursive_result_changed_to_go", "parser_or_schema", lambda p: p.__setitem__("recursive_or_pcd_result", "GO_RECURSIVE_OUTER_PROOF"))
    add("non_claims_removed", "parser_or_schema", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1]))
    add("validation_command_drift", "parser_or_schema", lambda p: p["validation_commands"].append("echo unsafe"))
    return cases


def mutation_cases(baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_payload())
    _validate_draft_payload(baseline)
    cases = []
    for mutation, surface, mutated in _mutated_cases(baseline):
        try:
            _validate_draft_payload(mutated)
            accepted = True
            error = ""
            layer = "accepted"
        except D128FullBlockAccumulatorBackendError as err:
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
    payload["mutation_inventory"] = expected_mutation_inventory()
    payload["cases"] = cases
    payload["case_count"] = len(cases)
    payload["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    payload["summary"]["mutation_cases"] = len(cases)
    payload["summary"]["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    validate_payload(payload)
    return payload


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for case in payload["cases"]:
        writer.writerow({column: case[column] for column in TSV_COLUMNS})
    return output.getvalue()


def _safe_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_absolute():
        raise D128FullBlockAccumulatorBackendError(f"output path must be repo-relative: {path}")
    pure = pathlib.PurePosixPath(path.as_posix())
    if path.as_posix() != pure.as_posix() or any(part in ("", ".", "..") for part in pure.parts):
        raise D128FullBlockAccumulatorBackendError(f"output path must be repo-relative without traversal: {path}")
    candidate = ROOT.joinpath(*pure.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128FullBlockAccumulatorBackendError(f"output path escapes repository: {path}") from err
    return candidate


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    outputs: list[tuple[pathlib.Path, bytes]] = []
    if json_path is not None:
        outputs.append((_safe_output_path(json_path), json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"))
    if tsv_path is not None:
        outputs.append((_safe_output_path(tsv_path), to_tsv(payload).encode("utf-8")))
    resolved_outputs = [path.resolve(strict=False) for path, _data in outputs]
    if len(resolved_outputs) != len(set(resolved_outputs)):
        raise D128FullBlockAccumulatorBackendError("write-json and write-tsv output paths must be distinct")
    for path, data in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as handle:
            tmp = pathlib.Path(handle.name)
            handle.write(data)
        tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the d128 full-block non-recursive accumulator backend evidence. "
            "GO means accumulator integrity only; recursive/PCD outer proof remains NO-GO."
        )
    )
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    if args.write_json is None and args.write_tsv is None:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
