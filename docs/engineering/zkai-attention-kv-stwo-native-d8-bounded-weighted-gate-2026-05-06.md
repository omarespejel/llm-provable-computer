# zkAI Attention/KV Native Stwo d8 Bounded Weighted Gate - 2026-05-06

## Question

Can the native Stwo bounded weighted-attention/KV policy from issue `#456` move
from the small `d=4` fixture to the existing `d=8` causal-prefix masked sequence
without losing verifier-side recomputation, AIR row checks, or mutation-rejection
discipline?

## Result

GO for a narrow `d=8` bounded weighted-attention native Stwo proof.

The checked artifact proves a fixed eight-step, `d=8` causal-prefix attention/KV
sequence using the deterministic score-to-weight policy from issue `#456`:

```text
weight = 2 ** (4 - min(max_score - score, 4))
```

Each allowed candidate contributes to the output. The verifier recomputes the
append-only KV carry, candidate scores, max score, bounded weights, denominator,
weighted numerators, floor-division outputs, and remainders before proof
verification. The native AIR proves the row arithmetic tying those public rows
together: dot products, nonnegative score and causal gaps, weight-value
products, and output quotient/remainder relations.

This is a scale/semantics result for native Stwo transformer-shaped receipts. It
is not exact Softmax, not exp/div Softmax semantics, not full transformer
inference, not long-context evidence, and not recursion or PCD.

## Evidence

- Input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.json`
- Input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.tsv`
- Proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.envelope.json`
- Gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.json`
- Gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.tsv`
- Input generator: `scripts/zkai_attention_kv_stwo_native_d8_bounded_weighted_proof_input.py`
- Gate: `scripts/zkai_attention_kv_d8_bounded_weighted_native_gate.py`
- Native proof verifier: `src/stwo_backend/attention_kv_native_d8_bounded_weighted_proof.rs`
- Native proof CLI: `src/bin/zkai_attention_kv_native_d8_bounded_weighted_proof.rs`

## Checked Surface

| Field | Value |
| --- | ---: |
| Key width | `8` |
| Value width | `8` |
| Sequence length | `8` |
| Initial KV rows | `2` |
| Final KV rows | `10` |
| Score rows | `52` |
| Trace rows | `64` |
| Proof size | `36769` bytes |
| Envelope size | `386078` bytes |
| Mutation cases rejected | `15 / 15` |

Checked attention outputs:

```text
[
  [1, 1, 0, -1, 2, -1, 1, 1],
  [3, 1, 0, 0, -1, 2, 1, 1],
  [4, -1, 0, 2, 1, 0, -1, 1],
  [3, 1, -1, 1, 1, 0, 0, 2],
  [3, 2, 0, -1, 1, 2, -1, 1],
  [5, 1, 1, -2, 0, 3, -2, 1],
  [4, 4, -2, 0, 1, 1, 2, -1],
  [-3, 4, 0, -2, 3, 1, -1, 0]
]
```

The important difference from the earlier `d=8` argmax surface is that the
output is not copied from one selected candidate row. Every causally allowed
candidate receives a monotone score-derived weight and contributes to the
weighted numerator. The output is the floor quotient of the numerator divided by
the denominator, with a checked remainder.

## Commitments

| Commitment | Value |
| --- | --- |
| Statement | `blake2b-256:9f5d0a15b4a5f5a8481f39ffad44df58824b773375163f2f0908b847082e7b5a` |
| Public instance | `blake2b-256:c9a5cc96afc62629650f3041e043de5723ead8244136e069f5b80cc297765333` |
| Score rows | `blake2b-256:e0bb80622c53d93004d92488f111b03a21ea13278f4d19658e34158beb0fc0bf` |
| Final KV cache | `blake2b-256:5d1f356ee8eaa8c5e6bd040e99fecc10fa96f9e117d93d4e88f103d02066c02a` |
| Outputs | `blake2b-256:5462bb712e33665feb3193d3a76cb0db8725a45e1742924bcfb5802d522f56d6` |

Single local engineering observations from the proof CLI:

| Command | Prove time | Verify time |
| --- | ---: | ---: |
| `prove ...d8-bounded-weighted...json ...d8-bounded-weighted...envelope.json` | `69.377042 ms` | `38.436583 ms` |
| `verify ...d8-bounded-weighted...envelope.json` | n/a | `85.596500 ms` |

These timings are host-local engineering observations only. They are not public
benchmark rows.

## Comparison To Existing Native Surfaces

This result preserves the same `d=8`, eight-step sequence shape as the issue
`#448` native argmax proof, but changes the attention readout from selected-row
copying to bounded weighted averaging.

| Route | Score rows | Proof size | Envelope size | Claim |
| --- | ---: | ---: | ---: | --- |
| `#448` d8 argmax | `52` | `24394` bytes | `265791` bytes | selected-row integer argmax |
| `#456` d4 bounded weighted | `18` | `23952` bytes | `220004` bytes | bounded weighted policy |
| `#460` d8 bounded weighted | `52` | `36769` bytes | `386078` bytes | bounded weighted policy at d8 |

The interesting point is not that d8 is free. It is not. The weighted-product
and quotient/remainder columns add proof and envelope size. The useful result is
that the semantics survive at the same width and carried-state shape as the d8
native attention/KV fixture while retaining checked mutation rejection.

## Mutation Coverage

The gate rejects `15 / 15` checked mutations:

- statement commitment relabeling,
- public-instance commitment relabeling,
- weight-policy relabeling,
- attention-output vector relabeling,
- outputs-commitment relabeling,
- score-row count relabeling,
- final-KV commitment relabeling,
- target/backend relabeling,
- proof/envelope metric smuggling,
- exact-Softmax overclaim drift,
- blocker removal,
- non-claim removal,
- unknown-field injection.

## Claim Boundary

This result should be described as:

> A native Stwo proof for a `d=8` bounded weighted-attention/KV receipt with
> verifier-recomputed monotone score-derived weights and AIR-checked weighted-
> product and quotient/remainder rows.

It should not be described as:

- exact Softmax,
- transformer inference,
- long-context inference,
- private-witness attention,
- recursive proof aggregation,
- on-chain verification,
- a public benchmark row.

## Why This Matters

The attention/KV lane now has six native axes:

1. `#448`: stateful causal masked attention/KV in native Stwo,
2. `#450`: sequence-length scaling,
3. `#453`: width scaling,
4. `#455`: head multiplicity,
5. `#456`: bounded weighted attention instead of selected-row argmax,
6. `#460`: bounded weighted attention at the same `d=8` width as the native
   masked-sequence fixture.

This moves the STARK-native transformer story from “the proof binds a carried KV
state and an argmax read” toward “the proof binds a carried KV state and an
attention-shaped weighted read from that state.” The next useful experiment is
issue `#461`: two-head bounded weighted attention, not exact Softmax claims.

## Reproduction

```bash
python3 scripts/zkai_attention_kv_stwo_native_d8_bounded_weighted_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_d8_bounded_weighted_proof_input

cargo +nightly-2025-07-14 test attention_kv_native_d8_bounded_weighted_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_bounded_weighted_proof -- \
  prove docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_bounded_weighted_proof -- \
  verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d8_bounded_weighted_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_d8_bounded_weighted_native_gate
```
