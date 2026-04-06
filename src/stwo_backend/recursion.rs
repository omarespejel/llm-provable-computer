use serde::{Deserialize, Serialize};

use crate::error::{Result, VmError};
use crate::proof::{ExecutionClaimCommitments, StarkProofBackend, VanillaStarkExecutionProof};

pub const STWO_RECURSION_BATCH_VERSION_PHASE6: &str = "stwo-phase6-recursion-batch-v1";
pub const STWO_RECURSION_BATCH_SCOPE_PHASE6: &str =
    "stwo_execution_proof_batch_preaggregation_manifest";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase6RecursionBatchEntry {
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub steps: usize,
    pub proof_bytes: usize,
    pub commitment_program_hash: String,
    pub commitment_stark_options_hash: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase6RecursionBatchManifest {
    pub proof_backend: StarkProofBackend,
    pub batch_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub total_proofs: usize,
    pub total_steps: usize,
    pub total_proof_bytes: usize,
    pub entries: Vec<Phase6RecursionBatchEntry>,
}

pub fn phase6_prepare_recursion_batch(
    proofs: &[VanillaStarkExecutionProof],
) -> Result<Phase6RecursionBatchManifest> {
    let first = proofs.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "recursion batch preparation requires at least one proof".to_string(),
        )
    })?;
    if first.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "recursion batch preparation requires `stwo` proofs, got `{}`",
            first.proof_backend
        )));
    }
    required_commitments(first)?;

    let mut entries = Vec::with_capacity(proofs.len());
    let mut total_steps = 0usize;
    let mut total_proof_bytes = 0usize;

    for (index, proof) in proofs.iter().enumerate() {
        if proof.proof_backend != StarkProofBackend::Stwo {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses backend `{}`; expected `stwo` for recursion batching",
                proof.proof_backend
            )));
        }
        if proof.proof_backend_version != first.proof_backend_version {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses backend version `{}`; expected `{}`",
                proof.proof_backend_version, first.proof_backend_version
            )));
        }
        if proof.claim.statement_version != first.claim.statement_version {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses statement version `{}`; expected `{}`",
                proof.claim.statement_version, first.claim.statement_version
            )));
        }
        if proof.claim.semantic_scope != first.claim.semantic_scope {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses semantic scope `{}`; expected `{}`",
                proof.claim.semantic_scope, first.claim.semantic_scope
            )));
        }
        let commitments = required_commitments(proof)?;
        if commitments.stark_options_hash != first_commitment_stark_options_hash(first)? {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses stark options hash `{}`; expected `{}`",
                commitments.stark_options_hash,
                first_commitment_stark_options_hash(first)?
            )));
        }

        total_steps += proof.claim.steps;
        total_proof_bytes += proof.proof.len();
        entries.push(Phase6RecursionBatchEntry {
            proof_backend_version: proof.proof_backend_version.clone(),
            statement_version: proof.claim.statement_version.clone(),
            semantic_scope: proof.claim.semantic_scope.clone(),
            steps: proof.claim.steps,
            proof_bytes: proof.proof.len(),
            commitment_program_hash: commitments.program_hash.clone(),
            commitment_stark_options_hash: commitments.stark_options_hash.clone(),
        });
    }

    Ok(Phase6RecursionBatchManifest {
        proof_backend: StarkProofBackend::Stwo,
        batch_version: STWO_RECURSION_BATCH_VERSION_PHASE6.to_string(),
        semantic_scope: STWO_RECURSION_BATCH_SCOPE_PHASE6.to_string(),
        proof_backend_version: first.proof_backend_version.clone(),
        statement_version: first.claim.statement_version.clone(),
        total_proofs: entries.len(),
        total_steps,
        total_proof_bytes,
        entries,
    })
}

fn required_commitments(proof: &VanillaStarkExecutionProof) -> Result<&ExecutionClaimCommitments> {
    proof.claim.commitments.as_ref().ok_or_else(|| {
        VmError::InvalidConfig(
            "recursion batch preparation requires commitment metadata".to_string(),
        )
    })
}

fn first_commitment_stark_options_hash(proof: &VanillaStarkExecutionProof) -> Result<String> {
    Ok(required_commitments(proof)?.stark_options_hash.clone())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::assembly::parse_program;
    use crate::proof::{
        production_v1_stark_options, CLAIM_SEMANTIC_SCOPE_V1, CLAIM_STATEMENT_VERSION_V1,
    };
    use crate::state::MachineState;
    use crate::Attention2DMode;

    fn sample_proof(program_source: &str, program_hash: &str) -> VanillaStarkExecutionProof {
        let program = parse_program(program_source).expect("parse");
        VanillaStarkExecutionProof {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: "stwo-phase5-arithmetic-subset-v1".to_string(),
            claim: crate::proof::VanillaStarkExecutionClaim {
                statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
                semantic_scope: CLAIM_SEMANTIC_SCOPE_V1.to_string(),
                program,
                attention_mode: Attention2DMode::AverageHard,
                transformer_config: None,
                steps: 3,
                final_state: MachineState::with_memory(vec![0, 0, 0, 0]),
                options: production_v1_stark_options(),
                equivalence: None,
                commitments: Some(ExecutionClaimCommitments {
                    scheme_version: "v1".to_string(),
                    hash_function: "blake2b-256".to_string(),
                    program_hash: program_hash.to_string(),
                    transformer_config_hash: "cfg".to_string(),
                    deterministic_model_hash: "model".to_string(),
                    stark_options_hash: "opts".to_string(),
                    prover_build_info: "build".to_string(),
                    prover_build_hash: "buildhash".to_string(),
                }),
            },
            proof: vec![1, 2, 3],
        }
    }

    #[test]
    fn phase6_recursion_batch_manifest_accepts_compatible_stwo_proofs() {
        let proofs = vec![
            sample_proof(".memory 4\nLOADI 1\nHALT\n", "hash-a"),
            sample_proof(".memory 4\nLOADI 2\nHALT\n", "hash-b"),
        ];
        let manifest = phase6_prepare_recursion_batch(&proofs).expect("prepare batch");
        assert_eq!(manifest.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(manifest.total_proofs, 2);
        assert_eq!(manifest.total_steps, 6);
        assert_eq!(manifest.total_proof_bytes, 6);
        assert_eq!(manifest.entries[0].commitment_program_hash, "hash-a");
        assert_eq!(manifest.entries[1].commitment_program_hash, "hash-b");
    }
}
