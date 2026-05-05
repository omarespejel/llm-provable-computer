#!/usr/bin/env python3
"""Route selector for proof-backed attention/KV-cache receipts.

This gate consumes the existing source-backed attention/KV transition receipt
and asks whether the repository currently has a proof-backed route for the same
public statement fields. The current answer has five narrow GO routes: an
external snarkjs/Groth16 statement receipt over the source-backed attention/KV
contract, and a RISC Zero receipt whose guest computes the tiny integer-argmax
attention/KV transition semantics, and a second RISC Zero receipt whose guest
computes a three-step carried KV-cache sequence, and a third RISC Zero receipt
whose guest computes a fixed eight-step carried KV-cache sequence, and a fourth
RISC Zero receipt whose guest computes a fixed eight-step d=8 causal-prefix
masked sequence. Native Stwo attention arithmetic, Softmax, and recursion
remain explicitly outside the current proof route.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_transition_receipt_probe.py"
SNARK_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_snark_statement_receipt_gate.py"
RISC0_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_risc0_semantics_receipt_gate.py"
RISC0_SEQUENCE_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_risc0_sequence_receipt_gate.py"
RISC0_SCALED_SEQUENCE_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py"
RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py"
)
SOURCE_EVIDENCE_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-transition-receipt-2026-05.json"
)
SNARK_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-snark-statement-receipt-2026-05.json"
)
RISC0_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-risc0-semantics-receipt-2026-05.json"
)
RISC0_SEQUENCE_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-risc0-sequence-receipt-2026-05.json"
)
RISC0_SCALED_SEQUENCE_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.json"
)
RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.json"
)
JSON_OUT = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-proof-route-selector-2026-05.json"
)
TSV_OUT = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-proof-route-selector-2026-05.tsv"
)

SCHEMA = "zkai-attention-kv-proof-route-selector-gate-v1"
DECISION = "GO_EXTERNAL_SNARK_RISC0_TRANSITION_SEQUENCE_SCALED_AND_WIDE_MASKED_SEQUENCE_RECEIPTS_FOR_ATTENTION_KV"
FIRST_BLOCKER = "NO_NATIVE_ATTENTION_ARITHMETIC_PROOF_BACKEND"
CLAIM_BOUNDARY = (
    "EXTERNAL_SNARK_AND_RISC0_TRANSITION_SEQUENCE_SCALED_SEQUENCE_WIDE_MASKED_SEQUENCE_RECEIPTS_PROOF_BACKED_"
    "NOT_NATIVE_STWO_NOT_SOFTMAX_NOT_LONG_CONTEXT_OR_FULL_INFERENCE_NOT_RECURSION_OR_PCD_NOT_AGENT_CORRECTNESS"
)
SOURCE_DATE_EPOCH_DEFAULT = 0

REQUIRED_PUBLIC_FIELDS = (
    "model_config_commitment",
    "prior_kv_cache_commitment",
    "input_commitment",
    "attention_output_commitment",
    "next_kv_cache_commitment",
    "public_instance_commitment",
    "proof_commitment",
    "proof_status",
    "verifier_domain",
    "statement_commitment",
)

SOURCE_ROUTE_ID = "source_backed_attention_kv_receipt_contract"
LOCAL_STWO_ROUTE_ID = "local_stwo_attention_kv_transition_proof"
EXTERNAL_SNARK_ROUTE_ID = "external_snark_attention_kv_statement_receipt"
EXTERNAL_ZKVM_ROUTE_ID = "external_zkvm_attention_kv_semantics_receipt"
EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID = "external_zkvm_attention_kv_sequence_semantics_receipt"
EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID = "external_zkvm_attention_kv_scaled_sequence_semantics_receipt"
EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID = "external_zkvm_attention_kv_wide_masked_sequence_semantics_receipt"
SOFTMAX_ROUTE_ID = "softmax_attention_kv_claim"

BASE_ROUTES = (
    {
        "route_id": SOURCE_ROUTE_ID,
        "status": "GO_SOURCE_CONTRACT_ONLY",
        "blocker": "NOT_PROOF_BACKED",
        "usable_today": True,
        "proof_backed": False,
    },
    {
        "route_id": LOCAL_STWO_ROUTE_ID,
        "status": "NO_GO_MISSING_NATIVE_ATTENTION_KV_PROOF_ARTIFACT",
        "blocker": "NO_EXECUTABLE_NATIVE_ATTENTION_KV_PROOF_SURFACE",
        "usable_today": False,
        "proof_backed": False,
    },
    {
        "route_id": EXTERNAL_SNARK_ROUTE_ID,
        "status": "GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_SOURCE_CONTRACT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_ZKVM_ROUTE_ID,
        "status": "GO_RISC0_ATTENTION_KV_TRANSITION_SEMANTICS_RECEIPT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID,
        "status": "GO_RISC0_ATTENTION_KV_SEQUENCE_SEMANTICS_RECEIPT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID,
        "status": "GO_RISC0_ATTENTION_KV_SCALED_SEQUENCE_SEMANTICS_RECEIPT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID,
        "status": "GO_RISC0_ATTENTION_KV_WIDE_MASKED_SEQUENCE_SEMANTICS_RECEIPT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": SOFTMAX_ROUTE_ID,
        "status": "NO_GO_OUT_OF_SCOPE_FOR_INTEGER_ARGMAX_FIXTURE",
        "blocker": "SOFTMAX_SEMANTICS_ARE_NOT_PROVED_BY_THE_CURRENT_FIXTURE",
        "usable_today": False,
        "proof_backed": False,
    },
)

TSV_COLUMNS = (
    "decision",
    "first_blocker",
    "source_contract_decision",
    "source_contract_proof_status",
    "proof_backed_routes_available",
    "routes_checked",
    "mutations_checked",
    "mutations_rejected",
    "source_statement_commitment",
)

EXPECTED_MUTATION_NAMES = (
    "source_contract_decision_drift",
    "source_contract_proof_status_overclaim",
    "source_contract_mutation_rejections_drift",
    "missing_required_public_field",
    "local_stwo_route_relabel_go",
    "external_snark_route_removed",
    "external_snark_receipt_decision_drift",
    "external_snark_receipt_mutation_rejections_drift",
    "external_zkvm_route_removed",
    "external_zkvm_receipt_decision_drift",
    "external_zkvm_receipt_mutation_rejections_drift",
    "external_zkvm_receipt_next_kv_items_drift",
    "external_zkvm_metric_source_drift",
    "external_zkvm_sequence_route_removed",
    "external_zkvm_sequence_receipt_decision_drift",
    "external_zkvm_sequence_receipt_mutation_rejections_drift",
    "external_zkvm_sequence_length_drift",
    "external_zkvm_sequence_intermediate_state_drift",
    "external_zkvm_sequence_metric_source_drift",
    "external_zkvm_scaled_sequence_route_removed",
    "external_zkvm_scaled_sequence_receipt_decision_drift",
    "external_zkvm_scaled_sequence_receipt_mutation_rejections_drift",
    "external_zkvm_scaled_sequence_length_drift",
    "external_zkvm_scaled_sequence_intermediate_state_drift",
    "external_zkvm_scaled_sequence_metric_source_drift",
    "external_zkvm_wide_masked_sequence_route_removed",
    "external_zkvm_wide_masked_sequence_receipt_decision_drift",
    "external_zkvm_wide_masked_sequence_receipt_mutation_rejections_drift",
    "external_zkvm_wide_masked_sequence_length_drift",
    "external_zkvm_wide_masked_sequence_width_or_masking_drift",
    "external_zkvm_wide_masked_sequence_intermediate_state_drift",
    "external_zkvm_wide_masked_sequence_metric_source_drift",
    "fake_verifier_time_metric",
    "fake_proof_size_metric",
    "next_go_criteria_weakened",
    "non_claims_weakened",
    "claim_boundary_weakened",
    "first_blocker_removed",
    "unknown_field_injection",
)

EXPECTED_NEXT_GO_CRITERIA = (
    "native Stwo proof checks the attention arithmetic instead of wrapping or re-executing the reference transition",
    "the carried KV-cache sequence scales beyond a fixed eight-step fixture without weakening intermediate-state binding",
    "a d=16 or multi-head fixture preserves the same width, masking, and intermediate-state binding guarantees",
    "the explicit causal-prefix masking axis remains statement data in any native route",
    "prior KV, intermediate KV, input/query, attention output, final KV, verifier domain, proof status, and statement commitment relabels reject after proof serialization",
    "Softmax is kept out of scope unless the proof covers Softmax semantics",
)

EXPECTED_NON_CLAIMS = (
    "not a native attention arithmetic proof",
    "not a Stwo proof",
    "not a Softmax proof",
    "not full autoregressive inference",
    "not agent correctness",
    "not native Stwo proving",
    "not recursive or proof-carrying data",
    "not a long-context KV-cache benchmark",
    "not a benchmark row",
)


class AttentionKvRouteSelectorError(ValueError):
    pass


def _load_source_module():
    """Load the source-backed attention/KV probe without package assumptions."""

    spec = importlib.util.spec_from_file_location("zkai_attention_kv_transition_receipt_probe", SOURCE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load source script: {SOURCE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_snark_module():
    """Load the external SNARK statement-receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location("zkai_attention_kv_snark_statement_receipt_gate", SNARK_RECEIPT_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load SNARK receipt script: {SNARK_RECEIPT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_risc0_module():
    """Load the RISC Zero semantics-receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location("zkai_attention_kv_risc0_semantics_receipt_gate", RISC0_RECEIPT_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load RISC Zero receipt script: {RISC0_RECEIPT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_risc0_sequence_module():
    """Load the RISC Zero sequence-receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location("zkai_attention_kv_risc0_sequence_receipt_gate", RISC0_SEQUENCE_RECEIPT_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load RISC Zero sequence receipt script: {RISC0_SEQUENCE_RECEIPT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_risc0_scaled_sequence_module():
    """Load the RISC Zero scaled-sequence receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_risc0_scaled_sequence_receipt_gate",
        RISC0_SCALED_SEQUENCE_RECEIPT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load RISC Zero scaled sequence receipt script: {RISC0_SCALED_SEQUENCE_RECEIPT_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_risc0_wide_masked_sequence_module():
    """Load the RISC Zero wide/masked sequence receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate",
        RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load RISC Zero wide masked sequence receipt script: {RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE = _load_source_module()
SNARK = _load_snark_module()
RISC0 = _load_risc0_module()
RISC0_SEQUENCE = _load_risc0_sequence_module()
RISC0_SCALED_SEQUENCE = _load_risc0_scaled_sequence_module()
RISC0_WIDE_MASKED_SEQUENCE = _load_risc0_wide_masked_sequence_module()


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize payload fragments deterministically before hashing."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    """Commit to a typed payload fragment under an explicit domain string."""

    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _git_commit() -> str:
    """Return the current repository commit, or an explicit unavailable marker."""

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


def _generated_at() -> str:
    """Return a reproducible generation timestamp from SOURCE_DATE_EPOCH."""

    raw = os.environ.get("SOURCE_DATE_EPOCH", str(SOURCE_DATE_EPOCH_DEFAULT))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise AttentionKvRouteSelectorError("SOURCE_DATE_EPOCH must be an integer") from err
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def load_source_payload(path: pathlib.Path = SOURCE_EVIDENCE_JSON) -> dict[str, Any]:
    """Load and validate the source-backed receipt payload used as input."""

    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = SOURCE.run_probe()
    SOURCE.validate_payload(payload)
    return payload


def load_snark_payload(path: pathlib.Path = SNARK_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the external SNARK statement-receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing SNARK receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    SNARK.validate_payload(payload)
    return payload


def load_risc0_payload(path: pathlib.Path = RISC0_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the RISC Zero semantics-receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing RISC Zero receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    RISC0.validate_payload(payload)
    return payload


def load_risc0_sequence_payload(path: pathlib.Path = RISC0_SEQUENCE_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the RISC Zero sequence-receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing RISC Zero sequence receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    RISC0_SEQUENCE.validate_payload(payload)
    return payload


def load_risc0_scaled_sequence_payload(path: pathlib.Path = RISC0_SCALED_SEQUENCE_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the RISC Zero scaled-sequence receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing RISC Zero scaled sequence receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    RISC0_SCALED_SEQUENCE.validate_payload(payload)
    return payload


def load_risc0_wide_masked_sequence_payload(path: pathlib.Path = RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the RISC Zero wide/masked sequence receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing RISC Zero wide masked sequence receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    RISC0_WIDE_MASKED_SEQUENCE.validate_payload(payload)
    return payload


def snark_receipt_summary(snark_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the proof-backed route fields the selector depends on."""

    metrics = snark_payload["receipt_metrics"]
    statement = snark_payload["statement_receipt"]
    return {
        "schema": snark_payload["schema"],
        "decision": snark_payload["decision"],
        "result": snark_payload["result"],
        "claim_boundary": snark_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json",
        "proof_system": snark_payload["external_system"]["proof_system"],
        "proof_system_version": snark_payload["external_system"]["version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "public_signal_count": metrics["public_signal_count"],
        "public_signal_field_count": statement["public_signal_field_count"],
        "statement_commitment": statement["statement_commitment"],
        "receipt_commitment": statement["receipt_commitment"],
        "mutations_checked": snark_payload["case_count"],
        "mutations_rejected": sum(1 for case in snark_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": snark_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def risc0_receipt_summary(risc0_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the RISC Zero semantics route fields the selector depends on."""

    metrics = risc0_payload["proof_metrics"]
    journal = risc0_payload["journal"]
    return {
        "schema": risc0_payload["schema"],
        "decision": risc0_payload["decision"],
        "result": risc0_payload["result"],
        "claim_boundary": risc0_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.json",
        "proof_system": risc0_payload["system"],
        "proof_system_version": risc0_payload["receipt_verification"]["risc0_zkvm_version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "verifier_time_ms": metrics["verifier_time_ms"],
        "proof_generation_time_source": metrics["proof_generation_time_source"],
        "verifier_time_source": metrics["verifier_time_source"],
        "journal_commitment": risc0_payload["journal_commitment"],
        "receipt_commitment": risc0_payload["receipt_commitment"],
        "image_id_hex": risc0_payload["receipt_verification"]["image_id_hex"],
        "selected_position": journal["selected_position"],
        "attention_output": journal["attention_output"],
        "next_kv_items": risc0_payload["summary"]["next_kv_items"],
        "next_kv_cache": journal["next_kv_cache"],
        "mutations_checked": risc0_payload["case_count"],
        "mutations_rejected": sum(1 for case in risc0_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": risc0_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def risc0_sequence_receipt_summary(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the RISC Zero carried-sequence route fields the selector depends on."""

    metrics = sequence_payload["proof_metrics"]
    journal = sequence_payload["journal"]
    summary = sequence_payload["summary"]
    return {
        "schema": sequence_payload["schema"],
        "decision": sequence_payload["decision"],
        "result": sequence_payload["result"],
        "claim_boundary": sequence_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.json",
        "proof_system": sequence_payload["system"],
        "proof_system_version": sequence_payload["receipt_verification"]["risc0_zkvm_version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "verifier_time_ms": metrics["verifier_time_ms"],
        "proof_generation_time_source": metrics["proof_generation_time_source"],
        "verifier_time_source": metrics["verifier_time_source"],
        "journal_commitment": sequence_payload["journal_commitment"],
        "statement_commitment": sequence_payload["statement_fields"]["statement_commitment"],
        "receipt_commitment": sequence_payload["receipt_commitment"],
        "image_id_hex": sequence_payload["receipt_verification"]["image_id_hex"],
        "sequence_length": journal["sequence_length"],
        "transition_rows": len(journal["transitions"]),
        "selected_positions": summary["selected_positions"],
        "attention_outputs": summary["attention_outputs"],
        "final_kv_items": summary["final_kv_items"],
        "transition_commitments": sequence_payload["transition_commitments"],
        "mutations_checked": sequence_payload["case_count"],
        "mutations_rejected": sum(1 for case in sequence_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": sequence_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def risc0_scaled_sequence_receipt_summary(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the RISC Zero scaled carried-sequence route fields the selector depends on."""

    metrics = sequence_payload["proof_metrics"]
    journal = sequence_payload["journal"]
    summary = sequence_payload["summary"]
    return {
        "schema": sequence_payload["schema"],
        "decision": sequence_payload["decision"],
        "result": sequence_payload["result"],
        "claim_boundary": sequence_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.json",
        "proof_system": sequence_payload["system"],
        "proof_system_version": sequence_payload["receipt_verification"]["risc0_zkvm_version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "verifier_time_ms": metrics["verifier_time_ms"],
        "proof_generation_time_source": metrics["proof_generation_time_source"],
        "verifier_time_source": metrics["verifier_time_source"],
        "journal_commitment": sequence_payload["journal_commitment"],
        "statement_commitment": sequence_payload["statement_fields"]["statement_commitment"],
        "receipt_commitment": sequence_payload["receipt_commitment"],
        "image_id_hex": sequence_payload["receipt_verification"]["image_id_hex"],
        "sequence_length": journal["sequence_length"],
        "transition_rows": len(journal["transitions"]),
        "selected_positions": summary["selected_positions"],
        "attention_outputs": summary["attention_outputs"],
        "final_kv_items": summary["final_kv_items"],
        "transition_commitments": sequence_payload["transition_commitments"],
        "mutations_checked": sequence_payload["case_count"],
        "mutations_rejected": sum(1 for case in sequence_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": sequence_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def risc0_wide_masked_sequence_receipt_summary(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the RISC Zero d=8 causal-prefix carried-sequence route fields."""

    metrics = sequence_payload["proof_metrics"]
    journal = sequence_payload["journal"]
    summary = sequence_payload["summary"]
    return {
        "schema": sequence_payload["schema"],
        "decision": sequence_payload["decision"],
        "result": sequence_payload["result"],
        "claim_boundary": sequence_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.json",
        "proof_system": sequence_payload["system"],
        "proof_system_version": sequence_payload["receipt_verification"]["risc0_zkvm_version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "verifier_time_ms": metrics["verifier_time_ms"],
        "proof_generation_time_source": metrics["proof_generation_time_source"],
        "verifier_time_source": metrics["verifier_time_source"],
        "journal_commitment": sequence_payload["journal_commitment"],
        "statement_commitment": sequence_payload["statement_fields"]["statement_commitment"],
        "receipt_commitment": sequence_payload["receipt_commitment"],
        "image_id_hex": sequence_payload["receipt_verification"]["image_id_hex"],
        "sequence_length": journal["sequence_length"],
        "transition_rows": len(journal["transitions"]),
        "key_width": journal["key_width"],
        "value_width": journal["value_width"],
        "masking_policy": journal["masking_policy"],
        "selected_positions": summary["selected_positions"],
        "attention_outputs": summary["attention_outputs"],
        "final_kv_items": summary["final_kv_items"],
        "transition_commitments": sequence_payload["transition_commitments"],
        "mutations_checked": sequence_payload["case_count"],
        "mutations_rejected": sum(1 for case in sequence_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": sequence_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def route_inventory() -> list[dict[str, Any]]:
    """Return the checked route candidates as fresh dictionaries."""

    snark = snark_receipt_summary(load_snark_payload())
    risc0 = risc0_receipt_summary(load_risc0_payload())
    risc0_sequence = risc0_sequence_receipt_summary(load_risc0_sequence_payload())
    risc0_scaled_sequence = risc0_scaled_sequence_receipt_summary(load_risc0_scaled_sequence_payload())
    risc0_wide_masked_sequence = risc0_wide_masked_sequence_receipt_summary(load_risc0_wide_masked_sequence_payload())
    routes = [dict(route) for route in BASE_ROUTES]
    snark_route = route_candidate_by_id(routes, EXTERNAL_SNARK_ROUTE_ID)
    snark_route["evidence"] = snark["evidence"]
    snark_route["proof_system"] = snark["proof_system"]
    snark_route["proof_size_bytes"] = snark["proof_size_bytes"]
    snark_route["public_signal_count"] = snark["public_signal_count"]
    snark_route["statement_commitment"] = snark["statement_commitment"]
    snark_route["receipt_commitment"] = snark["receipt_commitment"]
    zkvm_route = route_candidate_by_id(routes, EXTERNAL_ZKVM_ROUTE_ID)
    zkvm_route["evidence"] = risc0["evidence"]
    zkvm_route["proof_system"] = risc0["proof_system"]
    zkvm_route["proof_system_version"] = risc0["proof_system_version"]
    zkvm_route["proof_size_bytes"] = risc0["proof_size_bytes"]
    zkvm_route["journal_commitment"] = risc0["journal_commitment"]
    zkvm_route["receipt_commitment"] = risc0["receipt_commitment"]
    zkvm_route["image_id_hex"] = risc0["image_id_hex"]
    zkvm_route["selected_position"] = risc0["selected_position"]
    zkvm_route["next_kv_items"] = risc0["next_kv_items"]
    sequence_route = route_candidate_by_id(routes, EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID)
    sequence_route["evidence"] = risc0_sequence["evidence"]
    sequence_route["proof_system"] = risc0_sequence["proof_system"]
    sequence_route["proof_system_version"] = risc0_sequence["proof_system_version"]
    sequence_route["proof_size_bytes"] = risc0_sequence["proof_size_bytes"]
    sequence_route["journal_commitment"] = risc0_sequence["journal_commitment"]
    sequence_route["statement_commitment"] = risc0_sequence["statement_commitment"]
    sequence_route["receipt_commitment"] = risc0_sequence["receipt_commitment"]
    sequence_route["image_id_hex"] = risc0_sequence["image_id_hex"]
    sequence_route["sequence_length"] = risc0_sequence["sequence_length"]
    sequence_route["transition_rows"] = risc0_sequence["transition_rows"]
    sequence_route["final_kv_items"] = risc0_sequence["final_kv_items"]
    scaled_sequence_route = route_candidate_by_id(routes, EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID)
    scaled_sequence_route["evidence"] = risc0_scaled_sequence["evidence"]
    scaled_sequence_route["proof_system"] = risc0_scaled_sequence["proof_system"]
    scaled_sequence_route["proof_system_version"] = risc0_scaled_sequence["proof_system_version"]
    scaled_sequence_route["proof_size_bytes"] = risc0_scaled_sequence["proof_size_bytes"]
    scaled_sequence_route["journal_commitment"] = risc0_scaled_sequence["journal_commitment"]
    scaled_sequence_route["statement_commitment"] = risc0_scaled_sequence["statement_commitment"]
    scaled_sequence_route["receipt_commitment"] = risc0_scaled_sequence["receipt_commitment"]
    scaled_sequence_route["image_id_hex"] = risc0_scaled_sequence["image_id_hex"]
    scaled_sequence_route["sequence_length"] = risc0_scaled_sequence["sequence_length"]
    scaled_sequence_route["transition_rows"] = risc0_scaled_sequence["transition_rows"]
    scaled_sequence_route["final_kv_items"] = risc0_scaled_sequence["final_kv_items"]
    wide_masked_sequence_route = route_candidate_by_id(routes, EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID)
    wide_masked_sequence_route["evidence"] = risc0_wide_masked_sequence["evidence"]
    wide_masked_sequence_route["proof_system"] = risc0_wide_masked_sequence["proof_system"]
    wide_masked_sequence_route["proof_system_version"] = risc0_wide_masked_sequence["proof_system_version"]
    wide_masked_sequence_route["proof_size_bytes"] = risc0_wide_masked_sequence["proof_size_bytes"]
    wide_masked_sequence_route["journal_commitment"] = risc0_wide_masked_sequence["journal_commitment"]
    wide_masked_sequence_route["statement_commitment"] = risc0_wide_masked_sequence["statement_commitment"]
    wide_masked_sequence_route["receipt_commitment"] = risc0_wide_masked_sequence["receipt_commitment"]
    wide_masked_sequence_route["image_id_hex"] = risc0_wide_masked_sequence["image_id_hex"]
    wide_masked_sequence_route["sequence_length"] = risc0_wide_masked_sequence["sequence_length"]
    wide_masked_sequence_route["transition_rows"] = risc0_wide_masked_sequence["transition_rows"]
    wide_masked_sequence_route["key_width"] = risc0_wide_masked_sequence["key_width"]
    wide_masked_sequence_route["value_width"] = risc0_wide_masked_sequence["value_width"]
    wide_masked_sequence_route["masking_policy"] = risc0_wide_masked_sequence["masking_policy"]
    wide_masked_sequence_route["final_kv_items"] = risc0_wide_masked_sequence["final_kv_items"]
    return routes


def route_candidate_by_id(routes: list[dict[str, Any]], route_id: str) -> dict[str, Any]:
    for route in routes:
        if route.get("route_id") == route_id:
            return route
    raise AttentionKvRouteSelectorError(f"missing route candidate: {route_id}")


def source_contract_summary(source_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the source-backed receipt fields relevant to route selection."""

    receipt = source_payload["receipt"]
    return {
        "source_schema": source_payload["schema"],
        "source_decision": source_payload["decision"],
        "source_evidence": "docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json",
        "source_statement_commitment": receipt["statement_commitment"],
        "source_proof_status": receipt["proof_status"],
        "source_verifier_domain": receipt["verifier_domain"],
        "source_mutations_checked": source_payload["mutations_checked"],
        "source_mutations_rejected": source_payload["mutations_rejected"],
        "source_all_mutations_rejected": source_payload["all_mutations_rejected"],
        "required_public_fields": list(REQUIRED_PUBLIC_FIELDS),
        "present_public_fields": [field for field in REQUIRED_PUBLIC_FIELDS if field in receipt],
    }


def build_payload() -> dict[str, Any]:
    """Build and self-validate the proof-route selector decision payload."""

    source_payload = load_source_payload()
    snark_payload = load_snark_payload()
    risc0_payload = load_risc0_payload()
    risc0_sequence_payload = load_risc0_sequence_payload()
    risc0_scaled_sequence_payload = load_risc0_scaled_sequence_payload()
    risc0_wide_masked_sequence_payload = load_risc0_wide_masked_sequence_payload()
    summary = source_contract_summary(source_payload)
    snark_summary = snark_receipt_summary(snark_payload)
    risc0_summary = risc0_receipt_summary(risc0_payload)
    risc0_sequence_summary = risc0_sequence_receipt_summary(risc0_sequence_payload)
    risc0_scaled_sequence_summary = risc0_scaled_sequence_receipt_summary(risc0_scaled_sequence_payload)
    risc0_wide_masked_sequence_summary = risc0_wide_masked_sequence_receipt_summary(risc0_wide_masked_sequence_payload)
    routes = route_inventory()
    proof_backed_routes_available = [
        route["route_id"]
        for route in routes
        if route["usable_today"] is True and route["proof_backed"] is True
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "generated_at": _generated_at(),
        "git_commit": os.environ.get("ZKAI_ATTENTION_KV_ROUTE_SELECTOR_GIT_COMMIT", _git_commit()),
        "question": (
            "Can the checked attention/KV transition receipt be promoted from a source-backed "
            "contract to a proof-backed receipt today?"
        ),
        "source_contract": summary,
        "external_snark_receipt": snark_summary,
        "external_risc0_receipt": risc0_summary,
        "external_risc0_sequence_receipt": risc0_sequence_summary,
        "external_risc0_scaled_sequence_receipt": risc0_scaled_sequence_summary,
        "external_risc0_wide_masked_sequence_receipt": risc0_wide_masked_sequence_summary,
        "route_candidates": routes,
        "proof_backed_routes_available": proof_backed_routes_available,
        "metrics": {
            "snark_proof_size_bytes": snark_summary["proof_size_bytes"],
            "snark_public_signal_count": snark_summary["public_signal_count"],
            "risc0_receipt_size_bytes": risc0_summary["proof_size_bytes"],
            "risc0_verifier_time_ms": risc0_summary["verifier_time_ms"],
            "risc0_verifier_time_source": risc0_summary["verifier_time_source"],
            "risc0_sequence_receipt_size_bytes": risc0_sequence_summary["proof_size_bytes"],
            "risc0_sequence_verifier_time_ms": risc0_sequence_summary["verifier_time_ms"],
            "risc0_sequence_verifier_time_source": risc0_sequence_summary["verifier_time_source"],
            "risc0_scaled_sequence_receipt_size_bytes": risc0_scaled_sequence_summary["proof_size_bytes"],
            "risc0_scaled_sequence_verifier_time_ms": risc0_scaled_sequence_summary["verifier_time_ms"],
            "risc0_scaled_sequence_verifier_time_source": risc0_scaled_sequence_summary["verifier_time_source"],
            "risc0_wide_masked_sequence_receipt_size_bytes": risc0_wide_masked_sequence_summary["proof_size_bytes"],
            "risc0_wide_masked_sequence_verifier_time_ms": risc0_wide_masked_sequence_summary["verifier_time_ms"],
            "risc0_wide_masked_sequence_verifier_time_source": risc0_wide_masked_sequence_summary["verifier_time_source"],
            "proof_generation_time_ms": None,
            "verifier_time_ms": None,
            "timing_policy": snark_summary["timing_policy"],
            "risc0_timing_policy": risc0_summary["timing_policy"],
        },
        "next_go_criteria": list(EXPECTED_NEXT_GO_CRITERIA),
        "non_claims": list(EXPECTED_NON_CLAIMS),
    }
    payload["selector_commitment"] = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "source_contract": payload["source_contract"],
            "external_snark_receipt": payload["external_snark_receipt"],
            "external_risc0_receipt": payload["external_risc0_receipt"],
            "external_risc0_sequence_receipt": payload["external_risc0_sequence_receipt"],
            "external_risc0_scaled_sequence_receipt": payload["external_risc0_scaled_sequence_receipt"],
            "external_risc0_wide_masked_sequence_receipt": payload["external_risc0_wide_masked_sequence_receipt"],
            "route_candidates": payload["route_candidates"],
            "proof_backed_routes_available": payload["proof_backed_routes_available"],
            "metrics": payload["metrics"],
            "next_go_criteria": payload["next_go_criteria"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-proof-route-selector:v1",
    )
    payload["mutation_cases"] = run_mutation_cases(payload)
    payload["mutations_checked"] = len(payload["mutation_cases"])
    payload["mutations_rejected"] = sum(1 for item in payload["mutation_cases"] if item["rejected"] is True)
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    validate_payload(payload)
    return payload


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    """Apply one deterministic mutation that the selector must reject."""

    out = copy.deepcopy(payload)
    out.pop("mutation_cases", None)
    out.pop("mutations_checked", None)
    out.pop("mutations_rejected", None)
    out.pop("all_mutations_rejected", None)
    if name == "source_contract_decision_drift":
        out["source_contract"]["source_decision"] = "GO_PROOF_BACKED_ATTENTION_KV_RECEIPT"
    elif name == "source_contract_proof_status_overclaim":
        out["source_contract"]["source_proof_status"] = "PROVEN_BY_STWO"
    elif name == "source_contract_mutation_rejections_drift":
        out["source_contract"]["source_mutations_rejected"] -= 1
    elif name == "missing_required_public_field":
        out["source_contract"]["present_public_fields"].remove("next_kv_cache_commitment")
    elif name == "local_stwo_route_relabel_go":
        local_stwo_route = route_candidate_by_id(out["route_candidates"], LOCAL_STWO_ROUTE_ID)
        local_stwo_route["status"] = "GO_NATIVE_STWO_ATTENTION_KV_PROOF"
        local_stwo_route["usable_today"] = True
        local_stwo_route["proof_backed"] = True
        out["proof_backed_routes_available"] = [LOCAL_STWO_ROUTE_ID]
    elif name == "external_snark_route_removed":
        snark_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_SNARK_ROUTE_ID)
        snark_route["status"] = "NO_GO_MISSING_ATTENTION_KV_SNARK_RECEIPT"
        snark_route["usable_today"] = False
        snark_route["proof_backed"] = False
        out["proof_backed_routes_available"] = []
    elif name == "external_snark_receipt_decision_drift":
        out["external_snark_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_SNARK_RECEIPT"
    elif name == "external_snark_receipt_mutation_rejections_drift":
        out["external_snark_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_route_removed":
        zkvm_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_ZKVM_ROUTE_ID)
        zkvm_route["status"] = "NO_GO_MISSING_ATTENTION_KV_ZKVM_RECEIPT"
        zkvm_route["usable_today"] = False
        zkvm_route["proof_backed"] = False
        out["proof_backed_routes_available"] = [EXTERNAL_SNARK_ROUTE_ID]
    elif name == "external_zkvm_receipt_decision_drift":
        out["external_risc0_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_RISC0_SEMANTICS_RECEIPT"
    elif name == "external_zkvm_receipt_mutation_rejections_drift":
        out["external_risc0_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_receipt_next_kv_items_drift":
        out["external_risc0_receipt"]["next_kv_items"] -= 1
    elif name == "external_zkvm_metric_source_drift":
        out["external_risc0_receipt"]["verifier_time_source"] = "carried_from_existing_evidence_not_remeasured"
    elif name == "external_zkvm_sequence_route_removed":
        sequence_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID)
        sequence_route["status"] = "NO_GO_MISSING_ATTENTION_KV_SEQUENCE_ZKVM_RECEIPT"
        sequence_route["usable_today"] = False
        sequence_route["proof_backed"] = False
        out["proof_backed_routes_available"] = [EXTERNAL_SNARK_ROUTE_ID, EXTERNAL_ZKVM_ROUTE_ID]
    elif name == "external_zkvm_sequence_receipt_decision_drift":
        out["external_risc0_sequence_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_RISC0_SEQUENCE_RECEIPT"
    elif name == "external_zkvm_sequence_receipt_mutation_rejections_drift":
        out["external_risc0_sequence_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_sequence_length_drift":
        out["external_risc0_sequence_receipt"]["sequence_length"] = 1
    elif name == "external_zkvm_sequence_intermediate_state_drift":
        out["external_risc0_sequence_receipt"]["selected_positions"][1] = 99
    elif name == "external_zkvm_sequence_metric_source_drift":
        out["external_risc0_sequence_receipt"]["verifier_time_source"] = "carried_from_existing_evidence_not_remeasured"
    elif name == "external_zkvm_scaled_sequence_route_removed":
        scaled_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID)
        scaled_route["status"] = "NO_GO_MISSING_ATTENTION_KV_SCALED_SEQUENCE_ZKVM_RECEIPT"
        scaled_route["usable_today"] = False
        scaled_route["proof_backed"] = False
        out["proof_backed_routes_available"] = [
            EXTERNAL_SNARK_ROUTE_ID,
            EXTERNAL_ZKVM_ROUTE_ID,
            EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID,
        ]
    elif name == "external_zkvm_scaled_sequence_receipt_decision_drift":
        out["external_risc0_scaled_sequence_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_RISC0_SCALED_SEQUENCE_RECEIPT"
    elif name == "external_zkvm_scaled_sequence_receipt_mutation_rejections_drift":
        out["external_risc0_scaled_sequence_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_scaled_sequence_length_drift":
        out["external_risc0_scaled_sequence_receipt"]["sequence_length"] = 3
    elif name == "external_zkvm_scaled_sequence_intermediate_state_drift":
        out["external_risc0_scaled_sequence_receipt"]["selected_positions"][4] = 99
    elif name == "external_zkvm_scaled_sequence_metric_source_drift":
        out["external_risc0_scaled_sequence_receipt"]["verifier_time_source"] = "carried_from_existing_evidence_not_remeasured"
    elif name == "external_zkvm_wide_masked_sequence_route_removed":
        wide_masked_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID)
        wide_masked_route["status"] = "NO_GO_MISSING_ATTENTION_KV_WIDE_MASKED_SEQUENCE_ZKVM_RECEIPT"
        wide_masked_route["usable_today"] = False
        wide_masked_route["proof_backed"] = False
        out["proof_backed_routes_available"] = [
            EXTERNAL_SNARK_ROUTE_ID,
            EXTERNAL_ZKVM_ROUTE_ID,
            EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID,
            EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID,
        ]
    elif name == "external_zkvm_wide_masked_sequence_receipt_decision_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["decision"] = (
            "NO_GO_MISSING_ATTENTION_KV_RISC0_WIDE_MASKED_SEQUENCE_RECEIPT"
        )
    elif name == "external_zkvm_wide_masked_sequence_receipt_mutation_rejections_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_wide_masked_sequence_length_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["sequence_length"] = 3
    elif name == "external_zkvm_wide_masked_sequence_width_or_masking_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["masking_policy"] = "none"
    elif name == "external_zkvm_wide_masked_sequence_intermediate_state_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["selected_positions"][3] = 99
    elif name == "external_zkvm_wide_masked_sequence_metric_source_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["verifier_time_source"] = "carried_from_existing_evidence_not_remeasured"
    elif name == "fake_verifier_time_metric":
        out["metrics"]["verifier_time_ms"] = 7.5
    elif name == "fake_proof_size_metric":
        out["metrics"]["snark_proof_size_bytes"] = 1024
    elif name == "next_go_criteria_weakened":
        out["next_go_criteria"] = ["any zkVM receipt wraps the source-backed contract"]
    elif name == "non_claims_weakened":
        out["non_claims"] = [claim for claim in out["non_claims"] if claim != "not native Stwo proving"]
    elif name == "claim_boundary_weakened":
        out["claim_boundary"] = "PROOF_BACKED_ATTENTION_KV_RECEIPT"
    elif name == "first_blocker_removed":
        out["first_blocker"] = "NONE"
    elif name == "unknown_field_injection":
        out["unexpected"] = "accepted"
    else:
        raise AttentionKvRouteSelectorError(f"unknown mutation: {name}")
    return out


def run_mutation_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Run every expected mutation and record whether validation rejects it."""

    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvRouteSelectorError as err:
            cases.append({"name": name, "rejected": True, "reason": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "reason": "accepted"})
    return cases


def validate_source_contract(summary: Any) -> None:
    """Validate that the source-backed receipt contract has not drifted."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("source contract must be an object")
    if summary.get("source_schema") != SOURCE.SCHEMA:
        raise AttentionKvRouteSelectorError("source schema drift")
    if summary.get("source_decision") != SOURCE.DECISION:
        raise AttentionKvRouteSelectorError("source decision drift")
    if summary.get("source_proof_status") != "SOURCE_BACKED_RECEIPT_NOT_PROVEN":
        raise AttentionKvRouteSelectorError("source proof status overclaim")
    if summary.get("source_verifier_domain") != "ptvm:zkai:attention-kv-transition:v1":
        raise AttentionKvRouteSelectorError("source verifier-domain drift")
    if summary.get("source_mutations_checked") != len(SOURCE.EXPECTED_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("source mutation count drift")
    if summary.get("source_mutations_rejected") != len(SOURCE.EXPECTED_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("source mutation rejection drift")
    if summary.get("source_all_mutations_rejected") is not True:
        raise AttentionKvRouteSelectorError("source fail-closed drift")
    if tuple(summary.get("required_public_fields", ())) != REQUIRED_PUBLIC_FIELDS:
        raise AttentionKvRouteSelectorError("required public field list drift")
    if tuple(summary.get("present_public_fields", ())) != REQUIRED_PUBLIC_FIELDS:
        raise AttentionKvRouteSelectorError("present public field list drift")
    commitment = summary.get("source_statement_commitment")
    if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
        raise AttentionKvRouteSelectorError("source statement commitment drift")


def validate_routes(routes: Any) -> None:
    """Reject route inventory edits that would silently change the gate question."""

    if routes != route_inventory():
        raise AttentionKvRouteSelectorError("route inventory drift")


def validate_snark_receipt(summary: Any) -> None:
    """Validate the proof-backed external SNARK receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external SNARK receipt must be an object")
    expected = snark_receipt_summary(load_snark_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("external SNARK receipt drift")
    if summary["decision"] != SNARK.DECISION:
        raise AttentionKvRouteSelectorError("external SNARK decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external SNARK result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external SNARK fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external SNARK mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["public_signal_count"] <= 0:
        raise AttentionKvRouteSelectorError("external SNARK proof metric drift")


def validate_risc0_receipt(summary: Any) -> None:
    """Validate the proof-backed RISC Zero semantics receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external RISC Zero receipt must be an object")
    expected = risc0_receipt_summary(load_risc0_payload())
    summary_for_compare = dict(summary)
    expected_for_compare = dict(expected)
    proof_generation_time_source = summary_for_compare.pop("proof_generation_time_source", None)
    expected_for_compare.pop("proof_generation_time_source", None)
    if summary_for_compare != expected_for_compare:
        raise AttentionKvRouteSelectorError("external RISC Zero receipt drift")
    if summary["decision"] != RISC0.DECISION:
        raise AttentionKvRouteSelectorError("external RISC Zero decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external RISC Zero result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external RISC Zero fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external RISC Zero mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["verifier_time_ms"] <= 0:
        raise AttentionKvRouteSelectorError("external RISC Zero proof metric drift")
    if proof_generation_time_source not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRouteSelectorError("external RISC Zero proof-generation metric source drift")
    if summary["verifier_time_source"] != "current_verify_run":
        raise AttentionKvRouteSelectorError("external RISC Zero verifier metric source drift")
    if summary["selected_position"] != 0 or summary["attention_output"] != [2, 1]:
        raise AttentionKvRouteSelectorError("external RISC Zero semantics drift")
    if summary["next_kv_items"] != 3 or len(summary["next_kv_cache"]) != summary["next_kv_items"]:
        raise AttentionKvRouteSelectorError("external RISC Zero KV update drift")


def validate_risc0_sequence_receipt(summary: Any) -> None:
    """Validate the proof-backed RISC Zero carried-sequence receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external RISC Zero sequence receipt must be an object")
    expected = risc0_sequence_receipt_summary(load_risc0_sequence_payload())
    summary_for_compare = dict(summary)
    expected_for_compare = dict(expected)
    proof_generation_time_source = summary_for_compare.pop("proof_generation_time_source", None)
    expected_for_compare.pop("proof_generation_time_source", None)
    if summary_for_compare != expected_for_compare:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence receipt drift")
    if summary["decision"] != RISC0_SEQUENCE.DECISION:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external RISC Zero sequence result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["verifier_time_ms"] <= 0:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence proof metric drift")
    if proof_generation_time_source not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence proof-generation metric source drift")
    if summary["verifier_time_source"] != "current_verify_run":
        raise AttentionKvRouteSelectorError("external RISC Zero sequence verifier metric source drift")
    if summary["sequence_length"] != 3 or summary["transition_rows"] != 3:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence length drift")
    if summary["selected_positions"] != [0, 2, 3]:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence intermediate state drift")
    if summary["attention_outputs"] != [[2, 1], [4, 2], [5, -2]]:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence output drift")
    if summary["final_kv_items"] != 5:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence final KV drift")
    if len(summary["transition_commitments"]) != summary["transition_rows"]:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence transition commitment drift")


def validate_risc0_scaled_sequence_receipt(summary: Any) -> None:
    """Validate the proof-backed RISC Zero scaled carried-sequence receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence receipt must be an object")
    expected = risc0_scaled_sequence_receipt_summary(load_risc0_scaled_sequence_payload())
    summary_for_compare = dict(summary)
    expected_for_compare = dict(expected)
    proof_generation_time_source = summary_for_compare.pop("proof_generation_time_source", None)
    expected_for_compare.pop("proof_generation_time_source", None)
    if summary_for_compare != expected_for_compare:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence receipt drift")
    if summary["decision"] != RISC0_SCALED_SEQUENCE.DECISION:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["verifier_time_ms"] <= 0:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence proof metric drift")
    if proof_generation_time_source not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence proof-generation metric source drift")
    if summary["verifier_time_source"] != "current_verify_run":
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence verifier metric source drift")
    if summary["sequence_length"] != 8 or summary["transition_rows"] != 8:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence length drift")
    if summary["selected_positions"] != [0, 2, 3, 4, 5, 4, 5, 6]:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence intermediate state drift")
    if summary["attention_outputs"] != [[2, 1], [4, 2], [5, -2], [0, 6], [7, 1], [0, 6], [7, 1], [-3, 4]]:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence output drift")
    if summary["final_kv_items"] != 10:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence final KV drift")
    if len(summary["transition_commitments"]) != summary["transition_rows"]:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence transition commitment drift")


def validate_risc0_wide_masked_sequence_receipt(summary: Any) -> None:
    """Validate the proof-backed RISC Zero d=8 causal-prefix sequence receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence receipt must be an object")
    expected = risc0_wide_masked_sequence_receipt_summary(load_risc0_wide_masked_sequence_payload())
    summary_for_compare = dict(summary)
    expected_for_compare = dict(expected)
    proof_generation_time_source = summary_for_compare.pop("proof_generation_time_source", None)
    expected_for_compare.pop("proof_generation_time_source", None)
    if summary_for_compare != expected_for_compare:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence receipt drift")
    if summary["decision"] != RISC0_WIDE_MASKED_SEQUENCE.DECISION:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["verifier_time_ms"] <= 0:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence proof metric drift")
    if proof_generation_time_source not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence proof-generation metric source drift")
    if summary["verifier_time_source"] != "current_verify_run":
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence verifier metric source drift")
    if summary["sequence_length"] != 8 or summary["transition_rows"] != 8:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence length drift")
    if summary["key_width"] != 8 or summary["value_width"] != 8:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence width drift")
    if summary["masking_policy"] != "causal_prefix_position_lte_query_token":
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence masking drift")
    if summary["selected_positions"] != [0, 2, 3, 3, 5, 5, 7, 9]:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence intermediate state drift")
    if summary["attention_outputs"] != [
        [2, 1, 0, -1, 3, 0, 1, 2],
        [4, 2, 1, 0, -1, 3, 2, 1],
        [5, -2, 0, 3, 1, 1, -1, 2],
        [5, -2, 0, 3, 1, 1, -1, 2],
        [7, 1, 2, -2, 0, 5, -3, 1],
        [7, 1, 2, -2, 0, 5, -3, 1],
        [6, 6, -2, 0, 2, 1, 3, -1],
        [-5, 5, 1, -3, 4, 2, -2, 0],
    ]:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence output drift")
    if summary["final_kv_items"] != 10:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence final KV drift")
    if len(summary["transition_commitments"]) != summary["transition_rows"]:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence transition commitment drift")


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    """Validate selector shape, commitments, non-claims, and fail-closed cases."""

    if not isinstance(payload, dict):
        raise AttentionKvRouteSelectorError("payload must be an object")
    allowed_keys = {
        "schema",
        "decision",
        "claim_boundary",
        "first_blocker",
        "generated_at",
        "git_commit",
        "question",
        "source_contract",
        "external_snark_receipt",
        "external_risc0_receipt",
        "external_risc0_sequence_receipt",
        "external_risc0_scaled_sequence_receipt",
        "external_risc0_wide_masked_sequence_receipt",
        "route_candidates",
        "proof_backed_routes_available",
        "metrics",
        "next_go_criteria",
        "non_claims",
        "selector_commitment",
        "mutation_cases",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
    }
    if set(payload) - allowed_keys:
        raise AttentionKvRouteSelectorError("unknown top-level field")
    if payload.get("schema") != SCHEMA:
        raise AttentionKvRouteSelectorError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionKvRouteSelectorError("decision drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionKvRouteSelectorError("claim boundary drift")
    if payload.get("first_blocker") != FIRST_BLOCKER:
        raise AttentionKvRouteSelectorError("first blocker drift")
    validate_source_contract(payload.get("source_contract"))
    validate_snark_receipt(payload.get("external_snark_receipt"))
    validate_risc0_receipt(payload.get("external_risc0_receipt"))
    validate_risc0_sequence_receipt(payload.get("external_risc0_sequence_receipt"))
    validate_risc0_scaled_sequence_receipt(payload.get("external_risc0_scaled_sequence_receipt"))
    validate_risc0_wide_masked_sequence_receipt(payload.get("external_risc0_wide_masked_sequence_receipt"))
    validate_routes(payload.get("route_candidates"))
    if payload.get("proof_backed_routes_available") != [
        "external_snark_attention_kv_statement_receipt",
        "external_zkvm_attention_kv_semantics_receipt",
        "external_zkvm_attention_kv_sequence_semantics_receipt",
        "external_zkvm_attention_kv_scaled_sequence_semantics_receipt",
        "external_zkvm_attention_kv_wide_masked_sequence_semantics_receipt",
    ]:
        raise AttentionKvRouteSelectorError("proof-backed route relabeling")
    expected_metrics = {
        "snark_proof_size_bytes": payload["external_snark_receipt"]["proof_size_bytes"],
        "snark_public_signal_count": payload["external_snark_receipt"]["public_signal_count"],
        "risc0_receipt_size_bytes": payload["external_risc0_receipt"]["proof_size_bytes"],
        "risc0_verifier_time_ms": payload["external_risc0_receipt"]["verifier_time_ms"],
        "risc0_verifier_time_source": payload["external_risc0_receipt"]["verifier_time_source"],
        "risc0_sequence_receipt_size_bytes": payload["external_risc0_sequence_receipt"]["proof_size_bytes"],
        "risc0_sequence_verifier_time_ms": payload["external_risc0_sequence_receipt"]["verifier_time_ms"],
        "risc0_sequence_verifier_time_source": payload["external_risc0_sequence_receipt"]["verifier_time_source"],
        "risc0_scaled_sequence_receipt_size_bytes": payload["external_risc0_scaled_sequence_receipt"]["proof_size_bytes"],
        "risc0_scaled_sequence_verifier_time_ms": payload["external_risc0_scaled_sequence_receipt"]["verifier_time_ms"],
        "risc0_scaled_sequence_verifier_time_source": payload["external_risc0_scaled_sequence_receipt"]["verifier_time_source"],
        "risc0_wide_masked_sequence_receipt_size_bytes": payload["external_risc0_wide_masked_sequence_receipt"]["proof_size_bytes"],
        "risc0_wide_masked_sequence_verifier_time_ms": payload["external_risc0_wide_masked_sequence_receipt"]["verifier_time_ms"],
        "risc0_wide_masked_sequence_verifier_time_source": payload["external_risc0_wide_masked_sequence_receipt"]["verifier_time_source"],
        "proof_generation_time_ms": None,
        "verifier_time_ms": None,
        "timing_policy": payload["external_snark_receipt"]["timing_policy"],
        "risc0_timing_policy": payload["external_risc0_receipt"]["timing_policy"],
    }
    if payload.get("metrics") != expected_metrics:
        raise AttentionKvRouteSelectorError("metric smuggling")
    next_go_criteria = payload.get("next_go_criteria")
    if not isinstance(next_go_criteria, list) or any(not isinstance(item, str) for item in next_go_criteria):
        raise AttentionKvRouteSelectorError("next-go criteria drift")
    if tuple(next_go_criteria) != EXPECTED_NEXT_GO_CRITERIA:
        raise AttentionKvRouteSelectorError("next-go criteria drift")
    non_claims = payload.get("non_claims")
    if tuple(non_claims or ()) != EXPECTED_NON_CLAIMS:
        raise AttentionKvRouteSelectorError("non-claim drift")
    expected_commitment = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "source_contract": payload["source_contract"],
            "external_snark_receipt": payload["external_snark_receipt"],
            "external_risc0_receipt": payload["external_risc0_receipt"],
            "external_risc0_sequence_receipt": payload["external_risc0_sequence_receipt"],
            "external_risc0_scaled_sequence_receipt": payload["external_risc0_scaled_sequence_receipt"],
            "external_risc0_wide_masked_sequence_receipt": payload["external_risc0_wide_masked_sequence_receipt"],
            "route_candidates": payload["route_candidates"],
            "proof_backed_routes_available": payload["proof_backed_routes_available"],
            "metrics": payload["metrics"],
            "next_go_criteria": payload["next_go_criteria"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-proof-route-selector:v1",
    )
    if payload.get("selector_commitment") != expected_commitment:
        raise AttentionKvRouteSelectorError("selector commitment drift")
    if allow_missing_mutation_summary:
        return
    mutation_cases = payload.get("mutation_cases")
    if not isinstance(mutation_cases, list):
        raise AttentionKvRouteSelectorError("mutation cases must be a list")
    if tuple(item.get("name") for item in mutation_cases) != EXPECTED_MUTATION_NAMES:
        raise AttentionKvRouteSelectorError("mutation case names drift")
    if any(item.get("rejected") is not True for item in mutation_cases):
        raise AttentionKvRouteSelectorError("mutation rejection drift")
    if payload.get("mutations_checked") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("mutation count drift")
    if payload.get("mutations_rejected") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("mutation rejection count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvRouteSelectorError("fail-closed summary drift")


def to_tsv(payload: dict[str, Any]) -> str:
    """Render the selector result as a stable one-row TSV summary."""

    rows: list[str] = []
    writer = csv.DictWriter(_ListWriter(rows), fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "decision": payload["decision"],
            "first_blocker": payload["first_blocker"],
            "source_contract_decision": payload["source_contract"]["source_decision"],
            "source_contract_proof_status": payload["source_contract"]["source_proof_status"],
            "proof_backed_routes_available": len(payload["proof_backed_routes_available"]),
            "routes_checked": len(payload["route_candidates"]),
            "mutations_checked": payload["mutations_checked"],
            "mutations_rejected": payload["mutations_rejected"],
            "source_statement_commitment": payload["source_contract"]["source_statement_commitment"],
        }
    )
    return "".join(rows)


class _ListWriter:
    def __init__(self, rows: list[str]) -> None:
        """Create a minimal file-like adapter for csv.DictWriter."""

        self.rows = rows

    def write(self, value: str) -> int:
        """Append one CSV chunk and report the written byte count."""

        self.rows.append(value)
        return len(value)


def write_outputs(payload: dict[str, Any], json_out: pathlib.Path, tsv_out: pathlib.Path) -> None:
    """Validate and write the JSON/TSV evidence artifacts."""

    validate_payload(payload)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    tsv_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tsv_out.write_text(to_tsv(payload), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command-line flags for stdout and checked-in evidence output."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""

    args = parse_args()
    payload = build_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.no_write:
        write_outputs(payload, args.write_json, args.write_tsv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
