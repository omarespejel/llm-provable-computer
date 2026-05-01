from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_native_relation_witness_oracle.py"
SPEC = importlib.util.spec_from_file_location("zkai_d64_native_relation_witness_oracle", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load native relation oracle from {SCRIPT_PATH}")
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


class ZkAID64NativeRelationWitnessOracleTests(unittest.TestCase):
    def test_payload_records_relation_oracle_go_without_proof_claim(self) -> None:
        with mock.patch.dict("os.environ", {"ZKAI_GIT_COMMIT": "test-commit"}, clear=True):
            payload = ORACLE.build_payload()

        ORACLE.validate_payload(payload)
        self.assertEqual(payload["schema"], ORACLE.SCHEMA)
        self.assertEqual(payload["decision"], ORACLE.DECISION)
        self.assertIn("not a Stwo proof", payload["non_claims"])
        self.assertEqual(payload["source_fixture"]["proof_status"], "REFERENCE_FIXTURE_NOT_PROVEN")
        self.assertEqual(payload["relation_witness"]["row_counts"]["projection_mul_rows"], 49_152)
        self.assertEqual(payload["relation_witness"]["row_counts"]["trace_rows_excluding_static_table"], 49_920)
        self.assertEqual(payload["relation_witness"]["row_counts"]["activation_table_rows"], 2_049)
        self.assertEqual(payload["mutation_suite"]["mutations_checked"], len(ORACLE.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutation_suite"]["mutations_rejected"], len(ORACLE.EXPECTED_MUTATION_NAMES))

    def test_public_instance_and_statement_binding_fields_are_hard_pinned(self) -> None:
        payload = ORACLE.build_payload()
        witness = payload["relation_witness"]

        self.assertEqual(
            ORACLE.PUBLIC_INSTANCE_FIELDS,
            (
                "target_id",
                "width",
                "ff_dim",
                "input_activation_commitment",
                "output_activation_commitment",
                "model_config_commitment",
                "proof_native_parameter_commitment",
                "normalization_config_commitment",
                "activation_lookup_commitment",
            ),
        )
        del witness["public_instance"]["proof_native_parameter_commitment"]
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "public instance field set"):
            ORACLE.validate_relation_witness(witness)

        payload = ORACLE.build_payload()
        del payload["relation_witness"]["statement_binding"]["statement_commitment"]
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "statement binding field set"):
            ORACLE.validate_relation_witness(payload["relation_witness"])

    def test_relation_oracle_rejects_parameter_and_table_drift(self) -> None:
        payload = ORACLE.build_payload()
        witness = payload["relation_witness"]
        wrong_commitment = "blake2b-256:" + "aa" * 32

        cases = [
            (("public_instance", "proof_native_parameter_commitment"), "relation witness mismatch: public_instance"),
            (("parameter_manifest", "matrix_trees", "gate", "root"), "relation witness mismatch: parameter_manifest"),
            (("parameter_manifest", "activation_table_tree", "root"), "relation witness mismatch: parameter_manifest"),
            (("statement_binding", "backend_version_required"), "relation witness mismatch: statement_binding"),
        ]
        for path, message in cases:
            mutated = ORACLE.mutate_path(witness, path, wrong_commitment)
            with self.subTest(path=path):
                with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, message):
                    ORACLE.validate_relation_witness(mutated)

    def test_relation_oracle_rejects_row_and_output_drift(self) -> None:
        payload = ORACLE.build_payload()
        witness = payload["relation_witness"]

        mutated = ORACLE.mutate_path(witness, ("row_counts", "projection_mul_rows"), 1)
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "relation witness mismatch"):
            ORACLE.validate_relation_witness(mutated)

        mutated = ORACLE.mutate_path(witness, ("relation_samples", "output_head_q8"), [0] * 8)
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "relation witness mismatch"):
            ORACLE.validate_relation_witness(mutated)

    def test_relation_oracle_recomputes_rmsnorm_and_commitment_surface(self) -> None:
        fixture = ORACLE.FIXTURE.build_fixture()
        reference = ORACLE.FIXTURE.evaluate_reference_block()

        mutated = copy.deepcopy(reference)
        mutated["normed_q8"][0] += 1
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "RMSNorm row relation mismatch"):
            ORACLE.relation_witness(mutated, fixture)

        mutated = copy.deepcopy(reference)
        mutated["output_q8"][0] += 1
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "commitment surface mismatch"):
            ORACLE.relation_witness(mutated, fixture)

    def test_relation_check_names_advertise_recomputed_scope(self) -> None:
        payload = ORACLE.build_payload()
        check_names = {case["name"] for case in payload["relation_witness"]["relation_checks"]}

        self.assertIn("proof_native_parameter_manifest_recomputed", check_names)
        self.assertIn("public_statement_commitments_recomputed", check_names)
        self.assertIn("rmsnorm_rows_recomputed", check_names)
        self.assertNotIn("input_output_commitments", check_names)
        self.assertNotIn("rmsnorm_rows", check_names)

    def test_mutation_corpus_is_exact_and_fail_closed(self) -> None:
        payload = ORACLE.build_payload()
        names = {case["name"] for case in payload["mutation_suite"]["cases"]}

        self.assertEqual(names, set(ORACLE.EXPECTED_MUTATION_NAMES))
        self.assertTrue(all(case["rejected"] for case in payload["mutation_suite"]["cases"]))

        payload["mutation_suite"]["mutations_rejected"] -= 1
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "mutation suite drift"):
            ORACLE.validate_payload(payload)

    def test_payload_validation_rejects_source_fixture_drift(self) -> None:
        payload = ORACLE.build_payload()
        payload["source_fixture"]["statement_commitment"] = "blake2b-256:" + "bb" * 32

        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "source fixture drift"):
            ORACLE.validate_payload(payload)

    def test_payload_validation_rejects_claim_boundary_drift(self) -> None:
        payload = ORACLE.build_payload()
        payload["non_claims"].remove("not a Stwo proof")
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "non-claims drift"):
            ORACLE.validate_payload(payload)

        payload = ORACLE.build_payload()
        payload["next_backend_step"] = "claim this is already a native proof"
        with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "next backend step drift"):
            ORACLE.validate_payload(payload)

    def test_rows_for_tsv_are_stable(self) -> None:
        payload = ORACLE.build_payload()
        rows = ORACLE.rows_for_tsv(payload)

        self.assertEqual(rows[0]["target_id"], "rmsnorm-swiglu-residual-d64-v2")
        self.assertEqual(rows[0]["decision"], ORACLE.DECISION)
        self.assertEqual(rows[0]["projection_mul_rows"], 49_152)
        self.assertEqual(rows[0]["mutations_checked"], len(ORACLE.EXPECTED_MUTATION_NAMES))
        self.assertEqual(rows[0]["mutations_rejected"], len(ORACLE.EXPECTED_MUTATION_NAMES))

    def test_write_outputs_round_trips_json_and_tsv(self) -> None:
        payload = ORACLE.build_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "oracle.json"
            tsv_path = tmp / "oracle.tsv"
            ORACLE.write_outputs(payload, json_path, tsv_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], ORACLE.SCHEMA)
            lines = tsv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0].split("\t"), list(ORACLE.TSV_COLUMNS))
            self.assertIn(ORACLE.DECISION, lines[1])

    def test_write_outputs_wraps_os_errors(self) -> None:
        payload = ORACLE.build_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            bad_parent = pathlib.Path(raw_tmp) / "not-a-dir"
            bad_parent.write_text("file", encoding="utf-8")
            with self.assertRaisesRegex(ORACLE.NativeRelationWitnessOracleError, "failed to write"):
                ORACLE.write_outputs(payload, bad_parent / "out.json", None)


if __name__ == "__main__":
    unittest.main()
