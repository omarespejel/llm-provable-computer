# Matched d64/d128 Evidence Table

Date: 2026-05-14

Issue: #570

## Decision

`GO_MATCHED_D64_D128_EVIDENCE_TABLE_NO_GO_NATIVE_PROOF_SIZE_WIN`

This gate builds a single checked table across the current d64 and d128
evidence so that proof rows, source artifacts, compressed handles, external
SNARK receipts, package bytes, paper-reported competitor rows, and missing
native proof objects are not conflated.

The result is a GO for evidence organization and a NO-GO for matched proof-size
claims.

## Why This Matters

The tempting comparison remains:

> The current d128 verifier-facing package without VK is `4,752` bytes, or
> `0.688696x` NANOZK's paper-reported `6.9 KB` transformer block row.

The allowed interpretation is narrower:

> The `4,752` byte row is a verifier-facing package over a compressed
> statement-chain handle and an external Groth16 statement receipt. It is not a
> native Stwo d128 block proof object.

This distinction matters because the research thesis is STARK-native proof
architecture. Groth16 is useful here as an external statement-binding/package
accounting layer, but it is not the STARK-native result. The Stwo-native lane
is represented by the d64 and d128 receipt-chain rows; proof-size comparison
requires the still-missing native d128 block proof object.

## Evidence

- JSON: `docs/engineering/evidence/zkai-matched-d64-d128-evidence-table-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-matched-d64-d128-evidence-table-2026-05.tsv`
- Gate: `scripts/zkai_matched_d64_d128_evidence_table_gate.py`
- Tests: `scripts/tests/test_zkai_matched_d64_d128_evidence_table_gate.py`

Source artifacts:

- `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d64-external-recursion-adapter-2026-05.json`
- `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json`
- `docs/engineering/evidence/zkai-one-transformer-block-surface-2026-05.json`
- `docs/engineering/evidence/zkai-one-block-executable-package-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-d128-native-block-gap-accounting-2026-05.json`
- `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`

## Checked Rows

| Row | Object class | Value | Boundary |
|---|---|---:|---|
| d64 Stwo receipt chain | `stwo_native_receipt_chain_rows` | `49,600` rows | row-count scaling only |
| d128 Stwo receipt chain | `stwo_native_receipt_chain_rows` | `197,504` rows, `3.981935x` d64 | row-count scaling only |
| d128 attention statement chain | `source_statement_chain_rows` | `199,553` rows, `1.010374x` d128 | statement-binding shape |
| d128 source statement chain | `source_statement_chain_artifact_bytes` | `14,624` bytes | source artifact, not proof |
| d128 compressed chain | `compressed_statement_chain_artifact_bytes` | `2,559` bytes | transcript handle, not proof |
| d64 Groth16 receipt proof | `external_snark_statement_receipt_proof_bytes` | `806` bytes | external SNARK, not Stwo recursion |
| d128 Groth16 receipt proof | `external_snark_statement_receipt_proof_bytes` | `807` bytes | external SNARK, not native d128 proof |
| d128 package without VK | `verifier_facing_package_without_vk_bytes` | `4,752` bytes, `0.688696x` NANOZK | compact package signal only |
| d128 package with VK | `verifier_facing_package_with_vk_bytes` | `10,608` bytes, `1.537391x` NANOZK | setup-counted package only |
| NANOZK block proof | `paper_reported_external_proof_bytes` | `6,900` decimal bytes | paper-reported external context |
| native d128 block proof object | `missing_native_stark_block_proof_bytes` | missing | required before matched benchmark |

## Interpretation

This table strengthens the research process by making the current comparison
surface auditable:

- Stwo-native evidence exists for d64 and d128 receipt-chain row scaling.
- External Groth16 receipts exist for statement binding and package accounting.
- The compact `4,752` byte row is interesting, but it is package accounting.
- NANOZK remains paper-reported external context, not locally reproduced.
- The missing object is still a native or matched d128 block proof object.

That means the next breakthrough gate is unchanged: build the native d128 block
proof object or prove that the compact package signal does not survive native
aggregation.

## Non-Claims

- Not a native d128 transformer-block proof.
- Not a NANOZK proof-size win.
- Not a matched benchmark against NANOZK, Jolt Atlas, EZKL, DeepProve-1, RISC
  Zero, or Obelyzk.
- Not verifier-time or prover-time evidence.
- Not recursive aggregation or proof-carrying data.
- Not verification of Stwo slice proofs inside Groth16.
- Not full transformer inference.
- Not exact real-valued Softmax, LayerNorm, or GELU.
- Not production-ready.

## Validation

The full `just gate` path is included for local release validation; if the
dependency cache or network blocks it, record the exact blocker instead of
claiming a pass.

```bash
python3 scripts/zkai_matched_d64_d128_evidence_table_gate.py --write-json docs/engineering/evidence/zkai-matched-d64-d128-evidence-table-2026-05.json --write-tsv docs/engineering/evidence/zkai-matched-d64-d128-evidence-table-2026-05.tsv
python3 -m py_compile scripts/zkai_matched_d64_d128_evidence_table_gate.py scripts/tests/test_zkai_matched_d64_d128_evidence_table_gate.py
python3 -m unittest scripts.tests.test_zkai_matched_d64_d128_evidence_table_gate
git diff --check
just gate-fast
just gate
```
