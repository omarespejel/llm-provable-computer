use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion};
use llm_provable_computer::HullKvCache;
use rand::{rngs::StdRng, Rng, SeedableRng};

fn bench_query_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("hull_query_vs_bruteforce");

    for size in [100, 500, 1_000, 5_000, 10_000] {
        let mut rng = StdRng::seed_from_u64(42);
        let mut cache = HullKvCache::new();

        for i in 0..size {
            let y = rng.gen_range(-1000.0f32..1000.0f32);
            cache.insert([i as f32, y], &[y]);
        }

        let queries: Vec<[f32; 2]> = (0..100)
            .map(|_| {
                [
                    rng.gen_range(-10.0f32..10.0f32),
                    rng.gen_range(-10.0f32..10.0f32),
                ]
            })
            .collect();

        group.bench_with_input(BenchmarkId::new("hull_argmax", size), &size, |b, _| {
            let mut idx = 0;
            b.iter(|| {
                let q = queries[idx % queries.len()];
                idx += 1;
                black_box(cache.query_argmax(q).unwrap())
            });
        });

        group.bench_with_input(
            BenchmarkId::new("bruteforce_argmax", size),
            &size,
            |b, _| {
                let mut idx = 0;
                b.iter(|| {
                    let q = queries[idx % queries.len()];
                    idx += 1;
                    black_box(cache.query_argmax_bruteforce(q).unwrap())
                });
            },
        );
    }

    group.finish();
}

fn bench_monotonic_insert(c: &mut Criterion) {
    let mut group = c.benchmark_group("hull_monotonic_insert");

    for size in [100, 1_000, 10_000] {
        group.bench_with_input(BenchmarkId::new("incremental", size), &size, |b, &size| {
            b.iter(|| {
                let mut rng = StdRng::seed_from_u64(42);
                let mut cache = HullKvCache::new();
                for i in 0..size {
                    let y = rng.gen_range(-1000.0f32..1000.0f32);
                    cache.insert([i as f32, y], &[y]);
                }
                black_box(cache.total_size())
            });
        });
    }

    group.finish();
}

fn bench_insert_then_query(c: &mut Criterion) {
    let mut group = c.benchmark_group("hull_insert_then_query");

    for size in [100, 1_000, 10_000] {
        group.bench_with_input(
            BenchmarkId::new("full_pipeline", size),
            &size,
            |b, &size| {
                b.iter(|| {
                    let mut rng = StdRng::seed_from_u64(42);
                    let mut cache = HullKvCache::new();
                    for i in 0..size {
                        let y = rng.gen_range(-1000.0f32..1000.0f32);
                        cache.insert([i as f32, y], &[y]);
                    }
                    // 100 queries after building
                    for _ in 0..100 {
                        let q = [
                            rng.gen_range(-10.0f32..10.0f32),
                            rng.gen_range(-10.0f32..10.0f32),
                        ];
                        black_box(cache.query_argmax(q).unwrap());
                    }
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_query_scaling,
    bench_monotonic_insert,
    bench_insert_then_query
);
criterion_main!(benches);
