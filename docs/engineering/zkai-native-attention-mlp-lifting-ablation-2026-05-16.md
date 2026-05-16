# zkAI Native Attention+MLP Lifting Ablation - 2026-05-16

## Result

This gate checks whether the explicit PCS lifting cost explains why the first
native attention-plus-MLP single proof barely beats the two-proof frontier.

The answer is a narrow NO-GO:

- checked single proof: `40,668` local typed bytes;
- previous two-proof frontier: `40,700` local typed bytes;
- current saving: `32` typed bytes;
- only positive typed-field delta in the single proof:
  `+640` bytes in `fri_decommitments`;
- projected single proof if that entire overhang disappeared: `40,028` typed
  bytes;
- projected saving versus the two-proof frontier: `672` typed bytes
  (`1.6511%`);
- projected gap to NANOZK's paper-reported `6,900` byte d128 row:
  `33,128` typed bytes;
- projected reduction still needed from the ablated object: `82.7621%`.

So the lifting overhang is real and worth tracking, but it is not the
breakthrough by itself.

## Interpretation

The first single proof used explicit `pcs_lifting_log_size = 19` because the d8
attention interaction tree and the d128 MLP base tree have very different
sizes. That heterogeneous-tree cost shows up as the only group where the single
proof is larger than the two-proof frontier.

But the scale is the key point. The overhang is `640` typed bytes. Removing it
completely would move the object from `40,668` to `40,028` typed bytes, not
toward the `6,900` byte external comparison row.

The next high-upside attack is therefore not only "make lifting cheaper." The
next useful research paths are:

1. native AIR for the attention-output-to-d128-input adapter;
2. query-value reduction or opening-economics changes;
3. a different component boundary that removes more verifier-facing material;
4. only then another external comparison pass.

## Non-Claims

- This is not a regenerated proof after removing lifting overhead.
- This is not proof that the `640` bytes are removable without verifier changes.
- This is not a NANOZK proof-size win.
- This is not a matched NANOZK workload or benchmark.
- This is not native AIR proof of the attention-output-to-d128-input adapter.
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
