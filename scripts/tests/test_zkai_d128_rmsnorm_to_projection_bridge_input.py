from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_to_projection_bridge_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_rmsnorm_to_projection_bridge_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 bridge input generator from {SCRIPT_PATH}")
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
DERIVED_RMSNORM_SOURCE = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json"
)


class ZkAiD128RmsnormToProjectionBridgeInputTests(unittest.TestCase):
    def fresh_payload(self) -> dict:
        return BRIDGE.build_payload()

    def test_payload_builds_statement_bound_bridge(self) -> None:
        payload = self.fresh_payload()
        BRIDGE.validate_payload(payload)
        self.assertEqual(payload["operation"], "rmsnorm_to_projection_bridge")
        self.assertEqual(payload["row_count"], BRIDGE.WIDTH)
        self.assertEqual(payload["width"], 128)
        self.assertEqual(payload["source_rmsnorm_output_row_domain"], BRIDGE.SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN)
        self.assertEqual(payload["projection_input_row_domain"], BRIDGE.PROJECTION_INPUT_ROW_DOMAIN)
        self.assertNotEqual(payload["projection_input_row_commitment"], payload["forbidden_output_activation_commitment"])
        self.assertEqual(payload["rows"][0]["rmsnorm_normed_q8"], -387)
        self.assertEqual(payload["rows"][0]["projection_input_q8"], -387)

    def test_payload_rejects_projection_full_output_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["projection_input_row_commitment"] = payload["forbidden_output_activation_commitment"]
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "relabeled as full output"):
            BRIDGE.validate_payload(payload)

    def test_payload_rejects_bridge_row_equality_drift(self) -> None:
        payload = self.fresh_payload()
        payload["rows"][0]["projection_input_q8"] += 1
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "bridge row equality drift"):
            BRIDGE.validate_payload(payload)

    def test_payload_rejects_source_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_rmsnorm_output_row_commitment"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "source RMSNorm output commitment"):
            BRIDGE.validate_payload(payload)

    def test_payload_rejects_projection_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["projection_input_row_commitment"] = "blake2b-256:" + "99" * 32
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "projection input commitment"):
            BRIDGE.validate_payload(payload)

    def test_payload_rejects_statement_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_rmsnorm_statement_commitment"] = "blake2b-256:" + "aa" * 32
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "statement commitment"):
            BRIDGE.validate_payload(payload)

    def test_payload_rejects_public_instance_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["public_instance_commitment"] = "blake2b-256:" + "bb" * 32
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "public instance"):
            BRIDGE.validate_payload(payload)

    def test_payload_accepts_validation_commands_as_multiset(self) -> None:
        payload = self.fresh_payload()
        payload["validation_commands"] = list(reversed(payload["validation_commands"]))
        BRIDGE.validate_payload(payload)

    def test_payload_rejects_validation_command_duplicate(self) -> None:
        payload = self.fresh_payload()
        payload["validation_commands"] = [*payload["validation_commands"], payload["validation_commands"][0]]
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "validation commands drift"):
            BRIDGE.validate_payload(payload)

    def test_source_validation_rejects_normed_m31_bound_drift(self) -> None:
        source = copy.deepcopy(BRIDGE.load_source())
        source["rows"][0]["normed_q8"] = BRIDGE.M31_MODULUS
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "signed M31 bounds"):
            BRIDGE.validate_source(source)

    def test_source_validation_rejects_normed_commitment_drift(self) -> None:
        source = copy.deepcopy(BRIDGE.load_source())
        source["rmsnorm_output_row_commitment"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "source RMSNorm output row commitment"):
            BRIDGE.validate_source(source)

    def test_source_validation_rejects_malformed_statement_commitment(self) -> None:
        source = copy.deepcopy(BRIDGE.load_source())
        source["statement_commitment"] = "blake2b-256:" + "AA" * 32
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "source statement_commitment"):
            BRIDGE.validate_source(source)

    def test_source_validation_rejects_malformed_public_instance_commitment(self) -> None:
        source = copy.deepcopy(BRIDGE.load_source())
        source["public_instance_commitment"] = "not-a-commitment"
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "source public_instance_commitment"):
            BRIDGE.validate_source(source)

    def test_load_source_accepts_attention_derived_payload_when_self_consistent(self) -> None:
        source = BRIDGE.load_source(DERIVED_RMSNORM_SOURCE)
        self.assertNotEqual(source["statement_commitment"], BRIDGE.SOURCE_RMSNORM_STATEMENT_COMMITMENT)
        self.assertNotEqual(
            source["public_instance_commitment"],
            BRIDGE.SOURCE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT,
        )
        self.assertNotEqual(
            source["rmsnorm_output_row_commitment"],
            BRIDGE.SOURCE_RMSNORM_OUTPUT_ROW_COMMITMENT,
        )

        payload = BRIDGE.build_payload(source=source)
        self.assertEqual(payload["source_rmsnorm_statement_commitment"], source["statement_commitment"])
        self.assertEqual(
            payload["source_rmsnorm_output_row_commitment"],
            source["rmsnorm_output_row_commitment"],
        )
        BRIDGE.validate_payload(payload)

    def test_target_validation_rejects_target_commitment_drift(self) -> None:
        target = copy.deepcopy(BRIDGE.load_target())
        target["summary"]["target_commitment"] = "blake2b-256:" + "cc" * 32
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            path = pathlib.Path(raw_tmp) / "target.json"
            path.write_text(json.dumps(target), encoding="utf-8")
            with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "target commitment drift"):
                BRIDGE.load_target(path)

    def test_build_payload_rejects_caller_supplied_target_drift(self) -> None:
        target = copy.deepcopy(BRIDGE.load_target())
        target["target_spec"]["required_proof_backend_version"] = "stwo-rmsnorm-swiglu-residual-d128-v0"
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "target backend version drift"):
            BRIDGE.build_payload(target=target)

    def test_validate_payload_rejects_caller_supplied_target_drift(self) -> None:
        payload = self.fresh_payload()
        target = copy.deepcopy(BRIDGE.load_target())
        target["target_spec"]["target_commitment"] = "blake2b-256:" + "dd" * 32
        with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "target spec commitment drift"):
            BRIDGE.validate_payload(payload, target=target)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "bridge.json"
            tsv_path = tmp / "bridge.tsv"
            BRIDGE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn("projection_input_row_commitment", tsv)
            self.assertIn(payload["statement_commitment"], tsv)

    def test_write_outputs_rejects_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(BRIDGE.D128BridgeInputError, "escapes repository"):
                BRIDGE.write_outputs(payload, tmp / "bridge.json", None)


if __name__ == "__main__":
    unittest.main()
