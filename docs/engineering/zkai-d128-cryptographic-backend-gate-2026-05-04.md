# d128 Cryptographic Backend Gate

Date: 2026-05-05

## Decision

`GO_D128_EXTERNAL_SNARK_AND_ZKVM_STATEMENT_RECEIPT_BACKENDS_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT`

This gate answers issue `#426`.

The repository has a checked proof-native d128 two-slice public-input contract
from issue `#424`. Issue `#428` adds an executable external
`snarkjs/Groth16` statement receipt for that contract, and issue `#433` now adds
a real RISC Zero receipt over the corresponding issue `#422` public journal.

This supersedes the earlier bounded no-go for external statement receipts. It
does not change the local-recursion boundary: there is still no local
nested-verifier AIR/circuit and no local PCD/IVC outer proof generator.

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

The checked repo probe now finds two usable external cryptographic backend
routes for the same statement surface:

- issue `#433`: a RISC Zero receipt over the issue `#422` journal contract;
- issue `#428`: a `snarkjs/Groth16` statement receipt over the issue `#424`
  public-input contract.

The local recursive/PCD routes remain missing:

| Route | Status | Usable today |
|---|---|---:|
| Source proof-native two-slice contract | `GO_INPUT_CONTRACT_ONLY_NOT_CRYPTOGRAPHIC_BACKEND` | yes, as input only |
| Local Stwo nested verifier backend | `NO_GO_MISSING_NESTED_VERIFIER_AIR_OR_CIRCUIT` | no |
| Local PCD or IVC outer proof backend | `NO_GO_MISSING_OUTER_PROOF_GENERATOR_AND_VERIFIER_HANDLE` | no |
| External zkVM statement receipt backend | `GO_EXTERNAL_RISC0_STATEMENT_RECEIPT_BACKEND_FOR_D128_CONTRACT` | yes |
| External SNARK or IVC statement receipt backend | `GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_BACKEND_FOR_D128_CONTRACT` | yes |
| Starknet settlement adapter | `DEFERRED_UNTIL_A_PROOF_OBJECT_EXISTS` | no |

The remaining missing objects are:

> local nested verifier AIR/circuit and local PCD/IVC backend

## Why This Matters

The previous issue `#424` result is a real improvement: it compresses the
verifier-facing two-slice transcript/public-input object. But it is not a
cryptographic proof object produced by a backend.

This gate makes the remaining research fork explicit:

- build a local nested-verifier AIR/circuit or PCD/IVC backend for the same
  public-input contract; or
- use the external SNARK and RISC Zero receipts as proof-system-independent
  controls for statement-envelope binding, without treating either as recursion.

The external SNARK/IVC branch is no longer a missing route: issue `#428`
landed the `GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_BACKEND_FOR_D128_CONTRACT`
adapter. The external zkVM branch is also no longer a missing route: issue `#433`
landed the `GO_EXTERNAL_RISC0_STATEMENT_RECEIPT_BACKEND_FOR_D128_CONTRACT`
receipt. `DEFERRED_UNTIL_A_PROOF_OBJECT_EXISTS` still applies only to the
Starknet settlement adapter, because no settlement-shaped adapter exists for
these proof objects yet.

The route table reports the SNARK proof size (`802` bytes) and the RISC Zero
receipt size (`310234` bytes) plus its single local engineering verifier/prover
times as route-scoped metrics. The backend decision keeps a
`proof_metrics_by_route` map so the SNARK and RISC Zero measurements are not
collapsed into one unlabeled backend-wide metric block. Do not promote those
single-run RISC Zero times into public benchmark claims or cross-system
comparisons.

The dedicated RISC Zero receipt gate remains the canonical strict verifier for
the receipt artifact. This aggregate backend gate validates the checked RISC
Zero evidence by default without re-running the local RISC Zero host toolchain,
so route classification can run in environments that only need to check pinned
evidence. Use `--strict-risc0-reverify` when the local RISC Zero toolchain is
available and the aggregate gate should also re-run the host verifier.

## Mutation Coverage

The gate rejects `37 / 37` mutation cases, including:

- source file-hash, payload-hash, result, compression-result, recursive-result,
  and claim-boundary drift;
- target, selected statement, selected source hash, selected public instance,
  selected proof-native parameter, verifier-domain, backend-version, source
  accumulator, and source verifier-handle relabeling;
- compressed artifact and verifier-handle commitment drift;
- repo-probe dependency or artifact-presence relabeling;
- fake local nested-verifier, local PCD/IVC, stale external zkVM, or stale
  external SNARK/IVC route relabeling;
- route blocker removal and route-level metric smuggling;
- decision-level proof-size, verifier-time, proof-generation-time,
  route-scoped metric, and metric-source relabeling; and
- parser-level non-claim removal, validation-command drift, and unknown-field
  injection.

## Non-Claims

This gate does not claim:

- recursive aggregation;
- proof-carrying data;
- STARK-in-STARK verification;
- recursive verification of the underlying Stwo slice proofs inside SNARK or
  zkVM;
- a RISC Zero benchmark;
- paper-facing verifier-time or proof-generation benchmark evidence;
- a cross-system performance comparison;
- that SP1, Halo2, Nova, or other external systems cannot implement the
  contract;
- a public zkML benchmark row; or
- onchain deployment evidence.

## Reproduce

```bash
PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" \
python3 scripts/zkai_d128_risc0_statement_receipt_gate.py \
  --verify-existing \
  --write-json docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.tsv

python3 scripts/zkai_d128_cryptographic_backend_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-cryptographic-backend-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-cryptographic-backend-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_d128_risc0_statement_receipt_gate \
  scripts.tests.test_zkai_d128_cryptographic_backend_gate
python3 -m py_compile scripts/zkai_d128_cryptographic_backend_gate.py \
  scripts/zkai_d128_risc0_statement_receipt_gate.py \
  scripts/tests/test_zkai_d128_risc0_statement_receipt_gate.py \
  scripts/tests/test_zkai_d128_cryptographic_backend_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Next Step

Issue `#428` and issue `#433` are now proof-system-independent controls: one
SNARK receipt and one zkVM receipt bind the same d128 two-slice statement
surface. The next useful implementation experiment is no longer "produce any
external receipt"; it is either local recursion/PCD for the two-slice target, or
a comparative external-control pass that keeps SNARK and zkVM receipt metrics
strictly scoped as adapter evidence.
