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
- recursive-adjacent Phase 29 and Phase 30 boundary artifacts exist,
- bounded multi-runtime semantic-agreement artifacts exist,
- Hugging Face provenance manifests exist as reproducibility artifacts,
- ONNX-facing provenance now binds exported graph, metadata companion, and
  declared external-data side files,
- attestation-friendly subject digests plus optional builder/source release
  metadata now exist on the HF provenance surface,
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
- add externally signed provenance only as a release-layer extension, not as a
  proof-semantics claim,
- keep the claim phrased as provenance/reproducibility, not proof semantics.

### 3. Keep semantic-agreement artifacts bounded

Do not let the runtime-consistency line drift into a false general-equivalence
claim.

Concrete rule:

- every public description must keep `research-v3` in the bounded
  semantic-agreement bucket,
- hardening should continue to focus on manifest, trace, event, and commitment
  mismatch rejection.

### 4. Then move to recursive compression

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
   local identity binding versus what would require external signed
   attestations,
2. then recurse over the existing decode boundary rather than inventing a new
   statement surface.
