# transformer-vm-rs — Status and Next Plan

This file now tracks current milestone status and the next tranche of work. The original day-by-day bootstrap plan has been superseded by the implemented repository.

---

## Current Status

As of **March 18, 2026**:

- **Milestone 1 is complete.**
  - Deterministic transformer-shaped execution is implemented.
  - The VM supports arithmetic, bitwise, compare, branching, stack, and subroutine instructions.
  - Native, transformer, Burn, and ONNX execution paths are available.
- **Milestone 2 is complete for the current proof scope.**
  - The repository ships an in-tree vanilla STARK prover/verifier.
  - Proof generation and verification are exposed through the CLI.
  - The validated proof subset covers average-hard deterministic execution for arithmetic, memory, control-flow, stack, and subroutine instructions.
- **Validation status checked locally on 2026-03-18**
  - `cargo test` passes
  - `cargo test --features full` passes

---

## Completed Milestones

### Milestone 1: Deterministic Transformer VM

Delivered:

- `.tvm` parser with labels, `.memory`, and `.init`
- `MachineState` encoding and decoding at `d_model = 36`
- 2D attention and `HullKvCache`
- Compiled transformer runtime
- Native semantic oracle
- Differential verification between runtimes
- CLI runner and TUI
- Optional Burn and ONNX execution flows
- Examples, shipped programs, property tests, stress tests, and benchmarks

### Milestone 2: Vanilla STARK Proof

Delivered:

- In-repo finite field, polynomial, Merkle, FRI, and STARK components
- AIR construction over VM execution traces
- JSON proof serialization helpers
- CLI proof generation and verification commands
- Round-trip proof coverage in unit, smoke, and CLI tests

Current proof boundary:

- Supported:
  - `average-hard` attention
  - `NOP`, `LOADI`, `LOAD`, `STORE`
  - `PUSH`, `POP`
  - `ADD`, `ADDM`, `SUB`, `SUBM`, `MUL`, `MULM`
  - `CALL`, `RET`, `JMP`, `JZ`, `JNZ`, `HALT`
- Not yet supported:
  - `softmax` and `hard-softmax` proof paths
  - bitwise instructions
  - compare instructions
  - public claims with `carry_flag = true`
  - zero-knowledge hiding of the claim

---

## Next Milestone

### Milestone 3: Production STARK Prover (STWO)

Primary goal: replace the educational vanilla proving backend with a production-grade STWO backend while preserving the current execution semantics and proof surface.

Planned work:

- [ ] Encode the current VM AIR in STWO trace/constraint form
- [ ] Preserve the current supported instruction subset before widening the AIR
- [ ] Add a proof-backend abstraction so CLI and library callers can choose vanilla vs STWO
- [ ] Reuse the existing public claim shape or define a clean migration path
- [ ] Benchmark STWO proving and verification against the vanilla implementation
- [ ] Add regression tests that compare STWO and vanilla verification on shared fixtures

Milestone 3 exit criteria:

- STWO proofs verify for the same shipped average-hard subset that milestone 2 proves today
- The CLI can generate and verify STWO-backed proofs
- The repository has comparative benchmark data for vanilla vs STWO

---

## Follow-On Work

- [ ] Extend the AIR to bitwise instructions
- [ ] Extend the AIR to compare instructions and carry-flag claims
- [ ] Decide whether non-average-hard attention should ever be provable or remain execution-only
- [ ] Improve benchmark reporting and doc comments
- [ ] Decide release and publishing steps
- [ ] Revisit hybrid or trained layers after the production proving backend stabilizes
- [ ] Revisit a WASM frontend only after the current VM and proof surfaces are stable
