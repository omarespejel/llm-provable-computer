import copy
import tempfile
import unittest
from unittest import mock

from scripts import zkai_native_attention_mlp_transcript_stable_comparison_gate as gate


class NativeAttentionMlpTranscriptStableComparisonGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def comparison_by_id(self, comparison_id: str) -> dict:
        comparisons = {comparison["comparison_id"]: comparison for comparison in self.fresh_payload()["comparisons"]}
        return comparisons[comparison_id]

    def test_payload_records_no_go_and_key_numbers(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload)
        summary = payload["summary"]

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertFalse(summary["stable_frontier_promotion"])
        self.assertEqual(
            summary["stable_comparison_result"],
            "NO_GO_VARIANT_PROOF_ARTIFACTS_AND_QUERY_INVENTORY_MISSING",
        )
        self.assertEqual(summary["current_frontier_typed_bytes"], 41_932)
        self.assertEqual(summary["best_reported_label_control_saving_bytes"], 736)
        self.assertEqual(summary["label_control_direct_opening_value_saving_bytes"], 112)
        self.assertEqual(summary["label_control_transcript_path_sensitive_saving_bytes"], 624)
        self.assertEqual(summary["stable_promotable_comparison_count"], 0)
        self.assertFalse(summary["nanozk_win_claimed"])

    def test_label_control_saving_is_decomposed_into_direct_and_path_sensitive_parts(self) -> None:
        label_control = self.comparison_by_id("compact_base_v2_vs_duplicate_label_control")

        self.assertEqual(label_control["typed_saving_bytes"], 736)
        self.assertEqual(label_control["json_saving_bytes"], 2_651)
        self.assertEqual(label_control["adapter_trace_cell_saving"], 512)
        self.assertEqual(label_control["direct_opening_value_saving_bytes"], 112)
        self.assertEqual(label_control["transcript_path_sensitive_saving_bytes"], 624)
        self.assertEqual(label_control["transcript_path_sensitive_share"], 0.847826)
        self.assertFalse(label_control["proof_backend_versions_equal"])
        self.assertFalse(label_control["statement_versions_equal"])
        self.assertFalse(label_control["transcript_stable_for_promotion"])
        self.assertEqual(
            label_control["promotion_status"],
            "NO_GO_LABELS_DIFFER_AND_VARIANT_PROOF_ARTIFACTS_MISSING",
        )

    def test_legacy_and_compact_unconstrained_controls_pin_the_shape_interpretation(self) -> None:
        legacy = self.comparison_by_id("legacy_microprobe_vs_current_frontier")
        weak = self.comparison_by_id("unconstrained_compact_v2_vs_duplicate_label_control")
        compact_vs_weak = self.comparison_by_id("referenced_compact_v2_vs_unconstrained_compact_v2")

        self.assertEqual(legacy["typed_saving_bytes"], 704)
        self.assertEqual(legacy["direct_opening_value_saving_bytes"], 112)
        self.assertEqual(legacy["transcript_path_sensitive_saving_bytes"], 592)
        self.assertTrue(legacy["proof_backend_versions_equal"])
        self.assertEqual(legacy["promotion_status"], "NO_GO_VARIANT_PROOF_ARTIFACT_MISSING")

        self.assertEqual(weak["typed_saving_bytes"], 112)
        self.assertEqual(weak["direct_opening_value_saving_bytes"], 112)
        self.assertEqual(weak["transcript_path_sensitive_saving_bytes"], 0)

        self.assertEqual(compact_vs_weak["typed_saving_bytes"], 624)
        self.assertEqual(compact_vs_weak["direct_opening_value_saving_bytes"], 0)
        self.assertEqual(compact_vs_weak["transcript_path_sensitive_saving_bytes"], 624)
        self.assertTrue(compact_vs_weak["proof_backend_versions_equal"])
        self.assertTrue(compact_vs_weak["statement_versions_equal"])

    def test_variant_inventory_marks_only_current_frontier_as_artifact_backed(self) -> None:
        variants = {variant["id"]: variant for variant in self.fresh_payload()["variant_inventory"]}

        current = variants["current_duplicate_adapter_v1_frontier"]
        compact = variants["compact_base_v2_referenced_fixed_columns"]
        self.assertTrue(current["artifact_backed"])
        self.assertEqual(current["query_inventory_status"], "PINNED_RECORD_STREAM")
        self.assertEqual(
            current["query_inventory_fingerprint"],
            "4f1b230afc4f7fec71ce632faa2b0b9512276467aa9dd05f48cd1fba4ba581f4",
        )
        self.assertRegex(current["query_inventory_fingerprint"], r"^[0-9a-f]{64}$")
        self.assertRegex(current["statement_commitment"], r"^blake2b-256:[0-9a-f]{64}$")
        self.assertRegex(current["public_instance_commitment"], r"^blake2b-256:[0-9a-f]{64}$")
        self.assertFalse(compact["artifact_backed"])
        self.assertEqual(compact["query_inventory_status"], "MISSING_VARIANT_PROOF_ARTIFACT")
        self.assertIsNone(compact["query_inventory_fingerprint"])
        self.assertIsNone(compact["public_instance_commitment"])
        self.assertRegex(compact["reported_shape_fingerprint"], r"^blake2b-256:[0-9a-f]{64}$")

    def test_stability_policy_rejects_grouped_bytes_as_query_inventory(self) -> None:
        policy = self.fresh_payload()["stability_policy"]
        self.assertTrue(policy["promotion_requires_source_artifact_per_variant"])
        self.assertTrue(policy["promotion_requires_query_inventory_fingerprint"])
        self.assertTrue(policy["grouped_bytes_alone_are_not_a_query_inventory"])

    def test_promotion_status_requires_commitments_and_query_fingerprint(self) -> None:
        variants = {variant["id"]: variant for variant in self.fresh_payload()["variant_inventory"]}
        baseline = copy.deepcopy(variants["current_duplicate_adapter_v1_frontier"])
        candidate = copy.deepcopy(variants["compact_base_legacy_label_microprobe"])
        candidate["artifact_backed"] = True
        candidate["query_inventory_status"] = "PINNED_RECORD_STREAM"
        candidate["proof_backend_version"] = baseline["proof_backend_version"]
        candidate["statement_version"] = baseline["statement_version"]

        self.assertEqual(
            gate.promotion_status(baseline, candidate),
            "NO_GO_CANDIDATE_STATEMENT_COMMITMENT_MISSING",
        )

        candidate["statement_commitment"] = "blake2b-256:" + "22" * 32
        self.assertEqual(
            gate.promotion_status(baseline, candidate),
            "NO_GO_CANDIDATE_PUBLIC_INSTANCE_COMMITMENT_MISSING",
        )

        candidate["public_instance_commitment"] = "blake2b-256:" + "33" * 32
        self.assertEqual(
            gate.promotion_status(baseline, candidate),
            "NO_GO_CANDIDATE_QUERY_INVENTORY_FINGERPRINT_MISSING",
        )

        candidate["query_inventory_fingerprint"] = "blake2b-256:" + "11" * 32
        self.assertEqual(
            gate.promotion_status(baseline, candidate),
            "NO_GO_CANDIDATE_QUERY_INVENTORY_FINGERPRINT_MISSING",
        )

        candidate["query_inventory_fingerprint"] = "11" * 32
        self.assertEqual(gate.promotion_status(baseline, candidate), "GO_TRANSCRIPT_STABLE")

    def test_mutations_reject_overclaims_and_fake_inventory(self) -> None:
        payload = self.fresh_payload()
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(gate.MUTATION_NAMES))
        self.assertEqual([case["name"] for case in payload["cases"]], list(gate.MUTATION_NAMES))

        mutated = self.fresh_payload()
        mutated["summary"]["stable_frontier_promotion"] = True
        gate.refresh_payload_commitment(mutated)
        with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "summary drift|frontier overclaim"):
            gate.validate_payload(mutated)

        mutated = self.fresh_payload()
        mutated["summary"]["nanozk_win_claimed"] = True
        gate.refresh_payload_commitment(mutated)
        with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "summary drift|NANOZK overclaim"):
            gate.validate_payload(mutated)

    def test_sources_are_hash_bound_and_artifact_order_independent(self) -> None:
        sources = gate.load_sources()
        sources["source_artifacts"].reverse()
        gate.validate_sources(sources)

        mutated = copy.deepcopy(sources)
        artifacts_by_id = {artifact["id"]: artifact for artifact in mutated["source_artifacts"]}
        artifacts_by_id["adapter_compression_ablation_gate"]["sha256"] = "00" * 32
        with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "adapter_compression_ablation_gate hash drift"):
            gate.validate_sources(mutated)

    def test_source_validation_rejects_malformed_artifact_inventory(self) -> None:
        sources = gate.load_sources()

        mutated = copy.deepcopy(sources)
        mutated["source_artifacts"].append(copy.deepcopy(mutated["source_artifacts"][0]))
        with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "duplicate source artifact id"):
            gate.validate_sources(mutated)

        mutated = copy.deepcopy(sources)
        mutated["source_artifacts"][0] = "bad"
        with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "source artifact 0 must be object"):
            gate.validate_sources(mutated)

    def test_source_validation_pins_current_envelope_and_record_stream(self) -> None:
        sources = gate.load_sources()
        gate.validate_sources(sources)

        mutated = copy.deepcopy(sources)
        mutated["envelope"]["input"]["statement_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "statement commitment drift"):
            gate.validate_sources(mutated)

        mutated = copy.deepcopy(sources)
        mutated["accounting"]["rows"][0]["local_binary_accounting"]["record_stream_sha256"] = "22" * 32
        with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "record-stream drift"):
            gate.validate_sources(mutated)

    def test_tsv_contains_comparison_rows(self) -> None:
        tsv = gate.to_tsv(self.fresh_payload())
        self.assertIn("compact_base_v2_vs_duplicate_label_control", tsv)
        self.assertIn("\t736\t2651\t112\t624\t0.847826\t", tsv)
        self.assertIn("NO_GO_LABELS_DIFFER_AND_VARIANT_PROOF_ARTIFACTS_MISSING", tsv)

    def test_read_json_rejects_non_finite_constants(self) -> None:
        path = gate.EVIDENCE_DIR / f"test-nan-{gate.secrets.token_hex(8)}.json"
        try:
            path.write_text('{"bad": NaN}', encoding="utf-8")
            with self.assertRaises(gate.TranscriptStableComparisonError):
                gate.read_json(path, "nan JSON")
        finally:
            path.unlink(missing_ok=True)

    def test_read_json_open_error_is_structured(self) -> None:
        with mock.patch.object(gate.os, "open", side_effect=OSError("boom")):
            with self.assertRaises(gate.TranscriptStableComparisonError) as cm:
                gate.read_json(gate.ABLATION_PATH, "ablation")
        self.assertIn("ablation", str(cm.exception))
        self.assertIn("boom", str(cm.exception))

    def test_write_outputs_rejects_outside_path_and_symlink(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as temp_dir:
            outside = gate.pathlib.Path(temp_dir) / "out.json"
            with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "output path must stay"):
                gate.write_outputs(payload, outside, None)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = gate.pathlib.Path(temp_dir) / "target.json"
            link = gate.EVIDENCE_DIR / f"test-symlink-out-{gate.secrets.token_hex(8)}.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            try:
                with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "symlink"):
                    gate.write_outputs(payload, link, None)
            finally:
                link.unlink(missing_ok=True)

    def test_write_outputs_rejects_pinned_input_overwrite(self) -> None:
        with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "pinned input evidence"):
            gate.require_output_path(gate.ABLATION_PATH, ".json")

    def test_write_outputs_does_not_remove_stale_deterministic_temp(self) -> None:
        payload = self.fresh_payload()
        out = gate.EVIDENCE_DIR / f"test-stale-out-{gate.secrets.token_hex(8)}.json"
        stale = gate.EVIDENCE_DIR / f".{out.name}.tmp-{gate.os.getpid()}"
        try:
            stale.write_text("keep", encoding="utf-8")

            gate.write_outputs(payload, out, None)

            self.assertEqual(stale.read_text(encoding="utf-8"), "keep")
            self.assertTrue(out.exists())
        finally:
            out.unlink(missing_ok=True)
            stale.unlink(missing_ok=True)

    def test_write_text_atomic_rejects_symlink_parent(self) -> None:
        if getattr(gate.os, "O_NOFOLLOW", 0) == 0:
            self.skipTest("platform lacks O_NOFOLLOW")
        with tempfile.TemporaryDirectory() as outside_dir:
            outside = gate.pathlib.Path(outside_dir)
            link_parent = gate.EVIDENCE_DIR / f"test-link-parent-{gate.secrets.token_hex(8)}"
            link_parent.symlink_to(outside, target_is_directory=True)
            try:
                with self.assertRaisesRegex(gate.TranscriptStableComparisonError, "direct child"):
                    gate.write_text_atomic(link_parent / "out.json", "{}\n")
            finally:
                link_parent.unlink(missing_ok=True)
                self.assertFalse((outside / "out.json").exists())


if __name__ == "__main__":
    unittest.main()
