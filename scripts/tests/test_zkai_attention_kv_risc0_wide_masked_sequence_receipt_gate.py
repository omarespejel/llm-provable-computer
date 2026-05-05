from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load attention/KV RISC Zero wide masked sequence receipt gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiAttentionKvRisc0WideMaskedSequenceReceiptGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not GATE.JSON_OUT.exists():
            raise AssertionError(f"required attention/KV RISC Zero wide masked sequence receipt evidence is missing: {GATE.JSON_OUT}")
        cls.payload = json.loads(GATE.JSON_OUT.read_text(encoding="utf-8"))
        GATE.validate_payload(cls.payload)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_risc0_env_does_not_add_empty_path_entry(self) -> None:
        with mock.patch.dict(os.environ, {"HOME": "/tmp/risc0-test-home", "PATH": ""}):
            env = GATE.risc0_env()

        self.assertNotIn("", env["PATH"].split(os.pathsep))

    def test_checked_receipt_reverifies_with_local_risc0_toolchain(self) -> None:
        available, reason = GATE.local_risc0_toolchain_available()
        if not available:
            self.skipTest(f"RISC Zero toolchain unavailable for strict receipt re-verification: {reason}")

        GATE.validate_payload(self.fresh_payload(), strict_receipt=True)

    def test_checked_payload_records_carried_sequence_go(self) -> None:
        payload = self.fresh_payload()

        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["route_id"], "risc0_attention_kv_wide_masked_sequence_semantics_receipt")
        self.assertEqual(payload["system"], "RISC Zero")
        self.assertEqual(payload["issue"], 446)
        self.assertEqual(payload["source_issue"], 444)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertEqual({case["mutation"] for case in payload["cases"]}, GATE.EXPECTED_MUTATION_SET)

    def test_guest_journal_binds_eight_carried_kv_transitions(self) -> None:
        payload = self.fresh_payload()
        journal = payload["journal"]

        self.assertEqual(journal, GATE.expected_journal())
        self.assertEqual(journal["schema"], GATE.JOURNAL_SCHEMA)
        self.assertEqual(journal["semantics"], GATE.SEMANTICS)
        self.assertEqual(journal["masking_policy"], GATE.MASKING_POLICY)
        self.assertEqual(journal["sequence_length"], 8)
        self.assertEqual(len(journal["transitions"]), 8)
        self.assertEqual([row["selected_position"] for row in journal["transitions"]], [0, 2, 3, 3, 5, 5, 7, 9])
        self.assertEqual(
            [row["attention_output"] for row in journal["transitions"]],
            [
                [2, 1, 0, -1, 3, 0, 1, 2],
                [4, 2, 1, 0, -1, 3, 2, 1],
                [5, -2, 0, 3, 1, 1, -1, 2],
                [5, -2, 0, 3, 1, 1, -1, 2],
                [7, 1, 2, -2, 0, 5, -3, 1],
                [7, 1, 2, -2, 0, 5, -3, 1],
                [6, 6, -2, 0, 2, 1, 3, -1],
                [-5, 5, 1, -3, 4, 2, -2, 0],
            ],
        )
        for idx in range(1, len(journal["transitions"])):
            self.assertEqual(journal["transitions"][idx]["prior_kv_cache"], journal["transitions"][idx - 1]["next_kv_cache"])
        self.assertEqual(journal["final_kv_cache"], journal["transitions"][-1]["next_kv_cache"])
        self.assertEqual(len(journal["final_kv_cache"]), 10)

    def test_transition_commitments_and_statement_fields_bind_journal(self) -> None:
        payload = self.fresh_payload()
        journal = payload["journal"]

        self.assertEqual(payload["transition_commitments"], GATE.transition_commitments(journal))
        expected_statement = GATE.statement_fields(
            journal,
            payload["receipt_commitment"],
            payload["receipt_verification"]["image_id_hex"],
        )
        self.assertEqual(payload["statement_fields"], expected_statement)
        GATE.validate_statement_fields(
            payload["statement_fields"],
            journal,
            payload["receipt_commitment"],
            payload["receipt_verification"]["image_id_hex"],
        )

    def test_receipt_artifact_and_reverification_are_bound_to_current_journal(self) -> None:
        payload = self.fresh_payload()
        artifact = payload["receipt_artifact"]
        verification = payload["receipt_verification"]

        self.assertTrue((GATE.ROOT / artifact["path"]).is_file())
        self.assertGreater(artifact["size_bytes"], 0)
        self.assertLessEqual(artifact["size_bytes"], GATE.MAX_RECEIPT_BYTES)
        self.assertEqual(artifact["commitment"], payload["receipt_commitment"])
        self.assertEqual(verification["host_summary_schema"], "zkai-attention-kv-risc0-wide-masked-sequence-host-summary-v1")
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

    def test_carried_prove_time_accepts_matching_receipt_artifact(self) -> None:
        payload = self.fresh_payload()
        receipt_path = GATE.ROOT / payload["receipt_artifact"]["path"]

        self.assertEqual(
            GATE.carried_proof_generation_time(payload, receipt_path.read_bytes()),
            payload["proof_metrics"]["proof_generation_time_ms"],
        )

    def test_carried_prove_time_does_not_cross_receipt_artifacts(self) -> None:
        payload = self.fresh_payload()
        receipt_path = GATE.ROOT / payload["receipt_artifact"]["path"]
        previous = copy.deepcopy(payload)
        previous["receipt_artifact"]["sha256"] = "00" * 32

        self.assertIsNone(GATE.carried_proof_generation_time(previous, receipt_path.read_bytes()))

    def test_receipt_path_rejects_source_tree_outputs(self) -> None:
        source_path = GATE.ROOT / "scripts" / "zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py"

        with self.assertRaisesRegex(GATE.AttentionKvRisc0WideMaskedSequenceReceiptError, "approved artifact directories") as err:
            GATE.require_allowed_receipt_path(source_path, label="receipt", layer="output_path")

        self.assertEqual(err.exception.layer, "output_path")

    def test_rejects_transition_deletion(self) -> None:
        payload = self.fresh_payload()
        payload["journal"]["transitions"].pop(1)

        with self.assertRaisesRegex(GATE.AttentionKvRisc0WideMaskedSequenceReceiptError, "journal mismatch") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "sequence_journal")

    def test_rejects_transition_reordering(self) -> None:
        payload = self.fresh_payload()
        payload["journal"]["transitions"].reverse()

        with self.assertRaisesRegex(GATE.AttentionKvRisc0WideMaskedSequenceReceiptError, "journal mismatch") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "sequence_journal")

    def test_rejects_intermediate_kv_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["journal"]["transitions"][1]["next_kv_cache"][2]["value"] = [0, 0, 0, 0, 0, 0, 0, 0]

        with self.assertRaisesRegex(GATE.AttentionKvRisc0WideMaskedSequenceReceiptError, "journal mismatch") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "sequence_journal")

    def test_rejects_statement_commitment_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["statement_fields"]["statement_commitment"] = "blake2b-256:" + "66" * 32

        with self.assertRaisesRegex(GATE.AttentionKvRisc0WideMaskedSequenceReceiptError, "statement fields mismatch") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "statement_contract")

    def test_rejects_metric_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["proof_metrics"]["verifier_time_ms"] = 1.0

        with self.assertRaisesRegex(GATE.AttentionKvRisc0WideMaskedSequenceReceiptError, "verify time") as err:
            GATE.validate_payload(payload)

        self.assertEqual(err.exception.layer, "proof_metrics")

    def test_verify_existing_requires_existing_json_for_prove_time(self) -> None:
        old_argv = sys.argv[:]
        try:
            sys.argv = [
                str(SCRIPT_PATH),
                "--verify-existing",
                "--receipt",
                str(GATE.RECEIPT_OUT),
            ]
            with self.assertRaisesRegex(GATE.AttentionKvRisc0WideMaskedSequenceReceiptError, "requires --write-json"):
                GATE.main()
        finally:
            sys.argv = old_argv

    def test_verify_existing_uses_canonical_evidence_not_stale_target_output(self) -> None:
        stale_target_output = GATE.ROOT / "target" / "stale-wide-masked-sequence-receipt-evidence.json"
        self.assertEqual(GATE.previous_evidence_path_for_verify(stale_target_output), GATE.JSON_OUT)
        self.assertEqual(GATE.previous_evidence_path_for_verify(GATE.JSON_OUT), GATE.JSON_OUT)

    def test_tsv_contains_stable_sequence_receipt_row(self) -> None:
        text = GATE.to_tsv(self.fresh_payload())
        self.assertTrue(GATE.TSV_OUT.is_file())
        self.assertEqual(GATE.TSV_OUT.read_text(encoding="utf-8"), text)
        lines = text.splitlines()

        self.assertEqual(lines[0].split("\t"), list(GATE.TSV_COLUMNS))
        self.assertIn("risc0_attention_kv_wide_masked_sequence_semantics_receipt", lines[1])
        self.assertIn(GATE.DECISION, lines[1])


if __name__ == "__main__":
    unittest.main()
