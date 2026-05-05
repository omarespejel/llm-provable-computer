from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_risc0_statement_receipt_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_risc0_statement_receipt_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 RISC Zero receipt gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128Risc0StatementReceiptGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not GATE.JSON_OUT.exists():
            raise unittest.SkipTest("RISC Zero statement receipt evidence has not been generated yet")
        cls.payload = json.loads(GATE.JSON_OUT.read_text(encoding="utf-8"))
        GATE.validate_payload(cls.payload)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_checked_payload_records_real_risc0_go(self) -> None:
        payload = self.fresh_payload()

        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["evidence_schema"], GATE.EVIDENCE_SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["route_id"], "risc0_zkvm_statement_receipt")
        self.assertEqual(payload["system"], "RISC Zero")
        self.assertEqual(payload["issue"], 433)
        self.assertEqual(payload["source_issue"], 424)
        self.assertEqual(payload["adapter_issue"], 422)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertEqual({case["mutation"] for case in payload["cases"]}, GATE.EXPECTED_MUTATION_SET)

    def test_receipt_artifact_and_verification_are_bound_to_current_journal(self) -> None:
        payload = self.fresh_payload()
        artifact = payload["receipt_artifact"]
        verification = payload["receipt_verification"]

        self.assertTrue((GATE.ROOT / artifact["path"]).is_file())
        self.assertGreater(artifact["size_bytes"], 0)
        self.assertLessEqual(artifact["size_bytes"], GATE.MAX_RECEIPT_BYTES)
        self.assertEqual(artifact["commitment"], payload["receipt_commitment"])
        self.assertEqual(verification["host_summary_schema"], "zkai-d128-risc0-host-summary-v1")
        self.assertEqual(verification["host_summary_mode"], "verify")
        self.assertTrue(verification["strict_receipt_reverified"])
        self.assertTrue(verification["verifier_executed"])
        self.assertTrue(verification["receipt_verified"])
        self.assertTrue(verification["decoded_journal_matches_expected"])
        self.assertEqual(verification["journal_sha256"], GATE.sha256_bytes(GATE.expected_journal_bytes()))
        self.assertEqual(len(verification["image_id_hex"]), 64)
        self.assertEqual(verification["risc0_zkvm_version"], GATE.RISC0_ZKVM_VERSION)

    def test_metrics_are_single_local_engineering_only(self) -> None:
        metrics = self.fresh_payload()["proof_metrics"]

        self.assertTrue(metrics["metrics_enabled"])
        self.assertEqual(metrics["timing_policy"], "single_local_run_engineering_only")
        self.assertGreater(metrics["proof_size_bytes"], 0)
        self.assertGreater(metrics["proof_generation_time_ms"], 0)
        self.assertGreater(metrics["verifier_time_ms"], 0)

    def test_rejects_journal_policy_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["journal_contract"]["policy_label"] = "fake-policy"

        with self.assertRaisesRegex(GATE.D128Risc0StatementReceiptError, "journal contract mismatch") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "journal_contract")

    def test_rejects_receipt_commitment_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["receipt_commitment"] = "blake2b-256:" + "33" * 32

        with self.assertRaisesRegex(GATE.D128Risc0StatementReceiptError, "receipt commitment") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "receipt_metadata")

    def test_rejects_strict_reverification_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["receipt_verification"]["strict_receipt_reverified"] = False

        with self.assertRaisesRegex(GATE.D128Risc0StatementReceiptError, "strict receipt") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "receipt_metadata")

    def test_rejects_receipt_path_traversal(self) -> None:
        payload = self.fresh_payload()
        payload["receipt_artifact"]["path"] = "../outside-repo-receipt.bincode"

        with self.assertRaisesRegex(GATE.D128Risc0StatementReceiptError, "escapes repository root") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "receipt_artifact")

    def test_rejects_metric_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["proof_metrics"]["verifier_time_ms"] = 1.0

        with self.assertRaisesRegex(GATE.D128Risc0StatementReceiptError, "verify time") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "proof_metrics")

    def test_rejects_missing_receipt_artifact(self) -> None:
        payload = self.fresh_payload()
        payload["receipt_artifact"]["path"] = "docs/engineering/evidence/missing-risc0-receipt.bincode"

        with self.assertRaisesRegex(GATE.D128Risc0StatementReceiptError, "receipt artifact missing") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "receipt_artifact")

    def test_verify_existing_requires_existing_json_for_prove_time(self) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = [
                str(SCRIPT_PATH),
                "--verify-existing",
                "--receipt",
                str(GATE.RECEIPT_OUT),
            ]
            with self.assertRaisesRegex(GATE.D128Risc0StatementReceiptError, "requires --write-json"):
                GATE.main()

            sys.argv = [
                str(SCRIPT_PATH),
                "--verify-existing",
                "--receipt",
                str(GATE.RECEIPT_OUT),
                "--write-json",
                "target/missing-risc0-statement-receipt.json",
            ]
            with self.assertRaisesRegex(GATE.D128Risc0StatementReceiptError, "requires an existing RISC Zero evidence JSON"):
                GATE.main()
        finally:
            sys.argv = old_argv

    def test_tsv_contains_stable_risc0_row(self) -> None:
        text = GATE.to_tsv(self.fresh_payload())
        lines = text.splitlines()

        self.assertEqual(lines[0].split("\t"), list(GATE.TSV_COLUMNS))
        self.assertIn("risc0_zkvm_statement_receipt", lines[1])
        self.assertIn(GATE.DECISION, lines[1])


if __name__ == "__main__":
    unittest.main()
