from __future__ import annotations

import copy
import io
import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


REPO = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts" / "check_approximation_budget.py"
SPEC = importlib.util.spec_from_file_location("check_approximation_budget", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load approximation budget module from {MODULE_PATH}")
MOD = importlib.util.module_from_spec(SPEC)
sys.modules["check_approximation_budget"] = MOD
SPEC.loader.exec_module(MOD)


class ApproximationBudgetTests(unittest.TestCase):
    def load_case(self) -> dict:
        payload = MOD.load_json(
            REPO
            / "tests"
            / "fixtures"
            / "reference_cases"
            / "toy_approximation_budget_bundle.json"
        )
        return copy.deepcopy(payload["cases"][0])

    def load_negative_cases(self) -> list[dict]:
        payload = MOD.load_json(
            REPO
            / "tests"
            / "fixtures"
            / "reference_cases"
            / "toy_approximation_budget_negative_bundle.json"
        )
        return copy.deepcopy(payload["cases"])

    def test_valid_fixture_case_passes(self) -> None:
        MOD.check_case(self.load_case())

    def test_main_rejects_non_object_json_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bundle.json"
            path.write_text("[]", encoding="utf-8")
            with (
                mock.patch.object(sys, "argv", ["check_approximation_budget.py", str(path)]),
                mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
            ):
                self.assertEqual(MOD.main(), 1)
                self.assertIn("budget JSON must be an object", stderr.getvalue())

    def test_negative_fixture_cases_fail_closed(self) -> None:
        cases = self.load_negative_cases()
        self.assertGreaterEqual(len(cases), 3)
        for case in cases:
            with self.subTest(case_id=case.get("case_id", "<missing>")):
                with self.assertRaises(ValueError):
                    MOD.check_case(case)

    def test_rejects_bool_as_number(self) -> None:
        case = self.load_case()
        case["evidence"]["max_logit_error"] = True
        with self.assertRaisesRegex(ValueError, "max_logit_error must be numeric"):
            MOD.check_case(case)

    def test_rejects_non_finite_number(self) -> None:
        case = self.load_case()
        case["evidence"]["kl_divergence"] = float("nan")
        with self.assertRaisesRegex(ValueError, "kl_divergence must be finite"):
            MOD.check_case(case)

    def test_rejects_budget_overrun(self) -> None:
        case = self.load_case()
        case["evidence"]["max_logit_error"] = 0.2
        with self.assertRaisesRegex(ValueError, "exceeds budget"):
            MOD.check_case(case)

    def test_rejects_missing_token_flips_when_budget_requires_it(self) -> None:
        case = self.load_case()
        del case["evidence"]["token_flips"]
        with self.assertRaisesRegex(ValueError, "token_flips must be an integer"):
            MOD.check_case(case)


if __name__ == "__main__":
    unittest.main()
