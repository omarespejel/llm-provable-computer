from __future__ import annotations

import copy
import gzip
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_matched_rmsnorm_swiglu_block_feasibility.py"
SPEC = importlib.util.spec_from_file_location(
    "zkai_matched_rmsnorm_swiglu_block_feasibility",
    SCRIPT_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load matched-block feasibility probe from {SCRIPT_PATH}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class ZkAIMatchedRMSNormSwiGLUBlockFeasibilityTests(unittest.TestCase):
    def test_target_estimates_are_pinned_for_d64_and_d128(self) -> None:
        d64 = PROBE.matched_target(64)
        d128 = PROBE.matched_target(128)

        self.assertEqual(d64["ff_dim"], 256)
        self.assertEqual(d64["required_proof_backend_version"], "stwo-rmsnorm-swiglu-residual-d64-v1")
        self.assertEqual(d64["estimated_linear_muls"], 49_152)
        self.assertEqual(d64["estimated_activation_rows"], 256)
        self.assertEqual(d128["ff_dim"], 512)
        self.assertEqual(d128["required_proof_backend_version"], "stwo-rmsnorm-swiglu-residual-d128-v1")
        self.assertEqual(d128["estimated_linear_muls"], 196_608)
        self.assertEqual(d128["estimated_activation_rows"], 512)

    def test_payload_records_current_surface_no_go_for_both_targets(self) -> None:
        with mock.patch.dict(os.environ, {"ZKAI_GIT_COMMIT": "test-commit"}, clear=True):
            payload = PROBE.build_payload()

        self.assertEqual(payload["schema"], PROBE.SCHEMA)
        self.assertEqual(payload["generated_at"], "1970-01-01T00:00:00Z")
        self.assertEqual(payload["decision"], PROBE.DECISION_NO_GO)
        self.assertEqual(payload["summary"]["target_count"], 2)
        self.assertEqual(payload["summary"]["no_go_count"], 2)
        self.assertEqual(payload["summary"]["go_count"], 0)
        self.assertEqual(payload["current_surface"]["claim_transformer_config"]["d_model"], 36)
        self.assertEqual(payload["current_surface"]["block_logical_width"], 4)
        self.assertEqual(payload["current_surface"]["claim_mul_memory_ops"], 7)
        with gzip.open(PROBE.CURRENT_PROOF_PATH, "rt", encoding="utf-8") as handle:
            proof = json.load(handle)
        self.assertEqual(
            payload["current_surface"]["proof_payload_bytes"],
            len(PROBE.canonical_json_bytes(proof["proof"])),
        )
        self.assertTrue(payload["current_surface"]["fixture_gate"]["fixture_gate_detected"])

        widths = [row["target_width"] for row in payload["rows"]]
        self.assertEqual(widths, [64, 128])
        for row in payload["rows"]:
            self.assertEqual(row["status"], "NO_GO_CURRENT_SURFACE")
            blocker_ids = {blocker["id"] for blocker in row["blockers"]}
            self.assertIn("proof_claim_d_model_mismatch", blocker_ids)
            self.assertIn("statement_profile_width_mismatch", blocker_ids)
            self.assertIn("instruction_surface_too_small_for_swiglu", blocker_ids)
            self.assertIn("proof_generator_fixture_allowlist", blocker_ids)

    def test_current_surface_rejects_stale_statement_evidence(self) -> None:
        evidence = json.loads(PROBE.CURRENT_EVIDENCE_PATH.read_text(encoding="utf-8"))
        proof_path = PROBE.CURRENT_PROOF_PATH

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            evidence["summary"]["stwo-statement-envelope"]["all_mutations_rejected"] = False
            evidence_path = tmp / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            with self.assertRaisesRegex(PROBE.FeasibilityError, "does not reject every checked mutation"):
                PROBE.current_surface(evidence_path=evidence_path, proof_path=proof_path)

    def test_current_surface_rejects_profile_metadata_drift(self) -> None:
        evidence = json.loads(PROBE.CURRENT_EVIDENCE_PATH.read_text(encoding="utf-8"))
        evidence["artifact_metadata"]["transformer_block_profile"]["logical_width"] = 64

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            evidence_path = tmp / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            with self.assertRaisesRegex(PROBE.FeasibilityError, "logical_width disagrees"):
                PROBE.current_surface(evidence_path=evidence_path, proof_path=PROBE.CURRENT_PROOF_PATH)

    def test_current_surface_rejects_baseline_statement_model_id_drift(self) -> None:
        evidence = json.loads(PROBE.CURRENT_EVIDENCE_PATH.read_text(encoding="utf-8"))
        evidence["cases"][0]["baseline_statement"]["model_id"] = "urn:zkai:ptvm:wrong-model"

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            evidence_path = tmp / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            with self.assertRaisesRegex(PROBE.FeasibilityError, "baseline_statement.model_id"):
                PROBE.current_surface(evidence_path=evidence_path, proof_path=PROBE.CURRENT_PROOF_PATH)

    def test_current_surface_rejects_missing_baseline_statement_model_id(self) -> None:
        evidence = json.loads(PROBE.CURRENT_EVIDENCE_PATH.read_text(encoding="utf-8"))
        del evidence["cases"][0]["baseline_statement"]["model_id"]

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            evidence_path = tmp / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            with self.assertRaisesRegex(PROBE.FeasibilityError, "baseline_statement.model_id"):
                PROBE.current_surface(evidence_path=evidence_path, proof_path=PROBE.CURRENT_PROOF_PATH)

    def test_current_surface_rejects_malformed_proof_instruction_shape(self) -> None:
        with gzip.open(PROBE.CURRENT_PROOF_PATH, "rt", encoding="utf-8") as handle:
            proof = json.load(handle)
        proof["claim"]["program"]["instructions"][0] = {"Load": 0, "Extra": 1}

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            proof_path = tmp / "proof.json.gz"
            with gzip.open(proof_path, "wt", encoding="utf-8") as handle:
                json.dump(proof, handle)

            with self.assertRaisesRegex(PROBE.FeasibilityError, "singleton object"):
                PROBE.current_surface(
                    evidence_path=PROBE.CURRENT_EVIDENCE_PATH,
                    proof_path=proof_path,
                )

    def test_fixture_gate_scan_fails_closed_when_source_markers_are_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            source = tmp / "probe.rs"
            source.write_text("fn matches_linear_block_v4_with_lookup() {}\n", encoding="utf-8")

            result = PROBE._fixture_gate_scan(source)

        self.assertFalse(result["fixture_gate_detected"])
        self.assertTrue(result["markers"]["linear_block_v4_with_lookup"])
        self.assertFalse(result["markers"]["decoding_step_v2_family"])

    def test_fixture_gate_scan_records_external_paths_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            source = pathlib.Path(raw_tmp) / "probe.rs"
            source.write_text(
                "\n".join(
                    [
                        "fn matches_linear_block_v4_with_lookup() {}",
                        "fn matches_decoding_step_v2() {}",
                        "// broader arithmetic-subset AIR coverage remains internal",
                    ]
                ),
                encoding="utf-8",
            )

            result = PROBE._fixture_gate_scan(source)

        self.assertTrue(result["fixture_gate_detected"])
        self.assertTrue(result["source_path"])
        self.assertNotEqual(result["source_path"], ".")

    def test_tsv_rows_are_stable_and_include_gap_factor(self) -> None:
        current = {
            "proof_backend_version": PROBE.CURRENT_FIXTURE_PROOF_SYSTEM_VERSION,
            "claim_transformer_config": {"d_model": 36},
            "block_logical_width": 4,
            "claim_mul_memory_ops": 7,
            "fixture_gate": {"fixture_gate_detected": True},
        }
        rows = [
            PROBE.classify_target(current, PROBE.matched_target(64)),
            PROBE.classify_target(current, PROBE.matched_target(128)),
        ]
        payload = {"rows": rows}

        tsv_rows = PROBE.rows_for_tsv(payload)

        self.assertEqual(tsv_rows[0]["target_width"], 64)
        self.assertEqual(tsv_rows[0]["mul_gap_factor"], "7021.714")
        self.assertEqual(tsv_rows[1]["mul_gap_factor"], "28086.857")
        self.assertEqual(tsv_rows[0]["blocker_count"], 4)

    def test_generated_at_is_deterministic_by_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(PROBE._generated_at(), "1970-01-01T00:00:00Z")

    def test_generated_at_rejects_malformed_source_date_epoch(self) -> None:
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "not-an-int"}, clear=True):
            with self.assertRaisesRegex(PROBE.FeasibilityError, "SOURCE_DATE_EPOCH"):
                PROBE._generated_at()

    def test_generated_at_rejects_out_of_range_source_date_epoch(self) -> None:
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": str(10**100)}, clear=True):
            with self.assertRaisesRegex(PROBE.FeasibilityError, "timestamp range"):
                PROBE._generated_at()

    def test_classifier_can_report_go_for_synthetic_matched_surface(self) -> None:
        current = {
            "proof_backend_version": "stwo-rmsnorm-swiglu-residual-d64-v1",
            "claim_transformer_config": {"d_model": 64},
            "block_logical_width": 64,
            "claim_mul_memory_ops": 49_152,
            "fixture_gate": {"fixture_gate_detected": False},
        }

        row = PROBE.classify_target(current, PROBE.matched_target(64))

        self.assertEqual(row["status"], "GO_FEASIBLE")
        self.assertEqual(row["blockers"], [])
        self.assertEqual(PROBE.decision_for_rows([row]), PROBE.DECISION_GO)

    def test_classifier_allows_explicit_matched_backend_even_if_fixture_markers_remain(self) -> None:
        current = {
            "proof_backend_version": "stwo-rmsnorm-swiglu-residual-d64-v1",
            "claim_transformer_config": {"d_model": 64},
            "block_logical_width": 64,
            "claim_mul_memory_ops": 49_152,
            "fixture_gate": {"fixture_gate_detected": True},
        }

        row = PROBE.classify_target(current, PROBE.matched_target(64))

        self.assertEqual(row["status"], "GO_FEASIBLE")
        self.assertEqual(row["blockers"], [])

    def test_classifier_keeps_fixture_blocker_for_renamed_backend_version(self) -> None:
        current = {
            "proof_backend_version": "stwo-phase10-linear-block-v5-renamed",
            "claim_transformer_config": {"d_model": 64},
            "block_logical_width": 64,
            "claim_mul_memory_ops": 49_152,
            "fixture_gate": {"fixture_gate_detected": True},
        }

        row = PROBE.classify_target(current, PROBE.matched_target(64))

        self.assertEqual(row["status"], "NO_GO_CURRENT_SURFACE")
        self.assertEqual(
            [blocker["id"] for blocker in row["blockers"]],
            ["proof_backend_version_mismatch", "proof_generator_fixture_allowlist"],
        )
        self.assertEqual(row["blockers"][1]["proof_backend_version"], "stwo-phase10-linear-block-v5-renamed")

    def test_classifier_rejects_backend_version_drift_on_matched_shape(self) -> None:
        current = {
            "proof_backend_version": "corrupt-version",
            "claim_transformer_config": {"d_model": 64},
            "block_logical_width": 64,
            "claim_mul_memory_ops": 49_152,
            "fixture_gate": {"fixture_gate_detected": False},
        }

        row = PROBE.classify_target(current, PROBE.matched_target(64))

        self.assertEqual(row["status"], "NO_GO_CURRENT_SURFACE")
        self.assertEqual([blocker["id"] for blocker in row["blockers"]], ["proof_backend_version_mismatch"])
        self.assertEqual(PROBE.decision_for_rows([row]), PROBE.DECISION_NO_GO)

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        payload = {
            "schema": PROBE.SCHEMA,
            "rows": [
                PROBE.classify_target(
                    {
                        "proof_backend_version": PROBE.CURRENT_FIXTURE_PROOF_SYSTEM_VERSION,
                        "claim_transformer_config": {"d_model": 36},
                        "block_logical_width": 4,
                        "claim_mul_memory_ops": 7,
                        "fixture_gate": {"fixture_gate_detected": True},
                    },
                    PROBE.matched_target(64),
                )
            ],
        }

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "out.json"
            tsv_path = tmp / "out.tsv"
            PROBE.write_outputs(copy.deepcopy(payload), json_path, tsv_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], PROBE.SCHEMA)
            tsv = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv[0].split("\t"), list(PROBE.TSV_COLUMNS))
            self.assertEqual(tsv[1].split("\t")[0], "64")


if __name__ == "__main__":
    unittest.main()
