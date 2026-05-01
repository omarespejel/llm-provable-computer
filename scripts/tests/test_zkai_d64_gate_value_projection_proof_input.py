from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_gate_value_projection_proof_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_gate_value_projection_proof_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load gate/value projection input generator from {SCRIPT_PATH}")
GATE_VALUE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE_VALUE)


class ZkAiD64GateValueProjectionProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE_VALUE.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_builds_and_validates(self) -> None:
        payload = self.fresh_payload()
        GATE_VALUE.validate_payload(payload)
        self.assertEqual(payload["row_count"], 2 * GATE_VALUE.FF_DIM * GATE_VALUE.WIDTH)
        self.assertEqual(len(payload["projection_input_q8"]), GATE_VALUE.WIDTH)
        self.assertEqual(payload["source_projection_input_row_commitment"], GATE_VALUE.PROJECTION_INPUT_ROW_COMMITMENT)
        self.assertEqual(payload["gate_matrix_root"], GATE_VALUE.GATE_MATRIX_ROOT)
        self.assertEqual(payload["value_matrix_root"], GATE_VALUE.VALUE_MATRIX_ROOT)
        self.assertNotEqual(payload["gate_value_projection_output_commitment"], GATE_VALUE.OUTPUT_ACTIVATION_COMMITMENT)

    def test_payload_rejects_projection_output_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["gate_value_projection_output_commitment"] = GATE_VALUE.OUTPUT_ACTIVATION_COMMITMENT
        with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "relabeled as full output"):
            GATE_VALUE.validate_payload(payload)

    def test_payload_rejects_source_bridge_projection_commitment_drift(self) -> None:
        bridge = copy.deepcopy(GATE_VALUE.load_bridge())
        bridge["projection_input_row_commitment"] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "projection_input_row_commitment"):
            GATE_VALUE.build_payload(bridge)

    def test_payload_rejects_projection_input_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["projection_input_q8"][0] += 1
        with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "projection input commitment"):
            GATE_VALUE.validate_payload(payload)

    def test_payload_rejects_projection_input_value_drift(self) -> None:
        payload = self.fresh_payload()
        payload["projection_input_q8"] = payload["projection_input_q8"][:-1]
        with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "projection input vector"):
            GATE_VALUE.validate_payload(payload)

    def test_payload_rejects_projection_row_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["gate_value_projection_mul_row_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "gate/value projection row"):
            GATE_VALUE.validate_payload(payload)

    def test_payload_rejects_gate_matrix_root_drift(self) -> None:
        payload = self.fresh_payload()
        payload["gate_matrix_root"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "gate_matrix_root"):
            GATE_VALUE.validate_payload(payload)

    def test_payload_rejects_value_matrix_root_drift(self) -> None:
        payload = self.fresh_payload()
        payload["value_matrix_root"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "value_matrix_root"):
            GATE_VALUE.validate_payload(payload)

    def test_payload_rejects_value_output_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["value_projection_q8"][0] += 1
        with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "value projection output drift"):
            GATE_VALUE.validate_payload(payload)

    def test_load_bridge_rejects_oversized_source_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "oversized-bridge.json"
            source_path.write_text(" " * (GATE_VALUE.MAX_BRIDGE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "exceeds max size"):
                GATE_VALUE.load_bridge(source_path)

    def test_load_bridge_rejects_non_file_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "regular file"):
                GATE_VALUE.load_bridge(pathlib.Path(tmp))

    def test_load_bridge_rejects_invalid_utf8_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "invalid-utf8.json"
            source_path.write_bytes(b"\xff")
            with self.assertRaisesRegex(GATE_VALUE.GateValueProjectionInputError, "failed to load"):
                GATE_VALUE.load_bridge(source_path)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "gate-value.json"
            tsv_path = pathlib.Path(tmp) / "gate-value.tsv"
            GATE_VALUE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            rows = GATE_VALUE.rows_for_tsv(loaded)
            self.assertEqual(len(rows), 1)
            tsv_text = tsv_path.read_text(encoding="utf-8")
            self.assertIn("gate_value_projection_output_commitment", tsv_text)
            self.assertIn(payload["gate_value_projection_output_commitment"], tsv_text)


if __name__ == "__main__":
    unittest.main()
