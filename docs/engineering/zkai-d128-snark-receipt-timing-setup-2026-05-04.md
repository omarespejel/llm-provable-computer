# d128 SNARK Receipt Timing And Setup Gate

Date: 2026-05-04

## Decision

`GO_D128_SNARK_RECEIPT_TIMING_AND_THROWAWAY_SETUP_REGENERATION`

This gate answers issue `#430`.

The issue `#428` SNARK statement receipt is no longer only an existence result.
The repository now regenerates a local throwaway Groth16 setup for the same
statement-receipt circuit, produces five fresh proofs, verifies all five proofs,
and records median-of-5 timing evidence.

This remains a research adapter. The setup is explicitly local/throwaway and is
not a production trusted setup. The proof still receipts the issue `#424`
public-input contract; it does not recursively verify the underlying Stwo slice
proofs inside Groth16.

## Measured Result

Timing policy: `median_of_5_runs_from_perf_counter_ns_on_local_host`.

| Metric | Result |
|---|---:|
| Setup time, single local throwaway run | `29978.661 ms` |
| Proof-generation time, median of 5 | `349.647 ms` |
| Proof-generation time, min / max | `345.260 ms` / `364.744 ms` |
| Verifier time, median of 5 | `290.702 ms` |
| Verifier time, min / max | `281.518 ms` / `292.157 ms` |
| Generated proof size values | `803`, `804`, `805` bytes |
| Generated verification-key size | `5849` bytes |
| Source #428 proof size | `802` bytes |
| Source #428 verification-key size | `5854` bytes |

The generated proof bytes vary because Groth16 proving is randomized. The public
signals stay pinned: every generated proof emits public signals with file hash
`9ee74a372fb7c1958994e91e87365d7fc4c717badbfaa29722af5a7b3c204387`, matching
the checked #428 public-signal artifact.

## Setup Policy

| Field | Value |
|---|---|
| Setup class | `local_throwaway_groth16_setup_for_statement_receipt_timing_only` |
| Production trusted setup | `false` |
| Curve | `bn128` |
| Powers-of-tau power | `12` |
| proving key checked in | `false` |
| setup artifacts checked in | `false` |
| setup artifact scope | temporary directory deleted after gate |
| snarkjs | `0.7.6` |
| circom | `2.0.9` |

This is intentionally not promoted into a production ceremony claim. It only
shows that the statement-receipt route can be regenerated, proved, and verified
under a pinned local toolchain.

## Mutation Coverage

The gate rejects `15 / 15` timing/setup mutations, including:

- source #428 receipt decision, claim-boundary, and metric relabeling;
- setup-policy promotion to production;
- proving-key checked-in relabeling;
- timing-policy drift;
- proof-generation and verifier median metric smuggling;
- public-signal, generated-public, verification-key, and proof-size binding
  drift;
- non-claim removal;
- validation-command removal; and
- unknown top-level field injection.

## Non-Claims

This gate does not claim:

- recursive aggregation;
- proof-carrying data;
- STARK-in-SNARK verification;
- verification of the underlying Stwo slice proofs inside Groth16;
- a production trusted setup;
- an onchain verifier benchmark;
- a public zkML throughput benchmark; or
- that Groth16 is the preferred production backend.

## Reproduce

```bash
npm ci --prefix scripts
python3 scripts/zkai_d128_snark_receipt_timing_setup_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-snark-receipt-timing-setup-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-snark-receipt-timing-setup-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_snark_receipt_timing_setup_gate
python3 -m py_compile scripts/zkai_d128_snark_receipt_timing_setup_gate.py \
  scripts/tests/test_zkai_d128_snark_receipt_timing_setup_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Next Step

Issue `#422` remains the next proof-system-transfer test: run the same public
input contract through zkVM public journal/public-values semantics. A local probe
on this machine found `circom 2.0.9` available but no installed RISC Zero or SP1
CLI (`rzup`, `cargo-risczero`, `sp1up`, `cargo-prove` not found), so #422 should
start with an explicit toolchain/bootstrap gate before claiming a zkVM receipt.
