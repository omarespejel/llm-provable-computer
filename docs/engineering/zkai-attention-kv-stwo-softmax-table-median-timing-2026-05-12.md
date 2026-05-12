# Stwo Softmax-table median timing gate

Date: 2026-05-12

## Purpose

Add an engineering-local median-of-5 verifier timing harness for the existing
Stwo Softmax-table source arithmetic, LogUp sidecar, and fused route family.

This is a verification-timing discipline gate. It is not a paper benchmark and
not a production performance claim.

## Decision

`GO_ENGINEERING_LOCAL_MEDIAN_OF_5_VERIFY_TIMING_HARNESS`

The gate now records `11` route profiles, `33` existing proof envelopes, and
`165` in-process typed verifier runs.

## Timing policy

- Policy:
  `median_of_5_existing_typed_envelope_verifier_runs_microsecond_capture_engineering_only`
- Scope:
  `existing_envelope_loaded_once_then_typed_stwo_verify_function_timed_in_process`
- Excluded from timed window:
  - proof generation,
  - cargo/build time,
  - subprocess startup,
  - file reads,
  - JSON deserialization.

The Rust timing binary loads and deserializes each existing envelope once, then
times five calls to the matching typed Stwo verifier function with
`std::time::Instant`.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.tsv`
- Rust harness:
  `src/bin/zkai_attention_kv_stwo_softmax_table_timing.rs`
- Python gate:
  `scripts/zkai_attention_kv_stwo_median_timing_gate.py`

Checked summary:

| Metric | Value |
| --- | ---: |
| Profiles checked | `11` |
| Route envelope rows checked | `33` |
| Verifier runs captured | `165` |
| Mutation cases rejected | `13 / 13` |
| Min fused median verify time | `6,070 us` |
| Max fused median verify time | `136,566 us` |

Selected profile medians:

| Profile | Source + sidecar median | Fused median | Fused / source+sidecar |
| --- | ---: | ---: | ---: |
| `d8_single_head_seq8` | `3,821 us` | `6,417 us` | `1.679403x` |
| `d16_single_head_seq8` | `4,608 us` | `6,070 us` | `1.317274x` |
| `d32_single_head_seq8` | `8,537 us` | `12,073 us` | `1.414197x` |
| `d8_two_head_seq32` | `50,014 us` | `136,566 us` | `2.730555x` |
| `d16_two_head_seq16` | `21,052 us` | `63,760 us` | `3.028691x` |

## Interpretation

This gate is useful, but it does **not** support a verifier-time win claim for
the fused route on this host. Most selected fused envelopes are slower to verify
than the measured source+sidecar median sum in this local run. This is
engineering-local timing evidence, not a public benchmark claim.

That does not contradict the current STARK-native architecture thesis. The
stronger checked result remains proof-object plumbing and byte accounting:
fusion can share proof structure and reduce proof-object bytes across controlled
profiles. This timing gate adds discipline around the next question instead of
turning proof-size evidence into an unsupported speed claim.

## Non-claims

- Not prover timing.
- Not cargo or build timing.
- Not subprocess timing.
- Not a public benchmark.
- Not exact real-valued Softmax.
- Not full inference.
- Not recursion or PCD.

## Reproduction

```bash
cargo +nightly-2025-07-14 run --locked --release --features stwo-backend \
  --bin zkai_attention_kv_stwo_softmax_table_timing -- \
  --evidence-dir docs/engineering/evidence --runs 5

python3 scripts/zkai_attention_kv_stwo_median_timing_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_median_timing_gate

cargo +nightly-2025-07-14 test --locked --release --features stwo-backend \
  --bin zkai_attention_kv_stwo_softmax_table_timing

cargo +nightly-2025-07-14 fmt --check

git diff --check
```
