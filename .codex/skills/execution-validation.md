---
name: execution-validation
description: Activate when implementing or reviewing MachineState encoding, instruction compilation, runtime stepping, determinism checks, or benchmark claims in llm-provable-computer. Use this whenever a change touches RFC-003 or RFC-004 behavior, or when sourced performance claims need to become measured results.
prerequisites: rg, git, RFC-003, RFC-004-005, willingness to build reference oracles
---

# Execution Validation

<purpose>
Validate that encoded state, compiled instructions, and runtime stepping agree with the intended VM semantics before any performance or demo work is trusted.
</purpose>

<context>
- `RFC-003-state-encoding-compiler.md` defines `MachineState`, token encoding, the simplified ISA, and compiler targets.
- `RFC-004-005-runtime-hybrid.md` defines the execution loop and result surface.
- `IMPLEMENTATION_PLAN.md` expects correctness on small programs before long-run throughput work.
- `README.md` and `PAPER_DIGEST.md` cite source throughput and accuracy claims; those are not locally reproduced yet.
</context>

<procedure>
1. Read `RFC-003-state-encoding-compiler.md`, `RFC-004-005-runtime-hybrid.md`, and the testing sections in `SPEC.md`.
2. Start with state round-trip tests:
   - encode -> decode preserves every field
   - flag bits and signed accumulator handling are explicit
3. Build a tiny native reference interpreter for the simplified ISA before validating compiled execution.
4. Add instruction-level tests one opcode at a time: `NOP`, `LOAD`, `STORE`, `ADD`, `SUB`, `JMP`, `JZ`, `HALT`.
5. Compare compiled/runtime behavior against the reference interpreter on short programs before running long traces.
6. Measure throughput only after correctness is stable; report measured results separately from sourced claims.
7. When benchmarks appear, record the environment and command used so future agents can reproduce them.
</procedure>

<patterns>
<do>
  - Treat determinism as a testable property, not a narrative claim.
  - Keep a native reference path for semantic comparisons.
  - Use short, focused programs as fixtures before attempting long execution traces.
</do>
<dont>
  - Do not trust compiler output without a reference interpreter -> compare every opcode path first.
  - Do not report sourced `33K+ tokens/sec` numbers as local performance -> benchmark the actual workspace first.
  - Do not jump to hybrid or WASM features before the simplified ISA passes cleanly.
</dont>
</patterns>

<examples>
Example: first semantic fixture
```text
Program: ADD 5; ADD 3; HALT
Expected final state: ACC = 8, halted = true
```

Example: validation ladder
```text
state round-trip -> single-opcode tests -> short programs -> long traces -> benchmarks
```
</examples>

<troubleshooting>
| Symptom | Cause | Fix |
|---------|-------|-----|
| Encode/decode loses sign or flag information | Bit layout is inconsistent or underspecified | Lock the layout with round-trip tests before compiler work |
| Runtime diverges from the reference interpreter after a few steps | Instruction compiler and runtime semantics are out of sync | Compare state after every step and isolate the first failing opcode |
| Throughput numbers vary wildly between runs | Benchmark includes setup, logging, or debug assertions | Separate warmup/setup from the measured loop and record benchmark conditions |
</troubleshooting>

<references>
- `RFC-003-state-encoding-compiler.md`: state encoding, ISA, compiler surface
- `RFC-004-005-runtime-hybrid.md`: runtime loop and execution result
- `SPEC.md`: testing strategy and architecture integration
- `IMPLEMENTATION_PLAN.md`: milestone order for runtime validation
- `README.md`: public claims that must stay aligned with measured progress
- `PAPER_DIGEST.md`: sourced claims and caveats
</references>
