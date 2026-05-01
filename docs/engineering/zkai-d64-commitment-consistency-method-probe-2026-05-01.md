# zkAI d64 commitment-consistency method probe - 2026-05-01

## Question

Given the d64 Stwo vector-row surface result, what is the smallest honest
commitment-consistency method for the next native proof PR?

The blocker is not the arithmetic surface. The blocker is proving that private
weight and activation-table rows used by the AIR match the public statement.

## Result

GO for a dual-commitment method:

> Keep the existing publication hashes for audit/export identity, and add a
> proof-native parameter commitment that the native AIR public instance must
> bind.

This is not a proof. It is the checked method choice for issue `#346`.

## Concrete Counts

The checked d64 fixture gives:

- matrix row leaves: `576`
  - gate rows: `256`
  - value rows: `256`
  - down rows: `64`
- committed parameter scalars: `49,216`
- activation-table leaves: `2,049`
- activation lookup rows in the reference block: `256`
- distinct activation-table rows touched by the reference block: `204`
- selected proof-native parameter commitment:
  `blake2b-256:861784bd57c039f7fd661810eac42f2aa1893a315ba8e14b441c32717e65efbc`

## Method Matrix

| Method | Status | Interpretation |
| --- | --- | --- |
| `metadata_only_statement_commitments` | `NO_GO` | Metadata can relabel claims without forcing private witness rows to match them. |
| `publication_hash_inside_air` | `NO_GO_FOR_FIRST_PR` | Directly binding Blake2b/SHA-style hashes inside AIR is the wrong first implementation target. |
| `external_merkle_openings_only` | `NO_GO` | Openings outside the proof do not prove the Stwo witness consumed those rows. |
| `public_parameter_columns` | `POSSIBLE_BUT_EXPENSIVE` | Exact but exposes `49,216` parameter scalars; useful as a debug fallback, not the best private-model path. |
| `dual_publication_and_proof_native_parameter_commitment` | `GO_FOR_NEXT_PR` | Add a proof-native parameter commitment to the statement and bind it in the native proof public instance. |

## Why This Matters

This prevents two easy ways to fool ourselves:

1. Treating the existing publication hashes as if the AIR had verified them.
2. Treating external Merkle openings as if they bind the private proof witness.

Neither is enough. The proof relation must consume a commitment surface that is
native to the proof, and the statement receipt must bind that same surface.

## Next PR Target

The next implementation PR should:

1. Add `proof_native_parameter_commitment` to the d64 statement fixture.
2. Keep the existing publication commitments as audit/export identifiers.
3. Update mutation tests so relabeling the proof-native commitment rejects.
4. Make the native d64 proof public instance bind the proof-native parameter
   commitment before claiming an honest proof.

## Evidence

Machine-readable evidence:

- `docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.json`
- `docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.tsv`

Generator and tests:

- `scripts/zkai_d64_commitment_consistency_method_probe.py`
- `scripts/tests/test_zkai_d64_commitment_consistency_method_probe.py`

## Non-Claims

This is not:

- a Stwo proof,
- a proof-size or timing benchmark,
- a claim that publication hashes are verified inside the AIR,
- a claim that Merkle openings alone bind private witness rows,
- full transformer inference.

## Validation

Focused validation:

```bash
python3 -m py_compile \
  scripts/zkai_d64_commitment_consistency_method_probe.py \
  scripts/tests/test_zkai_d64_commitment_consistency_method_probe.py

python3 -m unittest \
  scripts.tests.test_zkai_d64_commitment_consistency_method_probe \
  scripts.tests.test_zkai_d64_rmsnorm_swiglu_statement_fixture

python3 scripts/zkai_d64_commitment_consistency_method_probe.py \
  --write-json docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.tsv
```

Repository gates before merge:

```bash
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
