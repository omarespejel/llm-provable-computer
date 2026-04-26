# Phase43 Second-Boundary Feasibility Gate (April 25, 2026; refreshed April 26)

Date: 2026-04-25
Refresh: 2026-04-26

## Scope

This note answers the second-boundary question for Phase43 source-root binding:

> Can the verifier accept an emitted Phase43 source surface plus the compact projection proof without replaying the full trace or the Phase30 manifest, and does the current source side emit that surface honestly enough to count as a real boundary?

The goal is still the same as before:

- do not force a second result,
- do not relabel a verifier-only prototype as a boundary,
- only promote to **GO** if the source side actually emits the proof-native surface the verifier consumes.

## Evidence bundle

- `docs/engineering/evidence/phase43-source-root-feasibility-publication-2026-04.tsv`
- `docs/engineering/evidence/phase43-source-root-feasibility-publication-2026-04.json`
- `docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.tsv`
- `docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.json`
- `docs/engineering/figures/phase43-source-root-feasibility-experimental-2026-04.svg`
- `docs/engineering/figures/phase43-source-root-feasibility-experimental-2026-04.png`
- `docs/engineering/figures/phase43-source-root-feasibility-experimental-2026-04.pdf`
- `docs/engineering/phase43-proof-native-source-emission-feasibility-2026-04-26.md`

## Predeclared gate criteria

Phase43 counts as a real second boundary only if both of the following are true.

1. The mechanism works without the full Phase43 trace.
   - A real compact Phase43 proof must verify against a source-root claim without requiring the verifier to rebuild projection rows from the full trace.
2. The current source surface can supply the needed proof-native inputs honestly.
   - The source side must emit the proof-native commitments and public inputs needed for the verifier to check that source-root claim without falling back to full-trace replay or legacy Blake2b-only commitments.

## Code-backed result

The current code now records a clean **GO**:

- `source_root_claim_candidate_available = true`
- `source_root_compact_binding_verified_without_trace = true`
- `verifier_can_drop_full_phase43_trace_today = true`
- `useful_second_boundary_today = true`
- `decision = go_emitted_proof_native_source_boundary`

That is the important change from April 25.
The verifier-only prototype remains checked in and still reports **PARTIAL**.
What changed is that the source side now emits a real boundary surface:

- `Phase43HistoryReplayProofNativeSourceArtifact`
- `Phase43HistoryReplayProofNativeSourceChainPublicOutputBoundary`

The verifier accepts that emitted boundary plus the compact projection proof without the full Phase43 trace or the Phase30 manifest.

## Why this is now an honest boundary

The current source surface no longer stops at legacy hash-level commitments.
It now emits the proof-native fields that were missing in the April 25 gate:

- `projection_commitment_emitted_by_source_chain`
- `projection_row_commitment_or_openings_in_stwo_field_domain`
- `phase12_to_phase14_history_transform_public_inputs`
- `phase30_step_envelope_commitments_as_stwo_public_inputs`
- `non_blake2b_source_commitment_path_for_verifier`

The verifier-side acceptance consumes that emitted boundary directly.
The old prototype path is still fenced fail-closed:

- it remains marked as derived from the full trace inside the prototype helper,
- it still rejects any recommitted artifact that self-reports upstream source-proof emission,
- the **GO** result now comes only from the emitted boundary path, not from the prototype object.

## Feasibility benchmark

The tracked benchmark now compares:

1. Candidate path
   - accept one emitted Phase43 proof-native source boundary plus one compact Phase43 projection proof
2. Current baseline
   - derive the Phase43 source-root claim from the full Phase43 trace plus the Phase30 manifest, then verify the same compact Phase43 projection proof

This remains engineering-only evidence.
It is good enough to answer the gate honestly, but it is not a paper-promotion pass.

### Publication-lane checkpoint

At `2` steps on the conservative carry-free publication lane:

| Candidate total verifier-side work | Current baseline total verifier-side work | Ratio |
|---:|---:|---:|
| 0.857 ms | 1.045 ms | 1.22x |

### Experimental carry-aware results through 1024 steps

Checked median-of-5 engineering timings on the experimental carry-aware backend:

| Steps | Candidate total verifier-side work | Current baseline total verifier-side work | Ratio |
|---|---:|---:|---:|
| 2 | 0.830 ms | 1.018 ms | 1.23x |
| 4 | 0.842 ms | 1.160 ms | 1.38x |
| 8 | 0.937 ms | 1.390 ms | 1.48x |
| 16 | 1.009 ms | 1.805 ms | 1.79x |
| 32 | 1.156 ms | 2.620 ms | 2.27x |
| 64 | 1.490 ms | 4.303 ms | 2.89x |
| 128 | 2.073 ms | 7.651 ms | 3.69x |
| 256 | 3.109 ms | 14.064 ms | 4.52x |
| 512 | 5.337 ms | 27.598 ms | 5.17x |
| 1024 | 7.879 ms | 52.447 ms | 6.66x |

Causal decomposition at `1024` steps:

- compact proof only: `1.749 ms`
- source-root derivation only: `47.974 ms`
- source-boundary binding only: `2.424 ms`

This matters for the claim boundary:

- the emitted boundary is a heavier and more honest object than the earlier prototype source-root claim,
- so the ratio is smaller than the prototype-only feasibility run,
- but the replay-elimination shape is still real and still grows with `N`.

That is enough for the second-boundary gate.

## Honest read

### What is real now

- Phase43 source-root binding is a real second replay-eliminating boundary on the current emitted source surface.
- The verifier can accept the emitted proof-native boundary plus the compact proof without the full Phase43 trace.
- The verifier can do the same without the Phase30 manifest.
- The candidate-vs-baseline gap still grows with step count because the baseline keeps paying local source-root derivation work.

### What is still not claimed

- This is still engineering evidence, not a paper-facing promotion.
- The old verifier-shape prototype is not itself the boundary result and remains checked in only as a fenced historical intermediate.
- The ratio is not a “faster FRI” claim. The win is replay elimination and source-surface exposure, not a cryptographic-verifier speedup.

## Decision

### Verdict

**GO for claiming Phase43 as a real second boundary on the current emitted source surface.**

### Narrow caveat that stays in scope

The emitted boundary is a real verifier surface, but its checked performance evidence is still engineering-lane evidence, not a publication-lane promotion.

### Next move

Keep the paper wording careful:

- claim a real second boundary,
- describe the performance result as engineering evidence,
- keep the prototype note as historical context rather than as the load-bearing proof.

## Reproduction commands

Publication-lane checkpoint:

```bash
BENCH_RUNS=5 \
CAPTURE_TIMINGS=1 \
scripts/engineering/generate_phase43_source_root_feasibility_bundle.sh
```

Experimental feasibility sweep:

```bash
BENCH_RUNS=5 \
CAPTURE_TIMINGS=1 \
STEP_COUNTS=2,4,8,16,32,64,128,256,512,1024 \
scripts/engineering/generate_phase43_source_root_feasibility_bundle.sh
```

Figure generation:

```bash
python3 scripts/engineering/generate_phase43_source_root_feasibility_figure.py \
  --input-tsv docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.tsv
```
