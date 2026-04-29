#!/usr/bin/env python3
"""Compose a checked Stwo zkAIStatementReceiptV1 into AgentStepReceiptV1.

This harness is intentionally a composition gate, not a new proof verifier. It
consumes the checked Stwo statement-envelope benchmark from the native Stwo gate,
requires that result to pass, then binds the statement commitment into an
AgentStepReceiptV1 model_receipt_commitment and mutates both layers to verify
fail-closed behavior.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts" / "agent_step_receipt_relabeling_harness.py"
STWO_BENCHMARK_PATH = ROOT / "scripts" / "zkai_stwo_statement_envelope_benchmark.py"
DEFAULT_STWO_EVIDENCE_PATH = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-stwo-statement-envelope-benchmark-2026-04.json"
)
DEFAULT_ARTIFACT_DIR = (
    ROOT / "docs" / "engineering" / "evidence" / "agent-step-zkai-stwo-composition-2026-04"
)
_CHECKED_STWO_EVIDENCE_CACHE: dict[pathlib.Path, dict[str, Any]] = {}
COMPOSITION_SCHEMA = "agent-step-zkai-stwo-composition-v1"
COMPOSED_BUNDLE_SCHEMA = "agent-step-zkai-stwo-composed-bundle-v1"
TSV_COLUMNS = [
    "mutation",
    "surface",
    "baseline_accepted",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
]
AGENT_FIELD_TO_STWO_STATEMENT = {
    "model_identity": "model_id",
    "model_commitment": "model_artifact_commitment",
    "model_config_commitment": "config_commitment",
    "model_receipt_commitment": "statement_commitment",
    "observation_commitment": "input_commitment",
    "action_commitment": "output_commitment",
    "runtime_domain": "verifier_domain",
}


class CompositionError(ValueError):
    pass


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = _load_module("agent_step_receipt_harness_for_composition", HARNESS_PATH)
STWO = _load_module("zkai_stwo_statement_envelope_for_composition", STWO_BENCHMARK_PATH)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_label(path: pathlib.Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _git_commit() -> str:
    override = os.environ.get("AGENT_ZKAI_COMPOSITION_GIT_COMMIT")
    if override:
        return override
    git = shutil.which("git")
    if git is None:
        return "unknown"
    try:
        return subprocess.check_output(
            [git, "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _canonical_command(command: list[str] | None) -> list[str]:
    override = os.environ.get("AGENT_ZKAI_COMPOSITION_COMMAND_JSON")
    if override:
        parsed = json.loads(override)
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise RuntimeError("AGENT_ZKAI_COMPOSITION_COMMAND_JSON must be a JSON array of strings")
        return parsed
    return command or []


def load_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as err:
        raise CompositionError(f"failed to load JSON {path}: {err}") from err


def _source_evidence_path(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise CompositionError(f"source evidence path escapes repository: {path}")
    if not resolved.is_file():
        raise CompositionError(f"source evidence path is missing: {path}")
    return resolved


def _validate_stwo_evidence_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise CompositionError("Stwo evidence must be a JSON object")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise CompositionError("Stwo evidence lacks a valid summary")
    statement = summary.get("stwo-statement-envelope")
    if not isinstance(statement, dict):
        raise CompositionError("Stwo evidence lacks statement-envelope summary")
    proof_only = summary.get("stwo-proof-only")
    if not isinstance(proof_only, dict):
        raise CompositionError("Stwo evidence lacks proof-only summary")
    if payload.get("schema") != STWO.BENCHMARK_SCHEMA:
        raise CompositionError(f"unsupported Stwo benchmark schema {payload.get('schema')!r}")
    if payload.get("suite_kind") != "native_stwo_statement_relabeling":
        raise CompositionError("Stwo evidence is not the native statement relabeling suite")
    external = payload.get("external_system")
    if not isinstance(external, dict):
        raise CompositionError("Stwo evidence lacks external_system metadata")
    if external.get("name") != "ptvm-stwo-backend":
        raise CompositionError("Stwo evidence names an unexpected external system")
    if external.get("version") != STWO.STWO_PROOF_SYSTEM_VERSION:
        raise CompositionError("Stwo evidence version does not match the checked native primitive")
    if not STWO.benchmark_passed(payload):
        raise CompositionError("checked Stwo statement-envelope benchmark did not pass")
    if statement.get("mutations_rejected") != STWO.EXPECTED_MUTATION_COUNT:
        raise CompositionError("Stwo statement-envelope mutation count is incomplete")
    if proof_only.get("mutations_rejected") != 1:
        raise CompositionError("Stwo proof-only calibration no longer matches the checked gate")
    return payload


def checked_stwo_evidence(path: pathlib.Path) -> dict[str, Any]:
    evidence_path = _source_evidence_path(path)
    cached = _CHECKED_STWO_EVIDENCE_CACHE.get(evidence_path)
    if cached is None:
        cached = _validate_stwo_evidence_payload(load_json(evidence_path))
        _CHECKED_STWO_EVIDENCE_CACHE[evidence_path] = copy.deepcopy(cached)
    return copy.deepcopy(cached)


def _checked_stwo_payload(stwo_evidence: dict[str, Any]) -> dict[str, Any]:
    checked_stwo_evidence_path = stwo_evidence.get("_source_path")
    if checked_stwo_evidence_path is not None:
        return checked_stwo_evidence(pathlib.Path(checked_stwo_evidence_path))
    return _validate_stwo_evidence_payload(stwo_evidence)


def _assert_evidence_matches_envelope(stwo_evidence: dict[str, Any], envelope: dict[str, Any]) -> None:
    cases = stwo_evidence.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CompositionError("Stwo benchmark evidence has no cases")
    proof = STWO.stwo_proof_payload(envelope)
    proof_sha256 = STWO.proof_sha256(proof)
    public_instance_commitment = STWO.public_instance_commitment(proof)
    commitments = {
        case.get("baseline_statement_commitment")
        for case in cases
        if isinstance(case, dict)
    }
    if commitments != {envelope.get("statement_commitment")}:
        raise CompositionError("checked Stwo evidence baseline statement commitment mismatch")
    statement_hashes = {
        case.get("baseline_statement_sha256")
        for case in cases
        if isinstance(case, dict)
    }
    if statement_hashes != {STWO.statement_payload_sha256(envelope)}:
        raise CompositionError("checked Stwo evidence baseline statement payload mismatch")
    proof_hashes = {
        case.get("baseline_statement", {}).get("proof_commitment")
        for case in cases
        if isinstance(case, dict) and isinstance(case.get("baseline_statement"), dict)
    }
    if proof_hashes != {proof_sha256}:
        raise CompositionError("checked Stwo evidence baseline proof payload mismatch")
    public_instance_commitments = {
        case.get("baseline_public_instance_commitment")
        for case in cases
        if isinstance(case, dict)
    }
    if public_instance_commitments != {public_instance_commitment}:
        raise CompositionError("checked Stwo evidence baseline public instance mismatch")


def _assert_stwo_envelope_checked(envelope: dict[str, Any]) -> None:
    def checked_elsewhere(_proof: dict[str, Any]) -> None:
        return None

    STWO.verify_statement_envelope(envelope, external_verify=checked_elsewhere)


def baseline_stwo_envelope() -> dict[str, Any]:
    envelope = STWO.baseline_envelope()
    _assert_stwo_envelope_checked(envelope)
    return envelope


def _statement_commitment_for_agent(envelope: dict[str, Any]) -> str:
    return str(envelope["statement_commitment"])


def zkai_statement_receipt_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    statement = copy.deepcopy(envelope["statement"])
    return {
        "schema": STWO.STATEMENT_SCHEMA,
        "statement_commitment": envelope["statement_commitment"],
        **statement,
    }


def _set_trust_class(bundle: dict[str, Any], field_path: str, trust_class: str) -> None:
    for entry in bundle["receipt"]["field_trust_class_vector"]:
        if entry["field_path"] == field_path:
            entry["trust_class"] = trust_class
            return
    raise CompositionError(f"trust vector is missing {field_path}")


def _set_evidence(
    bundle: dict[str, Any],
    field_path: str,
    *,
    evidence_kind: str,
    trust_class: str,
) -> None:
    field = field_path[1:]
    for entry in bundle["evidence_manifest"]["entries"]:
        if entry["corresponding_receipt_field"] == field_path:
            entry["evidence_kind"] = evidence_kind
            entry["trust_class"] = trust_class
            entry["commitment"] = HARNESS._evidence_commitment_for_field(field_path, bundle["receipt"][field])
            entry["non_claims"] = sorted(
                set(entry["non_claims"]) | {"does-not-prove-agent-truthfulness"},
                key=lambda item: item.encode("utf-8"),
            )
            return
    raise CompositionError(f"evidence manifest is missing {field_path}")


def build_composed_bundle(envelope: dict[str, Any] | None = None) -> dict[str, Any]:
    envelope = baseline_stwo_envelope() if envelope is None else copy.deepcopy(envelope)
    statement = envelope["statement"]
    bundle = HARNESS.build_valid_bundle()
    receipt = bundle["receipt"]
    receipt["runtime_domain"] = statement["verifier_domain"]
    receipt["model_identity"] = statement["model_id"]
    receipt["model_commitment"] = statement["model_artifact_commitment"]
    receipt["model_config_commitment"] = statement["config_commitment"]
    receipt["model_receipt_commitment"] = _statement_commitment_for_agent(envelope)
    receipt["observation_commitment"] = statement["input_commitment"]
    receipt["action_commitment"] = statement["output_commitment"]

    for field in (
        "runtime_domain",
        "model_identity",
        "model_commitment",
        "model_config_commitment",
        "model_receipt_commitment",
        "observation_commitment",
        "action_commitment",
    ):
        _set_trust_class(bundle, f"/{field}", "proved")
        _set_evidence(bundle, f"/{field}", evidence_kind="subreceipt", trust_class="proved")

    HARNESS.recompute_manifest_commitments(bundle)
    return bundle


def _agent_fields_match_statement(bundle: dict[str, Any], envelope: dict[str, Any]) -> None:
    receipt = bundle["receipt"]
    statement = envelope["statement"]
    for agent_field, stwo_field in AGENT_FIELD_TO_STWO_STATEMENT.items():
        expected = envelope["statement_commitment"] if stwo_field == "statement_commitment" else statement[stwo_field]
        if receipt[agent_field] != expected:
            raise CompositionError(
                f"AgentStepReceiptV1 /{agent_field} does not match zkAIStatementReceiptV1 {stwo_field}"
            )


def verify_composition(
    bundle: dict[str, Any],
    *,
    envelope: dict[str, Any],
    stwo_evidence: dict[str, Any],
) -> bool:
    stwo_evidence = _checked_stwo_payload(stwo_evidence)
    _assert_stwo_envelope_checked(envelope)
    _assert_evidence_matches_envelope(stwo_evidence, envelope)
    _agent_fields_match_statement(bundle, envelope)
    HARNESS.verify_bundle(bundle)
    return True


def _source_evidence_with_path(path: pathlib.Path) -> dict[str, Any]:
    payload = checked_stwo_evidence(path)
    payload = copy.deepcopy(payload)
    payload["_source_path"] = str(path.resolve())
    return payload


def _composition_case(
    name: str,
    surface: str,
    bundle: dict[str, Any],
    envelope: dict[str, Any],
    stwo_evidence: dict[str, Any],
) -> dict[str, Any]:
    try:
        verify_composition(bundle, envelope=envelope, stwo_evidence=stwo_evidence)
    except (CompositionError, HARNESS.AgentReceiptError, STWO.StwoEnvelopeError) as err:
        return {
            "mutation": name,
            "surface": surface,
            "baseline_accepted": True,
            "mutated_accepted": False,
            "rejected": True,
            "rejection_layer": classify_composition_error(err),
            "error": str(err),
        }
    return {
        "mutation": name,
        "surface": surface,
        "baseline_accepted": True,
        "mutated_accepted": True,
        "rejected": False,
        "rejection_layer": "accepted",
        "error": "",
    }


def classify_composition_error(error: BaseException) -> str:
    if isinstance(error, HARNESS.AgentReceiptError):
        return "agent_receipt_verifier"
    if isinstance(error, STWO.StwoEnvelopeError):
        return "zkai_statement_receipt"
    lowered = str(error).lower()
    if "does not match zkaistatementreceiptv1" in lowered:
        return "agent_to_zkai_link_binding"
    if (
        "benchmark" in lowered
        or "mutation count" in lowered
        or "calibration" in lowered
        or "checked stwo evidence" in lowered
        or "source evidence" in lowered
    ):
        return "checked_source_evidence"
    return "composition_verifier"


def mutation_cases(stwo_evidence_path: pathlib.Path) -> list[dict[str, Any]]:
    envelope = baseline_stwo_envelope()
    evidence = _source_evidence_with_path(stwo_evidence_path)
    cases: list[dict[str, Any]] = []

    for mutation, mutate in sorted(HARNESS.mutation_cases().items()):
        bundle = build_composed_bundle(envelope)
        if mutation == "trust_class_upgrade_without_proof":
            for entry in bundle["receipt"]["field_trust_class_vector"]:
                if entry["field_path"] == "/tool_receipts_root":
                    entry["trust_class"] = "proved"
                    break
            else:
                raise CompositionError("trust vector is missing /tool_receipts_root")
            HARNESS.recompute_receipt_commitment(bundle)
        else:
            mutate(bundle)
        cases.append(_composition_case(mutation, "agent_receipt", bundle, envelope, evidence))

    for mutation, (_category, mutated_envelope) in sorted(STWO.mutated_envelopes().items()):
        bundle = build_composed_bundle(envelope)
        cases.append(
            _composition_case(
                f"zkai_{mutation}",
                "zkai_statement_receipt",
                bundle,
                mutated_envelope,
                evidence,
            )
        )

    _category, mutated_subreceipt = STWO.mutated_envelopes()["model_id_relabeling"]
    self_consistent = build_composed_bundle(mutated_subreceipt)
    cases.append(
        _composition_case(
            "agent_points_to_mutated_zkai_subreceipt",
            "cross_layer_composition",
            self_consistent,
            mutated_subreceipt,
            evidence,
        )
    )

    tampered_evidence = copy.deepcopy(evidence)
    for case in tampered_evidence["cases"]:
        if case["adapter"] == "stwo-statement-envelope" and case["mutation"] == "model_id_relabeling":
            case["rejected"] = False
            case["mutated_accepted"] = True
            case["rejection_layer"] = "accepted"
            case["error"] = ""
            break
    tampered_evidence.pop("_source_path", None)
    cases.append(
        _composition_case(
            "checked_stwo_evidence_tampered",
            "source_evidence",
            build_composed_bundle(envelope),
            envelope,
            tampered_evidence,
        )
    )
    return cases


def _run_rust_agent_verifier(
    bundle_path: pathlib.Path,
    model_subreceipt_path: pathlib.Path,
    checked_stwo_evidence_path: pathlib.Path,
) -> dict[str, Any]:
    cmd = [
        "cargo",
        "run",
        "--quiet",
        "--example",
        "agent_step_zkai_stwo_receipt_verify",
        "--",
        str(bundle_path),
        str(model_subreceipt_path),
        str(checked_stwo_evidence_path),
    ]
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise CompositionError(
            "Rust AgentStepReceiptV1 verifier command failed: "
            f"stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as err:
        raise CompositionError(f"Rust AgentStepReceiptV1 verifier returned invalid JSON: {err}") from err
    if payload.get("schema") != "agent-step-zkai-stwo-rust-callback-verifier-v1":
        raise CompositionError("Rust AgentStepReceiptV1 verifier returned an unexpected schema")
    results = payload.get("results")
    if not isinstance(results, list) or len(results) != 1:
        raise CompositionError("Rust AgentStepReceiptV1 verifier returned malformed results")
    result = results[0]
    if result.get("case_id") != "baseline" or result.get("accepted") is not True:
        raise CompositionError(f"Rust AgentStepReceiptV1 verifier rejected baseline: {result}")
    return payload


def run_composition(
    *,
    stwo_evidence_path: pathlib.Path = DEFAULT_STWO_EVIDENCE_PATH,
    artifact_dir: pathlib.Path = DEFAULT_ARTIFACT_DIR,
    rust_verify: bool = False,
    command: list[str] | None = None,
) -> dict[str, Any]:
    source_evidence = _source_evidence_with_path(stwo_evidence_path)
    envelope = baseline_stwo_envelope()
    bundle = build_composed_bundle(envelope)
    verify_composition(bundle, envelope=envelope, stwo_evidence=source_evidence)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = artifact_dir / "agent_step_zkai_stwo_composed_receipt.json"
    bundle_path.write_bytes(canonical_json_bytes(bundle) + b"\n")
    subreceipt_path = artifact_dir / "zkai_stwo_statement_receipt.json"
    subreceipt_path.write_bytes(canonical_json_bytes(zkai_statement_receipt_payload(envelope)) + b"\n")

    rust_result = None
    if rust_verify:
        rust_result = _run_rust_agent_verifier(
            bundle_path,
            subreceipt_path,
            _source_evidence_path(stwo_evidence_path),
        )

    cases = mutation_cases(stwo_evidence_path)
    passed = all(case["rejected"] for case in cases)
    statement = envelope["statement"]
    result = {
        "schema": COMPOSITION_SCHEMA,
        "suite_kind": "agent_step_zkai_statement_receipt_composition",
        "result": "GO" if passed else "NO_GO",
        "non_claims": [
            "not_end_to_end_verifiable_intelligence",
            "not_full_transformer_inference",
            "not_a_new_stwo_security_audit",
            "not_backend_independence",
            "does_not_prove_agent_truthfulness_or_policy_semantics",
        ],
        "repro": {
            "git_commit": _git_commit(),
            "command": _canonical_command(command),
        },
        "source_stwo_statement_evidence": {
            "path": str(_source_evidence_path(stwo_evidence_path).relative_to(ROOT)),
            "sha256": file_sha256(_source_evidence_path(stwo_evidence_path)),
            "schema": source_evidence["schema"],
            "summary": source_evidence["summary"],
            "external_system": source_evidence["external_system"],
        },
        "composed_agent_receipt": {
            "schema": COMPOSED_BUNDLE_SCHEMA,
            "path": _path_label(bundle_path),
            "model_subreceipt_path": _path_label(subreceipt_path),
            "sha256": file_sha256(bundle_path),
            "model_subreceipt_sha256": file_sha256(subreceipt_path),
            "receipt_commitment": bundle["receipt"]["receipt_commitment"],
            "model_receipt_commitment": bundle["receipt"]["model_receipt_commitment"],
            "model_receipt_statement_commitment": envelope["statement_commitment"],
            "agent_field_to_zkai_statement_field": AGENT_FIELD_TO_STWO_STATEMENT,
            "rust_agent_receipt_verifier": rust_result,
        },
        "zkai_statement_receipt": {
            "receipt_version": statement["receipt_version"],
            "verifier_domain": statement["verifier_domain"],
            "proof_system": statement["proof_system"],
            "proof_system_version": statement["proof_system_version"],
            "statement_kind": statement["statement_kind"],
            "model_id": statement["model_id"],
            "statement_commitment": envelope["statement_commitment"],
        },
        "baseline_accepted": True,
        "case_count": len(cases),
        "all_mutations_rejected": passed,
        "cases": cases,
        "summary": {
            "agent_receipt_mutations": sum(1 for case in cases if case["surface"] == "agent_receipt"),
            "zkai_statement_receipt_mutations": sum(1 for case in cases if case["surface"] == "zkai_statement_receipt"),
            "cross_layer_composition_mutations": sum(1 for case in cases if case["surface"] == "cross_layer_composition"),
            "source_evidence_mutations": sum(1 for case in cases if case["surface"] == "source_evidence"),
            "mutations_rejected": sum(1 for case in cases if case["rejected"]),
        },
    }
    return result


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for case in payload["cases"]:
        row = {column: case[column] for column in TSV_COLUMNS}
        if row["error"] == "":
            row["error"] = "none"
        writer.writerow(row)
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stwo-evidence", type=pathlib.Path, default=DEFAULT_STWO_EVIDENCE_PATH)
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--rust-verify", action="store_true", help="also validate the composed bundle with the Rust AgentStepReceiptV1 parser")
    parser.add_argument("--json", action="store_true", help="print JSON result")
    parser.add_argument("--tsv", action="store_true", help="print TSV result")
    parser.add_argument("--write-json", type=pathlib.Path, help="write JSON result")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write TSV result")
    args = parser.parse_args(argv)

    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    payload = run_composition(
        stwo_evidence_path=args.stwo_evidence,
        artifact_dir=args.artifact_dir,
        rust_verify=args.rust_verify,
        command=[os.environ.get("PYTHON", "python3"), "scripts/agent_step_zkai_stwo_composition.py", *effective_argv],
    )
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tsv_text = to_tsv(payload)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json_text, encoding="utf-8")
    if args.write_tsv:
        args.write_tsv.parent.mkdir(parents=True, exist_ok=True)
        args.write_tsv.write_text(tsv_text, encoding="utf-8")
    if args.json:
        print(json_text, end="")
    if args.tsv:
        print(tsv_text, end="")
    if not (args.json or args.tsv or args.write_json or args.write_tsv):
        summary = payload["summary"]
        print(
            f"{payload['result']}: rejected {summary['mutations_rejected']}/{payload['case_count']} "
            "agent/zkAI composition mutations"
        )
    return 0 if payload["baseline_accepted"] and payload["all_mutations_rejected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
