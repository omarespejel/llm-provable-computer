import copy
import json
import pathlib
import subprocess
import tempfile
import unittest

from scripts import zkai_attention_kv_stwo_fine_grained_component_schema_gate as gate


class AttentionKvStwoFineGrainedComponentSchemaGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload_base = gate.build_payload()

    def setUp(self) -> None:
        self.payload = copy.deepcopy(self.payload_base)

    def strip_mutation_summary(self, payload):
        payload = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            payload.pop(key, None)
        return payload

    def assert_rejects(self, payload, message):
        with self.assertRaises(gate.StwoFineGrainedComponentSchemaGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True, expected_rows=self.payload["rows"])
        self.assertIn(message, str(ctx.exception))

    def test_records_fine_grained_schema_with_binary_serializer_no_go(self):
        payload = self.payload
        gate.validate_payload(payload, expected_rows=payload["rows"])
        aggregate = payload["aggregate"]

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["issue"], 534)
        self.assertEqual(payload["source_issues"], [469, 476, 531])
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["accounting_source"], gate.ACCOUNTING_SOURCE)
        self.assertEqual(payload["component_schema_status"], gate.COMPONENT_SCHEMA_STATUS)
        self.assertEqual(payload["stable_binary_serializer_status"], gate.STABLE_BINARY_SERIALIZER_STATUS)
        self.assertEqual(payload["grouped_reconstruction_status"], gate.GROUPED_RECONSTRUCTION_STATUS)
        self.assertEqual(
            payload["fine_grained_component_schema_commitment"],
            gate.EXPECTED_FINE_GRAINED_COMPONENT_SCHEMA_COMMITMENT,
        )
        self.assertEqual(payload["size_constants"], gate.SIZE_CONSTANTS)
        self.assertEqual(payload["open_component_questions"], list(gate.OPEN_COMPONENT_QUESTIONS))
        self.assertEqual(len(payload["rows"]), 27)
        self.assertEqual(payload["mutations_checked"], gate.EXPECTED_MUTATION_COUNT)
        self.assertEqual(payload["mutations_rejected"], gate.EXPECTED_MUTATION_COUNT)
        self.assertTrue(payload["all_mutations_rejected"])

        self.assertEqual(aggregate["role_totals"], gate.EXPECTED_ROLE_TOTALS)
        self.assertEqual(aggregate["source_plus_sidecar_minus_fused_delta"], gate.EXPECTED_DELTA_TOTALS)
        self.assertEqual(aggregate["typed_saving_share_vs_source_plus_sidecar"], 0.167376)
        self.assertEqual(aggregate["json_saving_share_vs_source_plus_sidecar"], 0.213636)
        self.assertEqual(aggregate["largest_component_saving_bucket"], "fri_decommitment_merkle_path_bytes")
        self.assertEqual(aggregate["largest_component_saving_bucket_bytes"], 17312)

    def test_rows_bind_component_sums_and_grouped_reconstruction(self):
        rows = {(row["profile_id"], row["role"]): row for row in self.payload["rows"]}
        source = rows[("d8_single_head_seq8", "source")]
        self.assertEqual(source["component_bytes"]["sampled_opened_value_bytes"], 8000)
        self.assertEqual(source["component_bytes"]["queried_value_bytes"], 6000)
        self.assertEqual(source["component_bytes"]["trace_decommitment_merkle_path_bytes"], 1536)
        self.assertEqual(source["component_sum_bytes"], source["typed_size_estimate_bytes"])
        self.assertEqual(source["grouped_reconstruction"], source["stwo_grouped_breakdown"])
        self.assertEqual(source["grouped_reconstruction"]["fixed_overhead"], 48)

        sixteen = rows[("d8_sixteen_head_seq8", "fused")]
        self.assertEqual(sixteen["typed_size_estimate_bytes"], 22660)
        self.assertEqual(sixteen["component_bytes"]["fri_decommitment_merkle_path_bytes"], 3744)
        self.assertEqual(sixteen["component_bytes"]["trace_decommitment_merkle_path_bytes"], 3584)

    def test_declared_mutations_reject(self):
        self.assertEqual([item["name"] for item in self.payload["mutation_cases"]], list(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(all(item["rejected"] is True for item in self.payload["mutation_cases"]))

    def test_rejects_metric_smuggling_and_overclaims(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["stable_binary_serializer_status"] = "GO_STABLE_BINARY_STWO_SERIALIZER"
        self.assert_rejects(payload, "stable_binary_serializer_status drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["component_schema_status"] = "GO_BINARY_COMPONENT_SCHEMA"
        self.assert_rejects(payload, "component_schema_status drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["open_component_questions"].pop()
        self.assert_rejects(payload, "open_component_questions drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["size_constants"]["secure_field_bytes"] = 15
        self.assert_rejects(payload, "size_constants drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["rows"][0]["typed_size_estimate_bytes"] += 1
        self.assert_rejects(payload, "component sum drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["rows"][0]["proof_sha256"] = "0" * 64
        with self.assertRaises(gate.StwoFineGrainedComponentSchemaGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn("commitment drift", str(ctx.exception))

        payload = self.strip_mutation_summary(self.payload)
        payload["rows"][0]["proof_sha256"] = "A" * 64
        self.assert_rejects(payload, "proof_sha256 must be a 64-char lowercase hex SHA-256 digest")

        payload = self.strip_mutation_summary(self.payload)
        payload["rows"][0]["component_bytes"]["fri_decommitment_merkle_path_bytes"] += 1
        self.assert_rejects(payload, "component sum drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["rows"][0]["grouped_reconstruction"]["fri_decommitments"] += 1
        self.assert_rejects(payload, "grouped reconstruction drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["rows"][0]["component_sum_bytes"] = float(payload["rows"][0]["component_sum_bytes"])
        self.assert_rejects(payload, "component_sum_bytes must be an integer")

        payload = self.strip_mutation_summary(self.payload)
        payload["rows"][0]["json_minus_typed_size_bytes"] = float(payload["rows"][0]["json_minus_typed_size_bytes"])
        self.assert_rejects(payload, "json_minus_typed_size_bytes must be an integer")

        payload = self.strip_mutation_summary(self.payload)
        payload["aggregate"]["source_plus_sidecar_minus_fused_delta"]["typed_size_estimate_bytes"] += 1
        self.assert_rejects(payload, "aggregate drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["rows"][0]["role"] = "different"
        self.assert_rejects(payload, "role drift")

    def test_tsv_summary_matches_payload(self):
        tsv = gate.to_tsv(self.payload, expected_rows=self.payload["rows"])
        self.assertIn("source", tsv)
        self.assertIn("201256", tsv)
        self.assertIn("fused", tsv)
        self.assertIn("211380", tsv)
        self.assertIn("fri_decommitment_merkle_path_bytes", tsv)

    def test_write_paths_are_constrained_to_evidence_dir(self):
        relative = pathlib.Path("docs/engineering/evidence/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.json")
        self.assertEqual(gate.require_output_path(relative), gate.JSON_OUT.resolve())

        with tempfile.TemporaryDirectory() as tmp:
            outside = pathlib.Path(tmp) / "out.json"
            with self.assertRaisesRegex(gate.StwoFineGrainedComponentSchemaGateError, "output path"):
                gate.write_outputs(self.payload, outside, gate.TSV_OUT)

    def test_artifact_specs_reject_paths_outside_evidence_dir(self):
        rows = copy.deepcopy(gate.section_delta_rows()[:1])
        rows[0]["artifacts"]["source"]["path"] = "../Cargo.toml"
        with self.assertRaisesRegex(
            gate.StwoFineGrainedComponentSchemaGateError,
            "d8_single_head_seq8/source escapes docs/engineering/evidence",
        ):
            gate.artifact_specs(rows)

    def test_rejects_cli_reported_proof_sha256_drift(self):
        original = gate.run_stwo_component_schema

        def fake_cli(paths):
            payload = original(paths)
            payload["rows"][0]["proof_sha256"] = "0" * 64
            return payload

        gate.run_stwo_component_schema = fake_cli
        try:
            with self.assertRaisesRegex(gate.StwoFineGrainedComponentSchemaGateError, "CLI proof_sha256 drift"):
                gate.build_rows()
        finally:
            gate.run_stwo_component_schema = original

    def test_rejects_cli_reported_json_proof_size_drift(self):
        original = gate.run_stwo_component_schema

        def fake_cli(paths):
            payload = original(paths)
            payload["rows"][0]["json_proof_size_bytes"] += 1
            return payload

        gate.run_stwo_component_schema = fake_cli
        try:
            with self.assertRaisesRegex(
                gate.StwoFineGrainedComponentSchemaGateError,
                "CLI json_proof_size_bytes drift",
            ):
                gate.build_rows()
        finally:
            gate.run_stwo_component_schema = original

    def test_artifact_proof_metadata_rejects_oversized_and_non_utf8_envelopes(self):
        original_cap = gate.MAX_ENVELOPE_JSON_BYTES
        with tempfile.TemporaryDirectory() as tmp:
            oversized = pathlib.Path(tmp) / "oversized.json"
            oversized.write_text('{"proof":[0]}', encoding="utf-8")
            gate.MAX_ENVELOPE_JSON_BYTES = 4
            try:
                with self.assertRaisesRegex(gate.StwoFineGrainedComponentSchemaGateError, "artifact envelope exceeds"):
                    gate.artifact_proof_metadata(str(oversized))
            finally:
                gate.MAX_ENVELOPE_JSON_BYTES = original_cap

            non_utf8 = pathlib.Path(tmp) / "non-utf8.json"
            non_utf8.write_bytes(b"\xff")
            with self.assertRaisesRegex(gate.StwoFineGrainedComponentSchemaGateError, "not valid UTF-8"):
                gate.artifact_proof_metadata(str(non_utf8))

            empty = pathlib.Path(tmp) / "empty.json"
            empty.touch()
            with self.assertRaisesRegex(gate.StwoFineGrainedComponentSchemaGateError, "artifact envelope is empty"):
                gate.artifact_proof_metadata(str(empty))

            with self.assertRaisesRegex(gate.StwoFineGrainedComponentSchemaGateError, "not a regular file"):
                gate.artifact_proof_metadata(tmp)

    def test_rust_cli_rejects_malformed_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / "bad-envelope.json"
            bad.write_text(json.dumps({"proof": [300]}), encoding="utf-8")
            completed = subprocess.run(
                [
                    "cargo",
                    "+nightly-2025-07-14",
                    "run",
                    "--quiet",
                    "--locked",
                    "--features",
                    "stwo-backend",
                    "--bin",
                    "zkai_stwo_proof_component_schema",
                    "--",
                    str(bad),
                ],
                cwd=gate.ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=gate.STWO_COMPONENT_SCHEMA_TIMEOUT_SECONDS,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("exceeds u8", completed.stderr)


if __name__ == "__main__":
    unittest.main()
