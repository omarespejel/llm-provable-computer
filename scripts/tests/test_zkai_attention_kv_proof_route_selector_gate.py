from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "zkai_attention_kv_proof_route_selector_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_kv_proof_route_selector_gate", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load {SCRIPT}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionKvProofRouteSelectorGateTests(unittest.TestCase):
    def test_selector_revalidates_quantized_receipts_with_native_backing_proofs(self) -> None:
        GATE._load_quantized_softmax_receipt_payload.cache_clear()
        GATE._load_multihead_quantized_softmax_receipt_payload.cache_clear()
        GATE._load_longseq_fused_softmax_payload.cache_clear()
        GATE._load_d16_fused_softmax_payload.cache_clear()
        GATE._load_d16_two_head_fused_softmax_payload.cache_clear()
        GATE._load_d16_two_head_longseq_fused_softmax_payload.cache_clear()
        GATE._load_d16_quantized_softmax_receipt_payload.cache_clear()
        GATE._load_d16_two_head_quantized_softmax_receipt_payload.cache_clear()
        GATE._load_softmax_edge_corpus_payload.cache_clear()
        try:
            with mock.patch.object(GATE.QUANTIZED_SOFTMAX, "validate_result") as validate_single:
                GATE.load_quantized_softmax_receipt_payload(run_native=True)
            validate_single.assert_called_once()
            self.assertEqual(validate_single.call_args.kwargs, {"run_native": True})

            with mock.patch.object(GATE.MULTIHEAD_QUANTIZED_SOFTMAX, "validate_result") as validate_multihead:
                GATE.load_multihead_quantized_softmax_receipt_payload(run_native=True)
            validate_multihead.assert_called_once()
            self.assertEqual(validate_multihead.call_args.kwargs, {"run_native": True})

            with mock.patch.object(GATE.LONGSEQ_FUSED_SOFTMAX, "validate_fused_envelope") as validate_longseq:
                GATE.load_longseq_fused_softmax_payload(run_native=True)
            self.assertTrue(any(call.kwargs.get("run_native") is True for call in validate_longseq.call_args_list))

            with mock.patch.object(GATE.D16_FUSED_SOFTMAX, "validate_fused_envelope") as validate_d16:
                GATE.load_d16_fused_softmax_payload(run_native=True)
            self.assertTrue(any(call.kwargs.get("run_native") is True for call in validate_d16.call_args_list))

            with mock.patch.object(
                GATE.D16_TWO_HEAD_FUSED_SOFTMAX,
                "validate_fused_envelope",
            ) as validate_d16_two_head:
                GATE.load_d16_two_head_fused_softmax_payload(run_native=True)
            self.assertTrue(any(call.kwargs.get("run_native") is True for call in validate_d16_two_head.call_args_list))

            with mock.patch.object(
                GATE.D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX,
                "validate_fused_envelope",
            ) as validate_d16_two_head_longseq:
                GATE.load_d16_two_head_longseq_fused_softmax_payload(run_native=True)
            self.assertTrue(
                any(call.kwargs.get("run_native") is True for call in validate_d16_two_head_longseq.call_args_list)
            )

            with mock.patch.object(GATE.D16_QUANTIZED_SOFTMAX, "validate_result") as validate_d16_quantized:
                GATE.load_d16_quantized_softmax_receipt_payload(run_native=True)
            validate_d16_quantized.assert_called_once()
            self.assertEqual(validate_d16_quantized.call_args.kwargs, {"run_native": True})

            with mock.patch.object(
                GATE.D16_TWO_HEAD_QUANTIZED_SOFTMAX,
                "validate_result",
            ) as validate_d16_two_head_quantized:
                GATE.load_d16_two_head_quantized_softmax_receipt_payload(run_native=True)
            validate_d16_two_head_quantized.assert_called_once()
            self.assertEqual(validate_d16_two_head_quantized.call_args.kwargs, {"run_native": True})
        finally:
            GATE._load_quantized_softmax_receipt_payload.cache_clear()
            GATE._load_multihead_quantized_softmax_receipt_payload.cache_clear()
            GATE._load_longseq_fused_softmax_payload.cache_clear()
            GATE._load_d16_fused_softmax_payload.cache_clear()
            GATE._load_d16_two_head_fused_softmax_payload.cache_clear()
            GATE._load_d16_two_head_longseq_fused_softmax_payload.cache_clear()
            GATE._load_d16_quantized_softmax_receipt_payload.cache_clear()
            GATE._load_d16_two_head_quantized_softmax_receipt_payload.cache_clear()
            GATE._load_softmax_edge_corpus_payload.cache_clear()

    def test_selector_default_receipt_loaders_are_structural_only(self) -> None:
        GATE._load_quantized_softmax_receipt_payload.cache_clear()
        GATE._load_multihead_quantized_softmax_receipt_payload.cache_clear()
        GATE._load_longseq_fused_softmax_payload.cache_clear()
        GATE._load_d16_fused_softmax_payload.cache_clear()
        GATE._load_d16_two_head_fused_softmax_payload.cache_clear()
        GATE._load_d16_two_head_longseq_fused_softmax_payload.cache_clear()
        GATE._load_d16_quantized_softmax_receipt_payload.cache_clear()
        GATE._load_d16_two_head_quantized_softmax_receipt_payload.cache_clear()
        GATE._load_softmax_edge_corpus_payload.cache_clear()
        try:
            with mock.patch.object(GATE.QUANTIZED_SOFTMAX, "validate_result") as validate_single:
                GATE.load_quantized_softmax_receipt_payload()
            validate_single.assert_called_once()
            self.assertEqual(validate_single.call_args.kwargs, {"run_native": False})

            with mock.patch.object(GATE.MULTIHEAD_QUANTIZED_SOFTMAX, "validate_result") as validate_multihead:
                GATE.load_multihead_quantized_softmax_receipt_payload()
            validate_multihead.assert_called_once()
            self.assertEqual(validate_multihead.call_args.kwargs, {"run_native": False})

            with mock.patch.object(GATE.LONGSEQ_FUSED_SOFTMAX, "validate_fused_envelope") as validate_longseq:
                GATE.load_longseq_fused_softmax_payload()
            self.assertFalse(any(call.kwargs.get("run_native") is True for call in validate_longseq.call_args_list))

            with mock.patch.object(GATE.D16_FUSED_SOFTMAX, "validate_fused_envelope") as validate_d16:
                GATE.load_d16_fused_softmax_payload()
            self.assertFalse(any(call.kwargs.get("run_native") is True for call in validate_d16.call_args_list))

            with mock.patch.object(
                GATE.D16_TWO_HEAD_FUSED_SOFTMAX,
                "validate_fused_envelope",
            ) as validate_d16_two_head:
                GATE.load_d16_two_head_fused_softmax_payload()
            self.assertFalse(any(call.kwargs.get("run_native") is True for call in validate_d16_two_head.call_args_list))

            with mock.patch.object(
                GATE.D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX,
                "validate_fused_envelope",
            ) as validate_d16_two_head_longseq:
                GATE.load_d16_two_head_longseq_fused_softmax_payload()
            self.assertFalse(
                any(call.kwargs.get("run_native") is True for call in validate_d16_two_head_longseq.call_args_list)
            )

            with mock.patch.object(GATE.D16_QUANTIZED_SOFTMAX, "validate_result") as validate_d16_quantized:
                GATE.load_d16_quantized_softmax_receipt_payload()
            validate_d16_quantized.assert_called_once()
            self.assertEqual(validate_d16_quantized.call_args.kwargs, {"run_native": False})

            with mock.patch.object(
                GATE.D16_TWO_HEAD_QUANTIZED_SOFTMAX,
                "validate_result",
            ) as validate_d16_two_head_quantized:
                GATE.load_d16_two_head_quantized_softmax_receipt_payload()
            validate_d16_two_head_quantized.assert_called_once()
            self.assertEqual(validate_d16_two_head_quantized.call_args.kwargs, {"run_native": False})
        finally:
            GATE._load_quantized_softmax_receipt_payload.cache_clear()
            GATE._load_multihead_quantized_softmax_receipt_payload.cache_clear()
            GATE._load_longseq_fused_softmax_payload.cache_clear()
            GATE._load_d16_fused_softmax_payload.cache_clear()
            GATE._load_d16_two_head_fused_softmax_payload.cache_clear()
            GATE._load_d16_two_head_longseq_fused_softmax_payload.cache_clear()
            GATE._load_d16_quantized_softmax_receipt_payload.cache_clear()
            GATE._load_d16_two_head_quantized_softmax_receipt_payload.cache_clear()
            GATE._load_softmax_edge_corpus_payload.cache_clear()

    def test_regression_issue_448_records_native_stwo_and_external_control_routes(self) -> None:
        payload = GATE.build_payload()

        self.assertEqual(len(GATE.EXPECTED_MUTATION_NAMES), 93)
        self.assertIn("multihead_quantized_softmax_trace_rows_drift", GATE.EXPECTED_MUTATION_NAMES)
        self.assertIn(
            "multihead_quantized_softmax_trace_rows_drift",
            [case["name"] for case in payload["mutation_cases"]],
        )
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["first_blocker"], GATE.FIRST_BLOCKER)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertEqual(payload["source_contract"]["source_decision"], GATE.SOURCE.DECISION)
        self.assertEqual(payload["source_contract"]["source_proof_status"], "SOURCE_BACKED_RECEIPT_NOT_PROVEN")
        self.assertEqual(payload["source_contract"]["present_public_fields"], list(GATE.REQUIRED_PUBLIC_FIELDS))
        self.assertEqual(
            payload["proof_backed_routes_available"],
            [
                "local_stwo_attention_kv_d8_masked_sequence_proof",
                "local_stwo_attention_kv_d8_quantized_softmax_table_kernel_receipt",
                "local_stwo_attention_kv_multihead_quantized_softmax_table_kernel_receipt",
                "local_stwo_attention_kv_two_head_longseq_fused_bounded_softmax_table_logup_proof",
                "local_stwo_attention_kv_d16_fused_bounded_softmax_table_logup_proof",
                "local_stwo_attention_kv_d16_two_head_fused_bounded_softmax_table_logup_proof",
                "local_stwo_attention_kv_d16_two_head_longseq_fused_bounded_softmax_table_logup_proof",
                "local_stwo_attention_kv_d16_quantized_softmax_table_kernel_receipt",
                "local_stwo_attention_kv_d16_two_head_quantized_softmax_table_kernel_receipt",
                "external_snark_attention_kv_statement_receipt",
                "external_zkvm_attention_kv_semantics_receipt",
                "external_zkvm_attention_kv_sequence_semantics_receipt",
                "external_zkvm_attention_kv_scaled_sequence_semantics_receipt",
                "external_zkvm_attention_kv_wide_masked_sequence_semantics_receipt",
            ],
        )
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["decision"], GATE.LOCAL_STWO_PROOF_DECISION)
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["proof_size_bytes"], 24394)
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["envelope_size_bytes"], 265791)
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["sequence_length"], 8)
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["score_row_count"], 52)
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["trace_row_count"], 64)
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["key_width"], 8)
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["value_width"], 8)
        self.assertEqual(
            payload["native_stwo_masked_sequence_receipt"]["masking_policy"],
            "causal_prefix_position_lte_query_token",
        )
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["tie_break"], "lowest_position")
        self.assertEqual(
            payload["native_stwo_masked_sequence_receipt"]["selected_positions"],
            [0, 2, 3, 3, 5, 5, 7, 9],
        )
        self.assertEqual(payload["native_stwo_masked_sequence_receipt"]["final_kv_items"], 10)
        self.assertEqual(payload["quantized_softmax_receipt"]["decision"], GATE.QUANTIZED_SOFTMAX_DECISION)
        self.assertEqual(payload["quantized_softmax_receipt"]["route_id"], GATE.QUANTIZED_SOFTMAX_ROUTE_ID)
        self.assertEqual(payload["quantized_softmax_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["quantized_softmax_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["quantized_softmax_receipt"]["proof_size_bytes"], 47698)
        self.assertEqual(payload["quantized_softmax_receipt"]["lookup_claims"], 52)
        self.assertEqual(payload["quantized_softmax_receipt"]["table_rows"], 9)
        self.assertEqual(payload["quantized_softmax_receipt"]["score_gap_clip"], 8)
        self.assertEqual(payload["quantized_softmax_receipt"]["steps"], 8)
        self.assertEqual(payload["quantized_softmax_receipt"]["score_rows"], 52)
        self.assertEqual(payload["quantized_softmax_receipt"]["real_softmax_status"], GATE.QUANTIZED_SOFTMAX.REAL_SOFTMAX_STATUS)
        self.assertIn("< 1 output unit", payload["quantized_softmax_receipt"]["division_error_bound"])
        self.assertIn("no real-valued Softmax", payload["quantized_softmax_receipt"]["table_error_bound_policy"])
        self.assertEqual(payload["quantized_softmax_receipt"]["mutations_checked"], GATE.QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT)
        self.assertEqual(payload["quantized_softmax_receipt"]["mutations_rejected"], GATE.QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT)
        self.assertEqual(
            payload["multihead_quantized_softmax_receipt"]["decision"],
            GATE.MULTIHEAD_QUANTIZED_SOFTMAX_DECISION,
        )
        self.assertEqual(
            payload["multihead_quantized_softmax_receipt"]["route_id"],
            GATE.MULTIHEAD_QUANTIZED_SOFTMAX_ROUTE_ID,
        )
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["profiles_checked"], 4)
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["head_counts_checked"], [2, 4, 8, 16])
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["lookup_claims_total"], 1560)
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["score_rows_total"], 1560)
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["trace_rows_total"], 1920)
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["fused_proof_size_bytes_sum"], 227357)
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["max_fused_proof_size_bytes"], 65006)
        self.assertEqual(payload["multihead_quantized_softmax_receipt"]["real_softmax_status"], GATE.MULTIHEAD_QUANTIZED_SOFTMAX.REAL_SOFTMAX_STATUS)
        self.assertIn("input_steps order", payload["multihead_quantized_softmax_receipt"]["output_order_policy"])
        self.assertEqual(len(payload["multihead_quantized_softmax_receipt"]["profile_fused_envelope_commitments"]), 4)
        self.assertEqual(len(payload["multihead_quantized_softmax_receipt"]["profile_fused_proof_commitments"]), 4)
        self.assertTrue(
            all(
                commitment.startswith("blake2b-256:")
                for commitment in payload["multihead_quantized_softmax_receipt"]["profile_fused_proof_commitments"]
            )
        )
        self.assertEqual(
            payload["multihead_quantized_softmax_receipt"]["mutations_checked"],
            GATE.MULTIHEAD_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["multihead_quantized_softmax_receipt"]["mutations_rejected"],
            GATE.MULTIHEAD_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["decision"], GATE.LONGSEQ_FUSED_SOFTMAX_DECISION)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["route_id"], GATE.LONGSEQ_FUSED_SOFTMAX_ROUTE_ID)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["source_head_count"], 2)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["sequence_length_per_head"], 16)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["lookup_claims"], 336)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["trace_rows"], 512)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["fused_proof_size_bytes"], 60502)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["fused_envelope_size_bytes"], 1050248)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["source_plus_sidecar_raw_proof_bytes"], 79444)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["fused_saves_vs_source_plus_sidecar_bytes"], 18942)
        self.assertEqual(payload["longseq_fused_softmax_receipt"]["fused_to_source_plus_sidecar_ratio"], "0.761568")
        self.assertIn("not a long-context benchmark", payload["longseq_fused_softmax_receipt"]["non_claims"])
        self.assertEqual(
            payload["longseq_fused_softmax_receipt"]["mutations_checked"],
            GATE.LONGSEQ_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["longseq_fused_softmax_receipt"]["mutations_rejected"],
            GATE.LONGSEQ_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(payload["d16_fused_softmax_receipt"]["decision"], GATE.D16_FUSED_SOFTMAX_DECISION)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["route_id"], GATE.D16_FUSED_SOFTMAX_ROUTE_ID)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["d16_fused_softmax_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["d16_fused_softmax_receipt"]["key_width"], 16)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["value_width"], 16)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["lookup_claims"], 52)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["trace_rows"], 64)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["fused_proof_size_bytes"], 64503)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["fused_envelope_size_bytes"], 666515)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["source_plus_sidecar_raw_proof_bytes"], 74961)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["fused_saves_vs_source_plus_sidecar_bytes"], 10458)
        self.assertEqual(payload["d16_fused_softmax_receipt"]["fused_to_source_plus_sidecar_ratio"], "0.860487")
        self.assertTrue(
            payload["d16_fused_softmax_receipt"]["fused_envelope_commitment"].startswith("blake2b-256:")
        )
        self.assertTrue(payload["d16_fused_softmax_receipt"]["fused_proof_commitment"].startswith("blake2b-256:"))
        self.assertIn("not exact Softmax attention", payload["d16_fused_softmax_receipt"]["non_claims"])
        self.assertEqual(
            payload["d16_fused_softmax_receipt"]["mutations_checked"],
            GATE.D16_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["d16_fused_softmax_receipt"]["mutations_rejected"],
            GATE.D16_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["d16_two_head_fused_softmax_receipt"]["decision"],
            GATE.D16_TWO_HEAD_FUSED_SOFTMAX_DECISION,
        )
        self.assertEqual(
            payload["d16_two_head_fused_softmax_receipt"]["route_id"],
            GATE.D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID,
        )
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["key_width"], 16)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["value_width"], 16)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["head_count"], 2)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["lookup_claims"], 104)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["trace_rows"], 128)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["source_proof_size_bytes"], 73508)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["sidecar_proof_size_bytes"], 18088)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["source_plus_sidecar_raw_proof_bytes"], 91596)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["fused_proof_size_bytes"], 78211)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["fused_envelope_size_bytes"], 921008)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["fused_saves_vs_source_plus_sidecar_bytes"], 13385)
        self.assertEqual(payload["d16_two_head_fused_softmax_receipt"]["fused_to_source_plus_sidecar_ratio"], "0.853869")
        self.assertIn("not exact Softmax attention", payload["d16_two_head_fused_softmax_receipt"]["non_claims"])
        self.assertEqual(
            payload["d16_two_head_fused_softmax_receipt"]["mutations_checked"],
            GATE.D16_TWO_HEAD_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["d16_two_head_fused_softmax_receipt"]["mutations_rejected"],
            GATE.D16_TWO_HEAD_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["d16_two_head_longseq_fused_softmax_receipt"]["decision"],
            GATE.D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_DECISION,
        )
        self.assertEqual(
            payload["d16_two_head_longseq_fused_softmax_receipt"]["route_id"],
            GATE.D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_ROUTE_ID,
        )
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["key_width"], 16)
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["value_width"], 16)
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["head_count"], 2)
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["sequence_length_per_head"], 16)
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["lookup_claims"], 336)
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["trace_rows"], 512)
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["source_proof_size_bytes"], 83330)
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["sidecar_proof_size_bytes"], 24828)
        self.assertEqual(
            payload["d16_two_head_longseq_fused_softmax_receipt"]["source_plus_sidecar_raw_proof_bytes"],
            108158,
        )
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["fused_proof_size_bytes"], 84868)
        self.assertEqual(payload["d16_two_head_longseq_fused_softmax_receipt"]["fused_envelope_size_bytes"], 1569707)
        self.assertEqual(
            payload["d16_two_head_longseq_fused_softmax_receipt"]["fused_saves_vs_source_plus_sidecar_bytes"],
            23290,
        )
        self.assertEqual(
            payload["d16_two_head_longseq_fused_softmax_receipt"]["fused_to_source_plus_sidecar_ratio"],
            "0.784667",
        )
        self.assertIn("not exact Softmax attention", payload["d16_two_head_longseq_fused_softmax_receipt"]["non_claims"])
        self.assertEqual(
            payload["d16_two_head_longseq_fused_softmax_receipt"]["mutations_checked"],
            GATE.D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["d16_two_head_longseq_fused_softmax_receipt"]["mutations_rejected"],
            GATE.D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["decision"], GATE.D16_QUANTIZED_SOFTMAX_DECISION)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["route_id"], GATE.D16_QUANTIZED_SOFTMAX_ROUTE_ID)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["proof_size_bytes"], 64503)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["key_width"], 16)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["value_width"], 16)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["sequence_length"], 8)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["lookup_claims"], 52)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["table_rows"], 9)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["score_gap_clip"], 8)
        self.assertEqual(payload["d16_quantized_softmax_receipt"]["real_softmax_status"], GATE.D16_QUANTIZED_SOFTMAX.REAL_SOFTMAX_STATUS)
        self.assertIn("< 1 output unit", payload["d16_quantized_softmax_receipt"]["division_error_bound"])
        self.assertIn("no real-valued Softmax", payload["d16_quantized_softmax_receipt"]["table_error_bound_policy"])
        self.assertEqual(
            payload["d16_quantized_softmax_receipt"]["mutations_checked"],
            GATE.D16_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["d16_quantized_softmax_receipt"]["mutations_rejected"],
            GATE.D16_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["d16_two_head_quantized_softmax_receipt"]["decision"],
            GATE.D16_TWO_HEAD_QUANTIZED_SOFTMAX_DECISION,
        )
        self.assertEqual(
            payload["d16_two_head_quantized_softmax_receipt"]["route_id"],
            GATE.D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID,
        )
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["proof_system"], "Stwo")
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["proof_backend"], "stwo")
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["proof_size_bytes"], 78211)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["envelope_size_bytes"], 921008)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["key_width"], 16)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["value_width"], 16)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["head_count"], 2)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["sequence_length_per_head"], 8)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["input_steps"], 16)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["lookup_claims"], 104)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["table_rows"], 9)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["score_rows"], 104)
        self.assertEqual(payload["d16_two_head_quantized_softmax_receipt"]["trace_rows"], 128)
        self.assertEqual(
            payload["d16_two_head_quantized_softmax_receipt"]["real_softmax_status"],
            GATE.D16_TWO_HEAD_QUANTIZED_SOFTMAX.REAL_SOFTMAX_STATUS,
        )
        self.assertIn(
            "input_steps order",
            payload["d16_two_head_quantized_softmax_receipt"]["output_order_policy"],
        )
        self.assertIn("< 1 output unit", payload["d16_two_head_quantized_softmax_receipt"]["division_error_bound"])
        self.assertIn(
            "no real-valued Softmax",
            payload["d16_two_head_quantized_softmax_receipt"]["table_error_bound_policy"],
        )
        self.assertEqual(
            len(payload["d16_two_head_quantized_softmax_receipt"]["per_head_step_denominators"]),
            16,
        )
        self.assertTrue(
            all(
                item["denominator"] > 0
                for item in payload["d16_two_head_quantized_softmax_receipt"]["per_head_step_denominators"]
            )
        )
        self.assertEqual(
            payload["d16_two_head_quantized_softmax_receipt"]["mutations_checked"],
            GATE.D16_TWO_HEAD_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["d16_two_head_quantized_softmax_receipt"]["mutations_rejected"],
            GATE.D16_TWO_HEAD_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT,
        )
        self.assertEqual(
            payload["softmax_denominator_rounding_edge_corpus"]["decision"],
            GATE.SOFTMAX_EDGE_CORPUS.DECISION,
        )
        self.assertEqual(payload["softmax_denominator_rounding_edge_corpus"]["edge_case_count"], 7)
        self.assertEqual(payload["softmax_denominator_rounding_edge_corpus"]["route_mutations_checked"], 9)
        self.assertEqual(payload["softmax_denominator_rounding_edge_corpus"]["route_mutations_rejected"], 9)
        self.assertEqual(payload["softmax_denominator_rounding_edge_corpus"]["min_denominator"], 256)
        self.assertEqual(payload["softmax_denominator_rounding_edge_corpus"]["max_denominator"], 852)
        self.assertIn(
            "NOT_REAL_VALUED_SOFTMAX",
            payload["softmax_denominator_rounding_edge_corpus"]["claim_boundary"],
        )
        self.assertEqual(payload["external_snark_receipt"]["decision"], GATE.SNARK.DECISION)
        self.assertEqual(payload["external_risc0_receipt"]["decision"], GATE.RISC0.DECISION)
        self.assertEqual(payload["external_risc0_receipt"]["next_kv_items"], 3)
        self.assertEqual(len(payload["external_risc0_receipt"]["next_kv_cache"]), 3)
        self.assertEqual(payload["external_risc0_sequence_receipt"]["decision"], GATE.RISC0_SEQUENCE.DECISION)
        self.assertEqual(payload["external_risc0_sequence_receipt"]["sequence_length"], 3)
        self.assertEqual(payload["external_risc0_sequence_receipt"]["transition_rows"], 3)
        self.assertEqual(payload["external_risc0_sequence_receipt"]["selected_positions"], [0, 2, 3])
        self.assertEqual(payload["external_risc0_sequence_receipt"]["final_kv_items"], 5)
        self.assertEqual(payload["external_risc0_scaled_sequence_receipt"]["decision"], GATE.RISC0_SCALED_SEQUENCE.DECISION)
        self.assertEqual(payload["external_risc0_scaled_sequence_receipt"]["sequence_length"], 8)
        self.assertEqual(payload["external_risc0_scaled_sequence_receipt"]["transition_rows"], 8)
        self.assertEqual(
            payload["external_risc0_scaled_sequence_receipt"]["selected_positions"],
            [0, 2, 3, 4, 5, 4, 5, 6],
        )
        self.assertEqual(payload["external_risc0_scaled_sequence_receipt"]["final_kv_items"], 10)
        self.assertEqual(payload["external_risc0_wide_masked_sequence_receipt"]["decision"], GATE.RISC0_WIDE_MASKED_SEQUENCE.DECISION)
        self.assertEqual(payload["external_risc0_wide_masked_sequence_receipt"]["sequence_length"], 8)
        self.assertEqual(payload["external_risc0_wide_masked_sequence_receipt"]["transition_rows"], 8)
        self.assertEqual(payload["external_risc0_wide_masked_sequence_receipt"]["key_width"], 8)
        self.assertEqual(payload["external_risc0_wide_masked_sequence_receipt"]["value_width"], 8)
        self.assertEqual(
            payload["external_risc0_wide_masked_sequence_receipt"]["masking_policy"],
            "causal_prefix_position_lte_query_token",
        )
        self.assertEqual(payload["external_risc0_wide_masked_sequence_receipt"]["tie_break"], "lowest_position")
        self.assertEqual(
            payload["external_risc0_wide_masked_sequence_receipt"]["selected_positions"],
            [0, 2, 3, 3, 5, 5, 7, 9],
        )
        self.assertEqual(payload["external_risc0_wide_masked_sequence_receipt"]["final_kv_items"], 10)
        self.assertEqual(payload["external_risc0_receipt"]["proof_generation_time_source"], "current_prove_run")
        self.assertEqual(payload["external_risc0_receipt"]["verifier_time_source"], "current_verify_run")
        self.assertIn(
            payload["external_risc0_sequence_receipt"]["proof_generation_time_source"],
            {"current_prove_run", "carried_from_existing_evidence_not_remeasured"},
        )
        self.assertEqual(payload["external_risc0_sequence_receipt"]["verifier_time_source"], "current_verify_run")
        self.assertEqual(payload["non_claims"], list(GATE.EXPECTED_NON_CLAIMS))
        self.assertEqual(
            payload["metrics"]["native_stwo_proof_size_bytes"],
            payload["native_stwo_masked_sequence_receipt"]["proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["native_stwo_envelope_size_bytes"],
            payload["native_stwo_masked_sequence_receipt"]["envelope_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["quantized_softmax_proof_size_bytes"],
            payload["quantized_softmax_receipt"]["proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["quantized_softmax_lookup_claims"],
            payload["quantized_softmax_receipt"]["lookup_claims"],
        )
        self.assertEqual(
            payload["metrics"]["multihead_quantized_softmax_lookup_claims_total"],
            payload["multihead_quantized_softmax_receipt"]["lookup_claims_total"],
        )
        self.assertEqual(
            payload["metrics"]["multihead_quantized_softmax_head_counts_checked"],
            payload["multihead_quantized_softmax_receipt"]["head_counts_checked"],
        )
        self.assertEqual(
            payload["metrics"]["longseq_fused_softmax_lookup_claims"],
            payload["longseq_fused_softmax_receipt"]["lookup_claims"],
        )
        self.assertEqual(
            payload["metrics"]["longseq_fused_softmax_fused_proof_size_bytes"],
            payload["longseq_fused_softmax_receipt"]["fused_proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["d16_fused_softmax_lookup_claims"],
            payload["d16_fused_softmax_receipt"]["lookup_claims"],
        )
        self.assertEqual(
            payload["metrics"]["d16_fused_softmax_fused_proof_size_bytes"],
            payload["d16_fused_softmax_receipt"]["fused_proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["d16_two_head_fused_softmax_lookup_claims"],
            payload["d16_two_head_fused_softmax_receipt"]["lookup_claims"],
        )
        self.assertEqual(
            payload["metrics"]["d16_two_head_fused_softmax_head_count"],
            payload["d16_two_head_fused_softmax_receipt"]["head_count"],
        )
        self.assertEqual(
            payload["metrics"]["d16_two_head_fused_softmax_fused_proof_size_bytes"],
            payload["d16_two_head_fused_softmax_receipt"]["fused_proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["d16_two_head_longseq_fused_softmax_lookup_claims"],
            payload["d16_two_head_longseq_fused_softmax_receipt"]["lookup_claims"],
        )
        self.assertEqual(payload["metrics"]["d16_two_head_longseq_fused_softmax_trace_rows"], 512)
        self.assertEqual(payload["metrics"]["d16_two_head_longseq_fused_softmax_key_width"], 16)
        self.assertEqual(payload["metrics"]["d16_two_head_longseq_fused_softmax_head_count"], 2)
        self.assertEqual(payload["metrics"]["d16_two_head_longseq_fused_softmax_sequence_length_per_head"], 16)
        self.assertEqual(
            payload["metrics"]["d16_two_head_longseq_fused_softmax_fused_proof_size_bytes"],
            payload["d16_two_head_longseq_fused_softmax_receipt"]["fused_proof_size_bytes"],
        )
        self.assertEqual(payload["metrics"]["d16_two_head_longseq_fused_softmax_fused_proof_size_bytes"], 84868)
        self.assertEqual(
            payload["metrics"]["d16_quantized_softmax_proof_size_bytes"],
            payload["d16_quantized_softmax_receipt"]["proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["d16_quantized_softmax_key_width"],
            payload["d16_quantized_softmax_receipt"]["key_width"],
        )
        self.assertEqual(
            payload["metrics"]["d16_two_head_quantized_softmax_proof_size_bytes"],
            payload["d16_two_head_quantized_softmax_receipt"]["proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["d16_two_head_quantized_softmax_lookup_claims"],
            payload["d16_two_head_quantized_softmax_receipt"]["lookup_claims"],
        )
        self.assertEqual(
            payload["metrics"]["d16_two_head_quantized_softmax_head_count"],
            payload["d16_two_head_quantized_softmax_receipt"]["head_count"],
        )
        self.assertEqual(
            payload["metrics"]["d16_two_head_quantized_softmax_input_steps"],
            payload["d16_two_head_quantized_softmax_receipt"]["input_steps"],
        )
        self.assertEqual(
            payload["metrics"]["d16_softmax_edge_case_count"],
            payload["softmax_denominator_rounding_edge_corpus"]["edge_case_count"],
        )
        self.assertEqual(payload["metrics"]["d16_softmax_edge_min_denominator"], 256)
        self.assertEqual(payload["metrics"]["d16_softmax_edge_max_denominator"], 852)
        self.assertEqual(payload["metrics"]["d16_softmax_edge_route_mutations_rejected"], 9)
        self.assertEqual(payload["metrics"]["snark_proof_size_bytes"], payload["external_snark_receipt"]["proof_size_bytes"])
        self.assertEqual(payload["metrics"]["risc0_receipt_size_bytes"], payload["external_risc0_receipt"]["proof_size_bytes"])
        self.assertEqual(
            payload["metrics"]["risc0_sequence_receipt_size_bytes"],
            payload["external_risc0_sequence_receipt"]["proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["risc0_scaled_sequence_receipt_size_bytes"],
            payload["external_risc0_scaled_sequence_receipt"]["proof_size_bytes"],
        )
        self.assertEqual(
            payload["metrics"]["risc0_wide_masked_sequence_receipt_size_bytes"],
            payload["external_risc0_wide_masked_sequence_receipt"]["proof_size_bytes"],
        )
        self.assertEqual(payload["mutations_checked"], len(GATE.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(GATE.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_gate_rejects_proof_backed_route_relabeling(self) -> None:
        payload = GATE.build_payload()
        payload.pop("mutation_cases")
        payload.pop("mutations_checked")
        payload.pop("mutations_rejected")
        payload.pop("all_mutations_rejected")
        local_route = GATE.route_candidate_by_id(payload["route_candidates"], GATE.LOCAL_STWO_ROUTE_ID)
        local_route["usable_today"] = False
        local_route["proof_backed"] = False
        local_route["status"] = "NO_GO_MISSING_NATIVE_STWO_ATTENTION_KV_PROOF"
        payload["proof_backed_routes_available"] = [
            route for route in payload["proof_backed_routes_available"] if route != GATE.LOCAL_STWO_ROUTE_ID
        ]

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "route inventory"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_gate_rejects_fake_metrics(self) -> None:
        payload = GATE.build_payload()
        payload.pop("mutation_cases")
        payload.pop("mutations_checked")
        payload.pop("mutations_rejected")
        payload.pop("all_mutations_rejected")
        payload["metrics"]["verifier_time_ms"] = 1.0

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "metric smuggling"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_risc0_receipt_summary_accepts_verify_existing_proof_time_sources(self) -> None:
        payload = GATE.build_payload()
        for source in (
            "current_prove_run",
            "carried_from_existing_evidence_not_remeasured",
            "not_remeasured_in_verify_existing",
        ):
            summary = copy.deepcopy(payload["external_risc0_receipt"])
            summary["proof_generation_time_source"] = source
            GATE.validate_risc0_receipt(summary)

    def test_risc0_sequence_receipt_summary_accepts_verify_existing_proof_time_sources(self) -> None:
        payload = GATE.build_payload()
        for source in (
            "current_prove_run",
            "carried_from_existing_evidence_not_remeasured",
            "not_remeasured_in_verify_existing",
        ):
            summary = copy.deepcopy(payload["external_risc0_sequence_receipt"])
            summary["proof_generation_time_source"] = source
            GATE.validate_risc0_sequence_receipt(summary)

    def test_risc0_scaled_sequence_receipt_summary_accepts_verify_existing_proof_time_sources(self) -> None:
        payload = GATE.build_payload()
        for source in (
            "current_prove_run",
            "carried_from_existing_evidence_not_remeasured",
            "not_remeasured_in_verify_existing",
        ):
            summary = copy.deepcopy(payload["external_risc0_scaled_sequence_receipt"])
            summary["proof_generation_time_source"] = source
            GATE.validate_risc0_scaled_sequence_receipt(summary)

    def test_risc0_wide_masked_sequence_receipt_summary_accepts_verify_existing_proof_time_sources(self) -> None:
        payload = GATE.build_payload()
        for source in (
            "current_prove_run",
            "carried_from_existing_evidence_not_remeasured",
            "not_remeasured_in_verify_existing",
        ):
            summary = copy.deepcopy(payload["external_risc0_wide_masked_sequence_receipt"])
            summary["proof_generation_time_source"] = source
            GATE.validate_risc0_wide_masked_sequence_receipt(summary)

    def test_gate_rejects_missing_required_public_field(self) -> None:
        payload = GATE.build_payload()
        payload.pop("mutation_cases")
        payload.pop("mutations_checked")
        payload.pop("mutations_rejected")
        payload.pop("all_mutations_rejected")
        payload["source_contract"]["present_public_fields"] = payload["source_contract"]["present_public_fields"][:-1]

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "present public field"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_gate_rejects_mutation_summary_drift(self) -> None:
        payload = GATE.build_payload()
        payload["mutation_cases"][0]["rejected"] = False

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "mutation rejection"):
            GATE.validate_payload(payload)

    def test_d16_two_head_quantized_validator_pins_scope_policy_and_commitment_fields(self) -> None:
        payload = GATE.build_payload()
        base_summary = payload["d16_two_head_quantized_softmax_receipt"]
        original_summary_fn = GATE.d16_two_head_quantized_softmax_receipt_summary
        cases = {
            "denominator_policy": "external denominator",
            "division_rule": "round-to-nearest",
            "rounding_rule": "truncate_toward_zero",
            "head_binding_policy": "metadata only",
            "step_binding_policy": "metadata only",
            "output_order_policy": "derived from input_steps order, but heads may be shuffled",
            "causal_mask_policy": "not checked",
            "claim_boundary": "GO_REAL_VALUED_SOFTMAX_FULL_INFERENCE",
            "fused_gate_decision": "GO_DIFFERENT_FUSED_GATE",
            "weight_table_commitment": "blake2b-256:" + "55" * 32,
            "source_statement_commitment": "blake2b-256:" + "44" * 32,
            "source_public_instance_commitment": "blake2b-256:" + "43" * 32,
            "source_score_row_commitment": "blake2b-256:" + "42" * 32,
            "source_outputs_commitment": "blake2b-256:" + "41" * 32,
            "source_final_kv_cache_commitment": "blake2b-256:" + "40" * 32,
        }
        try:
            for field, value in cases.items():
                mutated = copy.deepcopy(base_summary)
                mutated[field] = value
                GATE.d16_two_head_quantized_softmax_receipt_summary = lambda _payload, mutated=mutated: mutated
                with self.subTest(field=field):
                    with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, field):
                        GATE.validate_d16_two_head_quantized_softmax_receipt(mutated)
        finally:
            GATE.d16_two_head_quantized_softmax_receipt_summary = original_summary_fn

    def test_multihead_quantized_softmax_rejects_trace_row_drift(self) -> None:
        payload = GATE.build_payload()
        summary = copy.deepcopy(payload["multihead_quantized_softmax_receipt"])
        summary["trace_rows_total"] = 896

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "trace-row-count drift"):
            GATE.validate_multihead_quantized_softmax_receipt(summary)

    def test_multihead_quantized_softmax_rejects_missing_trace_rows_as_gate_error(self) -> None:
        payload = GATE.build_payload()
        payload["multihead_quantized_softmax_receipt"].pop("trace_rows_total")

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "trace-row-count drift"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_multihead_quantized_softmax_rejects_float_trace_rows_as_gate_error(self) -> None:
        payload = GATE.build_payload()
        payload["multihead_quantized_softmax_receipt"]["trace_rows_total"] = 1920.0

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "trace-row-count drift"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_gate_rejects_malformed_next_go_criteria_as_gate_error(self) -> None:
        payload = GATE.build_payload()
        payload.pop("mutation_cases")
        payload.pop("mutations_checked")
        payload.pop("mutations_rejected")
        payload.pop("all_mutations_rejected")
        payload["next_go_criteria"] = None

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "next-go criteria drift"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_tsv_columns_are_stable(self) -> None:
        payload = GATE.build_payload()

        self.assertEqual(GATE.to_tsv(payload).splitlines()[0].split("\t"), list(GATE.TSV_COLUMNS))

    def test_write_outputs_round_trips(self) -> None:
        payload = GATE.build_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_out = tmp / "out.json"
            tsv_out = tmp / "out.tsv"
            GATE.write_outputs(payload, json_out, tsv_out)

            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            GATE.validate_payload(loaded)
            self.assertTrue(tsv_out.read_text(encoding="utf-8").startswith("decision\t"))

    def test_stwo_native_input_rejects_oversized_json_before_parse(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = pathlib.Path(raw_tmp) / "oversized-input.json"
            path.write_text(" " * (GATE.STWO_NATIVE_MASKED_SEQUENCE_MAX_INPUT_JSON_BYTES + 1), encoding="utf-8")

            with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "input evidence exceeds max size"):
                GATE.load_stwo_native_masked_sequence_payload(path)

    def test_stwo_native_envelope_rejects_oversized_json_before_parse(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = pathlib.Path(raw_tmp) / "oversized-envelope.json"
            path.write_text(
                " " * (GATE.STWO_NATIVE_MASKED_SEQUENCE_MAX_ENVELOPE_JSON_BYTES + 1),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "proof envelope exceeds max size"):
                GATE.load_stwo_native_masked_sequence_envelope(path)

    def test_stwo_native_envelope_validates_embedded_input_without_default_payload_read(self) -> None:
        def fail_default_payload_read(*_args, **_kwargs):
            raise AssertionError("envelope loader must not read the default input payload")

        original_loader = GATE.load_stwo_native_masked_sequence_payload
        try:
            GATE.load_stwo_native_masked_sequence_payload = fail_default_payload_read

            envelope = GATE.load_stwo_native_masked_sequence_envelope(
                GATE.STWO_NATIVE_MASKED_SEQUENCE_ENVELOPE_JSON
            )
        finally:
            GATE.load_stwo_native_masked_sequence_payload = original_loader

        self.assertEqual(envelope["decision"], GATE.LOCAL_STWO_PROOF_DECISION)

    def test_stwo_native_envelope_wraps_embedded_input_validation_errors(self) -> None:
        envelope = json.loads(GATE.STWO_NATIVE_MASKED_SEQUENCE_ENVELOPE_JSON.read_text(encoding="utf-8"))
        envelope["input"]["statement_version"] = "tampered"

        with tempfile.TemporaryDirectory() as raw_tmp:
            path = pathlib.Path(raw_tmp) / "tampered-envelope.json"
            path.write_text(json.dumps(envelope), encoding="utf-8")

            with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "embedded input drift"):
                GATE.load_stwo_native_masked_sequence_envelope(path)

    def test_stwo_native_summary_rejects_split_brain_input_and_envelope(self) -> None:
        payload = GATE.load_stwo_native_masked_sequence_payload()
        drifted_payload = dict(payload)
        drifted_payload["statement_commitment"] = f"blake2b-256:{'00' * 32}"

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "envelope/input drift"):
            GATE.stwo_native_masked_sequence_summary(drifted_payload)

    def test_stwo_native_payload_wrapper_normalizes_unexpected_validator_errors(self) -> None:
        def raise_type_error(_payload):
            raise TypeError("synthetic malformed payload")

        original_validator = GATE.STWO_NATIVE_MASKED_SEQUENCE.validate_payload
        try:
            GATE.STWO_NATIVE_MASKED_SEQUENCE.validate_payload = raise_type_error

            with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "synthetic malformed payload"):
                GATE.validate_stwo_native_masked_sequence_payload({}, "synthetic native payload")
        finally:
            GATE.STWO_NATIVE_MASKED_SEQUENCE.validate_payload = original_validator

    def test_quantized_softmax_receipt_loader_wraps_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = pathlib.Path(raw_tmp) / "malformed-quantized-receipt.json"
            path.write_text("{", encoding="utf-8")

            with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "quantized Softmax receipt malformed"):
                GATE.load_quantized_softmax_receipt_payload(path)

    def test_individual_mutations_reject(self) -> None:
        payload = GATE.build_payload()

        for name in GATE.EXPECTED_MUTATION_NAMES:
            mutated = GATE.mutate_payload(payload, name)
            with self.assertRaises(GATE.AttentionKvRouteSelectorError):
                GATE.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_route_mutations_are_route_id_based(self) -> None:
        payload = GATE.build_payload()
        payload["route_candidates"] = list(reversed(payload["route_candidates"]))

        local_stwo_removed = GATE.mutate_payload(payload, "local_stwo_route_removed")
        local_stwo_route = GATE.route_candidate_by_id(local_stwo_removed["route_candidates"], GATE.LOCAL_STWO_ROUTE_ID)
        self.assertFalse(local_stwo_route["usable_today"])
        self.assertFalse(local_stwo_route["proof_backed"])

        quantized_removed = GATE.mutate_payload(payload, "quantized_softmax_route_removed")
        quantized_route = GATE.route_candidate_by_id(
            quantized_removed["route_candidates"], GATE.QUANTIZED_SOFTMAX_ROUTE_ID
        )
        self.assertFalse(quantized_route["usable_today"])
        self.assertFalse(quantized_route["proof_backed"])

        d16_removed = GATE.mutate_payload(payload, "d16_fused_softmax_route_removed")
        d16_route = GATE.route_candidate_by_id(d16_removed["route_candidates"], GATE.D16_FUSED_SOFTMAX_ROUTE_ID)
        self.assertFalse(d16_route["usable_today"])
        self.assertFalse(d16_route["proof_backed"])

        d16_two_head_removed = GATE.mutate_payload(payload, "d16_two_head_fused_softmax_route_removed")
        d16_two_head_route = GATE.route_candidate_by_id(
            d16_two_head_removed["route_candidates"],
            GATE.D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID,
        )
        self.assertFalse(d16_two_head_route["usable_today"])
        self.assertFalse(d16_two_head_route["proof_backed"])

        d16_two_head_longseq_removed = GATE.mutate_payload(
            payload,
            "d16_two_head_longseq_fused_softmax_route_removed",
        )
        d16_two_head_longseq_route = GATE.route_candidate_by_id(
            d16_two_head_longseq_removed["route_candidates"],
            GATE.D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_ROUTE_ID,
        )
        self.assertFalse(d16_two_head_longseq_route["usable_today"])
        self.assertFalse(d16_two_head_longseq_route["proof_backed"])

        d16_quantized_removed = GATE.mutate_payload(payload, "d16_quantized_softmax_route_removed")
        d16_quantized_route = GATE.route_candidate_by_id(
            d16_quantized_removed["route_candidates"], GATE.D16_QUANTIZED_SOFTMAX_ROUTE_ID
        )
        self.assertFalse(d16_quantized_route["usable_today"])
        self.assertFalse(d16_quantized_route["proof_backed"])

        d16_two_head_quantized_removed = GATE.mutate_payload(
            payload,
            "d16_two_head_quantized_softmax_route_removed",
        )
        d16_two_head_quantized_route = GATE.route_candidate_by_id(
            d16_two_head_quantized_removed["route_candidates"],
            GATE.D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID,
        )
        self.assertFalse(d16_two_head_quantized_route["usable_today"])
        self.assertFalse(d16_two_head_quantized_route["proof_backed"])

        snark_removed = GATE.mutate_payload(payload, "external_snark_route_removed")
        snark_route = GATE.route_candidate_by_id(snark_removed["route_candidates"], GATE.EXTERNAL_SNARK_ROUTE_ID)
        self.assertFalse(snark_route["usable_today"])
        self.assertFalse(snark_route["proof_backed"])

        zkvm_removed = GATE.mutate_payload(payload, "external_zkvm_route_removed")
        zkvm_route = GATE.route_candidate_by_id(zkvm_removed["route_candidates"], GATE.EXTERNAL_ZKVM_ROUTE_ID)
        self.assertFalse(zkvm_route["usable_today"])
        self.assertFalse(zkvm_route["proof_backed"])

        sequence_removed = GATE.mutate_payload(payload, "external_zkvm_sequence_route_removed")
        sequence_route = GATE.route_candidate_by_id(
            sequence_removed["route_candidates"], GATE.EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID
        )
        self.assertFalse(sequence_route["usable_today"])
        self.assertFalse(sequence_route["proof_backed"])

        scaled_sequence_removed = GATE.mutate_payload(payload, "external_zkvm_scaled_sequence_route_removed")
        scaled_sequence_route = GATE.route_candidate_by_id(
            scaled_sequence_removed["route_candidates"], GATE.EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID
        )
        self.assertFalse(scaled_sequence_route["usable_today"])
        self.assertFalse(scaled_sequence_route["proof_backed"])

        wide_masked_sequence_removed = GATE.mutate_payload(payload, "external_zkvm_wide_masked_sequence_route_removed")
        wide_masked_sequence_route = GATE.route_candidate_by_id(
            wide_masked_sequence_removed["route_candidates"], GATE.EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID
        )
        self.assertFalse(wide_masked_sequence_route["usable_today"])
        self.assertFalse(wide_masked_sequence_route["proof_backed"])


if __name__ == "__main__":
    unittest.main()
