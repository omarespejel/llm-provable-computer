# Design Notes

These notes track engineering specifications for the experimental `stwo` line, carried-state artifact ladder, and related verifier/hardening work.

They are implementation documents, not publication-facing claims.

Repository-wide hardening and test policy lives in
[`docs/engineering/hardening-policy.md`](../hardening-policy.md) and
[`docs/engineering/hardening-strategy.md`](../hardening-strategy.md).

The detailed phase chronology moved out of the public README lives in
[`engineering-timeline.md`](engineering-timeline.md).

Verifiable-intelligence receipt design begins with
[`agent-step-receipt-spec.md`](agent-step-receipt-spec.md). That note scopes
Tablero as a typed receipt boundary for agent-step evidence, not as a claim that
Tablero itself proves agents, reasoning, tool truth, or policy semantics.
- [zkAI statement receipt spec](zkai-statement-receipt-spec.md)
- [statement-bound transformer primitive spec](statement-bound-transformer-primitive-spec.md)
- [Stwo statement-bound primitive gate](../zkai-stwo-statement-bound-primitive-gate-2026-04-29.md)
- [Stwo statement-bound transformer-block result gate](../zkai-stwo-statement-bound-transformer-block-result-gate-2026-05-01.md)
- [Matched RMSNorm-SwiGLU block feasibility gate](../zkai-matched-rmsnorm-swiglu-block-feasibility-gate-2026-05-01.md)
- [d64 RMSNorm-SwiGLU implementation-surface probe](../zkai-d64-rmsnorm-swiglu-surface-probe-2026-05-01.md)
- [d64 RMSNorm-SwiGLU statement fixture](../zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05-01.md)
- [d64 external-adapter surface probe](../zkai-d64-external-adapter-surface-probe-2026-05-01.md)
- [Agent-step zkAI Stwo composition gate](../agent-step-zkai-stwo-composition-gate-2026-04-29.md)
- [Agent-step model subreceipt callback gate](../agent-step-model-subreceipt-callback-gate-2026-04-29.md)
