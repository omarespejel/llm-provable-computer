# zkAI d64 native relation witness oracle - 2026-05-01

## Question

Before writing the d64 Stwo AIR/export relation, can we define a fail-closed
reference oracle for the exact relation the AIR must encode?

## Result

GO for a relation-witness oracle. NO-GO-YET for an exact native Stwo proof.

The oracle consumes the same d64 proof-facing public instance landed in PR #350
and recomputes the canonical RMSNorm-SwiGLU-residual witness rows:

- width: `64`
- feed-forward dimension: `256`
- pinned `proof_system_version_required`: `stwo-rmsnorm-swiglu-residual-d64-v2`
- projection multiplication rows: `49,152`
- trace rows excluding the static activation table: `49,920`
- bounded activation table rows: `2,049`
- relation checks: `9`
- mutation suite: `16 / 16` rejected

This is the right intermediate artifact because it separates two risks:

- relation semantics: can we define exactly what rows must be checked?
- Stwo encoding: can we encode those row checks into AIR/proof form?

This PR only answers the first question.

## What The Oracle Checks

The oracle recomputes and binds:

- the proof-native parameter manifest and commitment,
- model/config/input/output public-instance commitments from the underlying vectors,
- normalization config commitment,
- activation lookup commitment,
- RMSNorm rows from the input vector and RMS scale vector,
- gate/value/down projection rows,
- bounded activation lookup rows,
- SwiGLU mix rows,
- residual output rows,
- statement/public-instance/backend-version bindings.

## Mutation Coverage

The checked mutation suite rejects relabeling or stale-evidence drift for:

- proof-native parameter commitment in the public instance,
- proof-native parameter commitment in the manifest,
- gate parameter root,
- RMS scale root,
- activation-table root,
- input commitment,
- output commitment,
- normalization config commitment,
- activation lookup commitment,
- public-instance commitment,
- statement commitment,
- backend version,
- relation row count,
- gate projection output sample,
- activation lookup output sample,
- residual output sample.

## Non-Claims

This is not:

- a Stwo proof,
- verifier-time evidence,
- AIR constraints,
- backend independence evidence,
- full transformer inference,
- `not proof that private witness rows already open to proof_native_parameter_commitment`.

## Next Step

Encode this relation oracle as native Stwo AIR/export rows that consume the same
public instance. The first useful native proof PR should prove a narrow slice or
record an exact blocker without weakening `rmsnorm-swiglu-residual-d64-v2`.

## Evidence

Machine-readable evidence:

- `docs/engineering/evidence/zkai-d64-native-relation-witness-oracle-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-relation-witness-oracle-2026-05.tsv`

Generator and tests:

- `scripts/zkai_d64_native_relation_witness_oracle.py`
- `scripts/tests/test_zkai_d64_native_relation_witness_oracle.py`

## Validation

```bash
just gate-fast

python3 -m py_compile \
  scripts/zkai_d64_native_relation_witness_oracle.py \
  scripts/tests/test_zkai_d64_native_relation_witness_oracle.py

python3 -m unittest \
  scripts.tests.test_zkai_d64_native_relation_witness_oracle \
  scripts.tests.test_zkai_d64_rmsnorm_swiglu_statement_fixture \
  scripts.tests.test_zkai_d64_stwo_vector_row_surface_probe

python3 scripts/zkai_d64_native_relation_witness_oracle.py \
  --write-json docs/engineering/evidence/zkai-d64-native-relation-witness-oracle-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-native-relation-witness-oracle-2026-05.tsv

just gate
```
