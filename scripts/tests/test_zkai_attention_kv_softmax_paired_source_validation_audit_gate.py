import copy
import json
import tempfile
import unittest

from scripts import zkai_attention_kv_air_private_softmax_table_lookup_gate as d8_sidecar
from scripts import zkai_attention_kv_d8_fused_softmax_table_native_gate as d8_fused
from scripts import zkai_attention_kv_softmax_paired_source_validation_audit_gate as gate


class AttentionKvSoftmaxPairedSourceValidationAuditGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = gate.build_result()

    def test_build_result_rejects_all_paired_source_mutations(self):
        gate.validate_result(self.result)
        self.assertEqual(self.result["decision"], gate.DECISION)
        self.assertEqual(self.result["targets_checked"], 11)
        self.assertEqual(self.result["targets_rejected"], 11)
        self.assertEqual(self.result["accepted_targets"], [])
        self.assertEqual(self.result["sidecar_targets_checked"], 5)
        self.assertEqual(self.result["fused_targets_checked"], 6)
        self.assertIn("NOT_NEW_PROOF", self.result["claim_boundary"])

    def test_rejects_target_acceptance_drift(self):
        mutated = copy.deepcopy(self.result)
        mutated["target_results"][0]["rejected"] = False
        mutated["targets_rejected"] -= 1
        mutated["accepted_targets"] = [mutated["target_results"][0]["target_id"]]
        with self.assertRaisesRegex(gate.PairedSourceValidationAuditGateError, "result drift for targets_rejected"):
            gate.validate_result(mutated)

    def test_rejects_target_order_drift(self):
        mutated = copy.deepcopy(self.result)
        mutated["target_results"] = list(reversed(mutated["target_results"]))
        with self.assertRaisesRegex(gate.PairedSourceValidationAuditGateError, "target result order drift"):
            gate.validate_result(mutated)

    def test_sidecar_direct_validator_rejects_matching_malformed_pair(self):
        source_input = d8_sidecar.read_bounded_json(
            d8_sidecar.SOURCE_INPUT_JSON, d8_sidecar.MAX_SOURCE_INPUT_JSON_BYTES, "source input"
        )
        envelope = d8_sidecar.read_bounded_json(
            d8_sidecar.LOOKUP_ENVELOPE_JSON, d8_sidecar.MAX_LOOKUP_ENVELOPE_JSON_BYTES, "lookup envelope"
        )
        source_input = gate.mutate_source(source_input)
        envelope = copy.deepcopy(envelope)
        envelope["source_input"] = source_input
        with self.assertRaisesRegex(d8_sidecar.AttentionKvAirPrivateSoftmaxTableLookupGateError, "source input"):
            d8_sidecar.validate_lookup_envelope(envelope, source_input, d8_sidecar.LOOKUP_ENVELOPE_SIZE_BYTES)

    def test_fused_direct_validator_rejects_matching_malformed_pair(self):
        source_input = d8_fused.read_bounded_json(
            d8_fused.SOURCE_INPUT_JSON, d8_fused.MAX_SOURCE_INPUT_JSON_BYTES, "source input"
        )
        envelope = d8_fused.read_bounded_json(
            d8_fused.FUSED_ENVELOPE_JSON, d8_fused.MAX_FUSED_ENVELOPE_JSON_BYTES, "fused envelope"
        )
        source_input = gate.mutate_source(source_input)
        envelope = copy.deepcopy(envelope)
        envelope["source_input"] = source_input
        with self.assertRaisesRegex(d8_fused.AttentionKvD8FusedSoftmaxTableGateError, "source input"):
            d8_fused.validate_fused_envelope(envelope, source_input, run_native=False)

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = gate.pathlib.Path(tmp)
            json_path = tmp_path / "paired-source-audit.json"
            tsv_path = tmp_path / "paired-source-audit.tsv"
            gate.write_json(json_path, self.result)
            gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            gate.validate_result(loaded)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn(gate.DECISION, tsv)
            self.assertIn("11", tsv)
            self.assertIn(gate.MUTATION, tsv)


if __name__ == "__main__":
    unittest.main()
