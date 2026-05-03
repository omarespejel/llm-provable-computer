# d128 Recursive/PCD Route Selector

Date: 2026-05-03

## Decision

`NO_GO_LOCAL_D128_RECURSIVE_PCD_BACKEND_TODAY`

Issue `#420` asked for the smallest executable recursive or proof-carrying-data
backend target: the d128 `rmsnorm_public_rows` plus
`rmsnorm_projection_bridge` two-slice contract.

The route selector records a bounded no-go for the local Stwo-native route
today. The blocker is not the statement contract. The blocker is the missing
backend object:

`NO_EXECUTABLE_NESTED_VERIFIER_BACKEND_FOR_D128_TWO_SLICE_TARGET`

A real GO still requires an executable recursive or PCD proof object, a verifier
handle, and public-input binding for:

- `two_slice_target_commitment`;
- selected slice statement commitments;
- selected source evidence hashes;
- verifier domain and backend version.

## What Remains GO

The two local accumulator routes remain valid, but they stay explicitly
pre-recursive:

| Route | Status | Boundary |
|---|---|---|
| d128 two-slice non-recursive accumulator | `GO_PRE_RECURSIVE_INTEGRITY_ONLY` | `NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF` |
| d128 full-block non-recursive accumulator | `GO_PRE_RECURSIVE_INTEGRITY_ONLY` | `NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF` |

These objects bind statement and source-evidence commitments. They must not be
reported as recursive compression, PCD, or a compressed cryptographic verifier
object.

## Route Table

| Route | Status | Usable today | Next action |
|---|---:|---:|---|
| Local Stwo nested-verifier AIR | `NO_GO_MISSING_NESTED_VERIFIER_AIR` | no | Design or import a verifier-in-AIR/circuit for the two selected d128 slice verifiers. |
| Local Stwo/PCD outer proof | `NO_GO_MISSING_OUTER_PCD_PROOF_SYSTEM` | no | Add a PCD/IVC backend that proves the selected verifier checks and binds the same public inputs. |
| Two-slice non-recursive accumulator | `GO_PRE_RECURSIVE_INTEGRITY_ONLY` | yes | Keep as a source-bound handoff object; do not report recursive metrics from it. |
| Full-block non-recursive accumulator | `GO_PRE_RECURSIVE_INTEGRITY_ONLY` | yes | Keep as the strongest local statement-bound d128 handoff object. |
| Proof-native two-slice compression without recursion | `GO_PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION` | yes | Use as a smaller verifier-facing transcript/public-input object; do not report recursive metrics from it. |
| External zkVM statement-receipt adapter | `RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO` | no | Map the exact two-slice statement into a zkVM receipt adapter and test relabeling. |
| External SNARK/IVC statement adapter | `RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO` | no | Test whether a SNARK/IVC receipt can bind the same d128 two-slice statement contract. |
| Starknet settlement adapter | `DEFERRED_UNTIL_LOCAL_OR_EXTERNAL_PROOF_OBJECT_EXISTS` | no | Wait until one proof object exists for the same public-input contract. |

## SOTA Context

The current external ecosystem makes this route selector stricter, not weaker.
StarkWare's public S-two material describes recursive proving as part of the
broader S-two direction, and Starknet documentation describes SHARP proof
aggregation using proof recursion. That does not imply this repository already
has a nested-verifier AIR or PCD artifact for the d128 slice verifiers.

General zkVM systems provide a plausible external-adapter route. RISC Zero
receipts bind a journal to execution of a specific image ID, and SP1 exposes
proof/metadata and recursion-related prover surfaces. Those are useful future
adapter targets, but they are not local Stwo-native recursion and are not GO
until the exact d128 two-slice statement contract is encoded and mutation-tested.

Sources checked for route context:

- StarkWare S-two prover announcement: <https://starkware.co/blog/s-two-prover/>
- StarkWare recursive circuit proving note: <https://starkware.co/blog/minutes-to-seconds-efficiency-gains-with-recursive-circuit-proving/>
- Starknet SHARP documentation: <https://docs.starknet.io/architecture/sharp>
- RISC Zero receipt documentation: <https://docs.rs/risc0-zkvm/latest/risc0_zkvm/struct.Receipt.html>
- SP1 prover crate surface: <https://docs.rs/sp1-prover>

## Mutation Coverage

The gate rejects `24 / 24` mutation cases across:

- source two-slice and full-block accumulator result or claim-boundary drift;
- recursive/PCD no-go result drift;
- route relabeling from no-go or candidate into GO;
- route removal and blocker removal;
- next-route drift back to local recursion without an artifact;
- recursive proof-size, verifier-time, and proof-generation-time metric
  smuggling;
- top-level decision/result/issue drift;
- weakened GO criterion, non-claim removal, validation-command drift, and
  unknown-field injection.

## Recommendation

Do not keep spending the next sprint trying to extract local Stwo-native
recursion from the current repository surface. The local route is blocked before
metrics.

The next two useful research moves are:

1. external zkVM statement-receipt adapter for the exact d128 two-slice
   contract, tracked in issue `#422`;
2. cryptographic backend work over the proof-native two-slice compression
   contract, tracked in issue `#426`.

The first tests proof-system independence. The second tests whether the now
checked issue `#424` compressed object can be bound by an executable proof,
receipt, PCD, or recursive-verifier backend without changing the statement
boundary.

## Current-State Postscript After Issue `#424`

Issue `#424` now has a narrow GO in
`docs/engineering/zkai-d128-proof-native-two-slice-compression-2026-05-03.md`.
That follow-up compresses the two-slice transcript/public-input contract into a
smaller verifier-facing object, but it does not change this route selector's
recursive/PCD conclusion: local Stwo-native recursion remains blocked before
metrics.

## Reproduce

```bash
python3 scripts/zkai_d128_recursive_pcd_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-recursive-pcd-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-recursive-pcd-route-selector-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_recursive_pcd_route_selector_gate
python3 -m py_compile scripts/zkai_d128_recursive_pcd_route_selector_gate.py \
  scripts/tests/test_zkai_d128_recursive_pcd_route_selector_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
