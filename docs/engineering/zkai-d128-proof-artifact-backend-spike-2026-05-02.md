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
- the partial `d=128` parameterized vector residual-add slice handle;
- the still-missing full `d=128` transformer-block proof object.

## Decision

**Bounded NO-GO for a full d128 transformer-block proof artifact on the current
backend route. Partial GO for d128 RMSNorm public rows, the
RMSNorm-to-projection bridge, d128 gate/value projection, d128 activation/SwiGLU,
and the parameterized d128 vector residual-add slice.**

The current first full-block blocker is:

> d128 RMSNorm public-row, RMSNorm-to-projection bridge, gate/value projection,
> activation/SwiGLU, and parameterized vector residual-add proof handles exist,
> but down-projection, native residual, and full transformer-block composition
> handles are still
> missing

This supersedes the earlier residual-only, RMSNorm-plus-residual, and
RMSNorm-bridge-plus-residual states. The repository can now prove five d128
slice surfaces. The residual-add slice is parameterized and not a native
residual proof. The repository still cannot report a full d128 block proof size,
verifier time, or relabeling suite.

## Result

| Field | Value |
| --- | --- |
| Decision | `NO_GO_D128_FULL_BLOCK_PROOF_ARTIFACT_SLICES_MISSING` |
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
| d128 parameterized residual-add route | `GO_PARTIAL_D128_RESIDUAL_ADD_ONLY` |
| Parameterized full-block route | `NO_GO_FULL_BLOCK_SLICES_MISSING` |
| RMSNorm proof roundtrip | locally constructed and verified by Rust tests |
| Bridge proof roundtrip | locally constructed and verified by Rust tests |
| Gate/value proof roundtrip | locally constructed and verified by Rust tests |
| Activation/SwiGLU proof roundtrip | locally constructed and verified by Rust tests |
| Parameterized residual-add proof roundtrip | locally constructed and verified by Rust tests |
| Checked-in proof bytes | no |
| Full-block metrics | blocked before full proof object |
| Mutation checks | `53 / 53` rejected |

## Backend-route classification

| Route | Status | Interpretation |
| --- | --- | --- |
| `existing_d64_slice_chain` | `GO_ANCHOR_ONLY` | The six-slice `d=64` proof chain exists and remains the working local anchor. It is not a `d=128` proof. |
| `direct_d128_native_modules` | `NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING` | d128 RMSNorm public-row, bridge, gate/value, and activation/SwiGLU native modules exist, but down-projection, native residual, composition, and the full-block verifier are missing. |
| `direct_d128_rmsnorm_public_row_air` | `GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY` | A real Stwo proof handle exists for the d128 RMSNorm public-row slice. |
| `direct_d128_rmsnorm_to_projection_bridge_air` | `GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY` | A real Stwo proof handle exists for the d128 handoff from RMSNorm-local rows to projection-input rows. |
| `direct_d128_gate_value_projection_air` | `GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY` | A real Stwo proof handle exists for the d128 gate/value projection multiplication rows that consume the bridge output. |
| `direct_d128_activation_swiglu_air` | `GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY` | A real Stwo proof handle exists for the d128 activation/SwiGLU rows that consume the gate/value output and emit hidden activation. |
| `lift_existing_d64_modules_by_metadata` | `NO_GO` | The d64 modules validate d64 width, target id, domains, proof versions, and log sizes. A metadata relabel cannot make them d128. |
| `parameterized_vector_residual_add_air` | `GO_PARTIAL_D128_RESIDUAL_ADD_ONLY` | A real parameterized Stwo proof handle exists for the d128 residual-add vector slice. |
| `parameterized_transformer_block_air` | `NO_GO_FULL_BLOCK_SLICES_MISSING` | Down-projection, native residual, and full block composition do not exist yet. |
| `d128_metrics_and_relabeling_suite` | `NO_GO_BLOCKED_BEFORE_PROOF_OBJECT` | Full-block proof size, verifier time, and relabeling resistance remain unreported until a full d128 proof object exists. |

## Working anchors

The current local anchors are:

- the checked `d=64` native slice chain: `rmsnorm_public_rows`,
  `rmsnorm_projection_bridge`, `gate_value_projection`, `activation_swiglu`,
  `down_projection`, and `residual_add`;
- the checked `d=128` RMSNorm public-row proof surface;
- the checked `d=128` RMSNorm-to-projection bridge proof surface;
- the checked `d=128` gate/value projection proof surface;
- the checked `d=128` activation/SwiGLU proof surface;
- the checked `d=128` residual-add vector proof surface.

The d64 anchor proves the receipt discipline and slice interfaces are not
fiction. The d128 RMSNorm, bridge, gate/value projection, activation/SwiGLU, and
residual-add anchors prove the backend can now clear five statement-bound d128
proof slices. They do not form a full d128 transformer-block proof.

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
- the d128 residual-add vector evidence before starting, including statement,
  public-instance, proof-native parameter, input, residual-delta, output, and row
  commitment recomputation;
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

No full-block `d=128` proof size, verifier time, proof-generation time, or
relabeling-resistance metric is reported here. Those numbers are blocked until:

- all required d128 slices exist;
- a full d128 proof artifact or composed receipt exists;
- a d128 verifier handle exists for the full statement;
- the statement envelope binds model/config/input/output/public-instance/
  proof-native-parameter/proof/verifying-key/setup/evidence-manifest/domain
  commitments, or explicit null-domain rules where a field is not applicable;
- relabeling tests reject drift in model, config, weights, input, output,
  public-instance, proof, verifying-key, setup, evidence-manifest, and
  verifier-domain fields.

The next concrete backend follow-up is the d128 down-projection proof handle:
consume `hidden_activation_commitment`, bind the deterministic down-projection
matrix, and emit a residual-delta commitment without reporting full-block
metrics.

## Non-claims

This result does **not** claim:

- a full local d128 transformer-block proof artifact;
- verifier-time evidence for a full d128 transformer block;
- proof-size evidence for a full d128 transformer block;
- recursive aggregation;
- backend independence evidence;
- a matched NANOZK or DeepProve benchmark;
- that d128 is impossible.

## Evidence

- Full-block backend spike JSON:
  `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json`
- Full-block backend spike TSV:
  `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv`
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
- d128 residual-add vector input JSON:
  `docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json`
- d128 residual-add vector input TSV:
  `docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv`
- Backend spike script:
  `scripts/zkai_d128_proof_artifact_backend_spike_gate.py`
- RMSNorm public-row input script:
  `scripts/zkai_d128_rmsnorm_public_row_proof_input.py`
- RMSNorm-to-projection bridge input script:
  `scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py`
- Gate/value projection input script:
  `scripts/zkai_d128_gate_value_projection_proof_input.py`
- Activation/SwiGLU input script:
  `scripts/zkai_d128_activation_swiglu_proof_input.py`
- Residual-add input script:
  `scripts/zkai_d128_vector_residual_add_proof_input.py`
- Tests:
  `scripts/tests/test_zkai_d128_proof_artifact_backend_spike_gate.py`
  `scripts/tests/test_zkai_d128_rmsnorm_public_row_proof_input.py`
  `scripts/tests/test_zkai_d128_rmsnorm_to_projection_bridge_input.py`
  `scripts/tests/test_zkai_d128_gate_value_projection_proof_input.py`
  `scripts/tests/test_zkai_d128_activation_swiglu_proof_input.py`
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

python3 scripts/zkai_d128_vector_residual_add_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv

python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_d128_rmsnorm_public_row_proof_input \
  scripts.tests.test_zkai_d128_rmsnorm_to_projection_bridge_input \
  scripts.tests.test_zkai_d128_gate_value_projection_proof_input \
  scripts.tests.test_zkai_d128_activation_swiglu_proof_input \
  scripts.tests.test_zkai_d128_vector_residual_add_proof_input \
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
