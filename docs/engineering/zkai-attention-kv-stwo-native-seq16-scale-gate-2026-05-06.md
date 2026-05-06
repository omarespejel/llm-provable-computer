# zkAI Attention/KV Native Stwo Seq16 Scale Gate - 2026-05-06

## Question

Can the native Stwo attention/KV proof from issue `#448` scale by one real
transformer axis while preserving the same statement-binding and mutation-rejection
discipline?

## Result

GO for sequence-length scaling.

The checked artifact keeps the same intentionally narrow arithmetic surface:

- single-head `d=8` key/value width,
- integer-argmax attention,
- causal-prefix masking,
- lowest-position tie break,
- public score rows,
- verifier-recomputed append-only KV carry,
- statement-bound prior/input/output/final-state commitments.

It scales the native Stwo proof from the issue `#448` eight-step sequence to a
sixteen-step sequence. This is not a `d=16` width result and not a Softmax result.
It is a sequence-length scaling result for the native STARK attention/KV surface.

## Evidence

- Seq16 input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json`
- Seq16 input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.tsv`
- Seq16 proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json`
- Seq16 scale gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.json`
- Seq16 scale gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.tsv`
- Seq16 input generator: `scripts/zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input.py`
- Seq16 scale gate: `scripts/zkai_attention_kv_seq16_native_scale_gate.py`
- Shared native proof verifier: `src/stwo_backend/attention_kv_native_masked_sequence_proof.rs`

## Checked Surface

| Field | 8-step baseline | 16-step scaled proof |
| --- | ---: | ---: |
| Sequence length | `8` | `16` |
| Key width | `8` | `8` |
| Value width | `8` | `8` |
| Initial KV rows | `2` | `2` |
| Final KV rows | `10` | `18` |
| Score rows | `52` | `168` |
| Trace rows | `64` | `256` |
| Proof size | `24394` bytes | `32444` bytes |
| Envelope size | `265791` bytes | `464320` bytes |
| Mutation cases rejected | route selector `42 / 42` | scale gate `16 / 16` |

Seq16 selected positions:

```text
[0, 2, 3, 3, 5, 5, 7, 9, 7, 3, 7, 3, 7, 5, 7, 16]
```

Seq16 commitments:

| Commitment | Value |
| --- | --- |
| Statement | `blake2b-256:eabc8237a657963661169f4efc072325ee286a1ad676cfd28d31b6a10ed1bdc9` |
| Public instance | `blake2b-256:8e270e1992341e7f6d324036cfff0b53f2e1667080d7ea835dbe2c8bdf524bbb` |
| Score rows | `blake2b-256:787be4bbff96e717903be52573bd3650b175e55763075f5a7a3c9cbcc980d042` |
| Final KV cache | `blake2b-256:86c882ac29740c92f2ec57eb1775c61a9e4f0e15938ff0ccc45f73e73e98c89f` |
| Outputs | `blake2b-256:dce93ad4386e305734a9fafe2152cdbc65d28af4e90890ed511b9007e15209a3` |
| Scale gate | `blake2b-256:fbe95adbb130a1038c493d4c4f37340e0557aa4004e9ac2a290a114a5dce919c` |

Single local engineering observations from the proof CLI:

| Command | Prove time | Verify time |
| --- | ---: | ---: |
| `prove ...seq16...json ...seq16...envelope.json` | `135.124667 ms` | `79.893334 ms` |
| `verify ...seq16...envelope.json` | n/a | `92.952333 ms` |

These timings are single local engineering observations, not benchmark medians
and not publication-grade comparisons.

## Why This Matters

The issue `#448` result showed that a tiny attention/KV carried-state surface can
be expressed as native Stwo AIR. This result tests whether that was a one-off toy
shape. It is stronger in one specific way: the verifier now accepts a second
native proof profile with more carried-state transitions, more public score rows,
and a larger trace, while preserving the same binding discipline.

This supports the transformer/STARK paper's central thesis more directly than an
external adapter would: transformer decode has trace-shaped carried state, and the
native proof can scale along the sequence axis without changing proof systems.

## Non-Claims

- This is not Softmax.
- This is not multi-head attention.
- This is not `d=16` width scaling.
- This is not long-context inference.
- This is not a full transformer block.
- This is not private-witness privacy; score rows are public.
- This is not recursion or proof-carrying data.
- This is not a public benchmark row.

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_seq16_native_scale_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input \
  scripts.tests.test_zkai_attention_kv_seq16_native_scale_gate

cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof \
  --lib --features stwo-backend
```

## Next GO/NO-GO Targets

Do not jump to full inference. The next useful native STARK axes are:

1. two-head fixed sequence with explicit head identity and per-head commitments;
2. `d=16` width scaling with the same score-row and statement-binding discipline;
3. bounded Softmax-like approximation only with a statement-bound numeric policy;
4. composition with the native RMSNorm/block receipt commitments.
