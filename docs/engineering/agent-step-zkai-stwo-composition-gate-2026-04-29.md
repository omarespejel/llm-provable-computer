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
- the same composed bundle and nested statement receipt verify through the Rust
  production `AgentStepReceiptV1` zkAI/Stwo callback verifier on the baseline,
- relabeling at either layer rejects fail-closed.

The mutation totals below are produced by the Python composition matrix. The
recorded Rust callback run is a baseline acceptance check; focused tests also
exercise a tampered nested statement receipt through that Rust callback path and
require rejection, but the JSON mutation-count table is still the Python matrix.

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
- Nested zkAI statement receipt fixture consumed by the Rust callback verifier:
  `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04/zkai_stwo_statement_receipt.json`

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

These rejection counts come from the Python composition matrix. The checked JSON
evidence records Rust callback baseline acceptance separately under
`rust_agent_receipt_verifier`.

The composed `AgentStepReceiptV1` baseline and the nested Stwo
`zkAIStatementReceiptV1` fixture are accepted by the Rust production callback
path through:

```bash
cargo run --quiet --example agent_step_zkai_stwo_receipt_verify -- \
  docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04/agent_step_zkai_stwo_composed_receipt.json \
  docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04/zkai_stwo_statement_receipt.json \
  docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.json
```

The recorded Rust adapter output is:

```json
{
  "schema": "agent-step-zkai-stwo-rust-callback-verifier-v1",
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

The important negative detail is that the parser-only agent receipt API still
does not inspect the nested Stwo receipt body. That is deliberate: the parser
checks the agent receipt's internal canonicalization, evidence, and trust rules.
The production Rust callback path now checks the nested `zkAIStatementReceiptV1`,
the checked Stwo evidence handle, and the cross-layer equality between agent
fields and statement fields.

The checked source-evidence handle is bound to the exact nested receipt, not just
to a generic GO result: the Rust callback verifier validates the Stwo evidence
schema, suite, system, version, case corpus, evidence-manifest commitment,
baseline statement commitment, baseline statement payload hash, baseline proof
commitment, and baseline public-instance commitment before accepting the
composed agent receipt.

Focused tests additionally mutate the nested statement receipt and require the
Rust callback verifier to reject it. Those callback-path tamper checks are test
coverage, not the source of the `36 / 36` matrix above.

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

The immediate nested-subreceipt verifier callback hardening is implemented in
`docs/engineering/agent-step-model-subreceipt-callback-gate-2026-04-29.md` and
now exercised by this gate. The next useful research step is a larger
Stwo-native statement-bound transformer block, not another callback seam.
