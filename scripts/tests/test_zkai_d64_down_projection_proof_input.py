from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_down_projection_proof_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_down_projection_proof_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load down projection input generator from {SCRIPT_PATH}")
DOWN_PROJECTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOWN_PROJECTION)


class ZkAiD64DownProjectionProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = DOWN_PROJECTION.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_builds_and_validates(self) -> None:
        payload = self.fresh_payload()
        DOWN_PROJECTION.validate_payload(payload)
        self.assertEqual(payload["row_count"], DOWN_PROJECTION.WIDTH * DOWN_PROJECTION.FF_DIM)
        self.assertEqual(payload["down_projection_mul_rows"], DOWN_PROJECTION.WIDTH * DOWN_PROJECTION.FF_DIM)
        self.assertEqual(payload["residual_delta_rows"], DOWN_PROJECTION.WIDTH)
        self.assertEqual(len(payload["hidden_q8"]), DOWN_PROJECTION.FF_DIM)
        self.assertEqual(len(payload["residual_delta_q8"]), DOWN_PROJECTION.WIDTH)
        self.assertEqual(payload["down_matrix_root"], DOWN_PROJECTION.DOWN_MATRIX_ROOT)
        self.assertEqual(payload["source_hidden_activation_commitment"], DOWN_PROJECTION.HIDDEN_ACTIVATION_COMMITMENT)
        self.assertNotEqual(payload["residual_delta_commitment"], DOWN_PROJECTION.OUTPUT_ACTIVATION_COMMITMENT)

    def test_payload_rejects_residual_delta_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_commitment"] = DOWN_PROJECTION.OUTPUT_ACTIVATION_COMMITMENT
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "relabeled as full output"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_source_hidden_commitment_drift(self) -> None:
        source = copy.deepcopy(DOWN_PROJECTION.load_source())
        source["hidden_activation_commitment"] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "hidden_activation_commitment"):
            DOWN_PROJECTION.build_payload(source)

    def test_payload_rejects_hidden_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["hidden_q8"][0] += 1
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "source hidden activation commitment"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_hidden_vector_length_drift(self) -> None:
        payload = self.fresh_payload()
        payload["hidden_q8"] = payload["hidden_q8"][:-1]
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "hidden activation vector"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] += 1
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "residual delta output drift"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_hidden_q8_bounds_drift(self) -> None:
        payload = self.fresh_payload()
        payload["hidden_q8"][0] = DOWN_PROJECTION.Q8_SEMANTIC_ABS_BOUND + 1
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "q8 semantic"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_q8_bounds_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] = DOWN_PROJECTION.Q8_SEMANTIC_ABS_BOUND + 1
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "q8 semantic"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_down_matrix_root_drift(self) -> None:
        payload = self.fresh_payload()
        payload["down_matrix_root"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "down_matrix_root"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "residual delta commitment"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_row_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["down_projection_mul_row_commitment"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "down projection row"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_load_source_rejects_oversized_source_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "oversized-source.json"
            source_path.write_text(" " * (DOWN_PROJECTION.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "exceeds max size"):
                DOWN_PROJECTION.load_source(source_path)

    def test_load_source_rejects_non_file_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "regular file"):
                DOWN_PROJECTION.load_source(pathlib.Path(tmp))

    def test_load_source_rejects_invalid_utf8_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "invalid-utf8.json"
            source_path.write_bytes(b"\xff")
            with self.assertRaisesRegex(DOWN_PROJECTION.DownProjectionInputError, "failed to load"):
                DOWN_PROJECTION.load_source(source_path)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "down-projection.json"
            tsv_path = pathlib.Path(tmp) / "down-projection.tsv"
            DOWN_PROJECTION.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            rows = DOWN_PROJECTION.rows_for_tsv(loaded)
            self.assertEqual(len(rows), 1)
            tsv_text = tsv_path.read_text(encoding="utf-8")
            self.assertIn("residual_delta_commitment", tsv_text)
            self.assertIn(payload["residual_delta_commitment"], tsv_text)
            self.assertEqual(
                rows[0]["non_claims"],
                json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
            )


if __name__ == "__main__":
    unittest.main()
