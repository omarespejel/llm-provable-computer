#!/usr/bin/env python3
"""Check per-tensor range policy for d64/d128 transformer-block receipts.

The d64 fixture happened to stay inside the old q8 semantic magnitude bound.
The d128 block does not: projection outputs, SwiGLU hidden activations,
residual deltas, and final outputs exceed +/-1024 while still satisfying the
signed-M31 statement domain used by the slice verifiers.

This gate turns that observation into checked evidence. The d128 receipt
composition gate consumes the resulting commitment as statement data, so range
policy is bound per tensor identity rather than applied as one global q8 rule.
"""

from __future__ import annotations

import argparse
import copy
import csv
import dataclasses
import hashlib
import io
import json
import os
import pathlib
import re
import stat as stat_module
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-range-policy-discipline-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-range-policy-discipline-2026-05.tsv"

SCHEMA = "zkai-d128-range-policy-discipline-gate-v1"
DECISION = "GO_PER_TENSOR_RANGE_POLICY_REQUIRED_FOR_D128_BLOCK"
Q8_SEMANTIC_ABS_BOUND = 1024
M31_MODULUS = (1 << 31) - 1
MAX_SOURCE_JSON_BYTES = 16 * 1024 * 1024

RANGE_POLICY_DOMAIN = "ptvm:zkai:d128-range-policy-discipline:v1"

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_range_policy_discipline_gate.py --write-json docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_range_policy_discipline_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate-fast",
    "just gate",
]

NON_CLAIMS = [
    "not a new d128 proof object",
    "not recursive aggregation",
    "not proof-size or verifier-time benchmark evidence",
    "not a claim that q8 semantic bounds are wrong for weights or selected public rows",
    "not a claim that d64 and d128 use different arithmetic semantics",
]

TSV_COLUMNS = (
    "dimension",
    "source_slice",
    "tensor_id",
    "policy",
    "element_count",
    "min",
    "max",
    "max_abs",
    "outside_q8_count",
    "outside_q8_allowed",
    "signed_m31_ok",
    "policy_accepts",
)


class D128RangePolicyError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class SourceSpec:
    source_id: str
    dimension: str
    slice_id: str
    path: pathlib.Path
    schema: str
    decision: str


@dataclasses.dataclass(frozen=True)
class TensorSpec:
    dimension: str
    source_id: str
    source_slice: str
    tensor_id: str
    field_path: str
    policy: str
    outside_q8_allowed: bool
    q8_required: bool = False
    signed_m31_required: bool = True
    divisor_field: str | None = None


SOURCE_SPECS = (
    SourceSpec(
        "d64_rmsnorm",
        "d64",
        "rmsnorm_public_rows",
        EVIDENCE_DIR / "zkai-d64-native-rmsnorm-public-row-proof-2026-05.json",
        "zkai-d64-native-rmsnorm-public-row-air-proof-input-v2",
        "GO_PUBLIC_ROW_INPUT_FOR_D64_RMSNORM_AIR_PROOF",
    ),
    SourceSpec(
        "d64_gate_value",
        "d64",
        "gate_value_projection",
        EVIDENCE_DIR / "zkai-d64-gate-value-projection-proof-2026-05.json",
        "zkai-d64-gate-value-projection-air-proof-input-v2",
        "GO_INPUT_FOR_D64_GATE_VALUE_PROJECTION_AIR_PROOF",
    ),
    SourceSpec(
        "d64_activation",
        "d64",
        "activation_swiglu",
        EVIDENCE_DIR / "zkai-d64-activation-swiglu-proof-2026-05.json",
        "zkai-d64-activation-swiglu-air-proof-input-v1",
        "GO_INPUT_FOR_D64_ACTIVATION_SWIGLU_AIR_PROOF",
    ),
    SourceSpec(
        "d64_down",
        "d64",
        "down_projection",
        EVIDENCE_DIR / "zkai-d64-down-projection-proof-2026-05.json",
        "zkai-d64-down-projection-air-proof-input-v2",
        "GO_INPUT_FOR_D64_DOWN_PROJECTION_AIR_PROOF",
    ),
    SourceSpec(
        "d64_residual",
        "d64",
        "residual_add",
        EVIDENCE_DIR / "zkai-d64-residual-add-proof-2026-05.json",
        "zkai-d64-residual-add-air-proof-input-v1",
        "GO_INPUT_FOR_D64_RESIDUAL_ADD_AIR_PROOF",
    ),
    SourceSpec(
        "d128_rmsnorm",
        "d128",
        "rmsnorm_public_rows",
        EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json",
        "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3",
        "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF",
    ),
    SourceSpec(
        "d128_gate_value",
        "d128",
        "gate_value_projection",
        EVIDENCE_DIR / "zkai-d128-gate-value-projection-proof-2026-05.json",
        "zkai-d128-gate-value-projection-air-proof-input-v1",
        "GO_INPUT_FOR_D128_GATE_VALUE_PROJECTION_AIR_PROOF",
    ),
    SourceSpec(
        "d128_activation",
        "d128",
        "activation_swiglu",
        EVIDENCE_DIR / "zkai-d128-activation-swiglu-proof-2026-05.json",
        "zkai-d128-activation-swiglu-air-proof-input-v1",
        "GO_INPUT_FOR_D128_ACTIVATION_SWIGLU_AIR_PROOF",
    ),
    SourceSpec(
        "d128_down",
        "d128",
        "down_projection",
        EVIDENCE_DIR / "zkai-d128-down-projection-proof-2026-05.json",
        "zkai-d128-down-projection-air-proof-input-v1",
        "GO_INPUT_FOR_D128_DOWN_PROJECTION_AIR_PROOF",
    ),
    SourceSpec(
        "d128_residual",
        "d128",
        "residual_add",
        EVIDENCE_DIR / "zkai-d128-residual-add-proof-2026-05.json",
        "zkai-d128-residual-add-air-proof-input-v1",
        "GO_INPUT_FOR_D128_RESIDUAL_ADD_AIR_PROOF",
    ),
)


def tensor_specs_for(dimension: str) -> tuple[TensorSpec, ...]:
    prefix = dimension
    return (
        TensorSpec(prefix, f"{prefix}_rmsnorm", "rmsnorm_public_rows", "input_activation", "rows.input_q8", "q8_semantic_bound_1024", False, q8_required=True),
        TensorSpec(prefix, f"{prefix}_rmsnorm", "rmsnorm_public_rows", "rmsnorm_normed", "rows.normed_q8", "q8_semantic_bound_1024", False, q8_required=True),
        TensorSpec(prefix, f"{prefix}_rmsnorm", "rmsnorm_public_rows", "rmsnorm_scaled_floor", "rows.scaled_floor", "q8_semantic_bound_1024", False, q8_required=True),
        TensorSpec(prefix, f"{prefix}_gate_value", "gate_value_projection", "projection_input", "projection_input_q8", "q8_semantic_bound_1024", False, q8_required=True),
        TensorSpec(prefix, f"{prefix}_gate_value", "gate_value_projection", "gate_projection_output", "gate_projection_q8", "signed_m31_fixed_point_projection_output", True),
        TensorSpec(prefix, f"{prefix}_gate_value", "gate_value_projection", "value_projection_output", "value_projection_q8", "signed_m31_fixed_point_projection_output", True),
        TensorSpec(prefix, f"{prefix}_activation", "activation_swiglu", "activated_gate_lut", "activated_gate_q8", "activation_lut_clamp_bound_1024", False, q8_required=True),
        TensorSpec(prefix, f"{prefix}_activation", "activation_swiglu", "hidden_activation", "hidden_q8", "signed_m31_post_swiglu_hidden", True),
        TensorSpec(prefix, f"{prefix}_down", "down_projection", "residual_delta", "residual_delta_q8", "signed_m31_quotient_remainder_bound", True, divisor_field="residual_delta_scale_divisor"),
        TensorSpec(prefix, f"{prefix}_down", "down_projection", "residual_delta_remainder", "residual_delta_remainder_q8", "bounded_nonnegative_remainder", False, signed_m31_required=False, divisor_field="residual_delta_scale_divisor"),
        TensorSpec(prefix, f"{prefix}_residual", "residual_add", "final_output_activation", "output_q8", "signed_m31_residual_output", True),
    )


TENSOR_SPECS = (*tensor_specs_for("d64"), *tensor_specs_for("d128"))


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


def expect_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise D128RangePolicyError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def expect_key_set(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise D128RangePolicyError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise D128RangePolicyError(f"{label} key mismatch: missing={missing}, extra={extra}")


def relative_path(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _read_repo_regular_file_bytes(path: pathlib.Path) -> bytes:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise D128RangePolicyError(f"source evidence must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128RangePolicyError(f"source evidence escapes repository: {path}") from err
    try:
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise D128RangePolicyError(f"source evidence is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise D128RangePolicyError(f"source evidence is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise D128RangePolicyError(f"source evidence changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                data = handle.read(MAX_SOURCE_JSON_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise D128RangePolicyError(f"failed to read source evidence {path}: {err}") from err
    if len(data) > MAX_SOURCE_JSON_BYTES:
        raise D128RangePolicyError(f"source evidence exceeds max size: {path}")
    return data


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        payload = parse_json_bytes(_read_repo_regular_file_bytes(path), path)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128RangePolicyError(f"failed to parse source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D128RangePolicyError(f"source evidence must be an object: {path}")
    return payload


def parse_json_bytes(raw: bytes, path: pathlib.Path) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128RangePolicyError(f"failed to parse source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D128RangePolicyError(f"source evidence must be an object: {path}")
    return payload


def validate_source_payload(source: dict[str, Any], spec: SourceSpec) -> None:
    expect_equal(source.get("schema"), spec.schema, f"{spec.source_id} schema")
    expect_equal(source.get("decision"), spec.decision, f"{spec.source_id} decision")
    if not str(source.get("target_id", "")).startswith("rmsnorm-swiglu-residual"):
        raise D128RangePolicyError(f"{spec.source_id} target_id drift")
    if spec.dimension == "d64":
        expect_equal(source.get("width"), 64, f"{spec.source_id} width")
    if spec.dimension == "d128":
        expect_equal(source.get("width"), 128, f"{spec.source_id} width")
    verifier_domain = source.get("verifier_domain")
    if not isinstance(verifier_domain, str) or not verifier_domain:
        raise D128RangePolicyError(f"{spec.source_id} verifier_domain missing")
    dimension_pattern = re.compile(rf"(^|:){re.escape(spec.dimension)}(-|:)")
    if not dimension_pattern.search(verifier_domain):
        raise D128RangePolicyError(f"{spec.source_id} verifier domain dimension drift")


def source_snapshots() -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        raw = _read_repo_regular_file_bytes(spec.path)
        payload = parse_json_bytes(raw, spec.path)
        validate_source_payload(payload, spec)
        snapshots[spec.source_id] = {
            "payload": payload,
            "file_sha256": sha256_hex_bytes(raw),
            "payload_sha256": sha256_hex_json(payload),
        }
    return snapshots


def source_payloads() -> dict[str, dict[str, Any]]:
    snapshots = source_snapshots()
    payloads: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        payloads[spec.source_id] = snapshots[spec.source_id]["payload"]
    return payloads


def source_manifest(snapshots: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    manifest = []
    for index, spec in enumerate(SOURCE_SPECS):
        snapshot = snapshots[spec.source_id]
        manifest.append(
            {
                "index": index,
                "source_id": spec.source_id,
                "dimension": spec.dimension,
                "slice_id": spec.slice_id,
                "path": relative_path(spec.path),
                "schema": spec.schema,
                "decision": spec.decision,
                "file_sha256": snapshot["file_sha256"],
                "payload_sha256": snapshot["payload_sha256"],
            }
        )
    return manifest


def extract_values(payload: dict[str, Any], path: str) -> list[int]:
    if path.startswith("rows."):
        field = path.split(".", 1)[1]
        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows:
            raise D128RangePolicyError(f"{path} source rows missing")
        values = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise D128RangePolicyError(f"{path} row {index} must be an object")
            value = row.get(field)
            if not isinstance(value, int) or isinstance(value, bool):
                raise D128RangePolicyError(f"{path} row {index} value must be an integer")
            values.append(value)
        return values
    value = payload.get(path)
    if not isinstance(value, list) or not value:
        raise D128RangePolicyError(f"{path} must be a non-empty list")
    values = []
    for index, item in enumerate(value):
        if not isinstance(item, int) or isinstance(item, bool):
            raise D128RangePolicyError(f"{path}[{index}] must be an integer")
        values.append(item)
    return values


def signed_m31_ok(values: list[int]) -> bool:
    return all(-M31_MODULUS < value < M31_MODULUS for value in values)


def policy_accepts(spec: TensorSpec, values: list[int], source: dict[str, Any]) -> tuple[bool, str]:
    if spec.signed_m31_required and not signed_m31_ok(values):
        return False, "signed M31 bound violation"
    outside = sum(1 for value in values if abs(value) > Q8_SEMANTIC_ABS_BOUND)
    if spec.q8_required and outside:
        return False, "q8 semantic bound violation"
    if spec.policy == "bounded_nonnegative_remainder":
        if spec.divisor_field is None:
            return False, "remainder divisor missing"
        divisor = source.get(spec.divisor_field)
        if not isinstance(divisor, int) or divisor <= 0:
            return False, "remainder divisor invalid"
        if any(value < 0 or value >= divisor for value in values):
            return False, "remainder outside divisor range"
    if outside and not spec.outside_q8_allowed:
        return False, "q8 outside count not allowed by policy"
    return True, "accepted"


def tensor_policy_rows(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for spec in TENSOR_SPECS:
        source = payloads[spec.source_id]
        values = extract_values(source, spec.field_path)
        outside_q8_count = sum(1 for value in values if abs(value) > Q8_SEMANTIC_ABS_BOUND)
        accepts, reason = policy_accepts(spec, values, source)
        rows.append(
            {
                "dimension": spec.dimension,
                "source_slice": spec.source_slice,
                "source_id": spec.source_id,
                "tensor_id": spec.tensor_id,
                "field_path": spec.field_path,
                "policy": spec.policy,
                "element_count": len(values),
                "min": min(values),
                "max": max(values),
                "max_abs": max(abs(value) for value in values),
                "outside_q8_count": outside_q8_count,
                "outside_q8_allowed": spec.outside_q8_allowed,
                "q8_required": spec.q8_required,
                "signed_m31_required": spec.signed_m31_required,
                "signed_m31_ok": signed_m31_ok(values),
                "policy_accepts": accepts,
                "policy_reason": reason,
            }
        )
    return rows


def _non_remainder(row: dict[str, Any]) -> bool:
    return row["policy"] != "bounded_nonnegative_remainder"


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_dimension = {
        dimension: [row for row in rows if row["dimension"] == dimension and _non_remainder(row)]
        for dimension in ("d64", "d128")
    }
    d128_outside = [row for row in by_dimension["d128"] if row["outside_q8_count"] > 0]
    d64_outside = [row for row in by_dimension["d64"] if row["outside_q8_count"] > 0]
    hidden = next(row for row in rows if row["dimension"] == "d128" and row["tensor_id"] == "hidden_activation")
    residual = next(row for row in rows if row["dimension"] == "d128" and row["tensor_id"] == "residual_delta")
    output = next(row for row in rows if row["dimension"] == "d128" and row["tensor_id"] == "final_output_activation")
    return {
        "tensor_policy_count": len(rows),
        "q8_semantic_abs_bound": Q8_SEMANTIC_ABS_BOUND,
        "m31_modulus": M31_MODULUS,
        "all_policies_accept": all(row["policy_accepts"] for row in rows),
        "d64_global_q8_happens_to_hold": not d64_outside,
        "d128_global_q8_policy_rejected": bool(d128_outside),
        "d128_outside_q8_tensor_count": len(d128_outside),
        "d128_outside_q8_tensors": [row["tensor_id"] for row in d128_outside],
        "d128_hidden_outside_q8_count": hidden["outside_q8_count"],
        "d128_residual_delta_outside_q8_count": residual["outside_q8_count"],
        "d128_output_outside_q8_count": output["outside_q8_count"],
        "d128_max_abs": max(row["max_abs"] for row in by_dimension["d128"]),
        "interpretation": "d128 proves that statement-bound transformer receipts need tensor-identity-specific range policy; d64 staying inside +/-1024 was fixture-specific, not a universal verifier rule.",
    }


def build_core_payload() -> dict[str, Any]:
    snapshots = source_snapshots()
    payloads = {spec.source_id: snapshots[spec.source_id]["payload"] for spec in SOURCE_SPECS}
    rows = tensor_policy_rows(payloads)
    policy_commitment = blake2b_commitment(rows, RANGE_POLICY_DOMAIN)
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "question": "Does the d128 statement-bound transformer block require per-tensor range policy rather than one global q8 semantic bound?",
        "source_evidence_manifest": source_manifest(snapshots),
        "range_policy_commitment": policy_commitment,
        "tensor_policies": rows,
        "summary": build_summary(rows) | {"range_policy_commitment": policy_commitment},
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }


def checked_range_policy_commitment() -> str:
    payload = build_core_payload()
    validate_payload(payload, require_mutations=False)
    commitment = payload["range_policy_commitment"]
    if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
        raise D128RangePolicyError("range_policy_commitment must be a blake2b-256 commitment")
    return commitment


def _core_fields(payload: dict[str, Any]) -> dict[str, Any]:
    core = {
        key: copy.deepcopy(value)
        for key, value in payload.items()
        if key not in {"case_count", "all_mutations_rejected", "cases"}
    }
    if isinstance(core.get("summary"), dict):
        core["summary"].pop("mutation_cases", None)
        core["summary"].pop("mutations_rejected", None)
    return core


def _validate_core(payload: dict[str, Any]) -> None:
    expected = build_core_payload()
    actual_core = _core_fields(payload)
    if actual_core != expected:
        for key in sorted(set(actual_core) | set(expected)):
            if actual_core.get(key) != expected.get(key):
                raise D128RangePolicyError(f"core payload drift at {key}")
        raise D128RangePolicyError("core payload drift")


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []

    def add(name: str, surface: str, mutator: Any) -> None:
        mutated = copy.deepcopy(baseline)
        mutator(mutated)
        cases.append((name, surface, mutated))

    def row(dimension: str, tensor_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        for item in payload["tensor_policies"]:
            if item["dimension"] == dimension and item["tensor_id"] == tensor_id:
                return item
        raise AssertionError((dimension, tensor_id))

    def manifest_entry(payload: dict[str, Any], source_id: str) -> dict[str, Any]:
        for item in payload["source_evidence_manifest"]:
            if item["source_id"] == source_id:
                return item
        raise AssertionError(source_id)

    add(
        "d128_hidden_reclassified_as_q8",
        "range_policy",
        lambda p: row("d128", "hidden_activation", p).__setitem__("policy", "q8_semantic_bound_1024"),
    )
    add(
        "d128_residual_delta_reclassified_as_q8",
        "range_policy",
        lambda p: row("d128", "residual_delta", p).__setitem__("q8_required", True),
    )
    add(
        "d128_gate_projection_outside_count_erased",
        "range_policy",
        lambda p: row("d128", "gate_projection_output", p).__setitem__("outside_q8_count", 0),
    )
    add(
        "d128_output_signed_m31_violation_hidden",
        "range_policy",
        lambda p: row("d128", "final_output_activation", p).__setitem__("signed_m31_ok", False),
    )
    add(
        "d64_happens_to_fit_rewritten_as_universal_rule",
        "summary",
        lambda p: p["summary"].__setitem__("interpretation", "global q8 bounds are universal"),
    )
    add(
        "d128_global_q8_rejection_removed",
        "summary",
        lambda p: p["summary"].__setitem__("d128_global_q8_policy_rejected", False),
    )
    add(
        "range_policy_commitment_drift",
        "range_policy_commitment",
        lambda p: p.__setitem__("range_policy_commitment", "blake2b-256:" + "00" * 32),
    )
    add(
        "source_manifest_schema_drift",
        "source_evidence_manifest",
        lambda p: manifest_entry(p, "d128_activation").__setitem__(
            "schema",
            "zkai-d128-activation-swiglu-air-proof-input-v2",
        ),
    )
    add(
        "validation_command_drift",
        "validation_commands",
        lambda p: p["validation_commands"].pop(),
    )
    add(
        "unknown_top_level_field",
        "parser_or_schema",
        lambda p: p.__setitem__("extra", "forbidden"),
    )
    return cases


def expected_mutation_inventory() -> list[dict[str, str]]:
    return [
        {"mutation": mutation, "surface": surface, "rejection_layer": surface}
        for mutation, surface, _mutated in _mutated_cases(build_core_payload())
    ]


ERROR_LAYER_PATTERNS = (
    (re.compile(r"\bsource_evidence_manifest\b"), "source_evidence_manifest"),
    (re.compile(r"\bvalidation_commands\b|\bvalidation commands\b"), "validation_commands"),
    (re.compile(r"\brange_policy_commitment\b"), "range_policy_commitment"),
    (re.compile(r"\bsummary\b"), "summary"),
    (re.compile(r"\bkey mismatch\b|\bextra="), "parser_or_schema"),
    (re.compile(r"\btensor_policies\b"), "range_policy"),
    (re.compile(r"\brange\b|\bpolicy\b"), "range_policy"),
)


def classify_error(error: Exception) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and code:
        return code
    text = str(error).lower()
    for pattern, layer in ERROR_LAYER_PATTERNS:
        if pattern.search(text):
            return layer
    return "parser_or_schema"


def mutation_cases(baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_core_payload())
    validate_payload(baseline, require_mutations=False)
    cases = []
    for mutation, surface, mutated in _mutated_cases(baseline):
        try:
            validate_payload(mutated, require_mutations=False)
            accepted = True
            error = ""
            layer = "accepted"
        except D128RangePolicyError as err:
            accepted = False
            error = str(err)
            layer = classify_error(err)
        cases.append(
            {
                "mutation": mutation,
                "surface": surface,
                "baseline_accepted": True,
                "mutated_accepted": accepted,
                "rejected": not accepted,
                "rejection_layer": layer,
                "error": error,
            }
        )
    return cases


def build_gate_result() -> dict[str, Any]:
    payload = build_core_payload()
    cases = mutation_cases(payload)
    result = copy.deepcopy(payload)
    result["case_count"] = len(cases)
    result["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    result["cases"] = cases
    result["summary"]["mutation_cases"] = len(cases)
    result["summary"]["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    validate_payload(result)
    if not result["all_mutations_rejected"]:
        raise D128RangePolicyError("not all range-policy mutations rejected")
    return result


def validate_payload(payload: Any, *, require_mutations: bool = True) -> None:
    if not isinstance(payload, dict):
        raise D128RangePolicyError("range-policy payload must be an object")
    expected_keys = {
        "schema",
        "decision",
        "question",
        "source_evidence_manifest",
        "range_policy_commitment",
        "tensor_policies",
        "summary",
        "non_claims",
        "validation_commands",
    }
    if require_mutations:
        expected_keys |= {"case_count", "all_mutations_rejected", "cases"}
    expect_key_set(payload, expected_keys, "range-policy payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non_claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    _validate_core(payload)
    summary = payload["summary"]
    expected_summary_keys = {
        "tensor_policy_count",
        "q8_semantic_abs_bound",
        "m31_modulus",
        "all_policies_accept",
        "d64_global_q8_happens_to_hold",
        "d128_global_q8_policy_rejected",
        "d128_outside_q8_tensor_count",
        "d128_outside_q8_tensors",
        "d128_hidden_outside_q8_count",
        "d128_residual_delta_outside_q8_count",
        "d128_output_outside_q8_count",
        "d128_max_abs",
        "interpretation",
        "range_policy_commitment",
    }
    if require_mutations:
        expected_summary_keys |= {"mutation_cases", "mutations_rejected"}
    expect_key_set(summary, expected_summary_keys, "summary")
    expect_equal(summary["all_policies_accept"], True, "all policies accept")
    expect_equal(summary["d64_global_q8_happens_to_hold"], True, "d64 q8 fixture fit")
    expect_equal(summary["d128_global_q8_policy_rejected"], True, "d128 global q8 rejection")
    expect_equal(summary["d128_hidden_outside_q8_count"], 491, "d128 hidden outside q8 count")
    expect_equal(summary["d128_residual_delta_outside_q8_count"], 111, "d128 residual outside q8 count")
    expect_equal(summary["d128_output_outside_q8_count"], 111, "d128 output outside q8 count")
    expect_equal(summary["d128_max_abs"], 112680, "d128 max abs")
    if require_mutations:
        cases = payload.get("cases")
        if not isinstance(cases, list):
            raise D128RangePolicyError("mutation cases must be a list")
        expected = expected_mutation_inventory()
        expect_equal(payload.get("case_count"), len(cases), "case count length")
        expect_equal(payload.get("case_count"), len(expected), "case count inventory")
        expect_equal(summary.get("mutation_cases"), len(cases), "summary mutation case count")
        rejected_count = 0
        for index, (case, expected_case) in enumerate(zip(cases, expected, strict=True)):
            expect_key_set(
                case,
                {
                    "mutation",
                    "surface",
                    "baseline_accepted",
                    "mutated_accepted",
                    "rejected",
                    "rejection_layer",
                    "error",
                },
                f"mutation case {index}",
            )
            expect_equal(case.get("mutation"), expected_case["mutation"], f"mutation case {index} name")
            expect_equal(case.get("surface"), expected_case["surface"], f"mutation case {index} surface")
            expect_equal(
                case.get("rejection_layer"),
                expected_case["rejection_layer"],
                f"mutation case {index} rejection_layer",
            )
            expect_equal(case.get("baseline_accepted"), True, f"mutation case {index} baseline")
            if case["rejected"]:
                rejected_count += 1
                if not case.get("error"):
                    raise D128RangePolicyError(f"mutation case {index} error must be non-empty")
            expect_equal(case.get("mutated_accepted"), not case.get("rejected"), f"mutation case {index} relation")
        expect_equal(summary.get("mutations_rejected"), rejected_count, "summary mutations rejected")
        expect_equal(rejected_count, len(cases), "all mutation cases rejected")
        expect_equal(payload.get("all_mutations_rejected"), True, "all mutations rejected")


def to_tsv(payload: dict[str, Any]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in payload["tensor_policies"]:
        writer.writerow({column: row[column] for column in TSV_COLUMNS})
    return out.getvalue()


def write_outputs(payload: dict[str, Any], json_out: pathlib.Path, tsv_out: pathlib.Path) -> None:
    validate_payload(payload)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    tsv_out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=json_out.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        tmp_json = pathlib.Path(handle.name)
    tmp_json.replace(json_out)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=tsv_out.parent, delete=False) as handle:
        handle.write(to_tsv(payload))
        tmp_tsv = pathlib.Path(handle.name)
    tmp_tsv.replace(tsv_out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
