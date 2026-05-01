from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_to_projection_bridge_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_rmsnorm_to_projection_bridge_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load bridge input generator from {SCRIPT_PATH}")
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


class ZkAiD64RmsnormToProjectionBridgeInputTests(unittest.TestCase):
    def test_payload_builds_and_validates(self) -> None:
        payload = BRIDGE.build_payload()
        BRIDGE.validate_payload(payload)
        self.assertEqual(payload["row_count"], BRIDGE.WIDTH)
        self.assertEqual(payload["source_rmsnorm_output_row_commitment"], BRIDGE.RMSNORM_OUTPUT_ROW_COMMITMENT)
        self.assertEqual(payload["projection_input_row_commitment"], BRIDGE.PROJECTION_INPUT_ROW_COMMITMENT)
        self.assertNotEqual(payload["projection_input_row_commitment"], BRIDGE.OUTPUT_ACTIVATION_COMMITMENT)

    def test_payload_rejects_projection_full_output_relabeling(self) -> None:
        payload = BRIDGE.build_payload()
        payload["projection_input_row_commitment"] = BRIDGE.OUTPUT_ACTIVATION_COMMITMENT
        with self.assertRaisesRegex(BRIDGE.BridgeInputError, "relabeled as full output"):
            BRIDGE.validate_payload(payload)

    def test_payload_rejects_bridge_row_equality_drift(self) -> None:
        payload = BRIDGE.build_payload()
        row0 = payload["rows"][0]
        base = row0["rmsnorm_normed_q8"]
        row0["projection_input_q8"] = base + 1 if base < 127 else base - 1
        with self.assertRaisesRegex(BRIDGE.BridgeInputError, "bridge row equality drift"):
            BRIDGE.validate_payload(payload)

    def test_payload_rejects_source_commitment_drift(self) -> None:
        payload = BRIDGE.build_payload()
        payload["source_rmsnorm_output_row_commitment"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(BRIDGE.BridgeInputError, "source_rmsnorm_output_row_commitment"):
            BRIDGE.validate_payload(payload)

    def test_payload_rejects_projection_commitment_drift(self) -> None:
        payload = BRIDGE.build_payload()
        payload["projection_input_row_commitment"] = "blake2b-256:" + "99" * 32
        with self.assertRaisesRegex(BRIDGE.BridgeInputError, "projection_input_row_commitment"):
            BRIDGE.validate_payload(payload)

    def test_load_source_rejects_oversized_source_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "oversized-source.json"
            source_path.write_text(" " * (BRIDGE.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(BRIDGE.BridgeInputError, "exceeds max size"):
                BRIDGE.load_source(source_path)

    def test_source_validation_rejects_normed_commitment_drift(self) -> None:
        source = copy.deepcopy(BRIDGE.load_source())
        source["rmsnorm_output_row_commitment"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(BRIDGE.BridgeInputError, "source RMSNorm output row commitment"):
            BRIDGE.validate_source(source)

    def test_write_outputs_round_trips(self) -> None:
        payload = BRIDGE.build_payload()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "bridge.json"
            tsv_path = pathlib.Path(tmp) / "bridge.tsv"
            BRIDGE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            rows = BRIDGE.rows_for_tsv(loaded)
            self.assertEqual(len(rows), 1)
            self.assertIn("projection_input_row_commitment", tsv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
