#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat as stat_module
import subprocess
import sys
from typing import Optional


class DirtyFingerprintError(RuntimeError):
    pass


def _git_output(repo_root: pathlib.Path, command: list[str]) -> bytes:
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise DirtyFingerprintError(f"failed to run {' '.join(command)}: executable not found") from error
    except OSError as error:
        raise DirtyFingerprintError(f"failed to run {' '.join(command)}: {error}") from error

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).decode("utf-8", "replace").strip()
        suffix = f": {detail}" if detail else ""
        raise DirtyFingerprintError(
            f"git command failed ({' '.join(command)}): exit {result.returncode}{suffix}"
        )
    return result.stdout


def compute_dirty_fingerprint(repo_root: pathlib.Path, limit: int) -> tuple[str, bool]:
    if limit < 0:
        raise DirtyFingerprintError("dirty fingerprint byte limit must be non-negative")

    repo_root = repo_root.resolve(strict=True)
    remaining = limit
    truncated = False
    hasher = hashlib.sha256()

    status = _git_output(repo_root, ["git", "status", "--porcelain=v1", "-z"])
    hasher.update(b"status\0")
    hasher.update(status)

    paths: set[bytes] = set()
    for command in (
        ["git", "diff", "--name-only", "-z", "--no-ext-diff"],
        ["git", "diff", "--cached", "--name-only", "-z", "--no-ext-diff"],
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    ):
        output = _git_output(repo_root, command)
        paths.update(path for path in output.split(b"\0") if path)

    for raw_path in sorted(paths):
        path_text = raw_path.decode("utf-8", "surrogateescape")
        repo_relative_path = pathlib.Path(path_text)
        if repo_relative_path.is_absolute() or ".." in repo_relative_path.parts:
            raise DirtyFingerprintError(
                f"dirty fingerprint path escapes repository: {path_text!r}"
            )
        path = repo_root / repo_relative_path
        hasher.update(b"path\0")
        hasher.update(raw_path)
        hasher.update(b"\0")
        try:
            file_stat = path.lstat()
        except OSError as error:
            hasher.update(f"missing:{error.errno}".encode("ascii"))
            continue
        hasher.update(f"mode:{file_stat.st_mode}:size:{file_stat.st_size}".encode("ascii"))
        if stat_module.S_ISLNK(file_stat.st_mode):
            try:
                link_target = os.readlink(path)
            except OSError as error:
                raise DirtyFingerprintError(
                    f"failed to read dirty symlink target {path_text!r}: {error}"
                ) from error
            hasher.update(b"symlink\0")
            hasher.update(os.fsencode(link_target))
            continue
        if not stat_module.S_ISREG(file_stat.st_mode):
            continue
        if remaining <= 0:
            truncated = True
            continue
        fd = None
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        except OSError as error:
            raise DirtyFingerprintError(
                f"failed to read dirty file {path_text!r}: {error}"
            ) from error
        try:
            open_stat = os.fstat(fd)
            if not stat_module.S_ISREG(open_stat.st_mode):
                raise DirtyFingerprintError(f"dirty path is no longer a regular file: {path_text!r}")
            if (open_stat.st_dev, open_stat.st_ino) != (file_stat.st_dev, file_stat.st_ino):
                raise DirtyFingerprintError(f"dirty file changed while fingerprinting: {path_text!r}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                chunk = handle.read(min(remaining, open_stat.st_size))
        except OSError as error:
            raise DirtyFingerprintError(
                f"failed to read dirty file {path_text!r}: {error}"
            ) from error
        finally:
            if fd is not None:
                os.close(fd)
        hasher.update(chunk)
        remaining -= len(chunk)
        if open_stat.st_size > len(chunk):
            truncated = True

    return hasher.hexdigest(), truncated


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit the Phase40 dirty-state fingerprint hash and truncation flag."
    )
    parser.add_argument("limit", type=int, help="maximum regular-file bytes to hash")
    parser.add_argument(
        "--repo-root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="git repository root; defaults to the current working directory",
    )
    args = parser.parse_args(argv)

    try:
        fingerprint, truncated = compute_dirty_fingerprint(args.repo_root, args.limit)
    except DirtyFingerprintError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(fingerprint)
    print("true" if truncated else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
