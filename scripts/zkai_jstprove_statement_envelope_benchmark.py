#!/usr/bin/env python3
"""External JSTprove/Remainder relabeling benchmark for statement-bound zkAI artifacts."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import base64
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "docs" / "engineering" / "evidence" / "zkai-jstprove-statement-envelope-2026-05"
BENCHMARK_SCHEMA = "zkai-jstprove-statement-envelope-benchmark-v1"
ENVELOPE_SCHEMA = "zkai-jstprove-statement-envelope-v1"
STATEMENT_SCHEMA = "zkai-external-statement-v1"
JSTPROVE_UPSTREAM_COMMIT = "7c3cbbee83aaa01adde700673f00e317a4e902f9"
JSTPROVE_REMAINDER_COMMIT = "06a5f406"
JSTPROVE_PROOF_SYSTEM_VERSION = f"jstprove-{JSTPROVE_UPSTREAM_COMMIT[:8]}"
JSTPROVE_VERIFIER_DOMAIN = f"jstprove-remainder-verify-commit-{JSTPROVE_UPSTREAM_COMMIT[:8]}"
JSTPROVE_BIN_ENV = "ZKAI_JSTPROVE_REMAINDER_BIN"
GIT_COMMIT_OVERRIDE_ENV = "ZKAI_JSTPROVE_BENCHMARK_GIT_COMMIT"
COMMAND_OVERRIDE_ENV = "ZKAI_JSTPROVE_BENCHMARK_COMMAND_JSON"
HEX_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
ALLOWED_ARTIFACTS = frozenset({"model.msgpack", "input.msgpack", "proof.msgpack"})
MODEL_SOURCE_ARTIFACT = "tiny_gemm.onnx"
EXPECTED_STATEMENT = {
    "model_id": "urn:zkai:jstprove-demo:tiny-gemm-remainder-v1",
    "input_id": "urn:zkai:input:tiny-gemm-vector-v1",
    "output_id": "urn:zkai:output:tiny-gemm-proof-embedded-output-v1",
    "quantization_config_id": "urn:zkai:jstprove-remainder:auto-quantization-v1",
    "proof_system": "JSTprove/Remainder-GKR-sumcheck",
    "proof_system_version": JSTPROVE_PROOF_SYSTEM_VERSION,
    "verifier_domain": JSTPROVE_VERIFIER_DOMAIN,
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
EXPECTED_ADAPTERS = ("jstprove-proof-only", "jstprove-statement-envelope")
EXPECTED_MUTATION_NAMES = (
    "config_id_relabeling",
    "input_artifact_bytes_relabeling",
    "input_artifact_hash_relabeling",
    "input_id_relabeling",
    "model_artifact_hash_relabeling",
    "model_id_relabeling",
    "output_id_relabeling",
    "proof_hash_relabeling",
    "proof_system_version_relabeling",
    "setup_commitment_relabeling",
    "statement_commitment_relabeling",
    "upstream_commit_relabeling",
    "verifier_domain_relabeling",
)
EXPECTED_MUTATION_SET = frozenset(EXPECTED_MUTATION_NAMES)
EXPECTED_CASE_PAIRS = frozenset(
    (adapter, mutation) for adapter in EXPECTED_ADAPTERS for mutation in EXPECTED_MUTATION_NAMES
)


class JstproveEnvelopeError(ValueError):
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


def _artifact_path(name: str) -> pathlib.Path:
    if name not in ALLOWED_ARTIFACTS:
        raise JstproveEnvelopeError(f"unsupported JSTprove artifact reference: {name}")
    path = (ARTIFACT_DIR / name).resolve()
    artifact_root = ARTIFACT_DIR.resolve()
    if artifact_root not in path.parents and path != artifact_root:
        raise JstproveEnvelopeError(f"artifact path escapes evidence directory: {name}")
    if not path.is_file():
        raise JstproveEnvelopeError(f"artifact path is missing: {name}")
    return path


def _artifact_bytes(envelope: dict[str, Any], name: str) -> bytes:
    if name not in ALLOWED_ARTIFACTS:
        raise JstproveEnvelopeError(f"unsupported JSTprove artifact reference: {name}")
    overrides = envelope.get("artifact_overrides", {})
    if overrides:
        if not isinstance(overrides, dict):
            raise JstproveEnvelopeError("artifact_overrides must be an object")
        encoded = overrides.get(name)
        if encoded is not None:
            if not isinstance(encoded, str):
                raise JstproveEnvelopeError(f"artifact override for {name} must be base64 text")
            try:
                return base64.b64decode(encoded.encode("ascii"), validate=True)
            except (ValueError, UnicodeEncodeError) as err:
                raise JstproveEnvelopeError(f"artifact override for {name} is not valid base64") from err
    return _artifact_path(name).read_bytes()


def artifact_sha256(envelope: dict[str, Any], name: str) -> str:
    return sha256_bytes(_artifact_bytes(envelope, name))


def statement_commitment(statement: dict[str, Any]) -> str:
    return blake2b_commitment(statement, "ptvm:zkai:jstprove-statement:v1")


def statement_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    statement = envelope.get("statement", {})
    return copy.deepcopy(statement) if isinstance(statement, dict) else {}


def statement_payload_sha256(envelope: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(statement_payload(envelope)))


def _artifact_metadata() -> dict[str, Any]:
    metadata = _load_json(ARTIFACT_DIR / "metadata.json")
    if not isinstance(metadata, dict):
        raise JstproveEnvelopeError("metadata.json must be an object")
    return metadata


def baseline_envelope() -> dict[str, Any]:
    metadata = _artifact_metadata()
    statement = {
        "schema": STATEMENT_SCHEMA,
        **EXPECTED_STATEMENT,
        "model_artifact_sha256": metadata["artifacts"]["model.msgpack"],
        "input_artifact_sha256": metadata["artifacts"]["input.msgpack"],
        "proof_sha256": metadata["artifacts"]["proof.msgpack"],
        "model_source_sha256": metadata["source_artifacts"][MODEL_SOURCE_ARTIFACT],
        "upstream_commit": JSTPROVE_UPSTREAM_COMMIT,
        "remainder_commit": JSTPROVE_REMAINDER_COMMIT,
        "setup_commitment": None,
    }
    return {
        "schema": ENVELOPE_SCHEMA,
        "statement": statement,
        "statement_commitment": statement_commitment(statement),
        "artifacts": {
            "model_path": "model.msgpack",
            "input_path": "input.msgpack",
            "proof_path": "proof.msgpack",
        },
        "artifact_overrides": {},
        "non_claims": [
            "not_a_performance_benchmark",
            "not_a_jstprove_security_audit",
            "not_a_system_ranking",
            "tiny_gemm_fixture_not_transformer_proof",
        ],
    }


def _refresh_statement_commitment(envelope: dict[str, Any]) -> None:
    envelope["statement_commitment"] = statement_commitment(envelope["statement"])


def _encode_tiny_input_msgpack(values: list[float]) -> bytes:
    if len(values) > 15:
        raise JstproveEnvelopeError("tiny input encoder only supports fixarray lengths")
    out = bytearray([0x81, 0xA5])
    out.extend(b"input")
    out.append(0x90 + len(values))
    for value in values:
        out.append(0xCB)
        out.extend(struct.pack(">d", value))
    return bytes(out)


def _mutated_input_bytes() -> bytes:
    # Use a semantic mutation, not a low-bit float perturbation that quantization can round away.
    return _encode_tiny_input_msgpack([2.0, 2.0])


def mutated_envelopes() -> dict[str, tuple[str, dict[str, Any]]]:
    baseline = baseline_envelope()

    def mutate_statement(field: str, value: Any, category: str) -> tuple[str, dict[str, Any]]:
        env = copy.deepcopy(baseline)
        env["statement"][field] = value
        _refresh_statement_commitment(env)
        return category, env

    out: dict[str, tuple[str, dict[str, Any]]] = {
        "model_id_relabeling": mutate_statement(
            "model_id", "urn:zkai:jstprove-demo:different-tiny-gemm-v1", "statement_policy"
        ),
        "input_id_relabeling": mutate_statement(
            "input_id", "urn:zkai:input:different-tiny-gemm-vector-v1", "statement_policy"
        ),
        "output_id_relabeling": mutate_statement(
            "output_id", "urn:zkai:output:different-tiny-gemm-output-v1", "statement_policy"
        ),
        "config_id_relabeling": mutate_statement(
            "quantization_config_id",
            "urn:zkai:jstprove-remainder:different-quantization-v1",
            "statement_policy",
        ),
        "verifier_domain_relabeling": mutate_statement(
            "verifier_domain", "jstprove-remainder-verify-commit-deadbeef", "domain_or_version_allowlist"
        ),
        "proof_system_version_relabeling": mutate_statement(
            "proof_system_version", "jstprove-deadbeef", "domain_or_version_allowlist"
        ),
        "model_artifact_hash_relabeling": mutate_statement(
            "model_artifact_sha256", "00" * 32, "artifact_binding"
        ),
        "input_artifact_hash_relabeling": mutate_statement(
            "input_artifact_sha256", "11" * 32, "artifact_binding"
        ),
        "proof_hash_relabeling": mutate_statement("proof_sha256", "22" * 32, "artifact_binding"),
        "upstream_commit_relabeling": mutate_statement(
            "upstream_commit", "deadbeef", "domain_or_version_allowlist"
        ),
        "setup_commitment_relabeling": mutate_statement(
            "setup_commitment", "33" * 32, "setup_binding"
        ),
    }

    commitment_env = copy.deepcopy(baseline)
    commitment_env["statement_commitment"] = f"blake2b-256:{'44' * 32}"
    out["statement_commitment_relabeling"] = ("statement_commitment", commitment_env)

    input_env = copy.deepcopy(baseline)
    mutated_input = _mutated_input_bytes()
    input_env["artifact_overrides"] = {
        "input.msgpack": base64.b64encode(mutated_input).decode("ascii")
    }
    input_env["statement"]["input_artifact_sha256"] = sha256_bytes(mutated_input)
    _refresh_statement_commitment(input_env)
    out["input_artifact_bytes_relabeling"] = ("external_proof_verifier", input_env)

    return out


def _required_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise JstproveEnvelopeError(f"{label} must be an object")
    return value


def _required_artifact_reference(artifacts: dict[str, Any], key: str) -> str:
    value = artifacts.get(key)
    if not isinstance(value, str) or not value:
        raise JstproveEnvelopeError(f"artifacts.{key} must be a non-empty string")
    if value not in ALLOWED_ARTIFACTS:
        raise JstproveEnvelopeError(f"artifacts.{key} is not an allowed JSTprove artifact")
    return value


def _check_statement_policy(statement: dict[str, Any]) -> None:
    if statement.get("schema") != STATEMENT_SCHEMA:
        raise JstproveEnvelopeError("unsupported statement schema")
    for key, expected in EXPECTED_STATEMENT.items():
        if statement.get(key) != expected:
            raise JstproveEnvelopeError(f"statement policy mismatch for {key}")
    if statement.get("upstream_commit") != JSTPROVE_UPSTREAM_COMMIT:
        raise JstproveEnvelopeError("upstream commit mismatch")
    if statement.get("remainder_commit") != JSTPROVE_REMAINDER_COMMIT:
        raise JstproveEnvelopeError("Remainder dependency commit mismatch")
    if "setup_commitment" not in statement:
        raise JstproveEnvelopeError("setup commitment must be explicitly null")
    if statement["setup_commitment"] is not None:
        raise JstproveEnvelopeError("setup commitment must be null for JSTprove verifier-facing adapter")


def _check_artifact_hashes(envelope: dict[str, Any]) -> tuple[str, str, str]:
    artifacts = _required_dict(envelope.get("artifacts"), "artifacts")
    model_name = _required_artifact_reference(artifacts, "model_path")
    input_name = _required_artifact_reference(artifacts, "input_path")
    proof_name = _required_artifact_reference(artifacts, "proof_path")
    statement = envelope["statement"]
    checks = [
        (artifact_sha256(envelope, model_name), statement.get("model_artifact_sha256"), "model artifact hash"),
        (artifact_sha256(envelope, input_name), statement.get("input_artifact_sha256"), "input artifact hash"),
        (artifact_sha256(envelope, proof_name), statement.get("proof_sha256"), "proof hash"),
        (
            sha256_file(ARTIFACT_DIR / MODEL_SOURCE_ARTIFACT),
            statement.get("model_source_sha256"),
            "model source hash",
        ),
    ]
    for actual, expected, label in checks:
        if actual != expected:
            raise JstproveEnvelopeError(f"{label} mismatch")
    return model_name, input_name, proof_name


def _materialized_artifacts(envelope: dict[str, Any], tmp: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    artifacts = _required_dict(envelope.get("artifacts"), "artifacts")
    model_name = _required_artifact_reference(artifacts, "model_path")
    input_name = _required_artifact_reference(artifacts, "input_path")
    proof_name = _required_artifact_reference(artifacts, "proof_path")
    paths = []
    for name in (model_name, input_name, proof_name):
        out = tmp / name
        out.write_bytes(_artifact_bytes(envelope, name))
        paths.append(out)
    return paths[0], paths[1], paths[2]


def jstprove_verify(envelope: dict[str, Any]) -> None:
    binary = os.environ.get(JSTPROVE_BIN_ENV, "jstprove-remainder")
    binary_path = pathlib.Path(binary)
    if binary_path.is_absolute():
        if not binary_path.is_file():
            raise JstproveEnvelopeError(f"JSTprove Remainder verifier is missing: {binary}")
        if not os.access(binary_path, os.X_OK):
            raise JstproveEnvelopeError(f"JSTprove Remainder verifier is not executable: {binary}")
    if not binary_path.is_absolute() and shutil.which(binary) is None:
        raise JstproveEnvelopeError(f"JSTprove Remainder verifier is not on PATH: {binary}")
    with tempfile.TemporaryDirectory(prefix="zkai-jstprove-proof-") as raw_tmp:
        model_path, input_path, proof_path = _materialized_artifacts(envelope, pathlib.Path(raw_tmp))
        try:
            result = subprocess.run(
                [
                    binary,
                    "--quiet",
                    "verify",
                    "--model",
                    str(model_path),
                    "--proof",
                    str(proof_path),
                    "--input",
                    str(input_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
        except subprocess.TimeoutExpired as err:
            raise JstproveEnvelopeError("JSTprove Remainder verifier timed out") from err
        except OSError as err:
            raise JstproveEnvelopeError(f"JSTprove Remainder verifier failed to start: {err}") from err
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if result.returncode != 0:
        raise JstproveEnvelopeError(f"JSTprove Remainder verifier rejected: {output}")


def verify_statement_envelope(
    envelope: dict[str, Any],
    *,
    external_verify: Callable[[dict[str, Any]], None] = jstprove_verify,
) -> None:
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        raise JstproveEnvelopeError("unsupported envelope schema")
    statement = envelope.get("statement")
    if not isinstance(statement, dict):
        raise JstproveEnvelopeError("statement must be an object")
    if envelope.get("statement_commitment") != statement_commitment(statement):
        raise JstproveEnvelopeError("statement_commitment mismatch")
    _check_statement_policy(statement)
    _check_artifact_hashes(envelope)
    external_verify(envelope)


def verify_proof_only(
    envelope: dict[str, Any],
    external_verify: Callable[[dict[str, Any]], None] = jstprove_verify,
) -> None:
    external_verify(envelope)


def classify_error(message: str) -> str:
    lowered = message.lower()
    if "jstprove remainder verifier rejected" in lowered or "timed out" in lowered:
        return "external_proof_verifier"
    if "artifact" in lowered or "proof hash" in lowered or "source hash" in lowered:
        return "artifact_binding"
    if "setup" in lowered:
        return "setup_binding"
    if "must be" in lowered:
        return "parser_or_schema"
    if "domain" in lowered or "version" in lowered or "commit" in lowered:
        return "domain_or_version_allowlist"
    if "policy mismatch" in lowered:
        return "statement_policy"
    if "commitment" in lowered:
        return "statement_commitment"
    return "adapter_policy"


def _case_result(
    adapter: str,
    envelope: dict[str, Any],
    external_verify: Callable[[dict[str, Any]], None],
) -> tuple[bool, str]:
    try:
        if adapter == "jstprove-proof-only":
            verify_proof_only(envelope, external_verify=external_verify)
        elif adapter == "jstprove-statement-envelope":
            verify_statement_envelope(envelope, external_verify=external_verify)
        else:
            raise JstproveEnvelopeError(f"unsupported adapter {adapter!r}")
    except JstproveEnvelopeError as err:
        return False, str(err)
    return True, ""


def run_benchmark(
    command: list[str] | None = None,
    external_verify: Callable[[dict[str, Any]], None] = jstprove_verify,
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
                    "baseline_artifact_hashes": {
                        name: artifact_sha256(baseline, name) for name in sorted(ALLOWED_ARTIFACTS)
                    },
                    "mutated_artifact_hashes": {
                        name: artifact_sha256(envelope, name) for name in sorted(ALLOWED_ARTIFACTS)
                    },
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
    metadata = _artifact_metadata()
    return {
        "schema": BENCHMARK_SCHEMA,
        "suite_kind": "external_jstprove_statement_relabeling",
        "external_system": {
            "name": "JSTprove",
            "upstream_commit": JSTPROVE_UPSTREAM_COMMIT,
            "remainder_commit": JSTPROVE_REMAINDER_COMMIT,
            "verification_api": "jstprove-remainder verify --model model.msgpack --proof proof.msgpack --input input.msgpack",
            "proof_system": EXPECTED_STATEMENT["proof_system"],
        },
        "non_claims": [
            "not_a_performance_benchmark",
            "not_a_jstprove_security_audit",
            "not_a_system_ranking",
            "proof_only_no_go_is_limited_to_metadata_outside_the_jstprove_acceptance_path",
            "tiny_gemm_fixture_not_transformer_proof",
        ],
        "repro": {
            "git_commit": os.environ.get(GIT_COMMIT_OVERRIDE_ENV, _git_commit()),
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
    override_json = os.environ.get(COMMAND_OVERRIDE_ENV)
    if override_json:
        try:
            parsed = json.loads(override_json)
        except json.JSONDecodeError as err:
            raise RuntimeError(f"{COMMAND_OVERRIDE_ENV} must be a valid JSON array of strings") from err
        if not isinstance(parsed, list) or not all(isinstance(part, str) for part in parsed):
            raise RuntimeError(f"{COMMAND_OVERRIDE_ENV} must be a JSON array of strings")
        return parsed
    return command or []


def _validated_git_commit(value: str) -> str:
    if value == "unknown" or HEX_SHA_RE.fullmatch(value):
        return value
    raise RuntimeError(f"{GIT_COMMIT_OVERRIDE_ENV} must be 'unknown' or a 7-40 character hex SHA")


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
    proof_only = summary["jstprove-proof-only"]
    statement_envelope = summary["jstprove-statement-envelope"]
    proof_cases = {
        case["mutation"]: case
        for case in payload["cases"]
        if case["adapter"] == "jstprove-proof-only"
    }
    return (
        proof_only["baseline_accepted"]
        and statement_envelope["baseline_accepted"]
        and proof_only["mutations_rejected"] == 1
        and bool(proof_cases["input_artifact_bytes_relabeling"].get("rejected"))
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
    repro = payload.get("repro")
    if isinstance(repro, dict) and "git_commit" in repro:
        repro["git_commit"] = _validated_git_commit(str(repro["git_commit"]))
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
            f"proof-only rejected {summary['jstprove-proof-only']['mutations_rejected']}/"
            f"{summary['jstprove-proof-only']['mutation_count']} mutations; "
            f"statement-envelope rejected {summary['jstprove-statement-envelope']['mutations_rejected']}/"
            f"{summary['jstprove-statement-envelope']['mutation_count']} mutations"
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
