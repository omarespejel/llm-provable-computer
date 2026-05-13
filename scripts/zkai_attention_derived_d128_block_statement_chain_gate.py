#!/usr/bin/env python3
"""Build a statement chain for the attention-derived d128 block surface."""

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
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

INPUT_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-input-2026-05.json"
RMSNORM_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json"
PROJECTION_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-projection-boundary-2026-05.json"
ACTIVATION_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-activation-swiglu-2026-05.json"
DOWN_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-down-projection-2026-05.json"
RESIDUAL_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-residual-add-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-block-statement-chain-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-block-statement-chain-2026-05.tsv"

SCHEMA = "zkai-attention-derived-d128-block-statement-chain-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_BLOCK_STATEMENT_CHAIN"
RESULT = "GO_COMMITTED_SLICE_CHAIN_NO_GO_SINGLE_COMPOSED_PROOF"
CLAIM_BOUNDARY = (
    "ONE_STATEMENT_CHAIN_BINDS_ATTENTION_DERIVED_D128_SLICES_"
    "NOT_ONE_COMPOSED_PROOF_NOT_PROOF_SIZE_EVIDENCE_NOT_MODEL_FAITHFUL_WEIGHTS"
)
STATEMENT_DOMAIN = "ptvm:zkai:attention-derived-d128:block-statement-chain:v1"
MAX_SOURCE_BYTES = 32 * 1024 * 1024

ARTIFACT_SPECS = {
    "input": {
        "path": INPUT_JSON,
        "schema": "zkai-attention-derived-d128-input-gate-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_INPUT_FIXTURE",
        "result": "GO_VALUE_CONNECTED_INPUT_ARTIFACT_NO_GO_CURRENT_D128_BLOCK",
        "payload_commitment": "sha256:2ae84c02a4267c6e85786d1317fdd2c6d7921970169db09bd66dfbd9f34b7a77",
    },
    "rmsnorm": {
        "path": RMSNORM_JSON,
        "schema": "zkai-attention-derived-d128-rmsnorm-public-row-gate-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_RMSNORM_PUBLIC_ROW_INPUT",
        "result": "GO_VALUE_CONNECTED_RMSNORM_SLICE_INPUT_NO_GO_FULL_BLOCK",
        "payload_commitment": "sha256:863c74ca6adcc1da81409cd80806014c54475479b195cf3ff71e0f5c0d0a3301",
    },
    "projection": {
        "path": PROJECTION_JSON,
        "schema": "zkai-attention-derived-d128-projection-boundary-gate-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_PROJECTION_BOUNDARY_INPUT",
        "result": "GO_VALUE_CONNECTED_GATE_VALUE_PROJECTION_INPUT_NO_GO_FULL_BLOCK",
        "payload_commitment": "sha256:627115a11d771a6da1c50407963efa5eb39c52226adf69deedc43083c05a0af6",
    },
    "activation_swiglu": {
        "path": ACTIVATION_JSON,
        "schema": "zkai-attention-derived-d128-activation-swiglu-gate-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_ACTIVATION_SWIGLU_INPUT",
        "result": "GO_VALUE_CONNECTED_ACTIVATION_SWIGLU_INPUT_NO_GO_FULL_BLOCK",
        "payload_commitment": "sha256:bf058e95c387d536d85a2a9b455c0f211ecfc7bc1f71ba4df3b17aec9442b302",
    },
    "down_projection": {
        "path": DOWN_JSON,
        "schema": "zkai-attention-derived-d128-down-projection-gate-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_DOWN_PROJECTION_INPUT",
        "result": "GO_VALUE_CONNECTED_DOWN_PROJECTION_INPUT_NO_GO_FULL_BLOCK",
        "payload_commitment": "sha256:66dd7949ef35d6ddecf6ee0534dabe7e78ccb898776e7e1fa7bcbac2e2aaf150",
    },
    "residual_add": {
        "path": RESIDUAL_JSON,
        "schema": "zkai-attention-derived-d128-residual-add-gate-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_RESIDUAL_ADD_INPUT",
        "result": "GO_VALUE_CONNECTED_RESIDUAL_ADD_INPUT_NO_GO_SINGLE_BLOCK_PROOF",
        "payload_commitment": "sha256:a82f94544eb2f7415fa0caec9605730a857e5a380bed0cbccb6ec2bd6f869861",
    },
}

NON_CLAIMS = [
    "not one composed d128 transformer-block proof",
    "not recursive composition",
    "not proof-size savings",
    "not timing evidence",
    "not learned model weights",
    "not exact LayerNorm or GELU",
    "not full autoregressive inference",
    "not production-ready",
    "slice commitments are bound as a statement chain, not verified inside one outer proof",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_block_statement_chain_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_block_statement_chain_gate.py scripts/tests/test_zkai_attention_derived_d128_block_statement_chain_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_block_statement_chain_gate",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "source_artifacts",
    "block_statement",
    "block_statement_commitment",
    "summary",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = (
    "decision",
    "result",
    "block_statement_commitment",
    "source_attention_outputs_commitment",
    "derived_input_activation_commitment",
    "derived_output_activation_commitment",
    "slice_count",
    "edge_count",
    "accounted_relation_rows",
    "projection_mul_rows",
    "down_projection_mul_rows",
    "activation_lookup_rows",
    "mutations_rejected",
)


class AttentionDerivedD128BlockStatementChainError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AttentionDerivedD128BlockStatementChainError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise AttentionDerivedD128BlockStatementChainError(f"invalid JSON value: {err}") from err


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return "blake2b-256:" + digest.hexdigest()


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128BlockStatementChainError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128BlockStatementChainError(f"{label} must be list")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise AttentionDerivedD128BlockStatementChainError(f"{label} must be string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128BlockStatementChainError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128BlockStatementChainError(f"{label} must be boolean")
    return value


def _digest(value: Any, label: str, *, prefix: str = "blake2b-256") -> str:
    text = _str(value, label)
    if not text.startswith(f"{prefix}:"):
        raise AttentionDerivedD128BlockStatementChainError(f"{label} must be a {prefix} commitment")
    digest = text.removeprefix(f"{prefix}:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise AttentionDerivedD128BlockStatementChainError(f"{label} must be a 32-byte lowercase hex digest")
    return text


def _sha(value: Any, label: str) -> str:
    return _digest(value, label, prefix="sha256")


def read_source_bytes(path: pathlib.Path) -> bytes:
    root = ROOT.resolve()
    raw_candidate = path if path.is_absolute() else ROOT / path
    candidate = pathlib.Path(os.path.abspath(raw_candidate))
    if candidate.is_symlink():
        raise AttentionDerivedD128BlockStatementChainError(f"source path must not be symlink: {path}")
    try:
        relative = candidate.relative_to(root)
    except ValueError as err:
        raise AttentionDerivedD128BlockStatementChainError(f"source path must stay inside repository: {path}") from err
    current = root
    pre_stat = None
    try:
        for part in relative.parts:
            current = current / part
            part_stat = current.lstat()
            if stat_module.S_ISLNK(part_stat.st_mode):
                raise AttentionDerivedD128BlockStatementChainError(f"source path must not traverse symlinks: {path}")
            pre_stat = part_stat
        if pre_stat is None or not stat_module.S_ISREG(pre_stat.st_mode):
            raise AttentionDerivedD128BlockStatementChainError(f"source path must be a repo file: {path}")
        if pre_stat.st_size > MAX_SOURCE_BYTES:
            raise AttentionDerivedD128BlockStatementChainError(f"source path exceeds size limit: {path}")
        fd: int | None = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if (post_stat.st_dev, post_stat.st_ino, post_stat.st_size) != (
                pre_stat.st_dev,
                pre_stat.st_ino,
                pre_stat.st_size,
            ):
                raise AttentionDerivedD128BlockStatementChainError(f"source path changed while reading: {path}")
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise AttentionDerivedD128BlockStatementChainError(f"source path must remain a regular file: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(MAX_SOURCE_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise AttentionDerivedD128BlockStatementChainError(f"failed reading source path {path}: {err}") from err
    if len(raw) > MAX_SOURCE_BYTES:
        raise AttentionDerivedD128BlockStatementChainError(f"source path exceeds size limit after open: {path}")
    return raw


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    raw = read_source_bytes(path)
    try:
        parsed = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise AttentionDerivedD128BlockStatementChainError(f"failed parsing JSON source {path}: {err}") from err
    return _dict(parsed, f"JSON source {path}"), raw


def validate_source_payload(artifact_id: str, payload: dict[str, Any]) -> None:
    spec = ARTIFACT_SPECS[artifact_id]
    for key in ("schema", "decision", "result", "payload_commitment"):
        expected = _str(spec[key], f"{artifact_id}.{key}")
        actual = _str(payload.get(key), f"{artifact_id}.{key}")
        if actual != expected:
            raise AttentionDerivedD128BlockStatementChainError(
                f"{artifact_id} {key} drift: expected {expected}, got {actual}"
            )
    if not _bool(payload.get("all_mutations_rejected"), f"{artifact_id}.all_mutations_rejected"):
        raise AttentionDerivedD128BlockStatementChainError(f"{artifact_id} mutations were not all rejected")
    if _int(payload.get("case_count"), f"{artifact_id}.case_count") != len(
        _list(payload.get("mutation_inventory"), f"{artifact_id}.mutation_inventory")
    ):
        raise AttentionDerivedD128BlockStatementChainError(f"{artifact_id} mutation count drift")


def load_artifacts() -> dict[str, Any]:
    payloads: dict[str, dict[str, Any]] = {}
    source_artifacts: list[dict[str, Any]] = []
    for artifact_id, spec in ARTIFACT_SPECS.items():
        path = spec["path"]
        payload, raw = load_json(path)
        validate_source_payload(artifact_id, payload)
        payloads[artifact_id] = payload
        source_artifacts.append(
            {
                "id": artifact_id,
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "schema": payload["schema"],
                "decision": payload["decision"],
                "result": payload["result"],
                "payload_commitment": payload["payload_commitment"],
                "case_count": payload["case_count"],
                "all_mutations_rejected": payload["all_mutations_rejected"],
            }
        )
    return {"payloads": payloads, "source_artifacts": source_artifacts}


def _summary(payloads: dict[str, dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    return _dict(payloads[artifact_id].get("summary"), f"{artifact_id}.summary")


def _source_summary(payloads: dict[str, dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    return _dict(payloads[artifact_id].get("source_summary"), f"{artifact_id}.source_summary")


def _comparison(payloads: dict[str, dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    return _dict(payloads[artifact_id].get("comparison_summary"), f"{artifact_id}.comparison_summary")


def edge(edge_id: str, left: str, right: str, commitment: str, *, prefix: str = "blake2b-256") -> dict[str, Any]:
    if left != right:
        raise AttentionDerivedD128BlockStatementChainError(
            f"edge drift: {edge_id}: left {left} does not match right {right}"
        )
    matched = _digest(commitment, f"{edge_id}.commitment", prefix=prefix)
    if matched != left:
        raise AttentionDerivedD128BlockStatementChainError(
            f"edge drift: {edge_id}: stored commitment {matched} does not match checked value {left}"
        )
    return {"id": edge_id, "commitment": matched, "matches": True}


def build_edges(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    input_summary = _summary(payloads, "input")
    rmsnorm_summary = _summary(payloads, "rmsnorm")
    projection_summary = _summary(payloads, "projection")
    activation_summary = _summary(payloads, "activation_swiglu")
    activation_source = _source_summary(payloads, "activation_swiglu")
    down_summary = _summary(payloads, "down_projection")
    down_source = _source_summary(payloads, "down_projection")
    residual_summary = _summary(payloads, "residual_add")
    residual_source = _source_summary(payloads, "residual_add")

    return [
        edge(
            "attention_outputs_to_input",
            _digest(input_summary["source_attention_outputs_commitment"], "input.source_attention_outputs_commitment"),
            _digest(rmsnorm_summary["source_attention_outputs_commitment"], "rmsnorm.source_attention_outputs_commitment"),
            input_summary["source_attention_outputs_commitment"],
        ),
        edge(
            "input_activation_to_rmsnorm",
            _digest(input_summary["derived_input_activation_commitment"], "input.derived_input_activation_commitment"),
            _digest(rmsnorm_summary["input_activation_commitment"], "rmsnorm.input_activation_commitment"),
            input_summary["derived_input_activation_commitment"],
        ),
        edge(
            "rmsnorm_to_projection",
            _digest(rmsnorm_summary["rmsnorm_output_row_commitment"], "rmsnorm.rmsnorm_output_row_commitment"),
            _digest(projection_summary["derived_rmsnorm_output_row_commitment"], "projection.derived_rmsnorm_output_row_commitment"),
            rmsnorm_summary["rmsnorm_output_row_commitment"],
        ),
        edge(
            "projection_to_activation_gate_value",
            _digest(
                projection_summary["derived_gate_value_projection_output_commitment"],
                "projection.derived_gate_value_projection_output_commitment",
            ),
            _digest(
                activation_summary["derived_gate_value_projection_output_commitment"],
                "activation.derived_gate_value_projection_output_commitment",
            ),
            projection_summary["derived_gate_value_projection_output_commitment"],
        ),
        edge(
            "activation_statement_to_down_projection_source",
            _sha(payloads["activation_swiglu"]["payload_commitment"], "activation.payload_commitment"),
            _sha(down_summary["source_activation_swiglu_payload_commitment"], "down.source_activation_swiglu_payload_commitment"),
            payloads["activation_swiglu"]["payload_commitment"],
            prefix="sha256",
        ),
        edge(
            "activation_hidden_to_down_projection",
            _digest(activation_summary["derived_hidden_activation_commitment"], "activation.derived_hidden_activation_commitment"),
            _digest(down_summary["source_hidden_activation_commitment"], "down.source_hidden_activation_commitment"),
            activation_summary["derived_hidden_activation_commitment"],
        ),
        edge(
            "down_projection_to_residual_delta",
            _digest(down_summary["derived_residual_delta_commitment"], "down.derived_residual_delta_commitment"),
            _digest(residual_summary["source_residual_delta_commitment"], "residual.source_residual_delta_commitment"),
            down_summary["derived_residual_delta_commitment"],
        ),
        edge(
            "residual_input_reuses_derived_input",
            _digest(input_summary["derived_input_activation_commitment"], "input.derived_input_activation_commitment"),
            _digest(residual_summary["source_input_activation_commitment"], "residual.source_input_activation_commitment"),
            residual_summary["source_input_activation_commitment"],
        ),
        edge(
            "residual_source_payloads_bind_prior_slices",
            _sha(payloads["down_projection"]["payload_commitment"], "down.payload_commitment"),
            _sha(residual_source["source_down_projection_payload_commitment"], "residual.source_down_projection_payload_commitment"),
            payloads["down_projection"]["payload_commitment"],
            prefix="sha256",
        ),
        edge(
            "activation_source_reuses_projection_boundary",
            _sha(payloads["projection"]["payload_commitment"], "projection.payload_commitment"),
            _sha(activation_source["source_projection_boundary_payload_commitment"], "activation.source_projection_boundary_payload_commitment"),
            payloads["projection"]["payload_commitment"],
            prefix="sha256",
        ),
        edge(
            "down_source_reuses_activation_output",
            _digest(activation_summary["derived_activation_output_commitment"], "activation.derived_activation_output_commitment"),
            _digest(down_source["source_activation_output_commitment"], "down.source_activation_output_commitment"),
            activation_summary["derived_activation_output_commitment"],
        ),
    ]


def build_relation_rows(payloads: dict[str, dict[str, Any]]) -> dict[str, int]:
    rmsnorm = _summary(payloads, "rmsnorm")
    projection = _summary(payloads, "projection")
    activation = _summary(payloads, "activation_swiglu")
    down = _summary(payloads, "down_projection")
    residual = _summary(payloads, "residual_add")
    rows = {
        "rmsnorm_public_rows": _int(rmsnorm["row_count"], "rmsnorm.row_count"),
        "gate_value_projection_mul_rows": _int(projection["gate_value_mul_rows"], "projection.gate_value_mul_rows"),
        "activation_lookup_rows": _int(activation["activation_lookup_rows"], "activation.activation_lookup_rows"),
        "swiglu_mix_rows": _int(activation["swiglu_mix_rows"], "activation.swiglu_mix_rows"),
        "down_projection_mul_rows": _int(down["down_projection_mul_rows"], "down.down_projection_mul_rows"),
        "residual_delta_rows": _int(down["residual_delta_rows"], "down.residual_delta_rows"),
        "residual_add_rows": _int(residual["residual_add_rows"], "residual.residual_add_rows"),
    }
    rows["accounted_relation_rows"] = sum(rows.values())
    return rows


def build_block_statement(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    input_summary = _summary(payloads, "input")
    rmsnorm_summary = _summary(payloads, "rmsnorm")
    projection_summary = _summary(payloads, "projection")
    activation_summary = _summary(payloads, "activation_swiglu")
    down_summary = _summary(payloads, "down_projection")
    residual_summary = _summary(payloads, "residual_add")
    edges = build_edges(payloads)
    relation_rows = build_relation_rows(payloads)
    statement = {
        "schema": "zkai-attention-derived-d128-block-statement-chain-v1",
        "slice_order": list(ARTIFACT_SPECS),
        "source_attention_outputs_commitment": _digest(
            input_summary["source_attention_outputs_commitment"],
            "input.source_attention_outputs_commitment",
        ),
        "derived_input_activation_commitment": _digest(
            input_summary["derived_input_activation_commitment"],
            "input.derived_input_activation_commitment",
        ),
        "derived_rmsnorm_statement_commitment": _digest(
            rmsnorm_summary["rmsnorm_statement_commitment"],
            "rmsnorm.rmsnorm_statement_commitment",
        ),
        "derived_projection_statement_commitment": _digest(
            projection_summary["derived_gate_value_statement_commitment"],
            "projection.derived_gate_value_statement_commitment",
        ),
        "derived_activation_statement_commitment": _digest(
            activation_summary["derived_activation_statement_commitment"],
            "activation.derived_activation_statement_commitment",
        ),
        "derived_down_projection_statement_commitment": _digest(
            down_summary["derived_down_projection_statement_commitment"],
            "down.derived_down_projection_statement_commitment",
        ),
        "derived_residual_add_statement_commitment": _digest(
            residual_summary["derived_residual_add_statement_commitment"],
            "residual.derived_residual_add_statement_commitment",
        ),
        "derived_hidden_activation_commitment": _digest(
            activation_summary["derived_hidden_activation_commitment"],
            "activation.derived_hidden_activation_commitment",
        ),
        "derived_residual_delta_commitment": _digest(
            down_summary["derived_residual_delta_commitment"],
            "down.derived_residual_delta_commitment",
        ),
        "derived_output_activation_commitment": _digest(
            residual_summary["derived_output_activation_commitment"],
            "residual.derived_output_activation_commitment",
        ),
        "payload_commitments": {artifact_id: payloads[artifact_id]["payload_commitment"] for artifact_id in ARTIFACT_SPECS},
        "edges": edges,
        "relation_rows": relation_rows,
        "all_edges_match": all(_bool(edge_item["matches"], f"edge.{edge_item['id']}.matches") for edge_item in edges),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return statement


def build_context() -> dict[str, Any]:
    artifacts = load_artifacts()
    payloads = artifacts["payloads"]
    statement = build_block_statement(payloads)
    statement_commitment = blake2b_commitment(statement, STATEMENT_DOMAIN)
    return {
        "payloads": payloads,
        "source_artifacts": artifacts["source_artifacts"],
        "block_statement": statement,
        "block_statement_commitment": statement_commitment,
    }


def build_summary(statement: dict[str, Any], statement_commitment: str) -> dict[str, Any]:
    relation_rows = _dict(statement["relation_rows"], "statement.relation_rows")
    return {
        "block_statement_commitment": statement_commitment,
        "source_attention_outputs_commitment": statement["source_attention_outputs_commitment"],
        "derived_input_activation_commitment": statement["derived_input_activation_commitment"],
        "derived_hidden_activation_commitment": statement["derived_hidden_activation_commitment"],
        "derived_residual_delta_commitment": statement["derived_residual_delta_commitment"],
        "derived_output_activation_commitment": statement["derived_output_activation_commitment"],
        "slice_count": len(_list(statement["slice_order"], "statement.slice_order")),
        "edge_count": len(_list(statement["edges"], "statement.edges")),
        "all_edges_match": _bool(statement["all_edges_match"], "statement.all_edges_match"),
        "accounted_relation_rows": _int(relation_rows["accounted_relation_rows"], "relation_rows.accounted_relation_rows"),
        "projection_mul_rows": _int(relation_rows["gate_value_projection_mul_rows"], "relation_rows.gate_value_projection_mul_rows"),
        "down_projection_mul_rows": _int(relation_rows["down_projection_mul_rows"], "relation_rows.down_projection_mul_rows"),
        "activation_lookup_rows": _int(relation_rows["activation_lookup_rows"], "relation_rows.activation_lookup_rows"),
        "residual_add_rows": _int(relation_rows["residual_add_rows"], "relation_rows.residual_add_rows"),
        "go_result": "GO for a committed attention-derived d128 slice statement chain",
        "no_go_result": "NO-GO for one composed proof, proof-size savings, timings, or model-faithful learned weights",
    }


def build_core_payload(context: dict[str, Any]) -> dict[str, Any]:
    statement = copy.deepcopy(context["block_statement"])
    statement_commitment = context["block_statement_commitment"]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "block_statement": statement,
        "block_statement_commitment": statement_commitment,
        "summary": build_summary(statement, statement_commitment),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    validate_payload(payload, context=context)
    return payload


def validate_source_artifacts(payload: dict[str, Any], context: dict[str, Any]) -> None:
    expected = context["source_artifacts"]
    actual = _list(payload.get("source_artifacts"), "source_artifacts")
    if actual != expected:
        raise AttentionDerivedD128BlockStatementChainError("source artifact drift")


def validate_block_statement(statement: Any, context: dict[str, Any]) -> None:
    actual = _dict(statement, "block_statement")
    expected = context["block_statement"]
    if actual != expected:
        raise AttentionDerivedD128BlockStatementChainError("block statement drift")
    if not _bool(actual["all_edges_match"], "block_statement.all_edges_match"):
        raise AttentionDerivedD128BlockStatementChainError("edge match overclaim")


def validate_payload(payload: Any, *, context: dict[str, Any] | None = None) -> None:
    payload = _dict(payload, "payload")
    context = build_context() if context is None else context
    keys = set(payload)
    if keys not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionDerivedD128BlockStatementChainError(f"payload keys drift: {sorted(keys)}")
    if payload.get("schema") != SCHEMA:
        raise AttentionDerivedD128BlockStatementChainError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionDerivedD128BlockStatementChainError("decision drift")
    if payload.get("result") != RESULT:
        raise AttentionDerivedD128BlockStatementChainError("result drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128BlockStatementChainError("claim boundary drift")
    validate_source_artifacts(payload, context)
    validate_block_statement(payload.get("block_statement"), context)
    expected_statement_commitment = context["block_statement_commitment"]
    if payload.get("block_statement_commitment") != expected_statement_commitment:
        raise AttentionDerivedD128BlockStatementChainError("block statement commitment drift")
    expected_summary = build_summary(context["block_statement"], expected_statement_commitment)
    if _dict(payload.get("summary"), "summary") != expected_summary:
        raise AttentionDerivedD128BlockStatementChainError("summary drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128BlockStatementChainError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128BlockStatementChainError("validation commands drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise AttentionDerivedD128BlockStatementChainError("payload commitment drift")
    if keys == FINAL_KEYS:
        inventory = _list(payload.get("mutation_inventory"), "mutation_inventory")
        cases = _list(payload.get("cases"), "cases")
        if tuple(inventory) != EXPECTED_MUTATIONS:
            raise AttentionDerivedD128BlockStatementChainError("mutation inventory drift")
        if _int(payload.get("case_count"), "case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128BlockStatementChainError("mutation count drift")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128BlockStatementChainError("mutation cases drift")
        if not _bool(payload.get("all_mutations_rejected"), "all_mutations_rejected"):
            raise AttentionDerivedD128BlockStatementChainError("mutation rejection drift")
        for index, expected_name in enumerate(EXPECTED_MUTATIONS):
            case_dict = _dict(cases[index], f"mutation case {index}")
            if _str(case_dict.get("name"), "mutation case name") != expected_name:
                raise AttentionDerivedD128BlockStatementChainError("mutation case name drift")
            if _bool(case_dict.get("accepted"), "mutation case accepted"):
                raise AttentionDerivedD128BlockStatementChainError("mutation accepted unexpectedly")
            if not _bool(case_dict.get("rejected"), "mutation case rejected"):
                raise AttentionDerivedD128BlockStatementChainError("mutation rejection flag drift")
            expected_error = _str(EXPECTED_MUTATION_ERRORS[expected_name], "expected mutation error")
            if _str(case_dict.get("error"), "mutation case error") != expected_error:
                raise AttentionDerivedD128BlockStatementChainError("mutation case error drift")


MutationFn = Callable[[dict[str, Any]], None]


def _set_payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


def _drift_first_edge(payload: dict[str, Any]) -> None:
    payload["block_statement"]["edges"][0]["commitment"] = "blake2b-256:" + "22" * 32


def _drift_relation_rows(payload: dict[str, Any]) -> None:
    payload["block_statement"]["relation_rows"]["accounted_relation_rows"] += 1


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_overclaim", lambda p: p.__setitem__("decision", "GO_FULL_D128_TRANSFORMER_BLOCK"), True),
    ("result_overclaim", lambda p: p.__setitem__("result", "GO_SINGLE_COMPOSED_PROOF"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "FULL_LAYER_PROOF_SIZE_EVIDENCE"), True),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "33" * 32), True),
    (
        "source_payload_commitment_drift",
        lambda p: p["source_artifacts"][1].__setitem__("payload_commitment", "sha256:" + "44" * 32),
        True,
    ),
    ("slice_order_drift", lambda p: p["block_statement"]["slice_order"].reverse(), True),
    ("edge_commitment_drift", _drift_first_edge, True),
    (
        "input_activation_relabeling",
        lambda p: p["block_statement"].__setitem__(
            "derived_input_activation_commitment", p["block_statement"]["derived_output_activation_commitment"]
        ),
        True,
    ),
    (
        "hidden_activation_relabeling",
        lambda p: p["block_statement"].__setitem__(
            "derived_hidden_activation_commitment", p["block_statement"]["derived_input_activation_commitment"]
        ),
        True,
    ),
    (
        "residual_delta_relabeling",
        lambda p: p["block_statement"].__setitem__(
            "derived_residual_delta_commitment", p["block_statement"]["derived_input_activation_commitment"]
        ),
        True,
    ),
    (
        "output_relabels_input",
        lambda p: p["block_statement"].__setitem__(
            "derived_output_activation_commitment", p["block_statement"]["derived_input_activation_commitment"]
        ),
        True,
    ),
    ("relation_row_count_drift", _drift_relation_rows, True),
    (
        "all_edges_match_overclaim",
        lambda p: p["block_statement"].__setitem__("all_edges_match", False),
        True,
    ),
    (
        "statement_commitment_drift",
        lambda p: p.__setitem__("block_statement_commitment", "blake2b-256:" + "55" * 32),
        True,
    ),
    ("summary_output_drift", lambda p: p["summary"].__setitem__("derived_output_activation_commitment", "blake2b-256:" + "66" * 32), True),
    ("summary_rows_drift", lambda p: p["summary"].__setitem__("accounted_relation_rows", 1), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("validation_command_removed", lambda p: p.__setitem__("validation_commands", p["validation_commands"][1:]), True),
    ("payload_commitment_drift", _set_payload_commitment_drift, False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)
EXPECTED_MUTATION_ERRORS = {
    "decision_overclaim": "decision drift",
    "result_overclaim": "result drift",
    "claim_boundary_overclaim": "claim boundary drift",
    "source_artifact_hash_drift": "source artifact drift",
    "source_payload_commitment_drift": "source artifact drift",
    "slice_order_drift": "block statement drift",
    "edge_commitment_drift": "block statement drift",
    "input_activation_relabeling": "block statement drift",
    "hidden_activation_relabeling": "block statement drift",
    "residual_delta_relabeling": "block statement drift",
    "output_relabels_input": "block statement drift",
    "relation_row_count_drift": "block statement drift",
    "all_edges_match_overclaim": "block statement drift",
    "statement_commitment_drift": "block statement commitment drift",
    "summary_output_drift": "summary drift",
    "summary_rows_drift": "summary drift",
    "non_claim_removed": "non-claims drift",
    "validation_command_removed": "validation commands drift",
    "payload_commitment_drift": "payload commitment drift",
}


def run_mutation_cases(core_payload: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core_payload)
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated, context=context)
        except AttentionDerivedD128BlockStatementChainError as err:
            expected_error = EXPECTED_MUTATION_ERRORS.get(name)
            if expected_error is None:
                raise AttentionDerivedD128BlockStatementChainError(f"mutation error marker missing: {name}") from err
            actual_error = str(err)
            if expected_error not in actual_error:
                raise AttentionDerivedD128BlockStatementChainError(
                    f"mutation produced unexpected error: {name}: {actual_error}"
                ) from err
            cases.append({"name": name, "accepted": False, "rejected": True, "error": expected_error})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    core = build_core_payload(context)
    cases = run_mutation_cases(core, context)
    final = copy.deepcopy(core)
    final["mutation_inventory"] = list(EXPECTED_MUTATIONS)
    final["cases"] = cases
    final["case_count"] = len(cases)
    final["all_mutations_rejected"] = all(case["rejected"] and not case["accepted"] for case in cases)
    refresh_payload_commitment(final)
    validate_payload(final, context=context)
    return final


def to_tsv(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> str:
    validate_payload(payload, context=context)
    if set(payload) != FINAL_KEYS:
        raise AttentionDerivedD128BlockStatementChainError("TSV requires finalized payload")
    row = {
        "decision": payload["decision"],
        "result": payload["result"],
        "block_statement_commitment": payload["summary"]["block_statement_commitment"],
        "source_attention_outputs_commitment": payload["summary"]["source_attention_outputs_commitment"],
        "derived_input_activation_commitment": payload["summary"]["derived_input_activation_commitment"],
        "derived_output_activation_commitment": payload["summary"]["derived_output_activation_commitment"],
        "slice_count": payload["summary"]["slice_count"],
        "edge_count": payload["summary"]["edge_count"],
        "accounted_relation_rows": payload["summary"]["accounted_relation_rows"],
        "projection_mul_rows": payload["summary"]["projection_mul_rows"],
        "down_projection_mul_rows": payload["summary"]["down_projection_mul_rows"],
        "activation_lookup_rows": payload["summary"]["activation_lookup_rows"],
        "mutations_rejected": sum(1 for case in payload["cases"] if case["rejected"]),
    }
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return handle.getvalue()


def require_output_path(path: pathlib.Path, *, suffix: str | None = None) -> pathlib.Path:
    evidence_root = EVIDENCE_DIR.resolve()
    raw_candidate = path if path.is_absolute() else ROOT / path
    candidate = pathlib.Path(os.path.abspath(raw_candidate))
    try:
        relative = candidate.relative_to(evidence_root)
    except ValueError as err:
        raise AttentionDerivedD128BlockStatementChainError(
            f"output path must stay under docs/engineering/evidence: {path}"
        ) from err
    current = evidence_root
    for part in relative.parent.parts:
        current = current / part
        try:
            part_stat = current.lstat()
        except OSError as err:
            raise AttentionDerivedD128BlockStatementChainError(f"output parent must exist: {current}") from err
        if stat_module.S_ISLNK(part_stat.st_mode):
            raise AttentionDerivedD128BlockStatementChainError(f"output path must not traverse symlinks: {path}")
        if not stat_module.S_ISDIR(part_stat.st_mode):
            raise AttentionDerivedD128BlockStatementChainError(f"output parent must be a directory: {current}")
    if suffix is not None and candidate.suffix != suffix:
        raise AttentionDerivedD128BlockStatementChainError(f"output path must end with {suffix}: {path}")
    if candidate.is_symlink():
        raise AttentionDerivedD128BlockStatementChainError(f"output path must not be a symlink: {path}")
    if candidate.exists() and candidate.is_dir():
        raise AttentionDerivedD128BlockStatementChainError(f"output path must not be a directory: {path}")
    try:
        real_parent = candidate.parent.resolve(strict=True)
    except OSError as err:
        raise AttentionDerivedD128BlockStatementChainError(
            f"output parent cannot be resolved: {candidate.parent}"
        ) from err
    try:
        real_parent.relative_to(evidence_root)
    except ValueError as err:
        raise AttentionDerivedD128BlockStatementChainError(f"output parent escapes evidence dir: {candidate.parent}") from err
    return candidate


def atomic_write_text(path: pathlib.Path, text: str, *, suffix: str | None = None) -> None:
    resolved = require_output_path(path, suffix=suffix)
    if not resolved.parent.exists():
        raise AttentionDerivedD128BlockStatementChainError(f"output parent must exist: {resolved.parent}")
    parent_stat = resolved.parent.lstat()
    if not stat_module.S_ISDIR(parent_stat.st_mode):
        raise AttentionDerivedD128BlockStatementChainError(f"output parent must be a directory: {resolved.parent}")
    dir_fd = os.open(
        resolved.parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    tmp_name = f".{resolved.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    tmp_created = False
    try:
        open_parent_stat = os.fstat(dir_fd)
        if (open_parent_stat.st_dev, open_parent_stat.st_ino) != (parent_stat.st_dev, parent_stat.st_ino):
            raise AttentionDerivedD128BlockStatementChainError(f"output parent changed while opening: {resolved.parent}")
        fd = os.open(tmp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
        tmp_created = True
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(tmp_name, resolved.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        tmp_created = False
        os.fsync(dir_fd)
    except Exception:
        if tmp_created:
            try:
                os.unlink(tmp_name, dir_fd=dir_fd)
            except OSError:
                pass
        raise
    finally:
        os.close(dir_fd)


def write_outputs(
    payload: dict[str, Any],
    json_path: pathlib.Path | None = None,
    tsv_path: pathlib.Path | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> None:
    validate_payload(payload, context=context)
    if json_path is not None:
        atomic_write_text(json_path, pretty_json(payload) + "\n", suffix=".json")
    if tsv_path is not None:
        atomic_write_text(tsv_path, to_tsv(payload, context=context), suffix=".tsv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = build_context()
    payload = build_gate_result(context)
    write_outputs(payload, args.write_json, args.write_tsv, context=context)
    summary = {
        "decision": payload["decision"],
        "result": payload["result"],
        "block_statement_commitment": payload["summary"]["block_statement_commitment"],
        "derived_output_activation_commitment": payload["summary"]["derived_output_activation_commitment"],
        "slice_count": payload["summary"]["slice_count"],
        "edge_count": payload["summary"]["edge_count"],
        "accounted_relation_rows": payload["summary"]["accounted_relation_rows"],
        "mutations_rejected": sum(1 for case in payload["cases"] if case["rejected"]),
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
