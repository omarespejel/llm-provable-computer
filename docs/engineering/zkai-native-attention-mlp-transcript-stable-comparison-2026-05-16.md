# zkAI Native Attention+MLP Transcript-Stable Comparison - 2026-05-16

## Result

This gate attacks issue #633: can the compact-adapter proof-size lead be
promoted without being fooled by Fiat-Shamir transcript or Merkle path churn?

The answer is useful, but conservative:

- NO-GO: no compact-adapter variant is transcript-stable enough to replace the
  current `41,932` typed-byte frontier;
- GO: the prior `736` typed-byte label-control saving is decomposed into
  direct opened-value savings versus transcript/path-sensitive savings;
- GO: the gate records why grouped byte counts alone are not a query inventory;
- GO: overclaim mutations reject frontier promotion, NANOZK promotion, fake
  query inventory, and source-artifact drift.

Human interpretation: the adapter compression idea is still alive, but most of
the small saving is in the part of a proof that can move when transcript labels
or sampled query paths move. That is exactly the place where we should be
suspicious before promoting a frontier result.

## Numbers

Current checked native-adapter frontier:

- typed proof-field bytes: `41,932`;
- JSON proof bytes: `119,790`;
- current two-proof frontier: `40,700` typed bytes;
- NANOZK paper-reported d128 row: `6,900` bytes;
- current record-stream fingerprint:
  `4f1b230afc4f7fec71ce632faa2b0b9512276467aa9dd05f48cd1fba4ba581f4`.

Label-control compact adapter comparison:

- duplicate-adapter label-control: `43,228` typed bytes;
- compact-base label-control: `42,492` typed bytes;
- reported typed saving: `736` bytes;
- direct opened-value saving: `112` bytes;
- FRI/Merkle path-sensitive saving: `624` bytes;
- path-sensitive share: `84.7826%`.

Legacy-label microprobe:

- typed saving versus current frontier: `704` bytes;
- direct opened-value saving: `112` bytes;
- FRI/Merkle path-sensitive saving: `592` bytes;
- path-sensitive share: `84.0909%`.

Unconstrained compact control:

- typed saving versus duplicate-adapter label-control: `112` bytes;
- direct opened-value saving: `112` bytes;
- path-sensitive saving: `0` bytes.

Referenced compact versus unconstrained compact:

- typed saving: `624` bytes;
- direct opened-value saving: `0` bytes;
- path-sensitive saving: `624` bytes.

This is the key research signal: the stable-looking floor is only `112` typed
bytes today. The larger `736` byte signal is still interesting, but it lives
mostly in path-sensitive proof plumbing and needs a stable reprove or
multi-transcript policy.

## Stability Policy

The gate treats a proof-size comparison as promotable only if it has:

- one source artifact per variant;
- pinned proof backend and statement labels, or an explicit variant-invariant
  transcript policy;
- statement and public-instance commitments;
- grouped typed proof-field accounting;
- a query-inventory fingerprint.

The current artifact has a pinned record-stream fingerprint from local binary
accounting. The local compact and duplicate adapter variants do not yet have
their own proof artifacts or query inventories, so none of the comparisons are
promotable.

## Why This Matters

This prevents the research loop from fooling itself. Small native proof-size
deltas can be dominated by query positions and Merkle path overlap. If a
sub-kilobyte win is mostly path-sensitive, it should not become a frontier
claim until both variants are rerun under a stable transcript policy or a
multi-transcript reporting rule.

The next honest attack is still compact adapter compression, but with stricter
measurement:

1. re-run duplicate and compact adapter variants with variant-invariant labels,
   or run multiple transcript seeds;
2. emit per-variant proof artifacts and local binary accounting;
3. record query-inventory fingerprints;
4. promote only if the compact route stays smaller under that policy.

## Non-Claims

- This is not a promoted native attention+MLP frontier.
- This is not a transcript-stable compact-adapter proof-size win.
- This is not a NANOZK proof-size win.
- This is not a matched external zkML benchmark.
- This is not timing evidence.
- This is not a full transformer block proof.
- This is not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-native-attention-mlp-transcript-stable-comparison-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-transcript-stable-comparison-2026-05.tsv`
- `scripts/zkai_native_attention_mlp_transcript_stable_comparison_gate.py`
- `scripts/tests/test_zkai_native_attention_mlp_transcript_stable_comparison_gate.py`

## Validation

```bash
python3 scripts/zkai_native_attention_mlp_transcript_stable_comparison_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-transcript-stable-comparison-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-transcript-stable-comparison-2026-05.tsv
python3 -m py_compile scripts/zkai_native_attention_mlp_transcript_stable_comparison_gate.py scripts/tests/test_zkai_native_attention_mlp_transcript_stable_comparison_gate.py
python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_transcript_stable_comparison_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
