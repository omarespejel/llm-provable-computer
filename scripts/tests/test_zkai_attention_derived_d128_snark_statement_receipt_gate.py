from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_snark_statement_receipt_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_snark_statement_receipt_gate", GATE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load gate from {GATE_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


def fake_external_verify(_proof, public_signals, _verification_key) -> None:
    if public_signals[0] == "12345":
        raise GATE.AttentionDerivedD128SnarkReceiptError(
            "fake proof verifier rejected public signal",
            layer="external_proof_verifier",
        )


class AttentionDerivedD128SnarkStatementReceiptGateTests(unittest.TestCase):
    def test_baseline_receipt_binds_attention_derived_contract(self) -> None:
        receipt = GATE.baseline_receipt()
        statement = receipt["statement"]
        metrics = GATE.source_route_metrics(statement["source_contract"])

        self.assertEqual(receipt["statement_commitment"], GATE.statement_commitment(statement))
        self.assertEqual(receipt["receipt_commitment"], GATE.receipt_commitment(receipt))
        self.assertEqual(len(statement["public_signal_field_entries"]), 16)
        self.assertEqual(len(receipt["public_signals"]), 17)
        self.assertEqual(receipt["public_signals"], GATE.expected_public_signals(statement["public_signal_field_entries"]))
        self.assertEqual(metrics["source_chain_artifact_bytes"], 14_624)
        self.assertEqual(metrics["compressed_artifact_bytes"], 2_559)
        self.assertEqual(metrics["byte_savings"], 12_065)
        self.assertEqual(metrics["source_relation_rows"], 199_553)
        self.assertEqual(
            metrics["input_contract_commitment"],
            "blake2b-256:503fb256305f03a8da20b6872753234dbf776bb1b81044485949b4072152ed39",
        )

    def test_gate_records_go_and_rejects_full_mutation_inventory(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertEqual({case["mutation"] for case in payload["cases"]}, GATE.EXPECTED_MUTATION_SET)
        self.assertEqual(
            payload["proof_verifier_checks"]["public_signal_relabeling"]["rejection_layer"],
            "external_proof_verifier",
        )

    def test_existing_two_slice_snark_receipt_is_not_reused_for_attention_contract(self) -> None:
        comparison = GATE.control_public_signal_comparison()

        self.assertFalse(comparison["same_public_signals"])
        self.assertEqual(comparison["control_public_signal_count"], 17)
        self.assertEqual(comparison["attention_public_signal_count"], 17)
        self.assertEqual(comparison["matching_positions"], 0)

    def test_repro_git_commit_ignores_environment_override(self) -> None:
        with mock.patch.dict(GATE.os.environ, {"ZKAI_ATTENTION_D128_SNARK_RECEIPT_GIT_COMMIT": "spoofed"}, clear=False):
            with mock.patch.object(GATE, "_git_commit", return_value="a" * 40):
                payload = GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(payload["repro"]["git_commit"], "a" * 40)

    def test_snarkjs_launch_failure_is_layered(self) -> None:
        GATE.SNARKJS_VERIFIED_CACHE.clear()
        with mock.patch.object(GATE.subprocess, "run", side_effect=FileNotFoundError("npx")):
            with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "failed to launch snarkjs command") as err:
                GATE._snarkjs_verify_cached("launch-failure-test", b"{}", b"[]", b"{}", ("missing-snarkjs",))

        self.assertEqual(err.exception.layer, "external_proof_verifier")

    def test_snarkjs_env_override_must_resolve_to_pinned_binary(self) -> None:
        with mock.patch.dict(GATE.os.environ, {GATE.SNARKJS_ENV: "/tmp/fake-snarkjs"}, clear=False):
            with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "override is not allowed") as err:
                GATE.snarkjs_command()

        self.assertEqual(err.exception.layer, "external_proof_verifier")

        pinned = GATE.SNARKJS_BINARY.resolve()
        with mock.patch.dict(GATE.os.environ, {GATE.SNARKJS_ENV: str(GATE.SNARKJS_BINARY)}, clear=False):
            self.assertEqual(GATE.snarkjs_command(), (str(pinned),))

    def test_snarkjs_success_parser_rejects_not_ok_substrings(self) -> None:
        self.assertTrue(GATE.snarkjs_verify_reported_ok("[INFO]  snarkJS: OK!"))
        self.assertTrue(GATE.snarkjs_verify_reported_ok("OK"))
        self.assertFalse(GATE.snarkjs_verify_reported_ok("[INFO]  snarkJS: NOT OK"))
        self.assertFalse(GATE.snarkjs_verify_reported_ok("NOT OK"))

    def test_snarkjs_version_parser_requires_exact_version(self) -> None:
        self.assertTrue(GATE.snarkjs_version_reported("snarkjs@0.7.6\nUsage: snarkjs ..."))
        self.assertTrue(GATE.snarkjs_version_reported("0.7.6"))
        self.assertFalse(GATE.snarkjs_version_reported("snarkjs@0.7.60\nUsage: snarkjs ..."))
        self.assertFalse(GATE.snarkjs_version_reported("snarkjs@0.7.5"))

    def test_snarkjs_verified_cache_uses_digest_token(self) -> None:
        GATE.SNARKJS_VERIFIED_CACHE.clear()
        result = mock.Mock(returncode=0, stdout="[INFO]  snarkJS: OK!", stderr="")
        with mock.patch.object(GATE, "assert_snarkjs_version") as version:
            with mock.patch.object(GATE.subprocess, "run", return_value=result) as run:
                GATE._snarkjs_verify_cached("digest", b"{}", b"[]", b"{}", ("snarkjs",))
                GATE._snarkjs_verify_cached("digest", b"{}", b"[]", b"{}", ("snarkjs",))

        self.assertEqual(version.call_count, 1)
        self.assertEqual(run.call_count, 1)
        self.assertIn((("snarkjs",), "digest"), GATE.SNARKJS_VERIFIED_CACHE)

    def test_raw_proof_only_accepts_semantic_relabel_but_statement_receipt_rejects(self) -> None:
        _surface, relabeled = GATE.mutated_receipts()["input_contract_commitment_relabeling"]

        GATE.verify_proof_only(relabeled, external_verify=fake_external_verify)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "source_contract mismatch") as err:
            GATE.verify_statement_receipt(relabeled, external_verify=fake_external_verify)
        self.assertEqual(err.exception.layer, "statement_policy")

    def test_source_payload_runs_source_gate_validator(self) -> None:
        forged = copy.deepcopy(GATE.source_payload())
        forged["summary"]["byte_savings"] = 1

        GATE.source_payload.cache_clear()
        try:
            with mock.patch.object(GATE, "load_json", return_value=forged):
                with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "source route gate validation failed") as err:
                    GATE.source_payload()
            self.assertEqual(err.exception.layer, "source_contract")
        finally:
            GATE.source_payload.cache_clear()

    def test_public_signal_drift_is_rejected_by_raw_snark_verifier_check(self) -> None:
        check = GATE.proof_verifier_public_signal_check(GATE.baseline_receipt(), fake_external_verify)

        self.assertTrue(check["rejected"])
        self.assertFalse(check["mutated_accepted"])
        self.assertEqual(check["rejection_layer"], "external_proof_verifier")

    def test_artifact_input_metric_smuggling_and_unknown_fields_fail_closed(self) -> None:
        for name in (
            "artifacts_map_drift",
            "input_payload_drift",
            "embedded_proof_relabeling",
            "embedded_vk_relabeling",
            "embedded_public_signals_relabeling",
            "proof_size_metric_smuggled",
            "verifier_time_metric_smuggled",
            "proof_generation_time_metric_smuggled",
            "unknown_statement_field_added",
            "unknown_top_level_field_added",
        ):
            _surface, receipt = GATE.mutated_receipts()[name]
            with self.assertRaises(GATE.AttentionDerivedD128SnarkReceiptError):
                GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)

    def test_statement_schema_rejects_extra_keys_after_recommit(self) -> None:
        receipt = GATE.baseline_receipt()
        receipt["statement"]["unexpected"] = True
        GATE._refresh_statement_commitment(receipt)

        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "statement keys mismatch") as err:
            GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)

        self.assertEqual(err.exception.layer, "parser_or_schema")

    def test_embedded_artifact_objects_must_match_checked_artifacts(self) -> None:
        for name in ("embedded_proof_relabeling", "embedded_vk_relabeling", "embedded_public_signals_relabeling"):
            _surface, receipt = GATE.mutated_receipts()[name]
            with self.assertRaises(GATE.AttentionDerivedD128SnarkReceiptError) as err:
                GATE.verify_statement_receipt(receipt, external_verify=fake_external_verify)
            self.assertEqual(err.exception.layer, "artifact_binding")

    def test_input_artifact_must_match_derived_public_fields(self) -> None:
        receipt = GATE.baseline_receipt()
        forged_input = copy.deepcopy(receipt["input"])
        forged_input["contract"][0] = "0"

        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "input contract fields mismatch") as err:
            GATE.validate_input_artifact(
                forged_input,
                receipt["public_signals"],
                receipt["statement"]["public_signal_field_entries"],
            )

        self.assertEqual(err.exception.layer, "artifact_binding")

    def test_run_gate_reuses_one_baseline_snapshot(self) -> None:
        with mock.patch.object(GATE, "baseline_receipt", wraps=GATE.baseline_receipt) as baseline:
            GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(baseline.call_count, 1)

    def test_payload_validation_rejects_forged_summary(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        forged = copy.deepcopy(payload)
        forged["cases"][0]["rejected"] = False
        forged["cases"][0]["mutated_accepted"] = True

        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "not all attention-derived SNARK receipt mutations rejected"):
            GATE.validate_payload(forged)

    def test_payload_validation_rederives_verifier_facing_fields(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        forged = copy.deepcopy(payload)
        forged["statement_receipt"]["proof_sha256"] = "0" * 64

        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "statement receipt mismatch") as err:
            GATE.validate_payload(forged)

        self.assertEqual(err.exception.layer, "statement_policy")

    def test_payload_validation_rederives_receipt_metrics(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        forged = copy.deepcopy(payload)
        forged["receipt_metrics"]["public_signals_bytes"] += 1

        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "receipt metrics mismatch") as err:
            GATE.validate_payload(forged)

        self.assertEqual(err.exception.layer, "receipt_metrics")

    def test_payload_validation_rejects_repro_drift(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)
        for mutation in (
            lambda p: p["repro"].__setitem__("command", "python3 fake.py"),
            lambda p: p["repro"].__setitem__("git_commit", "not-a-commit"),
            lambda p: p["repro"].__setitem__("unexpected", True),
        ):
            forged = copy.deepcopy(payload)
            mutation(forged)
            with self.assertRaises(GATE.AttentionDerivedD128SnarkReceiptError) as err:
                GATE.validate_payload(forged)
            self.assertEqual(err.exception.layer, "parser_or_schema")

    def test_payload_and_tsv_reject_malformed_case_shapes(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)

        forged_inventory = copy.deepcopy(payload)
        forged_inventory["mutation_inventory"][0] = "not-an-object"
        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "mutation inventory\\[0\\] must be an object") as err:
            GATE.validate_payload(forged_inventory)
        self.assertEqual(err.exception.layer, "parser_or_schema")

        forged_case = copy.deepcopy(payload)
        forged_case["cases"][0] = "not-an-object"
        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "case\\[0\\] must be an object") as err:
            GATE.validate_payload(forged_case)
        self.assertEqual(err.exception.layer, "parser_or_schema")

        forged_tsv = copy.deepcopy(payload)
        del forged_tsv["cases"][0]["error"]
        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "missing TSV keys") as err:
            GATE.to_tsv(forged_tsv)
        self.assertEqual(err.exception.layer, "parser_or_schema")

    def test_tsv_columns_are_stable(self) -> None:
        payload = GATE.run_gate(external_verify=fake_external_verify)

        self.assertEqual(GATE.to_tsv(payload).splitlines()[0].split("\t"), list(GATE.TSV_COLUMNS))

    def test_output_path_must_stay_under_evidence_dir(self) -> None:
        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "output path must stay"):
            GATE.write_text_checked(ROOT / "outside.json", "{}\n")
        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "output path must stay"):
            GATE.write_text_checked(GATE.EVIDENCE_DIR, "{}\n")
        with self.assertRaisesRegex(GATE.AttentionDerivedD128SnarkReceiptError, "output path must be a file"):
            GATE.write_text_checked(GATE.ARTIFACT_DIR, "{}\n")

    def test_artifact_input_writer_derives_expected_public_inputs(self) -> None:
        entries = GATE.contract_field_entries()
        expected_input = {"contract": [entry["public_signal"] for entry in entries]}

        self.assertEqual(len(expected_input["contract"]), 16)
        self.assertEqual(GATE.expected_public_signals(entries), [str(sum(int(field) for field in expected_input["contract"]) % GATE.BN128_FIELD_MODULUS), *expected_input["contract"]])

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
