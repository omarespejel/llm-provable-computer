from __future__ import annotations

import pathlib
import re
import unittest


REPO = pathlib.Path(__file__).resolve().parents[2]
MERGE_GATE = REPO / "scripts" / "local_merge_gate.sh"


class LocalMergeGateWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = MERGE_GATE.read_text(encoding="utf-8")

    def test_paper_preflight_surface_is_conditionally_wired(self) -> None:
        self.assertIn("changed_path_is_paper_preflight_surface()", self.script)
        self.assertIn('changed_path_has_prefix "docs/paper/"', self.script)
        self.assertIn('changed_path_has_prefix "docs/engineering/paper2-claim-evidence.yml"', self.script)
        self.assertIn('changed_path_has_prefix "docs/engineering/paper3-claim-evidence.yml"', self.script)
        self.assertIn("run_paper_preflight_if_needed()", self.script)
        self.assertIn("run_logged paper-preflight bash scripts/run_paper_preflight_suite.sh", self.script)
        self.assertGreaterEqual(len(re.findall(r"run_paper_preflight_if_needed", self.script)), 4)

    def test_approximation_budget_surface_is_conditionally_wired(self) -> None:
        self.assertIn("changed_path_is_approximation_budget_surface()", self.script)
        self.assertIn('changed_path_has_prefix "docs/engineering/approximation-budget.md"', self.script)
        self.assertIn('changed_path_has_prefix "scripts/check_approximation_budget.py"', self.script)
        self.assertIn("run_approximation_budget_if_needed()", self.script)
        self.assertIn(
            "run_logged approximation-budget bash scripts/run_approximation_budget_suite.sh",
            self.script,
        )
        self.assertGreaterEqual(
            len(re.findall(r"run_approximation_budget_if_needed", self.script)),
            4,
        )


if __name__ == "__main__":
    unittest.main()
