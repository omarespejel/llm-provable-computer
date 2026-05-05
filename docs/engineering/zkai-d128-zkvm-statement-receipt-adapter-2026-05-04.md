# d128 zkVM Statement-Receipt Adapter Gate

Date: 2026-05-05

## Decision

`NO_GO_D128_ZKVM_STATEMENT_RECEIPT_ADAPTER_INCOMPLETE`

This gate answers issue `#422`.

The issue `#424` d128 two-slice public-input contract can be mapped into a
zkVM-style public journal / public-values contract. That contract binds the
same statement boundary used by the external SNARK receipt route: selected slice
statement commitments, source evidence hashes, public-instance commitments,
proof-native parameter commitments, verifier domain, backend version, source
accumulator commitment, and source verifier-handle commitment.

This adapter gate remains a bounded NO-GO because it maps and probes the route
but does not itself verify a zkVM receipt. The follow-up issue `#433` now
provides the real RISC Zero receipt and host verification for the same journal
contract. Treat this file as the journal-contract and adapter-boundary record;
treat `docs/engineering/zkai-d128-risc0-statement-receipt-2026-05-05.md` as the
route-specific RISC Zero receipt GO.

The gate also fails closed for future local environments: command availability
or an arbitrary file at the receipt path is not enough to advance the route. A
candidate receipt artifact must be non-empty, no larger than `1,048,576` bytes,
parseable as `zkai-d128-zkvm-statement-receipt-candidate-v1`, route-matched,
and bound to the current journal commitment before the blocker can move past
artifact availability. The blocker states are intentionally distinct:
`MISSING_ZKVM_RECEIPT_ARTIFACT` means no file exists,
`MISSING_OR_UNREADABLE_ZKVM_RECEIPT_ARTIFACT` means a file exists but is empty,
oversized, unparseable, uses the wrong candidate schema, mismatches the route or
zkVM system, is not bound to the current journal commitment, or lacks a valid
`receipt_commitment`, and
`MISSING_ZKVM_RECEIPT_VERIFICATION_AND_PUBLIC_VALUES_BINDING` means a
candidate exists but verifier execution and public-values binding are still not
implemented. A GO still requires the gate to run the route verifier and check
that the public journal / public-values bind the exact statement contract below.
The receipt probe records the configured byte cap and whether the cap was
exceeded; it intentionally does not record the artifact's exact byte length, so
local timing-field churn in downstream receipt evidence does not force this
adapter evidence to be regenerated.

## Checked Result

| Field | Value |
|---|---|
| Source issue | `#424` |
| Source contract | `docs/engineering/evidence/zkai-d128-proof-native-two-slice-compression-2026-05.json` |
| Journal contract schema | `zkai-d128-zkvm-statement-journal-contract-v1` |
| Journal commitment | `blake2b-256:f5890b4cff1f1fba01caabe692af96e53a1c514b2f84201d17b2a793af298569` |
| Input commitment | `blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6` |
| Output commitment | `blake2b-256:cca7656213e2439236b6ec2fefb7aa57daf6411fc6b3e9dedd27cd4fa7b428c4` |
| Policy label | `statement-receipt-adapter-policy:d128-two-slice:no-metadata-relabeling:v1` |
| Action label | `verify_d128_two_slice_statement_receipt` |
| RISC Zero route | candidate artifact present; adapter gate stops before verifier execution |
| SP1 route | missing `sp1up`, `cargo-prove`; no receipt artifact |
| Proof metrics | disabled in this adapter gate; issue `#433` carries the RISC Zero receipt metrics |
| Mutation coverage | `23 / 23` rejected |

## What This Means

This is not a failure of the statement-bound receipt direction. It separates two
facts that should not be collapsed:

- `GO`: the #424 statement has a concrete zkVM public journal/public-values
  contract.
- `NO-GO`: this adapter gate still does not execute the zkVM verifier or check
  public-values binding itself.
- `FOLLOW-UP GO`: issue `#433` executes the RISC Zero route for this journal
  contract and verifies a real receipt.

That is useful evidence for the paper because it keeps the claim honest: the
SNARK adapter route is real, the RISC Zero route is real in issue `#433`, and
this issue `#422` artifact remains the checked journal/adapter boundary instead
of pretending to be the route verifier.

## Mutation Coverage

The gate rejects `23 / 23` mutations across:

- source #424 decision, claim-boundary, and target commitment relabeling;
- journal schema, policy, action, verifier-domain, source-hash, and commitment
  relabeling;
- RISC Zero and SP1 toolchain availability relabeling;
- route relabeling from NO-GO to GO;
- fake receipt-artifact presence;
- receipt-probe byte-bound removal and byte-limit drift;
- proof-size, verifier-time, and proof-generation metric smuggling;
- top-level decision relabeling;
- non-claim removal;
- validation-command removal; and
- unknown top-level field injection.

## Non-Claims

This gate does not claim:

- a zkVM receipt;
- a RISC Zero proof;
- an SP1 proof;
- a zkML performance benchmark;
- recursive verification of the underlying Stwo slice proofs inside a zkVM;
- that RISC Zero or SP1 cannot implement this contract;
- that RISC Zero or SP1 are missing statement binding internally;
- a Starknet deployment result; or
- replacement of the Stwo-native d128 transformer receipt track.

## Reproduce

```bash
python3 scripts/zkai_d128_zkvm_statement_receipt_adapter_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-zkvm-statement-receipt-adapter-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-zkvm-statement-receipt-adapter-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_zkvm_statement_receipt_adapter_gate
python3 -m py_compile scripts/zkai_d128_zkvm_statement_receipt_adapter_gate.py \
  scripts/tests/test_zkai_d128_zkvm_statement_receipt_adapter_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Follow-Up

Issue `#433` is the follow-up for the real fixture. It pins RISC Zero `3.0.5`,
checks in a receipt artifact for this exact journal contract, verifies the
receipt against the compiled image id, and rejects relabeling of model/program
identity, input commitment, output commitment, action/policy label, verifier
domain, receipt commitment, and journal commitment.
