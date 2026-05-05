from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "scripts" / "zkai_d64_external_recursion_adapter_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_external_recursion_adapter_gate", GATE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load gate from {GATE_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


def fake_external_verify(_proof, public_signals, _verification_key) -> None:
    if public_signals[0] == "12345":
        raise GATE.D64ExternalRecursionAdapterError(
            "fake proof verifier rejected public signal",
            layer="external_proof_verifier",
        )


class D64ExternalRecursionAdapterGateTests(unittest.TestCase):
    def test_contract_field_entries_bind_expected_nested_verifier_contract(self) -> None:
        contract = GATE.source_contract()
        entries = GATE.contract_field_entries(contract)
        public_signals = GATE.expected_public_signals(entries)

        self.assertEqual(
            contract["nested_verifier_contract_commitment"],
            "blake2b-256:d2aadb57aa5f0ab996fe740dc8e6b8fca12c30149de4208d2e9dab2828232d3a",
        )
        self.assertEqual(contract["nested_verifier_contract"]["selected_slice_ids"], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        self.assertEqual(len(entries), 21)
        self.assertEqual(len(public_signals), 22)
        self.assertEqual(public_signals[1:], [entry["public_signal"] for entry in entries])

    def test_gate_records_go_and_rejects_full_mutation_inventory(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertEqual({case["mutation"] for case in payload["cases"]}, GATE.EXPECTED_MUTATION_SET)
        self.assertEqual(
            payload["proof_verifier_checks"]["public_signal_relabeling"]["rejection_layer"],
            "external_proof_verifier",
        )

    def test_repro_git_commit_ignores_environment_override(self) -> None:
        actual_commit = "a" * 40
        with mock.patch.dict(GATE.os.environ, {"ZKAI_D64_EXTERNAL_ADAPTER_GIT_COMMIT": "spoofed"}, clear=False):
            with mock.patch.object(GATE, "_git_commit", return_value=actual_commit):
                payload = GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(payload["repro"]["git_commit"], actual_commit)

    def test_snarkjs_path_supports_command_with_args(self) -> None:
        GATE.assert_snarkjs_version.cache_clear()
        GATE._snarkjs_verify_cached.cache_clear()
        responses = [
            GATE.subprocess.CompletedProcess(["npx", "-y", "snarkjs@0.7.6", "--version"], 0, stdout="snarkjs@0.7.6\n", stderr=""),
            GATE.subprocess.CompletedProcess(["npx", "-y", "snarkjs@0.7.6", "groth16", "verify"], 0, stdout="[INFO]  snarkJS: OK!\n", stderr=""),
        ]
        with mock.patch.dict(GATE.os.environ, {GATE.SNARKJS_ENV: "npx -y snarkjs@0.7.6"}, clear=False):
            command = GATE.snarkjs_command()
            with mock.patch.object(GATE.subprocess, "run", side_effect=responses) as run:
                GATE._snarkjs_verify_cached("snarkjs-path-args-test", b"{}", b"[]", b"{}", command)

        self.assertEqual(command, ("npx", "-y", "snarkjs@0.7.6"))
        self.assertEqual(run.call_args_list[0].args[0], ["npx", "-y", "snarkjs@0.7.6", "--version"])
        self.assertEqual(run.call_args_list[1].args[0][:5], ["npx", "-y", "snarkjs@0.7.6", "groth16", "verify"])

    def test_snarkjs_launch_failure_is_layered(self) -> None:
        GATE.assert_snarkjs_version.cache_clear()
        GATE._snarkjs_verify_cached.cache_clear()
        with mock.patch.object(GATE.subprocess, "run", side_effect=FileNotFoundError("npx")):
            with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "failed to launch snarkjs command") as err:
                GATE._snarkjs_verify_cached("launch-failure-test", b"{}", b"[]", b"{}", ("missing-snarkjs",))

        self.assertEqual(err.exception.layer, "external_proof_verifier")

    def test_raw_proof_only_accepts_semantic_relabel_but_statement_receipt_rejects(self) -> None:
        _surface, relabeled = GATE.mutated_receipts()["nested_verifier_contract_commitment_relabeling"]

        GATE.verify_proof_only(relabeled, external_verify=fake_external_verify)
        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "source_contract mismatch") as err:
            GATE.verify_statement_receipt(relabeled, external_verify=fake_external_verify)
        self.assertEqual(err.exception.layer, "statement_policy")

    def test_source_payload_runs_source_gate_validator(self) -> None:
        forged = copy.deepcopy(GATE.source_payload())
        forged["nested_verifier_contract"]["selected_nested_verifier_checks"][0]["slice_id"] = "fake_slice"

        GATE.source_payload.cache_clear()
        try:
            with mock.patch.object(GATE, "load_json", return_value=forged):
                with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "source #379 gate validation failed") as err:
                    GATE.source_payload()
            self.assertEqual(err.exception.layer, "source_contract")
        finally:
            GATE.source_payload.cache_clear()

    def test_public_signal_drift_is_rejected_by_raw_snark_verifier_check(self) -> None:
        check = GATE.proof_verifier_public_signal_check(GATE.baseline_receipt(), fake_external_verify)

        self.assertTrue(check["rejected"])
        self.assertFalse(check["mutated_accepted"])
        self.assertEqual(check["rejection_layer"], "external_proof_verifier")

    def test_metric_smuggling_and_unknown_fields_fail_closed(self) -> None:
        for name in (
            "proof_size_metric_smuggled",
            "verifier_time_metric_smuggled",
            "proof_generation_time_metric_smuggled",
        ):
            _surface, receipt = GATE.mutated_receipts()[name]
            with self.assertRaises(GATE.D64ExternalRecursionAdapterError) as err:
                GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)
            self.assertEqual(err.exception.layer, "receipt_metrics")

        for name in (
            "unknown_top_level_field_added",
        ):
            _surface, receipt = GATE.mutated_receipts()[name]
            with self.assertRaises(GATE.D64ExternalRecursionAdapterError):
                GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)

    def test_statement_receipt_rejects_unknown_statement_field(self) -> None:
        _surface, receipt = GATE.mutated_receipts()["unknown_statement_field_added"]

        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "statement keys mismatch") as err:
            GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)
        self.assertEqual(err.exception.layer, "statement_policy")

    def test_statement_receipt_binds_public_signals_artifact(self) -> None:
        _surface, receipt = GATE.mutated_receipts()["public_signal_relabeling"]

        with self.assertRaises(GATE.D64ExternalRecursionAdapterError) as err:
            GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)
        self.assertIn(err.exception.layer, {"public_signal_binding", "artifact_binding"})

    def test_statement_receipt_rejects_embedded_proof_and_vk_swap(self) -> None:
        _surface, receipt = GATE.mutated_receipts()["embedded_proof_and_verification_key_payload_relabeling"]

        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "proof artifact payload mismatch") as err:
            GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)
        self.assertEqual(err.exception.layer, "artifact_binding")

    def test_payload_validation_rejects_forged_summary(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        forged = copy.deepcopy(payload)
        forged["cases"][0]["rejected"] = False
        forged["cases"][0]["mutated_accepted"] = True

        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "not all d64 external adapter mutations rejected") as err:
            GATE.validate_payload(forged)
        self.assertEqual(err.exception.layer, "mutation_suite")

    def test_payload_validation_rejects_forged_repro(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        forged_command = copy.deepcopy(payload)
        forged_command["repro"]["command"] = "python3 scripts/fake_gate.py"
        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "repro command mismatch") as command_err:
            GATE.validate_payload(forged_command)
        self.assertEqual(command_err.exception.layer, "parser_or_schema")

        forged_commit = copy.deepcopy(payload)
        forged_commit["repro"]["git_commit"] = "not-a-git-sha"
        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "repro git_commit must be") as commit_err:
            GATE.validate_payload(forged_commit)
        self.assertEqual(commit_err.exception.layer, "parser_or_schema")

    def test_payload_validation_rederives_statement_receipt(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        forged = copy.deepcopy(payload)
        forged["statement_receipt"]["proof_sha256"] = "0" * 64

        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "statement receipt mismatch") as err:
            GATE.validate_payload(forged)
        self.assertEqual(err.exception.layer, "statement_policy")

    def test_payload_validation_rederives_receipt_metrics(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        forged = copy.deepcopy(payload)
        forged["receipt_metrics"]["public_signals_bytes"] += 1

        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "receipt metrics mismatch") as err:
            GATE.validate_payload(forged)
        self.assertEqual(err.exception.layer, "receipt_metrics")

    def test_tsv_columns_are_stable(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(GATE.to_tsv(payload).splitlines()[0].split("\t"), list(GATE.TSV_COLUMNS))

    def test_output_path_must_stay_under_evidence_dir(self) -> None:
        with self.assertRaisesRegex(GATE.D64ExternalRecursionAdapterError, "output path must stay"):
            GATE.write_text_checked(ROOT / "outside.json", "{}\n")

    def test_checked_json_artifact_matches_current_schema_when_present(self) -> None:
        path = GATE.JSON_OUT
        if not path.exists():
            self.skipTest("JSON evidence has not been generated yet")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertTrue(payload["all_mutations_rejected"])


if __name__ == "__main__":
    unittest.main()
