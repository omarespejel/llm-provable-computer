import copy
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_derived_d128_mlp_fusion_attribution_gate as gate


class AttentionDerivedD128MlpFusionAttributionGateTests(unittest.TestCase):
    def test_payload_records_exact_attribution(self) -> None:
        payload = gate.build_payload()
        aggregate = payload["aggregate"]
        summary = payload["summary"]
        self.assertEqual(aggregate["available_separate_typed_bytes"], 59_344)
        self.assertEqual(aggregate["derived_fused_typed_bytes"], 22_576)
        self.assertEqual(aggregate["typed_saving_vs_separate_bytes"], 36_768)
        self.assertEqual(aggregate["typed_ratio_vs_separate"], 0.380426)
        self.assertEqual(summary["opening_plumbing_saved_bytes"], 33_280)
        self.assertEqual(summary["opening_plumbing_share"], 0.905135)
        self.assertEqual(summary["largest_saved_group"], "fri_decommitments")
        gate.validate_payload(payload)

    def test_group_attribution_ranks_fri_and_trace_decommitments(self) -> None:
        payload = gate.build_payload()
        ranked = payload["ranked_saved_groups"]
        self.assertEqual(ranked[0]["group"], "fri_decommitments")
        self.assertEqual(ranked[0]["saved_typed_bytes"], 20_512)
        self.assertEqual(ranked[1]["group"], "trace_decommitments")
        self.assertEqual(ranked[1]["saved_typed_bytes"], 12_768)
        saved = ranked[0]["saved_typed_bytes"] + ranked[1]["saved_typed_bytes"]
        self.assertEqual(saved, payload["summary"]["opening_plumbing_saved_bytes"])

    def test_mutations_reject(self) -> None:
        payload = gate.build_payload()
        result = gate.run_mutations(payload)
        self.assertEqual(result["case_count"], len(gate.MUTATION_NAMES))
        self.assertTrue(result["all_mutations_rejected"])

    def test_compression_probe_overclaim_rejects(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["summary"]["safe_compression_status"] = "SAFE_INTERNAL_BUCKET_REMOVED"
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaises(gate.MlpFusionAttributionError):
            gate.validate_payload(mutated)

    def test_group_saved_drift_rejects(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["group_attribution"]["fri_decommitments"]["saved_typed_bytes"] = 1
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaises(gate.MlpFusionAttributionError):
            gate.validate_payload(mutated)

    def test_route_gate_status_drift_rejects(self) -> None:
        route_gate = gate.read_json(gate.ROUTE_GATE_PATH, 4 * 1024 * 1024, "route gate JSON")
        route_gate["comparison"]["matched_six_separate_derived_baseline_status"] = "PARTIAL"
        with self.assertRaises(gate.MlpFusionAttributionError):
            gate.validate_route_gate(route_gate)

    def test_read_json_rejects_non_finite_constants(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            path = gate.pathlib.Path(temp_dir) / "nan.json"
            path.write_text('{"bad": NaN}', encoding="utf-8")
            with self.assertRaises(gate.MlpFusionAttributionError):
                gate.read_json(path, 1024, "nan JSON")

    def test_read_json_open_error_is_structured(self) -> None:
        with mock.patch.object(gate.os, "open", side_effect=OSError("boom")):
            with self.assertRaises(gate.MlpFusionAttributionError) as cm:
                gate.read_json(gate.ACCOUNTING_PATH, 16 * 1024 * 1024, "accounting JSON")
        message = str(cm.exception)
        self.assertIn("accounting JSON", message)
        self.assertIn("boom", message)

    def test_attribution_output_rejects_symlink(self) -> None:
        payload = gate.build_payload()
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            temp_path = gate.pathlib.Path(temp_dir)
            target = temp_path / "target.json"
            link = temp_path / "out.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(gate.MlpFusionAttributionError):
                gate.write_json(link, payload)

    def test_attribution_output_rejects_escape_without_mkdir(self) -> None:
        payload = gate.build_payload()
        with tempfile.TemporaryDirectory() as temp_dir:
            outside_dir = gate.pathlib.Path(temp_dir) / "outside"
            with self.assertRaises(gate.MlpFusionAttributionError):
                gate.write_json(outside_dir / "out.json", payload)
            self.assertFalse(outside_dir.exists())


if __name__ == "__main__":
    unittest.main()
