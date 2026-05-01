use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

use crate::error::{Result, VmError};

pub const ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION: &str = "zkai-d64-native-export-contract-v1";
pub const ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION: &str =
    "GO_NATIVE_EXPORT_CONTRACT_NOT_AIR_PROOF";
pub const ZKAI_D64_NATIVE_EXPORT_NEXT_BACKEND_STEP: &str =
    "encode this relation oracle as native Stwo AIR/export rows that consume the same public instance";
pub const ZKAI_D64_NATIVE_RELATION_ORACLE_SCHEMA: &str =
    "zkai-d64-native-relation-witness-oracle-v1";
pub const ZKAI_D64_NATIVE_RELATION_ORACLE_DECISION: &str =
    "GO_RELATION_WITNESS_ORACLE_NOT_STWO_PROOF";
pub const ZKAI_D64_TARGET_ID: &str = "rmsnorm-swiglu-residual-d64-v2";
pub const ZKAI_D64_REQUIRED_BACKEND_VERSION: &str = "stwo-rmsnorm-swiglu-residual-d64-v2";
pub const ZKAI_D64_VERIFIER_DOMAIN: &str = "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v2";
pub const ZKAI_D64_WIDTH: usize = 64;
pub const ZKAI_D64_FF_DIM: usize = 256;
pub const ZKAI_D64_INPUT_ROWS: usize = 64;
pub const ZKAI_D64_RMS_SQUARE_ROWS: usize = 64;
pub const ZKAI_D64_RMS_NORM_ROWS: usize = 64;
pub const ZKAI_D64_GATE_PROJECTION_MUL_ROWS: usize = 16_384;
pub const ZKAI_D64_VALUE_PROJECTION_MUL_ROWS: usize = 16_384;
pub const ZKAI_D64_ACTIVATION_LOOKUP_ROWS: usize = 256;
pub const ZKAI_D64_SWIGLU_MIX_ROWS: usize = 256;
pub const ZKAI_D64_DOWN_PROJECTION_MUL_ROWS: usize = 16_384;
pub const ZKAI_D64_RESIDUAL_ROWS: usize = 64;
pub const ZKAI_D64_PROJECTION_MUL_ROWS: usize = 49_152;
pub const ZKAI_D64_TRACE_ROWS_EXCLUDING_STATIC_TABLE: usize = 49_920;
pub const ZKAI_D64_ACTIVATION_TABLE_ROWS: usize = 2_049;
pub const ZKAI_D64_RELATION_CHECKS: usize = 9;
pub const ZKAI_D64_MUTATIONS_CHECKED: usize = 16;
pub const ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT: &str =
    "blake2b-256:861784bd57c039f7fd661810eac42f2aa1893a315ba8e14b441c32717e65efbc";
pub const ZKAI_D64_MODEL_CONFIG_COMMITMENT: &str =
    "blake2b-256:8c74650ddc92619abe50998e3f034312f1e281d5abb35230667518adb493d449";
pub const ZKAI_D64_NORMALIZATION_CONFIG_COMMITMENT: &str =
    "blake2b-256:bfd18a548d24acdf90518744f24e4dd742e68cd2df5f006d3eacc02f3217dc72";
pub const ZKAI_D64_ACTIVATION_LOOKUP_COMMITMENT: &str =
    "blake2b-256:3487a9ab6cd871b7b46e54c004bf547fe9db9ba8e90b3872ba6ae3cfb990c4b3";
pub const ZKAI_D64_INPUT_ACTIVATION_COMMITMENT: &str =
    "blake2b-256:4f765c71601320b3ee9341056299e79a004fa94aaa2edcb5c161cb7366b051fc";
pub const ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT: &str =
    "blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f";
pub const ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT: &str =
    "blake2b-256:ee01ed070eddd5b85990461776834fd827ecd8d37d295fdfa0b2d518b6b6366d";
pub const ZKAI_D64_STATEMENT_COMMITMENT: &str =
    "blake2b-256:9689c4c4e46a62d3f4156c818c1cc146e7312ff91a44f521bd897e806b2f3b38";
pub const ZKAI_D64_RELATION_COMMITMENT: &str =
    "blake2b-256:0903d8b3dd480a59ce2e47e3b4762ca0743794715492caae304d99629bfdb686";

const PUBLIC_INSTANCE_FIELDS: &[&str] = &[
    "activation_lookup_commitment",
    "ff_dim",
    "input_activation_commitment",
    "model_config_commitment",
    "normalization_config_commitment",
    "output_activation_commitment",
    "proof_native_parameter_commitment",
    "target_id",
    "width",
];

const STATEMENT_BINDING_FIELDS: &[&str] = &[
    "backend_version_required",
    "public_instance_commitment",
    "statement_commitment",
    "verifier_domain",
];

const ROW_COUNT_FIELDS: &[&str] = &[
    "activation_lookup_rows",
    "activation_table_rows",
    "down_projection_mul_rows",
    "gate_projection_mul_rows",
    "input_rows",
    "projection_mul_rows",
    "residual_rows",
    "rms_norm_rows",
    "rms_square_rows",
    "swiglu_mix_rows",
    "trace_rows_excluding_static_table",
    "value_projection_mul_rows",
];

const EXPECTED_RELATION_CHECK_NAMES: &[&str] = &[
    "activation_lookup_rows",
    "down_projection_rows",
    "gate_value_projection_rows",
    "proof_native_parameter_manifest_recomputed",
    "public_instance_field_set",
    "public_statement_commitments_recomputed",
    "residual_rows",
    "rmsnorm_rows_recomputed",
    "swiglu_mix_rows",
];

const EXPECTED_MUTATION_NAMES: &[&str] = &[
    "activation_lookup_commitment_relabeling",
    "activation_lookup_output_relabeling",
    "activation_table_root_relabeling",
    "backend_version_relabeling",
    "gate_parameter_root_relabeling",
    "gate_projection_output_relabeling",
    "input_activation_commitment_relabeling",
    "normalization_config_commitment_relabeling",
    "output_activation_commitment_relabeling",
    "proof_native_parameter_commitment_manifest_relabeling",
    "proof_native_parameter_commitment_public_instance_relabeling",
    "public_instance_commitment_relabeling",
    "relation_row_count_relabeling",
    "residual_output_relabeling",
    "rms_scale_root_relabeling",
    "statement_commitment_relabeling",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not a Stwo proof",
    "not verifier-time evidence",
    "not AIR constraints",
    "not backend independence evidence",
    "not full transformer inference",
    "not proof that private witness rows already open to proof_native_parameter_commitment",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RelationCheckRecord {
    pub name: String,
    pub status: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MutationRecord {
    pub name: String,
    pub rejected: bool,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD64NativeExportContract {
    pub contract_version: String,
    pub decision: String,
    pub target_id: String,
    pub width: usize,
    pub ff_dim: usize,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub proof_status: String,
    pub proof_native_parameter_commitment: String,
    pub model_config_commitment: String,
    pub normalization_config_commitment: String,
    pub activation_lookup_commitment: String,
    pub input_activation_commitment: String,
    pub output_activation_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub relation_commitment: String,
    pub projection_mul_rows: usize,
    pub trace_rows_excluding_static_table: usize,
    pub activation_table_rows: usize,
    pub relation_checks: usize,
    pub relation_check_records: Vec<RelationCheckRecord>,
    pub mutations_checked: usize,
    pub mutations_rejected: usize,
    pub mutation_records: Vec<MutationRecord>,
    pub oracle_schema: String,
    pub oracle_decision: String,
    pub non_claims: Vec<String>,
}

impl ZkAiD64NativeExportContract {
    pub fn validate(&self) -> Result<()> {
        expect_eq(
            &self.contract_version,
            ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION,
            "native export contract version",
        )?;
        expect_eq(
            &self.decision,
            ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION,
            "native export contract decision",
        )?;
        expect_eq(&self.target_id, ZKAI_D64_TARGET_ID, "target id")?;
        expect_usize(self.width, ZKAI_D64_WIDTH, "width")?;
        expect_usize(self.ff_dim, ZKAI_D64_FF_DIM, "ff dim")?;
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
            &self.proof_status,
            "REFERENCE_FIXTURE_NOT_PROVEN",
            "proof status",
        )?;
        expect_commitment(
            &self.proof_native_parameter_commitment,
            "proof native parameter",
        )?;
        expect_eq(
            &self.proof_native_parameter_commitment,
            ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT,
            "proof native parameter commitment",
        )?;
        expect_commitment(&self.model_config_commitment, "model config")?;
        expect_eq(
            &self.model_config_commitment,
            ZKAI_D64_MODEL_CONFIG_COMMITMENT,
            "model config commitment",
        )?;
        expect_commitment(
            &self.normalization_config_commitment,
            "normalization config",
        )?;
        expect_eq(
            &self.normalization_config_commitment,
            ZKAI_D64_NORMALIZATION_CONFIG_COMMITMENT,
            "normalization config commitment",
        )?;
        expect_commitment(&self.activation_lookup_commitment, "activation lookup")?;
        expect_eq(
            &self.activation_lookup_commitment,
            ZKAI_D64_ACTIVATION_LOOKUP_COMMITMENT,
            "activation lookup commitment",
        )?;
        expect_commitment(&self.input_activation_commitment, "input activation")?;
        expect_eq(
            &self.input_activation_commitment,
            ZKAI_D64_INPUT_ACTIVATION_COMMITMENT,
            "input activation commitment",
        )?;
        expect_commitment(&self.output_activation_commitment, "output activation")?;
        expect_eq(
            &self.output_activation_commitment,
            ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT,
            "output activation commitment",
        )?;
        expect_commitment(&self.public_instance_commitment, "public instance")?;
        expect_eq(
            &self.public_instance_commitment,
            ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT,
            "public instance commitment",
        )?;
        expect_commitment(&self.statement_commitment, "statement")?;
        expect_eq(
            &self.statement_commitment,
            ZKAI_D64_STATEMENT_COMMITMENT,
            "statement commitment",
        )?;
        expect_commitment(&self.relation_commitment, "relation")?;
        expect_eq(
            &self.relation_commitment,
            ZKAI_D64_RELATION_COMMITMENT,
            "relation commitment",
        )?;
        expect_usize(
            self.projection_mul_rows,
            ZKAI_D64_PROJECTION_MUL_ROWS,
            "projection mul rows",
        )?;
        expect_usize(
            self.trace_rows_excluding_static_table,
            ZKAI_D64_TRACE_ROWS_EXCLUDING_STATIC_TABLE,
            "trace rows excluding static table",
        )?;
        expect_usize(
            self.activation_table_rows,
            ZKAI_D64_ACTIVATION_TABLE_ROWS,
            "activation table rows",
        )?;
        expect_usize(
            self.relation_checks,
            ZKAI_D64_RELATION_CHECKS,
            "relation checks",
        )?;
        validate_relation_check_records(&self.relation_check_records)?;
        expect_usize(
            self.mutations_checked,
            ZKAI_D64_MUTATIONS_CHECKED,
            "mutations checked",
        )?;
        expect_usize(
            self.mutations_rejected,
            ZKAI_D64_MUTATIONS_CHECKED,
            "mutations rejected",
        )?;
        validate_mutation_records(
            &self.mutation_records,
            self.mutations_checked,
            self.mutations_rejected,
        )?;
        expect_eq(
            &self.oracle_schema,
            ZKAI_D64_NATIVE_RELATION_ORACLE_SCHEMA,
            "oracle schema",
        )?;
        expect_eq(
            &self.oracle_decision,
            ZKAI_D64_NATIVE_RELATION_ORACLE_DECISION,
            "oracle decision",
        )?;
        expect_str_set_eq(
            self.non_claims.iter().map(String::as_str),
            EXPECTED_NON_CLAIMS,
            "export contract non claims",
        )?;
        Ok(())
    }
}

pub fn zkai_d64_native_export_contract_from_oracle_json_str(
    raw_oracle_json: &str,
) -> Result<ZkAiD64NativeExportContract> {
    let value: Value = serde_json::from_str(raw_oracle_json)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    zkai_d64_native_export_contract_from_oracle_value(&value)
}

pub fn zkai_d64_native_export_contract_from_oracle_value(
    oracle: &Value,
) -> Result<ZkAiD64NativeExportContract> {
    let root = object_at(oracle, &[], "oracle root")?;
    expect_exact_keys(
        root,
        &[
            "decision",
            "generated_at",
            "git_commit",
            "mutation_suite",
            "next_backend_step",
            "non_claims",
            "relation_witness",
            "schema",
            "source_fixture",
        ],
        "oracle root",
    )?;
    let schema = string_at(oracle, &["schema"])?;
    expect_eq(
        schema,
        ZKAI_D64_NATIVE_RELATION_ORACLE_SCHEMA,
        "oracle schema",
    )?;
    let oracle_decision = string_at(oracle, &["decision"])?;
    expect_eq(
        oracle_decision,
        ZKAI_D64_NATIVE_RELATION_ORACLE_DECISION,
        "oracle decision",
    )?;
    let next_backend_step = string_at(oracle, &["next_backend_step"])?;
    expect_eq(
        next_backend_step,
        ZKAI_D64_NATIVE_EXPORT_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    let non_claims = expect_string_set(oracle, &["non_claims"], EXPECTED_NON_CLAIMS, "non claims")?;

    let witness = object_at(oracle, &["relation_witness"], "relation witness")?;
    expect_exact_keys(
        witness,
        &[
            "parameter_manifest",
            "public_instance",
            "relation_checks",
            "relation_commitment",
            "relation_samples",
            "row_counts",
            "statement_binding",
            "value_ranges",
        ],
        "relation witness",
    )?;

    let public_instance = object_at(
        oracle,
        &["relation_witness", "public_instance"],
        "public instance",
    )?;
    expect_exact_keys(public_instance, PUBLIC_INSTANCE_FIELDS, "public instance")?;
    let statement_binding = object_at(
        oracle,
        &["relation_witness", "statement_binding"],
        "statement binding",
    )?;
    expect_exact_keys(
        statement_binding,
        STATEMENT_BINDING_FIELDS,
        "statement binding",
    )?;
    let row_counts = object_at(oracle, &["relation_witness", "row_counts"], "row counts")?;
    expect_exact_keys(row_counts, ROW_COUNT_FIELDS, "row counts")?;

    let target_id = string_at(
        oracle,
        &["relation_witness", "public_instance", "target_id"],
    )?;
    expect_eq(target_id, ZKAI_D64_TARGET_ID, "public-instance target id")?;
    let width = usize_at(oracle, &["relation_witness", "public_instance", "width"])?;
    expect_usize(width, ZKAI_D64_WIDTH, "public-instance width")?;
    let ff_dim = usize_at(oracle, &["relation_witness", "public_instance", "ff_dim"])?;
    expect_usize(ff_dim, ZKAI_D64_FF_DIM, "public-instance ff dim")?;

    let required_backend_version = string_at(
        oracle,
        &[
            "relation_witness",
            "statement_binding",
            "backend_version_required",
        ],
    )?;
    expect_eq(
        required_backend_version,
        ZKAI_D64_REQUIRED_BACKEND_VERSION,
        "statement backend version",
    )?;
    let verifier_domain = string_at(
        oracle,
        &["relation_witness", "statement_binding", "verifier_domain"],
    )?;
    expect_eq(
        verifier_domain,
        ZKAI_D64_VERIFIER_DOMAIN,
        "statement verifier domain",
    )?;

    let proof_native_parameter_commitment = string_at(
        oracle,
        &[
            "relation_witness",
            "public_instance",
            "proof_native_parameter_commitment",
        ],
    )?;
    expect_eq(
        proof_native_parameter_commitment,
        string_at(
            oracle,
            &[
                "relation_witness",
                "parameter_manifest",
                "proof_native_parameter_commitment",
            ],
        )?,
        "proof-native parameter commitment linkage",
    )?;
    expect_eq(
        proof_native_parameter_commitment,
        string_at(
            oracle,
            &["source_fixture", "proof_native_parameter_commitment"],
        )?,
        "source-fixture proof-native parameter commitment linkage",
    )?;
    let public_instance_commitment = string_at(
        oracle,
        &[
            "relation_witness",
            "statement_binding",
            "public_instance_commitment",
        ],
    )?;
    expect_eq(
        public_instance_commitment,
        string_at(oracle, &["source_fixture", "public_instance_commitment"])?,
        "source-fixture public instance commitment linkage",
    )?;
    let statement_commitment = string_at(
        oracle,
        &[
            "relation_witness",
            "statement_binding",
            "statement_commitment",
        ],
    )?;
    expect_eq(
        statement_commitment,
        string_at(oracle, &["source_fixture", "statement_commitment"])?,
        "source-fixture statement commitment linkage",
    )?;
    expect_eq(
        target_id,
        string_at(oracle, &["source_fixture", "target_id"])?,
        "source-fixture target linkage",
    )?;

    let projection_mul_rows = usize_at(
        oracle,
        &["relation_witness", "row_counts", "projection_mul_rows"],
    )?;
    expect_usize(
        projection_mul_rows,
        ZKAI_D64_PROJECTION_MUL_ROWS,
        "projection mul rows",
    )?;
    let trace_rows_excluding_static_table = usize_at(
        oracle,
        &[
            "relation_witness",
            "row_counts",
            "trace_rows_excluding_static_table",
        ],
    )?;
    expect_usize(
        trace_rows_excluding_static_table,
        ZKAI_D64_TRACE_ROWS_EXCLUDING_STATIC_TABLE,
        "trace rows excluding static table",
    )?;
    let activation_table_rows = usize_at(
        oracle,
        &["relation_witness", "row_counts", "activation_table_rows"],
    )?;
    expect_usize(
        activation_table_rows,
        ZKAI_D64_ACTIVATION_TABLE_ROWS,
        "activation table rows",
    )?;
    validate_row_count_constants(oracle)?;
    validate_projection_row_additivity(oracle)?;
    let relation_check_records = validate_relation_checks(oracle)?;
    let (mutations_checked, mutations_rejected, mutation_records) =
        validate_mutation_suite(oracle)?;

    let contract = ZkAiD64NativeExportContract {
        contract_version: ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION.to_string(),
        decision: ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION.to_string(),
        target_id: target_id.to_string(),
        width,
        ff_dim,
        required_backend_version: required_backend_version.to_string(),
        verifier_domain: verifier_domain.to_string(),
        proof_status: string_at(oracle, &["source_fixture", "proof_status"])?.to_string(),
        proof_native_parameter_commitment: proof_native_parameter_commitment.to_string(),
        model_config_commitment: string_at(
            oracle,
            &[
                "relation_witness",
                "public_instance",
                "model_config_commitment",
            ],
        )?
        .to_string(),
        normalization_config_commitment: string_at(
            oracle,
            &[
                "relation_witness",
                "public_instance",
                "normalization_config_commitment",
            ],
        )?
        .to_string(),
        activation_lookup_commitment: string_at(
            oracle,
            &[
                "relation_witness",
                "public_instance",
                "activation_lookup_commitment",
            ],
        )?
        .to_string(),
        input_activation_commitment: string_at(
            oracle,
            &[
                "relation_witness",
                "public_instance",
                "input_activation_commitment",
            ],
        )?
        .to_string(),
        output_activation_commitment: string_at(
            oracle,
            &[
                "relation_witness",
                "public_instance",
                "output_activation_commitment",
            ],
        )?
        .to_string(),
        public_instance_commitment: public_instance_commitment.to_string(),
        statement_commitment: statement_commitment.to_string(),
        relation_commitment: string_at(oracle, &["relation_witness", "relation_commitment"])?
            .to_string(),
        projection_mul_rows,
        trace_rows_excluding_static_table,
        activation_table_rows,
        relation_checks: EXPECTED_RELATION_CHECK_NAMES.len(),
        relation_check_records,
        mutations_checked,
        mutations_rejected,
        mutation_records,
        oracle_schema: schema.to_string(),
        oracle_decision: oracle_decision.to_string(),
        non_claims,
    };
    contract.validate()?;
    Ok(contract)
}

fn validate_row_count_constants(oracle: &Value) -> Result<()> {
    for (field, expected) in [
        ("input_rows", ZKAI_D64_INPUT_ROWS),
        ("rms_square_rows", ZKAI_D64_RMS_SQUARE_ROWS),
        ("rms_norm_rows", ZKAI_D64_RMS_NORM_ROWS),
        (
            "gate_projection_mul_rows",
            ZKAI_D64_GATE_PROJECTION_MUL_ROWS,
        ),
        (
            "value_projection_mul_rows",
            ZKAI_D64_VALUE_PROJECTION_MUL_ROWS,
        ),
        ("activation_lookup_rows", ZKAI_D64_ACTIVATION_LOOKUP_ROWS),
        ("swiglu_mix_rows", ZKAI_D64_SWIGLU_MIX_ROWS),
        (
            "down_projection_mul_rows",
            ZKAI_D64_DOWN_PROJECTION_MUL_ROWS,
        ),
        ("residual_rows", ZKAI_D64_RESIDUAL_ROWS),
        ("projection_mul_rows", ZKAI_D64_PROJECTION_MUL_ROWS),
        (
            "trace_rows_excluding_static_table",
            ZKAI_D64_TRACE_ROWS_EXCLUDING_STATIC_TABLE,
        ),
        ("activation_table_rows", ZKAI_D64_ACTIVATION_TABLE_ROWS),
    ] {
        expect_usize(
            usize_at(oracle, &["relation_witness", "row_counts", field])?,
            expected,
            field,
        )?;
    }
    Ok(())
}

fn validate_projection_row_additivity(oracle: &Value) -> Result<()> {
    let gate = usize_at(
        oracle,
        &["relation_witness", "row_counts", "gate_projection_mul_rows"],
    )?;
    let value = usize_at(
        oracle,
        &[
            "relation_witness",
            "row_counts",
            "value_projection_mul_rows",
        ],
    )?;
    let down = usize_at(
        oracle,
        &["relation_witness", "row_counts", "down_projection_mul_rows"],
    )?;
    let projection = usize_at(
        oracle,
        &["relation_witness", "row_counts", "projection_mul_rows"],
    )?;
    if gate + value + down != projection {
        return Err(contract_error(format!(
            "projection row additivity mismatch: {gate} + {value} + {down} != {projection}"
        )));
    }
    let trace = usize_at(
        oracle,
        &[
            "relation_witness",
            "row_counts",
            "trace_rows_excluding_static_table",
        ],
    )?;
    let trace_parts = [
        "input_rows",
        "rms_square_rows",
        "rms_norm_rows",
        "gate_projection_mul_rows",
        "value_projection_mul_rows",
        "activation_lookup_rows",
        "swiglu_mix_rows",
        "down_projection_mul_rows",
        "residual_rows",
    ];
    let mut sum = 0usize;
    for part in trace_parts {
        sum += usize_at(oracle, &["relation_witness", "row_counts", part])?;
    }
    if sum != trace {
        return Err(contract_error(format!(
            "trace row additivity mismatch: {sum} != {trace}"
        )));
    }
    Ok(())
}

fn validate_relation_checks(oracle: &Value) -> Result<Vec<RelationCheckRecord>> {
    let checks = array_at(oracle, &["relation_witness", "relation_checks"])?;
    if checks.len() != EXPECTED_RELATION_CHECK_NAMES.len() {
        return Err(contract_error(format!(
            "relation check count mismatch: got {}, expected {}",
            checks.len(),
            EXPECTED_RELATION_CHECK_NAMES.len()
        )));
    }
    let mut records = Vec::with_capacity(checks.len());
    let mut names = BTreeSet::new();
    for check in checks {
        let name = string_field(check, "name", "relation check")?;
        let status = string_field(check, "status", "relation check")?;
        if status != "GO" {
            return Err(contract_error(format!(
                "relation check {name} has non-GO status {status}"
            )));
        }
        names.insert(name.to_string());
        records.push(RelationCheckRecord {
            name: name.to_string(),
            status: status.to_string(),
        });
    }
    expect_set_eq(names, EXPECTED_RELATION_CHECK_NAMES, "relation check names")?;
    Ok(records)
}

fn validate_mutation_suite(oracle: &Value) -> Result<(usize, usize, Vec<MutationRecord>)> {
    let suite = object_at(oracle, &["mutation_suite"], "mutation suite")?;
    expect_exact_keys(
        suite,
        &[
            "baseline_valid",
            "cases",
            "decision",
            "mutations_checked",
            "mutations_rejected",
        ],
        "mutation suite",
    )?;
    if !bool_at(oracle, &["mutation_suite", "baseline_valid"])? {
        return Err(contract_error("mutation suite baseline is not valid"));
    }
    expect_eq(
        string_at(oracle, &["mutation_suite", "decision"])?,
        "GO",
        "mutation suite decision",
    )?;
    let mutations_checked = usize_at(oracle, &["mutation_suite", "mutations_checked"])?;
    let mutations_rejected = usize_at(oracle, &["mutation_suite", "mutations_rejected"])?;
    expect_usize(
        mutations_checked,
        EXPECTED_MUTATION_NAMES.len(),
        "mutations checked",
    )?;
    expect_usize(
        mutations_rejected,
        EXPECTED_MUTATION_NAMES.len(),
        "mutations rejected",
    )?;

    let cases = array_at(oracle, &["mutation_suite", "cases"])?;
    if cases.len() != EXPECTED_MUTATION_NAMES.len() {
        return Err(contract_error(format!(
            "mutation case count mismatch: got {}, expected {}",
            cases.len(),
            EXPECTED_MUTATION_NAMES.len()
        )));
    }
    let mut records = Vec::with_capacity(cases.len());
    let mut names = BTreeSet::new();
    for case in cases {
        let name = string_field(case, "name", "mutation case")?;
        if !bool_field(case, "rejected", "mutation case")? {
            return Err(contract_error(format!("mutation case {name} was accepted")));
        }
        let reason = string_field(case, "reason", "mutation case")?;
        if reason == "accepted" || reason.is_empty() {
            return Err(contract_error(format!(
                "mutation case {name} has invalid rejection reason"
            )));
        }
        names.insert(name.to_string());
        records.push(MutationRecord {
            name: name.to_string(),
            rejected: true,
            reason: reason.to_string(),
        });
    }
    expect_set_eq(names, EXPECTED_MUTATION_NAMES, "mutation names")?;
    Ok((mutations_checked, mutations_rejected, records))
}

fn validate_relation_check_records(records: &[RelationCheckRecord]) -> Result<()> {
    if records.len() != EXPECTED_RELATION_CHECK_NAMES.len() {
        return Err(contract_error(format!(
            "relation check record count mismatch: got {}, expected {}",
            records.len(),
            EXPECTED_RELATION_CHECK_NAMES.len()
        )));
    }
    let mut names = BTreeSet::new();
    for record in records {
        if record.status != "GO" {
            return Err(contract_error(format!(
                "relation check {} has non-GO status {}",
                record.name, record.status
            )));
        }
        names.insert(record.name.clone());
    }
    expect_set_eq(
        names,
        EXPECTED_RELATION_CHECK_NAMES,
        "relation check record names",
    )
}

fn validate_mutation_records(
    records: &[MutationRecord],
    mutations_checked: usize,
    mutations_rejected: usize,
) -> Result<()> {
    expect_usize(
        mutations_checked,
        EXPECTED_MUTATION_NAMES.len(),
        "mutation record checked count",
    )?;
    expect_usize(
        mutations_rejected,
        EXPECTED_MUTATION_NAMES.len(),
        "mutation record rejected count",
    )?;
    if records.len() != EXPECTED_MUTATION_NAMES.len() {
        return Err(contract_error(format!(
            "mutation record count mismatch: got {}, expected {}",
            records.len(),
            EXPECTED_MUTATION_NAMES.len()
        )));
    }
    let mut names = BTreeSet::new();
    for record in records {
        if !record.rejected {
            return Err(contract_error(format!(
                "mutation record {} was accepted",
                record.name
            )));
        }
        if record.reason.is_empty() || record.reason == "accepted" {
            return Err(contract_error(format!(
                "mutation record {} has invalid rejection reason",
                record.name
            )));
        }
        names.insert(record.name.clone());
    }
    expect_set_eq(names, EXPECTED_MUTATION_NAMES, "mutation record names")
}

fn object_at<'a>(value: &'a Value, path: &[&str], label: &str) -> Result<&'a Map<String, Value>> {
    let mut cursor = value;
    for key in path {
        cursor = cursor
            .get(*key)
            .ok_or_else(|| contract_error(format!("{label} missing field {key}")))?;
    }
    cursor
        .as_object()
        .ok_or_else(|| contract_error(format!("{label} must be an object")))
}

fn array_at<'a>(value: &'a Value, path: &[&str]) -> Result<&'a Vec<Value>> {
    let cursor = value_at(value, path)?;
    cursor
        .as_array()
        .ok_or_else(|| contract_error(format!("{} must be an array", path.join("."))))
}

fn value_at<'a>(value: &'a Value, path: &[&str]) -> Result<&'a Value> {
    let mut cursor = value;
    for key in path {
        cursor = cursor
            .get(*key)
            .ok_or_else(|| contract_error(format!("missing field {}", path.join("."))))?;
    }
    Ok(cursor)
}

fn string_at<'a>(value: &'a Value, path: &[&str]) -> Result<&'a str> {
    value_at(value, path)?
        .as_str()
        .ok_or_else(|| contract_error(format!("{} must be a string", path.join("."))))
}

fn usize_at(value: &Value, path: &[&str]) -> Result<usize> {
    let raw = value_at(value, path)?
        .as_u64()
        .ok_or_else(|| contract_error(format!("{} must be an unsigned integer", path.join("."))))?;
    usize::try_from(raw).map_err(|_| contract_error(format!("{} exceeds usize", path.join("."))))
}

fn bool_at(value: &Value, path: &[&str]) -> Result<bool> {
    value_at(value, path)?
        .as_bool()
        .ok_or_else(|| contract_error(format!("{} must be a bool", path.join("."))))
}

fn string_field<'a>(value: &'a Value, key: &str, label: &str) -> Result<&'a str> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| contract_error(format!("{label} field {key} must be a string")))
}

fn bool_field(value: &Value, key: &str, label: &str) -> Result<bool> {
    value
        .get(key)
        .and_then(Value::as_bool)
        .ok_or_else(|| contract_error(format!("{label} field {key} must be a bool")))
}

fn expect_string_set(
    value: &Value,
    path: &[&str],
    expected: &[&str],
    label: &str,
) -> Result<Vec<String>> {
    let items = array_at(value, path)?;
    let actual: Vec<&str> = items
        .iter()
        .map(|item| {
            item.as_str()
                .ok_or_else(|| contract_error(format!("{label} item must be a string")))
        })
        .collect::<Result<_>>()?;
    expect_str_set_eq(actual.iter().copied(), expected, label)?;
    Ok(actual.into_iter().map(str::to_string).collect())
}

fn expect_str_set_eq<'a>(
    actual: impl IntoIterator<Item = &'a str>,
    expected: &[&str],
    label: &str,
) -> Result<()> {
    let actual_vec: Vec<&str> = actual.into_iter().collect();
    if actual_vec.len() != expected.len() {
        return Err(contract_error(format!(
            "{label} count mismatch: got {}, expected {}",
            actual_vec.len(),
            expected.len()
        )));
    }
    let actual_set: BTreeSet<String> = actual_vec.iter().map(|item| item.to_string()).collect();
    if actual_set.len() != actual_vec.len() {
        return Err(contract_error(format!("{label} contains duplicates")));
    }
    let expected_set: BTreeSet<String> = expected.iter().map(|item| item.to_string()).collect();
    if actual_set != expected_set {
        return Err(contract_error(format!(
            "{label} mismatch: got {:?}, expected {:?}",
            actual_set, expected_set
        )));
    }
    Ok(())
}

fn expect_exact_keys(object: &Map<String, Value>, expected: &[&str], label: &str) -> Result<()> {
    let actual: BTreeSet<String> = object.keys().cloned().collect();
    expect_set_eq(actual, expected, label)
}

fn expect_set_eq(actual: BTreeSet<String>, expected: &[&str], label: &str) -> Result<()> {
    let expected_set: BTreeSet<String> = expected.iter().map(|item| item.to_string()).collect();
    if actual != expected_set {
        return Err(contract_error(format!(
            "{label} mismatch: got {:?}, expected {:?}",
            actual, expected_set
        )));
    }
    Ok(())
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(contract_error(format!(
            "{label} mismatch: got {actual:?}, expected {expected:?}"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(contract_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_commitment(value: &str, label: &str) -> Result<()> {
    let Some(hex) = value.strip_prefix("blake2b-256:") else {
        return Err(contract_error(format!(
            "{label} commitment uses wrong scheme"
        )));
    };
    if hex.len() != 64
        || !hex
            .chars()
            .all(|ch| ch.is_ascii_hexdigit() && !ch.is_ascii_uppercase())
    {
        return Err(contract_error(format!(
            "{label} commitment is not lowercase 32-byte hex"
        )));
    }
    Ok(())
}

fn contract_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!("d64 native export contract: {}", message.into()))
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
    fn native_export_contract_consumes_oracle_evidence() {
        let contract =
            zkai_d64_native_export_contract_from_oracle_json_str(ORACLE_JSON).expect("contract");

        assert_eq!(
            contract.contract_version,
            ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION
        );
        assert_eq!(contract.decision, ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION);
        assert_eq!(contract.target_id, ZKAI_D64_TARGET_ID);
        assert_eq!(contract.width, ZKAI_D64_WIDTH);
        assert_eq!(contract.ff_dim, ZKAI_D64_FF_DIM);
        assert_eq!(
            contract.required_backend_version,
            ZKAI_D64_REQUIRED_BACKEND_VERSION
        );
        assert_eq!(contract.projection_mul_rows, ZKAI_D64_PROJECTION_MUL_ROWS);
        assert_eq!(
            contract.trace_rows_excluding_static_table,
            ZKAI_D64_TRACE_ROWS_EXCLUDING_STATIC_TABLE
        );
        assert_eq!(
            contract.activation_table_rows,
            ZKAI_D64_ACTIVATION_TABLE_ROWS
        );
        assert_eq!(contract.mutations_checked, ZKAI_D64_MUTATIONS_CHECKED);
        assert_eq!(contract.mutations_rejected, ZKAI_D64_MUTATIONS_CHECKED);
        assert_eq!(
            contract.relation_check_records.len(),
            ZKAI_D64_RELATION_CHECKS
        );
        assert_eq!(contract.mutation_records.len(), ZKAI_D64_MUTATIONS_CHECKED);
        contract.validate().expect("contract validates");
    }

    #[test]
    fn native_export_contract_rejects_public_instance_drift() {
        for path in [
            &[
                "relation_witness",
                "public_instance",
                "proof_native_parameter_commitment",
            ][..],
            &[
                "relation_witness",
                "public_instance",
                "normalization_config_commitment",
            ],
            &[
                "relation_witness",
                "public_instance",
                "activation_lookup_commitment",
            ],
            &["relation_witness", "public_instance", "target_id"],
        ] {
            let value = mutate(
                path,
                Value::String("blake2b-256:".to_string() + &"77".repeat(32)),
            );
            let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
            assert!(
                err.to_string().contains("d64 native export contract"),
                "{err}"
            );
        }
    }

    #[test]
    fn native_export_contract_rejects_statement_binding_drift() {
        for path in [
            &[
                "relation_witness",
                "statement_binding",
                "backend_version_required",
            ][..],
            &[
                "relation_witness",
                "statement_binding",
                "public_instance_commitment",
            ],
            &[
                "relation_witness",
                "statement_binding",
                "statement_commitment",
            ],
            &["relation_witness", "statement_binding", "verifier_domain"],
        ] {
            let value = mutate(path, Value::String("wrong".to_string()));
            let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
            assert!(
                err.to_string().contains("d64 native export contract"),
                "{err}"
            );
        }
    }

    #[test]
    fn native_export_contract_rejects_row_count_drift() {
        for path in [
            &["relation_witness", "row_counts", "projection_mul_rows"][..],
            &[
                "relation_witness",
                "row_counts",
                "trace_rows_excluding_static_table",
            ],
            &["relation_witness", "row_counts", "activation_table_rows"],
            &["relation_witness", "row_counts", "gate_projection_mul_rows"],
        ] {
            let value = mutate(path, Value::from(1u64));
            let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
            assert!(
                err.to_string().contains("row") || err.to_string().contains("additivity"),
                "{err}"
            );
        }
    }

    #[test]
    fn native_export_contract_rejects_balanced_row_count_drift() {
        let mut value = oracle_value();
        value["relation_witness"]["row_counts"]["input_rows"] = Value::from(65u64);
        value["relation_witness"]["row_counts"]["residual_rows"] = Value::from(63u64);

        let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("input_rows"), "{err}");
    }

    #[test]
    fn native_export_contract_rejects_relation_check_drift() {
        let mut value = oracle_value();
        value["relation_witness"]["relation_checks"][0]["name"] = Value::String("weaker".into());

        let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("relation check names"), "{err}");
    }

    #[test]
    fn native_export_contract_rejects_mutation_suite_drift() {
        let mut value = oracle_value();
        value["mutation_suite"]["cases"][0]["rejected"] = Value::Bool(false);

        let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("was accepted"), "{err}");

        let mut value = oracle_value();
        value["mutation_suite"]["mutations_rejected"] = Value::from(15u64);
        let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("mutations rejected"), "{err}");
    }

    #[test]
    fn native_export_contract_rejects_non_claim_drift() {
        let mut value = oracle_value();
        value["non_claims"][2] = Value::String("already AIR constraints".into());

        let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("non claims mismatch"), "{err}");
    }

    #[test]
    fn native_export_contract_rejects_missing_export_non_claim_caveat() {
        let mut value = oracle_value();
        let array = value["non_claims"]
            .as_array_mut()
            .expect("non claims array");
        array.retain(|item| {
            item.as_str()
                != Some(
                    "not proof that private witness rows already open to proof_native_parameter_commitment",
                )
        });

        let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("non claims count"), "{err}");
    }

    #[test]
    fn native_export_contract_rejects_next_backend_step_drift() {
        let value = mutate(
            &["next_backend_step"],
            Value::String("claim this is already native AIR".into()),
        );

        let err = zkai_d64_native_export_contract_from_oracle_value(&value).unwrap_err();
        assert!(err.to_string().contains("next backend step"), "{err}");
    }

    #[test]
    fn native_export_contract_accepts_oracle_non_claim_reordering() {
        let mut value = oracle_value();
        let array = value["non_claims"]
            .as_array_mut()
            .expect("non claims array");
        let first = array.remove(0);
        array.push(first);

        zkai_d64_native_export_contract_from_oracle_value(&value)
            .expect("set-equivalent non claims accepted");
    }

    #[test]
    fn native_export_contract_round_trip_rejects_relation_record_drift() {
        let contract =
            zkai_d64_native_export_contract_from_oracle_json_str(ORACLE_JSON).expect("contract");
        let mut value = serde_json::to_value(&contract).expect("contract json");
        value["relation_check_records"][0]["name"] = Value::String("weaker_check".into());
        let drifted: ZkAiD64NativeExportContract =
            serde_json::from_value(value).expect("drifted contract json shape");

        let err = drifted.validate().unwrap_err();
        assert!(
            err.to_string().contains("relation check record names"),
            "{err}"
        );
    }

    #[test]
    fn native_export_contract_round_trip_rejects_mutation_record_drift() {
        let contract =
            zkai_d64_native_export_contract_from_oracle_json_str(ORACLE_JSON).expect("contract");
        let mut value = serde_json::to_value(&contract).expect("contract json");
        value["mutation_records"][0]["rejected"] = Value::Bool(false);
        let drifted: ZkAiD64NativeExportContract =
            serde_json::from_value(value).expect("drifted contract json shape");

        let err = drifted.validate().unwrap_err();
        assert!(err.to_string().contains("was accepted"), "{err}");
    }
}
