from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
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

FIXTURE = ROOT / "tools" / "reference_verifier" / "fixtures" / "phase37-reference-receipt.json"
EXPECTED_COMMITMENT = "3f9732d90f3d02a218f3ef3e03c0b3bd8ae5fed4b1fb5d2af82a927d0cc03425"


class Phase37ReferenceVerifierTests(unittest.TestCase):
    def load_fixture(self) -> dict:
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_reference_fixture_verifies_and_commitment_is_stable(self) -> None:
        receipt = self.load_fixture()
        self.assertEqual(
            MOD.commit_phase37_receipt(receipt),
            EXPECTED_COMMITMENT,
        )
        MOD.verify_phase37_receipt(receipt)

    def test_rejects_tampered_commitment(self) -> None:
        receipt = self.load_fixture()
        receipt["recursive_artifact_chain_harness_receipt_commitment"] = "0" * 64
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "commitment mismatch"):
            MOD.verify_phase37_receipt(receipt)

    def test_rejects_recursive_claim_flag(self) -> None:
        receipt = self.load_fixture()
        receipt["recursive_verification_claimed"] = True
        receipt["recursive_artifact_chain_harness_receipt_commitment"] = MOD.commit_phase37_receipt(receipt)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "recursive_verification_claimed"):
            MOD.verify_phase37_receipt(receipt)

    def test_rejects_uppercase_hash_even_when_recommitted(self) -> None:
        receipt = self.load_fixture()
        receipt["phase35_recursive_target_manifest_commitment"] = "A" * 64
        receipt["recursive_artifact_chain_harness_receipt_commitment"] = MOD.commit_phase37_receipt(receipt)
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "lowercase 64-character hex"):
            MOD.verify_phase37_receipt(receipt)

    def test_rejects_unknown_field(self) -> None:
        receipt = self.load_fixture()
        receipt["unexpected"] = True
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "unknown Phase 37 fields"):
            MOD.verify_phase37_receipt(receipt)

    def test_rejects_non_object_json_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(MOD.ReferenceVerifierError, "JSON root must be an object"):
                MOD.load_json_object(path)

    def test_missing_field_fails_before_commitment_check(self) -> None:
        receipt = self.load_fixture()
        del receipt["phase30_source_chain_commitment"]
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "missing Phase 37 fields"):
            MOD.verify_phase37_receipt(receipt)

    def test_commitment_changes_when_domain_field_changes(self) -> None:
        receipt = self.load_fixture()
        changed = copy.deepcopy(receipt)
        changed["phase30_source_chain_commitment"] = "1" * 64
        self.assertNotEqual(
            MOD.commit_phase37_receipt(receipt),
            MOD.commit_phase37_receipt(changed),
        )

    def test_rejects_total_steps_that_exceed_u128_encoding(self) -> None:
        receipt = self.load_fixture()
        receipt["total_steps"] = 2**128
        with self.assertRaisesRegex(MOD.ReferenceVerifierError, "exceeds 128-bit encoding"):
            MOD.verify_phase37_receipt(receipt)

    def test_deterministic_parser_mutation_corpus_rejects_invalid_receipts(self) -> None:
        mutations = {
            "wrong_backend_type": (
                lambda receipt: receipt.__setitem__("proof_backend", 7),
                "proof_backend must be a string",
            ),
            "boolean_total_steps": (
                lambda receipt: receipt.__setitem__("total_steps", True),
                "total_steps must be an integer",
            ),
            "zero_total_steps": (
                lambda receipt: receipt.__setitem__("total_steps", 0),
                "total_steps must be positive",
            ),
            "short_hash": (
                lambda receipt: receipt.__setitem__("phase29_input_contract_commitment", "abc"),
                "lowercase 64-character hex",
            ),
            "missing_hash": (
                lambda receipt: receipt.__delitem__("phase30_source_chain_commitment"),
                "missing Phase 37 fields",
            ),
            "unknown_field": (
                lambda receipt: receipt.__setitem__("extra_debug_field", "not-bound"),
                "unknown Phase 37 fields",
            ),
            "source_binding_false": (
                lambda receipt: receipt.__setitem__("source_binding_verified", False),
                "source_binding_verified",
            ),
            "commitment_drift": (
                lambda receipt: receipt.__setitem__("phase30_source_chain_commitment", "1" * 64),
                "commitment mismatch",
            ),
        }
        for name, (mutate, expected_error) in mutations.items():
            with self.subTest(name=name):
                receipt = self.load_fixture()
                mutate(receipt)
                with self.assertRaisesRegex(MOD.ReferenceVerifierError, expected_error):
                    MOD.verify_phase37_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
