# Native Stwo Softmax-Table Proof Byte Accounting

Date: 2026-05-07

Issue: `#469`

## Decision

`GO_JSON_STARK_PROOF_SUBOBJECT_ACCOUNTING_NO_GO_BINARY_PCS_FRI_ACCOUNTING`

This gate records stable JSON subobject byte accounting for the checked native
Stwo bounded Softmax-table attention/KV proof envelopes from issues `#463` and
`#471`.

The true binary PCS/FRI accounting request remains a bounded no-go:

`NO_GO_TYPED_BINARY_STWO_PROOF_COMPONENT_SCHEMA_NOT_EXPOSED`

The reason is concrete. The checked `proof` byte buffer in these envelopes is
not an opaque typed binary proof object. It is UTF-8 JSON with one
`stark_proof` object. That lets us account for stable JSON subobjects below the
top-level sections, but it does not expose a stable typed/binary serialization
schema for PCS/FRI internals.

## Result

| Route | Heads | Score rows | Trace rows | Raw proof bytes | Envelope file bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bounded Softmax-table | 1 | 52 | 64 | 44,692 | 451,982 |
| Bounded Softmax-table | 2 | 104 | 128 | 47,104 | 563,637 |

Doubling heads, score rows, and trace rows adds only `2,412` raw proof bytes
(`1.053969x`) but adds `111,655` checked envelope file bytes (`1.247034x`).
That is the useful engineering signal: the proof object and the checked
statement envelope tell different size stories.

This is not a scaling law. It is one controlled `1 -> 2` head comparison at the
same `d=8`, same sequence length, and same bounded Softmax-table policy.

## Top-Level Proof Sections

The raw proof payload contains exactly one `stark_proof` object with these
canonical JSON section sizes:

| Section | 1 head bytes | 2 head bytes | Delta |
| --- | ---: | ---: | ---: |
| `config` | 136 | 136 | 0 |
| `commitments` | 340 | 346 | 6 |
| `sampled_values` | 19,830 | 20,368 | 538 |
| `decommitments` | 5,494 | 5,798 | 304 |
| `queried_values` | 12,868 | 13,214 | 346 |
| `proof_of_work` | 3 | 4 | 1 |
| `fri_proof` | 5,896 | 7,113 | 1,217 |

The largest top-level raw-proof delta is `fri_proof`, which accounts for
`1,217 / 2,412 = 50.456%` of the raw-proof byte delta.

## FRI JSON Subobjects

Within the JSON `fri_proof`, the dominant increase is decommitment material:

| FRI group | 1 head bytes | 2 head bytes | Delta |
| --- | ---: | ---: | ---: |
| commitments | 686 | 788 | 102 |
| decommitments | 4,036 | 5,054 | 1,018 |
| witnesses | 769 | 821 | 52 |
| last-layer polynomial | 72 | 70 | -2 |
| JSON structure overhead | 333 | 380 | 47 |

The two-head route also has one additional JSON FRI inner layer:

| FRI subobject | 1 head | 2 heads | Delta |
| --- | ---: | ---: | ---: |
| first layer bytes | 1,780 | 1,871 | 91 |
| inner layers bytes | 3,993 | 5,121 | 1,128 |
| inner layer count | 5 | 6 | 1 |
| last-layer polynomial bytes | 72 | 70 | -2 |

This supports a bounded explanation of the `1 -> 2` head proof-size result:
the raw proof delta is mostly FRI/query/decommitment material, not duplicated
per-row statement material.

## Envelope Distortion

The envelope file is a pretty-printed checked artifact, not just the raw proof.
Its canonical subcomponents move differently:

| Envelope component | 1 head bytes | 2 head bytes | Delta |
| --- | ---: | ---: | ---: |
| canonical input JSON | 34,893 | 67,945 | 33,052 |
| canonical proof-byte array JSON | 134,589 | 141,869 | 7,280 |
| canonical envelope metadata JSON | 379 | 412 | 33 |

The checked envelope file delta is `46.291x` the raw proof delta. That does not
mean Stwo proof bytes are growing by that factor. It means the checked
engineering envelope includes duplicated/public statement material and JSON
encoding overhead that must not be confused with proof-object growth.

## Claim Boundary

This gate is:

- JSON subobject proof-byte accounting for two checked native Stwo
  bounded Softmax-table attention/KV proof envelopes;
- engineering evidence for why the raw proof grows modestly in the checked
  `1 -> 2` head point;
- a bounded no-go for true binary PCS/FRI internal accounting until typed
  serializer/schema hooks exist.

This gate is not:

- binary PCS/FRI internal accounting;
- a proof-size scaling law;
- a public performance benchmark row;
- a timing benchmark;
- exact Softmax attention;
- AIR-private lookup arguments;
- full autoregressive inference;
- proof aggregation or recursion;
- controlled-grid coverage.

## Tamper Coverage

The gate rejects `19 / 19` checked mutations:

- single-head proof-size metric smuggling;
- two-head proof-size metric smuggling;
- single-head envelope-size metric smuggling;
- two-head envelope-size metric smuggling;
- top-level `fri_proof` byte smuggling;
- FRI inner-layer byte smuggling;
- FRI decommitment-group byte smuggling;
- sampled-value lane-length smuggling;
- queried-value lane-length smuggling;
- dominant-delta section relabeling;
- binary-accounting overclaim drift;
- claim-boundary binary overclaim drift;
- first-blocker removal;
- envelope-ratio metric smuggling;
- proof-ratio metric smuggling;
- source gate commitment relabeling;
- statement commitment relabeling;
- non-claim removal;
- unknown-field injection.

## Artifacts

- JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05.tsv`
- Script: `scripts/zkai_attention_kv_softmax_table_proof_byte_accounting_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_softmax_table_proof_byte_accounting_gate.py`

## Reproduction

```bash
python3 scripts/zkai_attention_kv_d8_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_two_head_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_softmax_table_proof_byte_accounting_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_softmax_table_proof_byte_accounting_gate

just gate-fast
just gate
```

## Next Research Hooks

1. Expose or build a typed binary proof serializer/schema so this can become
   real binary PCS/FRI component accounting rather than JSON subobject
   accounting.
2. Run the same accounting over a controlled grid across sequence length, head
   count, and width before claiming a proof-size growth law.
3. Work issue `#470` to move bounded Softmax-table membership from public-row
   verifier recomputation into AIR-private table/lookup columns.
