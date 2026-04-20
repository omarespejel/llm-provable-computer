from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "paper" / "phase44b_public_projection_logup_probe.py"

SPEC = importlib.util.spec_from_file_location("phase44b_public_projection_logup_probe", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load Phase44B probe script from {SCRIPT}")
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules["phase44b_public_projection_logup_probe"] = PROBE
SPEC.loader.exec_module(PROBE)


class Phase44BPublicProjectionLogUpProbeTests(unittest.TestCase):
    def test_demo_probe_writes_bounded_evidence(self) -> None:
        trace = PROBE.build_demo_trace()
        projection = PROBE.build_projection(trace)
        transcript_bundle = PROBE.build_public_projection_logup_transcript_bundle(trace, projection)
        challenge_bundle = PROBE.derive_public_projection_logup_challenges(
            transcript_bundle, trace, projection
        )
        relation_bundle = PROBE.build_public_projection_logup_relation_bundle(
            trace, projection, transcript_bundle, challenge_bundle
        )
        evidence = PROBE.build_probe_evidence(trace, projection)

        self.assertEqual(evidence["issue"], 180)
        self.assertEqual(evidence["probe"], "phase44b-public-projection-logup-binding")
        self.assertEqual(evidence["total_steps"], 2)
        self.assertEqual(evidence["pair_width"], 2)
        self.assertEqual(evidence["projection_row_count"], 2)
        self.assertEqual(evidence["probe_decision"], "keep_alive_bridge_bound_not_compression")
        self.assertEqual(evidence["phase30_source_chain_commitment"], trace["phase30_source_chain_commitment"])
        self.assertEqual(
            evidence["public_projection_logup_transcript_fields"], transcript_bundle["fields"]
        )
        self.assertEqual(
            evidence["public_projection_logup_transcript_terms"], transcript_bundle["terms"]
        )
        self.assertEqual(
            evidence["public_projection_logup_challenges"],
            {key: value for key, value in challenge_bundle.items() if key != "schema_version"},
        )
        self.assertEqual(
            evidence["public_projection_logup_relation_shape"],
            {key: value for key, value in relation_bundle.items() if key != "schema_version"},
        )
        for key in (
            "trace_commitment",
            "projection_commitment",
            "phase30_source_chain_commitment",
            "appended_pairs_commitment",
            "lookup_rows_commitments_commitment",
            "phase30_step_envelopes_commitment",
            "public_projection_logup_transcript_commitment",
            "public_projection_logup_challenge_seed_commitment",
            "public_projection_logup_relation_commitment",
            "public_projection_logup_binding_commitment",
        ):
            with self.subTest(key=key):
                self.assertRegex(evidence[key], r"^[0-9a-f]{64}$")

        self.assertEqual(
            evidence["public_projection_logup_transcript_fields"][0]["name"],
            "schema_version",
        )
        self.assertIn(
            trace["phase12_start_public_state_commitment"],
            evidence["public_projection_logup_transcript_terms"],
        )
        self.assertIn(
            trace["phase14_end_boundary_commitment"],
            evidence["public_projection_logup_transcript_terms"],
        )
        self.assertEqual(
            evidence["public_projection_logup_challenges"]["lookup_z"],
            challenge_bundle["lookup_z"],
        )
        self.assertEqual(
            evidence["public_projection_logup_challenges"]["lookup_alpha"],
            challenge_bundle["lookup_alpha"],
        )
        self.assertEqual(
            evidence["public_projection_logup_relation_shape"]["row_count"],
            trace["total_steps"],
        )
        self.assertEqual(
            evidence["public_projection_logup_relation_shape"]["domain_separator"],
            PROBE.PHASE44B_LOGUP_BINDING_DOMAIN,
        )

    def test_probe_rejects_row_order_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        trace["rows"] = list(reversed(trace["rows"]))
        with self.assertRaisesRegex(ValueError, "step_index drift"):
            PROBE.build_probe_evidence(trace, PROBE.build_projection(trace))

    def test_probe_rejects_source_chain_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        trace["phase30_source_chain_commitment"] = PROBE.hash32("tampered-source-chain")
        with self.assertRaisesRegex(ValueError, "source-chain commitment drift"):
            PROBE.build_probe_evidence(trace, PROBE.build_projection(trace))

    def test_probe_rejects_lookup_commitment_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        trace["lookup_rows_commitments_commitment"] = PROBE.hash32("tampered")
        with self.assertRaisesRegex(ValueError, "lookup-row commitment drift"):
            PROBE.build_probe_evidence(trace, PROBE.build_projection(trace))

    def test_probe_rejects_top_level_trace_boundary_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        trace["phase12_end_public_state_commitment"] = PROBE.hash32("tampered")
        with self.assertRaisesRegex(ValueError, "phase12_end_public_state_commitment"):
            PROBE.build_probe_evidence(trace, PROBE.build_projection(trace))

    def test_probe_rejects_duplicated_evidence_boundary_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        projection = PROBE.build_projection(trace)
        evidence = PROBE.build_probe_evidence(trace, projection)
        evidence["initial_kv_cache_commitment"] = PROBE.hash32("tampered")
        with self.assertRaisesRegex(ValueError, "initial_kv_cache_commitment drift"):
            PROBE.validate_public_projection_logup_evidence(trace, projection, evidence)

    def test_probe_rejects_embedded_state_step_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        trace["rows"][0]["phase12_to_state"]["kv_history_length"] = 999
        with self.assertRaisesRegex(ValueError, "kv_history_length drift"):
            PROBE.build_probe_evidence(trace, PROBE.build_projection(trace))

    def test_probe_rejects_embedded_state_commitment_shape_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        trace["rows"][0]["phase14_from_state"]["kv_history_frontier_commitment"] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "kv_history_frontier_commitment"):
            PROBE.build_probe_evidence(trace, PROBE.build_projection(trace))

    def test_probe_rejects_transcript_field_omission(self) -> None:
        trace = PROBE.build_demo_trace()
        projection = PROBE.build_projection(trace)
        evidence = PROBE.build_probe_evidence(trace, projection)
        evidence["public_projection_logup_transcript_fields"] = evidence[
            "public_projection_logup_transcript_fields"
        ][1:]
        with self.assertRaisesRegex(ValueError, "transcript field drift"):
            PROBE.validate_public_projection_logup_evidence(trace, projection, evidence)

    def test_probe_rejects_transcript_field_reordering(self) -> None:
        trace = PROBE.build_demo_trace()
        projection = PROBE.build_projection(trace)
        evidence = PROBE.build_probe_evidence(trace, projection)
        fields = copy.deepcopy(evidence["public_projection_logup_transcript_fields"])
        fields[1], fields[2] = fields[2], fields[1]
        evidence["public_projection_logup_transcript_fields"] = fields
        with self.assertRaisesRegex(ValueError, "transcript field drift"):
            PROBE.validate_public_projection_logup_evidence(trace, projection, evidence)

    def test_probe_rejects_challenge_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        projection = PROBE.build_projection(trace)
        evidence = PROBE.build_probe_evidence(trace, projection)
        evidence["public_projection_logup_challenges"] = dict(
            evidence["public_projection_logup_challenges"]
        )
        evidence["public_projection_logup_challenges"]["lookup_alpha"] = (
            evidence["public_projection_logup_challenges"]["lookup_alpha"] + 1
        ) % PROBE.M31_MODULUS or 1
        with self.assertRaisesRegex(ValueError, "challenge bundle drift"):
            PROBE.validate_public_projection_logup_evidence(trace, projection, evidence)

    def test_probe_rejects_relation_shape_drift(self) -> None:
        trace = PROBE.build_demo_trace()
        projection = PROBE.build_projection(trace)
        evidence = PROBE.build_probe_evidence(trace, projection)
        evidence["public_projection_logup_relation_shape"] = dict(
            evidence["public_projection_logup_relation_shape"]
        )
        evidence["public_projection_logup_relation_shape"]["claimed_sum"] = (
            evidence["public_projection_logup_relation_shape"]["claimed_sum"] + 1
        ) % PROBE.M31_MODULUS
        with self.assertRaisesRegex(ValueError, "relation shape drift"):
            PROBE.validate_public_projection_logup_evidence(trace, projection, evidence)

    def test_probe_cli_writes_evidence_and_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = pathlib.Path(tmpdir) / "evidence.json"
            rc = PROBE.main(["--output", str(output), "--emit-surfaces"])
            self.assertEqual(rc, 0)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(evidence["probe"], "phase44b-public-projection-logup-binding")
            self.assertIn("public_projection_logup_transcript_fields", evidence)
            self.assertIn("public_projection_logup_challenges", evidence)
            self.assertIn("public_projection_logup_relation_shape", evidence)
            self.assertTrue((output.parent / "phase43-trace.json").exists())
            self.assertTrue((output.parent / "phase43-projection.json").exists())

            trace_json = output.parent / "phase43-trace.json"
            round_trip_output = pathlib.Path(tmpdir) / "round-trip-evidence.json"
            rc = PROBE.main(["--trace-json", str(trace_json), "--output", str(round_trip_output)])
            self.assertEqual(rc, 0)
            round_trip = json.loads(round_trip_output.read_text(encoding="utf-8"))
            self.assertEqual(round_trip["trace_commitment"], evidence["trace_commitment"])


if __name__ == "__main__":
    unittest.main()
