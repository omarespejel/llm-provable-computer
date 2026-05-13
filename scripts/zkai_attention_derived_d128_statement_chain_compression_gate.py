#!/usr/bin/env python3
"""Compress the attention-derived d128 statement-chain transcript.

This gate consumes the checked attention-derived d128 block statement chain and
asks a deliberately narrow question: can we build a smaller verifier-facing
statement-chain handle that preserves the public commitments and claim boundary?

This is transcript/artifact compression, not proof composition, recursion, or
proof-size evidence.
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
import secrets
import stat as stat_module
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_CHAIN = EVIDENCE_DIR / "zkai-attention-derived-d128-block-statement-chain-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-statement-chain-compression-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-statement-chain-compression-2026-05.tsv"

SCHEMA = "zkai-attention-derived-d128-statement-chain-compression-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_STATEMENT_CHAIN_TRANSCRIPT_COMPRESSION"
RESULT = "GO_COMPRESSED_VERIFIER_FACING_STATEMENT_CHAIN_ARTIFACT_NO_GO_PROOF_SIZE"
CLAIM_BOUNDARY = "STATEMENT_CHAIN_TRANSCRIPT_COMPRESSION_NOT_PROOF_COMPOSITION_NOT_PROOF_SIZE_EVIDENCE"
COMPRESSED_ARTIFACT_SCHEMA = "zkai-attention-derived-d128-statement-chain-compressed-artifact-v1"
VERIFIER_HANDLE_SCHEMA = "zkai-attention-derived-d128-statement-chain-compression-verifier-handle-v1"
COMPRESSED_ARTIFACT_KIND = "attention-derived-d128-statement-chain-compressed-transcript"
COMPRESSED_ARTIFACT_DOMAIN = "ptvm:zkai:attention-derived-d128:statement-chain-compressed-artifact:v1"
VERIFIER_HANDLE_DOMAIN = "ptvm:zkai:attention-derived-d128:statement-chain-compression-verifier-handle:v1"
MAX_SOURCE_BYTES = 16 * 1024 * 1024

SOURCE_SCHEMA = "zkai-attention-derived-d128-block-statement-chain-gate-v1"
SOURCE_DECISION = "GO_ATTENTION_DERIVED_D128_BLOCK_STATEMENT_CHAIN"
SOURCE_RESULT = "GO_COMMITTED_SLICE_CHAIN_NO_GO_SINGLE_COMPOSED_PROOF"
EXPECTED_SOURCE_BLOCK_STATEMENT = "blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5"
EXPECTED_SOURCE_PAYLOAD = "sha256:555998c5aecacc6e1d5e3ae8940f249f263c5b8dd3a40bf07cfa024478f6bd52"
EXPECTED_SOURCE_CASES = 19
EXPECTED_SOURCE_SLICES = 6
EXPECTED_SOURCE_EDGES = 11
EXPECTED_SOURCE_ROWS = 199_553

NON_CLAIMS = [
    "not one composed d128 transformer-block proof",
    "not recursive aggregation",
    "not proof-carrying data",
    "not proof-size evidence",
    "not verifier-time evidence",
    "not proof-generation-time evidence",
    "not learned model weights",
    "not matched NANOZK benchmark evidence",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_statement_chain_compression_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-statement-chain-compression-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-statement-chain-compression-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_statement_chain_compression_gate.py scripts/tests/test_zkai_attention_derived_d128_statement_chain_compression_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_statement_chain_compression_gate",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

EXPECTED_MUTATIONS = (
    "source_schema_drift",
    "source_decision_drift",
    "source_result_drift",
    "source_payload_commitment_drift",
    "source_block_statement_drift",
    "source_summary_statement_drift",
    "source_edges_not_all_match",
    "source_slice_count_drift",
    "source_edge_count_drift",
    "source_row_count_drift",
    "source_case_count_drift",
    "compressed_artifact_commitment_drift",
    "compressed_artifact_claim_boundary_drift",
    "compressed_public_input_removed",
    "verifier_handle_commitment_drift",
    "verifier_handle_artifact_drift",
    "compression_metric_relabeling",
    "proof_size_metric_smuggled",
    "non_claims_removed",
    "validation_command_drift",
)


class AttentionDerivedD128StatementChainCompressionError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AttentionDerivedD128StatementChainCompressionError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise AttentionDerivedD128StatementChainCompressionError(f"invalid JSON value: {err}") from err


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return "blake2b-256:" + digest.hexdigest()


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return sha256_json(material)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def read_source_bytes(path: pathlib.Path, label: str) -> bytes:
    root = ROOT.resolve()
    candidate = pathlib.Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as err:
        raise AttentionDerivedD128StatementChainCompressionError(f"{label} must stay inside repository") from err

    current = root
    pre_stat = None
    try:
        for part in relative.parts:
            current = current / part
            part_stat = current.lstat()
            if stat_module.S_ISLNK(part_stat.st_mode):
                raise AttentionDerivedD128StatementChainCompressionError(f"{label} must not traverse symlinks")
            pre_stat = part_stat
        if pre_stat is None or not stat_module.S_ISREG(pre_stat.st_mode):
            raise AttentionDerivedD128StatementChainCompressionError(f"{label} must be a repo file")
        fd: int | None = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise AttentionDerivedD128StatementChainCompressionError(f"{label} must be a repo file")
            if (post_stat.st_dev, post_stat.st_ino, post_stat.st_size) != (
                pre_stat.st_dev,
                pre_stat.st_ino,
                pre_stat.st_size,
            ):
                raise AttentionDerivedD128StatementChainCompressionError(f"{label} changed while reading")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(MAX_SOURCE_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise AttentionDerivedD128StatementChainCompressionError(f"failed to read {label}: {err}") from err
    if len(raw) > MAX_SOURCE_BYTES:
        raise AttentionDerivedD128StatementChainCompressionError(f"{label} exceeds max source bytes")
    return raw


def parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise AttentionDerivedD128StatementChainCompressionError(f"failed to parse {label}: {err}") from err
    if not isinstance(payload, dict):
        raise AttentionDerivedD128StatementChainCompressionError(f"{label} must be object")
    return payload


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return parse_json_bytes(read_source_bytes(path, str(path.relative_to(ROOT))), str(path.relative_to(ROOT)))


def _dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128StatementChainCompressionError(f"{field} must be object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128StatementChainCompressionError(f"{field} must be list")
    return value


def _str(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise AttentionDerivedD128StatementChainCompressionError(f"{field} must be string")
    return value


def _int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128StatementChainCompressionError(f"{field} must be integer")
    return value


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128StatementChainCompressionError(f"{field} must be boolean")
    return value


def source_summary(source: dict[str, Any]) -> dict[str, Any]:
    if _str(source.get("schema"), "source.schema") != SOURCE_SCHEMA:
        raise AttentionDerivedD128StatementChainCompressionError("source schema drift")
    if _str(source.get("decision"), "source.decision") != SOURCE_DECISION:
        raise AttentionDerivedD128StatementChainCompressionError("source decision drift")
    if _str(source.get("result"), "source.result") != SOURCE_RESULT:
        raise AttentionDerivedD128StatementChainCompressionError("source result drift")
    if _str(source.get("payload_commitment"), "source.payload_commitment") != EXPECTED_SOURCE_PAYLOAD:
        raise AttentionDerivedD128StatementChainCompressionError("source payload commitment drift")
    if _str(source.get("block_statement_commitment"), "source.block_statement_commitment") != EXPECTED_SOURCE_BLOCK_STATEMENT:
        raise AttentionDerivedD128StatementChainCompressionError("source block statement drift")
    if not _bool(source.get("all_mutations_rejected"), "source.all_mutations_rejected"):
        raise AttentionDerivedD128StatementChainCompressionError("source mutation rejection drift")
    if _int(source.get("case_count"), "source.case_count") != EXPECTED_SOURCE_CASES:
        raise AttentionDerivedD128StatementChainCompressionError("source case count drift")
    summary = _dict(source.get("summary"), "source.summary")
    if _str(summary.get("block_statement_commitment"), "source.summary.block_statement_commitment") != EXPECTED_SOURCE_BLOCK_STATEMENT:
        raise AttentionDerivedD128StatementChainCompressionError("source summary statement drift")
    if not _bool(summary.get("all_edges_match"), "source.summary.all_edges_match"):
        raise AttentionDerivedD128StatementChainCompressionError("source edges-not-all-match drift")
    if _int(summary.get("slice_count"), "source.summary.slice_count") != EXPECTED_SOURCE_SLICES:
        raise AttentionDerivedD128StatementChainCompressionError("source slice count drift")
    if _int(summary.get("edge_count"), "source.summary.edge_count") != EXPECTED_SOURCE_EDGES:
        raise AttentionDerivedD128StatementChainCompressionError("source edge count drift")
    if _int(summary.get("accounted_relation_rows"), "source.summary.accounted_relation_rows") != EXPECTED_SOURCE_ROWS:
        raise AttentionDerivedD128StatementChainCompressionError("source row count drift")
    return summary


def build_compressed_artifact(source: dict[str, Any], source_raw: bytes) -> dict[str, Any]:
    summary = source_summary(source)
    source_artifact = {
        "path": str(SOURCE_CHAIN.relative_to(ROOT)),
        "file_sha256": sha256_bytes(source_raw),
        "payload_commitment": source["payload_commitment"],
        "block_statement_commitment": source["block_statement_commitment"],
    }
    required_public_inputs = {
        "block_statement_commitment": source["block_statement_commitment"],
        "source_attention_outputs_commitment": summary["source_attention_outputs_commitment"],
        "derived_input_activation_commitment": summary["derived_input_activation_commitment"],
        "derived_hidden_activation_commitment": summary["derived_hidden_activation_commitment"],
        "derived_residual_delta_commitment": summary["derived_residual_delta_commitment"],
        "derived_output_activation_commitment": summary["derived_output_activation_commitment"],
        "slice_count": summary["slice_count"],
        "edge_count": summary["edge_count"],
        "accounted_relation_rows": summary["accounted_relation_rows"],
        "projection_mul_rows": summary["projection_mul_rows"],
        "down_projection_mul_rows": summary["down_projection_mul_rows"],
        "activation_lookup_rows": summary["activation_lookup_rows"],
        "residual_add_rows": summary["residual_add_rows"],
        "source_payload_commitment": source["payload_commitment"],
    }
    preimage = {
        "artifact_kind": COMPRESSED_ARTIFACT_KIND,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifact": source_artifact,
        "required_public_inputs": required_public_inputs,
        "non_claims": list(NON_CLAIMS),
    }
    artifact = {
        "schema": COMPRESSED_ARTIFACT_SCHEMA,
        "artifact_kind": COMPRESSED_ARTIFACT_KIND,
        "claim_boundary": CLAIM_BOUNDARY,
        "preimage": preimage,
    }
    artifact["compressed_artifact_commitment"] = blake2b_commitment(preimage, COMPRESSED_ARTIFACT_DOMAIN)
    return artifact


def build_verifier_handle(artifact: dict[str, Any]) -> dict[str, Any]:
    preimage = {
        "accepted": True,
        "accepted_artifact_commitment": artifact["compressed_artifact_commitment"],
        "accepted_artifact_schema": artifact["schema"],
        "accepted_claim_boundary": artifact["claim_boundary"],
        "required_public_inputs": artifact["preimage"]["required_public_inputs"],
        "verifier_steps": [
            "recompute source file sha256",
            "check source payload and block statement commitments",
            "check compressed artifact commitment",
            "check all required public inputs",
            "reject proof-size, recursion, timing, or production claims",
        ],
    }
    handle = {
        "schema": VERIFIER_HANDLE_SCHEMA,
        "accepted": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "preimage": preimage,
    }
    handle["verifier_handle_commitment"] = blake2b_commitment(preimage, VERIFIER_HANDLE_DOMAIN)
    return handle


def serialized_len(value: Any) -> int:
    return len((pretty_json(value) + "\n").encode("utf-8"))


def build_core_payload(source: dict[str, Any], source_raw: bytes) -> dict[str, Any]:
    artifact = build_compressed_artifact(source, source_raw)
    handle = build_verifier_handle(artifact)
    source_bytes = len(source_raw)
    compressed_bytes = serialized_len(artifact)
    byte_savings = source_bytes - compressed_bytes
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_chain": {
            "path": str(SOURCE_CHAIN.relative_to(ROOT)),
            "file_sha256": sha256_bytes(source_raw),
            "payload_commitment": source["payload_commitment"],
            "block_statement_commitment": source["block_statement_commitment"],
        },
        "compressed_artifact": artifact,
        "verifier_handle": handle,
        "compression_metrics": {
            "source_chain_artifact_bytes": source_bytes,
            "compressed_artifact_bytes": compressed_bytes,
            "byte_savings": byte_savings,
            "compressed_to_source_ratio": round(compressed_bytes / source_bytes, 6),
            "timing_mode": "not_timed",
            "proof_size_metrics": None,
        },
        "recursive_or_pcd_status": {
            "result": "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_MISSING",
            "first_blocker": "no executable outer proof currently proves the attention-derived d128 slice-chain verifier checks inside one cryptographic object",
            "outer_proof_artifacts": [],
            "proof_metrics": None,
        },
        "summary": {
            "go_result": "GO for verifier-facing transcript compression of the attention-derived d128 statement chain",
            "no_go_result": "NO-GO for proof composition, recursive aggregation, proof-size savings, timings, or production readiness",
            "block_statement_commitment": source["block_statement_commitment"],
            "source_chain_artifact_bytes": source_bytes,
            "compressed_artifact_bytes": compressed_bytes,
            "byte_savings": byte_savings,
            "compressed_to_source_ratio": round(compressed_bytes / source_bytes, 6),
            "source_relation_rows": source_summary(source)["accounted_relation_rows"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }


def build_payload() -> dict[str, Any]:
    source_raw = read_source_bytes(SOURCE_CHAIN, "source chain JSON")
    source = parse_json_bytes(source_raw, "source chain JSON")
    payload = build_core_payload(source, source_raw)
    payload = finalize_payload(payload)
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


def validate_compressed_artifact(artifact: dict[str, Any]) -> None:
    if _str(artifact.get("schema"), "compressed_artifact.schema") != COMPRESSED_ARTIFACT_SCHEMA:
        raise AttentionDerivedD128StatementChainCompressionError("compressed artifact schema drift")
    if _str(artifact.get("claim_boundary"), "compressed_artifact.claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128StatementChainCompressionError("compressed artifact claim boundary drift")
    preimage = _dict(artifact.get("preimage"), "compressed_artifact.preimage")
    expected = blake2b_commitment(preimage, COMPRESSED_ARTIFACT_DOMAIN)
    if _str(artifact.get("compressed_artifact_commitment"), "compressed_artifact.commitment") != expected:
        raise AttentionDerivedD128StatementChainCompressionError("compressed artifact commitment drift")
    required = _dict(preimage.get("required_public_inputs"), "compressed_artifact.required_public_inputs")
    for key in (
        "block_statement_commitment",
        "source_attention_outputs_commitment",
        "derived_input_activation_commitment",
        "derived_output_activation_commitment",
        "source_payload_commitment",
    ):
        _str(required.get(key), f"compressed_artifact.required_public_inputs.{key}")
    if _str(required["block_statement_commitment"], "required block statement") != EXPECTED_SOURCE_BLOCK_STATEMENT:
        raise AttentionDerivedD128StatementChainCompressionError("compressed public input block statement drift")
    if _str(required["source_payload_commitment"], "required source payload") != EXPECTED_SOURCE_PAYLOAD:
        raise AttentionDerivedD128StatementChainCompressionError("compressed public input payload drift")
    if _int(required.get("slice_count"), "compressed_artifact.required_public_inputs.slice_count") != EXPECTED_SOURCE_SLICES:
        raise AttentionDerivedD128StatementChainCompressionError("compressed public input slice count drift")
    if _int(required.get("edge_count"), "compressed_artifact.required_public_inputs.edge_count") != EXPECTED_SOURCE_EDGES:
        raise AttentionDerivedD128StatementChainCompressionError("compressed public input edge count drift")
    if (
        _int(required.get("accounted_relation_rows"), "compressed_artifact.required_public_inputs.accounted_relation_rows")
        != EXPECTED_SOURCE_ROWS
    ):
        raise AttentionDerivedD128StatementChainCompressionError("compressed public input row count drift")


def validate_verifier_handle(handle: dict[str, Any], artifact: dict[str, Any]) -> None:
    if _str(handle.get("schema"), "verifier_handle.schema") != VERIFIER_HANDLE_SCHEMA:
        raise AttentionDerivedD128StatementChainCompressionError("verifier handle schema drift")
    if not _bool(handle.get("accepted"), "verifier_handle.accepted"):
        raise AttentionDerivedD128StatementChainCompressionError("verifier handle acceptance drift")
    if _str(handle.get("claim_boundary"), "verifier_handle.claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128StatementChainCompressionError("verifier handle claim boundary drift")
    preimage = _dict(handle.get("preimage"), "verifier_handle.preimage")
    if _str(preimage.get("accepted_artifact_commitment"), "verifier_handle.accepted_artifact_commitment") != artifact[
        "compressed_artifact_commitment"
    ]:
        raise AttentionDerivedD128StatementChainCompressionError("verifier handle artifact drift")
    expected = blake2b_commitment(preimage, VERIFIER_HANDLE_DOMAIN)
    if _str(handle.get("verifier_handle_commitment"), "verifier_handle.commitment") != expected:
        raise AttentionDerivedD128StatementChainCompressionError("verifier handle commitment drift")


def validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise AttentionDerivedD128StatementChainCompressionError("payload must be object")
    if _str(payload.get("schema"), "schema") != SCHEMA:
        raise AttentionDerivedD128StatementChainCompressionError("schema drift")
    if _str(payload.get("decision"), "decision") != DECISION:
        raise AttentionDerivedD128StatementChainCompressionError("decision drift")
    if _str(payload.get("result"), "result") != RESULT:
        raise AttentionDerivedD128StatementChainCompressionError("result drift")
    if _str(payload.get("claim_boundary"), "claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128StatementChainCompressionError("claim boundary drift")
    source = _dict(payload.get("source_chain"), "source_chain")
    if _str(source.get("payload_commitment"), "source_chain.payload_commitment") != EXPECTED_SOURCE_PAYLOAD:
        raise AttentionDerivedD128StatementChainCompressionError("source chain payload commitment drift")
    if _str(source.get("block_statement_commitment"), "source_chain.block_statement_commitment") != EXPECTED_SOURCE_BLOCK_STATEMENT:
        raise AttentionDerivedD128StatementChainCompressionError("source chain block statement drift")
    validate_compressed_artifact(_dict(payload.get("compressed_artifact"), "compressed_artifact"))
    validate_verifier_handle(
        _dict(payload.get("verifier_handle"), "verifier_handle"),
        _dict(payload.get("compressed_artifact"), "compressed_artifact"),
    )
    metrics = _dict(payload.get("compression_metrics"), "compression_metrics")
    source_bytes = _int(metrics.get("source_chain_artifact_bytes"), "source_chain_artifact_bytes")
    compressed_bytes = _int(metrics.get("compressed_artifact_bytes"), "compressed_artifact_bytes")
    if source_bytes <= 0 or compressed_bytes <= 0:
        raise AttentionDerivedD128StatementChainCompressionError("compression metrics must be positive")
    if _int(metrics.get("byte_savings"), "byte_savings") != source_bytes - compressed_bytes:
        raise AttentionDerivedD128StatementChainCompressionError("compression byte savings drift")
    if metrics.get("proof_size_metrics") is not None:
        raise AttentionDerivedD128StatementChainCompressionError("proof size metric smuggled")
    summary = _dict(payload.get("summary"), "summary")
    if _str(summary.get("block_statement_commitment"), "summary.block_statement_commitment") != EXPECTED_SOURCE_BLOCK_STATEMENT:
        raise AttentionDerivedD128StatementChainCompressionError("summary block statement drift")
    if _int(summary.get("source_relation_rows"), "summary.source_relation_rows") != EXPECTED_SOURCE_ROWS:
        raise AttentionDerivedD128StatementChainCompressionError("summary source relation rows drift")
    if _int(summary.get("source_chain_artifact_bytes"), "summary.source_chain_artifact_bytes") != source_bytes:
        raise AttentionDerivedD128StatementChainCompressionError("summary source bytes drift")
    if _int(summary.get("compressed_artifact_bytes"), "summary.compressed_artifact_bytes") != compressed_bytes:
        raise AttentionDerivedD128StatementChainCompressionError("summary compressed bytes drift")
    if _int(summary.get("byte_savings"), "summary.byte_savings") != source_bytes - compressed_bytes:
        raise AttentionDerivedD128StatementChainCompressionError("summary byte savings drift")
    recursive = _dict(payload.get("recursive_or_pcd_status"), "recursive_or_pcd_status")
    if _str(recursive.get("result"), "recursive_or_pcd_status.result") != "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_MISSING":
        raise AttentionDerivedD128StatementChainCompressionError("recursive status drift")
    if recursive.get("proof_metrics") is not None:
        raise AttentionDerivedD128StatementChainCompressionError("recursive proof metric smuggled")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128StatementChainCompressionError("non_claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128StatementChainCompressionError("validation command drift")
    if ("cases" in payload) != ("case_count" in payload):
        raise AttentionDerivedD128StatementChainCompressionError("mutation finalization drift")
    if "cases" in payload:
        inventory = _list(payload.get("mutation_inventory"), "mutation_inventory")
        cases = _list(payload.get("cases"), "cases")
        if tuple(inventory) != EXPECTED_MUTATIONS:
            raise AttentionDerivedD128StatementChainCompressionError("mutation inventory drift")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128StatementChainCompressionError("mutation cases drift")
        if _int(payload.get("case_count"), "case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128StatementChainCompressionError("mutation count drift")
        if not _bool(payload.get("all_mutations_rejected"), "all_mutations_rejected"):
            raise AttentionDerivedD128StatementChainCompressionError("mutation rejection drift")
        for index, expected_name in enumerate(EXPECTED_MUTATIONS):
            case = _dict(cases[index], f"case {index}")
            if _str(case.get("name"), "case.name") != expected_name:
                raise AttentionDerivedD128StatementChainCompressionError("mutation case name drift")
            if _bool(case.get("accepted"), "case.accepted"):
                raise AttentionDerivedD128StatementChainCompressionError("mutation accepted unexpectedly")
            if not _bool(case.get("rejected"), "case.rejected"):
                raise AttentionDerivedD128StatementChainCompressionError("mutation rejection flag drift")
            _str(case.get("error"), "case.error")
    if _str(payload.get("payload_commitment"), "payload_commitment") != payload_commitment(payload):
        raise AttentionDerivedD128StatementChainCompressionError("payload commitment drift")


MutationFn = Callable[[dict[str, Any]], None]


def _recommit_artifact(payload: dict[str, Any]) -> None:
    artifact = payload["compressed_artifact"]
    artifact["compressed_artifact_commitment"] = blake2b_commitment(
        artifact["preimage"], COMPRESSED_ARTIFACT_DOMAIN
    )


def _recommit_handle(payload: dict[str, Any]) -> None:
    handle = payload["verifier_handle"]
    handle["verifier_handle_commitment"] = blake2b_commitment(handle["preimage"], VERIFIER_HANDLE_DOMAIN)


def run_mutations(base_payload: dict[str, Any]) -> list[dict[str, Any]]:
    def mutate_source_schema(payload: dict[str, Any]) -> None:
        payload["source_chain"]["payload_commitment"] = "sha256:" + "00" * 32

    mutations: dict[str, MutationFn] = {
        "source_schema_drift": lambda p: p.__setitem__("schema", "different"),
        "source_decision_drift": lambda p: p.__setitem__("decision", "NO_GO"),
        "source_result_drift": lambda p: p.__setitem__("result", "NO_GO"),
        "source_payload_commitment_drift": mutate_source_schema,
        "source_block_statement_drift": lambda p: p["source_chain"].__setitem__(
            "block_statement_commitment", "blake2b-256:" + "00" * 32
        ),
        "source_summary_statement_drift": lambda p: p["summary"].__setitem__(
            "block_statement_commitment", "blake2b-256:" + "11" * 32
        ),
        "source_edges_not_all_match": lambda p: p["compressed_artifact"]["preimage"][
            "required_public_inputs"
        ].__setitem__("edge_count", 10),
        "source_slice_count_drift": lambda p: p["compressed_artifact"]["preimage"][
            "required_public_inputs"
        ].__setitem__("slice_count", 5),
        "source_edge_count_drift": lambda p: p["summary"].__setitem__("source_relation_rows", 1),
        "source_row_count_drift": lambda p: p["compressed_artifact"]["preimage"][
            "required_public_inputs"
        ].__setitem__("accounted_relation_rows", 1),
        "source_case_count_drift": lambda p: p.__setitem__("case_count", 1),
        "compressed_artifact_commitment_drift": lambda p: p["compressed_artifact"].__setitem__(
            "compressed_artifact_commitment", "blake2b-256:" + "22" * 32
        ),
        "compressed_artifact_claim_boundary_drift": lambda p: (
            p["compressed_artifact"].__setitem__("claim_boundary", "RECURSIVE"),
            p["compressed_artifact"]["preimage"].__setitem__("claim_boundary", "RECURSIVE"),
            _recommit_artifact(p),
        ),
        "compressed_public_input_removed": lambda p: (
            p["compressed_artifact"]["preimage"]["required_public_inputs"].pop("derived_output_activation_commitment"),
            _recommit_artifact(p),
        ),
        "verifier_handle_commitment_drift": lambda p: p["verifier_handle"].__setitem__(
            "verifier_handle_commitment", "blake2b-256:" + "33" * 32
        ),
        "verifier_handle_artifact_drift": lambda p: (
            p["verifier_handle"]["preimage"].__setitem__("accepted_artifact_commitment", "blake2b-256:" + "44" * 32),
            _recommit_handle(p),
        ),
        "compression_metric_relabeling": lambda p: p["compression_metrics"].__setitem__("byte_savings", 0),
        "proof_size_metric_smuggled": lambda p: p["compression_metrics"].__setitem__(
            "proof_size_metrics", {"proof_bytes": 1}
        ),
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
        except AttentionDerivedD128StatementChainCompressionError as err:
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
            "block_statement_commitment",
            "source_chain_artifact_bytes",
            "compressed_artifact_bytes",
            "byte_savings",
            "compressed_to_source_ratio",
            "mutations_rejected",
        ]
    )
    summary = payload["summary"]
    writer.writerow(
        [
            payload["decision"],
            payload["result"],
            summary["block_statement_commitment"],
            summary["source_chain_artifact_bytes"],
            summary["compressed_artifact_bytes"],
            summary["byte_savings"],
            summary["compressed_to_source_ratio"],
            payload["case_count"],
        ]
    )
    return out.getvalue()


def require_output_path(path: pathlib.Path, *, suffix: str) -> pathlib.Path:
    candidate = pathlib.Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    evidence_root = EVIDENCE_DIR.resolve()
    try:
        relative = candidate.relative_to(evidence_root)
    except ValueError as err:
        raise AttentionDerivedD128StatementChainCompressionError("output path must stay under evidence dir") from err
    current = evidence_root
    for part in relative.parent.parts:
        current = current / part
        try:
            part_stat = current.lstat()
        except OSError as err:
            raise AttentionDerivedD128StatementChainCompressionError(f"output parent must exist: {current}") from err
        if stat_module.S_ISLNK(part_stat.st_mode):
            raise AttentionDerivedD128StatementChainCompressionError("output path must not traverse symlinks")
        if not stat_module.S_ISDIR(part_stat.st_mode):
            raise AttentionDerivedD128StatementChainCompressionError(f"output parent must be directory: {current}")
    if candidate.suffix != suffix:
        raise AttentionDerivedD128StatementChainCompressionError(f"output path must end with {suffix}")
    if candidate.is_symlink() or (candidate.exists() and candidate.is_dir()):
        raise AttentionDerivedD128StatementChainCompressionError("output path must be a non-symlink file")
    return candidate


def atomic_write_text(path: pathlib.Path, text: str, *, suffix: str) -> None:
    output = require_output_path(path, suffix=suffix)
    parent_fd = os.open(output.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    tmp_name = f".{output.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    tmp_created = False
    try:
        fd: int | None = os.open(
            tmp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
        tmp_created = True
        try:
            handle = os.fdopen(fd, "w", encoding="utf-8", newline="")
        except Exception:
            os.close(fd)
            fd = None
            raise
        fd = None
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(tmp_name, output.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        tmp_created = False
        os.fsync(parent_fd)
    except Exception:
        if tmp_created:
            try:
                os.unlink(tmp_name, dir_fd=parent_fd)
            except OSError:
                pass
        raise
    finally:
        os.close(parent_fd)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    if json_path is None and tsv_path is None:
        raise AttentionDerivedD128StatementChainCompressionError("at least one output path is required")
    if json_path is not None:
        atomic_write_text(json_path, pretty_json(payload) + "\n", suffix=".json")
    if tsv_path is not None:
        atomic_write_text(tsv_path, to_tsv(payload), suffix=".tsv")


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
                        "block_statement_commitment": payload["summary"]["block_statement_commitment"],
                        "source_chain_artifact_bytes": payload["summary"]["source_chain_artifact_bytes"],
                        "compressed_artifact_bytes": payload["summary"]["compressed_artifact_bytes"],
                        "byte_savings": payload["summary"]["byte_savings"],
                        "compressed_to_source_ratio": payload["summary"]["compressed_to_source_ratio"],
                        "mutations_rejected": payload["case_count"],
                    },
                    sort_keys=True,
                )
            )
        else:
            print(pretty_json(payload))
    except AttentionDerivedD128StatementChainCompressionError as err:
        print(f"attention-derived d128 statement-chain compression gate failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
