from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_public_row_proof_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_rmsnorm_public_row_proof_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 RMSNorm input generator from {SCRIPT_PATH}")
D128_RMSNORM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D128_RMSNORM)


class ZkAiD128RmsnormPublicRowProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = D128_RMSNORM.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_builds_and_validates(self) -> None:
        payload = self.fresh_payload()
        D128_RMSNORM.validate_payload(payload)
        self.assertEqual(payload["target_id"], D128_RMSNORM.TARGET_ID)
        self.assertEqual(payload["operation"], D128_RMSNORM.OPERATION)
        self.assertEqual(payload["width"], 128)
        self.assertEqual(payload["row_count"], 128)
        self.assertEqual(len(payload["rows"]), 128)
        self.assertEqual(payload["rms_q8"], 55)
        self.assertEqual(payload["average_square_floor"], 3056)
        self.assertNotEqual(payload["rmsnorm_output_row_commitment"], payload["statement_commitment"])
        self.assertNotEqual(payload["statement_commitment"], D128_RMSNORM.TARGET_COMMITMENT)
        self.assertEqual(payload["statement_commitment"], D128_RMSNORM.statement_commitment(payload))

    def test_payload_rejects_target_summary_drift(self) -> None:
        target = D128_RMSNORM.load_target()
        target["summary"]["target_width"] = 64
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "target summary mismatch"):
            D128_RMSNORM.build_payload(target)

    def test_payload_rejects_domain_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rmsnorm_output_row_domain"] = "ptvm:zkai:d128-output-activation:v1"
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "domain mismatch"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_input_row_relation_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rows"][0]["input_square"] += 1
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "input square"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_scaled_floor_relation_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rows"][2]["scale_remainder"] = 0
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "scaled floor"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_normed_relation_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rows"][0]["normed_q8"] += 1
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "normed relation"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_average_square_drift(self) -> None:
        payload = self.fresh_payload()
        payload["average_square_floor"] += 1
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "average square"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_rms_scale_tree_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rms_scale_tree_root"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "RMS scale tree"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_output_row_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rmsnorm_output_row_commitment"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "output row"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_statement_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["statement_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "statement commitment"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_validation_command_drift(self) -> None:
        payload = self.fresh_payload()
        payload["validation_commands"] = payload["validation_commands"][:-1]
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "validation_commands"):
            D128_RMSNORM.validate_payload(payload)

    def test_payload_rejects_uppercase_commitment_hex(self) -> None:
        payload = self.fresh_payload()
        payload["proof_native_parameter_commitment"] = payload["proof_native_parameter_commitment"].upper().replace(
            "BLAKE2B-256:", "blake2b-256:"
        )
        with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "lowercase"):
            D128_RMSNORM.validate_payload(payload)

    def test_load_target_rejects_oversized_source_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "oversized-target.json"
            source_path.write_text(" " * (D128_RMSNORM.MAX_TARGET_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "exceeds max size"):
                D128_RMSNORM.load_target(source_path)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            json_path = pathlib.Path(tmp) / "d128-rmsnorm.json"
            tsv_path = pathlib.Path(tmp) / "d128-rmsnorm.tsv"
            D128_RMSNORM.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            rows = D128_RMSNORM.rows_for_tsv(loaded)
            self.assertEqual(len(rows), 1)
            self.assertIn(payload["rmsnorm_output_row_commitment"], tsv_path.read_text(encoding="utf-8"))

    def test_write_outputs_rejects_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "d128-rmsnorm.json"
            with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "escapes repository"):
                D128_RMSNORM.write_outputs(payload, json_path, None)
            self.assertFalse(json_path.exists())

    def test_write_outputs_rejects_symlink_outputs_inside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            target = pathlib.Path(tmp) / "target.json"
            target.write_text("existing\n", encoding="utf-8")
            symlink = pathlib.Path(tmp) / "linked.json"
            symlink.symlink_to(target)
            with self.assertRaisesRegex(D128_RMSNORM.D128RmsnormPublicRowInputError, "symlink"):
                D128_RMSNORM.write_outputs(payload, symlink, None)
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")


if __name__ == "__main__":
    unittest.main()
