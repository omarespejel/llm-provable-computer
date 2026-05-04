from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_zkvm_statement_receipt_adapter_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_zkvm_statement_receipt_adapter_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 zkVM gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class D128ZkvmStatementReceiptAdapterGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.checked_payload = GATE.build_payload(probe=cls.fixture_probe())

    @staticmethod
    def fixture_probe() -> dict:
        commands = {}
        for command_id, command in GATE.COMMAND_PROBES:
            commands[command_id] = {
                "command_id": command_id,
                "command": list(command),
                "available": False,
                "returncode": None,
                "stdout": "",
                "stderr": "",
            }
        return {
            "probe_scope": "local_cli_bootstrap_only_no_network_install",
            "host_os": "test",
            "commands": commands,
        }

    def payload(self) -> dict:
        return copy.deepcopy(self.checked_payload)

    def test_gate_records_honest_toolchain_no_go(self) -> None:
        payload = self.payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["issue"], 422)
        self.assertEqual(payload["source_issue"], 424)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "NO_GO")
        self.assertEqual(payload["backend_decision"]["first_blocker"], GATE.FIRST_BLOCKER)
        self.assertEqual(payload["summary"], GATE.SUMMARY_BY_BLOCKER[GATE.FIRST_BLOCKER])
        self.assertEqual(payload["backend_decision"]["usable_route_ids"], [])
        self.assertFalse(payload["backend_decision"]["proof_metrics"]["metrics_enabled"])
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))

    def test_journal_contract_binds_source_public_inputs(self) -> None:
        payload = self.payload()
        source = payload["source_contract"]
        journal = payload["journal_contract"]
        self.assertEqual(journal["input_commitment"], source["two_slice_target_commitment"])
        self.assertEqual(journal["output_commitment"], source["compressed_artifact_commitment"])
        self.assertEqual(journal["verifier_domain"], source["public_input_contract"]["verifier_domain"])
        self.assertEqual(journal["public_values"], source["public_input_contract"])
        self.assertEqual(journal["policy_label"], GATE.POLICY_LABEL)
        self.assertEqual(journal["action_label"], GATE.ACTION_LABEL)
        self.assertEqual(journal, GATE.journal_contract(source))

    def test_routes_name_missing_commands_and_no_metrics(self) -> None:
        routes = {route["route_id"]: route for route in self.payload()["route_decisions"]}
        self.assertEqual(routes["risc0_zkvm_statement_receipt"]["missing_commands"], ["rzup", "cargo-risczero"])
        self.assertEqual(routes["sp1_zkvm_statement_receipt"]["missing_commands"], ["sp1up", "cargo-prove"])
        for route in routes.values():
            self.assertFalse(route["usable_today"])
            self.assertTrue(route["status"].startswith("NO_GO"))
            self.assertTrue(all(value is None for value in route["proof_metrics"].values()))

    def test_route_stays_no_go_with_toolchain_and_unverified_receipt_file(self) -> None:
        probe = self.fixture_probe()
        for entry in probe["commands"].values():
            entry["available"] = True
            entry["returncode"] = 0
            entry["stdout"] = f"{entry['command_id']} test-version"

        original_routes = GATE.ZKVM_ROUTES
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            receipt_path = pathlib.Path(raw_tmp) / "receipt.json"
            receipt_path.write_text("{}\n", encoding="utf-8")
            relative_receipt = receipt_path.relative_to(GATE.ROOT).as_posix()
            GATE.ZKVM_ROUTES = tuple({**route, "receipt_artifact": relative_receipt} for route in original_routes)
            try:
                payload = GATE.build_payload(probe=probe)
                GATE.validate_payload(payload)
            finally:
                GATE.ZKVM_ROUTES = original_routes

        self.assertEqual(payload["backend_decision"]["usable_route_ids"], [])
        self.assertEqual(payload["backend_decision"]["first_blocker"], GATE.RECEIPT_VERIFICATION_BLOCKER)
        for route in payload["route_decisions"]:
            self.assertFalse(route["usable_today"])
            self.assertEqual(route["status"], "NO_GO_ZKVM_RECEIPT_VERIFICATION_NOT_IMPLEMENTED")
            self.assertEqual(route["first_blocker"], "missing_receipt_verification_and_public_values_binding")

    def test_backend_blocker_prefers_toolchain_ready_route(self) -> None:
        probe = self.fixture_probe()
        for command_id in ("sp1up", "cargo-prove"):
            probe["commands"][command_id]["available"] = True
            probe["commands"][command_id]["returncode"] = 0
            probe["commands"][command_id]["stdout"] = f"{command_id} test-version"

        payload = GATE.build_payload(probe=probe)
        GATE.validate_payload(payload)
        self.assertEqual(payload["backend_decision"]["first_blocker"], "MISSING_ZKVM_RECEIPT_ARTIFACT")
        self.assertEqual(payload["summary"], GATE.SUMMARY_BY_BLOCKER["MISSING_ZKVM_RECEIPT_ARTIFACT"])

    def test_rejects_journal_relabeling(self) -> None:
        payload = self.payload()
        core = GATE._core_payload(payload)
        core["journal_contract"]["policy_label"] = "fake-policy"
        with self.assertRaisesRegex(GATE.D128ZkvmStatementReceiptAdapterError, "journal contract mismatch") as err:
            GATE.validate_core_payload(core)
        self.assertEqual(err.exception.layer, "journal_contract")
        cases = {case["mutation"]: case for case in payload["cases"]}
        self.assertTrue(cases["journal_policy_relabeling"]["rejected"])
        self.assertEqual(cases["journal_policy_relabeling"]["rejection_layer"], "journal_contract")

    def test_rejects_route_relabeling_to_go(self) -> None:
        payload = self.payload()
        core = GATE._core_payload(payload)
        core["route_decisions"][0]["usable_today"] = True
        core["route_decisions"][0]["status"] = "GO_ZKVM_STATEMENT_RECEIPT_AVAILABLE"
        core["route_decisions"][0]["first_blocker"] = "none"
        with self.assertRaisesRegex(GATE.D128ZkvmStatementReceiptAdapterError, "route decisions mismatch") as err:
            GATE.validate_core_payload(core)
        self.assertEqual(err.exception.layer, "route_decisions")

    def test_rejects_metric_smuggling(self) -> None:
        payload = self.payload()
        core = GATE._core_payload(payload)
        core["backend_decision"]["proof_metrics"]["proof_size_bytes"] = 1
        with self.assertRaisesRegex(GATE.D128ZkvmStatementReceiptAdapterError, "backend decision mismatch") as err:
            GATE.validate_core_payload(core)
        self.assertEqual(err.exception.layer, "backend_decision")

    def test_rejects_mutation_case_diagnostic_drift_and_extra_fields(self) -> None:
        payload = self.payload()
        payload["cases"][0]["rejection_layer"] = "accepted"
        with self.assertRaisesRegex(GATE.D128ZkvmStatementReceiptAdapterError, "case .* mismatch") as err:
            GATE.validate_payload(payload)
        self.assertEqual(err.exception.layer, "mutation_suite")

        payload = self.payload()
        payload["cases"][0]["extra"] = True
        with self.assertRaisesRegex(GATE.D128ZkvmStatementReceiptAdapterError, r"case\[0\] keys mismatch") as err:
            GATE.validate_payload(payload)
        self.assertEqual(err.exception.layer, "mutation_suite")

    def test_tsv_contains_route_rows(self) -> None:
        tsv = GATE.to_tsv(self.payload())
        self.assertEqual(tsv.splitlines()[0].split("\t"), list(GATE.TSV_COLUMNS))
        self.assertIn("risc0_zkvm_statement_receipt", tsv)
        self.assertIn("sp1_zkvm_statement_receipt", tsv)

    def test_output_paths_fail_closed(self) -> None:
        same = pathlib.Path("docs/engineering/evidence/same-output")
        with self.assertRaisesRegex(GATE.D128ZkvmStatementReceiptAdapterError, "outputs must be distinct") as err:
            GATE.resolve_output_paths(same, same)
        self.assertEqual(err.exception.layer, "output_path")
        with self.assertRaisesRegex(GATE.D128ZkvmStatementReceiptAdapterError, "not a directory") as err:
            GATE.resolve_output_path(GATE.EVIDENCE_DIR)
        self.assertEqual(err.exception.layer, "output_path")
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            path = pathlib.Path(raw_tmp) / "out.json"
            GATE.write_text_checked(path, "{}\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "{}\n")


if __name__ == "__main__":
    unittest.main()
