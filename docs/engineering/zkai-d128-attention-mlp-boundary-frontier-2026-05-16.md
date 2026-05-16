# d128 Attention plus RMSNorm-MLP Boundary Frontier

Date: 2026-05-16

## Result

This PR pins the current d128 attention-plus-MLP frontier as a **two-proof
target**, not as one native transformer-block proof.

Decision:

`NARROW_CLAIM_ATTENTION_PLUS_DERIVED_MLP_BOUNDARY_FRONTIER_PINNED`

Result:

`GO_TWO_PROOF_TARGET_PINNED_NO_GO_SINGLE_NATIVE_ATTENTION_MLP_OBJECT_YET`

## Human Meaning

The latest MLP result is real: the attention-derived RMSNorm-MLP fused proof is
`22,576` local typed bytes and saves `36,768` typed bytes versus six separate
derived MLP-side proof objects.

Once we include the current d8 fused attention proof as a separate proof object,
the honest frontier is:

- d8 fused attention proof: `18,124` typed bytes
- derived d128 RMSNorm-MLP fused proof: `22,576` typed bytes
- current two-proof frontier: `40,700` typed bytes
- current two-proof JSON proof bytes: `116,258`

Against the same attention proof plus six separate derived MLP-side proof
objects, the route is still meaningfully smaller:

- separate attention fused + six MLP proofs: `77,468` typed bytes
- current two-proof route: `40,700` typed bytes
- typed saving: `36,768` bytes
- typed ratio: `0.525378x`

That is useful, but it is not enough for the breakthrough claim. The frontier is
still two proof objects. The next actual breakthrough gate is a native proof
object that puts attention arithmetic, lookup membership, the value adapter, and
the derived RMSNorm-MLP surface into one proof boundary.

## NANOZK Distance

NANOZK reports a `6.9 KB` d128 transformer-block row in the paper. This gate
does not claim a matched benchmark, but it records the distance honestly:

- paper-reported NANOZK row: `6,900` bytes
- current local typed two-proof frontier: `40,700` bytes
- remaining gap: `33,800` typed bytes
- reduction needed from the current two-proof target: `83.0467%`

This is why comparing the compact handoff artifact or the MLP-only proof against
NANOZK would be misleading. The current comparable object class for us is still
not a single block proof.

## Handoff Route

The compressed attention-derived statement-chain artifact is still interesting:

- source chain artifact: `14,624` bytes
- compressed handoff artifact: `2,559` bytes
- artifact ratio: `0.174986x`

But this artifact is not a STARK proof object. It is a verifier-facing handoff.
It is useful for architecture, not for proof-size comparison.

## Mechanism

The previous attribution gate found that `90.5135%` of the derived MLP fusion
saving comes from FRI plus trace decommitment plumbing. This frontier gate turns
that into the next engineering target: the way to exploit more saving is not to
delete verifier-required opening data from the MLP proof, but to make a larger
native boundary that shares proof-system plumbing across attention and MLP.

## Claim Boundary

This gate records:

- GO for the current value-connected two-proof target.
- GO for MLP-side fusion saving still mattering after a separate attention
  proof is included.
- GO for the compressed statement-chain handoff as an architecture artifact.
- NO-GO for claiming one native attention-plus-MLP proof object.
- NO-GO for claiming a NANOZK proof-size win.

## Non-Claims

- Not one native attention plus MLP proof object.
- Not a full transformer block proof.
- Not a NANOZK proof-size win.
- Not a matched NANOZK workload or benchmark.
- Not proof that the compressed handoff artifact is a proof object.
- Not timing evidence.
- Not recursion or proof-carrying data.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-2026-05.json`
- `docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-statement-chain-compression-2026-05.json`

## Validation

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-accounting-2026-05.json
python3 scripts/zkai_d128_attention_mlp_boundary_frontier_gate.py --write-json docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-attention-mlp-boundary-frontier-2026-05.tsv
python3 -m py_compile scripts/zkai_d128_attention_mlp_boundary_frontier_gate.py scripts/tests/test_zkai_d128_attention_mlp_boundary_frontier_gate.py
python3 -m unittest scripts.tests.test_zkai_d128_attention_mlp_boundary_frontier_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
