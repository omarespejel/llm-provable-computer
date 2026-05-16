import copy
import os
import tempfile
import unittest
from pathlib import Path

from scripts import zkai_native_attention_mlp_single_proof_gate as gate


class NativeAttentionMlpSingleProofGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = gate.build_context()
        gate.validate_context(cls.context)
        cls.payload = gate.build_payload(cls.context)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_pins_single_proof_numbers(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload, context=self.context)
        summary = payload["summary"]
        self.assertEqual(summary["single_proof_typed_bytes"], 41_932)
        self.assertEqual(summary["two_proof_frontier_typed_bytes"], 40_700)
        self.assertEqual(summary["typed_saving_vs_two_proof_bytes"], -1_232)
        self.assertEqual(summary["typed_delta_vs_two_proof_bytes"], 1_232)
        self.assertEqual(summary["typed_ratio_vs_two_proof"], 1.03027)
        self.assertEqual(summary["single_proof_json_bytes"], 119_790)
        self.assertEqual(summary["two_proof_frontier_json_bytes"], 116_258)
        self.assertEqual(summary["json_saving_vs_two_proof_bytes"], -3_532)
        self.assertEqual(summary["json_delta_vs_two_proof_bytes"], 3_532)
        self.assertEqual(summary["json_ratio_vs_two_proof"], 1.030381)
        self.assertEqual(summary["pcs_lifting_log_size"], 19)
        self.assertEqual(summary["adapter_trace_cells"], 1_536)
        self.assertIs(summary["native_adapter_air_proven"], True)

    def test_payload_keeps_adapter_and_nanozk_as_non_claims(self) -> None:
        routes = self.fresh_payload()["routes"]
        self.assertEqual(
            routes["native_single_proof_object"]["status"],
            "GO_VERIFIED_SINGLE_NATIVE_STWO_PROOF_OBJECT_WITH_NATIVE_ADAPTER_AIR",
        )
        self.assertEqual(
            routes["adapter_boundary"]["status"],
            "GO_NATIVE_ADAPTER_AIR_PROVEN_IN_SINGLE_STWO_PROOF_OBJECT",
        )
        self.assertEqual(routes["adapter_boundary"]["adapter_row_count"], 128)
        self.assertEqual(routes["adapter_boundary"]["adapter_trace_cells"], 1_536)
        self.assertIs(routes["adapter_boundary"]["native_adapter_air_proven"], True)
        self.assertEqual(
            routes["two_proof_frontier_comparison"]["status"],
            "NO_GO_NATIVE_ADAPTER_AIR_COSTS_MORE_THAN_CURRENT_TWO_PROOF_FRONTIER",
        )
        self.assertEqual(
            routes["nanozk_comparison_boundary"]["status"],
            "NO_GO_NOT_NANOZK_COMPARABLE",
        )
        self.assertIs(routes["nanozk_comparison_boundary"]["proof_size_win_claimed"], False)

    def test_validation_commands_are_bound_to_proved_input(self) -> None:
        payload = self.fresh_payload()
        input_payload = self.context["envelope"]["input"]
        self.assertEqual(payload["validation_commands"], input_payload["validation_commands"])
        self.assertEqual(payload["validation_commands"], list(gate.EXPECTED_VALIDATION_COMMANDS))
        self.assertNotIn("py_compile", "\n".join(payload["validation_commands"]))
        payload["validation_commands"] = list(payload["validation_commands"])
        payload["validation_commands"].append("python3 -m py_compile scripts/zkai_native_attention_mlp_single_proof_gate.py")
        gate.refresh_routes_and_payload(payload)
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "validation_commands drift"):
            gate.validate_payload(payload, context=self.context)

    def test_input_validation_command_drift_rejects(self) -> None:
        context = copy.deepcopy(self.context)
        context["envelope"]["input"]["validation_commands"].append(
            "python3 -m py_compile scripts/zkai_native_attention_mlp_single_proof_gate.py"
        )
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "input validation commands drift"):
            gate.validate_context(context)

    def test_source_artifact_paths_are_posix(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(
            [artifact["path"] for artifact in payload["source_artifacts"]],
            [
                gate.ENVELOPE_PATH.relative_to(gate.ROOT).as_posix(),
                gate.ACCOUNTING_PATH.relative_to(gate.ROOT).as_posix(),
                gate.ROUTE_BUDGET_PATH.relative_to(gate.ROOT).as_posix(),
            ],
        )

    def test_type_coercion_drift_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["summary"]["pcs_lifting_log_size"] = 19.0
        gate.refresh_routes_and_payload(payload)
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "summary"):
            gate.validate_payload(payload, context=self.context)

        payload = self.fresh_payload()
        payload["routes"]["adapter_boundary"]["native_adapter_air_proven"] = 0
        gate.refresh_routes_and_payload(payload)
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "routes"):
            gate.validate_payload(payload, context=self.context)

    def test_all_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        cases = payload["mutation_result"]["cases"]
        self.assertEqual(payload["mutation_inventory"]["cases"], list(gate.MUTATION_NAMES))
        self.assertEqual(len(cases), len(gate.MUTATION_NAMES))
        self.assertEqual([case["name"] for case in cases], list(gate.MUTATION_NAMES))
        self.assertTrue(all(case["rejected"] for case in cases))
        self.assertEqual({case["reason"] for case in cases}, set(gate.EXPECTED_MUTATION_REASONS.values()))
        for case in cases:
            self.assertEqual(case["reason"], gate.EXPECTED_MUTATION_REASONS[case["name"]])

    def test_promoting_nanozk_win_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["routes"]["nanozk_comparison_boundary"]["proof_size_win_claimed"] = True
        gate.refresh_routes_and_payload(payload)
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "proof_size_win_claimed drift"):
            gate.validate_payload(payload, context=self.context)

    def test_payload_commitment_drift_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "payload commitment drift"):
            gate.validate_payload(payload, context=self.context)

    def test_to_tsv_validates_payload(self) -> None:
        tsv = gate.to_tsv(self.fresh_payload(), self.context)
        expected = (
            "decision\tresult\tsingle_proof_typed_bytes\ttwo_proof_frontier_typed_bytes\t"
            "typed_saving_vs_two_proof_bytes\ttyped_ratio_vs_two_proof\t"
            "single_proof_json_bytes\ttwo_proof_frontier_json_bytes\t"
            "json_saving_vs_two_proof_bytes\tjson_ratio_vs_two_proof\tpcs_lifting_log_size\t"
            "native_adapter_air_proven\ttyped_gap_to_nanozk_reported_bytes\t"
            "typed_reduction_needed_to_nanozk_reported_share\n"
            "GO_NATIVE_ATTENTION_MLP_SINGLE_STWO_PROOF_OBJECT_VERIFIES\t"
            "NARROW_CLAIM_NATIVE_ADAPTER_AIR_VERIFIES_WITH_TYPED_SIZE_COST\t"
            "41932\t40700\t-1232\t1.03027\t119790\t116258\t-3532\t1.030381\t19\tTrue\t35032\t0.835448\n"
        )
        self.assertEqual(tsv, expected)

    def test_written_payload_validates(self) -> None:
        handle = tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix=".tmp-native-attention-mlp-single-proof-",
            suffix=".json",
            delete=False,
        )
        path = Path(handle.name)
        handle.close()
        try:
            gate.write_json(path, self.fresh_payload())
            loaded = gate.read_json(path, "written single proof JSON")
            gate.validate_payload(loaded, context=self.context)
        finally:
            path.unlink(missing_ok=True)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_json_output_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR, prefix=".tmp-single-proof-json-symlink-") as tmp:
            temp_dir = Path(tmp)
            target = temp_dir / "target.json"
            link = temp_dir / "out.json"
            target.write_text("{}", encoding="utf-8")
            try:
                link.symlink_to(target)
            except OSError as err:
                self.skipTest(f"symlink creation unavailable: {err}")
            with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "symlink"):
                gate.write_json(link, self.fresh_payload())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_tsv_output_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR, prefix=".tmp-single-proof-tsv-symlink-") as tmp:
            temp_dir = Path(tmp)
            target = temp_dir / "target.tsv"
            link = temp_dir / "out.tsv"
            target.write_text("", encoding="utf-8")
            try:
                link.symlink_to(target)
            except OSError as err:
                self.skipTest(f"symlink creation unavailable: {err}")
            with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "symlink"):
                gate.write_tsv(link, self.fresh_payload(), self.context)

    def test_json_output_path_escape_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "single-proof.json"
            with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "escapes evidence directory"):
                gate.write_json(outside, self.fresh_payload())

    def test_tsv_output_path_escape_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "single-proof.tsv"
            with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "escapes evidence directory"):
                gate.write_tsv(outside, self.fresh_payload(), self.context)


if __name__ == "__main__":
    unittest.main()
