# S-two Upstream Sync Audit

Snapshot date: **April 21, 2026**.

This note records the local-versus-upstream S-two status after refreshing the
local `stwo-cairo` inspection clones and re-checking the published `stwo`
crate line.

## Repository pin status

The repository currently pins the Rust proving crates in the repo-root
`Cargo.toml` to:

- `stwo = 2.2.0`
- `stwo-constraint-framework = 2.2.0`

These are still the active backend crates consumed by the experimental
`stwo-backend` feature in this repository.

Published crate status on April 21, 2026:

- `cargo info stwo` reports version `2.2.0`
- `cargo info stwo-constraint-framework` reports version `2.2.0`

So there is no newer published crate release to move to yet. Any upgrade beyond
this point would require a git pin to an unreleased upstream commit rather than
a semver crate bump.

## Upstream branch posture

There are two different upstream moving surfaces:

1. `starkware-libs/stwo`
   - published release tag in active use here: `v2.2.0`
   - moving development branch: `dev`
   - `dev` is only one commit ahead of `v2.2.0` at the time of this audit, and
     that delta is CI-facing (`93dd93e04 Add CI check that ensure-verifier-no_std/Cargo.lock is up-to-date. (#1387)`).
2. `starkware-libs/stwo-cairo`
   - moving branch: `main`
   - local inspection clones were previously stale and are now refreshed.

The practical result is important: the repository is already on the latest
published `stwo` crate line, while the meaningful upstream drift is currently in
`stwo-cairo`, not in a newer released `stwo` crate.

## Local clone drift observed

Local clones audited:

- `/Users/espejelomar/StarkNet/zk-ai/stwo-cairo`
- `/Users/espejelomar/StarkNet/zk-ai/stwo-cairo-src`

Observed before refresh:

- local `HEAD`: `cf18bdf4710bd084dbcb0af90102e635d5de1935`
- local top commit: `2026-02-12 cf18bdf47 Bump stwo. (#1637)`
- `origin/main`: `01eb5d60767539b02466ec4163723a76ffec3481`
- upstream top commit: `2026-04-19 01eb5d607 Bump stwo and replaces panics with errors. (#1749)`

Observed after refresh:

- local `HEAD`: `01eb5d60767539b02466ec4163723a76ffec3481`
- local branch status: clean on `main`

The refresh required backing up one untracked generated artifact from the old
`cairo-prove/example/` tree:

- `/Users/espejelomar/StarkNet/zk-ai/stwo-cairo-src-backups/example_proof-2026-04-21.json`

That backup is external to this repository and was moved only because upstream
deleted the old `cairo-prove` subtree.

## Upstream capabilities that matter for this repository

The refreshed `stwo-cairo` line adds or clarifies several capabilities relevant
to the next backend-widening sprint:

1. The old `cairo-prove` CLI is gone. The README now points developers to
   `proving-utils` and `scarb prove` for Cairo proving flows.
2. The Cairo prover line now includes support for:
   - precomputed twiddles,
   - precomputed preprocessed trace polys,
   - explicit prover memory-pool entry points,
   - generated component integration,
   - additional small-memory / `memory_id_to_small` surfaces,
   - `verify_triple_sum` integration.
3. The Cairo verifier line now includes:
   - `fold_step`-aware FRI handling,
   - leaf-packing-aware verification paths,
   - new FRI tests around those surfaces.
4. The latest top commit tightens error posture by replacing some panic-driven
   paths with error returns.

For this repository, the meaningful takeaway is not "new recursion is now ready
for arbitrary custom AIRs." The meaningful takeaway is that the live upstream
surface is stronger for:

- lookup-heavy custom proving,
- explicit preprocessing reuse,
- tighter verifier behavior,
- and more efficient witness/prover plumbing.

## Practical implication for this repository

The experimental backend in `provable-transformer-vm` is pinned to published
`stwo` crates, not to the local `stwo-cairo` working tree. So:

1. There is no immediate crate-version bump to make inside this repository; the
   published `stwo` surface is already at the latest semver release we can use
   without switching to a git dependency.
2. The local engineering assumptions should be updated:
   - stop referring to `cairo-prove` as the current upstream utility surface,
   - treat `proving-utils` and `scarb prove` as the live Cairo-facing route,
   - treat `fold_step`, leaf packing, precomputed twiddles/trees, and memory
     pool entry points as real upstream signals for later custom-AIR work.
3. The refreshed clones strengthen the case for moving the main breakthrough
   route toward tensor-native, lookup-aware S-two proofs rather than adding more
   VM-manifest wrapper layers.

## Audit conclusion

1. Keep the repository's current `stwo = 2.2.0` and
   `stwo-constraint-framework = 2.2.0` crate pins explicit until a deliberate
   git-pin or future semver release upgrade lands.
2. Treat the local `stwo-cairo` refresh as complete for this audit: both local
   inspection clones now match upstream `main` at `01eb5d607`.
3. Update repository-facing assumptions and docs to reflect the removal of the
   old `cairo-prove` path in upstream `stwo-cairo`.
4. Do not block tensor-native phase work on unreleased generic recursion APIs.
   The meaningful live upstream signal is improved lookup/preprocessing/prover
   plumbing, not public custom-recursion closure.
5. Treat this note as a narrow engineering audit, not as a benchmark or proof
   of upstream recursion readiness.

## Phase89 decision

Phase89 is complete when the repository internalizes the refreshed upstream
facts correctly:

- latest published `stwo` crates: still `2.2.0`,
- active upstream `stwo` development branch: `dev`,
- meaningful clone drift and capability movement: `stwo-cairo main`,
- next engineering priority: tensor-native, lookup-aware S-two work on top of
  the current crate line.
