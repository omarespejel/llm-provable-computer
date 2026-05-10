#!/usr/bin/env python3
"""Checked fused native Stwo two-head seq32 bounded Softmax-table gate for issue #537.

This gate records the scale-up attempt after the checked two-head fixed-length
route: one native Stwo proof object checks both attention arithmetic and LogUp
table membership for a deterministic two-head, thirty-two-step-per-head d=8
fixture. It remains an implementation-exact integer table/floor-division
kernel result, not a real-valued Softmax or full-inference claim.
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
SOURCE_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.json"
FUSED_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-proof-2026-05.envelope.json"
SOURCE_INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_two_head_seq32_bounded_softmax_table_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.tsv"

MAX_SOURCE_INPUT_JSON_BYTES = 4_194_304
MAX_SOURCE_ENVELOPE_JSON_BYTES = 8_388_608
MAX_SIDECAR_ENVELOPE_JSON_BYTES = 8_388_608
MAX_FUSED_ENVELOPE_JSON_BYTES = 8_388_608
FUSED_VERIFY_TIMEOUT_SECONDS = 300

SCHEMA = "zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-v1"
ISSUE = 537
SOURCE_ISSUE = 537
SIDECAR_ISSUE = 537
DECISION = "GO_NATIVE_STWO_TWO_HEAD_SEQ32_FUSED_ATTENTION_ARITHMETIC_AND_SOFTMAX_TABLE_LOGUP_MEMBERSHIP"
ROUTE_ID = "local_stwo_attention_kv_two_head_seq32_fused_bounded_softmax_table_logup_proof"
CLAIM_BOUNDARY = (
    "ONE_NATIVE_STWO_TWO_HEAD_SEQ32_BOUNDED_SOFTMAX_TABLE_ATTENTION_PROOF_WITH_LOGUP_TABLE_MEMBERSHIP_"
    "NOT_EXACT_SOFTMAX_NOT_FULL_INFERENCE_NOT_LONG_CONTEXT_NOT_RECURSION_OR_PCD"
)
FUSION_STATUS = "GO_ONE_NATIVE_STWO_PROOF_OBJECT_WITH_ATTENTION_ARITHMETIC_AND_LOGUP_MEMBERSHIP"
NON_FUSED_STATUS = "GO_MATCHED_TWO_HEAD_SEQ32_SOURCE_PLUS_LOGUP_SIDECAR_COMPARATOR_RECORDED"
TIMING_POLICY = "proof_existence_and_byte_accounting_only_not_public_benchmark"

SOURCE_PROOF_SIZE_BYTES = 62_983
SOURCE_ENVELOPE_SIZE_BYTES = 2_418_371
SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES = 98_012
SIDECAR_PROOF_SIZE_BYTES = 35_029
SIDECAR_ENVELOPE_SIZE_BYTES = 2_196_691
FUSED_PROOF_SIZE_BYTES = 66_327
FUSED_ENVELOPE_SIZE_BYTES = 2_448_150
FUSED_OVER_SOURCE_PROOF_BYTES = FUSED_PROOF_SIZE_BYTES - SOURCE_PROOF_SIZE_BYTES
FUSED_SAVES_VS_SOURCE_PLUS_SIDECAR_BYTES = SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES - FUSED_PROOF_SIZE_BYTES
FUSED_TO_SOURCE_PLUS_SIDECAR_RATIO = "0.676723"

SOURCE_STATEMENT_COMMITMENT = "blake2b-256:03267fbc084726c1249fbd6025cc3ec3fdc30214f7c75693810c5b72188ace55"
SOURCE_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:0ad7c095d610d9dc23e830c61fb208dffa70a14540ccada29ae60294cc480fb6"
SOURCE_SCORE_ROW_COMMITMENT = "blake2b-256:e5c820264442f869e8d0516306da9d563541f5178b11df3e0e75d8174c261e22"
SOURCE_FINAL_KV_CACHE_COMMITMENT = "blake2b-256:025974913402fa376e990b6c86f91e317e3603d887e690c26b2c90bf8cb28cb8"
SOURCE_OUTPUTS_COMMITMENT = "blake2b-256:893d7caa9d9ce54e43508c4890209805f24a7cba43d0951592e812de1dbcfd69"
SOURCE_WEIGHT_TABLE_COMMITMENT = "blake2b-256:79dd63cc0ca1403a4d4e9673ecdfd6aa3ab728841e54ae14cca309322b7e38f2"
SOURCE_HEAD_COUNT = 2
SOURCE_WEIGHT_POLICY = "exp2_half_gap_table_clipped_8_floor_division"
SOURCE_SCORE_GAP_CLIP = 8
SOURCE_SCORE_ROWS = 1184
SOURCE_TRACE_ROWS = 2048
SOURCE_TABLE_ROWS = 9
SOURCE_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-two-head-seq32-bounded-softmax-table-v1"
SOURCE_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-statement-v1"
SOURCE_SEMANTIC_SCOPE = "two_head_seq32_d8_bounded_table_softmax_approx_attention_kv_causal_mask_rows_bound_to_statement_receipt"
SOURCE_DECISION = "GO_STWO_NATIVE_ATTENTION_KV_TWO_HEAD_SEQ32_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
SOURCE_INPUT_DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_TWO_HEAD_SEQ32_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
SOURCE_TARGET_ID = "attention-kv-d8-causal-mask-two-head-seq32-bounded-softmax-table-v1"
SOURCE_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-seq32-bounded-softmax-table:v1"
LOOKUP_RELATION = "AttentionKvTwoHeadSeq32FusedSoftmaxTableRelation"
LOOKUP_RELATION_WIDTH = 2
FUSED_BACKEND_VERSION = "stwo-attention-kv-two-head-seq32-fused-bounded-softmax-table-logup-v1"
FUSED_PROOF_SCHEMA_VERSION = "stwo-attention-kv-two-head-seq32-fused-bounded-softmax-table-logup-proof-v1"
FUSED_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-logup-statement-v1"
FUSED_SEMANTIC_SCOPE = "two_head_seq32_d8_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof"
FUSED_TARGET_ID = "attention-kv-two-head-seq32-d8-causal-mask-fused-bounded-softmax-table-logup-v1"
FUSED_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-seq32-fused-bounded-softmax-table-logup:v1"

TABLE_MULTIPLICITIES = (
    {"gap": 0, "weight": 256, "multiplicity": 74},
    {"gap": 1, "weight": 181, "multiplicity": 6},
    {"gap": 2, "weight": 128, "multiplicity": 10},
    {"gap": 3, "weight": 91, "multiplicity": 5},
    {"gap": 4, "weight": 64, "multiplicity": 9},
    {"gap": 5, "weight": 45, "multiplicity": 15},
    {"gap": 6, "weight": 32, "multiplicity": 8},
    {"gap": 7, "weight": 23, "multiplicity": 6},
    {"gap": 8, "weight": 16, "multiplicity": 1051},
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
    "claim_boundary_exact_softmax_overclaim",
    "source_statement_commitment_relabeling",
    "source_head_count_metric_smuggling",
    "lookup_claim_count_metric_smuggling",
    "source_plus_sidecar_metric_smuggling",
    "fused_savings_metric_smuggling",
    "fused_ratio_metric_smuggling",
    "table_multiplicity_drift",
    "source_input_head_index_relabeling",
    "source_input_output_remainder_drift",
    "proof_byte_tamper",
    "target_id_relabeling",
    "verifier_domain_relabeling",
    "statement_version_relabeling",
    "proof_backend_version_relabeling",
    "proof_schema_version_relabeling",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_stwo_native_two_head_seq32_bounded_softmax_table_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.tsv",
    "cargo +nightly-2025-07-14 test --locked attention_kv_native_two_head_seq32_bounded_softmax_table_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_seq32_bounded_softmax_table_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_seq32_bounded_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 test --locked attention_kv_two_head_seq32_fused_softmax_table --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_seq32_fused_softmax_table_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_seq32_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 test --locked attention_kv_two_head_seq32_softmax_table_lookup --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_seq32_softmax_table_lookup_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_two_head_seq32_air_private_softmax_table_lookup_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-gate-2026-05.tsv",
    "python3 scripts/zkai_attention_kv_two_head_seq32_fused_softmax_table_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_seq32_fused_softmax_table_native_gate",
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

_NATIVE_VERIFY_CACHE: dict[tuple[str, int], dict[str, Any]] = {}


class AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE_INPUT_MODULE = load_script_module(
    SOURCE_INPUT_SCRIPT, "zkai_attention_kv_stwo_native_two_head_seq32_bounded_softmax_table_proof_input"
)


def read_bounded_bytes(path: pathlib.Path, max_bytes: int, label: str) -> bytes:
    try:
        if not path.is_file():
            raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"missing {label}: {path}")
        size = path.stat().st_size
        if size <= 0 or size > max_bytes:
            raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"{label} size drift: got {size}, max {max_bytes}")
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except OSError as err:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"{label} read failed: {err}") from err
    if len(raw) <= 0 or len(raw) > max_bytes:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(
            f"{label} size drift: got {len(raw)}, max {max_bytes}"
        )
    return raw


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    raw = read_bounded_bytes(path, max_bytes, label)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"{label} is not JSON: {err}") from err


def read_expected_fused_envelope() -> tuple[dict[str, Any], bytes]:
    envelope_bytes = read_bounded_bytes(FUSED_ENVELOPE_JSON, MAX_FUSED_ENVELOPE_JSON_BYTES, "fused envelope")
    if len(envelope_bytes) != FUSED_ENVELOPE_SIZE_BYTES:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(
            f"fused envelope file size drift: got {len(envelope_bytes)}, expected {FUSED_ENVELOPE_SIZE_BYTES}"
        )
    try:
        envelope = json.loads(envelope_bytes)
    except json.JSONDecodeError as err:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"fused envelope is not JSON: {err}") from err
    if not isinstance(envelope, dict):
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("fused envelope must be a JSON object")
    return envelope, envelope_bytes


def type_strict_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(type_strict_equal(actual[key], expected[key]) for key in expected)
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            type_strict_equal(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return actual == expected


def assert_exact_keys(mapping: dict[str, Any], expected_keys: set[str], label: str) -> None:
    actual = set(mapping)
    if actual != expected_keys:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(
            f"{label} key drift: missing={sorted(expected_keys - actual)} extra={sorted(actual - expected_keys)}"
        )


def assert_fields(mapping: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, expected_value in expected.items():
        if mapping.get(key) != expected_value:
            raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(
                f"{label} field drift for {key}: got {mapping.get(key)!r}, expected {expected_value!r}"
            )


def proof_bytes(envelope: dict[str, Any]) -> bytes:
    proof = envelope.get("proof")
    if not isinstance(proof, list):
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("proof must be a byte list")
    if len(proof) != FUSED_PROOF_SIZE_BYTES:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("proof byte length drift")
    if any(not isinstance(byte, int) or isinstance(byte, bool) or byte < 0 or byte > 255 for byte in proof):
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("proof byte outside uint8 range")
    return bytes(proof)


def mutate_same_size_stark_proof_commitment(envelope: dict[str, Any]) -> None:
    proof = envelope.get("proof")
    if not isinstance(proof, list) or not proof:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("cannot mutate missing proof bytes")
    proof[0] = (int(proof[0]) + 1) % 256


def validate_source_input_contract(source_input: dict[str, Any]) -> None:
    SOURCE_INPUT_MODULE.validate_payload(source_input)
    expected = {
        "decision": SOURCE_INPUT_DECISION,
        "target_id": SOURCE_TARGET_ID,
        "required_backend_version": SOURCE_BACKEND_VERSION,
        "statement_version": SOURCE_STATEMENT_VERSION,
        "semantic_scope": SOURCE_SEMANTIC_SCOPE,
        "verifier_domain": SOURCE_VERIFIER_DOMAIN,
        "head_count": SOURCE_HEAD_COUNT,
        "score_row_count": SOURCE_SCORE_ROWS,
        "trace_row_count": SOURCE_TRACE_ROWS,
        "weight_policy": SOURCE_WEIGHT_POLICY,
        "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
        "statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "final_kv_cache_commitment": SOURCE_FINAL_KV_CACHE_COMMITMENT,
        "outputs_commitment": SOURCE_OUTPUTS_COMMITMENT,
        "weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
    }
    assert_fields(source_input, expected, "source input")


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
        "source_head_count": SOURCE_HEAD_COUNT,
        "score_rows": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
        "weight_policy": SOURCE_WEIGHT_POLICY,
        "lookup_relation": LOOKUP_RELATION,
        "lookup_relation_width": LOOKUP_RELATION_WIDTH,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "source_plus_sidecar_raw_proof_bytes": SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        "table_multiplicities": [dict(entry) for entry in TABLE_MULTIPLICITIES],
        "timing_policy": TIMING_POLICY,
        "non_claims": list(NON_CLAIMS),
    }


def expected_fused_verifier_summary(envelope_size_bytes: int) -> dict[str, Any]:
    return {
        "mode": "verify",
        "proof_size_bytes": FUSED_PROOF_SIZE_BYTES,
        "envelope_size_bytes": envelope_size_bytes,
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "source_plus_sidecar_raw_proof_bytes": SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        "verified": True,
    }


def assert_native_verifier_summary(mapping: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    assert_exact_keys(mapping, set(expected) | {"schema", "fused_envelope_path"}, label)
    schema = mapping.get("schema")
    if not isinstance(schema, str) or not schema.endswith("-cli-summary-v1"):
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"{label} schema drift")
    path = mapping.get("fused_envelope_path")
    if not isinstance(path, str) or not path.endswith(".json"):
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"{label} fused envelope path drift")
    assert_fields(mapping, expected, label)


def verify_fused_envelope_bytes_with_native_cli(envelope_bytes: bytes) -> None:
    if len(envelope_bytes) <= 0 or len(envelope_bytes) > MAX_FUSED_ENVELOPE_JSON_BYTES:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("fused envelope byte size drift")
    digest = hashlib.blake2b(envelope_bytes, digest_size=32).hexdigest()
    cache_key = (digest, len(envelope_bytes))
    cached = _NATIVE_VERIFY_CACHE.get(cache_key)
    expected = expected_fused_verifier_summary(len(envelope_bytes))
    if cached is not None:
        assert_native_verifier_summary(cached, expected, "cached native fused verifier summary")
        return
    with tempfile.TemporaryDirectory() as tmp:
        envelope_path = pathlib.Path(tmp) / "fused-envelope.json"
        envelope_path.write_bytes(envelope_bytes)
        with subprocess.Popen(
            [
                "cargo",
                "+nightly-2025-07-14",
                "run",
                "--locked",
                "--features",
                "stwo-backend",
                "--bin",
                "zkai_attention_kv_native_two_head_seq32_fused_softmax_table_proof",
                "--",
                "verify",
                str(envelope_path),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as proc:
            try:
                stdout, stderr = proc.communicate(timeout=FUSED_VERIFY_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as error:
                proc.kill()
                _stdout, stderr = proc.communicate()
                raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(
                    f"native fused verifier timed out after {FUSED_VERIFY_TIMEOUT_SECONDS}s: {stderr[-1000:]}"
                ) from error
    if proc.returncode != 0:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(
            f"native fused verifier failed with {proc.returncode}: {stderr[-1000:]}"
        )
    summary = json.loads(stdout)
    assert_native_verifier_summary(summary, expected, "native fused verifier summary")
    _NATIVE_VERIFY_CACHE[cache_key] = summary


def validate_fused_envelope(
    envelope: dict[str, Any],
    source_input: dict[str, Any],
    *,
    run_native: bool = False,
    native_envelope_bytes: bytes | None = None,
) -> None:
    validate_source_input_contract(source_input)
    assert_exact_keys(
        envelope,
        {
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
        },
        "fused envelope",
    )
    assert_fields(
        envelope,
        {
            "proof_backend": "stwo",
            "proof_backend_version": FUSED_BACKEND_VERSION,
            "proof_schema_version": FUSED_PROOF_SCHEMA_VERSION,
            "statement_version": FUSED_STATEMENT_VERSION,
            "semantic_scope": FUSED_SEMANTIC_SCOPE,
            "decision": DECISION.replace("TWO_HEAD_SEQ32_", ""),
            "target_id": FUSED_TARGET_ID,
            "verifier_domain": FUSED_VERIFIER_DOMAIN,
        },
        "fused envelope",
    )
    if not type_strict_equal(envelope.get("source_input"), source_input):
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("fused source input split-brain drift")
    if not type_strict_equal(envelope.get("fused_summary"), expected_summary(source_input)):
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("fused summary drift")
    proof_bytes(envelope)
    if run_native:
        verify_fused_envelope_bytes_with_native_cli(native_envelope_bytes or canonical_json_bytes(envelope))


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def mutation_cases(result: dict[str, Any], envelope: dict[str, Any], source_input: dict[str, Any]) -> list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]]:
    cases: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]] = []

    def add(name: str, mutator: Any) -> None:
        result_copy = copy.deepcopy(result)
        envelope_copy = copy.deepcopy(envelope)
        source_copy = copy.deepcopy(source_input)
        mutator(result_copy, envelope_copy, source_copy)
        cases.append((name, result_copy, envelope_copy, source_copy))

    add("fused_decision_relabeling", lambda r, _e, _s: r.__setitem__("decision", "GO_REAL_SOFTMAX"))
    add("fusion_status_relabeling", lambda _r, e, _s: e["fused_summary"].__setitem__("fusion_status", "GO_SIDE_CAR_ONLY"))
    add("claim_boundary_exact_softmax_overclaim", lambda r, _e, _s: r.__setitem__("claim_boundary", "GO_EXACT_REAL_SOFTMAX"))
    add("source_statement_commitment_relabeling", lambda _r, e, _s: e["fused_summary"].__setitem__("source_statement_commitment", "blake2b-256:" + "55" * 32))
    add("source_head_count_metric_smuggling", lambda _r, e, _s: e["fused_summary"].__setitem__("source_head_count", 9))
    add("lookup_claim_count_metric_smuggling", lambda _r, e, _s: e["fused_summary"].__setitem__("lookup_claims", SOURCE_SCORE_ROWS - 1))
    add("source_plus_sidecar_metric_smuggling", lambda r, _e, _s: r.__setitem__("source_plus_sidecar_raw_proof_bytes", SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES + 1))
    add("fused_savings_metric_smuggling", lambda r, _e, _s: r.__setitem__("fused_saves_vs_source_plus_sidecar_bytes", FUSED_SAVES_VS_SOURCE_PLUS_SIDECAR_BYTES - 1))
    add("fused_ratio_metric_smuggling", lambda r, _e, _s: r.__setitem__("fused_to_source_plus_sidecar_ratio", "1.000000"))
    add("table_multiplicity_drift", lambda _r, e, _s: e["fused_summary"]["table_multiplicities"][0].__setitem__("multiplicity", 1))
    add("source_input_head_index_relabeling", lambda _r, e, s: (s["score_rows"][0].__setitem__("head_index", 8), e.__setitem__("source_input", s)))
    add("source_input_output_remainder_drift", lambda _r, e, s: (s["score_rows"][0]["output_remainder"].__setitem__(0, 999), e.__setitem__("source_input", s)))
    add("proof_byte_tamper", lambda _r, e, _s: mutate_same_size_stark_proof_commitment(e))
    add("target_id_relabeling", lambda _r, e, _s: e.__setitem__("target_id", "different"))
    add("verifier_domain_relabeling", lambda _r, e, _s: e.__setitem__("verifier_domain", "different"))
    add("statement_version_relabeling", lambda _r, e, _s: e.__setitem__("statement_version", "different"))
    add("proof_backend_version_relabeling", lambda _r, e, _s: e.__setitem__("proof_backend_version", "different"))
    add("proof_schema_version_relabeling", lambda _r, e, _s: e.__setitem__("proof_schema_version", "different"))
    add("unknown_field_injection", lambda _r, e, _s: e.__setitem__("sidecar_proof", []))
    return cases


def validate_result(result: dict[str, Any], envelope: dict[str, Any], source_input: dict[str, Any]) -> None:
    mutation_results = result.get("mutation_results")
    expected = build_result(envelope, source_input, mutation_results if isinstance(mutation_results, list) else [])
    for key, value in expected.items():
        if key == "mutation_results":
            continue
        if result.get(key) != value:
            raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError(f"result drift for {key}")
    validate_fused_envelope(envelope, source_input)
    if not isinstance(mutation_results, list) or len(mutation_results) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("mutation result shape drift")
    if tuple(item.get("name") for item in mutation_results if isinstance(item, dict)) != EXPECTED_MUTATION_NAMES:
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("mutation result name drift")
    if any(item.get("rejected") is not True for item in mutation_results if isinstance(item, dict)):
        raise AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError("mutation accepted")


def build_result(envelope: dict[str, Any], source_input: dict[str, Any], mutation_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
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
        "source_plus_sidecar_raw_proof_bytes": SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        "fused_proof_size_bytes": FUSED_PROOF_SIZE_BYTES,
        "fused_envelope_size_bytes": FUSED_ENVELOPE_SIZE_BYTES,
        "fused_over_source_proof_bytes": FUSED_OVER_SOURCE_PROOF_BYTES,
        "fused_saves_vs_source_plus_sidecar_bytes": FUSED_SAVES_VS_SOURCE_PLUS_SIDECAR_BYTES,
        "fused_to_source_plus_sidecar_ratio": FUSED_TO_SOURCE_PLUS_SIDECAR_RATIO,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "source_head_count": SOURCE_HEAD_COUNT,
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "source_public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "source_score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "source_final_kv_cache_commitment": SOURCE_FINAL_KV_CACHE_COMMITMENT,
        "source_outputs_commitment": SOURCE_OUTPUTS_COMMITMENT,
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "fused_envelope_commitment": "blake2b-256:" + hashlib.blake2b(canonical_json_bytes(envelope), digest_size=32).hexdigest(),
        "fused_proof_commitment": "blake2b-256:" + hashlib.blake2b(proof_bytes(envelope), digest_size=32).hexdigest(),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_results": mutation_results,
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": sum(1 for item in mutation_results if item.get("rejected")),
    }


def baseline_mutation_results() -> list[dict[str, Any]]:
    """Return a structurally valid mutation vector for seeding mutated cases."""

    return [{"name": name, "rejected": True, "error": "baseline placeholder"} for name in EXPECTED_MUTATION_NAMES]


def run_gate() -> dict[str, Any]:
    source_input = read_bounded_json(SOURCE_INPUT_JSON, MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    envelope, envelope_bytes = read_expected_fused_envelope()
    validate_fused_envelope(envelope, source_input, run_native=True, native_envelope_bytes=envelope_bytes)
    result = build_result(envelope, source_input, baseline_mutation_results())
    mutation_results = []
    for name, mutated_result, mutated_envelope, mutated_source in mutation_cases(result, envelope, source_input):
        try:
            validate_result(mutated_result, mutated_envelope, mutated_source)
        except AttentionKvTwoHeadSeq32FusedSoftmaxTableGateError as err:
            mutation_results.append({"name": name, "rejected": True, "error": str(err)})
        else:
            mutation_results.append({"name": name, "rejected": False, "error": "mutation accepted"})
    result = build_result(envelope, source_input, mutation_results)
    validate_result(result, envelope, source_input)
    return result


def write_json(path: pathlib.Path, result: dict[str, Any]) -> None:
    source_input = read_bounded_json(SOURCE_INPUT_JSON, MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    envelope, _envelope_bytes = read_expected_fused_envelope()
    validate_result(result, envelope, source_input)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(path: pathlib.Path, result: dict[str, Any]) -> None:
    source_input = read_bounded_json(SOURCE_INPUT_JSON, MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    envelope, _envelope_bytes = read_expected_fused_envelope()
    validate_result(result, envelope, source_input)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TSV_COLUMNS,
            delimiter="\t",
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    result = run_gate()
    write_json(args.write_json, result)
    write_tsv(args.write_tsv, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
