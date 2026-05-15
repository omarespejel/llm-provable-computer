#!/usr/bin/env python3
"""Build the d128 down-projection proof input.

This native-proof input consumes the d128 activation/SwiGLU hidden activation
output, checks deterministic down-projection multiplication rows, and emits a
residual-delta commitment. It intentionally does not prove residual addition,
composition, recursion, or the final block output commitment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import stat as stat_module
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ACTIVATION_SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_activation_swiglu_proof_input.py"
SOURCE_JSON = ROOT / "docs" / "engineering" / "evidence" / "zkai-d128-activation-swiglu-proof-2026-05.json"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d128-down-projection-proof-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d128-down-projection-proof-2026-05.tsv"

SCHEMA = "zkai-d128-down-projection-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_D128_DOWN_PROJECTION_AIR_PROOF"
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
WIDTH = 128
FF_DIM = 512
M31_MODULUS = (1 << 31) - 1
MAX_SOURCE_JSON_BYTES = 2 * 1024 * 1024
Q8_SEMANTIC_ABS_BOUND = 1024
SOURCE_ACTIVATION_SWIGLU_SCHEMA = "zkai-d128-activation-swiglu-air-proof-input-v1"
SOURCE_ACTIVATION_SWIGLU_DECISION = "GO_INPUT_FOR_D128_ACTIVATION_SWIGLU_AIR_PROOF"
SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION = "stwo-d128-activation-swiglu-air-proof-v1"
SOURCE_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT = "blake2b-256:b6f7c2b52c71ff5b096c6151305d24a07f40d162c65836d72b7c39bbdc319f31"
SOURCE_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:400909bc5391608356a82db328209e275788787658d9689a88a66fbaa669695e"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:7e6ae6d301fc60ac2232d807d155785eabe653cf4e91971adda470a04246a572"
HIDDEN_ACTIVATION_COMMITMENT = "blake2b-256:ba8f9379f07a133f640a6594b6a06ae7b8d374110dc0f4b3a9779743734ad312"
DERIVED_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT = "blake2b-256:6fe34d1b0da8ad503ee3ac83b42199fc242110f0e81cd9353f7ba71ceea90738"
DERIVED_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:c1848a2bbdb4d8f897cd4a6764bc8b74c1db0bcd8441828ab2cde1e68310b4fb"
DERIVED_HIDDEN_ACTIVATION_COMMITMENT = "blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4"
TARGET_COMMITMENT = "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18"
PROOF_NATIVE_PARAMETER_KIND = "d128-down-projection-synthetic-parameters-v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:d128-proof-native-parameter-commitment:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:d128-public-instance:v1"
WEIGHT_GENERATOR_SEED = "zkai-d128-down-projection-synthetic-parameters-2026-05-v1"
HIDDEN_ACTIVATION_DOMAIN = "ptvm:zkai:d128-hidden-activation:v1"
RESIDUAL_DELTA_DOMAIN = "ptvm:zkai:d128-residual-delta:v1"
DOWN_PROJECTION_MUL_ROW_DOMAIN = "ptvm:zkai:d128-down-projection-mul-rows:v1"
MATRIX_ROW_LEAF_DOMAIN = "ptvm:zkai:d128:param-matrix-row-leaf:v1"
MATRIX_ROW_TREE_DOMAIN = "ptvm:zkai:d128:param-matrix-row-tree:v1"

# Filled from the deterministic generator output.
DOWN_MATRIX_ROOT = "blake2b-256:0d6cd2bee99c821788d1faf5dd24e5e3e8ff4d4d4acd4d99c46a10ecc166c7ab"
PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:ee69217168238b20e0b46a722554b42abe4fd5c599231f130d25ca7e4b432aef"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:8a5fd95ef4fb5284374788c03861099a32ed7c2082cbdccd6bedd3d9b211f9e1"
STATEMENT_COMMITMENT = "blake2b-256:70f900b6d26fb33273c0123b4c4d6b7723e45612b2ca6fd9d536e613e8412599"
RESIDUAL_DELTA_COMMITMENT = "blake2b-256:d04770d7ab488a3e2366265ed45b039e590d1e03604c7954ac379ce0c37de2b2"
RESIDUAL_DELTA_REMAINDER_SHA256 = "a99010fcd4f0898287b58960f979b086208ea7eff6ca51f0e8af827ec916ef3d"
DOWN_PROJECTION_MUL_ROW_COMMITMENT = "blake2b-256:76c1e5a35ffbc0c9b390f73d3491d973e85180421ac6168c0cb0e18a91a2ca68"
DERIVED_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:a4c0e39d34dce67783230532ee7031449b1d2aec9add232ef40f43073e372735"
DERIVED_STATEMENT_COMMITMENT = "blake2b-256:3ca2a06054a8ae8a9526bce62a4bc3a91e6f302fc3cb4866d7e2dc2afbf5f23e"
DERIVED_RESIDUAL_DELTA_COMMITMENT = "blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec"
DERIVED_RESIDUAL_DELTA_REMAINDER_SHA256 = "745d0cc14f1f5c595db32b81dd4b58b49df2e9b98b4ca6e7ec5fc3065811f895"
DERIVED_DOWN_PROJECTION_MUL_ROW_COMMITMENT = "blake2b-256:cd051c1ff66c5b413203b6d612d7c70ff14a0be7723c214c2808b12625fcc278"
RANGE_POLICY = "signed-M31 hidden activations and residual deltas; exact residual delta quotient/remainder binding; q8 down weights"

NEXT_BACKEND_STEP = "bind d128 residual-add rows to residual_delta_commitment and output_activation_commitment"

NON_CLAIMS = [
    "not full d128 block proof",
    "not residual proof",
    "not recursive composition",
    "not binding the full d128 output_activation_commitment",
    "not a private down-weight opening proof",
    "down projection aggregation is verifier-recomputed from checked public multiplication rows, not a private AIR aggregation claim",
]

PROOF_VERIFIER_HARDENING = [
    "source d128 activation/SwiGLU evidence validation before down-projection construction",
    "source activation statement and public-instance commitments checked before proof verification",
    "hidden activation commitment recomputation before proof verification",
    "down-projection multiplication row commitment recomputation before proof verification",
    "residual-delta commitment recomputation before proof verification",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "AIR multiplication relation for every checked down-projection row",
    "down matrix root recomputed from checked row weights",
    "signed-M31 bounds for hidden activations and residual deltas; exact residual delta quotient/remainder binding; fixed-point q8 semantic bounds for down weights",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_down_projection_proof_input.py --write-json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_down_projection_proof_input",
    "cargo +nightly-2025-07-14 test d128_native_down_projection_proof --lib --features stwo-backend",
    "just gate-fast",
    "just gate",
]
DERIVED_VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_down_projection_proof_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_down_projection_proof_input",
    "cargo +nightly-2025-07-14 test d128_native_down_projection_proof --lib --features stwo-backend",
    "just gate-fast",
    "just gate",
]

SOURCE_ACTIVATION_ANCHORS = (
    {
        "kind": "synthetic",
        "statement_commitment": SOURCE_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT,
        "public_instance_commitment": SOURCE_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
        "hidden_activation_commitment": HIDDEN_ACTIVATION_COMMITMENT,
        "residual_delta_commitment": RESIDUAL_DELTA_COMMITMENT,
        "residual_delta_remainder_sha256": RESIDUAL_DELTA_REMAINDER_SHA256,
        "down_projection_mul_row_commitment": DOWN_PROJECTION_MUL_ROW_COMMITMENT,
        "public_instance_commitment_out": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment_out": STATEMENT_COMMITMENT,
        "validation_commands": VALIDATION_COMMANDS,
    },
    {
        "kind": "attention_derived",
        "statement_commitment": DERIVED_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT,
        "public_instance_commitment": DERIVED_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
        "hidden_activation_commitment": DERIVED_HIDDEN_ACTIVATION_COMMITMENT,
        "residual_delta_commitment": DERIVED_RESIDUAL_DELTA_COMMITMENT,
        "residual_delta_remainder_sha256": DERIVED_RESIDUAL_DELTA_REMAINDER_SHA256,
        "down_projection_mul_row_commitment": DERIVED_DOWN_PROJECTION_MUL_ROW_COMMITMENT,
        "public_instance_commitment_out": DERIVED_PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment_out": DERIVED_STATEMENT_COMMITMENT,
        "validation_commands": DERIVED_VALIDATION_COMMANDS,
    },
)

TSV_COLUMNS = (
    "target_id",
    "decision",
    "width",
    "ff_dim",
    "row_count",
    "down_projection_mul_rows",
    "residual_delta_rows",
    "residual_delta_scale_divisor",
    "residual_delta_remainder_sha256",
    "source_hidden_activation_commitment",
    "source_activation_swiglu_statement_commitment",
    "source_activation_swiglu_public_instance_commitment",
    "down_matrix_root",
    "residual_delta_commitment",
    "down_projection_mul_row_commitment",
    "residual_delta_relabels_full_output",
    "non_claims",
    "next_backend_step",
)


class D128DownProjectionInputError(ValueError):
    pass


def _read_repo_regular_file_bytes(path: pathlib.Path) -> tuple[bytes, pathlib.Path]:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise D128DownProjectionInputError(f"module path must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128DownProjectionInputError(f"module path escapes repository: {path}") from err
    try:
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise D128DownProjectionInputError(f"module path is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise D128DownProjectionInputError(f"module path is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise D128DownProjectionInputError(f"module path changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                return handle.read(), resolved
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise D128DownProjectionInputError(f"failed to load module path {path}: {err}") from err


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    source, resolved = _read_repo_regular_file_bytes(path)
    spec = importlib.util.spec_from_loader(module_name, loader=None, origin=str(resolved))
    if spec is None:
        raise D128DownProjectionInputError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(resolved)
    exec(compile(source, str(resolved), "exec"), module.__dict__)
    return module


ACTIVATION_SWIGLU = _load_module(ACTIVATION_SCRIPT_PATH, "zkai_d128_activation_swiglu_proof_input")


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


def blake2b_hex(data: bytes, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(data)
    return digest.hexdigest()


def sequence_commitment(values: list[int], domain: str, shape: list[int]) -> str:
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": shape,
            "values_sha256": sha256_hex(values),
        },
        domain,
    )


def residual_delta_commitment(quotients: list[int], remainders: list[int], divisor: int) -> str:
    return blake2b_commitment(
        {
            "divisor": divisor,
            "encoding": "signed_division_result_sequence_v1",
            "quotients_sha256": sha256_hex(quotients),
            "remainders_sha256": sha256_hex(remainders),
            "shape": [len(quotients)],
        },
        RESIDUAL_DELTA_DOMAIN,
    )


def require_commitment(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("blake2b-256:"):
        raise D128DownProjectionInputError(f"{label} must be a blake2b-256 commitment")
    digest = value.removeprefix("blake2b-256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise D128DownProjectionInputError(f"{label} must be a 32-byte lowercase hex digest")
    return value


def source_activation_anchor(source: dict[str, Any]) -> dict[str, Any]:
    statement = require_commitment(
        source.get("statement_commitment"),
        "source_activation_swiglu_statement_commitment",
    )
    public_instance = require_commitment(
        source.get("public_instance_commitment"),
        "source_activation_swiglu_public_instance_commitment",
    )
    hidden = require_commitment(
        source.get("hidden_activation_commitment"),
        "source_hidden_activation_commitment",
    )
    for anchor in SOURCE_ACTIVATION_ANCHORS:
        if (
            statement == anchor["statement_commitment"]
            and public_instance == anchor["public_instance_commitment"]
            and hidden == anchor["hidden_activation_commitment"]
        ):
            return anchor
    if closest := next(
        (anchor for anchor in SOURCE_ACTIVATION_ANCHORS if hidden == anchor["hidden_activation_commitment"]),
        None,
    ):
        mismatches = []
        if statement != closest["statement_commitment"]:
            mismatches.append("statement_commitment mismatch")
        if public_instance != closest["public_instance_commitment"]:
            mismatches.append("public_instance_commitment mismatch")
        raise D128DownProjectionInputError(
            "source activation/SwiGLU anchor is not approved for "
            f"{closest['kind']} anchor: {', '.join(mismatches)}"
        )
    expected = ", ".join(
        f"{anchor['kind']}={anchor['hidden_activation_commitment']}" for anchor in SOURCE_ACTIVATION_ANCHORS
    )
    raise D128DownProjectionInputError(
        "source activation/SwiGLU anchor is not approved: "
        f"hidden_activation_commitment unknown; expected one of {expected}"
    )


def parse_blake2b_hex(value: str, label: str) -> bytes:
    if not isinstance(value, str):
        raise D128DownProjectionInputError(f"{label} must be a hex digest")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128DownProjectionInputError(f"{label} must be a 32-byte lowercase hex digest")
    return bytes.fromhex(raw)


def require_signed_m31(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128DownProjectionInputError(f"{label} must be an integer")
    if value <= -M31_MODULUS or value >= M31_MODULUS:
        raise D128DownProjectionInputError(f"{label} outside signed M31 bounds")


def require_signed_q8(value: Any, label: str) -> None:
    require_signed_m31(value, label)
    if not (-Q8_SEMANTIC_ABS_BOUND <= value <= Q8_SEMANTIC_ABS_BOUND):
        raise D128DownProjectionInputError(f"{label} outside fixed-point q8 semantic bounds")


def deterministic_int(label: str, *indices: int, min_value: int, max_value: int) -> int:
    if min_value > max_value:
        raise D128DownProjectionInputError("invalid deterministic integer range")
    material = ":".join([WEIGHT_GENERATOR_SEED, label, *(str(index) for index in indices)]).encode("utf-8")
    raw = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return min_value + raw % (max_value - min_value + 1)


def weight_value(matrix: str, row: int, col: int) -> int:
    if matrix != "down":
        raise D128DownProjectionInputError(f"unknown projection matrix: {matrix}")
    return deterministic_int(f"{matrix}_weight_q8", row, col, min_value=-8, max_value=8)


def merkle_root(leaf_hashes: list[str], domain: str) -> str:
    if not leaf_hashes:
        raise D128DownProjectionInputError("cannot commit an empty matrix tree")
    level = leaf_hashes
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = [*level, level[-1]]
        next_level = []
        for index in range(0, len(level), 2):
            next_level.append(
                blake2b_hex(
                    parse_blake2b_hex(level[index], "left matrix hash")
                    + parse_blake2b_hex(level[index + 1], "right matrix hash"),
                    domain,
                )
            )
        level = next_level
    return f"blake2b-256:{level[0]}"


def matrix_row_values(rows: list[dict[str, int]], output_index: int) -> list[int]:
    return [row["weight_q8"] for row in rows if row["output_index"] == output_index]


def matrix_root(rows: list[dict[str, int]]) -> str:
    leaf_hashes = []
    for output_index in range(WIDTH):
        values = matrix_row_values(rows, output_index)
        if len(values) != FF_DIM:
            raise D128DownProjectionInputError("down matrix row width mismatch")
        leaf = {
            "kind": "matrix_row",
            "matrix": "down",
            "row": output_index,
            "shape": [FF_DIM],
            "values_sha256": sha256_hex(values),
        }
        leaf_hashes.append(blake2b_hex(canonical_json_bytes(leaf), MATRIX_ROW_LEAF_DOMAIN))
    return merkle_root(leaf_hashes, MATRIX_ROW_TREE_DOMAIN)


def rows_commitment(rows: list[dict[str, int]]) -> str:
    material = [
        [
            row["row_index"],
            row["output_index"],
            row["hidden_index"],
            row["hidden_q8"],
            row["weight_q8"],
            row["product_q8"],
        ]
        for row in rows
    ]
    return blake2b_commitment(
        {
            "encoding": "d128_down_projection_mul_rows_v1",
            "shape": [len(rows), 6],
            "rows_sha256": sha256_hex(material),
        },
        DOWN_PROJECTION_MUL_ROW_DOMAIN,
    )


def proof_native_parameter_commitment(down_root: str) -> str:
    return blake2b_commitment(
        {
            "down_matrix_root": down_root,
            "ff_dim": FF_DIM,
            "kind": PROOF_NATIVE_PARAMETER_KIND,
            "target_commitment": TARGET_COMMITMENT,
            "weight_generator_seed": WEIGHT_GENERATOR_SEED,
            "width": WIDTH,
        },
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )


def statement_commitment(payload: dict[str, Any]) -> str:
    return blake2b_commitment(
        {
            "down_matrix_root": payload["down_matrix_root"],
            "down_projection_mul_row_commitment": payload["down_projection_mul_row_commitment"],
            "ff_dim": payload["ff_dim"],
            "operation": "down_projection",
            "proof_native_parameter_commitment": payload["proof_native_parameter_commitment"],
            "required_backend_version": REQUIRED_BACKEND_VERSION,
            "residual_delta_commitment": payload["residual_delta_commitment"],
            "residual_delta_scale_divisor": payload["residual_delta_scale_divisor"],
            "row_count": payload["row_count"],
            "source_activation_swiglu_proof_version": SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
            "source_activation_swiglu_public_instance_commitment": payload["source_activation_swiglu_public_instance_commitment"],
            "source_activation_swiglu_statement_commitment": payload["source_activation_swiglu_statement_commitment"],
            "source_hidden_activation_commitment": payload["source_hidden_activation_commitment"],
            "target_commitment": TARGET_COMMITMENT,
            "target_id": TARGET_ID,
            "verifier_domain": VERIFIER_DOMAIN,
            "width": payload["width"],
        },
        VERIFIER_DOMAIN,
    )


def public_instance_commitment(statement: str) -> str:
    return blake2b_commitment(
        {
            "ff_dim": FF_DIM,
            "operation": "down_projection",
            "target_commitment": statement,
            "width": WIDTH,
        },
        PUBLIC_INSTANCE_DOMAIN,
    )


def load_source(path: pathlib.Path = SOURCE_JSON) -> dict[str, Any]:
    try:
        if path.is_symlink():
            raise D128DownProjectionInputError(f"source activation/SwiGLU evidence must not be a symlink: {path}")
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError as err:
            raise D128DownProjectionInputError(f"source activation/SwiGLU evidence escapes repository: {path}") from err
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise D128DownProjectionInputError(f"source activation/SwiGLU evidence is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise D128DownProjectionInputError(f"source activation/SwiGLU evidence is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise D128DownProjectionInputError(f"source activation/SwiGLU evidence changed while reading: {path}")
            with os.fdopen(fd, "rb") as source_file:
                fd = None
                source_bytes = source_file.read(MAX_SOURCE_JSON_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
        if len(source_bytes) > MAX_SOURCE_JSON_BYTES:
            raise D128DownProjectionInputError(
                f"source activation/SwiGLU evidence exceeds max size: got at least {len(source_bytes)} bytes, limit {MAX_SOURCE_JSON_BYTES} bytes"
            )
        payload = json.loads(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128DownProjectionInputError(f"failed to load activation/SwiGLU evidence: {err}") from err
    validate_source(payload)
    return payload


def validate_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise D128DownProjectionInputError("source activation/SwiGLU evidence must be an object")
    constants = {
        "schema": SOURCE_ACTIVATION_SWIGLU_SCHEMA,
        "decision": SOURCE_ACTIVATION_SWIGLU_DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
    }
    for field, expected in constants.items():
        if source.get(field) != expected:
            raise D128DownProjectionInputError(f"source activation/SwiGLU field mismatch: {field}")
    try:
        ACTIVATION_SWIGLU.validate_payload(source)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors for this script.
        raise D128DownProjectionInputError(f"source activation/SwiGLU validation failed: {err}") from err
    source_activation_anchor(source)


def source_hidden_vector(source: dict[str, Any]) -> list[int]:
    validate_source(source)
    hidden = source["hidden_q8"]
    if not isinstance(hidden, list) or len(hidden) != FF_DIM:
        raise D128DownProjectionInputError("source hidden activation vector mismatch")
    for index, item in enumerate(hidden):
        require_signed_m31(item, f"source hidden activation {index}")
    if sequence_commitment(hidden, HIDDEN_ACTIVATION_DOMAIN, [FF_DIM]) != source["hidden_activation_commitment"]:
        raise D128DownProjectionInputError("source hidden activation commitment drift")
    return hidden


def build_rows(hidden: list[int]) -> tuple[list[dict[str, int]], list[int], list[int]]:
    if len(hidden) != FF_DIM:
        raise D128DownProjectionInputError("hidden activation vector length mismatch")
    rows: list[dict[str, int]] = []
    residual_delta: list[int] = []
    residual_delta_remainder: list[int] = []
    row_index = 0
    for output_index in range(WIDTH):
        acc = 0
        for hidden_index, hidden_q8 in enumerate(hidden):
            weight_q8 = weight_value("down", output_index, hidden_index)
            require_signed_m31(hidden_q8, "hidden activation")
            require_signed_q8(weight_q8, "down projection weight")
            product_q8 = hidden_q8 * weight_q8
            require_signed_m31(product_q8, "down projection product")
            rows.append(
                {
                    "row_index": row_index,
                    "output_index": output_index,
                    "hidden_index": hidden_index,
                    "hidden_q8": hidden_q8,
                    "weight_q8": weight_q8,
                    "product_q8": product_q8,
                }
            )
            acc += product_q8
            row_index += 1
        quotient, remainder = divmod(acc, FF_DIM)
        residual_delta.append(quotient)
        residual_delta_remainder.append(remainder)
    return rows, residual_delta, residual_delta_remainder


def build_payload(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = load_source() if source is None else source
    anchor = source_activation_anchor(source)
    hidden = source_hidden_vector(source)
    rows, residual_delta, residual_delta_remainder = build_rows(hidden)
    down_root = matrix_root(rows)
    native_parameter = proof_native_parameter_commitment(down_root)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "row_count": len(rows),
        "down_projection_mul_rows": WIDTH * FF_DIM,
        "residual_delta_rows": WIDTH,
        "source_activation_swiglu_proof_version": SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
        "source_activation_swiglu_statement_commitment": source["statement_commitment"],
        "source_activation_swiglu_public_instance_commitment": source["public_instance_commitment"],
        "source_hidden_activation_commitment": source["hidden_activation_commitment"],
        "down_matrix_root": down_root,
        "proof_native_parameter_commitment": native_parameter,
        "residual_delta_scale_divisor": FF_DIM,
        "residual_delta_commitment": residual_delta_commitment(residual_delta, residual_delta_remainder, FF_DIM),
        "down_projection_mul_row_commitment": rows_commitment(rows),
        "public_instance_commitment": "",
        "statement_commitment": "",
        "hidden_q8": hidden,
        "residual_delta_q8": residual_delta,
        "residual_delta_remainder_q8": residual_delta_remainder,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(anchor["validation_commands"]),
    }
    statement = statement_commitment(payload)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = public_instance_commitment(statement)
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise D128DownProjectionInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "target_id", "required_backend_version", "verifier_domain", "width", "ff_dim",
        "row_count", "down_projection_mul_rows", "residual_delta_rows", "source_activation_swiglu_proof_version",
        "source_activation_swiglu_statement_commitment", "source_activation_swiglu_public_instance_commitment",
        "source_hidden_activation_commitment", "down_matrix_root", "proof_native_parameter_commitment",
        "residual_delta_scale_divisor", "residual_delta_commitment", "down_projection_mul_row_commitment",
        "public_instance_commitment", "statement_commitment", "hidden_q8", "residual_delta_q8",
        "residual_delta_remainder_q8", "non_claims", "proof_verifier_hardening", "next_backend_step",
        "validation_commands",
    }
    if set(payload) != expected_fields:
        raise D128DownProjectionInputError("payload field set mismatch")
    if payload.get("residual_delta_commitment") == OUTPUT_ACTIVATION_COMMITMENT:
        raise D128DownProjectionInputError("residual delta commitment relabeled as full output commitment")
    source_anchor = source_activation_anchor(
        {
            "statement_commitment": payload.get("source_activation_swiglu_statement_commitment"),
            "public_instance_commitment": payload.get("source_activation_swiglu_public_instance_commitment"),
            "hidden_activation_commitment": payload.get("source_hidden_activation_commitment"),
        }
    )
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "row_count": WIDTH * FF_DIM,
        "down_projection_mul_rows": WIDTH * FF_DIM,
        "residual_delta_rows": WIDTH,
        "residual_delta_scale_divisor": FF_DIM,
        "source_activation_swiglu_proof_version": SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
        "source_activation_swiglu_statement_commitment": source_anchor["statement_commitment"],
        "source_activation_swiglu_public_instance_commitment": source_anchor["public_instance_commitment"],
        "source_hidden_activation_commitment": source_anchor["hidden_activation_commitment"],
        "down_matrix_root": DOWN_MATRIX_ROOT,
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "residual_delta_commitment": source_anchor["residual_delta_commitment"],
        "down_projection_mul_row_commitment": source_anchor["down_projection_mul_row_commitment"],
        "public_instance_commitment": source_anchor["public_instance_commitment_out"],
        "statement_commitment": source_anchor["statement_commitment_out"],
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": source_anchor["validation_commands"],
    }
    for field, expected in constants.items():
        if expected == "TO_BE_FILLED":
            continue
        if payload.get(field) != expected:
            raise D128DownProjectionInputError(f"payload field mismatch: {field}")
    for field in (
        "source_activation_swiglu_statement_commitment", "source_activation_swiglu_public_instance_commitment",
        "source_hidden_activation_commitment", "down_matrix_root", "proof_native_parameter_commitment",
        "residual_delta_commitment", "down_projection_mul_row_commitment", "public_instance_commitment", "statement_commitment",
    ):
        require_commitment(payload[field], field)
    hidden = payload["hidden_q8"]
    residual_delta = payload["residual_delta_q8"]
    residual_delta_remainder = payload["residual_delta_remainder_q8"]
    if not isinstance(hidden, list) or len(hidden) != FF_DIM:
        raise D128DownProjectionInputError("hidden activation vector mismatch")
    if not isinstance(residual_delta, list) or len(residual_delta) != WIDTH:
        raise D128DownProjectionInputError("residual delta vector mismatch")
    if not isinstance(residual_delta_remainder, list) or len(residual_delta_remainder) != WIDTH:
        raise D128DownProjectionInputError("residual delta remainder vector mismatch")
    for label, values in (("hidden activation", hidden), ("residual delta", residual_delta)):
        for index, item in enumerate(values):
            if label == "hidden activation" or label == "residual delta":
                require_signed_m31(item, f"{label} {index}")
            else:
                require_signed_q8(item, f"{label} {index}")
    for index, item in enumerate(residual_delta_remainder):
        if not isinstance(item, int) or isinstance(item, bool):
            raise D128DownProjectionInputError(f"residual delta remainder {index} must be an integer")
        if item < 0 or item >= FF_DIM:
            raise D128DownProjectionInputError(f"residual delta remainder {index} outside divisor range")
    if sequence_commitment(hidden, HIDDEN_ACTIVATION_DOMAIN, [FF_DIM]) != payload["source_hidden_activation_commitment"]:
        raise D128DownProjectionInputError("source hidden activation commitment drift")
    rows, recomputed_delta, recomputed_remainder = build_rows(hidden)
    for expected_row_index, row in enumerate(rows):
        expected_keys = {"row_index", "output_index", "hidden_index", "hidden_q8", "weight_q8", "product_q8"}
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise D128DownProjectionInputError("row field set mismatch")
        if row["row_index"] != expected_row_index:
            raise D128DownProjectionInputError("row index drift")
        if not isinstance(row["output_index"], int) or not (0 <= row["output_index"] < WIDTH):
            raise D128DownProjectionInputError("output index drift")
        if not isinstance(row["hidden_index"], int) or not (0 <= row["hidden_index"] < FF_DIM):
            raise D128DownProjectionInputError("hidden index drift")
        for field in ("hidden_q8", "weight_q8", "product_q8"):
            require_signed_m31(row[field], field)
        require_signed_m31(row["hidden_q8"], "hidden_q8")
        require_signed_q8(row["weight_q8"], "weight_q8")
        if row["product_q8"] != row["hidden_q8"] * row["weight_q8"]:
            raise D128DownProjectionInputError("down projection product relation drift")
        if row["weight_q8"] != weight_value("down", row["output_index"], row["hidden_index"]):
            raise D128DownProjectionInputError("down projection weight drift")
        if hidden[row["hidden_index"]] != row["hidden_q8"]:
            raise D128DownProjectionInputError("hidden activation value drift")
    if recomputed_delta != residual_delta:
        raise D128DownProjectionInputError("residual delta output drift")
    if recomputed_remainder != residual_delta_remainder:
        raise D128DownProjectionInputError("residual delta remainder drift")
    if matrix_root(rows) != payload["down_matrix_root"]:
        raise D128DownProjectionInputError("down matrix root recomputation drift")
    if proof_native_parameter_commitment(payload["down_matrix_root"]) != payload["proof_native_parameter_commitment"]:
        raise D128DownProjectionInputError("proof-native parameter commitment drift")
    if residual_delta_commitment(residual_delta, residual_delta_remainder, payload["residual_delta_scale_divisor"]) != payload["residual_delta_commitment"]:
        raise D128DownProjectionInputError("residual delta commitment drift")
    if rows_commitment(rows) != payload["down_projection_mul_row_commitment"]:
        raise D128DownProjectionInputError("down projection row commitment drift")
    if statement_commitment(payload) != payload["statement_commitment"]:
        raise D128DownProjectionInputError("statement commitment drift")
    if public_instance_commitment(payload["statement_commitment"]) != payload["public_instance_commitment"]:
        raise D128DownProjectionInputError("public instance commitment drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    return [
        {
            "target_id": payload["target_id"],
            "decision": payload["decision"],
            "width": payload["width"],
            "ff_dim": payload["ff_dim"],
            "row_count": payload["row_count"],
            "down_projection_mul_rows": payload["down_projection_mul_rows"],
            "residual_delta_rows": payload["residual_delta_rows"],
            "residual_delta_scale_divisor": payload["residual_delta_scale_divisor"],
            "residual_delta_remainder_sha256": sha256_hex(payload["residual_delta_remainder_q8"]),
            "source_hidden_activation_commitment": payload["source_hidden_activation_commitment"],
            "source_activation_swiglu_statement_commitment": payload["source_activation_swiglu_statement_commitment"],
            "source_activation_swiglu_public_instance_commitment": payload["source_activation_swiglu_public_instance_commitment"],
            "down_matrix_root": payload["down_matrix_root"],
            "residual_delta_commitment": payload["residual_delta_commitment"],
            "down_projection_mul_row_commitment": payload["down_projection_mul_row_commitment"],
            "residual_delta_relabels_full_output": str(payload["residual_delta_commitment"] == OUTPUT_ACTIVATION_COMMITMENT).lower(),
            "non_claims": json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
            "next_backend_step": payload["next_backend_step"],
        }
    ]


def _assert_repo_path(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128DownProjectionInputError(f"output path escapes repository: {path}") from err
    if path.is_symlink():
        raise D128DownProjectionInputError(f"output path must not be a symlink: {path}")
    if resolved.exists() and resolved.is_dir():
        raise D128DownProjectionInputError(f"output path must not be a directory: {path}")
    return resolved


def _atomic_write_text(path: pathlib.Path, text: str) -> pathlib.Path:
    resolved = _assert_repo_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
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
        try:
            tmp_path.unlink(missing_ok=True)
        finally:
            raise
    return resolved


def _tsv_text(payload: dict[str, Any]) -> str:
    rows = rows_for_tsv(payload, validated=True)
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    if json_path is not None:
        _atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if tsv_path is not None:
        _atomic_write_text(tsv_path, _tsv_text(payload))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-json", type=pathlib.Path, default=SOURCE_JSON)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(load_source(args.source_json))
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    summary = {
        "schema": SCHEMA,
        "decision": payload["decision"],
        "row_count": payload["row_count"],
        "source_hidden_activation_commitment": payload["source_hidden_activation_commitment"],
        "down_matrix_root": payload["down_matrix_root"],
        "residual_delta_commitment": payload["residual_delta_commitment"],
        "residual_delta_relabels_full_output": False,
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
