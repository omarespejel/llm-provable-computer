# Native d128 Block Proof-Object Route

Date: 2026-05-14

## Question

Can the current d128 block surface be claimed as one native or matched
transformer-block proof object?

## Decision

`NO_GO_EXECUTABLE_NATIVE_D128_BLOCK_OUTER_PROOF_BACKEND_MISSING`

This is a bounded no-go, but it is useful. The current route has strong
sub-results:

- a full six-slice d128 verifier-facing accumulator over `197,504` checked
  rows;
- a compressed attention-derived d128 statement-chain input contract of
  `2,559` bytes over `199,553` source relation rows;
- an external verifier-facing package of `4,752` bytes without the reusable VK;
- a matched evidence table that keeps the `4,752` byte package separate from
  NANOZK's paper-reported `6.9 KB` transformer block proof row.

None of those is the missing object. The missing object is an executable native
outer proof backend that proves the d128 slice-verifier checks and binds the
block proof-object public inputs.

## Result

| Surface | Status | Rows | Bytes | Boundary |
| --- | --- | ---: | ---: | --- |
| Six-slice d128 verifier accumulator | `GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR_NOT_OUTER_PROOF` | `197,504` | | binds receipts and public inputs, not slice verifier execution inside an outer proof |
| Smallest d128 two-slice outer target | `NO_GO_EXECUTABLE_TWO_SLICE_OUTER_PROOF_OBJECT_MISSING` | `256` | | blocked before metrics |
| Attention-derived compressed input contract | `GO_ATTENTION_DERIVED_D128_OUTER_PROOF_INPUT_CONTRACT_NOT_OUTER_PROOF` | `199,553` | `2,559` | compressed transcript, not proof-size evidence |
| External package without VK | `GO_COMPACT_VERIFIER_FACING_PACKAGE_NOT_NATIVE_PROOF` | | `4,752` | compact package signal, not a native proof |
| External package with VK | `GO_SELF_CONTAINED_VERIFIER_FACING_PACKAGE_WITH_VK_NOT_NATIVE_PROOF` | | `10,608` | includes reusable VK bytes; still packaging evidence, not a native proof |
| Native d128 block proof object | `NO_GO_EXECUTABLE_NATIVE_D128_BLOCK_OUTER_PROOF_BACKEND_MISSING` | | | required before proof-size, timing, or matched NANOZK claims |
| NANOZK reported block row | `SOURCE_BACKED_EXTERNAL_CONTEXT_NOT_LOCALLY_REPRODUCED` | | `6,900` | external context only |

Metadata for the rows above:

- Block target: `rmsnorm-swiglu-residual-d128-v1`; receipt version:
  `zkai-d128-block-receipt-v1`; required backend:
  `stwo-rmsnorm-swiglu-residual-d128-v1`.
- Slice backend versions:
  `stwo-d128-rmsnorm-public-row-air-proof-v3`,
  `stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1`,
  `stwo-d128-gate-value-projection-air-proof-v1`,
  `stwo-d128-activation-swiglu-air-proof-v1`,
  `stwo-d128-down-projection-air-proof-v1`,
  `stwo-d128-residual-add-air-proof-v1`.
- Step counts: six d128 slice receipts; `197,504` full-accumulator checked
  rows; `199,553` attention-derived source relation rows; `256` selected
  two-slice target rows; `13 / 13` route-gate mutations rejected.
- Package byte classes: `4,752` bytes without VK; `10,608` bytes with VK.
- Timing mode: no prover/verifier timing collected in this route. Timing
  fields remain null because the native d128 outer proof object is missing.
- Evidence paths: `docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.json`
  and `docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.tsv`.
- Reproduction command: the first command under `Reproduce` regenerates the
  JSON and TSV evidence from the checked source artifacts.

## Interpretation

The important human meaning is:

> We are close enough to see a compact verifier-facing package shape, but not
> close enough to claim a native block proof. The next real breakthrough gate is
> a native two-slice outer proof backend, not another wrapper around package
> bytes.

The `4,752` byte package remains a strong search signal because it is
`0.688696x` NANOZK's paper-reported `6.9 KB` block row. The route gate records
why that is not a proof-size win: the object classes differ, NANOZK is not
locally reproduced, and no native d128 block proof object exists yet.

## First Blocker

The repository still has no executable native outer proof backend that proves
the d128 slice-verifier checks and binds the block proof-object public inputs.
Allowed issue `#387` blocker category:
`no parameterized AIR route for the d128 vector-block surface`.

The two-slice target is already `NO-GO`, so the six-slice d128 block cannot be
claimed as one native proof object.

## Next Minimal Experiment

Implement the smallest native two-slice outer proof backend over
`rmsnorm_public_rows` and `rmsnorm_projection_bridge` verifier checks, with
public-input binding and relabeling rejection, before trying the full six-slice
d128 block.

## Non-Claims

- Not a native d128 transformer-block proof.
- Not a NANOZK proof-size win.
- Not a matched benchmark against NANOZK, Jolt Atlas, EZKL, DeepProve-1, RISC
  Zero, or Obelyzk.
- Not verifier-time or prover-time evidence.
- Not recursive aggregation or proof-carrying data.
- Not verification of the six Stwo slice proofs inside the external Groth16
  receipt.
- Not full transformer inference.
- Not exact real-valued Softmax, LayerNorm, or GELU.
- Not production-ready.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.tsv`
- Gate:
  `scripts/zkai_native_d128_block_proof_object_route_gate.py`
- Tests:
  `scripts/tests/test_zkai_native_d128_block_proof_object_route_gate.py`

## Reproduce

```bash
python3 scripts/zkai_native_d128_block_proof_object_route_gate.py \
  --write-json docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.tsv

python3 -m py_compile scripts/zkai_native_d128_block_proof_object_route_gate.py \
  scripts/tests/test_zkai_native_d128_block_proof_object_route_gate.py
python3 -m unittest scripts.tests.test_zkai_native_d128_block_proof_object_route_gate
python3 scripts/research_issue_lint.py --repo-root .
git diff --check
just gate-fast
just gate
```
