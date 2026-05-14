#!/usr/bin/env python3
"""Build a matched d64/d128 evidence table without promoting package bytes into proof claims."""

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

D64_BLOCK_RECEIPT = ENGINEERING_EVIDENCE / "zkai-d64-block-receipt-composition-gate-2026-05.json"
D64_EXTERNAL_SNARK = ENGINEERING_EVIDENCE / "zkai-d64-external-recursion-adapter-2026-05.json"
D128_BLOCK_RECEIPT = ENGINEERING_EVIDENCE / "zkai-d128-block-receipt-composition-gate-2026-05.json"
ONE_BLOCK_SURFACE = ENGINEERING_EVIDENCE / "zkai-one-transformer-block-surface-2026-05.json"
PACKAGE_ACCOUNTING = ENGINEERING_EVIDENCE / "zkai-one-block-executable-package-accounting-2026-05.json"
D128_GAP_ACCOUNTING = ENGINEERING_EVIDENCE / "zkai-d128-native-block-gap-accounting-2026-05.json"
PUBLISHED_ZKML_NUMBERS = PAPER_EVIDENCE / "published-zkml-numbers-2026-04.tsv"

JSON_OUT = ENGINEERING_EVIDENCE / "zkai-matched-d64-d128-evidence-table-2026-05.json"
TSV_OUT = ENGINEERING_EVIDENCE / "zkai-matched-d64-d128-evidence-table-2026-05.tsv"

SCHEMA = "zkai-matched-d64-d128-evidence-table-v1"
DECISION = "GO_MATCHED_D64_D128_EVIDENCE_TABLE_NO_GO_NATIVE_PROOF_SIZE_WIN"
RESULT = "GO_OBJECT_CLASS_SEPARATION_NO_GO_MATCHED_BENCHMARK"
CLAIM_BOUNDARY = (
    "MATCHED_EVIDENCE_TABLE_ONLY_SEPARATES_STWO_NATIVE_ROWS_EXTERNAL_SNARK_RECEIPTS_"
    "PACKAGE_BYTES_AND_PAPER_REPORTED_CONTEXT"
)

EXPECTED_D64_ROWS = 49_600
EXPECTED_D128_ROWS = 197_504
EXPECTED_D128_OVER_D64_RATIO = 3.981935
EXPECTED_D128_CHAIN_ROWS = 199_553
EXPECTED_D128_CHAIN_EXTRA_ROWS = 2_049
EXPECTED_D128_CHAIN_VS_D128_RATIO = 1.010374

EXPECTED_SOURCE_CHAIN_BYTES = 14_624
EXPECTED_COMPRESSED_CHAIN_BYTES = 2_559
EXPECTED_COMPRESSED_CHAIN_RATIO_VS_SOURCE = 0.174986
EXPECTED_SNARK_PROOF_BYTES = 807
EXPECTED_SNARK_PUBLIC_SIGNAL_BYTES = 1_386
EXPECTED_SNARK_VERIFICATION_KEY_BYTES = 5_856
EXPECTED_PACKAGE_WITHOUT_VK_BYTES = 4_752
EXPECTED_PACKAGE_WITH_VK_BYTES = 10_608
EXPECTED_PACKAGE_WITHOUT_VK_RATIO_VS_SOURCE = 0.324945
EXPECTED_PACKAGE_WITH_VK_RATIO_VS_SOURCE = 0.725383
EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK = 0.688696
EXPECTED_PACKAGE_WITH_VK_VS_NANOZK = 1.537391
EXPECTED_SOURCE_CHAIN_VS_NANOZK = 2.11942
EXPECTED_COMPRESSED_CHAIN_VS_NANOZK = 0.37087
EXPECTED_SNARK_PROOF_VS_NANOZK = 0.116957

EXPECTED_D64_SNARK_PROOF_BYTES = 806
EXPECTED_D64_SNARK_PUBLIC_SIGNAL_BYTES = 1_797
EXPECTED_D64_SNARK_VERIFICATION_KEY_BYTES = 6_776
EXPECTED_D64_SNARK_MUTATIONS = 36

EXPECTED_NANOZK_BLOCK_BYTES = 6_900
EXPECTED_NANOZK_BLOCK_SIZE = "6.9 KB"
EXPECTED_NANOZK_PROVE_SECONDS = "6.3"
EXPECTED_NANOZK_VERIFY_SECONDS = "0.023"

NON_CLAIMS = [
    "not a native d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched benchmark against NANOZK, Jolt Atlas, EZKL, DeepProve-1, RISC Zero, or Obelyzk",
    "not verifier-time or prover-time evidence",
    "not recursive aggregation or proof-carrying data",
    "not verification of Stwo slice proofs inside Groth16",
    "not full transformer inference",
    "not exact real-valued Softmax, LayerNorm, or GELU",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_matched_d64_d128_evidence_table_gate.py --write-json docs/engineering/evidence/zkai-matched-d64-d128-evidence-table-2026-05.json --write-tsv docs/engineering/evidence/zkai-matched-d64-d128-evidence-table-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_matched_d64_d128_evidence_table_gate.py scripts/tests/test_zkai_matched_d64_d128_evidence_table_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_matched_d64_d128_evidence_table_gate",
    "git diff --check",
    "just gate-fast",
]

REQUIRED_ROW_FIELDS = (
    "row_id",
    "system",
    "dimension_or_scope",
    "backend_family",
    "object_class",
    "evidence_status",
    "workload_scope",
    "metric",
    "value",
    "unit",
    "source_path",
    "comparison_boundary",
)

MUTATION_NAMES = (
    "package_without_vk_promoted_to_native_proof",
    "matched_benchmark_claim_enabled",
    "nanozk_reproduced_locally_without_source",
    "native_d128_proof_size_smuggled",
    "d64_row_drift",
    "d128_row_drift",
    "package_without_vk_drift",
    "source_artifact_hash_drift",
    "row_object_class_removed",
    "non_claim_removed",
)


class MatchedD64D128EvidenceTableError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as err:
        raise MatchedD64D128EvidenceTableError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise MatchedD64D128EvidenceTableError(f"invalid JSON value: {err}") from err


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
        raise MatchedD64D128EvidenceTableError(f"{field} must be object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise MatchedD64D128EvidenceTableError(f"{field} must be list")
    return value


def _int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise MatchedD64D128EvidenceTableError(f"{field} must be integer")
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
        raise MatchedD64D128EvidenceTableError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise MatchedD64D128EvidenceTableError(f"source evidence must be object: {path}")
    return payload, raw


def load_tsv(path: pathlib.Path) -> tuple[list[dict[str, str]], bytes]:
    try:
        raw = SURFACE.read_source_bytes(path, str(path.relative_to(ROOT)))
        text = raw.decode("utf-8")
    except Exception as err:
        raise MatchedD64D128EvidenceTableError(f"failed to load source TSV {path}: {err}") from err
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    fieldnames = reader.fieldnames or []
    duplicates = sorted({field for field in fieldnames if fieldnames.count(field) > 1})
    if duplicates:
        raise MatchedD64D128EvidenceTableError(f"TSV source has duplicate columns: {duplicates}")
    rows = list(reader)
    if not rows:
        raise MatchedD64D128EvidenceTableError(f"TSV source must not be empty: {path}")
    for index, row in enumerate(rows, start=2):
        if None in row:
            raise MatchedD64D128EvidenceTableError(f"TSV source row {index} has extra cells")
        if any(value is None for value in row.values()):
            raise MatchedD64D128EvidenceTableError(f"TSV source row {index} has missing cells")
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
        descriptor["result"] = payload.get("result")
    else:
        descriptor["row_count"] = len(payload)
    return descriptor


def _parse_reported_size_bytes(value: str) -> int:
    parts = value.strip().split()
    if len(parts) != 2 or parts[1] != "KB":
        raise MatchedD64D128EvidenceTableError(f"unsupported reported proof size: {value}")
    try:
        kilobytes = float(parts[0])
    except ValueError as err:
        raise MatchedD64D128EvidenceTableError(f"unsupported reported proof size: {value}") from err
    return int(round(kilobytes * 1000))


def _nanozk_block_row(rows: list[dict[str, str]]) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if row.get("system") == "NANOZK"
        and row.get("workload_label") == "Transformer block proof"
        and row.get("workload_scope") == "Per-layer block proof"
    ]
    if len(matches) != 1:
        raise MatchedD64D128EvidenceTableError("expected exactly one NANOZK transformer block row")
    row = matches[0]
    if row.get("proof_size_reported") != EXPECTED_NANOZK_BLOCK_SIZE:
        raise MatchedD64D128EvidenceTableError("NANOZK proof-size drift")
    if row.get("prove_seconds") != EXPECTED_NANOZK_PROVE_SECONDS:
        raise MatchedD64D128EvidenceTableError("NANOZK prove-time drift")
    if row.get("verify_seconds") != EXPECTED_NANOZK_VERIFY_SECONDS:
        raise MatchedD64D128EvidenceTableError("NANOZK verify-time drift")
    if _parse_reported_size_bytes(row["proof_size_reported"]) != EXPECTED_NANOZK_BLOCK_BYTES:
        raise MatchedD64D128EvidenceTableError("NANOZK parsed proof-size drift")
    return row


def checked_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str], list[dict[str, Any]]]:
    d64_block, d64_block_raw = load_json(D64_BLOCK_RECEIPT)
    d64_snark, d64_snark_raw = load_json(D64_EXTERNAL_SNARK)
    d128_block, d128_block_raw = load_json(D128_BLOCK_RECEIPT)
    surface, surface_raw = load_json(ONE_BLOCK_SURFACE)
    package, package_raw = load_json(PACKAGE_ACCOUNTING)
    gap, gap_raw = load_json(D128_GAP_ACCOUNTING)
    published_rows, published_raw = load_tsv(PUBLISHED_ZKML_NUMBERS)
    nanozk = _nanozk_block_row(published_rows)

    d64_summary = _dict(d64_block.get("summary"), "d64_block.summary")
    d128_summary = _dict(d128_block.get("summary"), "d128_block.summary")
    surface_summary = _dict(surface.get("summary"), "surface.summary")
    package_summary = _dict(package.get("summary"), "package.summary")
    gap_summary = _dict(gap.get("summary"), "gap.summary")
    d64_receipt_metrics = _dict(d64_snark.get("receipt_metrics"), "d64_snark.receipt_metrics")

    if d64_block.get("schema") != "zkai-d64-block-receipt-composition-gate-v1":
        raise MatchedD64D128EvidenceTableError("d64 block schema drift")
    if d64_block.get("decision") != "GO_D64_BLOCK_RECEIPT_COMPOSITION_GATE":
        raise MatchedD64D128EvidenceTableError("d64 block decision drift")
    if d64_summary.get("total_checked_rows") != EXPECTED_D64_ROWS:
        raise MatchedD64D128EvidenceTableError("d64 checked-row drift")
    if d64_summary.get("slice_count") != 6:
        raise MatchedD64D128EvidenceTableError("d64 slice-count drift")
    if d64_block.get("case_count") != 14 or d64_block.get("all_mutations_rejected") is not True:
        raise MatchedD64D128EvidenceTableError("d64 mutation rejection drift")

    if d64_snark.get("schema") != "zkai-d64-external-recursion-adapter-gate-v1":
        raise MatchedD64D128EvidenceTableError("d64 SNARK schema drift")
    if d64_snark.get("decision") != "GO_D64_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_NESTED_VERIFIER_CONTRACT":
        raise MatchedD64D128EvidenceTableError("d64 SNARK decision drift")
    if d64_receipt_metrics.get("proof_size_bytes") != EXPECTED_D64_SNARK_PROOF_BYTES:
        raise MatchedD64D128EvidenceTableError("d64 SNARK proof-byte drift")
    if d64_receipt_metrics.get("public_signals_bytes") != EXPECTED_D64_SNARK_PUBLIC_SIGNAL_BYTES:
        raise MatchedD64D128EvidenceTableError("d64 SNARK public-signal byte drift")
    if d64_receipt_metrics.get("verification_key_bytes") != EXPECTED_D64_SNARK_VERIFICATION_KEY_BYTES:
        raise MatchedD64D128EvidenceTableError("d64 SNARK VK byte drift")
    if d64_snark.get("case_count") != EXPECTED_D64_SNARK_MUTATIONS or d64_snark.get("all_mutations_rejected") is not True:
        raise MatchedD64D128EvidenceTableError("d64 SNARK mutation rejection drift")

    if d128_block.get("schema") != "zkai-d128-block-receipt-composition-gate-v1":
        raise MatchedD64D128EvidenceTableError("d128 block schema drift")
    if d128_block.get("decision") != "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE":
        raise MatchedD64D128EvidenceTableError("d128 block decision drift")
    if d128_summary.get("total_checked_rows") != EXPECTED_D128_ROWS:
        raise MatchedD64D128EvidenceTableError("d128 checked-row drift")
    if d128_summary.get("slice_count") != 6:
        raise MatchedD64D128EvidenceTableError("d128 slice-count drift")
    if d128_block.get("case_count") != 21 or d128_block.get("all_mutations_rejected") is not True:
        raise MatchedD64D128EvidenceTableError("d128 mutation rejection drift")

    if surface.get("schema") != "zkai-one-transformer-block-surface-v1":
        raise MatchedD64D128EvidenceTableError("one-block surface schema drift")
    if surface_summary.get("d64_checked_rows") != EXPECTED_D64_ROWS:
        raise MatchedD64D128EvidenceTableError("surface d64 row drift")
    if surface_summary.get("d128_checked_rows") != EXPECTED_D128_ROWS:
        raise MatchedD64D128EvidenceTableError("surface d128 row drift")
    if surface_summary.get("d128_over_d64_checked_row_ratio") != EXPECTED_D128_OVER_D64_RATIO:
        raise MatchedD64D128EvidenceTableError("surface d128/d64 ratio drift")
    if surface_summary.get("attention_derived_d128_statement_chain_rows") != EXPECTED_D128_CHAIN_ROWS:
        raise MatchedD64D128EvidenceTableError("surface statement-chain row drift")

    if package.get("schema") != "zkai-one-block-executable-package-accounting-v1":
        raise MatchedD64D128EvidenceTableError("package schema drift")
    expected_package_fields = {
        "source_statement_chain_bytes": EXPECTED_SOURCE_CHAIN_BYTES,
        "compressed_statement_chain_bytes": EXPECTED_COMPRESSED_CHAIN_BYTES,
        "snark_proof_bytes": EXPECTED_SNARK_PROOF_BYTES,
        "snark_public_signals_bytes": EXPECTED_SNARK_PUBLIC_SIGNAL_BYTES,
        "snark_verification_key_bytes": EXPECTED_SNARK_VERIFICATION_KEY_BYTES,
        "package_without_vk_bytes": EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
        "package_with_vk_bytes": EXPECTED_PACKAGE_WITH_VK_BYTES,
        "package_without_vk_ratio_vs_source": EXPECTED_PACKAGE_WITHOUT_VK_RATIO_VS_SOURCE,
        "package_with_vk_ratio_vs_source": EXPECTED_PACKAGE_WITH_VK_RATIO_VS_SOURCE,
    }
    for field, expected in expected_package_fields.items():
        if package_summary.get(field) != expected:
            raise MatchedD64D128EvidenceTableError(f"package field drift: {field}")

    if gap.get("schema") != "zkai-d128-native-block-gap-accounting-v1":
        raise MatchedD64D128EvidenceTableError("gap accounting schema drift")
    if gap.get("result") != "GO_INTERESTING_PACKAGE_SIGNAL_NO_GO_NANOZK_SIZE_WIN":
        raise MatchedD64D128EvidenceTableError("gap result drift")
    if gap_summary.get("matched_benchmark_claim_allowed") is not False:
        raise MatchedD64D128EvidenceTableError("gap matched-claim guard drift")
    if gap_summary.get("native_d128_block_proof_bytes") is not None:
        raise MatchedD64D128EvidenceTableError("native d128 proof object unexpectedly present")

    sources = [
        source_descriptor(D64_BLOCK_RECEIPT, "d64_block_receipt_json", d64_block_raw, d64_block),
        source_descriptor(D64_EXTERNAL_SNARK, "d64_external_snark_json", d64_snark_raw, d64_snark),
        source_descriptor(D128_BLOCK_RECEIPT, "d128_block_receipt_json", d128_block_raw, d128_block),
        source_descriptor(ONE_BLOCK_SURFACE, "one_block_surface_json", surface_raw, surface),
        source_descriptor(PACKAGE_ACCOUNTING, "one_block_package_accounting_json", package_raw, package),
        source_descriptor(D128_GAP_ACCOUNTING, "d128_native_block_gap_accounting_json", gap_raw, gap),
        source_descriptor(PUBLISHED_ZKML_NUMBERS, "published_zkml_numbers_tsv", published_raw, published_rows),
    ]
    return d64_block, d64_snark, d128_block, surface, package, gap, nanozk, sources


def _row(
    row_id: str,
    system: str,
    dimension_or_scope: str,
    backend_family: str,
    object_class: str,
    evidence_status: str,
    workload_scope: str,
    metric: str,
    value: int | float | None,
    unit: str,
    source_path: pathlib.Path,
    comparison_boundary: str,
    *,
    ratio_vs_d64_rows: float | None = None,
    ratio_vs_d128_rows: float | None = None,
    ratio_vs_source_statement_chain: float | None = None,
    ratio_vs_nanozk_reported: float | None = None,
) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "system": system,
        "dimension_or_scope": dimension_or_scope,
        "backend_family": backend_family,
        "object_class": object_class,
        "evidence_status": evidence_status,
        "workload_scope": workload_scope,
        "metric": metric,
        "value": value,
        "unit": unit,
        "ratio_vs_d64_checked_rows": ratio_vs_d64_rows,
        "ratio_vs_d128_checked_rows": ratio_vs_d128_rows,
        "ratio_vs_source_statement_chain": ratio_vs_source_statement_chain,
        "ratio_vs_nanozk_reported": ratio_vs_nanozk_reported,
        "source_path": str(source_path.relative_to(ROOT)),
        "comparison_boundary": comparison_boundary,
    }


def evidence_rows() -> list[dict[str, Any]]:
    return [
        _row(
            "local_d64_stwo_receipt_chain_rows",
            "provable-transformer-vm",
            "d64",
            "Stwo native proof-backed receipt chain",
            "stwo_native_receipt_chain_rows",
            "locally_checked_artifact",
            "six-slice RMSNorm/SwiGLU/residual block receipt composition",
            "checked rows",
            EXPECTED_D64_ROWS,
            "rows",
            D64_BLOCK_RECEIPT,
            "row-count scaling evidence only; not one compressed proof object",
        ),
        _row(
            "local_d128_stwo_receipt_chain_rows",
            "provable-transformer-vm",
            "d128",
            "Stwo native proof-backed receipt chain",
            "stwo_native_receipt_chain_rows",
            "locally_checked_artifact",
            "six-slice RMSNorm/SwiGLU/residual block receipt composition",
            "checked rows",
            EXPECTED_D128_ROWS,
            "rows",
            D128_BLOCK_RECEIPT,
            "row-count scaling evidence only; not proof-size benchmark evidence",
            ratio_vs_d64_rows=EXPECTED_D128_OVER_D64_RATIO,
        ),
        _row(
            "local_d128_attention_statement_chain_rows",
            "provable-transformer-vm",
            "d128 attention-derived block surface",
            "source-backed statement chain over Stwo-derived block receipts",
            "source_statement_chain_rows",
            "locally_checked_artifact",
            "attention-derived d128 block statement chain",
            "statement-chain rows",
            EXPECTED_D128_CHAIN_ROWS,
            "rows",
            ONE_BLOCK_SURFACE,
            "statement-binding shape evidence; not proof bytes",
            ratio_vs_d64_rows=round(EXPECTED_D128_CHAIN_ROWS / EXPECTED_D64_ROWS, 6),
            ratio_vs_d128_rows=EXPECTED_D128_CHAIN_VS_D128_RATIO,
        ),
        _row(
            "local_d128_source_statement_chain_bytes",
            "provable-transformer-vm",
            "d128 attention-derived block surface",
            "source-backed statement chain over Stwo-derived block receipts",
            "source_statement_chain_artifact_bytes",
            "locally_checked_artifact",
            "attention-derived d128 block statement chain",
            "source artifact bytes",
            EXPECTED_SOURCE_CHAIN_BYTES,
            "bytes",
            PACKAGE_ACCOUNTING,
            "source artifact size; not a proof object",
            ratio_vs_nanozk_reported=EXPECTED_SOURCE_CHAIN_VS_NANOZK,
        ),
        _row(
            "local_d128_compressed_statement_chain_bytes",
            "provable-transformer-vm",
            "d128 attention-derived block surface",
            "compressed transcript handle over source-backed statement chain",
            "compressed_statement_chain_artifact_bytes",
            "locally_checked_artifact",
            "attention-derived d128 block statement chain",
            "compressed artifact bytes",
            EXPECTED_COMPRESSED_CHAIN_BYTES,
            "bytes",
            PACKAGE_ACCOUNTING,
            "compressed transcript handle; not a proof object",
            ratio_vs_source_statement_chain=EXPECTED_COMPRESSED_CHAIN_RATIO_VS_SOURCE,
            ratio_vs_nanozk_reported=EXPECTED_COMPRESSED_CHAIN_VS_NANOZK,
        ),
        _row(
            "local_d64_external_snark_statement_receipt_proof_bytes",
            "provable-transformer-vm",
            "d64",
            "external snarkjs/Groth16 statement receipt",
            "external_snark_statement_receipt_proof_bytes",
            "locally_checked_artifact",
            "statement receipt over d64 nested-verifier contract fields",
            "proof bytes",
            EXPECTED_D64_SNARK_PROOF_BYTES,
            "bytes",
            D64_EXTERNAL_SNARK,
            "external SNARK receipt; not Stwo-native recursion",
            ratio_vs_nanozk_reported=round(EXPECTED_D64_SNARK_PROOF_BYTES / EXPECTED_NANOZK_BLOCK_BYTES, 6),
        ),
        _row(
            "local_d128_external_snark_statement_receipt_proof_bytes",
            "provable-transformer-vm",
            "d128 attention-derived block surface",
            "external snarkjs/Groth16 statement receipt",
            "external_snark_statement_receipt_proof_bytes",
            "locally_checked_artifact",
            "statement receipt over attention-derived d128 input contract",
            "proof bytes",
            EXPECTED_SNARK_PROOF_BYTES,
            "bytes",
            PACKAGE_ACCOUNTING,
            "external SNARK receipt; not a native d128 block proof",
            ratio_vs_nanozk_reported=EXPECTED_SNARK_PROOF_VS_NANOZK,
        ),
        _row(
            "local_d128_package_without_vk_bytes",
            "provable-transformer-vm",
            "d128 attention-derived block surface",
            "compressed statement chain plus external SNARK proof and public signals",
            "verifier_facing_package_without_vk_bytes",
            "locally_checked_artifact",
            "attention-derived d128 executable package",
            "package bytes without VK",
            EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
            "bytes",
            PACKAGE_ACCOUNTING,
            "interesting compact package signal; not matched proof-size evidence",
            ratio_vs_source_statement_chain=EXPECTED_PACKAGE_WITHOUT_VK_RATIO_VS_SOURCE,
            ratio_vs_nanozk_reported=EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK,
        ),
        _row(
            "local_d128_package_with_vk_bytes",
            "provable-transformer-vm",
            "d128 attention-derived block surface",
            "compressed statement chain plus external SNARK proof, public signals, and VK",
            "verifier_facing_package_with_vk_bytes",
            "locally_checked_artifact",
            "attention-derived d128 executable package",
            "package bytes with VK",
            EXPECTED_PACKAGE_WITH_VK_BYTES,
            "bytes",
            PACKAGE_ACCOUNTING,
            "self-contained package accounting; not matched proof-size evidence",
            ratio_vs_source_statement_chain=EXPECTED_PACKAGE_WITH_VK_RATIO_VS_SOURCE,
            ratio_vs_nanozk_reported=EXPECTED_PACKAGE_WITH_VK_VS_NANOZK,
        ),
        _row(
            "external_nanozk_reported_transformer_block_proof_bytes",
            "NANOZK",
            "GPT-2-scale d768 block",
            "Halo2 IPA SNARK plus lookups",
            "paper_reported_external_proof_bytes",
            "paper_reported_not_locally_reproduced",
            "per-layer transformer block proof",
            "reported proof bytes",
            EXPECTED_NANOZK_BLOCK_BYTES,
            "decimal_bytes",
            PUBLISHED_ZKML_NUMBERS,
            "external context only; not locally reproduced",
        ),
        _row(
            "missing_native_d128_block_proof_object",
            "provable-transformer-vm",
            "d128",
            "Stwo native aggregated transformer-block proof",
            "missing_native_stark_block_proof_bytes",
            "missing_required_for_matched_benchmark",
            "single native or matched d128 transformer-block proof object",
            "native proof bytes",
            None,
            "bytes",
            D128_GAP_ACCOUNTING,
            "required before any NANOZK proof-size comparison claim",
        ),
    ]


def validate_rows(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 11:
        raise MatchedD64D128EvidenceTableError("unexpected evidence row count")
    row_ids = [row.get("row_id") for row in rows]
    if len(set(row_ids)) != len(row_ids):
        raise MatchedD64D128EvidenceTableError("duplicate row_id")
    for row in rows:
        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                raise MatchedD64D128EvidenceTableError(f"evidence row missing field: {field}")
            if field != "value" and row[field] in ("", None):
                raise MatchedD64D128EvidenceTableError(f"evidence row has empty field: {field}")
    by_id = {row["row_id"]: row for row in rows}
    package = by_id["local_d128_package_without_vk_bytes"]
    if package["object_class"] != "verifier_facing_package_without_vk_bytes":
        raise MatchedD64D128EvidenceTableError("package row object-class drift")
    if package["value"] != EXPECTED_PACKAGE_WITHOUT_VK_BYTES:
        raise MatchedD64D128EvidenceTableError("package row value drift")
    if package["ratio_vs_nanozk_reported"] != EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK:
        raise MatchedD64D128EvidenceTableError("package row NANOZK ratio drift")
    if "not matched proof-size evidence" not in package["comparison_boundary"]:
        raise MatchedD64D128EvidenceTableError("package row boundary drift")
    nanozk = by_id["external_nanozk_reported_transformer_block_proof_bytes"]
    if nanozk["evidence_status"] != "paper_reported_not_locally_reproduced":
        raise MatchedD64D128EvidenceTableError("NANOZK reproduction status drift")
    missing = by_id["missing_native_d128_block_proof_object"]
    if missing["value"] is not None:
        raise MatchedD64D128EvidenceTableError("missing native proof row must stay null")


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["row_id"]: row for row in rows}
    summary = {
        "table_row_count": len(rows),
        "locally_checked_row_count": sum(1 for row in rows if row["evidence_status"] == "locally_checked_artifact"),
        "paper_reported_external_row_count": sum(
            1 for row in rows if row["evidence_status"] == "paper_reported_not_locally_reproduced"
        ),
        "missing_required_row_count": sum(
            1 for row in rows if row["evidence_status"] == "missing_required_for_matched_benchmark"
        ),
        "d64_checked_rows": EXPECTED_D64_ROWS,
        "d128_checked_rows": EXPECTED_D128_ROWS,
        "d128_over_d64_checked_row_ratio": EXPECTED_D128_OVER_D64_RATIO,
        "attention_derived_statement_chain_rows": EXPECTED_D128_CHAIN_ROWS,
        "attention_derived_statement_chain_extra_rows_vs_d128_receipt": EXPECTED_D128_CHAIN_EXTRA_ROWS,
        "attention_derived_statement_chain_vs_d128_receipt_ratio": EXPECTED_D128_CHAIN_VS_D128_RATIO,
        "source_statement_chain_bytes": EXPECTED_SOURCE_CHAIN_BYTES,
        "compressed_statement_chain_bytes": EXPECTED_COMPRESSED_CHAIN_BYTES,
        "d128_external_snark_proof_bytes": EXPECTED_SNARK_PROOF_BYTES,
        "d128_external_snark_public_signal_bytes": EXPECTED_SNARK_PUBLIC_SIGNAL_BYTES,
        "d128_external_snark_verification_key_bytes": EXPECTED_SNARK_VERIFICATION_KEY_BYTES,
        "d128_package_without_vk_bytes": EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
        "d128_package_without_vk_vs_nanozk_reported_ratio": EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK,
        "d128_package_with_vk_bytes": EXPECTED_PACKAGE_WITH_VK_BYTES,
        "d128_package_with_vk_vs_nanozk_reported_ratio": EXPECTED_PACKAGE_WITH_VK_VS_NANOZK,
        "nanozk_reported_block_proof_bytes_decimal": EXPECTED_NANOZK_BLOCK_BYTES,
        "native_d128_block_proof_bytes": by_id["missing_native_d128_block_proof_object"]["value"],
        "matched_benchmark_claim_allowed": False,
        "stark_native_claim_allowed": (
            "Stwo-native d64/d128 receipt-chain rows exist and scale to d128; proof-size claims do not."
        ),
        "snark_receipt_interpretation": (
            "Groth16 rows are external statement receipts used for binding/package accounting, not STARK-native proof objects."
        ),
        "go_result": "GO for a matched evidence table that separates object classes and comparison boundaries.",
        "no_go_result": "NO-GO for claiming a native d128 proof-size win or matched NANOZK benchmark.",
    }
    if summary["table_row_count"] != 11:
        raise MatchedD64D128EvidenceTableError("summary row-count drift")
    if summary["locally_checked_row_count"] != 9:
        raise MatchedD64D128EvidenceTableError("summary local-row count drift")
    if summary["paper_reported_external_row_count"] != 1:
        raise MatchedD64D128EvidenceTableError("summary external-row count drift")
    if summary["missing_required_row_count"] != 1:
        raise MatchedD64D128EvidenceTableError("summary missing-row count drift")
    return summary


def build_payload_core() -> dict[str, Any]:
    _d64_block, _d64_snark, _d128_block, _surface, _package, _gap, _nanozk, sources = checked_sources()
    rows = evidence_rows()
    validate_rows(rows)
    summary = build_summary(rows)
    return {
        "schema": SCHEMA,
        "issue": 570,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": sources,
        "evidence_rows": rows,
        "summary": summary,
        "claim_guard": {
            "matched_benchmark_claim_allowed": False,
            "native_d128_proof_size_claim_allowed": False,
            "package_bytes_are_proof_bytes": False,
            "reason": (
                "the compact 4,752-byte row is a verifier-facing package over an external SNARK statement "
                "receipt and compressed statement-chain handle, not a native Stwo d128 proof object"
            ),
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }


def validate_payload_core(payload: dict[str, Any], *, expected: dict[str, Any] | None = None) -> None:
    base = expected if expected is not None else build_payload_core()
    if payload != base:
        if not isinstance(payload, dict):
            raise MatchedD64D128EvidenceTableError("payload must be object")
        if payload.get("schema") != SCHEMA:
            raise MatchedD64D128EvidenceTableError("schema drift")
        if payload.get("decision") != DECISION:
            raise MatchedD64D128EvidenceTableError("decision drift")
        if payload.get("result") != RESULT:
            raise MatchedD64D128EvidenceTableError("result drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise MatchedD64D128EvidenceTableError("claim boundary drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise MatchedD64D128EvidenceTableError("non-claims drift")
        if payload.get("source_artifacts") != base["source_artifacts"]:
            raise MatchedD64D128EvidenceTableError("source artifact drift")
        if payload.get("summary") != base["summary"]:
            raise MatchedD64D128EvidenceTableError("summary drift")
        if payload.get("claim_guard") != base["claim_guard"]:
            raise MatchedD64D128EvidenceTableError("claim guard drift")
        if payload.get("evidence_rows") != base["evidence_rows"]:
            rows = _list(payload.get("evidence_rows"), "evidence_rows")
            validate_rows(rows)
            raise MatchedD64D128EvidenceTableError("evidence row drift")
        raise MatchedD64D128EvidenceTableError("payload drift")


def mutation_cases(core: dict[str, Any], *, expected_core: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    def by_id(payload: dict[str, Any], row_id: str) -> dict[str, Any]:
        return next(row for row in payload["evidence_rows"] if row["row_id"] == row_id)

    def mutate(name: str, payload: dict[str, Any]) -> None:
        if name == "package_without_vk_promoted_to_native_proof":
            by_id(payload, "local_d128_package_without_vk_bytes")["object_class"] = "native_stark_block_proof_bytes"
        elif name == "matched_benchmark_claim_enabled":
            payload["claim_guard"]["matched_benchmark_claim_allowed"] = True
        elif name == "nanozk_reproduced_locally_without_source":
            by_id(payload, "external_nanozk_reported_transformer_block_proof_bytes")[
                "evidence_status"
            ] = "locally_reproduced"
        elif name == "native_d128_proof_size_smuggled":
            by_id(payload, "missing_native_d128_block_proof_object")["value"] = 4096
        elif name == "d64_row_drift":
            by_id(payload, "local_d64_stwo_receipt_chain_rows")["value"] = 1
        elif name == "d128_row_drift":
            by_id(payload, "local_d128_stwo_receipt_chain_rows")["value"] = 1
        elif name == "package_without_vk_drift":
            by_id(payload, "local_d128_package_without_vk_bytes")["value"] = 1
        elif name == "source_artifact_hash_drift":
            payload["source_artifacts"][0]["file_sha256"] = "0" * 64
        elif name == "row_object_class_removed":
            by_id(payload, "local_d128_package_without_vk_bytes").pop("object_class")
        elif name == "non_claim_removed":
            payload["non_claims"].remove("not a NANOZK proof-size win")
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
        raise MatchedD64D128EvidenceTableError("payload must be object")
    candidate = {key: value for key, value in payload.items() if key != "payload_commitment"}
    if candidate != base:
        if payload.get("schema") != SCHEMA:
            raise MatchedD64D128EvidenceTableError("schema drift")
        if payload.get("decision") != DECISION:
            raise MatchedD64D128EvidenceTableError("decision drift")
        if payload.get("result") != RESULT:
            raise MatchedD64D128EvidenceTableError("result drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise MatchedD64D128EvidenceTableError("claim boundary drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise MatchedD64D128EvidenceTableError("non-claims drift")
        if payload.get("all_mutations_rejected") is not True:
            raise MatchedD64D128EvidenceTableError("mutation rejection drift")
        if _dict(payload.get("claim_guard"), "claim_guard").get("matched_benchmark_claim_allowed") is not False:
            raise MatchedD64D128EvidenceTableError("matched benchmark guard drift")
        raise MatchedD64D128EvidenceTableError("payload drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise MatchedD64D128EvidenceTableError("payload commitment drift")


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
    writer.writerow(
        [
            "row_id",
            "system",
            "dimension_or_scope",
            "backend_family",
            "object_class",
            "evidence_status",
            "metric",
            "value",
            "unit",
            "ratio_vs_d64_checked_rows",
            "ratio_vs_d128_checked_rows",
            "ratio_vs_source_statement_chain",
            "ratio_vs_nanozk_reported",
            "comparison_boundary",
        ]
    )
    for row in payload["evidence_rows"]:
        writer.writerow(
            [
                row["row_id"],
                row["system"],
                row["dimension_or_scope"],
                row["backend_family"],
                row["object_class"],
                row["evidence_status"],
                row["metric"],
                row["value"] if row["value"] is not None else "",
                row["unit"],
                row["ratio_vs_d64_checked_rows"] if row["ratio_vs_d64_checked_rows"] is not None else "",
                row["ratio_vs_d128_checked_rows"] if row["ratio_vs_d128_checked_rows"] is not None else "",
                row["ratio_vs_source_statement_chain"] if row["ratio_vs_source_statement_chain"] is not None else "",
                row["ratio_vs_nanozk_reported"] if row["ratio_vs_nanozk_reported"] is not None else "",
                row["comparison_boundary"],
            ]
        )
    return out.getvalue()


def _assert_no_repo_symlink_components(path: pathlib.Path, label: str) -> None:
    absolute = path if path.is_absolute() else ROOT / path
    try:
        relative = absolute.relative_to(ROOT)
    except ValueError as err:
        raise MatchedD64D128EvidenceTableError(f"{label} must stay inside repository") from err
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise MatchedD64D128EvidenceTableError(f"{label} must not include symlink components")


def _assert_output_path(path: pathlib.Path, label: str) -> pathlib.Path:
    raw = str(path).replace("\\", "/")
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise MatchedD64D128EvidenceTableError(f"{label} must be repo-relative")
    if pathlib.PurePosixPath(*relative.parts[:3]) != pathlib.PurePosixPath("docs/engineering/evidence"):
        raise MatchedD64D128EvidenceTableError(f"{label} must stay under docs/engineering/evidence")
    full = ROOT.joinpath(*relative.parts)
    _assert_no_repo_symlink_components(full.parent, label)
    if full.is_symlink():
        raise MatchedD64D128EvidenceTableError(f"{label} must not include symlink components")
    return full


def _directory_identity(path: pathlib.Path, label: str) -> tuple[int, int]:
    try:
        path_stat = path.lstat()
    except OSError as err:
        raise MatchedD64D128EvidenceTableError(f"{label} parent directory is unavailable: {err}") from err
    if stat_module.S_ISLNK(path_stat.st_mode) or not stat_module.S_ISDIR(path_stat.st_mode):
        raise MatchedD64D128EvidenceTableError(f"{label} parent must be a real directory")
    return (path_stat.st_dev, path_stat.st_ino)


def _assert_directory_identity(path: pathlib.Path, identity: tuple[int, int], label: str) -> None:
    _assert_no_repo_symlink_components(path, label)
    if _directory_identity(path, label) != identity:
        raise MatchedD64D128EvidenceTableError(f"{label} parent directory changed while writing")


def _open_stable_directory(path: pathlib.Path, label: str) -> tuple[int, tuple[int, int]]:
    _assert_no_repo_symlink_components(path, label)
    if not path.exists():
        raise MatchedD64D128EvidenceTableError(f"{label} parent directory must already exist")
    identity = _directory_identity(path, label)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as err:
        raise MatchedD64D128EvidenceTableError(f"failed to open {label} parent directory: {err}") from err
    try:
        fd_stat = os.fstat(fd)
        if not stat_module.S_ISDIR(fd_stat.st_mode):
            raise MatchedD64D128EvidenceTableError(f"{label} parent must be a real directory")
        if (fd_stat.st_dev, fd_stat.st_ino) != identity:
            raise MatchedD64D128EvidenceTableError(f"{label} parent directory changed while opening")
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
        raise MatchedD64D128EvidenceTableError("at least one output path is required")
    if len(outputs) == 2 and os.path.abspath(outputs[0][0]).casefold() == os.path.abspath(outputs[1][0]).casefold():
        raise MatchedD64D128EvidenceTableError("json and tsv output paths must differ")

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
                raise MatchedD64D128EvidenceTableError(f"{label} must not include symlink components")
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
                raise MatchedD64D128EvidenceTableError(f"failed to create unique temporary output for {label}")
            with os.fdopen(file_fd, "wb") as handle:
                file_fd = None
                handle.write(contents)
                handle.flush()
                os.fsync(handle.fileno())
            _assert_directory_identity(path.parent, identity, label)
            return (path.parent / temp_name, temp_name, parent_fd, identity)
        except Exception:
            if file_fd is not None:
                try:
                    os.close(file_fd)
                except OSError as cleanup_error:
                    print(f"warning: failed to close temporary output fd: {cleanup_error}", file=sys.stderr)
            try:
                if temp_name is not None:
                    try:
                        os.unlink(temp_name, dir_fd=parent_fd)
                    except FileNotFoundError:
                        pass
                    except OSError as cleanup_error:
                        print(f"warning: failed to remove temporary output: {cleanup_error}", file=sys.stderr)
                    try:
                        os.fsync(parent_fd)
                    except OSError as cleanup_error:
                        print(f"warning: failed to fsync output directory during cleanup: {cleanup_error}", file=sys.stderr)
            finally:
                try:
                    os.close(parent_fd)
                except OSError as cleanup_error:
                    print(f"warning: failed to close output directory fd during cleanup: {cleanup_error}", file=sys.stderr)
            raise

    def replace_temp(temp: tuple[pathlib.Path, str, int, tuple[int, int]], path: pathlib.Path, label: str) -> None:
        _tmp_path, temp_name, parent_fd, identity = temp
        _assert_directory_identity(path.parent, identity, label)
        if path.is_symlink():
            raise MatchedD64D128EvidenceTableError(f"{label} must not include symlink components")
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
                raise MatchedD64D128EvidenceTableError("rollback output path must not include symlink components")
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
                    raise MatchedD64D128EvidenceTableError("output path must not include symlink components")
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
        raise MatchedD64D128EvidenceTableError(f"failed to write output path: {detail}") from write_error


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
