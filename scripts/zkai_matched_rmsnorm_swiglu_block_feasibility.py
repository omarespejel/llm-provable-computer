#!/usr/bin/env python3
"""Feasibility probe for matched d64/d128 RMSNorm-SwiGLU block targets.

This is intentionally a gate, not a benchmark.  It compares the checked
statement-bound Stwo transformer-block surface against the minimum shape needed
for a public d=64 or d=128 RMSNorm-SwiGLU-residual block.  If the current proof
surface cannot honestly support that target, the output records an explicit
NO-GO with the exact blockers.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
CURRENT_EVIDENCE_PATH = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.json"
)
CURRENT_PROOF_PATH = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-stwo-statement-bound-transformer-block-2026-05"
    / "linear_block_v4_with_lookup.proof.json.gz"
)
CURRENT_STWO_SOURCE_PATH = ROOT / "src" / "stwo_backend" / "arithmetic_subset_prover.rs"

SCHEMA = "zkai-matched-rmsnorm-swiglu-block-feasibility-v1"
DECISION_GO = "GO_MATCHED_STWO_PROOF_SURFACE"
DECISION_NO_GO = "NO_GO_CURRENT_STWO_PROOF_SURFACE"
TARGET_WIDTHS = (64, 128)
FF_DIM_MULTIPLIER = 4
CURRENT_EXPECTED_MODEL_ID = "urn:zkai:ptvm:rmsnorm-gated-affine-residual-block-v1"
CURRENT_FIXTURE_PROOF_SYSTEM_VERSION = "stwo-phase10-linear-block-v4-with-lookup"
DEFAULT_SOURCE_DATE_EPOCH = 0
TSV_COLUMNS = (
    "target_width",
    "status",
    "reason",
    "current_d_model",
    "current_logical_width",
    "target_ff_dim",
    "target_estimated_linear_muls",
    "current_mul_memory_ops",
    "mul_gap_factor",
    "target_activation_rows",
    "target_norm_rows",
    "blocker_count",
)


class FeasibilityError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                value = json.load(handle)
        else:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
    except (OSError, json.JSONDecodeError, gzip.BadGzipFile) as err:
        raise FeasibilityError(f"failed to load JSON artifact {path}: {err}") from err
    if not isinstance(value, dict):
        raise FeasibilityError(f"JSON artifact {path} must be an object")
    return value


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FeasibilityError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise FeasibilityError(f"{label} must be a list")
    return value


def _instruction_op_ids(proof: dict[str, Any]) -> list[str]:
    program = _require_dict(_require_dict(proof.get("claim"), "claim").get("program"), "claim.program")
    instructions = _require_list(program.get("instructions"), "claim.program.instructions")
    op_ids: list[str] = []
    for index, instruction in enumerate(instructions):
        if isinstance(instruction, str):
            op_ids.append(instruction)
            continue
        if not isinstance(instruction, dict) or len(instruction) != 1:
            raise FeasibilityError(f"claim.program.instructions[{index}] must be a string or singleton object")
        op_ids.append(next(iter(instruction)))
    return op_ids


def _generated_at() -> str:
    source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH", str(DEFAULT_SOURCE_DATE_EPOCH))
    try:
        timestamp = int(source_date_epoch)
    except ValueError as err:
        raise FeasibilityError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise FeasibilityError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _git_commit() -> str:
    override = os.environ.get("ZKAI_GIT_COMMIT")
    if override:
        return override
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _statement_envelope_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    summary = _require_dict(evidence.get("summary"), "summary")
    statement_summary = _require_dict(summary.get("stwo-statement-envelope"), "summary.stwo-statement-envelope")
    if statement_summary.get("baseline_accepted") is not True:
        raise FeasibilityError("current statement-envelope baseline is not accepted")
    if statement_summary.get("all_mutations_rejected") is not True:
        raise FeasibilityError("current statement-envelope evidence does not reject every checked mutation")
    if statement_summary.get("mutations_checked") not in (None, statement_summary.get("mutation_count")):
        raise FeasibilityError("current statement-envelope mutation count aliases disagree")
    return statement_summary


def _current_block_profile(evidence: dict[str, Any]) -> dict[str, Any]:
    profile = _require_dict(evidence.get("block_profile"), "block_profile")
    artifact_metadata = _require_dict(evidence.get("artifact_metadata"), "artifact_metadata")
    metadata_profile = _require_dict(
        artifact_metadata.get("transformer_block_profile"),
        "artifact_metadata.transformer_block_profile",
    )
    if profile.get("logical_width") != metadata_profile.get("logical_width"):
        raise FeasibilityError("current block profile logical_width disagrees with artifact metadata")
    if profile.get("profile_version") != metadata_profile.get("profile_version"):
        raise FeasibilityError("current block profile version disagrees with artifact metadata")
    return profile


def _baseline_statement_model_id(evidence: dict[str, Any]) -> str:
    cases = _require_list(evidence.get("cases"), "cases")
    if not cases:
        raise FeasibilityError("cases must not be empty")
    model_ids: set[str] = set()
    for index, case in enumerate(cases):
        case_dict = _require_dict(case, f"cases[{index}]")
        statement = _require_dict(case_dict.get("baseline_statement"), f"cases[{index}].baseline_statement")
        model_id = statement.get("model_id")
        if model_id != CURRENT_EXPECTED_MODEL_ID:
            raise FeasibilityError(
                f"cases[{index}].baseline_statement.model_id must be "
                f"{CURRENT_EXPECTED_MODEL_ID!r}, got {model_id!r}"
            )
        model_ids.add(model_id)
    if model_ids != {CURRENT_EXPECTED_MODEL_ID}:
        raise FeasibilityError("baseline statement model IDs are inconsistent")
    return CURRENT_EXPECTED_MODEL_ID


def _fixture_gate_scan(source_path: pathlib.Path = CURRENT_STWO_SOURCE_PATH) -> dict[str, Any]:
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as err:
        raise FeasibilityError(f"failed to read Stwo source {source_path}: {err}") from err
    markers = {
        "linear_block_v4_with_lookup": "matches_linear_block_v4_with_lookup" in source,
        "decoding_step_v2_family": "matches_decoding_step_v2" in source,
        "broader_arithmetic_subset_internal": "broader arithmetic-subset AIR coverage remains internal" in source,
    }
    return {
        "source_path": str(source_path.relative_to(ROOT)),
        "source_sha256": sha256_file(source_path),
        "fixture_gate_detected": all(markers.values()),
        "markers": markers,
    }


def current_surface(
    evidence_path: pathlib.Path = CURRENT_EVIDENCE_PATH,
    proof_path: pathlib.Path = CURRENT_PROOF_PATH,
    source_path: pathlib.Path = CURRENT_STWO_SOURCE_PATH,
) -> dict[str, Any]:
    evidence = _load_json(evidence_path)
    proof = _load_json(proof_path)
    statement_summary = _statement_envelope_summary(evidence)
    block_profile = _current_block_profile(evidence)
    statement_model_id = _baseline_statement_model_id(evidence)
    claim = _require_dict(proof.get("claim"), "claim")
    transformer_config = _require_dict(claim.get("transformer_config"), "claim.transformer_config")
    final_state = _require_dict(claim.get("final_state"), "claim.final_state")
    memory = _require_list(final_state.get("memory"), "claim.final_state.memory")
    op_ids = _instruction_op_ids(proof)
    proof_payload = _require_list(proof.get("proof"), "proof")
    return {
        "evidence_path": str(evidence_path.relative_to(ROOT)),
        "evidence_sha256": sha256_file(evidence_path),
        "proof_path": str(proof_path.relative_to(ROOT)),
        "proof_sha256": sha256_file(proof_path),
        "proof_backend": proof.get("proof_backend"),
        "proof_backend_version": proof.get("proof_backend_version"),
        "statement_model_id": statement_model_id,
        "claim_semantic_scope": claim.get("semantic_scope"),
        "claim_steps": claim.get("steps"),
        "claim_transformer_config": transformer_config,
        "claim_memory_cells": len(memory),
        "claim_instruction_count": len(op_ids),
        "claim_mul_memory_ops": op_ids.count("MulMemory"),
        "claim_add_memory_ops": op_ids.count("AddMemory"),
        "proof_payload_bytes": len(proof_payload),
        "block_profile_version": block_profile.get("profile_version"),
        "block_logical_width": block_profile.get("logical_width"),
        "block_operation_ids": block_profile.get("operation_ids"),
        "statement_envelope_mutations_checked": statement_summary.get("mutation_count"),
        "statement_envelope_mutations_rejected": statement_summary.get("mutations_rejected"),
        "fixture_gate": _fixture_gate_scan(source_path),
    }


def matched_target(width: int) -> dict[str, Any]:
    if width <= 0:
        raise FeasibilityError("target width must be positive")
    ff_dim = width * FF_DIM_MULTIPLIER
    linear_muls = 3 * width * ff_dim
    return {
        "target_id": f"rmsnorm-swiglu-residual-d{width}-v1",
        "statement_kind": "transformer-block",
        "model_id": f"urn:zkai:ptvm:rmsnorm-swiglu-residual-d{width}-v1",
        "required_proof_backend_version": f"stwo-rmsnorm-swiglu-residual-d{width}-v1",
        "width": width,
        "ff_dim": ff_dim,
        "activation": "SwiGLU",
        "normalization": "RMSNorm",
        "residual": True,
        "estimated_linear_muls": linear_muls,
        "estimated_activation_rows": ff_dim,
        "estimated_norm_rows": 1,
        "required_statement_bindings": [
            "model_artifact_commitment",
            "model_config_commitment",
            "weight_commitment",
            "input_activation_commitment",
            "output_activation_commitment",
            "normalization_config_commitment",
            "activation_lookup_commitment",
            "public_instance_commitment",
            "proof_commitment",
            "verifying_key_commitment",
            "setup_commitment",
            "verifier_domain",
            "proof_system_version",
        ],
    }


def classify_target(current: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    current_config = _require_dict(current.get("claim_transformer_config"), "current.claim_transformer_config")
    current_d_model = current_config.get("d_model")
    current_width = current.get("block_logical_width")
    current_mul_ops = current.get("claim_mul_memory_ops")
    blockers: list[dict[str, Any]] = []

    if current_d_model != target["width"]:
        blockers.append(
            {
                "id": "proof_claim_d_model_mismatch",
                "current": current_d_model,
                "required": target["width"],
                "why_it_matters": "the checked proof public claim is not a d64/d128 transformer block claim",
            }
        )
    if current_width != target["width"]:
        blockers.append(
            {
                "id": "statement_profile_width_mismatch",
                "current": current_width,
                "required": target["width"],
                "why_it_matters": "the statement receipt binds a width-4 profile, not a matched public benchmark width",
            }
        )
    if current_mul_ops < target["estimated_linear_muls"]:
        blockers.append(
            {
                "id": "instruction_surface_too_small_for_swiglu",
                "current_mul_memory_ops": current_mul_ops,
                "estimated_required_linear_muls": target["estimated_linear_muls"],
                "why_it_matters": "a matched SwiGLU block needs gate, value, and down projections over d x ff_dim matrices",
            }
        )
    fixture_gate = _require_dict(current.get("fixture_gate"), "current.fixture_gate")
    proof_backend_version = current.get("proof_backend_version")
    allowed_backend_versions = {
        CURRENT_FIXTURE_PROOF_SYSTEM_VERSION,
        target["required_proof_backend_version"],
    }
    if proof_backend_version not in allowed_backend_versions:
        blockers.append(
            {
                "id": "proof_backend_version_mismatch",
                "current": proof_backend_version,
                "allowed": sorted(allowed_backend_versions),
                "why_it_matters": "the gate only classifies the checked fixture surface or the explicit matched target backend",
            }
        )
    if not fixture_gate.get("fixture_gate_detected") and proof_backend_version == CURRENT_FIXTURE_PROOF_SYSTEM_VERSION:
        blockers.append(
            {
                "id": "unsupported_source_probe",
                "why_it_matters": "the probe could not confirm the current fixture-gated Stwo proof surface",
            }
        )
    if fixture_gate.get("fixture_gate_detected"):
        blockers.append(
            {
                "id": "proof_generator_fixture_allowlist",
                "proof_backend_version": proof_backend_version,
                "pinned_fixture_version": CURRENT_FIXTURE_PROOF_SYSTEM_VERSION,
                "why_it_matters": "the current Stwo generator is scoped to shipped fixtures/decoding families, not arbitrary matched MLP programs",
            }
        )

    gap = float(target["estimated_linear_muls"]) / float(current_mul_ops or 1)
    status = "GO_FEASIBLE" if not blockers else "NO_GO_CURRENT_SURFACE"
    reason = (
        "current checked proof surface satisfies the matched RMSNorm-SwiGLU target shape"
        if status == "GO_FEASIBLE"
        else "current checked Stwo proof surface is a bounded statement-binding fixture, not a matched d64/d128 RMSNorm-SwiGLU proof"
    )
    return {
        "target_id": target["target_id"],
        "target_width": target["width"],
        "status": status,
        "reason": reason,
        "current_d_model": current_d_model,
        "current_logical_width": current_width,
        "current_mul_memory_ops": current_mul_ops,
        "target_ff_dim": target["ff_dim"],
        "target_estimated_linear_muls": target["estimated_linear_muls"],
        "mul_gap_factor": gap,
        "target_activation_rows": target["estimated_activation_rows"],
        "target_norm_rows": target["estimated_norm_rows"],
        "blockers": blockers,
    }


def decision_for_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        raise FeasibilityError("rows must not be empty")
    return DECISION_GO if all(row["status"] == "GO_FEASIBLE" for row in rows) else DECISION_NO_GO


def build_payload(
    *,
    evidence_path: pathlib.Path = CURRENT_EVIDENCE_PATH,
    proof_path: pathlib.Path = CURRENT_PROOF_PATH,
    source_path: pathlib.Path = CURRENT_STWO_SOURCE_PATH,
) -> dict[str, Any]:
    current = current_surface(evidence_path=evidence_path, proof_path=proof_path, source_path=source_path)
    targets = [matched_target(width) for width in TARGET_WIDTHS]
    rows = [classify_target(current, target) for target in targets]
    return {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "decision": decision_for_rows(rows),
        "research_issue": "https://github.com/omarespejel/provable-transformer-vm/issues/335",
        "current_surface": current,
        "targets": targets,
        "rows": rows,
        "summary": {
            "target_count": len(rows),
            "no_go_count": sum(1 for row in rows if row["status"].startswith("NO_GO")),
            "go_count": sum(1 for row in rows if row["status"] == "GO_FEASIBLE"),
            "first_required_backend_work": "parameterized Stwo AIR or export path for RMSNorm/SwiGLU/residual vector blocks",
            "current_result_is_still_useful_for": "statement-binding and agent-step composition discipline",
            "current_result_is_not": "a matched d64/d128 zkML benchmark",
        },
        "next_required_work": [
            {
                "id": "parameterized_vector_public_claim",
                "description": "Expose input/output activation, weight, normalization, activation-lookup, and config commitments as verifier-facing public statement material.",
            },
            {
                "id": "stwo_air_for_vector_mlp_block",
                "description": "Add or export a proof surface whose constraints actually cover RMSNorm, SwiGLU gate/value/down projections, and residual addition at d=64 before d=128.",
            },
            {
                "id": "same_statement_external_adapter",
                "description": "If using EZKL/ONNX or another proof stack for comparison, bind the same statement fields and run the same relabeling suite.",
            },
        ],
        "non_claims": [
            "This is not a d64 or d128 proof result.",
            "This is not a performance benchmark.",
            "This does not claim full transformer inference.",
            "This does not claim that the width-4 statement-bound block already proves matched RMSNorm-SwiGLU semantics.",
            "This does not claim Stwo is incapable of such a proof; it records that the current repo proof surface does not expose it.",
        ],
        "repro": {
            "git_commit": _git_commit(),
            "command": [
                "python3",
                "scripts/zkai_matched_rmsnorm_swiglu_block_feasibility.py",
                "--write-json",
                "docs/engineering/evidence/zkai-matched-rmsnorm-swiglu-block-feasibility-2026-05.json",
                "--write-tsv",
                "docs/engineering/evidence/zkai-matched-rmsnorm-swiglu-block-feasibility-2026-05.tsv",
            ],
        },
    }


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in _require_list(payload.get("rows"), "rows"):
        rows.append(
            {
                "target_width": row["target_width"],
                "status": row["status"],
                "reason": row["reason"],
                "current_d_model": row["current_d_model"],
                "current_logical_width": row["current_logical_width"],
                "target_ff_dim": row["target_ff_dim"],
                "target_estimated_linear_muls": row["target_estimated_linear_muls"],
                "current_mul_memory_ops": row["current_mul_memory_ops"],
                "mul_gap_factor": f"{row['mul_gap_factor']:.3f}",
                "target_activation_rows": row["target_activation_rows"],
                "target_norm_rows": row["target_norm_rows"],
                "blocker_count": len(row["blockers"]),
            }
        )
    return rows


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if tsv_path is not None:
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        with tsv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows_for_tsv(payload))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the JSON payload to stdout")
    parser.add_argument("--write-json", type=pathlib.Path, help="write the JSON payload")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write the TSV summary")
    args = parser.parse_args(argv)

    try:
        payload = build_payload()
        write_outputs(payload, args.write_json, args.write_tsv)
    except FeasibilityError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
