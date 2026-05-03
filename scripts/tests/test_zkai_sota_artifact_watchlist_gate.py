from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_sota_artifact_watchlist_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_sota_artifact_watchlist_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load SOTA watchlist gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class ZkAiSotaArtifactWatchlistGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_current_sota_classification_without_leaderboard(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)

        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["checked_at"], "2026-05-03")
        self.assertEqual(payload["issue"], "#419")
        self.assertEqual(payload["summary"]["system_count"], 12)
        self.assertEqual(payload["summary"]["empirical_adapter_rows"], ["EZKL", "snarkjs", "JSTprove/Remainder"])
        self.assertEqual(payload["summary"]["deployment_calibration_rows"], ["Obelyzk"])
        self.assertIn("not a leaderboard", payload["non_claims"])
        self.assertIn("#420", payload["summary"]["current_best_next_research_step"])

    def test_source_backed_systems_are_not_promoted_to_adapter_rows(self) -> None:
        systems = {row["system"]: row for row in self.fresh_payload()["systems"]}

        for name in ("DeepProve-1", "NANOZK", "Jolt Atlas", "Giza/LuminAIR"):
            row = systems[name]
            self.assertFalse(row["baseline_verification_reproducible"])
            self.assertFalse(row["metadata_mutation_reproducible"])
            self.assertNotEqual(row["status"], GATE.STATUS_EMPIRICAL)
        self.assertEqual(systems["NANOZK"]["status"], GATE.STATUS_COMPACT_CONTEXT)
        self.assertIn("not a matched local benchmark", systems["NANOZK"]["recommended_use"])
        self.assertEqual(systems["DeepProve-1"]["status"], GATE.STATUS_MODEL_SCALE_CONTEXT)

    def test_settlement_and_zkvm_rows_are_context_not_local_metrics(self) -> None:
        systems = {row["system"]: row for row in self.fresh_payload()["systems"]}

        self.assertEqual(systems["Obelyzk"]["status"], GATE.STATUS_DEPLOYMENT_CONTEXT)
        self.assertIn("not local verifier-time comparison", systems["Obelyzk"]["recommended_use"])
        self.assertEqual(systems["RISC Zero"]["status"], GATE.STATUS_ZKVM_WATCHLIST)
        self.assertEqual(systems["SP1"]["status"], GATE.STATUS_ZKVM_WATCHLIST)
        self.assertEqual(systems["SNIP-36"]["status"], GATE.STATUS_SETTLEMENT_WATCHLIST)
        self.assertIn("park until", systems["SNIP-36"]["recommended_use"])

    def test_mutation_inventory_rejects_every_overclaim_surface(self) -> None:
        payload = self.fresh_payload()
        cases = {case["mutation"]: case for case in payload["cases"]}

        self.assertEqual(payload["case_count"], 12)
        self.assertTrue(payload["all_mutations_rejected"])
        for mutation in (
            "deep_prove_promoted_to_empirical",
            "nanozk_matched_benchmark_overclaim",
            "jolt_baseline_verification_overclaim",
            "obelyzk_local_verifier_time_overclaim",
            "risc_zero_promoted_to_zkml_throughput",
            "snip36_promoted_to_local_deployment",
            "systems_commitment_stale_after_edit",
        ):
            self.assertTrue(cases[mutation]["rejected"], mutation)
            self.assertTrue(cases[mutation]["error"], mutation)

    def test_rejects_deepprove_empirical_promotion_after_recommit(self) -> None:
        payload = self.fresh_payload()
        row = next(row for row in payload["systems"] if row["system"] == "DeepProve-1")
        row.update(
            {
                "status": GATE.STATUS_EMPIRICAL,
                "public_proof_artifact_available": True,
                "public_verifier_input_available": True,
                "baseline_verification_reproducible": True,
                "metadata_mutation_reproducible": True,
                "recommended_use": "empirical adapter row",
            }
        )
        payload["systems_commitment"] = GATE.blake2b_commitment(
            payload["systems"], "ptvm:zkai:sota-artifact-watchlist:systems:v1"
        )
        payload["summary"] = GATE.summary_for_systems(payload["systems"])
        payload["summary"]["mutation_cases"] = payload["case_count"]
        payload["summary"]["mutations_rejected"] = payload["case_count"]

        with self.assertRaisesRegex(GATE.SotaWatchlistError, "unapproved empirical adapter promotion"):
            GATE.validate_payload(payload)

    def test_rejects_nanozk_matched_benchmark_language(self) -> None:
        payload = self.fresh_payload()
        row = next(row for row in payload["systems"] if row["system"] == "NANOZK")
        row["recommended_use"] = "matched local benchmark"
        payload["systems_commitment"] = GATE.blake2b_commitment(
            payload["systems"], "ptvm:zkai:sota-artifact-watchlist:systems:v1"
        )

        with self.assertRaisesRegex(GATE.SotaWatchlistError, "source-backed system promoted"):
            GATE.validate_payload(payload)

    def test_rejects_non_https_primary_source(self) -> None:
        payload = self.fresh_payload()
        row = next(row for row in payload["systems"] if row["system"] == "SP1")
        row["primary_source"] = "http://docs.succinct.xyz/"
        payload["systems_commitment"] = GATE.blake2b_commitment(
            payload["systems"], "ptvm:zkai:sota-artifact-watchlist:systems:v1"
        )

        with self.assertRaisesRegex(GATE.SotaWatchlistError, "primary source must be https"):
            GATE.validate_payload(payload)

    def test_rejects_stale_checked_at(self) -> None:
        payload = self.fresh_payload()
        row = next(row for row in payload["systems"] if row["system"] == "RISC Zero")
        row["checked_at"] = "2026-04-01"
        payload["systems_commitment"] = GATE.blake2b_commitment(
            payload["systems"], "ptvm:zkai:sota-artifact-watchlist:systems:v1"
        )

        with self.assertRaisesRegex(GATE.SotaWatchlistError, "checked_at drift"):
            GATE.validate_payload(payload)

    def test_rejects_stale_system_commitment(self) -> None:
        payload = self.fresh_payload()
        row = next(row for row in payload["systems"] if row["system"] == "DeepProve-1")
        row["next_action"] = "silently claim done"

        with self.assertRaisesRegex(GATE.SotaWatchlistError, "systems commitment mismatch"):
            GATE.validate_payload(payload)

    def test_tsv_rows_are_stable_and_make_boolean_status_explicit(self) -> None:
        rows = GATE.rows_for_tsv(self.fresh_payload())

        self.assertEqual([row["system"] for row in rows], GATE.REQUIRED_SYSTEM_ORDER)
        self.assertEqual(rows[0]["system"], "EZKL")
        self.assertEqual(rows[0]["baseline_verification_reproducible"], "true")
        self.assertEqual(rows[5]["system"], "NANOZK")
        self.assertEqual(rows[5]["metadata_mutation_reproducible"], "false")
        self.assertEqual(rows[-1]["system"], "SNIP-36")
        self.assertIn("proof_facts", rows[-1]["next_action"])

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "watchlist.json"
            tsv_path = tmp / "watchlist.tsv"
            GATE.write_outputs(payload, json_path, tsv_path)

            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["systems_commitment"], payload["systems_commitment"])
            tsv = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv[0].split("\t"), list(GATE.TSV_COLUMNS))
            self.assertIn("DeepProve-1", tsv[5])
            self.assertIn("SNIP-36", tsv[-1])

    def test_git_commit_override_is_normalized_and_validated(self) -> None:
        old = dict()
        key = "ZKAI_SOTA_WATCHLIST_GIT_COMMIT"
        if key in GATE.os.environ:
            old[key] = GATE.os.environ[key]
        try:
            GATE.os.environ[key] = "  ABCDEF123456  "
            self.assertEqual(GATE._git_commit(), "abcdef123456")
            GATE.os.environ[key] = "not-a-sha"
            with self.assertRaisesRegex(GATE.SotaWatchlistError, "7-40 character hex SHA"):
                GATE._git_commit()
        finally:
            if key in old:
                GATE.os.environ[key] = old[key]
            else:
                GATE.os.environ.pop(key, None)


if __name__ == "__main__":
    unittest.main()
