from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_deepprove_nanozk_adapter_feasibility.py"
SPEC = importlib.util.spec_from_file_location("zkai_deepprove_nanozk_adapter_feasibility", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load adapter feasibility probe from {SCRIPT_PATH}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class ZkAIDeepProveNanoZKAdapterFeasibilityTests(unittest.TestCase):
    def test_probe_records_no_go_for_public_relabeling_adapter(self) -> None:
        payload = PROBE.build_probe()
        PROBE.validate_probe(payload)

        self.assertEqual(payload["decision"], PROBE.DECISION)
        self.assertEqual(payload["conclusion"]["benchmark_result"], "NOT_RUN")
        systems = {system["system"]: system for system in payload["systems"]}
        self.assertEqual(
            systems["DeepProve-1"]["adapter_gate"],
            "NO_GO_PUBLIC_GPT2_ARTIFACT_NOT_REPRODUCIBLE",
        )
        self.assertEqual(
            systems["NANOZK"]["adapter_gate"],
            "NO_GO_NO_PUBLIC_VERIFIER_OR_PROOF_ARTIFACT",
        )
        self.assertFalse(systems["DeepProve-1"]["public_proof_artifact_available"])
        self.assertFalse(systems["NANOZK"]["public_proof_artifact_available"])
        self.assertFalse(systems["DeepProve-1"]["relabeling_benchmark_run"])
        self.assertFalse(systems["NANOZK"]["relabeling_benchmark_run"])

    def test_probe_records_exact_source_handles_without_turning_them_into_adapter_rows(self) -> None:
        payload = PROBE.build_probe()
        systems = {system["system"]: system for system in payload["systems"]}

        self.assertEqual(
            systems["DeepProve-1"]["source_inspection"]["checked_commit"],
            PROBE.DEEPPROVE_COMMIT,
        )
        self.assertEqual(
            systems["NANOZK"]["source_inspection"]["source_sha256"],
            PROBE.NANOZK_ARXIV_SOURCE_SHA256,
        )
        self.assertEqual(
            payload["conclusion"]["paper_usage"],
            "source_backed_context_only_not_empirical_adapter_row",
        )
        self.assertIn("not a DeepProve-1 soundness finding", payload["non_claims"])
        self.assertIn("not a NANOZK soundness finding", payload["non_claims"])

    def test_validation_rejects_benchmark_overclaims(self) -> None:
        payload = PROBE.build_probe()
        payload["systems"][0]["relabeling_benchmark_run"] = True
        payload["systems_commitment"] = PROBE.blake2b_commitment(
            payload["systems"], "ptvm:zkai:external-adapter-systems:v1"
        )

        with self.assertRaisesRegex(PROBE.AdapterFeasibilityError, "benchmark-run overclaim"):
            PROBE.validate_probe(payload)


    def test_validation_rejects_public_verifier_overclaims(self) -> None:
        payload = PROBE.build_probe()
        payload["systems"][0]["public_verifier_available"] = True
        payload["systems_commitment"] = PROBE.blake2b_commitment(
            payload["systems"], "ptvm:zkai:external-adapter-systems:v1"
        )

        with self.assertRaisesRegex(PROBE.AdapterFeasibilityError, "verifier availability overclaim"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_public_artifact_overclaims(self) -> None:
        payload = PROBE.build_probe()
        payload["systems"][1]["public_proof_artifact_available"] = True
        payload["systems_commitment"] = PROBE.blake2b_commitment(
            payload["systems"], "ptvm:zkai:external-adapter-systems:v1"
        )

        with self.assertRaisesRegex(PROBE.AdapterFeasibilityError, "public proof artifact overclaim"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_unknown_payload_fields(self) -> None:
        payload = PROBE.build_probe()
        payload["unreviewed_adapter_claim"] = "must not ride along"

        with self.assertRaisesRegex(PROBE.AdapterFeasibilityError, "payload field set mismatch"):
            PROBE.validate_probe(payload)

    def test_rows_for_tsv_are_stable(self) -> None:
        payload = PROBE.build_probe()
        rows = PROBE.rows_for_tsv(payload)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["system"], "DeepProve-1")
        self.assertEqual(rows[0]["relabeling_benchmark_run"], "false")
        self.assertEqual(rows[1]["system"], "NANOZK")
        self.assertEqual(rows[1]["baseline_verification_reproducible"], "false")

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "feasibility.json"
            tsv_path = tmp / "feasibility.tsv"
            PROBE.write_outputs(payload, json_path, tsv_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], PROBE.SCHEMA)
            tsv_lines = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv_lines[0].split("\t"), list(PROBE.TSV_COLUMNS))
            self.assertIn("DeepProve-1", tsv_lines[1])
            self.assertIn("NANOZK", tsv_lines[2])

    def test_write_outputs_wraps_os_errors(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            out_path = pathlib.Path(raw_tmp) / "feasibility.json"
            with (
                mock.patch.object(PROBE.tempfile, "NamedTemporaryFile", side_effect=OSError("disk full")),
                self.assertRaisesRegex(PROBE.AdapterFeasibilityError, "failed to write"),
            ):
                PROBE.write_json_output(payload, out_path)

    def test_write_outputs_rolls_back_json_if_tsv_replace_fails(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "feasibility.json"
            tsv_path = tmp / "feasibility.tsv"
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
                self.assertRaisesRegex(PROBE.AdapterFeasibilityError, "failed to write"),
            ):
                PROBE.write_outputs(payload, json_path, tsv_path)

            self.assertGreaterEqual(calls["count"], 2)
            self.assertEqual(json_path.read_text(encoding="utf-8"), "old-json\n")
            self.assertEqual(tsv_path.read_text(encoding="utf-8"), "old-tsv\n")

    def test_individual_writers_do_not_create_unrequested_formats(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "only.json"
            tsv_path = tmp / "only.tsv"

            PROBE.write_json_output(payload, json_path)
            self.assertTrue(json_path.exists())
            self.assertFalse(tsv_path.exists())

            PROBE.write_tsv_output(payload, tsv_path)
            self.assertTrue(tsv_path.exists())

    def test_git_commit_override_is_normalized(self) -> None:
        override = "  " + ("ABCDEF" * 6) + "ABCD  "
        with mock.patch.dict(os.environ, {"ZKAI_EXTERNAL_FEASIBILITY_GIT_COMMIT": override}):
            self.assertEqual(PROBE._git_commit(), ("abcdef" * 6) + "abcd")

    def test_git_commit_override_rejects_non_sha_text(self) -> None:
        with mock.patch.dict(os.environ, {"ZKAI_EXTERNAL_FEASIBILITY_GIT_COMMIT": "not-a-sha"}):
            with self.assertRaisesRegex(PROBE.AdapterFeasibilityError, "7-40 character hex SHA"):
                PROBE._git_commit()


if __name__ == "__main__":
    unittest.main()
