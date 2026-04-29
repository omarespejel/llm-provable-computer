#!/usr/bin/env python3
"""Reference mutation oracle for AgentStepReceiptV1 relabeling checks.

This script is intentionally stricter than a fixture generator and narrower
than a production verifier. It exercises the commitment-binding rules from the
agent-step receipt design note against a deterministic toy receipt, then
mutates receipt fields while preserving their original evidence graph and
requires stale-evidence rejection.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import copy
import hashlib
import json
import re
import unicodedata
from typing import Any


class AgentReceiptError(ValueError):
    pass


TRUST_CLASS_RANK = {
    "omitted": 0,
    "attested": 1,
    "replayed": 2,
    "dependency_dropped": 3,
    "proved": 4,
}
EVIDENCE_KINDS = {"proof", "attestation", "replay_source", "subreceipt"}
EVIDENCE_KINDS_BY_TRUST_CLASS = {
    "attested": {"attestation"},
    "replayed": {"replay_source"},
    "dependency_dropped": {"subreceipt"},
    "proved": {"proof", "subreceipt"},
}
DEPENDENCY_KINDS = {
    "source_manifest",
    "proof_trace",
    "model_receipt",
    "tool_receipt",
    "state_commitment",
    "policy_commitment",
    "transcript",
    "other",
}
REQUIRED_SUBFACT_KINDS = {"proof", "attestation", "subreceipt"}
HASH_LENGTHS = {
    "blake2b-256": 64,
    "blake2s-256": 64,
    "sha256": 64,
    "sha384": 96,
    "sha512": 128,
}
RECEIPT_VERSION = "agent-step-receipt-v1"
RECEIPT_PARSER_VERSION = "agent-step-receipt-parser-v1"
VERIFIER_DOMAIN = "agent-step-receipt-test-domain"
PROOF_BACKEND = "stwo"
PROOF_BACKEND_VERSION = "stwo-agent-step-test-proof-v1"
ALLOWED_BACKENDS = {(PROOF_BACKEND, PROOF_BACKEND_VERSION)}
ALLOWED_PARSER_BY_RECEIPT = {RECEIPT_VERSION: {RECEIPT_PARSER_VERSION}}
ALLOWED_VERIFIER_DOMAINS = {VERIFIER_DOMAIN}
ALLOWED_REPLACEMENT_RECEIPT_VERSIONS = {RECEIPT_VERSION}

RECEIPT_FIELDS = (
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
)
RECEIPT_FIELD_PATHS = frozenset(f"/{field}" for field in RECEIPT_FIELDS)
SELF_BOUND_FIELDS = {
    "/dependency_drop_manifest_commitment",
    "/evidence_manifest_commitment",
    "/field_trust_class_vector",
    "/receipt_commitment",
}
PROVED_FIELDS = {"/model_receipt_commitment"}
MUTATION_FIELDS = {
    "receipt_version": "receipt_version",
    "model_id": "model_identity",
    "runtime_domain": "runtime_domain",
    "proof_backend": "proof_backend",
    "receipt_parser_version": "receipt_parser_version",
    "weights_commitment": "model_commitment",
    "model_receipt_commitment": "model_receipt_commitment",
    "input_commitment": "observation_commitment",
    "output_action_commitment": "action_commitment",
    "quantization_config_commitment": "model_config_commitment",
    "policy_hash": "policy_commitment",
    "tool_output_hash": "tool_receipts_root",
    "prior_state_commitment": "prior_state_commitment",
    "next_state_commitment": "next_state_commitment",
    "backend_proof_system_version": "proof_backend_version",
    "verifier_domain_separator": "verifier_domain",
    "transcript_hash": "transcript_commitment",
}
EVIDENCE_ID_RE = re.compile(
    r"^urn:agent-step:evidence:[a-z0-9][a-z0-9._-]{0,63}:[a-z0-9][a-z0-9._-]{0,127}$"
)
DEPENDENCY_ID_RE = re.compile(
    r"^urn:agent-step:dependency:[a-z0-9][a-z0-9._-]{0,63}:[a-z0-9][a-z0-9._-]{0,127}$"
)
SCHEMA_VERSION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,127}$")


def _walk_json(value: Any) -> None:
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise AgentReceiptError("non-NFC string")
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, int):
        return
    elif isinstance(value, float):
        raise AgentReceiptError("floating point values are not allowed")
    elif isinstance(value, list):
        for item in value:
            _walk_json(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise AgentReceiptError("non-string object key")
            _walk_json(key)
            _walk_json(item)
    else:
        raise AgentReceiptError(f"unsupported JSON value type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    _walk_json(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def commitment_for(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def validate_commitment(value: str, label: str) -> None:
    if not isinstance(value, str) or ":" not in value:
        raise AgentReceiptError(f"{label} commitment must be algorithm:hex")
    algorithm, digest = value.split(":", 1)
    expected_len = HASH_LENGTHS.get(algorithm)
    if expected_len is None:
        raise AgentReceiptError(f"{label} uses unsupported algorithm {algorithm!r}")
    if len(digest) != expected_len or not re.fullmatch(r"[0-9a-f]+", digest):
        raise AgentReceiptError(f"{label} digest has invalid length or casing")


def validate_schema_version(value: Any, label: str) -> None:
    if not isinstance(value, str) or SCHEMA_VERSION_RE.fullmatch(value) is None:
        raise AgentReceiptError(f"{label} must be an ASCII schema-version string")


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AgentReceiptError(f"{label} must be an object")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise AgentReceiptError(f"{label} must be a string")
    return value


def validate_sorted_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise AgentReceiptError(f"{label} must be a list")
    strings = [require_string(item, label) for item in value]
    if strings != sorted(strings, key=lambda item: item.encode("utf-8")):
        raise AgentReceiptError(f"{label} must be sorted")
    if len(strings) != len(set(strings)):
        raise AgentReceiptError(f"duplicate {label} entry")
    return strings


def _json_pointer(field: str) -> str:
    return f"/{field}"


def _field_from_pointer(pointer: str) -> str:
    if not pointer.startswith("/"):
        raise AgentReceiptError(f"invalid JSON Pointer {pointer!r}")
    field = pointer[1:]
    if "/" in field or "~" in field:
        raise AgentReceiptError(f"unsupported nested JSON Pointer {pointer!r}")
    return field


def _receipt_payload_for_commitment(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    payload["receipt_commitment"] = None
    return payload


def _evidence_commitment_for_field(field_path: str, value: Any) -> str:
    return commitment_for(
        {"field": field_path, "value": value},
        "agent-step-receipt-v1.evidence-field-binding",
    )


def _base_receipt() -> dict[str, Any]:
    values = {
        "receipt_version": RECEIPT_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "runtime_domain": "agent-runtime-test-domain",
        "proof_backend": PROOF_BACKEND,
        "proof_backend_version": PROOF_BACKEND_VERSION,
        "receipt_parser_version": RECEIPT_PARSER_VERSION,
        "prior_state_commitment": commitment_for("prior-state", "toy"),
        "observation_commitment": commitment_for("observation", "toy"),
        "model_identity": "toy-transformer-block-v1",
        "model_commitment": commitment_for("model-weights", "toy"),
        "model_config_commitment": commitment_for("model-config", "toy"),
        "model_receipt_commitment": commitment_for("model-proof-receipt", "toy"),
        "tool_receipts_root": commitment_for("tool-output-root", "toy"),
        "policy_commitment": commitment_for("policy", "toy"),
        "action_commitment": commitment_for("action", "toy"),
        "next_state_commitment": commitment_for("next-state", "toy"),
        "transcript_commitment": commitment_for("transcript", "toy"),
        "dependency_drop_manifest_commitment": None,
        "evidence_manifest_commitment": None,
        "field_trust_class_vector": [],
        "receipt_commitment": None,
    }
    trust_classes = {
        "receipt_version": "replayed",
        "verifier_domain": "replayed",
        "runtime_domain": "replayed",
        "proof_backend": "replayed",
        "proof_backend_version": "replayed",
        "receipt_parser_version": "replayed",
        "prior_state_commitment": "replayed",
        "observation_commitment": "replayed",
        "model_identity": "attested",
        "model_commitment": "replayed",
        "model_config_commitment": "replayed",
        "model_receipt_commitment": "proved",
        "tool_receipts_root": "attested",
        "policy_commitment": "replayed",
        "action_commitment": "replayed",
        "next_state_commitment": "replayed",
        "transcript_commitment": "replayed",
        "dependency_drop_manifest_commitment": "replayed",
        "evidence_manifest_commitment": "replayed",
        "field_trust_class_vector": "replayed",
        "receipt_commitment": "replayed",
    }
    values["field_trust_class_vector"] = [
        {"field_path": _json_pointer(field), "trust_class": trust_class}
        for field, trust_class in sorted(trust_classes.items())
    ]
    return values


def build_valid_bundle() -> dict[str, Any]:
    receipt = _base_receipt()
    dependency_manifest = {
        "manifest_version": "agent-step-dependency-drop-manifest-v1",
        "entries": [],
    }
    receipt["dependency_drop_manifest_commitment"] = commitment_for(
        dependency_manifest,
        "agent-step-receipt-v1.dependency-drop-manifest",
    )
    entries = []
    trust_by_field = {
        entry["field_path"]: entry["trust_class"]
        for entry in receipt["field_trust_class_vector"]
    }
    for field_path, trust_class in trust_by_field.items():
        if field_path in SELF_BOUND_FIELDS:
            continue
        field = _field_from_pointer(field_path)
        kind = "proof" if field_path in PROVED_FIELDS else "replay_source"
        if trust_class == "attested":
            kind = "attestation"
        entries.append(
            {
                "evidence_id": f"urn:agent-step:evidence:{field.replace('_', '-')}:0",
                "evidence_kind": kind,
                "commitment": _evidence_commitment_for_field(field_path, receipt[field]),
                "trust_class": trust_class,
                "verifier_domain": VERIFIER_DOMAIN,
                "corresponding_receipt_field": field_path,
                "non_claims": ["does-not-prove-agent-truthfulness"],
            }
        )
    entries.sort(key=lambda entry: entry["evidence_id"].encode("utf-8"))
    evidence_manifest = {
        "manifest_version": "agent-step-evidence-manifest-v1",
        "entries": entries,
    }
    receipt["evidence_manifest_commitment"] = commitment_for(
        evidence_manifest,
        "agent-step-receipt-v1.evidence-manifest",
    )
    receipt["receipt_commitment"] = commitment_for(
        _receipt_payload_for_commitment(receipt),
        "agent-step-receipt-v1.receipt",
    )
    return {
        "receipt": receipt,
        "evidence_manifest": evidence_manifest,
        "dependency_drop_manifest": dependency_manifest,
    }


def _validate_trust_vector(receipt: dict[str, Any]) -> dict[str, str]:
    vector = receipt["field_trust_class_vector"]
    if not isinstance(vector, list):
        raise AgentReceiptError("field_trust_class_vector must be a list")
    paths = []
    trust_by_field = {}
    for raw_entry in vector:
        entry = require_dict(raw_entry, "trust-class entry")
        if set(entry) != {"field_path", "trust_class"}:
            raise AgentReceiptError("trust-class entry has unexpected keys")
        path = require_string(entry["field_path"], "trust-class field path")
        trust_class = require_string(entry["trust_class"], "trust class")
        if trust_class not in TRUST_CLASS_RANK:
            raise AgentReceiptError(f"unknown trust class {trust_class!r}")
        field = _field_from_pointer(path)
        if field not in receipt:
            raise AgentReceiptError(f"trust vector names absent field {path}")
        if path in trust_by_field:
            raise AgentReceiptError(f"duplicate trust vector path {path}")
        paths.append(path)
        trust_by_field[path] = trust_class
    if paths != sorted(paths, key=lambda path: path.encode("utf-8")):
        raise AgentReceiptError("field_trust_class_vector is not sorted by field path bytes")
    expected_paths = sorted((_json_pointer(field) for field in RECEIPT_FIELDS), key=lambda p: p.encode("utf-8"))
    if paths != expected_paths:
        raise AgentReceiptError("field_trust_class_vector does not cover every receipt field")
    return trust_by_field


def _validate_evidence_manifest(manifest: dict[str, Any], receipt: dict[str, Any], trust_by_field: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    if set(manifest) != {"manifest_version", "entries"}:
        raise AgentReceiptError("evidence manifest has unexpected keys")
    if manifest["manifest_version"] != "agent-step-evidence-manifest-v1":
        raise AgentReceiptError("unsupported evidence manifest version")
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise AgentReceiptError("evidence entries must be a list")
    entries = [require_dict(entry, "evidence entry") for entry in entries]
    for entry in entries:
        if set(entry) != {
            "evidence_id",
            "evidence_kind",
            "commitment",
            "trust_class",
            "verifier_domain",
            "corresponding_receipt_field",
            "non_claims",
        }:
            raise AgentReceiptError("evidence entry has unexpected keys")
    ids = [require_string(entry["evidence_id"], "evidence_id") for entry in entries]
    if ids != sorted(ids, key=lambda value: value.encode("utf-8")):
        raise AgentReceiptError("evidence entries are not sorted by evidence_id bytes")
    if len(ids) != len(set(ids)):
        raise AgentReceiptError("duplicate evidence_id")
    by_field: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        evidence_id = require_string(entry["evidence_id"], "evidence_id")
        evidence_kind = require_string(entry["evidence_kind"], "evidence kind")
        trust_class = require_string(entry["trust_class"], "evidence trust class")
        verifier_domain = require_string(entry["verifier_domain"], "evidence verifier domain")
        field_path = require_string(entry["corresponding_receipt_field"], "evidence receipt field")
        if not EVIDENCE_ID_RE.fullmatch(evidence_id):
            raise AgentReceiptError("invalid evidence_id")
        if evidence_kind not in EVIDENCE_KINDS:
            raise AgentReceiptError("unknown evidence kind")
        if trust_class not in TRUST_CLASS_RANK:
            raise AgentReceiptError("unknown evidence trust class")
        if verifier_domain != VERIFIER_DOMAIN:
            raise AgentReceiptError("evidence verifier domain mismatch")
        validate_commitment(entry["commitment"], "evidence")
        validate_sorted_string_list(entry["non_claims"], "evidence non_claims")
        if field_path not in trust_by_field:
            raise AgentReceiptError("evidence points at unknown receipt field")
        if trust_by_field[field_path] == "omitted":
            raise AgentReceiptError("evidence points at omitted receipt field")
        field = _field_from_pointer(field_path)
        if entry["commitment"] != _evidence_commitment_for_field(field_path, receipt[field]):
            raise AgentReceiptError(f"evidence commitment does not bind {field_path}")
        by_field.setdefault(field_path, []).append(entry)
    return by_field


def _validate_dependency_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if set(manifest) != {"manifest_version", "entries"}:
        raise AgentReceiptError("dependency-drop manifest has unexpected keys")
    if manifest["manifest_version"] != "agent-step-dependency-drop-manifest-v1":
        raise AgentReceiptError("unsupported dependency-drop manifest version")
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise AgentReceiptError("dependency-drop entries must be a list")
    entries = [require_dict(entry, "dependency-drop entry") for entry in entries]
    for entry in entries:
        if set(entry) != {
            "dependency_id",
            "dependency_kind",
            "source_commitment",
            "replacement_commitment",
            "replacement_receipt_version",
            "trust_class",
            "verifier_domain",
            "corresponding_receipt_field",
            "reason_for_drop",
            "required_subproof_or_attestation",
            "non_claims",
        }:
            raise AgentReceiptError("dependency-drop entry has unexpected keys")
    ids = [require_string(entry["dependency_id"], "dependency_id") for entry in entries]
    if ids != sorted(ids, key=lambda value: value.encode("utf-8")):
        raise AgentReceiptError("dependency-drop entries are not sorted by dependency_id bytes")
    if len(ids) != len(set(ids)):
        raise AgentReceiptError("duplicate dependency_id")
    for entry in entries:
        dependency_id = require_string(entry["dependency_id"], "dependency_id")
        dependency_kind = require_string(entry["dependency_kind"], "dependency kind")
        trust_class = require_string(entry["trust_class"], "dependency trust class")
        verifier_domain = require_string(entry["verifier_domain"], "dependency verifier domain")
        field_path = require_string(entry["corresponding_receipt_field"], "dependency receipt field")
        if not DEPENDENCY_ID_RE.fullmatch(dependency_id):
            raise AgentReceiptError("invalid dependency_id")
        if dependency_kind not in DEPENDENCY_KINDS:
            raise AgentReceiptError("unknown dependency kind")
        validate_commitment(entry["source_commitment"], "dependency source")
        validate_commitment(entry["replacement_commitment"], "dependency replacement")
        validate_schema_version(entry["replacement_receipt_version"], "replacement receipt version")
        if entry["replacement_receipt_version"] not in ALLOWED_REPLACEMENT_RECEIPT_VERSIONS:
            raise AgentReceiptError("unsupported replacement receipt version")
        if trust_class not in TRUST_CLASS_RANK:
            raise AgentReceiptError("unknown dependency trust class")
        if trust_class != "dependency_dropped":
            raise AgentReceiptError("dependency-drop entry must use dependency_dropped trust class")
        if verifier_domain != VERIFIER_DOMAIN:
            raise AgentReceiptError("dependency-drop verifier domain mismatch")
        if field_path not in RECEIPT_FIELD_PATHS:
            raise AgentReceiptError("dependency-drop entry points at unknown receipt field")
        if field_path in SELF_BOUND_FIELDS:
            raise AgentReceiptError("dependency-drop entry points at self-bound field")
        if not isinstance(entry["reason_for_drop"], str) or not entry["reason_for_drop"]:
            raise AgentReceiptError("dependency-drop reason must be a non-empty string")
        required = entry["required_subproof_or_attestation"]
        if required is not None:
            required = require_dict(required, "required subproof/attestation")
            if set(required) != {"kind", "commitment", "verifier_domain"}:
                raise AgentReceiptError("required subproof/attestation has unexpected keys")
            required_kind = require_string(required["kind"], "required subproof/attestation kind")
            required_domain = require_string(
                required["verifier_domain"],
                "required subproof/attestation verifier domain",
            )
            if required_kind not in REQUIRED_SUBFACT_KINDS:
                raise AgentReceiptError("unknown required subproof/attestation kind")
            validate_commitment(required["commitment"], "required subproof/attestation")
            if required_domain != VERIFIER_DOMAIN:
                raise AgentReceiptError("required subproof/attestation verifier domain mismatch")
        validate_sorted_string_list(entry["non_claims"], "dependency non_claims")
    return entries


def verify_bundle(bundle: dict[str, Any]) -> bool:
    bundle = require_dict(bundle, "bundle")
    if set(bundle) != {"receipt", "evidence_manifest", "dependency_drop_manifest"}:
        raise AgentReceiptError("bundle has unexpected keys")
    receipt = require_dict(bundle["receipt"], "receipt")
    evidence_manifest = require_dict(bundle["evidence_manifest"], "evidence manifest")
    dependency_manifest = require_dict(bundle["dependency_drop_manifest"], "dependency-drop manifest")
    if set(receipt) != set(RECEIPT_FIELDS):
        raise AgentReceiptError("receipt has missing or unexpected fields")
    if receipt["receipt_version"] != RECEIPT_VERSION:
        raise AgentReceiptError("unsupported receipt version")
    if receipt["verifier_domain"] not in ALLOWED_VERIFIER_DOMAINS:
        raise AgentReceiptError("unsupported verifier domain")
    if receipt["receipt_parser_version"] not in ALLOWED_PARSER_BY_RECEIPT[receipt["receipt_version"]]:
        raise AgentReceiptError("unsupported receipt parser version")
    if (receipt["proof_backend"], receipt["proof_backend_version"]) not in ALLOWED_BACKENDS:
        raise AgentReceiptError("unsupported proof backend version")

    expected_dependency_commitment = commitment_for(
        dependency_manifest,
        "agent-step-receipt-v1.dependency-drop-manifest",
    )
    if receipt["dependency_drop_manifest_commitment"] != expected_dependency_commitment:
        raise AgentReceiptError("dependency_drop_manifest_commitment mismatch")
    expected_evidence_commitment = commitment_for(
        evidence_manifest,
        "agent-step-receipt-v1.evidence-manifest",
    )
    if receipt["evidence_manifest_commitment"] != expected_evidence_commitment:
        raise AgentReceiptError("evidence_manifest_commitment mismatch")

    trust_by_field = _validate_trust_vector(receipt)
    evidence_by_field = _validate_evidence_manifest(evidence_manifest, receipt, trust_by_field)
    dependency_entries = _validate_dependency_manifest(dependency_manifest)
    dropped_fields = {
        field_path
        for field_path, trust_class in trust_by_field.items()
        if trust_class == "dependency_dropped"
    }
    dependency_fields = [entry["corresponding_receipt_field"] for entry in dependency_entries]
    if set(dependency_fields) != dropped_fields:
        raise AgentReceiptError("dependency-drop manifest does not match dropped fields")
    if len(dependency_fields) != len(set(dependency_fields)):
        raise AgentReceiptError("duplicate dependency-drop receipt field")
    dependency_by_field = {entry["corresponding_receipt_field"]: entry for entry in dependency_entries}
    for field_path, trust_class in trust_by_field.items():
        if field_path in SELF_BOUND_FIELDS:
            continue
        if trust_class == "omitted":
            field = _field_from_pointer(field_path)
            if receipt[field] is not None:
                raise AgentReceiptError(f"omitted field {field_path} must be null")
            continue
        entries = evidence_by_field.get(field_path, [])
        if not entries:
            raise AgentReceiptError(f"missing evidence for {field_path}")
        aggregate = max(TRUST_CLASS_RANK[entry["trust_class"]] for entry in entries)
        if aggregate < TRUST_CLASS_RANK[trust_class]:
            raise AgentReceiptError(f"insufficient evidence trust class for {field_path}")
        compatible_kinds = EVIDENCE_KINDS_BY_TRUST_CLASS[trust_class]
        if not any(
            entry["trust_class"] == trust_class and entry["evidence_kind"] in compatible_kinds
            for entry in entries
        ):
            raise AgentReceiptError(f"{trust_class} field {field_path} lacks compatible evidence")
        if trust_class == "dependency_dropped":
            dependency_entry = dependency_by_field[field_path]
            field = _field_from_pointer(field_path)
            if dependency_entry["replacement_commitment"] != receipt[field]:
                raise AgentReceiptError(f"dependency-dropped field {field_path} replacement mismatch")
            required = dependency_entry["required_subproof_or_attestation"]
            if required is None:
                raise AgentReceiptError(f"dependency-dropped field {field_path} lacks required support")
            if required["kind"] != "subreceipt":
                raise AgentReceiptError(f"dependency-dropped field {field_path} support must be a subreceipt")
            if required["commitment"] != dependency_entry["replacement_commitment"]:
                raise AgentReceiptError(f"dependency-dropped field {field_path} support commitment mismatch")
            if not any(
                entry["trust_class"] == "dependency_dropped"
                and entry["evidence_kind"] == required["kind"]
                for entry in entries
            ):
                raise AgentReceiptError(f"dependency-dropped field {field_path} lacks required evidence kind")

    expected_receipt_commitment = commitment_for(
        _receipt_payload_for_commitment(receipt),
        "agent-step-receipt-v1.receipt",
    )
    if receipt["receipt_commitment"] != expected_receipt_commitment:
        raise AgentReceiptError("receipt_commitment mismatch")
    return True


def recompute_receipt_commitment(bundle: dict[str, Any]) -> None:
    bundle["receipt"]["receipt_commitment"] = commitment_for(
        _receipt_payload_for_commitment(bundle["receipt"]),
        "agent-step-receipt-v1.receipt",
    )


def recompute_manifest_commitments(bundle: dict[str, Any]) -> None:
    bundle["receipt"]["dependency_drop_manifest_commitment"] = commitment_for(
        bundle["dependency_drop_manifest"],
        "agent-step-receipt-v1.dependency-drop-manifest",
    )
    bundle["receipt"]["evidence_manifest_commitment"] = commitment_for(
        bundle["evidence_manifest"],
        "agent-step-receipt-v1.evidence-manifest",
    )
    recompute_receipt_commitment(bundle)


def _mutate_field(field: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def mutate(bundle: dict[str, Any]) -> None:
        # Deliberately leave evidence entries untouched: these cases check that
        # a receipt field cannot be relabeled against stale source evidence.
        bundle["receipt"][field] = value
        recompute_receipt_commitment(bundle)

    return mutate


def _mutation_scope(name: str) -> str:
    if name in MUTATION_FIELDS:
        return "receipt-field-stale-evidence"
    if name == "dependency_drop_manifest":
        return "stale-dependency-manifest-commitment"
    if name == "evidence_manifest":
        return "stale-evidence-manifest-commitment"
    if name == "trust_class_upgrade_without_proof":
        return "unsupported-trust-upgrade"
    raise AgentReceiptError(f"unknown mutation case {name!r}")


def mutation_cases() -> dict[str, Callable[[dict[str, Any]], None]]:
    cases = {
        name: _mutate_field(field, f"tampered-{name}")
        for name, field in MUTATION_FIELDS.items()
    }

    def mutate_dependency_drop_manifest(bundle: dict[str, Any]) -> None:
        bundle["receipt"]["dependency_drop_manifest_commitment"] = commitment_for(
            "tampered-dependency-manifest",
            "toy",
        )
        recompute_receipt_commitment(bundle)

    cases["dependency_drop_manifest"] = mutate_dependency_drop_manifest

    def mutate_evidence_manifest(bundle: dict[str, Any]) -> None:
        bundle["receipt"]["evidence_manifest_commitment"] = commitment_for(
            "tampered-evidence-manifest",
            "toy",
        )
        recompute_receipt_commitment(bundle)

    cases["evidence_manifest"] = mutate_evidence_manifest

    def upgrade_trust_class(bundle: dict[str, Any]) -> None:
        for entry in bundle["receipt"]["field_trust_class_vector"]:
            if entry["field_path"] == "/model_identity":
                entry["trust_class"] = "proved"
        recompute_receipt_commitment(bundle)

    cases["trust_class_upgrade_without_proof"] = upgrade_trust_class
    return cases


def make_omitted_tool_receipt_bundle() -> dict[str, Any]:
    bundle = build_valid_bundle()
    receipt = bundle["receipt"]
    receipt["tool_receipts_root"] = None
    for entry in receipt["field_trust_class_vector"]:
        if entry["field_path"] == "/tool_receipts_root":
            entry["trust_class"] = "omitted"
    bundle["evidence_manifest"]["entries"] = [
        entry
        for entry in bundle["evidence_manifest"]["entries"]
        if entry["corresponding_receipt_field"] != "/tool_receipts_root"
    ]
    recompute_manifest_commitments(bundle)
    return bundle


def make_dependency_dropped_model_receipt_bundle() -> dict[str, Any]:
    bundle = build_valid_bundle()
    receipt = bundle["receipt"]
    for entry in receipt["field_trust_class_vector"]:
        if entry["field_path"] == "/model_receipt_commitment":
            entry["trust_class"] = "dependency_dropped"
    for entry in bundle["evidence_manifest"]["entries"]:
        if entry["corresponding_receipt_field"] == "/model_receipt_commitment":
            entry["evidence_kind"] = "subreceipt"
            entry["trust_class"] = "dependency_dropped"
    bundle["dependency_drop_manifest"]["entries"] = [
        {
            "dependency_id": "urn:agent-step:dependency:model-receipt:0",
            "dependency_kind": "model_receipt",
            "source_commitment": commitment_for("model-receipt-source", "toy"),
            "replacement_commitment": receipt["model_receipt_commitment"],
            "replacement_receipt_version": RECEIPT_VERSION,
            "trust_class": "dependency_dropped",
            "verifier_domain": VERIFIER_DOMAIN,
            "corresponding_receipt_field": "/model_receipt_commitment",
            "reason_for_drop": "model receipt replay replaced by typed receipt commitment",
            "required_subproof_or_attestation": {
                "kind": "subreceipt",
                "commitment": receipt["model_receipt_commitment"],
                "verifier_domain": VERIFIER_DOMAIN,
            },
            "non_claims": ["does-not-prove-agent-truthfulness"],
        }
    ]
    recompute_manifest_commitments(bundle)
    return bundle


def run_all_mutations() -> list[dict[str, Any]]:
    results = []
    for name, mutate in mutation_cases().items():
        bundle = build_valid_bundle()
        mutate(bundle)
        try:
            verify_bundle(bundle)
        except AgentReceiptError as error:
            results.append(
                {
                    "mutation": name,
                    "scope": _mutation_scope(name),
                    "rejected": True,
                    "error": str(error),
                }
            )
        else:
            results.append(
                {
                    "mutation": name,
                    "scope": _mutation_scope(name),
                    "rejected": False,
                    "error": "",
                }
            )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON results")
    args = parser.parse_args(argv)

    verify_bundle(build_valid_bundle())
    results = run_all_mutations()
    if args.json:
        print(json.dumps({"schema": "agent-step-relabeling-harness-v1", "results": results}, indent=2))
    else:
        for result in results:
            status = "rejected" if result["rejected"] else "SURVIVED"
            print(f"{result['mutation']}: {status}")
    return 0 if all(result["rejected"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
