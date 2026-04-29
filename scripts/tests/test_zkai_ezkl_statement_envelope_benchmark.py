from __future__ import annotations

import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
BENCHMARK_PATH = ROOT / "scripts" / "zkai_ezkl_statement_envelope_benchmark.py"
SPEC = importlib.util.spec_from_file_location("zkai_ezkl_statement_envelope_benchmark", BENCHMARK_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load EZKL benchmark from {BENCHMARK_PATH}")
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)


def fake_external_verify(proof, _settings_path, _vk_path, _srs_path):
    if proof["instances"][0][0].startswith("7"):
        raise BENCH.EzklEnvelopeError("EZKL proof verifier rejected mutated public instance")


class ZkAIEzklStatementEnvelopeBenchmarkTests(unittest.TestCase):
    def test_baseline_statement_commitment_matches(self) -> None:
        envelope = BENCH.baseline_envelope()

        self.assertEqual(
            envelope["statement_commitment"],
            BENCH.statement_commitment(envelope["statement"]),
        )

    def test_raw_proof_only_accepts_metadata_relabeling_with_fake_verifier(self) -> None:
        _category, envelope = BENCH.mutated_envelopes()["model_id_relabeling"]

        BENCH.verify_proof_only(
            envelope,
            pathlib.Path("/tmp/nonexistent-srs-not-read-by-fake"),
            external_verify=fake_external_verify,
        )

    def test_statement_envelope_rejects_model_id_relabeling(self) -> None:
        _category, envelope = BENCH.mutated_envelopes()["model_id_relabeling"]

        with self.assertRaisesRegex(BENCH.EzklEnvelopeError, "statement policy mismatch"):
            BENCH.verify_statement_envelope(
                envelope,
                pathlib.Path("/tmp/nonexistent-srs-not-read-before-policy-failure"),
                external_verify=fake_external_verify,
            )

    def test_statement_envelope_delegates_public_instance_mutation_to_external_verifier(self) -> None:
        _category, envelope = BENCH.mutated_envelopes()["proof_public_instance_relabeling"]
        with tempfile.NamedTemporaryFile() as srs:
            pathlib.Path(srs.name).write_bytes(b"unit-test-srs")
            envelope["statement"]["srs_sha256"] = BENCH.sha256_file(pathlib.Path(srs.name))
            envelope["statement_commitment"] = BENCH.statement_commitment(envelope["statement"])

            with self.assertRaisesRegex(BENCH.EzklEnvelopeError, "EZKL proof verifier rejected"):
                BENCH.verify_statement_envelope(
                    envelope,
                    pathlib.Path(srs.name),
                    external_verify=fake_external_verify,
                )

    def test_ensure_srs_fails_fast_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            missing = pathlib.Path(raw_tmp) / "missing-kzg17.srs"
            with self.assertRaisesRegex(FileNotFoundError, "missing EZKL KZG SRS"):
                BENCH.ensure_srs(missing)

    def test_ezkl_verify_rejects_runtime_version_mismatch(self) -> None:
        original_ezkl = sys.modules.get("ezkl")
        sys.modules["ezkl"] = types.SimpleNamespace(verify=lambda *_args, **_kwargs: True)
        try:
            with mock.patch.object(BENCH.importlib.metadata, "version", return_value="0.0.0"):
                with self.assertRaisesRegex(BENCH.EzklEnvelopeError, "does not match expected"):
                    BENCH.ezkl_verify(
                        {"instances": [["1"]]},
                        pathlib.Path("settings.json"),
                        pathlib.Path("vk.key"),
                        pathlib.Path("srs"),
                    )
        finally:
            if original_ezkl is None:
                del sys.modules["ezkl"]
            else:
                sys.modules["ezkl"] = original_ezkl

    def test_main_fails_when_statement_envelope_baseline_is_rejected(self) -> None:
        payload = {
            "summary": {
                "ezkl-proof-only": {
                    "baseline_accepted": True,
                    "mutations_rejected": 1,
                    "mutation_count": 7,
                    "all_mutations_rejected": False,
                },
                "ezkl-statement-envelope": {
                    "baseline_accepted": False,
                    "mutations_rejected": 7,
                    "mutation_count": 7,
                    "all_mutations_rejected": True,
                },
            },
            "cases": [],
        }
        with mock.patch.object(BENCH, "run_benchmark", return_value=payload):
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(BENCH.main(["--json", "--srs-path", "unused"]), 1)

    def test_tsv_columns_are_stable(self) -> None:
        payload = {
            "cases": [
                {
                    "adapter": "ezkl-proof-only",
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

        self.assertEqual(
            BENCH.to_tsv(payload).splitlines()[0].split("\t"),
            BENCH.TSV_COLUMNS,
        )

    def test_command_json_override_preserves_portable_argv_vector(self) -> None:
        original = os.environ.get("ZKAI_EZKL_BENCHMARK_COMMAND_JSON")
        os.environ["ZKAI_EZKL_BENCHMARK_COMMAND_JSON"] = json.dumps(
            [
                "env",
                "ZKAI_EZKL_SRS_PATH=target/ezkl/kzg17.srs",
                "python3",
                "scripts/zkai_ezkl_statement_envelope_benchmark.py",
            ]
        )
        try:
            self.assertEqual(
                BENCH._canonical_command(["ignored"]),
                [
                    "env",
                    "ZKAI_EZKL_SRS_PATH=target/ezkl/kzg17.srs",
                    "python3",
                    "scripts/zkai_ezkl_statement_envelope_benchmark.py",
                ],
            )
        finally:
            if original is None:
                del os.environ["ZKAI_EZKL_BENCHMARK_COMMAND_JSON"]
            else:
                os.environ["ZKAI_EZKL_BENCHMARK_COMMAND_JSON"] = original

    def test_checked_evidence_uses_portable_repro_command(self) -> None:
        path = ROOT / "docs" / "engineering" / "evidence" / "zkai-ezkl-statement-envelope-benchmark-2026-04.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        command = payload["repro"]["command"]

        self.assertEqual(command[0], "env")
        self.assertTrue(any(part.startswith("ZKAI_EZKL_BENCHMARK_GIT_COMMIT=") for part in command))
        self.assertIn("ZKAI_EZKL_SRS_PATH=target/ezkl/kzg17.srs", command)
        self.assertIn("python3", command)


if __name__ == "__main__":
    unittest.main()
