# transformer-vm-rs

**Execute programs inside a transformer. Deterministically.**

The first open-source implementation of [Percepta's "Can LLMs Be Computers?"](https://www.percepta.ai/blog/can-llms-be-computers) architecture in Rust.

Compiles programs into transformer weight matrices. The model's forward pass IS the execution. Each token = one step of computation. 100% accuracy. No external tools.

Built with [burn](https://github.com/tracel-ai/burn). Runs on CPU, CUDA, Metal, wgpu.

## Key Innovation: O(log n) Attention via 2D Convex Hulls

Standard attention: O(n²) — can't run millions of execution steps.

2D attention heads (d_head=2) + HullKVCache: O(k + log n) per step — millions of steps on CPU.

The trick: with 2-dimensional keys, the argmax key always lies on the convex hull. Binary search on the hull gives O(log n) lookups instead of O(n) scans.

## Architecture

```
7 layers | d_model=36 | 18 heads × 2 dims | HullKVCache | Gated FF
```

## Source

> **Can LLMs Be Computers?** — Christos Tzamos et al., Percepta (March 2026)
> [Blog post](https://www.percepta.ai/blog/can-llms-be-computers) | [HN Discussion](https://news.ycombinator.com/item?id=47348275)

## License

MIT
