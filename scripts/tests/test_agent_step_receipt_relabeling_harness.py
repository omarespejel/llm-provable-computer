from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS_PATH = ROOT / "scripts" / "agent_step_receipt_relabeling_harness.py"
SPEC = importlib.util.spec_from_file_location("agent_step_receipt_harness", HARNESS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load agent receipt harness from {HARNESS_PATH}")
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class AgentStepReceiptRelabelingHarnessTests(unittest.TestCase):
    def test_valid_fixture_verifies(self) -> None:
        self.assertTrue(HARNESS.verify_bundle(HARNESS.build_valid_bundle()))

    def test_all_declared_relabeling_mutations_reject(self) -> None:
        results = HARNESS.run_all_mutations()

        self.assertEqual(set(HARNESS.mutation_cases()), {result["mutation"] for result in results})
        self.assertTrue(
            all(result["rejected"] for result in results),
            [result for result in results if not result["rejected"]],
        )

    def test_receipt_field_mutations_are_labeled_as_stale_evidence_scope(self) -> None:
        results = {
            result["mutation"]: result
            for result in HARNESS.run_all_mutations()
        }

        for name in HARNESS.MUTATION_FIELDS:
            self.assertEqual(results[name]["scope"], "receipt-field-stale-evidence")

    def test_each_required_issue_mutation_has_a_case(self) -> None:
        expected = {
            "receipt_version",
            "model_id",
            "runtime_domain",
            "proof_backend",
            "receipt_parser_version",
            "weights_commitment",
            "model_receipt_commitment",
            "input_commitment",
            "output_action_commitment",
            "quantization_config_commitment",
            "policy_hash",
            "tool_output_hash",
            "prior_state_commitment",
            "next_state_commitment",
            "backend_proof_system_version",
            "verifier_domain_separator",
            "dependency_drop_manifest",
            "evidence_manifest",
            "transcript_hash",
            "trust_class_upgrade_without_proof",
        }

        self.assertTrue(expected.issubset(HARNESS.mutation_cases()))

    def test_omitted_tool_receipts_are_allowed_only_without_claim_or_evidence(self) -> None:
        bundle = HARNESS.make_omitted_tool_receipt_bundle()
        self.assertTrue(HARNESS.verify_bundle(bundle))

        claimed = copy.deepcopy(bundle)
        claimed["receipt"]["tool_receipts_root"] = HARNESS.commitment_for(
            "tool-output-root",
            "tampered",
        )
        HARNESS.recompute_receipt_commitment(claimed)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "omitted field"):
            HARNESS.verify_bundle(claimed)

    def test_trust_vector_reordering_rejects(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["receipt"]["field_trust_class_vector"] = list(
            reversed(bundle["receipt"]["field_trust_class_vector"])
        )
        HARNESS.recompute_receipt_commitment(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "not sorted"):
            HARNESS.verify_bundle(bundle)

    def test_evidence_field_relabel_with_recomputed_receipt_rejects(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["receipt"]["model_identity"] = "different-model-label"
        HARNESS.recompute_receipt_commitment(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "evidence commitment"):
            HARNESS.verify_bundle(bundle)

    def test_parser_version_alias_rejects_even_with_recomputed_receipt(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["receipt"]["receipt_parser_version"] = "agent-step-receipt-parser-v01"
        HARNESS.recompute_receipt_commitment(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "parser version"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_duplicate_id_rejects(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        dep = bundle["dependency_drop_manifest"]["entries"][0]
        bundle["dependency_drop_manifest"]["entries"] = [dep, copy.deepcopy(dep)]
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "duplicate dependency_id"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_dropped_fixture_verifies(self) -> None:
        self.assertTrue(HARNESS.verify_bundle(HARNESS.make_dependency_dropped_model_receipt_bundle()))

    def test_dependency_drop_unknown_kind_rejects(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0]["dependency_kind"] = "model-proof"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "unknown dependency kind"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_non_ascii_replacement_version_rejects(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0]["replacement_receipt_version"] = "receipt\u00e9-v1"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "schema-version"):
            HARNESS.verify_bundle(bundle)

    def test_required_subfact_domain_relabel_rejects(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0]["required_subproof_or_attestation"][
            "verifier_domain"
        ] = "other-domain"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "verifier domain mismatch"):
            HARNESS.verify_bundle(bundle)

    def test_evidence_domain_relabel_rejects(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["evidence_manifest"]["entries"][0]["verifier_domain"] = "other-domain"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "evidence verifier domain mismatch"):
            HARNESS.verify_bundle(bundle)

    def test_self_consistent_receipt_domain_relabel_rejects(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["receipt"]["verifier_domain"] = "other-domain"
        for entry in bundle["evidence_manifest"]["entries"]:
            if entry["corresponding_receipt_field"] == "/verifier_domain":
                entry["commitment"] = HARNESS._evidence_commitment_for_field(
                    "/verifier_domain",
                    "other-domain",
                )
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "unsupported verifier domain"):
            HARNESS.verify_bundle(bundle)

    def test_replacement_receipt_version_alias_rejects(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0][
            "replacement_receipt_version"
        ] = "agent-step-receipt-v01"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "unsupported replacement receipt version"):
            HARNESS.verify_bundle(bundle)

    def test_attested_field_requires_attestation_evidence_kind(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        for entry in bundle["evidence_manifest"]["entries"]:
            if entry["corresponding_receipt_field"] == "/model_identity":
                entry["evidence_kind"] = "replay_source"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "attested field"):
            HARNESS.verify_bundle(bundle)

    def test_replayed_field_requires_replay_source_evidence_kind(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        for entry in bundle["evidence_manifest"]["entries"]:
            if entry["corresponding_receipt_field"] == "/policy_commitment":
                entry["evidence_kind"] = "attestation"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "replayed field"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_manifest_must_map_each_dropped_field_once(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        receipt = bundle["receipt"]
        receipt["policy_commitment"] = receipt["model_receipt_commitment"]
        for entry in receipt["field_trust_class_vector"]:
            if entry["field_path"] == "/policy_commitment":
                entry["trust_class"] = "dependency_dropped"
        for entry in bundle["evidence_manifest"]["entries"]:
            if entry["corresponding_receipt_field"] == "/policy_commitment":
                entry["evidence_kind"] = "subreceipt"
                entry["trust_class"] = "dependency_dropped"
                entry["commitment"] = HARNESS._evidence_commitment_for_field(
                    "/policy_commitment",
                    receipt["policy_commitment"],
                )
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "does not match dropped fields"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_manifest_replacement_must_match_named_field(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0]["replacement_commitment"] = HARNESS.commitment_for(
            "wrong-replacement",
            "toy",
        )
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "replacement mismatch"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_required_support_must_bind_replacement(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0]["required_subproof_or_attestation"][
            "commitment"
        ] = HARNESS.commitment_for("wrong-support", "toy")
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "support commitment mismatch"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_required_support_kind_must_be_subreceipt(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0]["required_subproof_or_attestation"][
            "kind"
        ] = "proof"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "support must be a subreceipt"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_evidence_kind_must_be_subreceipt(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        for entry in bundle["evidence_manifest"]["entries"]:
            if entry["corresponding_receipt_field"] == "/model_receipt_commitment":
                entry["evidence_kind"] = "attestation"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "dependency_dropped field"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_rejects_proof_kind_even_when_evidence_matches(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0]["required_subproof_or_attestation"][
            "kind"
        ] = "proof"
        for entry in bundle["evidence_manifest"]["entries"]:
            if entry["corresponding_receipt_field"] == "/model_receipt_commitment":
                entry["evidence_kind"] = "proof"
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "lacks compatible evidence"):
            HARNESS.verify_bundle(bundle)

    def test_top_level_non_object_rejects_without_raw_exception(self) -> None:
        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "bundle must be an object"):
            HARNESS.verify_bundle(None)

    def test_receipt_non_object_rejects_without_raw_exception(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["receipt"] = []

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "receipt must be an object"):
            HARNESS.verify_bundle(bundle)

    def test_evidence_manifest_non_object_rejects_without_raw_exception(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["evidence_manifest"] = []
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "evidence manifest must be an object"):
            HARNESS.verify_bundle(bundle)

    def test_dependency_drop_manifest_non_object_rejects_without_raw_exception(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"] = []
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "dependency-drop manifest must be an object"):
            HARNESS.verify_bundle(bundle)

    def test_malformed_evidence_id_rejects_without_raw_exception(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        del bundle["evidence_manifest"]["entries"][0]["evidence_id"]
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "unexpected keys"):
            HARNESS.verify_bundle(bundle)

    def test_non_string_dependency_id_rejects_without_raw_exception(self) -> None:
        bundle = HARNESS.make_dependency_dropped_model_receipt_bundle()
        bundle["dependency_drop_manifest"]["entries"][0]["dependency_id"] = 7
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "dependency_id must be a string"):
            HARNESS.verify_bundle(bundle)

    def test_non_object_trust_vector_entry_rejects_without_raw_exception(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["receipt"]["field_trust_class_vector"][0] = "not-an-object"
        HARNESS.recompute_receipt_commitment(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "trust-class entry must be an object"):
            HARNESS.verify_bundle(bundle)

    def test_malformed_non_claims_reject_without_raw_exception(self) -> None:
        bundle = HARNESS.build_valid_bundle()
        bundle["evidence_manifest"]["entries"][0]["non_claims"] = [3]
        HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(HARNESS.AgentReceiptError, "evidence non_claims must be a string"):
            HARNESS.verify_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
