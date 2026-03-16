# transformer-vm-rs — Implementation Plan

---

## Phase 1: Convex Hull Engine (Days 1-3)

### Day 1: 2D Convex Hull

- [ ] Implement `Point2D` and `ConvexHull2D` data structure
- [ ] Implement incremental upper/lower hull construction (Andrew's monotone chain)
- [ ] Implement `insert()` with hull maintenance
- [ ] Implement `query_argmax()` with ternary search on hull
- [ ] Unit tests: hull validity after random insertions, argmax correctness
- [ ] Property tests: every argmax result matches brute-force O(n) scan
- [ ] Benchmark: query time vs n (verify O(log n) scaling)

### Day 2: HullKVCache

- [ ] **RFC-001:** Wrap ConvexHull2D with value storage → `HullKvCache`
- [ ] Implement `insert(key: [f32; 2], value: &[f32])` 
- [ ] Implement `query_argmax(query: [f32; 2]) -> (id, &[f32])`
- [ ] Handle edge cases: duplicate keys, collinear points, empty cache
- [ ] Stress test: 1M insertions + queries, verify correctness and timing
- [ ] Benchmark against naive O(n) scan KV cache

### Day 3: 2D Attention Head

- [ ] **RFC-002:** Implement `Attention2D` struct with W_q, W_k, W_v projections (d_model → 2)
- [ ] Implement `forward_step()` with HullKVCache integration
- [ ] Implement `MultiHead2DAttention` (18 heads, concat to d_model=36)
- [ ] Implement output projection (d_model → d_model)
- [ ] Unit tests: single head output shape, multi-head concatenation
- [ ] Differential test: 2D argmax attention matches full O(n) softmax-hardened attention

---

## Phase 2: State Machine (Days 4-6)

### Day 4: State Encoding

- [ ] **RFC-003:** Implement `MachineState` struct
- [ ] Implement `encode_state()` and `decode_state()` (binary encoding in d_model=36)
- [ ] Implement simplified ISA: NOP, LOAD, STORE, ADD, SUB, JMP, JZ, HALT
- [ ] Round-trip tests: encode → decode for all state field ranges
- [ ] Edge cases: overflow, underflow, zero flag

### Day 5: Gated Feed-Forward + Transformer Block

- [ ] Implement `GatedFeedForward` with `gate * value` structure
- [ ] Implement `TransformerVmBlock` (LayerNorm + MultiHead2D + GatedFF)
- [ ] Implement `TransformerVm` (embedding → blocks → head)
- [ ] Forward pass smoke test with random weights
- [ ] Verify output shape: input [B, T] → output [B, T, vocab]

### Day 6: Instruction Compiler

- [ ] Implement `InstructionCompiler` for each ISA instruction
- [ ] Compile ADD: set FF weights to modify ACC dimensions + increment PC
- [ ] Compile LOAD: set attention weights to query memory address from KV history
- [ ] Compile STORE: set token encoding to emit memory write into KV cache
- [ ] Compile JMP/JZ: set FF weights to modify PC dimensions (conditional on flags)
- [ ] Compile HALT: set halt flag dimension
- [ ] Unit test: each instruction produces correct state transition

---

## Phase 3: Execution (Days 7-9)

### Day 7: Program Compiler + Runtime

- [ ] **RFC-004:** Implement `ProgramCompiler` — compile instruction sequence into TransformerVm weights
- [ ] Implement `ExecutionRuntime` — autoregressive execution loop
- [ ] Implement execution trace recording
- [ ] Test: compile and execute a 3-instruction program (ADD 5, ADD 3, HALT → ACC=8)

### Day 8: Integration Testing

- [ ] Counter program: count from 0 to N
- [ ] Addition program: compute A + B via repeated increment
- [ ] Memory test: STORE values, LOAD them back
- [ ] Conditional branching: compute absolute value (JZ to skip negation)
- [ ] Long execution: 10,000+ steps without drift
- [ ] Compare with native Rust execution of same programs

### Day 9: Performance + TUI

- [ ] Measure tokens/sec on CPU
- [ ] Implement ratatui TUI showing live execution trace:
  - Machine state (PC, ACC, SP, flags)
  - Memory contents
  - Execution step counter
  - Throughput
- [ ] `examples/counter.rs` — visual counter execution
- [ ] `examples/addition.rs` — visual addition execution

---

## Phase 4: Polish (Days 10-12)

### Day 10: Advanced Programs

- [ ] Implement multiplication via addition loop
- [ ] Implement Fibonacci sequence
- [ ] Implement simple sort (bubble sort on small array)
- [ ] Record execution traces for README demos

### Day 11: Documentation + Benchmarks

- [ ] Comprehensive doc comments
- [ ] README with architecture diagram, quick start, benchmark results
- [ ] Criterion benchmarks: hull operations, forward pass, full execution
- [ ] Comparison table: transformer-vm-rs throughput vs native execution

### Day 12: Launch

- [ ] Push to GitHub: `AbdelStark/transformer-vm-rs`
- [ ] Publish to crates.io
- [ ] Write announcement tweet
- [ ] Post to HN, r/rust, r/MachineLearning
- [ ] Share with Percepta team / Christos Tzamos

---

## Phase 5: Post-Launch (Week 2+)

- [ ] **RFC-005:** Hybrid architecture scaffold (compiled + trained layers)
- [ ] WASM bytecode compiler (beyond simplified ISA)
- [ ] Tract integration for optimized inference
- [ ] Differentiable attention variant (HardSoftmax with temperature)
- [ ] Sudoku solver demo (compile backtracking solver)
- [ ] Browser demo via WASM compilation of the Rust code itself (meta!)
- [ ] Blog post: "Building a Computer Inside a Transformer in Rust"
- [ ] Explore integration with verifiable computation (STARK proof of transformer execution)

---

## Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| HullKVCache O(log n) verified | Day 2 |
| Simple program executes correctly | Day 7 |
| 10K+ step execution without errors | Day 8 |
| 10K+ tokens/sec on CPU | Day 9 |
| Published to crates.io | Day 12 |
| GitHub stars (week 1) | 200-500 |
