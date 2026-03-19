<identity>
transformer-vm-rs is an implemented Rust workspace for a deterministic transformer-shaped virtual machine and an in-tree vanilla STARK prover over its execution trace. Milestone 1 and Milestone 2 are complete in the repository; Milestone 3 (STWO integration) is the next major target.
</identity>

<stack>
| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Language | Rust | 2021 | Cargo workspace is checked in |
| Package manager | Cargo | current manifest | `Cargo.toml` and `Cargo.lock` are present |
| CLI | clap | 4.5.38 | `tvm` binary in `src/bin/tvm.rs` |
| Terminal UI | ratatui, crossterm | 0.29.0 / 0.28.1 | Interactive execution viewer |
| Proof stack | In-repo vanilla STARK | local modules | `src/proof.rs` plus `src/vanillastark/` |
| Optional tensor runtime | Burn | 0.20.1 | Gated by `burn-model` |
| Optional export/runtime | ONNX + Tract | 0.2.3 / 0.23.0-dev.2 | Gated by `onnx-export` |
| Serialization | serde, serde_json | 1.0.219 / 1.0.140 | Proof and metadata IO |
| Test tooling | `cargo test`, criterion, proptest | current manifest | Default and feature-gated suites exist |
</stack>

<status>
- Milestone 1: complete.
- Milestone 2: complete for the current proof scope.
- Verified locally on 2026-03-18:
  - `cargo test`
  - `cargo test --features full`
- Current vanilla STARK scope:
  - supported: `NOP`, `LOADI`, `LOAD`, `STORE`, `PUSH`, `POP`, `ADD`, `ADDM`, `SUB`, `SUBM`, `MUL`, `MULM`, `CALL`, `RET`, `JMP`, `JZ`, `JNZ`, `HALT`
  - rejected: softmax and hard-softmax proof paths, bitwise instructions, compare instructions, non-halted public claims, public claims with `carry_flag = true`
- Current proof is transparent, not zero-knowledge: the public claim includes the program, attention mode, step count, and final state.
</status>

<structure>
Current repository:

```text
Cargo.toml
Cargo.lock
README.md
SPEC.md
IMPLEMENTATION_PLAN.md
CLAUDE.md
RFC-001-hull-kv-cache.md
RFC-002-2d-attention.md
RFC-003-state-encoding-compiler.md
RFC-004-005-runtime-hybrid.md
LICENSE
src/
  assembly.rs           # .tvm parser, directives, labels
  compiler.rs           # ProgramCompiler
  config.rs             # TransformerVmConfig, Attention2DMode
  engine.rs             # Shared execution traits/results
  error.rs              # VmError and Result
  geometry.rs           # Point2D and HullKvCache
  instruction.rs        # Program + ISA
  interpreter.rs        # Native semantic oracle
  memory.rs             # AddressedMemory and write histories
  model.rs              # TransformerVm and compiled transition logic
  runtime.rs            # Transformer execution loop
  state.rs              # MachineState and token encoding
  proof.rs              # Execution-proof plumbing and AIR wiring
  verification.rs       # Lockstep engine comparison
  tui.rs                # ratatui execution viewer
  vanillastark/         # Field, polynomial, Merkle, FRI, STARK internals
  burn_model.rs         # Optional Burn model
  burn_runtime.rs       # Optional Burn runtime
  onnx_export.rs        # Optional ONNX exporter
  onnx_runtime.rs       # Optional Tract runtime
  bin/tvm.rs            # CLI
tests/
examples/
benches/
programs/
scripts/
docs/specs/llm-computer-milestone-1-gaps/  # Archival milestone-1 gap-closure docs
```

Historical design docs (`RFC-*.md`, `docs/specs/**`) are still useful context, but the current code and `SPEC.md` are the source of truth for shipped behavior.
</structure>

<commands>
| Task | Command | Notes |
|------|---------|-------|
| Inventory files | `rg --files` | Fastest repo scan |
| Check repo state | `git status --short` | Separate your edits from unrelated files |
| Run default suite | `cargo test` | Core milestone-1 and milestone-2 validation |
| Run full engine suite | `cargo test --features full` | Burn + ONNX + Python validator + CLI workflow |
| Run a program | `cargo run --bin tvm -- programs/fibonacci.tvm` | Shortcut for `tvm run` |
| Trace execution | `cargo run --bin tvm -- run programs/counter.tvm --trace` | Emits trace and summary |
| Verify transformer vs native | `cargo run --bin tvm -- run programs/fibonacci.tvm --verify-native` | Lockstep comparison |
| Verify all engines | `cargo run --features full --bin tvm -- run programs/fibonacci.tvm --verify-all` | Transformer + native + Burn + ONNX |
| Create a proof | `cargo run --bin tvm -- prove-stark programs/fibonacci.tvm -o /tmp/fib.proof.json` | Uses current vanilla STARK path |
| Verify a proof | `cargo run --bin tvm -- verify-stark /tmp/fib.proof.json` | Re-checks a saved proof |
| Review doc drift | `git diff -- README.md SPEC.md IMPLEMENTATION_PLAN.md CLAUDE.md` | Use before finishing doc/context work |
</commands>

<conventions>
  <document_hierarchy>
  1. `SPEC.md` describes the current technical baseline.
  2. `README.md` is the public overview and workflow entrypoint.
  3. `IMPLEMENTATION_PLAN.md` tracks milestone status and next work, not the original bootstrap schedule.
  4. `RFC-*.md` and `docs/specs/**` are historical design context unless explicitly refreshed.
  5. `CLAUDE.md` is agent-facing context and should stay aligned with the observed repository.
  </document_hierarchy>

  <code_and_status_rules>
  - Describe implemented behavior from code and tests, not from older plans.
  - When discussing proof support, call out the exact supported and rejected surface instead of saying "partial" generically.
  - Do not describe the current vanilla STARK path as zero-knowledge; it is a transparent proof with a public claim.
  - Optional Burn and ONNX workflows are real, but feature-gated.
  - Memory size and encoded addresses are effectively capped by `u8::MAX`.
  </code_and_status_rules>

  <doc_sync>
  When project status changes:
  1. Update `SPEC.md` first.
  2. Propagate user-facing wording to `README.md`.
  3. Update `IMPLEMENTATION_PLAN.md` with milestone state and next steps.
  4. Update `CLAUDE.md` if the repo surface, commands, or milestone boundaries changed.
  5. Run targeted searches for stale terms such as `docs-only`, `WASM`, `planned`, `zero knowledge`, or outdated milestone labels.
  </doc_sync>
</conventions>

<workflows>
  <doc_or_context_change>
  1. Read the relevant source file plus the corresponding code modules or tests.
  2. Prefer current API and test behavior over older RFC language.
  3. Keep implemented-vs-next boundaries explicit.
  4. Review `git diff` for top-level docs before finishing.
  </doc_or_context_change>

  <proof_change>
  1. Read `src/proof.rs` and `src/vanillastark/**`.
  2. Update support and limitation language in `SPEC.md` and `README.md`.
  3. Re-run at least `cargo test` and, when Burn or ONNX paths are affected, `cargo test --features full`.
  </proof_change>

  <engine_change>
  1. Read `src/runtime.rs`, `src/interpreter.rs`, and `src/verification.rs`.
  2. If CLI behavior changes, update `README.md` quick-start commands.
  3. If feature-gated runtimes change, update both `README.md` and this file's command/status notes.
  </engine_change>
</workflows>

<boundaries>
  <forbidden>
  - `.git/**`
  - Secret material (`.env*`, keys, tokens, certificates)
  - Destructive cleanup of user-created files without an explicit request
  </forbidden>

  <careful>
  - `CLAUDE.md`, top-level docs, and proof/status wording: keep them synchronized; do not make one-off edits.
  - `fib.proof.json` is currently untracked local output; treat it as workspace data, not as a tracked source file.
  </careful>
</boundaries>

<troubleshooting>
  <known_issues>
  | Symptom | Likely cause | Fix |
  |---------|--------------|-----|
  | `prove-stark` rejects a program | Unsupported instruction, attention mode, or claim shape | Check `src/proof.rs::validate_proof_inputs` and the carry/halted restrictions |
  | Burn or ONNX commands are unavailable | Missing feature flag | Re-run with `--features burn-model`, `--features onnx-export`, or `--features full` |
  | Docs mention WASM compilation as current behavior | Stale pre-implementation text | Prefer `SPEC.md` and the source tree over old planning language |
  | An engine mismatch appears during verification | Trace divergence across runtimes | Inspect `ExecutionTraceEntry` output and compare instruction/state pairs |
  </known_issues>
</troubleshooting>

<memory>
  <project_decisions>
  - 2026-03-16: Started as a docs-first architecture exercise before code generation.
  - 2026-03-17: Milestone 1 landed as a working Rust implementation with differential verification and optional Burn/ONNX portability.
  - 2026-03-18: Milestone 2 completed with an in-tree vanilla STARK prover/verifier over the average-hard deterministic VM subset.
  - 2026-03-18: The proof path remains transparent for now; zero-knowledge hiding and STWO integration are future work, not current behavior.
  </project_decisions>

  <lessons_learned>
  - Top-level status docs drift quickly once code exists; re-verify against tests before updating them.
  - Historical RFC language can remain useful, but current repo behavior must come from code plus test coverage.
  - The most important proof caveat today is scope, not existence: milestone 2 works, but only for the validated deterministic subset.
  </lessons_learned>
</memory>
