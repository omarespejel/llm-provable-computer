# Appendix Artifact Index

- Bundle dir: `docs/paper/artifacts/stwo-richer-multi-interval-gemma-v1-2026-04-21`
- Scope: explicit multi-interval accumulation plus folded prototype plus richer verifier-bound family artifact
- Frozen manifest entries:
  - `bundle_version: stwo-richer-multi-interval-gemma-v1`
  - `repo_root: .`
  - `nightly_toolchain: +nightly-2025-07-14`
  - `bundle_dir: docs/paper/artifacts/stwo-richer-multi-interval-gemma-v1-2026-04-21`
  - `generator_script: scripts/paper/generate_stwo_richer_multi_interval_gemma_bundle.sh`
  - `generator_script_sha256: 5b3669682815d907beb2e9b78f6e7548699482febce80f502ee82c516b177219`
  - `generator_git_revision: 0f29208aed5d8de9e6f219093929fa3ed6fece9d`
  - `generator_git_branch: codex/phase102-104-gemma-accumulation`
  - `generator_git_commit_date: 2026-04-21T20:59:34+03:00`
  - `generator_worktree_state: clean`
  - `generator_allow_dirty_build: 0`
  - `gemma_proof: gemma-block-v4.stark.json`
  - `single_interval_explicit_artifact: single-interval-repeated-gemma-slice-accumulation.stwo.json`
  - `single_interval_folded_artifact: single-interval-folded-gemma-slice-accumulation.stwo.json`
  - `single_interval_richer_family_artifact: single-interval-folded-gemma-richer-slice-family.stwo.json`
  - `multi_interval_artifact: multi-interval-gemma-richer-family-accumulation.stwo.json`
  - `folded_multi_interval_artifact: folded-multi-interval-gemma-accumulation-prototype.stwo.json`
  - `folded_richer_multi_interval_artifact: folded-multi-interval-gemma-richer-family.stwo.json`
  - `canonical_sha256_file: sha256sums.txt`
  - `provenance_sha256_file: provenance_sha256sums.txt`
  - `auxiliary_benchmarks_file: benchmarks.tsv`
  - `auxiliary_commands_log: commands.log`
  - `auxiliary_comparison_file: comparison.tsv`
  - `total_intervals: 4`
  - `interval_total_slices: 4`
  - `token_position_start: 0`
  - `token_position_stride: 1`
  - `start_block_index: 2`
  - `scope: explicit multi-interval accumulation plus folded prototype plus richer verifier-bound family artifact over one shared S-two proof surface`

## Table

| Quantity | Value |
|---|---:|
| Shared execution proof bytes | `90432` |
| Explicit multi-interval JSON bytes | `1036298` |
| Folded multi-interval prototype JSON bytes | `5214` |
| Folded richer multi-interval JSON bytes | `7100` |
| Folded prototype / explicit ratio | `0.005031` |
| Richer-family / explicit ratio | `0.006851` |
| Explicit multi-interval vs naive duplication savings | `3090402` bytes |
| Phase101.5 folded group count | `2` |
| Phase102 folded richer group count | `2` |

## Interpretation

The Phase101.5 folded prototype is still the smaller surface. Phase102 intentionally adds richer verifier-checked structure back on top of that folded handoff. The result is still much smaller than the explicit Phase99 multi-interval source artifact while carrying more transformer-shaped family information than the bare folded prototype alone.
