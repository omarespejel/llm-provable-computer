#!/usr/bin/env python3
"""Account for the executable one-block statement package without overclaiming."""

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
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import zkai_one_transformer_block_surface_gate as SURFACE  # noqa: E402


EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SCORECARD = EVIDENCE_DIR / "zkai-one-transformer-block-surface-2026-05.json"
COMPRESSION = EVIDENCE_DIR / "zkai-attention-derived-d128-statement-chain-compression-2026-05.json"
SNARK_RECEIPT = EVIDENCE_DIR / "zkai-attention-derived-d128-snark-statement-receipt-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-one-block-executable-package-accounting-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-one-block-executable-package-accounting-2026-05.tsv"

SCHEMA = "zkai-one-block-executable-package-accounting-v1"
DECISION = "GO_ONE_BLOCK_EXECUTABLE_PACKAGE_ACCOUNTING_NO_GO_NATIVE_PROOF_SIZE"
RESULT = "GO_EXTERNAL_RECEIPT_PACKAGE_ACCOUNTING_NO_GO_NATIVE_BLOCK_PROOF"
CLAIM_BOUNDARY = (
    "EXTERNAL_STATEMENT_RECEIPT_PACKAGE_ACCOUNTING_NOT_NATIVE_BLOCK_PROOF_"
    "NOT_RECURSION_NOT_TIMING_NOT_PRODUCTION_SETUP"
)

EXPECTED_SOURCE_CHAIN_BYTES = 14_624
EXPECTED_COMPRESSED_ARTIFACT_BYTES = 2_559
EXPECTED_PROOF_BYTES = 807
EXPECTED_PUBLIC_SIGNALS_BYTES = 1_386
EXPECTED_VERIFICATION_KEY_BYTES = 5_856
EXPECTED_PACKAGE_WITHOUT_VK_BYTES = 4_752
EXPECTED_PACKAGE_WITH_VK_BYTES = 10_608
EXPECTED_PACKAGE_WITHOUT_VK_RATIO = 0.324945
EXPECTED_PACKAGE_WITH_VK_RATIO = 0.725383
EXPECTED_SAVING_WITHOUT_VK_BYTES = 9_872
EXPECTED_SAVING_WITH_VK_BYTES = 4_016
EXPECTED_COMPRESSED_RATIO = 0.174986
EXPECTED_STATEMENT_ROWS = 199_553
EXPECTED_RECEIPT_MUTATIONS = 40
EXPECTED_PUBLIC_SIGNAL_COUNT = 17
EXPECTED_BLOCK_STATEMENT = "blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5"
EXPECTED_INPUT_CONTRACT = "blake2b-256:503fb256305f03a8da20b6872753234dbf776bb1b81044485949b4072152ed39"
EXPECTED_RECEIPT_COMMITMENT = "blake2b-256:b9448afdbce5b2eac524274fa8be99595ca3fae933931300ff38c9fba3e52c1d"

NON_CLAIMS = [
    "not a native d128 transformer-block proof",
    "not recursive aggregation",
    "not proof-carrying data",
    "not verification of the six Stwo slice proofs inside Groth16",
    "not native proof-size evidence for a fused route",
    "not verifier-time evidence",
    "not proof-generation-time evidence",
    "not a production trusted setup",
    "not a matched NANOZK or Jolt benchmark",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_one_block_executable_package_accounting_gate.py --write-json docs/engineering/evidence/zkai-one-block-executable-package-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-one-block-executable-package-accounting-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_one_block_executable_package_accounting_gate.py scripts/tests/test_zkai_one_block_executable_package_accounting_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_one_block_executable_package_accounting_gate",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

MUTATION_NAMES = (
    "source_chain_bytes_drift",
    "compressed_artifact_bytes_drift",
    "proof_bytes_drift",
    "public_signals_bytes_drift",
    "verification_key_bytes_drift",
    "package_without_vk_bytes_drift",
    "package_with_vk_ratio_drift",
    "source_artifact_hash_drift",
    "claim_boundary_native_overclaim",
    "non_claim_removed",
    "timing_metric_smuggled",
    "result_changed_to_native_proof",
)


class OneBlockPackageAccountingError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise OneBlockPackageAccountingError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise OneBlockPackageAccountingError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OneBlockPackageAccountingError(f"{field} must be object")
    return value


def _int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise OneBlockPackageAccountingError(f"{field} must be integer")
    return value


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = SURFACE.read_source_bytes(path, str(path.relative_to(ROOT)))
        payload = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except Exception as err:
        raise OneBlockPackageAccountingError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise OneBlockPackageAccountingError(f"source evidence must be object: {path}")
    return payload, raw


def source_descriptor(path: pathlib.Path, kind: str, raw: bytes, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": str(path.relative_to(ROOT)),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        "schema": payload.get("schema"),
        "decision": payload.get("decision"),
    }


def checked_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    scorecard, scorecard_raw = load_json(SCORECARD)
    compression, compression_raw = load_json(COMPRESSION)
    snark, snark_raw = load_json(SNARK_RECEIPT)

    scorecard_summary = _dict(scorecard.get("summary"), "scorecard.summary")
    compression_summary = _dict(compression.get("summary"), "compression.summary")
    snark_source = _dict(snark.get("source_route_metrics"), "snark.source_route_metrics")
    snark_receipt = _dict(snark.get("receipt_metrics"), "snark.receipt_metrics")
    snark_statement = _dict(snark.get("statement_receipt"), "snark.statement_receipt")

    if scorecard.get("schema") != "zkai-one-transformer-block-surface-v1":
        raise OneBlockPackageAccountingError("scorecard schema drift")
    if scorecard.get("decision") != "GO_ONE_TRANSFORMER_BLOCK_SURFACE_NO_GO_MATCHED_LAYER_PROOF":
        raise OneBlockPackageAccountingError("scorecard decision drift")
    if scorecard_summary.get("attention_derived_d128_block_statement_commitment") != EXPECTED_BLOCK_STATEMENT:
        raise OneBlockPackageAccountingError("scorecard block statement drift")
    if scorecard_summary.get("attention_derived_d128_input_contract_commitment") != EXPECTED_INPUT_CONTRACT:
        raise OneBlockPackageAccountingError("scorecard input contract drift")
    if scorecard_summary.get("attention_derived_d128_snark_receipt_commitment") != EXPECTED_RECEIPT_COMMITMENT:
        raise OneBlockPackageAccountingError("scorecard receipt commitment drift")
    if scorecard_summary.get("attention_derived_d128_statement_chain_compressed_ratio") != EXPECTED_COMPRESSED_RATIO:
        raise OneBlockPackageAccountingError("scorecard compressed ratio drift")

    if compression.get("schema") != "zkai-attention-derived-d128-statement-chain-compression-gate-v1":
        raise OneBlockPackageAccountingError("compression schema drift")
    if compression.get("decision") != "GO_ATTENTION_DERIVED_D128_STATEMENT_CHAIN_TRANSCRIPT_COMPRESSION":
        raise OneBlockPackageAccountingError("compression decision drift")
    if compression.get("result") != "GO_COMPRESSED_VERIFIER_FACING_STATEMENT_CHAIN_ARTIFACT_NO_GO_PROOF_SIZE":
        raise OneBlockPackageAccountingError("compression result drift")
    if compression_summary.get("source_chain_artifact_bytes") != EXPECTED_SOURCE_CHAIN_BYTES:
        raise OneBlockPackageAccountingError("compression source bytes drift")
    if compression_summary.get("compressed_artifact_bytes") != EXPECTED_COMPRESSED_ARTIFACT_BYTES:
        raise OneBlockPackageAccountingError("compression compressed bytes drift")
    if compression_summary.get("compressed_to_source_ratio") != EXPECTED_COMPRESSED_RATIO:
        raise OneBlockPackageAccountingError("compression ratio drift")
    if compression_summary.get("source_relation_rows") != EXPECTED_STATEMENT_ROWS:
        raise OneBlockPackageAccountingError("compression relation rows drift")

    if snark.get("schema") != "zkai-attention-derived-d128-snark-statement-receipt-gate-v1":
        raise OneBlockPackageAccountingError("SNARK receipt schema drift")
    if snark.get("decision") != "GO_ATTENTION_DERIVED_D128_SNARK_STATEMENT_RECEIPT_FOR_OUTER_PROOF_INPUT_CONTRACT":
        raise OneBlockPackageAccountingError("SNARK receipt decision drift")
    if snark.get("result") != "GO":
        raise OneBlockPackageAccountingError("SNARK receipt result drift")
    if snark.get("all_mutations_rejected") is not True or snark.get("case_count") != EXPECTED_RECEIPT_MUTATIONS:
        raise OneBlockPackageAccountingError("SNARK receipt mutation rejection drift")
    if snark_source.get("source_chain_artifact_bytes") != EXPECTED_SOURCE_CHAIN_BYTES:
        raise OneBlockPackageAccountingError("SNARK source bytes drift")
    if snark_source.get("compressed_artifact_bytes") != EXPECTED_COMPRESSED_ARTIFACT_BYTES:
        raise OneBlockPackageAccountingError("SNARK compressed bytes drift")
    if snark_source.get("compressed_to_source_ratio") != EXPECTED_COMPRESSED_RATIO:
        raise OneBlockPackageAccountingError("SNARK compressed ratio drift")
    if snark_source.get("source_relation_rows") != EXPECTED_STATEMENT_ROWS:
        raise OneBlockPackageAccountingError("SNARK relation rows drift")
    if snark_source.get("block_statement_commitment") != EXPECTED_BLOCK_STATEMENT:
        raise OneBlockPackageAccountingError("SNARK block statement drift")
    if snark_source.get("input_contract_commitment") != EXPECTED_INPUT_CONTRACT:
        raise OneBlockPackageAccountingError("SNARK input contract drift")
    if snark_statement.get("receipt_commitment") != EXPECTED_RECEIPT_COMMITMENT:
        raise OneBlockPackageAccountingError("SNARK receipt commitment drift")
    if snark_receipt.get("proof_size_bytes") != EXPECTED_PROOF_BYTES:
        raise OneBlockPackageAccountingError("SNARK proof bytes drift")
    if snark_receipt.get("public_signals_bytes") != EXPECTED_PUBLIC_SIGNALS_BYTES:
        raise OneBlockPackageAccountingError("SNARK public signals bytes drift")
    if snark_receipt.get("verification_key_bytes") != EXPECTED_VERIFICATION_KEY_BYTES:
        raise OneBlockPackageAccountingError("SNARK verification key bytes drift")
    if snark_receipt.get("public_signal_count") != EXPECTED_PUBLIC_SIGNAL_COUNT:
        raise OneBlockPackageAccountingError("SNARK public signal count drift")
    if snark_receipt.get("verifier_time_ms") is not None or snark_receipt.get("proof_generation_time_ms") is not None:
        raise OneBlockPackageAccountingError("SNARK timing metric must not be claimed")

    sources = [
        source_descriptor(SCORECARD, "one_block_scorecard_json", scorecard_raw, scorecard),
        source_descriptor(COMPRESSION, "statement_chain_compression_json", compression_raw, compression),
        source_descriptor(SNARK_RECEIPT, "snark_statement_receipt_json", snark_raw, snark),
    ]
    return scorecard, compression, snark, sources


def package_summary(compression: dict[str, Any], snark: dict[str, Any]) -> dict[str, Any]:
    compression_summary = _dict(compression.get("summary"), "compression.summary")
    snark_receipt = _dict(snark.get("receipt_metrics"), "snark.receipt_metrics")
    source_bytes = _int(compression_summary.get("source_chain_artifact_bytes"), "source bytes")
    compressed_bytes = _int(compression_summary.get("compressed_artifact_bytes"), "compressed bytes")
    proof_bytes = _int(snark_receipt.get("proof_size_bytes"), "proof bytes")
    public_bytes = _int(snark_receipt.get("public_signals_bytes"), "public signal bytes")
    vk_bytes = _int(snark_receipt.get("verification_key_bytes"), "verification key bytes")
    package_without_vk = compressed_bytes + proof_bytes + public_bytes
    package_with_vk = package_without_vk + vk_bytes
    saving_without_vk = source_bytes - package_without_vk
    saving_with_vk = source_bytes - package_with_vk
    summary = {
        "source_statement_chain_bytes": source_bytes,
        "compressed_statement_chain_bytes": compressed_bytes,
        "snark_proof_bytes": proof_bytes,
        "snark_public_signals_bytes": public_bytes,
        "snark_verification_key_bytes": vk_bytes,
        "package_without_vk_bytes": package_without_vk,
        "package_without_vk_ratio_vs_source": round(package_without_vk / source_bytes, 6),
        "package_without_vk_saving_bytes": saving_without_vk,
        "package_without_vk_saving_share": round(saving_without_vk / source_bytes, 6),
        "package_with_vk_bytes": package_with_vk,
        "package_with_vk_ratio_vs_source": round(package_with_vk / source_bytes, 6),
        "package_with_vk_saving_bytes": saving_with_vk,
        "package_with_vk_saving_share": round(saving_with_vk / source_bytes, 6),
        "statement_chain_rows": EXPECTED_STATEMENT_ROWS,
        "receipt_public_signal_count": EXPECTED_PUBLIC_SIGNAL_COUNT,
        "receipt_mutations_rejected": EXPECTED_RECEIPT_MUTATIONS,
        "strongest_claim": "The external executable one-block statement package is smaller than the source statement-chain artifact both without and with the reusable verification key counted.",
        "no_go_result": "NO-GO for native block proof-size evidence, recursion, verifier-time evidence, production setup, or matched competitor benchmark.",
    }
    expected = {
        "package_without_vk_bytes": EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
        "package_without_vk_ratio_vs_source": EXPECTED_PACKAGE_WITHOUT_VK_RATIO,
        "package_without_vk_saving_bytes": EXPECTED_SAVING_WITHOUT_VK_BYTES,
        "package_with_vk_bytes": EXPECTED_PACKAGE_WITH_VK_BYTES,
        "package_with_vk_ratio_vs_source": EXPECTED_PACKAGE_WITH_VK_RATIO,
        "package_with_vk_saving_bytes": EXPECTED_SAVING_WITH_VK_BYTES,
    }
    for key, value in expected.items():
        if summary[key] != value:
            raise OneBlockPackageAccountingError(f"package summary drift: {key}")
    return summary


def package_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "surface": "source statement-chain artifact",
            "bytes": summary["source_statement_chain_bytes"],
            "ratio_vs_source": 1.0,
            "saving_bytes": 0,
            "scope": "source JSON statement chain",
        },
        {
            "surface": "compressed statement-chain artifact",
            "bytes": summary["compressed_statement_chain_bytes"],
            "ratio_vs_source": EXPECTED_COMPRESSED_RATIO,
            "saving_bytes": EXPECTED_SOURCE_CHAIN_BYTES - EXPECTED_COMPRESSED_ARTIFACT_BYTES,
            "scope": "verifier-facing transcript handle, not proof",
        },
        {
            "surface": "compressed artifact plus proof plus public signals",
            "bytes": summary["package_without_vk_bytes"],
            "ratio_vs_source": summary["package_without_vk_ratio_vs_source"],
            "saving_bytes": summary["package_without_vk_saving_bytes"],
            "scope": "per-receipt package when verification key is reusable",
        },
        {
            "surface": "compressed artifact plus proof plus public signals plus verification key",
            "bytes": summary["package_with_vk_bytes"],
            "ratio_vs_source": summary["package_with_vk_ratio_vs_source"],
            "saving_bytes": summary["package_with_vk_saving_bytes"],
            "scope": "self-contained research package, not production setup",
        },
    ]


def build_payload_core() -> dict[str, Any]:
    _scorecard, compression, snark, sources = checked_sources()
    summary = package_summary(compression, snark)
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": sources,
        "package_rows": package_rows(summary),
        "summary": summary,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }


def validate_payload_core(payload: dict[str, Any]) -> None:
    expected = build_payload_core()
    if payload != expected:
        if not isinstance(payload, dict):
            raise OneBlockPackageAccountingError("payload must be object")
        if payload.get("schema") != SCHEMA:
            raise OneBlockPackageAccountingError("schema drift")
        if payload.get("decision") != DECISION:
            raise OneBlockPackageAccountingError("decision drift")
        if payload.get("result") != RESULT:
            raise OneBlockPackageAccountingError("result drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise OneBlockPackageAccountingError("claim boundary drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise OneBlockPackageAccountingError("non-claims drift")
        if payload.get("source_artifacts") != expected["source_artifacts"]:
            raise OneBlockPackageAccountingError("source artifact drift")
        if payload.get("package_rows") != expected["package_rows"]:
            raise OneBlockPackageAccountingError("package rows drift")
        if payload.get("summary") != expected["summary"]:
            raise OneBlockPackageAccountingError("summary drift")
        raise OneBlockPackageAccountingError("payload drift")


def mutation_cases(core: dict[str, Any]) -> list[dict[str, Any]]:
    def mutate(name: str, payload: dict[str, Any]) -> None:
        if name == "source_chain_bytes_drift":
            payload["summary"]["source_statement_chain_bytes"] = 1
        elif name == "compressed_artifact_bytes_drift":
            payload["summary"]["compressed_statement_chain_bytes"] = 1
        elif name == "proof_bytes_drift":
            payload["summary"]["snark_proof_bytes"] = 1
        elif name == "public_signals_bytes_drift":
            payload["summary"]["snark_public_signals_bytes"] = 1
        elif name == "verification_key_bytes_drift":
            payload["summary"]["snark_verification_key_bytes"] = 1
        elif name == "package_without_vk_bytes_drift":
            payload["summary"]["package_without_vk_bytes"] = 1
        elif name == "package_with_vk_ratio_drift":
            payload["summary"]["package_with_vk_ratio_vs_source"] = 1.0
        elif name == "source_artifact_hash_drift":
            payload["source_artifacts"][0]["file_sha256"] = "0" * 64
        elif name == "claim_boundary_native_overclaim":
            payload["claim_boundary"] = "NATIVE_BLOCK_PROOF_SIZE_RESULT"
        elif name == "non_claim_removed":
            payload["non_claims"].remove("not native proof-size evidence for a fused route")
        elif name == "timing_metric_smuggled":
            payload["summary"]["verifier_time_ms"] = 1.0
        elif name == "result_changed_to_native_proof":
            payload["result"] = "GO_NATIVE_BLOCK_PROOF_SIZE"
        else:
            raise AssertionError(f"unhandled mutation {name}")

    cases = []
    for name in MUTATION_NAMES:
        mutated = copy.deepcopy(core)
        mutate(name, mutated)
        try:
            validate_payload_core(mutated)
        except Exception as err:  # noqa: BLE001 - serialized evidence records rejection text.
            cases.append({"mutation": name, "rejected": True, "error": str(err) or type(err).__name__})
        else:
            cases.append({"mutation": name, "rejected": False, "error": ""})
    return cases


def build_payload_uncommitted() -> dict[str, Any]:
    core = build_payload_core()
    cases = mutation_cases(core)
    core["mutation_inventory"] = list(MUTATION_NAMES)
    core["cases"] = cases
    core["case_count"] = len(cases)
    core["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    return core


def validate_payload(payload: dict[str, Any]) -> None:
    expected = build_payload_uncommitted()
    if not isinstance(payload, dict):
        raise OneBlockPackageAccountingError("payload must be object")
    candidate = {key: value for key, value in payload.items() if key != "payload_commitment"}
    if candidate != expected:
        if payload.get("schema") != SCHEMA:
            raise OneBlockPackageAccountingError("schema drift")
        if payload.get("decision") != DECISION:
            raise OneBlockPackageAccountingError("decision drift")
        if payload.get("result") != RESULT:
            raise OneBlockPackageAccountingError("result drift")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            raise OneBlockPackageAccountingError("claim boundary drift")
        if payload.get("non_claims") != NON_CLAIMS:
            raise OneBlockPackageAccountingError("non-claims drift")
        if payload.get("all_mutations_rejected") is not True:
            raise OneBlockPackageAccountingError("mutation rejection drift")
        raise OneBlockPackageAccountingError("payload drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise OneBlockPackageAccountingError("payload commitment drift")


def build_payload() -> dict[str, Any]:
    payload = build_payload_uncommitted()
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload)
    return payload


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(["surface", "bytes", "ratio_vs_source", "saving_bytes", "scope"])
    for row in payload["package_rows"]:
        writer.writerow([row["surface"], row["bytes"], row["ratio_vs_source"], row["saving_bytes"], row["scope"]])
    return out.getvalue()


def _assert_output_path(path: pathlib.Path, label: str) -> pathlib.Path:
    raw = str(path).replace("\\", "/")
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise OneBlockPackageAccountingError(f"{label} must be repo-relative")
    if pathlib.PurePosixPath(*relative.parts[:3]) != pathlib.PurePosixPath("docs/engineering/evidence"):
        raise OneBlockPackageAccountingError(f"{label} must stay under docs/engineering/evidence")
    full = ROOT.joinpath(*relative.parts)
    current = ROOT
    for part in full.relative_to(ROOT).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise OneBlockPackageAccountingError(f"{label} must not include symlink components")
    if full.is_symlink():
        raise OneBlockPackageAccountingError(f"{label} must not include symlink components")
    return full


def _atomic_write(path: pathlib.Path, contents: bytes, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parent_stat = path.parent.lstat()
    if not stat_module.S_ISDIR(parent_stat.st_mode) or stat_module.S_ISLNK(parent_stat.st_mode):
        raise OneBlockPackageAccountingError(f"{label} parent must be a real directory")
    temp = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        parent_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _read_existing_output(path: pathlib.Path) -> bytes | None:
    if not path.exists():
        return None
    return SURFACE.read_source_bytes(path, "existing output")


def _remove_output(path: pathlib.Path, label: str) -> None:
    _assert_output_path(path.relative_to(ROOT), label)
    if path.is_symlink():
        raise OneBlockPackageAccountingError(f"{label} must not include symlink components")
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    outputs = []
    if json_path is not None:
        outputs.append((_assert_output_path(json_path, "json output path"), (pretty_json(payload) + "\n").encode()))
    if tsv_path is not None:
        outputs.append((_assert_output_path(tsv_path, "tsv output path"), to_tsv(payload).encode()))
    if not outputs:
        raise OneBlockPackageAccountingError("at least one output path is required")
    if len(outputs) == 2 and os.path.abspath(outputs[0][0]).casefold() == os.path.abspath(outputs[1][0]).casefold():
        raise OneBlockPackageAccountingError("json and tsv output paths must differ")

    originals: dict[pathlib.Path, bytes | None] = {path: _read_existing_output(path) for path, _contents in outputs}
    replaced: list[pathlib.Path] = []
    try:
        for path, contents in outputs:
            _atomic_write(path, contents, "output path")
            replaced.append(path)
    except (OSError, OneBlockPackageAccountingError) as err:
        rollback_errors: list[str] = []
        for path in reversed(replaced):
            try:
                original = originals[path]
                if original is None:
                    _remove_output(path, "rollback output path")
                else:
                    _atomic_write(path, original, "rollback output path")
            except (OSError, OneBlockPackageAccountingError) as rollback_err:
                rollback_errors.append(f"{path}: {rollback_err}")
        if rollback_errors:
            joined = "; ".join(rollback_errors)
            raise OneBlockPackageAccountingError(f"failed to write output path: {err}; rollback errors: {joined}") from err
        raise OneBlockPackageAccountingError(f"failed to write output path: {err}") from err


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    payload = build_payload()
    if args.write_json is None and args.write_tsv is None:
        print(pretty_json(payload))
    else:
        write_outputs(payload, args.write_json, args.write_tsv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
