from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "generate_bad_phase37_artifacts.py"
FIXTURE = ROOT / "tools" / "reference_verifier" / "fixtures" / "phase37-reference-receipt.json"
REFERENCE_VERIFIER = ROOT / "tools" / "reference_verifier" / "reference_verifier.py"

SPEC = importlib.util.spec_from_file_location("reference_verifier", REFERENCE_VERIFIER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load reference verifier from {REFERENCE_VERIFIER}")
REF = importlib.util.module_from_spec(SPEC)
sys.modules["reference_verifier"] = REF
SPEC.loader.exec_module(REF)


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pycache_dirs() -> list[pathlib.Path]:
    return [
        path
        for root in (ROOT / "scripts", ROOT / "tools")
        for path in root.glob("**/__pycache__")
        if path.is_dir()
    ]


def run_generator(output_dir: pathlib.Path) -> pathlib.Path:
    completed = subprocess.run(
        [sys.executable, "-B", str(GENERATOR), str(FIXTURE), str(output_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    return pathlib.Path(completed.stdout.strip())


class Phase37AdversarialMutationGeneratorTests(unittest.TestCase):
    def test_manifest_and_file_names_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = pathlib.Path(tempdir)
            first_manifest = run_generator(temp / "first")
            second_manifest = run_generator(temp / "second")
            first = load_json(first_manifest)
            second = load_json(second_manifest)

            expected_names = [
                "flip_recursive_verification_claim",
                "flip_cryptographic_compression_claim",
                "flip_source_binding_flag",
                "uppercase_phase33_commitment",
                "remove_phase30_source_chain_commitment",
                "add_unknown_field",
                "zero_total_steps",
                "overflow_total_steps",
                "tamper_final_commitment",
                "drift_source_chain_recommitted_boundary_probe",
            ]
            self.assertEqual(first["schema"], "phase37-adversarial-mutation-manifest-v1")
            self.assertEqual(first["mutation_count"], len(expected_names))
            self.assertEqual(
                first["source_receipt"]["path"],
                "tools/reference_verifier/fixtures/phase37-reference-receipt.json",
            )
            self.assertEqual(first["source_receipt"], second["source_receipt"])
            self.assertNotIn("output_dir", first)
            self.assertEqual([item["name"] for item in first["mutations"]], expected_names)
            self.assertEqual([item["name"] for item in second["mutations"]], expected_names)
            self.assertEqual(
                [item["file_name"] for item in first["mutations"]],
                [item["file_name"] for item in second["mutations"]],
            )

    def test_generated_artifacts_match_expected_reference_verifier_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = pathlib.Path(tempdir) / "mutations"
            manifest = load_json(run_generator(output_dir))
            by_name = {item["name"]: item for item in manifest["mutations"]}

            for item in manifest["mutations"]:
                artifact = load_json(output_dir / item["file_name"])
                if item["expected_reference_verifier"] == "fail":
                    with self.assertRaisesRegex(REF.ReferenceVerifierError, re.escape(item["actual_error"][:40])):
                        REF.verify_phase37_receipt(artifact)
                else:
                    REF.verify_phase37_receipt(artifact)

            recursive = load_json(output_dir / by_name["flip_recursive_verification_claim"]["file_name"])
            self.assertTrue(recursive["recursive_verification_claimed"])
            self.assertEqual(
                recursive["recursive_artifact_chain_harness_receipt_commitment"],
                REF.commit_phase37_receipt(recursive),
            )

            uppercased = load_json(output_dir / by_name["uppercase_phase33_commitment"]["file_name"])
            self.assertTrue(uppercased["phase33_recursive_public_inputs_commitment"].isupper())

            tampered = load_json(output_dir / by_name["tamper_final_commitment"]["file_name"])
            self.assertEqual(tampered["recursive_artifact_chain_harness_receipt_commitment"], "0" * 64)

            boundary_probe = load_json(
                output_dir / by_name["drift_source_chain_recommitted_boundary_probe"]["file_name"]
            )
            self.assertEqual(boundary_probe["phase30_source_chain_commitment"], "1" * 64)
            self.assertEqual(
                boundary_probe["recursive_artifact_chain_harness_receipt_commitment"],
                REF.commit_phase37_receipt(boundary_probe),
            )
            self.assertEqual(
                by_name["drift_source_chain_recommitted_boundary_probe"]["actual_reference_verifier"],
                "pass_reference_only",
            )

    def test_generator_does_not_write_python_cache_files(self) -> None:
        for cache in pycache_dirs():
            shutil.rmtree(cache)
        with tempfile.TemporaryDirectory() as tempdir:
            run_generator(pathlib.Path(tempdir) / "mutations")
        self.assertEqual(pycache_dirs(), [])

    def test_generator_rejects_populated_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_dir = pathlib.Path(tempdir) / "mutations"
            output_dir.mkdir()
            (output_dir / "stale.json").write_text("{}", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-B", str(GENERATOR), str(FIXTURE), str(output_dir)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("output directory must be empty", completed.stderr)


if __name__ == "__main__":
    unittest.main()
