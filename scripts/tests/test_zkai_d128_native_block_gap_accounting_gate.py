from __future__ import annotations

import contextlib
import copy
import io
import json
import pathlib
import tempfile
import unittest

from scripts import zkai_d128_native_block_gap_accounting_gate as gate


class D128NativeBlockGapAccountingGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload_base = gate.build_payload()

    def setUp(self) -> None:
        self.payload = copy.deepcopy(self.payload_base)

    def test_builds_gap_accounting_without_claiming_nanozk_win(self) -> None:
        gate.validate_payload(self.payload)
        self.assertEqual(self.payload["schema"], gate.SCHEMA)
        self.assertEqual(self.payload["decision"], gate.DECISION)
        self.assertEqual(self.payload["result"], gate.RESULT)
        self.assertEqual(self.payload["claim_boundary"], gate.CLAIM_BOUNDARY)
        self.assertEqual(len(self.payload["source_artifacts"]), 4)
        self.assertEqual(len(self.payload["gap_rows"]), 5)
        self.assertEqual(self.payload["case_count"], len(gate.MUTATION_NAMES))
        self.assertTrue(self.payload["all_mutations_rejected"])

        summary = self.payload["summary"]
        self.assertIsNone(summary["native_d128_block_proof_bytes"])
        self.assertIsNone(summary["native_d128_block_verifier_time_ms"])
        self.assertFalse(summary["matched_benchmark_claim_allowed"])
        self.assertEqual(summary["nanozk_reported_block_proof_bytes_decimal"], 6900)
        self.assertEqual(summary["local_package_without_vk_bytes"], 4752)
        self.assertEqual(summary["local_package_without_vk_vs_nanozk_reported_ratio"], 0.688696)
        self.assertTrue(summary["local_package_without_vk_less_than_nanozk_reported_bytes"])
        self.assertEqual(summary["local_package_with_vk_bytes"], 10608)
        self.assertEqual(summary["local_package_with_vk_vs_nanozk_reported_ratio"], 1.537391)
        self.assertEqual(summary["attention_derived_statement_chain_extra_rows_vs_d128_receipt"], 2049)
        self.assertEqual(summary["attention_derived_statement_chain_vs_d128_receipt_ratio"], 1.010374)

        self.assertFalse(self.payload["claim_guard"]["matched_benchmark_claim_allowed"])
        self.assertIn("not a NANOZK proof-size win", self.payload["non_claims"])
        self.assertIn("NO-GO", summary["no_go_result"])

    def test_gap_rows_are_stable(self) -> None:
        rows = {row["surface"]: row for row in self.payload["gap_rows"]}
        self.assertEqual(rows["NANOZK transformer block proof"]["value"], 6900)
        self.assertEqual(rows["local attention-derived package without VK"]["value"], 4752)
        self.assertEqual(rows["local attention-derived package without VK"]["ratio_vs_nanozk_reported"], 0.688696)
        self.assertEqual(
            rows["local attention-derived package without VK"]["comparison_status"],
            "INTERESTING_SMALLER_PACKAGE_NOT_MATCHED_PROOF_BENCHMARK",
        )
        self.assertEqual(rows["native d128 block proof object"]["comparison_status"], "MISSING_REQUIRED_FOR_MATCHED_BENCHMARK")
        self.assertIsNone(rows["native d128 block proof object"]["value"])

    def test_mutations_reject_overclaims_and_metric_drift(self) -> None:
        cases = {case["mutation"]: case for case in self.payload["cases"]}
        for name in gate.MUTATION_NAMES:
            self.assertIn(name, cases)
            self.assertTrue(cases[name]["rejected"], name)
            self.assertTrue(cases[name]["error"], name)
        self.assertIn("summary drift", cases["native_block_proof_size_smuggled"]["error"])
        self.assertIn("claim guard drift", cases["matched_benchmark_claim_enabled"]["error"])
        self.assertIn("non-claims drift", cases["non_claim_removed"]["error"])

    def test_rejects_payload_and_commitment_drift(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["summary"]["local_package_without_vk_bytes"] = 1
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "payload drift"):
            gate.validate_payload(payload)

        payload = copy.deepcopy(self.payload)
        payload["claim_guard"]["matched_benchmark_claim_allowed"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "matched benchmark guard drift"):
            gate.validate_payload(payload)

        payload = copy.deepcopy(self.payload)
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "payload commitment drift"):
            gate.validate_payload(payload)

    def test_source_validation_rejects_drift(self) -> None:
        surface, package, _matrix, nanozk, _sources = gate.checked_sources()
        surface["summary"]["d128_checked_rows"] = 1
        with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "gap summary drift|d128"):
            gate.build_gap_summary(surface, package, nanozk)

        surface, package, _matrix, nanozk, _sources = gate.checked_sources()
        package["summary"]["snark_proof_bytes"] = 1
        with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "external receipt overhead|gap summary"):
            gate.build_gap_summary(surface, package, nanozk)

        self.assertEqual(gate._parse_reported_size_bytes("6.9 KB"), 6900)
        with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "unsupported reported proof size"):
            gate._parse_reported_size_bytes("6.9 KiB")

    def test_tsv_and_write_outputs(self) -> None:
        tsv = gate.to_tsv(self.payload)
        self.assertIn(
            "local attention-derived package without VK\tpackage bytes versus NANOZK reported bytes\t4752\tbytes\t0.688696",
            tsv,
        )
        self.assertIn("native d128 block proof object\tproof bytes\t\tbytes\t\tMISSING_REQUIRED", tsv)

        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="d128-native-block-gap-accounting-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        try:
            gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), self.payload)
            self.assertIn("comparison_status", tsv_path.read_text(encoding="utf-8"))
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "repo-relative"):
                gate.write_outputs(self.payload, pathlib.Path(tmp) / "out.json", None)

    def test_write_outputs_rolls_back_when_second_replace_fails(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="d128-native-block-gap-json-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
            handle.write(b"original-json")
        tsv_path = json_path.with_suffix(".tsv")
        tsv_path.unlink(missing_ok=True)

        original_replace = gate.os.replace
        try:
            def fail_on_tsv(src, dst, *args, **kwargs):
                if pathlib.Path(dst).name == tsv_path.name:
                    raise OSError("simulated second replace failure")
                return original_replace(src, dst, *args, **kwargs)

            gate.os.replace = fail_on_tsv
            with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "failed to write output path"):
                gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json_path.read_text(encoding="utf-8"), "original-json")
            self.assertFalse(tsv_path.exists())
        finally:
            gate.os.replace = original_replace
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_success_path_close_failure_does_not_roll_back_outputs(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="d128-native-block-gap-close-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        tsv_path.unlink(missing_ok=True)

        original_close = gate.os.close
        try:
            def close_then_fail_for_directory(fd, *args, **kwargs):
                mode = gate.os.fstat(fd).st_mode
                original_close(fd, *args, **kwargs)
                if gate.stat_module.S_ISDIR(mode):
                    raise OSError("simulated directory close failure")

            gate.os.close = close_then_fail_for_directory
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), self.payload)
            self.assertIn("comparison_status", tsv_path.read_text(encoding="utf-8"))
            self.assertIn("warning: failed to close output directory fd", stderr.getvalue())
        finally:
            gate.os.close = original_close
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_temp_cleanup_closes_parent_when_cleanup_fsync_fails(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="d128-native-block-gap-cleanup-",
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
            with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "failed to write output path"):
                gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), None)
            self.assertTrue(state["closed_directory"])
            self.assertFalse(json_path.exists())
        finally:
            gate._assert_directory_identity = original_assert_identity
            gate.os.fsync = original_fsync
            gate.os.close = original_close
            json_path.unlink(missing_ok=True)

    def test_loaders_reject_duplicate_keys_and_columns(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="d128-native-block-gap-duplicate-key-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
            handle.write('{"value": 1, "value": 2}\n')
        try:
            with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "duplicate JSON key"):
                gate.load_json(json_path)
        finally:
            json_path.unlink(missing_ok=True)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="d128-native-block-gap-duplicate-column-",
            suffix=".tsv",
            delete=False,
        ) as handle:
            tsv_path = pathlib.Path(handle.name)
            handle.write("a\ta\n1\t2\n")
        try:
            with self.assertRaisesRegex(gate.D128NativeBlockGapAccountingError, "duplicate columns"):
                gate.load_tsv(tsv_path)
        finally:
            tsv_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
