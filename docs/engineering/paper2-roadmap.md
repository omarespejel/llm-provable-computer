# Paper 2 Engineering Roadmap

This note turns the second-paper draft boundary into concrete implementation
work.

The target paper claim is:

- proof-carrying decode surfaces,
- carried-state validity,
- statement-preserving pre-recursive aggregation boundaries.

The roadmap below is intentionally scoped to that claim. It does not assume that
recursive compression is already available.

## Current status

The repository is already strong enough for the bounded paper-2 claim:

- carried-state packaging layers are implemented through the current
  pre-recursive aggregation boundary,
- recursive-adjacent Phase 29 and Phase 30 boundary artifacts exist,
- bounded multi-runtime semantic-agreement artifacts exist,
- Hugging Face provenance manifests exist as reproducibility artifacts,
- ONNX-facing provenance now binds exported graph, metadata companion, and
  declared external-data side files,
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

This work remains highest leverage because the paper’s main claim is about
public statement stability at those boundaries.

### 2. Extend provenance binding toward attestation-friendly release metadata

The next substantive gap is no longer basic ONNX sidecar binding. It is richer
attestation-friendly provenance over the same release surface.

Concrete targets:

- bind exporter identity more explicitly,
- bind graph-constraint identity where exporter metadata exposes it,
- preserve external-file identity where ONNX layout requires it,
- add richer release/build metadata without letting the claim drift into proof
  semantics,
- keep the claim phrased as provenance/reproducibility, not proof semantics.

### 3. Keep semantic-agreement artifacts bounded

Do not let the runtime-consistency line drift into a false general-equivalence
claim.

Concrete rule:

- every public description must keep `research-v3` in the bounded
  semantic-agreement bucket,
- hardening should continue to focus on manifest, trace, event, and commitment
  mismatch rejection.

### 4. Only then move to recursive compression

Recursive work should come after the public decode statement is stable enough
that recursion preserves a claim the repository already exposes cleanly.

That means the next recursive milestone should be phrased as:

- recursion over the existing decode boundary,

not:

- a new statement surface invented by the recursive layer itself.

## Practical next step

The next concrete engineering slice should be:

1. one more targeted verifier/tamper pass over the expanded HF provenance
   manifest surface,
2. then attestation-friendly release-metadata hardening over the same bounded
   provenance claim.
