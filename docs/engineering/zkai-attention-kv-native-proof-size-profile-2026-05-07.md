# ZKAI Attention/KV Native Proof-Size Profile (2026-05-07)

## Decision

`GO_TWO_POINT_NATIVE_STWO_ATTENTION_KV_PROOF_SIZE_PROFILE_ENGINEERING_ONLY`

Issue `#467` now has a checked two-point profile over the existing native Stwo
bounded weighted attention/KV artifacts:

- single-head `d=8`, sequence length `8`;
- two-head `d=8`, sequence length `8` per head.

This is an engineering profile, not a public benchmark row and not a scaling law.

## Checked Result

| Route | Heads | Score rows | Trace rows | Proof bytes | Envelope bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single-head bounded weighted | 1 | 52 | 64 | 36,769 | 386,078 |
| Two-head bounded weighted | 2 | 104 | 128 | 41,175 | 512,060 |

Derived ratios:

| Metric | Ratio |
| --- | ---: |
| Score rows | 2.000000x |
| Trace rows | 2.000000x |
| Proof bytes | 1.119829x |
| Envelope bytes | 1.326312x |
| Proof-byte growth / score-row growth | 0.559915x |
| Envelope-byte growth / score-row growth | 0.663156x |

The interesting signal is that rows double exactly while proof bytes grow by
only `4,406` bytes. The envelope grows more (`125,982` bytes) because the
checked JSON artifact carries duplicated statement/input/proof material, so the
profile deliberately separates raw proof bytes from checked-envelope bytes.

The raw proof bytes are a compact JSON payload containing one `stark_proof`
object. The gate now decomposes that proof object into top-level JSON section
sizes:

| Proof section | Single-head bytes | Two-head bytes | Delta |
| --- | ---: | ---: | ---: |
| `config` | 136 | 136 | 0 |
| `commitments` | 335 | 345 | 10 |
| `sampled_values` | 15,066 | 15,701 | 635 |
| `decommitments` | 5,408 | 6,504 | 1,096 |
| `queried_values` | 9,801 | 10,329 | 528 |
| `proof_of_work` | 4 | 4 | 0 |
| `fri_proof` | 5,894 | 8,031 | 2,137 |
| JSON wrapper overhead | 125 | 125 | 0 |

The proof-byte delta is exactly accounted for by top-level proof sections:
`36,769 -> 41,175` is `+4,406` bytes, and the top-level section payload delta is
also `+4,406` bytes while wrapper overhead stays constant.

The checked proof configuration is the same in both artifacts:

```json
{
  "fri_config": {
    "fold_step": 1,
    "log_blowup_factor": 1,
    "log_last_layer_degree_bound": 0,
    "n_queries": 3
  },
  "lifting_log_size": null,
  "pow_bits": 10
}
```

The gate records missing structural fields explicitly rather than inferring
them:

| Field | Status |
| --- | --- |
| Preprocessed columns | not exposed by current native gate |
| Base trace columns | not exposed by current native gate |
| Extension columns | not exposed by current native gate |
| Prover time | not measured by this profile |
| Verifier time | not measured by this profile |

The controlled-grid status is also explicit: this profile covers only
`head_count in {1, 2}` at `sequence_length_per_head = 8`; sequence lengths `4`
and `16`, plus a possible `4`-head fixture, remain open under issue `#467`.

## Interpretation

This is positive for the STARK-transformer research lane, but it must stay
bounded:

- The current two-point proof-byte signal is consistent with fixed PCS/FRI
  overhead dominating at tiny attention/KV sizes.
- The result does not prove a general sublinear proof-size law.
- The profile decomposes top-level JSON proof sections, but not binary
  PCS/FRI internals or a deep Merkle/query accounting.
- The profile records proof configuration, but the current native gate does not
  expose preprocessed, base, or extension column counts.
- The profile includes no new timing data.

The right paper-safe sentence is:

> In the current native Stwo attention/KV fixtures, moving from one to two
> heads doubles score rows and trace rows while raw proof bytes grow from
> 36,769 to 41,175. The `4,406`-byte delta is concentrated in top-level
> `fri_proof` and `decommitments` sections. We treat this as engineering
> evidence of fixed-overhead pressure at small sizes, not as a scaling-law
> benchmark.

## Mutation Coverage

The profile gate rejects all checked mutation classes:

- single-head proof-size metric smuggling;
- two-head proof-size metric smuggling;
- single-head envelope-size metric smuggling;
- two-head envelope-size metric smuggling;
- row-ratio metric smuggling;
- proof-ratio metric smuggling;
- FRI-section metric smuggling;
- controlled-grid status overclaim;
- column-breakdown overclaim;
- source gate commitment relabeling;
- statement commitment relabeling;
- scaling-law overclaim drift;
- interpretation overclaim drift;
- first-blocker removal;
- public benchmark timing-policy overclaim;
- binary proof-component byte-breakdown overclaim;
- non-claim removal;
- unknown-field injection.

All `18 / 18` mutation cases reject.

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-native-proof-size-profile-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-native-proof-size-profile-2026-05.tsv`
- Gate commitment:
  `blake2b-256:361c252d0bea7c042a78dbeb8512c4c8ae5af4115b8c34cdbf1e37b04c452311`

## Reproduction

```bash
python3 scripts/zkai_attention_kv_d8_bounded_weighted_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.tsv
python3 scripts/zkai_attention_kv_two_head_bounded_weighted_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.tsv
python3 scripts/zkai_attention_kv_proof_size_profile_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-native-proof-size-profile-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-native-proof-size-profile-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_kv_proof_size_profile_gate
```

## Next Research Lead

The next stronger result is a controlled grid:

- head count: `1`, `2`, maybe `4`;
- sequence length per head: `4`, `8`, `16`;
- width: `d=8`;
- semantics: bounded weighted only.

That grid is required before this profile can become paper-facing proof-size
evidence.
