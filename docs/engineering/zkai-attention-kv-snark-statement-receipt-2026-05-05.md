# zkAI Attention/KV SNARK Statement Receipt - 2026-05-05

## Question

Can the source-backed attention/KV transition contract be wrapped by a real
proof-backed statement receipt without changing its public state-binding fields?

## Result

GO, with a narrow claim boundary.

The checked source-backed attention/KV transition receipt now has a real
verifier-facing `snarkjs/Groth16/BN128` statement receipt. The SNARK public
signals bind the source contract's model/config, prior KV state, input/query
state, attention output, next KV state, public-instance commitment, score-trace
commitment, source proof status, source verifier domain, source model id, and
source statement kind.

Decision:

`GO_ATTENTION_KV_SNARK_STATEMENT_RECEIPT_FOR_SOURCE_BACKED_TRANSITION_CONTRACT`

Claim boundary:

`SNARK_STATEMENT_RECEIPT_BINDS_ATTENTION_KV_SOURCE_CONTRACT_NOT_ATTENTION_ARITHMETIC_PROOF`

This is the first proof-backed attention/KV statement-binding adapter in the
repo. It is not a proof that Groth16 recomputes attention arithmetic. The
source transition remains the Python reference contract; the SNARK receipt binds
that contract into a proof object and prevents post-proof relabeling of the
claim.

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.tsv`
- Verifier-facing artifacts: `docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05/`
- Source receipt evidence: `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json`
- Generator: `scripts/zkai_attention_kv_snark_statement_receipt_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_snark_statement_receipt_gate.py`

## Checked Outcomes

| Surface | Result |
| --- | ---: |
| Proof system | `snarkjs/Groth16/BN128` |
| `snarkjs` version | `0.7.6` |
| `circom` version | `2.0.9` |
| Proof size | `802` bytes |
| Verification key size | `6040` bytes |
| Public signals | `18` |
| Public signal field entries | `17` |
| Mutations checked | `36` |
| Mutations rejected | `36` |
| Timing policy | `not_measured_in_this_gate` |

The checked mutation suite rejects source-statement, model/config, prior-KV,
input, output, next-KV, public-instance, score-trace, proof-status, verifier
domain, model id, statement-kind, public-signal, field-entry, artifact-hash,
setup, metric-smuggling, non-claim, validation-command, and unknown-field
mutations.

The raw proof verifier is also checked: the original proof verifies, while
public-signal drift fails.

## Interpretation

This converts the attention/KV state-binding result from "source-backed contract
only" into "source-backed contract plus proof-backed statement receipt." That is
valuable for the verifiable-AI agenda because carried state is where
autoregressive and agentic claims can be relabeled most easily: a valid output
claim is not enough if the prior cache or next cache can be swapped after the
proof.

The result should be described as statement-binding evidence, not as model-scale
proving evidence.

## Non-Claims

- This is not an attention arithmetic proof.
- This is not a Softmax proof.
- This is not a Stwo-native proof.
- This is not recursive aggregation.
- This is not proof-carrying data.
- This is not verification of a native Stwo attention proof inside Groth16.
- This is not a production trusted setup.
- This is not a prover-performance benchmark.
- This is not a zkVM receipt.
- This is not onchain deployment evidence.
- This is not full transformer inference.
- This is not agent correctness.

## Reproduce

```bash
npm ci --prefix scripts

python3 scripts/zkai_attention_kv_snark_statement_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_snark_statement_receipt_gate
python3 -m py_compile \
  scripts/zkai_attention_kv_snark_statement_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_snark_statement_receipt_gate.py
```

## Next GO Criterion

The next stronger result is a native attention/KV proof route: preserve the same
public state-binding fields, but move from a SNARK statement receipt over a
source contract to a proof that actually checks the attention transition
arithmetic under the chosen semantics.
