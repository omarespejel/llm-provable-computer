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

#[derive(Debug, Clone, Default)]
pub struct HullKvCache {
    entries: Vec<Entry>,
    upper_hull: Vec<usize>,
    lower_hull: Vec<usize>,
}

impl HullKvCache {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, key: [f32; 2], value: &[f32]) -> usize {
        let id = self.entries.len();
        self.entries.push(Entry {
            point: Point2D {
                x: key[0],
                y: key[1],
                id,
            },
            value: value.to_vec(),
        });
        self.rebuild_hulls();
        id
    }

    pub fn query_argmax(&self, query: [f32; 2]) -> Result<(Point2D, &[f32])> {
        if self.entries.is_empty() {
            return Err(VmError::EmptyHull);
        }

        let best_upper = self.best_on_chain(&self.upper_hull, query);
        let best_lower = self.best_on_chain(&self.lower_hull, query);
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

    pub fn total_size(&self) -> usize {
        self.entries.len()
    }

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

        let mut ordered = self
            .entries
            .iter()
            .map(|entry| entry.point)
            .collect::<Vec<_>>();
        ordered.sort_by(|left, right| {
            left.x
                .partial_cmp(&right.x)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| {
                    left.y
                        .partial_cmp(&right.y)
                        .unwrap_or(std::cmp::Ordering::Equal)
                })
                .then_with(|| left.id.cmp(&right.id))
        });

        self.lower_hull = build_chain(&ordered);
        ordered.reverse();
        self.upper_hull = build_chain(&ordered);
    }

    fn best_on_chain(&self, chain: &[usize], query: [f32; 2]) -> usize {
        match chain.len() {
            0 => unreachable!("empty chains are filtered by query_argmax"),
            1 => chain[0],
            _ => {
                let mut lo = 0usize;
                let mut hi = chain.len() - 1;

                while hi.saturating_sub(lo) > 3 {
                    let third = (hi - lo) / 3;
                    let mid_left = lo + third;
                    let mid_right = hi - third;
                    let left_score = dot(query, self.entries[chain[mid_left]].point);
                    let right_score = dot(query, self.entries[chain[mid_right]].point);
                    if left_score <= right_score {
                        lo = mid_left;
                    } else {
                        hi = mid_right;
                    }
                }

                let mut best = chain[lo];
                let mut best_score = dot(query, self.entries[best].point);
                for candidate in chain.iter().take(hi + 1).skip(lo).copied() {
                    let score = dot(query, self.entries[candidate].point);
                    if score > best_score {
                        best = candidate;
                        best_score = score;
                    }
                }
                best
            }
        }
    }
}

fn build_chain(points: &[Point2D]) -> Vec<usize> {
    let mut chain: Vec<Point2D> = Vec::new();
    for point in points {
        while chain.len() >= 2 {
            let second = chain[chain.len() - 1];
            let first = chain[chain.len() - 2];
            if cross(first, second, *point) <= 0.0 {
                chain.pop();
            } else {
                break;
            }
        }
        chain.push(*point);
    }
    chain.into_iter().map(|point| point.id).collect()
}

fn cross(a: Point2D, b: Point2D, c: Point2D) -> f32 {
    (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
}

fn dot(query: [f32; 2], point: Point2D) -> f32 {
    query[0] * point.x + query[1] * point.y
}
