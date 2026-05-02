from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_vector_residual_add_proof_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_vector_residual_add_proof_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 residual-add input generator from {SCRIPT_PATH}")
D128_RESIDUAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D128_RESIDUAL)


class ZkAiD128VectorResidualAddProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = D128_RESIDUAL.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_builds_and_validates(self) -> None:
        payload = self.fresh_payload()
        D128_RESIDUAL.validate_payload(payload)
        self.assertEqual(payload["target_id"], D128_RESIDUAL.TARGET_ID)
        self.assertEqual(payload["operation"], D128_RESIDUAL.OPERATION)
        self.assertEqual(payload["width"], 128)
        self.assertEqual(payload["row_count"], 128)
        self.assertEqual(len(payload["rows"]), 128)
        self.assertEqual(payload["rows"][0]["input_q8"] + payload["rows"][0]["residual_delta_q8"], payload["rows"][0]["output_q8"])
        self.assertNotEqual(payload["residual_delta_commitment"], payload["output_activation_commitment"])
        self.assertNotEqual(payload["input_activation_commitment"], payload["output_activation_commitment"])

    def test_payload_rejects_target_summary_drift(self) -> None:
        target = D128_RESIDUAL.load_target()
        target["summary"]["target_width"] = 64
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "target summary mismatch"):
            D128_RESIDUAL.build_payload(target)

    def test_payload_rejects_residual_delta_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_commitment"] = payload["output_activation_commitment"]
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "relabeled as full output"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_input_relabeling_as_output(self) -> None:
        payload = self.fresh_payload()
        payload["input_activation_commitment"] = payload["output_activation_commitment"]
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "input activation commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_input_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["input_q8"][0] += 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "input activation commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_residual_delta_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] += 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "residual delta commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_output_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["output_q8"][0] += 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "output activation commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_row_relation_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rows"][0]["output_q8"] += 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "row relation"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_row_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_row_commitment"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "row commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_statement_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["statement_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "statement commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_public_instance_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["public_instance_commitment"] = "blake2b-256:" + "22" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "public instance"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_proof_native_parameter_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["proof_native_parameter_commitment"] = "blake2b-256:" + "33" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "proof-native parameter"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_q8_bound_drift(self) -> None:
        payload = self.fresh_payload()
        payload["output_q8"][0] = D128_RESIDUAL.Q8_SEMANTIC_ABS_BOUND + 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "q8 semantic"):
            D128_RESIDUAL.validate_payload(payload)

    def test_load_target_rejects_oversized_source_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "oversized-target.json"
            source_path.write_text(" " * (D128_RESIDUAL.MAX_TARGET_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "exceeds max size"):
                D128_RESIDUAL.load_target(source_path)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            json_path = pathlib.Path(tmp) / "d128-residual.json"
            tsv_path = pathlib.Path(tmp) / "d128-residual.tsv"
            D128_RESIDUAL.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            rows = D128_RESIDUAL.rows_for_tsv(loaded)
            self.assertEqual(len(rows), 1)
            self.assertIn(payload["output_activation_commitment"], tsv_path.read_text(encoding="utf-8"))

    def test_write_outputs_rejects_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "d128-residual.json"
            with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "escapes repository"):
                D128_RESIDUAL.write_outputs(payload, json_path, None)
            self.assertFalse(json_path.exists())

    def test_write_outputs_rejects_symlink_outputs_inside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            target = pathlib.Path(tmp) / "target.json"
            target.write_text("existing\n", encoding="utf-8")
            symlink = pathlib.Path(tmp) / "linked.json"
            symlink.symlink_to(target)
            with self.assertRaisesRegex(D128_RESIDUAL.D128VectorResidualAddInputError, "symlink"):
                D128_RESIDUAL.write_outputs(payload, symlink, None)
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")

    def test_atomic_write_cleans_temp_file_when_replace_fails(self) -> None:
        original_replace = D128_RESIDUAL.os.replace
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            out = pathlib.Path(tmp) / "out.json"

            def fail_replace(_src: pathlib.Path, _dst: pathlib.Path) -> None:
                raise OSError("simulated replace failure")

            try:
                D128_RESIDUAL.os.replace = fail_replace
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    D128_RESIDUAL._atomic_write_text(out, "payload\n")
                leftovers = [path for path in pathlib.Path(tmp).iterdir() if path.name != "out.json"]
                self.assertEqual(leftovers, [])
                self.assertFalse(out.exists())
            finally:
                D128_RESIDUAL.os.replace = original_replace


if __name__ == "__main__":
    unittest.main()
