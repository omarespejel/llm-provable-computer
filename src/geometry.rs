use crate::config::Attention2DMode;
use crate::error::{Result, VmError};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Point2D {
    pub x: f32,
    pub y: f32,
    pub id: usize,
}

#[derive(Debug, Clone)]
struct Entry {
    point: Point2D,
    value: Vec<f32>,
}

/// Convex Hull KV Cache for O(log n) attention lookups in 2D.
///
/// Maintains the convex hull of all inserted keys incrementally. For the
/// common case where keys arrive with monotonically increasing x-coordinates
/// (memory writes where x = step number), insertion is amortized O(1).
///
/// Queries find the key maximizing `dot(query, key)` in O(log h) via ternary
/// search on the hull, where h is the hull size.
#[derive(Debug, Clone)]
pub struct HullKvCache {
    entries: Vec<Entry>,
    /// Upper hull indices, sorted by ascending x-coordinate.
    upper_hull: Vec<usize>,
    /// Lower hull indices, sorted by ascending x-coordinate.
    lower_hull: Vec<usize>,
    /// Largest x-coordinate seen so far.
    max_x_seen: f32,
    /// True while all insertions have had non-decreasing x-coordinates.
    monotonic: bool,
}

impl Default for HullKvCache {
    fn default() -> Self {
        Self {
            entries: Vec::new(),
            upper_hull: Vec::new(),
            lower_hull: Vec::new(),
            max_x_seen: f32::NEG_INFINITY,
            monotonic: true,
        }
    }
}

impl HullKvCache {
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert a new key-value pair and maintain the convex hull.
    ///
    /// When x-coordinates are monotonically non-decreasing (the normal case
    /// for memory-write histories where x = step number): amortized O(1).
    /// For general insertion order: O(n log n) full rebuild.
    pub fn insert(&mut self, key: [f32; 2], value: &[f32]) -> usize {
        let id = self.entries.len();
        let point = Point2D {
            x: key[0],
            y: key[1],
            id,
        };
        self.entries.push(Entry {
            point,
            value: value.to_vec(),
        });

        // The fast append path requires strictly increasing x-coordinates.
        // Equal x causes collinear points (cross = 0) where the append
        // logic can't distinguish which point should stay on the hull.
        if id > 0 && key[0] <= self.max_x_seen {
            self.monotonic = false;
        }
        if key[0] > self.max_x_seen {
            self.max_x_seen = key[0];
        }

        if self.monotonic {
            append_to_lower_hull(&self.entries, &mut self.lower_hull, id);
            append_to_upper_hull(&self.entries, &mut self.upper_hull, id);
        } else {
            self.rebuild_hulls();
        }

        id
    }

    /// Find the key that maximizes `dot(query, key)` among all inserted keys.
    ///
    /// O(log h) where h is the hull size, via ternary search.
    pub fn query_argmax(&self, query: [f32; 2]) -> Result<(Point2D, &[f32])> {
        if self.entries.is_empty() {
            return Err(VmError::EmptyHull);
        }

        let best_upper = best_on_chain(&self.entries, &self.upper_hull, query);
        let best_lower = best_on_chain(&self.entries, &self.lower_hull, query);
        let upper_score = dot(query, self.entries[best_upper].point);
        let lower_score = dot(query, self.entries[best_lower].point);
        let best = if upper_score >= lower_score {
            best_upper
        } else {
            best_lower
        };

        let entry = &self.entries[best];
        Ok((entry.point, entry.value.as_slice()))
    }

    /// Query the cache according to the selected attention mode.
    ///
    /// `AverageHard` uses the convex hull argmax path. Softer modes scan the
    /// full history so they can blend values by score.
    pub fn query_value(&self, query: [f32; 2], mode: &Attention2DMode) -> Result<Vec<f32>> {
        match mode {
            Attention2DMode::AverageHard => {
                self.query_argmax(query).map(|(_, value)| value.to_vec())
            }
            Attention2DMode::HardSoftmax { temperature } => {
                self.query_weighted(query, *temperature)
            }
            Attention2DMode::Softmax => self.query_weighted(query, 1.0),
        }
    }

    /// Brute-force O(n) argmax scan for testing and comparison.
    pub fn query_argmax_bruteforce(&self, query: [f32; 2]) -> Result<(Point2D, &[f32])> {
        let best = self
            .entries
            .iter()
            .max_by(|left, right| {
                let left_score = dot(query, left.point);
                let right_score = dot(query, right.point);
                left_score
                    .partial_cmp(&right_score)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .ok_or(VmError::EmptyHull)?;
        Ok((best.point, best.value.as_slice()))
    }

    /// Number of distinct points currently on the convex hull.
    pub fn hull_size(&self) -> usize {
        let mut ids = self
            .upper_hull
            .iter()
            .chain(self.lower_hull.iter())
            .copied()
            .collect::<Vec<_>>();
        ids.sort_unstable();
        ids.dedup();
        ids.len()
    }

    /// Total number of KV pairs inserted.
    pub fn total_size(&self) -> usize {
        self.entries.len()
    }

    /// Whether all insertions so far have had non-decreasing x-coordinates.
    pub fn is_monotonic(&self) -> bool {
        self.monotonic
    }

    /// All points currently on the hull (deduplicated, sorted by id).
    pub fn hull_points(&self) -> Vec<Point2D> {
        let mut ids = self
            .upper_hull
            .iter()
            .chain(self.lower_hull.iter())
            .copied()
            .collect::<Vec<_>>();
        ids.sort_unstable();
        ids.dedup();
        ids.into_iter().map(|id| self.entries[id].point).collect()
    }

    fn rebuild_hulls(&mut self) {
        if self.entries.is_empty() {
            self.upper_hull.clear();
            self.lower_hull.clear();
            return;
        }

        let mut ordered: Vec<Point2D> = self.entries.iter().map(|e| e.point).collect();
        ordered.sort_by(|a, b| {
            a.x.partial_cmp(&b.x)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.y.partial_cmp(&b.y).unwrap_or(std::cmp::Ordering::Equal))
                .then_with(|| a.id.cmp(&b.id))
        });

        self.lower_hull = build_lower_chain(&ordered);
        self.upper_hull = build_upper_chain(&ordered);
    }

    fn query_weighted(&self, query: [f32; 2], temperature: f32) -> Result<Vec<f32>> {
        if self.entries.is_empty() {
            return Err(VmError::EmptyHull);
        }
        if !temperature.is_finite() || temperature <= 0.0 {
            return Err(VmError::InvalidConfig(format!(
                "soft attention temperature must be finite and > 0, got {temperature}"
            )));
        }

        let scores = self
            .entries
            .iter()
            .map(|entry| dot(query, entry.point) / temperature)
            .collect::<Vec<_>>();
        let max_score = scores.iter().copied().fold(f32::NEG_INFINITY, f32::max);
        let weights = scores
            .iter()
            .map(|score| (*score - max_score).exp())
            .collect::<Vec<_>>();
        let weight_sum = weights.iter().sum::<f32>();

        let mut blended = vec![0.0; self.entries[0].value.len()];
        for (entry, weight) in self.entries.iter().zip(weights.iter().copied()) {
            let normalized = weight / weight_sum;
            for (slot, value) in blended.iter_mut().zip(entry.value.iter().copied()) {
                *slot += normalized * value;
            }
        }

        Ok(blended)
    }
}

/// Append a point at the right end of the lower hull (ascending x).
/// Removes intermediate points that violate the lower-hull convexity.
fn append_to_lower_hull(entries: &[Entry], hull: &mut Vec<usize>, id: usize) {
    let point = entries[id].point;
    while hull.len() >= 2 {
        let a = entries[hull[hull.len() - 2]].point;
        let b = entries[hull[hull.len() - 1]].point;
        if cross(a, b, point) <= 0.0 {
            hull.pop();
        } else {
            break;
        }
    }
    hull.push(id);
}

/// Append a point at the right end of the upper hull (ascending x).
/// Removes intermediate points that violate the upper-hull convexity.
fn append_to_upper_hull(entries: &[Entry], hull: &mut Vec<usize>, id: usize) {
    let point = entries[id].point;
    while hull.len() >= 2 {
        let a = entries[hull[hull.len() - 2]].point;
        let b = entries[hull[hull.len() - 1]].point;
        if cross(a, b, point) >= 0.0 {
            hull.pop();
        } else {
            break;
        }
    }
    hull.push(id);
}

/// Build the lower hull chain from points sorted by ascending x.
fn build_lower_chain(points: &[Point2D]) -> Vec<usize> {
    let mut chain: Vec<Point2D> = Vec::new();
    for &point in points {
        while chain.len() >= 2 {
            let a = chain[chain.len() - 2];
            let b = chain[chain.len() - 1];
            if cross(a, b, point) <= 0.0 {
                chain.pop();
            } else {
                break;
            }
        }
        chain.push(point);
    }
    chain.into_iter().map(|p| p.id).collect()
}

/// Build the upper hull chain from points sorted by ascending x.
fn build_upper_chain(points: &[Point2D]) -> Vec<usize> {
    let mut chain: Vec<Point2D> = Vec::new();
    for &point in points {
        while chain.len() >= 2 {
            let a = chain[chain.len() - 2];
            let b = chain[chain.len() - 1];
            if cross(a, b, point) >= 0.0 {
                chain.pop();
            } else {
                break;
            }
        }
        chain.push(point);
    }
    chain.into_iter().map(|p| p.id).collect()
}

/// Ternary search on a hull chain for the point maximizing dot(query, point).
/// O(log h) where h is the chain length.
fn best_on_chain(entries: &[Entry], chain: &[usize], query: [f32; 2]) -> usize {
    match chain.len() {
        0 => unreachable!("empty chains filtered by query_argmax"),
        1 => chain[0],
        _ => {
            let mut lo = 0usize;
            let mut hi = chain.len() - 1;

            while hi.saturating_sub(lo) > 3 {
                let third = (hi - lo) / 3;
                let mid_left = lo + third;
                let mid_right = hi - third;
                let left_score = dot(query, entries[chain[mid_left]].point);
                let right_score = dot(query, entries[chain[mid_right]].point);
                if left_score <= right_score {
                    lo = mid_left;
                } else {
                    hi = mid_right;
                }
            }

            let mut best = chain[lo];
            let mut best_score = dot(query, entries[best].point);
            for &candidate in &chain[lo..=hi] {
                let score = dot(query, entries[candidate].point);
                if score > best_score {
                    best = candidate;
                    best_score = score;
                }
            }
            best
        }
    }
}

fn cross(a: Point2D, b: Point2D, c: Point2D) -> f32 {
    (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
}

fn dot(query: [f32; 2], point: Point2D) -> f32 {
    query[0] * point.x + query[1] * point.y
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cross_product_sign_determines_turn_direction() {
        let a = Point2D {
            x: 0.0,
            y: 0.0,
            id: 0,
        };
        let b = Point2D {
            x: 1.0,
            y: 0.0,
            id: 1,
        };
        let c_left = Point2D {
            x: 1.0,
            y: 1.0,
            id: 2,
        };
        let c_right = Point2D {
            x: 1.0,
            y: -1.0,
            id: 3,
        };
        let c_straight = Point2D {
            x: 2.0,
            y: 0.0,
            id: 4,
        };

        assert!(cross(a, b, c_left) > 0.0, "left turn should be positive");
        assert!(cross(a, b, c_right) < 0.0, "right turn should be negative");
        assert!(
            (cross(a, b, c_straight)).abs() < 1e-6,
            "collinear should be zero"
        );
    }

    #[test]
    fn dot_product_computes_correctly() {
        let point = Point2D {
            x: 3.0,
            y: 4.0,
            id: 0,
        };
        assert_eq!(dot([1.0, 0.0], point), 3.0);
        assert_eq!(dot([0.0, 1.0], point), 4.0);
        assert_eq!(dot([1.0, 1.0], point), 7.0);
        assert_eq!(dot([-1.0, 0.0], point), -3.0);
    }

    #[test]
    fn hull_points_returns_deduplicated_hull() {
        let mut cache = HullKvCache::new();
        // Square corners
        cache.insert([0.0, 0.0], &[0.0]);
        cache.insert([1.0, 0.0], &[1.0]);
        cache.insert([1.0, 1.0], &[2.0]);
        cache.insert([0.0, 1.0], &[3.0]);
        // Interior point (should not be on hull)
        cache.insert([0.5, 0.5], &[4.0]);

        let hull = cache.hull_points();
        assert_eq!(
            hull.len(),
            4,
            "only corners should be on hull, got {hull:?}"
        );
    }

    #[test]
    fn query_weighted_rejects_zero_temperature() {
        let mut cache = HullKvCache::new();
        cache.insert([1.0, 1.0], &[1.0]);
        let err = cache.query_weighted([1.0, 0.0], 0.0).unwrap_err();
        assert!(err.to_string().contains("temperature"));
    }

    #[test]
    fn query_weighted_rejects_negative_temperature() {
        let mut cache = HullKvCache::new();
        cache.insert([1.0, 1.0], &[1.0]);
        let err = cache.query_weighted([1.0, 0.0], -1.0).unwrap_err();
        assert!(err.to_string().contains("temperature"));
    }

    #[test]
    fn query_weighted_rejects_nan_temperature() {
        let mut cache = HullKvCache::new();
        cache.insert([1.0, 1.0], &[1.0]);
        assert!(cache.query_weighted([1.0, 0.0], f32::NAN).is_err());
    }

    #[test]
    fn query_weighted_empty_cache() {
        let cache = HullKvCache::new();
        assert!(cache.query_weighted([1.0, 0.0], 1.0).is_err());
    }

    #[test]
    fn query_value_dispatches_to_argmax_for_average_hard() {
        let mut cache = HullKvCache::new();
        cache.insert([0.0, 5.0], &[5.0]);
        cache.insert([10.0, 0.0], &[10.0]);

        let value = cache
            .query_value([1.0, 0.0], &Attention2DMode::AverageHard)
            .unwrap();
        assert_eq!(value, vec![10.0], "average-hard should return argmax point");
    }

    #[test]
    fn query_value_dispatches_to_weighted_for_softmax() {
        let mut cache = HullKvCache::new();
        cache.insert([0.0, 0.0], &[0.0]);
        cache.insert([10.0, 0.0], &[10.0]);

        let value = cache
            .query_value([1.0, 0.0], &Attention2DMode::Softmax)
            .unwrap();
        // Softmax blends, so result should be between 0 and 10
        assert!(
            value[0] > 0.0 && value[0] <= 10.0,
            "softmax value={:?}",
            value
        );
    }

    #[test]
    fn query_argmax_bruteforce_matches_for_known_points() {
        let mut cache = HullKvCache::new();
        cache.insert([1.0, 0.0], &[1.0]);
        cache.insert([0.0, 5.0], &[5.0]);
        cache.insert([-3.0, 0.0], &[-3.0]);

        // Query [0, 1] should find point with max y
        let (pt, val) = cache.query_argmax_bruteforce([0.0, 1.0]).unwrap();
        assert_eq!(pt.y, 5.0);
        assert_eq!(val, &[5.0]);
    }

    #[test]
    fn rebuild_hulls_handles_empty() {
        let mut cache = HullKvCache::new();
        cache.rebuild_hulls();
        assert!(cache.upper_hull.is_empty());
        assert!(cache.lower_hull.is_empty());
    }

    #[test]
    fn total_size_tracks_all_insertions() {
        let mut cache = HullKvCache::new();
        assert_eq!(cache.total_size(), 0);
        cache.insert([1.0, 1.0], &[1.0]);
        assert_eq!(cache.total_size(), 1);
        cache.insert([2.0, 2.0], &[2.0]);
        assert_eq!(cache.total_size(), 2);
    }

    #[test]
    fn is_monotonic_initially_true() {
        let cache = HullKvCache::new();
        assert!(cache.is_monotonic());
    }

    #[test]
    fn equal_x_breaks_monotonic() {
        let mut cache = HullKvCache::new();
        cache.insert([1.0, 0.0], &[0.0]);
        cache.insert([1.0, 1.0], &[1.0]); // equal x
        assert!(!cache.is_monotonic());
    }
}
