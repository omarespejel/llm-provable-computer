from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "zkai_range_disciplined_activation_receipt.py"
SPEC = importlib.util.spec_from_file_location("zkai_range_disciplined_activation_receipt", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load {SCRIPT}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class RangeDisciplinedActivationReceiptTests(unittest.TestCase):
    def test_payload_is_go_and_fail_closed(self) -> None:
        payload = PROBE.build_payload()

        self.assertEqual(payload["decision"], PROBE.DECISION)
        self.assertEqual(payload["summary"]["baseline_scale_status"], "NO_GO")
        self.assertEqual(payload["summary"]["scaled_go_count"], 4)
        self.assertEqual(payload["summary"]["case_count"], 5)
        self.assertEqual(payload["summary"]["mutations_checked"], 35)
        self.assertEqual(payload["summary"]["mutations_rejected"], 35)
        self.assertTrue(payload["summary"]["all_receipts_fail_closed"])

    def test_receipt_binds_scale_and_range_contract(self) -> None:
        source = PROBE.load_source_evidence()
        row = source["relu_scaling_probe"][1]
        receipt = PROBE.build_receipt(source, row)

        self.assertTrue(PROBE.verify_receipt(receipt, source))
        tampered = copy.deepcopy(receipt)
        tampered["range_contract"]["scale"] = "0.333"

        with self.assertRaisesRegex(PROBE.RangeActivationReceiptError, "scale"):
            PROBE.verify_receipt(tampered, source)

    def test_receipt_binds_backend_gate_status(self) -> None:
        source = PROBE.load_source_evidence()
        row = source["relu_scaling_probe"][0]
        receipt = PROBE.build_receipt(source, row)
        tampered = copy.deepcopy(receipt)
        tampered["range_contract"]["backend_gate"]["status"] = "GO"

        with self.assertRaisesRegex(PROBE.RangeActivationReceiptError, "range_contract|config_commitment|public_instance"):
            PROBE.verify_receipt(tampered, source)

    def test_source_evidence_conclusion_is_required(self) -> None:
        source = PROBE.load_source_evidence()
        source["conclusion"]["relu_scaling"] = "INPUT_DEPENDENT"

        with self.assertRaisesRegex(PROBE.RangeActivationReceiptError, "scaling conclusion"):
            PROBE.validate_source_evidence(source)

    def test_source_evidence_softmax_conclusion_is_required(self) -> None:
        source = PROBE.load_source_evidence()
        source["conclusion"].pop("softmax_source_check")

        with self.assertRaisesRegex(PROBE.RangeActivationReceiptError, "Softmax source-check"):
            PROBE.validate_source_evidence(source)

    def test_payload_validation_rejects_missing_mutation_rejection(self) -> None:
        payload = PROBE.build_payload()
        payload["cases"][0]["mutations_rejected"] -= 1

        with self.assertRaisesRegex(PROBE.RangeActivationReceiptError, "mutation rejection"):
            PROBE.validate_payload(payload)

    def test_payload_validation_rejects_detailed_mutation_drift(self) -> None:
        payload = PROBE.build_payload()
        payload["cases"][0]["mutation_cases"][0]["rejected"] = False

        with self.assertRaisesRegex(PROBE.RangeActivationReceiptError, "mutation case rejection"):
            PROBE.validate_payload(payload)

    def test_payload_validation_rejects_summary_counter_drift(self) -> None:
        payload = PROBE.build_payload()
        payload["summary"]["scaled_go_count"] -= 1

        with self.assertRaisesRegex(PROBE.RangeActivationReceiptError, "summary scaled GO"):
            PROBE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        payload = PROBE.build_payload()

        self.assertEqual(PROBE.to_tsv(payload).splitlines()[0].split("\t"), list(PROBE.TSV_COLUMNS))

    def test_write_outputs_round_trips(self) -> None:
        payload = PROBE.build_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_out = tmp / "out.json"
            tsv_out = tmp / "out.tsv"
            PROBE.write_outputs(payload, json_out, tsv_out)

            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            PROBE.validate_payload(loaded)
            self.assertTrue(tsv_out.read_text(encoding="utf-8").startswith("case_id\t"))


if __name__ == "__main__":
    unittest.main()
