import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from scripts import zkai_matched_d64_d128_evidence_table_gate as gate


class MatchedD64D128EvidenceTableGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = gate.build_payload()

    def test_payload_separates_object_classes_and_keeps_claim_guard_closed(self) -> None:
        self.assertEqual(self.payload["schema"], gate.SCHEMA)
        self.assertEqual(self.payload["decision"], gate.DECISION)
        self.assertFalse(self.payload["claim_guard"]["matched_benchmark_claim_allowed"])
        self.assertFalse(self.payload["claim_guard"]["native_d128_proof_size_claim_allowed"])
        self.assertFalse(self.payload["claim_guard"]["package_bytes_are_proof_bytes"])
        self.assertEqual(self.payload["summary"]["d64_checked_rows"], 49600)
        self.assertEqual(self.payload["summary"]["d128_checked_rows"], 197504)
        self.assertEqual(self.payload["summary"]["d128_package_without_vk_bytes"], 4752)
        self.assertEqual(self.payload["summary"]["native_d128_block_proof_bytes"], None)
        self.assertIn("STARK-native proof objects", json.dumps(self.payload))

    def test_rows_have_required_boundaries_and_expected_backend_classes(self) -> None:
        rows = {row["row_id"]: row for row in self.payload["evidence_rows"]}
        self.assertEqual(rows["local_d64_stwo_receipt_chain_rows"]["backend_family"], "Stwo native proof-backed receipt chain")
        self.assertEqual(rows["local_d128_stwo_receipt_chain_rows"]["ratio_vs_d64_checked_rows"], 3.981935)
        self.assertEqual(
            rows["local_d128_external_snark_statement_receipt_proof_bytes"]["object_class"],
            "external_snark_statement_receipt_proof_bytes",
        )
        self.assertEqual(
            rows["local_d128_package_without_vk_bytes"]["object_class"],
            "verifier_facing_package_without_vk_bytes",
        )
        self.assertIn("not matched proof-size evidence", rows["local_d128_package_without_vk_bytes"]["comparison_boundary"])
        self.assertEqual(
            rows["external_nanozk_reported_transformer_block_proof_bytes"]["evidence_status"],
            "paper_reported_not_locally_reproduced",
        )
        self.assertIsNone(rows["missing_native_d128_block_proof_object"]["value"])

    def test_tsv_is_deterministic_and_includes_claim_boundary_columns(self) -> None:
        text = gate.to_tsv(self.payload)
        lines = text.splitlines()
        self.assertEqual(
            lines[0],
            "row_id\tsystem\tdimension_or_scope\tbackend_family\tobject_class\tevidence_status\tmetric\tvalue\tunit\tratio_vs_d64_checked_rows\tratio_vs_d128_checked_rows\tratio_vs_source_statement_chain\tratio_vs_nanozk_reported\tcomparison_boundary",
        )
        self.assertIn("local_d128_package_without_vk_bytes", text)
        self.assertIn("external_nanozk_reported_transformer_block_proof_bytes", text)
        self.assertIn("missing_native_d128_block_proof_object", text)
        self.assertEqual(text, gate.to_tsv(self.payload))

    def test_mutations_are_all_rejected(self) -> None:
        self.assertEqual(self.payload["case_count"], len(gate.MUTATION_NAMES))
        self.assertTrue(self.payload["all_mutations_rejected"])
        rejected = {case["mutation"]: case["error"] for case in self.payload["cases"] if case["rejected"]}
        for name in gate.MUTATION_NAMES:
            self.assertIn(name, rejected)

    def test_payload_commitment_detects_drift(self) -> None:
        mutated = json.loads(json.dumps(self.payload))
        mutated["summary"]["d128_package_without_vk_bytes"] = 1
        with self.assertRaisesRegex(gate.MatchedD64D128EvidenceTableError, "payload drift|summary drift"):
            gate.validate_payload(mutated)

        mutated = json.loads(json.dumps(self.payload))
        mutated["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.MatchedD64D128EvidenceTableError, "payload commitment drift"):
            gate.validate_payload(mutated)

    def test_loaders_reject_duplicate_json_keys_and_tsv_columns(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="matched-d64-d128-duplicate-key-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
            handle.write('{"value": 1, "value": 2}\n')
        try:
            with self.assertRaisesRegex(gate.MatchedD64D128EvidenceTableError, "duplicate JSON key"):
                gate.load_json(json_path)
        finally:
            json_path.unlink(missing_ok=True)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="matched-d64-d128-duplicate-column-",
            suffix=".tsv",
            delete=False,
        ) as handle:
            tsv_path = pathlib.Path(handle.name)
            handle.write("a\ta\n1\t2\n")
        try:
            with self.assertRaisesRegex(gate.MatchedD64D128EvidenceTableError, "duplicate columns"):
                gate.load_tsv(tsv_path)
        finally:
            tsv_path.unlink(missing_ok=True)

    def test_write_outputs_rejects_outside_repo_and_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.MatchedD64D128EvidenceTableError, "repo-relative"):
                gate.write_outputs(self.payload, pathlib.Path(tmp) / "out.json", None)

        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="matched-d64-d128-output-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        tsv_path.unlink(missing_ok=True)
        try:
            gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), self.payload)
            self.assertIn("object_class", tsv_path.read_text(encoding="utf-8"))
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_cleanup_fsync_warning_preserves_original_write_error(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="matched-d64-d128-cleanup-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()

        original_assert_identity = gate._assert_directory_identity
        original_fsync = gate.os.fsync
        original_close = gate.os.close
        state = {"assert_calls": 0, "closed_directory": False}

        try:
            def fail_after_temp_write(path, identity, label):
                original_assert_identity(path, identity, label)
                if label == "output path 1":
                    state["assert_calls"] += 1
                    if state["assert_calls"] == 2:
                        raise OSError("simulated post-temp identity failure")

            def fail_directory_fsync(fd, *args, **kwargs):
                mode = gate.os.fstat(fd).st_mode
                if gate.stat_module.S_ISDIR(mode):
                    raise OSError("simulated cleanup fsync failure")
                return original_fsync(fd, *args, **kwargs)

            def record_directory_close(fd, *args, **kwargs):
                try:
                    mode = gate.os.fstat(fd).st_mode
                except OSError:
                    mode = 0
                if gate.stat_module.S_ISDIR(mode):
                    state["closed_directory"] = True
                return original_close(fd, *args, **kwargs)

            gate._assert_directory_identity = fail_after_temp_write
            gate.os.fsync = fail_directory_fsync
            gate.os.close = record_directory_close
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaisesRegex(
                    gate.MatchedD64D128EvidenceTableError,
                    "simulated post-temp identity failure",
                ):
                    gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), None)
            self.assertTrue(state["closed_directory"])
            self.assertFalse(json_path.exists())
            self.assertIn("warning: failed to fsync output directory during cleanup", stderr.getvalue())
        finally:
            gate._assert_directory_identity = original_assert_identity
            gate.os.fsync = original_fsync
            gate.os.close = original_close
            json_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
