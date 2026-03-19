use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
use llm_provable_computer::vanillastark::{FieldElement, MPolynomial, RescuePrime, Stark};

/// Shared setup: build the Stark instance, trace, AIR, and boundary once.
struct StarkFixture {
    stark: Stark,
    trace: Vec<Vec<FieldElement>>,
    air: Vec<MPolynomial>,
    boundary: Vec<(usize, usize, FieldElement)>,
}

fn setup_fixture() -> StarkFixture {
    let rp = RescuePrime::new();
    let input = FieldElement::sample(b"0xdeadbeef");
    let output = rp.hash(input);

    let expansion_factor = 4;
    let num_colinearity_checks = 2;
    let security_level = 2;
    let num_cycles = rp.n + 1;
    let state_width = rp.m;

    let stark = Stark::new(
        expansion_factor,
        num_colinearity_checks,
        security_level,
        state_width,
        num_cycles,
        2,
    );

    let trace = rp.trace(input);
    let air = rp.transition_constraints(stark.omicron);
    let boundary = rp.boundary_constraints(output);

    StarkFixture {
        stark,
        trace,
        air,
        boundary,
    }
}

fn bench_rescue_prime_hash(c: &mut Criterion) {
    let rp = RescuePrime::new();
    let input = FieldElement::sample(b"0xdeadbeef");

    c.bench_function("rescue_prime_hash", |b| b.iter(|| rp.hash(input)));
}

fn bench_rescue_prime_trace(c: &mut Criterion) {
    let rp = RescuePrime::new();
    let input = FieldElement::sample(b"0xdeadbeef");

    c.bench_function("rescue_prime_trace", |b| b.iter(|| rp.trace(input)));
}

fn bench_transition_constraints(c: &mut Criterion) {
    let rp = RescuePrime::new();
    let stark = Stark::new(4, 2, 2, rp.m, rp.n + 1, 2);

    c.bench_function("transition_constraints", |b| {
        b.iter(|| rp.transition_constraints(stark.omicron))
    });
}

fn bench_stark_prove(c: &mut Criterion) {
    let fixture = setup_fixture();

    c.bench_function("stark_prove", |b| {
        b.iter(|| {
            fixture
                .stark
                .prove(&fixture.trace, &fixture.air, &fixture.boundary)
        })
    });
}

fn bench_stark_verify(c: &mut Criterion) {
    let fixture = setup_fixture();
    let proof = fixture
        .stark
        .prove(&fixture.trace, &fixture.air, &fixture.boundary);

    c.bench_function("stark_verify", |b| {
        b.iter(|| {
            fixture
                .stark
                .verify(&proof, &fixture.air, &fixture.boundary)
        })
    });
}

fn bench_stark_e2e(c: &mut Criterion) {
    let fixture = setup_fixture();

    c.bench_function("stark_e2e", |b| {
        b.iter(|| {
            let proof = fixture
                .stark
                .prove(&fixture.trace, &fixture.air, &fixture.boundary);
            let verdict = fixture
                .stark
                .verify(&proof, &fixture.air, &fixture.boundary);
            assert!(verdict);
        })
    });
}

fn bench_stark_proof_size(c: &mut Criterion) {
    let fixture = setup_fixture();

    c.bench_function("stark_proof_size", |b| {
        b.iter(|| {
            let proof = fixture
                .stark
                .prove(&fixture.trace, &fixture.air, &fixture.boundary);
            proof.len()
        })
    });
}

fn bench_field_ops(c: &mut Criterion) {
    let a = FieldElement::new(85408008396924667383611388730472331217);
    let b = FieldElement::new(174420698556543096520990950387834928928);

    let mut group = c.benchmark_group("field_ops");
    group.bench_function("add", |bench| bench.iter(|| a + b));
    group.bench_function("mul", |bench| bench.iter(|| a * b));
    group.bench_function("inv", |bench| bench.iter(|| a.inverse()));
    group.bench_function("pow_small", |bench| bench.iter(|| a.pow(3)));
    group.bench_function("pow_large", |bench| bench.iter(|| a.pow(b.value())));
    group.finish();
}

fn bench_polynomial_ops(c: &mut Criterion) {
    use llm_provable_computer::vanillastark::Polynomial;

    let coeffs: Vec<FieldElement> = (0..64).map(|i| FieldElement::new(i + 1)).collect();
    let poly = Polynomial::new(coeffs);
    let point = FieldElement::new(42);

    let mut group = c.benchmark_group("polynomial_ops");
    group.bench_function("evaluate_deg63", |b| b.iter(|| poly.evaluate(point)));

    let domain: Vec<FieldElement> = (0..8).map(|i| FieldElement::new(i + 1)).collect();
    let values: Vec<FieldElement> = (0..8).map(|i| FieldElement::new(i * 7 + 3)).collect();
    group.bench_function("interpolate_8pts", |b| {
        b.iter(|| Polynomial::interpolate_domain(&domain, &values))
    });
    group.finish();
}

fn bench_fri(c: &mut Criterion) {
    use llm_provable_computer::vanillastark::{Fri, Polynomial, ProofStream};

    let degree = 63;
    let expansion_factor = 4;
    let num_colinearity_tests = 17;
    let codeword_length = (degree + 1) * expansion_factor;

    let omega = FieldElement::primitive_nth_root(codeword_length as u128);
    let generator = FieldElement::generator();
    let fri = Fri::new(
        generator,
        omega,
        codeword_length,
        expansion_factor,
        num_colinearity_tests,
    );

    let polynomial = Polynomial::new((0..=degree).map(|i| FieldElement::new(i as u128)).collect());
    let domain: Vec<FieldElement> = (0..codeword_length).map(|i| omega.pow(i as u128)).collect();
    let codeword = polynomial.evaluate_domain(&domain);

    let mut group = c.benchmark_group("fri");

    group.bench_function("prove_deg63", |b| {
        b.iter(|| {
            let mut ps = ProofStream::new();
            fri.prove(&codeword, &mut ps);
        })
    });

    // Pre-generate proof for verify bench
    let mut ps = ProofStream::new();
    fri.prove(&codeword, &mut ps);
    let verify_ps = ps.clone();

    group.bench_function("verify_deg63", |b| {
        b.iter(|| {
            let mut ps = verify_ps.clone();
            ps.read_index = 0;
            let mut points = Vec::new();
            fri.verify(&mut ps, &mut points);
        })
    });

    group.finish();
}

fn bench_scaling(c: &mut Criterion) {
    let rp = RescuePrime::new();
    let input = FieldElement::sample(b"0xdeadbeef");
    let output = rp.hash(input);
    let trace = rp.trace(input);
    let num_cycles = rp.n + 1;
    let state_width = rp.m;

    let mut group = c.benchmark_group("scaling");

    for &checks in &[2, 4] {
        let security_level = 2 * checks;
        let stark = Stark::new(4, checks, security_level, state_width, num_cycles, 2);
        let air = rp.transition_constraints(stark.omicron);
        let boundary = rp.boundary_constraints(output);

        group.bench_with_input(
            BenchmarkId::new("prove", format!("checks={}", checks)),
            &checks,
            |b, _| b.iter(|| stark.prove(&trace, &air, &boundary)),
        );

        let proof = stark.prove(&trace, &air, &boundary);
        group.bench_with_input(
            BenchmarkId::new("verify", format!("checks={}", checks)),
            &checks,
            |b, _| b.iter(|| stark.verify(&proof, &air, &boundary)),
        );
    }

    group.finish();
}

criterion_group! {
    name = field_benches;
    config = Criterion::default().sample_size(100);
    targets = bench_field_ops
}

criterion_group! {
    name = polynomial_benches;
    config = Criterion::default().sample_size(50);
    targets = bench_polynomial_ops
}

criterion_group! {
    name = hash_benches;
    config = Criterion::default().sample_size(50);
    targets = bench_rescue_prime_hash, bench_rescue_prime_trace, bench_transition_constraints
}

criterion_group! {
    name = fri_benches;
    config = Criterion::default().sample_size(10);
    targets = bench_fri
}

criterion_group! {
    name = stark_benches;
    config = Criterion::default().sample_size(10);
    targets = bench_stark_prove, bench_stark_verify, bench_stark_e2e, bench_stark_proof_size
}

criterion_group! {
    name = scaling_benches;
    config = Criterion::default().sample_size(10);
    targets = bench_scaling
}

criterion_main!(
    field_benches,
    polynomial_benches,
    hash_benches,
    fri_benches,
    stark_benches,
    scaling_benches,
);
