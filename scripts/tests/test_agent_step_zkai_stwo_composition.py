from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSITION_PATH = ROOT / "scripts" / "agent_step_zkai_stwo_composition.py"
SPEC = importlib.util.spec_from_file_location("agent_step_zkai_stwo_composition", COMPOSITION_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load composition harness from {COMPOSITION_PATH}")
COMPOSITION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPOSITION)


class AgentStepZkAIStwoCompositionTests(unittest.TestCase):
    def test_composition_gate_is_go_and_rejects_all_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            payload = COMPOSITION.run_composition(artifact_dir=pathlib.Path(raw_tmp))

        self.assertEqual(payload["result"], "GO")
        self.assertTrue(payload["baseline_accepted"])
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], 36)
        self.assertEqual(payload["summary"]["agent_receipt_mutations"], 20)
        self.assertEqual(payload["summary"]["zkai_statement_receipt_mutations"], 14)
        self.assertEqual(payload["summary"]["cross_layer_composition_mutations"], 1)
        self.assertEqual(payload["summary"]["source_evidence_mutations"], 1)

    def test_composed_bundle_verifies_with_agent_receipt_harness(self) -> None:
        envelope = COMPOSITION.baseline_stwo_envelope()
        bundle = COMPOSITION.build_composed_bundle(envelope)
        evidence = COMPOSITION._source_evidence_with_path(COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH)

        self.assertTrue(COMPOSITION.HARNESS.verify_bundle(bundle))
        self.assertTrue(
            COMPOSITION.verify_composition(bundle, envelope=envelope, stwo_evidence=evidence)
        )
        self.assertEqual(
            bundle["receipt"]["model_receipt_commitment"],
            envelope["statement_commitment"],
        )

    def test_cross_layer_self_consistent_bad_subreceipt_is_rejected(self) -> None:
        _category, mutated_envelope = COMPOSITION.STWO.mutated_envelopes()["model_id_relabeling"]
        bundle = COMPOSITION.build_composed_bundle(mutated_envelope)
        evidence = COMPOSITION._source_evidence_with_path(COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH)

        self.assertTrue(COMPOSITION.HARNESS.verify_bundle(bundle))
        with self.assertRaisesRegex(
            COMPOSITION.STWO.StwoEnvelopeError,
            "statement policy mismatch for model_id",
        ):
            COMPOSITION.verify_composition(
                bundle,
                envelope=mutated_envelope,
                stwo_evidence=evidence,
            )

    def test_tampered_checked_stwo_evidence_rejects_fail_closed(self) -> None:
        envelope = COMPOSITION.baseline_stwo_envelope()
        bundle = COMPOSITION.build_composed_bundle(envelope)
        evidence = COMPOSITION.checked_stwo_evidence(COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH)
        tampered = copy.deepcopy(evidence)
        for case in tampered["cases"]:
            if (
                case["adapter"] == "stwo-statement-envelope"
                and case["mutation"] == "model_id_relabeling"
            ):
                case["rejected"] = False
                case["mutated_accepted"] = True
                case["rejection_layer"] = "accepted"
                case["error"] = ""
                break

        with self.assertRaisesRegex(COMPOSITION.CompositionError, "benchmark"):
            COMPOSITION.verify_composition(bundle, envelope=envelope, stwo_evidence=tampered)

    def test_checked_stwo_evidence_must_match_composed_envelope(self) -> None:
        envelope = COMPOSITION.baseline_stwo_envelope()
        bundle = COMPOSITION.build_composed_bundle(envelope)
        evidence = COMPOSITION.checked_stwo_evidence(COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH)
        tampered = copy.deepcopy(evidence)
        for case in tampered["cases"]:
            case["baseline_statement_commitment"] = "blake2b-256:" + "44" * 32

        with self.assertRaisesRegex(COMPOSITION.CompositionError, "baseline statement commitment"):
            COMPOSITION.verify_composition(bundle, envelope=envelope, stwo_evidence=tampered)

    def test_rejection_layer_classification_uses_exception_type(self) -> None:
        self.assertEqual(
            COMPOSITION.classify_composition_error(
                COMPOSITION.HARNESS.AgentReceiptError("unsupported proof backend version")
            ),
            "agent_receipt_verifier",
        )
        self.assertEqual(
            COMPOSITION.classify_composition_error(
                COMPOSITION.HARNESS.AgentReceiptError("unsupported verifier domain")
            ),
            "agent_receipt_verifier",
        )

    def test_agent_trust_upgrade_case_targets_unproved_field(self) -> None:
        cases = COMPOSITION.mutation_cases(COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH)
        case = next(item for item in cases if item["mutation"] == "trust_class_upgrade_without_proof")

        self.assertTrue(case["rejected"])
        self.assertIn("/tool_receipts_root", case["error"])

    def test_tsv_columns_are_stable(self) -> None:
        payload = {
            "cases": [
                {
                    "mutation": "case",
                    "surface": "agent_receipt",
                    "baseline_accepted": True,
                    "mutated_accepted": False,
                    "rejected": True,
                    "rejection_layer": "unit-test",
                    "error": "",
                }
            ]
        }

        self.assertEqual(
            COMPOSITION.to_tsv(payload).splitlines()[0].split("\t"),
            COMPOSITION.TSV_COLUMNS,
        )

    def test_checked_stwo_evidence_rejects_forged_summary(self) -> None:
        source = json.loads(COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH.read_text(encoding="utf-8"))
        source["summary"]["stwo-statement-envelope"]["mutations_rejected"] = 13
        with tempfile.TemporaryDirectory(dir=ROOT) as raw_tmp:
            path = pathlib.Path(raw_tmp) / "forged.json"
            path.write_text(json.dumps(source), encoding="utf-8")

            with self.assertRaisesRegex(COMPOSITION.CompositionError, "benchmark"):
                COMPOSITION.checked_stwo_evidence(path)

    def test_in_memory_stwo_evidence_runs_same_metadata_checks(self) -> None:
        evidence = COMPOSITION.checked_stwo_evidence(COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH)
        evidence["external_system"]["version"] = "wrong-stwo-version"

        with self.assertRaisesRegex(COMPOSITION.CompositionError, "version"):
            COMPOSITION._checked_stwo_payload(evidence)

    def test_source_evidence_path_is_loaded_once_for_mutation_suite(self) -> None:
        COMPOSITION._CHECKED_STWO_EVIDENCE_CACHE.clear()
        original_load_json = COMPOSITION.load_json
        load_count = 0

        def counting_load_json(path: pathlib.Path):
            nonlocal load_count
            if path.resolve() == COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH.resolve():
                load_count += 1
            return original_load_json(path)

        COMPOSITION.load_json = counting_load_json
        try:
            cases = COMPOSITION.mutation_cases(COMPOSITION.DEFAULT_STWO_EVIDENCE_PATH)
        finally:
            COMPOSITION.load_json = original_load_json
            COMPOSITION._CHECKED_STWO_EVIDENCE_CACHE.clear()

        self.assertEqual(len(cases), 36)
        self.assertEqual(load_count, 1)


if __name__ == "__main__":
    unittest.main()
