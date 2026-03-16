# RFC-002: 2D Attention Heads

## Summary

Implement attention heads restricted to exactly 2 dimensions per head. This is the architectural constraint that enables HullKVCache (RFC-001) to achieve O(log n) lookups. With d_model=36 and 18 heads, each head operates on a 2D query/key/value space.

## Key Design Decisions

### Average-Hard Attention

The original Percepta implementation uses "average-hard attention" — effectively argmax over keys. This is NOT softmax attention. For each query, the head returns the value associated with the key that maximizes dot(query, key). This is deterministic and non-differentiable.

```rust
pub enum Attention2DMode {
    /// Argmax: return value of the key with highest dot product.
    /// Deterministic, not differentiable. O(log n) via HullKVCache.
    AverageHard,
    /// Softmax with very low temperature: differentiable approximation.
    /// Falls back to O(n) scan (no hull optimization).
    HardSoftmax { temperature: f64 },
    /// Standard softmax: O(n) baseline for comparison.
    Softmax,
}
```

### Why 2D Is Sufficient

A 2D head can encode one "address dimension" (x) and one "value dimension" (y). For memory lookups in a program: x = memory address, y = priority/recency. The argmax in the query direction selects the most recent write to the queried address.

With 18 such heads (d_model=36), the model has 18 independent 2D lookup channels — enough to simultaneously access registers, memory cells, stack entries, and control flow state.

### Projection Matrices

```rust
pub struct Attention2D<B: Backend> {
    w_q: Linear<B>,  // d_model → 2
    w_k: Linear<B>,  // d_model → 2
    w_v: Linear<B>,  // d_model → 2
    head_idx: usize,
}

impl<B: Backend> Attention2D<B> {
    pub fn forward_step(
        &self,
        x: &Tensor<B, 2>,         // [B, d_model] current step
        cache: &mut HullKvCache,
    ) -> Tensor<B, 2> {           // [B, 2]
        let q = self.w_q.forward(x.clone());  // [B, 2]
        let k = self.w_k.forward(x.clone());  // [B, 2]
        let v = self.w_v.forward(x.clone());  // [B, 2]

        // Insert k,v into hull cache
        cache.insert(k.to_data(), v.to_data());

        // Query: find argmax key for this query
        let (_, val) = cache.query_argmax(q.to_data());
        Tensor::from_data(val)
    }
}
```

## Testing

1. **Dimension check:** Head dim is exactly 2 for all configurations
2. **Argmax correctness:** 2D attention matches brute-force full attention with hard argmax
3. **Multi-head assembly:** 18 heads produce [B, 36] output
4. **Cache integration:** KV cache grows correctly across steps
5. **Determinism:** Same input sequence produces identical output

## Acceptance Criteria

- Attention head operates strictly in 2D
- Integrates with HullKVCache for O(log n) queries
- Supports both AverageHard and Softmax modes
- Multi-head concatenation produces correct d_model output
