# Tablero Soundness Note (April 25, 2026)

This note states the strongest soundness claim the repository can currently make
about the Tablero pattern.

It is intentionally narrower than a new STARK theorem. The repository does **not**
claim a new proof-system soundness result independent of upstream S-two. The
claim here is statement preservation: when a verifier replaces an expensive
replay surface with a typed boundary object, under what assumptions does that
replacement preserve the same accepted statement set?

## Scope

- Primary demonstrated boundary: Phase44D typed source-chain public-output
  boundary
- Higher wrapper surfaces covered by the same statement-preservation shape:
  Phase45 public-input bridge, Phase46 proof-adapter receipt, Phase47 wrapper
  candidate, and Phase48 no-go wrapper attempt
- Underlying cryptographic backend: upstream S-two `verify` plus repository-local
  metadata, commitment, and replay-elimination checks
- Claim boundary: the pattern is structurally broader than zkML, but the checked
  empirical demonstrations in this repository remain in the transformer-VM lane

## Threat model

The adversary may:

- choose arbitrary serialized artifacts,
- splice stale nested artifacts into newer wrappers,
- mutate version strings, flags, or commitments,
- reorder public inputs or claimed rows,
- substitute a different compact claim under a boundary-width object,
- present a malformed or adversarial proof payload.

The adversary does **not** break the collision resistance of the local
Blake2b-based commitment functions and does not break the soundness of the
upstream S-two proof system.

## Objects and notation

Let:

- `R` be the underlying compact-proof relation checked by upstream S-two.
- `V_R(c, π)` be the compact verifier for claim `c` and proof `π`.
- `σ` be the heavier source surface that a replay baseline would inspect
  directly, such as a proof-checked Phase12 chain plus ordered Phase30 manifest.
- `U(σ, c)` be the replay-derived public surface that the baseline verifier would
  reconstruct from `σ` and compare against `c`.
- `Emit(σ, c)` be the deterministic source-side emission function that produces a
  typed boundary object `β` plus any nested commitments needed for later wrapper
  layers.
- `Bind(β, c)` be the repository-local binding predicate that checks that `β`
  carries the same source-root, public-output, ordering, flag, and commitment
  facts that the replay baseline would have derived from `σ` for `c`.

The Tablero verifier shape is:

```text
TableroVerify(β, c, π) :=
  Validate(β)
  and V_R(c, π)
  and Bind(β, c)
```

where `Validate(β)` is the typed-object schema/version/flag/commitment check for
that layer.

## Assumptions

### A1. Upstream compact-proof soundness

If `V_R(c, π) = 1`, then except with negligible probability `ε_R`, the claim `c`
is a true statement in relation `R` under the upstream S-two soundness model.

This note inherits that assumption; it does not reprove it.

### A2. Local commitment binding

The repository-local commitment functions used to bind nested artifacts,
public-input lanes, source roots, and wrapper objects are collision resistant up
to negligible probability `ε_H`.

This note treats those hash commitments as binding commitments, not as a new
cryptographic construction.

### A3. Proof-native emission completeness

For a Tablero boundary to replace replay honestly, the source side must emit the
proof-native fields that `Bind(β, c)` checks.

This assumption is exactly why Phase44D clears and Phase43 currently does not:
Phase43's feasibility gate records a real mechanism but a current no-go because
its source side does not yet emit the proof-native inputs needed to drop the full
trace honestly.

## The statement-preservation theorem

**Theorem 1 (Tablero statement preservation).** Let `β = Emit(σ, c)` be a typed
boundary object for compact claim `c` over source surface `σ`. Suppose:

1. `Validate(β)` succeeds,
2. `V_R(c, π)` succeeds,
3. `Bind(β, c)` succeeds, and
4. Assumptions A1-A3 hold.

Then, except with probability at most `ε_R + ε_H`, accepting `(β, c, π)` does
not widen the accepted statement set relative to the replay verifier that checks
`V_R(c, π)` and reconstructs the same public surface from `σ` directly.

Equivalently: the typed boundary may remove verifier-side replay work, but it
cannot change the accepted compact statement unless either the upstream proof
system is unsound, the local commitments collide, or the source side failed to
emit the proof-native data required by the binding predicate.

## Proof sketch

1. `V_R(c, π)` succeeds, so by A1 the compact claim `c` is valid for relation
   `R`, except with probability `ε_R`.
2. `Validate(β)` succeeds, so the typed boundary object satisfies its local
   object-level invariants: canonical version/scope, no replay-reintroduction
   flags, structurally well-formed commitments, and object self-commitment.
3. `Bind(β, c)` succeeds, so the fields of `β` that replace replay work match the
   compact claim `c` and the typed boundary's nested commitments. In this repo,
   this includes source-root binding, canonical public-output binding, ordered
   public-input binding, wrapper-commitment binding, and stale-commitment
   rejection on serialized artifacts.
4. By A2, the nested commitment checks are binding except with probability
   `ε_H`, so the adversary cannot splice a semantically different nested object
   under the same commitment except with negligible probability.
5. Therefore the verifier that accepts `β` is accepting the same compact claim
   `c` together with the same boundary facts that the replay baseline would have
   derived, but without recomputing those facts from `σ` inside the verifier.
6. So the accepted statement set is preserved up to `ε_R + ε_H`.

## Corollary for this repository

For the checked Phase44D path, the theorem says the following narrower sentence:

> If the compact Phase43 proof verifies, and the Phase44D typed boundary passes
> its source-root/public-output/commitment checks, then replacing ordered Phase30
> manifest replay with Phase44D boundary acceptance preserves the same
> source-bound compact statement up to upstream S-two soundness and local hash
> binding assumptions.

This is the strongest soundness sentence the current repository can defend for
Tablero today.

## Why Phase43 currently remains a no-go

The theorem has a real precondition: the source side must emit the proof-native
inputs that the binding predicate checks.

Phase43 fails that precondition today. The source-root mechanism is real, but the
current source surface does not emit the proof-native commitments and public
inputs required to drop the full Phase43 trace honestly. So Phase43 is a valid
engineering no-go, not a contradiction of the theorem.

## What this theorem does not claim

This note does **not** claim:

- a new STARK soundness theorem,
- a new S-two soundness theorem,
- recursive-proof compression soundness,
- knowledge soundness beyond the upstream proof system,
- backend-independent empirical validation,
- universal replay-elimination for every wrapper layer,
- any claim that the large Phase44D ratios are independent of the repository's
  current manifest serialization and hashing implementation.

The theorem is about statement preservation under typed replay replacement, not
about asymptotic optimality or universal speedups.

## Code mapping

The current repository surfaces this theorem through the following code paths.

### Core Phase44D boundary

- typed boundary validation and acceptance:
  `src/stwo_backend/history_replay_projection_prover.rs`
  - `verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance`
  - `verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding`
- nested source-emission and source-root checks:
  `src/stwo_backend/history_replay_projection_prover.rs`
  - `verify_phase44d_history_replay_projection_source_emission_public_output_acceptance`
  - `verify_phase44d_history_replay_projection_external_source_root_binding`

### Higher wrapper layers

- Phase45 bridge verification:
  `src/stwo_backend/recursion.rs`
  - `verify_phase45_recursive_verifier_public_input_bridge`
  - `verify_phase45_recursive_verifier_public_input_bridge_against_sources`
- Phase46 receipt verification:
  `src/stwo_backend/recursion.rs`
  - `verify_phase46_stwo_proof_adapter_receipt`
  - `verify_phase46_stwo_proof_adapter_receipt_against_sources`
- Phase47 candidate verification:
  `src/stwo_backend/recursion.rs`
  - `verify_phase47_recursive_verifier_wrapper_candidate`
  - `verify_phase47_recursive_verifier_wrapper_candidate_against_phase46`
- Phase48 no-go wrapper verification:
  `src/stwo_backend/recursion.rs`
  - `verify_phase48_recursive_proof_wrapper_attempt`
  - `verify_phase48_recursive_proof_wrapper_attempt_against_phase47`

## Current evidence classes behind the theorem

1. deterministic unit and tamper tests on the carry-aware proof surface,
2. disk-backed JSON round-trip and stale-commitment rejection for Phase44D/45/46/47/48,
3. bounded Kani harnesses for canonical public-input ordering plus Phase45/47/48
   replay-free flag and wrapper surfaces,
4. bounded fuzz smoke on manifest-style artifact loaders and Tablero artifact
   acceptors,
5. Miri/UB/sanitizer coverage through the repo hardening stack,
6. dependency audit and merge-gate evidence.

This is a strong engineering evidence stack. It is still weaker than a proof-assistant
formalization.

## Next honest escalation

If the repo needs stronger closure than this note provides, the next honest
escalation is not to widen the theorem informally. It is to move one step up
the rigor ladder:

1. keep the current deterministic and adversarial test stack,
2. add stronger seeded fuzz corpora on the newer Tablero surfaces,
3. add bounded model-checking for the exact binding predicates that replace
   replay, and only then
4. if the claim needs proof-assistant-grade certainty, formalize the typed
   boundary statement in Lean or a similar assistant.

That sequence matches the way StarkWare now describes its own formal-soundness
roadmap for S-two-adjacent systems: proof assistants are the end of the
escalation ladder, not the first step.
