# Paper Artifact Bundles

This directory contains frozen artifact bundles plus verifier-surface indexes.

## Publication-facing cited bundles

These are the bundles directly used by the current paper package:

- `production-v1-2026-04-04/`
- `stwo-experimental-v1-2026-04-06/`
- `stwo-proof-carrying-aggregation-v1-2026-04-11/`
- `phase63-65-proof-carrying-artifact-v1-2026-04-20/`
- `phase66-69-proof-carrying-hardening-v1-2026-04-21/`
- `phase70-80-proof-checked-decode-bridge-v1-2026-04-21/`

These are the bundles that should be treated as the paper's primary reproducibility and systems-evidence surfaces.

The Phase63-65 directory is a code-and-validation verifier-surface index rather than a
new proof-output bundle. It pins the April 20 checkpoint where shared lookup identity
and typed carried state became verifier-visible across the transformer-shaped
proof-carrying artifact line.

The Phase66-69 directory continues that verifier-surface line. It pins chained
transition handoffs, a publication-facing artifact table, an independent replay audit
manifest, and a symbolic-model-to-artifact mapping. It is still not a new proof-output
bundle and not a runtime benchmark.

The Phase70-80 directory freezes the bounded decode-bridge stop condition. It pins
the role-neutral handoff layer, the actual S-two step-envelope and shared-lookup
registry receipts, the chunked-history carry receipt, and the proof-checked
publication decode-bridge table. It is still a code-and-validation verifier-surface
index rather than a new proof-output bundle.

Later Phase81-88 translated seam and composition surfaces remain implemented in-repo,
but they are not yet cut as frozen publication-facing artifact directories.

## Archival provenance bundles

These older carried-state bundles are retained as provenance for the development of the aggregation line:

- `stwo-accumulation-v1-2026-04-09/`
- `stwo-folded-interval-v1-2026-04-10/`
- `stwo-chained-folded-interval-v1-2026-04-10/`

They remain useful supporting evidence, but they are not the main cited artifact tiers for the current paper package.

## Frozen-bundle handling

Do not rewrite or relocate frozen bundle contents casually.

In particular, avoid editing:

- `commands.log`
- `manifest.txt`
- `sha256sums.txt`
- artifact JSON / gzip files

Those files are provenance objects. Their recorded paths, command lines, and hashes are part of the evidence trail.

Host-specific absolute paths inside frozen command logs and manifests are expected historical provenance, not documentation drift.

When regenerating related engineering bundles, prefer a fresh scratch output
directory under `docs/paper/artifacts/`. The accumulation-bundle generator
refuses to overwrite frozen-looking bundle directories unless
`ALLOW_OVERWRITE_FROZEN=1` is set explicitly.
