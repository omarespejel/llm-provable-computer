# d128 component-native two-slice reprove

Date: 2026-05-15

## Question

Can the selected d128 RMSNorm public-row and projection-bridge relations be
reproven as native Stwo components with one shared proof object smaller than
the selected inner-proof verifier-execution target?

## Decision

`GO_D128_COMPONENT_NATIVE_TWO_SLICE_REPROVE_PROOF_OBJECT`

This is the first positive native-reprove attack against the `12,688` typed-byte
d128 verifier-execution target. It proves the selected RMSNorm public-row and
RMSNorm-to-projection bridge components together in one Stwo proof object, using
shared commitment/opening plumbing.

It is not a matched NANOZK proof-size win. It is a real structural-saving signal
and a better next research target than the strict inner-proof verifier-execution
route.

## Checked Numbers

| Object | JSON proof bytes | Local typed bytes | Status |
| --- | ---: | ---: | --- |
| Previous selected inner-proof target | `34,866` | `12,688` | concrete target, not native reprove |
| Component-native two-slice reprove | `22,139` | `9,056` | real native Stwo proof object |
| NANOZK paper-reported d128 row | `6,900` | `6,900` | paper-reported, not locally reproduced |

The component-native reprove removes `3,632` local typed bytes from the previous
`12,688` typed-byte target, a `28.6255%` reduction.

It closes `62.7505%` of the original typed gap to NANOZK's paper-reported
`6,900` byte d128 row. The remaining gap is `2,156` typed bytes, so this route
still needs a further `23.8074%` reduction from the new `9,056` typed-byte proof
to equal that reported row.

The JSON proof payload also shrinks from `34,866` to `22,139` bytes, a
`36.5026%` reduction. JSON remains secondary to the local typed accounting.

## Interpretation

This is the strongest comparison signal in the d128 route so far.

The previous compact outer statement proof was small, but it was a statement
binding object and not comparable to a block proof. This result is more
interesting because it replaces the two selected inner proof objects with a
native proof over the selected component relations.

In human terms: the proof got smaller by proving the two related transformer
relations together, instead of carrying or targeting two separate proof objects.
That is exactly the STARK-native architecture thesis we are trying to test.

The result is still scoped:

- It covers two selected d128 relations, not the full transformer block.
- It reproves native component relations; it does not execute the inner Stwo
  verifier inside another proof.
- It is above NANOZK's paper-reported row, so the only honest claim is that the
  native-reprove path is now promising and measurable.

## Next Attack

The next useful experiment is not to relabel this as a win. It is to attack the
remaining `2,156` typed bytes.

Promising directions:

1. Reduce query/decommitment footprint for the two-slice reprove without
   weakening statement commitments.
2. Fuse additional model-faithful d128 block relations under the same proof
   plumbing and check whether amortization improves the ratio.
3. Split the typed accounting by FRI samples, OODS samples, queried values, and
   trace decommitments to identify the dominant remaining byte source.
4. Keep a strict no-claim boundary until there is either a full-block native
   proof object or a matched external benchmark.

## First Blocker

`component-native reproving closes most of the 12,688-to-6,900 typed-byte gap,
but the checked proof is still 9,056 local typed bytes, 2,156 bytes above
NANOZK's paper-reported d128 block-proof row`

## Non-Claims

- Not a NANOZK proof-size win.
- Not a matched NANOZK benchmark.
- Not locally reproduced NANOZK evidence.
- Not native verifier execution of the selected inner Stwo proofs.
- Not recursion or proof-carrying data.
- Not a native full d128 transformer-block proof.
- Not upstream Stwo proof serialization.
- Not timing evidence.
- Not full transformer inference.
- Not production-ready zkML.

## Evidence

- Input:
  `docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json`
- Proof envelope:
  `docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json`
- Gate JSON:
  `docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-gate-2026-05.json`
- Gate TSV:
  `docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-gate-2026-05.tsv`
- Gate:
  `scripts/zkai_d128_component_native_two_slice_reprove_gate.py`
- Tests:
  `scripts/tests/test_zkai_d128_component_native_two_slice_reprove_gate.py`
- Rust module:
  `src/stwo_backend/d128_native_component_two_slice_reprove.rs`
- CLI:
  `src/bin/zkai_d128_component_native_two_slice_reprove.rs`

The gate rejects `19 / 19` source, metric, comparison, overclaim,
record-stream, validation-command, and payload-commitment mutations.

## Reproduce

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- build-input docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- prove docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- verify docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json
python3 scripts/zkai_d128_component_native_two_slice_reprove_gate.py --write-json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-gate-2026-05.tsv
python3 -m py_compile scripts/zkai_d128_component_native_two_slice_reprove_gate.py scripts/tests/test_zkai_d128_component_native_two_slice_reprove_gate.py
python3 -m unittest scripts.tests.test_zkai_d128_component_native_two_slice_reprove_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_component_two_slice_reprove --lib
cargo +nightly-2025-07-14 fmt --check
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
