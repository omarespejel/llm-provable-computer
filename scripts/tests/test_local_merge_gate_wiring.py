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

    def _run_mode_body(self, mode: str) -> str:
        markers = [
            ("smoke", 'if (( RUN_LOCAL )) && [[ "$RUN_MODE" == "smoke" ]]; then'),
            ("full", 'elif (( RUN_LOCAL )) && [[ "$RUN_MODE" == "full" ]]; then'),
            ("hardening", 'elif (( RUN_LOCAL )) && [[ "$RUN_MODE" == "hardening" ]]; then'),
            ("none", 'elif (( RUN_LOCAL )) && [[ "$RUN_MODE" == "none" ]]; then'),
        ]
        marker_by_mode = dict(markers)
        marker = marker_by_mode[mode]
        start = self.script.find(marker)
        self.assertNotEqual(start, -1, f"missing RUN_MODE block: {mode}")
        body_start = start + len(marker)
        next_starts = [
            self.script.find(next_marker, body_start)
            for next_mode, next_marker in markers
            if next_mode != mode
        ]
        next_starts = [index for index in next_starts if index != -1 and index > start]
        self.assertTrue(next_starts, f"missing end marker for RUN_MODE block: {mode}")
        return self.script[body_start : min(next_starts)]

    def _assert_runner_in_local_modes(self, fn_name: str) -> None:
        pattern = rf"(?m)^\s*{re.escape(fn_name)}(?!\(\))\b"
        for mode in ("smoke", "full", "hardening"):
            with self.subTest(mode=mode, runner=fn_name):
                self.assertRegex(self._run_mode_body(mode), pattern)

    def test_paper_preflight_surface_is_conditionally_wired(self) -> None:
        self.assertIn("changed_path_is_paper_preflight_surface()", self.script)
        body = self._shell_function_body("changed_path_is_paper_preflight_surface")
        expected_triggers = [
            "docs/paper/",
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
            "scripts/run_phase39_real_decode_composition_suite.sh",
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
        self._assert_runner_in_local_modes("run_paper_preflight_if_needed")

    def test_reference_verifier_surface_is_conditionally_wired(self) -> None:
        self.assertIn("changed_path_is_reference_verifier_surface()", self.script)
        body = self._shell_function_body("changed_path_is_reference_verifier_surface")
        expected_triggers = [
            "tools/reference_verifier/",
            "scripts/run_reference_verifier_suite.sh",
            "docs/engineering/paper3-claim-evidence.yml",
            "docs/engineering/paper3-composition-prototype.md",
            "spec/stwo-phase38-paper3-composition-prototype.schema.json",
            "spec/stwo-phase30-decoding-step-envelope-manifest.schema.json",
            "spec/stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json",
            "src/stwo_backend/recursion.rs",
            "scripts/local_merge_gate.sh",
        ]
        for trigger in expected_triggers:
            with self.subTest(trigger=trigger):
                self.assertIn(f'changed_path_has_prefix "{trigger}"', body)
        runner_body = self._shell_function_body("run_reference_verifier_if_needed")
        self.assertIn("if changed_path_is_reference_verifier_surface; then", runner_body)
        self.assertIn("run_reference_verifier_smoke", runner_body)
        self._assert_runner_in_local_modes("run_reference_verifier_if_needed")

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
        self._assert_runner_in_local_modes("run_approximation_budget_if_needed")

    def test_phase38_schema_surface_is_conditionally_wired(self) -> None:
        self.assertIn("changed_path_is_phase38_schema_surface()", self.script)
        body = self._shell_function_body("changed_path_is_phase38_schema_surface")
        expected_triggers = [
            "spec/stwo-phase38-paper3-composition-prototype.schema.json",
            "spec/stwo-phase30-decoding-step-envelope-manifest.schema.json",
            "spec/stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json",
            "docs/engineering/paper3-claim-evidence.yml",
            "docs/engineering/paper3-composition-prototype.md",
            "src/stwo_backend/recursion.rs",
            "scripts/tests/test_phase38_schema.py",
            "scripts/run_phase38_schema_suite.sh",
            "scripts/local_merge_gate.sh",
        ]
        for trigger in expected_triggers:
            with self.subTest(trigger=trigger):
                self.assertIn(f'changed_path_has_prefix "{trigger}"', body)
        runner_body = self._shell_function_body("run_phase38_schema_if_needed")
        self.assertIn("if changed_path_is_phase38_schema_surface; then", runner_body)
        self.assertIn(
            "run_logged phase38-schema env SKIP_PAPER_PREFLIGHT=1 bash scripts/run_phase38_schema_suite.sh",
            runner_body,
        )
        self.assertIn(
            "run_logged phase38-schema bash scripts/run_phase38_schema_suite.sh",
            runner_body,
        )
        self._assert_runner_in_local_modes("run_phase38_schema_if_needed")

    def test_phase39_real_decode_composition_surface_is_conditionally_wired(self) -> None:
        self.assertIn("changed_path_is_phase39_real_decode_composition_surface()", self.script)
        body = self._shell_function_body("changed_path_is_phase39_real_decode_composition_surface")
        expected_triggers = [
            "src/stwo_backend/decoding.rs",
            "src/stwo_backend/recursion.rs",
            "docs/engineering/paper3-claim-evidence.yml",
            "docs/engineering/paper3-composition-prototype.md",
            "scripts/run_phase39_real_decode_composition_suite.sh",
            "tools/reference_verifier/",
            "scripts/local_merge_gate.sh",
        ]
        for trigger in expected_triggers:
            with self.subTest(trigger=trigger):
                self.assertIn(f'changed_path_has_prefix "{trigger}"', body)
        runner_body = self._shell_function_body(
            "run_phase39_real_decode_composition_if_needed"
        )
        self.assertIn(
            "if changed_path_is_phase39_real_decode_composition_surface; then",
            runner_body,
        )
        self.assertIn(
            "run_logged phase39-real-decode-composition bash scripts/run_phase39_real_decode_composition_suite.sh",
            runner_body,
        )
        self._assert_runner_in_local_modes("run_phase39_real_decode_composition_if_needed")


if __name__ == "__main__":
    unittest.main()
