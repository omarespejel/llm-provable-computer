# Tablero Technical Review Packet - 2026-05-05

This is the internal technical-review checklist for:

`Tablero: Typed Verifier Boundaries for Layered STARK Systems, with Evidence from STARK-zkML`

This packet is not a publication/default-lane release packet. It includes
explicitly labeled experimental evidence so trusted reviewers can inspect the
upside result without confusing it for default-backend behavior.

## What To Send

Primary files:

- `docs/paper/abstract-tablero-2026.md`
- `docs/paper/tablero-typed-verifier-boundaries-2026.md`
- `docs/paper/appendix-tablero-claim-boundary.md`
- `docs/paper/appendix-methodology-and-reproducibility.md`
- `docs/paper/appendix-system-comparison.md`

Evidence ledger:

- `docs/engineering/tablero-claim-evidence.yml`

Publication-safe core figures:

- `docs/paper/figures/tablero-results-overview-2026-04.svg`
- `docs/paper/figures/tablero-replay-baseline-breakdown-2026-04.svg`

Experimental review figure:

- `docs/paper/figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg`

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
| Cross-family replay avoidance | Three checked layout families through `1024` steps on the explicitly labeled carry-aware experimental backend. |
| Measured scaling law | Experimental review evidence only: replay baseline near-linear over the checked grids; typed path grows more slowly in the measured regime. |
| Optimized replay red-team | Median-of-nine optimized replay verifier tightens the frontier ratio to a host-noise-sensitive `~261x`-`~330x` band. |
| Supporting second boundary | A distinct emitted-source surface clears as supporting evidence on the conservative publication row. |
| Compactness no-go | A smaller handoff object is not promoted as replay avoidance because it does not remove the replay dependency. |
| Statement-binding extension | External adapters and receipt gates support the distinction between proof validity and application statement validity. |
| Native Stwo attention/KV bridge | Tiny checked native AIR for fixed `d=8` causal-prefix integer-argmax attention/KV carried state; experimental bridge for the next transformer/STARK paper, not a Tablero performance row. |

## Do Not Say

- Do not say Tablero makes STARK verification hundreds of times faster.
- Do not say the result is backend independent.
- Do not say this is recursive proof compression.
- Do not say this proves full transformer inference.
- Do not say the external adapters show EZKL, snarkjs, JSTprove, RISC Zero, or Stwo are unsound.
- Do not say the attention/KV SNARK statement receipt proves attention arithmetic or Softmax semantics.
- Do not say the attention/KV RISC Zero transition or sequence receipts are native Stwo proofs, Softmax proofs, full inference proofs, long-context benchmarks, or recursive/PCD results.
- Do not say the native Stwo attention/KV proof is Softmax, multi-head attention, long-context inference, full inference, a benchmark row, or recursive/PCD.

## Validation Gate

Run before circulating a fresh snapshot:

```bash
python3 scripts/paper/generate_tablero_results_overview.py
python3 scripts/paper/generate_tablero_scaling_law.py
python3 scripts/paper/generate_tablero_replay_breakdown.py
python3 scripts/paper/paper_preflight.py --repo-root .
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend
python3 -m unittest scripts.tests.test_aggregate_tablero_replay_breakdown scripts.tests.test_zkai_attention_kv_transition_receipt_probe scripts.tests.test_zkai_attention_kv_snark_statement_receipt_gate scripts.tests.test_zkai_attention_kv_stwo_native_masked_sequence_proof_input scripts.tests.test_zkai_attention_kv_proof_route_selector_gate
git diff --check
```

## Current Stronger-Venue Follow-Up

The attention/KV lane now has a tiny native Stwo AIR proof for the fixed `d=8`
causal-prefix masked integer-argmax carried-state surface. The proof checks `52`
score rows over a `64`-row trace, emits selected positions
`0, 2, 3, 3, 5, 5, 7, 9`, binds ten final KV rows, and has a `24394`-byte proof
inside a `265791`-byte checked envelope. The route selector now records six
proof-backed routes and rejects `42 / 42` checked mutations. External
`snarkjs/Groth16` and RISC Zero receipts remain useful controls for
statement-binding and zkVM semantic transfer, but they are not the headline.

The next research result should scale the native Stwo surface, not add another
metadata adapter:

1. Preserve the source-backed receipt contract that already binds prior KV, input,
   output, next KV, model config, verifier domain, and proof status.
2. Keep the external SNARK statement receipt as a proof-system-independent
   statement-binding control.
3. Scale the native Stwo proof by one axis only: `d=16`, multi-head, longer fixed
   sequence, or a bounded Softmax-like approximation.
4. Treat the external RISC Zero rows as controls and only widen them if they
   remain useful for cross-proof-system carried-state evidence.
5. Keep Softmax out of scope unless the native proof actually covers the chosen attention
   semantics.
6. Report GO only when the same relabeling surfaces reject after proof serialization.
7. Report NO-GO if the route collapses into a stateless block, metadata-only receipt, or
   missing backend.
