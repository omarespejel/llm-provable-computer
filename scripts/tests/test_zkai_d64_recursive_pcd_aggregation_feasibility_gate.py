from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_recursive_pcd_aggregation_feasibility_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_recursive_pcd_aggregation_feasibility_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load recursive/PCD feasibility gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD64RecursivePCDAggregationFeasibilityGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_target_go_and_recursive_no_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["aggregation_target_result"], GATE.TARGET_RESULT)
        self.assertEqual(payload["recursive_or_pcd_proof_result"], GATE.RECURSIVE_OR_PCD_RESULT)
        self.assertEqual(payload["summary"]["slice_count"], 6)
        self.assertEqual(payload["summary"]["total_checked_rows"], 49600)
        self.assertEqual(payload["summary"]["composition_mutation_cases"], 14)
        self.assertEqual(payload["summary"]["composition_mutations_rejected"], 14)
        self.assertEqual(payload["case_count"], 16)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertIn("missing recursive verifier", payload["summary"]["first_blocker"])

    def test_aggregation_target_commitment_round_trips(self) -> None:
        payload = self.fresh_payload()
        expected = GATE.blake2b_commitment(payload["aggregation_target_manifest"], GATE.TARGET_DOMAIN)
        self.assertEqual(payload["aggregation_target_commitment"], expected)

    def test_target_manifest_binds_all_nested_slice_checks(self) -> None:
        checks = self.fresh_payload()["aggregation_target_manifest"]["required_nested_verifier_checks"]
        self.assertEqual([check["index"] for check in checks], list(range(6)))
        self.assertEqual(
            [check["slice_id"] for check in checks],
            [
                "rmsnorm_public_rows",
                "rmsnorm_projection_bridge",
                "gate_value_projection",
                "activation_swiglu",
                "down_projection",
                "residual_add",
            ],
        )
        for check in checks:
            self.assertTrue(check["source_path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(check["source_file_sha256"]), 64)
            self.assertEqual(len(check["source_payload_sha256"]), 64)

    def test_mutation_layers_cover_recursive_and_target_surfaces(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["recursive_claim_true_without_proof"]["rejection_layer"], "recursive_or_pcd_attempt")
        self.assertEqual(cases["pcd_claim_true_without_proof"]["rejection_layer"], "recursive_or_pcd_attempt")
        self.assertEqual(cases["invented_recursive_proof_artifact"]["rejection_layer"], "recursive_or_pcd_attempt")
        self.assertEqual(cases["target_manifest_slice_version_drift"]["rejection_layer"], "aggregation_target_manifest")
        self.assertEqual(cases["source_block_receipt_payload_hash_drift"]["rejection_layer"], "source_block_receipt_evidence")

    def test_rejects_self_consistent_block_receipt_projection_drift(self) -> None:
        payload = self.fresh_payload()
        payload["block_receipt_projection"]["proof_native_parameter_commitment"] = "blake2b-256:" + "88" * 32
        GATE.refresh_commitments(payload)
        with self.assertRaisesRegex(GATE.D64RecursivePCDFeasibilityError, "block receipt projection"):
            GATE.validate_payload(payload)

    def test_rejects_attempt_to_claim_recursive_result(self) -> None:
        payload = self.fresh_payload()
        payload["result"] = "GO"
        with self.assertRaisesRegex(GATE.D64RecursivePCDFeasibilityError, "result"):
            GATE.validate_payload(payload)

    def test_rejects_recursive_artifact_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["recursive_or_pcd_attempt"]["recursive_proof_artifacts"].append(
            {"path": "docs/engineering/evidence/fake-recursive-proof.json"}
        )
        with self.assertRaisesRegex(GATE.D64RecursivePCDFeasibilityError, "recursive proof artifact"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "recursive-pcd-feasibility.json"
            tsv_path = tmp / "recursive-pcd-feasibility.tsv"
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("recursive_claim_true_without_proof", tsv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
