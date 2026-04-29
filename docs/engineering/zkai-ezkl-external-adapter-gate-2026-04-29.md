# zkAI EZKL external-adapter gate - 2026-04-29

## Purpose

Test whether the zkAI relabeling benchmark can be moved beyond local verifier
implementations by using a real external zkML proof verifier.

The target is EZKL `23.0.5`, using its Python verifier over:

- `proof.json`
- `settings.json`
- `vk.key`
- KZG SRS from `https://kzg.ezkl.xyz/kzg17.srs`

This follows the EZKL verification model documented as proof verification with
`proof.json`, `vk.key`, `settings.json`, and SRS.

## Checked artifacts

Artifact directory:

`docs/engineering/evidence/zkai-ezkl-statement-envelope-2026-04/`

Checked files:

- `identity.onnx`
- `input.json`
- `settings.json`
- `vk.key`
- `proof.json`
- `metadata.json`

Generated benchmark evidence:

- `docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.json`
- `docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.tsv`

Generator commit recorded in evidence:

`703ac1f5a0f7919de4ae0d9539d3f7d9612b9fe9`

## Result

Two adapters were tested against the same baseline proof and the same mutation
set.

| Adapter | Baseline | Mutations rejected | Gate |
|---|---:|---:|---|
| `ezkl-proof-only` | accepted | 1 / 7 | NO-GO for statement-bound relabeling |
| `ezkl-statement-envelope` | accepted | 7 / 7 | GO for external proof-backed statement envelope |

The raw proof-only path rejects the mutated public instance, as it should, but
accepts metadata-only relabeling because those labels are outside the EZKL proof
acceptance path. This is not an EZKL bug and not an EZKL security finding. It is
the expected boundary between proof validity and application statement binding.

The statement-envelope path first checks the statement commitment, artifact
hashes, label policy, verifier domain, SRS hash, and public-instance digest, and
then delegates proof validity to EZKL. Under that adapter, all seven mutations
are rejected.

## Interpretation

This is the first useful external-adapter result for the zkAI relabeling line.

The important finding is not that EZKL is weak. EZKL verifies the circuit proof
it is given. The finding is that a zkAI system needs an explicit
statement-binding layer around external proof systems if it wants to reject
model/input/output/config relabeling as a verifier-level property.

That gives a clean decomposition:

- External zkML proof verifier: validates the mathematical proof.
- Statement envelope: binds the proof to model identity, input identity, output
  identity, config identity, artifact hashes, SRS identity, and verifier domain.
- Relabeling benchmark: tests whether changing user-facing claims without valid
  corresponding evidence is rejected.

## Reproduction

Environment used:

- Python `3.12.11`
- EZKL `23.0.5`
- ONNX `1.21.0`
- macOS arm64

Install into an isolated environment:

```bash
uv venv --python /opt/homebrew/bin/python3.12 /tmp/ptvm-ezkl-venv
uv pip install --python /tmp/ptvm-ezkl-venv/bin/python ezkl==23.0.5 onnx==1.21.0
```

Run the benchmark:

```bash
ZKAI_EZKL_BENCHMARK_GIT_COMMIT=703ac1f5a0f7919de4ae0d9539d3f7d9612b9fe9 \
ZKAI_EZKL_SRS_PATH=target/ezkl/kzg17.srs \
  /tmp/ptvm-ezkl-venv/bin/python scripts/zkai_ezkl_statement_envelope_benchmark.py \
  --write-json docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.json \
  --write-tsv docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.tsv
```

Focused tests:

```bash
python3.12 -m unittest scripts.tests.test_zkai_ezkl_statement_envelope_benchmark
```

## Non-claims

- This is not an EZKL security audit.
- This is not a system ranking.
- This is not a performance benchmark.
- The proof-only NO-GO is limited to metadata outside the raw EZKL acceptance
  path.
- The statement-envelope GO is an adapter result, not a claim that raw EZKL
  proves model/input/output labels by itself.

## Follow-up

The next useful extension is to repeat the same adapter shape against a second
external artifact with a different proof system or deployment surface. A useful
candidate must expose a reproducible local verifier and a clear public-input or
statement-binding surface; otherwise the result should be recorded as a NO-GO,
not forced into the benchmark.
