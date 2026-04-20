# Phase44D Source-Emitted Root Manifest Checker

Control issue: 180. This is an evidence/provenance checker for the typed Rust
source-emission verifier, not a main AIR integration and not an upstream
source-chain proof.

## Purpose

Phase44D defines a deterministic source-emitted root manifest that the Rust
final verifier contract can consume without relying on implicit source-side
state.
The checker answers one bounded question:

```text
Can the compact root, source root, and source-emitted root be recomputed from
one canonical manifest while preserving issue id, source-surface version,
total step count, log size, and ordered source/compact fields, while rejecting
replayed or expected-row drift for the chosen `total_steps`?
```

If this checker passes, the manifest is suitable as provenance evidence for the
typed Rust source-emission contract:

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
- `verify_phase44d_recursive_verifier_public_output_handoff(...)`
- `verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(...)`
- `verify_phase44d_recursive_verifier_public_output_aggregation(...)`
- `verify_phase45_recursive_verifier_public_input_bridge(...)`
- `verify_phase45_recursive_verifier_public_input_bridge_against_sources(...)`

If it fails, the final verifier input boundary is not yet precise enough.

The current Rust surface also exposes the Phase44D terminal-boundary LogUp
closure and the Phase45 ordered public-input bridge. The closure binds the
source-side public boundary LogUp sum to the compact proof component claimed
sum. The Phase45 bridge freezes those closure fields into ordered lanes before
any recursive verifier adapter is allowed to claim compression.

## Manifest Contract

The canonical manifest lives at:

```text
docs/engineering/design/phase44d_source_root_manifest.json
```

The top-level manifest fields are intentionally exact:

- `schema`: `phase44d-source-root-manifest-v1`
- `probe`: `phase44d-source-emitted-root-manifest`
- `issue_id`: `180`
- `source_surface_version`: `phase44d-final-boundary-source-v1`
- `total_steps`: the bounded source-transition count
- `log_size`: `ilog2(total_steps)`
- `compact_root`: the canonical root of the compact-row preimage
- `source_root`: the canonical root of the source-row preimage
- `source_emitted_root`: the root emitted by the source-side boundary
- `compact_root_preimage`: the ordered compact-root payload
- `source_root_preimage`: the ordered source-root payload
- `kill_labels`: ordered rejection labels
- `mutation_checks`: ordered rejection metadata

The checker rejects missing or extra top-level fields. This is deliberate: the
manifest is a boundary contract, so the Rust final verifier should not need to
guess which fields matter.

## Root Definitions

The checker uses canonical JSON with sorted object keys and compact separators.
Roots are SHA-256 hashes over tagged canonical JSON payloads:

```text
compact_root = sha256(canonical_json({tag: "phase44d-compact-root-v1", value: compact_root_preimage}))
source_root  = sha256(canonical_json({tag: "phase44d-source-root-v1", value: source_root_preimage}))
```

The source-root preimage includes the compact root, so the source root binds the
compact surface. The checker then requires:

```text
source_emitted_root == source_root
```

## Rejection Surface

The checker must fail closed on these mutation labels:

| Kill label | What it must break |
|---|---|
| `issue_id_drift` | The manifest no longer targets issue 180. |
| `source_surface_version_drift` | The source-surface version changes. |
| `total_steps_drift` | The step count drifts from the ordered preimages. |
| `log_size_drift` | The log size no longer equals `ilog2(total_steps)`. |
| `compact_root_drift` | The stored compact root no longer matches the compact preimage. |
| `source_root_drift` | The stored source root no longer matches the source preimage. |
| `source_emitted_root_drift` | The source-emitted root no longer equals the canonical source root. |
| `compact_row_reordering` | The compact-row order changes. |
| `source_row_reordering` | The source-row order changes. |
| `missing_compact_root_preimage` | The compact preimage is absent. |
| `missing_source_root_preimage` | The source preimage is absent. |
| `missing_source_root_field` | The top-level source-root field is absent. |

Object key order is normalized by canonical JSON, so the reordering checks apply
to ordered compact/source row lists. Those lists are the order-sensitive replay
surface the final verifier boundary must bind, and any replay/expected-row drift
that changes their canonical sequence must be rejected.

## Local Runner

Run the checker locally with:

```bash
scripts/run_phase44d_source_root_manifest.sh
```

The runner validates the canonical manifest and writes deterministic evidence to:

```text
docs/engineering/design/phase44d_source_root_manifest.evidence.json
```

## Non-Goals

Phase44D does not claim:

- AIR-trace verification,
- proof-byte validation,
- upstream source-chain proof emission,
- recursive compression,
- or publication-facing proof-system soundness.

It is only a deterministic provenance path for deciding what the source side
must emit for the Rust final verifier and for the Phase44D recursive-verifier
handoff. The handoff and aggregation manifests are still pre-recursive
contracts; they keep the verifier input narrow, but they are not themselves a
recursive proof.
