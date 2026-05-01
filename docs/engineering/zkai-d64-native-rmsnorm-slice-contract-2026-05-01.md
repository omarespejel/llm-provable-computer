# zkAI d64 native RMSNorm slice contract - 2026-05-01

## Question

Can the native Rust/Stwo side consume the d64 export contract for one concrete
relation family before attempting the whole RMSNorm-SwiGLU-residual block?

## Result

GO for a native RMSNorm slice contract. NO-GO-YET for AIR constraints or an
exact Stwo proof.

The Rust module `src/stwo_backend/d64_native_rmsnorm_slice_contract.rs` consumes
the checked d64 relation oracle through `ZkAiD64NativeExportContract`, then pins
the RMSNorm-specific slice:

- target ID, backend version, verifier domain,
- source export contract version and decision,
- `proof_native_parameter_commitment`,
- normalization config commitment,
- input activation commitment,
- public-instance commitment,
- statement commitment,
- relation commitment,
- RMS scale tree root,
- `64` RMS square rows,
- `64` RMS normalized rows,
- exact `input_q8` and `normed_q8` range summaries,
- exact `rmsnorm_rows_recomputed:GO` relation-check identity.

## Why This Matters

This is the first relation-family consumption point after the d64 export
contract. It is intentionally smaller than the full block: it isolates the
normalization surface so the next AIR/export PR has a bounded target and cannot
quietly substitute a looser statement.

The review loop on the export contract found a general rule we now preserve
here: a serialized handoff must carry semantic identities, not only counts.
For this slice, that means the exported contract carries the exact RMSNorm
relation-check identity and rejects round-trip drift of that identity.

## Non-Claims

The checked `non_claims` literals are:

- `not a Stwo proof`
- `not verifier-time evidence`
- `not full d64 block proof`
- `not projection, activation, SwiGLU, down-projection, or residual proof`
- `not proof that private witness rows already open to proof_native_parameter_commitment`

## Next Step

Encode the `rms_square_rows` and `rms_norm_rows` constraints as native Stwo AIR
rows bound to `proof_native_parameter_commitment`. If that slice cannot be
encoded without weakening the statement, record the exact blocker before
attempting activation lookup or projection rows.

## Evidence

Machine-readable evidence:

- `docs/engineering/evidence/zkai-d64-native-rmsnorm-slice-contract-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-slice-contract-2026-05.tsv`

## Validation

```bash
cargo test d64_native_rmsnorm_slice_contract --lib
cargo test d64_native_export_contract --lib
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
