# d128 RMSNorm-to-projection bridge proof - 2026-05-02

## Question

Can the checked `d=128` RMSNorm public-row output be consumed by a second native
Stwo proof slice that re-emits the same vector under the projection-input domain,
without relabeling it as a full block output?

## Decision

**GO for a d128 RMSNorm-to-projection bridge slice.**

This is a real Stwo AIR/prover/verifier surface for `128` bridge rows. It
consumes the checked d128 RMSNorm output-row commitment, proves equality between
RMSNorm-local rows and projection-input rows, and emits a new domain-separated
projection-input row commitment. It is intentionally not a gate/value projection
proof, activation proof, down-projection proof, residual proof, or full d128
transformer-block proof.

## Result

| Field | Value |
| --- | --- |
| Input schema | `zkai-d128-rmsnorm-to-projection-bridge-air-proof-input-v1` |
| Input decision | `GO_INPUT_FOR_D128_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF` |
| Proof decision | `GO_D128_RMSNORM_TO_PROJECTION_INPUT_BRIDGE_AIR_PROOF` |
| Rust proof version | `stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1` |
| Statement version | `zkai-d128-rmsnorm-to-projection-bridge-statement-v1` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| Row count | `128` |
| Source RMSNorm output row commitment | `blake2b-256:d8b6f5e54e874e46624cb9c9987dbcc42db2aa9fc83d4d7230294fbbccb88b87` |
| Projection input row commitment | `blake2b-256:84fd5765c9ed8d21ced01ace55c5f95b34f16d159864c1ec20d9a0cd4cd67b17` |
| Statement commitment | `blake2b-256:fe0a9e59560611ed5220fd25b082806977a66a7032f457fce2cd5c3a41856728` |
| Public instance commitment | `blake2b-256:ca94d85cb0ed5e9001cd3def00817060745fa015bd8dda5f08732944f7418383` |
| Proof-native parameter commitment | `blake2b-256:ff31d2b502dac1e7d9f9cca69c4bd31e93e068dab49884e61a300a99389d58c1` |
| Proof handle | `prove_zkai_d128_rmsnorm_to_projection_bridge_envelope` |
| Verifier handle | `verify_zkai_d128_rmsnorm_to_projection_bridge_envelope` |
| Input parser | `zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str` |
| Evidence JSON | `docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json` |
| Evidence TSV | `docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv` |

## Relation

For each checked coordinate, the AIR verifies the bridge relation:

```text
rmsnorm_normed_q8[i] = projection_input_q8[i]
```

The verifier recomputes the source RMSNorm output-row commitment and the
projection-input row commitment before proof verification. The statement also
binds:

- source RMSNorm statement commitment;
- source RMSNorm public-instance commitment;
- source RMSNorm public-row proof version;
- source and destination row domains;
- target commitment;
- required backend version;
- verifier domain;
- public-instance commitment;
- proof-native parameter commitment.

The bridge rejects attempts to relabel the projection-input row commitment as
the pinned full output-activation commitment. That guard is narrow: it only says
this bridge is not a final block-output proof.

## Non-claims

This result does **not** claim:

- a full d128 transformer-block proof;
- gate, value, down-projection, activation, SwiGLU, or residual correctness;
- binding of the full d128 output-activation commitment;
- verifier-time or proof-size evidence for the full d128 target;
- recursive aggregation.

## Why This Matters

Before this result, the d128 route had a normalization proof and a residual-add
proof, but it did not yet prove the handoff between adjacent slice domains. This
bridge closes the first consumption step: RMSNorm-local rows can now be accepted
as projection-input rows only when the source commitment, destination commitment,
statement, public instance, proof-native parameters, row equality relation, and
proof bytes all agree.

The real arithmetic surface after the bridge has since landed as
`docs/engineering/zkai-d128-gate-value-projection-proof-2026-05-02.md`: it
consumes `projection_input_row_commitment` and produces a gate/value output
commitment. The next backend blocker is now the activation/SwiGLU slice that
consumes that gate/value output.

## Reproduce

```bash
python3 scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py \
  --write-json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv

just gate-fast

python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_to_projection_bridge_input

cargo +nightly-2025-07-14 test \
  d128_native_rmsnorm_to_projection_bridge_proof \
  --lib \
  --features stwo-backend

just gate
```
