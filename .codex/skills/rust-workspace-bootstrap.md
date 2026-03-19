---
name: rust-workspace-bootstrap
description: Activate when a task requires creating Cargo.toml, src/, tests/, examples/, or benches/ in llm-provable-computer, or translating the written spec into the first Rust workspace. Use this only after explicit approval, because the repository currently contains no Cargo project and bootstrap is a structural change.
prerequisites: explicit approval, Rust toolchain, rg, git
---

# Rust Workspace Bootstrap

<purpose>
Create the first Rust workspace from the written architecture without inventing extra modules or pretending code already exists.
</purpose>

<context>
- Current repo state: docs only.
- Planned module tree is in `SPEC.md` section 5.
- Candidate dependencies are listed in `RESOURCES.md`; they are not installed state.
- Phase 1 starts with convex hull, `HullKvCache`, 2D attention, state encoding, and runtime pieces from `IMPLEMENTATION_PLAN.md`.
</context>

<procedure>
1. Confirm approval to create `Cargo.toml`, `src/`, `tests/`, `examples/`, `benches/`, `Cargo.lock`, or `rust-toolchain*`.
2. Read `SPEC.md`, `RFC-001-hull-kv-cache.md`, `RFC-002-2d-attention.md`, and `RFC-003-state-encoding-compiler.md`.
3. Scaffold only the Phase 1 surface needed for the current task:
   - `Cargo.toml`
   - `src/lib.rs`
   - low-level modules such as `src/convex_hull.rs` and `src/hull_kv_cache.rs`
   - matching tests under `tests/`
4. Keep interfaces aligned with the documented names unless the approved task includes a rename.
5. Add brute-force correctness oracles before performance work.
6. Treat dependency versions copied from `RESOURCES.md` as `[verify]` until the workspace is tested.
7. After the skeleton compiles, update `README.md` and `SPEC.md` to separate implemented modules from planned ones.
</procedure>

<patterns>
<do>
  - Start with a minimal library crate and add modules incrementally.
  - Implement the lowest-level data structures before model orchestration.
  - Keep examples and benches out of the first bootstrap unless the task explicitly asks for them.
</do>
<dont>
  - Do not create the full planned tree on day one -> scaffold only what the approved task needs.
  - Do not pin extra crates beyond the docs without approval -> start from `RESOURCES.md` and verify.
  - Do not mix runtime UI (`ratatui`) into the first correctness milestone -> land core algorithms first.
</dont>
</patterns>

<examples>
Example: first approved scaffold
```text
Cargo.toml
src/lib.rs
src/convex_hull.rs
src/hull_kv_cache.rs
tests/hull_kv_cache_tests.rs
```

Example: module export skeleton
```rust
pub mod convex_hull;
pub mod hull_kv_cache;
```
</examples>

<troubleshooting>
| Symptom | Cause | Fix |
|---------|-------|-----|
| `cargo init` or `cargo test` was assumed to exist earlier | No Rust workspace was present | Stop, scaffold explicitly, and update docs to reflect the new state |
| Module names in code and docs drift | Bootstrap renamed files without syncing docs | Reconcile names in `SPEC.md` and the affected RFC before adding more code |
| Too many dependencies appear in the first PR | Full roadmap was scaffolded instead of Phase 1 core | Remove non-core crates and land the smallest compilable slice |
</troubleshooting>

<references>
- `SPEC.md`: planned module tree and architecture baseline
- `IMPLEMENTATION_PLAN.md`: Phase 1 sequencing
- `RFC-001-hull-kv-cache.md`: cache interface and acceptance criteria
- `RFC-002-2d-attention.md`: attention head constraints
- `RFC-003-state-encoding-compiler.md`: next-layer interfaces after cache work
- `RESOURCES.md`: candidate dependencies
</references>
