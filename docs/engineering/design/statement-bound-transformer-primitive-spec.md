# Statement-Bound Transformer Primitive Spec

Status: feasibility spec for issue #310. This is not a publication claim and not
a full transformer-inference proof.

## Purpose

The next prover-side research step should test the statement-binding lesson from
the external adapters on a Stwo-native primitive.

A useful first result is not scale. A useful first result is one accepted
transparent proof whose surrounding receipt binds the claimed primitive, weights,
input, output, configuration, backend version, verifier domain, and public
instance digest, and whose verifier rejects every stale-evidence relabeling
attempt.

## Current external lesson

The checked EZKL and snarkjs adapter results agree:

- raw proof verification accepts the baseline proof,
- raw proof verification rejects proof-public-input drift,
- raw proof verification does not reject metadata-only relabeling because those
  labels are outside the raw proof verifier's acceptance path,
- a statement envelope around the same proof rejects all checked relabeling
  mutations.

The Stwo-native primitive should not repeat that mistake. Its public API should
make the statement receipt a first-class verifier input, not optional
application metadata.

## Candidate target

Best first target: the existing Stwo linear-block-with-lookup surface exercised
by `programs/linear_block_v4_with_lookup.tvm`.

Why this target is credible:

- it already has prove/verify CLI coverage in the repo,
- it is transformer-shaped but still bounded,
- it exposes normalization/lookup companion surfaces that are close to the
  current proof-stack strengths,
- it avoids jumping directly to full attention or full autoregressive inference,
- it is small enough for a fail-closed relabeling harness.

Fallback target: a smaller quantized linear or `matmul-2x2` primitive if the
linear-block-with-lookup surface is too coupled to older proof metadata.

Do not start with full attention, KV-cache transition, or full transformer block
unless the bounded primitive below already has a statement-bound receipt.

## Statement fields

A `zkAIStatementReceiptV1` for the Stwo-native primitive must bind:

| Field | Required content |
| --- | --- |
| `receipt_version` | `zkai-statement-receipt-v1` or successor. |
| `verifier_domain` | Exact Stwo primitive verifier domain. |
| `proof_system` | `stwo`. |
| `proof_system_version` | Exact backend/proof version string accepted by the verifier. |
| `statement_kind` | `transformer-primitive`. |
| `model_id` | Primitive or block identifier, not a full-model claim. |
| `model_artifact_commitment` | Program, weights, and/or circuit/AIR identity commitment. |
| `proof_native_parameter_commitment` | Proof-friendly commitment to private parameter/table rows when publication hashes are retained for audit/export identity. |
| `input_commitment` | Canonical input vector/state commitment. |
| `output_commitment` | Canonical output vector/state commitment. |
| `config_commitment` | Shape, fixed-point, lookup, normalization, and runtime config commitment. |
| `public_instance_commitment` | Commitment to verifier public inputs/claim fields. |
| `proof_commitment` | Commitment to the Stwo proof object or accepted proof receipt. |
| `verifying_key_commitment` | Stwo verifier/AIR identity commitment, or `null` only if the backend semantics are setup-free and version-bound. |
| `setup_commitment` | Transparent setup/FRI/config commitment or `null` with an explicit domain rule. |
| `evidence_manifest_commitment` | Source handles for program, input, proof, and statement artifacts. |
| `statement_commitment` | Domain-separated commitment over all fields above. |

## Acceptance rule

The verifier should accept only if:

1. The Stwo proof verifies under the expected backend/version/domain.
2. The statement receipt commitment recomputes.
3. The proof public-input digest matches `public_instance_commitment`.
4. The program/weights/config/input/output commitments, `proof_commitment`,
   `proof_native_parameter_commitment`, `verifying_key_commitment`, `setup_commitment`, and
   `evidence_manifest_commitment` recompute from source artifacts or accepted
   source handles.
5. The verifier rejects unknown versions, alternate domains, stale public inputs,
   and receipt fields whose trust class exceeds their evidence support.

## Required mutation matrix

The first implementation must accept a baseline and reject stale-evidence
mutations for:

- primitive/model ID,
- program or weight commitment,
- input commitment,
- output commitment,
- config commitment,
- `proof_native_parameter_commitment` when the statement family uses a
  proof-native private-parameter binding target,
- public-instance commitment,
- proof commitment,
- `verifying_key_commitment`,
- verifier domain,
- backend/proof version,
- setup/FRI/config commitment,
- evidence manifest commitment,
- statement commitment.

The result is not credible if rejection happens only because a mutation produces
malformed syntax. Commitment-valued mutations must use syntactically valid but
wrong commitments. In particular, the `verifying_key_commitment` mutation must
swap the verifier/AIR identity commitment to a valid but wrong value and must be
rejected as a statement-binding failure, not as a parser failure. For d64-v2 and
other dual-commitment statement families, the same rule applies to
`proof_native_parameter_commitment`: mutating it must reject because the native
binding target changed, not because the receipt syntax is malformed.

## Minimum GO result

A minimum primitive GO result is now checked in. The gate note is:

- `docs/engineering/zkai-stwo-statement-bound-primitive-gate-2026-04-29.md`

The result contains:

- one accepted Stwo-native primitive proof,
- one checked `zkAIStatementReceiptV1`-style envelope around that proof,
- a 14-mutation relabeling suite,
- raw proof-only rejection of the proof-public-claim mutation,
- statement-envelope rejection of all 14 mutations,
- exact commands, hashes, and non-claims.

This supports the claim:

> The statement-binding receipt pattern that held for EZKL and snarkjs also
> applies to this repo's Stwo-native transformer-shaped primitive.

It does not support claims of full transformer inference, backend independence,
production zkML throughput, or agent correctness.

## Bounded Transformer-Block Result

The next bounded Stwo-native result is also checked in:

- `docs/engineering/zkai-stwo-statement-bound-transformer-block-result-gate-2026-05-01.md`
- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.json`
- `docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05.json`

That result wraps the checked Stwo proof with a width-4
`transformer-block` statement receipt for
`urn:zkai:ptvm:rmsnorm-gated-affine-residual-block-v1`. The block profile binds
RMSNorm-scale lookup, quantized affine projection, gated value mixing, residual
addition, bounded activation lookup, the proof object, verifier domain, setup
identity, public instance, and source evidence. Raw proof-only verification
rejects only `1 / 14` relabels because most labels are outside the raw proof
acceptance path. The statement receipt rejects `14 / 14`, and the composed
agent-step receipt rejects `36 / 36` nested and cross-layer mutations with the
Rust callback verifier accepting the honest bundle.

This is a real statement-binding and composition result. It is still not a
d64/d128 matched benchmark, not full SwiGLU MLP, not full transformer
inference, not recursive/on-chain verification, and not backend independence.
The next comparison result should move from this width-4 baseline to a matched
d64 or d128 RMSNorm/SwiGLU/residual target before comparing against public zkML
systems.

The follow-up implementation-surface probe narrows the required work:

- `docs/engineering/zkai-d64-rmsnorm-swiglu-surface-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-surface-probe-2026-05.json`

That probe records a direct TVM-fixture-growth NO-GO. A minimal `d=64` target
needs roughly `49,152` projection multiplications and `49,152` weight scalars,
while the current TVM representation has a `u8` address/PC surface and the
checked transformer-block fixture has `21` memory cells, `43` instructions, and
`7` `MulMemory` operations. The next credible result therefore needs a
parameterized vector-block AIR/export path with committed weights, not a larger
hand-written toy fixture.

The next committed-target fixture is also checked in:

- `docs/engineering/zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05.json`

That fixture is a GO for a canonical statement target, not for proof generation.
It pins deterministic signed-q8 RMSNorm-SwiGLU-residual semantics for `d=64`,
`ff_dim=256`, `49,152` projection multiplications, `49,152` projection weight
scalars, and `64` RMS scale scalars (`49,216` total committed parameter
scalars).
It binds model/config/weight/input/output/normalization/activation/public-instance
commitments and rejects `14 / 14` checked relabeling mutations, including a
proof-status overclaim. The next backend must prove this statement, or record an
exact blocker against this fixture rather than against a drifting prose target.

The external-adapter surface probe is now also checked in:

- `docs/engineering/zkai-d64-external-adapter-surface-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-external-adapter-surface-probe-2026-05.json`
- `docs/engineering/evidence/zkai-d64-external-adapter-surface-probe-2026-05.tsv`

That probe records a NO-GO for treating a vanilla external float-style export as
an exact proof of the canonical d64 statement. The exact statement requires
signed-q8 arithmetic, floor-division rounding, integer square-root, a bounded
integer SiLU lookup table, committed parameter tables, and statement-receipt
binding. A naive float-style drift canary changes `61 / 64` output positions, so
approximate export is a different statement unless it gets a separate target and
commitment. The receipt target remains reusable once an exact native or custom
external proof exists.

The JSTprove/Remainder shape probe adds a smaller external proof-stack axis:

- `docs/engineering/zkai-jstprove-shape-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.json`
- `docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.tsv`

That probe is not a d64 benchmark and not a transformer proof, but it is useful
operator-pressure context. Tiny `Gemm -> residual Add` and
`Gemm -> LayerNormalization` fixtures prove and verify under JSTprove/Remainder,
while `Gemm -> Softmax` is refused at proof construction as an unconstrained op
and `Gemm -> Relu` fails witness generation on range-check capacity. This keeps
the research split explicit: statement binding, exact statement semantics, and
backend operator support are separate gates.

The native Stwo vector-row surface probe is also checked in:

- `docs/engineering/zkai-d64-stwo-vector-row-surface-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-stwo-vector-row-surface-probe-2026-05.json`
- `docs/engineering/evidence/zkai-d64-stwo-vector-row-surface-probe-2026-05.tsv`

That probe records the useful split for the next proof PR: the exact d64
arithmetic surface is a GO (`49,920` trace rows excluding the static activation
table, `49,152` projection multiplication rows, max checked intermediate
`849,454`, safely below the signed M31 limit), but exact native proof generation
is still NO-GO-YET until weight and activation-table commitment consistency are
verified inside the relation.

The commitment-consistency method probe chooses the next implementation method:

- `docs/engineering/zkai-d64-commitment-consistency-method-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.json`
- `docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.tsv`

The checked method is a dual commitment surface. Keep the current publication
hashes for audit/export identity, but add a
`proof_native_parameter_commitment` to the d64 statement and bind that field in
the native proof public instance. The probe explicitly rejects metadata-only
binding and external Merkle openings that are not consumed by the proof relation.

The canonical d64-v2 statement fixture carries the field now and rejects
`15 / 15` checked relabeling mutations, including
`proof_native_parameter_commitment`. The remaining proof work is to make the
native relation consume it.

## NO-GO criteria

Record an explicit NO-GO if:

- the existing Stwo proof object does not expose enough stable public claim fields
  to bind input/output/config cleanly,
- proof generation is too expensive for a reproducible PR-sized gate,
- the only available mutations hit parser errors rather than statement-binding
  checks,
- the proof surface is too coupled to an older internal claim format to wrap
  without broad trusted-core changes.

A NO-GO here is still useful. It would identify the missing public-statement
surface that future Stwo-native zkAI proofs must expose.

## PR-sized implementation plan

1. Add a small Stwo statement-receipt builder for the selected primitive.
2. Reuse the existing proof generation path for the primitive; do not create a
   new AIR in the first PR unless required.
3. Emit a checked baseline receipt and proof hash under `docs/engineering/evidence/`.
4. Add a mutation harness that rewrites receipt fields to valid-but-wrong values.
5. Add tests for baseline acceptance and every rejection class.
6. Add a gate note with exact commands and claim boundaries.
7. Only after that, decide whether to promote any sentence into the paper.

## Next-paper direction

If this result lands, the next paper should not be framed as "we made another
zkML prover." The stronger framing is:

> Verifiable AI needs both proof validity and statement binding. Transparent
> Stwo proofs provide the computation evidence; statement receipts bind that
> evidence to model/input/output/config claims; Tablero-style typed boundaries
> make the resulting receipts composable without replaying every dependency.
