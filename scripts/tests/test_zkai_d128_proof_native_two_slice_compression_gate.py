from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_proof_native_two_slice_compression_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_proof_native_two_slice_compression_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 proof-native two-slice compression gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128ProofNativeTwoSliceCompressionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_narrow_compression_go_and_recursive_no_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["issue"], 424)
        self.assertEqual(payload["compression_result"], GATE.COMPRESSION_RESULT)
        self.assertEqual(payload["recursive_or_pcd_result"], GATE.RECURSIVE_OR_PCD_RESULT)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertEqual(payload["summary"]["selected_checked_rows"], 256)
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_compressed_artifact_is_smaller_than_source_accumulator(self) -> None:
        metrics = self.fresh_payload()["compression_status"]["compression_metrics"]
        self.assertEqual(metrics["timing_mode"], "not_timed")
        self.assertIsNone(metrics["recursive_proof_metrics"])
        self.assertGreater(metrics["source_accumulator_artifact_serialized_bytes"], metrics["compressed_artifact_serialized_bytes"])
        self.assertEqual(
            metrics["byte_savings"],
            metrics["source_accumulator_artifact_serialized_bytes"] - metrics["compressed_artifact_serialized_bytes"],
        )
        self.assertLess(metrics["artifact_bytes_ratio_vs_source_accumulator"], 1.0)

    def test_public_input_contract_binds_target_slices_sources_and_backend(self) -> None:
        payload = self.fresh_payload()
        public_inputs = payload["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]
        transcript = payload["compressed_artifact"]["preimage"]["compressed_transcript"]
        self.assertEqual(public_inputs["two_slice_target_commitment"], payload["source_accumulator"]["two_slice_target_commitment"])
        self.assertEqual(
            public_inputs["required_public_inputs"],
            [
                "two_slice_target_commitment",
                "selected_slice_statement_commitments",
                "selected_source_evidence_hashes",
                "selected_slice_public_instance_commitments",
                "selected_slice_proof_native_parameter_commitments",
                "verifier_domain",
                "required_backend_version",
                "source_accumulator_commitment",
                "source_verifier_handle_commitment",
            ],
        )
        self.assertEqual(
            public_inputs["selected_slice_statement_commitments"],
            [{"slice_id": entry["slice_id"], "statement_commitment": entry["statement_commitment"]} for entry in transcript],
        )
        self.assertEqual(
            public_inputs["selected_source_evidence_hashes"],
            [
                {
                    "slice_id": entry["slice_id"],
                    "source_file_sha256": entry["source_file_sha256"],
                    "source_payload_sha256": entry["source_payload_sha256"],
                }
                for entry in transcript
            ],
        )
        self.assertEqual(
            public_inputs["selected_slice_public_instance_commitments"],
            [{"slice_id": entry["slice_id"], "public_instance_commitment": entry["public_instance_commitment"]} for entry in transcript],
        )
        self.assertEqual(
            public_inputs["selected_slice_proof_native_parameter_commitments"],
            [
                {"slice_id": entry["slice_id"], "proof_native_parameter_commitment": entry["proof_native_parameter_commitment"]}
                for entry in transcript
            ],
        )
        self.assertEqual(public_inputs["source_accumulator_commitment"], payload["source_accumulator"]["accumulator_commitment"])
        self.assertEqual(public_inputs["source_verifier_handle_commitment"], payload["source_accumulator"]["verifier_handle_commitment"])

    def test_compressed_artifact_and_verifier_handle_commitments_round_trip(self) -> None:
        payload = self.fresh_payload()
        source = GATE.load_checked_accumulator()
        artifact = payload["compressed_artifact"]
        GATE.verify_compressed_artifact(artifact, source)
        self.assertEqual(
            artifact["compressed_artifact_commitment"],
            GATE.blake2b_commitment(artifact["preimage"], GATE.COMPRESSED_ARTIFACT_DOMAIN),
        )
        handle = payload["verifier_handle"]
        GATE.verify_verifier_handle(handle, artifact, source)
        self.assertEqual(
            handle["verifier_handle_commitment"],
            GATE.blake2b_commitment(handle["preimage"], GATE.VERIFIER_HANDLE_DOMAIN),
        )
        self.assertTrue(handle["accepted"])

    def test_recursive_or_pcd_metrics_remain_blocked(self) -> None:
        status = self.fresh_payload()["recursive_or_pcd_status"]
        self.assertFalse(status["recursive_outer_proof_claimed"])
        self.assertFalse(status["pcd_outer_proof_claimed"])
        self.assertFalse(status["stark_in_stark_claimed"])
        self.assertEqual(status["outer_proof_artifacts"], [])
        self.assertTrue(all(value is None for value in status["proof_metrics"].values()))
        self.assertIn("no executable recursive/PCD", status["first_blocker"])

    def test_mutation_inventory_covers_binding_compression_and_non_claim_surfaces(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        expected_layers = {
            "source_accumulator_commitment_drift": "source_accumulator",
            "compressed_artifact_commitment_drift": "compressed_artifact",
            "compressed_public_target_commitment_drift": "compressed_artifact",
            "compressed_selected_source_hash_drift": "compressed_artifact",
            "compressed_verifier_domain_drift": "compressed_artifact",
            "compressed_backend_version_drift": "compressed_artifact",
            "compressed_slice_removed": "compressed_artifact",
            "compression_ratio_relabeling": "compression_metrics",
            "verifier_handle_artifact_commitment_drift": "verifier_handle",
            "recursive_outer_proof_claimed": "recursive_or_pcd_status",
            "recursive_proof_metric_smuggled": "recursive_or_pcd_status",
            "recursive_result_changed_to_go": "parser_or_schema",
        }
        for mutation, layer in expected_layers.items():
            with self.subTest(mutation=mutation):
                self.assertTrue(cases[mutation]["rejected"])
                self.assertEqual(cases[mutation]["rejection_layer"], layer)

    def test_rejects_target_statement_and_source_relabeling(self) -> None:
        mutations = [
            lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"].__setitem__(
                "two_slice_target_commitment", "blake2b-256:" + "11" * 32
            ),
            lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]["selected_slice_statement_commitments"][0].__setitem__(
                "statement_commitment", "blake2b-256:" + "22" * 32
            ),
            lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]["selected_source_evidence_hashes"][0].__setitem__(
                "source_payload_sha256", "33" * 32
            ),
        ]
        for mutate in mutations:
            payload = self.fresh_payload()
            mutate(payload)
            with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "compressed artifact"):
                GATE.validate_payload(payload)

    def test_rejects_backend_domain_and_verifier_handle_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]["verifier_domain"] = "ptvm:tampered:v0"
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "compressed artifact"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["verifier_handle"]["preimage"]["accepted_artifact_commitment"] = "blake2b-256:" + "44" * 32
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "verifier handle"):
            GATE.validate_payload(payload)

    def test_rejects_recursive_claim_or_metric_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["recursive_or_pcd_status"]["recursive_outer_proof_claimed"] = True
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "recursive or PCD status"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["recursive_or_pcd_status"]["proof_metrics"]["recursive_verifier_time_ms"] = 1.0
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "recursive or PCD status"):
            GATE.validate_payload(payload)

    def test_rejects_unknown_top_level_and_nested_keys(self) -> None:
        payload = self.fresh_payload()
        payload["unexpected"] = True
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "keys mismatch"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]["unexpected"] = True
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "keys mismatch"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][0]["unexpected"] = True
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "mutation case 0 keys mismatch"):
            GATE.validate_payload(payload)

    def test_rejects_partial_duplicate_and_tampered_mutation_metadata(self) -> None:
        payload = self.fresh_payload()
        del payload["cases"]
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "mutation metadata"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][1] = copy.deepcopy(payload["cases"][0])
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "duplicate mutation case"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][0]["error"] = "rewritten error"
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "mutation case 0 error"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips_under_evidence_dir(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "compression.json").relative_to(GATE.ROOT)
            tsv_path = (tmp / "compression.tsv").relative_to(GATE.ROOT)
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads((GATE.ROOT / json_path).read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("recursive_result_changed_to_go", (GATE.ROOT / tsv_path).read_text(encoding="utf-8"))

    def test_write_outputs_rejects_unsafe_paths(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "repo-relative"):
                GATE.write_outputs(payload, pathlib.Path(raw_tmp) / "compression.json", None)
            json_target = pathlib.Path(raw_tmp) / "compression.json"
            tsv_link = pathlib.Path(raw_tmp) / "compression.tsv"
            try:
                tsv_link.symlink_to(json_target)
            except OSError:
                self.skipTest("symlink creation not supported in this environment")
            with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "distinct"):
                GATE.write_outputs(payload, json_target.relative_to(GATE.ROOT), tsv_link.relative_to(GATE.ROOT))

        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "without traversal"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/evidence/../compression.json"), None)
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "docs/engineering/evidence"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/not-evidence/compression.json"), None)
        with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "end in .json"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/evidence/compression.txt"), None)

        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp, tempfile.TemporaryDirectory(dir=GATE.ROOT) as outside:
            link = pathlib.Path(raw_tmp) / "link.json"
            try:
                link.symlink_to(pathlib.Path(outside) / "escaped.json")
            except OSError:
                self.skipTest("symlink creation not supported in this environment")
            with self.assertRaisesRegex(GATE.D128ProofNativeTwoSliceCompressionError, "docs/engineering/evidence"):
                GATE.write_outputs(payload, link.relative_to(GATE.ROOT), None)


if __name__ == "__main__":
    unittest.main()
