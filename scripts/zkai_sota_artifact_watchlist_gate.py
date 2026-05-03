#!/usr/bin/env python3
"""Gate the zkAI SOTA artifact watchlist.

The watchlist is a comparison-discipline artifact, not a benchmark. It records
which public systems can currently support reproducible adapter rows and which
must remain source-backed context until proof bytes, verifier inputs, and a
mutation surface are available.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import tempfile
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-sota-artifact-watchlist-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-sota-artifact-watchlist-2026-05.tsv"

SCHEMA = "zkai-sota-artifact-watchlist-v1"
DECISION = "GO_CHECKED_SOTA_ARTIFACT_WATCHLIST"
QUESTION = (
    "Which current zkML, zkAI, zkVM, and settlement systems have enough public "
    "artifacts to support a reproducible statement-binding adapter row or matched "
    "comparison, and which remain source-backed context only?"
)
CHECKED_AT = "2026-05-03"
ISSUE = "#419"

STATUS_EMPIRICAL = "EMPIRICAL_STATEMENT_ADAPTER_ROW"
STATUS_LOCAL_RECEIPT = "LOCAL_STATEMENT_RECEIPT_ONLY"
STATUS_SOURCE_CONTEXT = "SOURCE_BACKED_CONTEXT_ONLY"
STATUS_COMPACT_CONTEXT = "SOURCE_BACKED_COMPACT_CALIBRATION_ONLY"
STATUS_MODEL_SCALE_CONTEXT = "SOURCE_BACKED_MODEL_SCALE_CONTEXT_ONLY"
STATUS_DEPLOYMENT_CONTEXT = "DEPLOYMENT_CALIBRATION_ONLY"
STATUS_ZKVM_WATCHLIST = "ZKVM_RECEIPT_WATCHLIST"
STATUS_SETTLEMENT_WATCHLIST = "SETTLEMENT_API_WATCHLIST"

ALLOWED_STATUSES = {
    STATUS_EMPIRICAL,
    STATUS_LOCAL_RECEIPT,
    STATUS_SOURCE_CONTEXT,
    STATUS_COMPACT_CONTEXT,
    STATUS_MODEL_SCALE_CONTEXT,
    STATUS_DEPLOYMENT_CONTEXT,
    STATUS_ZKVM_WATCHLIST,
    STATUS_SETTLEMENT_WATCHLIST,
}

REQUIRED_SYSTEM_ORDER = [
    "EZKL",
    "snarkjs",
    "JSTprove/Remainder",
    "native Stwo d128 receipt",
    "DeepProve-1",
    "NANOZK",
    "Jolt Atlas",
    "Giza/LuminAIR",
    "Obelyzk",
    "RISC Zero",
    "SP1",
    "SNIP-36",
]

EMPIRICAL_SYSTEMS = {"EZKL", "snarkjs", "JSTprove/Remainder"}
SOURCE_CONTEXT_ONLY_SYSTEMS = {"DeepProve-1", "NANOZK", "Jolt Atlas", "Giza/LuminAIR"}
SETTLEMENT_OR_ZKVM_SYSTEMS = {"Obelyzk", "RISC Zero", "SP1", "SNIP-36"}

TSV_COLUMNS = (
    "system",
    "proof_system_axis",
    "status",
    "evidence_level",
    "public_proof_artifact_available",
    "public_verifier_input_available",
    "baseline_verification_reproducible",
    "metadata_mutation_reproducible",
    "recommended_use",
    "blocked_metric",
    "next_action",
)

VALIDATION_COMMANDS = [
    "just gate-fast",
    "python3 scripts/zkai_sota_artifact_watchlist_gate.py --write-json docs/engineering/evidence/zkai-sota-artifact-watchlist-2026-05.json --write-tsv docs/engineering/evidence/zkai-sota-artifact-watchlist-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_sota_artifact_watchlist_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate",
]

NON_CLAIMS = [
    "not a leaderboard",
    "not a matched performance benchmark",
    "not evidence that source-context systems lack statement binding internally",
    "not evidence that external proof systems are insecure",
    "not a recursive-proof result",
    "not a Starknet deployment claim for the local d128 receipt",
]


class SotaWatchlistError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _generated_at() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", "0")
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise SotaWatchlistError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise SotaWatchlistError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _git_commit() -> str:
    override = os.environ.get("ZKAI_SOTA_WATCHLIST_GIT_COMMIT")
    if override and override.strip():
        normalized = override.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{7,40}", normalized):
            raise SotaWatchlistError("ZKAI_SOTA_WATCHLIST_GIT_COMMIT must be a 7-40 character hex SHA")
        return normalized
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def classification_rules() -> list[dict[str, str]]:
    return [
        {
            "rule": "empirical_adapter_row",
            "description": (
                "Requires baseline proof verification plus a metadata/statement mutation suite "
                "that can be run from checked commands."
            ),
        },
        {
            "rule": "source_backed_context_only",
            "description": (
                "Paper, blog, source, or reported metrics without public proof bytes and verifier inputs "
                "must not be promoted to an empirical adapter or matched benchmark row."
            ),
        },
        {
            "rule": "deployment_calibration_only",
            "description": (
                "A live contract or transaction can calibrate settlement posture, but it is not a local "
                "verifier-time comparator unless the same workload object can be replayed locally."
            ),
        },
        {
            "rule": "zkvm_receipt_watchlist",
            "description": (
                "zkVM receipts are relevant for statement/action receipts but are not zkML throughput rows "
                "until a matched model workload and public-value contract are pinned."
            ),
        },
    ]


def system_rows() -> list[dict[str, Any]]:
    return [
        {
            "system": "EZKL",
            "proof_system_axis": "SNARK/Halo2-KZG ONNX adapter",
            "status": STATUS_EMPIRICAL,
            "evidence_level": "local_empirical_adapter",
            "checked_at": CHECKED_AT,
            "primary_source": "https://docs.ezkl.xyz/",
            "local_evidence": "docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.json",
            "public_proof_artifact_available": True,
            "public_verifier_input_available": True,
            "baseline_verification_reproducible": True,
            "metadata_mutation_reproducible": True,
            "recommended_use": "empirical statement-envelope adapter row; not a performance comparator",
            "blocked_metric": "matched transformer-block performance",
            "next_action": "keep as adapter baseline; do not call proof-only relabeling an EZKL bug",
        },
        {
            "system": "snarkjs",
            "proof_system_axis": "SNARK/Groth16 Circom adapter",
            "status": STATUS_EMPIRICAL,
            "evidence_level": "local_empirical_adapter",
            "checked_at": CHECKED_AT,
            "primary_source": "https://github.com/iden3/snarkjs",
            "local_evidence": "docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.json",
            "public_proof_artifact_available": True,
            "public_verifier_input_available": True,
            "baseline_verification_reproducible": True,
            "metadata_mutation_reproducible": True,
            "recommended_use": "empirical statement-envelope adapter row; proof-system-independent binding evidence",
            "blocked_metric": "matched transformer-block performance",
            "next_action": "keep as second external adapter for proof-system independence",
        },
        {
            "system": "JSTprove/Remainder",
            "proof_system_axis": "GKR/sum-check adapter",
            "status": STATUS_EMPIRICAL,
            "evidence_level": "local_empirical_adapter",
            "checked_at": CHECKED_AT,
            "primary_source": "https://github.com/remainder-org/JSTprove",
            "local_evidence": "docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.json",
            "public_proof_artifact_available": True,
            "public_verifier_input_available": True,
            "baseline_verification_reproducible": True,
            "metadata_mutation_reproducible": True,
            "recommended_use": "empirical statement-envelope adapter row for GKR/sum-check shaped proofs",
            "blocked_metric": "matched transformer-block performance",
            "next_action": "extend only if a transformer-adjacent fixture clears the same adapter bar",
        },
        {
            "system": "native Stwo d128 receipt",
            "proof_system_axis": "Stwo-native statement-bound transformer receipt",
            "status": STATUS_LOCAL_RECEIPT,
            "evidence_level": "local_receipt_composition",
            "checked_at": CHECKED_AT,
            "primary_source": "https://github.com/starkware-libs/stwo",
            "local_evidence": "docs/engineering/evidence/zkai-d128-full-block-accumulator-backend-2026-05.json",
            "public_proof_artifact_available": True,
            "public_verifier_input_available": True,
            "baseline_verification_reproducible": True,
            "metadata_mutation_reproducible": True,
            "recommended_use": "local statement-bound receipt and accumulator evidence; not external SOTA row",
            "blocked_metric": "recursive proof size, recursive verifier time, and proof-generation time",
            "next_action": "work issue #420 for executable two-slice recursive or PCD backend",
        },
        {
            "system": "DeepProve-1",
            "proof_system_axis": "SNARK-side model-scale LLM proving",
            "status": STATUS_MODEL_SCALE_CONTEXT,
            "evidence_level": "source_backed_context",
            "checked_at": CHECKED_AT,
            "primary_source": "https://www.lagrange.dev/blog/deepprove-1",
            "local_evidence": "docs/engineering/evidence/zkai-deepprove-nanozk-adapter-feasibility-2026-05.json",
            "public_proof_artifact_available": False,
            "public_verifier_input_available": False,
            "baseline_verification_reproducible": False,
            "metadata_mutation_reproducible": False,
            "recommended_use": "source-backed model-scale context only; do not use as empirical adapter row",
            "blocked_metric": "metadata relabeling result and matched verifier-time row",
            "next_action": "revisit when public proof bytes, verifier inputs, and model/input/output commitments are released",
        },
        {
            "system": "NANOZK",
            "proof_system_axis": "layerwise LLM proof / compact verifier-facing object",
            "status": STATUS_COMPACT_CONTEXT,
            "evidence_level": "source_backed_context",
            "checked_at": CHECKED_AT,
            "primary_source": "https://arxiv.org/abs/2603.18046",
            "local_evidence": "docs/engineering/evidence/zkai-d128-layerwise-comparator-target-2026-05.json",
            "public_proof_artifact_available": False,
            "public_verifier_input_available": False,
            "baseline_verification_reproducible": False,
            "metadata_mutation_reproducible": False,
            "recommended_use": "source-backed compact-object calibration only; not a matched local benchmark",
            "blocked_metric": "adapter row and matched d128 proof benchmark",
            "next_action": "revisit if a public NANOZK verifier, proof bundle, and verifier inputs are published",
        },
        {
            "system": "Jolt Atlas",
            "proof_system_axis": "lookup-centric SNARK / ONNX and transformer-shaped workloads",
            "status": STATUS_MODEL_SCALE_CONTEXT,
            "evidence_level": "source_backed_context",
            "checked_at": CHECKED_AT,
            "primary_source": "https://arxiv.org/abs/2602.17452",
            "local_evidence": "",
            "public_proof_artifact_available": False,
            "public_verifier_input_available": False,
            "baseline_verification_reproducible": False,
            "metadata_mutation_reproducible": False,
            "recommended_use": "source-backed architecture context until proof/verifier bundles are reproducible",
            "blocked_metric": "matched ONNX/GPT adapter row",
            "next_action": "track whether public artifacts expose proof, public inputs, model identity, and verifier route",
        },
        {
            "system": "Giza/LuminAIR",
            "proof_system_axis": "STARK-native graph-to-AIR path",
            "status": STATUS_SOURCE_CONTEXT,
            "evidence_level": "source_backed_context",
            "checked_at": CHECKED_AT,
            "primary_source": "https://www.gizatech.xyz/",
            "local_evidence": "",
            "public_proof_artifact_available": False,
            "public_verifier_input_available": False,
            "baseline_verification_reproducible": False,
            "metadata_mutation_reproducible": False,
            "recommended_use": "source-backed STARK-native architecture context",
            "blocked_metric": "matched graph proof adapter row",
            "next_action": "revisit if public proof artifacts and verifier-input bundles become available",
        },
        {
            "system": "Obelyzk",
            "proof_system_axis": "STARK-native recursive/onchain settlement calibration",
            "status": STATUS_DEPLOYMENT_CONTEXT,
            "evidence_level": "source_backed_deployment_calibration",
            "checked_at": CHECKED_AT,
            "primary_source": "https://docs.rs/crate/obelyzk/0.3.0",
            "local_evidence": "docs/paper/evidence/obelyzk-sepolia-comparator-note-2026-04-25.md",
            "public_proof_artifact_available": False,
            "public_verifier_input_available": False,
            "baseline_verification_reproducible": False,
            "metadata_mutation_reproducible": False,
            "recommended_use": "deployment calibration only; not local verifier-time comparison",
            "blocked_metric": "matched local verifier-time row",
            "next_action": "keep pinned contract/tx context; only upgrade after live replay or local verifier route is reproducible",
        },
        {
            "system": "RISC Zero",
            "proof_system_axis": "zkVM receipt and public journal model",
            "status": STATUS_ZKVM_WATCHLIST,
            "evidence_level": "watchlist_context",
            "checked_at": CHECKED_AT,
            "primary_source": "https://dev.risczero.com/",
            "local_evidence": "",
            "public_proof_artifact_available": False,
            "public_verifier_input_available": False,
            "baseline_verification_reproducible": False,
            "metadata_mutation_reproducible": False,
            "recommended_use": "watchlist for agent/action receipts and public-output binding, not zkML throughput row",
            "blocked_metric": "matched model/action receipt adapter row",
            "next_action": "track issue #422; open a fixture only if a matched public-values contract and model workload are pinned",
        },
        {
            "system": "SP1",
            "proof_system_axis": "zkVM receipt and public-values model",
            "status": STATUS_ZKVM_WATCHLIST,
            "evidence_level": "watchlist_context",
            "checked_at": CHECKED_AT,
            "primary_source": "https://docs.succinct.xyz/",
            "local_evidence": "",
            "public_proof_artifact_available": False,
            "public_verifier_input_available": False,
            "baseline_verification_reproducible": False,
            "metadata_mutation_reproducible": False,
            "recommended_use": "watchlist for statement/action receipt binding, not zkML throughput row",
            "blocked_metric": "matched model/action receipt adapter row",
            "next_action": "track issue #422; test only after pinning public values, verifying key, proof, and model/action statement fields",
        },
        {
            "system": "SNIP-36",
            "proof_system_axis": "Starknet protocol-native proof verification interface",
            "status": STATUS_SETTLEMENT_WATCHLIST,
            "evidence_level": "spec_context",
            "checked_at": CHECKED_AT,
            "primary_source": "https://community.starknet.io/t/snip-36-in-protocol-proof-verification/116123",
            "local_evidence": "",
            "public_proof_artifact_available": False,
            "public_verifier_input_available": False,
            "baseline_verification_reproducible": False,
            "metadata_mutation_reproducible": False,
            "recommended_use": "settlement API watchlist; park until a local proof-facts adapter exists",
            "blocked_metric": "local Starknet transaction hash and onchain proof-facts acceptance",
            "next_action": "defer until local proof objects can be expressed as protocol-native proof_facts",
        },
    ]


def build_payload() -> dict[str, Any]:
    systems = system_rows()
    payload = {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "git_commit": _git_commit(),
        "checked_at": CHECKED_AT,
        "issue": ISSUE,
        "decision": DECISION,
        "question": QUESTION,
        "classification_rules": classification_rules(),
        "systems": systems,
        "systems_commitment": blake2b_commitment(systems, "ptvm:zkai:sota-artifact-watchlist:systems:v1"),
        "summary": summary_for_systems(systems),
        "paper_actions": paper_actions(),
        "validation_commands": VALIDATION_COMMANDS,
        "non_claims": NON_CLAIMS,
    }
    payload["mutation_inventory"] = mutation_inventory()
    payload["cases"] = mutation_cases(payload)
    payload["case_count"] = len(payload["cases"])
    payload["all_mutations_rejected"] = all(case["rejected"] for case in payload["cases"])
    payload["summary"]["mutation_cases"] = payload["case_count"]
    payload["summary"]["mutations_rejected"] = sum(1 for case in payload["cases"] if case["rejected"])
    validate_payload(payload)
    return payload


def summary_for_systems(systems: list[dict[str, Any]]) -> dict[str, Any]:
    empirical = [row["system"] for row in systems if row["status"] == STATUS_EMPIRICAL]
    source_context = [
        row["system"]
        for row in systems
        if row["status"] in {STATUS_SOURCE_CONTEXT, STATUS_COMPACT_CONTEXT, STATUS_MODEL_SCALE_CONTEXT}
    ]
    watchlist = [row["system"] for row in systems if row["status"] in {STATUS_ZKVM_WATCHLIST, STATUS_SETTLEMENT_WATCHLIST}]
    return {
        "system_count": len(systems),
        "empirical_adapter_rows": empirical,
        "source_context_only_rows": source_context,
        "deployment_calibration_rows": [row["system"] for row in systems if row["status"] == STATUS_DEPLOYMENT_CONTEXT],
        "watchlist_rows": watchlist,
        "current_best_next_research_step": "issue #420 executable two-slice recursive/PCD backend, not another context-only comparator row",
    }


def paper_actions() -> list[dict[str, str]]:
    return [
        {
            "paper": "Tablero",
            "action": (
                "Use the watchlist to keep external adapters, deployment calibration, and source-backed "
                "zkML context in separate lanes."
            ),
        },
        {
            "paper": "Transformer/STARK alignment",
            "action": (
                "Frame current SOTA as convergence around lookup-heavy transformer proving plus a missing "
                "public-artifact layer for matched comparison."
            ),
        },
        {
            "paper": "Verifiable AI / statement receipts",
            "action": (
                "Promote statement-binding receipts only when proof validity, public statement fields, "
                "and mutation rejection are checked together."
            ),
        },
    ]


def canonical_system_expectations() -> dict[str, dict[str, Any]]:
    return {row["system"]: row for row in system_rows()}


def _is_https_url(raw: str) -> bool:
    parsed = urlparse(raw)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_payload(payload: dict[str, Any], *, require_mutations: bool = True) -> None:
    expected_fields = {
        "schema",
        "generated_at",
        "git_commit",
        "checked_at",
        "issue",
        "decision",
        "question",
        "classification_rules",
        "systems",
        "systems_commitment",
        "summary",
        "paper_actions",
        "validation_commands",
        "non_claims",
        "mutation_inventory",
        "cases",
        "case_count",
        "all_mutations_rejected",
    }
    if set(payload) != expected_fields:
        raise SotaWatchlistError("payload field set mismatch")
    if payload["schema"] != SCHEMA:
        raise SotaWatchlistError("schema drift")
    if payload["decision"] != DECISION:
        raise SotaWatchlistError("decision drift")
    if payload["question"] != QUESTION:
        raise SotaWatchlistError("question drift")
    if payload["classification_rules"] != classification_rules():
        raise SotaWatchlistError("classification rules drift")
    if payload["paper_actions"] != paper_actions():
        raise SotaWatchlistError("paper actions drift")
    if payload["non_claims"] != NON_CLAIMS:
        raise SotaWatchlistError("non-claims drift")
    validate_generated_at(payload["generated_at"])
    validate_git_commit(payload["git_commit"])
    if payload["checked_at"] != CHECKED_AT:
        raise SotaWatchlistError("checked_at drift")
    if payload["issue"] != ISSUE:
        raise SotaWatchlistError("issue drift")
    if payload["validation_commands"] != VALIDATION_COMMANDS:
        raise SotaWatchlistError("validation command drift")
    for non_claim in ("not a leaderboard", "not a matched performance benchmark", "not a recursive-proof result"):
        if non_claim not in payload["non_claims"]:
            raise SotaWatchlistError("required non-claim missing")
    systems = require_list(payload["systems"], "systems")
    if payload["systems_commitment"] != blake2b_commitment(systems, "ptvm:zkai:sota-artifact-watchlist:systems:v1"):
        raise SotaWatchlistError("systems commitment mismatch")
    validate_systems(systems)
    validate_summary(payload["summary"], systems)
    if require_mutations:
        validate_mutations(payload)


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise SotaWatchlistError(f"{field} must be a list")
    return value


def validate_generated_at(raw: Any) -> None:
    if not isinstance(raw, str) or not raw.endswith("Z"):
        raise SotaWatchlistError("generated_at malformed")
    try:
        parsed = dt.datetime.fromisoformat(raw.removesuffix("Z") + "+00:00")
    except ValueError as err:
        raise SotaWatchlistError("generated_at malformed") from err
    if parsed.tzinfo is None:
        raise SotaWatchlistError("generated_at malformed")


def validate_git_commit(raw: Any) -> None:
    if not isinstance(raw, str) or re.fullmatch(r"[0-9a-f]{7,40}", raw) is None:
        raise SotaWatchlistError("git_commit malformed")


def validate_systems(systems: list[dict[str, Any]]) -> None:
    expected_system_fields = {
        "system",
        "proof_system_axis",
        "status",
        "evidence_level",
        "checked_at",
        "primary_source",
        "local_evidence",
        "public_proof_artifact_available",
        "public_verifier_input_available",
        "baseline_verification_reproducible",
        "metadata_mutation_reproducible",
        "recommended_use",
        "blocked_metric",
        "next_action",
    }
    names = [row.get("system") for row in systems]
    if names != REQUIRED_SYSTEM_ORDER:
        raise SotaWatchlistError("system inventory drift")
    for row in systems:
        if set(row) != expected_system_fields:
            raise SotaWatchlistError(f"system field set mismatch for {row.get('system')}")
        system = row["system"]
        status = row["status"]
        if status not in ALLOWED_STATUSES:
            raise SotaWatchlistError(f"unknown status for {system}")
        if row["checked_at"] != CHECKED_AT:
            raise SotaWatchlistError(f"checked_at drift for {system}")
        if not _is_https_url(row["primary_source"]):
            raise SotaWatchlistError(f"primary source must be https URL for {system}")
        if not isinstance(row["local_evidence"], str):
            raise SotaWatchlistError(f"local evidence must be a string for {system}")
        if row["local_evidence"]:
            _resolve_repo_relative_existing_file(row["local_evidence"], f"local evidence for {system}")
        canonical = canonical_system_expectations()[system]
        for field, expected in canonical.items():
            if row[field] != expected:
                raise SotaWatchlistError(f"canonical {field} drift for {system}")
        for flag in (
            "public_proof_artifact_available",
            "public_verifier_input_available",
            "baseline_verification_reproducible",
            "metadata_mutation_reproducible",
        ):
            if not isinstance(row[flag], bool):
                raise SotaWatchlistError(f"{flag} must be boolean for {system}")
        if status == STATUS_EMPIRICAL:
            if system not in EMPIRICAL_SYSTEMS:
                raise SotaWatchlistError(f"unapproved empirical adapter promotion for {system}")
            if not all(
                row[flag]
                for flag in (
                    "public_proof_artifact_available",
                    "public_verifier_input_available",
                    "baseline_verification_reproducible",
                    "metadata_mutation_reproducible",
                )
            ):
                raise SotaWatchlistError(f"empirical adapter row lacks reproducible artifacts for {system}")
            if not row["local_evidence"]:
                raise SotaWatchlistError(f"empirical adapter row missing local evidence for {system}")
        if system in SOURCE_CONTEXT_ONLY_SYSTEMS:
            if status == STATUS_EMPIRICAL:
                raise SotaWatchlistError(f"source-backed system promoted to empirical adapter: {system}")
            if row["baseline_verification_reproducible"] or row["metadata_mutation_reproducible"]:
                raise SotaWatchlistError(f"source-backed system overclaims reproducibility: {system}")
            if _source_context_matched_overclaim(row["recommended_use"]):
                raise SotaWatchlistError(f"source-backed system promoted to matched benchmark: {system}")
        if system == "NANOZK":
            if "not a matched local benchmark" not in row["recommended_use"]:
                raise SotaWatchlistError("NANOZK must remain non-matched context")
        if system == "Obelyzk":
            if row["status"] != STATUS_DEPLOYMENT_CONTEXT:
                raise SotaWatchlistError("Obelyzk status drift")
            if "not local verifier-time comparison" not in row["recommended_use"]:
                raise SotaWatchlistError("Obelyzk local verifier-time overclaim")
        if system in SETTLEMENT_OR_ZKVM_SYSTEMS and row["status"] == STATUS_EMPIRICAL:
            raise SotaWatchlistError(f"settlement/zkVM context promoted to empirical adapter: {system}")


def validate_summary(summary: Any, systems: list[dict[str, Any]]) -> None:
    if not isinstance(summary, dict):
        raise SotaWatchlistError("summary must be object")
    expected = {
        "system_count",
        "empirical_adapter_rows",
        "source_context_only_rows",
        "deployment_calibration_rows",
        "watchlist_rows",
        "current_best_next_research_step",
        "mutation_cases",
        "mutations_rejected",
    }
    if set(summary) != expected:
        raise SotaWatchlistError("summary field set mismatch")
    if summary["system_count"] != len(systems):
        raise SotaWatchlistError("summary system count drift")
    if summary["empirical_adapter_rows"] != ["EZKL", "snarkjs", "JSTprove/Remainder"]:
        raise SotaWatchlistError("empirical adapter summary drift")
    if summary["deployment_calibration_rows"] != ["Obelyzk"]:
        raise SotaWatchlistError("deployment summary drift")
    expected_source_context = [
        row["system"]
        for row in systems
        if row["status"] in {STATUS_SOURCE_CONTEXT, STATUS_COMPACT_CONTEXT, STATUS_MODEL_SCALE_CONTEXT}
    ]
    if summary["source_context_only_rows"] != expected_source_context:
        raise SotaWatchlistError("source-context summary drift")
    expected_watchlist = [
        row["system"]
        for row in systems
        if row["status"] in {STATUS_ZKVM_WATCHLIST, STATUS_SETTLEMENT_WATCHLIST}
    ]
    if summary["watchlist_rows"] != expected_watchlist:
        raise SotaWatchlistError("watchlist summary drift")
    if "#420" not in summary["current_best_next_research_step"]:
        raise SotaWatchlistError("best-next-step drift")


def _source_context_matched_overclaim(recommended_use: str) -> bool:
    normalized = " ".join(recommended_use.lower().split())
    if re.search(r"\bmatched\b", normalized) is None:
        return False
    allowed_negations = (
        "not a matched",
        "not matched",
        "not as a matched",
    )
    return not any(phrase in normalized for phrase in allowed_negations)


def _resolve_repo_relative_existing_file(path_text: str, field: str) -> pathlib.Path:
    raw_path = pathlib.PurePosixPath(path_text)
    if raw_path.is_absolute() or ".." in raw_path.parts:
        raise SotaWatchlistError(f"{field} must be a repo-relative path")
    resolved = (ROOT / pathlib.Path(*raw_path.parts)).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise SotaWatchlistError(f"{field} escapes repository") from err
    if not resolved.is_file():
        raise SotaWatchlistError(f"{field} does not exist: {path_text}")
    return resolved


def mutation_inventory() -> list[dict[str, str]]:
    return [
        {"mutation": "deep_prove_promoted_to_empirical", "surface": "source_context"},
        {"mutation": "nanozk_matched_benchmark_overclaim", "surface": "source_context"},
        {"mutation": "jolt_baseline_verification_overclaim", "surface": "source_context"},
        {"mutation": "obelyzk_local_verifier_time_overclaim", "surface": "deployment_context"},
        {"mutation": "risc_zero_promoted_to_zkml_throughput", "surface": "zkvm_watchlist"},
        {"mutation": "snip36_promoted_to_local_deployment", "surface": "settlement_watchlist"},
        {"mutation": "ezkl_artifact_removed", "surface": "empirical_adapter"},
        {"mutation": "primary_source_downgraded_to_http", "surface": "source_integrity"},
        {"mutation": "checked_at_stale", "surface": "source_integrity"},
        {"mutation": "system_inventory_removed", "surface": "parser_or_schema"},
        {"mutation": "non_claim_removed", "surface": "claim_boundary"},
        {"mutation": "systems_commitment_stale_after_edit", "surface": "commitment"},
    ]


def _find_system(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for row in payload["systems"]:
        if row["system"] == name:
            return row
    raise SotaWatchlistError(f"system not found: {name}")


def _recommit_systems(payload: dict[str, Any]) -> None:
    payload["systems_commitment"] = blake2b_commitment(payload["systems"], "ptvm:zkai:sota-artifact-watchlist:systems:v1")
    payload["summary"] = summary_for_systems(payload["systems"])
    payload["summary"]["mutation_cases"] = payload.get("case_count", 0)
    payload["summary"]["mutations_rejected"] = payload.get("summary", {}).get("mutations_rejected", 0)


def _mutation_fns() -> dict[str, Callable[[dict[str, Any]], None]]:
    return {
        "deep_prove_promoted_to_empirical": lambda p: _find_system(p, "DeepProve-1").update(
            {
                "status": STATUS_EMPIRICAL,
                "public_proof_artifact_available": True,
                "public_verifier_input_available": True,
                "baseline_verification_reproducible": True,
                "metadata_mutation_reproducible": True,
                "recommended_use": "empirical adapter row",
            }
        ),
        "nanozk_matched_benchmark_overclaim": lambda p: _find_system(p, "NANOZK").update(
            {"recommended_use": "matched local benchmark"}
        ),
        "jolt_baseline_verification_overclaim": lambda p: _find_system(p, "Jolt Atlas").update(
            {"baseline_verification_reproducible": True}
        ),
        "obelyzk_local_verifier_time_overclaim": lambda p: _find_system(p, "Obelyzk").update(
            {"recommended_use": "local verifier-time comparison"}
        ),
        "risc_zero_promoted_to_zkml_throughput": lambda p: _find_system(p, "RISC Zero").update(
            {"status": STATUS_EMPIRICAL, "recommended_use": "empirical zkML throughput row"}
        ),
        "snip36_promoted_to_local_deployment": lambda p: _find_system(p, "SNIP-36").update(
            {"status": STATUS_EMPIRICAL, "recommended_use": "local Starknet transaction proven"}
        ),
        "ezkl_artifact_removed": lambda p: _find_system(p, "EZKL").update({"local_evidence": ""}),
        "primary_source_downgraded_to_http": lambda p: _find_system(p, "NANOZK").update(
            {"primary_source": "http://arxiv.org/abs/2603.18046"}
        ),
        "checked_at_stale": lambda p: _find_system(p, "SP1").update({"checked_at": "2026-04-01"}),
        "system_inventory_removed": lambda p: p["systems"].pop(),
        "non_claim_removed": lambda p: p["non_claims"].remove("not a leaderboard"),
        "systems_commitment_stale_after_edit": lambda p: _find_system(p, "DeepProve-1").update(
            {"next_action": "silently claim done"}
        ),
    }


def mutation_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    fns = _mutation_fns()
    for index, item in enumerate(mutation_inventory()):
        mutation = item["mutation"]
        mutated = copy.deepcopy(payload)
        mutated.pop("mutation_inventory", None)
        mutated.pop("cases", None)
        mutated.pop("case_count", None)
        mutated.pop("all_mutations_rejected", None)
        mutated["summary"].pop("mutation_cases", None)
        mutated["summary"].pop("mutations_rejected", None)
        fns[mutation](mutated)
        if mutation != "systems_commitment_stale_after_edit":
            if "systems" in mutated:
                mutated["systems_commitment"] = blake2b_commitment(mutated["systems"], "ptvm:zkai:sota-artifact-watchlist:systems:v1")
            if "systems" in mutated and "summary" in mutated:
                mutated["summary"] = summary_for_systems(mutated["systems"])
        mutated["mutation_inventory"] = mutation_inventory()
        mutated["cases"] = []
        mutated["case_count"] = 0
        mutated["all_mutations_rejected"] = False
        mutated["summary"]["mutation_cases"] = 0
        mutated["summary"]["mutations_rejected"] = 0
        rejected = False
        error = ""
        try:
            validate_payload(mutated, require_mutations=False)
        except SotaWatchlistError as err:
            rejected = True
            error = str(err) or f"{type(err).__name__} with empty message"
        cases.append(
            {
                "index": index,
                "mutation": mutation,
                "surface": item["surface"],
                "baseline_result": "accepted",
                "mutated_accepted": not rejected,
                "rejected": rejected,
                "rejection_layer": item["surface"],
                "error": error,
            }
        )
    return cases


def validate_mutations(payload: dict[str, Any]) -> None:
    expected_inventory = mutation_inventory()
    if payload["mutation_inventory"] != expected_inventory:
        raise SotaWatchlistError("mutation inventory drift")
    cases = require_list(payload["cases"], "cases")
    if len(cases) != len(expected_inventory):
        raise SotaWatchlistError("mutation case count drift")
    seen = set()
    for index, case in enumerate(cases):
        expected = expected_inventory[index]
        if case.get("index") != index:
            raise SotaWatchlistError("mutation case index drift")
        if case.get("mutation") != expected["mutation"]:
            raise SotaWatchlistError("mutation case order drift")
        if case.get("surface") != expected["surface"]:
            raise SotaWatchlistError("mutation case surface drift")
        if case["mutation"] in seen:
            raise SotaWatchlistError("duplicate mutation case")
        seen.add(case["mutation"])
        if case.get("baseline_result") != "accepted":
            raise SotaWatchlistError("mutation baseline drift")
        if case.get("mutated_accepted") is not False or case.get("rejected") is not True:
            raise SotaWatchlistError("mutation was not rejected")
        if not case.get("error"):
            raise SotaWatchlistError("mutation error must be non-empty")
    if payload["case_count"] != len(cases):
        raise SotaWatchlistError("serialized mutation count drift")
    if payload["all_mutations_rejected"] is not True:
        raise SotaWatchlistError("not all mutations rejected")
    if payload["summary"]["mutation_cases"] != len(cases):
        raise SotaWatchlistError("summary mutation count drift")
    if payload["summary"]["mutations_rejected"] != len(cases):
        raise SotaWatchlistError("summary mutation rejection drift")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, str]]:
    validate_payload(payload)
    rows: list[dict[str, str]] = []
    for row in payload["systems"]:
        rows.append(
            {
                "system": row["system"],
                "proof_system_axis": row["proof_system_axis"],
                "status": row["status"],
                "evidence_level": row["evidence_level"],
                "public_proof_artifact_available": str(row["public_proof_artifact_available"]).lower(),
                "public_verifier_input_available": str(row["public_verifier_input_available"]).lower(),
                "baseline_verification_reproducible": str(row["baseline_verification_reproducible"]).lower(),
                "metadata_mutation_reproducible": str(row["metadata_mutation_reproducible"]).lower(),
                "recommended_use": row["recommended_use"],
                "blocked_metric": row["blocked_metric"],
                "next_action": row["next_action"],
            }
        )
    return rows


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _tsv_text(payload: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows_for_tsv(payload))
    return buffer.getvalue()


def _atomic_write_pair(files: list[tuple[pathlib.Path, str]]) -> None:
    staged: list[tuple[pathlib.Path, pathlib.Path]] = []
    backups: list[tuple[pathlib.Path, pathlib.Path, bool]] = []
    try:
        for final_path, content in files:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=final_path.parent,
                prefix=f".{final_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                tmp_path = pathlib.Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((tmp_path, final_path))
        for tmp_path, final_path in staged:
            with tempfile.NamedTemporaryFile(
                dir=final_path.parent,
                prefix=f".{final_path.name}.backup.",
                suffix=".tmp",
                delete=False,
            ) as backup_handle:
                backup_path = pathlib.Path(backup_handle.name)
            backup_path.unlink(missing_ok=True)
            existed = final_path.exists()
            if existed:
                final_path.replace(backup_path)
            backups.append((final_path, backup_path, existed))
            tmp_path.replace(final_path)
    except OSError as err:
        for final_path, backup_path, existed in reversed(backups):
            try:
                final_path.unlink(missing_ok=True)
                if existed:
                    backup_path.replace(final_path)
            except OSError:
                pass
        for tmp_path, _ in staged:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        for _, backup_path, _ in backups:
            try:
                backup_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise SotaWatchlistError(f"failed to write SOTA watchlist outputs: {err}") from err
    for _, backup_path, _ in backups:
        try:
            backup_path.unlink(missing_ok=True)
        except OSError:
            pass


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path, tsv_path: pathlib.Path) -> None:
    validate_payload(payload)
    _atomic_write_pair([(json_path, _json_text(payload)), (tsv_path, _tsv_text(payload))])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--write-json", type=pathlib.Path, default=None, help="write JSON evidence to this path")
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None, help="write TSV evidence to this path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if args.write_json is not None and args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    elif args.write_json is not None:
        validate_payload(payload)
        _atomic_write_pair([(args.write_json, _json_text(payload))])
    elif args.write_tsv is not None:
        validate_payload(payload)
        _atomic_write_pair([(args.write_tsv, _tsv_text(payload))])


if __name__ == "__main__":
    main()
