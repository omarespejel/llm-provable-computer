from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import unittest
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "engineering" / "design" / "phase44d-final-boundary-acceptance.md"

SCHEMA = "phase44d-final-boundary-acceptance-v1"
SOURCE_CLAIM_VERSION = "phase44d-source-claim-v1"
COMPACT_PROOF_VERSION = "phase44d-compact-proof-v1"
CURRENT_SOURCE_SURFACE_VERSION = "phase43-history-replay-field-projection-v1"
CURRENT_SOURCE_CLAIM_EPOCH = "phase44d-source-claim-epoch-1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash32(label: str, value: Any) -> str:
    digest = hashlib.sha256()
    digest.update(label.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json(value))
    return digest.hexdigest()


def commitment_payload(value: dict[str, Any], commitment_key: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != commitment_key}


def build_source_preimage() -> dict[str, Any]:
    return {
        "projection_log_size": 3,
        "projection_row_count": 8,
        "row_labels": [f"phase44c/projection/row-{index}" for index in range(8)],
        "source_surface_version": CURRENT_SOURCE_SURFACE_VERSION,
    }


def canonical_source_root(preimage: dict[str, Any]) -> str:
    return hash32("phase44d-canonical-source-root-v1", preimage)


def source_preimage_layout_errors(preimage: dict[str, Any]) -> list[str]:
    expected = build_source_preimage()
    required = set(expected)
    if set(preimage) != required:
        return ["mismatched_source_layout"]
    for key, value in expected.items():
        if preimage.get(key) != value:
            return ["mismatched_source_layout"]
    return []


def build_source_claim(root: str) -> dict[str, Any]:
    claim = {
        "claim_epoch": CURRENT_SOURCE_CLAIM_EPOCH,
        "claim_version": SOURCE_CLAIM_VERSION,
        "canonical_source_root": root,
        "source_emitter": "phase44c-source-emitted-projection-root-binding",
        "source_surface_version": CURRENT_SOURCE_SURFACE_VERSION,
    }
    return {
        **claim,
        "source_claim_commitment": hash32(SOURCE_CLAIM_VERSION, claim),
    }


def build_compact_proof(root: str) -> dict[str, Any]:
    proof = {
        "compact_proof_version": COMPACT_PROOF_VERSION,
        "payload_digest": hash32(
            "phase44d-compact-proof-payload-v1",
            {
                "projection_row_count": 8,
                "source_root": root,
                "transcript_shape": "phase44d-boundary-compression-placeholder",
            },
        ),
        "source_root": root,
        "transcript_terms": [
            "phase12-start-boundary",
            root,
            "phase14-end-boundary",
        ],
    }
    return {
        **proof,
        "compact_proof_commitment": hash32(COMPACT_PROOF_VERSION, proof),
    }


def build_envelope(*, useful: bool = True) -> dict[str, Any]:
    preimage = build_source_preimage()
    root = canonical_source_root(preimage)
    return {
        "schema": SCHEMA,
        "canonical_source_root_preimage": preimage,
        "externally_emitted_canonical_source_root": root,
        "externally_emitted_canonical_source_root_verified": True,
        "source_claim": build_source_claim(root),
        "compact_proof": build_compact_proof(root),
        "useful_compression_boundary": useful,
    }


def validate_phase44d_boundary(envelope: dict[str, Any]) -> dict[str, Any]:
    rejection_labels: list[str] = []

    if envelope.get("schema") != SCHEMA:
        rejection_labels.append("schema_drift")

    preimage = envelope.get("canonical_source_root_preimage")
    external_root = envelope.get("externally_emitted_canonical_source_root")
    external_verified = envelope.get("externally_emitted_canonical_source_root_verified")

    if not external_root or external_verified is not True:
        rejection_labels.append("missing_source_root")

    if not isinstance(preimage, dict):
        rejection_labels.append("missing_source_root")
        recomputed_root = None
    else:
        rejection_labels.extend(source_preimage_layout_errors(preimage))
        recomputed_root = canonical_source_root(preimage)
        if preimage.get("source_surface_version") != CURRENT_SOURCE_SURFACE_VERSION:
            rejection_labels.append("stale_source_claim")
        if external_root and external_root != recomputed_root:
            rejection_labels.append("mismatched_source_root")

    source_claim = envelope.get("source_claim")
    if not isinstance(source_claim, dict):
        rejection_labels.append("stale_source_claim")
    else:
        claim_payload = commitment_payload(source_claim, "source_claim_commitment")
        expected_claim_commitment = hash32(SOURCE_CLAIM_VERSION, claim_payload)
        if source_claim.get("claim_version") != SOURCE_CLAIM_VERSION:
            rejection_labels.append("stale_source_claim")
        if source_claim.get("claim_epoch") != CURRENT_SOURCE_CLAIM_EPOCH:
            rejection_labels.append("stale_source_claim")
        if source_claim.get("source_surface_version") != CURRENT_SOURCE_SURFACE_VERSION:
            rejection_labels.append("stale_source_claim")
        if source_claim.get("canonical_source_root") != external_root:
            rejection_labels.append("mismatched_source_root")
        if source_claim.get("source_claim_commitment") != expected_claim_commitment:
            rejection_labels.append("stale_source_claim")

    compact_proof = envelope.get("compact_proof")
    if not isinstance(compact_proof, dict):
        rejection_labels.append("compact_proof_mismatch")
    else:
        expected_terms = [
            "phase12-start-boundary",
            compact_proof.get("source_root"),
            "phase14-end-boundary",
        ]
        recomputed_payload_digest = hash32(
            "phase44d-compact-proof-payload-v1",
            {
                "projection_row_count": 8,
                "source_root": compact_proof.get("source_root"),
                "transcript_shape": "phase44d-boundary-compression-placeholder",
            },
        )
        expected_proof_payload = {
            "compact_proof_version": COMPACT_PROOF_VERSION,
            "payload_digest": recomputed_payload_digest,
            "source_root": compact_proof.get("source_root"),
            "transcript_terms": expected_terms,
        }
        expected_proof_commitment = hash32(COMPACT_PROOF_VERSION, expected_proof_payload)
        if compact_proof.get("compact_proof_version") != COMPACT_PROOF_VERSION:
            rejection_labels.append("compact_proof_mismatch")
        if compact_proof.get("source_root") != external_root:
            rejection_labels.append("compact_proof_mismatch")
        if compact_proof.get("transcript_terms") != expected_terms:
            rejection_labels.append("compact_proof_mismatch")
        if compact_proof.get("payload_digest") != recomputed_payload_digest:
            rejection_labels.append("compact_proof_mismatch")
        if compact_proof.get("compact_proof_commitment") != expected_proof_commitment:
            rejection_labels.append("compact_proof_mismatch")

    accepted = envelope.get("useful_compression_boundary") is True and not rejection_labels
    return {
        "accepted": accepted,
        "rejection_labels": sorted(set(rejection_labels)),
        "useful_compression_boundary": accepted,
    }


class Phase44DFinalBoundaryAcceptanceTests(unittest.TestCase):
    def assert_rejected(self, envelope: dict[str, Any], label: str) -> None:
        decision = validate_phase44d_boundary(envelope)
        self.assertFalse(decision["accepted"])
        self.assertFalse(decision["useful_compression_boundary"])
        self.assertIn(label, decision["rejection_labels"])

    def test_document_records_adversarial_boundary_labels(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for phrase in (
            "useful_compression_boundary = false",
            "externally emitted canonical source root",
            "replay or",
            "expected-row drift",
            "narrow Rust verifier surface",
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
            "verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance",
            "verify_phase44d_recursive_verifier_public_output_handoff",
            "verify_phase44d_recursive_verifier_public_output_handoff_against_boundary",
            "verify_phase44d_recursive_verifier_public_output_aggregation",
            "verify_phase45_recursive_verifier_public_input_bridge",
            "verify_phase45_recursive_verifier_public_input_bridge_against_sources",
            "O(boundary_width)",
            "recursive-verifier handoff",
            "not completed recursive proof closure",
            "publication-grade source emission proof",
            "missing_source_root",
            "mismatched_source_root",
            "stale_source_claim",
            "compact_proof_mismatch",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_only_fully_verified_externalized_shape_crosses_boundary(self) -> None:
        decision = validate_phase44d_boundary(build_envelope(useful=True))
        self.assertTrue(decision["accepted"])
        self.assertTrue(decision["useful_compression_boundary"])
        self.assertEqual(decision["rejection_labels"], [])

    def test_missing_source_root_keeps_boundary_false(self) -> None:
        envelope = build_envelope(useful=True)
        del envelope["externally_emitted_canonical_source_root"]

        self.assert_rejected(envelope, "missing_source_root")

    def test_unverified_source_root_keeps_boundary_false(self) -> None:
        envelope = build_envelope(useful=True)
        envelope["externally_emitted_canonical_source_root_verified"] = False

        self.assert_rejected(envelope, "missing_source_root")

    def test_mismatched_source_root_rejects_self_consistent_wrong_claim(self) -> None:
        envelope = build_envelope(useful=True)
        wrong_root = "1" * 64
        envelope["externally_emitted_canonical_source_root"] = wrong_root
        envelope["source_claim"] = build_source_claim(wrong_root)
        envelope["compact_proof"] = build_compact_proof(wrong_root)

        self.assert_rejected(envelope, "mismatched_source_root")

    def test_source_layout_drift_rejects_recommitted_root_claim_and_proof(self) -> None:
        envelope = build_envelope(useful=True)
        preimage = copy.deepcopy(envelope["canonical_source_root_preimage"])
        preimage["projection_row_count"] = 4
        preimage["projection_log_size"] = 2
        preimage["row_labels"] = preimage["row_labels"][:4]
        wrong_root = canonical_source_root(preimage)
        envelope["canonical_source_root_preimage"] = preimage
        envelope["externally_emitted_canonical_source_root"] = wrong_root
        envelope["source_claim"] = build_source_claim(wrong_root)
        envelope["compact_proof"] = build_compact_proof(wrong_root)

        self.assert_rejected(envelope, "mismatched_source_layout")

    def test_stale_source_claim_rejects_recommitted_claim(self) -> None:
        envelope = build_envelope(useful=True)
        source_claim = copy.deepcopy(envelope["source_claim"])
        source_claim["source_surface_version"] = "phase42-legacy-source-surface-v1"
        source_claim["source_claim_commitment"] = hash32(
            SOURCE_CLAIM_VERSION,
            commitment_payload(source_claim, "source_claim_commitment"),
        )
        envelope["source_claim"] = source_claim

        self.assert_rejected(envelope, "stale_source_claim")

    def test_stale_source_epoch_rejects_recommitted_claim(self) -> None:
        envelope = build_envelope(useful=True)
        source_claim = copy.deepcopy(envelope["source_claim"])
        source_claim["claim_epoch"] = "phase44c-prior-claim-epoch"
        source_claim["source_claim_commitment"] = hash32(
            SOURCE_CLAIM_VERSION,
            commitment_payload(source_claim, "source_claim_commitment"),
        )
        envelope["source_claim"] = source_claim

        self.assert_rejected(envelope, "stale_source_claim")

    def test_compact_proof_payload_mismatch_keeps_boundary_false(self) -> None:
        envelope = build_envelope(useful=True)
        envelope["compact_proof"]["payload_digest"] = hash32("tampered", "payload")

        self.assert_rejected(envelope, "compact_proof_mismatch")

    def test_compact_proof_payload_digest_drift_rejects_recommitted_proof(self) -> None:
        envelope = build_envelope(useful=True)
        compact_proof = copy.deepcopy(envelope["compact_proof"])
        compact_proof["payload_digest"] = hash32("tampered", "payload")
        compact_proof["compact_proof_commitment"] = hash32(
            COMPACT_PROOF_VERSION,
            commitment_payload(compact_proof, "compact_proof_commitment"),
        )
        envelope["compact_proof"] = compact_proof

        self.assert_rejected(envelope, "compact_proof_mismatch")

    def test_compact_proof_source_root_mismatch_keeps_boundary_false(self) -> None:
        envelope = build_envelope(useful=True)
        wrong_root = "2" * 64
        envelope["compact_proof"] = build_compact_proof(wrong_root)

        self.assert_rejected(envelope, "compact_proof_mismatch")

    def test_false_input_boundary_never_promotes_itself(self) -> None:
        decision = validate_phase44d_boundary(build_envelope(useful=False))

        self.assertFalse(decision["accepted"])
        self.assertFalse(decision["useful_compression_boundary"])
        self.assertEqual(decision["rejection_labels"], [])


if __name__ == "__main__":
    unittest.main()
