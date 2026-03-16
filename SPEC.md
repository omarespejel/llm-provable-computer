# transformer-vm-rs — Technical Specification

## Rust Implementation of "Can LLMs Be Computers?" using Burn & Tract

**Version 0.1.0-draft | March 2026**

---

## 1. Project Overview

transformer-vm-rs implements the key architectural innovations from Percepta's "Can LLMs Be Computers?" in Rust: 2D attention heads with HullKVCache for O(log n) lookups, the gated feed-forward compilation target, and a WASM-to-transformer weight compiler. The goal is to provide the first open-source implementation of a transformer that can deterministically execute programs inside its forward pass.

### 1.1 What We Build

1. **2D Attention Engine:** Attention heads restricted to 2 dimensions with convex-hull-based O(log n) KV lookup (HullKVCache)
2. **Gated Feed-Forward Compiler:** A module that compiles deterministic operations (WASM instructions) into gated FF layer weights
3. **WASM → Transformer Compiler:** A toolchain that takes .wasm bytecode and produces transformer weight matrices
4. **Execution Runtime:** An autoregressive inference loop that executes programs token-by-token through the transformer's forward pass
5. **Hybrid Architecture Scaffold:** Support for mixing compiled (deterministic) and trained (probabilistic) layers

### 1.2 What We Do NOT Build (Phase 1)

- Full WASM interpreter compilation (start with a simpler instruction set)
- Differentiable attention variants (start with average-hard attention)
- Training integration (start with compiled-only)
- GPU-optimized HullKVCache kernels

---

## 2. Core Architecture

### 2.1 Model Configuration

```rust
#[derive(Config, Debug, Clone)]
pub struct TransformerVmConfig {
    /// Model hidden dimension. Must be divisible by num_heads.
    /// Percepta uses d_model=36, 18 heads → 2 dims/head.
    pub d_model: usize,
    /// Number of attention heads. d_model / num_heads MUST equal 2.
    pub num_heads: usize,
    /// Number of transformer layers
    pub num_layers: usize,
    /// Vocabulary size (state encoding alphabet)
    pub vocab_size: usize,
    /// Maximum sequence length (execution trace length)
    pub max_seq_len: usize,
    /// Feed-forward intermediate dimension
    pub ff_dim: usize,
    /// Attention type
    #[config(default = "AverageHard")]
    pub attention_type: AttentionType,
}

#[derive(Debug, Clone)]
pub enum AttentionType {
    /// Average-hard attention: argmax lookup, not differentiable.
    /// Used in the original Percepta work.
    AverageHard,
    /// Softmax with temperature → 0: differentiable approximation.
    /// For future training integration.
    HardSoftmax { temperature: f64 },
    /// Standard softmax attention (baseline comparison).
    StandardSoftmax,
}

impl TransformerVmConfig {
    pub fn head_dim(&self) -> usize {
        assert_eq!(self.d_model / self.num_heads, 2,
            "transformer-vm requires exactly 2 dimensions per head");
        2
    }

    /// Percepta's reference configuration
    pub fn percepta_reference() -> Self {
        Self {
            d_model: 36,
            num_heads: 18,
            num_layers: 7,
            vocab_size: 256,  // byte-level state encoding
            max_seq_len: 1_000_000,
            ff_dim: 72,
            attention_type: AttentionType::AverageHard,
        }
    }
}
```

### 2.2 2D Attention Head

The central innovation. Each head operates on 2D key-value pairs, enabling convex-hull-based O(log n) lookups.

```rust
/// A single 2D attention head.
///
/// Unlike standard attention (d_head = 64-128), this head has exactly
/// 2 dimensions. This enables geometric algorithms (convex hull) for
/// efficient argmax computation.
///
/// Standard attention: O(n) per query (scan all keys)
/// 2D attention + HullKVCache: O(log n) per query (binary search on hull)
pub struct Attention2D<B: Backend> {
    /// Query projection: d_model → 2
    w_q: Linear<B>,
    /// Key projection: d_model → 2
    w_k: Linear<B>,
    /// Value projection: d_model → 2
    w_v: Linear<B>,
    /// Output projection: 2 → d_model/num_heads contribution
    w_o: Linear<B>,
    /// Head index (for output slice assignment)
    head_idx: usize,
}

impl<B: Backend> Attention2D<B> {
    /// Compute attention for this head.
    ///
    /// With AverageHard attention: finds the key with maximum dot product
    /// with the query (argmax), returns the corresponding value.
    /// With HullKVCache: this is O(log n) instead of O(n).
    pub fn forward(
        &self,
        x: &Tensor<B, 3>,           // [B, T, d_model]
        kv_cache: &HullKvCache<B>,   // maintained incrementally
        attention_type: &AttentionType,
    ) -> Tensor<B, 3>;  // [B, 1, 2] for the current step
}
```

### 2.3 HullKVCache

The data structure that makes million-step execution tractable.

```rust
/// Convex Hull KV Cache for O(log n) attention lookups in 2D.
///
/// In 2D, the key that maximizes dot product with any query lies on
/// the convex hull of all keys. The convex hull of n 2D points has
/// O(n) vertices in the worst case but can be maintained incrementally,
/// and querying (finding the tangent point for a given direction)
/// takes O(log h) where h is the hull size.
///
/// For program execution, keys encode memory addresses / state indices.
/// The convex hull structure enables O(log n) "memory lookups" where
/// standard attention would require O(n) scans.
pub struct HullKvCache {
    /// Upper hull points (sorted by x-coordinate)
    upper_hull: Vec<Point2D>,
    /// Lower hull points (sorted by x-coordinate)
    lower_hull: Vec<Point2D>,
    /// Associated values for each hull point
    values: HashMap<PointId, Vec<f32>>,
    /// Total number of KV pairs inserted
    size: usize,
}

#[derive(Clone, Copy)]
pub struct Point2D {
    pub x: f32,
    pub y: f32,
    pub id: PointId,
}

impl HullKvCache {
    /// Insert a new key-value pair. Maintains the convex hull incrementally.
    /// Amortized O(log n) per insertion.
    pub fn insert(&mut self, key: Point2D, value: &[f32]);

    /// Query: find the key that maximizes dot(query, key) on the hull.
    /// O(log h) where h is the hull size, via binary search on the hull.
    pub fn query_argmax(&self, query: Point2D) -> (Point2D, &[f32]);

    /// Number of points currently on the convex hull
    pub fn hull_size(&self) -> usize;

    /// Total number of KV pairs
    pub fn total_size(&self) -> usize;
}
```

### 2.4 Multi-Head 2D Attention

```rust
/// Multi-head attention where every head is 2D.
/// d_model = num_heads × 2.
pub struct MultiHead2DAttention<B: Backend> {
    heads: Vec<Attention2D<B>>,
    /// Per-head HullKVCache instances
    caches: Vec<HullKvCache>,
    /// Output projection: d_model → d_model
    out_proj: Linear<B>,
    num_heads: usize,
}
```

### 2.5 Gated Feed-Forward Layer

```rust
/// Gated feed-forward layer used as the compilation target.
///
/// output = gate(x) * value(x)
///
/// For compiled weights: gate encodes condition logic,
/// value encodes the transformation to apply.
/// For trained weights: standard gated FF (SwiGLU-like).
pub struct GatedFeedForward<B: Backend> {
    /// Projects input to gate + value (2 × ff_dim)
    ff_in: Linear<B>,
    /// Projects back to d_model
    ff_out: Linear<B>,
    ff_dim: usize,
}

impl<B: Backend> GatedFeedForward<B> {
    pub fn forward(&self, x: Tensor<B, 3>) -> Tensor<B, 3> {
        let projected = self.ff_in.forward(x);  // [B, T, 2*ff_dim]
        let chunks = projected.chunk(2, 2);      // gate: [B,T,ff_dim], val: [B,T,ff_dim]
        let gated = chunks[0].clone() * chunks[1].clone();
        self.ff_out.forward(gated)
    }
}
```

### 2.6 Transformer Block

```rust
pub struct TransformerVmBlock<B: Backend> {
    attention: MultiHead2DAttention<B>,
    ff: GatedFeedForward<B>,
    norm1: LayerNorm<B>,
    norm2: LayerNorm<B>,
}
```

### 2.7 Full Model

```rust
pub struct TransformerVm<B: Backend> {
    embedding: Embedding<B>,
    blocks: Vec<TransformerVmBlock<B>>,
    final_norm: LayerNorm<B>,
    lm_head: Linear<B>,
    config: TransformerVmConfig,
}

impl<B: Backend> TransformerVm<B> {
    /// Execute one step: given current state token, produce next state token.
    /// This is deterministic — same input always produces same output.
    pub fn step(&mut self, token: usize) -> usize;

    /// Execute a program for N steps from initial state.
    pub fn execute(&mut self, initial_state: &[usize], max_steps: usize) -> Vec<usize>;
}
```

---

## 3. WASM-to-Weights Compiler

### 3.1 Compilation Pipeline

```
C source → (Clang/Emscripten) → WASM bytecode → (compiler) → TransformerVm weights
```

### 3.2 Instruction Encoding Strategy

Each WASM instruction is encoded as a pattern in the transformer's weight matrices such that:

1. **Attention layers** implement memory read/write operations (the 2D hull structure maps address → value)
2. **FF layers** implement ALU operations (arithmetic, logic, comparison) via the gated structure
3. **The autoregressive loop** provides the program counter advancement

### 3.3 State Token Encoding

The program state (registers, memory, PC) is encoded into a fixed-size token representation of dimension d_model. For d_model=36:

- Bits 0-7: Program counter (instruction pointer)
- Bits 8-15: Stack pointer
- Bits 16-23: Accumulator / current value
- Bits 24-35: Flags, addressing mode, auxiliary

### 3.4 Simplified Instruction Set (Phase 1)

Before compiling full WASM, start with a minimal instruction set to validate the architecture:

| Instruction | Encoding | Operation |
|-------------|----------|-----------|
| NOP | 0x00 | No operation (PC += 1) |
| LOAD addr | 0x01 | ACC = MEM[addr] |
| STORE addr | 0x02 | MEM[addr] = ACC |
| ADD imm | 0x03 | ACC = ACC + imm |
| SUB imm | 0x04 | ACC = ACC - imm |
| JMP addr | 0x05 | PC = addr |
| JZ addr | 0x06 | if ACC == 0: PC = addr |
| HALT | 0xFF | Stop execution |

---

## 4. Testing Strategy

### Unit Tests

- HullKVCache: insertion maintains valid convex hull
- HullKVCache: query_argmax returns correct point for all query directions
- HullKVCache: O(log n) scaling verified empirically
- 2D attention head: argmax attention matches brute-force scan
- Gated FF: correct gating behavior with compiled weights
- State encoding: round-trip encode/decode preserves state

### Integration Tests

- Simple program (counter: increment ACC until overflow) executes correctly
- Addition program produces correct results for random inputs
- Comparison with native execution: same program, same output
- Million-step execution: no drift, no errors

### Property Tests

- Determinism: same input always produces same output sequence
- Hull invariant: after every insertion, hull property holds
- State conservation: state encoding is bijective (no information loss)

---

## 5. Module Structure

```
transformer-vm-rs/
├── Cargo.toml
├── README.md
├── LICENSE                          # MIT
├── src/
│   ├── lib.rs                       # Public API
│   ├── config.rs                    # TransformerVmConfig
│   ├── attention_2d.rs              # 2D attention head
│   ├── hull_kv_cache.rs             # HullKVCache (convex hull data structure)
│   ├── convex_hull.rs               # 2D convex hull algorithms
│   ├── multi_head_2d.rs             # Multi-head 2D attention
│   ├── gated_ff.rs                  # Gated feed-forward (compilation target)
│   ├── transformer_block.rs         # TransformerVmBlock
│   ├── model.rs                     # TransformerVm (full model)
│   ├── state_encoding.rs            # Program state ↔ token encoding
│   ├── compiler/
│   │   ├── mod.rs
│   │   ├── instruction_set.rs       # Simplified ISA
│   │   ├── isa_to_weights.rs        # Instruction → weight matrix compilation
│   │   └── wasm_compiler.rs         # WASM bytecode → weights (Phase 2)
│   ├── runtime.rs                   # Execution loop
│   └── diagnostics.rs               # Execution trace analysis
├── tests/
│   ├── hull_tests.rs
│   ├── attention_2d_tests.rs
│   ├── compiler_tests.rs
│   ├── execution_tests.rs
│   └── property_tests.rs
├── examples/
│   ├── addition.rs                  # Compile and run an addition program
│   ├── counter.rs                   # Simple counting loop
│   ├── sudoku.rs                    # Backtracking Sudoku solver (Phase 2)
│   └── demo_tui.rs                  # TUI showing execution trace
└── benches/
    ├── hull_benchmark.rs
    └── execution_benchmark.rs
```
