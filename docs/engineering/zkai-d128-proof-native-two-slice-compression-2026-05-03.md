# d128 Proof-Native Two-Slice Compression Gate

Date: 2026-05-03

## Decision

`GO_D128_PROOF_NATIVE_TWO_SLICE_TRANSCRIPT_COMPRESSION`

This gate answers issue `#424`.

The repository now has one compressed verifier-facing object for the d128
two-slice public-input/transcript contract. The result is deliberately narrow:
it is proof-native transcript and public-input compression, not recursive
aggregation, not proof-carrying data, and not STARK-in-STARK verification.

## What Is GO

The compressed object consumes the checked d128 two-slice non-recursive
accumulator and binds the same smallest useful target:

| Field | Value |
|---|---|
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Selected checked rows | `256` |
| Two-slice target commitment | `blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6` |
| Source accumulator commitment | `blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d` |
| Compressed artifact commitment | `blake2b-256:cca7656213e2439236b6ec2fefb7aa57daf6411fc6b3e9dedd27cd4fa7b428c4` |
| Verifier-handle commitment | `blake2b-256:704d117c500f82b109cee00370436af47f487e33e3c95368d0170fd0a31d6641` |
| Claim boundary | `PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION` |

The local verifier handle accepts only if it can recompute and bind:

1. `two_slice_target_commitment`;
2. selected slice statement commitments;
3. selected source evidence hashes;
4. selected public-instance commitments;
5. selected proof-native parameter commitments;
6. verifier domain;
7. required backend version;
8. source accumulator commitment; and
9. source verifier-handle commitment.

## Compression Result

The object is smaller than the source non-recursive accumulator artifact:

| Metric | Value |
|---|---:|
| Source accumulator artifact bytes | `8822` |
| Compressed artifact bytes | `4435` |
| Byte savings | `4387` |
| Compressed/source byte ratio | `0.50272` |
| Timing mode | `not_timed` |

This is an artifact-size result only. It does not report recursive proof size,
recursive verifier time, recursive proof-generation time, or on-chain cost.

## What Remains NO-GO

`NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING`

The first recursive/PCD blocker remains:

> no executable recursive/PCD outer proof backend currently proves the two selected d128 slice-verifier checks inside one cryptographic outer proof

This gate therefore does not close the recursive-proof route. It gives the next
backend a smaller, sharper public-input/transcript object to target.

## Mutation Coverage

The gate rejects `34 / 34` mutation cases, including:

- source accumulator file-hash, payload-hash, result, claim-boundary, and
  accumulator-commitment drift;
- compressed artifact commitment and claim-boundary drift;
- target, selected statement, selected source hash, selected public instance,
  selected proof-native parameter, verifier-domain, backend-version, and source
  accumulator relabeling;
- compressed slice removal, duplication, reordering, and row-count drift;
- compression-metric relabeling;
- verifier-handle commitment, claim-boundary, accepted-artifact, and required
  public-input drift;
- recursive/PCD claim relabeling, recursive metric smuggling, and blocker
  removal;
- parser-level attempts to relabel the result, weaken non-claims, or change
  validation commands.

## Non-Claims

This gate does not claim:

- recursive aggregation of selected slice proofs;
- proof-carrying data;
- STARK-in-STARK verification;
- one cryptographic outer proof over the selected verifiers;
- proof-size evidence for a recursive outer proof;
- verifier-time evidence for a recursive outer proof;
- proof-generation-time evidence for a recursive outer proof;
- aggregation of all six d128 slice proofs;
- matched public zkML benchmark evidence;
- on-chain deployment evidence.

## Reproduce

```bash
python3 scripts/zkai_d128_proof_native_two_slice_compression_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-native-two-slice-compression-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-native-two-slice-compression-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_proof_native_two_slice_compression_gate
python3 -m py_compile scripts/zkai_d128_proof_native_two_slice_compression_gate.py \
  scripts/tests/test_zkai_d128_proof_native_two_slice_compression_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Next Step

The next research step is no longer "can we compress the transcript at all?"
That is now a narrow GO.

The next step is to replace this transcript-compressed object with a real
cryptographic backend:

- a recursive/PCD proof backend over the same public-input contract; or
- an external zkVM/SNARK statement receipt adapter over the same contract; or
- a deliberately scoped no-go identifying the exact missing backend feature.

Tracked follow-up: issue `#426`.

Do not report recursive metrics until one of those proof objects exists.
