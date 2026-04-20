#!/usr/bin/env python3
"""Phase44C source-emitted projection-root / canonical source-root probe."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Iterable


SCHEMA = "phase44c-projection-root-binding-manifest-v1"
PROBE = "phase44c-source-emitted-projection-root-binding"
PHASE43_SURFACE_VERSION = "phase43-history-replay-field-projection-v1"
HASH32_RE = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_MANIFEST = pathlib.Path("docs/engineering/design/phase44c-projection-root-manifest.json")
DEFAULT_EVIDENCE = pathlib.Path("target/phase44c-projection-root-probe/evidence.json")


class Phase44CError(Exception):
    """Raised when a supplied manifest fails the Phase44C source checks."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash32_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash32_json(tag: str, value: Any) -> str:
    payload = canonical_json({"tag": tag, "value": value})
    return hash32_text(payload)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise Phase44CError(f"{path} could not be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise Phase44CError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise Phase44CError(f"{path} must contain a JSON object")
    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase44CError(message)


def require_hash32(value: Any, label: str) -> str:
    require(isinstance(value, str), f"{label} must be a lowercase hex string")
    require(bool(HASH32_RE.match(value)), f"{label} must be a 64-character lowercase hex string")
    return value


def is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


def ilog2_pow2(value: int) -> int:
    require(is_power_of_two(value), f"row count {value} must be a power of two")
    return value.bit_length() - 1


def load_manifest(path: pathlib.Path) -> dict[str, Any]:
    manifest = load_json(path)
    require(manifest.get("schema") == SCHEMA, f"unexpected schema: {manifest.get('schema')!r}")
    require(manifest.get("probe") == PROBE, f"unexpected probe id: {manifest.get('probe')!r}")
    require(
        manifest.get("source_surface_version") == PHASE43_SURFACE_VERSION,
        f"unexpected source_surface_version: {manifest.get('source_surface_version')!r}",
    )
    require("canonical_source_root_preimage" in manifest, "missing canonical_source_root_preimage")
    validate_manifest_kill_labels(manifest)
    return manifest


def validate_manifest_kill_labels(manifest: dict[str, Any]) -> None:
    require("kill_labels" in manifest, "missing kill_labels")
    require("mutation_checks" in manifest, "missing mutation_checks")
    require(
        isinstance(manifest["kill_labels"], list) and manifest["kill_labels"],
        "kill_labels must be a non-empty list",
    )
    require(
        isinstance(manifest["mutation_checks"], list) and manifest["mutation_checks"],
        "mutation_checks must be a non-empty list",
    )
    manifest_labels = []
    for index, label in enumerate(manifest["kill_labels"]):
        require(isinstance(label, str), f"kill_labels[{index}] must be a string")
        manifest_labels.append(label)
    check_labels = []
    for index, item in enumerate(manifest["mutation_checks"]):
        require(isinstance(item, dict), "mutation_checks entries must be objects")
        label = item.get("label")
        require(isinstance(label, str), f"mutation_checks[{index}].label must be a string")
        check_labels.append(label)
    require(
        manifest_labels == check_labels,
        "kill_labels must match mutation_checks labels in order",
    )


def load_stwo_source_mechanics(stwo_root: pathlib.Path) -> dict[str, Any]:
    stwo_root = stwo_root.resolve()
    require(stwo_root.is_dir(), f"Stwo source root must be a directory: {stwo_root}")
    require(
        (stwo_root / "crates/stwo/Cargo.toml").exists(),
        f"Stwo source root does not contain crates/stwo/Cargo.toml: {stwo_root}",
    )
    checks = {
        "pcs_mix_root": (
            stwo_root / "crates/stwo/src/prover/pcs/mod.rs",
            ["MC::mix_root(channel, tree.commitment.root())", "commitment.root()"],
        ),
        "fri_root_binding": (
            stwo_root / "crates/stwo/src/prover/fri.rs",
            ["MC::mix_root(channel, layer.merkle_tree.root())", "log_size"],
        ),
        "twiddle_root_coset": (
            stwo_root / "crates/stwo/src/prover/poly/twiddles.rs",
            ["root_coset", "extract_subdomain_twiddles", "domain_log_size", "subdomain_log_size"],
        ),
        "accumulation_root_coset": (
            stwo_root / "crates/stwo/src/prover/air/accumulation.rs",
            ["CanonicCoset::new(log_size + log_expansion).circle_domain()", "root_coset: subdomain.half_coset"],
        ),
    }
    evidence: dict[str, Any] = {}
    for name, (path, markers) in checks.items():
        path = path.resolve()
        require(path.exists(), f"missing cloned Stwo source file: {path}")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise Phase44CError(f"failed to read cloned Stwo source file {path}: {exc}") from exc
        missing = [marker for marker in markers if marker not in text]
        require(not missing, f"{path} is missing required Stwo mechanics markers: {missing}")
        evidence[name] = {
            "path": str(path.relative_to(stwo_root)),
            "markers": list(markers),
        }
    return evidence


def validate_preimage(preimage: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(preimage, dict), "canonical_source_root_preimage must be an object")
    source_version = preimage.get("source_surface_version")
    row_count = preimage.get("projection_row_count")
    log_size = preimage.get("projection_log_size")
    row_labels = preimage.get("row_labels")

    require(source_version == PHASE43_SURFACE_VERSION, f"unexpected preimage source_surface_version: {source_version!r}")
    require(isinstance(row_count, int), "projection_row_count must be an integer")
    require(isinstance(log_size, int), "projection_log_size must be an integer")
    require(isinstance(row_labels, list) and row_labels, "row_labels must be a non-empty list")
    require(len(row_labels) == row_count, "projection_row_count must equal len(row_labels)")
    require(is_power_of_two(row_count), "projection_row_count must be a power of two")
    require(log_size == ilog2_pow2(row_count), "projection_log_size must equal ilog2(projection_row_count)")
    for index, label in enumerate(row_labels):
        require(isinstance(label, str) and label, f"row_labels[{index}] must be a non-empty string")
        require(label == f"phase44c/projection/row-{index}", f"row_labels[{index}] must preserve canonical order")
    require(len(set(row_labels)) == len(row_labels), "row_labels must be unique")
    canonical_payload = {
        "source_surface_version": source_version,
        "projection_row_count": row_count,
        "projection_log_size": log_size,
        "row_labels": row_labels,
    }
    canonical_root = hash32_json("phase44c-projection-root-binding-v1", canonical_payload)
    return {
        "projection_row_count": row_count,
        "projection_log_size": log_size,
        "row_labels": row_labels,
        "canonical_source_root": canonical_root,
    }


def apply_mutation(manifest: dict[str, Any], label: str) -> dict[str, Any]:
    mutated = copy.deepcopy(manifest)
    preimage = mutated["canonical_source_root_preimage"]
    if label == "row_count_drift":
        preimage["projection_row_count"] = int(preimage["projection_row_count"]) + 1
    elif label == "log_size_drift":
        preimage["projection_log_size"] = int(preimage["projection_log_size"]) + 1
    elif label == "row_order_drift":
        preimage["row_labels"] = list(reversed(preimage["row_labels"]))
    elif label == "row_replacement":
        labels = list(preimage["row_labels"])
        labels[0] = "phase44c/projection/row-X"
        preimage["row_labels"] = labels
    elif label == "source_surface_version_drift":
        preimage["source_surface_version"] = "phase43-history-replay-field-projection-v2"
    elif label == "canonical_preimage_truncation":
        preimage.pop("row_labels", None)
    elif label == "binding_alias_drift":
        mutated["probe"] = "phase44c-binding-alias-drift"
    else:
        raise Phase44CError(f"unknown kill label: {label}")
    return mutated


def probe_manifest(manifest: dict[str, Any], stwo_root: pathlib.Path | None = None) -> dict[str, Any]:
    require(manifest.get("schema") == SCHEMA, f"unexpected schema: {manifest.get('schema')!r}")
    require(manifest.get("probe") == PROBE, f"unexpected probe id: {manifest.get('probe')!r}")
    validate_manifest_kill_labels(manifest)
    source_mechanics = load_stwo_source_mechanics(stwo_root) if stwo_root is not None else None
    preimage = manifest.get("canonical_source_root_preimage")
    result = validate_preimage(preimage)
    source_emitted_projection_root = require_hash32(
        manifest.get("source_emitted_projection_root"),
        "source_emitted_projection_root",
    )
    require(
        source_emitted_projection_root == result["canonical_source_root"],
        "source-emitted projection root must match the canonical source-root",
    )

    kill_results: list[dict[str, Any]] = []
    for item in manifest["mutation_checks"]:
        require(isinstance(item, dict), "mutation_checks entries must be objects")
        label = item.get("label")
        expect = item.get("expect")
        require(isinstance(label, str) and label, "mutation check label must be a non-empty string")
        require(expect == "reject", f"mutation check {label!r} must expect rejection")

        mutated = apply_mutation(manifest, label)
        rejected = False
        rejection_error = ""
        try:
            validate_preimage(mutated["canonical_source_root_preimage"])
            require(mutated.get("probe") == PROBE, "probe alias drift detected")
        except Phase44CError as exc:
            rejected = True
            rejection_error = str(exc)
        require(rejected, f"kill label {label!r} did not reject")
        kill_results.append(
            {
                "label": label,
                "rejected": rejected,
                "rejection_error": rejection_error,
                "mutation_description": item.get("description", ""),
            }
        )

    return {
        "schema": "phase44c-projection-root-binding-evidence-v1",
        "probe": PROBE,
        "source_surface_version": manifest["source_surface_version"],
        "source_mechanics": source_mechanics,
        "projection_row_count": result["projection_row_count"],
        "projection_log_size": result["projection_log_size"],
        "source_emitted_projection_root": source_emitted_projection_root,
        "canonical_source_root": result["canonical_source_root"],
        "kill_results": kill_results,
    }


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=DEFAULT_MANIFEST,
        help="phase44c canonical manifest",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=DEFAULT_EVIDENCE,
        help="where to write the probe evidence JSON",
    )
    parser.add_argument(
        "--stwo-root",
        type=pathlib.Path,
        help="optional path to the cloned upstream Stwo source tree; when omitted, source mechanics evidence is absent",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        manifest = load_manifest(args.manifest)
        evidence = probe_manifest(manifest, args.stwo_root)
        write_json(args.output, evidence)
        print(f"Phase44C probe evidence written: {args.output}")
        return 0
    except Phase44CError as exc:
        print(f"Phase44C probe failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
