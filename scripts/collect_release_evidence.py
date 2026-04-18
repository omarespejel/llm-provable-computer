#!/usr/bin/env python3
"""Collect and validate local release evidence bundles.

The bundle is intentionally local-first. It records the exact git checkout,
toolchain metadata, selected artifact hashes, benchmark result hashes, merge-gate
evidence hashes, and the command-log hashes referenced by merge-gate evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


SCHEMA_VERSION = 1
RELEASE_EVIDENCE_SCHEMA = "spec/release-evidence.schema.json"
CHUNK_SIZE = 1024 * 1024
HEX_40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ReleaseEvidenceError(RuntimeError):
    pass


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_canonical_json(payload: Any) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_hex40(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_40_RE.fullmatch(value))


def is_hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_64_RE.fullmatch(value))


def run_capture(args: list[str], cwd: Path) -> str | None:
    try:
        return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def normalize_repo_prefix(value: str, repo_root: Path) -> str:
    path = Path(value)
    resolved = path if path.is_absolute() else repo_root / path
    try:
        rel = str(resolved.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return ""
    return rel.rstrip("/") + "/"


def status_entry_path(line: str) -> str:
    path = line[3:] if len(line) > 3 else ""
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    return path.strip()


def filter_status_porcelain(status: str, ignored_prefixes: list[str]) -> str:
    if not ignored_prefixes:
        return status
    kept = []
    for line in status.splitlines():
        path = status_entry_path(line)
        if path and any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in ignored_prefixes):
            continue
        kept.append(line)
    return "\n".join(kept) + ("\n" if kept else "")


def sanitize_remote_url(value: str | None) -> tuple[str | None, bool]:
    if not value:
        return None, False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None, True
    if parsed.scheme and parsed.netloc:
        had_credentials = bool(parsed.username or parsed.password)
        host = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        sanitized = urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))
        return sanitized, had_credentials
    return value, False


def path_for_json(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(repo_root.resolve()))
    except ValueError:
        return str(resolved)


def resolve_path(raw_path: str, bundle_root: Path, repo_root: Path | None) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    candidates = [bundle_root / path]
    if repo_root is not None:
        candidates.append(repo_root / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def require_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise ReleaseEvidenceError(f"{label} does not exist: {path}")
    if not path.is_file():
        raise ReleaseEvidenceError(f"{label} is not a regular file: {path}")
    return path


def file_record(path: Path, repo_root: Path, *, role: str, label: str | None = None) -> dict[str, Any]:
    resolved = require_file(path if path.is_absolute() else repo_root / path, role).resolve()
    record: dict[str, Any] = {
        "role": role,
        "path": path_for_json(resolved, repo_root),
        "size_bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }
    if label:
        record["label"] = label
    return record


def git_metadata(
    repo_root: Path,
    *,
    require_clean: bool,
    clean_ignore_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    head = run_capture(["git", "rev-parse", "HEAD"], repo_root)
    branch = run_capture(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    remote_raw = run_capture(["git", "config", "--get", "remote.origin.url"], repo_root)
    remote, remote_had_credentials = sanitize_remote_url(remote_raw)
    if not is_hex40(head):
        raise ReleaseEvidenceError("git rev-parse HEAD did not return a lowercase 40-char SHA")
    ignored_prefixes = [
        prefix
        for prefix in (
            normalize_repo_prefix(value, repo_root) for value in (clean_ignore_prefixes or [])
        )
        if prefix
    ]
    raw_status = run_capture(["git", "status", "--porcelain"], repo_root) or ""
    status = filter_status_porcelain(raw_status, ignored_prefixes)
    dirty = bool(status.strip())
    if require_clean and dirty:
        raise ReleaseEvidenceError("worktree is dirty; release evidence must bind a clean checkout")
    return {
        "head_sha": head,
        "branch": branch,
        "remote_origin": remote,
        "remote_origin_had_credentials": remote_had_credentials,
        "dirty": dirty,
        "status_sha256": sha256_bytes(status.encode("utf-8")),
        "clean_ignored_prefixes": ignored_prefixes,
    }


def toolchain_metadata(repo_root: Path) -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "rustc": run_capture(["rustc", "--version"], repo_root),
        "cargo": run_capture(["cargo", "--version"], repo_root),
        "rustup_active_toolchain": run_capture(["rustup", "show", "active-toolchain"], repo_root),
    }


def host_metadata() -> dict[str, Any]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "processor": platform.processor(),
    }


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact parser error varies
        raise ReleaseEvidenceError(f"failed to parse {label} as JSON: {exc}") from exc


def merge_gate_command_logs(
    evidence: dict[str, Any],
    repo_root: Path,
    evidence_path: Path,
) -> list[dict[str, Any]]:
    commands = evidence.get("local_commands")
    if not isinstance(commands, list):
        raise ReleaseEvidenceError(f"{evidence_path}: local_commands must be a list")
    records: list[dict[str, Any]] = []
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            raise ReleaseEvidenceError(f"{evidence_path}: local_commands[{index}] must be an object")
        log_file = command.get("log_file")
        recorded_hash = command.get("log_sha256")
        if not isinstance(log_file, str) or not log_file:
            raise ReleaseEvidenceError(f"{evidence_path}: local_commands[{index}].log_file is missing")
        if not is_hex64(recorded_hash):
            raise ReleaseEvidenceError(f"{evidence_path}: local_commands[{index}].log_sha256 is not lowercase hex")
        resolved = Path(log_file)
        if not resolved.is_absolute():
            resolved = repo_root / resolved
        resolved = require_file(resolved, f"merge-gate command log {index}").resolve()
        actual_hash = sha256_file(resolved)
        if actual_hash != recorded_hash:
            raise ReleaseEvidenceError(
                f"{evidence_path}: local_commands[{index}] log hash mismatch for {resolved}"
            )
        records.append(
            {
                "name": command.get("name"),
                "command": command.get("command"),
                "exit_code": command.get("exit_code"),
                "path": path_for_json(resolved, repo_root),
                "sha256": actual_hash,
                "recorded_sha256": recorded_hash,
                "matches_recorded": True,
            }
        )
    return records


def collect_merge_gate_evidence(path: Path, repo_root: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_root / path
    record = file_record(resolved, repo_root, role="merge_gate_evidence")
    evidence = load_json(resolved, "merge-gate evidence")
    if not isinstance(evidence, dict):
        raise ReleaseEvidenceError(f"{resolved}: merge-gate evidence must be a JSON object")
    for key in ("base_sha", "head_sha"):
        if not is_hex40(evidence.get(key)):
            raise ReleaseEvidenceError(f"{resolved}: {key} must be a lowercase 40-char SHA")
    command_logs = merge_gate_command_logs(evidence, repo_root, resolved)
    return {
        "evidence_file": record,
        "pr_number": evidence.get("pr_number"),
        "pr_url": evidence.get("pr_url"),
        "base_sha": evidence.get("base_sha"),
        "head_sha": evidence.get("head_sha"),
        "run_mode": evidence.get("run_mode"),
        "quiet_seconds": evidence.get("quiet_seconds"),
        "review_gate": evidence.get("review_gate"),
        "local_command_count": len(command_logs),
        "command_logs": command_logs,
    }


def benchmark_record(path: Path, repo_root: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_root / path
    record = file_record(resolved, repo_root, role="benchmark_result")
    validator = repo_root / "benchmarks" / "validate_benchmark_result.py"
    completed = subprocess.run(
        [sys.executable, str(validator), str(resolved)],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "result_file": record,
        "validator": {
            "command": [sys.executable, str(validator), str(resolved)],
            "exit_code": completed.returncode,
            "stdout_sha256": sha256_bytes(completed.stdout.encode("utf-8")),
            "stderr_sha256": sha256_bytes(completed.stderr.encode("utf-8")),
            "passed": completed.returncode == 0,
        },
    }


def add_bundle_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload.pop("bundle_digest", None)
    payload["bundle_digest"] = {
        "algorithm": "sha256-canonical-json-without-bundle_digest",
        "sha256": sha256_canonical_json(payload),
    }
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = -1
    tmp_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        tmp_path.replace(path)
    finally:
        if fd != -1:
            os.close(fd)
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def collect_release_evidence(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    if not args.merge_gate_evidence:
        raise ReleaseEvidenceError("at least one --merge-gate-evidence file is required")
    schema_path = repo_root / RELEASE_EVIDENCE_SCHEMA
    schema = file_record(schema_path, repo_root, role="release_evidence_schema")
    git = git_metadata(
        repo_root,
        require_clean=args.require_clean,
        clean_ignore_prefixes=args.clean_ignore_prefix,
    )
    artifacts = [
        file_record(Path(path), repo_root, role="release_artifact")
        for path in args.artifact
    ]
    schema_artifacts = [
        file_record(Path(path), repo_root, role="schema_artifact")
        for path in args.schema_artifact
    ]
    merge_gates = [collect_merge_gate_evidence(Path(path), repo_root) for path in args.merge_gate_evidence]
    benchmarks = [benchmark_record(Path(path), repo_root) for path in args.benchmark_result]
    failed_benchmarks = [item for item in benchmarks if not item["validator"]["passed"]]
    if failed_benchmarks:
        failed = ", ".join(item["result_file"]["path"] for item in failed_benchmarks)
        raise ReleaseEvidenceError(f"benchmark validation failed for: {failed}")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "checkpoint": {
            "name": args.checkpoint,
            "kind": args.checkpoint_kind,
        },
        "repo_root": str(repo_root),
        "bundle_schema": schema,
        "git": git,
        "toolchain": toolchain_metadata(repo_root),
        "host": host_metadata(),
        "merge_gate_evidence": merge_gates,
        "benchmark_results": benchmarks,
        "artifacts": artifacts,
        "schema_artifacts": schema_artifacts,
        "non_claims": [
            "Does not verify external attestation signatures or trust chains.",
            "Does not replace the local merge gate; it records local evidence after it exists.",
            "Does not turn benchmark evidence into a performance claim without the benchmark result schema and logs.",
        ],
    }
    return add_bundle_digest(payload)


def validate_file_record(
    record: Any,
    field: str,
    errors: list[str],
    bundle_root: Path,
    repo_root: Path | None,
) -> Path | None:
    if not isinstance(record, dict):
        errors.append(f"{field} must be an object")
        return None
    raw_path = record.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        errors.append(f"{field}.path must be a non-empty string")
        return None
    if not is_hex64(record.get("sha256")):
        errors.append(f"{field}.sha256 must be lowercase 64-char hex")
        return None
    if not isinstance(record.get("size_bytes"), int) or record["size_bytes"] < 0:
        errors.append(f"{field}.size_bytes must be a non-negative integer")
    path = resolve_path(raw_path, bundle_root, repo_root)
    if not path.exists():
        errors.append(f"{field}.path does not exist: {path}")
        return path
    if not path.is_file():
        errors.append(f"{field}.path is not a regular file: {path}")
        return path
    actual_hash = sha256_file(path)
    if actual_hash != record.get("sha256"):
        errors.append(f"{field}.sha256 does not match file bytes: {path}")
    if isinstance(record.get("size_bytes"), int) and path.stat().st_size != record["size_bytes"]:
        errors.append(f"{field}.size_bytes does not match file bytes: {path}")
    return path


def validate_bundle_digest(payload: dict[str, Any], errors: list[str]) -> None:
    digest = payload.get("bundle_digest")
    if not isinstance(digest, dict):
        errors.append("bundle_digest must be an object")
        return
    if digest.get("algorithm") != "sha256-canonical-json-without-bundle_digest":
        errors.append("bundle_digest.algorithm is unsupported")
    recorded = digest.get("sha256")
    if not is_hex64(recorded):
        errors.append("bundle_digest.sha256 must be lowercase 64-char hex")
        return
    payload_without_digest = dict(payload)
    payload_without_digest.pop("bundle_digest", None)
    actual = sha256_canonical_json(payload_without_digest)
    if actual != recorded:
        errors.append("bundle_digest.sha256 does not match canonical payload")


def validate_merge_gate_record(
    record: Any,
    index: int,
    errors: list[str],
    bundle_root: Path,
    repo_root: Path | None,
    repo_head: str | None,
) -> None:
    field = f"merge_gate_evidence[{index}]"
    if not isinstance(record, dict):
        errors.append(f"{field} must be an object")
        return
    evidence_path = validate_file_record(
        record.get("evidence_file"),
        f"{field}.evidence_file",
        errors,
        bundle_root,
        repo_root,
    )
    command_logs = record.get("command_logs")
    if not isinstance(command_logs, list):
        errors.append(f"{field}.command_logs must be a list")
        command_logs = []
    if not isinstance(record.get("local_command_count"), int):
        errors.append(f"{field}.local_command_count must be an integer")
    elif record.get("local_command_count") != len(command_logs):
        errors.append(f"{field}.local_command_count does not match command_logs length")
    head_sha = record.get("head_sha")
    if not is_hex40(head_sha):
        errors.append(f"{field}.head_sha must be lowercase 40-char hex")
    elif repo_head and head_sha != repo_head:
        errors.append(f"{field}.head_sha does not match bundle git.head_sha")
    base_sha = record.get("base_sha")
    if not is_hex40(base_sha):
        errors.append(f"{field}.base_sha must be lowercase 40-char hex")
    if evidence_path and evidence_path.exists():
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{field}.evidence_file failed to parse: {exc}")
            evidence = None
        if isinstance(evidence, dict):
            if evidence.get("base_sha") != base_sha:
                errors.append(f"{field}.base_sha does not match evidence file")
            if evidence.get("head_sha") != head_sha:
                errors.append(f"{field}.head_sha does not match evidence file")
            evidence_commands = evidence.get("local_commands")
            if isinstance(evidence_commands, list) and len(evidence_commands) != len(command_logs):
                errors.append(f"{field}.command_logs length does not match evidence local_commands")
        else:
            evidence_commands = None
    else:
        evidence_commands = None
    for command_index, command in enumerate(command_logs):
        command_field = f"{field}.command_logs[{command_index}]"
        if not isinstance(command, dict):
            errors.append(f"{command_field} must be an object")
            continue
        raw_path = command.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"{command_field}.path must be a non-empty string")
            continue
        if command.get("matches_recorded") is not True:
            errors.append(f"{command_field}.matches_recorded must be true")
        if not is_hex64(command.get("sha256")):
            errors.append(f"{command_field}.sha256 must be lowercase 64-char hex")
            continue
        if command.get("recorded_sha256") != command.get("sha256"):
            errors.append(f"{command_field}.recorded_sha256 must match sha256")
        path = resolve_path(raw_path, bundle_root, repo_root)
        if isinstance(evidence_commands, list) and command_index < len(evidence_commands):
            evidence_command = evidence_commands[command_index]
            if not isinstance(evidence_command, dict):
                errors.append(f"{command_field} evidence local_commands entry must be an object")
            else:
                evidence_log_file = evidence_command.get("log_file")
                evidence_log_sha = evidence_command.get("log_sha256")
                if not isinstance(evidence_log_file, str) or not evidence_log_file:
                    errors.append(f"{command_field} evidence log_file is missing")
                else:
                    evidence_log_path = resolve_path(evidence_log_file, bundle_root, repo_root)
                    if evidence_log_path.resolve() != path.resolve():
                        errors.append(f"{command_field}.path does not match evidence local_commands log_file")
                if evidence_log_sha != command.get("sha256"):
                    errors.append(f"{command_field}.sha256 does not match evidence local_commands log_sha256")
        if not path.exists():
            errors.append(f"{command_field}.path does not exist: {path}")
            continue
        if sha256_file(path) != command["sha256"]:
            errors.append(f"{command_field}.sha256 does not match log bytes: {path}")


def validate_benchmark_record(
    record: Any,
    index: int,
    errors: list[str],
    bundle_root: Path,
    repo_root: Path | None,
    trusted_repo_root: Path | None,
) -> None:
    field = f"benchmark_results[{index}]"
    if not isinstance(record, dict):
        errors.append(f"{field} must be an object")
        return
    result_path = validate_file_record(
        record.get("result_file"),
        f"{field}.result_file",
        errors,
        bundle_root,
        repo_root,
    )
    validator = record.get("validator")
    if not isinstance(validator, dict):
        errors.append(f"{field}.validator must be an object")
    else:
        if validator.get("passed") is not True or validator.get("exit_code") != 0:
            errors.append(f"{field}.validator must have passed with exit_code 0")
        if not is_hex64(validator.get("stdout_sha256")):
            errors.append(f"{field}.validator.stdout_sha256 must be lowercase 64-char hex")
        if not is_hex64(validator.get("stderr_sha256")):
            errors.append(f"{field}.validator.stderr_sha256 must be lowercase 64-char hex")
    if result_path and result_path.exists() and trusted_repo_root is not None:
        validator_path = trusted_repo_root / "benchmarks" / "validate_benchmark_result.py"
        completed = subprocess.run(
            [sys.executable, str(validator_path), str(result_path)],
            cwd=trusted_repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            errors.append(f"{field}.result_file no longer passes benchmark validator")


def validate_release_evidence(path: Path, *, check_live_repo: bool = False) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"failed to parse JSON: {exc}"]
    if not isinstance(payload, dict):
        return ["release evidence must be a JSON object"]
    bundle_root = path.resolve().parent
    repo_root_raw = payload.get("repo_root")
    repo_root = Path(repo_root_raw) if isinstance(repo_root_raw, str) and repo_root_raw else None
    live_repo_root: Path | None = None
    trusted_repo_root: Path | None = None
    if check_live_repo:
        if repo_root is None:
            errors.append("repo_root must be a non-empty string for --check-live-repo")
        elif not repo_root.exists() or not repo_root.is_dir():
            errors.append("repo_root must be an existing directory for --check-live-repo")
        else:
            live_repo_root = repo_root.resolve()
            current_repo_root = default_repo_root().resolve()
            if live_repo_root == current_repo_root:
                trusted_repo_root = live_repo_root
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str) or not UTC_TIMESTAMP_RE.fullmatch(generated_at):
        errors.append("generated_at must be a UTC timestamp like 2026-04-18T00:00:00Z")
    validate_bundle_digest(payload, errors)
    validate_file_record(payload.get("bundle_schema"), "bundle_schema", errors, bundle_root, repo_root)
    checkpoint = payload.get("checkpoint")
    if not isinstance(checkpoint, dict):
        errors.append("checkpoint must be an object")
    else:
        if not isinstance(checkpoint.get("name"), str) or not checkpoint["name"]:
            errors.append("checkpoint.name must be a non-empty string")
        if not isinstance(checkpoint.get("kind"), str) or not checkpoint["kind"]:
            errors.append("checkpoint.kind must be a non-empty string")
    git = payload.get("git")
    repo_head = None
    if not isinstance(git, dict):
        errors.append("git must be an object")
    else:
        repo_head = git.get("head_sha") if is_hex40(git.get("head_sha")) else None
        if repo_head is None:
            errors.append("git.head_sha must be lowercase 40-char hex")
        if not isinstance(git.get("branch"), str) and git.get("branch") is not None:
            errors.append("git.branch must be string or null")
        if not isinstance(git.get("remote_origin"), str) and git.get("remote_origin") is not None:
            errors.append("git.remote_origin must be string or null")
        if not isinstance(git.get("remote_origin_had_credentials"), bool):
            errors.append("git.remote_origin_had_credentials must be boolean")
        ignored_prefixes = git.get("clean_ignored_prefixes")
        if not isinstance(ignored_prefixes, list) or not all(
            isinstance(prefix, str) for prefix in ignored_prefixes
        ):
            errors.append("git.clean_ignored_prefixes must be a string list")
        if not isinstance(git.get("dirty"), bool):
            errors.append("git.dirty must be boolean")
        if not is_hex64(git.get("status_sha256")):
            errors.append("git.status_sha256 must be lowercase 64-char hex")
        if live_repo_root is not None:
            live_head = run_capture(["git", "rev-parse", "HEAD"], live_repo_root)
            live_status = run_capture(["git", "status", "--porcelain"], live_repo_root)
            if live_head is not None and live_head != git.get("head_sha"):
                errors.append("git.head_sha does not match current repo HEAD")
            if live_status is not None:
                ignored_prefixes = (
                    git["clean_ignored_prefixes"]
                    if isinstance(git.get("clean_ignored_prefixes"), list)
                    and all(isinstance(prefix, str) for prefix in git["clean_ignored_prefixes"])
                    else []
                )
                live_status = filter_status_porcelain(live_status, ignored_prefixes)
                live_dirty = bool(live_status.strip())
                if isinstance(git.get("dirty"), bool) and live_dirty != git["dirty"]:
                    errors.append("git.dirty does not match current repo state")
                live_status_sha = sha256_bytes(live_status.encode("utf-8"))
                if is_hex64(git.get("status_sha256")) and live_status_sha != git["status_sha256"]:
                    errors.append("git.status_sha256 does not match current repo status")
    for key in ("toolchain", "host"):
        if not isinstance(payload.get(key), dict):
            errors.append(f"{key} must be an object")
    merge_gates = payload.get("merge_gate_evidence")
    if not isinstance(merge_gates, list):
        errors.append("merge_gate_evidence must be a list")
    elif not merge_gates:
        errors.append("merge_gate_evidence must contain at least one evidence record")
    else:
        for index, record in enumerate(merge_gates):
            validate_merge_gate_record(record, index, errors, bundle_root, repo_root, repo_head)
    benchmarks = payload.get("benchmark_results")
    if not isinstance(benchmarks, list):
        errors.append("benchmark_results must be a list")
    else:
        if check_live_repo and benchmarks and trusted_repo_root is None and live_repo_root is not None:
            errors.append(
                "benchmark_results cannot be live-validated safely unless repo_root "
                "matches the current trusted checkout"
            )
        for index, record in enumerate(benchmarks):
            validate_benchmark_record(
                record,
                index,
                errors,
                bundle_root,
                repo_root,
                trusted_repo_root,
            )
    for list_key in ("artifacts", "schema_artifacts"):
        records = payload.get(list_key)
        if not isinstance(records, list):
            errors.append(f"{list_key} must be a list")
        else:
            for index, record in enumerate(records):
                validate_file_record(record, f"{list_key}[{index}]", errors, bundle_root, repo_root)
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims:
        errors.append("non_claims must be a non-empty list")
    elif not all(isinstance(item, str) and "not" in item.lower() for item in non_claims):
        errors.append("non_claims entries must explicitly state non-claims")
    return errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="collect a release evidence bundle")
    collect.add_argument("--repo-root", default=str(default_repo_root()), help="repository root")
    collect.add_argument("--output", required=True, help="output JSON path")
    collect.add_argument("--checkpoint", required=True, help="checkpoint name")
    collect.add_argument("--checkpoint-kind", default="paper-release", help="checkpoint kind")
    collect.add_argument("--merge-gate-evidence", action="append", default=[], help="local merge-gate evidence.json to bind")
    collect.add_argument("--benchmark-result", action="append", default=[], help="benchmark result JSON to bind")
    collect.add_argument("--artifact", action="append", default=[], help="release artifact to hash")
    collect.add_argument("--schema-artifact", action="append", default=[], help="schema artifact to hash")
    collect.add_argument("--require-clean", action="store_true", help="fail when git status is dirty")
    collect.add_argument("--clean-ignore-prefix", action="append", default=[], help="repo-relative prefix ignored only for clean-status checks")

    validate = subparsers.add_parser("validate", help="validate a release evidence bundle")
    validate.add_argument("bundle", help="release evidence JSON")
    validate.add_argument("--check-live-repo", action="store_true", help="also compare recorded git state to the current repo_root checkout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.command == "collect":
        try:
            payload = collect_release_evidence(args)
            output = Path(args.output)
            write_json_atomic(output, payload)
            errors = validate_release_evidence(output, check_live_repo=True)
        except ReleaseEvidenceError as exc:
            print(f"release evidence collection failed: {exc}", file=sys.stderr)
            return 1
        if errors:
            for error in errors:
                print(f"release evidence validation error: {error}", file=sys.stderr)
            return 1
        print(f"release evidence bundle written: {output}")
        return 0
    if args.command == "validate":
        errors = validate_release_evidence(Path(args.bundle), check_live_repo=args.check_live_repo)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"release evidence bundle valid: {args.bundle}")
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
