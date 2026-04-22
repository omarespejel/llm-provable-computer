# Phase114 Public Benchmark Table Spec

## Goal

Publish one benchmark table that is useful, honest, and hard to misread.

The table must do two things at once:

1. report the repository's own frozen artifact metrics exactly, and
2. place those metrics next to public zkML systems without pretending unlike
   workloads are directly comparable.

## Core rule

Do not mix these two evidence classes into a fake leaderboard.

The table must have two explicit classes of rows:

- `internal-frozen-artifact`
- `public-paper-context`

## Internal frozen-artifact rows

These rows may report exact repository numbers because they are generated from
frozen bundles with manifests, commands, hashes, and verifier paths.

Required columns:

- system
- evidence_class
- surface
- backend_family
- workload_shape
- shared-proof reuse
- repeated-structure handling
- proof bytes
- artifact bytes
- explicit-source bytes
- ratio versus explicit source
- verify path status
- note

Expected first internal rows:

- repeated `2`-window Phase107 explicit source
- repeated `4`-window Phase107 explicit source
- repeated `8`-window Phase107 explicit source
- Phase109 pair-fold artifact
- Phase110 repeated-window fold tree artifact
- later Phase112 semantic artifact
- later Phase113 richer-family artifact

## Public-paper-context rows

These rows are architectural context only.

They should never be written as matched wall-clock winners against the
repository rows unless the workload, hardware, privacy mode, accuracy target,
and proof statement are actually aligned.

Required columns:

- system
- evidence_class
- backend_family
- proving_surface
- repeated-structure handling
- lookup specialization
- public workload claim
- public metric claim
- comparability_to_repo
- source

Recommended first public rows:

- `zkLLM`
- `Jolt Atlas`
- `NANOZK`
- `ZKTorch`

## Row guidance

### zkLLM

Use it to show:

- explicit lookup-heavy treatment for non-arithmetic tensor operations
- explicit attention specialization via `zkAttn`
- one public full-inference claim for large LLMs

Use the public metric only as context:

- under `15` minutes for `13B`-parameter inference
- proof under `200 kB`

Comparability label:

- `not matched; different backend, workload, and privacy/performance regime`

Source:

- arXiv `2404.16109`

### Jolt Atlas

Use it to show:

- direct ONNX/tensor relations rather than CPU or VM emulation
- lookup-centric SNARK-side convergence

Comparability label:

- `not matched; architecture-context row`

Source:

- arXiv `2602.17452`

### NANOZK

Use it to show:

- layerwise decomposition as a serious transformer-proof route
- lookup approximations for softmax, GELU, and LayerNorm

Comparability label:

- `not matched; layerwise proof envelope rather than repeated-window artifact surface`

Source:

- arXiv `2603.18046`

### ZKTorch

Use it to show:

- specialized basic blocks plus parallel proof accumulation

Comparability label:

- `not matched; different accumulation stack and proof statement`

Source:

- arXiv `2507.07031`

## Table wording rules

The caption or surrounding note must say:

- repository rows are frozen artifact metrics,
- public-paper rows are architecture-context rows,
- no direct leaderboard claim is intended,
- and the purpose of the table is to show where the repository sits in the
  design space.

## Non-goals

The table must not imply:

- fastest prover,
- smallest proof globally,
- best wall-clock system,
- or that a verifier-bound artifact metric is the same thing as a production
  prover benchmark.

## Stop condition

Phase114 is complete when the repository has:

- one checked table with clearly separated internal and public rows,
- source links for every public row,
- exact frozen-bundle hashes for every internal row,
- and wording that survives hostile reading without collapsing into a fake
  cross-paper benchmark claim.
