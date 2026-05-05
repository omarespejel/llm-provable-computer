#!/usr/bin/env python3
"""Route selector for proof-backed attention/KV-cache receipts.

This gate consumes the existing source-backed attention/KV transition receipt
and asks whether the repository currently has a proof-backed route for the same
public statement fields. The current answer is a narrow GO for one route: an
external snarkjs/Groth16 statement receipt over the source-backed attention/KV
contract. Native attention arithmetic, Softmax, zkVM, and recursion remain
explicitly outside the current proof route.
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
SOURCE_EVIDENCE_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-transition-receipt-2026-05.json"
)
SNARK_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-snark-statement-receipt-2026-05.json"
)
JSON_OUT = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-proof-route-selector-2026-05.json"
)
TSV_OUT = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-proof-route-selector-2026-05.tsv"
)

SCHEMA = "zkai-attention-kv-proof-route-selector-gate-v1"
DECISION = "GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_ATTENTION_KV_SOURCE_CONTRACT"
FIRST_BLOCKER = "NO_NATIVE_ATTENTION_ARITHMETIC_PROOF_BACKEND"
CLAIM_BOUNDARY = "EXTERNAL_SNARK_STATEMENT_RECEIPT_PROOF_BACKED_NOT_ATTENTION_ARITHMETIC_PROOF"
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

BASE_ROUTES = (
    {
        "route_id": "source_backed_attention_kv_receipt_contract",
        "status": "GO_SOURCE_CONTRACT_ONLY",
        "blocker": "NOT_PROOF_BACKED",
        "usable_today": True,
        "proof_backed": False,
    },
    {
        "route_id": "local_stwo_attention_kv_transition_proof",
        "status": "NO_GO_MISSING_NATIVE_ATTENTION_KV_PROOF_ARTIFACT",
        "blocker": "NO_EXECUTABLE_NATIVE_ATTENTION_KV_PROOF_SURFACE",
        "usable_today": False,
        "proof_backed": False,
    },
    {
        "route_id": "external_snark_attention_kv_statement_receipt",
        "status": "GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_SOURCE_CONTRACT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": "external_zkvm_attention_kv_statement_receipt",
        "status": "NO_GO_MISSING_ATTENTION_KV_JOURNAL_AND_RECEIPT_ARTIFACT",
        "blocker": "NO_ATTENTION_KV_ZKVM_JOURNAL_OR_RECEIPT_FOR_THIS_PUBLIC_INSTANCE",
        "usable_today": False,
        "proof_backed": False,
    },
    {
        "route_id": "softmax_attention_kv_claim",
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
    "external_zkvm_route_relabel_go",
    "fake_verifier_time_metric",
    "fake_proof_size_metric",
    "next_go_criteria_weakened",
    "claim_boundary_weakened",
    "first_blocker_removed",
    "unknown_field_injection",
)

EXPECTED_NEXT_GO_CRITERIA = (
    "native Stwo proof or zkVM receipt verifies the same public-instance fields",
    "a native proof checks the attention arithmetic instead of only wrapping the source-backed contract",
    "prior KV, input/query, attention output, next KV, verifier domain, proof status, and statement commitment relabels reject after proof serialization",
    "Softmax is kept out of scope unless the proof covers Softmax semantics",
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


SOURCE = _load_source_module()
SNARK = _load_snark_module()


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


def route_inventory() -> list[dict[str, Any]]:
    """Return the checked route candidates as fresh dictionaries."""

    snark = snark_receipt_summary(load_snark_payload())
    routes = [dict(route) for route in BASE_ROUTES]
    snark_route = next(
        (
            route
            for route in routes
            if route.get("route_id") == "external_snark_attention_kv_statement_receipt"
        ),
        None,
    )
    if snark_route is None:
        raise AttentionKvRouteSelectorError("missing external SNARK route candidate")
    snark_route["evidence"] = snark["evidence"]
    snark_route["proof_system"] = snark["proof_system"]
    snark_route["proof_size_bytes"] = snark["proof_size_bytes"]
    snark_route["public_signal_count"] = snark["public_signal_count"]
    snark_route["statement_commitment"] = snark["statement_commitment"]
    snark_route["receipt_commitment"] = snark["receipt_commitment"]
    return routes


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
    summary = source_contract_summary(source_payload)
    snark_summary = snark_receipt_summary(snark_payload)
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
        "route_candidates": routes,
        "proof_backed_routes_available": proof_backed_routes_available,
        "metrics": {
            "proof_size_bytes": snark_summary["proof_size_bytes"],
            "public_signal_count": snark_summary["public_signal_count"],
            "proof_generation_time_ms": None,
            "verifier_time_ms": None,
            "timing_policy": snark_summary["timing_policy"],
        },
        "next_go_criteria": list(EXPECTED_NEXT_GO_CRITERIA),
        "non_claims": [
            "not a native attention arithmetic proof",
            "not a Stwo proof",
            "not a Softmax proof",
            "not full autoregressive inference",
            "not agent correctness",
            "not a zkVM receipt",
            "not recursive or proof-carrying data",
            "not a benchmark row",
        ],
    }
    payload["selector_commitment"] = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "source_contract": payload["source_contract"],
            "external_snark_receipt": payload["external_snark_receipt"],
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
        out["route_candidates"][1]["status"] = "GO_NATIVE_STWO_ATTENTION_KV_PROOF"
        out["route_candidates"][1]["usable_today"] = True
        out["route_candidates"][1]["proof_backed"] = True
        out["proof_backed_routes_available"] = ["local_stwo_attention_kv_transition_proof"]
    elif name == "external_snark_route_removed":
        out["route_candidates"][2]["status"] = "NO_GO_MISSING_ATTENTION_KV_SNARK_RECEIPT"
        out["route_candidates"][2]["usable_today"] = False
        out["route_candidates"][2]["proof_backed"] = False
        out["proof_backed_routes_available"] = []
    elif name == "external_snark_receipt_decision_drift":
        out["external_snark_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_SNARK_RECEIPT"
    elif name == "external_snark_receipt_mutation_rejections_drift":
        out["external_snark_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_route_relabel_go":
        out["route_candidates"][3]["status"] = "GO_ZKVM_ATTENTION_KV_STATEMENT_RECEIPT"
        out["route_candidates"][3]["usable_today"] = True
        out["route_candidates"][3]["proof_backed"] = True
        out["proof_backed_routes_available"] = ["external_zkvm_attention_kv_statement_receipt"]
    elif name == "fake_verifier_time_metric":
        out["metrics"]["verifier_time_ms"] = 7.5
    elif name == "fake_proof_size_metric":
        out["metrics"]["proof_size_bytes"] = 1024
    elif name == "next_go_criteria_weakened":
        out["next_go_criteria"] = ["any zkVM receipt wraps the source-backed contract"]
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
    validate_routes(payload.get("route_candidates"))
    if payload.get("proof_backed_routes_available") != ["external_snark_attention_kv_statement_receipt"]:
        raise AttentionKvRouteSelectorError("proof-backed route relabeling")
    expected_metrics = {
        "proof_size_bytes": payload["external_snark_receipt"]["proof_size_bytes"],
        "public_signal_count": payload["external_snark_receipt"]["public_signal_count"],
        "proof_generation_time_ms": None,
        "verifier_time_ms": None,
        "timing_policy": payload["external_snark_receipt"]["timing_policy"],
    }
    if payload.get("metrics") != expected_metrics:
        raise AttentionKvRouteSelectorError("metric smuggling")
    next_go_criteria = payload.get("next_go_criteria")
    if not isinstance(next_go_criteria, list) or any(not isinstance(item, str) for item in next_go_criteria):
        raise AttentionKvRouteSelectorError("next-go criteria drift")
    if tuple(next_go_criteria) != EXPECTED_NEXT_GO_CRITERIA:
        raise AttentionKvRouteSelectorError("next-go criteria drift")
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or any("not " not in str(item) for item in non_claims):
        raise AttentionKvRouteSelectorError("non-claim drift")
    expected_commitment = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "source_contract": payload["source_contract"],
            "external_snark_receipt": payload["external_snark_receipt"],
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
