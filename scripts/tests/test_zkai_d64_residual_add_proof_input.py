from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_residual_add_proof_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_residual_add_proof_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load residual-add input generator from {SCRIPT_PATH}")
RESIDUAL_ADD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESIDUAL_ADD)


class ZkAiD64ResidualAddProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = RESIDUAL_ADD.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_builds_and_validates(self) -> None:
        payload = self.fresh_payload()
        RESIDUAL_ADD.validate_payload(payload)
        self.assertEqual(payload["row_count"], RESIDUAL_ADD.WIDTH)
        self.assertEqual(len(payload["input_q8"]), RESIDUAL_ADD.WIDTH)
        self.assertEqual(len(payload["residual_delta_q8"]), RESIDUAL_ADD.WIDTH)
        self.assertEqual(len(payload["output_q8"]), RESIDUAL_ADD.WIDTH)
        self.assertEqual(payload["input_activation_commitment"], RESIDUAL_ADD.INPUT_ACTIVATION_COMMITMENT)
        self.assertEqual(payload["residual_delta_commitment"], RESIDUAL_ADD.RESIDUAL_DELTA_COMMITMENT)
        self.assertEqual(payload["output_activation_commitment"], RESIDUAL_ADD.OUTPUT_ACTIVATION_COMMITMENT)
        self.assertNotEqual(payload["residual_delta_commitment"], payload["output_activation_commitment"])
        self.assertNotEqual(payload["input_activation_commitment"], payload["output_activation_commitment"])
        self.assertEqual(payload["rows"][0]["input_q8"] + payload["rows"][0]["residual_delta_q8"], payload["rows"][0]["output_q8"])

    def test_payload_rejects_residual_delta_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_commitment"] = payload["output_activation_commitment"]
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "relabeled as full output"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_input_relabeling_as_output(self) -> None:
        payload = self.fresh_payload()
        payload["input_activation_commitment"] = payload["output_activation_commitment"]
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "input activation commitment"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_source_residual_delta_commitment_drift(self) -> None:
        source = copy.deepcopy(RESIDUAL_ADD.load_source())
        source["residual_delta_commitment"] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "residual_delta_commitment"):
            RESIDUAL_ADD.build_payload(source)

    def test_payload_rejects_input_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["input_q8"][0] += 1
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "input activation commitment"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_residual_delta_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] += 1
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "residual delta commitment"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_output_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["output_q8"][0] += 1
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "output activation commitment"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_row_relation_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rows"][0]["output_q8"] += 1
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "row relation"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_input_q8_bounds_drift(self) -> None:
        payload = self.fresh_payload()
        payload["input_q8"][0] = RESIDUAL_ADD.Q8_SEMANTIC_ABS_BOUND + 1
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "q8 semantic"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_residual_delta_q8_bounds_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] = RESIDUAL_ADD.Q8_SEMANTIC_ABS_BOUND + 1
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "q8 semantic"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_output_q8_bounds_drift(self) -> None:
        payload = self.fresh_payload()
        payload["output_q8"][0] = RESIDUAL_ADD.Q8_SEMANTIC_ABS_BOUND + 1
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "q8 semantic"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_payload_rejects_row_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_row_commitment"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "row commitment"):
            RESIDUAL_ADD.validate_payload(payload)

    def test_load_source_rejects_oversized_source_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "oversized-source.json"
            source_path.write_text(" " * (RESIDUAL_ADD.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "exceeds max size"):
                RESIDUAL_ADD.load_source(source_path)

    def test_load_source_rejects_non_file_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "regular file"):
                RESIDUAL_ADD.load_source(pathlib.Path(tmp))

    def test_load_source_rejects_invalid_utf8_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "invalid-utf8.json"
            source_path.write_bytes(b"\xff")
            with self.assertRaisesRegex(RESIDUAL_ADD.ResidualAddInputError, "failed to load"):
                RESIDUAL_ADD.load_source(source_path)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "residual-add.json"
            tsv_path = pathlib.Path(tmp) / "residual-add.tsv"
            RESIDUAL_ADD.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            rows = RESIDUAL_ADD.rows_for_tsv(loaded)
            self.assertEqual(len(rows), 1)
            tsv_text = tsv_path.read_text(encoding="utf-8")
            self.assertIn("output_activation_commitment", tsv_text)
            self.assertIn(payload["output_activation_commitment"], tsv_text)
            self.assertEqual(
                rows[0]["non_claims"],
                json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
            )


if __name__ == "__main__":
    unittest.main()
