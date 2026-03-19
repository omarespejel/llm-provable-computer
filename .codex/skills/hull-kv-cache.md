---
name: hull-kv-cache
description: Activate when implementing, testing, reviewing, or debugging the convex-hull KV cache, 2D attention lookup path, or any O(log n) argmax-attention claim in llm-provable-computer. Use this for geometry-heavy work where correctness and complexity claims both matter.
prerequisites: rg, git, RFC-001, RFC-002, property-test mindset
---

# HullKVCache

<purpose>
Implement and verify the 2D convex-hull cache that makes argmax attention sublinear. This is the most failure-sensitive algorithm in the repository plan.
</purpose>

<context>
- `RFC-001-hull-kv-cache.md` defines the cache interface and acceptance criteria.
- `RFC-002-2d-attention.md` depends on each head staying strictly 2D.
- `IMPLEMENTATION_PLAN.md` puts convex hull correctness before higher-level model work.
- The repo currently has no code, so start from tests and oracles rather than optimizing for integration.
</context>

<procedure>
1. Read `RFC-001-hull-kv-cache.md`, `RFC-002-2d-attention.md`, and the `HullKvCache` sections in `SPEC.md`.
2. Build a brute-force oracle over raw points before writing hull search logic.
3. Implement point helpers and hull invariant checks first:
   - orientation / cross-product
   - monotonic ordering
   - convexity checks after each insertion
4. Implement insertion with explicit edge-case handling for:
   - empty cache
   - single point
   - duplicate keys
   - collinear points
   - duplicate x-coordinates
5. Implement `query_argmax()` and compare every result against the brute-force oracle across random seeds.
6. Add property tests before benchmarks.
7. Benchmark insert and query separately; only then connect the cache to higher-level attention code.
</procedure>

<patterns>
<do>
  - Keep value storage separate from hull search logic so geometry bugs are easier to isolate.
  - Compare against a brute-force `dot(query, key)` scan for every nontrivial test case.
  - Use deterministic tie-breaking for duplicates and collinear points.
</do>
<dont>
  - Do not optimize before a brute-force oracle exists -> you will not know if the hull is wrong.
  - Do not couple `HullKvCache` directly to Burn tensors in the first iteration -> keep the core structure data-only.
  - Do not claim `O(log n)` from code inspection alone -> add benchmarks that separate query time from insertion/setup.
</dont>
</patterns>

<examples>
Example: correctness oracle
```rust
let (best_id, _) = cache.query_argmax([qx, qy]);
assert_eq!(best_id, brute_force_best_id(&points, [qx, qy]));
```

Example: edge-case test set
```text
empty -> 1 point -> duplicate point -> collinear line -> random cloud -> adversarial sorted inserts
```
</examples>

<troubleshooting>
| Symptom | Cause | Fix |
|---------|-------|-----|
| Query returns an interior point | Hull pruning or tangent search is wrong | Recompute against the brute-force oracle and inspect the hull after each insert |
| Duplicate or collinear inserts panic or reorder unpredictably | Tie-breaking rules were never defined | Add deterministic ordering and explicit duplicate handling |
| Benchmark does not show sublinear query scaling | Query benchmark is dominated by setup or small `n` | Prebuild the cache, separate insert/query benches, and increase dataset size |
</troubleshooting>

<references>
- `RFC-001-hull-kv-cache.md`: primary interface, complexity targets, tests
- `RFC-002-2d-attention.md`: why the cache depends on 2D heads
- `SPEC.md`: `HullKvCache` placement in the wider architecture
- `IMPLEMENTATION_PLAN.md`: phase ordering and success criteria
</references>
