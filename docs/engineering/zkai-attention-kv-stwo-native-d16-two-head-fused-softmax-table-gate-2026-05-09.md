# zkAI Attention/KV d16 Two-Head Fused Softmax-Table Gate - 2026-05-09

## Question

Can the native Stwo attention/KV route combine two stress axes at once: width
`d=16` and two attention heads, while fusing bounded Softmax-table attention
arithmetic with LogUp table membership in one proof object?

## Result

GO, with a deliberately bounded claim.

The checked fused artifact proves the `d16`, two-head, eight-step-per-head
bounded Softmax-table attention fixture in one native Stwo proof object. It
binds the same source statement used by the arithmetic source proof, carries the
same public table commitment, and checks LogUp membership in the fused proof.

Machine-readable evidence:

- source input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.json`
- source proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.envelope.json`
- LogUp sidecar proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- fused proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-proof-2026-05.envelope.json`
- fused gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-gate-2026-05.json`
- fused gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-gate-2026-05.tsv`

## Checked Metrics

| metric | value |
|---|---:|
| key/value width | `16` |
| heads | `2` |
| steps per head | `8` |
| lookup claims / score rows | `104` |
| trace rows | `128` |
| Softmax-table rows | `9` |
| source proof bytes | `73,508` |
| LogUp sidecar proof bytes | `18,088` |
| source+sidecar proof bytes | `91,596` |
| fused proof bytes | `78,211` |
| fused overhead over source proof | `4,703` |
| fused saving vs source+sidecar | `13,385` |
| fused/source+sidecar ratio | `0.853869` |

The fused gate rejects `30 / 30` mutations, including statement relabeling,
weight-table relabeling, score-row commitment drift, source-input split-brain
drift, table-multiplicity drift, proof-byte tampering, source/sidecar proof
injection, and exact-Softmax overclaim edits.

## Why This Matters

Earlier fused Softmax-table evidence checked width, head count, and sequence
length mostly one axis at a time. This result combines width and head count in
one native Stwo proof object:

- compared with `d16` single-head, lookup claims and trace rows double, while
  fused proof bytes grow `1.212517x`;
- compared with `d8` two-head, lookup claims and trace rows stay fixed, while
  widening to `d16` grows fused proof bytes `1.579765x`;
- compared with the matched non-fused source+sidecar route, the fused proof is
  `13,385` bytes smaller.

This is evidence that the transformer-shaped route is not only a sequence or
head-count toy. It can carry a wider per-token vector and multiple heads inside
one statement-bound native Stwo proof object.

## Claim Boundary

This is not:

- exact real-valued Softmax;
- implementation-exact model Softmax;
- full autoregressive inference;
- a long-context benchmark;
- public timing evidence;
- recursion or PCD;
- on-chain verification evidence.

The proved kernel is a bounded integer Softmax-table approximation with clipped
score gaps, floor division, quotient/remainder checks, and statement-bound table
commitments.

## Validation

Regenerate source, sidecar, fused, and gate artifacts:

```bash
python3 scripts/zkai_attention_kv_stwo_native_d16_two_head_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_two_head_bounded_softmax_table_proof \
  -- prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_two_head_softmax_table_lookup_proof \
  -- prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_two_head_fused_softmax_table_proof \
  -- prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d16_two_head_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-gate-2026-05.tsv
```

Focused tests:

```bash
python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_d16_two_head_bounded_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_d16_two_head_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_d16_two_head_fused_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_fused_softmax_table_route_matrix_gate
```
