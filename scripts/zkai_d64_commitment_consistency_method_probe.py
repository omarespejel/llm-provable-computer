#!/usr/bin/env python3
"""Commitment-consistency method probe for the canonical d64 zkAI target.

This is not a Stwo proof. It decides which commitment surface should be carried
into the next native AIR PR so private weight/table rows cannot drift away from
the public statement.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

FIXTURE_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_swiglu_statement_fixture.py"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-commitment-consistency-method-probe-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-commitment-consistency-method-probe-2026-05.tsv"

SCHEMA = "zkai-d64-commitment-consistency-method-probe-v1"
DECISION = "GO_DUAL_PUBLICATION_AND_PROOF_NATIVE_PARAMETER_COMMITMENT"
SOURCE_DATE_EPOCH_DEFAULT = 0
DIRTY_GIT_COMMIT = "dirty"
GIT_COMMIT_OVERRIDE_ENVS = (
    "ZKAI_D64_COMMITMENT_CONSISTENCY_PROBE_GIT_COMMIT",
    "ZKAI_D64_EXTERNAL_ADAPTER_PROBE_GIT_COMMIT",
)

EXPECTED_MATRIX_ROW_LEAVES = 576
EXPECTED_PARAMETER_SCALARS = 49_216
EXPECTED_ACTIVATION_TABLE_LEAVES = 2_049
EXPECTED_ACTIVATION_LOOKUP_ROWS = 256
EXPECTED_DISTINCT_ACTIVATION_LOOKUPS = 204

TSV_COLUMNS = (
    "method",
    "status",
    "same_statement_target",
    "proof_native_parameter_commitment",
    "matrix_row_leaves",
    "parameter_scalars",
    "activation_table_leaves",
    "activation_lookup_rows",
    "distinct_activation_lookup_rows",
    "required_statement_change",
    "statement_commitment",
)


class CommitmentConsistencyProbeError(ValueError):
    pass


def _load_fixture_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_d64_rmsnorm_swiglu_statement_fixture", FIXTURE_PATH)
    if spec is None or spec.loader is None:
        raise CommitmentConsistencyProbeError(f"failed to load d64 fixture from {FIXTURE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_fixture_module()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blake2b_hex(data: bytes, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(data)
    return digest.hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    return f"blake2b-256:{blake2b_hex(canonical_json_bytes(value), domain)}"


def _generated_at() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(SOURCE_DATE_EPOCH_DEFAULT))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise CommitmentConsistencyProbeError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise CommitmentConsistencyProbeError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _validate_generated_at(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CommitmentConsistencyProbeError("generated_at must be a UTC timestamp string")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as err:
        raise CommitmentConsistencyProbeError("generated_at must be a valid UTC timestamp string") from err
    if parsed.tzinfo != dt.timezone.utc:
        raise CommitmentConsistencyProbeError("generated_at must be a UTC timestamp string")


def _git_commit() -> str:
    for env_name in GIT_COMMIT_OVERRIDE_ENVS:
        override = os.environ.get(env_name)
        if override and override.strip():
            return override.strip().lower()
    try:
        if _dirty_worktree_paths():
            return DIRTY_GIT_COMMIT
    except CommitmentConsistencyProbeError:
        return "unavailable"
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def _repo_relative(path: pathlib.Path) -> pathlib.Path | None:
    try:
        return path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None


def _dirty_worktree_paths() -> set[pathlib.Path]:
    commands = (
        ["git", "-C", str(ROOT), "diff", "--name-only"],
        ["git", "-C", str(ROOT), "diff", "--cached", "--name-only"],
        ["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard"],
    )
    dirty: set[pathlib.Path] = set()
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as err:
            raise CommitmentConsistencyProbeError("failed to inspect git worktree cleanliness") from err
        dirty.update(pathlib.Path(line) for line in completed.stdout.splitlines() if line)
    return dirty


def _is_checked_output_path(path: pathlib.Path | None) -> bool:
    if path is None:
        return False
    return path.resolve() in {JSON_OUT.resolve(), TSV_OUT.resolve()}


def _guard_checked_output_write(json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    if not (_is_checked_output_path(json_path) or _is_checked_output_path(tsv_path)):
        return
    allowed_dirty = {
        path
        for path in (_repo_relative(JSON_OUT), _repo_relative(TSV_OUT))
        if path is not None
    }
    dirty = _dirty_worktree_paths()
    unexpected = sorted(str(path) for path in dirty - allowed_dirty)
    if unexpected:
        preview = ", ".join(unexpected[:8])
        suffix = "" if len(unexpected) <= 8 else f", ... ({len(unexpected)} total)"
        raise CommitmentConsistencyProbeError(
            "refuse to write checked commitment-consistency evidence from dirty worktree: "
            f"{preview}{suffix}"
        )


def merkle_leaf(payload: dict[str, Any], domain: str) -> str:
    return blake2b_hex(canonical_json_bytes(payload), domain)


def merkle_parent(left: str, right: str, domain: str) -> str:
    return blake2b_hex(bytes.fromhex(left) + bytes.fromhex(right), domain)


def merkle_root(leaves: list[str], domain: str) -> str:
    if not leaves:
        raise CommitmentConsistencyProbeError("cannot commit an empty Merkle tree")
    level = leaves
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = [*level, level[-1]]
        level = [merkle_parent(level[index], level[index + 1], domain) for index in range(0, len(level), 2)]
    return f"blake2b-256:{level[0]}"


def matrix_row_values(matrix: str, row: int) -> list[int]:
    if matrix in {"gate", "value"}:
        return [FIXTURE.weight_value(matrix, row, col) for col in range(FIXTURE.WIDTH)]
    if matrix == "down":
        return [FIXTURE.weight_value(matrix, row, col) for col in range(FIXTURE.FF_DIM)]
    raise CommitmentConsistencyProbeError(f"unknown matrix: {matrix}")


def matrix_row_leaf(matrix: str, row: int, values: list[int]) -> dict[str, Any]:
    return {
        "kind": "matrix_row",
        "matrix": matrix,
        "row": row,
        "shape": [len(values)],
        "values_sha256": sha256_bytes(canonical_json_bytes(values)),
    }


def matrix_tree(matrix: str, rows: int) -> dict[str, Any]:
    leaves = [matrix_row_leaf(matrix, row, matrix_row_values(matrix, row)) for row in range(rows)]
    leaf_hashes = [merkle_leaf(leaf, "ptvm:zkai:d64:param-matrix-row-leaf:v1") for leaf in leaves]
    return {
        "matrix": matrix,
        "rows": rows,
        "row_width": len(matrix_row_values(matrix, 0)),
        "leaf_count": len(leaves),
        "root": merkle_root(leaf_hashes, "ptvm:zkai:d64:param-matrix-row-tree:v1"),
        "leaf_hashes_sha256": sha256_bytes(canonical_json_bytes(leaf_hashes)),
    }


def rms_scale_tree(reference: dict[str, Any]) -> dict[str, Any]:
    leaves = [
        {
            "kind": "rms_scale",
            "index": index,
            "value_q8": value,
        }
        for index, value in enumerate(reference["rms_scale_q8"])
    ]
    leaf_hashes = [merkle_leaf(leaf, "ptvm:zkai:d64:rms-scale-leaf:v1") for leaf in leaves]
    return {
        "kind": "rms_scale",
        "leaf_count": len(leaves),
        "root": merkle_root(leaf_hashes, "ptvm:zkai:d64:rms-scale-tree:v1"),
        "leaf_hashes_sha256": sha256_bytes(canonical_json_bytes(leaf_hashes)),
    }


def activation_table_tree() -> dict[str, Any]:
    table = FIXTURE.activation_table()
    leaves = [
        {
            "kind": "activation_table_entry",
            "x_q8": index - FIXTURE.ACTIVATION_CLAMP_Q8,
            "y_q8": value,
        }
        for index, value in enumerate(table)
    ]
    leaf_hashes = [merkle_leaf(leaf, "ptvm:zkai:d64:activation-entry-leaf:v1") for leaf in leaves]
    return {
        "kind": "bounded_silu_table",
        "domain_q8": [-FIXTURE.ACTIVATION_CLAMP_Q8, FIXTURE.ACTIVATION_CLAMP_Q8],
        "leaf_count": len(leaves),
        "root": merkle_root(leaf_hashes, "ptvm:zkai:d64:activation-entry-tree:v1"),
        "leaf_hashes_sha256": sha256_bytes(canonical_json_bytes(leaf_hashes)),
    }


def proof_native_parameter_manifest(reference: dict[str, Any]) -> dict[str, Any]:
    matrix_trees = {
        "gate": matrix_tree("gate", FIXTURE.FF_DIM),
        "value": matrix_tree("value", FIXTURE.FF_DIM),
        "down": matrix_tree("down", FIXTURE.WIDTH),
    }
    rms_tree = rms_scale_tree(reference)
    activation_tree = activation_table_tree()
    manifest = {
        "scheme": "d64-proof-native-parameter-manifest-v1",
        "matrix_trees": matrix_trees,
        "rms_scale_tree": rms_tree,
        "activation_table_tree": activation_tree,
        "counts": {
            "matrix_row_leaves": sum(tree["leaf_count"] for tree in matrix_trees.values()),
            "parameter_scalars": 3 * FIXTURE.WIDTH * FIXTURE.FF_DIM + FIXTURE.WIDTH,
            "activation_table_leaves": activation_tree["leaf_count"],
        },
    }
    manifest["proof_native_parameter_commitment"] = blake2b_commitment(
        {
            "scheme": manifest["scheme"],
            "matrix_roots": {name: tree["root"] for name, tree in matrix_trees.items()},
            "rms_scale_root": rms_tree["root"],
            "activation_table_root": activation_tree["root"],
            "counts": manifest["counts"],
        },
        "ptvm:zkai:d64:proof-native-parameter-manifest:v1",
    )
    return manifest


def activation_usage(reference: dict[str, Any]) -> dict[str, Any]:
    clamped = [
        max(-FIXTURE.ACTIVATION_CLAMP_Q8, min(FIXTURE.ACTIVATION_CLAMP_Q8, value))
        for value in reference["gate_projection_q8"]
    ]
    indices = [value + FIXTURE.ACTIVATION_CLAMP_Q8 for value in clamped]
    if not indices:
        raise CommitmentConsistencyProbeError("activation usage requires at least one projection row")
    if min(indices) < 0 or max(indices) >= EXPECTED_ACTIVATION_TABLE_LEAVES:
        raise CommitmentConsistencyProbeError("activation lookup index escaped table domain")
    return {
        "activation_lookup_rows": len(indices),
        "distinct_activation_lookup_rows": len(set(indices)),
        "min_lookup_index": min(indices),
        "max_lookup_index": max(indices),
        "lookup_indices_sha256": sha256_bytes(canonical_json_bytes(indices)),
        "clamped_projection_count": sum(
            1
            for raw, bounded in zip(reference["gate_projection_q8"], clamped, strict=True)
            if raw != bounded
        ),
    }


def method_matrix() -> list[dict[str, Any]]:
    return [
        {
            "method": "metadata_only_statement_commitments",
            "status": "NO_GO",
            "same_statement_target": False,
            "reason": "Receipt metadata can relabel commitments without forcing private witness rows to match them.",
            "required_statement_change": "none_but_insufficient",
            "next_action": "Do not use this as the native d64 proof method.",
        },
        {
            "method": "publication_hash_inside_air",
            "status": "NO_GO_FOR_FIRST_PR",
            "same_statement_target": True,
            "reason": "It would bind the existing publication hashes directly, but proving Blake2b/SHA-style hashing inside the AIR is the wrong first implementation target.",
            "required_statement_change": "none",
            "next_action": "Keep publication hashes for audit/export identity; do not make them the first AIR consistency mechanism.",
        },
        {
            "method": "external_merkle_openings_only",
            "status": "NO_GO",
            "same_statement_target": False,
            "reason": "Opening rows outside the proof does not prove the Stwo witness used those rows.",
            "required_statement_change": "would_need_relation_level_binding",
            "next_action": "Use openings only if the proof relation consumes and checks the opened rows.",
        },
        {
            "method": "public_parameter_columns",
            "status": "POSSIBLE_BUT_EXPENSIVE",
            "same_statement_target": True,
            "reason": "Making all parameters verifier-visible binds the relation, but exposes 49,216 q8 scalars and is not the best private-model path.",
            "required_statement_change": "public_parameter_payload_or_commitment_policy",
            "next_action": "Keep as a debugging fallback for the first exact proof if proof-native private commitments take too long.",
        },
        {
            "method": "dual_publication_and_proof_native_parameter_commitment",
            "status": "GO_FOR_NEXT_PR",
            "same_statement_target": True,
            "reason": "Carry the existing publication hashes and add a proof-native parameter commitment that the AIR/receipt can bind.",
            "required_statement_change": "add_proof_native_parameter_commitment_to_d64_statement",
            "next_action": "Update the d64 statement fixture with this field, then make the native proof public instance bind it.",
        },
    ]


def expected_non_claims() -> list[str]:
    return [
        "not a Stwo proof",
        "not a proof-size or timing benchmark",
        "not a claim that publication hashes are verified inside the AIR",
        "not a claim that Merkle openings alone bind private witness rows",
        "not full transformer inference",
    ]


def build_probe() -> dict[str, Any]:
    fixture = FIXTURE.build_fixture()
    FIXTURE.validate_payload(fixture)
    reference = FIXTURE.evaluate_reference_block()
    manifest = proof_native_parameter_manifest(reference)
    usage = activation_usage(reference)
    methods = method_matrix()
    return {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "git_commit": _git_commit(),
        "decision": DECISION,
        "source_fixture": {
            "schema": fixture["schema"],
            "target_id": fixture["target"]["target_id"],
            "proof_status": fixture["implementation_status"]["proof_status"],
            "statement_commitment": fixture["statement"]["statement_commitment"],
            "weight_commitment": fixture["statement"]["weight_commitment"],
            "activation_lookup_commitment": fixture["statement"]["activation_lookup_commitment"],
        },
        "proof_native_parameter_manifest": manifest,
        "proof_native_parameter_manifest_commitment": blake2b_commitment(
            manifest,
            "ptvm:zkai:d64:proof-native-parameter-manifest-payload:v1",
        ),
        "activation_usage": usage,
        "method_matrix": methods,
        "method_matrix_commitment": blake2b_commitment(methods, "ptvm:zkai:d64:commitment-method-matrix:v1"),
        "next_pr_target": {
            "issue": 346,
            "action": "add proof_native_parameter_commitment to the d64 statement fixture and bind it in the native proof public instance",
            "chosen_method": "dual_publication_and_proof_native_parameter_commitment",
        },
        "non_claims": expected_non_claims(),
    }


def validate_probe(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise CommitmentConsistencyProbeError("payload must be an object")
    expected_fields = {
        "schema",
        "generated_at",
        "git_commit",
        "decision",
        "source_fixture",
        "proof_native_parameter_manifest",
        "proof_native_parameter_manifest_commitment",
        "activation_usage",
        "method_matrix",
        "method_matrix_commitment",
        "next_pr_target",
        "non_claims",
    }
    if set(payload) != expected_fields:
        raise CommitmentConsistencyProbeError("payload field set mismatch")
    if payload["schema"] != SCHEMA:
        raise CommitmentConsistencyProbeError("schema mismatch")
    _validate_generated_at(payload["generated_at"])
    git_commit = payload["git_commit"]
    if not isinstance(git_commit, str) or not git_commit:
        raise CommitmentConsistencyProbeError("git_commit must be a non-empty string")
    if git_commit not in {"unavailable", DIRTY_GIT_COMMIT} and (
        len(git_commit) != 40 or any(char not in "0123456789abcdef" for char in git_commit)
    ):
        raise CommitmentConsistencyProbeError("git_commit must be a full lowercase hex commit hash")
    if payload["decision"] != DECISION:
        raise CommitmentConsistencyProbeError("decision drift")

    fixture = FIXTURE.build_fixture()
    expected_source = {
        "schema": fixture["schema"],
        "target_id": fixture["target"]["target_id"],
        "proof_status": fixture["implementation_status"]["proof_status"],
        "statement_commitment": fixture["statement"]["statement_commitment"],
        "weight_commitment": fixture["statement"]["weight_commitment"],
        "activation_lookup_commitment": fixture["statement"]["activation_lookup_commitment"],
    }
    if payload["source_fixture"] != expected_source:
        raise CommitmentConsistencyProbeError("source fixture drift")

    expected_manifest = proof_native_parameter_manifest(FIXTURE.evaluate_reference_block())
    counts = expected_manifest["counts"]
    if counts["matrix_row_leaves"] != EXPECTED_MATRIX_ROW_LEAVES:
        raise CommitmentConsistencyProbeError("matrix row leaf count drift")
    if counts["parameter_scalars"] != EXPECTED_PARAMETER_SCALARS:
        raise CommitmentConsistencyProbeError("parameter scalar count drift")
    if counts["activation_table_leaves"] != EXPECTED_ACTIVATION_TABLE_LEAVES:
        raise CommitmentConsistencyProbeError("activation table leaf count drift")
    if payload["proof_native_parameter_manifest"] != expected_manifest:
        raise CommitmentConsistencyProbeError("proof-native parameter manifest drift")
    if payload["proof_native_parameter_manifest_commitment"] != blake2b_commitment(
        expected_manifest,
        "ptvm:zkai:d64:proof-native-parameter-manifest-payload:v1",
    ):
        raise CommitmentConsistencyProbeError("proof-native parameter manifest commitment drift")

    expected_usage = activation_usage(FIXTURE.evaluate_reference_block())
    if expected_usage["activation_lookup_rows"] != EXPECTED_ACTIVATION_LOOKUP_ROWS:
        raise CommitmentConsistencyProbeError("activation lookup row count drift")
    if expected_usage["distinct_activation_lookup_rows"] != EXPECTED_DISTINCT_ACTIVATION_LOOKUPS:
        raise CommitmentConsistencyProbeError("distinct activation lookup count drift")
    if payload["activation_usage"] != expected_usage:
        raise CommitmentConsistencyProbeError("activation usage drift")

    expected_methods = method_matrix()
    if payload["method_matrix"] != expected_methods:
        raise CommitmentConsistencyProbeError("method matrix drift")
    if payload["method_matrix_commitment"] != blake2b_commitment(
        expected_methods,
        "ptvm:zkai:d64:commitment-method-matrix:v1",
    ):
        raise CommitmentConsistencyProbeError("method matrix commitment drift")
    by_method = {row["method"]: row for row in payload["method_matrix"]}
    if by_method["metadata_only_statement_commitments"]["status"] != "NO_GO":
        raise CommitmentConsistencyProbeError("metadata-only method must stay NO_GO")
    if by_method["external_merkle_openings_only"]["status"] != "NO_GO":
        raise CommitmentConsistencyProbeError("external opening-only method must stay NO_GO")
    if by_method["dual_publication_and_proof_native_parameter_commitment"]["status"] != "GO_FOR_NEXT_PR":
        raise CommitmentConsistencyProbeError("dual commitment method must stay selected")
    expected_next = {
        "issue": 346,
        "action": "add proof_native_parameter_commitment to the d64 statement fixture and bind it in the native proof public instance",
        "chosen_method": "dual_publication_and_proof_native_parameter_commitment",
    }
    if payload["next_pr_target"] != expected_next:
        raise CommitmentConsistencyProbeError("next PR target drift")
    if payload["non_claims"] != expected_non_claims():
        raise CommitmentConsistencyProbeError("non-claims drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_probe(payload)
    manifest = payload["proof_native_parameter_manifest"]
    counts = manifest["counts"]
    usage = payload["activation_usage"]
    return [
        {
            "method": row["method"],
            "status": row["status"],
            "same_statement_target": str(row["same_statement_target"]).lower(),
            "proof_native_parameter_commitment": manifest["proof_native_parameter_commitment"],
            "matrix_row_leaves": counts["matrix_row_leaves"],
            "parameter_scalars": counts["parameter_scalars"],
            "activation_table_leaves": counts["activation_table_leaves"],
            "activation_lookup_rows": usage["activation_lookup_rows"],
            "distinct_activation_lookup_rows": usage["distinct_activation_lookup_rows"],
            "required_statement_change": row["required_statement_change"],
            "statement_commitment": payload["source_fixture"]["statement_commitment"],
        }
        for row in payload["method_matrix"]
    ]


def _reserve_temp_path(parent: pathlib.Path, name: str) -> pathlib.Path:
    with tempfile.NamedTemporaryFile(dir=parent, prefix=f".{name}.", suffix=".tmp", delete=False) as handle:
        return pathlib.Path(handle.name)


def _atomic_write_pair(files: list[tuple[pathlib.Path, str]]) -> None:
    staged: list[tuple[pathlib.Path, pathlib.Path]] = []
    backups: list[tuple[pathlib.Path, pathlib.Path, bool]] = []
    try:
        for final_path, content in files:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=final_path.parent,
                prefix=f".{final_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                tmp_path = pathlib.Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((tmp_path, final_path))
        for tmp_path, final_path in staged:
            backup_path = _reserve_temp_path(final_path.parent, f"{final_path.name}.backup")
            backup_path.unlink(missing_ok=True)
            existed = final_path.exists()
            if existed:
                final_path.replace(backup_path)
            backups.append((final_path, backup_path, existed))
            tmp_path.replace(final_path)
    except OSError as err:
        for final_path, backup_path, existed in reversed(backups):
            try:
                final_path.unlink(missing_ok=True)
                if existed:
                    backup_path.replace(final_path)
            except OSError:
                pass
        for tmp_path, _ in staged:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        for _, backup_path, _ in backups:
            try:
                backup_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise CommitmentConsistencyProbeError(f"failed to write commitment consistency probe output: {err}") from err
    for _, backup_path, _ in backups:
        try:
            backup_path.unlink(missing_ok=True)
        except OSError:
            pass


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_probe(payload)
    if payload["git_commit"] == DIRTY_GIT_COMMIT:
        raise CommitmentConsistencyProbeError("refuse to write commitment-consistency evidence from dirty worktree")
    rows = rows_for_tsv(payload, validated=True)
    _guard_checked_output_write(json_path, tsv_path)
    files: list[tuple[pathlib.Path, str]] = []
    if json_path is not None:
        files.append((json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"))
    if tsv_path is not None:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        files.append((tsv_path, buffer.getvalue()))
    _atomic_write_pair(files)


def tampered_manifest(matrix: str = "gate") -> dict[str, Any]:
    reference = FIXTURE.evaluate_reference_block()
    out = proof_native_parameter_manifest(reference)
    tree = copy.deepcopy(out["matrix_trees"][matrix])
    tree["root"] = "blake2b-256:" + "00" * 32
    out["matrix_trees"][matrix] = tree
    out["proof_native_parameter_commitment"] = blake2b_commitment(
        {
            "scheme": out["scheme"],
            "matrix_roots": {name: item["root"] for name, item in out["matrix_trees"].items()},
            "rms_scale_root": out["rms_scale_tree"]["root"],
            "activation_table_root": out["activation_table_tree"]["root"],
            "counts": out["counts"],
        },
        "ptvm:zkai:d64:proof-native-parameter-manifest:v1",
    )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true", help="print the full probe payload")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_probe()
    validate_probe(payload)
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        manifest = payload["proof_native_parameter_manifest"]
        usage = payload["activation_usage"]
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "decision": payload["decision"],
                    "chosen_method": payload["next_pr_target"]["chosen_method"],
                    "matrix_row_leaves": manifest["counts"]["matrix_row_leaves"],
                    "parameter_scalars": manifest["counts"]["parameter_scalars"],
                    "activation_table_leaves": manifest["counts"]["activation_table_leaves"],
                    "distinct_activation_lookup_rows": usage["distinct_activation_lookup_rows"],
                    "proof_native_parameter_commitment": manifest["proof_native_parameter_commitment"],
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
