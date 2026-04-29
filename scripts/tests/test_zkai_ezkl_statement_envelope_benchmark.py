from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest


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


if __name__ == "__main__":
    unittest.main()
