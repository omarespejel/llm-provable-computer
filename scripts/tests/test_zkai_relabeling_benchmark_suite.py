from __future__ import annotations

import builtins
import csv
import importlib.util
import io
import json
import os
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "scripts" / "zkai_relabeling_benchmark_suite.py"
SPEC = importlib.util.spec_from_file_location("zkai_relabeling_benchmark_suite", SUITE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load relabeling benchmark suite from {SUITE_PATH}")
SUITE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUITE)


class ZkAIRelabelingBenchmarkSuiteTests(unittest.TestCase):
    def _module_names_loaded_from(self, path: pathlib.Path) -> set[str]:
        resolved = path.resolve()
        names = set()
        for name, module in sys.modules.items():
            module_file = getattr(module, "__file__", None)
            if module_file is None:
                continue
            try:
                if pathlib.Path(module_file).resolve() == resolved:
                    names.add(name)
            except OSError:
                continue
        return names

    def _load_declarative_adapter_module(self):
        module_name = "zkai_declarative_receipt_adapter_independence_check"
        spec = importlib.util.spec_from_file_location(module_name, SUITE.DECLARATIVE_ADAPTER_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _install_fake_rust_adapter_payload(self, payload: object):
        original_run = SUITE.subprocess.run

        class FakeCompleted:
            returncode = 0
            stderr = ""
            stdout = json.dumps(payload)

        def fake_run(*_args, **_kwargs):
            return FakeCompleted()

        SUITE.subprocess.run = fake_run
        return original_run

    def _install_fake_rust_adapter_results(self, results: list[dict[str, object]]):
        return self._install_fake_rust_adapter_payload(
            {
                "schema": "agent-step-receipt-rust-verifier-adapter-v1",
                "results": results,
            }
        )

    def _install_fake_rust_adapter_output(self, case_ids: list[str]):
        return self._install_fake_rust_adapter_results(
            [
                {
                    "case_id": case_id,
                    "accepted": case_id == "baseline",
                    "error": "" if case_id == "baseline" else "mutated failed",
                }
                for case_id in case_ids
            ]
        )

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

    def test_declarative_policy_suite_rejects_all_mutations(self) -> None:
        payload = SUITE.run_suite("declarative-policy")

        self.assertEqual(payload["adapter"], "declarative-policy")
        self.assertTrue(payload["baseline_accepted"])
        self.assertEqual(payload["baseline_error"], "")
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(SUITE.HARNESS.mutation_cases()))
        self.assertTrue(all(case["rejected"] for case in payload["cases"]))
        self.assertIn(
            "declarative_policy_sha256",
            payload["repro"]["verifier"],
        )

    def test_declarative_policy_adapter_does_not_import_mutation_oracle(self) -> None:
        harness_path = SUITE.HARNESS_PATH.resolve()
        forbidden_module_names = {
            "agent_step_receipt_relabeling_harness",
            "agent_step_receipt_harness",
            "scripts.agent_step_receipt_relabeling_harness",
        }
        before_harness_modules = self._module_names_loaded_from(harness_path)
        before_names = set(sys.modules)
        original_spec_from_file_location = importlib.util.spec_from_file_location
        original_import = builtins.__import__

        def guarded_spec_from_file_location(name, location, *args, **kwargs):
            if location is not None:
                try:
                    location_path = pathlib.Path(location).resolve()
                except (OSError, TypeError):
                    location_path = None
                if location_path == harness_path:
                    raise AssertionError(f"adapter attempted to load mutation oracle file: {location}")
            return original_spec_from_file_location(name, location, *args, **kwargs)

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            from_items = tuple(fromlist or ())
            requested = {name}
            requested.update(str(part) for part in from_items)
            requested.update(f"{name}.{part}" for part in from_items)
            if requested & forbidden_module_names:
                raise AssertionError(f"adapter attempted to import mutation oracle module: {name}")
            for requested_name in requested:
                if requested_name in forbidden_module_names and requested_name in sys.modules:
                    raise AssertionError(f"adapter attempted to reuse mutation oracle module: {requested_name}")
            return original_import(name, globals, locals, fromlist, level)

        importlib.util.spec_from_file_location = guarded_spec_from_file_location
        builtins.__import__ = guarded_import
        try:
            module = self._load_declarative_adapter_module()
        finally:
            builtins.__import__ = original_import
            importlib.util.spec_from_file_location = original_spec_from_file_location

        loaded_names = set(sys.modules) - before_names
        after_harness_modules = self._module_names_loaded_from(harness_path)

        self.assertNotIn("agent_step_receipt_relabeling_harness", module.__dict__)
        self.assertNotIn("HARNESS", module.__dict__)
        for forbidden_name in forbidden_module_names:
            forbidden_module = sys.modules.get(forbidden_name)
            if forbidden_module is not None:
                self.assertFalse(
                    any(value is forbidden_module for value in module.__dict__.values()),
                    f"adapter bound forbidden module via alias: {forbidden_name}",
                )
        self.assertFalse(
            after_harness_modules - before_harness_modules,
            f"adapter loaded mutation oracle under alternate module names: "
            f"{sorted(after_harness_modules - before_harness_modules)}",
        )
        self.assertFalse(forbidden_module_names & loaded_names)

    def test_declarative_policy_rejects_self_consistent_non_string_receipt_field(self) -> None:
        adapter = self._load_declarative_adapter_module()
        policy = adapter.load_policy(SUITE.DECLARATIVE_POLICY_PATH)
        bundle = SUITE.HARNESS.build_valid_bundle()
        bundle["receipt"]["runtime_domain"] = {"not": "a-string"}
        for entry in bundle["evidence_manifest"]["entries"]:
            if entry["corresponding_receipt_field"] == "/runtime_domain":
                entry["commitment"] = SUITE.HARNESS.commitment_for(
                    {"field": "/runtime_domain", "value": bundle["receipt"]["runtime_domain"]},
                    "agent-step-receipt-v1.evidence-field-binding",
                )
        SUITE.HARNESS.recompute_manifest_commitments(bundle)

        with self.assertRaisesRegex(adapter.DeclarativeReceiptError, "/runtime_domain must be a string"):
            adapter.verify_bundle(policy, bundle)

    def test_payload_records_reproducibility_and_artifact_hashes(self) -> None:
        payload = SUITE.run_suite("python-reference", command=["suite", "--adapter", "python-reference"])

        self.assertEqual(payload["repro"]["command"], ["suite", "--adapter", "python-reference"])
        self.assertIn("git_commit", payload["repro"])
        self.assertEqual(payload["repro"]["verifier"]["receipt_version"], SUITE.HARNESS.RECEIPT_VERSION)
        self.assertRegex(payload["repro"]["verifier"]["declarative_policy_sha256"], r"^[0-9a-f]{64}$")
        artifact_bundle = payload["repro"]["artifacts"]
        self.assertEqual(artifact_bundle["schema"], "zkai-relabeling-artifact-bundle-v1")
        baseline_hash = artifact_bundle["baseline"]["sha256"]
        self.assertRegex(baseline_hash, r"^[0-9a-f]{64}$")
        self.assertEqual(artifact_bundle["baseline"]["artifact"], SUITE.HARNESS.build_valid_bundle())
        for case in payload["cases"]:
            self.assertEqual(case["baseline_artifact_sha256"], baseline_hash)
            self.assertRegex(case["mutated_artifact_sha256"], r"^[0-9a-f]{64}$")
            mutation_record = artifact_bundle["mutations"][case["mutation"]]
            self.assertEqual(mutation_record["case_id"], case["mutation"])
            self.assertEqual(mutation_record["sha256"], case["mutated_artifact_sha256"])
            self.assertIsInstance(mutation_record["artifact"], dict)

    def test_command_json_override_preserves_argv_vector(self) -> None:
        original = os.environ.get("ZKAI_RELABELING_BENCHMARK_COMMAND_JSON")
        os.environ["ZKAI_RELABELING_BENCHMARK_COMMAND_JSON"] = json.dumps(
            ["env", "CARGO_TARGET_DIR=target/agent-relabeling-bench", "python3.12", "suite.py"]
        )
        try:
            self.assertEqual(
                SUITE._canonical_command(["ignored"]),
                ["env", "CARGO_TARGET_DIR=target/agent-relabeling-bench", "python3.12", "suite.py"],
            )
        finally:
            if original is None:
                del os.environ["ZKAI_RELABELING_BENCHMARK_COMMAND_JSON"]
            else:
                os.environ["ZKAI_RELABELING_BENCHMARK_COMMAND_JSON"] = original

    def test_checked_evidence_uses_portable_repro_command(self) -> None:
        evidence_dir = ROOT / "docs" / "engineering" / "evidence"
        evidence_paths = sorted(evidence_dir.glob("zkai-relabeling-benchmark-suite*.json"))
        baseline_paths = [path for path in evidence_paths if "-declarative-policy-" not in path.name]
        declarative_paths = [path for path in evidence_paths if "-declarative-policy-" in path.name]
        self.assertGreaterEqual(len(baseline_paths), 1, "missing baseline suite evidence file")
        self.assertGreaterEqual(len(declarative_paths), 1, "missing declarative-policy evidence file")
        for path in evidence_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            command = payload["repro"]["command"]
            self.assertEqual(command[0], "env")
            self.assertIn("CARGO_TARGET_DIR=target/agent-relabeling-bench", command)
            self.assertTrue(any(part.startswith("ZKAI_RELABELING_BENCHMARK_GIT_COMMIT=") for part in command))
            self.assertIn("python3.12", command)
            self.assertNotIn("/opt/homebrew/bin/python3.12", command)

    def test_artifact_hashes_use_harness_canonicalizer(self) -> None:
        original_mutated_bundles = SUITE._mutated_bundles
        SUITE._mutated_bundles = lambda: {"bad_float": {"not_canonical": 1.0}}
        try:
            with self.assertRaisesRegex(SUITE.HARNESS.AgentReceiptError, "floating point"):
                SUITE._artifact_hashes()
        finally:
            SUITE._mutated_bundles = original_mutated_bundles

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
        original_run = self._install_fake_rust_adapter_output(["baseline"])
        try:
            with self.assertRaisesRegex(RuntimeError, "incomplete case coverage"):
                SUITE._run_rust_production()
        finally:
            SUITE.subprocess.run = original_run

    def test_rust_adapter_rejects_duplicate_case_ids(self) -> None:
        original_run = self._install_fake_rust_adapter_output(["baseline", "baseline"])
        try:
            with self.assertRaisesRegex(RuntimeError, "duplicate case_id"):
                SUITE._run_rust_production()
        finally:
            SUITE.subprocess.run = original_run

    def test_rust_adapter_rejects_extra_case_ids(self) -> None:
        case_ids = ["baseline", *sorted(SUITE._case_catalog()), "unexpected_extra"]
        original_run = self._install_fake_rust_adapter_output(case_ids)
        try:
            with self.assertRaisesRegex(RuntimeError, "extra=\\['unexpected_extra'\\]"):
                SUITE._run_rust_production()
        finally:
            SUITE.subprocess.run = original_run

    def test_rust_adapter_rejects_non_boolean_acceptance(self) -> None:
        original_run = self._install_fake_rust_adapter_results(
            [{"case_id": "baseline", "accepted": "false", "error": ""}]
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "malformed result row"):
                SUITE._run_rust_production()
        finally:
            SUITE.subprocess.run = original_run

    def test_rust_adapter_rejects_non_object_payload(self) -> None:
        original_run = self._install_fake_rust_adapter_payload([])
        try:
            with self.assertRaisesRegex(RuntimeError, "malformed payload"):
                SUITE._run_rust_production()
        finally:
            SUITE.subprocess.run = original_run

    def test_declarative_adapter_metadata_is_verified(self) -> None:
        case_ids = ["baseline", *sorted(SUITE._case_catalog())]
        payload = {
            "schema": SUITE.DECLARATIVE_POLICY_ADAPTER_SCHEMA,
            "policy_path": str(SUITE.DECLARATIVE_POLICY_PATH.relative_to(SUITE.ROOT)),
            "policy_sha256": "0" * 64,
            "results": [
                {
                    "case_id": case_id,
                    "accepted": case_id == "baseline",
                    "error": "" if case_id == "baseline" else "mutated failed",
                }
                for case_id in case_ids
            ],
        }
        original_run = self._install_fake_rust_adapter_payload(payload)
        try:
            with self.assertRaisesRegex(RuntimeError, "metadata mismatch for policy_sha256"):
                SUITE._run_declarative_policy()
        finally:
            SUITE.subprocess.run = original_run

    def test_rejection_layers_distinguish_binding_and_policy_failures(self) -> None:
        payload = SUITE.run_suite("python-reference")
        layers = {case["mutation"]: case["rejection_layer"] for case in payload["cases"]}

        self.assertEqual(layers["model_id"], "cryptographic_binding")
        self.assertEqual(layers["dependency_drop_manifest"], "cryptographic_binding")
        self.assertEqual(layers["verifier_domain_separator"], "domain_or_version_allowlist")
        self.assertEqual(layers["trust_class_upgrade_without_proof"], "trust_policy")
        self.assertEqual(
            SUITE._classify_rejection("invalid commitment encoding"),
            "parser_or_schema_validation",
        )
        self.assertEqual(
            SUITE._classify_rejection("dependency_drop_manifest_commitment mismatch"),
            "cryptographic_binding",
        )

    def test_tsv_output_has_stable_public_columns(self) -> None:
        payload = SUITE.run_suite("python-reference")
        rows = list(csv.DictReader(io.StringIO(SUITE.to_tsv(payload)), delimiter="\t"))

        self.assertEqual(list(rows[0].keys()), SUITE.TSV_COLUMNS)
        self.assertEqual(len(rows), payload["case_count"])
        self.assertIn("model_identity_relabeling", {row["category"] for row in rows})


if __name__ == "__main__":
    unittest.main()
