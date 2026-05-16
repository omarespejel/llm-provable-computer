import copy
import unittest

from scripts import zkai_native_attention_mlp_source_backed_adapter_selector_gate as gate


class SourceBackedAdapterSelectorGateTests(unittest.TestCase):
    def test_payload_validates_and_rejects_mutations(self) -> None:
        context = gate.build_context()
        payload = gate.build_payload(context)
        gate.validate_payload(payload, context=context)
        cases = payload["mutation_result"]["cases"]
        self.assertEqual([case["name"] for case in cases], list(gate.MUTATION_NAMES))
        self.assertTrue(all(case["rejected"] for case in cases))
        self.assertEqual(payload["summary"]["compact_typed_bytes"], 40_812)
        self.assertEqual(payload["summary"]["compact_typed_delta_vs_two_proof_bytes"], 112)

    def test_frontier_overclaim_is_rejected(self) -> None:
        context = gate.build_context()
        payload = gate.build_payload(context)
        candidate = copy.deepcopy(payload)
        candidate["comparisons"]["compact_vs_two_proof_frontier"]["frontier_win_claimed"] = True
        candidate["payload_commitment"] = gate.payload_commitment(candidate)
        with self.assertRaises(gate.SourceBackedAdapterSelectorError):
            gate.validate_payload(candidate, context=context)

    def test_forged_mutation_result_is_rejected(self) -> None:
        context = gate.build_context()
        payload = gate.build_payload(context)
        candidate = copy.deepcopy(payload)
        candidate["mutation_result"]["cases"][0]["reason"] = "forged"
        candidate["payload_commitment"] = gate.payload_commitment(candidate)
        with self.assertRaises(gate.SourceBackedAdapterSelectorError):
            gate.validate_payload(candidate, context=context)

    def test_duplicate_accounting_row_path_is_rejected(self) -> None:
        context = gate.build_context()
        accounting = copy.deepcopy(context["accounting"])
        accounting["rows"][1]["evidence_relative_path"] = accounting["rows"][0]["evidence_relative_path"]

        with self.assertRaisesRegex(gate.SourceBackedAdapterSelectorError, "duplicate accounting row path"):
            gate.accounting_rows_by_path(accounting)

    def test_accounting_row_path_drift_is_rejected(self) -> None:
        context = gate.build_context()
        accounting = copy.deepcopy(context["accounting"])
        accounting["rows"][1]["evidence_relative_path"] = "unexpected-envelope.json"

        with self.assertRaisesRegex(gate.SourceBackedAdapterSelectorError, "accounting row path drift"):
            gate.accounting_rows_by_path(accounting)

    def test_missing_variant_accounting_row_is_structured_error(self) -> None:
        context = gate.build_context()
        rows = gate.accounting_rows_by_path(context["accounting"])
        rows.pop(gate.EXPECTED_VARIANTS["compact_selector"]["accounting_relative_path"])

        with self.assertRaisesRegex(gate.SourceBackedAdapterSelectorError, "missing accounting row"):
            gate.variant_payload("compact_selector", context, rows)


if __name__ == "__main__":
    unittest.main()
