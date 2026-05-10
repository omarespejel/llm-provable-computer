# zkAI Attention/KV Stwo Controlled Component Grid - 2026-05-10

## Question

Is the typed-component saving from fusing attention arithmetic with
Softmax-table LogUp membership a single-profile artifact, or does it persist
across the checked Stwo attention/table profiles?

## Decision

`GO_CHECKED_STWO_COMPONENT_GRID_WITH_FULL_FACTORIAL_GRID_NO_GO`

The checked grid supports a bounded engineering claim: across the ten existing
native Stwo fused attention/table profiles, every fused proof object is smaller
than the matched source-plus-LogUp-sidecar route under the fine-grained typed
component estimate.

This is **not** a full factorial benchmark. This gate now includes one `seq32`
sequence-axis extension, but it still does not include `d32`, all width/head/
sequence crossings, timing, stable binary proof bytes,
real-valued Softmax, full inference, recursion, or PCD.

## Evidence

- Gate script:
  `scripts/zkai_attention_kv_stwo_controlled_component_grid_gate.py`
- Gate tests:
  `scripts/tests/test_zkai_attention_kv_stwo_controlled_component_grid_gate.py`
- JSON evidence:
  `docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json`
- TSV evidence:
  `docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.tsv`
- Evidence commitment:
  `blake2b-256:9ada5fedb11764ad301c51bc84d78bfceb1a36444a41c9fedc21fd296453238d`

The gate is derived from already checked artifacts:

- route matrix issue `#505`
- section-delta issue `#531`
- fine-grained typed component schema issue `#534`

## Reproduction Metadata

- Operator/session: Omar Espejel local research checkout with Codex-assisted
  gate implementation.
- Repo/branch: `provable-transformer-vm`, branch
  `issue-537-seq32`.
- Base checked from: `origin/main` at
  `432845269bae497c37c8d565a1bdee6b6b66d2d7`.
- Rust/Stwo surface: Rust `nightly-2025-07-14`, Cargo.lock-pinned Stwo
  `2.2.0`, native `stwo-backend` proof artifacts already checked by the source
  gates.
- Timing policy: `proof_component_size_accounting_only_not_timing_not_public_benchmark`.
- Profile controls: ten checked profiles with lookup-claim counts from `52`
  to `1,184` and trace rows from `64` to `2,048`; row-level controls are in the
  JSON/TSV evidence.

## Result

Across the ten checked profiles:

| Metric | Value |
|---|---:|
| Source + sidecar typed estimate | `285,584` bytes |
| Fused typed estimate | `234,296` bytes |
| Typed saving | `51,288` bytes |
| Typed saving share | `17.9590%` |
| Source + sidecar JSON proof bytes | `814,142` bytes |
| Fused JSON proof bytes | `629,466` bytes |
| JSON proof-byte saving | `184,676` bytes |
| JSON proof-byte saving share | `22.6835%` |
| Per-profile typed saving range | `9.1035%` to `27.7371%` |

All ten checked profiles save typed component bytes. The strongest per-profile
typed saving is now the `d8_two_head_seq32` route at `27.7371%`. The weakest is the
`d16_single_head_seq8` route at `9.1035%`.

## Where the saving comes from

The typed saving is dominated by shared opening/decommitment structure:

| Component family | Saving | Share of typed saving |
|---|---:|---:|
| FRI + trace Merkle path bytes | `41,312` bytes | `80.5491%` |
| Opening plumbing including commitments | `44,896` bytes | `87.5370%` |

The largest single component bucket is:

`fri_decommitment_merkle_path_bytes = 21,824` bytes.

The next largest bucket is:

`trace_decommitment_merkle_path_bytes = 19,488` bytes.

## Interpretation

This supports the Stwo-native zkML thesis in a narrow, checked way:

1. Attention arithmetic and table-membership checks can be represented as one
   native Stwo proof object.
2. The fused object avoids duplicated proof-system plumbing that appears when
   arithmetic and LogUp membership are carried as separate proofs.
3. The saving is not just a single aggregate row; it persists across checked
   width, head-count, sequence, and combined-axis controls.

This is not Tablero-scale replay elimination. Tablero removes an entire repeated
verification path. This result is lower-level proof engineering: it shows that
native fused transformer receipts can reduce the cost of each proof object
before any higher-level composition pattern is applied.

## Claim Boundary

This gate may be cited internally as:

> Across ten checked native Stwo attention/table profiles, fusing attention
> arithmetic with Softmax-table LogUp membership reduced fine-grained typed
> proof-component size by `9.1035%` to `27.7371%` per profile, with a
> `51,288`-byte (`17.9590%`) aggregate saving. The saving is dominated by
> shared FRI and trace opening/decommitment structure.

Do not cite it as:

- a full factorial grid;
- a timing benchmark;
- a stable binary proof-size benchmark;
- a real-valued Softmax proof;
- full transformer inference;
- backend-internal source-vs-lookup column attribution;
- recursion, PCD, or Starknet deployment evidence.

## Missing Controls

The next step for a stronger paper claim is to add:

1. `d32` source/sidecar/fused proof artifacts;
2. a fuller crossing of width, head count, and sequence length;
3. timing only after the proof-object grid is stable.

Issue `#537` closes the first follow-up by adding the `seq32` sequence-axis
extension. If `d32` and additional crossings preserve positive fused savings,
the paper claim can move from "checked profile family" to a stronger scaling
statement.

## Validation

```bash
python3 scripts/zkai_attention_kv_stwo_controlled_component_grid_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_controlled_component_grid_gate

python3 scripts/zkai_attention_kv_stwo_fine_grained_component_schema_gate.py --no-write

just gate-fast

just gate
```
