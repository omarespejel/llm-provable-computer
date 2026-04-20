from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_phase42_boundary_correspondence.py"
SPEC = ROOT / "docs" / "engineering" / "design" / "phase42-boundary-correspondence-spec.md"
PAPER3 = ROOT / "docs" / "engineering" / "paper3-composition-prototype.md"

MODULE_SPEC = importlib.util.spec_from_file_location("phase42_checker", CHECKER)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"failed to load Phase42 checker from {CHECKER}")
PHASE42 = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules["phase42_checker"] = PHASE42
MODULE_SPEC.loader.exec_module(PHASE42)


def hash32(char: str) -> str:
    return char * 64


def sample_phase29_contract(start: str, end: str, total_steps: int = 3) -> dict:
    contract = {
        "proof_backend": "stwo",
        "contract_version": PHASE42.STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29,
        "semantic_scope": PHASE42.STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29,
        "phase28_artifact_version": "stwo-phase28-aggregated-chained-folded-intervalized-decoding-state-relation-v1",
        "phase28_semantic_scope": "stwo_execution_parameterized_aggregated_chained_folded_intervalized_proof_carrying_decoding_state_relation",
        "phase28_proof_backend_version": PHASE42.STWO_BACKEND_VERSION_PHASE12,
        "statement_version": PHASE42.CLAIM_STATEMENT_VERSION_V1,
        "required_recursion_posture": PHASE42.STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE,
        "recursive_verification_claimed": False,
        "cryptographic_compression_claimed": False,
        "phase28_bounded_aggregation_arity": 2,
        "phase28_member_count": 2,
        "phase28_member_summaries": 2,
        "phase28_nested_members": 2,
        "total_phase26_members": 4,
        "total_phase25_members": 8,
        "max_nested_chain_arity": 2,
        "max_nested_fold_arity": 2,
        "total_matrices": 1,
        "total_layouts": 1,
        "total_rollups": 1,
        "total_segments": 1,
        "total_steps": total_steps,
        "lookup_delta_entries": 3,
        "max_lookup_frontier_entries": 2,
        "source_template_commitment": hash32("a"),
        "global_start_state_commitment": start,
        "global_end_state_commitment": end,
        "aggregation_template_commitment": hash32("b"),
        "aggregated_chained_folded_interval_accumulator_commitment": hash32("c"),
        "input_contract_commitment": "",
    }
    contract["input_contract_commitment"] = PHASE42.commit_phase29_contract(contract)
    return contract


def make_envelope(index: int, input_boundary: str, output_boundary: str, layout_commitment: str) -> dict:
    envelope = {
        "envelope_version": PHASE42.STWO_DECODING_STEP_ENVELOPE_VERSION_PHASE30,
        "semantic_scope": PHASE42.STWO_DECODING_STEP_ENVELOPE_SCOPE_PHASE30,
        "proof_backend": "stwo",
        "proof_backend_version": PHASE42.STWO_BACKEND_VERSION_PHASE12,
        "statement_version": PHASE42.CLAIM_STATEMENT_VERSION_V1,
        "relation": PHASE42.STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30,
        "layout_commitment": layout_commitment,
        "source_chain_commitment": hash32("1"),
        "step_index": index,
        "input_boundary_commitment": input_boundary,
        "output_boundary_commitment": output_boundary,
        "input_lookup_rows_commitment": hash32("2"),
        "output_lookup_rows_commitment": hash32("3"),
        "shared_lookup_artifact_commitment": hash32("4"),
        "static_lookup_registry_commitment": hash32("5"),
        "proof_commitment": hash32("6"),
        "envelope_commitment": "",
    }
    envelope["envelope_commitment"] = PHASE42.commit_phase30_step_envelope(envelope)
    return envelope


def sample_phase30_manifest(start: str, end: str, total_steps: int = 3) -> dict:
    layout = {
        "layout_version": PHASE42.STWO_DECODING_LAYOUT_VERSION_PHASE12,
        "rolling_kv_pairs": 4,
        "pair_width": 4,
    }
    layout_commitment = PHASE42.commit_phase12_layout(layout)
    boundaries = [start] + [f"9{i:063x}"[-64:] for i in range(1, total_steps)] + [end]
    envelopes = [
        make_envelope(i, boundaries[i], boundaries[i + 1], layout_commitment)
        for i in range(total_steps)
    ]
    manifest = {
        "proof_backend": "stwo",
        "manifest_version": PHASE42.STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
        "semantic_scope": PHASE42.STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30,
        "proof_backend_version": PHASE42.STWO_BACKEND_VERSION_PHASE12,
        "statement_version": PHASE42.CLAIM_STATEMENT_VERSION_V1,
        "source_chain_version": PHASE42.STWO_DECODING_CHAIN_VERSION_PHASE12,
        "source_chain_semantic_scope": PHASE42.STWO_DECODING_CHAIN_SCOPE_PHASE12,
        "source_chain_commitment": hash32("1"),
        "layout": layout,
        "total_steps": total_steps,
        "chain_start_boundary_commitment": start,
        "chain_end_boundary_commitment": end,
        "step_envelopes_commitment": "",
        "envelopes": envelopes,
    }
    manifest["step_envelopes_commitment"] = PHASE42.commit_phase30_step_envelope_list(envelopes)
    return manifest


def sample_phase12_state(step_index: int, layout_commitment: str, salt: str) -> dict:
    state = {
        "state_version": PHASE42.STWO_DECODING_STATE_VERSION_PHASE12,
        "step_index": step_index,
        "position": step_index,
        "layout_commitment": layout_commitment,
        "persistent_state_commitment": hash32("a"),
        "kv_history_commitment": hash32(salt),
        "kv_history_length": step_index,
        "kv_cache_commitment": hash32("b"),
        "incoming_token_commitment": hash32("c"),
        "query_commitment": hash32("d"),
        "output_commitment": hash32("e"),
        "lookup_rows_commitment": hash32("f"),
        "public_state_commitment": "",
    }
    state["public_state_commitment"] = PHASE42.commit_phase12_public_state(state)
    return state


def sample_phase14_state_from_phase12(phase12: dict, salt: str) -> dict:
    state = {
        "state_version": PHASE42.STWO_DECODING_STATE_VERSION_PHASE14,
        "step_index": phase12["step_index"],
        "position": phase12["position"],
        "layout_commitment": phase12["layout_commitment"],
        "persistent_state_commitment": phase12["persistent_state_commitment"],
        "kv_history_commitment": phase12["kv_history_commitment"],
        "kv_history_length": phase12["kv_history_length"],
        "kv_history_chunk_size": 2,
        "kv_history_sealed_commitment": hash32("1"),
        "kv_history_sealed_chunks": 1,
        "kv_history_open_chunk_commitment": hash32("2"),
        "kv_history_open_chunk_pairs": 1,
        "kv_history_frontier_commitment": hash32(salt),
        "kv_history_frontier_pairs": 1,
        "lookup_transcript_commitment": hash32("4"),
        "lookup_transcript_entries": phase12["step_index"] + 1,
        "lookup_frontier_commitment": hash32("5"),
        "lookup_frontier_entries": 1,
        "kv_cache_commitment": phase12["kv_cache_commitment"],
        "incoming_token_commitment": phase12["incoming_token_commitment"],
        "query_commitment": phase12["query_commitment"],
        "output_commitment": phase12["output_commitment"],
        "lookup_rows_commitment": phase12["lookup_rows_commitment"],
        "public_state_commitment": "",
    }
    state["public_state_commitment"] = PHASE42.commit_phase14_public_state(state)
    return state


def sample_boundary_preimage_bundle(total_steps: int = 3) -> tuple[dict, dict, dict, dict]:
    layout = {
        "layout_version": PHASE42.STWO_DECODING_LAYOUT_VERSION_PHASE12,
        "rolling_kv_pairs": 4,
        "pair_width": 4,
    }
    layout_commitment = PHASE42.commit_phase12_layout(layout)
    phase12_start = sample_phase12_state(0, layout_commitment, "0")
    phase12_end = sample_phase12_state(total_steps, layout_commitment, "9")
    phase14_start = sample_phase14_state_from_phase12(phase12_start, "6")
    phase14_end = sample_phase14_state_from_phase12(phase12_end, "7")
    phase30 = sample_phase30_manifest(
        phase12_start["public_state_commitment"],
        phase12_end["public_state_commitment"],
        total_steps,
    )
    phase29 = sample_phase29_contract(
        PHASE42.commit_phase23_boundary_state(phase14_start),
        PHASE42.commit_phase23_boundary_state(phase14_end),
        total_steps,
    )
    evidence = {
        "issue": 180,
        "evidence_version": PHASE42.PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_VERSION,
        "relation_outcome": "hash_preimage_relation",
        "phase12_start_state": phase12_start,
        "phase12_end_state": phase12_end,
        "phase14_start_state": phase14_start,
        "phase14_end_state": phase14_end,
    }
    return phase29, phase30, PHASE42.prepare_phase41_expected(phase29, phase30), evidence


class Phase42BoundaryCorrespondenceTests(unittest.TestCase):
    def test_source_bound_phase41_is_not_phase42_success(self) -> None:
        phase29 = sample_phase29_contract(hash32("d"), hash32("e"))
        phase30 = sample_phase30_manifest(hash32("7"), hash32("8"))
        phase41 = PHASE42.prepare_phase41_expected(phase29, phase30)

        result = PHASE42.evaluate(phase29, phase30, phase41)

        self.assertEqual(result["issue"], 180)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["relation_outcome"], "impossible")
        self.assertEqual(result["decision"], "patch_once_then_stay")
        self.assertTrue(result["phase41_source_bound"])
        self.assertIn("Phase12 public-state boundary preimage", result["missing_evidence"])

    def test_boundary_preimage_evidence_unlocks_hash_preimage_relation(self) -> None:
        phase29, phase30, phase41, evidence = sample_boundary_preimage_bundle()

        result = PHASE42.evaluate(phase29, phase30, phase41, evidence)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["relation_outcome"], "hash_preimage_relation")
        self.assertEqual(result["decision"], "stay_current_path")
        self.assertTrue(result["phase41_source_bound"])
        self.assertEqual(
            result["boundary_preimage_commitments"]["phase23_start_boundary_commitment"],
            phase29["global_start_state_commitment"],
        )

    def test_direct_equality_is_accepted_as_direct_binding(self) -> None:
        phase30 = sample_phase30_manifest(hash32("7"), hash32("8"))
        phase29 = sample_phase29_contract(
            phase30["chain_start_boundary_commitment"],
            phase30["chain_end_boundary_commitment"],
        )

        result = PHASE42.evaluate(phase29, phase30)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["relation_outcome"], "equality")
        self.assertEqual(result["decision"], "stay_current_path")

    def test_rejects_stale_phase29_commitment(self) -> None:
        phase29 = sample_phase29_contract(hash32("d"), hash32("e"))
        phase29["global_start_state_commitment"] = hash32("f")
        phase30 = sample_phase30_manifest(hash32("7"), hash32("8"))

        with self.assertRaisesRegex(PHASE42.Phase42Error, "Phase29 contract"):
            PHASE42.evaluate(phase29, phase30)

    def test_rejects_stale_phase30_envelope_commitment(self) -> None:
        phase29 = sample_phase29_contract(hash32("d"), hash32("e"))
        phase30 = sample_phase30_manifest(hash32("7"), hash32("8"))
        phase30["envelopes"][0]["input_boundary_commitment"] = hash32("f")

        with self.assertRaisesRegex(PHASE42.Phase42Error, "Phase30 envelope 0"):
            PHASE42.evaluate(phase29, phase30)

    def test_rejects_swapped_phase41_source_boundary(self) -> None:
        phase29 = sample_phase29_contract(hash32("d"), hash32("e"))
        phase30 = sample_phase30_manifest(hash32("7"), hash32("8"))
        phase41 = PHASE42.prepare_phase41_expected(phase29, phase30)
        swapped = copy.deepcopy(phase41)
        swapped["phase29_global_start_state_commitment"] = phase41["phase29_global_end_state_commitment"]
        swapped["phase29_global_end_state_commitment"] = phase41["phase29_global_start_state_commitment"]
        swapped["start_boundary_translation_commitment"] = PHASE42.commit_phase41_boundary_translation_pair(
            "start",
            swapped["phase29_global_start_state_commitment"],
            swapped["phase30_chain_start_boundary_commitment"],
            swapped,
        )
        swapped["end_boundary_translation_commitment"] = PHASE42.commit_phase41_boundary_translation_pair(
            "end",
            swapped["phase29_global_end_state_commitment"],
            swapped["phase30_chain_end_boundary_commitment"],
            swapped,
        )
        swapped["boundary_translation_witness_commitment"] = (
            PHASE42.commit_phase41_boundary_translation_witness(swapped)
        )

        with self.assertRaisesRegex(PHASE42.Phase42Error, "source-bound Phase41"):
            PHASE42.evaluate(phase29, phase30, swapped)

    def test_rejects_phase14_preimage_that_does_not_bind_phase29(self) -> None:
        phase29, phase30, phase41, evidence = sample_boundary_preimage_bundle()
        evidence = copy.deepcopy(evidence)
        evidence["phase14_start_state"]["kv_history_frontier_commitment"] = hash32("8")
        evidence["phase14_start_state"]["public_state_commitment"] = (
            PHASE42.commit_phase14_public_state(evidence["phase14_start_state"])
        )

        with self.assertRaisesRegex(PHASE42.Phase42Error, "Phase14 start preimage"):
            PHASE42.evaluate(phase29, phase30, phase41, evidence)

    def test_rejects_phase12_preimage_that_does_not_bind_phase30(self) -> None:
        phase29, phase30, phase41, evidence = sample_boundary_preimage_bundle()
        evidence = copy.deepcopy(evidence)
        evidence["phase12_start_state"]["kv_cache_commitment"] = hash32("8")
        evidence["phase12_start_state"]["public_state_commitment"] = (
            PHASE42.commit_phase12_public_state(evidence["phase12_start_state"])
        )

        with self.assertRaisesRegex(PHASE42.Phase42Error, "Phase12 start preimage"):
            PHASE42.evaluate(phase29, phase30, phase41, evidence)

    def test_rejects_phase12_phase14_shared_core_mismatch(self) -> None:
        phase29, phase30, phase41, evidence = sample_boundary_preimage_bundle()
        evidence = copy.deepcopy(evidence)
        evidence["phase14_end_state"]["query_commitment"] = hash32("8")
        evidence["phase14_end_state"]["public_state_commitment"] = (
            PHASE42.commit_phase14_public_state(evidence["phase14_end_state"])
        )

        with self.assertRaisesRegex(PHASE42.Phase42Error, "shared carried-state field"):
            PHASE42.evaluate(phase29, phase30, phase41, evidence)

    def test_cli_reports_issue_and_patch_once_decision(self) -> None:
        phase29 = sample_phase29_contract(hash32("d"), hash32("e"))
        phase30 = sample_phase30_manifest(hash32("7"), hash32("8"))
        phase41 = PHASE42.prepare_phase41_expected(phase29, phase30)
        with tempfile.TemporaryDirectory() as tempdir:
            temp = pathlib.Path(tempdir)
            phase29_path = temp / "phase29.json"
            phase30_path = temp / "phase30.json"
            phase41_path = temp / "phase41.json"
            phase29_path.write_text(json.dumps(phase29), encoding="utf-8")
            phase30_path.write_text(json.dumps(phase30), encoding="utf-8")
            phase41_path.write_text(json.dumps(phase41), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(CHECKER),
                    "--phase29",
                    str(phase29_path),
                    "--phase30",
                    str(phase30_path),
                    "--phase41",
                    str(phase41_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
        self.assertEqual(result["issue"], 180)
        self.assertEqual(result["decision"], "patch_once_then_stay")

    def test_cli_accepts_boundary_preimage_evidence(self) -> None:
        phase29, phase30, phase41, evidence = sample_boundary_preimage_bundle()
        with tempfile.TemporaryDirectory() as tempdir:
            temp = pathlib.Path(tempdir)
            phase29_path = temp / "phase29.json"
            phase30_path = temp / "phase30.json"
            phase41_path = temp / "phase41.json"
            evidence_path = temp / "phase42-evidence.json"
            phase29_path.write_text(json.dumps(phase29), encoding="utf-8")
            phase30_path.write_text(json.dumps(phase30), encoding="utf-8")
            phase41_path.write_text(json.dumps(phase41), encoding="utf-8")
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(CHECKER),
                    "--phase29",
                    str(phase29_path),
                    "--phase30",
                    str(phase30_path),
                    "--phase41",
                    str(phase41_path),
                    "--boundary-preimage-evidence",
                    str(evidence_path),
                    "--require-clean-relation",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["relation_outcome"], "hash_preimage_relation")

    def test_docs_refer_back_to_issue_180_and_checker(self) -> None:
        spec = SPEC.read_text(encoding="utf-8")
        paper3 = PAPER3.read_text(encoding="utf-8")
        self.assertIn("issues/180", spec)
        self.assertIn("scripts/check_phase42_boundary_correspondence.py", paper3)
        self.assertIn("Issue #180", paper3)


if __name__ == "__main__":
    unittest.main()
