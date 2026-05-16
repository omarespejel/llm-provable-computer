import copy
import os
import tempfile
import unittest
from pathlib import Path

from scripts import zkai_native_attention_mlp_single_proof_route_gate as gate


class NativeAttentionMlpSingleProofRouteGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = gate.build_context()
        cls.payload = gate.build_payload(cls.context)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_pins_route_budget(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload, context=self.context)
        summary = payload["summary"]
        self.assertEqual(summary["current_two_proof_typed_bytes"], 40_700)
        self.assertEqual(summary["attention_proof_typed_bytes_available_to_remove"], 18_124)
        self.assertEqual(summary["mlp_surface_floor_typed_bytes"], 22_576)
        self.assertEqual(summary["mlp_surface_floor_ratio_vs_two_proof"], 0.554693)
        self.assertEqual(summary["typed_saving_if_mlp_surface_floor_holds_bytes"], 18_124)
        self.assertEqual(summary["typed_saving_if_mlp_surface_floor_holds_share"], 0.445307)
        self.assertEqual(summary["value_connected_chain_extra_rows"], 2_049)
        self.assertEqual(summary["value_connected_chain_to_mlp_row_ratio"], 1.010374)
        self.assertEqual(summary["native_proof_success_threshold_typed_bytes"], 40_700)
        self.assertEqual(summary["nanozk_gap_after_mlp_surface_floor_bytes"], 15_676)
        self.assertEqual(summary["nanozk_reduction_needed_after_mlp_surface_floor_share"], 0.694366)
        self.assertIs(summary["one_native_proof_exists"], False)

    def test_routes_keep_nanozk_and_native_proof_as_non_claims(self) -> None:
        routes = self.fresh_payload()["routes"]
        self.assertEqual(
            routes["native_single_proof_route_budget"]["status"],
            "GO_BUILD_ROUTE_BUT_NO_PROOF_OBJECT_EXISTS_YET",
        )
        self.assertIs(routes["native_single_proof_route_budget"]["one_native_proof_exists"], False)
        self.assertEqual(
            routes["nanozk_comparison_boundary"]["status"],
            "NO_GO_NOT_MATCHED_NANOZK_COMPARISON",
        )
        self.assertIs(routes["nanozk_comparison_boundary"]["matched_workload_or_object_class"], False)

    def test_all_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        cases = payload["mutation_result"]["cases"]
        self.assertEqual(payload["mutation_inventory"]["cases"], list(gate.MUTATION_NAMES))
        self.assertEqual(len(cases), len(gate.MUTATION_NAMES))
        self.assertTrue(all(case["rejected"] for case in cases))

    def test_promoting_native_proof_existence_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["routes"]["native_single_proof_route_budget"]["one_native_proof_exists"] = True
        gate.refresh_routes_and_payload(payload)
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofRouteError, "route drift"):
            gate.validate_payload(payload, context=self.context)

    def test_payload_commitment_drift_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofRouteError, "payload commitment drift"):
            gate.validate_payload(payload, context=self.context)

    def test_to_tsv_validates_payload(self) -> None:
        tsv = gate.to_tsv(self.fresh_payload(), self.context)
        expected = (
            "decision\tresult\tcurrent_two_proof_typed_bytes\t"
            "attention_proof_typed_bytes_available_to_remove\tmlp_surface_floor_typed_bytes\t"
            "mlp_surface_floor_ratio_vs_two_proof\tvalue_connected_chain_to_mlp_row_ratio\t"
            "native_proof_success_threshold_typed_bytes\tnanozk_gap_after_mlp_surface_floor_bytes\t"
            "one_native_proof_exists\r\n"
            "GO_ROUTE_BUDGET_FOR_NATIVE_ATTENTION_MLP_SINGLE_PROOF_OBJECT\t"
            "NARROW_CLAIM_IMPLEMENTATION_TARGET_PINNED_NO_NATIVE_PROOF_OBJECT_YET\t"
            "40700\t18124\t22576\t0.554693\t1.010374\t40700\t15676\tFalse\r\n"
        )
        self.assertEqual(tsv, expected)

    def test_written_payload_validates(self) -> None:
        handle = tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix=".tmp-native-attention-mlp-route-written-",
            suffix=".json",
            delete=False,
        )
        path = Path(handle.name)
        handle.close()
        try:
            gate.write_json(path, self.fresh_payload())
            payload = gate.load_json(path, "written route JSON")
            gate.validate_payload(payload, context=self.context)
        finally:
            path.unlink(missing_ok=True)

    def test_output_path_escape_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "route.json"
            with self.assertRaises(gate.attribution_gate.MlpFusionAttributionError):
                gate.attribution_gate.resolve_evidence_output_path(outside, "route JSON")

    def test_source_artifact_read_binds_payload_and_raw_bytes_once(self) -> None:
        handle = tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix=".tmp-native-attention-mlp-route-source-",
            suffix=".json",
            delete=False,
        )
        path = Path(handle.name)
        raw = b'{ "answer": 7, "nested": [1, 2, 3] }\n'
        try:
            handle.write(raw)
            handle.close()
            payload, loaded_raw = gate.read_json_and_raw_bytes(path, "route source")
            self.assertEqual(payload, {"answer": 7, "nested": [1, 2, 3]})
            self.assertEqual(loaded_raw, raw)
        finally:
            handle.close()
            path.unlink(missing_ok=True)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_source_artifact_read_rejects_symlink_source(self) -> None:
        target_handle = tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix=".tmp-native-attention-mlp-route-target-",
            suffix=".json",
            delete=False,
        )
        link_handle = tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix=".tmp-native-attention-mlp-route-link-",
            suffix=".json",
            delete=False,
        )
        target = Path(target_handle.name)
        link = Path(link_handle.name)
        try:
            target_handle.write(b'{"ok": true}\n')
            target_handle.close()
            link_handle.close()
            link.unlink()
            link.symlink_to(target)
            with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofRouteError, "symlink"):
                gate.read_json_and_raw_bytes(link, "linked route source")
        except OSError as err:
            self.skipTest(f"symlink creation unavailable: {err}")
        finally:
            target_handle.close()
            link_handle.close()
            link.unlink(missing_ok=True)
            target.unlink(missing_ok=True)

    def test_source_artifact_read_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "source.json"
            outside.write_text('{"ok": true}\n', encoding="utf-8")
            with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofRouteError, "escapes evidence directory"):
                gate.read_json_and_raw_bytes(outside, "outside route source")


if __name__ == "__main__":
    unittest.main()
