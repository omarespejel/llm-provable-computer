#![cfg(feature = "stwo-backend")]

use llm_provable_computer::stwo_backend::parse_phase30_decoding_step_proof_envelope_manifest_json;
use llm_provable_computer::{
    commit_phase29_recursive_compression_input_contract,
    commit_phase31_recursive_compression_decode_boundary_manifest,
    commit_phase32_recursive_compression_statement_contract,
    commit_phase33_recursive_compression_public_input_manifest,
    commit_phase34_recursive_compression_shared_lookup_manifest,
    commit_phase35_recursive_compression_target_manifest,
    commit_phase36_recursive_verifier_harness_receipt,
    commit_phase37_recursive_artifact_chain_harness_receipt,
    parse_phase29_recursive_compression_input_contract_json,
    parse_phase36_recursive_verifier_harness_receipt_json,
    parse_phase37_recursive_artifact_chain_harness_receipt_json, phase12_default_decoding_layout,
    phase30_prepare_decoding_step_proof_envelope_manifest,
    phase31_prepare_recursive_compression_decode_boundary_manifest,
    phase32_prepare_recursive_compression_statement_contract,
    phase33_prepare_recursive_compression_public_input_manifest,
    phase34_prepare_recursive_compression_shared_lookup_manifest,
    phase35_prepare_recursive_compression_target_manifest,
    phase36_prepare_recursive_verifier_harness_receipt,
    phase37_prepare_recursive_artifact_chain_harness_receipt,
    prove_phase12_decoding_demo_for_layout,
    verify_phase31_recursive_compression_decode_boundary_manifest_against_sources,
    verify_phase32_recursive_compression_statement_contract_against_phase31,
    verify_phase33_recursive_compression_public_input_manifest_against_phase32,
    verify_phase34_recursive_compression_shared_lookup_manifest_against_sources,
    verify_phase35_recursive_compression_target_manifest_against_sources,
    verify_phase37_recursive_artifact_chain_harness_receipt_against_sources,
    Phase29RecursiveCompressionInputContract, Phase30DecodingStepProofEnvelopeManifest,
    Phase31RecursiveCompressionDecodeBoundaryManifest,
    Phase32RecursiveCompressionStatementContract, Phase33RecursiveCompressionPublicInputManifest,
    Phase34RecursiveCompressionSharedLookupManifest, Phase35RecursiveCompressionTargetManifest,
    Phase36RecursiveVerifierHarnessReceipt, Phase37RecursiveArtifactChainHarnessReceipt,
    StarkProofBackend, VmError, CLAIM_STATEMENT_VERSION_V1,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28,
    STWO_BACKEND_VERSION_PHASE12, STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE,
    STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29,
    STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29,
};
use serde::Deserialize;

const CORPUS_MANIFEST_JSON: &str =
    include_str!("fixtures/known_bad/phase29_to_phase37/manifest.json");

#[derive(Debug, Deserialize)]
struct KnownBadManifest {
    schema_version: String,
    cases: Vec<KnownBadCase>,
}

#[derive(Debug, Deserialize)]
struct KnownBadCase {
    name: String,
    phase: String,
    verifier: String,
    mutation: String,
    expected_error_contains: String,
}

struct ValidArtifacts {
    phase29: Phase29RecursiveCompressionInputContract,
    phase30: Phase30DecodingStepProofEnvelopeManifest,
    phase31: Phase31RecursiveCompressionDecodeBoundaryManifest,
    phase32: Phase32RecursiveCompressionStatementContract,
    phase33: Phase33RecursiveCompressionPublicInputManifest,
    phase34: Phase34RecursiveCompressionSharedLookupManifest,
    phase35: Phase35RecursiveCompressionTargetManifest,
    phase36: Phase36RecursiveVerifierHarnessReceipt,
    phase37: Phase37RecursiveArtifactChainHarnessReceipt,
}

#[test]
fn phase29_to_phase37_known_bad_corpus_rejects_expected_failures() {
    let manifest: KnownBadManifest =
        serde_json::from_str(CORPUS_MANIFEST_JSON).expect("parse known-bad manifest");
    assert_eq!(manifest.schema_version, "known-bad-phase29-to-phase37-v1");
    assert!(
        !manifest.cases.is_empty(),
        "known-bad corpus must not be empty"
    );

    let valid = valid_artifacts();
    for case in &manifest.cases {
        run_known_bad_case(&valid, case);
    }
}

fn valid_artifacts() -> ValidArtifacts {
    let layout = phase12_default_decoding_layout();
    let chain = prove_phase12_decoding_demo_for_layout(&layout).expect("phase12 demo");
    let phase30 =
        phase30_prepare_decoding_step_proof_envelope_manifest(&chain).expect("phase30 manifest");
    let phase29 = phase29_contract_for_phase30(&phase30);
    let phase31 =
        phase31_prepare_recursive_compression_decode_boundary_manifest(&phase29, &phase30)
            .expect("phase31 manifest");
    let phase32 = phase32_prepare_recursive_compression_statement_contract(&phase31)
        .expect("phase32 contract");
    let phase33 = phase33_prepare_recursive_compression_public_input_manifest(&phase32)
        .expect("phase33 manifest");
    let phase34 = phase34_prepare_recursive_compression_shared_lookup_manifest(&phase33, &phase30)
        .expect("phase34 manifest");
    let phase35 =
        phase35_prepare_recursive_compression_target_manifest(&phase32, &phase33, &phase34)
            .expect("phase35 manifest");
    let phase36 =
        phase36_prepare_recursive_verifier_harness_receipt(&phase35, &phase32, &phase33, &phase34)
            .expect("phase36 receipt");
    let phase37 = phase37_prepare_recursive_artifact_chain_harness_receipt(&phase29, &phase30)
        .expect("phase37 receipt");

    ValidArtifacts {
        phase29,
        phase30,
        phase31,
        phase32,
        phase33,
        phase34,
        phase35,
        phase36,
        phase37,
    }
}

fn phase29_contract_for_phase30(
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Phase29RecursiveCompressionInputContract {
    let mut contract = Phase29RecursiveCompressionInputContract {
        proof_backend: StarkProofBackend::Stwo,
        contract_version: STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29.to_string(),
        semantic_scope: STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29.to_string(),
        phase28_artifact_version:
            STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28
                .to_string(),
        phase28_semantic_scope:
            STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28
                .to_string(),
        phase28_proof_backend_version: STWO_BACKEND_VERSION_PHASE12.to_string(),
        statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
        required_recursion_posture: STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE.to_string(),
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        phase28_bounded_aggregation_arity: 2,
        phase28_member_count: 2,
        phase28_member_summaries: 2,
        phase28_nested_members: 2,
        total_phase26_members: 4,
        total_phase25_members: 8,
        max_nested_chain_arity: 2,
        max_nested_fold_arity: 2,
        total_matrices: 16,
        total_layouts: 16,
        total_rollups: 8,
        total_segments: 8,
        total_steps: phase30.total_steps,
        lookup_delta_entries: 12,
        max_lookup_frontier_entries: 4,
        source_template_commitment: "a".repeat(64),
        global_start_state_commitment: phase30.chain_start_boundary_commitment.clone(),
        global_end_state_commitment: phase30.chain_end_boundary_commitment.clone(),
        aggregation_template_commitment: "b".repeat(64),
        aggregated_chained_folded_interval_accumulator_commitment: "c".repeat(64),
        input_contract_commitment: String::new(),
    };
    contract.input_contract_commitment =
        commit_phase29_recursive_compression_input_contract(&contract)
            .expect("commit phase29 contract");
    contract
}

fn run_known_bad_case(valid: &ValidArtifacts, case: &KnownBadCase) {
    match (
        case.phase.as_str(),
        case.verifier.as_str(),
        case.mutation.as_str(),
    ) {
        ("phase29", "parse", "recursive_claim_recommitted") => {
            let mut contract = valid.phase29.clone();
            contract.recursive_verification_claimed = true;
            contract.input_contract_commitment =
                commit_phase29_recursive_compression_input_contract(&contract)
                    .expect("recommit phase29 contract");
            let json = serde_json::to_string(&contract).expect("serialize phase29 contract");
            assert_err_contains(
                &case.name,
                parse_phase29_recursive_compression_input_contract_json(&json),
                &case.expected_error_contains,
            );
        }
        ("phase30", "parse", "malformed_json") => {
            assert_err_contains(
                &case.name,
                parse_phase30_decoding_step_proof_envelope_manifest_json("{"),
                &case.expected_error_contains,
            );
        }
        ("phase30", "parse", "step_index_drift") => {
            let mut manifest = valid.phase30.clone();
            manifest.envelopes[0].step_index += 1;
            let json = serde_json::to_string(&manifest).expect("serialize phase30 manifest");
            assert_err_contains(
                &case.name,
                parse_phase30_decoding_step_proof_envelope_manifest_json(&json),
                &case.expected_error_contains,
            );
        }
        ("phase31", "against_sources", "total_steps_recommitted") => {
            let mut manifest = valid.phase31.clone();
            manifest.total_steps += 1;
            manifest.decode_boundary_bridge_commitment =
                commit_phase31_recursive_compression_decode_boundary_manifest(&manifest)
                    .expect("recommit phase31 manifest");
            assert_err_contains(
                &case.name,
                verify_phase31_recursive_compression_decode_boundary_manifest_against_sources(
                    &manifest,
                    &valid.phase29,
                    &valid.phase30,
                ),
                &case.expected_error_contains,
            );
        }
        ("phase32", "against_sources", "phase31_commitment_recommitted") => {
            let mut contract = valid.phase32.clone();
            contract.phase31_decode_boundary_bridge_commitment = "d".repeat(64);
            contract.recursive_statement_contract_commitment =
                commit_phase32_recursive_compression_statement_contract(&contract)
                    .expect("recommit phase32 contract");
            assert_err_contains(
                &case.name,
                verify_phase32_recursive_compression_statement_contract_against_phase31(
                    &contract,
                    &valid.phase31,
                ),
                &case.expected_error_contains,
            );
        }
        ("phase33", "against_sources", "phase32_commitment_recommitted") => {
            let mut manifest = valid.phase33.clone();
            manifest.phase32_recursive_statement_contract_commitment = "e".repeat(64);
            manifest.recursive_public_inputs_commitment =
                commit_phase33_recursive_compression_public_input_manifest(&manifest)
                    .expect("recommit phase33 manifest");
            assert_err_contains(
                &case.name,
                verify_phase33_recursive_compression_public_input_manifest_against_phase32(
                    &manifest,
                    &valid.phase32,
                ),
                &case.expected_error_contains,
            );
        }
        ("phase34", "against_sources", "lookup_commitment_recommitted") => {
            let mut manifest = valid.phase34.clone();
            manifest.input_lookup_rows_commitments_commitment = "f".repeat(64);
            manifest.shared_lookup_public_inputs_commitment =
                commit_phase34_recursive_compression_shared_lookup_manifest(&manifest)
                    .expect("recommit phase34 manifest");
            assert_err_contains(
                &case.name,
                verify_phase34_recursive_compression_shared_lookup_manifest_against_sources(
                    &manifest,
                    &valid.phase33,
                    &valid.phase30,
                ),
                &case.expected_error_contains,
            );
        }
        ("phase35", "against_sources", "phase33_commitment_recommitted") => {
            let mut manifest = valid.phase35.clone();
            manifest.phase33_recursive_public_inputs_commitment = "1".repeat(64);
            manifest.recursive_target_manifest_commitment =
                commit_phase35_recursive_compression_target_manifest(&manifest)
                    .expect("recommit phase35 manifest");
            assert_err_contains(
                &case.name,
                verify_phase35_recursive_compression_target_manifest_against_sources(
                    &manifest,
                    &valid.phase32,
                    &valid.phase33,
                    &valid.phase34,
                ),
                &case.expected_error_contains,
            );
        }
        ("phase36", "parse", "source_binding_false_recommitted") => {
            let mut receipt = valid.phase36.clone();
            receipt.source_binding_verified = false;
            receipt.recursive_verifier_harness_receipt_commitment =
                commit_phase36_recursive_verifier_harness_receipt(&receipt)
                    .expect("recommit phase36 receipt");
            let json = serde_json::to_string(&receipt).expect("serialize phase36 receipt");
            assert_err_contains(
                &case.name,
                parse_phase36_recursive_verifier_harness_receipt_json(&json),
                &case.expected_error_contains,
            );
        }
        ("phase37", "parse", "phase35_malformed_hash_recommitted") => {
            let mut receipt = valid.phase37.clone();
            receipt.phase35_recursive_target_manifest_commitment = "not-a-hash".to_string();
            receipt.recursive_artifact_chain_harness_receipt_commitment =
                commit_phase37_recursive_artifact_chain_harness_receipt(&receipt)
                    .expect("recommit phase37 receipt");
            let json = serde_json::to_string(&receipt).expect("serialize phase37 receipt");
            assert_err_contains(
                &case.name,
                parse_phase37_recursive_artifact_chain_harness_receipt_json(&json),
                &case.expected_error_contains,
            );
        }
        ("phase37", "against_sources", "phase36_commitment_recommitted") => {
            let mut receipt = valid.phase37.clone();
            receipt.phase36_recursive_verifier_harness_receipt_commitment = "2".repeat(64);
            receipt.recursive_artifact_chain_harness_receipt_commitment =
                commit_phase37_recursive_artifact_chain_harness_receipt(&receipt)
                    .expect("recommit phase37 receipt");
            assert_err_contains(
                &case.name,
                verify_phase37_recursive_artifact_chain_harness_receipt_against_sources(
                    &receipt,
                    &valid.phase29,
                    &valid.phase30,
                ),
                &case.expected_error_contains,
            );
        }
        _ => panic!("unhandled known-bad corpus case: {case:?}"),
    }
}

fn assert_err_contains<T>(case_name: &str, result: Result<T, VmError>, expected: &str) {
    match result {
        Ok(_) => panic!("known-bad case `{case_name}` unexpectedly passed"),
        Err(err) => {
            let message = err.to_string();
            assert!(
                message.contains(expected),
                "known-bad case `{case_name}` failed with `{message}`, expected substring `{expected}`"
            );
        }
    }
}
