# Tensor-Native Phase89-95 Roadmap

This note records the post-freeze plan after the bounded decode bridge and the
translated composition prototype. The core decision is simple:

- keep the proof-carrying decode / carried-state line as a bounded artifact line,
- stop treating more VM-manifest wrappers as the main breakthrough path,
- move the main breakthrough route to tensor-native, lookup-aware S-two proofs.

## Why this roadmap exists

The repository now has two different kinds of value:

1. a strong semantics and verifier-boundary machine:
   - proof-carrying decode surfaces,
   - carried-state binding,
   - manifest hardening,
   - negative and tamper-path testing,
   - source-bound artifact packaging.
2. an unfinished but more breakthrough-relevant tensor line:
   - first-layer relation claims,
   - MLE / PCS opening claims,
   - shared lookup identity,
   - typed carried state,
   - transformer-shaped transition artifacts.

The second line is the one that can answer the stronger question:

> are transformer workloads structurally better served by STARK-native proving
> surfaces than by generic circuit lowering?

## Current checkpoint

The first result-bearing step on this line now exists:

- one frozen tensor-native `stwo` primitive bundle under
  `docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/`,
- one verifier-enforced canonical normalization table identity,
- one table-registry commitment,
- one direct shared-normalization proof reused across `2` fixed primitive steps.

That means Phase91 and Phase92 are no longer only roadmap items. The next
meaningful work is Phase93 and Phase94: short typed carried-state chaining on
top of a real primitive line, then a frozen transformer-shaped tensor-native
bundle.

## Phase89: upstream sync audit

Goal:

- refresh local `stwo-cairo` inspection clones,
- re-check the published `stwo` crate line,
- stop carrying stale upstream assumptions into the next implementation wave.

Deliverables:

- refreshed audit note in
  `docs/engineering/design/stwo-upstream-sync-audit-2026-04-21.md`,
- explicit recognition that the latest published crate line is still `2.2.0`,
- explicit recognition that `stwo-cairo` removed the old `cairo-prove` CLI and
  now points developers to `proving-utils` / `scarb prove`.

Stop condition:

- local upstream assumptions are current,
- no repository doc implies a newer semver crate than actually exists.

## Phase90: freeze the bounded decode artifact

Goal:

- keep the proof-checked decode bridge as citation-grade supporting evidence,
- stop extending it as though it will by itself become cheap transformer
  proving.

Deliverables:

- frozen artifact pointer to
  `docs/paper/artifacts/phase70-80-proof-checked-decode-bridge-v1-2026-04-21/`,
- roadmap wording that treats the decode line as supporting evidence and
  semantics infrastructure.

Stop condition:

- no new wrapper layer is added just to make the decode line look more like
  recursion or compression.

## Phase91: shared-table reuse across multiple steps

Goal:

- turn shared lookup identity into operational reuse on the tensor line.

Primary code surfaces:

- `src/stwo_backend/shared_lookup_artifact.rs`
- `src/stwo_backend/lookup_component.rs`
- `src/stwo_backend/lookup_prover.rs`
- `src/stwo_backend/normalization_component.rs`
- `src/stwo_backend/normalization_prover.rs`

Deliverables:

- one canonical lookup-table identity reused across multiple openings or steps,
- verifier checks that reject mismatched reused-table claims,
- negative mutations for swapped table identity, row drift, and multiplicity
  drift.

Stop condition:

- reuse is verifier-enforced and source-bound, not just repeated metadata.

## Phase92: one real transformer primitive over S-two

Goal:

- stop proving wrapper artifacts and prove one transformer-relevant relation
  directly in custom S-two AIR.

Preferred first primitive:

- normalization first, because the repository already contains a real
  normalization lookup surface and can convert that into a stronger
  transformer-native relation with the least wasted motion.

Fallback primitive:

- attention-score lookup path, if the normalization path proves too weak as a
  narrative step.

Primary code surfaces:

- `src/stwo_backend/normalization_component.rs`
- `src/stwo_backend/normalization_prover.rs`
- `src/stwo_backend/arithmetic_component.rs`
- `src/stwo_backend/arithmetic_subset_prover.rs`

Deliverables:

- one direct primitive claim,
- one direct primitive proof path,
- one verifier path,
- one benchmarkable fixed-shape artifact,
- negative mutations for malformed witness rows and table mismatches.

Stop condition:

- the repository can point to at least one transformer-relevant primitive proved
  directly in S-two rather than only via VM/decode composition.

## Phase93: chain 2-4 primitive steps with typed carried state

Goal:

- combine tensor-native proving with the carried-state machinery that already
  exists.

Primary code surfaces:

- `src/stwo_backend/decoding.rs`
- `src/stwo_backend/shared_lookup_artifact.rs`
- `src/stwo_backend/normalization_prover.rs`

Deliverables:

- typed carried-state links across a short primitive chain,
- continuity checks that reject step reordering and boundary substitution,
- one short chain artifact that preserves explicit start/end boundaries.

Stop condition:

- the repository has a short tensor-native chain with enforced continuity, not
  just isolated primitive proofs.

## Phase94: freeze a transformer-shaped S-two artifact bundle

Goal:

- package the tensor-native line into publication-facing evidence.

Required metrics:

- prove time,
- verify time,
- proof bytes,
- carried-state boundary identity,
- shared-table identity,
- negative mutation outcomes.

Deliverables:

- a frozen bundle under `docs/paper/artifacts/`,
- one publication-facing table row surface,
- one source-bound appendix index.

Stop condition:

- the artifact line is citeable and reproducible without implying full
  standard-softmax closure.

## Phase95: transformer-specific folding / accumulation design

Goal:

- move to accumulation only after a real tensor-native artifact exists.

Deliverables:

- a design note, not a premature proof claim,
- explicit novelty boundary:
  transformer-specific accumulation with shared lookup tables and carried state,
  not generic AIR or CCS folding.

Stop condition:

- the design starts from a real Phase92-94 artifact and does not speculate about
  savings that current artifacts do not justify.

## Research answer this roadmap aims to produce

If the roadmap succeeds, the repository should be able to support the following
claim cleanly:

> STARK-native proving is structurally attractive for transformer workloads not
> because "a VM can be wrapped in a STARK," but because repeated
> lookup-heavy, tensor-shaped, state-carrying relations can be expressed
> directly and packaged with verifier-enforced continuity.

That is a stronger and more defensible result than another layer of VM-manifest
composition.
