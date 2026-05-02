#!/usr/bin/env python3
"""Build the d128 RMSNorm-to-projection bridge proof input.

This native-proof input consumes the checked d128 RMSNorm public-row output and
re-emits the same vector under a projection-input domain. It is deliberately a
bridge slice only: no projection matrix multiplication, activation, residual,
composition, recursion, or full-block metric is claimed here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_JSON = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
TARGET_JSON = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv"

SCHEMA = "zkai-d128-rmsnorm-to-projection-bridge-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_D128_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF"
OPERATION = "rmsnorm_to_projection_bridge"
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
WIDTH = 128
TARGET_COMMITMENT = "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18"
SOURCE_RMSNORM_SCHEMA = "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3"
SOURCE_RMSNORM_DECISION = "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF"
SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION = "stwo-d128-rmsnorm-public-row-air-proof-v3"
SOURCE_RMSNORM_STATEMENT_COMMITMENT = "blake2b-256:de944915f2664ac7a893f4ba9a029323f7408eac58bf39170a0935d7832ccbd8"
SOURCE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:2dfa2ceffd67f95059b3d6cd639a82577f2bbd7be43e99c25814feb703a8fd72"
SOURCE_RMSNORM_OUTPUT_ROW_COMMITMENT = "blake2b-256:d8b6f5e54e874e46624cb9c9987dbcc42db2aa9fc83d4d7230294fbbccb88b87"
SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN = "ptvm:zkai:d128-rmsnorm-output-row:v1"
PROJECTION_INPUT_ROW_DOMAIN = "ptvm:zkai:d128-projection-input-row:v1"
PROOF_NATIVE_PARAMETER_KIND = "d128-rmsnorm-to-projection-bridge-synthetic-parameters-v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:d128-proof-native-parameter-commitment:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:d128-public-instance:v1"
# Guard value from the existing d128 residual-add target evidence. The bridge may
# carry the same coordinates into a projection-input domain, but it must not be
# relabeled as a final block output commitment.
FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:7e6ae6d301fc60ac2232d807d155785eabe653cf4e91971adda470a04246a572"
NEXT_BACKEND_STEP = (
    "encode d128 gate/value projection rows that consume projection_input_row_commitment and produce gate/value projection output commitments"
)
MAX_SOURCE_JSON_BYTES = 1_048_576
MAX_TARGET_JSON_BYTES = 2 * 1024 * 1024
M31_MODULUS = (1 << 31) - 1

NON_CLAIMS = [
    "not full d128 block proof",
    "not gate, value, or down projection proof",
    "not activation, SwiGLU, or residual proof",
    "not binding the full d128 output_activation_commitment",
    "bridge proves only the domain-separated handoff from RMSNorm-local rows to projection-input rows",
]

PROOF_VERIFIER_HARDENING = [
    "source d128 RMSNorm evidence validation before bridge construction",
    "source RMSNorm statement commitment binding before bridge verification",
    "source RMSNorm output row commitment recomputation before proof verification",
    "projection input row commitment recomputation before proof verification",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "AIR equality between RMSNorm-local rows and projection-input rows",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py --write-json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_to_projection_bridge_input",
    "cargo +nightly-2025-07-14 test d128_native_rmsnorm_to_projection_bridge_proof --lib --features stwo-backend",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "operation",
    "width",
    "row_count",
    "source_rmsnorm_public_row_proof_version",
    "source_rmsnorm_statement_commitment",
    "source_rmsnorm_output_row_commitment",
    "projection_input_row_commitment",
    "projection_input_relabels_full_output",
    "statement_commitment",
    "non_claims",
    "next_backend_step",
)


class D128BridgeInputError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def sequence_commitment(values: list[int], domain: str, width: int = WIDTH) -> str:
    values_json = json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": [width],
            "values_sha256": sha256_bytes(values_json),
        },
        domain,
    )


def statement_commitment(payload: dict[str, Any], target_commitment: str) -> str:
    return blake2b_commitment(
        {
            "forbidden_output_activation_commitment": payload["forbidden_output_activation_commitment"],
            "operation": OPERATION,
            "projection_input_row_commitment": payload["projection_input_row_commitment"],
            "projection_input_row_domain": payload["projection_input_row_domain"],
            "required_backend_version": REQUIRED_BACKEND_VERSION,
            "row_count": payload["row_count"],
            "source_rmsnorm_output_row_commitment": payload["source_rmsnorm_output_row_commitment"],
            "source_rmsnorm_output_row_domain": payload["source_rmsnorm_output_row_domain"],
            "source_rmsnorm_public_instance_commitment": payload["source_rmsnorm_public_instance_commitment"],
            "source_rmsnorm_public_row_proof_version": SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
            "source_rmsnorm_statement_commitment": payload["source_rmsnorm_statement_commitment"],
            "target_commitment": target_commitment,
            "target_id": TARGET_ID,
            "verifier_domain": VERIFIER_DOMAIN,
            "width": payload["width"],
        },
        VERIFIER_DOMAIN,
    )


def proof_native_parameter_commitment(statement: str) -> str:
    return blake2b_commitment(
        {"kind": PROOF_NATIVE_PARAMETER_KIND, "target_commitment": statement},
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )


def public_instance_commitment(statement: str, width: int = WIDTH) -> str:
    return blake2b_commitment(
        {"operation": OPERATION, "target_commitment": statement, "width": width},
        PUBLIC_INSTANCE_DOMAIN,
    )


def require_commitment(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("blake2b-256:"):
        raise D128BridgeInputError(f"{label} must be a blake2b-256 commitment")
    digest = value.removeprefix("blake2b-256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise D128BridgeInputError(f"{label} must be a 32-byte lowercase hex digest")
    return value


def require_signed_m31(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128BridgeInputError(f"{label} must be an integer")
    if value <= -M31_MODULUS or value >= M31_MODULUS:
        raise D128BridgeInputError(f"{label} outside signed M31 bounds")


def load_json(path: pathlib.Path, max_bytes: int, label: str) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise D128BridgeInputError(f"{label} is not a regular file: {path}")
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            raise D128BridgeInputError(f"{label} exceeds max size")
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128BridgeInputError(f"failed to load {label}: {err}") from err
    if not isinstance(payload, dict):
        raise D128BridgeInputError(f"{label} must be an object")
    return payload


def load_target(path: pathlib.Path = TARGET_JSON) -> dict[str, Any]:
    target = load_json(path, MAX_TARGET_JSON_BYTES, "d128 target evidence")
    validate_target(target)
    return target


def validate_target(target: Any) -> str:
    if not isinstance(target, dict):
        raise D128BridgeInputError("target evidence must be an object")
    summary = target.get("summary")
    if not isinstance(summary, dict):
        raise D128BridgeInputError("target summary missing")
    if summary.get("target_commitment") is None:
        raise D128BridgeInputError("target commitment missing")
    target_commitment = require_commitment(summary["target_commitment"], "target commitment")
    if target_commitment != TARGET_COMMITMENT:
        raise D128BridgeInputError("target commitment drift")
    spec = target.get("target_spec")
    if not isinstance(spec, dict):
        raise D128BridgeInputError("target spec missing")
    if spec.get("target_id") != TARGET_ID or spec.get("width") != WIDTH:
        raise D128BridgeInputError("target spec mismatch")
    if spec.get("target_commitment") != TARGET_COMMITMENT:
        raise D128BridgeInputError("target spec commitment drift")
    if spec.get("required_proof_backend_version") != REQUIRED_BACKEND_VERSION:
        raise D128BridgeInputError("target backend version drift")
    return target_commitment


def load_source(path: pathlib.Path = SOURCE_JSON) -> dict[str, Any]:
    source = load_json(path, MAX_SOURCE_JSON_BYTES, "source RMSNorm public-row evidence")
    validate_source(source)
    return source


def validate_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise D128BridgeInputError("source evidence must be an object")
    constants = {
        "schema": SOURCE_RMSNORM_SCHEMA,
        "decision": SOURCE_RMSNORM_DECISION,
        "operation": "rmsnorm_public_rows",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
    }
    for field, expected in constants.items():
        if source.get(field) != expected:
            raise D128BridgeInputError(f"source field mismatch: {field}")
    for field in (
        "statement_commitment",
        "public_instance_commitment",
        "rmsnorm_output_row_commitment",
    ):
        require_commitment(source.get(field), f"source {field}")
    if source["statement_commitment"] != SOURCE_RMSNORM_STATEMENT_COMMITMENT:
        raise D128BridgeInputError("source RMSNorm statement commitment drift")
    if source["public_instance_commitment"] != SOURCE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT:
        raise D128BridgeInputError("source RMSNorm public-instance commitment drift")
    if source["rmsnorm_output_row_commitment"] != SOURCE_RMSNORM_OUTPUT_ROW_COMMITMENT:
        raise D128BridgeInputError("source RMSNorm output row commitment drift")
    rows = source.get("rows")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise D128BridgeInputError("source rows mismatch")
    values: list[int] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("index") != index:
            raise D128BridgeInputError("source row index mismatch")
        value = row.get("normed_q8")
        require_signed_m31(value, "source normed_q8")
        values.append(value)
    if sequence_commitment(values, SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN) != source["rmsnorm_output_row_commitment"]:
        raise D128BridgeInputError("source RMSNorm output row commitment drift")


def build_payload(source: dict[str, Any] | None = None, target: dict[str, Any] | None = None) -> dict[str, Any]:
    source = load_source() if source is None else source
    validate_source(source)
    target = load_target() if target is None else target
    target_commitment = validate_target(target)
    rows = [
        {
            "index": row["index"],
            "rmsnorm_normed_q8": row["normed_q8"],
            "projection_input_q8": row["normed_q8"],
        }
        for row in source["rows"]
    ]
    values = [row["projection_input_q8"] for row in rows]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "operation": OPERATION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_rmsnorm_public_row_proof_version": SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "source_rmsnorm_statement_commitment": source["statement_commitment"],
        "source_rmsnorm_public_instance_commitment": source["public_instance_commitment"],
        "source_rmsnorm_output_row_domain": SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN,
        "projection_input_row_domain": PROJECTION_INPUT_ROW_DOMAIN,
        "source_rmsnorm_output_row_commitment": source["rmsnorm_output_row_commitment"],
        "projection_input_row_commitment": sequence_commitment(values, PROJECTION_INPUT_ROW_DOMAIN),
        "forbidden_output_activation_commitment": FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT,
        "public_instance_commitment": "",
        "proof_native_parameter_commitment": "",
        "statement_commitment": "",
        "rows": rows,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    statement = statement_commitment(payload, target_commitment)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = public_instance_commitment(statement)
    payload["proof_native_parameter_commitment"] = proof_native_parameter_commitment(statement)
    validate_payload(payload, target=target)
    return payload


def validate_payload(payload: Any, *, target: dict[str, Any] | None = None) -> None:
    if not isinstance(payload, dict):
        raise D128BridgeInputError("payload must be an object")
    expected_fields = {
        "schema",
        "decision",
        "operation",
        "target_id",
        "required_backend_version",
        "verifier_domain",
        "width",
        "row_count",
        "source_rmsnorm_public_row_proof_version",
        "source_rmsnorm_statement_commitment",
        "source_rmsnorm_public_instance_commitment",
        "source_rmsnorm_output_row_domain",
        "projection_input_row_domain",
        "source_rmsnorm_output_row_commitment",
        "projection_input_row_commitment",
        "forbidden_output_activation_commitment",
        "public_instance_commitment",
        "proof_native_parameter_commitment",
        "statement_commitment",
        "rows",
        "non_claims",
        "proof_verifier_hardening",
        "next_backend_step",
        "validation_commands",
    }
    if set(payload) != expected_fields:
        raise D128BridgeInputError("payload field set mismatch")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "operation": OPERATION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_rmsnorm_public_row_proof_version": SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "source_rmsnorm_output_row_domain": SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN,
        "projection_input_row_domain": PROJECTION_INPUT_ROW_DOMAIN,
        "forbidden_output_activation_commitment": FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    for field, expected in constants.items():
        if payload.get(field) != expected:
            raise D128BridgeInputError(f"payload field mismatch: {field}")
    for field in (
        "source_rmsnorm_statement_commitment",
        "source_rmsnorm_public_instance_commitment",
        "source_rmsnorm_output_row_commitment",
        "projection_input_row_commitment",
        "forbidden_output_activation_commitment",
        "public_instance_commitment",
        "proof_native_parameter_commitment",
        "statement_commitment",
    ):
        require_commitment(payload[field], field)
    if payload["projection_input_row_commitment"] == payload["forbidden_output_activation_commitment"]:
        raise D128BridgeInputError("projection input commitment relabeled as full output commitment")
    rows = payload["rows"]
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise D128BridgeInputError("row vector mismatch")
    rms_values: list[int] = []
    projection_values: list[int] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"index", "rmsnorm_normed_q8", "projection_input_q8"}:
            raise D128BridgeInputError("row field set mismatch")
        if row["index"] != index:
            raise D128BridgeInputError("row index drift")
        require_signed_m31(row["rmsnorm_normed_q8"], "rmsnorm_normed_q8")
        require_signed_m31(row["projection_input_q8"], "projection_input_q8")
        if row["rmsnorm_normed_q8"] != row["projection_input_q8"]:
            raise D128BridgeInputError("bridge row equality drift")
        rms_values.append(row["rmsnorm_normed_q8"])
        projection_values.append(row["projection_input_q8"])
    if sequence_commitment(rms_values, SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN) != payload["source_rmsnorm_output_row_commitment"]:
        raise D128BridgeInputError("source RMSNorm output commitment recomputation drift")
    if sequence_commitment(projection_values, PROJECTION_INPUT_ROW_DOMAIN) != payload["projection_input_row_commitment"]:
        raise D128BridgeInputError("projection input commitment recomputation drift")
    target = load_target() if target is None else target
    target_commitment = validate_target(target)
    statement = statement_commitment(payload, target_commitment)
    if payload["statement_commitment"] != statement:
        raise D128BridgeInputError("statement commitment drift")
    if payload["public_instance_commitment"] != public_instance_commitment(statement):
        raise D128BridgeInputError("public instance commitment drift")
    if payload["proof_native_parameter_commitment"] != proof_native_parameter_commitment(statement):
        raise D128BridgeInputError("proof-native parameter commitment drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    return [
        {
            "target_id": payload["target_id"],
            "decision": payload["decision"],
            "operation": payload["operation"],
            "width": payload["width"],
            "row_count": payload["row_count"],
            "source_rmsnorm_public_row_proof_version": payload["source_rmsnorm_public_row_proof_version"],
            "source_rmsnorm_statement_commitment": payload["source_rmsnorm_statement_commitment"],
            "source_rmsnorm_output_row_commitment": payload["source_rmsnorm_output_row_commitment"],
            "projection_input_row_commitment": payload["projection_input_row_commitment"],
            "projection_input_relabels_full_output": str(
                payload["projection_input_row_commitment"] == payload["forbidden_output_activation_commitment"]
            ).lower(),
            "statement_commitment": payload["statement_commitment"],
            "non_claims": json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
            "next_backend_step": payload["next_backend_step"],
        }
    ]


def _assert_repo_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise D128BridgeInputError(f"output path must not be a symlink: {path}")
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128BridgeInputError(f"output path escapes repository: {path}") from err
    if resolved.exists() and resolved.is_dir():
        raise D128BridgeInputError(f"output path must not be a directory: {path}")
    parent = resolved.parent
    if parent.exists() and not parent.is_dir():
        raise D128BridgeInputError(f"output parent is not a directory: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _fsync_parent_directories(paths: list[pathlib.Path]) -> None:
    seen: set[pathlib.Path] = set()
    for path in paths:
        parent = path.resolve().parent
        if parent in seen:
            continue
        seen.add(parent)
        flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
        try:
            fd = os.open(parent, flags)
        except OSError:
            continue
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _atomic_write_text(path: pathlib.Path, text: str) -> pathlib.Path:
    resolved = _assert_repo_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=resolved.parent, delete=False) as handle:
        tmp = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(tmp, resolved)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return resolved


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    written: list[pathlib.Path] = []
    if json_path is not None:
        written.append(_atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"))
    if tsv_path is not None:
        from io import StringIO

        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_for_tsv(payload, validated=True))
        written.append(_atomic_write_text(tsv_path, buffer.getvalue()))
    _fsync_parent_directories(written)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-json", type=pathlib.Path, default=SOURCE_JSON)
    parser.add_argument("--target-json", type=pathlib.Path, default=TARGET_JSON)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(load_source(args.source_json), load_target(args.target_json))
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "decision": payload["decision"],
                    "source_rmsnorm_output_row_commitment": payload["source_rmsnorm_output_row_commitment"],
                    "projection_input_row_commitment": payload["projection_input_row_commitment"],
                    "projection_input_relabels_full_output": False,
                    "row_count": payload["row_count"],
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
