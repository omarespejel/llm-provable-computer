# Phase44D Final Boundary Acceptance

Control issue: <https://github.com/omarespejel/provable-transformer-vm/issues/180>

## Purpose

Phase44D is the adversarial acceptance boundary for the current
compression-route probe. It documents when the project may set:

```text
useful_compression_boundary = true
```

The current answer is deliberately:

```text
useful_compression_boundary = false
```

until an externally emitted canonical source root is verified and the compact
proof is shown to bind that same source root.
The typed source-emission evidence path also must fail closed on replay or
expected-row drift for the chosen `total_steps`; local self-consistency is not
enough.

This phase now has a narrow Rust verifier surface:

- `Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary`
- `Phase44DHistoryReplayProjectionSourceEmission`
- `Phase44DHistoryReplayProjectionSourceEmissionPublicOutput`
- `Phase44DHistoryReplayProjectionSourceEmittedRootArtifact`
- `Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure`
- `Phase44DRecursiveVerifierPublicOutputHandoff`
- `Phase44DRecursiveVerifierPublicOutputAggregation`
- `Phase45RecursiveVerifierPublicInputBridge`
- `Phase45RecursiveVerifierPublicInputLane`
- `derive_phase44d_history_replay_projection_terminal_boundary_logup_closure(...)`
- `verify_phase44d_history_replay_projection_terminal_boundary_logup_closure(...)`
- `emit_phase44d_history_replay_projection_source_chain_public_output_boundary(...)`
- `emit_phase44d_history_replay_projection_source_emission(...)`
- `emit_phase44d_history_replay_projection_source_emission_public_output(...)`
- `project_phase44d_history_replay_projection_source_emission_public_output(...)`
- `phase44d_prepare_recursive_verifier_public_output_handoff(...)`
- `phase44d_prepare_recursive_verifier_public_output_aggregation(...)`
- `phase45_prepare_recursive_verifier_public_input_bridge(...)`
- `verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(...)`
- `verify_phase44d_history_replay_projection_source_emission_acceptance(...)`
- `verify_phase44d_history_replay_projection_source_emission_public_output_acceptance(...)`
- `verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(...)`
- `verify_phase44d_recursive_verifier_public_output_handoff(...)`
- `verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(...)`
- `verify_phase44d_recursive_verifier_public_output_aggregation(...)`
- `verify_phase45_recursive_verifier_public_input_bridge(...)`
- `verify_phase45_recursive_verifier_public_input_bridge_against_sources(...)`

The source path now has a direct producer API for the typed source-emission
public output and a source-chain public output boundary. The verifier checks
that source-chain boundary before delegating to the compact/source proof
verifier. The recursion module now adds a narrow recursive-verifier handoff and
an aggregation manifest over those handoffs. Both surfaces commit to the
source-chain public output boundary, compact proof reference, source-root
acceptance, and no-replay flags while preserving `O(boundary_width)` verifier
complexity.

The terminal boundary LogUp closure is now a first-class typed object. It
binds the public boundary LogUp sum and the compact component claimed sum under
the Stwo-Cairo cancellation shape:

```text
public_boundary_logup_sum + terminal_boundary_component_claimed_sum == 0
```

Phase45 freezes the ordered public-input lanes consumed by the future recursive
verifier adapter. This bridge is deliberately not a recursive proof adapter; it
is a canonical public-input contract that rejects reordered lanes, stale
handoffs, stale compact envelopes, and false recursive/compression claims.

It is still not a publication-grade recursive proof, because the current repo
does not yet contain a recursive verifier that proves this handoff inside a
proof system. In short: this is a source-emission public output and
emitted-root artifact, plus a recursive-verifier handoff boundary. It is not completed recursive proof closure.
It is also not yet a publication-grade source emission proof, because the
upstream source-chain proof still has to emit this boundary as its own public
output.

## Why The Boundary Must Stay False

Phase42 established the core rule for this route: witness-only compatibility is
not a success condition. A later phase may keep the route alive with bounded
source-binding probes, but a final useful-compression claim needs more than a
locally self-consistent manifest.

The dangerous false-positive pattern is:

```text
local checker recomputes local root
local claim points at that root
local compact proof points at that root
therefore useful_compression_boundary = true
```

That pattern is not acceptable. It can pass even when the source side never
emitted the root, when the claim is stale, or when the compact proof is bound to
a different statement than the one the source artifact actually produced.

The boundary must remain false because all of these attacks are possible
without an externally emitted canonical source root:

| Attack | Why it is not useful compression |
|---|---|
| `missing_source_root` | The checker can only prove that its own local serialization is self-consistent. |
| `mismatched_source_root` | The compact path may bind a root that is not the canonical source artifact. |
| `stale_source_claim` | A prior source surface, claim epoch, or row layout can be replayed as if it were current. |
| `compact_proof_mismatch` | A proof or transcript commitment can be detached from the source root it is supposed to compress. |

False is therefore the safe state, not a failure of progress. It means the
route is still a bridge/probe, not a final useful-compression result.

## Acceptance Contract

Phase44D accepts useful compression only if all of the following are true:

1. The source side externally emits a canonical source root.
2. The verifier independently recomputes the canonical source root from the
   canonical source preimage.
3. The externally emitted canonical source root equals the independently
   recomputed canonical source root.
4. The source claim is fresh: it binds the current source-surface version, the
   current claim epoch, and the externally emitted canonical source root.
5. The compact proof binds the same externally emitted canonical source root.
6. The compact proof commitment matches the compact proof payload and
   transcript being checked.

Equivalently:

```text
useful_compression_boundary =
  external_source_root_present
  && external_source_root_verified
  && external_source_root == canonical_source_root(source_preimage)
  && fresh_source_claim_binds(external_source_root)
  && compact_proof_binds(external_source_root)
  && compact_proof_commitment_matches_payload
```

If any term is false, the only acceptable decision is:

```json
{
  "accepted": false,
  "useful_compression_boundary": false
}
```

## Required Negative Checks

The Phase44D standalone tests must fail closed for these adversarial cases:

| Label | Required behavior |
|---|---|
| `missing_source_root` | Reject any attempt to set `useful_compression_boundary = true` without an externally emitted canonical source root. |
| `mismatched_source_root` | Reject even if the source claim and compact proof are internally self-consistent around the wrong root. |
| `stale_source_claim` | Reject a source claim that binds an old source-surface version or claim epoch, even if its own commitment is recomputed. |
| `compact_proof_mismatch` | Reject a compact proof whose source root or payload commitment does not match the accepted source root. |

These checks are intentionally adversarial. They are meant to prevent a local
manifest, source claim, and compact proof from all agreeing on the same wrong
thing.

## Current Decision

The current project state may report bounded progress from Phase44B and
Phase44C source-binding probes and the Phase44D typed artifact verifier, but it
must not report final publication-grade useful compression. The current decision
remains:

```json
{
  "accepted": false,
  "useful_compression_boundary": false,
  "reason": "typed source emission is verified locally but not yet emitted by an upstream source-chain proof"
}
```

## Non-Claims

Phase44D does not claim:

- recursive compression;
- recursive proof completion;
- proof-carrying decoding closure;
- upstream production source-emission integration;
- source-chain integration that emits the source artifact as a public output;
- a recursive verifier proof that consumes the handoff in the current repo;
- or permission to set `useful_compression_boundary = true` from local
  self-consistency alone.
