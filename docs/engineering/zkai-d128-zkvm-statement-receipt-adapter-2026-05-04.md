# d128 zkVM Statement-Receipt Adapter Gate

Date: 2026-05-04

## Decision

`NO_GO_D128_ZKVM_STATEMENT_RECEIPT_TOOLCHAIN_BOOTSTRAP_MISSING`

This gate answers issue `#422`.

The issue `#424` d128 two-slice public-input contract can be mapped into a
zkVM-style public journal / public-values contract. That contract binds the
same statement boundary used by the external SNARK receipt route: selected slice
statement commitments, source evidence hashes, public-instance commitments,
proof-native parameter commitments, verifier domain, backend version, source
accumulator commitment, and source verifier-handle commitment.

The route is still a bounded NO-GO today because this local machine does not
have a RISC Zero or SP1 proving toolchain installed, and the repository does not
contain a real zkVM receipt artifact for the contract.

The gate also fails closed for future local environments: command availability
or a receipt-looking file is not enough to produce a GO. A GO requires the gate
to run the route verifier and check that the public journal / public-values bind
the exact statement contract below.

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
| RISC Zero route | missing `rzup`, `cargo-risczero`; no receipt artifact |
| SP1 route | missing `sp1up`, `cargo-prove`; no receipt artifact |
| Proof metrics | disabled; no proof object exists |
| Mutation coverage | `21 / 21` rejected |

## What This Means

This is not a failure of the statement-bound receipt direction. It separates two
facts that should not be collapsed:

- `GO`: the #424 statement has a concrete zkVM public journal/public-values
  contract.
- `NO-GO`: there is no local executable RISC Zero or SP1 receipt route today.

That is useful evidence for the paper because it keeps the claim honest: the
SNARK adapter route is real, while the zkVM adapter route is now precisely
blocked at toolchain/bootstrap and receipt-artifact availability.

## Mutation Coverage

The gate rejects `21 / 21` mutations across:

- source #424 decision, claim-boundary, and target commitment relabeling;
- journal schema, policy, action, verifier-domain, source-hash, and commitment
  relabeling;
- RISC Zero and SP1 toolchain availability relabeling;
- route relabeling from NO-GO to GO;
- fake receipt-artifact presence;
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

## Next Step

The follow-up for a real fixture is tracked separately in issue `#433`. Pick one route, install/pin its
proving toolchain in a reproducible way, and produce the smallest real receipt
for this exact journal contract. The GO criterion remains strict: verifier
accepts the receipt and relabeling of model/program identity, input commitment,
output commitment, action/policy label, verifier domain, proof-system version,
or journal/public-values commitment is rejected.
