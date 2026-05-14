# Native d128 Two-Slice Verifier-Execution Target

Date: 2026-05-14

## Question

What exact proof objects and typed proof-field surface must the next native Stwo
two-slice verifier-execution AIR consume?

Selected slices:

- `rmsnorm_public_rows`
- `rmsnorm_projection_bridge`

## Decision

`GO_SELECTED_INNER_PROOF_OBJECTS_PINNED_NATIVE_VERIFIER_EXECUTION_TARGET`

This is a target-pinning result, not recursion. The repository now checks in the
two selected inner Stwo proof envelopes and records their local typed
`StarkProof` accounting next to the compact native outer statement proof.

## Result

| Object | JSON proof bytes | Local typed bytes | Envelope bytes |
| --- | ---: | ---: | ---: |
| `rmsnorm_public_rows` inner Stwo proof | `22,425` | `9,128` | `217,347` |
| `rmsnorm_projection_bridge` inner Stwo proof | `12,441` | `3,560` | `117,771` |
| Selected inner proof total | `34,866` | `12,688` | |
| Compressed outer statement proof | `3,516` | `1,792` | `34,471` |

The selected inner proof target is:

- `9.916382x` the compact outer statement proof in JSON proof bytes.
- `7.080357x` the compact outer statement proof in local typed proof-field bytes.
- `1.838841x` NANOZK's paper-reported `6.9 KB` block-proof row in typed bytes.
- `5.053043x` NANOZK's paper-reported row in JSON proof bytes.

The compact outer statement proof remains:

- `0.259710x` NANOZK's paper-reported row in typed bytes.
- `0.509565x` NANOZK's paper-reported row in JSON proof bytes.

The gate rejects `29 / 29` target, row-field, metric, overclaim, validation,
and mutation-summary drift cases.

## Interpretation

This is the sharpest comparison boundary so far.

The compact outer statement proof is real and small, but it does not execute the
inner Stwo verifiers. The pinned inner proof envelopes show the object class
that a native verifier-execution result must consume or replace. In human terms:
the target is now concrete, and the gap is measurable.

The next breakthrough gate is not another package wrapper. It is a native Stwo
AIR that proves verifier execution for the two pinned proof envelopes while
binding slice IDs, statement commitments, source hashes, backend-version labels,
and public-input order.

## First Blocker

`the target proof envelopes are now concrete, but the repo still lacks a native
Stwo AIR that executes the two selected inner Stwo verifier checks`

## Non-Claims

- Not native verifier execution of the selected inner Stwo proofs.
- Not recursion or proof-carrying data.
- Not a native d128 transformer-block proof.
- Not a NANOZK proof-size win.
- Not a matched external zkML benchmark.
- Not verifier-time or prover-time evidence.
- Not full transformer inference.
- Not production-ready zkML.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.tsv`
- RMSNorm proof envelope:
  `docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json`
- Projection-bridge proof envelope:
  `docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json`
- Gate:
  `scripts/zkai_native_d128_two_slice_verifier_execution_target_gate.py`
- Tests:
  `scripts/tests/test_zkai_native_d128_two_slice_verifier_execution_target_gate.py`
- Envelope CLI:
  `src/bin/zkai_d128_selected_two_slice_proof_envelopes.rs`

## Reproduce

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_selected_two_slice_proof_envelopes -- prove docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_selected_two_slice_proof_envelopes -- verify docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json
python3 scripts/zkai_native_d128_two_slice_verifier_execution_target_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.tsv
python3 -m py_compile scripts/zkai_native_d128_two_slice_verifier_execution_target_gate.py scripts/tests/test_zkai_native_d128_two_slice_verifier_execution_target_gate.py
python3 -m unittest scripts.tests.test_zkai_native_d128_two_slice_verifier_execution_target_gate
cargo +nightly-2025-07-14 fmt --check
git diff --check
just gate-fast
just gate
```
