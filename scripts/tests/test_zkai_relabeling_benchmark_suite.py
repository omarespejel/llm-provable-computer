from __future__ import annotations

import csv
import importlib.util
import io
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "scripts" / "zkai_relabeling_benchmark_suite.py"
SPEC = importlib.util.spec_from_file_location("zkai_relabeling_benchmark_suite", SUITE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load relabeling benchmark suite from {SUITE_PATH}")
SUITE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUITE)


class ZkAIRelabelingBenchmarkSuiteTests(unittest.TestCase):
    def test_catalog_covers_every_declared_mutation_case(self) -> None:
        cases = set(SUITE.HARNESS.mutation_cases())
        catalog = set(SUITE.MUTATION_CATALOG)

        self.assertEqual(cases, catalog)

    def test_required_public_categories_are_present(self) -> None:
        categories = {metadata["category"] for metadata in SUITE.MUTATION_CATALOG.values()}

        self.assertTrue(
            {
                "model_identity_relabeling",
                "model_weights_relabeling",
                "input_context_relabeling",
                "output_action_relabeling",
                "model_config_relabeling",
                "policy_relabeling",
                "tool_output_relabeling",
                "prior_state_relabeling",
                "next_state_relabeling",
                "proof_system_version_relabeling",
                "verifier_domain_relabeling",
                "dependency_manifest_relabeling",
                "evidence_manifest_relabeling",
                "trust_class_upgrade_relabeling",
            }.issubset(categories)
        )

    def test_python_reference_suite_rejects_all_mutations(self) -> None:
        payload = SUITE.run_suite("python-reference")

        self.assertEqual(payload["schema"], "zkai-relabeling-benchmark-suite-v1")
        self.assertTrue(payload["baseline_accepted"])
        self.assertEqual(payload["baseline_error"], "")
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(SUITE.HARNESS.mutation_cases()))
        self.assertTrue(all(case["rejected"] for case in payload["cases"]))

    def test_payload_records_reproducibility_and_artifact_hashes(self) -> None:
        payload = SUITE.run_suite("python-reference", command=["suite", "--adapter", "python-reference"])

        self.assertEqual(payload["repro"]["command"], ["suite", "--adapter", "python-reference"])
        self.assertIn("git_commit", payload["repro"])
        self.assertEqual(payload["repro"]["verifier"]["receipt_version"], SUITE.HARNESS.RECEIPT_VERSION)
        baseline_hash = payload["repro"]["artifacts"]["baseline"]["sha256"]
        self.assertRegex(baseline_hash, r"^[0-9a-f]{64}$")
        for case in payload["cases"]:
            self.assertEqual(case["baseline_artifact_sha256"], baseline_hash)
            self.assertRegex(case["mutated_artifact_sha256"], r"^[0-9a-f]{64}$")

    def test_baseline_failure_is_reported_as_structured_payload(self) -> None:
        original = SUITE._python_verify
        calls = {"count": 0}

        def fake_verify(_bundle):
            calls["count"] += 1
            if calls["count"] == 1:
                return False, "baseline failed"
            return False, "mutated failed"

        SUITE._python_verify = fake_verify
        try:
            payload = SUITE.run_suite("python-reference")
        finally:
            SUITE._python_verify = original

        self.assertFalse(payload["baseline_accepted"])
        self.assertEqual(payload["baseline_error"], "baseline failed")
        self.assertTrue(all(case["rejected"] for case in payload["cases"]))

    def test_rust_adapter_requires_exact_case_coverage(self) -> None:
        original_run = SUITE.subprocess.run

        class FakeCompleted:
            returncode = 0
            stderr = ""
            stdout = (
                '{"schema":"agent-step-receipt-rust-verifier-adapter-v1",'
                '"results":[{"case_id":"baseline","accepted":true,"error":""}]}'
            )

        def fake_run(*_args, **_kwargs):
            return FakeCompleted()

        SUITE.subprocess.run = fake_run
        try:
            with self.assertRaisesRegex(RuntimeError, "incomplete case coverage"):
                SUITE._run_rust_production()
        finally:
            SUITE.subprocess.run = original_run

    def test_rejection_layers_distinguish_binding_and_policy_failures(self) -> None:
        payload = SUITE.run_suite("python-reference")
        layers = {case["mutation"]: case["rejection_layer"] for case in payload["cases"]}

        self.assertEqual(layers["model_id"], "cryptographic_binding")
        self.assertEqual(layers["dependency_drop_manifest"], "cryptographic_binding")
        self.assertEqual(layers["verifier_domain_separator"], "domain_or_version_allowlist")
        self.assertEqual(layers["trust_class_upgrade_without_proof"], "trust_policy")

    def test_tsv_output_has_stable_public_columns(self) -> None:
        payload = SUITE.run_suite("python-reference")
        rows = list(csv.DictReader(io.StringIO(SUITE.to_tsv(payload)), delimiter="\t"))

        self.assertEqual(list(rows[0].keys()), SUITE.TSV_COLUMNS)
        self.assertEqual(len(rows), payload["case_count"])
        self.assertIn("model_identity_relabeling", {row["category"] for row in rows})


if __name__ == "__main__":
    unittest.main()
