import copy
import tempfile
import unittest
from unittest import mock

from scripts import zkai_native_attention_mlp_adapter_air_frontier_gate as gate


class NativeAttentionMlpAdapterAirFrontierGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_pins_adapter_air_frontier(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload)
        summary = payload["summary"]
        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertEqual(summary["native_adapter_air_status"], "READY_FOR_NATIVE_AIR_IMPLEMENTATION")
        self.assertFalse(summary["native_adapter_air_proven_in_current_artifact"])
        self.assertEqual(summary["adapter_rows"], 128)
        self.assertEqual(summary["adapter_columns"], 9)
        self.assertEqual(summary["adapter_trace_cells"], 1536)
        self.assertEqual(summary["constraint_count"], len(gate.CONSTRAINTS))
        self.assertTrue(summary["adapter_outputs_match_d128_input_commitment"])
        self.assertTrue(summary["all_remainders_fit_three_bits"])

    def test_budget_records_only_32_typed_bytes_of_size_slack(self) -> None:
        payload = self.fresh_payload()
        summary = payload["summary"]
        self.assertEqual(summary["single_proof_typed_bytes"], 40_668)
        self.assertEqual(summary["two_proof_frontier_typed_bytes"], 40_700)
        self.assertEqual(summary["typed_slack_vs_two_proof_bytes"], 32)
        self.assertEqual(summary["max_adapter_overhead_for_size_win_bytes"], 32)
        self.assertEqual(summary["native_adapter_air_size_breakthrough_status"], "NO_GO")
        self.assertEqual(summary["current_gap_to_nanozk_reported_bytes"], 33_768)

    def test_projection_rows_satisfy_native_air_candidate_relations(self) -> None:
        sources = gate.load_sources()
        projection = gate.validate_projection_rows(sources["derived"])
        self.assertEqual(projection["row_count"], 128)
        self.assertGreaterEqual(projection["min_floor_remainder_q8"], 0)
        self.assertLess(projection["max_floor_remainder_q8"], 8)
        self.assertEqual(projection["output_min_q8"], -4)
        self.assertEqual(projection["output_max_q8"], 5)
        self.assertEqual(projection["output_sum_q8"], 104)

    def test_projection_rows_reject_bias_policy_compensation(self) -> None:
        sources = gate.load_sources()
        derived = copy.deepcopy(sources["derived"])
        row = derived["derived_input"]["projection_rows"][0]
        row["bias_q8"] += 9
        row["primary_q8"] -= 1
        with self.assertRaisesRegex(gate.AdapterAirFrontierError, "bias policy drift"):
            gate.validate_projection_rows(derived)

    def test_candidate_constraints_include_commitment_boundary(self) -> None:
        payload = self.fresh_payload()
        candidate = payload["adapter_air_candidate"]
        self.assertIn("output_q8_commitment_equals_d128_rmsnorm_input_activation_commitment", candidate["constraints"])
        self.assertEqual(
            candidate["source_attention_outputs_commitment"],
            "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
        )
        self.assertEqual(
            candidate["output_d128_input_activation_commitment"],
            "blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35",
        )

    def test_mutations_reject_overclaims_and_drift(self) -> None:
        payload = self.fresh_payload()
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(gate.MUTATION_NAMES))
        self.assertEqual([case["name"] for case in payload["cases"]], list(gate.MUTATION_NAMES))

        mutated = self.fresh_payload()
        mutated["summary"]["native_adapter_air_proven_in_current_artifact"] = True
        gate.refresh_payload_commitment(mutated)
        with self.assertRaises(gate.AdapterAirFrontierError):
            gate.validate_payload(mutated)

        mutated = self.fresh_payload()
        mutated["summary"]["native_adapter_air_size_breakthrough_status"] = "GO"
        gate.refresh_payload_commitment(mutated)
        with self.assertRaises(gate.AdapterAirFrontierError):
            gate.validate_payload(mutated)

    def test_source_artifacts_are_hash_bound(self) -> None:
        payload = self.fresh_payload()
        artifacts = {artifact["id"]: artifact for artifact in payload["source_artifacts"]}
        self.assertEqual(
            set(artifacts),
            {
                "attention_derived_d128_input_gate",
                "native_attention_mlp_single_proof_gate",
                "native_attention_mlp_lifting_ablation_gate",
            },
        )
        for artifact in artifacts.values():
            self.assertTrue(artifact["path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(artifact["sha256"]), 64)
            self.assertEqual(len(artifact["payload_sha256"]), 64)

    def test_tsv_round_trips_from_validated_payload(self) -> None:
        payload = self.fresh_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn("READY_FOR_NATIVE_AIR_IMPLEMENTATION", tsv)
        self.assertIn("\t32\t", tsv)
        self.assertIn("implement the adapter component", tsv)

    def test_read_json_rejects_non_finite_constants(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            path = gate.pathlib.Path(temp_dir) / "nan.json"
            path.write_text('{"bad": NaN}', encoding="utf-8")
            with self.assertRaises(gate.AdapterAirFrontierError):
                gate.read_json(path, "nan JSON")

    def test_read_json_open_error_is_structured(self) -> None:
        with mock.patch.object(gate.os, "open", side_effect=OSError("boom")):
            with self.assertRaises(gate.AdapterAirFrontierError) as cm:
                gate.read_json(gate.DERIVED_INPUT_PATH, "derived input gate")
        self.assertIn("derived input gate", str(cm.exception))
        self.assertIn("boom", str(cm.exception))

    def test_write_outputs_rejects_outside_path_and_symlink(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as temp_dir:
            outside = gate.pathlib.Path(temp_dir) / "out.json"
            with self.assertRaisesRegex(gate.AdapterAirFrontierError, "output path must stay"):
                gate.write_outputs(payload, outside, None)

        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            temp_path = gate.pathlib.Path(temp_dir)
            target = temp_path / "target.json"
            link = temp_path / "out.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaisesRegex(gate.AdapterAirFrontierError, "symlink"):
                gate.write_outputs(payload, link, None)


if __name__ == "__main__":
    unittest.main()
