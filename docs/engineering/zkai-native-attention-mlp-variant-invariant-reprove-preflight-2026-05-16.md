# zkAI Native Attention+MLP Variant-Invariant Reprove Preflight - 2026-05-16

## Result

This gate attacks issue #636: can we immediately reprove duplicate and compact
native attention-to-d128 adapter variants under a variant-invariant or
multi-transcript policy?

The answer is a useful NO-GO:

- NO-GO: the current source cannot yet run the source-backed compact-vs-duplicate
  reprove experiment;
- GO: the blocker is now source-pinned, not hand-wavy;
- GO: the gate records the exact stable measurement budget from the previous
  transcript-stable comparison;
- GO: mutation tests reject fake reprove support, compact-frontier promotion,
  NANOZK promotion, fake selector presence, source hash drift, and erased
  path-sensitive budget.

Human interpretation: the compact-adapter idea is still alive, but the current
backend is not ready to measure it honestly. The source still duplicates
`adapter_trace(input)?` into both the preprocessed trace and the base trace, and
the input validation pins the duplicate `1,536`-cell adapter trace shape. There
is no duplicate-vs-compact selector and no per-variant compact proof artifact.

## Numbers

Carried forward from the checked transcript-stable comparison:

- current frontier: `41,932` typed bytes;
- duplicate-adapter label control: `43,228` typed bytes;
- compact-adapter label control: `42,492` typed bytes;
- reported compact saving: `736` typed bytes;
- stable direct opened-value floor: `112` typed bytes;
- path-sensitive bytes that still need a real reprove: `624`;
- NANOZK paper-reported d128 block row: `6,900` bytes;
- compact frontier promoted: `false`;
- NANOZK win claimed: `false`.

The important point is the split:

- `112` bytes are the defensible floor today;
- `624` bytes are still in transcript/Merkle path-sensitive territory.

That means comparison work should stop until the backend can emit real
duplicate and compact proof artifacts.

## Source Blockers

The preflight pins four blockers:

- the single-proof source extends `adapter_trace(input)?` into the preprocessed
  trace;
- the same source extends `adapter_trace(input)?` into the base trace;
- input validation pins `adapter_trace_cells` to the duplicate `1,536`-cell
  constant;
- the CLI/input/envelope surface has no compact-vs-duplicate adapter selector.

This is why issue #636 cannot honestly close yet. The next PR must be source
work, not another accounting-only comparison.

## Next Required PR

Add a source-backed compact adapter selector:

1. add explicit duplicate and compact adapter modes with versioned statement
   labels;
2. make compact mode prove only the non-public adapter witness columns while
   referencing fixed columns;
3. emit separate duplicate and compact proof envelopes;
4. emit per-variant local binary accounting and record-stream fingerprints;
5. compare under a declared multi-transcript policy or a defensible
   variant-invariant transcript policy.

GO after that PR: compact verifies, preserves value binding, emits source
artifacts and query fingerprints, and stays smaller than duplicate under the
declared policy.

NO-GO after that PR: compact fails verification, weakens value binding, or only
wins through path-sensitive query churn.

## Non-Claims

- This is not a compact-adapter proof artifact.
- This is not a transcript-stable compact-adapter proof-size win.
- This is not a replacement for the current native attention+MLP frontier.
- This is not a NANOZK proof-size win.
- This is not a matched external zkML benchmark.
- This is not timing evidence.
- This is not a full transformer block proof.
- This is not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-native-attention-mlp-variant-invariant-reprove-preflight-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-variant-invariant-reprove-preflight-2026-05.tsv`
- `scripts/zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate.py`
- `scripts/tests/test_zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate.py`

## Validation

```bash
python3 scripts/zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-variant-invariant-reprove-preflight-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-variant-invariant-reprove-preflight-2026-05.tsv
python3 -m py_compile scripts/zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate.py scripts/tests/test_zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate.py
python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
