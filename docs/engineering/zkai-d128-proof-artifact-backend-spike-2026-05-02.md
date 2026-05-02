# d128 proof artifact backend spike - 2026-05-02

## Question

Can the checked `d=128` RMSNorm-SwiGLU-residual target be routed through the
current local backend as a real proof artifact with a verifier handle and
relabeling tests?

This gate starts from the comparator-target result and asks the implementation
question directly. It separates:

- the pinned `d=128` target shape;
- the working `d=64` native slice proof chain;
- the new partial `d=128` parameterized residual-add proof handle;
- the still-missing full `d=128` transformer-block proof object.

## Decision

**Bounded NO-GO for a full d128 transformer-block proof artifact on the current
backend route. Partial GO for a parameterized d128 residual-add vector slice.**

The current first full-block blocker is:

> a parameterized d128 residual-add vector proof handle exists, but
> parameterized RMSNorm, projection, activation, down-projection, and full
> transformer-block composition handles are still missing

This supersedes the earlier absolute blocker that no parameterized vector-block
route existed. The repository can now prove one d128 vector slice. It still
cannot report a full d128 block proof size, verifier time, or relabeling suite.

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
| Direct d128 native module route | `NO_GO` |
| Parameterized residual-add route | `GO_PARTIAL_D128_RESIDUAL_ADD_ONLY` |
| Parameterized full-block route | `NO_GO_FULL_BLOCK_SLICES_MISSING` |
| Residual-add proof roundtrip | locally constructed and verified by Rust tests |
| Checked-in residual-add proof bytes | no |
| Full-block metrics | blocked before full proof object |
| Mutation checks | `14 / 14` rejected |

## Backend-route classification

| Route | Status | Interpretation |
| --- | --- | --- |
| `existing_d64_slice_chain` | `GO_ANCHOR_ONLY` | The six-slice `d=64` proof chain exists and remains the working local anchor. It is not a `d=128` proof. |
| `direct_d128_native_modules` | `NO_GO` | No `src/stwo_backend/d128_native_*` proof modules or exported d128 prove/verify handles exist. |
| `lift_existing_d64_modules_by_metadata` | `NO_GO` | The d64 modules validate d64 width, target id, domains, proof versions, and log sizes. A metadata relabel cannot make them d128. |
| `parameterized_vector_residual_add_air` | `GO_PARTIAL_D128_RESIDUAL_ADD_ONLY` | A real parameterized Stwo proof handle exists for the d128 residual-add vector slice. |
| `parameterized_transformer_block_air` | `NO_GO_FULL_BLOCK_SLICES_MISSING` | The other d128 slices and full block composition do not exist yet. |
| `d128_metrics_and_relabeling_suite` | `NO_GO_BLOCKED_BEFORE_PROOF_OBJECT` | Full-block proof size, verifier time, and relabeling resistance remain unreported until a full d128 proof object exists. |

## Working anchors

The current local anchors are:

- the checked `d=64` native slice chain: `rmsnorm_public_rows`,
  `rmsnorm_projection_bridge`, `gate_value_projection`, `activation_swiglu`,
  `down_projection`, and `residual_add`;
- the checked `d=128` parameterized residual-add vector proof surface.

The d64 anchor proves the receipt discipline and slice interfaces are not
fiction. The d128 residual-add anchor proves the parameterized vector proof route
can clear width `128` for one slice. Its proof object is constructed and
verified by Rust tests; the checked-in evidence records deterministic public
inputs and route classification rather than durable proof bytes. Neither anchor
is a full d128 transformer-block proof.

## Why this closes a fooling-ourselves gap

The previous gate made the missing route executable. This update makes the
state more precise:

- it validates the d128 target evidence before starting;
- it validates the d64 composition anchor before starting;
- it validates the full d128 residual-add vector evidence before starting,
  including statement, public-instance, and proof-native parameter commitment
  recomputation;
- it checks that the expected direct d128 native modules and exports are still
  absent;
- it checks that the current d64 modules remain hard-coded to d64
  width/domain surfaces;
- it records the partial parameterized route as a GO without promoting it to a
  full-block proof;
- it rejects metric smuggling and route-promotion mutations.

## Toolchain note

The Stwo backend requires the repository's pinned nightly toolchain:
`cargo +nightly-2025-07-14`. A stable-channel invocation fails inside upstream
`stwo` feature gates before reaching repository proof code, so stable failure is
not evidence about the d128 route.

## Metrics policy

No full-block `d=128` proof size, verifier time, proof-generation time, or
relabeling resistance is reported here. Those numbers are blocked until:

- all required d128 slices exist;
- a full d128 proof artifact or composed receipt exists;
- a d128 verifier handle exists for the full statement;
- the statement envelope binds model/config/input/output/parameter/proof/verifier
  domain commitments;
- relabeling tests reject drift in model, config, weights, input, output, proof,
  verifying key, setup, and verifier-domain fields.

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
- d128 residual-add vector input JSON:
  `docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json`
- d128 residual-add vector input TSV:
  `docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv`
- Backend spike script:
  `scripts/zkai_d128_proof_artifact_backend_spike_gate.py`
- Residual-add input script:
  `scripts/zkai_d128_vector_residual_add_proof_input.py`
- Tests:
  `scripts/tests/test_zkai_d128_proof_artifact_backend_spike_gate.py`
  `scripts/tests/test_zkai_d128_vector_residual_add_proof_input.py`

## Reproduce

```bash
python3 scripts/zkai_d128_vector_residual_add_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv

python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_d128_vector_residual_add_proof_input \
  scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate

cargo +nightly-2025-07-14 test \
  zkai_vector_block_residual_add_proof \
  --lib \
  --features stwo-backend

cargo +nightly-2025-07-14 test \
  --lib \
  stwo_backend::d64_native_rmsnorm_air_feasibility::tests::d64_rmsnorm_air_feasibility_records_existing_component_no_go \
  --features stwo-backend \
  -- --nocapture --exact

just gate-fast

python3 scripts/paper/paper_preflight.py --repo-root .

just gate
```
