# zkAI d64 native RMSNorm public-row AIR proof - 2026-05-01

## Question

Can we move past statement contracts and produce a real native Stwo proof for a
bounded d64 transformer primitive without overclaiming full zkML inference?

## Result

GO for a first native Stwo AIR proof over the public d64 RMSNorm row surface.

The Rust module `src/stwo_backend/d64_native_rmsnorm_public_row_proof.rs`
proves the checked `64`-row RMSNorm arithmetic surface as a Stwo AIR component.
The verifier binds the proof to the exact public rows by using those rows as
preprocessed verifier-known columns and enforcing trace equality against them.

The component proves, for every coordinate:

```text
input_i * input_i = square_i
input_i * rms_scale_i = scaled_floor_i * 256 + scale_remainder_i
scaled_floor_i * 256 = normed_i * rms_q8 + norm_remainder_i
```

The verifier recomputes the commitment-bearing public-row artifacts before
proof verification:

- input activation commitment,
- normalization config commitment,
- RMS scale tree root.

It also recomputes verifier-side scalar values from the checked rows:

- row count,
- sum of squares,
- `rms_q8 = isqrt(floor(sum_squares / 64))`.

The verifier hardening is intentionally fail-closed:

- public-row arithmetic uses signed-M31 bounds and checked integer operations
  before field encoding,
- `rms_q8` is recomputed with exact integer arithmetic, not floating-point
  square root,
- the proof's PCS configuration must match the d64 public-row v1 PCS profile
  before commitment-root recomputation: `pow_bits=10`,
  `fri_config={log_last_layer_degree_bound=0, log_blowup_factor=1,
  n_queries=3, fold_step=1}`, `lifting_log_size=None`,
- malformed proof commitment vectors are rejected before indexing,
- proof bytes are bounded before JSON deserialization.

## Why This Matters

This is the first step that crosses from "statement-bound zkAI target" into
"native Stwo proof for a transformer primitive." It is deliberately small:
RMSNorm only, public rows only, no projection or activation proof, and no
private witness hiding.

The useful research split is now explicit:

- the per-row arithmetic is proven by native Stwo AIR,
- the scalar sqrt/range relation is verifier-side checked over public rows,
- moving that scalar check into AIR-native range or lookup constraints is
tracked separately in issue `#356`.

## Non-Claims

The checked non-claims are:

- `not private witness privacy`
- `not full d64 block proof`
- `not projection, activation, SwiGLU, down-projection, or residual proof`
- `rms_q8 scalar sqrt correctness is verifier-side checked over public rows, not yet AIR-native range proof`
- `not proof that private witness rows open to proof_native_parameter_commitment beyond public rms_scale_tree_root recomputation`
- `not binding the full d64 output_activation_commitment from only RMSNorm local rows`

## Evidence

Machine-readable input evidence:

- `docs/engineering/evidence/zkai-d64-native-rmsnorm-public-row-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-public-row-proof-2026-05.tsv`

Rust proof module:

- `src/stwo_backend/d64_native_rmsnorm_public_row_proof.rs`

## Validation

```bash
cargo +nightly-2025-07-14 test d64_native_rmsnorm_public_row_proof --lib --features stwo-backend
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Next Step

Issue `#356` is the next hardening lane: move the
`rms_q8 = isqrt(floor(sum_squares / 64))` scalar check from verifier-side
public-row recomputation into an AIR-native bounded inequality or lookup
argument.
