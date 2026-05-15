import copy
import tempfile
import unittest
from unittest import mock

from scripts import zkai_d128_gate_value_activation_fused_gate as gate


class GateValueActivationFusedGateTests(unittest.TestCase):
    def test_payload_records_expected_typed_saving(self) -> None:
        payload = gate.build_payload()
        aggregate = payload["aggregate"]
        self.assertEqual(aggregate["fused_local_typed_bytes"], 17_760)
        self.assertEqual(aggregate["separate_local_typed_bytes"], 23_280)
        self.assertEqual(aggregate["typed_saving_vs_separate_bytes"], 5_520)
        self.assertEqual(aggregate["typed_ratio_vs_separate"], 0.762887)
        gate.validate_payload(payload)

    def test_mutations_reject(self) -> None:
        payload = gate.build_payload()
        result = gate.run_mutations(payload)
        self.assertEqual(result["case_count"], len(gate.MUTATION_NAMES))
        self.assertTrue(result["all_mutations_rejected"])

    def test_claim_boundary_overclaim_rejects(self) -> None:
        payload = gate.build_payload()
        payload["claim_boundary"] = "FULL_D128_TRANSFORMER_BLOCK_PROOF"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaises(gate.FusedGateError):
            gate.validate_payload(payload)

    def test_grouped_delta_drift_rejects(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["grouped_delta_vs_separate_bytes"]["trace_decommitments"] = -1
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaises(gate.FusedGateError):
            gate.validate_payload(mutated)

    def test_evidence_path_drift_rejects(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["evidence"]["fused_envelope"] = "docs/engineering/evidence/other.json"
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaises(gate.FusedGateError):
            gate.validate_payload(mutated)

    def test_read_json_open_error_is_structured(self) -> None:
        with mock.patch.object(gate.os, "open", side_effect=OSError("boom")):
            with self.assertRaises(gate.FusedGateError):
                gate.read_json(gate.ACCOUNTING_PATH, 4 * 1024 * 1024, "accounting JSON")

    def test_read_json_rejects_non_finite_constants(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            path = gate.pathlib.Path(temp_dir) / "nan.json"
            path.write_text('{"bad": NaN}', encoding="utf-8")
            with self.assertRaises(gate.FusedGateError):
                gate.read_json(path, 1024, "nan JSON")

    def test_validate_envelope_stat_error_is_structured(self) -> None:
        expected = gate.EXPECTED_ROLES[gate.FUSED_ENVELOPE_PATH.name]
        with self.assertRaises(gate.FusedGateError):
            gate.validate_envelope(gate.EVIDENCE_DIR / "__missing_d128_fused_envelope.json", expected)

    def test_atomic_output_rejects_symlink(self) -> None:
        payload = gate.build_payload()
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as temp_dir:
            temp_path = gate.pathlib.Path(temp_dir)
            target = temp_path / "target.json"
            link = temp_path / "out.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(gate.FusedGateError):
                gate.write_json(link, payload)


if __name__ == "__main__":
    unittest.main()
