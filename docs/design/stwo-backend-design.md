# S-two Backend Design

## Goal

Add an experimental S-two / STWO proving backend to `llm-provable-computer` without breaking the current `statement-v1` claim contract or the existing vanilla STARK path.

The design target is conservative:

- preserve current semantics and claim scope,
- isolate proving backend concerns behind an explicit abstraction,
- ship an arithmetic-subset S-two path before attempting lookup-backed nonlinearities or recursion,
- make recursion a later compression layer, not the first migration step.

## Why this document exists

The paper at `docs/paper/stark-transformer-alignment-2026.md` now argues that S-two recursion and M31-native proving strengthen the architectural case for STARK-native verifiable AI. The repo does not yet implement that backend.

This document defines the minimum serious path from the current in-repo vanilla STARK to an S-two-backed prover.

## Current state

Today the repository has the following properties:

- proof generation is implemented in `src/proof.rs`
- the prover/verifier backend is the local module `src/vanillastark/mod.rs`
- proof claims are versioned under `statement-v1`
- verifier semantics include transformer/native lockstep re-execution
- the proved attention mode is currently `average-hard`
- the current proof relation rejects unsupported instructions outside the vanilla AIR subset

This means the migration problem is not just “swap one prover crate for another.” The repo currently couples:

- witness generation,
- AIR shape,
- proof serialization,
- verifier claim logic,
- backend assumptions.

## Non-goals for the first S-two milestone

The first S-two milestone should not try to solve all of the following at once:

- full standard-softmax proving,
- recursion,
- onchain verification,
- learned/trained model weights,
- zero-knowledge hiding,
- complete ISA proof coverage.

Trying to do all of those together would turn the migration into an unbounded rewrite.

## Design principles

### 1. Preserve statement semantics first

`statement-v1` is the user-visible proof contract. The first S-two integration should preserve:

- claim fields,
- semantic scope,
- lockstep verification behavior,
- output digest structure where possible.

If proof bytes or backend metadata differ, that is acceptable. If the semantic statement changes, that is a `statement-v2` problem and should be treated separately.

### 2. Separate backend from witness extraction

Introduce a backend boundary so that trace construction and semantic checks happen once, while proof generation can vary by backend.

Proposed shape:

```rust
pub trait ProofBackend {
    type Proof;
    type VerifyParams;

    fn backend_name(&self) -> &'static str;
    fn prove(&self, witness: &ProofWitness, params: &ProofParams) -> Result<Self::Proof>;
    fn verify(
        &self,
        proof: &Self::Proof,
        claim: &ProofClaim,
        params: &Self::VerifyParams,
    ) -> Result<()>;
}
```

Then split current logic into:

- semantic execution and witness extraction,
- claim assembly,
- backend-specific proving,
- backend-specific verification.

### 3. Keep vanilla STARK as a reference backend

Do not remove or degrade the current vanilla backend while integrating S-two. It should remain:

- the correctness oracle for migration,
- the fallback local backend,
- the parity target for tests.

## Proposed phases

### Phase 0: Backend abstraction refactor

Deliverables:

- extract current witness and claim assembly into backend-agnostic structs,
- rename current implementation internally to `VanillaBackend`,
- add CLI/backend selection, for example:

```text
cargo run --bin tvm -- prove-stark programs/addition.tvm --backend vanilla
cargo run --bin tvm -- prove-stark programs/addition.tvm --backend stwo
```

Acceptance criteria:

- no semantic changes to `statement-v1`,
- current tests remain green,
- default backend remains `vanilla`.

### Phase 1: S-two arithmetic-subset proving

Scope:

- `addition`,
- `multiply`,
- `counter`,
- `dot_product` if feasible,
- the arithmetic-only instruction subset already supported by the vanilla AIR.

Deliverables:

- experimental `stwo` feature flag,
- proof generation for at least one shipped arithmetic program,
- verification path that checks the same claim semantics,
- backend fingerprint metadata in proof output.

Acceptance criteria:

- `vanilla` and `stwo` both prove the same program semantics,
- lockstep verification still runs,
- proof generation failures clearly explain unsupported shapes.

### Phase 2: AIR parity and unsupported-op inventory

Before adding nonlinearities, inventory exactly what remains unsupported.

Deliverables:

- explicit documented opcode coverage table,
- tests that prove or reject each instruction class deterministically,
- mismatch report between the vanilla AIR subset and the desired S-two target subset.

Acceptance criteria:

- no hidden unsupported behavior,
- CLI can explain whether a program is outside the S-two-supported subset.

### Phase 3: One lookup-backed nonlinearity path

This is the highest-leverage technical milestone for the paper.

Target:

- prove one non-arithmetic path, preferably a tiny lookup-backed softmax-family or normalization-family component.

Deliverables:

- fixed-point lookup semantics,
- table commitment strategy,
- one proved nonlinearity benchmark,
- cross-check against transformer/native/ONNX paths where applicable.

Acceptance criteria:

- one non-arithmetic component enters the proved relation on the S-two backend,
- tests demonstrate both semantic agreement and proof validity.

### Phase 4: Recursive compression and aggregation

Only after Phase 1–3 exist does recursion become the right next step.

Targets:

- aggregate multiple proof artifacts from the reproducibility suite,
- compress proof bundles for appendix-ready or onchain-friendly outputs,
- prepare for a future Starknet-facing verification story.

Why later:

- recursion only compounds value once there is an S-two proof to recurse on,
- the March 31, 2026 circuit-recursion upgrade is strategically important, but not a substitute for backend migration.

## Serialization and claim compatibility

Proof outputs should add backend metadata while preserving semantic claim fields.

Suggested additions:

- `proof_backend: vanilla | stwo`
- `proof_backend_version`
- `backend_fingerprint`

These fields should live in `ExecutionClaimCommitments`, not as new semantic fields on
`VanillaStarkExecutionClaim`. They belong to the proof-artifact and prover-metadata layer, alongside
existing commitment metadata such as `scheme_version`, `hash_function`, and `prover_build_info`.

Because these additions do not change the meaning of the claimed computation, they are
backward-compatible commitment metadata only. They should therefore be introduced with
`#[serde(default)]` compatibility where needed and do **not** require forking to `statement-v2`.

Reserve `statement-v2` for material semantic changes to the statement itself, such as changing the
meaning of `VanillaStarkExecutionClaim`, altering required semantic fields, or widening the proved
relation beyond the current `statement-v1` scope.

## Testing strategy

### Golden-path parity tests

For each shipped arithmetic fixture:

- run transformer/native lockstep,
- prove with `vanilla`,
- prove with `stwo`,
- verify both,
- compare final semantic outputs and claim digests.

### Negative tests

For unsupported shapes:

- softmax path,
- unsupported instructions,
- overflow-dependent programs,
- carry-flag claims,

assert that backend rejection is explicit and stable.

### Artifact tests

Generate backend-tagged reproducibility metadata:

- benchmark JSON or TSV,
- artifact hashes,
- backend fingerprints,
- commands log.

## Risks

### Risk 1: AIR mismatch

The current vanilla AIR and an S-two-compatible AIR may not line up cleanly. If so, preserve claim semantics and accept backend-specific internal trace shape.

### Risk 2: Statement drift

The easiest mistake is letting an experimental S-two path silently widen or alter the semantic statement. Guard against this with explicit statement-version checks.

### Risk 3: Premature recursion work

Recursion is attractive because the latest StarkWare update is impressive, but adding it before there is a functioning S-two backend would produce architecture theater rather than real progress.

## Recommended implementation order

1. backend abstraction,
2. arithmetic-subset S-two backend,
3. opcode coverage inventory,
4. one lookup-backed nonlinearity,
5. recursive aggregation.

## Definition of success

The first meaningful success condition is not “recursive proof on Starknet.”

It is this:

> The same `statement-v1` semantic claim can be proved for at least one shipped program by both the current vanilla backend and an experimental S-two backend, with verifier-side lockstep semantics preserved.

Once that exists, the rest of the roadmap becomes technically serious rather than aspirational.
