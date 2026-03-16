# transformer-vm-rs — Resources

---

## 1. Primary Sources

| Resource | URL |
|----------|-----|
| **Blog post** | https://www.percepta.ai/blog/can-llms-be-computers |
| **HN discussion** | https://news.ycombinator.com/item?id=47348275 |
| **Percepta homepage** | https://www.percepta.ai/ |
| **Percepta careers** | https://jobs.ashbyhq.com/percepta |

## 2. Authors & Team

| Name | Role | Profile |
|------|------|---------|
| **Christos Tzamos** | Lead author, Percepta | https://tzamos.com, https://linkedin.com/in/ctzamos |
| **Athul Paul Jacob** | Researcher, Percepta | (mentioned in LinkedIn) |
| Percepta | General Catalyst transformation company | https://www.percepta.ai |

Prior work by Tzamos: "Teaching Transformers to Solve Combinatorial Problems through Efficient Trial & Error" (NeurIPS 2025) — GPT-2 achieving 99% on Sudoku via DFS strategy.

## 3. Architecture Quick Reference

| Component | Value |
|-----------|-------|
| d_model | 36 |
| num_heads | 18 |
| head_dim | 2 |
| num_layers | 7 |
| ff structure | gated (gate * val) |
| attention type | average-hard (argmax) |
| KV cache | HullKVCache (2D convex hull) |
| decoding complexity | O(k + log n) |
| throughput | 33K+ tokens/sec (CPU) |

## 4. Related Work

### Theoretical Foundations

| Paper | Year | Key idea |
|-------|------|----------|
| RASP (Weiss et al.) | 2021 | Programs that compile to Transformer weights |
| Looped Transformers as Programmable Computers (Giannou et al.) | 2023 | Theoretical proof Transformers are Turing-complete |
| Transformers Learn Shortcuts to Automata (Liu et al.) | 2023 | Transformers learning state machines |
| Neural Turing Machines (Graves et al.) | 2014 | Differentiable memory + neural controller |
| DeltaNet (Schlag et al.) | 2021 | Fast weight programming in transformers |

### Percepta Prior Work

| Paper | Year | Key idea |
|-------|------|----------|
| Teaching Transformers Combinatorial Problems | NeurIPS 2025 | GPT-2 + DFS for Sudoku (99% accuracy) |

### Efficient Attention

| Paper | Year | Relevance |
|-------|------|-----------|
| FlashAttention (Dao et al.) | 2022 | IO-aware attention optimization |
| Gated Linear Attention | 2024 | Linear attention with gating |
| Stolen Attention Effect | 2024 | Convex hull analysis of attention heads |

## 5. Convex Hull Algorithms

The HullKVCache requires efficient 2D convex hull operations:

| Algorithm | Insert | Query | Best for |
|-----------|--------|-------|----------|
| Andrew's monotone chain | O(n) rebuild | O(log h) tangent | Static hull |
| Incremental insertion | Amortized O(log n) | O(log h) | Online/streaming |
| Chan's algorithm | O(n log h) | O(log h) | Optimal worst-case |

For our use case (online insertions during autoregressive generation), **incremental insertion** is the right choice.

Key reference: "Computational Geometry: Algorithms and Applications" (de Berg et al.) Chapter 1.

## 6. Cargo Dependencies

```toml
[dependencies]
burn = { version = "0.20", features = ["ndarray", "wgpu", "autodiff"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
ratatui = "0.29"
crossterm = "0.28"
tracing = "0.1"
tracing-subscriber = "0.3"

[dev-dependencies]
criterion = "0.5"
proptest = "1"
approx = "0.5"
rand = "0.8"

# Phase 2: WASM support
# wasmparser = "0.225"  # for parsing .wasm files
# wasmtime = "30"       # for reference execution comparison
```

## 7. Verifiable Computation Angle

This project has a direct connection to your verifiable computation thesis:

**A STARK proof of transformer-vm execution** would prove that a program was executed correctly inside a transformer. This is more powerful than proving native WASM execution because:

1. The execution trace is in the model's output — it's a sequence of tokens, naturally suited to sequential verification
2. The 2D attention operations (convex hull queries) are algebraically simple — amenable to arithmetization
3. The gated FF operations are just matrix multiplies and element-wise products — standard STARK-provable operations

A "verified transformer-vm" would mean: given a program and inputs, a STARK proof certifies that the transformer correctly executed the program and produced the claimed output. This is the "verifiable computation for AI" thesis made concrete.

## 8. Strategic Positioning

| Project | What | Synergy |
|---------|------|---------|
| **attnres** | Attention over preceding layers | Different problem: which layers vs how to attend |
| **ddl-rs** | Geometric residual connections | Complementary: DDL improves trained layers |
| **jepa-rs** | World model architectures | Different domain: perception vs computation |
| **transformer-vm-rs** | Deterministic computation in transformers | Unique: no one else has this in Rust |

transformer-vm-rs is the most novel of the four — it implements an idea that has no reference implementation anywhere. The Percepta blog post is the only source. This makes it both the hardest (no code to reference) and the highest-signal project (pure from-paper implementation).
