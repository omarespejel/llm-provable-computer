from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import unittest


REPO = pathlib.Path(__file__).resolve().parents[3]
MODULE_PATH = REPO / "scripts" / "reference" / "run_reference_decode.py"
SPEC = importlib.util.spec_from_file_location("run_reference_decode", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load reference decode module from {MODULE_PATH}")
MOD = importlib.util.module_from_spec(SPEC)
sys.modules["run_reference_decode"] = MOD
SPEC.loader.exec_module(MOD)


class ReferenceDecodeTests(unittest.TestCase):
    def load_fixture(self, name: str) -> dict:
        return MOD.load_json(REPO / "tests" / "fixtures" / "reference_cases" / name)

    def test_fixture_embedded_expected_comparison_passes(self) -> None:
        fixture = self.load_fixture("toy_reference_case.json")
        report = MOD.build_report(fixture)
        MOD.check_report(fixture, report)
        self.assertEqual(report, fixture["expected_comparison"])

    def test_top_k_comes_from_fixture(self) -> None:
        fixture = self.load_fixture("toy_reference_case_topk3.json")
        report = MOD.build_report(fixture)
        MOD.check_report(fixture, report)
        self.assertEqual(report["reference"]["topk"], [1, 0, 2])
        self.assertEqual(report["candidate"]["topk"], [1, 0, 2])
        self.assertEqual(report["metrics"]["topk_overlap"], 3)

    def test_check_report_rejects_tampered_expected_comparison(self) -> None:
        fixture = copy.deepcopy(self.load_fixture("toy_reference_case.json"))
        report = MOD.build_report(fixture)
        fixture["expected_comparison"]["metrics"]["max_logit_error"] = 0.25
        with self.assertRaisesRegex(ValueError, "did not match expected_comparison"):
            MOD.check_report(fixture, report)

    def test_rejects_bool_in_numeric_fields(self) -> None:
        fixture = self.load_fixture("toy_reference_case.json")
        fixture = copy.deepcopy(fixture)
        fixture["reference_decode"]["context_scale"] = True
        with self.assertRaisesRegex(ValueError, "context_scale must be numeric"):
            MOD.build_report(fixture)

        fixture = self.load_fixture("toy_reference_case.json")
        fixture = copy.deepcopy(fixture)
        fixture["reference_decode"]["context_tokens"] = [2, True, 1]
        with self.assertRaisesRegex(
            ValueError, r"context_tokens\[1\] must be an integer"
        ):
            MOD.build_report(fixture)

    def test_rejects_length_mismatch(self) -> None:
        fixture = self.load_fixture("toy_reference_case.json")
        fixture = copy.deepcopy(fixture)
        fixture["candidate"]["logits"] = [0.95, 0.65]
        with self.assertRaisesRegex(ValueError, "length mismatch"):
            MOD.build_report(fixture)


if __name__ == "__main__":
    unittest.main()
