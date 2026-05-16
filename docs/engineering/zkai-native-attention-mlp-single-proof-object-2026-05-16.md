# zkAI Native Attention+MLP Single-Proof Object - 2026-05-16

## Result

This PR turns the route budget into a real native Stwo proof-object probe.

The checked result is a narrow GO:

- one native Stwo proof object verifies locally;
- it contains the d8 fused attention + Softmax-table LogUp surface and the
  attention-derived d128 RMSNorm-MLP fused surface;
- local typed proof bytes: `40,668`;
- previous two-proof frontier: `40,700` typed bytes;
- typed saving versus that frontier: `32` bytes;
- typed ratio: `0.999214x`;
- JSON proof bytes: `115,924`;
- previous two-proof JSON proof bytes: `116,258`;
- JSON saving: `334` bytes;
- JSON ratio: `0.997127x`;
- explicit PCS lifting log size: `19`.

This is the first checked proof object that puts the attention LogUp surface
and the six d128 MLP-side components under one Stwo proof. It barely beats the
two-proof target, so the honest claim is architectural feasibility with a very
small byte win, not a compression breakthrough yet.

## Important Constraint

The route cannot use the default publication-v1 PCS profile unchanged.

The combined proof has a large MLP base tree and a much smaller attention
interaction tree. Stwo's default `lifting_log_size: None` assumes the largest
domains are equal across trees, except possibly for the preprocessed tree. That
assumption caused an invalid decommitment path for the small interaction tree.

The fix is to pin an explicit route-specific lifting log size:

- `pcs_lifting_log_size = 19`
- PCS profile: `publication_v1_with_explicit_lifting_log_size`

This is evidence, not just plumbing: the cost of making heterogeneous
attention/MLP trees live in one proof object is visible in the proof bytes.

## Interpretation

The result is interesting but not enough.

What it proves:

- attention arithmetic + Softmax-table membership and the d128 MLP surface can
  share one Stwo proof object;
- the proof verifies and its commitments are recomputed from source rows;
- the route is below the previous two-proof typed target by `32` bytes.

What it does not prove:

- it does not prove the attention-output-to-d128-input adapter inside AIR;
- it does not prove a full transformer block;
- it is not NANOZK-comparable;
- it is not a proof-size win against NANOZK's reported `6,900` byte d128 row.

Distance to NANOZK remains large:

- single-proof typed bytes: `40,668`;
- NANOZK paper-reported d128 block row: `6,900` bytes;
- gap: `33,768` typed bytes;
- reduction still needed from this object: `83.0333%`.

## Next Breakthrough Gate

The next useful experiments are:

1. Prove the attention-output-to-d128-input adapter as native AIR, or record a
   precise NO-GO.
2. Reduce the explicit-lifting cost from heterogeneous tree sizes.
3. Split or reorder components only if it lowers typed bytes while preserving a
   single proof object and verifier binding.
4. Compare the resulting native object against the two-proof frontier and only
   then revisit external comparison.

## Evidence

- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.input.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.tsv`
- `src/stwo_backend/native_attention_mlp_single_proof.rs`
- `src/bin/zkai_native_attention_mlp_single_proof.rs`
- `scripts/zkai_native_attention_mlp_single_proof_gate.py`
- `scripts/tests/test_zkai_native_attention_mlp_single_proof_gate.py`

## Validation

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- build-input docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- prove docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- verify docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json
python3 scripts/zkai_native_attention_mlp_single_proof_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_single_proof_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend native_attention_mlp_single_proof --lib
git diff --check
just gate-fast
just gate
```

The proof-pinned `validation_commands` list intentionally excludes optional
local syntax checks. During review, `python3 -m py_compile
scripts/zkai_native_attention_mlp_single_proof_gate.py
scripts/tests/test_zkai_native_attention_mlp_single_proof_gate.py` was also run
as an extra local check, but it is not part of the statement-bound command list.
