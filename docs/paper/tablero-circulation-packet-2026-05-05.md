# Tablero Circulation Packet - 2026-05-05

This is the paper-facing circulation checklist for:

`Tablero: Typed Verifier Boundaries for Layered STARK Systems, with Evidence from STARK-zkML`

## What To Send

Primary files:

- `docs/paper/abstract-tablero-2026.md`
- `docs/paper/tablero-typed-verifier-boundaries-2026.md`
- `docs/paper/appendix-tablero-claim-boundary.md`
- `docs/paper/appendix-methodology-and-reproducibility.md`
- `docs/paper/appendix-system-comparison.md`

Evidence ledger:

- `docs/engineering/tablero-claim-evidence.yml`

Core figures:

- `docs/paper/figures/tablero-results-overview-2026-04.svg`
- `docs/paper/figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg`
- `docs/paper/figures/tablero-replay-baseline-breakdown-2026-04.svg`

## Safe Summary

Tablero is a typed verifier-boundary pattern for layered STARK systems. When the
source side emits complete, commitment-bound boundary facts, a verifier can replace an
expensive replay path with a compact typed object without widening the accepted
statement set.

## Evidence Snapshot

The current paper package supports these checked claims:

| Claim | Evidence posture |
| --- | --- |
| Statement preservation | Theorem under compact-proof soundness, commitment binding, and source-emission completeness. |
| Cross-family replay avoidance | Three checked layout families through `1024` steps. |
| Measured scaling law | Replay baseline near-linear over the checked grids; typed path grows more slowly in the measured regime. |
| Optimized replay red-team | Median-of-nine optimized replay verifier tightens the frontier ratio to a host-noise-sensitive `~261x`-`~330x` band. |
| Supporting second boundary | A distinct emitted-source surface clears as supporting evidence on the conservative publication row. |
| Compactness no-go | A smaller handoff object is not promoted as replay avoidance because it does not remove the replay dependency. |
| Statement-binding extension | External adapters and receipt gates support the distinction between proof validity and application statement validity. |

## Do Not Say

- Do not say Tablero makes STARK verification hundreds of times faster.
- Do not say the result is backend independent.
- Do not say this is recursive proof compression.
- Do not say this proves full transformer inference.
- Do not say the external adapters show EZKL, snarkjs, JSTprove, RISC Zero, or Stwo are unsound.
- Do not say the source-backed attention/KV receipt is proof-backed.

## Validation Gate

Run before circulating a fresh snapshot:

```bash
python3 scripts/paper/generate_tablero_results_overview.py
python3 scripts/paper/generate_tablero_scaling_law.py
python3 scripts/paper/generate_tablero_replay_breakdown.py
python3 scripts/paper/paper_preflight.py --repo-root .
python3 -m unittest scripts.tests.test_aggregate_tablero_replay_breakdown scripts.tests.test_zkai_attention_kv_transition_receipt_probe scripts.tests.test_zkai_attention_kv_proof_route_selector_gate
git diff --check
```

## Current Stronger-Venue Follow-Up

The next research result should be proof-backed attention/KV state binding:

1. Preserve the source-backed receipt contract that already binds prior KV, input,
   output, next KV, model config, verifier domain, and proof status.
2. Replace the source-backed proof status with a real proof-backed adapter or native
   Stwo proof over the same public fields.
3. Keep Softmax out of scope unless the proof actually covers the chosen attention
   semantics.
4. Report GO only when the same relabeling surfaces reject after proof serialization.
5. Report NO-GO if the route collapses into a stateless block, metadata-only receipt, or
   missing backend.
