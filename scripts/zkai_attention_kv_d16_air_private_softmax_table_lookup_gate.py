#!/usr/bin/env python3
"""Checked AIR-constrained d16 Softmax-table lookup sidecar gate for issue #501.

This gate records the narrow positive result: the existing native d=16 bounded
Softmax-table attention proof now has a second native Stwo LogUp proof that
constrains all `(clipped score gap, table weight)` claims against the
statement-bound weight table.  It is deliberately not described as a fused
attention-arithmetic-plus-lookup component and not as exact Softmax.
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
SOURCE_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json"
LOOKUP_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json"
SOURCE_INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.tsv"

MAX_SOURCE_INPUT_JSON_BYTES = 1_048_576
MAX_LOOKUP_ENVELOPE_JSON_BYTES = 1_048_576

SCHEMA = "zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-v1"
ISSUE = 501
SOURCE_ISSUE = 501
DECISION = "GO_NATIVE_STWO_AIR_CONSTRAINED_SOFTMAX_TABLE_LOOKUP_RELATION_SIDECAR"
CLAIM_BOUNDARY = (
    "NATIVE_STWO_D16_BOUNDED_SOFTMAX_TABLE_LOOKUP_MEMBERSHIP_CONSTRAINED_BY_LOGUP_SIDECAR_"
    "NOT_FUSED_ATTENTION_LOOKUP_COMPONENT_NOT_EXACT_SOFTMAX_NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD"
)
LOOKUP_STATUS = "GO_STWO_LOGUP_TABLE_MEMBERSHIP_SIDECAR_PROOF"
FUSED_COMPONENT_STATUS = "NO_GO_FUSED_ATTENTION_ARITHMETIC_AND_LOOKUP_COMPONENT_NOT_BUILT"
NEXT_BACKEND_STEP = (
    "fuse the attention arithmetic columns and Softmax-table LogUp relation into one native component, "
    "then repeat the check on the two-head route"
)
TIMING_POLICY = "no_new_timing_proof_existence_and_relation_gate_only"
LOOKUP_VERIFY_TIMEOUT_SECONDS = 180

SOURCE_DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_D16_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
SOURCE_STATEMENT_COMMITMENT = "blake2b-256:4292fdf43f7f08a5820584e3e80ba22e6bc8a378a9811a5983799b36badda462"
SOURCE_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:bad2b16dd13bc731bace7459a4aee8c28f470de7541fa8181034552c22e1ca34"
SOURCE_SCORE_ROW_COMMITMENT = "blake2b-256:7ad8c6066d1bf36cae62d4e2da29a9b3fd04b74acd6b1e4a33e6018464cbfb66"
SOURCE_WEIGHT_TABLE_COMMITMENT = "blake2b-256:d2eb4b2f2162e4748a7eb125efb9cb499ca41698844f94eae039dfa96f45ceb5"
SOURCE_WEIGHT_POLICY = "exp2_half_gap_table_clipped_8_floor_division"
SOURCE_SCORE_GAP_CLIP = 8
SOURCE_SCORE_ROWS = 52
SOURCE_TRACE_ROWS = 64
SOURCE_TABLE_ROWS = 9

LOOKUP_PROOF_VERSION = "stwo-attention-kv-d16-softmax-table-logup-sidecar-proof-v1"
LOOKUP_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-statement-v1"
LOOKUP_SEMANTIC_SCOPE = "d16_bounded_softmax_table_membership_constrained_by_native_stwo_logup_sidecar"
LOOKUP_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-d16-softmax-table-logup-sidecar:v1"
LOOKUP_TARGET_ID = "attention-kv-d16-causal-mask-bounded-softmax-table-logup-sidecar-v1"
LOOKUP_RELATION = "AttentionKvD16SoftmaxTableLookupRelation"
LOOKUP_RELATION_WIDTH = 2
LOOKUP_PROOF_SIZE_BYTES = 13_445
LOOKUP_ENVELOPE_SIZE_BYTES = 257_041
LOOKUP_PROOF_COMMITMENTS = 4
LOOKUP_TRACE_COMMITMENTS = 3
LOOKUP_TABLE_MULTIPLICITIES = (
    {"gap": 0, "weight": 256, "multiplicity": 9},
    {"gap": 1, "weight": 181, "multiplicity": 0},
    {"gap": 2, "weight": 128, "multiplicity": 1},
    {"gap": 3, "weight": 91, "multiplicity": 0},
    {"gap": 4, "weight": 64, "multiplicity": 2},
    {"gap": 5, "weight": 45, "multiplicity": 0},
    {"gap": 6, "weight": 32, "multiplicity": 0},
    {"gap": 7, "weight": 23, "multiplicity": 0},
    {"gap": 8, "weight": 16, "multiplicity": 40},
)
EXPECTED_LOOKUP_TABLE_MULTIPLICITIES = LOOKUP_TABLE_MULTIPLICITIES

NON_CLAIMS = (
    "not a fused attention-arithmetic-plus-lookup component",
    "not exact Softmax attention",
    "not exp/div Softmax semantics",
    "not full autoregressive inference",
    "not long-context benchmark evidence",
    "not recursive verification or PCD",
    "not private witness privacy",
    "not on-chain verification evidence",
)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 test attention_kv_d16_softmax_table_lookup --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_d16_softmax_table_lookup_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_d16_softmax_table_lookup_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_d16_air_private_softmax_table_lookup_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_d16_air_private_softmax_table_lookup_gate",
    "just gate-fast",
    "just gate",
)

EXPECTED_MUTATION_NAMES = (
    "lookup_decision_relabeling",
    "lookup_status_relabeling",
    "fused_component_overclaim",
    "claim_boundary_fused_overclaim",
    "claim_boundary_exact_softmax_overclaim",
    "source_statement_commitment_relabeling",
    "source_weight_table_commitment_relabeling",
    "lookup_relation_relabeling",
    "lookup_relation_width_relabeling",
    "lookup_claim_count_metric_smuggling",
    "lookup_proof_size_metric_smuggling",
    "lookup_envelope_size_metric_smuggling",
    "table_multiplicity_drift",
    "non_claim_removed",
    "next_backend_step_removed",
    "source_input_split_brain",
    "unknown_field_injection",
    "lookup_receipt_unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = 18

TSV_COLUMNS = (
    "decision",
    "lookup_status",
    "fused_component_status",
    "lookup_claims",
    "table_rows",
    "lookup_proof_size_bytes",
    "lookup_envelope_size_bytes",
    "source_statement_commitment",
    "source_weight_table_commitment",
    "mutations_checked",
    "mutations_rejected",
)

_LOOKUP_VERIFY_CACHE: set[tuple[str, int]] = set()


class AttentionKvAirPrivateSoftmaxTableLookupGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise ImportError(f"failed to import {module_name} from {path}: {err}") from err
    return module


SOURCE_INPUT_MODULE = load_script_module(
    SOURCE_INPUT_SCRIPT, "zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input"
)


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    raw = read_bounded_bytes(path, max_bytes, label)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"failed to read {label}: {err}") from err


def read_bounded_bytes(path: pathlib.Path, max_bytes: int, label: str) -> bytes:
    expected_size = bounded_file_size(path, max_bytes, label)
    try:
        raw = path.read_bytes()
    except OSError as err:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"failed to read {label}: {err}") from err
    if len(raw) != expected_size:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(
            f"{label} read size drift: stat={expected_size}, read={len(raw)}"
        )
    return raw


def bounded_file_size(path: pathlib.Path, max_bytes: int, label: str) -> int:
    if not path.is_file():
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"{label} size drift: got {size}, max {max_bytes}")
    return size


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


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


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def parse_lookup_proof(proof_bytes: list[Any]) -> dict[str, Any]:
    if not isinstance(proof_bytes, list):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup proof must be a byte list")
    if len(proof_bytes) != LOOKUP_PROOF_SIZE_BYTES:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup proof byte length drift")
    if any(not isinstance(byte, int) or isinstance(byte, bool) or byte < 0 or byte > 255 for byte in proof_bytes):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup proof bytes must be uint8 values")
    try:
        proof_payload = json.loads(bytes(proof_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"failed to decode lookup proof payload: {err}") from err
    if set(proof_payload) != {"stark_proof"}:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup proof payload schema drift")
    stark_proof = proof_payload["stark_proof"]
    if not isinstance(stark_proof, dict):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup stark_proof must be an object")
    commitments = stark_proof.get("commitments")
    if not isinstance(commitments, list) or len(commitments) != LOOKUP_PROOF_COMMITMENTS:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup proof commitment count drift")
    return stark_proof


def verify_lookup_envelope_bytes_with_native_cli(envelope_bytes: bytes, label: str) -> None:
    """Run the real native Stwo verifier on the exact bytes parsed by the gate."""
    if len(envelope_bytes) <= 0 or len(envelope_bytes) > MAX_LOOKUP_ENVELOPE_JSON_BYTES:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(
            f"{label} size drift: got {len(envelope_bytes)}, max {MAX_LOOKUP_ENVELOPE_JSON_BYTES}"
        )
    digest = hashlib.blake2b(envelope_bytes, digest_size=32).hexdigest()
    cache_key = (digest, len(envelope_bytes))
    if cache_key in _LOOKUP_VERIFY_CACHE:
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
        "zkai_attention_kv_native_d16_softmax_table_lookup_proof",
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
            timeout=LOOKUP_VERIFY_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(
            f"native lookup verifier failed to run for {label}: {err}"
        ) from err
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        suffix = detail[-1] if detail else f"exit code {completed.returncode}"
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(
            f"native lookup verifier rejected {label}: {suffix}"
        )
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(
            f"native lookup verifier emitted malformed JSON for {label}: {err}"
        ) from err
    expected_summary = {
        "mode": "verify",
        "verified": True,
        "proof_size_bytes": LOOKUP_PROOF_SIZE_BYTES,
        "envelope_size_bytes": len(envelope_bytes),
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise AttentionKvAirPrivateSoftmaxTableLookupGateError(
                f"native lookup verifier summary drift for {key}: got {summary.get(key)!r}"
            )
    _LOOKUP_VERIFY_CACHE.add(cache_key)


def verify_lookup_envelope_with_native_cli(path: pathlib.Path) -> None:
    raw = read_bounded_bytes(path, MAX_LOOKUP_ENVELOPE_JSON_BYTES, "lookup sidecar envelope")
    verify_lookup_envelope_bytes_with_native_cli(raw, str(path))


def validate_source_input(source_input: Any) -> None:
    if not isinstance(source_input, dict):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("source input must be an object")
    if source_input.get("decision") != SOURCE_DECISION:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("source decision drift")
    try:
        SOURCE_INPUT_MODULE.validate_payload(source_input)
    except Exception as err:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"source input validation drift: {err}") from err
    expected_scalars = {
        "statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "weight_policy": SOURCE_WEIGHT_POLICY,
        "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
        "score_row_count": SOURCE_SCORE_ROWS,
        "trace_row_count": SOURCE_TRACE_ROWS,
    }
    for key, expected in expected_scalars.items():
        if source_input.get(key) != expected:
            raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"source {key} drift")


def validate_lookup_envelope(envelope: Any, source_input: dict[str, Any], envelope_size_bytes: int) -> dict[str, Any]:
    validate_source_input(source_input)
    if not isinstance(envelope, dict):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup envelope must be an object")
    allowed = {
        "proof_backend",
        "proof_backend_version",
        "statement_version",
        "semantic_scope",
        "decision",
        "verifier_domain",
        "lookup_summary",
        "source_input",
        "proof",
    }
    if set(envelope) != allowed:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup envelope schema drift")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup proof backend drift")
    expected_scalars = {
        "proof_backend_version": LOOKUP_PROOF_VERSION,
        "statement_version": LOOKUP_STATEMENT_VERSION,
        "semantic_scope": LOOKUP_SEMANTIC_SCOPE,
        "decision": DECISION,
        "verifier_domain": LOOKUP_VERIFIER_DOMAIN,
    }
    for key, expected in expected_scalars.items():
        if envelope.get(key) != expected:
            raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"{key} drift")
    if not type_strict_equal(envelope.get("source_input"), source_input):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup envelope source input split-brain drift")
    summary = envelope.get("lookup_summary")
    if not isinstance(summary, dict):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup summary must be an object")
    expected_summary = {
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "source_public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "source_score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "score_rows": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
        "weight_policy": SOURCE_WEIGHT_POLICY,
        "lookup_relation": LOOKUP_RELATION,
        "lookup_relation_width": LOOKUP_RELATION_WIDTH,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "table_multiplicities": list(EXPECTED_LOOKUP_TABLE_MULTIPLICITIES),
    }
    if not type_strict_equal(summary, expected_summary):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup summary drift")
    stark_proof = parse_lookup_proof(envelope["proof"])
    return {
        "proof_backend": envelope["proof_backend"],
        "proof_version": envelope["proof_backend_version"],
        "statement_version": envelope["statement_version"],
        "semantic_scope": envelope["semantic_scope"],
        "verifier_domain": envelope["verifier_domain"],
        "target_id": LOOKUP_TARGET_ID,
        "source_statement_commitment": summary["source_statement_commitment"],
        "source_public_instance_commitment": summary["source_public_instance_commitment"],
        "source_score_row_commitment": summary["source_score_row_commitment"],
        "source_weight_table_commitment": summary["source_weight_table_commitment"],
        "source_weight_policy": summary["weight_policy"],
        "score_rows": summary["score_rows"],
        "trace_rows": summary["trace_rows"],
        "lookup_claims": summary["lookup_claims"],
        "table_rows": summary["table_rows"],
        "score_gap_clip": summary["score_gap_clip"],
        "lookup_relation": summary["lookup_relation"],
        "lookup_relation_width": summary["lookup_relation_width"],
        "lookup_trace_commitments": LOOKUP_TRACE_COMMITMENTS,
        "lookup_proof_commitments": len(stark_proof["commitments"]),
        "table_multiplicities": summary["table_multiplicities"],
        "lookup_proof_size_bytes": len(envelope["proof"]),
        "lookup_envelope_size_bytes": envelope_size_bytes,
    }


def build_payload() -> dict[str, Any]:
    source_input = read_bounded_json(SOURCE_INPUT_JSON, MAX_SOURCE_INPUT_JSON_BYTES, "source bounded Softmax-table input")
    validate_source_input(source_input)
    envelope_raw = read_bounded_bytes(LOOKUP_ENVELOPE_JSON, MAX_LOOKUP_ENVELOPE_JSON_BYTES, "lookup sidecar envelope")
    envelope_size_bytes = len(envelope_raw)
    if envelope_size_bytes != LOOKUP_ENVELOPE_SIZE_BYTES:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup envelope size drift")
    try:
        envelope = json.loads(envelope_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"failed to read lookup sidecar envelope: {err}") from err
    receipt = validate_lookup_envelope(envelope, source_input, envelope_size_bytes)
    verify_lookup_envelope_bytes_with_native_cli(envelope_raw, str(LOOKUP_ENVELOPE_JSON))
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "lookup_status": LOOKUP_STATUS,
        "fused_component_status": FUSED_COMPONENT_STATUS,
        "next_backend_step": NEXT_BACKEND_STEP,
        "timing_policy": TIMING_POLICY,
        "lookup_receipt": receipt,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["gate_commitment"] = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "lookup_status": payload["lookup_status"],
            "fused_component_status": payload["fused_component_status"],
            "source_statement_commitment": receipt["source_statement_commitment"],
            "source_weight_table_commitment": receipt["source_weight_table_commitment"],
            "lookup_proof_size_bytes": receipt["lookup_proof_size_bytes"],
        },
        "ptvm:zkai:attention-kv-d16-softmax-table-logup-sidecar-gate:v1",
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
    receipt = mutated["lookup_receipt"]
    if name == "lookup_decision_relabeling":
        mutated["decision"] = "GO_FUSED_LOOKUP"
    elif name == "lookup_status_relabeling":
        mutated["lookup_status"] = "NO_GO"
    elif name == "fused_component_overclaim":
        mutated["fused_component_status"] = "GO_FUSED_ATTENTION_AND_LOOKUP_COMPONENT"
    elif name == "claim_boundary_fused_overclaim":
        mutated["claim_boundary"] = mutated["claim_boundary"].replace("NOT_FUSED_ATTENTION_LOOKUP_COMPONENT_", "")
    elif name == "claim_boundary_exact_softmax_overclaim":
        mutated["claim_boundary"] = mutated["claim_boundary"].replace("NOT_EXACT_SOFTMAX_", "")
    elif name == "source_statement_commitment_relabeling":
        receipt["source_statement_commitment"] = "blake2b-256:" + "11" * 32
    elif name == "source_weight_table_commitment_relabeling":
        receipt["source_weight_table_commitment"] = "blake2b-256:" + "22" * 32
    elif name == "lookup_relation_relabeling":
        receipt["lookup_relation"] = "ForgedRelation"
    elif name == "lookup_relation_width_relabeling":
        receipt["lookup_relation_width"] = 3
    elif name == "lookup_claim_count_metric_smuggling":
        receipt["lookup_claims"] += 1
    elif name == "lookup_proof_size_metric_smuggling":
        receipt["lookup_proof_size_bytes"] += 1
    elif name == "lookup_envelope_size_metric_smuggling":
        receipt["lookup_envelope_size_bytes"] += 1
    elif name == "table_multiplicity_drift":
        receipt["table_multiplicities"][0]["multiplicity"] += 1
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][1:]
    elif name == "next_backend_step_removed":
        mutated["next_backend_step"] = ""
    elif name == "source_input_split_brain":
        receipt["source_score_row_commitment"] = "blake2b-256:" + "33" * 32
    elif name == "unknown_field_injection":
        mutated["unexpected"] = True
    elif name == "lookup_receipt_unknown_field_injection":
        receipt["unexpected"] = True
    else:
        raise AssertionError(f"unknown mutation: {name}")
    return mutated


def mutation_cases_for(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_mutation_spec()
    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvAirPrivateSoftmaxTableLookupGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "accepted mutation"})
    return cases


def validate_mutation_spec() -> None:
    if len(EXPECTED_MUTATION_NAMES) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("mutation spec count drift")


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("payload must be an object")
    allowed = {
        "schema",
        "issue",
        "source_issue",
        "decision",
        "claim_boundary",
        "lookup_status",
        "fused_component_status",
        "next_backend_step",
        "timing_policy",
        "lookup_receipt",
        "non_claims",
        "validation_commands",
        "gate_commitment",
        "mutation_cases",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
    }
    if not allow_missing_mutation_summary:
        expected_keys = allowed
    else:
        expected_keys = allowed - {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if set(payload) != expected_keys:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("payload field set mismatch")
    expected_scalars = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "lookup_status": LOOKUP_STATUS,
        "fused_component_status": FUSED_COMPONENT_STATUS,
        "next_backend_step": NEXT_BACKEND_STEP,
        "timing_policy": TIMING_POLICY,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            raise AttentionKvAirPrivateSoftmaxTableLookupGateError(f"{key} drift")
    receipt = payload.get("lookup_receipt")
    if not isinstance(receipt, dict):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup_receipt must be an object")
    expected_receipt = {
        "proof_backend": "stwo",
        "proof_version": LOOKUP_PROOF_VERSION,
        "statement_version": LOOKUP_STATEMENT_VERSION,
        "semantic_scope": LOOKUP_SEMANTIC_SCOPE,
        "verifier_domain": LOOKUP_VERIFIER_DOMAIN,
        "target_id": LOOKUP_TARGET_ID,
        "source_statement_commitment": SOURCE_STATEMENT_COMMITMENT,
        "source_public_instance_commitment": SOURCE_PUBLIC_INSTANCE_COMMITMENT,
        "source_score_row_commitment": SOURCE_SCORE_ROW_COMMITMENT,
        "source_weight_table_commitment": SOURCE_WEIGHT_TABLE_COMMITMENT,
        "source_weight_policy": SOURCE_WEIGHT_POLICY,
        "score_rows": SOURCE_SCORE_ROWS,
        "trace_rows": SOURCE_TRACE_ROWS,
        "lookup_claims": SOURCE_SCORE_ROWS,
        "table_rows": SOURCE_TABLE_ROWS,
        "score_gap_clip": SOURCE_SCORE_GAP_CLIP,
        "lookup_relation": LOOKUP_RELATION,
        "lookup_relation_width": LOOKUP_RELATION_WIDTH,
        "lookup_trace_commitments": LOOKUP_TRACE_COMMITMENTS,
        "lookup_proof_commitments": LOOKUP_PROOF_COMMITMENTS,
        "table_multiplicities": list(EXPECTED_LOOKUP_TABLE_MULTIPLICITIES),
        "lookup_proof_size_bytes": LOOKUP_PROOF_SIZE_BYTES,
        "lookup_envelope_size_bytes": LOOKUP_ENVELOPE_SIZE_BYTES,
    }
    if not type_strict_equal(receipt, expected_receipt):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("lookup_receipt drift")
    expected_gate_commitment = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "lookup_status": payload["lookup_status"],
            "fused_component_status": payload["fused_component_status"],
            "source_statement_commitment": receipt["source_statement_commitment"],
            "source_weight_table_commitment": receipt["source_weight_table_commitment"],
            "lookup_proof_size_bytes": receipt["lookup_proof_size_bytes"],
        },
        "ptvm:zkai:attention-kv-d16-softmax-table-logup-sidecar-gate:v1",
    )
    if payload.get("gate_commitment") != expected_gate_commitment:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("gate_commitment drift")
    if allow_missing_mutation_summary and "mutation_cases" not in payload:
        return
    cases = payload.get("mutation_cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("mutation case count drift")
    if [case.get("name") for case in cases] != list(EXPECTED_MUTATION_NAMES):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("mutation case name drift")
    if any(set(case) != {"name", "rejected", "error"} for case in cases):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("mutation case schema drift")
    rejected = sum(1 for case in cases if case.get("rejected") is True)
    if payload.get("mutations_checked") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("mutations_checked drift")
    if payload.get("mutations_rejected") != rejected or rejected != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("mutation rejection drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvAirPrivateSoftmaxTableLookupGateError("all_mutations_rejected drift")


def to_tsv(payload: dict[str, Any]) -> str:
    receipt = payload["lookup_receipt"]
    row = {
        "decision": payload["decision"],
        "lookup_status": payload["lookup_status"],
        "fused_component_status": payload["fused_component_status"],
        "lookup_claims": receipt["lookup_claims"],
        "table_rows": receipt["table_rows"],
        "lookup_proof_size_bytes": receipt["lookup_proof_size_bytes"],
        "lookup_envelope_size_bytes": receipt["lookup_envelope_size_bytes"],
        "source_statement_commitment": receipt["source_statement_commitment"],
        "source_weight_table_commitment": receipt["source_weight_table_commitment"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
    }
    out = []
    out.append("\t".join(TSV_COLUMNS))
    out.append("\t".join(str(row[column]) for column in TSV_COLUMNS))
    return "\n".join(out) + "\n"


def write_json(payload: dict[str, Any], path: pathlib.Path) -> None:
    validate_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(payload: dict[str, Any], path: pathlib.Path) -> None:
    validate_payload(payload)
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
    print(
        json.dumps(
            {
                "decision": payload["decision"],
                "lookup_claims": payload["lookup_receipt"]["lookup_claims"],
                "lookup_proof_size_bytes": payload["lookup_receipt"]["lookup_proof_size_bytes"],
                "mutations_checked": payload["mutations_checked"],
                "mutations_rejected": payload["mutations_rejected"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
