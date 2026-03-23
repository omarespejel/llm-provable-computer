<identity>
llm-provable-computer is an implemented Rust workspace for a deterministic transformer-shaped virtual machine and an in-tree vanilla STARK prover over its execution trace. Milestone 1 and Milestone 2 are complete in the repository; Milestone 3 (STWO integration) is the next major target.
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
- Verified locally on 2026-03-19:
  - `cargo fmt --all --check`
  - `cargo clippy --all-targets --all-features -- -D warnings`
  - `cargo test --all-features`
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
CLAUDE.md
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
```

</structure>

<commands>
| Task | Command | Notes |
|------|---------|-------|
| Inventory files | `rg --files` | Fastest repo scan |
| Check repo state | `git status --short` | Separate your edits from unrelated files |
| Run default suite | `cargo test` | Core milestone-1 and milestone-2 validation |
| Check formatting | `cargo fmt --all --check` | Matches CI-ready rustfmt output |
| Run strict lint pass | `cargo clippy --all-targets --all-features -- -D warnings` | Keep the full tree warning-free |
| Run full engine suite | `cargo test --all-features` | Burn + ONNX + Python validator + CLI workflow |
| Run a program | `cargo run --bin tvm -- programs/fibonacci.tvm` | Shortcut for `tvm run` |
| Trace execution | `cargo run --bin tvm -- run programs/counter.tvm --trace` | Emits trace and summary |
| Verify transformer vs native | `cargo run --bin tvm -- run programs/fibonacci.tvm --verify-native` | Lockstep comparison |
| Verify all engines | `cargo run --features full --bin tvm -- run programs/fibonacci.tvm --verify-all` | Transformer + native + Burn + ONNX |
| Create a proof | `cargo run --bin tvm -- prove-stark programs/fibonacci.tvm -o /tmp/fib.proof.json` | Uses current vanilla STARK path |
| Verify a proof | `cargo run --bin tvm -- verify-stark /tmp/fib.proof.json` | Re-checks a saved proof |
| Review doc drift | `git diff -- README.md CLAUDE.md docs/` | Use before finishing doc/context work |
</commands>

<workflows>
  <doc_or_context_change>
  1. Read the relevant source file plus the corresponding code modules or tests.
  2. Prefer current API and test behavior over older RFC language.
  3. Keep implemented-vs-next boundaries explicit.
  4. Review `git diff` for top-level docs before finishing.
  </doc_or_context_change>

  <proof_change>
  1. Read `src/proof.rs` and `src/vanillastark/**`.
  2. Update support and limitation language in `README.md`, `CLAUDE.md`, and matching files under `docs/`.
  3. Re-run at least `cargo test` and, when Burn or ONNX paths are affected, `cargo test --all-features`.
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
  </careful>
</boundaries>

<troubleshooting>
  <known_issues>
  | Symptom | Likely cause | Fix |
  |---------|--------------|-----|
  | `prove-stark` rejects a program | Unsupported instruction, attention mode, or claim shape | Check `src/proof.rs::validate_proof_inputs` and the carry/halted restrictions |
  | Burn or ONNX commands are unavailable | Missing feature flag | Re-run with `--features burn-model`, `--features onnx-export`, or `--features full` |
  | Docs mention WASM compilation as current behavior | Stale pre-implementation text | Prefer `README.md`, `CLAUDE.md`, and the source tree over old planning language |
  | An engine mismatch appears during verification | Trace divergence across runtimes | Inspect `ExecutionTraceEntry` output and compare instruction/state pairs |
  </known_issues>
</troubleshooting>
