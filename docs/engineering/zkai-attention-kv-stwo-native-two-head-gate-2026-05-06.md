# zkAI Attention/KV Native Stwo Two-Head Gate - 2026-05-06

## Question

Can the native Stwo attention/KV proof from issues `#448`, `#450`, and `#453`
scale from one head to two explicit heads while preserving statement binding,
per-head carried KV semantics, and mutation-rejection discipline?

## Result

GO for a narrow two-head native Stwo attention/KV proof.

The checked artifact keeps the same intentionally bounded arithmetic surface:

- two explicit attention heads,
- `d=8` key/value width per head,
- eight carried input steps per head,
- integer-argmax attention,
- causal-prefix masking,
- lowest-position tie break,
- public score rows,
- verifier-recomputed append-only KV carry per head,
- statement-bound prior/input/output/final-state commitments.

This is a multi-head-axis result. It is not Softmax, not long-context
inference, not full autoregressive inference, not proof aggregation across
heads, and not recursion or PCD.

## Evidence

- Two-head input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json`
- Two-head input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.tsv`
- Two-head proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.envelope.json`
- Two-head gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-gate-2026-05.json`
- Two-head gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-gate-2026-05.tsv`
- Two-head input generator: `scripts/zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input.py`
- Two-head gate: `scripts/zkai_attention_kv_two_head_native_gate.py`
- Shared native proof verifier: `src/stwo_backend/attention_kv_native_masked_sequence_proof.rs`

## Checked Surface

| Field | d8 single-head baseline | d8 two-head proof |
| --- | ---: | ---: |
| Heads | `1` | `2` |
| Sequence length per head | `8` | `8` |
| Total input steps | `8` | `16` |
| Key width per head | `8` | `8` |
| Value width per head | `8` | `8` |
| Initial KV rows | `2` | `4` |
| Final KV rows | `10` | `20` |
| Score rows | `52` | `104` |
| Trace rows | `64` | `128` |
| Proof size | `24394` bytes | `25453` bytes |
| Envelope size | `265791` bytes | `343719` bytes |
| Mutation cases rejected | route selector `42 / 42` | two-head gate `18 / 18` |

The two-head proof doubles checked input steps, score rows, and trace rows while
the proof byte payload grows from `24394` bytes to `25453` bytes
(`1.043412x`). The envelope grows more because it includes the larger public
input body (`1.293193x`), which is expected for this public-row fixture.

The selected positions are flattened in input-step order, interleaving head `0`
and head `1`:

```text
[1, 1, 1, 1, 0, 2, 2, 4, 0, 0, 7, 2, 2, 5, 6, 2]
```

That matters because the two-head artifact is not a relabeled single-head proof.
The score rows, input steps, final KV cache, output rows, statement commitment,
and public-instance commitment include explicit head identity where the old
single-head profile did not.

## Commitments

| Commitment | Value |
| --- | --- |
| Statement | `blake2b-256:718f31a22d372cf1a334791b116a535317a230503350b616d42bdd7dc3fe4aab` |
| Public instance | `blake2b-256:9e037276f313dd05838b2d64f9c04a8ebc096bb171213cf439423f39e0e6d91f` |
| Score rows | `blake2b-256:ce21110487f94644359707df3dac02bc1cf40c9a748d29dd8f45581904683167` |
| Final KV cache | `blake2b-256:1b4289832e620201afaf25aba2a816e4f34cadf352accf163fe40a6431ca6bc5` |
| Outputs | `blake2b-256:03f3b934ae0148d5db3de1313ad6d93604fc7509df30e386d20e1e91d59421fd` |

Single local engineering observations from the proof CLI:

| Command | Prove time | Verify time |
| --- | ---: | ---: |
| `prove ...two-head...json ...two-head...envelope.json` | `147.698625 ms` | `196.311208 ms` |
| `verify ...two-head...envelope.json` | n/a | `67.687959 ms` |

These timings are single local engineering observations, not benchmark medians
and not publication-grade comparisons.

## Why This Matters

The issue `#450` result scaled sequence length. The issue `#453` result scaled
vector width. This result scales the third basic transformer-attention axis:
head multiplicity.

The useful research point is structural, not performance marketing: carried
autoregressive attention state can be split into explicit per-head streams and
still accepted by the same native Stwo verifier family with head identity bound
into public rows and commitments. The verifier rejects relabeling of head count,
input-step head identity, score-row head identity, selected positions, final KV
state, output commitments, route metadata, and metric claims.

This is directly useful for the STARK-transformer paper because it moves the
attention/KV lane closer to real transformer structure without leaving the
native Stwo proof path.

## Non-Claims

- This is not Softmax.
- This is not long-context inference.
- This is not full autoregressive inference.
- This is not a full transformer block.
- This is not private-witness privacy; score rows are public.
- This is not recursion or proof-carrying data.
- This is not proof aggregation across heads.
- This is not a public benchmark row.

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_two_head_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input \
  scripts.tests.test_zkai_attention_kv_two_head_native_gate

cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof \
  --lib --features stwo-backend

just lib
just gate-fast
just gate
```

## Next GO/NO-GO Targets

Do not jump to full inference. The next useful native STARK axes are:

1. bounded Softmax-like approximation with an explicit numeric policy (tracked
   as issue `#456`);
2. larger per-head sequence frontier after preserving the same head-binding
   rejection surface;
3. composition with native RMSNorm/block receipt commitments.
