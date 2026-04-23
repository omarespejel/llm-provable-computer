# Publication-grade STARK profile

The execution-proof surface exposes three named option profiles. Use the right one for
the right context.

| Profile          | `(expansion, q, security)` | Conjectured bits ( `q · log2(rho⁻¹)` ) | Conservative bits ( `q · log2(rho⁻¹) / 2` ) | Intended use                                           |
| ---------------- | -------------------------- | -------------------------------------- | ------------------------------------------- | ------------------------------------------------------ |
| `default`        | (4, 2, 2)                  | 4                                      | 2                                           | Library smoke tests only. Not a security claim.        |
| `production-v1`  | (4, 16, 32)                | 32                                     | 16                                          | Routine CI and integration runs. Not a security claim. |
| `publication-v1` | (16, 24, 48)               | 96                                     | 48                                          | Paper-cited evidence, public release artifacts.        |

## Which bound to quote

Two bounds appear in the STARK literature for the cost of forging a proof
under FRI:

- The **conjectured** per-query bound is `log2(rho⁻¹) · q` bits. This is the
  optimistic figure that most practical STARK projects publish.
- The **conservative** Reed-Solomon list-decoding bound is roughly half that:
  `log2(rho⁻¹) · q / 2` bits.

Any external publication MUST quote one of these explicitly and label it.
The `publication-v1` profile is sized so the conservative bound is at least
48 bits and the conjectured bound is at least 96 bits, which is sufficient for
publication-grade evidence at this code-base scope. Do not use `production-v1`
or `default` for any artifact that will be cited as a cryptographic claim.

## CLI usage

```bash
# Generate a paper-cited proof (slow; budget 5-10x production-v1).
cargo run --release --bin tvm -- prove-stark programs/fibonacci.tvm \
  -o fib.publication.proof.json \
  --stark-profile publication-v1

# Verify under the publication-v1 floor.
cargo run --release --bin tvm -- verify-stark fib.publication.proof.json \
  --verification-profile publication-v1
```

## Programmatic usage

```rust
use llm_provable_computer::{
    publication_v1_stark_options,
    prove_execution_stark_with_options,
    verify_execution_stark_with_reexecution_and_policy,
};
use llm_provable_computer::proof::publication_v1_security_floor_policy;

let proof = prove_execution_stark_with_options(&model, max_steps, publication_v1_stark_options())?;
assert!(
    verify_execution_stark_with_reexecution_and_policy(&proof, publication_v1_security_floor_policy())?
);
```

## Test coverage

The library guarantees:

- `publication-v1` clears the `StarkVerificationPolicy::strict()` floor of
  80 conjectured bits (`publication_profile_v1_is_validated_by_strict_policy`).
- `publication-v1` is at least 32 conjectured bits stronger than `production-v1`
  (`publication_profile_v1_meets_min_conjectured_security_floor`).
- The CLI surfaces `--stark-profile publication-v1` and
  `--verification-profile publication-v1` and uses the same options as the
  library helpers.
