#!/usr/bin/env python3
"""Lint agent-native research issue templates and ledger files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


TEMPLATE_REQUIRED_IDS = {
    "research-frontier.yml": {
        "owner_role",
        "thesis",
        "why_it_matters_for_serious_paper",
        "smallest_falsifying_experiment",
        "go_gate",
        "no_go_gate",
        "required_artifacts",
        "non_claims",
        "local_validation_plan",
    },
    "hardening-followup.yml": {
        "observed_risk",
        "evidence_or_location",
        "why_not_current_pr",
        "smallest_fix_or_test",
        "go_no_go",
        "local_validation_plan",
    },
    "paper-claim.yml": {
        "claim",
        "evidence_paths",
        "claim_boundary",
        "non_claims",
        "competitor_context",
        "promotion_gate",
        "local_validation_plan",
    },
}

LEDGER_REQUIRED_FIELDS = {
    "id",
    "status",
    "thesis",
    "why_it_matters_for_serious_paper",
    "smallest_falsifying_experiment",
    "go_gate",
    "no_go_gate",
    "required_artifacts",
    "non_claims",
}

LEDGER_REQUIRED_STRINGS = {
    "thesis",
    "why_it_matters_for_serious_paper",
    "smallest_falsifying_experiment",
    "go_gate",
    "no_go_gate",
}

LEDGER_REQUIRED_NON_EMPTY_STRING_LISTS = {
    "required_artifacts",
    "non_claims",
}

LEDGER_OPTIONAL_STRING_LISTS = {
    "evidence_paths",
    "blocked_by",
}

LEDGER_ALLOWED_FIELDS = (
    LEDGER_REQUIRED_FIELDS
    | {"owner_role"}
    | LEDGER_OPTIONAL_STRING_LISTS
)

LEDGER_STATUSES = {
    "EXPLORE",
    "EXECUTE",
    "PAPER_CANDIDATE",
    "FOLLOWUP",
    "GO",
    "NARROW_CLAIM",
    "FOLLOWUP_ISSUE",
    "KILL",
    "NO_GO",
    "DONE",
}

LEDGER_OWNER_ROLES = {"scout", "experimenter", "skeptic", "integrator"}


def _template_ids(text: str) -> list[str]:
    ids: list[str] = []
    block_scalar_indent: int | None = None
    block_scalar_pattern = re.compile(r"^(?P<indent>\s*)[A-Za-z0-9_-]+:\s*[|>][-+0-9 ]*(?:#.*)?$")
    id_pattern = re.compile(r"^\s*id:\s*([a-z0-9_-]+)\s*(?:#.*)?$")

    for line in text.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if block_scalar_indent is not None:
            if not stripped:
                continue
            if indent > block_scalar_indent:
                continue
            block_scalar_indent = None

        block_match = block_scalar_pattern.match(line)
        if block_match:
            block_scalar_indent = len(block_match.group("indent"))
            continue

        id_match = id_pattern.match(line)
        if id_match:
            ids.append(id_match.group(1))

    return ids


def lint_issue_templates(repo_root: Path) -> list[str]:
    errors: list[str] = []
    template_dir = repo_root / ".github" / "ISSUE_TEMPLATE"
    config_path = template_dir / "config.yml"
    if not config_path.is_file():
        if config_path.exists():
            errors.append(f"{config_path}: issue template config must be a file")
        else:
            errors.append(f"missing issue template config file: {config_path}")
    elif not _blank_issues_disabled(config_path.read_text(encoding="utf-8")):
        errors.append(f"{config_path}: blank issues must be disabled")

    for filename, required_ids in sorted(TEMPLATE_REQUIRED_IDS.items()):
        path = template_dir / filename
        if not path.is_file():
            if path.exists():
                errors.append(f"{path}: issue template must be a file")
            else:
                errors.append(f"missing issue template: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        found_ids = _template_ids(text)
        found_id_set = set(found_ids)
        missing_ids = sorted(required_ids - found_id_set)
        if missing_ids:
            errors.append(f"{path}: missing ids: {', '.join(missing_ids)}")
        duplicate_ids = sorted(id_ for id_, count in Counter(found_ids).items() if count > 1)
        if duplicate_ids:
            errors.append(f"{path}: duplicate ids: {', '.join(duplicate_ids)}")
        if "Do not use GitHub CI as the research loop." not in text:
            errors.append(f"{path}: must remind agents not to use GitHub CI as the research loop")
    return errors


def lint_research_policy(repo_root: Path) -> list[str]:
    errors: list[str] = []
    required_files = [
        repo_root / ".codex" / "research" / "north_star.yml",
        repo_root / ".codex" / "research" / "operating_model.yml",
        repo_root / ".codex" / "research" / "schemas" / "frontier_track.schema.json",
    ]
    for path in required_files:
        if not path.is_file():
            if path.exists():
                errors.append(f"{path}: research policy path must be a file")
            else:
                errors.append(f"missing research policy file: {path}")

    operating_model = repo_root / ".codex" / "research" / "operating_model.yml"
    if operating_model.is_file():
        text = operating_model.read_text(encoding="utf-8")
        for needle in ("qodo", "coderabbit", "local_first", "workflow_dispatch"):
            if needle not in text:
                errors.append(f"{operating_model}: missing policy keyword {needle!r}")

    return errors


def lint_frontier_ledger(repo_root: Path) -> list[str]:
    errors: list[str] = []
    path = repo_root / ".codex" / "research" / "frontier_ledger.jsonl"
    if not path.exists():
        return errors
    if not path.is_file():
        errors.append(f"{path}: frontier ledger must be a file")
        return errors

    seen_ids: set[str] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(entry, dict):
            errors.append(f"{path}:{line_number}: ledger entry must be a JSON object")
            continue

        missing = sorted(LEDGER_REQUIRED_FIELDS - set(entry))
        if missing:
            errors.append(f"{path}:{line_number}: missing fields: {', '.join(missing)}")
        extra = sorted(set(entry) - LEDGER_ALLOWED_FIELDS)
        if extra:
            errors.append(f"{path}:{line_number}: unknown fields: {', '.join(extra)}")
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not re.match(r"^[a-z0-9][a-z0-9_-]*$", entry_id):
            errors.append(f"{path}:{line_number}: invalid id")
        elif entry_id in seen_ids:
            errors.append(f"{path}:{line_number}: duplicate id {entry_id}")
        else:
            seen_ids.add(entry_id)
        if entry.get("status") not in LEDGER_STATUSES:
            errors.append(f"{path}:{line_number}: invalid status {entry.get('status')!r}")
        for field in LEDGER_REQUIRED_STRINGS:
            if field in entry and not _non_empty_string(entry[field]):
                errors.append(f"{path}:{line_number}: {field} must be a non-empty string")
        for field in LEDGER_REQUIRED_NON_EMPTY_STRING_LISTS:
            if not isinstance(entry.get(field), list) or not entry.get(field):
                errors.append(f"{path}:{line_number}: {field} must be a non-empty list")
            elif not all(_non_empty_string(item) for item in entry[field]):
                errors.append(f"{path}:{line_number}: {field} entries must be non-empty strings")
        owner_role = entry.get("owner_role")
        if "owner_role" in entry and owner_role not in LEDGER_OWNER_ROLES:
            errors.append(f"{path}:{line_number}: invalid owner_role {owner_role!r}")
        for field in LEDGER_OPTIONAL_STRING_LISTS:
            if field in entry:
                if not isinstance(entry[field], list):
                    errors.append(f"{path}:{line_number}: {field} must be a list")
                elif not all(_non_empty_string(item) for item in entry[field]):
                    errors.append(f"{path}:{line_number}: {field} entries must be non-empty strings")

    return errors


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _blank_issues_disabled(text: str) -> bool:
    for line in text.splitlines():
        key_value = line.split("#", 1)[0].strip()
        if not key_value or ":" not in key_value:
            continue
        key, value = key_value.split(":", 1)
        if key.strip() == "blank_issues_enabled":
            return value.strip().lower() == "false"
    return False


def lint(repo_root: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(lint_issue_templates(repo_root))
    errors.extend(lint_research_policy(repo_root))
    errors.extend(lint_frontier_ledger(repo_root))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    errors = lint(repo_root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("research issue lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
