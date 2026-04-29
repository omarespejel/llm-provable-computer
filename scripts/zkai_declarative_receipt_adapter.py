#!/usr/bin/env python3
"""Declarative policy adapter for AgentStepReceiptV1 conformance checks.

This adapter is intentionally separate from the Python mutation oracle and the
Rust production verifier. It consumes a checked policy document and verifies
receipt bundles by recomputing the same public commitment predicates from the
serialized artifact under test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-agent-step-receipt-declarative-policy-2026-04.json"
)
ADAPTER_SCHEMA = "agent-step-receipt-declarative-policy-adapter-v1"
POLICY_SCHEMA = "agent-step-receipt-declarative-policy-v1"
EVIDENCE_ID_RE = re.compile(
    r"^urn:agent-step:evidence:[a-z0-9][a-z0-9._-]{0,63}:[a-z0-9][a-z0-9._-]{0,127}$"
)
DEPENDENCY_ID_RE = re.compile(
    r"^urn:agent-step:dependency:[a-z0-9][a-z0-9._-]{0,63}:[a-z0-9][a-z0-9._-]{0,127}$"
)
SCHEMA_VERSION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,127}$")


class DeclarativeReceiptError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DeclarativeReceiptError(f"duplicate JSON object key {key!r}")
        out[key] = value
    return out


def _load_json_file(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as err:
        raise DeclarativeReceiptError(f"invalid JSON: {err}") from err


def _walk_json(value: Any) -> None:
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise DeclarativeReceiptError("non-NFC string")
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, int):
        return
    elif isinstance(value, float):
        raise DeclarativeReceiptError("floating point values are not allowed")
    elif isinstance(value, list):
        for item in value:
            _walk_json(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise DeclarativeReceiptError("non-string object key")
            _walk_json(key)
            _walk_json(item)
    else:
        raise DeclarativeReceiptError(f"unsupported JSON value type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    _walk_json(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _policy_sha256(policy: dict[str, Any]) -> str:
    return _sha256_hex(canonical_json_bytes(policy))


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DeclarativeReceiptError(f"{label} must be an object")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise DeclarativeReceiptError(f"{label} must be a string")
    return value


def _require_string_set(policy: dict[str, Any], key: str) -> set[str]:
    values = policy.get(key)
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise DeclarativeReceiptError(f"policy {key} must be a string list")
    return set(values)


def load_policy(policy_path: pathlib.Path) -> dict[str, Any]:
    policy = require_object(_load_json_file(policy_path), "policy")
    if policy.get("schema") != POLICY_SCHEMA:
        raise DeclarativeReceiptError(f"unsupported policy schema {policy.get('schema')!r}")

    required = {
        "schema",
        "allowed_replacement_receipt_versions",
        "dependency_kinds",
        "domain_separators",
        "evidence_kinds",
        "evidence_kinds_by_trust_class",
        "hash_lengths",
        "manifest_versions",
        "proof_backends",
        "receipt_commitment_fields",
        "receipt_fields",
        "receipt_optional_string_fields",
        "receipt_parser_versions",
        "receipt_versions",
        "receipt_string_fields",
        "required_subfact_kinds",
        "self_bound_fields",
        "trust_class_rank",
        "verifier_domains",
    }
    if set(policy) != required:
        raise DeclarativeReceiptError("policy has missing or unexpected keys")
    _require_string_set(policy, "receipt_fields")
    _require_string_set(policy, "self_bound_fields")
    _require_string_set(policy, "verifier_domains")
    _require_string_set(policy, "receipt_versions")
    _require_string_set(policy, "dependency_kinds")
    _require_string_set(policy, "evidence_kinds")
    _require_string_set(policy, "required_subfact_kinds")
    _require_string_set(policy, "allowed_replacement_receipt_versions")
    receipt_fields = _require_string_set(policy, "receipt_fields")
    string_fields = _require_string_set(policy, "receipt_string_fields")
    optional_string_fields = _require_string_set(policy, "receipt_optional_string_fields")
    commitment_fields = _require_string_set(policy, "receipt_commitment_fields")
    if string_fields & optional_string_fields:
        raise DeclarativeReceiptError("policy string and optional-string receipt fields overlap")
    if (string_fields | optional_string_fields | {"field_trust_class_vector"}) != receipt_fields:
        raise DeclarativeReceiptError("policy receipt field type coverage mismatch")
    if not commitment_fields.issubset(string_fields | optional_string_fields):
        raise DeclarativeReceiptError("policy commitment fields must be string or optional-string fields")
    return policy


def _field_path(field: str) -> str:
    return f"/{field}"


def _field_from_pointer(policy: dict[str, Any], pointer: str) -> str:
    if not pointer.startswith("/"):
        raise DeclarativeReceiptError(f"invalid JSON Pointer {pointer!r}")
    field = pointer[1:]
    if "/" in field or "~" in field:
        raise DeclarativeReceiptError(f"unsupported nested JSON Pointer {pointer!r}")
    if field not in set(policy["receipt_fields"]):
        raise DeclarativeReceiptError(f"unknown receipt field {pointer!r}")
    return field


def _validate_schema_version(value: Any, label: str) -> None:
    if not isinstance(value, str) or SCHEMA_VERSION_RE.fullmatch(value) is None:
        raise DeclarativeReceiptError(f"{label} must be an ASCII schema-version string")


def _validate_commitment(policy: dict[str, Any], value: Any, label: str) -> None:
    if not isinstance(value, str) or ":" not in value:
        raise DeclarativeReceiptError(f"{label} commitment must be algorithm:hex")
    algorithm, digest = value.split(":", 1)
    expected_len = policy["hash_lengths"].get(algorithm)
    if expected_len is None:
        raise DeclarativeReceiptError(f"{label} uses unsupported algorithm {algorithm!r}")
    if len(digest) != expected_len or re.fullmatch(r"[0-9a-f]+", digest) is None:
        raise DeclarativeReceiptError(f"{label} digest has invalid length or casing")


def _validate_sorted_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise DeclarativeReceiptError(f"{label} must be a list")
    strings = [require_string(item, label) for item in value]
    if strings != sorted(strings, key=lambda item: item.encode("utf-8")):
        raise DeclarativeReceiptError(f"{label} must be sorted")
    if len(strings) != len(set(strings)):
        raise DeclarativeReceiptError(f"duplicate {label} entry")
    return strings


def _verify_receipt_field_types(policy: dict[str, Any], receipt: dict[str, Any]) -> None:
    for field in policy["receipt_string_fields"]:
        if not isinstance(receipt[field], str):
            raise DeclarativeReceiptError(f"receipt field /{field} must be a string")
    for field in policy["receipt_optional_string_fields"]:
        if receipt[field] is not None and not isinstance(receipt[field], str):
            raise DeclarativeReceiptError(f"receipt field /{field} must be a string or null")
    for field in policy["receipt_commitment_fields"]:
        if receipt[field] is not None:
            _validate_commitment(policy, receipt[field], f"receipt field /{field}")


def _commitment_for(policy: dict[str, Any], value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _receipt_payload_for_commitment(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(receipt))
    payload["receipt_commitment"] = None
    return payload


def _evidence_commitment_for_field(policy: dict[str, Any], field_path: str, value: Any) -> str:
    return _commitment_for(
        policy,
        {"field": field_path, "value": value},
        policy["domain_separators"]["evidence_field_binding"],
    )


def _verify_trust_vector(policy: dict[str, Any], receipt: dict[str, Any]) -> dict[str, str]:
    rank = policy["trust_class_rank"]
    vector = receipt["field_trust_class_vector"]
    if not isinstance(vector, list):
        raise DeclarativeReceiptError("field_trust_class_vector must be a list")
    paths: list[str] = []
    trust_by_field: dict[str, str] = {}
    for raw in vector:
        entry = require_object(raw, "trust-class entry")
        if set(entry) != {"field_path", "trust_class"}:
            raise DeclarativeReceiptError("trust-class entry has unexpected keys")
        path = require_string(entry["field_path"], "trust-class field path")
        trust_class = require_string(entry["trust_class"], "trust class")
        if trust_class not in rank:
            raise DeclarativeReceiptError(f"unknown trust class {trust_class!r}")
        _field_from_pointer(policy, path)
        if path in trust_by_field:
            raise DeclarativeReceiptError(f"duplicate trust vector path {path}")
        paths.append(path)
        trust_by_field[path] = trust_class
    if paths != sorted(paths, key=lambda value: value.encode("utf-8")):
        raise DeclarativeReceiptError("field_trust_class_vector is not sorted by field path bytes")
    expected = sorted((_field_path(field) for field in policy["receipt_fields"]), key=lambda value: value.encode("utf-8"))
    if paths != expected:
        raise DeclarativeReceiptError("field_trust_class_vector does not cover every receipt field")
    return trust_by_field


def _verify_evidence_manifest(
    policy: dict[str, Any],
    manifest: dict[str, Any],
    receipt: dict[str, Any],
    trust_by_field: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    if set(manifest) != {"manifest_version", "entries"}:
        raise DeclarativeReceiptError("evidence manifest has unexpected keys")
    if manifest["manifest_version"] != policy["manifest_versions"]["evidence_manifest"]:
        raise DeclarativeReceiptError("unsupported evidence manifest version")
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise DeclarativeReceiptError("evidence entries must be a list")
    entries = [require_object(entry, "evidence entry") for entry in entries]
    expected_keys = {
        "evidence_id",
        "evidence_kind",
        "commitment",
        "trust_class",
        "verifier_domain",
        "corresponding_receipt_field",
        "non_claims",
    }
    for entry in entries:
        if set(entry) != expected_keys:
            raise DeclarativeReceiptError("evidence entry has unexpected keys")
    ids = [require_string(entry["evidence_id"], "evidence_id") for entry in entries]
    if ids != sorted(ids, key=lambda value: value.encode("utf-8")):
        raise DeclarativeReceiptError("evidence entries are not sorted by evidence_id bytes")
    if len(ids) != len(set(ids)):
        raise DeclarativeReceiptError("duplicate evidence_id")

    by_field: dict[str, list[dict[str, Any]]] = {}
    evidence_kinds = set(policy["evidence_kinds"])
    rank = policy["trust_class_rank"]
    verifier_domains = set(policy["verifier_domains"])
    for entry in entries:
        evidence_id = require_string(entry["evidence_id"], "evidence_id")
        evidence_kind = require_string(entry["evidence_kind"], "evidence kind")
        trust_class = require_string(entry["trust_class"], "evidence trust class")
        verifier_domain = require_string(entry["verifier_domain"], "evidence verifier domain")
        field_path = require_string(entry["corresponding_receipt_field"], "evidence receipt field")
        if EVIDENCE_ID_RE.fullmatch(evidence_id) is None:
            raise DeclarativeReceiptError("invalid evidence_id")
        if evidence_kind not in evidence_kinds:
            raise DeclarativeReceiptError("unknown evidence kind")
        if trust_class not in rank:
            raise DeclarativeReceiptError("unknown evidence trust class")
        if verifier_domain not in verifier_domains:
            raise DeclarativeReceiptError("evidence verifier domain mismatch")
        _validate_commitment(policy, entry["commitment"], "evidence")
        _validate_sorted_string_list(entry["non_claims"], "evidence non_claims")
        if field_path not in trust_by_field:
            raise DeclarativeReceiptError("evidence points at unknown receipt field")
        if field_path in set(policy["self_bound_fields"]):
            raise DeclarativeReceiptError("evidence points at self-bound receipt field")
        if trust_by_field[field_path] == "omitted":
            raise DeclarativeReceiptError("evidence points at omitted receipt field")
        field = _field_from_pointer(policy, field_path)
        expected = _evidence_commitment_for_field(policy, field_path, receipt[field])
        if entry["commitment"] != expected:
            raise DeclarativeReceiptError(f"evidence commitment does not bind {field_path}")
        by_field.setdefault(field_path, []).append(entry)
    return by_field


def _verify_dependency_manifest(policy: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if set(manifest) != {"manifest_version", "entries"}:
        raise DeclarativeReceiptError("dependency-drop manifest has unexpected keys")
    if manifest["manifest_version"] != policy["manifest_versions"]["dependency_drop_manifest"]:
        raise DeclarativeReceiptError("unsupported dependency-drop manifest version")
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise DeclarativeReceiptError("dependency-drop entries must be a list")
    entries = [require_object(entry, "dependency-drop entry") for entry in entries]
    expected_keys = {
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
    }
    for entry in entries:
        if set(entry) != expected_keys:
            raise DeclarativeReceiptError("dependency-drop entry has unexpected keys")
    ids = [require_string(entry["dependency_id"], "dependency_id") for entry in entries]
    if ids != sorted(ids, key=lambda value: value.encode("utf-8")):
        raise DeclarativeReceiptError("dependency-drop entries are not sorted by dependency_id bytes")
    if len(ids) != len(set(ids)):
        raise DeclarativeReceiptError("duplicate dependency_id")

    dependency_kinds = set(policy["dependency_kinds"])
    rank = policy["trust_class_rank"]
    verifier_domains = set(policy["verifier_domains"])
    receipt_paths = {_field_path(field) for field in policy["receipt_fields"]}
    self_bound = set(policy["self_bound_fields"])
    required_kinds = set(policy["required_subfact_kinds"])
    replacement_versions = set(policy["allowed_replacement_receipt_versions"])
    for entry in entries:
        dependency_id = require_string(entry["dependency_id"], "dependency_id")
        dependency_kind = require_string(entry["dependency_kind"], "dependency kind")
        trust_class = require_string(entry["trust_class"], "dependency trust class")
        verifier_domain = require_string(entry["verifier_domain"], "dependency verifier domain")
        field_path = require_string(entry["corresponding_receipt_field"], "dependency receipt field")
        if DEPENDENCY_ID_RE.fullmatch(dependency_id) is None:
            raise DeclarativeReceiptError("invalid dependency_id")
        if dependency_kind not in dependency_kinds:
            raise DeclarativeReceiptError("unknown dependency kind")
        _validate_commitment(policy, entry["source_commitment"], "dependency source")
        _validate_commitment(policy, entry["replacement_commitment"], "dependency replacement")
        _validate_schema_version(entry["replacement_receipt_version"], "replacement receipt version")
        if entry["replacement_receipt_version"] not in replacement_versions:
            raise DeclarativeReceiptError("unsupported replacement receipt version")
        if trust_class not in rank:
            raise DeclarativeReceiptError("unknown dependency trust class")
        if trust_class != "dependency_dropped":
            raise DeclarativeReceiptError("dependency-drop entry must use dependency_dropped trust class")
        if verifier_domain not in verifier_domains:
            raise DeclarativeReceiptError("dependency-drop verifier domain mismatch")
        if field_path not in receipt_paths:
            raise DeclarativeReceiptError("dependency-drop entry points at unknown receipt field")
        if field_path in self_bound:
            raise DeclarativeReceiptError("dependency-drop entry points at self-bound field")
        if not isinstance(entry["reason_for_drop"], str) or not entry["reason_for_drop"]:
            raise DeclarativeReceiptError("dependency-drop reason must be a non-empty string")
        required = entry["required_subproof_or_attestation"]
        if required is not None:
            required = require_object(required, "required subproof/attestation")
            if set(required) != {"kind", "commitment", "verifier_domain"}:
                raise DeclarativeReceiptError("required subproof/attestation has unexpected keys")
            required_kind = require_string(required["kind"], "required subproof/attestation kind")
            required_domain = require_string(
                required["verifier_domain"],
                "required subproof/attestation verifier domain",
            )
            if required_kind not in required_kinds:
                raise DeclarativeReceiptError("unknown required subproof/attestation kind")
            _validate_commitment(policy, required["commitment"], "required subproof/attestation")
            if required_domain not in verifier_domains:
                raise DeclarativeReceiptError("required subproof/attestation verifier domain mismatch")
        _validate_sorted_string_list(entry["non_claims"], "dependency non_claims")
    return entries


def verify_bundle(policy: dict[str, Any], bundle: dict[str, Any]) -> bool:
    bundle = require_object(bundle, "bundle")
    if set(bundle) != {"receipt", "evidence_manifest", "dependency_drop_manifest"}:
        raise DeclarativeReceiptError("bundle has unexpected keys")
    receipt = require_object(bundle["receipt"], "receipt")
    evidence_manifest = require_object(bundle["evidence_manifest"], "evidence manifest")
    dependency_manifest = require_object(bundle["dependency_drop_manifest"], "dependency-drop manifest")
    if set(receipt) != set(policy["receipt_fields"]):
        raise DeclarativeReceiptError("receipt has missing or unexpected fields")
    _verify_receipt_field_types(policy, receipt)

    if receipt["receipt_version"] not in set(policy["receipt_versions"]):
        raise DeclarativeReceiptError("unsupported receipt version")
    if receipt["verifier_domain"] not in set(policy["verifier_domains"]):
        raise DeclarativeReceiptError("unsupported verifier domain")
    parser_versions = policy["receipt_parser_versions"].get(receipt["receipt_version"], [])
    if receipt["receipt_parser_version"] not in set(parser_versions):
        raise DeclarativeReceiptError("unsupported receipt parser version")
    backend_pair = {
        "proof_backend": receipt["proof_backend"],
        "proof_backend_version": receipt["proof_backend_version"],
    }
    if backend_pair not in policy["proof_backends"]:
        raise DeclarativeReceiptError("unsupported proof backend version")

    expected_dependency_commitment = _commitment_for(
        policy,
        dependency_manifest,
        policy["domain_separators"]["dependency_drop_manifest"],
    )
    if receipt["dependency_drop_manifest_commitment"] != expected_dependency_commitment:
        raise DeclarativeReceiptError("dependency_drop_manifest_commitment mismatch")
    expected_evidence_commitment = _commitment_for(
        policy,
        evidence_manifest,
        policy["domain_separators"]["evidence_manifest"],
    )
    if receipt["evidence_manifest_commitment"] != expected_evidence_commitment:
        raise DeclarativeReceiptError("evidence_manifest_commitment mismatch")

    trust_by_field = _verify_trust_vector(policy, receipt)
    evidence_by_field = _verify_evidence_manifest(policy, evidence_manifest, receipt, trust_by_field)
    dependency_entries = _verify_dependency_manifest(policy, dependency_manifest)
    dropped_fields = {
        field_path
        for field_path, trust_class in trust_by_field.items()
        if trust_class == "dependency_dropped"
    }
    dependency_fields = [entry["corresponding_receipt_field"] for entry in dependency_entries]
    if set(dependency_fields) != dropped_fields:
        raise DeclarativeReceiptError("dependency-drop manifest does not match dropped fields")
    if len(dependency_fields) != len(set(dependency_fields)):
        raise DeclarativeReceiptError("duplicate dependency-drop receipt field")
    dependency_by_field = {entry["corresponding_receipt_field"]: entry for entry in dependency_entries}

    rank = policy["trust_class_rank"]
    compatible_by_trust = {
        trust_class: set(kinds)
        for trust_class, kinds in policy["evidence_kinds_by_trust_class"].items()
    }
    for field_path, trust_class in trust_by_field.items():
        if field_path in set(policy["self_bound_fields"]):
            continue
        field = _field_from_pointer(policy, field_path)
        if trust_class == "omitted":
            if receipt[field] is not None:
                raise DeclarativeReceiptError(f"omitted field {field_path} must be null")
            if field_path in evidence_by_field or field_path in dependency_by_field:
                raise DeclarativeReceiptError(f"omitted field {field_path} must not have evidence")
            continue
        entries = evidence_by_field.get(field_path, [])
        if not entries:
            raise DeclarativeReceiptError(f"missing evidence for {field_path}")
        aggregate = max(rank[entry["trust_class"]] for entry in entries)
        if aggregate < rank[trust_class]:
            raise DeclarativeReceiptError(f"insufficient evidence trust class for {field_path}")
        compatible = compatible_by_trust.get(trust_class, set())
        if not any(
            entry["trust_class"] == trust_class and entry["evidence_kind"] in compatible
            for entry in entries
        ):
            raise DeclarativeReceiptError(f"{trust_class} field {field_path} lacks compatible evidence")
        if trust_class == "dependency_dropped":
            dependency_entry = dependency_by_field[field_path]
            if dependency_entry["replacement_commitment"] != receipt[field]:
                raise DeclarativeReceiptError(f"dependency-dropped field {field_path} replacement mismatch")
            required = dependency_entry["required_subproof_or_attestation"]
            if required is None:
                raise DeclarativeReceiptError(f"dependency-dropped field {field_path} lacks required support")
            if required["kind"] != "subreceipt":
                raise DeclarativeReceiptError(f"dependency-dropped field {field_path} support must be a subreceipt")
            if required["commitment"] != dependency_entry["replacement_commitment"]:
                raise DeclarativeReceiptError(f"dependency-dropped field {field_path} support commitment mismatch")
            if not any(
                entry["trust_class"] == "dependency_dropped"
                and entry["evidence_kind"] == required["kind"]
                for entry in entries
            ):
                raise DeclarativeReceiptError(f"dependency-dropped field {field_path} lacks required evidence kind")

    expected_receipt_commitment = _commitment_for(
        policy,
        _receipt_payload_for_commitment(receipt),
        policy["domain_separators"]["receipt"],
    )
    if receipt["receipt_commitment"] != expected_receipt_commitment:
        raise DeclarativeReceiptError("receipt_commitment mismatch")
    return True


def _split_case_arg(index: int, arg: str) -> tuple[str, pathlib.Path]:
    if "=" in arg:
        case_id, raw_path = arg.split("=", 1)
    else:
        case_id, raw_path = f"case_{index}", arg
    if not case_id:
        raise DeclarativeReceiptError("case_id must not be empty")
    return case_id, pathlib.Path(raw_path)


def _case_result(policy: dict[str, Any], case_id: str, path: pathlib.Path) -> dict[str, Any]:
    try:
        bundle = _load_json_file(path)
        verify_bundle(policy, bundle)
    except DeclarativeReceiptError as err:
        return {"case_id": case_id, "accepted": False, "error": str(err)}
    except OSError as err:
        return {"case_id": case_id, "accepted": False, "error": f"I/O error: {err}"}
    return {"case_id": case_id, "accepted": True, "error": ""}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--policy",
        type=pathlib.Path,
        default=DEFAULT_POLICY_PATH,
        help="checked declarative policy JSON",
    )
    parser.add_argument("cases", nargs="+", help="case_id=path JSON bundle inputs")
    args = parser.parse_args(argv)

    policy_path = args.policy.resolve()
    try:
        policy = load_policy(policy_path)
        results = [
            _case_result(policy, case_id, path)
            for case_id, path in (_split_case_arg(index, arg) for index, arg in enumerate(args.cases))
        ]
    except DeclarativeReceiptError as err:
        print(f"declarative adapter setup failed: {err}", file=sys.stderr)
        return 2

    try:
        policy_label = str(policy_path.relative_to(ROOT))
    except ValueError:
        policy_label = str(policy_path)

    print(
        json.dumps(
            {
                "schema": ADAPTER_SCHEMA,
                "policy_path": policy_label,
                "policy_sha256": _policy_sha256(policy),
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
