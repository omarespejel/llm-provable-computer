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

It also proves the public scalar sqrt/range surface with bounded
nonnegative-gap decompositions:

```text
rms_q8^2 + sqrt_low_delta = average_square_floor
(rms_q8 + 1)^2 = average_square_floor + sqrt_high_gap + 1
sqrt_low_delta, sqrt_high_gap are 17-bit nonnegative decompositions
```

Together with the verifier-side public-row check that
`average_square_floor = floor(sum_squares / 64)`, this moves the
`rms_q8 = isqrt(floor(sum_squares / 64))` inequality from host-only
recomputation into the AIR for this bounded public scalar surface.

The verifier recomputes the commitment-bearing public-row artifacts before
proof verification:

- input activation commitment,
- RMSNorm-local output row commitment over `normed_q8`,
- normalization config commitment,
- RMS scale tree root.

It still recomputes verifier-side aggregate values from the checked public rows:

- row count,
- sum of squares,
- `average_square_floor = floor(sum_squares / 64)`,
- the public `rms_q8` value before the AIR proof is generated or verified.

The verifier hardening is intentionally fail-closed:

- public-row arithmetic uses signed-M31 bounds and checked integer operations
  before field encoding,
- `rms_q8` is recomputed with exact integer arithmetic, not floating-point
  square root,
- the AIR enforces the sqrt inequality using 17-bit nonnegative gap
  decompositions for the current public-row scalar surface,
- the RMSNorm-local output row commitment is recomputed from `normed_q8` before
  proof verification, so it cannot be relabeled independently of the checked
  rows,
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
- the bounded scalar sqrt/range inequality is now proven by native Stwo AIR over
  the verifier-checked public scalar,
- the RMSNorm-local output row commitment is bound to the checked `normed_q8`
  rows,
- row aggregation, private witness opening, projection, activation, and residual
  relations remain outside this proof slice.

## Non-Claims

The checked non-claims are:

- `not private witness privacy`
- `not full d64 block proof`
- `not projection, activation, SwiGLU, down-projection, or residual proof`
- `rms_q8 scalar sqrt inequality is AIR-native only for this public scalar row surface`
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

Issue `#356` is now closed by this bounded public-scalar AIR hardening. The
first part of issue `#358` is also closed: the proof input now carries a
recomputed local `rmsnorm_output_row_commitment` for `normed_q8` rows. The
follow-up bridge proof now consumes that local commitment and emits a
domain-separated `projection_input_row_commitment`:

- `docs/engineering/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json`
- `src/stwo_backend/d64_native_rmsnorm_to_projection_bridge_proof.rs`

The follow-up gate/value and activation/SwiGLU proofs now extend this path to a
domain-separated `hidden_activation_commitment`. The next native-proof lane is
down projection before any full d64 `output_activation_commitment` is claimed.
