# d128 compact-preprocessed component reprove

Date: 2026-05-15

## Question

Can the selected public d128 RMSNorm and projection-bridge relations be
reproven with preprocessed public columns instead of duplicated public trace
columns, while preserving statement binding and local verification?

## Decision

`GO_D128_COMPONENT_NATIVE_COMPACT_PREPROCESSED_REPROVE`

This is a stronger d128 native-reprove signal than the first component-native
two-slice result. The previous native reprove proved the selected RMSNorm
public-row and projection-bridge relations together, but it still duplicated
the public row values as both preprocessed columns and base trace columns. This
slice keeps the public row commitments, evaluates the same relation family over
preprocessed columns, and leaves one anchor trace column per selected component
so the Stwo framework trace shape remains explicit.

## Checked Numbers

| Object | JSON proof bytes | Local typed bytes | Status |
| --- | ---: | ---: | --- |
| Previous selected inner-proof target | `34,866` | `12,688` | concrete target, not native reprove |
| Component-native two-slice reprove | `22,139` | `9,056` | prior native Stwo baseline |
| Compact-preprocessed component reprove | `17,350` | `6,264` | new native Stwo proof object |
| NANOZK paper-reported d128 row | `6,900` | `6,900` | paper-reported, not locally reproduced |

The compact-preprocessed proof removes `2,792` local typed bytes from the
previous component-native two-slice proof, a `30.8304%` reduction.

Against the original `12,688` typed-byte target, it removes `6,424` typed bytes,
a `50.6305%` reduction.

Against NANOZK's paper-reported `6,900` byte d128 row, this local typed object
is `6,264` bytes, ratio `0.907826x`, or `636` typed bytes smaller.

## Interpretation

This is the first d128 result that crosses the external paper-reported row under
the repo's local typed accounting. That is interesting, but it is not a matched
NANOZK win.

The mechanism matters more than the headline number. The selected surface is
public-row RMSNorm plus a public RMSNorm-to-projection bridge. For that kind of
surface, the proof does not need to commit the same public values twice. It can
bind the public row data as preprocessed columns, enforce the arithmetic over
those columns, and keep only small anchor trace columns. That is a concrete
STARK-native compression lever.

The result is still scoped:

- It covers two selected d128 relations, not the full transformer block.
- It is local typed accounting, not upstream Stwo serialization.
- It is not a locally reproduced NANOZK benchmark.
- It does not say that STARKs beat NANOZK or that this is production zkML.

## Why This Is A Better Research Target

The previous frontier was `9,056` typed bytes, still `2,156` bytes above the
paper-reported NANOZK row. The byte split showed the remaining weight was not
the projection bridge. It was duplicated public trace surface in the RMSNorm
proof shape.

This PR attacks that directly. The compact proof drops:

- sampled values from `184` to `98`;
- queried base-field values from `552` to `294`;
- trace decommitment witnesses from `54` to `48`;
- local typed bytes from `9,056` to `6,264`.

That is the cleanest mechanism found so far for the d128 comparison route.

## First Blocker

`The typed proof object is now below NANOZK's paper-reported 6.9 KB row, but the
workload is only the selected public RMSNorm plus projection-bridge surface, not
NANOZK's full d128 transformer block row and not locally reproduced NANOZK
evidence.`

## Next Attack

1. Extend the compact-preprocessed technique to the next d128 model-faithful
   relations and measure where it stops helping.
2. Identify which later block surfaces require private witness columns or
   lookup-heavy sidecars and cannot use this public-row compression directly.
3. Build a matched d128 block comparison table that separates local typed
   accounting, JSON proof bytes, paper-reported external numbers, and locally
   reproduced external numbers.
4. Keep the claim boundary strict until there is a full d128 block proof object
   or a matched external reproduction.

## Non-Claims

- Not a matched NANOZK benchmark.
- Not locally reproduced NANOZK evidence.
- Not proof that STARKs beat NANOZK.
- Not a full d128 transformer-block proof.
- Not private witness privacy.
- Not a timing result.
- Not upstream Stwo proof serialization.
- Not full transformer inference.
- Not production-ready zkML.

## Evidence

- Input:
  `docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json`
- Compact proof envelope:
  `docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json`
- Gate JSON:
  `docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.json`
- Gate TSV:
  `docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.tsv`
- Gate:
  `scripts/zkai_d128_component_compact_preprocessed_reprove_gate.py`
- Tests:
  `scripts/tests/test_zkai_d128_component_compact_preprocessed_reprove_gate.py`
- Rust module:
  `src/stwo_backend/d128_native_component_two_slice_reprove.rs`
- CLI:
  `src/bin/zkai_d128_component_native_two_slice_reprove.rs`

The gate rejects `17 / 17` source, metric, comparison, overclaim,
record-count, validation-command, and payload-commitment mutations.

## Reproduce

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- prove-compact docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- verify-compact docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json
python3 scripts/zkai_d128_component_compact_preprocessed_reprove_gate.py --write-json docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.tsv
python3 -m py_compile scripts/zkai_d128_component_compact_preprocessed_reprove_gate.py scripts/tests/test_zkai_d128_component_compact_preprocessed_reprove_gate.py
python3 -m unittest scripts.tests.test_zkai_d128_component_compact_preprocessed_reprove_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_component_two_slice_reprove --lib
cargo +nightly-2025-07-14 fmt --check
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
