# Native d128 Two-Slice Outer Backend Gate

Date: 2026-05-14

## Question

Can the selected d128 two-slice surface now be claimed as an executable native
Stwo outer proof backend?

Selected slices:

- `rmsnorm_public_rows`
- `rmsnorm_projection_bridge`

## Decision

`NO_GO_EXECUTABLE_NATIVE_D128_TWO_SLICE_OUTER_PROOF_BACKEND_MISSING`

This is a bounded no-go. It is still useful because it narrows the blocker more
precisely than the earlier d128 block route gate.

The repository has:

- two selected inner Stwo slice proof modules;
- a `256`-row two-slice target;
- a non-recursive accumulator that binds selected statements and source hashes;
- a proof-native compressed transcript artifact;
- an external Groth16 statement receipt for the compressed contract;
- a compact `4,752` byte package signal for the broader d128 block route.

The repository still does not have:

- a native Stwo verifier-execution AIR/backend for the two selected verifier
  checks;
- a native outer proof artifact;
- a native outer verifier handle;
- fail-closed mutation tests for that future native proof artifact.

## Result

| Surface | Classification | Rows | Bytes | Native outer claim |
| --- | --- | ---: | ---: | --- |
| `rmsnorm_public_rows` inner Stwo proof | `INNER_STWO_SLICE_PROOF_NOT_OUTER_VERIFIER_EXECUTION` | `128` | | no |
| `rmsnorm_projection_bridge` inner Stwo proof | `INNER_STWO_SLICE_PROOF_NOT_OUTER_VERIFIER_EXECUTION` | `128` | | no |
| Two-slice non-recursive accumulator | `GO_NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF` | `256` | | no |
| Proof-native transcript compression | `GO_TRANSCRIPT_COMPRESSION_NOT_OUTER_PROOF` | `256` | `4,435` | no |
| External Groth16 statement receipt | `GO_EXTERNAL_SNARK_RECEIPT_NOT_NATIVE_STWO` | | `802` | no |
| Native d128 block route | `NO_GO_BLOCK_ROUTE_BLOCKED_BY_TWO_SLICE_OUTER_BACKEND` | | `4,752` | no |
| Required native two-slice outer backend | `MISSING_REQUIRED_NATIVE_OUTER_BACKEND` | | | missing |
| Required native outer proof artifact | `MISSING_REQUIRED_NATIVE_OUTER_PROOF_ARTIFACT` | | | missing |
| Required native outer verifier handle | `MISSING_REQUIRED_NATIVE_OUTER_VERIFIER_HANDLE` | | | missing |
| Required native outer artifact tests | `MISSING_REQUIRED_NATIVE_OUTER_MUTATION_TESTS` | | | missing |

## Numbers

- Selected checked rows: `256`.
- Two-slice target commitment:
  `blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6`.
- Non-recursive accumulator commitment:
  `blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d`.
- Source accumulator artifact: `8,822` bytes.
- Compressed transcript artifact: `4,435` bytes, ratio `0.50272x`.
- External Groth16 statement receipt: `802` proof bytes, `1,389` public-signal
  bytes, `5,854` verification-key bytes.
- Broader d128 package signal without VK: `4,752` bytes, `0.688696x` NANOZK's
  paper-reported `6,900` byte row.
- Broader d128 package with VK: `10,608` bytes, `1.537391x` NANOZK's
  paper-reported row.
- Mutation coverage: `29 / 29` mutations rejected.

## First Blocker

`no parameterized Stwo AIR/verifier-execution route exists for the selected d128
rmsnorm_public_rows and rmsnorm_projection_bridge verifier checks`

That is the next real engineering object. Additional wrappers, packages, or
external receipts do not close this gate unless they execute the selected
verifier checks in the claimed native proof system.

## Interpretation

The positive signal is still real: the two-slice surface has useful structure,
and the compressed/package objects are small. But the comparison with systems
like NANOZK is not ready until the native object class matches. The honest
paper-facing sentence is:

> We have inner native Stwo slice proofs, statement-bound accumulators, compact
> transcript/package artifacts, and external receipts; the missing breakthrough
> gate is a native Stwo outer backend that proves selected verifier execution.

## Non-Claims

- Not a native d128 two-slice outer proof.
- Not a native d128 transformer-block proof.
- Not a NANOZK proof-size win.
- Not a matched benchmark against NANOZK or another public zkML system.
- Not recursive aggregation or proof-carrying data.
- Not proof-size evidence for a native outer proof.
- Not verifier-time or prover-time evidence for a native outer proof.
- Not verification of the selected Stwo slice verifiers inside Stwo.
- Not full transformer inference.
- Not production-ready.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-backend-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-backend-2026-05.tsv`
- Gate:
  `scripts/zkai_native_d128_two_slice_outer_backend_gate.py`
- Tests:
  `scripts/tests/test_zkai_native_d128_two_slice_outer_backend_gate.py`

## Reproduce

```bash
python3 scripts/zkai_native_d128_two_slice_outer_backend_gate.py \
  --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-backend-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-backend-2026-05.tsv

python3 -m py_compile scripts/zkai_native_d128_two_slice_outer_backend_gate.py \
  scripts/tests/test_zkai_native_d128_two_slice_outer_backend_gate.py
python3 -m unittest scripts.tests.test_zkai_native_d128_two_slice_outer_backend_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
