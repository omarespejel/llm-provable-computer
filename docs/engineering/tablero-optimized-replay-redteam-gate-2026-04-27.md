# Tablero optimized-replay red-team gate (April 27, 2026)

This note records the red-team measurement requested by issue #290: an
honestly-optimized replay verifier that (a) skips per-step embedded proof
re-verification (the typed boundary verifier does the same) and (b) uses
binary canonical commitments over fixed-size cryptographic identities and
the raw stark-proof byte buffer instead of JSON-serialize-then-hash for the
chain summary and per-step proof commitments.

The original PR-292 issue description scoped this experiment as a
median-of-five measurement. During the in-PR review pass, an in-flight
variance investigation showed that five samples were undersampling the
host-noise band on the `manifest_finalize` bucket (the `3x3` family in
particular swung by `2.7x` between two independent median-of-five sessions
on the same host). The canonical evidence and this gate note therefore
upgraded to a median-of-nine measurement. The benchmark shell script
explicitly accepts both `BENCH_RUNS=5` and `BENCH_RUNS=9` for canonical
output paths so that a future re-run can reproduce either number.
Median-of-nine is what the paper currently reports; median-of-five is
retained as a sanctioned regeneration mode and the result it produces is
recorded below for full transparency.

## Scope

- Source family: same three carry-aware experimental Phase12 layout families
used elsewhere (default, `2x2`, `3x3`).
- Backend version (exact identifier):
`stwo-phase12-decoding-family-v10-carry-aware-experimental`.
- Manifest format: optimized binary-commitment manifest stamped with
`manifest_version = stwo-phase30-decoding-step-proof-envelope-optimized-manifest-v1` and
`semantic_scope = stwo_execution_parameterized_decoding_step_proof_envelope_manifest_optimized_binary_commitments`.
This is **distinct** from the publication-default JSON-keyed manifest;
consumers cannot accidentally substitute one for the other.
- Frontier: `1024` honest proof-checked steps (same shared frontier as the
family-matrix and replay-decomposition evidence).
- Timing mode: `measured_median`.
- Timing unit: `milliseconds`.
- Timing policy: `median_of_9_runs_from_microsecond_capture` (canonical;
  the script also accepts `median_of_5_runs_from_microsecond_capture`
  under the same canonical-path allow-list, used in the original
  measurement; current canonical evidence is the median-of-nine band).
- Aggregation strategy: `median_total_representative_run` (consistent with
the existing replay-decomposition aggregator).
- Benchmark identity: `benchmark_version = stwo-tablero-replay-breakdown-optimized-benchmark-v1`,
`semantic_scope = tablero_replay_baseline_optimized_decomposition_over_checked_layout_families_over_phase12_carry_aware_experimental_backend`.

## What the optimized verifier does and does not do

It still verifies that the manifest is consistent with the chain. The
manifest-vs-chain consistency check, including the `verify_phase12_decoding_chain_structure`
call that re-derives every recorded `from_state`/`to_state` pair from the
program's deterministic re-execution, is unchanged.

It deliberately differs from the publication-default replay verifier in two
explicit ways:

1. It does **not** call `verify_supported_phase12_decoding_step_proof` per
  step. Justification: the typed Phase44D boundary verifier (which is the
   surface this engineering experiment is set up to compare against) does
   not re-verify embedded step proofs either, and the compact projection
   proof's trace commitment already binds the trace that includes every
   step proof's public-output surface. The chain comes pre-validated from
   the proof-checked construction; the optimized replay inherits that
   trust.
2. It uses
  `phase30_commit_phase12_decoding_chain_for_step_envelopes_binary_with_step_commitments` and
   `phase30_commit_step_proof_binary` instead of the JSON-keyed
   counterparts. The binary helpers hash only fixed-size cryptographic
   identities (chain version metadata, layout commitment, ordered list of
   per-step boundary and shared-lookup commitments) plus the raw
   stark-proof byte buffer. They are domain-separated from the JSON path so
   the two schemes cannot collide.

The optimized verifier is **not** a drop-in replacement for the
publication-default verifier. The publication-default manifest format is
keyed by JSON-hashed commitments; deploying the optimized verifier in
production would require migrating the manifest format to binary
commitments. This is an engineering-only red-team measurement.

## Evidence

- `docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.tsv`
- `docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.json`

## Result

Median-of-five runs at `1024` steps:


| Family  | Optimized replay total | Original replay total | Speedup | Optimized ratio (optimized replay total : typed-boundary verify) |
| ------- | ---------------------- | --------------------- | ------- | ---------------------------------------------------------------- |
| default | `2,684.106 ms`         | `8,317.269 ms`        | `3.1x`  | `330.1x`                                                         |
| `2x2`   | `2,145.775 ms`         | `7,182.913 ms`        | `3.3x`  | `264.2x`                                                         |
| `3x3`   | `2,170.899 ms`         | `7,721.977 ms`        | `3.6x`  | `261.2x`                                                         |


The headline replay-avoidance ratio at the `1024`-step frontier moves from
`917x`-`1066x` (Section 6.2 of the paper) to a host-noise-sensitive band of
`~261x`-`~330x` once the JSON-tax components of the original replay path
are removed. This is a median-of-nine measurement; an earlier median-of-five
session on the same host produced a `~426x`-`~711x` band, with the `3x3`
median in particular pulled high by an unlucky run; the present median-of-nine
result is more representative of the underlying distribution and is the one
the paper now reports.

## Causal decomposition of the optimized total

The optimization touches two of the four non-trivial replay buckets:


| Bucket                               | Original (JSON-keyed) | Optimized (binary) | Change       |
| ------------------------------------ | --------------------- | ------------------ | ------------ |
| source-chain commitment              | `~2,260 ms`           | `~0.8-1.3 ms`      | `-99.9%`     |
| per-step proof commitment            | `~2,250 ms`           | `~110-140 ms`      | `-94% to -95%` |
| manifest finalize (state derivation) | `~1,860 ms`           | `~2,030-2,545 ms`  | `host-noise dominated` |
| equality check                       | `~0.2 ms`             | `~0.1-1.0 ms`      | `noise band` |


The two binary-commitment buckets shrink by `>90%`, confirming that almost
all of those buckets' cost in the original path was JSON-serialize overhead
rather than cryptographic work. The `manifest_finalize` bucket unfortunately
swings by a factor of `~1.5-2.7x` between independent median-of-five
sessions even on the same host: it includes the per-step state-derivation
work that confirms every recorded `from_state`/`to_state` pair against the
program's deterministic re-execution, and that work appears to be cache-
and memory-noise sensitive at `1024` steps on this machine. The structural
per-step work in this bucket is the residual the typed boundary genuinely
avoids; its absolute ms value should be read as an order-of-magnitude band,
not a tight number.

## Interpretation

1. The slope-difference structural claim (Section 6.3 of the paper) is
  unaffected. The optimized replay surface still scales linearly in `N`
   while the typed-boundary verify surface stays sublinear.
2. The constant-factor headline tightens by a meaningful factor: the
   implementation-cost component of the original `~1000x` figure is a
   `~3.1-3.6x` factor in this median-of-nine measurement; the
   implementation-independent component is a `~261-330x` band at the
   checked frontier across the three families and reflects work the
   typed boundary genuinely avoids by relying on the compact projection
   proof's trace commitment instead of re-deriving states from the chain.
3. The optimized-replay total is host-noise sensitive at this scale.
   The nine timed runs span `1,790-8,083 ms` for `2x2` (range factor
   `4.52x`), `2,018-7,196 ms` for default (range factor `3.57x`), and
   `1,865-4,906 ms` for `3x3` (range factor `2.63x`). The median
   suppresses single-run outliers, but the underlying distribution is
   wide and a quieter measurement environment (or a substantially larger
   sample count) would be needed to tighten the constants further. The
   structural conclusions are robust to this noise (the slope, the
   residual order of magnitude, the per-bucket savings); the specific
   cell values in Table 3a should be read as an order-of-magnitude band,
   not a tight number.
4. The headline number in the paper now leads with the slope claim and
   reports both the original and optimized constants explicitly.

## Reproduction

```bash
cargo +nightly-2025-07-14 build --release --features stwo-backend --bin tvm
BENCH_RUNS=5 \
CAPTURE_TIMINGS=1 \
  scripts/engineering/generate_tablero_replay_breakdown_optimized_benchmark.sh
```

The shell script asserts the resulting JSON's `benchmark_version`,
`semantic_scope`, `timing_mode`, `timing_policy`, `timing_unit`, and
`timing_runs` match the expected identity above before overwriting the
checked-in evidence, so a re-run that drifts onto a different lane fails
closed instead of silently landing in publication evidence. The pre-build
keeps run-to-run host noise low.

## References

- Issue #290 (red-team replay baseline; this gate closes the experiment).
- Issue #288 (paper-research meta tracker).
- `src/stwo_backend/decoding.rs`:
`phase30_prepare_decoding_step_proof_envelope_manifest_optimized`,
`verify_phase30_decoding_step_proof_envelope_manifest_against_chain_optimized_replay_with_breakdown`,
`phase30_commit_step_proof_binary`,
`phase30_commit_phase12_decoding_chain_for_step_envelopes_binary_with_step_commitments`.
- `docs/paper/tablero-typed-verifier-boundaries-2026.md` Section 6.6 ("Red-teaming the constant").

