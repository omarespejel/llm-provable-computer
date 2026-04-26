# Published zkML Calibration Note (2026-04-24, refreshed for the Tablero presentation package)

This note records the literature-facing calibration posture for the presentation paper.
It is a workload-scope and claim-scope note, not a matched benchmark claim.

Primary source table:

- `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`

## What this table is for

The table is a structured extraction of public numbers and local evidence rows.
It is meant to support disciplined positioning, not backend branding.

Three points matter most.

1. The strongest current zkML systems are already lookup-aware, regardless of whether
   they sit on SNARK or STARK stacks.
2. This repository does not yet have a matched full-model transformer benchmark against
   those public systems.
3. The local evidence is therefore split by verifier-facing regime rather than smoothed
   into a fake universal win story.

## The three local regimes that matter

The local package currently exposes three different verifier-facing regimes.

1. **Proving surface.** A narrow proving-bound calibration row for a compact reusable
   proof bundle.
2. **Typed-boundary latency surface.** The main Tablero row: verify a compact proof,
   accept a typed boundary, and avoid replaying the ordered manifest baseline.
3. **Compact-object surface.** A smaller handoff object that improves serialized size but
   does not win on local verifier latency.

Those rows should not be collapsed into one slogan because they improve different costs.

## What the typed-boundary row actually means

The large local ratios in the presentation paper come from the typed-boundary latency
surface. The baseline in that experiment is the verifier-side replay path that this
codebase actually pays today, especially ordered canonical serialization, hashing, and
manifest reconstruction.

That is a real cost and a real result. But it is still implementation grounded. The
paper should say explicitly that the ratios measure replay avoidance against the current
manifest implementation, not a universal lower bound on every possible replay design.

## External calibration that is actually useful

The strongest public STARK-native deployment calibration in this package is the Obelyzk
Starknet Sepolia verifier object.

It is useful because it pins:

- a concrete verifier contract,
- a concrete verified transaction,
- a concrete calldata width, and
- public gas numbers for a deployed recursive path.

It is **not** a matched local verifier-time comparator to the typed-boundary experiment.
The objects live at different layers of the stack.

A narrower compact-object comparison is also honest:

- public NANOZK material reports a small verifier-facing proof object with fast
  verification, and
- the local compact handoff object is smaller but slower on its current path.

Again, the point is not that one system categorically wins. The point is that the right
comparison depends on which verifier-facing layer is being discussed.

## Immediate consequence for the paper

The safest public claim is:

- lookup-friendly proof systems align well with transformer workloads,
- this repository contributes a typed verifier-boundary pattern plus a formal
  statement-preservation criterion, and
- the local evidence should be read by verifier-facing regime: proving surface, typed
  boundary latency surface, and compact-object surface.

That is strong enough to be interesting and narrow enough to remain defensible.
