# zkAI d64 RMSNorm-to-projection bridge AIR proof - 2026-05-01

## Question

Can the next native Stwo proof slice consume the RMSNorm-local
`rmsnorm_output_row_commitment` without relabeling it as the full d64
`output_activation_commitment`?

## Result

GO for a bounded RMSNorm-to-projection bridge AIR proof.

This is a narrow handoff proof. It consumes the checked RMSNorm-local
`normed_q8` rows under `rmsnorm_output_row_commitment`, proves row equality to a
separate projection-input row surface, and emits a domain-separated
`projection_input_row_commitment` for the next gate/value projection slice.

It deliberately does not prove gate/value projection arithmetic, activation,
SwiGLU, down-projection, residual addition, or the full d64 output activation
commitment.

## Checked commitments

| Surface | Commitment |
|---|---|
| Source RMSNorm output rows | `blake2b-256:c9ab975e440661ce7796f33b75008d20e7eb26a4c41956d2f723093e4ac373a7` |
| Projection input rows | `blake2b-256:3a84feca5eab58736fdf01369fc64d3afc45c97ecdc629e64f0bb2eb2f8de094` |
| Full d64 output activation | `blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f` |
| Projection input relabels full output | `false` |

The proof binds 64 rows. Each row contains the RMSNorm-local `normed_q8` value
and the projection-input value, and the AIR enforces equality between them.

## Evidence

Machine-readable input evidence:

- `docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.tsv`

Generator and tests:

- `scripts/zkai_d64_rmsnorm_to_projection_bridge_input.py`
- `scripts/tests/test_zkai_d64_rmsnorm_to_projection_bridge_input.py`

Rust proof module:

- `src/stwo_backend/d64_native_rmsnorm_to_projection_bridge_proof.rs`

## Fail-closed coverage

The focused Rust tests reject:

- source RMSNorm output commitment drift,
- projection input commitment drift,
- projection-input commitment relabeling as the full d64 output commitment,
- row equality drift,
- tampering a checked public row after proving,
- proof-byte tampering,
- proof commitment-vector shape drift.

The Python generator tests additionally check source-evidence commitment drift
and round-trip JSON/TSV output generation.

## Non-claims

- This is not a full d64 block proof.
- This is not a gate, value, or down projection proof.
- This is not an activation, SwiGLU, or residual proof.
- This does not bind the full d64 `output_activation_commitment`.
- This bridge proves only the domain-separated handoff from RMSNorm-local rows to
  projection-input rows.

## Interpretation

This closes the most immediate #358 self-deception risk: the RMSNorm-local output
is now consumed by a next proof surface instead of being verbally treated as the
full block output. The follow-up gate/value projection proof now consumes
`projection_input_row_commitment` and emits a domain-separated
`gate_value_projection_output_commitment`; the follow-up activation/SwiGLU proof
then consumes that output and emits a domain-separated
`hidden_activation_commitment`; the follow-up down-projection proof then consumes
that hidden activation and emits a domain-separated
`residual_delta_commitment`. The remaining full-block seam is residual closure.

## Reproduce

```bash
python3 scripts/zkai_d64_rmsnorm_to_projection_bridge_input.py \
  --write-json docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_rmsnorm_to_projection_bridge_input
cargo +nightly-2025-07-14 test d64_native_rmsnorm_to_projection_bridge_proof --lib --features stwo-backend
```

## Next step

The activation/SwiGLU slice is now recorded in
`docs/engineering/zkai-d64-activation-swiglu-proof-2026-05-02.md`, and the
down-projection slice is recorded in
`docs/engineering/zkai-d64-down-projection-proof-2026-05-02.md`. Do not claim
the full d64 output until residual rows are also proven or explicitly
source-bound.
