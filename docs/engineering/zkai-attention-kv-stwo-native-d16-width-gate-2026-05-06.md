# zkAI Attention/KV Native Stwo d16 Width Gate - 2026-05-06

## Question

Can the native Stwo attention/KV proof from issues `#448` and `#450` scale by
width while preserving the same statement-binding and mutation-rejection
discipline?

## Result

GO for width scaling.

The checked artifact keeps the same intentionally narrow arithmetic surface:

- single-head attention,
- integer-argmax attention,
- causal-prefix masking,
- lowest-position tie break,
- public score rows,
- verifier-recomputed append-only KV carry,
- statement-bound prior/input/output/final-state commitments.

It doubles key/value width from `d=8` to `d=16` while holding sequence length,
score-row count, and trace-row count fixed. This is a width-axis result. It is
not a sequence-length result, not Softmax, not multi-head attention, not full
inference, and not recursion or PCD.

## Evidence

- d16 input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json`
- d16 input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.tsv`
- d16 proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json`
- d16 width gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-width-gate-2026-05.json`
- d16 width gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-width-gate-2026-05.tsv`
- d16 input generator: `scripts/zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input.py`
- d16 width gate: `scripts/zkai_attention_kv_d16_native_width_gate.py`
- Shared native proof verifier: `src/stwo_backend/attention_kv_native_masked_sequence_proof.rs`

## Checked Surface

| Field | d8 baseline | d16 scaled proof |
| --- | ---: | ---: |
| Sequence length | `8` | `8` |
| Key width | `8` | `16` |
| Value width | `8` | `16` |
| Initial KV rows | `2` | `2` |
| Final KV rows | `10` | `10` |
| Score rows | `52` | `52` |
| Trace rows | `64` | `64` |
| Proof size | `24394` bytes | `31621` bytes |
| Envelope size | `265791` bytes | `358124` bytes |
| Mutation cases rejected | route selector `42 / 42` | width gate `16 / 16` |

The selected positions change under the wider vectors:

```text
[1, 1, 3, 1, 5, 3, 1, 3]
```

That matters because the d16 artifact is not a relabeled d8 proof with wider
metadata. The public score rows, selected output rows, final KV commitment, and
statement commitment are all recomputed for the wider vector fixture.

## Commitments

| Commitment | Value |
| --- | --- |
| Statement | `blake2b-256:9ca216aefb582e0877d46deacf4af936bf61aa3f6c7865b22675d7698ffc3cd6` |
| Public instance | `blake2b-256:bd7415e074c0699ced0c774f987b6eceae9ca5607cc6df0e0714723db3aa8551` |
| Score rows | `blake2b-256:8973b8fdcbf26b031b38491ff405cf93f40aee9eeaa2fc0b6bdbe31b960ac855` |
| Final KV cache | `blake2b-256:90b89f3256f1c080b60e06abfeb81ba4a68bfee6cd9ef49ed604cb4898ec774d` |
| Outputs | `blake2b-256:c62aac346e84ef24b5bd1618e6e17a5cf86bf8f4185fc01e6f393da0ff085e47` |

Single local engineering observations from the proof CLI:

| Command | Prove time | Verify time |
| --- | ---: | ---: |
| `prove ...d16...json ...d16...envelope.json` | `59.833750 ms` | `33.492041 ms` |
| `verify ...d16...envelope.json` | n/a | `39.157917 ms` |

These timings are single local engineering observations, not benchmark medians
and not publication-grade comparisons.

## Why This Matters

The issue `#450` result scaled sequence length. This result scales a different
transformer axis: vector width. Holding sequence length fixed while doubling
key/value width gives a cleaner test of whether the native AIR is tied to one
small vector layout.

The answer is now no for this narrow surface: the same native Stwo proof route
accepts a `d=16` statement-bound carried-state attention/KV fixture and rejects
width, route, commitment, metric, non-claim, and parser mutations.

This is directly useful for the STARK-transformer paper because it supports the
claim that transformer decode state can be organized as trace-shaped native STARK
work, not only as external SNARK/zkVM adapters.

## Non-Claims

- This is not Softmax.
- This is not multi-head attention.
- This is not sequence-length scaling beyond the existing seq16 result.
- This is not long-context inference.
- This is not a full transformer block.
- This is not private-witness privacy; score rows are public.
- This is not recursion or proof-carrying data.
- This is not a public benchmark row.

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d16_native_width_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-width-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-width-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input \
  scripts.tests.test_zkai_attention_kv_d16_native_width_gate

cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof \
  --lib --features stwo-backend
```

## Next GO/NO-GO Targets

Do not jump to full inference. The next useful native STARK axes are:

1. two-head fixed sequence with explicit head identity and per-head commitments;
2. bounded Softmax-like approximation only with a statement-bound numeric policy;
3. composition with the native RMSNorm/block receipt commitments.
