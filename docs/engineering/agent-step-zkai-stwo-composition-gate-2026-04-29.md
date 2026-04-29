# Agent-step zkAI Stwo composition gate - 2026-04-29

## Question

Test whether the checked native Stwo `zkAIStatementReceiptV1` can be consumed as
the `model_receipt_commitment` inside an `AgentStepReceiptV1`.

This is a composition gate, not a new proof-system result. It checks that:

- the source Stwo statement-envelope benchmark is still a GO result,
- the agent receipt binds its model/input/output/config/runtime fields to the
  checked Stwo statement receipt,
- the resulting `AgentStepReceiptV1` bundle verifies with the existing Python
  reference verifier,
- the same composed bundle verifies with the Rust production
  `AgentStepReceiptV1` parser/verifier,
- relabeling at either layer rejects fail-closed.

## Artifacts

- Composition harness:
  `scripts/agent_step_zkai_stwo_composition.py`
- Focused tests:
  `scripts/tests/test_agent_step_zkai_stwo_composition.py`
- Checked JSON evidence:
  `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.json`
- Checked TSV evidence:
  `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.tsv`
- Composed receipt fixture:
  `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04/agent_step_zkai_stwo_composed_receipt.json`

The composed receipt binds:

| Agent field | Stwo statement field |
| --- | --- |
| `runtime_domain` | `verifier_domain` |
| `model_identity` | `model_id` |
| `model_commitment` | `model_artifact_commitment` |
| `model_config_commitment` | `config_commitment` |
| `model_receipt_commitment` | `statement_commitment` |
| `observation_commitment` | `input_commitment` |
| `action_commitment` | `output_commitment` |

## Result

Decision: **GO**.

| Surface | Mutations rejected |
| --- | ---: |
| Agent receipt stale-evidence mutations | 20 / 20 |
| zkAI statement receipt relabeling mutations | 14 / 14 |
| Cross-layer self-consistent bad subreceipt | 1 / 1 |
| Checked source-evidence tamper | 1 / 1 |
| Total | 36 / 36 |

The composed `AgentStepReceiptV1` baseline is accepted by the Rust production
parser through:

```bash
cargo run --quiet --example agent_step_receipt_verify -- \
  baseline=docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04/agent_step_zkai_stwo_composed_receipt.json
```

The recorded Rust adapter output is:

```json
{
  "schema": "agent-step-receipt-rust-verifier-adapter-v1",
  "results": [
    {
      "case_id": "baseline",
      "accepted": true,
      "error": ""
    }
  ]
}
```

## Interpretation

This closes the first composition step from statement-bound zkAI toward
verifiable-intelligence receipts:

```text
Stwo proof
        -> checked zkAI statement receipt
        -> AgentStepReceiptV1.model_receipt_commitment
        -> future Tablero / audit / settlement boundary
```

The important negative detail is that the agent receipt parser alone does not
inspect the nested Stwo receipt body. That is deliberate: the parser checks the
agent receipt's internal canonicalization, evidence, and trust rules. The
composition harness checks the nested `zkAIStatementReceiptV1` and the
cross-layer equality between agent fields and statement fields. A production
agent verifier must keep both layers, or must replace the harness with an
equivalent nested-subreceipt verifier callback.

## Reproduction

Regenerate the composition evidence:

```bash
python3 scripts/agent_step_zkai_stwo_composition.py \
  --rust-verify \
  --write-json docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.json \
  --write-tsv docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.tsv
```

Run the focused tests:

```bash
python3 -m unittest scripts.tests.test_agent_step_zkai_stwo_composition
```

Run the adjacent receipt and Stwo statement-envelope tests:

```bash
python3 -m unittest \
  scripts.tests.test_agent_step_receipt_relabeling_harness \
  scripts.tests.test_zkai_stwo_statement_envelope_benchmark
```

## Non-claims

- This is not end-to-end verifiable intelligence.
- This is not full transformer inference.
- This is not a new Stwo security audit.
- This is not backend independence.
- This does not prove model truthfulness, policy semantics, policy compliance,
  tool-output truth, or agent reasoning.

## Follow-up

The next useful implementation hardening is a nested-subreceipt verifier callback
for `AgentStepReceiptV1`: the production verifier would receive a
`model_receipt_commitment` and an adapter that verifies the corresponding
`zkAIStatementReceiptV1`, instead of relying on an external composition harness.
