from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_two_slice_outer_proof_object_spike_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_two_slice_outer_proof_object_spike_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 two-slice outer proof-object spike gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128TwoSliceOuterProofObjectSpikeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_two_slice_target_go_and_outer_proof_no_go(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["issue"], 408)
        self.assertEqual(payload["target_result"], GATE.TARGET_RESULT)
        self.assertEqual(payload["outer_proof_object_result"], GATE.OUTER_PROOF_RESULT)
        self.assertEqual(payload["summary"]["selected_slice_count"], 2)
        self.assertEqual(payload["summary"]["selected_checked_rows"], 256)
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertIn("no executable outer proof", payload["summary"]["first_blocker"])

    def test_two_slice_target_commitment_round_trips(self) -> None:
        payload = self.fresh_payload()
        expected = GATE.blake2b_commitment(payload["two_slice_target_manifest"], GATE.TARGET_DOMAIN)
        self.assertEqual(payload["two_slice_target_commitment"], expected)
        self.assertEqual(payload["outer_public_input_contract"]["two_slice_target_commitment"], expected)
        self.assertEqual(
            payload["outer_public_input_contract"]["required_public_inputs"],
            [
                "two_slice_target_commitment",
                "selected_slice_statement_commitments",
                "selected_source_evidence_hashes",
            ],
        )
        self.assertEqual(len(payload["outer_public_input_contract"]["selected_slice_statement_commitments"]), 2)
        self.assertEqual(len(payload["outer_public_input_contract"]["selected_source_evidence_hashes"]), 2)

    def test_selected_slice_inventory_is_minimal_and_ordered(self) -> None:
        target = self.fresh_payload()["two_slice_target_manifest"]
        checks = target["selected_slice_checks"]
        self.assertEqual(target["selected_slice_ids"], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        self.assertEqual([check["slice_id"] for check in checks], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        self.assertEqual([check["index"] for check in checks], [0, 1])
        self.assertEqual(sum(check["row_count"] for check in checks), 256)
        for check in checks:
            self.assertTrue(check["source_path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(check["source_file_sha256"]), 64)
            self.assertEqual(len(check["source_payload_sha256"]), 64)
            self.assertTrue(check["statement_commitment"].startswith("blake2b-256:"))

    def test_source_descriptor_binds_full_aggregation_gate(self) -> None:
        descriptor = self.fresh_payload()["source_aggregation_evidence"]
        self.assertEqual(
            descriptor["path"],
            "docs/engineering/evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.json",
        )
        self.assertEqual(descriptor["aggregation_target_result"], GATE.AGGREGATION.TARGET_RESULT)
        self.assertEqual(descriptor["aggregated_proof_object_result"], GATE.AGGREGATION.AGGREGATED_PROOF_RESULT)
        self.assertTrue(descriptor["aggregation_target_commitment"].startswith("blake2b-256:"))

    def test_candidate_inventory_records_missing_required_outer_artifacts(self) -> None:
        inventory = {item["name"]: item for item in self.fresh_payload()["candidate_inventory"]}
        self.assertEqual(
            inventory["d128_full_aggregation_target_gate"]["classification"],
            "FULL_TARGET_ONLY_NOT_TWO_SLICE_OUTER_PROOF",
        )
        self.assertEqual(inventory["d64_two_slice_nested_verifier_spike"]["classification"], "REFERENCE_ONLY_NOT_D128")
        self.assertFalse(inventory["required_two_slice_outer_module"]["exists"])
        self.assertFalse(inventory["required_two_slice_outer_proof_artifact"]["exists"])
        self.assertFalse(inventory["required_two_slice_outer_verifier_handle"]["exists"])
        self.assertFalse(inventory["required_two_slice_outer_mutation_tests"]["exists"])
        self.assertTrue(all(not item["accepted_as_outer_proof_object"] for item in inventory.values()))

    def test_proof_object_attempt_blocks_metrics_until_artifact_exists(self) -> None:
        attempt = self.fresh_payload()["proof_object_attempt"]
        self.assertFalse(attempt["outer_proof_object_claimed"])
        self.assertFalse(attempt["pcd_accumulator_claimed"])
        self.assertFalse(attempt["verifier_handle_claimed"])
        self.assertFalse(attempt["two_slice_target_commitment_bound_as_public_input"])
        self.assertFalse(attempt["selected_slice_statements_bound"])
        self.assertFalse(attempt["selected_source_evidence_hashes_bound"])
        self.assertEqual(attempt["outer_proof_artifacts"], [])
        self.assertEqual(attempt["verifier_handles"], [])
        self.assertTrue(attempt["blocked_before_metrics"])
        self.assertTrue(all(value is None for value in attempt["proof_metrics"].values()))

    def test_mutation_inventory_covers_target_artifact_and_metric_surfaces(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        expected_layers = {
            "source_feasibility_file_hash_drift": "source_aggregation_evidence",
            "two_slice_target_commitment_drift": "two_slice_target_commitment",
            "selected_slice_removed": "two_slice_target",
            "candidate_inventory_acceptance_relabel": "candidate_inventory",
            "outer_proof_claimed_without_artifact": "proof_object_attempt",
            "target_public_input_claimed_without_proof": "proof_object_attempt",
            "selected_statements_claimed_without_proof": "proof_object_attempt",
            "proof_size_metric_smuggled_before_proof": "proof_object_attempt",
            "proof_generation_time_metric_smuggled_before_proof": "proof_object_attempt",
            "outer_proof_result_changed_to_go": "parser_or_schema",
        }
        for mutation, layer in expected_layers.items():
            with self.subTest(mutation=mutation):
                self.assertTrue(cases[mutation]["rejected"])
                self.assertEqual(cases[mutation]["rejection_layer"], layer)

    def test_rejects_self_consistent_target_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["two_slice_target_manifest"]["statement_commitment"] = "blake2b-256:" + "44" * 32
        GATE.refresh_commitments(payload)
        with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "two-slice target manifest"):
            GATE.validate_payload(payload)

    def test_rejects_outer_proof_claim_without_artifact(self) -> None:
        payload = self.fresh_payload()
        payload["proof_object_attempt"]["two_slice_target_commitment_bound_as_public_input"] = True
        with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "claimed"):
            GATE.validate_payload(payload)

    def test_rejects_metric_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["proof_object_attempt"]["proof_metrics"]["verifier_time_ms"] = 1.2
        with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "metric"):
            GATE.validate_payload(payload)

    def test_rejects_non_repo_relative_candidate_path(self) -> None:
        original_specs = GATE.CANDIDATE_SPECS
        try:
            GATE.CANDIDATE_SPECS = (
                {
                    "name": "absolute_path",
                    "kind": "required_outer_proof_artifact",
                    "path": "/tmp/not-this-repo.json",
                    "expected_exists": False,
                    "classification": "MISSING_REQUIRED_ARTIFACT",
                    "required_for_go": True,
                    "reason": "candidate paths must be repo-relative",
                },
            )
            with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "repo-relative"):
                GATE.candidate_inventory()
        finally:
            GATE.CANDIDATE_SPECS = original_specs

    def test_candidate_inventory_treats_dangling_symlink_as_present_required_artifact(self) -> None:
        original_specs = GATE.CANDIDATE_SPECS
        try:
            with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
                tmp = pathlib.Path(raw_tmp)
                link = tmp / "dangling-two-slice-proof.json"
                link.symlink_to(tmp / "missing-target.json")
                GATE.CANDIDATE_SPECS = (
                    {
                        "name": "dangling_required_artifact",
                        "kind": "required_outer_proof_artifact",
                        "path": link.relative_to(ROOT).as_posix(),
                        "expected_exists": False,
                        "classification": "MISSING_REQUIRED_ARTIFACT",
                        "required_for_go": True,
                        "reason": "dangling symlink placeholders must count as present",
                    },
                )
                with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "now exists"):
                    GATE.candidate_inventory()
        finally:
            GATE.CANDIDATE_SPECS = original_specs

    def test_build_payload_returns_copies_of_module_level_lists(self) -> None:
        payload = GATE.build_payload()
        payload["proof_object_attempt"]["missing_backend_features"].append("tampered")
        payload["non_claims"].append("tampered")
        payload["validation_commands"].append("tampered")
        payload["pivot_options"].append({"track": "tampered"})
        self.assertNotIn("tampered", GATE.MISSING_BACKEND_FEATURES)
        self.assertNotIn("tampered", GATE.NON_CLAIMS)
        self.assertNotIn("tampered", GATE.VALIDATION_COMMANDS)
        self.assertNotIn({"track": "tampered"}, GATE.PIVOT_OPTIONS)

    def test_rejects_partial_mutation_metadata_on_serialized_result(self) -> None:
        payload = self.fresh_payload()
        del payload["cases"]
        with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "mutation metadata"):
            GATE.validate_payload(payload)

    def test_rejects_cases_without_mutation_inventory(self) -> None:
        payload = self.fresh_payload()
        del payload["mutation_inventory"]
        with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "mutation metadata"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        header = GATE.to_tsv(self.fresh_payload()).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "two-slice-spike.json").relative_to(ROOT)
            tsv_path = (tmp / "two-slice-spike.tsv").relative_to(ROOT)
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads((ROOT / json_path).read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("outer_proof_claimed_without_artifact", (ROOT / tsv_path).read_text(encoding="utf-8"))

    def test_write_outputs_rejects_absolute_paths(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            absolute_path = pathlib.Path(raw_tmp) / "two-slice-spike.json"
            with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "repo-relative"):
                GATE.write_outputs(payload, absolute_path, None)

    def test_write_outputs_rejects_traversal_paths(self) -> None:
        payload = self.fresh_payload()
        with self.assertRaisesRegex(GATE.D128TwoSliceOuterProofObjectSpikeError, "without traversal"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/../two-slice-spike.json"), None)


if __name__ == "__main__":
    unittest.main()
