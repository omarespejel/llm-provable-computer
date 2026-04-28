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
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_of_mean_256_iteration_microprofile`
- Step frontier: `1024` for `default`, `2x2`, and `3x3`

Regeneration command:

```bash
BENCH_RUNS=5 ITERATIONS=256 CAPTURE_TIMINGS=1 \
  scripts/engineering/generate_tablero_boundary_binding_microprofile_benchmark.sh
```

The generator fails closed if the benchmark identity, timing policy, family set, step
count, component count, verification flags, or non-additivity notes drift. It writes
median-of-five component rows so a single noisy microprofile run does not become the
checked evidence payload.

## Result

At the checked `1024`-step frontier, the full binding-only verifier surface remains in
single-digit milliseconds:

| Family | Boundary bytes | Full binding mean |
| --- | ---: | ---: |
| `default` | `6,561` | `5.084 ms` |
| `2x2` | `6,545` | `5.020 ms` |
| `3x3` | `6,557` | `4.965 ms` |

The dominant call-site probes are:

| Family | Source-root binding | Compact-claim validation | Terminal public sum | Nested recommits |
| --- | ---: | ---: | ---: | ---: |
| `default` | `2.456 ms` | `1.232 ms` | `8.348 us` | `1.920-4.815 us` |
| `2x2` | `2.447 ms` | `1.192 ms` | `8.230 us` | `1.868-4.715 us` |
| `3x3` | `2.479 ms` | `1.193 ms` | `8.266 us` | `1.867-4.792 us` |

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
