from __future__ import annotations

import copy
import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_d128_value_adapter_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_d128_value_adapter_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load attention d128 value adapter gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class AttentionD128ValueAdapterGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_builds_honest_no_go_adapter_gate(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertEqual(payload["non_claims"], GATE.NON_CLAIMS)
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATIONS))
        self.assertTrue(payload["all_mutations_rejected"])

        summary = payload["summary"]
        self.assertEqual(summary["attention_cells"], 64)
        self.assertEqual(summary["target_width"], 128)
        self.assertEqual(summary["best_candidate_id"], "best_global_affine_over_tiled_attention")
        self.assertEqual(summary["best_candidate_mismatches"], 124)
        self.assertTrue(summary["target_matches_synthetic_pattern"])
        payload["non_claims"].append("mutated outside constants")
        payload["validation_commands"].append("mutated outside constants")
        self.assertNotIn("mutated outside constants", GATE.NON_CLAIMS)
        self.assertNotIn("mutated outside constants", GATE.VALIDATION_COMMANDS)

    def test_adapter_analysis_binds_source_commitments_and_shapes(self) -> None:
        analysis = self.fresh_payload()["adapter_analysis"]
        self.assertEqual(
            analysis["attention"]["outputs_commitment"],
            "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
        )
        self.assertEqual(analysis["attention"]["shape"], [8, 8])
        self.assertEqual(analysis["attention"]["min_q8"], -3)
        self.assertEqual(analysis["attention"]["max_q8"], 5)
        self.assertEqual(
            analysis["d128_input"]["input_activation_commitment"],
            "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78",
        )
        self.assertEqual(analysis["d128_input"]["width"], 128)
        self.assertEqual(analysis["d128_input"]["min_q8"], -96)
        self.assertEqual(analysis["d128_input"]["max_q8"], 95)
        self.assertEqual(
            analysis["statement_bridge"]["bridge_statement_commitment"],
            "blake2b-256:f180e809c0b0329bc340b34864d8067d6dfa9c4335471ba6adec94e203ec4d2e",
        )
        self.assertEqual(
            analysis["statement_bridge"]["feed_equality_status"],
            "NO_GO_CURRENT_FIXTURES_DO_NOT_BIND_VALUE_EQUALITY",
        )

    def test_rejects_statement_bridge_feed_status_drift(self) -> None:
        attention, d128_input, bridge, _ = GATE._load_sources()
        bridge["summary"]["feed_equality_status"] = "GO_VALUE_EQUALITY"
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "feed equality status drift"):
            GATE.build_adapter_analysis(attention, d128_input, bridge)

    def test_candidate_policies_do_not_match_target(self) -> None:
        candidates = {candidate["id"]: candidate for candidate in self.fresh_payload()["adapter_analysis"]["candidate_policies"]}
        self.assertEqual(candidates["tile_flat_attention_twice"]["mismatch_count"], 127)
        self.assertEqual(candidates["pad_flat_attention_with_zeroes"]["mismatch_count"], 128)
        self.assertEqual(candidates["repeat_each_attention_cell"]["mismatch_count"], 128)
        self.assertEqual(candidates["first_step_repeat_16"]["mismatch_count"], 127)
        self.assertEqual(candidates["last_step_repeat_16"]["mismatch_count"], 128)
        self.assertEqual(candidates["best_global_affine_over_tiled_attention"]["mismatch_count"], 124)
        self.assertFalse(any(candidate["exact_match"] for candidate in candidates.values()))

    def test_detects_independent_d128_fixture_pattern(self) -> None:
        attention, d128_input, _, _ = GATE._load_sources()
        target = GATE._extract_d128_input(d128_input)
        self.assertTrue(all((((13 * index + 7) % 193) - 96) == value for index, value in enumerate(target)))
        self.assertEqual(target[:8], [-89, -76, -63, -50, -37, -24, -11, 2])
        self.assertEqual(target[-8:], [-73, -60, -47, -34, -21, -8, 5, 18])

        attention_outputs = GATE._extract_attention_outputs(attention)
        flat = [cell for row in attention_outputs for cell in row]
        self.assertEqual(len(flat), 64)
        self.assertEqual(min(flat), -3)
        self.assertEqual(max(flat), 5)

    def test_rejects_value_adapter_overclaims(self) -> None:
        payload = self.fresh_payload()
        payload["adapter_analysis"]["candidate_policies"][0]["exact_match"] = True
        payload["adapter_analysis_commitment"] = GATE.blake2b_commitment(payload["adapter_analysis"], GATE.PAYLOAD_DOMAIN)
        payload["summary"] = GATE.summary_from_analysis(payload["adapter_analysis"], payload["adapter_analysis_commitment"])
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "adapter analysis content drift"):
            GATE.validate_payload(payload, expected=self.payload)

        payload = self.fresh_payload()
        payload["adapter_analysis"]["best_candidate"]["mismatch_count"] = 0
        payload["adapter_analysis_commitment"] = GATE.blake2b_commitment(payload["adapter_analysis"], GATE.PAYLOAD_DOMAIN)
        payload["summary"] = GATE.summary_from_analysis(payload["adapter_analysis"], payload["adapter_analysis_commitment"])
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "adapter analysis content drift"):
            GATE.validate_payload(payload)

    def test_source_artifacts_are_hash_bound(self) -> None:
        artifacts = {artifact["id"]: artifact for artifact in self.fresh_payload()["source_artifacts"]}
        self.assertEqual(
            set(artifacts),
            {"attention_d8_bounded_softmax_table", "d128_rmsnorm_input", "attention_block_statement_bridge"},
        )
        for artifact in artifacts.values():
            self.assertTrue(artifact["path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(artifact["sha256"]), 64)
            self.assertEqual(len(artifact["payload_sha256"]), 64)

    def test_rejects_source_artifact_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_artifacts"][0]["sha256"] = "nothex"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "sha256"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["source_artifacts"][0]["sha256"] = "44" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "hash drift"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["source_artifacts"][0]["path"] = "../outside.json"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "repo-relative"):
            GATE.validate_payload(payload)

    def test_tsv_derives_from_analysis(self) -> None:
        payload = self.fresh_payload()
        forged = "blake2b-256:" + "77" * 32
        actual = payload["adapter_analysis"]["attention"]["outputs_commitment"]
        payload["summary"]["attention_outputs_commitment"] = forged
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "summary drift"):
            GATE.validate_payload(payload)
        tsv = GATE.to_tsv(self.fresh_payload())
        self.assertIn(actual, tsv)
        self.assertNotIn(forged, tsv)

    def test_mutation_inventory_rejects_claim_drift(self) -> None:
        payload = self.fresh_payload()
        case_by_name = {case["name"]: case for case in payload["cases"]}
        self.assertEqual(list(case_by_name), list(GATE.EXPECTED_MUTATIONS))
        for name in (
            "decision_promoted",
            "claim_boundary_overclaim",
            "candidate_exact_match_overclaim",
            "candidate_mismatch_zeroed",
            "best_candidate_zeroed",
            "self_consistent_forged_best_candidate_positive",
            "target_pattern_relabelled",
            "source_artifact_sha_drift",
            "payload_commitment_drift",
        ):
            with self.subTest(name=name):
                self.assertTrue(case_by_name[name]["rejected"])
                self.assertFalse(case_by_name[name]["accepted"])

    def test_rejects_numeric_summary_type_drift(self) -> None:
        payload = self.fresh_payload()
        payload["adapter_analysis"]["best_candidate"]["mean_abs_error"] = "47.734375"
        payload["adapter_analysis_commitment"] = GATE.blake2b_commitment(
            payload["adapter_analysis"], GATE.PAYLOAD_DOMAIN
        )
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "finite number"):
            GATE.summary_from_analysis(payload["adapter_analysis"], payload["adapter_analysis_commitment"])
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "adapter analysis content drift"):
            GATE.validate_payload(payload)

    def test_rejects_self_consistent_forged_adapter_analysis(self) -> None:
        payload = self.fresh_payload()
        payload["adapter_analysis"]["best_candidate"]["mismatch_count"] = 1
        payload["adapter_analysis"]["best_candidate"]["mismatch_share"] = 1 / 128
        payload["adapter_analysis_commitment"] = GATE.blake2b_commitment(
            payload["adapter_analysis"], GATE.PAYLOAD_DOMAIN
        )
        payload["summary"] = GATE.summary_from_analysis(
            payload["adapter_analysis"], payload["adapter_analysis_commitment"]
        )
        GATE.refresh_payload_commitment(payload)
        self.assertEqual(payload["summary"]["best_candidate_mismatches"], 1)
        self.assertEqual(payload["payload_commitment"], GATE.payload_commitment(payload))
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "adapter analysis content drift"):
            GATE.validate_payload(payload)

    def test_rejects_malformed_mutation_cases(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0] = 0
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "malformed mutation case"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        del payload["cases"][0]["accepted"]
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "malformed mutation case"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][0]["name"] = "unknown_mutation"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "malformed mutation case"):
            GATE.validate_payload(payload)

    def test_allows_human_mutation_error_wording_drift(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["error"] = "same rejected outcome with clearer wording"
        GATE.refresh_payload_commitment(payload)
        GATE.validate_payload(payload)

    def test_rejects_forged_mutation_outcomes(self) -> None:
        payload = self.fresh_payload()
        real_run_mutation_cases = GATE.run_mutation_cases

        def changed_outcome(core_payload: dict, expected_context: dict) -> list[dict]:
            cases = real_run_mutation_cases(core_payload, expected_context)
            cases[0]["accepted"] = True
            cases[0]["rejected"] = False
            return cases

        with mock.patch.object(GATE, "run_mutation_cases", side_effect=changed_outcome):
            with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "mutation cases drift"):
                GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][0]["accepted"] = True
        payload["cases"][0]["rejected"] = False
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "mutation was not rejected"):
            GATE.validate_payload(payload)

    def test_source_read_loops_until_eof(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-d128-value-adapter-read-loop-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            path = pathlib.Path(handle.name)
            handle.write(b'{"ok": true, "items": [1, 2, 3]}')

        real_read = GATE.os_read

        def short_read(fd: int, count: int) -> bytes:
            return real_read(fd, min(count, 3))

        try:
            with mock.patch.object(GATE, "os_read", side_effect=short_read):
                self.assertEqual(GATE.read_source_bytes(path), b'{"ok": true, "items": [1, 2, 3]}')
        finally:
            path.unlink(missing_ok=True)

    def test_write_outputs_round_trip_and_rejects_outside_path(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-d128-value-adapter-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        try:
            GATE.write_outputs(self.fresh_payload(), json_path.relative_to(GATE.ROOT), tsv_path.relative_to(GATE.ROOT))
            self.assertTrue(json_path.exists())
            self.assertTrue(tsv_path.exists())
            with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "output path must stay"):
                GATE.write_outputs(self.fresh_payload(), pathlib.Path("/tmp/out.json"), None)
            with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "output path must end"):
                GATE.write_outputs(self.fresh_payload(), None, json_path)
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_write_outputs_rolls_back_json_tsv_pair_on_partial_failure(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-d128-value-adapter-rollback-test-",
            suffix=".json",
            delete=False,
            mode="w",
            encoding="utf-8",
        ) as handle:
            json_path = pathlib.Path(handle.name)
            handle.write("old json\n")
        tsv_path = json_path.with_suffix(".tsv")
        tsv_path.write_text("old tsv\n", encoding="utf-8")
        real_replace = GATE.os_replace

        def fail_tsv_commit(src: str, dst: str, *args: object, **kwargs: object) -> None:
            if dst == tsv_path.name and src.startswith(f".{tsv_path.name}.") and src.endswith(".tmp"):
                raise OSError("simulated tsv replace failure")
            real_replace(src, dst, *args, **kwargs)

        try:
            with mock.patch.object(GATE, "os_replace", side_effect=fail_tsv_commit):
                with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "failed writing output group"):
                    GATE.write_outputs(self.fresh_payload(), json_path.relative_to(GATE.ROOT), tsv_path.relative_to(GATE.ROOT))
            self.assertEqual(json_path.read_text(encoding="utf-8"), "old json\n")
            self.assertEqual(tsv_path.read_text(encoding="utf-8"), "old tsv\n")
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_rejects_malformed_commitments_and_parent_symlink_outputs(self) -> None:
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "lowercase hex digest"):
            GATE._commitment("blake2b-256:not-hex", "bad commitment")
        with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "lowercase hex digest"):
            GATE._commitment("sha256:" + "AA" * 32, "uppercase commitment")

        with tempfile.TemporaryDirectory() as outside_dir:
            link_path = GATE.EVIDENCE_DIR / "attention-d128-value-adapter-symlink-parent-test"
            try:
                os.symlink(outside_dir, link_path)
                with self.assertRaisesRegex(GATE.AttentionD128ValueAdapterError, "output parent must stay"):
                    GATE.require_output_path(link_path / "out.json", ".json")
            finally:
                link_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
