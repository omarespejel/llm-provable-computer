import copy
import json
import os
import tempfile
import unittest

from scripts import zkai_attention_kv_d32_air_private_softmax_table_lookup_gate as gate


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

    def same_digit_mutation(self, value):
        for candidate in (value + 1, value - 1):
            if 0 <= candidate <= 255 and len(str(candidate)) == len(str(value)):
                return candidate
        self.fail(f"no same-digit mutation available for {value}")

    def same_size_tampered_envelope_json(self):
        envelope = json.loads(gate.LOOKUP_ENVELOPE_JSON.read_text(encoding="utf-8"))
        proof_payload = json.loads(bytes(envelope["proof"]).decode("utf-8"))
        commitments = proof_payload["stark_proof"]["commitments"]
        commitments[0][0] = self.same_digit_mutation(commitments[0][0])
        proof_bytes = json.dumps(proof_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(len(proof_bytes), len(envelope["proof"]))
        envelope["proof"] = list(proof_bytes)
        serialized = json.dumps(envelope, indent=2, sort_keys=True)
        self.assertEqual(len(serialized.encode("utf-8")), gate.LOOKUP_ENVELOPE_SIZE_BYTES)
        return serialized

    def test_build_payload_records_logup_sidecar_go(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        receipt = payload["lookup_receipt"]
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["lookup_status"], gate.LOOKUP_STATUS)
        self.assertEqual(payload["fused_component_status"], gate.FUSED_COMPONENT_STATUS)
        self.assertEqual(receipt["lookup_claims"], 52)
        self.assertEqual(receipt["table_rows"], 9)
        self.assertEqual(receipt["lookup_relation"], gate.LOOKUP_RELATION)
        self.assertEqual(receipt["lookup_relation_width"], 2)
        self.assertEqual(receipt["lookup_proof_size_bytes"], 15562)
        self.assertEqual(receipt["lookup_envelope_size_bytes"], 379207)
        self.assertEqual(receipt["lookup_proof_commitments"], 4)
        self.assertEqual(receipt["lookup_trace_commitments"], 3)
        self.assertEqual(sum(row["multiplicity"] for row in receipt["table_multiplicities"]), 52)
        self.assertEqual(receipt["table_multiplicities"][-1]["multiplicity"], 43)
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
        payload["lookup_receipt"]["lookup_claims"] = 52.0
        self.assert_rejects(payload, "lookup_receipt drift")

    def test_native_verifier_rejects_same_size_tampered_proof_payload(self):
        serialized = self.same_size_tampered_envelope_json()
        with tempfile.TemporaryDirectory() as tmp:
            tampered = gate.pathlib.Path(tmp) / "same-size-tampered-envelope.json"
            tampered.write_text(serialized, encoding="utf-8")
            with self.assertRaisesRegex(
                gate.AttentionKvAirPrivateSoftmaxTableLookupGateError,
                "native lookup verifier rejected",
            ):
                gate.verify_lookup_envelope_with_native_cli(tampered)

    def test_native_verifier_cache_is_bound_to_exact_envelope_bytes(self):
        gate._LOOKUP_VERIFY_CACHE.clear()
        envelope = json.loads(gate.LOOKUP_ENVELOPE_JSON.read_text(encoding="utf-8"))
        original = json.dumps(envelope, indent=2, sort_keys=True)
        tampered = self.same_size_tampered_envelope_json()
        self.assertEqual(len(original.encode("utf-8")), len(tampered.encode("utf-8")))
        with tempfile.TemporaryDirectory() as tmp:
            path = gate.pathlib.Path(tmp) / "lookup-envelope.json"
            path.write_text(original, encoding="utf-8")
            gate.verify_lookup_envelope_with_native_cli(path)
            stat = path.stat()
            path.write_text(tampered, encoding="utf-8")
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            with self.assertRaisesRegex(
                gate.AttentionKvAirPrivateSoftmaxTableLookupGateError,
                "native lookup verifier rejected",
            ):
                gate.verify_lookup_envelope_with_native_cli(path)

    def test_rejects_embedded_source_input_float_and_bool_relabeling(self):
        source_input = json.loads(gate.SOURCE_INPUT_JSON.read_text(encoding="utf-8"))
        envelope = json.loads(gate.LOOKUP_ENVELOPE_JSON.read_text(encoding="utf-8"))
        for relabel in (8.0, True):
            mutated = copy.deepcopy(envelope)
            mutated["source_input"]["score_gap_clip"] = relabel
            with self.assertRaisesRegex(
                gate.AttentionKvAirPrivateSoftmaxTableLookupGateError,
                "lookup envelope source input split-brain drift",
            ):
                gate.validate_lookup_envelope(mutated, source_input, gate.LOOKUP_ENVELOPE_SIZE_BYTES)

    def test_rejects_matching_mutated_source_denominator_pair(self):
        source_input = json.loads(gate.SOURCE_INPUT_JSON.read_text(encoding="utf-8"))
        envelope = json.loads(gate.LOOKUP_ENVELOPE_JSON.read_text(encoding="utf-8"))
        mutated_source = copy.deepcopy(source_input)
        mutated_source["score_rows"][0]["weight_denominator"] = 0
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["source_input"] = mutated_source
        with self.assertRaisesRegex(
            gate.AttentionKvAirPrivateSoftmaxTableLookupGateError,
            "source input validation drift",
        ):
            gate.validate_lookup_envelope(mutated_envelope, mutated_source, gate.LOOKUP_ENVELOPE_SIZE_BYTES)

    def test_rejects_matching_mutated_source_remainder_pair(self):
        source_input = json.loads(gate.SOURCE_INPUT_JSON.read_text(encoding="utf-8"))
        envelope = json.loads(gate.LOOKUP_ENVELOPE_JSON.read_text(encoding="utf-8"))
        mutated_source = copy.deepcopy(source_input)
        mutated_source["score_rows"][0]["output_remainder"][0] = (
            mutated_source["score_rows"][0]["weight_denominator"]
        )
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["source_input"] = mutated_source
        with self.assertRaisesRegex(
            gate.AttentionKvAirPrivateSoftmaxTableLookupGateError,
            "source input validation drift",
        ):
            gate.validate_lookup_envelope(mutated_envelope, mutated_source, gate.LOOKUP_ENVELOPE_SIZE_BYTES)

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("15562", tsv)
        self.assertIn(gate.SOURCE_STATEMENT_COMMITMENT, tsv)

    def test_write_json_validates_before_writing(self):
        payload = gate.build_payload()
        payload["lookup_receipt"]["lookup_proof_size_bytes"] += 1
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.AttentionKvAirPrivateSoftmaxTableLookupGateError, "lookup_receipt drift"):
                gate.write_json(payload, gate.pathlib.Path(tmp) / "bad.json")


if __name__ == "__main__":
    unittest.main()
