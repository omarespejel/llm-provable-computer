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
    def setUp(self) -> None:
        patcher = mock.patch.dict(
            PROBE.os.environ,
            {
                "SOURCE_DATE_EPOCH": "0",
                "ZKAI_D64_COMMITMENT_CONSISTENCY_PROBE_GIT_COMMIT": "a" * 40,
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_git_commit_honors_probe_specific_override(self) -> None:
        raw_commit = "ABCDEF0123456789ABCDEF0123456789ABCDEF01"
        with mock.patch.dict(
            PROBE.os.environ,
            {
                "SOURCE_DATE_EPOCH": "0",
                "ZKAI_D64_COMMITMENT_CONSISTENCY_PROBE_GIT_COMMIT": raw_commit,
            },
            clear=True,
        ):
            payload = PROBE.build_probe()
            PROBE.validate_probe(payload)
            self.assertEqual(payload["git_commit"], raw_commit.lower())

    def test_git_commit_honors_external_adapter_override_alias(self) -> None:
        raw_commit = "1234ABCD1234ABCD1234ABCD1234ABCD1234ABCD"
        with mock.patch.dict(
            PROBE.os.environ,
            {
                "SOURCE_DATE_EPOCH": "0",
                "ZKAI_D64_EXTERNAL_ADAPTER_PROBE_GIT_COMMIT": raw_commit,
            },
            clear=True,
        ):
            payload = PROBE.build_probe()
            PROBE.validate_probe(payload)
            self.assertEqual(payload["git_commit"], raw_commit.lower())

    def test_git_commit_returns_dirty_sentinel(self) -> None:
        with (
            mock.patch.dict(PROBE.os.environ, {}, clear=True),
            mock.patch.object(PROBE, "_dirty_worktree_paths", return_value={pathlib.Path("scripts/changed.py")}),
        ):
            self.assertEqual(PROBE._git_commit(), PROBE.DIRTY_GIT_COMMIT)

    def test_git_commit_treats_dirty_checked_outputs_as_clean_enough(self) -> None:
        allowed = {
            pathlib.Path("docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.json"),
            pathlib.Path("docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.tsv"),
        }
        completed = mock.Mock(stdout="b" * 40 + "\n")
        with (
            mock.patch.dict(PROBE.os.environ, {}, clear=True),
            mock.patch.object(PROBE, "_dirty_worktree_paths", return_value=allowed),
            mock.patch.object(PROBE.subprocess, "run", return_value=completed),
        ):
            self.assertEqual(PROBE._git_commit(), "b" * 40)

    def test_git_commit_timeout_returns_unavailable(self) -> None:
        with (
            mock.patch.dict(PROBE.os.environ, {}, clear=True),
            mock.patch.object(PROBE, "_dirty_worktree_paths", return_value=set()),
            mock.patch.object(
                PROBE.subprocess,
                "run",
                side_effect=PROBE.subprocess.TimeoutExpired(["git"], PROBE.GIT_TIMEOUT_SECONDS),
            ),
        ):
            self.assertEqual(PROBE._git_commit(), "unavailable")

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

    def test_activation_usage_rejects_empty_projection_surface(self) -> None:
        reference = PROBE.FIXTURE.evaluate_reference_block()
        reference["gate_projection_q8"] = []

        with self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "at least one projection row"):
            PROBE.activation_usage(reference)

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
        self.assertEqual(
            payload["source_fixture"]["proof_native_parameter_commitment"],
            payload["proof_native_parameter_manifest"]["proof_native_parameter_commitment"],
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
        payload["proof_native_parameter_manifest"]["matrix_trees"]["gate"]["leaf_hashes_sha256"] = "00" * 32
        payload["proof_native_parameter_manifest_commitment"] = PROBE.blake2b_commitment(
            payload["proof_native_parameter_manifest"],
            "ptvm:zkai:d64:proof-native-parameter-manifest-payload:v1",
        )

        with self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "proof-native parameter manifest drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_source_fixture_manifest_commitment_mismatch(self) -> None:
        payload = PROBE.build_probe()
        payload["proof_native_parameter_manifest"]["proof_native_parameter_commitment"] = "blake2b-256:" + "55" * 32
        payload["proof_native_parameter_manifest_commitment"] = PROBE.blake2b_commitment(
            payload["proof_native_parameter_manifest"],
            "ptvm:zkai:d64:proof-native-parameter-manifest-payload:v1",
        )

        with self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "commitment mismatch"):
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
                mock.patch.object(PROBE.tempfile, "NamedTemporaryFile", side_effect=OSError("disk full")),
                self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "failed to write"),
            ):
                PROBE.write_outputs(payload, json_path, None)

    def test_write_outputs_rolls_back_json_if_later_replace_fails(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "probe.json"
            tsv_path = tmp / "probe.tsv"
            json_path.write_text("old-json\n", encoding="utf-8")
            tsv_path.write_text("old-tsv\n", encoding="utf-8")
            original_replace = pathlib.Path.replace
            calls = {"count": 0}

            def fail_second_final_replace(self: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
                calls["count"] += 1
                if target == tsv_path and ".backup." not in self.name:
                    raise OSError("tsv replace failed")
                return original_replace(self, target)

            with (
                mock.patch.object(pathlib.Path, "replace", new=fail_second_final_replace),
                self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "failed to write"),
            ):
                PROBE.write_outputs(payload, json_path, tsv_path)

            self.assertGreaterEqual(calls["count"], 2)
            self.assertEqual(json_path.read_text(encoding="utf-8"), "old-json\n")
            self.assertEqual(tsv_path.read_text(encoding="utf-8"), "old-tsv\n")

    def test_checked_output_write_rejects_dirty_source_paths(self) -> None:
        payload = PROBE.build_probe()
        with (
            mock.patch.object(PROBE, "_dirty_worktree_paths", return_value={pathlib.Path("scripts/changed.py")}),
            self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "dirty worktree"),
        ):
            PROBE.write_outputs(payload, PROBE.JSON_OUT, PROBE.TSV_OUT)

    def test_write_outputs_rejects_dirty_commit_sentinel(self) -> None:
        payload = PROBE.build_probe()
        payload["git_commit"] = PROBE.DIRTY_GIT_COMMIT

        with self.assertRaisesRegex(PROBE.CommitmentConsistencyProbeError, "dirty worktree"):
            PROBE.write_outputs(payload, None, None)

    def test_checked_output_write_allows_dirty_checked_outputs_only(self) -> None:
        allowed = {
            pathlib.Path("docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.json"),
            pathlib.Path("docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.tsv"),
        }
        with mock.patch.object(PROBE, "_dirty_worktree_paths", return_value=allowed):
            PROBE._guard_checked_output_write(PROBE.JSON_OUT, PROBE.TSV_OUT)

    def test_temp_output_write_does_not_enforce_checked_artifact_guard(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with mock.patch.object(PROBE, "_dirty_worktree_paths", side_effect=AssertionError("unexpected guard")):
                PROBE.write_outputs(payload, tmp / "probe.json", tmp / "probe.tsv")


if __name__ == "__main__":
    unittest.main()
