#!/usr/bin/env python3
"""Lightweight benchmark evidence harness.

The harness is intentionally safe by default: it loads a case manifest, records
repository and host metadata, and emits a JSON plan unless --run is provided.
When execution is enabled, commands are run without a shell, outputs are stored
next to the JSON result, and repeated runs are summarized with p50/p95.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


@dataclasses.dataclass(frozen=True)
class InputSpec:
    path: Path
    label: str | None = None
    optional: bool = False


@dataclasses.dataclass(frozen=True)
class CaseSpec:
    name: str
    command: list[str]
    description: str | None = None
    cwd: Path | None = None
    repeat: int = 1
    env: dict[str, str] | None = None
    timeout_s: float | None = None
    allow_failure: bool = False
    inputs: list[InputSpec] = dataclasses.field(default_factory=list)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sanitize_token(value: str | None, fallback: str = "anon") -> str:
    if not value:
        return fallback
    pieces = []
    for char in value:
        if char.isalnum() or char in {"-", "_", "."}:
            pieces.append(char)
        else:
            pieces.append("_")
    cleaned = "".join(pieces).strip("._")
    return cleaned or fallback


def percentile(values: list[float], pct: float) -> float:
    if not values:
        raise ValueError("cannot compute percentile on an empty list")
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def load_case_manifest(path: Path) -> tuple[dict[str, Any], list[CaseSpec]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        manifest_meta: dict[str, Any] = {}
        cases_raw = raw
    elif isinstance(raw, dict):
        manifest_meta = {k: v for k, v in raw.items() if k != "cases"}
        cases_raw = raw.get("cases", [])
        if not isinstance(cases_raw, list):
            raise ValueError("case manifest must contain a list under 'cases'")
    else:
        raise ValueError("case manifest must be a JSON object or list")

    cases: list[CaseSpec] = []
    for index, entry in enumerate(cases_raw, 1):
        if not isinstance(entry, dict):
            raise ValueError(f"case #{index} must be an object")
        name = entry.get("name")
        command = entry.get("command")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"case #{index} is missing a non-empty name")
        if not isinstance(command, list) or not command or not all(
            isinstance(arg, str) for arg in command
        ):
            raise ValueError(f"case {name!r} must define command as a non-empty string list")
        repeat = int(entry.get("repeat", 1))
        if repeat < 1:
            raise ValueError(f"case {name!r} repeat must be >= 1")
        cwd_value = entry.get("cwd")
        cwd = (repo_root() / cwd_value).resolve() if isinstance(cwd_value, str) else None
        env_value = entry.get("env")
        env = None
        if env_value is not None:
            if not isinstance(env_value, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in env_value.items()
            ):
                raise ValueError(f"case {name!r} env must be a string-to-string object")
            env = dict(env_value)
        inputs: list[InputSpec] = []
        for raw_input in entry.get("inputs", []) or []:
            if isinstance(raw_input, str):
                inputs.append(InputSpec(path=(repo_root() / raw_input).resolve()))
                continue
            if isinstance(raw_input, dict):
                path_value = raw_input.get("path")
                if not isinstance(path_value, str) or not path_value:
                    raise ValueError(f"case {name!r} input entries need a path")
                label_value = raw_input.get("label")
                optional_value = bool(raw_input.get("optional", False))
                inputs.append(
                    InputSpec(
                        path=(repo_root() / path_value).resolve(),
                        label=label_value if isinstance(label_value, str) else None,
                        optional=optional_value,
                    )
                )
                continue
            raise ValueError(f"case {name!r} inputs must be strings or objects")
        timeout_value = entry.get("timeout_s")
        timeout_s = float(timeout_value) if timeout_value is not None else None
        cases.append(
            CaseSpec(
                name=name,
                description=entry.get("description") if isinstance(entry.get("description"), str) else None,
                command=list(command),
                cwd=cwd,
                repeat=repeat,
                env=env,
                timeout_s=timeout_s,
                allow_failure=bool(entry.get("allow_failure", False)),
                inputs=inputs,
            )
        )
    return manifest_meta, cases


def git_metadata(root: Path) -> dict[str, Any]:
    def capture(args: list[str]) -> str | None:
        try:
            result = subprocess.run(
                args,
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
        return result.stdout.strip()

    head = capture(["git", "rev-parse", "HEAD"])
    short_head = capture(["git", "rev-parse", "--short", "HEAD"])
    status = capture(["git", "status", "--short"])
    branch = capture(["git", "branch", "--show-current"])
    return {
        "sha": head,
        "short_sha": short_head,
        "branch": branch,
        "dirty": bool(status),
        "status_porcelain": status.splitlines() if status else [],
    }


def toolchain_metadata(root: Path) -> dict[str, Any]:
    def capture(args: list[str]) -> str | None:
        try:
            result = subprocess.run(
                args,
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
        return result.stdout.strip()

    rustc_vv = capture(["rustc", "-Vv"])
    cargo_v = capture(["cargo", "-V"])
    rustup_active = capture(["rustup", "show", "active-toolchain"])
    return {
        "rustc_vv": rustc_vv,
        "cargo_v": cargo_v,
        "rustup_active_toolchain": rustup_active,
        "python_version": sys.version.split()[0],
    }


def host_metadata() -> dict[str, Any]:
    uname = platform.uname()
    return {
        "system": uname.system,
        "node": uname.node,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "processor": uname.processor,
        "cpu_count": os.cpu_count(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def peak_rss_unit() -> str:
    return "kilobytes" if platform.system() == "Linux" else "bytes"


def hash_inputs(inputs: list[InputSpec]) -> list[dict[str, Any]]:
    hashed: list[dict[str, Any]] = []
    for spec in inputs:
        if not spec.path.exists():
            if spec.optional:
                hashed.append(
                    {
                        "path": str(spec.path),
                        "label": spec.label,
                        "optional": True,
                        "exists": False,
                        "sha256": None,
                        "size_bytes": None,
                    }
                )
                continue
            raise FileNotFoundError(f"missing input file: {spec.path}")
        hashed.append(
            {
                "path": str(spec.path),
                "label": spec.label,
                "optional": spec.optional,
                "exists": True,
                "sha256": sha256_file(spec.path),
                "size_bytes": spec.path.stat().st_size,
            }
        )
    return hashed


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_case(
    case: CaseSpec,
    run_root: Path,
    dry_run: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": case.name,
        "description": case.description,
        "command": case.command,
        "cwd": str(case.cwd or repo_root()),
        "repeat": case.repeat,
        "allow_failure": case.allow_failure,
        "inputs": hash_inputs(case.inputs),
        "runs": [],
    }
    if dry_run:
        result["status"] = "dry-run"
        return result

    env = os.environ.copy()
    if case.env:
        env.update(case.env)

    case_dir = run_root / sanitize_token(case.name)
    case_dir.mkdir(parents=True, exist_ok=True)

    durations_ms: list[float] = []
    failed_runs: list[dict[str, Any]] = []

    for run_index in range(1, case.repeat + 1):
        stdout_path = case_dir / f"run-{run_index}.stdout.txt"
        stderr_path = case_dir / f"run-{run_index}.stderr.txt"
        started_at = utc_now()
        started_perf = time.perf_counter()
        timed_out = False
        returncode: int | None = None
        peak_rss_value: int | None = None
        user_time_s: float | None = None
        system_time_s: float | None = None

        with tempfile.TemporaryFile() as stdout_tmp, tempfile.TemporaryFile() as stderr_tmp:
            proc = subprocess.Popen(
                case.command,
                cwd=str(case.cwd or repo_root()),
                env=env,
                stdout=stdout_tmp,
                stderr=stderr_tmp,
            )
            try:
                if hasattr(os, "wait4"):
                    if case.timeout_s is None:
                        _, status, rusage = os.wait4(proc.pid, 0)
                    else:
                        deadline = time.monotonic() + case.timeout_s
                        while True:
                            pid, status, rusage = os.wait4(proc.pid, os.WNOHANG)
                            if pid != 0:
                                break
                            if time.monotonic() >= deadline:
                                timed_out = True
                                proc.kill()
                                _, status, rusage = os.wait4(proc.pid, 0)
                                break
                            time.sleep(0.05)
                    returncode = os.waitstatus_to_exitcode(status)
                    peak_rss_value = getattr(rusage, "ru_maxrss", None)
                    user_time_s = getattr(rusage, "ru_utime", None)
                    system_time_s = getattr(rusage, "ru_stime", None)
                else:
                    proc.wait(timeout=case.timeout_s)
                    returncode = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                proc.wait()
                returncode = proc.returncode
            ended_perf = time.perf_counter()
            stdout_tmp.seek(0)
            stderr_tmp.seek(0)
            stdout_bytes = stdout_tmp.read()
            stderr_bytes = stderr_tmp.read()

        write_text(stdout_path, stdout_bytes.decode("utf-8", errors="replace"))
        write_text(stderr_path, stderr_bytes.decode("utf-8", errors="replace"))

        duration_ms = (ended_perf - started_perf) * 1000.0
        durations_ms.append(duration_ms)
        run_record = {
            "index": run_index,
            "started_at": started_at,
            "ended_at": utc_now(),
            "duration_ms": round(duration_ms, 3),
            "returncode": returncode,
            "timed_out": timed_out,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_sha256": sha256_bytes(stdout_bytes),
            "stderr_sha256": sha256_bytes(stderr_bytes),
            "stdout_size_bytes": len(stdout_bytes),
            "stderr_size_bytes": len(stderr_bytes),
            "peak_rss": peak_rss_value,
            "peak_rss_unit": peak_rss_unit() if peak_rss_value is not None else None,
            "user_time_s": round(user_time_s, 6) if user_time_s is not None else None,
            "system_time_s": round(system_time_s, 6) if system_time_s is not None else None,
        }
        result["runs"].append(run_record)

        if returncode != 0:
            failed_runs.append(run_record)
            if not case.allow_failure:
                break

    result["status"] = "passed" if not failed_runs else "failed"
    if durations_ms:
        result["summary"] = {
            "runs": len(durations_ms),
            "min_ms": round(min(durations_ms), 3),
            "mean_ms": round(statistics.mean(durations_ms), 3),
            "p50_ms": round(percentile(durations_ms, 0.50), 3),
            "p95_ms": round(percentile(durations_ms, 0.95), 3),
            "max_ms": round(max(durations_ms), 3),
        }
    else:
        result["summary"] = {"runs": 0}
    if failed_runs:
        result["failed_runs"] = failed_runs
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        default="benchmarks/cases.example.json",
        help="Path to the benchmark case manifest.",
    )
    parser.add_argument(
        "--output",
        help="Output JSON path. Defaults to benchmarks/results/benchmark-<timestamp>.json.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the benchmark commands instead of emitting a dry-run plan.",
    )
    parser.add_argument(
        "--select",
        action="append",
        default=[],
        help="Run only cases whose names match one of these values.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    root = repo_root()
    cases_path = (root / args.cases).resolve() if not Path(args.cases).is_absolute() else Path(args.cases)
    if not cases_path.exists():
        print(f"benchmark case manifest not found: {cases_path}", file=sys.stderr)
        return 2

    manifest_meta, cases = load_case_manifest(cases_path)
    if args.select:
        selected = set(args.select)
        cases = [case for case in cases if case.name in selected]
    if not cases:
        print("no benchmark cases selected", file=sys.stderr)
        return 2

    output_path = Path(args.output) if args.output else root / "benchmarks" / "results" / f"benchmark-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
    if not output_path.is_absolute():
        output_path = (root / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run_root = output_path.parent / f"{output_path.stem}-logs"
    run_root.mkdir(parents=True, exist_ok=True)

    dry_run = not args.run
    case_manifest_hash = sha256_file(cases_path)
    harness_hash = sha256_file(Path(__file__).resolve())
    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "mode": "dry-run" if dry_run else "run",
        "repo_root": str(root),
        "output_path": str(output_path),
        "benchmark_root": str(Path(__file__).resolve().parent),
        "case_manifest": {
            "path": str(cases_path),
            "sha256": case_manifest_hash,
            "metadata": manifest_meta,
        },
        "harness": {
            "path": str(Path(__file__).resolve()),
            "sha256": harness_hash,
        },
        "inputs": [
            {
                "path": str(cases_path),
                "role": "case_manifest",
                "sha256": case_manifest_hash,
            },
            {
                "path": str(Path(__file__).resolve()),
                "role": "harness",
                "sha256": harness_hash,
            },
        ],
        "git": git_metadata(root),
        "toolchain": toolchain_metadata(root),
        "host": host_metadata(),
        "selected_cases": [case.name for case in cases],
        "cases": [],
    }

    exit_code = 0
    for case in cases:
        case_result = run_case(case, run_root=run_root, dry_run=dry_run)
        payload["cases"].append(case_result)
        if case_result["status"] == "failed" and not case.allow_failure:
            exit_code = 1

    write_text(output_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"wrote benchmark JSON: {output_path}")
    print(f"mode: {payload['mode']}")
    for case in payload["cases"]:
        summary = case.get("summary", {})
        print(
            f"- {case['name']}: {case['status']}"
            + (f" (runs={summary.get('runs', 0)}, p50_ms={summary.get('p50_ms')}, p95_ms={summary.get('p95_ms')})" if summary else "")
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
