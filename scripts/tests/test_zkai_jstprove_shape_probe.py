from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_jstprove_shape_probe.py"
SPEC = importlib.util.spec_from_file_location("zkai_jstprove_shape_probe", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load JSTprove shape probe from {SCRIPT_PATH}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def synthetic_results() -> list[dict[str, object]]:
    results = []
    for index, fixture in enumerate(PROBE.EXPECTED_FIXTURE_ORDER, start=1):
        status = PROBE.EXPECTED_STATUS[fixture]
        failed_step = ""
        failure_kind = ""
        proof_bytes: int | None = 10_000 + index
        gate = "GO_CHECKED_SMALL_SHAPE"
        if status == "NO_GO":
            failed_step = "witness" if fixture != "tiny_gemm_softmax" else "prove"
            failure_kind = PROBE.EXPECTED_FAILURE_KIND[fixture]
            proof_bytes = None
            gate = f"NO_GO_{failure_kind.upper()}"
        catalog = {item["fixture"]: item for item in PROBE.fixture_catalog()}[fixture]
        results.append(
            {
                "fixture": fixture,
                "gate": gate,
                "op_sequence": catalog["op_sequence"],
                "transformer_relevance": catalog["transformer_relevance"],
                "status": status,
                "failed_step": failed_step,
                "failure_kind": failure_kind,
                "proof_bytes": proof_bytes,
                "model_bytes": 300 + index,
                "onnx_bytes": 120 + index,
                "input_bytes": 17,
                "prove_seconds": "0.100000" if status == "GO" else "NA",
                "verify_seconds": "0.200000" if status == "GO" else "NA",
                "primary_observation": catalog["primary_observation"],
                "steps": [],
            }
        )
    return results


def synthetic_dimension_sweep() -> list[dict[str, object]]:
    return [
        {
            "dimension": dimension,
            "status": "GO",
            "failed_step": "",
            "failure_kind": "",
            "proof_bytes": 20_000 + dimension,
            "model_bytes": 1_000 + dimension,
            "onnx_bytes": 400 + dimension,
            "prove_seconds": "0.100000",
            "verify_seconds": "0.200000",
        }
        for dimension in PROBE.GEMM_SWEEP_DIMENSIONS
    ]


def synthetic_relu_scaling_probe() -> list[dict[str, object]]:
    rows = []
    for scale in PROBE.RELU_SCALE_FACTORS:
        if scale == "1":
            rows.append(
                {
                    "scale": scale,
                    "status": "NO_GO",
                    "failed_step": "witness",
                    "failure_kind": "range_check_capacity",
                    "proof_bytes": None,
                    "model_bytes": 1_100,
                    "onnx_bytes": 410,
                    "prove_seconds": "NA",
                    "verify_seconds": "NA",
                }
            )
        else:
            rows.append(
                {
                    "scale": scale,
                    "status": "GO",
                    "failed_step": "",
                    "failure_kind": "",
                    "proof_bytes": 30_000 + len(rows),
                    "model_bytes": 1_100,
                    "onnx_bytes": 410,
                    "prove_seconds": "0.300000",
                    "verify_seconds": "0.400000",
                }
            )
    return rows


def synthetic_softmax_source_probe() -> dict[str, object]:
    return {
        "status": "SOURCE_HIT",
        "source_root": "/tmp/JSTprove",
        "source_commit": "7c3cbbee83aaa01adde700673f00e317a4e902f9",
        "hits": [
            {
                "category": "remainder_refusal",
                "path": "src/remainder.rs",
                "line": 123,
                "text": "Softmax op is not yet constrained",
            }
        ],
        "softmax_refusal_found": True,
        "observation": "Pinned source inspection found Softmax-related backend code.",
    }


def synthetic_payload() -> dict[str, object]:
    return PROBE.build_payload(
        synthetic_results(),
        jstprove_bin=pathlib.Path("/tmp/jstprove-remainder"),
        work_dir=pathlib.Path("/tmp/jstprove-shape-test"),
        dimension_sweep=synthetic_dimension_sweep(),
        relu_scaling_probe=synthetic_relu_scaling_probe(),
        softmax_source=synthetic_softmax_source_probe(),
    )


class ZkAIJstproveShapeProbeTests(unittest.TestCase):
    def test_payload_records_operator_support_split_without_transformer_claim(self) -> None:
        payload = synthetic_payload()
        PROBE.validate_payload(payload)

        self.assertEqual(payload["decision"], PROBE.DECISION)
        self.assertEqual(payload["conclusion"]["go_count"], 5)
        self.assertEqual(payload["conclusion"]["no_go_count"], 3)
        self.assertEqual(payload["conclusion"]["gemm_dimension_sweep"], "GO_DIMS_1_2_4")
        self.assertEqual(payload["conclusion"]["relu_scaling"], "INPUT_DEPENDENT_BASELINE_FAILS_SCALED_VARIANTS_CLEAR")
        self.assertEqual(
            set(payload["conclusion"]["go_transformer_adjacent_fixtures"]),
            {"tiny_gemm_residual_add", "tiny_gemm_layernorm", "tiny_gemm_batchnorm"},
        )
        self.assertIn("not a full transformer proof", payload["non_claims"])
        self.assertIn("not a Tablero result", payload["non_claims"])

    def test_rows_for_tsv_are_stable(self) -> None:
        payload = synthetic_payload()
        rows = PROBE.rows_for_tsv(payload)

        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]["fixture"], "tiny_gemm")
        self.assertEqual(rows[0]["status"], "GO")
        self.assertEqual(rows[5]["fixture"], "tiny_gemm_relu")
        self.assertEqual(rows[5]["failure_kind"], "range_check_capacity")
        self.assertEqual(PROBE.to_tsv(payload).splitlines()[0].split("\t"), list(PROBE.TSV_COLUMNS))

    def test_validation_rejects_status_overclaim(self) -> None:
        payload = synthetic_payload()
        for result in payload["results"]:
            if result["fixture"] == "tiny_gemm_relu":
                result["status"] = "GO"
                result["proof_bytes"] = 1
                result["failed_step"] = ""
                result["failure_kind"] = ""
                result["gate"] = "GO_CHECKED_SMALL_SHAPE"
        payload["results_commitment"] = PROBE.blake2b_commitment(
            payload["results"], "ptvm:zkai:jstprove-shape-results:v1"
        )

        with self.assertRaisesRegex(PROBE.JstproveShapeProbeError, "tiny_gemm_relu status drift"):
            PROBE.validate_payload(payload)

    def test_validation_rejects_failure_kind_drift(self) -> None:
        payload = synthetic_payload()
        for result in payload["results"]:
            if result["fixture"] == "tiny_gemm_softmax":
                result["failure_kind"] = "external_tool_error"
                result["gate"] = "NO_GO_EXTERNAL_TOOL_ERROR"
        payload["results_commitment"] = PROBE.blake2b_commitment(
            payload["results"], "ptvm:zkai:jstprove-shape-results:v1"
        )

        with self.assertRaisesRegex(PROBE.JstproveShapeProbeError, "tiny_gemm_softmax failure kind drift"):
            PROBE.validate_payload(payload)

    def test_validation_rejects_paper_usage_overclaim(self) -> None:
        payload = synthetic_payload()
        payload["conclusion"]["paper_usage"] = "transformer_proof_row"

        with self.assertRaisesRegex(PROBE.JstproveShapeProbeError, "paper usage overclaim"):
            PROBE.validate_payload(payload)

    def test_validation_rejects_unknown_conclusion_fields(self) -> None:
        payload = synthetic_payload()
        payload["conclusion"]["publish_as_performance_result"] = True

        with self.assertRaisesRegex(PROBE.JstproveShapeProbeError, "conclusion field set mismatch"):
            PROBE.validate_payload(payload)

    def test_classify_failure_keeps_interesting_blockers_distinct(self) -> None:
        self.assertEqual(
            PROBE.classify_failure("witness", "Relu delta nv 20 exceeds two-chunk range-check capacity"),
            "range_check_capacity",
        )
        self.assertEqual(
            PROBE.classify_failure("prove", "Softmax op is not yet constrained in the Remainder backend"),
            "unconstrained_backend_op",
        )
        self.assertEqual(
            PROBE.classify_failure("witness", "unsupported op type MatMul in layer node_0"),
            "unsupported_witness_op",
        )

    def test_resolve_jstprove_binary_rejects_absolute_missing_or_non_executable(self) -> None:
        missing = ROOT / "target" / "definitely-missing-jstprove-remainder"
        with self.assertRaisesRegex(PROBE.JstproveShapeProbeError, "verifier is missing"):
            PROBE._resolve_jstprove_binary(str(missing))

        with tempfile.TemporaryDirectory() as raw_tmp:
            binary = pathlib.Path(raw_tmp) / "jstprove-remainder"
            binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            binary.chmod(0o600)
            with self.assertRaisesRegex(PROBE.JstproveShapeProbeError, "verifier is not executable"):
                PROBE._resolve_jstprove_binary(str(binary))

    def test_resolve_jstprove_binary_resolves_relative_path_before_fixture_cwd(self) -> None:
        original_cwd = pathlib.Path.cwd()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            binary = tmp / "bin" / "jstprove-remainder"
            binary.parent.mkdir()
            binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            binary.chmod(0o700)
            os.chdir(tmp)
            try:
                resolved = PROBE._resolve_jstprove_binary("bin/jstprove-remainder")
            finally:
                os.chdir(original_cwd)

        self.assertEqual(resolved, binary.resolve())

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        payload = synthetic_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "shape.json"
            tsv_path = tmp / "shape.tsv"
            PROBE.write_outputs(payload, json_path, tsv_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], PROBE.SCHEMA)
            self.assertEqual(tsv_path.read_text(encoding="utf-8").splitlines()[1].split("\t")[0], "tiny_gemm")

    def test_checked_json_evidence_validates_when_present(self) -> None:
        if not PROBE.JSON_OUT.exists():
            self.skipTest("checked shape-probe evidence has not been generated")
        payload = json.loads(PROBE.JSON_OUT.read_text(encoding="utf-8"))

        PROBE.validate_payload(payload)

    def test_git_commit_override_is_validated(self) -> None:
        with self.assertRaisesRegex(PROBE.JstproveShapeProbeError, "must be a 7-40 character hex SHA"):
            with mock.patch.dict(os.environ, {PROBE.GIT_COMMIT_ENV: "not-a-sha"}):
                PROBE._git_commit()


if __name__ == "__main__":
    unittest.main()
