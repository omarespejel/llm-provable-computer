use llm_provable_computer::{Attention2DMode, HullKvCache};
use rand::{rngs::StdRng, Rng, SeedableRng};

#[test]
fn hull_query_matches_bruteforce_for_random_inputs() {
    let mut rng = StdRng::seed_from_u64(7);
    let mut cache = HullKvCache::new();

    for idx in 0..128 {
        let x = rng.gen_range(-100.0f32..100.0f32) + idx as f32 * 0.01;
        let y = rng.gen_range(-100.0f32..100.0f32);
        cache.insert([x, y], &[idx as f32]);
    }

    for _ in 0..512 {
        let query = [
            rng.gen_range(-20.0f32..20.0f32),
            rng.gen_range(-20.0f32..20.0f32),
        ];
        let (fast_point, fast_value) = cache.query_argmax(query).expect("non-empty cache");
        let (slow_point, slow_value) = cache
            .query_argmax_bruteforce(query)
            .expect("non-empty cache");

        let fast_score = query[0] * fast_point.x + query[1] * fast_point.y;
        let slow_score = query[0] * slow_point.x + query[1] * slow_point.y;

        assert!(
            (fast_score - slow_score).abs() < 1e-3,
            "query={query:?}, fast={fast_point:?}, slow={slow_point:?}"
        );
        assert_eq!(fast_value[0], slow_value[0]);
    }
}

#[test]
fn hull_size_stays_bounded_by_total_size() {
    let mut cache = HullKvCache::new();
    for idx in 0..32 {
        cache.insert([idx as f32, (idx * idx) as f32], &[idx as f32]);
        assert!(cache.hull_size() <= cache.total_size());
    }
}

#[test]
fn monotonic_insert_uses_fast_path() {
    let mut cache = HullKvCache::new();
    for i in 0..100 {
        cache.insert([i as f32, (i as f32).sin() * 50.0], &[i as f32]);
    }
    assert!(cache.is_monotonic());
    assert!(cache.hull_size() > 0);
    assert!(cache.hull_size() <= cache.total_size());
}

#[test]
fn non_monotonic_insert_falls_back_to_rebuild() {
    let mut cache = HullKvCache::new();
    cache.insert([10.0, 5.0], &[0.0]);
    cache.insert([5.0, 3.0], &[1.0]); // x decreased
    cache.insert([20.0, 7.0], &[2.0]);
    assert!(!cache.is_monotonic());

    // Queries still correct
    let (pt, _) = cache.query_argmax([1.0, 0.0]).unwrap();
    assert_eq!(pt.x, 20.0); // rightmost point for query [1, 0]
}

#[test]
fn single_point_hull() {
    let mut cache = HullKvCache::new();
    cache.insert([3.0, 4.0], &[42.0]);

    let (pt, val) = cache.query_argmax([1.0, 0.0]).unwrap();
    assert_eq!(pt.x, 3.0);
    assert_eq!(pt.y, 4.0);
    assert_eq!(val[0], 42.0);
    assert_eq!(cache.hull_size(), 1);
}

#[test]
fn two_point_hull() {
    let mut cache = HullKvCache::new();
    cache.insert([0.0, 0.0], &[0.0]);
    cache.insert([1.0, 1.0], &[1.0]);

    // Query direction [1, 0] should prefer rightmost
    let (pt, _) = cache.query_argmax([1.0, 0.0]).unwrap();
    assert_eq!(pt.x, 1.0);

    // Query direction [-1, 0] should prefer leftmost
    let (pt, _) = cache.query_argmax([-1.0, 0.0]).unwrap();
    assert_eq!(pt.x, 0.0);
}

#[test]
fn collinear_points_handled() {
    let mut cache = HullKvCache::new();
    // All points on y = x line
    for i in 0..10 {
        cache.insert([i as f32, i as f32], &[i as f32]);
    }

    // Query [1, 0] should find rightmost
    let (pt, _) = cache.query_argmax([1.0, 0.0]).unwrap();
    assert_eq!(pt.x, 9.0);

    // Query [-1, -1] should find leftmost (origin)
    let (pt, _) = cache.query_argmax([-1.0, -1.0]).unwrap();
    assert_eq!(pt.x, 0.0);
}

#[test]
fn empty_hull_returns_error() {
    let cache = HullKvCache::new();
    assert!(cache.query_argmax([1.0, 0.0]).is_err());
}

#[test]
fn duplicate_x_coordinates_handled() {
    let mut cache = HullKvCache::new();
    cache.insert([1.0, 0.0], &[0.0]);
    cache.insert([1.0, 5.0], &[1.0]);
    cache.insert([1.0, -3.0], &[2.0]);

    // Query [0, 1] should find highest y
    let (pt, _) = cache.query_argmax([0.0, 1.0]).unwrap();
    assert_eq!(pt.y, 5.0);

    // Query [0, -1] should find lowest y
    let (pt, _) = cache.query_argmax([0.0, -1.0]).unwrap();
    assert_eq!(pt.y, -3.0);
}

#[test]
fn large_monotonic_insert_stays_correct() {
    let mut rng = StdRng::seed_from_u64(123);
    let mut cache = HullKvCache::new();

    for i in 0..10_000 {
        let y = rng.gen_range(-10_000.0f32..10_000.0f32);
        cache.insert([i as f32, y], &[y]);
    }

    assert!(cache.is_monotonic());

    // Verify 100 random queries against brute force
    for _ in 0..100 {
        let query = [
            rng.gen_range(-10.0f32..10.0f32),
            rng.gen_range(-10.0f32..10.0f32),
        ];
        let (fast_pt, _) = cache.query_argmax(query).unwrap();
        let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

        let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
        let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

        assert!(
            (fast_score - slow_score).abs() < 1e-1,
            "query={query:?}, fast_score={fast_score}, slow_score={slow_score}, diff={}",
            (fast_score - slow_score).abs()
        );
    }
}

#[test]
fn memory_pattern_latest_write_wins() {
    // Simulate the actual memory-write pattern used by AddressedMemory:
    // x = step number (monotonic), y = stored value, query = [1, 0] (latest write)
    let mut cache = HullKvCache::new();
    cache.insert([0.0, 10.0], &[10.0]); // step 0: write 10
    cache.insert([3.0, 42.0], &[42.0]); // step 3: write 42
    cache.insert([7.0, 99.0], &[99.0]); // step 7: write 99

    // Query [1, 0] should return the latest write (highest step = highest x)
    let (pt, val) = cache.query_argmax([1.0, 0.0]).unwrap();
    assert_eq!(pt.x, 7.0);
    assert_eq!(val[0], 99.0);
}

#[test]
fn softmax_query_blends_values_by_recency() {
    let mut cache = HullKvCache::new();
    cache.insert([0.0, 0.0], &[0.0]);
    cache.insert([2.0, 0.0], &[0.0]);
    cache.insert([4.0, 10.0], &[10.0]);

    let value = cache
        .query_value([1.0, 0.0], &Attention2DMode::Softmax)
        .unwrap();

    assert!(
        (value[0] - 8.668_133).abs() < 1e-4,
        "softmax value={value:?}"
    );
}

#[test]
fn hard_softmax_temperature_controls_sharpness() {
    let mut cache = HullKvCache::new();
    cache.insert([0.0, 0.0], &[0.0]);
    cache.insert([2.0, 0.0], &[0.0]);
    cache.insert([4.0, 10.0], &[10.0]);

    let sharp = cache
        .query_value(
            [1.0, 0.0],
            &Attention2DMode::HardSoftmax { temperature: 0.5 },
        )
        .unwrap();
    let smooth = cache
        .query_value(
            [1.0, 0.0],
            &Attention2DMode::HardSoftmax { temperature: 10.0 },
        )
        .unwrap();

    assert!(sharp[0] > smooth[0], "sharp={sharp:?} smooth={smooth:?}");
    assert!(smooth[0] > 0.0, "expected blending, got {smooth:?}");
}
