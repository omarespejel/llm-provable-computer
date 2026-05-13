from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_projection_boundary_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_projection_boundary_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load projection boundary gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionDerivedD128ProjectionBoundaryGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = GATE.build_context()
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_result_connects_derived_rmsnorm_to_gate_value_projection(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload, context=copy.deepcopy(self.context))
        summary = payload["summary"]
        bridge = payload["bridge_payload"]
        gate_value = payload["gate_value_projection_payload"]
        source = payload["source_summary"]
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(summary["derived_rmsnorm_output_row_commitment"], source["derived_rmsnorm_output_row_commitment"])
        self.assertEqual(bridge["source_rmsnorm_output_row_commitment"], source["derived_rmsnorm_output_row_commitment"])
        self.assertEqual(bridge["projection_input_row_commitment"], gate_value["source_projection_input_row_commitment"])
        self.assertEqual(gate_value["row_count"], 131_072)
        self.assertEqual(gate_value["gate_projection_mul_rows"], 65_536)
        self.assertEqual(gate_value["value_projection_mul_rows"], 65_536)
        self.assertEqual(payload["case_count"], 12)
        self.assertTrue(payload["all_mutations_rejected"])

    def test_current_block_comparison_is_explicitly_not_matching(self) -> None:
        payload = self.fresh_payload()
        comparison = payload["comparison_summary"]
        self.assertFalse(comparison["matches_existing_d128_gate_value_projection"])
        self.assertEqual(comparison["current_projection_input_mismatch_count"], 127)
        self.assertEqual(comparison["current_gate_projection_mismatch_count"], 512)
        self.assertEqual(comparison["current_value_projection_mismatch_count"], 512)
        self.assertFalse(payload["summary"]["matches_existing_d128_gate_value_projection"])

    def test_bridge_rejects_row_equality_drift(self) -> None:
        payload = self.fresh_payload()
        payload["bridge_payload"]["rows"][0]["projection_input_q8"] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ProjectionBoundaryError, "projection boundary payload drift|bridge equality"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_gate_value_rejects_source_projection_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["gate_value_projection_payload"]["source_projection_input_row_commitment"] = "blake2b-256:" + "66" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ProjectionBoundaryError, "projection boundary payload drift|source projection"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_gate_value_rejects_standalone_source_bridge_public_instance_drift(self) -> None:
        payload = self.fresh_payload()["gate_value_projection_payload"]
        payload["source_bridge_public_instance_commitment"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ProjectionBoundaryError, "source bridge public instance"):
            GATE.validate_gate_value_projection_payload(payload)

    def test_gate_value_rejects_output_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["gate_value_projection_payload"]["gate_projection_q8"][0] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ProjectionBoundaryError, "projection boundary payload drift|gate projection"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_consumption_overclaim(self) -> None:
        payload = self.fresh_payload()
        payload["summary"]["matches_existing_d128_gate_value_projection"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ProjectionBoundaryError, "overclaim|payload drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_to_tsv_requires_final_payload(self) -> None:
        core = GATE.build_core_payload(copy.deepcopy(self.context))
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ProjectionBoundaryError, "finalized payload"):
            GATE.to_tsv(core, context=copy.deepcopy(self.context))

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "projection-boundary.json"
            tsv_path = tmp / "projection-boundary.tsv"
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn("derived_gate_value_projection_output_commitment", tsv)
            self.assertIn(payload["summary"]["derived_gate_value_projection_output_commitment"], tsv)

    def test_write_outputs_rejects_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ProjectionBoundaryError, "docs/engineering/evidence"):
                GATE.write_outputs(payload, tmp / "projection-boundary.json", None)


if __name__ == "__main__":
    unittest.main()
