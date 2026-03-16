use proptest::prelude::*;
use transformer_vm_rs::{decode_state, encode_state, HullKvCache, MachineState};

proptest! {
    #[test]
    fn state_round_trips_for_all_valid_fields(
        pc in 0u8..=255u8,
        acc in i16::MIN..=i16::MAX,
        sp in 0u8..=255u8,
        zero_flag in any::<bool>(),
        carry_flag in any::<bool>(),
        halted in any::<bool>(),
    ) {
        let state = MachineState {
            pc,
            acc,
            sp,
            zero_flag,
            carry_flag,
            halted,
            memory: vec![0; 4],
        };
        let token = encode_state(&state, 36).unwrap();
        let decoded = decode_state(&token, state.memory.clone()).unwrap();
        prop_assert_eq!(decoded, state);
    }

    #[test]
    fn hull_argmax_matches_bruteforce_random(
        points in prop::collection::vec(
            (-100.0f32..100.0f32, -100.0f32..100.0f32),
            2..64,
        ),
        queries in prop::collection::vec(
            (-10.0f32..10.0f32, -10.0f32..10.0f32),
            1..16,
        ),
    ) {
        let mut cache = HullKvCache::new();
        for (i, &(x, y)) in points.iter().enumerate() {
            // Add small offset to avoid exact duplicate x values
            cache.insert([x + i as f32 * 0.001, y], &[i as f32]);
        }

        for &(qx, qy) in &queries {
            let query = [qx, qy];
            let (fast_pt, _) = cache.query_argmax(query).unwrap();
            let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

            let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
            let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

            prop_assert!(
                (fast_score - slow_score).abs() < 1e-2,
                "query={query:?}, fast_score={fast_score}, slow_score={slow_score}"
            );
        }
    }

    #[test]
    fn hull_argmax_matches_bruteforce_monotonic(
        values in prop::collection::vec(-1000.0f32..1000.0f32, 2..128),
        queries in prop::collection::vec(
            (-10.0f32..10.0f32, -10.0f32..10.0f32),
            1..16,
        ),
    ) {
        let mut cache = HullKvCache::new();
        for (i, &y) in values.iter().enumerate() {
            cache.insert([i as f32, y], &[y]);
        }

        prop_assert!(cache.is_monotonic());

        for &(qx, qy) in &queries {
            let query = [qx, qy];
            let (fast_pt, _) = cache.query_argmax(query).unwrap();
            let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

            let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
            let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

            prop_assert!(
                (fast_score - slow_score).abs() < 1e-2,
                "query={query:?}, fast_score={fast_score}, slow_score={slow_score}"
            );
        }
    }

    #[test]
    fn hull_size_bounded_by_total(
        insertions in prop::collection::vec(
            (-50.0f32..50.0f32, -50.0f32..50.0f32),
            1..100,
        ),
    ) {
        let mut cache = HullKvCache::new();
        for (i, &(x, y)) in insertions.iter().enumerate() {
            cache.insert([x, y], &[i as f32]);
            prop_assert!(cache.hull_size() <= cache.total_size());
        }
    }

    #[test]
    fn monotonic_insert_preserves_flag(
        values in prop::collection::vec(-1000.0f32..1000.0f32, 1..200),
    ) {
        let mut cache = HullKvCache::new();
        for (i, &y) in values.iter().enumerate() {
            cache.insert([i as f32, y], &[y]);
        }
        prop_assert!(cache.is_monotonic());
    }

    #[test]
    fn non_monotonic_insert_clears_flag(
        values in prop::collection::vec(-100.0f32..100.0f32, 3..50),
    ) {
        let mut cache = HullKvCache::new();
        // Insert in reverse order to guarantee non-monotonic
        for (i, &y) in values.iter().enumerate() {
            let x = (values.len() - i) as f32;
            cache.insert([x, y], &[y]);
        }
        // With 3+ values in reverse x order, monotonic must be false
        prop_assert!(!cache.is_monotonic());

        // But queries should still be correct
        for &y in &values {
            let query = [1.0, y.signum()];
            let (fast_pt, _) = cache.query_argmax(query).unwrap();
            let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

            let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
            let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

            prop_assert!(
                (fast_score - slow_score).abs() < 1e-2,
                "query={query:?}, fast_score={fast_score}, slow_score={slow_score}"
            );
        }
    }
}
