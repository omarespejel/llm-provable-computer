# d64 block receipt composition gate - 2026-05-02

## Question

Can the checked native d64 proof slices be composed into one statement-bound
block receipt without claiming recursive proof compression?

## Decision

**GO for a statement-bound composition receipt over checked slice evidence
handles.**

This result consumes the six checked d64 slice artifacts:

1. RMSNorm public rows.
2. RMSNorm-to-projection bridge.
3. Gate/value projection.
4. Activation/SwiGLU.
5. Down projection.
6. Residual add / final output binding.

The composition gate verifies that these slice handles form one ordered
commitment chain ending at the final d64 `output_activation_commitment`, then
exposes one domain-separated `block_receipt_commitment`.

## Result

| Field | Value |
| --- | --- |
| Decision | `GO_D64_BLOCK_RECEIPT_COMPOSITION_GATE` |
| Slice count | `6` |
| Total checked slice rows | `49,600` |
| Mutation cases | `14 / 14` rejected |
| Block receipt commitment | `blake2b-256:b902e651e7bb78fcf6dac5d7162c6c10fb3694dd1066a0b675e49aae18e39d42` |
| Slice-chain commitment | `blake2b-256:52727069692d826d8549f730cd1ccf052e40dfeed7e6525ba2256fbaf8ae099e` |
| Evidence-manifest commitment | `blake2b-256:f82ec7049be3c6635b5a726b5add9f76f293351be75d52514afa000c7f6a7d5c` |

## What the receipt binds

The block receipt binds:

- model config: target, width, feed-forward dimension, fixed-point scale,
  activation clamp, fixture schema, and required backend version;
- `input_activation_commitment`;
- `output_activation_commitment`;
- `proof_native_parameter_commitment`;
- `public_instance_commitment`;
- original d64 `statement_commitment`;
- verifier domain;
- exact slice schemas and proof-version identifiers;
- source evidence file hashes and payload hashes;
- the ordered slice commitment chain.

## Chain verified

The gate checks these edges:

```text
input_activation_commitment
  -> RMSNorm public rows
  -> rmsnorm_output_row_commitment
  -> projection-input bridge
  -> projection_input_row_commitment
  -> gate/value projection
  -> gate_projection_output_commitment
  -> value_projection_output_commitment
  -> gate_value_projection_output_commitment
  -> activation/SwiGLU
  -> hidden_activation_commitment
  -> down projection
  -> residual_delta_commitment
  -> residual add with original input_activation_commitment
  -> output_activation_commitment
```

This is the first local d64 artifact that presents the slice chain as one
verifier-facing receipt. It is still a composition receipt, not a recursive
aggregate proof.

## Fail-closed coverage

The mutation suite rejects:

- missing bridge slice;
- reordered bridge/projection slices;
- duplicated final slice with missing down-projection slice;
- stale hidden activation edge;
- stale residual-delta edge;
- residual-delta commitment relabeled as final output;
- backend-version drift;
- verifier-domain drift;
- slice proof-version drift;
- model-config drift;
- input-commitment drift;
- output-commitment drift;
- source evidence payload-hash drift after outer recommit;
- source evidence file-hash drift after outer recommit.

The tests also check direct RMSNorm row-relation drift and down-projection
source drift.

## Why this is the right next result

Modern proof systems separate local proof validity from the higher-level claim
being made about that proof. The repo's external adapters already show this for
EZKL, snarkjs, JSTprove, and native Stwo. The d64 path now applies the same
lesson to a transformer-shaped native route: a verifier-facing object should
bind not only "some slice proof accepted" but also the ordered statement chain
that gives the proof its meaning.

This is also the correct intermediate object before recursive or
proof-carrying-data work. Recursive composition should aggregate a receipt like
this, not a loose collection of slice files whose statement chain is only
understood by prose.

## Non-claims

This result does **not** claim:

- recursive aggregation of the six slice proofs;
- one compressed verifier object;
- private parameter-opening proof;
- model-scale transformer inference;
- verifier-time benchmark evidence;
- onchain deployment evidence.

## Follow-up issues

- `#377`: recursive or proof-carrying-data aggregation for the d64 block
  receipt.
- `#376`: d128 layerwise receipt comparator target for source-backed comparison
  against public layerwise zkML context.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.tsv`
- Script:
  `scripts/zkai_d64_block_receipt_composition_gate.py`
- Tests:
  `scripts/tests/test_zkai_d64_block_receipt_composition_gate.py`

## Reproduce

```bash
python3 scripts/zkai_d64_block_receipt_composition_gate.py \
  --write-json docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_block_receipt_composition_gate

python3 -m py_compile \
  scripts/zkai_d64_block_receipt_composition_gate.py \
  scripts/tests/test_zkai_d64_block_receipt_composition_gate.py

python3 scripts/paper/paper_preflight.py --repo-root .

git diff --check
```
