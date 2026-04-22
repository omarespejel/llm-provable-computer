#!/usr/bin/env python3
import argparse
import hashlib
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
PHASE113_SOURCE_FIXTURE = pathlib.Path(
    "fuzz/corpus/phase113_richer_gemma_window_family/source_phase113.json"
)
PHASE113_SOURCE_SHA256 = (
    "bcd08bdd5ca6fa0626d15c64fba18a084bc757cd3cd706484500873648c7a189"
)


def env_flag_is_true(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def normalized_toolchain(value: str) -> str:
    return value.lstrip("+")


def load_rust_toolchain() -> str:
    in_ci = env_flag_is_true("CI") or env_flag_is_true("GITHUB_ACTIONS")
    env_toolchain = os.environ.get("FUZZ_RUST_TOOLCHAIN")
    if env_toolchain and not in_ci:
        return normalized_toolchain(env_toolchain)
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
    return normalized_toolchain(channel)


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
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            f"command failed with exit code {error.returncode}: {' '.join(args)}"
        ) from error


def write_json(path: pathlib.Path, value: object) -> None:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(serialized)
    if path.stat().st_size == 0:
        raise SystemExit(f"generated empty fuzz corpus file: {path}")
    json.loads(path.read_text())


def phase29_update_usize(hasher, value: int) -> None:
    hasher.update(int(value).to_bytes(16, byteorder="little", signed=False))


def phase29_update_bool(hasher, value: bool) -> None:
    hasher.update(bytes([1 if value else 0]))


def phase29_update_len_prefixed(hasher, value: str) -> None:
    encoded = value.encode()
    phase29_update_usize(hasher, len(encoded))
    hasher.update(encoded)


def commit_phase29_contract(contract: dict[str, object]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, "phase29-contract")
    for field in (
        "proof_backend",
        "contract_version",
        "semantic_scope",
        "phase28_artifact_version",
        "phase28_semantic_scope",
        "phase28_proof_backend_version",
        "statement_version",
        "required_recursion_posture",
    ):
        value = contract[field]
        if not isinstance(value, str):
            raise SystemExit(f"Phase 29 `{field}` must be a string")
        phase29_update_len_prefixed(hasher, value)
    for field in ("recursive_verification_claimed", "cryptographic_compression_claimed"):
        value = contract[field]
        if not isinstance(value, bool):
            raise SystemExit(f"Phase 29 `{field}` must be a bool")
        phase29_update_bool(hasher, value)
    for field in (
        "phase28_bounded_aggregation_arity",
        "phase28_member_count",
        "phase28_member_summaries",
        "phase28_nested_members",
        "total_phase26_members",
        "total_phase25_members",
        "max_nested_chain_arity",
        "max_nested_fold_arity",
        "total_matrices",
        "total_layouts",
        "total_rollups",
        "total_segments",
        "total_steps",
        "lookup_delta_entries",
        "max_lookup_frontier_entries",
    ):
        value = contract[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise SystemExit(f"Phase 29 `{field}` must be a non-negative integer")
        phase29_update_usize(hasher, value)
    for field in (
        "source_template_commitment",
        "global_start_state_commitment",
        "global_end_state_commitment",
        "aggregation_template_commitment",
        "aggregated_chained_folded_interval_accumulator_commitment",
    ):
        value = contract[field]
        if not isinstance(value, str):
            raise SystemExit(f"Phase 29 `{field}` must be a string")
        phase29_update_len_prefixed(hasher, value)
    return hasher.hexdigest()


def phase29_contract_for_phase30(phase30: dict[str, object]) -> dict[str, object]:
    total_steps = phase30.get("total_steps")
    start_commitment = phase30.get("chain_start_boundary_commitment")
    end_commitment = phase30.get("chain_end_boundary_commitment")
    proof_backend_version = phase30.get("proof_backend_version")
    statement_version = phase30.get("statement_version")
    if not isinstance(total_steps, int) or total_steps <= 0:
        raise SystemExit("Phase 30 seed must declare a positive integer total_steps")
    for label, value in (
        ("chain_start_boundary_commitment", start_commitment),
        ("chain_end_boundary_commitment", end_commitment),
        ("proof_backend_version", proof_backend_version),
        ("statement_version", statement_version),
    ):
        if not isinstance(value, str) or not value:
            raise SystemExit(f"Phase 30 seed is missing `{label}`")

    contract: dict[str, object] = {
        "proof_backend": "stwo",
        "contract_version": "stwo-phase29-recursive-compression-input-contract-v1",
        "semantic_scope": "stwo_phase29_recursive_compression_input_contract",
        "phase28_artifact_version": (
            "stwo-phase28-aggregated-chained-folded-intervalized-"
            "decoding-state-relation-v1"
        ),
        "phase28_semantic_scope": (
            "stwo_execution_parameterized_aggregated_chained_folded_intervalized_"
            "proof_carrying_decoding_state_relation"
        ),
        "phase28_proof_backend_version": proof_backend_version,
        "statement_version": statement_version,
        "required_recursion_posture": "pre-recursive-proof-carrying-aggregation",
        "recursive_verification_claimed": False,
        "cryptographic_compression_claimed": False,
        "phase28_bounded_aggregation_arity": 2,
        "phase28_member_count": 2,
        "phase28_member_summaries": 2,
        "phase28_nested_members": 2,
        "total_phase26_members": 4,
        "total_phase25_members": 8,
        "max_nested_chain_arity": 2,
        "max_nested_fold_arity": 2,
        "total_matrices": 16,
        "total_layouts": 16,
        "total_rollups": 8,
        "total_segments": 8,
        "total_steps": total_steps,
        "lookup_delta_entries": 12,
        "max_lookup_frontier_entries": 4,
        "source_template_commitment": "a" * 64,
        "global_start_state_commitment": start_commitment,
        "global_end_state_commitment": end_commitment,
        "aggregation_template_commitment": "b" * 64,
        "aggregated_chained_folded_interval_accumulator_commitment": "c" * 64,
        "input_contract_commitment": "",
    }
    contract["input_contract_commitment"] = commit_phase29_contract(contract)
    return contract


def load_phase113_fixture(root: pathlib.Path = ROOT) -> dict[str, object]:
    phase113_source = root / PHASE113_SOURCE_FIXTURE
    if not phase113_source.exists():
        raise FileNotFoundError(
            f"missing phase113 fuzz-corpus source fixture: {phase113_source}"
        )
    try:
        phase113_bytes = phase113_source.read_bytes()
    except OSError as exc:
        raise OSError(
            f"failed to read phase113 fuzz-corpus source fixture {phase113_source}: {exc}"
        ) from exc
    fixture_sha256 = hashlib.sha256(phase113_bytes).hexdigest()
    if fixture_sha256 != PHASE113_SOURCE_SHA256:
        raise ValueError(
            "phase113 fuzz-corpus source fixture digest mismatch: "
            f"expected {PHASE113_SOURCE_SHA256}, got {fixture_sha256} "
            f"for {phase113_source}"
        )
    try:
        phase113_payload = json.loads(phase113_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"phase113 fuzz-corpus source fixture is not valid UTF-8: {phase113_source}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"phase113 fuzz-corpus source fixture is not valid JSON: {phase113_source}: {exc}"
        ) from exc
    if not isinstance(phase113_payload, dict):
        raise TypeError("phase113 fuzz-corpus source fixture must decode to a JSON object")
    return phase113_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate curated fuzz corpus inputs for decoding-related targets."
    )
    parser.add_argument(
        "--output-root",
        type=pathlib.Path,
        default=CORPUS,
        help="Corpus root directory to populate. Defaults to fuzz/corpus.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    corpus_root = args.output_root.resolve()

    phase12_path = corpus_root / "phase12_decoding_manifest" / "valid_phase12.json"
    phase14_path = corpus_root / "phase14_decoding_manifest" / "valid_phase14.json"
    artifact_path = corpus_root / "phase12_shared_lookup_artifact" / "valid_artifact.json"
    phase29_path = (
        corpus_root / "phase29_recursive_compression_input_contract" / "valid_phase29.json"
    )
    phase30_path = (
        corpus_root / "phase30_decoding_step_proof_envelope_manifest" / "valid_phase30.json"
    )
    support_root = corpus_root / "_support"
    phase30_raw_path = support_root / "phase30_raw.json"
    phase31_path = support_root / "phase31_decode_boundary_manifest.json"
    phase32_path = support_root / "phase32_statement_contract.json"
    phase33_path = support_root / "phase33_public_input_manifest.json"
    phase34_path = support_root / "phase34_shared_lookup_manifest.json"
    phase35_path = (
        corpus_root / "phase35_recursive_compression_target_manifest" / "valid_phase35.json"
    )
    phase36_path = (
        corpus_root / "phase36_recursive_verifier_harness_receipt" / "valid_phase36.json"
    )
    phase37_path = (
        corpus_root / "phase37_recursive_artifact_chain_harness_receipt" / "valid_phase37.json"
    )

    phase12_path.parent.mkdir(parents=True, exist_ok=True)
    phase14_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    phase29_path.parent.mkdir(parents=True, exist_ok=True)
    phase30_path.parent.mkdir(parents=True, exist_ok=True)
    support_root.mkdir(parents=True, exist_ok=True)
    phase35_path.parent.mkdir(parents=True, exist_ok=True)
    phase36_path.parent.mkdir(parents=True, exist_ok=True)
    phase37_path.parent.mkdir(parents=True, exist_ok=True)

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
    steps = phase12.get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise SystemExit("phase12 corpus generation did not produce decoding steps")
    if "layout" not in phase12:
        raise SystemExit("phase12 corpus generation did not produce layout")
    first_step = steps[0]
    if not isinstance(first_step, dict):
        raise SystemExit(
            f"phase12 corpus generation produced a non-object first step: {first_step!r}"
        )
    referenced_commitment = first_step.get("shared_lookup_artifact_commitment")
    if not isinstance(referenced_commitment, str) or not referenced_commitment:
        raise SystemExit(
            "phase12 corpus generation first step is missing shared_lookup_artifact_commitment"
        )
    matching_artifacts = [
        artifact
        for artifact in lookup_artifacts
        if isinstance(artifact, dict)
        and artifact.get("artifact_commitment") == referenced_commitment
        and "layout_commitment" in artifact
    ]
    if len(matching_artifacts) != 1:
        raise SystemExit(
            "phase12 corpus generation must produce exactly one shared lookup artifact "
            f"matching first step commitment {referenced_commitment!r}, found "
            f"{len(matching_artifacts)} in {lookup_artifacts!r}"
        )
    first_artifact = matching_artifacts[0]

    artifact_input = {
        "layout": phase12["layout"],
        "expected_layout_commitment": first_artifact["layout_commitment"],
        "artifact": first_artifact,
    }
    write_json(artifact_path, artifact_input)

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
        "prepare-stwo-decoding-step-envelope-manifest",
        "--proof",
        str(phase12_path),
        "-o",
        str(phase30_path),
    )
    phase30 = json.loads(phase30_path.read_text())
    write_json(phase30_raw_path, phase30)
    phase30_input = {
        "manifest": phase30,
        "chain": phase12,
    }
    write_json(phase30_path, phase30_input)

    phase29 = phase29_contract_for_phase30(phase30)
    write_json(phase29_path, phase29)
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
        "verify-stwo-recursive-compression-input-contract",
        "--input",
        str(phase29_path),
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
        "prepare-stwo-recursive-compression-decode-boundary-manifest",
        "--contract",
        str(phase29_path),
        "--manifest",
        str(phase30_raw_path),
        "-o",
        str(phase31_path),
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
        "prepare-stwo-recursive-compression-statement-contract",
        "--manifest",
        str(phase31_path),
        "-o",
        str(phase32_path),
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
        "prepare-stwo-recursive-compression-public-input-manifest",
        "--contract",
        str(phase32_path),
        "-o",
        str(phase33_path),
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
        "prepare-stwo-recursive-compression-shared-lookup-manifest",
        "--public-inputs",
        str(phase33_path),
        "--envelopes",
        str(phase30_raw_path),
        "-o",
        str(phase34_path),
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
        "prepare-stwo-recursive-compression-target-manifest",
        "--statement-contract",
        str(phase32_path),
        "--public-inputs",
        str(phase33_path),
        "--shared-lookup",
        str(phase34_path),
        "-o",
        str(phase35_path),
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
        "prepare-stwo-recursive-verifier-harness-receipt",
        "--target",
        str(phase35_path),
        "--statement-contract",
        str(phase32_path),
        "--public-inputs",
        str(phase33_path),
        "--shared-lookup",
        str(phase34_path),
        "-o",
        str(phase36_path),
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
        "prepare-stwo-recursive-artifact-chain-harness-receipt",
        "--contract",
        str(phase29_path),
        "--manifest",
        str(phase30_raw_path),
        "-o",
        str(phase37_path),
    )
    for generated_path in (
        phase31_path,
        phase32_path,
        phase33_path,
        phase34_path,
        phase35_path,
        phase36_path,
        phase37_path,
    ):
        write_json(generated_path, json.loads(generated_path.read_text()))
    phase113_path = (
        corpus_root / "phase113_richer_gemma_window_family" / "valid_phase113.json"
    )
    phase113_path.parent.mkdir(parents=True, exist_ok=True)
    phase113_payload = load_phase113_fixture()
    write_json(phase113_path, phase113_payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
