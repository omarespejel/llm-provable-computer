#!/usr/bin/env python3
"""Checked fused native Stwo d32 bounded Softmax-table gate for issue #501.

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
SOURCE_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d32-bounded-softmax-table-proof-2026-05.json"
SOURCE_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d32-bounded-softmax-table-proof-2026-05.envelope.json"
SIDECAR_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d32-softmax-table-logup-sidecar-proof-2026-05.envelope.json"
FUSED_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d32-fused-softmax-table-proof-2026-05.envelope.json"
SOURCE_INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_d32_bounded_softmax_table_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d32-fused-softmax-table-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d32-fused-softmax-table-gate-2026-05.tsv"

MAX_SOURCE_INPUT_JSON_BYTES = 1_048_576
MAX_SOURCE_ENVELOPE_JSON_BYTES = 2_097_152
MAX_SIDECAR_ENVELOPE_JSON_BYTES = 1_048_576
MAX_FUSED_ENVELOPE_JSON_BYTES = 2_097_152
FUSED_VERIFY_TIMEOUT_SECONDS = 180

SCHEMA = "zkai-attention-kv-stwo-native-d32-fused-softmax-table-gate-v1"
ISSUE = 6
SOURCE_ISSUE = 6
SIDECAR_ISSUE = 6
DECISION = "GO_NATIVE_STWO_FUSED_ATTENTION_ARITHMETIC_AND_SOFTMAX_TABLE_LOGUP_MEMBERSHIP"
ROUTE_ID = "local_stwo_attention_kv_d32_fused_bounded_softmax_table_logup_proof"
CLAIM_BOUNDARY = (
    "ONE_NATIVE_STWO_D32_BOUNDED_SOFTMAX_TABLE_ATTENTION_PROOF_WITH_LOGUP_TABLE_MEMBERSHIP_"
    "NOT_EXACT_SOFTMAX_NOT_FULL_INFERENCE_NOT_LONG_CONTEXT_NOT_RECURSION_OR_PCD"
)
FUSION_STATUS = "GO_ONE_NATIVE_STWO_PROOF_OBJECT_WITH_ATTENTION_ARITHMETIC_AND_LOGUP_MEMBERSHIP"
NON_FUSED_STATUS = "GO_MATCHED_D32_SOURCE_PLUS_LOGUP_SIDECAR_COMPARATOR_RECORDED"
TIMING_POLICY = "proof_existence_and_byte_accounting_only_not_public_benchmark"

SOURCE_PROOF_SIZE_BYTES = 101_120
SOURCE_ENVELOPE_SIZE_BYTES = 1_061_990
SIDECAR_PROOF_SIZE_BYTES = 15_562
SIDECAR_ENVELOPE_SIZE_BYTES = 379_293
SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES = SOURCE_PROOF_SIZE_BYTES + SIDECAR_PROOF_SIZE_BYTES
FUSED_PROOF_SIZE_BYTES = 107_261
FUSED_ENVELOPE_SIZE_BYTES = 1_113_806
FUSED_OVER_SOURCE_PROOF_BYTES = FUSED_PROOF_SIZE_BYTES - SOURCE_PROOF_SIZE_BYTES
FUSED_SAVES_VS_SOURCE_PLUS_SIDECAR_BYTES = SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES - FUSED_PROOF_SIZE_BYTES
# Fixed-decimal strings keep checked evidence stable across JSON encoders.
FUSED_TO_SOURCE_PLUS_SIDECAR_RATIO = "0.919259"

SOURCE_STATEMENT_COMMITMENT = "blake2b-256:4af09c5ac6c8450089a161e3bc16203a6ae7ecdf5a7e7db61f8adf5716c7dff2"
SOURCE_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:b766261277d12de6ab09e8e57f45c9f411767f52ef9b873abec13bbd4f0e8b82"
SOURCE_SCORE_ROW_COMMITMENT = "blake2b-256:41f6f2bc5241757627ec0a4f18dad27fe81a5a07070127bd7c131b9c4c54bf4d"
SOURCE_WEIGHT_TABLE_COMMITMENT = "blake2b-256:5d051b56bc57cec33985c25ff686379434c3419c3b52b7374840590f64ace458"
SOURCE_WEIGHT_POLICY = "exp2_half_gap_table_clipped_8_floor_division"
SOURCE_SCORE_GAP_CLIP = 8
SOURCE_SCORE_ROWS = 52
SOURCE_TRACE_ROWS = 64
SOURCE_TABLE_ROWS = 9
LOOKUP_RELATION = "AttentionKvD32FusedSoftmaxTableRelation"
LOOKUP_RELATION_WIDTH = 2
SIDECAR_LOOKUP_RELATION = "AttentionKvD32SoftmaxTableLookupRelation"
SIDECAR_LOOKUP_RELATION_WIDTH = 2
SIDECAR_BACKEND_VERSION = "stwo-attention-kv-d32-softmax-table-logup-sidecar-proof-v1"
SIDECAR_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-d32-softmax-table-logup-sidecar-statement-v1"
SIDECAR_SEMANTIC_SCOPE = "d32_bounded_softmax_table_membership_constrained_by_native_stwo_logup_sidecar"
SIDECAR_TARGET_ID = "attention-kv-d32-causal-mask-bounded-softmax-table-logup-sidecar-v1"
SIDECAR_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-d32-softmax-table-logup-sidecar:v1"

FUSED_BACKEND_VERSION = "stwo-attention-kv-d32-fused-bounded-softmax-table-logup-v1"
FUSED_PROOF_SCHEMA_VERSION = "stwo-attention-kv-d32-fused-bounded-softmax-table-logup-proof-v1"
FUSED_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-d32-fused-softmax-table-logup-statement-v1"
FUSED_SEMANTIC_SCOPE = "d32_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof"
FUSED_TARGET_ID = "attention-kv-d32-causal-mask-fused-bounded-softmax-table-logup-v1"
FUSED_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-d32-fused-bounded-softmax-table-logup:v1"
FUSED_PROOF_COMMITMENTS = 4
FUSED_TRACE_COMMITMENTS = 3

TABLE_MULTIPLICITIES = (
    {"gap": 0, "weight": 256, "multiplicity": 8},
    {"gap": 1, "weight": 181, "multiplicity": 0},
    {"gap": 2, "weight": 128, "multiplicity": 1},
    {"gap": 3, "weight": 91, "multiplicity": 0},
    {"gap": 4, "weight": 64, "multiplicity": 0},
    {"gap": 5, "weight": 45, "multiplicity": 0},
    {"gap": 6, "weight": 32, "multiplicity": 0},
    {"gap": 7, "weight": 23, "multiplicity": 0},
    {"gap": 8, "weight": 16, "multiplicity": 43},
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
    "lookup_relation_relabeling",
    "lookup_claim_count_metric_smuggling",
    "source_plus_sidecar_metric_smuggling",
    "fused_proof_size_metric_smuggling",
    "source_input_statement_commitment_relabeling",
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
    "cargo +nightly-2025-07-14 test --locked attention_kv_d32_fused_softmax_table --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_d32_fused_softmax_table_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-d32-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-d32-fused-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_d32_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d32-fused-softmax-table-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_d32_fused_softmax_table_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d32-fused-softmax-table-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d32-fused-softmax-table-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_d32_fused_softmax_table_native_gate",
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
    "source_statement_commitment",
    "source_weight_table_commitment",
)

_FUSED_VERIFY_CACHE: set[tuple[str, int]] = set()


class AttentionKvD32FusedSoftmaxTableGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise ImportError(f"failed to import {module_name} from {path}: {err}") from err
    return module


SOURCE_INPUT_MODULE = load_script_module(
    SOURCE_INPUT_SCRIPT, "zkai_attention_kv_stwo_native_d32_bounded_softmax_table_proof_input"
)


def read_bounded_bytes(path: pathlib.Path, max_bytes: int, label: str) -> bytes:
    if not path.is_file():
        raise AttentionKvD32FusedSoftmaxTableGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"{label} size drift: got {size}, max {max_bytes}")
    try:
        raw = path.read_bytes()
    except OSError as err:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"failed to read {label}: {err}") from err
    if len(raw) != size:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"{label} read size drift: stat={size}, read={len(raw)}")
    return raw


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    raw = read_bounded_bytes(path, max_bytes, label)
    return parse_bounded_json_bytes(raw, label)


def parse_bounded_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"failed to decode {label}: {err}") from err


def expect_artifact_size(raw: bytes, expected_size: int, label: str) -> None:
    if len(raw) != expected_size:
        raise AttentionKvD32FusedSoftmaxTableGateError(
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


def parse_stark_proof(proof_bytes: list[Any], expected_bytes: int, label: str) -> dict[str, Any]:
    if not isinstance(proof_bytes, list):
        raise AttentionKvD32FusedSoftmaxTableGateError(f"{label} proof must be a byte list")
    if len(proof_bytes) != expected_bytes:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"{label} proof byte length drift")
    if any(not isinstance(byte, int) or isinstance(byte, bool) or byte < 0 or byte > 255 for byte in proof_bytes):
        raise AttentionKvD32FusedSoftmaxTableGateError(f"{label} proof bytes must be uint8 values")
    try:
        payload = json.loads(bytes(proof_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"failed to decode {label} proof payload: {err}") from err
    if set(payload) != {"stark_proof"}:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"{label} proof payload schema drift")
    stark_proof = payload["stark_proof"]
    if not isinstance(stark_proof, dict):
        raise AttentionKvD32FusedSoftmaxTableGateError(f"{label} stark_proof must be an object")
    commitments = stark_proof.get("commitments")
    if not isinstance(commitments, list) or len(commitments) != FUSED_PROOF_COMMITMENTS:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"{label} proof commitment count drift")
    return stark_proof


def same_digit_int_mutation(value: int, label: str) -> int:
    for candidate in (value + 1, value - 1):
        if 0 <= candidate <= 255 and len(str(candidate)) == len(str(value)):
            return candidate
    raise AttentionKvD32FusedSoftmaxTableGateError(f"no same-width byte mutation for {label}")


def mutate_same_size_stark_proof_commitment(envelope: dict[str, Any]) -> None:
    payload = json.loads(bytes(envelope["proof"]).decode("utf-8"))
    commitments = payload["stark_proof"]["commitments"]
    commitments[0][0] = same_digit_int_mutation(
        commitments[0][0], "first proof commitment byte"
    )
    proof_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(proof_bytes) != len(envelope["proof"]):
        raise AttentionKvD32FusedSoftmaxTableGateError("same-size proof mutation changed byte length")
    envelope["proof"] = list(proof_bytes)


def type_strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(type_strict_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(type_strict_equal(a, b) for a, b in zip(left, right))
    return left == right


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def proof_bytes(envelope: dict[str, Any]) -> bytes:
    proof = envelope.get("proof")
    if not isinstance(proof, list) or not all(isinstance(value, int) for value in proof):
        raise AttentionKvD32FusedSoftmaxTableGateError("fused proof bytes drift")
    return bytes(proof)


def fused_artifact_commitments(envelope: dict[str, Any]) -> tuple[str, str]:
    envelope_commitment = "blake2b-256:" + hashlib.blake2b(
        canonical_json_bytes(envelope), digest_size=32
    ).hexdigest()
    proof_commitment = "blake2b-256:" + hashlib.blake2b(proof_bytes(envelope), digest_size=32).hexdigest()
    return envelope_commitment, proof_commitment


def verify_fused_envelope_bytes_with_native_cli(envelope_bytes: bytes, label: str) -> None:
    if len(envelope_bytes) <= 0 or len(envelope_bytes) > MAX_FUSED_ENVELOPE_JSON_BYTES:
        raise AttentionKvD32FusedSoftmaxTableGateError(
            f"{label} size drift: got {len(envelope_bytes)}, max {MAX_FUSED_ENVELOPE_JSON_BYTES}"
        )
    digest = hashlib.blake2b(envelope_bytes, digest_size=32).hexdigest()
    cache_key = (digest, len(envelope_bytes))
    if cache_key in _FUSED_VERIFY_CACHE:
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
        "zkai_attention_kv_native_d32_fused_softmax_table_proof",
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
        raise AttentionKvD32FusedSoftmaxTableGateError(f"native fused verifier failed to run for {label}: {err}") from err
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        suffix = detail[-1] if detail else f"exit code {completed.returncode}"
        raise AttentionKvD32FusedSoftmaxTableGateError(f"native fused verifier rejected {label}: {suffix}")
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"native fused verifier emitted malformed JSON: {err}") from err
    expected = {
        "mode": "verify",
        "verified": True,
        "proof_size_bytes": FUSED_PROOF_SIZE_BYTES,
        "envelope_size_bytes": len(envelope_bytes),
        "source_plus_sidecar_raw_proof_bytes": SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
    }
    for key, expected_value in expected.items():
        if summary.get(key) != expected_value:
            raise AttentionKvD32FusedSoftmaxTableGateError(
                f"native fused verifier summary drift for {key}: got {summary.get(key)!r}"
            )
    _FUSED_VERIFY_CACHE.add(cache_key)


def expected_summary(source_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "fusion_status": FUSION_STATUS,
        "non_fused_status": NON_FUSED_STATUS,
        "source_statement_commitment": source_input["statement_commitment"],
        "source_public_instance_commitment": source_input["public_instance_commitment"],
        "source_score_row_commitment": source_input["score_row_commitment"],
        "source_weight_table_commitment": source_input["weight_table_commitment"],
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


def validate_source_artifacts(source_input: dict[str, Any], source_envelope: dict[str, Any], sidecar_envelope: dict[str, Any]) -> None:
    try:
        SOURCE_INPUT_MODULE.validate_payload(source_input)
    except Exception as err:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"source input validation drift: {err}") from err
    if not type_strict_equal(source_envelope.get("input"), source_input):
        raise AttentionKvD32FusedSoftmaxTableGateError("source envelope/input split-brain drift")
    if len(source_envelope.get("proof", [])) != SOURCE_PROOF_SIZE_BYTES:
        raise AttentionKvD32FusedSoftmaxTableGateError("source proof size drift")
    if len(sidecar_envelope.get("proof", [])) != SIDECAR_PROOF_SIZE_BYTES:
        raise AttentionKvD32FusedSoftmaxTableGateError("sidecar proof size drift")
    expected_sidecar_scalars = {
        "proof_backend": "stwo",
        "proof_backend_version": SIDECAR_BACKEND_VERSION,
        "statement_version": SIDECAR_STATEMENT_VERSION,
        "semantic_scope": SIDECAR_SEMANTIC_SCOPE,
        "decision": "GO_NATIVE_STWO_AIR_CONSTRAINED_SOFTMAX_TABLE_LOOKUP_RELATION_SIDECAR",
        "target_id": SIDECAR_TARGET_ID,
        "verifier_domain": SIDECAR_VERIFIER_DOMAIN,
    }
    for key, expected_value in expected_sidecar_scalars.items():
        if not type_strict_equal(sidecar_envelope.get(key), expected_value):
            raise AttentionKvD32FusedSoftmaxTableGateError(f"sidecar {key} drift")
    lookup_summary = sidecar_envelope.get("lookup_summary")
    if not isinstance(lookup_summary, dict):
        raise AttentionKvD32FusedSoftmaxTableGateError("sidecar lookup summary missing")
    expected_sidecar = {
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "source_public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "source_score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "score_rows": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
        "weight_policy": SOURCE_WEIGHT_POLICY,
        "lookup_relation": SIDECAR_LOOKUP_RELATION,
        "lookup_relation_width": SIDECAR_LOOKUP_RELATION_WIDTH,
        "lookup_claims": SOURCE_SCORE_ROWS,
    }
    for key, expected_value in expected_sidecar.items():
        if not type_strict_equal(lookup_summary.get(key), expected_value):
            raise AttentionKvD32FusedSoftmaxTableGateError(f"sidecar summary drift for {key}")


def validate_fused_envelope(envelope: Any, source_input: dict[str, Any], *, run_native: bool) -> None:
    if not isinstance(envelope, dict):
        raise AttentionKvD32FusedSoftmaxTableGateError("fused envelope must be an object")
    try:
        SOURCE_INPUT_MODULE.validate_payload(source_input)
    except Exception as err:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"source input validation drift: {err}") from err
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
        raise AttentionKvD32FusedSoftmaxTableGateError(f"unknown fused envelope field(s): {sorted(extra_keys)}")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvD32FusedSoftmaxTableGateError("fused proof backend drift")
    if envelope.get("proof_backend_version") != FUSED_BACKEND_VERSION:
        raise AttentionKvD32FusedSoftmaxTableGateError("fused proof backend version drift")
    if envelope.get("proof_schema_version") != FUSED_PROOF_SCHEMA_VERSION:
        raise AttentionKvD32FusedSoftmaxTableGateError("fused proof schema version drift")
    if envelope.get("statement_version") != FUSED_STATEMENT_VERSION:
        raise AttentionKvD32FusedSoftmaxTableGateError("fused statement version drift")
    if envelope.get("semantic_scope") != FUSED_SEMANTIC_SCOPE:
        raise AttentionKvD32FusedSoftmaxTableGateError("fused semantic scope drift")
    if envelope.get("decision") != DECISION:
        raise AttentionKvD32FusedSoftmaxTableGateError("fused decision drift")
    if envelope.get("target_id") != FUSED_TARGET_ID:
        raise AttentionKvD32FusedSoftmaxTableGateError("fused target id drift")
    if envelope.get("verifier_domain") != FUSED_VERIFIER_DOMAIN:
        raise AttentionKvD32FusedSoftmaxTableGateError("fused verifier domain drift")
    if not type_strict_equal(envelope.get("source_input"), source_input):
        raise AttentionKvD32FusedSoftmaxTableGateError("fused source input split-brain drift")
    if not type_strict_equal(envelope.get("fused_summary"), expected_summary(source_input)):
        raise AttentionKvD32FusedSoftmaxTableGateError("fused summary drift")
    parse_stark_proof(envelope.get("proof"), FUSED_PROOF_SIZE_BYTES, "fused")
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
        "table_multiplicity_drift",
        lambda v: v["fused_summary"]["table_multiplicities"][0].__setitem__(
            "multiplicity", 10
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
    source_envelope, _source_raw = read_sized_envelope(
        SOURCE_ENVELOPE_JSON,
        MAX_SOURCE_ENVELOPE_JSON_BYTES,
        SOURCE_ENVELOPE_SIZE_BYTES,
        "source envelope",
    )
    sidecar_envelope, _sidecar_raw = read_sized_envelope(
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
    validate_source_artifacts(source_input, source_envelope, sidecar_envelope)
    validate_fused_envelope(fused_envelope, source_input, run_native=False)
    verify_fused_envelope_bytes_with_native_cli(fused_raw, str(FUSED_ENVELOPE_JSON))

    mutation_results = []
    for name, mutated, run_native in mutation_cases(fused_envelope):
        try:
            validate_fused_envelope(mutated, source_input, run_native=run_native)
        except Exception as err:  # noqa: BLE001 - gate records exact rejection surface.
            mutation_results.append({"name": name, "rejected": True, "error": str(err)})
        else:
            mutation_results.append({"name": name, "rejected": False, "error": "mutation accepted"})
    mutation_names = tuple(result["name"] for result in mutation_results)
    if mutation_names != EXPECTED_MUTATION_NAMES:
        raise AttentionKvD32FusedSoftmaxTableGateError("mutation case order/name drift")
    rejected = sum(1 for result in mutation_results if result["rejected"])
    if rejected != EXPECTED_MUTATION_COUNT:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"mutation rejection drift: got {rejected}")
    fused_envelope_commitment, fused_proof_commitment = fused_artifact_commitments(fused_envelope)

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
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "fused_envelope_commitment": fused_envelope_commitment,
        "fused_proof_commitment": fused_proof_commitment,
        "table_multiplicities": list(TABLE_MULTIPLICITIES),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_results": mutation_results,
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": rejected,
    }
    validate_result(result)
    return result


def validate_result(result: dict[str, Any]) -> None:
    if not isinstance(result, dict):
        raise AttentionKvD32FusedSoftmaxTableGateError("result must be an object")
    fused_envelope, _fused_raw = read_sized_envelope(
        FUSED_ENVELOPE_JSON,
        MAX_FUSED_ENVELOPE_JSON_BYTES,
        FUSED_ENVELOPE_SIZE_BYTES,
        "fused envelope",
    )
    fused_envelope_commitment, fused_proof_commitment = fused_artifact_commitments(fused_envelope)
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
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "fused_envelope_commitment": fused_envelope_commitment,
        "fused_proof_commitment": fused_proof_commitment,
        "table_multiplicities": list(TABLE_MULTIPLICITIES),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": EXPECTED_MUTATION_COUNT,
    }
    required = set(expected_exact) | {"mutation_results"}
    missing = required - set(result)
    if missing:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"missing result keys: {sorted(missing)}")
    extra = set(result) - required
    if extra:
        raise AttentionKvD32FusedSoftmaxTableGateError(f"unknown result keys: {sorted(extra)}")
    for key in ("fused_envelope_commitment", "fused_proof_commitment"):
        value = expected_exact[key]
        if not isinstance(value, str) or not value.startswith("blake2b-256:"):
            raise AttentionKvD32FusedSoftmaxTableGateError(f"{key} drift")
    for key, expected_value in expected_exact.items():
        if not type_strict_equal(result.get(key), expected_value):
            raise AttentionKvD32FusedSoftmaxTableGateError(f"result drift for {key}")
    mutation_results = result["mutation_results"]
    if not isinstance(mutation_results, list) or len(mutation_results) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvD32FusedSoftmaxTableGateError("mutation result shape drift")
    for item in mutation_results:
        if not isinstance(item, dict):
            raise AttentionKvD32FusedSoftmaxTableGateError("mutation result shape drift")
        if set(item) != {"name", "rejected", "error"}:
            raise AttentionKvD32FusedSoftmaxTableGateError("mutation result schema drift")
    mutation_names = tuple(item["name"] for item in mutation_results)
    if mutation_names != EXPECTED_MUTATION_NAMES:
        raise AttentionKvD32FusedSoftmaxTableGateError("mutation result name drift")
    for item in mutation_results:
        if (
            not isinstance(item, dict)
            or item.get("rejected") is not True
            or not isinstance(item.get("error"), str)
            or not item["error"]
        ):
            raise AttentionKvD32FusedSoftmaxTableGateError("mutation result rejection drift")


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
            raise AttentionKvD32FusedSoftmaxTableGateError("TSV round-trip drift")
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
