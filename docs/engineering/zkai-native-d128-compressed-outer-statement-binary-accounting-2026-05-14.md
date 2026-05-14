# Native d128 compressed outer statement binary accounting

Date: 2026-05-14

Issue: #583

## Decision

`GO_LOCAL_BINARY_TYPED_ACCOUNTING_FOR_COMPRESSED_D128_OUTER_STATEMENT_PROOF`

The compressed native Stwo d128 outer-statement proof now has a checked
repo-owned typed accounting view. The accounting uses the existing Rust
`zkai_stwo_proof_binary_accounting` CLI to parse the `StarkProof` payload and
reconstruct a deterministic local record stream over typed proof fields:

- trace commitments
- trace Merkle decommitment witnesses
- sampled OODS values
- queried base-field values
- FRI witness values
- FRI commitments and decommitments
- proof-of-work
- PCS config

This is deliberately narrower than stable binary proof serialization. It is a
local typed accounting record stream, not upstream Stwo wire bytes.

## Checked Numbers

- proof object: compressed d128 two-slice native Stwo outer-statement proof
- backend version:
  `stwo-d128-two-slice-outer-statement-air-proof-v2-compressed-digest`
- JSON proof payload bytes: `3,516`
- local typed accounting bytes: `1,792`
- JSON minus local typed bytes: `1,724`
- JSON / local typed ratio: `1.962054x`
- local record-stream bytes: `1,084`
- local record-stream SHA-256:
  `3764bc286e5dffee3d9186861a5c2faeb44eff4add7a5c9613bb302e80197fad`
- proof SHA-256:
  `9977aeefe8021845a46a382be143824f10605b3ec676eaf0ed25e46f2d90e5f1`
- mutation cases rejected: `20 / 20`

Against the NANOZK paper-reported `6.9 KB` d128 transformer-block proof row:

- JSON proof payload ratio: `0.509565x`
- local typed accounting ratio: `0.259710x`

## Interpretation

This strengthens the current d128 signal. The earlier `3,516` byte result was
still JSON proof-payload accounting. The new `1,792` byte local typed view says
the compactness is not only JSON syntax. Most of the typed payload is the
actual proof-field surface: `960` bytes of sampled values, `480` bytes of
queried values, `224` bytes of trace commitments/decommitments, and small FRI
and fixed-overhead pieces.

The honest comparison is still conservative. This is an interesting-range
signal versus NANOZK, not a matched benchmark win. The object class differs:
this proof binds a compressed outer statement over selected host-verified d128
slice results. It is not yet a native d128 transformer-block proof executing
the selected inner verifier checks inside Stwo.

## Non-Claims

- not upstream Stwo proof serialization
- not binary PCS/FRI wire-format accounting
- not native verifier execution of the selected inner Stwo proofs
- not recursion or proof-carrying data
- not a native d128 transformer-block proof
- not a matched NANOZK proof-size win
- not a public benchmark
- not timing evidence
- not full transformer inference
- not production-ready zkML

## Artifacts

- JSON evidence:
  `docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json`
- TSV evidence:
  `docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.tsv`
- source proof envelope:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json`

## Local Validation

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json
python3 scripts/zkai_native_d128_compressed_outer_statement_binary_accounting_gate.py --write-json docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.tsv
python3 -m py_compile scripts/zkai_native_d128_compressed_outer_statement_binary_accounting_gate.py scripts/tests/test_zkai_native_d128_compressed_outer_statement_binary_accounting_gate.py
python3 -m unittest scripts.tests.test_zkai_native_d128_compressed_outer_statement_binary_accounting_gate
cargo +nightly-2025-07-14 fmt --check
git diff --check
just gate-fast
```
