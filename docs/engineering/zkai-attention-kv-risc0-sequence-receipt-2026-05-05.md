# zkAI Attention/KV RISC Zero Sequence Receipt - 2026-05-05

## Question

Can the one-transition attention/KV semantics receipt be extended to a real
carried-state sequence without claiming native Stwo attention proving, Softmax,
recursion, or full inference?

## Result

GO for a narrow RISC Zero carried-state sequence receipt.

The checked guest reads a private three-step attention/KV fixture. For each step
it appends the new KV row, recomputes two-wide integer dot-product scores,
selects the highest score with lowest-position tie-break, emits the attention
output, and carries the next KV cache into the following step. The journal
contains every intermediate transition row:

- step `0`: selected position `0`, output `[2, 1]`;
- step `1`: selected position `2`, output `[4, 2]`;
- step `2`: selected position `3`, output `[5, -2]`;
- final KV cache rows: `5`.

This is materially stronger than the one-transition receipt because the gate now
checks carried-state integrity: deleting, reordering, or relabeling an
intermediate transition rejects.

Decision:

`GO_ATTENTION_KV_RISC0_SEQUENCE_RECEIPT_FOR_CARRIED_KV_STATE`

Claim boundary:

`RISC0_RECEIPT_PROVES_THREE_STEP_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_NOT_STWO_OR_SOFTMAX`

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.tsv`
- Receipt artifact: `docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.bincode`
- RISC Zero fixture: `programs/risc0-attention-kv-sequence-receipt/`
- Gate: `scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_risc0_sequence_receipt_gate.py`

## Checked Metrics

| Metric | Value |
| --- | ---: |
| Proof system | `RISC Zero` |
| RISC Zero version | `3.0.5` |
| Sequence length | `3` transitions |
| Key/value width | `2` / `2` |
| Masking policy | `none` |
| Tie break | `lowest_position` |
| Receipt size | `246730` bytes |
| Proof generation time | `13568.944 ms` |
| Verifier time | `21.225 ms` |
| Timing policy | `single_local_run_engineering_only` |
| Mutations checked | `27` |
| Mutations rejected | `27` |

The timings are engineering-only single local runs. They are useful to detect
large regressions in this artifact, not as public benchmark claims against other
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

This is the first attention/KV artifact in this repository where a proof-backed
external route covers more than one state update. It demonstrates the important
verifiable-intelligence property in miniature: the proof does not only certify a
single output; it certifies an ordered sequence of state transitions whose
intermediate KV caches cannot be silently deleted, reordered, or relabeled.

The result is still deliberately bounded. It does not prove Softmax, full model
inference, long context, native Stwo attention arithmetic, recursion, PCD, or
agent correctness. The next stronger native result remains a local Stwo proof for
the same attention/KV semantics surface. A separate scaling result would increase
sequence length and key/value width under the same mutation discipline.

## Reproduce

```bash
cargo test --manifest-path programs/risc0-attention-kv-sequence-receipt/Cargo.toml

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 \
  scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py \
  --verify-existing \
  --write-json target/zkai-attention-kv-risc0-sequence-receipt-verify.json \
  --write-tsv target/zkai-attention-kv-risc0-sequence-receipt-verify.tsv

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_risc0_sequence_receipt_gate

python3 -m py_compile \
  scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_sequence_receipt_gate.py
```
