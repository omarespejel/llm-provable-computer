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

    def _shell_function_body(self, fn_name: str) -> str:
        match = re.search(
            rf"^{re.escape(fn_name)}\(\) \{{(?P<body>.*?)^\}}",
            self.script,
            flags=re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, f"missing function: {fn_name}")
        return match.group("body")

    def _shell_call_site_count(self, fn_name: str) -> int:
        # Count invocation lines only; this intentionally excludes definitions.
        return len(re.findall(rf"(?m)^\s*{re.escape(fn_name)}\s*$", self.script))

    def test_paper_preflight_surface_is_conditionally_wired(self) -> None:
        self.assertIn("changed_path_is_paper_preflight_surface()", self.script)
        body = self._shell_function_body("changed_path_is_paper_preflight_surface")
        expected_triggers = [
            "docs/paper/",
            "docs/engineering/paper2-claim-evidence.yml",
            "docs/engineering/paper3-claim-evidence.yml",
            "docs/engineering/design/phase29-recursive-compression-input-contract-spec.md",
            "docs/engineering/paper3-composition-prototype.md",
            "docs/engineering/reproducibility.md",
            "src/",
            "spec/",
            "tools/reference_verifier/",
            "fuzz/fuzz_targets/",
            "scripts/generate_bad_phase37_artifacts.py",
            "scripts/run_formal_contract_suite.sh",
            "scripts/run_fuzz_smoke_suite.sh",
            "scripts/run_mutation_survivor_tracking_suite.sh",
            "scripts/run_phase37_mutation_generator_suite.sh",
            "scripts/run_reference_verifier_suite.sh",
            "scripts/paper/",
            "scripts/run_paper_preflight_suite.sh",
            "scripts/local_merge_gate.sh",
        ]
        for trigger in expected_triggers:
            with self.subTest(trigger=trigger):
                self.assertIn(f'changed_path_has_prefix "{trigger}"', body)
        self.assertNotIn('changed_path_has_prefix "docs/engineering/"', body)
        runner_body = self._shell_function_body("run_paper_preflight_if_needed")
        self.assertIn("if changed_path_is_paper_preflight_surface; then", runner_body)
        self.assertIn(
            "run_logged paper-preflight bash scripts/run_paper_preflight_suite.sh",
            runner_body,
        )
        self.assertGreaterEqual(
            self._shell_call_site_count("run_paper_preflight_if_needed"),
            3,
        )

    def test_approximation_budget_surface_is_conditionally_wired(self) -> None:
        self.assertIn("changed_path_is_approximation_budget_surface()", self.script)
        body = self._shell_function_body("changed_path_is_approximation_budget_surface")
        expected_triggers = [
            "docs/engineering/approximation-budget.md",
            "scripts/check_approximation_budget.py",
            "scripts/tests/test_check_approximation_budget.py",
            "scripts/run_approximation_budget_suite.sh",
            "tests/fixtures/reference_cases/toy_approximation_budget_bundle.json",
            "tests/fixtures/reference_cases/toy_approximation_budget_negative_bundle.json",
            "scripts/local_merge_gate.sh",
        ]
        for trigger in expected_triggers:
            with self.subTest(trigger=trigger):
                self.assertIn(f'changed_path_has_prefix "{trigger}"', body)
        runner_body = self._shell_function_body("run_approximation_budget_if_needed")
        self.assertIn(
            "if changed_path_is_approximation_budget_surface; then",
            runner_body,
        )
        self.assertIn(
            "run_logged approximation-budget bash scripts/run_approximation_budget_suite.sh",
            runner_body,
        )
        self.assertGreaterEqual(
            self._shell_call_site_count("run_approximation_budget_if_needed"),
            3,
        )


if __name__ == "__main__":
    unittest.main()
