from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_native_d128_two_slice_outer_backend_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_native_d128_two_slice_outer_backend_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load native d128 two-slice outer backend gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class NativeD128TwoSliceOuterBackendGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_records_native_outer_no_go_without_downgrading_inner_stwo(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)

        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["issue"], 581)
        self.assertEqual(payload["inner_stwo_baseline_result"], GATE.INNER_STWO_BASELINE_RESULT)
        self.assertEqual(payload["native_outer_backend_result"], GATE.NATIVE_OUTER_BACKEND_RESULT)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertFalse(payload["claim_guard"]["native_two_slice_outer_proof_exists"])
        self.assertFalse(payload["claim_guard"]["package_bytes_are_native_proof_bytes"])
        self.assertFalse(payload["claim_guard"]["snark_bytes_are_native_proof_bytes"])
        self.assertFalse(payload["claim_guard"]["matched_nanozk_claim_allowed"])
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))

    def test_summary_preserves_interesting_numbers_without_native_proof_claim(self) -> None:
        summary = self.fresh_payload()["summary"]
        self.assertEqual(summary["selected_checked_rows"], 256)
        self.assertEqual(summary["source_accumulator_artifact_bytes"], 8822)
        self.assertEqual(summary["compressed_artifact_bytes"], 4435)
        self.assertEqual(summary["compressed_artifact_vs_source_ratio"], 0.50272)
        self.assertEqual(summary["external_snark_proof_bytes"], 802)
        self.assertEqual(summary["external_snark_public_signal_bytes"], 1389)
        self.assertEqual(summary["external_snark_vk_bytes"], 5854)
        self.assertEqual(summary["package_without_vk_bytes"], 4752)
        self.assertEqual(summary["package_without_vk_vs_nanozk_reported_ratio"], 0.688696)
        self.assertEqual(summary["package_with_vk_bytes"], 10608)
        self.assertEqual(summary["package_with_vk_vs_nanozk_reported_ratio"], 1.537391)
        self.assertEqual(summary["nanozk_reported_block_proof_bytes_decimal"], 6900)
        self.assertFalse(summary["proof_metrics_enabled"])
        self.assertIn("no parameterized Stwo AIR", summary["first_blocker"])
        self.assertIn("build the native Stwo verifier-execution surface", summary["next_backend_step"])

    def test_candidate_inventory_separates_inner_stwo_accumulators_packages_and_missing_backend(self) -> None:
        by_name = {item["name"]: item for item in self.fresh_payload()["candidate_inventory"]}
        self.assertEqual(
            by_name["rmsnorm_public_rows_inner_stwo_proof"]["classification"],
            "INNER_STWO_SLICE_PROOF_NOT_OUTER_VERIFIER_EXECUTION",
        )
        self.assertEqual(
            by_name["rmsnorm_projection_bridge_inner_stwo_proof"]["classification"],
            "INNER_STWO_SLICE_PROOF_NOT_OUTER_VERIFIER_EXECUTION",
        )
        self.assertEqual(
            by_name["two_slice_non_recursive_accumulator"]["classification"],
            "GO_NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF",
        )
        self.assertEqual(by_name["two_slice_proof_native_transcript_compression"]["bytes"], 4435)
        self.assertEqual(by_name["external_groth16_statement_receipt"]["bytes"], 802)
        self.assertFalse(by_name["required_native_two_slice_outer_backend_module"]["exists"])
        self.assertTrue(by_name["required_native_two_slice_outer_backend_module"]["required_for_go"])
        self.assertTrue(all(item["supports_native_outer_claim"] is False for item in by_name.values()))

    def test_native_outer_attempt_binds_existing_two_slice_contract_but_blocks_metrics(self) -> None:
        payload = self.fresh_payload()
        attempt = payload["native_outer_attempt"]
        self.assertEqual(attempt["selected_slice_ids"], ["rmsnorm_public_rows", "rmsnorm_projection_bridge"])
        self.assertEqual(attempt["selected_checked_rows"], 256)
        self.assertEqual(
            attempt["two_slice_target_commitment"],
            "blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6",
        )
        self.assertEqual(
            attempt["accumulator_commitment"],
            "blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d",
        )
        self.assertIn("selected_source_evidence_hashes", attempt["required_bound_fields"])
        self.assertIn("selected_slice_statement_commitments", attempt["required_bound_fields"])
        self.assertEqual(
            {item["verifier_domain"] for item in attempt["verifier_domain_labels"]},
            {"ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"},
        )
        self.assertEqual(
            {item["required_backend_version"] for item in attempt["required_backend_versions"]},
            {"stwo-rmsnorm-swiglu-residual-d128-v1"},
        )
        self.assertEqual(
            [item["proof_backend_version"] for item in attempt["selected_slice_proof_backend_versions"]],
            [
                "stwo-d128-rmsnorm-public-row-air-proof-v3",
                "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1",
            ],
        )
        self.assertFalse(attempt["attempt"]["native_outer_proof_artifact_exists"])
        self.assertIsNone(attempt["attempt"]["native_outer_proof_bytes"])
        self.assertTrue(attempt["attempt"]["blocked_before_native_proof_bytes"])

    def test_rejects_native_outer_overclaims_and_metric_smuggling(self) -> None:
        for mutation in (
            "inner_stwo_promoted_to_outer_backend",
            "accumulator_promoted_to_native_outer_proof",
            "compression_promoted_to_native_outer_proof",
            "snark_receipt_promoted_to_native_outer_proof",
            "native_outer_artifact_claimed",
            "local_verifier_handle_claimed",
            "public_input_binding_claimed",
            "native_proof_bytes_smuggled",
            "package_bytes_relabelled_as_native_proof_bytes",
            "snark_bytes_relabelled_as_native_proof_bytes",
            "matched_nanozk_claim_enabled",
            "decision_changed_to_go",
            "selected_slice_ids_reordered",
            "selected_checked_rows_drift",
            "target_commitment_drift",
            "accumulator_commitment_drift",
            "verifier_handle_commitment_drift",
            "required_bound_field_removed",
            "verifier_domain_label_drift",
            "backend_version_label_drift",
            "proof_backend_version_label_drift",
        ):
            with self.subTest(mutation=mutation):
                mutated = GATE.mutate_payload(self.fresh_payload(), mutation)
                with self.assertRaises(GATE.NativeD128TwoSliceOuterBackendError):
                    GATE.validate_core_payload(mutated)

    def test_all_checked_mutations_reject_with_expected_layers(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertFalse(any(case["mutated_accepted"] for case in payload["cases"]))
        layers = {case["rejection_layer"] for case in payload["cases"]}
        self.assertEqual(
            layers,
            {"source_artifacts", "candidate_inventory", "native_outer_attempt", "claim_guard", "parser_or_schema"},
        )

    def test_rejects_stored_case_tampering_and_unknown_fields(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["rejected"] = False
        with self.assertRaisesRegex(GATE.NativeD128TwoSliceOuterBackendError, "cases"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["invented_native_outer_metric"] = 1
        with self.assertRaisesRegex(GATE.NativeD128TwoSliceOuterBackendError, "key set mismatch"):
            GATE.validate_payload(payload)

    def test_loader_rejects_duplicate_json_keys(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=GATE.EVIDENCE_DIR,
            prefix="native-d128-two-slice-duplicate-key-",
            suffix=".json",
            delete=False,
        ) as handle:
            path = pathlib.Path(handle.name)
            handle.write('{"value": 1, "value": 2}\n')
        try:
            with self.assertRaisesRegex(GATE.NativeD128TwoSliceOuterBackendError, "duplicate JSON key"):
                GATE.load_json(path)
        finally:
            path.unlink(missing_ok=True)

    def test_tsv_and_write_outputs(self) -> None:
        payload = self.fresh_payload()
        header = GATE.to_tsv(payload).splitlines()[0].split("\t")
        self.assertEqual(tuple(header), GATE.TSV_COLUMNS)
        self.assertIn("required_native_two_slice_outer_backend_module", GATE.to_tsv(payload))

        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "native-two-slice.json").relative_to(ROOT)
            tsv_path = (tmp / "native-two-slice.tsv").relative_to(ROOT)
            GATE.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads((ROOT / json_path).read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            self.assertIn("external_groth16_statement_receipt", (ROOT / tsv_path).read_text(encoding="utf-8"))

            with self.assertRaisesRegex(GATE.NativeD128TwoSliceOuterBackendError, "distinct"):
                GATE.write_outputs(payload, json_path, json_path)

        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            with self.assertRaisesRegex(GATE.NativeD128TwoSliceOuterBackendError, "repo-relative"):
                GATE.write_outputs(payload, pathlib.Path(raw_tmp) / "bad.json", None)
        with self.assertRaisesRegex(GATE.NativeD128TwoSliceOuterBackendError, "without traversal"):
            GATE.write_outputs(payload, pathlib.Path("docs/engineering/../bad.json"), None)

    def test_write_outputs_cleans_temp_file_when_replace_fails(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "native-two-slice.json").relative_to(ROOT)
            with mock.patch.object(pathlib.Path, "replace", side_effect=OSError("forced replace failure")):
                with self.assertRaisesRegex(OSError, "forced replace failure"):
                    GATE.write_outputs(payload, json_path, None)
            self.assertEqual(list(tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
