from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_two_slice_recursive_pcd_backend_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_two_slice_recursive_pcd_backend_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 recursive/PCD backend gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128TwoSliceRecursivePCDBackendGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_recursive_pcd_no_go_without_downgrading_accumulator_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "BOUNDED_NO_GO")
        self.assertEqual(payload["issue"], 411)
        self.assertEqual(payload["accumulator_baseline_result"], GATE.ACCUMULATOR_BASELINE_RESULT)
        self.assertEqual(payload["recursive_or_pcd_result"], GATE.RECURSIVE_OR_PCD_RESULT)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertEqual(payload["source_accumulator"]["result"], "GO")
        self.assertEqual(payload["source_accumulator"]["claim_boundary"], GATE.EXPECTED_SOURCE_CLAIM_BOUNDARY)

    def test_probe_binds_the_existing_two_slice_public_inputs(self) -> None:
        payload = self.fresh_payload()
        descriptor = payload["source_accumulator"]
        probe = payload["backend_probe"]
        self.assertEqual(probe["selected_slice_ids"], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        self.assertEqual(probe["selected_checked_rows"], 256)
        self.assertEqual(probe["two_slice_target_commitment"], descriptor["two_slice_target_commitment"])
        self.assertEqual(probe["accumulator_commitment"], descriptor["accumulator_commitment"])
        self.assertEqual(probe["verifier_handle_commitment"], descriptor["verifier_handle_commitment"])
        self.assertTrue(probe["attempt"]["blocked_before_metrics"])
        self.assertFalse(probe["attempt"]["proof_metrics_enabled"])

    def test_candidate_inventory_separates_inner_starks_accumulator_and_missing_backend(self) -> None:
        payload = self.fresh_payload()
        by_name = {item["name"]: item for item in payload["candidate_inventory"]}
        self.assertEqual(
            by_name["d128_two_slice_accumulator_backend"]["classification"],
            "GO_NON_RECURSIVE_ACCUMULATOR_ONLY",
        )
        self.assertEqual(
            by_name["d128_rmsnorm_public_row_inner_stark"]["classification"],
            "INNER_STARK_VERIFIER_NOT_NESTED_VERIFIER_CIRCUIT",
        )
        self.assertFalse(by_name["required_d128_two_slice_recursive_pcd_backend_module"]["exists"])
        self.assertTrue(by_name["required_d128_two_slice_recursive_pcd_backend_module"]["required_for_go"])

    def test_all_checked_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertFalse(any(case["mutated_accepted"] for case in payload["cases"]))
        self.assertEqual(
            {case["rejection_layer"] for case in payload["cases"]},
            {"source_accumulator", "candidate_inventory", "recursive_or_pcd_attempt", "parser_or_schema"},
        )

    def test_rejects_recursive_claim_relabeling_and_metric_smuggling(self) -> None:
        for mutation in (
            "recursive_artifact_claimed_without_artifact",
            "pcd_artifact_claimed_without_artifact",
            "local_verifier_handle_claimed_without_artifact",
            "proof_size_metric_smuggled_before_artifact",
            "verifier_time_metric_smuggled_before_artifact",
            "proof_generation_time_metric_smuggled_before_artifact",
            "recursive_or_pcd_result_changed_to_go",
        ):
            with self.subTest(mutation=mutation):
                mutated = GATE.mutate_payload(self.fresh_payload(), mutation)
                with self.assertRaises(GATE.D128TwoSliceRecursivePCDBackendError):
                    GATE.validate_core_payload(mutated)

    def test_rejects_candidate_inventory_tampering(self) -> None:
        for mutation in (
            "candidate_inventory_acceptance_relabel",
            "candidate_inventory_required_artifact_removed",
            "candidate_inventory_file_sha256_tampered",
            "candidate_inventory_required_token_removed",
        ):
            with self.subTest(mutation=mutation):
                mutated = GATE.mutate_payload(self.fresh_payload(), mutation)
                with self.assertRaisesRegex(GATE.D128TwoSliceRecursivePCDBackendError, "candidate inventory"):
                    GATE.validate_core_payload(mutated)

    def test_rejects_stored_case_tampering(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["rejected"] = False
        with self.assertRaisesRegex(GATE.D128TwoSliceRecursivePCDBackendError, "cases"):
            GATE.validate_payload(payload)

    def test_rejects_unknown_top_level_field(self) -> None:
        payload = self.fresh_payload()
        payload["invented_recursive_metric"] = 1
        with self.assertRaisesRegex(GATE.D128TwoSliceRecursivePCDBackendError, "key set mismatch"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips_and_rejects_collisions(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "recursive.json").relative_to(ROOT)
            tsv_path = (tmp / "recursive.tsv").relative_to(ROOT)
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads((ROOT / json_path).read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("recursive_artifact_claimed_without_artifact", (ROOT / tsv_path).read_text(encoding="utf-8"))
            with self.assertRaisesRegex(GATE.D128TwoSliceRecursivePCDBackendError, "distinct"):
                GATE.write_outputs(payload, json_path, json_path)

    def test_write_outputs_rejects_absolute_and_traversal_paths(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            with self.assertRaisesRegex(GATE.D128TwoSliceRecursivePCDBackendError, "repo-relative"):
                GATE.write_outputs(payload, pathlib.Path(raw_tmp) / "recursive.json", None)
        with self.assertRaisesRegex(GATE.D128TwoSliceRecursivePCDBackendError, "without traversal"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/../recursive.json"), None)

    def test_write_outputs_cleans_temp_file_when_replace_fails(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "recursive.json").relative_to(ROOT)
            with mock.patch.object(pathlib.Path, "replace", side_effect=OSError("forced replace failure")):
                with self.assertRaisesRegex(OSError, "forced replace failure"):
                    GATE.write_outputs(payload, json_path, None)
            self.assertEqual(list(tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
