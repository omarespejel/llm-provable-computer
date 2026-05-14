# One-Block Executable Package Accounting

Date: 2026-05-14

## Question

Once the attention-derived d128 statement chain has an executable external
statement receipt, how large is the verifier-facing package compared with the
source statement-chain artifact?

## Decision

`GO_ONE_BLOCK_EXECUTABLE_PACKAGE_ACCOUNTING_NO_GO_NATIVE_PROOF_SIZE`

The result is useful but narrow: the external executable statement package is
smaller than the source statement-chain artifact, both when the verification
key is treated as reusable and when it is counted in the package.

This is package accounting for an external statement receipt. It is not native
block proof-size evidence.

## Result

| Surface | Bytes | Ratio vs source | Saving |
| --- | ---: | ---: | ---: |
| Source statement-chain artifact | `14,624` | `1.000000x` | `0` |
| Compressed statement-chain artifact | `2,559` | `0.174986x` | `12,065` |
| Compressed artifact + proof + public signals | `4,752` | `0.324945x` | `9,872` |
| Compressed artifact + proof + public signals + VK | `10,608` | `0.725383x` | `4,016` |

The receipt still binds `17` public signals and carries `40 / 40` mutation
rejection from the upstream executable receipt gate.

## Interpretation

The useful signal is not that Groth16 is the desired production backend. The
useful signal is that the statement-bound one-block route now has a concrete
verifier-facing package-accounting discipline:

```text
source statement chain: 14,624 bytes
  -> compressed transcript: 2,559 bytes
  -> compressed transcript + proof + public signals: 4,752 bytes
  -> plus reusable/setup VK counted once: 10,608 bytes
```

This strengthens the architecture path because it turns the attention-derived
block surface into a package with explicit accounting, commitments, and
mutation rejection, instead of only a prose claim.

## Non-Claims

- Not a native d128 transformer-block proof.
- Not recursive aggregation.
- Not proof-carrying data.
- Not verification of the six Stwo slice proofs inside Groth16.
- Not native proof-size evidence for a fused route.
- Not verifier-time evidence.
- Not proof-generation-time evidence.
- Not a production trusted setup.
- Not a matched NANOZK or Jolt benchmark.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-one-block-executable-package-accounting-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-one-block-executable-package-accounting-2026-05.tsv`
- Gate:
  `scripts/zkai_one_block_executable_package_accounting_gate.py`
- Tests:
  `scripts/tests/test_zkai_one_block_executable_package_accounting_gate.py`

## Reproduce

```bash
python3 scripts/zkai_one_block_executable_package_accounting_gate.py \
  --write-json docs/engineering/evidence/zkai-one-block-executable-package-accounting-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-one-block-executable-package-accounting-2026-05.tsv

python3 -m py_compile scripts/zkai_one_block_executable_package_accounting_gate.py \
  scripts/tests/test_zkai_one_block_executable_package_accounting_gate.py
python3 -m unittest scripts.tests.test_zkai_one_block_executable_package_accounting_gate
git diff --check
just gate-fast
just gate
```
