from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_phase44d_source_root_manifest.py"
MANIFEST = ROOT / "docs" / "engineering" / "design" / "phase44d_source_root_manifest.json"
BOUNDARY_DOC = ROOT / "docs" / "engineering" / "design" / "phase44d-final-boundary-acceptance.md"

SPEC = importlib.util.spec_from_file_location("phase44d_checker", CHECKER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load Phase44D checker from {CHECKER}")
PHASE44D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PHASE44D)


class Phase44DSourceEmissionPublicOutputTests(unittest.TestCase):
    def load_manifest(self) -> dict[str, object]:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_public_output_binds_source_emission_without_replay_signal(self) -> None:
        manifest = self.load_manifest()
        validated = PHASE44D.validate_manifest(manifest)
        evidence = PHASE44D.probe_manifest(manifest)
        doc_text = BOUNDARY_DOC.read_text(encoding="utf-8")
        manifest_text = MANIFEST.read_text(encoding="utf-8")

        self.assertEqual(validated["source_root"], validated["source_emitted_root"])
        self.assertEqual(
            evidence["source_root_fields"],
            ["source_root", "source_emitted_root", "source_root_preimage"],
        )
        self.assertEqual(
            evidence["compact_root_fields"],
            ["compact_root", "compact_root_preimage"],
        )
        self.assertTrue(all(result["rejected"] for result in evidence["mutation_results"]))

        for text in (doc_text, manifest_text, json.dumps(evidence, sort_keys=True)):
            with self.subTest(text=text[:80]):
                self.assertNotIn("expected_rows", text)
                self.assertNotIn("full_trace", text)

        for phrase in (
            "Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary",
            "Phase44DHistoryReplayProjectionSourceEmission",
            "Phase44DHistoryReplayProjectionSourceEmissionPublicOutput",
            "Phase44DHistoryReplayProjectionSourceEmittedRootArtifact",
            "Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure",
            "Phase44DRecursiveVerifierPublicOutputHandoff",
            "Phase44DRecursiveVerifierPublicOutputAggregation",
            "Phase45RecursiveVerifierPublicInputBridge",
            "Phase45RecursiveVerifierPublicInputLane",
            "derive_phase44d_history_replay_projection_terminal_boundary_logup_closure",
            "verify_phase44d_history_replay_projection_terminal_boundary_logup_closure",
            "emit_phase44d_history_replay_projection_source_chain_public_output_boundary",
            "emit_phase44d_history_replay_projection_source_emission",
            "emit_phase44d_history_replay_projection_source_emission_public_output",
            "project_phase44d_history_replay_projection_source_emission_public_output",
            "phase44d_prepare_recursive_verifier_public_output_handoff",
            "phase44d_prepare_recursive_verifier_public_output_aggregation",
            "phase45_prepare_recursive_verifier_public_input_bridge",
            "verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance",
            "verify_phase44d_history_replay_projection_source_emission_acceptance",
            "verify_phase44d_history_replay_projection_source_emission_public_output_acceptance",
            "verify_phase44d_recursive_verifier_public_output_handoff",
            "verify_phase44d_recursive_verifier_public_output_handoff_against_boundary",
            "verify_phase44d_recursive_verifier_public_output_aggregation",
            "verify_phase45_recursive_verifier_public_input_bridge",
            "verify_phase45_recursive_verifier_public_input_bridge_against_sources",
            "O(boundary_width)",
            "recursive-verifier handoff",
            "source-emission public output",
            "emitted-root artifact",
            "externally emitted canonical source root",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, doc_text)


if __name__ == "__main__":
    unittest.main()
