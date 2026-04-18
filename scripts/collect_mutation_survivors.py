#!/usr/bin/env python3
"""Collect and validate mutation-survivor evidence.

This script intentionally understands a small, stable surface of cargo-mutants
output: the text files that list caught, missed, timed-out, and unviable mutants.
It is used to turn a heavy local mutation run into explicit evidence instead of
letting survivors disappear into an untracked `mutants.out` directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPORT_SCHEMA = "mutation-survivor-report-v1"
LEDGER_SCHEMA = "mutation-survivor-ledger-v1"
CHUNK_SIZE = 1024 * 1024
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

OUTCOME_FILES = {
    "caught": ("caught.txt", "caught"),
    "survived": ("missed.txt", "missed"),
    "timeout": ("timeout.txt", "timeout"),
    "unviable": ("unviable.txt", "unviable"),
}


class MutationEvidenceError(RuntimeError):
    pass


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def path_for_json(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(repo_root.resolve()))
    except ValueError:
        return str(resolved)


def run_capture(args: list[str], cwd: Path) -> str | None:
    try:
        return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def parse_outcome_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    if not path.is_file():
        raise MutationEvidenceError(f"outcome path is not a regular file: {path}")
    lines = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return lines


def first_existing(root: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def outcome_records(mutants_dir: Path, repo_root: Path) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    outcomes: dict[str, list[str]] = {}
    source_files: list[dict[str, Any]] = []
    for outcome, names in OUTCOME_FILES.items():
        path = first_existing(mutants_dir, names)
        if path is None:
            outcomes[outcome] = []
            continue
        lines = parse_outcome_file(path)
        outcomes[outcome] = lines
        source_files.append(
            {
                "role": f"cargo_mutants_{outcome}",
                "path": path_for_json(path, repo_root),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "entries": len(lines),
            }
        )
    return outcomes, source_files


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    mutants_dir = Path(args.mutants_dir).resolve()
    if not mutants_dir.exists():
        raise MutationEvidenceError(f"mutants directory does not exist: {mutants_dir}")
    if not mutants_dir.is_dir():
        raise MutationEvidenceError(f"mutants directory is not a directory: {mutants_dir}")

    outcomes, source_files = outcome_records(mutants_dir, repo_root)
    target_files = list(args.target or [])
    if not target_files:
        target_output = run_capture(["bash", "scripts/run_mutation_suite.sh", "--print-targets"], repo_root)
        target_files = target_output.splitlines() if target_output else []

    counts = {name: len(values) for name, values in outcomes.items()}
    counts["total_classified"] = sum(counts.values())

    return {
        "schema": REPORT_SCHEMA,
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "mutants_dir": path_for_json(mutants_dir, repo_root),
        "tool": {
            "cargo_mutants": run_capture(["cargo", "mutants", "--version"], repo_root),
            "rustc": run_capture(["rustc", "--version"], repo_root),
            "cargo": run_capture(["cargo", "--version"], repo_root),
        },
        "target_files": target_files,
        "counts": counts,
        "source_files": source_files,
        "survived": outcomes["survived"],
        "timeouts": outcomes["timeout"],
        "unviable": outcomes["unviable"],
        "policy": {
            "survived_or_timeout_requires_triage": True,
            "paper_milestone_requires_no_untriaged_survivors": True,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_ledger_json(markdown_path: Path) -> Any:
    text = markdown_path.read_text(encoding="utf-8")
    marker = "```json mutation-survivors-v1"
    start = text.find(marker)
    if start == -1:
        raise MutationEvidenceError("missing ```json mutation-survivors-v1 ledger block")
    start = text.find("\n", start)
    if start == -1:
        raise MutationEvidenceError("ledger block has no JSON payload")
    end = text.find("```", start + 1)
    if end == -1:
        raise MutationEvidenceError("ledger block is not closed")
    payload = text[start:end].strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise MutationEvidenceError(f"ledger JSON is malformed: {exc}") from exc


def require_string_list(value: Any, field: str, errors: list[str], *, non_empty: bool = False) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        errors.append(f"{field} must be a list of non-empty strings")
    elif non_empty and not value:
        errors.append(f"{field} must not be empty")


def validate_triage_entries(entries: Any, field: str, errors: list[str]) -> None:
    if not isinstance(entries, list):
        errors.append(f"{field} must be a list")
        return
    for index, entry in enumerate(entries):
        entry_field = f"{field}[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_field} must be an object")
            continue
        for key in ("mutant", "target", "outcome", "classification", "evidence", "next_action"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                errors.append(f"{entry_field}.{key} must be a non-empty string")
        if entry.get("classification") == "untriaged":
            errors.append(f"{entry_field}.classification must not be untriaged")
        if entry.get("outcome") not in {"survived", "timeout"}:
            errors.append(f"{entry_field}.outcome must be survived or timeout")
        if not isinstance(entry.get("paper_blocker"), bool):
            errors.append(f"{entry_field}.paper_blocker must be boolean")


def validate_ledger(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["ledger must be a JSON object"]
    if payload.get("schema") != LEDGER_SCHEMA:
        errors.append(f"schema must be {LEDGER_SCHEMA}")
    updated_at = payload.get("updated_at")
    if not isinstance(updated_at, str) or not UTC_TIMESTAMP_RE.fullmatch(updated_at):
        errors.append("updated_at must be a UTC timestamp like 2026-04-18T00:00:00Z")
    require_string_list(payload.get("trusted_targets"), "trusted_targets", errors, non_empty=True)
    require_string_list(payload.get("milestone_commands"), "milestone_commands", errors, non_empty=True)
    non_claims = payload.get("non_claims")
    require_string_list(non_claims, "non_claims", errors, non_empty=True)
    current_status = payload.get("current_status")
    if not isinstance(current_status, dict):
        errors.append("current_status must be an object")
    else:
        validate_triage_entries(current_status.get("surviving_mutants"), "current_status.surviving_mutants", errors)
        validate_triage_entries(current_status.get("timed_out_mutants"), "current_status.timed_out_mutants", errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    summarize = subparsers.add_parser("summarize", help="summarize a cargo-mutants output directory")
    summarize.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    summarize.add_argument("--mutants-dir", required=True)
    summarize.add_argument("--output", required=True)
    summarize.add_argument("--target", action="append", default=[])

    check_doc = subparsers.add_parser("check-doc", help="validate docs/engineering/mutation-survivors.md")
    check_doc.add_argument("path", help="mutation survivor ledger markdown")

    args = parser.parse_args(argv)
    try:
        if args.command == "summarize":
            summary = build_summary(args)
            write_json(Path(args.output), summary)
            print(f"mutation survivor summary written: {args.output}")
            if summary["survived"] or summary["timeouts"]:
                print(
                    "warning: mutation survivors/timeouts require triage in docs/engineering/mutation-survivors.md",
                    file=sys.stderr,
                )
            return 0
        if args.command == "check-doc":
            ledger = extract_ledger_json(Path(args.path))
            errors = validate_ledger(ledger)
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
            print(f"mutation survivor ledger valid: {args.path}")
            return 0
    except MutationEvidenceError as exc:
        print(f"mutation survivor evidence error: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
