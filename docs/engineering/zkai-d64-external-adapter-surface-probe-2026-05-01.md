# zkAI d64 external-adapter surface probe - 2026-05-01

## Question

Can the canonical `d=64` RMSNorm-SwiGLU-residual statement fixture be sent to a
vanilla external proof adapter now, and can we honestly compare verifier/prover
numbers against external zkML stacks from that path?

## Decision

**NO-GO for an exact vanilla external export today.**

**GO for reusing the statement-receipt target once an exact proof exists.**

This is not an EZKL or ONNX security finding. It is an adapter-surface finding:
the checked `d=64` target is an exact signed-q8 integer statement, while a
vanilla floating export would prove a different statement unless it encodes the
same rounding, integer-root, lookup, and commitment semantics.

## What was checked

The probe uses the canonical statement fixture from:

- `docs/engineering/zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05.json`

Pinned statement commitment:

`blake2b-256:c548a003ed77ad02736fe31f3d24ee1d941994e9b14351d57fad9799970cecc6`

The fixture remains `REFERENCE_FIXTURE_NOT_PROVEN`; this probe does not change
that status.

## Adapter matrix

| Candidate adapter | Gate | Same-statement proof claim | Interpretation |
|---|---|---|---|
| `vanilla_onnx_ezkl_exact_export` | `NO_GO` | `NO_GO` | The exact integer statement is not currently encoded by a vanilla float export path. |
| `float_onnx_approximation` | `NO_GO_FOR_SAME_STATEMENT` | `NO_GO` | Could define a separate approximate statement, but cannot stand in for the committed fixture. |
| `custom_table_range_external_circuit` | `POSSIBLE_NOT_CHECKED` | `NOT_CHECKED` | A custom circuit/adapter may work if it binds the existing statement exactly. |
| `stwo_vector_row_air` | `REFERRED_TO_BACKEND_TRACK` | `NOT_CHECKED` | This remains the native proof path for the exact statement. |
| `zkai_statement_receipt_only` | `GO_FOR_BINDING_TARGET_NOT_PROOF` | `NO_GO` | The receipt can bind the target, but it still needs a delegated exact proof. |

## Exact semantics that block a naive export

The external adapter must encode all of these before it can claim to prove the
same statement:

- signed-q8 integer arithmetic,
- floor-division rounding at normalization, projection, hidden mixing, and down
  projection points,
- integer square-root for the RMS denominator,
- the bounded integer SiLU lookup table,
- committed parameter tables for `49,216` scalars,
- statement-receipt binding for model/config/weight/input/output/public-instance
  commitments.

A naive float-style drift canary changes `61 / 64` output positions and has max
absolute output delta `10` q8 units. That is a strong enough warning that a
floating export should be treated as a different statement, not as an adapter for
this one.

## Dependency note

The checked evidence intentionally does not record host dependency availability.
That keeps the JSON/TSV reproducible across machines. For local diagnosis, run
the probe with `--include-host-deps`.

Host dependency availability is not the main research blocker. Even with the
external runtime installed, the exact-semantics blocker above remains unless the
adapter circuit encodes the fixture's integer operations and statement receipt.

## Why this matters

This prevents a common self-deception route: exporting a close-looking ONNX graph
and then comparing its proof numbers as if it proved the same committed d64
statement. It does not.

The next credible comparison must choose one of two honest paths:

1. build an exact custom external circuit/adapter that binds this same statement
   commitment, or
2. build the native Stwo vector-row AIR/export path and use it as the exact proof
   backend.

A third path, approximate floating inference, is allowed only if we write and
bind a new approximate statement target with its own commitments and non-claims.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d64-external-adapter-surface-probe-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d64-external-adapter-surface-probe-2026-05.tsv`
- Probe generator:
  `scripts/zkai_d64_external_adapter_surface_probe.py`
- Tests:
  `scripts/tests/test_zkai_d64_external_adapter_surface_probe.py`

## Reproduce

```bash
python3 scripts/zkai_d64_external_adapter_surface_probe.py \
  --write-json docs/engineering/evidence/zkai-d64-external-adapter-surface-probe-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-external-adapter-surface-probe-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_external_adapter_surface_probe
```

## Non-claims

- This is not an EZKL security finding.
- This is not a claim that EZKL or ONNX cannot encode custom exact integer
  circuits.
- This is not a proof-generation benchmark.
- This is not a verifier-time benchmark.
- This is not evidence that the d64 statement is proven.
- This is not full transformer inference.
