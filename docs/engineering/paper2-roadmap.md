# Paper 2 Engineering Roadmap

This note maps the current bounded paper-2 scope into concrete implementation
sequencing and hardening work.

## Roadmap scope

Implementation goals this roadmap supports:

- proof-carrying decode surfaces,
- carried-state validity,
- statement-preserving pre-recursive aggregation boundaries.

The roadmap below stays inside those verifier boundaries and does not assume
that recursive compression is already available.

## Current status

The repository is already strong enough for the bounded paper-2 claim:

- carried-state packaging layers are implemented through the current
  pre-recursive aggregation boundary,
- recursive-adjacent Phase 29, Phase 30, and Phase 31 boundary artifacts
  exist,
- a Phase 32 statement contract now restates the same public decode boundary
  that future recursive compression must preserve,
- a Phase 33 public-input manifest now freezes the exact ordered public inputs
  that a future recursive verifier must preserve over that same statement,
- a Phase 34 shared-lookup manifest now freezes the ordered lookup-facing
  public inputs a future recursive/shared-table verifier would need to preserve
  over that same statement,
- a Phase 35 target manifest now unifies the Phase 32, Phase 33, and Phase 34
  preserved commitments into one canonical recursive target artifact,
- a Phase 36 verifier harness receipt now records that the exact Phase 35
  target and its Phase 32, Phase 33, and Phase 34 sources were checked by the
  repository verifier path, without claiming recursive compression,
- bounded multi-runtime semantic-agreement artifacts exist,
- Hugging Face provenance manifests exist as reproducibility artifacts,
- ONNX-facing provenance now binds exported graph, metadata companion, and
  declared external-data side files,
- attestation-friendly subject digests plus optional builder/source release
  metadata now exist on the HF provenance surface,
- the HF provenance surface can now also bind an external in-toto/SLSA-style
  statement file as a narrow release-layer identity projection,
- ONNX-facing provenance now also binds exporter identity and graph-constraint
  identity where metadata exposes those constraints,
- parser/verifier hardening has materially improved the trust boundary around
  those surfaces.

## Remaining engineering priorities

### 1. Keep hardening the exact paper-facing verifier boundaries

Focus on:

- carried-state package verification,
- recursive-compression input contract verification,
- step-envelope manifest verification,
- decode-boundary bridge manifest verification,
- recursive statement-contract verification,
- recursive public-input manifest verification,
- recursive shared-lookup manifest verification,
- `research-v3` artifact verification,
- HF provenance manifest verification.

This work remains highest leverage because the paper’s main claim is that these
verifier boundaries define the repository’s current reproducibility and
statement-stability envelope.

### 2. Keep provenance binding honest beyond the current ONNX identity layer

The next substantive gap is no longer basic ONNX sidecar binding, exporter
identity, or graph-constraint identity on the local manifest surface. It is
stronger externally signed provenance over the same release boundary.

Concrete targets:

- preserve external-file identity where ONNX layout requires it,
- keep the new builder/source metadata aligned with signed attestation subjects
  rather than proof semantics,
- keep external statement binding narrow and machine-checkable at the release
  layer,
- add full external signature/trust-chain verification only as a release-layer
  extension, not as a proof-semantics claim,
- keep the claim phrased as provenance/reproducibility, not proof semantics.

### 3. Keep semantic-agreement artifacts bounded

Do not let the runtime-consistency line drift into a false general-equivalence
claim.

Concrete rule:

- every public description must keep `research-v3` in the bounded
  semantic-agreement bucket,
- hardening should continue to focus on manifest, trace, event, and commitment
  mismatch rejection.

### 4. Keep the recursive-adjacent decode boundary explicit

The repository now has the exact bridge that later recursive work should
consume: a Phase 31 manifest that binds the Phase 29 recursive-compression
input contract to the Phase 30 ordered decode-envelope manifest without
changing the public decode statement, a Phase 32 contract that restates that
same boundary as the public recursive target, and a Phase 33 manifest that
freezes the exact ordered public inputs a recursive verifier would need to
preserve. The repository now also has a Phase 34 manifest that freezes the
ordered lookup-facing public inputs already exposed by the Phase 30 step
envelopes. The new Phase 35 target manifest binds those preserved surfaces into
one canonical recursive target commitment. The Phase 36 verifier harness
receipt then records that the target verifier was run against those exact source
artifacts. It is useful operational evidence, but it is still not recursive
proof closure.

That means the next recursive work should preserve:

- the existing decode statement,
- the existing start/end carried-state boundary semantics,
- the existing package commitments already exposed by the repository,
- the Phase 32 public statement contract derived from that bridge.
- the Phase 33 public-input ordering and commitments derived from that
  contract.
- the Phase 34 shared-lookup ordering and commitments derived from those public
  inputs and the Phase 30 envelopes.
- the Phase 35 unified recursive target commitment derived from Phase 32,
  Phase 33, and Phase 34.
- the Phase 36 source-bound verifier receipt over that target, as an
  operational check rather than a compressed proof.

### 5. Then move to recursive compression

Recursive work should come after the public decode statement is stable enough
that recursion preserves a claim the repository already exposes cleanly.

That means the next recursive milestone should be phrased as:

- recursion over the existing decode boundary,

not:

- a new statement surface invented by the recursive layer itself.

## Claim boundary reminder

The associated paper draft phrases the bounded publication claim as
proof-carrying decode surfaces, carried-state validity, and
statement-preserving pre-recursive aggregation boundaries. This engineering note
exists to sequence the implementation work that keeps those boundaries honest.

## Practical next step

The next concrete engineering slice should be:

1. keep the expanded HF provenance verifier narrow and explicit about what is
   local identity binding and external statement binding versus what would still
   require external signed attestation verification,
2. keep the Phase 31 decode-boundary bridge, Phase 32 recursive statement
   contract, Phase 33 public-input manifest, Phase 34 shared-lookup manifest,
   Phase 35 target manifest, and Phase 36 verifier harness receipt narrow and
   explicit about what is bound from earlier artifacts versus what would require
   actual recursive verification,
3. then recurse over that existing decode boundary and public-input ordering
   rather than inventing a new statement surface.
