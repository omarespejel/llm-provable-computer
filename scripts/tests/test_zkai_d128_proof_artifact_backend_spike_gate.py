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
        self.assertEqual(payload["summary"]["direct_d128_route"], "NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING")
        self.assertEqual(payload["summary"]["d128_rmsnorm_public_row_route"], "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY")
        self.assertEqual(
            payload["summary"]["d128_rmsnorm_to_projection_bridge_route"],
            "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
        )
        self.assertEqual(payload["summary"]["d128_gate_value_projection_route"], "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY")
        self.assertEqual(payload["summary"]["d128_activation_swiglu_route"], "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY")
        self.assertEqual(payload["summary"]["parameterized_residual_add_route"], "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY")
        self.assertEqual(payload["summary"]["parameterized_full_block_route"], "NO_GO_FULL_BLOCK_SLICES_MISSING")
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))
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
        self.assertNotIn("src/stwo_backend/d128_native_rmsnorm_to_projection_bridge_proof.rs", probe["missing_d128_modules"])
        self.assertNotIn("src/stwo_backend/d128_native_gate_value_projection_proof.rs", probe["missing_d128_modules"])
        self.assertNotIn("src/stwo_backend/d128_native_activation_swiglu_proof.rs", probe["missing_d128_modules"])
        self.assertNotIn("prove_zkai_d128_rmsnorm_to_projection_bridge_envelope", probe["missing_d128_export_symbols"])
        self.assertNotIn("prove_zkai_d128_gate_value_projection_envelope", probe["missing_d128_export_symbols"])
        self.assertNotIn("prove_zkai_d128_activation_swiglu_envelope", probe["missing_d128_export_symbols"])
        self.assertEqual(probe["d128_rmsnorm_public_row"]["status"], "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY")
        self.assertEqual(probe["d128_rmsnorm_public_row"]["present_symbols"], list(GATE.D128_RMSNORM_SYMBOLS))
        self.assertEqual(
            probe["d128_rmsnorm_public_row"]["statement_commitment"],
            GATE.D128_BRIDGE_GATE.SOURCE_RMSNORM_STATEMENT_COMMITMENT,
        )
        self.assertEqual(
            probe["d128_rmsnorm_public_row"]["public_instance_commitment"],
            GATE.D128_BRIDGE_GATE.SOURCE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT,
        )
        self.assertEqual(
            probe["d128_rmsnorm_public_row"]["rmsnorm_output_row_commitment"],
            GATE.D128_BRIDGE_GATE.SOURCE_RMSNORM_OUTPUT_ROW_COMMITMENT,
        )
        self.assertEqual(
            probe["d128_rmsnorm_to_projection_bridge"]["status"],
            "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
        )
        self.assertEqual(
            probe["d128_rmsnorm_to_projection_bridge"]["present_symbols"],
            list(GATE.D128_BRIDGE_SYMBOLS),
        )
        self.assertEqual(
            probe["d128_rmsnorm_to_projection_bridge"]["source_rmsnorm_statement_commitment"],
            probe["d128_rmsnorm_public_row"]["statement_commitment"],
        )
        self.assertEqual(
            probe["d128_rmsnorm_to_projection_bridge"]["source_rmsnorm_public_instance_commitment"],
            probe["d128_rmsnorm_public_row"]["public_instance_commitment"],
        )
        self.assertEqual(
            probe["d128_rmsnorm_to_projection_bridge"]["source_rmsnorm_output_row_commitment"],
            probe["d128_rmsnorm_public_row"]["rmsnorm_output_row_commitment"],
        )
        self.assertFalse(probe["d128_rmsnorm_to_projection_bridge"]["projection_input_relabels_full_output"])
        self.assertEqual(probe["d128_gate_value_projection"]["status"], "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY")
        self.assertEqual(probe["d128_gate_value_projection"]["present_symbols"], list(GATE.D128_GATE_VALUE_SYMBOLS))
        self.assertEqual(
            probe["d128_gate_value_projection"]["source_projection_input_row_commitment"],
            probe["d128_rmsnorm_to_projection_bridge"]["projection_input_row_commitment"],
        )
        gate_value_evidence = GATE.load_json(GATE.D128_GATE_VALUE_EVIDENCE)
        for field in GATE.D128_GATE_VALUE_COMMITMENT_FIELDS:
            self.assertIn(field, probe["d128_gate_value_projection"])
            self.assertEqual(
                probe["d128_gate_value_projection"][field],
                gate_value_evidence[field],
            )
        self.assertFalse(probe["d128_gate_value_projection"]["projection_output_relabels_full_output"])
        self.assertEqual(probe["d128_activation_swiglu"]["status"], "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY")
        self.assertEqual(probe["d128_activation_swiglu"]["present_symbols"], list(GATE.D128_ACTIVATION_SYMBOLS))
        activation_evidence = GATE.load_json(GATE.D128_ACTIVATION_EVIDENCE)
        for field in GATE.D128_ACTIVATION_COMMITMENT_FIELDS:
            self.assertIn(field, probe["d128_activation_swiglu"])
            self.assertEqual(
                probe["d128_activation_swiglu"][field],
                activation_evidence[field],
            )
        self.assertEqual(
            probe["d128_activation_swiglu"]["source_gate_value_projection_output_commitment"],
            probe["d128_gate_value_projection"]["gate_value_projection_output_commitment"],
        )
        self.assertFalse(probe["d128_activation_swiglu"]["hidden_relabels_full_output"])
        self.assertEqual(probe["parameterized_residual_add"]["status"], "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY")
        self.assertEqual(probe["parameterized_residual_add"]["present_symbols"], list(GATE.PARAMETERIZED_RESIDUAL_ADD_SYMBOLS))
        self.assertEqual(probe["missing_parameterized_full_block_symbols"], list(GATE.MISSING_PARAMETERIZED_FULL_BLOCK_SYMBOLS))
        self.assertEqual(len(probe["d64_hardcoded_markers"]), len(GATE.D64_HARDCODE_MARKERS))
        markers = {row["path"]: row["markers"] for row in probe["d64_hardcoded_markers"]}
        self.assertIn("src/stwo_backend/d64_native_rmsnorm_to_projection_bridge_proof.rs", markers)
        self.assertIn(
            "ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION",
            markers["src/stwo_backend/d64_native_rmsnorm_to_projection_bridge_proof.rs"],
        )

    def test_source_probe_runs_full_residual_add_evidence_validator(self) -> None:
        original = GATE.VECTOR_RESIDUAL_GATE.validate_payload

        def reject(_payload: dict) -> None:
            raise GATE.VECTOR_RESIDUAL_GATE.D128VectorResidualAddInputError("simulated residual evidence drift")

        try:
            GATE.VECTOR_RESIDUAL_GATE.validate_payload = reject
            with self.assertRaisesRegex(GATE.D128BackendSpikeError, "residual-add evidence"):
                GATE.build_source_probe()
        finally:
            GATE.VECTOR_RESIDUAL_GATE.validate_payload = original

    def test_source_probe_runs_full_rmsnorm_evidence_validator(self) -> None:
        original = GATE.D128_RMSNORM_GATE.validate_payload

        def reject(_payload: dict) -> None:
            raise GATE.D128_RMSNORM_GATE.D128RmsnormPublicRowInputError("simulated rmsnorm evidence drift")

        try:
            GATE.D128_RMSNORM_GATE.validate_payload = reject
            with self.assertRaisesRegex(GATE.D128BackendSpikeError, "RMSNorm public-row evidence"):
                GATE.build_source_probe()
        finally:
            GATE.D128_RMSNORM_GATE.validate_payload = original

    def test_source_probe_runs_full_gate_value_evidence_validator(self) -> None:
        original = GATE.D128_GATE_VALUE_GATE.validate_payload

        def reject(_payload: dict) -> None:
            raise GATE.D128_GATE_VALUE_GATE.GateValueProjectionInputError("simulated gate/value evidence drift")

        try:
            GATE.D128_GATE_VALUE_GATE.validate_payload = reject
            with self.assertRaisesRegex(GATE.D128BackendSpikeError, "gate/value projection evidence"):
                GATE.build_source_probe()
        finally:
            GATE.D128_GATE_VALUE_GATE.validate_payload = original

    def test_source_probe_runs_full_activation_swiglu_evidence_validator(self) -> None:
        original = GATE.D128_ACTIVATION_GATE.validate_payload

        def reject(_payload: dict) -> None:
            raise GATE.D128_ACTIVATION_GATE.ActivationSwiGluInputError("simulated activation evidence drift")

        try:
            GATE.D128_ACTIVATION_GATE.validate_payload = reject
            with self.assertRaisesRegex(GATE.D128BackendSpikeError, "activation/SwiGLU evidence"):
                GATE.build_source_probe()
        finally:
            GATE.D128_ACTIVATION_GATE.validate_payload = original

    def test_source_probe_runs_full_bridge_evidence_validator(self) -> None:
        original = GATE.D128_BRIDGE_GATE.validate_payload

        def reject(_payload: dict) -> None:
            raise GATE.D128_BRIDGE_GATE.D128BridgeInputError("simulated bridge evidence drift")

        try:
            GATE.D128_BRIDGE_GATE.validate_payload = reject
            with self.assertRaisesRegex(GATE.D128BackendSpikeError, "RMSNorm-to-projection bridge evidence"):
                GATE.build_source_probe()
        finally:
            GATE.D128_BRIDGE_GATE.validate_payload = original

    def test_source_probe_rejects_bridge_evidence_source_binding_drift(self) -> None:
        original = GATE.load_json
        original_validate = GATE.D128_BRIDGE_GATE.validate_payload
        bridge_path = GATE.D128_BRIDGE_EVIDENCE

        def load_with_tampered_bridge(path: pathlib.Path) -> dict:
            payload = original(path)
            if path == bridge_path:
                payload = copy.deepcopy(payload)
                payload["source_rmsnorm_statement_commitment"] = "blake2b-256:" + "33" * 32
            return payload

        try:
            GATE.load_json = load_with_tampered_bridge
            GATE.D128_BRIDGE_GATE.validate_payload = lambda _payload: None
            with self.assertRaisesRegex(GATE.D128BackendSpikeError, "d128 bridge source RMSNorm statement"):
                GATE.build_source_probe()
        finally:
            GATE.load_json = original
            GATE.D128_BRIDGE_GATE.validate_payload = original_validate

    def test_rust_symbol_probe_rejects_comment_only_surfaces(self) -> None:
        self.assertTrue(
            GATE.rust_declares_symbol(
                "pub fn prove_zkai_vector_block_envelope() {}\n",
                "prove_zkai_vector_block_envelope",
            )
        )
        self.assertFalse(
            GATE.rust_declares_symbol(
                "// pub fn prove_zkai_vector_block_envelope() {}\n",
                "prove_zkai_vector_block_envelope",
            )
        )
        self.assertTrue(
            GATE.rust_reexports_symbol(
                "pub use zkai_vector_block_residual_add_proof::{\n"
                "    prove_zkai_vector_block_envelope,\n"
                "};\n",
                "zkai_vector_block_residual_add_proof",
                "prove_zkai_vector_block_envelope",
            )
        )
        self.assertFalse(
            GATE.rust_reexports_symbol(
                "// pub use zkai_vector_block_residual_add_proof::{prove_zkai_vector_block_envelope};\n",
                "zkai_vector_block_residual_add_proof",
                "prove_zkai_vector_block_envelope",
            )
        )

    def test_backend_routes_block_metrics_until_proof_exists(self) -> None:
        routes = {row["route"]: row for row in self.fresh_payload()["backend_routes"]}
        self.assertEqual(routes["existing_d64_slice_chain"]["status"], "GO_ANCHOR_ONLY")
        self.assertEqual(routes["direct_d128_native_modules"]["status"], "NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING")
        self.assertEqual(routes["direct_d128_rmsnorm_public_row_air"]["status"], "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY")
        self.assertTrue(routes["direct_d128_rmsnorm_public_row_air"]["local_roundtrip_proof_constructed"])
        self.assertFalse(routes["direct_d128_rmsnorm_public_row_air"]["checked_in_proof_artifact_exists"])
        self.assertEqual(
            routes["direct_d128_rmsnorm_to_projection_bridge_air"]["status"],
            "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
        )
        self.assertTrue(routes["direct_d128_rmsnorm_to_projection_bridge_air"]["local_roundtrip_proof_constructed"])
        self.assertFalse(routes["direct_d128_rmsnorm_to_projection_bridge_air"]["checked_in_proof_artifact_exists"])
        self.assertEqual(routes["direct_d128_gate_value_projection_air"]["status"], "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY")
        self.assertTrue(routes["direct_d128_gate_value_projection_air"]["local_roundtrip_proof_constructed"])
        self.assertFalse(routes["direct_d128_gate_value_projection_air"]["checked_in_proof_artifact_exists"])
        self.assertEqual(routes["direct_d128_activation_swiglu_air"]["status"], "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY")
        self.assertTrue(routes["direct_d128_activation_swiglu_air"]["local_roundtrip_proof_constructed"])
        self.assertFalse(routes["direct_d128_activation_swiglu_air"]["checked_in_proof_artifact_exists"])
        self.assertEqual(routes["lift_existing_d64_modules_by_metadata"]["status"], "NO_GO")
        self.assertEqual(routes["parameterized_vector_residual_add_air"]["status"], "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY")
        self.assertTrue(routes["parameterized_vector_residual_add_air"]["local_roundtrip_proof_constructed"])
        self.assertFalse(routes["parameterized_vector_residual_add_air"]["checked_in_proof_artifact_exists"])
        self.assertEqual(routes["parameterized_transformer_block_air"]["status"], "NO_GO_FULL_BLOCK_SLICES_MISSING")
        self.assertEqual(routes["d128_metrics_and_relabeling_suite"]["status"], "NO_GO_BLOCKED_BEFORE_PROOF_OBJECT")
        for name, row in routes.items():
            self.assertIsNone(row["proof_size_bytes"], name)
            self.assertIsNone(row["verifier_time_ms"], name)

    def test_proof_status_records_toolchain_and_no_metrics(self) -> None:
        status = self.fresh_payload()["proof_status"]
        self.assertFalse(status["proof_artifact_exists"])
        self.assertFalse(status["verifier_handle_exists"])
        self.assertTrue(status["partial_d128_rmsnorm_public_row_proof_exists"])
        self.assertTrue(status["partial_d128_rmsnorm_public_row_verifier_exists"])
        self.assertTrue(status["partial_d128_rmsnorm_public_row_local_roundtrip_proof_constructed"])
        self.assertFalse(status["partial_d128_rmsnorm_public_row_checked_in_proof_artifact_exists"])
        self.assertTrue(status["partial_d128_rmsnorm_to_projection_bridge_proof_exists"])
        self.assertTrue(status["partial_d128_rmsnorm_to_projection_bridge_verifier_exists"])
        self.assertTrue(status["partial_d128_rmsnorm_to_projection_bridge_local_roundtrip_proof_constructed"])
        self.assertFalse(status["partial_d128_rmsnorm_to_projection_bridge_checked_in_proof_artifact_exists"])
        self.assertTrue(status["partial_d128_gate_value_projection_proof_exists"])
        self.assertTrue(status["partial_d128_gate_value_projection_verifier_exists"])
        self.assertTrue(status["partial_d128_gate_value_projection_local_roundtrip_proof_constructed"])
        self.assertFalse(status["partial_d128_gate_value_projection_checked_in_proof_artifact_exists"])
        self.assertTrue(status["partial_d128_activation_swiglu_proof_exists"])
        self.assertTrue(status["partial_d128_activation_swiglu_verifier_exists"])
        self.assertTrue(status["partial_d128_activation_swiglu_local_roundtrip_proof_constructed"])
        self.assertFalse(status["partial_d128_activation_swiglu_checked_in_proof_artifact_exists"])
        self.assertTrue(status["partial_parameterized_residual_add_proof_exists"])
        self.assertTrue(status["partial_parameterized_residual_add_verifier_exists"])
        self.assertTrue(status["partial_parameterized_residual_add_local_roundtrip_proof_constructed"])
        self.assertFalse(status["partial_parameterized_residual_add_checked_in_proof_artifact_exists"])
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

    def test_rejects_bridge_source_statement_binding_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_probe"]["d128_rmsnorm_to_projection_bridge"][
            "source_rmsnorm_statement_commitment"
        ] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "bridge source RMSNorm statement"):
            GATE.validate_payload(payload)

    def test_rejects_bridge_route_source_binding_drift(self) -> None:
        payload = self.fresh_payload()
        route = next(row for row in payload["backend_routes"] if row["route"] == "direct_d128_rmsnorm_to_projection_bridge_air")
        route["source_rmsnorm_public_instance_commitment"] = "blake2b-256:" + "22" * 32
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "route source public-instance"):
            GATE.validate_payload(payload)

    def test_rejects_bridge_route_projection_input_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        route = next(
            row for row in payload["backend_routes"] if row["route"] == "direct_d128_rmsnorm_to_projection_bridge_air"
        )
        route["projection_input_row_commitment"] = "blake2b-256:" + "44" * 32
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "route projection-input commitment"):
            GATE.validate_payload(payload)

    def test_rejects_bridge_route_projection_input_relabeling(self) -> None:
        payload = self.fresh_payload()
        route = next(
            row for row in payload["backend_routes"] if row["route"] == "direct_d128_rmsnorm_to_projection_bridge_air"
        )
        payload["source_probe"]["d128_rmsnorm_to_projection_bridge"][
            "projection_input_row_commitment"
        ] = GATE.D128_BRIDGE_GATE.FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT
        route["projection_input_row_commitment"] = GATE.D128_BRIDGE_GATE.FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "authoritative projection-input commitment"):
            GATE.validate_payload(payload)

    def test_rejects_malformed_equal_bridge_projection_commitments(self) -> None:
        payload = self.fresh_payload()
        route = next(
            row for row in payload["backend_routes"] if row["route"] == "direct_d128_rmsnorm_to_projection_bridge_air"
        )
        payload["source_probe"]["d128_rmsnorm_to_projection_bridge"][
            "projection_input_row_commitment"
        ] = "not-a-commitment"
        route["projection_input_row_commitment"] = "not-a-commitment"
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "projection-input commitment"):
            GATE.validate_payload(payload)

    def test_rejects_equal_but_unpinned_bridge_projection_commitments(self) -> None:
        payload = self.fresh_payload()
        route = next(
            row for row in payload["backend_routes"] if row["route"] == "direct_d128_rmsnorm_to_projection_bridge_air"
        )
        alternate = "blake2b-256:" + "55" * 32
        payload["source_probe"]["d128_rmsnorm_to_projection_bridge"][
            "projection_input_row_commitment"
        ] = alternate
        route["projection_input_row_commitment"] = alternate
        GATE.set_gate_commitment(payload)
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "authoritative projection-input commitment"):
            GATE.validate_payload(payload)

    def test_rejects_route_promotion(self) -> None:
        payload = self.fresh_payload()
        route = next(row for row in payload["backend_routes"] if row["route"] == "parameterized_transformer_block_air")
        route["status"] = "GO"
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "parameterized full-block route status"):
            GATE.validate_payload(payload)

    def test_rejects_activation_source_binding_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_probe"]["d128_activation_swiglu"][
            "source_gate_value_projection_statement_commitment"
        ] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "activation/SwiGLU source gate/value statement"):
            GATE.validate_payload(payload)

    def test_rejects_activation_source_output_binding_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_probe"]["d128_activation_swiglu"][
            "source_gate_value_projection_output_commitment"
        ] = "blake2b-256:" + "88" * 32
        route = next(row for row in payload["backend_routes"] if row["route"] == "direct_d128_activation_swiglu_air")
        route["source_gate_value_projection_output_commitment"] = "blake2b-256:" + "88" * 32
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "activation/SwiGLU source gate/value output"):
            GATE.validate_payload(payload)

    def test_rejects_activation_source_projection_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_probe"]["d128_activation_swiglu"][
            "source_gate_projection_output_commitment"
        ] = "blake2b-256:" + "89" * 32
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "source_gate_projection_output_commitment"):
            GATE.validate_payload(payload)

    def test_rejects_activation_row_metadata_drift(self) -> None:
        for field, pattern in [
            ("row_count", "row count"),
            ("activation_lookup_rows", "activation lookup rows"),
            ("swiglu_mix_rows", "swiglu mix rows"),
        ]:
            payload = self.fresh_payload()
            payload["source_probe"]["d128_activation_swiglu"][field] = 1
            with self.subTest(field=field):
                with self.assertRaisesRegex(GATE.D128BackendSpikeError, pattern):
                    GATE.validate_payload(payload)

    def test_rejects_activation_route_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        route = next(row for row in payload["backend_routes"] if row["route"] == "direct_d128_activation_swiglu_air")
        route["hidden_activation_commitment"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "activation/SwiGLU route hidden"):
            GATE.validate_payload(payload)

    def test_rejects_activation_hidden_full_output_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["source_probe"]["d128_activation_swiglu"][
            "hidden_activation_commitment"
        ] = GATE.D128_ACTIVATION_GATE.OUTPUT_ACTIVATION_COMMITMENT
        payload["source_probe"]["d128_activation_swiglu"]["hidden_relabels_full_output"] = True
        route = next(row for row in payload["backend_routes"] if row["route"] == "direct_d128_activation_swiglu_air")
        route["hidden_activation_commitment"] = GATE.D128_ACTIVATION_GATE.OUTPUT_ACTIVATION_COMMITMENT
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "hidden relabel guard"):
            GATE.validate_payload(payload)

    def test_rejects_removed_missing_module(self) -> None:
        payload = self.fresh_payload()
        payload["source_probe"]["missing_d128_modules"] = payload["source_probe"]["missing_d128_modules"][1:]
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "missing d128 module"):
            GATE.validate_payload(payload)

    def test_rejects_removed_non_claim(self) -> None:
        payload = self.fresh_payload()
        payload["non_claims"].remove("not a full local d128 transformer-block proof artifact")
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "non-claims"):
            GATE.validate_payload(payload)

    def test_gate_commitment_rejects_saved_artifact_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_probe"]["d64_slices"][0]["evidence"]["payload_sha256"] = "0" * 64
        with self.assertRaisesRegex(GATE.D128BackendSpikeError, "gate commitment"):
            GATE.validate_payload(payload)

    def test_mutation_layers_cover_routes_sources_and_metrics(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        self.assertEqual(cases["decision_promoted_to_go"]["rejection_layer"], "top_level")
        self.assertEqual(cases["direct_d128_route_promoted"]["rejection_layer"], "backend_routes")
        self.assertEqual(cases["d128_rmsnorm_to_projection_bridge_route_promoted"]["rejection_layer"], "backend_routes")
        self.assertEqual(cases["d128_gate_value_projection_route_promoted"]["rejection_layer"], "backend_routes")
        self.assertEqual(cases["d128_activation_swiglu_route_promoted"]["rejection_layer"], "backend_routes")
        self.assertEqual(
            cases["d128_gate_value_projection_statement_commitment_drift"]["rejection_layer"],
            "source_probe",
        )
        self.assertEqual(
            cases["d128_gate_value_projection_route_statement_commitment_drift"]["rejection_layer"],
            "backend_routes",
        )
        self.assertEqual(
            cases["d128_activation_swiglu_statement_commitment_drift"]["rejection_layer"],
            "source_probe",
        )
        self.assertEqual(
            cases["d128_activation_swiglu_source_output_commitment_drift"]["rejection_layer"],
            "source_probe",
        )
        self.assertEqual(
            cases["d128_activation_swiglu_source_gate_projection_output_commitment_drift"]["rejection_layer"],
            "source_probe",
        )
        self.assertEqual(
            cases["d128_activation_swiglu_source_value_projection_output_commitment_drift"]["rejection_layer"],
            "source_probe",
        )
        self.assertEqual(
            cases["d128_activation_swiglu_hidden_relabels_full_output"]["rejection_layer"],
            "source_probe",
        )
        self.assertEqual(
            cases["d128_activation_swiglu_route_statement_commitment_drift"]["rejection_layer"],
            "backend_routes",
        )
        self.assertEqual(cases["full_block_parameterized_route_promoted"]["rejection_layer"], "backend_routes")
        self.assertEqual(cases["missing_module_removed"]["rejection_layer"], "source_probe")
        self.assertEqual(cases["proof_size_metric_smuggled"]["rejection_layer"], "metrics")
        for case in cases.values():
            self.assertTrue(case["rejected"])
            self.assertFalse(case["mutated_accepted"])
            self.assertTrue(case["error"])

    def test_mutation_harness_raises_on_unexpected_validator_bug(self) -> None:
        payload = self.fresh_payload()
        original_validate_payload = GATE.validate_payload

        def bugged_validate_payload(_payload: dict, *, require_mutations: bool = True) -> None:
            raise KeyError("unexpected-validator-bug")

        try:
            GATE.validate_payload = bugged_validate_payload
            with self.assertRaisesRegex(RuntimeError, "mutation harness failed"):
                GATE.mutation_cases(payload)
        finally:
            GATE.validate_payload = original_validate_payload

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
            self.assertEqual(tsv[len(payload["backend_routes"]) + 2].split("\t"), list(GATE.MUTATION_TSV_COLUMNS))

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

    def test_write_outputs_rejects_symlink_outputs_inside_repo(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            target = tmp / "target.json"
            target.write_text("existing\n", encoding="utf-8")
            symlink = tmp / "linked.json"
            symlink.symlink_to(target)
            with self.assertRaisesRegex(GATE.D128BackendSpikeError, "symlink"):
                GATE.write_outputs(payload, symlink, None)
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")

    def test_atomic_write_cleans_temp_file_when_replace_fails(self) -> None:
        original_replace = GATE.os.replace
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            out = tmp / "out.json"

            def fail_replace(_src: pathlib.Path, _dst: pathlib.Path) -> None:
                raise OSError("simulated replace failure")

            try:
                GATE.os.replace = fail_replace
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    GATE._atomic_write_text(out, "payload\n")
                leftovers = [path for path in tmp.iterdir() if path.name != "out.json"]
                self.assertEqual(leftovers, [])
                self.assertFalse(out.exists())
            finally:
                GATE.os.replace = original_replace

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
