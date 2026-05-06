# zkAI Attention/KV Native Stwo Bounded Softmax-Table Gate - 2026-05-07

## Question

Can the native Stwo attention/KV receipt move beyond the existing bounded
power-of-two weighted policy into a stronger Softmax-like approximation while
preserving statement binding, verifier-side recomputation, native AIR checking,
and mutation rejection?

## Result

GO for a narrow bounded Softmax-table native Stwo proof.

The checked artifact proves the same fixed eight-step, `d=8` causal-prefix
attention/KV sequence as the earlier bounded weighted route, but replaces the
hard-coded clipped power-of-two weight rule with a statement-bound exp-like
lookup table over clipped score gaps:

```text
clipped_gap = min(max_score - score, 8)
weight = table[clipped_gap]
```

The table is:

| clipped gap | weight |
| ---: | ---: |
| 0 | 256 |
| 1 | 181 |
| 2 | 128 |
| 3 | 91 |
| 4 | 64 |
| 5 | 45 |
| 6 | 32 |
| 7 | 23 |
| 8 | 16 |

The table identity, score scale, gap clip, denominator policy, output
quotient/remainder policy, and non-claims are bound into the statement. The
verifier recomputes the append-only KV carry, candidate scores, max score,
clipped score gaps, table-derived weights, denominators, weighted numerators,
floor-division outputs, and remainders before proof verification. The native AIR
proves row arithmetic for dot products, nonnegative score and causal gaps,
table-derived weight-value products, and output quotient/remainder relations.

This is not exact Softmax. It does not prove exp/div semantics. It is also not
an AIR-private lookup argument: table membership is verifier-recomputed over the
public rows and bound into the proof input before native proof verification.

## Evidence

- Input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json`
- Input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.tsv`
- Proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json`
- Gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json`
- Gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.tsv`
- Input generator: `scripts/zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input.py`
- Gate: `scripts/zkai_attention_kv_d8_bounded_softmax_table_native_gate.py`
- Native proof verifier: `src/stwo_backend/attention_kv_native_d8_bounded_softmax_table_proof.rs`
- Native proof CLI: `src/bin/zkai_attention_kv_native_d8_bounded_softmax_table_proof.rs`

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
| Score gap clip | `8` |
| Weight bits | `9` |
| Output remainder bits | `16` |
| Proof size | `44692` bytes |
| Envelope size | `451982` bytes |
| Mutation cases rejected | `18 / 18` |

Checked attention outputs:

```text
[
  [1, 1, 0, -1, 1, -1, 2, 1],
  [3, 1, 1, 0, -1, 1, 2, 0],
  [3, -1, 0, 1, 1, 0, -1, 1],
  [2, 1, 0, 1, 1, 0, 1, 1],
  [3, 2, 0, -1, 1, 1, -1, 1],
  [5, 1, 1, -2, 0, 3, -2, 1],
  [4, 4, -2, 0, 1, 1, 2, -1],
  [-3, 3, 0, -2, 3, 1, -1, 0]
]
```

## Commitments

| Commitment | Value |
| --- | --- |
| Statement | `blake2b-256:ce2f67e8009f647cef6282bc687e0346e52a27101d814b9626cd02163b417398` |
| Public instance | `blake2b-256:384bff181005ababda4e2227b3184382edf8069f4a112b436735886c2b567d31` |
| Score rows | `blake2b-256:1279d23d93288d6ddce174aaae45b895f8c0ba690754c0a3035a84a556efb5ec` |
| Final KV cache | `blake2b-256:593789678d4a171b53a2a91698d0cba11798c5b9273b9242a1d2e4d694e26873` |
| Outputs | `blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638` |
| Weight table | `blake2b-256:8c45ca7eec1032a0ffa5d5a1e842bebd5f6268d75f82d696b29ec7cf9a420e13` |

Single local engineering observations from the proof CLI:

| Command | Prove time | Verify time |
| --- | ---: | ---: |
| `prove ...bounded-softmax-table...json ...bounded-softmax-table...envelope.json` | `80.970708 ms` | `52.410459 ms` |
| `verify ...bounded-softmax-table...envelope.json` | n/a | `67.957250 ms` |

These timings are host-local engineering observations only. They are not public
benchmark rows.

## Comparison To Prior Native Weighted Route

| Route | Score rows | Trace rows | Proof size | Envelope size | Claim |
| --- | ---: | ---: | ---: | ---: | --- |
| `#460` d8 bounded weighted | `52` | `64` | `36769` bytes | `386078` bytes | power-of-two clipped weighted policy |
| `#463` d8 bounded Softmax-table | `52` | `64` | `44692` bytes | `451982` bytes | statement-bound exp-like table policy |

This is a positive but honest result. The stronger table policy costs proof
bytes and envelope bytes. The useful point is that the native proof still
verifies with the same carried-state, width, and sequence shape while binding a
more explicit Softmax-like approximation policy.

## Mutation Coverage

The gate rejects `18 / 18` checked mutations:

- statement commitment relabeling;
- public-instance commitment relabeling;
- weight-policy relabeling;
- weight-table commitment relabeling;
- score-scale relabeling;
- score-gap-clip relabeling;
- attention-output relabeling;
- output-commitment relabeling;
- score-row-count relabeling;
- final-KV relabeling;
- target-id relabeling;
- backend-version relabeling;
- proof-size metric smuggling;
- envelope-size metric smuggling;
- exact-Softmax overclaim drift;
- first-blocker removal;
- non-claim removal;
- unknown-field injection.

## Claim Boundary

This result should be described as:

> A native Stwo proof for a `d=8` bounded Softmax-table attention/KV receipt with
> statement-bound exp-like weights and verifier-recomputed table membership over
> public rows.

It should not be described as:

- exact Softmax;
- exp/div Softmax semantics;
- AIR-private lookup-table membership;
- full transformer inference;
- long-context inference;
- private-witness attention;
- recursive proof aggregation;
- on-chain verification;
- a public benchmark row.

## Why This Matters

This result moves the native STARK transformer lane from a hand-coded weighted
read to a table-bound approximation policy. That is closer to the structure of
real transformer attention, while preserving the claim discipline that exact
Softmax and private lookup arguments remain future work.

The next useful experiments are:

1. add AIR-private lookup/table columns for this same policy;
2. combine the table policy with two-head carried state;
3. profile proof bytes across the table, power-of-two, and argmax policies under
   a controlled grid.

## Reproduction

```bash
python3 scripts/zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input

cargo +nightly-2025-07-14 test attention_kv_native_d8_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_bounded_softmax_table_proof -- \
  prove docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_bounded_softmax_table_proof -- \
  verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d8_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_d8_bounded_softmax_table_native_gate
```
