# STARK-Native Transformer Proof Claim Pack - 2026-05

## Thesis

The current evidence supports a bounded paper-facing thesis:

> STARK-native transformer proofs can fuse attention arithmetic and
> lookup-heavy bounded Softmax-table membership into one proof object, sharing
> commitment and opening plumbing that would otherwise be paid by separate
> source-arithmetic and lookup-sidecar proofs.

This is a proof-architecture claim over checked bounded integer attention
fixtures. It is not a claim about exact real-valued Softmax, full model
inference, public benchmark performance, production readiness, recursion, PCD,
or Starknet deployment.

## Defensible Claims

1. Native Stwo evidence now checks source arithmetic, LogUp sidecar, and fused
   proof objects for a controlled Softmax-table route family.
2. The checked route matrix has eleven matched rows across width, head-count,
   sequence-length, and combined-axis profiles, with fused proof bytes smaller
   than source-plus-sidecar proof bytes in each row.
3. The section-delta and typed-size evidence agree on the mechanism: the fused
   object mostly avoids duplicated opening/decommitment structure.
4. The local binary typed accounting slice gives deterministic repo-owned
   accounting over typed Stwo proof fields, while explicitly keeping upstream
   stable proof serialization as a non-claim.
5. The model-faithful bridge checks that the existing d8 bounded Softmax-table
   fixture trace is exactly the trace emitted by a model-facing quantized
   attention policy at the trace boundary.

## Evidence Handles

- Route matrix:
  `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json`
- Controlled component grid:
  `docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json`
- Section delta:
  `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json`
- Typed size estimate:
  `docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.json`
- Binary typed accounting:
  `docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json`
- Median timing discipline:
  `docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.json`
- Seq32 fused route:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.json`
- Model-faithful bridge:
  `docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.json`
- Machine-readable claim pack:
  `docs/paper/evidence/stark-native-transformer-claim-pack-2026-05.json`

## Quantitative Core

The route matrix records eleven checked matched profiles. Across those rows,
the fused proof bytes total `736,727` versus `930,824` bytes for the matched
source-plus-sidecar controls, a `194,097` byte aggregate saving. Matched fused
ratios range from `0.676723` to `0.919259`.

The controlled component grid records ten checked fine-grained typed-component
profiles. The source-plus-sidecar typed estimate totals `285,584` bytes and the
fused typed estimate totals `234,296` bytes, a `51,288` byte (`17.9590%`)
aggregate saving. Per-profile typed saving ranges from `9.1035%` to `27.7371%`.

The section-delta evidence attributes `92.7722%` of the serialized proof-byte
saving to the opening bucket, dominated by FRI proof and decommitment material.
The typed-size evidence similarly shows decommitment-dominated savings, with
FRI plus trace decommitments accounting for `36,896` of `42,492` typed-estimate
saved bytes in the checked nine-profile slice.

The seq32 extension is the strongest sequence-axis row in the current route
matrix: `d8`, two heads, `32` steps per head, `1,184` lookup claims, `2,048`
trace rows, `66,327` fused proof bytes, and `98,012` source-plus-sidecar proof
bytes, for a `0.676723` fused ratio.

## GO / NO-GO Posture

GO:

- Use the claim that bounded attention arithmetic and Softmax-table membership
  can be fused into one native Stwo proof object.
- Use matched proof-byte, typed-size, section-delta, and component-grid evidence
  as proof-architecture support.
- Say the observed savings are dominated by shared opening/decommitment
  plumbing.
- Say the d8 fixture now has a checked model-facing quantized-attention bridge
  at the trace boundary.

NO-GO:

- Do not describe this as exact real-valued Softmax.
- Do not describe this as full inference or a complete transformer runtime.
- Do not describe this as a public benchmark or a verifier-time win.
- Do not describe this as production-ready or Starknet deployed.
- Do not describe the local accounting stream as upstream Stwo proof
  serialization.
- Do not claim backend-internal source-vs-lookup byte attribution.

## Blockers

1. Stable verifier-facing binary Stwo proof serialization is not exposed on this
   repo surface.
2. Backend-internal attribution between source arithmetic and lookup columns is
   still missing.
3. The local median-of-5 timing gate is discipline only; it does not support a
   fused verifier-time win claim.
4. The model-faithful bridge covers the checked d8 fixture trace only.
5. Starknet verifier packaging, calldata accounting, deployment, release gates,
   and adversarial integration hardening remain incomplete.
6. No tokenizer/model-weight import, full runtime, accuracy, or perplexity gate
   is bound.

## Validation

```bash
just gate-fast

python3 scripts/zkai_paper_claim_pack_gate.py \
  --write-json docs/paper/evidence/stark-native-transformer-claim-pack-2026-05.json

python3 -m unittest scripts.tests.test_zkai_paper_claim_pack_gate

git diff --check

just gate
```
