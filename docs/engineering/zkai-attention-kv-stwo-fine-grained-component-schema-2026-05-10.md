# zkAI Attention/KV Stwo Fine-Grained Component Schema - 2026-05-10

Issue: `#534`

## Question

Issue `#476` showed that the fused Softmax-table route still saves `42,492`
bytes against matched source-plus-sidecar controls when measured through Stwo's
own typed proof-size estimator. That route still used Stwo's grouped typed
breakdown.

This gate asks the next stricter engineering question: can we split the typed
estimate into smaller public Stwo proof components without claiming stable
verifier-facing binary proof bytes?

## Decision

`GO_FINE_GRAINED_TYPED_COMPONENT_SCHEMA_WITH_STABLE_BINARY_SERIALIZER_NO_GO`

GO for a fine-grained typed component schema obtained by traversing public
Stwo `2.2.0` `StarkProof` fields and applying Rust `size_of` estimates for the
field/hash/config objects.

NO-GO for stable canonical binary proof serialization. This is not a claim about
the exact verifier-facing binary proof artifact because this repository still
has no stable Stwo binary serializer exposed for these proof objects.

## Artifacts

- JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.tsv`
- Rust CLI: `src/bin/zkai_stwo_proof_component_schema.rs`
- Gate: `scripts/zkai_attention_kv_stwo_fine_grained_component_schema_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_stwo_fine_grained_component_schema_gate.py`

Fine-grained component-schema commitment:

`blake2b-256:bf6acc8377fc36eb5151c4dcf6428d8bd7ffeba9b5507fd8c1db0145d8e5e127`

## Exact Reproduction Surface

Backend/accounting source:

- Stwo crate: `stwo 2.2.0`
- proof object: `StarkProof<Blake2sM31MerkleHasher>`
- accounting source:
  `public_stwo_2_2_0_stark_proof_field_traversal_and_mem_size_estimates`
- proof payload kind: UTF-8 JSON object with one `stark_proof` field
- stable binary serializer status:
  `NO_GO_STABLE_BINARY_STWO_PROOF_SERIALIZER_NOT_EXPOSED`
- component schema status:
  `GO_FINE_GRAINED_TYPED_COMPONENT_SCHEMA_STABLE_BINARY_SERIALIZER_NO_GO`

Size constants checked by the gate:

| Object | Bytes |
|---|---:|
| `BaseField` | 4 |
| `SecureField` | 16 |
| `Blake2sHash` | 32 |
| proof-of-work scalar | 8 |
| `PcsConfig` | 40 |

The gate checks the same nine matched profiles as issue `#476`, with three roles
per profile: source arithmetic proof, LogUp sidecar proof, and fused proof.

## Aggregate Read

Across the same nine matched profiles:

| Role | JSON proof bytes | Stwo typed estimate bytes | JSON / typed |
|---|---:|---:|---:|
| Source arithmetic proofs | 528,303 | 201,256 | 2.625030x |
| LogUp sidecar proofs | 187,827 | 52,616 | 3.569770x |
| Source + sidecar total | 716,130 | 253,872 | 2.820831x |
| Fused proofs | 563,139 | 211,380 | 2.664107x |
| Fused saving | 152,991 | 42,492 | - |

The fine-grained component schema preserves the issue `#476` headline: fusion
still saves `42,492` typed-estimate bytes (`16.7376%`) against the matched
source-plus-sidecar typed estimate.

Where the `42,492` typed-estimate saved bytes appear:

| Fine-grained typed component | Saved bytes |
|---|---:|
| FRI decommitment Merkle paths | 17,312 |
| Trace decommitment Merkle paths | 16,448 |
| FRI layer witnesses | 2,752 |
| FRI commitments | 2,272 |
| Sampled opened values | 1,296 |
| Queried values | 972 |
| Trace commitments | 864 |
| Config bytes | 360 |
| FRI last-layer polynomial | 144 |
| Proof-of-work scalar | 72 |

## Interpretation

The useful engineering result is narrower and stronger than the previous grouped
read: the fused proof saves typed-estimate bytes mostly by removing repeated
Merkle-path material in the separate source and sidecar proofs. FRI Merkle paths
and trace Merkle paths account for `33,760` of the `42,492` saved bytes.

This supports the current STARK-engineering direction: when source arithmetic
and table-membership checks are fused into one proof, they share commitment and
opening structure instead of paying a second proof's decommitment surface.

## Claim Boundary

This gate is:

- fine-grained typed Stwo component-schema accounting;
- checked over matched source, sidecar, and fused proof objects;
- a reconstruction of Stwo's grouped typed breakdown from public fields;
- an engineering proof-size result, not timing;
- a GO for public-field component attribution;
- a NO-GO for stable canonical binary serialization.

This gate is not:

- stable verifier-facing binary proof bytes;
- backend-internal source arithmetic versus LogUp lookup column attribution;
- exact public benchmark proof bytes;
- timing evidence;
- exact real-valued Softmax;
- full inference;
- recursion or PCD.

Open component questions:

1. Stable canonical binary Stwo proof serialization.
2. Verifier-facing binary byte encoding for every component.
3. Backend-internal source arithmetic versus LogUp lookup column attribution.

## Validation

Regenerate the fine-grained component evidence:

```bash
python3 scripts/zkai_attention_kv_stwo_fine_grained_component_schema_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05.tsv
```

Run the focused tests:

```bash
python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_fine_grained_component_schema_gate
```

Run the Rust CLI directly:

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_stwo_proof_component_schema -- <envelope.json>...
```

Run the broader gate stack before merging:

```bash
just gate-fast
just gate
```

## Next Research Hooks

1. Add or request a stable Stwo binary proof serializer so this typed component
   schema can be compared against actual verifier-facing binary bytes.
2. Add backend-local component counters that label source arithmetic columns,
   lookup columns, and shared PCS/FRI material directly.
3. Use the Merkle-path-dominated saving to prioritize fused transformer routes
   where separate arithmetic and lookup proofs would duplicate opening work.
