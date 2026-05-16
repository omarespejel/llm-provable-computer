# zkAI Native Attention+MLP Adapter-AIR Frontier - 2026-05-16

## Result

This gate started as the correctness-first frontier for the native
attention-plus-MLP route. It is now closed by the regenerated single-proof
object: the attention-output-to-d128-input adapter is proved as a native AIR
component inside the same Stwo proof.

The result is a narrow GO/NO-GO:

- GO: the exact adapter constraint surface is now specified and checked against
  the existing attention-derived d128 input artifact;
- GO: the adapter rows are value-connected to the attention output commitment
  and the d128 RMSNorm input commitment;
- GO: the regenerated Stwo proof includes the adapter component and verifies
  locally;
- NO-GO: this cannot be called a size breakthrough because the native-adapter
  proof now costs `1,232` typed bytes more than the two-proof frontier;
- NO-GO: this is still not a NANOZK-comparable benchmark or proof-size win.

Bounded result: issue #629 closes the native AIR implementation question, but
opens the harder compression question. We now know the proof is more correct,
and also know exactly how much size we need to recover.

## Numbers

- Current single proof with native adapter AIR: `41,932` local typed bytes.
- Current two-proof frontier: `40,700` local typed bytes.
- Current delta versus two-proof target: `+1,232` typed bytes.
- Adapter candidate rows: `128`.
- Adapter candidate trace columns: `9` value columns plus `3` remainder-bit
  columns.
- Adapter candidate trace cells: `1,536`.
- Adapter constraints pinned: `10`.
- Current gap to NANOZK's paper-reported `6,900` byte d128 row: `35,032`
  typed bytes.

The human interpretation is simple: proving the adapter natively was the right
correctness move, and it made the current byte metric worse. That is still
useful. It tells us the next proof object should attack adapter representation,
query/opening economics, or component boundaries without weakening value
binding.

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

The first question is now answered for this fixture: yes. The second remains
open and hard. The first native adapter-AIR implementation should be judged as a
correctness gate, not a compression gate.

## Non-Claims

- This is not proof-size savings from native adapter AIR.
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
just gate
```
