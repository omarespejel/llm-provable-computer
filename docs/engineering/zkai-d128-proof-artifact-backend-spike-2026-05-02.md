# d128 proof artifact backend spike - 2026-05-02

## Question

Can the checked `d=128` RMSNorm-SwiGLU-residual target be routed through the
current local backend as a real proof artifact with a verifier handle and
relabeling tests?

This gate separates:

- the pinned `d=128` target shape;
- the working `d=64` native slice proof chain;
- the partial `d=128` RMSNorm public-row proof handle;
- the partial `d=128` RMSNorm-to-projection bridge proof handle;
- the partial `d=128` gate/value projection proof handle;
- the partial `d=128` activation/SwiGLU proof handle;
- the partial `d=128` down-projection proof handle;
- the source-bound `d=128` residual-add proof handle;
- the statement-bound `d=128` block receipt composition gate;
- the partial `d=128` parameterized vector residual-add slice handle;
- the still-missing recursive or single compressed `d=128` transformer-block
  proof object.

## Decision

**Bounded NO-GO for an aggregated full d128 transformer-block proof artifact on
the current backend route. GO for a statement-bound d128 block receipt composed
from six proof-backed slices. Partial GO remains for the individual d128
RMSNorm public rows, RMSNorm-to-projection bridge, gate/value projection,
activation/SwiGLU, down-projection, source-bound residual-add, and
parameterized vector residual-add slices.**

The current first full-block blocker is:

> a statement-bound d128 block receipt now composes six proof-backed slices, but
> recursive aggregation or a single compressed verifier object is still missing

This supersedes the earlier residual-only, RMSNorm-plus-residual,
RMSNorm-bridge-plus-residual, and six-slices-without-composition states. The
repository can now prove six d128 slice surfaces and bind them into one block
receipt. The repository still cannot report an aggregated d128 block proof size
or verifier time, because the recursive/single-proof object does not exist.

## Result

| Field | Value |
| --- | --- |
| Decision | `NO_GO_D128_AGGREGATED_FULL_BLOCK_PROOF_ARTIFACT_MISSING` |
| Result | `BOUNDED_NO_GO` |
| Issue | `#387` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| FF dimension | `512` |
| Required backend version | `stwo-rmsnorm-swiglu-residual-d128-v1` |
| d64 anchor | `GO_ANCHOR_ONLY` |
| Direct d128 native chain route | `NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING` |
| d128 RMSNorm public-row route | `GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY` |
| d128 RMSNorm-to-projection bridge route | `GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY` |
| d128 gate/value projection route | `GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY` |
| d128 activation/SwiGLU route | `GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY` |
| d128 down-projection route | `GO_PARTIAL_D128_DOWN_PROJECTION_ONLY` |
| d128 source-bound residual-add route | `GO_D128_SOURCE_BOUND_RESIDUAL_ADD_ONLY` |
| d128 block receipt composition route | `GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE` |
| d128 parameterized residual-add route | `GO_PARTIAL_D128_RESIDUAL_ADD_ONLY` |
| Parameterized full-block route | `NO_GO_AGGREGATED_PROOF_OBJECT_MISSING` |
| RMSNorm proof roundtrip | locally constructed and verified by Rust tests |
| Bridge proof roundtrip | locally constructed and verified by Rust tests |
| Gate/value proof roundtrip | locally constructed and verified by Rust tests |
| Activation/SwiGLU proof roundtrip | locally constructed and verified by Rust tests |
| Down-projection proof roundtrip | locally constructed and verified by Rust tests over `65,536` checked multiplication rows |
| Source-bound residual-add proof roundtrip | locally constructed and verified by Rust tests |
| Block receipt composition | `197,504` checked rows, `20 / 20` receipt mutations rejected |
| Parameterized residual-add proof roundtrip | locally constructed and verified by Rust tests |
| Checked-in proof bytes | no |
| Full-block proof metrics | blocked before aggregated proof object |
| Mutation checks | `100 / 100` rejected |

## Backend-route classification

| Route | Status | Interpretation |
| --- | --- | --- |
| `existing_d64_slice_chain` | `GO_ANCHOR_ONLY` | The six-slice `d=64` proof chain exists and remains the working local anchor. It is not a `d=128` proof. |
| `direct_d128_native_modules` | `NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING` | d128 RMSNorm public-row, bridge, gate/value, activation/SwiGLU, down-projection, and source-bound residual-add native modules exist, but a direct native full-block verifier is still missing. |
| `direct_d128_rmsnorm_public_row_air` | `GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY` | A real Stwo proof handle exists for the d128 RMSNorm public-row slice. |
| `direct_d128_rmsnorm_to_projection_bridge_air` | `GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY` | A real Stwo proof handle exists for the d128 handoff from RMSNorm-local rows to projection-input rows. |
| `direct_d128_gate_value_projection_air` | `GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY` | A real Stwo proof handle exists for the d128 gate/value projection multiplication rows that consume the bridge output. |
| `direct_d128_activation_swiglu_air` | `GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY` | A real Stwo proof handle exists for the d128 activation/SwiGLU rows that consume the gate/value output and emit hidden activation. |
| `direct_d128_down_projection_air` | `GO_PARTIAL_D128_DOWN_PROJECTION_ONLY` | A real Stwo proof handle exists for the d128 down-projection rows that consume hidden activation and emit an exact residual-delta quotient/remainder commitment. |
| `direct_d128_residual_add_air` | `GO_D128_SOURCE_BOUND_RESIDUAL_ADD_ONLY` | A real Stwo proof handle exists for source-bound d128 residual addition, consuming the down-projection residual delta and emitting the final output activation commitment. |
| `lift_existing_d64_modules_by_metadata` | `NO_GO` | The d64 modules validate d64 width, target id, domains, proof versions, and log sizes. A metadata relabel cannot make them d128. |
| `parameterized_vector_residual_add_air` | `GO_PARTIAL_D128_RESIDUAL_ADD_ONLY` | A real parameterized Stwo proof handle exists for the d128 residual-add vector slice. |
| `parameterized_transformer_block_air` | `NO_GO_AGGREGATED_PROOF_OBJECT_MISSING` | A block receipt exists, but recursive aggregation or one compressed verifier object does not. |
| `d128_block_receipt_composition` | `GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE` | The six checked d128 slice handles compose into one statement-bound receipt over `197,504` checked rows. |
| `d128_metrics_and_relabeling_suite` | `NO_GO_BLOCKED_BEFORE_PROOF_OBJECT` | Full-block proof size and verifier time remain unreported until an aggregated d128 proof object exists. |

## Working anchors

The current local anchors are:

- the checked `d=64` native slice chain: `rmsnorm_public_rows`,
  `rmsnorm_projection_bridge`, `gate_value_projection`, `activation_swiglu`,
  `down_projection`, and `residual_add`;
- the checked `d=128` RMSNorm public-row proof surface;
- the checked `d=128` RMSNorm-to-projection bridge proof surface;
- the checked `d=128` gate/value projection proof surface;
- the checked `d=128` activation/SwiGLU proof surface;
- the checked `d=128` down-projection proof surface;
- the checked source-bound `d=128` residual-add proof surface;
- the checked `d=128` block receipt composition gate;
- the checked `d=128` residual-add vector proof surface.

The d64 anchor proves the receipt discipline and slice interfaces are not
fiction. The d128 RMSNorm, bridge, gate/value projection, activation/SwiGLU,
down-projection, and residual-add anchors prove the backend can now clear six
statement-bound d128 proof slices. The block receipt gate proves those six
slices compose into one statement-bound receipt. They do not form a recursive or
single compressed d128 transformer-block proof.

## Why this closes a fooling-ourselves gap

The gate now validates:

- the d128 target evidence before starting;
- the d64 composition anchor before starting;
- the d128 RMSNorm public-row evidence before starting, including statement,
  public-instance, proof-native parameter, normalization-config, input,
  scale-tree, and output-row commitment recomputation;
- the d128 RMSNorm-to-projection bridge evidence before starting, including
  source statement binding, source RMSNorm output commitment recomputation,
  projection-input commitment recomputation, public-instance recomputation,
  proof-native parameter recomputation, and relabel rejection against the full
  output-activation commitment;
- the d128 gate/value projection evidence before starting, including source
  bridge binding, projection-input commitment recomputation, gate/value matrix
  root recomputation, multiplication-row commitment recomputation, gate/value
  output commitment recomputation, public-instance recomputation,
  proof-native parameter recomputation, and relabel rejection against the full
  output-activation commitment;
- the d128 activation/SwiGLU evidence before starting, including source
  gate/value statement and public-instance binding, source gate/value output
  commitment recomputation, activation lookup commitment recomputation,
  activation output commitment recomputation, hidden activation commitment
  recomputation, row commitment recomputation, statement/public-instance
  recomputation, proof-native parameter recomputation, and relabel rejection
  against the full output-activation commitment;
- the d128 down-projection evidence before starting, including source
  activation statement/public-instance binding, source hidden-activation
  commitment recomputation, down-matrix-root recomputation,
  multiplication-row commitment recomputation, exact residual-delta
  quotient/remainder/divisor commitment recomputation, range-policy validation,
  statement/public-instance recomputation, proof-native parameter recomputation,
  and relabel rejection against the full
  output-activation commitment;
- the d128 residual-add vector evidence before starting, including statement,
  public-instance, proof-native parameter, input, residual-delta, output, and row
  commitment recomputation;
- the d128 source-bound residual-add evidence before starting, including
  RMSNorm source-statement binding, down-projection statement/public-instance
  binding, exact residual-delta quotient/remainder binding, input/output
  commitment recomputation, and relabel rejection;
- the d128 block receipt composition evidence before starting, including source
  file hashes, source payload hashes, six-slice ordering, inter-slice
  commitment edges, block statement recomputation, block receipt recomputation,
  and `20 / 20` receipt mutation rejection;
- that the remaining expected d128 native modules and exports are still absent;
- that the d64 modules remain hard-coded to d64 width/domain surfaces;
- that the partial routes are GO without promoting them to a full-block proof;
- that metric smuggling and route-promotion mutations are rejected.

## Toolchain note

The Stwo backend requires the repository's pinned nightly toolchain:
`cargo +nightly-2025-07-14`. A stable-channel invocation fails inside upstream
`stwo` feature gates before reaching repository proof code, so stable failure is
not evidence about the d128 route.

## Metrics policy

No aggregated full-block `d=128` proof size, verifier time, proof-generation
time, or compressed-proof relabeling-resistance metric is reported here. Those
numbers are blocked until:

- an aggregated d128 proof artifact exists;
- a d128 verifier handle exists for the aggregated full statement;
- the statement envelope binds model/config/input/output/public-instance/
  proof-native-parameter/proof/verifying-key/setup/evidence-manifest/domain
  commitments, or explicit null-domain rules where a field is not applicable;
- relabeling tests reject drift in model, config, weights, input, output,
  public-instance, proof, verifying-key, setup, evidence-manifest, and
  verifier-domain fields.

The concrete backend follow-up is now recorded in
`docs/engineering/zkai-d128-aggregated-proof-object-feasibility-2026-05-03.md`.
That gate classifies the checked block receipt as a valid aggregation target but
records a bounded no-go for claiming a recursive, PCD, or one compressed proof
object today. Until an outer proof object and verifier handle exist, report the
d128 result as a statement-bound receipt over six proof-backed slices, not as
one compressed proof.

## Non-claims

This result does **not** claim:

- an aggregated local d128 transformer-block proof artifact;
- verifier-time evidence for an aggregated d128 transformer block proof;
- proof-size evidence for an aggregated d128 transformer block proof;
- recursive aggregation;
- backend independence evidence;
- a matched NANOZK or DeepProve benchmark;
- that d128 is impossible.

## Evidence

- Full-block backend spike JSON:
  `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json`
- Full-block backend spike TSV:
  `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv`
- d128 block receipt composition JSON:
  `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json`
- d128 block receipt composition TSV:
  `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv`
- d128 RMSNorm public-row input JSON:
  `docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json`
- d128 RMSNorm public-row input TSV:
  `docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.tsv`
- d128 RMSNorm-to-projection bridge input JSON:
  `docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json`
- d128 RMSNorm-to-projection bridge input TSV:
  `docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv`
- d128 gate/value projection input JSON:
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json`
- d128 gate/value projection input TSV:
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.tsv`
- d128 activation/SwiGLU input JSON:
  `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json`
- d128 activation/SwiGLU input TSV:
  `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.tsv`
- d128 down-projection input JSON:
  `docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json`
- d128 down-projection input TSV:
  `docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.tsv`
- d128 source-bound residual-add input JSON:
  `docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json`
- d128 source-bound residual-add input TSV:
  `docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.tsv`
- d128 residual-add vector input JSON:
  `docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json`
- d128 residual-add vector input TSV:
  `docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv`
- Backend spike script:
  `scripts/zkai_d128_proof_artifact_backend_spike_gate.py`
- Block receipt composition script:
  `scripts/zkai_d128_block_receipt_composition_gate.py`
- RMSNorm public-row input script:
  `scripts/zkai_d128_rmsnorm_public_row_proof_input.py`
- RMSNorm-to-projection bridge input script:
  `scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py`
- Gate/value projection input script:
  `scripts/zkai_d128_gate_value_projection_proof_input.py`
- Activation/SwiGLU input script:
  `scripts/zkai_d128_activation_swiglu_proof_input.py`
- Down-projection input script:
  `scripts/zkai_d128_down_projection_proof_input.py`
- Residual-add input script:
  `scripts/zkai_d128_residual_add_proof_input.py`
- Parameterized residual-add input script:
  `scripts/zkai_d128_vector_residual_add_proof_input.py`
- Tests:
  `scripts/tests/test_zkai_d128_proof_artifact_backend_spike_gate.py`
  `scripts/tests/test_zkai_d128_block_receipt_composition_gate.py`
  `scripts/tests/test_zkai_d128_rmsnorm_public_row_proof_input.py`
  `scripts/tests/test_zkai_d128_rmsnorm_to_projection_bridge_input.py`
  `scripts/tests/test_zkai_d128_gate_value_projection_proof_input.py`
  `scripts/tests/test_zkai_d128_activation_swiglu_proof_input.py`
  `scripts/tests/test_zkai_d128_down_projection_proof_input.py`
  `scripts/tests/test_zkai_d128_residual_add_proof_input.py`
  `scripts/tests/test_zkai_d128_vector_residual_add_proof_input.py`

## Reproduce

```bash
python3 scripts/zkai_d128_rmsnorm_public_row_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.tsv

python3 scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py \
  --write-json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv

python3 scripts/zkai_d128_gate_value_projection_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.tsv

python3 scripts/zkai_d128_activation_swiglu_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.tsv

python3 scripts/zkai_d128_down_projection_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.tsv

python3 scripts/zkai_d128_residual_add_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.tsv

python3 scripts/zkai_d128_vector_residual_add_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv

python3 scripts/zkai_d128_block_receipt_composition_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv

python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_d128_rmsnorm_public_row_proof_input \
  scripts.tests.test_zkai_d128_rmsnorm_to_projection_bridge_input \
  scripts.tests.test_zkai_d128_gate_value_projection_proof_input \
  scripts.tests.test_zkai_d128_activation_swiglu_proof_input \
  scripts.tests.test_zkai_d128_down_projection_proof_input \
  scripts.tests.test_zkai_d128_residual_add_proof_input \
  scripts.tests.test_zkai_d128_vector_residual_add_proof_input \
  scripts.tests.test_zkai_d128_block_receipt_composition_gate \
  scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate

cargo +nightly-2025-07-14 test \
  d128_native_rmsnorm_public_row_proof \
  --lib \
  --features stwo-backend

cargo +nightly-2025-07-14 test \
  d128_native_rmsnorm_to_projection_bridge_proof \
  --lib \
  --features stwo-backend

cargo +nightly-2025-07-14 test \
  d128_native_gate_value_projection_proof \
  --lib \
  --features stwo-backend

cargo +nightly-2025-07-14 test \
  d128_native_activation_swiglu_proof \
  --lib \
  --features stwo-backend

cargo +nightly-2025-07-14 test \
  d128_native_down_projection_proof \
  --lib \
  --features stwo-backend

cargo +nightly-2025-07-14 test \
  d128_native_residual_add_proof \
  --lib \
  --features stwo-backend

cargo +nightly-2025-07-14 test \
  zkai_vector_block_residual_add_proof \
  --lib \
  --features stwo-backend

cargo +nightly-2025-07-14 test \
  --lib \
  stwo_backend::d64_native_rmsnorm_air_feasibility::tests::d64_rmsnorm_air_feasibility_records_existing_component_no_go \
  --features stwo-backend \
  -- \
  --nocapture \
  --exact

just gate-fast
python3 scripts/paper/paper_preflight.py --repo-root .
just gate
```
