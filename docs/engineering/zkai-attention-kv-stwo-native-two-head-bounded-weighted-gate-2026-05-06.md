# ZKAI Attention/KV Native Stwo Two-Head Bounded Weighted Gate (2026-05-06)

## Decision

`GO_NATIVE_STWO_ATTENTION_KV_TWO_HEAD_BOUNDED_WEIGHTED_D8_MASKED_SEQUENCE`

Issue `#461` is a narrow GO: the native Stwo attention/KV lane now has a real proof-backed two-head `d=8` causal-prefix bounded weighted-attention receipt.

This combines the two previously separate axes:

- issue `#455`: explicit two-head state binding for integer-argmax attention/KV;
- issue `#460`: bounded score-derived weighted attention for the `d=8` single-head fixture.

## Checked Surface

- Heads: `2`
- Key width: `8`
- Value width: `8`
- Sequence length per head: `8`
- Initial KV rows: `4`
- Final KV rows: `20`
- Score rows: `104`
- Trace rows: `128`
- Weight policy: `power2_gap_clipped_4_floor_division`
- Proof bytes: `41175`
- Envelope bytes: `512060`
- Gate mutations: `16 / 16` rejected
- Timing policy: `single_local_dev_profile_engineering_only_not_public_benchmark`

The statement commitment is:

`blake2b-256:57bbf22000a70ea241a43bcf3ecd79a723b497827ca5782d39577d8bb242810b`

## What The Verifier Recomputes

Before proof verification, the verifier-side parser and input validator recompute:

- per-head append-only KV carry;
- per-candidate query-key dot products;
- max score per head and step;
- bounded power-of-two weights from score gaps;
- weighted value products;
- weighted numerators and denominators;
- floor quotient outputs and nonnegative remainders;
- score-row, input-step, KV-cache, output, public-instance, and statement commitments.

The proof-input generator also pins the upstream two-head source payload by
schema, target, backend version, proof version, statement version, shape fields,
and canonical SHA-256 before deriving the bounded weighted rows. That prevents a
future source-fixture edit from silently changing this evidence bundle.

The AIR checks row arithmetic for dot products, score-gap bit decomposition, causal-gap bit decomposition, weight bit decomposition, weighted-value products, and output quotient/remainder relations.

## Mutation Coverage

The gate rejects all checked mutation classes:

- statement commitment relabeling;
- public-instance commitment relabeling;
- head-count relabeling;
- weight-policy relabeling;
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

## Interpretation

This is the strongest native attention/KV result so far because it combines multi-head carried state with weighted attention semantics in the same Stwo proof surface.

One interesting engineering signal is that the score-row count doubles versus the single-head `d=8` bounded weighted route (`104` vs `52`), while proof bytes grow from `36769` to `41175` and checked-envelope bytes grow from `386078` to `512060`. This is not a paper benchmark claim: it is a local engineering observation that should be profiled under a stronger timing and proof-size policy before public use.

## Non-Claims

This is not exact Softmax attention. It does not prove exp/div semantics. It is not full transformer inference, not long-context evidence, not proof aggregation across heads, not recursive verification, not PCD, and not Starknet deployment evidence.

## Reproduction

```bash
python3 scripts/zkai_attention_kv_stwo_native_two_head_bounded_weighted_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_two_head_bounded_weighted_proof_input
cargo +nightly-2025-07-14 test attention_kv_native_two_head_bounded_weighted_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_two_head_bounded_weighted_proof -- prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_two_head_bounded_weighted_proof -- verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json
python3 scripts/zkai_attention_kv_two_head_bounded_weighted_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_bounded_weighted_native_gate
```
