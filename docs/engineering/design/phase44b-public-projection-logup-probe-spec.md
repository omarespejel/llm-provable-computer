# Phase 44B Public Projection LogUp Probe

Control issue: <https://github.com/omarespejel/provable-transformer-vm/issues/180>

## Purpose

Phase 44B is a bounded probe for the current Phase43 keep-alive route. It does
not claim cryptographic compression, recursive closure, or a new proof backend.
It answers a narrower question:

> Can the Phase43 projection artifact be bound to a public-data-style LogUp
> transcript without reintroducing the full replay trace as the only source of
> truth?

The probe is intentionally documentation- and script-only. It does not edit the
reserved Rust implementation files that currently own the Phase43 bridge:

- `src/stwo_backend/history_replay_projection_prover.rs`
- `src/stwo_backend/mod.rs`
- `src/lib.rs`

## Primary References

The probe follows two upstream surfaces:

1. Stwo core LogUp/GKR lookup batching:
   - `crates/constraint-framework/src/logup.rs`
   - `crates/stwo/src/prover/lookups/gkr_prover.rs`
   - `crates/stwo/src/prover/lookups/gkr_verifier.rs`
2. stwo-cairo public-data lookup binding:
   - `stwo_cairo_prover/crates/cairo-air/src/air.rs`
   - `stwo_cairo_prover/crates/cairo-air/src/claims.rs`
   - `stwo_cairo_verifier/crates/cairo_air/src/claims.cairo`

The stwo-cairo `PublicData.logup_sum(...)` surface is the closest public
reference for the role this probe plays: a public-data binding over ordered
inputs, not a new proof system and not a Cairo-side recursion claim.

## What Is Bound

The probe consumes the canonical Phase43 replay-trace surface and recomputes
the same replay-side commitments that the current Rust code already defines:

- `phase43_trace_commitment`
- `appended_pairs_commitment`
- `lookup_rows_commitments_commitment`
- `phase30_step_envelopes_commitment`
- `projection_commitment`

It then computes a separate Phase44B public binding:

- `public_projection_logup_transcript_commitment`
- `public_projection_logup_binding_commitment`

The transcript commitment is the ordered public row/data digest.
The binding commitment ties that digest to the Phase43 trace commitment and the
projection commitment.

The probe now makes the transcript shape explicit instead of treating it as an
opaque list of strings. Its ordered transcript fields are:

- replay and layout metadata: `issue`, `trace_version`, `relation_outcome`,
  `transform_rule`, `proof_backend`, `proof_backend_version`,
  `statement_version`
- replay/projection commitments: `trace_commitment`,
  `projection_commitment`, `phase30_source_chain_commitment`,
  `appended_pairs_commitment`, `lookup_rows_commitments_commitment`,
  `phase30_step_envelopes_commitment`
- boundary commitments: the start/end public-state, start/end boundary, and
  start/end history commitments for Phase12/Phase14
- replay sizing: `initial_kv_cache_commitment`, `total_steps`, `pair_width`,
  `projection_row_count`, `projection_column_count`
- per-row public fields in canonical replay order: step index, appended pair,
  lookup row commitments, step-envelope commitment, and the paired public-state
  commitments carried by the Phase12 and Phase14 states

Those ordered fields are hashed into the transcript commitment. The transcript
commitment is then used to derive the LogUp challenges, and the source-chain
commitment is re-derived from the ordered replay rows so source drift cannot be
hidden behind a stale top-level field.

## Exact Computation

The probe mirrors the current Rust serialization rules:

- `usize` values are encoded as 16 little-endian bytes.
- `bool` values are encoded as one byte `0` or `1`.
- `i16` values are encoded as two little-endian bytes using the same
  M31-conversion rule as the Rust implementation.
- 32-byte lowercase hex commitments are consumed as 64-character strings.
- Projection commitments split 32-byte hex strings into 16 u16 limbs, matching
  the current Phase43 projection layout.

The Phase44B probe follows this order:

1. Recompute the replay-side commitments from a bounded Phase43 trace.
2. Recompute the projection rows and the projection commitment.
3. Build the public transcript from the ordered row and boundary public fields.
4. Hash the transcript into `public_projection_logup_transcript_commitment`.
5. Derive the Phase44B LogUp challenge seed from the transcript commitment,
   the source-chain commitment, and the projection commitment.
6. Derive the bounded LogUp challenges `z` and `alpha` from that seed.
7. Build the explicit LogUp relation shape over the ordered row digest, using
   the canonical replay-row order, `z`, `alpha`, and the corresponding
   alpha-power weights.
8. Hash the transcript commitment together with the replay/source/projection
   commitments and the relation commitment into
   `public_projection_logup_binding_commitment`.

## Probe Bounds

The probe is deliberately small:

- at least 2 replay rows,
- at most 64 replay rows,
- power-of-two row count,
- positive pair width,
- deterministic synthetic demo mode for local verification,
- optional `--trace-json` mode for later feed-in of a real Phase43 trace file.

The bounded demo is enough to catch binding drift in the new public bridge
without requiring a reserved-file patch.

## Non-Claims

Phase 44B does not claim:

- recursive proof closure,
- cryptographic compression,
- exact Cairo `QM31` evaluation of `PublicData.logup_sum(...)`,
- full standard-softmax inference,
- or a final Phase43 breakthrough result.

The probe only claims that the Phase43 replay/projection surface can be bound to
a public-data-style transcript in a deterministic, reviewable way. It also does
not claim to be the final Rust implementation; the probe is explicitly a
bounded design bridge toward a live helper.

## LogUp Relation Shape

The Phase44B relation is intentionally shaped like a LogUp-style public-data
binding rather than a generic checksum. In the probe, each replay row contributes
one ordered row digest, one challenge-derived denominator, and one alpha-weighted
term:

- `row_digest = H(row_fields)`
- `denominator = z + row_digest`
- `term = alpha^row_index / denominator`

The evidence records:

- the canonical row order,
- the ordered public row fields used to derive each row digest,
- the derived `z` and `alpha` challenges,
- the per-row alpha-power weights and denominators,
- the claimed sum over the row terms,
- and the relation commitment that binds the whole shape.

This is still a bounded probe, not a claim that the exact Cairo `QM31`
implementation is reproduced here. The point is that the bridge now exposes the
same transcript/challenge/relation scaffolding that a later Rust/AIR helper can
consume directly.

## Drift Tests

The probe includes mutation tests for the main replay/source failure modes:

- row order drift,
- source-chain commitment drift,
- transcript-field omission/reordering,
- LogUp challenge drift,
- and relation-shape drift.

These are intentionally source-bound, not witness-only. They are meant to catch
the common failure mode where a probe still passes after a stale or reshuffled
replay source is fed into it.

## Local Artifacts

The mergeable implementation lives in:

- `scripts/paper/phase44b_public_projection_logup_probe.py`
- `scripts/run_phase44b_public_projection_logup_probe.sh`
- `scripts/tests/test_phase44b_public_projection_logup_probe.py`

The shell wrapper writes its evidence to:

- `target/phase44b-public-projection-logup-probe/evidence.json`

and also emits the synthetic trace and projection surfaces used to derive it.

## If a Direct Rust Patch Is Needed Later

If the Phase44B probe later needs to become a live source-bound helper in Rust,
the exact patch would be:

1. add a public `commit_phase43_public_projection_logup_binding(...)` helper in
   `src/stwo_backend/history_replay_projection_prover.rs`,
2. add a public `verify_phase43_public_projection_logup_binding(...)` helper in
   the same file,
3. re-export the new helper from `src/stwo_backend/mod.rs`,
4. re-export the public API from `src/lib.rs`.

That patch is not applied here to avoid conflicts with the reserved files.
