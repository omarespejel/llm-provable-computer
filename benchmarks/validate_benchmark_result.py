#!/usr/bin/env python3
"""Validate benchmark evidence JSON and its sidecar hashes.

This is intentionally dependency-free. The JSON Schema in `spec/` documents the
expected shape; this validator enforces the reproducibility-critical bindings
that plain schema validation cannot check, such as command hashes and log file
digests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SUPPORTED_SCHEMA_VERSION = 1
SCHEMA_PATH = Path("spec/benchmark-result.schema.json")
HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
CHUNK_SIZE = 1024 * 1024


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_canonical_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_64_RE.fullmatch(value))


def validator_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_evidence_path(
    raw_path: str,
    bundle_root: Path,
    repo_root: Path | None = None,
) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    candidates = [bundle_root / path]
    if repo_root is not None:
        candidates.append(repo_root / path)
    candidates.extend(
        [
            validator_repo_root() / path,
            Path.cwd() / path,
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return bundle_root / path


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def validate_file_record(
    record: Any,
    field: str,
    mode: str,
    errors: list[str],
    bundle_root: Path,
    repo_root: Path | None,
) -> None:
    if not isinstance(record, dict):
        errors.append(f"{field} must be an object")
        return
    require(isinstance(record.get("path"), str) and record["path"], errors, f"{field}.path must be a non-empty string")
    require(isinstance(record.get("optional"), bool), errors, f"{field}.optional must be boolean")
    if mode == "dry-run":
        require(record.get("exists") is None, errors, f"{field}.exists must be null in dry-run")
        require(record.get("sha256") is None, errors, f"{field}.sha256 must be null in dry-run")
        require(record.get("hashing") == "deferred-until-run", errors, f"{field}.hashing must be deferred in dry-run")
        return
    exists = record.get("exists")
    require(isinstance(exists, bool), errors, f"{field}.exists must be boolean in run mode")
    if exists:
        path = resolve_evidence_path(record["path"], bundle_root, repo_root)
        require(path.exists(), errors, f"{field}.path does not exist: {path}")
        require(is_hex64(record.get("sha256")), errors, f"{field}.sha256 must be lowercase 64-char hex")
        if path.exists() and is_hex64(record.get("sha256")):
            require(sha256_file(path) == record["sha256"], errors, f"{field}.sha256 does not match file bytes: {path}")
        require(isinstance(record.get("size_bytes"), int) and record["size_bytes"] >= 0, errors, f"{field}.size_bytes must be non-negative integer")
        if path.exists() and isinstance(record.get("size_bytes"), int):
            require(path.stat().st_size == record["size_bytes"], errors, f"{field}.size_bytes does not match file: {path}")
    else:
        require(record.get("optional") is True, errors, f"{field} can be missing only when optional")
        require(record.get("sha256") is None, errors, f"{field}.sha256 must be null when missing")


def validate_run_record(
    record: Any,
    field: str,
    errors: list[str],
    bundle_root: Path,
) -> None:
    if not isinstance(record, dict):
        errors.append(f"{field} must be an object")
        return
    for key in ("index", "returncode", "stdout_size_bytes", "stderr_size_bytes"):
        require(isinstance(record.get(key), int), errors, f"{field}.{key} must be integer")
    require(isinstance(record.get("timed_out"), bool), errors, f"{field}.timed_out must be boolean")
    for key in ("stdout_sha256", "stderr_sha256", "log_sha256"):
        require(is_hex64(record.get(key)), errors, f"{field}.{key} must be lowercase 64-char hex")
    for key in ("stdout_path", "stderr_path"):
        require(isinstance(record.get(key), str) and record[key], errors, f"{field}.{key} must be a non-empty string")
        path = resolve_evidence_path(record.get(key, ""), bundle_root)
        require(path.exists(), errors, f"{field}.{key} does not exist: {path}")
    stdout_path = resolve_evidence_path(record.get("stdout_path", ""), bundle_root)
    stderr_path = resolve_evidence_path(record.get("stderr_path", ""), bundle_root)
    if stdout_path.exists() and is_hex64(record.get("stdout_sha256")):
        require(sha256_file(stdout_path) == record["stdout_sha256"], errors, f"{field}.stdout_sha256 does not match log bytes")
    if stderr_path.exists() and is_hex64(record.get("stderr_sha256")):
        require(sha256_file(stderr_path) == record["stderr_sha256"], errors, f"{field}.stderr_sha256 does not match log bytes")
    binding = {
        "index": record.get("index"),
        "returncode": record.get("returncode"),
        "timed_out": record.get("timed_out"),
        "stdout_sha256": record.get("stdout_sha256"),
        "stdout_size_bytes": record.get("stdout_size_bytes"),
        "stderr_sha256": record.get("stderr_sha256"),
        "stderr_size_bytes": record.get("stderr_size_bytes"),
    }
    if is_hex64(record.get("log_sha256")):
        require(record["log_sha256"] == sha256_canonical_json(binding), errors, f"{field}.log_sha256 does not bind stdout/stderr hashes")


def validate_case(
    case: Any,
    index: int,
    mode: str,
    errors: list[str],
    bundle_root: Path,
    repo_root: Path | None,
) -> None:
    field = f"cases[{index}]"
    if not isinstance(case, dict):
        errors.append(f"{field} must be an object")
        return
    require(isinstance(case.get("name"), str) and case["name"], errors, f"{field}.name must be a non-empty string")
    require(isinstance(case.get("command"), list) and all(isinstance(x, str) for x in case.get("command", [])), errors, f"{field}.command must be a string list")
    binding = case.get("command_binding")
    require(isinstance(binding, dict), errors, f"{field}.command_binding must be an object")
    if isinstance(binding, dict):
        require(binding.get("command") == case.get("command"), errors, f"{field}.command_binding.command must match command")
        if is_hex64(case.get("command_sha256")):
            require(case["command_sha256"] == sha256_canonical_json(binding), errors, f"{field}.command_sha256 does not match command_binding")
    require(is_hex64(case.get("command_sha256")), errors, f"{field}.command_sha256 must be lowercase 64-char hex")
    require(case.get("status") in {"dry-run", "passed", "failed"}, errors, f"{field}.status has unsupported value")
    for list_key in ("inputs", "outputs"):
        require(isinstance(case.get(list_key), list), errors, f"{field}.{list_key} must be a list")
        for item_index, item in enumerate(case.get(list_key, [])):
            validate_file_record(
                item,
                f"{field}.{list_key}[{item_index}]",
                mode,
                errors,
                bundle_root,
                repo_root,
            )
    require(isinstance(case.get("runs"), list), errors, f"{field}.runs must be a list")
    if mode == "dry-run":
        require(case.get("status") == "dry-run", errors, f"{field}.status must be dry-run in dry-run mode")
        require(case.get("runs") == [], errors, f"{field}.runs must be empty in dry-run mode")
        return
    for run_index, run in enumerate(case.get("runs", [])):
        validate_run_record(run, f"{field}.runs[{run_index}]", errors, bundle_root)
    summary = case.get("summary")
    require(isinstance(summary, dict), errors, f"{field}.summary must be present in run mode")
    if isinstance(summary, dict):
        for key in ("runs", "min_ms", "mean_ms", "p50_ms", "p95_ms", "max_ms"):
            require(key in summary, errors, f"{field}.summary missing {key}")


def validate_result(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"failed to parse JSON: {exc}"]
    if not isinstance(payload, dict):
        return ["benchmark result must be a JSON object"]
    bundle_root = path.resolve().parent
    repo_root = None
    repo_root_raw = payload.get("repo_root")
    if isinstance(repo_root_raw, str) and repo_root_raw:
        repo_root = Path(repo_root_raw)

    require(payload.get("schema_version") == SUPPORTED_SCHEMA_VERSION, errors, "schema_version must be 1")
    mode = payload.get("mode")
    require(mode in {"dry-run", "run"}, errors, "mode must be dry-run or run")
    schema = payload.get("result_schema")
    require(isinstance(schema, dict), errors, "result_schema must be an object")
    if isinstance(schema, dict):
        require(schema.get("path", "").endswith(str(SCHEMA_PATH)), errors, "result_schema.path must point to spec/benchmark-result.schema.json")
        require(is_hex64(schema.get("sha256")), errors, "result_schema.sha256 must be lowercase 64-char hex")
        schema_path = resolve_evidence_path(
            schema.get("path", ""),
            bundle_root,
            repo_root or validator_repo_root(),
        )
        require(schema_path.exists(), errors, f"result_schema.path does not exist: {schema_path}")
        if schema_path.exists() and is_hex64(schema.get("sha256")):
            require(sha256_file(schema_path) == schema["sha256"], errors, "result_schema.sha256 does not match schema file")
    for key in ("case_manifest", "harness", "git", "toolchain", "host"):
        require(isinstance(payload.get(key), dict), errors, f"{key} must be an object")
    require(isinstance(payload.get("cases"), list) and payload["cases"], errors, "cases must be a non-empty list")
    if isinstance(payload.get("cases"), list) and mode in {"dry-run", "run"}:
        for index, case in enumerate(payload["cases"]):
            validate_case(case, index, mode, errors, bundle_root, repo_root)
    return errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", help="Benchmark JSON result produced by benchmarks/run_benchmarks.py")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    errors = validate_result(Path(args.result))
    if errors:
        for error in errors:
            print(f"benchmark-result invalid: {error}", file=sys.stderr)
        return 1
    print(f"benchmark-result valid: {args.result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
