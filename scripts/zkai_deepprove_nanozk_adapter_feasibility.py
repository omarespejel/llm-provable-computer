#!/usr/bin/env python3
"""DeepProve-1 / NANOZK relabeling-adapter feasibility probe.

This is not a proof benchmark. It records whether public DeepProve-1 or NANOZK
artifacts currently satisfy the minimum bar for the zkAI statement-relabeling
benchmark used for EZKL, snarkjs, and native Stwo adapters.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-deepprove-nanozk-adapter-feasibility-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-deepprove-nanozk-adapter-feasibility-2026-05.tsv"

SCHEMA = "zkai-deepprove-nanozk-adapter-feasibility-v1"
SOURCE_DATE_EPOCH_DEFAULT = 0
DECISION = "NO_GO_PUBLIC_RELABELING_ADAPTER_BENCHMARK"

DEEPPROVE_COMMIT = "7d21c35e5e1cb006e413f4a9676333e9e1506a87"
NANOZK_ARXIV_SOURCE_SHA256 = "c505715f18d2bbb8dc01852a764b171984eb51f54a74d03790e29294e78ef2b4"

TSV_COLUMNS = (
    "system",
    "claim_scope",
    "adapter_gate",
    "public_verifier_available",
    "public_proof_artifact_available",
    "baseline_verification_reproducible",
    "relabeling_benchmark_run",
    "primary_blocker",
    "next_action",
)


class AdapterFeasibilityError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _generated_at() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(SOURCE_DATE_EPOCH_DEFAULT))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise AdapterFeasibilityError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise AdapterFeasibilityError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _git_commit() -> str:
    override = os.environ.get("ZKAI_EXTERNAL_FEASIBILITY_GIT_COMMIT")
    if override and override.strip():
        return override.strip().lower()
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


def adapter_bar() -> list[dict[str, str]]:
    return [
        {
            "criterion": "public_verifier",
            "description": "A runnable verifier command or API is publicly available for the claimed proof object.",
        },
        {
            "criterion": "public_baseline_artifact",
            "description": "A proof artifact plus verifier inputs are public enough to reproduce baseline acceptance.",
        },
        {
            "criterion": "statement_surface",
            "description": "The accepted object exposes model/input/output/config/setup/domain labels that can be mutated.",
        },
        {
            "criterion": "local_or_scripted_reproduction",
            "description": "The baseline verification and relabeling mutations can be reproduced from a checked command.",
        },
    ]


def candidate_systems() -> list[dict[str, Any]]:
    return [
        {
            "system": "DeepProve-1",
            "claim_scope": "reported full GPT-2 inference proof and transformer graph/layer support",
            "adapter_gate": "NO_GO_PUBLIC_GPT2_ARTIFACT_NOT_REPRODUCIBLE",
            "public_verifier_available": "PARTIAL_PUBLIC_REPO_API_NOT_MATCHED_TO_DEEPPROVE1_ARTIFACT",
            "public_proof_artifact_available": False,
            "baseline_verification_reproducible": False,
            "relabeling_benchmark_run": False,
            "primary_blocker": (
                "The public deep-prove repository exposes research code and MLP/CNN benchmark paths, "
                "but this probe did not find a public DeepProve-1 GPT-2 proof artifact plus verifier "
                "test vector matching the blog claim."
            ),
            "next_action": (
                "Revisit if Lagrange publishes a DeepProve-1 proof package with proof bytes, verifier "
                "inputs, model/input/output commitments, and a runnable verifier command."
            ),
            "sources": [
                {
                    "label": "DeepProve-1 blog",
                    "url": "https://lagrange.dev/blog/deepprove-1",
                    "used_for": "claim scope and transformer-feature context",
                },
                {
                    "label": "deep-prove public repository",
                    "url": "https://github.com/Lagrange-Labs/deep-prove",
                    "checked_commit": DEEPPROVE_COMMIT,
                    "used_for": "public artifact and verifier-surface inspection",
                },
            ],
            "source_inspection": {
                "clone_command": "git clone --depth 1 https://github.com/Lagrange-Labs/deep-prove.git",
                "checked_commit": DEEPPROVE_COMMIT,
                "public_repo_readme_scope": "MLP/CNN public benchmark path; zkml README says supported layers are dense, ReLU, maxpool, and convolution",
                "deep_prove_1_gpt2_artifacts_found": [],
                "nearby_llm_file": "zkml/assets/scripts/llms/gpt2_internal.py",
                "why_nearby_file_is_insufficient": (
                    "The script dumps GPT-2 internals, but it is not a public proof artifact, "
                    "verification key, or reproducible DeepProve-1 proof verifier input."
                ),
            },
        },
        {
            "system": "NANOZK",
            "claim_scope": "reported layerwise constant-size transformer proofs up to d=128",
            "adapter_gate": "NO_GO_NO_PUBLIC_VERIFIER_OR_PROOF_ARTIFACT",
            "public_verifier_available": False,
            "public_proof_artifact_available": False,
            "baseline_verification_reproducible": False,
            "relabeling_benchmark_run": False,
            "primary_blocker": (
                "The arXiv paper/source exposes the method, theorem framing, and reported numbers, "
                "but this probe did not find a public verifier implementation or proof artifact for "
                "baseline acceptance and relabeling mutations."
            ),
            "next_action": (
                "Revisit if a NANOZK repository, artifact bundle, or verifier command is published; "
                "until then use NANOZK only as source-backed field context."
            ),
            "sources": [
                {
                    "label": "NANOZK arXiv page",
                    "url": "https://arxiv.org/abs/2603.18046",
                    "used_for": "claim scope, reported d=128 proof size, and verification time",
                },
                {
                    "label": "NANOZK arXiv source",
                    "url": "https://arxiv.org/e-print/2603.18046",
                    "sha256": NANOZK_ARXIV_SOURCE_SHA256,
                    "used_for": "artifact-link inspection",
                },
            ],
            "source_inspection": {
                "download_command": "curl -fsSL https://arxiv.org/e-print/2603.18046 -o nanozk-src.tar",
                "source_sha256": NANOZK_ARXIV_SOURCE_SHA256,
                "source_files": [
                    "00README.json",
                    "fancyhdr.sty",
                    "iclr2026_conference.bst",
                    "iclr2026_conference.sty",
                    "main.bbl",
                    "main.tex",
                    "natbib.sty",
                    "references.bib",
                ],
                "direct_code_links_found": [
                    "https://github.com/zkonduit/ezkl",
                    "https://github.com/zcash/halo2",
                ],
                "why_direct_code_links_are_insufficient": (
                    "The source links dependency projects, not a NANOZK proof artifact, verifier command, "
                    "or benchmark reproduction package."
                ),
            },
        },
    ]


def build_probe() -> dict[str, Any]:
    systems = candidate_systems()
    payload = {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "git_commit": _git_commit(),
        "decision": DECISION,
        "question": (
            "Can DeepProve-1 or NANOZK be run through the same zkAI statement-relabeling "
            "benchmark used for EZKL, snarkjs, and native Stwo adapters?"
        ),
        "adapter_bar": adapter_bar(),
        "systems": systems,
        "systems_commitment": blake2b_commitment(systems, "ptvm:zkai:external-adapter-systems:v1"),
        "conclusion": {
            "benchmark_result": "NOT_RUN",
            "why": (
                "Both candidates are relevant field context, but neither currently exposes the public "
                "proof artifact plus verifier inputs required for a reproducible relabeling adapter."
            ),
            "paper_usage": "source_backed_context_only_not_empirical_adapter_row",
        },
        "non_claims": [
            "not a DeepProve-1 soundness finding",
            "not a NANOZK soundness finding",
            "not evidence that either system is insecure",
            "not evidence that either system lacks statement binding internally",
            "not a matched performance benchmark",
            "not a claim that future public artifacts will fail the relabeling benchmark",
        ],
    }
    validate_probe(payload)
    return payload


def validate_probe(payload: dict[str, Any]) -> None:
    expected_fields = {
        "schema",
        "generated_at",
        "git_commit",
        "decision",
        "question",
        "adapter_bar",
        "systems",
        "systems_commitment",
        "conclusion",
        "non_claims",
    }
    if set(payload) != expected_fields:
        raise AdapterFeasibilityError("payload field set mismatch")
    if payload["schema"] != SCHEMA:
        raise AdapterFeasibilityError("schema drift")
    if payload["decision"] != DECISION:
        raise AdapterFeasibilityError("decision drift")
    systems = payload["systems"]
    if payload["systems_commitment"] != blake2b_commitment(systems, "ptvm:zkai:external-adapter-systems:v1"):
        raise AdapterFeasibilityError("systems commitment mismatch")
    names = [system.get("system") for system in systems]
    if names != ["DeepProve-1", "NANOZK"]:
        raise AdapterFeasibilityError("candidate system drift")
    for system in systems:
        if system.get("public_proof_artifact_available") is not False:
            raise AdapterFeasibilityError("public proof artifact overclaim")
        if system.get("baseline_verification_reproducible") is not False:
            raise AdapterFeasibilityError("baseline verification overclaim")
        if system.get("relabeling_benchmark_run") is not False:
            raise AdapterFeasibilityError("benchmark-run overclaim")
        if not str(system.get("adapter_gate", "")).startswith("NO_GO"):
            raise AdapterFeasibilityError("adapter gate drift")
    conclusion = payload["conclusion"]
    if conclusion.get("benchmark_result") != "NOT_RUN":
        raise AdapterFeasibilityError("conclusion overclaim")
    required_non_claims = {
        "not a DeepProve-1 soundness finding",
        "not a NANOZK soundness finding",
        "not a matched performance benchmark",
    }
    if not required_non_claims.issubset(set(payload["non_claims"])):
        raise AdapterFeasibilityError("non-claim drift")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, str]]:
    def stable_scalar(value: Any) -> str:
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    rows: list[dict[str, str]] = []
    for system in payload["systems"]:
        rows.append(
            {
                "system": system["system"],
                "claim_scope": system["claim_scope"],
                "adapter_gate": system["adapter_gate"],
                "public_verifier_available": stable_scalar(system["public_verifier_available"]),
                "public_proof_artifact_available": stable_scalar(system["public_proof_artifact_available"]),
                "baseline_verification_reproducible": stable_scalar(system["baseline_verification_reproducible"]),
                "relabeling_benchmark_run": stable_scalar(system["relabeling_benchmark_run"]),
                "primary_blocker": system["primary_blocker"],
                "next_action": system["next_action"],
            }
        )
    return rows


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path, tsv_path: pathlib.Path) -> None:
    validate_probe(payload)
    try:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        with tsv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows_for_tsv(payload))
    except OSError as err:
        raise AdapterFeasibilityError(f"failed to write feasibility outputs: {err}") from err


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--write-json", type=pathlib.Path, default=None, help="write JSON evidence to this path")
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None, help="write TSV evidence to this path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_probe()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    json_path = args.write_json
    tsv_path = args.write_tsv
    if json_path is not None or tsv_path is not None:
        write_outputs(payload, json_path or JSON_OUT, tsv_path or TSV_OUT)


if __name__ == "__main__":
    main()
