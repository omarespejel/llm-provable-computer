# Phase115 Richer Linear-block Window Family Scaling Spec

## Goal

Turn the single-point Phase113 result into a supported scaling claim over the
window counts the repository can currently derive from frozen source leaves
without inventing a new proof surface.

Phase113 answered:

> can a richer transformer-family handoff stay compact at `w8`?

Phase115 answers:

> does that richer-family handoff stay compact as the supported repeated-window
> family grows from `w4` to `w8`?

## Why this phase exists

A single compact artifact can still be a coincidence.

A scaling sweep is more useful because it tests whether the richer-family layer
is behaving like a stable handoff surface or whether it starts quietly growing
back toward the explicit repeated-window source as more windows are chained.

The honest scope here is narrow:

- use the existing frozen Phase107 repeated-window leaves,
- derive Phase112 and Phase113 surfaces at the supported power-of-two leaf
  counts already available from that frozen family,
- and publish the exact byte-level comparison.

## Input surface

Phase115 should consume the frozen repeated-window source family under:

- `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/`

Supported scaling points for this first sweep:

- `w4` from the first `2` Phase107 leaves,
- `w8` from the first `4` Phase107 leaves.

This phase should not claim `w2` support because Phase112 inherits the Phase110
contract that requires at least `2` leaves.

## Output surface

Introduce one new publication-facing bundle:

- `stwo-richer-linear-block-window-family-scaling-v1-2026-04-22/`

It should contain:

- one `w4` Phase112 semantics artifact,
- one `w4` Phase113 richer-family artifact,
- one `w8` Phase112 semantics artifact,
- one `w8` Phase113 richer-family artifact,
- one scaling TSV with explicit, semantics, and richer-family byte counts,
- one comparison TSV with richer-versus-explicit ratios and richer-over-semantics
  overhead,
- one public-comparison note that keeps the claim verifier-bound and
  non-leaderboard.

## Benchmark target

The key Phase115 numbers are:

- Phase113 `w4` bytes versus explicit Phase107 `w4` bytes,
- Phase113 `w8` bytes versus explicit Phase107 `w8` bytes,
- Phase113 overhead above Phase112 at `w4`,
- Phase113 overhead above Phase112 at `w8`,
- and whether the richer-versus-explicit ratio improves as the explicit source
  grows.

## Required tests

- Phase113 `w4` stays below the explicit Phase107 `w4` source,
- Phase113 `w8` stays below the explicit Phase107 `w8` source,
- richer-over-semantics overhead remains stable across `w4` and `w8`,
- richer-versus-explicit ratio improves from `w4` to `w8`.

## Non-claims

Phase115 does not claim:

- recursion,
- cryptographic accumulation,
- a matched benchmark against public zkML papers,
- or stable scaling for arbitrary window counts beyond the frozen source family.

## Stop condition

Phase115 is complete when the repository can point to:

- one frozen scaling bundle over supported repeated-window counts,
- one machine-readable scaling table,
- one test slice that proves the richer-family surface remains compact at both
  supported scaling points,
- and one explicit note that this is still a verifier-bound artifact sweep,
  not a production prover benchmark.
