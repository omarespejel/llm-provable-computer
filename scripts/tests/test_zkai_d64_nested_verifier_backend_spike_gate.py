from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_nested_verifier_backend_spike_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_nested_verifier_backend_spike_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d64 nested-verifier backend spike gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD64NestedVerifierBackendSpikeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_safe_checkpoint_and_hard_no_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["backend_result"], GATE.BACKEND_RESULT)
        self.assertEqual(payload["safe_checkpoint"]["main_commit"], GATE.SAFE_MAIN_COMMIT_AFTER_PR381)
        self.assertEqual(payload["safe_checkpoint"]["recorded_after_pr"], 381)
        self.assertEqual(payload["case_count"], 20)
        self.assertTrue(payload["all_mutations_rejected"])

    def test_consumes_checked_two_slice_contract(self) -> None:
        payload = self.fresh_payload()
        source = payload["source_contract_evidence"]
        self.assertEqual(source["path"], "docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json")
        self.assertEqual(source["contract_result"], GATE.CONTRACT.CONTRACT_RESULT)
        self.assertEqual(source["backend_proof_result"], GATE.CONTRACT.BACKEND_RESULT)
        self.assertEqual(payload["selected_slice_ids"], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        self.assertEqual(payload["nested_verifier_contract_commitment"], source["nested_verifier_contract_commitment"])

    def test_backend_attempt_blocks_metrics_until_proof_exists(self) -> None:
        attempt = self.fresh_payload()["backend_attempt"]
        self.assertFalse(attempt["proof_object_exists"])
        self.assertFalse(attempt["verifier_handle_exists"])
        self.assertFalse(attempt["nested_verifier_contract_commitment_bound_in_outer_backend"])
        self.assertIsNone(attempt["proof_size_bytes"])
        self.assertIsNone(attempt["verifier_time_ms"])
        self.assertTrue(attempt["blocked_before_metrics"])
        self.assertIn("nested verifier program/AIR/circuit for rmsnorm_public_rows", attempt["missing_backend_features"])
        self.assertIn("no executable outer proof/PCD backend", attempt["first_blocker"])

    def test_candidate_inventory_rejects_harness_and_requires_missing_go_artifacts(self) -> None:
        inventory = {item["candidate_id"]: item for item in self.fresh_payload()["backend_attempt"]["candidate_inventory"]}
        self.assertEqual(inventory["checked_two_slice_nested_verifier_contract"]["status"], "CONTRACT_ONLY_NOT_OUTER_PROOF")
        self.assertEqual(inventory["phase36_recursive_verifier_harness_receipt"]["status"], "HARNESS_RECEIPT_NOT_NESTED_PROOF")
        self.assertEqual(
            inventory["decoding_accumulator_demos"]["status"],
            "PRE_RECURSIVE_ACCUMULATOR_DEMO_NOT_D64_SLICE_VERIFIER_PROOF",
        )
        self.assertEqual(inventory["required_two_slice_outer_proof_artifact"]["status"], "MISSING_REQUIRED_GO_ARTIFACT")
        self.assertEqual(inventory["required_two_slice_outer_verifier_handle"]["status"], "MISSING_REQUIRED_GO_ARTIFACT")
        for item in inventory.values():
            self.assertFalse(item["accepted_as_outer_backend"])

    def test_summary_counts_required_missing_artifacts(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(payload["summary"]["candidate_count"], len(GATE.CANDIDATE_SPECS))
        self.assertEqual(payload["summary"]["required_go_artifacts_missing"], 3)
        self.assertEqual(payload["summary"]["mutation_cases"], 20)
        self.assertEqual(payload["summary"]["mutations_rejected"], 20)

    def test_mutation_layers_cover_checkpoint_contract_inventory_and_metrics(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["safe_checkpoint_commit_drift"]["rejection_layer"], "safe_checkpoint")
        self.assertEqual(cases["source_contract_file_hash_drift"]["rejection_layer"], "source_contract_evidence")
        self.assertEqual(cases["nested_verifier_contract_commitment_drift"]["rejection_layer"], "nested_verifier_contract")
        self.assertEqual(cases["candidate_inventory_acceptance_relabel"]["rejection_layer"], "candidate_inventory")
        self.assertEqual(cases["proof_size_metric_smuggled_before_proof"]["rejection_layer"], "backend_attempt")
        self.assertEqual(cases["result_changed_to_go"]["rejection_layer"], "parser_or_schema")

    def test_rejects_self_consistent_attempt_to_call_harness_a_backend(self) -> None:
        payload = self.fresh_payload()
        candidate = payload["backend_attempt"]["candidate_inventory"][2]
        candidate["status"] = "OUTER_PROOF_VERIFIED"
        candidate["accepted_as_outer_backend"] = True
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "candidate inventory"):
            GATE.validate_payload(payload)

    def test_rejects_proof_metric_without_proof_object(self) -> None:
        payload = self.fresh_payload()
        payload["backend_attempt"]["proof_size_bytes"] = 8192
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "proof-size metric"):
            GATE.validate_payload(payload)

    def test_rejects_safe_checkpoint_drift(self) -> None:
        payload = self.fresh_payload()
        payload["safe_checkpoint"]["main_commit"] = "1" * 40
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "safe checkpoint"):
            GATE.validate_payload(payload)

    def test_rejects_noncanonical_source_contract_path(self) -> None:
        payload = self.fresh_payload()
        payload["source_contract_evidence"]["path"] = (
            "docs/engineering/evidence/../evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json"
        )
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "source contract evidence path"):
            GATE.validate_payload(payload)

    def test_rejects_validation_command_drift(self) -> None:
        payload = self.fresh_payload()
        payload["validation_commands"][0] = "python3 scripts/tampered.py"
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "validation commands"):
            GATE.validate_payload(payload)

    def test_rejects_inconsistent_case_count(self) -> None:
        payload = self.fresh_payload()
        payload["case_count"] += 1
        payload["summary"]["mutation_cases"] = payload["case_count"]
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "mutation case_count"):
            GATE.validate_payload(payload)

    def test_rejects_non_fail_closed_case_metadata(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["mutated_accepted"] = True
        payload["cases"][0]["rejected"] = False
        payload["summary"]["mutations_rejected"] -= 1
        payload["all_mutations_rejected"] = False
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "not all backend spike mutations"):
            GATE.validate_payload(payload)

    def test_rejects_duplicate_mutation_case(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][1] = copy.deepcopy(payload["cases"][0])
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "duplicate mutation case"):
            GATE.validate_payload(payload)

    def test_rejects_missing_mutation_metadata_on_serialized_result(self) -> None:
        payload = self.fresh_payload()
        del payload["mutation_inventory"]
        del payload["cases"]
        del payload["case_count"]
        del payload["all_mutations_rejected"]
        payload["summary"].pop("mutation_cases")
        payload["summary"].pop("mutations_rejected")
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendSpikeError, "mutation metadata"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "backend-spike.json"
            tsv_path = tmp / "backend-spike.tsv"
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("proof_size_metric_smuggled_before_proof", tsv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
