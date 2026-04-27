# Tablero optimized-replay red-team gate (April 27, 2026)

This note records the red-team measurement requested by issue #290: an
honestly-optimized replay verifier that (a) skips per-step embedded proof
re-verification (the typed boundary verifier does the same) and (b) uses
binary canonical commitments over fixed-size cryptographic identities and
the raw stark-proof byte buffer instead of JSON-serialize-then-hash for the
chain summary and per-step proof commitments.

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
- Timing policy: `median_of_5_runs_from_microsecond_capture`.
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
| default | `3,496.950 ms`         | `8,317.269 ms`        | `2.4x`  | `430.1x`                                                         |
| `2x2`   | `3,457.447 ms`         | `7,182.913 ms`        | `2.1x`  | `425.7x`                                                         |
| `3x3`   | `5,911.703 ms`         | `7,721.977 ms`        | `1.3x`  | `711.3x`                                                         |


The headline replay-avoidance ratio at the `1024`-step frontier moves from
`917x`-`1066x` (Section 6.2 of the paper) to a host-noise-sensitive band of
`~426x`-`~711x` once the JSON-tax components of the original replay path
are removed.

## Causal decomposition of the optimized total

The optimization touches two of the four non-trivial replay buckets:


| Bucket                               | Original (JSON-keyed) | Optimized (binary) | Change       |
| ------------------------------------ | --------------------- | ------------------ | ------------ |
| source-chain commitment              | `~2,260 ms`           | `~0.7-1.3 ms`      | `-99.9%`     |
| per-step proof commitment            | `~2,250 ms`           | `~150-210 ms`      | `-90% to -93%` |
| manifest finalize (state derivation) | `~1,860 ms`           | `~3,300-5,750 ms`  | `host-noise dominated` |
| equality check                       | `~0.2 ms`             | `~0.3-3.7 ms`      | `noise band` |


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
2. The constant-factor headline tightens, but only modestly: the
   implementation-cost component of the original `~1000x` figure is a
   `~1.3-2.4x` factor in this measurement (and is itself the smaller
   contributor); the implementation-independent component is a
   `~430-710x` band at the checked frontier across the three families
   and reflects work the typed boundary genuinely avoids by relying on
   the compact projection proof's trace commitment instead of re-deriving
   states from the chain.
3. The optimized-replay total is host-noise sensitive at this scale.
   Two independent median-of-five sessions on the same host can differ
   by a factor of `~1.5-2.7x` on the optimized total; the structural
   conclusions are robust to this noise (the slope, the residual order
   of magnitude, the per-bucket savings) but the specific cell values in
   Table 3a should be read as an order-of-magnitude band, not a tight
   number.
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

