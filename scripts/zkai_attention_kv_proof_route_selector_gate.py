#!/usr/bin/env python3
"""Route selector for proof-backed attention/KV-cache receipts.

This gate consumes the existing source-backed and external proof-backed
attention/KV evidence and asks which route is usable today. The current answer
has thirteen narrow GO routes: one native Stwo AIR proof for the d=8 causal-prefix
integer-argmax attention/KV sequence, one native Stwo proof-backed single-head
implementation-exact quantized Softmax-table receipt, one native Stwo
proof-backed multi-head implementation-exact quantized Softmax-table receipt,
one native Stwo two-head long-sequence fused Softmax-table/LogUp proof, one
native Stwo d16 fused Softmax-table/LogUp proof, one native Stwo d16
two-head fused Softmax-table/LogUp proof, one native Stwo d16
implementation-exact quantized Softmax-table receipt, one native Stwo d16
two-head implementation-exact quantized Softmax-table receipt, one external
snarkjs/Groth16 statement receipt, and four RISC Zero controls that re-execute the
transition/sequence semantics in a zkVM. Real-valued Softmax, public
long-context benchmarks, full inference, and recursion/PCD remain explicitly
outside the current proof route.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import functools
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_transition_receipt_probe.py"
SNARK_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_snark_statement_receipt_gate.py"
RISC0_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_risc0_semantics_receipt_gate.py"
RISC0_SEQUENCE_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_risc0_sequence_receipt_gate.py"
RISC0_SCALED_SEQUENCE_RECEIPT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py"
RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py"
)
STWO_NATIVE_MASKED_SEQUENCE_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_stwo_native_masked_sequence_proof_input.py"
)
QUANTIZED_SOFTMAX_RECEIPT_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_quantized_softmax_receipt_gate.py"
)
MULTIHEAD_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py"
)
LONGSEQ_FUSED_SOFTMAX_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate.py"
)
D16_FUSED_SOFTMAX_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_d16_fused_softmax_table_native_gate.py"
D16_TWO_HEAD_FUSED_SOFTMAX_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_d16_two_head_fused_softmax_table_native_gate.py"
)
D16_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_d16_quantized_softmax_receipt_gate.py"
)
D16_TWO_HEAD_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate.py"
)
SOFTMAX_EDGE_CORPUS_SCRIPT = (
    ROOT / "scripts" / "zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate.py"
)
SOURCE_EVIDENCE_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-transition-receipt-2026-05.json"
)
SNARK_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-snark-statement-receipt-2026-05.json"
)
RISC0_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-risc0-semantics-receipt-2026-05.json"
)
RISC0_SEQUENCE_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-risc0-sequence-receipt-2026-05.json"
)
RISC0_SCALED_SEQUENCE_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.json"
)
RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.json"
)
STWO_NATIVE_MASKED_SEQUENCE_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json"
)
STWO_NATIVE_MASKED_SEQUENCE_ENVELOPE_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json"
)
QUANTIZED_SOFTMAX_RECEIPT_JSON = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json"
)
MULTIHEAD_QUANTIZED_SOFTMAX_RECEIPT_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json"
)
LONGSEQ_FUSED_SOFTMAX_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.json"
)
LONGSEQ_FUSED_SOFTMAX_SOURCE_INPUT_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.json"
)
LONGSEQ_FUSED_SOFTMAX_ENVELOPE_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json"
)
D16_FUSED_SOFTMAX_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.json"
)
D16_FUSED_SOFTMAX_SOURCE_INPUT_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json"
)
D16_FUSED_SOFTMAX_ENVELOPE_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json"
)
D16_TWO_HEAD_FUSED_SOFTMAX_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-gate-2026-05.json"
)
D16_TWO_HEAD_FUSED_SOFTMAX_SOURCE_INPUT_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.json"
)
D16_TWO_HEAD_FUSED_SOFTMAX_ENVELOPE_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-proof-2026-05.envelope.json"
)
D16_QUANTIZED_SOFTMAX_RECEIPT_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json"
)
D16_TWO_HEAD_QUANTIZED_SOFTMAX_RECEIPT_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.json"
)
SOFTMAX_EDGE_CORPUS_JSON = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json"
)
STWO_NATIVE_MASKED_SEQUENCE_MAX_INPUT_JSON_BYTES = 1_048_576
STWO_NATIVE_MASKED_SEQUENCE_MAX_ENVELOPE_JSON_BYTES = 1_048_576
QUANTIZED_SOFTMAX_RECEIPT_MAX_JSON_BYTES = 1_048_576
MULTIHEAD_QUANTIZED_SOFTMAX_RECEIPT_MAX_JSON_BYTES = 2_097_152
LONGSEQ_FUSED_SOFTMAX_MAX_JSON_BYTES = 1_048_576
LONGSEQ_FUSED_SOFTMAX_SOURCE_INPUT_MAX_JSON_BYTES = 2_097_152
LONGSEQ_FUSED_SOFTMAX_ENVELOPE_MAX_JSON_BYTES = 4_194_304
D16_FUSED_SOFTMAX_MAX_JSON_BYTES = 1_048_576
D16_FUSED_SOFTMAX_SOURCE_INPUT_MAX_JSON_BYTES = 1_048_576
D16_FUSED_SOFTMAX_ENVELOPE_MAX_JSON_BYTES = 2_097_152
D16_TWO_HEAD_FUSED_SOFTMAX_MAX_JSON_BYTES = 1_048_576
D16_TWO_HEAD_FUSED_SOFTMAX_SOURCE_INPUT_MAX_JSON_BYTES = 2_097_152
D16_TWO_HEAD_FUSED_SOFTMAX_ENVELOPE_MAX_JSON_BYTES = 2_097_152
D16_QUANTIZED_SOFTMAX_RECEIPT_MAX_JSON_BYTES = 1_048_576
D16_TWO_HEAD_QUANTIZED_SOFTMAX_RECEIPT_MAX_JSON_BYTES = 1_048_576
SOFTMAX_EDGE_CORPUS_MAX_JSON_BYTES = 1_048_576
JSON_OUT = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-proof-route-selector-2026-05.json"
)
TSV_OUT = (
    ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-proof-route-selector-2026-05.tsv"
)

SCHEMA = "zkai-attention-kv-proof-route-selector-gate-v1"
DECISION = (
    "GO_NATIVE_STWO_SINGLE_MULTIHEAD_LONGSEQ_D16_FUSED_D16_TWO_HEAD_FUSED_D16_QUANTIZED_D16_TWO_HEAD_QUANTIZED_SOFTMAX_AND_EXTERNAL_SNARK_RISC0_ATTENTION_KV_RECEIPTS"
)
FIRST_BLOCKER = "NO_REAL_VALUED_SOFTMAX_LONG_CONTEXT_FULL_INFERENCE_OR_RECURSION_PCD_PROOF"
CLAIM_BOUNDARY = (
    "NATIVE_STWO_D8_CAUSAL_MASKED_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_PROOF_AND_NATIVE_STWO_D8_IMPLEMENTATION_EXACT_"
    "QUANTIZED_SOFTMAX_TABLE_RECEIPT_AND_NATIVE_STWO_MULTIHEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT_"
    "AND_NATIVE_STWO_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_TABLE_PROOF_"
    "AND_NATIVE_STWO_D16_FUSED_SOFTMAX_TABLE_PROOF_"
    "AND_NATIVE_STWO_D16_TWO_HEAD_FUSED_SOFTMAX_TABLE_PROOF_"
    "AND_NATIVE_STWO_D16_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT_"
    "AND_NATIVE_STWO_D16_TWO_HEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT_"
    "AND_EXTERNAL_SNARK_RISC0_CONTROLS_NOT_REAL_VALUED_SOFTMAX_NOT_LONG_CONTEXT_OR_FULL_INFERENCE_NOT_RECURSION_OR_PCD_NOT_AGENT_CORRECTNESS"
)
SOURCE_DATE_EPOCH_DEFAULT = 0

REQUIRED_PUBLIC_FIELDS = (
    "model_config_commitment",
    "prior_kv_cache_commitment",
    "input_commitment",
    "attention_output_commitment",
    "next_kv_cache_commitment",
    "public_instance_commitment",
    "proof_commitment",
    "proof_status",
    "verifier_domain",
    "statement_commitment",
)

SOURCE_ROUTE_ID = "source_backed_attention_kv_receipt_contract"
LOCAL_STWO_ROUTE_ID = "local_stwo_attention_kv_d8_masked_sequence_proof"
LOCAL_STWO_PROOF_DECISION = "GO_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF"
QUANTIZED_SOFTMAX_ROUTE_ID = "local_stwo_attention_kv_d8_quantized_softmax_table_kernel_receipt"
QUANTIZED_SOFTMAX_DECISION = "GO_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
MULTIHEAD_QUANTIZED_SOFTMAX_ROUTE_ID = (
    "local_stwo_attention_kv_multihead_quantized_softmax_table_kernel_receipt"
)
MULTIHEAD_QUANTIZED_SOFTMAX_DECISION = (
    "GO_SCALED_MULTIHEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
)
LONGSEQ_FUSED_SOFTMAX_ROUTE_ID = "local_stwo_attention_kv_two_head_longseq_fused_bounded_softmax_table_logup_proof"
LONGSEQ_FUSED_SOFTMAX_DECISION = (
    "GO_NATIVE_STWO_TWO_HEAD_LONGSEQ_FUSED_ATTENTION_ARITHMETIC_AND_SOFTMAX_TABLE_LOGUP_MEMBERSHIP"
)
D16_FUSED_SOFTMAX_ROUTE_ID = "local_stwo_attention_kv_d16_fused_bounded_softmax_table_logup_proof"
D16_FUSED_SOFTMAX_DECISION = (
    "GO_NATIVE_STWO_FUSED_ATTENTION_ARITHMETIC_AND_SOFTMAX_TABLE_LOGUP_MEMBERSHIP"
)
D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID = "local_stwo_attention_kv_d16_two_head_fused_bounded_softmax_table_logup_proof"
D16_TWO_HEAD_FUSED_SOFTMAX_DECISION = (
    "GO_NATIVE_STWO_FUSED_ATTENTION_ARITHMETIC_AND_SOFTMAX_TABLE_LOGUP_MEMBERSHIP"
)
D16_QUANTIZED_SOFTMAX_ROUTE_ID = "local_stwo_attention_kv_d16_quantized_softmax_table_kernel_receipt"
D16_QUANTIZED_SOFTMAX_DECISION = "GO_D16_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID = "local_stwo_attention_kv_d16_two_head_quantized_softmax_table_kernel_receipt"
D16_TWO_HEAD_QUANTIZED_SOFTMAX_DECISION = "GO_D16_TWO_HEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
EXTERNAL_SNARK_ROUTE_ID = "external_snark_attention_kv_statement_receipt"
EXTERNAL_ZKVM_ROUTE_ID = "external_zkvm_attention_kv_semantics_receipt"
EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID = "external_zkvm_attention_kv_sequence_semantics_receipt"
EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID = "external_zkvm_attention_kv_scaled_sequence_semantics_receipt"
EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID = "external_zkvm_attention_kv_wide_masked_sequence_semantics_receipt"
REAL_VALUED_SOFTMAX_ROUTE_ID = "real_valued_softmax_attention_kv_claim"

BASE_ROUTES = (
    {
        "route_id": SOURCE_ROUTE_ID,
        "status": "GO_SOURCE_CONTRACT_ONLY",
        "blocker": "NOT_PROOF_BACKED",
        "usable_today": True,
        "proof_backed": False,
    },
    {
        "route_id": LOCAL_STWO_ROUTE_ID,
        "status": "GO_STWO_NATIVE_ATTENTION_KV_D8_MASKED_SEQUENCE_AIR_PROOF",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": QUANTIZED_SOFTMAX_ROUTE_ID,
        "status": QUANTIZED_SOFTMAX_DECISION,
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": MULTIHEAD_QUANTIZED_SOFTMAX_ROUTE_ID,
        "status": MULTIHEAD_QUANTIZED_SOFTMAX_DECISION,
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": LONGSEQ_FUSED_SOFTMAX_ROUTE_ID,
        "status": LONGSEQ_FUSED_SOFTMAX_DECISION,
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": D16_FUSED_SOFTMAX_ROUTE_ID,
        "status": D16_FUSED_SOFTMAX_DECISION,
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID,
        "status": D16_TWO_HEAD_FUSED_SOFTMAX_DECISION,
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": D16_QUANTIZED_SOFTMAX_ROUTE_ID,
        "status": D16_QUANTIZED_SOFTMAX_DECISION,
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID,
        "status": D16_TWO_HEAD_QUANTIZED_SOFTMAX_DECISION,
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_SNARK_ROUTE_ID,
        "status": "GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_SOURCE_CONTRACT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_ZKVM_ROUTE_ID,
        "status": "GO_RISC0_ATTENTION_KV_TRANSITION_SEMANTICS_RECEIPT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID,
        "status": "GO_RISC0_ATTENTION_KV_SEQUENCE_SEMANTICS_RECEIPT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID,
        "status": "GO_RISC0_ATTENTION_KV_SCALED_SEQUENCE_SEMANTICS_RECEIPT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID,
        "status": "GO_RISC0_ATTENTION_KV_WIDE_MASKED_SEQUENCE_SEMANTICS_RECEIPT",
        "blocker": None,
        "usable_today": True,
        "proof_backed": True,
    },
    {
        "route_id": REAL_VALUED_SOFTMAX_ROUTE_ID,
        "status": "NO_GO_REAL_VALUED_SOFTMAX_OUT_OF_SCOPE_FOR_QUANTIZED_TABLE_KERNEL",
        "blocker": "REAL_VALUED_EXP_DIV_SOFTMAX_NOT_PROVED_BY_CURRENT_KERNEL",
        "usable_today": False,
        "proof_backed": False,
    },
)

EXPECTED_PROOF_BACKED_ROUTES_AVAILABLE = (
    LOCAL_STWO_ROUTE_ID,
    QUANTIZED_SOFTMAX_ROUTE_ID,
    MULTIHEAD_QUANTIZED_SOFTMAX_ROUTE_ID,
    LONGSEQ_FUSED_SOFTMAX_ROUTE_ID,
    D16_FUSED_SOFTMAX_ROUTE_ID,
    D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID,
    D16_QUANTIZED_SOFTMAX_ROUTE_ID,
    D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID,
    EXTERNAL_SNARK_ROUTE_ID,
    EXTERNAL_ZKVM_ROUTE_ID,
    EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID,
    EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID,
    EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID,
)

TSV_COLUMNS = (
    "decision",
    "first_blocker",
    "source_contract_decision",
    "source_contract_proof_status",
    "proof_backed_routes_available",
    "routes_checked",
    "mutations_checked",
    "mutations_rejected",
    "source_statement_commitment",
)


def proof_routes_except(*excluded: str) -> list[str]:
    """Return the canonical proof-backed route list minus named removed routes."""

    excluded_set = set(excluded)
    return [route for route in EXPECTED_PROOF_BACKED_ROUTES_AVAILABLE if route not in excluded_set]

EXPECTED_MUTATION_NAMES = (
    "source_contract_decision_drift",
    "source_contract_proof_status_overclaim",
    "source_contract_mutation_rejections_drift",
    "missing_required_public_field",
    "local_stwo_route_removed",
    "local_stwo_native_receipt_decision_drift",
    "local_stwo_native_receipt_statement_drift",
    "quantized_softmax_route_removed",
    "quantized_softmax_receipt_decision_drift",
    "quantized_softmax_receipt_route_drift",
    "quantized_softmax_receipt_mutation_rejections_drift",
    "quantized_softmax_real_softmax_overclaim",
    "quantized_softmax_denominator_drift",
    "multihead_quantized_softmax_route_removed",
    "multihead_quantized_softmax_receipt_decision_drift",
    "multihead_quantized_softmax_receipt_route_drift",
    "multihead_quantized_softmax_receipt_mutation_rejections_drift",
    "multihead_quantized_softmax_real_softmax_overclaim",
    "multihead_quantized_softmax_profile_count_drift",
    "multihead_quantized_softmax_trace_rows_drift",
    "multihead_quantized_softmax_output_mapping_drift",
    "longseq_fused_softmax_route_removed",
    "longseq_fused_softmax_decision_drift",
    "longseq_fused_softmax_lookup_claims_drift",
    "longseq_fused_softmax_exact_softmax_overclaim",
    "longseq_fused_softmax_mutation_rejections_drift",
    "d16_fused_softmax_route_removed",
    "d16_fused_softmax_decision_drift",
    "d16_fused_softmax_width_drift",
    "d16_fused_softmax_exact_softmax_overclaim",
    "d16_fused_softmax_mutation_rejections_drift",
    "d16_two_head_fused_softmax_route_removed",
    "d16_two_head_fused_softmax_decision_drift",
    "d16_two_head_fused_softmax_width_or_head_drift",
    "d16_two_head_fused_softmax_exact_softmax_overclaim",
    "d16_two_head_fused_softmax_mutation_rejections_drift",
    "d16_quantized_softmax_route_removed",
    "d16_quantized_softmax_receipt_decision_drift",
    "d16_quantized_softmax_receipt_route_drift",
    "d16_quantized_softmax_real_softmax_overclaim",
    "d16_quantized_softmax_width_drift",
    "d16_quantized_softmax_denominator_drift",
    "d16_quantized_softmax_mutation_rejections_drift",
    "d16_two_head_quantized_softmax_route_removed",
    "d16_two_head_quantized_softmax_receipt_decision_drift",
    "d16_two_head_quantized_softmax_receipt_route_drift",
    "d16_two_head_quantized_softmax_real_softmax_overclaim",
    "d16_two_head_quantized_softmax_width_or_head_drift",
    "d16_two_head_quantized_softmax_denominator_drift",
    "d16_two_head_quantized_softmax_output_order_drift",
    "d16_two_head_quantized_softmax_mutation_rejections_drift",
    "d16_softmax_edge_corpus_claim_boundary_drift",
    "d16_softmax_edge_corpus_route_mutation_rejections_drift",
    "external_snark_route_removed",
    "external_snark_receipt_decision_drift",
    "external_snark_receipt_mutation_rejections_drift",
    "external_zkvm_route_removed",
    "external_zkvm_receipt_decision_drift",
    "external_zkvm_receipt_mutation_rejections_drift",
    "external_zkvm_receipt_next_kv_items_drift",
    "external_zkvm_metric_source_drift",
    "external_zkvm_sequence_route_removed",
    "external_zkvm_sequence_receipt_decision_drift",
    "external_zkvm_sequence_receipt_mutation_rejections_drift",
    "external_zkvm_sequence_length_drift",
    "external_zkvm_sequence_intermediate_state_drift",
    "external_zkvm_sequence_metric_source_drift",
    "external_zkvm_scaled_sequence_route_removed",
    "external_zkvm_scaled_sequence_receipt_decision_drift",
    "external_zkvm_scaled_sequence_receipt_mutation_rejections_drift",
    "external_zkvm_scaled_sequence_length_drift",
    "external_zkvm_scaled_sequence_intermediate_state_drift",
    "external_zkvm_scaled_sequence_metric_source_drift",
    "external_zkvm_wide_masked_sequence_route_removed",
    "external_zkvm_wide_masked_sequence_receipt_decision_drift",
    "external_zkvm_wide_masked_sequence_receipt_mutation_rejections_drift",
    "external_zkvm_wide_masked_sequence_length_drift",
    "external_zkvm_wide_masked_sequence_width_or_masking_drift",
    "external_zkvm_wide_masked_sequence_tie_break_drift",
    "external_zkvm_wide_masked_sequence_intermediate_state_drift",
    "external_zkvm_wide_masked_sequence_metric_source_drift",
    "fake_verifier_time_metric",
    "fake_proof_size_metric",
    "next_go_criteria_weakened",
    "non_claims_weakened",
    "claim_boundary_weakened",
    "first_blocker_removed",
    "unknown_field_injection",
)

EXPECTED_NEXT_GO_CRITERIA = (
    "native Stwo proof scales the d8 causal-mask integer-argmax attention arithmetic beyond the fixed eight-step fixture without weakening intermediate-state binding",
    "the carried KV-cache sequence scales beyond a fixed eight-step fixture without weakening intermediate-state binding",
    "larger-width, higher-head-count, or longer-context fixtures preserve the same masking, intermediate-state, denominator/remainder, and output-order binding guarantees",
    "the implementation-exact quantized Softmax-table receipt scales beyond the checked two-head, four-head, eight-head, and sixteen-head d8 fixtures without weakening head/output binding",
    "the explicit causal-prefix masking axis remains statement data in any native route",
    "prior KV, intermediate KV, input/query, attention output, final KV, verifier domain, proof status, and statement commitment relabels reject after proof serialization",
    "real-valued exp/div Softmax stays out of scope unless the proof covers that exact kernel and error bound",
)

EXPECTED_NON_CLAIMS = (
    "not real-valued Softmax",
    "not full autoregressive inference",
    "not agent correctness",
    "not recursive or proof-carrying data",
    "not a long-context KV-cache benchmark",
    "not a benchmark row",
)


class AttentionKvRouteSelectorError(ValueError):
    pass


def _load_source_module():
    """Load the source-backed attention/KV probe without package assumptions."""

    spec = importlib.util.spec_from_file_location("zkai_attention_kv_transition_receipt_probe", SOURCE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load source script: {SOURCE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_snark_module():
    """Load the external SNARK statement-receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location("zkai_attention_kv_snark_statement_receipt_gate", SNARK_RECEIPT_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load SNARK receipt script: {SNARK_RECEIPT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_risc0_module():
    """Load the RISC Zero semantics-receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location("zkai_attention_kv_risc0_semantics_receipt_gate", RISC0_RECEIPT_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load RISC Zero receipt script: {RISC0_RECEIPT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_risc0_sequence_module():
    """Load the RISC Zero sequence-receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location("zkai_attention_kv_risc0_sequence_receipt_gate", RISC0_SEQUENCE_RECEIPT_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load RISC Zero sequence receipt script: {RISC0_SEQUENCE_RECEIPT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_risc0_scaled_sequence_module():
    """Load the RISC Zero scaled-sequence receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_risc0_scaled_sequence_receipt_gate",
        RISC0_SCALED_SEQUENCE_RECEIPT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load RISC Zero scaled sequence receipt script: {RISC0_SCALED_SEQUENCE_RECEIPT_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_risc0_wide_masked_sequence_module():
    """Load the RISC Zero wide/masked sequence receipt gate without package assumptions."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate",
        RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load RISC Zero wide masked sequence receipt script: {RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_stwo_native_masked_sequence_module():
    """Load the native Stwo masked-sequence input gate without package assumptions."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_stwo_native_masked_sequence_proof_input",
        STWO_NATIVE_MASKED_SEQUENCE_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load Stwo native masked sequence script: {STWO_NATIVE_MASKED_SEQUENCE_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_quantized_softmax_receipt_module():
    """Load the implementation-exact quantized Softmax receipt gate."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_quantized_softmax_receipt_gate",
        QUANTIZED_SOFTMAX_RECEIPT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load quantized Softmax receipt script: {QUANTIZED_SOFTMAX_RECEIPT_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_multihead_quantized_softmax_receipt_module():
    """Load the multi-head implementation-exact quantized Softmax receipt gate."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_multihead_quantized_softmax_receipt_gate",
        MULTIHEAD_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load multi-head quantized Softmax receipt script: {MULTIHEAD_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_longseq_fused_softmax_module():
    """Load the two-head long-sequence fused Softmax-table gate."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate",
        LONGSEQ_FUSED_SOFTMAX_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load long-sequence fused Softmax-table gate: {LONGSEQ_FUSED_SOFTMAX_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_d16_fused_softmax_module():
    """Load the d16 fused Softmax-table gate."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_d16_fused_softmax_table_native_gate",
        D16_FUSED_SOFTMAX_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load d16 fused Softmax-table gate: {D16_FUSED_SOFTMAX_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_d16_two_head_fused_softmax_module():
    """Load the d16 two-head fused Softmax-table gate."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_d16_two_head_fused_softmax_table_native_gate",
        D16_TWO_HEAD_FUSED_SOFTMAX_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load d16 two-head fused Softmax-table gate: {D16_TWO_HEAD_FUSED_SOFTMAX_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_d16_quantized_softmax_receipt_module():
    """Load the d16 implementation-exact quantized Softmax receipt gate."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_d16_quantized_softmax_receipt_gate",
        D16_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load d16 quantized Softmax receipt script: {D16_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_d16_two_head_quantized_softmax_receipt_module():
    """Load the d16 two-head implementation-exact quantized Softmax receipt gate."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate",
        D16_TWO_HEAD_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(
            f"failed to load d16 two-head quantized Softmax receipt script: {D16_TWO_HEAD_QUANTIZED_SOFTMAX_RECEIPT_SCRIPT}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_softmax_edge_corpus_module():
    """Load the d16 denominator/rounding edge-corpus gate."""

    spec = importlib.util.spec_from_file_location(
        "zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate",
        SOFTMAX_EDGE_CORPUS_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise AttentionKvRouteSelectorError(f"failed to load Softmax edge-corpus gate: {SOFTMAX_EDGE_CORPUS_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE = _load_source_module()
SNARK = _load_snark_module()
RISC0 = _load_risc0_module()
RISC0_SEQUENCE = _load_risc0_sequence_module()
RISC0_SCALED_SEQUENCE = _load_risc0_scaled_sequence_module()
RISC0_WIDE_MASKED_SEQUENCE = _load_risc0_wide_masked_sequence_module()
STWO_NATIVE_MASKED_SEQUENCE = _load_stwo_native_masked_sequence_module()
QUANTIZED_SOFTMAX = _load_quantized_softmax_receipt_module()
MULTIHEAD_QUANTIZED_SOFTMAX = _load_multihead_quantized_softmax_receipt_module()
LONGSEQ_FUSED_SOFTMAX = _load_longseq_fused_softmax_module()
D16_FUSED_SOFTMAX = _load_d16_fused_softmax_module()
D16_TWO_HEAD_FUSED_SOFTMAX = _load_d16_two_head_fused_softmax_module()
D16_QUANTIZED_SOFTMAX = _load_d16_quantized_softmax_receipt_module()
D16_TWO_HEAD_QUANTIZED_SOFTMAX = _load_d16_two_head_quantized_softmax_receipt_module()
SOFTMAX_EDGE_CORPUS = _load_softmax_edge_corpus_module()


def validate_stwo_native_masked_sequence_payload(payload: Any, label: str) -> None:
    """Normalize native Stwo input validation failures into this gate's error type."""

    try:
        STWO_NATIVE_MASKED_SEQUENCE.validate_payload(payload)
    except STWO_NATIVE_MASKED_SEQUENCE.AttentionKvStwoNativeInputError as error:
        raise AttentionKvRouteSelectorError(f"{label} drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"{label} malformed: {error}") from error


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize payload fragments deterministically before hashing."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    """Commit to a typed payload fragment under an explicit domain string."""

    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _git_commit() -> str:
    """Return the current repository commit, or an explicit unavailable marker."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def _generated_at() -> str:
    """Return a reproducible generation timestamp from SOURCE_DATE_EPOCH."""

    raw = os.environ.get("SOURCE_DATE_EPOCH", str(SOURCE_DATE_EPOCH_DEFAULT))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise AttentionKvRouteSelectorError("SOURCE_DATE_EPOCH must be an integer") from err
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def load_source_payload(path: pathlib.Path = SOURCE_EVIDENCE_JSON) -> dict[str, Any]:
    """Load and validate the source-backed receipt payload used as input."""

    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = SOURCE.run_probe()
    SOURCE.validate_payload(payload)
    return payload


def load_snark_payload(path: pathlib.Path = SNARK_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the external SNARK statement-receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing SNARK receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    SNARK.validate_payload(payload)
    return payload


def load_risc0_payload(path: pathlib.Path = RISC0_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the RISC Zero semantics-receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing RISC Zero receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    RISC0.validate_payload(payload)
    return payload


def load_risc0_sequence_payload(path: pathlib.Path = RISC0_SEQUENCE_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the RISC Zero sequence-receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing RISC Zero sequence receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    RISC0_SEQUENCE.validate_payload(payload)
    return payload


def load_risc0_scaled_sequence_payload(path: pathlib.Path = RISC0_SCALED_SEQUENCE_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the RISC Zero scaled-sequence receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing RISC Zero scaled sequence receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    RISC0_SCALED_SEQUENCE.validate_payload(payload)
    return payload


def load_risc0_wide_masked_sequence_payload(path: pathlib.Path = RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_JSON) -> dict[str, Any]:
    """Load and validate the RISC Zero wide/masked sequence receipt payload."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing RISC Zero wide masked sequence receipt evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    RISC0_WIDE_MASKED_SEQUENCE.validate_payload(payload)
    return payload


def read_bounded_text(path: pathlib.Path, max_bytes: int, label: str) -> str:
    """Read a JSON evidence file with an enforced byte cap."""

    if not path.exists():
        raise AttentionKvRouteSelectorError(f"missing {label}: {path}")
    if not path.is_file():
        raise AttentionKvRouteSelectorError(f"{label} is not a regular file: {path}")
    size = path.stat().st_size
    if size > max_bytes:
        raise AttentionKvRouteSelectorError(
            f"{label} exceeds max size: got {size} bytes, limit {max_bytes} bytes"
        )
    with path.open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise AttentionKvRouteSelectorError(
            f"{label} exceeds max size: got more than {max_bytes} bytes, limit {max_bytes} bytes"
        )
    return raw.decode("utf-8")


def load_stwo_native_masked_sequence_payload(path: pathlib.Path = STWO_NATIVE_MASKED_SEQUENCE_JSON) -> dict[str, Any]:
    """Load and validate the native Stwo masked-sequence proof input payload."""

    raw = read_bounded_text(
        path,
        STWO_NATIVE_MASKED_SEQUENCE_MAX_INPUT_JSON_BYTES,
        "Stwo native masked sequence input evidence",
    )
    payload = json.loads(raw)
    validate_stwo_native_masked_sequence_payload(payload, "Stwo native masked sequence input evidence")
    return payload


def load_stwo_native_masked_sequence_envelope(
    path: pathlib.Path = STWO_NATIVE_MASKED_SEQUENCE_ENVELOPE_JSON,
) -> dict[str, Any]:
    """Load the checked native Stwo proof envelope and bind it back to the input."""

    raw = read_bounded_text(
        path,
        STWO_NATIVE_MASKED_SEQUENCE_MAX_ENVELOPE_JSON_BYTES,
        "Stwo native masked sequence proof envelope",
    )
    envelope = json.loads(raw)
    if not isinstance(envelope, dict):
        raise AttentionKvRouteSelectorError("Stwo native proof envelope must be an object")
    expected_keys = {
        "decision",
        "input",
        "proof",
        "proof_backend",
        "proof_backend_version",
        "semantic_scope",
        "statement_version",
    }
    if set(envelope) != expected_keys:
        raise AttentionKvRouteSelectorError("Stwo native proof envelope schema drift")
    input_payload = envelope.get("input")
    validate_stwo_native_masked_sequence_payload(input_payload, "Stwo native proof envelope embedded input")
    if envelope.get("decision") != LOCAL_STWO_PROOF_DECISION:
        raise AttentionKvRouteSelectorError("Stwo native proof envelope decision drift")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvRouteSelectorError("Stwo native proof envelope backend drift")
    if envelope.get("proof_backend_version") != input_payload["required_backend_version"]:
        raise AttentionKvRouteSelectorError("Stwo native proof envelope backend-version drift")
    if envelope.get("semantic_scope") != input_payload["semantic_scope"]:
        raise AttentionKvRouteSelectorError("Stwo native proof envelope semantic-scope drift")
    if envelope.get("statement_version") != input_payload["statement_version"]:
        raise AttentionKvRouteSelectorError("Stwo native proof envelope statement-version drift")
    proof = envelope.get("proof")
    if not isinstance(proof, list) or not proof:
        raise AttentionKvRouteSelectorError("Stwo native proof bytes missing")
    if any(not isinstance(item, int) or item < 0 or item > 255 for item in proof):
        raise AttentionKvRouteSelectorError("Stwo native proof bytes malformed")
    return envelope


@functools.lru_cache(maxsize=2)
def _load_quantized_softmax_receipt_payload(path: pathlib.Path, run_native: bool) -> dict[str, Any]:
    """Load and validate the current implementation-exact quantized Softmax receipt payload."""

    raw = read_bounded_text(
        path,
        QUANTIZED_SOFTMAX_RECEIPT_MAX_JSON_BYTES,
        "quantized Softmax receipt evidence",
    )
    try:
        payload = json.loads(raw)
        QUANTIZED_SOFTMAX.validate_result(payload, run_native=run_native)
    except QUANTIZED_SOFTMAX.QuantizedSoftmaxReceiptGateError as error:
        raise AttentionKvRouteSelectorError(f"quantized Softmax receipt drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"quantized Softmax receipt malformed: {error}") from error
    return payload


def load_quantized_softmax_receipt_payload(
    path: pathlib.Path = QUANTIZED_SOFTMAX_RECEIPT_JSON,
    *,
    run_native: bool = False,
) -> dict[str, Any]:
    """Load the implementation-exact quantized Softmax receipt payload as a fresh object."""

    return copy.deepcopy(_load_quantized_softmax_receipt_payload(path, run_native))


@functools.lru_cache(maxsize=2)
def _load_multihead_quantized_softmax_receipt_payload(path: pathlib.Path, run_native: bool) -> dict[str, Any]:
    """Load and validate the current multi-head quantized Softmax receipt payload."""

    raw = read_bounded_text(
        path,
        MULTIHEAD_QUANTIZED_SOFTMAX_RECEIPT_MAX_JSON_BYTES,
        "multi-head quantized Softmax receipt evidence",
    )
    try:
        payload = json.loads(raw)
        MULTIHEAD_QUANTIZED_SOFTMAX.validate_result(payload, run_native=run_native)
    except MULTIHEAD_QUANTIZED_SOFTMAX.MultiheadQuantizedSoftmaxReceiptGateError as error:
        raise AttentionKvRouteSelectorError(f"multi-head quantized Softmax receipt drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"multi-head quantized Softmax receipt malformed: {error}") from error
    return payload


def load_multihead_quantized_softmax_receipt_payload(
    path: pathlib.Path = MULTIHEAD_QUANTIZED_SOFTMAX_RECEIPT_JSON,
    *,
    run_native: bool = False,
) -> dict[str, Any]:
    """Load the multi-head implementation-exact quantized Softmax receipt payload."""

    return copy.deepcopy(_load_multihead_quantized_softmax_receipt_payload(path, run_native))


@functools.lru_cache(maxsize=2)
def _load_longseq_fused_softmax_payload(path: pathlib.Path, run_native: bool) -> dict[str, Any]:
    """Load the gate payload and its fixed source/envelope evidence pair."""

    raw = read_bounded_text(
        path,
        LONGSEQ_FUSED_SOFTMAX_MAX_JSON_BYTES,
        "two-head long-sequence fused Softmax-table gate evidence",
    )
    source_raw = read_bounded_text(
        LONGSEQ_FUSED_SOFTMAX_SOURCE_INPUT_JSON,
        LONGSEQ_FUSED_SOFTMAX_SOURCE_INPUT_MAX_JSON_BYTES,
        "two-head long-sequence source input evidence",
    )
    envelope_raw = read_bounded_text(
        LONGSEQ_FUSED_SOFTMAX_ENVELOPE_JSON,
        LONGSEQ_FUSED_SOFTMAX_ENVELOPE_MAX_JSON_BYTES,
        "two-head long-sequence fused Softmax-table proof envelope",
    )
    try:
        payload = json.loads(raw)
        source_input = json.loads(source_raw)
        envelope = json.loads(envelope_raw)
        LONGSEQ_FUSED_SOFTMAX.validate_result(payload, envelope, source_input)
        if run_native:
            LONGSEQ_FUSED_SOFTMAX.validate_fused_envelope(
                envelope,
                source_input,
                run_native=True,
                native_envelope_bytes=envelope_raw.encode("utf-8"),
            )
    except LONGSEQ_FUSED_SOFTMAX.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError as error:
        raise AttentionKvRouteSelectorError(f"two-head long-sequence fused Softmax-table drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"two-head long-sequence fused Softmax-table malformed: {error}") from error
    return payload


def load_longseq_fused_softmax_payload(
    path: pathlib.Path = LONGSEQ_FUSED_SOFTMAX_JSON,
    *,
    run_native: bool = False,
) -> dict[str, Any]:
    """Load the two-head long-sequence fused Softmax-table gate payload."""

    return copy.deepcopy(_load_longseq_fused_softmax_payload(path, run_native))


@functools.lru_cache(maxsize=2)
def _load_d16_fused_softmax_payload(path: pathlib.Path, run_native: bool) -> dict[str, Any]:
    """Load the d16 fused gate payload and its fixed source/envelope evidence pair."""

    raw = read_bounded_text(
        path,
        D16_FUSED_SOFTMAX_MAX_JSON_BYTES,
        "d16 fused Softmax-table gate evidence",
    )
    source_raw = read_bounded_text(
        D16_FUSED_SOFTMAX_SOURCE_INPUT_JSON,
        D16_FUSED_SOFTMAX_SOURCE_INPUT_MAX_JSON_BYTES,
        "d16 source input evidence",
    )
    envelope_raw = read_bounded_text(
        D16_FUSED_SOFTMAX_ENVELOPE_JSON,
        D16_FUSED_SOFTMAX_ENVELOPE_MAX_JSON_BYTES,
        "d16 fused Softmax-table proof envelope",
    )
    try:
        payload = json.loads(raw)
        source_input = json.loads(source_raw)
        envelope = json.loads(envelope_raw)
        D16_FUSED_SOFTMAX.SOURCE_INPUT_MODULE.validate_payload(source_input)
        D16_FUSED_SOFTMAX.SOURCE_INPUT_MODULE.validate_payload(envelope.get("source_input"))
        D16_FUSED_SOFTMAX.validate_result(payload)
        D16_FUSED_SOFTMAX.validate_fused_envelope(envelope, source_input, run_native=run_native)
    except D16_FUSED_SOFTMAX.AttentionKvD16FusedSoftmaxTableGateError as error:
        raise AttentionKvRouteSelectorError(f"d16 fused Softmax-table drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"d16 fused Softmax-table malformed: {error}") from error
    return payload


def load_d16_fused_softmax_payload(
    path: pathlib.Path = D16_FUSED_SOFTMAX_JSON,
    *,
    run_native: bool = False,
) -> dict[str, Any]:
    """Load the d16 fused Softmax-table gate payload."""

    return copy.deepcopy(_load_d16_fused_softmax_payload(path, run_native))


@functools.lru_cache(maxsize=2)
def _load_d16_two_head_fused_softmax_payload(path: pathlib.Path, run_native: bool) -> dict[str, Any]:
    """Load the d16 two-head fused gate payload and its fixed source/envelope evidence pair."""

    raw = read_bounded_text(
        path,
        D16_TWO_HEAD_FUSED_SOFTMAX_MAX_JSON_BYTES,
        "d16 two-head fused Softmax-table gate evidence",
    )
    source_raw = read_bounded_text(
        D16_TWO_HEAD_FUSED_SOFTMAX_SOURCE_INPUT_JSON,
        D16_TWO_HEAD_FUSED_SOFTMAX_SOURCE_INPUT_MAX_JSON_BYTES,
        "d16 two-head source input evidence",
    )
    envelope_raw = read_bounded_text(
        D16_TWO_HEAD_FUSED_SOFTMAX_ENVELOPE_JSON,
        D16_TWO_HEAD_FUSED_SOFTMAX_ENVELOPE_MAX_JSON_BYTES,
        "d16 two-head fused Softmax-table proof envelope",
    )
    try:
        payload = json.loads(raw)
        source_input = json.loads(source_raw)
        envelope = json.loads(envelope_raw)
        D16_TWO_HEAD_FUSED_SOFTMAX.SOURCE_INPUT_MODULE.validate_payload(source_input)
        D16_TWO_HEAD_FUSED_SOFTMAX.SOURCE_INPUT_MODULE.validate_payload(envelope.get("source_input"))
        D16_TWO_HEAD_FUSED_SOFTMAX.validate_result(payload)
        D16_TWO_HEAD_FUSED_SOFTMAX.validate_fused_envelope(envelope, source_input, run_native=run_native)
    except D16_TWO_HEAD_FUSED_SOFTMAX.AttentionKvD16TwoHeadFusedSoftmaxTableGateError as error:
        raise AttentionKvRouteSelectorError(f"d16 two-head fused Softmax-table drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"d16 two-head fused Softmax-table malformed: {error}") from error
    return payload


def load_d16_two_head_fused_softmax_payload(
    path: pathlib.Path = D16_TWO_HEAD_FUSED_SOFTMAX_JSON,
    *,
    run_native: bool = False,
) -> dict[str, Any]:
    """Load the d16 two-head fused Softmax-table gate payload."""

    return copy.deepcopy(_load_d16_two_head_fused_softmax_payload(path, run_native))


@functools.lru_cache(maxsize=2)
def _load_d16_quantized_softmax_receipt_payload(path: pathlib.Path, run_native: bool) -> dict[str, Any]:
    """Load and validate the d16 implementation-exact quantized Softmax receipt payload."""

    raw = read_bounded_text(
        path,
        D16_QUANTIZED_SOFTMAX_RECEIPT_MAX_JSON_BYTES,
        "d16 quantized Softmax receipt evidence",
    )
    try:
        payload = json.loads(raw)
        D16_QUANTIZED_SOFTMAX.validate_result(payload, run_native=run_native)
    except D16_QUANTIZED_SOFTMAX.QuantizedSoftmaxReceiptGateError as error:
        raise AttentionKvRouteSelectorError(f"d16 quantized Softmax receipt drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"d16 quantized Softmax receipt malformed: {error}") from error
    return payload


def load_d16_quantized_softmax_receipt_payload(
    path: pathlib.Path = D16_QUANTIZED_SOFTMAX_RECEIPT_JSON,
    *,
    run_native: bool = False,
) -> dict[str, Any]:
    """Load the d16 implementation-exact quantized Softmax receipt payload."""

    return copy.deepcopy(_load_d16_quantized_softmax_receipt_payload(path, run_native))


@functools.lru_cache(maxsize=1)
def _load_softmax_edge_corpus_payload(path: pathlib.Path) -> dict[str, Any]:
    """Load and validate the d16 Softmax denominator/rounding edge corpus."""

    raw = read_bounded_text(
        path,
        SOFTMAX_EDGE_CORPUS_MAX_JSON_BYTES,
        "d16 Softmax denominator/rounding edge corpus evidence",
    )
    try:
        payload = json.loads(raw)
        SOFTMAX_EDGE_CORPUS.validate_result(payload)
    except SOFTMAX_EDGE_CORPUS.SoftmaxEdgeCorpusGateError as error:
        raise AttentionKvRouteSelectorError(f"d16 Softmax edge corpus drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"d16 Softmax edge corpus malformed: {error}") from error
    return payload


@functools.lru_cache(maxsize=2)
def _load_d16_two_head_quantized_softmax_receipt_payload(path: pathlib.Path, run_native: bool) -> dict[str, Any]:
    """Load and validate the d16 two-head implementation-exact quantized Softmax receipt payload."""

    raw = read_bounded_text(
        path,
        D16_TWO_HEAD_QUANTIZED_SOFTMAX_RECEIPT_MAX_JSON_BYTES,
        "d16 two-head quantized Softmax receipt evidence",
    )
    try:
        payload = json.loads(raw)
        D16_TWO_HEAD_QUANTIZED_SOFTMAX.validate_result(payload, run_native=run_native)
    except D16_TWO_HEAD_QUANTIZED_SOFTMAX.D16TwoHeadQuantizedSoftmaxReceiptGateError as error:
        raise AttentionKvRouteSelectorError(f"d16 two-head quantized Softmax receipt drift: {error}") from error
    except Exception as error:
        raise AttentionKvRouteSelectorError(f"d16 two-head quantized Softmax receipt malformed: {error}") from error
    return payload


def load_d16_two_head_quantized_softmax_receipt_payload(
    path: pathlib.Path = D16_TWO_HEAD_QUANTIZED_SOFTMAX_RECEIPT_JSON,
    *,
    run_native: bool = False,
) -> dict[str, Any]:
    """Load the d16 two-head implementation-exact quantized Softmax receipt payload."""

    return copy.deepcopy(_load_d16_two_head_quantized_softmax_receipt_payload(path, run_native))


def load_softmax_edge_corpus_payload(
    path: pathlib.Path = SOFTMAX_EDGE_CORPUS_JSON,
) -> dict[str, Any]:
    """Load the d16 Softmax denominator/rounding edge corpus payload."""

    return copy.deepcopy(_load_softmax_edge_corpus_payload(path))


def snark_receipt_summary(snark_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the proof-backed route fields the selector depends on."""

    metrics = snark_payload["receipt_metrics"]
    statement = snark_payload["statement_receipt"]
    return {
        "schema": snark_payload["schema"],
        "decision": snark_payload["decision"],
        "result": snark_payload["result"],
        "claim_boundary": snark_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json",
        "proof_system": snark_payload["external_system"]["proof_system"],
        "proof_system_version": snark_payload["external_system"]["version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "public_signal_count": metrics["public_signal_count"],
        "public_signal_field_count": statement["public_signal_field_count"],
        "statement_commitment": statement["statement_commitment"],
        "receipt_commitment": statement["receipt_commitment"],
        "mutations_checked": snark_payload["case_count"],
        "mutations_rejected": sum(1 for case in snark_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": snark_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def risc0_receipt_summary(risc0_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the RISC Zero semantics route fields the selector depends on."""

    metrics = risc0_payload["proof_metrics"]
    journal = risc0_payload["journal"]
    return {
        "schema": risc0_payload["schema"],
        "decision": risc0_payload["decision"],
        "result": risc0_payload["result"],
        "claim_boundary": risc0_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.json",
        "proof_system": risc0_payload["system"],
        "proof_system_version": risc0_payload["receipt_verification"]["risc0_zkvm_version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "verifier_time_ms": metrics["verifier_time_ms"],
        "proof_generation_time_source": metrics["proof_generation_time_source"],
        "verifier_time_source": metrics["verifier_time_source"],
        "journal_commitment": risc0_payload["journal_commitment"],
        "receipt_commitment": risc0_payload["receipt_commitment"],
        "image_id_hex": risc0_payload["receipt_verification"]["image_id_hex"],
        "selected_position": journal["selected_position"],
        "attention_output": journal["attention_output"],
        "next_kv_items": risc0_payload["summary"]["next_kv_items"],
        "next_kv_cache": journal["next_kv_cache"],
        "mutations_checked": risc0_payload["case_count"],
        "mutations_rejected": sum(1 for case in risc0_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": risc0_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def risc0_sequence_receipt_summary(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the RISC Zero carried-sequence route fields the selector depends on."""

    metrics = sequence_payload["proof_metrics"]
    journal = sequence_payload["journal"]
    summary = sequence_payload["summary"]
    return {
        "schema": sequence_payload["schema"],
        "decision": sequence_payload["decision"],
        "result": sequence_payload["result"],
        "claim_boundary": sequence_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.json",
        "proof_system": sequence_payload["system"],
        "proof_system_version": sequence_payload["receipt_verification"]["risc0_zkvm_version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "verifier_time_ms": metrics["verifier_time_ms"],
        "proof_generation_time_source": metrics["proof_generation_time_source"],
        "verifier_time_source": metrics["verifier_time_source"],
        "journal_commitment": sequence_payload["journal_commitment"],
        "statement_commitment": sequence_payload["statement_fields"]["statement_commitment"],
        "receipt_commitment": sequence_payload["receipt_commitment"],
        "image_id_hex": sequence_payload["receipt_verification"]["image_id_hex"],
        "sequence_length": journal["sequence_length"],
        "transition_rows": len(journal["transitions"]),
        "selected_positions": summary["selected_positions"],
        "attention_outputs": summary["attention_outputs"],
        "final_kv_items": summary["final_kv_items"],
        "transition_commitments": sequence_payload["transition_commitments"],
        "mutations_checked": sequence_payload["case_count"],
        "mutations_rejected": sum(1 for case in sequence_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": sequence_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def risc0_scaled_sequence_receipt_summary(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the RISC Zero scaled carried-sequence route fields the selector depends on."""

    metrics = sequence_payload["proof_metrics"]
    journal = sequence_payload["journal"]
    summary = sequence_payload["summary"]
    return {
        "schema": sequence_payload["schema"],
        "decision": sequence_payload["decision"],
        "result": sequence_payload["result"],
        "claim_boundary": sequence_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.json",
        "proof_system": sequence_payload["system"],
        "proof_system_version": sequence_payload["receipt_verification"]["risc0_zkvm_version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "verifier_time_ms": metrics["verifier_time_ms"],
        "proof_generation_time_source": metrics["proof_generation_time_source"],
        "verifier_time_source": metrics["verifier_time_source"],
        "journal_commitment": sequence_payload["journal_commitment"],
        "statement_commitment": sequence_payload["statement_fields"]["statement_commitment"],
        "receipt_commitment": sequence_payload["receipt_commitment"],
        "image_id_hex": sequence_payload["receipt_verification"]["image_id_hex"],
        "sequence_length": journal["sequence_length"],
        "transition_rows": len(journal["transitions"]),
        "selected_positions": summary["selected_positions"],
        "attention_outputs": summary["attention_outputs"],
        "final_kv_items": summary["final_kv_items"],
        "transition_commitments": sequence_payload["transition_commitments"],
        "mutations_checked": sequence_payload["case_count"],
        "mutations_rejected": sum(1 for case in sequence_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": sequence_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def risc0_wide_masked_sequence_receipt_summary(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the RISC Zero d=8 causal-prefix carried-sequence route fields."""

    metrics = sequence_payload["proof_metrics"]
    journal = sequence_payload["journal"]
    summary = sequence_payload["summary"]
    return {
        "schema": sequence_payload["schema"],
        "decision": sequence_payload["decision"],
        "result": sequence_payload["result"],
        "claim_boundary": sequence_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.json",
        "proof_system": sequence_payload["system"],
        "proof_system_version": sequence_payload["receipt_verification"]["risc0_zkvm_version"],
        "proof_size_bytes": metrics["proof_size_bytes"],
        "verifier_time_ms": metrics["verifier_time_ms"],
        "proof_generation_time_source": metrics["proof_generation_time_source"],
        "verifier_time_source": metrics["verifier_time_source"],
        "journal_commitment": sequence_payload["journal_commitment"],
        "statement_commitment": sequence_payload["statement_fields"]["statement_commitment"],
        "receipt_commitment": sequence_payload["receipt_commitment"],
        "image_id_hex": sequence_payload["receipt_verification"]["image_id_hex"],
        "sequence_length": journal["sequence_length"],
        "transition_rows": len(journal["transitions"]),
        "key_width": journal["key_width"],
        "value_width": journal["value_width"],
        "masking_policy": journal["masking_policy"],
        "tie_break": journal["tie_break"],
        "selected_positions": summary["selected_positions"],
        "attention_outputs": summary["attention_outputs"],
        "final_kv_items": summary["final_kv_items"],
        "transition_commitments": sequence_payload["transition_commitments"],
        "mutations_checked": sequence_payload["case_count"],
        "mutations_rejected": sum(1 for case in sequence_payload["cases"] if case["rejected"] is True),
        "all_mutations_rejected": sequence_payload["all_mutations_rejected"],
        "timing_policy": metrics["timing_policy"],
    }


def stwo_native_masked_sequence_summary(native_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the native Stwo d=8 causal-prefix proof route fields."""

    envelope = load_stwo_native_masked_sequence_envelope()
    envelope_input = envelope["input"]
    if native_payload != envelope_input:
        raise AttentionKvRouteSelectorError("Stwo native proof envelope/input drift")
    proof = envelope["proof"]
    return {
        "schema": envelope_input["schema"],
        "decision": envelope["decision"],
        "result": "GO",
        "claim_boundary": (
            "NATIVE_STWO_D8_CAUSAL_MASKED_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_AIR_PROOF_"
            "NOT_SOFTMAX_NOT_MULTIHEAD_NOT_LONG_CONTEXT_NOT_RECURSION_OR_PCD"
        ),
        "evidence": "docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json",
        "proof_artifact": (
            "docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json"
        ),
        "proof_system": "Stwo",
        "proof_backend": envelope["proof_backend"],
        "proof_system_version": envelope_input["proof_version"],
        "proof_size_bytes": len(proof),
        "envelope_size_bytes": STWO_NATIVE_MASKED_SEQUENCE_ENVELOPE_JSON.stat().st_size,
        "statement_commitment": envelope_input["statement_commitment"],
        "public_instance_commitment": envelope_input["public_instance_commitment"],
        "score_row_commitment": envelope_input["score_row_commitment"],
        "final_kv_cache_commitment": envelope_input["final_kv_cache_commitment"],
        "outputs_commitment": envelope_input["outputs_commitment"],
        "sequence_length": envelope_input["sequence_length"],
        "score_row_count": envelope_input["score_row_count"],
        "trace_row_count": envelope_input["trace_row_count"],
        "key_width": envelope_input["key_width"],
        "value_width": envelope_input["value_width"],
        "masking_policy": envelope_input["masking_policy"],
        "tie_break": envelope_input["tie_break"],
        "selected_positions": envelope_input["selected_positions"],
        "attention_outputs": envelope_input["attention_outputs"],
        "initial_kv_items": envelope_input["initial_kv_items"],
        "final_kv_items": envelope_input["final_kv_items"],
        "timing_policy": "single_local_dev_profile_engineering_only",
    }


def quantized_softmax_receipt_summary(softmax_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the narrow quantized Softmax-table route fields the selector depends on."""

    contract = softmax_payload["kernel_contract"]
    metrics = contract["kernel_metrics"]
    return {
        "schema": softmax_payload["schema"],
        "decision": softmax_payload["decision"],
        "route_id": softmax_payload["route_id"],
        "result": "GO",
        "claim_boundary": softmax_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json",
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "proof_size_bytes": softmax_payload["fused_proof_size_bytes"],
        "envelope_size_bytes": softmax_payload["fused_envelope_size_bytes"],
        "fused_gate_decision": softmax_payload["fused_gate_decision"],
        "kernel_name": contract["kernel_name"],
        "kernel_status": contract["kernel_status"],
        "real_softmax_status": contract["real_softmax_status"],
        "score_scale": contract["score_scale"],
        "score_gap_clip": contract["score_gap_clip"],
        "weight_policy": contract["weight_policy"],
        "weight_table_commitment": contract["weight_table_commitment"],
        "denominator_policy": contract["denominator_policy"],
        "division_rule": contract["division_rule"],
        "rounding_rule": contract["rounding_rule"],
        "division_error_bound": contract["division_error_bound"],
        "table_error_bound_policy": contract["table_error_bound_policy"],
        "source_statement_commitment": contract["source_statement_commitment"],
        "source_public_instance_commitment": contract["source_public_instance_commitment"],
        "source_score_row_commitment": contract["source_score_row_commitment"],
        "lookup_claims": softmax_payload["lookup_claims"],
        "table_rows": softmax_payload["table_rows"],
        "steps": metrics["steps"],
        "score_rows": metrics["score_rows"],
        "per_step_denominators": metrics["per_step_denominators"],
        "max_observed_division_error_fraction": metrics["max_observed_division_error_fraction"],
        "mutations_checked": softmax_payload["mutations_checked"],
        "mutations_rejected": softmax_payload["mutations_rejected"],
        "all_mutations_rejected": softmax_payload["mutations_rejected"] == softmax_payload["mutations_checked"],
        "timing_policy": softmax_payload["timing_policy"],
    }


def multihead_quantized_softmax_receipt_summary(softmax_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the multi-head quantized Softmax-table route fields."""

    contract = softmax_payload["kernel_contract"]
    metrics = contract["aggregate_metrics"]
    profiles = contract["profiles"]
    return {
        "schema": softmax_payload["schema"],
        "decision": softmax_payload["decision"],
        "route_id": softmax_payload["route_id"],
        "result": "GO",
        "claim_boundary": softmax_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json",
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "kernel_name": contract["kernel_name"],
        "kernel_status": contract["kernel_status"],
        "real_softmax_status": contract["real_softmax_status"],
        "score_scale": contract["score_scale"],
        "score_gap_clip": contract["score_gap_clip"],
        "weight_policy": contract["weight_policy"],
        "denominator_policy": contract["denominator_policy"],
        "division_rule": contract["division_rule"],
        "rounding_rule": contract["rounding_rule"],
        "division_error_bound": contract["division_error_bound"],
        "table_error_bound_policy": contract["table_error_bound_policy"],
        "head_binding_policy": contract["head_binding_policy"],
        "step_binding_policy": contract["step_binding_policy"],
        "output_order_policy": contract["output_order_policy"],
        "causal_mask_policy": contract["causal_mask_policy"],
        "profiles_checked": softmax_payload["profiles_checked"],
        "head_counts_checked": softmax_payload["head_counts_checked"],
        "lookup_claims_total": softmax_payload["lookup_claims_total"],
        "score_rows_total": softmax_payload["score_rows_total"],
        "trace_rows_total": softmax_payload["trace_rows_total"],
        "table_rows": softmax_payload["table_rows"],
        "fused_proof_size_bytes_sum": softmax_payload["fused_proof_size_bytes_sum"],
        "max_fused_proof_size_bytes": softmax_payload["max_fused_proof_size_bytes"],
        "profile_statement_commitments": [profile["source_statement_commitment"] for profile in profiles],
        "profile_weight_table_commitments": [profile["source_weight_table_commitment"] for profile in profiles],
        "profile_fused_envelope_commitments": [profile["fused_envelope_commitment"] for profile in profiles],
        "profile_fused_proof_commitments": [profile["fused_proof_commitment"] for profile in profiles],
        "profile_output_index_policies": [profile["output_index_policy"] for profile in profiles],
        "max_observed_division_error_fraction": metrics["max_observed_division_error_fraction"],
        "mutations_checked": softmax_payload["mutations_checked"],
        "mutations_rejected": softmax_payload["mutations_rejected"],
        "all_mutations_rejected": softmax_payload["mutations_rejected"] == softmax_payload["mutations_checked"],
        "timing_policy": softmax_payload["timing_policy"],
    }


def longseq_fused_softmax_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the two-head long-sequence fused Softmax-table route fields."""

    return {
        "schema": payload["schema"],
        "decision": payload["decision"],
        "route_id": payload["route_id"],
        "result": "GO",
        "claim_boundary": payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.json",
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "fusion_status": payload["fusion_status"],
        "non_fused_status": payload["non_fused_status"],
        "source_head_count": payload["source_head_count"],
        "sequence_length_per_head": 16,
        "lookup_claims": payload["lookup_claims"],
        "score_rows": payload["lookup_claims"],
        "trace_rows": payload["trace_rows"],
        "table_rows": payload["table_rows"],
        "source_proof_size_bytes": payload["source_proof_size_bytes"],
        "source_envelope_size_bytes": payload["source_envelope_size_bytes"],
        "source_plus_sidecar_raw_proof_bytes": payload["source_plus_sidecar_raw_proof_bytes"],
        "fused_proof_size_bytes": payload["fused_proof_size_bytes"],
        "fused_envelope_size_bytes": payload["fused_envelope_size_bytes"],
        "fused_over_source_proof_bytes": payload["fused_over_source_proof_bytes"],
        "fused_saves_vs_source_plus_sidecar_bytes": payload["fused_saves_vs_source_plus_sidecar_bytes"],
        "fused_to_source_plus_sidecar_ratio": payload["fused_to_source_plus_sidecar_ratio"],
        "source_statement_commitment": payload["source_statement_commitment"],
        "source_public_instance_commitment": payload["source_public_instance_commitment"],
        "source_score_row_commitment": payload["source_score_row_commitment"],
        "source_final_kv_cache_commitment": payload["source_final_kv_cache_commitment"],
        "source_outputs_commitment": payload["source_outputs_commitment"],
        "source_weight_table_commitment": payload["source_weight_table_commitment"],
        "fused_envelope_commitment": payload["fused_envelope_commitment"],
        "fused_proof_commitment": payload["fused_proof_commitment"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
        "all_mutations_rejected": payload["mutations_checked"] == payload["mutations_rejected"],
        "timing_policy": payload["timing_policy"],
        "non_claims": payload["non_claims"],
    }


def d16_fused_softmax_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the d16 fused Softmax-table route fields."""

    return {
        "schema": payload["schema"],
        "decision": payload["decision"],
        "route_id": payload["route_id"],
        "result": "GO",
        "claim_boundary": payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.json",
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "fusion_status": payload["fusion_status"],
        "non_fused_status": payload["non_fused_status"],
        "key_width": 16,
        "value_width": 16,
        "lookup_claims": payload["lookup_claims"],
        "score_rows": payload["lookup_claims"],
        "trace_rows": payload["trace_rows"],
        "table_rows": payload["table_rows"],
        "source_proof_size_bytes": payload["source_proof_size_bytes"],
        "source_envelope_size_bytes": payload["source_envelope_size_bytes"],
        "source_plus_sidecar_raw_proof_bytes": payload["source_plus_sidecar_raw_proof_bytes"],
        "fused_proof_size_bytes": payload["fused_proof_size_bytes"],
        "fused_envelope_size_bytes": payload["fused_envelope_size_bytes"],
        "fused_over_source_proof_bytes": payload["fused_over_source_proof_bytes"],
        "fused_saves_vs_source_plus_sidecar_bytes": payload["fused_saves_vs_source_plus_sidecar_bytes"],
        "fused_to_source_plus_sidecar_ratio": payload["fused_to_source_plus_sidecar_ratio"],
        "lookup_relation": payload["lookup_relation"],
        "lookup_relation_width": payload["lookup_relation_width"],
        "source_statement_commitment": payload["source_statement_commitment"],
        "source_public_instance_commitment": payload["source_public_instance_commitment"],
        "source_score_row_commitment": payload["source_score_row_commitment"],
        "source_weight_table_commitment": payload["source_weight_table_commitment"],
        "fused_envelope_commitment": payload["fused_envelope_commitment"],
        "fused_proof_commitment": payload["fused_proof_commitment"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
        "all_mutations_rejected": payload["mutations_checked"] == payload["mutations_rejected"],
        "timing_policy": payload["timing_policy"],
        "non_claims": payload["non_claims"],
    }


def d16_two_head_fused_softmax_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the d16 two-head fused Softmax-table route fields."""

    return {
        "schema": payload["schema"],
        "decision": payload["decision"],
        "route_id": payload["route_id"],
        "result": "GO",
        "claim_boundary": payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-gate-2026-05.json",
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "fusion_status": payload["fusion_status"],
        "non_fused_status": payload["non_fused_status"],
        "key_width": 16,
        "value_width": 16,
        "head_count": payload["source_head_count"],
        "lookup_claims": payload["lookup_claims"],
        "score_rows": payload["lookup_claims"],
        "trace_rows": payload["trace_rows"],
        "table_rows": payload["table_rows"],
        "source_proof_size_bytes": payload["source_proof_size_bytes"],
        "source_envelope_size_bytes": payload["source_envelope_size_bytes"],
        "sidecar_proof_size_bytes": payload["sidecar_proof_size_bytes"],
        "source_plus_sidecar_raw_proof_bytes": payload["source_plus_sidecar_raw_proof_bytes"],
        "fused_proof_size_bytes": payload["fused_proof_size_bytes"],
        "fused_envelope_size_bytes": payload["fused_envelope_size_bytes"],
        "fused_over_source_proof_bytes": payload["fused_over_source_proof_bytes"],
        "fused_saves_vs_source_plus_sidecar_bytes": payload["fused_saves_vs_source_plus_sidecar_bytes"],
        "fused_to_source_plus_sidecar_ratio": f"{payload['fused_to_source_plus_sidecar_ratio']:.6f}",
        "lookup_relation": payload["lookup_relation"],
        "lookup_relation_width": payload["lookup_relation_width"],
        "source_statement_commitment": payload["source_statement_commitment"],
        "source_public_instance_commitment": payload["source_public_instance_commitment"],
        "source_score_row_commitment": payload["source_score_row_commitment"],
        "source_final_kv_cache_commitment": payload["source_final_kv_cache_commitment"],
        "source_outputs_commitment": payload["source_outputs_commitment"],
        "source_weight_table_commitment": payload["source_weight_table_commitment"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
        "all_mutations_rejected": payload["mutations_checked"] == payload["mutations_rejected"],
        "timing_policy": payload["timing_policy"],
        "non_claims": payload["non_claims"],
    }


def d16_quantized_softmax_receipt_summary(softmax_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the d16 quantized Softmax-table receipt route fields."""

    contract = softmax_payload["kernel_contract"]
    metrics = contract["kernel_metrics"]
    return {
        "schema": softmax_payload["schema"],
        "decision": softmax_payload["decision"],
        "route_id": softmax_payload["route_id"],
        "result": "GO",
        "claim_boundary": softmax_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json",
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "proof_size_bytes": softmax_payload["fused_proof_size_bytes"],
        "envelope_size_bytes": softmax_payload["fused_envelope_size_bytes"],
        "fused_gate_decision": softmax_payload["fused_gate_decision"],
        "kernel_name": contract["kernel_name"],
        "kernel_status": contract["kernel_status"],
        "real_softmax_status": contract["real_softmax_status"],
        "score_scale": contract["score_scale"],
        "key_width": contract["key_width"],
        "value_width": contract["value_width"],
        "sequence_length": contract["sequence_length"],
        "score_gap_clip": contract["score_gap_clip"],
        "weight_policy": contract["weight_policy"],
        "weight_table_commitment": contract["weight_table_commitment"],
        "denominator_policy": contract["denominator_policy"],
        "division_rule": contract["division_rule"],
        "rounding_rule": contract["rounding_rule"],
        "division_error_bound": contract["division_error_bound"],
        "table_error_bound_policy": contract["table_error_bound_policy"],
        "source_statement_commitment": contract["source_statement_commitment"],
        "source_public_instance_commitment": contract["source_public_instance_commitment"],
        "source_score_row_commitment": contract["source_score_row_commitment"],
        "source_outputs_commitment": contract["source_outputs_commitment"],
        "source_final_kv_cache_commitment": contract["source_final_kv_cache_commitment"],
        "lookup_claims": softmax_payload["lookup_claims"],
        "table_rows": softmax_payload["table_rows"],
        "steps": metrics["steps"],
        "score_rows": metrics["score_rows"],
        "per_step_denominators": metrics["per_step_denominators"],
        "max_observed_division_error_fraction": metrics["max_observed_division_error_fraction"],
        "mutations_checked": softmax_payload["mutations_checked"],
        "mutations_rejected": softmax_payload["mutations_rejected"],
        "all_mutations_rejected": softmax_payload["mutations_rejected"] == softmax_payload["mutations_checked"],
        "timing_policy": softmax_payload["timing_policy"],
    }


def d16_two_head_quantized_softmax_receipt_summary(softmax_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the d16 two-head quantized Softmax-table receipt route fields."""

    contract = softmax_payload["kernel_contract"]
    metrics = contract["kernel_metrics"]
    return {
        "schema": softmax_payload["schema"],
        "decision": softmax_payload["decision"],
        "route_id": softmax_payload["route_id"],
        "result": "GO",
        "claim_boundary": softmax_payload["claim_boundary"],
        "evidence": (
            "docs/engineering/evidence/"
            "zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.json"
        ),
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "proof_size_bytes": softmax_payload["fused_proof_size_bytes"],
        "envelope_size_bytes": softmax_payload["fused_envelope_size_bytes"],
        "fused_gate_decision": softmax_payload["fused_gate_decision"],
        "kernel_name": contract["kernel_name"],
        "kernel_status": contract["kernel_status"],
        "real_softmax_status": contract["real_softmax_status"],
        "score_scale": contract["score_scale"],
        "key_width": contract["key_width"],
        "value_width": contract["value_width"],
        "head_count": contract["head_count"],
        "sequence_length_per_head": contract["sequence_length_per_head"],
        "score_gap_clip": contract["score_gap_clip"],
        "weight_policy": contract["weight_policy"],
        "weight_table_commitment": contract["weight_table_commitment"],
        "denominator_policy": contract["denominator_policy"],
        "division_rule": contract["division_rule"],
        "rounding_rule": contract["rounding_rule"],
        "division_error_bound": contract["division_error_bound"],
        "table_error_bound_policy": contract["table_error_bound_policy"],
        "head_binding_policy": contract["head_binding_policy"],
        "step_binding_policy": contract["step_binding_policy"],
        "output_order_policy": contract["output_order_policy"],
        "causal_mask_policy": contract["causal_mask_policy"],
        "source_statement_commitment": contract["source_statement_commitment"],
        "source_public_instance_commitment": contract["source_public_instance_commitment"],
        "source_score_row_commitment": contract["source_score_row_commitment"],
        "source_outputs_commitment": contract["source_outputs_commitment"],
        "source_final_kv_cache_commitment": contract["source_final_kv_cache_commitment"],
        "lookup_claims": softmax_payload["lookup_claims"],
        "table_rows": softmax_payload["table_rows"],
        "input_steps": metrics["input_steps"],
        "score_rows": metrics["score_rows"],
        "trace_rows": metrics["trace_rows"],
        "per_head_step_denominators": metrics["per_head_step_denominators"],
        "max_observed_division_error_fraction": metrics["max_observed_division_error_fraction"],
        "mutations_checked": softmax_payload["mutations_checked"],
        "mutations_rejected": softmax_payload["mutations_rejected"],
        "all_mutations_rejected": softmax_payload["mutations_rejected"] == softmax_payload["mutations_checked"],
        "timing_policy": softmax_payload["timing_policy"],
    }


def softmax_edge_corpus_summary(edge_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the d16 denominator/rounding edge-corpus fields."""

    return {
        "schema": edge_payload["schema"],
        "decision": edge_payload["decision"],
        "result": "GO",
        "claim_boundary": edge_payload["claim_boundary"],
        "evidence": "docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json",
        "edge_case_count": edge_payload["edge_case_count"],
        "route_mutations_checked": edge_payload["route_mutations_checked"],
        "route_mutations_rejected": edge_payload["route_mutations_rejected"],
        "all_route_mutations_rejected": (
            edge_payload["route_mutations_checked"] == edge_payload["route_mutations_rejected"]
        ),
        "min_denominator": edge_payload["min_denominator"],
        "max_denominator": edge_payload["max_denominator"],
        "max_remainder_ratio": edge_payload["max_remainder_ratio"],
        "negative_numerator_cases": edge_payload["negative_numerator_cases"],
        "all_scores_equal_denominator": next(
            case["denominator"] for case in edge_payload["edge_cases"] if case["name"] == "all_scores_equal"
        ),
        "all_clipped_denominator": next(
            case["denominator"] for case in edge_payload["edge_cases"] if case["name"] == "all_nonmax_scores_clipped"
        ),
        "dominant_denominator": next(
            case["denominator"] for case in edge_payload["edge_cases"] if case["name"] == "one_dominant_key_all_others_clipped"
        ),
        "timing_policy": edge_payload["timing_policy"],
    }


def route_inventory(*, run_native: bool = False) -> list[dict[str, Any]]:
    """Return the checked route candidates as fresh dictionaries."""

    snark = snark_receipt_summary(load_snark_payload())
    risc0 = risc0_receipt_summary(load_risc0_payload())
    risc0_sequence = risc0_sequence_receipt_summary(load_risc0_sequence_payload())
    risc0_scaled_sequence = risc0_scaled_sequence_receipt_summary(load_risc0_scaled_sequence_payload())
    risc0_wide_masked_sequence = risc0_wide_masked_sequence_receipt_summary(load_risc0_wide_masked_sequence_payload())
    stwo_native = stwo_native_masked_sequence_summary(load_stwo_native_masked_sequence_payload())
    quantized_softmax = quantized_softmax_receipt_summary(
        load_quantized_softmax_receipt_payload(run_native=run_native)
    )
    multihead_quantized_softmax = multihead_quantized_softmax_receipt_summary(
        load_multihead_quantized_softmax_receipt_payload(run_native=run_native)
    )
    longseq_fused_softmax = longseq_fused_softmax_summary(
        load_longseq_fused_softmax_payload(run_native=run_native)
    )
    d16_fused_softmax = d16_fused_softmax_summary(load_d16_fused_softmax_payload(run_native=run_native))
    d16_two_head_fused_softmax = d16_two_head_fused_softmax_summary(
        load_d16_two_head_fused_softmax_payload(run_native=run_native)
    )
    d16_quantized_softmax = d16_quantized_softmax_receipt_summary(
        load_d16_quantized_softmax_receipt_payload(run_native=run_native)
    )
    d16_two_head_quantized_softmax = d16_two_head_quantized_softmax_receipt_summary(
        load_d16_two_head_quantized_softmax_receipt_payload(run_native=run_native)
    )
    routes = [dict(route) for route in BASE_ROUTES]
    local_stwo_route = route_candidate_by_id(routes, LOCAL_STWO_ROUTE_ID)
    local_stwo_route["evidence"] = stwo_native["evidence"]
    local_stwo_route["proof_artifact"] = stwo_native["proof_artifact"]
    local_stwo_route["proof_system"] = stwo_native["proof_system"]
    local_stwo_route["proof_system_version"] = stwo_native["proof_system_version"]
    local_stwo_route["proof_size_bytes"] = stwo_native["proof_size_bytes"]
    local_stwo_route["envelope_size_bytes"] = stwo_native["envelope_size_bytes"]
    local_stwo_route["statement_commitment"] = stwo_native["statement_commitment"]
    local_stwo_route["public_instance_commitment"] = stwo_native["public_instance_commitment"]
    local_stwo_route["score_row_commitment"] = stwo_native["score_row_commitment"]
    local_stwo_route["sequence_length"] = stwo_native["sequence_length"]
    local_stwo_route["score_row_count"] = stwo_native["score_row_count"]
    local_stwo_route["trace_row_count"] = stwo_native["trace_row_count"]
    local_stwo_route["key_width"] = stwo_native["key_width"]
    local_stwo_route["value_width"] = stwo_native["value_width"]
    local_stwo_route["masking_policy"] = stwo_native["masking_policy"]
    local_stwo_route["tie_break"] = stwo_native["tie_break"]
    local_stwo_route["final_kv_items"] = stwo_native["final_kv_items"]
    quantized_softmax_route = route_candidate_by_id(routes, QUANTIZED_SOFTMAX_ROUTE_ID)
    quantized_softmax_route["evidence"] = quantized_softmax["evidence"]
    quantized_softmax_route["proof_system"] = quantized_softmax["proof_system"]
    quantized_softmax_route["proof_backend"] = quantized_softmax["proof_backend"]
    quantized_softmax_route["proof_size_bytes"] = quantized_softmax["proof_size_bytes"]
    quantized_softmax_route["envelope_size_bytes"] = quantized_softmax["envelope_size_bytes"]
    quantized_softmax_route["kernel_name"] = quantized_softmax["kernel_name"]
    quantized_softmax_route["kernel_status"] = quantized_softmax["kernel_status"]
    quantized_softmax_route["real_softmax_status"] = quantized_softmax["real_softmax_status"]
    quantized_softmax_route["score_scale"] = quantized_softmax["score_scale"]
    quantized_softmax_route["score_gap_clip"] = quantized_softmax["score_gap_clip"]
    quantized_softmax_route["lookup_claims"] = quantized_softmax["lookup_claims"]
    quantized_softmax_route["table_rows"] = quantized_softmax["table_rows"]
    quantized_softmax_route["source_statement_commitment"] = quantized_softmax["source_statement_commitment"]
    quantized_softmax_route["weight_table_commitment"] = quantized_softmax["weight_table_commitment"]
    multihead_quantized_softmax_route = route_candidate_by_id(routes, MULTIHEAD_QUANTIZED_SOFTMAX_ROUTE_ID)
    multihead_quantized_softmax_route["evidence"] = multihead_quantized_softmax["evidence"]
    multihead_quantized_softmax_route["proof_system"] = multihead_quantized_softmax["proof_system"]
    multihead_quantized_softmax_route["proof_backend"] = multihead_quantized_softmax["proof_backend"]
    multihead_quantized_softmax_route["fused_proof_size_bytes_sum"] = multihead_quantized_softmax[
        "fused_proof_size_bytes_sum"
    ]
    multihead_quantized_softmax_route["max_fused_proof_size_bytes"] = multihead_quantized_softmax[
        "max_fused_proof_size_bytes"
    ]
    multihead_quantized_softmax_route["kernel_name"] = multihead_quantized_softmax["kernel_name"]
    multihead_quantized_softmax_route["kernel_status"] = multihead_quantized_softmax["kernel_status"]
    multihead_quantized_softmax_route["real_softmax_status"] = multihead_quantized_softmax["real_softmax_status"]
    multihead_quantized_softmax_route["score_scale"] = multihead_quantized_softmax["score_scale"]
    multihead_quantized_softmax_route["score_gap_clip"] = multihead_quantized_softmax["score_gap_clip"]
    multihead_quantized_softmax_route["profiles_checked"] = multihead_quantized_softmax["profiles_checked"]
    multihead_quantized_softmax_route["head_counts_checked"] = multihead_quantized_softmax["head_counts_checked"]
    multihead_quantized_softmax_route["lookup_claims_total"] = multihead_quantized_softmax["lookup_claims_total"]
    multihead_quantized_softmax_route["table_rows"] = multihead_quantized_softmax["table_rows"]
    multihead_quantized_softmax_route["profile_statement_commitments"] = multihead_quantized_softmax[
        "profile_statement_commitments"
    ]
    multihead_quantized_softmax_route["profile_weight_table_commitments"] = multihead_quantized_softmax[
        "profile_weight_table_commitments"
    ]
    multihead_quantized_softmax_route["profile_fused_envelope_commitments"] = multihead_quantized_softmax[
        "profile_fused_envelope_commitments"
    ]
    multihead_quantized_softmax_route["profile_fused_proof_commitments"] = multihead_quantized_softmax[
        "profile_fused_proof_commitments"
    ]
    longseq_fused_softmax_route = route_candidate_by_id(routes, LONGSEQ_FUSED_SOFTMAX_ROUTE_ID)
    longseq_fused_softmax_route["evidence"] = longseq_fused_softmax["evidence"]
    longseq_fused_softmax_route["proof_system"] = longseq_fused_softmax["proof_system"]
    longseq_fused_softmax_route["proof_backend"] = longseq_fused_softmax["proof_backend"]
    longseq_fused_softmax_route["fusion_status"] = longseq_fused_softmax["fusion_status"]
    longseq_fused_softmax_route["non_fused_status"] = longseq_fused_softmax["non_fused_status"]
    longseq_fused_softmax_route["source_head_count"] = longseq_fused_softmax["source_head_count"]
    longseq_fused_softmax_route["sequence_length_per_head"] = longseq_fused_softmax["sequence_length_per_head"]
    longseq_fused_softmax_route["lookup_claims"] = longseq_fused_softmax["lookup_claims"]
    longseq_fused_softmax_route["trace_rows"] = longseq_fused_softmax["trace_rows"]
    longseq_fused_softmax_route["table_rows"] = longseq_fused_softmax["table_rows"]
    longseq_fused_softmax_route["source_proof_size_bytes"] = longseq_fused_softmax["source_proof_size_bytes"]
    longseq_fused_softmax_route["fused_proof_size_bytes"] = longseq_fused_softmax["fused_proof_size_bytes"]
    longseq_fused_softmax_route["fused_envelope_size_bytes"] = longseq_fused_softmax["fused_envelope_size_bytes"]
    longseq_fused_softmax_route["source_statement_commitment"] = longseq_fused_softmax["source_statement_commitment"]
    longseq_fused_softmax_route["source_weight_table_commitment"] = longseq_fused_softmax[
        "source_weight_table_commitment"
    ]
    longseq_fused_softmax_route["fused_envelope_commitment"] = longseq_fused_softmax[
        "fused_envelope_commitment"
    ]
    longseq_fused_softmax_route["fused_proof_commitment"] = longseq_fused_softmax["fused_proof_commitment"]
    d16_fused_softmax_route = route_candidate_by_id(routes, D16_FUSED_SOFTMAX_ROUTE_ID)
    d16_fused_softmax_route["evidence"] = d16_fused_softmax["evidence"]
    d16_fused_softmax_route["proof_system"] = d16_fused_softmax["proof_system"]
    d16_fused_softmax_route["proof_backend"] = d16_fused_softmax["proof_backend"]
    d16_fused_softmax_route["fusion_status"] = d16_fused_softmax["fusion_status"]
    d16_fused_softmax_route["non_fused_status"] = d16_fused_softmax["non_fused_status"]
    d16_fused_softmax_route["key_width"] = d16_fused_softmax["key_width"]
    d16_fused_softmax_route["value_width"] = d16_fused_softmax["value_width"]
    d16_fused_softmax_route["lookup_claims"] = d16_fused_softmax["lookup_claims"]
    d16_fused_softmax_route["trace_rows"] = d16_fused_softmax["trace_rows"]
    d16_fused_softmax_route["table_rows"] = d16_fused_softmax["table_rows"]
    d16_fused_softmax_route["source_proof_size_bytes"] = d16_fused_softmax["source_proof_size_bytes"]
    d16_fused_softmax_route["fused_proof_size_bytes"] = d16_fused_softmax["fused_proof_size_bytes"]
    d16_fused_softmax_route["fused_envelope_size_bytes"] = d16_fused_softmax["fused_envelope_size_bytes"]
    d16_fused_softmax_route["source_statement_commitment"] = d16_fused_softmax["source_statement_commitment"]
    d16_fused_softmax_route["source_weight_table_commitment"] = d16_fused_softmax[
        "source_weight_table_commitment"
    ]
    d16_two_head_fused_softmax_route = route_candidate_by_id(routes, D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID)
    d16_two_head_fused_softmax_route["evidence"] = d16_two_head_fused_softmax["evidence"]
    d16_two_head_fused_softmax_route["proof_system"] = d16_two_head_fused_softmax["proof_system"]
    d16_two_head_fused_softmax_route["proof_backend"] = d16_two_head_fused_softmax["proof_backend"]
    d16_two_head_fused_softmax_route["fusion_status"] = d16_two_head_fused_softmax["fusion_status"]
    d16_two_head_fused_softmax_route["non_fused_status"] = d16_two_head_fused_softmax["non_fused_status"]
    d16_two_head_fused_softmax_route["key_width"] = d16_two_head_fused_softmax["key_width"]
    d16_two_head_fused_softmax_route["value_width"] = d16_two_head_fused_softmax["value_width"]
    d16_two_head_fused_softmax_route["head_count"] = d16_two_head_fused_softmax["head_count"]
    d16_two_head_fused_softmax_route["lookup_claims"] = d16_two_head_fused_softmax["lookup_claims"]
    d16_two_head_fused_softmax_route["trace_rows"] = d16_two_head_fused_softmax["trace_rows"]
    d16_two_head_fused_softmax_route["table_rows"] = d16_two_head_fused_softmax["table_rows"]
    d16_two_head_fused_softmax_route["source_proof_size_bytes"] = d16_two_head_fused_softmax[
        "source_proof_size_bytes"
    ]
    d16_two_head_fused_softmax_route["sidecar_proof_size_bytes"] = d16_two_head_fused_softmax[
        "sidecar_proof_size_bytes"
    ]
    d16_two_head_fused_softmax_route["fused_proof_size_bytes"] = d16_two_head_fused_softmax[
        "fused_proof_size_bytes"
    ]
    d16_two_head_fused_softmax_route["fused_envelope_size_bytes"] = d16_two_head_fused_softmax[
        "fused_envelope_size_bytes"
    ]
    d16_two_head_fused_softmax_route["source_statement_commitment"] = d16_two_head_fused_softmax[
        "source_statement_commitment"
    ]
    d16_two_head_fused_softmax_route["source_weight_table_commitment"] = d16_two_head_fused_softmax[
        "source_weight_table_commitment"
    ]
    d16_quantized_softmax_route = route_candidate_by_id(routes, D16_QUANTIZED_SOFTMAX_ROUTE_ID)
    d16_quantized_softmax_route["evidence"] = d16_quantized_softmax["evidence"]
    d16_quantized_softmax_route["proof_system"] = d16_quantized_softmax["proof_system"]
    d16_quantized_softmax_route["proof_backend"] = d16_quantized_softmax["proof_backend"]
    d16_quantized_softmax_route["proof_size_bytes"] = d16_quantized_softmax["proof_size_bytes"]
    d16_quantized_softmax_route["envelope_size_bytes"] = d16_quantized_softmax["envelope_size_bytes"]
    d16_quantized_softmax_route["kernel_name"] = d16_quantized_softmax["kernel_name"]
    d16_quantized_softmax_route["kernel_status"] = d16_quantized_softmax["kernel_status"]
    d16_quantized_softmax_route["real_softmax_status"] = d16_quantized_softmax["real_softmax_status"]
    d16_quantized_softmax_route["key_width"] = d16_quantized_softmax["key_width"]
    d16_quantized_softmax_route["value_width"] = d16_quantized_softmax["value_width"]
    d16_quantized_softmax_route["sequence_length"] = d16_quantized_softmax["sequence_length"]
    d16_quantized_softmax_route["score_scale"] = d16_quantized_softmax["score_scale"]
    d16_quantized_softmax_route["score_gap_clip"] = d16_quantized_softmax["score_gap_clip"]
    d16_quantized_softmax_route["lookup_claims"] = d16_quantized_softmax["lookup_claims"]
    d16_quantized_softmax_route["table_rows"] = d16_quantized_softmax["table_rows"]
    d16_quantized_softmax_route["source_statement_commitment"] = d16_quantized_softmax[
        "source_statement_commitment"
    ]
    d16_quantized_softmax_route["weight_table_commitment"] = d16_quantized_softmax["weight_table_commitment"]
    d16_two_head_quantized_softmax_route = route_candidate_by_id(routes, D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID)
    d16_two_head_quantized_softmax_route["evidence"] = d16_two_head_quantized_softmax["evidence"]
    d16_two_head_quantized_softmax_route["proof_system"] = d16_two_head_quantized_softmax["proof_system"]
    d16_two_head_quantized_softmax_route["proof_backend"] = d16_two_head_quantized_softmax["proof_backend"]
    d16_two_head_quantized_softmax_route["proof_size_bytes"] = d16_two_head_quantized_softmax["proof_size_bytes"]
    d16_two_head_quantized_softmax_route["envelope_size_bytes"] = d16_two_head_quantized_softmax[
        "envelope_size_bytes"
    ]
    d16_two_head_quantized_softmax_route["kernel_name"] = d16_two_head_quantized_softmax["kernel_name"]
    d16_two_head_quantized_softmax_route["kernel_status"] = d16_two_head_quantized_softmax["kernel_status"]
    d16_two_head_quantized_softmax_route["real_softmax_status"] = d16_two_head_quantized_softmax[
        "real_softmax_status"
    ]
    d16_two_head_quantized_softmax_route["key_width"] = d16_two_head_quantized_softmax["key_width"]
    d16_two_head_quantized_softmax_route["value_width"] = d16_two_head_quantized_softmax["value_width"]
    d16_two_head_quantized_softmax_route["head_count"] = d16_two_head_quantized_softmax["head_count"]
    d16_two_head_quantized_softmax_route["sequence_length_per_head"] = d16_two_head_quantized_softmax[
        "sequence_length_per_head"
    ]
    d16_two_head_quantized_softmax_route["input_steps"] = d16_two_head_quantized_softmax["input_steps"]
    d16_two_head_quantized_softmax_route["score_scale"] = d16_two_head_quantized_softmax["score_scale"]
    d16_two_head_quantized_softmax_route["score_gap_clip"] = d16_two_head_quantized_softmax["score_gap_clip"]
    d16_two_head_quantized_softmax_route["lookup_claims"] = d16_two_head_quantized_softmax["lookup_claims"]
    d16_two_head_quantized_softmax_route["table_rows"] = d16_two_head_quantized_softmax["table_rows"]
    d16_two_head_quantized_softmax_route["source_statement_commitment"] = d16_two_head_quantized_softmax[
        "source_statement_commitment"
    ]
    d16_two_head_quantized_softmax_route["weight_table_commitment"] = d16_two_head_quantized_softmax[
        "weight_table_commitment"
    ]
    snark_route = route_candidate_by_id(routes, EXTERNAL_SNARK_ROUTE_ID)
    snark_route["evidence"] = snark["evidence"]
    snark_route["proof_system"] = snark["proof_system"]
    snark_route["proof_size_bytes"] = snark["proof_size_bytes"]
    snark_route["public_signal_count"] = snark["public_signal_count"]
    snark_route["statement_commitment"] = snark["statement_commitment"]
    snark_route["receipt_commitment"] = snark["receipt_commitment"]
    zkvm_route = route_candidate_by_id(routes, EXTERNAL_ZKVM_ROUTE_ID)
    zkvm_route["evidence"] = risc0["evidence"]
    zkvm_route["proof_system"] = risc0["proof_system"]
    zkvm_route["proof_system_version"] = risc0["proof_system_version"]
    zkvm_route["proof_size_bytes"] = risc0["proof_size_bytes"]
    zkvm_route["journal_commitment"] = risc0["journal_commitment"]
    zkvm_route["receipt_commitment"] = risc0["receipt_commitment"]
    zkvm_route["image_id_hex"] = risc0["image_id_hex"]
    zkvm_route["selected_position"] = risc0["selected_position"]
    zkvm_route["next_kv_items"] = risc0["next_kv_items"]
    sequence_route = route_candidate_by_id(routes, EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID)
    sequence_route["evidence"] = risc0_sequence["evidence"]
    sequence_route["proof_system"] = risc0_sequence["proof_system"]
    sequence_route["proof_system_version"] = risc0_sequence["proof_system_version"]
    sequence_route["proof_size_bytes"] = risc0_sequence["proof_size_bytes"]
    sequence_route["journal_commitment"] = risc0_sequence["journal_commitment"]
    sequence_route["statement_commitment"] = risc0_sequence["statement_commitment"]
    sequence_route["receipt_commitment"] = risc0_sequence["receipt_commitment"]
    sequence_route["image_id_hex"] = risc0_sequence["image_id_hex"]
    sequence_route["sequence_length"] = risc0_sequence["sequence_length"]
    sequence_route["transition_rows"] = risc0_sequence["transition_rows"]
    sequence_route["final_kv_items"] = risc0_sequence["final_kv_items"]
    scaled_sequence_route = route_candidate_by_id(routes, EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID)
    scaled_sequence_route["evidence"] = risc0_scaled_sequence["evidence"]
    scaled_sequence_route["proof_system"] = risc0_scaled_sequence["proof_system"]
    scaled_sequence_route["proof_system_version"] = risc0_scaled_sequence["proof_system_version"]
    scaled_sequence_route["proof_size_bytes"] = risc0_scaled_sequence["proof_size_bytes"]
    scaled_sequence_route["journal_commitment"] = risc0_scaled_sequence["journal_commitment"]
    scaled_sequence_route["statement_commitment"] = risc0_scaled_sequence["statement_commitment"]
    scaled_sequence_route["receipt_commitment"] = risc0_scaled_sequence["receipt_commitment"]
    scaled_sequence_route["image_id_hex"] = risc0_scaled_sequence["image_id_hex"]
    scaled_sequence_route["sequence_length"] = risc0_scaled_sequence["sequence_length"]
    scaled_sequence_route["transition_rows"] = risc0_scaled_sequence["transition_rows"]
    scaled_sequence_route["final_kv_items"] = risc0_scaled_sequence["final_kv_items"]
    wide_masked_sequence_route = route_candidate_by_id(routes, EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID)
    wide_masked_sequence_route["evidence"] = risc0_wide_masked_sequence["evidence"]
    wide_masked_sequence_route["proof_system"] = risc0_wide_masked_sequence["proof_system"]
    wide_masked_sequence_route["proof_system_version"] = risc0_wide_masked_sequence["proof_system_version"]
    wide_masked_sequence_route["proof_size_bytes"] = risc0_wide_masked_sequence["proof_size_bytes"]
    wide_masked_sequence_route["journal_commitment"] = risc0_wide_masked_sequence["journal_commitment"]
    wide_masked_sequence_route["statement_commitment"] = risc0_wide_masked_sequence["statement_commitment"]
    wide_masked_sequence_route["receipt_commitment"] = risc0_wide_masked_sequence["receipt_commitment"]
    wide_masked_sequence_route["image_id_hex"] = risc0_wide_masked_sequence["image_id_hex"]
    wide_masked_sequence_route["sequence_length"] = risc0_wide_masked_sequence["sequence_length"]
    wide_masked_sequence_route["transition_rows"] = risc0_wide_masked_sequence["transition_rows"]
    wide_masked_sequence_route["key_width"] = risc0_wide_masked_sequence["key_width"]
    wide_masked_sequence_route["value_width"] = risc0_wide_masked_sequence["value_width"]
    wide_masked_sequence_route["masking_policy"] = risc0_wide_masked_sequence["masking_policy"]
    wide_masked_sequence_route["tie_break"] = risc0_wide_masked_sequence["tie_break"]
    wide_masked_sequence_route["final_kv_items"] = risc0_wide_masked_sequence["final_kv_items"]
    return copy.deepcopy(routes)


def route_candidate_by_id(routes: list[dict[str, Any]], route_id: str) -> dict[str, Any]:
    for route in routes:
        if route.get("route_id") == route_id:
            return route
    raise AttentionKvRouteSelectorError(f"missing route candidate: {route_id}")


def source_contract_summary(source_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the source-backed receipt fields relevant to route selection."""

    receipt = source_payload["receipt"]
    return {
        "source_schema": source_payload["schema"],
        "source_decision": source_payload["decision"],
        "source_evidence": "docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json",
        "source_statement_commitment": receipt["statement_commitment"],
        "source_proof_status": receipt["proof_status"],
        "source_verifier_domain": receipt["verifier_domain"],
        "source_mutations_checked": source_payload["mutations_checked"],
        "source_mutations_rejected": source_payload["mutations_rejected"],
        "source_all_mutations_rejected": source_payload["all_mutations_rejected"],
        "required_public_fields": list(REQUIRED_PUBLIC_FIELDS),
        "present_public_fields": [field for field in REQUIRED_PUBLIC_FIELDS if field in receipt],
    }


def build_payload(*, run_native: bool = False) -> dict[str, Any]:
    """Build and self-validate the proof-route selector decision payload."""

    source_payload = load_source_payload()
    snark_payload = load_snark_payload()
    risc0_payload = load_risc0_payload()
    risc0_sequence_payload = load_risc0_sequence_payload()
    risc0_scaled_sequence_payload = load_risc0_scaled_sequence_payload()
    risc0_wide_masked_sequence_payload = load_risc0_wide_masked_sequence_payload()
    stwo_native_masked_sequence_payload = load_stwo_native_masked_sequence_payload()
    quantized_softmax_payload = load_quantized_softmax_receipt_payload(run_native=run_native)
    multihead_quantized_softmax_payload = load_multihead_quantized_softmax_receipt_payload(run_native=run_native)
    longseq_fused_softmax_payload = load_longseq_fused_softmax_payload(run_native=run_native)
    d16_fused_softmax_payload = load_d16_fused_softmax_payload(run_native=run_native)
    d16_two_head_fused_softmax_payload = load_d16_two_head_fused_softmax_payload(run_native=run_native)
    d16_quantized_softmax_payload = load_d16_quantized_softmax_receipt_payload(run_native=run_native)
    d16_two_head_quantized_softmax_payload = load_d16_two_head_quantized_softmax_receipt_payload(
        run_native=run_native
    )
    softmax_edge_corpus_payload = load_softmax_edge_corpus_payload()
    summary = source_contract_summary(source_payload)
    snark_summary = snark_receipt_summary(snark_payload)
    risc0_summary = risc0_receipt_summary(risc0_payload)
    risc0_sequence_summary = risc0_sequence_receipt_summary(risc0_sequence_payload)
    risc0_scaled_sequence_summary = risc0_scaled_sequence_receipt_summary(risc0_scaled_sequence_payload)
    risc0_wide_masked_sequence_summary = risc0_wide_masked_sequence_receipt_summary(risc0_wide_masked_sequence_payload)
    stwo_native_masked_sequence_receipt = stwo_native_masked_sequence_summary(stwo_native_masked_sequence_payload)
    quantized_softmax_receipt = quantized_softmax_receipt_summary(quantized_softmax_payload)
    multihead_quantized_softmax_receipt = multihead_quantized_softmax_receipt_summary(
        multihead_quantized_softmax_payload
    )
    longseq_fused_softmax_receipt = longseq_fused_softmax_summary(longseq_fused_softmax_payload)
    d16_fused_softmax_receipt = d16_fused_softmax_summary(d16_fused_softmax_payload)
    d16_two_head_fused_softmax_receipt = d16_two_head_fused_softmax_summary(d16_two_head_fused_softmax_payload)
    d16_quantized_softmax_receipt = d16_quantized_softmax_receipt_summary(d16_quantized_softmax_payload)
    d16_two_head_quantized_softmax_receipt = d16_two_head_quantized_softmax_receipt_summary(
        d16_two_head_quantized_softmax_payload
    )
    softmax_edge_corpus = softmax_edge_corpus_summary(softmax_edge_corpus_payload)
    routes = route_inventory(run_native=run_native)
    proof_backed_routes_available = [
        route["route_id"]
        for route in routes
        if route["usable_today"] is True and route["proof_backed"] is True
    ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "generated_at": _generated_at(),
        "git_commit": os.environ.get("ZKAI_ATTENTION_KV_ROUTE_SELECTOR_GIT_COMMIT", _git_commit()),
        "question": (
            "Can the checked attention/KV transition receipt be promoted from a source-backed "
            "contract to a proof-backed receipt today?"
        ),
        "source_contract": summary,
        "external_snark_receipt": snark_summary,
        "external_risc0_receipt": risc0_summary,
        "external_risc0_sequence_receipt": risc0_sequence_summary,
        "external_risc0_scaled_sequence_receipt": risc0_scaled_sequence_summary,
        "external_risc0_wide_masked_sequence_receipt": risc0_wide_masked_sequence_summary,
        "native_stwo_masked_sequence_receipt": stwo_native_masked_sequence_receipt,
        "quantized_softmax_receipt": quantized_softmax_receipt,
        "multihead_quantized_softmax_receipt": multihead_quantized_softmax_receipt,
        "longseq_fused_softmax_receipt": longseq_fused_softmax_receipt,
        "d16_fused_softmax_receipt": d16_fused_softmax_receipt,
        "d16_two_head_fused_softmax_receipt": d16_two_head_fused_softmax_receipt,
        "d16_quantized_softmax_receipt": d16_quantized_softmax_receipt,
        "d16_two_head_quantized_softmax_receipt": d16_two_head_quantized_softmax_receipt,
        "softmax_denominator_rounding_edge_corpus": softmax_edge_corpus,
        "route_candidates": routes,
        "proof_backed_routes_available": proof_backed_routes_available,
        "metrics": {
            "native_stwo_proof_size_bytes": stwo_native_masked_sequence_receipt["proof_size_bytes"],
            "native_stwo_envelope_size_bytes": stwo_native_masked_sequence_receipt["envelope_size_bytes"],
            "native_stwo_score_row_count": stwo_native_masked_sequence_receipt["score_row_count"],
            "native_stwo_trace_row_count": stwo_native_masked_sequence_receipt["trace_row_count"],
            "quantized_softmax_proof_size_bytes": quantized_softmax_receipt["proof_size_bytes"],
            "quantized_softmax_envelope_size_bytes": quantized_softmax_receipt["envelope_size_bytes"],
            "quantized_softmax_lookup_claims": quantized_softmax_receipt["lookup_claims"],
            "quantized_softmax_table_rows": quantized_softmax_receipt["table_rows"],
            "quantized_softmax_max_observed_division_error_fraction": (
                quantized_softmax_receipt["max_observed_division_error_fraction"]
            ),
            "multihead_quantized_softmax_fused_proof_size_bytes_sum": (
                multihead_quantized_softmax_receipt["fused_proof_size_bytes_sum"]
            ),
            "multihead_quantized_softmax_max_fused_proof_size_bytes": (
                multihead_quantized_softmax_receipt["max_fused_proof_size_bytes"]
            ),
            "multihead_quantized_softmax_lookup_claims_total": (
                multihead_quantized_softmax_receipt["lookup_claims_total"]
            ),
            "multihead_quantized_softmax_trace_rows_total": (
                multihead_quantized_softmax_receipt["trace_rows_total"]
            ),
            "multihead_quantized_softmax_profiles_checked": (
                multihead_quantized_softmax_receipt["profiles_checked"]
            ),
            "multihead_quantized_softmax_head_counts_checked": (
                multihead_quantized_softmax_receipt["head_counts_checked"]
            ),
            "multihead_quantized_softmax_max_observed_division_error_fraction": (
                multihead_quantized_softmax_receipt["max_observed_division_error_fraction"]
            ),
            "longseq_fused_softmax_lookup_claims": longseq_fused_softmax_receipt["lookup_claims"],
            "longseq_fused_softmax_trace_rows": longseq_fused_softmax_receipt["trace_rows"],
            "longseq_fused_softmax_fused_proof_size_bytes": (
                longseq_fused_softmax_receipt["fused_proof_size_bytes"]
            ),
            "longseq_fused_softmax_fused_envelope_size_bytes": (
                longseq_fused_softmax_receipt["fused_envelope_size_bytes"]
            ),
            "longseq_fused_softmax_source_plus_sidecar_raw_proof_bytes": (
                longseq_fused_softmax_receipt["source_plus_sidecar_raw_proof_bytes"]
            ),
            "longseq_fused_softmax_fused_saves_vs_source_plus_sidecar_bytes": (
                longseq_fused_softmax_receipt["fused_saves_vs_source_plus_sidecar_bytes"]
            ),
            "longseq_fused_softmax_fused_to_source_plus_sidecar_ratio": (
                longseq_fused_softmax_receipt["fused_to_source_plus_sidecar_ratio"]
            ),
            "d16_fused_softmax_lookup_claims": d16_fused_softmax_receipt["lookup_claims"],
            "d16_fused_softmax_trace_rows": d16_fused_softmax_receipt["trace_rows"],
            "d16_fused_softmax_key_width": d16_fused_softmax_receipt["key_width"],
            "d16_fused_softmax_value_width": d16_fused_softmax_receipt["value_width"],
            "d16_fused_softmax_fused_proof_size_bytes": d16_fused_softmax_receipt["fused_proof_size_bytes"],
            "d16_fused_softmax_fused_envelope_size_bytes": d16_fused_softmax_receipt["fused_envelope_size_bytes"],
            "d16_fused_softmax_source_plus_sidecar_raw_proof_bytes": (
                d16_fused_softmax_receipt["source_plus_sidecar_raw_proof_bytes"]
            ),
            "d16_fused_softmax_fused_saves_vs_source_plus_sidecar_bytes": (
                d16_fused_softmax_receipt["fused_saves_vs_source_plus_sidecar_bytes"]
            ),
            "d16_fused_softmax_fused_to_source_plus_sidecar_ratio": (
                d16_fused_softmax_receipt["fused_to_source_plus_sidecar_ratio"]
            ),
            "d16_two_head_fused_softmax_lookup_claims": d16_two_head_fused_softmax_receipt["lookup_claims"],
            "d16_two_head_fused_softmax_trace_rows": d16_two_head_fused_softmax_receipt["trace_rows"],
            "d16_two_head_fused_softmax_key_width": d16_two_head_fused_softmax_receipt["key_width"],
            "d16_two_head_fused_softmax_value_width": d16_two_head_fused_softmax_receipt["value_width"],
            "d16_two_head_fused_softmax_head_count": d16_two_head_fused_softmax_receipt["head_count"],
            "d16_two_head_fused_softmax_fused_proof_size_bytes": (
                d16_two_head_fused_softmax_receipt["fused_proof_size_bytes"]
            ),
            "d16_two_head_fused_softmax_fused_envelope_size_bytes": (
                d16_two_head_fused_softmax_receipt["fused_envelope_size_bytes"]
            ),
            "d16_two_head_fused_softmax_source_plus_sidecar_raw_proof_bytes": (
                d16_two_head_fused_softmax_receipt["source_plus_sidecar_raw_proof_bytes"]
            ),
            "d16_two_head_fused_softmax_fused_saves_vs_source_plus_sidecar_bytes": (
                d16_two_head_fused_softmax_receipt["fused_saves_vs_source_plus_sidecar_bytes"]
            ),
            "d16_two_head_fused_softmax_fused_to_source_plus_sidecar_ratio": (
                d16_two_head_fused_softmax_receipt["fused_to_source_plus_sidecar_ratio"]
            ),
            "d16_quantized_softmax_proof_size_bytes": d16_quantized_softmax_receipt["proof_size_bytes"],
            "d16_quantized_softmax_envelope_size_bytes": d16_quantized_softmax_receipt["envelope_size_bytes"],
            "d16_quantized_softmax_lookup_claims": d16_quantized_softmax_receipt["lookup_claims"],
            "d16_quantized_softmax_table_rows": d16_quantized_softmax_receipt["table_rows"],
            "d16_quantized_softmax_key_width": d16_quantized_softmax_receipt["key_width"],
            "d16_quantized_softmax_value_width": d16_quantized_softmax_receipt["value_width"],
            "d16_quantized_softmax_sequence_length": d16_quantized_softmax_receipt["sequence_length"],
            "d16_quantized_softmax_max_observed_division_error_fraction": (
                d16_quantized_softmax_receipt["max_observed_division_error_fraction"]
            ),
            "d16_two_head_quantized_softmax_proof_size_bytes": (
                d16_two_head_quantized_softmax_receipt["proof_size_bytes"]
            ),
            "d16_two_head_quantized_softmax_envelope_size_bytes": (
                d16_two_head_quantized_softmax_receipt["envelope_size_bytes"]
            ),
            "d16_two_head_quantized_softmax_lookup_claims": (
                d16_two_head_quantized_softmax_receipt["lookup_claims"]
            ),
            "d16_two_head_quantized_softmax_table_rows": d16_two_head_quantized_softmax_receipt["table_rows"],
            "d16_two_head_quantized_softmax_key_width": d16_two_head_quantized_softmax_receipt["key_width"],
            "d16_two_head_quantized_softmax_value_width": d16_two_head_quantized_softmax_receipt["value_width"],
            "d16_two_head_quantized_softmax_head_count": d16_two_head_quantized_softmax_receipt["head_count"],
            "d16_two_head_quantized_softmax_sequence_length_per_head": (
                d16_two_head_quantized_softmax_receipt["sequence_length_per_head"]
            ),
            "d16_two_head_quantized_softmax_input_steps": d16_two_head_quantized_softmax_receipt["input_steps"],
            "d16_two_head_quantized_softmax_max_observed_division_error_fraction": (
                d16_two_head_quantized_softmax_receipt["max_observed_division_error_fraction"]
            ),
            "d16_softmax_edge_case_count": softmax_edge_corpus["edge_case_count"],
            "d16_softmax_edge_route_mutations_checked": softmax_edge_corpus["route_mutations_checked"],
            "d16_softmax_edge_route_mutations_rejected": softmax_edge_corpus["route_mutations_rejected"],
            "d16_softmax_edge_min_denominator": softmax_edge_corpus["min_denominator"],
            "d16_softmax_edge_max_denominator": softmax_edge_corpus["max_denominator"],
            "d16_softmax_edge_max_remainder_ratio": softmax_edge_corpus["max_remainder_ratio"],
            "snark_proof_size_bytes": snark_summary["proof_size_bytes"],
            "snark_public_signal_count": snark_summary["public_signal_count"],
            "risc0_receipt_size_bytes": risc0_summary["proof_size_bytes"],
            "risc0_verifier_time_ms": risc0_summary["verifier_time_ms"],
            "risc0_verifier_time_source": risc0_summary["verifier_time_source"],
            "risc0_sequence_receipt_size_bytes": risc0_sequence_summary["proof_size_bytes"],
            "risc0_sequence_verifier_time_ms": risc0_sequence_summary["verifier_time_ms"],
            "risc0_sequence_verifier_time_source": risc0_sequence_summary["verifier_time_source"],
            "risc0_scaled_sequence_receipt_size_bytes": risc0_scaled_sequence_summary["proof_size_bytes"],
            "risc0_scaled_sequence_verifier_time_ms": risc0_scaled_sequence_summary["verifier_time_ms"],
            "risc0_scaled_sequence_verifier_time_source": risc0_scaled_sequence_summary["verifier_time_source"],
            "risc0_wide_masked_sequence_receipt_size_bytes": risc0_wide_masked_sequence_summary["proof_size_bytes"],
            "risc0_wide_masked_sequence_verifier_time_ms": risc0_wide_masked_sequence_summary["verifier_time_ms"],
            "risc0_wide_masked_sequence_verifier_time_source": risc0_wide_masked_sequence_summary["verifier_time_source"],
            "proof_generation_time_ms": None,
            "verifier_time_ms": None,
            "timing_policy": snark_summary["timing_policy"],
            "risc0_timing_policy": risc0_summary["timing_policy"],
        },
        "next_go_criteria": list(EXPECTED_NEXT_GO_CRITERIA),
        "non_claims": list(EXPECTED_NON_CLAIMS),
    }
    payload["selector_commitment"] = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "source_contract": payload["source_contract"],
            "external_snark_receipt": payload["external_snark_receipt"],
            "external_risc0_receipt": payload["external_risc0_receipt"],
            "external_risc0_sequence_receipt": payload["external_risc0_sequence_receipt"],
            "external_risc0_scaled_sequence_receipt": payload["external_risc0_scaled_sequence_receipt"],
            "external_risc0_wide_masked_sequence_receipt": payload["external_risc0_wide_masked_sequence_receipt"],
            "native_stwo_masked_sequence_receipt": payload["native_stwo_masked_sequence_receipt"],
            "quantized_softmax_receipt": payload["quantized_softmax_receipt"],
            "multihead_quantized_softmax_receipt": payload["multihead_quantized_softmax_receipt"],
            "longseq_fused_softmax_receipt": payload["longseq_fused_softmax_receipt"],
            "d16_fused_softmax_receipt": payload["d16_fused_softmax_receipt"],
            "d16_two_head_fused_softmax_receipt": payload["d16_two_head_fused_softmax_receipt"],
            "d16_quantized_softmax_receipt": payload["d16_quantized_softmax_receipt"],
            "d16_two_head_quantized_softmax_receipt": payload["d16_two_head_quantized_softmax_receipt"],
            "softmax_denominator_rounding_edge_corpus": payload["softmax_denominator_rounding_edge_corpus"],
            "route_candidates": payload["route_candidates"],
            "proof_backed_routes_available": payload["proof_backed_routes_available"],
            "metrics": payload["metrics"],
            "next_go_criteria": payload["next_go_criteria"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-proof-route-selector:v1",
    )
    payload["mutation_cases"] = run_mutation_cases(payload)
    payload["mutations_checked"] = len(payload["mutation_cases"])
    payload["mutations_rejected"] = sum(1 for item in payload["mutation_cases"] if item["rejected"] is True)
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    validate_payload(payload)
    return payload


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    """Apply one deterministic mutation that the selector must reject."""

    out = copy.deepcopy(payload)
    out.pop("mutation_cases", None)
    out.pop("mutations_checked", None)
    out.pop("mutations_rejected", None)
    out.pop("all_mutations_rejected", None)
    if name == "source_contract_decision_drift":
        out["source_contract"]["source_decision"] = "GO_PROOF_BACKED_ATTENTION_KV_RECEIPT"
    elif name == "source_contract_proof_status_overclaim":
        out["source_contract"]["source_proof_status"] = "PROVEN_BY_STWO"
    elif name == "source_contract_mutation_rejections_drift":
        out["source_contract"]["source_mutations_rejected"] -= 1
    elif name == "missing_required_public_field":
        out["source_contract"]["present_public_fields"].remove("next_kv_cache_commitment")
    elif name == "local_stwo_route_removed":
        local_stwo_route = route_candidate_by_id(out["route_candidates"], LOCAL_STWO_ROUTE_ID)
        local_stwo_route["status"] = "NO_GO_MISSING_NATIVE_STWO_ATTENTION_KV_PROOF"
        local_stwo_route["usable_today"] = False
        local_stwo_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(LOCAL_STWO_ROUTE_ID)
    elif name == "local_stwo_native_receipt_decision_drift":
        out["native_stwo_masked_sequence_receipt"]["decision"] = (
            "NO_GO_MISSING_NATIVE_STWO_ATTENTION_KV_MASKED_SEQUENCE_PROOF"
        )
    elif name == "local_stwo_native_receipt_statement_drift":
        out["native_stwo_masked_sequence_receipt"]["statement_commitment"] = (
            "blake2b-256:0000000000000000000000000000000000000000000000000000000000000000"
        )
    elif name == "quantized_softmax_route_removed":
        quantized_route = route_candidate_by_id(out["route_candidates"], QUANTIZED_SOFTMAX_ROUTE_ID)
        quantized_route["status"] = "NO_GO_MISSING_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
        quantized_route["usable_today"] = False
        quantized_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(QUANTIZED_SOFTMAX_ROUTE_ID)
    elif name == "quantized_softmax_receipt_decision_drift":
        out["quantized_softmax_receipt"]["decision"] = "NO_GO_MISSING_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
    elif name == "quantized_softmax_receipt_route_drift":
        out["quantized_softmax_receipt"]["route_id"] = "real_valued_softmax_attention_kv_claim"
    elif name == "quantized_softmax_receipt_mutation_rejections_drift":
        out["quantized_softmax_receipt"]["mutations_rejected"] -= 1
    elif name == "quantized_softmax_real_softmax_overclaim":
        out["quantized_softmax_receipt"]["real_softmax_status"] = "GO_REAL_VALUED_SOFTMAX"
    elif name == "quantized_softmax_denominator_drift":
        out["quantized_softmax_receipt"]["per_step_denominators"][0] = 0
    elif name == "multihead_quantized_softmax_route_removed":
        multihead_route = route_candidate_by_id(out["route_candidates"], MULTIHEAD_QUANTIZED_SOFTMAX_ROUTE_ID)
        multihead_route["status"] = "NO_GO_MISSING_MULTIHEAD_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
        multihead_route["usable_today"] = False
        multihead_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(MULTIHEAD_QUANTIZED_SOFTMAX_ROUTE_ID)
    elif name == "multihead_quantized_softmax_receipt_decision_drift":
        out["multihead_quantized_softmax_receipt"]["decision"] = (
            "NO_GO_MISSING_MULTIHEAD_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
        )
    elif name == "multihead_quantized_softmax_receipt_route_drift":
        out["multihead_quantized_softmax_receipt"]["route_id"] = "real_valued_softmax_attention_kv_claim"
    elif name == "multihead_quantized_softmax_receipt_mutation_rejections_drift":
        out["multihead_quantized_softmax_receipt"]["mutations_rejected"] -= 1
    elif name == "multihead_quantized_softmax_real_softmax_overclaim":
        out["multihead_quantized_softmax_receipt"]["real_softmax_status"] = "GO_REAL_VALUED_SOFTMAX"
    elif name == "multihead_quantized_softmax_profile_count_drift":
        out["multihead_quantized_softmax_receipt"]["profiles_checked"] = 1
    elif name == "multihead_quantized_softmax_trace_rows_drift":
        out["multihead_quantized_softmax_receipt"]["trace_rows_total"] = 896
    elif name == "multihead_quantized_softmax_output_mapping_drift":
        out["multihead_quantized_softmax_receipt"]["profile_output_index_policies"][1] = (
            "step_index_times_head_count_plus_head"
        )
    elif name == "longseq_fused_softmax_route_removed":
        longseq_route = route_candidate_by_id(out["route_candidates"], LONGSEQ_FUSED_SOFTMAX_ROUTE_ID)
        longseq_route["status"] = "NO_GO_MISSING_TWO_HEAD_LONGSEQUENCE_FUSED_SOFTMAX_TABLE_PROOF"
        longseq_route["usable_today"] = False
        longseq_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(LONGSEQ_FUSED_SOFTMAX_ROUTE_ID)
    elif name == "longseq_fused_softmax_decision_drift":
        out["longseq_fused_softmax_receipt"]["decision"] = "NO_GO_MISSING_TWO_HEAD_LONGSEQUENCE_FUSED_SOFTMAX_TABLE_PROOF"
    elif name == "longseq_fused_softmax_lookup_claims_drift":
        out["longseq_fused_softmax_receipt"]["lookup_claims"] = 104
    elif name == "longseq_fused_softmax_exact_softmax_overclaim":
        out["longseq_fused_softmax_receipt"]["claim_boundary"] = "GO_REAL_VALUED_SOFTMAX_LONG_CONTEXT_BENCHMARK"
    elif name == "longseq_fused_softmax_mutation_rejections_drift":
        out["longseq_fused_softmax_receipt"]["mutations_rejected"] -= 1
    elif name == "d16_fused_softmax_route_removed":
        d16_route = route_candidate_by_id(out["route_candidates"], D16_FUSED_SOFTMAX_ROUTE_ID)
        d16_route["status"] = "NO_GO_MISSING_D16_FUSED_SOFTMAX_TABLE_PROOF"
        d16_route["usable_today"] = False
        d16_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(D16_FUSED_SOFTMAX_ROUTE_ID)
    elif name == "d16_fused_softmax_decision_drift":
        out["d16_fused_softmax_receipt"]["decision"] = "NO_GO_MISSING_D16_FUSED_SOFTMAX_TABLE_PROOF"
    elif name == "d16_fused_softmax_width_drift":
        out["d16_fused_softmax_receipt"]["key_width"] = 8
    elif name == "d16_fused_softmax_exact_softmax_overclaim":
        out["d16_fused_softmax_receipt"]["claim_boundary"] = "GO_REAL_VALUED_SOFTMAX_WIDTH_BENCHMARK"
    elif name == "d16_fused_softmax_mutation_rejections_drift":
        out["d16_fused_softmax_receipt"]["mutations_rejected"] -= 1
    elif name == "d16_two_head_fused_softmax_route_removed":
        d16_two_head_route = route_candidate_by_id(out["route_candidates"], D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID)
        d16_two_head_route["status"] = "NO_GO_MISSING_D16_TWO_HEAD_FUSED_SOFTMAX_TABLE_PROOF"
        d16_two_head_route["usable_today"] = False
        d16_two_head_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID)
    elif name == "d16_two_head_fused_softmax_decision_drift":
        out["d16_two_head_fused_softmax_receipt"]["decision"] = (
            "NO_GO_MISSING_D16_TWO_HEAD_FUSED_SOFTMAX_TABLE_PROOF"
        )
    elif name == "d16_two_head_fused_softmax_width_or_head_drift":
        out["d16_two_head_fused_softmax_receipt"]["head_count"] = 1
    elif name == "d16_two_head_fused_softmax_exact_softmax_overclaim":
        out["d16_two_head_fused_softmax_receipt"]["claim_boundary"] = (
            "GO_REAL_VALUED_SOFTMAX_WIDTH_AND_MULTIHEAD_BENCHMARK"
        )
    elif name == "d16_two_head_fused_softmax_mutation_rejections_drift":
        out["d16_two_head_fused_softmax_receipt"]["mutations_rejected"] -= 1
    elif name == "d16_quantized_softmax_route_removed":
        d16_quantized_route = route_candidate_by_id(out["route_candidates"], D16_QUANTIZED_SOFTMAX_ROUTE_ID)
        d16_quantized_route["status"] = "NO_GO_MISSING_D16_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
        d16_quantized_route["usable_today"] = False
        d16_quantized_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(D16_QUANTIZED_SOFTMAX_ROUTE_ID)
    elif name == "d16_quantized_softmax_receipt_decision_drift":
        out["d16_quantized_softmax_receipt"]["decision"] = "NO_GO_MISSING_D16_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
    elif name == "d16_quantized_softmax_receipt_route_drift":
        out["d16_quantized_softmax_receipt"]["route_id"] = "real_valued_softmax_attention_kv_claim"
    elif name == "d16_quantized_softmax_real_softmax_overclaim":
        out["d16_quantized_softmax_receipt"]["real_softmax_status"] = "GO_REAL_VALUED_SOFTMAX"
    elif name == "d16_quantized_softmax_width_drift":
        out["d16_quantized_softmax_receipt"]["key_width"] = 8
    elif name == "d16_quantized_softmax_denominator_drift":
        out["d16_quantized_softmax_receipt"]["per_step_denominators"][0] = 0
    elif name == "d16_quantized_softmax_mutation_rejections_drift":
        out["d16_quantized_softmax_receipt"]["mutations_rejected"] -= 1
    elif name == "d16_two_head_quantized_softmax_route_removed":
        d16_two_head_quantized_route = route_candidate_by_id(
            out["route_candidates"], D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID
        )
        d16_two_head_quantized_route["status"] = "NO_GO_MISSING_D16_TWO_HEAD_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
        d16_two_head_quantized_route["usable_today"] = False
        d16_two_head_quantized_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID)
    elif name == "d16_two_head_quantized_softmax_receipt_decision_drift":
        out["d16_two_head_quantized_softmax_receipt"]["decision"] = (
            "NO_GO_MISSING_D16_TWO_HEAD_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
        )
    elif name == "d16_two_head_quantized_softmax_receipt_route_drift":
        out["d16_two_head_quantized_softmax_receipt"]["route_id"] = "real_valued_softmax_attention_kv_claim"
    elif name == "d16_two_head_quantized_softmax_real_softmax_overclaim":
        out["d16_two_head_quantized_softmax_receipt"]["real_softmax_status"] = "GO_REAL_VALUED_SOFTMAX"
    elif name == "d16_two_head_quantized_softmax_width_or_head_drift":
        out["d16_two_head_quantized_softmax_receipt"]["head_count"] = 1
    elif name == "d16_two_head_quantized_softmax_denominator_drift":
        out["d16_two_head_quantized_softmax_receipt"]["per_head_step_denominators"][0]["denominator"] = 0
    elif name == "d16_two_head_quantized_softmax_output_order_drift":
        out["d16_two_head_quantized_softmax_receipt"]["output_order_policy"] = "head_index_times_sequence_length_plus_step"
    elif name == "d16_two_head_quantized_softmax_mutation_rejections_drift":
        out["d16_two_head_quantized_softmax_receipt"]["mutations_rejected"] -= 1
    elif name == "d16_softmax_edge_corpus_claim_boundary_drift":
        out["softmax_denominator_rounding_edge_corpus"]["claim_boundary"] = "GO_REAL_VALUED_SOFTMAX_EDGE_CORPUS"
    elif name == "d16_softmax_edge_corpus_route_mutation_rejections_drift":
        out["softmax_denominator_rounding_edge_corpus"]["route_mutations_rejected"] -= 1
    elif name == "external_snark_route_removed":
        snark_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_SNARK_ROUTE_ID)
        snark_route["status"] = "NO_GO_MISSING_ATTENTION_KV_SNARK_RECEIPT"
        snark_route["usable_today"] = False
        snark_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(EXTERNAL_SNARK_ROUTE_ID)
    elif name == "external_snark_receipt_decision_drift":
        out["external_snark_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_SNARK_RECEIPT"
    elif name == "external_snark_receipt_mutation_rejections_drift":
        out["external_snark_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_route_removed":
        zkvm_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_ZKVM_ROUTE_ID)
        zkvm_route["status"] = "NO_GO_MISSING_ATTENTION_KV_ZKVM_RECEIPT"
        zkvm_route["usable_today"] = False
        zkvm_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(EXTERNAL_ZKVM_ROUTE_ID)
    elif name == "external_zkvm_receipt_decision_drift":
        out["external_risc0_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_RISC0_SEMANTICS_RECEIPT"
    elif name == "external_zkvm_receipt_mutation_rejections_drift":
        out["external_risc0_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_receipt_next_kv_items_drift":
        out["external_risc0_receipt"]["next_kv_items"] -= 1
    elif name == "external_zkvm_metric_source_drift":
        out["external_risc0_receipt"]["verifier_time_source"] = "carried_from_existing_evidence_not_remeasured"
    elif name == "external_zkvm_sequence_route_removed":
        sequence_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID)
        sequence_route["status"] = "NO_GO_MISSING_ATTENTION_KV_SEQUENCE_ZKVM_RECEIPT"
        sequence_route["usable_today"] = False
        sequence_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(EXTERNAL_ZKVM_SEQUENCE_ROUTE_ID)
    elif name == "external_zkvm_sequence_receipt_decision_drift":
        out["external_risc0_sequence_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_RISC0_SEQUENCE_RECEIPT"
    elif name == "external_zkvm_sequence_receipt_mutation_rejections_drift":
        out["external_risc0_sequence_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_sequence_length_drift":
        out["external_risc0_sequence_receipt"]["sequence_length"] = 1
    elif name == "external_zkvm_sequence_intermediate_state_drift":
        out["external_risc0_sequence_receipt"]["selected_positions"][1] = 99
    elif name == "external_zkvm_sequence_metric_source_drift":
        out["external_risc0_sequence_receipt"]["verifier_time_source"] = "carried_from_existing_evidence_not_remeasured"
    elif name == "external_zkvm_scaled_sequence_route_removed":
        scaled_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID)
        scaled_route["status"] = "NO_GO_MISSING_ATTENTION_KV_SCALED_SEQUENCE_ZKVM_RECEIPT"
        scaled_route["usable_today"] = False
        scaled_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(EXTERNAL_ZKVM_SCALED_SEQUENCE_ROUTE_ID)
    elif name == "external_zkvm_scaled_sequence_receipt_decision_drift":
        out["external_risc0_scaled_sequence_receipt"]["decision"] = "NO_GO_MISSING_ATTENTION_KV_RISC0_SCALED_SEQUENCE_RECEIPT"
    elif name == "external_zkvm_scaled_sequence_receipt_mutation_rejections_drift":
        out["external_risc0_scaled_sequence_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_scaled_sequence_length_drift":
        out["external_risc0_scaled_sequence_receipt"]["sequence_length"] = 3
    elif name == "external_zkvm_scaled_sequence_intermediate_state_drift":
        out["external_risc0_scaled_sequence_receipt"]["selected_positions"][4] = 99
    elif name == "external_zkvm_scaled_sequence_metric_source_drift":
        out["external_risc0_scaled_sequence_receipt"]["verifier_time_source"] = "carried_from_existing_evidence_not_remeasured"
    elif name == "external_zkvm_wide_masked_sequence_route_removed":
        wide_masked_route = route_candidate_by_id(out["route_candidates"], EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID)
        wide_masked_route["status"] = "NO_GO_MISSING_ATTENTION_KV_WIDE_MASKED_SEQUENCE_ZKVM_RECEIPT"
        wide_masked_route["usable_today"] = False
        wide_masked_route["proof_backed"] = False
        out["proof_backed_routes_available"] = proof_routes_except(EXTERNAL_ZKVM_WIDE_MASKED_SEQUENCE_ROUTE_ID)
    elif name == "external_zkvm_wide_masked_sequence_receipt_decision_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["decision"] = (
            "NO_GO_MISSING_ATTENTION_KV_RISC0_WIDE_MASKED_SEQUENCE_RECEIPT"
        )
    elif name == "external_zkvm_wide_masked_sequence_receipt_mutation_rejections_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["mutations_rejected"] -= 1
    elif name == "external_zkvm_wide_masked_sequence_length_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["sequence_length"] = 3
    elif name == "external_zkvm_wide_masked_sequence_width_or_masking_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["masking_policy"] = "none"
    elif name == "external_zkvm_wide_masked_sequence_tie_break_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["tie_break"] = "highest_position"
    elif name == "external_zkvm_wide_masked_sequence_intermediate_state_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["selected_positions"][3] = 99
    elif name == "external_zkvm_wide_masked_sequence_metric_source_drift":
        out["external_risc0_wide_masked_sequence_receipt"]["verifier_time_source"] = "carried_from_existing_evidence_not_remeasured"
    elif name == "fake_verifier_time_metric":
        out["metrics"]["verifier_time_ms"] = 7.5
    elif name == "fake_proof_size_metric":
        out["metrics"]["snark_proof_size_bytes"] = 1024
    elif name == "next_go_criteria_weakened":
        out["next_go_criteria"] = ["any zkVM receipt wraps the source-backed contract"]
    elif name == "non_claims_weakened":
        out["non_claims"] = [claim for claim in out["non_claims"] if claim != "not real-valued Softmax"]
    elif name == "claim_boundary_weakened":
        out["claim_boundary"] = "PROOF_BACKED_ATTENTION_KV_RECEIPT"
    elif name == "first_blocker_removed":
        out["first_blocker"] = "NONE"
    elif name == "unknown_field_injection":
        out["unexpected"] = "accepted"
    else:
        raise AttentionKvRouteSelectorError(f"unknown mutation: {name}")
    return out


def run_mutation_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Run every expected mutation and record whether validation rejects it."""

    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvRouteSelectorError as err:
            cases.append({"name": name, "rejected": True, "reason": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "reason": "accepted"})
    return cases


def validate_source_contract(summary: Any) -> None:
    """Validate that the source-backed receipt contract has not drifted."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("source contract must be an object")
    if summary.get("source_schema") != SOURCE.SCHEMA:
        raise AttentionKvRouteSelectorError("source schema drift")
    if summary.get("source_decision") != SOURCE.DECISION:
        raise AttentionKvRouteSelectorError("source decision drift")
    if summary.get("source_proof_status") != "SOURCE_BACKED_RECEIPT_NOT_PROVEN":
        raise AttentionKvRouteSelectorError("source proof status overclaim")
    if summary.get("source_verifier_domain") != "ptvm:zkai:attention-kv-transition:v1":
        raise AttentionKvRouteSelectorError("source verifier-domain drift")
    if summary.get("source_mutations_checked") != len(SOURCE.EXPECTED_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("source mutation count drift")
    if summary.get("source_mutations_rejected") != len(SOURCE.EXPECTED_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("source mutation rejection drift")
    if summary.get("source_all_mutations_rejected") is not True:
        raise AttentionKvRouteSelectorError("source fail-closed drift")
    if tuple(summary.get("required_public_fields", ())) != REQUIRED_PUBLIC_FIELDS:
        raise AttentionKvRouteSelectorError("required public field list drift")
    if tuple(summary.get("present_public_fields", ())) != REQUIRED_PUBLIC_FIELDS:
        raise AttentionKvRouteSelectorError("present public field list drift")
    commitment = summary.get("source_statement_commitment")
    if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
        raise AttentionKvRouteSelectorError("source statement commitment drift")


def validate_routes(routes: Any) -> None:
    """Reject route inventory edits that would silently change the gate question."""

    if routes != route_inventory():
        raise AttentionKvRouteSelectorError("route inventory drift")


def validate_snark_receipt(summary: Any) -> None:
    """Validate the proof-backed external SNARK receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external SNARK receipt must be an object")
    expected = snark_receipt_summary(load_snark_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("external SNARK receipt drift")
    if summary["decision"] != SNARK.DECISION:
        raise AttentionKvRouteSelectorError("external SNARK decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external SNARK result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external SNARK fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external SNARK mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["public_signal_count"] <= 0:
        raise AttentionKvRouteSelectorError("external SNARK proof metric drift")


def validate_risc0_receipt(summary: Any) -> None:
    """Validate the proof-backed RISC Zero semantics receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external RISC Zero receipt must be an object")
    expected = risc0_receipt_summary(load_risc0_payload())
    summary_for_compare = dict(summary)
    expected_for_compare = dict(expected)
    proof_generation_time_source = summary_for_compare.pop("proof_generation_time_source", None)
    expected_for_compare.pop("proof_generation_time_source", None)
    if summary_for_compare != expected_for_compare:
        raise AttentionKvRouteSelectorError("external RISC Zero receipt drift")
    if summary["decision"] != RISC0.DECISION:
        raise AttentionKvRouteSelectorError("external RISC Zero decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external RISC Zero result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external RISC Zero fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external RISC Zero mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["verifier_time_ms"] <= 0:
        raise AttentionKvRouteSelectorError("external RISC Zero proof metric drift")
    if proof_generation_time_source not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRouteSelectorError("external RISC Zero proof-generation metric source drift")
    if summary["verifier_time_source"] != "current_verify_run":
        raise AttentionKvRouteSelectorError("external RISC Zero verifier metric source drift")
    if summary["selected_position"] != 0 or summary["attention_output"] != [2, 1]:
        raise AttentionKvRouteSelectorError("external RISC Zero semantics drift")
    if summary["next_kv_items"] != 3 or len(summary["next_kv_cache"]) != summary["next_kv_items"]:
        raise AttentionKvRouteSelectorError("external RISC Zero KV update drift")


def validate_risc0_sequence_receipt(summary: Any) -> None:
    """Validate the proof-backed RISC Zero carried-sequence receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external RISC Zero sequence receipt must be an object")
    expected = risc0_sequence_receipt_summary(load_risc0_sequence_payload())
    summary_for_compare = dict(summary)
    expected_for_compare = dict(expected)
    proof_generation_time_source = summary_for_compare.pop("proof_generation_time_source", None)
    expected_for_compare.pop("proof_generation_time_source", None)
    if summary_for_compare != expected_for_compare:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence receipt drift")
    if summary["decision"] != RISC0_SEQUENCE.DECISION:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external RISC Zero sequence result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["verifier_time_ms"] <= 0:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence proof metric drift")
    if proof_generation_time_source not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence proof-generation metric source drift")
    if summary["verifier_time_source"] != "current_verify_run":
        raise AttentionKvRouteSelectorError("external RISC Zero sequence verifier metric source drift")
    if summary["sequence_length"] != 3 or summary["transition_rows"] != 3:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence length drift")
    if summary["selected_positions"] != [0, 2, 3]:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence intermediate state drift")
    if summary["attention_outputs"] != [[2, 1], [4, 2], [5, -2]]:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence output drift")
    if summary["final_kv_items"] != 5:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence final KV drift")
    if len(summary["transition_commitments"]) != summary["transition_rows"]:
        raise AttentionKvRouteSelectorError("external RISC Zero sequence transition commitment drift")


def validate_risc0_scaled_sequence_receipt(summary: Any) -> None:
    """Validate the proof-backed RISC Zero scaled carried-sequence receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence receipt must be an object")
    expected = risc0_scaled_sequence_receipt_summary(load_risc0_scaled_sequence_payload())
    summary_for_compare = dict(summary)
    expected_for_compare = dict(expected)
    proof_generation_time_source = summary_for_compare.pop("proof_generation_time_source", None)
    expected_for_compare.pop("proof_generation_time_source", None)
    if summary_for_compare != expected_for_compare:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence receipt drift")
    if summary["decision"] != RISC0_SCALED_SEQUENCE.DECISION:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["verifier_time_ms"] <= 0:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence proof metric drift")
    if proof_generation_time_source not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence proof-generation metric source drift")
    if summary["verifier_time_source"] != "current_verify_run":
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence verifier metric source drift")
    if summary["sequence_length"] != 8 or summary["transition_rows"] != 8:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence length drift")
    if summary["selected_positions"] != [0, 2, 3, 4, 5, 4, 5, 6]:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence intermediate state drift")
    if summary["attention_outputs"] != [[2, 1], [4, 2], [5, -2], [0, 6], [7, 1], [0, 6], [7, 1], [-3, 4]]:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence output drift")
    if summary["final_kv_items"] != 10:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence final KV drift")
    if len(summary["transition_commitments"]) != summary["transition_rows"]:
        raise AttentionKvRouteSelectorError("external RISC Zero scaled sequence transition commitment drift")


def validate_risc0_wide_masked_sequence_receipt(summary: Any) -> None:
    """Validate the proof-backed RISC Zero d=8 causal-prefix sequence receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence receipt must be an object")
    expected = risc0_wide_masked_sequence_receipt_summary(load_risc0_wide_masked_sequence_payload())
    summary_for_compare = dict(summary)
    expected_for_compare = dict(expected)
    proof_generation_time_source = summary_for_compare.pop("proof_generation_time_source", None)
    expected_for_compare.pop("proof_generation_time_source", None)
    if summary_for_compare != expected_for_compare:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence receipt drift")
    if summary["decision"] != RISC0_WIDE_MASKED_SEQUENCE.DECISION:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence result drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence fail-closed drift")
    if summary["mutations_checked"] != summary["mutations_rejected"]:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence mutation rejection drift")
    if summary["proof_size_bytes"] <= 0 or summary["verifier_time_ms"] <= 0:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence proof metric drift")
    if proof_generation_time_source not in {
        "current_prove_run",
        "carried_from_existing_evidence_not_remeasured",
        "not_remeasured_in_verify_existing",
    }:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence proof-generation metric source drift")
    if summary["verifier_time_source"] != "current_verify_run":
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence verifier metric source drift")
    if summary["sequence_length"] != 8 or summary["transition_rows"] != 8:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence length drift")
    if summary["key_width"] != 8 or summary["value_width"] != 8:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence width drift")
    if summary["masking_policy"] != "causal_prefix_position_lte_query_token":
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence masking drift")
    if summary["tie_break"] != "lowest_position":
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence tie-break drift")
    if summary["selected_positions"] != [0, 2, 3, 3, 5, 5, 7, 9]:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence intermediate state drift")
    if summary["attention_outputs"] != [
        [2, 1, 0, -1, 3, 0, 1, 2],
        [4, 2, 1, 0, -1, 3, 2, 1],
        [5, -2, 0, 3, 1, 1, -1, 2],
        [5, -2, 0, 3, 1, 1, -1, 2],
        [7, 1, 2, -2, 0, 5, -3, 1],
        [7, 1, 2, -2, 0, 5, -3, 1],
        [6, 6, -2, 0, 2, 1, 3, -1],
        [-5, 5, 1, -3, 4, 2, -2, 0],
    ]:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence output drift")
    if summary["final_kv_items"] != 10:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence final KV drift")
    if len(summary["transition_commitments"]) != summary["transition_rows"]:
        raise AttentionKvRouteSelectorError("external RISC Zero wide masked sequence transition commitment drift")


def validate_stwo_native_masked_sequence_receipt(summary: Any) -> None:
    """Validate the proof-backed native Stwo d=8 causal-prefix sequence receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("native Stwo masked sequence receipt must be an object")
    expected = stwo_native_masked_sequence_summary(load_stwo_native_masked_sequence_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("native Stwo masked sequence receipt drift")
    if summary["decision"] != LOCAL_STWO_PROOF_DECISION:
        raise AttentionKvRouteSelectorError("native Stwo masked sequence decision drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("native Stwo masked sequence result drift")
    if summary["proof_system"] != "Stwo" or summary["proof_backend"] != "stwo":
        raise AttentionKvRouteSelectorError("native Stwo masked sequence backend drift")
    if summary["proof_size_bytes"] <= 0 or summary["envelope_size_bytes"] <= summary["proof_size_bytes"]:
        raise AttentionKvRouteSelectorError("native Stwo masked sequence proof metric drift")
    if summary["sequence_length"] != 8:
        raise AttentionKvRouteSelectorError("native Stwo masked sequence length drift")
    if summary["score_row_count"] != 52 or summary["trace_row_count"] != 64:
        raise AttentionKvRouteSelectorError("native Stwo masked sequence row-count drift")
    if summary["key_width"] != 8 or summary["value_width"] != 8:
        raise AttentionKvRouteSelectorError("native Stwo masked sequence width drift")
    if summary["masking_policy"] != "causal_prefix_position_lte_query_token":
        raise AttentionKvRouteSelectorError("native Stwo masked sequence masking drift")
    if summary["tie_break"] != "lowest_position":
        raise AttentionKvRouteSelectorError("native Stwo masked sequence tie-break drift")
    if summary["selected_positions"] != [0, 2, 3, 3, 5, 5, 7, 9]:
        raise AttentionKvRouteSelectorError("native Stwo masked sequence selected-position drift")
    if summary["final_kv_items"] != 10:
        raise AttentionKvRouteSelectorError("native Stwo masked sequence final KV drift")
    for key in (
        "statement_commitment",
        "public_instance_commitment",
        "score_row_commitment",
        "final_kv_cache_commitment",
        "outputs_commitment",
    ):
        commitment = summary.get(key)
        if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
            raise AttentionKvRouteSelectorError(f"native Stwo masked sequence {key} drift")


def validate_quantized_softmax_receipt(summary: Any) -> None:
    """Validate the implementation-exact quantized Softmax-table receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("quantized Softmax receipt must be an object")
    expected = quantized_softmax_receipt_summary(load_quantized_softmax_receipt_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("quantized Softmax receipt drift")
    if summary["decision"] != QUANTIZED_SOFTMAX_DECISION:
        raise AttentionKvRouteSelectorError("quantized Softmax decision drift")
    if summary["route_id"] != QUANTIZED_SOFTMAX_ROUTE_ID:
        raise AttentionKvRouteSelectorError("quantized Softmax route drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("quantized Softmax result drift")
    if summary["proof_system"] != "Stwo" or summary["proof_backend"] != "stwo":
        raise AttentionKvRouteSelectorError("quantized Softmax backend drift")
    if summary["kernel_name"] != QUANTIZED_SOFTMAX.KERNEL_NAME:
        raise AttentionKvRouteSelectorError("quantized Softmax kernel-name drift")
    if summary["kernel_status"] != QUANTIZED_SOFTMAX.KERNEL_STATUS:
        raise AttentionKvRouteSelectorError("quantized Softmax kernel-status drift")
    if summary["real_softmax_status"] != QUANTIZED_SOFTMAX.REAL_SOFTMAX_STATUS:
        raise AttentionKvRouteSelectorError("quantized Softmax real-valued overclaim")
    if summary["score_scale"] != 1 or summary["score_gap_clip"] != 8:
        raise AttentionKvRouteSelectorError("quantized Softmax scaling drift")
    if summary["lookup_claims"] != 52 or summary["table_rows"] != 9:
        raise AttentionKvRouteSelectorError("quantized Softmax lookup/table drift")
    if summary["steps"] != 8 or summary["score_rows"] != 52:
        raise AttentionKvRouteSelectorError("quantized Softmax row-count drift")
    if len(summary["per_step_denominators"]) != summary["steps"] or any(
        not isinstance(item, int) or item <= 0 for item in summary["per_step_denominators"]
    ):
        raise AttentionKvRouteSelectorError("quantized Softmax denominator drift")
    if summary["mutations_checked"] != QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("quantized Softmax mutation count drift")
    if summary["mutations_rejected"] != QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("quantized Softmax mutation rejection drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("quantized Softmax fail-closed drift")
    if not isinstance(summary.get("division_error_bound"), str) or "< 1 output unit" not in summary["division_error_bound"]:
        raise AttentionKvRouteSelectorError("quantized Softmax division-bound drift")
    if "no real-valued Softmax" not in summary.get("table_error_bound_policy", ""):
        raise AttentionKvRouteSelectorError("quantized Softmax real-valued error-bound overclaim")
    for key in ("source_statement_commitment", "source_public_instance_commitment", "source_score_row_commitment"):
        commitment = summary.get(key)
        if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
            raise AttentionKvRouteSelectorError(f"quantized Softmax {key} drift")


def validate_multihead_quantized_softmax_receipt(summary: Any) -> None:
    """Validate the multi-head implementation-exact quantized Softmax-table receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax receipt must be an object")
    expected = multihead_quantized_softmax_receipt_summary(load_multihead_quantized_softmax_receipt_payload())
    if summary["decision"] != MULTIHEAD_QUANTIZED_SOFTMAX_DECISION:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax decision drift")
    if summary["route_id"] != MULTIHEAD_QUANTIZED_SOFTMAX_ROUTE_ID:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax route drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax result drift")
    if summary["proof_system"] != "Stwo" or summary["proof_backend"] != "stwo":
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax backend drift")
    if summary["kernel_name"] != MULTIHEAD_QUANTIZED_SOFTMAX.KERNEL_NAME:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax kernel-name drift")
    if summary["kernel_status"] != MULTIHEAD_QUANTIZED_SOFTMAX.KERNEL_STATUS:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax kernel-status drift")
    if summary["real_softmax_status"] != MULTIHEAD_QUANTIZED_SOFTMAX.REAL_SOFTMAX_STATUS:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax real-valued overclaim")
    if summary["score_scale"] != 1 or summary["score_gap_clip"] != 8:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax scaling drift")
    if summary["profiles_checked"] != 4 or summary["head_counts_checked"] != [2, 4, 8, 16]:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax profile/head-count drift")
    if summary["lookup_claims_total"] != 1560 or summary["score_rows_total"] != 1560:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax row-count drift")
    trace_rows_total = summary.get("trace_rows_total")
    if type(trace_rows_total) is not int or trace_rows_total != 1920:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax trace-row-count drift")
    if summary["table_rows"] != 9:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax table drift")
    if summary["fused_proof_size_bytes_sum"] != 227357 or summary["max_fused_proof_size_bytes"] != 65006:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax proof metric drift")
    if summary["mutations_checked"] != MULTIHEAD_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax mutation count drift")
    if summary["mutations_rejected"] != MULTIHEAD_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax mutation rejection drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax fail-closed drift")
    if "input_steps order" not in summary.get("output_order_policy", ""):
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax output-order drift")
    if any("input_steps order" not in policy for policy in summary.get("profile_output_index_policies", [])):
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax per-profile output-order drift")
    if not isinstance(summary.get("division_error_bound"), str) or "< 1 output unit" not in summary["division_error_bound"]:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax division-bound drift")
    if "no real-valued Softmax" not in summary.get("table_error_bound_policy", ""):
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax real-valued error-bound overclaim")
    for key in (
        "profile_statement_commitments",
        "profile_weight_table_commitments",
        "profile_fused_envelope_commitments",
        "profile_fused_proof_commitments",
    ):
        commitments = summary.get(key)
        if not isinstance(commitments, list) or len(commitments) != summary["profiles_checked"]:
            raise AttentionKvRouteSelectorError(f"multi-head quantized Softmax {key} shape drift")
        if any(not isinstance(commitment, str) or not commitment.startswith("blake2b-256:") for commitment in commitments):
            raise AttentionKvRouteSelectorError(f"multi-head quantized Softmax {key} drift")
    if summary != expected:
        raise AttentionKvRouteSelectorError("multi-head quantized Softmax receipt drift")


def validate_longseq_fused_softmax_receipt(summary: Any) -> None:
    """Validate the two-head long-sequence fused Softmax-table route summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax receipt must be an object")
    expected = longseq_fused_softmax_summary(load_longseq_fused_softmax_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax receipt drift")
    if summary["decision"] != LONGSEQ_FUSED_SOFTMAX_DECISION:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax decision drift")
    if summary["route_id"] != LONGSEQ_FUSED_SOFTMAX_ROUTE_ID:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax route drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax result drift")
    if summary["proof_system"] != "Stwo" or summary["proof_backend"] != "stwo":
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax backend drift")
    if summary["source_head_count"] != 2 or summary["sequence_length_per_head"] != 16:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax shape drift")
    if summary["lookup_claims"] != 336 or summary["score_rows"] != 336:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax lookup drift")
    if summary["trace_rows"] != 512 or summary["table_rows"] != 9:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax trace/table drift")
    if summary["source_proof_size_bytes"] != 52366 or summary["fused_proof_size_bytes"] != 60502:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax proof-size drift")
    if summary["fused_envelope_size_bytes"] != 1050248:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax envelope-size drift")
    if summary["source_plus_sidecar_raw_proof_bytes"] != 79444:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax source-plus-sidecar drift")
    if summary["fused_saves_vs_source_plus_sidecar_bytes"] != 18942:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax savings comparator drift")
    if summary["fused_to_source_plus_sidecar_ratio"] != "0.761568":
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax ratio comparator drift")
    if summary["mutations_checked"] != LONGSEQ_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax mutation count drift")
    if summary["mutations_rejected"] != LONGSEQ_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax mutation rejection drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax fail-closed drift")
    for key in (
        "source_statement_commitment",
        "source_public_instance_commitment",
        "source_score_row_commitment",
        "source_final_kv_cache_commitment",
        "source_outputs_commitment",
        "source_weight_table_commitment",
        "fused_envelope_commitment",
        "fused_proof_commitment",
    ):
        commitment = summary.get(key)
        if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
            raise AttentionKvRouteSelectorError(f"long-sequence fused Softmax {key} drift")
    if not isinstance(summary.get("non_claims"), list) or "not a long-context benchmark" not in summary["non_claims"]:
        raise AttentionKvRouteSelectorError("long-sequence fused Softmax non-claim drift")


def validate_d16_fused_softmax_receipt(summary: Any) -> None:
    """Validate the d16 fused Softmax-table route summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("d16 fused Softmax receipt must be an object")
    expected = d16_fused_softmax_summary(load_d16_fused_softmax_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("d16 fused Softmax receipt drift")
    if summary["decision"] != D16_FUSED_SOFTMAX_DECISION:
        raise AttentionKvRouteSelectorError("d16 fused Softmax decision drift")
    if summary["route_id"] != D16_FUSED_SOFTMAX_ROUTE_ID:
        raise AttentionKvRouteSelectorError("d16 fused Softmax route drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("d16 fused Softmax result drift")
    if summary["proof_system"] != "Stwo" or summary["proof_backend"] != "stwo":
        raise AttentionKvRouteSelectorError("d16 fused Softmax backend drift")
    if summary["key_width"] != 16 or summary["value_width"] != 16:
        raise AttentionKvRouteSelectorError("d16 fused Softmax width drift")
    if summary["lookup_claims"] != 52 or summary["score_rows"] != 52:
        raise AttentionKvRouteSelectorError("d16 fused Softmax lookup drift")
    if summary["trace_rows"] != 64 or summary["table_rows"] != 9:
        raise AttentionKvRouteSelectorError("d16 fused Softmax trace/table drift")
    if summary["source_proof_size_bytes"] != 61516 or summary["fused_proof_size_bytes"] != 64503:
        raise AttentionKvRouteSelectorError("d16 fused Softmax proof-size drift")
    if summary["fused_envelope_size_bytes"] != 666515:
        raise AttentionKvRouteSelectorError("d16 fused Softmax envelope-size drift")
    if summary["source_plus_sidecar_raw_proof_bytes"] != 74961:
        raise AttentionKvRouteSelectorError("d16 fused Softmax source-plus-sidecar drift")
    if summary["fused_saves_vs_source_plus_sidecar_bytes"] != 10458:
        raise AttentionKvRouteSelectorError("d16 fused Softmax savings comparator drift")
    if summary["fused_to_source_plus_sidecar_ratio"] != "0.860487":
        raise AttentionKvRouteSelectorError("d16 fused Softmax ratio comparator drift")
    if summary["lookup_relation"] != "AttentionKvD16FusedSoftmaxTableRelation":
        raise AttentionKvRouteSelectorError("d16 fused Softmax lookup relation drift")
    if summary["lookup_relation_width"] != 2:
        raise AttentionKvRouteSelectorError("d16 fused Softmax lookup relation width drift")
    if summary["mutations_checked"] != D16_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("d16 fused Softmax mutation count drift")
    if summary["mutations_rejected"] != D16_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("d16 fused Softmax mutation rejection drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("d16 fused Softmax fail-closed drift")
    for key in (
        "source_statement_commitment",
        "source_public_instance_commitment",
        "source_score_row_commitment",
        "source_weight_table_commitment",
        "fused_envelope_commitment",
        "fused_proof_commitment",
    ):
        commitment = summary.get(key)
        if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
            raise AttentionKvRouteSelectorError(f"d16 fused Softmax {key} drift")
    if not isinstance(summary.get("non_claims"), list) or "not exact Softmax attention" not in summary["non_claims"]:
        raise AttentionKvRouteSelectorError("d16 fused Softmax non-claim drift")


def validate_d16_two_head_fused_softmax_receipt(summary: Any) -> None:
    """Validate the d16 two-head fused Softmax-table route summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax receipt must be an object")
    expected = d16_two_head_fused_softmax_summary(load_d16_two_head_fused_softmax_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax receipt drift")
    if summary["decision"] != D16_TWO_HEAD_FUSED_SOFTMAX_DECISION:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax decision drift")
    if summary["route_id"] != D16_TWO_HEAD_FUSED_SOFTMAX_ROUTE_ID:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax route drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax result drift")
    if summary["proof_system"] != "Stwo" or summary["proof_backend"] != "stwo":
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax backend drift")
    if summary["key_width"] != 16 or summary["value_width"] != 16 or summary["head_count"] != 2:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax width/head drift")
    if summary["lookup_claims"] != 104 or summary["score_rows"] != 104:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax lookup drift")
    if summary["trace_rows"] != 128 or summary["table_rows"] != 9:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax trace/table drift")
    if summary["source_proof_size_bytes"] != 73508 or summary["sidecar_proof_size_bytes"] != 18088:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax source/sidecar proof-size drift")
    if summary["fused_proof_size_bytes"] != 78211:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax proof-size drift")
    if summary["fused_envelope_size_bytes"] != 921008:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax envelope-size drift")
    if summary["source_plus_sidecar_raw_proof_bytes"] != 91596:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax source-plus-sidecar drift")
    if summary["fused_saves_vs_source_plus_sidecar_bytes"] != 13385:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax savings comparator drift")
    if summary["fused_to_source_plus_sidecar_ratio"] != "0.853869":
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax ratio comparator drift")
    if summary["lookup_relation"] != "AttentionKvD16TwoHeadFusedSoftmaxTableRelation":
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax lookup relation drift")
    if summary["lookup_relation_width"] != 2:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax lookup relation width drift")
    if summary["mutations_checked"] != D16_TWO_HEAD_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax mutation count drift")
    if summary["mutations_rejected"] != D16_TWO_HEAD_FUSED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax mutation rejection drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax fail-closed drift")
    for key in (
        "source_statement_commitment",
        "source_public_instance_commitment",
        "source_score_row_commitment",
        "source_final_kv_cache_commitment",
        "source_outputs_commitment",
        "source_weight_table_commitment",
    ):
        commitment = summary.get(key)
        if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
            raise AttentionKvRouteSelectorError(f"d16 two-head fused Softmax {key} drift")
    if not isinstance(summary.get("non_claims"), list) or "not exact Softmax attention" not in summary["non_claims"]:
        raise AttentionKvRouteSelectorError("d16 two-head fused Softmax non-claim drift")


def validate_d16_quantized_softmax_receipt(summary: Any) -> None:
    """Validate the d16 implementation-exact quantized Softmax-table receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("d16 quantized Softmax receipt must be an object")
    expected = d16_quantized_softmax_receipt_summary(load_d16_quantized_softmax_receipt_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax receipt drift")
    if summary["decision"] != D16_QUANTIZED_SOFTMAX_DECISION:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax decision drift")
    if summary["route_id"] != D16_QUANTIZED_SOFTMAX_ROUTE_ID:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax route drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("d16 quantized Softmax result drift")
    if summary["proof_system"] != "Stwo" or summary["proof_backend"] != "stwo":
        raise AttentionKvRouteSelectorError("d16 quantized Softmax backend drift")
    if summary["kernel_name"] != D16_QUANTIZED_SOFTMAX.KERNEL_NAME:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax kernel-name drift")
    if summary["kernel_status"] != D16_QUANTIZED_SOFTMAX.KERNEL_STATUS:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax kernel-status drift")
    if summary["real_softmax_status"] != D16_QUANTIZED_SOFTMAX.REAL_SOFTMAX_STATUS:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax real-valued overclaim")
    if summary["score_scale"] != 1 or summary["score_gap_clip"] != 8:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax scaling drift")
    if summary["key_width"] != 16 or summary["value_width"] != 16 or summary["sequence_length"] != 8:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax width/sequence drift")
    if summary["lookup_claims"] != 52 or summary["table_rows"] != 9:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax lookup/table drift")
    if summary["steps"] != 8 or summary["score_rows"] != 52:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax row-count drift")
    if summary["proof_size_bytes"] != 64503 or summary["envelope_size_bytes"] != 666515:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax proof metric drift")
    if len(summary["per_step_denominators"]) != summary["steps"] or any(
        not isinstance(item, int) or item <= 0 for item in summary["per_step_denominators"]
    ):
        raise AttentionKvRouteSelectorError("d16 quantized Softmax denominator drift")
    if summary["mutations_checked"] != D16_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax mutation count drift")
    if summary["mutations_rejected"] != D16_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax mutation rejection drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax fail-closed drift")
    if not isinstance(summary.get("division_error_bound"), str) or "< 1 output unit" not in summary["division_error_bound"]:
        raise AttentionKvRouteSelectorError("d16 quantized Softmax division-bound drift")
    if "no real-valued Softmax" not in summary.get("table_error_bound_policy", ""):
        raise AttentionKvRouteSelectorError("d16 quantized Softmax real-valued error-bound overclaim")
    for key in (
        "source_statement_commitment",
        "source_public_instance_commitment",
        "source_score_row_commitment",
        "source_outputs_commitment",
        "source_final_kv_cache_commitment",
    ):
        commitment = summary.get(key)
        if not isinstance(commitment, str) or not commitment.startswith("blake2b-256:"):
            raise AttentionKvRouteSelectorError(f"d16 quantized Softmax {key} drift")


def validate_d16_two_head_quantized_softmax_receipt(summary: Any) -> None:
    """Validate the d16 two-head implementation-exact quantized Softmax-table receipt summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax receipt must be an object")
    expected = d16_two_head_quantized_softmax_receipt_summary(
        load_d16_two_head_quantized_softmax_receipt_payload()
    )
    if summary != expected:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax receipt drift")
    if summary["decision"] != D16_TWO_HEAD_QUANTIZED_SOFTMAX_DECISION:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax decision drift")
    if summary["route_id"] != D16_TWO_HEAD_QUANTIZED_SOFTMAX_ROUTE_ID:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax route drift")
    if summary["result"] != "GO":
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax result drift")
    if summary["proof_system"] != "Stwo" or summary["proof_backend"] != "stwo":
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax backend drift")
    if summary["claim_boundary"] != D16_TWO_HEAD_QUANTIZED_SOFTMAX.CLAIM_BOUNDARY:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax claim_boundary drift")
    if summary["fused_gate_decision"] != D16_TWO_HEAD_FUSED_SOFTMAX.DECISION:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax fused_gate_decision drift")
    if summary["kernel_name"] != D16_TWO_HEAD_QUANTIZED_SOFTMAX.KERNEL_NAME:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax kernel-name drift")
    if summary["kernel_status"] != D16_TWO_HEAD_QUANTIZED_SOFTMAX.KERNEL_STATUS:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax kernel-status drift")
    if summary["real_softmax_status"] != D16_TWO_HEAD_QUANTIZED_SOFTMAX.REAL_SOFTMAX_STATUS:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax real-valued overclaim")
    if summary["score_scale"] != 1 or summary["score_gap_clip"] != 8:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax scaling drift")
    if summary["key_width"] != 16 or summary["value_width"] != 16:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax width drift")
    if summary["head_count"] != 2 or summary["sequence_length_per_head"] != 8 or summary["input_steps"] != 16:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax head/sequence drift")
    if summary["lookup_claims"] != 104 or summary["score_rows"] != 104 or summary["trace_rows"] != 128:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax row-count drift")
    if summary["table_rows"] != 9:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax table drift")
    if summary["proof_size_bytes"] != 78211 or summary["envelope_size_bytes"] != 921008:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax proof metric drift")
    expected_kernel_policy_fields = {
        "denominator_policy": "sum_positive_statement_bound_table_weights_per_head_step",
        "division_rule": "output = numerator.div_euclid(denominator); remainder = numerator.rem_euclid(denominator)",
        "rounding_rule": "floor_toward_negative_infinity_via_euclidean_division_positive_denominator",
        "head_binding_policy": "each score row binds head_index; outputs are keyed by (head_index, local_step_index)",
        "step_binding_policy": "each score row binds per-head local step_index derived from statement input_steps order",
        "output_order_policy": (
            "attention_outputs index is derived from statement input_steps order, not from a hard-coded head layout"
        ),
        "causal_mask_policy": "causal_prefix_position_lte_query_token checked on every emitted score row",
        "weight_table_commitment": "blake2b-256:852c06058232d0c0871d2559e57b55c85ab30932cf07ef1814b01143209706f0",
    }
    for key, expected_value in expected_kernel_policy_fields.items():
        if summary.get(key) != expected_value:
            raise AttentionKvRouteSelectorError(f"d16 two-head quantized Softmax {key} drift")
    denominators = summary.get("per_head_step_denominators")
    if not isinstance(denominators, list) or len(denominators) != 16:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax denominator shape drift")
    if any(
        not isinstance(item, dict) or type(item.get("denominator")) is not int or item["denominator"] <= 0
        for item in denominators
    ):
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax denominator drift")
    if summary["mutations_checked"] != D16_TWO_HEAD_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax mutation count drift")
    if summary["mutations_rejected"] != D16_TWO_HEAD_QUANTIZED_SOFTMAX.EXPECTED_MUTATION_COUNT:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax mutation rejection drift")
    if summary["all_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax fail-closed drift")
    if not isinstance(summary.get("division_error_bound"), str) or "< 1 output unit" not in summary["division_error_bound"]:
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax division-bound drift")
    if "no real-valued Softmax" not in summary.get("table_error_bound_policy", ""):
        raise AttentionKvRouteSelectorError("d16 two-head quantized Softmax real-valued error-bound overclaim")
    expected_source_commitment_fields = {
        "source_statement_commitment": "blake2b-256:53ef16ba16ce365697c9f95e87cf1e4ef2a5975d04aebd03dca92792b28a5be8",
        "source_public_instance_commitment": "blake2b-256:5ddd35aa741b465bb91f1ed2129b346839887a56e69ee44ed769fcbe97dea160",
        "source_score_row_commitment": "blake2b-256:da24ff81018d62d7111330ffc71d432b822d88f5383d70bc7a3acb7df2ba6114",
        "source_outputs_commitment": "blake2b-256:3a3a5ce91d1d54a89b2f0236411491085ef2d12012b97e9ac314e617ad7dc30e",
        "source_final_kv_cache_commitment": "blake2b-256:e4c3c24f65bcb5b770a4d81be224317bcecf4b0a46bffb9692440e278a8d81a8",
    }
    for key, expected_value in expected_source_commitment_fields.items():
        if summary.get(key) != expected_value:
            raise AttentionKvRouteSelectorError(f"d16 two-head quantized Softmax {key} drift")


def validate_softmax_edge_corpus(summary: Any) -> None:
    """Validate the d16 denominator/rounding edge-corpus summary."""

    if not isinstance(summary, dict):
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus must be an object")
    expected = softmax_edge_corpus_summary(load_softmax_edge_corpus_payload())
    if summary != expected:
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus drift")
    if summary["decision"] != SOFTMAX_EDGE_CORPUS.DECISION:
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus decision drift")
    if summary["claim_boundary"] != SOFTMAX_EDGE_CORPUS.CLAIM_BOUNDARY:
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus claim boundary drift")
    if summary["edge_case_count"] != len(SOFTMAX_EDGE_CORPUS.EDGE_CASE_NAMES):
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus case-count drift")
    if summary["route_mutations_checked"] != len(SOFTMAX_EDGE_CORPUS.ROUTE_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus mutation-count drift")
    if summary["route_mutations_rejected"] != len(SOFTMAX_EDGE_CORPUS.ROUTE_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus mutation rejection drift")
    if summary["all_route_mutations_rejected"] is not True:
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus fail-closed drift")
    if summary["min_denominator"] != 256 or summary["max_denominator"] != 852:
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus denominator drift")
    if summary["all_scores_equal_denominator"] != 768:
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus equal-score denominator drift")
    if summary["all_clipped_denominator"] != 304 or summary["dominant_denominator"] != 304:
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus clipped denominator drift")
    if "NOT_REAL_VALUED_SOFTMAX" not in summary["claim_boundary"] or "NOT_NEW_PROOF" not in summary["claim_boundary"]:
        raise AttentionKvRouteSelectorError("d16 Softmax edge corpus overclaim drift")


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    """Validate selector shape, commitments, non-claims, and fail-closed cases."""

    if not isinstance(payload, dict):
        raise AttentionKvRouteSelectorError("payload must be an object")
    allowed_keys = {
        "schema",
        "decision",
        "claim_boundary",
        "first_blocker",
        "generated_at",
        "git_commit",
        "question",
        "source_contract",
        "external_snark_receipt",
        "external_risc0_receipt",
        "external_risc0_sequence_receipt",
        "external_risc0_scaled_sequence_receipt",
        "external_risc0_wide_masked_sequence_receipt",
        "native_stwo_masked_sequence_receipt",
        "quantized_softmax_receipt",
        "multihead_quantized_softmax_receipt",
        "longseq_fused_softmax_receipt",
        "d16_fused_softmax_receipt",
        "d16_two_head_fused_softmax_receipt",
        "d16_quantized_softmax_receipt",
        "d16_two_head_quantized_softmax_receipt",
        "softmax_denominator_rounding_edge_corpus",
        "route_candidates",
        "proof_backed_routes_available",
        "metrics",
        "next_go_criteria",
        "non_claims",
        "selector_commitment",
        "mutation_cases",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
    }
    if set(payload) - allowed_keys:
        raise AttentionKvRouteSelectorError("unknown top-level field")
    if payload.get("schema") != SCHEMA:
        raise AttentionKvRouteSelectorError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionKvRouteSelectorError("decision drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionKvRouteSelectorError("claim boundary drift")
    if payload.get("first_blocker") != FIRST_BLOCKER:
        raise AttentionKvRouteSelectorError("first blocker drift")
    validate_source_contract(payload.get("source_contract"))
    validate_snark_receipt(payload.get("external_snark_receipt"))
    validate_risc0_receipt(payload.get("external_risc0_receipt"))
    validate_risc0_sequence_receipt(payload.get("external_risc0_sequence_receipt"))
    validate_risc0_scaled_sequence_receipt(payload.get("external_risc0_scaled_sequence_receipt"))
    validate_risc0_wide_masked_sequence_receipt(payload.get("external_risc0_wide_masked_sequence_receipt"))
    validate_stwo_native_masked_sequence_receipt(payload.get("native_stwo_masked_sequence_receipt"))
    validate_quantized_softmax_receipt(payload.get("quantized_softmax_receipt"))
    validate_multihead_quantized_softmax_receipt(payload.get("multihead_quantized_softmax_receipt"))
    validate_longseq_fused_softmax_receipt(payload.get("longseq_fused_softmax_receipt"))
    validate_d16_fused_softmax_receipt(payload.get("d16_fused_softmax_receipt"))
    validate_d16_two_head_fused_softmax_receipt(payload.get("d16_two_head_fused_softmax_receipt"))
    validate_d16_quantized_softmax_receipt(payload.get("d16_quantized_softmax_receipt"))
    validate_d16_two_head_quantized_softmax_receipt(payload.get("d16_two_head_quantized_softmax_receipt"))
    validate_softmax_edge_corpus(payload.get("softmax_denominator_rounding_edge_corpus"))
    validate_routes(payload.get("route_candidates"))
    if tuple(payload.get("proof_backed_routes_available") or ()) != EXPECTED_PROOF_BACKED_ROUTES_AVAILABLE:
        raise AttentionKvRouteSelectorError("proof-backed route relabeling")
    expected_metrics = {
        "native_stwo_proof_size_bytes": payload["native_stwo_masked_sequence_receipt"]["proof_size_bytes"],
        "native_stwo_envelope_size_bytes": payload["native_stwo_masked_sequence_receipt"]["envelope_size_bytes"],
        "native_stwo_score_row_count": payload["native_stwo_masked_sequence_receipt"]["score_row_count"],
        "native_stwo_trace_row_count": payload["native_stwo_masked_sequence_receipt"]["trace_row_count"],
        "quantized_softmax_proof_size_bytes": payload["quantized_softmax_receipt"]["proof_size_bytes"],
        "quantized_softmax_envelope_size_bytes": payload["quantized_softmax_receipt"]["envelope_size_bytes"],
        "quantized_softmax_lookup_claims": payload["quantized_softmax_receipt"]["lookup_claims"],
        "quantized_softmax_table_rows": payload["quantized_softmax_receipt"]["table_rows"],
        "quantized_softmax_max_observed_division_error_fraction": (
            payload["quantized_softmax_receipt"]["max_observed_division_error_fraction"]
        ),
        "multihead_quantized_softmax_fused_proof_size_bytes_sum": (
            payload["multihead_quantized_softmax_receipt"]["fused_proof_size_bytes_sum"]
        ),
        "multihead_quantized_softmax_max_fused_proof_size_bytes": (
            payload["multihead_quantized_softmax_receipt"]["max_fused_proof_size_bytes"]
        ),
        "multihead_quantized_softmax_lookup_claims_total": (
            payload["multihead_quantized_softmax_receipt"]["lookup_claims_total"]
        ),
        "multihead_quantized_softmax_trace_rows_total": (
            payload["multihead_quantized_softmax_receipt"].get("trace_rows_total")
        ),
        "multihead_quantized_softmax_profiles_checked": (
            payload["multihead_quantized_softmax_receipt"]["profiles_checked"]
        ),
        "multihead_quantized_softmax_head_counts_checked": (
            payload["multihead_quantized_softmax_receipt"]["head_counts_checked"]
        ),
        "multihead_quantized_softmax_max_observed_division_error_fraction": (
            payload["multihead_quantized_softmax_receipt"]["max_observed_division_error_fraction"]
        ),
        "longseq_fused_softmax_lookup_claims": payload["longseq_fused_softmax_receipt"]["lookup_claims"],
        "longseq_fused_softmax_trace_rows": payload["longseq_fused_softmax_receipt"]["trace_rows"],
        "longseq_fused_softmax_fused_proof_size_bytes": (
            payload["longseq_fused_softmax_receipt"]["fused_proof_size_bytes"]
        ),
        "longseq_fused_softmax_fused_envelope_size_bytes": (
            payload["longseq_fused_softmax_receipt"]["fused_envelope_size_bytes"]
        ),
        "longseq_fused_softmax_source_plus_sidecar_raw_proof_bytes": (
            payload["longseq_fused_softmax_receipt"]["source_plus_sidecar_raw_proof_bytes"]
        ),
        "longseq_fused_softmax_fused_saves_vs_source_plus_sidecar_bytes": (
            payload["longseq_fused_softmax_receipt"]["fused_saves_vs_source_plus_sidecar_bytes"]
        ),
        "longseq_fused_softmax_fused_to_source_plus_sidecar_ratio": (
            payload["longseq_fused_softmax_receipt"]["fused_to_source_plus_sidecar_ratio"]
        ),
        "d16_fused_softmax_lookup_claims": payload["d16_fused_softmax_receipt"]["lookup_claims"],
        "d16_fused_softmax_trace_rows": payload["d16_fused_softmax_receipt"]["trace_rows"],
        "d16_fused_softmax_key_width": payload["d16_fused_softmax_receipt"]["key_width"],
        "d16_fused_softmax_value_width": payload["d16_fused_softmax_receipt"]["value_width"],
        "d16_fused_softmax_fused_proof_size_bytes": (
            payload["d16_fused_softmax_receipt"]["fused_proof_size_bytes"]
        ),
        "d16_fused_softmax_fused_envelope_size_bytes": (
            payload["d16_fused_softmax_receipt"]["fused_envelope_size_bytes"]
        ),
        "d16_fused_softmax_source_plus_sidecar_raw_proof_bytes": (
            payload["d16_fused_softmax_receipt"]["source_plus_sidecar_raw_proof_bytes"]
        ),
        "d16_fused_softmax_fused_saves_vs_source_plus_sidecar_bytes": (
            payload["d16_fused_softmax_receipt"]["fused_saves_vs_source_plus_sidecar_bytes"]
        ),
        "d16_fused_softmax_fused_to_source_plus_sidecar_ratio": (
            payload["d16_fused_softmax_receipt"]["fused_to_source_plus_sidecar_ratio"]
        ),
        "d16_two_head_fused_softmax_lookup_claims": payload["d16_two_head_fused_softmax_receipt"][
            "lookup_claims"
        ],
        "d16_two_head_fused_softmax_trace_rows": payload["d16_two_head_fused_softmax_receipt"]["trace_rows"],
        "d16_two_head_fused_softmax_key_width": payload["d16_two_head_fused_softmax_receipt"]["key_width"],
        "d16_two_head_fused_softmax_value_width": payload["d16_two_head_fused_softmax_receipt"]["value_width"],
        "d16_two_head_fused_softmax_head_count": payload["d16_two_head_fused_softmax_receipt"]["head_count"],
        "d16_two_head_fused_softmax_fused_proof_size_bytes": (
            payload["d16_two_head_fused_softmax_receipt"]["fused_proof_size_bytes"]
        ),
        "d16_two_head_fused_softmax_fused_envelope_size_bytes": (
            payload["d16_two_head_fused_softmax_receipt"]["fused_envelope_size_bytes"]
        ),
        "d16_two_head_fused_softmax_source_plus_sidecar_raw_proof_bytes": (
            payload["d16_two_head_fused_softmax_receipt"]["source_plus_sidecar_raw_proof_bytes"]
        ),
        "d16_two_head_fused_softmax_fused_saves_vs_source_plus_sidecar_bytes": (
            payload["d16_two_head_fused_softmax_receipt"]["fused_saves_vs_source_plus_sidecar_bytes"]
        ),
        "d16_two_head_fused_softmax_fused_to_source_plus_sidecar_ratio": (
            payload["d16_two_head_fused_softmax_receipt"]["fused_to_source_plus_sidecar_ratio"]
        ),
        "d16_quantized_softmax_proof_size_bytes": payload["d16_quantized_softmax_receipt"]["proof_size_bytes"],
        "d16_quantized_softmax_envelope_size_bytes": payload["d16_quantized_softmax_receipt"]["envelope_size_bytes"],
        "d16_quantized_softmax_lookup_claims": payload["d16_quantized_softmax_receipt"]["lookup_claims"],
        "d16_quantized_softmax_table_rows": payload["d16_quantized_softmax_receipt"]["table_rows"],
        "d16_quantized_softmax_key_width": payload["d16_quantized_softmax_receipt"]["key_width"],
        "d16_quantized_softmax_value_width": payload["d16_quantized_softmax_receipt"]["value_width"],
        "d16_quantized_softmax_sequence_length": payload["d16_quantized_softmax_receipt"]["sequence_length"],
        "d16_quantized_softmax_max_observed_division_error_fraction": (
            payload["d16_quantized_softmax_receipt"]["max_observed_division_error_fraction"]
        ),
        "d16_two_head_quantized_softmax_proof_size_bytes": (
            payload["d16_two_head_quantized_softmax_receipt"]["proof_size_bytes"]
        ),
        "d16_two_head_quantized_softmax_envelope_size_bytes": (
            payload["d16_two_head_quantized_softmax_receipt"]["envelope_size_bytes"]
        ),
        "d16_two_head_quantized_softmax_lookup_claims": (
            payload["d16_two_head_quantized_softmax_receipt"]["lookup_claims"]
        ),
        "d16_two_head_quantized_softmax_table_rows": (
            payload["d16_two_head_quantized_softmax_receipt"]["table_rows"]
        ),
        "d16_two_head_quantized_softmax_key_width": (
            payload["d16_two_head_quantized_softmax_receipt"]["key_width"]
        ),
        "d16_two_head_quantized_softmax_value_width": (
            payload["d16_two_head_quantized_softmax_receipt"]["value_width"]
        ),
        "d16_two_head_quantized_softmax_head_count": (
            payload["d16_two_head_quantized_softmax_receipt"]["head_count"]
        ),
        "d16_two_head_quantized_softmax_sequence_length_per_head": (
            payload["d16_two_head_quantized_softmax_receipt"]["sequence_length_per_head"]
        ),
        "d16_two_head_quantized_softmax_input_steps": (
            payload["d16_two_head_quantized_softmax_receipt"]["input_steps"]
        ),
        "d16_two_head_quantized_softmax_max_observed_division_error_fraction": (
            payload["d16_two_head_quantized_softmax_receipt"]["max_observed_division_error_fraction"]
        ),
        "d16_softmax_edge_case_count": payload["softmax_denominator_rounding_edge_corpus"]["edge_case_count"],
        "d16_softmax_edge_route_mutations_checked": (
            payload["softmax_denominator_rounding_edge_corpus"]["route_mutations_checked"]
        ),
        "d16_softmax_edge_route_mutations_rejected": (
            payload["softmax_denominator_rounding_edge_corpus"]["route_mutations_rejected"]
        ),
        "d16_softmax_edge_min_denominator": payload["softmax_denominator_rounding_edge_corpus"]["min_denominator"],
        "d16_softmax_edge_max_denominator": payload["softmax_denominator_rounding_edge_corpus"]["max_denominator"],
        "d16_softmax_edge_max_remainder_ratio": (
            payload["softmax_denominator_rounding_edge_corpus"]["max_remainder_ratio"]
        ),
        "snark_proof_size_bytes": payload["external_snark_receipt"]["proof_size_bytes"],
        "snark_public_signal_count": payload["external_snark_receipt"]["public_signal_count"],
        "risc0_receipt_size_bytes": payload["external_risc0_receipt"]["proof_size_bytes"],
        "risc0_verifier_time_ms": payload["external_risc0_receipt"]["verifier_time_ms"],
        "risc0_verifier_time_source": payload["external_risc0_receipt"]["verifier_time_source"],
        "risc0_sequence_receipt_size_bytes": payload["external_risc0_sequence_receipt"]["proof_size_bytes"],
        "risc0_sequence_verifier_time_ms": payload["external_risc0_sequence_receipt"]["verifier_time_ms"],
        "risc0_sequence_verifier_time_source": payload["external_risc0_sequence_receipt"]["verifier_time_source"],
        "risc0_scaled_sequence_receipt_size_bytes": payload["external_risc0_scaled_sequence_receipt"]["proof_size_bytes"],
        "risc0_scaled_sequence_verifier_time_ms": payload["external_risc0_scaled_sequence_receipt"]["verifier_time_ms"],
        "risc0_scaled_sequence_verifier_time_source": payload["external_risc0_scaled_sequence_receipt"]["verifier_time_source"],
        "risc0_wide_masked_sequence_receipt_size_bytes": payload["external_risc0_wide_masked_sequence_receipt"]["proof_size_bytes"],
        "risc0_wide_masked_sequence_verifier_time_ms": payload["external_risc0_wide_masked_sequence_receipt"]["verifier_time_ms"],
        "risc0_wide_masked_sequence_verifier_time_source": payload["external_risc0_wide_masked_sequence_receipt"]["verifier_time_source"],
        "proof_generation_time_ms": None,
        "verifier_time_ms": None,
        "timing_policy": payload["external_snark_receipt"]["timing_policy"],
        "risc0_timing_policy": payload["external_risc0_receipt"]["timing_policy"],
    }
    if payload.get("metrics") != expected_metrics:
        raise AttentionKvRouteSelectorError("metric smuggling")
    next_go_criteria = payload.get("next_go_criteria")
    if not isinstance(next_go_criteria, list) or any(not isinstance(item, str) for item in next_go_criteria):
        raise AttentionKvRouteSelectorError("next-go criteria drift")
    if tuple(next_go_criteria) != EXPECTED_NEXT_GO_CRITERIA:
        raise AttentionKvRouteSelectorError("next-go criteria drift")
    non_claims = payload.get("non_claims")
    if tuple(non_claims or ()) != EXPECTED_NON_CLAIMS:
        raise AttentionKvRouteSelectorError("non-claim drift")
    expected_commitment = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "source_contract": payload["source_contract"],
            "external_snark_receipt": payload["external_snark_receipt"],
            "external_risc0_receipt": payload["external_risc0_receipt"],
            "external_risc0_sequence_receipt": payload["external_risc0_sequence_receipt"],
            "external_risc0_scaled_sequence_receipt": payload["external_risc0_scaled_sequence_receipt"],
            "external_risc0_wide_masked_sequence_receipt": payload["external_risc0_wide_masked_sequence_receipt"],
            "native_stwo_masked_sequence_receipt": payload["native_stwo_masked_sequence_receipt"],
            "quantized_softmax_receipt": payload["quantized_softmax_receipt"],
            "multihead_quantized_softmax_receipt": payload["multihead_quantized_softmax_receipt"],
            "longseq_fused_softmax_receipt": payload["longseq_fused_softmax_receipt"],
            "d16_fused_softmax_receipt": payload["d16_fused_softmax_receipt"],
            "d16_two_head_fused_softmax_receipt": payload["d16_two_head_fused_softmax_receipt"],
            "d16_quantized_softmax_receipt": payload["d16_quantized_softmax_receipt"],
            "d16_two_head_quantized_softmax_receipt": payload["d16_two_head_quantized_softmax_receipt"],
            "softmax_denominator_rounding_edge_corpus": payload["softmax_denominator_rounding_edge_corpus"],
            "route_candidates": payload["route_candidates"],
            "proof_backed_routes_available": payload["proof_backed_routes_available"],
            "metrics": payload["metrics"],
            "next_go_criteria": payload["next_go_criteria"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-proof-route-selector:v1",
    )
    if payload.get("selector_commitment") != expected_commitment:
        raise AttentionKvRouteSelectorError("selector commitment drift")
    if allow_missing_mutation_summary:
        return
    mutation_cases = payload.get("mutation_cases")
    if not isinstance(mutation_cases, list):
        raise AttentionKvRouteSelectorError("mutation cases must be a list")
    if tuple(item.get("name") for item in mutation_cases) != EXPECTED_MUTATION_NAMES:
        raise AttentionKvRouteSelectorError("mutation case names drift")
    if any(item.get("rejected") is not True for item in mutation_cases):
        raise AttentionKvRouteSelectorError("mutation rejection drift")
    if payload.get("mutations_checked") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("mutation count drift")
    if payload.get("mutations_rejected") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvRouteSelectorError("mutation rejection count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvRouteSelectorError("fail-closed summary drift")


def to_tsv(payload: dict[str, Any]) -> str:
    """Render the selector result as a stable one-row TSV summary."""

    rows: list[str] = []
    writer = csv.DictWriter(_ListWriter(rows), fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "decision": payload["decision"],
            "first_blocker": payload["first_blocker"],
            "source_contract_decision": payload["source_contract"]["source_decision"],
            "source_contract_proof_status": payload["source_contract"]["source_proof_status"],
            "proof_backed_routes_available": len(payload["proof_backed_routes_available"]),
            "routes_checked": len(payload["route_candidates"]),
            "mutations_checked": payload["mutations_checked"],
            "mutations_rejected": payload["mutations_rejected"],
            "source_statement_commitment": payload["source_contract"]["source_statement_commitment"],
        }
    )
    return "".join(rows)


class _ListWriter:
    def __init__(self, rows: list[str]) -> None:
        """Create a minimal file-like adapter for csv.DictWriter."""

        self.rows = rows

    def write(self, value: str) -> int:
        """Append one CSV chunk and report the written byte count."""

        self.rows.append(value)
        return len(value)


def write_outputs(payload: dict[str, Any], json_out: pathlib.Path, tsv_out: pathlib.Path) -> None:
    """Validate and write the JSON/TSV evidence artifacts."""

    validate_payload(payload)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    tsv_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tsv_out.write_text(to_tsv(payload), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command-line flags for stdout and checked-in evidence output."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--run-native",
        action="store_true",
        help="run native proof verification for proof-backed quantized Softmax receipt routes",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""

    args = parse_args()
    payload = build_payload(run_native=args.run_native)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.no_write:
        write_outputs(payload, args.write_json, args.write_tsv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
