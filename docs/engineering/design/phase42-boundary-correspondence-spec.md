# Phase42 Boundary Correspondence Decision Gate

Control issue: <https://github.com/omarespejel/provable-transformer-vm/issues/180>

## Purpose

Phase42 is a kill test for the current Paper 3 breakthrough route. It decides
whether the Phase29/30/41 boundary stack can become proof-bearing composition
or whether the project should pivot to direct layerwise/tensor proving.

The question is deliberately narrow:

```text
Can Phase30 / Phase12 public-state boundaries be related to
Phase29 / Phase28 / Phase14 / Phase23 boundary-state commitments
from real source artifacts?
```

If the answer is yes, Phase43 can consume a proof-bearing boundary bridge. If
the answer is no, more manifest layers would be misleading and the project
should pivot.

## Source Surfaces

Phase29 exposes the Phase28-derived aggregation boundary:

```text
phase29.global_start_state_commitment
phase29.global_end_state_commitment
phase29.input_contract_commitment
phase29.source_template_commitment
phase29.aggregation_template_commitment
```

Phase30 exposes the Phase12 decode-chain boundary:

```text
phase30.chain_start_boundary_commitment
phase30.chain_end_boundary_commitment
phase30.source_chain_commitment
phase30.step_envelopes_commitment
phase30.envelopes[*].input_boundary_commitment
phase30.envelopes[*].output_boundary_commitment
```

Phase41 exposes a source-bound pair witness:

```text
phase41.phase29_global_start_state_commitment
phase41.phase29_global_end_state_commitment
phase41.phase30_chain_start_boundary_commitment
phase41.phase30_chain_end_boundary_commitment
phase41.start_boundary_translation_commitment
phase41.end_boundary_translation_commitment
phase41.boundary_translation_witness_commitment
```

Phase41 is necessary evidence, but it is not sufficient for Phase42 success.
It proves that both boundary domains are bound to the same Phase29/30 sources;
it does not prove that the two domains encode the same underlying boundary
preimage.

## Relation Contract

The only acceptable Phase42 relation outcomes are:

| Outcome | Meaning |
|---|---|
| `equality` | Phase29 and Phase30 already expose identical start/end boundary commitments. |
| `projection` | Phase30 boundaries are a deterministic subset of the Phase29/Phase28 boundary preimage. |
| `deterministic_transform` | A fixed public transform maps the Phase29/Phase28 boundary preimage to the Phase30/Phase12 boundary. |
| `hash_preimage_relation` | Both domains hash or commit different encodings of the same exposed underlying boundary preimage. |
| `impossible` | Current artifacts do not expose enough source data to define a non-witness-only relation. |

Any other wording is not a Phase42 success condition.

## Current Decision State

For the current Phase29/30/41 artifact surface, the executable decision gate is:

```text
relation_outcome = impossible
decision = patch_required
```

This does not mean the full route is globally impossible. It means the current
serialized artifacts expose a source-bound Phase41 boundary pair, but they do
not expose the Phase12 public-state preimage and Phase14/23 boundary-state
preimage needed to classify the relation as `projection`,
`deterministic_transform`, or `hash_preimage_relation`.

The next stay-current-path step is therefore one minimal upstream exposure
patch: expose or derive the missing preimage data in a way the Phase42 checker
can recompute from real sources. If that cannot be done without witness-only
claims, Issue #180 requires a pivot.

## Required Checker Behavior

The Phase42 checker must:

- refer to Issue #180 in its output;
- verify the Phase29 input contract commitment;
- verify Phase30 envelope commitments, chain boundaries, step links, layout
  commitments, and step-envelope list commitment;
- verify Phase41 internal commitments when a witness is supplied;
- verify Phase41 source binding against Phase29 and Phase30;
- reject stale Phase29 or Phase30 commitments;
- reject swapped or stale Phase41 boundaries;
- report Phase41-only compatibility as `patch_required`, not success.

The checker is intentionally stricter than a descriptive manifest. It is a
decision tool: either the boundary relation is clean, or the route is blocked.

## Pass Criteria

Stay on the current route only if a later Phase42 update can report:

```json
{
  "issue": 180,
  "accepted": true,
  "relation_outcome": "projection | deterministic_transform | hash_preimage_relation",
  "decision": "stay_current_path"
}
```

`equality` is also accepted, but it means Phase31 direct binding should be used
instead of Phase41 translation.

## Fail Criteria

Pivot if Phase42 remains at:

```json
{
  "issue": 180,
  "accepted": false,
  "relation_outcome": "impossible",
  "decision": "patch_required"
}
```

after one minimal attempt to expose the missing source preimages, or if any
mutation test can satisfy the checker with synthetic/witness-only
compatibility.

## Non-Claims

Phase42 does not claim:

- recursive proof closure;
- cryptographic compression;
- full standard-softmax transformer inference;
- external benchmark superiority;
- that Phase41 alone makes Phase31/37 pass.

