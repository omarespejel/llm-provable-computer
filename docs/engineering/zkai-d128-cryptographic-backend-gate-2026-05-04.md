# d128 Cryptographic Backend Gate

Date: 2026-05-04

## Decision

`GO_D128_EXTERNAL_SNARK_STATEMENT_RECEIPT_BACKEND_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT`

This gate answers issue `#426`.

The repository has a checked proof-native d128 two-slice public-input contract
from issue `#424`, and issue `#428` now adds an executable external
`snarkjs/Groth16` statement receipt for that contract.

This supersedes the original bounded no-go for the external SNARK route. It does
not change the local-recursion boundary: there is still no local nested-verifier
AIR/circuit, no local PCD/IVC outer proof generator, and no real zkVM receipt.
Issue `#422` now narrows the zkVM branch to a checked public journal/public-values
contract plus a toolchain/bootstrap no-go.

## Source Contract

The source contract is the issue `#424` proof-native two-slice object:

| Field | Value |
|---|---|
| Source result | `GO` |
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Selected checked rows | `256` |
| Two-slice target commitment | `blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6` |
| Compressed artifact commitment | `blake2b-256:cca7656213e2439236b6ec2fefb7aa57daf6411fc6b3e9dedd27cd4fa7b428c4` |
| Verifier-handle commitment | `blake2b-256:704d117c500f82b109cee00370436af47f487e33e3c95368d0170fd0a31d6641` |
| Compressed artifact bytes | `4435` |

The target backend must bind the same public-input contract:

1. `two_slice_target_commitment`;
2. selected slice statement commitments;
3. selected source evidence hashes;
4. selected public-instance commitments;
5. selected proof-native parameter commitments;
6. verifier domain;
7. required backend version;
8. source accumulator commitment; and
9. source verifier-handle commitment.

## Backend Probe

The checked repo probe now finds one usable external cryptographic backend
route: the issue `#428` `snarkjs/Groth16` statement receipt for the exact issue
`#424` public-input contract. The local recursive/PCD routes remain missing, and
the real external zkVM receipt route remains missing:

| Route | Status | Usable today |
|---|---|---:|
| Source proof-native two-slice contract | `GO_INPUT_CONTRACT_ONLY_NOT_CRYPTOGRAPHIC_BACKEND` | yes, as input only |
| Local Stwo nested verifier backend | `NO_GO_MISSING_NESTED_VERIFIER_AIR_OR_CIRCUIT` | no |
| Local PCD or IVC outer proof backend | `NO_GO_MISSING_OUTER_PROOF_GENERATOR_AND_VERIFIER_HANDLE` | no |
| External zkVM statement receipt backend | `NO_GO_D128_ZKVM_STATEMENT_RECEIPT_TOOLCHAIN_BOOTSTRAP_MISSING` | no |
| External SNARK or IVC statement receipt backend | `GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_BACKEND_FOR_D128_CONTRACT` | yes |
| Starknet settlement adapter | `DEFERRED_UNTIL_A_PROOF_OBJECT_EXISTS` | no |

The remaining missing objects are:

> local nested verifier AIR/circuit, local PCD/IVC backend, and real external zkVM receipt

## Why This Matters

The previous issue `#424` result is a real improvement: it compresses the
verifier-facing two-slice transcript/public-input object. But it is not a
cryptographic proof object produced by a backend.

This gate makes the remaining research fork explicit:

- build a local nested-verifier AIR/circuit or PCD/IVC backend for the same
  public-input contract; or
- install/pin one external zkVM toolchain and produce a real statement receipt
  over the issue `#422` journal/public-values contract.

The external SNARK/IVC branch is no longer a missing route: issue `#428`
landed the `GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_BACKEND_FOR_D128_CONTRACT`
adapter. `DEFERRED_UNTIL_A_PROOF_OBJECT_EXISTS` still applies only to the
Starknet settlement adapter, because no settlement-shaped proof object exists
for this contract yet.

The SNARK route may now report the checked proof size (`802` bytes). Do not
report verifier time or proof-generation time until a dedicated timing gate
measures them.

## Mutation Coverage

The gate rejects `35 / 35` mutation cases, including:

- source file-hash, payload-hash, result, compression-result, recursive-result,
  and claim-boundary drift;
- target, selected statement, selected source hash, selected public instance,
  selected proof-native parameter, verifier-domain, backend-version, source
  accumulator, and source verifier-handle relabeling;
- compressed artifact and verifier-handle commitment drift;
- repo-probe dependency or artifact-presence relabeling;
- fake local nested-verifier, local PCD/IVC, external zkVM receipt, or stale
  external SNARK/IVC route relabeling;
- route blocker removal and route-level metric smuggling;
- decision-level proof-size, verifier-time, and proof-generation-time metric
  smuggling; and
- parser-level non-claim removal, validation-command drift, and unknown-field
  injection.

## Non-Claims

This gate does not claim:

- recursive aggregation;
- proof-carrying data;
- STARK-in-STARK verification;
- a zkVM receipt;
- recursive verification of the underlying Stwo slice proofs inside SNARK;
- verifier-time evidence for a cryptographic backend;
- proof-generation-time evidence for a cryptographic backend;
- that RISC Zero, SP1, Halo2, Nova, or other external systems cannot implement
  the contract;
- a public zkML benchmark row; or
- onchain deployment evidence.

## Reproduce

```bash
python3 scripts/zkai_d128_cryptographic_backend_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-cryptographic-backend-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-cryptographic-backend-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_cryptographic_backend_gate
python3 -m py_compile scripts/zkai_d128_cryptographic_backend_gate.py \
  scripts/tests/test_zkai_d128_cryptographic_backend_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Next Step

Issue `#428` is now the proof-system-independent control: a real SNARK
statement receipt exists for the exact issue `#424` public-input contract. Issue
`#422` now records the corresponding zkVM journal/public-values contract and the
first blocker (`MISSING_LOCAL_ZKVM_TOOLCHAIN_BOOTSTRAP`). The next useful
implementation experiment is route-specific: install and pin either RISC Zero or
SP1, then produce a real receipt for that exact contract without reporting
proof metrics until the receipt verifies.
