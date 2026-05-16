# zkAI Native Attention+MLP Single-Proof Route - 2026-05-16

## Result

This gate pins the next honest breakthrough target after the d128
attention-plus-MLP two-proof frontier.

Current state:

- current value-connected two-proof target: `40,700` local typed bytes
- separate d8 fused attention proof in that target: `18,124` typed bytes
- attention-derived d128 RMSNorm-MLP fused proof: `22,576` typed bytes
- value-connected chain rows: `199,553`
- MLP fused rows: `197,504`
- extra value-connected rows over MLP fused surface: `2,049`
- row ratio: `1.010374x`

The route budget is:

- a real native attention-plus-MLP proof object must verify locally and come in
  below `40,700` typed bytes to beat the current two-proof target;
- if it could preserve the current MLP fused proof surface, the floor would be
  `22,576` typed bytes, or `0.554693x` the current two-proof target;
- that hypothetical floor would remove `18,124` typed bytes from the current
  two-proof target, a `44.5307%` saving;
- that floor is still not a NANOZK win: it remains `15,676` typed bytes above
  NANOZK's paper-reported `6,900` byte d128 row, so it would still need a
  `69.4366%` reduction from the MLP-surface floor.

## Interpretation

This is a GO for building the native boundary route, not proof that the boundary
exists.

The important signal is that the value-connected attention-derived chain is only
`1.010374x` the current MLP fused row surface, while the current two-proof target
still pays a separate `18,124` typed-byte attention proof object. If a single
native boundary can share the proof plumbing instead of paying for two proof
objects, there is a real compression path to test.

The hard limit is also explicit: even a very good first native boundary is not
automatically NANOZK-comparable. It first needs a matched object class and a real
native proof object, then a separate external comparison pass.

## Non-Claims

- This is not a native attention plus MLP proof object.
- This is not proof that one native boundary will be `22,576` typed bytes.
- This is not a full transformer block proof.
- This is not a NANOZK proof-size win.
- This is not a matched NANOZK workload or benchmark.
- This is not timing evidence.
- This is not recursion or proof-carrying data.
- This is not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-route-2026-05.tsv`
- `scripts/zkai_native_attention_mlp_single_proof_route_gate.py`
- `scripts/tests/test_zkai_native_attention_mlp_single_proof_route_gate.py`

## Validation

```bash
python3 scripts/zkai_native_attention_mlp_single_proof_route_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-single-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-single-proof-route-2026-05.tsv
python3 -m py_compile scripts/zkai_native_attention_mlp_single_proof_route_gate.py scripts/tests/test_zkai_native_attention_mlp_single_proof_route_gate.py
python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_single_proof_route_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
