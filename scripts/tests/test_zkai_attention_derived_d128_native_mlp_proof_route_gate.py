import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


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

    def test_records_native_route_go_without_weakening_existing_mlp_result(self) -> None:
        summary = self.payload["summary"]
        self.assertEqual(
            self.payload["decision"],
            "GO_ATTENTION_DERIVED_D128_NATIVE_MLP_FUSED_PROOF_REGENERATED",
        )
        self.assertEqual(summary["value_connected_chain_rows"], 199_553)
        self.assertEqual(summary["current_mlp_fused_rows"], 197_504)
        self.assertEqual(summary["row_ratio"], 1.010374)
        self.assertEqual(summary["current_mlp_fused_typed_bytes"], 24_832)
        self.assertEqual(summary["current_mlp_typed_saving_vs_separate_bytes"], 32_144)
        self.assertEqual(summary["current_mlp_typed_saving_ratio_vs_separate"], 0.564167)
        self.assertEqual(summary["derived_fused_proof_bytes"], 68_560)
        self.assertEqual(summary["derived_fused_envelope_bytes"], 716_944)
        self.assertEqual(summary["derived_fused_typed_bytes"], 22_576)
        self.assertEqual(summary["available_separate_component_count"], 4)
        self.assertEqual(summary["available_separate_typed_bytes"], 46_208)
        self.assertEqual(summary["typed_saving_vs_available_separate_bytes"], 23_632)
        self.assertEqual(summary["typed_ratio_vs_available_separate"], 0.488573)

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

    def test_all_six_components_are_currently_native_input_shape(self) -> None:
        rows = {row["component_id"]: row for row in self.payload["component_input_frontier"]}
        self.assertEqual(rows["rmsnorm_public_rows"]["native_component_input_status"], "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE")
        self.assertEqual(rows["rmsnorm_projection_bridge"]["native_component_input_status"], "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE")
        self.assertEqual(rows["gate_value_projection"]["native_component_input_status"], "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE")
        self.assertEqual(rows["activation_swiglu"]["native_component_input_status"], "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE")
        self.assertEqual(rows["down_projection"]["native_component_input_status"], "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE")
        self.assertEqual(rows["residual_add"]["native_component_input_status"], "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE")
        self.assertEqual(self.payload["summary"]["native_compatible_components"], 6)
        self.assertEqual(self.payload["summary"]["native_incompatible_components"], 0)

    def test_binds_derived_native_activation_proof_envelope(self) -> None:
        summary = self.payload["summary"]
        self.assertEqual(summary["derived_native_activation_proof_bytes"], 24_455)
        self.assertEqual(summary["derived_native_activation_envelope_bytes"], 227_031)
        self.assertEqual(
            summary["derived_native_activation_hidden_commitment"],
            "blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4",
        )

    def test_binds_derived_native_down_projection_proof_envelope(self) -> None:
        summary = self.payload["summary"]
        self.assertEqual(summary["derived_native_down_proof_bytes"], 58_151)
        self.assertEqual(summary["derived_native_down_envelope_bytes"], 480_346)
        self.assertEqual(
            summary["derived_native_down_residual_delta_commitment"],
            "blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec",
        )
        self.assertEqual(
            summary["derived_native_down_statement_commitment"],
            "blake2b-256:3ca2a06054a8ae8a9526bce62a4bc3a91e6f302fc3cb4866d7e2dc2afbf5f23e",
        )

    def test_binds_derived_native_residual_add_proof_envelope(self) -> None:
        summary = self.payload["summary"]
        self.assertEqual(summary["derived_native_residual_proof_bytes"], 16_042)
        self.assertEqual(summary["derived_native_residual_envelope_bytes"], 155_655)
        self.assertEqual(
            summary["derived_native_residual_output_commitment"],
            "blake2b-256:25feb3aa6a2a092602c86d10c767f71cdae3c60eade0254a2d121124b712bcf9",
        )
        self.assertEqual(
            summary["derived_native_residual_statement_commitment"],
            "blake2b-256:106bf2581e2588d8ed28f31d93438ba0f546a752d743bea533df8640a6048c5d",
        )

    def test_rejects_coordinated_residual_statement_drift(self) -> None:
        original_load_json = GATE._load_json
        drifted_statement = "blake2b-256:" + "22" * 32

        def load_with_coordinated_drift(path: pathlib.Path, label: str):
            payload, raw = original_load_json(path, label)
            if path == GATE.DERIVED_NATIVE_RESIDUAL:
                payload = dict(payload)
                payload["statement_commitment"] = drifted_statement
            if path == GATE.DERIVED_NATIVE_RESIDUAL_ENVELOPE:
                payload = dict(payload)
                input_payload = dict(payload["input"])
                input_payload["statement_commitment"] = drifted_statement
                payload["input"] = input_payload
            return payload, raw

        with mock.patch.object(GATE, "_load_json", side_effect=load_with_coordinated_drift):
            with self.assertRaisesRegex(
                GATE.NativeMlpProofRouteError,
                "derived native residual statement_commitment drift",
            ):
                GATE.build_context()

    def test_rejects_coordinated_activation_down_statement_drift(self) -> None:
        original_load_json = GATE._load_json
        drifted_statement = "blake2b-256:" + "11" * 32

        def load_with_coordinated_drift(path: pathlib.Path, label: str):
            payload, raw = original_load_json(path, label)
            if path == GATE.DERIVED_NATIVE_ACTIVATION:
                payload = dict(payload)
                payload["statement_commitment"] = drifted_statement
            if path == GATE.DERIVED_NATIVE_ACTIVATION_ENVELOPE:
                payload = dict(payload)
                input_payload = dict(payload["input"])
                input_payload["statement_commitment"] = drifted_statement
                payload["input"] = input_payload
            if path == GATE.DERIVED_NATIVE_DOWN:
                payload = dict(payload)
                payload["source_activation_swiglu_statement_commitment"] = drifted_statement
            if path == GATE.DERIVED_NATIVE_DOWN_ENVELOPE:
                payload = dict(payload)
                input_payload = dict(payload["input"])
                input_payload["source_activation_swiglu_statement_commitment"] = drifted_statement
                payload["input"] = input_payload
            return payload, raw

        with mock.patch.object(GATE, "_load_json", side_effect=load_with_coordinated_drift):
            with self.assertRaisesRegex(
                GATE.NativeMlpProofRouteError,
                "derived native activation statement_commitment drift",
            ):
                GATE.build_context()

    def test_pins_required_fused_artifacts_and_missing_matched_baseline(self) -> None:
        required = self.payload["required_derived_fused_artifacts"]
        self.assertEqual(len(required), 3)
        for artifact in required:
            self.assertTrue(artifact["required_for_go"])
            self.assertTrue(artifact["exists"])
            self.assertEqual(
                artifact["status"],
                "PRESENT_REQUIRED_NATIVE_ATTENTION_DERIVED_FUSED_PROOF_ARTIFACT",
            )
        missing = self.payload["missing_matched_separate_envelopes"]
        self.assertEqual(len(missing), 2)
        for artifact in missing:
            self.assertTrue(artifact["required_for_complete_six_separate_baseline"])
            self.assertFalse(artifact["exists"])
            self.assertEqual(artifact["status"], "MISSING_MATCHED_DERIVED_SEPARATE_COMPONENT_ENVELOPE")

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

    def test_rejects_required_artifact_and_matched_baseline_relabeling(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["required_derived_fused_artifacts"][0]["exists"] = False
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.NativeMlpProofRouteError, "payload content drift|required derived fused artifact"):
            GATE.validate_payload(payload, context=self.context)
        payload = copy.deepcopy(self.payload)
        payload["missing_matched_separate_envelopes"][0]["exists"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.NativeMlpProofRouteError, "payload content drift|matched separate envelope"):
            GATE.validate_payload(payload, context=self.context)

    def test_tsv_output(self) -> None:
        tsv = GATE.to_tsv(self.payload, context=self.context)
        self.assertIn("native_incompatible_components", tsv.splitlines()[0])
        self.assertTrue(tsv.splitlines()[1].endswith("\t6\t0\t24455\t227031\t58151\t480346\t16042\t155655"))

    def test_written_payload_round_trip(self) -> None:
        tmp_root = ROOT / "docs" / "engineering" / "evidence"
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            json_path = pathlib.Path(tmp) / "native-mlp-route.json"
            tsv_path = pathlib.Path(tmp) / "native-mlp-route.tsv"
            GATE.write_outputs(self.payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text())
            GATE.validate_payload(loaded, context=self.context)
            self.assertTrue(tsv_path.read_text().startswith("decision\tresult"))

    def test_atomic_write_does_not_follow_old_deterministic_temp_symlink(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        tmp_root = ROOT / "docs" / "engineering" / "evidence"
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            tmp_path = pathlib.Path(tmp)
            target = tmp_path / "native-mlp-route.json"
            text = GATE.pretty_json(self.payload) + "\n"
            old_tmp = target.with_name(
                f".{target.name}.{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}.tmp"
            )
            redirected = tmp_path / "redirected.txt"
            redirected.write_text("do-not-touch", encoding="utf-8")
            try:
                old_tmp.symlink_to(redirected)
            except OSError as err:
                self.skipTest(f"symlink creation unavailable: {err}")
            GATE.atomic_write(target, text)
            self.assertEqual(redirected.read_text(encoding="utf-8"), "do-not-touch")
            self.assertEqual(target.read_text(encoding="utf-8"), text)

    def test_atomic_write_cleanup_does_not_mask_replace_error(self) -> None:
        tmp_root = ROOT / "docs" / "engineering" / "evidence"
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            target = pathlib.Path(tmp) / "native-mlp-route.json"
            text = GATE.pretty_json(self.payload) + "\n"
            with (
                mock.patch.object(GATE.os, "replace", side_effect=RuntimeError("replace failed")),
                mock.patch.object(GATE.pathlib.Path, "unlink", side_effect=OSError("cleanup failed")),
            ):
                with self.assertRaisesRegex(RuntimeError, "replace failed"):
                    GATE.atomic_write(target, text)


if __name__ == "__main__":
    unittest.main()
