from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import unittest


REPO = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts" / "check_approximation_budget.py"
SPEC = importlib.util.spec_from_file_location("check_approximation_budget", MODULE_PATH)
assert SPEC and SPEC.loader
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

    def test_valid_fixture_case_passes(self) -> None:
        MOD.check_case(self.load_case())

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
