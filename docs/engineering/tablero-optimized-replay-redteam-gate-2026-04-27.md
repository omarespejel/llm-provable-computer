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
- Frontier: `1024` honest proof-checked steps (same shared frontier as the
  family-matrix and replay-decomposition evidence).
- Timing mode: `measured_median`.
- Timing policy: `median_of_5_runs_from_microsecond_capture`.
- Aggregation strategy: `median_total_representative_run` (consistent with
  the existing replay-decomposition aggregator).

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
   `phase30_commit_phase12_decoding_chain_for_step_envelopes_binary` and
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

- `docs/engineering/evidence/phase44d-carry-aware-experimental-replay-baseline-breakdown-optimized-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-replay-baseline-breakdown-optimized-2026-04.json`

## Result

Median-of-five runs at `1024` steps:

| Family | Optimized replay total | Original replay total | Speedup | Optimized ratio (typed-boundary verify : optimized replay total) |
| --- | ---: | ---: | ---: | ---: |
| default | `2,371.934 ms` | `8,317.269 ms` | `3.5x` | `291.7x` |
| `2x2` | `2,085.380 ms` | `7,182.913 ms` | `3.4x` | `256.8x` |
| `3x3` | `2,202.230 ms` | `7,721.977 ms` | `3.5x` | `265.0x` |

The headline replay-avoidance ratio at the `1024`-step frontier moves from
`917x`-`1066x` (Section 6.2 of the paper) to `~257x`-`~292x` once the
JSON-tax component of the original replay path is removed.

## Causal decomposition of the optimized total

The optimization touches two of the four non-trivial replay buckets:

| Bucket | Original (JSON-keyed) | Optimized (binary) | Change |
| --- | ---: | ---: | ---: |
| source-chain commitment | `~2,260 ms` | `~115 ms` | `-95%` |
| per-step proof commitment | `~2,250 ms` | `~118 ms` | `-95%` |
| manifest finalize (state derivation) | `~1,860 ms` | `~1,950 ms` | `~unchanged` |
| equality check | `~0.2 ms` | `~0.13 ms` | `~unchanged` |

The two binary-commitment buckets each drop by roughly `19x`, confirming
that `~95%` of those buckets' cost in the original path was JSON-serialize
overhead rather than cryptographic work. The `manifest_finalize` bucket is
unchanged because it still includes the per-step state-derivation work that
confirms every recorded `from_state`/`to_state` pair against the program's
deterministic re-execution. That structural per-step work is the residual
the typed boundary genuinely avoids.

## Interpretation

1. The slope-difference structural claim (Section 6.3 of the paper) is
   unaffected. The optimized replay surface still scales linearly in `N`
   while the typed-boundary verify surface stays sublinear.
2. The constant-factor headline tightens by `~3.5x`. The
   implementation-cost component of the original `~1000x` figure is
   `~3.5x`; the implementation-independent component is `~270x` at the
   checked frontier and reflects work the typed boundary genuinely avoids
   by relying on the compact projection proof's trace commitment instead
   of re-deriving states from the chain.
3. The headline number in the paper now leads with the slope claim and
   reports both the original and optimized constants explicitly.

## Reproduction

```bash
BENCH_RUNS=5 \
CAPTURE_TIMINGS=1 \
  scripts/engineering/generate_tablero_replay_breakdown_optimized_benchmark.sh
```

Optionally pre-build the release binary first
(`cargo +nightly-2025-07-14 build --release --features stwo-backend --bin tvm`)
to keep run-to-run host noise low.

## References

- Issue #290 (red-team replay baseline; this gate closes the experiment).
- Issue #288 (paper-research meta tracker).
- `src/stwo_backend/decoding.rs`:
  `phase30_prepare_decoding_step_proof_envelope_manifest_optimized`,
  `verify_phase30_decoding_step_proof_envelope_manifest_against_chain_optimized_replay_with_breakdown`,
  `phase30_commit_step_proof_binary`,
  `phase30_commit_phase12_decoding_chain_for_step_envelopes_binary`.
- `docs/paper/tablero-typed-verifier-boundaries-2026.md` Section 6.6 ("Red-teaming the constant").
