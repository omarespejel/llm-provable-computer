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

## 6. Sources

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
