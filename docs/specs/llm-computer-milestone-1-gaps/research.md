# Research: Milestone 1 Gaps — Real Transformer Execution

## 1. What Percepta Claims vs What We Have

### 1.1 Architecture Comparison

| Aspect | Percepta (blog) | transformer-vm-rs | Gap |
|--------|----------------|-------------------|-----|
| Layers | 7 | 1-4 (configurable) | Minor — config change |
| d_model | 36 | 36 | None |
| Heads | 18 (2D each) | 18 (2D each) | None |
| Attention | "Average-hard" (argmax, average ties) | Argmax via HullKvCache | None — equivalent in practice |
| Feed-forward | Gated: `gate * value` | Gated: `gate * value` via compiled matrices | None |
| State encoding | Not specified (implied binary) | Binary, {-1, +1}, 36 dimensions | None |
| ISA | WASM interpreter compiled into weights | Custom 26-instruction ISA | **Major** — no WASM |
| Weight format | Presumably standard tensor format | Custom `Matrix` struct in Rust | **Major** — not portable |
| Inference engine | Presumably PyTorch or custom | Hand-rolled Rust | **Major** — not framework-standard |
| ONNX / export | Unknown | None | **Major** — can't prove it's a real transformer |
| Throughput | 33K tok/sec (unspecified CPU) | 116K-576K tok/sec (release, M-series) | None — we're faster |
| Accuracy | 100% deterministic | 100% deterministic (verified) | None |

### 1.2 What "Average-Hard Attention" Actually Is

From formal language theory (Barceló et al., 2024; Angluin et al., 2023):

1. Compute `score_j = dot(q, k_j)` for all keys j
2. Find `max_score = max_j(score_j)`
3. Collect the set S of ALL positions where `score_j == max_score`
4. Return the **uniform average** of `v_j` for `j in S`

This differs from:
- **Unique-hard attention**: picks one winner arbitrarily on ties
- **Softmax attention**: weights all positions by exp(score)/sum

In practice, with compiled weights designed to produce unique maxima (our case), average-hard reduces to plain argmax. Our HullKvCache implementation is correct.

**Critical note**: Average-hard attention is NOT differentiable with respect to keys and queries. The blog's claim about differentiability was challenged on HN and is unproven.

### 1.3 Percepta's Undisclosed Details

The following are **not specified anywhere** in the blog post:

- Whether LayerNorm is used (likely omitted or identity for compiled weights)
- Whether residual connections exist (likely omitted — compiled weights can absorb them)
- The exact compilation procedure: how WASM opcodes become W_q, W_k, W_v, W_ff matrices
- State encoding format (bit-level layout within d_model=36)
- CPU hardware for the 33K tok/sec benchmark
- No code, no weights, no compiler have been released

### 1.4 Closest Open-Source Reference

**Giannou et al. (2023)**: "Looped Transformers as Programmable Computers"
- Paper: arxiv.org/abs/2301.13196
- Code: github.com/jysohn1108/Looped-Transformer
- Uses a single SUBLEQ instruction (Turing-complete one-instruction ISA)
- Compiles SUBLEQ programs into PyTorch transformer weights
- Demonstrates the compilation pipeline Percepta claims but doesn't show

This is the closest reference for understanding how instruction → weight compilation works in practice.

---

## 2. The Three Major Gaps

### Gap 1: No Standard Model Format

**Problem**: Our weights live in hand-rolled `Matrix` structs. No ML framework can load them. We can't prove to anyone that "this is a real transformer" without them being able to load the model into PyTorch, ONNX Runtime, or similar.

**Why it matters**: The whole thesis of the Percepta work is that a *standard transformer* can be a computer. If our implementation only runs in custom Rust code, it's just a VM with extra steps.

### Gap 2: No Framework-Based Forward Pass

**Problem**: Our forward pass is mathematically correct (real matmul, real gated FF, real hull attention), but implemented as direct Rust code. The execution doesn't flow through a standard tensor computation graph.

**Why it matters**: Reproducibility. Anyone should be able to load the model in PyTorch and get the same results. That's the proof.

### Gap 3: No ONNX Interop

**Problem**: We can't export our compiled model to ONNX, and we can't demonstrate the model running in any standard inference engine.

**Why it matters**: ONNX is the universal model interchange format. A model that exists only in a custom format isn't a "real" model in the ML community's eyes.

---

## 3. Framework Options

### 3.1 Burn 0.20.1

**Pros:**
- Pure Rust, aligns with our stack
- `#[derive(Module)]` for model definition
- `NdArray` backend: pure Rust, no external deps, deterministic
- New `CubeCL CPU` backend: up to 4x faster than LibTorch
- Backend Extension system for custom ops (designed for flash attention etc.)
- Record system for model serialization (MessagePack, bincode, JSON)
- `burn-onnx` can import ONNX models (but NOT export)
- Inference-only mode: use base backend without `Autodiff` wrapper

**Cons:**
- **Cannot export to ONNX** — import only (issue #918 open, unimplemented)
- Pre-1.0 API, breaking changes between minor versions
- Record format is Burn-specific (not readable by PyTorch/ONNX Runtime)
- Would need custom Backend Extension for HullKvCache attention

**Assessment**: Good for implementing the model in a real framework, but doesn't solve the ONNX export gap.

### 3.2 Tract

**Pros:**
- Pure Rust ONNX inference runtime
- Can load ONNX models and run them
- `TypedModel` API for building models programmatically
- Custom operator support via `EvalOp`/`TypedOp` traits
- All needed ops: MatMul, element-wise mul, bias add, argmax
- NNEF/OPL serialization format
- Designed for embedded/deterministic inference

**Cons:**
- Cannot export TO ONNX (reads ONNX, writes NNEF)
- No GPU support
- Performance ~2x slower than ONNX Runtime (but adequate for our use)
- Would need custom `HullAttention` op implementation

**Assessment**: Good for running ONNX models, but doesn't help us create ONNX files.

### 3.3 ONNX Generation (Python or Rust)

**The key insight**: Neither Burn nor Tract can EXPORT ONNX. But we can GENERATE ONNX model files directly using the ONNX protobuf format.

**Python path** (recommended for initial prototype):
- `onnx.helper.make_model`, `make_graph`, `make_node`, `make_tensor`
- Can create arbitrary model graphs including custom ops
- Mature, well-documented, widely used
- Generate the .onnx file, then load it in Burn/Tract/ONNX Runtime

**Rust path** (for integration into our codebase):
- `onnx-protobuf` crate: raw protobuf structs for ONNX format
- Can serialize valid `.onnx` files from Rust
- Lower-level but keeps everything in Rust

### 3.4 Recommended Architecture

```
┌─────────────────────────────────────────────────────┐
│                  transformer-vm-rs                    │
│                                                       │
│  ┌──────────────┐    ┌──────────────┐                │
│  │  Current VM   │    │  Burn Model   │                │
│  │  (fast path)  │    │  (real xfmr)  │                │
│  │  Matrix/Rust  │    │  NdArray BE   │                │
│  └──────┬───────┘    └──────┬───────┘                │
│         │                    │                         │
│         ▼                    ▼                         │
│    ExecutionRuntime    BurnExecutionRuntime             │
│         │                    │                         │
│         └────────┬───────────┘                         │
│                  ▼                                     │
│         Differential Verifier                          │
│    (both must produce same trace)                      │
│                                                       │
│  ┌──────────────┐    ┌──────────────┐                │
│  │ ONNX Export   │    │  Tract Runner │                │
│  │ (onnx-protobuf│    │  (loads .onnx)│                │
│  │  or Python)   │    │              │                │
│  └──────┬───────┘    └──────┬───────┘                │
│         │                    │                         │
│         ▼                    ▼                         │
│      model.onnx ──────> Tract inference                │
│         │                                             │
│         ▼                                             │
│   ONNX Runtime / PyTorch (external validation)         │
└─────────────────────────────────────────────────────┘
```

---

## 4. Tiny Reference Models

### 4.1 HuggingFace Tiny Models

| Model | d_model | Layers | Heads | ONNX? | Notes |
|-------|---------|--------|-------|-------|-------|
| `hf-internal-testing/tiny-random-gpt2` | 32 | 2 | 2 | No (exportable) | Random weights, test fixture |
| `fxmarty/gpt2-tiny-onnx` | varies | varies | varies | **Yes** | Pre-exported ONNX |
| `TaylorAI/gte-tiny` | 384 | ~3 | varies | **Yes** (quantized too) | Trained, ONNX included |
| `google/t5-efficient-tiny` | 256 | 4+4 | 4 | No (exportable) | Smallest trained Google model |
| Custom (stas00 recipe) | 8+ | 1+ | 1+ | Exportable | Arbitrary tiny config |

### 4.2 Our Target Model Spec

For the "real transformer" demonstration, we want:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| d_model | 36 | Match Percepta exactly |
| num_heads | 18 | Match Percepta (2D per head) |
| num_layers | 1-7 | Configurable, start with 1 |
| ff_dim | 72 | 2x d_model, match Percepta |
| vocab_size | N/A | We use continuous state encoding, not discrete tokens |
| attention | Custom (hull or decomposed) | See RFC-B below |
| format | ONNX + Burn Records | Dual export |

### 4.3 ONNX Custom Operators

For HullAttention, two approaches:

**Option A: Custom op domain**
```
domain: "com.transformer_vm"
op_type: "HullAttention2D"
```
Requires custom runtime support in ONNX Runtime / Tract.

**Option B: Decompose into standard ops**
Express 2D argmax attention using standard ONNX ops:
- MatMul for Q*K^T
- ReduceMax + Where for argmax selection
- Gather for value retrieval

Option B is more portable but loses the O(log n) hull optimization. For correctness demonstration, Option B suffices — the results are identical, just O(n) instead of O(log n).

---

## 5. Key Decisions Needed

1. **Burn vs Tract vs Both?** — Recommendation: Burn for model definition + weights, ONNX generation for portability, Tract for validation.

2. **Custom attention op vs standard-op decomposition?** — Recommendation: Start with standard-op decomposition for ONNX portability, add custom hull op as optimization.

3. **Python ONNX generation vs Rust?** — Recommendation: Rust via `onnx-protobuf` to keep single-language stack, with Python script as validation tool.

4. **How to handle the WASM gap?** — Out of scope for this milestone. Our custom ISA is sufficient to demonstrate the architecture. WASM compilation is a separate future milestone.

5. **What constitutes "proof" that this is a real transformer?** — Being able to: (a) export weights to ONNX, (b) load them in ONNX Runtime or PyTorch, (c) run the same program and get the same trace.

---

## 6. Giannou Reference Implementation Analysis

The closest open-source reference to what Percepta describes is the Giannou et al. "Looped Transformers as Programmable Computers" implementation at `github.com/jysohn1108/Looped-Transformer`. A detailed code analysis reveals the exact compilation pattern.

### 6.1 Architecture (the TF class)

The transformer block (`subleq.py:710-760`) has this exact structure:

```python
class TF:
    Q  = np.zeros((num_rows_Q, num_rows_X))   # Query projection
    K  = np.zeros((num_rows_Q, num_rows_X))   # Key projection
    V  = np.zeros((num_rows_X, num_rows_X))   # Value projection
    W1 = np.zeros((num_rows_W, num_rows_X))   # FF layer 1 weight
    b1 = np.zeros((num_rows_W, num_cols_X))   # FF layer 1 bias
    W2 = np.zeros((num_rows_X, num_rows_W))   # FF layer 2 weight
    b2 = np.zeros((num_rows_X, num_cols_X))   # FF layer 2 bias

    def forward(self, X):
        # Attention: X' = X + V @ X @ softmax(X^T K^T Q X, temperature=lambda)
        softmax_output = numpy_softmax(X.T @ K.T @ Q @ X, lam=lambda)
        attn = X + V @ X @ softmax_output

        # Feed-forward: output = attn + W2 @ ReLU(W1 @ attn + b1) + b2
        output = attn + W2 @ numpy_relu(W1 @ attn + b1) + b2
        return output
```

Key observations:
- **Residual connections** are used (`X +` and `attn +`)
- **No LayerNorm** — error correction layer serves as substitute
- **ReLU activation** in FF (not gated `gate * value` — Percepta's gating is different from Giannou's)
- **State is a 2D matrix** `(num_rows_X, n)`, not a 1D token vector
- **Biases are 2D** `(rows, cols)`, allowing per-column bias (critical for selective writes)
- **Large lambda** (10-100) makes softmax approach hard argmax

### 6.2 How Instructions Compile to Weights

Each SUBLEQ instruction cycle uses **13 transformer blocks** across 6 logical steps:

| Step | Blocks | Attention? | What it does |
|------|--------|-----------|-------------|
| `read_inst` | 1 | 1 head | Q/K match PC against positional encodings → selects current instruction column |
| `read_mem` | 1 | 2 heads | Q/K match address pointers against column positions → reads mem[a] and mem[b] |
| `subtract_mem` | 3 | None | ReLU carry circuits compute mem[b] - mem[a] in binary (6 neurons per bit) |
| `write_mem` | 1 | 1 head | Attention selects target column, FF writes result with indicator-row gating |
| `conditional_branch` | 3 | None | Compute branch flag, conditionally update PC |
| `error_correction` | 1 | None | Snap all {-1, +1} encoded values back to exact {-1, +1} to fix softmax drift |

The weight-setting pattern is always:
1. Instantiate `TF(...)` with zero weights
2. Set Q, K, V entries (identity sub-matrices for address matching)
3. Set W1, b1, W2, b2 entries (identity, scaled identity, or carry-circuit weights)
4. Return the configured block

### 6.3 Attention as Address Lookup

Attention implements memory addressing via positional encoding matching:

```
score(col_i, col_j) = x_i^T @ K^T @ Q @ x_j
```

When Q and K extract the PC bits and positional encoding bits respectively, the score is maximized for the column whose positional encoding matches the current PC — implementing an argmax selector.

With large lambda (hard softmax), this is equivalent to our HullKvCache argmax. The mathematical difference: Giannou uses softmax-with-temperature approaching hard, we use actual geometric argmax on the convex hull. Both produce the same result.

### 6.4 Binary Arithmetic via ReLU Circuits

The most complex weight structures implement binary addition with carry propagation. For N-bit numbers, `subtract_mem` uses 6*N ReLU neurons per bit position:

```python
# For each bit i, 6 neurons compute carry chain:
f.W1[6*(N-i),   ref+N-j] = (2**(j-1)) / 2
f.W1[6*(N-i)+1, ref+N-j] = (2**(j-1)) / 2
# ... (pattern from Lemma C.1 of the paper)
f.W2[output_row, 6*(N-i):6*(N-i+1)] = 2*np.array([1,-1,1,-1,1,-1])
```

This is directly analogous to our bitwise instruction compilation in `model.rs`, where we decompose AND/OR/XOR into per-bit operations in the gated FF.

### 6.5 Key Differences from Our Approach

| Aspect | Giannou | transformer-vm-rs |
|--------|---------|-------------------|
| State shape | 2D matrix (rows × columns) | 1D vector (d_model=36) |
| ISA | SUBLEQ (1 instruction) | 26-instruction ISA |
| Arithmetic | ReLU carry circuits (6N neurons/bit) | Direct i16 arithmetic via gated FF |
| Memory model | Column-based (each addr = column) | Per-address HullKvCache |
| Attention | Softmax with high temperature | True argmax via convex hull |
| Error correction | Explicit snap-back layer | Not needed (exact integer arithmetic) |
| FF activation | ReLU | Gated (gate * value) |
| Framework | NumPy | Rust |

### 6.6 Implications for Our ONNX Export

The Giannou implementation validates that **the compilation approach works**: you CAN populate transformer weight matrices to execute arbitrary programs. Their forward pass uses standard ops (MatMul, Softmax, ReLU, Add) — exactly what we need for ONNX export.

The key insight for our ONNX export: since our gated FF uses `gate * value` instead of `ReLU`, the ONNX graph needs `Mul` (element-wise) instead of `Relu`. Both are standard ONNX ops.

---

## 7. Sources

- Percepta blog: percepta.ai/blog/can-llms-be-computers
- HN discussion: news.ycombinator.com/item?id=47348275
- Giannou et al. (2023): "Looped Transformers as Programmable Computers" (arxiv 2301.13196)
- Giannou reference code: github.com/jysohn1108/Looped-Transformer
- Burn framework: burn.dev, github.com/tracel-ai/burn
- Burn 0.20.0 release: burn.dev/blog/release-0.20.0/
- Burn ONNX import: github.com/tracel-ai/burn-onnx
- Burn ONNX export request: github.com/tracel-ai/burn/issues/918
- Tract: github.com/sonos/tract
- ONNX spec: onnx.ai/onnx/intro/python.html
- onnx-protobuf crate: crates.io/crates/onnx-protobuf
- Average-hard attention: Barceló et al. (2024), arxiv 2308.03212
- ALTA compiler: Yang et al. (2024), arxiv 2410.18077
