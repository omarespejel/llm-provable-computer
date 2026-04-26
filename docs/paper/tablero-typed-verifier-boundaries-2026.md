# Tablero: Typed Verifier Boundaries for Layered STARK Systems, with Evidence from STARK-zkML

<p><strong>Abdelhamid Bakhta</strong><br>
StarkWare</p>

<p><strong>Omar Espejel</strong><br>
Starknet Foundation</p>

*April 2026 draft*

## Abstract

Layered proof systems often pay a verifier-side replay cost long after the core
cryptographic statement has already been fixed. In practice, a verifier may first
check a compact proof and then still spend most of its wall-clock budget
reconstructing ordered manifests, public-input tables, or source-chain summaries.
This paper isolates a design pattern for removing that replay cost without widening
what the verifier accepts. We call the pattern **Tablero**: a typed verifier boundary
that binds the same public facts the replay path would have reconstructed, but does
so through a compact boundary object and explicit commitment checks.

The main technical claim is a statement-preservation theorem: if the underlying
compact proof system is sound, the boundary object is well formed, and the boundary
binding checks are complete for the emitted source facts, then accepting the typed
boundary preserves the same accepted statement set as replaying the heavier source
surface directly. This is not a new STARK theorem and not a recursive-compression
result. It is a theorem about when replay replacement is honest.

We then study the pattern in a transformer-shaped STARK-zkML laboratory. On the
current experimental backend, the main typed-boundary path reproduces across three
layout families. At the checked frontier, the replay-avoidance ratio grows from
`19.2x` to `250.6x` on the `3x3` family and reaches `312.3x` on the default family and
`925.1x` on the `2x2` family at `1024` checked steps. The dominant avoided cost is not
faster FRI verification; it is the verifier-side replay path itself, especially
ordered canonical serialization and hashing in the manifest baseline. A second
candidate boundary is also reported honestly as a negative result: it did not clear
as a meaningful replay-elimination boundary under the current source-emission and cost
structure.

The contribution is therefore threefold: a reusable verifier-boundary pattern, a
formal statement-preservation criterion for deploying it safely, and an empirical
study showing when and why replay elimination opens a growing latency gap in a layered
STARK stack.

______________________________________________________________________

## 1. Introduction

The hardest systems problems in proof engineering often arise above the core proof.
A stack can already have a cryptographically meaningful compact statement and still
force the verifier to replay heavy structure around it: ordered manifests,
derived public-input vectors, source-chain commitments, or receipt wrappers.
Those replay surfaces matter because they are where wall-clock latency,
serialization overhead, and implementation complexity can pile up even when the
core proof relation is already fixed.

This paper studies that layer. The question is not whether recursive STARK systems,
lookup-heavy verifiers, or zkML stacks are possible in principle. The question is
more operational:

**When can a verifier replace an expensive replay surface with a typed boundary object
without changing what it accepts?**

That question matters well beyond zkML. Any layered STARK system with a compact proof
at one layer and replay-heavy verification logic at the next layer can face the same
tradeoff. A typed boundary is attractive because it can compress the verifier-facing
object and remove replay work. But it is only honest if the boundary object is bound
to the same statement the replay path would have enforced.

We use a transformer-shaped STARK-zkML stack as the empirical lab because it makes
these replay surfaces unusually visible. The stack already exposes compact proofs,
source-bound verification paths, bridge objects, handoff receipts, wrapper candidates,
and a hardening program aimed at malformed or stale serialized artifacts. That gives us
a realistic setting in which the replay surface is both large enough to matter and
formal enough to study.

The paper makes four claims.

1. **Design claim.** Tablero is a reusable settlement-layer pattern for layered STARK
   systems: replace verifier-side replay with a typed boundary whose fields are
   commitment-bound to the compact statement.
2. **Formal claim.** Under explicit assumptions, accepting the typed boundary preserves
   the same accepted statement set as replaying the heavier source surface.
3. **Empirical claim.** In the current transformer-shaped empirical lab, the main typed
   boundary reproduces across three layout families and exhibits a growing-in-`N`
   replay-avoidance curve.
4. **Boundary claim.** The pattern is not universal. It only applies where the source
   side emits enough proof-native material and where the replay surface is expensive
   enough to be worth removing. We include one bounded negative result to mark that
   boundary explicitly.

We also state the non-claims up front. This paper does **not** claim a new STARK
soundness theorem, backend independence, recursive proof compression, a full end-to-end
transformer benchmark, or a universal lower bound on replay cost across all
implementations. The empirical demonstrations remain in one transformer-shaped STARK-zkML
lane, and the large latency ratios are implementation-grounded replay-avoidance ratios,
not claims that cryptographic verification itself became hundreds of times faster.

______________________________________________________________________

## 2. Replay Surfaces in Layered STARK Systems

Consider a layered verifier with two kinds of work.

- **Compact-proof work.** Verify the claim and proof that define the compact
  cryptographic statement.
- **Replay work.** Reconstruct or recheck heavier source-side structure around that
  compact statement: ordered manifests, source-chain objects, public-input lists,
  receipt wrappers, or other derived commitments.

A verifier that performs both is often logically correct but architecturally
inefficient. The replay path may dominate wall-clock cost even when the compact proof
is relatively small.

That distinction motivates a cleaner abstraction.

A **typed verifier boundary** is a compact object emitted by the source side that carries
exactly the boundary facts the verifier would otherwise derive by replaying the heavier
surface. The verifier then accepts the compact proof together with the typed boundary,
provided it can validate the object and prove that the object's fields bind to the same
compact statement.

The question is not whether a smaller object exists. The question is whether accepting
that smaller object preserves the same statement.

______________________________________________________________________

## 3. The Tablero Pattern

We now define the pattern in abstract form.

### 3.1 Objects and notation

Let:

- `R` be the underlying compact-proof relation;
- `c` be a public compact claim in relation `R`;
- `π` be a proof for `c`;
- `V_R(c, π)` be the verifier for `R`;
- `σ` be the heavier source surface that a replay baseline would inspect directly;
- `β` be a typed boundary object emitted from `σ` and `c`.

The source surface `σ` can be any structured object whose replay path yields public
facts that the verifier currently depends on: ordered manifests, source-chain summaries,
bridge commitments, or receipt-level derived public inputs.

### 3.2 Definition: typed verifier boundary

**Definition 1 (Typed verifier boundary).** A typed verifier boundary `β` for compact
claim `c` over source surface `σ` is a compact object emitted by the source side such
that:

1. `β` is schema-valid and version-valid,
2. `β` exposes the public boundary facts the replay verifier would otherwise derive
   from `σ`, and
3. `β` carries enough commitment-bound information for the verifier to check that
   those facts belong to the same compact claim `c`.

### 3.3 Definition: Tablero acceptance rule

Let `Validate(β)` be the object-level validation predicate for the typed boundary, and
let `Bind(β, c)` be the repository-local binding predicate that checks boundary-to-claim
consistency.

Then the Tablero acceptance rule is:

```text
TableroVerify(β, c, π) := Validate(β) and V_R(c, π) and Bind(β, c)
```

Intuitively:

- `V_R(c, π)` keeps the compact cryptographic statement honest,
- `Validate(β)` prevents malformed or semantically invalid boundary objects, and
- `Bind(β, c)` prevents stale or mismatched boundary data from being attached to the
  wrong compact claim.

### 3.4 When the pattern applies

Tablero is not a universal wrapper trick. It applies only when two conditions hold.

1. **Replay worth removing.** The replay surface is expensive enough that replacing it
   would materially change verifier cost.
2. **Source emission completeness.** The source side emits the proof-native data needed
   for the binding predicate to recreate the same public boundary the replay verifier
   would have enforced.

If either condition fails, the right outcome is not to force the pattern. It is to record
an honest no-go.

______________________________________________________________________

## 4. Statement Preservation

The formal question is now precise: under what assumptions does replacing replay with a
typed boundary preserve the same accepted statement set?

### 4.1 Assumptions

We assume:

1. **Compact-proof soundness.** If `V_R(c, π)` accepts, then `c` is a true statement in
   relation `R` except with negligible probability `ε_R`.
2. **Commitment binding.** The commitment functions used inside the boundary object and
   its nested objects are collision resistant except with negligible probability `ε_H`.
3. **Emission completeness.** The source side emits enough proof-native data for
   `Bind(β, c)` to check all boundary facts that the replay verifier would otherwise
   derive from `σ`.

These are deliberately ordinary assumptions. The theorem below is not claiming a new
cryptographic primitive. It is a theorem about preserving the same statement under a
replay replacement discipline.

### 4.2 Theorem

**Theorem 1 (Tablero statement preservation).** Let `β` be a typed verifier boundary
emitted from source surface `σ` and compact claim `c`. Suppose:

1. `Validate(β)` accepts,
2. `V_R(c, π)` accepts,
3. `Bind(β, c)` accepts, and
4. the three assumptions above hold.

Then, except with probability at most `ε_R + ε_H`, accepting `(β, c, π)` through
`TableroVerify` does not widen the accepted statement set relative to a verifier that
checks `V_R(c, π)` and reconstructs the same public boundary facts directly from `σ`.

### 4.3 Proof sketch

The proof is straightforward.

1. By compact-proof soundness, `V_R(c, π)` implies that `c` is a valid compact statement
   except with probability `ε_R`.
2. `Validate(β)` guarantees that the boundary object is structurally well formed, uses
   the expected schema and semantic scope, and respects object-level invariants.
3. `Bind(β, c)` guarantees that the public facts carried by `β` are commitment-bound to
   the same compact claim `c` rather than to some stale or semantically different object.
4. By commitment binding, the adversary cannot substitute a semantically different nested
   object under the same commitments except with probability `ε_H`.
5. Therefore the verifier that accepts `β` is accepting the same compact claim and the
   same public boundary facts that the replay verifier would have enforced, but without
   recomputing those facts from `σ` inside the verifier.

So the accepted statement set is preserved up to `ε_R + ε_H`.

### 4.4 What the theorem does not say

The theorem does **not** imply:

- that every replay surface can be replaced honestly,
- that every typed boundary improves cost,
- that a boundary result automatically generalizes across backends,
- that recursive compression has already been achieved.

It says only that when a boundary is emitted completely and bound correctly, replacing
replay with that boundary does not widen the accepted statement set.

______________________________________________________________________

## 5. Implementation Boundary and Assurance

The empirical laboratory behind this paper is a layered transformer-shaped STARK stack
that already exposes:

- a compact proof path,
- a typed boundary path,
- a public-input bridge,
- a proof-adapter receipt,
- higher wrapper surfaces, and
- a structured source-side replay baseline.

That stack is valuable because it lets us test the pattern under adversarial conditions
rather than only in prose.

The implementation assurance stack used for this paper is intentionally auditor-style.
It includes:

- deterministic tamper tests for malformed, stale, reordered, and semantically drifted
  serialized artifacts,
- deterministic tests for witness-discipline failures in the experimental arithmetic
  layer,
- bounded model checking on the narrow boundary and wrapper predicates that replace
  replay,
- differential fuzzing on serialized boundary and wrapper inputs,
- runtime hardening that converts panic-prone shape assumptions into fail-closed errors
  on trusted-core paths.

This assurance stack does not replace the theorem. It complements it. The theorem says
what claim is justified if the boundary path is implemented correctly; the assurance
stack increases confidence that the implementation is not silently violating the
conditions of the theorem.

______________________________________________________________________

## 6. Empirical Evaluation

### 6.1 Setup and scope

The empirical demonstrations in this paper come from one transformer-shaped STARK-zkML
laboratory. They are not a matched benchmark against external systems. They are measured
median-of-five results on one experimental backend, used to study the behavior of typed
replay replacement under controlled variations in layout geometry.

The main comparison is always the same:

- **Typed-boundary path.** Verify the compact proof and accept one typed boundary object.
- **Replay baseline.** Verify the same compact proof and then replay the ordered manifest
  that the typed boundary is designed to replace.

The important interpretation rule is simple:

> These ratios measure replay avoidance on the current implementation, not faster FRI
> verification and not a universal lower bound on all possible manifest designs.

### 6.2 Cross-family transferability

The main positive result is not a single large ratio. It is that the same mechanism
reproduces across three layout families with the same growing-in-`N` shape.

#### Table 1. Frontier summary across checked layout families

| Family | Checked frontier | Replay-avoidance ratio at frontier | Typed-boundary verify | Replay baseline verify |
| --- | ---: | ---: | ---: | ---: |
| default | `1024` | `312.3x` | `427.209 ms` | `133,430.237 ms` |
| `2x2` | `1024` | `925.1x` | `11.133 ms` | `10,299.110 ms` |
| `3x3` | `256` | `250.6x` | `125.753 ms` | `31,511.802 ms` |

This is the strongest empirical claim the current paper should make.

- The mechanism survives all three checked families.
- The constants differ sharply.
- The ratio grows with `N` on every checked family.

That means the typed boundary is removing a linearly growing replay surface rather than
merely shaving a constant factor.

### 6.3 What is constant and what is not

One subtle but important point must be stated explicitly.

Across the checked families, the boundary artifact itself is nearly constant in size:
roughly `6.3-6.6 KB` at the checked frontiers. That is the clean cryptographic property.

The **verify time** of the boundary is **not** family-constant. It varies substantially
because the binding work still depends on the underlying compact path and layout geometry.
So the right sentence is:

> Tablero exposes a near-constant boundary artifact size across checked families, while
> the boundary verify cost remains family dependent.

This distinction matters. If we blur it, a reviewer can correctly object that the data do
not show family-invariant verifier cost.

### 6.4 Causal decomposition

The large ratios are easy to misread if we only quote the frontier numbers. The causal
breakdown shows where the baseline actually spends time.

#### Table 2. Frontier causal decomposition

| Family | Compact proof only | Boundary binding only | Replay only |
| --- | ---: | ---: | ---: |
| default (`1024`) | `77.942 ms` | `277.236 ms` | `137,423.421 ms` |
| `2x2` (`1024`) | `2.350 ms` | `5.116 ms` | `8,996.324 ms` |
| `3x3` (`256`) | `26.649 ms` | `79.561 ms` | `32,233.963 ms` |

This is the main empirical lesson:

- the compact proof stays relatively small,
- the typed boundary binding stays much smaller than the replay baseline, and
- the replay baseline dominates because it performs ordered canonical serialization,
  hashing, and manifest reconstruction work that the typed boundary removes from the
  verifier path.

So a `925x` ratio is not a claim that STARK verification itself became `925x` faster.
It is a claim that the current verifier-side replay surface became unnecessary once the
same public facts were carried by a typed, commitment-bound boundary object.

### 6.5 Bounded negative result

The paper also includes one negative result because that is part of the pattern's honest
boundary.

We evaluated a second candidate boundary over a different source-binding surface. It did
not clear as a meaningful replay-elimination boundary. Two problems blocked it:

1. the source side did not yet emit enough proof-native material to let the verifier bind
   the boundary completely, and
2. the dependency it would have eliminated was already too cheap to produce a meaningful
   replay-avoidance gain.

That is not a failure of the theorem. It is exactly the situation in which the theorem's
preconditions do not hold, and the right result is a recorded no-go rather than an
inflated second positive example.

______________________________________________________________________

## 7. External Calibration

The paper should not present the local results in isolation. The strongest honest
external calibration we currently have is a source-backed public STARK-native deployment
row from Obelyzk's Starknet Sepolia verifier object [2, 3].

That row is useful because it gives:

- a concrete recursive verifier contract,
- a concrete verified transaction,
- a concrete calldata width, and
- public gas numbers for a live settlement path.

What it does **not** give is a matched local verifier-time comparator to the typed
boundary results in this paper. The objects live at different layers:

- the public Obelyzk object is a recursive settlement proof rather than a pre-recursive boundary object,
- the main local object in this paper is a pre-recursive typed verifier boundary,
- the narrower local compact handoff object is a compactness surface rather than a replay
  avoidance surface.

That is why the external calibration should be read as deployment posture, not as an
apples-to-apples verifier race.

A second, narrower external calibration remains useful in the compact-object regime.
Public NANOZK material reports a `5.5 KB`, `24 ms` verifier-facing layer proof on a
small-width workload [1]. The closest local compact handoff object is smaller but slower
on its current path. That is another example of the paper's central claim: different
verifier-facing layers improve different costs.

______________________________________________________________________

## 8. Threats to Validity and Explicit Non-Claims

This paper is only strong if its claim boundary stays narrow.

### 8.1 Experimental-backend scope

The large replay-avoidance curves reported here come from one experimental backend. That
backend has been hardened aggressively, but the empirical demonstrations are still
backend-scoped. Today we can defend transferability across layout families. We cannot yet
defend backend independence.

### 8.2 Implementation-dependent replay cost

The replay baseline in this paper is real, but it is also implementation grounded.
In the current codebase, the dominant replay cost comes from ordered canonical
serialization, hashing, and manifest reconstruction. That is the cost Tablero removes in
this system. It is not a theorem that every replay implementation in every system would
pay the same constant factors.

### 8.3 No recursive-compression claim

The typed boundary path is not recursive proof compression. It is a settlement-layer
replacement of verifier-side replay. The paper therefore does not claim:

- recursive or proof-carrying data constructions,
- incrementally verifiable computation,
- backend-independent proof of the pattern,
- full end-to-end transformer inference proving,
- onchain deployment of the typed boundary path itself.

### 8.4 No universal speedup claim

The paper does not claim that Tablero is always a win. A typed boundary only helps when:

- the replay surface is expensive, and
- the source side emits enough proof-native binding material.

The recorded negative result exists precisely to show that we are not smoothing over this
constraint.

______________________________________________________________________

## 9. Conclusion

The main point of this paper is simple.

A layered STARK system often already knows the compact statement it wants to enforce, but
still wastes verifier time replaying heavier source structure around that statement.
Tablero is a disciplined way to remove that replay work: emit a typed, commitment-bound
boundary object and prove that accepting it preserves the same accepted statement set.

That gives a contribution at three levels.

- At the design level, it names a settlement-layer pattern that appears whenever replay
  dominates verification.
- At the formal level, it states a clean statement-preservation theorem with explicit
  preconditions.
- At the empirical level, it shows a real replay-avoidance curve across three layout
  families, together with a bounded negative result that marks where the pattern does not
  yet apply.

This is not the end of the story. The next steps are clear: broader backend transfer,
stronger external calibration, and eventually a recursive layer that preserves the same
boundary semantics. But those are follow-on results. The present paper is about the
strongest honest claim the current system can already defend.

______________________________________________________________________

## References

1. NANOZK authors. *Public transformer-proof abstract and verifier-object metrics*. Public materials cited in the package calibration note.
2. BitSage. *Obelyzk public verifier object on Starknet Sepolia*. Public docs.rs materials for `obelyzk` 0.3.0.
3. BitSage. *Obelyzk paper and Starknet Sepolia gas figures*. Public paper linked from the `obelyzk` 0.3.0 docs.rs package.
