from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_kv_risc0_semantics_receipt_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_kv_risc0_semantics_receipt_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load attention/KV RISC Zero receipt gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiAttentionKvRisc0SemanticsReceiptGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not GATE.JSON_OUT.exists():
            raise unittest.SkipTest("attention/KV RISC Zero semantics receipt evidence has not been generated yet")
        cls.payload = json.loads(GATE.JSON_OUT.read_text(encoding="utf-8"))
        GATE.validate_payload(cls.payload)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_checked_payload_records_narrow_risc0_semantics_go(self) -> None:
        payload = self.fresh_payload()

        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["route_id"], "risc0_attention_kv_transition_semantics_receipt")
        self.assertEqual(payload["system"], "RISC Zero")
        self.assertEqual(payload["issue"], 441)
        self.assertEqual(payload["source_issue"], 336)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertEqual({case["mutation"] for case in payload["cases"]}, GATE.EXPECTED_MUTATION_SET)

    def test_guest_journal_matches_reference_attention_kv_semantics(self) -> None:
        payload = self.fresh_payload()
        journal = payload["journal"]

        self.assertEqual(journal, GATE.expected_journal())
        self.assertEqual(journal["schema"], GATE.JOURNAL_SCHEMA)
        self.assertEqual(journal["semantics"], GATE.SEMANTICS)
        self.assertEqual(journal["selected_position"], 0)
        self.assertEqual(journal["attention_output"], [2, 1])
        self.assertEqual(len(journal["next_kv_cache"]), 3)
        self.assertEqual(journal["scores"], GATE.source_transition()["scores"])

    def test_source_statement_fields_are_bound_to_guest_journal(self) -> None:
        payload = self.fresh_payload()

        self.assertEqual(payload["source_statement_fields"], GATE.expected_source_statement_fields())
        GATE.validate_source_statement_fields(payload["source_statement_fields"], payload["journal"])

    def test_receipt_artifact_and_verification_are_bound_to_current_journal(self) -> None:
        payload = self.fresh_payload()
        artifact = payload["receipt_artifact"]
        verification = payload["receipt_verification"]

        self.assertTrue((GATE.ROOT / artifact["path"]).is_file())
        self.assertGreater(artifact["size_bytes"], 0)
        self.assertLessEqual(artifact["size_bytes"], GATE.MAX_RECEIPT_BYTES)
        self.assertEqual(artifact["commitment"], payload["receipt_commitment"])
        self.assertEqual(verification["host_summary_schema"], "zkai-attention-kv-risc0-host-summary-v1")
        self.assertEqual(verification["host_summary_mode"], "verify")
        self.assertTrue(verification["strict_receipt_reverified"])
        self.assertTrue(verification["verifier_executed"])
        self.assertTrue(verification["receipt_verified"])
        self.assertTrue(verification["decoded_journal_matches_expected"])
        self.assertEqual(verification["journal_sha256"], GATE.sha256_bytes(GATE.host_json_bytes(GATE.expected_journal())))
        self.assertEqual(len(verification["image_id_hex"]), 64)
        self.assertEqual(verification["risc0_zkvm_version"], GATE.RISC0_ZKVM_VERSION)

    def test_metrics_are_single_local_engineering_only(self) -> None:
        metrics = self.fresh_payload()["proof_metrics"]

        self.assertTrue(metrics["metrics_enabled"])
        self.assertEqual(metrics["timing_policy"], "single_local_run_engineering_only")
        self.assertGreater(metrics["proof_size_bytes"], 0)
        self.assertGreater(metrics["proof_generation_time_ms"], 0)
        self.assertGreater(metrics["verifier_time_ms"], 0)

    def test_rejects_guest_journal_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["journal"]["attention_output"] = [0, 0]

        with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "journal mismatch") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "journal_semantics")

    def test_rejects_source_statement_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["source_statement_fields"]["statement_commitment"] = "blake2b-256:" + "66" * 32

        with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "source statement fields mismatch") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "source_statement_contract")

    def test_rejects_receipt_commitment_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["receipt_commitment"] = "blake2b-256:" + "33" * 32

        with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "receipt commitment") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "receipt_metadata")

    def test_rejects_strict_reverification_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["receipt_verification"]["strict_receipt_reverified"] = False

        with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "strict receipt") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "receipt_metadata")

    def test_rejects_receipt_path_traversal(self) -> None:
        payload = self.fresh_payload()
        payload["receipt_artifact"]["path"] = "../outside-repo-receipt.bincode"

        with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "escapes repository root") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "receipt_artifact")

    def test_rejects_metric_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["proof_metrics"]["verifier_time_ms"] = 1.0

        with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "verify time") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "proof_metrics")

    def test_rejects_claim_boundary_overreach(self) -> None:
        payload = self.fresh_payload()
        payload["claim_boundary"] = "NATIVE_STWO_ATTENTION_KV_PROOF"

        with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "claim boundary") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "parser_or_schema")

    def test_verify_existing_requires_existing_json_for_prove_time(self) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = [
                str(SCRIPT_PATH),
                "--verify-existing",
                "--receipt",
                str(GATE.RECEIPT_OUT),
            ]
            with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "requires --write-json"):
                GATE.main()

            sys.argv = [
                str(SCRIPT_PATH),
                "--verify-existing",
                "--receipt",
                str(GATE.RECEIPT_OUT),
                "--write-json",
                "target/missing-attention-kv-risc0-semantics-receipt.json",
            ]
            with self.assertRaisesRegex(GATE.AttentionKvRisc0SemanticsReceiptError, "requires an existing attention/KV RISC Zero evidence JSON"):
                GATE.main()
        finally:
            sys.argv = old_argv

    def test_tsv_contains_stable_risc0_semantics_row(self) -> None:
        text = GATE.to_tsv(self.fresh_payload())
        lines = text.splitlines()

        self.assertEqual(lines[0].split("\t"), list(GATE.TSV_COLUMNS))
        self.assertIn("risc0_attention_kv_transition_semantics_receipt", lines[1])
        self.assertIn(GATE.DECISION, lines[1])


if __name__ == "__main__":
    unittest.main()
