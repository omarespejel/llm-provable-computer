# zkAI Stwo Fusion Mechanism Ablation - 2026-05-13

## Question

Is the observed source-plus-sidecar versus fused proof-size saving just a
serialized artifact accident, or does the checked evidence point to a concrete
STARK-native mechanism?

## Decision

GO for the bounded paper-architecture claim:

> The checked fused attention/Softmax-table route saves proof bytes primarily
> by sharing opening and decommitment plumbing that separate source-arithmetic
> and LogUp sidecar proofs duplicate.

This is still not backend-internal byte attribution. The current proof
envelopes expose proof-object sections and local typed accounting, not semantic
column labels or exact source-arithmetic versus lookup byte spans.

## Evidence

Machine-readable evidence:

- `docs/engineering/evidence/zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.tsv`

The gate cross-checks these existing inputs:

- `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json`

## Checked Result

- Route matrix: `11` matched profiles, `930,824` source-plus-sidecar JSON proof
  bytes, `736,727` fused JSON proof bytes, `194,097` bytes saved.
- Section delta: ten-profile JSON slice saves `184,676` bytes, with `92.7722%`
  of the saving in the opening bucket; the largest exposed section delta is
  `fri_proof` at `102,304` bytes.
- Typed-size estimate: nine-profile typed slice saves `42,492` bytes, with
  `36,896` bytes (`86.8305%`) from FRI plus trace decommitments.
- Controlled component grid: ten-profile typed grid saves `51,288` bytes, with
  `87.5370%` attributed to opening plumbing and `80.5491%` to FRI/trace Merkle
  path savings.
- d32 local binary accounting: fused local typed bytes are `50,380` versus
  `53,000` source-plus-sidecar bytes, a positive `2,620` byte local typed
  saving. This remains repo-owned accounting, not upstream Stwo wire format.

## Interpretation

The strongest current mechanism is not "fused proofs are smaller" in the
abstract. The stronger mechanism is:

1. source arithmetic and LogUp table membership each pay proof-system opening
   structure when proven separately;
2. the fused proof pays one shared opening/decommitment surface for the same
   bounded attention/table statement family;
3. independent JSON section, typed-size, controlled-grid, and d32 local typed
   accounting all point in the same direction;
4. the claim remains explicitly bounded to checked fixture families.

## Non-Claims

- Not backend-internal source arithmetic versus lookup byte attribution.
- Not upstream Stwo verifier-facing binary proof serialization.
- Not timing evidence or a public benchmark.
- Not exact real-valued Softmax.
- Not full inference.
- Not a `d64` or `d128` RMSNorm-SwiGLU transformer-block proof.
- Not production-ready.

## Validation

```bash
python3 scripts/zkai_attention_kv_stwo_fusion_mechanism_ablation_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_fusion_mechanism_ablation_gate

just gate-fast

git diff --check
```
