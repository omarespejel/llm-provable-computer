# Published zkML Calibration Note (2026-04-24)

This note records the current literature-facing calibration pass for the repository's
STARK-vs-SNARK transformer positioning after the checked one-shot, shared-table, and
Phase12-style shared-bundle rows landed in the paper evidence set.

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
- `Jolt Atlas` reports `14s` prove time and `0.517s` verify time for a
  `~0.25M`-parameter `nanoGPT` model, and `~38s` end-to-end for `GPT-2 (125M)`.
- `EZKL`, as quoted by `Jolt Atlas` on the same `nanoGPT` workload, reports
  `237s` proof time and `0.34s` verify time.
- `BitSage obelyzk.rs` reports a `41.4s` warm-cache proof for one
  `Qwen2.5-14B` token on `H100`; this is the closest public STARK-native
  comparator row, but it is repo-reported and not a matched benchmark.
- the current repository's strongest literature-facing local row is now the checked
  Phase12-style shared lookup bundle at three paired rows: `4,968` raw proof bytes,
  `14.939 ms` prove time, and `6.745 ms` verify time from
  `docs/paper/evidence/stwo-phase12-shared-lookup-bundle-reuse-2026-04.tsv`.
  That is still not a full transformer benchmark, but it is a verifier-bound,
  multi-table reuse row rather than a deleted fixed-fixture artifact.

## Immediate consequence for paper positioning

The defensible public claim is narrower than “STARKs are already faster for
transformers.”

The current defensible claim is:

- lookup-friendly proof systems align with transformer non-arithmetic pressure,
- the repository now provides one-shot and reuse-sensitive `stwo` calibration rows,
  including a verifier-bound two-table bundle row, and
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
2. widen that reuse-sensitive measurement discipline to richer kernels before making
   the headline broader, and
3. add narrower external comparator rows only when workload boundary, hardware, and
   proof object are explicit enough to avoid backend-slogan comparisons.
