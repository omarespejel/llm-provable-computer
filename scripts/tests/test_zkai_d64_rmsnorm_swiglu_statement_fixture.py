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
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_swiglu_statement_fixture.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_rmsnorm_swiglu_statement_fixture", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d64 statement fixture from {SCRIPT_PATH}")
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


class ZkAID64RMSNormSwiGLUStatementFixtureTests(unittest.TestCase):
    def test_target_shape_and_operation_counts_are_pinned(self) -> None:
        target = FIXTURE.target_spec()

        self.assertEqual(target["target_id"], "rmsnorm-swiglu-residual-d64-v1")
        self.assertEqual(target["width"], 64)
        self.assertEqual(target["ff_dim"], 256)
        self.assertEqual(target["linear_projection_muls"], 49_152)
        self.assertEqual(target["projection_weight_scalars"], 49_152)
        self.assertEqual(target["rms_scale_scalars"], 64)
        self.assertEqual(target["total_committed_parameter_scalars"], 49_216)
        self.assertEqual(target["required_backend_version"], "stwo-rmsnorm-swiglu-residual-d64-v1")

    def test_reference_block_is_deterministic_and_dimensioned(self) -> None:
        first = FIXTURE.evaluate_reference_block()
        second = FIXTURE.evaluate_reference_block()

        self.assertEqual(first, second)
        self.assertEqual(len(first["input_q8"]), 64)
        self.assertEqual(len(first["rms_scale_q8"]), 64)
        self.assertEqual(len(first["gate_projection_q8"]), 256)
        self.assertEqual(len(first["value_projection_q8"]), 256)
        self.assertEqual(len(first["hidden_q8"]), 256)
        self.assertEqual(len(first["output_q8"]), 64)

    def test_activation_table_is_pinned_and_bounded(self) -> None:
        table = FIXTURE.activation_table()

        self.assertEqual(len(table), 2 * FIXTURE.ACTIVATION_CLAMP_Q8 + 1)
        self.assertEqual(table[FIXTURE.ACTIVATION_CLAMP_Q8], 0)
        self.assertEqual(FIXTURE.activation_lut_value(-10_000), table[0])
        self.assertEqual(FIXTURE.activation_lut_value(10_000), table[-1])

    def test_statement_fixture_validates_and_rejects_mutations(self) -> None:
        with mock.patch.dict(os.environ, {"ZKAI_GIT_COMMIT": "test-commit"}, clear=True):
            payload = FIXTURE.build_fixture()

        self.assertEqual(payload["schema"], FIXTURE.SCHEMA)
        self.assertEqual(payload["generated_at"], "1970-01-01T00:00:00Z")
        self.assertEqual(payload["git_commit"], "test-commit")
        self.assertEqual(payload["decision"], "GO_STATEMENT_TARGET_PINNED_NOT_PROVEN")
        self.assertEqual(payload["implementation_status"]["proof_status"], "REFERENCE_FIXTURE_NOT_PROVEN")
        FIXTURE.validate_statement(payload["statement"])

        mutations = payload["mutation_suite"]
        self.assertTrue(mutations["baseline_valid"])
        self.assertEqual(mutations["decision"], "GO")
        self.assertEqual(mutations["mutations_checked"], 14)
        self.assertEqual(mutations["mutations_rejected"], 14)

    def test_statement_binding_rejects_valid_looking_wrong_commitments(self) -> None:
        statement = FIXTURE.build_fixture()["statement"]
        mutated = copy.deepcopy(statement)
        mutated["weight_commitment"] = "11" * 32

        with self.assertRaisesRegex(FIXTURE.StatementFixtureError, "weight_commitment"):
            FIXTURE.validate_statement(mutated)

    def test_statement_binding_rejects_proof_status_overclaim(self) -> None:
        statement = FIXTURE.build_fixture()["statement"]
        mutated = copy.deepcopy(statement)
        mutated["proof_status"] = "PROVEN"

        with self.assertRaisesRegex(FIXTURE.StatementFixtureError, "proof_status"):
            FIXTURE.validate_statement(mutated)

    def test_output_commitment_changes_when_reference_output_changes(self) -> None:
        reference = FIXTURE.evaluate_reference_block()
        baseline = FIXTURE.commitments(reference)
        changed = copy.deepcopy(reference)
        changed["output_q8"][0] += 1

        self.assertNotEqual(
            baseline["output_activation_commitment"],
            FIXTURE.commitments(changed)["output_activation_commitment"],
        )

    def test_rows_for_tsv_are_stable(self) -> None:
        payload = FIXTURE.build_fixture()
        rows = FIXTURE.rows_for_tsv(payload)

        self.assertEqual(rows[0]["target_id"], "rmsnorm-swiglu-residual-d64-v1")
        self.assertEqual(rows[0]["proof_status"], "REFERENCE_FIXTURE_NOT_PROVEN")
        self.assertEqual(rows[0]["width"], 64)
        self.assertEqual(rows[0]["ff_dim"], 256)
        self.assertEqual(rows[0]["linear_projection_muls"], 49_152)
        self.assertEqual(rows[0]["projection_weight_scalars"], 49_152)
        self.assertEqual(rows[0]["rms_scale_scalars"], 64)
        self.assertEqual(rows[0]["total_committed_parameter_scalars"], 49_216)
        self.assertEqual(rows[0]["mutations_checked"], 14)
        self.assertEqual(rows[0]["mutations_rejected"], 14)

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        payload = FIXTURE.build_fixture()

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "fixture.json"
            tsv_path = tmp / "fixture.tsv"
            FIXTURE.write_outputs(payload, json_path, tsv_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], FIXTURE.SCHEMA)
            tsv = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(tsv[0].split("\t"), list(FIXTURE.TSV_COLUMNS))
            self.assertEqual(tsv[1].split("\t")[0], "rmsnorm-swiglu-residual-d64-v1")

    def test_generated_at_rejects_bad_env(self) -> None:
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "bad"}, clear=True):
            with self.assertRaisesRegex(FIXTURE.StatementFixtureError, "SOURCE_DATE_EPOCH"):
                FIXTURE._generated_at()


if __name__ == "__main__":
    unittest.main()
