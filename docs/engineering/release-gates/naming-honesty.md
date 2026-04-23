# Naming honesty for fixtures and bundles

The active S-two proof surface proves a 25-instruction VM under a Stwo-side
AIR with shared lookup and decoding manifests layered on top. It does not
prove a transformer in any standard sense.

The tensor-shaped frontend (`src/model.rs`) compiles each `.tvm` instruction
into a deterministic FFN block; the public verifier checks that this frontend
agrees with the native interpreter step-for-step under re-execution. That
agreement is real evidence and is independently regression-tested. It is not
the same thing as proving a learned transformer or a standard-softmax inference.

This file pins the naming policy that keeps the public-facing surface honest.

## Policy

A fixture, manifest, bundle, or artifact name MAY reference a real model
family (e.g. "Gemma") if and only if the underlying `.tvm` program faithfully
implements that model family's primitive operations on real inputs. A fixture
that hard-codes the expected output of the lookup it claims to attest does NOT
qualify.

Every other fixture / artifact MUST use a name that describes what the
underlying program actually does. The accepted prefixes are:

- `linear_block_*.tvm` — sequences of LOAD / MULM / ADDM that compute scalar
  dot products, with no claim of attention semantics.
- `lookup_fixture_*.tvm` — programs that hard-code the expected lookup pair
  for shared-table proofs.
- `arithmetic_*.tvm` — small-arithmetic test programs.

## Fixtures requiring rename

The following fixtures currently use the `gemma_block_*` prefix but compute
hand-coded scalar dot products plus pre-computed lookup pairs. They do not
implement a Gemma block. Their names create an impression that the proofs
do not deliver.

| Current name              | Honest replacement                       | What the program does                                                                                  |
| ------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `programs/gemma_block_v1.tvm` | `programs/linear_block_v1.tvm`         | scalar `q · k` style dot products with two memory cells                                                |
| `programs/gemma_block_v2.tvm` | `programs/linear_block_v2.tvm`         | same shape, slightly different memory layout                                                           |
| `programs/gemma_block_v3.tvm` | `programs/linear_block_v3.tvm`         | adds a `residual` projection step                                                                       |
| `programs/gemma_block_v4.tvm` | `programs/linear_block_v4_with_lookup.tvm` | dot products + four hard-coded shared-lookup pairs (norm/activation rows). The lookup pairs are constants in the program; the proof attests "the program that hard-codes these pairs writes them," nothing about Gemma. |

Renaming the `.tvm` files invalidates every frozen bundle that cites them by
basename and every CLI doc snippet that names them. The path forward is:

1. Land the renames on a `linear-block-naming` branch.
2. Regenerate every cited bundle under the renamed fixtures, with the
   `publication-v1` STARK profile (`docs/engineering/release-gates/publication-profile.md`).
3. Bump every artifact's `*_version` constant by one minor and add a note
   to the release gate that the prior frozen bundles are superseded.
4. Update the README "Common Commands" section to use the new names.

The corresponding Stwo-side artifact and constant identifiers should drop
the substring `gemma` and use `linear_block` / `lookup_fixture` to match.
This is mechanical: every `STWO_*GEMMA*` constant maps to `STWO_*LINEAR_BLOCK*`
or `STWO_*LOOKUP_FIXTURE*`. See:

```
src/stwo_backend/tensor_native_artifact.rs   STWO_GEMMA_BLOCK_*
src/stwo_backend/recursion.rs                STWO_*GEMMA*_PHASE*
docs/paper/artifacts/stwo-*-gemma-*-2026-04-21/
scripts/paper/generate_stwo_*_gemma_*_bundle.sh
```

The renames are out of scope for the current commit because they require
re-running the full Stwo bundle generator under the publication-v1 profile,
which is a multi-hour run on the CI builder. Schedule them as the next
release-gate commit and gate publication on their landing.

## Tests

A new top-level test will assert that no `*.tvm` filename under `programs/`
contains the substring `gemma` once the renames land. The test is staged
behind a feature flag now so it can be flipped to the active gate in the same
commit that removes the last legacy fixture name.

## What stays unchanged

- The transformer/native equivalence-check semantics of the existing prover.
- The Stwo backend behavior. Renames are surface-level.
- The `statement-v1` semantic scope and its constants.
