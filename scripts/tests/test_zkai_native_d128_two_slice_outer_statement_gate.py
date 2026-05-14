import copy
import json
import unittest

from scripts import zkai_native_d128_two_slice_outer_statement_gate as gate
from scripts import zkai_native_d128_two_slice_outer_statement_input as input_builder


class NativeD128TwoSliceOuterStatementGateTests(unittest.TestCase):
    def test_input_builder_records_host_verified_non_claim(self) -> None:
        input_obj = input_builder.build_input()
        self.assertEqual(
            input_obj["decision"],
            "NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_INPUT",
        )
        self.assertEqual(input_obj["selected_checked_rows"], 256)
        self.assertEqual(
            input_obj["selected_slice_ids"],
            ["rmsnorm_public_rows", "rmsnorm_projection_bridge"],
        )
        self.assertIn(
            "not native verifier execution of the selected inner Stwo proofs",
            input_obj["non_claims"],
        )

    def test_input_builder_escapes_commitment_payload_strings(self) -> None:
        row = copy.deepcopy(input_builder.ROWS[0])
        row["slice_id"] = 'slice"with\\json'
        payload = input_builder.row_statement_json(row)
        self.assertEqual(json.loads(payload)["slice_id"], row["slice_id"])

    def test_gate_records_narrow_go_without_nanozk_win(self) -> None:
        result = gate.build_gate()
        self.assertEqual(
            result["result"],
            "NARROW_GO_NATIVE_STWO_OUTER_STATEMENT_BINDING_NOT_VERIFIER_EXECUTION",
        )
        self.assertEqual(result["metrics"]["native_outer_statement_proof_bytes"], 3516)
        self.assertEqual(result["metrics"]["proof_vs_nanozk_reported_row_ratio"], 0.509565)
        self.assertEqual(result["metrics"]["proof_saving_vs_prior_uncompressed_bytes"], 7525)
        self.assertEqual(result["metrics"]["proof_saving_vs_prior_uncompressed_share"], 0.681551)
        self.assertEqual(result["case_count"], 28)
        self.assertIn("proof_backend_version_relabelled_as_uncompressed_v1", result["mutation_inventory"])
        self.assertIn("compressed_public_instance_commitment_drift", result["mutation_inventory"])
        self.assertIn("compressed_proof_native_parameter_commitment_drift", result["mutation_inventory"])
        self.assertIn("not a NANOZK proof-size win", result["non_claims"])
        self.assertIn(
            "not a matched NANOZK proof-size win even though this payload is smaller than NANOZK's paper-reported row",
            result["non_claims"],
        )
        self.assertIn("not stable binary proof-size accounting", result["non_claims"])
        self.assertIn("just gate-fast", result["validation_commands"])

    def test_same_output_path_resolves_aliases(self) -> None:
        alias = gate.ROOT / "." / gate.JSON_OUT.relative_to(gate.ROOT)
        self.assertTrue(gate.same_output_path(gate.JSON_OUT, alias))

    def test_gate_rejects_artifact_relabeling(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        envelope["decision"] = "GO_NATIVE_VERIFIER_EXECUTION"
        with self.assertRaises(gate.OuterStatementGateError):
            gate.validate_artifact(envelope, input_obj)

    def test_gate_rejects_unknown_envelope_key(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        envelope["unexpected_claim"] = "native verifier execution"
        with self.assertRaisesRegex(gate.OuterStatementGateError, "envelope keys mismatch"):
            gate.validate_artifact(envelope, input_obj)

    def test_gate_rejects_list_reordering_even_when_envelope_matches(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        input_obj["proof_verifier_hardening"] = list(reversed(input_obj["proof_verifier_hardening"]))
        envelope["input"] = input_obj
        with self.assertRaisesRegex(gate.OuterStatementGateError, "proof verifier hardening mismatch"):
            gate.validate_artifact(envelope, input_obj)

    def test_gate_rejects_proof_byte_tamper(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        envelope["proof"][0] = (envelope["proof"][0] + 1) % 256
        with self.assertRaises(gate.OuterStatementGateError):
            gate.validate_artifact(envelope, input_obj)

    def test_gate_rejects_compressed_public_instance_commitment_tamper(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        input_obj["public_instance_commitment"] = "blake2b-256:" + "11" * 32
        envelope["input"] = input_obj
        with self.assertRaisesRegex(gate.OuterStatementGateError, "public instance commitment mismatch"):
            gate.validate_artifact(envelope, input_obj)

    def test_gate_rejects_compressed_proof_parameter_commitment_tamper(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        input_obj["proof_native_parameter_commitment"] = "blake2b-256:" + "22" * 32
        envelope["input"] = input_obj
        with self.assertRaisesRegex(gate.OuterStatementGateError, "proof-native parameter commitment mismatch"):
            gate.validate_artifact(envelope, input_obj)

    def test_gate_rejects_legacy_uncompressed_proof_version_relabel(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        envelope["proof_backend_version"] = "stwo-d128-two-slice-outer-statement-air-proof-v1"
        with self.assertRaisesRegex(gate.OuterStatementGateError, "proof backend version mismatch"):
            gate.validate_artifact(envelope, input_obj)

    def test_gate_rejects_source_hash_drift(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        envelope["input"]["rows"][0]["source_payload_sha256"] = "aa" * 32
        with self.assertRaises(gate.OuterStatementGateError):
            gate.validate_artifact(envelope, input_obj)

    def test_all_declared_mutations_reject(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        cases = gate.run_mutations(copy.deepcopy(envelope), input_obj)
        self.assertEqual(len(cases), len(gate.mutations()))
        self.assertTrue(all(case["rejected"] for case in cases))

    def test_run_mutations_propagates_non_domain_errors(self) -> None:
        input_obj = gate.load_json(gate.INPUT_JSON)
        envelope = gate.load_json(gate.ENVELOPE_JSON)
        original_validate = gate.validate_artifact
        try:
            gate.validate_artifact = lambda _envelope, _input_obj: (_ for _ in ()).throw(RuntimeError("boom"))
            with self.assertRaises(RuntimeError):
                gate.run_mutations(copy.deepcopy(envelope), input_obj)
        finally:
            gate.validate_artifact = original_validate


if __name__ == "__main__":
    unittest.main()
