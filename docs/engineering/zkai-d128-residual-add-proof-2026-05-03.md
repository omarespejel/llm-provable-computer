# d128 Source-Bound Residual-Add Proof Gate

Date: 2026-05-03

## Question

Can the d128 transformer-block route consume the exact down-projection
`residual_delta_commitment`, add it to the original input activation, and emit a
statement-bound final output activation commitment without pretending the full
block is already composed?

## Decision

GO for the source-bound d128 residual-add proof slice.

This is not a GO for a full d128 transformer-block proof, recursion, proof-size
benchmark, or verifier-time benchmark. The remaining blocker is a real
recursive/proof-carrying aggregation object over the checked d128 block
receipt.

## Evidence

| Field | Value |
|---|---|
| Schema | `zkai-d128-residual-add-air-proof-input-v1` |
| Decision | `GO_INPUT_FOR_D128_RESIDUAL_ADD_AIR_PROOF` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| Rows | `128` |
| Source RMSNorm proof | `stwo-d128-rmsnorm-public-row-air-proof-v3` |
| Source RMSNorm statement commitment | `blake2b-256:de944915f2664ac7a893f4ba9a029323f7408eac58bf39170a0935d7832ccbd8` |
| Source down-projection proof | `stwo-d128-down-projection-air-proof-v1` |
| Source down-projection statement commitment | `blake2b-256:70f900b6d26fb33273c0123b4c4d6b7723e45612b2ca6fd9d536e613e8412599` |
| Source down-projection public-instance commitment | `blake2b-256:8a5fd95ef4fb5284374788c03861099a32ed7c2082cbdccd6bedd3d9b211f9e1` |
| Range policy | `input_activation_q8_semantic_bound_1024; residual_delta_and_output_signed_m31` |
| Input activation commitment | `blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78` |
| Residual delta commitment | `blake2b-256:d04770d7ab488a3e2366265ed45b039e590d1e03604c7954ac379ce0c37de2b2` |
| Residual delta remainder SHA-256 | `a99010fcd4f0898287b58960f979b086208ea7eff6ca51f0e8af827ec916ef3d` |
| Output activation commitment | `blake2b-256:869a0046bdaba3f6a7f98a3ffec618479c9dc91df2a342900c76f9ba53215fc1` |
| Residual-add row commitment | `blake2b-256:be931ba0fe63ea16d3dc2abb2fc2bafaa13ccf0db1f43fee9e734d5f2bf1100d` |
| Proof-native parameter commitment | `blake2b-256:f958da6fa72df8bc32873b3602a128ed35b65f9427e8627af0b39ff7e21b31bc` |
| Statement commitment | `blake2b-256:7324cabcfe588b50f9fd4c52d0654b1f110cb157b757dac643362a70010f0fb2` |

Machine-readable evidence:

- `docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json`
- `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv`

## What The Proof Slice Checks

The residual-add proof slice binds:

- the original d128 RMSNorm/input activation statement commitment;
- the down-projection statement and public-instance commitments;
- the exact quotient/remainder-bound residual delta commitment emitted by the
  d128 down-projection proof;
- the final output activation commitment;
- the residual-add row commitment;
- a proof-native parameter commitment over the target and source statement.

The important range-policy detail is that only the original input activation is
treated as q8-semantic bounded. The down-projection residual deltas and final
output activations are signed-M31 bounded, because the real d128 down-projection
residual deltas exceed the synthetic q8 residual-control range.

## Rejected Drift

The focused residual-add tests reject:

- tampered proof bytes;
- PCS config drift;
- extra proof commitment vector entries;
- public row tampering after proving;
- input q8 bound violations;
- residual-delta and output signed-M31 bound violations;
- residual-delta remainder drift;
- residual-delta commitment drift;
- source-commitment drift;
- relabeling an intermediate residual delta as the full output.

The backend spike gate now treats the d128 route as having six checked proof
handles plus a statement-bound block receipt composition gate over those
handles. It still records a bounded NO-GO for aggregated full-block proof
metrics because recursive aggregation or a single compressed verifier object
does not exist yet.

## Reproduce

```bash
python3 scripts/zkai_d128_residual_add_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_residual_add_proof_input

cargo +nightly-2025-07-14 test d128_native_residual_add_proof --lib --features stwo-backend

python3 scripts/zkai_d128_block_receipt_composition_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_block_receipt_composition_gate

python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate

python3 scripts/paper/paper_preflight.py --repo-root .

just gate-fast

just gate
```

## Next Step

Attempt recursive or proof-carrying aggregation of the checked d128 block
receipt. Do not report aggregated d128 proof size, verifier time, or external
comparison metrics until that proof object exists or a checked aggregation no-go
is recorded.
