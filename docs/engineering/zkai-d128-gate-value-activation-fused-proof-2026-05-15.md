# d128 Gate/Value + Activation Fused Proof

Date: 2026-05-15

## Decision

`GO_D128_GATE_VALUE_ACTIVATION_FUSED_TYPED_PROOF_SAVING`

The first adjacent-component d128 fusion probe is positive. A single native
Stwo proof over d128 gate/value projection plus activation/SwiGLU verifies and
is smaller than the two separate native proof objects under local typed
proof-field accounting.

## Checked Surface

- width: `128`
- gate/value rows: `131,072`
- activation/SwiGLU rows: `512`
- backend: native Stwo, publication-v1 PCS profile
- fused components: `gate_value_projection` and `activation_swiglu`
- mutation gate: `18 / 18` rejected

## Numbers

| Object | JSON proof bytes | Local typed proof bytes |
| --- | ---: | ---: |
| separate gate/value proof | `57,930` | `16,360` |
| separate activation/SwiGLU proof | `24,449` | `6,920` |
| separate total | `82,379` | `23,280` |
| fused gate/value + activation proof | `62,865` | `17,760` |

The fused proof saves:

- `19,514` JSON proof bytes, ratio `0.763119x`
- `5,520` local typed proof-field bytes, ratio `0.762887x`
- `23.7113%` of the separate typed proof-field bytes

## Where The Saving Comes From

| Group | Fused minus separate typed bytes |
| --- | ---: |
| fixed overhead | `-48` |
| FRI decommitments | `-2,560` |
| FRI samples | `-384` |
| OODS samples | `-128` |
| queried values | `-96` |
| trace decommitments | `-2,304` |

The important part is mechanism. The dense compact-preprocessed route failed on
gate/value alone because it increased FRI and Merkle decommitment bytes. This
route wins because two adjacent components share one proof object with one
preprocessed tree and one base tree, so the commitment/opening/decommitment
plumbing is paid once.

That is exactly the STARK-native architecture thesis this repo is trying to
test.

## Interpretation

This strengthens the breakthrough path, but it does not finish it.

The positive claim is:

> Adjacent d128 transformer relations can share native Stwo proof plumbing.
> For gate/value projection plus activation/SwiGLU, the fused proof removes
> `5,520` local typed bytes versus separate native proof objects.

The claim is still scoped. This is not a full d128 transformer-block proof and
not a NANOZK benchmark win. It is evidence that the right compression mechanism
for dense d128 work is fusion across adjacent relations, not direct dense-row
compact preprocessing.

## First Blocker

The fused proof covers only gate/value plus activation/SwiGLU. The next attack
must add down-projection or a lookup-heavy sidecar and check whether the saving
persists across a fuller block surface.

## Artifacts

- fused input:
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.input.json`
- fused envelope:
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json`
- activation envelope:
  `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json`
- binary accounting:
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-binary-accounting-2026-05.json`
- gate JSON:
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.json`
- gate TSV:
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.tsv`
- Rust module:
  `src/stwo_backend/d128_native_gate_value_activation_fused_proof.rs`
- CLIs:
  `src/bin/zkai_d128_activation_swiglu_proof.rs`,
  `src/bin/zkai_d128_gate_value_activation_fused_proof.rs`
- gate:
  `scripts/zkai_d128_gate_value_activation_fused_gate.py`
- tests:
  `scripts/tests/test_zkai_d128_gate_value_activation_fused_gate.py`

## Non-Claims

- Not a full d128 transformer-block proof.
- Not a NANOZK proof-size win.
- Not a matched external zkML benchmark.
- Not recursion or proof-carrying data.
- Not private parameter-opening proof.
- Not upstream Stwo proof serialization.
- Not timing evidence.
- Not full transformer inference.
- Not production-ready zkML.

## Validation

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- prove docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- verify docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- build-input docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- prove docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-d128-gate-value-activation-fused-binary-accounting-2026-05.json
python3 scripts/zkai_d128_gate_value_activation_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_gate_value_activation_fused_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_gate_value_activation_fused_proof --lib
git diff --check
just gate-fast
```
