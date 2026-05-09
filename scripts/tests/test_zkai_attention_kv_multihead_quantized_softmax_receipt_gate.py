import copy
import json
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_multihead_quantized_softmax_receipt_gate as gate


class MultiheadQuantizedSoftmaxReceiptGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = gate.load_sources()
        cls.envelopes = gate.load_envelopes()
        cls.result = gate.build_base_receipt(cls.sources, cls.envelopes)
        cls.result["mutation_results"] = [
            {"name": name, "rejected": True, "error": "covered by mutation-specific unit tests"}
            for name in gate.EXPECTED_MUTATION_NAMES
        ]
        gate.validate_receipt(cls.result, cls.sources, cls.envelopes)

    def test_records_multihead_exact_integer_kernel_without_real_softmax_overclaim(self):
        result = self.result
        contract = result["kernel_contract"]
        metrics = contract["aggregate_metrics"]
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(result["route_id"], gate.ROUTE_ID)
        self.assertEqual(contract["kernel_name"], gate.KERNEL_NAME)
        self.assertEqual(contract["kernel_status"], gate.KERNEL_STATUS)
        self.assertEqual(contract["real_softmax_status"], gate.REAL_SOFTMAX_STATUS)
        self.assertIn("input_steps order", contract["output_order_policy"])
        self.assertEqual(result["profiles_checked"], 4)
        self.assertEqual(result["head_counts_checked"], [2, 4, 8, 16])
        self.assertEqual(metrics["total_heads_checked"], 30)
        self.assertEqual(result["lookup_claims_total"], 1560)
        self.assertEqual(result["score_rows_total"], 1560)
        self.assertEqual(result["fused_proof_size_bytes_sum"], 227357)
        self.assertEqual(result["max_fused_proof_size_bytes"], 65006)
        self.assertEqual(result["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(result["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))

    def test_profile_metrics_recompute_denominators_and_output_mapping(self):
        profiles = {profile["profile_id"]: profile for profile in self.result["kernel_contract"]["profiles"]}
        self.assertEqual(profiles["two_head"]["head_count"], 2)
        self.assertEqual(profiles["two_head"]["sequence_length_per_head"], 8)
        self.assertEqual(profiles["two_head"]["score_rows"], 104)
        self.assertEqual(profiles["two_head"]["lookup_claims"], 104)
        self.assertEqual(profiles["four_head"]["head_count"], 4)
        self.assertEqual(profiles["four_head"]["sequence_length_per_head"], 8)
        self.assertEqual(profiles["four_head"]["score_rows"], 208)
        self.assertEqual(profiles["four_head"]["lookup_claims"], 208)
        self.assertEqual(profiles["eight_head"]["head_count"], 8)
        self.assertEqual(profiles["eight_head"]["sequence_length_per_head"], 8)
        self.assertEqual(profiles["eight_head"]["score_rows"], 416)
        self.assertEqual(profiles["eight_head"]["lookup_claims"], 416)
        self.assertEqual(profiles["sixteen_head"]["head_count"], 16)
        self.assertEqual(profiles["sixteen_head"]["sequence_length_per_head"], 8)
        self.assertEqual(profiles["sixteen_head"]["score_rows"], 832)
        self.assertEqual(profiles["sixteen_head"]["lookup_claims"], 832)
        for profile in profiles.values():
            denominators = profile["per_head_step_denominators"]
            self.assertEqual(len(denominators), profile["head_count"] * profile["sequence_length_per_head"])
            self.assertTrue(all(item["denominator"] > 0 for item in denominators))
            self.assertLess(profile["max_observed_division_error_decimal"], 1.0)
            self.assertRegex(profile["fused_envelope_commitment"], r"^blake2b-256:[0-9a-f]{64}$")
            self.assertRegex(profile["fused_proof_commitment"], r"^blake2b-256:[0-9a-f]{64}$")

    def test_output_index_mapping_uses_input_steps_not_naive_layout(self):
        two_map = gate.output_index_by_head_step(self.sources["two_head"])
        four_map = gate.output_index_by_head_step(self.sources["four_head"])
        self.assertEqual(two_map[(0, 0)], 0)
        self.assertEqual(two_map[(1, 0)], 1)
        self.assertEqual(two_map[(0, 7)], 14)
        self.assertEqual(two_map[(1, 7)], 15)
        self.assertEqual(four_map[(0, 0)], 0)
        self.assertEqual(four_map[(1, 0)], 1)
        self.assertEqual(four_map[(2, 0)], 16)
        self.assertEqual(four_map[(3, 0)], 17)
        self.assertEqual(four_map[(2, 7)], 30)
        self.assertEqual(four_map[(3, 7)], 31)
        eight_map = gate.output_index_by_head_step(self.sources["eight_head"])
        self.assertEqual(eight_map[(0, 0)], 0)
        self.assertEqual(eight_map[(3, 0)], 17)
        self.assertEqual(eight_map[(4, 0)], 32)
        self.assertEqual(eight_map[(7, 0)], 49)
        self.assertEqual(eight_map[(4, 7)], 46)
        self.assertEqual(eight_map[(7, 7)], 63)
        sixteen_map = gate.output_index_by_head_step(self.sources["sixteen_head"])
        self.assertEqual(sixteen_map[(0, 0)], 0)
        self.assertEqual(sixteen_map[(7, 0)], 49)
        self.assertEqual(sixteen_map[(8, 0)], 64)
        self.assertEqual(sixteen_map[(15, 0)], 113)
        self.assertEqual(sixteen_map[(8, 7)], 78)
        self.assertEqual(sixteen_map[(15, 7)], 127)

    def test_all_declared_non_native_mutations_reject(self):
        checked = 0
        for name, receipt, sources, envelopes, native_profile_ids in gate.mutation_cases(
            self.result, self.sources, self.envelopes
        ):
            if native_profile_ids:
                continue
            with self.assertRaises(gate.MultiheadQuantizedSoftmaxReceiptGateError, msg=name):
                gate.validate_receipt(receipt, sources, envelopes, native_profile_ids=native_profile_ids)
            checked += 1
        self.assertEqual(
            checked,
            sum(1 for case in gate.mutation_cases(self.result, self.sources, self.envelopes) if not case[4]),
        )

    def test_run_gate_invokes_all_native_backing_gates(self):
        with mock.patch.object(gate.two_head_fused_gate, "run_gate") as two_head_run_gate:
            with mock.patch.object(gate.four_head_fused_gate, "run_gate") as four_head_run_gate:
                with mock.patch.object(gate.eight_head_fused_gate, "run_gate") as eight_head_run_gate:
                    with mock.patch.object(gate.sixteen_head_fused_gate, "run_gate") as sixteen_head_run_gate:
                        with mock.patch.object(gate, "mutation_cases", return_value=[]):
                            with mock.patch.object(gate, "validate_receipt"):
                                result = gate.run_gate()

        two_head_run_gate.assert_called_once_with()
        four_head_run_gate.assert_called_once_with()
        eight_head_run_gate.assert_called_once_with()
        sixteen_head_run_gate.assert_called_once_with()
        self.assertEqual(result["decision"], gate.DECISION)

    def test_fused_proof_tamper_rejects_without_native_verifier(self):
        proof_tamper_cases = [
            case for case in gate.mutation_cases(self.result, self.sources, self.envelopes) if "proof_byte_tamper" in case[0]
        ]
        self.assertEqual(
            [case[0] for case in proof_tamper_cases],
            [
                "fused_two_head_proof_byte_tamper",
                "fused_four_head_proof_byte_tamper",
                "fused_eight_head_proof_byte_tamper",
                "fused_sixteen_head_proof_byte_tamper",
            ],
        )
        self.assertTrue(all(not case[4] for case in proof_tamper_cases))
        for name, receipt, sources, envelopes, native_profile_ids in proof_tamper_cases:
            with self.assertRaisesRegex(
                gate.MultiheadQuantizedSoftmaxReceiptGateError,
                "kernel contract|kernel_contract",
                msg=name,
            ):
                gate.validate_receipt(receipt, sources, envelopes, native_profile_ids=native_profile_ids)

    def test_validate_result_defaults_to_structural_validation_only(self):
        with mock.patch.object(gate, "load_sources", return_value=self.sources):
            with mock.patch.object(gate, "load_envelopes", return_value=self.envelopes):
                with mock.patch.object(gate, "validate_receipt") as validate_receipt:
                    gate.validate_result(self.result)
        validate_receipt.assert_called_once_with(
            self.result,
            self.sources,
            self.envelopes,
            native_profile_ids=set(),
        )

    def test_validate_result_can_opt_into_all_native_profiles(self):
        with mock.patch.object(gate, "load_sources", return_value=self.sources):
            with mock.patch.object(gate, "load_envelopes", return_value=self.envelopes):
                with mock.patch.object(gate, "validate_receipt") as validate_receipt:
                    gate.validate_result(self.result, run_native=True)
        validate_receipt.assert_called_once_with(
            self.result,
            self.sources,
            self.envelopes,
            native_profile_ids=set(gate.profile_ids()),
        )

    def test_rejects_source_denominator_remainder_and_causal_mask_drift(self):
        source = copy.deepcopy(self.sources["two_head"])
        source["score_rows"][0]["weight_denominator"] = 0
        with self.assertRaisesRegex(gate.MultiheadQuantizedSoftmaxReceiptGateError, "validation drift|denominator"):
            gate.validate_quantized_kernel_for_profile(
                gate.PROFILE_BY_ID["two_head"],
                source,
                self.envelopes["two_head"],
            )

        source = copy.deepcopy(self.sources["two_head"])
        source["score_rows"][0]["output_remainder"][0] = 999
        with self.assertRaisesRegex(gate.MultiheadQuantizedSoftmaxReceiptGateError, "validation drift|quotient|remainder"):
            gate.validate_quantized_kernel_for_profile(
                gate.PROFILE_BY_ID["two_head"],
                source,
                self.envelopes["two_head"],
            )

        source = copy.deepcopy(self.sources["two_head"])
        source["score_rows"][0]["candidate_position"] = source["score_rows"][0]["token_position"] + 1
        with self.assertRaisesRegex(gate.MultiheadQuantizedSoftmaxReceiptGateError, "validation drift|causal mask"):
            gate.validate_quantized_kernel_for_profile(
                gate.PROFILE_BY_ID["two_head"],
                source,
                self.envelopes["two_head"],
            )

        source = copy.deepcopy(self.sources["two_head"])
        head_step = (source["score_rows"][0]["head_index"], source["score_rows"][0]["step_index"])
        for row in source["score_rows"]:
            if (row["head_index"], row["step_index"]) == head_step:
                row["token_position"] += 1
        with self.assertRaisesRegex(gate.MultiheadQuantizedSoftmaxReceiptGateError, "validation drift|token-position"):
            gate.validate_quantized_kernel_for_profile(
                gate.PROFILE_BY_ID["two_head"],
                source,
                self.envelopes["two_head"],
            )

    def test_rejects_coherent_output_vector_truncation(self):
        source = copy.deepcopy(self.sources["two_head"])
        row = source["score_rows"][0]
        row["attention_output"] = row["attention_output"][:-1]
        row["output_remainder"] = row["output_remainder"][:-1]
        row["weighted_numerator"] = row["weighted_numerator"][:-1]
        with self.assertRaisesRegex(gate.MultiheadQuantizedSoftmaxReceiptGateError, "validation drift|vector length"):
            gate.validate_quantized_kernel_for_profile(
                gate.PROFILE_BY_ID["two_head"],
                source,
                self.envelopes["two_head"],
            )

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            json_path = tmp_dir / "receipt.json"
            tsv_path = tmp_dir / "receipt.tsv"
            gate.write_json(json_path, self.result)
            gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["decision"], gate.DECISION)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn(gate.ROUTE_ID, tsv)
            self.assertIn(gate.REAL_SOFTMAX_STATUS, tsv)
            self.assertIn("2,4,8,16", tsv)

    def test_write_json_rejects_overclaim_or_unknown_key(self):
        payload = copy.deepcopy(self.result)
        payload["kernel_contract"]["real_softmax_status"] = "GO_REAL_VALUED_SOFTMAX"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.MultiheadQuantizedSoftmaxReceiptGateError, "kernel_contract|kernel contract"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

        payload = copy.deepcopy(self.result)
        payload["unexpected"] = "claim smuggling"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.MultiheadQuantizedSoftmaxReceiptGateError, "unknown receipt field"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

    def test_write_json_rejects_mutation_result_shape_drift(self):
        payload = copy.deepcopy(self.result)
        payload["mutation_results"][0]["rejected"] = False
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.MultiheadQuantizedSoftmaxReceiptGateError, "mutation result rejection drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)


if __name__ == "__main__":
    unittest.main()
