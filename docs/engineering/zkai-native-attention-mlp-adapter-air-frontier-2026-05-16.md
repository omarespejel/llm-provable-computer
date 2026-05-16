# zkAI Native Attention+MLP Adapter-AIR Frontier - 2026-05-16

## Result

This gate does not implement the native adapter. It pins the exact
correctness-first attack for the native attention-plus-MLP route: the next proof
object must prove the attention-output-to-d128-input adapter as a native AIR
component.

The result is a narrow GO/NO-GO:

- GO: the exact adapter constraint surface is now specified and checked against
  the existing attention-derived d128 input artifact;
- GO: the adapter rows are value-connected to the attention output commitment
  and the d128 RMSNorm input commitment;
- NO-GO: this is not yet a regenerated Stwo proof with the adapter component
  included, and this PR must not be treated as closing the native AIR
  implementation tracked in issue #629;
- NO-GO: this cannot be called a size breakthrough because the current one-proof
  object only has `32` typed bytes of slack versus the two-proof frontier;
- NO-GO: adding the adapter to the actual proof requires a Rust/Stwo component
  change plus regenerated one-proof verification evidence. Treating the
  externally checked projection rows as proof-internal constraints would weaken
  verifier binding.

Bounded NO-GO for this PR: implementing the adapter as native AIR requires
changing the Rust/Stwo single-proof component and regenerating a verifier-checked
one-proof artifact. Treating the externally checked projection rows as if they
were already inside the proof would weaken verifier binding, so this PR stops at
pinning the exact constraint surface and opens issue #629 for the native
implementation.

## Numbers

- Current single proof: `40,668` local typed bytes.
- Current two-proof frontier: `40,700` local typed bytes.
- Current slack versus two-proof target: `32` typed bytes.
- Adapter candidate rows: `128`.
- Adapter candidate trace columns: `9` value columns plus `3` remainder-bit
  columns.
- Adapter candidate trace cells: `1,536`.
- Adapter constraints pinned: `10`.
- Current gap to NANOZK's paper-reported `6,900` byte d128 row: `33,768`
  typed bytes.

The human interpretation is simple: proving the adapter natively is the right
correctness move, but it almost certainly makes the current byte metric worse
before it gets better. That is still useful. It tells us the next proof object
should prioritize honest value binding first, then attack query/opening
economics or component boundaries.

## Adapter Surface

The checked policy is the existing fixed public projection:

```text
primary_source_index = i mod 64
mix_source_index     = (17*i + 11) mod 64
bias_q8              = ((7*i + 3) mod 9) - 4
numerator_q8         = 9*primary_q8 + 5*mix_q8 + bias_q8
numerator_q8         = 8*output_q8 + floor_remainder_q8
```

The gate checks that all floor remainders fit in `3` boolean bits and that the
adapter outputs match the d128 RMSNorm input commitment
`blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`.

## Interpretation

This strengthens the breakthrough path by separating two questions that were
easy to blur:

1. Can we make the attention-to-MLP handoff value-correct inside the native
   proof architecture?
2. Can we make that stricter proof object smaller?

The first question now has a concrete implementation target. The second remains
open and hard. The current adapter overhead budget for preserving even the tiny
single-proof size win is only `32` typed bytes, so the first native adapter-AIR
implementation should be judged as a correctness gate, not a compression gate.
Follow-up issue #629 tracks that implementation.

## Non-Claims

- This is not a regenerated Stwo proof with the adapter component included.
- This is not proof-size savings.
- This is not a NANOZK proof-size win.
- This is not a matched NANOZK workload or benchmark.
- This is not exact real-valued Softmax.
- This is not full transformer block inference.
- This is not timing evidence.
- This is not recursion or proof-carrying data.
- This is not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-native-attention-mlp-adapter-air-frontier-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-adapter-air-frontier-2026-05.tsv`
- `scripts/zkai_native_attention_mlp_adapter_air_frontier_gate.py`
- `scripts/tests/test_zkai_native_attention_mlp_adapter_air_frontier_gate.py`

Source evidence pinned by hash:

- `docs/engineering/evidence/zkai-attention-derived-d128-input-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.json`

## Validation

```bash
python3 scripts/zkai_native_attention_mlp_adapter_air_frontier_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-adapter-air-frontier-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-adapter-air-frontier-2026-05.tsv
python3 -m py_compile scripts/zkai_native_attention_mlp_adapter_air_frontier_gate.py scripts/tests/test_zkai_native_attention_mlp_adapter_air_frontier_gate.py
python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_adapter_air_frontier_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
```
