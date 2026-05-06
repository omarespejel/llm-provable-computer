# zkAI Attention/KV Native Stwo Bounded Weighted Gate - 2026-05-06

## Question

Can the native Stwo attention/KV proof surface move beyond integer argmax toward
a weighted-attention policy while preserving carried KV binding, verifier-side
recomputation, and mutation-rejection discipline?

## Result

GO for a narrow bounded weighted-attention native Stwo proof.

The checked artifact proves a fixed `d=4`, four-step causal-prefix attention/KV
sequence using a deterministic score-to-weight policy:

```text
weight = 2 ** (4 - min(max_score - score, 4))
```

Each allowed candidate contributes to the output. The verifier recomputes the
append-only KV carry, candidate scores, max score, bounded weights, denominator,
weighted numerators, floor-division outputs, and remainders before proof
verification. The native AIR proves the row arithmetic tying those public rows
together: dot products, nonnegative score and causal gaps, weight-value
products, and output quotient/remainder relations.

This is the first native weighted-attention proof surface in this repo. It is
not exact Softmax, not exp/div Softmax semantics, not full transformer
inference, not long-context evidence, and not recursion or PCD.

## Evidence

- Input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.json`
- Input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.tsv`
- Proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.envelope.json`
- Gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-gate-2026-05.json`
- Gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-gate-2026-05.tsv`
- Input generator: `scripts/zkai_attention_kv_stwo_native_bounded_weighted_proof_input.py`
- Gate: `scripts/zkai_attention_kv_bounded_weighted_native_gate.py`
- Native proof verifier: `src/stwo_backend/attention_kv_native_bounded_weighted_proof.rs`
- Native proof CLI: `src/bin/zkai_attention_kv_native_bounded_weighted_proof.rs`

## Checked Surface

| Field | Value |
| --- | ---: |
| Key width | `4` |
| Value width | `4` |
| Sequence length | `4` |
| Initial KV rows | `2` |
| Final KV rows | `6` |
| Score rows | `18` |
| Trace rows | `64` |
| Proof size | `23952` bytes |
| Envelope size | `220004` bytes |
| Mutation cases rejected | `15 / 15` |

Checked attention outputs:

```text
[[3, 2, 1, 2], [2, 3, 2, 2], [3, 3, 1, 3], [3, 2, 2, 3]]
```

The important difference from the earlier argmax surface is that the output is
not copied from one selected candidate row. Every candidate that passes the
causal mask receives a monotone score-derived weight and contributes to the
weighted numerator. The output is the floor quotient of the numerator divided
by the denominator, with a checked remainder.

## Commitments

| Commitment | Value |
| --- | --- |
| Statement | `blake2b-256:8da9dc33204d842d63c4176f031d4e5d67e8a019ffc4a3ea612b0421bf6e85a6` |
| Public instance | `blake2b-256:97c906fd4b0b7d3aaf6fb070f81a47089fda42bfe9a53b8f69f6a10a360b7332` |
| Score rows | `blake2b-256:6c734a88db733852b64d0221f9f98ef8a6fedd1c11d1ac2efbcb9c1fb263ad73` |
| Final KV cache | `blake2b-256:a0768c1d4b820a86c35616f989e69a83332a990d01e5115627fddfab08dd0c02` |
| Outputs | `blake2b-256:0b4689167fd37910ef304b68346de47fde150de3f1a1f732c70cf14486f3987b` |

Single local engineering observations from the proof CLI:

| Command | Prove time | Verify time |
| --- | ---: | ---: |
| `prove ...bounded-weighted...json ...bounded-weighted...envelope.json` | `48.146250 ms` | `26.648875 ms` |
| `verify ...bounded-weighted...envelope.json` | n/a | `29.051542 ms` |

These timings are host-local engineering observations only. They are not public
benchmark rows.

## Mutation Coverage

The gate rejects `15 / 15` checked mutations:

- statement commitment relabeling,
- public-instance commitment relabeling,
- weight-policy relabeling,
- weighted score/output relabeling,
- quotient/remainder relabeling,
- final-KV commitment relabeling,
- target/backend relabeling,
- proof/envelope metric smuggling,
- exact-Softmax overclaim drift,
- blocker removal,
- non-claim removal,
- unknown-field injection.

## Claim Boundary

This result should be described as:

> A native Stwo proof for a bounded weighted-attention/KV receipt with verifier-
> recomputed monotone score-derived weights and AIR-checked weighted-product and
> quotient/remainder rows.

It should not be described as:

- exact Softmax,
- transformer inference,
- long-context inference,
- private-witness attention,
- recursive proof aggregation,
- on-chain verification,
- a public benchmark row.

## Why This Matters

The attention/KV lane now has five native axes:

1. `#448`: stateful causal masked attention/KV in native Stwo,
2. `#450`: sequence-length scaling,
3. `#453`: width scaling,
4. `#455`: head multiplicity,
5. `#456`: bounded weighted attention instead of selected-row argmax.

This is the first step from “the proof binds the carried KV state” toward “the
proof binds an attention-shaped weighted read from that carried state.” The next
useful experiments are `#460` (`d=8` bounded weighted attention) and `#461`
(two-head bounded weighted attention), not exact Softmax claims.

## Reproduction

```bash
python3 scripts/zkai_attention_kv_stwo_native_bounded_weighted_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_bounded_weighted_proof_input

cargo +nightly-2025-07-14 test attention_kv_native_bounded_weighted_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_bounded_weighted_proof -- \
  prove docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_bounded_weighted_proof -- \
  verify docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_bounded_weighted_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_bounded_weighted_native_gate
```
