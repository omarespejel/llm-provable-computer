# zkAI Attention/KV Stwo Binary Typed Proof Accounting - 2026-05-12

## Question

Can the d32 matched source, LogUp sidecar, and fused Stwo proof envelopes be
accounted through a deterministic repo-owned binary/typed format without
claiming upstream Stwo proof serialization?

## Decision

`GO_REPO_OWNED_LOCAL_BINARY_TYPED_ACCOUNTING_FOR_D32_MATCHED_ENVELOPES`

GO for a bounded first slice of stable local binary typed accounting over the
existing d32 matched proof envelopes:

- source arithmetic envelope;
- LogUp sidecar envelope;
- fused attention-arithmetic-plus-LogUp envelope.

The accounting format is a repo-owned canonical local record stream over typed
`StarkProof` fields. Each record pins a component path, scalar kind, item count,
item byte width, and total bytes. The Rust CLI commits to that record stream
with SHA-256 and checks that the component sum exactly matches Stwo's typed
`size_estimate()` and grouped `size_breakdown_estimate()` reconstruction.

This is not an upstream Stwo proof wire format.

## Artifacts

- Rust CLI: `src/bin/zkai_stwo_proof_binary_accounting.rs`
- Gate script: `scripts/zkai_attention_kv_stwo_binary_typed_proof_accounting_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_stwo_binary_typed_proof_accounting_gate.py`
- JSON evidence: `docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json`
- TSV evidence: `docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.tsv`

Evidence commitment:

`blake2b-256:bdff60cab41a2f060d9fc9a7777eed3d512c4652f5a961df81bc25f3557412be`

## Checked Metrics

| Role | JSON proof bytes | Local typed bytes | JSON minus local typed bytes |
|---|---:|---:|---:|
| Source arithmetic | `101,120` | `48,624` | `52,496` |
| LogUp sidecar | `15,562` | `4,376` | `11,186` |
| Source + sidecar | `116,682` | `53,000` | `63,682` |
| Fused | `107,261` | `50,380` | `56,881` |
| Fused saving | `9,421` | `2,620` | `6,801` |

Record-stream commitments:

| Role | SHA-256 |
|---|---|
| Source arithmetic | `da702acb52e9158eeaa5762859413d1981507397a0733b25f8db22d4dbac0c0c` |
| LogUp sidecar | `5fe39b76460bf0b1f64ded9f42033b6316bb2297bae9a15fe10a30cce1ec1f0e` |
| Fused | `d89c7f36588cb64db8fa2df25277a6c0f0b77c1a1c4e380a96bf118677f74f1a` |

## Safety Checks

The Rust CLI fails closed on:

- missing `--evidence-dir`;
- input paths outside the canonical evidence directory;
- symlink inputs;
- non-regular files;
- envelope JSON over `16 MiB`;
- proof byte arrays over `2 MiB`;
- non-`stwo` proof backends;
- missing required proof backend or statement versions;
- malformed proof byte arrays;
- proof payloads that are not a JSON object with exactly one `stark_proof`;
- local typed component sums that do not match Stwo `size_estimate()`;
- local grouped reconstruction that does not match Stwo
  `size_breakdown_estimate()`.

The Python gate freezes the schema, accounting domain, format version, d32
envelope metadata, non-claims, aggregate metrics, CLI summary commitment, and
payload commitment. It rejects `20 / 20` schema, domain/version, metric,
commitment, ordering, and overclaim mutations.

## Claim Boundary

This gate is:

- local binary typed proof-accounting evidence for d32 matched envelopes;
- deterministic accounting over typed Stwo proof fields;
- a repo-owned canonical local accounting format;
- proof-byte accounting only.

This gate is not:

- upstream Stwo proof serialization;
- binary PCS/FRI wire-format accounting;
- backend-internal source arithmetic versus lookup attribution;
- timing evidence;
- a public benchmark;
- exact real-valued Softmax;
- full inference;
- recursion or PCD.

## Validation

Regenerate the evidence:

```bash
python3 scripts/zkai_attention_kv_stwo_binary_typed_proof_accounting_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.tsv
```

Run the focused tests:

```bash
python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_binary_typed_proof_accounting_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting
```

Check whitespace before committing:

```bash
git diff --check
```
