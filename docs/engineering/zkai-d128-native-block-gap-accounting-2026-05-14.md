# d128 Native Block Gap Accounting

Date: 2026-05-14

## Decision

`GO_D128_NATIVE_BLOCK_GAP_ACCOUNTING_NO_GO_MATCHED_LAYER_PROOF`

This gate records the exact gap between the current attention-derived d128
block surface and a real matched transformer-block proof claim.

The interesting signal is narrow:

> The attention-derived d128 route has an external verifier-facing package that
> is byte-smaller than the source-backed NANOZK block proof-size row, but the
> object classes are different.

So the result is a GO for prioritizing native aggregation work, and a NO-GO for
claiming a smaller proof than NANOZK.

## Evidence

- JSON: `docs/engineering/evidence/zkai-d128-native-block-gap-accounting-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-d128-native-block-gap-accounting-2026-05.tsv`
- Gate: `scripts/zkai_d128_native_block_gap_accounting_gate.py`
- Tests: `scripts/tests/test_zkai_d128_native_block_gap_accounting_gate.py`

Source artifacts:

- `docs/engineering/evidence/zkai-one-transformer-block-surface-2026-05.json`
- `docs/engineering/evidence/zkai-one-block-executable-package-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-may2026-competitor-metric-matrix.json`
- `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`

## Checked Numbers

| Surface | Value | Status |
|---|---:|---|
| NANOZK source-backed transformer block proof row | `6,900` decimal bytes | external context only |
| local attention-derived package without VK | `4,752` bytes, `0.688696x` NANOZK row | interesting package signal, not matched proof benchmark |
| local attention-derived package with VK | `10,608` bytes, `1.537391x` NANOZK row | self-contained package, not matched proof benchmark |
| source statement-chain artifact | `14,624` bytes, `2.119420x` NANOZK row | source artifact, not proof |
| compressed statement-chain artifact | `2,559` bytes, `0.370870x` NANOZK row | transcript handle, not proof |
| external receipt overhead without VK | `2,193` bytes | proof plus public signals |
| d128 receipt chain | `197,504` checked rows | six-slice receipt chain |
| attention-derived d128 statement chain | `199,553` rows | `2,049` extra rows, `1.010374x` d128 receipt chain |
| native d128 block proof object | missing | required before matched benchmark claims |

## Interpretation

This is useful because it turns a tempting comparison into a checked claim
boundary.

The tempting sentence is:

> `4,752` bytes is smaller than NANOZK's reported `6.9 KB` transformer block
> proof row.

The allowed sentence is:

> The current verifier-facing package is compact enough to justify pursuing
> native aggregation, but it is not a native or matched transformer-block proof
> object.

That matters for the paper path. It tells us the block route is no longer only
abstract architecture. There is a concrete byte-level target: if a future native
aggregation route can preserve the compact verifier-facing package shape while
actually proving the d128 block/slice verifiers in one object, then we would
have a serious comparison point. We do not have that yet.

## Current Blockers

- Native aggregated d128 transformer-block proof object is missing.
- Matched workload is missing: local attention-derived d128 package is not
  NANOZK's GPT-2-scale d768 block.
- Native verifier-time and prover-time evidence are missing.
- Recursion or proof-carrying aggregation over the six Stwo slice proofs is
  missing.
- Verification-key/setup accounting is still external and not production setup
  evidence.

## Non-Claims

- Not a native d128 transformer-block proof.
- Not a NANOZK proof-size win.
- Not a matched benchmark against NANOZK, Jolt Atlas, EZKL, DeepProve-1, RISC
  Zero, or Obelyzk.
- Not verifier-time or prover-time evidence.
- Not recursive aggregation or proof-carrying data.
- Not verification of the six Stwo slice proofs inside the external Groth16
  receipt.
- Not full transformer inference.
- Not exact real-valued Softmax, LayerNorm, or GELU.
- Not production-ready.

## Validation

```bash
python3 scripts/zkai_d128_native_block_gap_accounting_gate.py --write-json docs/engineering/evidence/zkai-d128-native-block-gap-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-native-block-gap-accounting-2026-05.tsv
python3 -m py_compile scripts/zkai_d128_native_block_gap_accounting_gate.py scripts/tests/test_zkai_d128_native_block_gap_accounting_gate.py
python3 -m unittest scripts.tests.test_zkai_d128_native_block_gap_accounting_gate
git diff --check
just gate-fast
just gate
```
