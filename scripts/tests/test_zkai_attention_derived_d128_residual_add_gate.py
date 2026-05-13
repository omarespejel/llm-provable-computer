from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_residual_add_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_residual_add_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load derived residual-add gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionDerivedD128ResidualAddGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = GATE.build_context()
        cls.payload = GATE.build_gate_result(copy.deepcopy(cls.context))

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_result_connects_derived_input_and_residual_delta_to_output(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload, context=copy.deepcopy(self.context))
        summary = payload["summary"]
        residual = payload["residual_add_payload"]
        source = payload["source_summary"]
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(residual["row_count"], 128)
        self.assertEqual(summary["residual_add_rows"], 128)
        self.assertEqual(
            residual["input_activation_commitment"],
            source["source_input_activation_commitment"],
        )
        self.assertEqual(
            residual["residual_delta_commitment"],
            source["source_residual_delta_commitment"],
        )
        self.assertEqual(summary["derived_output_activation_commitment"], residual["output_activation_commitment"])
        self.assertEqual(summary["derived_residual_add_statement_commitment"], residual["statement_commitment"])
        self.assertEqual(payload["case_count"], 17)
        self.assertTrue(payload["all_mutations_rejected"])

    def test_current_residual_comparison_is_explicitly_not_matching(self) -> None:
        payload = self.fresh_payload()
        comparison = payload["comparison_summary"]
        self.assertFalse(comparison["matches_existing_d128_residual_add"])
        self.assertEqual(comparison["input_mismatch_count"], 127)
        self.assertEqual(comparison["residual_delta_mismatch_count"], 128)
        self.assertEqual(comparison["output_mismatch_count"], 128)
        self.assertFalse(payload["summary"]["matches_existing_d128_residual_add"])

    def test_mutation_errors_are_stable_markers(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(
            {case["name"]: case["error"] for case in payload["cases"]},
            GATE.EXPECTED_MUTATION_ERRORS,
        )

    def test_mutation_errors_reject_unexpected_markers(self) -> None:
        original = GATE.EXPECTED_MUTATION_ERRORS["decision_overclaim"]
        GATE.EXPECTED_MUTATION_ERRORS["decision_overclaim"] = "impossible marker"
        try:
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "unexpected error"):
                GATE.run_mutation_cases(
                    GATE.build_core_payload(copy.deepcopy(self.context)),
                    copy.deepcopy(self.context),
                )
        finally:
            GATE.EXPECTED_MUTATION_ERRORS["decision_overclaim"] = original

    def test_payload_rejects_source_input_payload_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_payload"]["source_input_payload_commitment"] = "sha256:" + "66" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "derived residual-add payload drift|source input"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_source_down_payload_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_payload"]["source_down_projection_payload_commitment"] = "sha256:" + "77" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "derived residual-add payload drift|down-projection"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_input_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_payload"]["input_q8"][0] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "derived residual-add payload drift|input"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_residual_delta_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_payload"]["residual_delta_q8"][0] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "derived residual-add payload drift|residual delta"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_output_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_payload"]["output_q8"][0] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "derived residual-add payload drift|output"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_output_relabeling_as_input(self) -> None:
        payload = self.fresh_payload()
        payload["residual_add_payload"]["output_activation_commitment"] = payload["residual_add_payload"]["input_activation_commitment"]
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "derived residual-add payload drift|output"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_statement_commitment_binds_required_backend_version(self) -> None:
        payload = self.fresh_payload()["residual_add_payload"]
        mutated = copy.deepcopy(payload)
        mutated["required_backend_version"] = mutated["required_backend_version"] + "-drift"
        self.assertNotEqual(GATE.statement_commitment(payload), GATE.statement_commitment(mutated))

    def test_payload_rejects_existing_residual_consumption_overclaim(self) -> None:
        payload = self.fresh_payload()
        payload["summary"]["matches_existing_d128_residual_add"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "overclaim|payload drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_to_tsv_requires_final_payload(self) -> None:
        core = GATE.build_core_payload(copy.deepcopy(self.context))
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "finalized payload"):
            GATE.to_tsv(core, context=copy.deepcopy(self.context))

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "residual-add.json"
            tsv_path = tmp / "residual-add.tsv"
            GATE.write_outputs(payload, json_path, tsv_path, context=copy.deepcopy(self.context))
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn("derived_output_activation_commitment", tsv)
            self.assertIn(payload["summary"]["derived_output_activation_commitment"], tsv)

    def test_write_outputs_anchors_relative_paths_to_repo_root(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp, tempfile.TemporaryDirectory() as raw_cwd:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "residual-add.json").relative_to(GATE.ROOT)
            tsv_path = (tmp / "residual-add.tsv").relative_to(GATE.ROOT)
            original_cwd = pathlib.Path.cwd()
            try:
                os.chdir(raw_cwd)
                GATE.write_outputs(payload, json_path, tsv_path, context=copy.deepcopy(self.context))
            finally:
                os.chdir(original_cwd)
            self.assertEqual(json.loads((tmp / "residual-add.json").read_text(encoding="utf-8")), payload)
            self.assertIn(
                payload["summary"]["derived_output_activation_commitment"],
                (tmp / "residual-add.tsv").read_text(encoding="utf-8"),
            )

    def test_write_outputs_rejects_paths_outside_evidence_dir(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "docs/engineering/evidence"):
                GATE.write_outputs(payload, tmp / "residual-add.json", None, context=copy.deepcopy(self.context))

    def test_write_outputs_rejects_wrong_suffix(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "end with .json"):
                GATE.write_outputs(payload, tmp / "residual-add.txt", None, context=copy.deepcopy(self.context))

    def test_load_json_rejects_unhardened_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            source = tmp / "source.json"
            source.write_text(json.dumps(GATE.build_core_payload(copy.deepcopy(self.context))), encoding="utf-8")
            link = tmp / "link.json"
            link.symlink_to(source)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "symlink"):
                GATE.load_json(link)
        with tempfile.TemporaryDirectory() as raw_tmp:
            outside = pathlib.Path(raw_tmp) / "source.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "escapes repository"):
                GATE.load_json(outside)

    def test_load_json_rejects_oversized_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            source = pathlib.Path(raw_tmp) / "oversized.json"
            source.write_text(" " * (GATE.DERIVED_DOWN.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "exceeds max size"):
                GATE.load_json(source)

    def test_load_module_rejects_symlinked_helper(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            link = pathlib.Path(raw_tmp) / "helper.py"
            link.symlink_to(GATE.RESIDUAL_ADD_PATH)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ResidualAddError, "symlink"):
                GATE._load_module(link, "symlinked_helper")


if __name__ == "__main__":
    unittest.main()
