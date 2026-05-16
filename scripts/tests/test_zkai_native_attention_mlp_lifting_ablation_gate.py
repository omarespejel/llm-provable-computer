import copy
import tempfile
import unittest
from unittest import mock

from scripts import zkai_native_attention_mlp_lifting_ablation_gate as gate


class NativeAttentionMlpLiftingAblationGateTests(unittest.TestCase):
    def test_payload_records_lifting_ablation_no_go(self) -> None:
        payload = gate.build_payload()
        summary = payload["summary"]
        self.assertEqual(summary["single_proof_typed_bytes"], 40_668)
        self.assertEqual(summary["two_proof_frontier_typed_bytes"], 40_700)
        self.assertEqual(summary["current_typed_saving_vs_two_proof_bytes"], 32)
        self.assertEqual(summary["positive_overhang_group"], "fri_decommitments")
        self.assertEqual(summary["fri_decommitment_overhang_bytes"], 640)
        self.assertEqual(summary["projected_typed_bytes_without_fri_overhang"], 40_028)
        self.assertEqual(summary["projected_gap_to_nanozk_reported_bytes"], 33_128)
        self.assertEqual(summary["lifting_only_breakthrough_status"], "NO_GO")
        gate.validate_payload(payload)

    def test_group_delta_pins_only_positive_overhang(self) -> None:
        payload = gate.build_payload()
        deltas = payload["group_deltas"]
        positives = {
            name: values["single_minus_two_proof_delta_bytes"]
            for name, values in deltas.items()
            if values["single_minus_two_proof_delta_bytes"] > 0
        }
        self.assertEqual(positives, {"fri_decommitments": 640})
        self.assertEqual(sum(value["single_minus_two_proof_delta_bytes"] for value in deltas.values()), -32)

    def test_mutations_reject(self) -> None:
        payload = gate.build_payload()
        result = gate.run_mutations(payload)
        self.assertEqual(result["case_count"], len(gate.MUTATION_NAMES))
        self.assertTrue(result["all_mutations_rejected"])

    def test_status_overclaim_rejects(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["summary"]["lifting_only_breakthrough_status"] = "GO"
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaises(gate.LiftingAblationError):
            gate.validate_payload(mutated)

    def test_projected_metric_smuggling_rejects(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["summary"]["projected_typed_bytes_without_fri_overhang"] = 6_900
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaises(gate.LiftingAblationError):
            gate.validate_payload(mutated)

    def test_source_artifact_hash_drift_rejects(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["source_artifacts"][0]["sha256"] = "0" * 64
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaises(gate.LiftingAblationError):
            gate.validate_payload(mutated)

    def test_read_json_rejects_non_finite_constants(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            path = gate.pathlib.Path(temp_dir) / "nan.json"
            path.write_text('{"bad": NaN}', encoding="utf-8")
            with self.assertRaises(gate.LiftingAblationError):
                gate.read_json(path, 1024, "nan JSON")

    def test_read_json_open_error_is_structured(self) -> None:
        with mock.patch.object(gate.os, "open", side_effect=OSError("boom")):
            with self.assertRaises(gate.LiftingAblationError) as cm:
                gate.read_json(gate.SINGLE_ACCOUNTING_PATH, 16 * 1024 * 1024, "single accounting JSON")
        message = str(cm.exception)
        self.assertIn("single accounting JSON", message)
        self.assertIn("boom", message)

    def test_read_json_rejects_post_read_size_drift(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            path = gate.pathlib.Path(temp_dir) / "drift.json"
            path.write_text('{"ok": true}', encoding="utf-8")
            real_fstat = gate.os.fstat
            calls = 0

            def drifting_fstat(fd: int) -> gate.os.stat_result:
                nonlocal calls
                calls += 1
                result = real_fstat(fd)
                if calls == 2:
                    values = list(result)
                    values[6] = result.st_size + 1
                    return gate.os.stat_result(values)
                return result

            with mock.patch.object(gate.os, "fstat", side_effect=drifting_fstat):
                with self.assertRaises(gate.LiftingAblationError) as cm:
                    gate.read_json(path, 1024, "drifting JSON")
        self.assertIn("changed while reading", str(cm.exception))

    def test_output_rejects_symlink(self) -> None:
        payload = gate.build_payload()
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            temp_path = gate.pathlib.Path(temp_dir)
            target = temp_path / "target.json"
            link = temp_path / "out.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(gate.LiftingAblationError):
                gate.write_json(link, payload)

    def test_output_rejects_escape_without_mkdir(self) -> None:
        payload = gate.build_payload()
        with tempfile.TemporaryDirectory() as temp_dir:
            outside_dir = gate.pathlib.Path(temp_dir) / "outside"
            with self.assertRaises(gate.LiftingAblationError):
                gate.write_json(outside_dir / "out.json", payload)
            self.assertFalse(outside_dir.exists())


if __name__ == "__main__":
    unittest.main()
