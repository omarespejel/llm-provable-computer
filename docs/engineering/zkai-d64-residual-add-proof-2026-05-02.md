# zkAI d64 residual-add AIR proof - 2026-05-02

## Question

Can the native Stwo d64 path consume `residual_delta_commitment`, bind the
canonical input activation, prove the residual-add rows, and only then emit or
accept the final `output_activation_commitment`?

## Result

GO for a bounded residual-add AIR proof slice.

Backend version: `stwo-rmsnorm-swiglu-residual-d64-v2`.
Timing mode: `not timed` (proof/verify correctness gate).
Checked step count: `64` residual-add rows.

This slice consumes two committed surfaces:

- `input_activation_commitment` from the canonical d64 public instance,
- `residual_delta_commitment` from the down-projection proof slice.

It proves `64` public residual-add rows in native Stwo AIR:

```text
input_q8[i] + residual_delta_q8[i] = output_q8[i]
```

Before accepting the proof, the verifier recomputes the input activation
commitment, the source residual-delta commitment, the residual-add row
commitment, and the final output activation commitment.

This is the first native d64 slice that reaches the final
`output_activation_commitment`. It is still not recursive composition of all d64
proof slices and still not a private parameter-opening proof.

## Checked commitments

| Surface | Commitment |
|---|---|
| Input activation | `blake2b-256:4f765c71601320b3ee9341056299e79a004fa94aaa2edcb5c161cb7366b051fc` |
| Source residual delta | `blake2b-256:ff67391fd2636e118af323efb1ed559114421a96e8ea30a7424c114e7074622a` |
| Residual-add rows | `blake2b-256:6baf5415fa20ad7fce80b14c361815ea55553fe7609b17bff383c16771651592` |
| Final output activation | `blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f` |
| Residual delta relabels full output | `false` |
| Input relabels output | `false` |

## Evidence

Machine-readable input evidence:

- `docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.tsv`

Generator and tests:

- `scripts/zkai_d64_residual_add_proof_input.py`
- `scripts/tests/test_zkai_d64_residual_add_proof_input.py`

Rust proof module:

- `src/stwo_backend/d64_native_residual_add_proof.rs`

## Fail-closed coverage

The focused Rust tests reject:

- residual-delta relabeling as the full d64 output commitment,
- input activation relabeling as the full d64 output commitment,
- input activation vector drift,
- residual-delta vector drift,
- output activation vector drift,
- fixed-point q8 semantic-bound drift for input, residual delta, and output activations,
- residual-add row relation drift,
- residual-add row commitment drift,
- oversized input JSON,
- oversized proof bytes,
- proof-byte tampering,
- proof commitment-vector shape drift,
- PCS verifier-profile drift before commitment-root recomputation.

The focused Python generator tests additionally reject source down-projection
evidence drift, source residual-delta commitment drift, oversized source JSON,
non-file source paths, invalid UTF-8 source JSON, and JSON/TSV round-trip issues.

## Non-claims

- This is not recursive composition of all d64 proof slices.
- This is not a private parameter-opening proof.
- This is not model-scale transformer inference.
- This is not verifier-time benchmark evidence.
- This is not onchain deployment evidence.
- The q8 bound here is a fixed-point semantic bound (`[-1024, 1024]`) for this
  statement surface, not an `int8` storage claim.

## Interpretation

This closes the #372 seam. The native path now advances from RMSNorm public rows,
through projection, activation/SwiGLU, down projection, and residual-addition to
the final d64 `output_activation_commitment`.

The result is useful because the final output commitment is no longer a reference
fixture assumption after down projection. It is checked by a native residual-add
AIR slice that consumes the intermediate residual-delta commitment and the public
input activation commitment.

The next honest strengthening is a composition step: consume all checked slice
receipts as one statement-bound block receipt, without claiming recursive
compression unless a real recursive proof exists.

## Reproduce

```bash
python3 scripts/zkai_d64_residual_add_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_residual_add_proof_input
cargo +nightly-2025-07-14 test d64_native_residual_add_proof --lib --features stwo-backend
```

## Next step

Issue #374 tracks composing the native d64 proof slices into a single
statement-bound block receipt that validates the slice chain and exposes one
final receipt object for the agent/verifiable-AI layer.
