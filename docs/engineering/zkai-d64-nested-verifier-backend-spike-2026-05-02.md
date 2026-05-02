# d64 nested-verifier backend spike gate - 2026-05-02

## Question

Can the repository actually build an executable outer proof or PCD artifact for
this two-slice nested-verifier contract?

- `rmsnorm_public_rows`
- `rmsnorm_projection_bridge`

The GO criterion is intentionally strict: one checked outer proof or PCD
accumulator must verify the selected slice-verifier checks and bind
`nested_verifier_contract_commitment` as public input.

## Safe checkpoint

The safe working state before this backend spike is:

| Field | Value |
| --- | --- |
| Checkpoint | `main-after-pr-381` |
| `main` commit | `6fae0d115f6554258782d00612c2cecdc376af38` |
| Purpose | rollback checkpoint before executable nested-verifier backend exploration |

## Decision

**Hard NO-GO for a real nested-verifier backend artifact in the current
repository.**

This is not a NO-GO for the research direction. It is a hard boundary on what
can be claimed today: the repo has a checked two-slice public-input contract,
but it does not yet have the executable outer proof, PCD accumulator, verifier
handle, or binding test required to claim recursion or PCD aggregation.

## Result

| Field | Value |
| --- | --- |
| Decision | `NO_GO_D64_TWO_SLICE_NESTED_VERIFIER_BACKEND_ARTIFACT_MISSING` |
| Result | `HARD_NO_GO` |
| Backend result | `NO_GO_EXECUTABLE_OUTER_BACKEND_ARTIFACT_MISSING` |
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Source contract commitment | `blake2b-256:4a02af0e424022e995e17e780d20e3b229d52de8e15427af21630b4dfdf7c4cd` |
| Candidate surfaces inventoried | `8` |
| Required GO artifacts missing | `3` |
| Spike mutation checks | `20 / 20` rejected |

## Candidate inventory

The gate prevents current surfaces from being relabeled as recursive evidence:

| Candidate | Status |
| --- | --- |
| Checked two-slice nested-verifier contract | `CONTRACT_ONLY_NOT_OUTER_PROOF` |
| d64 recursive/PCD aggregation feasibility gate | `AGGREGATION_TARGET_ONLY_NOT_OUTER_PROOF` |
| Phase36 recursive-verifier harness receipt | `HARNESS_RECEIPT_NOT_NESTED_PROOF` |
| Decoding accumulator demos | `PRE_RECURSIVE_ACCUMULATOR_DEMO_NOT_D64_SLICE_VERIFIER_PROOF` |
| Archived Stwo accumulation bundle | `ARCHIVED_DECODING_ARTIFACT_NOT_CURRENT_D64_BACKEND` |
| Required two-slice outer proof artifact | `MISSING_REQUIRED_GO_ARTIFACT` |
| Required two-slice outer verifier handle | `MISSING_REQUIRED_GO_ARTIFACT` |
| Required two-slice outer mutation tests | `MISSING_REQUIRED_GO_ARTIFACT` |

## Exact blocker

The first blocker is:

> no executable outer proof/PCD backend artifact in the current repository can
> prove the selected two d64 slice-verifier checks and bind
> `nested_verifier_contract_commitment` as a public input

The missing backend features are:

- nested verifier program, AIR, or circuit for `rmsnorm_public_rows`;
- nested verifier program, AIR, or circuit for `rmsnorm_projection_bridge`;
- outer proof or PCD accumulator object over those selected verifier checks;
- outer verifier handle for that proof or accumulator object;
- public-input binding inside the outer backend for
  `nested_verifier_contract_commitment`;
- mutation tests against relabeling of the outer proof public inputs.

## Metrics policy

No proof-size, verifier-time, recursive-row-count, compression-ratio, or onchain
cost number is reported here. Those metrics are blocked until a proof or
accumulator object exists.

This matters because several old repository surfaces have useful names such as
"recursive harness" or "accumulator". The gate classifies them explicitly and
refuses to count them as the missing backend.

## Pivot options if this remains blocked

1. **Proof-native two-slice compression:** compress the two-slice receipt into a
   proof-native object without calling it recursion.
2. **Simpler non-recursive accumulator:** build a verifier-facing accumulator
   over the two selected checks and keep proof semantics explicit.
3. **Different backend route:** try an external recursion-capable backend for
   the two-slice statement envelope and keep the result framed as an adapter
   result until Stwo-native recursion exists.

## Non-claims

This result does **not** claim:

- a recursive proof object;
- a PCD accumulator;
- a benchmark;
- proof-size evidence;
- verifier-time evidence;
- six-slice d64 aggregation;
- d128 evidence;
- onchain deployment evidence.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d64-nested-verifier-backend-spike-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d64-nested-verifier-backend-spike-2026-05.tsv`
- Script:
  `scripts/zkai_d64_nested_verifier_backend_spike_gate.py`
- Tests:
  `scripts/tests/test_zkai_d64_nested_verifier_backend_spike_gate.py`

## Reproduce

```bash
just gate-fast

python3 scripts/zkai_d64_nested_verifier_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d64-nested-verifier-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-nested-verifier-backend-spike-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_nested_verifier_backend_spike_gate

python3 scripts/paper/paper_preflight.py --repo-root .

just gate
```
