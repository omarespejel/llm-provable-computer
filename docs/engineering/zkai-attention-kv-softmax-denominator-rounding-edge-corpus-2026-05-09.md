# zkAI Attention/KV Softmax Denominator/Rounding Edge Corpus - 2026-05-09

## Question

Can the d16 implementation-exact quantized Softmax-table receipt survive
adversarial denominator and floor-division edge cases without widening the claim
into real-valued Softmax or a new proof result?

## Result

GO, as correctness hardening.

Issue `#507` adds a deterministic edge corpus for the bounded integer
Softmax-table kernel used by the d16 fused native Stwo receipt. The gate checks
the arithmetic contract directly:

- statement-bound table lookup with clipped score gaps;
- strictly positive denominators;
- weighted numerator recomputation;
- Euclidean floor division with nonnegative remainders;
- `0 <= remainder < denominator` for every output coordinate;
- route-level rejection of denominator/remainder drift through source, LogUp
  sidecar, and fused receipt validators.

This is not a new proof object. It is not real-valued `exp` / division Softmax.
It is not model-accuracy evidence and not a benchmark.

## Checked Corpus

| Edge case | Denominator | Relevant behavior |
| --- | ---: | --- |
| `single_allowed_candidate_min_denominator` | `256` | minimum one-candidate positive denominator |
| `all_scores_equal` | `768` | three equal maximum-score candidates, all weight `256` |
| `all_nonmax_scores_clipped` | `304` | one max candidate plus three clipped-gap candidates |
| `one_dominant_key_all_others_clipped` | `304` | dominant key with all nonmax scores clipped |
| `negative_numerator_floor_division` | `768` | negative weighted numerator under positive denominator |
| `mixed_remainder_extremes` | `517` | mixed signs and nonzero remainders |
| `table_entry_multiplicity_extremes` | `852` | every table gap `0..8` appears at least once |

The observed denominator range is `256..852`. The largest checked remainder
ratio is `0.842105`, still strictly below one denominator as required by the
Euclidean remainder contract.

## Validator Hardening

The interesting implementation finding was an API-boundary issue, not a
generated-artifact issue.

Normal route construction already validates the generated source artifacts.
However, the standalone d16 sidecar and fused validators previously trusted the
caller-provided `source_input` after only checking that the envelope embedded the
same object. A caller could therefore present a matching malformed
source/envelope pair to the validator API and bypass the source-input arithmetic
checks at that boundary.

This PR hardens that boundary:

- `scripts/zkai_attention_kv_d16_air_private_softmax_table_lookup_gate.py`
  now calls `validate_source_input(source_input)` inside
  `validate_lookup_envelope`.
- `scripts/zkai_attention_kv_d16_fused_softmax_table_native_gate.py` now calls
  the source-input module's `validate_payload(source_input)` inside
  `validate_fused_envelope`.

The new regression tests mutate denominator and remainder fields in a matching
source/envelope pair and require rejection through direct source-input
validation before the paired malformed artifact is accepted.

## Route Mutations

The edge-corpus gate checks and rejects `9 / 9` route mutations:

| Mutation | Route | Result |
| --- | --- | --- |
| `source_denominator_zero` | source | rejected |
| `source_remainder_equal_denominator` | source | rejected |
| `source_negative_remainder` | source | rejected |
| `sidecar_matching_source_denominator_zero` | sidecar | rejected |
| `sidecar_matching_source_remainder_equal_denominator` | sidecar | rejected |
| `sidecar_matching_source_negative_remainder` | sidecar | rejected |
| `fused_matching_source_denominator_zero` | fused | rejected |
| `fused_matching_source_remainder_equal_denominator` | fused | rejected |
| `fused_matching_source_negative_remainder` | fused | rejected |

## Claim Boundary

This result supports the statement:

> The checked d16 quantized Softmax-table receipt has deterministic
> denominator and floor-division edge coverage, and source/sidecar/fused route
> validators reject denominator/remainder drift even when the malformed source
> and envelope are paired consistently.

It does not support:

- real-valued Softmax;
- an approximation error bound against real Softmax;
- implementation-exact model Softmax;
- full inference;
- long-context inference;
- public benchmark comparisons;
- recursion or PCD.

## Evidence

- Edge corpus JSON:
  `docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json`
- Edge corpus TSV:
  `docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.tsv`
- Edge corpus gate:
  `scripts/zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate.py`
- Edge corpus tests:
  `scripts/tests/test_zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate.py`
- Sidecar regression tests:
  `scripts/tests/test_zkai_attention_kv_d16_air_private_softmax_table_lookup_gate.py`
- Fused regression tests:
  `scripts/tests/test_zkai_attention_kv_d16_fused_softmax_table_native_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate \
  scripts.tests.test_zkai_attention_kv_d16_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_d16_fused_softmax_table_native_gate

python3 scripts/zkai_attention_kv_d16_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv

just gate-fast
just gate
```
