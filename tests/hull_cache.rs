use rand::{rngs::StdRng, Rng, SeedableRng};
use transformer_vm_rs::HullKvCache;

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
