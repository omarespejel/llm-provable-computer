# zkAI Attention/KV Softmax Paired-Source Validation Audit

Date: 2026-05-09  
Issue: #510  
Result: GO for paired-source validator API hardening

## Question

Can a caller pass a malformed Softmax-table source input and a matching malformed
proof envelope to a standalone sidecar or fused validator, bypassing checks that
are only applied during artifact construction?

This is a validator API hardening question. It is not a new proof result,
benchmark, real-valued Softmax claim, or model-accuracy claim.

## Finding

The audit reproduced a real paired-source boundary gap in older d8/two-head/
four-head and long-sequence sidecar/fused validator APIs: if the caller mutated
`score_rows[0].output_remainder[0]` and mirrored that same malformed source into
the envelope, several validators accepted because they only checked that the two
copies matched.

The fix is direct source-input validation at the standalone validator boundary.
After the patch, the checked audit gate rejects the same paired malformed object
across all inspected targets.

## Checked Targets

| Target | Route | Result |
| --- | --- | --- |
| `d8_sidecar` | sidecar | rejected |
| `two_head_sidecar` | sidecar | rejected |
| `four_head_sidecar` | sidecar | rejected |
| `two_head_longseq_sidecar` | sidecar | rejected |
| `d16_sidecar` | sidecar | rejected |
| `d8_fused` | fused | rejected |
| `two_head_fused` | fused | rejected |
| `four_head_fused` | fused | rejected |
| `eight_head_fused` | fused | rejected |
| `two_head_longseq_fused` | fused | rejected |
| `d16_fused` | fused | rejected |

Summary: `11 / 11` checked targets reject the paired malformed source/envelope
mutation.

## Evidence

Machine-readable evidence:

- `docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.tsv`

The mutation is deterministic:

```text
score_rows[0].output_remainder[0] += 1
```

The mutation is intentionally mirrored into both the caller-provided source input
and the envelope's `source_input` field. The gate therefore checks the API
boundary directly instead of only checking split-brain mismatch.

## Validation Commands

```bash
python3 scripts/zkai_attention_kv_softmax_paired_source_validation_audit_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_kv_softmax_paired_source_validation_audit_gate
just gate-fast
just gate
```

## Claim Boundary

This result strengthens the bounded Softmax-table track by closing a validator
API class that could otherwise make evidence look stronger than the standalone
acceptance logic actually was. It does not change the core claim boundary:
bounded integer Softmax-table receipts are checked; exact real-valued Softmax,
full inference, privacy, recursion/PCD, and public benchmark claims remain out of
scope.
