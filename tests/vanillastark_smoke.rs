use llm_provable_computer::vanillastark::{FieldElement, RescuePrime, Stark};

#[test]
fn vanillastark_round_trip_proof_verifies() {
    let rescue_prime = RescuePrime::new();
    let input = FieldElement::sample(b"0xdeadbeef");
    let output = rescue_prime.hash(input);

    let stark = Stark::new(4, 2, 2, rescue_prime.m, rescue_prime.n + 1, 2);
    let trace = rescue_prime.trace(input);
    let air = rescue_prime.transition_constraints(stark.omicron);
    let boundary = rescue_prime.boundary_constraints(output);
    let proof = stark.prove(&trace, &air, &boundary);

    assert!(stark.verify(&proof, &air, &boundary));
}
