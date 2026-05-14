# Native d128 two-slice outer statement proof

Date: 2026-05-14

Issue: #583

## Decision

`NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_AIR_PROOF`

The repository now has a real native Stwo proof over the two selected d128
outer statement rows:

- `rmsnorm_public_rows`
- `rmsnorm_projection_bridge`

The proof binds the selected slice IDs, row counts, statement commitments,
public-instance commitments, proof-native parameter commitments, source evidence
hashes, backend labels, verifier-domain labels, the two-slice target
commitment, the non-recursive accumulator commitment, and the verifier-handle
commitment.

After review hardening, the proof uses an empty preprocessed tree and one
verifier-recomputed base trace for the selected outer-statement rows. The base
root is checked against the validated input before Stwo verification.

## Checked Numbers

- selected rows: `256`
- selected slices: `2`
- backend/profile: `Rust nightly-2025-07-14` with `--features stwo-backend`
- backend version: `stwo-d128-two-slice-outer-statement-air-proof-v1`
- timing mode: `proof_existence_and_byte_accounting_only_not_public_benchmark`
- native outer statement proof bytes: `11,041`
  (`serde_json`-serialized native Stwo proof payload bytes)
- native outer statement envelope bytes: `94,864`
- proof SHA-256:
  `8cd1352ea9cff6dfd2a4b25fc881649679c10a1751be7568e72936ac3f397d9e`
- statement commitment:
  `blake2b-256:ab06c13b3bd24aad37285c4b6c759b9c30faf747af3248c2e45a2c245e7f8dc8`
- public-instance commitment:
  `blake2b-256:dbb25a1e94bb38c2aeedfcf38b2cebd401427c633860577893e46389f3565beb`
- mutation cases rejected: `25 / 25`, including unknown envelope-key and list-order rejection

The native outer statement proof is `1.600145x` the NANOZK paper-reported
`6.9 KB` transformer-block proof row. This is not a NANOZK win because the
workload and object class are not matched, and this proof does not execute the
inner Stwo verifier inside Stwo.

## Interpretation

This is useful progress, but it narrows the claim instead of completing issue `#583`.
We moved from compact package accounting to a native Stwo proof object
that binds the two selected host-verified slice results. That gives the next
verifier-execution route a concrete target and prevents relabeling package
bytes, compressed transcripts, or external SNARK bytes as native Stwo proof
bytes.

The result is not yet the breakthrough gate. The breakthrough gate remains:
execute the selected inner Stwo verifier checks inside a native Stwo outer AIR,
then measure proof bytes from that native object.

## Non-Claims

- not native verifier execution of the selected inner Stwo proofs
- not recursion or proof-carrying data
- not a native d128 transformer-block proof
- not a NANOZK proof-size win
- not a matched external zkML benchmark
- not stable binary proof-size accounting
- not full transformer inference
- not production-ready zkML

## Artifacts

- input JSON:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json`
- input TSV:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv`
- proof envelope:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json`
- gate JSON:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.json`
- gate TSV:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.tsv`

## Local Validation

```bash
python3 scripts/zkai_native_d128_two_slice_outer_statement_input.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv
cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- prove docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- verify docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 test d128_native_two_slice_outer_statement_proof --lib --features stwo-backend
python3 scripts/zkai_native_d128_two_slice_outer_statement_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_native_d128_two_slice_outer_statement_gate
git diff --check
just gate-fast
```

Full `just gate` status: attempted locally, but not counted as passed. The
release gate cleared gates `01` through `10` and then stalled in gate `11`
(`cargo-deny -> cargo fetch`). Offline retry reached the same dependency-check
stage and failed because uncached transitive crates required network fetches.
