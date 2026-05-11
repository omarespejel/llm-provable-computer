#!/usr/bin/env python3
"""Verify the zkAI competitor landscape systems commitment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import stat as stat_module
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "docs" / "engineering" / "evidence" / "zkai-competitor-landscape-2026-05.json"
MAX_EVIDENCE_JSON_BYTES = 1_048_576
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_SCHEMA = "zkai-competitor-landscape-v1"
EXPECTED_SYSTEMS_DOMAIN = "ptvm:zkai:competitor-landscape:systems:v1"


class CompetitorLandscapeCommitmentError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def systems_commitment(systems: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(systems))
    return f"blake2b-256:{digest.hexdigest()}"


def _open_repo_regular_file(path: pathlib.Path) -> tuple[int, pathlib.Path]:
    root = ROOT.resolve()
    candidate = path if path.is_absolute() else ROOT / path
    candidate = pathlib.Path(os.path.abspath(candidate))
    try:
        relative = candidate.relative_to(root)
    except ValueError as err:
        raise CompetitorLandscapeCommitmentError(f"evidence path escapes repository: {path}") from err

    current = root
    pre_stat = None
    try:
        for part in relative.parts:
            current = current / part
            part_stat = current.lstat()
            if stat_module.S_ISLNK(part_stat.st_mode):
                raise CompetitorLandscapeCommitmentError(f"evidence path must not traverse symlinks: {path}")
            pre_stat = part_stat
        if pre_stat is None or not stat_module.S_ISREG(pre_stat.st_mode):
            raise CompetitorLandscapeCommitmentError(f"evidence path is not a regular file: {path}")
        fd = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise CompetitorLandscapeCommitmentError(f"evidence path is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise CompetitorLandscapeCommitmentError(f"evidence path changed while reading: {path}")
            opened_fd = fd
            fd = None
            return opened_fd, candidate
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise CompetitorLandscapeCommitmentError(f"failed to read evidence path {path}: {err}") from err


def load_payload(path: pathlib.Path) -> dict[str, Any]:
    fd, _candidate = _open_repo_regular_file(path)
    with os.fdopen(fd, "rb") as handle:
        raw = handle.read(MAX_EVIDENCE_JSON_BYTES + 1)
    if len(raw) > MAX_EVIDENCE_JSON_BYTES:
        raise CompetitorLandscapeCommitmentError(
            f"evidence JSON exceeds max size: got at least {len(raw)} bytes, limit {MAX_EVIDENCE_JSON_BYTES}"
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise CompetitorLandscapeCommitmentError(f"invalid JSON in {path}: {err}") from err
    if not isinstance(payload, dict):
        raise CompetitorLandscapeCommitmentError("competitor landscape evidence must be a JSON object")
    return payload


def validate_payload(payload: dict[str, Any]) -> str:
    schema_version = payload.get("schema_version")
    if type(schema_version) is not int or schema_version != EXPECTED_SCHEMA_VERSION:
        raise CompetitorLandscapeCommitmentError("schema_version drift")

    schema = payload.get("schema")
    if schema != EXPECTED_SCHEMA:
        raise CompetitorLandscapeCommitmentError("schema drift")

    domain = payload.get("systems_commitment_domain")
    if domain != EXPECTED_SYSTEMS_DOMAIN:
        raise CompetitorLandscapeCommitmentError("systems_commitment_domain drift")

    stored = payload.get("systems_commitment")
    if not isinstance(stored, str) or not stored.startswith("blake2b-256:"):
        raise CompetitorLandscapeCommitmentError("systems_commitment must be a blake2b-256 commitment")
    digest = stored.removeprefix("blake2b-256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise CompetitorLandscapeCommitmentError("systems_commitment must contain a lowercase 32-byte hex digest")

    systems = payload.get("systems")
    if not isinstance(systems, list) or not systems:
        raise CompetitorLandscapeCommitmentError("systems must be a non-empty list")

    expected = systems_commitment(systems, domain)
    if stored != expected:
        raise CompetitorLandscapeCommitmentError(
            f"systems commitment mismatch: stored {stored}, recomputed {expected}"
        )
    return expected


def check_path(path: pathlib.Path) -> str:
    return validate_payload(load_payload(path))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence",
        type=pathlib.Path,
        default=DEFAULT_EVIDENCE,
        help="competitor landscape evidence JSON to validate",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        commitment = check_path(args.evidence)
    except CompetitorLandscapeCommitmentError as err:
        print(f"competitor landscape commitment check failed: {err}", file=sys.stderr)
        return 1
    print(f"competitor landscape systems commitment OK: {commitment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
