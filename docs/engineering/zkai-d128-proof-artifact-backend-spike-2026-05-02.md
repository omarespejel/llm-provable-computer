# d128 proof artifact backend spike - 2026-05-02

## Question

Can the checked `d=128` RMSNorm-SwiGLU-residual target be routed through the
current local backend as a real proof artifact with a verifier handle and
relabeling tests?

This gate starts from the comparator-target result and asks the implementation
question directly. It separates:

- the pinned `d=128` target shape;
- the working `d=64` native slice proof chain;
- the missing backend route for a real `d=128` proof object.

## Decision

**Bounded NO-GO for the current backend route.**

The first blocker is:

> no parameterized d128 vector-block AIR/prover/verifier handle; current native
> proof modules are d64 target/domain/width hard-coded and no d128 native module
> exports exist

This does not invalidate the d128 target. It means the target is still a proof
artifact backlog item, not a metric-producing result.

## Result

| Field | Value |
| --- | --- |
| Decision | `NO_GO_D128_PROOF_ARTIFACT_PARAMETERIZED_AIR_MISSING` |
| Result | `BOUNDED_NO_GO` |
| Issue | `#387` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| FF dimension | `512` |
| Required backend version | `stwo-rmsnorm-swiglu-residual-d128-v1` |
| d64 anchor | `GO_ANCHOR_ONLY` |
| Direct d128 module route | `NO_GO` |
| Parameterized vector-block route | `NO_GO_FIRST_BLOCKER` |
| Metrics | blocked before proof object |
| Mutation checks | `14 / 14` rejected |

## Backend-route classification

| Route | Status | Interpretation |
| --- | --- | --- |
| `existing_d64_slice_chain` | `GO_ANCHOR_ONLY` | The six-slice `d=64` proof chain exists and remains the working local anchor. It is not a `d=128` proof. |
| `direct_d128_native_modules` | `NO_GO` | No `src/stwo_backend/d128_native_*` proof modules or exported d128 prove/verify handles exist. |
| `lift_existing_d64_modules_by_metadata` | `NO_GO` | The d64 modules validate d64 width, target id, domains, proof versions, and log sizes. A metadata relabel cannot make them d128. |
| `parameterized_vector_block_air` | `NO_GO_FIRST_BLOCKER` | The repository lacks a parameterized vector-block AIR/prover/verifier surface. |
| `d128_metrics_and_relabeling_suite` | `NO_GO_BLOCKED_BEFORE_PROOF_OBJECT` | Proof size, verifier time, and relabeling resistance remain unreported until a d128 proof object exists. |

## Working anchor

The current local anchor is the checked `d=64` native slice chain:

- `rmsnorm_public_rows`;
- `rmsnorm_projection_bridge`;
- `gate_value_projection`;
- `activation_swiglu`;
- `down_projection`;
- `residual_add`.

The composition gate records six slices and `49600` checked rows. That anchor is
useful because it proves the receipt discipline and slice interfaces are not
fiction. It does not provide a direct scale-up route to `d=128`.

## Why this closes a fooling-ourselves gap

Before this gate, the repository had a target-spec NO-GO saying "a d128 proof
artifact is missing." This gate makes the missing route executable:

- it validates the d128 target evidence before starting;
- it validates the d64 composition anchor before starting;
- it checks that the expected d128 modules and exported symbols are absent;
- it checks that the current d64 modules are hard-coded to d64 width/domain
  surfaces;
- it fails closed if a future branch adds a d128 or parameterized route while
  this evidence still claims NO-GO;
- it rejects metric smuggling and route-promotion mutations.

## Toolchain note

The Stwo backend requires the repository's pinned nightly toolchain:
`cargo +nightly-2025-07-14`. A stable-channel invocation fails inside upstream
`stwo` feature gates before reaching repository proof code, so stable failure is
not evidence about the d128 route.

## Metrics policy

No local `d=128` proof size, verifier time, proof-generation time, or relabeling
resistance is reported here. Those numbers are blocked until:

- a local d128 proof artifact exists;
- a d128 verifier handle exists;
- the statement envelope binds model/config/input/output/parameter/proof/verifier
  domain commitments;
- relabeling tests reject drift in model, config, weights, input, output, proof,
  verifying key, setup, and verifier-domain fields.

## Non-claims

This result does **not** claim:

- a local d128 proof artifact;
- verifier-time evidence for d128;
- proof-size evidence for d128;
- recursive aggregation;
- backend independence evidence;
- a matched NANOZK or DeepProve benchmark;
- that d128 is impossible.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv`
- Script:
  `scripts/zkai_d128_proof_artifact_backend_spike_gate.py`
- Tests:
  `scripts/tests/test_zkai_d128_proof_artifact_backend_spike_gate.py`

## Reproduce

```bash
python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate

cargo +nightly-2025-07-14 test --lib d64 --features stwo-backend -- --nocapture

python3 scripts/paper/paper_preflight.py --repo-root .
```
