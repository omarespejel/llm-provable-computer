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
- one direct shared-normalization proof reused across `2` fixed primitive steps,
- one frozen transformer-shaped tensor-native bundle under
  `docs/paper/artifacts/stwo-tensor-native-transformer-shaped-v1-2026-04-21/`,
- one `4`-step typed carried-state chain over the primitive template,
- one Gemma-shaped core-slice artifact binding that chain to a real
  `gemma_block_v4` S-two proof plus shared-normalization and shared-activation
  receipts,
- one frozen repeated-slice bundle under
  `docs/paper/artifacts/stwo-repeated-gemma-slice-accumulation-v1-2026-04-21/`,
- one Phase94.75 richer slice binding selected memory-window rows plus score,
  grouped-value, residual, normalization, and activation invariants, and
- one Phase95 repeated-slice accumulation artifact over `4` Gemma-like slices
  that reuses `90,432` shared proof bytes instead of `361,728` naive repeated
  proof bytes and saves `3,998,305` JSON bytes versus duplicating the richer
  slice `4` times,
- one frozen richer multi-interval bundle under
  `docs/paper/artifacts/stwo-richer-multi-interval-gemma-v1-2026-04-21/`,
- one explicit Phase99 multi-interval source artifact at `1,036,298` JSON
  bytes,
- one Phase101.5 folded multi-interval prototype at `5,214` JSON bytes, about
  `0.5031%` of the explicit surface, and
- one Phase102 richer verifier-bound derivative at `7,100` JSON bytes, about
  `0.6851%` of the explicit surface and only `1,886` bytes above the thinner
  folded prototype.

That means Phase91 through Phase95 are no longer only roadmap items. The next
meaningful work is no longer "can we derive one multi-interval folded object at
all?" The repository can already do that. The next meaningful work is
transformer-specific accumulation or folding on top of this frozen repeated and
multi-interval line, not more wrapper layers.

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

## Phase94.5: Gemma block core slice

Goal:

- prove that the transformer-shaped tensor-native line can bind to one real
  Gemma-like execution proof instead of stopping at a synthetic chain alone.

Primary code surfaces:

- `src/stwo_backend/tensor_native_artifact.rs`
- `src/bin/tvm.rs`
- `scripts/paper/generate_stwo_tensor_native_transformer_bundle.sh`

Deliverables:

- one verifier-checked core-slice artifact over `gemma_block_v4`,
- one nested proof binding between the `4`-step chain artifact and the
  underlying S-two execution proof,
- one shared-normalization row-set commitment,
- one shared-activation row-set commitment, and
- one frozen bundle that records the end-to-end artifact hashes and timings.

Stop condition:

- the repository can point to one real Gemma-shaped tensor-native artifact line
  without claiming full-block tensor-native proving or recursive aggregation.

## Phase94.75: richer Gemma slice

Goal:

- strengthen the Gemma-shaped artifact line without jumping to a full Gemma
  block.

Primary code surfaces:

- `src/stwo_backend/tensor_native_artifact.rs`
- `src/bin/tvm.rs`
- `tests/cli.rs`
- `scripts/paper/generate_stwo_repeated_gemma_slice_accumulation_bundle.sh`

Deliverables:

- one richer-slice artifact over `gemma_block_v4`,
- one selected-memory-window commitment,
- bound local/global score, grouped-value, residual, normalization, and
  activation summaries, and
- negative mutations for summary drift and commitment drift.

Stop condition:

- the repository can point to one Gemma-shaped slice artifact that says more
  than "this proof existed" and less than "we proved the whole block directly."

## Phase95: repeated Gemma-slice accumulation

Goal:

- turn repeated Gemma-like structure into a benchmarkable repeated-slice
  artifact surface.

Deliverables:

- one repeated-slice accumulation artifact over multiple block-indexed members,
- one frozen bundle with exact timings, hashes, and byte-level reuse metrics,
- explicit comparison against naive repeated proof duplication and naive repeated
  richer-slice duplication, and
- verifier checks that reject member drift, block-index drift, and shared proof
  substitution.

Stop condition:

- the repository can point to one honest repeated-structure result without
  pretending that repeated-slice reuse is already recursive cryptographic
  compression.

## Phase96: transformer-specific folding / accumulation design

Goal:

- design the real compression step only after the repository already has a
  frozen repeated-slice benchmark surface.

Deliverables:

- a design note or first prototype with an explicit novelty boundary:
  transformer-specific accumulation or folding with shared lookup tables and
  carried state, not generic AIR or CCS folding.

Stop condition:

- the design starts from the real Phase95 repeated-slice artifact and does not
  speculate about savings that the repository cannot already ground.

## Phase96.5: first folded repeated-slice prototype

Goal:

- derive the first compact folded repeated-slice artifact directly from the
  explicit Phase95 repeated Gemma-slice accumulation surface.

Deliverables:

- one `Phase965FoldedGemmaSliceAccumulationArtifact`,
- bounded contiguous folded groups over the explicit Phase95 members,
- verifier checks that recompute those folded groups from the Phase95 source,
- negative mutations for source-binding drift, group drift, and accumulator
  drift.

Stop condition:

- the repository can point to one smaller folded repeated-slice derivative that
  stays explicitly bound to the Phase95 source artifact and still makes no
  recursion claim.

## Phase97: frozen explicit-vs-folded benchmark bundle

Goal:

- freeze one publication-facing benchmark bundle that compares explicit repeated
  accumulation against the first folded derivative over the same Gemma-like
  slice interval.

Deliverables:

- one frozen artifact directory under `docs/paper/artifacts/`,
- exact JSON-byte deltas for explicit vs folded accumulation,
- exact timings and SHA-256 hashes,
- one appendix-ready index explaining the claim boundary.

Stop condition:

- the repository can point to one reproducible explicit-vs-folded benchmark
  bundle with exact hashes and byte deltas, not only in-memory structs.

## Phase98: richer folded Gemma slice family

Goal:

- extend the folded line from repeated-slice totals to a richer family summary
  that still stays source-bound and pre-recursive.

Deliverables:

- one `Phase98FoldedGemmaRicherSliceFamilyArtifact`,
- selected-memory-window family commitment,
- richer invariant-summary family commitment,
- family-level score / residual / normalization / activation summaries, and
- verifier checks for family-commitment and summary drift.

Stop condition:

- the repository can point to one compact richer-family derivative that is
  anchored to both the explicit Phase95 source artifact and the Phase96.5
  folded artifact.

## Phase99: multi-interval richer-family accumulation

Goal:

- move from one repeated Gemma-like interval to several token-position-indexed
  interval families over the same shared proof surface.

Deliverables:

- one explicit multi-interval richer-family accumulation artifact,
- interval members indexed by token position and bound to canonical Phase95,
  Phase96.5, and Phase98 reconstructions,
- verifier checks for interval-member drift and token-position-stride drift,
- and explicit aggregate score / residual / normalization / activation
  summaries across intervals.

Stop condition:

- the repository can point to one honest explicit accumulation surface over
  multiple interval families instead of one folded interval only.

## Phase100: frozen multi-interval benchmark bundle

Goal:

- freeze the first publication-facing benchmark directory that compares
  explicit multi-interval accumulation against the folded multi-interval
  prototype.

Deliverables:

- one frozen artifact directory under `docs/paper/artifacts/`,
- exact byte deltas for:
  - naive single-interval explicit accumulation duplication vs explicit
    multi-interval
    accumulation,
  - explicit multi-interval accumulation vs folded multi-interval prototype,
- exact timings and SHA-256 hashes,
- and one appendix-ready index explaining the claim boundary.

Stop condition:

- the repository can point to one reproducible multi-interval benchmark bundle
  with exact hashes, byte deltas, and handoff commitments.

Current checkpoint:

- `docs/paper/artifacts/stwo-multi-interval-folded-gemma-v1-2026-04-21/`
  now freezes the first Phase99/101.5 benchmark bundle.
- It records `1,036,298` explicit multi-interval JSON bytes versus `5,214`
  folded multi-interval prototype bytes.
- It also records `4,126,700` bytes for blind duplication of the
  single-interval explicit accumulation artifact, so the Phase99 artifact saves
  `3,090,402` bytes before the first folded derivative is even applied.
- The folded prototype then saves a further `1,031,084` bytes relative to the
  explicit multi-interval source artifact while remaining pre-recursive.

## Phase101: accumulation handoff design

Goal:

- define the smallest honest handoff object that a later recursive or
  cryptographic accumulation layer would consume.

Deliverables:

- one design note capturing the handoff boundary,
- one stable accumulation handoff commitment in the folded prototype line, and
- explicit non-claims distinguishing the handoff surface from actual recursion.

Stop condition:

- the repository can point to a stable handoff object rather than skipping from
  explicit interval members straight to vague future recursion claims.

## Phase101.5: first folded multi-interval prototype

Goal:

- derive the first compact folded prototype over several explicit interval
  families.

Deliverables:

- one folded multi-interval prototype artifact,
- bounded folded groups over Phase99 interval members,
- one accumulation handoff commitment,
- one folded prototype accumulator commitment, and
- verifier checks for group drift and handoff drift.

Stop condition:

- the repository can point to one explicit multi-interval source and one
  smaller folded multi-interval derivative that stays verifier-bound and
  pre-recursive.

## Phase102: richer multi-interval family derivative

Goal:

- reintroduce more transformer-shaped family structure on top of the folded
  multi-interval handoff without pretending that this is already recursive
  compression.

Deliverables:

- one `Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact`,
- explicit bindings to the Phase99 source and Phase101.5 folded commitments,
- verifier-enforced sequence commitments for token positions, Phase98 members,
  selected memory-window families, and invariant-summary families, and
- negative mutations that reject richer-family sequence drift.

Frozen result:

- bundle:
  `docs/paper/artifacts/stwo-richer-multi-interval-gemma-v1-2026-04-21/`
- explicit Phase99 multi-interval JSON bytes: `1,036,298`
- Phase101.5 folded prototype JSON bytes: `5,214`
- Phase102 richer-family JSON bytes: `7,100`
- Phase101.5 folded ratio vs explicit: `0.005031`
- Phase102 richer-family ratio vs explicit: `0.006851`
- richer-family overhead above folded prototype: `1,886` bytes

Stop condition:

- the repository can point to one richer verifier-bound multi-interval
  derivative that remains much smaller than the explicit source while carrying
  more transformer-shaped family structure than the bare folded prototype.

## Phase103: frozen richer multi-interval benchmark bundle

Goal:

- freeze the new richer multi-interval line into a publication-facing artifact
  bundle with exact commands, timings, hashes, and comparison notes.

Deliverables:

- bundle generator:
  `scripts/paper/generate_stwo_richer_multi_interval_gemma_bundle.sh`
- frozen bundle:
  `docs/paper/artifacts/stwo-richer-multi-interval-gemma-v1-2026-04-21/`
- appendix artifact index, artifact summary TSV, comparison TSV, and hashes.

Frozen result:

- shared execution proof bytes: `90,432`
- explicit multi-interval JSON bytes: `1,036,298`
- folded multi-interval JSON bytes: `5,214`
- folded richer multi-interval JSON bytes: `7,100`
- folded prototype / explicit ratio: `0.5031%`
- richer-family / explicit ratio: `0.6851%`
- explicit vs naive single-interval duplication savings: `3,090,402` bytes

Stop condition:

- the repository has one citation-grade richer multi-interval bundle rather
  than only local JSON outputs.

## Phase104: richer multi-interval accumulation design

Goal:

- state clearly what the richer multi-interval derivative means and what later
  accumulation work must consume from it.

Deliverables:

- design note:
  `docs/engineering/design/phase104-richer-multi-interval-accumulation-spec.md`
- explicit non-claims separating this surface from recursion, IVC, or final
  cryptographic compression.

Stop condition:

- later accumulation work can start from a stable handoff object instead of
  redefining the richer multi-interval surface ad hoc.

## Research answer this roadmap aims to produce

If the roadmap succeeds, the repository should be able to support the following
claim cleanly:

> STARK-native proving is structurally attractive for transformer workloads not
> because "a VM can be wrapped in a STARK," but because repeated
> lookup-heavy, tensor-shaped, state-carrying relations can be expressed
> directly, packaged with verifier-enforced continuity, and then benchmarked in
> repeated-slice form before any recursive compression claims are made.

That is a stronger and more defensible result than another layer of VM-manifest
composition.
