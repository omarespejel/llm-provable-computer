# zkAI Attention/KV RISC Zero Scaled Sequence Receipt - 2026-05-05

## Question

Can the three-step attention/KV carried-state receipt be scaled to a larger
fixed sequence while preserving the same fail-closed mutation discipline?

## Result

GO for a narrow eight-step RISC Zero carried-state sequence receipt.

The checked guest reads a private eight-step attention/KV fixture. For each step
it appends the new KV row, recomputes two-wide integer dot-product scores,
selects the highest score with lowest-position tie-break, emits the attention
output, and carries the next KV cache into the following step. The journal
contains every intermediate transition row:

- selected positions: `[0, 2, 3, 4, 5, 4, 5, 6]`;
- attention outputs: `[[2, 1], [4, 2], [5, -2], [0, 6], [7, 1], [0, 6], [7, 1], [-3, 4]]`;
- final KV cache rows: `10`.

This is stronger than the three-step receipt because it keeps the same deletion,
reordering, intermediate-state relabeling, commitment-binding, receipt-metadata,
and metric-smuggling rejection surface while moving from `3` to `8` carried
updates.

Decision:

`GO_ATTENTION_KV_RISC0_SCALED_SEQUENCE_RECEIPT_FOR_CARRIED_KV_STATE`

Claim boundary:

`RISC0_RECEIPT_PROVES_EIGHT_STEP_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_NOT_STWO_OR_SOFTMAX`

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.tsv`
- Receipt artifact: `docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.bincode`
- RISC Zero fixture: `programs/risc0-attention-kv-scaled-sequence-receipt/`
- Gate: `scripts/zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py`

## Checked Metrics

| Metric | Value |
| --- | ---: |
| Proof system | `RISC Zero` |
| RISC Zero version | `3.0.5` |
| Sequence length | `8` transitions |
| Key/value width | `2` / `2` |
| Masking policy | `none` |
| Tie break | `lowest_position` |
| Receipt size | `264146` bytes |
| Proof generation time | `29761.524 ms` |
| Proof generation time source | `current_prove_run` |
| Verifier time | `18.056 ms` |
| Timing policy | `single_local_run_engineering_only` |
| Mutations checked | `27` |
| Mutations rejected | `27` |

The timings are engineering-only single local runs. They are useful for local
regression checks on this artifact, not public benchmark claims against other
systems.

## Mutation Surface

The gate rejects:

- transition deletion;
- transition reordering;
- intermediate prior-KV relabeling;
- intermediate next-KV relabeling;
- intermediate input-query relabeling;
- intermediate attention-output relabeling;
- intermediate score-trace relabeling;
- initial-KV and final-KV relabeling;
- input-step reordering;
- sequence-length relabeling;
- transition-commitment and statement-commitment relabeling;
- route, system, image-id, receipt-commitment, and strict-reverification relabeling;
- proof-size, proof-generation-time, and verifier-time metric smuggling;
- native-Stwo, Softmax, recursion, non-claim, validation-command, and unknown-field smuggling.

## Interpretation

This result answers issue `#444` as a concrete scaling GO for the zkVM carried
state route. The important result is not that eight steps is large; it is that a
real proof object can bind a longer ordered KV-cache update sequence and still
reject the same adversarial edits that mattered for the three-step result.

The result remains deliberately bounded. It does not prove Softmax, full model
inference, long context, native Stwo attention arithmetic, recursion, PCD, or
agent correctness. The next useful scaling questions are tracked in issue `#446`: a wider `d=8` or
`d=16` key/query/value fixture, explicit causal masking, and eventually a native
Stwo attention arithmetic proof for the same public-instance surface.

## Reproduce

```bash
just gate-fast

CARGO_TARGET_DIR=target/risc0-attention-kv-sequence-receipt \
  cargo test --manifest-path programs/risc0-attention-kv-scaled-sequence-receipt/Cargo.toml

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 \
  scripts/zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py \
  --verify-existing \
  --write-json target/zkai-attention-kv-risc0-scaled-sequence-receipt-verify.json \
  --write-tsv target/zkai-attention-kv-risc0-scaled-sequence-receipt-verify.tsv

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_risc0_scaled_sequence_receipt_gate

python3 -m py_compile \
  scripts/zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py

python3 scripts/paper/paper_preflight.py --repo-root .

git diff --check

just gate
```
