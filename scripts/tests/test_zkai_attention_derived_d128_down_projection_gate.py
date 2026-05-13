from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_down_projection_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_down_projection_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load derived down-projection gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionDerivedD128DownProjectionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = GATE.build_context()
        cls.payload = GATE.build_gate_result(copy.deepcopy(cls.context))

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_result_connects_derived_hidden_to_down_projection(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload, context=copy.deepcopy(self.context))
        summary = payload["summary"]
        down = payload["down_projection_payload"]
        source = payload["source_summary"]
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(down["row_count"], 65536)
        self.assertEqual(down["down_projection_mul_rows"], 65536)
        self.assertEqual(down["residual_delta_rows"], 128)
        self.assertEqual(down["residual_delta_scale_divisor"], 512)
        self.assertEqual(
            down["source_hidden_activation_commitment"],
            source["source_hidden_activation_commitment"],
        )
        self.assertEqual(summary["derived_residual_delta_commitment"], down["residual_delta_commitment"])
        self.assertEqual(
            summary["derived_down_projection_statement_commitment"],
            down["statement_commitment"],
        )
        self.assertEqual(payload["case_count"], 16)
        self.assertTrue(payload["all_mutations_rejected"])

    def test_current_down_projection_comparison_is_explicitly_not_matching(self) -> None:
        payload = self.fresh_payload()
        comparison = payload["comparison_summary"]
        self.assertFalse(comparison["matches_existing_d128_down_projection"])
        self.assertEqual(comparison["hidden_mismatch_count"], 512)
        self.assertEqual(comparison["residual_delta_mismatch_count"], 128)
        self.assertEqual(comparison["residual_remainder_mismatch_count"], 128)
        self.assertFalse(payload["summary"]["matches_existing_d128_down_projection"])

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
            with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "unexpected error"):
                GATE.run_mutation_cases(
                    GATE.build_core_payload(copy.deepcopy(self.context)),
                    copy.deepcopy(self.context),
                )
        finally:
            GATE.EXPECTED_MUTATION_ERRORS["decision_overclaim"] = original

    def test_payload_rejects_source_activation_payload_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["down_projection_payload"]["source_activation_swiglu_payload_commitment"] = "sha256:" + "66" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "derived down-projection payload drift|source activation"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_hidden_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["down_projection_payload"]["hidden_q8"][0] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "derived down-projection payload drift|hidden"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_residual_delta_drift(self) -> None:
        payload = self.fresh_payload()
        payload["down_projection_payload"]["residual_delta_q8"][0] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "derived down-projection payload drift|residual delta"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_residual_delta_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["down_projection_payload"]["residual_delta_commitment"] = GATE.DOWN.OUTPUT_ACTIVATION_COMMITMENT
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "derived down-projection payload drift|full output"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_consumption_overclaim(self) -> None:
        payload = self.fresh_payload()
        payload["summary"]["matches_existing_d128_down_projection"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "overclaim|payload drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_to_tsv_requires_final_payload(self) -> None:
        core = GATE.build_core_payload(copy.deepcopy(self.context))
        with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "finalized payload"):
            GATE.to_tsv(core, context=copy.deepcopy(self.context))

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "down-projection.json"
            tsv_path = tmp / "down-projection.tsv"
            GATE.write_outputs(payload, json_path, tsv_path, context=copy.deepcopy(self.context))
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn("derived_residual_delta_commitment", tsv)
            self.assertIn(payload["summary"]["derived_residual_delta_commitment"], tsv)

    def test_write_outputs_anchors_relative_paths_to_repo_root(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp, tempfile.TemporaryDirectory() as raw_cwd:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "down-projection.json").relative_to(GATE.ROOT)
            tsv_path = (tmp / "down-projection.tsv").relative_to(GATE.ROOT)
            original_cwd = pathlib.Path.cwd()
            try:
                os.chdir(raw_cwd)
                GATE.write_outputs(payload, json_path, tsv_path, context=copy.deepcopy(self.context))
            finally:
                os.chdir(original_cwd)
            self.assertEqual(json.loads((tmp / "down-projection.json").read_text(encoding="utf-8")), payload)
            self.assertIn(
                payload["summary"]["derived_residual_delta_commitment"],
                (tmp / "down-projection.tsv").read_text(encoding="utf-8"),
            )

    def test_write_outputs_rejects_paths_outside_evidence_dir(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "docs/engineering/evidence"):
                GATE.write_outputs(payload, tmp / "down-projection.json", None, context=copy.deepcopy(self.context))

    def test_write_outputs_rejects_wrong_suffix(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "end with .json"):
                GATE.write_outputs(payload, tmp / "down-projection.txt", None, context=copy.deepcopy(self.context))

    def test_load_json_rejects_unhardened_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            source = tmp / "source.json"
            source.write_text(json.dumps(GATE.build_core_payload(copy.deepcopy(self.context))), encoding="utf-8")
            link = tmp / "link.json"
            link.symlink_to(source)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "symlink"):
                GATE.load_json(link)
        with tempfile.TemporaryDirectory() as raw_tmp:
            outside = pathlib.Path(raw_tmp) / "source.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "escapes repository"):
                GATE.load_json(outside)

    def test_load_json_rejects_oversized_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            source = pathlib.Path(raw_tmp) / "oversized.json"
            source.write_text(" " * (GATE.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(GATE.AttentionDerivedD128DownProjectionError, "exceeds max size"):
                GATE.load_json(source)


if __name__ == "__main__":
    unittest.main()
