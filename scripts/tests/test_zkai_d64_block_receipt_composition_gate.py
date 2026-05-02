from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_block_receipt_composition_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_block_receipt_composition_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load block receipt composition gate from {SCRIPT_PATH}")
COMPOSITION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COMPOSITION
SPEC.loader.exec_module(COMPOSITION)


class ZkAiD64BlockReceiptCompositionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = COMPOSITION.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_result_is_go_and_rejects_all_mutations(self) -> None:
        payload = self.fresh_payload()
        COMPOSITION.validate_payload(payload)
        self.assertEqual(payload["schema"], COMPOSITION.SCHEMA)
        self.assertEqual(payload["decision"], COMPOSITION.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["summary"]["slice_count"], 6)
        self.assertEqual(payload["summary"]["total_checked_rows"], 49600)
        self.assertEqual(payload["case_count"], 14)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["summary"]["mutations_rejected"], 14)
        self.assertEqual(
            payload["block_receipt"]["output_activation_commitment"],
            COMPOSITION.OUTPUT_ACTIVATION_COMMITMENT,
        )

    def test_receipt_commitment_round_trips(self) -> None:
        payload = self.fresh_payload()
        receipt = payload["block_receipt"]
        expected = COMPOSITION.blake2b_commitment(
            COMPOSITION._receipt_payload_for_commitment(receipt),
            "ptvm:zkai:d64-block:receipt:v1",
        )
        self.assertEqual(receipt["block_receipt_commitment"], expected)

    def test_rejects_missing_reordered_and_duplicated_slice_chain(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        for mutation in (
            "missing_bridge_slice",
            "reordered_bridge_and_projection",
            "duplicated_final_slice_missing_down",
        ):
            with self.subTest(mutation=mutation):
                self.assertTrue(cases[mutation]["rejected"])
                self.assertEqual(cases[mutation]["rejection_layer"], "slice_chain_shape")

    def test_rejects_stale_commitment_edges(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["stale_hidden_activation_edge"]["rejection_layer"], "commitment_chain")
        self.assertIn("activation-to-down", cases["stale_hidden_activation_edge"]["error"])
        self.assertEqual(cases["stale_residual_delta_edge"]["rejection_layer"], "commitment_chain")
        self.assertIn("down-to-residual", cases["stale_residual_delta_edge"]["error"])

    def test_rejects_source_manifest_hash_drift_after_outer_recommit(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertTrue(cases["source_file_hash_drift"]["rejected"])
        self.assertEqual(cases["source_file_hash_drift"]["rejection_layer"], "source_evidence_manifest")
        self.assertIn("source file hash", cases["source_file_hash_drift"]["error"])
        self.assertTrue(cases["source_payload_hash_drift"]["rejected"])
        self.assertEqual(cases["source_payload_hash_drift"]["rejection_layer"], "source_evidence_manifest")
        self.assertIn("source payload hash", cases["source_payload_hash_drift"]["error"])

    def test_rejects_extra_source_manifest_entry(self) -> None:
        payload = self.fresh_payload()
        extra = copy.deepcopy(payload["source_evidence_manifest"][0])
        extra["index"] = len(payload["source_evidence_manifest"])
        extra["slice_id"] = "unexpected_extra_slice"
        payload["source_evidence_manifest"].append(extra)
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "source evidence manifest order"):
            COMPOSITION.validate_payload(payload)

    def test_rejects_self_consistent_wrong_model_config(self) -> None:
        payload = self.fresh_payload()
        payload["block_receipt"]["model_config"]["width"] = 128
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "model_config"):
            COMPOSITION.validate_payload(payload)

    def test_rejects_self_consistent_stale_output_commitment(self) -> None:
        payload = self.fresh_payload()
        payload["block_receipt"]["output_activation_commitment"] = "blake2b-256:" + "44" * 32
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "output_activation_commitment"):
            COMPOSITION.validate_payload(payload)

    def test_rejects_malformed_slice_row_count_without_raw_exception(self) -> None:
        for value in (None, "64", 0, -1, True):
            with self.subTest(row_count=value):
                payload = self.fresh_payload()
                if value is None:
                    del payload["slice_chain"][0]["row_count"]
                else:
                    payload["slice_chain"][0]["row_count"] = value
                COMPOSITION.refresh_commitments(payload)
                with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "row_count"):
                    COMPOSITION.validate_payload(payload)

    def test_rejects_missing_slice_commitment_key_without_raw_exception(self) -> None:
        payload = self.fresh_payload()
        del payload["slice_chain"][5]["source_commitments"]["residual_delta_commitment"]
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "source commitment keys"):
            COMPOSITION.validate_payload(payload)

    def test_receipt_commitment_mutations_report_block_receipt_layer(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["verifier_domain_drift"]["rejection_layer"], "block_receipt")
        self.assertIn("block receipt verifier_domain", cases["verifier_domain_drift"]["error"])
        self.assertEqual(cases["input_commitment_drift"]["rejection_layer"], "block_receipt")
        self.assertIn("block receipt input_activation_commitment", cases["input_commitment_drift"]["error"])
        self.assertEqual(cases["output_commitment_drift"]["rejection_layer"], "block_receipt")
        self.assertIn("block receipt output_activation_commitment", cases["output_commitment_drift"]["error"])

    def test_rejects_public_rmsnorm_row_relation_drift(self) -> None:
        source = COMPOSITION.source_payloads()
        source["rmsnorm_public_rows"]["rows"][0]["normed_q8"] += 1
        with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "normed relation"):
            COMPOSITION.validate_rmsnorm_public_row(source["rmsnorm_public_rows"])

    def test_rejects_down_projection_residual_delta_source_drift(self) -> None:
        source = COMPOSITION.source_payloads()
        source["down_projection"]["residual_delta_commitment"] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "down-to-residual"):
            COMPOSITION.build_payload(source)

    def test_tsv_columns_are_stable(self) -> None:
        header = COMPOSITION.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), COMPOSITION.TSV_COLUMNS)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "block-receipt.json"
            tsv_path = tmp / "block-receipt.tsv"
            COMPOSITION.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("missing_bridge_slice", tsv_path.read_text(encoding="utf-8"))

    def test_load_json_rejects_oversized_repo_local_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            path = pathlib.Path(raw_tmp) / "oversized.json"
            path.write_text(" " * (COMPOSITION.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "exceeds max size"):
                COMPOSITION.load_json(path)

    def test_load_json_rejects_invalid_utf8_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            path = pathlib.Path(raw_tmp) / "invalid.json"
            path.write_bytes(b"\xff")
            with self.assertRaisesRegex(COMPOSITION.D64BlockReceiptError, "failed to load"):
                COMPOSITION.load_json(path)


if __name__ == "__main__":
    unittest.main()
