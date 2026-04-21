# Appendix Artifact Index (S-two Folded Gemma Slice Family Bundle V1)

## Canonical Bundle Parameters
- Bundle version: stwo-folded-gemma-slice-family-v1
- Repo root: .
- Nightly toolchain: +nightly-2025-07-14
- Bundle dir: docs/paper/artifacts/stwo-folded-gemma-slice-family-v1-2026-04-21
- Chain artifact: tensor-native-chain.stwo.json
- Gemma proof: gemma-block-v4.stark.json
- Gemma core slice artifact: gemma-block-core-slice.stwo.json
- Gemma richer slice artifact: gemma-block-richer-slice.stwo.json
- Explicit accumulation artifact: repeated-gemma-slice-accumulation.stwo.json
- Folded accumulation artifact: folded-gemma-slice-accumulation.stwo.json
- Folded richer family artifact: folded-gemma-richer-slice-family.stwo.json
- Canonical sha256 file: sha256sums.txt
- Auxiliary benchmarks file: benchmarks.tsv
- Auxiliary commands log: commands.log
- Total slices: 4
- Token position: 0
- Start block index: 2
- Scope: explicit repeated Gemma-slice accumulation plus folded derivatives over one shared S-two proof surface

## Artifact Summary

| Field | Value |
|---|---|
| Chain artifact file | `tensor-native-chain.stwo.json` |
| Chain artifact size (bytes) | `119566` |
| Chain artifact SHA-256 | `a48b50f2433db33d167434b3ce6476cc5786ce783e035b0001256e00e78d7e79` |
| Chain total steps | `4` |
| Shared execution proof file | `gemma-block-v4.stark.json` |
| Shared execution proof bytes | `90432` |
| Shared execution proof JSON bytes | `734065` |
| Shared execution proof SHA-256 | `5f08504d82be1ddb8c0e0e663fa34a3a280b4d4e772d2d40430601feaef79673` |
| Shared execution proof backend version | `stwo-phase10-gemma-block-v4` |
| Gemma richer-slice file | `gemma-block-richer-slice.stwo.json` |
| Gemma richer-slice size (bytes) | `1257495` |
| Gemma richer-slice SHA-256 | `bce1b0d9367cfe8353edba17ca3ab1961ce8f4b8673deb1e178ff3c3b71c9bc9` |
| Explicit accumulation file | `repeated-gemma-slice-accumulation.stwo.json` |
| Explicit accumulation size (bytes) | `1031675` |
| Explicit accumulation SHA-256 | `c28ac23e1d95807475637003ba634ff452b7ee406d8e498dfcfe547994160976` |
| Folded accumulation file | `folded-gemma-slice-accumulation.stwo.json` |
| Folded accumulation size (bytes) | `4296` |
| Folded accumulation SHA-256 | `4e7decd7911529b7c850c3a7f86c74b213290caa8186513a69e72196a9ad0c52` |
| Folded accumulation version | `stwo-phase96-5-folded-gemma-slice-accumulation-artifact-v1` |
| Folded accumulation scope | `stwo_tensor_native_folded_gemma_slice_accumulation_artifact` |
| Bounded fold arity | `2` |
| Total folded groups | `2` |
| Explicit vs folded bytes saved | `1027379` |
| Folded / explicit byte ratio | `0.004164` |
| Folded richer-family file | `folded-gemma-richer-slice-family.stwo.json` |
| Folded richer-family size (bytes) | `2114` |
| Folded richer-family SHA-256 | `64b3b02fa1dffa36ed5a6fcdcee92e073287e84926f4caa1d0fe335151a82472` |
| Folded richer-family version | `stwo-phase98-folded-gemma-richer-slice-family-artifact-v1` |
| Folded richer-family scope | `stwo_tensor_native_folded_gemma_richer_slice_family_artifact` |
| Local score sum | `8` |
| Global score sum | `8` |
| Grouped value mix sum | `32` |
| Residual output sum | `16` |
| Primary norm range | `16..16` |
| Secondary norm range | `4..4` |
| Primary activation output sum | `4` |
| Secondary activation output sum | `4` |
| Family delta vs folded bytes | `-2182` |

## Notes
- This bundle is pre-recursive. The folded artifacts are verifier-bound derivatives over the explicit Phase95 source artifact, not standalone recursive proofs.
- The main benchmark comparison here is explicit repeated accumulation versus the first folded repeated-slice derivative.
- The richer-family artifact extends that line by binding selected memory-window and fixed-program invariant families over the same repeated Gemma-like source interval.
- `benchmarks.tsv` and `commands.log` are auxiliary run records and are intentionally excluded from `sha256sums.txt` because timings depend on environment.
