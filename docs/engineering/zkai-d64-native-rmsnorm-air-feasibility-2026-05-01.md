# zkAI d64 native RMSNorm AIR feasibility gate - 2026-05-01

## Question

Can the existing Stwo normalization lookup primitive be reused honestly as the
native AIR/proof step for the d64 RMSNorm slice contract?

## Result

NO-GO for reusing the existing normalization lookup primitive as the d64
RMSNorm AIR proof.

The follow-up d64-specific public-row AIR component now exists and supersedes
the implementation-target half of this feasibility note. That later proof
consumes the same public-row surface and adds an AIR-native bounded sqrt
inequality for the public `rms_q8` scalar, plus a recomputed
RMSNorm-local output row commitment over `normed_q8`. This note remains the
checked NO-GO for relabeling the old five-row normalization lookup primitive as
the d64 RMSNorm proof.

## Why This Matters

The existing normalization component is a useful internal lookup pilot, but it
is not the d64 RMSNorm statement. It proves membership in a five-row
reciprocal-square-root lookup table:

- `(1, 256)`
- `(2, 181)`
- `(4, 128)`
- `(8, 91)`
- `(16, 64)`

The d64 RMSNorm slice contract requires a different surface:

- `64` RMS square rows,
- `64` RMS normalization rows,
- binding to `proof_native_parameter_commitment`,
- binding to `rms_scale_tree_root`,
- preservation of the d64 statement commitment and public-instance commitment.

Treating the old five-row primitive as the d64 proof would blur "a lookup demo
exists" into "the d64 RMSNorm relation is proven." This gate makes that
overclaim fail closed.

## Blockers

The checked blockers are:

- `existing_component_table_rows_5_not_d64_rms_square_rows_64`
- `existing_component_has_no_proof_native_parameter_commitment_input`
- `existing_component_has_no_rms_scale_tree_root_binding`
- `existing_component_claims_lookup_membership_not_rmsnorm_arithmetic_rows`
- `existing_component_statement_contract_marks_primitive_internal`

## Non-Claims

The checked non-claims are:

- `not a d64 AIR proof`
- `not verifier-time evidence`
- `not proof-native parameter opening evidence`
- `not a 64-row RMSNorm constraint system`
- `not safe to reuse the Phase5/Phase10 normalization primitive as the d64 slice proof`

## Superseding Result

The d64-specific public-row proof is recorded in:

- `docs/engineering/zkai-d64-native-rmsnorm-public-row-proof-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-public-row-proof-2026-05.json`
- `src/stwo_backend/d64_native_rmsnorm_public_row_proof.rs`

That result still does not prove private parameter openings or full d64 block
output semantics. It only supersedes the earlier "build a d64-specific RMSNorm
AIR component" implementation target.

## Next Step

Continue from the public-row proof by bridging local RMSNorm rows into the next
d64 relation surface:

- consume the existing local `rmsnorm_output_row_commitment`,
- only claim the full d64 `output_activation_commitment` after the remaining
  activation, projection, and residual rows are proven or source-bound.

Do not reuse the current normalization lookup primitive as the d64 proof unless
it is upgraded to carry those exact bindings.

## Evidence

Machine-readable evidence:

- `docs/engineering/evidence/zkai-d64-native-rmsnorm-air-feasibility-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-air-feasibility-2026-05.tsv`

Rust gate:

- `src/stwo_backend/d64_native_rmsnorm_air_feasibility.rs`

## Validation

```bash
cargo test d64_native_rmsnorm_air_feasibility --lib --features stwo-backend
cargo test d64_native_rmsnorm_slice_contract --lib
cargo test d64_native_export_contract --lib
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
