# zkAI Stwo statement-bound transformer-block gate - 2026-04-30

## Question

Define the smallest honest next target after the checked Stwo
linear-block-with-lookup statement receipt:

> Can this repository produce a Stwo-native statement-bound proof for one
> transformer-shaped block, while preserving the relabeling rejection discipline
> already checked for external adapters, the native Stwo primitive, and the
> composed agent-step receipt?

This is a design and implementation gate. It is not yet a proof result.

## Current baseline

The current checked native Stwo result is intentionally smaller:

- proof system: `stwo-transparent-stark`
- proof-system version: `stwo-phase10-linear-block-v4-with-lookup`
- statement kind: `transformer-primitive`
- model ID: `urn:zkai:ptvm:linear-block-v4-with-lookup`
- checked statement-envelope result: raw proof-only verification rejects
  `1 / 14` checked relabels, while the statement envelope rejects `14 / 14`
- checked agent composition result: the composed receipt rejects `36 / 36`
  checked nested and cross-layer mutations

The baseline establishes the binding lesson:

> proof validity is not statement validity.

It does not establish transformer-block semantics.

## Target

The next target is:

- name: `rmsnorm-affine-residual-block-v1`
- statement kind: `transformer-block`
- width: `4`
- integer domain: signed fixed-width quantized M31-compatible integers
- required operations:
  - `rmsnorm_scale_lookup`
  - `quantized_affine_projection`
  - `residual_add`

The target is deliberately small. A width-4 block is large enough to include
real transformer structure and small enough to keep proof-generation debugging
bounded.

## Binding surface

The statement receipt must bind at least these public fields:

- `model_artifact_commitment`
- `model_config_commitment`
- `input_commitment`
- `output_commitment`
- `public_instance_commitment`
- `proof_commitment`
- `verifying_key_commitment`
- `setup_commitment`
- `verifier_domain`
- `proof_system_version`
- `evidence_manifest_commitment`

The implementation should reject a relabeling of any of these fields after
recomputing unrelated wrapper digests.

## GO criteria

This track is a GO only if all of the following pass:

1. A native Stwo verifier accepts one honest transformer-block instance with the
   declared width, operations, and public instance.
2. The zkAI statement receipt binds every public commitment listed above.
3. The mutation suite rejects model, input, output, config, proof,
   public-instance, verifier-domain, proof-system-version, setup,
   verifying-key, and evidence-manifest relabeling.
4. The composed agent-step receipt accepts the honest transformer-block
   statement receipt as its model subreceipt.
5. The Rust callback path rejects at least one nested statement-receipt
   relabeling and one cross-layer agent-field relabeling.

## NO-GO criteria

Stop and record a NO-GO if any of these happen:

1. The Stwo path cannot emit an honest proof for the declared block without
   removing normalization or residual semantics.
2. The verifier accepts any statement-receipt mutation after recomputing
   unrelated digests.
3. The target collapses into a plain linear toy by dropping both normalization
   and residual structure.
4. The verifier accepts a proof whose public instance no longer matches the
   receipt commitment.

## Artifacts

The machine-readable gate is:

- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-plan-2026-04.json`

The validator is:

- `scripts/zkai_stwo_transformer_block_plan.py`

Focused tests:

```bash
python3 -m unittest scripts.tests.test_zkai_stwo_transformer_block_plan
```

Validate the gate plan:

```bash
python3 scripts/zkai_stwo_transformer_block_plan.py --json
```

## Non-claims

- This is not full transformer inference.
- This is not an agent reasoning proof.
- This is not a throughput or latency benchmark.
- This is not backend independence.
- This is not recursive or on-chain verification.
- This does not claim that the existing linear-block primitive already proves
  transformer-block semantics.
- This does not claim model truthfulness, policy compliance, or tool-output
  truth.

## Next implementation PR

The next PR should implement the bounded harness, not expand the claim:

1. Build one honest width-4 fixture.
2. Generate or load one native Stwo proof for the declared block.
3. Construct a `zkai-statement-receipt-v1` for that proof.
4. Run a statement-relabeling mutation suite.
5. Compose the checked statement receipt into the agent-step receipt callback
   path.
6. Record GO or NO-GO explicitly.
