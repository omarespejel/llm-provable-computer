import copy
import json
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate as gate


class AttentionKvSoftmaxDenominatorRoundingEdgeCorpusGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = gate.build_result()
        cls.by_name = {case["name"]: case for case in cls.result["edge_cases"]}

    def test_build_result_records_edge_corpus_go(self):
        gate.validate_result(self.result)
        self.assertEqual(self.result["decision"], gate.DECISION)
        self.assertEqual(self.result["edge_case_count"], len(gate.EDGE_CASE_NAMES))
        self.assertEqual(self.result["route_mutations_checked"], len(gate.ROUTE_MUTATION_NAMES))
        self.assertEqual(self.result["route_mutations_rejected"], len(gate.ROUTE_MUTATION_NAMES))
        self.assertIn("NOT_REAL_VALUED_SOFTMAX", self.result["claim_boundary"])
        self.assertIn("NOT_NEW_PROOF", self.result["claim_boundary"])

    def test_all_scores_equal_denominator(self):
        case = self.by_name["all_scores_equal"]
        self.assertEqual(case["weights"], [256, 256, 256])
        self.assertEqual(case["denominator"], 768)
        self.assertEqual(case["outputs"][0], 5)

    def test_single_allowed_candidate_min_denominator(self):
        case = self.by_name["single_allowed_candidate_min_denominator"]
        self.assertEqual(case["candidate_count"], 1)
        self.assertEqual(case["denominator"], 256)
        self.assertEqual(case["outputs"][:2], [5, -3])

    def test_all_nonmax_scores_clipped_denominator(self):
        case = self.by_name["all_nonmax_scores_clipped"]
        self.assertEqual(case["clipped_gaps"], [0, 8, 8, 8])
        self.assertEqual(case["weights"], [256, 16, 16, 16])
        self.assertEqual(case["denominator"], 304)
        self.assertEqual(case["max_remainder_ratio"], "0.842105")

    def test_dominant_key_matches_clipped_denominator_family(self):
        case = self.by_name["one_dominant_key_all_others_clipped"]
        self.assertEqual(case["weights"], [256, 16, 16, 16])
        self.assertEqual(case["denominator"], 304)
        self.assertEqual(case["clipped_gaps"].count(gate.SCORE_GAP_CLIP), 3)

    def test_negative_numerator_floor_has_nonnegative_remainder(self):
        case = self.by_name["negative_numerator_floor_division"]
        self.assertGreater(case["negative_numerator_dimensions"], 0)
        for numerator, output, remainder in zip(case["numerators"], case["outputs"], case["remainders"], strict=True):
            self.assertEqual(numerator, output * case["denominator"] + remainder)
            self.assertGreaterEqual(remainder, 0)
            self.assertLess(remainder, case["denominator"])

    def test_table_entry_multiplicity_covers_every_gap(self):
        case = self.by_name["table_entry_multiplicity_extremes"]
        multiplicities = {row["gap"]: row["multiplicity"] for row in case["table_multiplicities"]}
        for gap in range(gate.SCORE_GAP_CLIP + 1):
            self.assertGreaterEqual(multiplicities[gap], 1)
        self.assertEqual(case["candidate_count"], 10)

    def test_route_mutations_all_rejected(self):
        self.assertEqual(
            [row["name"] for row in self.result["route_mutation_results"]],
            list(gate.ROUTE_MUTATION_NAMES),
        )
        self.assertTrue(all(row["rejected"] for row in self.result["route_mutation_results"]))
        self.assertTrue(all(row["error"].endswith("Error") for row in self.result["route_mutation_results"]))
        self.assertIn("sidecar_matching_source_negative_remainder", gate.ROUTE_MUTATION_NAMES)
        self.assertIn("fused_matching_source_negative_remainder", gate.ROUTE_MUTATION_NAMES)

    def test_rejects_pristine_artifact_validation_drift(self):
        with mock.patch.object(
            gate.source_gate,
            "validate_source_pair",
            side_effect=gate.source_gate.AttentionKvBoundedSoftmaxTableNativeGateError("source drift"),
        ):
            with self.assertRaisesRegex(gate.SoftmaxEdgeCorpusGateError, "pristine artifact validation drift"):
                gate.route_rejection_results()

    def test_rejects_route_mutation_result_drift(self):
        mutated = copy.deepcopy(self.result)
        mutated["route_mutation_results"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.SoftmaxEdgeCorpusGateError, "route mutation result drift"):
            gate.validate_result(mutated)

    def test_rejects_claim_boundary_drift(self):
        mutated = copy.deepcopy(self.result)
        mutated["claim_boundary"] = mutated["claim_boundary"].replace("NOT_REAL_VALUED_SOFTMAX_", "")
        with self.assertRaisesRegex(gate.SoftmaxEdgeCorpusGateError, "result drift for claim_boundary"):
            gate.validate_result(mutated)

    def test_rejects_max_remainder_ratio_drift(self):
        mutated = copy.deepcopy(self.result)
        mutated["max_remainder_ratio"] = "0.842106"
        with self.assertRaisesRegex(gate.SoftmaxEdgeCorpusGateError, "max remainder ratio drift"):
            gate.validate_result(mutated)

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = gate.pathlib.Path(tmp)
            json_path = tmp / "edge-corpus.json"
            tsv_path = tmp / "edge-corpus.tsv"
            gate.write_json(json_path, self.result)
            gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            gate.validate_result(loaded)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn(gate.DECISION, tsv)
            self.assertIn("304", tsv)
            self.assertIn("negative_numerator_floor_division", tsv)


if __name__ == "__main__":
    unittest.main()
