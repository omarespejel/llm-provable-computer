# Issue #275 follow-up: second execution-proof surface and honest `4+` scaling

Date: 2026-04-26

This note records the repository state for GitHub issue `#275` (honest `4+`
second execution-proof family / backend for Tablero-style transfer claims).

## Disambiguation

The issue asks for a **second** honest execution-proof surface that can drive
the same Phase44D typed-boundary benchmark **beyond** the shipped carry-free
`2`-step checkpoint.

Two different readings matter for claims:

1. **Distinct from shipped carry-free publication default**
   The Phase12 **carry-aware experimental** execution-proof surface already
   constructs proof-checked Phase12 decoding chains at `4` through `1024` steps
   and runs the Phase44D source-emission benchmark over that chain. Checked
   median-of-5 engineering evidence lives in:

   - `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv`
   - `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.json`
   - `scripts/engineering/generate_phase44d_carry_aware_experimental_scaling_benchmark.sh`
   - `src/stwo_backend/primitive_benchmark.rs` (`phase44d_source_emission_experimental_benchmark_clears_honest_one_zero_two_four_steps`)

   This is **experimental lane only** (not the publication default backend).

2. **Distinct scalable surface that is also carry-free / publication-default**
   Still **no-go** for the default `decoding_step_v2` Phase12 demo family under
   bounded incoming and lookup rescaling. Verbatim blocker from
   `bench-stwo-phase44d-rescaled-exploratory` when the highest requested step
   count is `4`:

   > `phase44d rescaled exploratory benchmark could not find a carry-free rescaling profile that supports a proof-checked 4-step Phase12 source chain`

   Decision context:

   - `docs/engineering/phase44d-core-proving-lane-decision-gate-2026-04-24.md`
   - `docs/engineering/phase44d-second-backend-feasibility-gate-2026-04-25.md`

## Honest conclusion for paper-facing wording

- Do **not** upgrade publication claims to “carry-free Tablero scales past `2`
  steps” without a new carry-free family or proof surface that clears honest
  `4+` on the same benchmark.
- The carry-aware lane **does** answer the narrower engineering question “can
  the Phase44D mechanism scale in `N` on a different Phase12 execution-proof
  commitment ruleset?” with checked evidence, subject to the experimental claim
  boundary in `AGENTS.md`.

## Next research moves (tracked separately)

See GitHub issue `#277` (“Next-paper research backlog: Phase44D backends,
carry-free scaling, formal hooks”) for a prioritized backlog beyond this status
snapshot.
