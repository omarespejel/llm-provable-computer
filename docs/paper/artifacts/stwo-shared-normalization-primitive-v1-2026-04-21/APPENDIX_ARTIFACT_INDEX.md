# Appendix Artifact Index (S-two Shared-Normalization Primitive V1)

## Run Metadata
- Generated at utc: 2026-04-21T12:56:29Z
- Repo root: .
- Git commit: 56ebe51f40095916522e7f04dc0e187f1e90f4b6
- Git commit short: 56ebe51
- Git branch: codex/phase91-92-shared-normalization-primitive
- Rustc: rustc 1.90.0-nightly (e9182f195 2025-07-13)
- Cargo: cargo 1.90.0-nightly (eabb4cd92 2025-07-09)
- Host platform: Darwin 23.6.0 arm64
- Nightly toolchain: +nightly-2025-07-14
- Bundle dir: docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21
- Artifact: shared-normalization-primitive.stwo.json
- Scope: tensor-native shared-normalization primitive with verifier-enforced shared-table identity

## Artifact Summary

| Field | Value |
|---|---|
| Artifact file | `shared-normalization-primitive.stwo.json` |
| Artifact size (bytes) | `93819` |
| SHA-256 | `6702759ac006b7fbc51610721d186a7050b8e19bfc0854ee6b3e2f99c10699f2` |
| Artifact version | `stwo-phase92-shared-normalization-primitive-artifact-v1` |
| Semantic scope | `stwo_tensor_native_shared_normalization_primitive_artifact` |
| Artifact commitment | `936005382ba9dc176687b014401fefdfc2ee22f6ce9495257c4dab3ff60aa3a6` |
| Step claims commitment | `ad50101ca7de985408fc71f068a7595bee361042ec61924cbf792240b23380b5` |
| Static table registry version | `stwo-phase92-shared-normalization-table-registry-v1` |
| Static table registry scope | `stwo_tensor_native_shared_normalization_table_registry` |
| Static table registry commitment | `5fbdca3a939c778419112c387775d8f4fbfea70047eb56b709534ab218212920` |
| Static table id | `phase5-normalization-q8-v1` |
| Canonical table rows | `5` |
| Total steps | `2` |
| Total claimed rows | `2` |
| Shared proof backend version | `stwo-phase10-shared-normalization-lookup-v1` |
| Shared proof statement version | `stwo-shared-normalization-lookup-v1` |
| Shared proof bytes | `9136` |

## Timing Summary (seconds)

| Label | Seconds |
|---|---:|
| prepare_shared_normalization_primitive | 1 |
| verify_shared_normalization_primitive | 1 |

## Notes
- This bundle freezes one tensor-native `stwo` primitive artifact rather than a VM-composition wrapper.
- The verifier binds one canonical normalization table identity, one table-registry commitment, and one direct shared-normalization proof across two fixed primitive steps.
- The artifact remains intentionally narrow: it does not claim full standard-softmax inference, recursive aggregation, or cross-step multiplicity-aware lookup reuse.
