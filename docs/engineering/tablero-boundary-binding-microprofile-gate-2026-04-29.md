# Tablero boundary-binding microprofile gate (2026-04-29)

## Scope

This gate answers issue #291: the typed-boundary verifier path needed a narrow
component microprofile so we could check whether the accepted boundary object hides a
replay-shaped cost surface.

This is experimental-lane evidence. It uses the carry-aware execution-proof backend and
must not be read as a publication-default backend promotion.

## Evidence

- TSV: `docs/engineering/evidence/tablero-boundary-binding-microprofile-2026-04.tsv`
- JSON: `docs/engineering/evidence/tablero-boundary-binding-microprofile-2026-04.json`
- Generator: `scripts/engineering/generate_tablero_boundary_binding_microprofile_benchmark.sh`
- Benchmark identity: `stwo-tablero-boundary-binding-microprofile-benchmark-v1`
- Scope: `tablero_typed_boundary_binding_microprofile_over_checked_layout_families_over_phase12_carry_aware_experimental_backend`
- Backend version: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Claim scope: `post_compact_proof_phase44d_typed_boundary_binding_microprofile`
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_of_mean_256_iteration_microprofile`
- Step frontier: `1024` for `default`, `2x2`, and `3x3`

Regeneration command:

```bash
NIGHTLY_TOOLCHAIN=+nightly-2025-07-14 BENCH_RUNS=5 ITERATIONS=256 CAPTURE_TIMINGS=1 \
  scripts/engineering/generate_tablero_boundary_binding_microprofile_benchmark.sh
```

The generator fails closed if the benchmark identity, timing policy, family set, step
count, component count, verification flags, or non-additivity notes drift. It writes
median-of-five component rows so a single noisy microprofile run does not become the
checked evidence payload.
All table values below are median-of-run-means from the checked policy
`median_of_5_runs_of_mean_256_iteration_microprofile`; the JSON/TSV stamp the aggregate
payload as `timing_mode=measured_median`.

## Result

At the checked `1024`-step frontier, the full binding-only verifier surface remains in
single-digit milliseconds:

| Family | Boundary bytes | Full binding median-of-run-means |
| --- | ---: | ---: |
| `default` | `6,649` | `5.294 ms` |
| `2x2` | `6,633` | `5.212 ms` |
| `3x3` | `6,645` | `5.074 ms` |

The dominant call-site probes are:

| Family | Source-root binding median-of-run-means | Compact-claim validation median-of-run-means | Terminal public-sum median-of-run-means | Nested recommits median-of-run-means |
| --- | ---: | ---: | ---: | ---: |
| `default` | `2.542 ms` | `1.213 ms` | `8.148 us` | `1.878-5.535 us` |
| `2x2` | `2.592 ms` | `1.284 ms` | `8.159 us` | `1.960-4.958 us` |
| `3x3` | `2.602 ms` | `1.245 ms` | `8.326 us` | `1.849-4.710 us` |

The source-root binding and compact-claim validation probes intentionally include nested
validation work. The rows are independent call-site probes, not an additive/exclusive
profile of the full verifier call.

## Interpretation

This microprofile supports the existing replay-avoidance interpretation:

1. The typed-boundary path does not contain a hidden per-step manifest replay surface.
2. The fixed nested recommit checks are microsecond-scale at the checked frontier.
3. The terminal-boundary LogUp public-sum check is fixed-width and microsecond-scale.
4. The millisecond-scale cost is in source-root/compact-claim validation and binding,
   not in rebuilding the ordered source manifest.

This does not prove a new asymptotic theorem. It is an implementation audit artifact that
makes the current `1024`-step frontier claim harder to misread: the typed-boundary verifier
is paying boundary validation and source-root binding, while the replay baseline pays the
linear source-surface reconstruction it was designed to remove.

## Follow-up

A useful future optimization/audit target is an exclusive profiler for the source-root
binding validator. The current microprofile deliberately uses production call sites and
therefore double-counts nested validation when rows are read together. An exclusive
instrumented profiler could split compact-claim validation, source-root field checks,
LogUp statement recomputation, and commitment checks without changing production verifier
behavior.
