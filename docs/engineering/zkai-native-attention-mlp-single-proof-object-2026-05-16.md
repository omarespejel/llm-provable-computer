# zkAI Native Attention+MLP Single-Proof Object - 2026-05-16

## Result

This PR updates the route from a statement-bound adapter probe into a real
native Stwo proof object with the attention-to-d128 adapter proved inside the
same object.

The checked result is a correctness GO and a size NO-GO:

- one native Stwo proof object verifies locally;
- it contains the d8 fused attention + Softmax-table LogUp surface and the
  attention-derived d128 RMSNorm-MLP fused surface;
- it now also proves the 128-row attention-output-to-d128-input adapter as
  native AIR;
- proof backend version:
  `stwo-native-attention-mlp-single-proof-object-native-adapter-v1`;
- statement version:
  `zkai-native-attention-mlp-single-proof-object-native-adapter-statement-v1`;
- local typed proof bytes: `41,932`;
- previous two-proof frontier: `40,700` typed bytes;
- typed delta versus that frontier: `+1,232` bytes;
- typed ratio: `1.030270x`;
- JSON proof bytes: `119,790`;
- previous two-proof JSON proof bytes: `116,258`;
- JSON delta: `+3,532` bytes;
- JSON ratio: `1.030381x`;
- adapter rows: `128`;
- adapter trace cells: `1,536`;
- explicit PCS lifting log size: `19`.

This is the first checked proof object that puts the attention LogUp surface,
the native attention-to-d128 adapter, and the six d128 MLP-side components
under one Stwo proof. It does not beat the two-proof target anymore. That is
still progress: it closes the value-binding weakness that reviewers would
attack, and it makes the next compression target precise.

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
attention/adapter/MLP trees live in one proof object is visible in the proof
bytes.

The adapter values are intentionally mirrored into the base trace and the
preprocessed trace in this version. The base trace is the proved witness; the
preprocessed copy is the verifier-recomputed public projection used to bind that
witness to the source attention output and d128 RMSNorm input artifacts. Issue
`#631` tracks compressing this boundary without dropping that binding.

## Interpretation

The result is interesting but not enough.

What it proves:

- attention arithmetic + Softmax-table membership and the d128 MLP surface can
  share one Stwo proof object;
- the attention-to-d128 handoff is now value-checked by native adapter AIR;
- the proof verifies and its commitments are recomputed from source rows;
- the result is pinned to proof backend version
  `stwo-native-attention-mlp-single-proof-object-native-adapter-v1` and
  statement version
  `zkai-native-attention-mlp-single-proof-object-native-adapter-statement-v1`;
- the stricter route costs `1,232` typed bytes over the previous two-proof
  target.

What it does not prove:

- it does not prove a full transformer block;
- it is not NANOZK-comparable;
- it is not a proof-size win against NANOZK's reported `6,900` byte d128 row.

Distance to NANOZK remains large:

- single-proof typed bytes: `41,932`;
- NANOZK paper-reported d128 block row: `6,900` bytes;
- gap: `35,032` typed bytes;
- reduction still needed from this object: `83.5448%`.

## Next Breakthrough Gate

The next useful experiments are:

1. Compress the adapter AIR representation without weakening value binding.
2. Reduce query/opening value pressure from the added adapter columns.
3. Split or reorder components only if it lowers typed bytes while preserving a
   single proof object and verifier binding.
4. Compare the resulting native object against the two-proof frontier and only
   then revisit external comparison.

Follow-up issue: `#631` tracks the adapter-compression attack.

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
