# Phase43 Second-Boundary Feasibility Gate (April 25, 2026)

Date: 2026-04-25

## Scope

This note answers the first question in the current Tablero-strengthening roadmap:

> Can Phase43 source-root binding become a real second replay-eliminating boundary, or is it still only a useful internal mechanism with missing source-surface exposure?

The goal is not to force a second result. The goal is to avoid fooling ourselves about whether Phase43 is already a transferable boundary or still a blocked prototype.

## Evidence bundle

- `docs/engineering/evidence/phase43-source-root-feasibility-publication-2026-04.tsv`
- `docs/engineering/evidence/phase43-source-root-feasibility-publication-2026-04.json`
- `docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.tsv`
- `docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.json`
- `docs/engineering/figures/phase43-source-root-feasibility-experimental-2026-04.svg`
- `docs/engineering/figures/phase43-source-root-feasibility-experimental-2026-04.png`
- `docs/engineering/figures/phase43-source-root-feasibility-experimental-2026-04.pdf`

## Predeclared gate criteria

Phase43 counts as a real second boundary only if both of the following are true.

1. The mechanism works without the full Phase43 trace.
   - A real compact Phase43 proof must verify against a source-root claim without requiring the verifier to rebuild projection rows from the full trace.
2. The current source surface can supply the needed proof-native inputs honestly.
   - The source side must emit the proof-native commitments and public inputs needed for the verifier to check that source-root claim without falling back to full-trace replay or legacy Blake2b-only commitments.

If criterion 1 holds but criterion 2 fails, the honest result is:
- useful mechanism,
- no current second boundary,
- source-emission patch required before any paper claim.

## Code-backed feasibility result

The new combined feasibility assessment in `src/stwo_backend/history_replay_projection_prover.rs` records exactly that split.

Current result:

- `source_root_claim_candidate_available = true`
- `source_root_compact_binding_verified_without_trace = true`
- `verifier_can_drop_full_phase43_trace_today = false`
- `useful_second_boundary_today = false`
- `decision = no_go_missing_proof_native_source_emission`

So the mechanism is real, but the current source surface still blocks an honest second-boundary claim.

## Why the current source surface still blocks promotion

The current Phase30-backed source surface still exposes only legacy hash-level commitments.
It does not expose the proof-native inputs the verifier would need to accept a Phase43 source-root artifact directly.

The missing inputs recorded by the code are:

- `projection_commitment_emitted_by_source_chain`
- `projection_row_commitment_or_openings_in_stwo_field_domain`
- `phase12_to_phase14_history_transform_public_inputs`
- `phase30_step_envelope_commitments_as_stwo_public_inputs`
- `non_blake2b_source_commitment_path_for_verifier`

That is the blocker. Without these, any claimed Phase43 boundary still depends on local derivation from the full Phase43 trace plus Phase30 manifest.

## Feasibility prototype benchmark

To decide whether the missing source-emission patch is worth pursuing, the repo now includes a bounded feasibility benchmark.

It compares two verifier paths over the same real compact Phase43 proof:

1. Candidate path
   - accept one emitted Phase43 source-root claim plus one compact Phase43 projection proof
2. Current baseline
   - derive that same source-root claim from the full Phase43 trace plus Phase30 manifest, then verify the same compact Phase43 projection proof

This is an engineering-only prototype benchmark. It does **not** claim that the current source side already emits the source-root claim.

### Publication-lane checkpoint

The shipped carry-free publication lane still clears only the `2`-step point on the current execution-proof surface.
That point is worth recording because it shows the same mechanism on the conservative backend, but it does not change the decision:
the current blocker is still missing proof-native source emission.

At `2` steps on the publication lane:

| Candidate verify | Current baseline verify | Ratio |
|---:|---:|---:|
| 11.931 ms | 28.647 ms | 2.40x |

### Experimental carry-aware results through 128 steps

Single-run engineering timings on the experimental carry-aware Phase12 backend:

| Steps | Candidate verify | Current baseline verify | Ratio |
|---|---:|---:|---:|
| 2 | 8.884 ms | 16.055 ms | 1.81x |
| 4 | 10.560 ms | 19.312 ms | 1.83x |
| 8 | 11.125 ms | 26.531 ms | 2.38x |
| 16 | 16.281 ms | 40.423 ms | 2.48x |
| 32 | 18.391 ms | 62.614 ms | 3.40x |
| 64 | 25.692 ms | 110.134 ms | 4.29x |
| 128 | 55.495 ms | 389.573 ms | 7.02x |

Causal decomposition at 128 steps:

- compact proof only: `25.496 ms`
- source-root derivation only: `229.715 ms`
- source-root binding only: `30.356 ms`

So the gap is not a copy of Phase44D's huge manifest-replay elimination result, but it is also not flat noise.
The avoided work grows with step count because the current baseline keeps paying local source-root derivation from the full trace and Phase30 surface.

### Why the checked-in frontier stops at 128

The checked-in experimental evidence deliberately stops at `128` steps.
The go/no-go question is already decided by the missing proof-native source-emission surface, not by pushing the same prototype benchmark to larger `N`.
An additional `256/512/1024` exploratory run was intentionally not carried into the tracked gate because it cannot turn a missing-source-surface no-go into an honest boundary claim.

## Honest read

### What is real now

- Phase43 source-root binding is a real mechanism.
- The verifier can check the source-root claim against the same real compact proof without the full trace once the claim exists.
- The candidate-vs-baseline gap grows with step count on the experimental lane.

### What is not real yet

- Phase43 is **not** currently a real second boundary on shipped source surfaces.
- The repo cannot yet claim that the source chain emits the proof-native artifact needed to drop the full Phase43 trace honestly.
- This is not ready for paper promotion.

## Decision

### Verdict

**NO-GO for claiming Phase43 as a second Tablero boundary today.**

### Narrow positive result worth keeping

The repo now has evidence that a source-root-emission patch would not be cosmetic.
If the missing proof-native source inputs were emitted by the source chain, the verifier path would avoid a growing amount of full-trace derivation work.
That makes the patch research-worthy.

### Next move

Open a dedicated source-emission issue and keep it separate from paper-facing claims.
The next honest gate is:

> emit the proof-native Phase43 source-root surface from the source side, then rerun this same benchmark and only then decide whether Phase43 is a real second boundary.

## Reproduction commands

Publication-lane checkpoint:

```bash
cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  bench-stwo-phase43-source-root-feasibility \
  --capture-timings \
  --output-tsv docs/engineering/evidence/phase43-source-root-feasibility-publication-2026-04.tsv \
  --output-json docs/engineering/evidence/phase43-source-root-feasibility-publication-2026-04.json
```

Experimental feasibility sweep:

```bash
cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  bench-stwo-phase43-source-root-feasibility-experimental \
  --step-counts 2,4,8,16,32,64,128 \
  --capture-timings \
  --output-tsv docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.tsv \
  --output-json docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.json
```

Figure generation:

```bash
# requires matplotlib in the active Python environment
python3 scripts/engineering/generate_phase43_source_root_feasibility_figure.py
```
