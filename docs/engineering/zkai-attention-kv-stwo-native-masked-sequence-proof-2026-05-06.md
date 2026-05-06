# zkAI Attention/KV Native Stwo Masked-Sequence Proof - 2026-05-06

## Question

Can the attention/KV carried-state surface move from source contracts and
external proof controls into a native Stwo AIR proof, even for a deliberately tiny
fixture?

## Result

GO for a narrow native Stwo proof.

The checked artifact proves a fixed eight-step `d=8` causal-prefix masked
integer-argmax attention/KV sequence. The verifier-facing statement binds:

- initial KV cache commitment,
- input/query step commitment,
- per-candidate score-row commitment,
- final KV cache commitment,
- attention-output commitment,
- public-instance commitment,
- statement commitment,
- backend and statement versions,
- causal-prefix masking policy,
- lowest-position tie-break policy.

This is the first native Stwo attention/KV proof surface in this lane. It is a
small proof of transformer-shaped carried state, not a full transformer or
performance benchmark.

## Evidence

- Input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json`
- Input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.tsv`
- Proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json`
- Input generator: `scripts/zkai_attention_kv_stwo_native_masked_sequence_proof_input.py`
- Native proof CLI: `src/bin/zkai_attention_kv_native_masked_sequence_proof.rs`
- Native AIR module: `src/stwo_backend/attention_kv_native_masked_sequence_proof.rs`
- Route selector: `docs/engineering/zkai-attention-kv-proof-route-selector-2026-05-05.md`

## Checked Surface

| Field | Value |
| --- | ---: |
| Sequence length | `8` |
| Key width | `8` |
| Value width | `8` |
| Initial KV rows | `2` |
| Final KV rows | `10` |
| Score rows | `52` |
| Trace rows | `64` |
| Selected positions | `[0, 2, 3, 3, 5, 5, 7, 9]` |
| Masking policy | `causal_prefix_position_lte_query_token` |
| Tie break | `lowest_position` |
| Proof size | `24394` bytes |
| Envelope size | `265801` bytes |
| Single local prove+verify run prove time | `41.107458 ms` |
| Single local prove+verify run verify time | `29.894042 ms` |
| Separate single local verify run time | `43.516 ms` |

Commitments:

| Commitment | Value |
| --- | --- |
| Statement | `blake2b-256:dcb688e7e2d7076b2f2fe35c6aa3a12af57d676101c300b48cbda66797e4f232` |
| Public instance | `blake2b-256:3c5a7c1aaf6b7ececf3d729935b0548b0b947ce3c649f0370dd44fc687227631` |
| Score rows | `blake2b-256:8348dc0d9c052050c77bc56a4c08896c283ca710ab2caca30f1bab60d8451337` |
| Final KV cache | `blake2b-256:74038853585ec88f7211e615910923d194d5731af74197c370daaf906d0be1e2` |
| Outputs | `blake2b-256:a39a6d6e90b4fa06d443807d4fe9110c0986a67c930d9ceff4e0bc4bbce9c083` |

The timing values above are single local engineering observations from the proof
CLI. They are not publication-grade benchmark medians.

## AIR / Verifier Checks

The native proof path checks the public-row arithmetic and verifier-side state
transition contract together:

- row values equal the committed public rows used by the verifier;
- enabled, mask, selected, and tied flags are boolean;
- enabled score rows require causal mask allowance;
- per-coordinate products satisfy `query_i * key_i = product_i`;
- each score equals the sum of products;
- selected score dominates candidate score through a bit-decomposed non-negative
  score gap;
- candidate position satisfies the causal-prefix gap;
- tied candidates satisfy the lowest-position tie-break gap;
- selected rows bind the emitted attention output to the selected value;
- verifier-side validation recomputes append-only KV carry, selected positions,
  output rows, and all statement commitments before accepting the proof.

## Negative Coverage

The Rust test surface rejects:

- score product drift,
- selected-output relabeling,
- statement/commitment drift,
- tie-break drift,
- public-row mutation after proving,
- proof byte tampering,
- unexpected commitment-vector entries,
- PCS config drift,
- oversized proof input.

The Python input tests reject malformed geometry and malformed public-row
fixtures. The route selector then rejects `42 / 42` route/removal, native-statement
drift, external-control drift, fake-metric, non-claim, blocker, and parser/schema
mutations.

## Non-Claims

- This is not Softmax.
- This is not multi-head attention.
- This is not long-context inference.
- This is not a full transformer block.
- This is not private-witness privacy; the checked score rows are public rows.
- This is not recursion or proof-carrying data.
- This is not a benchmark row.

## Interpretation

This is the first concrete bridge from the paper's transformer/STARK thesis into
a native Stwo attention/KV proof. The result is intentionally small, but it is
not a metadata wrapper: the proof checks the score rows and carried-state
selection logic for a transformer-shaped autoregressive state surface.

For the paper program, the roles are now clean:

- Main transformer/STARK story: transformer decode is a trace-shaped carried
  state machine.
- Tablero story: typed boundaries remove replay and bind claims across layers.
- External adapters: appendix/control evidence for statement binding across proof
  systems.
- Native Stwo attention/KV proof: the new experimental bridge showing that the
  stateful transformer surface can be expressed as a native STARK AIR.

## Next GO/NO-GO Targets

The next result should scale one axis at a time. This follow-up is tracked in
issue `#450`.

1. `d=16` causal-prefix masked integer-argmax attention/KV sequence.
2. Two-head fixed sequence with explicit head identity in the statement.
3. Longer fixed sequence with the same public-row and statement-binding rules.
4. A bounded Softmax-like approximation only if the numeric approximation policy
   is statement-bound and checked by the verifier.
5. A bridge from native RMSNorm/block receipt commitments into the attention/KV
   statement.

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_masked_sequence_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof \
  --lib --features stwo-backend

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_masked_sequence_proof_input
```
