from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_proof_artifact_backend_spike_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_proof_artifact_backend_spike_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 backend spike gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128ProofArtifactBackendSpikeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_bounded_no_go_after_d64_anchor(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["issue"], 387)
        self.assertEqual(payload["summary"]["d64_anchor_route"], "GO_ANCHOR_ONLY")
        self.assertEqual(payload["summary"]["direct_d128_route"], "NO_GO")
        self.assertEqual(payload["summary"]["parameterized_route"], "NO_GO_FIRST_BLOCKER")
        self.assertEqual(payload["case_count"], 14)
        self.assertTrue(payload["all_mutations_rejected"])

    def test_target_matches_pinned_d128_comparator_shape(self) -> None:
        target = self.fresh_payload()["target"]
        self.assertEqual(target["target_id"], "rmsnorm-swiglu-residual-d128-v1")
        self.assertEqual(target["width"], 128)
        self.assertEqual(target["ff_dim"], 512)
        self.assertEqual(target["required_backend_version"], "stwo-rmsnorm-swiglu-residual-d128-v1")
        self.assertTrue(target["target_commitment"].startswith("blake2b-256:"))

    def test_d64_anchor_keeps_six_working_slices_but_not_d128(self) -> None:
        anchor = self.fresh_payload()["d64_anchor"]
        self.assertEqual(anchor["status"], "GO_ANCHOR_ONLY")
        self.assertEqual(anchor["slice_count"], 6)
        self.assertEqual(anchor["total_checked_rows"], 49600)
        self.assertIn("not a d128 proof route", anchor["claim_boundary"])
        self.assertEqual([row["slice"] for row in anchor["slices"]], [
            "rmsnorm_public_rows",
            "rmsnorm_projection_bridge",
            "gate_value_projection",
            "activation_swiglu",
            "down_projection",
            "residual_add",
        ])
        for row in anchor["slices"]:
            self.assertTrue(row["module"]["exists"])
            self.assertTrue(row["evidence"]["schema"].startswith("zkai-d64"))

    def test_source_probe_is_fail_closed_on_missing_d128_route(self) -> None:
        probe = self.fresh_payload()["source_probe"]
        self.assertEqual(probe["missing_d128_modules"], list(GATE.EXPECTED_D128_MODULES))
        self.assertEqual(probe["missing_d128_export_symbols"], list(GATE.EXPECTED_D128_EXPORT_SYMBOLS))
        self.assertEqual(probe["missing_parameterized_symbols"], list(GATE.PARAMETERIZED_SYMBOLS))
        self.assertEqual(len(probe["d64_hardcoded_markers"]), len(GATE.D64_HARDCODE_MARKERS))

    def test_backend_routes_block_metrics_until_proof_exists(self) -> None:
        routes = {row["route"]: row for row in self.fresh_payload()["backend_routes"]}
        self.assertEqual(routes["existing_d64_slice_chain"]["status"], "GO_ANCHOR_ONLY")
        self.assertEqual(routes["direct_d128_native_modules"]["status"], "NO_GO")
        self.assertEqual(routes["lift_existing_d64_modules_by_metadata"]["status"], "NO_GO")
        self.assertEqual(routes["parameterized_vector_block_air"]["status"], "NO_GO_FIRST_BLOCKER")
        self.assertEqual(routes["d128_metrics_and_relabeling_suite"]["status"], "NO_GO_BLOCKED_BEFORE_PROOF_OBJECT")
        for name, row in routes.items():
            self.assertIsNone(row["proof_size_bytes"], name)
            self.assertIsNone(row["verifier_time_ms"], name)

    def test_proof_status_records_toolchain_and_no_metrics(self) -> None:
        status = self.fresh_payload()["proof_status"]
        self.assertFalse(status["proof_artifact_exists"])
        self.assertFalse(status["verifier_handle_exists"])
        self.assertFalse(status["statement_relabeling_suite_exists"])
        self.assertTrue(status["blocked_before_metrics"])
        self.assertIsNone(status["proof_size_bytes"])
        self.assertIsNone(status["verifier_time_ms"])
        self.assertEqual(status["required_toolchain"], "nightly-2025-07-14")
        self.assertEqual(status["stable_toolchain_status"], "not_supported_by_upstream_stwo_feature_gates")

    def test_rejects_metric_smuggling(self) -> None:
        payload = self.fresh_payload()
        payload["proof_status"]["verifier_time_ms"] = 1.0
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "verifier time"):
            GATE.validate_payload(payload)

    def test_rejects_route_promotion(self) -> None:
        payload = self.fresh_payload()
        route = next(row for row in payload["backend_routes"] if row["route"] == "parameterized_vector_block_air")
        route["status"] = "GO"
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "parameterized route status"):
            GATE.validate_payload(payload)

    def test_rejects_removed_missing_module(self) -> None:
        payload = self.fresh_payload()
        payload["source_probe"]["missing_d128_modules"] = payload["source_probe"]["missing_d128_modules"][1:]
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "missing d128 module"):
            GATE.validate_payload(payload)

    def test_rejects_removed_non_claim(self) -> None:
        payload = self.fresh_payload()
        payload["non_claims"].remove("not a local d128 proof artifact")
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "non-claims"):
            GATE.validate_payload(payload)

    def test_mutation_layers_cover_routes_sources_and_metrics(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["decision_promoted_to_go"]["rejection_layer"], "top_level")
        self.assertEqual(cases["direct_d128_route_promoted"]["rejection_layer"], "backend_routes")
        self.assertEqual(cases["parameterized_route_promoted"]["rejection_layer"], "backend_routes")
        self.assertEqual(cases["missing_module_removed"]["rejection_layer"], "source_probe")
        self.assertEqual(cases["proof_size_metric_smuggled"]["rejection_layer"], "metrics")
        for case in cases.values():
            self.assertTrue(case["rejected"])
            self.assertFalse(case["mutated_accepted"])
            self.assertTrue(case["error"])

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "d128-backend-spike.json"
            tsv_path = tmp / "d128-backend-spike.tsv"
            GATE.write_outputs(payload, json_path, tsv_path)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), payload)
            tsv = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv[0].split("\t"), list(GATE.TSV_COLUMNS))
            self.assertIn("direct_d128_native_modules", tsv[2])
            self.assertEqual(tsv[7].split("\t"), list(GATE.MUTATION_TSV_COLUMNS))

    def test_write_outputs_rejects_paths_outside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "d128-backend-spike.json"
            tsv_path = tmp / "d128-backend-spike.tsv"
            with self.assertRaisesRegex(GATE.D128BackendSpikeError, "output path escapes repository"):
                GATE.write_outputs(payload, json_path, tsv_path)
            self.assertFalse(json_path.exists())
            self.assertFalse(tsv_path.exists())

    def test_write_outputs_fsyncs_parent_directory_after_replace(self) -> None:
        payload = self.fresh_payload()
        original = GATE._fsync_parent_directories
        synced: list[pathlib.Path] = []

        def record(paths: list[pathlib.Path]) -> None:
            synced.extend(paths)

        try:
            GATE._fsync_parent_directories = record
            with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
                tmp = pathlib.Path(raw_tmp)
                json_path = tmp / "d128-backend-spike.json"
                tsv_path = tmp / "d128-backend-spike.tsv"
                GATE.write_outputs(payload, json_path, tsv_path)
            self.assertEqual(synced, [json_path.resolve(), tsv_path.resolve()])
        finally:
            GATE._fsync_parent_directories = original


if __name__ == "__main__":
    unittest.main()
