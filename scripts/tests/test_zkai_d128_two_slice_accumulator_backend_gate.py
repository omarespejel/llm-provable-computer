from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_two_slice_accumulator_backend_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_two_slice_accumulator_backend_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 two-slice accumulator backend gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128TwoSliceAccumulatorBackendGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_accumulator_go_and_recursive_no_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["issue"], 409)
        self.assertEqual(payload["accumulator_result"], GATE.ACCUMULATOR_RESULT)
        self.assertEqual(payload["recursive_or_pcd_result"], GATE.RECURSIVE_OR_PCD_RESULT)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertEqual(payload["summary"]["selected_checked_rows"], 256)
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_accumulator_binds_target_statements_and_source_hashes(self) -> None:
        payload = self.fresh_payload()
        artifact = payload["accumulator_artifact"]
        preimage = artifact["preimage"]
        public_inputs = preimage["public_inputs"]
        transcript = preimage["verifier_transcript"]
        self.assertEqual(public_inputs["two_slice_target_commitment"], payload["source_two_slice_target"]["two_slice_target_commitment"])
        self.assertEqual(
            public_inputs["required_public_inputs"],
            [
                "two_slice_target_commitment",
                "selected_slice_statement_commitments",
                "selected_source_evidence_hashes",
            ],
        )
        self.assertEqual(
            public_inputs["selected_slice_statement_commitments"],
            [
                {"slice_id": entry["slice_id"], "statement_commitment": entry["statement_commitment"]}
                for entry in transcript
            ],
        )
        self.assertEqual(
            public_inputs["selected_source_evidence_hashes"],
            [
                {
                    "slice_id": entry["slice_id"],
                    "source_file_sha256": entry["source_file_sha256"],
                    "source_payload_sha256": entry["source_payload_sha256"],
                }
                for entry in transcript
            ],
        )

    def test_accumulator_and_verifier_commitments_round_trip(self) -> None:
        payload = self.fresh_payload()
        artifact = payload["accumulator_artifact"]
        GATE.verify_accumulator_artifact(artifact)
        expected_acc = GATE.blake2b_commitment(artifact["preimage"], GATE.ACCUMULATOR_DOMAIN)
        self.assertEqual(artifact["accumulator_commitment"], expected_acc)
        handle = payload["verifier_handle"]
        GATE.verify_verifier_handle(handle, artifact)
        expected_handle = GATE.blake2b_commitment(handle["preimage"], GATE.VERIFIER_HANDLE_DOMAIN)
        self.assertEqual(handle["verifier_handle_commitment"], expected_handle)
        self.assertTrue(handle["accepted"])

    def test_selected_sources_validate_with_slice_local_validators(self) -> None:
        transcript = self.fresh_payload()["accumulator_artifact"]["preimage"]["verifier_transcript"]
        self.assertEqual([entry["slice_id"] for entry in transcript], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        self.assertEqual(sum(entry["row_count"] for entry in transcript), 256)
        for entry in transcript:
            self.assertTrue(entry["verified"])
            self.assertTrue(entry["source_path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(entry["source_file_sha256"]), 64)
            self.assertEqual(len(entry["source_payload_sha256"]), 64)
            self.assertTrue(entry["statement_commitment"].startswith("blake2b-256:"))

    def test_recursive_or_pcd_metrics_remain_blocked(self) -> None:
        status = self.fresh_payload()["recursive_or_pcd_status"]
        self.assertFalse(status["recursive_outer_proof_claimed"])
        self.assertFalse(status["pcd_outer_proof_claimed"])
        self.assertEqual(status["outer_proof_artifacts"], [])
        self.assertTrue(all(value is None for value in status["proof_metrics"].values()))
        self.assertIn("no executable recursive/PCD", status["first_blocker"])

    def test_mutation_inventory_covers_binding_and_non_claim_surfaces(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        expected_layers = {
            "source_two_slice_file_hash_drift": "source_two_slice_target",
            "accumulator_commitment_drift": "accumulator_artifact",
            "public_input_selected_statement_drift": "accumulator_artifact",
            "selected_slice_removed": "accumulator_artifact",
            "source_statement_commitment_drift": "accumulator_artifact",
            "validator_result_false": "accumulator_artifact",
            "verifier_handle_commitment_drift": "verifier_handle",
            "recursive_outer_proof_claimed": "recursive_or_pcd_status",
            "recursive_proof_metric_smuggled": "recursive_or_pcd_status",
            "recursive_result_changed_to_go": "recursive_or_pcd_status",
        }
        for mutation, layer in expected_layers.items():
            with self.subTest(mutation=mutation):
                self.assertTrue(cases[mutation]["rejected"])
                self.assertEqual(cases[mutation]["rejection_layer"], layer)

    def test_rejects_target_public_input_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["accumulator_artifact"]["preimage"]["public_inputs"]["two_slice_target_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(GATE.D128TwoSliceAccumulatorBackendError, "accumulator"):
            GATE.validate_payload(payload)

    def test_rejects_source_hash_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["accumulator_artifact"]["preimage"]["verifier_transcript"][0]["source_payload_sha256"] = "22" * 32
        with self.assertRaisesRegex(GATE.D128TwoSliceAccumulatorBackendError, "accumulator"):
            GATE.validate_payload(payload)

    def test_rejects_recursive_claim_without_backend(self) -> None:
        payload = self.fresh_payload()
        payload["recursive_or_pcd_status"]["recursive_outer_proof_claimed"] = True
        with self.assertRaisesRegex(GATE.D128TwoSliceAccumulatorBackendError, "recursive"):
            GATE.validate_payload(payload)

    def test_rejects_metric_smuggling_before_recursive_backend_exists(self) -> None:
        payload = self.fresh_payload()
        payload["recursive_or_pcd_status"]["proof_metrics"]["recursive_verifier_time_ms"] = 1.0
        with self.assertRaisesRegex(GATE.D128TwoSliceAccumulatorBackendError, "metric"):
            GATE.validate_payload(payload)

    def test_rejects_partial_mutation_metadata(self) -> None:
        payload = self.fresh_payload()
        del payload["cases"]
        with self.assertRaisesRegex(GATE.D128TwoSliceAccumulatorBackendError, "mutation metadata"):
            GATE.validate_payload(payload)

    def test_accepted_mutation_case_reports_not_all_rejected(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["mutated_accepted"] = True
        payload["cases"][0]["rejected"] = False
        payload["cases"][0]["rejection_layer"] = "accepted"
        payload["cases"][0]["error"] = ""
        payload["all_mutations_rejected"] = False
        with self.assertRaisesRegex(GATE.D128TwoSliceAccumulatorBackendError, "not all"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "accumulator.json").relative_to(ROOT)
            tsv_path = (tmp / "accumulator.tsv").relative_to(ROOT)
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads((ROOT / json_path).read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("recursive_result_changed_to_go", (ROOT / tsv_path).read_text(encoding="utf-8"))

    def test_write_outputs_rejects_absolute_and_traversal_paths(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            with self.assertRaisesRegex(GATE.D128TwoSliceAccumulatorBackendError, "repo-relative"):
                GATE.write_outputs(payload, pathlib.Path(raw_tmp) / "accumulator.json", None)
        with self.assertRaisesRegex(GATE.D128TwoSliceAccumulatorBackendError, "without traversal"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/../accumulator.json"), None)


if __name__ == "__main__":
    unittest.main()
