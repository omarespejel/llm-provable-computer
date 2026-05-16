# Attention-Derived d128 MLP Fusion Attribution

Date: 2026-05-16

## Result

The exact six-envelope attention-derived d128 RMSNorm-MLP fusion result is a
**GO** for attribution and a **NO-GO** for safe internal compression before a
new proof-object boundary.

Decision:

`NARROW_CLAIM_EXACT_DERIVED_MLP_FUSION_SAVING_IS_SHARED_OPENING_PLUMBING`

Result:

`NO_GO_SAFE_INTERNAL_COMPRESSION_BEFORE_NEW_ATTENTION_PLUS_MLP_OBJECT`

## Human Meaning

The MLP-side fused proof is not smaller because of a vague JSON artifact. The
checked typed accounting says the saving is mostly the thing we hoped STARKs
would share: verifier opening and decommitment plumbing.

The exact derived MLP-side surface is:

- fused proof: `22,576` local typed bytes
- six separate proof objects: `59,344` local typed bytes
- typed saving: `36,768` bytes
- typed ratio: `0.380426x`

The attribution is sharper:

- FRI decommitments save `20,512` typed bytes (`55.7876%` of the saving)
- trace decommitments save `12,768` typed bytes (`34.7258%`)
- FRI plus trace decommitments save `33,280` typed bytes (`90.5135%`)
- FRI decommitments plus trace decommitments plus FRI samples save `35,408`
  typed bytes (`96.3011%`)

That means the current result is structural. The biggest bucket is not safely
removable inside the same proof object, because dropping FRI decommitments would
drop verifier opening witness material. The honest next frontier is to share
that plumbing with a larger native proof object, especially attention plus
RMSNorm-MLP.

## Checked Group Attribution

| Group | Separate typed bytes | Fused typed bytes | Saved typed bytes | Share of total saving |
|---|---:|---:|---:|---:|
| FRI decommitments | `31,296` | `10,784` | `20,512` | `0.557876` |
| trace decommitments | `17,184` | `4,416` | `12,768` | `0.347258` |
| FRI samples | `2,848` | `720` | `2,128` | `0.057876` |
| OODS samples | `4,416` | `3,776` | `640` | `0.017406` |
| query values | `3,312` | `2,832` | `480` | `0.013055` |
| fixed overhead | `288` | `48` | `240` | `0.006527` |

## Compression Probe

The largest apparent target is FRI decommitments: `20,512` typed bytes. The gate
records this as:

`NO_GO_DROP_FRI_DECOMMITMENTS_WOULD_DROP_VERIFIER_OPENING_WITNESS`

That is not a failure of the fusion thesis. It narrows the claim: the saving is
already the shared proof-plumbing win. The next compression lever is not to
delete those bytes from the MLP proof; it is to make more transformer work share
the same opening/decommitment surface.

## Claim Boundary

This gate records:

- GO for exact typed attribution of the derived d128 MLP-side fusion saving.
- GO that the saving is dominated by shared FRI and trace decommitment groups.
- NO-GO for safe internal compression of the largest bucket without changing
  the proof-object class.
- NO-GO for claiming attention plus MLP in one native proof object.
- NO-GO for any NANOZK benchmark win.

## Correctness Boundary

The gate checks:

- accounting row set is exactly one fused row plus six separate rows
- proof backend version and statement version for all seven proof objects
- proof JSON bytes and local typed bytes for all seven proof objects
- grouped typed reconstruction for all seven proof objects
- exact six-envelope route-gate status
- fused/separate proof-byte and typed-byte metrics
- ranked group attribution
- compression-probe non-overclaim status
- mutation rejection for metric drift, group drift, role removal, evidence-path
  drift, non-claim removal, and compression-overclaim drift

The mutation gate rejects `19 / 19` cases.

## Non-Claims

- Not attention plus MLP in one native proof object.
- Not a new proof object.
- Not a smaller fused MLP proof.
- Not a NANOZK benchmark win.
- Not a matched external zkML benchmark.
- Not upstream Stwo serialization.
- Not timing evidence.
- Not recursion or proof-carrying data.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.tsv`

## Validation

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json
python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv
python3 scripts/zkai_attention_derived_d128_mlp_fusion_attribution_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.tsv
python3 -m py_compile scripts/zkai_attention_derived_d128_mlp_fusion_attribution_gate.py scripts/tests/test_zkai_attention_derived_d128_mlp_fusion_attribution_gate.py
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_mlp_fusion_attribution_gate
git diff --check
just gate-fast
```
