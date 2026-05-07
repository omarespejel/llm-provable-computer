import copy
import tempfile
import unittest

from scripts import zkai_attention_kv_two_head_air_private_softmax_table_lookup_gate as gate


class AttentionKvAirPrivateSoftmaxTableLookupGateTests(unittest.TestCase):
    def strip_mutation_summary(self, payload):
        payload = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            payload.pop(key, None)
        return payload

    def assert_rejects(self, payload, message):
        with self.assertRaises(gate.AttentionKvAirPrivateSoftmaxTableLookupGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def test_build_payload_records_logup_sidecar_go(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        receipt = payload["lookup_receipt"]
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["lookup_status"], gate.LOOKUP_STATUS)
        self.assertEqual(payload["fused_component_status"], gate.FUSED_COMPONENT_STATUS)
        self.assertEqual(receipt["lookup_claims"], 104)
        self.assertEqual(receipt["table_rows"], 9)
        self.assertEqual(receipt["source_head_count"], 2)
        self.assertEqual(receipt["lookup_relation"], gate.LOOKUP_RELATION)
        self.assertEqual(receipt["lookup_relation_width"], 2)
        self.assertEqual(receipt["lookup_proof_size_bytes"], 18104)
        self.assertEqual(receipt["lookup_envelope_size_bytes"], 333577)
        self.assertEqual(receipt["lookup_proof_commitments"], 4)
        self.assertEqual(receipt["lookup_trace_commitments"], 3)
        self.assertEqual(sum(row["multiplicity"] for row in receipt["table_multiplicities"]), 104)
        self.assertEqual(receipt["table_multiplicities"][-1]["multiplicity"], 70)
        self.assertEqual(payload["single_head_comparison"]["single_head_lookup_claims"], 52)
        self.assertEqual(payload["single_head_comparison"]["proof_size_ratio"], "1.227806")
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_individual_mutations_reject(self):
        payload = gate.build_payload()
        for name in gate.EXPECTED_MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.AttentionKvAirPrivateSoftmaxTableLookupGateError, msg=name):
                gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_fused_component_overclaim(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["fused_component_status"] = "GO_FUSED_ATTENTION_ARITHMETIC_AND_LOOKUP_COMPONENT"
        self.assert_rejects(payload, "fused_component_status drift")

    def test_rejects_claim_boundary_exact_softmax_overclaim(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["claim_boundary"] = payload["claim_boundary"].replace("NOT_EXACT_SOFTMAX_", "")
        self.assert_rejects(payload, "claim_boundary drift")

    def test_rejects_table_multiplicity_drift(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["lookup_receipt"]["table_multiplicities"][0]["multiplicity"] += 1
        self.assert_rejects(payload, "lookup_receipt drift")

    def test_rejects_source_statement_relabeling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["lookup_receipt"]["source_statement_commitment"] = "blake2b-256:" + "aa" * 32
        self.assert_rejects(payload, "lookup_receipt drift")

    def test_rejects_lookup_receipt_unknown_field(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["lookup_receipt"]["unexpected"] = True
        self.assert_rejects(payload, "lookup_receipt drift")

    def test_rejects_mutation_summary_drift(self):
        payload = gate.build_payload()
        payload["mutation_cases"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.AttentionKvAirPrivateSoftmaxTableLookupGateError, "mutation rejection drift"):
            gate.validate_payload(payload)

    def test_rejects_mutation_spec_count_drift(self):
        original_names = gate.EXPECTED_MUTATION_NAMES
        try:
            gate.EXPECTED_MUTATION_NAMES = original_names[:-1]
            with self.assertRaisesRegex(gate.AttentionKvAirPrivateSoftmaxTableLookupGateError, "mutation spec count drift"):
                gate.validate_mutation_spec()
        finally:
            gate.EXPECTED_MUTATION_NAMES = original_names

    def test_rejects_float_encoded_lookup_claim_count(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["lookup_receipt"]["lookup_claims"] = 104.0
        self.assert_rejects(payload, "lookup_receipt drift")

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("18104", tsv)
        self.assertIn("1.227806", tsv)
        self.assertIn(gate.SOURCE_STATEMENT_COMMITMENT, tsv)

    def test_write_json_validates_before_writing(self):
        payload = gate.build_payload()
        payload["lookup_receipt"]["lookup_proof_size_bytes"] += 1
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.AttentionKvAirPrivateSoftmaxTableLookupGateError, "lookup_receipt drift"):
                gate.write_json(payload, gate.pathlib.Path(tmp) / "bad.json")


if __name__ == "__main__":
    unittest.main()
