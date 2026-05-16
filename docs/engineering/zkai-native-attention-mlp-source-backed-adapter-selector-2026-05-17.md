# Source-backed compact adapter selector

Issue: [#637](https://github.com/omarespejel/provable-transformer-vm/issues/637)

## Result

`NARROW_CLAIM_SOURCE_BACKED_COMPACT_ADAPTER_SELECTOR_VERIFIES`

Follow-up: [#639](https://github.com/omarespejel/provable-transformer-vm/issues/639)

The native attention-plus-MLP single-proof route now has source-backed duplicate
and compact adapter modes. Both modes verify locally. The compact mode keeps the
verifier-recomputed 12-column adapter preprocessed trace, but proves only the 8
base witness columns needed for value binding:

- `primary_q8`
- `mix_q8`
- `numerator_q8`
- `output_q8`
- `floor_remainder_q8`
- three remainder bits

The compact AIR still checks those witness values against the preprocessed
source-derived columns, and still enforces numerator, quotient/remainder, and
boolean bit constraints.

## Numbers

| Route | Adapter base cells | JSON proof bytes | Local typed bytes |
|---|---:|---:|---:|
| Source-backed duplicate selector | `1,536` | `124,585` | `43,228` |
| Source-backed compact selector | `1,024` | `116,091` | `40,812` |
| Current two-proof frontier | n/a | `116,258` | `40,700` |

Compact saves `2,416` typed bytes and `8,494` JSON proof bytes versus the
matching source-backed duplicate selector.

Compact is still `112` typed bytes above the current two-proof frontier, so this
is not a typed proof-size frontier win. It is a real mechanism win and a useful
near-miss.

The typed saving decomposes as:

| Group | Saving bytes |
|---|---:|
| OODS samples | `64` |
| Query values | `48` |
| FRI samples | `64` |
| FRI decommitments | `1,728` |
| Trace decommitments | `512` |
| Fixed overhead | `0` |

Only `112` bytes are direct opened-value savings. The remaining `2,304` bytes
are path-sensitive FRI/Merkle/query-position savings, so the promoted claim must
stay narrow.

## Claim Boundary

This PR shows:

- source-backed duplicate and compact adapter modes exist in the Rust backend;
- both variants produce real verifying Stwo proof artifacts;
- compact proves fewer adapter base cells while preserving value binding;
- compact is smaller than the matching source-backed duplicate selector.

This PR does not show:

- a transcript-stable compact-adapter frontier win;
- a typed proof-size win over the current two-proof frontier;
- a NANOZK proof-size win;
- a matched external zkML benchmark;
- timing evidence;
- a full transformer block proof;
- production readiness.

## Evidence

- `docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.input.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.input.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-binary-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-2026-05.tsv`

## Reproduction

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- build-input-duplicate-selector docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- build-input-compact docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- prove docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- prove docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- verify docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- verify docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-native-attention-mlp-source-backed-duplicate-adapter-2026-05.envelope.json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-compact-adapter-2026-05.envelope.json > docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-binary-accounting-2026-05.json
python3 scripts/zkai_native_attention_mlp_source_backed_adapter_selector_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-source-backed-adapter-selector-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_source_backed_adapter_selector_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend native_attention_mlp_single_proof --lib
```
