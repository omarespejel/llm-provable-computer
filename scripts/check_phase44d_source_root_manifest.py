#!/usr/bin/env python3
"""Phase44D source-emitted root manifest/provenance checker."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Iterable


SCHEMA = "phase44d-source-root-manifest-v1"
EVIDENCE_SCHEMA = "phase44d-source-root-manifest-evidence-v1"
PROBE = "phase44d-source-emitted-root-manifest"
ISSUE_ID = 180
SOURCE_SURFACE_VERSION = "phase44d-final-boundary-source-v1"
DEFAULT_TOTAL_STEPS = 8
DEFAULT_MANIFEST = pathlib.Path("docs/engineering/design/phase44d_source_root_manifest.json")
DEFAULT_EVIDENCE = pathlib.Path("docs/engineering/design/phase44d_source_root_manifest.evidence.json")
HASH32_RE = re.compile(r"^[0-9a-f]{64}$")

TOP_LEVEL_KEYS = (
    "schema",
    "probe",
    "issue_id",
    "source_surface_version",
    "total_steps",
    "log_size",
    "compact_root",
    "source_root",
    "source_emitted_root",
    "compact_root_preimage",
    "source_root_preimage",
    "kill_labels",
    "mutation_checks",
)
COMPACT_PREIMAGE_KEYS = (
    "issue_id",
    "source_surface_version",
    "total_steps",
    "log_size",
    "compact_rows",
)
SOURCE_PREIMAGE_KEYS = (
    "issue_id",
    "source_surface_version",
    "total_steps",
    "log_size",
    "compact_root",
    "source_rows",
)
MUTATION_CHECK_KEYS = ("label", "expect", "description")
KILL_LABELS = (
    "issue_id_drift",
    "source_surface_version_drift",
    "total_steps_drift",
    "log_size_drift",
    "compact_root_drift",
    "source_root_drift",
    "source_emitted_root_drift",
    "compact_row_reordering",
    "source_row_reordering",
    "missing_compact_root_preimage",
    "missing_source_root_preimage",
    "missing_source_root_field",
)


class Phase44DError(Exception):
    """Raised when a manifest fails the Phase44D source-root contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash32_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash32_json(tag: str, value: Any) -> str:
    return hash32_text(canonical_json({"tag": tag, "value": value}))


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Phase44DError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise Phase44DError(f"{path} must contain a JSON object")
    return data


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase44DError(message)


def require_exact_keys(value: Any, expected_keys: Iterable[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    expected = set(expected_keys)
    actual = set(value.keys())
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    require(not missing, f"{label} missing required fields: {missing}")
    require(not extra, f"{label} has unexpected fields: {extra}")
    return value


def require_int(value: Any, label: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{label} must be an integer")
    return value


def require_hash32(value: Any, label: str) -> str:
    require(isinstance(value, str), f"{label} must be a lowercase hex string")
    require(bool(HASH32_RE.match(value)), f"{label} must be a 64-character lowercase hex string")
    return value


def is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


def ilog2_pow2(value: int) -> int:
    require(is_power_of_two(value), f"total_steps {value} must be a power of two")
    return value.bit_length() - 1


def expected_compact_rows(total_steps: int) -> list[str]:
    return [f"phase44d/compact/step-{index}" for index in range(total_steps)]


def expected_source_rows(total_steps: int) -> list[str]:
    return [f"phase44d/source/step-{index}" for index in range(total_steps)]


def validate_step_shape(total_steps: int, log_size: int, label: str) -> None:
    require(total_steps > 0, f"{label}.total_steps must be positive")
    require(is_power_of_two(total_steps), f"{label}.total_steps must be a power of two")
    require(log_size == ilog2_pow2(total_steps), f"{label}.log_size must equal ilog2(total_steps)")


def validate_common_binding(value: dict[str, Any], label: str) -> tuple[int, int]:
    issue_id = require_int(value.get("issue_id"), f"{label}.issue_id")
    total_steps = require_int(value.get("total_steps"), f"{label}.total_steps")
    log_size = require_int(value.get("log_size"), f"{label}.log_size")
    require(issue_id == ISSUE_ID, f"{label}.issue_id must equal {ISSUE_ID}")
    require(
        value.get("source_surface_version") == SOURCE_SURFACE_VERSION,
        f"{label}.source_surface_version must equal {SOURCE_SURFACE_VERSION!r}",
    )
    validate_step_shape(total_steps, log_size, label)
    return total_steps, log_size


def validate_compact_preimage(preimage: Any) -> tuple[int, int, str]:
    compact = require_exact_keys(preimage, COMPACT_PREIMAGE_KEYS, "compact_root_preimage")
    total_steps, log_size = validate_common_binding(compact, "compact_root_preimage")
    rows = compact.get("compact_rows")
    require(isinstance(rows, list), "compact_root_preimage.compact_rows must be a list")
    require(rows == expected_compact_rows(total_steps), "compact rows must preserve canonical order")
    require(len(rows) == total_steps, "compact row count must equal total_steps")
    require(len(set(rows)) == len(rows), "compact rows must be unique")
    return total_steps, log_size, hash32_json("phase44d-compact-root-v1", compact)


def validate_source_preimage(preimage: Any, expected_compact_root: str) -> tuple[int, int, str]:
    source = require_exact_keys(preimage, SOURCE_PREIMAGE_KEYS, "source_root_preimage")
    total_steps, log_size = validate_common_binding(source, "source_root_preimage")
    compact_root = require_hash32(source.get("compact_root"), "source_root_preimage.compact_root")
    require(compact_root == expected_compact_root, "source_root_preimage.compact_root must match compact_root")
    rows = source.get("source_rows")
    require(isinstance(rows, list), "source_root_preimage.source_rows must be a list")
    require(rows == expected_source_rows(total_steps), "source rows must preserve canonical order")
    require(len(rows) == total_steps, "source row count must equal total_steps")
    require(len(set(rows)) == len(rows), "source rows must be unique")
    return total_steps, log_size, hash32_json("phase44d-source-root-v1", source)


def validate_mutation_catalog(manifest: dict[str, Any]) -> None:
    kill_labels = manifest.get("kill_labels")
    checks = manifest.get("mutation_checks")
    require(isinstance(kill_labels, list), "kill_labels must be a list")
    require(isinstance(checks, list), "mutation_checks must be a list")
    require(tuple(kill_labels) == KILL_LABELS, "kill_labels must match the canonical Phase44D order")
    check_labels: list[str] = []
    for index, item in enumerate(checks):
        item = require_exact_keys(item, MUTATION_CHECK_KEYS, f"mutation_checks[{index}]")
        label = item.get("label")
        expect = item.get("expect")
        description = item.get("description")
        require(isinstance(label, str) and label, f"mutation_checks[{index}].label must be a non-empty string")
        require(expect == "reject", f"mutation_checks[{index}].expect must be 'reject'")
        require(
            isinstance(description, str) and description,
            f"mutation_checks[{index}].description must be a non-empty string",
        )
        check_labels.append(label)
    require(tuple(check_labels) == KILL_LABELS, "mutation_checks labels must match kill_labels in order")


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = require_exact_keys(manifest, TOP_LEVEL_KEYS, "manifest")
    require(manifest.get("schema") == SCHEMA, f"unexpected schema: {manifest.get('schema')!r}")
    require(manifest.get("probe") == PROBE, f"unexpected probe id: {manifest.get('probe')!r}")

    total_steps = require_int(manifest.get("total_steps"), "manifest.total_steps")
    log_size = require_int(manifest.get("log_size"), "manifest.log_size")
    issue_id = require_int(manifest.get("issue_id"), "manifest.issue_id")
    require(issue_id == ISSUE_ID, f"manifest.issue_id must equal {ISSUE_ID}")
    require(
        manifest.get("source_surface_version") == SOURCE_SURFACE_VERSION,
        f"manifest.source_surface_version must equal {SOURCE_SURFACE_VERSION!r}",
    )
    validate_step_shape(total_steps, log_size, "manifest")

    compact_total_steps, compact_log_size, canonical_compact_root = validate_compact_preimage(
        manifest.get("compact_root_preimage")
    )
    compact_root = require_hash32(manifest.get("compact_root"), "manifest.compact_root")
    require(compact_root == canonical_compact_root, "manifest.compact_root must match compact_root_preimage")
    require(compact_total_steps == total_steps, "compact_root_preimage.total_steps must match manifest.total_steps")
    require(compact_log_size == log_size, "compact_root_preimage.log_size must match manifest.log_size")

    source_total_steps, source_log_size, canonical_source_root = validate_source_preimage(
        manifest.get("source_root_preimage"), compact_root
    )
    source_root = require_hash32(manifest.get("source_root"), "manifest.source_root")
    source_emitted_root = require_hash32(manifest.get("source_emitted_root"), "manifest.source_emitted_root")
    require(source_root == canonical_source_root, "manifest.source_root must match source_root_preimage")
    require(source_emitted_root == canonical_source_root, "source_emitted_root must equal canonical source_root")
    require(source_total_steps == total_steps, "source_root_preimage.total_steps must match manifest.total_steps")
    require(source_log_size == log_size, "source_root_preimage.log_size must match manifest.log_size")

    validate_mutation_catalog(manifest)
    return {
        "issue_id": issue_id,
        "source_surface_version": manifest["source_surface_version"],
        "total_steps": total_steps,
        "log_size": log_size,
        "compact_root": compact_root,
        "source_root": source_root,
        "source_emitted_root": source_emitted_root,
    }


def load_manifest(path: pathlib.Path) -> dict[str, Any]:
    manifest = load_json(path)
    validate_manifest(manifest)
    return manifest


def apply_mutation(manifest: dict[str, Any], label: str) -> dict[str, Any]:
    mutated = copy.deepcopy(manifest)
    if label == "issue_id_drift":
        mutated["issue_id"] = ISSUE_ID + 1
    elif label == "source_surface_version_drift":
        mutated["source_surface_version"] = "phase44d-final-boundary-source-v2"
    elif label == "total_steps_drift":
        mutated["total_steps"] = int(mutated["total_steps"]) + 1
    elif label == "log_size_drift":
        mutated["log_size"] = int(mutated["log_size"]) + 1
    elif label == "compact_root_drift":
        mutated["compact_root"] = "0" * 64
    elif label == "source_root_drift":
        mutated["source_root"] = "0" * 64
    elif label == "source_emitted_root_drift":
        mutated["source_emitted_root"] = "0" * 64
    elif label == "compact_row_reordering":
        mutated["compact_root_preimage"]["compact_rows"] = list(reversed(mutated["compact_root_preimage"]["compact_rows"]))
    elif label == "source_row_reordering":
        mutated["source_root_preimage"]["source_rows"] = list(reversed(mutated["source_root_preimage"]["source_rows"]))
    elif label == "missing_compact_root_preimage":
        mutated.pop("compact_root_preimage", None)
    elif label == "missing_source_root_preimage":
        mutated.pop("source_root_preimage", None)
    elif label == "missing_source_root_field":
        mutated.pop("source_root", None)
    else:
        raise Phase44DError(f"unknown kill label: {label}")
    return mutated


def probe_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    validated = validate_manifest(manifest)
    mutation_results: list[dict[str, Any]] = []
    for item in manifest["mutation_checks"]:
        label = item["label"]
        mutated = apply_mutation(manifest, label)
        rejected = False
        rejection_error = ""
        try:
            validate_manifest(mutated)
        except Phase44DError as exc:
            rejected = True
            rejection_error = str(exc)
        require(rejected, f"kill label {label!r} did not reject")
        mutation_results.append(
            {
                "label": label,
                "rejected": rejected,
                "rejection_error": rejection_error,
                "mutation_description": item["description"],
            }
        )

    return {
        "schema": EVIDENCE_SCHEMA,
        "probe": PROBE,
        "issue_id": validated["issue_id"],
        "source_surface_version": validated["source_surface_version"],
        "total_steps": validated["total_steps"],
        "log_size": validated["log_size"],
        "compact_root": validated["compact_root"],
        "source_root": validated["source_root"],
        "source_emitted_root": validated["source_emitted_root"],
        "source_root_fields": ["source_root", "source_emitted_root", "source_root_preimage"],
        "compact_root_fields": ["compact_root", "compact_root_preimage"],
        "manifest_canonical_sha256": hash32_text(canonical_json(manifest)),
        "mutation_results": mutation_results,
    }


def build_default_manifest(total_steps: int = DEFAULT_TOTAL_STEPS) -> dict[str, Any]:
    log_size = ilog2_pow2(total_steps)
    compact_preimage: dict[str, Any] = {
        "issue_id": ISSUE_ID,
        "source_surface_version": SOURCE_SURFACE_VERSION,
        "total_steps": total_steps,
        "log_size": log_size,
        "compact_rows": expected_compact_rows(total_steps),
    }
    compact_root = hash32_json("phase44d-compact-root-v1", compact_preimage)
    source_preimage: dict[str, Any] = {
        "issue_id": ISSUE_ID,
        "source_surface_version": SOURCE_SURFACE_VERSION,
        "total_steps": total_steps,
        "log_size": log_size,
        "compact_root": compact_root,
        "source_rows": expected_source_rows(total_steps),
    }
    source_root = hash32_json("phase44d-source-root-v1", source_preimage)
    descriptions = {
        "issue_id_drift": "issue id must remain bound to issue 180",
        "source_surface_version_drift": "source surface version must not drift",
        "total_steps_drift": "total_steps must match ordered compact/source rows",
        "log_size_drift": "log_size must equal ilog2(total_steps)",
        "compact_root_drift": "compact root must match its canonical preimage",
        "source_root_drift": "source root must match its canonical preimage",
        "source_emitted_root_drift": "source-emitted root must equal source root",
        "compact_row_reordering": "compact row ordering must be canonical",
        "source_row_reordering": "source row ordering must be canonical",
        "missing_compact_root_preimage": "compact root preimage is required",
        "missing_source_root_preimage": "source root preimage is required",
        "missing_source_root_field": "top-level source root is required",
    }
    return {
        "schema": SCHEMA,
        "probe": PROBE,
        "issue_id": ISSUE_ID,
        "source_surface_version": SOURCE_SURFACE_VERSION,
        "total_steps": total_steps,
        "log_size": log_size,
        "compact_root": compact_root,
        "source_root": source_root,
        "source_emitted_root": source_root,
        "compact_root_preimage": compact_preimage,
        "source_root_preimage": source_preimage,
        "kill_labels": list(KILL_LABELS),
        "mutation_checks": [
            {"label": label, "expect": "reject", "description": descriptions[label]} for label in KILL_LABELS
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=DEFAULT_MANIFEST,
        help="Phase44D source-root manifest JSON",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=DEFAULT_EVIDENCE,
        help="where to write deterministic Phase44D evidence JSON",
    )
    parser.add_argument(
        "--write-default-manifest",
        action="store_true",
        help="write the canonical default manifest before validating it",
    )
    parser.add_argument(
        "--total-steps",
        type=int,
        default=DEFAULT_TOTAL_STEPS,
        help="total_steps for --write-default-manifest; must be a power of two",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.write_default_manifest:
            write_json(args.manifest, build_default_manifest(args.total_steps))
        manifest = load_manifest(args.manifest)
        evidence = probe_manifest(manifest)
        write_json(args.output, evidence)
    except Phase44DError as exc:
        print(f"Phase44D source-root manifest check failed: {exc}", file=sys.stderr)
        return 1

    print(f"Phase44D source-root manifest evidence written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
