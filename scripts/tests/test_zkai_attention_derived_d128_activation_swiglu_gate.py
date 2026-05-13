from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_activation_swiglu_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_activation_swiglu_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load derived activation/SwiGLU gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionDerivedD128ActivationSwiGluGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = GATE.build_context()
        cls.payload = GATE.build_gate_result(copy.deepcopy(cls.context))

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_result_connects_derived_projection_to_activation_swiglu(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload, context=copy.deepcopy(self.context))
        summary = payload["summary"]
        activation = payload["activation_swiglu_payload"]
        source = payload["source_summary"]
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(activation["row_count"], 512)
        self.assertEqual(activation["activation_lookup_rows"], 2049)
        self.assertEqual(activation["swiglu_mix_rows"], 512)
        self.assertEqual(
            activation["source_gate_value_projection_output_commitment"],
            source["derived_gate_value_projection_output_commitment"],
        )
        self.assertEqual(summary["derived_activation_output_commitment"], activation["activation_output_commitment"])
        self.assertEqual(summary["derived_hidden_activation_commitment"], activation["hidden_activation_commitment"])
        self.assertEqual(payload["case_count"], 15)
        self.assertTrue(payload["all_mutations_rejected"])

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
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "unexpected error"):
                GATE.run_mutation_cases(
                    GATE.build_core_payload(copy.deepcopy(self.context)),
                    copy.deepcopy(self.context),
                )
        finally:
            GATE.EXPECTED_MUTATION_ERRORS["decision_overclaim"] = original

    def test_current_activation_comparison_is_explicitly_not_matching(self) -> None:
        payload = self.fresh_payload()
        comparison = payload["comparison_summary"]
        self.assertFalse(comparison["matches_existing_d128_activation_swiglu"])
        self.assertEqual(comparison["activation_output_mismatch_count"], 288)
        self.assertEqual(comparison["hidden_activation_mismatch_count"], 512)
        self.assertFalse(payload["summary"]["matches_existing_d128_activation_swiglu"])

    def test_activation_payload_rejects_source_projection_boundary_drift(self) -> None:
        payload = self.fresh_payload()
        payload["activation_swiglu_payload"]["source_projection_boundary_payload_commitment"] = "blake2b-256:" + "66" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "derived activation payload drift|source projection"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_activation_payload_rejects_source_gate_value_output_drift(self) -> None:
        payload = self.fresh_payload()
        payload["activation_swiglu_payload"]["source_gate_value_projection_output_commitment"] = "blake2b-256:" + "77" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "derived activation payload drift|gate/value"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_activation_payload_rejects_gate_projection_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["activation_swiglu_payload"]["gate_projection_q8"][0] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "derived activation payload drift|gate projection"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_activation_payload_rejects_hidden_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["activation_swiglu_payload"]["hidden_activation_commitment"] = GATE.ACTIVATION.OUTPUT_ACTIVATION_COMMITMENT
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "derived activation payload drift|full output"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_activation_payload_rejects_activation_output_drift(self) -> None:
        payload = self.fresh_payload()
        payload["activation_swiglu_payload"]["activated_gate_q8"][0] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "derived activation payload drift|activation output"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_consumption_overclaim(self) -> None:
        payload = self.fresh_payload()
        payload["summary"]["matches_existing_d128_activation_swiglu"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "overclaim|payload drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_to_tsv_requires_final_payload(self) -> None:
        core = GATE.build_core_payload(copy.deepcopy(self.context))
        with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "finalized payload"):
            GATE.to_tsv(core, context=copy.deepcopy(self.context))

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "activation-swiglu.json"
            tsv_path = tmp / "activation-swiglu.tsv"
            GATE.write_outputs(payload, json_path, tsv_path, context=copy.deepcopy(self.context))
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn("derived_hidden_activation_commitment", tsv)
            self.assertIn(payload["summary"]["derived_hidden_activation_commitment"], tsv)

    def test_write_outputs_anchors_relative_paths_to_repo_root(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp, tempfile.TemporaryDirectory() as raw_cwd:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "activation-swiglu.json").relative_to(GATE.ROOT)
            tsv_path = (tmp / "activation-swiglu.tsv").relative_to(GATE.ROOT)
            original_cwd = pathlib.Path.cwd()
            try:
                os.chdir(raw_cwd)
                GATE.write_outputs(payload, json_path, tsv_path, context=copy.deepcopy(self.context))
            finally:
                os.chdir(original_cwd)
            self.assertEqual(json.loads((tmp / "activation-swiglu.json").read_text(encoding="utf-8")), payload)
            self.assertIn(
                payload["summary"]["derived_hidden_activation_commitment"],
                (tmp / "activation-swiglu.tsv").read_text(encoding="utf-8"),
            )

    def test_write_outputs_rejects_paths_outside_evidence_dir(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "docs/engineering/evidence"):
                GATE.write_outputs(payload, tmp / "activation-swiglu.json", None, context=copy.deepcopy(self.context))

    def test_write_outputs_rejects_wrong_suffix(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "end with .json"):
                GATE.write_outputs(payload, tmp / "activation-swiglu.txt", None, context=copy.deepcopy(self.context))

    def test_load_json_rejects_unhardened_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            source = tmp / "source.json"
            source.write_text(json.dumps(GATE.build_core_payload(copy.deepcopy(self.context))), encoding="utf-8")
            link = tmp / "link.json"
            link.symlink_to(source)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "symlink"):
                GATE.load_json(link)
        with tempfile.TemporaryDirectory() as raw_tmp:
            outside = pathlib.Path(raw_tmp) / "source.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "escapes repository"):
                GATE.load_json(outside)

    def test_load_json_rejects_oversized_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            source = pathlib.Path(raw_tmp) / "oversized.json"
            source.write_text(" " * (GATE.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(GATE.AttentionDerivedD128ActivationSwiGluError, "exceeds max size"):
                GATE.load_json(source)


if __name__ == "__main__":
    unittest.main()
