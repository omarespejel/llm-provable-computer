#!/usr/bin/env python3
"""Generate deterministic adversarial Phase 37 receipt artifacts.

The generator targets the Phase 37 reference receipt surface. Most emitted
artifacts are expected to fail the independent reference verifier. One artifact
is intentionally a boundary probe: it drifts a source commitment and recomputes
the Phase 37 receipt commitment, so the standalone reference verifier should
pass it while source-bound recomputation must catch it.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
from collections.abc import Callable
from typing import Any

sys.dont_write_bytecode = True

ROOT = pathlib.Path(__file__).resolve().parents[1]
REFERENCE_VERIFIER_PATH = ROOT / "tools" / "reference_verifier" / "reference_verifier.py"
MANIFEST_NAME = "phase37-adversarial-manifest.json"
GENERATOR_VERSION = "phase37-adversarial-mutation-generator-v1"


class MutationGeneratorError(RuntimeError):
    pass


def _load_reference_verifier() -> Any:
    spec = importlib.util.spec_from_file_location("phase37_reference_verifier", REFERENCE_VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise MutationGeneratorError(f"failed to load reference verifier from {REFERENCE_VERIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["phase37_reference_verifier"] = module
    spec.loader.exec_module(module)
    return module


REF = _load_reference_verifier()


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_file(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def manifest_display_path(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_receipt(path: pathlib.Path) -> dict[str, Any]:
    receipt = REF.load_json_object(path)
    REF.verify_phase37_receipt(receipt)
    return receipt


def write_json(path: pathlib.Path, value: Any) -> None:
    path.write_text(stable_json(value), encoding="utf-8")


def recommit(receipt: dict[str, Any]) -> None:
    receipt["recursive_artifact_chain_harness_receipt_commitment"] = REF.commit_phase37_receipt(
        receipt
    )


def flip_recursive_claim(receipt: dict[str, Any]) -> None:
    receipt["recursive_verification_claimed"] = True
    recommit(receipt)


def flip_compression_claim(receipt: dict[str, Any]) -> None:
    receipt["cryptographic_compression_claimed"] = True
    recommit(receipt)


def flip_source_binding(receipt: dict[str, Any]) -> None:
    receipt["source_binding_verified"] = False
    recommit(receipt)


def uppercase_phase33_commitment(receipt: dict[str, Any]) -> None:
    receipt["phase33_recursive_public_inputs_commitment"] = receipt[
        "phase33_recursive_public_inputs_commitment"
    ].upper()
    recommit(receipt)


def remove_phase30_source_chain(receipt: dict[str, Any]) -> None:
    del receipt["phase30_source_chain_commitment"]


def add_unknown_field(receipt: dict[str, Any]) -> None:
    receipt["unexpected_phase37_debug_field"] = {
        "reason": "unknown fields must not survive artifact parsing"
    }


def zero_total_steps(receipt: dict[str, Any]) -> None:
    receipt["total_steps"] = 0


def overflow_total_steps(receipt: dict[str, Any]) -> None:
    receipt["total_steps"] = 2**128


def tamper_final_commitment(receipt: dict[str, Any]) -> None:
    receipt["recursive_artifact_chain_harness_receipt_commitment"] = "0" * 64


def drift_source_chain_recommitted(receipt: dict[str, Any]) -> None:
    receipt["phase30_source_chain_commitment"] = "1" * 64
    recommit(receipt)


MutationFn = Callable[[dict[str, Any]], None]

MUTATIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "flip_recursive_verification_claim",
        "description": "Recommit a receipt that falsely claims recursive verification.",
        "changed_paths": ["recursive_verification_claimed", "recursive_artifact_chain_harness_receipt_commitment"],
        "expected_reference_verifier": "fail",
        "expected_error": "recursive_verification_claimed",
        "apply": flip_recursive_claim,
    },
    {
        "name": "flip_cryptographic_compression_claim",
        "description": "Recommit a receipt that falsely claims cryptographic compression.",
        "changed_paths": ["cryptographic_compression_claimed", "recursive_artifact_chain_harness_receipt_commitment"],
        "expected_reference_verifier": "fail",
        "expected_error": "cryptographic_compression_claimed",
        "apply": flip_compression_claim,
    },
    {
        "name": "flip_source_binding_flag",
        "description": "Recommit a receipt with the source-binding verification flag disabled.",
        "changed_paths": ["source_binding_verified", "recursive_artifact_chain_harness_receipt_commitment"],
        "expected_reference_verifier": "fail",
        "expected_error": "source_binding_verified",
        "apply": flip_source_binding,
    },
    {
        "name": "uppercase_phase33_commitment",
        "description": "Recommit a receipt whose Phase 33 commitment is uppercase hex.",
        "changed_paths": ["phase33_recursive_public_inputs_commitment", "recursive_artifact_chain_harness_receipt_commitment"],
        "expected_reference_verifier": "fail",
        "expected_error": "lowercase 64-character hex",
        "apply": uppercase_phase33_commitment,
    },
    {
        "name": "remove_phase30_source_chain_commitment",
        "description": "Remove a required source-chain commitment field.",
        "changed_paths": ["phase30_source_chain_commitment"],
        "expected_reference_verifier": "fail",
        "expected_error": "missing Phase 37 fields",
        "apply": remove_phase30_source_chain,
    },
    {
        "name": "add_unknown_field",
        "description": "Add an unknown field that must not survive strict parsing.",
        "changed_paths": ["unexpected_phase37_debug_field"],
        "expected_reference_verifier": "fail",
        "expected_error": "unknown Phase 37 fields",
        "apply": add_unknown_field,
    },
    {
        "name": "zero_total_steps",
        "description": "Set total_steps to zero.",
        "changed_paths": ["total_steps"],
        "expected_reference_verifier": "fail",
        "expected_error": "total_steps must be positive",
        "apply": zero_total_steps,
    },
    {
        "name": "overflow_total_steps",
        "description": "Set total_steps beyond the 128-bit transcript encoding range.",
        "changed_paths": ["total_steps"],
        "expected_reference_verifier": "fail",
        "expected_error": "exceeds 128-bit encoding",
        "apply": overflow_total_steps,
    },
    {
        "name": "tamper_final_commitment",
        "description": "Overwrite the final Phase 37 receipt commitment without updating transcript fields.",
        "changed_paths": ["recursive_artifact_chain_harness_receipt_commitment"],
        "expected_reference_verifier": "fail",
        "expected_error": "commitment mismatch",
        "apply": tamper_final_commitment,
    },
    {
        "name": "drift_source_chain_recommitted_boundary_probe",
        "description": "Drift a source commitment and recompute the Phase 37 receipt commitment; this should pass the standalone reference verifier and remain a source-recompute boundary probe.",
        "changed_paths": ["phase30_source_chain_commitment", "recursive_artifact_chain_harness_receipt_commitment"],
        "expected_reference_verifier": "pass_reference_only",
        "expected_error": "",
        "apply": drift_source_chain_recommitted,
    },
)


def evaluate_reference_verifier(receipt: dict[str, Any]) -> tuple[str, str]:
    try:
        REF.verify_phase37_receipt(receipt)
    except REF.ReferenceVerifierError as exc:
        return "fail", str(exc)
    return "pass_reference_only", ""


def mutation_file_name(index: int, name: str) -> str:
    return f"phase37_adversarial_{index:02d}_{name}.json"


def generate(receipt_path: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
    source = load_receipt(receipt_path)
    if output_dir.exists():
        if not output_dir.is_dir():
            raise MutationGeneratorError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise MutationGeneratorError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "schema": "phase37-adversarial-mutation-manifest-v1",
        "generator_version": GENERATOR_VERSION,
        "source_receipt": {
            "path": manifest_display_path(receipt_path),
            "sha256": sha256_file(receipt_path),
        },
        "mutation_count": len(MUTATIONS),
        "mutations": [],
    }

    for index, spec in enumerate(MUTATIONS, start=1):
        mutated = copy.deepcopy(source)
        apply = spec["apply"]
        apply(mutated)
        result, error = evaluate_reference_verifier(mutated)
        expected = str(spec["expected_reference_verifier"])
        if result != expected:
            raise MutationGeneratorError(
                f"mutation {spec['name']} expected reference verifier {expected}, got {result}: {error}"
            )
        expected_error = str(spec["expected_error"])
        if expected_error and expected_error not in error:
            raise MutationGeneratorError(
                f"mutation {spec['name']} expected error containing {expected_error!r}, got {error!r}"
            )

        file_name = mutation_file_name(index, str(spec["name"]))
        artifact_path = output_dir / file_name
        write_json(artifact_path, mutated)
        manifest["mutations"].append(
            {
                "name": spec["name"],
                "file_name": file_name,
                "sha256": sha256_file(artifact_path),
                "description": spec["description"],
                "changed_paths": spec["changed_paths"],
                "expected_reference_verifier": expected,
                "actual_reference_verifier": result,
                "actual_error": error,
            }
        )

    manifest_path = output_dir / MANIFEST_NAME
    write_json(manifest_path, manifest)
    return manifest_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=pathlib.Path, help="valid Phase 37 receipt JSON")
    parser.add_argument("output_dir", type=pathlib.Path, help="directory for generated artifacts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest_path = generate(args.receipt, args.output_dir)
    except (OSError, json.JSONDecodeError, MutationGeneratorError, REF.ReferenceVerifierError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
