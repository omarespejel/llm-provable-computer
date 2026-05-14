from __future__ import annotations

import copy
import json
import pathlib
import tempfile
import unittest

from scripts import zkai_one_block_executable_package_accounting_gate as gate


class OneBlockExecutablePackageAccountingGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload_base = gate.build_payload()

    def setUp(self) -> None:
        self.payload = copy.deepcopy(self.payload_base)

    def test_builds_package_accounting_without_native_proof_overclaim(self) -> None:
        gate.validate_payload(self.payload)
        self.assertEqual(self.payload["schema"], gate.SCHEMA)
        self.assertEqual(self.payload["decision"], gate.DECISION)
        self.assertEqual(self.payload["result"], gate.RESULT)
        self.assertEqual(self.payload["claim_boundary"], gate.CLAIM_BOUNDARY)
        self.assertEqual(len(self.payload["source_artifacts"]), 3)
        self.assertEqual(len(self.payload["package_rows"]), 4)
        self.assertEqual(self.payload["case_count"], len(gate.MUTATION_NAMES))
        self.assertTrue(self.payload["all_mutations_rejected"])

        summary = self.payload["summary"]
        self.assertEqual(summary["source_statement_chain_bytes"], 14624)
        self.assertEqual(summary["compressed_statement_chain_bytes"], 2559)
        self.assertEqual(summary["snark_proof_bytes"], 807)
        self.assertEqual(summary["snark_public_signals_bytes"], 1386)
        self.assertEqual(summary["snark_verification_key_bytes"], 5856)
        self.assertEqual(summary["package_without_vk_bytes"], 4752)
        self.assertEqual(summary["package_without_vk_ratio_vs_source"], 0.324945)
        self.assertEqual(summary["package_without_vk_saving_bytes"], 9872)
        self.assertEqual(summary["package_without_vk_saving_share"], 0.675055)
        self.assertEqual(summary["package_with_vk_bytes"], 10608)
        self.assertEqual(summary["package_with_vk_ratio_vs_source"], 0.725383)
        self.assertEqual(summary["package_with_vk_saving_bytes"], 4016)
        self.assertEqual(summary["package_with_vk_saving_share"], 0.274617)
        self.assertIn("NO-GO", summary["no_go_result"])
        self.assertIn("not native proof-size evidence for a fused route", self.payload["non_claims"])

    def test_package_rows_are_stable(self) -> None:
        rows = {row["surface"]: row for row in self.payload["package_rows"]}
        self.assertEqual(rows["source statement-chain artifact"]["bytes"], 14624)
        self.assertEqual(rows["compressed statement-chain artifact"]["bytes"], 2559)
        self.assertEqual(rows["compressed artifact plus proof plus public signals"]["bytes"], 4752)
        self.assertEqual(
            rows["compressed artifact plus proof plus public signals plus verification key"]["bytes"],
            10608,
        )
        self.assertEqual(
            rows["compressed artifact plus proof plus public signals"]["scope"],
            "per-receipt package when verification key is reusable",
        )

    def test_mutations_reject_relevant_drift(self) -> None:
        cases = {case["mutation"]: case for case in self.payload["cases"]}
        for name in gate.MUTATION_NAMES:
            self.assertIn(name, cases)
            self.assertTrue(cases[name]["rejected"], name)
            self.assertTrue(cases[name]["error"], name)
        self.assertIn("summary drift", cases["package_without_vk_bytes_drift"]["error"])
        self.assertIn("claim boundary drift", cases["claim_boundary_native_overclaim"]["error"])
        self.assertIn("non-claims drift", cases["non_claim_removed"]["error"])

    def test_rejects_payload_and_commitment_drift(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["summary"]["package_with_vk_bytes"] = 1
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.OneBlockPackageAccountingError, "payload drift"):
            gate.validate_payload(payload)

        payload = copy.deepcopy(self.payload)
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.OneBlockPackageAccountingError, "payload commitment drift"):
            gate.validate_payload(payload)

    def test_source_validation_rejects_metric_smuggling(self) -> None:
        _scorecard, compression, snark, _sources = gate.checked_sources()
        compression["summary"]["source_chain_artifact_bytes"] = 1
        with self.assertRaisesRegex(gate.OneBlockPackageAccountingError, "package summary drift"):
            gate.package_summary(compression, snark)

        _scorecard, compression, snark, _sources = gate.checked_sources()
        snark["receipt_metrics"]["proof_size_bytes"] = 1
        with self.assertRaisesRegex(gate.OneBlockPackageAccountingError, "package summary drift"):
            gate.package_summary(compression, snark)

    def test_tsv_and_write_outputs(self) -> None:
        tsv = gate.to_tsv(self.payload)
        self.assertIn("compressed artifact plus proof plus public signals\t4752\t0.324945\t9872", tsv)
        self.assertIn(
            "compressed artifact plus proof plus public signals plus verification key\t10608\t0.725383\t4016",
            tsv,
        )

        with tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix="one-block-package-accounting-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        try:
            gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), self.payload)
            self.assertIn("surface", tsv_path.read_text(encoding="utf-8"))
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.OneBlockPackageAccountingError, "repo-relative"):
                gate.write_outputs(self.payload, pathlib.Path(tmp) / "out.json", None)

    def test_write_outputs_rolls_back_when_second_replace_fails(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix="one-block-package-accounting-json-",
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
            with self.assertRaisesRegex(gate.OneBlockPackageAccountingError, "failed to write output path"):
                gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json_path.read_text(encoding="utf-8"), "original-json")
            self.assertFalse(tsv_path.exists())
        finally:
            gate.os.replace = original_replace
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_load_json_rejects_non_finite_constants(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.EVIDENCE_DIR,
            prefix="one-block-package-accounting-non-finite-",
            suffix=".json",
            delete=False,
        ) as handle:
            path = pathlib.Path(handle.name)
            handle.write('{"value": Infinity}\n')
        try:
            with self.assertRaisesRegex(gate.OneBlockPackageAccountingError, "non-finite JSON constant"):
                gate.load_json(path)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
