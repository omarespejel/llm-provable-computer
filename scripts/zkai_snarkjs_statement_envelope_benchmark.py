#!/usr/bin/env python3
"""External snarkjs/Groth16 relabeling benchmark for statement-bound zkAI artifacts."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "docs" / "engineering" / "evidence" / "zkai-snarkjs-statement-envelope-2026-04"
BENCHMARK_SCHEMA = "zkai-snarkjs-statement-envelope-benchmark-v1"
ENVELOPE_SCHEMA = "zkai-snarkjs-statement-envelope-v1"
STATEMENT_SCHEMA = "zkai-external-statement-v1"
SNARKJS_VERSION = "0.7.6"
SNARKJS_VERIFIER_DOMAIN = f"snarkjs-groth16-verify-v{SNARKJS_VERSION}"
SNARKJS_COMMAND = ("npx", "-y", f"snarkjs@{SNARKJS_VERSION}")
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
EXPECTED_STATEMENT = {
    "model_id": "urn:zkai:snarkjs-demo:square-v1",
    "input_id": "urn:zkai:input:scalar-seven-v1",
    "output_id": "urn:zkai:output:square-scalar-forty-nine-v1",
    "quantization_config_id": "urn:zkai:snarkjs-settings:square-public-io-v1",
    "proof_system": "snarkjs/Groth16/BN128",
    "proof_system_version": SNARKJS_VERSION,
    "verifier_domain": SNARKJS_VERIFIER_DOMAIN,
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
EXPECTED_ADAPTERS = ("snarkjs-proof-only", "snarkjs-statement-envelope")
EXPECTED_MUTATION_NAMES = (
    "circuit_artifact_hash_relabeling",
    "config_id_relabeling",
    "input_artifact_hash_relabeling",
    "input_id_relabeling",
    "model_id_relabeling",
    "output_id_relabeling",
    "proof_hash_relabeling",
    "proof_system_version_relabeling",
    "public_signal_relabeling",
    "setup_commitment_relabeling",
    "statement_commitment_relabeling",
    "verifier_domain_relabeling",
    "verification_key_file_hash_relabeling",
    "verification_key_hash_relabeling",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)
EXPECTED_MUTATION_SET = frozenset(EXPECTED_MUTATION_NAMES)
EXPECTED_CASE_PAIRS = frozenset(
    (adapter, mutation) for adapter in EXPECTED_ADAPTERS for mutation in EXPECTED_MUTATION_NAMES
)


class SnarkjsEnvelopeError(ValueError):
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
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def proof_sha256(proof: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(proof))


def public_signals_sha256(public_signals: list[Any]) -> str:
    return sha256_bytes(canonical_json_bytes(public_signals))


def verification_key_sha256(vk: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(vk))


def statement_commitment(statement: dict[str, Any]) -> str:
    return blake2b_commitment(statement, "ptvm:zkai:snarkjs-statement:v1")


def statement_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    statement = envelope.get("statement", {})
    return copy.deepcopy(statement) if isinstance(statement, dict) else {}


def statement_payload_sha256(envelope: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(statement_payload(envelope)))


def baseline_envelope() -> dict[str, Any]:
    metadata = _load_json(ARTIFACT_DIR / "metadata.json")
    proof = _load_json(ARTIFACT_DIR / "proof.json")
    public_signals = _load_json(ARTIFACT_DIR / "public.json")
    verification_key = _load_json(ARTIFACT_DIR / "verification_key.json")
    statement = {
        "schema": STATEMENT_SCHEMA,
        **EXPECTED_STATEMENT,
        "circuit_artifact_sha256": metadata["artifacts"]["square.circom"],
        "input_artifact_sha256": metadata["artifacts"]["input.json"],
        "verification_key_sha256": verification_key_sha256(verification_key),
        "verification_key_file_sha256": metadata["artifacts"]["verification_key.json"],
        "proof_sha256": proof_sha256(proof),
        "public_signals_sha256": public_signals_sha256(public_signals),
        "setup_commitment": metadata["artifacts"]["verification_key.json"],
    }
    return {
        "schema": ENVELOPE_SCHEMA,
        "statement": statement,
        "statement_commitment": statement_commitment(statement),
        "artifacts": {
            "circuit_path": "square.circom",
            "input_path": "input.json",
            "verification_key_path": "verification_key.json",
        },
        "snarkjs_proof": proof,
        "public_signals": public_signals,
        "verification_key": verification_key,
        "non_claims": [
            "not_a_performance_benchmark",
            "not_a_snarkjs_security_audit",
            "not_a_system_ranking",
        ],
    }


def _refresh_statement_commitment(envelope: dict[str, Any]) -> None:
    envelope["statement_commitment"] = statement_commitment(envelope["statement"])


def mutate_first_public_signal(public_signals: list[Any]) -> None:
    if not public_signals or not isinstance(public_signals[0], str) or not public_signals[0]:
        raise SnarkjsEnvelopeError("baseline snarkjs proof must contain a non-empty first public signal")
    first = public_signals[0]
    public_signals[0] = "50" if first != "50" else "49"


def mutated_envelopes() -> dict[str, tuple[str, dict[str, Any]]]:
    baseline = baseline_envelope()

    def mutate_statement(field: str, value: str, category: str) -> tuple[str, dict[str, Any]]:
        env = copy.deepcopy(baseline)
        env["statement"][field] = value
        _refresh_statement_commitment(env)
        return category, env

    out: dict[str, tuple[str, dict[str, Any]]] = {
        "model_id_relabeling": mutate_statement(
            "model_id", "urn:zkai:snarkjs-demo:different-square-v1", "statement_policy"
        ),
        "input_id_relabeling": mutate_statement(
            "input_id", "urn:zkai:input:different-scalar-v1", "statement_policy"
        ),
        "output_id_relabeling": mutate_statement(
            "output_id", "urn:zkai:output:different-output-v1", "statement_policy"
        ),
        "config_id_relabeling": mutate_statement(
            "quantization_config_id",
            "urn:zkai:snarkjs-settings:different-public-io-v1",
            "statement_policy",
        ),
        "verifier_domain_relabeling": mutate_statement(
            "verifier_domain", "snarkjs-groth16-verify-v999.0.0", "domain_or_version_allowlist"
        ),
        "circuit_artifact_hash_relabeling": mutate_statement(
            "circuit_artifact_sha256", "00" * 32, "artifact_binding"
        ),
        "input_artifact_hash_relabeling": mutate_statement(
            "input_artifact_sha256", "44" * 32, "artifact_binding"
        ),
        "verification_key_hash_relabeling": mutate_statement(
            "verification_key_sha256", "11" * 32, "artifact_binding"
        ),
        "verification_key_file_hash_relabeling": mutate_statement(
            "verification_key_file_sha256", "55" * 32, "artifact_binding"
        ),
        "proof_hash_relabeling": mutate_statement("proof_sha256", "22" * 32, "artifact_binding"),
        "proof_system_version_relabeling": mutate_statement(
            "proof_system_version", "999.0.0", "domain_or_version_allowlist"
        ),
        "setup_commitment_relabeling": mutate_statement(
            "setup_commitment", "33" * 32, "setup_binding"
        ),
    }

    commitment_env = copy.deepcopy(baseline)
    commitment_env["statement_commitment"] = f"blake2b-256:{'66' * 32}"
    out["statement_commitment_relabeling"] = ("statement_commitment", commitment_env)

    public_env = copy.deepcopy(baseline)
    mutate_first_public_signal(public_env["public_signals"])
    public_env["statement"]["public_signals_sha256"] = public_signals_sha256(
        public_env["public_signals"]
    )
    _refresh_statement_commitment(public_env)
    out["public_signal_relabeling"] = ("external_proof_verifier", public_env)
    return out


def _artifact_path(relative_path: str) -> pathlib.Path:
    path = ARTIFACT_DIR / relative_path
    resolved = path.resolve()
    if ARTIFACT_DIR.resolve() not in resolved.parents and resolved != ARTIFACT_DIR.resolve():
        raise SnarkjsEnvelopeError(f"artifact path escapes artifact directory: {relative_path}")
    if not resolved.is_file():
        raise SnarkjsEnvelopeError(f"artifact path is missing: {relative_path}")
    return resolved


def _required_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SnarkjsEnvelopeError(f"{label} must be an object")
    return value


def _required_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SnarkjsEnvelopeError(f"{label} must be a list")
    return value


def _required_artifact_reference(artifacts: dict[str, Any], key: str) -> str:
    value = artifacts.get(key)
    if not isinstance(value, str) or not value:
        raise SnarkjsEnvelopeError(f"artifacts.{key} must be a non-empty string")
    return value


def _snarkjs_payloads(
    envelope: dict[str, Any],
) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    proof = _required_dict(envelope.get("snarkjs_proof"), "snarkjs_proof")
    public_signals = _required_list(envelope.get("public_signals"), "public_signals")
    verification_key = _required_dict(envelope.get("verification_key"), "verification_key")
    return proof, public_signals, verification_key


def _check_statement_policy(statement: dict[str, Any]) -> None:
    for key, expected in EXPECTED_STATEMENT.items():
        if statement.get(key) != expected:
            raise SnarkjsEnvelopeError(f"statement policy mismatch for {key}")
    if statement.get("schema") != STATEMENT_SCHEMA:
        raise SnarkjsEnvelopeError("unsupported statement schema")


def _check_artifact_hashes(
    envelope: dict[str, Any],
    proof: dict[str, Any],
    public_signals: list[Any],
    verification_key: dict[str, Any],
) -> pathlib.Path:
    artifacts = _required_dict(envelope.get("artifacts"), "artifacts")
    circuit_path = _artifact_path(_required_artifact_reference(artifacts, "circuit_path"))
    input_path = _artifact_path(_required_artifact_reference(artifacts, "input_path"))
    vk_path = _artifact_path(_required_artifact_reference(artifacts, "verification_key_path"))
    vk_from_file = _required_dict(_load_json(vk_path), "verification_key artifact")
    inline_vk_hash = verification_key_sha256(verification_key)
    file_vk_hash = verification_key_sha256(vk_from_file)
    if file_vk_hash != inline_vk_hash:
        raise SnarkjsEnvelopeError("verification-key object does not match verification-key artifact")
    statement = envelope["statement"]
    checks = [
        (sha256_file(circuit_path), statement.get("circuit_artifact_sha256"), "circuit artifact hash"),
        (sha256_file(input_path), statement.get("input_artifact_sha256"), "input artifact hash"),
        (sha256_file(vk_path), statement.get("verification_key_file_sha256"), "verification-key file hash"),
        (inline_vk_hash, statement.get("verification_key_sha256"), "verification-key canonical hash"),
        (proof_sha256(proof), statement.get("proof_sha256"), "proof hash"),
        (
            public_signals_sha256(public_signals),
            statement.get("public_signals_sha256"),
            "public-signals hash",
        ),
    ]
    for actual, expected, label in checks:
        if actual != expected:
            raise SnarkjsEnvelopeError(f"{label} mismatch")
    if statement.get("setup_commitment") != statement.get("verification_key_file_sha256"):
        raise SnarkjsEnvelopeError("setup binding mismatch")
    return vk_path


def snarkjs_verify(
    proof: dict[str, Any],
    public_signals: list[Any],
    verification_key: dict[str, Any],
) -> None:
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = pathlib.Path(raw_tmp)
        proof_path = tmp / "proof.json"
        public_path = tmp / "public.json"
        vk_path = tmp / "verification_key.json"
        proof_path.write_text(json.dumps(proof, sort_keys=True), encoding="utf-8")
        public_path.write_text(json.dumps(public_signals, sort_keys=True), encoding="utf-8")
        vk_path.write_text(json.dumps(verification_key, sort_keys=True), encoding="utf-8")
        result = subprocess.run(
            [*SNARKJS_COMMAND, "groth16", "verify", str(vk_path), str(public_path), str(proof_path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    output = ANSI_ESCAPE_RE.sub("", output)
    if result.returncode != 0:
        raise SnarkjsEnvelopeError(f"snarkjs groth16 verifier rejected: {output}")
    if "OK" not in output:
        raise SnarkjsEnvelopeError(f"snarkjs groth16 verifier did not report OK: {output}")


def verify_statement_envelope(
    envelope: dict[str, Any],
    *,
    external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify,
) -> None:
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        raise SnarkjsEnvelopeError("unsupported envelope schema")
    statement = envelope.get("statement")
    if not isinstance(statement, dict):
        raise SnarkjsEnvelopeError("statement must be an object")
    proof, public_signals, verification_key = _snarkjs_payloads(envelope)
    if envelope.get("statement_commitment") != statement_commitment(statement):
        raise SnarkjsEnvelopeError("statement_commitment mismatch")
    _check_statement_policy(statement)
    _check_artifact_hashes(envelope, proof, public_signals, verification_key)
    external_verify(proof, public_signals, verification_key)


def verify_proof_only(
    envelope: dict[str, Any],
    external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify,
) -> None:
    proof, public_signals, verification_key = _snarkjs_payloads(envelope)
    external_verify(proof, public_signals, verification_key)


def classify_error(message: str) -> str:
    lowered = message.lower()
    if "snarkjs groth16 verifier rejected" in lowered:
        return "external_proof_verifier"
    if "must be" in lowered:
        return "parser_or_schema"
    if "artifact" in lowered or "proof hash" in lowered or "verification-key" in lowered:
        return "artifact_binding"
    if "public-signals" in lowered:
        return "public_instance_binding"
    if "setup" in lowered:
        return "setup_binding"
    if "domain" in lowered or "version" in lowered:
        return "domain_or_version_allowlist"
    if "policy mismatch" in lowered:
        return "statement_policy"
    if "commitment" in lowered:
        return "statement_commitment"
    return "adapter_policy"


def _case_result(
    adapter: str,
    envelope: dict[str, Any],
    external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None],
) -> tuple[bool, str]:
    try:
        if adapter == "snarkjs-proof-only":
            verify_proof_only(envelope, external_verify=external_verify)
        elif adapter == "snarkjs-statement-envelope":
            verify_statement_envelope(envelope, external_verify=external_verify)
        else:
            raise SnarkjsEnvelopeError(f"unsupported adapter {adapter!r}")
    except Exception as err:  # noqa: BLE001 - the benchmark records verifier failures.
        return False, str(err)
    return True, ""


def run_benchmark(
    command: list[str] | None = None,
    external_verify: Callable[[dict[str, Any], list[Any], dict[str, Any]], None] = snarkjs_verify,
) -> dict[str, Any]:
    baseline = baseline_envelope()
    mutations = mutated_envelopes()
    if set(mutations) != EXPECTED_MUTATION_SET:
        raise RuntimeError("mutation corpus does not match expected external relabeling suite")
    cases = []
    for adapter in EXPECTED_ADAPTERS:
        baseline_accepted, baseline_error = _case_result(adapter, baseline, external_verify)
        for mutation, (category, envelope) in sorted(mutations.items()):
            accepted, error = _case_result(adapter, envelope, external_verify)
            cases.append(
                {
                    "adapter": adapter,
                    "mutation": mutation,
                    "category": category,
                    "baseline_statement": statement_payload(baseline),
                    "mutated_statement": statement_payload(envelope),
                    "baseline_statement_sha256": statement_payload_sha256(baseline),
                    "mutated_statement_sha256": statement_payload_sha256(envelope),
                    "baseline_statement_commitment": baseline.get("statement_commitment", ""),
                    "mutated_statement_commitment": envelope.get("statement_commitment", ""),
                    "baseline_public_signals_sha256": public_signals_sha256(baseline["public_signals"]),
                    "mutated_public_signals_sha256": public_signals_sha256(envelope["public_signals"]),
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
    metadata = _load_json(ARTIFACT_DIR / "metadata.json")
    return {
        "schema": BENCHMARK_SCHEMA,
        "suite_kind": "external_snarkjs_statement_relabeling",
        "external_system": {
            "name": "snarkjs",
            "version": SNARKJS_VERSION,
            "verification_api": "snarkjs groth16 verify verification_key.json public.json proof.json",
            "proof_system": EXPECTED_STATEMENT["proof_system"],
        },
        "non_claims": [
            "not_a_performance_benchmark",
            "not_a_snarkjs_security_audit",
            "not_a_system_ranking",
            "proof_only_no_go_is_limited_to_metadata_outside_the_snarkjs_acceptance_path",
        ],
        "repro": {
            "git_commit": os.environ.get("ZKAI_SNARKJS_BENCHMARK_GIT_COMMIT", _git_commit()),
            "command": _canonical_command(command),
            "artifact_dir": str(ARTIFACT_DIR.relative_to(ROOT)),
            "artifact_metadata_sha256": sha256_file(ARTIFACT_DIR / "metadata.json"),
        },
        "artifact_metadata": metadata,
        "cases": cases,
        "summary": summary,
    }


def _git_commit() -> str:
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
    override_json = os.environ.get("ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON")
    if override_json:
        try:
            parsed = json.loads(override_json)
        except json.JSONDecodeError as err:
            raise RuntimeError(
                "ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON must be a valid JSON array of strings"
            ) from err
        if not isinstance(parsed, list) or not all(isinstance(part, str) for part in parsed):
            raise RuntimeError("ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON must be a JSON array of strings")
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
    proof_only = summary["snarkjs-proof-only"]
    statement_envelope = summary["snarkjs-statement-envelope"]
    proof_cases = {
        case["mutation"]: case
        for case in payload["cases"]
        if case["adapter"] == "snarkjs-proof-only"
    }
    return (
        proof_only["baseline_accepted"]
        and statement_envelope["baseline_accepted"]
        and proof_only["mutations_rejected"] == 1
        and bool(proof_cases["public_signal_relabeling"].get("rejected"))
        and statement_envelope["all_mutations_rejected"]
    )


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
    parser.add_argument("--json", action="store_true", help="print JSON result")
    parser.add_argument("--tsv", action="store_true", help="print TSV result")
    parser.add_argument("--write-json", type=pathlib.Path, help="write JSON result to this path")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write TSV result to this path")
    args = parser.parse_args(argv)

    payload = run_benchmark(command=[os.environ.get("PYTHON", "python3"), *sys.argv])
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
            f"proof-only rejected {summary['snarkjs-proof-only']['mutations_rejected']}/"
            f"{summary['snarkjs-proof-only']['mutation_count']} mutations; "
            f"statement-envelope rejected {summary['snarkjs-statement-envelope']['mutations_rejected']}/"
            f"{summary['snarkjs-statement-envelope']['mutation_count']} mutations"
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
