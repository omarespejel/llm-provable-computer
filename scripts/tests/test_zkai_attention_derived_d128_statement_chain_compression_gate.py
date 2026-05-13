import copy
import json
import pathlib
import tempfile
import unittest

from scripts import zkai_attention_derived_d128_statement_chain_compression_gate as gate


class AttentionDerivedD128StatementChainCompressionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_builds_compressed_artifact_without_proof_overclaim(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload)

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertEqual(payload["claim_boundary"], gate.CLAIM_BOUNDARY)
        self.assertEqual(payload["case_count"], 22)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["source_chain"]["payload_commitment"], gate.EXPECTED_SOURCE_PAYLOAD)
        self.assertEqual(
            payload["summary"]["block_statement_commitment"],
            gate.EXPECTED_SOURCE_BLOCK_STATEMENT,
        )

        metrics = payload["compression_metrics"]
        self.assertEqual(metrics["source_chain_artifact_bytes"], 14624)
        self.assertEqual(metrics["compressed_artifact_bytes"], 2559)
        self.assertEqual(metrics["byte_savings"], 12065)
        self.assertEqual(metrics["compressed_to_source_ratio"], 0.174986)
        self.assertIsNone(metrics["proof_size_metrics"])
        self.assertIn("not proof-size evidence", payload["non_claims"])

    def test_mutation_inventory_is_stable(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(tuple(payload["mutation_inventory"]), gate.EXPECTED_MUTATIONS)
        self.assertEqual([case["name"] for case in payload["cases"]], list(gate.EXPECTED_MUTATIONS))
        self.assertTrue(all(case["rejected"] and not case["accepted"] for case in payload["cases"]))

    def test_rejects_commitment_and_metric_drift(self) -> None:
        payload = self.fresh_payload()
        payload["compressed_artifact"]["compressed_artifact_commitment"] = "blake2b-256:" + "00" * 32
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, "compressed artifact"):
            gate.validate_payload(payload)

        payload = self.fresh_payload()
        payload["compression_metrics"]["proof_size_metrics"] = {"proof_bytes": 1}
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, "proof size metric"):
            gate.validate_payload(payload)

        payload = self.fresh_payload()
        payload["summary"]["source_relation_rows"] = 1
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, "summary source relation"):
            gate.validate_payload(payload)

    def test_source_summary_rejects_upstream_drift(self) -> None:
        source = gate.load_json(gate.SOURCE_CHAIN)
        source["summary"]["block_statement_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, "source summary statement"):
            gate.source_summary(source)

        source = gate.load_json(gate.SOURCE_CHAIN)
        source["summary"]["edge_count"] = 10
        with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, "source edge count"):
            gate.source_summary(source)

    def test_tsv_contains_single_summary_row(self) -> None:
        tsv = gate.to_tsv(self.fresh_payload())
        self.assertIn("source_chain_artifact_bytes\tcompressed_artifact_bytes\tbyte_savings", tsv)
        self.assertIn("14624\t2559\t12065\t0.174986\t22", tsv)

    def test_rejects_recommitted_public_input_drift(self) -> None:
        payload = self.fresh_payload()
        required = payload["compressed_artifact"]["preimage"]["required_public_inputs"]
        required["derived_hidden_activation_commitment"] = "blake2b-256:" + "44" * 32
        payload["compressed_artifact"]["compressed_artifact_commitment"] = gate.blake2b_commitment(
            payload["compressed_artifact"]["preimage"], gate.COMPRESSED_ARTIFACT_DOMAIN
        )
        payload["verifier_handle"]["preimage"]["accepted_artifact_commitment"] = payload["compressed_artifact"][
            "compressed_artifact_commitment"
        ]
        payload["verifier_handle"]["preimage"]["required_public_inputs"] = copy.deepcopy(required)
        payload["verifier_handle"]["verifier_handle_commitment"] = gate.blake2b_commitment(
            payload["verifier_handle"]["preimage"], gate.VERIFIER_HANDLE_DOMAIN
        )
        payload["payload_commitment"] = gate.payload_commitment(payload)

        with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, "public input drift"):
            gate.validate_payload(payload)

    def test_rejects_recommitted_source_artifact_drift(self) -> None:
        payload = self.fresh_payload()
        payload["compressed_artifact"]["preimage"]["source_artifact"]["file_sha256"] = "sha256:" + "44" * 32
        payload["compressed_artifact"]["compressed_artifact_commitment"] = gate.blake2b_commitment(
            payload["compressed_artifact"]["preimage"], gate.COMPRESSED_ARTIFACT_DOMAIN
        )
        payload["verifier_handle"]["preimage"]["accepted_artifact_commitment"] = payload["compressed_artifact"][
            "compressed_artifact_commitment"
        ]
        payload["verifier_handle"]["verifier_handle_commitment"] = gate.blake2b_commitment(
            payload["verifier_handle"]["preimage"], gate.VERIFIER_HANDLE_DOMAIN
        )
        payload["payload_commitment"] = gate.payload_commitment(payload)

        with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, "source artifact drift"):
            gate.validate_payload(payload)

    def test_write_outputs_round_trip_and_rejects_bad_paths(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "compression.json"
            tsv_path = tmp / "compression.tsv"
            gate.write_outputs(payload, json_path, tsv_path)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), payload)
            self.assertIn("byte_savings", tsv_path.read_text(encoding="utf-8"))

            with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, ".json"):
                gate.write_outputs(payload, tmp / "bad.txt", None)

        with tempfile.TemporaryDirectory() as raw_tmp:
            with self.assertRaisesRegex(gate.AttentionDerivedD128StatementChainCompressionError, "evidence"):
                gate.write_outputs(payload, pathlib.Path(raw_tmp) / "outside.json", None)


if __name__ == "__main__":
    unittest.main()
