#!/usr/bin/env python3
"""Account for the d128 native-block proof gap without turning signals into claims."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import secrets
import stat as stat_module
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_one_transformer_block_surface_gate as SURFACE  # noqa: E402


ENGINEERING_EVIDENCE = ROOT / "docs" / "engineering" / "evidence"
PAPER_EVIDENCE = ROOT / "docs" / "paper" / "evidence"

ONE_BLOCK_SURFACE = ENGINEERING_EVIDENCE / "zkai-one-transformer-block-surface-2026-05.json"
PACKAGE_ACCOUNTING = ENGINEERING_EVIDENCE / "zkai-one-block-executable-package-accounting-2026-05.json"
COMPETITOR_MATRIX = ENGINEERING_EVIDENCE / "zkai-may2026-competitor-metric-matrix.json"
PUBLISHED_ZKML_NUMBERS = PAPER_EVIDENCE / "published-zkml-numbers-2026-04.tsv"

JSON_OUT = ENGINEERING_EVIDENCE / "zkai-d128-native-block-gap-accounting-2026-05.json"
TSV_OUT = ENGINEERING_EVIDENCE / "zkai-d128-native-block-gap-accounting-2026-05.tsv"

SCHEMA = "zkai-d128-native-block-gap-accounting-v1"
DECISION = "GO_D128_NATIVE_BLOCK_GAP_ACCOUNTING_NO_GO_MATCHED_LAYER_PROOF"
RESULT = "GO_INTERESTING_PACKAGE_SIGNAL_NO_GO_NANOZK_SIZE_WIN"
CLAIM_BOUNDARY = (
    "D128_BLOCK_SURFACE_GAP_ACCOUNTING_ONLY_NOT_NATIVE_PROOF_SIZE_"
    "NOT_MATCHED_NANOZK_BENCHMARK_NOT_RECURSION_NOT_TIMING"
)

EXPECTED_SURFACE_DECISION = "GO_ONE_TRANSFORMER_BLOCK_SURFACE_NO_GO_MATCHED_LAYER_PROOF"
EXPECTED_PACKAGE_DECISION = "GO_ONE_BLOCK_EXECUTABLE_PACKAGE_ACCOUNTING_NO_GO_NATIVE_PROOF_SIZE"
EXPECTED_PACKAGE_RESULT = "GO_EXTERNAL_RECEIPT_PACKAGE_ACCOUNTING_NO_GO_NATIVE_BLOCK_PROOF"
EXPECTED_MATRIX_DECISION = "GO_SOURCE_BACKED_COMPETITOR_MATRIX_NO_GO_MATCHED_BENCHMARK_CLAIMS"

EXPECTED_NANOZK_BLOCK_PROOF_BYTES_DECIMAL = 6_900
EXPECTED_NANOZK_BLOCK_PROOF_SIZE = "6.9 KB"
EXPECTED_NANOZK_PROVE_SECONDS = "6.3"
EXPECTED_NANOZK_VERIFY_SECONDS = "0.023"

EXPECTED_D64_ROWS = 49_600
EXPECTED_D128_ROWS = 197_504
EXPECTED_D128_OVER_D64_RATIO = 3.981935
EXPECTED_ATTENTION_CHAIN_ROWS = 199_553
EXPECTED_ATTENTION_CHAIN_EXTRA_ROWS = 2_049
EXPECTED_ATTENTION_CHAIN_VS_D128_RATIO = 1.010374

EXPECTED_SOURCE_CHAIN_BYTES = 14_624
EXPECTED_COMPRESSED_CHAIN_BYTES = 2_559
EXPECTED_COMPRESSED_CHAIN_RATIO = 0.174986
EXPECTED_SNARK_PROOF_BYTES = 807
EXPECTED_PUBLIC_SIGNALS_BYTES = 1_386
EXPECTED_VERIFICATION_KEY_BYTES = 5_856
EXPECTED_PACKAGE_WITHOUT_VK_BYTES = 4_752
EXPECTED_PACKAGE_WITH_VK_BYTES = 10_608
EXPECTED_PACKAGE_WITHOUT_VK_RATIO_VS_SOURCE = 0.324945
EXPECTED_PACKAGE_WITH_VK_RATIO_VS_SOURCE = 0.725383
EXPECTED_PACKAGE_WITHOUT_VK_SAVING = 9_872
EXPECTED_PACKAGE_WITH_VK_SAVING = 4_016
EXPECTED_PACKAGE_MUTATIONS = 12
EXPECTED_RECEIPT_MUTATIONS = 40

EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK_RATIO = 0.688696
EXPECTED_PACKAGE_WITH_VK_VS_NANOZK_RATIO = 1.537391
EXPECTED_SOURCE_CHAIN_VS_NANOZK_RATIO = 2.11942
EXPECTED_COMPRESSED_CHAIN_VS_NANOZK_RATIO = 0.37087
EXPECTED_PROOF_ONLY_VS_NANOZK_RATIO = 0.116957
EXPECTED_EXTERNAL_RECEIPT_OVERHEAD_WITHOUT_VK_BYTES = 2_193
EXPECTED_EXTERNAL_RECEIPT_OVERHEAD_WITHOUT_VK_SHARE_OF_SOURCE = 0.149959
EXPECTED_VK_OVERHEAD_VS_PACKAGE_WITHOUT_VK_RATIO = 1.232323

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
    "python3 scripts/zkai_d128_native_block_gap_accounting_gate.py --write-json docs/engineering/evidence/zkai-d128-native-block-gap-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-native-block-gap-accounting-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_d128_native_block_gap_accounting_gate.py scripts/tests/test_zkai_d128_native_block_gap_accounting_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_d128_native_block_gap_accounting_gate",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

MUTATION_NAMES = (
    "native_block_proof_size_smuggled",
    "matched_benchmark_claim_enabled",
    "nanozk_size_drift",
    "package_without_vk_bytes_drift",
    "package_with_vk_bytes_drift",
    "d128_rows_drift",
    "attention_chain_rows_drift",
    "source_artifact_hash_drift",
    "non_claim_removed",
    "claim_boundary_overclaim",
    "result_changed_to_size_win",
    "mutation_rejection_disabled",
)


class D128NativeBlockGapAccountingError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise D128NativeBlockGapAccountingError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise D128NativeBlockGapAccountingError(f"invalid JSON value: {err}") from err


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
        raise D128NativeBlockGapAccountingError(f"{field} must be object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D128NativeBlockGapAccountingError(f"{field} must be list")
    return value


def _int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128NativeBlockGapAccountingError(f"{field} must be integer")
    return value


def _number(value: Any, field: str) -> int | float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise D128NativeBlockGapAccountingError(f"{field} must be number")
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
        raise D128NativeBlockGapAccountingError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D128NativeBlockGapAccountingError(f"source evidence must be object: {path}")
    return payload, raw


def load_tsv(path: pathlib.Path) -> tuple[list[dict[str, str]], bytes]:
    try:
        raw = SURFACE.read_source_bytes(path, str(path.relative_to(ROOT)))
        text = raw.decode("utf-8")
    except Exception as err:
        raise D128NativeBlockGapAccountingError(f"failed to load source TSV {path}: {err}") from err
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    fieldnames = reader.fieldnames or []
    duplicates = sorted({field for field in fieldnames if fieldnames.count(field) > 1})
    if duplicates:
        raise D128NativeBlockGapAccountingError(f"TSV source has duplicate columns: {duplicates}")
    rows = list(reader)
    if not rows:
        raise D128NativeBlockGapAccountingError(f"TSV source must not be empty: {path}")
    for index, row in enumerate(rows, start=2):
        if None in row:
            raise D128NativeBlockGapAccountingError(f"TSV source row {index} has extra cells")
        if any(value is None for value in row.values()):
            raise D128NativeBlockGapAccountingError(f"TSV source row {index} has missing cells")
    return rows, raw


def source_descriptor(path: pathlib.Path, kind: str, raw: bytes, payload: Any) -> dict[str, Any]:
    descriptor: dict[str, Any] = {
        "kind": kind,
        "path": str(path.relative_to(ROOT)),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
    }
    if isinstance(payload, dict):
        descriptor["payload_sha256"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        descriptor["schema"] = payload.get("schema")
        descriptor["decision"] = payload.get("decision")
    else:
        descriptor["row_count"] = len(payload)
    return descriptor


def _parse_reported_size_bytes(value: str) -> int:
    parts = value.strip().split()
    if len(parts) != 2 or parts[1] != "KB":
        raise D128NativeBlockGapAccountingError(f"unsupported reported proof size: {value}")
    try:
        kilobytes = float(parts[0])
    except ValueError as err:
        raise D128NativeBlockGapAccountingError(f"unsupported reported proof size: {value}") from err
    bytes_decimal = int(round(kilobytes * 1000))
    if bytes_decimal <= 0:
        raise D128NativeBlockGapAccountingError("reported proof size must be positive")
    return bytes_decimal


def _nanozk_block_row(rows: list[dict[str, str]]) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if row.get("system") == "NANOZK"
        and row.get("workload_label") == "Transformer block proof"
        and row.get("workload_scope") == "Per-layer block proof"
    ]
    if len(matches) != 1:
        raise D128NativeBlockGapAccountingError("expected exactly one NANOZK transformer block row")
    row = matches[0]
    if row.get("proof_size_reported") != EXPECTED_NANOZK_BLOCK_PROOF_SIZE:
        raise D128NativeBlockGapAccountingError("NANOZK proof-size drift")
    if row.get("prove_seconds") != EXPECTED_NANOZK_PROVE_SECONDS:
        raise D128NativeBlockGapAccountingError("NANOZK prove-time drift")
    if row.get("verify_seconds") != EXPECTED_NANOZK_VERIFY_SECONDS:
        raise D128NativeBlockGapAccountingError("NANOZK verify-time drift")
    parsed = _parse_reported_size_bytes(row["proof_size_reported"])
    if parsed != EXPECTED_NANOZK_BLOCK_PROOF_BYTES_DECIMAL:
        raise D128NativeBlockGapAccountingError("NANOZK parsed proof-size drift")
    return row


def checked_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str], list[dict[str, Any]]]:
    surface, surface_raw = load_json(ONE_BLOCK_SURFACE)
    package, package_raw = load_json(PACKAGE_ACCOUNTING)
    matrix, matrix_raw = load_json(COMPETITOR_MATRIX)
    published_rows, published_raw = load_tsv(PUBLISHED_ZKML_NUMBERS)
    nanozk = _nanozk_block_row(published_rows)

    surface_summary = _dict(surface.get("summary"), "surface.summary")
    package_summary = _dict(package.get("summary"), "package.summary")

    if surface.get("schema") != "zkai-one-transformer-block-surface-v1":
        raise D128NativeBlockGapAccountingError("surface schema drift")
    if surface.get("decision") != EXPECTED_SURFACE_DECISION:
        raise D128NativeBlockGapAccountingError("surface decision drift")
    if surface_summary.get("d64_checked_rows") != EXPECTED_D64_ROWS:
        raise D128NativeBlockGapAccountingError("d64 row drift")
    if surface_summary.get("d128_checked_rows") != EXPECTED_D128_ROWS:
        raise D128NativeBlockGapAccountingError("d128 row drift")
    if surface_summary.get("d128_over_d64_checked_row_ratio") != EXPECTED_D128_OVER_D64_RATIO:
        raise D128NativeBlockGapAccountingError("d128/d64 ratio drift")
    if surface_summary.get("attention_derived_d128_statement_chain_rows") != EXPECTED_ATTENTION_CHAIN_ROWS:
        raise D128NativeBlockGapAccountingError("attention-chain row drift")
    if surface_summary.get("attention_derived_d128_statement_chain_compressed_ratio") != EXPECTED_COMPRESSED_CHAIN_RATIO:
        raise D128NativeBlockGapAccountingError("attention-chain compression ratio drift")
    if surface_summary.get("attention_derived_d128_snark_receipt_proof_bytes") != EXPECTED_SNARK_PROOF_BYTES:
        raise D128NativeBlockGapAccountingError("surface SNARK proof-byte drift")

    if package.get("schema") != "zkai-one-block-executable-package-accounting-v1":
        raise D128NativeBlockGapAccountingError("package schema drift")
    if package.get("decision") != EXPECTED_PACKAGE_DECISION:
        raise D128NativeBlockGapAccountingError("package decision drift")
    if package.get("result") != EXPECTED_PACKAGE_RESULT:
        raise D128NativeBlockGapAccountingError("package result drift")
    if package.get("case_count") != EXPECTED_PACKAGE_MUTATIONS or package.get("all_mutations_rejected") is not True:
        raise D128NativeBlockGapAccountingError("package mutation rejection drift")
    expected_package_fields = {
        "source_statement_chain_bytes": EXPECTED_SOURCE_CHAIN_BYTES,
        "compressed_statement_chain_bytes": EXPECTED_COMPRESSED_CHAIN_BYTES,
        "snark_proof_bytes": EXPECTED_SNARK_PROOF_BYTES,
        "snark_public_signals_bytes": EXPECTED_PUBLIC_SIGNALS_BYTES,
        "snark_verification_key_bytes": EXPECTED_VERIFICATION_KEY_BYTES,
        "package_without_vk_bytes": EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
        "package_without_vk_ratio_vs_source": EXPECTED_PACKAGE_WITHOUT_VK_RATIO_VS_SOURCE,
        "package_without_vk_saving_bytes": EXPECTED_PACKAGE_WITHOUT_VK_SAVING,
        "package_with_vk_bytes": EXPECTED_PACKAGE_WITH_VK_BYTES,
        "package_with_vk_ratio_vs_source": EXPECTED_PACKAGE_WITH_VK_RATIO_VS_SOURCE,
        "package_with_vk_saving_bytes": EXPECTED_PACKAGE_WITH_VK_SAVING,
        "statement_chain_rows": EXPECTED_ATTENTION_CHAIN_ROWS,
        "receipt_mutations_rejected": EXPECTED_RECEIPT_MUTATIONS,
    }
    for field, expected in expected_package_fields.items():
        if package_summary.get(field) != expected:
            raise D128NativeBlockGapAccountingError(f"package field drift: {field}")

    if matrix.get("schema") != "zkai-may2026-competitor-metric-matrix-v1":
        raise D128NativeBlockGapAccountingError("competitor matrix schema drift")
    if matrix.get("decision") != EXPECTED_MATRIX_DECISION:
        raise D128NativeBlockGapAccountingError("competitor matrix decision drift")
    if "not native proof-size evidence from the external package-accounting rows" not in _list(
        matrix.get("non_claims"), "matrix.non_claims"
    ):
        raise D128NativeBlockGapAccountingError("competitor matrix package non-claim drift")
    local_rows = _list(matrix.get("local_rows"), "matrix.local_rows")
    package_without_vk_rows = [
        row
        for row in local_rows
        if isinstance(row, dict) and row.get("surface") == "attention-derived d128 executable package without VK"
    ]
    if len(package_without_vk_rows) != 1 or package_without_vk_rows[0].get("value") != EXPECTED_PACKAGE_WITHOUT_VK_BYTES:
        raise D128NativeBlockGapAccountingError("competitor matrix package row drift")

    sources = [
        source_descriptor(ONE_BLOCK_SURFACE, "one_block_surface_json", surface_raw, surface),
        source_descriptor(PACKAGE_ACCOUNTING, "one_block_package_accounting_json", package_raw, package),
        source_descriptor(COMPETITOR_MATRIX, "competitor_metric_matrix_json", matrix_raw, matrix),
        source_descriptor(PUBLISHED_ZKML_NUMBERS, "published_zkml_numbers_tsv", published_raw, published_rows),
    ]
    return surface, package, matrix, nanozk, sources


def build_gap_summary(
    surface: dict[str, Any],
    package: dict[str, Any],
    nanozk: dict[str, str],
) -> dict[str, Any]:
    surface_summary = _dict(surface.get("summary"), "surface.summary")
    package_summary = _dict(package.get("summary"), "package.summary")
    nanozk_bytes = _parse_reported_size_bytes(nanozk["proof_size_reported"])

    d128_rows = _int(surface_summary.get("d128_checked_rows"), "d128 checked rows")
    chain_rows = _int(surface_summary.get("attention_derived_d128_statement_chain_rows"), "chain rows")
    source_bytes = _int(package_summary.get("source_statement_chain_bytes"), "source statement-chain bytes")
    compressed_bytes = _int(package_summary.get("compressed_statement_chain_bytes"), "compressed bytes")
    proof_bytes = _int(package_summary.get("snark_proof_bytes"), "SNARK proof bytes")
    public_bytes = _int(package_summary.get("snark_public_signals_bytes"), "public signal bytes")
    vk_bytes = _int(package_summary.get("snark_verification_key_bytes"), "verification key bytes")
    package_without_vk = _int(package_summary.get("package_without_vk_bytes"), "package without VK bytes")
    package_with_vk = _int(package_summary.get("package_with_vk_bytes"), "package with VK bytes")

    external_receipt_overhead = package_without_vk - compressed_bytes
    if external_receipt_overhead != proof_bytes + public_bytes:
        raise D128NativeBlockGapAccountingError("external receipt overhead accounting drift")
    gap_summary = {
        "native_d128_block_proof_bytes": None,
        "native_d128_block_verifier_time_ms": None,
        "matched_benchmark_claim_allowed": False,
        "nanozk_reported_block_proof_size": nanozk["proof_size_reported"],
        "nanozk_reported_block_proof_bytes_decimal": nanozk_bytes,
        "nanozk_reported_prove_seconds": nanozk["prove_seconds"],
        "nanozk_reported_verify_seconds": nanozk["verify_seconds"],
        "local_package_without_vk_bytes": package_without_vk,
        "local_package_without_vk_vs_nanozk_reported_ratio": round(package_without_vk / nanozk_bytes, 6),
        "local_package_without_vk_less_than_nanozk_reported_bytes": package_without_vk < nanozk_bytes,
        "local_package_with_vk_bytes": package_with_vk,
        "local_package_with_vk_vs_nanozk_reported_ratio": round(package_with_vk / nanozk_bytes, 6),
        "source_statement_chain_bytes": source_bytes,
        "source_statement_chain_vs_nanozk_reported_ratio": round(source_bytes / nanozk_bytes, 6),
        "compressed_statement_chain_bytes": compressed_bytes,
        "compressed_statement_chain_vs_nanozk_reported_ratio": round(compressed_bytes / nanozk_bytes, 6),
        "snark_statement_receipt_proof_bytes": proof_bytes,
        "snark_statement_receipt_proof_vs_nanozk_reported_ratio": round(proof_bytes / nanozk_bytes, 6),
        "external_receipt_overhead_without_vk_bytes": external_receipt_overhead,
        "external_receipt_overhead_without_vk_share_of_source": round(external_receipt_overhead / source_bytes, 6),
        "verification_key_overhead_bytes": vk_bytes,
        "verification_key_overhead_vs_package_without_vk_ratio": round(vk_bytes / package_without_vk, 6),
        "d64_checked_rows": surface_summary["d64_checked_rows"],
        "d128_checked_rows": d128_rows,
        "d128_over_d64_checked_row_ratio": surface_summary["d128_over_d64_checked_row_ratio"],
        "attention_derived_statement_chain_rows": chain_rows,
        "attention_derived_statement_chain_extra_rows_vs_d128_receipt": chain_rows - d128_rows,
        "attention_derived_statement_chain_vs_d128_receipt_ratio": round(chain_rows / d128_rows, 6),
        "strongest_claim": (
            "The attention-derived d128 route has an external verifier-facing package that is byte-smaller "
            "than the source-backed NANOZK block proof size row, but the object classes are different."
        ),
        "go_result": (
            "GO for treating the byte comparison as a prioritization signal for native aggregation work."
        ),
        "no_go_result": (
            "NO-GO for claiming a smaller proof than NANOZK until a native or matched d128 block proof object exists."
        ),
    }
    expected = {
        "local_package_without_vk_vs_nanozk_reported_ratio": EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK_RATIO,
        "local_package_with_vk_vs_nanozk_reported_ratio": EXPECTED_PACKAGE_WITH_VK_VS_NANOZK_RATIO,
        "source_statement_chain_vs_nanozk_reported_ratio": EXPECTED_SOURCE_CHAIN_VS_NANOZK_RATIO,
        "compressed_statement_chain_vs_nanozk_reported_ratio": EXPECTED_COMPRESSED_CHAIN_VS_NANOZK_RATIO,
        "snark_statement_receipt_proof_vs_nanozk_reported_ratio": EXPECTED_PROOF_ONLY_VS_NANOZK_RATIO,
        "external_receipt_overhead_without_vk_bytes": EXPECTED_EXTERNAL_RECEIPT_OVERHEAD_WITHOUT_VK_BYTES,
        "external_receipt_overhead_without_vk_share_of_source": EXPECTED_EXTERNAL_RECEIPT_OVERHEAD_WITHOUT_VK_SHARE_OF_SOURCE,
        "verification_key_overhead_vs_package_without_vk_ratio": EXPECTED_VK_OVERHEAD_VS_PACKAGE_WITHOUT_VK_RATIO,
        "attention_derived_statement_chain_extra_rows_vs_d128_receipt": EXPECTED_ATTENTION_CHAIN_EXTRA_ROWS,
        "attention_derived_statement_chain_vs_d128_receipt_ratio": EXPECTED_ATTENTION_CHAIN_VS_D128_RATIO,
    }
    for field, expected_value in expected.items():
        if gap_summary[field] != expected_value:
            raise D128NativeBlockGapAccountingError(f"gap summary drift: {field}")
    return gap_summary


def gap_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "surface": "NANOZK transformer block proof",
            "metric": "source-backed reported proof size",
            "value": summary["nanozk_reported_block_proof_bytes_decimal"],
            "unit": "decimal_bytes",
            "comparison_status": "EXTERNAL_CONTEXT_ONLY",
        },
        {
            "surface": "local attention-derived package without VK",
            "metric": "package bytes versus NANOZK reported bytes",
            "value": summary["local_package_without_vk_bytes"],
            "unit": "bytes",
            "ratio_vs_nanozk_reported": summary["local_package_without_vk_vs_nanozk_reported_ratio"],
            "comparison_status": "INTERESTING_SMALLER_PACKAGE_NOT_MATCHED_PROOF_BENCHMARK",
        },
        {
            "surface": "local attention-derived package with VK",
            "metric": "self-contained package bytes versus NANOZK reported bytes",
            "value": summary["local_package_with_vk_bytes"],
            "unit": "bytes",
            "ratio_vs_nanozk_reported": summary["local_package_with_vk_vs_nanozk_reported_ratio"],
            "comparison_status": "LARGER_WITH_SETUP_NOT_MATCHED_PROOF_BENCHMARK",
        },
        {
            "surface": "d128 receipt chain to attention-derived statement chain",
            "metric": "extra relation rows for attention-to-block statement binding",
            "value": summary["attention_derived_statement_chain_extra_rows_vs_d128_receipt"],
            "unit": "rows",
            "ratio_vs_d128_receipt": summary["attention_derived_statement_chain_vs_d128_receipt_ratio"],
            "comparison_status": "LOCAL_BLOCK_SURFACE_SHAPE_SIGNAL",
        },
        {
            "surface": "native d128 block proof object",
            "metric": "proof bytes",
            "value": summary["native_d128_block_proof_bytes"],
            "unit": "bytes",
            "comparison_status": "MISSING_REQUIRED_FOR_MATCHED_BENCHMARK",
        },
    ]


def build_payload_core() -> dict[str, Any]:
    surface, package, _matrix, nanozk, sources = checked_sources()
    summary = build_gap_summary(surface, package, nanozk)
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": sources,
        "gap_rows": gap_rows(summary),
        "summary": summary,
        "claim_guard": {
            "tempting_observation": "local package without VK is byte-smaller than NANOZK reported block proof row",
            "matched_benchmark_claim_allowed": False,
            "reason": (
                "the local row is an external executable statement package over an attention-derived d128 input "
                "contract, not a native or matched transformer-block proof object"
            ),
        },
        "blockers": [
            "native aggregated d128 transformer-block proof object is missing",
            "matched workload is missing: local attention-derived d128 package is not NANOZK GPT-2-scale d768 block",
            "native verifier-time and prover-time evidence are missing",
            "recursion or proof-carrying aggregation over the six Stwo slice proofs is missing",
            "verification-key/setup accounting is still external and not production setup evidence",
        ],
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }


def validate_payload_core(payload: dict[str, Any], *, expected: dict[str, Any] | None = None) -> None:
    base = expected if expected is not None else build_payload_core()
    if payload != base:
        if not isinstance(payload, dict):
            raise D128NativeBlockGapAccountingError("payload must be object")
        if payload.get("schema") != SCHEMA:
            raise D128NativeBlockGapAccountingError("schema drift")
        if payload.get("decision") != DECISION:
            raise D128NativeBlockGapAccountingError("decision drift")
        if payload.get("result") != RESULT:
            raise D128NativeBlockGapAccountingError("result drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise D128NativeBlockGapAccountingError("claim boundary drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise D128NativeBlockGapAccountingError("non-claims drift")
        if payload.get("source_artifacts") != base["source_artifacts"]:
            raise D128NativeBlockGapAccountingError("source artifact drift")
        if payload.get("summary") != base["summary"]:
            raise D128NativeBlockGapAccountingError("summary drift")
        if payload.get("claim_guard") != base["claim_guard"]:
            raise D128NativeBlockGapAccountingError("claim guard drift")
        raise D128NativeBlockGapAccountingError("payload drift")


def mutation_cases(core: dict[str, Any], *, expected_core: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    def mutate(name: str, payload: dict[str, Any]) -> None:
        if name == "native_block_proof_size_smuggled":
            payload["summary"]["native_d128_block_proof_bytes"] = 4096
        elif name == "matched_benchmark_claim_enabled":
            payload["claim_guard"]["matched_benchmark_claim_allowed"] = True
        elif name == "nanozk_size_drift":
            payload["summary"]["nanozk_reported_block_proof_bytes_decimal"] = 1
        elif name == "package_without_vk_bytes_drift":
            payload["summary"]["local_package_without_vk_bytes"] = 1
        elif name == "package_with_vk_bytes_drift":
            payload["summary"]["local_package_with_vk_bytes"] = 1
        elif name == "d128_rows_drift":
            payload["summary"]["d128_checked_rows"] = 1
        elif name == "attention_chain_rows_drift":
            payload["summary"]["attention_derived_statement_chain_rows"] = 1
        elif name == "source_artifact_hash_drift":
            payload["source_artifacts"][0]["file_sha256"] = "0" * 64
        elif name == "non_claim_removed":
            payload["non_claims"].remove("not a NANOZK proof-size win")
        elif name == "claim_boundary_overclaim":
            payload["claim_boundary"] = "NATIVE_D128_BLOCK_PROOF_SIZE_WIN"
        elif name == "result_changed_to_size_win":
            payload["result"] = "GO_SMALLER_THAN_NANOZK"
        elif name == "mutation_rejection_disabled":
            payload["all_mutations_rejected"] = False
        else:
            raise AssertionError(f"unhandled mutation {name}")

    cases = []
    base = expected_core if expected_core is not None else core
    for name in MUTATION_NAMES:
        mutated = copy.deepcopy(core)
        mutate(name, mutated)
        try:
            validate_payload_core(mutated, expected=base)
        except Exception as err:  # noqa: BLE001 - evidence records rejection text.
            cases.append({"mutation": name, "rejected": True, "error": str(err) or type(err).__name__})
        else:
            cases.append({"mutation": name, "rejected": False, "error": ""})
    return cases


def build_payload_uncommitted() -> dict[str, Any]:
    core = build_payload_core()
    expected_core = copy.deepcopy(core)
    cases = mutation_cases(core, expected_core=expected_core)
    core["mutation_inventory"] = list(MUTATION_NAMES)
    core["cases"] = cases
    core["case_count"] = len(cases)
    core["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    return core


def validate_payload(payload: dict[str, Any], *, expected: dict[str, Any] | None = None) -> None:
    base = expected if expected is not None else build_payload_uncommitted()
    if not isinstance(payload, dict):
        raise D128NativeBlockGapAccountingError("payload must be object")
    candidate = {key: value for key, value in payload.items() if key != "payload_commitment"}
    if candidate != base:
        if payload.get("schema") != SCHEMA:
            raise D128NativeBlockGapAccountingError("schema drift")
        if payload.get("decision") != DECISION:
            raise D128NativeBlockGapAccountingError("decision drift")
        if payload.get("result") != RESULT:
            raise D128NativeBlockGapAccountingError("result drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise D128NativeBlockGapAccountingError("claim boundary drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise D128NativeBlockGapAccountingError("non-claims drift")
        if payload.get("all_mutations_rejected") is not True:
            raise D128NativeBlockGapAccountingError("mutation rejection drift")
        if _dict(payload.get("claim_guard"), "claim_guard").get("matched_benchmark_claim_allowed") is not False:
            raise D128NativeBlockGapAccountingError("matched benchmark guard drift")
        raise D128NativeBlockGapAccountingError("payload drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise D128NativeBlockGapAccountingError("payload commitment drift")


def build_payload() -> dict[str, Any]:
    payload = build_payload_uncommitted()
    expected = copy.deepcopy(payload)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload, expected=expected)
    return payload


def to_tsv(payload: dict[str, Any], *, expected: dict[str, Any] | None = None) -> str:
    validate_payload(payload, expected=expected)
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(["surface", "metric", "value", "unit", "ratio", "comparison_status"])
    for row in payload["gap_rows"]:
        ratio = row.get("ratio_vs_nanozk_reported", row.get("ratio_vs_d128_receipt", ""))
        writer.writerow([row["surface"], row["metric"], row["value"], row["unit"], ratio, row["comparison_status"]])
    return out.getvalue()


def _assert_no_repo_symlink_components(path: pathlib.Path, label: str) -> None:
    absolute = path if path.is_absolute() else ROOT / path
    try:
        relative = absolute.relative_to(ROOT)
    except ValueError as err:
        raise D128NativeBlockGapAccountingError(f"{label} must stay inside repository") from err
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise D128NativeBlockGapAccountingError(f"{label} must not include symlink components")


def _assert_output_path(path: pathlib.Path, label: str) -> pathlib.Path:
    raw = str(path).replace("\\", "/")
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise D128NativeBlockGapAccountingError(f"{label} must be repo-relative")
    if pathlib.PurePosixPath(*relative.parts[:3]) != pathlib.PurePosixPath("docs/engineering/evidence"):
        raise D128NativeBlockGapAccountingError(f"{label} must stay under docs/engineering/evidence")
    full = ROOT.joinpath(*relative.parts)
    _assert_no_repo_symlink_components(full.parent, label)
    if full.is_symlink():
        raise D128NativeBlockGapAccountingError(f"{label} must not include symlink components")
    return full


def _directory_identity(path: pathlib.Path, label: str) -> tuple[int, int]:
    try:
        path_stat = path.lstat()
    except OSError as err:
        raise D128NativeBlockGapAccountingError(f"{label} parent directory is unavailable: {err}") from err
    if stat_module.S_ISLNK(path_stat.st_mode) or not stat_module.S_ISDIR(path_stat.st_mode):
        raise D128NativeBlockGapAccountingError(f"{label} parent must be a real directory")
    return (path_stat.st_dev, path_stat.st_ino)


def _assert_directory_identity(path: pathlib.Path, identity: tuple[int, int], label: str) -> None:
    _assert_no_repo_symlink_components(path, label)
    if _directory_identity(path, label) != identity:
        raise D128NativeBlockGapAccountingError(f"{label} parent directory changed while writing")


def _open_stable_directory(path: pathlib.Path, label: str) -> tuple[int, tuple[int, int]]:
    _assert_no_repo_symlink_components(path, label)
    if not path.exists():
        raise D128NativeBlockGapAccountingError(f"{label} parent directory must already exist")
    identity = _directory_identity(path, label)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as err:
        raise D128NativeBlockGapAccountingError(f"failed to open {label} parent directory: {err}") from err
    try:
        fd_stat = os.fstat(fd)
        if not stat_module.S_ISDIR(fd_stat.st_mode):
            raise D128NativeBlockGapAccountingError(f"{label} parent must be a real directory")
        if (fd_stat.st_dev, fd_stat.st_ino) != identity:
            raise D128NativeBlockGapAccountingError(f"{label} parent directory changed while opening")
    except Exception:
        os.close(fd)
        raise
    return fd, identity


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    expected = {key: value for key, value in payload.items() if key != "payload_commitment"}
    outputs = []
    if json_path is not None:
        outputs.append((_assert_output_path(json_path, "json output path"), (pretty_json(payload) + "\n").encode()))
    if tsv_path is not None:
        outputs.append((_assert_output_path(tsv_path, "tsv output path"), to_tsv(payload, expected=expected).encode()))
    if not outputs:
        raise D128NativeBlockGapAccountingError("at least one output path is required")
    if len(outputs) == 2 and os.path.abspath(outputs[0][0]).casefold() == os.path.abspath(outputs[1][0]).casefold():
        raise D128NativeBlockGapAccountingError("json and tsv output paths must differ")

    temps: list[tuple[pathlib.Path, str, int, tuple[int, int]]] = []
    replaced: list[pathlib.Path] = []
    original_bytes: dict[pathlib.Path, bytes | None] = {}
    write_error: Exception | None = None
    rollback_errors: list[str] = []

    def write_temp(path: pathlib.Path, contents: bytes, label: str) -> tuple[pathlib.Path, str, int, tuple[int, int]]:
        parent_fd, identity = _open_stable_directory(path.parent, label)
        temp_name: str | None = None
        file_fd: int | None = None
        try:
            _assert_directory_identity(path.parent, identity, label)
            if path.is_symlink():
                raise D128NativeBlockGapAccountingError(f"{label} must not include symlink components")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            for _ in range(100):
                candidate = f".{path.name}.{secrets.token_hex(8)}.tmp"
                try:
                    file_fd = os.open(candidate, flags, 0o600, dir_fd=parent_fd)
                    temp_name = candidate
                    break
                except FileExistsError:
                    continue
            if file_fd is None or temp_name is None:
                raise D128NativeBlockGapAccountingError(f"failed to create unique temporary output for {label}")
            with os.fdopen(file_fd, "wb") as handle:
                file_fd = None
                handle.write(contents)
                handle.flush()
                os.fsync(handle.fileno())
            _assert_directory_identity(path.parent, identity, label)
            return (path.parent / temp_name, temp_name, parent_fd, identity)
        except Exception:
            if file_fd is not None:
                os.close(file_fd)
            if temp_name is not None:
                try:
                    os.unlink(temp_name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
                except FileNotFoundError:
                    pass
            os.close(parent_fd)
            raise

    def replace_temp(temp: tuple[pathlib.Path, str, int, tuple[int, int]], path: pathlib.Path, label: str) -> None:
        _tmp_path, temp_name, parent_fd, identity = temp
        _assert_directory_identity(path.parent, identity, label)
        if path.is_symlink():
            raise D128NativeBlockGapAccountingError(f"{label} must not include symlink components")
        os.replace(temp_name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
        _assert_directory_identity(path.parent, identity, label)

    def rollback_replace(path: pathlib.Path, contents: bytes) -> None:
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        tmp = write_temp(path, contents, "rollback output path")
        temps.append(tmp)
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        replace_temp(tmp, path, "rollback output path")

    def rollback_remove(path: pathlib.Path) -> None:
        _assert_output_path(path.relative_to(ROOT), "rollback output path")
        parent_fd, identity = _open_stable_directory(path.parent, "rollback output path")
        try:
            _assert_directory_identity(path.parent, identity, "rollback output path")
            if path.is_symlink():
                raise D128NativeBlockGapAccountingError("rollback output path must not include symlink components")
            try:
                os.unlink(path.name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            os.fsync(parent_fd)
            _assert_directory_identity(path.parent, identity, "rollback output path")
        finally:
            os.close(parent_fd)

    try:
        for path, _contents in outputs:
            if path.exists():
                if path.is_symlink():
                    raise D128NativeBlockGapAccountingError("output path must not include symlink components")
                original_bytes[path] = SURFACE.read_source_bytes(path, "existing output")
            else:
                original_bytes[path] = None
        for index, (path, contents) in enumerate(outputs, start=1):
            label = f"output path {index}"
            temp = write_temp(path, contents, label)
            temps.append(temp)
            replace_temp(temp, path, label)
            replaced.append(path)
    except Exception as err:  # noqa: BLE001 - wrap write failures with rollback diagnostics.
        write_error = err
    if write_error is None:
        for _temp_path, _temp_name, parent_fd, _identity in temps:
            try:
                os.close(parent_fd)
            except OSError as err:
                print(f"warning: failed to close output directory fd: {err}", file=sys.stderr)
    else:
        for path in reversed(replaced):
            try:
                original = original_bytes.get(path)
                if original is None:
                    rollback_remove(path)
                else:
                    rollback_replace(path, original)
            except Exception as err:  # noqa: BLE001 - report rollback diagnostics.
                rollback_errors.append(str(err) or type(err).__name__)
        for _temp_path, temp_name, parent_fd, _identity in temps:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except FileNotFoundError:
                pass
            except Exception as err:  # noqa: BLE001
                rollback_errors.append(str(err) or type(err).__name__)
            finally:
                try:
                    os.close(parent_fd)
                except OSError:
                    pass
        detail = str(write_error) or type(write_error).__name__
        if rollback_errors:
            detail = f"{detail}; rollback errors: {'; '.join(rollback_errors)}"
        raise D128NativeBlockGapAccountingError(f"failed to write output path: {detail}") from write_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args(argv)
    payload = build_payload()
    if args.write_json or args.write_tsv:
        write_outputs(payload, args.write_json, args.write_tsv)
    else:
        print(pretty_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
