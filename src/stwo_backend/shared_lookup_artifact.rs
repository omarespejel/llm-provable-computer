use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};

use serde_json::Value;

use super::lookup_prover::{
    verify_phase10_shared_binary_step_lookup_envelope, Phase10SharedLookupProofEnvelope,
    STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10,
};
use super::normalization_prover::{
    verify_phase10_shared_normalization_lookup_envelope,
    Phase10SharedNormalizationLookupProofEnvelope, STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10,
};
use super::{Phase3LookupTableRow, STWO_DECODING_STATE_VERSION_PHASE12};
use crate::error::{Result, VmError};

pub const STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12: &str =
    "stwo-phase12-shared-lookup-artifact-v1";
pub const STWO_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12: &str =
    "stwo_parameterized_decoding_shared_lookup_artifact";
pub(crate) const DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE: &str =
    "stwo_decoding_step_v2_execution_with_shared_normalization_lookup";
pub(crate) const DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE: &str =
    "stwo_decoding_step_v2_execution_with_shared_binary_step_lookup";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct EmbeddedSharedNormalizationClaimRow {
    norm_sq_memory_index: u8,
    inv_sqrt_q8_memory_index: u8,
    expected_norm_sq: i16,
    expected_inv_sqrt_q8: i16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct EmbeddedSharedNormalizationProof {
    statement_version: String,
    semantic_scope: String,
    claimed_rows: Vec<EmbeddedSharedNormalizationClaimRow>,
    proof_envelope: Value,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct EmbeddedSharedActivationClaimRow {
    input_memory_index: u8,
    output_memory_index: u8,
    expected_input: i16,
    expected_output: i16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct EmbeddedSharedActivationLookupProof {
    statement_version: String,
    semantic_scope: String,
    claimed_rows: Vec<EmbeddedSharedActivationClaimRow>,
    proof_envelope: Value,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase12SharedLookupArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub layout_commitment: String,
    pub lookup_rows_commitment: String,
    pub flattened_lookup_rows: Vec<i16>,
    pub normalization_proof_envelope: Value,
    pub activation_proof_envelope: Value,
}

pub fn commit_phase12_shared_lookup_rows(layout_commitment: &str, flattened_lookup_rows: &[i16]) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE12.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"lookup-rows");
    for value in flattened_lookup_rows {
        hasher.update(&value.to_le_bytes());
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

pub fn commit_phase12_shared_lookup_artifact(
    layout_commitment: &str,
    flattened_lookup_rows: &[i16],
    normalization_proof_envelope: &Value,
    activation_proof_envelope: &Value,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    let rows_json = serde_json::to_vec(flattened_lookup_rows)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(rows_json.len() as u64).to_le_bytes());
    hasher.update(&rows_json);
    let normalization_json = serde_json::to_vec(normalization_proof_envelope)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(normalization_json.len() as u64).to_le_bytes());
    hasher.update(&normalization_json);
    let activation_json = serde_json::to_vec(activation_proof_envelope)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(activation_json.len() as u64).to_le_bytes());
    hasher.update(&activation_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

pub fn build_phase12_shared_lookup_artifact(
    layout_commitment: &str,
    flattened_lookup_rows: Vec<i16>,
    normalization_proof_envelope: Value,
    activation_proof_envelope: Value,
) -> Result<Phase12SharedLookupArtifact> {
    let lookup_rows_commitment =
        commit_phase12_shared_lookup_rows(layout_commitment, &flattened_lookup_rows);
    let artifact_commitment = commit_phase12_shared_lookup_artifact(
        layout_commitment,
        &flattened_lookup_rows,
        &normalization_proof_envelope,
        &activation_proof_envelope,
    )?;
    Ok(Phase12SharedLookupArtifact {
        artifact_version: STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12.to_string(),
        semantic_scope: STWO_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12.to_string(),
        artifact_commitment,
        layout_commitment: layout_commitment.to_string(),
        lookup_rows_commitment,
        flattened_lookup_rows,
        normalization_proof_envelope,
        activation_proof_envelope,
    })
}

pub fn verify_phase12_shared_lookup_artifact(
    artifact: &Phase12SharedLookupArtifact,
    expected_layout_commitment: &str,
) -> Result<()> {
    if artifact.artifact_version != STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 12 shared lookup artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 12 shared lookup artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.layout_commitment != expected_layout_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 shared lookup artifact layout commitment `{}` does not match expected `{}`",
            artifact.layout_commitment, expected_layout_commitment
        )));
    }

    let expected_lookup_rows_commitment =
        commit_phase12_shared_lookup_rows(expected_layout_commitment, &artifact.flattened_lookup_rows);
    if artifact.lookup_rows_commitment != expected_lookup_rows_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 12 shared lookup artifact lookup_rows_commitment does not match its flattened rows"
                .to_string(),
        ));
    }

    let expected_artifact_commitment = commit_phase12_shared_lookup_artifact(
        expected_layout_commitment,
        &artifact.flattened_lookup_rows,
        &artifact.normalization_proof_envelope,
        &artifact.activation_proof_envelope,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 12 shared lookup artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }
    let normalization_wrapper: EmbeddedSharedNormalizationProof =
        serde_json::from_value(artifact.normalization_proof_envelope.clone())
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    if normalization_wrapper.statement_version != STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 12 shared lookup artifact normalization statement version `{}`",
            normalization_wrapper.statement_version
        )));
    }
    if normalization_wrapper.semantic_scope != DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 12 shared lookup artifact normalization scope `{}`",
            normalization_wrapper.semantic_scope
        )));
    }
    let normalization_rows: Vec<(i16, i16)> = normalization_wrapper
        .claimed_rows
        .iter()
        .map(|row| (row.expected_norm_sq, row.expected_inv_sqrt_q8))
        .collect();

    let activation_wrapper: EmbeddedSharedActivationLookupProof =
        serde_json::from_value(artifact.activation_proof_envelope.clone())
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    if activation_wrapper.statement_version != STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 12 shared lookup artifact activation statement version `{}`",
            activation_wrapper.statement_version
        )));
    }
    if activation_wrapper.semantic_scope != DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 12 shared lookup artifact activation scope `{}`",
            activation_wrapper.semantic_scope
        )));
    }
    let activation_rows: Vec<Phase3LookupTableRow> = activation_wrapper
        .claimed_rows
        .iter()
        .map(|row| {
            let output = u8::try_from(row.expected_output).map_err(|_| {
                VmError::InvalidConfig(
                    "Phase 12 shared lookup artifact activation output is not a canonical u8"
                        .to_string(),
                )
            })?;
            if output > 1 {
                return Err(VmError::InvalidConfig(
                    "Phase 12 shared lookup artifact activation output must be binary".to_string(),
                ));
            }
            Ok(Phase3LookupTableRow {
                input: row.expected_input,
                output,
            })
        })
        .collect::<Result<_>>()?;
    if normalization_rows.len() != activation_rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 shared lookup artifact row counts disagree: normalization={}, activation={}",
            normalization_rows.len(),
            activation_rows.len()
        )));
    }
    let mut expected_flattened_rows =
        Vec::with_capacity(normalization_rows.len() * 4);
    for (normalization_row, activation_row) in
        normalization_rows.iter().zip(activation_rows.iter())
    {
        expected_flattened_rows.push(normalization_row.0);
        expected_flattened_rows.push(normalization_row.1);
        expected_flattened_rows.push(activation_row.input);
        expected_flattened_rows.push(i16::from(activation_row.output));
    }
    if artifact.flattened_lookup_rows != expected_flattened_rows {
        return Err(VmError::InvalidConfig(
            "Phase 12 shared lookup artifact flattened rows do not match the embedded lookup proofs"
                .to_string(),
        ));
    }
    let normalization_envelope: Phase10SharedNormalizationLookupProofEnvelope =
        serde_json::from_value(normalization_wrapper.proof_envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    let normalization_envelope_rows: Vec<(u16, u16)> = normalization_rows
        .iter()
        .map(|(norm_sq, inv_sqrt_q8)| {
            Ok((
                u16::try_from(*norm_sq).map_err(|_| {
                    VmError::InvalidConfig(
                        "Phase 12 shared lookup artifact normalization row is not a canonical u16"
                            .to_string(),
                    )
                })?,
                u16::try_from(*inv_sqrt_q8).map_err(|_| {
                    VmError::InvalidConfig(
                        "Phase 12 shared lookup artifact normalization inverse row is not a canonical u16"
                            .to_string(),
                    )
                })?,
            ))
        })
        .collect::<Result<_>>()?;
    if normalization_envelope.claimed_rows != normalization_envelope_rows {
        return Err(VmError::InvalidConfig(
            "Phase 12 shared lookup artifact normalization wrapper rows do not match the embedded proof envelope"
                .to_string(),
        ));
    }
    if !verify_phase10_shared_normalization_lookup_envelope(&normalization_envelope)? {
        return Err(VmError::UnsupportedProof(
            "Phase 12 shared lookup artifact normalization proof did not verify".to_string(),
        ));
    }
    let activation_envelope: Phase10SharedLookupProofEnvelope =
        serde_json::from_value(activation_wrapper.proof_envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    if activation_envelope.claimed_rows != activation_rows {
        return Err(VmError::InvalidConfig(
            "Phase 12 shared lookup artifact activation wrapper rows do not match the embedded proof envelope"
                .to_string(),
        ));
    }
    if !verify_phase10_shared_binary_step_lookup_envelope(&activation_envelope)? {
        return Err(VmError::UnsupportedProof(
            "Phase 12 shared lookup artifact activation proof did not verify".to_string(),
        ));
    }

    Ok(())
}

fn lower_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::stwo_backend::lookup_component::Phase3LookupTableRow;
    use crate::stwo_backend::lookup_prover::prove_phase10_shared_binary_step_lookup_envelope;
    use crate::stwo_backend::normalization_prover::prove_phase10_shared_normalization_lookup_envelope;

    #[test]
    fn phase12_shared_lookup_artifact_verifies_nested_envelopes() {
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow { input: 1, output: 1 },
            Phase3LookupTableRow { input: 0, output: 1 },
        ];
        let normalization_envelope =
            prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                .expect("normalization envelope");
        let activation_envelope =
            prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                .expect("activation envelope");
        let normalization_wrapper = serde_json::json!({
            "statement_version": STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10,
            "semantic_scope": DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE,
            "claimed_rows": [
                {
                    "norm_sq_memory_index": 16,
                    "inv_sqrt_q8_memory_index": 17,
                    "expected_norm_sq": 16,
                    "expected_inv_sqrt_q8": 64
                },
                {
                    "norm_sq_memory_index": 18,
                    "inv_sqrt_q8_memory_index": 19,
                    "expected_norm_sq": 4,
                    "expected_inv_sqrt_q8": 128
                }
            ],
            "proof_envelope": normalization_envelope
        });
        let activation_wrapper = serde_json::json!({
            "statement_version": STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10,
            "semantic_scope": DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE,
            "claimed_rows": [
                {
                    "input_memory_index": 20,
                    "output_memory_index": 21,
                    "expected_input": 1,
                    "expected_output": 1
                },
                {
                    "input_memory_index": 22,
                    "output_memory_index": 23,
                    "expected_input": 0,
                    "expected_output": 1
                }
            ],
            "proof_envelope": activation_envelope
        });
        let artifact = build_phase12_shared_lookup_artifact(
            "layout-commitment",
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper,
            activation_wrapper,
        )
        .expect("artifact");

        verify_phase12_shared_lookup_artifact(&artifact, "layout-commitment")
            .expect("artifact verifies");
    }

    #[test]
    fn phase12_shared_lookup_artifact_rejects_tampered_nested_proof_bytes() {
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow { input: 1, output: 1 },
            Phase3LookupTableRow { input: 0, output: 1 },
        ];
        let normalization_envelope =
            prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                .expect("normalization envelope");
        let mut activation_envelope =
            prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                .expect("activation envelope");
        activation_envelope.proof[0] ^= 0x01;
        let normalization_wrapper = serde_json::json!({
            "statement_version": STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10,
            "semantic_scope": DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE,
            "claimed_rows": [
                {
                    "norm_sq_memory_index": 16,
                    "inv_sqrt_q8_memory_index": 17,
                    "expected_norm_sq": 16,
                    "expected_inv_sqrt_q8": 64
                },
                {
                    "norm_sq_memory_index": 18,
                    "inv_sqrt_q8_memory_index": 19,
                    "expected_norm_sq": 4,
                    "expected_inv_sqrt_q8": 128
                }
            ],
            "proof_envelope": normalization_envelope
        });
        let activation_wrapper = serde_json::json!({
            "statement_version": STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10,
            "semantic_scope": DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE,
            "claimed_rows": [
                {
                    "input_memory_index": 20,
                    "output_memory_index": 21,
                    "expected_input": 1,
                    "expected_output": 1
                },
                {
                    "input_memory_index": 22,
                    "output_memory_index": 23,
                    "expected_input": 0,
                    "expected_output": 1
                }
            ],
            "proof_envelope": activation_envelope
        });
        let artifact = build_phase12_shared_lookup_artifact(
            "layout-commitment",
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper,
            activation_wrapper,
        )
        .expect("artifact");

        let error = verify_phase12_shared_lookup_artifact(&artifact, "layout-commitment")
            .expect_err("tampered nested proof should fail");
        assert!(
            error
                .to_string()
                .contains("activation proof did not verify")
                || error.to_string().contains("unsupported")
                || error.to_string().contains("serialization error"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn phase12_shared_lookup_artifact_rejects_noncanonical_activation_output() {
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow { input: 1, output: 1 },
            Phase3LookupTableRow { input: 0, output: 1 },
        ];
        let normalization_envelope =
            prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                .expect("normalization envelope");
        let activation_envelope =
            prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                .expect("activation envelope");
        let normalization_wrapper = serde_json::json!({
            "statement_version": STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10,
            "semantic_scope": DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE,
            "claimed_rows": [
                {
                    "norm_sq_memory_index": 16,
                    "inv_sqrt_q8_memory_index": 17,
                    "expected_norm_sq": 16,
                    "expected_inv_sqrt_q8": 64
                },
                {
                    "norm_sq_memory_index": 18,
                    "inv_sqrt_q8_memory_index": 19,
                    "expected_norm_sq": 4,
                    "expected_inv_sqrt_q8": 128
                }
            ],
            "proof_envelope": normalization_envelope
        });
        let activation_wrapper = serde_json::json!({
            "statement_version": STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10,
            "semantic_scope": DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE,
            "claimed_rows": [
                {
                    "input_memory_index": 20,
                    "output_memory_index": 21,
                    "expected_input": 1,
                    "expected_output": -255
                },
                {
                    "input_memory_index": 22,
                    "output_memory_index": 23,
                    "expected_input": 0,
                    "expected_output": 1
                }
            ],
            "proof_envelope": activation_envelope
        });
        let artifact = build_phase12_shared_lookup_artifact(
            "layout-commitment",
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper,
            activation_wrapper,
        )
        .expect("artifact");

        let error = verify_phase12_shared_lookup_artifact(&artifact, "layout-commitment")
            .expect_err("noncanonical activation output should fail");
        assert!(
            error
                .to_string()
                .contains("activation output is not a canonical u8"),
            "unexpected error: {error}"
        );
    }
}
