from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "reference_verifier" / "reference_verifier.py"
SPEC = importlib.util.spec_from_file_location("reference_verifier", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load reference verifier from {MODULE_PATH}")
MOD = importlib.util.module_from_spec(SPEC)
sys.modules["reference_verifier"] = MOD
SPEC.loader.exec_module(MOD)

FIXTURE = ROOT / "tools" / "reference_verifier" / "fixtures" / "phase38-reference-composition.json"
PHASE30_SCHEMA = ROOT / "spec" / "stwo-phase30-decoding-step-envelope-manifest.schema.json"
PHASE37_SCHEMA = ROOT / "spec" / "stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json"
EXPECTED_COMPOSITION_COMMITMENT = "e44a6d3f001503d6eafe0e78a3a556ca5237c9124e10a1848d172d2c2e9e3c06"


class Phase38ReferenceVerifierTests(unittest.TestCase):
    def load_fixture(self) -> dict:
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def recompute(self, prototype: dict) -> dict:
        prototype = copy.deepcopy(prototype)
        for segment in prototype["segments"]:
            receipt = segment["phase37_receipt"]
            receipt["recursive_artifact_chain_harness_receipt_commitment"] = MOD.commit_phase37_receipt(
                receipt
            )
            segment["phase37_receipt_commitment"] = receipt[
                "recursive_artifact_chain_harness_receipt_commitment"
            ]
            segment["lookup_identity_commitment"] = MOD.commit_phase38_lookup_identity(
                segment["phase30_manifest"]
            )
        prototype["shared_lookup_identity_commitment"] = MOD.commit_phase38_shared_lookup_identity(
            prototype["segments"][0]
        )
        prototype["segment_list_commitment"] = MOD.commit_phase38_segment_list(prototype["segments"])
        prototype["composition_commitment"] = MOD.commit_phase38_composition_prototype(prototype)
        return prototype

    def test_reference_fixture_verifies_and_commitment_is_stable(self) -> None:
        prototype = self.load_fixture()
        self.assertEqual(MOD.commit_phase38_composition_prototype(prototype), EXPECTED_COMPOSITION_COMMITMENT)
        MOD.verify_phase38_composition(prototype)

    def test_cli_verifies_phase38_fixture(self) -> None:
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "verify-phase38", str(FIXTURE)],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("verify-phase38 PASS", result.stdout)

    def test_referenced_phase30_and_phase37_schemas_are_present(self) -> None:
        self.assertTrue(PHASE30_SCHEMA.is_file())
        self.assertTrue(PHASE37_SCHEMA.is_file())

    def test_rejects_boundary_gap_even_when_recommitted(self) -> None:
        prototype = self.load_fixture()
        segment = prototype["segments"][1]
        segment["chain_start_boundary_commitment"] = "0" * 64
        segment["phase30_manifest"]["chain_start_boundary_commitment"] = "0" * 64
        segment["phase30_manifest"]["envelopes"][0]["input_boundary_commitment"] = "0" * 64
        segment["phase37_receipt"]["chain_start_boundary_commitment"] = "0" * 64
        prototype = self.recompute(prototype)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "boundary gap"):
            MOD.verify_phase38_composition(prototype)

    def test_rejects_shared_lookup_identity_drift_even_when_recommitted(self) -> None:
        prototype = self.load_fixture()
        prototype["segments"][1]["phase30_manifest"]["layout"]["pair_width"] = 3
        prototype = self.recompute(prototype)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "shared lookup identity drift"):
            MOD.verify_phase38_composition(prototype)

    def test_rejects_source_chain_drift_even_when_recommitted(self) -> None:
        prototype = self.load_fixture()
        segment = prototype["segments"][1]
        segment["phase30_source_chain_commitment"] = "1" * 64
        segment["phase30_manifest"]["source_chain_commitment"] = "1" * 64
        segment["phase37_receipt"]["phase30_source_chain_commitment"] = "1" * 64
        for envelope in segment["phase30_manifest"]["envelopes"]:
            envelope["source_chain_commitment"] = "1" * 64
        prototype = self.recompute(prototype)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "source-chain identity drift"):
            MOD.verify_phase38_composition(prototype)

    def test_rejects_execution_template_drift_even_when_recommitted(self) -> None:
        prototype = self.load_fixture()
        segment = prototype["segments"][1]
        segment["source_template_commitment"] = "2" * 64
        segment["phase29_contract"]["source_template_commitment"] = "2" * 64
        segment["phase37_receipt"]["source_template_commitment"] = "2" * 64
        prototype = self.recompute(prototype)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "source template drift"):
            MOD.verify_phase38_composition(prototype)

    def test_rejects_wrong_segment_count(self) -> None:
        prototype = self.load_fixture()
        prototype["segment_count"] = 3
        prototype["composition_commitment"] = MOD.commit_phase38_composition_prototype(prototype)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "segment_count"):
            MOD.verify_phase38_composition(prototype)

    def test_rejects_wrong_package_count_delta(self) -> None:
        prototype = self.load_fixture()
        prototype["package_count_delta"] += 1
        prototype["composition_commitment"] = MOD.commit_phase38_composition_prototype(prototype)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "package_count_delta"):
            MOD.verify_phase38_composition(prototype)

    def test_rejects_recursive_and_compression_claim_flags(self) -> None:
        for flag in ("recursive_verification_claimed", "cryptographic_compression_claimed"):
            with self.subTest(flag=flag):
                prototype = self.load_fixture()
                prototype[flag] = True
                prototype["composition_commitment"] = MOD.commit_phase38_composition_prototype(prototype)
                with self.assertRaisesRegex(MOD.ReferenceVerifierError, flag):
                    MOD.verify_phase38_composition(prototype)

    def test_rejects_swapped_phase37_receipt_commitment(self) -> None:
        prototype = self.load_fixture()
        prototype["segments"][0]["phase37_receipt_commitment"] = prototype["segments"][1][
            "phase37_receipt_commitment"
        ]
        prototype["segment_list_commitment"] = MOD.commit_phase38_segment_list(prototype["segments"])
        prototype["composition_commitment"] = MOD.commit_phase38_composition_prototype(prototype)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "Phase 37 receipt commitment"):
            MOD.verify_phase38_composition(prototype)

    def test_rejects_reordered_segment_list(self) -> None:
        prototype = self.load_fixture()
        prototype["segments"] = list(reversed(prototype["segments"]))
        prototype["segment_list_commitment"] = MOD.commit_phase38_segment_list(prototype["segments"])
        prototype["composition_commitment"] = MOD.commit_phase38_composition_prototype(prototype)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "segment_index"):
            MOD.verify_phase38_composition(prototype)

    def test_rejects_non_object_json_root_for_phase38_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.json"
            path.write_text("[]", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "verify-phase38", str(path)],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("JSON root must be an object", result.stderr)


if __name__ == "__main__":
    unittest.main()
