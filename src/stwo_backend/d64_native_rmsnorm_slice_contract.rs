use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

use crate::error::{Result, VmError};

use super::d64_native_export_contract::{
    zkai_d64_native_export_contract_from_oracle_value, RelationCheckRecord,
    ZkAiD64NativeExportContract, ZKAI_D64_INPUT_ACTIVATION_COMMITMENT,
    ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION, ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION,
    ZKAI_D64_NORMALIZATION_CONFIG_COMMITMENT, ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT,
    ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT, ZKAI_D64_RELATION_COMMITMENT,
    ZKAI_D64_REQUIRED_BACKEND_VERSION, ZKAI_D64_RMS_NORM_ROWS, ZKAI_D64_RMS_SQUARE_ROWS,
    ZKAI_D64_STATEMENT_COMMITMENT, ZKAI_D64_TARGET_ID, ZKAI_D64_VERIFIER_DOMAIN, ZKAI_D64_WIDTH,
};

pub const ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION: &str =
    "zkai-d64-native-rmsnorm-slice-contract-v1";
pub const ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION: &str = "GO_NATIVE_RMSNORM_SLICE_NOT_AIR_PROOF";
pub const ZKAI_D64_NATIVE_RMSNORM_SLICE_NEXT_BACKEND_STEP: &str =
    "encode rms_square_rows and rms_norm_rows as native Stwo AIR constraints bound to proof_native_parameter_commitment";
pub const ZKAI_D64_RMS_SCALE_TREE_ROOT: &str =
    "blake2b-256:c803dcaebdd6a3ec0e39a60bd71c64914e5badaceca9445e8cabfa0ac8fb90f3";
pub const ZKAI_D64_RMSNORM_RELATION_CHECK_NAME: &str = "rmsnorm_rows_recomputed";

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not a Stwo proof",
    "not verifier-time evidence",
    "not full d64 block proof",
    "not projection, activation, SwiGLU, down-projection, or residual proof",
    "not proof that private witness rows already open to proof_native_parameter_commitment",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct D64ValueRangeRecord {
    pub count: usize,
    pub min: i64,
    pub max: i64,
    pub max_abs: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD64NativeRmsnormSliceContract {
    pub contract_version: String,
    pub decision: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub source_export_contract_version: String,
    pub source_export_decision: String,
    pub proof_native_parameter_commitment: String,
    pub normalization_config_commitment: String,
    pub input_activation_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub relation_commitment: String,
    pub rms_scale_tree_root: String,
    pub width: usize,
    pub rms_square_rows: usize,
    pub rms_norm_rows: usize,
    pub input_q8_range: D64ValueRangeRecord,
    pub normed_q8_range: D64ValueRangeRecord,
    pub rmsnorm_relation_check: RelationCheckRecord,
    pub non_claims: Vec<String>,
    pub next_backend_step: String,
}

impl ZkAiD64NativeRmsnormSliceContract {
    pub fn validate(&self) -> Result<()> {
        expect_eq(
            &self.contract_version,
            ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION,
            "rmsnorm slice contract version",
        )?;
        expect_eq(
            &self.decision,
            ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION,
            "rmsnorm slice decision",
        )?;
        expect_eq(&self.target_id, ZKAI_D64_TARGET_ID, "target id")?;
        expect_eq(
            &self.required_backend_version,
            ZKAI_D64_REQUIRED_BACKEND_VERSION,
            "required backend version",
        )?;
        expect_eq(
            &self.verifier_domain,
            ZKAI_D64_VERIFIER_DOMAIN,
            "verifier domain",
        )?;
        expect_eq(
            &self.source_export_contract_version,
            ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION,
            "source export contract version",
        )?;
        expect_eq(
            &self.source_export_decision,
            ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION,
            "source export decision",
        )?;
        expect_eq(
            &self.proof_native_parameter_commitment,
            ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT,
            "proof-native parameter commitment",
        )?;
        expect_eq(
            &self.normalization_config_commitment,
            ZKAI_D64_NORMALIZATION_CONFIG_COMMITMENT,
            "normalization config commitment",
        )?;
        expect_eq(
            &self.input_activation_commitment,
            ZKAI_D64_INPUT_ACTIVATION_COMMITMENT,
            "input activation commitment",
        )?;
        expect_eq(
            &self.public_instance_commitment,
            ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT,
            "public instance commitment",
        )?;
        expect_eq(
            &self.statement_commitment,
            ZKAI_D64_STATEMENT_COMMITMENT,
            "statement commitment",
        )?;
        expect_eq(
            &self.relation_commitment,
            ZKAI_D64_RELATION_COMMITMENT,
            "relation commitment",
        )?;
        expect_eq(
            &self.rms_scale_tree_root,
            ZKAI_D64_RMS_SCALE_TREE_ROOT,
            "rms scale tree root",
        )?;
        expect_usize(self.width, ZKAI_D64_WIDTH, "width")?;
        expect_usize(
            self.rms_square_rows,
            ZKAI_D64_RMS_SQUARE_ROWS,
            "rms square rows",
        )?;
        expect_usize(self.rms_norm_rows, ZKAI_D64_RMS_NORM_ROWS, "rms norm rows")?;
        expect_value_range(
            &self.input_q8_range,
            D64ValueRangeRecord {
                count: ZKAI_D64_WIDTH,
                min: -192,
                max: 190,
                max_abs: 192,
            },
            "input_q8 range",
        )?;
        expect_value_range(
            &self.normed_q8_range,
            D64ValueRangeRecord {
                count: ZKAI_D64_WIDTH,
                min: -452,
                max: 454,
                max_abs: 454,
            },
            "normed_q8 range",
        )?;
        expect_eq(
            &self.rmsnorm_relation_check.name,
            ZKAI_D64_RMSNORM_RELATION_CHECK_NAME,
            "rmsnorm relation check name",
        )?;
        expect_eq(
            &self.rmsnorm_relation_check.status,
            "GO",
            "rmsnorm relation check status",
        )?;
        expect_str_set_eq(
            self.non_claims.iter().map(String::as_str),
            EXPECTED_NON_CLAIMS,
            "rmsnorm slice non claims",
        )?;
        expect_eq(
            &self.next_backend_step,
            ZKAI_D64_NATIVE_RMSNORM_SLICE_NEXT_BACKEND_STEP,
            "rmsnorm slice next backend step",
        )?;
        Ok(())
    }
}

pub fn zkai_d64_native_rmsnorm_slice_contract_from_oracle_json_str(
    raw_oracle_json: &str,
) -> Result<ZkAiD64NativeRmsnormSliceContract> {
    let value: Value = serde_json::from_str(raw_oracle_json)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    zkai_d64_native_rmsnorm_slice_contract_from_oracle_value(&value)
}

pub fn zkai_d64_native_rmsnorm_slice_contract_from_oracle_value(
    oracle: &Value,
) -> Result<ZkAiD64NativeRmsnormSliceContract> {
    let export_contract = zkai_d64_native_export_contract_from_oracle_value(oracle)?;
    export_contract.validate()?;
    let rmsnorm_relation_check = relation_check_from_export(&export_contract)?;

    let rms_scale_tree_root = string_at(
        oracle,
        &[
            "relation_witness",
            "parameter_manifest",
            "rms_scale_tree",
            "root",
        ],
    )?;
    expect_eq(
        rms_scale_tree_root,
        ZKAI_D64_RMS_SCALE_TREE_ROOT,
        "rms scale tree root",
    )?;
    let rms_square_rows = usize_at(
        oracle,
        &["relation_witness", "row_counts", "rms_square_rows"],
    )?;
    let rms_norm_rows = usize_at(oracle, &["relation_witness", "row_counts", "rms_norm_rows"])?;
    let input_q8_range = value_range_at(oracle, &["relation_witness", "value_ranges", "input_q8"])?;
    let normed_q8_range =
        value_range_at(oracle, &["relation_witness", "value_ranges", "normed_q8"])?;

    let contract = ZkAiD64NativeRmsnormSliceContract {
        contract_version: ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION.to_string(),
        decision: ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION.to_string(),
        target_id: export_contract.target_id.clone(),
        required_backend_version: export_contract.required_backend_version.clone(),
        verifier_domain: export_contract.verifier_domain.clone(),
        source_export_contract_version: export_contract.contract_version.clone(),
        source_export_decision: export_contract.decision.clone(),
        proof_native_parameter_commitment: export_contract
            .proof_native_parameter_commitment
            .clone(),
        normalization_config_commitment: export_contract.normalization_config_commitment.clone(),
        input_activation_commitment: export_contract.input_activation_commitment.clone(),
        public_instance_commitment: export_contract.public_instance_commitment.clone(),
        statement_commitment: export_contract.statement_commitment.clone(),
        relation_commitment: export_contract.relation_commitment.clone(),
        rms_scale_tree_root: rms_scale_tree_root.to_string(),
        width: export_contract.width,
        rms_square_rows,
        rms_norm_rows,
        input_q8_range,
        normed_q8_range,
        rmsnorm_relation_check,
        non_claims: EXPECTED_NON_CLAIMS
            .iter()
            .map(|item| item.to_string())
            .collect(),
        next_backend_step: ZKAI_D64_NATIVE_RMSNORM_SLICE_NEXT_BACKEND_STEP.to_string(),
    };
    contract.validate()?;
    Ok(contract)
}

fn relation_check_from_export(
    contract: &ZkAiD64NativeExportContract,
) -> Result<RelationCheckRecord> {
    contract
        .relation_check_records
        .iter()
        .find(|record| record.name == ZKAI_D64_RMSNORM_RELATION_CHECK_NAME)
        .cloned()
        .ok_or_else(|| rmsnorm_error("missing rmsnorm relation check"))
}

fn value_range_at(value: &Value, path: &[&str]) -> Result<D64ValueRangeRecord> {
    let object = object_at(value, path, "value range")?;
    expect_exact_keys(object, &["count", "max", "max_abs", "min"], "value range")?;
    Ok(D64ValueRangeRecord {
        count: usize_at(value, &[path, &["count"]].concat())?,
        min: i64_at(value, &[path, &["min"]].concat())?,
        max: i64_at(value, &[path, &["max"]].concat())?,
        max_abs: i64_at(value, &[path, &["max_abs"]].concat())?,
    })
}

fn object_at<'a>(value: &'a Value, path: &[&str], label: &str) -> Result<&'a Map<String, Value>> {
    let mut cursor = value;
    for key in path {
        cursor = cursor
            .get(*key)
            .ok_or_else(|| rmsnorm_error(format!("{label} missing field {key}")))?;
    }
    cursor
        .as_object()
        .ok_or_else(|| rmsnorm_error(format!("{label} must be an object")))
}

fn value_at<'a>(value: &'a Value, path: &[&str]) -> Result<&'a Value> {
    let mut cursor = value;
    for key in path {
        cursor = cursor
            .get(*key)
            .ok_or_else(|| rmsnorm_error(format!("missing field {}", path.join("."))))?;
    }
    Ok(cursor)
}

fn string_at<'a>(value: &'a Value, path: &[&str]) -> Result<&'a str> {
    value_at(value, path)?
        .as_str()
        .ok_or_else(|| rmsnorm_error(format!("{} must be a string", path.join("."))))
}

fn usize_at(value: &Value, path: &[&str]) -> Result<usize> {
    let raw = value_at(value, path)?
        .as_u64()
        .ok_or_else(|| rmsnorm_error(format!("{} must be an unsigned integer", path.join("."))))?;
    usize::try_from(raw).map_err(|_| rmsnorm_error(format!("{} exceeds usize", path.join("."))))
}

fn i64_at(value: &Value, path: &[&str]) -> Result<i64> {
    value_at(value, path)?
        .as_i64()
        .ok_or_else(|| rmsnorm_error(format!("{} must be a signed integer", path.join("."))))
}

fn expect_value_range(
    actual: &D64ValueRangeRecord,
    expected: D64ValueRangeRecord,
    label: &str,
) -> Result<()> {
    if actual != &expected {
        return Err(rmsnorm_error(format!(
            "{label} mismatch: got {actual:?}, expected {expected:?}"
        )));
    }
    Ok(())
}

fn expect_exact_keys(object: &Map<String, Value>, expected: &[&str], label: &str) -> Result<()> {
    let actual: BTreeSet<String> = object.keys().cloned().collect();
    let expected_set: BTreeSet<String> = expected.iter().map(|item| item.to_string()).collect();
    if actual != expected_set {
        return Err(rmsnorm_error(format!(
            "{label} mismatch: got {actual:?}, expected {expected_set:?}"
        )));
    }
    Ok(())
}

fn expect_str_set_eq<'a>(
    actual: impl IntoIterator<Item = &'a str>,
    expected: &[&str],
    label: &str,
) -> Result<()> {
    let actual_vec: Vec<&str> = actual.into_iter().collect();
    if actual_vec.len() != expected.len() {
        return Err(rmsnorm_error(format!(
            "{label} count mismatch: got {}, expected {}",
            actual_vec.len(),
            expected.len()
        )));
    }
    let actual_set: BTreeSet<String> = actual_vec.iter().map(|item| item.to_string()).collect();
    if actual_set.len() != actual_vec.len() {
        return Err(rmsnorm_error(format!("{label} contains duplicates")));
    }
    let expected_set: BTreeSet<String> = expected.iter().map(|item| item.to_string()).collect();
    if actual_set != expected_set {
        return Err(rmsnorm_error(format!(
            "{label} mismatch: got {actual_set:?}, expected {expected_set:?}"
        )));
    }
    Ok(())
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(rmsnorm_error(format!(
            "{label} mismatch: got {actual:?}, expected {expected:?}"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(rmsnorm_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn rmsnorm_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d64 native rmsnorm slice contract: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    const ORACLE_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d64-native-relation-witness-oracle-2026-05.json"
    );

    fn oracle_value() -> Value {
        serde_json::from_str(ORACLE_JSON).expect("oracle evidence json")
    }

    fn mutate(path: &[&str], replacement: Value) -> Value {
        let mut value = oracle_value();
        let mut cursor = &mut value;
        for key in &path[..path.len() - 1] {
            cursor = cursor.get_mut(*key).expect("path segment exists");
        }
        cursor[path[path.len() - 1]] = replacement;
        value
    }

    #[test]
    fn rmsnorm_slice_contract_consumes_export_contract() {
        let contract = zkai_d64_native_rmsnorm_slice_contract_from_oracle_json_str(ORACLE_JSON)
            .expect("rmsnorm slice contract");

        assert_eq!(
            contract.contract_version,
            ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION
        );
        assert_eq!(contract.decision, ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION);
        assert_eq!(
            contract.source_export_contract_version,
            ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION
        );
        assert_eq!(contract.width, ZKAI_D64_WIDTH);
        assert_eq!(contract.rms_square_rows, ZKAI_D64_RMS_SQUARE_ROWS);
        assert_eq!(contract.rms_norm_rows, ZKAI_D64_RMS_NORM_ROWS);
        assert_eq!(
            contract.rmsnorm_relation_check.name,
            ZKAI_D64_RMSNORM_RELATION_CHECK_NAME
        );
        contract.validate().expect("slice validates");
    }

    #[test]
    fn rmsnorm_slice_contract_rejects_relation_check_drift() {
        let mut value = oracle_value();
        value["relation_witness"]["relation_checks"][3]["status"] = Value::String("NO_GO".into());

        let err = zkai_d64_native_rmsnorm_slice_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("non-GO status"), "{err}");
    }

    #[test]
    fn rmsnorm_slice_contract_rejects_rms_row_count_drift() {
        let value = mutate(
            &["relation_witness", "row_counts", "rms_norm_rows"],
            Value::from(63u64),
        );

        let err = zkai_d64_native_rmsnorm_slice_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("rms_norm_rows"), "{err}");
    }

    #[test]
    fn rmsnorm_slice_contract_rejects_rms_scale_tree_root_drift() {
        let value = mutate(
            &[
                "relation_witness",
                "parameter_manifest",
                "rms_scale_tree",
                "root",
            ],
            Value::String("blake2b-256:".to_string() + &"77".repeat(32)),
        );

        let err = zkai_d64_native_rmsnorm_slice_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("rms scale tree root"), "{err}");
    }

    #[test]
    fn rmsnorm_slice_contract_rejects_normed_range_drift() {
        let value = mutate(
            &["relation_witness", "value_ranges", "normed_q8", "max_abs"],
            Value::from(455u64),
        );

        let err = zkai_d64_native_rmsnorm_slice_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("normed_q8 range"), "{err}");
    }

    #[test]
    fn rmsnorm_slice_contract_rejects_round_trip_relation_check_drift() {
        let contract = zkai_d64_native_rmsnorm_slice_contract_from_oracle_json_str(ORACLE_JSON)
            .expect("rmsnorm slice contract");
        let mut value = serde_json::to_value(&contract).expect("slice contract json");
        value["rmsnorm_relation_check"]["name"] = Value::String("weaker_check".into());
        let drifted: ZkAiD64NativeRmsnormSliceContract =
            serde_json::from_value(value).expect("drifted slice contract shape");

        let err = drifted.validate().unwrap_err();
        assert!(err.to_string().contains("relation check name"), "{err}");
    }

    #[test]
    fn rmsnorm_slice_contract_rejects_round_trip_non_claim_drift() {
        let contract = zkai_d64_native_rmsnorm_slice_contract_from_oracle_json_str(ORACLE_JSON)
            .expect("rmsnorm slice contract");
        let mut value = serde_json::to_value(&contract).expect("slice contract json");
        value["non_claims"][0] = Value::String("already a Stwo proof".into());
        let drifted: ZkAiD64NativeRmsnormSliceContract =
            serde_json::from_value(value).expect("drifted slice contract shape");

        let err = drifted.validate().unwrap_err();
        assert!(err.to_string().contains("non claims mismatch"), "{err}");
    }
}
