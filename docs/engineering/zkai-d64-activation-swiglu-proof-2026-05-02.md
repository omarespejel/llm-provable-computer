# zkAI d64 activation/SwiGLU AIR proof - 2026-05-02

## Question

Can the native Stwo d64 path consume `gate_value_projection_output_commitment`,
source-bind the bounded activation lookup plus SwiGLU mixing rows, and emit an
intermediate hidden activation commitment without relabeling it as the full d64
block output?

## Result

GO for a bounded activation/SwiGLU AIR proof slice.

This slice consumes the gate/value projection output commitment:
`gate_value_projection_output_commitment`. It proves `256` public activation and
SwiGLU rows in native Stwo AIR:

- `256` bounded activation lookup rows,
- `256` SwiGLU mix rows.

Each row is verifier-recomputed from the checked gate/value projection vectors
and then constrained in AIR:

```text
activation_q8 * value_q8 = product_q16
product_q16 = hidden_q8 * 256 + remainder_q16
0 <= remainder_q16 < 256
```

The verifier recomputes the source gate/value output commitment, the activation
lookup commitment, the activation output commitment, the hidden activation
commitment, and the activation/SwiGLU row commitment before accepting the proof.

This deliberately does not prove down projection, residual addition, or the full
d64 `output_activation_commitment`.

## Checked commitments

| Surface | Commitment |
|---|---|
| Source gate projection output | `blake2b-256:11d4782e19becb15a541ff542971789049c802277255410db88b6423998b1ef8` |
| Source value projection output | `blake2b-256:71599f8691b781d78edddac94f09c3b4c1d572e20013c6122faea8d83abf724d` |
| Source gate/value projection output | `blake2b-256:d7127c1002acd821428da00b5ca1aabdb5a43809d6834b9b6b08d13d8e9f8e02` |
| Activation lookup table | `blake2b-256:3487a9ab6cd871b7b46e54c004bf547fe9db9ba8e90b3872ba6ae3cfb990c4b3` |
| Activation output | `blake2b-256:0affe836f18831511792d49333e153038a5a15c4de501f11535060c458395464` |
| Hidden activation output | `blake2b-256:18482fa6e000d8fb0e0d7b39db46355eeec556622ca69478d1a039438495b047` |
| Activation/SwiGLU rows | `blake2b-256:2a2bde136784be11b6bfcadfa09b1c952580c97d967b1a8ebeac2f9d69d9bd2e` |
| Full d64 output activation | `blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f` |
| Hidden activation relabels full output | `false` |

## Evidence

Machine-readable input evidence:

- `docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.tsv`

Generator and tests:

- `scripts/zkai_d64_activation_swiglu_proof_input.py`
- `scripts/tests/test_zkai_d64_activation_swiglu_proof_input.py`

Rust proof module:

- `src/stwo_backend/d64_native_activation_swiglu_proof.rs`

## Fail-closed coverage

The focused Rust tests reject:

- hidden activation relabeling as the full d64 output commitment,
- source gate projection vector drift,
- activation output drift,
- hidden activation output drift,
- activation lookup commitment drift,
- activation/SwiGLU row commitment drift,
- oversized input JSON,
- oversized proof bytes,
- proof-byte tampering,
- proof commitment-vector shape drift.

The focused Python generator tests additionally reject source gate/value evidence
drift, gate/vector drift, activation output drift, hidden output drift,
activation lookup commitment drift, row commitment drift, oversized source JSON,
non-file source paths, invalid UTF-8 source JSON, and JSON/TSV round-trip issues.

## Non-claims

- This is not a full d64 block proof.
- This is not a down-projection proof.
- This is not a residual proof.
- This does not bind the full d64 `output_activation_commitment`.
- This is not a private activation-lookup opening proof; activation rows are
  verifier-recomputed from checked public rows before proof verification.
- This is not model-scale transformer inference.

## Interpretation

This closes the immediate #368 seam: the native path now advances from RMSNorm
public rows, through a projection-input bridge, through gate/value projection
rows, and into a proved activation/SwiGLU row slice. The remaining d64
full-block gap is now closed by the follow-up down-projection and residual-add
slices: the route reaches a domain-separated residual delta, then proves the
residual-add rows that emit the final `output_activation_commitment`.

The interesting research point is the shape, not the scale: the result shows the
statement-bound transformer path can keep moving across real transformer seams
without collapsing hidden activations into an overclaimed final output.

## Reproduce

```bash
python3 scripts/zkai_d64_activation_swiglu_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_activation_swiglu_proof_input
cargo +nightly-2025-07-14 test d64_native_activation_swiglu_proof --lib --features stwo-backend
```

## Next step

The down-projection slice now consumes `hidden_activation_commitment` and
produces a domain-separated residual-delta commitment:

- `docs/engineering/zkai-d64-down-projection-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.json`
- `src/stwo_backend/d64_native_down_projection_proof.rs`

Do not claim the full d64 output until residual addition is also proven or
explicitly source-bound.
