import copy
import json
import math
import pathlib
import tempfile
import unittest

from scripts import zkai_may2026_competitor_metric_matrix_gate as gate


class May2026CompetitorMetricMatrixGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload_base = gate.build_payload()

    def setUp(self) -> None:
        self.payload = copy.deepcopy(self.payload_base)

    def test_builds_source_backed_comparison_without_overclaiming(self):
        payload = self.payload
        gate.validate_payload(payload)

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["claim_boundary"], gate.CLAIM_BOUNDARY)
        self.assertEqual(len(payload["source_artifacts"]), 4)
        self.assertEqual(len(payload["external_rows"]), 5)
        self.assertEqual(len(payload["local_rows"]), 3)
        self.assertIn("not a matched benchmark", payload["non_claims"][0])

        external = {(row["system"], row["workload_label"]): row for row in payload["external_rows"]}
        self.assertEqual(external[("NANOZK", "Transformer block proof")]["proof_size_reported"], "6.9 KB")
        self.assertEqual(external[("NANOZK", "Transformer block proof")]["prove_seconds"], "6.3")
        self.assertEqual(external[("Jolt Atlas", "GPT-2 proof")]["prove_seconds"], "38")
        self.assertEqual(external[("EZKL (reported by Jolt Atlas)", "NanoGPT proof")]["prove_seconds"], "237")

        local = {row["surface"]: row for row in payload["local_rows"]}
        self.assertEqual(local["Stwo attention/Softmax-table fusion"]["value"], 194097)
        self.assertEqual(local["d64 RMSNorm/SwiGLU/residual block receipt"]["value"], 49600)
        self.assertEqual(local["d128 RMSNorm/SwiGLU/residual comparator target"]["value"], 196608)
        self.assertEqual(
            local["d128 RMSNorm/SwiGLU/residual comparator target"]["local_status"],
            "NO_GO_LOCAL_D128_PROOF_ARTIFACT_MISSING",
        )

    def test_rejects_source_metric_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["external_rows"][0]["prove_seconds"] = "0"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "payload drift"):
            gate.validate_payload(payload)

    def test_rejects_local_overclaim_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["local_rows"][2]["local_status"] = "GO_LOCAL_D128_PROOF"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "payload drift"):
            gate.validate_payload(payload)

    def test_rejects_commitment_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "payload commitment drift"):
            gate.validate_payload(payload)

    def test_tsv_contains_external_and_local_rows(self):
        tsv = gate.to_tsv(self.payload)
        self.assertIn("external\tNANOZK\tTransformer block proof\t6.3\t0.023\t6.9 KB", tsv)
        self.assertIn("local\tprovable-transformer-vm\tStwo attention/Softmax-table fusion", tsv)
        self.assertIn("matched route JSON proof-byte saving\t194097", tsv)

    def test_source_artifact_hashes_match_single_read_bytes(self):
        payload = gate.build_payload_uncommitted()
        source_by_path = {artifact["path"]: artifact for artifact in payload["source_artifacts"]}
        for path in (gate.PUBLISHED_ZKML_NUMBERS, gate.FUSION_MECHANISM, gate.D64_BLOCK_RECEIPT, gate.D128_TARGET):
            raw = gate.read_source_bytes(path, "test source")
            artifact = source_by_path[str(path.relative_to(gate.ROOT))]
            self.assertEqual(artifact["sha256"], gate.hashlib.sha256(raw).hexdigest())

    def test_write_outputs_round_trip_and_rejects_outside_path(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="competitor-matrix-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        try:
            gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, self.payload)
            self.assertIn("row_kind", tsv_path.read_text(encoding="utf-8"))
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "repo-relative"):
                gate.write_outputs(self.payload, pathlib.Path(tmp) / "out.json", gate.TSV_OUT.relative_to(gate.ROOT))

        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="competitor-output-parent-",
            delete=False,
        ) as handle:
            parent_file = pathlib.Path(handle.name)
        try:
            with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "failed to write output path"):
                gate.write_outputs(
                    self.payload,
                    (parent_file / "out.json").relative_to(gate.ROOT),
                    gate.TSV_OUT.relative_to(gate.ROOT),
                )
        finally:
            parent_file.unlink(missing_ok=True)

    def test_write_outputs_rolls_back_when_second_replace_fails(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="competitor-transaction-json-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
            handle.write(b"original-json")
        tsv_path = json_path.with_suffix(".tsv")
        tsv_path.unlink(missing_ok=True)

        original_replace = gate.os.replace
        original_write_bytes = pathlib.Path.write_bytes
        try:
            def fail_on_tsv(src, dst):
                if pathlib.Path(dst) == tsv_path:
                    raise OSError("simulated second replace failure")
                return original_replace(src, dst)

            def fail_direct_write(_path, _contents):
                raise AssertionError("rollback must restore through an atomic temp replace")

            gate.os.replace = fail_on_tsv
            pathlib.Path.write_bytes = fail_direct_write
            with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "failed to write output path"):
                gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json_path.read_text(encoding="utf-8"), "original-json")
            self.assertFalse(tsv_path.exists())
        finally:
            gate.os.replace = original_replace
            pathlib.Path.write_bytes = original_write_bytes
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_write_outputs_rollback_does_not_follow_swapped_symlink(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="competitor-transaction-symlink-json-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
            handle.write(b"original-json")
        tsv_path = json_path.with_suffix(".tsv")
        tsv_path.unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            outside_target = pathlib.Path(tmp) / "outside-target.json"
            outside_target.write_text("outside-original", encoding="utf-8")
            original_replace = gate.os.replace
            try:
                def swap_json_target_on_tsv(src, dst):
                    if pathlib.Path(dst) == tsv_path:
                        json_path.unlink(missing_ok=True)
                        try:
                            json_path.symlink_to(outside_target)
                        except OSError as err:
                            self.skipTest(f"symlink creation is unavailable: {err}")
                        raise OSError("simulated second replace failure after target swap")
                    return original_replace(src, dst)

                gate.os.replace = swap_json_target_on_tsv
                with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "failed to write output path"):
                    gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
                self.assertEqual(outside_target.read_text(encoding="utf-8"), "outside-original")
                self.assertTrue(json_path.is_symlink())
                self.assertFalse(tsv_path.exists())
            finally:
                gate.os.replace = original_replace
                json_path.unlink(missing_ok=True)
                tsv_path.unlink(missing_ok=True)

    def test_json_helpers_reject_non_finite_values(self):
        payload = copy.deepcopy(self.payload)
        payload["local_rows"][0]["value"] = math.nan
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "invalid JSON value"):
            gate.canonical_json_bytes(payload)

        payload = copy.deepcopy(self.payload)
        payload["not_json_serializable"] = {1, 2, 3}
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "invalid JSON value"):
            gate.canonical_json_bytes(payload)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="competitor-non-finite-",
            suffix=".json",
            delete=False,
        ) as handle:
            path = pathlib.Path(handle.name)
            handle.write('{"value": Infinity}\n')
        try:
            with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "non-finite JSON constant"):
                gate.load_json(path)
        finally:
            path.unlink(missing_ok=True)

    def test_source_field_helpers_reject_wrong_types(self):
        fusion = gate.load_json(gate.FUSION_MECHANISM)
        fusion["route_matrix"]["fused_savings_bytes_total"] = "194097"
        d64 = gate.load_json(gate.D64_BLOCK_RECEIPT)
        d128 = gate.load_json(gate.D128_TARGET)

        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "fusion savings must be integer"):
            gate._local_rows(fusion, d64, d128)

        fusion = gate.load_json(gate.FUSION_MECHANISM)
        fusion["section_delta"]["opening_bucket_savings_share"] = "0.927722"
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "fusion opening share must be numeric"):
            gate._local_rows(fusion, d64, d128)

        fusion = gate.load_json(gate.FUSION_MECHANISM)
        fusion["section_delta"]["opening_bucket_savings_share"] = math.inf
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "fusion opening share must be finite"):
            gate._local_rows(fusion, d64, d128)

        fusion = gate.load_json(gate.FUSION_MECHANISM)
        fusion["section_delta"]["opening_bucket_savings_share"] = 1.1
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "fusion opening share must be between 0 and 1"):
            gate._local_rows(fusion, d64, d128)

        fusion = gate.load_json(gate.FUSION_MECHANISM)
        fusion["route_matrix"]["fused_savings_bytes_total"] = 0
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "fusion savings must be positive"):
            gate._local_rows(fusion, d64, d128)

        fusion = gate.load_json(gate.FUSION_MECHANISM)
        d64 = gate.load_json(gate.D64_BLOCK_RECEIPT)
        d64["summary"]["mutations_rejected"] = d64["summary"]["mutation_cases"] - 1
        with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "d64 mutation rejection summary drift"):
            gate._local_rows(fusion, d64, d128)

    def test_load_tsv_rejects_missing_required_columns(self):
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="competitor-bad-published-",
            suffix=".tsv",
            delete=False,
        ) as handle:
            path = pathlib.Path(handle.name)
            handle.write("system\tworkload_label\nNANOZK\tTransformer block proof\n")
        try:
            with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "TSV source missing columns"):
                gate.load_tsv(path)
        finally:
            path.unlink(missing_ok=True)

    def test_read_source_bytes_rejects_symlink_source(self):
        with tempfile.TemporaryDirectory(dir=gate.ENGINEERING_EVIDENCE) as tmp:
            real_path = pathlib.Path(tmp) / "real.json"
            real_path.write_text("{}", encoding="utf-8")
            link_path = pathlib.Path(tmp) / "linked.json"
            try:
                link_path.symlink_to(real_path)
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            with self.assertRaisesRegex(gate.CompetitorMetricMatrixError, "symlinks"):
                gate.read_source_bytes(link_path, "symlink test")


if __name__ == "__main__":
    unittest.main()
