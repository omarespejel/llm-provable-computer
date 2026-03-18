# transformer-vm-rs — Implementation Plan

---

## Phase 1: Convex Hull Engine (Days 1-3)

### Day 1: 2D Convex Hull

- [x] Implement `Point2D` and `ConvexHull2D` data structure
- [x] Implement incremental upper/lower hull construction (Andrew's monotone chain)
- [x] Implement `insert()` with hull maintenance
- [x] Implement `query_argmax()` with ternary search on hull
- [x] Unit tests: hull validity after random insertions, argmax correctness
- [x] Property tests: every argmax result matches brute-force O(n) scan
- [x] Benchmark: query time vs n (verify O(log n) scaling)

### Day 2: HullKVCache

- [x] **RFC-001:** Wrap ConvexHull2D with value storage → `HullKvCache`
- [x] Implement `insert(key: [f32; 2], value: &[f32])`
- [x] Implement `query_argmax(query: [f32; 2]) -> (id, &[f32])`
- [x] Handle edge cases: duplicate keys, collinear points, empty cache
- [x] Stress test: 1M insertions + queries, verify correctness and timing
- [x] Benchmark against naive O(n) scan KV cache

### Day 3: 2D Attention Head

- [x] **RFC-002:** Implement `Attention2D` struct with W_q, W_k, W_v projections (d_model → 2)
- [x] Implement `forward_step()` with HullKVCache integration
- [x] Implement `MultiHead2DAttention` (18 heads, concat to d_model=36)
- [x] Implement output projection (d_model → d_model)
- [x] Unit tests: single head output shape, multi-head concatenation
- [x] Differential test: 2D argmax attention matches full O(n) softmax-hardened attention

---

## Phase 2: State Machine (Days 4-6)

### Day 4: State Encoding

- [x] **RFC-003:** Implement `MachineState` struct
- [x] Implement `encode_state()` and `decode_state()` (binary encoding in d_model=36)
- [x] Implement simplified ISA: NOP, LOAD, STORE, ADD, SUB, JMP, JZ, HALT
- [x] Round-trip tests: encode → decode for all state field ranges
- [x] Edge cases: overflow, underflow, zero flag

### Day 5: Gated Feed-Forward + Transformer Block

- [x] Implement `GatedFeedForward` with `gate * value` structure
- [x] Implement `TransformerVmBlock` (LayerNorm + MultiHead2D + GatedFF)
- [x] Implement `TransformerVm` (embedding → blocks → head)
- [x] Forward pass smoke test with compiled weights
- [x] Verify state encoding round-trips through the full forward pass

### Day 6: Instruction Compiler

- [x] Implement `InstructionCompiler` for each ISA instruction
- [x] Compile ADD: set FF weights to modify ACC dimensions + increment PC
- [x] Compile LOAD: set attention weights to query memory address from KV history
- [x] Compile STORE: set token encoding to emit memory write into KV cache
- [x] Compile JMP/JZ: set FF weights to modify PC dimensions (conditional on flags)
- [x] Compile HALT: set halt flag dimension
- [x] Unit test: each instruction produces correct state transition

---

## Phase 3: Execution (Days 7-9)

### Day 7: Program Compiler + Runtime

- [x] **RFC-004:** Implement `ProgramCompiler` — compile instruction sequence into TransformerVm weights
- [x] Implement `ExecutionRuntime` — autoregressive execution loop
- [x] Implement execution trace recording
- [x] Test: compile and execute a 3-instruction program (ADD 5, ADD 3, HALT → ACC=8)

### Day 8: Integration Testing

- [x] Counter program: count from 0 to N
- [x] Addition program: compute A + B via repeated increment
- [x] Memory test: STORE values, LOAD them back
- [x] Conditional branching: compute absolute value (JZ to skip negation)
- [x] Long execution: 10,000+ steps without drift
- [x] Compare with native Rust execution of same programs

### Day 9: Performance + TUI

- [x] Measure tokens/sec on CPU
- [x] Implement ratatui TUI showing live execution trace:
  - Machine state (PC, ACC, SP, flags)
  - Memory contents
  - Execution step counter
  - Throughput
- [x] `examples/counter.rs` — visual counter execution
- [x] `examples/addition.rs` — visual addition execution

---

## Phase 4: Polish (Days 10-12)

### Day 10: Advanced Programs

- [x] Implement multiplication via addition loop
- [x] Implement Fibonacci sequence
- [ ] Implement simple sort (bubble sort on small array)
- [ ] Record execution traces for README demos

### Day 11: Documentation + Benchmarks

- [ ] Comprehensive doc comments
- [ ] README with architecture diagram, quick start, benchmark results
- [x] Criterion benchmarks: hull operations, forward pass, full execution
- [ ] Comparison table: transformer-vm-rs throughput vs native execution

### Day 12: Launch

- [x] Push to GitHub: `AbdelStark/transformer-vm-rs`
- [ ] Publish to crates.io
- [ ] Write announcement tweet
- [ ] Post to HN, r/rust, r/MachineLearning
- [ ] Share with Percepta team / Christos Tzamos

---

## Phase 5: Post-Launch (Week 2+)

- [ ] **RFC-005:** Hybrid architecture scaffold (compiled + trained layers)
- [ ] WASM bytecode compiler (beyond simplified ISA)
- [ ] Tract integration for optimized inference
- [x] Differentiable attention variant (HardSoftmax with temperature)
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
