from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_rmsnorm_public_row_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_rmsnorm_public_row_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load attention-derived RMSNorm gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionDerivedD128RmsnormPublicRowGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()
        cls.context = GATE.build_context()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_builds_attention_derived_rmsnorm_payload(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload, context=self.context)

        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], 11)

        summary = payload["summary"]
        self.assertEqual(
            summary["source_attention_outputs_commitment"],
            "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
        )
        self.assertEqual(
            summary["input_activation_commitment"],
            "blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35",
        )
        self.assertEqual(
            summary["rmsnorm_statement_commitment"],
            "blake2b-256:5abd10e4a7bb9ed3eea14b6ea2beb22caac45c8cb6f6b10928585001d57ad57d",
        )
        self.assertEqual(summary["row_count"], 128)
        self.assertEqual(summary["rms_q8"], 2)
        self.assertEqual(summary["sum_squares"], 638)
        self.assertEqual(summary["average_square_floor"], 4)
        self.assertFalse(summary["matches_current_d128_block_input"])
        self.assertEqual(summary["current_d128_mismatch_count"], 127)

    def test_nested_rmsnorm_payload_consumes_derived_input_values(self) -> None:
        payload = self.fresh_payload()
        derived_input, _raw = GATE.load_json(GATE.DERIVED_INPUT_JSON)
        derived_values = derived_input["derived_input"]["values_q8"]
        rmsnorm = payload["rmsnorm_public_row_payload"]

        GATE.RMSNORM.validate_payload(rmsnorm)
        self.assertEqual([row["input_q8"] for row in rmsnorm["rows"]], derived_values)
        self.assertEqual(rmsnorm["input_activation_commitment"], derived_input["derived_input"]["input_activation_commitment"])
        self.assertNotEqual(
            rmsnorm["input_activation_commitment"],
            payload["source_summary"]["current_d128_input_activation_commitment"],
        )

    def test_rejects_rmsnorm_input_row_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rmsnorm_public_row_payload"]["rows"][0]["input_q8"] = 42
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128RmsnormPublicRowError, "derived RMSNorm payload drift"):
            GATE.validate_payload(payload, context=self.context)

    def test_rejects_current_block_consumption_overclaim(self) -> None:
        payload = self.fresh_payload()
        payload["summary"]["matches_current_d128_block_input"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128RmsnormPublicRowError, "derived RMSNorm payload drift"):
            GATE.validate_payload(payload, context=self.context)

    def test_rejects_payload_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "00" * 32
        with self.assertRaisesRegex(GATE.AttentionDerivedD128RmsnormPublicRowError, "payload commitment"):
            GATE.validate_payload(payload, context=self.context)

    def test_tsv_contains_summary_row(self) -> None:
        tsv = GATE.to_tsv(self.fresh_payload(), context=self.context)
        self.assertIn("GO_ATTENTION_DERIVED_D128_RMSNORM_PUBLIC_ROW_INPUT", tsv)
        self.assertIn("8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35", tsv)
        self.assertIn("\tfalse\t127\t11", tsv)

    def test_write_outputs_round_trips_and_rejects_outside_path(self) -> None:
        payload = self.fresh_payload()
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-derived-rmsnorm-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        try:
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("rmsnorm_statement_commitment", tsv_path.read_text(encoding="utf-8"))
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(GATE.AttentionDerivedD128RmsnormPublicRowError, "output path"):
                GATE.write_outputs(payload, pathlib.Path(tmp) / "outside.json", None)


if __name__ == "__main__":
    unittest.main()
