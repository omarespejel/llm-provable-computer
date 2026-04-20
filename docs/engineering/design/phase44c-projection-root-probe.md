# Phase44C Source-Emitted Projection Root Probe

Control issue: none yet. This is a bounded local probe, not a publication claim.

## Purpose

Phase44C is a kill probe for the source-emitted Stwo projection root path.
It checks whether a projection root emitted by the source side can be bound to a
canonical source-root manifest without drifting on row count, log size, row
ordering, or source-surface version.

The probe is intentionally narrow:

```text
Can a source-emitted projection root and a canonical source-root manifest
be recomputed from the same normalized preimage, with matching row count
and log-size mechanics?
```

If the answer is yes, the current Phase44C route stays alive as a bounded
source-bound probe. If the answer is no, the source-side projection contract is
too loose and the route should be killed before any Rust-side integration is
attempted.

## Prerequisites

Phase44C can optionally inspect a local checkout of the upstream Stwo source.
Pass `--stwo-root` to the checker when that evidence is needed; the local
runner forwards `STWO_ROOT` to that flag when the environment variable is set.
The path must point at a checkout containing `crates/stwo/Cargo.toml`. If no
Stwo checkout is supplied, Phase44C still validates the canonical manifest and
mutation checks, and emits `source_mechanics: null` in the evidence.

## Why Stwo Matters Here

The Stwo source under `STWO_ROOT` shows that root binding and log-size mechanics
are explicit, not implicit:

- `crates/stwo/src/prover/pcs/mod.rs` mixes Merkle roots into the channel with
  `MC::mix_root(channel, tree.commitment.root())`.
- `crates/stwo/src/prover/fri.rs` also mixes Merkle roots and keeps `log_size`
  in the query/folding path.
- `crates/stwo/src/prover/poly/twiddles.rs` defines the coset tower with
  `root_coset` and extracts subdomain twiddles from `domain_log_size` /
  `subdomain_log_size`.
- `crates/stwo/src/prover/air/accumulation.rs` derives committed subdomains
  from `CanonicCoset::new(log_size + log_expansion).circle_domain()` and
  carries the derived `root_coset: subdomain.half_coset`.

Phase44C uses those source facts as a mechanical check. It does not try to
rebuild the Rust prover; it only verifies that the canonical manifest and the
source-emitted root binding respect the same row-count and log-size discipline.

## Canonical Root Manifest

The canonical manifest lives at:

```text
docs/engineering/design/phase44c-projection-root-manifest.json
```

The manifest is the bounded source of truth for the probe. It carries:

- `schema`: `phase44c-projection-root-binding-manifest-v1`
- `probe`: `phase44c-source-emitted-projection-root-binding`
- `source_surface_version`: the Phase43 field-native projection version
- `projection_row_count`
- `projection_log_size`
- `source_emitted_projection_root`
- `canonical_source_root_preimage`
- `kill_labels`
- `mutation_checks`

The canonical preimage is normalized as canonical JSON and hashed by the local
probe. The manifest stores the source-emitted projection root explicitly, and
the probe rejects any manifest where that stored root does not match the
canonical source-root derived from the same normalized preimage. The probe rejects any
manifest where:

- the row count is not a power of two,
- `projection_log_size` does not equal `ilog2(projection_row_count)`,
- the row count and log size do not agree inside the canonical preimage,
- the source-surface version drifts,
- the row ordering changes,
- or the source-emitted root and canonical root stop matching the same
  canonical preimage.

## Kill Labels

These are the required kill labels for the probe. They are intentionally
bounded and should all fail closed:

| Kill label | What it must break |
|---|---|
| `row_count_drift` | The projection row count no longer matches the canonical preimage. |
| `log_size_drift` | The projection log size no longer matches `ilog2(row_count)`. |
| `row_order_drift` | The canonical row ordering is changed. |
| `row_replacement` | One row label is replaced with a different row label. |
| `source_surface_version_drift` | The Phase43 source surface version changes. |
| `canonical_preimage_truncation` | The canonical preimage loses required fields or rows. |
| `binding_alias_drift` | The binding surface is no longer a canonical source-root binding. |

The probe script applies each mutation to the canonical manifest and must reject
every one.

## Mutation Checks

The local mutation checks are simple, bounded, and deterministic:

1. Load the canonical manifest.
2. Recompute the projection root from the canonical preimage.
3. Recompute the canonical source-root from the same preimage.
4. Verify the Stwo source mechanics when a cloned upstream tree is supplied.
5. Apply each kill-label mutation and require rejection.

Acceptance requires all of the following:

- the manifest schema is correct,
- the projection row count is a power of two,
- the log size matches the row count,
- if `--stwo-root` is supplied directly, or `STWO_ROOT` is supplied through the
  local runner, the Stwo source mechanics are present in that cloned source
  tree,
- every kill label fails closed.

## Local Runner

Run the probe locally with:

```bash
scripts/run_phase44c_projection_root_probe.sh
```

The runner writes evidence to:

```text
target/phase44c-projection-root-probe/evidence.json
```

## Non-Goals

Phase44C does not claim:

- full Rust-side integration,
- recursive compression,
- proof-carrying decoding closure,
- GitHub CI validation,
- or any publication-facing proof claim.

This is a bounded source-binding probe only.
