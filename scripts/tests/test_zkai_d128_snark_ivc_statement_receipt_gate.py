from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "scripts" / "zkai_d128_snark_ivc_statement_receipt_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_snark_ivc_statement_receipt_gate", GATE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load gate from {GATE_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


def fake_external_verify(_proof, public_signals, _verification_key) -> None:
    if public_signals[0] == "12345":
        raise GATE.D128SnarkReceiptError("fake proof verifier rejected public signal", layer="external_proof_verifier")


class D128SnarkIvcStatementReceiptGateTests(unittest.TestCase):
    def test_baseline_receipt_binds_expected_contract_public_signals(self) -> None:
        receipt = GATE.baseline_receipt()
        statement = receipt["statement"]

        self.assertEqual(receipt["statement_commitment"], GATE.statement_commitment(statement))
        self.assertEqual(receipt["receipt_commitment"], GATE.receipt_commitment(receipt))
        self.assertEqual(len(statement["public_signal_field_entries"]), 16)
        self.assertEqual(len(receipt["public_signals"]), 17)
        self.assertEqual(receipt["public_signals"], GATE.expected_public_signals(statement["public_signal_field_entries"]))
        self.assertEqual(
            statement["source_contract"]["public_input_contract"]["two_slice_target_commitment"],
            "blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6",
        )

    def test_gate_records_go_and_rejects_full_mutation_inventory(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertEqual({case["mutation"] for case in payload["cases"]}, GATE.EXPECTED_MUTATION_SET)
        self.assertEqual(
            payload["proof_verifier_checks"]["public_signal_relabeling"]["rejection_layer"],
            "external_proof_verifier",
        )

    def test_raw_proof_only_accepts_semantic_relabel_but_statement_receipt_rejects(self) -> None:
        _surface, relabeled = GATE.mutated_receipts()["target_commitment_relabeling"]

        GATE.verify_proof_only(relabeled, external_verify=fake_external_verify)
        with self.assertRaisesRegex(GATE.D128SnarkReceiptError, "source_contract mismatch") as err:
            GATE.verify_statement_receipt(relabeled, external_verify=fake_external_verify)
        self.assertEqual(err.exception.layer, "statement_policy")

    def test_public_signal_drift_is_rejected_by_raw_snark_verifier_check(self) -> None:
        check = GATE.proof_verifier_public_signal_check(GATE.baseline_receipt(), fake_external_verify)

        self.assertTrue(check["rejected"])
        self.assertFalse(check["mutated_accepted"])
        self.assertEqual(check["rejection_layer"], "external_proof_verifier")

    def test_metric_smuggling_and_unknown_fields_fail_closed(self) -> None:
        for name in (
            "proof_size_metric_smuggled",
            "verifier_time_metric_smuggled",
            "proof_generation_time_metric_smuggled",
            "unknown_top_level_field_added",
        ):
            _surface, receipt = GATE.mutated_receipts()[name]
            with self.assertRaises(GATE.D128SnarkReceiptError):
                GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)

    def test_payload_validation_rejects_forged_summary(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        forged = copy.deepcopy(payload)
        forged["cases"][0]["rejected"] = False
        forged["cases"][0]["mutated_accepted"] = True

        with self.assertRaisesRegex(GATE.D128SnarkReceiptError, "not all SNARK receipt mutations rejected"):
            GATE.validate_payload(forged)

    def test_tsv_columns_are_stable(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(GATE.to_tsv(payload).splitlines()[0].split("\t"), list(GATE.TSV_COLUMNS))

    def test_output_path_must_stay_under_evidence_dir(self) -> None:
        with self.assertRaisesRegex(GATE.D128SnarkReceiptError, "output path must stay"):
            GATE.write_text_checked(ROOT / "outside.json", "{}\n")

    def test_checked_json_artifact_matches_current_schema_when_present(self) -> None:
        path = GATE.JSON_OUT
        if not path.exists():
            self.skipTest("JSON evidence has not been generated yet")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertTrue(payload["all_mutations_rejected"])


if __name__ == "__main__":
    unittest.main()
