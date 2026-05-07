#!/usr/bin/env python3
"""Checked fused native Stwo four-head bounded Softmax-table gate for issue #491.

This gate records the breakthrough route: one native Stwo proof object checks the
bounded attention arithmetic and the LogUp table-membership relation. It is not
an exact real-valued Softmax claim and not full inference.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import tempfile
from types import ModuleType
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json"
SOURCE_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json"
SIDECAR_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json"
FUSED_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json"
SOURCE_INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.tsv"

MAX_SOURCE_INPUT_JSON_BYTES = 1_048_576
MAX_SOURCE_ENVELOPE_JSON_BYTES = 1_048_576
MAX_SIDECAR_ENVELOPE_JSON_BYTES = 1_048_576
MAX_FUSED_ENVELOPE_JSON_BYTES = 1_048_576
FUSED_VERIFY_TIMEOUT_SECONDS = 300

SCHEMA = "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-v1"
ISSUE = 491
SOURCE_ISSUE = 482
SIDECAR_ISSUE = 482
DECISION = "GO_NATIVE_STWO_FUSED_ATTENTION_ARITHMETIC_AND_SOFTMAX_TABLE_LOGUP_MEMBERSHIP"
ROUTE_ID = "local_stwo_attention_kv_four_head_fused_bounded_softmax_table_logup_proof"
CLAIM_BOUNDARY = (
    "ONE_NATIVE_STWO_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_ATTENTION_PROOF_WITH_LOGUP_TABLE_MEMBERSHIP_"
    "NOT_EXACT_SOFTMAX_NOT_FULL_INFERENCE_NOT_LONG_CONTEXT_NOT_RECURSION_OR_PCD"
)
FUSION_STATUS = "GO_ONE_NATIVE_STWO_PROOF_OBJECT_WITH_ATTENTION_ARITHMETIC_AND_LOGUP_MEMBERSHIP"
NON_FUSED_STATUS = "NO_SOURCE_PLUS_SIDECAR_SPLIT_BRAIN_SURFACE_IN_THIS_ROUTE"
TIMING_POLICY = "proof_existence_and_byte_accounting_only_not_public_benchmark"

SOURCE_PROOF_SIZE_BYTES = 52_746
SOURCE_ENVELOPE_SIZE_BYTES = 788_949
SIDECAR_PROOF_SIZE_BYTES = 21_783
SIDECAR_ENVELOPE_SIZE_BYTES = 543_187
SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES = SOURCE_PROOF_SIZE_BYTES + SIDECAR_PROOF_SIZE_BYTES
FUSED_PROOF_SIZE_BYTES = 53_468
FUSED_ENVELOPE_SIZE_BYTES = 797_717
FUSED_OVER_SOURCE_PROOF_BYTES = FUSED_PROOF_SIZE_BYTES - SOURCE_PROOF_SIZE_BYTES
FUSED_SAVES_VS_SOURCE_PLUS_SIDECAR_BYTES = SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES - FUSED_PROOF_SIZE_BYTES
FUSED_TO_SOURCE_PLUS_SIDECAR_RATIO = FUSED_PROOF_SIZE_BYTES / SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES

SOURCE_STATEMENT_COMMITMENT = "blake2b-256:c0fe8e31be336f35dd021bc16d35674750456e17b8cd52dca5718a820aef9db6"
SOURCE_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:4bb332e513d1ef635ce76d7fd705e8187800081417fa138f449c47ab8be9069f"
SOURCE_SCORE_ROW_COMMITMENT = "blake2b-256:ec1fa95aab49398c1fb3253cf87308e8014c09ad7e3fca6e23b496c72731fa7e"
SOURCE_FINAL_KV_CACHE_COMMITMENT = "blake2b-256:b0690b8a16ecc946e1ee5212f43bbef21648df1fe2471d08aaa1df5a87440600"
SOURCE_OUTPUTS_COMMITMENT = "blake2b-256:0a80c5aea1f2611adca6e9d01a3316ae9f5960136021b705125a66ede06a6f09"
SOURCE_WEIGHT_TABLE_COMMITMENT = "blake2b-256:3c3e5002672d7efa6b7a1293d17388c98344f61aceae7914f00a391ce355de62"
SOURCE_HEAD_COUNT = 4
SOURCE_WEIGHT_POLICY = "exp2_half_gap_table_clipped_8_floor_division"
SOURCE_SCORE_GAP_CLIP = 8
SOURCE_SCORE_ROWS = 208
SOURCE_TRACE_ROWS = 256
SOURCE_TABLE_ROWS = 9
SOURCE_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-four-head-bounded-softmax-table-v1"
SOURCE_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-statement-v1"
SOURCE_SEMANTIC_SCOPE = "four_head_d8_bounded_table_softmax_approx_attention_kv_causal_mask_rows_bound_to_statement_receipt"
SOURCE_DECISION = "GO_STWO_NATIVE_ATTENTION_KV_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
SOURCE_INPUT_DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
SOURCE_TARGET_ID = "attention-kv-d8-causal-mask-four-head-bounded-softmax-table-v1"
SOURCE_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-four-head-bounded-softmax-table:v1"
LOOKUP_RELATION = "AttentionKvFourHeadFusedSoftmaxTableRelation"
SIDECAR_LOOKUP_RELATION = "AttentionKvFourHeadSoftmaxTableLookupRelation"
LOOKUP_RELATION_WIDTH = 2
SOURCE_PROOF_COMMITMENTS = 3
SIDECAR_PROOF_COMMITMENTS = 4

FUSED_BACKEND_VERSION = "stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-v1"
FUSED_PROOF_SCHEMA_VERSION = "stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-proof-v1"
FUSED_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-logup-statement-v1"
FUSED_SEMANTIC_SCOPE = "four_head_d8_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof"
FUSED_TARGET_ID = "attention-kv-four-head-d8-causal-mask-fused-bounded-softmax-table-logup-v1"
FUSED_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-four-head-fused-bounded-softmax-table-logup:v1"
FUSED_PROOF_COMMITMENTS = 4
FUSED_TRACE_COMMITMENTS = 3

TABLE_MULTIPLICITIES = (
    {"gap": 0, "weight": 256, "multiplicity": 40},
    {"gap": 1, "weight": 181, "multiplicity": 2},
    {"gap": 2, "weight": 128, "multiplicity": 4},
    {"gap": 3, "weight": 91, "multiplicity": 6},
    {"gap": 4, "weight": 64, "multiplicity": 2},
    {"gap": 5, "weight": 45, "multiplicity": 3},
    {"gap": 6, "weight": 32, "multiplicity": 2},
    {"gap": 7, "weight": 23, "multiplicity": 1},
    {"gap": 8, "weight": 16, "multiplicity": 148},
)
NON_CLAIMS = (
    "not exact Softmax attention",
    "not exp/div Softmax semantics",
    "not full autoregressive inference",
    "not a long-context benchmark",
    "not recursive verification or PCD",
    "not private witness privacy",
    "not on-chain verification evidence",
    "clipped-gap derivation and source-row semantics are verifier-recomputed from public rows before proof verification",
)

EXPECTED_MUTATION_NAMES = (
    "fused_decision_relabeling",
    "fusion_status_relabeling",
    "non_fused_status_relabeling",
    "claim_boundary_exact_softmax_overclaim",
    "semantic_scope_exact_softmax_overclaim",
    "source_statement_commitment_relabeling",
    "source_weight_table_commitment_relabeling",
    "source_score_row_commitment_relabeling",
    "source_final_kv_commitment_relabeling",
    "source_outputs_commitment_relabeling",
    "source_head_count_metric_smuggling",
    "lookup_relation_relabeling",
    "lookup_claim_count_metric_smuggling",
    "source_plus_sidecar_metric_smuggling",
    "fused_proof_size_metric_smuggling",
    "source_input_statement_commitment_relabeling",
    "source_input_head_index_relabeling",
    "table_multiplicity_drift",
    "non_claim_removed",
    "source_input_split_brain_weight",
    "source_input_output_remainder_drift",
    "proof_byte_tamper",
    "target_id_relabeling",
    "verifier_domain_relabeling",
    "statement_version_relabeling",
    "proof_backend_version_relabeling",
    "proof_schema_version_relabeling",
    "sidecar_proof_injection",
    "source_proof_injection",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 test --locked attention_kv_four_head_fused_softmax_table --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_four_head_fused_softmax_table_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_four_head_fused_softmax_table_native_gate",
    "just lib",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "decision",
    "route_id",
    "lookup_claims",
    "table_rows",
    "source_proof_size_bytes",
    "sidecar_proof_size_bytes",
    "source_plus_sidecar_raw_proof_bytes",
    "fused_proof_size_bytes",
    "fused_over_source_proof_bytes",
    "fused_saves_vs_source_plus_sidecar_bytes",
    "fused_to_source_plus_sidecar_ratio",
    "mutations_checked",
    "mutations_rejected",
    "source_head_count",
    "source_statement_commitment",
    "source_final_kv_cache_commitment",
    "source_outputs_commitment",
    "source_weight_table_commitment",
)

_FUSED_VERIFY_CACHE: dict[tuple[str, int], dict[str, Any]] = {}
_NATIVE_VERIFY_CACHE: dict[tuple[str, int, str], dict[str, Any]] = {}


class AttentionKvFourHeadFusedSoftmaxTableGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise ImportError(f"failed to import {module_name} from {path}: {err}") from err
    return module


SOURCE_INPUT_MODULE = load_script_module(
    SOURCE_INPUT_SCRIPT, "zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input"
)


def read_bounded_bytes(path: pathlib.Path, max_bytes: int, label: str) -> bytes:
    if not path.is_file():
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} size drift: got {size}, max {max_bytes}")
    try:
        raw = path.read_bytes()
    except OSError as err:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"failed to read {label}: {err}") from err
    if len(raw) != size:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} read size drift: stat={size}, read={len(raw)}")
    return raw


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    raw = read_bounded_bytes(path, max_bytes, label)
    return parse_bounded_json_bytes(raw, label)


def parse_bounded_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"failed to decode {label}: {err}") from err


def expect_artifact_size(raw: bytes, expected_size: int, label: str) -> None:
    if len(raw) != expected_size:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            f"{label} size drift: got {len(raw)}, expected {expected_size}"
        )


def read_sized_envelope(
    path: pathlib.Path,
    max_bytes: int,
    expected_size: int,
    label: str,
) -> tuple[Any, bytes]:
    raw = read_bounded_bytes(path, max_bytes, label)
    expect_artifact_size(raw, expected_size, label)
    return parse_bounded_json_bytes(raw, label), raw


def parse_stark_proof(
    proof_bytes: list[Any],
    expected_bytes: int,
    label: str,
    *,
    expected_commitments: int,
) -> dict[str, Any]:
    if not isinstance(proof_bytes, list):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} proof must be a byte list")
    if len(proof_bytes) != expected_bytes:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} proof byte length drift")
    if any(not isinstance(byte, int) or isinstance(byte, bool) or byte < 0 or byte > 255 for byte in proof_bytes):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} proof bytes must be uint8 values")
    try:
        payload = json.loads(bytes(proof_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"failed to decode {label} proof payload: {err}") from err
    if set(payload) != {"stark_proof"}:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} proof payload schema drift")
    stark_proof = payload["stark_proof"]
    if not isinstance(stark_proof, dict):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} stark_proof must be an object")
    commitments = stark_proof.get("commitments")
    if not isinstance(commitments, list) or len(commitments) != expected_commitments:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} proof commitment count drift")
    return stark_proof


def same_digit_int_mutation(value: int, label: str) -> int:
    for candidate in (value + 1, value - 1):
        if 0 <= candidate <= 255 and len(str(candidate)) == len(str(value)):
            return candidate
    raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"no same-width byte mutation for {label}")


def mutate_same_size_stark_proof_commitment(envelope: dict[str, Any]) -> None:
    payload = json.loads(bytes(envelope["proof"]).decode("utf-8"))
    commitments = payload["stark_proof"]["commitments"]
    commitments[0][0] = same_digit_int_mutation(
        commitments[0][0], "first proof commitment byte"
    )
    proof_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(proof_bytes) != len(envelope["proof"]):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("same-size proof mutation changed byte length")
    envelope["proof"] = list(proof_bytes)


def assert_fields(mapping: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, expected_value in expected.items():
        if mapping.get(key) != expected_value:
            raise AttentionKvFourHeadFusedSoftmaxTableGateError(
                f"{label} drift for {key}: got {mapping.get(key)!r}"
            )


def assert_exact_keys(mapping: dict[str, Any], expected_keys: set[str], label: str) -> None:
    if not isinstance(mapping, dict):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} must be an object")
    extra_keys = set(mapping) - expected_keys
    missing_keys = expected_keys - set(mapping)
    if extra_keys or missing_keys:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            f"{label} field set drift: extra={sorted(extra_keys)}, missing={sorted(missing_keys)}"
        )


def assert_native_verifier_summary(
    mapping: dict[str, Any],
    expected: dict[str, Any],
    label: str,
    *,
    dynamic_path_key: str,
) -> None:
    assert_exact_keys(mapping, set(expected) | {"schema", dynamic_path_key}, label)
    schema = mapping.get("schema")
    if not isinstance(schema, str) or not schema.endswith("-cli-summary-v1"):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"{label} schema drift: got {schema!r}")
    dynamic_path = mapping.get(dynamic_path_key)
    if not isinstance(dynamic_path, str) or not dynamic_path.endswith(".json"):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            f"{label} {dynamic_path_key} drift: got {dynamic_path!r}"
        )
    assert_fields(mapping, expected, label)


def verify_envelope_bytes_with_native_cli(
    envelope_bytes: bytes,
    label: str,
    *,
    max_bytes: int,
    binary: str,
    expected_summary: dict[str, Any],
    dynamic_path_key: str = "envelope_path",
) -> None:
    if len(envelope_bytes) <= 0 or len(envelope_bytes) > max_bytes:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            f"{label} size drift: got {len(envelope_bytes)}, max {max_bytes}"
        )
    digest = hashlib.blake2b(envelope_bytes, digest_size=32).hexdigest()
    cache_key = (digest, len(envelope_bytes), binary)
    cached_summary = _NATIVE_VERIFY_CACHE.get(cache_key)
    if cached_summary is not None:
        assert_native_verifier_summary(
            cached_summary,
            expected_summary,
            f"native {label} verifier summary",
            dynamic_path_key=dynamic_path_key,
        )
        return
    with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as tmp:
        tmp.write(envelope_bytes)
        tmp_path = pathlib.Path(tmp.name)
    command = [
        "cargo",
        "+nightly-2025-07-14",
        "run",
        "--locked",
        "--features",
        "stwo-backend",
        "--bin",
        binary,
        "--",
        "verify",
        str(tmp_path),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=FUSED_VERIFY_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            f"native {label} verifier failed to run: {err}"
        ) from err
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        suffix = detail[-1] if detail else f"exit code {completed.returncode}"
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            f"native {label} verifier rejected artifact: {suffix}"
        )
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            f"native {label} verifier emitted malformed JSON: {err}"
        ) from err
    assert_native_verifier_summary(
        summary,
        expected_summary,
        f"native {label} verifier summary",
        dynamic_path_key=dynamic_path_key,
    )
    _NATIVE_VERIFY_CACHE[cache_key] = summary


def verify_fused_envelope_bytes_with_native_cli(envelope_bytes: bytes, label: str) -> None:
    if len(envelope_bytes) <= 0 or len(envelope_bytes) > MAX_FUSED_ENVELOPE_JSON_BYTES:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            f"{label} size drift: got {len(envelope_bytes)}, max {MAX_FUSED_ENVELOPE_JSON_BYTES}"
        )
    digest = hashlib.blake2b(envelope_bytes, digest_size=32).hexdigest()
    cache_key = (digest, len(envelope_bytes))
    cached_summary = _FUSED_VERIFY_CACHE.get(cache_key)
    expected = expected_fused_verifier_summary(len(envelope_bytes))
    if cached_summary is not None:
        assert_native_verifier_summary(
            cached_summary,
            expected,
            f"native fused {label} verifier summary",
            dynamic_path_key="fused_envelope_path",
        )
        return
    with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as tmp:
        tmp.write(envelope_bytes)
        tmp_path = pathlib.Path(tmp.name)
    command = [
        "cargo",
        "+nightly-2025-07-14",
        "run",
        "--locked",
        "--features",
        "stwo-backend",
        "--bin",
        "zkai_attention_kv_native_four_head_fused_softmax_table_proof",
        "--",
        "verify",
        str(tmp_path),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=FUSED_VERIFY_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"native fused verifier failed to run for {label}: {err}") from err
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        suffix = detail[-1] if detail else f"exit code {completed.returncode}"
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"native fused verifier rejected {label}: {suffix}")
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"native fused verifier emitted malformed JSON: {err}") from err
    assert_native_verifier_summary(
        summary,
        expected,
        f"native fused {label} verifier summary",
        dynamic_path_key="fused_envelope_path",
    )
    _FUSED_VERIFY_CACHE[cache_key] = summary


def expected_fused_verifier_summary(envelope_size_bytes: int) -> dict[str, Any]:
    return {
        "mode": "verify",
        "verified": True,
        "proof_size_bytes": FUSED_PROOF_SIZE_BYTES,
        "envelope_size_bytes": envelope_size_bytes,
        "source_plus_sidecar_raw_proof_bytes": SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
    }


def expected_summary(source_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "sidecar_issue": SIDECAR_ISSUE,
        "fusion_status": FUSION_STATUS,
        "non_fused_status": NON_FUSED_STATUS,
        "source_statement_commitment": source_input["statement_commitment"],
        "source_public_instance_commitment": source_input["public_instance_commitment"],
        "source_score_row_commitment": source_input["score_row_commitment"],
        "source_final_kv_cache_commitment": source_input["final_kv_cache_commitment"],
        "source_outputs_commitment": source_input["outputs_commitment"],
        "source_weight_table_commitment": source_input["weight_table_commitment"],
        "source_head_count": source_input["head_count"],
        "score_rows": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
        "weight_policy": SOURCE_WEIGHT_POLICY,
        "lookup_relation": LOOKUP_RELATION,
        "lookup_relation_width": LOOKUP_RELATION_WIDTH,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "source_plus_sidecar_raw_proof_bytes": SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        "table_multiplicities": list(TABLE_MULTIPLICITIES),
        "timing_policy": TIMING_POLICY,
        "non_claims": list(NON_CLAIMS),
    }


def validate_source_input_contract(source_input: dict[str, Any]) -> None:
    assert_fields(
        source_input,
        {
            "decision": SOURCE_INPUT_DECISION,
            "issue": SOURCE_ISSUE,
            "target_id": SOURCE_TARGET_ID,
            "required_backend_version": SOURCE_BACKEND_VERSION,
            "proof_version": "stwo-attention-kv-d8-causal-mask-four-head-bounded-softmax-table-air-proof-v1",
            "statement_version": SOURCE_STATEMENT_VERSION,
            "semantic_scope": SOURCE_SEMANTIC_SCOPE,
            "verifier_domain": SOURCE_VERIFIER_DOMAIN,
            "semantics": "bounded_table_softmax_approx_attention",
            "weight_policy": SOURCE_WEIGHT_POLICY,
            "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
            "head_count": SOURCE_HEAD_COUNT,
            "score_row_count": SOURCE_SCORE_ROWS,
            "trace_row_count": SOURCE_TRACE_ROWS,
            "statement_commitment": SOURCE_STATEMENT_COMMITMENT,
            "public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
            "score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
            "final_kv_cache_commitment": SOURCE_FINAL_KV_CACHE_COMMITMENT,
            "outputs_commitment": SOURCE_OUTPUTS_COMMITMENT,
            "weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        },
        "source input",
    )
    if len(source_input.get("score_rows", [])) != SOURCE_SCORE_ROWS:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("source score row count drift")
    if len(source_input.get("weight_table", [])) != SOURCE_TABLE_ROWS:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("source weight table row count drift")


def validate_source_artifacts(
    source_input: dict[str, Any],
    source_envelope: dict[str, Any],
    sidecar_envelope: dict[str, Any],
    *,
    source_envelope_bytes: bytes,
    sidecar_envelope_bytes: bytes,
) -> None:
    if (
        parse_bounded_json_bytes(source_envelope_bytes, "source envelope bytes")
        != source_envelope
    ):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            "source envelope bytes/dict split-brain drift"
        )
    if (
        parse_bounded_json_bytes(sidecar_envelope_bytes, "sidecar envelope bytes")
        != sidecar_envelope
    ):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(
            "sidecar envelope bytes/dict split-brain drift"
        )
    try:
        SOURCE_INPUT_MODULE.validate_payload(source_input)
    except Exception as err:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"source input validation drift: {err}") from err
    validate_source_input_contract(source_input)
    assert_exact_keys(
        source_envelope,
        {
            "proof_backend",
            "proof_backend_version",
            "statement_version",
            "semantic_scope",
            "decision",
            "input",
            "proof",
        },
        "source envelope",
    )
    if source_envelope.get("input") != source_input:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("source envelope/input split-brain drift")
    assert_fields(
        source_envelope,
        {
            "proof_backend": "stwo",
            "proof_backend_version": SOURCE_BACKEND_VERSION,
            "statement_version": SOURCE_STATEMENT_VERSION,
            "semantic_scope": SOURCE_SEMANTIC_SCOPE,
            "decision": SOURCE_DECISION,
        },
        "source envelope",
    )
    parse_stark_proof(
        source_envelope.get("proof"),
        SOURCE_PROOF_SIZE_BYTES,
        "source",
        expected_commitments=SOURCE_PROOF_COMMITMENTS,
    )
    verify_envelope_bytes_with_native_cli(
        source_envelope_bytes,
        "source",
        max_bytes=MAX_SOURCE_ENVELOPE_JSON_BYTES,
        binary="zkai_attention_kv_native_four_head_bounded_softmax_table_proof",
        expected_summary={
            "mode": "verify",
            "verified": True,
            "proof_size_bytes": SOURCE_PROOF_SIZE_BYTES,
            "envelope_size_bytes": len(source_envelope_bytes),
            "statement_commitment": SOURCE_STATEMENT_COMMITMENT,
            "score_row_count": SOURCE_SCORE_ROWS,
            "trace_row_count": SOURCE_TRACE_ROWS,
        },
    )
    assert_exact_keys(
        sidecar_envelope,
        {
            "proof_backend",
            "proof_backend_version",
            "statement_version",
            "semantic_scope",
            "decision",
            "verifier_domain",
            "source_input",
            "lookup_summary",
            "proof",
        },
        "sidecar envelope",
    )
    assert_fields(
        sidecar_envelope,
        {
            "proof_backend": "stwo",
            "proof_backend_version": "stwo-attention-kv-four-head-softmax-table-logup-sidecar-proof-v1",
            "statement_version": "zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-statement-v1",
            "semantic_scope": "four_head_bounded_softmax_table_membership_constrained_by_native_stwo_logup_sidecar",
            "decision": "GO_NATIVE_STWO_AIR_CONSTRAINED_SOFTMAX_TABLE_LOOKUP_RELATION_SIDECAR",
            "verifier_domain": "ptvm:zkai:attention-kv-stwo-native-four-head-softmax-table-logup-sidecar:v1",
        },
        "sidecar envelope",
    )
    if sidecar_envelope.get("source_input") != source_input:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("sidecar source input split-brain drift")
    parse_stark_proof(
        sidecar_envelope.get("proof"),
        SIDECAR_PROOF_SIZE_BYTES,
        "sidecar",
        expected_commitments=SIDECAR_PROOF_COMMITMENTS,
    )
    lookup_summary = sidecar_envelope.get("lookup_summary")
    if not isinstance(lookup_summary, dict):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("sidecar lookup summary missing")
    expected_sidecar = {
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "source_public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "source_score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "source_final_kv_cache_commitment": SOURCE_FINAL_KV_CACHE_COMMITMENT,
        "source_outputs_commitment": SOURCE_OUTPUTS_COMMITMENT,
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "source_head_count": SOURCE_HEAD_COUNT,
        "score_rows": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
        "weight_policy": SOURCE_WEIGHT_POLICY,
        "lookup_relation": SIDECAR_LOOKUP_RELATION,
        "lookup_relation_width": LOOKUP_RELATION_WIDTH,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "table_multiplicities": list(TABLE_MULTIPLICITIES),
    }
    assert_exact_keys(lookup_summary, set(expected_sidecar), "sidecar lookup summary")
    for key, expected_value in expected_sidecar.items():
        if lookup_summary.get(key) != expected_value:
            raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"sidecar summary drift for {key}")
    verify_envelope_bytes_with_native_cli(
        sidecar_envelope_bytes,
        "sidecar",
        max_bytes=MAX_SIDECAR_ENVELOPE_JSON_BYTES,
        binary="zkai_attention_kv_native_four_head_softmax_table_lookup_proof",
        expected_summary={
            "mode": "verify",
            "verified": True,
            "proof_size_bytes": SIDECAR_PROOF_SIZE_BYTES,
            "envelope_size_bytes": len(sidecar_envelope_bytes),
            "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
            "lookup_claims": SOURCE_SCORE_ROWS,
            "table_rows": SOURCE_TABLE_ROWS,
        },
        dynamic_path_key="lookup_envelope_path",
    )


def validate_fused_envelope(envelope: dict[str, Any], source_input: dict[str, Any], *, run_native: bool) -> None:
    allowed_keys = {
        "proof_backend",
        "proof_backend_version",
        "proof_schema_version",
        "statement_version",
        "semantic_scope",
        "decision",
        "target_id",
        "verifier_domain",
        "fused_summary",
        "source_input",
        "proof",
    }
    extra_keys = set(envelope) - allowed_keys
    if extra_keys:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"unknown fused envelope field(s): {sorted(extra_keys)}")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused proof backend drift")
    if envelope.get("proof_backend_version") != FUSED_BACKEND_VERSION:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused proof backend version drift")
    if envelope.get("proof_schema_version") != FUSED_PROOF_SCHEMA_VERSION:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused proof schema version drift")
    if envelope.get("statement_version") != FUSED_STATEMENT_VERSION:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused statement version drift")
    if envelope.get("semantic_scope") != FUSED_SEMANTIC_SCOPE:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused semantic scope drift")
    if envelope.get("decision") != DECISION:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused decision drift")
    if envelope.get("target_id") != FUSED_TARGET_ID:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused target id drift")
    if envelope.get("verifier_domain") != FUSED_VERIFIER_DOMAIN:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused verifier domain drift")
    if envelope.get("source_input") != source_input:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused source input split-brain drift")
    if envelope.get("fused_summary") != expected_summary(source_input):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("fused summary drift")
    parse_stark_proof(
        envelope.get("proof"),
        FUSED_PROOF_SIZE_BYTES,
        "fused",
        expected_commitments=FUSED_PROOF_COMMITMENTS,
    )
    if run_native:
        verify_fused_envelope_bytes_with_native_cli(
            json.dumps(envelope, indent=2, ensure_ascii=False).encode("utf-8"),
            "in-memory fused envelope",
        )


def mutation_cases(envelope: dict[str, Any]) -> list[tuple[str, dict[str, Any], bool]]:
    cases: list[tuple[str, dict[str, Any], bool]] = []

    def add(name: str, mutator, run_native: bool = False) -> None:
        value = copy.deepcopy(envelope)
        mutator(value)
        cases.append((name, value, run_native))

    add("fused_decision_relabeling", lambda v: v.__setitem__("decision", "GO_EXACT_SOFTMAX_FUSED_PROOF"))
    add("fusion_status_relabeling", lambda v: v["fused_summary"].__setitem__("fusion_status", "GO_SIDE_CAR_ONLY"))
    add(
        "non_fused_status_relabeling",
        lambda v: v["fused_summary"].__setitem__(
            "non_fused_status", "SIDE_CAR_STILL_REQUIRED"
        ),
    )
    add(
        "claim_boundary_exact_softmax_overclaim",
        lambda v: v["fused_summary"]["non_claims"].remove("not exact Softmax attention"),
    )
    add(
        "semantic_scope_exact_softmax_overclaim",
        lambda v: v.__setitem__("semantic_scope", "exact_real_valued_softmax_attention"),
    )
    add(
        "source_statement_commitment_relabeling",
        lambda v: v["fused_summary"].__setitem__(
            "source_statement_commitment", "blake2b-256:" + "11" * 32
        ),
    )
    add(
        "source_weight_table_commitment_relabeling",
        lambda v: v["fused_summary"].__setitem__(
            "source_weight_table_commitment", "blake2b-256:" + "22" * 32
        ),
    )
    add(
        "source_score_row_commitment_relabeling",
        lambda v: v["fused_summary"].__setitem__(
            "source_score_row_commitment", "blake2b-256:" + "33" * 32
        ),
    )
    add(
        "source_final_kv_commitment_relabeling",
        lambda v: v["fused_summary"].__setitem__(
            "source_final_kv_cache_commitment", "blake2b-256:" + "34" * 32
        ),
    )
    add(
        "source_outputs_commitment_relabeling",
        lambda v: v["fused_summary"].__setitem__(
            "source_outputs_commitment", "blake2b-256:" + "35" * 32
        ),
    )
    add(
        "source_head_count_metric_smuggling",
        lambda v: v["fused_summary"].__setitem__("source_head_count", SOURCE_HEAD_COUNT + 1),
    )
    add("lookup_relation_relabeling", lambda v: v["fused_summary"].__setitem__("lookup_relation", "OtherRelation"))
    add(
        "lookup_claim_count_metric_smuggling",
        lambda v: v["fused_summary"].__setitem__("lookup_claims", SOURCE_SCORE_ROWS + 1),
    )
    add(
        "source_plus_sidecar_metric_smuggling",
        lambda v: v["fused_summary"].__setitem__(
            "source_plus_sidecar_raw_proof_bytes", SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES - 1
        ),
    )
    add("fused_proof_size_metric_smuggling", lambda v: v["proof"].append(0))
    add(
        "source_input_statement_commitment_relabeling",
        lambda v: v["source_input"].__setitem__(
            "statement_commitment", "blake2b-256:" + "44" * 32
        ),
    )
    add(
        "source_input_head_index_relabeling",
        lambda v: v["source_input"]["score_rows"][0].__setitem__("head_index", SOURCE_HEAD_COUNT + 1),
    )
    add(
        "table_multiplicity_drift",
        lambda v: v["fused_summary"]["table_multiplicities"][0].__setitem__(
            "multiplicity", TABLE_MULTIPLICITIES[0]["multiplicity"] + 1
        ),
    )
    add("non_claim_removed", lambda v: v["fused_summary"]["non_claims"].pop())
    add(
        "source_input_split_brain_weight",
        lambda v: v["source_input"]["score_rows"][0].__setitem__(
            "attention_weight", 255
        ),
    )
    add(
        "source_input_output_remainder_drift",
        lambda v: v["source_input"]["score_rows"][0]["output_remainder"].__setitem__(
            0, 999
        ),
    )
    add("proof_byte_tamper", mutate_same_size_stark_proof_commitment, run_native=True)
    add("target_id_relabeling", lambda v: v.__setitem__("target_id", "different-target"))
    add("verifier_domain_relabeling", lambda v: v.__setitem__("verifier_domain", "different-domain"))
    add("statement_version_relabeling", lambda v: v.__setitem__("statement_version", "different-statement"))
    add(
        "proof_backend_version_relabeling",
        lambda v: v.__setitem__("proof_backend_version", "different-stwo-backend"),
    )
    add(
        "proof_schema_version_relabeling",
        lambda v: v.__setitem__("proof_schema_version", "different-fused-proof-schema"),
    )
    add("sidecar_proof_injection", lambda v: v.__setitem__("sidecar_proof", []))
    add("source_proof_injection", lambda v: v.__setitem__("source_proof", []))
    add("unknown_field_injection", lambda v: v.__setitem__("unexpected", "claim smuggling"))
    return cases


def run_gate() -> dict[str, Any]:
    source_input = read_bounded_json(SOURCE_INPUT_JSON, MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    source_envelope, source_raw = read_sized_envelope(
        SOURCE_ENVELOPE_JSON,
        MAX_SOURCE_ENVELOPE_JSON_BYTES,
        SOURCE_ENVELOPE_SIZE_BYTES,
        "source envelope",
    )
    sidecar_envelope, sidecar_raw = read_sized_envelope(
        SIDECAR_ENVELOPE_JSON,
        MAX_SIDECAR_ENVELOPE_JSON_BYTES,
        SIDECAR_ENVELOPE_SIZE_BYTES,
        "sidecar envelope",
    )
    fused_envelope, fused_raw = read_sized_envelope(
        FUSED_ENVELOPE_JSON,
        MAX_FUSED_ENVELOPE_JSON_BYTES,
        FUSED_ENVELOPE_SIZE_BYTES,
        "fused envelope",
    )
    validate_source_artifacts(
        source_input,
        source_envelope,
        sidecar_envelope,
        source_envelope_bytes=source_raw,
        sidecar_envelope_bytes=sidecar_raw,
    )
    validate_fused_envelope(fused_envelope, source_input, run_native=False)
    verify_fused_envelope_bytes_with_native_cli(fused_raw, str(FUSED_ENVELOPE_JSON))

    mutation_results = evaluate_mutation_results(fused_envelope, source_input)
    mutation_names = tuple(result["name"] for result in mutation_results)
    if mutation_names != EXPECTED_MUTATION_NAMES:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("mutation case order/name drift")
    rejected = sum(1 for result in mutation_results if result["rejected"])
    if rejected != EXPECTED_MUTATION_COUNT:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"mutation rejection drift: got {rejected}")

    result = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "sidecar_issue": SIDECAR_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "fusion_status": FUSION_STATUS,
        "non_fused_status": NON_FUSED_STATUS,
        "timing_policy": TIMING_POLICY,
        "source_proof_size_bytes": SOURCE_PROOF_SIZE_BYTES,
        "source_envelope_size_bytes": SOURCE_ENVELOPE_SIZE_BYTES,
        "sidecar_proof_size_bytes": SIDECAR_PROOF_SIZE_BYTES,
        "sidecar_envelope_size_bytes": SIDECAR_ENVELOPE_SIZE_BYTES,
        "source_plus_sidecar_raw_proof_bytes": SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        "fused_proof_size_bytes": FUSED_PROOF_SIZE_BYTES,
        "fused_envelope_size_bytes": FUSED_ENVELOPE_SIZE_BYTES,
        "fused_over_source_proof_bytes": FUSED_OVER_SOURCE_PROOF_BYTES,
        "fused_saves_vs_source_plus_sidecar_bytes": FUSED_SAVES_VS_SOURCE_PLUS_SIDECAR_BYTES,
        "fused_to_source_plus_sidecar_ratio": FUSED_TO_SOURCE_PLUS_SIDECAR_RATIO,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "lookup_relation": LOOKUP_RELATION,
        "lookup_relation_width": LOOKUP_RELATION_WIDTH,
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "source_public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "source_score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "source_final_kv_cache_commitment": SOURCE_FINAL_KV_CACHE_COMMITMENT,
        "source_outputs_commitment": SOURCE_OUTPUTS_COMMITMENT,
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "source_head_count": SOURCE_HEAD_COUNT,
        "table_multiplicities": list(TABLE_MULTIPLICITIES),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_results": mutation_results,
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": rejected,
    }
    validate_result(result)
    return result


def evaluate_mutation_results(fused_envelope: dict[str, Any], source_input: dict[str, Any]) -> list[dict[str, Any]]:
    mutation_results = []
    for name, mutated, run_native in mutation_cases(fused_envelope):
        try:
            validate_fused_envelope(mutated, source_input, run_native=run_native)
        except AttentionKvFourHeadFusedSoftmaxTableGateError as err:
            mutation_results.append({"name": name, "rejected": True, "error": str(err)})
        else:
            mutation_results.append({"name": name, "rejected": False, "error": "mutation accepted"})
    return mutation_results


def validate_result(result: dict[str, Any]) -> None:
    if not isinstance(result, dict):
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("result must be an object")
    expected_exact: dict[str, Any] = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "sidecar_issue": SIDECAR_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "fusion_status": FUSION_STATUS,
        "non_fused_status": NON_FUSED_STATUS,
        "timing_policy": TIMING_POLICY,
        "source_proof_size_bytes": SOURCE_PROOF_SIZE_BYTES,
        "source_envelope_size_bytes": SOURCE_ENVELOPE_SIZE_BYTES,
        "sidecar_proof_size_bytes": SIDECAR_PROOF_SIZE_BYTES,
        "sidecar_envelope_size_bytes": SIDECAR_ENVELOPE_SIZE_BYTES,
        "source_plus_sidecar_raw_proof_bytes": SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        "fused_proof_size_bytes": FUSED_PROOF_SIZE_BYTES,
        "fused_envelope_size_bytes": FUSED_ENVELOPE_SIZE_BYTES,
        "fused_over_source_proof_bytes": FUSED_OVER_SOURCE_PROOF_BYTES,
        "fused_saves_vs_source_plus_sidecar_bytes": FUSED_SAVES_VS_SOURCE_PLUS_SIDECAR_BYTES,
        "fused_to_source_plus_sidecar_ratio": FUSED_TO_SOURCE_PLUS_SIDECAR_RATIO,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "lookup_relation": LOOKUP_RELATION,
        "lookup_relation_width": LOOKUP_RELATION_WIDTH,
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "source_public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "source_score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "source_final_kv_cache_commitment": SOURCE_FINAL_KV_CACHE_COMMITMENT,
        "source_outputs_commitment": SOURCE_OUTPUTS_COMMITMENT,
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "source_head_count": SOURCE_HEAD_COUNT,
        "table_multiplicities": list(TABLE_MULTIPLICITIES),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": EXPECTED_MUTATION_COUNT,
    }
    required = set(expected_exact) | {"mutation_results"}
    missing = required - set(result)
    if missing:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"missing result keys: {sorted(missing)}")
    extra = set(result) - required
    if extra:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"unknown result keys: {sorted(extra)}")
    for key, expected_value in expected_exact.items():
        if result.get(key) != expected_value:
            raise AttentionKvFourHeadFusedSoftmaxTableGateError(f"result drift for {key}")
    mutation_results = result["mutation_results"]
    if not isinstance(mutation_results, list) or len(mutation_results) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("mutation result shape drift")
    for item in mutation_results:
        if not isinstance(item, dict):
            raise AttentionKvFourHeadFusedSoftmaxTableGateError("mutation result shape drift")
        if set(item) != {"name", "rejected", "error"}:
            raise AttentionKvFourHeadFusedSoftmaxTableGateError("mutation result schema drift")
    mutation_names = tuple(item["name"] for item in mutation_results)
    if mutation_names != EXPECTED_MUTATION_NAMES:
        raise AttentionKvFourHeadFusedSoftmaxTableGateError("mutation result name drift")
    for item in mutation_results:
        if (
            not isinstance(item, dict)
            or item.get("rejected") is not True
            or not isinstance(item.get("error"), str)
            or not item["error"]
        ):
            raise AttentionKvFourHeadFusedSoftmaxTableGateError("mutation result rejection drift")


def write_json(path: pathlib.Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_result(result)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = pathlib.Path(handle.name)
        handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    try:
        validate_result(json.loads(tmp_path.read_text(encoding="utf-8")))
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def write_tsv(path: pathlib.Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_result(result)
    row = {column: result[column] for column in TSV_COLUMNS}
    expected_row = {column: str(value) for column, value in row.items()}
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = pathlib.Path(handle.name)
        writer = csv.DictWriter(
            handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(row)
    try:
        with tmp_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        if rows != [expected_row]:
            raise AttentionKvFourHeadFusedSoftmaxTableGateError("TSV round-trip drift")
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    result = run_gate()
    write_json(args.write_json, result)
    write_tsv(args.write_tsv, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
