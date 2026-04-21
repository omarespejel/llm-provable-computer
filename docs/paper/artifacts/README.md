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
- `stwo-transformer-shaped-v1-2026-04-21/`
- `stwo-shared-normalization-primitive-v1-2026-04-21/`
- `stwo-tensor-native-transformer-shaped-v1-2026-04-21/`
- `stwo-repeated-gemma-slice-accumulation-v1-2026-04-21/`
- `stwo-folded-gemma-slice-family-v1-2026-04-21/`
- `stwo-multi-interval-folded-gemma-v1-2026-04-21/`
- `stwo-richer-multi-interval-gemma-v1-2026-04-21/`

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

The `stwo-transformer-shaped-v1-2026-04-21` directory is the first frozen
publication-facing transformer-shaped `stwo` bundle with reproducible artifact metrics.
It pins a five-step source chain, two translated segment manifests, a `28s` prepare
run, a `9s` verify run, `9,348,044` artifact bytes, and a package-count reduction from `5`
naive per-step packages to `2` composed translated segments. It remains a narrow
source-bound artifact, not a recursion or full-softmax claim.

The `stwo-shared-normalization-primitive-v1-2026-04-21` directory is the first
frozen publication-facing tensor-native `stwo` primitive bundle with reproducible
artifact metrics. It pins a direct shared-normalization proof reused across `2`
fixed primitive steps, one verifier-enforced canonical table identity, one
table-registry commitment, a `1s` prepare run, a `0s` verify run, `93,819`
artifact bytes, and `9,136` shared proof bytes. It remains an intentionally
narrow primitive artifact rather than a full-softmax or recursive claim.

The `stwo-tensor-native-transformer-shaped-v1-2026-04-21` directory is the
first frozen publication-facing transformer-shaped tensor-native `stwo` bundle.
It pins a `4`-step typed carried-state chain over the shared-normalization
primitive template, one real `gemma_block_v4` S-two execution proof, one Gemma
core-slice artifact that binds the chain to embedded shared-normalization and
shared-activation receipts, `119,566` chain-artifact bytes, `734,065` Gemma
proof JSON bytes, `1,055,612` core-slice bytes, a `1.142s` chain-prepare run,
and a `0.716s` `gemma_block_v4` prove run, plus one source-bound appendix
index with exact hashes and timings. It remains a narrow transformer-shaped
artifact line rather than a full-softmax or recursive claim.

The `stwo-repeated-gemma-slice-accumulation-v1-2026-04-21` directory extends
that tensor-native line into the first frozen repeated Gemma-slice benchmark
surface. It pins one Gemma richer-slice artifact that binds selected
memory-window rows plus score, grouped-value, residual, normalization, and
activation invariants, and one repeated-slice accumulation artifact over `4`
block-indexed slice members. The bundle records `90,432` shared execution proof
bytes against `361,728` naive repeated proof bytes, saving `271,296` proof
bytes by reusing the shared proof once, and it records `1,031,675`
accumulation-artifact bytes against `5,029,980` naive repeated richer-slice
JSON bytes, saving `3,998,305` JSON bytes versus blind richer-slice
duplication. It remains a verifier-bound repeated-slice artifact, not a
recursive cryptographic compression claim.

The `stwo-folded-gemma-slice-family-v1-2026-04-21` directory extends that line
one step further. It freezes the explicit Phase95 repeated-slice accumulation
artifact together with a smaller Phase96.5 folded repeated-slice derivative and
one Phase98 richer-family derivative. The main benchmark question is narrow and
artifact-facing: how much smaller the first folded derivative is than the
explicit repeated accumulation over the same Gemma-like interval, while both
remain verifier-bound to the same shared proof surface. It is still explicitly
pre-recursive and does not claim standalone recursive compression.

The `stwo-multi-interval-folded-gemma-v1-2026-04-21` directory extends that
line across several token-position-indexed interval families. It freezes one
explicit Phase99 multi-interval artifact, one Phase101.5 folded multi-interval
prototype, and the corresponding handoff commitments and appendix index. The
bundle records `1,036,298` explicit multi-interval JSON bytes versus `5,214`
folded multi-interval JSON bytes, so the first folded prototype is about
`0.5031%` of the explicit source JSON size on this frozen surface. It also
records `4,126,700` bytes for blind duplication of the single-interval
explicit accumulation artifact, so the explicit multi-interval artifact already
saves `3,090,402` bytes before any folded derivative is applied. This remains
a verifier-bound, pre-recursive artifact line rather than a cryptographic
recursion claim.

The `stwo-richer-multi-interval-gemma-v1-2026-04-21` directory extends that
same line by freezing the first Phase102 richer multi-interval derivative on
top of the Phase99 explicit source and the Phase101.5 folded handoff. The
bundle records `1,036,298` explicit multi-interval JSON bytes, `5,214` folded
multi-interval JSON bytes, and `7,100` folded richer multi-interval JSON
bytes. So the richer-family derivative is about `0.6851%` of the explicit
source JSON size while remaining only `1,886` bytes larger than the thinner
Phase101.5 folded prototype. This remains a verifier-bound, pre-recursive
artifact line rather than a cryptographic accumulation claim.

Later Phase81-84 translated seam surfaces remain implemented in-repo, but they are not
yet cut as frozen publication-facing artifact directories.

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
