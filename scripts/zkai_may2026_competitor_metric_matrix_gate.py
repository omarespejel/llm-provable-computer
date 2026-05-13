#!/usr/bin/env python3
"""Build the May 2026 zkML competitor metric matrix without overclaiming."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import os
import pathlib
import secrets
import stat as stat_module
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINEERING_EVIDENCE = ROOT / "docs" / "engineering" / "evidence"
PAPER_EVIDENCE = ROOT / "docs" / "paper" / "evidence"
PUBLISHED_ZKML_NUMBERS = PAPER_EVIDENCE / "published-zkml-numbers-2026-04.tsv"
FUSION_MECHANISM = ENGINEERING_EVIDENCE / "zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.json"
D64_BLOCK_RECEIPT = ENGINEERING_EVIDENCE / "zkai-d64-block-receipt-composition-gate-2026-05.json"
D128_TARGET = ENGINEERING_EVIDENCE / "zkai-d128-layerwise-comparator-target-2026-05.json"
JSON_OUT = ENGINEERING_EVIDENCE / "zkai-may2026-competitor-metric-matrix.json"
TSV_OUT = ENGINEERING_EVIDENCE / "zkai-may2026-competitor-metric-matrix.tsv"

SCHEMA = "zkai-may2026-competitor-metric-matrix-v1"
DECISION = "GO_SOURCE_BACKED_COMPETITOR_MATRIX_NO_GO_MATCHED_BENCHMARK_CLAIMS"
CLAIM_BOUNDARY = (
    "SOURCE_BACKED_MAY2026_ZKML_COMPETITOR_MATRIX_WITH_LOCAL_STWO_ATTENTION_FUSION_AND_"
    "TRANSFORMER_BLOCK_TARGET_CONTEXT_NOT_A_MATCHED_PUBLIC_BENCHMARK_NOT_FULL_INFERENCE"
)
MAX_SOURCE_BYTES = 16 * 1024 * 1024

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_may2026_competitor_metric_matrix_gate.py --write-json docs/engineering/evidence/zkai-may2026-competitor-metric-matrix.json --write-tsv docs/engineering/evidence/zkai-may2026-competitor-metric-matrix.tsv",
    "python3 -m unittest scripts.tests.test_zkai_may2026_competitor_metric_matrix_gate",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

NON_CLAIMS = [
    "not a matched benchmark against NANOZK, Jolt Atlas, EZKL, DeepProve-1, or RISC Zero",
    "not a local d128 proof result",
    "not proof-size or verifier-time evidence for a local d128 transformer block",
    "not full transformer inference",
    "not exact real-valued Softmax",
    "not production-ready",
]

EXPECTED_EXTERNAL_ROWS = {
    ("NANOZK", "Transformer block proof", "Per-layer block proof"): {
        "prove_seconds": "6.3",
        "verify_seconds": "0.023",
        "proof_size_reported": "6.9 KB",
    },
    ("NANOZK", "GPT-2-Small full model", "Sequential 12-layer end-to-end"): {
        "prove_seconds": "516",
        "verify_seconds": "NA",
        "proof_size_reported": "NA",
    },
    ("Jolt Atlas", "NanoGPT proof", "End-to-end"): {
        "prove_seconds": "14",
        "verify_seconds": "0.517",
        "proof_size_reported": "NA",
    },
    ("Jolt Atlas", "GPT-2 proof", "End-to-end"): {
        "prove_seconds": "38",
        "verify_seconds": "NA",
        "proof_size_reported": "NA",
    },
    ("EZKL (reported by Jolt Atlas)", "NanoGPT proof", "End-to-end"): {
        "prove_seconds": "237",
        "verify_seconds": "0.34",
        "proof_size_reported": "NA",
    },
}

REQUIRED_PUBLISHED_COLUMNS = {
    "system",
    "source_kind",
    "source_url",
    "source_locator",
    "backend_family",
    "workload_label",
    "workload_scope",
    "model_or_dims",
    "prove_seconds",
    "verify_seconds",
    "proof_size_reported",
    "setup_or_keygen_seconds",
    "hardware",
    "notes",
}


class CompetitorMetricMatrixError(ValueError):
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
        raise CompetitorMetricMatrixError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise CompetitorMetricMatrixError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def read_source_bytes(path: pathlib.Path, label: str) -> bytes:
    root = ROOT.resolve()
    candidate = pathlib.Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as err:
        raise CompetitorMetricMatrixError(f"source path must stay inside repository: {path}") from err

    current = root
    pre_stat = None
    try:
        for part in relative.parts:
            current = current / part
            part_stat = current.lstat()
            if stat_module.S_ISLNK(part_stat.st_mode):
                raise CompetitorMetricMatrixError(f"source path must not traverse symlinks: {path}")
            pre_stat = part_stat
        if pre_stat is None or not stat_module.S_ISREG(pre_stat.st_mode):
            raise CompetitorMetricMatrixError(f"source path must be a repo file: {path}")
        fd = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise CompetitorMetricMatrixError(f"source path must be a repo file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise CompetitorMetricMatrixError(f"source path changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(MAX_SOURCE_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise CompetitorMetricMatrixError(f"failed to read {label} source {path}: {err}") from err
    if len(raw) > MAX_SOURCE_BYTES:
        raise CompetitorMetricMatrixError(
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
        raise CompetitorMetricMatrixError(f"failed to load JSON source {path}: {err}") from err
    if not isinstance(payload, dict):
        raise CompetitorMetricMatrixError(f"JSON source must be object: {path}")
    return payload


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return _parse_json_bytes(path, read_source_bytes(path, "JSON"))


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _parse_tsv_bytes(path: pathlib.Path, raw: bytes) -> list[dict[str, str]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as err:
        raise CompetitorMetricMatrixError(f"failed to load TSV source {path}: {err}") from err
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    fieldname_list = reader.fieldnames or []
    duplicate_fields = sorted({field for field in fieldname_list if fieldname_list.count(field) > 1})
    if duplicate_fields:
        raise CompetitorMetricMatrixError(f"TSV source has duplicate columns: {duplicate_fields}")
    fieldnames = set(fieldname_list)
    missing = REQUIRED_PUBLISHED_COLUMNS - fieldnames
    if missing:
        raise CompetitorMetricMatrixError(f"TSV source missing columns: {sorted(missing)}")
    extra = fieldnames - REQUIRED_PUBLISHED_COLUMNS
    if extra:
        raise CompetitorMetricMatrixError(f"TSV source has extra columns: {sorted(extra)}")
    rows = list(reader)
    for index, row in enumerate(rows, start=2):
        if None in row:
            raise CompetitorMetricMatrixError(f"TSV source row {index} has extra cells")
    if not rows:
        raise CompetitorMetricMatrixError(f"TSV source must not be empty: {path}")
    return rows


def load_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    return _parse_tsv_bytes(path, read_source_bytes(path, "TSV"))


def _find_external_row(
    rows: list[dict[str, str]], system: str, workload_label: str, workload_scope: str
) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if row.get("system") == system
        and row.get("workload_label") == workload_label
        and row.get("workload_scope") == workload_scope
    ]
    if len(matches) != 1:
        raise CompetitorMetricMatrixError(
            f"expected one published row for {system} / {workload_label} / {workload_scope}"
        )
    row = matches[0]
    expected = EXPECTED_EXTERNAL_ROWS[(system, workload_label, workload_scope)]
    for key, value in expected.items():
        if row[key] != value:
            raise CompetitorMetricMatrixError(f"published metric drift for {system} / {workload_label}: {key}")
    return row


def _tsv_cell(row: dict[str, str], key: str, label: str) -> str:
    value = row.get(key)
    if value is None:
        raise CompetitorMetricMatrixError(f"{label} missing TSV column: {key}")
    return value


def _external_rows(published: list[dict[str, str]]) -> list[dict[str, Any]]:
    selected = []
    for system, workload, scope in EXPECTED_EXTERNAL_ROWS:
        row = _find_external_row(published, system, workload, scope)
        selected.append(
            {
                "system": _tsv_cell(row, "system", system),
                "source_url": _tsv_cell(row, "source_url", system),
                "source_locator": _tsv_cell(row, "source_locator", system),
                "backend_family": _tsv_cell(row, "backend_family", system),
                "workload_label": _tsv_cell(row, "workload_label", system),
                "workload_scope": _tsv_cell(row, "workload_scope", system),
                "model_or_dims": _tsv_cell(row, "model_or_dims", system),
                "prove_seconds": _tsv_cell(row, "prove_seconds", system),
                "verify_seconds": _tsv_cell(row, "verify_seconds", system),
                "proof_size_reported": _tsv_cell(row, "proof_size_reported", system),
                "setup_or_keygen_seconds": _tsv_cell(row, "setup_or_keygen_seconds", system),
                "hardware": _tsv_cell(row, "hardware", system),
                "comparison_status": "SOURCE_BACKED_CONTEXT_ONLY_NOT_LOCAL_REPRODUCTION",
            }
        )
    return selected


def _source_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> Any:
    current: Any = payload
    for part in path:
        if not isinstance(current, dict) or part not in current:
            raise CompetitorMetricMatrixError(f"{label} missing or malformed")
        current = current[part]
    return current


def _integer_source_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> int:
    value = _source_field(payload, path, label)
    if type(value) is not int:
        raise CompetitorMetricMatrixError(f"{label} must be integer")
    return value


def _numeric_source_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> float:
    value = _source_field(payload, path, label)
    if type(value) not in (int, float):
        raise CompetitorMetricMatrixError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise CompetitorMetricMatrixError(f"{label} must be finite")
    return number


def _share_source_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> float:
    number = _numeric_source_field(payload, path, label)
    if number < 0.0 or number > 1.0:
        raise CompetitorMetricMatrixError(f"{label} must be between 0 and 1")
    return number


def _string_source_field(payload: dict[str, Any], path: tuple[str, ...], label: str) -> str:
    value = _source_field(payload, path, label)
    if not isinstance(value, str):
        raise CompetitorMetricMatrixError(f"{label} must be string")
    return value


def _local_rows(fusion: dict[str, Any], d64: dict[str, Any], d128: dict[str, Any]) -> list[dict[str, Any]]:
    if _string_source_field(fusion, ("decision",), "fusion decision") != (
        "GO_STARK_NATIVE_FUSION_MECHANISM_ABLATION_FOR_PAPER_ARCHITECTURE_CLAIM"
    ):
        raise CompetitorMetricMatrixError("fusion mechanism decision drift")
    if _string_source_field(d64, ("decision",), "d64 decision") != "GO_D64_BLOCK_RECEIPT_COMPOSITION_GATE":
        raise CompetitorMetricMatrixError("d64 block receipt decision drift")
    if _string_source_field(d128, ("decision",), "d128 decision") != "NO_GO_D128_LAYERWISE_PROOF_ARTIFACT_MISSING":
        raise CompetitorMetricMatrixError("d128 target decision drift")

    fused_savings = _integer_source_field(fusion, ("route_matrix", "fused_savings_bytes_total"), "fusion savings")
    matched_profiles = _integer_source_field(
        fusion, ("route_matrix", "matched_profiles_checked"), "fusion matched profiles"
    )
    opening_share = _share_source_field(
        fusion, ("section_delta", "opening_bucket_savings_share"), "fusion opening share"
    )
    total_checked_rows = _integer_source_field(d64, ("summary", "total_checked_rows"), "d64 total checked rows")
    slice_count = _integer_source_field(d64, ("summary", "slice_count"), "d64 slice count")
    mutations_rejected = _integer_source_field(d64, ("summary", "mutations_rejected"), "d64 mutations rejected")
    mutation_cases = _integer_source_field(d64, ("summary", "mutation_cases"), "d64 mutation cases")
    target_linear_muls = _integer_source_field(
        d128, ("summary", "target_estimated_linear_muls"), "d128 target linear multiplications"
    )
    first_blocker = _string_source_field(d128, ("summary", "first_blocker"), "d128 first blocker")
    if fused_savings <= 0:
        raise CompetitorMetricMatrixError("fusion savings must be positive")
    if matched_profiles <= 0:
        raise CompetitorMetricMatrixError("fusion matched profiles must be positive")
    if total_checked_rows <= 0:
        raise CompetitorMetricMatrixError("d64 checked rows must be positive")
    if slice_count <= 0:
        raise CompetitorMetricMatrixError("d64 slice count must be positive")
    if mutations_rejected != mutation_cases or mutation_cases <= 0:
        raise CompetitorMetricMatrixError("d64 mutation rejection summary drift")
    if target_linear_muls <= 0:
        raise CompetitorMetricMatrixError("d128 target linear multiplications must be positive")

    return [
        {
            "system": "provable-transformer-vm",
            "surface": "Stwo attention/Softmax-table fusion",
            "local_status": "GO_BOUNDED_ARCHITECTURE_MECHANISM",
            "metric": "matched route JSON proof-byte saving",
            "value": fused_savings,
            "unit": "bytes",
            "support": f"{matched_profiles} matched profiles; opening share {opening_share:.6f}",
            "comparison_status": "LOCAL_MECHANISM_EVIDENCE_NOT_LAYERWISE_FULL_MODEL_BENCHMARK",
        },
        {
            "system": "provable-transformer-vm",
            "surface": "d64 RMSNorm/SwiGLU/residual block receipt",
            "local_status": "GO_STATEMENT_BOUND_RECEIPT_COMPOSITION",
            "metric": "checked slice rows",
            "value": total_checked_rows,
            "unit": "rows",
            "support": f"{slice_count} slices; {mutations_rejected} / {mutation_cases} mutations rejected",
            "comparison_status": "LOCAL_RECEIPT_CHAIN_NOT_RECURSIVE_PROOF_COMPRESSION",
        },
        {
            "system": "provable-transformer-vm",
            "surface": "d128 RMSNorm/SwiGLU/residual comparator target",
            "local_status": "NO_GO_LOCAL_D128_PROOF_ARTIFACT_MISSING",
            "metric": "target estimated linear multiplications",
            "value": target_linear_muls,
            "unit": "linear_muls",
            "support": first_blocker,
            "comparison_status": "TARGET_SPEC_ONLY_NOT_LOCAL_PROOF_RESULT",
        },
    ]


def build_payload() -> dict[str, Any]:
    payload = build_payload_uncommitted()
    expected = copy.deepcopy(payload)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload, expected=expected)
    return payload


def validate_payload(payload: dict[str, Any], *, expected: dict[str, Any] | None = None) -> None:
    if not isinstance(payload, dict):
        raise CompetitorMetricMatrixError("payload must be object")
    if expected is None:
        expected = build_payload_uncommitted()
    expected = {key: value for key, value in expected.items() if key != "payload_commitment"}
    candidate = {key: value for key, value in payload.items() if key != "payload_commitment"}
    if candidate != expected:
        if payload.get("schema") != SCHEMA:
            raise CompetitorMetricMatrixError("schema drift")
        if payload.get("decision") != DECISION:
            raise CompetitorMetricMatrixError("decision drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise CompetitorMetricMatrixError("claim boundary drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise CompetitorMetricMatrixError("non_claims drift")
        raise CompetitorMetricMatrixError("payload drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise CompetitorMetricMatrixError("payload commitment drift")


def build_payload_uncommitted() -> dict[str, Any]:
    published_raw = read_source_bytes(PUBLISHED_ZKML_NUMBERS, "published zkML TSV")
    fusion_raw = read_source_bytes(FUSION_MECHANISM, "fusion mechanism JSON")
    d64_raw = read_source_bytes(D64_BLOCK_RECEIPT, "d64 block receipt JSON")
    d128_raw = read_source_bytes(D128_TARGET, "d128 target JSON")
    published = _parse_tsv_bytes(PUBLISHED_ZKML_NUMBERS, published_raw)
    fusion = _parse_json_bytes(FUSION_MECHANISM, fusion_raw)
    d64 = _parse_json_bytes(D64_BLOCK_RECEIPT, d64_raw)
    d128 = _parse_json_bytes(D128_TARGET, d128_raw)
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": [
            _source_from_bytes(PUBLISHED_ZKML_NUMBERS, "published_zkml_numbers_tsv", published_raw),
            _source_from_bytes(FUSION_MECHANISM, "local_fusion_mechanism_json", fusion_raw),
            _source_from_bytes(D64_BLOCK_RECEIPT, "local_d64_block_receipt_json", d64_raw),
            _source_from_bytes(D128_TARGET, "local_d128_target_json", d128_raw),
        ],
        "external_rows": _external_rows(published),
        "local_rows": _local_rows(fusion, d64, d128),
        "interpretation": [
            "NANOZK and Jolt Atlas are the relevant layerwise/end-to-end competitors for headline zkML metrics.",
            "The local repo does not yet have a d128 layer proof to compare on proof size or verifier time.",
            "The local competitive claim is currently architectural: STARK-native fusion saves duplicated opening/decommitment plumbing.",
            "The next real block milestone is a parameterized d64 then d128 RMSNorm/SwiGLU/residual proof surface with the same statement bindings.",
        ],
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }


def to_tsv(payload: dict[str, Any]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(
        [
            "row_kind",
            "system",
            "surface_or_workload",
            "prove_seconds",
            "verify_seconds",
            "proof_size_reported",
            "local_metric",
            "local_value",
            "comparison_status",
        ]
    )
    for row in payload["external_rows"]:
        writer.writerow(
            [
                "external",
                row["system"],
                row["workload_label"],
                row["prove_seconds"],
                row["verify_seconds"],
                row["proof_size_reported"],
                "",
                "",
                row["comparison_status"],
            ]
        )
    for row in payload["local_rows"]:
        writer.writerow(
            [
                "local",
                row["system"],
                row["surface"],
                "",
                "",
                "",
                row["metric"],
                row["value"],
                row["comparison_status"],
            ]
        )
    return out.getvalue()


def _assert_output_path(path: pathlib.Path, label: str) -> pathlib.Path:
    raw = str(path).replace("\\", "/")
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise CompetitorMetricMatrixError(f"{label} must be repo-relative")
    if pathlib.PurePosixPath(*relative.parts[:3]) != pathlib.PurePosixPath("docs/engineering/evidence"):
        raise CompetitorMetricMatrixError(f"{label} must stay under docs/engineering/evidence")
    full = ROOT.joinpath(*relative.parts)
    _assert_no_repo_symlink_components(full.parent, label)
    if full.is_symlink():
        raise CompetitorMetricMatrixError(f"{label} must not include symlink components")
    return full


def _assert_no_repo_symlink_components(path: pathlib.Path, label: str) -> None:
    root = ROOT
    absolute = path if path.is_absolute() else ROOT / path
    try:
        relative = absolute.relative_to(ROOT)
    except ValueError as err:
        raise CompetitorMetricMatrixError(f"{label} must stay inside repository") from err
    if ".." in relative.parts:
        raise CompetitorMetricMatrixError(f"{label} must stay inside repository")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise CompetitorMetricMatrixError(f"{label} must not include symlink components")


def _directory_identity(path: pathlib.Path, label: str) -> tuple[int, int]:
    try:
        path_stat = path.lstat()
    except OSError as err:
        raise CompetitorMetricMatrixError(f"{label} parent directory is unavailable: {err}") from err
    if stat_module.S_ISLNK(path_stat.st_mode) or not stat_module.S_ISDIR(path_stat.st_mode):
        raise CompetitorMetricMatrixError(f"{label} parent must be a real directory")
    return (path_stat.st_dev, path_stat.st_ino)


def _assert_directory_identity(path: pathlib.Path, identity: tuple[int, int], label: str) -> None:
    _assert_no_repo_symlink_components(path, label)
    if _directory_identity(path, label) != identity:
        raise CompetitorMetricMatrixError(f"{label} parent directory changed while writing")


def _open_stable_directory(path: pathlib.Path, label: str) -> tuple[int, tuple[int, int]]:
    _assert_no_repo_symlink_components(path, label)
    path.mkdir(parents=True, exist_ok=True)
    _assert_no_repo_symlink_components(path, label)
    identity = _directory_identity(path, label)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as err:
        raise CompetitorMetricMatrixError(f"failed to open {label} parent directory: {err}") from err
    try:
        fd_stat = os.fstat(fd)
        if not stat_module.S_ISDIR(fd_stat.st_mode):
            raise CompetitorMetricMatrixError(f"{label} parent must be a real directory")
        if (fd_stat.st_dev, fd_stat.st_ino) != identity:
            raise CompetitorMetricMatrixError(f"{label} parent directory changed while opening")
    except Exception:
        os.close(fd)
        raise
    return fd, identity


def write_outputs(
    payload: dict[str, Any],
    json_path: pathlib.Path | None,
    tsv_path: pathlib.Path | None,
) -> None:
    validate_payload(payload)
    json_text = pretty_json(payload) + "\n"

    json_target = _assert_output_path(json_path, "json output path") if json_path is not None else None
    tsv_target = _assert_output_path(tsv_path, "tsv output path") if tsv_path is not None else None
    if json_target is None and tsv_target is None:
        raise CompetitorMetricMatrixError("at least one explicit output path is required")
    if (
        json_target is not None
        and tsv_target is not None
        and os.path.abspath(json_target).casefold() == os.path.abspath(tsv_target).casefold()
    ):
        raise CompetitorMetricMatrixError("json and tsv output paths must differ")

    outputs = []
    if json_target is not None:
        outputs.append((json_target, json_text))
    if tsv_target is not None:
        outputs.append((tsv_target, to_tsv(payload)))
    temps: list[tuple[pathlib.Path, str, int, tuple[int, int]]] = []
    replaced: list[pathlib.Path] = []
    original_bytes: dict[pathlib.Path, bytes | None] = {}
    write_error: Exception | None = None
    rollback_errors: list[str] = []

    def write_temp(path: pathlib.Path, contents: bytes, label: str) -> tuple[pathlib.Path, str, int, tuple[int, int]]:
        parent_fd, parent_identity = _open_stable_directory(path.parent, label)
        temp_name: str | None = None
        file_fd: int | None = None
        try:
            _assert_directory_identity(path.parent, parent_identity, label)
            if path.is_symlink():
                raise CompetitorMetricMatrixError(f"{label} must not include symlink components")
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
                raise CompetitorMetricMatrixError(f"failed to create unique temporary output for {label}")
            with os.fdopen(file_fd, "wb") as handle:
                file_fd = None
                handle.write(contents)
                handle.flush()
                os.fsync(handle.fileno())
            _assert_directory_identity(path.parent, parent_identity, label)
            return (path.parent / temp_name, temp_name, parent_fd, parent_identity)
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
        _, temp_name, parent_fd, parent_identity = temp
        _assert_directory_identity(path.parent, parent_identity, label)
        if path.is_symlink():
            raise CompetitorMetricMatrixError(f"{label} must not include symlink components")
        os.replace(temp_name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        _assert_directory_identity(path.parent, parent_identity, label)

    def cleanup_temp(temp: tuple[pathlib.Path, str, int, tuple[int, int]]) -> None:
        _, temp_name, parent_fd, _ = temp
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass

    def rollback_replace(path: pathlib.Path, contents: bytes) -> None:
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        tmp = write_temp(path, contents, "rollback output path")
        temps.append(tmp)
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        replace_temp(tmp, path, "rollback output path")

    def rollback_remove(path: pathlib.Path) -> None:
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        parent_fd, parent_identity = _open_stable_directory(path.parent, "rollback output path")
        try:
            _assert_directory_identity(path.parent, parent_identity, "rollback output path")
            if path.is_symlink():
                raise CompetitorMetricMatrixError("rollback output path must not include symlink components")
            try:
                os.unlink(path.name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            _assert_directory_identity(path.parent, parent_identity, "rollback output path")
        finally:
            os.close(parent_fd)

    try:
        try:
            for path, text in outputs:
                original_bytes[path] = read_source_bytes(path, "existing output") if path.exists() else None
                tmp = write_temp(path, text.encode("utf-8"), "output path")
                temps.append(tmp)
            for tmp, (path, _) in zip(temps, outputs, strict=True):
                replace_temp(tmp, path, "output path")
                replaced.append(path)
        except (CompetitorMetricMatrixError, OSError) as err:
            write_error = err
            raise CompetitorMetricMatrixError(f"failed to write output path: {err}") from err
    finally:
        if write_error is not None:
            for path in reversed(replaced):
                original = original_bytes.get(path)
                try:
                    _assert_output_path(path.relative_to(ROOT), "rollback output path")
                    if original is None:
                        rollback_remove(path)
                    else:
                        rollback_replace(path, original)
                except (CompetitorMetricMatrixError, OSError) as err:
                    rollback_errors.append(f"{path}: {err}")
        for tmp in temps:
            try:
                cleanup_temp(tmp)
            except OSError as err:
                if write_error is None:
                    raise CompetitorMetricMatrixError(f"failed to clean temporary output {tmp[0]}: {err}") from err
            finally:
                os.close(tmp[2])
        if rollback_errors:
            raise CompetitorMetricMatrixError(
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
    except CompetitorMetricMatrixError as err:
        print(f"competitor metric matrix gate failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
