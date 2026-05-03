from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_block_receipt_composition_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_block_receipt_composition_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 block receipt composition gate from {SCRIPT_PATH}")
COMPOSITION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COMPOSITION
SPEC.loader.exec_module(COMPOSITION)

EXPECTED_OUTPUT_ACTIVATION_COMMITMENT = (
    "blake2b-256:869a0046bdaba3f6a7f98a3ffec618479c9dc91df2a342900c76f9ba53215fc1"
)


class ZkAiD128BlockReceiptCompositionGateTests(unittest.TestCase):
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
        self.assertEqual(payload["summary"]["total_checked_rows"], 197_504)
        self.assertEqual(payload["case_count"], 20)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["summary"]["mutations_rejected"], 20)
        self.assertEqual(
            payload["block_receipt"]["output_activation_commitment"],
            EXPECTED_OUTPUT_ACTIVATION_COMMITMENT,
        )

    def test_receipt_and_statement_commitments_round_trip(self) -> None:
        payload = self.fresh_payload()
        receipt = payload["block_receipt"]
        self.assertEqual(
            receipt["statement_commitment"],
            "blake2b-256:f808e10c539370b63f8f8300a0a6dfa9cb0fa02eed4ca3fbd83a378c4a0a2b60",
        )
        self.assertEqual(
            receipt["block_receipt_commitment"],
            "blake2b-256:a2cd8a3dc2f3a5d176fe0a569929fd6e146c4cccfab9aaa18a92a3da057b9c3a",
        )

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

    def test_rejects_stale_commitment_and_statement_edges(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        expected_layers = {
            "stale_projection_input_edge": "commitment_chain",
            "stale_gate_value_edge": "commitment_chain",
            "stale_hidden_activation_edge": "commitment_chain",
            "stale_residual_delta_edge": "commitment_chain",
            "stale_rmsnorm_statement_edge": "commitment_chain",
            "stale_down_statement_edge": "commitment_chain",
        }
        for mutation, layer in expected_layers.items():
            with self.subTest(mutation=mutation):
                self.assertTrue(cases[mutation]["rejected"])
                self.assertEqual(cases[mutation]["rejection_layer"], layer)

    def test_rejects_source_manifest_hash_drift_after_outer_recommit(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertTrue(cases["source_file_hash_drift"]["rejected"])
        self.assertEqual(cases["source_file_hash_drift"]["rejection_layer"], "source_evidence_manifest")
        self.assertIn("source file hash", cases["source_file_hash_drift"]["error"])
        self.assertTrue(cases["source_payload_hash_drift"]["rejected"])
        self.assertEqual(cases["source_payload_hash_drift"]["rejection_layer"], "source_evidence_manifest")
        self.assertIn("source payload hash", cases["source_payload_hash_drift"]["error"])

    def test_rejects_noncanonical_source_manifest_path(self) -> None:
        payload = self.fresh_payload()
        payload["source_evidence_manifest"][0]["path"] = str(
            (ROOT / payload["source_evidence_manifest"][0]["path"]).resolve()
        )
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "canonical path"):
            COMPOSITION.validate_payload(payload)

    def test_rejects_extra_source_manifest_entry(self) -> None:
        payload = self.fresh_payload()
        extra = copy.deepcopy(payload["source_evidence_manifest"][0])
        extra["index"] = len(payload["source_evidence_manifest"])
        extra["slice_id"] = "unexpected_extra_slice"
        payload["source_evidence_manifest"].append(extra)
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "source evidence manifest order"):
            COMPOSITION.validate_payload(payload)

    def test_rejects_self_consistent_wrong_model_config(self) -> None:
        payload = self.fresh_payload()
        payload["block_receipt"]["model_config"]["width"] = 64
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "model_config"):
            COMPOSITION.validate_payload(payload)

    def test_rejects_self_consistent_stale_output_commitment(self) -> None:
        payload = self.fresh_payload()
        payload["block_receipt"]["output_activation_commitment"] = "blake2b-256:" + "44" * 32
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "output_activation_commitment"):
            COMPOSITION.validate_payload(payload)

    def test_rejects_malformed_slice_row_count_without_raw_exception(self) -> None:
        for value in (None, "128", 0, -1, True):
            with self.subTest(row_count=value):
                payload = self.fresh_payload()
                if value is None:
                    del payload["slice_chain"][0]["row_count"]
                else:
                    payload["slice_chain"][0]["row_count"] = value
                COMPOSITION.refresh_commitments(payload)
                with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "row_count"):
                    COMPOSITION.validate_payload(payload)

    def test_rejects_missing_slice_commitment_key_without_raw_exception(self) -> None:
        payload = self.fresh_payload()
        del payload["slice_chain"][5]["source_commitments"]["source_down_projection_statement_commitment"]
        COMPOSITION.refresh_commitments(payload)
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "source commitment keys"):
            COMPOSITION.validate_payload(payload)

    def test_receipt_commitment_mutations_report_block_receipt_layer(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["verifier_domain_drift"]["rejection_layer"], "block_receipt")
        self.assertIn("block receipt verifier_domain", cases["verifier_domain_drift"]["error"])
        self.assertEqual(cases["input_commitment_drift"]["rejection_layer"], "block_receipt")
        self.assertIn("block receipt input_activation_commitment", cases["input_commitment_drift"]["error"])
        self.assertEqual(cases["output_commitment_drift"]["rejection_layer"], "block_receipt")
        self.assertIn("block receipt output_activation_commitment", cases["output_commitment_drift"]["error"])

    def test_rejects_non_claim_and_mutation_metric_drift(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertTrue(cases["non_claims_drift"]["rejected"])
        self.assertEqual(cases["non_claims_drift"]["rejection_layer"], "parser_or_schema")

        payload = self.fresh_payload()
        payload["case_count"] = 1
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "case count"):
            COMPOSITION.validate_payload(payload)

        payload = self.fresh_payload()
        payload["summary"]["mutations_rejected"] = 0
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "mutations rejected"):
            COMPOSITION.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][0]["rejection_layer"] = "accepted"
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "rejection layer"):
            COMPOSITION.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][0]["mutated_accepted"] = True
        payload["cases"][0]["rejected"] = False
        payload["cases"][0]["rejection_layer"] = "accepted"
        payload["cases"][0]["error"] = ""
        payload["summary"]["mutations_rejected"] = payload["case_count"] - 1
        payload["all_mutations_rejected"] = False
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "all mutation cases rejected"):
            COMPOSITION.validate_payload(payload)

    def test_rejects_extra_claim_bearing_fields(self) -> None:
        for target, field in (
            ("payload", "proof_size_bytes"),
            ("block_receipt", "aggregated_proof_object"),
            ("summary", "verifier_time_ms"),
            ("mutation_case", "unchecked_metric"),
        ):
            with self.subTest(target=target):
                payload = self.fresh_payload()
                if target == "payload":
                    payload[field] = 1
                elif target == "block_receipt":
                    payload["block_receipt"][field] = "present"
                elif target == "summary":
                    payload["summary"][field] = 1.0
                else:
                    payload["cases"][0][field] = "present"
                with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "key set"):
                    COMPOSITION.validate_payload(payload)

    def test_rejects_down_projection_residual_delta_source_drift(self) -> None:
        source = COMPOSITION.source_payloads()
        source["down_projection"]["residual_delta_commitment"] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "down-to-residual"):
            COMPOSITION.build_payload(source)

    def test_tsv_columns_are_stable(self) -> None:
        header = COMPOSITION.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), COMPOSITION.TSV_COLUMNS)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "block-receipt.json"
            tsv_path = tmp / "block-receipt.tsv"
            COMPOSITION.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("missing_bridge_slice", tsv_path.read_text(encoding="utf-8"))

    def test_write_outputs_rejects_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            out = pathlib.Path(raw_tmp) / "outside.json"
            with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "escapes repository"):
                COMPOSITION.write_outputs(payload, out, None)

    def test_write_outputs_rejects_tsv_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_repo_tmp, tempfile.TemporaryDirectory() as raw_tmp:
            safe_json = pathlib.Path(raw_repo_tmp) / "safe.json"
            out = pathlib.Path(raw_tmp) / "outside.tsv"
            with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "escapes repository"):
                COMPOSITION.write_outputs(payload, safe_json, out)

    def test_write_outputs_rejects_symlink_outputs_inside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            real = tmp / "real.json"
            real.write_text("{}", encoding="utf-8")
            symlink = tmp / "link.json"
            symlink.symlink_to(real)
            with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "symlink"):
                COMPOSITION.write_outputs(payload, symlink, None)

    def test_write_outputs_rejects_symlink_tsv_outputs_inside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            safe_json = tmp / "safe.json"
            real = tmp / "real.tsv"
            real.write_text("x\n", encoding="utf-8")
            symlink = tmp / "link.tsv"
            symlink.symlink_to(real)
            with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "symlink"):
                COMPOSITION.write_outputs(payload, safe_json, symlink)

    def test_load_json_rejects_oversized_repo_local_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            path = pathlib.Path(raw_tmp) / "oversized.json"
            path.write_text(" " * (COMPOSITION.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "exceeds max size"):
                COMPOSITION.load_json(path)

    def test_load_json_rejects_invalid_utf8_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            path = pathlib.Path(raw_tmp) / "invalid.json"
            path.write_bytes(b"\xff")
            with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "failed to load"):
                COMPOSITION.load_json(path)

    def test_rejects_symlinked_source_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            real = tmp / "real.json"
            real.write_text("{}", encoding="utf-8")
            symlink = tmp / "source-link.json"
            symlink.symlink_to(real)
            with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "symlink"):
                COMPOSITION.load_json(symlink)
            with self.assertRaisesRegex(COMPOSITION.D128BlockReceiptError, "symlink"):
                COMPOSITION.file_sha256(symlink)


if __name__ == "__main__":
    unittest.main()
