#!/usr/bin/env python3
"""Paper claim-pack validator for the Stwo attention/Softmax-table evidence.

This gate is intentionally small. It checks that the machine-readable paper
claim pack stays narrow, that every referenced checked evidence path exists,
and that positive claim fields do not drift into public-benchmark, exact
Softmax, full-inference, or production-ready language.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys
import tempfile
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
JSON_OUT = ROOT / "docs/paper/evidence/stark-native-transformer-claim-pack-2026-05.json"
ALLOWED_OUTPUT_DIR = ROOT / "docs" / "paper" / "evidence"
ALLOWED_OUTPUT_PREFIX = pathlib.PurePosixPath("docs/paper/evidence")

SCHEMA = "stark-native-transformer-paper-claim-pack-v1"
DECISION = "GO_PAPER_CLAIM_PACK_NO_GO_PUBLIC_OR_PRODUCTION_CLAIMS"
THESIS_ID = "stark_native_attention_arithmetic_softmax_table_fusion"
CLAIM_BOUNDARY = (
    "STARK_NATIVE_PROOF_ARCHITECTURE_CLAIM_FOR_BOUNDED_INTEGER_ATTENTION_AND_SOFTMAX_TABLE_"
    "LOOKUP_MEMBERSHIP_NOT_EXACT_SOFTMAX_NOT_FULL_INFERENCE_NOT_PUBLIC_BENCHMARK_NOT_PRODUCTION_READY"
)

FORBIDDEN_POSITIVE_CLAIM_PATTERNS = {
    "full inference": re.compile(r"\bfull\s+(?:transformer\s+)?inference\b", re.IGNORECASE),
    "exact softmax": re.compile(r"\bexact\s+(?:real-valued\s+)?softmax\b", re.IGNORECASE),
    "public benchmark": re.compile(r"\bpublic\s+benchmark\b", re.IGNORECASE),
    "production-ready": re.compile(r"\bproduction[-\s]?ready\b", re.IGNORECASE),
    "starknet deployed": re.compile(r"\bstarknet\s+(?:mainnet\s+)?deployed\b", re.IGNORECASE),
}

POSITIVE_TEXT_FIELDS = (
    "thesis",
    "paper_claims",
    "go_posture",
    "go_criteria_satisfied",
)

NON_CLAIMS = [
    "not exact real-valued Softmax",
    "not full inference",
    "not public benchmark",
    "not production-ready",
    "not Starknet deployed",
    "not a stable upstream Stwo proof wire format",
    "not recursion or PCD",
    "not model accuracy, perplexity, tokenizer, weight-import, or runtime evidence",
]

BLOCKERS = [
    "stable verifier-facing binary proof serialization is not exposed upstream by Stwo in this repo surface",
    "backend-internal source-arithmetic versus lookup-column byte attribution is still a NO-GO",
    "local median-of-5 verifier timing does not support a fused verifier-time win claim",
    "model-faithful quantized attention is bridged only for the checked d8 fixture trace",
    "production Starknet verifier packaging, calldata/accounting, and deployment gates are not complete",
    "no full transformer runtime, tokenizer/model-weight import, or accuracy/perplexity gate is bound",
]

NO_GO_POSTURE = [
    "NO-GO for public performance or production deployment language.",
    "NO-GO for runtime, accuracy, recursion, PCD, or Starknet deployment claims.",
    "NO-GO for verifier-time improvement claims from the current timing run.",
]

EVIDENCE_REFS = [
    {
        "id": "route_matrix",
        "path": "docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json",
        "supports": "eleven checked source-sidecar-fused route rows with matched proof-byte ratios",
    },
    {
        "id": "controlled_component_grid",
        "path": "docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json",
        "supports": "ten checked fine-grained typed-component rows with positive fused savings",
    },
    {
        "id": "section_delta",
        "path": "docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json",
        "supports": "opening/decommitment dominated JSON section-delta savings",
    },
    {
        "id": "typed_size_estimate",
        "path": "docs/engineering/evidence/zkai-attention-kv-stwo-typed-size-estimate-2026-05.json",
        "supports": "Stwo typed size-estimate savings without claiming stable binary serialization",
    },
    {
        "id": "binary_typed_accounting",
        "path": "docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json",
        "supports": "repo-owned local binary typed accounting over d32 matched envelopes",
    },
    {
        "id": "median_timing",
        "path": "docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.json",
        "supports": "engineering-only median-of-5 verifier timing discipline and timing non-claim",
    },
    {
        "id": "seq32_fused",
        "path": "docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.json",
        "supports": "two-head d8 seq32 fused proof existence and matched source-sidecar comparison",
    },
    {
        "id": "model_faithful_bridge",
        "path": "docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.json",
        "supports": "checked equivalence between model-facing integer attention policy and the d8 fixture trace",
    },
]

EXPECTED_KEYS = {
    "schema",
    "decision",
    "thesis_id",
    "claim_boundary",
    "thesis",
    "paper_claims",
    "evidence_refs",
    "go_posture",
    "go_criteria_satisfied",
    "no_go_posture",
    "non_claims",
    "blockers",
    "validation_commands",
    "mutation_cases",
    "payload_commitment",
}

EXPECTED_MUTATION_NAMES = (
    "positive_full_inference_overclaim",
    "positive_exact_softmax_overclaim",
    "positive_public_benchmark_overclaim",
    "positive_production_ready_overclaim",
    "evidence_path_missing",
    "non_claim_removed",
    "blocker_removed",
    "no_go_posture_removed",
    "unknown_field_injection",
)


class ClaimPackGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten_strings(item)


def _assert_no_positive_overclaims(payload: dict[str, Any]) -> None:
    for field in POSITIVE_TEXT_FIELDS:
        for text in _flatten_strings(payload.get(field)):
            for label, pattern in FORBIDDEN_POSITIVE_CLAIM_PATTERNS.items():
                if pattern.search(text):
                    raise ClaimPackGateError(f"positive claim overclaim: {label} in {field}")


def _repo_relative_path(value: str | pathlib.Path, label: str) -> pathlib.PurePosixPath:
    raw_path = str(value).replace("\\", "/")
    if re.match(r"^[A-Za-z]:", raw_path):
        raise ClaimPackGateError(f"{label} must be repo-relative")
    path = pathlib.PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts:
        raise ClaimPackGateError(f"{label} must be repo-relative")
    return path


def _full_repo_path(relative_path: pathlib.PurePosixPath) -> pathlib.Path:
    return ROOT.joinpath(*relative_path.parts)


def _assert_repo_contained(full_path: pathlib.Path, label: str) -> None:
    try:
        full_path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (FileNotFoundError, ValueError) as err:
        raise ClaimPackGateError(f"{label} must stay within repo") from err


def _assert_no_repo_symlink_components(full_path: pathlib.Path, label: str) -> None:
    try:
        relative_parts = full_path.relative_to(ROOT).parts
    except ValueError as err:
        raise ClaimPackGateError(f"{label} must stay within repo") from err
    current = ROOT
    for part in relative_parts:
        current = current / part
        if current.is_symlink():
            raise ClaimPackGateError(f"{label} must not include symlink components")


def _assert_evidence_paths_exist(payload: dict[str, Any]) -> None:
    refs = payload.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ClaimPackGateError("evidence_refs must be a non-empty list")
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            raise ClaimPackGateError(f"evidence_refs[{index}] must be an object")
        path = ref.get("path")
        if not isinstance(path, str):
            raise ClaimPackGateError(f"evidence_refs[{index}].path must be repo-relative")
        full_path = _full_repo_path(_repo_relative_path(path, f"evidence_refs[{index}].path"))
        _assert_no_repo_symlink_components(full_path, f"evidence_refs[{index}].path")
        if not full_path.is_file():
            raise ClaimPackGateError(f"missing evidence path: {path}")
        _assert_repo_contained(full_path, f"evidence_refs[{index}].path")


def _assert_exact_list(value: Any, expected: list[str], label: str) -> None:
    if value != expected:
        raise ClaimPackGateError(f"{label} drift")


def validate_payload(payload: dict[str, Any]) -> None:
    if set(payload) != EXPECTED_KEYS:
        raise ClaimPackGateError("unknown or missing claim-pack field")
    if payload["schema"] != SCHEMA:
        raise ClaimPackGateError("schema drift")
    if payload["decision"] != DECISION:
        raise ClaimPackGateError("decision drift")
    if payload["thesis_id"] != THESIS_ID:
        raise ClaimPackGateError("thesis id drift")
    if payload["claim_boundary"] != CLAIM_BOUNDARY:
        raise ClaimPackGateError("claim boundary drift")
    _assert_no_positive_overclaims(payload)
    _assert_exact_list(payload["no_go_posture"], NO_GO_POSTURE, "no_go_posture")
    _assert_exact_list(payload["non_claims"], NON_CLAIMS, "non_claims")
    _assert_exact_list(payload["blockers"], BLOCKERS, "blockers")
    _assert_evidence_paths_exist(payload)
    mutation_cases = payload.get("mutation_cases")
    if not isinstance(mutation_cases, list) or len(mutation_cases) != len(EXPECTED_MUTATION_NAMES):
        raise ClaimPackGateError("mutation case count drift")
    for index, (case, expected_name) in enumerate(zip(mutation_cases, EXPECTED_MUTATION_NAMES, strict=True)):
        if case != {"name": expected_name, "rejected": True}:
            raise ClaimPackGateError(f"mutation case drift at {index}")
    if payload["payload_commitment"] != payload_commitment(payload):
        raise ClaimPackGateError("payload commitment drift")


def build_payload() -> dict[str, Any]:
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "thesis_id": THESIS_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "thesis": (
            "Checked Stwo evidence supports a paper-facing architecture claim: bounded integer attention "
            "arithmetic and Softmax-table LogUp membership can be fused into one native STARK proof object, "
            "sharing proof-system commitment and opening plumbing across the arithmetic and lookup-heavy parts."
        ),
        "paper_claims": [
            (
                "One checked proof object can bind attention arithmetic and statement-bound Softmax-table "
                "membership for the same bounded fixture family."
            ),
            (
                "Matched source-plus-sidecar controls show proof-object byte savings across checked width, "
                "head-count, sequence-length, and combined-axis profiles."
            ),
            (
                "Section-delta and typed-component evidence both point to shared opening and decommitment "
                "structure as the dominant source of savings."
            ),
            (
                "A model-facing quantized attention policy is checked equivalent to the existing d8 bounded "
                "Softmax-table fixture trace at the trace boundary."
            ),
        ],
        "evidence_refs": list(EVIDENCE_REFS),
        "go_posture": [
            "GO to present a bounded STARK-native proof-architecture claim in the paper evidence pack.",
            "GO to cite proof-existence, matched proof-byte accounting, typed-size accounting, and claim-boundary discipline.",
        ],
        "go_criteria_satisfied": [
            "checked source, sidecar, and fused proof evidence exists for the cited profiles",
            "machine-readable gates reject overclaim and evidence-drift mutations",
            "timing evidence is separated from proof-size evidence",
            "model-facing quantized policy is bridge-checked before runtime integration",
        ],
        "no_go_posture": list(NO_GO_POSTURE),
        "non_claims": list(NON_CLAIMS),
        "blockers": list(BLOCKERS),
        "validation_commands": [
            "just gate-fast",
            "python3 scripts/zkai_paper_claim_pack_gate.py --write-json docs/paper/evidence/stark-native-transformer-claim-pack-2026-05.json",
            "python3 -m unittest scripts.tests.test_zkai_paper_claim_pack_gate",
            "git diff --check",
            "just gate",
        ],
        "mutation_cases": [{"name": name, "rejected": True} for name in EXPECTED_MUTATION_NAMES],
    }
    payload["payload_commitment"] = payload_commitment(payload)
    return payload


def mutation_cases(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    cases: list[tuple[str, dict[str, Any]]] = []

    mutated = copy.deepcopy(payload)
    mutated["paper_claims"][0] = "This proves full inference."
    cases.append(("positive_full_inference_overclaim", mutated))

    mutated = copy.deepcopy(payload)
    mutated["paper_claims"][0] = "This proves exact Softmax."
    cases.append(("positive_exact_softmax_overclaim", mutated))

    mutated = copy.deepcopy(payload)
    mutated["go_posture"][0] = "GO for public benchmark publication."
    cases.append(("positive_public_benchmark_overclaim", mutated))

    mutated = copy.deepcopy(payload)
    mutated["paper_claims"][0] = "This is production-ready."
    cases.append(("positive_production_ready_overclaim", mutated))

    mutated = copy.deepcopy(payload)
    mutated["evidence_refs"][0]["path"] = "docs/engineering/evidence/missing-claim-pack-evidence.json"
    cases.append(("evidence_path_missing", mutated))

    mutated = copy.deepcopy(payload)
    mutated["non_claims"] = mutated["non_claims"][1:]
    cases.append(("non_claim_removed", mutated))

    mutated = copy.deepcopy(payload)
    mutated["blockers"] = mutated["blockers"][1:]
    cases.append(("blocker_removed", mutated))

    mutated = copy.deepcopy(payload)
    mutated["no_go_posture"] = mutated["no_go_posture"][1:]
    cases.append(("no_go_posture_removed", mutated))

    mutated = copy.deepcopy(payload)
    mutated["unexpected"] = "claim smuggling"
    cases.append(("unknown_field_injection", mutated))

    return cases


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    validate_payload(payload)
    relative_path = _repo_relative_path(path, "output path")
    if relative_path.parts[: len(ALLOWED_OUTPUT_PREFIX.parts)] != ALLOWED_OUTPUT_PREFIX.parts:
        raise ClaimPackGateError("output path must stay under docs/paper/evidence")
    path = _full_repo_path(relative_path)
    if path.is_symlink():
        raise ClaimPackGateError("output path must not be a symlink")
    _assert_no_repo_symlink_components(path.parent, "output parent hierarchy")
    path.parent.mkdir(parents=True, exist_ok=True)
    _assert_no_repo_symlink_components(path.parent, "output parent hierarchy")
    try:
        path.parent.resolve(strict=True).relative_to(ALLOWED_OUTPUT_DIR.resolve(strict=True))
    except ValueError as err:
        raise ClaimPackGateError("output path must stay under docs/paper/evidence") from err
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = pathlib.Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if path.is_symlink():
        tmp_path.unlink(missing_ok=True)
        raise ClaimPackGateError("output path must not be a symlink")
    tmp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    payload = build_payload()
    validate_payload(payload)
    for expected_name, mutated in mutation_cases(payload):
        try:
            validate_payload(mutated)
        except ClaimPackGateError:
            continue
        raise ClaimPackGateError(f"mutation did not reject: {expected_name}")

    if args.write_json:
        write_json(args.write_json, payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
