from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_layerwise_comparator_target_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_layerwise_comparator_target_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 comparator target gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128LayerwiseComparatorTargetGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_target_go_and_proof_no_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["target_result"], GATE.TARGET_RESULT)
        self.assertEqual(payload["local_proof_result"], GATE.LOCAL_PROOF_RESULT)
        self.assertEqual(payload["source_context_result"], GATE.SOURCE_CONTEXT_RESULT)
        self.assertEqual(payload["external_adapter_result"], GATE.EXTERNAL_ADAPTER_RESULT)
        self.assertEqual(payload["case_count"], 19)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["validation_commands"][0], "just gate-fast")
        self.assertEqual(payload["validation_commands"][-1], "just gate")

    def test_target_spec_is_the_d128_rmsnorm_swiglu_shape(self) -> None:
        target = self.fresh_payload()["target_spec"]
        self.assertEqual(target["width"], 128)
        self.assertEqual(target["ff_dim"], 512)
        self.assertEqual(target["estimated_linear_muls"], 196_608)
        self.assertEqual(target["estimated_activation_rows"], 512)
        self.assertEqual(target["estimated_residual_rows"], 128)
        self.assertEqual(target["row_operator_pressure"]["rmsnorm_rows"], 1)
        self.assertEqual(target["row_operator_pressure"]["swiglu_activation_rows"], 512)
        self.assertEqual(target["row_operator_pressure"]["residual_add_rows"], 128)
        self.assertEqual(target["d64_to_d128_scale_decision"], GATE.D128_SCALE_DECISION)
        self.assertEqual(target["required_proof_backend_version"], "stwo-rmsnorm-swiglu-residual-d128-v1")
        self.assertEqual(target["local_feasibility_status"], "NO_GO_CURRENT_SURFACE")
        self.assertTrue(target["target_commitment"].startswith("blake2b-256:"))
        generalization = {row["slice"]: row for row in target["d64_slice_generalization"]}
        self.assertEqual(generalization["rmsnorm_public_rows"]["d128_rows"], 128)
        self.assertIn("NOT_CURRENT_PROOF_SURFACE", generalization["gate_value_projection"]["decision"])
        self.assertEqual(generalization["residual_add"]["d128_rows"], 128)
        for required in (
            "model_artifact_commitment",
            "input_activation_commitment",
            "output_activation_commitment",
            "proof_commitment",
            "verifying_key_commitment",
            "verifier_domain",
        ):
            self.assertIn(required, target["required_statement_bindings"])

    def test_local_proof_status_blocks_metrics(self) -> None:
        status = self.fresh_payload()["local_proof_status"]
        self.assertFalse(status["proof_artifact_exists"])
        self.assertFalse(status["verifier_handle_exists"])
        self.assertFalse(status["statement_relabeling_suite_exists"])
        self.assertIsNone(status["proof_size_bytes"])
        self.assertIsNone(status["verifier_time_ms"])
        self.assertTrue(status["blocked_before_metrics"])
        blocker_ids = {blocker["id"] for blocker in status["inherited_feasibility_row"]["blockers"]}
        self.assertIn("proof_claim_d_model_mismatch", blocker_ids)
        self.assertIn("instruction_surface_too_small_for_swiglu", blocker_ids)

    def test_source_context_uses_nanozk_as_non_matched_calibration(self) -> None:
        nanozk = self.fresh_payload()["source_backed_context"]["NANOZK"]
        self.assertEqual(nanozk["system"], "NANOZK")
        self.assertEqual(nanozk["verify_seconds"], "0.024")
        self.assertEqual(nanozk["proof_size_reported"], "5.5 KB")
        self.assertIn("d=128", nanozk["model_or_dims"])
        self.assertIn("not a matched local benchmark", nanozk["claim_boundary"])
        self.assertIn("not as a matched workload benchmark", nanozk["notes"])

    def test_external_adapter_context_remains_not_run(self) -> None:
        external = self.fresh_payload()["external_adapter_status"]
        self.assertEqual(external["result"], GATE.EXTERNAL_ADAPTER_RESULT)
        self.assertEqual(external["paper_usage"], "source_backed_context_only_not_empirical_adapter_row")
        self.assertFalse(external["systems"]["DeepProve-1"]["public_proof_artifact_available"])
        self.assertFalse(external["systems"]["NANOZK"]["public_verifier_available"])
        self.assertFalse(external["systems"]["NANOZK"]["relabeling_benchmark_run"])

    def test_mutation_layers_cover_sources_target_metrics_and_external_context(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["matched_source_file_hash_drift"]["rejection_layer"], "source_evidence")
        self.assertEqual(cases["target_width_drift"]["rejection_layer"], "target_spec")
        self.assertEqual(cases["target_residual_row_count_drift"]["rejection_layer"], "target_spec")
        self.assertEqual(cases["target_scale_decision_promoted_to_go"]["rejection_layer"], "target_spec")
        self.assertEqual(cases["target_d64_slice_generalization_overclaim"]["rejection_layer"], "target_spec")
        self.assertEqual(cases["local_proof_size_metric_smuggled"]["rejection_layer"], "local_proof_status")
        self.assertEqual(cases["nanozk_source_context_promoted_to_matched"]["rejection_layer"], "source_context")
        self.assertEqual(cases["deepprove_public_artifact_overclaim"]["rejection_layer"], "external_adapter_status")
        self.assertEqual(cases["result_changed_to_go"]["rejection_layer"], "parser_or_schema")

    def test_rejects_local_d128_metric_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["local_proof_status"]["verifier_time_ms"] = 24.0
        with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "verifier-time metric"):
            GATE.validate_payload(payload)

    def test_rejects_source_context_promotion_to_matched_benchmark(self) -> None:
        payload = self.fresh_payload()
        payload["source_backed_context"]["NANOZK"]["claim_boundary"] = "matched local benchmark"
        with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "source-backed context"):
            GATE.validate_payload(payload)

    def test_rejects_external_public_artifact_overclaim(self) -> None:
        payload = self.fresh_payload()
        payload["external_adapter_status"]["systems"]["DeepProve-1"]["public_proof_artifact_available"] = True
        with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "external adapter status"):
            GATE.validate_payload(payload)

    def test_rejects_removed_non_claim(self) -> None:
        payload = self.fresh_payload()
        payload["non_claims"].remove("not a matched NANOZK benchmark")
        with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "non-claims"):
            GATE.validate_payload(payload)

    def test_rejects_duplicate_mutation_case(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][1] = copy.deepcopy(payload["cases"][0])
        with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "duplicate mutation case"):
            GATE.validate_payload(payload)

    def test_empty_mutation_generation_errors_get_non_empty_diagnostics(self) -> None:
        payload = GATE.build_payload()
        original_mutated_cases = GATE._mutated_cases

        def empty_generation_error(_payload: dict) -> list[tuple[str, str, dict, Exception]]:
            return [("matched_source_file_hash_drift", "source_evidence", copy.deepcopy(payload), RuntimeError())]

        try:
            GATE._mutated_cases = empty_generation_error
            cases = GATE.mutation_cases(payload)
        finally:
            GATE._mutated_cases = original_mutated_cases

        self.assertEqual(cases[0]["error"], "RuntimeError with empty message")
        self.assertTrue(cases[0]["rejected"])

    def test_rejects_rejected_mutation_case_without_error_message(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["error"] = ""
        with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "error must be non-empty"):
            GATE.validate_payload(payload)

    def test_rejects_missing_mutation_metadata_on_serialized_result(self) -> None:
        payload = self.fresh_payload()
        del payload["mutation_inventory"]
        del payload["cases"]
        del payload["case_count"]
        del payload["all_mutations_rejected"]
        payload["summary"].pop("mutation_cases")
        payload["summary"].pop("mutations_rejected")
        with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "mutation metadata"):
            GATE.validate_payload(payload)

    def test_tsv_rows_are_stable_and_contextual(self) -> None:
        rows = GATE.rows_for_tsv(self.fresh_payload())
        self.assertEqual([row["surface"] for row in rows], [
            "local_d128_target_spec",
            "local_d128_proof_artifact",
            "nanozk_d128_source_context",
            "deepprove_nanozk_adapter_context",
        ])
        self.assertEqual(rows[0]["status"], GATE.TARGET_RESULT)
        self.assertEqual(rows[1]["status"], GATE.LOCAL_PROOF_RESULT)
        self.assertEqual(rows[2]["verify_seconds"], "0.024")
        self.assertEqual(rows[2]["proof_size_reported"], "5.5 KB")
        self.assertIn("not empirical adapter", rows[3]["claim_boundary"])

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "d128-target.json"
            tsv_path = tmp / "d128-target.tsv"
            GATE.write_outputs(payload, json_path, tsv_path)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), payload)
            tsv = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv[0].split("\t"), list(GATE.TSV_COLUMNS))
            self.assertIn("nanozk_d128_source_context", tsv[3])

    def test_write_outputs_rejects_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "d128-target.json"
            tsv_path = tmp / "d128-target.tsv"
            with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "output path escapes repository"):
                GATE.write_outputs(payload, json_path, tsv_path)
            self.assertFalse(json_path.exists())
            self.assertFalse(tsv_path.exists())

    def test_write_outputs_rejects_directory_paths_inside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_dir = tmp / "json-output"
            tsv_path = tmp / "d128-target.tsv"
            json_dir.mkdir()
            with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "not a directory"):
                GATE.write_outputs(payload, json_dir, tsv_path)
            self.assertFalse(tsv_path.exists())

    def test_write_outputs_rejects_parent_paths_that_are_files(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            parent_file = tmp / "not-a-directory"
            parent_file.write_text("not a directory\n", encoding="utf-8")
            json_path = parent_file / "d128-target.json"
            tsv_path = tmp / "d128-target.tsv"
            with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "parent is not a directory"):
                GATE.write_outputs(payload, json_path, tsv_path)
            self.assertFalse(tsv_path.exists())

    def test_write_outputs_rejects_symlink_outputs(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            real_json = tmp / "real.json"
            json_link = tmp / "linked.json"
            tsv_path = tmp / "d128-target.tsv"
            real_json.write_text("old-json\n", encoding="utf-8")
            json_link.symlink_to(real_json)
            with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "must not be a symlink"):
                GATE.write_outputs(payload, json_link, tsv_path)
            self.assertFalse(tsv_path.exists())

    def test_write_outputs_does_not_replace_first_output_when_second_stage_fails(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "d128-target.json"
            tsv_path = tmp / "d128-target.tsv"
            json_path.write_text("old-json\n", encoding="utf-8")
            tsv_path.write_text("old-tsv\n", encoding="utf-8")
            original_stage_text = GATE._stage_text
            call_count = 0

            def flaky_stage_text(path: pathlib.Path, text: str) -> pathlib.Path:
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise GATE.D128ComparatorTargetError("forced second output stage failure")
                return original_stage_text(path, text)

            try:
                GATE._stage_text = flaky_stage_text
                with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "forced second output stage failure"):
                    GATE.write_outputs(payload, json_path, tsv_path)
            finally:
                GATE._stage_text = original_stage_text

            self.assertEqual(json_path.read_text(encoding="utf-8"), "old-json\n")
            self.assertEqual(tsv_path.read_text(encoding="utf-8"), "old-tsv\n")

    def test_write_outputs_rolls_back_with_atomic_replace_not_write_bytes(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "d128-target.json"
            tsv_path = tmp / "d128-target.tsv"
            json_path.write_text("old-json\n", encoding="utf-8")
            tsv_path.write_text("old-tsv\n", encoding="utf-8")
            original_replace = pathlib.Path.replace
            original_write_bytes = pathlib.Path.write_bytes
            replace_count = 0

            def fail_second_replace(self: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
                nonlocal replace_count
                replace_count += 1
                if replace_count == 2:
                    raise OSError("forced second replace failure")
                return original_replace(self, target)

            def forbid_write_bytes(self: pathlib.Path, data: bytes) -> int:
                raise AssertionError(f"rollback used in-place write_bytes on {self}")

            try:
                pathlib.Path.replace = fail_second_replace
                pathlib.Path.write_bytes = forbid_write_bytes
                with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "forced second replace failure"):
                    GATE.write_outputs(payload, json_path, tsv_path)
            finally:
                pathlib.Path.replace = original_replace
                pathlib.Path.write_bytes = original_write_bytes

            self.assertEqual(json_path.read_text(encoding="utf-8"), "old-json\n")
            self.assertEqual(tsv_path.read_text(encoding="utf-8"), "old-tsv\n")

    def test_write_outputs_preserves_stage_error_when_cleanup_fails(self) -> None:
        payload = self.fresh_payload()
        original_stage_text = GATE._stage_text

        class UnlinkFailingTmp:
            def __str__(self) -> str:
                return "unlink-failing.tmp"

            def unlink(self, missing_ok: bool = False) -> None:
                raise OSError("cleanup denied")

        call_count = 0

        def stage_then_fail(_path: pathlib.Path, _text: str) -> UnlinkFailingTmp:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return UnlinkFailingTmp()
            raise OSError("stage failed")

        try:
            GATE._stage_text = stage_then_fail
            with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
                tmp = pathlib.Path(raw_tmp)
                with self.assertRaisesRegex(
                    GATE.D128ComparatorTargetError,
                    "stage failed.*cleanup failed.*cleanup denied",
                ):
                    GATE.write_outputs(payload, tmp / "d128-target.json", tmp / "d128-target.tsv")
        finally:
            GATE._stage_text = original_stage_text

    def test_write_outputs_rejects_before_writing_partial_artifacts(self) -> None:
        payload = self.fresh_payload()
        payload["local_proof_status"]["proof_size_bytes"] = 5500
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "d128-target.json"
            tsv_path = tmp / "d128-target.tsv"
            with self.assertRaisesRegex(GATE.D128ComparatorTargetError, "proof-size metric"):
                GATE.write_outputs(payload, json_path, tsv_path)
            self.assertFalse(json_path.exists())
            self.assertFalse(tsv_path.exists())


if __name__ == "__main__":
    unittest.main()
