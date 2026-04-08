#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "fuzz" / "corpus"
FUZZ_TOOLCHAIN_TOML = ROOT / "fuzz" / "rust-toolchain.toml"
RUN_TIMEOUT_SECONDS = 300
DEFAULT_RUST_TOOLCHAIN = "nightly-2025-07-14"


def load_rust_toolchain() -> str:
    env_toolchain = os.environ.get("FUZZ_RUST_TOOLCHAIN")
    if env_toolchain:
        return env_toolchain
    try:
        with FUZZ_TOOLCHAIN_TOML.open("rb") as handle:
            config = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        print(
            f"warning: failed to read {FUZZ_TOOLCHAIN_TOML}: {error}; "
            f"falling back to {DEFAULT_RUST_TOOLCHAIN}",
            file=sys.stderr,
        )
        return DEFAULT_RUST_TOOLCHAIN
    channel = config.get("toolchain", {}).get("channel")
    if not isinstance(channel, str) or not channel:
        print(
            f"warning: {FUZZ_TOOLCHAIN_TOML} is missing toolchain.channel; "
            f"falling back to {DEFAULT_RUST_TOOLCHAIN}",
            file=sys.stderr,
        )
        return DEFAULT_RUST_TOOLCHAIN
    return channel


RUST_TOOLCHAIN = load_rust_toolchain()


def run(*args: str) -> None:
    try:
        subprocess.run(
            args,
            cwd=ROOT,
            check=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise SystemExit(
            f"command timed out after {RUN_TIMEOUT_SECONDS}s: {' '.join(args)}"
        ) from error


def write_json(path: pathlib.Path, value: object) -> None:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(serialized)
    if path.stat().st_size == 0:
        raise SystemExit(f"generated empty fuzz corpus file: {path}")
    json.loads(path.read_text())


def main() -> int:
    phase12_path = CORPUS / "phase12_decoding_manifest" / "valid_phase12.json"
    phase14_path = CORPUS / "phase14_decoding_manifest" / "valid_phase14.json"
    artifact_path = CORPUS / "phase12_shared_lookup_artifact" / "valid_artifact.json"

    phase12_path.parent.mkdir(parents=True, exist_ok=True)
    phase14_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    run(
        "cargo",
        f"+{RUST_TOOLCHAIN}",
        "run",
        "--quiet",
        "--features",
        "stwo-backend",
        "--bin",
        "tvm",
        "--",
        "prove-stwo-decoding-family-demo",
        "--output",
        str(phase12_path),
    )
    run(
        "cargo",
        f"+{RUST_TOOLCHAIN}",
        "run",
        "--quiet",
        "--features",
        "stwo-backend",
        "--bin",
        "tvm",
        "--",
        "prove-stwo-decoding-chunked-history-demo",
        "--output",
        str(phase14_path),
    )

    phase12 = json.loads(phase12_path.read_text())
    write_json(phase12_path, phase12)

    phase14 = json.loads(phase14_path.read_text())
    write_json(phase14_path, phase14)

    lookup_artifacts = phase12.get("shared_lookup_artifacts", [])
    if not lookup_artifacts:
        raise SystemExit("phase12 corpus generation did not produce shared lookup artifacts")
    if "layout" not in phase12:
        raise SystemExit("phase12 corpus generation did not produce layout")

    artifact_input = {
        "layout": phase12["layout"],
        "expected_layout_commitment": lookup_artifacts[0]["layout_commitment"],
        "artifact": lookup_artifacts[0],
    }
    write_json(artifact_path, artifact_input)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
