import copy
import json
import pathlib
import tempfile
import unittest

from scripts import zkai_attention_derived_d128_outer_proof_route_gate as gate


class AttentionDerivedD128OuterProofRouteGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_builds_no_go_outer_proof_route_with_input_contract(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload)

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertEqual(payload["summary"]["input_contract_status"], gate.INPUT_CONTRACT_RESULT)
        self.assertEqual(payload["summary"]["outer_proof_status"], gate.OUTER_PROOF_RESULT)
        self.assertEqual(payload["summary"]["block_statement_commitment"], gate.EXPECTED_BLOCK_STATEMENT)
        self.assertEqual(payload["summary"]["source_chain_artifact_bytes"], 14624)
        self.assertEqual(payload["summary"]["compressed_artifact_bytes"], 2559)
        self.assertEqual(payload["summary"]["byte_savings"], 12065)
        self.assertEqual(payload["summary"]["source_relation_rows"], 199553)
        self.assertEqual(payload["summary"]["slice_count"], 6)
        self.assertEqual(payload["summary"]["edge_count"], 11)
        self.assertEqual(payload["case_count"], 28)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertIsNone(payload["outer_proof_attempt"]["proof_metrics"])
        self.assertEqual(payload["outer_proof_attempt"]["outer_proof_artifacts"], [])

    def test_mutation_inventory_is_stable(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(tuple(payload["mutation_inventory"]), gate.EXPECTED_MUTATIONS)
        self.assertEqual([case["name"] for case in payload["cases"]], list(gate.EXPECTED_MUTATIONS))
        self.assertTrue(all(case["rejected"] and not case["accepted"] for case in payload["cases"]))

    def test_rejects_recommitted_contract_public_input_drift(self) -> None:
        payload = self.fresh_payload()
        required = payload["input_contract"]["preimage"]["required_public_inputs"]
        required["derived_hidden_activation_commitment"] = "blake2b-256:" + "44" * 32
        payload["input_contract"]["input_contract_commitment"] = gate.blake2b_commitment(
            payload["input_contract"]["preimage"], gate.INPUT_CONTRACT_DOMAIN
        )
        payload["payload_commitment"] = gate.payload_commitment(payload)

        with self.assertRaisesRegex(gate.AttentionDerivedD128OuterProofRouteError, "input contract drift"):
            gate.validate_payload(payload)

    def test_rejects_proof_metric_smuggling_before_outer_proof(self) -> None:
        payload = self.fresh_payload()
        payload["outer_proof_attempt"]["proof_metrics"] = {"proof_bytes": 1}
        payload["payload_commitment"] = gate.payload_commitment(payload)

        with self.assertRaisesRegex(gate.AttentionDerivedD128OuterProofRouteError, "proof metric"):
            gate.validate_payload(payload)

    def test_rejects_missing_mutation_audit_fields(self) -> None:
        payload = self.fresh_payload()
        for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected"):
            payload.pop(field)
        payload["payload_commitment"] = gate.payload_commitment(payload)

        with self.assertRaisesRegex(gate.AttentionDerivedD128OuterProofRouteError, "missing finalized field"):
            gate.validate_payload(payload)

    def test_rejects_expected_candidate_directory(self) -> None:
        original_root = gate.ROOT
        original_specs = gate.CANDIDATE_SPECS
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            (tmp / "candidate").mkdir()
            gate.ROOT = tmp
            gate.CANDIDATE_SPECS = (
                {
                    "name": "expected_candidate",
                    "path": "candidate",
                    "expected_exists": True,
                },
            )
            try:
                with self.assertRaisesRegex(gate.AttentionDerivedD128OuterProofRouteError, "candidate must be a file"):
                    gate.build_candidate_inventory()
            finally:
                gate.ROOT = original_root
                gate.CANDIDATE_SPECS = original_specs

    def test_rejects_missing_expected_candidate_separately(self) -> None:
        original_root = gate.ROOT
        original_specs = gate.CANDIDATE_SPECS
        with tempfile.TemporaryDirectory() as raw_tmp:
            gate.ROOT = pathlib.Path(raw_tmp)
            gate.CANDIDATE_SPECS = (
                {
                    "name": "missing_candidate",
                    "path": "candidate",
                    "expected_exists": True,
                },
            )
            try:
                with self.assertRaisesRegex(gate.AttentionDerivedD128OuterProofRouteError, "existence drift"):
                    gate.build_candidate_inventory()
            finally:
                gate.ROOT = original_root
                gate.CANDIDATE_SPECS = original_specs

    def test_tsv_contains_single_summary_row(self) -> None:
        tsv = gate.to_tsv(self.fresh_payload())
        self.assertIn("input_contract_commitment\touter_proof_status", tsv)
        self.assertIn("NO_GO_EXECUTABLE_ATTENTION_DERIVED_D128_OUTER_PROOF_BACKEND_MISSING", tsv)
        self.assertIn("\t14624\t2559\t12065\t199553\t28", tsv)

    def test_write_outputs_round_trip_and_rejects_bad_paths(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "outer-route.json"
            tsv_path = tmp / "outer-route.tsv"
            gate.write_outputs(payload, json_path, tsv_path)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), payload)
            self.assertIn("byte_savings", tsv_path.read_text(encoding="utf-8"))

            with self.assertRaisesRegex(gate.AttentionDerivedD128OuterProofRouteError, "failed|output path"):
                gate.write_outputs(payload, tmp / "bad.txt", None)

        with tempfile.TemporaryDirectory() as raw_tmp:
            with self.assertRaisesRegex(gate.AttentionDerivedD128OuterProofRouteError, "failed|evidence"):
                gate.write_outputs(payload, pathlib.Path(raw_tmp) / "outside.json", None)


if __name__ == "__main__":
    unittest.main()
