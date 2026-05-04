from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_cryptographic_backend_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_cryptographic_backend_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 cryptographic-backend gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class ZkAiD128CryptographicBackendGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_external_snark_go_over_proof_native_contract(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["issue"], 426)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertEqual(payload["source_proof_native_contract"]["issue"], 424)
        self.assertEqual(payload["source_proof_native_contract"]["result"], "GO")
        self.assertEqual(payload["backend_decision"]["primary_blocker"], GATE.PRIMARY_BLOCKER)
        self.assertEqual(
            payload["backend_decision"]["usable_cryptographic_backend_route_ids"],
            ["external_snark_or_ivc_statement_receipt_backend"],
        )
        self.assertFalse(payload["backend_decision"]["blocked_before_metrics"])
        self.assertEqual(payload["backend_decision"]["proof_metrics"]["proof_size_bytes"], 802)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))

    def test_source_contract_binds_exact_target_and_public_inputs(self) -> None:
        source = self.fresh_payload()["source_proof_native_contract"]
        public_inputs = source["public_input_contract"]
        self.assertEqual(source["selected_slice_ids"], list(GATE.EXPECTED_SELECTED_SLICE_IDS))
        self.assertEqual(source["selected_checked_rows"], 256)
        self.assertEqual(source["two_slice_target_commitment"], public_inputs["two_slice_target_commitment"])
        self.assertEqual(
            public_inputs["required_public_inputs"],
            [
                "two_slice_target_commitment",
                "selected_slice_statement_commitments",
                "selected_source_evidence_hashes",
                "selected_slice_public_instance_commitments",
                "selected_slice_proof_native_parameter_commitments",
                "verifier_domain",
                "required_backend_version",
                "source_accumulator_commitment",
                "source_verifier_handle_commitment",
            ],
        )
        self.assertEqual(len(public_inputs["selected_slice_statement_commitments"]), 2)
        self.assertEqual(len(public_inputs["selected_source_evidence_hashes"]), 2)
        self.assertEqual(len(public_inputs["selected_slice_public_instance_commitments"]), 2)
        self.assertEqual(len(public_inputs["selected_slice_proof_native_parameter_commitments"]), 2)
        self.assertGreater(source["compression_metrics"]["source_accumulator_artifact_serialized_bytes"], source["compression_metrics"]["compressed_artifact_serialized_bytes"])

    def test_route_table_separates_source_contract_from_backends(self) -> None:
        routes = {route["route_id"]: route for route in self.fresh_payload()["backend_routes"]}
        self.assertEqual(routes["source_proof_native_two_slice_contract"]["status"], "GO_INPUT_CONTRACT_ONLY_NOT_CRYPTOGRAPHIC_BACKEND")
        self.assertFalse(routes["source_proof_native_two_slice_contract"]["cryptographic_backend"])
        for route_id in (
            "local_stwo_nested_verifier_backend",
            "local_pcd_or_ivc_outer_proof_backend",
            "external_zkvm_statement_receipt_backend",
        ):
            with self.subTest(route_id=route_id):
                self.assertTrue(routes[route_id]["cryptographic_backend"])
                self.assertFalse(routes[route_id]["usable_today"])
                self.assertTrue(routes[route_id]["status"].startswith("NO_GO"))
                self.assertTrue(all(value is None for value in routes[route_id]["proof_metrics"].values()))
        snark_route = routes["external_snark_or_ivc_statement_receipt_backend"]
        self.assertTrue(snark_route["cryptographic_backend"])
        self.assertTrue(snark_route["usable_today"])
        self.assertTrue(snark_route["status"].startswith("GO_EXTERNAL_SNARK"))
        self.assertEqual(snark_route["proof_metrics"]["proof_size_bytes"], 802)
        self.assertIsNone(snark_route["proof_metrics"]["verifier_time_ms"])
        self.assertEqual(snark_route["evidence"]["tracked_issue"], 428)
        self.assertEqual(routes["external_zkvm_statement_receipt_backend"]["evidence"]["tracked_issue"], 422)
        self.assertEqual(routes["starknet_settlement_adapter"]["status"], "DEFERRED_UNTIL_A_PROOF_OBJECT_EXISTS")

    def test_backend_probe_records_checked_snark_artifact_but_no_local_or_zkvm_backend(self) -> None:
        probe = self.fresh_payload()["backend_probe"]
        self.assertEqual(probe, GATE.backend_probe())
        self.assertFalse(probe["external_zkvm_dependencies_declared"])
        self.assertFalse(probe["external_snark_ivc_dependencies_declared"])
        self.assertEqual(probe["external_zkvm_dependency_names"], [])
        self.assertEqual(probe["external_snark_ivc_dependency_names"], [])
        by_id = {artifact["artifact_id"]: artifact for artifact in probe["fixed_backend_artifacts"]}
        self.assertFalse(by_id["local_stwo_nested_verifier_module"]["exists"])
        self.assertFalse(by_id["external_zkvm_statement_receipt_artifact"]["exists"])
        self.assertTrue(by_id["external_snark_ivc_statement_receipt_artifact"]["exists"])
        self.assertIn(
            "docs/engineering/evidence/zkai-d128-snark-ivc-statement-receipt-2026-05.json",
            probe["artifact_candidates"],
        )

    def test_json_loader_reports_snark_receipt_layer(self) -> None:
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "SNARK receipt evidence is not a regular file") as err:
            GATE.load_json(
                GATE.EVIDENCE_DIR / "missing-snark-receipt-evidence.json",
                layer="external_snark_receipt",
                field="SNARK receipt evidence",
            )

        self.assertEqual(err.exception.layer, "external_snark_receipt")

    def test_cargo_dependency_probe_finds_nested_aliases(self) -> None:
        cargo_toml = {
            "dev-dependencies": {"sp1-sdk": "1"},
            "build-dependencies": {"snark": {"version": "1"}},
            "workspace": {"dependencies": {"risc0_alias": {"package": "risc0-zkvm", "version": "1"}}},
            "target": {"cfg(unix)": {"dependencies": {"nova-snark": "1"}}},
        }
        names = GATE.cargo_dependency_names(cargo_toml)
        self.assertTrue({"sp1-sdk", "snark", "risc0-zkvm", "nova-snark"} <= names)

    def test_mutation_inventory_covers_contract_backend_and_metric_surfaces(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        expected_layers = {
            "source_target_commitment_drift": "source_public_input_contract",
            "source_selected_source_hash_drift": "source_public_input_contract",
            "source_verifier_handle_commitment_drift": "source_public_input_contract",
            "repo_probe_dependency_hint_drift": "backend_probe",
            "route_local_nested_verifier_relabel_to_go": "backend_routes",
            "route_external_zkvm_relabel_to_go": "backend_routes",
            "route_metric_smuggled": "backend_routes",
            "backend_decision_usable_route_relabel_to_go": "backend_decision",
            "proof_size_metric_smuggled": "backend_decision",
            "validation_command_drift": "parser_or_schema",
        }
        for mutation, layer in expected_layers.items():
            with self.subTest(mutation=mutation):
                self.assertTrue(cases[mutation]["rejected"])
                self.assertEqual(cases[mutation]["rejection_layer"], layer)
                self.assertEqual(cases[mutation]["error_code"], mutation)

    def test_rejects_public_input_contract_relabeling(self) -> None:
        payload = self.fresh_payload()
        core = GATE._core_payload_for_case_replay(payload)
        core["source_proof_native_contract"]["public_input_contract"]["two_slice_target_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "source proof-native contract"):
            GATE.validate_core_payload(core)

        core = GATE._core_payload_for_case_replay(payload)
        core["source_proof_native_contract"]["public_input_contract"]["selected_slice_statement_commitments"][0]["statement_commitment"] = "blake2b-256:" + "22" * 32
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "source proof-native contract"):
            GATE.validate_core_payload(core)

    def test_rejects_fake_backend_go_or_metric_smuggling(self) -> None:
        core = GATE._core_payload_for_case_replay(self.fresh_payload())
        core["backend_routes"][1]["usable_today"] = True
        core["backend_routes"][1]["status"] = "GO_EXECUTABLE_BACKEND"
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "cryptographic route"):
            GATE.validate_core_payload(core)

        core = GATE._core_payload_for_case_replay(self.fresh_payload())
        core["backend_decision"]["proof_metrics"]["proof_size_bytes"] = 1024
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "decision proof size"):
            GATE.validate_core_payload(core)

    def test_rejects_partial_duplicate_and_tampered_mutation_metadata(self) -> None:
        payload = self.fresh_payload()
        del payload["cases"]
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "all-or-nothing"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][1] = copy.deepcopy(payload["cases"][0])
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "duplicate mutation case"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][0]["error"] = "free-form error text is not checked evidence"
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "keys mismatch"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["cases"][0]["error_code"] = "rewritten_error_code"
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "mutation case 0"):
            GATE.validate_payload(payload)

    def test_tsv_columns_are_route_table_not_mutation_text(self) -> None:
        lines = GATE.to_tsv(self.fresh_payload()).splitlines()
        self.assertEqual(tuple(lines[0].split("\t")), GATE.TSV_COLUMNS)
        self.assertIn("local_stwo_nested_verifier_backend", "\n".join(lines))
        self.assertNotIn("source_file_hash_drift", "\n".join(lines))

    def test_write_outputs_round_trips_under_evidence_dir(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "cryptographic-backend.json").relative_to(GATE.ROOT)
            tsv_path = (tmp / "cryptographic-backend.tsv").relative_to(GATE.ROOT)
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads((GATE.ROOT / json_path).read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("external_zkvm_statement_receipt_backend", (GATE.ROOT / tsv_path).read_text(encoding="utf-8"))

    def test_write_outputs_rejects_unsafe_paths(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "repo-relative"):
                GATE.write_outputs(payload, pathlib.Path(raw_tmp) / "cryptographic-backend.json", None)
            json_target = pathlib.Path(raw_tmp) / "cryptographic-backend.json"
            tsv_link = pathlib.Path(raw_tmp) / "cryptographic-backend.tsv"
            try:
                tsv_link.symlink_to(json_target)
            except OSError:
                self.skipTest("symlink creation not supported in this environment")
            with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "distinct"):
                GATE.write_outputs(payload, json_target.relative_to(GATE.ROOT), tsv_link.relative_to(GATE.ROOT))

        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "without traversal"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/evidence/../cryptographic-backend.json"), None)
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "docs/engineering/evidence"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/not-evidence/cryptographic-backend.json"), None)
        with self.assertRaisesRegex(GATE.D128CryptographicBackendGateError, "end in .tsv"):
            GATE.write_outputs(payload, None, pathlib.Path("docs/engineering/evidence/cryptographic-backend.txt"))


if __name__ == "__main__":
    unittest.main()
