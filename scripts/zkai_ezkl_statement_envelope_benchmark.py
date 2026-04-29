#!/usr/bin/env python3
"""External EZKL relabeling benchmark for statement-bound zkAI artifacts.

This benchmark deliberately separates two questions:

1. Does the raw external proof verifier accept the proof?
2. Does a statement envelope reject model/input/output/config relabeling around
   that proof?

The first question is handled by EZKL's Python verifier over proof, settings,
verification key, and SRS. The second question is handled by a small envelope
policy that binds the human-facing statement to checked artifact hashes and then
delegates proof validity to EZKL.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import copy
import csv
import hashlib
import importlib.metadata
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "docs" / "engineering" / "evidence" / "zkai-ezkl-statement-envelope-2026-04"
SRS_URL = "https://kzg.ezkl.xyz/kzg17.srs"
BENCHMARK_SCHEMA = "zkai-ezkl-statement-envelope-benchmark-v1"
ENVELOPE_SCHEMA = "zkai-ezkl-statement-envelope-v1"
STATEMENT_SCHEMA = "zkai-external-statement-v1"
EZKL_VERSION = "23.0.5"
EZKL_VERIFIER_DOMAIN = f"ezkl-python-verify-v{EZKL_VERSION}"

EXPECTED_STATEMENT = {
    "model_id": "urn:zkai:ezkl-demo:identity-v1",
    "input_id": "urn:zkai:input:scalar-one-v1",
    "output_id": "urn:zkai:output:identity-scalar-one-v1",
    "quantization_config_id": "urn:zkai:ezkl-settings:identity-public-io-v1",
    "proof_system": "EZKL/Halo2-KZG",
    "proof_system_version": EZKL_VERSION,
    "verifier_domain": EZKL_VERIFIER_DOMAIN,
}

TSV_COLUMNS = [
    "adapter",
    "mutation",
    "category",
    "baseline_accepted",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
]
EXPECTED_ADAPTERS = ("ezkl-proof-only", "ezkl-statement-envelope")
EXPECTED_MUTATION_NAMES = (
    "config_id_relabeling",
    "input_id_relabeling",
    "model_artifact_hash_relabeling",
    "model_id_relabeling",
    "output_id_relabeling",
    "proof_public_instance_relabeling",
    "verifier_domain_relabeling",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)
EXPECTED_MUTATION_SET = frozenset(EXPECTED_MUTATION_NAMES)
EXPECTED_CASE_PAIRS = frozenset(
    (adapter, mutation) for adapter in EXPECTED_ADAPTERS for mutation in EXPECTED_MUTATION_NAMES
)


class EzklEnvelopeError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_path(name: str) -> pathlib.Path:
    path = (ARTIFACT_DIR / name).resolve()
    artifact_root = ARTIFACT_DIR.resolve()
    if artifact_root not in path.parents and path != artifact_root:
        raise EzklEnvelopeError(f"artifact path escapes evidence directory: {name}")
    return path


def _proof_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    proof = envelope.get("ezkl_proof")
    if not isinstance(proof, dict):
        raise EzklEnvelopeError("ezkl_proof must be an object")
    return proof


def proof_public_instances_sha256(proof: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(proof.get("instances")))


def proof_sha256(proof: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(proof))


def statement_commitment(statement: dict[str, Any]) -> str:
    return blake2b_commitment(statement, "ptvm:zkai:ezkl-statement:v1")


def baseline_envelope() -> dict[str, Any]:
    metadata = _load_json(ARTIFACT_DIR / "metadata.json")
    proof = _load_json(ARTIFACT_DIR / "proof.json")
    statement = {
        "schema": STATEMENT_SCHEMA,
        **EXPECTED_STATEMENT,
        "model_artifact_sha256": metadata["artifacts"]["identity.onnx"],
        "input_artifact_sha256": metadata["artifacts"]["input.json"],
        "settings_sha256": metadata["artifacts"]["settings.json"],
        "vk_sha256": metadata["artifacts"]["vk.key"],
        "proof_sha256": proof_sha256(proof),
        "public_instances_sha256": proof_public_instances_sha256(proof),
        "srs_url": metadata["srs_url"],
        "srs_sha256": metadata["srs_sha256"],
    }
    return {
        "schema": ENVELOPE_SCHEMA,
        "statement": statement,
        "statement_commitment": statement_commitment(statement),
        "artifacts": {
            "model_path": "identity.onnx",
            "input_path": "input.json",
            "settings_path": "settings.json",
            "vk_path": "vk.key",
        },
        "ezkl_proof": proof,
        "non_claims": [
            "not_a_performance_benchmark",
            "not_an_ezkl_security_audit",
            "not_a_system_ranking",
        ],
    }


def _refresh_statement_commitment(envelope: dict[str, Any]) -> None:
    envelope["statement_commitment"] = statement_commitment(envelope["statement"])


def mutate_first_public_instance(proof: dict[str, Any]) -> None:
    instances = proof.get("instances")
    if (
        not isinstance(instances, list)
        or not instances
        or not isinstance(instances[0], list)
        or not instances[0]
        or not isinstance(instances[0][0], str)
        or not instances[0][0]
    ):
        raise EzklEnvelopeError("baseline EZKL proof must contain a non-empty first public instance")
    first = instances[0][0]
    replacement_prefix = "8" if first.startswith("7") else "7"
    instances[0][0] = replacement_prefix + first[1:]


def mutated_envelopes() -> dict[str, tuple[str, dict[str, Any]]]:
    baseline = baseline_envelope()

    def mutate_statement(field: str, value: str, category: str) -> tuple[str, dict[str, Any]]:
        env = copy.deepcopy(baseline)
        env["statement"][field] = value
        _refresh_statement_commitment(env)
        return category, env

    out: dict[str, tuple[str, dict[str, Any]]] = {
        "model_id_relabeling": mutate_statement(
            "model_id",
            "urn:zkai:ezkl-demo:different-model-v1",
            "statement_policy",
        ),
        "input_id_relabeling": mutate_statement(
            "input_id",
            "urn:zkai:input:different-scalar-v1",
            "statement_policy",
        ),
        "output_id_relabeling": mutate_statement(
            "output_id",
            "urn:zkai:output:different-output-v1",
            "statement_policy",
        ),
        "config_id_relabeling": mutate_statement(
            "quantization_config_id",
            "urn:zkai:ezkl-settings:different-config-v1",
            "statement_policy",
        ),
        "verifier_domain_relabeling": mutate_statement(
            "verifier_domain",
            "ezkl-python-verify-v999.0.0",
            "domain_or_version_allowlist",
        ),
        "model_artifact_hash_relabeling": mutate_statement(
            "model_artifact_sha256",
            "00" * 32,
            "artifact_binding",
        ),
    }

    proof_env = copy.deepcopy(baseline)
    mutate_first_public_instance(proof_env["ezkl_proof"])
    proof_env["statement"]["proof_sha256"] = proof_sha256(proof_env["ezkl_proof"])
    proof_env["statement"]["public_instances_sha256"] = proof_public_instances_sha256(proof_env["ezkl_proof"])
    _refresh_statement_commitment(proof_env)
    out["proof_public_instance_relabeling"] = ("external_proof_verifier", proof_env)

    return out


def ensure_srs(path: pathlib.Path) -> pathlib.Path:
    if not path.exists():
        raise FileNotFoundError(
            f"missing EZKL KZG SRS at {path}; provision {SRS_URL} first "
            "and set ZKAI_EZKL_SRS_PATH or pass --srs-path"
        )
    if not path.is_file():
        raise FileNotFoundError(f"EZKL KZG SRS path must be a readable file: {path}")
    with path.open("rb") as handle:
        handle.read(1)
    return path


def ezkl_verify(
    proof: dict[str, Any],
    settings_path: pathlib.Path,
    vk_path: pathlib.Path,
    srs_path: pathlib.Path,
) -> None:
    try:
        import ezkl  # type: ignore
    except ImportError as err:
        raise EzklEnvelopeError("ezkl Python package is not installed") from err

    try:
        installed_version = importlib.metadata.version("ezkl")
    except importlib.metadata.PackageNotFoundError as err:
        raise EzklEnvelopeError("ezkl package metadata is not available") from err
    expected_version = EXPECTED_STATEMENT["proof_system_version"]
    if installed_version != expected_version:
        raise EzklEnvelopeError(
            f"installed ezkl version {installed_version} does not match expected {expected_version}"
        )

    with tempfile.TemporaryDirectory(prefix="zkai-ezkl-proof-") as raw_tmp:
        proof_path = pathlib.Path(raw_tmp) / "proof.json"
        proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True), encoding="utf-8")
        accepted = ezkl.verify(str(proof_path), str(settings_path), str(vk_path), str(srs_path))
    if accepted is not True:
        raise EzklEnvelopeError("EZKL proof verifier returned false")


def _check_statement_policy(statement: dict[str, Any]) -> None:
    if statement.get("schema") != STATEMENT_SCHEMA:
        raise EzklEnvelopeError("unsupported statement schema")
    for field, expected in EXPECTED_STATEMENT.items():
        if statement.get(field) != expected:
            raise EzklEnvelopeError(f"statement policy mismatch for /{field}")


def _check_artifact_hashes(envelope: dict[str, Any]) -> tuple[pathlib.Path, pathlib.Path]:
    statement = envelope["statement"]
    artifacts = envelope["artifacts"]
    model_path = _artifact_path(artifacts["model_path"])
    input_path = _artifact_path(artifacts["input_path"])
    settings_path = _artifact_path(artifacts["settings_path"])
    vk_path = _artifact_path(artifacts["vk_path"])
    expected = {
        "model_artifact_sha256": sha256_file(model_path),
        "input_artifact_sha256": sha256_file(input_path),
        "settings_sha256": sha256_file(settings_path),
        "vk_sha256": sha256_file(vk_path),
        "proof_sha256": proof_sha256(_proof_payload(envelope)),
        "public_instances_sha256": proof_public_instances_sha256(_proof_payload(envelope)),
    }
    for field, actual in expected.items():
        if statement.get(field) != actual:
            raise EzklEnvelopeError(f"artifact hash mismatch for /{field}")
    return settings_path, vk_path


def verify_statement_envelope(
    envelope: dict[str, Any],
    srs_path: pathlib.Path,
    *,
    external_verify: Callable[[dict[str, Any], pathlib.Path, pathlib.Path, pathlib.Path], None] = ezkl_verify,
) -> None:
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        raise EzklEnvelopeError("unsupported envelope schema")
    statement = envelope.get("statement")
    if not isinstance(statement, dict):
        raise EzklEnvelopeError("statement must be an object")
    if envelope.get("statement_commitment") != statement_commitment(statement):
        raise EzklEnvelopeError("statement_commitment mismatch")
    _check_statement_policy(statement)
    settings_path, vk_path = _check_artifact_hashes(envelope)
    if statement.get("srs_url") != SRS_URL:
        raise EzklEnvelopeError("unsupported SRS URL")
    if sha256_file(srs_path) != statement.get("srs_sha256"):
        raise EzklEnvelopeError("SRS hash mismatch")
    external_verify(_proof_payload(envelope), settings_path, vk_path, srs_path)


def verify_proof_only(
    envelope: dict[str, Any],
    srs_path: pathlib.Path,
    external_verify: Callable[[dict[str, Any], pathlib.Path, pathlib.Path, pathlib.Path], None] = ezkl_verify,
) -> None:
    artifacts = envelope["artifacts"]
    settings_path = _artifact_path(artifacts["settings_path"])
    vk_path = _artifact_path(artifacts["vk_path"])
    external_verify(_proof_payload(envelope), settings_path, vk_path, srs_path)


def classify_error(error: str) -> str:
    lowered = error.lower()
    if "ezkl" in lowered or "constraint system" in lowered or "proof verifier" in lowered:
        return "external_proof_verifier"
    if "artifact hash" in lowered:
        return "artifact_binding"
    if "domain" in lowered or "version" in lowered:
        return "domain_or_version_allowlist"
    if "policy mismatch" in lowered:
        return "statement_policy"
    if "commitment" in lowered:
        return "statement_commitment"
    if "srs" in lowered:
        return "srs_binding"
    return "adapter_policy"


def _case_result(
    adapter: str,
    envelope: dict[str, Any],
    srs_path: pathlib.Path,
    external_verify: Callable[[dict[str, Any], pathlib.Path, pathlib.Path, pathlib.Path], None],
) -> tuple[bool, str]:
    try:
        if adapter == "ezkl-proof-only":
            verify_proof_only(envelope, srs_path, external_verify=external_verify)
        elif adapter == "ezkl-statement-envelope":
            verify_statement_envelope(envelope, srs_path, external_verify=external_verify)
        else:
            raise EzklEnvelopeError(f"unsupported adapter {adapter!r}")
    except Exception as err:  # noqa: BLE001 - the benchmark records verifier failures.
        return False, str(err)
    return True, ""


def run_benchmark(
    srs_path: pathlib.Path,
    command: list[str] | None = None,
    external_verify: Callable[[dict[str, Any], pathlib.Path, pathlib.Path, pathlib.Path], None] = ezkl_verify,
) -> dict[str, Any]:
    ensure_srs(srs_path)
    srs_sha256 = sha256_file(srs_path)
    baseline = baseline_envelope()
    mutations = mutated_envelopes()
    if set(mutations) != EXPECTED_MUTATION_SET:
        raise RuntimeError("mutation corpus does not match expected external relabeling suite")
    cases = []
    for adapter in EXPECTED_ADAPTERS:
        baseline_accepted, baseline_error = _case_result(
            adapter, baseline, srs_path, external_verify
        )
        for mutation, (category, envelope) in sorted(mutations.items()):
            accepted, error = _case_result(adapter, envelope, srs_path, external_verify)
            cases.append(
                {
                    "adapter": adapter,
                    "mutation": mutation,
                    "category": category,
                    "baseline_accepted": baseline_accepted,
                    "baseline_error": baseline_error,
                    "mutated_accepted": accepted,
                    "rejected": not accepted,
                    "rejection_layer": classify_error(error) if not accepted else "accepted",
                    "error": error,
                }
            )

    summary = summarize_cases(cases)
    if summary is None:
        raise RuntimeError("benchmark case corpus does not match expected external relabeling suite")

    return {
        "schema": BENCHMARK_SCHEMA,
        "suite_kind": "external_ezkl_statement_relabeling",
        "external_system": {
            "name": "EZKL",
            "version": EXPECTED_STATEMENT["proof_system_version"],
            "verification_api": "ezkl.verify(proof_path, settings_path, vk_path, srs_path)",
            "srs_url": SRS_URL,
            "srs_sha256": srs_sha256,
        },
        "non_claims": [
            "not_a_performance_benchmark",
            "not_an_ezkl_security_audit",
            "not_a_system_ranking",
            "proof_only_no_go_is_limited_to_metadata_outside_the_ezkl_acceptance_path",
        ],
        "repro": {
            "git_commit": os.environ.get("ZKAI_EZKL_BENCHMARK_GIT_COMMIT", _git_commit()),
            "command": _canonical_command(command),
            "artifact_dir": str(ARTIFACT_DIR.relative_to(ROOT)),
            "artifact_metadata_sha256": sha256_file(ARTIFACT_DIR / "metadata.json"),
        },
        "cases": cases,
        "summary": summary,
    }


def _git_commit() -> str:
    import subprocess

    git = shutil.which("git")
    if git is None:
        return "unknown"
    try:
        return subprocess.check_output(
            [git, "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _canonical_command(command: list[str] | None) -> list[str]:
    override_json = os.environ.get("ZKAI_EZKL_BENCHMARK_COMMAND_JSON")
    if override_json:
        parsed = json.loads(override_json)
        if not isinstance(parsed, list) or not all(isinstance(part, str) for part in parsed):
            raise RuntimeError("ZKAI_EZKL_BENCHMARK_COMMAND_JSON must be a JSON array of strings")
        return parsed
    return command or []


def summarize_cases(cases: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(cases, list):
        return None
    pairs = []
    for case in cases:
        if not isinstance(case, dict):
            return None
        adapter = case.get("adapter")
        mutation = case.get("mutation")
        if adapter not in EXPECTED_ADAPTERS or mutation not in EXPECTED_MUTATION_SET:
            return None
        pairs.append((adapter, mutation))
    if len(pairs) != len(EXPECTED_CASE_PAIRS) or set(pairs) != EXPECTED_CASE_PAIRS:
        return None
    return {
        adapter: {
            "baseline_accepted": all(
                bool(case.get("baseline_accepted")) for case in cases if case["adapter"] == adapter
            ),
            "mutations_rejected": sum(
                1 for case in cases if case["adapter"] == adapter and bool(case.get("rejected"))
            ),
            "mutation_count": sum(1 for case in cases if case["adapter"] == adapter),
            "all_mutations_rejected": all(
                bool(case.get("rejected")) for case in cases if case["adapter"] == adapter
            ),
        }
        for adapter in EXPECTED_ADAPTERS
    }


def benchmark_passed(payload: dict[str, Any]) -> bool:
    summary = summarize_cases(payload.get("cases"))
    if summary is None:
        return False
    if payload.get("summary") != summary:
        return False
    proof_only = summary["ezkl-proof-only"]
    statement_envelope = summary["ezkl-statement-envelope"]
    proof_cases = {
        case["mutation"]: case
        for case in payload["cases"]
        if case["adapter"] == "ezkl-proof-only"
    }
    return (
        proof_only["baseline_accepted"]
        and statement_envelope["baseline_accepted"]
        and proof_only["mutations_rejected"] == 1
        and bool(proof_cases["proof_public_instance_relabeling"].get("rejected"))
        and statement_envelope["all_mutations_rejected"]
    )


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for case in payload["cases"]:
        writer.writerow({column: case[column] for column in TSV_COLUMNS})
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--srs-path",
        type=pathlib.Path,
        default=pathlib.Path(os.environ.get("ZKAI_EZKL_SRS_PATH", "/tmp/ptvm-ezkl-kzg17.srs")),
        help="path to the EZKL kzg17 SRS cache",
    )
    parser.add_argument("--json", action="store_true", help="print JSON result")
    parser.add_argument("--tsv", action="store_true", help="print TSV result")
    parser.add_argument("--write-json", type=pathlib.Path, help="write JSON result to this path")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write TSV result to this path")
    args = parser.parse_args(argv)

    payload = run_benchmark(args.srs_path, command=[os.environ.get("PYTHON", "python3"), *sys.argv])
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
    passed = benchmark_passed(payload)
    if not (args.json or args.tsv or args.write_json or args.write_tsv):
        summary = payload["summary"]
        print(
            f"{'PASS' if passed else 'FAIL'}: "
            f"proof-only rejected {summary['ezkl-proof-only']['mutations_rejected']}/"
            f"{summary['ezkl-proof-only']['mutation_count']} mutations; "
            f"statement-envelope rejected {summary['ezkl-statement-envelope']['mutations_rejected']}/"
            f"{summary['ezkl-statement-envelope']['mutation_count']} mutations"
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
