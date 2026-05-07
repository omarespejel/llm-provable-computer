# zkAI Attention/KV Native Stwo Two-Head Bounded Softmax-Table Gate - 2026-05-07

## Question

Can the native Stwo attention/KV lane combine the two currently strongest axes:

- two-head carried KV-state binding; and
- a statement-bound bounded Softmax-table weighting policy?

## Result

GO for a narrow native Stwo two-head bounded Softmax-table proof.

Issue `#471` combines the issue `#461` two-head carried-state shape with the
issue `#463` bounded Softmax-table policy. The checked artifact proves a fixed
two-head, eight-step-per-head, `d=8` causal-prefix attention/KV sequence. For
each head and step, the verifier recomputes candidate scores, max score,
clipped score gap, table-derived weight, denominator, weighted numerator, floor
output, and remainder before native proof verification.

The bounded table policy is:

```text
clipped_gap = min(max_score - score, 8)
weight = table[clipped_gap]
```

The table is statement-bound:

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

The native AIR checks row arithmetic for dot products, nonnegative score and
causal gaps, table-derived weight-value products, and output
quotient/remainder relations. The statement binds the table commitment, score
scale, gap clip, denominator/output policy, per-head carried KV commitments,
outputs, and non-claims.

This is still not exact Softmax. It does not prove exp/div semantics. It is also
not an AIR-private lookup argument: table membership is verifier-recomputed over
public rows and bound into the proof input before native proof verification.

## Evidence

- Input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json`
- Input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.tsv`
- Proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json`
- Gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.json`
- Gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.tsv`
- Input generator: `scripts/zkai_attention_kv_stwo_native_two_head_bounded_softmax_table_proof_input.py`
- Gate: `scripts/zkai_attention_kv_two_head_bounded_softmax_table_native_gate.py`
- Native proof verifier: `src/stwo_backend/attention_kv_native_two_head_bounded_softmax_table_proof.rs`
- Native proof CLI: `src/bin/zkai_attention_kv_native_two_head_bounded_softmax_table_proof.rs`
- Backend version: `stwo-attention-kv-d8-causal-mask-two-head-bounded-softmax-table-v1`
- Proof version: `stwo-attention-kv-d8-causal-mask-two-head-bounded-softmax-table-air-proof-v1`
- Gate timing policy: `single_local_dev_profile_engineering_only_not_public_benchmark`

## Checked Surface

| Field | Value |
| --- | ---: |
| Heads | `2` |
| Key width | `8` |
| Value width | `8` |
| Sequence length per head | `8` |
| Initial KV rows | `4` |
| Final KV rows | `20` |
| Score rows | `104` |
| Trace rows | `128` |
| Score gap clip | `8` |
| Weight bits | `9` |
| Output remainder bits | `16` |
| Proof size | `47104` bytes |
| Envelope size | `563637` bytes |
| Mutation cases rejected | `23 / 23` |

Checked attention outputs:

```text
[
  [2, -3, 1, -4, 1, 2, 0, 1],
  [1, -2, 2, -1, 3, 0, -5, 1],
  [1, -4, 1, -4, 0, 4, -1, 2],
  [2, -3, 1, -1, 4, -1, -4, 1],
  [1, -1, 1, -1, 1, 0, 1, -3],
  [2, -2, -1, 1, 2, -1, -5, 2],
  [-1, -1, 0, 0, 2, 2, 3, -4],
  [3, 1, -1, -2, -3, 3, 1, 1],
  [3, -1, 2, -2, 2, -3, 1, -4],
  [1, -1, 0, 0, 0, 1, -2, 1],
  [3, -2, 1, -3, 0, 0, -2, -2],
  [1, -1, -3, 2, 1, -2, -4, 2],
  [0, -1, 0, 0, 1, 2, 2, -4],
  [3, -2, 0, -4, -1, 2, -3, 0],
  [-3, 2, 2, 1, 1, 0, 0, -2],
  [-1, 1, -3, 3, 0, -3, -2, -1]
]
```

## Commitments

| Commitment | Value |
| --- | --- |
| Statement | `blake2b-256:3430a919e3cede8302e11a7b182c3e85f1c0b894abe3a6c67f474fa83331fe2b` |
| Public instance | `blake2b-256:373e57f28dbf623016c07d90366c7fb1576220fa6d011a24371c0cdb2b1b69f9` |
| Score rows | `blake2b-256:3f7f2fb2da2281e4f8c4600a56d64606acaff4603d17cb5e794487e431ff2a78` |
| Final KV cache | `blake2b-256:747b8a86849b00f96402ca693cbf7255322cffbbc4dcdb88073e87598d7b1abb` |
| Outputs | `blake2b-256:4d03a0d881ef05c2d54e01668fd10e5da887523270068c3205d1a5632bc2edd6` |
| Weight table | `blake2b-256:ee5958fcab99005d7efc9311c55141cd7936c4d74f74e7cffd9af7483a2c02ea` |
| Gate | `blake2b-256:4480537073014d4fe68837c3b7750d34d1f1ef34157b21c39ff11ed998149a2e` |

The proof CLI emits deterministic JSON summaries and does not include wall-clock
timing fields. This gate records only artifact-size and mutation evidence, not a
public benchmark row.

## Comparison To Prior Native Routes

| Route | Heads | Score rows | Trace rows | Proof size | Envelope size | Claim |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `#460` d8 bounded weighted | `1` | `52` | `64` | `36769` bytes | `386078` bytes | power-of-two clipped weighted policy |
| `#461` two-head bounded weighted | `2` | `104` | `128` | `41175` bytes | `512060` bytes | two-head carry plus power-of-two clipped weighted policy |
| `#463` d8 bounded Softmax-table | `1` | `52` | `64` | `44692` bytes | `451982` bytes | statement-bound exp-like table policy |
| `#471` two-head bounded Softmax-table | `2` | `104` | `128` | `47104` bytes | `563637` bytes | two-head carry plus statement-bound exp-like table policy |

The most interesting engineering signal is the single-head to two-head
Softmax-table delta: score rows double from `52` to `104`, while raw proof bytes
grow from `44692` to `47104` (`1.054x`). The checked envelope grows more
substantially (`451982` to `563637`, `1.247x`) because it carries public rows and
pretty JSON proof bytes. This should stay engineering-only until issue `#469`
accounts for the binary PCS/FRI subobjects and a controlled grid exists.

## Mutation Coverage

The gate rejects `23 / 23` checked mutations:

- statement commitment relabeling;
- public-instance commitment relabeling;
- head-count relabeling;
- weight-policy relabeling;
- weight-table commitment relabeling;
- score-scale relabeling;
- score-gap-clip relabeling;
- attention-output relabeling;
- cross-head output-swap relabeling;
- output-commitment relabeling;
- score-row-count relabeling;
- quotient/remainder row drift;
- final-KV relabeling;
- final-KV cross-head swap relabeling;
- target-id relabeling;
- backend-version relabeling;
- proof-size metric smuggling;
- envelope-size metric smuggling;
- exact-Softmax overclaim drift;
- first-blocker removal;
- non-claim removal;
- nested receipt unknown-field injection;
- unknown-field injection.

## Claim Boundary

This result should be described as:

> A native Stwo proof for a two-head `d=8` bounded Softmax-table attention/KV
> receipt with statement-bound exp-like weights and verifier-recomputed table
> membership over public rows.

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

This is the strongest native attention/KV synthesis result so far. The repo now
has one checked Stwo route that combines explicit multi-head carried state with a
more Softmax-like, statement-bound weight policy. That is closer to transformer
attention than the earlier argmax and power-of-two weighted fixtures, while
still preserving the honest boundary around exact Softmax and lookup arguments.

The next useful experiments are:

1. issue `#470`: move table membership into AIR-private lookup/table columns or
   record the exact missing Stwo feature;
2. issue `#469`: account for binary PCS/FRI subobjects so the proof-byte signal
   is not inferred from JSON sections;
3. a controlled `1/2/4` head grid after #469, if the proof-byte signal remains
   interesting.

## Reproduction

```bash
python3 scripts/zkai_attention_kv_stwo_native_two_head_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_two_head_bounded_softmax_table_proof_input

cargo +nightly-2025-07-14 test attention_kv_native_two_head_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_bounded_softmax_table_proof -- \
  prove docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_bounded_softmax_table_proof -- \
  verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_two_head_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_bounded_softmax_table_native_gate

python3 -m py_compile \
  scripts/zkai_attention_kv_stwo_native_two_head_bounded_softmax_table_proof_input.py \
  scripts/zkai_attention_kv_two_head_bounded_softmax_table_native_gate.py \
  scripts/tests/test_zkai_attention_kv_stwo_native_two_head_bounded_softmax_table_proof_input.py \
  scripts/tests/test_zkai_attention_kv_two_head_bounded_softmax_table_native_gate.py

just lib
just gate-fast
just gate
```
