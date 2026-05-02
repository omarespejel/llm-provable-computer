from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_nested_verifier_backend_contract_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_nested_verifier_backend_contract_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d64 nested-verifier backend contract gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD64NestedVerifierBackendContractGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_contract_go_and_backend_no_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["contract_result"], GATE.CONTRACT_RESULT)
        self.assertEqual(payload["backend_proof_result"], GATE.BACKEND_RESULT)
        self.assertEqual(payload["summary"]["minimum_nested_slice_checks"], 2)
        self.assertEqual(payload["summary"]["selected_slice_count"], 2)
        self.assertEqual(payload["summary"]["source_feasibility_mutation_cases"], 16)
        self.assertEqual(payload["summary"]["source_feasibility_mutations_rejected"], 16)
        self.assertEqual(payload["case_count"], 20)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertIn("missing executable nested-verifier backend", payload["summary"]["first_blocker"])

    def test_contract_commitment_round_trips(self) -> None:
        payload = self.fresh_payload()
        expected = GATE.blake2b_commitment(payload["nested_verifier_contract"], GATE.CONTRACT_DOMAIN)
        self.assertEqual(payload["nested_verifier_contract_commitment"], expected)
        self.assertEqual(payload["summary"]["nested_verifier_contract_commitment"], expected)

    def test_selected_slice_contract_is_pinned_to_first_two_checks(self) -> None:
        contract = self.fresh_payload()["nested_verifier_contract"]
        self.assertEqual(contract["minimum_nested_slice_checks"], 2)
        self.assertEqual(contract["selected_slice_ids"], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        checks = contract["selected_nested_verifier_checks"]
        self.assertEqual([check["index"] for check in checks], [0, 1])
        self.assertEqual([check["slice_id"] for check in checks], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        self.assertEqual(checks[0]["proof_backend_version"], "stwo-d64-rmsnorm-public-row-air-proof-v2")
        self.assertEqual(checks[1]["proof_backend_version"], "stwo-d64-rmsnorm-to-projection-bridge-air-proof-v1")
        for check in checks:
            self.assertTrue(check["source_path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(check["source_file_sha256"]), 64)
            self.assertEqual(len(check["source_payload_sha256"]), 64)

    def test_contract_binds_statement_and_public_input_surfaces(self) -> None:
        contract = self.fresh_payload()["nested_verifier_contract"]
        for field in (
            "source_aggregation_target_commitment",
            "input_block_receipt_commitment",
            "public_instance_commitment",
            "proof_native_parameter_commitment",
            "statement_commitment",
            "input_activation_commitment",
            "output_activation_commitment",
            "slice_chain_commitment",
            "evidence_manifest_commitment",
        ):
            self.assertTrue(contract[field].startswith("blake2b-256:"), field)
        self.assertEqual(contract["verifier_domain"], "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v2")

    def test_mutation_layers_cover_contract_and_backend_surfaces(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["source_feasibility_payload_hash_drift"]["rejection_layer"], "source_feasibility_evidence")
        self.assertEqual(cases["selected_slice_version_drift"]["rejection_layer"], "nested_verifier_contract")
        self.assertEqual(cases["selected_slice_removed"]["rejection_layer"], "nested_verifier_contract")
        self.assertEqual(cases["nested_verifier_contract_commitment_drift"]["rejection_layer"], "nested_verifier_contract_commitment")
        self.assertEqual(cases["nested_verifier_claim_true_without_artifact"]["rejection_layer"], "backend_attempt")
        self.assertEqual(cases["invented_outer_backend_artifact"]["rejection_layer"], "backend_attempt")

    def test_rejects_self_consistent_contract_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["nested_verifier_contract"]["verifier_domain"] = "ptvm:zkai:d64-nested-verifier:tampered:v0"
        GATE.refresh_commitments(payload)
        payload["summary"]["nested_verifier_contract_commitment"] = payload["nested_verifier_contract_commitment"]
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "nested verifier contract"):
            GATE.validate_payload(payload)

    def test_rejects_selected_slice_reordering(self) -> None:
        payload = self.fresh_payload()
        payload["nested_verifier_contract"]["selected_nested_verifier_checks"].reverse()
        GATE.refresh_commitments(payload)
        payload["summary"]["nested_verifier_contract_commitment"] = payload["nested_verifier_contract_commitment"]
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "nested verifier contract"):
            GATE.validate_payload(payload)

    def test_rejects_attempt_to_claim_go_result(self) -> None:
        payload = self.fresh_payload()
        payload["result"] = "GO"
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "result"):
            GATE.validate_payload(payload)

    def test_rejects_backend_artifact_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["backend_attempt"]["proof_or_accumulator_artifacts"].append(
            {"path": "docs/engineering/evidence/fake-nested-proof.json"}
        )
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "outer backend artifact"):
            GATE.validate_payload(payload)

    def test_rejects_noncanonical_source_evidence_path(self) -> None:
        payload = self.fresh_payload()
        payload["source_feasibility_evidence"]["path"] = (
            "docs/engineering/evidence/../evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json"
        )
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "source feasibility evidence path"):
            GATE.validate_payload(payload)

    def test_rejects_validation_command_drift(self) -> None:
        payload = self.fresh_payload()
        payload["validation_commands"][0] = "python3 scripts/tampered.py"
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "validation commands"):
            GATE.validate_payload(payload)

    def test_rejects_inconsistent_mutation_case_count(self) -> None:
        payload = self.fresh_payload()
        payload["case_count"] = payload["case_count"] + 1
        payload["summary"]["mutation_cases"] = payload["case_count"]
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "mutation case_count"):
            GATE.validate_payload(payload)

    def test_rejects_inconsistent_all_mutations_rejected(self) -> None:
        payload = self.fresh_payload()
        payload["all_mutations_rejected"] = False
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "all_mutations_rejected"):
            GATE.validate_payload(payload)

    def test_rejects_consistent_but_non_fail_closed_mutation_metadata(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["mutated_accepted"] = True
        payload["cases"][0]["rejected"] = False
        payload["all_mutations_rejected"] = False
        payload["summary"]["mutations_rejected"] -= 1
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "not all nested-verifier contract mutations"):
            GATE.validate_payload(payload)

    def test_rejects_duplicate_mutation_case(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][1] = copy.deepcopy(payload["cases"][0])
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "duplicate mutation case"):
            GATE.validate_payload(payload)

    def test_rejects_mutation_inventory_drift(self) -> None:
        payload = self.fresh_payload()
        payload["mutation_inventory"][0]["mutation"] = "tampered_mutation"
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "mutation inventory"):
            GATE.validate_payload(payload)

    def test_rejects_case_inventory_reordering(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0], payload["cases"][1] = payload["cases"][1], payload["cases"][0]
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "mutation case inventory"):
            GATE.validate_payload(payload)

    def test_rejects_missing_mutation_metadata_on_serialized_gate_result(self) -> None:
        payload = self.fresh_payload()
        del payload["mutation_inventory"]
        del payload["cases"]
        del payload["case_count"]
        del payload["all_mutations_rejected"]
        payload["summary"].pop("mutation_cases")
        payload["summary"].pop("mutations_rejected")
        with self.assertRaisesRegex(GATE.D64NestedVerifierBackendContractError, "mutation metadata"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "nested-verifier-contract.json"
            tsv_path = tmp / "nested-verifier-contract.tsv"
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("nested_verifier_claim_true_without_artifact", tsv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
