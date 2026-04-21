# Appendix Artifact Index (S-two Tensor-Native Transformer Bundle V1)

## Run Metadata
- Generated at utc: 2026-04-21T13:38:59Z
- Repo root: .
- Git commit: d355946b030d6151d48d064f0f719903cdfce006
- Git commit short: d355946
- Git branch: codex/phase93-945-tensor-chain
- Rustc: rustc 1.90.0-nightly (e9182f195 2025-07-13)
- Cargo: cargo 1.90.0-nightly (eabb4cd92 2025-07-09)
- Host platform: Darwin 23.6.0 arm64
- Nightly toolchain: +nightly-2025-07-14
- Bundle dir: docs/paper/artifacts/stwo-tensor-native-transformer-shaped-v1-2026-04-21
- Chain artifact: tensor-native-chain.stwo.json
- Gemma proof: gemma-block-v4.stark.json
- Gemma core slice artifact: gemma-block-core-slice.stwo.json
- Scope: tensor-native transformer-shaped S-two chain plus Gemma block core slice

## Artifact Summary

| Field | Value |
|---|---|
| Chain artifact file | `tensor-native-chain.stwo.json` |
| Chain artifact size (bytes) | `119566` |
| Chain artifact SHA-256 | `a48b50f2433db33d167434b3ce6476cc5786ce783e035b0001256e00e78d7e79` |
| Chain artifact version | `stwo-phase93-tensor-native-chain-artifact-v1` |
| Chain scope | `stwo_tensor_native_transformer_shaped_chain_artifact` |
| Chain total steps | `4` |
| Shared proof bytes | `9136` |
| Gemma proof file | `gemma-block-v4.stark.json` |
| Gemma proof size (bytes) | `734065` |
| Gemma proof SHA-256 | `5f08504d82be1ddb8c0e0e663fa34a3a280b4d4e772d2d40430601feaef79673` |
| Gemma proof backend version | `stwo-phase10-gemma-block-v4` |
| Gemma proof steps | `43` |
| Gemma core-slice file | `gemma-block-core-slice.stwo.json` |
| Gemma core-slice size (bytes) | `1055612` |
| Gemma core-slice SHA-256 | `8aef03e65442d56d2fc5df0a20a190b24c7a96cbd0de762a0945544d6080ae66` |
| Gemma core-slice version | `stwo-phase94-5-gemma-block-core-slice-artifact-v1` |
| Gemma core-slice scope | `stwo_tensor_native_gemma_block_core_slice_artifact` |
| Gemma shared normalization rows | `2` |
| Gemma shared activation rows | `2` |
| Gemma execution proof bytes | `90432` |

## Timing Summary (seconds)

| Label | Seconds |
|---|---:|
| prepare_tensor_native_chain | 1.142 |
| verify_tensor_native_chain | 0.688 |
| prove_gemma_block_v4 | 0.716 |
| verify_gemma_block_v4 | 0.713 |
| prepare_gemma_block_core_slice | 0.766 |
| verify_gemma_block_core_slice | 0.780 |

## Notes
- The chain artifact is transformer-shaped but intentionally narrow: it proves one shared-normalization primitive template and enforces typed carried-state continuity across four local steps.
- The Gemma core-slice artifact binds that chain to a real `gemma_block_v4` S-two execution proof with embedded shared-normalization and shared-activation receipts.
- This bundle does not claim full standard-softmax transformer inference or recursive aggregation.
