import copy
import tempfile
import unittest
from unittest import mock

from scripts import zkai_native_attention_mlp_adapter_compression_ablation_gate as gate


class NativeAttentionMlpAdapterCompressionAblationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_pins_current_frontier_and_ablation_result(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload)
        summary = payload["summary"]
        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertEqual(summary["current_frontier_typed_bytes"], 41_932)
        self.assertEqual(summary["compact_base_legacy_microprobe_typed_bytes"], 41_228)
        self.assertEqual(summary["compact_base_legacy_microprobe_saving_bytes"], 704)
        self.assertEqual(summary["compact_base_v2_saving_vs_label_control_bytes"], 736)
        self.assertEqual(
            summary["frontier_replacement_status"],
            "NO_GO_TRANSCRIPT_STABLE_FRONTIER_NOT_ESTABLISHED",
        )
        self.assertFalse(summary["nanozk_win_claimed"])

    def test_variant_table_keeps_label_control_and_frontier_boundary(self) -> None:
        variants = {variant["id"]: variant for variant in self.fresh_payload()["variants"]}
        self.assertEqual(set(variants), {variant["id"] for variant in gate.VARIANTS})
        current = variants["current_duplicate_adapter_v1_frontier"]
        legacy = variants["compact_base_legacy_label_microprobe"]
        label_control = variants["duplicate_adapter_v2_label_control"]
        compact_v2 = variants["compact_base_v2_referenced_fixed_columns"]

        self.assertTrue(current["frontier_safe"])
        self.assertFalse(legacy["frontier_safe"])
        self.assertFalse(compact_v2["frontier_safe"])
        self.assertEqual(current["adapter_trace_cells"], 1_536)
        self.assertEqual(compact_v2["adapter_trace_cells"], 1_024)
        self.assertEqual(label_control["typed_bytes"] - compact_v2["typed_bytes"], 736)
        self.assertEqual(current["typed_bytes"] - legacy["typed_bytes"], 704)

    def test_deltas_keep_remaining_gap_and_nanozk_non_claim(self) -> None:
        deltas = self.fresh_payload()["deltas"]
        self.assertEqual(deltas["legacy_microprobe_remaining_gap_to_two_proof_bytes"], 528)
        self.assertEqual(deltas["current_frontier_gap_to_two_proof_bytes"], 1_232)
        self.assertEqual(deltas["current_frontier_gap_to_nanozk_reported_bytes"], 35_032)
        self.assertEqual(deltas["best_safe_frontier_replacement_typed_bytes"], 41_932)
        self.assertEqual(deltas["best_local_ablation_typed_bytes"], 41_228)

    def test_grouped_bytes_sum_to_typed_bytes(self) -> None:
        for variant in self.fresh_payload()["variants"]:
            grouped_total = sum(variant["grouped"][key] for key in gate.GROUP_KEYS)
            self.assertEqual(grouped_total, variant["typed_bytes"])

    def test_mutations_reject_overclaims_and_drift(self) -> None:
        payload = self.fresh_payload()
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(gate.MUTATION_NAMES))
        self.assertEqual([case["name"] for case in payload["cases"]], list(gate.MUTATION_NAMES))

        mutated = self.fresh_payload()
        mutated["summary"]["nanozk_win_claimed"] = True
        gate.refresh_payload_commitment(mutated)
        with self.assertRaisesRegex(gate.AdapterCompressionAblationError, "summary drift|NANOZK overclaim"):
            gate.validate_payload(mutated)

        mutated = self.fresh_payload()
        mutated["summary"]["frontier_replacement_status"] = "GO_REPLACE_FRONTIER"
        gate.refresh_payload_commitment(mutated)
        with self.assertRaisesRegex(gate.AdapterCompressionAblationError, "summary drift|frontier replacement overclaim"):
            gate.validate_payload(mutated)

    def test_current_sources_are_hash_bound(self) -> None:
        payload = self.fresh_payload()
        artifacts = {artifact["id"]: artifact for artifact in payload["source_artifacts"]}
        self.assertEqual(
            set(artifacts),
            {"current_single_proof_gate", "current_single_proof_binary_accounting"},
        )
        for artifact in artifacts.values():
            self.assertTrue(artifact["path"].startswith("docs/engineering/evidence/"))
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(artifact["payload_sha256"], r"^[0-9a-f]{64}$")

    def test_current_source_validation_pins_adapter_route_boundary(self) -> None:
        sources = gate.load_sources()
        gate.validate_current_sources(sources)

        mutated = copy.deepcopy(sources)
        mutated["gate"]["routes"]["adapter_boundary"]["native_adapter_air_proven"] = False
        with self.assertRaisesRegex(gate.AdapterCompressionAblationError, "adapter route native AIR proof drift"):
            gate.validate_current_sources(mutated)

        mutated = copy.deepcopy(sources)
        mutated["gate"]["routes"]["adapter_boundary"]["adapter_trace_cells"] += 1
        with self.assertRaisesRegex(gate.AdapterCompressionAblationError, "adapter route adapter_trace_cells mismatch"):
            gate.validate_current_sources(mutated)

    def test_current_source_validation_pins_raw_artifact_hashes(self) -> None:
        sources = gate.load_sources()
        mutated = copy.deepcopy(sources)
        artifacts_by_id = {artifact["id"]: artifact for artifact in mutated["source_artifacts"]}
        artifacts_by_id["current_single_proof_gate"]["sha256"] = "00" * 32
        with self.assertRaisesRegex(gate.AdapterCompressionAblationError, "current_single_proof_gate hash drift"):
            gate.validate_current_sources(mutated)

    def test_tsv_round_trips_from_validated_payload(self) -> None:
        payload = self.fresh_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn("compact_base_v2_referenced_fixed_columns", tsv)
        self.assertIn("\t42492\t", tsv)
        self.assertIn("\t-736\t", tsv)
        self.assertIn("False", tsv)

    def test_read_json_rejects_non_finite_constants(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            path = gate.pathlib.Path(temp_dir) / "nan.json"
            path.write_text('{"bad": NaN}', encoding="utf-8")
            with self.assertRaises(gate.AdapterCompressionAblationError):
                gate.read_json(path, "nan JSON")

    def test_read_json_open_error_is_structured(self) -> None:
        with mock.patch.object(gate.os, "open", side_effect=OSError("boom")):
            with self.assertRaises(gate.AdapterCompressionAblationError) as cm:
                gate.read_json(gate.CURRENT_GATE_PATH, "current gate")
        self.assertIn("current gate", str(cm.exception))
        self.assertIn("boom", str(cm.exception))

    def test_write_outputs_rejects_outside_path_and_symlink(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as temp_dir:
            outside = gate.pathlib.Path(temp_dir) / "out.json"
            with self.assertRaisesRegex(gate.AdapterCompressionAblationError, "output path must stay"):
                gate.write_outputs(payload, outside, None)

        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            temp_path = gate.pathlib.Path(temp_dir)
            target = temp_path / "target.json"
            link = temp_path / "out.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaisesRegex(gate.AdapterCompressionAblationError, "symlink"):
                gate.write_outputs(payload, link, None)


if __name__ == "__main__":
    unittest.main()
