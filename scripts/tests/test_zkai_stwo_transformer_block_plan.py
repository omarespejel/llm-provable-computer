from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "scripts" / "zkai_stwo_transformer_block_plan.py"
SPEC = importlib.util.spec_from_file_location("zkai_stwo_transformer_block_plan", PLAN_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load transformer-block plan validator from {PLAN_PATH}")
PLAN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PLAN
SPEC.loader.exec_module(PLAN)


class ZkAIStwoTransformerBlockPlanTests(unittest.TestCase):
    def _plan(self) -> dict:
        return PLAN.load_plan()

    def test_checked_plan_validates_and_summarizes_gate(self) -> None:
        summary = PLAN.validate_plan(self._plan())

        self.assertEqual(summary["schema"], PLAN.PLAN_SCHEMA)
        self.assertEqual(summary["status"], "design_gate")
        self.assertEqual(summary["target"], "rmsnorm-affine-residual-block-v1")
        self.assertEqual(summary["statement_kind"], "transformer-block")
        self.assertEqual(summary["width"], 4)
        self.assertEqual(summary["go_criteria_count"], 5)
        self.assertEqual(summary["no_go_criteria_count"], 4)

    def test_plan_requires_transformer_structure_not_linear_relabel(self) -> None:
        plan = self._plan()
        plan["target"]["operations"] = [
            {"id": "quantized_affine_projection", "description": "linear only"}
        ]

        with self.assertRaisesRegex(PLAN.PlanValidationError, "rmsnorm_scale_lookup"):
            PLAN.validate_plan(plan)

    def test_plan_requires_residual_structure(self) -> None:
        plan = self._plan()
        plan["target"]["operations"] = [
            item
            for item in plan["target"]["operations"]
            if item["id"] != "residual_add"
        ]

        with self.assertRaisesRegex(PLAN.PlanValidationError, "residual_add"):
            PLAN.validate_plan(plan)

    def test_plan_requires_statement_binding_fields(self) -> None:
        plan = self._plan()
        plan["target"]["public_commitments"].remove("evidence_manifest_commitment")

        with self.assertRaisesRegex(PLAN.PlanValidationError, "evidence_manifest_commitment"):
            PLAN.validate_plan(plan)

    def test_plan_requires_public_instance_binding(self) -> None:
        plan = self._plan()
        plan["target"]["public_commitments"].remove("public_instance_commitment")

        with self.assertRaisesRegex(PLAN.PlanValidationError, "public_instance_commitment"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_unhashable_public_commitment_cleanly(self) -> None:
        plan = self._plan()
        plan["target"]["public_commitments"].append({"bad": "shape"})

        with self.assertRaisesRegex(PLAN.PlanValidationError, "public_commitments"):
            PLAN.validate_plan(plan)

    def test_plan_requires_relabeling_go_criterion(self) -> None:
        plan = self._plan()
        plan["go_criteria"] = [
            item
            for item in plan["go_criteria"]
            if item["id"] != "relabeling_suite_rejects_all_statement_mutations"
        ]

        with self.assertRaisesRegex(PLAN.PlanValidationError, "relabeling_suite"):
            PLAN.validate_plan(plan)

    def test_plan_requires_no_go_for_linear_toy_collapse(self) -> None:
        plan = self._plan()
        plan["no_go_criteria"] = [
            item
            for item in plan["no_go_criteria"]
            if item["id"] != "target_collapses_to_linear_toy"
        ]

        with self.assertRaisesRegex(PLAN.PlanValidationError, "target_collapses_to_linear_toy"):
            PLAN.validate_plan(plan)

    def test_plan_keeps_existing_linear_block_as_baseline_not_result(self) -> None:
        plan = self._plan()
        self.assertEqual(
            plan["current_baseline"]["model_id"],
            "urn:zkai:ptvm:linear-block-v4-with-lookup",
        )
        self.assertEqual(
            plan["target"]["statement_kind"],
            "transformer-block",
        )
        self.assertIn(
            "does not claim that the existing linear-block primitive already proves transformer-block semantics",
            "\n".join(plan["non_claims"]).lower(),
        )

    def test_plan_rejects_overstated_baseline(self) -> None:
        plan = self._plan()
        plan["current_baseline"]["mutation_result"]["proof_only"][
            "decision"
        ] = "GO_FOR_STATEMENT_BINDING"

        with self.assertRaisesRegex(PLAN.PlanValidationError, "proof-only baseline"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_baseline_proof_system_version_drift(self) -> None:
        plan = self._plan()
        plan["current_baseline"]["proof_system_version"] = "stwo-phase999-invalid"

        with self.assertRaisesRegex(PLAN.PlanValidationError, "proof_system_version"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_statement_corpus_size_weakening(self) -> None:
        plan = self._plan()
        plan["current_baseline"]["mutation_result"]["statement_envelope"][
            "mutations_checked"
        ] = 1
        plan["current_baseline"]["mutation_result"]["statement_envelope"][
            "mutations_rejected"
        ] = 1

        with self.assertRaisesRegex(PLAN.PlanValidationError, "statement-envelope baseline"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_proof_only_corpus_size_drift(self) -> None:
        plan = self._plan()
        plan["current_baseline"]["mutation_result"]["proof_only"][
            "mutations_checked"
        ] = 1
        plan["current_baseline"]["mutation_result"]["proof_only"][
            "mutations_rejected"
        ] = 1

        with self.assertRaisesRegex(PLAN.PlanValidationError, "proof-only baseline"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_agent_composition_corpus_size_weakening(self) -> None:
        plan = self._plan()
        plan["current_baseline"]["agent_composition_result"][
            "mutations_checked"
        ] = 1
        plan["current_baseline"]["agent_composition_result"][
            "mutations_rejected"
        ] = 1

        with self.assertRaisesRegex(PLAN.PlanValidationError, "agent composition baseline"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_validation_command_coverage_weakening(self) -> None:
        plan = self._plan()
        plan["validation_commands"] = [
            "python3 scripts/zkai_stwo_transformer_block_plan.py --json",
            "python3 -m unittest scripts.tests.test_zkai_stwo_transformer_block_plan",
            "just gate-fast",
            "just gate",
        ]

        with self.assertRaisesRegex(PLAN.PlanValidationError, "test_zkai_stwo_statement_envelope"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_missing_fast_repo_gate(self) -> None:
        plan = self._plan()
        plan["validation_commands"] = [
            command for command in plan["validation_commands"] if command != "just gate-fast"
        ]

        with self.assertRaisesRegex(PLAN.PlanValidationError, "just gate-fast"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_missing_final_repo_gate(self) -> None:
        plan = self._plan()
        plan["validation_commands"] = [
            command
            for command in plan["validation_commands"]
            if command not in {"just gate", "just gate-no-nightly"}
        ]

        with self.assertRaisesRegex(PLAN.PlanValidationError, "final repo gate"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_final_repo_gate_not_last(self) -> None:
        plan = self._plan()
        plan["validation_commands"] = [
            "python3 scripts/zkai_stwo_transformer_block_plan.py --json",
            "just gate-fast",
            "just gate",
            "python3 -m unittest scripts.tests.test_zkai_stwo_transformer_block_plan scripts.tests.test_zkai_stwo_statement_envelope_benchmark scripts.tests.test_agent_step_zkai_stwo_composition",
        ]

        with self.assertRaisesRegex(PLAN.PlanValidationError, "end with final repo gate"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_non_string_validation_command_cleanly(self) -> None:
        plan = self._plan()
        plan["validation_commands"].append({"bad": "shape"})

        with self.assertRaisesRegex(PLAN.PlanValidationError, "validation_commands"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_empty_validation_commands_cleanly(self) -> None:
        plan = self._plan()
        plan["validation_commands"] = []

        with self.assertRaisesRegex(PLAN.PlanValidationError, "at least one command"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_missing_no_nightly_alternative(self) -> None:
        plan = self._plan()
        plan["validation_command_alternatives"] = []

        with self.assertRaisesRegex(PLAN.PlanValidationError, "validation_command_alternatives"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_wrong_no_nightly_alternative(self) -> None:
        plan = self._plan()
        plan["validation_command_alternatives"][0]["command"] = "just something-else"

        with self.assertRaisesRegex(PLAN.PlanValidationError, "just gate-no-nightly"):
            PLAN.validate_plan(plan)

    def test_plan_rejects_non_string_non_claim_cleanly(self) -> None:
        plan = self._plan()
        plan["non_claims"].append({"not": "a string"})

        with self.assertRaisesRegex(PLAN.PlanValidationError, "non_claims"):
            PLAN.validate_plan(plan)

    def test_main_returns_failure_on_malformed_plan_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = pathlib.Path(raw_tmp) / "bad.json"
            path.write_text("[]", encoding="utf-8")

            self.assertEqual(PLAN.main(["--plan", str(path), "--json"]), 1)

    def test_validation_rejects_mutated_plan_without_mutating_fixture(self) -> None:
        plan = self._plan()
        mutated = copy.deepcopy(plan)
        mutated["status"] = "result_go"

        with self.assertRaisesRegex(PLAN.PlanValidationError, "status"):
            PLAN.validate_plan(mutated)
        self.assertEqual(plan["status"], "design_gate")


if __name__ == "__main__":
    unittest.main()
