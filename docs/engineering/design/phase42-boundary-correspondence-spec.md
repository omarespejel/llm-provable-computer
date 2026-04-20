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

The checker emits only these decision labels:

| Decision | Meaning |
|---|---|
| `stay_current_path` | The exposed relation is clean enough to keep building the current route. |
| `patch_once_then_stay` | One bounded source-exposure patch is required before continuing. |
| `pivot` | The current route should move to the layerwise/tensor path. |
| `stop_and_reassess` | The evidence is inconsistent enough that no automatic route decision is safe. |

## Current Decision State

For the Phase29/30/41-only artifact surface, the executable decision gate is:

```text
relation_outcome = impossible
decision = patch_once_then_stay
```

This does not mean the full route is globally impossible. It means the current
serialized artifacts expose a source-bound Phase41 boundary pair, but they do
not expose the Phase12 public-state preimage and Phase14/23 boundary-state
preimage needed to classify the relation as `projection`,
`deterministic_transform`, or `hash_preimage_relation`.

The first minimal upstream exposure is a Phase42 boundary-preimage evidence
file. It carries:

```text
phase12_start_state
phase12_end_state
phase14_start_state
phase14_end_state
```

The checker recomputes:

```text
commit_phase12_public_state(phase12_start_state)
commit_phase12_public_state(phase12_end_state)
commit_phase14_public_state(phase14_start_state)
commit_phase14_public_state(phase14_end_state)
commit_phase23_boundary_state(phase14_start_state)
commit_phase23_boundary_state(phase14_end_state)
```

and then verifies:

```text
Phase12 start/end commitments == Phase30 chain start/end boundaries
Phase23 start/end commitments == Phase29 global start/end boundaries
Phase12 and Phase14 preimages share the same carried-state core
```

When those checks pass, the intended relation outcome is:

```text
relation_outcome = hash_preimage_relation
decision = stay_current_path
```

This keeps the success criterion proof-oriented: Phase42 succeeds only when the
two boundary domains are recomputable from exposed preimages, not when a
witness merely says they are compatible.

The Rust Phase42 source-bound implementation makes this gate stricter than the
synthetic JSON checker. It can construct and verify the boundary-preimage
evidence object, but that object still rejects real Phase12/28/29/30 sources:
Phase12 and Phase14 share the carried execution fields, but their
`kv_history_commitment` fields are different commitment domains. Phase12 uses a
linear history chain, while Phase14 uses the chunked history accumulator carried
into Phase23.

The next minimal patch is a separate Phase42 history-equivalence witness:

```text
witness_version = phase42-boundary-history-equivalence-witness-v1
relation_outcome = deterministic_transform
transform_rule = phase12-chain-replay-to-phase14-chunked-history-v1
full_history_replay_required = true
cryptographic_compression_claimed = false
```

This witness does not weaken the boundary-preimage evidence. Instead, it
replays the real Phase12 chain into the Phase14 chunked-history construction,
checks that the replayed Phase14 start/end states are exactly the Phase28 global
boundary preimages, and binds the append stream plus lookup-row replay with
commitments. If the live source stack accepts this witness, the current path is
not killed, but it is still not a final breakthrough result: Phase43 must
replace full replay with a compact proof or the route remains too expensive.

## Required Checker Behavior

The Phase42 checker must:

- refer to Issue #180 in its output;
- expose executable inputs for `--phase29`, `--phase30`, optional `--phase41`,
  and optional `--boundary-preimage-evidence`;
- verify the Phase29 input contract commitment;
- verify Phase30 envelope commitments, chain boundaries, step links, layout
  commitments, and step-envelope list commitment;
- verify Phase41 internal commitments when a witness is supplied;
- verify Phase41 source binding against Phase29 and Phase30;
- verify optional Phase42 boundary-preimage evidence;
- reject stale Phase29 or Phase30 commitments;
- reject swapped or stale Phase41 boundaries;
- reject Phase12/Phase14 preimages that do not recompute to the Phase30/Phase29
  boundary commitments;
- reject Phase12/Phase14 shared carried-state-core mismatches;
- report Phase41-only compatibility as `patch_once_then_stay`, not success.

History-equivalence-witness validation remains future work for a later Phase42
update. The current checker has no history-equivalence-witness CLI input, so it
does not yet reject full real source stacks solely because Phase12 linear history
and Phase14 chunked history are not bridged by that witness.

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

A full-replay `deterministic_transform` witness is an intermediate keep-alive
signal, not final success. It can justify proceeding to Phase43 only if it is
source-bound, mutation-tested, and explicit that no cryptographic compression is
claimed.

## Fail Criteria

Pivot if Phase42 remains at:

```json
{
  "issue": 180,
  "accepted": false,
  "relation_outcome": "impossible",
  "decision": "patch_once_then_stay"
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
