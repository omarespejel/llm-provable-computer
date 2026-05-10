# zkAI Attention/KV Stwo Typed Size Estimate - 2026-05-10

Issue: `#476`

## Question

The fused Softmax-table section-delta gate showed that fusion saves `152,991`
serialized JSON proof bytes against matched source-plus-sidecar proofs, with
`141,125` bytes in the opening bucket. That result was still JSON-section
accounting.

This gate asks the next stricter question: does the saving survive if we use
Stwo's typed proof-size estimate rather than JSON key lengths?

## Decision

`GO_STWO_TYPED_SIZE_ESTIMATE_BREAKDOWN_WITH_STABLE_BINARY_SERIALIZER_NO_GO`

GO for typed Stwo proof-size estimate accounting using
`StarkProof::size_estimate()` and `StarkProof::size_breakdown_estimate()` over
the matched source, sidecar, and fused proof objects.

NO-GO for stable canonical binary proof serialization and for fine-grained
binary attribution of every requested PCS/FRI component. Stwo exposes a typed
size estimate and a grouped typed breakdown, but this repository still does not
expose a stable binary serializer whose bytes are the verifier-facing proof
artifact, and the public typed breakdown does not split all commitment,
decommitment, FRI-witness, proof-of-work, and config bytes into separate
categories.

## Artifacts

- JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.tsv`
- Rust CLI: `src/bin/zkai_stwo_proof_size_estimate.rs`
- Gate: `scripts/zkai_attention_kv_stwo_typed_size_estimate_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_stwo_typed_size_estimate_gate.py`

Typed-size commitment:

`blake2b-256:fac45de863a66fedb8b0a569be8ab725dba98bd2cdd416a5c83ad83f7411ac46`

## Exact Reproduction Surface

Backend/accounting source:

- Stwo crate: `stwo 2.2.0`
- typed hook: `StarkProof::size_estimate()`
- grouped breakdown hook: `StarkProof::size_breakdown_estimate()`
- proof payload kind: UTF-8 JSON object with one `stark_proof` field
- stable binary serializer status:
  `NO_GO_STABLE_BINARY_STWO_PROOF_SERIALIZER_NOT_EXPOSED`
- fine-grained binary split status:
  `GO_GROUPED_STWO_TYPED_BREAKDOWN_FINE_GRAINED_BINARY_SPLITS_NO_GO`

The nine checked profiles are:

| Profile | Roles checked |
|---|---|
| `d8_single_head_seq8` | source, sidecar, fused |
| `d16_single_head_seq8` | source, sidecar, fused |
| `d8_two_head_seq8` | source, sidecar, fused |
| `d8_four_head_seq8` | source, sidecar, fused |
| `d8_eight_head_seq8` | source, sidecar, fused |
| `d8_sixteen_head_seq8` | source, sidecar, fused |
| `d8_two_head_seq16` | source, sidecar, fused |
| `d16_two_head_seq8` | source, sidecar, fused |
| `d16_two_head_seq16` | source, sidecar, fused |

The concrete envelope input paths are the `rows[].path` values in
`docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.json`.
The gate obtains those paths from
`scripts/zkai_attention_kv_fused_softmax_table_section_delta_gate.py` and then
binds every CLI-emitted row back to the expected path before assigning metrics
to a `(profile_id, role)` pair.

## Aggregate Read

Across the same nine matched profiles:

| Role | JSON proof bytes | Stwo typed estimate bytes | JSON / typed |
|---|---:|---:|---:|
| Source arithmetic proofs | 528,303 | 201,256 | 2.625030x |
| LogUp sidecar proofs | 187,827 | 52,616 | 3.569770x |
| Source + sidecar total | 716,130 | 253,872 | 2.820831x |
| Fused proofs | 563,139 | 211,380 | 2.664107x |
| Fused saving | 152,991 | 42,492 | - |

The typed saving is smaller than the JSON-section saving, as expected, but it
does not disappear. Fusion still saves `42,492` typed-estimate bytes
(`16.7376%`) against the matched source-plus-sidecar typed estimate.

Where the `42,492` typed-estimate saved bytes appear:

| Typed Stwo bucket | Saved bytes |
|---|---:|
| FRI decommitments | 19,584 |
| Trace decommitments | 17,312 |
| FRI samples | 2,896 |
| OODS samples | 1,296 |
| Query values | 972 |
| Fixed unclassified overhead | 432 |

Fine-grained categories that remain explicitly unexposed by this route:

- binary commitment bytes;
- binary sampled/opened value bytes;
- binary decommitment/Merkle path bytes;
- binary FRI witness bytes;
- binary FRI commitment bytes;
- proof-of-work bytes;
- config bytes.

## Interpretation

The earlier JSON-section result was not merely a JSON artifact. Stwo's own typed
estimate still says the fused proof pays less than the source-plus-sidecar pair.
The dominant typed saving is decommitment material: FRI decommitments plus trace
decommitments account for `36,896` of `42,492` saved typed-estimate bytes.

This is the precise STARK-engineering claim: fusion reduces repeated opening and
decommitment work even when measured through Stwo's typed proof-size estimator.

## Claim Boundary

This gate is:

- typed Stwo proof-size estimate accounting;
- grouped Stwo typed breakdown accounting;
- checked over the same nine matched source/sidecar/fused profiles as issue
  `#531`;
- an engineering proof-size result, not timing;
- a GO for Stwo typed estimate and typed breakdown;
- a NO-GO for stable canonical binary serialization.

This gate is not:

- stable verifier-facing binary proof bytes;
- fine-grained binary commitment, FRI witness, or FRI commitment attribution;
- backend-internal source arithmetic versus lookup column attribution;
- exact public benchmark proof bytes;
- timing evidence;
- exact real-valued Softmax;
- full inference;
- recursion or PCD.

## Validation

Regenerate the typed estimate evidence:

```bash
python3 scripts/zkai_attention_kv_stwo_typed_size_estimate_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.tsv
```

Run the focused tests:

```bash
python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_typed_size_estimate_gate
```

Run the Rust CLI directly:

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_stwo_proof_size_estimate -- <envelope.json>...
```

Run the broader gate stack before merging:

```bash
just gate-fast
just gate
```

## Next Research Hooks

1. Add or request a stable Stwo binary proof serializer so typed estimates can be
   compared against actual verifier-facing binary bytes.
2. Add backend labels for source arithmetic, LogUp lookup, and shared PCS/FRI
   material so typed estimates can become semantic source-vs-lookup
   attribution.
3. Use the decommitment-dominated typed saving to choose the next fused
   transformer shape: prioritize routes where separate source and lookup proofs
   would duplicate opening work.
