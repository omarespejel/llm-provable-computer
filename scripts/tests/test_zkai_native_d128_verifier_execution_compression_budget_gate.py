import copy
import pathlib
import shutil
import tempfile
import unittest

from scripts import zkai_native_d128_verifier_execution_compression_budget_gate as gate


class VerifierExecutionCompressionBudgetGateTests(unittest.TestCase):
    def test_build_payload_validates_budget(self) -> None:
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["mutations_checked"], len(gate.MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])
        budget = payload["compression_budget"]
        self.assertEqual(budget["current_verifier_target_typed_bytes"], 12_688)
        self.assertEqual(budget["typed_bytes_to_remove_to_equal_nanozk"], 5_788)
        self.assertEqual(budget["typed_required_reduction_ratio"], 0.456179)
        self.assertEqual(budget["current_target_typed_over_compact_statement"], 7.080357)

    def test_compact_statement_is_not_promoted_to_matched_comparison(self) -> None:
        payload = gate.build_payload()
        compact = payload["comparison_objects"]["compact_statement_binding"]
        self.assertFalse(compact["comparable_to_nanozk_block_proof"])
        self.assertEqual(compact["local_typed_bytes"], 1_792)
        self.assertEqual(compact["ratio_vs_nanozk_typed"], 0.25971)

    def test_rejects_source_descriptor_drift(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["source_evidence"][0]["file_sha256"] = "0" * 64
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(gate.CompressionBudgetGateError, "source evidence drift"):
            gate.validate_payload(mutated)

    def test_rejects_compact_statement_promotion(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["comparison_objects"]["compact_statement_binding"]["comparable_to_nanozk_block_proof"] = True
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(gate.CompressionBudgetGateError, "comparison objects drift"):
            gate.validate_payload(mutated)

    def test_rejects_reduction_budget_drift(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["compression_budget"]["typed_bytes_to_remove_to_equal_nanozk"] -= 1
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(gate.CompressionBudgetGateError, "compression budget drift"):
            gate.validate_payload(mutated)

    def test_rejects_attack_path_reclassification(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["attack_paths"][0]["classification"] = "LOW_PRIORITY"
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(gate.CompressionBudgetGateError, "attack paths drift"):
            gate.validate_payload(mutated)

    def test_tsv_contains_two_comparison_rows(self) -> None:
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertEqual(len(tsv.strip().splitlines()), 3)
        self.assertIn("compact_statement_binding", tsv)
        self.assertIn("selected_inner_verifier_execution_target", tsv)

    def test_output_path_rejects_escape(self) -> None:
        with self.assertRaisesRegex(
            gate.CompressionBudgetGateError, "under evidence dir|escapes repository|under repo root"
        ):
            gate.validate_output_path(pathlib.Path(tempfile.gettempdir()) / "outside.json")

    def test_output_path_rejects_symlink_parent(self) -> None:
        link = gate.EVIDENCE_DIR / ".tmp-budget-symlink-parent"
        with tempfile.TemporaryDirectory() as target:
            try:
                link.symlink_to(target, target_is_directory=True)
                with self.assertRaisesRegex(gate.CompressionBudgetGateError, "component must not be a symlink"):
                    gate.validate_output_path(link / "out.json")
            finally:
                link.unlink(missing_ok=True)

    def test_output_path_rejects_missing_parent(self) -> None:
        out = gate.EVIDENCE_DIR / ".tmp-budget-missing-parent" / "out.json"
        with self.assertRaisesRegex(gate.CompressionBudgetGateError, "output parent does not exist"):
            gate.validate_output_path(out)

    def test_output_path_rejects_directory(self) -> None:
        out = gate.EVIDENCE_DIR / ".tmp-budget-output-dir"
        try:
            out.mkdir(exist_ok=True)
            with self.assertRaisesRegex(gate.CompressionBudgetGateError, "output path must be a file"):
                gate.validate_output_path(out)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_atomic_write_roundtrip_under_evidence_dir(self) -> None:
        payload = gate.build_payload()
        out = gate.EVIDENCE_DIR / ".tmp-verifier-execution-compression-budget-test.json"
        try:
            gate.write_json(out, payload)
            self.assertTrue(out.exists())
            loaded, _ = gate.load_json(out)
            gate.validate_payload(loaded)
        finally:
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
