from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_input_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_input_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load attention-derived d128 input gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class AttentionDerivedD128InputGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_builds_attention_derived_input_gate(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["adapter_policy"]["policy_id"], "fixed_public_two_source_q8_projection_v1")
        self.assertEqual(payload["derived_input"]["width"], 128)
        self.assertEqual(payload["summary"]["derived_input_activation_commitment"], payload["derived_input"]["input_activation_commitment"])
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATIONS))

    def test_derived_vector_is_attention_value_connected(self) -> None:
        attention, _, _, _ = GATE.load_sources()
        attention_outputs = GATE.extract_attention_outputs(attention)
        values, rows = GATE.project_attention_to_d128(attention_outputs)
        payload = self.fresh_payload()
        self.assertEqual(payload["derived_input"]["values_q8"], values)
        self.assertEqual(payload["derived_input"]["projection_rows"], rows)
        self.assertEqual(values[:16], [1, 1, 2, -2, 1, 0, 4, 1, 4, 1, 1, 1, -1, 4, 3, 0])
        self.assertEqual(min(values), -4)
        self.assertEqual(max(values), 5)
        self.assertEqual(sum(values), 104)

    def test_projection_rows_recompute_outputs(self) -> None:
        payload = self.fresh_payload()
        for row in payload["derived_input"]["projection_rows"]:
            numerator = (
                row["primary_coeff"] * row["primary_q8"]
                + row["mix_coeff"] * row["mix_q8"]
                + row["bias_q8"]
            )
            self.assertEqual(row["numerator_q8"], numerator)
            self.assertEqual(row["output_q8"], numerator // row["denominator"])

    def test_uses_d128_rmsnorm_input_commitment_domain(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(payload["derived_input"]["input_activation_domain"], GATE.RMSNORM.INPUT_ACTIVATION_DOMAIN)
        self.assertEqual(
            payload["derived_input"]["input_activation_commitment"],
            GATE.RMSNORM.sequence_commitment(
                payload["derived_input"]["values_q8"],
                GATE.RMSNORM.INPUT_ACTIVATION_DOMAIN,
                GATE.WIDTH,
            ),
        )

    def test_records_no_go_against_current_d128_fixture(self) -> None:
        payload = self.fresh_payload()
        comparison = payload["current_d128_comparison"]
        self.assertFalse(comparison["derived_matches_current_input_values"])
        self.assertFalse(comparison["derived_matches_current_input_commitment"])
        self.assertEqual(comparison["mismatch_count_against_current"], 127)
        self.assertEqual(
            comparison["current_input_activation_commitment"],
            "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78",
        )

    def test_source_artifacts_are_hash_bound(self) -> None:
        payload = self.fresh_payload()
        artifacts = {artifact["id"]: artifact for artifact in payload["source_artifacts"]}
        self.assertEqual(
            set(artifacts),
            {"attention_d8_bounded_softmax_table", "current_d128_rmsnorm_input", "attention_d128_value_adapter_gate"},
        )
        for artifact in artifacts.values():
            self.assertTrue(artifact["path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(artifact["sha256"]), 64)
            self.assertEqual(len(artifact["payload_sha256"]), 64)

    def test_rejects_overclaims_and_drift(self) -> None:
        payload = self.fresh_payload()
        payload["current_d128_comparison"]["derived_matches_current_input_values"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128InputError, "derived input payload drift"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["claim_boundary"] = "MODEL_FAITHFUL_LEARNED_ADAPTER"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128InputError, "claim boundary drift"):
            GATE.validate_payload(payload)

    def test_rejects_projection_row_drift(self) -> None:
        payload = self.fresh_payload()
        payload["derived_input"]["projection_rows"][0]["output_q8"] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128InputError, "derived input payload drift"):
            GATE.validate_payload(payload)

    def test_rejects_source_artifact_hash_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_artifacts"][0]["sha256"] = "44" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128InputError, "source artifact hash drift"):
            GATE.validate_payload(payload)

    def test_mutation_inventory_rejects_claim_drift(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual([case["name"] for case in payload["cases"]], list(GATE.EXPECTED_MUTATIONS))
        self.assertTrue(all(case["rejected"] and not case["accepted"] for case in payload["cases"]))

        payload["cases"][0]["accepted"] = True
        payload["cases"][0]["rejected"] = False
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128InputError, "mutation accepted"):
            GATE.validate_payload(payload)

    def test_rejects_extra_mutation_case_without_raw_index_error(self) -> None:
        payload = self.fresh_payload()
        payload["cases"].append(
            {
                "name": "spoofed_extra_case",
                "accepted": False,
                "rejected": True,
                "error": "spoofed",
            }
        )
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128InputError, "mutation case count drift"):
            GATE.validate_payload(payload)

    def test_tsv_derives_from_validated_payload(self) -> None:
        payload = self.fresh_payload()
        tsv = GATE.to_tsv(payload)
        self.assertIn(payload["derived_input"]["input_activation_commitment"], tsv)
        self.assertIn("false", tsv)

    def test_write_outputs_round_trip_and_rejects_outside_path(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-derived-d128-input-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        try:
            GATE.write_outputs(self.fresh_payload(), json_path.relative_to(GATE.ROOT), tsv_path.relative_to(GATE.ROOT))
            self.assertTrue(json_path.exists())
            self.assertTrue(tsv_path.exists())
            with self.assertRaisesRegex(GATE.AttentionDerivedD128InputError, "output path must stay"):
                GATE.write_outputs(self.fresh_payload(), pathlib.Path("/tmp/out.json"), None)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128InputError, "output path must end"):
                GATE.write_outputs(self.fresh_payload(), None, json_path)
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
