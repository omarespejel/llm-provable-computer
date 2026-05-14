#!/usr/bin/env python3
"""Classify the native d128 block proof-object route without overclaiming."""

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

from scripts import zkai_attention_derived_d128_statement_chain_compression_gate as COMPRESSION  # noqa: E402
from scripts import zkai_one_transformer_block_surface_gate as SURFACE  # noqa: E402


EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

FULL_BLOCK_ACCUMULATOR = EVIDENCE_DIR / "zkai-d128-full-block-accumulator-backend-2026-05.json"
TWO_SLICE_OUTER_SPIKE = EVIDENCE_DIR / "zkai-d128-two-slice-outer-proof-object-spike-2026-05.json"
ATTENTION_DERIVED_OUTER_ROUTE = EVIDENCE_DIR / "zkai-attention-derived-d128-outer-proof-route-2026-05.json"
PACKAGE_ACCOUNTING = EVIDENCE_DIR / "zkai-one-block-executable-package-accounting-2026-05.json"
D128_GAP_ACCOUNTING = EVIDENCE_DIR / "zkai-d128-native-block-gap-accounting-2026-05.json"
MATCHED_D64_D128_TABLE = EVIDENCE_DIR / "zkai-matched-d64-d128-evidence-table-2026-05.json"

JSON_OUT = EVIDENCE_DIR / "zkai-native-d128-block-proof-object-route-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-d128-block-proof-object-route-2026-05.tsv"

NATIVE_PROOF_OBJECT_STATUS = "NO_GO_EXECUTABLE_NATIVE_D128_BLOCK_OUTER_PROOF_BACKEND_MISSING"
FULL_ACCUMULATOR_STATUS = "GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR_NOT_OUTER_PROOF"
TWO_SLICE_STATUS = "NO_GO_EXECUTABLE_TWO_SLICE_OUTER_PROOF_OBJECT_MISSING"
ATTENTION_INPUT_STATUS = "GO_ATTENTION_DERIVED_D128_OUTER_PROOF_INPUT_CONTRACT_NOT_OUTER_PROOF"
PACKAGE_STATUS = "GO_COMPACT_VERIFIER_FACING_PACKAGE_NOT_NATIVE_PROOF"
SCHEMA = "zkai-native-d128-block-proof-object-route-v1"
DECISION = NATIVE_PROOF_OBJECT_STATUS
RESULT = "BOUNDED_NO_GO_WITH_STRONG_NEXT_BACKEND_TARGET"
ISSUE = 387
CLAIM_BOUNDARY = (
    "D128_NATIVE_BLOCK_PROOF_OBJECT_ROUTE_ONLY_NOT_PROOF_SIZE_WIN_"
    "NOT_MATCHED_NANOZK_BENCHMARK_NOT_RECURSION_NOT_TIMING"
)

EXPECTED_D128_ROWS = 197_504
EXPECTED_ATTENTION_CHAIN_ROWS = 199_553
EXPECTED_ATTENTION_CHAIN_EXTRA_ROWS = 2_049
EXPECTED_TWO_SLICE_ROWS = 256
EXPECTED_PACKAGE_WITHOUT_VK_BYTES = 4_752
EXPECTED_PACKAGE_WITH_VK_BYTES = 10_608
EXPECTED_NANOZK_BYTES = 6_900
EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK = 0.688696
EXPECTED_PACKAGE_WITH_VK_VS_NANOZK = 1.537391
EXPECTED_COMPRESSED_CHAIN_BYTES = 2_559
EXPECTED_SOURCE_CHAIN_BYTES = 14_624
EXPECTED_COMPRESSED_CHAIN_RATIO = 0.174986

FIRST_BLOCKER_CATEGORY = "no parameterized AIR route for the d128 vector-block surface"
FIRST_BLOCKER = (
    f"allowed blocker category: {FIRST_BLOCKER_CATEGORY}; the repository still has no executable native outer "
    "proof backend that proves the d128 slice-verifier checks and binds the block proof-object public inputs; "
    "the two-slice target is already NO-GO, so the six-slice d128 block cannot be claimed as one native proof object"
)

NEXT_MINIMAL_EXPERIMENT = (
    "implement the smallest native two-slice outer proof backend over rmsnorm_public_rows and "
    "rmsnorm_projection_bridge verifier checks, with public-input binding and relabeling rejection, "
    "before trying the full six-slice d128 block"
)

GO_GATE = (
    "one executable native proof object verifies locally, binds block statement, slice statements, source hashes, "
    "and native proof-object public inputs, rejects relabeling mutations, and emits proof bytes from that object"
)

NO_GO_GATE = (
    "no executable native outer backend exists, the two-slice target cannot be proven, or any compact package "
    "row must be classified as an external statement package rather than a native d128 block proof object"
)

NON_CLAIMS = [
    "not a native d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched benchmark against NANOZK, Jolt Atlas, EZKL, DeepProve-1, RISC Zero, or Obelyzk",
    "not verifier-time or prover-time evidence",
    "not recursive aggregation or proof-carrying data",
    "not verification of the six Stwo slice proofs inside the external Groth16 receipt",
    "not full transformer inference",
    "not exact real-valued Softmax, LayerNorm, or GELU",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_native_d128_block_proof_object_route_gate.py --write-json docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_d128_block_proof_object_route_gate.py scripts/tests/test_zkai_native_d128_block_proof_object_route_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_d128_block_proof_object_route_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "row_id",
    "surface",
    "status",
    "object_class",
    "rows",
    "bytes",
    "ratio_vs_nanozk_reported",
    "can_support_native_claim",
    "claim_boundary",
)

MUTATION_NAMES = (
    "full_accumulator_promoted_to_native_proof",
    "two_slice_no_go_changed_to_go",
    "attention_input_contract_promoted_to_proof",
    "package_without_vk_promoted_to_proof_size",
    "native_proof_bytes_smuggled",
    "matched_nanozk_claim_enabled",
    "first_blocker_removed",
    "next_minimal_experiment_weakened",
    "non_claim_removed",
    "source_artifact_hash_drift",
    "route_row_removed",
    "result_changed_to_go",
    "validation_command_drift",
)


class NativeD128BlockProofObjectRouteError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise NativeD128BlockProofObjectRouteError(f"invalid JSON value: {err}") from err


def pretty_json(value: dict[str, Any]) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise NativeD128BlockProofObjectRouteError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _reject_duplicate_json_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in items:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def _dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NativeD128BlockProofObjectRouteError(f"{field} must be object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise NativeD128BlockProofObjectRouteError(f"{field} must be list")
    return value


def _int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise NativeD128BlockProofObjectRouteError(f"{field} must be integer")
    return value


def _num_or_none(value: Any, field: str) -> int | float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise NativeD128BlockProofObjectRouteError(f"{field} must be numeric or null")
    return value


def _str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeD128BlockProofObjectRouteError(f"{field} must be non-empty string")
    return value


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = SURFACE.read_source_bytes(path, str(path.relative_to(ROOT)))
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except Exception as err:
        raise NativeD128BlockProofObjectRouteError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise NativeD128BlockProofObjectRouteError(f"source evidence must be object: {path}")
    return payload, raw


def source_descriptor(path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        "schema": payload.get("schema"),
        "decision": payload.get("decision"),
        "result": payload.get("result"),
    }


def checked_sources() -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for key, path in (
        ("full_block_accumulator", FULL_BLOCK_ACCUMULATOR),
        ("two_slice_outer_spike", TWO_SLICE_OUTER_SPIKE),
        ("attention_derived_outer_route", ATTENTION_DERIVED_OUTER_ROUTE),
        ("package_accounting", PACKAGE_ACCOUNTING),
        ("d128_gap_accounting", D128_GAP_ACCOUNTING),
        ("matched_d64_d128_table", MATCHED_D64_D128_TABLE),
    ):
        payload, raw = load_json(path)
        loaded[key] = {
            "payload": payload,
            "raw": raw,
            "descriptor": source_descriptor(path, payload, raw),
        }
    validate_sources(loaded)
    return loaded


def validate_sources(sources: dict[str, dict[str, Any]]) -> None:
    full = _dict(sources["full_block_accumulator"]["payload"], "full accumulator")
    full_summary = _dict(full.get("summary"), "full accumulator summary")
    if full.get("decision") != "GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR_BACKEND":
        raise NativeD128BlockProofObjectRouteError("full accumulator decision drift")
    if full.get("accumulator_result") != "GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR":
        raise NativeD128BlockProofObjectRouteError("full accumulator result drift")
    if full.get("recursive_or_pcd_result") != "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING":
        raise NativeD128BlockProofObjectRouteError("full accumulator recursive status drift")
    if _int(full_summary.get("total_checked_rows"), "full accumulator rows") != EXPECTED_D128_ROWS:
        raise NativeD128BlockProofObjectRouteError("full accumulator row drift")
    if full.get("all_mutations_rejected") is not True or _int(full.get("case_count"), "full case_count") != 52:
        raise NativeD128BlockProofObjectRouteError("full accumulator mutation drift")

    two = _dict(sources["two_slice_outer_spike"]["payload"], "two-slice outer spike")
    two_summary = _dict(two.get("summary"), "two-slice summary")
    if two.get("decision") != "NO_GO_D128_TWO_SLICE_OUTER_PROOF_OBJECT_MISSING":
        raise NativeD128BlockProofObjectRouteError("two-slice outer decision drift")
    if two.get("outer_proof_object_result") != TWO_SLICE_STATUS:
        raise NativeD128BlockProofObjectRouteError("two-slice outer result drift")
    if _int(two_summary.get("selected_checked_rows"), "two-slice selected rows") != EXPECTED_TWO_SLICE_ROWS:
        raise NativeD128BlockProofObjectRouteError("two-slice row drift")
    if two.get("all_mutations_rejected") is not True or _int(two.get("case_count"), "two-slice case_count") != 40:
        raise NativeD128BlockProofObjectRouteError("two-slice mutation drift")

    outer = _dict(sources["attention_derived_outer_route"]["payload"], "attention outer route")
    outer_summary = _dict(outer.get("summary"), "attention outer summary")
    if outer.get("decision") != "NO_GO_ATTENTION_DERIVED_D128_OUTER_PROOF_OBJECT_MISSING":
        raise NativeD128BlockProofObjectRouteError("attention outer route decision drift")
    if outer_summary.get("input_contract_status") != "GO_ATTENTION_DERIVED_D128_OUTER_PROOF_INPUT_CONTRACT":
        raise NativeD128BlockProofObjectRouteError("attention input-contract status drift")
    if outer_summary.get("outer_proof_status") != "NO_GO_EXECUTABLE_ATTENTION_DERIVED_D128_OUTER_PROOF_BACKEND_MISSING":
        raise NativeD128BlockProofObjectRouteError("attention outer-proof status drift")
    if _int(outer_summary.get("source_relation_rows"), "attention rows") != EXPECTED_ATTENTION_CHAIN_ROWS:
        raise NativeD128BlockProofObjectRouteError("attention source row drift")
    if _int(outer_summary.get("compressed_artifact_bytes"), "compressed bytes") != EXPECTED_COMPRESSED_CHAIN_BYTES:
        raise NativeD128BlockProofObjectRouteError("attention compressed byte drift")
    if outer.get("all_mutations_rejected") is not True or _int(outer.get("case_count"), "attention case_count") != 28:
        raise NativeD128BlockProofObjectRouteError("attention outer mutation drift")

    package = _dict(sources["package_accounting"]["payload"], "package accounting")
    package_summary = _dict(package.get("summary"), "package summary")
    if package.get("decision") != "GO_ONE_BLOCK_EXECUTABLE_PACKAGE_ACCOUNTING_NO_GO_NATIVE_PROOF_SIZE":
        raise NativeD128BlockProofObjectRouteError("package decision drift")
    if _int(package_summary.get("package_without_vk_bytes"), "package without VK") != EXPECTED_PACKAGE_WITHOUT_VK_BYTES:
        raise NativeD128BlockProofObjectRouteError("package without VK drift")
    if _int(package_summary.get("package_with_vk_bytes"), "package with VK") != EXPECTED_PACKAGE_WITH_VK_BYTES:
        raise NativeD128BlockProofObjectRouteError("package with VK drift")
    if package.get("all_mutations_rejected") is not True or _int(package.get("case_count"), "package case_count") != 12:
        raise NativeD128BlockProofObjectRouteError("package mutation drift")

    gap = _dict(sources["d128_gap_accounting"]["payload"], "gap accounting")
    gap_summary = _dict(gap.get("summary"), "gap summary")
    if gap.get("result") != "GO_INTERESTING_PACKAGE_SIGNAL_NO_GO_NANOZK_SIZE_WIN":
        raise NativeD128BlockProofObjectRouteError("gap result drift")
    if gap_summary.get("native_d128_block_proof_bytes") is not None:
        raise NativeD128BlockProofObjectRouteError("native d128 proof unexpectedly present")
    if gap_summary.get("matched_benchmark_claim_allowed") is not False:
        raise NativeD128BlockProofObjectRouteError("matched benchmark guard drift")
    if _int(gap_summary.get("nanozk_reported_block_proof_bytes_decimal"), "NANOZK bytes") != EXPECTED_NANOZK_BYTES:
        raise NativeD128BlockProofObjectRouteError("NANOZK byte drift")
    if gap.get("all_mutations_rejected") is not True:
        raise NativeD128BlockProofObjectRouteError("gap mutation drift")

    matched = _dict(sources["matched_d64_d128_table"]["payload"], "matched table")
    matched_summary = _dict(matched.get("summary"), "matched table summary")
    if matched.get("result") != "GO_OBJECT_CLASS_SEPARATION_NO_GO_MATCHED_BENCHMARK":
        raise NativeD128BlockProofObjectRouteError("matched table result drift")
    if matched_summary.get("native_d128_block_proof_bytes") is not None:
        raise NativeD128BlockProofObjectRouteError("matched table native proof drift")
    if matched.get("claim_guard", {}).get("matched_benchmark_claim_allowed") is not False:
        raise NativeD128BlockProofObjectRouteError("matched table benchmark guard drift")
    if matched.get("all_mutations_rejected") is not True:
        raise NativeD128BlockProofObjectRouteError("matched table mutation drift")


def route_rows(sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    full_summary = sources["full_block_accumulator"]["payload"]["summary"]
    two_summary = sources["two_slice_outer_spike"]["payload"]["summary"]
    outer_summary = sources["attention_derived_outer_route"]["payload"]["summary"]
    package_summary = sources["package_accounting"]["payload"]["summary"]
    gap_summary = sources["d128_gap_accounting"]["payload"]["summary"]
    return [
        {
            "row_id": "full_d128_verifier_accumulator",
            "surface": "six-slice d128 verifier-facing accumulator",
            "status": FULL_ACCUMULATOR_STATUS,
            "object_class": "non_recursive_verifier_accumulator",
            "rows": full_summary["total_checked_rows"],
            "bytes": None,
            "ratio_vs_nanozk_reported": None,
            "can_support_native_claim": False,
            "claim_boundary": "binds receipts and public inputs; does not prove slice verifiers inside an outer proof",
        },
        {
            "row_id": "two_slice_outer_proof_target",
            "surface": "smallest d128 two-slice outer proof target",
            "status": TWO_SLICE_STATUS,
            "object_class": "missing_native_outer_proof_object",
            "rows": two_summary["selected_checked_rows"],
            "bytes": None,
            "ratio_vs_nanozk_reported": None,
            "can_support_native_claim": False,
            "claim_boundary": "the smaller two-slice target is already blocked before proof metrics",
        },
        {
            "row_id": "attention_derived_outer_input_contract",
            "surface": "attention-derived d128 compressed outer-proof input contract",
            "status": ATTENTION_INPUT_STATUS,
            "object_class": "checked_input_contract_not_proof",
            "rows": outer_summary["source_relation_rows"],
            "bytes": outer_summary["compressed_artifact_bytes"],
            "ratio_vs_nanozk_reported": round(outer_summary["compressed_artifact_bytes"] / EXPECTED_NANOZK_BYTES, 6),
            "can_support_native_claim": False,
            "claim_boundary": "compressed transcript and input contract; not proof-size evidence",
        },
        {
            "row_id": "external_package_without_vk",
            "surface": "external verifier-facing package without reusable VK",
            "status": PACKAGE_STATUS,
            "object_class": "external_statement_package_not_native_proof",
            "rows": None,
            "bytes": package_summary["package_without_vk_bytes"],
            "ratio_vs_nanozk_reported": EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK,
            "can_support_native_claim": False,
            "claim_boundary": "compact package signal only; object class differs from NANOZK block proof row",
        },
        {
            "row_id": "native_d128_block_proof_object",
            "surface": "single native or matched d128 transformer-block proof object",
            "status": NATIVE_PROOF_OBJECT_STATUS,
            "object_class": "missing_required_native_proof_object",
            "rows": None,
            "bytes": gap_summary["native_d128_block_proof_bytes"],
            "ratio_vs_nanozk_reported": None,
            "can_support_native_claim": False,
            "claim_boundary": "required before native proof-size, timing, or matched NANOZK claims",
        },
        {
            "row_id": "external_nanozk_context",
            "surface": "NANOZK paper-reported transformer block proof row",
            "status": "SOURCE_BACKED_EXTERNAL_CONTEXT_NOT_LOCALLY_REPRODUCED",
            "object_class": "paper_reported_external_proof_row",
            "rows": None,
            "bytes": EXPECTED_NANOZK_BYTES,
            "ratio_vs_nanozk_reported": 1.0,
            "can_support_native_claim": False,
            "claim_boundary": "external context row only; not reproduced locally and not matched workload evidence",
        },
    ]


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["row_id"]: row for row in rows}
    required = {
        "full_d128_verifier_accumulator",
        "two_slice_outer_proof_target",
        "attention_derived_outer_input_contract",
        "external_package_without_vk",
        "native_d128_block_proof_object",
        "external_nanozk_context",
    }
    if set(by_id) != required:
        raise NativeD128BlockProofObjectRouteError("route row inventory drift")
    return {
        "native_block_proof_object_status": NATIVE_PROOF_OBJECT_STATUS,
        "matched_nanozk_claim_allowed": False,
        "native_proof_size_claim_allowed": False,
        "package_bytes_are_proof_bytes": False,
        "d128_checked_rows": EXPECTED_D128_ROWS,
        "attention_derived_statement_chain_rows": EXPECTED_ATTENTION_CHAIN_ROWS,
        "attention_derived_statement_chain_extra_rows_vs_d128_receipt": EXPECTED_ATTENTION_CHAIN_EXTRA_ROWS,
        "two_slice_outer_target_rows": EXPECTED_TWO_SLICE_ROWS,
        "source_statement_chain_bytes": EXPECTED_SOURCE_CHAIN_BYTES,
        "compressed_statement_chain_bytes": EXPECTED_COMPRESSED_CHAIN_BYTES,
        "compressed_statement_chain_ratio": EXPECTED_COMPRESSED_CHAIN_RATIO,
        "package_without_vk_bytes": EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
        "package_without_vk_vs_nanozk_reported_ratio": EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK,
        "package_with_vk_bytes": EXPECTED_PACKAGE_WITH_VK_BYTES,
        "package_with_vk_vs_nanozk_reported_ratio": EXPECTED_PACKAGE_WITH_VK_VS_NANOZK,
        "nanozk_reported_block_proof_bytes_decimal": EXPECTED_NANOZK_BYTES,
        "strongest_positive_signal": (
            "the full d128 verifier accumulator binds 197,504 checked rows and the external package "
            "without VK is 4,752 bytes, but neither is a native proof object"
        ),
        "first_blocker": FIRST_BLOCKER,
        "next_minimal_experiment": NEXT_MINIMAL_EXPERIMENT,
        "go_gate": GO_GATE,
        "no_go_gate": NO_GO_GATE,
    }


def source_descriptor_map(sources: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        source["descriptor"]["path"]: source["descriptor"]
        for source in sources.values()
    }


def build_core_payload() -> dict[str, Any]:
    sources = checked_sources()
    expected_sources = source_descriptor_map(sources)
    rows = route_rows(sources)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": [sources[key]["descriptor"] for key in sorted(sources)],
        "route_rows": rows,
        "claim_guard": {
            "matched_nanozk_claim_allowed": False,
            "native_proof_size_claim_allowed": False,
            "package_bytes_are_proof_bytes": False,
            "native_d128_block_proof_object_exists": False,
        },
        "summary": build_summary(rows),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_core_payload(payload, expected_sources=expected_sources)
    return payload


def validate_core_payload(
    payload: dict[str, Any],
    *,
    expected_sources: dict[str, dict[str, Any]] | None = None,
) -> None:
    if payload.get("schema") != SCHEMA:
        raise NativeD128BlockProofObjectRouteError("schema drift")
    if payload.get("decision") != DECISION:
        raise NativeD128BlockProofObjectRouteError("decision drift")
    if payload.get("result") != RESULT:
        raise NativeD128BlockProofObjectRouteError("result drift")
    if payload.get("issue") != ISSUE:
        raise NativeD128BlockProofObjectRouteError("issue drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise NativeD128BlockProofObjectRouteError("claim boundary drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise NativeD128BlockProofObjectRouteError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise NativeD128BlockProofObjectRouteError("validation command drift")
    guard = _dict(payload.get("claim_guard"), "claim guard")
    if guard != {
        "matched_nanozk_claim_allowed": False,
        "native_proof_size_claim_allowed": False,
        "package_bytes_are_proof_bytes": False,
        "native_d128_block_proof_object_exists": False,
    }:
        raise NativeD128BlockProofObjectRouteError("claim guard drift")
    rows = _list(payload.get("route_rows"), "route rows")
    if build_summary(rows) != payload.get("summary"):
        raise NativeD128BlockProofObjectRouteError("summary drift")
    for row in rows:
        item = _dict(row, "route row")
        if set(item) != set(TSV_COLUMNS):
            raise NativeD128BlockProofObjectRouteError("route row key drift")
        if item["row_id"] == "external_package_without_vk":
            if item["bytes"] != EXPECTED_PACKAGE_WITHOUT_VK_BYTES:
                raise NativeD128BlockProofObjectRouteError("package bytes drift")
            if item["ratio_vs_nanozk_reported"] != EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK:
                raise NativeD128BlockProofObjectRouteError("package NANOZK ratio drift")
        if item["row_id"] == "native_d128_block_proof_object":
            if item["bytes"] is not None:
                raise NativeD128BlockProofObjectRouteError("native proof bytes smuggled")
            if item["status"] != NATIVE_PROOF_OBJECT_STATUS:
                raise NativeD128BlockProofObjectRouteError("native proof status drift")
        if item.get("can_support_native_claim") is not False:
            raise NativeD128BlockProofObjectRouteError("route row claim guard drift")
        _num_or_none(item.get("rows"), "route row rows")
        _num_or_none(item.get("bytes"), "route row bytes")
        _num_or_none(item.get("ratio_vs_nanozk_reported"), "route row ratio")
    descriptors = _list(payload.get("source_artifacts"), "source artifacts")
    if len(descriptors) != 6:
        raise NativeD128BlockProofObjectRouteError("source artifact count drift")
    if expected_sources is None:
        expected_sources = source_descriptor_map(checked_sources())
    actual_sources = {descriptor["path"]: descriptor for descriptor in descriptors}
    if actual_sources != expected_sources:
        raise NativeD128BlockProofObjectRouteError("source artifact drift")


def _finalized_fields_present(payload: dict[str, Any]) -> bool:
    return any(
        key in payload
        for key in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected", "payload_commitment")
    )


def validate_payload(payload: dict[str, Any]) -> None:
    expected_core = build_core_payload()
    for key, expected_value in expected_core.items():
        if payload.get(key) != expected_value:
            raise NativeD128BlockProofObjectRouteError(f"{key} drift")
    if not _finalized_fields_present(payload):
        if set(payload) != set(expected_core):
            raise NativeD128BlockProofObjectRouteError("draft payload key drift")
        return
    expected_keys = set(expected_core) | {"mutation_inventory", "cases", "case_count", "all_mutations_rejected", "payload_commitment"}
    if set(payload) != expected_keys:
        raise NativeD128BlockProofObjectRouteError("final payload key drift")
    if payload.get("mutation_inventory") != list(MUTATION_NAMES):
        raise NativeD128BlockProofObjectRouteError("mutation inventory drift")
    cases = _list(payload.get("cases"), "cases")
    if payload.get("case_count") != len(MUTATION_NAMES) or len(cases) != len(MUTATION_NAMES):
        raise NativeD128BlockProofObjectRouteError("mutation case count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise NativeD128BlockProofObjectRouteError("mutation rejection drift")
    for index, case in enumerate(cases):
        item = _dict(case, f"case {index}")
        if set(item) != {"mutation", "accepted", "rejected", "error"}:
            raise NativeD128BlockProofObjectRouteError("mutation case key drift")
        if item["mutation"] != MUTATION_NAMES[index]:
            raise NativeD128BlockProofObjectRouteError("mutation case order drift")
        if item["accepted"] is not False or item["rejected"] is not True:
            raise NativeD128BlockProofObjectRouteError("mutation case accepted")
        _str(item.get("error"), "mutation error")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise NativeD128BlockProofObjectRouteError("payload commitment drift")


def mutation_plan(name: str) -> Callable[[dict[str, Any]], None]:
    def row(row_id: str, field: str, value: Any) -> Callable[[dict[str, Any]], None]:
        def apply(payload: dict[str, Any]) -> None:
            for item in payload["route_rows"]:
                if item["row_id"] == row_id:
                    item[field] = value
                    return
            raise AssertionError(row_id)

        return apply

    plans: dict[str, Callable[[dict[str, Any]], None]] = {
        "full_accumulator_promoted_to_native_proof": row(
            "full_d128_verifier_accumulator", "can_support_native_claim", True
        ),
        "two_slice_no_go_changed_to_go": row("two_slice_outer_proof_target", "status", "GO_TWO_SLICE_OUTER_PROOF"),
        "attention_input_contract_promoted_to_proof": row(
            "attention_derived_outer_input_contract", "object_class", "native_proof_object"
        ),
        "package_without_vk_promoted_to_proof_size": row(
            "external_package_without_vk", "claim_boundary", "native proof-size evidence"
        ),
        "native_proof_bytes_smuggled": row("native_d128_block_proof_object", "bytes", 4_752),
        "matched_nanozk_claim_enabled": lambda payload: payload["claim_guard"].update(
            {"matched_nanozk_claim_allowed": True}
        ),
        "first_blocker_removed": lambda payload: payload["summary"].update({"first_blocker": ""}),
        "next_minimal_experiment_weakened": lambda payload: payload["summary"].update(
            {"next_minimal_experiment": "claim six-slice proof object from current package"}
        ),
        "non_claim_removed": lambda payload: payload["non_claims"].remove("not a NANOZK proof-size win"),
        "source_artifact_hash_drift": lambda payload: payload["source_artifacts"][0].update({"file_sha256": "0" * 64}),
        "route_row_removed": lambda payload: payload["route_rows"].pop(),
        "result_changed_to_go": lambda payload: payload.update({"result": "GO_NATIVE_D128_BLOCK_PROOF_OBJECT"}),
        "validation_command_drift": lambda payload: payload["validation_commands"].pop(),
    }
    return plans[name]


def mutation_cases(base: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name in MUTATION_NAMES:
        mutated = copy.deepcopy(base)
        error = ""
        accepted = False
        try:
            mutation_plan(name)(mutated)
        except Exception as err:
            raise NativeD128BlockProofObjectRouteError(f"mutation plan failed for {name}: {err}") from err
        try:
            validate_payload(mutated)
            accepted = True
        except Exception as err:  # noqa: BLE001 - evidence records rejection reason.
            error = f"validate failed: {str(err) or type(err).__name__}"
        cases.append(
            {
                "mutation": name,
                "accepted": accepted,
                "rejected": not accepted,
                "error": error,
            }
        )
    return cases


def build_payload() -> dict[str, Any]:
    payload = build_core_payload()
    cases = mutation_cases(payload)
    payload["mutation_inventory"] = list(MUTATION_NAMES)
    payload["cases"] = cases
    payload["case_count"] = len(cases)
    payload["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload)
    return payload


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in payload["route_rows"]:
        writer.writerow(row)
    return out.getvalue()


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    if json_path is None and tsv_path is None:
        raise NativeD128BlockProofObjectRouteError("at least one output path is required")
    if json_path is not None:
        try:
            COMPRESSION.atomic_write_text(json_path, pretty_json(payload) + "\n", suffix=".json")
        except Exception as err:
            raise NativeD128BlockProofObjectRouteError(f"failed to write JSON output: {err}") from err
    if tsv_path is not None:
        try:
            COMPRESSION.atomic_write_text(tsv_path, to_tsv(payload), suffix=".tsv")
        except Exception as err:
            raise NativeD128BlockProofObjectRouteError(f"failed to write TSV output: {err}") from err


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        payload = build_payload()
        if args.write_json or args.write_tsv:
            write_outputs(payload, args.write_json, args.write_tsv)
            print(
                json.dumps(
                    {
                        "decision": payload["decision"],
                        "result": payload["result"],
                        "native_block_proof_object_status": payload["summary"]["native_block_proof_object_status"],
                        "package_without_vk_bytes": payload["summary"]["package_without_vk_bytes"],
                        "package_without_vk_vs_nanozk_reported_ratio": payload["summary"][
                            "package_without_vk_vs_nanozk_reported_ratio"
                        ],
                        "d128_checked_rows": payload["summary"]["d128_checked_rows"],
                        "mutations_rejected": payload["case_count"],
                    },
                    sort_keys=True,
                )
            )
        else:
            print(pretty_json(payload))
    except NativeD128BlockProofObjectRouteError as err:
        print(f"native d128 block proof-object route gate failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
