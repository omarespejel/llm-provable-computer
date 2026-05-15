import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "zkai_attention_derived_d128_native_mlp_proof_route_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_native_mlp_proof_route_gate", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load {SCRIPT}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionDerivedD128NativeMlpProofRouteGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = GATE.build_context()
        self.payload = GATE.build_gate_result()

    def test_records_native_route_no_go_without_weakening_existing_mlp_result(self) -> None:
        summary = self.payload["summary"]
        self.assertEqual(
            self.payload["decision"],
            "NO_GO_ATTENTION_DERIVED_D128_NATIVE_MLP_FUSED_PROOF_NOT_REGENERATED",
        )
        self.assertEqual(summary["value_connected_chain_rows"], 199_553)
        self.assertEqual(summary["current_mlp_fused_rows"], 197_504)
        self.assertEqual(summary["row_ratio"], 1.010374)
        self.assertEqual(summary["current_mlp_fused_typed_bytes"], 24_832)
        self.assertEqual(summary["current_mlp_typed_saving_vs_separate_bytes"], 32_144)
        self.assertEqual(summary["current_mlp_typed_saving_ratio_vs_separate"], 0.564167)

    def test_keeps_derived_and_current_input_commitments_separate(self) -> None:
        summary = self.payload["summary"]
        self.assertEqual(
            summary["derived_input_activation_commitment"],
            "blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35",
        )
        self.assertEqual(
            summary["current_mlp_input_activation_commitment"],
            "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78",
        )
        self.assertFalse(self.payload["comparison"]["current_native_fused_proof_can_be_reused_for_derived_input"])

    def test_binds_current_mlp_input_and_envelope_commitments(self) -> None:
        comparison = self.payload["comparison"]
        self.assertEqual(
            comparison["current_mlp_fused_envelope_input_activation_commitment"],
            comparison["current_mlp_input_activation_commitment"],
        )
        context = copy.deepcopy(self.context)
        context["comparison"]["current_mlp_fused_envelope_input_activation_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(
            GATE.NativeMlpProofRouteError,
            "current MLP envelope/input activation commitment mismatch",
        ):
            GATE.build_core_payload(context)

    def test_only_first_component_is_currently_native_input_shape(self) -> None:
        rows = {row["component_id"]: row for row in self.payload["component_input_frontier"]}
        self.assertEqual(rows["rmsnorm_public_rows"]["native_component_input_status"], "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE")
        self.assertEqual(rows["rmsnorm_projection_bridge"]["native_component_input_status"], "NO_GO_NOT_CURRENT_NATIVE_COMPONENT_INPUT")
        self.assertEqual(rows["gate_value_projection"]["native_component_input_status"], "NO_GO_NOT_CURRENT_NATIVE_COMPONENT_INPUT")
        self.assertEqual(rows["activation_swiglu"]["native_component_input_status"], "NO_GO_NOT_CURRENT_NATIVE_COMPONENT_INPUT")
        self.assertEqual(rows["down_projection"]["native_component_input_status"], "NO_GO_NOT_CURRENT_NATIVE_COMPONENT_INPUT")
        self.assertEqual(rows["residual_add"]["native_component_input_status"], "NO_GO_NOT_CURRENT_NATIVE_COMPONENT_INPUT")
        self.assertEqual(self.payload["summary"]["native_compatible_components"], 1)
        self.assertEqual(self.payload["summary"]["native_incompatible_components"], 5)

    def test_pins_missing_native_attention_derived_artifacts(self) -> None:
        missing = self.payload["missing_native_artifacts"]
        self.assertEqual(len(missing), 3)
        for artifact in missing:
            self.assertTrue(artifact["required_for_go"])
            self.assertFalse(artifact["exists"])
            self.assertEqual(
                artifact["status"],
                "MISSING_REQUIRED_NATIVE_ATTENTION_DERIVED_PROOF_ARTIFACT",
            )

    def test_rejects_zero_current_mlp_rows_before_ratio(self) -> None:
        context = copy.deepcopy(self.context)
        context["comparison"]["current_mlp_fused_rows"] = 0
        with self.assertRaisesRegex(GATE.NativeMlpProofRouteError, "current MLP fused rows must be positive"):
            GATE.build_core_payload(context)

    def test_mutations_rejected(self) -> None:
        self.assertTrue(self.payload["all_mutations_rejected"])
        self.assertEqual(self.payload["case_count"], len(GATE.EXPECTED_MUTATIONS))
        self.assertEqual([case["name"] for case in self.payload["cases"]], list(GATE.EXPECTED_MUTATIONS))
        self.assertTrue(all(case["rejected"] and not case["accepted"] for case in self.payload["cases"]))

    def test_rejects_current_proof_reuse_overclaim(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["comparison"]["current_native_fused_proof_can_be_reused_for_derived_input"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.NativeMlpProofRouteError, "payload content drift|current proof reuse overclaim"):
            GATE.validate_payload(payload, context=self.context)

    def test_rejects_native_route_promotion(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["native_route_status"] = "GO_NATIVE_ROUTE"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.NativeMlpProofRouteError, "native route status drift"):
            GATE.validate_payload(payload, context=self.context)

    def test_rejects_missing_artifact_relabeling(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["missing_native_artifacts"][0]["exists"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.NativeMlpProofRouteError, "payload content drift|missing native artifact"):
            GATE.validate_payload(payload, context=self.context)

    def test_tsv_output(self) -> None:
        tsv = GATE.to_tsv(self.payload, context=self.context)
        self.assertIn("native_incompatible_components", tsv.splitlines()[0])
        self.assertIn("\t5", tsv.splitlines()[1])

    def test_written_payload_round_trip(self) -> None:
        tmp_root = ROOT / "docs" / "engineering" / "evidence"
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            json_path = pathlib.Path(tmp) / "native-mlp-route.json"
            tsv_path = pathlib.Path(tmp) / "native-mlp-route.tsv"
            GATE.write_outputs(self.payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text())
            GATE.validate_payload(loaded, context=self.context)
            self.assertTrue(tsv_path.read_text().startswith("decision\tresult"))


if __name__ == "__main__":
    unittest.main()
