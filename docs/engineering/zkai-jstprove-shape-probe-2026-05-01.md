# zkAI JSTprove shape probe - 2026-05-01

## Purpose

Issue #360 asked whether the JSTprove/Remainder adapter can move beyond the
checked one-node `Gemm` fixture without turning the result into an overclaim.
This gate answers a narrower engineering question:

> Which tiny transformer-adjacent ONNX shapes can a real
> `jstprove-remainder` verifier stack compile, witness, prove, and verify today?

This is not a JSTprove security audit, not a performance benchmark, not a
Tablero result, and not a full transformer proof.

## Environment

- JSTprove upstream commit: `7c3cbbee83aaa01adde700673f00e317a4e902f9`
- Remainder dependency commit: `06a5f406`
- Binary: `/tmp/jstprove-adapter-check/JSTprove/target/release/jstprove-remainder`
- ONNX generation Python: `/tmp/jstprove-adapter-check/onnx-venv/bin/python`
- Generator commit recorded in evidence:
  `4657787db01955b1d13248ede96ec49c3daa613b`

Checked evidence:

- `docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.json`
- `docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.tsv`

Generator:

- `scripts/zkai_jstprove_shape_probe.py`

## Result

| Fixture | Shape | Gate | Proof bytes | Observation |
| --- | --- | ---: | ---: | --- |
| `tiny_gemm` | `Gemm` | GO | `11,645` | Baseline tiny linear projection proves and verifies. |
| `tiny_gemm_add` | `Gemm -> Add` | GO | `36,449` | Extra Add layer proves and verifies. |
| `tiny_gemm_residual_add` | `Gemm(width-preserving) -> Add(input)` | GO | `56,054` | Residual-style Add proves and verifies. |
| `tiny_gemm_layernorm` | `Gemm(width-preserving) -> LayerNormalization` | GO | `52,080` | LayerNormalization-style tiny shape proves and verifies. |
| `tiny_gemm_batchnorm` | `Gemm -> BatchNormalization` | GO | `95,105` | Normalization-like tiny shape proves and verifies. |
| `tiny_gemm_relu` | `Gemm -> Relu` | NO-GO | n/a | Witness fails with `range_check_capacity`. |
| `tiny_gemm_softmax` | `Gemm(width-preserving) -> Softmax` | NO-GO | n/a | Witness succeeds, but proof construction refuses an unconstrained backend op. |
| `tiny_matmul_residual_add` | `MatMul -> Add(input)` | NO-GO | n/a | Compile succeeds, but witness generation reports unsupported `MatMul`. |

## Interpretation

This is a useful external proof-stack split:

- JSTprove/Remainder can prove tiny projection, residual-add, and
  normalization-shaped fixtures.
- The checked `Relu` path exposes a concrete Remainder range-check capacity
  blocker.
- The checked `Softmax` path reaches witness generation but is refused by proof
  construction because the op is not constrained in the Remainder backend.
- Literal ONNX `MatMul` compiles, but witness generation rejects it; `Gemm` is
  the working projection surface in this probe.

The positive part is paper-useful only as engineering context: it makes the
JSTprove adapter less toy-like than a one-node `Gemm` fixture because
`Gemm -> residual Add` and `Gemm -> LayerNormalization` are recognizably
transformer-adjacent. The negative part is also useful: it shows that statement
binding, proof validity, and operator support are three separate gates. A zkAI
system can bind a statement correctly while still being blocked by backend
operator coverage.

Follow-up issue #362 tracks the operator-blocker exploration separately so this
gate can stay closed once the checked shape evidence lands.

## Reproduction

Build JSTprove/Remainder:

```bash
git clone https://github.com/inference-labs-inc/JSTprove.git /tmp/jstprove-adapter-check/JSTprove
cd /tmp/jstprove-adapter-check/JSTprove
git checkout 7c3cbbee83aaa01adde700673f00e317a4e902f9
cargo build --release --bin jstprove-remainder
```

Create or reuse a Python environment with `onnx`, `numpy`, and `msgpack`.
The run that generated this gate used:

```bash
/tmp/jstprove-adapter-check/onnx-venv/bin/python -m pip install onnx numpy msgpack
```

Regenerate the evidence:

```bash
ZKAI_JSTPROVE_SHAPE_PROBE_GIT_COMMIT=4657787db01955b1d13248ede96ec49c3daa613b \
ZKAI_JSTPROVE_REMAINDER_BIN=/tmp/jstprove-adapter-check/JSTprove/target/release/jstprove-remainder \
  /tmp/jstprove-adapter-check/onnx-venv/bin/python \
  scripts/zkai_jstprove_shape_probe.py \
  --write-json docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.tsv
```

The script generates all ONNX fixtures and intermediate JSTprove artifacts under
`/tmp/zkai-jstprove-shape-probe` by default. The intermediate proof artifacts
are intentionally not checked in; the JSON/TSV record the gate result.

## Validation

```bash
python3 -m unittest scripts.tests.test_zkai_jstprove_shape_probe
python3 -m py_compile \
  scripts/zkai_jstprove_shape_probe.py \
  scripts/tests/test_zkai_jstprove_shape_probe.py
ZKAI_JSTPROVE_REMAINDER_BIN=/tmp/jstprove-adapter-check/JSTprove/target/release/jstprove-remainder \
  /tmp/jstprove-adapter-check/onnx-venv/bin/python \
  scripts/zkai_jstprove_shape_probe.py --json
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
```

## Non-claims

- This is not a JSTprove security finding.
- This is not a full transformer proof.
- This is not a performance benchmark.
- This is not evidence that larger JSTprove shapes remain small.
- This is not evidence that unsupported shapes are impossible in future
  JSTprove versions.
- This is not a Tablero result.
