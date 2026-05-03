from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_aggregated_proof_object_feasibility_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_aggregated_proof_object_feasibility_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 aggregated proof-object feasibility gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128AggregatedProofObjectFeasibilityGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_target_go_and_aggregation_no_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["issue"], 405)
        self.assertEqual(payload["aggregation_target_result"], GATE.TARGET_RESULT)
        self.assertEqual(payload["aggregated_proof_object_result"], GATE.AGGREGATED_PROOF_RESULT)
        self.assertEqual(payload["summary"]["slice_count"], 6)
        self.assertEqual(payload["summary"]["total_checked_rows"], 197_504)
        self.assertEqual(payload["summary"]["composition_mutation_cases"], 20)
        self.assertEqual(payload["summary"]["composition_mutations_rejected"], 20)
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertIn("missing outer proof", payload["summary"]["first_blocker"])

    def test_aggregation_target_commitment_round_trips(self) -> None:
        payload = self.fresh_payload()
        expected = GATE.blake2b_commitment(payload["aggregation_target_manifest"], GATE.TARGET_DOMAIN)
        self.assertEqual(payload["aggregation_target_commitment"], expected)

    def test_public_inputs_bind_receipt_and_statement_commitments(self) -> None:
        public_inputs = self.fresh_payload()["block_receipt_public_inputs"]
        self.assertEqual(
            public_inputs["block_receipt_commitment"],
            "blake2b-256:a2cd8a3dc2f3a5d176fe0a569929fd6e146c4cccfab9aaa18a92a3da057b9c3a",
        )
        self.assertEqual(
            public_inputs["statement_commitment"],
            "blake2b-256:f808e10c539370b63f8f8300a0a6dfa9cb0fa02eed4ca3fbd83a378c4a0a2b60",
        )
        self.assertEqual(
            public_inputs,
            self.fresh_payload()["aggregation_target_manifest"]["public_inputs"],
        )

    def test_target_manifest_binds_all_six_nested_slice_checks(self) -> None:
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
        self.assertEqual(sum(check["row_count"] for check in checks), 197_504)
        for check in checks:
            self.assertTrue(check["source_path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(check["source_file_sha256"]), 64)
            self.assertEqual(len(check["source_payload_sha256"]), 64)
            self.assertTrue(check["proof_native_parameter_commitment"].startswith("blake2b-256:"))
            self.assertTrue(check["public_instance_commitment"].startswith("blake2b-256:"))
            self.assertTrue(check["statement_commitment"].startswith("blake2b-256:"))

    def test_candidate_inventory_records_missing_required_artifacts(self) -> None:
        inventory = {item["name"]: item for item in self.fresh_payload()["candidate_inventory"]}
        self.assertEqual(inventory["d128_block_receipt_composition_gate"]["classification"], "GO_AGGREGATION_TARGET_ONLY")
        self.assertFalse(inventory["d128_full_block_native_module"]["exists"])
        self.assertFalse(inventory["d128_nested_verifier_aggregation_module"]["exists"])
        self.assertFalse(inventory["d128_aggregated_proof_artifact"]["exists"])
        self.assertFalse(inventory["d128_aggregated_verifier_handle"]["exists"])
        self.assertTrue(
            all(not item["accepted_as_aggregated_proof_object"] for item in inventory.values())
        )

    def test_proof_object_attempt_blocks_metrics_until_artifact_exists(self) -> None:
        attempt = self.fresh_payload()["proof_object_attempt"]
        self.assertFalse(attempt["aggregated_proof_object_claimed"])
        self.assertFalse(attempt["recursive_aggregation_claimed"])
        self.assertFalse(attempt["pcd_accumulator_claimed"])
        self.assertFalse(attempt["verifier_handle_claimed"])
        self.assertFalse(attempt["block_receipt_commitment_bound_as_public_input"])
        self.assertFalse(attempt["statement_commitment_bound_as_public_input"])
        self.assertEqual(attempt["aggregated_proof_artifacts"], [])
        self.assertEqual(attempt["verifier_handles"], [])
        self.assertTrue(attempt["blocked_before_metrics"])
        self.assertTrue(all(value is None for value in attempt["proof_metrics"].values()))

    def test_mutation_inventory_covers_binding_artifact_and_metric_surfaces(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        expected_layers = {
            "block_receipt_commitment_drift": "aggregation_target_manifest",
            "statement_commitment_drift": "aggregation_target_manifest",
            "nested_verifier_check_removed": "aggregation_target_manifest",
            "candidate_inventory_acceptance_relabel": "candidate_inventory",
            "aggregated_proof_claimed_without_artifact": "proof_object_attempt",
            "block_receipt_public_input_claimed_without_proof": "proof_object_attempt",
            "proof_size_metric_smuggled_before_proof": "proof_object_attempt",
            "decision_changed_to_go": "parser_or_schema",
        }
        for mutation, layer in expected_layers.items():
            with self.subTest(mutation=mutation):
                self.assertTrue(cases[mutation]["rejected"])
                self.assertEqual(cases[mutation]["rejection_layer"], layer)

    def test_rejects_self_consistent_block_receipt_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["aggregation_target_manifest"]["block_receipt_commitment"] = "blake2b-256:" + "33" * 32
        GATE.refresh_commitments(payload)
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "aggregation target manifest"):
            GATE.validate_payload(payload)

    def test_rejects_self_consistent_statement_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["aggregation_target_manifest"]["statement_commitment"] = "blake2b-256:" + "44" * 32
        GATE.refresh_commitments(payload)
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "aggregation target manifest"):
            GATE.validate_payload(payload)

    def test_rejects_attempt_to_claim_public_input_binding_without_proof(self) -> None:
        payload = self.fresh_payload()
        payload["proof_object_attempt"]["block_receipt_commitment_bound_as_public_input"] = True
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "claimed"):
            GATE.validate_payload(payload)

    def test_rejects_attempt_to_smuggle_proof_metrics(self) -> None:
        payload = self.fresh_payload()
        payload["proof_object_attempt"]["proof_metrics"]["verifier_time_ms"] = 2.5
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "metric"):
            GATE.validate_payload(payload)

    def test_rejects_noncanonical_source_evidence_path(self) -> None:
        payload = self.fresh_payload()
        payload["source_block_receipt_evidence"]["path"] = (
            "docs/engineering/evidence/../evidence/zkai-d128-block-receipt-composition-gate-2026-05.json"
        )
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "source block receipt evidence path"):
            GATE.validate_payload(payload)

    def test_rejects_candidate_inventory_drift(self) -> None:
        payload = self.fresh_payload()
        payload["candidate_inventory"].pop()
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "candidate inventory"):
            GATE.validate_payload(payload)

    def test_rejects_missing_slice_and_manifest_keys_without_raw_keyerror(self) -> None:
        source = GATE.load_json(GATE.BLOCK_RECEIPT_EVIDENCE)
        del source["slice_chain"][0]["schema"]
        del source["source_evidence_manifest"][0]["schema"]
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "key set"):
            GATE._build_payload_from_canonical_source(source)

    def test_rejects_validation_command_drift(self) -> None:
        payload = self.fresh_payload()
        payload["validation_commands"][0] = "python3 scripts/tampered.py"
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "validation commands"):
            GATE.validate_payload(payload)

    def test_rejects_inconsistent_mutation_case_count(self) -> None:
        payload = self.fresh_payload()
        payload["case_count"] += 1
        payload["summary"]["mutation_cases"] = payload["case_count"]
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "mutation case_count"):
            GATE.validate_payload(payload)

    def test_rejects_consistent_but_non_fail_closed_mutation_metadata(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["mutated_accepted"] = True
        payload["cases"][0]["rejected"] = False
        payload["all_mutations_rejected"] = False
        payload["summary"]["mutations_rejected"] -= 1
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "not all"):
            GATE.validate_payload(payload)

    def test_rejects_duplicate_mutation_case(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][1] = copy.deepcopy(payload["cases"][0])
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "duplicate mutation case"):
            GATE.validate_payload(payload)

    def test_rejects_missing_mutation_metadata_on_serialized_gate_result(self) -> None:
        payload = self.fresh_payload()
        del payload["mutation_inventory"]
        del payload["cases"]
        del payload["case_count"]
        del payload["all_mutations_rejected"]
        payload["summary"].pop("mutation_cases")
        payload["summary"].pop("mutations_rejected")
        with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "mutation metadata"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "d128-aggregate-proof-object.json"
            tsv_path = tmp / "d128-aggregate-proof-object.tsv"
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("aggregated_proof_claimed_without_artifact", tsv_path.read_text(encoding="utf-8"))

    def test_write_outputs_rejects_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            out = pathlib.Path(raw_tmp) / "outside.json"
            with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "escapes repository"):
                GATE.write_outputs(payload, out, None)

    def test_write_outputs_rejects_symlink_outputs_inside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            real = tmp / "real.json"
            real.write_text("{}", encoding="utf-8")
            symlink = tmp / "link.json"
            symlink.symlink_to(real)
            with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "symlink"):
                GATE.write_outputs(payload, symlink, None)

    def test_load_json_rejects_symlinked_source_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            real = tmp / "real.json"
            real.write_text("{}", encoding="utf-8")
            symlink = tmp / "source-link.json"
            symlink.symlink_to(real)
            with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "symlink"):
                GATE.load_json(symlink)
            with self.assertRaisesRegex(GATE.D128AggregatedProofObjectFeasibilityError, "symlink"):
                GATE.file_sha256(symlink)


if __name__ == "__main__":
    unittest.main()
