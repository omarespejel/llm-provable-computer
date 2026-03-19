use llm_provable_computer::vanillastark::{FieldElement, RescuePrime, Stark};

fn main() {
    println!("VanillaSTARK — Rust STARK prover/verifier");
    println!("==========================================");

    let rp = RescuePrime::new();
    let input = FieldElement::sample(b"0xdeadbeef");
    let output = rp.hash(input);
    println!("Rescue-Prime hash({}) = {}", input, output);

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

    println!("Generating STARK proof...");
    let trace = rp.trace(input);
    let air = rp.transition_constraints(stark.omicron);
    let boundary = rp.boundary_constraints(output);
    let proof = stark.prove(&trace, &air, &boundary);
    println!("Proof size: {} bytes", proof.len());

    println!("Verifying...");
    let verdict = stark.verify(&proof, &air, &boundary);
    println!("Verdict: {}", if verdict { "ACCEPT" } else { "REJECT" });
}
