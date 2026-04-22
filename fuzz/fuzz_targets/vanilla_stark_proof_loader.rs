#![no_main]

//! Adversarial-input coverage for the vanilla STARK proof JSON path.
//!
//! Targets the loader + every public verification entry point in
//! `proof.rs` so that no malformed claim, tampered proof bytes, or
//! claim-drift mutation can panic the verifier or escape the
//! statement-v1 metadata invariants. Verifier results are deliberately
//! discarded; the contract being fuzzed is panic-freedom and bounded
//! resource use, not soundness of valid proofs.

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::proof::{
    production_v1_verification_policy, publication_v1_security_floor_policy,
    VanillaStarkExecutionProof,
};
use llm_provable_computer::{
    verify_execution_stark, verify_execution_stark_claim_only,
    verify_execution_stark_claim_only_with_policy, verify_execution_stark_with_backend_and_policy,
    verify_execution_stark_with_policy,
    verify_execution_stark_with_reexecution, verify_execution_stark_with_reexecution_and_policy,
};

const MAX_INPUT_BYTES: usize = 8 * 1024 * 1024;

fuzz_target!(|data: &[u8]| {
    if data.len() > MAX_INPUT_BYTES {
        return;
    }

    let Ok(proof) = serde_json::from_slice::<VanillaStarkExecutionProof>(data) else {
        return;
    };

    // Bound trace length so we never let a malformed claim push the
    // verifier into a multi-minute proving-domain construction.
    if proof.claim.steps > 4096 {
        return;
    }
    if proof.claim.options.expansion_factor > 64
        || proof.claim.options.num_colinearity_checks > 64
        || proof.claim.options.security_level > 128
    {
        return;
    }

    let _ = verify_execution_stark(&proof);
    let _ = verify_execution_stark_claim_only(&proof);
    let _ = verify_execution_stark_with_policy(&proof, production_v1_verification_policy());
    let _ = verify_execution_stark_claim_only_with_policy(
        &proof,
        production_v1_verification_policy(),
    );
    let _ = verify_execution_stark_with_backend_and_policy(
        &proof,
        proof.proof_backend,
        production_v1_verification_policy(),
    );
    let _ = verify_execution_stark_with_reexecution(&proof);
    let _ = verify_execution_stark_with_reexecution_and_policy(
        &proof,
        publication_v1_security_floor_policy(),
    );
});
