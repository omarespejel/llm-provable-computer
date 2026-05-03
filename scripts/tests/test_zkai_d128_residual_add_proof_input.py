from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_residual_add_proof_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_residual_add_proof_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 residual-add input generator from {SCRIPT_PATH}")
D128_RESIDUAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D128_RESIDUAL)


class ZkAiD128ResidualAddProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = D128_RESIDUAL.build_payload()
        target_dir = ROOT / "target" / "local-hardening"
        target_dir.mkdir(parents=True, exist_ok=True)
        cls.target_dir = target_dir

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_builds_and_validates_real_down_projection_source(self) -> None:
        payload = self.fresh_payload()
        D128_RESIDUAL.validate_payload(payload)
        self.assertEqual(payload["width"], 128)
        self.assertEqual(payload["row_count"], 128)
        self.assertEqual(payload["residual_delta_commitment"], D128_RESIDUAL.RESIDUAL_DELTA_COMMITMENT)
        self.assertEqual(payload["input_activation_commitment"], D128_RESIDUAL.INPUT_ACTIVATION_COMMITMENT)
        self.assertNotEqual(payload["residual_delta_commitment"], payload["output_activation_commitment"])
        self.assertNotEqual(payload["input_activation_commitment"], payload["output_activation_commitment"])
        self.assertEqual(payload["rows"][0]["input_q8"] + payload["rows"][0]["residual_delta_q8"], payload["rows"][0]["output_q8"])
        self.assertLess(min(payload["residual_delta_q8"]), -D128_RESIDUAL.Q8_SEMANTIC_ABS_BOUND)
        self.assertGreater(max(payload["residual_delta_q8"]), D128_RESIDUAL.Q8_SEMANTIC_ABS_BOUND)
        self.assertIn("signed_m31", payload["range_policy"])

    def test_payload_rejects_rmsnorm_source_commitment_drift(self) -> None:
        source = copy.deepcopy(D128_RESIDUAL.load_rmsnorm_source())
        source["input_activation_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "input_activation_commitment"):
            D128_RESIDUAL.build_payload(source, D128_RESIDUAL.load_down_source())

    def test_payload_rejects_rmsnorm_source_statement_rebind(self) -> None:
        payload = self.fresh_payload()
        payload["source_rmsnorm_statement_commitment"] = "blake2b-256:" + "12" * 32
        payload["statement_commitment"] = D128_RESIDUAL.statement_commitment(payload)
        payload["public_instance_commitment"] = D128_RESIDUAL.public_instance_commitment(
            payload["statement_commitment"]
        )
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "source_rmsnorm_statement"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_down_source_residual_commitment_drift(self) -> None:
        source = copy.deepcopy(D128_RESIDUAL.load_down_source())
        source["residual_delta_commitment"] = "blake2b-256:" + "22" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "residual_delta_commitment"):
            D128_RESIDUAL.build_payload(D128_RESIDUAL.load_rmsnorm_source(), source)

    def test_payload_rejects_residual_delta_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_commitment"] = payload["output_activation_commitment"]
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "relabeled as full output"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_input_relabeling_as_output(self) -> None:
        payload = self.fresh_payload()
        payload["input_activation_commitment"] = payload["output_activation_commitment"]
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "input activation commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_input_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["input_q8"][0] += 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "input activation commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_residual_delta_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] += 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "residual delta commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_output_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["output_q8"][0] += 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "output activation commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_row_relation_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rows"][0]["output_q8"] += 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "row relation"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_row_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_row_commitment"] = "blake2b-256:" + "33" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "row commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_statement_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["statement_commitment"] = "blake2b-256:" + "44" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "statement commitment"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_public_instance_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["public_instance_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "public instance"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_proof_native_parameter_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["proof_native_parameter_commitment"] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "proof-native parameter"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_input_q8_bound_drift(self) -> None:
        payload = self.fresh_payload()
        payload["input_q8"][0] = D128_RESIDUAL.Q8_SEMANTIC_ABS_BOUND + 1
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "q8 semantic"):
            D128_RESIDUAL.validate_payload(payload)

    def test_payload_rejects_residual_delta_m31_bound_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] = D128_RESIDUAL.M31_MODULUS
        with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "signed M31"):
            D128_RESIDUAL.validate_payload(payload)

    def test_load_source_rejects_oversized_json(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.target_dir) as tmp:
            source_path = pathlib.Path(tmp) / "oversized.json"
            source_path.write_text(" " * (D128_RESIDUAL.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "exceeds max size"):
                D128_RESIDUAL.load_down_source(source_path)

    def test_load_source_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "source.json"
            source_path.write_text(json.dumps(D128_RESIDUAL.load_down_source()), encoding="utf-8")
            with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "escapes repository"):
                D128_RESIDUAL.load_down_source(source_path)

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

    def test_write_outputs_rejects_symlink_outputs_inside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            target = pathlib.Path(tmp) / "target.json"
            target.write_text("existing\n", encoding="utf-8")
            symlink = pathlib.Path(tmp) / "linked.json"
            symlink.symlink_to(target)
            with self.assertRaisesRegex(D128_RESIDUAL.D128ResidualAddInputError, "symlink"):
                D128_RESIDUAL.write_outputs(payload, symlink, None)
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")


if __name__ == "__main__":
    unittest.main()
