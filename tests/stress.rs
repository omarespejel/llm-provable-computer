//! Stress tests: large scale execution and hull operations.

use llm_provable_computer::{
    verify_model_against_native, Attention2DMode, ExecutionRuntime, HullKvCache, ProgramCompiler,
    TransformerVmConfig,
};
use rand::{rngs::StdRng, Rng, SeedableRng};

// --- Hull stress tests ---

#[test]
fn stress_hull_100k_monotonic_inserts_stays_correct() {
    let mut rng = StdRng::seed_from_u64(42);
    let mut cache = HullKvCache::new();

    for i in 0..100_000 {
        let y = rng.gen_range(-10_000.0f32..10_000.0f32);
        cache.insert([i as f32, y], &[y]);
    }

    assert!(cache.is_monotonic());
    assert!(cache.hull_size() <= cache.total_size());
    assert!(
        cache.hull_size() < 100_000,
        "hull should be much smaller than total: hull={}, total={}",
        cache.hull_size(),
        cache.total_size()
    );

    // Verify 200 random queries match brute force
    let mut mismatches = 0;
    for _ in 0..200 {
        let query = [
            rng.gen_range(-10.0f32..10.0f32),
            rng.gen_range(-10.0f32..10.0f32),
        ];
        let (fast_pt, _) = cache.query_argmax(query).unwrap();
        let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

        let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
        let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

        if (fast_score - slow_score).abs() > 1e-1 {
            mismatches += 1;
        }
    }
    assert_eq!(mismatches, 0, "all queries should match brute force");
}

#[test]
fn stress_hull_random_inserts_stays_correct() {
    let mut rng = StdRng::seed_from_u64(777);
    let mut cache = HullKvCache::new();

    // Non-monotonic inserts trigger O(n log n) rebuilds, so keep size reasonable
    for _ in 0..2_000 {
        let x = rng.gen_range(-1000.0f32..1000.0f32);
        let y = rng.gen_range(-1000.0f32..1000.0f32);
        cache.insert([x, y], &[x + y]);
    }

    assert!(!cache.is_monotonic());
    assert!(cache.hull_size() <= cache.total_size());

    // Verify 100 random queries
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
            (fast_score - slow_score).abs() < 1.0,
            "query={query:?}, fast_score={fast_score}, slow_score={slow_score}"
        );
    }
}

#[test]
fn stress_hull_1m_monotonic_inserts() {
    let mut rng = StdRng::seed_from_u64(1_000_000);
    let mut cache = HullKvCache::new();

    for i in 0..1_000_000 {
        let y = rng.gen_range(-10_000.0f32..10_000.0f32);
        cache.insert([i as f32, y], &[y]);
    }

    assert!(cache.is_monotonic());
    assert_eq!(cache.total_size(), 1_000_000);
    assert!(cache.hull_size() <= cache.total_size());

    // Verify 50 random queries match brute force
    for _ in 0..50 {
        let query = [
            rng.gen_range(-10.0f32..10.0f32),
            rng.gen_range(-10.0f32..10.0f32),
        ];
        let (fast_pt, _) = cache.query_argmax(query).unwrap();
        let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

        let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
        let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

        assert!(
            (fast_score - slow_score).abs() < 1.0,
            "query={query:?}, fast_score={fast_score}, slow_score={slow_score}"
        );
    }
}

#[test]
fn stress_hull_many_duplicate_x_coordinates() {
    let mut cache = HullKvCache::new();
    // Insert 1000 points, all at x=5.0 with varying y
    for i in 0..1000 {
        cache.insert([5.0, i as f32 - 500.0], &[i as f32]);
    }

    // Query [0, 1] should find max y = 499
    let (pt, _) = cache.query_argmax([0.0, 1.0]).unwrap();
    assert_eq!(pt.y, 499.0);

    // Query [0, -1] should find min y = -500
    let (pt, _) = cache.query_argmax([0.0, -1.0]).unwrap();
    assert_eq!(pt.y, -500.0);
}

// --- Long execution tests ---

#[test]
fn stress_long_execution_counter_10k_steps() {
    // Count from 0 to 2000 to guarantee 10,000+ execution steps.
    // Each iteration: LOAD + ADD + STORE + LOAD + SUBM + JZ + JMP = 7 steps
    // 2000 iterations * 7 + 4 (setup + teardown) = 14,004 steps
    let source = r#"
        .memory 4
        .init 1 2000

        LOADI 0
        STORE 0
    loop:
        LOAD 0
        ADD 1
        STORE 0
        LOAD 0
        SUBM 1
        JZ done
        JMP loop
    done:
        LOAD 0
        HALT
    "#;
    let config = TransformerVmConfig {
        num_layers: 2,
        ..TransformerVmConfig::default()
    };
    let model = ProgramCompiler
        .compile_source(source, config)
        .expect("compile");
    let comparison = verify_model_against_native(model, 20_000).expect("verify");

    assert!(comparison.transformer.halted);
    assert_eq!(comparison.transformer.final_state.acc, 2000);
    assert!(
        comparison.checked_steps > 10_000,
        "expected 10K+ steps, got {}",
        comparison.checked_steps
    );
    assert_eq!(
        comparison.transformer.final_state, comparison.native.final_state,
        "no drift after 10K+ step execution"
    );
}

#[test]
fn stress_long_execution_fibonacci_large() {
    // Compute Fibonacci(15) = 610
    let source = r#"
        .memory 5
        .init 0 0
        .init 1 1
        .init 3 0
        .init 4 14

    loop:
        LOAD 3
        SUBM 4
        JZ done
        LOAD 0
        ADDM 1
        STORE 2
        LOAD 1
        STORE 0
        LOAD 2
        STORE 1
        LOAD 3
        ADD 1
        STORE 3
        JMP loop
    done:
        LOAD 1
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let comparison = verify_model_against_native(model, 1000).expect("verify");

    assert!(comparison.transformer.halted);
    assert_eq!(
        comparison.transformer.final_state.acc, 610,
        "Fibonacci(15) = 610"
    );
}

#[test]
fn stress_repeated_memory_write_read_cycles() {
    // Write and read the same address many times
    let source = r#"
        .memory 2
        .init 1 100

        LOADI 0
        STORE 0
    loop:
        LOAD 0
        ADD 1
        STORE 0
        LOAD 0
        SUBM 1
        JZ done
        JMP loop
    done:
        LOAD 0
        HALT
    "#;
    let model = ProgramCompiler
        .compile_source(source, TransformerVmConfig::default())
        .expect("compile");
    let comparison = verify_model_against_native(model, 5000).expect("verify");

    assert!(comparison.transformer.halted);
    assert_eq!(comparison.transformer.final_state.acc, 100);
    assert_eq!(
        comparison.transformer.final_state,
        comparison.native.final_state
    );
}

// --- Multi-layer stress ---

#[test]
fn stress_multi_layer_4_fibonacci() {
    let source = std::fs::read_to_string("programs/fibonacci.tvm").expect("fixture");
    let config = TransformerVmConfig {
        num_layers: 4,
        ..TransformerVmConfig::default()
    };
    let model = ProgramCompiler
        .compile_source(&source, config)
        .expect("compile");
    let comparison = verify_model_against_native(model, 512).expect("verify");

    assert!(comparison.transformer.halted);
    assert_eq!(comparison.transformer.final_state.acc, 21);
}

// --- Soft attention stress ---

#[test]
fn stress_soft_attention_multiple_memory_writes() {
    // Write to the same address 50 times, then read with soft attention
    let mut lines = vec![".memory 2".to_string(), "LOADI 0".to_string()];

    // Write values 1..=50 to address 0
    for i in 1..=50 {
        lines.push(format!("LOADI {i}"));
        lines.push("STORE 0".to_string());
    }
    lines.push("LOAD 0".to_string());
    lines.push("HALT".to_string());

    let source = lines.join("\n");

    // With average-hard, should read 50 (latest write)
    let model = ProgramCompiler
        .compile_source(
            &source,
            TransformerVmConfig {
                attention_mode: Attention2DMode::AverageHard,
                ..TransformerVmConfig::default()
            },
        )
        .expect("compile");
    let comparison = verify_model_against_native(model, 200).expect("verify");
    assert_eq!(comparison.transformer.final_state.acc, 50);

    // With softmax, should read a blended value < 50
    let model = ProgramCompiler
        .compile_source(
            &source,
            TransformerVmConfig {
                attention_mode: Attention2DMode::Softmax,
                ..TransformerVmConfig::default()
            },
        )
        .expect("compile");
    let comparison = verify_model_against_native(model, 200).expect("verify");
    let blended = comparison.transformer.final_state.acc;
    assert!(blended > 0, "blended should be positive, got {blended}");
    assert!(
        blended <= 50,
        "blended should be <= max write, got {blended}"
    );
}

// --- Throughput sanity check ---

#[test]
fn stress_throughput_is_nonzero() {
    let source = std::fs::read_to_string("programs/fibonacci.tvm").expect("fixture");
    let model = ProgramCompiler
        .compile_source(&source, TransformerVmConfig::default())
        .expect("compile");
    let mut runtime = ExecutionRuntime::new(model, 512);
    let result = runtime.run().expect("run");

    // Throughput should be positive if execution took time
    if result.elapsed.as_nanos() > 0 {
        assert!(
            result.tokens_per_sec > 0.0,
            "tokens/sec should be positive, got {}",
            result.tokens_per_sec
        );
    }
}
