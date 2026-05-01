from __future__ import annotations

import importlib.util
import io
import json
import os
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
BENCHMARK_PATH = ROOT / "scripts" / "zkai_jstprove_statement_envelope_benchmark.py"
SPEC = importlib.util.spec_from_file_location("zkai_jstprove_statement_envelope_benchmark", BENCHMARK_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load JSTprove benchmark from {BENCHMARK_PATH}")
BENCH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BENCH
SPEC.loader.exec_module(BENCH)


def fake_external_verify(envelope):
    baseline = BENCH.baseline_envelope()
    if BENCH.artifact_sha256(envelope, "input.msgpack") != BENCH.artifact_sha256(baseline, "input.msgpack"):
        raise BENCH.JstproveEnvelopeError("JSTprove Remainder verifier rejected mutated input artifact")


def valid_pass_payload():
    cases = []
    for adapter in BENCH.EXPECTED_ADAPTERS:
        for mutation in BENCH.EXPECTED_MUTATION_NAMES:
            rejected = adapter == "jstprove-statement-envelope" or mutation == "input_artifact_bytes_relabeling"
            cases.append(
                {
                    "adapter": adapter,
                    "mutation": mutation,
                    "category": "unit-test",
                    "baseline_accepted": True,
                    "baseline_error": "",
                    "mutated_accepted": not rejected,
                    "rejected": rejected,
                    "rejection_layer": "unit-test" if rejected else "accepted",
                    "error": "rejected" if rejected else "",
                }
            )
    return {"cases": cases, "summary": BENCH.summarize_cases(cases)}


class ZkAIJstproveStatementEnvelopeBenchmarkTests(unittest.TestCase):
    def test_baseline_statement_commitment_matches(self) -> None:
        envelope = BENCH.baseline_envelope()

        self.assertEqual(
            envelope["statement_commitment"],
            BENCH.statement_commitment(envelope["statement"]),
        )

    def test_raw_proof_only_accepts_metadata_relabeling_with_fake_verifier(self) -> None:
        _category, envelope = BENCH.mutated_envelopes()["model_id_relabeling"]

        BENCH.verify_proof_only(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_rejects_model_id_relabeling(self) -> None:
        _category, envelope = BENCH.mutated_envelopes()["model_id_relabeling"]

        with self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "statement policy mismatch"):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_delegates_input_artifact_mutation_to_external_verifier(self) -> None:
        _category, envelope = BENCH.mutated_envelopes()["input_artifact_bytes_relabeling"]

        with self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "JSTprove Remainder verifier rejected"):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_rejects_artifact_hash_relabeling(self) -> None:
        _category, envelope = BENCH.mutated_envelopes()["proof_hash_relabeling"]

        with self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "proof hash mismatch"):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_hashes_model_source_artifact_bytes(self) -> None:
        envelope = BENCH.baseline_envelope()
        original_sha256_file = BENCH.sha256_file

        def fake_source_hash(path):
            if pathlib.Path(path).name == BENCH.MODEL_SOURCE_ARTIFACT:
                return "ff" * 32
            return original_sha256_file(path)

        with (
            mock.patch.object(BENCH, "sha256_file", side_effect=fake_source_hash),
            self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "model source hash mismatch"),
        ):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_rejects_missing_setup_commitment_fail_closed(self) -> None:
        envelope = BENCH.baseline_envelope()
        del envelope["statement"]["setup_commitment"]
        BENCH._refresh_statement_commitment(envelope)

        with self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "setup commitment must be explicitly null"):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_proof_only_rejects_malformed_artifact_override_fail_closed(self) -> None:
        envelope = BENCH.baseline_envelope()
        envelope["artifact_overrides"] = {"input.msgpack": "not base64"}

        with self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "not valid base64"):
            BENCH.verify_proof_only(envelope, external_verify=fake_external_verify)

    def test_artifact_reference_rejects_path_escape(self) -> None:
        envelope = BENCH.baseline_envelope()
        envelope["artifacts"]["proof_path"] = "../proof.msgpack"

        with self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "not an allowed JSTprove artifact"):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_jstprove_verify_times_out_fail_closed(self) -> None:
        with mock.patch.object(BENCH.shutil, "which", return_value="/usr/bin/jstprove-remainder"):
            with mock.patch.object(
                BENCH.subprocess,
                "run",
                side_effect=BENCH.subprocess.TimeoutExpired(cmd=["jstprove-remainder"], timeout=180),
            ):
                with self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "timed out"):
                    BENCH.jstprove_verify(BENCH.baseline_envelope())

    def test_jstprove_verify_wraps_spawn_errors(self) -> None:
        with mock.patch.object(BENCH.shutil, "which", return_value="/usr/bin/jstprove-remainder"):
            with mock.patch.object(BENCH.subprocess, "run", side_effect=OSError("exec format error")):
                with self.assertRaisesRegex(BENCH.JstproveEnvelopeError, "failed to start"):
                    BENCH.jstprove_verify(BENCH.baseline_envelope())

    def test_case_result_propagates_harness_bugs(self) -> None:
        def buggy_verify(_envelope, *, external_verify):  # noqa: ARG001
            raise KeyError("harness bug")

        with mock.patch.object(BENCH, "verify_statement_envelope", side_effect=buggy_verify):
            with self.assertRaises(KeyError):
                BENCH._case_result(
                    "jstprove-statement-envelope",
                    BENCH.baseline_envelope(),
                    fake_external_verify,
                )

    def test_run_benchmark_rejects_truncated_mutation_corpus(self) -> None:
        original = BENCH.mutated_envelopes

        def truncated():
            data = original()
            data.pop("model_id_relabeling")
            return data

        with mock.patch.object(BENCH, "mutated_envelopes", side_effect=truncated):
            with self.assertRaisesRegex(RuntimeError, "mutation corpus"):
                BENCH.run_benchmark(external_verify=fake_external_verify)

    def test_benchmark_pass_accepts_expected_differential_result(self) -> None:
        self.assertTrue(BENCH.benchmark_passed(valid_pass_payload()))

    def test_benchmark_pass_uses_raw_cases_not_forged_summary(self) -> None:
        payload = valid_pass_payload()
        for case in payload["cases"]:
            if case["adapter"] == "jstprove-statement-envelope" and case["mutation"] == "model_id_relabeling":
                case["rejected"] = False
                case["mutated_accepted"] = True
                case["rejection_layer"] = "accepted"
                case["error"] = ""
                break

        self.assertFalse(BENCH.benchmark_passed(payload))

    def test_benchmark_records_inspectable_mutation_payload_digests(self) -> None:
        payload = BENCH.run_benchmark(external_verify=fake_external_verify)
        case = next(
            item
            for item in payload["cases"]
            if item["adapter"] == "jstprove-statement-envelope"
            and item["mutation"] == "model_id_relabeling"
        )

        self.assertIn("baseline_statement", case)
        self.assertIn("mutated_statement", case)
        self.assertNotEqual(case["baseline_statement"], case["mutated_statement"])
        self.assertEqual(
            case["mutated_statement_sha256"],
            BENCH.sha256_bytes(BENCH.canonical_json_bytes(case["mutated_statement"])),
        )

    def test_main_fails_when_statement_envelope_baseline_is_rejected(self) -> None:
        payload = valid_pass_payload()
        for case in payload["cases"]:
            if case["adapter"] == "jstprove-statement-envelope":
                case["baseline_accepted"] = False
        payload["summary"] = BENCH.summarize_cases(payload["cases"])
        with mock.patch.object(BENCH, "run_benchmark", return_value=payload):
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(BENCH.main(["--json"]), 1)

    def test_tsv_columns_are_stable(self) -> None:
        payload = {
            "cases": [
                {
                    "adapter": "jstprove-proof-only",
                    "mutation": "model_id_relabeling",
                    "category": "statement_policy",
                    "baseline_accepted": True,
                    "mutated_accepted": True,
                    "rejected": False,
                    "rejection_layer": "accepted",
                    "error": "",
                }
            ]
        }

        self.assertEqual(BENCH.to_tsv(payload).splitlines()[0].split("\t"), BENCH.TSV_COLUMNS)

    def test_command_json_override_preserves_portable_argv_vector(self) -> None:
        original = os.environ.get("ZKAI_JSTPROVE_BENCHMARK_COMMAND_JSON")
        os.environ["ZKAI_JSTPROVE_BENCHMARK_COMMAND_JSON"] = json.dumps(
            ["env", "python3", "scripts/zkai_jstprove_statement_envelope_benchmark.py"]
        )
        try:
            self.assertEqual(
                BENCH._canonical_command(["ignored"]),
                ["env", "python3", "scripts/zkai_jstprove_statement_envelope_benchmark.py"],
            )
        finally:
            if original is None:
                del os.environ["ZKAI_JSTPROVE_BENCHMARK_COMMAND_JSON"]
            else:
                os.environ["ZKAI_JSTPROVE_BENCHMARK_COMMAND_JSON"] = original

    def test_git_commit_override_rejects_non_sha_text(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "7-40 character hex SHA"):
            BENCH._validated_git_commit("not-a-sha")

    def test_individual_writers_do_not_create_unrequested_formats(self) -> None:
        import tempfile

        payload = valid_pass_payload()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_json = pathlib.Path(tmp_dir) / "result.json"
            out_tsv = pathlib.Path(tmp_dir) / "result.tsv"
            with mock.patch.object(BENCH, "run_benchmark", return_value=payload):
                self.assertEqual(BENCH.main(["--write-json", str(out_json)]), 0)
            self.assertTrue(out_json.exists())
            self.assertFalse(out_tsv.exists())


if __name__ == "__main__":
    unittest.main()
