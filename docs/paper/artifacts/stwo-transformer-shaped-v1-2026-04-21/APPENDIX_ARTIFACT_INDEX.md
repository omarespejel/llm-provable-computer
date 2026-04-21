# Appendix Artifact Index (S-two Transformer-Shaped V1)

## Run Metadata
- Generated at utc: 2026-04-21T11:18:09Z
- Repo root: .
- Git commit: b9365dc13ff8bf6756dc46e0b1bfadf01eaf5e25
- Git commit short: b9365dc
- Git branch: codex/phase85-88-translated-composition-prototype
- Rustc: rustc 1.90.0-nightly (e9182f195 2025-07-13)
- Cargo: cargo 1.90.0-nightly (eabb4cd92 2025-07-09)
- Host platform: Darwin 23.6.0 arm64
- Nightly toolchain: +nightly-2025-07-14
- Bundle dir: docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21
- Artifact: transformer_shaped.stwo.bundle.json
- Scope: transformer-shaped source-bound translated composition bundle

## Artifact Summary

| Field | Value |
|---|---|
| Artifact file | `transformer_shaped.stwo.bundle.json` |
| Artifact size (bytes) | `9348044` |
| SHA-256 | `85886c6e1a82996e2e745f9c11f54ab0683ed18d3a5b4597c560921db2d2be23` |
| Bundle version | `stwo_transformer_shaped_artifact_bundle_v1` |
| Semantic scope | `stwo_transformer_shaped_translated_composition_bundle` |
| Source chain commitment | `c86b0d1003a7f6ac476da07d3b08b2d27b3ceb264e8fd637671167b7346db12a` |
| Source layout commitment | `ea1308011ffe10ed932941873f5ef24d1e50fa52a1cde812488a518bb6d3e16e` |
| Translated lookup identity commitment | `cd76b9850af0c86cd1104c5b57de1ca8e250357d934336a83a8b559e1dcaa902` |
| Total steps | `5` |
| Translated segment count | `2` |
| Naive per-step package count | `5` |
| Composed segment package count | `2` |
| Package count delta | `3` |
| Source-bound verifier available | `True` |
| Full history replay required | `True` |
| Full standard softmax inference claimed | `False` |
| Recursive verification claimed | `False` |
| Cryptographic compression claimed | `False` |
| Breakthrough claimed | `False` |
| Paper ready | `True` |
| Phase86 commitment | `a8ddcbc4faae31b41ab7595cfb42f5a94ecbcbe3891cb4de1b7726b5fb57f16d` |
| Phase87 commitment | `d84dbe9db1adfa4e784f43f819dd1ae09586437a167c312500a2a3e0c32af28c` |
| Bundle commitment | `629d24355bda9a55468ce72d632b55240a81e8a23afc021768324f024e7cdb08` |

## Timing Summary (seconds)

| Label | Seconds |
|---|---:|
| prepare_transformer_shaped_bundle | 28 |
| verify_transformer_shaped_bundle | 9 |

## Notes
- This bundle freezes one reproducible transformer-shaped `stwo` artifact with source-bound translated segment composition.
- The artifact remains intentionally narrow: it does not claim full standard-softmax inference, recursive aggregation, or cryptographic compression.
- Timing rows are local wall-clock bundle runs under an existing cargo build cache; they are artifact facts, not a normalized benchmark study.
