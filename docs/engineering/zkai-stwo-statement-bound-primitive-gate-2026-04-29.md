# zkAI Stwo statement-bound primitive gate - 2026-04-29

## Question

Test whether the statement-binding receipt result from the EZKL and snarkjs
external adapters also applies to this repo's native Stwo transformer-shaped
primitive.

The target is intentionally small:

- program: `programs/linear_block_v4_with_lookup.tvm`,
- proof backend: `stwo`,
- proof backend version: `stwo-phase10-linear-block-v4-with-lookup`,
- raw verifier: `cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- verify-stark <proof> --reexecute`,
- statement wrapper: `zkai-statement-receipt-v1` implemented by
  `scripts/zkai_stwo_statement_envelope_benchmark.py`.

This is a statement-binding gate, not a throughput benchmark, not a full
transformer-inference result, and not a Stwo security audit.

## Artifacts

The checked proof and metadata live at:

- `docs/engineering/evidence/zkai-stwo-statement-envelope-2026-04/linear_block_v4_with_lookup.proof.json.gz`
- `docs/engineering/evidence/zkai-stwo-statement-envelope-2026-04/metadata.json`

The checked benchmark outputs are:

- `docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.json`
- `docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.tsv`

## Result

| Adapter | Baseline | Mutations rejected | Decision |
| --- | --- | ---: | --- |
| `stwo-proof-only` | accepted | 1 / 14 | NO-GO for metadata-only statement relabeling |
| `stwo-statement-envelope` | accepted | 14 / 14 | GO for native Stwo proof-backed statement receipt |

The raw Stwo verifier rejects the proof-public-claim mutation, as expected. It
accepts metadata-only relabeling because the changed labels are outside the raw
proof object's acceptance path.

The statement receipt first binds the accepted proof to model/primitive ID,
program and model artifact commitment, input commitment, output commitment,
configuration commitment, public-instance commitment, proof commitment,
transparent setup commitment, verifier/AIR identity commitment, evidence
manifest commitment, backend version, verifier domain, and the checked proof
artifact path/hash recorded in `metadata.json`. Under that wrapper, all 14
checked mutations are rejected.

## Interpretation

This closes the minimum GO criterion for issue `#310`:

> The statement-binding receipt pattern that held for EZKL and snarkjs also
> applies to this repo's Stwo-native transformer-shaped primitive.

The important result is not that Stwo is weak. The raw Stwo verifier verifies the
Stwo proof. The result is that verifiable-AI integrations need an additional
statement receipt if they want semantic relabeling rejection to be a verifier
property.

In short:

> A proof is not a statement. A zkAI receipt binds the proof to the semantic
> claim that users or settlement layers actually rely on.

## Reproduction

Generate and compress the baseline Stwo proof deterministically:

```bash
cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  prove-stark programs/linear_block_v4_with_lookup.tvm \
  -o /tmp/linear_block_v4_with_lookup.proof.json \
  --max-steps 256
gzip -n -9 -c /tmp/linear_block_v4_with_lookup.proof.json \
  > docs/engineering/evidence/zkai-stwo-statement-envelope-2026-04/linear_block_v4_with_lookup.proof.json.gz
```

Verify the checked proof through the statement benchmark harness:

```bash
python3.12 scripts/zkai_stwo_statement_envelope_benchmark.py --json
```

Regenerate the benchmark evidence:

```bash
export ZKAI_STWO_BENCHMARK_COMMAND_JSON='["env","ZKAI_STWO_BENCHMARK_GIT_COMMIT=d8ef5ffd6806c51985b5be3f579d38cf7cb04bb9","python3.12","scripts/zkai_stwo_statement_envelope_benchmark.py","--write-json","docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.json","--write-tsv","docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.tsv"]'
ZKAI_STWO_BENCHMARK_GIT_COMMIT=d8ef5ffd6806c51985b5be3f579d38cf7cb04bb9 \
  python3.12 scripts/zkai_stwo_statement_envelope_benchmark.py \
  --write-json docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.json \
  --write-tsv docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.tsv
```

Run focused tests:

```bash
python3.12 -m unittest scripts.tests.test_zkai_stwo_statement_envelope_benchmark
```

## Non-claims

- This is not a performance benchmark.
- This is not full transformer inference.
- This is not a backend-independence result.
- This is not a Stwo security audit.
- This does not claim raw Stwo proof verification should bind application labels
  that are not part of the proof object.
- This does not replace circuit-level public inputs; it binds receipt-level
  semantics to the proof and public claim that the verifier already accepts.

## Follow-up

The next useful step is to move from this bounded primitive to either:

1. a Stwo-native statement-bound block with more transformer structure and the
   same receipt discipline, or
2. an agent/action receipt that consumes this `zkAIStatementReceiptV1` as a
   proved model subreceipt.

Do not use this gate to claim end-to-end verifiable intelligence. It is one
verified statement-binding building block.
