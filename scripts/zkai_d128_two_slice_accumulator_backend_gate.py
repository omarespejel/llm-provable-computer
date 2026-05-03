#!/usr/bin/env python3
"""Build and verify the d128 two-slice verifier-facing accumulator backend.

This is the issue #409 follow-up to the two-slice outer-proof target spike.  It
constructs a real verifier-facing accumulator over the two selected d128 slice
checks and verifies that the accumulator binds:

* the two-slice target commitment;
* the selected slice statement commitments; and
* the selected source evidence hashes.

The accumulator is deliberately non-recursive.  It verifies the source slice
evidence and accumulates the checked public inputs into one commitment, but it
is not a STARK-in-STARK proof, PCD object, compressed verifier object, or
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
TWO_SLICE_SCRIPT = ROOT / "scripts" / "zkai_d128_two_slice_outer_proof_object_spike_gate.py"
RMSNORM_SCRIPT = ROOT / "scripts" / "zkai_d128_rmsnorm_public_row_proof_input.py"
BRIDGE_SCRIPT = ROOT / "scripts" / "zkai_d128_rmsnorm_to_projection_bridge_input.py"
TWO_SLICE_EVIDENCE = EVIDENCE_DIR / "zkai-d128-two-slice-outer-proof-object-spike-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-two-slice-accumulator-backend-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-two-slice-accumulator-backend-2026-05.tsv"

SCHEMA = "zkai-d128-two-slice-accumulator-backend-v1"
DECISION = "GO_D128_TWO_SLICE_VERIFIER_ACCUMULATOR_BACKEND"
RESULT = "GO"
ISSUE = 409
ACCUMULATOR_RESULT = "GO_D128_TWO_SLICE_VERIFIER_ACCUMULATOR"
RECURSIVE_OR_PCD_RESULT = "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING"
ACCUMULATOR_SCHEMA = "zkai-d128-two-slice-verifier-accumulator-v1"
VERIFIER_HANDLE_SCHEMA = "zkai-d128-two-slice-accumulator-verifier-handle-v1"
ACCUMULATOR_KIND = "non-recursive-two-slice-verifier-accumulator"
CLAIM_BOUNDARY = "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF"
WIDTH = 128
EXPECTED_SELECTED_ROWS = 256
EXPECTED_SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")

ACCUMULATOR_DOMAIN = "ptvm:zkai:d128-two-slice:verifier-accumulator:v1"
VERIFIER_HANDLE_DOMAIN = "ptvm:zkai:d128-two-slice:accumulator-verifier-handle:v1"

GO_CRITERION = (
    "one verifier-facing accumulator object exists, a local verifier handle accepts it, "
    "and the accumulator binds two_slice_target_commitment, selected slice statement "
    "commitments, and selected source evidence hashes"
)

RECURSIVE_BLOCKER = (
    "no executable recursive/PCD outer proof backend currently proves the two selected "
    "d128 slice-verifier checks inside one cryptographic outer proof"
)

NON_CLAIMS = [
    "not recursive aggregation of the selected slice proofs",
    "not proof-carrying-data accumulation",
    "not a STARK-in-STARK verifier proof",
    "not one compressed cryptographic verifier object",
    "not proof-size evidence for a recursive outer proof",
    "not verifier-time evidence for a recursive outer proof",
    "not proof-generation-time evidence for a recursive outer proof",
    "not aggregation of all six d128 slice proofs",
    "not matched NANOZK, DeepProve, EZKL, snarkjs, or JSTprove comparison evidence",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_two_slice_accumulator_backend_gate.py --write-json docs/engineering/evidence/zkai-d128-two-slice-accumulator-backend-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-two-slice-accumulator-backend-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_two_slice_accumulator_backend_gate",
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
    ("source_two_slice_file_hash_drift", "source_two_slice_target"),
    ("source_two_slice_payload_hash_drift", "source_two_slice_target"),
    ("source_two_slice_result_drift", "source_two_slice_target"),
    ("source_two_slice_target_commitment_drift", "source_two_slice_target"),
    ("accumulator_commitment_drift", "accumulator_artifact"),
    ("accumulator_claim_boundary_changed_to_recursive", "accumulator_artifact"),
    ("source_full_aggregation_target_commitment_drift", "accumulator_artifact"),
    ("public_input_target_commitment_drift", "public_inputs"),
    ("public_input_selected_statement_drift", "public_inputs"),
    ("public_input_selected_source_hash_drift", "public_inputs"),
    ("selected_slice_removed", "selected_slice_transcript"),
    ("selected_slice_duplicated", "selected_slice_transcript"),
    ("selected_slice_reordered", "selected_slice_transcript"),
    ("selected_slice_row_count_drift", "selected_slice_transcript"),
    ("source_file_hash_drift", "selected_source_evidence"),
    ("source_payload_hash_drift", "selected_source_evidence"),
    ("source_statement_commitment_drift", "selected_source_evidence"),
    ("source_public_instance_commitment_drift", "selected_source_evidence"),
    ("source_target_commitment_drift", "selected_source_evidence"),
    ("verifier_domain_drift", "verifier_transcript"),
    ("validator_name_drift", "verifier_transcript"),
    ("validator_result_false", "verifier_transcript"),
    ("verifier_handle_commitment_drift", "verifier_handle"),
    ("verifier_handle_claim_boundary_changed_to_recursive", "verifier_handle"),
    ("verifier_handle_target_commitment_drift", "verifier_handle"),
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

SLICE_VALIDATOR_SCRIPTS = {
    "rmsnorm_public_rows": RMSNORM_SCRIPT,
    "rmsnorm_projection_bridge": BRIDGE_SCRIPT,
}

SLICE_VALIDATOR_MODULES = {
    "rmsnorm_public_rows": "zkai_d128_rmsnorm_for_two_slice_accumulator",
    "rmsnorm_projection_bridge": "zkai_d128_bridge_for_two_slice_accumulator",
}


class D128TwoSliceAccumulatorBackendError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128TwoSliceAccumulatorBackendError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


TWO_SLICE = _load_module(TWO_SLICE_SCRIPT, "zkai_d128_two_slice_spike_for_accumulator_backend")
SLICE_VALIDATORS = {
    slice_id: _load_module(path, SLICE_VALIDATOR_MODULES[slice_id])
    for slice_id, path in SLICE_VALIDATOR_SCRIPTS.items()
}


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
        raise D128TwoSliceAccumulatorBackendError(f"{field} mismatch")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128TwoSliceAccumulatorBackendError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D128TwoSliceAccumulatorBackendError(f"{field} must be a list")
    return value


def require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise D128TwoSliceAccumulatorBackendError(f"{field} must be a non-empty string")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128TwoSliceAccumulatorBackendError(f"{field} must be an integer")
    return value


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise D128TwoSliceAccumulatorBackendError(f"{field} must be a boolean")
    return value


def require_sha256_hex(value: Any, field: str) -> str:
    value = require_str(value, field)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise D128TwoSliceAccumulatorBackendError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def require_commitment(value: Any, field: str) -> str:
    value = require_str(value, field)
    if not value.startswith("blake2b-256:"):
        raise D128TwoSliceAccumulatorBackendError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128TwoSliceAccumulatorBackendError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def _cache_key(path: pathlib.Path) -> str:
    return path.resolve(strict=False).as_posix()


@lru_cache(maxsize=None)
def _file_sha256_cached(path_key: str) -> str:
    try:
        return TWO_SLICE.file_sha256(pathlib.Path(path_key))
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128TwoSliceAccumulatorBackendError(f"failed to hash source evidence {path_key}: {err}") from err


def file_sha256(path: pathlib.Path) -> str:
    return _file_sha256_cached(_cache_key(path))


@lru_cache(maxsize=None)
def _load_json_cached(path_key: str) -> dict[str, Any]:
    try:
        return TWO_SLICE.load_json(pathlib.Path(path_key))
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128TwoSliceAccumulatorBackendError(f"failed to load source evidence {path_key}: {err}") from err


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return copy.deepcopy(_load_json_cached(_cache_key(path)))


def relative_path(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def load_checked_two_slice_target(path: pathlib.Path = TWO_SLICE_EVIDENCE) -> dict[str, Any]:
    payload = load_json(path)
    try:
        TWO_SLICE.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128TwoSliceAccumulatorBackendError(f"two-slice target validation failed: {err}") from err
    expect_equal(payload.get("schema"), TWO_SLICE.SCHEMA, "two-slice source schema")
    expect_equal(payload.get("result"), TWO_SLICE.RESULT, "two-slice source result")
    expect_equal(payload.get("target_result"), TWO_SLICE.TARGET_RESULT, "two-slice target result")
    expect_equal(
        payload.get("outer_proof_object_result"),
        TWO_SLICE.OUTER_PROOF_RESULT,
        "two-slice prior proof-object result",
    )
    if payload.get("all_mutations_rejected") is not True:
        raise D128TwoSliceAccumulatorBackendError("two-slice source did not reject all checked mutations")
    return payload


def two_slice_source_descriptor(source: dict[str, Any], path: pathlib.Path = TWO_SLICE_EVIDENCE) -> dict[str, Any]:
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "result": source["result"],
        "target_result": source["target_result"],
        "outer_proof_object_result": source["outer_proof_object_result"],
        "two_slice_target_commitment": source["two_slice_target_commitment"],
    }


def _source_path(check: dict[str, Any]) -> pathlib.Path:
    raw = require_str(check.get("source_path"), "selected source path")
    pure = pathlib.PurePosixPath(raw)
    if pure.is_absolute() or raw != pure.as_posix() or any(part in ("", ".", "..") for part in pure.parts):
        raise D128TwoSliceAccumulatorBackendError(f"selected source path must be repo-relative: {raw}")
    path = ROOT.joinpath(*pure.parts)
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128TwoSliceAccumulatorBackendError(f"selected source path escapes repository: {raw}") from err
    return path


def _validate_slice_source(slice_id: str, source: dict[str, Any]) -> None:
    validator = SLICE_VALIDATORS.get(slice_id)
    if validator is None:
        raise D128TwoSliceAccumulatorBackendError(f"missing validator for selected slice {slice_id}")
    try:
        validator.validate_payload(source)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128TwoSliceAccumulatorBackendError(f"selected slice source validation failed for {slice_id}: {err}") from err


def _verify_check_against_source(check: dict[str, Any], source: dict[str, Any], path: pathlib.Path) -> dict[str, Any]:
    slice_id = require_str(check.get("slice_id"), "selected slice id")
    _validate_slice_source(slice_id, source)
    expect_equal(source.get("schema"), check.get("schema"), f"{slice_id} source schema")
    expect_equal(source.get("decision"), check.get("decision"), f"{slice_id} source decision")
    expect_equal(source.get("statement_commitment"), check.get("statement_commitment"), f"{slice_id} statement")
    expect_equal(
        source.get("public_instance_commitment"),
        check.get("public_instance_commitment"),
        f"{slice_id} public instance",
    )
    expect_equal(
        source.get("proof_native_parameter_commitment"),
        check.get("proof_native_parameter_commitment"),
        f"{slice_id} proof-native parameters",
    )
    expect_equal(source.get("row_count"), check.get("row_count"), f"{slice_id} row count")
    source_file_hash = file_sha256(path)
    source_payload_hash = sha256_hex_json(source)
    expect_equal(source_file_hash, check.get("source_file_sha256"), f"{slice_id} source file hash")
    expect_equal(source_payload_hash, check.get("source_payload_sha256"), f"{slice_id} source payload hash")
    for field, expected in require_object(check.get("source_commitments"), f"{slice_id} source commitments").items():
        actual = source.get(field)
        if actual != expected and source.get(f"source_{field}") == expected:
            actual = expected
        expect_equal(actual, expected, f"{slice_id} source commitment {field}")
    for field, expected in require_object(check.get("target_commitments"), f"{slice_id} target commitments").items():
        expect_equal(source.get(field), expected, f"{slice_id} target commitment {field}")
    return {
        "index": require_int(check.get("index"), f"{slice_id} index"),
        "slice_id": slice_id,
        "source_path": relative_path(path),
        "source_file_sha256": source_file_hash,
        "source_payload_sha256": source_payload_hash,
        "schema": source["schema"],
        "decision": source["decision"],
        "validator": SLICE_VALIDATOR_MODULES[slice_id],
        "validator_script": relative_path(SLICE_VALIDATOR_SCRIPTS[slice_id]),
        "verified": True,
        "row_count": source["row_count"],
        "statement_commitment": require_commitment(source.get("statement_commitment"), f"{slice_id} statement"),
        "public_instance_commitment": require_commitment(
            source.get("public_instance_commitment"),
            f"{slice_id} public instance",
        ),
        "proof_native_parameter_commitment": require_commitment(
            source.get("proof_native_parameter_commitment"),
            f"{slice_id} proof-native parameters",
        ),
        "source_commitments": copy.deepcopy(check["source_commitments"]),
        "target_commitments": copy.deepcopy(check["target_commitments"]),
    }


def build_verifier_transcript(source: dict[str, Any]) -> list[dict[str, Any]]:
    target = require_object(source.get("two_slice_target_manifest"), "two-slice target manifest")
    checks = require_list(target.get("selected_slice_checks"), "selected slice checks")
    if [require_str(require_object(check, "selected slice check").get("slice_id"), "selected slice id") for check in checks] != list(
        EXPECTED_SELECTED_SLICE_IDS
    ):
        raise D128TwoSliceAccumulatorBackendError("selected slice order mismatch")
    transcript = []
    for expected_index, raw_check in enumerate(checks):
        check = require_object(raw_check, f"selected slice check {expected_index}")
        expect_equal(check.get("index"), expected_index, f"selected slice {expected_index} index")
        path = _source_path(check)
        source_payload = load_json(path)
        transcript.append(_verify_check_against_source(check, source_payload, path))
    if sum(entry["row_count"] for entry in transcript) != EXPECTED_SELECTED_ROWS:
        raise D128TwoSliceAccumulatorBackendError("selected transcript checked-row total mismatch")
    return transcript


def _selected_statement_commitments(transcript: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"slice_id": entry["slice_id"], "statement_commitment": entry["statement_commitment"]}
        for entry in transcript
    ]


def _selected_source_evidence_hashes(transcript: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "slice_id": entry["slice_id"],
            "source_file_sha256": entry["source_file_sha256"],
            "source_payload_sha256": entry["source_payload_sha256"],
        }
        for entry in transcript
    ]


def accumulator_preimage(source: dict[str, Any], transcript: list[dict[str, Any]]) -> dict[str, Any]:
    public_inputs = copy.deepcopy(
        require_object(source.get("outer_public_input_contract"), "outer public input contract")
    )
    expect_equal(
        require_list(public_inputs.get("required_public_inputs"), "outer public input required public inputs"),
        [
            "two_slice_target_commitment",
            "selected_slice_statement_commitments",
            "selected_source_evidence_hashes",
        ],
        "outer public input required public inputs",
    )
    expect_equal(
        require_commitment(public_inputs.get("two_slice_target_commitment"), "outer public input target"),
        require_commitment(source.get("two_slice_target_commitment"), "source two-slice target commitment"),
        "public target",
    )
    expect_equal(
        require_list(public_inputs.get("selected_slice_statement_commitments"), "outer public input statements"),
        _selected_statement_commitments(transcript),
        "public statements",
    )
    expect_equal(
        require_list(public_inputs.get("selected_source_evidence_hashes"), "outer public input source hashes"),
        _selected_source_evidence_hashes(transcript),
        "public source hashes",
    )
    return {
        "accumulator_schema": ACCUMULATOR_SCHEMA,
        "accumulator_kind": ACCUMULATOR_KIND,
        "claim_boundary": CLAIM_BOUNDARY,
        "issue": ISSUE,
        "width": WIDTH,
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "public_inputs": public_inputs,
        "two_slice_target_manifest": copy.deepcopy(source["two_slice_target_manifest"]),
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
        "required_public_inputs": [
            "two_slice_target_commitment",
            "selected_slice_statement_commitments",
            "selected_source_evidence_hashes",
        ],
        "two_slice_target_commitment": public_inputs["two_slice_target_commitment"],
        "selected_slice_statement_commitments": copy.deepcopy(public_inputs["selected_slice_statement_commitments"]),
        "selected_source_evidence_hashes": copy.deepcopy(public_inputs["selected_source_evidence_hashes"]),
        "verifier_steps": [
            "validate checked two-slice target evidence",
            "validate selected source slice evidence with slice-local validators",
            "compare selected statement commitments and source hashes",
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
    source = load_checked_two_slice_target()
    artifact = accumulator_artifact(source)
    handle = verifier_handle(artifact)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "accumulator_result": ACCUMULATOR_RESULT,
        "recursive_or_pcd_result": RECURSIVE_OR_PCD_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_two_slice_target": two_slice_source_descriptor(source),
        "accumulator_artifact": artifact,
        "verifier_handle": handle,
        "recursive_or_pcd_status": recursive_or_pcd_status(),
        "summary": {
            "accumulator_status": ACCUMULATOR_RESULT,
            "recursive_or_pcd_status": RECURSIVE_OR_PCD_RESULT,
            "claim_boundary": CLAIM_BOUNDARY,
            "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
            "selected_checked_rows": EXPECTED_SELECTED_ROWS,
            "two_slice_target_commitment": source["two_slice_target_commitment"],
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
    descriptor = require_object(payload.get("source_two_slice_target"), "source two-slice target")
    expect_equal(descriptor.get("path"), relative_path(TWO_SLICE_EVIDENCE), "source two-slice path")
    source = load_checked_two_slice_target(ROOT / descriptor["path"])
    expect_equal(descriptor.get("file_sha256"), file_sha256(TWO_SLICE_EVIDENCE), "source two-slice file hash")
    expect_equal(descriptor.get("payload_sha256"), sha256_hex_json(source), "source two-slice payload hash")
    for field in ("schema", "decision", "result", "target_result", "outer_proof_object_result", "two_slice_target_commitment"):
        expect_equal(descriptor.get(field), source[field], f"source two-slice {field}")
    return source


def verify_accumulator_artifact(artifact: Any, source: dict[str, Any] | None = None) -> None:
    artifact = require_object(artifact, "accumulator artifact")
    expect_equal(artifact.get("schema"), ACCUMULATOR_SCHEMA, "accumulator schema")
    expect_equal(artifact.get("accumulator_kind"), ACCUMULATOR_KIND, "accumulator kind")
    expect_equal(artifact.get("claim_boundary"), CLAIM_BOUNDARY, "accumulator claim boundary")
    expect_equal(artifact.get("issue"), ISSUE, "accumulator issue")
    source = copy.deepcopy(source) if source is not None else load_checked_two_slice_target()
    expected_artifact = accumulator_artifact(source)
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
    expect_equal(status.get("result"), RECURSIVE_OR_PCD_RESULT, "recursive or PCD result")
    if status.get("recursive_outer_proof_claimed") is not False:
        raise D128TwoSliceAccumulatorBackendError("recursive outer proof claimed without backend")
    if status.get("pcd_outer_proof_claimed") is not False:
        raise D128TwoSliceAccumulatorBackendError("PCD outer proof claimed without backend")
    expect_equal(status.get("outer_proof_artifacts"), [], "recursive outer proof artifacts")
    metrics = require_object(status.get("proof_metrics"), "recursive proof metrics")
    for field in (
        "recursive_proof_size_bytes",
        "recursive_verifier_time_ms",
        "recursive_proof_generation_time_ms",
    ):
        if metrics.get(field) is not None:
            raise D128TwoSliceAccumulatorBackendError("recursive proof metric supplied before proof backend exists")
    expect_equal(status.get("first_blocker"), RECURSIVE_BLOCKER, "recursive blocker")


def _expected_summary(source: dict[str, Any], artifact: dict[str, Any], handle: dict[str, Any]) -> dict[str, Any]:
    return {
        "accumulator_status": ACCUMULATOR_RESULT,
        "recursive_or_pcd_status": RECURSIVE_OR_PCD_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "two_slice_target_commitment": source["two_slice_target_commitment"],
        "accumulator_commitment": artifact["accumulator_commitment"],
        "verifier_handle_commitment": handle["verifier_handle_commitment"],
        "go_criterion": GO_CRITERION,
        "recursive_blocker": RECURSIVE_BLOCKER,
    }


def _validate_common_payload(payload: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = require_object(payload, "two-slice accumulator backend payload")
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
        raise D128TwoSliceAccumulatorBackendError("draft payload must not include mutation metadata")
    expect_equal(payload.get("summary"), expected_summary, "summary")


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    has_cases = "cases" in payload
    has_case_count = "case_count" in payload
    has_all_mutations_rejected = "all_mutations_rejected" in payload
    has_mutation_inventory = "mutation_inventory" in payload
    if not (has_cases or has_case_count or has_all_mutations_rejected or has_mutation_inventory):
        raise D128TwoSliceAccumulatorBackendError("mutation metadata missing")
    if not (has_mutation_inventory and has_cases and has_case_count and has_all_mutations_rejected):
        raise D128TwoSliceAccumulatorBackendError(
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
                raise D128TwoSliceAccumulatorBackendError(f"mutation case {index} missing {column}")
        pair = (require_str(case["mutation"], f"mutation case {index} mutation"), require_str(case["surface"], f"mutation case {index} surface"))
        if pair in seen:
            raise D128TwoSliceAccumulatorBackendError(f"duplicate mutation case {index}")
        seen.add(pair)
        pairs.append(pair)
        expect_equal(case["baseline_result"], RESULT, f"mutation case {index} baseline result")
        require_bool(case["mutated_accepted"], f"mutation case {index} mutated_accepted")
        require_bool(case["rejected"], f"mutation case {index} rejected")
        if case["rejected"] == case["mutated_accepted"]:
            raise D128TwoSliceAccumulatorBackendError(f"mutation case {index} rejected/accepted mismatch")
        require_str(case["rejection_layer"], f"mutation case {index} rejection layer")
        if not isinstance(case["error"], str):
            raise D128TwoSliceAccumulatorBackendError(f"mutation case {index} error must be a string")
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
            raise D128TwoSliceAccumulatorBackendError(f"missing recomputed mutation case {index}")
        for column in TSV_COLUMNS:
            expect_equal(case[column], expected[column], f"mutation case {index} {column}")
    return len(cases), rejected


def _draft_payload_for_case_replay(payload: dict[str, Any]) -> dict[str, Any]:
    draft = copy.deepcopy(payload)
    for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected"):
        draft.pop(field, None)
    summary = require_object(draft.get("summary"), "summary")
    summary.pop("mutation_cases", None)
    summary.pop("mutations_rejected", None)
    return draft


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "two-slice accumulator backend payload")
    _source, _artifact, _handle, expected_summary = _validate_common_payload(payload)
    case_count, rejected = _validate_case_metadata(payload)
    if rejected != case_count:
        raise D128TwoSliceAccumulatorBackendError("not all accumulator backend mutations rejected")
    expected_summary["mutation_cases"] = case_count
    expected_summary["mutations_rejected"] = rejected
    expect_equal(payload.get("summary"), expected_summary, "summary")


def classify_error(error: Exception) -> str:
    text = str(error).lower()
    if "source two-slice" in text:
        return "source_two_slice_target"
    if "accumulator artifact" in text or "accumulator" in text:
        return "accumulator_artifact"
    if "public" in text:
        return "public_inputs"
    if "selected slice" in text or "transcript" in text or "row" in text:
        return "selected_slice_transcript"
    if "source" in text or "payload" in text or "file" in text or "statement" in text:
        return "selected_source_evidence"
    if "verifier handle" in text:
        return "verifier_handle"
    if "recursive" in text or "pcd" in text or "metric" in text or "blocker" in text:
        return "recursive_or_pcd_status"
    return "parser_or_schema"


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []

    def add(name: str, surface: str, mutator: Callable[[dict[str, Any]], None]) -> None:
        mutated = copy.deepcopy(baseline)
        mutator(mutated)
        cases.append((name, surface, mutated))

    add("source_two_slice_file_hash_drift", "source_two_slice_target", lambda p: p["source_two_slice_target"].__setitem__("file_sha256", "00" * 32))
    add("source_two_slice_payload_hash_drift", "source_two_slice_target", lambda p: p["source_two_slice_target"].__setitem__("payload_sha256", "11" * 32))
    add("source_two_slice_result_drift", "source_two_slice_target", lambda p: p["source_two_slice_target"].__setitem__("result", "GO"))
    add("source_two_slice_target_commitment_drift", "source_two_slice_target", lambda p: p["source_two_slice_target"].__setitem__("two_slice_target_commitment", "blake2b-256:" + "22" * 32))
    add("accumulator_commitment_drift", "accumulator_artifact", lambda p: p["accumulator_artifact"].__setitem__("accumulator_commitment", "blake2b-256:" + "33" * 32))
    add("accumulator_claim_boundary_changed_to_recursive", "accumulator_artifact", lambda p: p["accumulator_artifact"].__setitem__("claim_boundary", "RECURSIVE_OUTER_PROOF"))
    add("source_full_aggregation_target_commitment_drift", "accumulator_artifact", lambda p: p["accumulator_artifact"]["preimage"]["two_slice_target_manifest"].__setitem__("source_full_aggregation_target_commitment", "blake2b-256:" + "44" * 32))
    add("public_input_target_commitment_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"].__setitem__("two_slice_target_commitment", "blake2b-256:" + "55" * 32))
    add("public_input_selected_statement_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"]["selected_slice_statement_commitments"][0].__setitem__("statement_commitment", "blake2b-256:" + "66" * 32))
    add("public_input_selected_source_hash_drift", "public_inputs", lambda p: p["accumulator_artifact"]["preimage"]["public_inputs"]["selected_source_evidence_hashes"][0].__setitem__("source_payload_sha256", "77" * 32))
    add("selected_slice_removed", "selected_slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"].pop())
    add("selected_slice_duplicated", "selected_slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"].append(copy.deepcopy(p["accumulator_artifact"]["preimage"]["verifier_transcript"][0])))
    add("selected_slice_reordered", "selected_slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"].reverse())
    add("selected_slice_row_count_drift", "selected_slice_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("row_count", 127))
    add("source_file_hash_drift", "selected_source_evidence", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("source_file_sha256", "88" * 32))
    add("source_payload_hash_drift", "selected_source_evidence", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("source_payload_sha256", "99" * 32))
    add("source_statement_commitment_drift", "selected_source_evidence", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("statement_commitment", "blake2b-256:" + "aa" * 32))
    add("source_public_instance_commitment_drift", "selected_source_evidence", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("public_instance_commitment", "blake2b-256:" + "bb" * 32))
    add("source_target_commitment_drift", "selected_source_evidence", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][1]["target_commitments"].__setitem__("projection_input_row_commitment", "blake2b-256:" + "cc" * 32))
    add("verifier_domain_drift", "verifier_transcript", lambda p: p["accumulator_artifact"]["preimage"]["two_slice_target_manifest"].__setitem__("verifier_domain", "ptvm:zkai:d128:tampered-verifier-domain:v0"))
    add("validator_name_drift", "verifier_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("validator", "wrong_validator"))
    add("validator_result_false", "verifier_transcript", lambda p: p["accumulator_artifact"]["preimage"]["verifier_transcript"][0].__setitem__("verified", False))
    add("verifier_handle_commitment_drift", "verifier_handle", lambda p: p["verifier_handle"].__setitem__("verifier_handle_commitment", "blake2b-256:" + "dd" * 32))
    add("verifier_handle_claim_boundary_changed_to_recursive", "verifier_handle", lambda p: p["verifier_handle"].__setitem__("claim_boundary", "RECURSIVE_OUTER_PROOF"))
    add("verifier_handle_target_commitment_drift", "verifier_handle", lambda p: p["verifier_handle"]["preimage"].__setitem__("two_slice_target_commitment", "blake2b-256:" + "ee" * 32))
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
        except D128TwoSliceAccumulatorBackendError as err:
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
        raise D128TwoSliceAccumulatorBackendError(f"output path must be repo-relative: {path}")
    pure = pathlib.PurePosixPath(path.as_posix())
    if path.as_posix() != pure.as_posix() or any(part in ("", ".", "..") for part in pure.parts):
        raise D128TwoSliceAccumulatorBackendError(f"output path must be repo-relative without traversal: {path}")
    candidate = ROOT.joinpath(*pure.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128TwoSliceAccumulatorBackendError(f"output path escapes repository: {path}") from err
    return candidate


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    outputs: list[tuple[pathlib.Path, bytes]] = []
    if json_path is not None:
        outputs.append((_safe_output_path(json_path), json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"))
    if tsv_path is not None:
        outputs.append((_safe_output_path(tsv_path), to_tsv(payload).encode("utf-8")))
    for path, data in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as handle:
            tmp = pathlib.Path(handle.name)
            handle.write(data)
        tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the d128 two-slice non-recursive accumulator backend evidence. "
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
