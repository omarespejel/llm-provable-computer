import copy
import json
import math
import pathlib
import tempfile
import unittest

from scripts import zkai_one_transformer_block_surface_gate as gate


class OneTransformerBlockSurfaceGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload_base = gate.build_payload()

    def setUp(self) -> None:
        self.payload = copy.deepcopy(self.payload_base)

    def test_builds_one_block_surface_without_overclaiming(self):
        payload = self.payload
        gate.validate_payload(payload)

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["claim_boundary"], gate.CLAIM_BOUNDARY)
        self.assertEqual(len(payload["source_artifacts"]), 4)
        self.assertEqual(len(payload["component_rows"]), 4)
        self.assertTrue(any("not a matched benchmark" in claim for claim in payload["non_claims"]))

        rows = {row["surface"]: row for row in payload["component_rows"]}
        self.assertEqual(rows["attention/Softmax-table fused proof component"]["value"], 194097)
        self.assertEqual(rows["d64 RMSNorm/SwiGLU/residual receipt chain"]["value"], 49600)
        self.assertEqual(rows["d128 RMSNorm/SwiGLU/residual receipt chain"]["value"], 197504)
        self.assertEqual(rows["NANOZK transformer block context"]["value"], "6.9 KB")

        summary = payload["summary"]
        self.assertEqual(summary["attention_fusion_saving_bytes"], 194097)
        self.assertEqual(summary["d64_checked_rows"], 49600)
        self.assertEqual(summary["d128_checked_rows"], 197504)
        self.assertEqual(summary["d128_over_d64_checked_row_ratio"], 3.981935)
        self.assertIn("NO-GO", summary["no_go_result"])

    def test_rejects_payload_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["component_rows"][1]["value"] = 0
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "payload drift"):
            gate.validate_payload(payload)

    def test_rejects_claim_boundary_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["claim_boundary"] = "OVERCLAIM"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "claim boundary drift"):
            gate.validate_payload(payload)

    def test_rejects_commitment_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "payload commitment drift"):
            gate.validate_payload(payload)

    def test_source_component_validation_rejects_metric_drift(self):
        fusion = gate.load_json(gate.FUSION_MECHANISM)
        d64 = gate.load_json(gate.D64_BLOCK_RECEIPT)
        d128 = gate.load_json(gate.D128_BLOCK_RECEIPT)
        matrix = gate.load_json(gate.COMPETITOR_MATRIX)

        fusion["route_matrix"]["fused_savings_bytes_total"] = 0
        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "fusion metrics must be positive"):
            gate._component_rows(fusion, d64, d128, matrix)

        fusion = gate.load_json(gate.FUSION_MECHANISM)
        d128["summary"]["mutations_rejected"] = d128["summary"]["mutation_cases"] - 1
        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "d128 mutation rejection count drift"):
            gate._component_rows(fusion, d64, d128, matrix)

        d128 = gate.load_json(gate.D128_BLOCK_RECEIPT)
        nanozk_block_row = next(
            row
            for row in matrix["external_rows"]
            if row.get("system") == "NANOZK"
            and row.get("workload_label") == "Transformer block proof"
            and row.get("workload_scope") == "Per-layer block proof"
        )
        nanozk_block_row["proof_size_reported"] = "1 byte"
        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "NANOZK row drift"):
            gate._component_rows(fusion, d64, d128, matrix)

        matrix = gate.load_json(gate.COMPETITOR_MATRIX)
        nanozk_block_row = next(
            row
            for row in matrix["external_rows"]
            if row.get("system") == "NANOZK"
            and row.get("workload_label") == "Transformer block proof"
            and row.get("workload_scope") == "Per-layer block proof"
        )
        nanozk_block_row.pop("model_or_dims", None)
        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "NANOZK row drift: model_or_dims"):
            gate._component_rows(fusion, d64, d128, matrix)

    def test_tsv_contains_component_rows(self):
        tsv = gate.to_tsv(self.payload)
        self.assertIn("attention/Softmax-table fused proof component\tattention", tsv)
        self.assertIn("d128 RMSNorm/SwiGLU/residual receipt chain\tbounded_mlp_substitute", tsv)
        self.assertIn("NANOZK transformer block context\texternal_context", tsv)

    def test_write_outputs_round_trip_and_rejects_outside_path(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="one-block-surface-test-",
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
            self.assertIn("surface", tsv_path.read_text(encoding="utf-8"))
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "repo-relative"):
                gate.write_outputs(self.payload, pathlib.Path(tmp) / "out.json", None)

        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "json and tsv output paths must differ"):
            gate.write_outputs(
                self.payload,
                pathlib.Path("docs/engineering/evidence/one-block-case-collision.JSON"),
                pathlib.Path("docs/engineering/evidence/one-block-case-collision.json"),
            )

    def test_write_outputs_rolls_back_when_second_replace_fails(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="one-block-transaction-json-",
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
            def fail_on_tsv(src, dst, *args, **kwargs):
                if pathlib.Path(dst).name == tsv_path.name:
                    raise OSError("simulated second replace failure")
                return original_replace(src, dst, *args, **kwargs)

            def fail_direct_write(_path, _contents):
                raise AssertionError("rollback must restore through an atomic temp replace")

            gate.os.replace = fail_on_tsv
            pathlib.Path.write_bytes = fail_direct_write
            with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "failed to write output path"):
                gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json_path.read_text(encoding="utf-8"), "original-json")
            self.assertFalse(tsv_path.exists())
        finally:
            gate.os.replace = original_replace
            pathlib.Path.write_bytes = original_write_bytes
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_json_helpers_reject_non_finite_values(self):
        payload = copy.deepcopy(self.payload)
        payload["summary"]["d128_over_d64_checked_row_ratio"] = math.nan
        with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "invalid JSON value"):
            gate.canonical_json_bytes(payload)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.ENGINEERING_EVIDENCE,
            prefix="one-block-non-finite-",
            suffix=".json",
            delete=False,
        ) as handle:
            path = pathlib.Path(handle.name)
            handle.write('{"value": Infinity}\n')
        try:
            with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "non-finite JSON constant"):
                gate.load_json(path)
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
            with self.assertRaisesRegex(gate.OneTransformerBlockSurfaceError, "symlinks"):
                gate.read_source_bytes(link_path, "symlink test")


if __name__ == "__main__":
    unittest.main()
