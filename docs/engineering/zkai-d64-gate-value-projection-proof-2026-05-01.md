# zkAI d64 gate/value projection AIR proof - 2026-05-01

## Question

Can the next native Stwo proof slice consume
`projection_input_row_commitment` and prove the gate/value projection
multiplication rows without relabeling the result as the full d64 block output?

## Result

GO for a bounded gate/value projection AIR proof.

This slice consumes the RMSNorm-to-projection bridge output:
`projection_input_row_commitment`. It proves `32,768` public multiplication rows
in native Stwo AIR:

- `16,384` gate-projection rows,
- `16,384` value-projection rows.

Each row checks:

```text
projection_input_q8 * weight_q8 = product_q8
```

The verifier then recomputes the projection-input row commitment, gate/value
matrix roots, gate/value output vectors, the gate/value output commitments, and
the gate/value multiplication-row commitment before accepting the proof.

This deliberately does not prove activation, SwiGLU mixing, down projection,
residual addition, or the full d64 `output_activation_commitment`.

## Checked commitments

| Surface | Commitment |
|---|---|
| Source projection input rows | `blake2b-256:3a84feca5eab58736fdf01369fc64d3afc45c97ecdc629e64f0bb2eb2f8de094` |
| Gate matrix root | `blake2b-256:c7f5f490cc4140756951d0305a4786a1de9a282687c05a161ea04bd658657cfa` |
| Value matrix root | `blake2b-256:e63d0d6839c92386e50314370e8b13dee0aa68c624f8ce88c34f6a4c1a2c3174` |
| Gate projection output | `blake2b-256:11d4782e19becb15a541ff542971789049c802277255410db88b6423998b1ef8` |
| Value projection output | `blake2b-256:71599f8691b781d78edddac94f09c3b4c1d572e20013c6122faea8d83abf724d` |
| Gate/value projection output | `blake2b-256:d7127c1002acd821428da00b5ca1aabdb5a43809d6834b9b6b08d13d8e9f8e02` |
| Gate/value multiplication rows | `blake2b-256:2ea591b42ef4a2bc6c5c88f8dc33003bb4a0cf357b57f01e1c5b7dce822035db` |
| Full d64 output activation | `blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f` |
| Gate/value output relabels full output | `false` |

## Evidence

Machine-readable input evidence:

- `docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.tsv`

Generator and tests:

- `scripts/zkai_d64_gate_value_projection_proof_input.py`
- `scripts/tests/test_zkai_d64_gate_value_projection_proof_input.py`

Rust proof module:

- `src/stwo_backend/d64_native_gate_value_projection_proof.rs`

## Fail-closed coverage

The focused Rust tests reject:

- gate/value output relabeling as the full d64 output commitment,
- projection-input vector drift,
- projection-input commitment drift,
- gate output commitment drift,
- gate/value row commitment drift,
- checked public-row tampering after proving,
- proof-byte tampering,
- proof commitment-vector shape drift.

The focused Python generator tests additionally reject source bridge drift,
projection-input vector drift, projection-row commitment drift, matrix-root
drift, output-vector drift, oversized source bridge JSON, and JSON/TSV
round-trip issues.

One useful hardening observation: a one-row weight or product perturbation can
leave a floored projection output unchanged. That is why the proof binds both
output commitments and parameter-derived row commitments rather than relying only
on output-vector equality.

## Non-claims

- This is not a full d64 block proof.
- This is not an activation or SwiGLU proof.
- This is not a down-projection proof.
- This is not a residual proof.
- This does not bind the full d64 `output_activation_commitment`.
- Output aggregation is verifier-recomputed from checked public multiplication
  rows; this is not yet a private aggregation AIR claim.

## Interpretation

This closes the immediate #367 proof-native seam: the native path now advances
from RMSNorm-local rows through a domain-separated projection-input handoff and
into a proved gate/value projection row slice. The remaining d64 full-block gap
is now narrower and explicit: activation/SwiGLU, down projection, and residual
rows must still be proven or otherwise source-bound before the final output
commitment can be claimed.

## Reproduce

```bash
python3 scripts/zkai_d64_gate_value_projection_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_gate_value_projection_proof_input
cargo +nightly-2025-07-14 test d64_native_gate_value_projection_proof --lib --features stwo-backend
```

## Next step

The activation/SwiGLU slice is now recorded in
`docs/engineering/zkai-d64-activation-swiglu-proof-2026-05-02.md`. The next
remaining d64 seam is down projection over the domain-separated
`hidden_activation_commitment`. Do not claim the full d64 output until down
projection and residual rows are also proven or explicitly source-bound.
