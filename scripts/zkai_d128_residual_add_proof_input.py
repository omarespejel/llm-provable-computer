#!/usr/bin/env python3
"""Build the source-bound d128 residual-add proof input.

This consumes the checked d128 down-projection residual-delta commitment and the
canonical d128 block input activation, proves the residual-add rows, and emits a
final output-activation commitment. It is a native residual slice plus a
composition edge, not recursive aggregation of the preceding proofs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import pathlib
import stat as stat_module
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
RMSNORM_SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_public_row_proof_input.py"
DOWN_PROJECTION_SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_down_projection_proof_input.py"
RMSNORM_SOURCE_JSON = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
DOWN_SOURCE_JSON = EVIDENCE_DIR / "zkai-d128-down-projection-proof-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-residual-add-proof-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-residual-add-proof-2026-05.tsv"

SCHEMA = "zkai-d128-residual-add-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_D128_RESIDUAL_ADD_AIR_PROOF"
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
WIDTH = 128
M31_MODULUS = (1 << 31) - 1
Q8_SEMANTIC_ABS_BOUND = 1024
MAX_SOURCE_JSON_BYTES = 2 * 1024 * 1024

SOURCE_RMSNORM_SCHEMA = "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3"
SOURCE_RMSNORM_DECISION = "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF"
SOURCE_RMSNORM_PROOF_VERSION = "stwo-d128-rmsnorm-public-row-air-proof-v3"
SOURCE_RMSNORM_STATEMENT_COMMITMENT = "blake2b-256:de944915f2664ac7a893f4ba9a029323f7408eac58bf39170a0935d7832ccbd8"
SOURCE_DOWN_PROJECTION_SCHEMA = "zkai-d128-down-projection-air-proof-input-v1"
SOURCE_DOWN_PROJECTION_DECISION = "GO_INPUT_FOR_D128_DOWN_PROJECTION_AIR_PROOF"
SOURCE_DOWN_PROJECTION_PROOF_VERSION = "stwo-d128-down-projection-air-proof-v1"
SOURCE_DOWN_PROJECTION_STATEMENT_COMMITMENT = "blake2b-256:70f900b6d26fb33273c0123b4c4d6b7723e45612b2ca6fd9d536e613e8412599"
SOURCE_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:8a5fd95ef4fb5284374788c03861099a32ed7c2082cbdccd6bedd3d9b211f9e1"
TARGET_COMMITMENT = "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18"
INPUT_ACTIVATION_COMMITMENT = "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78"
RESIDUAL_DELTA_COMMITMENT = "blake2b-256:d04770d7ab488a3e2366265ed45b039e590d1e03604c7954ac379ce0c37de2b2"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:869a0046bdaba3f6a7f98a3ffec618479c9dc91df2a342900c76f9ba53215fc1"
RESIDUAL_ADD_ROW_COMMITMENT = "blake2b-256:be931ba0fe63ea16d3dc2abb2fc2bafaa13ccf0db1f43fee9e734d5f2bf1100d"
PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:f958da6fa72df8bc32873b3602a128ed35b65f9427e8627af0b39ff7e21b31bc"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:460b15062fab393fb27076ff82ce3d4ce2fcdcb8279171e9096809f697984cde"
STATEMENT_COMMITMENT = "blake2b-256:7324cabcfe588b50f9fd4c52d0654b1f110cb157b757dac643362a70010f0fb2"

INPUT_ACTIVATION_DOMAIN = "ptvm:zkai:d128-input-activation:v1"
RESIDUAL_DELTA_DOMAIN = "ptvm:zkai:d128-residual-delta:v1"
OUTPUT_ACTIVATION_DOMAIN = "ptvm:zkai:d128-output-activation:v1"
RESIDUAL_ADD_ROW_DOMAIN = "ptvm:zkai:d128-residual-add-rows:v1"
PROOF_NATIVE_PARAMETER_KIND = "d128-residual-add-source-bound-parameters-v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:d128-proof-native-parameter-commitment:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:d128-public-instance:v1"
RANGE_POLICY = "input_activation_q8_semantic_bound_1024; residual_delta_and_output_signed_m31"
NEXT_BACKEND_STEP = "compose all checked d128 slice receipts into one statement-bound block receipt before benchmarking"

NON_CLAIMS = [
    "not recursive composition of all d128 proof slices",
    "not private parameter-opening proof",
    "not model-scale transformer inference",
    "not verifier-time benchmark evidence for the full d128 block",
    "not onchain deployment evidence",
]

PROOF_VERIFIER_HARDENING = [
    "source RMSNorm input activation commitment recomputation before proof verification",
    "source down-projection residual-delta commitment recomputation before proof verification",
    "residual-add row commitment recomputation before proof verification",
    "final output activation commitment recomputation before proof verification",
    "AIR residual-add relation for every checked d128 output coordinate",
    "q8 semantic bound only for the original input activation",
    "signed-M31 bounds for residual delta and final output activations",
    "intermediate commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_residual_add_proof_input.py --write-json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_residual_add_proof_input",
    "cargo +nightly-2025-07-14 test d128_native_residual_add_proof --lib --features stwo-backend",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "width",
    "row_count",
    "source_rmsnorm_proof_version",
    "source_down_projection_proof_version",
    "input_activation_commitment",
    "residual_delta_commitment",
    "residual_delta_scale_divisor",
    "residual_delta_remainder_sha256",
    "output_activation_commitment",
    "residual_add_row_commitment",
    "range_policy",
    "residual_min",
    "residual_max",
    "output_min",
    "output_max",
    "residual_delta_relabels_full_output",
    "input_relabels_output",
    "non_claims",
    "next_backend_step",
)


class D128ResidualAddInputError(ValueError):
    pass


def _read_repo_regular_file_bytes(path: pathlib.Path) -> tuple[bytes, pathlib.Path]:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise D128ResidualAddInputError(f"module path must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128ResidualAddInputError(f"module path escapes repository: {path}") from err
    try:
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise D128ResidualAddInputError(f"module path is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise D128ResidualAddInputError(f"module path is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise D128ResidualAddInputError(f"module path changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                return handle.read(), resolved
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise D128ResidualAddInputError(f"failed to load module path {path}: {err}") from err


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    source, resolved = _read_repo_regular_file_bytes(path)
    spec = importlib.util.spec_from_loader(module_name, loader=None, origin=str(resolved))
    if spec is None:
        raise D128ResidualAddInputError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(resolved)
    exec(compile(source, str(resolved), "exec"), module.__dict__)
    return module


RMSNORM = _load_module(RMSNORM_SCRIPT_PATH, "zkai_d128_rmsnorm_public_row_proof_input")
DOWN_PROJECTION = _load_module(DOWN_PROJECTION_SCRIPT_PATH, "zkai_d128_down_projection_proof_input")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def sequence_commitment(values: list[int], domain: str, shape: list[int]) -> str:
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": shape,
            "values_sha256": sha256_hex(values),
        },
        domain,
    )


def rows_commitment(rows: list[dict[str, int]]) -> str:
    material = [[row["row_index"], row["input_q8"], row["residual_delta_q8"], row["output_q8"]] for row in rows]
    return blake2b_commitment(
        {
            "encoding": "d128_residual_add_rows_v1",
            "rows_sha256": sha256_hex(material),
            "shape": [len(rows), 4],
        },
        RESIDUAL_ADD_ROW_DOMAIN,
    )


def statement_commitment(payload: dict[str, Any]) -> str:
    return blake2b_commitment(
        {
            "input_activation_commitment": payload["input_activation_commitment"],
            "operation": "residual_add",
            "output_activation_commitment": payload["output_activation_commitment"],
            "range_policy": payload["range_policy"],
            "required_backend_version": REQUIRED_BACKEND_VERSION,
            "residual_add_row_commitment": payload["residual_add_row_commitment"],
            "residual_delta_commitment": payload["residual_delta_commitment"],
            "residual_delta_remainder_sha256": payload["residual_delta_remainder_sha256"],
            "residual_delta_scale_divisor": payload["residual_delta_scale_divisor"],
            "row_count": payload["row_count"],
            "source_down_projection_proof_version": SOURCE_DOWN_PROJECTION_PROOF_VERSION,
            "source_down_projection_public_instance_commitment": payload["source_down_projection_public_instance_commitment"],
            "source_down_projection_statement_commitment": payload["source_down_projection_statement_commitment"],
            "source_rmsnorm_proof_version": SOURCE_RMSNORM_PROOF_VERSION,
            "source_rmsnorm_statement_commitment": payload["source_rmsnorm_statement_commitment"],
            "target_commitment": TARGET_COMMITMENT,
            "target_id": TARGET_ID,
            "verifier_domain": VERIFIER_DOMAIN,
            "width": payload["width"],
        },
        VERIFIER_DOMAIN,
    )


def proof_native_parameter_commitment(source_down_statement: str) -> str:
    return blake2b_commitment(
        {
            "kind": PROOF_NATIVE_PARAMETER_KIND,
            "source_down_projection_statement_commitment": source_down_statement,
            "target_commitment": TARGET_COMMITMENT,
            "width": WIDTH,
        },
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )


def public_instance_commitment(statement: str) -> str:
    return blake2b_commitment(
        {"operation": "residual_add", "target_commitment": statement, "width": WIDTH},
        PUBLIC_INSTANCE_DOMAIN,
    )


def require_commitment(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("blake2b-256:"):
        raise D128ResidualAddInputError(f"{label} must be a blake2b-256 commitment")
    digest = value.removeprefix("blake2b-256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise D128ResidualAddInputError(f"{label} must be a 32-byte lowercase hex digest")
    return value


def require_signed_m31(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128ResidualAddInputError(f"{label} must be an integer")
    if value <= -M31_MODULUS or value >= M31_MODULUS:
        raise D128ResidualAddInputError(f"{label} outside signed M31 bounds")


def require_signed_q8(value: Any, label: str) -> None:
    require_signed_m31(value, label)
    if not (-Q8_SEMANTIC_ABS_BOUND <= value <= Q8_SEMANTIC_ABS_BOUND):
        raise D128ResidualAddInputError(f"{label} outside fixed-point q8 semantic bounds")


def _load_source(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        if path.is_symlink():
            raise D128ResidualAddInputError(f"{label} evidence must not be a symlink: {path}")
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError as err:
            raise D128ResidualAddInputError(f"{label} evidence escapes repository: {path}") from err
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise D128ResidualAddInputError(f"{label} evidence is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise D128ResidualAddInputError(f"{label} evidence is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise D128ResidualAddInputError(f"{label} evidence changed while reading: {path}")
            with os.fdopen(fd, "rb") as source_file:
                fd = None
                source_bytes = source_file.read(MAX_SOURCE_JSON_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
        if len(source_bytes) > MAX_SOURCE_JSON_BYTES:
            raise D128ResidualAddInputError(f"{label} evidence exceeds max size")
        payload = json.loads(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128ResidualAddInputError(f"failed to load {label} evidence: {err}") from err
    if not isinstance(payload, dict):
        raise D128ResidualAddInputError(f"{label} evidence must be an object")
    return payload


def load_rmsnorm_source(path: pathlib.Path = RMSNORM_SOURCE_JSON) -> dict[str, Any]:
    payload = _load_source(path, "RMSNorm")
    validate_rmsnorm_source(payload)
    return payload


def load_down_source(path: pathlib.Path = DOWN_SOURCE_JSON) -> dict[str, Any]:
    payload = _load_source(path, "down-projection")
    validate_down_source(payload)
    return payload


def validate_rmsnorm_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise D128ResidualAddInputError("source RMSNorm evidence must be an object")
    constants = {
        "schema": SOURCE_RMSNORM_SCHEMA,
        "decision": SOURCE_RMSNORM_DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "input_activation_commitment": INPUT_ACTIVATION_COMMITMENT,
    }
    for field, expected in constants.items():
        if source.get(field) != expected:
            raise D128ResidualAddInputError(f"source RMSNorm field mismatch: {field}")
    try:
        RMSNORM.validate_payload(source)
    except Exception as err:  # noqa: BLE001
        raise D128ResidualAddInputError(f"source RMSNorm validation failed: {err}") from err


def validate_down_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise D128ResidualAddInputError("source down-projection evidence must be an object")
    constants = {
        "schema": SOURCE_DOWN_PROJECTION_SCHEMA,
        "decision": SOURCE_DOWN_PROJECTION_DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "residual_delta_rows": WIDTH,
        "residual_delta_commitment": RESIDUAL_DELTA_COMMITMENT,
        "statement_commitment": SOURCE_DOWN_PROJECTION_STATEMENT_COMMITMENT,
        "public_instance_commitment": SOURCE_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
    }
    for field, expected in constants.items():
        if source.get(field) != expected:
            raise D128ResidualAddInputError(f"source down-projection field mismatch: {field}")
    try:
        DOWN_PROJECTION.validate_payload(source)
    except Exception as err:  # noqa: BLE001
        raise D128ResidualAddInputError(f"source down-projection validation failed: {err}") from err


def source_input_activation(source: dict[str, Any]) -> list[int]:
    validate_rmsnorm_source(source)
    rows = source.get("rows")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise D128ResidualAddInputError("source RMSNorm row vector mismatch")
    values: list[int] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or "input_q8" not in row:
            raise D128ResidualAddInputError("source RMSNorm row field mismatch")
        value = row["input_q8"]
        require_signed_q8(value, f"source input activation {index}")
        values.append(value)
    if sequence_commitment(values, INPUT_ACTIVATION_DOMAIN, [WIDTH]) != source["input_activation_commitment"]:
        raise D128ResidualAddInputError("source input activation commitment drift")
    return values


def source_residual_delta(source: dict[str, Any]) -> tuple[list[int], list[int], int]:
    validate_down_source(source)
    residual_delta = source.get("residual_delta_q8")
    remainders = source.get("residual_delta_remainder_q8")
    if not isinstance(residual_delta, list) or len(residual_delta) != WIDTH:
        raise D128ResidualAddInputError("source residual delta vector mismatch")
    if not isinstance(remainders, list) or len(remainders) != WIDTH:
        raise D128ResidualAddInputError("source residual delta remainder vector mismatch")
    for index, value in enumerate(residual_delta):
        require_signed_m31(value, f"source residual delta {index}")
    divisor = source["residual_delta_scale_divisor"]
    if DOWN_PROJECTION.residual_delta_commitment(residual_delta, remainders, divisor) != source["residual_delta_commitment"]:
        raise D128ResidualAddInputError("source residual delta commitment drift")
    return residual_delta, remainders, divisor


def build_rows(input_q8: list[int], residual_delta_q8: list[int]) -> list[dict[str, int]]:
    if len(input_q8) != WIDTH or len(residual_delta_q8) != WIDTH:
        raise D128ResidualAddInputError("vector length mismatch")
    rows: list[dict[str, int]] = []
    for row_index, (base, delta) in enumerate(zip(input_q8, residual_delta_q8, strict=True)):
        require_signed_q8(base, f"input activation {row_index}")
        require_signed_m31(delta, f"residual delta {row_index}")
        output = base + delta
        require_signed_m31(output, f"output activation {row_index}")
        rows.append({"row_index": row_index, "input_q8": base, "residual_delta_q8": delta, "output_q8": output})
    return rows


def build_payload(rmsnorm_source: dict[str, Any] | None = None, down_source: dict[str, Any] | None = None) -> dict[str, Any]:
    rmsnorm_source = load_rmsnorm_source() if rmsnorm_source is None else rmsnorm_source
    down_source = load_down_source() if down_source is None else down_source
    input_q8 = source_input_activation(rmsnorm_source)
    residual_delta_q8, residual_delta_remainder_q8, residual_delta_scale_divisor = source_residual_delta(down_source)
    rows = build_rows(input_q8, residual_delta_q8)
    output_q8 = [row["output_q8"] for row in rows]
    residual_add = rows_commitment(rows)
    output_activation = sequence_commitment(output_q8, OUTPUT_ACTIVATION_DOMAIN, [WIDTH])
    native_parameter = proof_native_parameter_commitment(down_source["statement_commitment"])
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_rmsnorm_proof_version": SOURCE_RMSNORM_PROOF_VERSION,
        "source_rmsnorm_statement_commitment": rmsnorm_source["statement_commitment"],
        "source_down_projection_proof_version": SOURCE_DOWN_PROJECTION_PROOF_VERSION,
        "source_down_projection_statement_commitment": down_source["statement_commitment"],
        "source_down_projection_public_instance_commitment": down_source["public_instance_commitment"],
        "range_policy": RANGE_POLICY,
        "input_activation_commitment": rmsnorm_source["input_activation_commitment"],
        "residual_delta_commitment": down_source["residual_delta_commitment"],
        "residual_delta_scale_divisor": residual_delta_scale_divisor,
        "residual_delta_remainder_sha256": sha256_hex(residual_delta_remainder_q8),
        "output_activation_commitment": output_activation,
        "residual_add_row_commitment": residual_add,
        "proof_native_parameter_commitment": native_parameter,
        "public_instance_commitment": "",
        "statement_commitment": "",
        "input_q8": input_q8,
        "residual_delta_q8": residual_delta_q8,
        "residual_delta_remainder_q8": residual_delta_remainder_q8,
        "output_q8": output_q8,
        "rows": rows,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    statement = statement_commitment(payload)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = public_instance_commitment(statement)
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise D128ResidualAddInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "target_id", "required_backend_version", "verifier_domain", "width", "row_count",
        "source_rmsnorm_proof_version", "source_rmsnorm_statement_commitment", "source_down_projection_proof_version",
        "source_down_projection_statement_commitment", "source_down_projection_public_instance_commitment", "range_policy",
        "input_activation_commitment", "residual_delta_commitment", "output_activation_commitment", "residual_add_row_commitment",
        "residual_delta_scale_divisor", "residual_delta_remainder_sha256", "proof_native_parameter_commitment",
        "public_instance_commitment", "statement_commitment", "input_q8", "residual_delta_q8", "residual_delta_remainder_q8",
        "output_q8", "rows", "non_claims", "proof_verifier_hardening", "next_backend_step", "validation_commands",
    }
    if set(payload) != expected_fields:
        raise D128ResidualAddInputError("payload field set mismatch")
    if payload["residual_delta_commitment"] == payload["output_activation_commitment"]:
        raise D128ResidualAddInputError("residual delta commitment relabeled as full output commitment")
    if payload["input_activation_commitment"] == payload["output_activation_commitment"]:
        raise D128ResidualAddInputError("input activation commitment relabeled as output activation commitment")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_rmsnorm_proof_version": SOURCE_RMSNORM_PROOF_VERSION,
        "source_rmsnorm_statement_commitment": SOURCE_RMSNORM_STATEMENT_COMMITMENT,
        "source_down_projection_proof_version": SOURCE_DOWN_PROJECTION_PROOF_VERSION,
        "source_down_projection_statement_commitment": SOURCE_DOWN_PROJECTION_STATEMENT_COMMITMENT,
        "source_down_projection_public_instance_commitment": SOURCE_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
        "range_policy": RANGE_POLICY,
        "input_activation_commitment": INPUT_ACTIVATION_COMMITMENT,
        "residual_delta_commitment": RESIDUAL_DELTA_COMMITMENT,
        "residual_delta_scale_divisor": 512,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    for field, expected in constants.items():
        if payload.get(field) != expected:
            raise D128ResidualAddInputError(f"payload field mismatch: {field}")
    for field in (
        "source_rmsnorm_statement_commitment", "source_down_projection_statement_commitment",
        "source_down_projection_public_instance_commitment", "input_activation_commitment", "residual_delta_commitment",
        "output_activation_commitment", "residual_add_row_commitment", "proof_native_parameter_commitment",
        "public_instance_commitment", "statement_commitment",
    ):
        require_commitment(payload[field], field)
    if payload["proof_native_parameter_commitment"] != proof_native_parameter_commitment(payload["source_down_projection_statement_commitment"]):
        raise D128ResidualAddInputError("proof-native parameter commitment drift")
    input_q8 = payload["input_q8"]
    residual_delta_q8 = payload["residual_delta_q8"]
    residual_delta_remainder_q8 = payload["residual_delta_remainder_q8"]
    output_q8 = payload["output_q8"]
    rows = payload["rows"]
    if not isinstance(input_q8, list) or len(input_q8) != WIDTH:
        raise D128ResidualAddInputError("input activation vector mismatch")
    if not isinstance(residual_delta_q8, list) or len(residual_delta_q8) != WIDTH:
        raise D128ResidualAddInputError("residual delta vector mismatch")
    if not isinstance(output_q8, list) or len(output_q8) != WIDTH:
        raise D128ResidualAddInputError("output activation vector mismatch")
    if not isinstance(residual_delta_remainder_q8, list) or len(residual_delta_remainder_q8) != WIDTH:
        raise D128ResidualAddInputError("residual delta remainder vector mismatch")
    for index, value in enumerate(input_q8):
        require_signed_q8(value, f"input activation {index}")
    for label, values in (("residual delta", residual_delta_q8), ("output activation", output_q8)):
        for index, value in enumerate(values):
            require_signed_m31(value, f"{label} {index}")
    for index, value in enumerate(residual_delta_remainder_q8):
        if not isinstance(value, int) or isinstance(value, bool):
            raise D128ResidualAddInputError(f"residual delta remainder {index} must be an integer")
        if value < 0 or value >= payload["residual_delta_scale_divisor"]:
            raise D128ResidualAddInputError(f"residual delta remainder {index} outside divisor range")
    if sha256_hex(residual_delta_remainder_q8) != payload["residual_delta_remainder_sha256"]:
        raise D128ResidualAddInputError("residual delta remainder hash drift")
    if DOWN_PROJECTION.residual_delta_commitment(
        residual_delta_q8,
        residual_delta_remainder_q8,
        payload["residual_delta_scale_divisor"],
    ) != payload["residual_delta_commitment"]:
        raise D128ResidualAddInputError("residual delta commitment drift")
    if sequence_commitment(input_q8, INPUT_ACTIVATION_DOMAIN, [WIDTH]) != payload["input_activation_commitment"]:
        raise D128ResidualAddInputError("input activation commitment drift")
    if sequence_commitment(output_q8, OUTPUT_ACTIVATION_DOMAIN, [WIDTH]) != payload["output_activation_commitment"]:
        raise D128ResidualAddInputError("output activation commitment drift")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise D128ResidualAddInputError("row vector mismatch")
    recomputed_rows = build_rows(input_q8, residual_delta_q8)
    if rows != recomputed_rows:
        raise D128ResidualAddInputError("residual-add row relation drift")
    if [row["output_q8"] for row in rows] != output_q8:
        raise D128ResidualAddInputError("output activation row drift")
    if rows_commitment(rows) != payload["residual_add_row_commitment"]:
        raise D128ResidualAddInputError("residual-add row commitment drift")
    if statement_commitment(payload) != payload["statement_commitment"]:
        raise D128ResidualAddInputError("statement commitment drift")
    if public_instance_commitment(payload["statement_commitment"]) != payload["public_instance_commitment"]:
        raise D128ResidualAddInputError("public instance commitment drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    residual = payload["residual_delta_q8"]
    output = payload["output_q8"]
    return [{
        "target_id": payload["target_id"],
        "decision": payload["decision"],
        "width": payload["width"],
        "row_count": payload["row_count"],
        "source_rmsnorm_proof_version": payload["source_rmsnorm_proof_version"],
        "source_down_projection_proof_version": payload["source_down_projection_proof_version"],
        "input_activation_commitment": payload["input_activation_commitment"],
        "residual_delta_commitment": payload["residual_delta_commitment"],
        "residual_delta_scale_divisor": payload["residual_delta_scale_divisor"],
        "residual_delta_remainder_sha256": payload["residual_delta_remainder_sha256"],
        "output_activation_commitment": payload["output_activation_commitment"],
        "residual_add_row_commitment": payload["residual_add_row_commitment"],
        "range_policy": payload["range_policy"],
        "residual_min": min(residual),
        "residual_max": max(residual),
        "output_min": min(output),
        "output_max": max(output),
        "residual_delta_relabels_full_output": str(payload["residual_delta_commitment"] == payload["output_activation_commitment"]).lower(),
        "input_relabels_output": str(payload["input_activation_commitment"] == payload["output_activation_commitment"]).lower(),
        "non_claims": json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
        "next_backend_step": payload["next_backend_step"],
    }]


def _assert_repo_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise D128ResidualAddInputError(f"output path must not be a symlink: {path}")
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128ResidualAddInputError(f"output path escapes repository: {path}") from err
    if resolved.exists() and resolved.is_dir():
        raise D128ResidualAddInputError(f"output path must not be a directory: {path}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _atomic_write_text(path: pathlib.Path, text: str) -> pathlib.Path:
    resolved = _assert_repo_output_path(path)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent)
    tmp_path = pathlib.Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, resolved)
        dir_fd = os.open(resolved.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return resolved


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    if json_path is not None:
        _atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if tsv_path is not None:
        import io

        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_for_tsv(payload, validated=True))
        _atomic_write_text(tsv_path, buffer.getvalue())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rmsnorm-source-json", type=pathlib.Path, default=RMSNORM_SOURCE_JSON)
    parser.add_argument("--down-source-json", type=pathlib.Path, default=DOWN_SOURCE_JSON)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(load_rmsnorm_source(args.rmsnorm_source_json), load_down_source(args.down_source_json))
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    summary = {
        "schema": SCHEMA,
        "decision": payload["decision"],
        "width": payload["width"],
        "row_count": payload["row_count"],
        "range_policy": payload["range_policy"],
        "residual_delta_commitment": payload["residual_delta_commitment"],
        "output_activation_commitment": payload["output_activation_commitment"],
        "statement_commitment": payload["statement_commitment"],
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
