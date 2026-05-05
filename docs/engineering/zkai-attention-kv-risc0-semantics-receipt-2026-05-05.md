# zkAI Attention/KV RISC Zero Semantics Receipt - 2026-05-05

## Question

Can the attention/KV state-binding fixture be backed by a real zkVM receipt
whose guest computes the transition semantics, rather than only binding a
precomputed source contract?

## Result

GO, with a narrow claim boundary.

The checked RISC Zero guest reads the tiny single-head attention/KV fixture,
appends the new KV row, recomputes integer dot-product attention scores under
an explicit no-mask policy, selects the maximum score with the lowest-position
tie break, emits the attention output, and commits the next KV cache in the
receipt journal.

Decision:

`GO_ATTENTION_KV_RISC0_SEMANTICS_RECEIPT_FOR_TINY_INTEGER_ARGMAX_TRANSITION`

Claim boundary:

`RISC0_RECEIPT_PROVES_TINY_INTEGER_ARGMAX_ATTENTION_KV_SEMANTICS_NOT_STWO_OR_SOFTMAX`

This is stronger than the earlier SNARK statement receipt for this lane because
the zkVM guest computes the transition semantics. It is still not a native Stwo
AIR/proof, not Softmax, not full transformer inference, and not recursion or
proof-carrying data.

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.tsv`
- Receipt artifact: `docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.bincode`
- RISC Zero fixture: `programs/risc0-attention-kv-transition-receipt/`
- Gate: `scripts/zkai_attention_kv_risc0_semantics_receipt_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_risc0_semantics_receipt_gate.py`

## Checked Outcomes

| Surface | Result |
| --- | ---: |
| Proof system | `RISC Zero` |
| `risc0-zkvm` version | `3.0.5` |
| Receipt size | `221842` bytes |
| Image ID | `cbc061838cd2a42993e6310f7e55d0b28c64b3693c985a2ccdb3626944d3d1eb` |
| Selected position | `0` |
| Attention output | `[2, 1]` |
| Masking policy | `none` |
| Next KV rows | `3` |
| Single local proof-generation time | `6909.913 ms` |
| Single local verification time | `14.938 ms` |
| Mutations checked | `22` |
| Mutations rejected | `22` |

The timing policy is `single_local_run_engineering_only`. These timings are not
public benchmark rows and should not be compared against other zkML systems.

The mutation suite rejects:

- prior-KV journal relabeling,
- input/query relabeling,
- attention-output relabeling,
- next-KV relabeling,
- score-trace relabeling,
- selected-position relabeling,
- source statement-contract relabeling,
- route/system/image-id/receipt commitment relabeling,
- strict-reverification removal,
- proof-size and timing metric smuggling,
- native-Stwo and Softmax claim smuggling,
- non-claim removal,
- validation-command removal,
- unknown top-level fields.

## Interpretation

This is the first attention/KV artifact in this repository where an external
proof system does more than wrap a source-backed statement contract. The guest
computes the tiny transition and the receipt journal is verified against the
same source fixture fields used by the state-binding contract.

That matters for verifiable intelligence because carried autoregressive state
is a real relabeling surface. A proof of an output is not enough if the prior
cache, score trace, selected token context, or next cache can be swapped after
the fact. This receipt proves one tiny step of that state transition under
explicit integer-argmax semantics.

The remaining blocker is also clearer: the repository still does not have a
native Stwo attention/KV AIR or proof. The next stronger result, tracked in
issue `#442`, is to preserve the same public fields and prove the transition in
the native trace backend, or to scale the zkVM guest from one tiny transition to
a sequence of carried KV updates.

## Non-Claims

- This is not a native Stwo attention/KV AIR or proof.
- This is not a Softmax attention proof.
- This is not full transformer inference.
- This is not recursive verification or PCD.
- This is not agent correctness.
- This is not a public zkML benchmark row.
- This is not a Starknet deployment result.

## Reproduce

```bash
PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" cargo test \
  --manifest-path programs/risc0-attention-kv-transition-receipt/Cargo.toml \
  -p host

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 \
  scripts/zkai_attention_kv_risc0_semantics_receipt_gate.py \
  --verify-existing \
  --write-json target/zkai-attention-kv-risc0-semantics-receipt-verify.json \
  --write-tsv target/zkai-attention-kv-risc0-semantics-receipt-verify.tsv

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_risc0_semantics_receipt_gate

python3 -m py_compile \
  scripts/zkai_attention_kv_risc0_semantics_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_semantics_receipt_gate.py
git diff --check
```

To regenerate the receipt from scratch, replace `--verify-existing` with
`--prove` and write to the checked evidence paths. Routine rechecks write to
`target/`: proof-generation time is marked as historical when it is not
remeasured, while verifier time is always taken from the current verification
run.
