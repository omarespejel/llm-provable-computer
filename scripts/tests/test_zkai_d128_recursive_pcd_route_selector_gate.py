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
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_recursive_pcd_route_selector_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_recursive_pcd_route_selector_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 recursive/PCD route selector from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128RecursivePCDRouteSelectorGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_records_bounded_no_go_and_selects_next_route(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["issue"], 420)
        self.assertEqual(payload["route_decision"]["primary_blocker"], GATE.PRIMARY_BLOCKER)
        self.assertEqual(payload["route_decision"]["next_route"], GATE.NEXT_ROUTE)
        self.assertFalse(payload["route_decision"]["proof_metrics"]["metrics_enabled"])

    def test_consumes_existing_go_accumulators_without_relabeling_them_as_recursion(self) -> None:
        payload = self.fresh_payload()
        source = payload["source_evidence"]
        self.assertEqual(source["two_slice_accumulator"]["result"], "GO")
        self.assertEqual(source["full_block_accumulator"]["result"], "GO")
        self.assertEqual(
            source["two_slice_accumulator"]["claim_boundary"],
            "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF",
        )
        by_route = {route["route_id"]: route for route in payload["route_table"]}
        self.assertTrue(by_route["local_two_slice_non_recursive_accumulator"]["usable_today"])
        self.assertTrue(by_route["local_full_block_non_recursive_accumulator"]["usable_today"])
        self.assertEqual(
            by_route["local_two_slice_non_recursive_accumulator"]["status"],
            "GO_PRE_RECURSIVE_INTEGRITY_ONLY",
        )

    def test_local_stwo_and_pcd_routes_remain_blocked_before_metrics(self) -> None:
        payload = self.fresh_payload()
        by_route = {route["route_id"]: route for route in payload["route_table"]}
        self.assertFalse(by_route["local_stwo_nested_verifier_air"]["usable_today"])
        self.assertFalse(by_route["local_stwo_pcd_outer_proof"]["usable_today"])
        self.assertIn("MISSING_NESTED_VERIFIER", by_route["local_stwo_nested_verifier_air"]["status"])
        self.assertIn("MISSING_OUTER_PCD", by_route["local_stwo_pcd_outer_proof"]["status"])
        metrics = payload["route_decision"]["proof_metrics"]
        self.assertIsNone(metrics["recursive_proof_size_bytes"])
        self.assertIsNone(metrics["recursive_verifier_time_ms"])
        self.assertIsNone(metrics["recursive_proof_generation_time_ms"])

    def test_candidate_routes_are_not_marked_as_successes(self) -> None:
        payload = self.fresh_payload()
        by_route = {route["route_id"]: route for route in payload["route_table"]}
        for route_id in (
            "proof_native_two_slice_compression_without_recursion",
            "external_zkvm_statement_receipt_adapter",
            "external_snark_or_ivc_statement_adapter",
        ):
            with self.subTest(route_id=route_id):
                self.assertEqual(by_route[route_id]["status"], "RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO")
                self.assertFalse(by_route[route_id]["usable_today"])
        self.assertEqual(by_route["proof_native_two_slice_compression_without_recursion"]["evidence"]["tracked_issue"], 424)
        self.assertEqual(by_route["external_zkvm_statement_receipt_adapter"]["evidence"]["tracked_issue"], 422)

    def test_all_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertFalse(any(case["mutated_accepted"] for case in payload["cases"]))
        self.assertEqual(
            {case["rejection_layer"] for case in payload["cases"]},
            {"source_evidence", "route_table", "route_decision", "parser_or_schema"},
        )

    def test_rejects_recursive_route_relabeling_and_metric_smuggling(self) -> None:
        for mutation in (
            "route_local_stwo_nested_verifier_relabel_to_go",
            "route_local_pcd_relabel_to_go",
            "route_external_adapter_relabel_to_go",
            "proof_size_metric_smuggled",
            "verifier_time_metric_smuggled",
            "proof_generation_time_metric_smuggled",
            "decision_changed_to_go",
        ):
            with self.subTest(mutation=mutation):
                mutated = GATE.mutate_payload(self.fresh_payload(), mutation)
                with self.assertRaises(GATE.D128RecursivePCDRouteSelectorError):
                    GATE.validate_core_payload(mutated)

    def test_rejects_source_evidence_drift(self) -> None:
        for mutation in (
            "source_two_slice_result_drift",
            "source_two_slice_claim_boundary_drift",
            "source_full_block_result_drift",
            "source_recursive_no_go_result_changed_to_go",
            "source_recursive_blocker_removed",
        ):
            with self.subTest(mutation=mutation):
                mutated = GATE.mutate_payload(self.fresh_payload(), mutation)
                with self.assertRaisesRegex(GATE.D128RecursivePCDRouteSelectorError, "mismatch"):
                    GATE.validate_core_payload(mutated)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips_and_rejects_collisions(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "route.json").relative_to(ROOT)
            tsv_path = (tmp / "route.tsv").relative_to(ROOT)
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads((ROOT / json_path).read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("local_stwo_nested_verifier_air", (ROOT / tsv_path).read_text(encoding="utf-8"))
            with self.assertRaisesRegex(GATE.D128RecursivePCDRouteSelectorError, "distinct"):
                GATE.write_outputs(payload, json_path, json_path)

    def test_write_outputs_rejects_absolute_and_traversal_paths(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            with self.assertRaisesRegex(GATE.D128RecursivePCDRouteSelectorError, "repo-relative"):
                GATE.write_outputs(payload, pathlib.Path(raw_tmp) / "route.json", None)
        with self.assertRaisesRegex(GATE.D128RecursivePCDRouteSelectorError, "without traversal"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/../route.json"), None)

    def test_write_outputs_cleans_temp_file_when_replace_fails(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "route.json").relative_to(ROOT)
            with mock.patch.object(pathlib.Path, "replace", side_effect=OSError("forced replace failure")):
                with self.assertRaisesRegex(OSError, "forced replace failure"):
                    GATE.write_outputs(payload, json_path, None)
            self.assertEqual(list(tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
