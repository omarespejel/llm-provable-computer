import copy
import tempfile
import unittest

from scripts import zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate as gate


class NativeAttentionMlpVariantInvariantReprovePreflightGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_records_no_go_and_key_numbers(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload)
        summary = payload["summary"]

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertFalse(summary["stable_reprove_supported_by_current_source"])
        self.assertFalse(summary["compact_frontier_promoted"])
        self.assertEqual(summary["current_frontier_typed_bytes"], 41_932)
        self.assertEqual(summary["duplicate_label_control_typed_bytes"], 43_228)
        self.assertEqual(summary["compact_label_control_typed_bytes"], 42_492)
        self.assertEqual(summary["label_control_saving_bytes"], 736)
        self.assertEqual(summary["stable_floor_bytes"], 112)
        self.assertEqual(summary["path_sensitive_bytes_that_need_reprove"], 624)
        self.assertFalse(summary["nanozk_win_claimed"])

    def test_source_preflight_pins_current_backend_blocker(self) -> None:
        preflight = self.fresh_payload()["source_preflight"]

        self.assertTrue(preflight["duplicate_adapter_in_preprocessed_trace"])
        self.assertTrue(preflight["duplicate_adapter_in_base_trace"])
        self.assertTrue(preflight["source_comment_says_adapter_intentionally_duplicated"])
        self.assertTrue(preflight["adapter_trace_cells_compile_time_constant"])
        self.assertTrue(preflight["input_validation_pins_duplicate_adapter_trace_cells"])
        self.assertFalse(preflight["variant_selector_present"])
        self.assertFalse(preflight["compact_adapter_backend_present"])
        self.assertFalse(preflight["variant_invariant_policy_present"])
        self.assertFalse(preflight["multi_transcript_policy_present"])

    def test_stable_measurement_rejects_fake_promotion(self) -> None:
        measurement = self.fresh_payload()["stable_measurement"]

        self.assertEqual(measurement["label_control_saving_bytes"], 736)
        self.assertEqual(measurement["direct_opening_value_saving_bytes"], 112)
        self.assertEqual(measurement["transcript_path_sensitive_saving_bytes"], 624)
        self.assertEqual(measurement["stable_promotable_comparison_count"], 0)
        self.assertFalse(measurement["nanozk_win_claimed"])

        payload = self.fresh_payload()
        payload["summary"]["stable_reprove_supported_by_current_source"] = True
        gate.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(gate.VariantInvariantReprovePreflightError, "reprove support overclaim"):
            gate.validate_payload(payload)

        payload = self.fresh_payload()
        payload["summary"]["stable_floor_bytes"] = 736
        gate.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(gate.VariantInvariantReprovePreflightError, "stable floor drift"):
            gate.validate_payload(payload)

    def test_source_shape_rejects_missing_duplicate_base_trace(self) -> None:
        source_text = gate.SOURCE_PATH.read_text(encoding="utf-8")
        mutated = source_text.replace(
            "attention_base.extend(adapter_trace(input)?);",
            "// compact route would remove the duplicate adapter base trace",
        )
        with self.assertRaisesRegex(gate.VariantInvariantReprovePreflightError, "base_adapter_trace"):
            gate.validate_source_shape(mutated)

    def test_source_shape_rejects_untracked_selector(self) -> None:
        source_text = gate.SOURCE_PATH.read_text(encoding="utf-8")
        mutated = source_text + "\nlet adapter_variant = \"compact\";\n"
        with self.assertRaisesRegex(gate.VariantInvariantReprovePreflightError, "unexpected variant selector"):
            gate.validate_source_shape(mutated)

    def test_all_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(gate.MUTATION_NAMES))
        self.assertEqual([case["name"] for case in payload["cases"]], list(gate.MUTATION_NAMES))
        self.assertTrue(all(case["rejected"] for case in payload["cases"]))

    def test_source_artifacts_are_hash_bound(self) -> None:
        artifacts = {artifact["id"]: artifact for artifact in self.fresh_payload()["source_artifacts"]}

        self.assertEqual(
            artifacts["native_attention_mlp_single_proof_source"]["sha256"],
            gate.EXPECTED_SOURCE_SHA256,
        )
        self.assertEqual(
            artifacts["transcript_stable_comparison_gate"]["sha256"],
            gate.EXPECTED_TRANSCRIPT_STABLE_SHA256,
        )
        self.assertEqual(
            artifacts["transcript_stable_comparison_gate"]["payload_sha256"],
            gate.EXPECTED_TRANSCRIPT_STABLE_PAYLOAD_SHA256,
        )

        payload = self.fresh_payload()
        payload["source_artifacts"][0]["sha256"] = "00" * 32
        gate.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(gate.VariantInvariantReprovePreflightError, "source_artifacts drift"):
            gate.validate_payload(payload)

    def test_tsv_contains_preflight_row(self) -> None:
        tsv = gate.to_tsv(self.fresh_payload())
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("\t41932\t43228\t42492\t736\t112\t624\tFalse\tFalse\t", tsv)
        self.assertIn("source-backed compact adapter selector", tsv)

    def test_output_paths_are_pinned_direct_children(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outside = gate.pathlib.Path(temp_dir) / "out.json"
            with self.assertRaisesRegex(gate.VariantInvariantReprovePreflightError, "direct child"):
                gate.require_output_path(outside, ".json")

        wrong = gate.EVIDENCE_DIR / "not-the-pinned-output.json"
        with self.assertRaisesRegex(gate.VariantInvariantReprovePreflightError, "pinned preflight evidence"):
            gate.require_output_path(wrong, ".json")

    def test_write_outputs_rejects_symlink(self) -> None:
        payload = self.fresh_payload()
        if not hasattr(gate.os, "symlink"):
            self.skipTest("symlink support required")
        with tempfile.TemporaryDirectory() as temp_dir:
            target = gate.pathlib.Path(temp_dir) / "target.json"
            link = gate.JSON_OUT
            backup = gate.JSON_OUT.read_bytes() if gate.JSON_OUT.exists() else None
            target.write_text("{}", encoding="utf-8")
            if link.exists():
                link.unlink()
            link.symlink_to(target)
            try:
                with self.assertRaisesRegex(gate.VariantInvariantReprovePreflightError, "symlink"):
                    gate.write_outputs(payload, link, None)
            finally:
                link.unlink(missing_ok=True)
                if backup is not None:
                    link.write_bytes(backup)


if __name__ == "__main__":
    unittest.main()
