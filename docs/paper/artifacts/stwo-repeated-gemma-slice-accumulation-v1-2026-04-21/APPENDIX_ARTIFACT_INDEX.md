# Appendix Artifact Index (S-two Repeated Gemma-Slice Accumulation Bundle V1)

## Canonical Bundle Parameters
- Bundle version: stwo-repeated-gemma-slice-accumulation-v1
- Repo root: .
- Nightly toolchain: +nightly-2025-07-14
- Bundle dir: docs/paper/artifacts/stwo-repeated-gemma-slice-accumulation-v1-2026-04-21
- Chain artifact: tensor-native-chain.stwo.json
- Gemma proof: gemma-block-v4.stark.json
- Gemma core slice artifact: gemma-block-core-slice.stwo.json
- Gemma richer slice artifact: gemma-block-richer-slice.stwo.json
- Repeated accumulation artifact: repeated-gemma-slice-accumulation.stwo.json
- Canonical sha256 file: sha256sums.txt
- Auxiliary benchmarks file: benchmarks.tsv
- Auxiliary commands log: commands.log
- Total slices: 4
- Token position: 0
- Start block index: 2
- Scope: repeated Gemma-like tensor-native slice accumulation over one shared S-two proof

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
| Shared execution proof steps | `43` |
| Gemma core-slice file | `gemma-block-core-slice.stwo.json` |
| Gemma core-slice size (bytes) | `1055612` |
| Gemma core-slice SHA-256 | `8aef03e65442d56d2fc5df0a20a190b24c7a96cbd0de762a0945544d6080ae66` |
| Gemma richer-slice file | `gemma-block-richer-slice.stwo.json` |
| Gemma richer-slice size (bytes) | `1257495` |
| Gemma richer-slice SHA-256 | `bce1b0d9367cfe8353edba17ca3ab1961ce8f4b8673deb1e178ff3c3b71c9bc9` |
| Richer-slice local score | `2` |
| Richer-slice global score | `2` |
| Richer-slice grouped value mix | `8` |
| Richer-slice residual output | `4` |
| Richer-slice selected memory window rows | `12` |
| Repeated accumulation file | `repeated-gemma-slice-accumulation.stwo.json` |
| Repeated accumulation size (bytes) | `1031675` |
| Repeated accumulation SHA-256 | `c28ac23e1d95807475637003ba634ff452b7ee406d8e498dfcfe547994160976` |
| Repeated accumulation version | `stwo-phase95-repeated-gemma-slice-accumulation-artifact-v1` |
| Repeated accumulation scope | `stwo_tensor_native_repeated_gemma_slice_accumulation_artifact` |
| Total slices | `4` |
| Repeated token position | `0` |
| Start block index | `2` |
| Terminal block index | `5` |
| Naive repeated proof bytes | `361728` |
| Proof bytes saved vs naive duplication | `271296` |
| Naive repeated richer-slice JSON bytes | `5029980` |
| Accumulation JSON bytes saved vs richer duplication | `3998305` |
| Members commitment | `37da2b237f0ec958061b80cba66cfad729dcc1b0b62e24ffe128dc0884e655fd` |
| Shared table registry commitment | `5fbdca3a939c778419112c387775d8f4fbfea70047eb56b709534ab218212920` |

## Notes
- This bundle does not claim recursive cryptographic compression. It freezes verifier-bound repeated-slice accumulation over one shared S-two proof and one repeated Gemma-like slice template.
- The richer slice strengthens the earlier core slice by binding selected memory-window rows plus score, grouped-value, residual, normalization, and activation invariants.
- The accumulation artifact shows the repository's intended benchmark shape: repeated transformer structure reuses one shared proof surface and one canonical lookup registry instead of duplicating full slice artifacts blindly.
- `benchmarks.tsv` and `commands.log` are auxiliary run records. They are intentionally excluded from `sha256sums.txt` because wall-clock timings are environment-dependent.
