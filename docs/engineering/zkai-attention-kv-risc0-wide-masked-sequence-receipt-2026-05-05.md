# zkAI Attention/KV RISC Zero Wide Masked Sequence Receipt - 2026-05-05

## Question

Can the eight-step carried KV-cache zkVM receipt survive the next honest
transformer-shape stressor: wider key/query/value vectors plus an explicit
causal-prefix masking policy?

## Result

GO for a narrow eight-step, `d=8`, causal-prefix RISC Zero carried-state
sequence receipt.

The checked guest reads a private attention/KV fixture with eight-wide keys,
queries, and values. For each step it appends the new KV row, filters the score
trace to entries whose `position <= token_position`, recomputes integer
dot-product scores, selects the highest score with lowest-position tie-break,
emits the attention output, and carries the next KV cache into the following
step. The journal contains every intermediate transition row:

- selected positions: `[0, 2, 3, 3, 5, 5, 7, 9]`;
- attention outputs:
  `[[2, 1, 0, -1, 3, 0, 1, 2], [4, 2, 1, 0, -1, 3, 2, 1], [5, -2, 0, 3, 1, 1, -1, 2], [5, -2, 0, 3, 1, 1, -1, 2], [7, 1, 2, -2, 0, 5, -3, 1], [7, 1, 2, -2, 0, 5, -3, 1], [6, 6, -2, 0, 2, 1, 3, -1], [-5, 5, 1, -3, 4, 2, -2, 0]]`;
- final KV cache rows: `10`.

This answers issue `#446` as a concrete external-control GO. It is stronger
than the prior eight-step fixture on two axes: key/query/value width moves from
`2` to `8`, and the masking policy is no longer implicit `none`; it is explicit
statement data with value `causal_prefix_position_lte_query_token`.

Decision:

`GO_ATTENTION_KV_RISC0_WIDE_MASKED_SEQUENCE_RECEIPT_FOR_CARRIED_KV_STATE`

Claim boundary:

`RISC0_RECEIPT_PROVES_EIGHT_STEP_D8_CAUSAL_PREFIX_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_NOT_STWO_NOT_SOFTMAX_NOT_RECURSION_OR_PCD_NOT_LONG_CONTEXT_OR_FULL_INFERENCE_NOT_AGENT_CORRECTNESS`

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.tsv`
- Receipt artifact: `docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.bincode`
- RISC Zero fixture: `programs/risc0-attention-kv-wide-masked-sequence-receipt/`
- Gate: `scripts/zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py`

## Checked Metrics

| Metric | Value |
| --- | ---: |
| Proof system | `RISC Zero` |
| RISC Zero version | `3.0.5` |
| Sequence length | `8` transitions |
| Key/value width | `8` / `8` |
| Masking policy | `causal_prefix_position_lte_query_token` |
| Tie break | `lowest_position` |
| Receipt size | `305266` bytes |
| Proof generation time | `236480.807 ms` |
| Proof generation time source | `current_prove_run` |
| Verifier time | `19.193 ms` |
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

This is a useful verifiable-intelligence result because the proof now binds an
ordered carried-state attention/KV update sequence with explicit masking and
wider vectors. In human terms: the verifier is no longer just checking that a
single attention step was wrapped in a statement receipt; it checks a real zkVM
receipt whose guest executed a small but transformer-shaped state update loop and
committed every intermediate state needed to reject relabeling or dropped-state
attacks.

The result remains deliberately bounded. It does not prove Softmax, full model
inference, long context, native Stwo attention arithmetic, recursion, PCD, or
agent correctness. It is an external zkVM control that raises confidence in the
statement-bound carried-state surface and narrows the next native Stwo target.

## Reproduce

```bash
just gate-fast

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" \
CARGO_TARGET_DIR=target/risc0-attention-kv-wide-masked-sequence-receipt \
  cargo test --manifest-path programs/risc0-attention-kv-wide-masked-sequence-receipt/Cargo.toml

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 \
  scripts/zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py \
  --verify-existing \
  --write-json target/zkai-attention-kv-risc0-wide-masked-sequence-receipt-verify.json \
  --write-tsv target/zkai-attention-kv-risc0-wide-masked-sequence-receipt-verify.tsv

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate

python3 -m py_compile \
  scripts/zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py

python3 scripts/paper/paper_preflight.py --repo-root .

git diff --check

just gate
```

## Next GO Criterion

Produce one native Stwo proof that explicitly verifies the chosen attention/KV
transition semantics while preserving the same public-instance fields, causal
masking policy, and intermediate-state rejection surface after proof
serialization. This is tracked in issue `#448`. If native Stwo remains blocked,
the next external-control stressor is `d=16`, multi-head, or longer-context
carried-state evidence with the same fail-closed mutation discipline.
