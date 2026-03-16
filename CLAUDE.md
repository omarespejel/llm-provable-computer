<identity>
transformer-vm-rs is a documentation-first Rust architecture repo for a planned transformer VM that executes programs deterministically via 2D attention, `HullKvCache`, and compiled feed-forward layers.
</identity>

<stack>
| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Repo state | Markdown design docs | n/a | Current tracked files are docs only; no Cargo workspace is checked in |
| Planned language | Rust | unpinned [verify] | `Cargo.toml`, `Cargo.lock`, and `rust-toolchain*` are absent |
| Planned ML runtime | Burn, Tract | unpinned [verify] | Mentioned in docs only; not installed or configured |
| Planned package manager | Cargo | unconfigured [verify] | Do not assume `cargo build` or `cargo test` work |
| Planned testing | `cargo test`, `proptest`, `criterion` | unpinned [verify] | Versions only appear in `RESOURCES.md` |
| VCS | git | `main` | Single commit `22f8c5c` dated 2026-03-16 |
</stack>

<structure>
Current repository:

```text
README.md                      # Public summary and external positioning [gated]
SPEC.md                        # Primary architecture baseline [gated]
IMPLEMENTATION_PLAN.md         # Phase ordering and milestones [gated]
RFC-001-hull-kv-cache.md       # HullKvCache design [gated]
RFC-002-2d-attention.md        # 2D attention design [gated]
RFC-003-state-encoding-compiler.md
                               # State encoding and compiler design [gated]
RFC-004-005-runtime-hybrid.md  # Runtime and hybrid architecture design [gated]
PAPER_DIGEST.md                # Source digest and caveats [gated]
RESOURCES.md                   # Candidate deps and citations [gated]
CLAUDE.md                      # Agent context [read-only unless explicitly requested]
.codex/skills/                 # Canonical skill files [read-only unless explicitly requested]
.claude/skills -> ../.codex/skills
.agents/skills -> ../.codex/skills
.git/                          # VCS internals [forbidden]
```

Planned but absent; explicit approval required before creating:

```text
Cargo.toml
LICENSE
src/
tests/
examples/
benches/
Cargo.lock
rust-toolchain.toml
```
</structure>

<commands>
| Task | Command | Notes |
|------|---------|-------|
| Inventory files | `rg --files` | Fastest way to confirm whether code has been added since last scan |
| Read architecture baseline | `sed -n '1,220p' SPEC.md` | Start here before architecture edits |
| Search core concepts | `rg -n "HullKvCache|Attention2D|MachineState|ExecutionRuntime" *.md` | Use term-specific searches before and after edits |
| Check repo state | `git status --short` | Separate your work from unrelated changes |
| Review doc drift | `git diff -- README.md SPEC.md RFC-*.md IMPLEMENTATION_PLAN.md RESOURCES.md PAPER_DIGEST.md` | Run before finishing doc changes |
| Check skill wiring | `ls -l .codex/skills .claude/skills .agents/skills` | Confirms symlinks still resolve |
| Guarded Rust tests [verify] | `if [ -f Cargo.toml ]; then cargo test; else echo "No Cargo.toml"; fi` | Do not report Rust tests as passing until a workspace exists |
</commands>

<conventions>
  <document_hierarchy>
  1. `SPEC.md` is the architecture baseline and planned module tree.
  2. `RFC-*.md` adds component detail; if an RFC conflicts with `SPEC.md`, resolve the conflict intentionally instead of silently picking one.
  3. `README.md` is the public summary; keep it shorter and less detailed than the spec.
  4. `IMPLEMENTATION_PLAN.md` is sequencing guidance, not proof that a feature exists.
  5. `RESOURCES.md` contains candidate dependencies and sources; versions there are planning inputs, not installed state.
  </document_hierarchy>

  <code_style>
  Planned Rust modules follow the `SPEC.md` section 5 naming pattern: `snake_case.rs` files and `CamelCase` types such as `TransformerVmConfig`, `HullKvCache`, `Attention2D`, `MachineState`, and `ExecutionRuntime`.
  Keep pseudo-code close to Rust syntax and internally consistent with existing names.
  Error-handling conventions are not defined in the repo yet; do not invent a repo-wide error architecture without approval.
  </code_style>

  <patterns>
    <do>
    - Start every task by classifying it as doc-only work or approved workspace bootstrap.
    - Read `SPEC.md` and the relevant RFC before changing terminology, interfaces, dependencies, or performance claims.
    - Update every affected doc in one change when a shared concept is renamed or re-scoped.
    - Label anything not present in the repo as `planned`, `Phase 1`, `Phase 2`, or `[verify]`.
    - Treat `SPEC.md` section 5 as the default scaffold if code creation is approved.
    </do>
    <dont>
    - Do not claim code, benches, tests, crates, or CI exist unless the files are present.
    - Do not change only `README.md` for architectural edits; sync `SPEC.md` and the matching RFC.
    - Do not present sourced throughput or dependency versions as locally reproduced facts.
    - Do not create the Rust workspace, module tree, or benches without explicit approval.
    </dont>
  </patterns>

  <commit_conventions>
  Observed history uses a Conventional-Commit-like format: `chore: init spec`.
  No commit hooks or policy files exist.
  If asked to commit, use `type: summary` or `type(scope): summary`, all lowercase.
  </commit_conventions>
</conventions>

<workflows>
  <doc_change>
  1. Determine whether the request is wording cleanup, architecture semantics, dependency change, or status reporting.
  2. Read `SPEC.md` and every RFC that names the touched concept.
  3. Update the authoritative file first, then propagate the change to dependent docs.
  4. Run `rg -n "<term>" *.md` for renamed modules, types, or dependencies.
  5. Review `git diff -- README.md SPEC.md RFC-*.md IMPLEMENTATION_PLAN.md RESOURCES.md PAPER_DIGEST.md`.
  6. Make the implemented-vs-planned boundary explicit before finishing.
  </doc_change>

  <architecture_change>
  1. Treat module layout changes, dependency version changes, ISA scope changes, and benchmark/performance claim changes as gated.
  2. State the affected files and semantic impact before editing.
  3. After approval, update `SPEC.md`, the relevant RFCs, `README.md`, and `RESOURCES.md` in the same change.
  4. If implementation order changes, update `IMPLEMENTATION_PLAN.md` too.
  </architecture_change>

  <workspace_bootstrap>
  1. Obtain explicit approval before creating `Cargo.toml`, `src/`, `tests/`, `examples/`, `benches/`, `Cargo.lock`, or `rust-toolchain*`.
  2. Read `SPEC.md` section 5 plus `RFC-001-hull-kv-cache.md` through `RFC-004-005-runtime-hybrid.md`.
  3. Scaffold the smallest viable workspace that matches the planned module names; start with `convex_hull`, `hull_kv_cache`, and tests before model orchestration.
  4. Add brute-force correctness oracles before performance work.
  5. Once code exists, update docs so implemented modules are clearly distinguished from planned modules.
  </workspace_bootstrap>

  <skill_maintenance>
  1. Add or update files under `.codex/skills/`.
  2. Register every skill in `.codex/skills/_index.md`.
  3. Verify `.claude/skills` and `.agents/skills` still point to `.codex/skills`.
  4. Do not change agent context files unless the task explicitly requests context work.
  </skill_maintenance>
</workflows>

<boundaries>
  <forbidden>
  DO NOT modify under any circumstances unless the user explicitly requests the specific action:
  - `.git/**`
  - `.env`, `.env.*`, `*.pem`, `*.key`, or any future secret material
  - destructive deletion or rename of top-level design docs
  - `CLAUDE.md`, `.codex/skills/**`, `.claude/skills`, `.agents/skills` outside agent-context work
  </forbidden>

  <gated>
  Modify only with explicit human approval:
  - `README.md`
  - `SPEC.md`
  - `IMPLEMENTATION_PLAN.md`
  - `RFC-*.md`
  - `PAPER_DIGEST.md`
  - `RESOURCES.md`
  - any creation or modification of `Cargo.toml`, `Cargo.lock`, `rust-toolchain*`, `src/**`, `tests/**`, `examples/**`, `benches/**`, `LICENSE`
  </gated>

  <safety_checks>
  Before any destructive or architecture-changing action:
  1. State the exact files to change.
  2. State whether the change is semantic, structural, or destructive.
  3. State the risk of drift or data loss.
  4. Wait for confirmation if files will be deleted, renamed, or if a new Rust workspace will be created.
  </safety_checks>
</boundaries>

<troubleshooting>
  <known_issues>
  | Symptom | Cause | Fix |
  |---------|-------|-----|
  | `cargo test` reports missing `Cargo.toml` | The repository has no Rust workspace yet | Stay in docs mode or get approval to bootstrap the workspace |
  | Dependency versions look authoritative but cannot be verified from config files | Versions only live in `RESOURCES.md` | Treat them as planned and keep `[verify]` markers until configs exist |
  | Docs disagree on module names or feature status | A change was applied in one file only | Update `SPEC.md` first, then the relevant RFC, then `README.md` |
  | Performance claims appear measured but no benches exist | `README.md` and `PAPER_DIGEST.md` summarize source claims | Label them as sourced, not locally reproduced |
  </known_issues>

  <recovery_patterns>
  When stuck, follow this cascade:
  1. Run `rg --files` to confirm whether code has been added since the last scan.
  2. Read `SPEC.md` and the relevant RFC before touching terminology or module structure.
  3. Use `git status --short` and `git diff` to isolate your edits from unrelated changes.
  4. If the task assumes code that is not present, stay in docs mode or request approval to bootstrap the workspace.
  5. If uncertainty remains, state the missing file or missing decision explicitly instead of guessing.
  </recovery_patterns>
</troubleshooting>

<environment>
- Harness: Codex via terminal
- File system scope: full repository access
- Network access: available
- Tool access: git, shell, web
- Human interaction model: synchronous chat with explicit approval for gated or destructive work
</environment>

<skills>
Modular skills live in `.codex/skills/` and are mirrored through `.claude/skills` and `.agents/skills`.

Available skills:
- `spec-rfc-sync.md`: keep `SPEC.md`, RFCs, README, and resource docs in sync
- `rust-workspace-bootstrap.md`: create the first Cargo workspace from the approved spec
- `hull-kv-cache.md`: implement and verify the convex-hull KV cache and 2D attention lookup path
- `execution-validation.md`: validate state encoding, compiler/runtime behavior, and benchmark claims

Load only the skill file relevant to the current task.
</skills>

<memory>
  <project_decisions>
  - 2026-03-16: Initialize the repository as docs-only architecture and RFCs before code generation - settle design first - rejected ad hoc coding without a written spec
  - 2026-03-16: Phase 1 targets a simplified ISA (`NOP`, `LOAD`, `STORE`, `ADD`, `SUB`, `JMP`, `JZ`, `HALT`) before full WASM - reduce scope and create a correctness baseline - rejected starting with full WASM compilation
  - 2026-03-16: Core execution primitive is 2D attention plus `HullKvCache` for `O(log n)` argmax lookups - make long execution traces tractable - rejected standard `O(n)` KV scans
  - 2026-03-16: Default planned attention mode is average-hard; differentiable variants are Phase 2 - preserve deterministic execution first - rejected training-first integration
  </project_decisions>

  <lessons_learned>
  - Distinguish observed repo state from planned implementation state in every edit.
  - `IMPLEMENTATION_PLAN.md` is scheduling guidance; `SPEC.md` and RFCs define the intended system.
  - Dependency versions in `RESOURCES.md` are planning inputs, not installed facts.
  </lessons_learned>
</memory>
