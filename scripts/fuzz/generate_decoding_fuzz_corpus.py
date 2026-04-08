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
    in_ci = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))
    env_toolchain = os.environ.get("FUZZ_RUST_TOOLCHAIN")
    if env_toolchain and not in_ci:
        return env_toolchain
    try:
        with FUZZ_TOOLCHAIN_TOML.open("rb") as handle:
            config = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        if in_ci:
            raise SystemExit(
                f"failed to read required CI fuzz toolchain file {FUZZ_TOOLCHAIN_TOML}: {error}"
            ) from error
        print(
            f"warning: failed to read {FUZZ_TOOLCHAIN_TOML}: {error}; "
            f"falling back to {DEFAULT_RUST_TOOLCHAIN}",
            file=sys.stderr,
        )
        return DEFAULT_RUST_TOOLCHAIN
    channel = config.get("toolchain", {}).get("channel")
    if not isinstance(channel, str) or not channel:
        if in_ci:
            raise SystemExit(
                f"{FUZZ_TOOLCHAIN_TOML} is missing required toolchain.channel in CI"
            )
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
    if not isinstance(lookup_artifacts, list) or not lookup_artifacts:
        raise SystemExit("phase12 corpus generation did not produce shared lookup artifacts")
    if "layout" not in phase12:
        raise SystemExit("phase12 corpus generation did not produce layout")
    layout_artifacts = [
        artifact
        for artifact in lookup_artifacts
        if isinstance(artifact, dict) and "layout_commitment" in artifact
    ]
    if len(layout_artifacts) != 1:
        raise SystemExit(
            "phase12 corpus generation must produce exactly one shared lookup artifact "
            f"with layout_commitment, found {len(layout_artifacts)} in "
            f"{lookup_artifacts!r}"
        )
    first_artifact = layout_artifacts[0]

    artifact_input = {
        "layout": phase12["layout"],
        "expected_layout_commitment": first_artifact["layout_commitment"],
        "artifact": first_artifact,
    }
    write_json(artifact_path, artifact_input)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
