#!/usr/bin/env python3
"""Checked native Stwo four-head d8 bounded Softmax-table-attention gate for issue #471.

The gate records the first native route combining four-head carried KV state with
a statement-bound bounded Softmax-table weighting policy. It is deliberately
scoped: table membership is verifier-recomputed over public rows, not an
AIR-private lookup argument, and this is not exact Softmax.
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
INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json"
ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json"
INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.tsv"
MAX_INPUT_JSON_BYTES = 1_048_576
MAX_ENVELOPE_JSON_BYTES = 1_048_576
NATIVE_VERIFY_TIMEOUT_SECONDS = 180

NATIVE_INPUT_SCHEMA = "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-air-proof-input-v1"
NATIVE_INPUT_DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
NATIVE_ENVELOPE_DECISION = "GO_STWO_NATIVE_ATTENTION_KV_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
TIMING_POLICY = "single_local_dev_profile_engineering_only_not_public_benchmark"

SCHEMA = "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-v1"
ISSUE = 482
SOURCE_ISSUE = 471
DECISION = "GO_NATIVE_STWO_ATTENTION_KV_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_D8_MASKED_SEQUENCE"
CLAIM_BOUNDARY = (
    "NATIVE_STWO_FOUR_HEAD_D8_CAUSAL_MASKED_BOUNDED_SOFTMAX_TABLE_ATTENTION_KV_PROOF_"
    "NOT_EXACT_SOFTMAX_NOT_PROOF_AGGREGATION_NOT_LONG_CONTEXT_NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD"
)
FIRST_BLOCKER = "NO_AIR_PRIVATE_LOOKUP_ARGUMENT_EXACT_SOFTMAX_EXP_DIV_AIR_OR_HEAD_AGGREGATION_YET"
ROUTE_ID = "local_stwo_attention_kv_four_head_bounded_softmax_table_masked_sequence_proof"

TARGET_ID = "attention-kv-d8-causal-mask-four-head-bounded-softmax-table-v1"
PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-four-head-bounded-softmax-table-air-proof-v1"
REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-four-head-bounded-softmax-table-v1"
STATEMENT_VERSION = "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-statement-v1"
SEMANTIC_SCOPE = "four_head_d8_bounded_table_softmax_approx_attention_kv_causal_mask_rows_bound_to_statement_receipt"
VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-four-head-bounded-softmax-table:v1"
SEMANTICS = "bounded_table_softmax_approx_attention"
WEIGHT_POLICY = "exp2_half_gap_table_clipped_8_floor_division"
SCORE_SCALE = 1
SCORE_GAP_CLIP = 8
SEQUENCE_LENGTH = 8
WEIGHT_TABLE = (
    {"gap": 0, "weight": 256},
    {"gap": 1, "weight": 181},
    {"gap": 2, "weight": 128},
    {"gap": 3, "weight": 91},
    {"gap": 4, "weight": 64},
    {"gap": 5, "weight": 45},
    {"gap": 6, "weight": 32},
    {"gap": 7, "weight": 23},
    {"gap": 8, "weight": 16},
)
PROOF_SIZE_BYTES = 52746
ENVELOPE_SIZE_BYTES = 788949
COMMITMENTS = {
    "statement_commitment": "blake2b-256:c0fe8e31be336f35dd021bc16d35674750456e17b8cd52dca5718a820aef9db6",
    "public_instance_commitment": "blake2b-256:4bb332e513d1ef635ce76d7fd705e8187800081417fa138f449c47ab8be9069f",
    "score_row_commitment": "blake2b-256:ec1fa95aab49398c1fb3253cf87308e8014c09ad7e3fca6e23b496c72731fa7e",
    "final_kv_cache_commitment": "blake2b-256:b0690b8a16ecc946e1ee5212f43bbef21648df1fe2471d08aaa1df5a87440600",
    "outputs_commitment": "blake2b-256:0a80c5aea1f2611adca6e9d01a3316ae9f5960136021b705125a66ede06a6f09",
    "weight_table_commitment": "blake2b-256:3c3e5002672d7efa6b7a1293d17388c98344f61aceae7914f00a391ce355de62",
}
EXPECTED_ATTENTION_OUTPUTS = (
    [0, -3, 4, -6, 1, 4, -2, 1],
    [-1, -2, 4, -3, 3, 2, -7, 1],
    [-1, -4, 3, -7, 0, 6, -3, 2],
    [-1, -4, 2, -2, 3, 0, -5, 1],
    [0, -2, 4, -5, 1, 1, -1, -2],
    [-1, -1, -1, 0, 0, 1, -8, 2],
    [-4, -1, 3, -2, 2, 5, 1, -5],
    [0, 1, 2, -5, -3, 6, -2, 1],
    [0, -1, 5, -4, 2, 0, -1, -4],
    [-2, -1, 2, -3, 0, 3, -5, 1],
    [0, -1, 5, -4, 2, 0, -1, -4],
    [-2, -1, 0, -1, 1, 1, -7, 2],
    [-3, -1, 3, -3, 1, 5, -1, -4],
    [0, -2, 3, -7, -1, 4, -6, 0],
    [-6, 2, 5, -2, 1, 3, -3, -2],
    [-3, 1, 0, 0, 0, 0, -5, -1],
    [-3, -4, 5, -9, 0, 8, -5, 3],
    [-2, -2, 7, -5, 4, 4, -9, 1],
    [-3, -4, 5, -9, 0, 8, -5, 2],
    [-2, -3, 6, -5, 4, 3, -9, 1],
    [-5, -2, 5, -5, 1, 8, -2, -3],
    [-3, -1, 2, -3, 0, 4, -8, 2],
    [-6, -1, 5, -4, 2, 7, -1, -5],
    [-2, 1, 4, -7, -3, 8, -4, 1],
    [-4, -3, 4, -8, 0, 7, -5, 2],
    [-8, 3, 7, -3, 1, 5, -6, -1],
    [-5, -2, 4, -7, 0, 7, -4, -1],
    [-4, -1, 2, -3, 1, 3, -9, 2],
    [-6, 0, 5, -4, 2, 7, -2, -4],
    [-5, 0, 5, -6, -1, 5, -6, 0],
    [-8, 2, 7, -4, 1, 5, -5, -2],
    [-5, 1, 2, -2, 0, 2, -7, -1],
)
EXPECTED_MUTATION_NAMES = (
    "four_head_table_statement_commitment_relabeling",
    "four_head_table_public_instance_commitment_relabeling",
    "four_head_table_head_count_relabeling",
    "four_head_table_weight_policy_relabeling",
    "four_head_table_weight_table_commitment_relabeling",
    "four_head_table_score_scale_relabeling",
    "four_head_table_score_gap_clip_relabeling",
    "four_head_table_attention_outputs_relabeling",
    "four_head_table_cross_head_output_swap_relabeling",
    "four_head_table_outputs_commitment_relabeling",
    "four_head_table_score_row_count_relabeling",
    "four_head_table_quotient_remainder_row_drift",
    "four_head_table_final_kv_relabeling",
    "four_head_table_final_kv_cross_head_swap_relabeling",
    "four_head_table_target_id_relabeling",
    "four_head_table_backend_version_relabeling",
    "proof_size_metric_smuggling",
    "envelope_size_metric_smuggling",
    "claim_boundary_exact_softmax_overclaim",
    "first_blocker_removed",
    "non_claim_removed",
    "receipt_unknown_field_injection",
    "unknown_field_injection",
)
SOURCE_PAIR_MUTATION_NAMES = {
    "four_head_table_quotient_remainder_row_drift",
    "four_head_table_final_kv_cross_head_swap_relabeling",
}
MUTATION_CASE_KEYS = {"name", "rejected", "error"}
_NATIVE_VERIFY_CACHE: set[tuple[str, int]] = set()
NON_CLAIMS = (
    "not exact Softmax attention",
    "not exp/div Softmax semantics",
    "not full autoregressive inference",
    "not recursive verification or PCD",
    "not a long-context benchmark",
    "not a public performance benchmark row",
    "not a Starknet deployment result",
    "source arithmetic proof only; AIR-private lookup membership is checked by the separate LogUp sidecar",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_four_head_bounded_softmax_table_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_four_head_bounded_softmax_table_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_four_head_bounded_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_four_head_bounded_softmax_table_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_four_head_bounded_softmax_table_native_gate",
    "just lib",
    "just gate-fast",
    "just gate",
)
TSV_COLUMNS = (
    "decision",
    "route_id",
    "semantics",
    "weight_policy",
    "score_gap_clip",
    "weight_table_commitment",
    "key_width",
    "value_width",
    "head_count",
    "sequence_length",
    "score_rows",
    "trace_rows",
    "proof_size_bytes",
    "envelope_size_bytes",
    "mutations_checked",
    "mutations_rejected",
    "statement_commitment",
)


class AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise ImportError(f"failed to import {module_name} from {path}: {err}") from err
    return module


INPUT_MODULE = load_script_module(INPUT_SCRIPT, "zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input")


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    bounded_file_size(path, max_bytes, label)
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"{label} size drift: read more than {max_bytes} bytes")
        return json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"failed to read {label}: {err}") from err


def read_bounded_bytes(path: pathlib.Path, max_bytes: int, label: str) -> bytes:
    expected_size = bounded_file_size(path, max_bytes, label)
    try:
        raw = path.read_bytes()
    except OSError as err:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"failed to read {label}: {err}") from err
    if len(raw) != expected_size:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(
            f"{label} read size drift: stat={expected_size}, read={len(raw)}"
        )
    return raw


def bounded_file_size(path: pathlib.Path, max_bytes: int, label: str) -> int:
    if not path.is_file():
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"{label} size drift: got {size}, max {max_bytes}")
    return size


def verify_native_envelope_bytes(envelope_bytes: bytes, label: str) -> None:
    if len(envelope_bytes) <= 0 or len(envelope_bytes) > MAX_ENVELOPE_JSON_BYTES:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(
            f"{label} size drift: got {len(envelope_bytes)}, max {MAX_ENVELOPE_JSON_BYTES}"
        )
    digest = hashlib.blake2b(envelope_bytes, digest_size=32).hexdigest()
    cache_key = (digest, len(envelope_bytes))
    if cache_key in _NATIVE_VERIFY_CACHE:
        return
    with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as tmp:
        tmp.write(envelope_bytes)
        tmp_path = pathlib.Path(tmp.name)
    command = [
        "cargo",
        "+nightly-2025-07-14",
        "run",
        "--features",
        "stwo-backend",
        "--bin",
        "zkai_attention_kv_native_four_head_bounded_softmax_table_proof",
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
            timeout=NATIVE_VERIFY_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(
            f"native bounded Softmax-table verifier failed to run for {label}: {err}"
        ) from err
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        suffix = detail[-1] if detail else f"exit code {completed.returncode}"
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(
            f"native bounded Softmax-table verifier rejected {label}: {suffix}"
        )
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(
            f"native bounded Softmax-table verifier emitted malformed JSON for {label}: {err}"
        ) from err
    expected_summary = {
        "mode": "verify",
        "verified": True,
        "proof_size_bytes": PROOF_SIZE_BYTES,
        "envelope_size_bytes": len(envelope_bytes),
        "statement_commitment": COMMITMENTS["statement_commitment"],
        "score_row_count": 208,
        "trace_row_count": 256,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(
                f"native bounded Softmax-table verifier summary drift for {key}: got {summary.get(key)!r}"
            )
    _NATIVE_VERIFY_CACHE.add(cache_key)


def verify_native_envelope(path: pathlib.Path) -> None:
    verify_native_envelope_bytes(read_bounded_bytes(path, MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope"), str(path))


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def validate_source_pair(input_payload: Any, envelope: Any) -> None:
    if not isinstance(input_payload, dict) or not isinstance(envelope, dict):
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("input/envelope must be objects")
    allowed_envelope_keys = {
        "proof_backend",
        "proof_backend_version",
        "statement_version",
        "semantic_scope",
        "decision",
        "input",
        "proof",
    }
    extra_envelope_keys = set(envelope) - allowed_envelope_keys
    if extra_envelope_keys:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(
            f"unknown envelope field(s): {sorted(extra_envelope_keys)}"
        )
    if input_payload.get("schema") != NATIVE_INPUT_SCHEMA:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("input schema drift")
    if input_payload.get("decision") != NATIVE_INPUT_DECISION:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("input decision drift")
    try:
        INPUT_MODULE.validate_payload(input_payload)
    except Exception as err:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"source input validation drift: {err}") from err
    if envelope.get("input") != input_payload:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("proof envelope/input split-brain drift")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("proof backend drift")
    if envelope.get("proof_backend_version") != REQUIRED_BACKEND_VERSION:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("proof backend version drift")
    if envelope.get("statement_version") != STATEMENT_VERSION:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("statement version drift")
    if envelope.get("semantic_scope") != SEMANTIC_SCOPE:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("semantic scope drift")
    if envelope.get("decision") != NATIVE_ENVELOPE_DECISION:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("proof envelope decision drift")
    proof = envelope.get("proof")
    if not isinstance(proof, list):
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("proof bytes must be a list")
    for index, byte in enumerate(proof):
        if isinstance(byte, bool) or not isinstance(byte, int):
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"proof byte[{index}] must be an integer")
        if byte < 0 or byte > 255:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"proof byte[{index}] outside byte range")
    if len(proof) != PROOF_SIZE_BYTES:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("proof byte length drift")
    if input_payload.get("target_id") != TARGET_ID:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("target_id drift")
    if input_payload.get("proof_version") != PROOF_VERSION:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("proof_version drift")
    if input_payload.get("required_backend_version") != REQUIRED_BACKEND_VERSION:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("required_backend_version drift")
    if input_payload.get("statement_version") != STATEMENT_VERSION:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("statement_version drift")
    if input_payload.get("semantic_scope") != SEMANTIC_SCOPE:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("semantic_scope drift")
    if input_payload.get("verifier_domain") != VERIFIER_DOMAIN:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("verifier_domain drift")
    if input_payload.get("semantics") != SEMANTICS:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("semantics drift")
    if input_payload.get("weight_policy") != WEIGHT_POLICY:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("weight_policy drift")
    if input_payload.get("score_scale") != SCORE_SCALE:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("score_scale drift")
    if input_payload.get("score_gap_clip") != SCORE_GAP_CLIP:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("score_gap_clip drift")
    if input_payload.get("weight_table") != list(WEIGHT_TABLE):
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("weight_table drift")
    if input_payload.get("head_count") != 4:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("head_count drift")
    if tuple(input_payload.get("attention_outputs", [])) != EXPECTED_ATTENTION_OUTPUTS:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("attention_outputs drift")
    for key, expected in COMMITMENTS.items():
        if input_payload.get(key) != expected:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"{key} drift")


def receipt_summary(input_payload: dict[str, Any], envelope: dict[str, Any], envelope_size_bytes: int) -> dict[str, Any]:
    validate_source_pair(input_payload, envelope)
    return {
        "route_id": ROUTE_ID,
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "decision": DECISION,
        "target_id": TARGET_ID,
        "proof_version": PROOF_VERSION,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "statement_version": STATEMENT_VERSION,
        "semantic_scope": SEMANTIC_SCOPE,
        "verifier_domain": VERIFIER_DOMAIN,
        "semantics": SEMANTICS,
        "weight_policy": WEIGHT_POLICY,
        "score_scale": input_payload["score_scale"],
        "score_gap_clip": input_payload["score_gap_clip"],
        "weight_table": input_payload["weight_table"],
        "key_width": input_payload["key_width"],
        "value_width": input_payload["value_width"],
        "head_count": input_payload["head_count"],
        "sequence_length": input_payload["sequence_length"],
        "initial_kv_items": input_payload["initial_kv_items"],
        "final_kv_items": input_payload["final_kv_items"],
        "score_rows": input_payload["score_row_count"],
        "trace_rows": input_payload["trace_row_count"],
        "attention_outputs": input_payload["attention_outputs"],
        "proof_size_bytes": len(envelope["proof"]),
        "envelope_size_bytes": envelope_size_bytes,
        "statement_commitment": input_payload["statement_commitment"],
        "public_instance_commitment": input_payload["public_instance_commitment"],
        "score_row_commitment": input_payload["score_row_commitment"],
        "final_kv_cache_commitment": input_payload["final_kv_cache_commitment"],
        "outputs_commitment": input_payload["outputs_commitment"],
        "weight_table_commitment": input_payload["weight_table_commitment"],
    }


def mutation_cases_for(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        try:
            if name in SOURCE_PAIR_MUTATION_NAMES:
                mutated_input, mutated_envelope = mutate_source_pair(name)
                validate_source_pair(mutated_input, mutated_envelope)
            else:
                mutated = mutate_payload(payload, name)
                validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvFourHeadBoundedSoftmaxTableNativeGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "accepted mutation"})
    return cases


def build_payload() -> dict[str, Any]:
    input_payload = read_bounded_json(INPUT_JSON, MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
    envelope_raw = read_bounded_bytes(ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
    envelope_size_bytes = len(envelope_raw)
    if envelope_size_bytes != ENVELOPE_SIZE_BYTES:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("bounded Softmax-table envelope size drift")
    try:
        envelope = json.loads(envelope_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"failed to read bounded Softmax-table envelope: {err}") from err
    receipt = receipt_summary(input_payload, envelope, envelope_size_bytes)
    verify_native_envelope_bytes(envelope_raw, str(ENVELOPE_JSON))
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "timing_policy": TIMING_POLICY,
        "bounded_softmax_table_receipt": receipt,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["gate_commitment"] = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "receipt_statement_commitment": receipt["statement_commitment"],
            "first_blocker": payload["first_blocker"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-four-head-bounded-softmax-table-native-gate:v1",
    )
    cases = mutation_cases_for(payload)
    payload["mutation_cases"] = cases
    payload["mutations_checked"] = len(cases)
    payload["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    validate_payload(payload)
    return payload


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        mutated.pop(key, None)
    receipt = mutated["bounded_softmax_table_receipt"]
    if name == "four_head_table_statement_commitment_relabeling":
        receipt["statement_commitment"] = "blake2b-256:" + "55" * 32
    elif name == "four_head_table_public_instance_commitment_relabeling":
        receipt["public_instance_commitment"] = "blake2b-256:" + "66" * 32
    elif name == "four_head_table_head_count_relabeling":
        receipt["head_count"] = 1
    elif name == "four_head_table_weight_policy_relabeling":
        receipt["weight_policy"] = "exact_softmax"
    elif name == "four_head_table_weight_table_commitment_relabeling":
        receipt["weight_table_commitment"] = "blake2b-256:" + "99" * 32
    elif name == "four_head_table_score_scale_relabeling":
        receipt["score_scale"] = 2
    elif name == "four_head_table_score_gap_clip_relabeling":
        receipt["score_gap_clip"] = 4
    elif name == "four_head_table_attention_outputs_relabeling":
        receipt["attention_outputs"][0][0] += 1
    elif name == "four_head_table_cross_head_output_swap_relabeling":
        receipt["attention_outputs"][0], receipt["attention_outputs"][1] = (
            receipt["attention_outputs"][1],
            receipt["attention_outputs"][0],
        )
    elif name == "four_head_table_outputs_commitment_relabeling":
        receipt["outputs_commitment"] = "blake2b-256:" + "77" * 32
    elif name == "four_head_table_score_row_count_relabeling":
        receipt["score_rows"] += 1
    elif name == "four_head_table_final_kv_relabeling":
        receipt["final_kv_cache_commitment"] = "blake2b-256:" + "88" * 32
    elif name == "four_head_table_target_id_relabeling":
        receipt["target_id"] = "attention-kv-d8-causal-mask-exact-softmax-v1"
    elif name == "four_head_table_backend_version_relabeling":
        receipt["required_backend_version"] = "fake-backend"
    elif name == "proof_size_metric_smuggling":
        receipt["proof_size_bytes"] += 1
    elif name == "envelope_size_metric_smuggling":
        receipt["envelope_size_bytes"] += 1
    elif name == "claim_boundary_exact_softmax_overclaim":
        mutated["claim_boundary"] = mutated["claim_boundary"].replace("NOT_EXACT_SOFTMAX_", "")
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "non_claim_removed":
        mutated["non_claims"].pop(0)
    elif name == "receipt_unknown_field_injection":
        receipt["unexpected"] = "nested claim smuggling"
    elif name == "unknown_field_injection":
        mutated["unexpected"] = "claim smuggling"
    else:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"unknown mutation: {name}")
    return mutated


def refresh_source_commitments(input_payload: dict[str, Any]) -> None:
    input_payload["score_row_commitment"] = INPUT_MODULE.rows_commitment(input_payload["score_rows"])
    input_payload["final_kv_cache_commitment"] = INPUT_MODULE.kv_commitment(
        input_payload["final_kv_cache"],
        INPUT_MODULE.FINAL_KV_DOMAIN,
    )
    input_payload["outputs_commitment"] = INPUT_MODULE.outputs_commitment(
        input_payload["input_steps"],
        input_payload["attention_outputs"],
    )
    input_payload["statement_commitment"] = INPUT_MODULE.statement_commitment(input_payload)
    input_payload["public_instance_commitment"] = INPUT_MODULE.public_instance_commitment(
        input_payload["statement_commitment"]
    )


def mutate_source_pair(name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    input_payload = copy.deepcopy(
        read_bounded_json(INPUT_JSON, MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
    )
    envelope = copy.deepcopy(
        read_bounded_json(ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
    )
    if name == "four_head_table_quotient_remainder_row_drift":
        input_payload["score_rows"][0]["output_remainder"][0] += 1
    elif name == "four_head_table_final_kv_cross_head_swap_relabeling":
        input_payload["final_kv_cache"][0], input_payload["final_kv_cache"][2] = (
            input_payload["final_kv_cache"][2],
            input_payload["final_kv_cache"][0],
        )
    else:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"unknown source-pair mutation: {name}")
    refresh_source_commitments(input_payload)
    envelope["input"] = input_payload
    return input_payload, envelope


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("payload must be object")
    allowed_keys = {
        "schema",
        "issue",
        "source_issue",
        "decision",
        "claim_boundary",
        "first_blocker",
        "timing_policy",
        "bounded_softmax_table_receipt",
        "non_claims",
        "validation_commands",
        "gate_commitment",
        "mutation_cases",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
    }
    extra = set(payload) - allowed_keys
    if extra:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"unknown field(s): {sorted(extra)}")
    expected = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "timing_policy": TIMING_POLICY,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"{key} drift")
    receipt = payload.get("bounded_softmax_table_receipt")
    if not isinstance(receipt, dict):
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("missing bounded Softmax-table receipt")
    expected_receipt = {
        "route_id": ROUTE_ID,
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "decision": DECISION,
        "target_id": TARGET_ID,
        "proof_version": PROOF_VERSION,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "statement_version": STATEMENT_VERSION,
        "semantic_scope": SEMANTIC_SCOPE,
        "verifier_domain": VERIFIER_DOMAIN,
        "semantics": SEMANTICS,
        "weight_policy": WEIGHT_POLICY,
        "score_scale": SCORE_SCALE,
        "score_gap_clip": SCORE_GAP_CLIP,
        "weight_table": list(WEIGHT_TABLE),
        "key_width": 8,
        "value_width": 8,
        "head_count": 4,
        "sequence_length": 8,
        "initial_kv_items": 8,
        "final_kv_items": 40,
        "score_rows": 208,
        "trace_rows": 256,
        "attention_outputs": [list(row) for row in EXPECTED_ATTENTION_OUTPUTS],
        "proof_size_bytes": PROOF_SIZE_BYTES,
        "envelope_size_bytes": ENVELOPE_SIZE_BYTES,
    }
    allowed_receipt_keys = set(expected_receipt) | set(COMMITMENTS)
    if set(receipt) != allowed_receipt_keys:
        extra = sorted(set(receipt) - allowed_receipt_keys)
        missing = sorted(allowed_receipt_keys - set(receipt))
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(
            f"bounded Softmax-table receipt schema drift: extra={extra} missing={missing}"
        )
    for key, expected_value in expected_receipt.items():
        if receipt.get(key) != expected_value:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"bounded Softmax-table receipt {key} drift")
    for key, expected_value in COMMITMENTS.items():
        if receipt.get(key) != expected_value:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError(f"bounded Softmax-table receipt {key} drift")
    expected_gate_commitment = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "receipt_statement_commitment": receipt["statement_commitment"],
            "first_blocker": payload["first_blocker"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-four-head-bounded-softmax-table-native-gate:v1",
    )
    if payload.get("gate_commitment") != expected_gate_commitment:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("gate commitment drift")
    if allow_missing_mutation_summary and "mutation_cases" not in payload:
        return
    cases = payload.get("mutation_cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("mutation case count drift")
    names = tuple(case.get("name") for case in cases if isinstance(case, dict))
    if names != EXPECTED_MUTATION_NAMES:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("mutation names drift")
    for case in cases:
        if not isinstance(case, dict) or set(case) != MUTATION_CASE_KEYS:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("mutation case schema drift")
        if case["rejected"] is not True:
            raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("mutation rejection drift")
    if payload.get("mutations_checked") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("mutations checked drift")
    if payload.get("mutations_rejected") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("mutations rejected drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvFourHeadBoundedSoftmaxTableNativeGateError("all mutations rejected drift")


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    receipt = payload["bounded_softmax_table_receipt"]
    row = {
        "decision": payload["decision"],
        "route_id": receipt["route_id"],
        "semantics": receipt["semantics"],
        "weight_policy": receipt["weight_policy"],
        "score_gap_clip": receipt["score_gap_clip"],
        "weight_table_commitment": receipt["weight_table_commitment"],
        "key_width": receipt["key_width"],
        "value_width": receipt["value_width"],
        "head_count": receipt["head_count"],
        "sequence_length": receipt["sequence_length"],
        "score_rows": receipt["score_rows"],
        "trace_rows": receipt["trace_rows"],
        "proof_size_bytes": receipt["proof_size_bytes"],
        "envelope_size_bytes": receipt["envelope_size_bytes"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
        "statement_commitment": receipt["statement_commitment"],
    }
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return buf.getvalue()


def write_json(payload: dict[str, Any], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(payload: dict[str, Any], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_tsv(payload), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    payload = build_payload()
    write_json(payload, args.write_json)
    write_tsv(payload, args.write_tsv)


if __name__ == "__main__":
    main()
