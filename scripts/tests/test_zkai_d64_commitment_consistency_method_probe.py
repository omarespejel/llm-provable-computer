from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_commitment_consistency_method_probe.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_commitment_consistency_method_probe", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load commitment consistency probe from {SCRIPT_PATH}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class ZkAID64CommitmentConsistencyMethodProbeTests(unittest.TestCase):
    def test_selects_dual_commitment_as_next_pr_method(self) -> None:
        payload = PROBE.build_probe()
        PROBE.validate_probe(payload)

        self.assertEqual(payload["decision"], PROBE.DECISION)
        self.assertEqual(
            payload["next_pr_target"]["chosen_method"],
            "dual_publication_and_proof_native_parameter_commitment",
        )
        by_method = {row["method"]: row for row in payload["method_matrix"]}
        self.assertEqual(by_method["metadata_only_statement_commitments"]["status"], "NO_GO")
        self.assertEqual(by_method["external_merkle_openings_only"]["status"], "NO_GO")
        self.assertEqual(by_method["public_parameter_columns"]["status"], "POSSIBLE_BUT_EXPENSIVE")
        self.assertEqual(
            by_method["dual_publication_and_proof_native_parameter_commitment"]["status"],
            "GO_FOR_NEXT_PR",
        )

    def test_manifest_counts_are_pinned(self) -> None:
        payload = PROBE.build_probe()
        counts = payload["proof_native_parameter_manifest"]["counts"]

        self.assertEqual(counts["matrix_row_leaves"], 576)
        self.assertEqual(counts["parameter_scalars"], 49_216)
        self.assertEqual(counts["activation_table_leaves"], 2_049)
        self.assertEqual(payload["proof_native_parameter_manifest"]["matrix_trees"]["gate"]["leaf_count"], 256)
        self.assertEqual(payload["proof_native_parameter_manifest"]["matrix_trees"]["value"]["leaf_count"], 256)
        self.assertEqual(payload["proof_native_parameter_manifest"]["matrix_trees"]["down"]["leaf_count"], 64)
        self.assertEqual(payload["proof_native_parameter_manifest"]["rms_scale_tree"]["leaf_count"], 64)

    def test_activation_usage_is_pinned(self) -> None:
        usage = PROBE.build_probe()["activation_usage"]

        self.assertEqual(usage["activation_lookup_rows"], 256)
        self.assertEqual(usage["distinct_activation_lookup_rows"], 204)
        self.assertEqual(usage["min_lookup_index"], 619)
        self.assertEqual(usage["max_lookup_index"], 1399)
        self.assertEqual(usage["clamped_projection_count"], 0)
        self.assertEqual(
            usage["lookup_indices_sha256"],
            "2b83ee17c8634ae1fea3f80bf3361cc83191859db2755fe5264ace164a25990c",
        )

    def test_activation_usage_matches_bounded_clamp_semantics(self) -> None:
        reference = PROBE.FIXTURE.evaluate_reference_block()
        reference["gate_projection_q8"] = [
            -PROBE.FIXTURE.ACTIVATION_CLAMP_Q8 - 17,
            PROBE.FIXTURE.ACTIVATION_CLAMP_Q8 + 23,
            0,
        ]

        usage = PROBE.activation_usage(reference)

        self.assertEqual(usage["activation_lookup_rows"], 3)
        self.assertEqual(usage["distinct_activation_lookup_rows"], 3)
        self.assertEqual(usage["min_lookup_index"], 0)
        self.assertEqual(usage["max_lookup_index"], 2 * PROBE.FIXTURE.ACTIVATION_CLAMP_Q8)
        self.assertEqual(usage["clamped_projection_count"], 2)

    def test_roots_are_stable_for_canonical_fixture(self) -> None:
        manifest = PROBE.build_probe()["proof_native_parameter_manifest"]

        self.assertEqual(
            manifest["proof_native_parameter_commitment"],
            "blake2b-256:861784bd57c039f7fd661810eac42f2aa1893a315ba8e14b441c32717e65efbc",
        )
        self.assertEqual(
            manifest["matrix_trees"]["gate"]["root"],
            "blake2b-256:c7f5f490cc4140756951d0305a4786a1de9a282687c05a161ea04bd658657cfa",
        )
        self.assertEqual(
            manifest["activation_table_tree"]["root"],
            "blake2b-256:393f30234f5f86554d163b2ad0b0759928bce420b878e35576816516f0a8d633",
        )

    def test_source_fixture_publication_hashes_remain_separate(self) -> None:
        payload = PROBE.build_probe()
        fixture = PROBE.FIXTURE.build_fixture()

        self.assertEqual(payload["source_fixture"]["weight_commitment"], fixture["statement"]["weight_commitment"])
        self.assertEqual(
            payload["source_fixture"]["activation_lookup_commitment"],
            fixture["statement"]["activation_lookup_commitment"],
        )
        self.assertNotEqual(
            payload["source_fixture"]["weight_commitment"],
            payload["proof_native_parameter_manifest"]["proof_native_parameter_commitment"],
        )
        self.assertIn("not a claim that publication hashes are verified inside the AIR", payload["non_claims"])

    def test_validation_rejects_extra_top_level_field(self) -> None:
        payload = PROBE.build_probe()
        payload["unvalidated_claim"] = "proof exists"

        with self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "payload field set mismatch"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_method_overclaim(self) -> None:
        payload = PROBE.build_probe()
        payload["method_matrix"][0]["status"] = "GO"
        payload["method_matrix_commitment"] = PROBE.blake2b_commitment(
            payload["method_matrix"],
            "ptvm:zkai:d64:commitment-method-matrix:v1",
        )

        with self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "method matrix drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_manifest_drift(self) -> None:
        payload = PROBE.build_probe()
        payload["proof_native_parameter_manifest"] = PROBE.tampered_manifest()
        payload["proof_native_parameter_manifest_commitment"] = PROBE.blake2b_commitment(
            payload["proof_native_parameter_manifest"],
            "ptvm:zkai:d64:proof-native-parameter-manifest-payload:v1",
        )

        with self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "proof-native parameter manifest drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_next_pr_target_drift(self) -> None:
        payload = PROBE.build_probe()
        payload["next_pr_target"]["chosen_method"] = "metadata_only_statement_commitments"

        with self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "next PR target drift"):
            PROBE.validate_probe(payload)

    def test_rows_for_tsv_are_stable_and_scoped(self) -> None:
        payload = PROBE.build_probe()
        rows = PROBE.rows_for_tsv(payload)

        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[-1]["method"], "dual_publication_and_proof_native_parameter_commitment")
        self.assertEqual(rows[-1]["status"], "GO_FOR_NEXT_PR")
        self.assertEqual(rows[-1]["matrix_row_leaves"], 576)
        self.assertEqual(rows[-1]["parameter_scalars"], 49_216)
        self.assertEqual(rows[-1]["distinct_activation_lookup_rows"], 204)

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
            self.assertIn("dual_publication_and_proof_native_parameter_commitment", "\n".join(tsv_lines))

    def test_write_outputs_wraps_os_errors(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            json_path = pathlib.Path(raw_tmp) / "probe.json"
            with (
                mock.patch.object(pathlib.Path, "write_text", side_effect=OSError("disk full")),
                self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "failed to write"),
            ):
                PROBE.write_outputs(payload, json_path, None)


if __name__ == "__main__":
    unittest.main()
