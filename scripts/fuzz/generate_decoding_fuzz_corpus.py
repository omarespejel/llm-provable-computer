#!/usr/bin/env python3
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "fuzz" / "corpus"


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    phase12_path = CORPUS / "phase12_decoding_manifest" / "valid_phase12.json"
    phase14_path = CORPUS / "phase14_decoding_manifest" / "valid_phase14.json"
    artifact_path = CORPUS / "phase12_shared_lookup_artifact" / "valid_artifact.json"

    phase12_path.parent.mkdir(parents=True, exist_ok=True)
    phase14_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    run(
        "cargo",
        "+nightly-2025-07-14",
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
        "+nightly-2025-07-14",
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
    phase12_path.write_text(json.dumps(phase12, sort_keys=True, separators=(",", ":")) + "\n")

    phase14 = json.loads(phase14_path.read_text())
    phase14_path.write_text(json.dumps(phase14, sort_keys=True, separators=(",", ":")) + "\n")

    lookup_artifacts = phase12.get("shared_lookup_artifacts", [])
    if not lookup_artifacts:
        raise SystemExit("phase12 corpus generation did not produce shared lookup artifacts")

    artifact_input = {
        "layout": phase12["layout"],
        "expected_layout_commitment": lookup_artifacts[0]["layout_commitment"],
        "artifact": lookup_artifacts[0],
    }
    artifact_path.write_text(json.dumps(artifact_input, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
