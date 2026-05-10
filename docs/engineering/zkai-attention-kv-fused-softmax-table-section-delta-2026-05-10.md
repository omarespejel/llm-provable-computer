# zkAI Attention/KV Fused Softmax-Table Section Delta - 2026-05-10

Issue: `#531`

## Question

The fused Softmax-table route matrix showed that one native Stwo proof object is
smaller than the matched source-plus-LogUp-sidecar pair across ten checked
profiles. The microprofile accounted for the fused proof bytes themselves.

This gate asks the next narrower question: where does the matched source+sidecar
versus fused saving appear at the exposed serialized `stark_proof` section
boundary?

## Decision

`GO_MATCHED_SOURCE_SIDECAR_VS_FUSED_STARK_PROOF_SECTION_DELTA_WITH_BACKEND_INTERNAL_SPLIT_NO_GO`

GO for matched source/sidecar/fused proof-section delta accounting across the
ten checked native Stwo fused Softmax-table routes.

NO-GO for backend-internal attribution between source arithmetic columns and
LogUp lookup columns. The checked proof envelopes expose serialized STARK proof
sections, not semantic column labels or byte spans. This gate records the useful
surface-level delta and keeps the backend-internal split as a non-claim.

## Artifacts

- JSON: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.tsv`
- Script: `scripts/zkai_attention_kv_fused_softmax_table_section_delta_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_fused_softmax_table_section_delta_gate.py`

Section-delta commitment:

`blake2b-256:cebba20d83321af95c77af424422dcbc8850b0a16543df24cd7ed1ec0a977448`

## Aggregate Read

Across the ten checked matched profiles:

| Role | Proof bytes |
|---|---:|
| Source arithmetic proofs | 591,286 |
| LogUp sidecar proofs | 222,856 |
| Source + sidecar total | 814,142 |
| Fused proofs | 629,466 |
| Fused saving | 184,676 |

Where the `184,676` saved bytes appear:

| Bucket | Saved bytes | Share of saving |
|---|---:|---:|
| Opening bucket (`decommitments` + `fri_proof`) | 171,328 | 92.7722% |
| Query bucket (`sampled_values` + `queried_values`) | 7,254 | 3.928% |
| Commitment bucket | 3,456 | 1.871% |
| Config + proof-of-work | 1,388 | 0.752% |
| JSON wrapper | 1,250 | 0.677% |

The opening bucket splits as:

| Section | Saved bytes |
|---|---:|
| `fri_proof` | 102,304 |
| `decommitments` | 69,024 |

## Interpretation

The useful result is not just that the fused proof is smaller. The checked delta
shows why it is smaller at the proof-object boundary: the fused route mostly
avoids carrying a second opening surface. In this artifact, `92.7722%` of the
saved bytes come from the opening bucket, dominated by FRI proof and
decommitment material.

That is the STARK-native engineering story: when attention arithmetic and table
membership are fused into one proof object, the proof no longer pays two mostly
separate opening surfaces for the source and lookup sidecar.

## Claim Boundary

This gate is:

- matched source-plus-sidecar versus fused proof-section accounting;
- checked over the same ten profiles as the route matrix;
- proof-byte evidence only;
- a GO for exposed serialized STARK proof-section deltas;
- a NO-GO for backend-internal source-vs-lookup attribution.

This gate is not:

- backend-internal source arithmetic versus lookup byte attribution;
- binary PCS/FRI internal accounting;
- timing evidence;
- a public benchmark;
- exact real-valued Softmax;
- full inference;
- recursion or PCD.

The validation also freezes route metadata and proof-schema inventories for the
ten checked profiles, including the legacy `null` schema status on source and
sidecar envelopes and the explicit fused proof schema for each fused route.

## Validation

Regenerate the section-delta evidence:

```bash
python3 scripts/zkai_attention_kv_fused_softmax_table_section_delta_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.tsv
```

Run the focused tests:

```bash
python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_section_delta_gate
```

Run the broader gate stack before merging:

```bash
just gate-fast
just gate
```

## Next Research Hooks

1. Add backend-native labels or counters for source arithmetic columns, LogUp
   lookup columns, and shared PCS/FRI material so issue `#531` can become true
   backend-internal attribution.
2. Add binary proof serialization hooks so JSON-section accounting can be
   replaced by binary PCS/FRI accounting.
3. Use this section-delta result to guide the next larger fused route: prioritize
   shapes where a separate lookup sidecar would otherwise add another opening
   surface.
