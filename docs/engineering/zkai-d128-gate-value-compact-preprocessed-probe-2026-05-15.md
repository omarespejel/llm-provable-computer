# d128 Gate/Value Compact-Preprocessed Probe

Date: 2026-05-15

## Decision

`NO_GO_D128_GATE_VALUE_COMPACT_PREPROCESSED_SIZE_WIN`

The compact-preprocessed route now verifies on the dense d128 gate/value
projection surface, but it is larger than the baseline native proof.

This is a useful narrowing result, not a failure of correctness.

## Checked Surface

- width: `128`
- feed-forward dimension: `512`
- checked rows: `131,072`
- gate projection multiplication rows: `65,536`
- value projection multiplication rows: `65,536`
- backend: native Stwo, publication-v1 PCS profile

## Numbers

| Object | JSON proof bytes | Local typed proof bytes | Ratio vs baseline typed |
|---|---:|---:|---:|
| baseline gate/value native proof | `57,930` | `16,360` | `1.000000x` |
| compact-preprocessed gate/value proof | `66,218` | `18,672` | `1.141320x` |

The compact proof is:

- `8,288` JSON proof bytes larger
- `2,312` typed proof-field bytes larger
- `14.1320%` larger under local typed accounting
- Mutation gate: 18/18 rejected

## Why It Matters

The earlier selected two-slice result was positive because public RMSNorm rows
and the projection bridge could move into preprocessed columns with only one
small anchor trace per selected component.

This PR tests whether that same idea generalizes to the next dense model-faithful
d128 relation. It does not, at least in this direct form.

The compact route saves some queried/opened value bytes:

- OODS samples: `-96` bytes
- queried values: `-72` bytes

But those savings are dominated by larger opening/decommitment structure:

- trace decommitments: `+480` bytes
- FRI samples: `+80` bytes
- FRI decommitments: `+1,920` bytes

The net result is `+2,312` typed bytes.

## Interpretation

This narrows the breakthrough path.

Compact-preprocessed rows remain valuable for small public/boundary relations,
but dense arithmetic probably needs a different win mechanism: fusion across
adjacent arithmetic/lookup components, aggregation that shares commitment and
opening plumbing, or a more native component layout that avoids paying extra
FRI/decommitment cost for row-order anchoring.

The result also protects the paper narrative from overclaiming. We can now say:

> The compact-preprocessed technique does not automatically reduce proof size
> on dense d128 gate/value projection. The next proof-size breakthrough should
> come from fused or aggregated proof architecture, not this direct dense-row
> compaction pattern.

## Artifacts

- baseline input:
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json`
- baseline envelope:
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json`
- compact envelope:
  `docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json`
- gate JSON:
  `docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.json`
- gate TSV:
  `docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.tsv`
- gate script:
  `scripts/zkai_d128_gate_value_compact_preprocessed_gate.py`
- tests:
  `scripts/tests/test_zkai_d128_gate_value_compact_preprocessed_gate.py`
- CLI:
  `src/bin/zkai_d128_gate_value_projection_proof.rs`

## Non-Claims

- Not a full d128 transformer-block proof.
- Not a NANOZK proof-size win.
- Not a matched external zkML benchmark.
- Not evidence that compact-preprocessed is the right dense-arithmetic path.
- Not private parameter-opening proof.
- Not upstream Stwo proof serialization.
- Not timing evidence.
- Not full transformer inference.
- Not production-ready zkML.

## Validation

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- prove docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- prove-compact docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- verify-compact docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json
python3 scripts/zkai_d128_gate_value_compact_preprocessed_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_gate_value_compact_preprocessed_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_gate_value_projection_proof --lib
```
