#!/usr/bin/env python3
"""Gate the d128 attention plus RMSNorm-MLP boundary frontier."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import pathlib
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_derived_d128_mlp_fusion_attribution_gate as attribution_gate  # noqa: E402
from scripts import zkai_attention_derived_d128_native_mlp_proof_route_gate as mlp_route_gate  # noqa: E402


EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
MAX_SOURCE_BYTES = 16 * 1024 * 1024

ACCOUNTING_PATH = EVIDENCE_DIR / "zkai-d128-attention-mlp-boundary-frontier-accounting-2026-05.json"
ATTENTION_BOUNDED_GATE_PATH = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json"
ATTENTION_FUSED_GATE_PATH = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05.json"
DERIVED_INPUT_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-input-2026-05.json"
DERIVED_CHAIN_COMPRESSION_PATH = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-statement-chain-compression-2026-05.json"
)
MLP_ROUTE_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json"
MLP_ATTRIBUTION_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.json"

JSON_OUT = EVIDENCE_DIR / "zkai-d128-attention-mlp-boundary-frontier-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-attention-mlp-boundary-frontier-2026-05.tsv"

SCHEMA = "zkai-d128-attention-mlp-boundary-frontier-gate-v1"
DECISION = "NARROW_CLAIM_ATTENTION_PLUS_DERIVED_MLP_BOUNDARY_FRONTIER_PINNED"
RESULT = "GO_TWO_PROOF_TARGET_PINNED_NO_GO_SINGLE_NATIVE_ATTENTION_MLP_OBJECT_YET"
ISSUE = "https://github.com/omarespejel/provable-transformer-vm/issues/603"
CLAIM_BOUNDARY = (
    "PINS_CURRENT_D8_ATTENTION_PROOF_PLUS_DERIVED_D128_RMSNORM_MLP_FUSED_PROOF_TARGET_"
    "WITHOUT_CLAIMING_ONE_NATIVE_BLOCK_PROOF_OR_NANOZK_COMPARABILITY"
)
PAYLOAD_DOMAIN = "ptvm:zkai:d128-attention-mlp-boundary-frontier:v1"
NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900

EXPECTED_ACCOUNTING = {
    "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json": {
        "role": "attention_bounded_softmax_table",
        "proof_backend_version": "stwo-attention-kv-d8-causal-mask-bounded-softmax-table-v1",
        "statement_version": "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-statement-v1",
        "proof_json_size_bytes": 44_692,
        "typed_size_estimate_bytes": 17_264,
    },
    "zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json": {
        "role": "attention_fused_softmax_table",
        "proof_backend_version": "stwo-attention-kv-d8-fused-bounded-softmax-table-logup-v1",
        "statement_version": "zkai-attention-kv-stwo-native-d8-fused-softmax-table-logup-statement-v1",
        "proof_json_size_bytes": 47_698,
        "typed_size_estimate_bytes": 18_124,
    },
    "zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json": {
        "role": "derived_d128_rmsnorm_mlp_fused",
        "proof_backend_version": "stwo-d128-rmsnorm-mlp-fused-air-proof-v1",
        "statement_version": "zkai-d128-rmsnorm-mlp-fused-statement-v1",
        "proof_json_size_bytes": 68_560,
        "typed_size_estimate_bytes": 22_576,
    },
}

EXPECTED_MLP = {
    "available_separate_typed_bytes": 59_344,
    "available_separate_proof_bytes": 198_937,
    "derived_fused_typed_bytes": 22_576,
    "derived_fused_proof_bytes": 68_560,
    "typed_saving_vs_available_separate_bytes": 36_768,
    "typed_ratio_vs_available_separate": 0.380426,
    "matched_six_separate_derived_baseline_status": "COMPLETE_EXACT_SIX_DERIVED_SEPARATE_ENVELOPES",
    "remaining_no_go_result": "NO-GO for attention plus MLP in one native proof object or matched external benchmark",
}

EXPECTED_ATTRIBUTION = {
    "opening_plumbing_saved_bytes": 33_280,
    "opening_plumbing_share": 0.905135,
    "compression_probe_result": "NO_GO_DROP_FRI_DECOMMITMENTS_WOULD_DROP_VERIFIER_OPENING_WITNESS",
}

EXPECTED_INPUT = {
    "source_attention_outputs_commitment": "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
    "derived_input_activation_commitment": "blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35",
    "adapter_policy_id": "fixed_public_two_source_q8_projection_v1",
    "matches_current_d128_input": False,
}

EXPECTED_HANDOFF = {
    "compressed_artifact_bytes": 2_559,
    "source_chain_artifact_bytes": 14_624,
    "byte_savings": 12_065,
    "compressed_to_source_ratio": 0.174986,
    "no_go_result": "NO-GO for proof composition, recursive aggregation, proof-size savings, timings, or production readiness",
}

NON_CLAIMS = (
    "not one native attention plus MLP proof object",
    "not a full transformer block proof",
    "not a NANOZK proof-size win",
    "not a matched NANOZK workload or benchmark",
    "not proof that the compressed handoff artifact is a proof object",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-accounting-2026-05.json",
    "python3 scripts/zkai_d128_attention_mlp_boundary_frontier_gate.py --write-json docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_d128_attention_mlp_boundary_frontier_gate.py scripts/tests/test_zkai_d128_attention_mlp_boundary_frontier_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_d128_attention_mlp_boundary_frontier_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "claim_boundary",
    "source_artifacts",
    "routes",
    "summary",
    "mechanism",
    "non_claims",
    "validation_commands",
    "route_commitment",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_result", "mutation_inventory"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = (
    "decision",
    "result",
    "attention_fused_typed_bytes",
    "derived_mlp_fused_typed_bytes",
    "two_proof_frontier_typed_bytes",
    "two_proof_frontier_json_proof_bytes",
    "six_separate_mlp_plus_attention_fused_typed_bytes",
    "typed_ratio_vs_six_separate_mlp_plus_attention_fused",
    "typed_saving_vs_six_separate_mlp_plus_attention_fused_bytes",
    "nanozk_reported_d128_block_proof_bytes",
    "typed_gap_to_nanozk_reported_bytes",
    "typed_reduction_needed_to_nanozk_reported_share",
    "compressed_handoff_artifact_bytes",
    "single_native_attention_mlp_status",
)


class AttentionMlpBoundaryFrontierError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AttentionMlpBoundaryFrontierError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def route_commitment(routes: dict[str, Any]) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(PAYLOAD_DOMAIN.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(routes))
    return "blake2b-256:" + digest.hexdigest()


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise AttentionMlpBoundaryFrontierError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionMlpBoundaryFrontierError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionMlpBoundaryFrontierError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionMlpBoundaryFrontierError(f"{label} must be integer")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AttentionMlpBoundaryFrontierError(f"{label} must be non-empty string")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionMlpBoundaryFrontierError(f"{label} must be boolean")
    return value


def load_json(path: pathlib.Path, label: str) -> Any:
    try:
        return attribution_gate.read_json(path, MAX_SOURCE_BYTES, label)
    except Exception as err:  # noqa: BLE001 - normalize imported gate errors for this gate.
        raise AttentionMlpBoundaryFrontierError(f"failed loading {label}: {err}") from err


def source_artifact(artifact_id: str, path: pathlib.Path) -> tuple[Any, dict[str, Any]]:
    payload = load_json(path, artifact_id)
    raw = canonical_json_bytes(payload)
    return (
        payload,
        {
            "id": artifact_id,
            "path": path.relative_to(ROOT).as_posix(),
            "payload_sha256": hashlib.sha256(raw).hexdigest(),
        },
    )


def accounting_rows(accounting: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if accounting.get("schema") != "zkai-stwo-local-binary-proof-accounting-cli-v1":
        raise AttentionMlpBoundaryFrontierError("accounting schema drift")
    rows = {}
    for row in _list(accounting.get("rows"), "accounting rows"):
        data = _dict(row, "accounting row")
        path = _str(data.get("evidence_relative_path"), "accounting evidence path")
        rows[path] = data
    if set(rows) != set(EXPECTED_ACCOUNTING):
        raise AttentionMlpBoundaryFrontierError("accounting row set drift")
    for path, expected in EXPECTED_ACCOUNTING.items():
        row = rows[path]
        metadata = _dict(row.get("envelope_metadata"), f"{path} metadata")
        local = _dict(row.get("local_binary_accounting"), f"{path} local accounting")
        if metadata.get("proof_backend_version") != expected["proof_backend_version"]:
            raise AttentionMlpBoundaryFrontierError(f"{path} proof backend drift")
        if metadata.get("statement_version") != expected["statement_version"]:
            raise AttentionMlpBoundaryFrontierError(f"{path} statement version drift")
        if row.get("proof_json_size_bytes") != expected["proof_json_size_bytes"]:
            raise AttentionMlpBoundaryFrontierError(f"{path} proof JSON bytes drift")
        if local.get("typed_size_estimate_bytes") != expected["typed_size_estimate_bytes"]:
            raise AttentionMlpBoundaryFrontierError(f"{path} typed bytes drift")
    return rows


def validate_sources(payloads: dict[str, Any]) -> None:
    mlp_route = _dict(payloads["mlp_route"], "MLP route")
    try:
        mlp_route_gate.validate_payload(mlp_route)
    except Exception as err:  # noqa: BLE001 - normalize imported gate errors for this gate.
        raise AttentionMlpBoundaryFrontierError(f"MLP route gate validation failed: {err}") from err
    mlp_summary = _dict(mlp_route.get("summary"), "MLP route summary")
    for key, expected in EXPECTED_MLP.items():
        if mlp_summary.get(key) != expected:
            raise AttentionMlpBoundaryFrontierError(f"MLP route summary drift: {key}")

    attribution = _dict(payloads["mlp_attribution"], "MLP attribution")
    try:
        attribution_gate.validate_payload(attribution)
    except Exception as err:  # noqa: BLE001 - normalize imported gate errors for this gate.
        raise AttentionMlpBoundaryFrontierError(f"MLP attribution validation failed: {err}") from err
    attribution_summary = _dict(attribution.get("summary"), "MLP attribution summary")
    for key, expected in EXPECTED_ATTRIBUTION.items():
        if attribution_summary.get(key) != expected:
            raise AttentionMlpBoundaryFrontierError(f"attribution summary drift: {key}")

    derived_input = _dict(payloads["derived_input"], "derived input")
    input_summary = _dict(derived_input.get("summary"), "derived input summary")
    for key, expected in EXPECTED_INPUT.items():
        if input_summary.get(key) != expected:
            raise AttentionMlpBoundaryFrontierError(f"derived input summary drift: {key}")

    handoff = _dict(payloads["chain_compression"], "chain compression")
    handoff_summary = _dict(handoff.get("summary"), "chain compression summary")
    for key, expected in EXPECTED_HANDOFF.items():
        if handoff_summary.get(key) != expected:
            raise AttentionMlpBoundaryFrontierError(f"chain compression summary drift: {key}")

    bounded_gate = _dict(payloads["attention_bounded_gate"], "bounded gate")
    bounded_receipt = _dict(bounded_gate.get("bounded_softmax_table_receipt"), "bounded receipt")
    fused_gate = _dict(payloads["attention_fused_gate"], "fused attention gate")
    if bounded_receipt.get("outputs_commitment") != input_summary["source_attention_outputs_commitment"]:
        raise AttentionMlpBoundaryFrontierError("bounded attention output commitment drift")
    if fused_gate.get("source_statement_commitment") != bounded_receipt.get("statement_commitment"):
        raise AttentionMlpBoundaryFrontierError("fused attention source statement drift")
    if fused_gate.get("source_public_instance_commitment") != bounded_receipt.get("public_instance_commitment"):
        raise AttentionMlpBoundaryFrontierError("fused attention public instance drift")


def build_context() -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    artifacts = []
    for artifact_id, path in (
        ("frontier_accounting", ACCOUNTING_PATH),
        ("attention_bounded_gate", ATTENTION_BOUNDED_GATE_PATH),
        ("attention_fused_gate", ATTENTION_FUSED_GATE_PATH),
        ("derived_input", DERIVED_INPUT_PATH),
        ("chain_compression", DERIVED_CHAIN_COMPRESSION_PATH),
        ("mlp_route", MLP_ROUTE_PATH),
        ("mlp_attribution", MLP_ATTRIBUTION_PATH),
    ):
        payload, artifact = source_artifact(artifact_id, path)
        payloads[artifact_id] = payload
        artifacts.append(artifact)

    validate_sources(payloads)
    rows = accounting_rows(_dict(payloads["frontier_accounting"], "frontier accounting"))
    return {"payloads": payloads, "source_artifacts": artifacts, "accounting_rows": rows}


def row_metrics(rows: dict[str, dict[str, Any]], path: str) -> dict[str, int]:
    row = rows[path]
    local = _dict(row.get("local_binary_accounting"), f"{path} local accounting")
    return {
        "proof_json_size_bytes": _int(row.get("proof_json_size_bytes"), f"{path} proof bytes"),
        "typed_size_estimate_bytes": _int(local.get("typed_size_estimate_bytes"), f"{path} typed bytes"),
    }


def build_routes(context: dict[str, Any]) -> dict[str, Any]:
    rows = context["accounting_rows"]
    payloads = context["payloads"]
    bounded = row_metrics(rows, "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json")
    attention_fused = row_metrics(
        rows, "zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json"
    )
    mlp_fused = row_metrics(rows, "zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json")
    mlp_summary = _dict(payloads["mlp_route"].get("summary"), "MLP route summary")
    attribution_summary = _dict(payloads["mlp_attribution"].get("summary"), "MLP attribution summary")
    input_summary = _dict(payloads["derived_input"].get("summary"), "derived input summary")
    handoff_summary = _dict(payloads["chain_compression"].get("summary"), "chain compression summary")

    attention_fused_plus_mlp_typed = attention_fused["typed_size_estimate_bytes"] + mlp_fused["typed_size_estimate_bytes"]
    attention_fused_plus_mlp_json = attention_fused["proof_json_size_bytes"] + mlp_fused["proof_json_size_bytes"]
    attention_fused_plus_six_mlp_typed = (
        attention_fused["typed_size_estimate_bytes"] + mlp_summary["available_separate_typed_bytes"]
    )
    attention_fused_plus_six_mlp_json = (
        attention_fused["proof_json_size_bytes"] + mlp_summary["available_separate_proof_bytes"]
    )
    bounded_plus_mlp_typed = bounded["typed_size_estimate_bytes"] + mlp_fused["typed_size_estimate_bytes"]
    bounded_plus_mlp_json = bounded["proof_json_size_bytes"] + mlp_fused["proof_json_size_bytes"]
    bounded_plus_six_mlp_typed = bounded["typed_size_estimate_bytes"] + mlp_summary["available_separate_typed_bytes"]
    bounded_plus_six_mlp_json = bounded["proof_json_size_bytes"] + mlp_summary["available_separate_proof_bytes"]
    nano_gap = attention_fused_plus_mlp_typed - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES
    if nano_gap <= 0:
        raise AttentionMlpBoundaryFrontierError("unexpected NANOZK gap non-positive")

    return {
        "attention_bounded_plus_derived_mlp_fused_separate_proofs": {
            "status": "GO_CURRENT_VALUE_CONNECTED_TWO_PROOF_ROUTE_WITH_BOUNDED_ATTENTION_SOURCE",
            "attention_typed_bytes": bounded["typed_size_estimate_bytes"],
            "attention_json_proof_bytes": bounded["proof_json_size_bytes"],
            "derived_mlp_fused_typed_bytes": mlp_fused["typed_size_estimate_bytes"],
            "derived_mlp_fused_json_proof_bytes": mlp_fused["proof_json_size_bytes"],
            "combined_typed_bytes": bounded_plus_mlp_typed,
            "combined_json_proof_bytes": bounded_plus_mlp_json,
            "combined_typed_ratio_vs_bounded_attention_plus_six_separate_mlp": ratio(
                bounded_plus_mlp_typed, bounded_plus_six_mlp_typed
            ),
            "combined_json_ratio_vs_bounded_attention_plus_six_separate_mlp": ratio(
                bounded_plus_mlp_json, bounded_plus_six_mlp_json
            ),
            "source_attention_outputs_commitment": input_summary["source_attention_outputs_commitment"],
            "derived_input_activation_commitment": input_summary["derived_input_activation_commitment"],
        },
        "attention_fused_softmax_table_plus_derived_mlp_fused_separate_proofs": {
            "status": "GO_CURRENT_BEST_TWO_PROOF_FRONTIER_TARGET_NOT_ONE_NATIVE_PROOF",
            "attention_fused_typed_bytes": attention_fused["typed_size_estimate_bytes"],
            "attention_fused_json_proof_bytes": attention_fused["proof_json_size_bytes"],
            "derived_mlp_fused_typed_bytes": mlp_fused["typed_size_estimate_bytes"],
            "derived_mlp_fused_json_proof_bytes": mlp_fused["proof_json_size_bytes"],
            "combined_typed_bytes": attention_fused_plus_mlp_typed,
            "combined_json_proof_bytes": attention_fused_plus_mlp_json,
            "six_separate_mlp_plus_attention_fused_typed_bytes": attention_fused_plus_six_mlp_typed,
            "six_separate_mlp_plus_attention_fused_json_proof_bytes": attention_fused_plus_six_mlp_json,
            "typed_saving_vs_six_separate_mlp_plus_attention_fused_bytes": mlp_summary[
                "typed_saving_vs_available_separate_bytes"
            ],
            "json_saving_vs_six_separate_mlp_plus_attention_fused_bytes": mlp_summary[
                "json_saving_vs_available_separate_bytes"
            ],
            "typed_ratio_vs_six_separate_mlp_plus_attention_fused": ratio(
                attention_fused_plus_mlp_typed, attention_fused_plus_six_mlp_typed
            ),
            "json_ratio_vs_six_separate_mlp_plus_attention_fused": ratio(
                attention_fused_plus_mlp_json, attention_fused_plus_six_mlp_json
            ),
            "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
            "typed_gap_to_nanozk_reported_bytes": nano_gap,
            "typed_reduction_needed_to_nanozk_reported_share": ratio(nano_gap, attention_fused_plus_mlp_typed),
        },
        "compressed_statement_handoff_plus_derived_mlp_fused": {
            "status": "GO_COMPACT_VERIFIER_FACING_HANDOFF_BUT_NO_GO_PROOF_SIZE_COMPARISON",
            "compressed_handoff_artifact_bytes": handoff_summary["compressed_artifact_bytes"],
            "source_chain_artifact_bytes": handoff_summary["source_chain_artifact_bytes"],
            "compressed_to_source_ratio": handoff_summary["compressed_to_source_ratio"],
            "compressed_handoff_plus_mlp_json_proof_payload_bytes": (
                handoff_summary["compressed_artifact_bytes"] + mlp_fused["proof_json_size_bytes"]
            ),
            "proof_size_claim_status": "NO_GO_HANDOFF_ARTIFACT_IS_NOT_A_STARK_PROOF_OBJECT",
        },
        "single_native_attention_plus_derived_mlp_fused": {
            "status": "NO_GO_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_MISSING",
            "first_blocker": "no native AIR/prover currently puts attention arithmetic, lookup membership, adapter, and derived RMSNorm-MLP in one proof object",
            "mechanism_hint": (
                "MLP-side fusion saved 36,768 typed bytes; "
                f"{attribution_summary['opening_plumbing_share']:.6f} of that saving came from shared opening plumbing"
            ),
            "next_smallest_experiment": (
                "build a native value-connected attention-to-RMSNorm adapter surface and compare one proof object "
                "against the current 40,700 typed-byte two-proof frontier target"
            ),
        },
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    data = context if context is not None else build_context()
    routes = build_routes(data)
    two_proof = routes["attention_fused_softmax_table_plus_derived_mlp_fused_separate_proofs"]
    handoff = routes["compressed_statement_handoff_plus_derived_mlp_fused"]
    summary = {
        "attention_fused_typed_bytes": two_proof["attention_fused_typed_bytes"],
        "derived_mlp_fused_typed_bytes": two_proof["derived_mlp_fused_typed_bytes"],
        "two_proof_frontier_typed_bytes": two_proof["combined_typed_bytes"],
        "two_proof_frontier_json_proof_bytes": two_proof["combined_json_proof_bytes"],
        "six_separate_mlp_plus_attention_fused_typed_bytes": two_proof[
            "six_separate_mlp_plus_attention_fused_typed_bytes"
        ],
        "typed_saving_vs_six_separate_mlp_plus_attention_fused_bytes": two_proof[
            "typed_saving_vs_six_separate_mlp_plus_attention_fused_bytes"
        ],
        "typed_ratio_vs_six_separate_mlp_plus_attention_fused": two_proof[
            "typed_ratio_vs_six_separate_mlp_plus_attention_fused"
        ],
        "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "typed_gap_to_nanozk_reported_bytes": two_proof["typed_gap_to_nanozk_reported_bytes"],
        "typed_reduction_needed_to_nanozk_reported_share": two_proof[
            "typed_reduction_needed_to_nanozk_reported_share"
        ],
        "compressed_handoff_artifact_bytes": handoff["compressed_handoff_artifact_bytes"],
        "single_native_attention_mlp_status": routes["single_native_attention_plus_derived_mlp_fused"]["status"],
    }
    mechanism = {
        "current_interesting_signal": (
            "MLP fusion still removes 36,768 typed bytes after attention is included as a separate proof object"
        ),
        "current_blocker": "the comparable frontier is still two proof objects, not one native attention plus MLP proof",
        "why_not_nanozk_win": (
            "the current two-proof frontier is 40,700 local typed bytes and the workload/object class is not matched"
        ),
        "next_attack": "native value-connected attention plus RMSNorm-MLP proof object or a deliberately typed boundary",
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(data["source_artifacts"]),
        "routes": routes,
        "summary": summary,
        "mechanism": mechanism,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "route_commitment": route_commitment(routes),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_payload(payload: Any, *, expected: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    key_set = set(data)
    if key_set not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionMlpBoundaryFrontierError(f"unexpected payload keys: {sorted(key_set ^ FINAL_KEYS)}")
    if data.get("schema") != SCHEMA:
        raise AttentionMlpBoundaryFrontierError("schema drift")
    if data.get("decision") != DECISION:
        raise AttentionMlpBoundaryFrontierError("decision drift")
    if data.get("result") != RESULT:
        raise AttentionMlpBoundaryFrontierError("result drift")
    if data.get("issue") != ISSUE:
        raise AttentionMlpBoundaryFrontierError("issue drift")
    if data.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionMlpBoundaryFrontierError("claim boundary drift")
    if data.get("non_claims") != list(NON_CLAIMS):
        raise AttentionMlpBoundaryFrontierError("non-claims drift")
    if data.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise AttentionMlpBoundaryFrontierError("validation command drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise AttentionMlpBoundaryFrontierError("payload commitment drift")

    expected_context = context if context is not None else build_context()
    expected_core = expected if expected is not None else build_core_payload(expected_context)
    if data.get("source_artifacts") != expected_context["source_artifacts"]:
        raise AttentionMlpBoundaryFrontierError("source artifact drift")
    if data.get("routes") != expected_core["routes"]:
        raise AttentionMlpBoundaryFrontierError("route drift")
    if data.get("summary") != expected_core["summary"]:
        raise AttentionMlpBoundaryFrontierError("summary drift")
    if data.get("mechanism") != expected_core["mechanism"]:
        raise AttentionMlpBoundaryFrontierError("mechanism drift")
    if data.get("route_commitment") != route_commitment(_dict(data.get("routes"), "routes")):
        raise AttentionMlpBoundaryFrontierError("route commitment drift")

    summary = _dict(data.get("summary"), "summary")
    if _int(summary.get("two_proof_frontier_typed_bytes"), "two-proof typed bytes") != 40_700:
        raise AttentionMlpBoundaryFrontierError("two-proof frontier typed bytes drift")
    if _int(summary.get("typed_gap_to_nanozk_reported_bytes"), "NANOZK gap") <= 0:
        raise AttentionMlpBoundaryFrontierError("NANOZK overclaim drift")
    if _str(summary.get("single_native_attention_mlp_status"), "single native status") != (
        "NO_GO_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_MISSING"
    ):
        raise AttentionMlpBoundaryFrontierError("single native status drift")

    routes = _dict(data.get("routes"), "routes")
    handoff = _dict(routes.get("compressed_statement_handoff_plus_derived_mlp_fused"), "handoff route")
    if handoff.get("proof_size_claim_status") != "NO_GO_HANDOFF_ARTIFACT_IS_NOT_A_STARK_PROOF_OBJECT":
        raise AttentionMlpBoundaryFrontierError("handoff proof-size overclaim")
    single = _dict(routes.get("single_native_attention_plus_derived_mlp_fused"), "single native route")
    if single.get("status") != "NO_GO_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_MISSING":
        raise AttentionMlpBoundaryFrontierError("single native route overclaim")

    if key_set == FINAL_KEYS:
        mutation_result = _dict(data.get("mutation_result"), "mutation result")
        inventory = _dict(data.get("mutation_inventory"), "mutation inventory")
        cases = _list(mutation_result.get("cases"), "mutation cases")
        if inventory.get("cases") != list(MUTATION_NAMES):
            raise AttentionMlpBoundaryFrontierError("mutation inventory drift")
        if inventory.get("case_count") != len(MUTATION_NAMES):
            raise AttentionMlpBoundaryFrontierError("mutation count drift")
        if inventory.get("all_mutations_rejected") is not True:
            raise AttentionMlpBoundaryFrontierError("mutation inventory not all rejected")
        if mutation_result.get("all_mutations_rejected") is not True:
            raise AttentionMlpBoundaryFrontierError("not all mutations rejected")
        names = []
        for index, value in enumerate(cases):
            case = _dict(value, f"mutation case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AttentionMlpBoundaryFrontierError("malformed mutation case")
            name = _str(case.get("name"), f"mutation case {index} name")
            names.append(name)
            if _bool(case.get("accepted"), f"{name} accepted") is not False:
                raise AttentionMlpBoundaryFrontierError(f"mutation accepted: {name}")
            if _bool(case.get("rejected"), f"{name} rejected") is not True:
                raise AttentionMlpBoundaryFrontierError(f"mutation not rejected: {name}")
            _str(case.get("error"), f"{name} error")
        if names != list(MUTATION_NAMES):
            raise AttentionMlpBoundaryFrontierError("mutation order drift")


MutationFn = Callable[[dict[str, Any]], None]


def _refresh_route_and_payload(payload: dict[str, Any]) -> None:
    payload["route_commitment"] = route_commitment(payload["routes"])
    refresh_payload_commitment(payload)


MUTATIONS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_promoted", lambda p: p.__setitem__("decision", "GO_ONE_NATIVE_ATTENTION_MLP_PROOF"), True),
    (
        "claim_boundary_overclaim",
        lambda p: p.__setitem__("claim_boundary", "MATCHED_NANOZK_COMPARABLE_ATTENTION_MLP_WIN"),
        True,
    ),
    (
        "two_proof_typed_bytes_reduced",
        lambda p: p["summary"].__setitem__("two_proof_frontier_typed_bytes", 6_900),
        True,
    ),
    (
        "nanozk_gap_zeroed",
        lambda p: p["summary"].__setitem__("typed_gap_to_nanozk_reported_bytes", 0),
        True,
    ),
    (
        "single_native_status_promoted",
        lambda p: p["routes"]["single_native_attention_plus_derived_mlp_fused"].__setitem__(
            "status", "GO_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_EXISTS"
        ),
        True,
    ),
    (
        "handoff_artifact_promoted_to_proof",
        lambda p: p["routes"]["compressed_statement_handoff_plus_derived_mlp_fused"].__setitem__(
            "proof_size_claim_status", "GO_HANDOFF_ARTIFACT_IS_PROOF_SIZE_COMPARABLE"
        ),
        True,
    ),
    (
        "attention_typed_bytes_drift",
        lambda p: p["routes"]["attention_fused_softmax_table_plus_derived_mlp_fused_separate_proofs"].__setitem__(
            "attention_fused_typed_bytes", 1
        ),
        True,
    ),
    (
        "source_artifact_hash_drift",
        lambda p: p["source_artifacts"][0].__setitem__("payload_sha256", "0" * 64),
        True,
    ),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", lambda p: p.__setitem__("payload_commitment", "sha256:" + "1" * 64), False),
)
MUTATION_NAMES = tuple(name for name, _, _ in MUTATIONS)


def run_mutations(core: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for name, mutator, refresh in MUTATIONS:
        mutated = copy.deepcopy(core)
        mutator(mutated)
        if refresh:
            _refresh_route_and_payload(mutated)
        try:
            validate_payload(mutated, expected=core, context=context)
        except AttentionMlpBoundaryFrontierError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return {"cases": cases, "all_mutations_rejected": all(case["rejected"] for case in cases)}


def build_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    expected_context = context if context is not None else build_context()
    core = build_core_payload(expected_context)
    mutation_result = run_mutations(core, expected_context)
    payload = copy.deepcopy(core)
    payload["mutation_result"] = mutation_result
    payload["mutation_inventory"] = {
        "case_count": len(MUTATION_NAMES),
        "all_mutations_rejected": mutation_result["all_mutations_rejected"],
        "cases": list(MUTATION_NAMES),
    }
    refresh_payload_commitment(payload)
    validate_payload(payload, context=expected_context)
    return payload


def to_tsv(payload: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    expected_context = context if context is not None else build_context()
    validate_payload(payload, context=expected_context)
    row = {column: payload["summary"].get(column, payload.get(column)) for column in TSV_COLUMNS}
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
    return handle.getvalue()


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    attribution_gate.write_bytes_atomic(path, data, "attention MLP boundary frontier JSON")


def write_tsv(path: pathlib.Path, payload: dict[str, Any], context: dict[str, Any]) -> None:
    attribution_gate.write_bytes_atomic(
        path,
        to_tsv(payload, context).encode("utf-8"),
        "attention MLP boundary frontier TSV",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args()

    context = build_context()
    payload = build_payload(context)
    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload, context)
    if not args.write_json and not args.write_tsv:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
