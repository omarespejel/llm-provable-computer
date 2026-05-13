#!/usr/bin/env python3
"""Build the one-transformer-block surface scorecard without overclaiming."""

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
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINEERING_EVIDENCE = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = ENGINEERING_EVIDENCE / "zkai-one-transformer-block-surface-2026-05.json"
TSV_OUT = ENGINEERING_EVIDENCE / "zkai-one-transformer-block-surface-2026-05.tsv"

FUSION_MECHANISM = ENGINEERING_EVIDENCE / "zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.json"
D64_BLOCK_RECEIPT = ENGINEERING_EVIDENCE / "zkai-d64-block-receipt-composition-gate-2026-05.json"
D128_BLOCK_RECEIPT = ENGINEERING_EVIDENCE / "zkai-d128-block-receipt-composition-gate-2026-05.json"
ATTENTION_DERIVED_D128_CHAIN = (
    ENGINEERING_EVIDENCE / "zkai-attention-derived-d128-block-statement-chain-2026-05.json"
)
COMPETITOR_MATRIX = ENGINEERING_EVIDENCE / "zkai-may2026-competitor-metric-matrix.json"
EXPECTED_ATTENTION_DERIVED_D128_BLOCK_STATEMENT_COMMITMENT = (
    "blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5"
)

SCHEMA = "zkai-one-transformer-block-surface-v1"
DECISION = "GO_ONE_TRANSFORMER_BLOCK_SURFACE_NO_GO_MATCHED_LAYER_PROOF"
CLAIM_BOUNDARY = (
    "SOURCE_BACKED_STARK_NATIVE_ATTENTION_AND_RMSNORM_SWIGLU_RESIDUAL_BLOCK_SURFACE_"
    "NOT_SINGLE_RECURSIVE_PROOF_OBJECT_NOT_MATCHED_NANOZK_BENCHMARK_NOT_FULL_INFERENCE"
)
MAX_SOURCE_BYTES = 16 * 1024 * 1024

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_one_transformer_block_surface_gate.py --write-json docs/engineering/evidence/zkai-one-transformer-block-surface-2026-05.json --write-tsv docs/engineering/evidence/zkai-one-transformer-block-surface-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_one_transformer_block_surface_gate.py scripts/tests/test_zkai_one_transformer_block_surface_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_one_transformer_block_surface_gate",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

NON_CLAIMS = [
    "not a matched benchmark against NANOZK or Jolt Atlas",
    "not one recursive or compressed proof object for a full transformer block",
    "not proof-size or verifier-time evidence for a local d128 layer proof",
    "not exact real-valued Softmax, LayerNorm, or GELU",
    "not full autoregressive inference",
    "not production-ready",
]


class OneTransformerBlockSurfaceError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as err:
        raise OneTransformerBlockSurfaceError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise OneTransformerBlockSurfaceError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def read_source_bytes(path: pathlib.Path, label: str) -> bytes:
    root = ROOT.resolve()
    candidate = pathlib.Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as err:
        raise OneTransformerBlockSurfaceError(f"source path must stay inside repository: {path}") from err

    current = root
    pre_stat = None
    try:
        for part in relative.parts:
            current = current / part
            part_stat = current.lstat()
            if stat_module.S_ISLNK(part_stat.st_mode):
                raise OneTransformerBlockSurfaceError(f"source path must not traverse symlinks: {path}")
            pre_stat = part_stat
        if pre_stat is None or not stat_module.S_ISREG(pre_stat.st_mode):
            raise OneTransformerBlockSurfaceError(f"source path must be a repo file: {path}")
        fd = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise OneTransformerBlockSurfaceError(f"source path must be a repo file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise OneTransformerBlockSurfaceError(f"source path changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(MAX_SOURCE_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise OneTransformerBlockSurfaceError(f"failed to read {label} source {path}: {err}") from err
    if len(raw) > MAX_SOURCE_BYTES:
        raise OneTransformerBlockSurfaceError(
            f"source exceeds max size: got at least {len(raw)} bytes, limit {MAX_SOURCE_BYTES}"
        )
    return raw


def _source_from_bytes(path: pathlib.Path, kind: str, raw: bytes) -> dict[str, str]:
    return {
        "kind": kind,
        "path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _parse_json_bytes(path: pathlib.Path, raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise OneTransformerBlockSurfaceError(f"failed to load JSON source {path}: {err}") from err
    if not isinstance(payload, dict):
        raise OneTransformerBlockSurfaceError(f"JSON source must be object: {path}")
    return payload


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return _parse_json_bytes(path, read_source_bytes(path, "JSON"))


def _dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OneTransformerBlockSurfaceError(f"{field} must be object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise OneTransformerBlockSurfaceError(f"{field} must be list")
    return value


def _string_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> str:
    value: Any = payload
    for key in path:
        value = _dict(value, ".".join(path)).get(key)
    if not isinstance(value, str):
        raise OneTransformerBlockSurfaceError(f"{label} must be string")
    return value


def _int_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> int:
    value: Any = payload
    for key in path:
        value = _dict(value, ".".join(path)).get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise OneTransformerBlockSurfaceError(f"{label} must be integer")
    return value


def _float_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> float:
    value: Any = payload
    for key in path:
        value = _dict(value, ".".join(path)).get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise OneTransformerBlockSurfaceError(f"{label} must be numeric")
    value_float = float(value)
    if not (0 <= value_float <= 1):
        raise OneTransformerBlockSurfaceError(f"{label} must be between 0 and 1")
    return value_float


def _nanozk_block_row(matrix: dict[str, Any]) -> dict[str, Any]:
    if _string_field(matrix, ("schema",), "competitor matrix schema") != "zkai-may2026-competitor-metric-matrix-v1":
        raise OneTransformerBlockSurfaceError("competitor matrix schema drift")
    if (
        _string_field(matrix, ("decision",), "competitor matrix decision")
        != "GO_SOURCE_BACKED_COMPETITOR_MATRIX_NO_GO_MATCHED_BENCHMARK_CLAIMS"
    ):
        raise OneTransformerBlockSurfaceError("competitor matrix decision drift")
    rows = _list(matrix.get("external_rows"), "competitor matrix external_rows")
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("system") == "NANOZK"
        and row.get("workload_label") == "Transformer block proof"
        and row.get("workload_scope") == "Per-layer block proof"
    ]
    if len(matches) != 1:
        raise OneTransformerBlockSurfaceError("expected one NANOZK transformer block row")
    row = matches[0]
    expected = {
        "prove_seconds": "6.3",
        "verify_seconds": "0.023",
        "proof_size_reported": "6.9 KB",
        "backend_family": "Halo2 IPA SNARK + lookups",
        "model_or_dims": "GPT-2-scale block; d=768; dff=3072",
    }
    for key, value in expected.items():
        if row.get(key) != value:
            raise OneTransformerBlockSurfaceError(f"NANOZK row drift: {key}")
    return row


def _validate_block_receipt(payload: dict[str, Any], width: int) -> dict[str, Any]:
    schema = f"zkai-d{width}-block-receipt-composition-gate-v1"
    decision = f"GO_D{width}_BLOCK_RECEIPT_COMPOSITION_GATE"
    if _string_field(payload, ("schema",), f"d{width} schema") != schema:
        raise OneTransformerBlockSurfaceError(f"d{width} block receipt schema drift")
    if _string_field(payload, ("decision",), f"d{width} decision") != decision:
        raise OneTransformerBlockSurfaceError(f"d{width} block receipt decision drift")
    if payload.get("all_mutations_rejected") is not True:
        raise OneTransformerBlockSurfaceError(f"d{width} block receipt mutations are not all rejected")
    summary = _dict(payload.get("summary"), f"d{width} summary")
    slice_count = _int_field(payload, ("summary", "slice_count"), f"d{width} slice count")
    total_rows = _int_field(payload, ("summary", "total_checked_rows"), f"d{width} checked rows")
    mutations = _int_field(payload, ("summary", "mutations_rejected"), f"d{width} mutations rejected")
    mutation_cases = _int_field(payload, ("summary", "mutation_cases"), f"d{width} mutation cases")
    if slice_count != 6:
        raise OneTransformerBlockSurfaceError(f"d{width} slice count drift")
    if total_rows <= 0:
        raise OneTransformerBlockSurfaceError(f"d{width} checked rows must be positive")
    if mutations != mutation_cases:
        raise OneTransformerBlockSurfaceError(f"d{width} mutation rejection count drift")
    return summary


def _validate_attention_derived_d128_chain(payload: dict[str, Any]) -> dict[str, Any]:
    if (
        _string_field(payload, ("schema",), "attention-derived d128 chain schema")
        != "zkai-attention-derived-d128-block-statement-chain-gate-v1"
    ):
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain schema drift")
    if (
        _string_field(payload, ("decision",), "attention-derived d128 chain decision")
        != "GO_ATTENTION_DERIVED_D128_BLOCK_STATEMENT_CHAIN"
    ):
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain decision drift")
    if (
        _string_field(payload, ("result",), "attention-derived d128 chain result")
        != "GO_COMMITTED_SLICE_CHAIN_NO_GO_SINGLE_COMPOSED_PROOF"
    ):
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain result drift")
    if payload.get("all_mutations_rejected") is not True:
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain mutations are not all rejected")
    summary = _dict(payload.get("summary"), "attention-derived d128 chain summary")
    if summary.get("all_edges_match") is not True:
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain edges do not all match")
    if _int_field(payload, ("summary", "slice_count"), "attention-derived d128 chain slice count") != 6:
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain slice count drift")
    if _int_field(payload, ("summary", "edge_count"), "attention-derived d128 chain edge count") != 11:
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain edge count drift")
    if _int_field(payload, ("case_count",), "attention-derived d128 chain mutations") != 19:
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain mutation count drift")
    if _int_field(payload, ("summary", "accounted_relation_rows"), "attention-derived d128 chain rows") <= 0:
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain rows must be positive")
    top_statement = _string_field(
        payload,
        ("block_statement_commitment",),
        "attention-derived d128 chain block statement commitment",
    )
    summary_statement = _string_field(
        payload,
        ("summary", "block_statement_commitment"),
        "attention-derived d128 chain summary block statement commitment",
    )
    if top_statement != EXPECTED_ATTENTION_DERIVED_D128_BLOCK_STATEMENT_COMMITMENT:
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain block statement commitment drift")
    if summary_statement != top_statement:
        raise OneTransformerBlockSurfaceError("attention-derived d128 chain summary commitment drift")
    return summary


def _component_rows(
    fusion: dict[str, Any],
    d64: dict[str, Any],
    d128: dict[str, Any],
    attention_derived_d128: dict[str, Any],
    matrix: dict[str, Any],
) -> list[dict[str, Any]]:
    if _string_field(fusion, ("schema",), "fusion schema") != "zkai-attention-kv-stwo-fusion-mechanism-ablation-v1":
        raise OneTransformerBlockSurfaceError("fusion schema drift")
    if (
        _string_field(fusion, ("decision",), "fusion decision")
        != "GO_STARK_NATIVE_FUSION_MECHANISM_ABLATION_FOR_PAPER_ARCHITECTURE_CLAIM"
    ):
        raise OneTransformerBlockSurfaceError("fusion decision drift")
    if fusion.get("all_mutations_rejected") is not True:
        raise OneTransformerBlockSurfaceError("fusion mutations are not all rejected")
    d64_summary = _validate_block_receipt(d64, 64)
    d128_summary = _validate_block_receipt(d128, 128)
    attention_derived_summary = _validate_attention_derived_d128_chain(attention_derived_d128)
    nanozk = _nanozk_block_row(matrix)

    fused_savings = _int_field(fusion, ("route_matrix", "fused_savings_bytes_total"), "fusion savings")
    fused_proof_bytes = _int_field(fusion, ("route_matrix", "fused_proof_size_bytes_total"), "fusion proof bytes")
    matched_profiles = _int_field(fusion, ("route_matrix", "matched_profiles_checked"), "matched profiles")
    opening_share = _float_field(fusion, ("section_delta", "opening_bucket_savings_share"), "opening share")
    if fused_savings <= 0 or fused_proof_bytes <= 0 or matched_profiles <= 0:
        raise OneTransformerBlockSurfaceError("fusion metrics must be positive")

    return [
        {
            "surface": "attention/Softmax-table fused proof component",
            "subsystem": "attention",
            "local_status": "GO_STARK_NATIVE_FUSION_MECHANISM",
            "metric": "matched fused-vs-source-plus-sidecar saving",
            "value": fused_savings,
            "unit": "json_proof_bytes",
            "support": f"{matched_profiles} matched profiles; opening/decommitment saving share {opening_share:.6f}",
            "comparison_status": "LOCAL_MECHANISM_EVIDENCE_NOT_LAYERWISE_BENCHMARK",
        },
        {
            "surface": "d64 RMSNorm/SwiGLU/residual receipt chain",
            "subsystem": "bounded_mlp_substitute",
            "local_status": "GO_STATEMENT_BOUND_RECEIPT_CHAIN",
            "metric": "checked slice rows",
            "value": d64_summary["total_checked_rows"],
            "unit": "rows",
            "support": f"{d64_summary['slice_count']} slices; {d64_summary['mutations_rejected']} / {d64_summary['mutation_cases']} mutations rejected",
            "comparison_status": "LOCAL_RECEIPT_CHAIN_NOT_SINGLE_PROOF_OBJECT",
        },
        {
            "surface": "d128 RMSNorm/SwiGLU/residual receipt chain",
            "subsystem": "bounded_mlp_substitute",
            "local_status": "GO_STATEMENT_BOUND_RECEIPT_CHAIN_NO_GO_PROOF_SIZE_BENCHMARK",
            "metric": "checked slice rows",
            "value": d128_summary["total_checked_rows"],
            "unit": "rows",
            "support": f"{d128_summary['slice_count']} slices; {d128_summary['mutations_rejected']} / {d128_summary['mutation_cases']} mutations rejected; proof-size benchmark still not claimed",
            "comparison_status": "LOCAL_RECEIPT_CHAIN_NOT_RECURSIVE_LAYER_PROOF",
        },
        {
            "surface": "attention-derived d128 block statement chain",
            "subsystem": "attention_to_block_boundary",
            "local_status": "GO_ATTENTION_DERIVED_STATEMENT_CHAIN_NO_GO_COMPOSED_PROOF",
            "metric": "accounted relation rows bound under one statement commitment",
            "value": attention_derived_summary["accounted_relation_rows"],
            "unit": "rows",
            "support": (
                f"{attention_derived_summary['slice_count']} slices; "
                f"{attention_derived_summary['edge_count']} edges; "
                "19 / 19 mutations rejected; "
                f"statement {attention_derived_summary['block_statement_commitment']}"
            ),
            "comparison_status": "LOCAL_STATEMENT_CHAIN_NOT_SINGLE_PROOF_OBJECT",
        },
        {
            "surface": "NANOZK transformer block context",
            "subsystem": "external_context",
            "local_status": "SOURCE_BACKED_EXTERNAL_CONTEXT",
            "metric": "reported transformer block proof",
            "value": nanozk["proof_size_reported"],
            "unit": "reported_proof_size",
            "support": f"{nanozk['prove_seconds']}s prove; {nanozk['verify_seconds']}s verify; {nanozk['model_or_dims']}",
            "comparison_status": "CONTEXT_ONLY_NOT_LOCAL_REPRODUCTION",
        },
    ]


def build_payload_uncommitted() -> dict[str, Any]:
    fusion_raw = read_source_bytes(FUSION_MECHANISM, "fusion mechanism JSON")
    d64_raw = read_source_bytes(D64_BLOCK_RECEIPT, "d64 block receipt JSON")
    d128_raw = read_source_bytes(D128_BLOCK_RECEIPT, "d128 block receipt JSON")
    attention_derived_raw = read_source_bytes(ATTENTION_DERIVED_D128_CHAIN, "attention-derived d128 chain JSON")
    matrix_raw = read_source_bytes(COMPETITOR_MATRIX, "competitor matrix JSON")
    fusion = _parse_json_bytes(FUSION_MECHANISM, fusion_raw)
    d64 = _parse_json_bytes(D64_BLOCK_RECEIPT, d64_raw)
    d128 = _parse_json_bytes(D128_BLOCK_RECEIPT, d128_raw)
    attention_derived = _parse_json_bytes(ATTENTION_DERIVED_D128_CHAIN, attention_derived_raw)
    matrix = _parse_json_bytes(COMPETITOR_MATRIX, matrix_raw)
    component_rows = _component_rows(fusion, d64, d128, attention_derived, matrix)
    d64_row = next(row for row in component_rows if row["surface"].startswith("d64 "))
    d128_row = next(row for row in component_rows if row["surface"].startswith("d128 "))
    attention_derived_row = next(
        row for row in component_rows if row["surface"] == "attention-derived d128 block statement chain"
    )
    attention_derived_summary = _validate_attention_derived_d128_chain(attention_derived)
    attention_row = next(row for row in component_rows if row["subsystem"] == "attention")
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": [
            _source_from_bytes(FUSION_MECHANISM, "local_attention_fusion_json", fusion_raw),
            _source_from_bytes(D64_BLOCK_RECEIPT, "local_d64_block_receipt_json", d64_raw),
            _source_from_bytes(D128_BLOCK_RECEIPT, "local_d128_block_receipt_json", d128_raw),
            _source_from_bytes(
                ATTENTION_DERIVED_D128_CHAIN,
                "local_attention_derived_d128_statement_chain_json",
                attention_derived_raw,
            ),
            _source_from_bytes(COMPETITOR_MATRIX, "source_backed_competitor_matrix_json", matrix_raw),
        ],
        "component_rows": component_rows,
        "block_component_map": [
            {
                "component": "attention",
                "checked_surface": "bounded Softmax-table attention with fused LogUp membership",
                "honest_scope": "STARK-native proof architecture mechanism, not exact real-valued Softmax",
            },
            {
                "component": "normalization",
                "checked_surface": "RMSNorm receipt slices",
                "honest_scope": "RMSNorm substitute for LayerNorm in this block surface",
            },
            {
                "component": "mlp_nonlinearity",
                "checked_surface": "bounded SiLU/SwiGLU activation and multiplication rows",
                "honest_scope": "GELU-style bounded nonlinearity substitute, not exact GELU",
            },
            {
                "component": "residual",
                "checked_surface": "residual-add receipt slices",
                "honest_scope": "statement-bound residual transition, not full autoregressive inference",
            },
            {
                "component": "attention_to_block_boundary",
                "checked_surface": "attention output through d128 block-output activation under one statement chain",
                "honest_scope": "one verifier-facing statement chain, not one composed proof object",
            },
        ],
        "summary": {
            "breakthrough_status": "credible_architecture_path_not_field_breakthrough",
            "strongest_claim": "STARK-native attention fusion and an attention-derived d128 RMSNorm/SwiGLU/residual statement chain now sit in one source-backed block-surface scorecard.",
            "go_result": "GO for one-block architecture surface accounting with an attention-derived d128 statement chain",
            "no_go_result": "NO-GO for matched NANOZK-style single layer proof, proof-size benchmark, verifier-time benchmark, or full inference",
            "attention_fusion_saving_bytes": attention_row["value"],
            "d64_checked_rows": d64_row["value"],
            "d128_checked_rows": d128_row["value"],
            "attention_derived_d128_statement_chain_rows": attention_derived_row["value"],
            "attention_derived_d128_statement_chain_edges": attention_derived_summary["edge_count"],
            "attention_derived_d128_block_statement_commitment": attention_derived_summary[
                "block_statement_commitment"
            ],
            "d128_over_d64_checked_row_ratio": round(float(d128_row["value"]) / float(d64_row["value"]), 6),
        },
        "next_required_work": [
            "turn the attention-derived statement chain into a proof-object composition or compression experiment",
            "add proof-carrying aggregation or recursion if claiming one proof object",
            "add median-of-5 timing only after the block proof surface is stable",
            "keep NANOZK/Jolt comparisons source-backed and non-matched until dimensions, semantics, hardware, and timing policy match",
        ],
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }


def build_payload() -> dict[str, Any]:
    payload = build_payload_uncommitted()
    expected = copy.deepcopy(payload)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload, expected=expected)
    return payload


def validate_payload(payload: dict[str, Any], *, expected: dict[str, Any] | None = None) -> None:
    if not isinstance(payload, dict):
        raise OneTransformerBlockSurfaceError("payload must be object")
    base = expected if expected is not None else build_payload_uncommitted()
    candidate = {key: value for key, value in payload.items() if key != "payload_commitment"}
    if candidate != base:
        if payload.get("schema") != SCHEMA:
            raise OneTransformerBlockSurfaceError("schema drift")
        if payload.get("decision") != DECISION:
            raise OneTransformerBlockSurfaceError("decision drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise OneTransformerBlockSurfaceError("claim boundary drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise OneTransformerBlockSurfaceError("non_claims drift")
        raise OneTransformerBlockSurfaceError("payload drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise OneTransformerBlockSurfaceError("payload commitment drift")


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(
        [
            "surface",
            "subsystem",
            "local_status",
            "metric",
            "value",
            "unit",
            "comparison_status",
            "support",
        ]
    )
    for row in payload["component_rows"]:
        writer.writerow(
            [
                row["surface"],
                row["subsystem"],
                row["local_status"],
                row["metric"],
                row["value"],
                row["unit"],
                row["comparison_status"],
                row["support"],
            ]
        )
    return out.getvalue()


def _assert_no_repo_symlink_components(path: pathlib.Path, label: str) -> None:
    absolute = path if path.is_absolute() else ROOT / path
    try:
        relative = absolute.relative_to(ROOT)
    except ValueError as err:
        raise OneTransformerBlockSurfaceError(f"{label} must stay inside repository") from err
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise OneTransformerBlockSurfaceError(f"{label} must not include symlink components")


def _assert_output_path(path: pathlib.Path, label: str) -> pathlib.Path:
    raw = str(path).replace("\\", "/")
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise OneTransformerBlockSurfaceError(f"{label} must be repo-relative")
    if pathlib.PurePosixPath(*relative.parts[:3]) != pathlib.PurePosixPath("docs/engineering/evidence"):
        raise OneTransformerBlockSurfaceError(f"{label} must stay under docs/engineering/evidence")
    full = ROOT.joinpath(*relative.parts)
    _assert_no_repo_symlink_components(full.parent, label)
    if full.is_symlink():
        raise OneTransformerBlockSurfaceError(f"{label} must not include symlink components")
    return full


def _directory_identity(path: pathlib.Path, label: str) -> tuple[int, int]:
    try:
        path_stat = path.lstat()
    except OSError as err:
        raise OneTransformerBlockSurfaceError(f"{label} parent directory is unavailable: {err}") from err
    if stat_module.S_ISLNK(path_stat.st_mode) or not stat_module.S_ISDIR(path_stat.st_mode):
        raise OneTransformerBlockSurfaceError(f"{label} parent must be a real directory")
    return (path_stat.st_dev, path_stat.st_ino)


def _assert_directory_identity(path: pathlib.Path, identity: tuple[int, int], label: str) -> None:
    _assert_no_repo_symlink_components(path, label)
    if _directory_identity(path, label) != identity:
        raise OneTransformerBlockSurfaceError(f"{label} parent directory changed while writing")


def _open_stable_directory(path: pathlib.Path, label: str) -> tuple[int, tuple[int, int]]:
    _assert_no_repo_symlink_components(path, label)
    path.mkdir(parents=True, exist_ok=True)
    _assert_no_repo_symlink_components(path, label)
    identity = _directory_identity(path, label)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as err:
        raise OneTransformerBlockSurfaceError(f"failed to open {label} parent directory: {err}") from err
    try:
        fd_stat = os.fstat(fd)
        if not stat_module.S_ISDIR(fd_stat.st_mode):
            raise OneTransformerBlockSurfaceError(f"{label} parent must be a real directory")
        if (fd_stat.st_dev, fd_stat.st_ino) != identity:
            raise OneTransformerBlockSurfaceError(f"{label} parent directory changed while opening")
    except Exception:
        os.close(fd)
        raise
    return fd, identity


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    outputs = []
    if json_path is not None:
        outputs.append((_assert_output_path(json_path, "json output path"), (pretty_json(payload) + "\n").encode("utf-8")))
    if tsv_path is not None:
        outputs.append((_assert_output_path(tsv_path, "tsv output path"), to_tsv(payload).encode("utf-8")))
    if not outputs:
        raise OneTransformerBlockSurfaceError("at least one explicit output path is required")
    if len(outputs) == 2 and os.path.abspath(outputs[0][0]).casefold() == os.path.abspath(outputs[1][0]).casefold():
        raise OneTransformerBlockSurfaceError("json and tsv output paths must differ")

    temps: list[tuple[pathlib.Path, str, int, tuple[int, int]]] = []
    replaced: list[pathlib.Path] = []
    original_bytes: dict[pathlib.Path, bytes | None] = {}
    write_error: Exception | None = None
    rollback_errors: list[str] = []

    def write_temp(path: pathlib.Path, contents: bytes, label: str) -> tuple[pathlib.Path, str, int, tuple[int, int]]:
        parent_fd, identity = _open_stable_directory(path.parent, label)
        temp_name: str | None = None
        file_fd: int | None = None
        try:
            _assert_directory_identity(path.parent, identity, label)
            if path.is_symlink():
                raise OneTransformerBlockSurfaceError(f"{label} must not include symlink components")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            for _ in range(100):
                candidate = f".{path.name}.{secrets.token_hex(8)}.tmp"
                try:
                    file_fd = os.open(candidate, flags, 0o600, dir_fd=parent_fd)
                    temp_name = candidate
                    break
                except FileExistsError:
                    continue
            if file_fd is None or temp_name is None:
                raise OneTransformerBlockSurfaceError(f"failed to create unique temporary output for {label}")
            with os.fdopen(file_fd, "wb") as handle:
                file_fd = None
                handle.write(contents)
                handle.flush()
                os.fsync(handle.fileno())
            _assert_directory_identity(path.parent, identity, label)
            return (path.parent / temp_name, temp_name, parent_fd, identity)
        except Exception:
            if file_fd is not None:
                os.close(file_fd)
            if temp_name is not None:
                try:
                    os.unlink(temp_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
            os.close(parent_fd)
            raise

    def replace_temp(temp: tuple[pathlib.Path, str, int, tuple[int, int]], path: pathlib.Path, label: str) -> None:
        _tmp_path, temp_name, parent_fd, identity = temp
        _assert_directory_identity(path.parent, identity, label)
        if path.is_symlink():
            raise OneTransformerBlockSurfaceError(f"{label} must not include symlink components")
        os.replace(temp_name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        _assert_directory_identity(path.parent, identity, label)

    def rollback_replace(path: pathlib.Path, contents: bytes) -> None:
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        tmp = write_temp(path, contents, "rollback output path")
        temps.append(tmp)
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        replace_temp(tmp, path, "rollback output path")

    def rollback_remove(path: pathlib.Path) -> None:
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        parent_fd, identity = _open_stable_directory(path.parent, "rollback output path")
        try:
            _assert_directory_identity(path.parent, identity, "rollback output path")
            if path.is_symlink():
                raise OneTransformerBlockSurfaceError("rollback output path must not include symlink components")
            try:
                os.unlink(path.name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            _assert_directory_identity(path.parent, identity, "rollback output path")
        finally:
            os.close(parent_fd)

    try:
        try:
            for path, contents in outputs:
                original_bytes[path] = read_source_bytes(path, "existing output") if path.exists() else None
                temps.append(write_temp(path, contents, "output path"))
            for temp, (path, _contents) in zip(temps, outputs, strict=True):
                replace_temp(temp, path, "output path")
                replaced.append(path)
        except (OneTransformerBlockSurfaceError, OSError) as err:
            write_error = err
            raise OneTransformerBlockSurfaceError(f"failed to write output path: {err}") from err
    finally:
        if write_error is not None:
            for path in reversed(replaced):
                original = original_bytes.get(path)
                try:
                    if original is None:
                        rollback_remove(path)
                    else:
                        rollback_replace(path, original)
                except (OneTransformerBlockSurfaceError, OSError) as err:
                    rollback_errors.append(f"{path}: {err}")
        for temp in temps:
            _tmp_path, temp_name, parent_fd, _identity = temp
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            finally:
                os.close(parent_fd)
        if rollback_errors:
            raise OneTransformerBlockSurfaceError(
                "failed to roll back output path after write error: "
                + "; ".join(rollback_errors)
                + f"; original write error: {write_error}"
            ) from write_error


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
        else:
            print(pretty_json(payload))
    except OneTransformerBlockSurfaceError as err:
        print(f"one transformer block surface gate failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
