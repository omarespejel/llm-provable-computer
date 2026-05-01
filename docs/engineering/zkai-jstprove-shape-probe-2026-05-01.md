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
- Generator dependencies: Python `3.13.11`, ONNX `1.21.0`,
  NumPy `2.4.4`, msgpack `(1, 1, 2)`, ONNX opset `17`
- Generator commit recorded in evidence:
  `376eaa8a80544d5b4121e33314aa6bd28250caa1`

Checked evidence:

- `docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.json`
- `docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.tsv`

Generator:

- `scripts/zkai_jstprove_shape_probe.py`

## Main fixture result

| Fixture | Shape | Gate | Proof bytes | Observation |
| --- | --- | ---: | ---: | --- |
| `tiny_gemm` | `Gemm` | GO | `11,645` | Baseline tiny linear projection proves and verifies. |
| `tiny_gemm_add` | `Gemm -> Add` | GO | `36,449` | Extra Add layer proves and verifies. |
| `tiny_gemm_residual_add` | `Gemm(width-preserving) -> Add(input)` | GO | `56,054` | Residual-style Add proves and verifies. |
| `tiny_gemm_layernorm` | `Gemm(width-preserving) -> LayerNormalization` | GO | `52,080` | LayerNormalization-style tiny shape proves and verifies. |
| `tiny_gemm_batchnorm` | `Gemm -> BatchNormalization` | GO | `95,105` | Normalization-like tiny shape proves and verifies. |
| `tiny_gemm_relu` | `Gemm -> Relu` | NO-GO | n/a | Baseline witness fails with `range_check_capacity`. |
| `tiny_gemm_softmax` | `Gemm(width-preserving) -> Softmax` | NO-GO | n/a | Witness succeeds, but proof construction refuses an unconstrained backend op. |
| `tiny_matmul_residual_add` | `MatMul -> Add(input)` | NO-GO | n/a | Compile succeeds, but witness generation reports unsupported `MatMul`. |

## Review-driven exploratory probes

The PR review asked for three extra checks before treating the result as useful:
Gemm dimension variation, ReLU input scaling, and a pinned Softmax source check.
Those checks are now part of the machine-readable evidence and committed under
`exploration_commitment`.

### Gemm dimension sweep

| Dimension | Gate | Proof bytes | Prove seconds | Verify seconds |
| ---: | ---: | ---: | ---: | ---: |
| `1` | GO | `11,726` | `0.799333` | `1.971647` |
| `2` | GO | `71,040` | `0.789629` | `1.948071` |
| `4` | GO | `70,138` | `0.781246` | `1.939688` |

Interpretation: this remains a tiny-shape probe, but the positive result is no
longer only a single scalar projection. JSTprove/Remainder clears `Gemm` at
widths `1`, `2`, and `4` in this checked setup.

### ReLU scaling probe

| Scale | Gate | Failure kind | Proof bytes | Prove seconds | Verify seconds |
| ---: | ---: | --- | ---: | ---: | ---: |
| `1` | NO-GO | `range_check_capacity` | n/a | n/a | n/a |
| `0.25` | GO | n/a | `87,377` | `3.995539` | `9.395193` |
| `0.1` | GO | n/a | `211,088` | `3.981442` | `9.412703` |
| `0.01` | GO | n/a | `227,462` | `3.987476` | `9.523842` |
| `0.001` | GO | n/a | `108,172` | `1.592207` | `4.051986` |

Interpretation: the baseline `Gemm -> Relu` NO-GO is not a blanket statement
that ReLU can never clear under this backend. It is a concrete range-capacity
failure at the checked magnitude. Scaled variants clear. That makes the next
research question sharper: decide whether a transformer-adjacent activation path
can keep all intermediate values within the current two-chunk range-check
capacity, or whether the backend needs a wider range-check surface.

### Softmax source check

The checked `Gemm -> Softmax` fixture reaches witness generation but fails at
proof construction with `unconstrained_backend_op`. The source probe ties this to
the pinned JSTprove source at commit `7c3cbbee83aaa01adde700673f00e317a4e902f9`.
The evidence records `SOURCE_HIT` with a Remainder proof-construction refusal in:

- `rust/jstprove_remainder/src/runner/circuit_builder.rs:458`

The source also contains Softmax witness and circuit-layer code, so the useful
split is precise: Softmax exists in the broader codebase, but the checked
Remainder path refuses this ONNX Softmax fixture at proof construction rather
than accepting an unconstrained committed shred.

The source probe also checked three additional local refs after fetching the
JSTprove remote:

| Ref | Commit | Result |
| --- | --- | --- |
| `origin/main-b` | `d71e49514f90877c1a6551514d1debec9930358e` | No Remainder Softmax path found. |
| `refs/tags/v2.12.1` | `eae2d6c214a46e8a43480dbab0239ff548786ee5` | No Remainder Softmax path found. |
| `origin/eliminate/relu-zero-delta-range-check` | `6d2f0e59343f3840634d028cd0f02309c1c0aa42` | No Remainder Softmax path found. |

This does not prove no future JSTprove branch can constrain Softmax. It does
close the narrower review question for this gate: the pinned branch refuses
Remainder Softmax at proof construction, and the checked alternative refs did
not expose a constrained Remainder Softmax path.

## Interpretation

This is a useful external proof-stack split:

- JSTprove/Remainder can prove tiny projection, residual-add, and
  normalization-shaped fixtures.
- `Gemm` clears at dimensions `1`, `2`, and `4` in this checked setup.
- Baseline `Gemm -> Relu` fails with a range-check-capacity error, but smaller
  scaled variants clear. The blocker is magnitude-sensitive in this probe.
- The checked `Softmax` path reaches witness generation but is refused by proof
  construction because the op is not constrained in the Remainder backend path.
- Literal ONNX `MatMul` compiles, but witness generation rejects it; `Gemm` is
  the working projection surface in this probe.

The positive part is paper-useful only as engineering context: it makes the
JSTprove adapter less toy-like than a one-node `Gemm` fixture because
`Gemm -> residual Add` and `Gemm -> LayerNormalization` are recognizably
transformer-adjacent. The negative part is also useful: it shows that statement
binding, proof validity, exact arithmetic semantics, and backend operator support
are separate gates. A zkAI system can bind a statement correctly while still
being blocked by backend operator coverage.

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
/tmp/jstprove-adapter-check/onnx-venv/bin/python -m pip install \
  onnx==1.21.0 numpy==2.4.4 msgpack==1.1.2
```

Regenerate the evidence:

```bash
git -C /tmp/jstprove-adapter-check/JSTprove fetch origin \
  '+refs/heads/*:refs/remotes/origin/*' '+refs/tags/*:refs/tags/*'

ZKAI_JSTPROVE_SHAPE_PROBE_GIT_COMMIT=376eaa8a80544d5b4121e33314aa6bd28250caa1 \
ZKAI_JSTPROVE_REMAINDER_BIN=/tmp/jstprove-adapter-check/JSTprove/target/release/jstprove-remainder \
  /tmp/jstprove-adapter-check/onnx-venv/bin/python \
  scripts/zkai_jstprove_shape_probe.py \
  --work-dir /tmp/zkai-jstprove-shape-probe-checked \
  --write-json docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.tsv
```

The script generates all ONNX fixtures and intermediate JSTprove artifacts under
a unique temp directory by default. The checked evidence command uses an
explicit `--work-dir` so the recorded evidence path is stable. The intermediate
proof artifacts are intentionally not checked in; the JSON/TSV record the gate
result.

## Validation

```bash
python3 -m unittest \
  scripts.tests.test_zkai_jstprove_shape_probe \
  scripts.tests.test_zkai_jstprove_statement_envelope_benchmark
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
