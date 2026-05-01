from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_external_adapter_surface_probe.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_external_adapter_surface_probe", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load external adapter probe from {SCRIPT_PATH}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class ZkAID64ExternalAdapterSurfaceProbeTests(unittest.TestCase):
    def test_probe_records_no_go_for_exact_vanilla_export(self) -> None:
        payload = PROBE.build_probe(module_overrides={}, cli_overrides={})
        PROBE.validate_probe(payload)

        self.assertEqual(payload["decision"], PROBE.DECISION)
        self.assertEqual(payload["conclusion"]["exact_vanilla_external_export"], "NO_GO")
        rows = {row["candidate_adapter"]: row for row in payload["candidate_adapters"]}
        self.assertEqual(rows["vanilla_onnx_ezkl_exact_export"]["gate"], "NO_GO")
        self.assertFalse(rows["vanilla_onnx_ezkl_exact_export"]["proof_generated"])
        self.assertIn(
            "signed_q8_integer_arithmetic",
            rows["vanilla_onnx_ezkl_exact_export"]["required_custom_semantics"],
        )
        self.assertIn("floor_division_rounding", rows["vanilla_onnx_ezkl_exact_export"]["required_custom_semantics"])
        self.assertIn("integer_square_root", rows["vanilla_onnx_ezkl_exact_export"]["required_custom_semantics"])
        self.assertIn(
            "bounded_integer_silu_lookup",
            rows["vanilla_onnx_ezkl_exact_export"]["required_custom_semantics"],
        )
        self.assertIn(
            "statement_receipt_binding",
            rows["vanilla_onnx_ezkl_exact_export"]["required_custom_semantics"],
        )

    def test_probe_reuses_canonical_statement_fixture_without_overclaiming(self) -> None:
        payload = PROBE.build_probe()
        fixture = PROBE.FIXTURE.build_fixture()

        self.assertEqual(
            payload["source_fixture"]["statement_commitment"],
            fixture["statement"]["statement_commitment"],
        )
        self.assertEqual(payload["source_fixture"]["proof_status"], "REFERENCE_FIXTURE_NOT_PROVEN")
        self.assertEqual(payload["source_fixture"]["mutation_suite"]["mutations_rejected"], 14)
        self.assertIn("not evidence that the d64 statement is proven", payload["non_claims"])

    def test_dependency_probe_can_be_injected_for_reproducible_tests(self) -> None:
        deps = PROBE.dependency_probe(
            module_overrides={"onnx": True, "onnxruntime": True, "numpy": True, "torch": True, "ezkl": True},
            cli_overrides={"ezkl": True},
        )

        self.assertTrue(deps["python_modules"]["onnx"])
        self.assertTrue(deps["python_modules"]["torch"])
        self.assertTrue(deps["cli_tools"]["ezkl"])
        self.assertTrue(deps["all_vanilla_external_runtime_present"])
        self.assertEqual(deps["mode"], "declared_requirements_with_overrides")

        missing_torch = PROBE.dependency_probe(
            module_overrides={"onnx": True, "onnxruntime": True, "numpy": True, "torch": False, "ezkl": True},
            cli_overrides={"ezkl": True},
        )
        self.assertFalse(missing_torch["all_vanilla_external_runtime_present"])

    def test_default_dependency_probe_is_reproducible_and_host_free(self) -> None:
        deps = PROBE.dependency_probe()

        self.assertEqual(deps["mode"], "declared_requirements_only")
        self.assertEqual(deps["python_modules"]["onnx"], "not_recorded")
        self.assertEqual(deps["cli_tools"]["ezkl"], "not_recorded")
        self.assertEqual(deps["all_vanilla_external_runtime_present"], "not_recorded")

    def test_git_commit_override_is_normalized(self) -> None:
        override = "  " + ("ABCDEF" * 6) + "ABCD  "
        with mock.patch.dict(os.environ, {"ZKAI_D64_EXTERNAL_ADAPTER_PROBE_GIT_COMMIT": override}):
            self.assertEqual(PROBE._git_commit(), ("abcdef" * 6) + "abcd")

    def test_validation_rejects_dependency_probe_drift(self) -> None:
        payload = PROBE.build_probe()
        payload["dependency_probe"]["all_vanilla_external_runtime_present"] = True

        with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "dependency probe drift"):
            PROBE.validate_probe(payload)

    def test_float_approximation_is_not_same_statement(self) -> None:
        reference = PROBE.FIXTURE.evaluate_reference_block()
        drift = PROBE.float_drift_summary(reference)

        self.assertEqual(drift["changed_output_positions"], 61)
        self.assertEqual(drift["max_abs_output_delta_q8"], 10)
        self.assertEqual(drift["exact_output_sha256"], PROBE.EXPECTED_EXACT_OUTPUT_SHA256)
        self.assertEqual(drift["float_like_output_sha256"], PROBE.EXPECTED_FLOAT_LIKE_OUTPUT_SHA256)
        self.assertNotEqual(drift["exact_output_sha256"], drift["float_like_output_sha256"])

    def test_rows_for_tsv_are_stable_and_scoped(self) -> None:
        payload = PROBE.build_probe()
        rows = PROBE.rows_for_tsv(payload)

        self.assertEqual(len(rows), 5)
        first = rows[0]
        self.assertEqual(first["candidate_adapter"], "vanilla_onnx_ezkl_exact_export")
        self.assertEqual(first["gate"], "NO_GO")
        self.assertEqual(first["same_statement_proof_claim"], "NO_GO")
        self.assertEqual(first["proof_generated"], "false")
        self.assertEqual(first["width"], 64)
        self.assertEqual(first["ff_dim"], 256)
        self.assertEqual(first["projection_weight_scalars"], 49_152)
        self.assertEqual(first["total_committed_parameter_scalars"], 49_216)

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        payload = PROBE.build_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "probe.json"
            tsv_path = tmp / "probe.tsv"
            PROBE.write_outputs(payload, json_path, tsv_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], PROBE.SCHEMA)
            tsv_lines = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv_lines[0].split("\t"), list(PROBE.TSV_COLUMNS))
            self.assertIn("vanilla_onnx_ezkl_exact_export", tsv_lines[1])

    def test_validation_rejects_stale_semantic_requirements(self) -> None:
        payload = PROBE.build_probe()
        payload["exact_semantic_requirements"] = [
            item for item in payload["exact_semantic_requirements"] if item["requirement"] != "integer_square_root"
        ]
        payload["exact_semantic_requirements_commitment"] = PROBE.blake2b_commitment(
            payload["exact_semantic_requirements"], "ptvm:zkai:d64-external-adapter-requirements:v1"
        )

        with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "semantic requirements drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_proof_generation_overclaim(self) -> None:
        payload = PROBE.build_probe()
        payload["candidate_adapters"][0]["proof_generated"] = True
        payload["candidate_matrix_commitment"] = PROBE.blake2b_commitment(
            payload["candidate_adapters"], "ptvm:zkai:d64-external-adapter-candidates:v1"
        )

        with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "candidate adapter matrix drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_stale_source_statement_commitment(self) -> None:
        payload = PROBE.build_probe()
        payload["source_fixture"]["statement_commitment"] = "blake2b-256:" + "00" * 32

        with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "source fixture drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_float_drift_canary_erasure(self) -> None:
        payload = PROBE.build_probe()
        payload["float_drift_summary"]["changed_output_positions"] = 0

        with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "float drift summary drift"):
            PROBE.validate_probe(payload)

    def test_write_outputs_wraps_os_errors(self) -> None:
        payload = PROBE.build_probe()
        with mock.patch.object(pathlib.Path, "write_text", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "failed to write"):
                PROBE.write_outputs(payload, pathlib.Path("/tmp/probe.json"), None)

    def test_candidate_matrix_commitment_rejects_silent_candidate_drift(self) -> None:
        payload = PROBE.build_probe()
        payload["candidate_adapters"][0]["gate"] = "GO"

        with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "candidate adapter matrix drift"):
            PROBE.validate_probe(payload)

    def test_validation_rejects_claim_boundary_drift(self) -> None:
        payload = PROBE.build_probe()
        payload["conclusion"]["statement_receipt_reuse"] = "GO"

        with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "conclusion drift"):
            PROBE.validate_probe(payload)

        payload = PROBE.build_probe()
        payload["non_claims"][0] = "not a caveat anymore"

        with self.assertRaisesRegex(PROBE.D64ExternalAdapterProbeError, "non-claims drift"):
            PROBE.validate_probe(payload)


if __name__ == "__main__":
    unittest.main()
