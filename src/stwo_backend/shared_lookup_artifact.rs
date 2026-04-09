use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};

use super::decoding::{commit_phase12_layout, Phase12DecodingLayout};
use super::lookup_prover::{
    verify_phase10_shared_binary_step_lookup_envelope, Phase10SharedLookupProofEnvelope,
    STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10,
};
use super::normalization_prover::{
    verify_phase10_shared_normalization_lookup_envelope,
    Phase10SharedNormalizationLookupProofEnvelope,
    STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10,
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

fn checked_lookup_index(index: usize, label: &str) -> Result<u8> {
    u8::try_from(index).map_err(|_| {
        VmError::InvalidConfig(format!(
            "Phase 12 shared lookup artifact {label} index {index} exceeds the u8 memory-address limit"
        ))
    })
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct EmbeddedSharedNormalizationClaimRow {
    pub(crate) norm_sq_memory_index: u8,
    pub(crate) inv_sqrt_q8_memory_index: u8,
    pub(crate) expected_norm_sq: i16,
    pub(crate) expected_inv_sqrt_q8: i16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct EmbeddedSharedNormalizationProof {
    pub(crate) statement_version: String,
    pub(crate) semantic_scope: String,
    pub(crate) claimed_rows: Vec<EmbeddedSharedNormalizationClaimRow>,
    pub(crate) proof_envelope: Phase10SharedNormalizationLookupProofEnvelope,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct EmbeddedSharedActivationClaimRow {
    pub(crate) input_memory_index: u8,
    pub(crate) output_memory_index: u8,
    pub(crate) expected_input: i16,
    pub(crate) expected_output: i16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct EmbeddedSharedActivationLookupProof {
    pub(crate) statement_version: String,
    pub(crate) semantic_scope: String,
    pub(crate) claimed_rows: Vec<EmbeddedSharedActivationClaimRow>,
    pub(crate) proof_envelope: Phase10SharedLookupProofEnvelope,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase12SharedLookupArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub layout_commitment: String,
    pub lookup_rows_commitment: String,
    pub flattened_lookup_rows: Vec<i16>,
    pub(crate) normalization_proof_envelope: EmbeddedSharedNormalizationProof,
    pub(crate) activation_proof_envelope: EmbeddedSharedActivationLookupProof,
}

pub fn commit_phase12_shared_lookup_rows(
    layout_commitment: &str,
    flattened_lookup_rows: &[i16],
) -> String {
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

pub(crate) fn commit_phase12_shared_lookup_artifact(
    layout_commitment: &str,
    flattened_lookup_rows: &[i16],
    normalization_proof_envelope: &EmbeddedSharedNormalizationProof,
    activation_proof_envelope: &EmbeddedSharedActivationLookupProof,
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

pub(crate) fn build_phase12_shared_lookup_artifact(
    layout_commitment: &str,
    flattened_lookup_rows: Vec<i16>,
    normalization_proof_envelope: EmbeddedSharedNormalizationProof,
    activation_proof_envelope: EmbeddedSharedActivationLookupProof,
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
    layout: &Phase12DecodingLayout,
    expected_layout_commitment: &str,
) -> Result<()> {
    layout.validate()?;
    let computed_layout_commitment = commit_phase12_layout(layout);
    if computed_layout_commitment != expected_layout_commitment {
        return Err(VmError::InvalidConfig(format!(
            "verify_phase12_shared_lookup_artifact expected layout commitment `{}` does not match the validated layout commitment `{}`",
            expected_layout_commitment, computed_layout_commitment
        )));
    }
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
    if artifact.layout_commitment != computed_layout_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 shared lookup artifact layout commitment `{}` does not match expected `{}`",
            artifact.layout_commitment, computed_layout_commitment
        )));
    }

    let expected_lookup_rows_commitment = commit_phase12_shared_lookup_rows(
        &computed_layout_commitment,
        &artifact.flattened_lookup_rows,
    );
    if artifact.lookup_rows_commitment != expected_lookup_rows_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 12 shared lookup artifact lookup_rows_commitment does not match its flattened rows"
                .to_string(),
        ));
    }

    let expected_artifact_commitment = commit_phase12_shared_lookup_artifact(
        &computed_layout_commitment,
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
    let normalization_wrapper = &artifact.normalization_proof_envelope;
    if normalization_wrapper.statement_version
        != STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10
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
    let lookup = layout.lookup_range()?;
    let expected_normalization_indices = [
        (
            checked_lookup_index(lookup.start, "normalization input")?,
            checked_lookup_index(lookup.start + 1, "normalization inverse output")?,
        ),
        (
            checked_lookup_index(lookup.start + 4, "normalization input")?,
            checked_lookup_index(lookup.start + 5, "normalization inverse output")?,
        ),
    ];
    if normalization_wrapper.claimed_rows.len() != expected_normalization_indices.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 shared lookup artifact normalization row count {} does not match expected {}",
            normalization_wrapper.claimed_rows.len(),
            expected_normalization_indices.len()
        )));
    }
    for (row, (expected_norm_idx, expected_inv_idx)) in normalization_wrapper
        .claimed_rows
        .iter()
        .zip(expected_normalization_indices)
    {
        if row.norm_sq_memory_index != expected_norm_idx
            || row.inv_sqrt_q8_memory_index != expected_inv_idx
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 12 shared lookup artifact normalization indices ({}, {}) do not match expected ({}, {})",
                row.norm_sq_memory_index,
                row.inv_sqrt_q8_memory_index,
                expected_norm_idx,
                expected_inv_idx
            )));
        }
    }

    let activation_wrapper = &artifact.activation_proof_envelope;
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
    let expected_activation_indices = [
        (
            checked_lookup_index(lookup.start + 2, "activation input")?,
            checked_lookup_index(lookup.start + 3, "activation output")?,
        ),
        (
            checked_lookup_index(lookup.start + 6, "activation input")?,
            checked_lookup_index(lookup.start + 7, "activation output")?,
        ),
    ];
    if activation_wrapper.claimed_rows.len() != expected_activation_indices.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 shared lookup artifact activation row count {} does not match expected {}",
            activation_wrapper.claimed_rows.len(),
            expected_activation_indices.len()
        )));
    }
    for (row, (expected_input_idx, expected_output_idx)) in activation_wrapper
        .claimed_rows
        .iter()
        .zip(expected_activation_indices)
    {
        if row.input_memory_index != expected_input_idx
            || row.output_memory_index != expected_output_idx
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 12 shared lookup artifact activation indices ({}, {}) do not match expected ({}, {})",
                row.input_memory_index,
                row.output_memory_index,
                expected_input_idx,
                expected_output_idx
            )));
        }
    }
    if normalization_rows.len() != activation_rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 shared lookup artifact row counts disagree: normalization={}, activation={}",
            normalization_rows.len(),
            activation_rows.len()
        )));
    }
    let mut expected_flattened_rows = Vec::with_capacity(normalization_rows.len() * 4);
    for (normalization_row, activation_row) in normalization_rows.iter().zip(activation_rows.iter())
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
    let normalization_envelope = &normalization_wrapper.proof_envelope;
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
    if !verify_phase10_shared_normalization_lookup_envelope(normalization_envelope)? {
        return Err(VmError::UnsupportedProof(
            "Phase 12 shared lookup artifact normalization proof did not verify".to_string(),
        ));
    }
    let activation_envelope = &activation_wrapper.proof_envelope;
    if activation_envelope.claimed_rows != activation_rows {
        return Err(VmError::InvalidConfig(
            "Phase 12 shared lookup artifact activation wrapper rows do not match the embedded proof envelope"
                .to_string(),
        ));
    }
    if !verify_phase10_shared_binary_step_lookup_envelope(activation_envelope)? {
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
    use crate::stwo_backend::decoding::{commit_phase12_layout, phase12_default_decoding_layout};
    use crate::stwo_backend::lookup_component::Phase3LookupTableRow;
    use crate::stwo_backend::lookup_prover::prove_phase10_shared_binary_step_lookup_envelope;
    use crate::stwo_backend::normalization_prover::prove_phase10_shared_normalization_lookup_envelope;

    const ORACLE_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12: &str =
        "stwo-phase12-shared-lookup-artifact-v1";
    const ORACLE_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12: &str =
        "stwo_parameterized_decoding_shared_lookup_artifact";
    const ORACLE_DECODING_STATE_VERSION_PHASE12: &str = "stwo-decoding-state-v11";
    const ORACLE_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10: &str =
        "stwo-shared-normalization-lookup-v1";
    const ORACLE_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10: &str =
        "stwo-shared-binary-step-lookup-v1";
    const ORACLE_DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE: &str =
        "stwo_decoding_step_v2_execution_with_shared_normalization_lookup";
    const ORACLE_DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE: &str =
        "stwo_decoding_step_v2_execution_with_shared_binary_step_lookup";

    fn oracle_lower_hex(bytes: &[u8]) -> String {
        const HEX: &[u8; 16] = b"0123456789abcdef";
        let mut out = String::with_capacity(bytes.len() * 2);
        for &byte in bytes {
            out.push(HEX[(byte >> 4) as usize] as char);
            out.push(HEX[(byte & 0x0f) as usize] as char);
        }
        out
    }

    fn oracle_blake2b_256(parts: &[Vec<u8>]) -> String {
        let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
        for part in parts {
            hasher.update(part);
        }
        let mut out = [0u8; 32];
        hasher
            .finalize_variable(&mut out)
            .expect("blake2b finalize");
        oracle_lower_hex(&out)
    }

    #[test]
    fn oracle_constants_match_production() {
        assert_eq!(
            ORACLE_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12,
            super::STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12
        );
        assert_eq!(
            ORACLE_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12,
            super::STWO_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12
        );
        assert_eq!(
            ORACLE_DECODING_STATE_VERSION_PHASE12,
            crate::stwo_backend::decoding::STWO_DECODING_STATE_VERSION_PHASE12
        );
        assert_eq!(
            ORACLE_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10,
            super::STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10
        );
        assert_eq!(
            ORACLE_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10,
            super::STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10
        );
        assert_eq!(
            ORACLE_DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE,
            super::DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE
        );
        assert_eq!(
            ORACLE_DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE,
            super::DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE
        );
    }

    fn oracle_commit_phase12_shared_lookup_rows(
        layout_commitment: &str,
        flattened_lookup_rows: &[i16],
    ) -> String {
        let mut parts = vec![
            ORACLE_DECODING_STATE_VERSION_PHASE12.as_bytes().to_vec(),
            layout_commitment.as_bytes().to_vec(),
            b"lookup-rows".to_vec(),
        ];
        for value in flattened_lookup_rows {
            parts.push(value.to_le_bytes().to_vec());
        }
        oracle_blake2b_256(&parts)
    }

    fn oracle_commit_phase12_shared_lookup_artifact(
        layout_commitment: &str,
        flattened_lookup_rows: &[i16],
        normalization_proof_envelope: &EmbeddedSharedNormalizationProof,
        activation_proof_envelope: &EmbeddedSharedActivationLookupProof,
    ) -> String {
        let rows_json = serde_json::to_vec(flattened_lookup_rows).expect("rows json");
        let normalization_json =
            serde_json::to_vec(normalization_proof_envelope).expect("normalization json");
        let activation_json =
            serde_json::to_vec(activation_proof_envelope).expect("activation json");
        oracle_blake2b_256(&[
            ORACLE_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12
                .as_bytes()
                .to_vec(),
            layout_commitment.as_bytes().to_vec(),
            (rows_json.len() as u64).to_le_bytes().to_vec(),
            rows_json,
            (normalization_json.len() as u64).to_le_bytes().to_vec(),
            normalization_json,
            (activation_json.len() as u64).to_le_bytes().to_vec(),
            activation_json,
        ])
    }

    fn oracle_verify_phase12_shared_lookup_artifact(
        artifact: &Phase12SharedLookupArtifact,
        layout: &Phase12DecodingLayout,
        expected_layout_commitment: &str,
    ) -> Result<()> {
        layout.validate()?;
        let computed_layout_commitment = commit_phase12_layout(layout);
        if computed_layout_commitment != expected_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "oracle_verify_phase12_shared_lookup_artifact expected layout commitment `{}` does not match the validated layout commitment `{}`",
                expected_layout_commitment, computed_layout_commitment
            )));
        }
        if artifact.artifact_version != ORACLE_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12 {
            return Err(VmError::InvalidConfig(format!(
                "unsupported Phase 12 shared lookup artifact version `{}`",
                artifact.artifact_version
            )));
        }
        if artifact.semantic_scope != ORACLE_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12 {
            return Err(VmError::InvalidConfig(format!(
                "unsupported Phase 12 shared lookup artifact scope `{}`",
                artifact.semantic_scope
            )));
        }
        if artifact.layout_commitment != computed_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 12 shared lookup artifact layout commitment `{}` does not match expected `{}`",
                artifact.layout_commitment, computed_layout_commitment
            )));
        }

        let expected_lookup_rows_commitment = oracle_commit_phase12_shared_lookup_rows(
            &computed_layout_commitment,
            &artifact.flattened_lookup_rows,
        );
        if artifact.lookup_rows_commitment != expected_lookup_rows_commitment {
            return Err(VmError::InvalidConfig(
                "Phase 12 shared lookup artifact lookup_rows_commitment does not match its flattened rows"
                    .to_string(),
            ));
        }

        let expected_artifact_commitment = oracle_commit_phase12_shared_lookup_artifact(
            &computed_layout_commitment,
            &artifact.flattened_lookup_rows,
            &artifact.normalization_proof_envelope,
            &artifact.activation_proof_envelope,
        );
        if artifact.artifact_commitment != expected_artifact_commitment {
            return Err(VmError::InvalidConfig(
                "Phase 12 shared lookup artifact commitment does not match its serialized contents"
                    .to_string(),
            ));
        }

        let lookup = layout.lookup_range()?;
        let expected_norm_indices = [
            (
                checked_lookup_index(lookup.start, "normalization input")?,
                checked_lookup_index(lookup.start + 1, "normalization inverse output")?,
            ),
            (
                checked_lookup_index(lookup.start + 4, "normalization input")?,
                checked_lookup_index(lookup.start + 5, "normalization inverse output")?,
            ),
        ];
        let normalization_wrapper = &artifact.normalization_proof_envelope;
        if normalization_wrapper.statement_version
            != ORACLE_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10
        {
            return Err(VmError::InvalidConfig(format!(
                "unsupported Phase 12 shared lookup artifact normalization statement version `{}`",
                normalization_wrapper.statement_version
            )));
        }
        if normalization_wrapper.semantic_scope
            != ORACLE_DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE
        {
            return Err(VmError::InvalidConfig(format!(
                "unsupported Phase 12 shared lookup artifact normalization scope `{}`",
                normalization_wrapper.semantic_scope
            )));
        }
        if normalization_wrapper.claimed_rows.len() != expected_norm_indices.len() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 12 shared lookup artifact normalization row count {} does not match expected {}",
                normalization_wrapper.claimed_rows.len(),
                expected_norm_indices.len()
            )));
        }
        for (row, (expected_norm_idx, expected_inv_idx)) in normalization_wrapper
            .claimed_rows
            .iter()
            .zip(expected_norm_indices)
        {
            if row.norm_sq_memory_index != expected_norm_idx
                || row.inv_sqrt_q8_memory_index != expected_inv_idx
            {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 12 shared lookup artifact normalization indices ({}, {}) do not match expected ({}, {})",
                    row.norm_sq_memory_index,
                    row.inv_sqrt_q8_memory_index,
                    expected_norm_idx,
                    expected_inv_idx
                )));
            }
        }

        let normalization_rows: Vec<(i16, i16)> = normalization_wrapper
            .claimed_rows
            .iter()
            .map(|row| (row.expected_norm_sq, row.expected_inv_sqrt_q8))
            .collect();
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
        if normalization_wrapper.proof_envelope.claimed_rows != normalization_envelope_rows {
            return Err(VmError::InvalidConfig(
                "Phase 12 shared lookup artifact normalization wrapper rows do not match the embedded proof envelope"
                    .to_string(),
            ));
        }

        let expected_activation_indices = [
            (
                checked_lookup_index(lookup.start + 2, "activation input")?,
                checked_lookup_index(lookup.start + 3, "activation output")?,
            ),
            (
                checked_lookup_index(lookup.start + 6, "activation input")?,
                checked_lookup_index(lookup.start + 7, "activation output")?,
            ),
        ];
        let activation_wrapper = &artifact.activation_proof_envelope;
        if activation_wrapper.statement_version != ORACLE_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10 {
            return Err(VmError::InvalidConfig(format!(
                "unsupported Phase 12 shared lookup artifact activation statement version `{}`",
                activation_wrapper.statement_version
            )));
        }
        if activation_wrapper.semantic_scope != ORACLE_DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE {
            return Err(VmError::InvalidConfig(format!(
                "unsupported Phase 12 shared lookup artifact activation scope `{}`",
                activation_wrapper.semantic_scope
            )));
        }
        if activation_wrapper.claimed_rows.len() != expected_activation_indices.len() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 12 shared lookup artifact activation row count {} does not match expected {}",
                activation_wrapper.claimed_rows.len(),
                expected_activation_indices.len()
            )));
        }
        for (row, (expected_input_idx, expected_output_idx)) in activation_wrapper
            .claimed_rows
            .iter()
            .zip(expected_activation_indices)
        {
            if row.input_memory_index != expected_input_idx
                || row.output_memory_index != expected_output_idx
            {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 12 shared lookup artifact activation indices ({}, {}) do not match expected ({}, {})",
                    row.input_memory_index,
                    row.output_memory_index,
                    expected_input_idx,
                    expected_output_idx
                )));
            }
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
                        "Phase 12 shared lookup artifact activation output must be binary"
                            .to_string(),
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
        if activation_wrapper.proof_envelope.claimed_rows != activation_rows {
            return Err(VmError::InvalidConfig(
                "Phase 12 shared lookup artifact activation wrapper rows do not match the embedded proof envelope"
                    .to_string(),
            ));
        }

        let mut expected_flattened_rows = Vec::with_capacity(normalization_rows.len() * 4);
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
        if !verify_phase10_shared_normalization_lookup_envelope(
            &normalization_wrapper.proof_envelope,
        )? {
            return Err(VmError::UnsupportedProof(
                "Phase 12 shared lookup artifact normalization proof did not verify".to_string(),
            ));
        }
        if !verify_phase10_shared_binary_step_lookup_envelope(&activation_wrapper.proof_envelope)? {
            return Err(VmError::UnsupportedProof(
                "Phase 12 shared lookup artifact activation proof did not verify".to_string(),
            ));
        }
        Ok(())
    }

    fn sample_layout_and_commitment() -> (Phase12DecodingLayout, String) {
        let layout = phase12_default_decoding_layout();
        let commitment = commit_phase12_layout(&layout);
        (layout, commitment)
    }

    fn normalization_wrapper(
        envelope: Phase10SharedNormalizationLookupProofEnvelope,
    ) -> EmbeddedSharedNormalizationProof {
        let (layout, _) = sample_layout_and_commitment();
        let lookup = layout.lookup_range().expect("lookup range");
        EmbeddedSharedNormalizationProof {
            statement_version: STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10.to_string(),
            semantic_scope: DECODING_STEP_V2_SHARED_NORMALIZATION_SCOPE.to_string(),
            claimed_rows: vec![
                EmbeddedSharedNormalizationClaimRow {
                    norm_sq_memory_index: checked_lookup_index(lookup.start, "normalization input")
                        .expect("normalization input fits in u8"),
                    inv_sqrt_q8_memory_index: checked_lookup_index(
                        lookup.start + 1,
                        "normalization inverse output",
                    )
                    .expect("normalization inverse output fits in u8"),
                    expected_norm_sq: 16,
                    expected_inv_sqrt_q8: 64,
                },
                EmbeddedSharedNormalizationClaimRow {
                    norm_sq_memory_index: checked_lookup_index(
                        lookup.start + 4,
                        "normalization input",
                    )
                    .expect("normalization input fits in u8"),
                    inv_sqrt_q8_memory_index: checked_lookup_index(
                        lookup.start + 5,
                        "normalization inverse output",
                    )
                    .expect("normalization inverse output fits in u8"),
                    expected_norm_sq: 4,
                    expected_inv_sqrt_q8: 128,
                },
            ],
            proof_envelope: envelope,
        }
    }

    fn activation_wrapper(
        envelope: Phase10SharedLookupProofEnvelope,
    ) -> EmbeddedSharedActivationLookupProof {
        let (layout, _) = sample_layout_and_commitment();
        let lookup = layout.lookup_range().expect("lookup range");
        EmbeddedSharedActivationLookupProof {
            statement_version: STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10.to_string(),
            semantic_scope: DECODING_STEP_V2_SHARED_ACTIVATION_SCOPE.to_string(),
            claimed_rows: vec![
                EmbeddedSharedActivationClaimRow {
                    input_memory_index: checked_lookup_index(lookup.start + 2, "activation input")
                        .expect("activation input fits in u8"),
                    output_memory_index: checked_lookup_index(
                        lookup.start + 3,
                        "activation output",
                    )
                    .expect("activation output fits in u8"),
                    expected_input: 1,
                    expected_output: 1,
                },
                EmbeddedSharedActivationClaimRow {
                    input_memory_index: checked_lookup_index(lookup.start + 6, "activation input")
                        .expect("activation input fits in u8"),
                    output_memory_index: checked_lookup_index(
                        lookup.start + 7,
                        "activation output",
                    )
                    .expect("activation output fits in u8"),
                    expected_input: 0,
                    expected_output: 1,
                },
            ],
            proof_envelope: envelope,
        }
    }

    #[test]
    fn phase12_shared_lookup_artifact_verifies_nested_envelopes() {
        let (layout, layout_commitment) = sample_layout_and_commitment();
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
            Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
        ];
        let normalization_envelope =
            prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                .expect("normalization envelope");
        let activation_envelope =
            prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                .expect("activation envelope");
        let artifact = build_phase12_shared_lookup_artifact(
            &layout_commitment,
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper(normalization_envelope),
            activation_wrapper(activation_envelope),
        )
        .expect("artifact");

        verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment)
            .expect("artifact verifies");
    }

    #[test]
    fn phase12_shared_lookup_artifact_rejects_tampered_nested_proof_bytes() {
        let (layout, layout_commitment) = sample_layout_and_commitment();
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
            Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
        ];
        let normalization_envelope =
            prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                .expect("normalization envelope");
        let mut activation_envelope =
            prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                .expect("activation envelope");
        if let Some(byte) = activation_envelope.proof.get_mut(0) {
            *byte ^= 0x01;
        } else {
            panic!(
                "activation_envelope.proof is empty after prove_phase10_shared_binary_step_lookup_envelope"
            );
        }
        let artifact = build_phase12_shared_lookup_artifact(
            &layout_commitment,
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper(normalization_envelope),
            activation_wrapper(activation_envelope),
        )
        .expect("artifact");

        let error = verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment)
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
        let (layout, layout_commitment) = sample_layout_and_commitment();
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
            Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
        ];
        let normalization_envelope =
            prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                .expect("normalization envelope");
        let activation_envelope =
            prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                .expect("activation envelope");
        let normalization_wrapper = normalization_wrapper(normalization_envelope);
        let mut activation_wrapper = activation_wrapper(activation_envelope);
        activation_wrapper.claimed_rows[0].expected_output = -255;
        let artifact = build_phase12_shared_lookup_artifact(
            &layout_commitment,
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper,
            activation_wrapper,
        )
        .expect("artifact");

        let error = verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment)
            .expect_err("noncanonical activation output should fail");
        assert!(
            error
                .to_string()
                .contains("activation output is not a canonical u8"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn phase12_shared_lookup_artifact_rejects_tampered_wrapper_indices() {
        let (layout, layout_commitment) = sample_layout_and_commitment();
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
            Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
        ];
        let normalization_envelope =
            prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                .expect("normalization envelope");
        let activation_envelope =
            prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                .expect("activation envelope");
        let mut artifact = build_phase12_shared_lookup_artifact(
            &layout_commitment,
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper(normalization_envelope),
            activation_wrapper(activation_envelope),
        )
        .expect("artifact");
        artifact.activation_proof_envelope.claimed_rows[0].input_memory_index += 1;
        artifact.artifact_commitment = commit_phase12_shared_lookup_artifact(
            &layout_commitment,
            &artifact.flattened_lookup_rows,
            &artifact.normalization_proof_envelope,
            &artifact.activation_proof_envelope,
        )
        .expect("recommit artifact");

        let error = verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment)
            .expect_err("tampered wrapper indices should fail");
        assert!(
            error.to_string().contains("activation indices")
                || error.to_string().contains("normalization indices"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn phase12_shared_lookup_artifact_rejects_recommitted_flattened_row_drift() {
        let (layout, layout_commitment) = sample_layout_and_commitment();
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
            Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
        ];
        let normalization_envelope =
            prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                .expect("normalization envelope");
        let activation_envelope =
            prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                .expect("activation envelope");
        let mut artifact = build_phase12_shared_lookup_artifact(
            &layout_commitment,
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper(normalization_envelope),
            activation_wrapper(activation_envelope),
        )
        .expect("artifact");

        artifact.flattened_lookup_rows[0] = 4;
        artifact.lookup_rows_commitment =
            commit_phase12_shared_lookup_rows(&layout_commitment, &artifact.flattened_lookup_rows);
        artifact.artifact_commitment = commit_phase12_shared_lookup_artifact(
            &layout_commitment,
            &artifact.flattened_lookup_rows,
            &artifact.normalization_proof_envelope,
            &artifact.activation_proof_envelope,
        )
        .expect("recommit artifact");

        let error = verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment)
            .expect_err("flattened-row drift should fail");
        assert!(
            error.to_string().contains("flattened rows do not match"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn phase12_shared_lookup_artifact_oracle_matches_production_on_valid_artifact() {
        let (layout, layout_commitment) = sample_layout_and_commitment();
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
            Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
        ];
        let artifact = build_phase12_shared_lookup_artifact(
            &layout_commitment,
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper(
                prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                    .expect("normalization envelope"),
            ),
            activation_wrapper(
                prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                    .expect("activation envelope"),
            ),
        )
        .expect("artifact");

        verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment)
            .expect("production verifier");
        oracle_verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment)
            .expect("oracle verifier");
    }

    #[test]
    fn phase12_shared_lookup_artifact_oracle_matches_production_on_tampered_indices() {
        let (layout, layout_commitment) = sample_layout_and_commitment();
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
            Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
        ];
        let mut artifact = build_phase12_shared_lookup_artifact(
            &layout_commitment,
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper(
                prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                    .expect("normalization envelope"),
            ),
            activation_wrapper(
                prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                    .expect("activation envelope"),
            ),
        )
        .expect("artifact");
        artifact.normalization_proof_envelope.claimed_rows[0].norm_sq_memory_index += 1;
        artifact.artifact_commitment = oracle_commit_phase12_shared_lookup_artifact(
            &layout_commitment,
            &artifact.flattened_lookup_rows,
            &artifact.normalization_proof_envelope,
            &artifact.activation_proof_envelope,
        );

        let production =
            verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment);
        let oracle =
            oracle_verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment);
        assert!(
            production.is_err(),
            "production unexpectedly accepted tampered artifact"
        );
        assert!(
            oracle.is_err(),
            "oracle unexpectedly accepted tampered artifact"
        );
    }

    #[test]
    fn phase12_shared_lookup_artifact_oracle_matches_production_on_tampered_proof_bytes() {
        let (layout, layout_commitment) = sample_layout_and_commitment();
        let normalization_rows = vec![(16u16, 64u16), (4u16, 128u16)];
        let activation_rows = vec![
            Phase3LookupTableRow {
                input: 1,
                output: 1,
            },
            Phase3LookupTableRow {
                input: 0,
                output: 1,
            },
        ];
        let mut artifact = build_phase12_shared_lookup_artifact(
            &layout_commitment,
            vec![16, 64, 1, 1, 4, 128, 0, 1],
            normalization_wrapper(
                prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                    .expect("normalization envelope"),
            ),
            activation_wrapper(
                prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                    .expect("activation envelope"),
            ),
        )
        .expect("artifact");
        let byte = artifact
            .activation_proof_envelope
            .proof_envelope
            .proof
            .first_mut()
            .expect("activation proof must contain at least one byte");
        *byte ^= 0x01;
        artifact.artifact_commitment = oracle_commit_phase12_shared_lookup_artifact(
            &layout_commitment,
            &artifact.flattened_lookup_rows,
            &artifact.normalization_proof_envelope,
            &artifact.activation_proof_envelope,
        );

        let production =
            verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment);
        let oracle =
            oracle_verify_phase12_shared_lookup_artifact(&artifact, &layout, &layout_commitment);
        assert!(
            production.is_err(),
            "production unexpectedly accepted tampered proof bytes"
        );
        assert!(
            oracle.is_err(),
            "oracle unexpectedly accepted tampered proof bytes"
        );
    }
}
