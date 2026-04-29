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
BENCHMARK_PATH = ROOT / "scripts" / "zkai_snarkjs_statement_envelope_benchmark.py"
SPEC = importlib.util.spec_from_file_location("zkai_snarkjs_statement_envelope_benchmark", BENCHMARK_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load snarkjs benchmark from {BENCHMARK_PATH}")
BENCH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BENCH
SPEC.loader.exec_module(BENCH)


def fake_external_verify(_proof, public_signals, _verification_key):
    if public_signals[0] == "50":
        raise BENCH.SnarkjsEnvelopeError("snarkjs groth16 verifier rejected mutated public signal")


def valid_pass_payload():
    cases = []
    for adapter in BENCH.EXPECTED_ADAPTERS:
        for mutation in BENCH.EXPECTED_MUTATION_NAMES:
            rejected = adapter == "snarkjs-statement-envelope" or mutation == "public_signal_relabeling"
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


class ZkAISnarkjsStatementEnvelopeBenchmarkTests(unittest.TestCase):
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

        with self.assertRaisesRegex(BENCH.SnarkjsEnvelopeError, "statement policy mismatch"):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_delegates_public_signal_mutation_to_external_verifier(self) -> None:
        _category, envelope = BENCH.mutated_envelopes()["public_signal_relabeling"]

        with self.assertRaisesRegex(BENCH.SnarkjsEnvelopeError, "snarkjs groth16 verifier rejected"):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_rejects_inline_verification_key_swap(self) -> None:
        envelope = BENCH.baseline_envelope()
        envelope["verification_key"]["protocol"] = "tampered-groth16"
        envelope["statement"]["verification_key_sha256"] = BENCH.verification_key_sha256(
            envelope["verification_key"]
        )
        BENCH._refresh_statement_commitment(envelope)

        with self.assertRaisesRegex(
            BENCH.SnarkjsEnvelopeError,
            "verification-key object does not match verification-key artifact",
        ):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_rejects_missing_artifact_reference_fail_closed(self) -> None:
        envelope = BENCH.baseline_envelope()
        del envelope["artifacts"]["verification_key_path"]

        with self.assertRaisesRegex(
            BENCH.SnarkjsEnvelopeError,
            "artifacts.verification_key_path must be a non-empty string",
        ):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_statement_envelope_rejects_missing_setup_commitment_fail_closed(self) -> None:
        envelope = BENCH.baseline_envelope()
        del envelope["statement"]["setup_commitment"]
        BENCH._refresh_statement_commitment(envelope)

        with self.assertRaisesRegex(
            BENCH.SnarkjsEnvelopeError,
            "setup commitment must be explicitly null",
        ):
            BENCH.verify_statement_envelope(envelope, external_verify=fake_external_verify)

    def test_proof_only_rejects_malformed_payload_fail_closed(self) -> None:
        envelope = BENCH.baseline_envelope()
        envelope["public_signals"] = {"not": "a list"}

        with self.assertRaisesRegex(BENCH.SnarkjsEnvelopeError, "public_signals must be a list"):
            BENCH.verify_proof_only(envelope, external_verify=fake_external_verify)

    def test_public_signal_mutation_rejects_malformed_shape(self) -> None:
        with self.assertRaisesRegex(BENCH.SnarkjsEnvelopeError, "non-empty first public signal"):
            BENCH.mutate_first_public_signal([])

    def test_snarkjs_verify_times_out_fail_closed(self) -> None:
        with mock.patch.object(
            BENCH.subprocess,
            "run",
            side_effect=BENCH.subprocess.TimeoutExpired(cmd=["snarkjs"], timeout=60),
        ):
            with self.assertRaisesRegex(BENCH.SnarkjsEnvelopeError, "timed out"):
                BENCH.snarkjs_verify({}, [], {})

    def test_case_result_propagates_harness_bugs(self) -> None:
        def buggy_verify(_envelope, *, external_verify):  # noqa: ARG001
            raise KeyError("harness bug")

        with mock.patch.object(BENCH, "verify_statement_envelope", side_effect=buggy_verify):
            with self.assertRaises(KeyError):
                BENCH._case_result(
                    "snarkjs-statement-envelope",
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
            if case["adapter"] == "snarkjs-statement-envelope" and case["mutation"] == "model_id_relabeling":
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
            if item["adapter"] == "snarkjs-statement-envelope"
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
            if case["adapter"] == "snarkjs-statement-envelope":
                case["baseline_accepted"] = False
        payload["summary"] = BENCH.summarize_cases(payload["cases"])
        with mock.patch.object(BENCH, "run_benchmark", return_value=payload):
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(BENCH.main(["--json"]), 1)

    def test_tsv_columns_are_stable(self) -> None:
        payload = {
            "cases": [
                {
                    "adapter": "snarkjs-proof-only",
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
        original = os.environ.get("ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON")
        os.environ["ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON"] = json.dumps(
            ["env", "python3", "scripts/zkai_snarkjs_statement_envelope_benchmark.py"]
        )
        try:
            self.assertEqual(
                BENCH._canonical_command(["ignored"]),
                ["env", "python3", "scripts/zkai_snarkjs_statement_envelope_benchmark.py"],
            )
        finally:
            if original is None:
                del os.environ["ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON"]
            else:
                os.environ["ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON"] = original

    def test_command_json_override_rejects_malformed_json(self) -> None:
        original = os.environ.get("ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON")
        os.environ["ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON"] = "{"
        try:
            with self.assertRaisesRegex(RuntimeError, "valid JSON array of strings"):
                BENCH._canonical_command(["ignored"])
        finally:
            if original is None:
                del os.environ["ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON"]
            else:
                os.environ["ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON"] = original

    def test_checked_evidence_uses_portable_repro_command(self) -> None:
        path = (
            ROOT
            / "docs"
            / "engineering"
            / "evidence"
            / "zkai-snarkjs-statement-envelope-benchmark-2026-04.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        command = payload["repro"]["command"]

        self.assertEqual(command[0], "env")
        self.assertTrue(any(part.startswith("ZKAI_SNARKJS_BENCHMARK_GIT_COMMIT=") for part in command))
        self.assertIn("python3", command)

    def test_ansi_escape_sanitizer_keeps_evidence_machine_readable(self) -> None:
        self.assertEqual(
            BENCH.ANSI_ESCAPE_RE.sub("", "\x1b[31;22m[ERROR]\x1b[39;1msnarkJS\x1b[0m"),
            "[ERROR]snarkJS",
        )


if __name__ == "__main__":
    unittest.main()
