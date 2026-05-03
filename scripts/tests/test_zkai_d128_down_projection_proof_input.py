from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_down_projection_proof_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_down_projection_proof_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 down projection input generator from {SCRIPT_PATH}")
DOWN_PROJECTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOWN_PROJECTION)


class ZkAiD128DownProjectionProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = DOWN_PROJECTION.build_payload()
        target_dir = ROOT / "target" / "local-hardening"
        target_dir.mkdir(parents=True, exist_ok=True)
        cls.target_dir = target_dir

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_builds_and_validates(self) -> None:
        payload = self.fresh_payload()
        DOWN_PROJECTION.validate_payload(payload)
        self.assertEqual(payload["row_count"], DOWN_PROJECTION.WIDTH * DOWN_PROJECTION.FF_DIM)
        self.assertEqual(payload["down_projection_mul_rows"], DOWN_PROJECTION.WIDTH * DOWN_PROJECTION.FF_DIM)
        self.assertEqual(payload["residual_delta_rows"], DOWN_PROJECTION.WIDTH)
        self.assertEqual(payload["residual_delta_scale_divisor"], DOWN_PROJECTION.FF_DIM)
        self.assertEqual(len(payload["hidden_q8"]), DOWN_PROJECTION.FF_DIM)
        self.assertEqual(len(payload["residual_delta_q8"]), DOWN_PROJECTION.WIDTH)
        self.assertEqual(len(payload["residual_delta_remainder_q8"]), DOWN_PROJECTION.WIDTH)
        self.assertEqual(payload["down_matrix_root"], DOWN_PROJECTION.DOWN_MATRIX_ROOT)
        self.assertEqual(payload["source_hidden_activation_commitment"], DOWN_PROJECTION.HIDDEN_ACTIVATION_COMMITMENT)
        self.assertEqual(payload["source_activation_swiglu_statement_commitment"], DOWN_PROJECTION.SOURCE_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT)
        self.assertEqual(payload["source_activation_swiglu_public_instance_commitment"], DOWN_PROJECTION.SOURCE_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT)
        self.assertNotEqual(payload["residual_delta_commitment"], DOWN_PROJECTION.OUTPUT_ACTIVATION_COMMITMENT)
        rows, quotients, remainders = DOWN_PROJECTION.build_rows(payload["hidden_q8"])
        self.assertEqual(quotients, payload["residual_delta_q8"])
        self.assertEqual(remainders, payload["residual_delta_remainder_q8"])
        first_acc = sum(row["product_q8"] for row in rows[: DOWN_PROJECTION.FF_DIM])
        self.assertEqual(
            payload["residual_delta_q8"][0] * DOWN_PROJECTION.FF_DIM + payload["residual_delta_remainder_q8"][0],
            first_acc,
        )

    def test_payload_rejects_residual_delta_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_commitment"] = DOWN_PROJECTION.OUTPUT_ACTIVATION_COMMITMENT
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "relabeled as full output"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_source_hidden_commitment_drift(self) -> None:
        source = copy.deepcopy(DOWN_PROJECTION.load_source())
        source["hidden_activation_commitment"] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "hidden_activation_commitment"):
            DOWN_PROJECTION.build_payload(source)

    def test_payload_rejects_source_statement_commitment_drift(self) -> None:
        source = copy.deepcopy(DOWN_PROJECTION.load_source())
        source["statement_commitment"] = "blake2b-256:" + "67" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "statement_commitment"):
            DOWN_PROJECTION.build_payload(source)

    def test_payload_rejects_source_public_instance_commitment_drift(self) -> None:
        source = copy.deepcopy(DOWN_PROJECTION.load_source())
        source["public_instance_commitment"] = "blake2b-256:" + "68" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "public_instance_commitment"):
            DOWN_PROJECTION.build_payload(source)

    def test_statement_commitment_binds_source_public_instance_commitment(self) -> None:
        payload = self.fresh_payload()
        tampered = self.fresh_payload()
        tampered["source_activation_swiglu_public_instance_commitment"] = "blake2b-256:" + "68" * 32
        self.assertNotEqual(
            DOWN_PROJECTION.statement_commitment(payload),
            DOWN_PROJECTION.statement_commitment(tampered),
        )

    def test_payload_rejects_hidden_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["hidden_q8"][0] += 1
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "source hidden activation commitment"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_hidden_vector_length_drift(self) -> None:
        payload = self.fresh_payload()
        payload["hidden_q8"] = payload["hidden_q8"][:-1]
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "hidden activation vector"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] += 1
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "residual delta output drift"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_remainder_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_remainder_q8"][0] = (payload["residual_delta_remainder_q8"][0] + 1) % DOWN_PROJECTION.FF_DIM
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "residual delta remainder drift"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_remainder_bound_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_remainder_q8"][0] = DOWN_PROJECTION.FF_DIM
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "outside divisor range"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_scale_divisor_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_scale_divisor"] = DOWN_PROJECTION.FF_DIM + 1
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "residual_delta_scale_divisor"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_hidden_m31_bounds_drift(self) -> None:
        payload = self.fresh_payload()
        payload["hidden_q8"][0] = DOWN_PROJECTION.M31_MODULUS
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "signed M31"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_m31_bounds_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_q8"][0] = DOWN_PROJECTION.M31_MODULUS
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "signed M31"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_down_matrix_root_drift(self) -> None:
        payload = self.fresh_payload()
        payload["down_matrix_root"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "down_matrix_root|down matrix root"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_statement_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["statement_commitment"] = "blake2b-256:" + "44" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "statement_commitment"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_public_instance_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["public_instance_commitment"] = "blake2b-256:" + "45" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "public_instance_commitment"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_validation_commands_drift(self) -> None:
        payload = self.fresh_payload()
        payload["validation_commands"] = ["cargo test"]
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "validation_commands"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_residual_delta_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_delta_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "residual_delta_commitment"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_payload_rejects_row_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["down_projection_mul_row_commitment"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "down_projection_mul_row_commitment"):
            DOWN_PROJECTION.validate_payload(payload)

    def test_load_source_rejects_oversized_source_json(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.target_dir) as tmp:
            source_path = pathlib.Path(tmp) / "oversized-source.json"
            source_path.write_text(" " * (DOWN_PROJECTION.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "exceeds max size"):
                DOWN_PROJECTION.load_source(source_path)

    def test_load_source_rejects_non_file_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.target_dir) as tmp:
            with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "regular file"):
                DOWN_PROJECTION.load_source(pathlib.Path(tmp))

    def test_load_source_rejects_symlink_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.target_dir) as tmp:
            source_path = pathlib.Path(tmp) / "source.json"
            link_path = pathlib.Path(tmp) / "link.json"
            source_path.write_text(json.dumps(DOWN_PROJECTION.load_source()), encoding="utf-8")
            link_path.symlink_to(source_path)
            with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "symlink"):
                DOWN_PROJECTION.load_source(link_path)

    def test_load_source_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "source.json"
            source_path.write_text(json.dumps(DOWN_PROJECTION.load_source()), encoding="utf-8")
            with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "escapes repository"):
                DOWN_PROJECTION.load_source(source_path)

    def test_load_source_rejects_swap_between_lstat_and_open(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.target_dir) as tmp:
            source_path = pathlib.Path(tmp) / "source.json"
            replacement_path = pathlib.Path(tmp) / "replacement.json"
            source_path.write_text(json.dumps(DOWN_PROJECTION.load_source()), encoding="utf-8")
            replacement_path.write_text(json.dumps(DOWN_PROJECTION.load_source()), encoding="utf-8")
            original_open = DOWN_PROJECTION.os.open

            def swapping_open(path, flags):  # type: ignore[no-untyped-def]
                if pathlib.Path(path) == source_path.resolve():
                    source_path.unlink()
                    replacement_path.rename(source_path)
                return original_open(path, flags)

            with mock.patch.object(DOWN_PROJECTION.os, "open", side_effect=swapping_open):
                with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "changed while reading"):
                    DOWN_PROJECTION.load_source(source_path)

    def test_load_source_rejects_invalid_utf8_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.target_dir) as tmp:
            source_path = pathlib.Path(tmp) / "invalid-utf8.json"
            source_path.write_bytes(b"\xff")
            with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "failed to load"):
                DOWN_PROJECTION.load_source(source_path)

    def test_load_module_rejects_symlink_helper_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.target_dir) as tmp:
            helper_path = pathlib.Path(tmp) / "helper.py"
            link_path = pathlib.Path(tmp) / "helper-link.py"
            helper_path.write_text("VALUE = 1\n", encoding="utf-8")
            link_path.symlink_to(helper_path)
            with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "symlink"):
                DOWN_PROJECTION._load_module(link_path, "tampered_helper")

    def test_load_module_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            helper_path = pathlib.Path(tmp) / "helper.py"
            helper_path.write_text("VALUE = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(DOWN_PROJECTION.D128DownProjectionInputError, "escapes repository"):
                DOWN_PROJECTION._load_module(helper_path, "escaped_helper")

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=self.target_dir) as tmp:
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
            self.assertEqual(rows[0]["non_claims"], json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    unittest.main()
