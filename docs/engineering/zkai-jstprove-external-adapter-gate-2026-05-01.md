# zkAI JSTprove external-adapter gate - 2026-05-01

## Purpose

Test whether the zkAI statement-envelope result from the EZKL and snarkjs
adapters repeats on a third external proof stack with a different proof system
and artifact shape.

The target is JSTprove at upstream commit
`7c3cbbee83aaa01adde700673f00e317a4e902f9`, using the `jstprove-remainder`
verifier over a tiny ONNX `Gemm` fixture:

- source model: `tiny_gemm.onnx`, a one-node ONNX Gemm graph,
- verifier-facing artifacts: `model.msgpack`, `input.msgpack`, and
  `proof.msgpack`,
- verifier: `jstprove-remainder verify --model model.msgpack --proof proof.msgpack --input input.msgpack`,
- proof family: JSTprove/Remainder GKR/sum-check.

This is a statement-binding benchmark, not a performance benchmark and not a
JSTprove security audit.

## Checked artifacts

Artifact directory:

`docs/engineering/evidence/zkai-jstprove-statement-envelope-2026-05/`

Checked files:

- `tiny_gemm.onnx`
- `model.msgpack`
- `input.msgpack`
- `proof.msgpack`
- `metadata.json`

Generated benchmark evidence:

- `docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.json`
- `docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.tsv`

Generator commit recorded in evidence:

`cfa331be04c7cfe7dd5345bcd95a2552714539e8`

## Result

Two adapters were tested against the same baseline proof and the same mutation
set.

| Adapter | Baseline | Mutations rejected | Gate |
|---|---:|---:|---|
| `jstprove-proof-only` | accepted | 1 / 13 | NO-GO for statement-bound relabeling |
| `jstprove-statement-envelope` | accepted | 13 / 13 | GO for external proof-backed statement envelope |

The raw proof-only path rejects a semantic input-artifact mutation, as it
should, but accepts metadata-only relabeling because those labels are outside
the raw JSTprove proof acceptance path. This is not a JSTprove bug and not a
JSTprove security finding. It is the expected boundary between proof validity
and application statement binding.

The statement-envelope path first checks the statement commitment, artifact
hashes, model/input/output/config labels, verifier domain, proof-system version,
upstream commit, Remainder dependency commit, and explicit setup non-claim, and
then delegates proof validity to JSTprove. Under that adapter, all 13 mutations
are rejected.

## Interpretation

This is the third useful external-adapter result for the zkAI relabeling line.
Together with EZKL and snarkjs, it supports the adapter-level verifier-boundary
claim:

> Proof validity and statement binding are distinct verifier layers.

The result is deliberately narrow. It does not say that raw JSTprove, raw EZKL,
or raw snarkjs are wrong. Each raw verifier validates the proof object and public
inputs it is given. The result says that a zkAI system needs an explicit
statement-binding receipt if it wants model/input/output/config/setup/domain
relabeling rejection to be a verifier-level property.

## Reproduction

Environment used:

- Python `3.12.11`
- Rust nightly `2025-03-27`
- `protoc` from Homebrew `protobuf` `34.1`
- JSTprove commit `7c3cbbee83aaa01adde700673f00e317a4e902f9`
- Remainder dependency commit `06a5f406`
- macOS arm64

Build JSTprove Remainder:

```bash
git clone https://github.com/inference-labs-inc/JSTprove.git /tmp/jstprove-adapter-check/JSTprove
cd /tmp/jstprove-adapter-check/JSTprove
git checkout 7c3cbbee83aaa01adde700673f00e317a4e902f9
cargo build --release --bin jstprove-remainder
```

Regenerate the benchmark evidence from this repository, pointing the harness at
the built verifier binary:

```bash
export ZKAI_JSTPROVE_REMAINDER_BIN=/tmp/jstprove-adapter-check/JSTprove/target/release/jstprove-remainder
export ZKAI_JSTPROVE_BENCHMARK_COMMAND_JSON='["env","ZKAI_JSTPROVE_BENCHMARK_GIT_COMMIT=cfa331be04c7cfe7dd5345bcd95a2552714539e8","ZKAI_JSTPROVE_REMAINDER_BIN=/path/to/jstprove-remainder","python3","scripts/zkai_jstprove_statement_envelope_benchmark.py","--write-json","docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.json","--write-tsv","docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.tsv"]'
ZKAI_JSTPROVE_BENCHMARK_GIT_COMMIT=cfa331be04c7cfe7dd5345bcd95a2552714539e8 \
  python3 scripts/zkai_jstprove_statement_envelope_benchmark.py \
  --write-json docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.tsv
```

The checked proof artifacts were generated with this local command shape:

```bash
# Create tiny_gemm.onnx with onnx.helper: input [1, 2], output [1, 1], one Gemm node.
./target/release/jstprove-remainder compile \
  --model tiny_gemm.onnx \
  --output model.msgpack \
  --no-compress
python3 create_input_msgpack.py  # raw msgpack {"input": [1.0, 2.0]}
./target/release/jstprove-remainder witness \
  --model model.msgpack \
  --input input.msgpack \
  --output witness.msgpack \
  --no-compress
./target/release/jstprove-remainder prove \
  --model model.msgpack \
  --witness witness.msgpack \
  --output proof.msgpack
./target/release/jstprove-remainder --quiet verify \
  --model model.msgpack \
  --proof proof.msgpack \
  --input input.msgpack
```

Only verifier-facing artifacts are checked in. The witness is intentionally
omitted because it is not needed to rerun the relabeling verifier benchmark.

## Negative fixture note

The upstream LeNet and mini-ResNet demo lanes were also tested during this gate.
They are reproducible but not suitable as checked-in adapter fixtures:

- LeNet uncompressed proof: `859 MiB`, generated in `193.96 s`.
- mini-ResNet compressed proof: `401.9 MiB`, generated in `260.29 s`.

Those results are useful engineering context but not publication evidence for
this adapter. The checked `tiny_gemm` fixture keeps the external verifier real
while keeping the repository artifact small enough to audit.

## Validation

Final validation used for this gate:

```bash
ZKAI_JSTPROVE_REMAINDER_BIN=/tmp/jstprove-adapter-check/JSTprove/target/release/jstprove-remainder \
  python3 scripts/zkai_jstprove_statement_envelope_benchmark.py --json
python3 -m unittest scripts.tests.test_zkai_jstprove_statement_envelope_benchmark
python3 -m py_compile \
  scripts/zkai_jstprove_statement_envelope_benchmark.py \
  scripts/tests/test_zkai_jstprove_statement_envelope_benchmark.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
```

## Non-claims

- This is not a JSTprove security audit.
- This is not a system ranking.
- This is not a performance benchmark.
- The proof-only NO-GO is limited to metadata outside the raw JSTprove acceptance
  path.
- The statement-envelope GO is an adapter result, not a claim that raw JSTprove
  proves model/input/output labels by itself.
- The `tiny_gemm` fixture is not a transformer proof.

Follow-up issue: https://github.com/omarespejel/provable-transformer-vm/issues/360 tracks whether the large JSTprove CNN proof-size behavior is a useful next research axis.
