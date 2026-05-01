from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_stwo_vector_row_surface_probe.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_stwo_vector_row_surface_probe", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d64 Stwo surface probe from {SCRIPT_PATH}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class ZkAID64StwoVectorRowSurfaceProbeTests(unittest.TestCase):
    def test_probe_splits_arithmetic_go_from_exact_proof_no_go(self) -> None:
        payload = PROBE.build_probe()
        PROBE.validate_probe(payload)

        self.assertEqual(payload["decision"], PROBE.DECISION)
        statuses = {row["gate"]: row["status"] for row in payload["decision_matrix"]}
        self.assertEqual(statuses["vector_row_arithmetic_surface"], "GO")
        self.assertEqual(statuses["m31_signed_range_fit"], "GO")
        self.assertEqual(statuses["statement_public_instance_binding"], "PARTIAL")
        self.assertEqual(statuses["weight_commitment_consistency"], "NO_GO_YET")
        self.assertEqual(statuses["activation_table_commitment_consistency"], "NO_GO_YET")
        self.assertEqual(statuses["native_stwo_exact_d64_proof"], "NO_GO_YET")

    def test_row_counts_are_pinned_to_d64_statement_shape(self) -> None:
        payload = PROBE.build_probe()
        rows = payload["witness_profile"]["row_counts"]

        self.assertEqual(rows["projection_mul_rows"], 49_152)
        self.assertEqual(rows["gate_projection_mul_rows"], 16_384)
        self.assertEqual(rows["value_projection_mul_rows"], 16_384)
        self.assertEqual(rows["down_projection_mul_rows"], 16_384)
        self.assertEqual(rows["activation_table_rows"], 2_049)
        self.assertEqual(rows["trace_rows_excluding_static_table"], 49_920)

    def test_m31_range_surface_is_pinned(self) -> None:
        payload = PROBE.build_probe()
        m31 = payload["witness_profile"]["m31_range"]

        self.assertEqual(m31["modulus"], 2_147_483_647)
        self.assertEqual(m31["signed_abs_limit"], 1_073_741_823)
        self.assertEqual(m31["max_abs_intermediate"], 849_454)
        self.assertTrue(m31["fits_signed_m31"])

    def test_projection_recomputation_stats_are_pinned(self) -> None:
        profile = PROBE.build_probe()["witness_profile"]
        stats = profile["projection_stats"]

        self.assertEqual(stats["gate"]["max_abs_accumulator"], 25_909)
        self.assertEqual(stats["value"]["max_abs_accumulator"], 27_364)
        self.assertEqual(stats["down"]["max_abs_accumulator"], 8_900)
        self.assertEqual(profile["intermediate_maxima"]["swiglu_product"], 52_328)

    def test_source_fixture_commitment_is_reused_without_claiming_proof(self) -> None:
        payload = PROBE.build_probe()
        fixture = PROBE.FIXTURE.build_fixture()

        self.assertEqual(
            payload["source_fixture"]["statement_commitment"],
            fixture["statement"]["statement_commitment"],
        )
        self.assertEqual(payload["source_fixture"]["proof_status"], "REFERENCE_FIXTURE_NOT_PROVEN")
        self.assertIn("not a Stwo proof", payload["non_claims"])
        self.assertFalse(payload["issue_scope"]["closes_related_issue"])
        self.assertIn("proof_size", payload["issue_scope"]["missing_for_issue_go"])

    def test_validation_rejects_top_level_field_drift(self) -> None:
        payload = PROBE.build_probe()
        payload["unvalidated_claim"] = "proof exists"

        with self.assertRaisesRegex(PROBE.D64VectorRowSurfaceError, "payload field set mismatch"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_arithmetic_overclaim(self) -> None:
        payload = PROBE.build_probe()
        payload["decision_matrix"][-1]["status"] = "GO"
        payload["decision_matrix_commitment"] = PROBE.blake2b_commitment(
            payload["decision_matrix"],
            "ptvm:zkai:d64-stwo-vector-row-decisions:v1",
        )

        with self.assertRaisesRegex(PROBE.D64VectorRowSurfaceError, "decision matrix drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_witness_profile_drift(self) -> None:
        payload = PROBE.build_probe()
        payload["witness_profile"]["row_counts"]["trace_rows_excluding_static_table"] += 1
        payload["witness_profile_commitment"] = PROBE.blake2b_commitment(
            payload["witness_profile"],
            "ptvm:zkai:d64-stwo-vector-row-profile:v1",
        )

        with self.assertRaisesRegex(PROBE.D64VectorRowSurfaceError, "witness profile drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_issue_scope_overclaim(self) -> None:
        payload = PROBE.build_probe()
        payload["issue_scope"]["closes_related_issue"] = True

        with self.assertRaisesRegex(PROBE.D64VectorRowSurfaceError, "issue scope drift"):
            PROBE.validate_probe(payload)

    def test_rows_for_tsv_are_stable_and_scoped(self) -> None:
        payload = PROBE.build_probe()
        rows = PROBE.rows_for_tsv(payload)

        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["target_id"], "rmsnorm-swiglu-residual-d64-v2")
        self.assertEqual(rows[0]["gate"], "vector_row_arithmetic_surface")
        self.assertEqual(rows[0]["status"], "GO")
        self.assertEqual(rows[0]["projection_mul_rows"], 49_152)
        self.assertEqual(rows[0]["fits_signed_m31"], "true")

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "probe.json"
            tsv_path = tmp / "probe.tsv"
            PROBE.write_outputs(payload, json_path, tsv_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], PROBE.SCHEMA)
            tsv_lines = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv_lines[0].split("\t"), list(PROBE.TSV_COLUMNS))
            self.assertIn("weight_commitment_consistency", "\n".join(tsv_lines))

    def test_write_outputs_wraps_os_errors(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            json_path = pathlib.Path(raw_tmp) / "probe.json"
            with (
                mock.patch.object(pathlib.Path, "write_text", side_effect=OSError("disk full")),
                self.assertRaisesRegex(PROBE.D64VectorRowSurfaceError, "failed to write"),
            ):
                PROBE.write_outputs(payload, json_path, None)


if __name__ == "__main__":
    unittest.main()
