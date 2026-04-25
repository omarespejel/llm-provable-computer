# Published zkML Calibration Note (2026-04-24)

This note records the current literature-facing calibration pass for the repository's
STARK-vs-SNARK transformer positioning after the checked one-shot, shared-table,
Phase12-style shared-bundle, Phase44D typed-boundary, and Phase71 handoff-receipt rows
landed in the paper evidence set.

Primary-source table:

- `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`

## What this table is for

It is a ground-truth extraction pass and workload-scope snapshot, not a claim of
matched benchmarking.

The repository's symbolic model is still useful as a structural model, but these
published numbers make three boundaries explicit:

1. current public 2026 zkML winners are lookup-aware systems, regardless of
   whether they sit on a SNARK or STARK stack,
2. this repository does not yet have a matched full-transformer `stwo` result on
   the same workload/hardware envelope as the strongest public SNARK papers, and
3. the symbolic ratio (`1.48x` for the GPT-2-small worked example) is therefore
   not yet an empirical wall-clock claim.

## What the extracted rows already show

- `NANOZK` reports `6.3s` prove time, `23ms` verify time, and `6.9 KB` proof
  size for a GPT-2-scale transformer block at `d = 768`.
- `NANOZK` also gives one narrower public verifier-object row directly in the
  abstract: for transformer models up to `d = 128`, it reports a `5.5 KB`
  layer proof with `24 ms` verification time.
- `Jolt Atlas` reports `14s` prove time and `0.517s` verify time for a
  `~0.25M`-parameter `nanoGPT` model, and `~38s` end-to-end for `GPT-2 (125M)`.
- `EZKL`, as quoted by `Jolt Atlas` on the same `nanoGPT` workload, reports
  `237s` proof time and `0.34s` verify time.
- `BitSage Obelyzk` now has a source-backed Starknet Sepolia verifier-object row:
  docs.rs pins recursive verifier contract
  `0x1c208a5fe731c0d03b098b524f274c537587ea1d43d903838cc4a2bf90c40c7`,
  verified tx
  `0x276c6a448829c0f3975080914a89c2a9611fc41912aff1fddfe29d8f3364ddc`,
  and `942` felt calldata for a 30-layer `SmolLM2-135M` recursive proof; the
  same page reports `3.55s` recursive compression on top of a `102s` GKR proof
  on `A10G`, and the accompanying paper reports `~280K` gas for one-layer GKR
  verify and `~2.5M` gas (`~$0.01`) for the full 40-layer Starknet Sepolia
  path. This sharpens deployment calibration, not a matched local verifier row.
- the current repository now exposes **three** literature-facing local calibration rows,
  each for a different regime:
  - the checked `Phase12`-style shared lookup bundle as the local proving-surface row at
    three paired rows:
    `4,968` raw proof bytes, `14.939 ms` prove, and `6.745 ms` verify from
    `docs/paper/evidence/stwo-phase12-shared-lookup-bundle-reuse-2026-04.tsv`;
  - the checked `Phase44D` typed source-emission boundary as the local latency row at
    the current two-step power-of-two point: `61,238` serialized bytes, `1.034 ms` boundary emission,
    and `0.957 ms` verify from
    `docs/paper/evidence/stwo-phase44d-source-emission-2026-04.tsv`; the same
    evidence file also records the causal split showing `0.456 ms` for the compact
    Phase43 proof alone, `15.856 ms` for ordered Phase30 manifest replay alone,
    and `0.399 ms` for typed-boundary binding after prior compact-proof verification;
  - the checked `Phase71` handoff receipt as the local compact-object row at three
    steps: `1,533` serialized bytes and `34.613 ms` verify from
    `docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.tsv`.
  These are still not full transformer benchmarks, but they now cover a proving-surface
  row, a latency-oriented typed boundary row, and a compactness-oriented receipt row
  rather than a single local artifact line.

## One narrow external comparator that is actually useful

If the paper needs exactly one narrower external comparator rather than another
full-model row, the only honest pairing in the current snapshot is the compact
verifier-object regime, and it should be used only as compact-object calibration:

- external row: `NANOZK` abstract layer proof at `d <= 128` -> `5.5 KB`, `24 ms`
  verification;
- closest local row: `Phase71` handoff receipt at three steps ->
  `1,533` serialized bytes, `34.613 ms` verification from
  `docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.tsv`.

That comparison is interesting because it splits cleanly:

- the current local `Phase71` object is **smaller** than the public `NANOZK`
  compact proof object, but
- it is **slower to verify** on the current path.

This is explicitly not a matched benchmark. The workloads and proof objects differ.
But it is still the most honest narrow comparator now available in public sources, and
it reinforces the paper's actual position: different verifier-facing layers improve
different costs.

## What the Obelyzk row now does and does not buy us

The refreshed `BitSage Obelyzk` row is useful because it upgrades the public
STARK-native comparator from a repo-reported README benchmark to a source-backed
Starknet Sepolia verifier-object record with an exact contract address, an exact
verified transaction hash, and an exact recursive calldata width.

What it still does **not** buy us is a matched local verifier-time row:

- the public Obelyzk object is a recursive STARK settlement proof over a GKR
  stack,
- the local `Phase44D` row is a pre-recursive typed-boundary latency surface,
  and
- the local `Phase71` row is a pre-recursive compact handoff surface.

So the Obelyzk row now strengthens deployment/on-chain calibration and public
STARK-native posture, but it does not turn the table into a same-regime verifier
race.

One further caveat matters for the repository's own large replay-avoidance
ratios. On the current local path, the dominant lower-layer baseline cost is the
ordered Phase30 manifest replay that this codebase actually pays, including
canonical JSON serialization and Blake2b hashing inside that replay flow. That
cost is real for this implementation, and it is exactly the work the typed
boundary removes here, but it should not be read as a universal lower bound on
manifest replay cost across every possible STARK stack or serialization design.

## Immediate consequence for paper positioning

The defensible public claim is narrower than “STARKs are already faster for
transformers.”

The current defensible claim is:

- lookup-friendly proof systems align with transformer non-arithmetic pressure,
- the repository now provides one-shot and reuse-sensitive `stwo` calibration rows
  across three different local surfaces: `Phase12` proving, `Phase44D` typed-boundary
  latency, and `Phase71` handoff-receipt compactness, and
- external calibration should be read by workload regime, not as a matched wall-clock
  race.

## What remains to calibrate

This table is necessary but not sufficient. It does not normalize:

- security level,
- hardware,
- exact sequence length,
- whether the workload is one layer, one block, or a full model,
- setup/keygen amortization,
- approximation strategy for non-arithmetic operations.

The next calibration step must therefore preserve the same standard:

1. keep adding only verifier-bound local rows whose reuse claim is enforced by the
   proof statement rather than by artifact deduplication,
2. keep the local calibration rows split by cost regime instead of collapsing them into
   a fake universal win story,
3. widen that reuse-sensitive measurement discipline to richer kernels before making
   the headline broader, and
4. add narrower external comparator rows only when workload boundary, hardware, and
   proof object are explicit enough to avoid backend-slogan comparisons.
