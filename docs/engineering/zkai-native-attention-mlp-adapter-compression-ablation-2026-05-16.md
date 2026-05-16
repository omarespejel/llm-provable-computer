# zkAI Native Attention+MLP Adapter Compression Ablation - 2026-05-16

## Result

This gate attacks issue #631: can we reduce the native attention-to-d128 adapter
cost without weakening value binding?

The answer is a useful narrow result, not a new frontier:

- GO: compacting the adapter base trace from `12` columns to `8` columns is a
  real structural saving under a label-control comparison;
- GO: the compact-base label-control saves `736` typed bytes versus the
  duplicate-adapter label-control;
- GO: the legacy-label microprobe would recover `704 / 1,232` typed bytes of
  the current adapter overhead, leaving only `528` typed bytes above the
  two-proof frontier;
- NO-GO: this PR does not replace the current checked frontier because changing
  statement/version labels changes Fiat-Shamir query positions and Merkle path
  overlap;
- NO-GO: this is not a NANOZK comparison or proof-size win.

The human interpretation: the adapter compression idea is alive, but proof-size
measurement is more fragile than we want. Base trace cells went down, but the
exact proof byte count can move because transcript metadata changes the sampled
query set. The next serious step is a transcript-stable comparison harness, then
a compact adapter route can be promoted or rejected cleanly.

## Numbers

Current checked frontier:

- proof object: duplicate adapter base + preprocessed adapter projection;
- adapter trace cells: `1,536`;
- proof JSON bytes: `119,790`;
- typed proof-field bytes: `41,932`;
- gap to two-proof frontier: `1,232` typed bytes;
- gap to NANOZK paper-reported d128 row: `35,032` typed bytes.

Legacy-label compact-base microprobe:

- adapter base trace columns: `8`;
- adapter trace cells: `1,024`;
- proof JSON bytes: `117,416`;
- typed proof-field bytes: `41,228`;
- saving versus current frontier: `704` typed bytes;
- remaining gap to two-proof frontier: `528` typed bytes.

Label-control comparison:

- duplicate-adapter v2 control: `43,228` typed bytes / `124,492` JSON bytes;
- compact-base v2: `42,492` typed bytes / `121,841` JSON bytes;
- compact-base v2 saving: `736` typed bytes / `2,651` JSON bytes;
- adapter trace-cell saving: `512` cells.

The label-control result is the important mechanism signal. It says compacting
the adapter base trace saves real typed proof-field bytes when compared against
a duplicate adapter with the same label family. It does not yet say the current
frontier should be replaced.

## Why This Matters

The previous native adapter-AIR result was correctness-first: it proved the
attention-to-d128 handoff inside the single Stwo proof object, but it cost
`1,232` typed bytes versus the two-proof frontier.

This ablation shows that a meaningful portion of that overhead is attackable.
The compact-base microprobe recovered `57.1429%` of the current overhead in the
legacy-label run. The stricter label-control run recovered `736` typed bytes
structurally.

The blocker is not whether adapter compression can save bytes. It can. The
blocker is whether we can measure and promote it without letting transcript
metadata churn fake progress or hide regressions.

Follow-up issue: `#633` tracks transcript-stable native proof-size comparisons.

## Non-Claims

- This is not a replacement for the current native attention+MLP frontier.
- This is not proof that compact-base adapter is always smaller after label
  changes.
- This is not a NANOZK proof-size win.
- This is not a matched NANOZK workload or benchmark.
- This is not a full transformer block proof.
- This is not timing evidence.
- This is not recursion or proof-carrying data.
- This is not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-native-attention-mlp-adapter-compression-ablation-2026-05.json`
- `docs/engineering/evidence/zkai-native-attention-mlp-adapter-compression-ablation-2026-05.tsv`
- `scripts/zkai_native_attention_mlp_adapter_compression_ablation_gate.py`
- `scripts/tests/test_zkai_native_attention_mlp_adapter_compression_ablation_gate.py`

## Validation

```bash
python3 scripts/zkai_native_attention_mlp_adapter_compression_ablation_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-adapter-compression-ablation-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-adapter-compression-ablation-2026-05.tsv
python3 -m py_compile scripts/zkai_native_attention_mlp_adapter_compression_ablation_gate.py scripts/tests/test_zkai_native_attention_mlp_adapter_compression_ablation_gate.py
python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_adapter_compression_ablation_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
