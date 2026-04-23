# Claim-drift guards

The active execution-proof surface exposes a small number of public verification entry points:

- `verify_execution_stark` (default; claim-only)
- `verify_execution_stark_claim_only` / `_with_policy`
- `verify_execution_stark_with_policy`
- `verify_execution_stark_with_reexecution` / `_and_policy`
- `verify_execution_stark_with_backend_and_policy`

The CLI sits on top of these with `--verification-profile {default | production-v1 | publication-v1}`.

The `statement-v1` semantic scope is the literal string
`native_isa_execution_with_transformer_native_equivalence_check`. That label
is a **commitment** to two things at the same time:

1. The STARK proof attests to a valid native-ISA execution trace.
2. The claim is bound to a transformer/native equivalence check (re-executable
   from claim data).

Either of those guarantees, broken silently, is a claim drift.

## What the guards enforce

Every verification entry point — including the claim-only entries — runs the
following invariants in order:

1. `validate_backend_metadata` — proof backend label matches the requested backend.
2. `validate_statement_metadata` — `statement_version` and `semantic_scope` match
   the v1 constants exactly; commitment scheme/version + hash function match.
3. `validate_proof_inputs` — the program is non-empty and matches the shipped S-two proof shape.
4. `validate_stark_options` — `expansion_factor` is power of two ≥ 4, q satisfies
   `2q ≥ security_level`, security level ≤ 128.
5. `validate_verification_policy` — `conjectured_security_bits(options)` ≥ caller's
   `min_conjectured_security_bits`.
6. `validate_public_state` — final state memory length matches program memory size.
7. `validate_transformer_config` — config validates; attention mode matches claim;
   **and the v1 scope requires the config to be present**.
8. `validate_equivalence_metadata` — fingerprints match the claim's own
   final state; **and the v1 scope requires equivalence to be present**.
9. `validate_claim_commitments` — every commitment hash recomputes from the
   claim's own bytes; `prover_build_info` non-empty.
10. The S-two backend label and backend-version family are checked before proof bytes
    are accepted by the verifier.

The two "v1 scope requires" rows are the claim-drift guards. Without them, a
claim could keep the v1 label while dropping the very payload that the label
promises to a verifier.

## Tests

- `proof::tests::verify_rejects_v1_claim_missing_equivalence_metadata`
- `proof::tests::verify_rejects_v1_claim_missing_transformer_config`
- `proof::tests::claim_only_verification_rejects_v1_scope_without_equivalence_metadata`
- `proof::tests::claim_only_verification_does_not_reexecute_equivalence_metadata`

The verification tests exercise the public verification entry points listed in
this gate and are maintained to prevent malformed claims from bypassing these invariants.

## Lockstep with the spec file

`spec/statement-v1.json` and the constants
`CLAIM_STATEMENT_VERSION_V1`, `CLAIM_SEMANTIC_SCOPE_V1`,
`CLAIM_COMMITMENT_SCHEME_VERSION_V1`, `CLAIM_COMMITMENT_HASH_FUNCTION_V1` are
synced by `proof::tests::statement_spec_contract_is_synced_with_constants`.
If you change a constant in `proof.rs`, change the spec file in the same commit.
