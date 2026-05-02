# zkAI d64 down-projection AIR proof - 2026-05-02

## Question

Can the native Stwo d64 path consume `hidden_activation_commitment`,
source-bind the down-projection multiplication rows, and emit a residual-delta
commitment without relabeling it as the full d64 block output?

## Result

GO for a bounded down-projection AIR proof slice.

Backend version: `stwo-rmsnorm-swiglu-residual-d64-v2`.
Timing mode: `not timed` (proof/verify correctness gate).
Checked step count: `16,384` down-projection multiplication rows (`ff_dim = 256`).

This slice consumes the activation/SwiGLU hidden activation commitment:
`hidden_activation_commitment`. It proves `16,384` public down-projection
multiplication rows in native Stwo AIR:

```text
hidden_q8 * down_weight_q8 = product_q8
```

The verifier then recomputes each output accumulator and applies the fixed
signed-q8 floor division by `ff_dim = 256`:

```text
residual_delta_q8[row] = floor(sum_col(product_q8[row, col]) / 256)
```

Before accepting the proof, the verifier recomputes the source hidden activation
commitment, the down matrix root from deterministic checked row weights, the
multiplication-row commitment, and the residual-delta commitment.

This deliberately does not prove residual addition or bind the final d64
`output_activation_commitment`.

## Checked commitments

| Surface | Commitment |
|---|---|
| Source hidden activation output | `blake2b-256:18482fa6e000d8fb0e0d7b39db46355eeec556622ca69478d1a039438495b047` |
| Down matrix root | `blake2b-256:19b08584116916a72297047f01e2dc7505fb19e9508b384c7d80dfe3cb82c330` |
| Down-projection rows | `blake2b-256:a0e069f148403112d512dff050b211e490e03d8af846d27c7f2cebe3bdb7fb68` |
| Residual delta output | `blake2b-256:ff67391fd2636e118af323efb1ed559114421a96e8ea30a7424c114e7074622a` |
| Full d64 output activation | `blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f` |
| Residual delta relabels full output | `false` |

## Evidence

Machine-readable input evidence:

- `docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.tsv`

Generator and tests:

- `scripts/zkai_d64_down_projection_proof_input.py`
- `scripts/tests/test_zkai_d64_down_projection_proof_input.py`

Rust proof module:

- `src/stwo_backend/d64_native_down_projection_proof.rs`

## Fail-closed coverage

The focused Rust tests reject:

- residual-delta relabeling as the full d64 output commitment,
- hidden activation vector drift,
- source hidden activation commitment drift,
- residual-delta vector drift,
- fixed-point q8 semantic-bound drift for hidden activations and residual deltas,
- down matrix root drift,
- down-projection row commitment drift,
- oversized input JSON,
- oversized proof bytes,
- proof-byte tampering,
- proof commitment-vector shape drift,
- PCS verifier-profile drift before commitment-root recomputation.

The focused Python generator tests additionally reject source activation/SwiGLU
evidence drift, hidden vector length drift, residual-delta commitment drift,
oversized source JSON, non-file source paths, invalid UTF-8 source JSON, and
JSON/TSV round-trip issues.

## Non-claims

- This is not a full d64 block proof.
- This is not a residual proof.
- This does not bind the full d64 `output_activation_commitment`.
- This is not a private down-weight opening proof; down-projection rows are
  verifier-recomputed from checked public rows before proof verification.
- This is not model-scale transformer inference.
- The q8 bound here is a fixed-point semantic bound (`[-1024, 1024]`) for this
  statement surface, not an `int8` storage claim.

## Interpretation

This closes the #371 seam: the native path now advances from RMSNorm public rows,
through a projection bridge, gate/value projection rows, activation/SwiGLU rows,
and into a proved down-projection row slice. The remaining d64 full-block gap is
now narrow and explicit: residual addition must still be proven or explicitly
source-bound before the final output commitment can be claimed.

The result is useful because it removes one more opportunity to confuse an
intermediate transformer value with the statement output. The proof validates a
real transformer relation surface, but it keeps the final-output claim gated on
the missing residual-add receipt.

## Reproduce

```bash
python3 scripts/zkai_d64_down_projection_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_down_projection_proof_input
cargo +nightly-2025-07-14 test d64_native_down_projection_proof --lib --features stwo-backend
```

## Next step

Issue #372 tracks the residual-add slice that consumes
`residual_delta_commitment` and the original input activation commitment, proves
`64` residual rows, and only then emits or accepts the final
`output_activation_commitment`.
