#!/usr/bin/env python3
"""Classify the attention-derived d128 statement-chain outer-proof route."""

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
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
COMPRESSION_SCRIPT = ROOT / "scripts" / "zkai_attention_derived_d128_statement_chain_compression_gate.py"
COMPRESSION_EVIDENCE = EVIDENCE_DIR / "zkai-attention-derived-d128-statement-chain-compression-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-outer-proof-route-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-outer-proof-route-2026-05.tsv"

SCHEMA = "zkai-attention-derived-d128-outer-proof-route-gate-v1"
DECISION = "NO_GO_ATTENTION_DERIVED_D128_OUTER_PROOF_OBJECT_MISSING"
RESULT = "BOUNDED_NO_GO"
INPUT_CONTRACT_RESULT = "GO_ATTENTION_DERIVED_D128_OUTER_PROOF_INPUT_CONTRACT"
OUTER_PROOF_RESULT = "NO_GO_EXECUTABLE_ATTENTION_DERIVED_D128_OUTER_PROOF_BACKEND_MISSING"
INPUT_CONTRACT_SCHEMA = "zkai-attention-derived-d128-outer-proof-input-contract-v1"
INPUT_CONTRACT_KIND = "attention-derived-d128-six-slice-outer-proof-input-contract"
INPUT_CONTRACT_DOMAIN = "ptvm:zkai:attention-derived-d128:outer-proof-input-contract:v1"
EXPECTED_COMPRESSION_PAYLOAD = "sha256:d15c409b11bd5d1f7ffd66caeabd94daf60ca7feca7dc325987aa26f07c2b423"
EXPECTED_BLOCK_STATEMENT = "blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5"
EXPECTED_SOURCE_BYTES = 14_624
EXPECTED_COMPRESSED_BYTES = 2_559
EXPECTED_BYTE_SAVINGS = 12_065
EXPECTED_RATIO = 0.174986
EXPECTED_ROWS = 199_553
EXPECTED_SLICES = 6
EXPECTED_EDGES = 11
EXPECTED_COMPRESSION_MUTATIONS = 22

FIRST_BLOCKER = (
    "no executable outer proof backend currently proves the six attention-derived d128 slice-chain verifier checks, "
    "binds the compressed statement-chain input contract as public input, and emits one verifier-facing proof object"
)

MISSING_BACKEND_FEATURES = [
    "nested verifier program/AIR/circuit for the six attention-derived d128 slice-chain checks",
    "outer proof object or PCD accumulator over the compressed statement-chain input contract",
    "outer verifier handle that accepts the input contract commitment as a public input",
    "public-input binding for block statement, compressed artifact, verifier handle, row counts, and source file hash",
    "mutation tests against relabeling the compressed transcript as proof-size or recursion evidence",
]

NON_CLAIMS = [
    "not one composed d128 transformer-block proof",
    "not recursive aggregation",
    "not proof-carrying data",
    "not proof-size evidence",
    "not verifier-time evidence",
    "not proof-generation-time evidence",
    "not matched NANOZK benchmark evidence",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_outer_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-outer-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-outer-proof-route-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_outer_proof_route_gate.py scripts/tests/test_zkai_attention_derived_d128_outer_proof_route_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_outer_proof_route_gate",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

EXPECTED_MUTATIONS = (
    "schema_drift",
    "decision_changed_to_go",
    "result_changed_to_go",
    "compression_source_path_drift",
    "compression_file_sha256_drift",
    "compression_payload_commitment_drift",
    "input_contract_schema_drift",
    "input_contract_block_statement_drift",
    "input_contract_compressed_artifact_drift",
    "input_contract_verifier_handle_drift",
    "input_contract_source_bytes_drift",
    "input_contract_compressed_bytes_drift",
    "input_contract_byte_savings_drift",
    "input_contract_ratio_drift",
    "input_contract_rows_drift",
    "input_contract_required_public_input_removed",
    "input_contract_required_public_input_drift",
    "outer_proof_result_changed_to_go",
    "outer_proof_artifact_smuggled",
    "outer_verifier_handle_claimed",
    "proof_metrics_smuggled",
    "blocked_before_metrics_disabled",
    "first_blocker_removed",
    "missing_backend_feature_removed",
    "candidate_inventory_required_relabel",
    "candidate_inventory_path_drift",
    "non_claims_removed",
    "validation_command_drift",
)

CANDIDATE_SPECS = (
    {
        "name": "compressed_statement_chain_input_contract",
        "kind": "checked_input_contract",
        "path": "docs/engineering/evidence/zkai-attention-derived-d128-statement-chain-compression-2026-05.json",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "INPUT_CONTRACT_ONLY_NOT_OUTER_PROOF",
        "reason": "defines the compressed public-input contract but does not prove the six verifier checks in one proof object",
    },
    {
        "name": "two_slice_outer_proof_spike_reference",
        "kind": "prior_no_go_reference",
        "path": "docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.json",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "REFERENCE_ONLY_NOT_ATTENTION_DERIVED_SIX_SLICE_PROOF",
        "reason": "two-slice d128 no-go evidence is useful prior art but cannot be relabeled as the attention-derived six-slice proof object",
    },
    {
        "name": "required_attention_derived_outer_module",
        "kind": "required_outer_backend_module",
        "path": "src/stwo_backend/attention_derived_d128_outer_proof.rs",
        "expected_exists": False,
        "required_for_go": True,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "reason": "no current Stwo-native outer proof module exists for the attention-derived d128 statement-chain verifier checks",
    },
    {
        "name": "required_attention_derived_outer_proof_artifact",
        "kind": "required_outer_proof_artifact",
        "path": "docs/engineering/evidence/zkai-attention-derived-d128-outer-proof-object-2026-05.json",
        "expected_exists": False,
        "required_for_go": True,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "reason": "no checked attention-derived d128 outer proof artifact exists",
    },
    {
        "name": "required_attention_derived_outer_verifier_handle",
        "kind": "required_outer_verifier_handle",
        "path": "docs/engineering/evidence/zkai-attention-derived-d128-outer-proof-verifier-2026-05.json",
        "expected_exists": False,
        "required_for_go": True,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "reason": "no local verifier handle exists for an attention-derived d128 outer proof object",
    },
    {
        "name": "required_attention_derived_outer_mutation_tests",
        "kind": "required_outer_proof_test_surface",
        "path": "scripts/tests/test_zkai_attention_derived_d128_outer_proof_object_backend.py",
        "expected_exists": False,
        "required_for_go": True,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "reason": "future outer proof public inputs must reject relabeling before metrics are meaningful",
    },
)


class AttentionDerivedD128OuterProofRouteError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionDerivedD128OuterProofRouteError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


COMPRESSION = _load_module(COMPRESSION_SCRIPT, "zkai_attention_derived_compression_for_outer_route")


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AttentionDerivedD128OuterProofRouteError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise AttentionDerivedD128OuterProofRouteError(f"invalid JSON value: {err}") from err


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return "blake2b-256:" + digest.hexdigest()


def _dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128OuterProofRouteError(f"{field} must be object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128OuterProofRouteError(f"{field} must be list")
    return value


def _str(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise AttentionDerivedD128OuterProofRouteError(f"{field} must be string")
    return value


def _int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128OuterProofRouteError(f"{field} must be integer")
    return value


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128OuterProofRouteError(f"{field} must be boolean")
    return value


def _load_json(path: pathlib.Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = COMPRESSION.read_source_bytes(path, label)
        payload = COMPRESSION.parse_json_bytes(raw, label)
        return payload, raw
    except Exception as err:
        if isinstance(err, AttentionDerivedD128OuterProofRouteError):
            raise
        raise AttentionDerivedD128OuterProofRouteError(f"failed to load {label}: {err}") from err


def load_compression_payload() -> tuple[dict[str, Any], bytes]:
    payload, raw = _load_json(COMPRESSION_EVIDENCE, "compression evidence")
    try:
        COMPRESSION.validate_payload(payload)
    except Exception as err:
        raise AttentionDerivedD128OuterProofRouteError(f"compression evidence rejected: {err}") from err
    if _str(payload.get("payload_commitment"), "compression.payload_commitment") != EXPECTED_COMPRESSION_PAYLOAD:
        raise AttentionDerivedD128OuterProofRouteError("compression payload commitment drift")
    return payload, raw


def source_descriptor(path: pathlib.Path, kind: str, raw: bytes, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": str(path.relative_to(ROOT)),
        "file_sha256": sha256_bytes(raw),
        "payload_commitment": _str(payload.get("payload_commitment"), f"{kind}.payload_commitment"),
    }


def build_input_contract(compression: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(compression.get("summary"), "compression.summary")
    metrics = _dict(compression.get("compression_metrics"), "compression.metrics")
    artifact = _dict(compression.get("compressed_artifact"), "compression.compressed_artifact")
    handle = _dict(compression.get("verifier_handle"), "compression.verifier_handle")
    required = _dict(
        _dict(artifact.get("preimage"), "compression.compressed_artifact.preimage").get("required_public_inputs"),
        "compression.required_public_inputs",
    )
    preimage = {
        "schema": INPUT_CONTRACT_SCHEMA,
        "contract_kind": INPUT_CONTRACT_KIND,
        "input_contract_result": INPUT_CONTRACT_RESULT,
        "block_statement_commitment": _str(summary.get("block_statement_commitment"), "summary.block_statement"),
        "compression_payload_commitment": _str(compression.get("payload_commitment"), "compression.payload_commitment"),
        "compressed_artifact_commitment": _str(
            artifact.get("compressed_artifact_commitment"), "compressed_artifact.commitment"
        ),
        "verifier_handle_commitment": _str(handle.get("verifier_handle_commitment"), "verifier_handle.commitment"),
        "source_chain_artifact_bytes": _int(metrics.get("source_chain_artifact_bytes"), "metrics.source_bytes"),
        "compressed_artifact_bytes": _int(metrics.get("compressed_artifact_bytes"), "metrics.compressed_bytes"),
        "byte_savings": _int(metrics.get("byte_savings"), "metrics.byte_savings"),
        "compressed_to_source_ratio": metrics.get("compressed_to_source_ratio"),
        "source_relation_rows": _int(summary.get("source_relation_rows"), "summary.source_relation_rows"),
        "slice_count": _int(required.get("slice_count"), "required.slice_count"),
        "edge_count": _int(required.get("edge_count"), "required.edge_count"),
        "required_public_inputs": copy.deepcopy(required),
    }
    contract = {
        "schema": INPUT_CONTRACT_SCHEMA,
        "contract_kind": INPUT_CONTRACT_KIND,
        "preimage": preimage,
    }
    contract["input_contract_commitment"] = blake2b_commitment(preimage, INPUT_CONTRACT_DOMAIN)
    return contract


def validate_input_contract(contract: dict[str, Any], expected: dict[str, Any]) -> None:
    if _str(contract.get("schema"), "input_contract.schema") != INPUT_CONTRACT_SCHEMA:
        raise AttentionDerivedD128OuterProofRouteError("input contract schema drift")
    if _str(contract.get("contract_kind"), "input_contract.contract_kind") != INPUT_CONTRACT_KIND:
        raise AttentionDerivedD128OuterProofRouteError("input contract kind drift")
    preimage = _dict(contract.get("preimage"), "input_contract.preimage")
    if _str(contract.get("input_contract_commitment"), "input_contract.commitment") != blake2b_commitment(
        preimage, INPUT_CONTRACT_DOMAIN
    ):
        raise AttentionDerivedD128OuterProofRouteError("input contract commitment drift")
    if contract != expected:
        raise AttentionDerivedD128OuterProofRouteError("input contract drift")


def build_candidate_inventory() -> list[dict[str, Any]]:
    inventory = []
    for spec in CANDIDATE_SPECS:
        path = ROOT / spec["path"]
        exists = path.exists()
        entry = dict(spec)
        entry["exists"] = exists
        if exists and path.is_file():
            raw = COMPRESSION.read_source_bytes(path, f"candidate {spec['name']}")
            entry["file_sha256"] = sha256_bytes(raw)
        else:
            entry["file_sha256"] = None
        if exists != spec["expected_exists"]:
            raise AttentionDerivedD128OuterProofRouteError(f"candidate existence drift: {spec['name']}")
        inventory.append(entry)
    return inventory


def build_core_payload() -> dict[str, Any]:
    compression, raw = load_compression_payload()
    source = source_descriptor(COMPRESSION_EVIDENCE, "compressed_statement_chain_evidence", raw, compression)
    input_contract = build_input_contract(compression)
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "source": source,
        "input_contract": input_contract,
        "candidate_inventory": build_candidate_inventory(),
        "outer_proof_attempt": {
            "result": OUTER_PROOF_RESULT,
            "blocked_before_metrics": True,
            "first_blocker": FIRST_BLOCKER,
            "missing_backend_features": list(MISSING_BACKEND_FEATURES),
            "outer_proof_artifacts": [],
            "outer_verifier_handles": [],
            "proof_metrics": None,
        },
        "summary": {
            "input_contract_status": INPUT_CONTRACT_RESULT,
            "outer_proof_status": OUTER_PROOF_RESULT,
            "block_statement_commitment": EXPECTED_BLOCK_STATEMENT,
            "source_chain_artifact_bytes": EXPECTED_SOURCE_BYTES,
            "compressed_artifact_bytes": EXPECTED_COMPRESSED_BYTES,
            "byte_savings": EXPECTED_BYTE_SAVINGS,
            "compressed_to_source_ratio": EXPECTED_RATIO,
            "source_relation_rows": EXPECTED_ROWS,
            "slice_count": EXPECTED_SLICES,
            "edge_count": EXPECTED_EDGES,
            "first_blocker": FIRST_BLOCKER,
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }


def build_payload() -> dict[str, Any]:
    payload = finalize_payload(build_core_payload())
    validate_payload(payload)
    return payload


def finalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(payload)
    cases = run_mutations(payload)
    payload["mutation_inventory"] = list(EXPECTED_MUTATIONS)
    payload["cases"] = cases
    payload["case_count"] = len(cases)
    payload["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    payload["payload_commitment"] = payload_commitment(payload)
    return payload


def expected_payload_parts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compression, raw = load_compression_payload()
    source = source_descriptor(COMPRESSION_EVIDENCE, "compressed_statement_chain_evidence", raw, compression)
    return source, build_input_contract(compression), {
        "candidate_inventory": build_candidate_inventory(),
    }


def validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise AttentionDerivedD128OuterProofRouteError("payload must be object")
    if _str(payload.get("schema"), "schema") != SCHEMA:
        raise AttentionDerivedD128OuterProofRouteError("schema drift")
    if _str(payload.get("decision"), "decision") != DECISION:
        raise AttentionDerivedD128OuterProofRouteError("decision drift")
    if _str(payload.get("result"), "result") != RESULT:
        raise AttentionDerivedD128OuterProofRouteError("result drift")
    expected_source, expected_contract, expected_inventory = expected_payload_parts()
    if _dict(payload.get("source"), "source") != expected_source:
        raise AttentionDerivedD128OuterProofRouteError("source compression evidence drift")
    validate_input_contract(_dict(payload.get("input_contract"), "input_contract"), expected_contract)
    if _list(payload.get("candidate_inventory"), "candidate_inventory") != expected_inventory["candidate_inventory"]:
        raise AttentionDerivedD128OuterProofRouteError("candidate inventory drift")
    attempt = _dict(payload.get("outer_proof_attempt"), "outer_proof_attempt")
    if _str(attempt.get("result"), "outer_proof_attempt.result") != OUTER_PROOF_RESULT:
        raise AttentionDerivedD128OuterProofRouteError("outer proof result drift")
    if not _bool(attempt.get("blocked_before_metrics"), "outer_proof_attempt.blocked_before_metrics"):
        raise AttentionDerivedD128OuterProofRouteError("blocked-before-metrics drift")
    if _str(attempt.get("first_blocker"), "outer_proof_attempt.first_blocker") != FIRST_BLOCKER:
        raise AttentionDerivedD128OuterProofRouteError("first blocker drift")
    if attempt.get("missing_backend_features") != MISSING_BACKEND_FEATURES:
        raise AttentionDerivedD128OuterProofRouteError("missing backend features drift")
    if attempt.get("outer_proof_artifacts") != []:
        raise AttentionDerivedD128OuterProofRouteError("outer proof artifact smuggled")
    if attempt.get("outer_verifier_handles") != []:
        raise AttentionDerivedD128OuterProofRouteError("outer verifier handle smuggled")
    if attempt.get("proof_metrics") is not None:
        raise AttentionDerivedD128OuterProofRouteError("proof metric smuggled before proof")
    summary = _dict(payload.get("summary"), "summary")
    expected_summary = {
        "input_contract_status": INPUT_CONTRACT_RESULT,
        "outer_proof_status": OUTER_PROOF_RESULT,
        "block_statement_commitment": EXPECTED_BLOCK_STATEMENT,
        "source_chain_artifact_bytes": EXPECTED_SOURCE_BYTES,
        "compressed_artifact_bytes": EXPECTED_COMPRESSED_BYTES,
        "byte_savings": EXPECTED_BYTE_SAVINGS,
        "compressed_to_source_ratio": EXPECTED_RATIO,
        "source_relation_rows": EXPECTED_ROWS,
        "slice_count": EXPECTED_SLICES,
        "edge_count": EXPECTED_EDGES,
        "first_blocker": FIRST_BLOCKER,
    }
    if summary != expected_summary:
        raise AttentionDerivedD128OuterProofRouteError("summary drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128OuterProofRouteError("non_claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128OuterProofRouteError("validation command drift")
    if ("cases" in payload) != ("case_count" in payload):
        raise AttentionDerivedD128OuterProofRouteError("mutation finalization drift")
    if "cases" in payload:
        inventory = _list(payload.get("mutation_inventory"), "mutation_inventory")
        cases = _list(payload.get("cases"), "cases")
        if tuple(inventory) != EXPECTED_MUTATIONS:
            raise AttentionDerivedD128OuterProofRouteError("mutation inventory drift")
        if _int(payload.get("case_count"), "case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128OuterProofRouteError("mutation count drift")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128OuterProofRouteError("mutation cases drift")
        if not _bool(payload.get("all_mutations_rejected"), "all_mutations_rejected"):
            raise AttentionDerivedD128OuterProofRouteError("mutation rejection drift")
        for index, expected_name in enumerate(EXPECTED_MUTATIONS):
            case = _dict(cases[index], f"case {index}")
            if _str(case.get("name"), "case.name") != expected_name:
                raise AttentionDerivedD128OuterProofRouteError("mutation case name drift")
            if _bool(case.get("accepted"), "case.accepted"):
                raise AttentionDerivedD128OuterProofRouteError("mutation accepted unexpectedly")
            if not _bool(case.get("rejected"), "case.rejected"):
                raise AttentionDerivedD128OuterProofRouteError("mutation rejection flag drift")
            _str(case.get("error"), "case.error")
    if _str(payload.get("payload_commitment"), "payload_commitment") != payload_commitment(payload):
        raise AttentionDerivedD128OuterProofRouteError("payload commitment drift")


MutationFn = Callable[[dict[str, Any]], None]


def _recommit_input_contract(payload: dict[str, Any]) -> None:
    contract = payload["input_contract"]
    contract["input_contract_commitment"] = blake2b_commitment(contract["preimage"], INPUT_CONTRACT_DOMAIN)


def _mutate_contract(payload: dict[str, Any], key: str, value: Any) -> None:
    payload["input_contract"]["preimage"][key] = value
    _recommit_input_contract(payload)


def _mutate_required(payload: dict[str, Any], key: str, value: Any) -> None:
    payload["input_contract"]["preimage"]["required_public_inputs"][key] = value
    _recommit_input_contract(payload)


def run_mutations(base_payload: dict[str, Any]) -> list[dict[str, Any]]:
    mutations: dict[str, MutationFn] = {
        "schema_drift": lambda p: p.__setitem__("schema", "different"),
        "decision_changed_to_go": lambda p: p.__setitem__("decision", "GO_ATTENTION_DERIVED_D128_OUTER_PROOF"),
        "result_changed_to_go": lambda p: p.__setitem__("result", "GO"),
        "compression_source_path_drift": lambda p: p["source"].__setitem__("path", "docs/engineering/evidence/other.json"),
        "compression_file_sha256_drift": lambda p: p["source"].__setitem__("file_sha256", "sha256:" + "00" * 32),
        "compression_payload_commitment_drift": lambda p: p["source"].__setitem__(
            "payload_commitment", "sha256:" + "11" * 32
        ),
        "input_contract_schema_drift": lambda p: (
            p["input_contract"].__setitem__("schema", "different"),
            p["input_contract"]["preimage"].__setitem__("schema", "different"),
            _recommit_input_contract(p),
        ),
        "input_contract_block_statement_drift": lambda p: _mutate_contract(
            p, "block_statement_commitment", "blake2b-256:" + "22" * 32
        ),
        "input_contract_compressed_artifact_drift": lambda p: _mutate_contract(
            p, "compressed_artifact_commitment", "blake2b-256:" + "33" * 32
        ),
        "input_contract_verifier_handle_drift": lambda p: _mutate_contract(
            p, "verifier_handle_commitment", "blake2b-256:" + "44" * 32
        ),
        "input_contract_source_bytes_drift": lambda p: _mutate_contract(p, "source_chain_artifact_bytes", 1),
        "input_contract_compressed_bytes_drift": lambda p: _mutate_contract(p, "compressed_artifact_bytes", 1),
        "input_contract_byte_savings_drift": lambda p: _mutate_contract(p, "byte_savings", 1),
        "input_contract_ratio_drift": lambda p: _mutate_contract(p, "compressed_to_source_ratio", 1.0),
        "input_contract_rows_drift": lambda p: _mutate_contract(p, "source_relation_rows", 1),
        "input_contract_required_public_input_removed": lambda p: (
            p["input_contract"]["preimage"]["required_public_inputs"].pop("derived_output_activation_commitment"),
            _recommit_input_contract(p),
        ),
        "input_contract_required_public_input_drift": lambda p: _mutate_required(
            p, "derived_hidden_activation_commitment", "blake2b-256:" + "55" * 32
        ),
        "outer_proof_result_changed_to_go": lambda p: p["outer_proof_attempt"].__setitem__("result", "GO"),
        "outer_proof_artifact_smuggled": lambda p: p["outer_proof_attempt"].__setitem__(
            "outer_proof_artifacts", ["docs/engineering/evidence/fake.json"]
        ),
        "outer_verifier_handle_claimed": lambda p: p["outer_proof_attempt"].__setitem__(
            "outer_verifier_handles", ["docs/engineering/evidence/fake-verifier.json"]
        ),
        "proof_metrics_smuggled": lambda p: p["outer_proof_attempt"].__setitem__("proof_metrics", {"proof_bytes": 1}),
        "blocked_before_metrics_disabled": lambda p: p["outer_proof_attempt"].__setitem__(
            "blocked_before_metrics", False
        ),
        "first_blocker_removed": lambda p: p["outer_proof_attempt"].__setitem__("first_blocker", ""),
        "missing_backend_feature_removed": lambda p: p["outer_proof_attempt"].__setitem__(
            "missing_backend_features", MISSING_BACKEND_FEATURES[:-1]
        ),
        "candidate_inventory_required_relabel": lambda p: p["candidate_inventory"][2].__setitem__(
            "required_for_go", False
        ),
        "candidate_inventory_path_drift": lambda p: p["candidate_inventory"][3].__setitem__("path", "other.json"),
        "non_claims_removed": lambda p: p.__setitem__("non_claims", []),
        "validation_command_drift": lambda p: p.__setitem__("validation_commands", []),
    }
    cases = []
    for name in EXPECTED_MUTATIONS:
        mutated = copy.deepcopy(base_payload)
        accepted = False
        error = ""
        try:
            mutations[name](mutated)
            mutated["payload_commitment"] = payload_commitment(mutated)
            validate_payload(mutated)
            accepted = True
        except AttentionDerivedD128OuterProofRouteError as err:
            error = str(err)
        cases.append({"name": name, "accepted": accepted, "rejected": not accepted, "error": error})
    return cases


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(
        [
            "decision",
            "result",
            "input_contract_commitment",
            "outer_proof_status",
            "source_chain_artifact_bytes",
            "compressed_artifact_bytes",
            "byte_savings",
            "source_relation_rows",
            "mutations_rejected",
        ]
    )
    writer.writerow(
        [
            payload["decision"],
            payload["result"],
            payload["input_contract"]["input_contract_commitment"],
            payload["summary"]["outer_proof_status"],
            payload["summary"]["source_chain_artifact_bytes"],
            payload["summary"]["compressed_artifact_bytes"],
            payload["summary"]["byte_savings"],
            payload["summary"]["source_relation_rows"],
            payload["case_count"],
        ]
    )
    return out.getvalue()


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    if json_path is None and tsv_path is None:
        raise AttentionDerivedD128OuterProofRouteError("at least one output path is required")
    if json_path is not None:
        try:
            COMPRESSION.atomic_write_text(json_path, pretty_json(payload) + "\n", suffix=".json")
        except Exception as err:
            raise AttentionDerivedD128OuterProofRouteError(f"failed to write JSON output: {err}") from err
    if tsv_path is not None:
        try:
            COMPRESSION.atomic_write_text(tsv_path, to_tsv(payload), suffix=".tsv")
        except Exception as err:
            raise AttentionDerivedD128OuterProofRouteError(f"failed to write TSV output: {err}") from err


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        payload = build_payload()
        if args.write_json or args.write_tsv:
            write_outputs(payload, args.write_json, args.write_tsv)
            print(
                json.dumps(
                    {
                        "decision": payload["decision"],
                        "result": payload["result"],
                        "input_contract_commitment": payload["input_contract"]["input_contract_commitment"],
                        "outer_proof_status": payload["summary"]["outer_proof_status"],
                        "source_chain_artifact_bytes": payload["summary"]["source_chain_artifact_bytes"],
                        "compressed_artifact_bytes": payload["summary"]["compressed_artifact_bytes"],
                        "byte_savings": payload["summary"]["byte_savings"],
                        "source_relation_rows": payload["summary"]["source_relation_rows"],
                        "mutations_rejected": payload["case_count"],
                    },
                    sort_keys=True,
                )
            )
        else:
            print(pretty_json(payload))
    except AttentionDerivedD128OuterProofRouteError as err:
        print(f"attention-derived d128 outer-proof route gate failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
