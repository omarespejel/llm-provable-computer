---
name: spec-rfc-sync
description: Activate when editing architecture docs, RFCs, README claims, dependency notes, or implementation plans in llm-provable-computer. Use this whenever a change could create drift between SPEC.md, RFC-*.md, README.md, RESOURCES.md, PAPER_DIGEST.md, or IMPLEMENTATION_PLAN.md, and whenever code work must be reflected back into the docs.
prerequisites: rg, git, repository markdown files
---

# Spec/RFC Sync

<purpose>
Keep the documentation set internally consistent. In this repository, documentation drift is a product bug, not a cosmetic issue.
</purpose>

<context>
- `SPEC.md` is the architecture baseline and planned module tree.
- `RFC-001-hull-kv-cache.md` through `RFC-004-005-runtime-hybrid.md` hold component-specific detail.
- `README.md` is public-facing summary; keep it shorter and less detailed than `SPEC.md`.
- `IMPLEMENTATION_PLAN.md` is sequencing and scope, not the normative architecture.
- `RESOURCES.md` holds candidate dependencies and citations; versions there are planned, not installed.
</context>

<procedure>
1. Classify the requested change: terminology sync, architecture change, dependency change, or status reporting.
2. Read `SPEC.md` plus every RFC that names the affected concept.
3. If the change affects public positioning or caveats, read `README.md` and `PAPER_DIGEST.md` too.
4. Update the authoritative file first:
   - architecture or module layout -> `SPEC.md`
   - component algorithm or interface detail -> matching RFC
   - schedule or scope -> `IMPLEMENTATION_PLAN.md`
   - dependency/source list -> `RESOURCES.md`
5. Propagate the change outward so the same concept uses the same names, scope, and status labels everywhere.
6. Run `rg -n "HullKvCache|Attention2D|MachineState|ExecutionRuntime|Burn|Tract" *.md` or a term-specific search to catch stale references.
7. Inspect `git diff -- README.md SPEC.md RFC-*.md IMPLEMENTATION_PLAN.md RESOURCES.md PAPER_DIGEST.md` before finishing.
</procedure>

<patterns>
<do>
  - Mark unimplemented work as `planned`, `Phase 1`, or `Phase 2`.
  - Keep one canonical spelling for modules and types (`HullKvCache`, `Attention2D`, `MachineState`, `ExecutionRuntime`).
  - When dependency versions change, update `RESOURCES.md` and any user-facing claim that mentions them.
</do>
<dont>
  - Do not treat `IMPLEMENTATION_PLAN.md` as proof that a feature exists -> confirm against repository files.
  - Do not update only `README.md` for architectural changes -> sync `SPEC.md` and the relevant RFC.
  - Do not convert sourced performance claims into observed results -> only call them measured after local benchmarks exist.
</dont>
</patterns>

<examples>
Example: rename a planned module
```text
1. Update the module path in SPEC.md section 5.
2. Update the corresponding RFC interface snippet.
3. Search the repo for the old name and fix README/plan mentions.
```

Example: mark a dependency as tentative
```text
In RESOURCES.md, keep the version under candidate dependencies and add [verify] in CLAUDE.md rather than presenting it as installed.
```
</examples>

<troubleshooting>
| Symptom | Cause | Fix |
|---------|-------|-----|
| `README.md` and `SPEC.md` disagree about implemented features | One file was edited in isolation | Update `SPEC.md` first, then reconcile `README.md` |
| An RFC uses older type names | An architectural rename was not propagated | Search the old identifier across `*.md` and update all hits in one patch |
| Dependency versions look authoritative but no config files exist | Versions only live in `RESOURCES.md` | Treat them as planned and verify before creating code/config |
</troubleshooting>

<references>
- `SPEC.md`: architecture baseline and planned module tree
- `README.md`: public summary
- `IMPLEMENTATION_PLAN.md`: phased execution plan
- `RFC-001-hull-kv-cache.md`: HullKvCache design
- `RFC-002-2d-attention.md`: 2D attention design
- `RFC-003-state-encoding-compiler.md`: state encoding/compiler design
- `RFC-004-005-runtime-hybrid.md`: runtime and hybrid architecture design
- `RESOURCES.md`: candidate dependencies and sources
- `PAPER_DIGEST.md`: source caveats and research framing
</references>
