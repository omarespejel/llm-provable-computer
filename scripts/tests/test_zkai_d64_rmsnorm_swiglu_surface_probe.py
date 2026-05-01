from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_swiglu_surface_probe.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_rmsnorm_swiglu_surface_probe", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d64 surface probe from {SCRIPT_PATH}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class ZkAID64RMSNormSwiGLUSurfaceProbeTests(unittest.TestCase):
    def test_d64_target_estimates_are_pinned(self) -> None:
        target = PROBE.d64_target()

        self.assertEqual(target["width"], 64)
        self.assertEqual(target["ff_dim"], 256)
        self.assertEqual(target["estimated_linear_muls"], 49_152)
        self.assertEqual(target["estimated_weight_scalars"], 49_152)
        self.assertEqual(target["required_proof_backend_version"], "stwo-rmsnorm-swiglu-residual-d64-v1")
        self.assertIn("weight_commitment", target["minimum_public_statement_bindings"])

    def test_scans_current_tvm_limits_from_source(self) -> None:
        limits = PROBE.scan_tvm_limits()

        self.assertTrue(limits["limits_are_current"])
        self.assertTrue(limits["pc_u8_detected"])
        self.assertTrue(limits["address_u8_detected"])
        self.assertTrue(limits["immediate_i16_detected"])
        self.assertEqual(limits["max_addressable_memory_cells"], 255)
        self.assertEqual(limits["pc_horizon"], 256)

    def test_scans_current_prover_fixture_gates_from_source(self) -> None:
        gates = PROBE.scan_prover_gates()

        self.assertTrue(gates["fixture_gate_detected"])
        self.assertFalse(gates["required_backend_version_present"])
        self.assertTrue(gates["markers"]["phase12_decoding_only"])
        self.assertTrue(gates["markers"]["broader_arithmetic_subset_internal"])

    def test_fixture_profile_is_pinned(self) -> None:
        profile = PROBE.fixture_profile()

        self.assertEqual(profile["memory_cells"], 21)
        self.assertEqual(profile["instruction_count"], 43)
        self.assertEqual(profile["mul_memory_ops"], 7)

    def test_payload_records_direct_tvm_lowering_no_go(self) -> None:
        with mock.patch.dict(os.environ, {"ZKAI_GIT_COMMIT": "test-commit"}, clear=True):
            payload = PROBE.build_payload()

        self.assertEqual(payload["schema"], PROBE.SCHEMA)
        self.assertEqual(payload["generated_at"], "1970-01-01T00:00:00Z")
        self.assertEqual(payload["decision"], PROBE.DECISION_NO_GO)
        self.assertEqual(payload["summary"]["direct_fixture_growth"], "NO_GO")
        self.assertEqual(payload["target"]["estimated_linear_muls"], 49_152)
        self.assertEqual(payload["current_tvm_limits"]["max_addressable_memory_cells"], 255)
        self.assertEqual(payload["current_tvm_limits"]["pc_horizon"], 256)

        blocker_ids = {blocker["id"] for blocker in payload["classification"]["blockers"]}
        self.assertIn("weight_surface_exceeds_u8_memory_addressing", blocker_ids)
        self.assertIn("unrolled_mul_surface_exceeds_u8_pc_horizon", blocker_ids)
        self.assertIn("current_fixture_is_toy_width", blocker_ids)
        self.assertIn("missing_parameterized_stwo_backend", blocker_ids)
        self.assertIn("carry_aware_lane_is_decoding_family_only", blocker_ids)

    def test_classifier_can_report_go_for_synthetic_parameterized_surface(self) -> None:
        target = PROBE.d64_target()
        limits = {
            "limits_are_current": True,
            "max_addressable_memory_cells": 65_536,
            "pc_horizon": 65_536,
        }
        gates = {
            "fixture_gate_detected": False,
            "required_backend_version_present": True,
            "markers": {"phase12_decoding_only": False},
        }
        fixture = {
            "memory_cells": 65_536,
            "instruction_count": 49_153,
            "mul_memory_ops": 49_152,
        }

        row = PROBE.classify_surface(target, limits, gates, fixture)

        self.assertEqual(row["status"], PROBE.DECISION_GO)
        self.assertEqual(row["blockers"], [])

    def test_scan_tvm_limits_fails_closed_when_markers_are_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            instruction = tmp / "instruction.rs"
            state = tmp / "state.rs"
            instruction.write_text("enum Instruction { Load(usize) }\n", encoding="utf-8")
            state.write_text("pub struct MachineState { pub pc: usize }\n", encoding="utf-8")

            limits = PROBE.scan_tvm_limits(instruction_path=instruction, state_path=state)

        self.assertFalse(limits["limits_are_current"])
        self.assertFalse(limits["pc_u8_detected"])
        self.assertFalse(limits["address_u8_detected"])

    def test_scan_prover_gates_fails_closed_when_markers_are_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            source = tmp / "arithmetic_subset_prover.rs"
            source.write_text("fn validate_phase5_proven_fixture() {}\n", encoding="utf-8")

            gates = PROBE.scan_prover_gates(source)

        self.assertFalse(gates["fixture_gate_detected"])
        self.assertTrue(gates["markers"]["fixture_gate_function"])
        self.assertFalse(gates["markers"]["linear_block_v4_exact_matcher"])

    def test_fixture_profile_rejects_missing_memory_directive(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = pathlib.Path(raw_tmp) / "bad.tvm"
            path.write_text("LOAD 0\nHALT\n", encoding="utf-8")

            with self.assertRaisesRegex(PROBE.SurfaceProbeError, "memory"):
                PROBE.fixture_profile(path)

    def test_tsv_rows_are_stable(self) -> None:
        payload = {
            "decision": PROBE.DECISION_NO_GO,
            "target": PROBE.d64_target(),
            "current_tvm_limits": {
                "max_addressable_memory_cells": 255,
                "pc_horizon": 256,
            },
            "current_fixture_profile": {
                "memory_cells": 21,
                "instruction_count": 43,
                "mul_memory_ops": 7,
            },
            "classification": {
                "weight_cells_over_memory_limit": 49_152 / 255,
                "mul_ops_over_pc_horizon": 49_152 / 256,
                "blockers": [{"id": "a"}, {"id": "b"}],
            },
        }

        rows = PROBE.rows_for_tsv(payload)

        self.assertEqual(rows[0]["target_width"], 64)
        self.assertEqual(rows[0]["weight_cells_over_memory_limit"], "192.753")
        self.assertEqual(rows[0]["mul_ops_over_pc_horizon"], "192.000")
        self.assertEqual(rows[0]["blocker_count"], 2)

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        with mock.patch.dict(os.environ, {"ZKAI_GIT_COMMIT": "test-commit"}, clear=True):
            payload = PROBE.build_payload()

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "out.json"
            tsv_path = tmp / "out.tsv"
            PROBE.write_outputs(copy.deepcopy(payload), json_path, tsv_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], PROBE.SCHEMA)
            tsv = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv[0].split("\t"), list(PROBE.TSV_COLUMNS))
            self.assertEqual(tsv[1].split("\t")[0], "64")

    def test_generated_at_is_deterministic_and_rejects_bad_env(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(PROBE._generated_at(), "1970-01-01T00:00:00Z")
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "bad"}, clear=True):
            with self.assertRaisesRegex(PROBE.SurfaceProbeError, "SOURCE_DATE_EPOCH"):
                PROBE._generated_at()
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": str(10**100)}, clear=True):
            with self.assertRaisesRegex(PROBE.SurfaceProbeError, "timestamp range"):
                PROBE._generated_at()


if __name__ == "__main__":
    unittest.main()
