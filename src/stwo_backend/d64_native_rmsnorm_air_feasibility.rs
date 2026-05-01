use serde::{Deserialize, Serialize};

use crate::error::{Result, VmError};

use super::d64_native_export_contract::{
    ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT, ZKAI_D64_RMS_NORM_ROWS, ZKAI_D64_RMS_SQUARE_ROWS,
    ZKAI_D64_TARGET_ID, ZKAI_D64_WIDTH,
};
use super::d64_native_rmsnorm_slice_contract::{
    zkai_d64_native_rmsnorm_slice_contract_from_oracle_json_str, ZkAiD64NativeRmsnormSliceContract,
    ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION, ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION,
    ZKAI_D64_NATIVE_RMSNORM_SLICE_NEXT_BACKEND_STEP, ZKAI_D64_RMS_SCALE_TREE_ROOT,
};
use super::normalization_component::{
    phase5_normalization_lookup_component_metadata, Phase5NormalizationTableRow,
};

pub const ZKAI_D64_RMSNORM_AIR_FEASIBILITY_SCHEMA: &str =
    "zkai-d64-native-rmsnorm-air-feasibility-gate-v1";
pub const ZKAI_D64_RMSNORM_AIR_FEASIBILITY_DECISION: &str =
    "NO_GO_EXISTING_NORMALIZATION_LOOKUP_NOT_D64_RMSNORM_AIR";
pub const ZKAI_D64_RMSNORM_AIR_FEASIBILITY_RUST_MODULE: &str =
    "src/stwo_backend/d64_native_rmsnorm_air_feasibility.rs";
pub const ZKAI_D64_RMSNORM_AIR_FEASIBILITY_KIND: &str = "research-gate";
pub const ZKAI_D64_RMSNORM_AIR_FEASIBILITY_NEXT_BACKEND_STEP: &str =
    "implement a d64-specific RMSNorm AIR component with 64 square rows, 64 normalization rows, proof_native_parameter_commitment binding, and rms_scale_tree_root binding";

const EXISTING_COMPONENT_NAME: &str = "Phase5NormalizationLookupRelation";
const EXISTING_COMPONENT_EXPECTED_LOG_SIZE: u32 = 4;

const EXPECTED_BLOCKERS: &[&str] = &[
    "existing_component_table_rows_5_not_d64_rms_square_rows_64",
    "existing_component_has_no_proof_native_parameter_commitment_input",
    "existing_component_has_no_rms_scale_tree_root_binding",
    "existing_component_claims_lookup_membership_not_rmsnorm_arithmetic_rows",
    "existing_component_statement_contract_marks_primitive_internal",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not a d64 AIR proof",
    "not verifier-time evidence",
    "not proof-native parameter opening evidence",
    "not a 64-row RMSNorm constraint system",
    "not safe to reuse the Phase5/Phase10 normalization primitive as the d64 slice proof",
];

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "cargo test d64_native_rmsnorm_air_feasibility --lib --features stwo-backend",
    "cargo test d64_native_rmsnorm_slice_contract --lib",
    "cargo test d64_native_export_contract --lib",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate-fast",
    "just gate",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExistingNormalizationComponentSummary {
    pub component_name: String,
    pub log_size: u32,
    pub semantics: String,
    pub statement_contract: String,
    pub lookup_table_row_count: usize,
    pub lookup_table_rows: Vec<Phase5NormalizationTableRow>,
    pub logup_relations_per_row: Vec<(String, usize)>,
    pub consumes_proof_native_parameter_commitment: bool,
    pub binds_rms_scale_tree_root: bool,
    pub proves_d64_rmsnorm_arithmetic_rows: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD64NativeRmsnormAirFeasibilityGate {
    pub schema: String,
    pub evidence_kind: String,
    pub rust_module: String,
    pub decision: String,
    pub target_id: String,
    pub source_rmsnorm_slice_contract_version: String,
    pub source_rmsnorm_slice_decision: String,
    pub source_rmsnorm_slice_next_backend_step: String,
    pub proof_native_parameter_commitment: String,
    pub rms_scale_tree_root: String,
    pub width: usize,
    pub d64_rms_square_rows: usize,
    pub d64_rms_norm_rows: usize,
    pub existing_component: ExistingNormalizationComponentSummary,
    pub blockers: Vec<String>,
    pub non_claims: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

impl ZkAiD64NativeRmsnormAirFeasibilityGate {
    pub fn validate(&self) -> Result<()> {
        expect_eq(
            &self.schema,
            ZKAI_D64_RMSNORM_AIR_FEASIBILITY_SCHEMA,
            "schema",
        )?;
        expect_eq(
            &self.evidence_kind,
            ZKAI_D64_RMSNORM_AIR_FEASIBILITY_KIND,
            "evidence kind",
        )?;
        expect_eq(
            &self.rust_module,
            ZKAI_D64_RMSNORM_AIR_FEASIBILITY_RUST_MODULE,
            "rust module",
        )?;
        expect_eq(
            &self.decision,
            ZKAI_D64_RMSNORM_AIR_FEASIBILITY_DECISION,
            "decision",
        )?;
        expect_eq(&self.target_id, ZKAI_D64_TARGET_ID, "target id")?;
        expect_eq(
            &self.source_rmsnorm_slice_contract_version,
            ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION,
            "source rmsnorm slice contract version",
        )?;
        expect_eq(
            &self.source_rmsnorm_slice_decision,
            ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION,
            "source rmsnorm slice decision",
        )?;
        expect_eq(
            &self.source_rmsnorm_slice_next_backend_step,
            ZKAI_D64_NATIVE_RMSNORM_SLICE_NEXT_BACKEND_STEP,
            "source rmsnorm slice next backend step",
        )?;
        expect_eq(
            &self.proof_native_parameter_commitment,
            ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT,
            "proof-native parameter commitment",
        )?;
        expect_eq(
            &self.rms_scale_tree_root,
            ZKAI_D64_RMS_SCALE_TREE_ROOT,
            "rms scale tree root",
        )?;
        expect_usize(self.width, ZKAI_D64_WIDTH, "width")?;
        expect_usize(
            self.d64_rms_square_rows,
            ZKAI_D64_RMS_SQUARE_ROWS,
            "d64 rms square rows",
        )?;
        expect_usize(
            self.d64_rms_norm_rows,
            ZKAI_D64_RMS_NORM_ROWS,
            "d64 rms norm rows",
        )?;
        validate_existing_component(&self.existing_component)?;
        expect_str_set_eq(
            self.blockers.iter().map(String::as_str),
            EXPECTED_BLOCKERS,
            "blockers",
        )?;
        expect_str_set_eq(
            self.non_claims.iter().map(String::as_str),
            EXPECTED_NON_CLAIMS,
            "non claims",
        )?;
        expect_eq(
            &self.next_backend_step,
            ZKAI_D64_RMSNORM_AIR_FEASIBILITY_NEXT_BACKEND_STEP,
            "next backend step",
        )?;
        expect_str_set_eq(
            self.validation_commands.iter().map(String::as_str),
            EXPECTED_VALIDATION_COMMANDS,
            "validation commands",
        )?;
        Ok(())
    }
}

pub fn zkai_d64_native_rmsnorm_air_feasibility_from_oracle_json_str(
    raw_oracle_json: &str,
) -> Result<ZkAiD64NativeRmsnormAirFeasibilityGate> {
    let slice = zkai_d64_native_rmsnorm_slice_contract_from_oracle_json_str(raw_oracle_json)?;
    zkai_d64_native_rmsnorm_air_feasibility_from_slice(&slice)
}

pub fn zkai_d64_native_rmsnorm_air_feasibility_from_slice(
    slice: &ZkAiD64NativeRmsnormSliceContract,
) -> Result<ZkAiD64NativeRmsnormAirFeasibilityGate> {
    slice.validate()?;
    let metadata =
        phase5_normalization_lookup_component_metadata(EXISTING_COMPONENT_EXPECTED_LOG_SIZE);
    let existing_component = ExistingNormalizationComponentSummary {
        component_name: EXISTING_COMPONENT_NAME.to_string(),
        log_size: metadata.log_size,
        semantics: metadata.semantics.to_string(),
        statement_contract: metadata.statement_contract.to_string(),
        lookup_table_row_count: metadata.lookup_table_rows.len(),
        lookup_table_rows: metadata.lookup_table_rows,
        logup_relations_per_row: metadata.logup_relations_per_row,
        consumes_proof_native_parameter_commitment: false,
        binds_rms_scale_tree_root: false,
        proves_d64_rmsnorm_arithmetic_rows: false,
    };
    let gate = ZkAiD64NativeRmsnormAirFeasibilityGate {
        schema: ZKAI_D64_RMSNORM_AIR_FEASIBILITY_SCHEMA.to_string(),
        evidence_kind: ZKAI_D64_RMSNORM_AIR_FEASIBILITY_KIND.to_string(),
        rust_module: ZKAI_D64_RMSNORM_AIR_FEASIBILITY_RUST_MODULE.to_string(),
        decision: ZKAI_D64_RMSNORM_AIR_FEASIBILITY_DECISION.to_string(),
        target_id: slice.target_id.clone(),
        source_rmsnorm_slice_contract_version: slice.contract_version.clone(),
        source_rmsnorm_slice_decision: slice.decision.clone(),
        source_rmsnorm_slice_next_backend_step: slice.next_backend_step.clone(),
        proof_native_parameter_commitment: slice.proof_native_parameter_commitment.clone(),
        rms_scale_tree_root: slice.rms_scale_tree_root.clone(),
        width: slice.width,
        d64_rms_square_rows: slice.rms_square_rows,
        d64_rms_norm_rows: slice.rms_norm_rows,
        existing_component,
        blockers: EXPECTED_BLOCKERS
            .iter()
            .map(|blocker| blocker.to_string())
            .collect(),
        non_claims: EXPECTED_NON_CLAIMS
            .iter()
            .map(|claim| claim.to_string())
            .collect(),
        next_backend_step: ZKAI_D64_RMSNORM_AIR_FEASIBILITY_NEXT_BACKEND_STEP.to_string(),
        validation_commands: EXPECTED_VALIDATION_COMMANDS
            .iter()
            .map(|command| command.to_string())
            .collect(),
    };
    gate.validate()?;
    Ok(gate)
}

pub fn zkai_d64_native_rmsnorm_air_feasibility_from_json_str(
    raw_gate_json: &str,
) -> Result<ZkAiD64NativeRmsnormAirFeasibilityGate> {
    let gate: ZkAiD64NativeRmsnormAirFeasibilityGate = serde_json::from_str(raw_gate_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    gate.validate()?;
    Ok(gate)
}

fn validate_existing_component(component: &ExistingNormalizationComponentSummary) -> Result<()> {
    expect_eq(
        &component.component_name,
        EXISTING_COMPONENT_NAME,
        "existing component name",
    )?;
    expect_usize(
        component.log_size as usize,
        EXISTING_COMPONENT_EXPECTED_LOG_SIZE as usize,
        "existing component log size",
    )?;
    if !component.semantics.contains("reciprocal-square-root") {
        return Err(feasibility_error(
            "existing component semantics no longer describe reciprocal-square-root lookup",
        ));
    }
    if !component
        .statement_contract
        .contains("primitive remains internal")
    {
        return Err(feasibility_error(
            "existing component statement contract no longer marks primitive as internal",
        ));
    }
    expect_usize(
        component.lookup_table_row_count,
        5,
        "existing component lookup table row count",
    )?;
    let expected_rows = vec![
        Phase5NormalizationTableRow {
            norm_sq: 1,
            inv_sqrt_q8: 256,
        },
        Phase5NormalizationTableRow {
            norm_sq: 2,
            inv_sqrt_q8: 181,
        },
        Phase5NormalizationTableRow {
            norm_sq: 4,
            inv_sqrt_q8: 128,
        },
        Phase5NormalizationTableRow {
            norm_sq: 8,
            inv_sqrt_q8: 91,
        },
        Phase5NormalizationTableRow {
            norm_sq: 16,
            inv_sqrt_q8: 64,
        },
    ];
    if component.lookup_table_rows != expected_rows {
        return Err(feasibility_error(format!(
            "existing component lookup rows drifted: got {:?}, expected {:?}",
            component.lookup_table_rows, expected_rows
        )));
    }
    let expected_relations = vec![("Phase5NormalizationLookupRelation".to_string(), 2)];
    if component.logup_relations_per_row != expected_relations {
        return Err(feasibility_error(format!(
            "existing component logup relations drifted: got {:?}, expected {:?}",
            component.logup_relations_per_row, expected_relations
        )));
    }
    if component.consumes_proof_native_parameter_commitment {
        return Err(feasibility_error(
            "existing component unexpectedly claims proof_native_parameter_commitment consumption",
        ));
    }
    if component.binds_rms_scale_tree_root {
        return Err(feasibility_error(
            "existing component unexpectedly claims rms_scale_tree_root binding",
        ));
    }
    if component.proves_d64_rmsnorm_arithmetic_rows {
        return Err(feasibility_error(
            "existing component unexpectedly claims d64 RMSNorm arithmetic rows",
        ));
    }
    Ok(())
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(feasibility_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(feasibility_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_str_set_eq<'a>(
    actual: impl IntoIterator<Item = &'a str>,
    expected: &[&str],
    label: &str,
) -> Result<()> {
    let mut actual_vec: Vec<&str> = actual.into_iter().collect();
    let mut expected_vec = expected.to_vec();
    actual_vec.sort_unstable();
    expected_vec.sort_unstable();
    if actual_vec != expected_vec {
        return Err(feasibility_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected_vec:?}"
        )));
    }
    Ok(())
}

fn feasibility_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d64 RMSNorm AIR feasibility gate rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const ORACLE_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d64-native-relation-witness-oracle-2026-05.json"
    );
    const FEASIBILITY_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d64-native-rmsnorm-air-feasibility-2026-05.json"
    );

    fn report() -> ZkAiD64NativeRmsnormAirFeasibilityGate {
        zkai_d64_native_rmsnorm_air_feasibility_from_oracle_json_str(ORACLE_JSON)
            .expect("feasibility report")
    }

    #[test]
    fn d64_rmsnorm_air_feasibility_records_existing_component_no_go() {
        let report = report();
        assert_eq!(report.decision, ZKAI_D64_RMSNORM_AIR_FEASIBILITY_DECISION);
        assert_eq!(report.d64_rms_square_rows, 64);
        assert_eq!(report.d64_rms_norm_rows, 64);
        assert_eq!(report.existing_component.lookup_table_row_count, 5);
        assert!(
            !report
                .existing_component
                .consumes_proof_native_parameter_commitment
        );
        assert!(!report.existing_component.binds_rms_scale_tree_root);
        assert!(!report.existing_component.proves_d64_rmsnorm_arithmetic_rows);
        assert!(report
            .blockers
            .contains(&"existing_component_has_no_rms_scale_tree_root_binding".to_string()));
    }

    #[test]
    fn checked_feasibility_evidence_round_trips() {
        let from_oracle = report();
        let from_json = zkai_d64_native_rmsnorm_air_feasibility_from_json_str(FEASIBILITY_JSON)
            .expect("checked evidence");
        assert_eq!(from_json, from_oracle);
    }

    #[test]
    fn feasibility_gate_rejects_source_slice_drift() {
        let mut value: Value = serde_json::from_str(ORACLE_JSON).expect("oracle json");
        value["relation_witness"]["parameter_manifest"]["rms_scale_tree"]["root"] =
            Value::String(ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT.to_string());
        let error = zkai_d64_native_rmsnorm_air_feasibility_from_oracle_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("rms scale tree root"));
    }

    #[test]
    fn feasibility_evidence_rejects_wrong_decision() {
        let mut value: Value = serde_json::from_str(FEASIBILITY_JSON).expect("evidence json");
        value["decision"] = Value::String("GO_EXISTING_COMPONENT_IS_D64_AIR".to_string());
        let error = zkai_d64_native_rmsnorm_air_feasibility_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("decision"));
    }

    #[test]
    fn feasibility_evidence_rejects_claimed_parameter_consumption() {
        let mut value: Value = serde_json::from_str(FEASIBILITY_JSON).expect("evidence json");
        value["existing_component"]["consumes_proof_native_parameter_commitment"] =
            Value::Bool(true);
        let error = zkai_d64_native_rmsnorm_air_feasibility_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("proof_native_parameter_commitment"));
    }

    #[test]
    fn feasibility_evidence_rejects_missing_blocker() {
        let mut value: Value = serde_json::from_str(FEASIBILITY_JSON).expect("evidence json");
        value["blockers"].as_array_mut().expect("blockers").pop();
        let error = zkai_d64_native_rmsnorm_air_feasibility_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("blockers"));
    }

    #[test]
    fn feasibility_evidence_rejects_table_row_drift() {
        let mut value: Value = serde_json::from_str(FEASIBILITY_JSON).expect("evidence json");
        value["existing_component"]["lookup_table_rows"][0]["inv_sqrt_q8"] = Value::from(255u64);
        let error = zkai_d64_native_rmsnorm_air_feasibility_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("lookup rows drifted"));
    }

    #[test]
    fn feasibility_evidence_rejects_unknown_fields() {
        let mut value: Value = serde_json::from_str(FEASIBILITY_JSON).expect("evidence json");
        value["surprise"] = Value::Bool(true);
        let error = zkai_d64_native_rmsnorm_air_feasibility_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("unknown field"));
    }
}
