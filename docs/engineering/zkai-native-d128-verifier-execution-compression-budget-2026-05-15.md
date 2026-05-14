# Native d128 verifier-execution compression budget

Date: 2026-05-15

## Question

How much must the real d128 verifier-execution target shrink before it can be
compared honestly with NANOZK's paper-reported d128 block-proof row?

## Decision

`GO_D128_VERIFIER_EXECUTION_COMPRESSION_BUDGET_PINNED`

This is a budget result, not a benchmark win. It consumes the checked
two-slice verifier-execution target and the compressed outer-statement typed
accounting evidence, then separates the compact binding object from the
object class that would be comparable to a NANOZK-style block proof.

## Checked Numbers

| Object | JSON proof bytes | Local typed bytes | NANOZK comparison status |
| --- | ---: | ---: | --- |
| Compact outer statement binding | `3,516` | `1,792` | real, compact, not comparable |
| Selected inner verifier-execution target | `34,866` | `12,688` | candidate only after native execution or component reprove |

Against NANOZK's paper-reported d128 block-proof row of `6,900` bytes:

- The real selected verifier target is `1.838841x` NANOZK in local typed bytes.
- It is `5.053043x` NANOZK in JSON proof bytes.
- Matching the NANOZK row in typed bytes requires removing `5,788` bytes.
- That is a `45.6179%` typed reduction from the current selected verifier target.
- Matching the NANOZK row in JSON bytes requires removing `27,966` bytes, an
  `80.2099%` JSON reduction.

The compact outer statement proof remains interesting:

- `1,792` local typed bytes.
- `0.259710x` NANOZK's paper row in typed bytes.
- `0.141236x` the selected verifier target in typed bytes.

But it is not the same object class. It binds host-verified selected slice
statements; it does not execute the selected inner Stwo verifier checks.

## Interpretation

This makes the next research attack concrete.

The "small object" path is useful as statement binding, but it cannot carry a
NANOZK proof-size claim. The comparable target is the selected inner
verifier-execution surface: `12,688` typed bytes over the two pinned Stwo proof
envelopes. To turn this into a serious comparison, the next result must either:

1. Execute the selected verifier checks inside a native Stwo outer AIR; or
2. Reprove the selected RMSNorm and projection-bridge relations as native
   components with the same source and statement commitments, replacing the
   inner-proof target instead of verifying it.

The second path is currently the more promising STARK-native research route. It
attacks the `12,688` typed-byte target directly instead of wrapping it.

## Attack Paths

| Path | Classification | Status |
| --- | --- | --- |
| `component_native_reprove` | `PROMISING_STARK_NATIVE_ROUTE` | Potentially comparable after same statement binding and native constraints |
| `native_stwo_verifier_execution_air` | `STRICT_VERIFIER_EXECUTION_ROUTE` | Comparable after native outer AIR executes selected inner verifier checks |
| `semantic_digest_binding` | `NOT_NANOZK_COMPARABLE_BUT_USEFUL_FOR_ARCHITECTURE` | Keep as binding primitive, not a block-proof comparison |
| `external_receipt_controls` | `CONTROL_NOT_NATIVE_STARK` | Useful calibration, not the core STARK-native thesis |

## First Blocker

`the compact outer statement proof is small, but the comparable object class is
the selected inner verifier-execution target at 12,688 local typed bytes, and
the repo still lacks a native Stwo AIR or component-native reprove that
replaces that target`

## Non-Claims

- Not a NANOZK proof-size win.
- Not a matched NANOZK benchmark.
- Not native verifier execution of the selected inner Stwo proofs.
- Not a native d128 transformer-block proof.
- Not recursion or proof-carrying data.
- Not upstream Stwo proof serialization.
- Not timing evidence.
- Not full transformer inference.
- Not production-ready zkML.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.tsv`
- Gate:
  `scripts/zkai_native_d128_verifier_execution_compression_budget_gate.py`
- Tests:
  `scripts/tests/test_zkai_native_d128_verifier_execution_compression_budget_gate.py`

The gate rejects `18 / 18` source, metric, comparison, route-classification,
claim-boundary, validation-command, and payload-commitment mutations.

## Reproduce

```bash
python3 scripts/zkai_native_d128_two_slice_verifier_execution_target_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.tsv
python3 scripts/zkai_native_d128_compressed_outer_statement_binary_accounting_gate.py --write-json docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.tsv
python3 scripts/zkai_native_d128_verifier_execution_compression_budget_gate.py --write-json docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.tsv
python3 -m py_compile scripts/zkai_native_d128_verifier_execution_compression_budget_gate.py scripts/tests/test_zkai_native_d128_verifier_execution_compression_budget_gate.py
python3 -m unittest scripts.tests.test_zkai_native_d128_verifier_execution_compression_budget_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
