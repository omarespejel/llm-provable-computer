# Appendix Artifact Index

- Bundle dir: `docs/paper/artifacts/stwo-repeated-richer-multi-interval-gemma-v1-2026-04-22`
- Scope: repeated multi-interval explicit accumulation plus folded prototype plus richer verifier-bound repeated-window family artifact
- Frozen manifest entries:
  - `bundle_version: stwo-repeated-richer-multi-interval-gemma-v1`
  - `repo_root: .`
  - `nightly_toolchain: +nightly-2025-07-14`
  - `bundle_dir: docs/paper/artifacts/stwo-repeated-richer-multi-interval-gemma-v1-2026-04-22`
  - `generator_script: scripts/paper/generate_stwo_repeated_richer_multi_interval_gemma_bundle.sh`
  - `generator_script_sha256: 6d4c11bd49a7133024d484f11b6cd6120051dec2276cd079115075f7c6352b50`
  - `generator_git_revision: 35b7097c9b350c075b5f9ba6ec093cc41a3a3147`
  - `generator_git_branch: codex/phase107-repeated-richer-family`
  - `generator_git_commit_date: 2026-04-22T01:45:44+03:00`
  - `generator_worktree_state: clean`
  - `generator_allow_dirty_build: 0`
  - `gemma_proof: gemma-block-v4.stark.json`
  - `single_window_artifact: single-window-multi-interval-gemma-richer-family-accumulation.stwo.json`
  - `repeated_artifact: repeated-multi-interval-gemma-richer-family-accumulation.stwo.json`
  - `folded_repeated_artifact: folded-repeated-multi-interval-gemma-accumulation-prototype.stwo.json`
  - `folded_richer_repeated_artifact: folded-repeated-multi-interval-gemma-richer-family.stwo.json`
  - `canonical_sha256_file: sha256sums.txt`
  - `provenance_sha256_file: provenance_sha256sums.txt`
  - `auxiliary_benchmarks_file: benchmarks.tsv`
  - `auxiliary_commands_log: commands.log`
  - `auxiliary_comparison_file: comparison.tsv`
  - `total_windows: 2`
  - `intervals_per_window: 2`
  - `interval_total_slices: 2`
  - `token_position_start: 0`
  - `token_position_stride: 1`
  - `start_block_index: 2`
  - `scope: single-window multi-interval baseline plus repeated-window explicit accumulation plus folded prototype plus richer verifier-bound repeated-window family artifact over one shared S-two proof surface`

## Table

| Quantity | Value |
|---|---:|
| Shared execution proof bytes | `90432` |
| Single-window multi-interval JSON bytes | `1032820` |
| Explicit repeated multi-interval JSON bytes | `1034361` |
| Folded repeated multi-interval prototype JSON bytes | `4740` |
| Folded richer repeated multi-interval JSON bytes | `5554` |
| Folded prototype / explicit ratio | `0.004583` |
| Richer-family / explicit ratio | `0.005369` |
| Explicit repeated-window vs naive duplication savings | `1031279` bytes |
| Phase106 folded group count | `1` |
| Phase107 folded richer group count | `1` |

## Interpretation

The Phase106 folded prototype is still the smallest repeated-window surface. Phase107 intentionally adds richer verifier-checked transformer-family structure back on top of that folded handoff. The result should remain much smaller than the explicit Phase105 repeated source artifact while carrying more repeated-window family information than the bare folded prototype alone.
