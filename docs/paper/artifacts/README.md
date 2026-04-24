# Paper Artifact Bundles

This directory contains frozen artifact bundles plus verifier-surface indexes.

## Publication-facing cited bundles

The active paper-facing bundles are:

- `stwo-proof-carrying-aggregation-v1-2026-04-11/`
- `phase63-65-proof-carrying-artifact-v1-2026-04-20/`
- `phase66-69-proof-carrying-hardening-v1-2026-04-21/`
- `phase70-80-proof-checked-decode-bridge-v1-2026-04-21/`
- `stwo-transformer-shaped-v1-2026-04-21/`
- `stwo-shared-normalization-primitive-v1-2026-04-21/`

These are the bundles that should be treated as the paper's primary reproducibility and
systems-evidence surfaces.

The Phase63-65, Phase66-69, and Phase70-80 directories are verifier-surface indexes, not
new proof-output bundles. They pin the carried-state, shared-lookup, and proof-checked
decode-bridge checkpoints that support the paper's narrower systems claims.

The `stwo-transformer-shaped-v1-2026-04-21` directory is the current frozen
transformer-shaped `stwo` bundle with reproducible artifact metrics.

The `stwo-shared-normalization-primitive-v1-2026-04-21` directory is the current
primitive-tier bundle for verifier-enforced shared-table identity.

Later implementation-specific and repeated-window artifact families were removed from the
tracked paper surface when the repository was narrowed to the carried-state and
repeated-reuse lines that still support the current paper claims.

## Archival provenance bundles

These older carried-state bundles are retained as provenance for the development of the
aggregation line:

- `stwo-accumulation-v1-2026-04-09/`
- `stwo-folded-interval-v1-2026-04-10/`
- `stwo-chained-folded-interval-v1-2026-04-10/`

They remain useful supporting evidence, but they are not the main cited artifact tiers
for the current paper package.

## Frozen-bundle handling

Do not rewrite or relocate frozen bundle contents casually.

In particular, avoid editing:

- `commands.log`
- `manifest.txt`
- `sha256sums.txt`
- artifact JSON / gzip files

Those files are provenance objects. Their recorded paths, command lines, and hashes are
part of the evidence trail.

Host-specific absolute paths inside frozen command logs and manifests are expected
historical provenance, not documentation drift.

When regenerating related engineering bundles, prefer a fresh scratch output directory
under `docs/paper/artifacts/`. The accumulation-bundle generator refuses to overwrite
frozen-looking bundle directories unless `ALLOW_OVERWRITE_FROZEN=1` is set explicitly.
