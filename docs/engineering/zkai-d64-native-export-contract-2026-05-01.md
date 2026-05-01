# zkAI d64 native export contract - 2026-05-01

## Question

Can the Rust/Stwo side consume the checked d64 relation-oracle evidence as a
strict native export contract before we attempt a full AIR/proof implementation?

## Result

GO for a native export contract. NO-GO-YET for native AIR constraints or an
exact Stwo proof.

The Rust module `src/stwo_backend/d64_native_export_contract.rs` ingests the
checked relation-oracle JSON and exports a pinned
`ZkAiD64NativeExportContract` for the canonical
`rmsnorm-swiglu-residual-d64-v2` target. It rejects drift in:

- target ID, width, feed-forward dimension, verifier domain, and backend
  version,
- proof-native parameter commitment,
- model/config/input/output public-instance commitments,
- normalization config commitment,
- activation lookup commitment,
- public-instance commitment,
- statement commitment,
- relation commitment,
- projection, trace, and activation-table row counts,
- relation check names and statuses,
- mutation names, mutation count, and rejection count,
- exact `next_backend_step` wording,
- non-claim wording that keeps this out of the proof/AIR claim lane and
  prevents implying that private witness rows are already opened by the native
  parameter commitment.

## Why This Matters

This is the first Rust-native consumption point for the d64 statement contract.
The previous oracle showed that the relation can be checked fail-closed in a
reference implementation. This contract makes the next AIR/export PR consume the
same public binding target instead of inventing a looser duplicate.

The useful discovery during implementation was a hardening gap in the first Rust
adapter draft: shape checks alone accepted a syntactically valid replacement
commitment for a public-instance field. The final module pins every checked d64
commitment value and rejects that drift.

## Non-Claims

This is not:

- a Stwo proof,
- verifier-time evidence,
- AIR constraints,
- backend independence evidence,
- full transformer inference,
- proof that private witness rows already open to
  `proof_native_parameter_commitment`.

## Next Step

Implement the smallest native AIR/export slice that consumes this contract. The
first useful slice should not try to prove the whole d64 block at once; it should
bind one relation family, such as the RMSNorm row surface or activation lookup
membership, to the same `proof_native_parameter_commitment` and reject relabeling
at the proof/export boundary.

## Validation

Machine-readable evidence:

- `docs/engineering/evidence/zkai-d64-native-export-contract-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-export-contract-2026-05.tsv`

Focused validation:

```bash
cargo test d64_native_export_contract --lib
```

Broader d64 validation:

```bash
python3 -m unittest \
  scripts.tests.test_zkai_d64_native_relation_witness_oracle \
  scripts.tests.test_zkai_d64_rmsnorm_swiglu_statement_fixture \
  scripts.tests.test_zkai_d64_stwo_vector_row_surface_probe \
  scripts.tests.test_zkai_d64_commitment_consistency_method_probe
```

Repository gates before merge:

```bash
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
