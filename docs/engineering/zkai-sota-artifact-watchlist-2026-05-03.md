# zkAI SOTA artifact watchlist gate - 2026-05-03

## Question

Which current zkML, zkAI, zkVM, and settlement systems have enough public
artifacts to support a reproducible statement-binding adapter row or matched
comparison, and which remain source-backed context only?

## Decision

**GO for a checked artifact watchlist.**

This is not a benchmark and not a leaderboard. It is a comparison-discipline
artifact for issue `#419`: before a public system becomes a paper-facing adapter
or comparator row, the repository must record whether baseline verification and
metadata/statement mutation are actually reproducible.

## Human-readable result

The useful discovery is not that one external project is weak. It is that the
field is currently split across different object types:

- EZKL, snarkjs, and JSTprove/Remainder already support local statement-envelope
  adapter rows in this repository.
- The native Stwo d128 path supports a statement-bound receipt and accumulator,
  but not recursive proof compression.
- DeepProve-1, NANOZK, Jolt Atlas, and Giza/LuminAIR are important SOTA context,
  but they do not currently give this repository a public proof plus verifier
  input bundle that can run the same relabeling benchmark.
- Obelyzk is useful deployment calibration, not a local verifier-time row.
- RISC Zero, SP1, and SNIP-36 are relevant to receipt and settlement design, but
  should not be treated as zkML throughput comparators without matched workloads.
- The zkVM receipt angle is worth a separate follow-up and is tracked in issue
  `#422`.

That means the next honest research step remains issue `#420`: build or cleanly
no-go an executable two-slice recursive/PCD backend. External rows should be
added only when proof bytes, verifier inputs, public statement fields, and
mutation tests are reproducible.

## Checked artifact

Machine-readable outputs:

- `docs/engineering/evidence/zkai-sota-artifact-watchlist-2026-05.json`
- `docs/engineering/evidence/zkai-sota-artifact-watchlist-2026-05.tsv`

The JSON records:

- 12 systems across SNARK, GKR/sum-check, STARK, zkVM, and settlement axes;
- 3 empirical statement-envelope adapter rows;
- 4 source-backed context rows;
- 1 deployment-calibration row;
- 3 watchlist rows;
- 12 negative mutation checks for overclaim surfaces.

## Classification rule

A system gets an empirical row only when all of these are true:

1. public proof artifact or local fixture is available;
2. verifier inputs or public values are available;
3. baseline verification is reproducible;
4. statement or metadata mutation is reproducible;
5. the row is scoped to the same object being compared.

If only paper, blog, source, or reported numbers are available, the system stays
source-backed context. That is useful, but it is not an empirical adapter row.

## SOTA read as of this gate

| System | Gate status | Paper use |
|---|---|---|
| EZKL | `EMPIRICAL_STATEMENT_ADAPTER_ROW` | External statement-envelope adapter baseline. |
| snarkjs | `EMPIRICAL_STATEMENT_ADAPTER_ROW` | Second SNARK statement-envelope adapter. |
| JSTprove/Remainder | `EMPIRICAL_STATEMENT_ADAPTER_ROW` | GKR/sum-check shaped statement-envelope adapter. |
| native Stwo d128 receipt | `LOCAL_STATEMENT_RECEIPT_ONLY` | Local d128 receipt/accumulator evidence, not external SOTA. |
| DeepProve-1 | `SOURCE_BACKED_MODEL_SCALE_CONTEXT_ONLY` | Model-scale context until public proof/verifier bundle exists. |
| NANOZK | `SOURCE_BACKED_COMPACT_CALIBRATION_ONLY` | Compact-object calibration only, not matched local benchmark. |
| Jolt Atlas | `SOURCE_BACKED_MODEL_SCALE_CONTEXT_ONLY` | Lookup-centric architecture context until artifacts are reproducible. |
| Giza/LuminAIR | `SOURCE_BACKED_CONTEXT_ONLY` | STARK-native graph-to-AIR context. |
| Obelyzk | `DEPLOYMENT_CALIBRATION_ONLY` | Starknet deployment calibration, not local verifier-time comparison. |
| RISC Zero | `ZKVM_RECEIPT_WATCHLIST` | Receipt/action binding watchlist, not zkML throughput row. |
| SP1 | `ZKVM_RECEIPT_WATCHLIST` | Receipt/action binding watchlist, not zkML throughput row. |
| SNIP-36 | `SETTLEMENT_API_WATCHLIST` | Settlement interface watchlist until local `proof_facts` adapter exists. |

## Mutation discipline

The gate rejects these overclaims:

- DeepProve-1 promoted to empirical adapter;
- NANOZK promoted to matched benchmark;
- Jolt Atlas baseline verification overclaimed;
- Obelyzk treated as local verifier-time comparison;
- RISC Zero treated as zkML throughput row;
- SNIP-36 treated as local deployment evidence;
- empirical adapter evidence removed;
- primary source downgraded away from HTTPS;
- stale checked date;
- system inventory removal;
- non-claim removal;
- stale systems commitment after edit.

## Validation

```bash
python3 scripts/zkai_sota_artifact_watchlist_gate.py \
  --write-json docs/engineering/evidence/zkai-sota-artifact-watchlist-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-sota-artifact-watchlist-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_sota_artifact_watchlist_gate
python3 scripts/paper/paper_preflight.py --repo-root .
```

## Claim boundary

This gate supports a stronger paper posture because it prevents lazy comparison.
It does not prove we beat public zkML systems. It says exactly which public
systems can be reproduced through our statement-envelope protocol today and
which systems remain roadmap context until public artifacts are sufficient.
