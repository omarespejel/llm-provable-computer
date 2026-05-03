from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "zkai_d128_range_policy_discipline_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_range_policy_discipline_gate", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load {SCRIPT}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules["zkai_d128_range_policy_discipline_gate"] = GATE
SPEC.loader.exec_module(GATE)


def tensor(payload: dict[str, object], dimension: str, tensor_id: str) -> dict[str, object]:
    rows = payload["tensor_policies"]
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, dict)
        if row["dimension"] == dimension and row["tensor_id"] == tensor_id:
            return row
    raise AssertionError((dimension, tensor_id))


class D128RangePolicyDisciplineGateTests(unittest.TestCase):
    def test_payload_records_d128_global_q8_no_go(self) -> None:
        payload = GATE.build_gate_result()

        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertTrue(payload["summary"]["all_policies_accept"])
        self.assertTrue(payload["summary"]["d64_global_q8_happens_to_hold"])
        self.assertTrue(payload["summary"]["d128_global_q8_policy_rejected"])
        self.assertEqual(payload["summary"]["d128_hidden_outside_q8_count"], 491)
        self.assertEqual(payload["summary"]["d128_residual_delta_outside_q8_count"], 111)
        self.assertEqual(payload["summary"]["d128_output_outside_q8_count"], 111)
        self.assertEqual(payload["summary"]["d128_max_abs"], 112680)
        self.assertEqual(payload["case_count"], 10)
        self.assertEqual(payload["summary"]["mutations_rejected"], 10)
        self.assertTrue(payload["all_mutations_rejected"])

    def test_d128_hidden_policy_accepts_signed_m31_not_q8(self) -> None:
        payload = GATE.build_gate_result()
        hidden = tensor(payload, "d128", "hidden_activation")

        self.assertEqual(hidden["policy"], "signed_m31_post_swiglu_hidden")
        self.assertEqual(hidden["min"], -99510)
        self.assertEqual(hidden["max"], 112680)
        self.assertEqual(hidden["outside_q8_count"], 491)
        self.assertTrue(hidden["outside_q8_allowed"])
        self.assertTrue(hidden["signed_m31_ok"])
        self.assertTrue(hidden["policy_accepts"])

    def test_d64_fixture_fit_is_not_promoted_to_universal_rule(self) -> None:
        payload = GATE.build_gate_result()
        d64_outside = [
            row
            for row in payload["tensor_policies"]
            if row["dimension"] == "d64" and row["policy"] != "bounded_nonnegative_remainder" and row["outside_q8_count"] > 0
        ]
        d128_outside = [
            row
            for row in payload["tensor_policies"]
            if row["dimension"] == "d128" and row["policy"] != "bounded_nonnegative_remainder" and row["outside_q8_count"] > 0
        ]

        self.assertEqual(d64_outside, [])
        self.assertEqual(
            [row["tensor_id"] for row in d128_outside],
            [
                "gate_projection_output",
                "value_projection_output",
                "hidden_activation",
                "residual_delta",
                "final_output_activation",
            ],
        )

    def test_payload_validation_rejects_policy_relabeling(self) -> None:
        payload = GATE.build_gate_result()
        tensor(payload, "d128", "hidden_activation")["policy"] = "q8_semantic_bound_1024"

        with self.assertRaisesRegex(GATE.D128RangePolicyError, "tensor_policies|core payload drift"):
            GATE.validate_payload(payload)

    def test_payload_validation_rejects_summary_drift(self) -> None:
        payload = GATE.build_gate_result()
        payload["summary"]["d128_global_q8_policy_rejected"] = False

        with self.assertRaisesRegex(GATE.D128RangePolicyError, "summary|core payload drift"):
            GATE.validate_payload(payload)

    def test_payload_validation_rejects_unknown_top_level_field(self) -> None:
        payload = GATE.build_gate_result()
        payload["extra"] = "forbidden"

        with self.assertRaisesRegex(GATE.D128RangePolicyError, "key mismatch"):
            GATE.validate_payload(payload)

    def test_source_schema_drift_is_rejected(self) -> None:
        source = copy.deepcopy(GATE.source_payloads()["d128_activation"])
        spec = next(spec for spec in GATE.SOURCE_SPECS if spec.source_id == "d128_activation")
        source["schema"] = "zkai-d128-activation-swiglu-air-proof-input-v2"

        with self.assertRaisesRegex(GATE.D128RangePolicyError, "schema"):
            GATE.validate_source_payload(source, spec)

    def test_tsv_columns_are_stable(self) -> None:
        payload = GATE.build_gate_result()

        self.assertEqual(GATE.to_tsv(payload).splitlines()[0].split("\t"), list(GATE.TSV_COLUMNS))

    def test_write_outputs_round_trips(self) -> None:
        payload = GATE.build_gate_result()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_out = tmp / "out.json"
            tsv_out = tmp / "out.tsv"
            GATE.write_outputs(payload, json_out, tsv_out)

            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            GATE.validate_payload(loaded)
            self.assertTrue(tsv_out.read_text(encoding="utf-8").startswith("dimension\t"))


if __name__ == "__main__":
    unittest.main()
