from __future__ import annotations

import json
import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = REPO / "spec" / "stwo-phase41-boundary-translation-witness.schema.json"
DOC = REPO / "docs" / "engineering" / "paper3-composition-prototype.md"

WITNESS_FIELDS = [
    "proof_backend",
    "witness_version",
    "semantic_scope",
    "proof_backend_version",
    "statement_version",
    "step_relation",
    "required_recursion_posture",
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
    "derivation_proof_claimed",
    "translation_rule",
    "phase29_contract_version",
    "phase29_semantic_scope",
    "phase29_contract_commitment",
    "phase30_manifest_version",
    "phase30_semantic_scope",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "total_steps",
    "phase29_global_start_state_commitment",
    "phase29_global_end_state_commitment",
    "phase30_chain_start_boundary_commitment",
    "phase30_chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "boundary_domains_differ",
    "start_boundary_translation_commitment",
    "end_boundary_translation_commitment",
    "boundary_translation_witness_commitment",
]

HASH_FIELDS = (
    "phase29_contract_commitment",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "phase29_global_start_state_commitment",
    "phase29_global_end_state_commitment",
    "phase30_chain_start_boundary_commitment",
    "phase30_chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "start_boundary_translation_commitment",
    "end_boundary_translation_commitment",
    "boundary_translation_witness_commitment",
)


class Phase41SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_schema_pins_phase41_surface(self) -> None:
        self.assertEqual(
            self.schema["$id"],
            "https://llm-provable-computer/spec/stwo-phase41-boundary-translation-witness.schema.json",
        )
        self.assertEqual(self.schema.get("type"), "object")
        self.assertIn("additionalProperties", self.schema)
        self.assertIs(self.schema["additionalProperties"], False)
        self.assertEqual(self.schema.get("required"), WITNESS_FIELDS)
        self.assertEqual(set(self.schema.get("properties", {})), set(WITNESS_FIELDS))

    def test_schema_pins_non_claims_and_source_domains(self) -> None:
        properties = self.schema["properties"]
        self.assertEqual(properties["proof_backend"], {"const": "stwo"})
        self.assertEqual(
            properties["witness_version"],
            {"const": "stwo-phase41-boundary-translation-witness-v1"},
        )
        self.assertEqual(
            properties["semantic_scope"],
            {"const": "stwo_execution_parameterized_boundary_translation_witness"},
        )
        self.assertEqual(
            properties["required_recursion_posture"],
            {"const": "pre-recursive-proof-carrying-aggregation"},
        )
        self.assertEqual(properties["recursive_verification_claimed"], {"const": False})
        self.assertEqual(properties["cryptographic_compression_claimed"], {"const": False})
        self.assertEqual(properties["derivation_proof_claimed"], {"const": False})
        self.assertEqual(
            properties["translation_rule"],
            {"const": "explicit-phase29-phase30-boundary-pair-v1"},
        )
        self.assertEqual(properties["boundary_domains_differ"], {"const": True})
        self.assertEqual(properties["total_steps"], {"type": "integer", "minimum": 1})

    def test_schema_uses_hash32_for_commitments(self) -> None:
        for field_name in HASH_FIELDS:
            with self.subTest(hash_field=field_name):
                self.assertEqual(
                    self.schema["properties"][field_name],
                    {"$ref": "#/$defs/hash32"},
                )
        self.assertEqual(
            self.schema["$defs"]["hash32"],
            {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        )

    def test_paper3_doc_points_to_phase41_schema_and_suite(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("spec/stwo-phase41-boundary-translation-witness.schema.json", doc)
        self.assertIn("scripts/run_phase41_boundary_translation_suite.sh", doc)


if __name__ == "__main__":
    unittest.main()
