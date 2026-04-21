# Appendix Artifact Index (S-two Multi-Interval Folded Gemma Bundle V1)

## Canonical Bundle Parameters
- Bundle version: stwo-multi-interval-folded-gemma-v1
- Repo root: .
- Nightly toolchain: +nightly-2025-07-14
- Bundle dir: docs/paper/artifacts/stwo-multi-interval-folded-gemma-v1-2026-04-21
- Gemma proof: gemma-block-v4.stark.json
- Single-interval explicit artifact: single-interval-repeated-gemma-slice-accumulation.stwo.json
- Single-interval folded artifact: single-interval-folded-gemma-slice-accumulation.stwo.json
- Single-interval richer-family artifact: single-interval-folded-gemma-richer-slice-family.stwo.json
- Multi-interval explicit artifact: multi-interval-gemma-richer-family-accumulation.stwo.json
- Folded multi-interval prototype artifact: folded-multi-interval-gemma-accumulation-prototype.stwo.json
- Canonical sha256 file: sha256sums.txt
- Auxiliary benchmarks file: benchmarks.tsv
- Auxiliary commands log: commands.log
- Total intervals: 4
- Interval total slices: 4
- Token position start: 0
- Token position stride: 1
- Scope: explicit multi-interval richer-family accumulation plus a folded pre-recursive prototype over one shared S-two proof surface

## Artifact Summary

| Field | Value |
|---|---|
| Shared execution proof bytes | `90432` |
| Shared execution proof JSON bytes | `734065` |
| Shared execution proof SHA-256 | `5f08504d82be1ddb8c0e0e663fa34a3a280b4d4e772d2d40430601feaef79673` |
| Single-interval explicit file | `single-interval-repeated-gemma-slice-accumulation.stwo.json` |
| Single-interval explicit size (bytes) | `1031675` |
| Single-interval explicit SHA-256 | `c28ac23e1d95807475637003ba634ff452b7ee406d8e498dfcfe547994160976` |
| Single-interval folded file | `single-interval-folded-gemma-slice-accumulation.stwo.json` |
| Single-interval folded size (bytes) | `4296` |
| Single-interval folded SHA-256 | `4e7decd7911529b7c850c3a7f86c74b213290caa8186513a69e72196a9ad0c52` |
| Single-interval richer-family file | `single-interval-folded-gemma-richer-slice-family.stwo.json` |
| Single-interval richer-family size (bytes) | `2114` |
| Single-interval richer-family SHA-256 | `64b3b02fa1dffa36ed5a6fcdcee92e073287e84926f4caa1d0fe335151a82472` |
| Multi-interval explicit file | `multi-interval-gemma-richer-family-accumulation.stwo.json` |
| Multi-interval explicit size (bytes) | `1036298` |
| Multi-interval explicit SHA-256 | `da894ba4dea5767a8d14fe370be50d2ce999c6571d58d901ffa71911a92941ab` |
| Multi-interval explicit version | `stwo-phase99-multi-interval-gemma-richer-family-accumulation-artifact-v1` |
| Multi-interval explicit scope | `stwo_tensor_native_multi_interval_gemma_richer_family_accumulation_artifact` |
| Folded multi-interval prototype file | `folded-multi-interval-gemma-accumulation-prototype.stwo.json` |
| Folded multi-interval prototype size (bytes) | `5214` |
| Folded multi-interval prototype SHA-256 | `6e3747925a08dc377585e457d2118bd1e06b702214888c37dd4e25f60ac67c9a` |
| Folded multi-interval prototype version | `stwo-phase101-5-folded-multi-interval-gemma-accumulation-prototype-artifact-v1` |
| Folded multi-interval prototype scope | `stwo_tensor_native_folded_multi_interval_gemma_accumulation_prototype_artifact` |
| Naive single-interval explicit duplication bytes | `4126700` |
| Multi-interval explicit vs naive explicit duplication bytes saved | `3090402` |
| Multi-interval explicit vs folded prototype bytes saved | `1031084` |
| Folded prototype / multi-interval explicit ratio | `0.005031` |
| Total folded interval groups | `2` |
| Accumulation handoff commitment | `c0121c799edfd7bc06fbd5037fc0950c4ae90281779353230677018182f7fbb2` |

## Notes
- This bundle is pre-recursive. The folded multi-interval artifact is a verifier-bound prototype derived from the explicit Phase99 source artifact, not a standalone recursive proof.
- The main benchmark question is explicit multi-interval accumulation versus the first folded multi-interval prototype on the same shared S-two proof surface.
- The secondary benchmark comparison is explicit multi-interval accumulation versus blind duplication of the single-interval explicit accumulation artifact.
