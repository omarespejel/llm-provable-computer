from __future__ import annotations

import json
import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = REPO / "spec" / "stwo-phase38-paper3-composition-prototype.schema.json"
PAPER3_EVIDENCE = REPO / "docs" / "engineering" / "paper3-claim-evidence.yml"

PROTOTYPE_FIELDS = [
    "proof_backend",
    "prototype_version",
    "semantic_scope",
    "proof_backend_version",
    "statement_version",
    "required_recursion_posture",
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
    "segment_count",
    "total_steps",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "shared_lookup_identity_commitment",
    "segment_list_commitment",
    "naive_per_step_package_count",
    "composed_segment_package_count",
    "package_count_delta",
    "segments",
    "composition_commitment",
]

PHASE29_FIELDS = [
    "proof_backend",
    "contract_version",
    "semantic_scope",
    "phase28_artifact_version",
    "phase28_semantic_scope",
    "phase28_proof_backend_version",
    "statement_version",
    "required_recursion_posture",
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
    "phase28_bounded_aggregation_arity",
    "phase28_member_count",
    "phase28_member_summaries",
    "phase28_nested_members",
    "total_phase26_members",
    "total_phase25_members",
    "max_nested_chain_arity",
    "max_nested_fold_arity",
    "total_matrices",
    "total_layouts",
    "total_rollups",
    "total_segments",
    "total_steps",
    "lookup_delta_entries",
    "max_lookup_frontier_entries",
    "source_template_commitment",
    "global_start_state_commitment",
    "global_end_state_commitment",
    "aggregation_template_commitment",
    "aggregated_chained_folded_interval_accumulator_commitment",
    "input_contract_commitment",
]

SEGMENT_FIELDS = [
    "segment_index",
    "step_start",
    "step_end",
    "total_steps",
    "phase29_contract",
    "phase30_manifest",
    "phase37_receipt",
    "phase37_receipt_commitment",
    "lookup_identity_commitment",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "phase34_shared_lookup_public_inputs_commitment",
    "input_lookup_rows_commitments_commitment",
    "output_lookup_rows_commitments_commitment",
    "shared_lookup_artifact_commitments_commitment",
    "static_lookup_registry_commitments_commitment",
]

HASH_FIELDS = {
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "shared_lookup_identity_commitment",
    "segment_list_commitment",
    "composition_commitment",
    "source_template_commitment",
    "global_start_state_commitment",
    "global_end_state_commitment",
    "aggregation_template_commitment",
    "aggregated_chained_folded_interval_accumulator_commitment",
    "input_contract_commitment",
    "phase37_receipt_commitment",
    "lookup_identity_commitment",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "phase34_shared_lookup_public_inputs_commitment",
    "input_lookup_rows_commitments_commitment",
    "output_lookup_rows_commitments_commitment",
    "shared_lookup_artifact_commitments_commitment",
    "static_lookup_registry_commitments_commitment",
}


class Phase38SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def assert_required_matches_properties(self, node: dict, expected: list[str]) -> None:
        self.assertEqual(node.get("type"), "object")
        self.assertFalse(node.get("additionalProperties"))
        self.assertEqual(node.get("required"), expected)
        self.assertEqual(set(node.get("properties", {})), set(expected))

    def assert_hash_fields_use_hash32(self, node: dict) -> None:
        for field_name, field_schema in node["properties"].items():
            if field_name.endswith("_commitment") or field_name in HASH_FIELDS:
                with self.subTest(hash_field=field_name):
                    self.assertEqual(field_schema, {"$ref": "#/$defs/hash32"})

    def test_schema_pins_phase38_top_level_surface(self) -> None:
        self.assertEqual(
            self.schema["$id"],
            "https://llm-provable-computer/spec/stwo-phase38-paper3-composition-prototype.schema.json",
        )
        self.assert_required_matches_properties(self.schema, PROTOTYPE_FIELDS)
        self.assertEqual(self.schema["properties"]["proof_backend"], {"const": "stwo"})
        self.assertEqual(
            self.schema["properties"]["prototype_version"],
            {"const": "stwo-phase38-paper3-composition-prototype-v1"},
        )
        self.assertEqual(
            self.schema["properties"]["semantic_scope"],
            {"const": "stwo_execution_parameterized_paper3_composition_prototype"},
        )
        self.assertEqual(
            self.schema["properties"]["recursive_verification_claimed"],
            {"const": False},
        )
        self.assertEqual(
            self.schema["properties"]["cryptographic_compression_claimed"],
            {"const": False},
        )
        self.assertEqual(self.schema["properties"]["segments"]["minItems"], 2)
        self.assert_hash_fields_use_hash32(self.schema)

    def test_schema_pins_nested_phase29_source_and_segment_surfaces(self) -> None:
        defs = self.schema["$defs"]
        self.assert_required_matches_properties(defs["phase29_contract"], PHASE29_FIELDS)
        self.assertEqual(
            defs["phase29_contract"]["properties"]["contract_version"],
            {"const": "stwo-phase29-recursive-compression-input-contract-v1"},
        )
        self.assertEqual(
            defs["phase29_contract"]["properties"]["phase28_artifact_version"],
            {"const": "stwo-phase28-aggregated-chained-folded-intervalized-decoding-state-relation-v1"},
        )
        self.assertEqual(
            defs["phase29_contract"]["properties"]["phase28_semantic_scope"],
            {"const": "stwo_execution_parameterized_aggregated_chained_folded_intervalized_proof_carrying_decoding_state_relation"},
        )
        self.assert_hash_fields_use_hash32(defs["phase29_contract"])

        self.assert_required_matches_properties(
            defs["source"],
            ["phase29_contract", "phase30_manifest", "phase37_receipt"],
        )
        self.assertEqual(
            defs["source"]["properties"]["phase30_manifest"],
            {"$ref": "stwo-phase30-decoding-step-envelope-manifest.schema.json"},
        )
        self.assertEqual(
            defs["source"]["properties"]["phase37_receipt"],
            {"$ref": "stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json"},
        )

        self.assert_required_matches_properties(defs["segment"], SEGMENT_FIELDS)
        self.assertEqual(
            defs["segment"]["properties"]["phase29_contract"],
            {"$ref": "#/$defs/phase29_contract"},
        )
        self.assert_hash_fields_use_hash32(defs["segment"])

    def test_paper3_claim_evidence_points_to_schema(self) -> None:
        evidence = PAPER3_EVIDENCE.read_text(encoding="utf-8")
        self.assertIn("spec/stwo-phase38-paper3-composition-prototype.schema.json", evidence)
        self.assertNotIn("no standalone Phase 38 JSON schema", evidence)


if __name__ == "__main__":
    unittest.main()
