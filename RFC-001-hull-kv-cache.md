# RFC-001: HullKVCache — O(log n) Attention via 2D Convex Hulls

## Summary

Implement HullKVCache, a KV cache data structure that exploits the geometry of 2D attention heads to achieve O(log n) argmax attention lookups instead of O(n) linear scans. This is the core algorithmic innovation that makes million-step program execution tractable inside a transformer.

## Motivation

Standard attention computes `softmax(Q K^T / √d) V`, requiring O(n) work per query to scan all n keys. For a program executing millions of steps, this becomes O(n²) total — prohibitive.

Key insight: when attention heads have exactly 2 dimensions, the key that maximizes `dot(q, k)` for any query q must lie on the **convex hull** of the key set. In 2D, convex hulls have O(n) points in the worst case but can be maintained incrementally, and the tangent point (argmax direction) can be found via binary search in O(log h) where h is the hull size.

## Mathematical Foundation

For a query vector `q ∈ R²` and key set `{k_1, ..., k_n} ⊂ R²`:

```
argmax_i dot(q, k_i) = argmax_i (q_x k_ix + q_y k_iy)
```

This is equivalent to finding the support point of the key set in direction q. For a convex set, the support point always lies on the boundary (the convex hull). In 2D, the upper and lower hulls can each be binary-searched in O(log h).

## Interface

```rust
pub struct HullKvCache {
    upper_hull: Vec<HullPoint>,  // sorted by x-coordinate, ascending
    lower_hull: Vec<HullPoint>,  // sorted by x-coordinate, ascending
    values: Vec<ValueEntry>,     // value vectors indexed by point ID
    next_id: usize,
}

pub struct HullPoint {
    pub x: f32,
    pub y: f32,
    pub id: usize,
}

pub struct ValueEntry {
    pub value: Vec<f32>,  // d_head dimensional (2 for 2D heads)
}
```

## Core Operations

### Insert (amortized O(log n))

```rust
impl HullKvCache {
    pub fn insert(&mut self, key: [f32; 2], value: &[f32]) -> usize {
        let id = self.next_id;
        self.next_id += 1;
        let point = HullPoint { x: key[0], y: key[1], id };

        // Insert into upper hull (points above the line from leftmost to rightmost)
        self.insert_upper_hull(point);
        // Insert into lower hull (points below the line)
        self.insert_lower_hull(point);

        self.values.push(ValueEntry { value: value.to_vec() });
        id
    }

    fn insert_upper_hull(&mut self, p: HullPoint) {
        // Find insertion position by x-coordinate (binary search)
        let pos = self.upper_hull.partition_point(|h| h.x < p.x);

        // Check if p is above the current hull at this x
        // If not, p is interior — skip
        if self.is_above_upper_hull(&p, pos) {
            self.upper_hull.insert(pos, p);
            // Remove points that are now interior
            self.prune_upper_hull(pos);
        }
    }
}
```

### Query Argmax (O(log h))

```rust
impl HullKvCache {
    /// Find the key maximizing dot(query, key) across all stored keys.
    /// Returns (point_id, value).
    pub fn query_argmax(&self, query: [f32; 2]) -> (usize, &[f32]) {
        // The argmax must be on the convex hull.
        // Determine which hull to search based on query direction.
        let best_upper = self.search_upper_hull(query);
        let best_lower = self.search_lower_hull(query);

        let dot_upper = query[0] * best_upper.x + query[1] * best_upper.y;
        let dot_lower = query[0] * best_lower.x + query[1] * best_lower.y;

        let best = if dot_upper >= dot_lower { best_upper } else { best_lower };
        (best.id, &self.values[best.id].value)
    }

    /// Binary search on the upper hull for the tangent point in direction q.
    /// The tangent point maximizes dot(q, p) among hull vertices.
    fn search_upper_hull(&self, query: [f32; 2]) -> &HullPoint {
        // For a convex polygon, dot(q, p) is unimodal along the hull.
        // Use ternary search or derivative-based binary search.
        let hull = &self.upper_hull;
        if hull.len() <= 2 {
            return hull.iter()
                .max_by(|a, b| dot(query, a).partial_cmp(&dot(query, b)).unwrap())
                .unwrap();
        }

        let mut lo = 0;
        let mut hi = hull.len() - 1;
        while hi - lo > 2 {
            let m1 = lo + (hi - lo) / 3;
            let m2 = hi - (hi - lo) / 3;
            if dot(query, &hull[m1]) < dot(query, &hull[m2]) {
                lo = m1;
            } else {
                hi = m2;
            }
        }
        (lo..=hi)
            .map(|i| &hull[i])
            .max_by(|a, b| dot(query, a).partial_cmp(&dot(query, b)).unwrap())
            .unwrap()
    }
}

fn dot(q: [f32; 2], p: &HullPoint) -> f32 {
    q[0] * p.x + q[1] * p.y
}
```

## Complexity Analysis

| Operation | Standard KV Cache | HullKVCache |
|-----------|-------------------|-------------|
| Insert | O(1) | Amortized O(log n) |
| Query (argmax) | O(n) | O(log h) ≤ O(log n) |
| Memory | O(n × d) | O(n × d) + O(h) hull overhead |
| Total for n steps | O(n²) | O(n log n) |

For a 1M step program: standard = 10¹² operations. HullKVCache = ~2×10⁷ operations. A 50,000x speedup.

## Testing

1. **Hull validity:** After every insertion, verify hull is convex (cross-product test)
2. **Argmax correctness:** For random queries, verify hull argmax matches brute-force O(n) scan
3. **Insertion edge cases:** collinear points, duplicate x-coordinates, single point
4. **Scaling:** Empirically verify O(log n) query time with increasing n
5. **Adversarial input:** Points in sorted order, reverse order, circle (all on hull)

## Acceptance Criteria

- Correct argmax for all query directions
- Valid convex hull invariant maintained after every insertion
- Query time empirically O(log n) verified up to n = 1M
- No unsafe code in the hull algorithms
