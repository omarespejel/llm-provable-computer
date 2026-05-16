# zkAI Native Attention+MLP Lifting Ablation - 2026-05-16

## Result

This gate checks whether the explicit PCS lifting and grouped proof-field
overhangs explain why the native-adapter attention-plus-MLP single proof is now
larger than the two-proof frontier.

The answer is a narrow NO-GO:

- checked single proof with native adapter AIR: `41,932` local typed bytes;
- previous two-proof frontier: `40,700` local typed bytes;
- current delta: `+1,232` typed bytes;
- positive typed-field deltas in the single proof:
  `+1,088` bytes in `fri_decommitments`, `+256` in `oods_samples`, and
  `+192` in `queries_values`;
- total positive grouped-field overhang: `1,536` typed bytes;
- projected single proof if the FRI-decommitment overhang disappeared:
  `40,844` typed bytes;
- projected single proof if all positive grouped-field deltas disappeared:
  `40,396` typed bytes;
- projected saving versus the two-proof frontier after removing all positive
  grouped-field deltas: `304` typed bytes (`0.7469%`);
- projected gap to NANOZK's paper-reported `6,900` byte d128 row:
  `33,496` typed bytes after removing all positive grouped-field deltas.

So the lifting/query overhangs are real and worth tracking, but they are not
the breakthrough by themselves.

## Interpretation

The native-adapter single proof still uses explicit `pcs_lifting_log_size = 19`
because the d8 attention interaction tree, adapter trace, and d128 MLP base tree
have different sizes. That heterogeneous-tree cost is visible, but it is no
longer the only positive delta.

The scale is the key point. Removing only the FRI-decommitment overhang would
move the object from `41,932` to `40,844` typed bytes, still larger than the
two-proof frontier. Removing every current positive grouped-field delta would
move it to `40,396` typed bytes, still `33,496` bytes above the `6,900` byte
external comparison row.

The next high-upside attack is therefore not only "make lifting cheaper." The
next useful research paths are:

1. adapter AIR compression without weakening value binding;
2. query-value reduction or opening-economics changes;
3. a different component boundary that removes more verifier-facing material;
4. only then another external comparison pass.

## Non-Claims

- This is not a regenerated proof after removing lifting overhead.
- This is not proof that the `1,536` positive grouped-field bytes are removable
  without verifier changes.
- This is not a NANOZK proof-size win.
- This is not a matched NANOZK workload or benchmark.
- This is not proof-size savings from native adapter AIR.
- This is not a full transformer block proof.
- This is not timing evidence.
- This is not recursion or proof-carrying data.
- This is not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.tsv`
- `scripts/zkai_native_attention_mlp_lifting_ablation_gate.py`
- `scripts/tests/test_zkai_native_attention_mlp_lifting_ablation_gate.py`

Source evidence pinned by hash:

- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-2026-05.json`

## Validation

```bash
python3 scripts/zkai_native_attention_mlp_lifting_ablation_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-lifting-ablation-2026-05.tsv
python3 -m py_compile scripts/zkai_native_attention_mlp_lifting_ablation_gate.py scripts/tests/test_zkai_native_attention_mlp_lifting_ablation_gate.py
python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_lifting_ablation_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
```
