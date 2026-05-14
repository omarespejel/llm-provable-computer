# Native d128 two-slice digest compression gate

Date: 2026-05-14

Issue: #585

## Decision

`GO_COMPRESSED_NATIVE_STWO_OUTER_STATEMENT_DIGEST_BINDING`

The d128 two-slice outer statement route now binds a compressed verifier-facing
digest surface instead of expanding every selected row digest into AIR columns.
The native proof commits to:

- statement commitment
- public-instance commitment
- proof-native parameter commitment

The statement commitment is still recomputed from the selected rows and binds
the selected slice IDs, source evidence hashes, backend labels, verifier-domain
labels, row counts, and slice commitments before proof verification.

## Checked Numbers

- selected rows: `256`
- selected slices: `2`
- prior native proof bytes: `11,041`
- compressed native proof bytes: `3,516`
- proof saving: `7,525` bytes, `68.1551%`
- prior envelope bytes: `94,864`
- compressed envelope bytes: `34,471`
- envelope saving: `60,393` bytes, `63.6627%`
- compressed proof ratio vs NANOZK paper-reported `6.9 KB` row: `0.509565x`
- mutation cases rejected: `25 / 25`
- proof SHA-256:
  `9977aeefe8021845a46a382be143824f10605b3ec676eaf0ed25e46f2d90e5f1`

## Interpretation

This is the first sharp proof-size win on the native d128 outer-statement
surface. The useful mechanism is not generic compression. It is a narrower
STARK-native binding surface: commit to the verifier-facing statement digest,
then let host validation expand that digest back to the selected row fields and
source hashes before verifying the native proof.

This does not complete the breakthrough gate. The route still does not execute
the selected inner Stwo verifiers inside Stwo, and the byte count is still JSON
proof payload accounting rather than stable binary proof-size accounting.

## Non-Claims

- not native verifier execution of the selected inner Stwo proofs
- not recursion or proof-carrying data
- not a native d128 transformer-block proof
- not a matched NANOZK proof-size win
- not stable binary proof-size accounting
- not full transformer inference
- not production-ready zkML

## Local Validation

```bash
python3 scripts/zkai_native_d128_two_slice_outer_statement_input.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv
cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- prove docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- verify docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json
python3 scripts/zkai_native_d128_two_slice_outer_statement_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.tsv
```
