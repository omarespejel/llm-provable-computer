# Tablero: Typed Verifier Boundaries for Layered STARK Systems, with Evidence from STARK-zkML

**Abdelhamid Bakhta**, StarkWare

**Omar Espejel**, Starknet Foundation

*April 2026 draft*

Short submission abstract: [abstract-tablero-2026.md](abstract-tablero-2026.md).

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
`17.7x` to `1011.9x` on the `3x3` family and reaches `1066.6x` on the default family and
`917.8x` on the `2x2` family at `1024` checked steps. The dominant avoided cost is
not faster FRI verification; it is per-step verifier-side replay work over the
source-chain surface. An explicit red-team measurement (median of nine
runs) against an honestly-optimized replay verifier (binary canonical
commitments and no redundant per-step serialization) tightens the headline
ratio at the checked frontier to a host-noise-sensitive band of
`~261x`-`~330x`, isolating an implementation-cost component of
`~3.1x`-`~3.6x` from a structural component of `~261x`-`~330x` that any
honest replay verifier pays. A second typed boundary on a distinct
emitted-source surface also clears as supporting positive evidence at `1.22x`
on the conservative publication row (Table 4); a broader engineering sweep
over the same surface is checked in but is not promoted here as a
paper-facing performance claim. The paper also reports one bounded
compactness no-go: a narrower handoff object that shrinks bytes but not
verifier latency because it compacts a replay-dependent path rather than
eliminating replay.

The contribution is therefore threefold: a reusable verifier-boundary pattern, a
formal statement-preservation criterion for deploying it safely, and an empirical
study showing when and why replay elimination opens a growing latency gap in a layered
STARK stack.

---

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
   enough to be worth removing. We include one smaller supporting second boundary and
   one bounded compactness no-go to mark that boundary explicitly.

We also state the non-claims up front. This paper does **not** claim a new STARK
soundness theorem, backend independence, recursive proof compression, a full end-to-end
transformer benchmark, or a universal lower bound on replay cost across all
implementations. The empirical demonstrations remain in one transformer-shaped STARK-zkML
lane, and the large latency ratios are implementation-grounded replay-avoidance ratios,
not claims that cryptographic verification itself became hundreds of times faster.

### 1.1 Research context

Tablero builds on a small set of related arguments that take the
"transformers as computers" premise from architectural intuition to a
checkable execution surface.

The original premise — that a transformer in decode mode behaves like a
computer running a deterministic program — was made concrete by Percepta's
*Can LLMs Be Computers?* [4]. AbdelStark's follow-on note *Can LLMs be
PROVABLE computers?* [5] asked the natural next question: if a transformer
can execute a program, can that execution produce independently checkable
evidence? His framing names the bridge directly: *the trace becomes the
witness*.

A separate argument [6] makes the structural case that STARK trace
structure naturally fits transformer decode because the workload already
exhibits repeated stateful local work over carried context, and that the
proof artifact for one decode step should preserve the carried boundary,
not just the visible output token. That argument establishes the
*architectural fit* between trace-based STARK proving and transformer
decode but does not provide a verifier-side mechanism that exploits it:
it argues that the carried boundary should be made visible, but it does
not provide the verifier that accepts it in lieu of replay.

This paper provides one such mechanism. Tablero is a verifier-side pattern
that lets a layered STARK system accept a typed certificate of the public
boundary facts a replay path would have reconstructed, without the
verifier walking the source-chain surface itself. The structural fit
between STARK traces and transformer decode is treated as a precondition,
not as a result of this paper. We do not contribute a new STARK
construction or a new transformer arithmetization. The contribution is
*systems-level*: a settlement-layer pattern that closes one specific cost
gap between "this execution can be proved" and "the verifier can check
that proof cheaply at deployment scale."

In the surrounding zkML literature, related lines come at the same problem
from different angles. zkLLM-style work introduces lookup machinery for
non-arithmetic tensor operations and attention-specific proving;
Jolt-Atlas brings a lookup-centric SNARK approach to ONNX tensor
operations; NANOZK [1] argues for layerwise zero-knowledge proofs for LLM
inference; Lagrange DeepProve-1 reports full GPT-2 inference proving as a
SNARK-side existence proof; LuminAIR with Giza × S-two demonstrates a
STARK-native graph-to-AIR path. These are predecessors and parallel work
in the broader zkML space. Tablero is orthogonal to them: none of them
gives a verifier-side replay-elimination pattern with a stated soundness
criterion and measured savings on the carried-state surface that
transformer decode naturally exposes.

---

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

---

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

---

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

---

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

---

## 6. Empirical Evaluation

### 6.1 Setup and scope

The empirical demonstrations in this paper come from one transformer-shaped STARK-zkML
laboratory. They are not a matched benchmark against external systems. They are measured
median-of-five results on one experimental backend, used to study the behavior of typed
replay replacement under controlled variations in layout geometry. The measurement policy,
reproducibility handles, and public wording rules are summarized in
[appendix-methodology-and-reproducibility.md](appendix-methodology-and-reproducibility.md).

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


| Family  | Checked frontier | Replay-avoidance ratio at frontier | Typed-boundary verify | Replay baseline verify |
| ------- | ---------------- | ---------------------------------- | --------------------- | ---------------------- |
| default | `1024`           | `1066.6x`                          | `8.130 ms`            | `8,671.126 ms`         |
| `2x2`   | `1024`           | `917.8x`                           | `8.121 ms`            | `7,453.229 ms`         |
| `3x3`   | `1024`           | `1011.9x`                          | `8.311 ms`            | `8,410.230 ms`         |


The structural claim is the slope difference fitted in Section 6.3, not the
constant-factor headline. The frontier ratios above are
implementation-dependent: a more aggressively optimized honest replay verifier
would tighten the constant. What is *not* implementation-dependent over our
checked grid is that the replay baseline grows near-linearly in `N` while the
typed-boundary path grows sublinearly, so the ratio grows with `N` for
structural reasons rather than because of one favorable endpoint.

- The mechanism survives all three checked families.
- The constants still differ materially.
- The ratio grows with `N` on every checked family.

That means the typed boundary is removing a replay surface that is near-linear over the
checked grid rather than merely shaving a constant factor.

Reproducibility note for Table 1 and Figure 1: the typed-boundary and
replay-baseline frontier rows are taken from the family-matrix evidence at
`docs/paper/evidence/tablero-results-overview-2026-04.tsv`, regenerated by
`python3 scripts/paper/generate_tablero_results_overview.py`. Table 3 below
comes from a separate replay-decomposition harness whose paper-facing rows
live at `docs/paper/evidence/tablero-replay-baseline-breakdown-2026-04.tsv`
and are regenerated by
`python3 scripts/paper/generate_tablero_replay_breakdown.py`. The "Replay
baseline verify" column in Table 1 and the "Replay total" column in Table 3
are therefore two distinct median-of-five measurements at the same `1024`
frontier and can disagree by tens of milliseconds across re-runs of the two
harnesses. They are not expected to match exactly; they are expected to lie
within the same percent-scale band, which they do.

![Tablero results overview across checked families](figures/tablero-results-overview-2026-04.svg)

**Figure 1.** The main empirical fact is the curve shape across the three checked
families. The frontier artifact size stays in a narrow band, while verifier cost remains
family dependent.

### 6.3 Checked scaling-law fit

The frontier table is intentionally not the whole argument. We also fit the full checked
curves in log-log space for each family. This is an explicitly labeled carry-aware
experimental-backend artifact: the source evidence is promoted from the engineering lane
with that label preserved in the filename and metadata. It is a measured-regime fit, not
an asymptotic theorem and not a claim about a default backend.

#### Table 2. Log-log slope fit over the checked grids


| Family  | Grid     | Typed-path slope | Replay-baseline slope | Ratio slope | Ratio fit `R^2` |
| ------- | -------- | ---------------- | --------------------- | ----------- | --------------- |
| default | `2-1024` | `0.3559`         | `0.9921`              | `0.6362`    | `0.9706`        |
| `2x2`   | `2-1024` | `0.3567`         | `0.9899`              | `0.6332`    | `0.9704`        |
| `3x3`   | `2-1024` | `0.3508`         | `0.9905`              | `0.6397`    | `0.9695`        |


The replay baseline is near-linear over the checked grids. The typed path grows much
more slowly over the same grids, so the ratio grows for structural reasons in the
measured regime. This is a stronger statement than quoting a single high endpoint.

The replay-baseline log-log fit is tight on every family
(`R^2 ≥ 0.9994`). The typed-path fit is looser, with `R^2` between `0.8872`
(`3x3`) and `0.9018` (default); on `3x3` in particular the slope estimate
carries wider uncertainty than on the other two families. The ratio fit
itself stays in a narrow band (`R^2` between `0.9695` and `0.9706`) because
the replay-baseline term dominates the log-log behavior of the ratio over
this grid.

![Tablero scaling-law fit across checked families](figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg)

**Figure 2.** The checked scaling-law fit separates the typed path, the replay baseline,
and the ratio curve on the carry-aware experimental backend. The result supports a
measured-regime scaling claim, not an unbounded asymptotic or default-backend claim.

Reproducibility note for Table 2 and Figure 2: regenerate the machine-readable TSV,
JSON, and SVG with `python3 scripts/paper/generate_tablero_scaling_law.py`. The script
uses only Python 3 standard-library code, reads median-of-five millisecond timing rows
from the checked carry-aware experimental evidence, and requires the step grids
`2-1024`, `2-1024`, and `2-1024` for the three families. Its outputs are
`docs/paper/evidence/tablero-carry-aware-experimental-scaling-law-2026-04.tsv`,
`docs/paper/evidence/tablero-carry-aware-experimental-scaling-law-2026-04.json`, and
`docs/paper/figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg`.

### 6.4 What is constant and what is not

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

### 6.5 Causal decomposition

The large ratios are easy to misread if we only quote the frontier numbers. The causal
breakdown shows where the baseline actually spends time.

#### Table 3. Replay baseline decomposition at the checked frontier


| Family           | Proof reverify | Source-chain commitment | Per-step commitment | Manifest finalize | Equality check | Replay total   |
| ---------------- | -------------- | ----------------------- | ------------------- | ----------------- | -------------- | -------------- |
| default (`1024`) | `1,910.784 ms` | `2,256.729 ms`          | `2,280.080 ms`      | `1,869.553 ms`    | `0.122 ms`     | `8,317.269 ms` |
| `2x2` (`1024`)   | `1,440.664 ms` | `2,036.751 ms`          | `2,029.761 ms`      | `1,675.663 ms`    | `0.075 ms`     | `7,182.913 ms` |
| `3x3` (`1024`)   | `1,733.076 ms` | `2,138.166 ms`          | `2,114.333 ms`      | `1,736.131 ms`    | `0.271 ms`     | `7,721.977 ms` |


This is the stronger causal lesson:

- the replay baseline is not one monolithic serialization bottleneck,
- proof re-verification, source-chain commitment rebuild, per-step commitment rebuild,
and manifest finalization each consume a comparable share of replay time, and
- the final equality comparison is negligible.

![Replay baseline breakdown across checked families](figures/tablero-replay-baseline-breakdown-2026-04.svg)

**Figure 3.** At the checked frontiers, replay time is spread across repeated proof
checks and commitment rebuilds rather than one dominant final comparison.

At the same `1024`-step frontiers, compact-proof verification stays between
`1.853 ms` (`2x2`) and `1.936 ms` (`3x3`), and typed-boundary binding stays
between `4.955 ms` (`2x2`) and `5.048 ms` (`3x3`). The verifier gap therefore
comes from removing a bundle of repeated replay work, not from accelerating
cryptographic verification itself.

### 6.6 Red-teaming the constant: an honestly-optimized replay verifier

The frontier ratios in Section 6.2 are measured against the current ordered
manifest-replay implementation. A natural reviewer objection is that the
headline value reads partly as "how much work the typed boundary avoids" and
partly as "how unoptimized the JSON-shaped replay path is." We measured this
explicitly. We added an alternate replay verifier in the engineering lane
that (a) skips per-step embedded proof re-verification (the typed boundary
verifier does the same; the compact projection proof's trace commitment
already binds the trace that includes every step proof's public-output
surface) and (b) commits the chain summary and per-step proof commitments
with a binary canonical encoding over fixed-size cryptographic identities
and the raw stark-proof byte buffer, instead of serializing every nested
proof structure to JSON before hashing. The verifier still rebuilds the
manifest from the chain and equality-checks; only the implementation surface
of the cryptographic-derivation and per-step-proof checks changes.

#### Table 3a. Optimized replay verifier at the `1024`-step frontier

Reproducibility note for Table 3a:

- Backend version: `stwo-phase12-decoding-family-v10-carry-aware-experimental` (the carry-aware experimental execution-proof backend, distinct from the publication-default `stwo-phase12-decoding-family-v9`).
- Optimized-replay manifest version: `stwo-phase30-decoding-step-proof-envelope-optimized-manifest-v1`; manifest scope: `stwo_execution_parameterized_decoding_step_proof_envelope_manifest_optimized_binary_commitments`.
- Optimized-replay benchmark identity: `benchmark_version = stwo-tablero-replay-breakdown-optimized-benchmark-v1`; `semantic_scope = tablero_replay_baseline_optimized_decomposition_over_checked_layout_families_over_phase12_carry_aware_experimental_backend`.
- Timing mode: `measured_median`. Timing policy: `median_of_9_runs_from_microsecond_capture` (canonical; the script also accepts `median_of_5_runs_from_microsecond_capture` for the original measurement, retained for reproducibility). Timing unit: `milliseconds`. Step count: `1024`. Aggregation strategy: `median_total_representative_run`.
- Engineering evidence: `docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.tsv` and `.json`.
- Regeneration: `cargo +nightly-2025-07-14 build --release --features stwo-backend --bin tvm` followed by `BENCH_RUNS=9 CAPTURE_TIMINGS=1 scripts/engineering/generate_tablero_replay_breakdown_optimized_benchmark.sh`. The shell script fails closed if the regenerated payload's identity drifts from this scope, and pins every `EXPECTED_*` identity field when the output paths resolve to the canonical checked-in evidence paths.

This is an explicit experimental-to-paper promotion of an
engineering-only red-team measurement. The optimized verifier is **not**
the publication-default verifier: the manifest format it consumes uses
binary commitments under a distinct version/scope (above), so a
publication-default JSON-keyed manifest is rejected before any equality
check runs.

| Family | Optimized replay total | Original replay total | Speedup | Ratio (optimized replay total : typed boundary verify) |
| --- | ---: | ---: | ---: | ---: |
| default (`1024`) | `2,684.106 ms` | `8,317.269 ms` | `3.1x` | `330.1x` |
| `2x2` (`1024`) | `2,145.775 ms` | `7,182.913 ms` | `3.3x` | `264.2x` |
| `3x3` (`1024`) | `2,170.899 ms` | `7,721.977 ms` | `3.6x` | `261.2x` |

Three facts matter here.

First, the headline replay-avoidance ratios in Section 6.2 (`917x`-`1066x`
at `N = 1024`) tighten to a band of `~261x`-`~330x` once the
optimized-replay verifier replaces the JSON-tax components of the original
path with binary canonical commitments. That is the implementation-cost
component of the headline. The residual ratio is what the typed boundary
genuinely avoids that an optimized replay verifier still pays.

Second, the optimized replay's cost decomposition shows the part of the
replay surface our binary-commitment optimization touches is genuinely
removed: the `source-chain commitment` bucket drops from `~2.3 s` to under
`~1.5 ms` (a `>99%` reduction) and the `per-step proof commitment` bucket
drops from `~2.3 s` to `~110-140 ms` (a `>93%` reduction). What dominates
the optimized-replay total is `manifest_finalize`, in the `~2.0-2.5 s`
band, because it includes the per-step state-derivation work that confirms
every recorded `from_state`/`to_state` pair is consistent with the
program's deterministic re-execution from the recorded initial state. That
structural per-step work is the part of replay the typed boundary truly
removes by relying on the compact projection proof's trace commitment
instead of re-deriving states.

Third, the slope claim (Section 6.3) is unaffected: the ratio still grows
with `N` because the optimized replay surface still scales linearly in `N`
(the `manifest_finalize` per-step state-derivation work is itself
linear-in-`N`), while the typed-boundary verify surface stays sublinear in
`N`. The constant-factor headline is honestly tightened: the
implementation-dependent component of the original `~1000x` figure is a
`~3.1-3.6x` factor, and the residual replay-work component is
`~261-330x` at the checked frontier across the three layout families for
this source-derivation surface.

Variance disclosure. The `manifest_finalize` bucket is host-noise
sensitive at this scale: per-step state derivation over `1024` steps does
not fit comfortably in L2/L3 cache on this host and is sensitive to
background system load. The optimized-replay total inherits that
variance. Across the nine timed runs that produced the median values
above, the per-family ranges of `replay_total_ms` are: `2,018-7,196 ms`
for default (range factor `3.57x`), `1,790-8,083 ms` for `2x2` (range
factor `4.52x`), and `1,865-4,906 ms` for `3x3` (range factor `2.63x`).
Combined with the family-matrix typed-boundary verify times
(`8.121-8.311 ms`) those single-run extremes correspond to a
worst-case-extreme ratio interval of roughly `~215x-~995x` across the
three families; the median policy suppresses single-run outliers but the
underlying distribution is wide. The conservative reading of Table 3a is
therefore the order-of-magnitude band (`~10^2-10^3` ratio at the checked
frontier on this host), not the specific cell values, and a quieter
measurement environment or a substantially larger sample count would be
needed to tighten the constants further. We treat that as a
measurement-quality limitation of the present study, not as an
instability in the structural claim of Section 6.3.

### 6.7 Supporting second boundary on a distinct source surface

The paper should not rely on only one replay-avoidance surface. The current empirical
lab also includes a second typed boundary on a distinct emitted-source surface.

This second boundary is not the paper's timing headline. Its verifier-side savings are
much smaller than the main replay baseline because the removed source-side derivation
work is smaller. But it is still structurally important because it shows that the
pattern is not singular to one replay surface.

#### Table 4. Supporting second-boundary publication checkpoint


| Surface                      | Checked point | Typed-boundary verify | Replay baseline verify | Ratio   |
| ---------------------------- | ------------- | --------------------- | ---------------------- | ------- |
| conservative publication row | `2`           | `0.857 ms`            | `1.045 ms`             | `1.22x` |


Evidence handle: [TSV](evidence/phase43-source-root-feasibility-publication-2026-04.tsv)
and [JSON](evidence/phase43-source-root-feasibility-publication-2026-04.json).

The supporting point matters because it is a distinct emitted-source surface, not
because it is large. The paper-facing claim here is only that the second surface clears
honestly on the conservative publication row.

A broader engineering sweep over the same surface is checked in the engineering lane,
but it is not promoted here as a paper-facing performance claim.

The right interpretation is narrow:

- the emitted-source boundary is a real second typed boundary,
- the gain is modest compared with the paper's main replay-elimination result, and
- the result is supporting transfer evidence rather than a second headline curve.

So this second result is supporting transfer evidence, not a replacement headline.

### 6.8 Bounded compactness no-go

The paper also includes one bounded no-go because that is part of the pattern's honest
boundary.

We evaluated a narrower handoff object on the conservative publication lane. It does
reduce serialized bytes, but it does not remove the ordered replay dependency that
dominates verifier time on that surface.

That means the handoff object is useful as a compactness result, but not as a
replay-avoidance result. In the checked median-of-five publication evidence, it is
smaller on bytes but slower on verifier time because the verifier still rebuilds the
same ordered replay surface underneath the compact object.

This is not a failure of the theorem. It is an example of the theorem's applicability
boundary:

1. a compact object alone is not enough if it does not remove replay from the verifier,
  and
2. not every smaller verifier-facing object should be promoted as a replay-elimination
  boundary.

---

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

---

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
pay the same constant factors. Section 6.6 reports the explicit red-team
measurement: an honestly-optimized replay verifier that skips per-step
embedded proof re-verification and uses binary canonical commitments
instead of JSON-serialize-then-hash narrows the headline ratio at the
checked frontier to a host-noise band of `~261x`-`~330x` at median of
nine. The `~3.1x`-`~3.6x` reduction is the implementation-cost component
of the headline; the residual `~261x`-`~330x` band is
the remaining measured replay-work component for this implementation's
source-derivation semantics and reflects work the typed boundary genuinely
avoids.

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

The recorded compactness no-go exists precisely to show that we are not smoothing over
this constraint.

---

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
families, a supporting second typed boundary on a distinct source surface, and one
bounded compactness no-go that marks where the pattern does not yet apply.

This is not the end of the story. Several open directions remain in the
broader space: broader cryptographic-backend transfer, stronger external
calibration against deployed verifiers, a recursive layer that preserves
the same boundary semantics, and prover-side cost reductions that make
end-to-end transformer proving practical at production scale. Whether
those directions are pursued by the authors of this paper or by other
groups, the present contribution remains a self-contained verifier-side
pattern with a stated soundness criterion and measured replay-avoidance
evidence on the carried-state surface that transformer decode naturally
exposes.

---

## References

1. NANOZK authors. *Public transformer-proof abstract and verifier-object metrics*. Public materials cited in the package calibration note.
2. BitSage. *Obelyzk public verifier object on Starknet Sepolia*. Public docs.rs materials for `obelyzk` 0.3.0.
3. BitSage. *Obelyzk paper and Starknet Sepolia gas figures*. Public paper linked from the `obelyzk` 0.3.0 docs.rs package.
4. Percepta. *Can LLMs Be Computers?* Public research note.
5. Hakim AbdelStark. *Can LLMs be PROVABLE computers?* Public research note. Names the bridge as `the trace becomes the witness`.
6. Omar Espejel. *Why STARK Execution Structure Fits Transformer Workloads*. `blog.espejel.lol`, 2026-04-15 (updated 2026-04-21).
