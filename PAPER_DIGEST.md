# Can LLMs Be Computers? — Technical Digest

**Authors:** Christos Tzamos and team at Percepta (General Catalyst transformation company)
**Date:** March 11, 2026
**Blog post:** [percepta.ai/blog/can-llms-be-computers](https://www.percepta.ai/blog/can-llms-be-computers)
**HN discussion:** [news.ycombinator.com/item?id=47348275](https://news.ycombinator.com/item?id=47348275)

---

## Core Claim

A standard autoregressive transformer can function as a universal computer. Percepta compiled a WebAssembly interpreter directly into the weights of a 7-layer transformer, enabling it to execute arbitrary C programs — step by step, token by token — entirely within the model's forward pass. No external tools. No tool-calling. The execution trace IS the model's output.

## Why This Matters

Standard LLMs are probabilistic next-token predictors. They approximate computation but cannot reliably execute it. Ask GPT-4 to add 1847392 + 9284716 and it will often get it wrong — token prediction is not digit-carrying. The current workaround (tool-calling) exits the model entirely: the LLM generates Python code, an external interpreter runs it, and results are injected back. The computation happens outside the differentiable graph.

Percepta's approach keeps computation inside the transformer. The model doesn't call a calculator — it IS a calculator. Each generated token represents one step of deterministic program execution. The execution trace is part of the model's output sequence, meaning (in theory) gradients can flow through the computation itself.

## Architecture

### Key Specifications

| Parameter | Value |
|-----------|-------|
| Layers | 7 |
| d_model | 36 |
| Attention heads | 18 |
| Dimensions per head | 2 |
| Throughput (CPU) | 33,000+ tokens/sec |
| Accuracy | 100% (deterministic) |
| Attention type | "Average-hard attention" |

### The 2D Attention Head Insight

This is the core architectural innovation. Each attention head operates in only 2 dimensions (d_model=36 / 18 heads = 2 dims per head). This is far smaller than standard transformers (typically 64-128 dims per head).

Why 2D matters: In 2D space, the convex hull of a set of points can be maintained incrementally in O(log n) time. This enables **HullKVCache** — a KV cache data structure that exploits 2D geometry to perform argmax attention lookups in O(log n) instead of O(n).

Standard attention: O(n²) per layer for n tokens — prohibitive for millions of execution steps.
HullKVCache attention: O(k + log n) per decoding step, where k is the program state size.

This is what makes million-step program execution tractable. Without this, the quadratic attention cost would make the approach impractical.

### Feed-Forward with Gating

The feed-forward layers use a gated architecture:

```
gate, val = ff_in(x).chunk(2, dim=-1)
output = gate * val  // or gated variant
```

This is structurally similar to SwiGLU/GeGLU but in the context of a compiled (not trained) model, the gates encode deterministic program logic rather than learned activations.

### The Compilation Pipeline

```
C source code
    ↓ (Clang/Emscripten)
WebAssembly bytecode (.wasm)
    ↓ (Percepta compiler)
Transformer weight matrices
    ↓ (Forward pass)
Execution trace (token by token)
```

Each WASM instruction is encoded into the transformer's weight matrices such that one forward pass step = one instruction execution. The transformer's autoregressive generation loop becomes the program's execution loop.

### State Representation

The program's state (registers, memory, program counter) is encoded in the token representation. Each token in the sequence encodes the complete machine state after one execution step. The attention mechanism provides the "memory" — the model looks back at previous states to read/write memory locations.

The 2D attention heads are sufficient because memory lookups in a WASM interpreter can be decomposed into 2D coordinate lookups (address → value), where the convex hull structure enables O(log n) search.

## Results

### Arithmetic

Multi-digit addition with 100% accuracy across millions of tokens. The model executes the same carry-propagation algorithm a CPU would — deterministically, not probabilistically. This is fundamentally different from an LLM "predicting" the answer.

### Sudoku

Solved Arto Inkala's "hardest Sudoku puzzle ever" with 100% accuracy in under 3 minutes. The model executes a compiled backtracking solver — it doesn't "reason" about the puzzle, it runs a program that solves it.

### Throughput

33,000+ tokens/sec on CPU. Each token = one execution step. For comparison, a 7B parameter LLM generates ~30-100 tokens/sec. The compact architecture (7 layers, d_model=36) enables this speed.

## Critical Limitations & Open Questions

### Not Trained — Compiled

**This is the most important caveat.** The weights are NOT learned via gradient descent. They are directly compiled from the WASM interpreter specification. This means:

- The model doesn't "learn" to compute — it has computation injected into its weights
- There is no training methodology demonstrated
- It's unclear if this approach can be made trainable
- One HN commenter: "If you want a WASM interpreter, just run a WASM interpreter"

### Differentiability is Unproven

The blog claims the execution trace is differentiable, which would allow integrating computational modules into trainable models. But the implementation uses "average-hard attention" which is NOT differentiable with respect to keys and queries. The authors acknowledge differentiable variants "should" work but don't demonstrate this.

### Performance vs Native Execution

33K tokens/sec sounds fast for a transformer, but may be ~10,000x slower than native WASM execution for the same programs. No benchmarks against native WASM, Python tool-calling, or a calculator are provided.

### No Code Released

No reference implementation, no model weights, no compilation toolchain. The blog post is the only artifact.

## Why This Is Still Architecturally Important

Despite the valid criticisms, two innovations have standalone value:

1. **2D Attention Heads + HullKVCache:** An attention mechanism that achieves O(log n) lookups by restricting heads to 2 dimensions and exploiting convex hull geometry. This is a genuine algorithmic contribution applicable beyond program execution — it could enable efficient long-context attention for any task where lookups can be decomposed into low-dimensional coordinates.

2. **The hybrid architecture concept:** A transformer where some layers perform deterministic computation (compiled weights) and other layers perform probabilistic generation (trained weights). The compiled layers could serve as "fast paths" for arithmetic, logic, and search, while trained layers handle language understanding and generation. This "fast/slow" hybrid is a compelling systems primitive.

As one HN commenter noted: "The most interesting thing here is that just 2D heads are enough to do useful computation and that there is an O(log n) algorithm to compute argmax attention with 2D heads. It seems that you could make an efficient pseudosymbolic LLM with some frozen layers that perform certain deterministic operations, but also other layers that are learned."

## Relationship to Prior Work

| Work | Approach | Difference |
|------|----------|------------|
| Tool-calling (ChatGPT + Python) | LLM generates code, external tool executes | Computation exits the model |
| RASP (Weiss et al., 2021) | Programs that compile to Transformer weights | Theoretical framework; Percepta claims practical WASM |
| Looped Transformers (Giannou et al.) | Transformers as programmable computers | Theoretical construction; Percepta adds efficient attention |
| GPT-25 (Percepta NeurIPS 2025) | Teaching Transformers combinatorial problems | Trained model; this work is compiled |
| Neural Turing Machines | Differentiable memory + controller | Learned controllers; Percepta compiles deterministic ones |
