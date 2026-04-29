use std::collections::{BTreeSet, HashMap};
use std::fmt;
use std::fs::{self, File};
use std::io::Read;
use std::path::Path;

use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::{Number, Value};
use unicode_normalization::UnicodeNormalization;

use crate::error::{Result, VmError};

pub const AGENT_STEP_RECEIPT_VERSION_V1: &str = "agent-step-receipt-v1";
pub const AGENT_STEP_RECEIPT_PARSER_VERSION_V1: &str = "agent-step-receipt-parser-v1";
pub const AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN: &str = "agent-step-receipt-test-domain";
pub const AGENT_STEP_RECEIPT_STWO_TEST_BACKEND_VERSION: &str = "stwo-agent-step-test-proof-v1";
pub const AGENT_EVIDENCE_MANIFEST_VERSION_V1: &str = "agent-step-evidence-manifest-v1";
pub const AGENT_DEPENDENCY_DROP_MANIFEST_VERSION_V1: &str =
    "agent-step-dependency-drop-manifest-v1";

const MAX_AGENT_STEP_RECEIPT_BUNDLE_JSON_BYTES: usize = 1024 * 1024;

const RECEIPT_FIELDS: &[&str] = &[
    "receipt_version",
    "verifier_domain",
    "runtime_domain",
    "proof_backend",
    "proof_backend_version",
    "receipt_parser_version",
    "prior_state_commitment",
    "observation_commitment",
    "model_identity",
    "model_commitment",
    "model_config_commitment",
    "model_receipt_commitment",
    "tool_receipts_root",
    "policy_commitment",
    "action_commitment",
    "next_state_commitment",
    "transcript_commitment",
    "dependency_drop_manifest_commitment",
    "evidence_manifest_commitment",
    "field_trust_class_vector",
    "receipt_commitment",
];

const SELF_BOUND_FIELDS: &[&str] = &[
    "/dependency_drop_manifest_commitment",
    "/evidence_manifest_commitment",
    "/field_trust_class_vector",
    "/receipt_commitment",
];

const COMMITMENT_FIELDS: &[&str] = &[
    "prior_state_commitment",
    "observation_commitment",
    "model_commitment",
    "model_config_commitment",
    "model_receipt_commitment",
    "tool_receipts_root",
    "policy_commitment",
    "action_commitment",
    "next_state_commitment",
    "transcript_commitment",
    "dependency_drop_manifest_commitment",
    "evidence_manifest_commitment",
    "receipt_commitment",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentStepReceiptBundleV1 {
    pub receipt: AgentStepReceiptV1,
    pub evidence_manifest: AgentEvidenceManifestV1,
    pub dependency_drop_manifest: AgentDependencyDropManifestV1,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentStepReceiptV1 {
    pub receipt_version: String,
    pub verifier_domain: String,
    pub runtime_domain: String,
    pub proof_backend: String,
    pub proof_backend_version: String,
    pub receipt_parser_version: String,
    pub prior_state_commitment: String,
    pub observation_commitment: String,
    pub model_identity: String,
    pub model_commitment: String,
    pub model_config_commitment: String,
    pub model_receipt_commitment: String,
    pub tool_receipts_root: Option<String>,
    pub policy_commitment: Option<String>,
    pub action_commitment: String,
    pub next_state_commitment: String,
    pub transcript_commitment: Option<String>,
    pub dependency_drop_manifest_commitment: String,
    pub evidence_manifest_commitment: String,
    pub field_trust_class_vector: Vec<AgentFieldTrustClassV1>,
    pub receipt_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentFieldTrustClassV1 {
    pub field_path: String,
    pub trust_class: AgentTrustClass,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentEvidenceManifestV1 {
    pub manifest_version: String,
    pub entries: Vec<AgentEvidenceEntryV1>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentEvidenceEntryV1 {
    pub evidence_id: String,
    pub evidence_kind: AgentEvidenceKind,
    pub commitment: String,
    pub trust_class: AgentTrustClass,
    pub verifier_domain: String,
    pub corresponding_receipt_field: String,
    pub non_claims: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentDependencyDropManifestV1 {
    pub manifest_version: String,
    pub entries: Vec<AgentDependencyDropEntryV1>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentDependencyDropEntryV1 {
    pub dependency_id: String,
    pub dependency_kind: AgentDependencyKind,
    pub source_commitment: String,
    pub replacement_commitment: String,
    pub replacement_receipt_version: String,
    pub trust_class: AgentTrustClass,
    pub verifier_domain: String,
    pub corresponding_receipt_field: String,
    pub reason_for_drop: String,
    pub required_subproof_or_attestation: Option<AgentRequiredSubfactV1>,
    pub non_claims: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentRequiredSubfactV1 {
    pub kind: AgentRequiredSubfactKind,
    pub commitment: String,
    pub verifier_domain: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AgentTrustClass {
    Omitted,
    Attested,
    Replayed,
    DependencyDropped,
    Proved,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AgentEvidenceKind {
    Proof,
    Attestation,
    ReplaySource,
    Subreceipt,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AgentDependencyKind {
    SourceManifest,
    ProofTrace,
    ModelReceipt,
    ToolReceipt,
    StateCommitment,
    PolicyCommitment,
    Transcript,
    Other,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AgentRequiredSubfactKind {
    Proof,
    Attestation,
    Subreceipt,
}

impl AgentTrustClass {
    fn rank(self) -> u8 {
        match self {
            Self::Omitted => 0,
            Self::Attested => 1,
            Self::Replayed => 2,
            Self::DependencyDropped => 3,
            Self::Proved => 4,
        }
    }
}

impl fmt::Display for AgentTrustClass {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let value = match self {
            Self::Omitted => "omitted",
            Self::Attested => "attested",
            Self::Replayed => "replayed",
            Self::DependencyDropped => "dependency_dropped",
            Self::Proved => "proved",
        };
        f.write_str(value)
    }
}

pub fn parse_agent_step_receipt_bundle_v1_json(json: &str) -> Result<AgentStepReceiptBundleV1> {
    if json.len() > MAX_AGENT_STEP_RECEIPT_BUNDLE_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 bundle JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_AGENT_STEP_RECEIPT_BUNDLE_JSON_BYTES
        )));
    }
    let value = parse_strict_json_value(json)?;
    let bundle: AgentStepReceiptBundleV1 =
        serde_json::from_value(value).map_err(agent_receipt_json_error)?;
    verify_agent_step_receipt_bundle_v1(&bundle)?;
    Ok(bundle)
}

pub fn load_agent_step_receipt_bundle_v1(path: &Path) -> Result<AgentStepReceiptBundleV1> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_AGENT_STEP_RECEIPT_BUNDLE_JSON_BYTES,
        "AgentStepReceiptV1 bundle",
    )?;
    let json = std::str::from_utf8(&bytes).map_err(|err| {
        VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 bundle is not UTF-8 JSON: {err}"
        ))
    })?;
    parse_agent_step_receipt_bundle_v1_json(json)
}

pub fn verify_agent_step_receipt_bundle_v1(bundle: &AgentStepReceiptBundleV1) -> Result<()> {
    if bundle.receipt.receipt_version != AGENT_STEP_RECEIPT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 receipt_version `{}` is unsupported",
            bundle.receipt.receipt_version
        )));
    }
    if bundle.receipt.verifier_domain != AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 verifier_domain `{}` is unsupported",
            bundle.receipt.verifier_domain
        )));
    }
    if bundle.receipt.receipt_parser_version != AGENT_STEP_RECEIPT_PARSER_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 receipt_parser_version `{}` is unsupported",
            bundle.receipt.receipt_parser_version
        )));
    }
    if (
        bundle.receipt.proof_backend.as_str(),
        bundle.receipt.proof_backend_version.as_str(),
    ) != ("stwo", AGENT_STEP_RECEIPT_STWO_TEST_BACKEND_VERSION)
    {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 proof backend `{}` version `{}` is unsupported",
            bundle.receipt.proof_backend, bundle.receipt.proof_backend_version
        )));
    }

    validate_schema_version(&bundle.receipt.receipt_version, "receipt_version")?;
    validate_schema_version(
        &bundle.receipt.receipt_parser_version,
        "receipt_parser_version",
    )?;
    validate_schema_version(&bundle.receipt.proof_backend, "proof_backend")?;
    validate_schema_version(
        &bundle.receipt.proof_backend_version,
        "proof_backend_version",
    )?;
    validate_schema_version(&bundle.receipt.verifier_domain, "verifier_domain")?;

    validate_receipt_commitment_fields(&bundle.receipt)?;

    let expected_dependency_commitment =
        commit_agent_dependency_drop_manifest_v1(&bundle.dependency_drop_manifest)?;
    if bundle.receipt.dependency_drop_manifest_commitment != expected_dependency_commitment {
        return Err(VmError::InvalidConfig(
            "AgentStepReceiptV1 dependency_drop_manifest_commitment mismatch".to_string(),
        ));
    }
    let expected_evidence_commitment =
        commit_agent_evidence_manifest_v1(&bundle.evidence_manifest)?;
    if bundle.receipt.evidence_manifest_commitment != expected_evidence_commitment {
        return Err(VmError::InvalidConfig(
            "AgentStepReceiptV1 evidence_manifest_commitment mismatch".to_string(),
        ));
    }

    let receipt_value = serde_json::to_value(&bundle.receipt)
        .map_err(|err| VmError::Serialization(format!("AgentStepReceiptV1 receipt: {err}")))?;
    let trust_by_field = validate_trust_vector(&bundle.receipt, &receipt_value)?;
    let evidence_by_field =
        validate_evidence_manifest(&bundle.evidence_manifest, &receipt_value, &trust_by_field)?;
    let dependency_by_field =
        validate_dependency_drop_manifest(&bundle.dependency_drop_manifest, &trust_by_field)?;

    validate_field_support(
        &receipt_value,
        &trust_by_field,
        &evidence_by_field,
        &dependency_by_field,
    )?;

    let expected_receipt_commitment = commit_agent_step_receipt_v1(&bundle.receipt)?;
    if bundle.receipt.receipt_commitment != expected_receipt_commitment {
        return Err(VmError::InvalidConfig(
            "AgentStepReceiptV1 receipt_commitment mismatch".to_string(),
        ));
    }
    Ok(())
}

pub fn commit_agent_step_receipt_v1(receipt: &AgentStepReceiptV1) -> Result<String> {
    let mut value = serde_json::to_value(receipt)
        .map_err(|err| VmError::Serialization(format!("AgentStepReceiptV1 receipt: {err}")))?;
    value["receipt_commitment"] = Value::Null;
    commitment_for_value(&value, "agent-step-receipt-v1.receipt")
}

pub fn commit_agent_evidence_manifest_v1(manifest: &AgentEvidenceManifestV1) -> Result<String> {
    let value = serde_json::to_value(manifest).map_err(|err| {
        VmError::Serialization(format!("AgentStepReceiptV1 evidence manifest: {err}"))
    })?;
    commitment_for_value(&value, "agent-step-receipt-v1.evidence-manifest")
}

pub fn commit_agent_dependency_drop_manifest_v1(
    manifest: &AgentDependencyDropManifestV1,
) -> Result<String> {
    let value = serde_json::to_value(manifest).map_err(|err| {
        VmError::Serialization(format!(
            "AgentStepReceiptV1 dependency-drop manifest: {err}"
        ))
    })?;
    commitment_for_value(&value, "agent-step-receipt-v1.dependency-drop-manifest")
}

fn validate_receipt_commitment_fields(receipt: &AgentStepReceiptV1) -> Result<()> {
    let value = serde_json::to_value(receipt)
        .map_err(|err| VmError::Serialization(format!("AgentStepReceiptV1 receipt: {err}")))?;
    for field in COMMITMENT_FIELDS {
        let Some(raw) = value.get(*field) else {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 receipt is missing `{field}`"
            )));
        };
        if raw.is_null() {
            continue;
        }
        let Some(commitment) = raw.as_str() else {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 `{field}` must be a commitment string or null"
            )));
        };
        validate_commitment(commitment, field)?;
    }
    Ok(())
}

fn validate_trust_vector(
    receipt: &AgentStepReceiptV1,
    receipt_value: &Value,
) -> Result<HashMap<String, AgentTrustClass>> {
    let expected_paths = sort_utf8(
        RECEIPT_FIELDS
            .iter()
            .map(|field| json_pointer_for_field(field))
            .collect(),
    );
    let mut observed_paths = Vec::with_capacity(receipt.field_trust_class_vector.len());
    let mut trust_by_field = HashMap::new();
    for entry in &receipt.field_trust_class_vector {
        validate_field_path(&entry.field_path)?;
        let field = field_from_pointer(&entry.field_path)?;
        if receipt_value.get(field).is_none() {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 trust vector names absent field {}",
                entry.field_path
            )));
        }
        if trust_by_field
            .insert(entry.field_path.clone(), entry.trust_class)
            .is_some()
        {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 duplicate trust vector path {}",
                entry.field_path
            )));
        }
        observed_paths.push(entry.field_path.clone());
    }
    let sorted_observed = sort_utf8(observed_paths.clone());
    if observed_paths != sorted_observed {
        return Err(VmError::InvalidConfig(
            "AgentStepReceiptV1 field_trust_class_vector is not sorted by field path bytes"
                .to_string(),
        ));
    }
    if observed_paths != expected_paths {
        return Err(VmError::InvalidConfig(
            "AgentStepReceiptV1 field_trust_class_vector does not cover every receipt field"
                .to_string(),
        ));
    }
    for (path, trust_class) in &trust_by_field {
        validate_allowed_trust_class(path, *trust_class)?;
        if SELF_BOUND_FIELDS.contains(&path.as_str()) && *trust_class != AgentTrustClass::Replayed {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 self-bound field {path} must be replayed"
            )));
        }
        let field = field_from_pointer(path)?;
        let value = receipt_value.get(field).ok_or_else(|| {
            VmError::InvalidConfig(format!("AgentStepReceiptV1 receipt field {path} is absent"))
        })?;
        match trust_class {
            AgentTrustClass::Omitted => {
                if !value.is_null() {
                    return Err(VmError::InvalidConfig(format!(
                        "AgentStepReceiptV1 omitted field {path} must be null"
                    )));
                }
            }
            _ if value.is_null() => {
                return Err(VmError::InvalidConfig(format!(
                    "AgentStepReceiptV1 non-omitted field {path} must not be null"
                )));
            }
            _ => {}
        }
    }
    Ok(trust_by_field)
}

fn validate_evidence_manifest(
    manifest: &AgentEvidenceManifestV1,
    receipt_value: &Value,
    trust_by_field: &HashMap<String, AgentTrustClass>,
) -> Result<HashMap<String, Vec<AgentEvidenceEntryV1>>> {
    if manifest.manifest_version != AGENT_EVIDENCE_MANIFEST_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 evidence manifest version `{}` is unsupported",
            manifest.manifest_version
        )));
    }
    let ids: Vec<String> = manifest
        .entries
        .iter()
        .map(|entry| entry.evidence_id.clone())
        .collect();
    validate_sorted_unique(&ids, "AgentStepReceiptV1 evidence_id")?;

    let mut by_field: HashMap<String, Vec<AgentEvidenceEntryV1>> = HashMap::new();
    for entry in &manifest.entries {
        validate_evidence_id(&entry.evidence_id)?;
        validate_commitment(&entry.commitment, "AgentStepReceiptV1 evidence commitment")?;
        validate_sorted_unique(&entry.non_claims, "AgentStepReceiptV1 evidence non_claims")?;
        if entry.verifier_domain != AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 evidence verifier domain mismatch".to_string(),
            ));
        }
        validate_field_path(&entry.corresponding_receipt_field)?;
        if SELF_BOUND_FIELDS.contains(&entry.corresponding_receipt_field.as_str()) {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 evidence points at self-bound receipt field".to_string(),
            ));
        }
        let trust_class = trust_by_field
            .get(&entry.corresponding_receipt_field)
            .ok_or_else(|| {
                VmError::InvalidConfig(
                    "AgentStepReceiptV1 evidence points at unknown receipt field".to_string(),
                )
            })?;
        if *trust_class == AgentTrustClass::Omitted {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 evidence points at omitted receipt field".to_string(),
            ));
        }
        if entry.trust_class == AgentTrustClass::Omitted {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 positive evidence cannot use omitted trust class".to_string(),
            ));
        }
        let field = field_from_pointer(&entry.corresponding_receipt_field)?;
        let value = receipt_value.get(field).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 evidence points at absent receipt field {}",
                entry.corresponding_receipt_field
            ))
        })?;
        let expected = evidence_commitment_for_field(&entry.corresponding_receipt_field, value)?;
        if entry.commitment != expected {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 evidence commitment does not bind {}",
                entry.corresponding_receipt_field
            )));
        }
        by_field
            .entry(entry.corresponding_receipt_field.clone())
            .or_default()
            .push(entry.clone());
    }
    Ok(by_field)
}

fn validate_dependency_drop_manifest(
    manifest: &AgentDependencyDropManifestV1,
    trust_by_field: &HashMap<String, AgentTrustClass>,
) -> Result<HashMap<String, AgentDependencyDropEntryV1>> {
    if manifest.manifest_version != AGENT_DEPENDENCY_DROP_MANIFEST_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 dependency-drop manifest version `{}` is unsupported",
            manifest.manifest_version
        )));
    }
    let ids: Vec<String> = manifest
        .entries
        .iter()
        .map(|entry| entry.dependency_id.clone())
        .collect();
    validate_sorted_unique(&ids, "AgentStepReceiptV1 dependency_id")?;

    let dropped_fields: BTreeSet<String> = trust_by_field
        .iter()
        .filter(|(_, trust_class)| **trust_class == AgentTrustClass::DependencyDropped)
        .map(|(field, _)| field.clone())
        .collect();
    let mut dependency_fields = Vec::new();
    let mut by_field = HashMap::new();

    for entry in &manifest.entries {
        validate_dependency_id(&entry.dependency_id)?;
        validate_commitment(
            &entry.source_commitment,
            "AgentStepReceiptV1 dependency source",
        )?;
        validate_commitment(
            &entry.replacement_commitment,
            "AgentStepReceiptV1 dependency replacement",
        )?;
        validate_schema_version(
            &entry.replacement_receipt_version,
            "replacement_receipt_version",
        )?;
        if entry.replacement_receipt_version != AGENT_STEP_RECEIPT_VERSION_V1 {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 unsupported replacement receipt version".to_string(),
            ));
        }
        if entry.trust_class != AgentTrustClass::DependencyDropped {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 dependency-drop entry must use dependency_dropped trust class"
                    .to_string(),
            ));
        }
        if entry.verifier_domain != AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 dependency-drop verifier domain mismatch".to_string(),
            ));
        }
        validate_field_path(&entry.corresponding_receipt_field)?;
        if SELF_BOUND_FIELDS.contains(&entry.corresponding_receipt_field.as_str()) {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 dependency-drop entry points at self-bound field".to_string(),
            ));
        }
        if !trust_by_field.contains_key(&entry.corresponding_receipt_field) {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 dependency-drop entry points at unknown receipt field"
                    .to_string(),
            ));
        }
        if entry.reason_for_drop.is_empty() {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 dependency-drop reason must be non-empty".to_string(),
            ));
        }
        let Some(required) = &entry.required_subproof_or_attestation else {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 dependency-dropped field {} lacks required support",
                entry.corresponding_receipt_field
            )));
        };
        if required.kind != AgentRequiredSubfactKind::Subreceipt {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 dependency-dropped field {} support must be a subreceipt",
                entry.corresponding_receipt_field
            )));
        }
        validate_commitment(
            &required.commitment,
            "AgentStepReceiptV1 required subproof/attestation",
        )?;
        if required.verifier_domain != AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 required subproof/attestation verifier domain mismatch"
                    .to_string(),
            ));
        }
        if required.commitment != entry.replacement_commitment {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 dependency-dropped field {} support commitment mismatch",
                entry.corresponding_receipt_field
            )));
        }
        validate_sorted_unique(
            &entry.non_claims,
            "AgentStepReceiptV1 dependency non_claims",
        )?;
        dependency_fields.push(entry.corresponding_receipt_field.clone());
        if by_field
            .insert(entry.corresponding_receipt_field.clone(), entry.clone())
            .is_some()
        {
            return Err(VmError::InvalidConfig(
                "AgentStepReceiptV1 duplicate dependency-drop receipt field".to_string(),
            ));
        }
    }

    let dependency_field_set: BTreeSet<String> = dependency_fields.into_iter().collect();
    if dependency_field_set != dropped_fields {
        return Err(VmError::InvalidConfig(
            "AgentStepReceiptV1 dependency-drop manifest does not match dropped fields".to_string(),
        ));
    }
    Ok(by_field)
}

fn validate_field_support(
    receipt_value: &Value,
    trust_by_field: &HashMap<String, AgentTrustClass>,
    evidence_by_field: &HashMap<String, Vec<AgentEvidenceEntryV1>>,
    dependency_by_field: &HashMap<String, AgentDependencyDropEntryV1>,
) -> Result<()> {
    for field_path in sort_utf8(trust_by_field.keys().cloned().collect()) {
        if SELF_BOUND_FIELDS.contains(&field_path.as_str()) {
            continue;
        }
        let trust_class = *trust_by_field.get(&field_path).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 missing trust class for {field_path}"
            ))
        })?;
        if trust_class == AgentTrustClass::Omitted {
            let field = field_from_pointer(&field_path)?;
            if !receipt_value.get(field).unwrap_or(&Value::Null).is_null() {
                return Err(VmError::InvalidConfig(format!(
                    "AgentStepReceiptV1 omitted field {field_path} must be null"
                )));
            }
            if evidence_by_field.contains_key(&field_path)
                || dependency_by_field.contains_key(&field_path)
            {
                return Err(VmError::InvalidConfig(format!(
                    "AgentStepReceiptV1 omitted field {field_path} must not have evidence or dependency-drop entries"
                )));
            }
            continue;
        }
        let entries = evidence_by_field.get(&field_path).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 missing evidence for {field_path}"
            ))
        })?;
        let aggregate = entries
            .iter()
            .map(|entry| entry.trust_class.rank())
            .max()
            .unwrap_or(0);
        if aggregate < trust_class.rank() {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 insufficient evidence trust class for {field_path}"
            )));
        }
        if !entries.iter().any(|entry| {
            entry.trust_class == trust_class
                && evidence_kind_supports(entry.evidence_kind, trust_class)
        }) {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 {trust_class} field {field_path} lacks compatible evidence"
            )));
        }
        if trust_class == AgentTrustClass::DependencyDropped {
            let dependency = dependency_by_field.get(&field_path).ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "AgentStepReceiptV1 dependency-dropped field {field_path} lacks dependency-drop entry"
                ))
            })?;
            let field = field_from_pointer(&field_path)?;
            let value = receipt_value.get(field).ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "AgentStepReceiptV1 dependency-dropped field {field_path} is absent"
                ))
            })?;
            let Some(value) = value.as_str() else {
                return Err(VmError::InvalidConfig(format!(
                    "AgentStepReceiptV1 dependency-dropped field {field_path} must be a commitment string"
                )));
            };
            if dependency.replacement_commitment != value {
                return Err(VmError::InvalidConfig(format!(
                    "AgentStepReceiptV1 dependency-dropped field {field_path} replacement mismatch"
                )));
            }
            if !entries.iter().any(|entry| {
                entry.trust_class == AgentTrustClass::DependencyDropped
                    && entry.evidence_kind == AgentEvidenceKind::Subreceipt
            }) {
                return Err(VmError::InvalidConfig(format!(
                    "AgentStepReceiptV1 dependency_dropped field {field_path} lacks required evidence kind"
                )));
            }
        }
    }
    Ok(())
}

fn evidence_kind_supports(kind: AgentEvidenceKind, trust_class: AgentTrustClass) -> bool {
    match trust_class {
        AgentTrustClass::Omitted => false,
        AgentTrustClass::Attested => kind == AgentEvidenceKind::Attestation,
        AgentTrustClass::Replayed => kind == AgentEvidenceKind::ReplaySource,
        AgentTrustClass::DependencyDropped => kind == AgentEvidenceKind::Subreceipt,
        AgentTrustClass::Proved => {
            kind == AgentEvidenceKind::Proof || kind == AgentEvidenceKind::Subreceipt
        }
    }
}

fn validate_allowed_trust_class(field_path: &str, trust_class: AgentTrustClass) -> Result<()> {
    let allowed = match field_path {
        "/receipt_version"
        | "/verifier_domain"
        | "/proof_backend"
        | "/proof_backend_version"
        | "/receipt_parser_version"
        | "/dependency_drop_manifest_commitment"
        | "/evidence_manifest_commitment"
        | "/field_trust_class_vector"
        | "/receipt_commitment" => &[AgentTrustClass::Replayed][..],
        "/runtime_domain" | "/model_identity" => &[
            AgentTrustClass::Proved,
            AgentTrustClass::Attested,
            AgentTrustClass::Replayed,
        ],
        "/model_receipt_commitment" => {
            &[AgentTrustClass::Proved, AgentTrustClass::DependencyDropped]
        }
        "/tool_receipts_root" | "/policy_commitment" | "/transcript_commitment" => &[
            AgentTrustClass::Proved,
            AgentTrustClass::Attested,
            AgentTrustClass::Replayed,
            AgentTrustClass::DependencyDropped,
            AgentTrustClass::Omitted,
        ],
        "/prior_state_commitment"
        | "/observation_commitment"
        | "/model_commitment"
        | "/model_config_commitment"
        | "/action_commitment"
        | "/next_state_commitment" => &[
            AgentTrustClass::Proved,
            AgentTrustClass::Attested,
            AgentTrustClass::Replayed,
            AgentTrustClass::DependencyDropped,
        ],
        _ => {
            return Err(VmError::InvalidConfig(format!(
                "AgentStepReceiptV1 unknown receipt field path {field_path}"
            )))
        }
    };
    if !allowed.contains(&trust_class) {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 field {field_path} cannot use trust class {trust_class}"
        )));
    }
    Ok(())
}

fn evidence_commitment_for_field(field_path: &str, value: &Value) -> Result<String> {
    let payload = serde_json::json!({
        "field": field_path,
        "value": value,
    });
    commitment_for_value(&payload, "agent-step-receipt-v1.evidence-field-binding")
}

fn commitment_for_value(value: &Value, domain: &str) -> Result<String> {
    validate_canonical_value(value)?;
    let mut canonical = Vec::new();
    write_canonical_json_value(value, &mut canonical)?;
    let mut output = [0u8; 32];
    let mut hasher = Blake2bVar::new(output.len()).map_err(|err| {
        VmError::Serialization(format!("AgentStepReceiptV1 blake2b-256 init: {err}"))
    })?;
    hasher.update(domain.as_bytes());
    hasher.update(b"\0");
    hasher.update(&canonical);
    hasher.finalize_variable(&mut output).map_err(|err| {
        VmError::Serialization(format!(
            "AgentStepReceiptV1 blake2b-256 finalization: {err}"
        ))
    })?;
    Ok(format!("blake2b-256:{}", hex_lower(&output)))
}

fn validate_canonical_value(value: &Value) -> Result<()> {
    match value {
        Value::Null | Value::Bool(_) | Value::Number(_) => Ok(()),
        Value::String(value) => validate_nfc(value, "string"),
        Value::Array(values) => {
            for item in values {
                validate_canonical_value(item)?;
            }
            Ok(())
        }
        Value::Object(map) => {
            for (key, item) in map {
                validate_nfc(key, "object key")?;
                validate_canonical_value(item)?;
            }
            Ok(())
        }
    }
}

fn write_canonical_json_value(value: &Value, out: &mut Vec<u8>) -> Result<()> {
    match value {
        Value::Null => out.extend_from_slice(b"null"),
        Value::Bool(value) => out.extend_from_slice(if *value { b"true" } else { b"false" }),
        Value::Number(value) => out.extend_from_slice(value.to_string().as_bytes()),
        Value::String(value) => out.extend_from_slice(
            serde_json::to_string(value)
                .map_err(|err| VmError::Serialization(format!("AgentStepReceiptV1 string: {err}")))?
                .as_bytes(),
        ),
        Value::Array(values) => {
            out.push(b'[');
            for (index, item) in values.iter().enumerate() {
                if index > 0 {
                    out.push(b',');
                }
                write_canonical_json_value(item, out)?;
            }
            out.push(b']');
        }
        Value::Object(map) => {
            out.push(b'{');
            let mut entries: Vec<_> = map.iter().collect();
            entries.sort_by(|(left, _), (right, _)| left.as_bytes().cmp(right.as_bytes()));
            for (index, (key, item)) in entries.iter().enumerate() {
                if index > 0 {
                    out.push(b',');
                }
                out.extend_from_slice(
                    serde_json::to_string(key)
                        .map_err(|err| {
                            VmError::Serialization(format!("AgentStepReceiptV1 object key: {err}"))
                        })?
                        .as_bytes(),
                );
                out.push(b':');
                write_canonical_json_value(item, out)?;
            }
            out.push(b'}');
        }
    }
    Ok(())
}

fn parse_strict_json_value(json: &str) -> Result<Value> {
    let mut deserializer = serde_json::Deserializer::from_str(json);
    let StrictJsonValueResult(value) = StrictJsonValue
        .deserialize(&mut deserializer)
        .map_err(agent_receipt_json_error)?;
    deserializer.end().map_err(agent_receipt_json_error)?;
    Ok(value)
}

struct StrictJsonValue;

struct StrictJsonValueVisitor;

impl<'de> DeserializeSeed<'de> for StrictJsonValue {
    type Value = StrictJsonValueResult;

    fn deserialize<D>(self, deserializer: D) -> std::result::Result<Self::Value, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictJsonValueVisitor)
    }
}

struct StrictJsonValueResult(Value);

impl<'de> Visitor<'de> for StrictJsonValueVisitor {
    type Value = StrictJsonValueResult;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("strict AgentStepReceiptV1 JSON")
    }

    fn visit_unit<E>(self) -> std::result::Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(StrictJsonValueResult(Value::Null))
    }

    fn visit_none<E>(self) -> std::result::Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(StrictJsonValueResult(Value::Null))
    }

    fn visit_bool<E>(self, value: bool) -> std::result::Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(StrictJsonValueResult(Value::Bool(value)))
    }

    fn visit_i64<E>(self, value: i64) -> std::result::Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(StrictJsonValueResult(Value::Number(Number::from(value))))
    }

    fn visit_u64<E>(self, value: u64) -> std::result::Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(StrictJsonValueResult(Value::Number(Number::from(value))))
    }

    fn visit_f64<E>(self, _value: f64) -> std::result::Result<Self::Value, E>
    where
        E: de::Error,
    {
        Err(E::custom(
            "AgentStepReceiptV1 JSON floating point values are not allowed",
        ))
    }

    fn visit_str<E>(self, value: &str) -> std::result::Result<Self::Value, E>
    where
        E: de::Error,
    {
        self.visit_string(value.to_string())
    }

    fn visit_string<E>(self, value: String) -> std::result::Result<Self::Value, E>
    where
        E: de::Error,
    {
        validate_nfc_de(&value, "string")?;
        Ok(StrictJsonValueResult(Value::String(value)))
    }

    fn visit_seq<A>(self, mut seq: A) -> std::result::Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(StrictJsonValueResult(value)) = seq.next_element_seed(StrictJsonValue)? {
            values.push(value);
        }
        Ok(StrictJsonValueResult(Value::Array(values)))
    }

    fn visit_map<A>(self, mut access: A) -> std::result::Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut values = serde_json::Map::new();
        while let Some(key) = access.next_key::<String>()? {
            validate_nfc_de(&key, "object key")?;
            if values.contains_key(&key) {
                return Err(de::Error::custom(format!(
                    "AgentStepReceiptV1 JSON duplicate object key `{key}`"
                )));
            }
            let StrictJsonValueResult(value) = access.next_value_seed(StrictJsonValue)?;
            values.insert(key, value);
        }
        Ok(StrictJsonValueResult(Value::Object(values)))
    }
}

fn agent_receipt_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Io => {
            VmError::Serialization(format!("AgentStepReceiptV1 JSON I/O error: {error}"))
        }
        serde_json::error::Category::Syntax
        | serde_json::error::Category::Data
        | serde_json::error::Category::Eof => {
            VmError::InvalidConfig(format!("AgentStepReceiptV1 JSON is invalid: {error}"))
        }
    }
}

fn read_json_bytes_with_limit(path: &Path, limit: usize, label: &str) -> Result<Vec<u8>> {
    let metadata = fs::symlink_metadata(path).map_err(|error| {
        VmError::InvalidConfig(format!(
            "{label} `{}` could not be inspected before reading: io_kind={:?}: {error}",
            path.display(),
            error.kind()
        ))
    })?;
    if !metadata.file_type().is_file() {
        return Err(VmError::InvalidConfig(format!(
            "{label} `{}` is not a regular file",
            path.display()
        )));
    }
    if metadata.len() > limit as u64 {
        return Err(VmError::InvalidConfig(format!(
            "{label} `{}` is {} bytes, exceeding the limit of {} bytes",
            path.display(),
            metadata.len(),
            limit
        )));
    }

    let file = open_json_file_for_read(path, label)?;
    let opened_metadata = file.metadata().map_err(|error| {
        VmError::InvalidConfig(format!(
            "{label} `{}` could not be inspected after opening: io_kind={:?}: {error}",
            path.display(),
            error.kind()
        ))
    })?;
    if !opened_metadata.file_type().is_file() {
        return Err(VmError::InvalidConfig(format!(
            "{label} `{}` is not a regular file after opening",
            path.display()
        )));
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;

        if metadata.dev() != opened_metadata.dev() || metadata.ino() != opened_metadata.ino() {
            return Err(VmError::InvalidConfig(format!(
                "{label} `{}` changed between metadata inspection and open",
                path.display()
            )));
        }
    }
    if opened_metadata.len() > limit as u64 {
        return Err(VmError::InvalidConfig(format!(
            "{label} `{}` is {} bytes after opening, exceeding the limit of {} bytes",
            path.display(),
            opened_metadata.len(),
            limit
        )));
    }

    let mut reader = file.take(limit as u64 + 1);
    let mut bytes = Vec::with_capacity(metadata.len().min(limit as u64) as usize);
    reader.read_to_end(&mut bytes).map_err(|error| {
        VmError::InvalidConfig(format!(
            "{label} `{}` could not be read: io_kind={:?}: {error}",
            path.display(),
            error.kind()
        ))
    })?;
    if bytes.len() > limit {
        return Err(VmError::InvalidConfig(format!(
            "{label} `{}` is {} bytes after reading, exceeding the limit of {} bytes",
            path.display(),
            bytes.len(),
            limit
        )));
    }
    Ok(bytes)
}

#[cfg(unix)]
fn open_json_file_for_read(path: &Path, label: &str) -> Result<File> {
    use std::fs::OpenOptions;
    use std::os::unix::fs::OpenOptionsExt;

    OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
        .open(path)
        .map_err(|error| {
            VmError::InvalidConfig(format!(
                "{label} `{}` could not be opened for reading without following symlinks or blocking: io_kind={:?}: {error}",
                path.display(),
                error.kind()
            ))
        })
}

#[cfg(not(unix))]
fn open_json_file_for_read(path: &Path, label: &str) -> Result<File> {
    File::open(path).map_err(|error| {
        VmError::InvalidConfig(format!(
            "{label} `{}` could not be opened for reading: io_kind={:?}: {error}",
            path.display(),
            error.kind()
        ))
    })
}

fn validate_field_path(value: &str) -> Result<()> {
    field_from_pointer(value)?;
    Ok(())
}

fn json_pointer_for_field(field: &str) -> String {
    format!("/{field}")
}

fn field_from_pointer(pointer: &str) -> Result<&str> {
    let Some(field) = pointer.strip_prefix('/') else {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 invalid JSON Pointer `{pointer}`"
        )));
    };
    if field.is_empty() || field.contains('/') || field.contains('~') {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 unsupported JSON Pointer `{pointer}`"
        )));
    }
    if !RECEIPT_FIELDS.contains(&field) {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 unknown receipt field `{pointer}`"
        )));
    }
    Ok(field)
}

fn validate_sorted_unique(values: &[String], label: &str) -> Result<()> {
    if values != sort_utf8(values.to_vec()) {
        return Err(VmError::InvalidConfig(format!(
            "{label} entries are not sorted by UTF-8 bytes"
        )));
    }
    let mut seen = BTreeSet::new();
    for value in values {
        if !seen.insert(value) {
            return Err(VmError::InvalidConfig(format!("duplicate {label} entry")));
        }
    }
    Ok(())
}

fn sort_utf8(mut values: Vec<String>) -> Vec<String> {
    values.sort_by(|left, right| left.as_bytes().cmp(right.as_bytes()));
    values
}

fn validate_evidence_id(value: &str) -> Result<()> {
    validate_ascii_urn(value, "urn:agent-step:evidence:", 64, 128, "evidence_id")
}

fn validate_dependency_id(value: &str) -> Result<()> {
    validate_ascii_urn(
        value,
        "urn:agent-step:dependency:",
        64,
        128,
        "dependency_id",
    )
}

fn validate_ascii_urn(
    value: &str,
    prefix: &str,
    namespace_max: usize,
    name_max: usize,
    label: &str,
) -> Result<()> {
    let Some(rest) = value.strip_prefix(prefix) else {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 invalid {label}"
        )));
    };
    let Some((namespace, name)) = rest.split_once(':') else {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 invalid {label}"
        )));
    };
    if !is_ascii_token(namespace, namespace_max) || !is_ascii_token(name, name_max) {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 invalid {label}"
        )));
    }
    Ok(())
}

fn is_ascii_token(value: &str, max_len: usize) -> bool {
    if value.is_empty() || value.len() > max_len {
        return false;
    }
    let mut chars = value.bytes();
    let Some(first) = chars.next() else {
        return false;
    };
    if !first.is_ascii_lowercase() && !first.is_ascii_digit() {
        return false;
    }
    chars.all(|byte| {
        byte.is_ascii_lowercase() || byte.is_ascii_digit() || matches!(byte, b'.' | b'_' | b'-')
    })
}

fn validate_schema_version(value: &str, label: &str) -> Result<()> {
    let mut bytes = value.bytes();
    let Some(first) = bytes.next() else {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 {label} must be an ASCII schema-version string"
        )));
    };
    if !first.is_ascii_alphabetic() || value.len() > 128 {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 {label} must be an ASCII schema-version string"
        )));
    }
    if !bytes.all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-')) {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 {label} must be an ASCII schema-version string"
        )));
    }
    Ok(())
}

fn validate_commitment(value: &str, label: &str) -> Result<()> {
    let Some((algorithm, digest)) = value.split_once(':') else {
        return Err(VmError::InvalidConfig(format!(
            "{label} commitment must be algorithm:lower_hex_digest"
        )));
    };
    let expected_len = match algorithm {
        "blake2b-256" | "blake2s-256" | "sha256" => 64,
        "sha384" => 96,
        "sha512" => 128,
        _ => {
            return Err(VmError::InvalidConfig(format!(
                "{label} uses unsupported commitment algorithm `{algorithm}`"
            )))
        }
    };
    if digest.len() != expected_len
        || !digest
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    {
        return Err(VmError::InvalidConfig(format!(
            "{label} digest has invalid length or casing"
        )));
    }
    Ok(())
}

fn validate_nfc(value: &str, label: &str) -> Result<()> {
    if !value.nfc().eq(value.chars()) {
        return Err(VmError::InvalidConfig(format!(
            "AgentStepReceiptV1 {label} is not Unicode NFC"
        )));
    }
    Ok(())
}

fn validate_nfc_de<E>(value: &str, label: &str) -> std::result::Result<(), E>
where
    E: de::Error,
{
    if !value.nfc().eq(value.chars()) {
        return Err(E::custom(format!(
            "AgentStepReceiptV1 {label} is not Unicode NFC"
        )));
    }
    Ok(())
}

fn hex_lower(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    fn toy_commit(value: &str, domain: &str) -> String {
        commitment_for_value(&Value::String(value.to_string()), domain).expect("toy commitment")
    }

    fn base_receipt() -> AgentStepReceiptV1 {
        let trust_classes = BTreeMap::from([
            ("action_commitment", AgentTrustClass::Replayed),
            (
                "dependency_drop_manifest_commitment",
                AgentTrustClass::Replayed,
            ),
            ("evidence_manifest_commitment", AgentTrustClass::Replayed),
            ("field_trust_class_vector", AgentTrustClass::Replayed),
            ("model_commitment", AgentTrustClass::Replayed),
            ("model_config_commitment", AgentTrustClass::Replayed),
            ("model_identity", AgentTrustClass::Attested),
            ("model_receipt_commitment", AgentTrustClass::Proved),
            ("next_state_commitment", AgentTrustClass::Replayed),
            ("observation_commitment", AgentTrustClass::Replayed),
            ("policy_commitment", AgentTrustClass::Replayed),
            ("prior_state_commitment", AgentTrustClass::Replayed),
            ("proof_backend", AgentTrustClass::Replayed),
            ("proof_backend_version", AgentTrustClass::Replayed),
            ("receipt_commitment", AgentTrustClass::Replayed),
            ("receipt_parser_version", AgentTrustClass::Replayed),
            ("receipt_version", AgentTrustClass::Replayed),
            ("runtime_domain", AgentTrustClass::Replayed),
            ("tool_receipts_root", AgentTrustClass::Attested),
            ("transcript_commitment", AgentTrustClass::Replayed),
            ("verifier_domain", AgentTrustClass::Replayed),
        ]);
        AgentStepReceiptV1 {
            receipt_version: AGENT_STEP_RECEIPT_VERSION_V1.to_string(),
            verifier_domain: AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN.to_string(),
            runtime_domain: "agent-runtime-test-domain".to_string(),
            proof_backend: "stwo".to_string(),
            proof_backend_version: AGENT_STEP_RECEIPT_STWO_TEST_BACKEND_VERSION.to_string(),
            receipt_parser_version: AGENT_STEP_RECEIPT_PARSER_VERSION_V1.to_string(),
            prior_state_commitment: toy_commit("prior-state", "toy"),
            observation_commitment: toy_commit("observation", "toy"),
            model_identity: "toy-transformer-block-v1".to_string(),
            model_commitment: toy_commit("model-weights", "toy"),
            model_config_commitment: toy_commit("model-config", "toy"),
            model_receipt_commitment: toy_commit("model-proof-receipt", "toy"),
            tool_receipts_root: Some(toy_commit("tool-output-root", "toy")),
            policy_commitment: Some(toy_commit("policy", "toy")),
            action_commitment: toy_commit("action", "toy"),
            next_state_commitment: toy_commit("next-state", "toy"),
            transcript_commitment: Some(toy_commit("transcript", "toy")),
            dependency_drop_manifest_commitment: String::new(),
            evidence_manifest_commitment: String::new(),
            field_trust_class_vector: trust_classes
                .into_iter()
                .map(|(field, trust_class)| AgentFieldTrustClassV1 {
                    field_path: json_pointer_for_field(field),
                    trust_class,
                })
                .collect(),
            receipt_commitment: String::new(),
        }
    }

    fn build_valid_bundle() -> AgentStepReceiptBundleV1 {
        let mut receipt = base_receipt();
        let dependency_drop_manifest = AgentDependencyDropManifestV1 {
            manifest_version: AGENT_DEPENDENCY_DROP_MANIFEST_VERSION_V1.to_string(),
            entries: Vec::new(),
        };
        receipt.dependency_drop_manifest_commitment =
            commit_agent_dependency_drop_manifest_v1(&dependency_drop_manifest)
                .expect("dependency manifest commitment");
        let receipt_value = serde_json::to_value(&receipt).expect("receipt value");
        let trust_by_field: BTreeMap<String, AgentTrustClass> = receipt
            .field_trust_class_vector
            .iter()
            .map(|entry| (entry.field_path.clone(), entry.trust_class))
            .collect();
        let mut entries = Vec::new();
        for (field_path, trust_class) in trust_by_field {
            if SELF_BOUND_FIELDS.contains(&field_path.as_str()) {
                continue;
            }
            let field = field_from_pointer(&field_path).expect("field pointer");
            let value = receipt_value.get(field).expect("field value");
            let evidence_kind = match trust_class {
                AgentTrustClass::Attested => AgentEvidenceKind::Attestation,
                AgentTrustClass::Proved => AgentEvidenceKind::Proof,
                _ => AgentEvidenceKind::ReplaySource,
            };
            entries.push(AgentEvidenceEntryV1 {
                evidence_id: format!("urn:agent-step:evidence:{}:0", field.replace('_', "-")),
                evidence_kind,
                commitment: evidence_commitment_for_field(&field_path, value)
                    .expect("evidence commitment"),
                trust_class,
                verifier_domain: AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN.to_string(),
                corresponding_receipt_field: field_path,
                non_claims: vec!["does-not-prove-agent-truthfulness".to_string()],
            });
        }
        entries.sort_by(|left, right| {
            left.evidence_id
                .as_bytes()
                .cmp(right.evidence_id.as_bytes())
        });
        let evidence_manifest = AgentEvidenceManifestV1 {
            manifest_version: AGENT_EVIDENCE_MANIFEST_VERSION_V1.to_string(),
            entries,
        };
        receipt.evidence_manifest_commitment =
            commit_agent_evidence_manifest_v1(&evidence_manifest)
                .expect("evidence manifest commitment");
        receipt.receipt_commitment =
            commit_agent_step_receipt_v1(&receipt).expect("receipt commitment");
        AgentStepReceiptBundleV1 {
            receipt,
            evidence_manifest,
            dependency_drop_manifest,
        }
    }

    fn recompute_manifest_commitments(bundle: &mut AgentStepReceiptBundleV1) {
        bundle.receipt.dependency_drop_manifest_commitment =
            commit_agent_dependency_drop_manifest_v1(&bundle.dependency_drop_manifest)
                .expect("dependency manifest commitment");
        bundle.receipt.evidence_manifest_commitment =
            commit_agent_evidence_manifest_v1(&bundle.evidence_manifest)
                .expect("evidence manifest commitment");
        recompute_receipt_commitment(bundle);
    }

    fn recompute_receipt_commitment(bundle: &mut AgentStepReceiptBundleV1) {
        bundle.receipt.receipt_commitment =
            commit_agent_step_receipt_v1(&bundle.receipt).expect("receipt commitment");
    }

    fn make_dependency_dropped_model_receipt_bundle() -> AgentStepReceiptBundleV1 {
        let mut bundle = build_valid_bundle();
        for entry in &mut bundle.receipt.field_trust_class_vector {
            if entry.field_path == "/model_receipt_commitment" {
                entry.trust_class = AgentTrustClass::DependencyDropped;
            }
        }
        let replacement = bundle.receipt.model_receipt_commitment.clone();
        bundle.dependency_drop_manifest.entries = vec![AgentDependencyDropEntryV1 {
            dependency_id: "urn:agent-step:dependency:model-receipt:0".to_string(),
            dependency_kind: AgentDependencyKind::ModelReceipt,
            source_commitment: toy_commit("full-model-proof-replay-source", "toy"),
            replacement_commitment: replacement.clone(),
            replacement_receipt_version: AGENT_STEP_RECEIPT_VERSION_V1.to_string(),
            trust_class: AgentTrustClass::DependencyDropped,
            verifier_domain: AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN.to_string(),
            corresponding_receipt_field: "/model_receipt_commitment".to_string(),
            reason_for_drop: "model proof replay replaced by subreceipt".to_string(),
            required_subproof_or_attestation: Some(AgentRequiredSubfactV1 {
                kind: AgentRequiredSubfactKind::Subreceipt,
                commitment: replacement,
                verifier_domain: AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN.to_string(),
            }),
            non_claims: vec!["does-not-prove-agent-truthfulness".to_string()],
        }];
        let receipt_value = serde_json::to_value(&bundle.receipt).expect("receipt value");
        for entry in &mut bundle.evidence_manifest.entries {
            if entry.corresponding_receipt_field == "/model_receipt_commitment" {
                entry.evidence_kind = AgentEvidenceKind::Subreceipt;
                entry.trust_class = AgentTrustClass::DependencyDropped;
                entry.commitment = evidence_commitment_for_field(
                    "/model_receipt_commitment",
                    receipt_value
                        .get("model_receipt_commitment")
                        .expect("model receipt value"),
                )
                .expect("evidence commitment");
            }
        }
        recompute_manifest_commitments(&mut bundle);
        bundle
    }

    fn make_omitted_tool_receipt_bundle() -> AgentStepReceiptBundleV1 {
        let mut bundle = build_valid_bundle();
        bundle.receipt.tool_receipts_root = None;
        for entry in &mut bundle.receipt.field_trust_class_vector {
            if entry.field_path == "/tool_receipts_root" {
                entry.trust_class = AgentTrustClass::Omitted;
            }
        }
        bundle
            .evidence_manifest
            .entries
            .retain(|entry| entry.corresponding_receipt_field != "/tool_receipts_root");
        recompute_manifest_commitments(&mut bundle);
        bundle
    }

    #[test]
    fn agent_step_receipt_valid_fixture_verifies_and_parses() {
        let bundle = build_valid_bundle();
        verify_agent_step_receipt_bundle_v1(&bundle).expect("valid bundle verifies");
        let json = serde_json::to_string(&bundle).expect("serialize bundle");
        parse_agent_step_receipt_bundle_v1_json(&json).expect("parse valid bundle");
    }

    #[cfg(unix)]
    #[test]
    fn agent_step_receipt_loader_rejects_symlink_path_boundary() {
        let dir = tempfile::tempdir().expect("tempdir");
        let target = dir.path().join("bundle.json");
        std::fs::write(
            &target,
            serde_json::to_vec(&build_valid_bundle()).expect("bundle json"),
        )
        .expect("write target");
        let link = dir.path().join("bundle-link.json");
        std::os::unix::fs::symlink(&target, &link).expect("symlink");

        let err = load_agent_step_receipt_bundle_v1(&link).expect_err("symlink rejects");
        assert!(
            err.to_string().contains("not a regular file")
                || err.to_string().contains("without following symlinks"),
            "{err}"
        );
    }

    #[test]
    fn agent_step_receipt_rejects_duplicate_json_keys_before_commitment_check() {
        let json =
            r#"{"receipt":{},"receipt":{},"evidence_manifest":{},"dependency_drop_manifest":{}}"#;
        let err = parse_agent_step_receipt_bundle_v1_json(json).expect_err("duplicate key rejects");
        assert!(err.to_string().contains("duplicate object key"));
    }

    #[test]
    fn agent_step_receipt_rejects_unknown_json_fields() {
        let mut value = serde_json::to_value(build_valid_bundle()).expect("bundle value");
        value["receipt"]["unexpected"] = Value::String("x".to_string());
        let err = parse_agent_step_receipt_bundle_v1_json(&value.to_string())
            .expect_err("unknown field rejects");
        assert!(err.to_string().contains("unknown field"));
    }

    #[test]
    fn agent_step_receipt_rejects_non_nfc_json_strings() {
        let mut value = serde_json::to_value(build_valid_bundle()).expect("bundle value");
        value["receipt"]["model_identity"] = Value::String("e\u{301}".to_string());
        let err = parse_agent_step_receipt_bundle_v1_json(&value.to_string())
            .expect_err("non-NFC string rejects");
        assert!(err.to_string().contains("not Unicode NFC"));
    }

    #[test]
    fn agent_step_receipt_rejects_stale_evidence_field_mutations() {
        let mutations: &[(&str, fn(&mut AgentStepReceiptBundleV1))] = &[
            ("runtime_domain", |bundle| {
                bundle.receipt.runtime_domain = "other-runtime-domain".to_string();
            }),
            ("model_identity", |bundle| {
                bundle.receipt.model_identity = "different-model-label".to_string();
            }),
            ("model_commitment", |bundle| {
                bundle.receipt.model_commitment = toy_commit("other-model", "toy");
            }),
            ("model_config_commitment", |bundle| {
                bundle.receipt.model_config_commitment = toy_commit("other-config", "toy");
            }),
            ("model_receipt_commitment", |bundle| {
                bundle.receipt.model_receipt_commitment = toy_commit("other-model-receipt", "toy");
            }),
            ("observation_commitment", |bundle| {
                bundle.receipt.observation_commitment = toy_commit("other-observation", "toy");
            }),
            ("action_commitment", |bundle| {
                bundle.receipt.action_commitment = toy_commit("other-action", "toy");
            }),
            ("policy_commitment", |bundle| {
                bundle.receipt.policy_commitment = Some(toy_commit("other-policy", "toy"));
            }),
            ("tool_receipts_root", |bundle| {
                bundle.receipt.tool_receipts_root = Some(toy_commit("other-tool", "toy"));
            }),
            ("prior_state_commitment", |bundle| {
                bundle.receipt.prior_state_commitment = toy_commit("other-prior", "toy");
            }),
            ("next_state_commitment", |bundle| {
                bundle.receipt.next_state_commitment = toy_commit("other-next", "toy");
            }),
            ("transcript_commitment", |bundle| {
                bundle.receipt.transcript_commitment = Some(toy_commit("other-transcript", "toy"));
            }),
        ];
        for (name, mutate) in mutations {
            let mut bundle = build_valid_bundle();
            mutate(&mut bundle);
            recompute_receipt_commitment(&mut bundle);
            let err = verify_agent_step_receipt_bundle_v1(&bundle)
                .expect_err(&format!("{name} should reject"));
            assert!(
                err.to_string().contains("evidence commitment")
                    || err.to_string().contains("unsupported")
                    || err.to_string().contains("mismatch"),
                "{name}: {err}"
            );
        }
    }

    #[test]
    fn agent_step_receipt_rejects_backend_and_parser_aliases() {
        let mut parser_alias = build_valid_bundle();
        parser_alias.receipt.receipt_parser_version = "agent-step-receipt-parser-v01".to_string();
        recompute_receipt_commitment(&mut parser_alias);
        let err =
            verify_agent_step_receipt_bundle_v1(&parser_alias).expect_err("parser alias rejects");
        assert!(err.to_string().contains("receipt_parser_version"));

        let mut backend_alias = build_valid_bundle();
        backend_alias.receipt.proof_backend_version = "stwo-agent-step-test-proof-v01".to_string();
        recompute_receipt_commitment(&mut backend_alias);
        let err =
            verify_agent_step_receipt_bundle_v1(&backend_alias).expect_err("backend alias rejects");
        assert!(err.to_string().contains("proof backend"));
    }

    #[test]
    fn agent_step_receipt_rejects_trust_vector_reordering() {
        let mut bundle = build_valid_bundle();
        bundle.receipt.field_trust_class_vector.reverse();
        recompute_receipt_commitment(&mut bundle);
        let err = verify_agent_step_receipt_bundle_v1(&bundle).expect_err("trust reorder rejects");
        assert!(err.to_string().contains("not sorted"));
    }

    #[test]
    fn agent_step_receipt_rejects_trust_class_upgrade_without_proof() {
        let mut bundle = build_valid_bundle();
        for entry in &mut bundle.receipt.field_trust_class_vector {
            if entry.field_path == "/model_identity" {
                entry.trust_class = AgentTrustClass::Proved;
            }
        }
        recompute_receipt_commitment(&mut bundle);
        let err = verify_agent_step_receipt_bundle_v1(&bundle).expect_err("trust upgrade rejects");
        assert!(
            err.to_string()
                .contains("insufficient evidence trust class")
                || err.to_string().contains("lacks compatible evidence")
        );
    }

    #[test]
    fn agent_step_receipt_rejects_evidence_for_self_bound_fields() {
        let mut bundle = build_valid_bundle();
        let receipt_value = serde_json::to_value(&bundle.receipt).expect("receipt value");
        bundle.evidence_manifest.entries.push(AgentEvidenceEntryV1 {
            evidence_id: "urn:agent-step:evidence:self-bound:0".to_string(),
            evidence_kind: AgentEvidenceKind::ReplaySource,
            commitment: evidence_commitment_for_field(
                "/receipt_commitment",
                receipt_value
                    .get("receipt_commitment")
                    .expect("receipt commitment"),
            )
            .expect("evidence commitment"),
            trust_class: AgentTrustClass::Replayed,
            verifier_domain: AGENT_STEP_RECEIPT_TEST_VERIFIER_DOMAIN.to_string(),
            corresponding_receipt_field: "/receipt_commitment".to_string(),
            non_claims: vec!["does-not-prove-agent-truthfulness".to_string()],
        });
        bundle.evidence_manifest.entries.sort_by(|left, right| {
            left.evidence_id
                .as_bytes()
                .cmp(right.evidence_id.as_bytes())
        });
        recompute_manifest_commitments(&mut bundle);
        let err =
            verify_agent_step_receipt_bundle_v1(&bundle).expect_err("self-bound evidence rejects");
        assert!(err.to_string().contains("self-bound receipt field"));
    }

    #[test]
    fn agent_step_receipt_omitted_field_allows_no_claim_only() {
        let mut bundle = make_omitted_tool_receipt_bundle();
        verify_agent_step_receipt_bundle_v1(&bundle).expect("omitted tool field verifies");
        bundle.receipt.tool_receipts_root = Some(toy_commit("tool-output-root", "tampered"));
        recompute_receipt_commitment(&mut bundle);
        let err = verify_agent_step_receipt_bundle_v1(&bundle).expect_err("omitted claim rejects");
        assert!(err.to_string().contains("omitted field"));
    }

    #[test]
    fn agent_step_receipt_rejects_manifest_domain_relabels() {
        let mut evidence = build_valid_bundle();
        evidence.evidence_manifest.entries[0].verifier_domain = "other-domain".to_string();
        recompute_manifest_commitments(&mut evidence);
        let err =
            verify_agent_step_receipt_bundle_v1(&evidence).expect_err("evidence domain rejects");
        assert!(err
            .to_string()
            .contains("evidence verifier domain mismatch"));

        let mut receipt_domain = build_valid_bundle();
        receipt_domain.receipt.verifier_domain = "other-domain".to_string();
        let receipt_value = serde_json::to_value(&receipt_domain.receipt).expect("receipt value");
        for entry in &mut receipt_domain.evidence_manifest.entries {
            if entry.corresponding_receipt_field == "/verifier_domain" {
                entry.commitment = evidence_commitment_for_field(
                    "/verifier_domain",
                    receipt_value.get("verifier_domain").expect("domain"),
                )
                .expect("evidence commitment");
            }
        }
        recompute_manifest_commitments(&mut receipt_domain);
        let err = verify_agent_step_receipt_bundle_v1(&receipt_domain).expect_err("domain rejects");
        assert!(err.to_string().contains("verifier_domain"));
    }

    #[test]
    fn agent_step_receipt_dependency_dropped_fixture_verifies() {
        let bundle = make_dependency_dropped_model_receipt_bundle();
        verify_agent_step_receipt_bundle_v1(&bundle).expect("dependency-dropped fixture verifies");
    }

    #[test]
    fn agent_step_receipt_dependency_drop_duplicate_id_rejects() {
        let mut bundle = make_dependency_dropped_model_receipt_bundle();
        let duplicate = bundle.dependency_drop_manifest.entries[0].clone();
        bundle.dependency_drop_manifest.entries.push(duplicate);
        recompute_manifest_commitments(&mut bundle);
        let err = verify_agent_step_receipt_bundle_v1(&bundle)
            .expect_err("duplicate dependency id rejects");
        assert!(err.to_string().contains("duplicate"));
    }

    #[test]
    fn agent_step_receipt_dependency_drop_must_map_each_dropped_field_once() {
        let mut bundle = make_dependency_dropped_model_receipt_bundle();
        bundle.receipt.policy_commitment = Some(bundle.receipt.model_receipt_commitment.clone());
        for entry in &mut bundle.receipt.field_trust_class_vector {
            if entry.field_path == "/policy_commitment" {
                entry.trust_class = AgentTrustClass::DependencyDropped;
            }
        }
        let receipt_value = serde_json::to_value(&bundle.receipt).expect("receipt value");
        for entry in &mut bundle.evidence_manifest.entries {
            if entry.corresponding_receipt_field == "/policy_commitment" {
                entry.evidence_kind = AgentEvidenceKind::Subreceipt;
                entry.trust_class = AgentTrustClass::DependencyDropped;
                entry.commitment = evidence_commitment_for_field(
                    "/policy_commitment",
                    receipt_value.get("policy_commitment").expect("policy"),
                )
                .expect("evidence commitment");
            }
        }
        recompute_manifest_commitments(&mut bundle);
        let err = verify_agent_step_receipt_bundle_v1(&bundle)
            .expect_err("missing dependency mapping rejects");
        assert!(err.to_string().contains("does not match dropped fields"));
    }

    #[test]
    fn agent_step_receipt_dependency_drop_replacement_and_support_must_match() {
        let mut replacement = make_dependency_dropped_model_receipt_bundle();
        replacement.dependency_drop_manifest.entries[0].replacement_commitment =
            toy_commit("wrong-replacement", "toy");
        recompute_manifest_commitments(&mut replacement);
        let err = verify_agent_step_receipt_bundle_v1(&replacement)
            .expect_err("replacement mismatch rejects");
        assert!(
            err.to_string().contains("support commitment mismatch")
                || err.to_string().contains("replacement mismatch")
        );

        let mut support = make_dependency_dropped_model_receipt_bundle();
        support.dependency_drop_manifest.entries[0]
            .required_subproof_or_attestation
            .as_mut()
            .expect("support")
            .kind = AgentRequiredSubfactKind::Proof;
        recompute_manifest_commitments(&mut support);
        let err = verify_agent_step_receipt_bundle_v1(&support).expect_err("support kind rejects");
        assert!(err.to_string().contains("support must be a subreceipt"));
    }

    #[test]
    fn agent_step_receipt_dependency_drop_rejects_version_and_domain_drift() {
        let mut version = make_dependency_dropped_model_receipt_bundle();
        version.dependency_drop_manifest.entries[0].replacement_receipt_version =
            "agent-step-receipt-v01".to_string();
        recompute_manifest_commitments(&mut version);
        let err = verify_agent_step_receipt_bundle_v1(&version)
            .expect_err("replacement receipt version drift rejects");
        assert!(
            err.to_string()
                .contains("unsupported replacement receipt version"),
            "{err}"
        );

        let mut domain = make_dependency_dropped_model_receipt_bundle();
        domain.dependency_drop_manifest.entries[0].verifier_domain = "other-domain".to_string();
        recompute_manifest_commitments(&mut domain);
        let err = verify_agent_step_receipt_bundle_v1(&domain).expect_err("domain drift rejects");
        assert!(
            err.to_string()
                .contains("dependency-drop verifier domain mismatch"),
            "{err}"
        );
    }

    #[test]
    fn agent_step_receipt_dependency_drop_rejects_unknown_dependency_kind() {
        let mut value =
            serde_json::to_value(make_dependency_dropped_model_receipt_bundle()).expect("bundle");
        value["dependency_drop_manifest"]["entries"][0]["dependency_kind"] =
            Value::String("model-proof".to_string());
        let err = parse_agent_step_receipt_bundle_v1_json(&value.to_string())
            .expect_err("unknown dependency kind rejects");
        assert!(
            err.to_string().contains("dependency_kind")
                || err.to_string().contains("unknown variant"),
            "{err}"
        );
    }

    #[test]
    fn agent_step_receipt_rejects_mixed_case_commitment_algorithm() {
        let mut bundle = build_valid_bundle();
        bundle.receipt.model_commitment =
            bundle
                .receipt
                .model_commitment
                .replacen("blake2b-256", "BLAKE2B-256", 1);
        recompute_receipt_commitment(&mut bundle);
        let err =
            verify_agent_step_receipt_bundle_v1(&bundle).expect_err("mixed-case algorithm rejects");
        assert!(err.to_string().contains("unsupported commitment algorithm"));
    }
}
