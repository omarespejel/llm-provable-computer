#!/usr/bin/env python3
"""Preflight the variant-invariant compact-adapter reprove route."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import pathlib
import secrets
import stat
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_PATH = ROOT / "src" / "stwo_backend" / "native_attention_mlp_single_proof.rs"
TRANSCRIPT_STABLE_PATH = (
    EVIDENCE_DIR / "zkai-native-attention-mlp-transcript-stable-comparison-2026-05.json"
)
JSON_OUT = (
    EVIDENCE_DIR
    / "zkai-native-attention-mlp-variant-invariant-reprove-preflight-2026-05.json"
)
TSV_OUT = (
    EVIDENCE_DIR
    / "zkai-native-attention-mlp-variant-invariant-reprove-preflight-2026-05.tsv"
)

SCHEMA = "zkai-native-attention-mlp-variant-invariant-reprove-preflight-gate-v1"
DECISION = "NO_GO_SOURCE_BACKED_VARIANT_INVARIANT_REPROVE_NOT_AVAILABLE"
RESULT = "NARROW_CLAIM_COMPACT_ADAPTER_REPROVE_REQUIRES_SOURCE_SELECTOR"
ISSUE = "https://github.com/omarespejel/provable-transformer-vm/issues/636"
PAYLOAD_DOMAIN = "ptvm:zkai:native-attention-mlp-variant-invariant-reprove-preflight:v1"
CLAIM_BOUNDARY = (
    "SOURCE_PREFLIGHT_FOR_VARIANT_INVARIANT_OR_MULTI_TRANSCRIPT_COMPACT_ADAPTER_REPROVE_"
    "WITHOUT_PROMOTING_A_COMPACT_FRONTIER"
)

EXPECTED_SOURCE_SHA256 = "c131506de19e489ec4e3ba3273801db9e01d668439212f906b2d866a6e50c908"
EXPECTED_TRANSCRIPT_STABLE_SHA256 = "0b129942254aa1800386de167ed741ab717658772e8a158bdea53de6e9db6de8"
EXPECTED_TRANSCRIPT_STABLE_PAYLOAD_SHA256 = (
    "6d6e74837bf6c28afafd692de2494a96d2a91d7623ae790cd865d02b08aa503c"
)

CURRENT_FRONTIER_TYPED_BYTES = 41_932
DUPLICATE_LABEL_CONTROL_TYPED_BYTES = 43_228
COMPACT_LABEL_CONTROL_TYPED_BYTES = 42_492
LABEL_CONTROL_SAVING_BYTES = 736
DIRECT_OPENING_VALUE_SAVING_BYTES = 112
TRANSCRIPT_PATH_SENSITIVE_SAVING_BYTES = 624
NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900

MAX_JSON_BYTES = 16 * 1024 * 1024
SOURCE_SNIPPETS = {
    "preprocessed_adapter_trace": "attention_preprocessed.extend(adapter_trace(input)?);",
    "base_adapter_trace": "attention_base.extend(adapter_trace(input)?);",
    "duplicate_comment": "The adapter is intentionally present in both traces",
    "trace_cell_constant": "const ADAPTER_TRACE_CELLS: usize = ADAPTER_WIDTH * ADAPTER_TRACE_COLUMNS;",
    "trace_cell_validation": "input.adapter_trace_cells,\n        ADAPTER_TRACE_CELLS,",
}
ABSENT_SOURCE_TOKENS = (
    "adapter_variant",
    "compact_adapter",
    "variant_invariant",
    "multi_transcript",
)

NON_CLAIMS = (
    "not a compact-adapter proof artifact",
    "not a transcript-stable compact-adapter proof-size win",
    "not a replacement for the current native attention+MLP frontier",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not timing evidence",
    "not a full transformer block proof",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-variant-invariant-reprove-preflight-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-variant-invariant-reprove-preflight-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate.py scripts/tests/test_zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_variant_invariant_reprove_preflight_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "claim_boundary",
    "source_artifacts",
    "source_preflight",
    "stable_measurement",
    "reprove_plan",
    "summary",
    "interpretation",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = (
    "decision",
    "result",
    "current_frontier_typed_bytes",
    "duplicate_label_control_typed_bytes",
    "compact_label_control_typed_bytes",
    "label_control_saving_bytes",
    "direct_opening_value_saving_bytes",
    "transcript_path_sensitive_saving_bytes",
    "stable_reprove_supported_by_current_source",
    "compact_frontier_promoted",
    "next_required_pr",
)


class VariantInvariantReprovePreflightError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise VariantInvariantReprovePreflightError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    digest = hashlib.blake2b(digest_size=32)
    digest.update(PAYLOAD_DOMAIN.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(material))
    return "blake2b-256:" + digest.hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VariantInvariantReprovePreflightError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VariantInvariantReprovePreflightError(f"{label} must be list")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise VariantInvariantReprovePreflightError(f"{label} must be boolean")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VariantInvariantReprovePreflightError(f"{label} must be integer")
    return value


def read_regular_file(path: pathlib.Path, label: str, max_bytes: int | None = None) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as err:
        raise VariantInvariantReprovePreflightError(f"failed to open {label}: {err}") from err
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise VariantInvariantReprovePreflightError(f"{label} must be a regular file")
        if max_bytes is not None and before.st_size > max_bytes:
            raise VariantInvariantReprovePreflightError(f"{label} exceeds max size")
        chunks: list[bytes] = []
        remaining = (max_bytes + 1) if max_bytes is not None else before.st_size + 1
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if max_bytes is not None and len(raw) > max_bytes:
            raise VariantInvariantReprovePreflightError(f"{label} exceeds max size")
        after = os.fstat(fd)
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise VariantInvariantReprovePreflightError(f"{label} changed while reading")
        return raw
    finally:
        os.close(fd)


def read_json(path: pathlib.Path, label: str) -> tuple[dict[str, Any], bytes]:
    raw = read_regular_file(path, label, MAX_JSON_BYTES)
    try:
        payload = json.loads(
            raw,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                VariantInvariantReprovePreflightError(f"{label} contains non-finite JSON constant {constant}")
            ),
        )
    except json.JSONDecodeError as err:
        raise VariantInvariantReprovePreflightError(f"failed to parse {label}: {err}") from err
    return _dict(payload, label), raw


def source_artifact(artifact_id: str, path: pathlib.Path, raw: bytes, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact = {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if payload is not None:
        artifact["payload_sha256"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return artifact


def validate_source_hashes(source_raw: bytes, transcript_payload: dict[str, Any], transcript_raw: bytes) -> None:
    if hashlib.sha256(source_raw).hexdigest() != EXPECTED_SOURCE_SHA256:
        raise VariantInvariantReprovePreflightError("native attention+MLP source hash drift")
    if hashlib.sha256(transcript_raw).hexdigest() != EXPECTED_TRANSCRIPT_STABLE_SHA256:
        raise VariantInvariantReprovePreflightError("transcript-stable evidence hash drift")
    if hashlib.sha256(canonical_json_bytes(transcript_payload)).hexdigest() != EXPECTED_TRANSCRIPT_STABLE_PAYLOAD_SHA256:
        raise VariantInvariantReprovePreflightError("transcript-stable payload hash drift")


def validate_source_shape(source_text: str) -> dict[str, Any]:
    present = {}
    for key, snippet in SOURCE_SNIPPETS.items():
        present[key] = snippet in source_text
        if not present[key]:
            raise VariantInvariantReprovePreflightError(f"missing source snippet: {key}")
    absent = {token: token not in source_text for token in ABSENT_SOURCE_TOKENS}
    if not all(absent.values()):
        raise VariantInvariantReprovePreflightError("unexpected variant selector token already present")
    return {
        "duplicate_adapter_in_preprocessed_trace": present["preprocessed_adapter_trace"],
        "duplicate_adapter_in_base_trace": present["base_adapter_trace"],
        "source_comment_says_adapter_intentionally_duplicated": present["duplicate_comment"],
        "adapter_trace_cells_compile_time_constant": present["trace_cell_constant"],
        "input_validation_pins_duplicate_adapter_trace_cells": present["trace_cell_validation"],
        "variant_selector_present": False,
        "compact_adapter_backend_present": False,
        "variant_invariant_policy_present": False,
        "multi_transcript_policy_present": False,
        "absent_tokens_checked": list(ABSENT_SOURCE_TOKENS),
    }


def validate_transcript_stable_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(payload.get("summary"), "transcript-stable summary")
    if summary.get("current_frontier_typed_bytes") != CURRENT_FRONTIER_TYPED_BYTES:
        raise VariantInvariantReprovePreflightError("current frontier typed drift")
    if summary.get("best_reported_label_control_saving_bytes") != LABEL_CONTROL_SAVING_BYTES:
        raise VariantInvariantReprovePreflightError("label-control saving drift")
    if summary.get("label_control_direct_opening_value_saving_bytes") != DIRECT_OPENING_VALUE_SAVING_BYTES:
        raise VariantInvariantReprovePreflightError("direct saving drift")
    if summary.get("label_control_transcript_path_sensitive_saving_bytes") != TRANSCRIPT_PATH_SENSITIVE_SAVING_BYTES:
        raise VariantInvariantReprovePreflightError("path-sensitive saving drift")
    if _bool(summary.get("stable_frontier_promotion"), "stable frontier promotion") is not False:
        raise VariantInvariantReprovePreflightError("stable frontier overclaim drift")
    if _bool(summary.get("nanozk_win_claimed"), "NANOZK win claimed") is not False:
        raise VariantInvariantReprovePreflightError("NANOZK overclaim drift")
    comparisons = _list(payload.get("comparisons"), "transcript-stable comparisons")
    promotable = [
        item
        for item in comparisons
        if _dict(item, "comparison").get("transcript_stable_for_promotion") is True
    ]
    if promotable:
        raise VariantInvariantReprovePreflightError("unexpected promotable compact comparison")
    return {
        "current_frontier_typed_bytes": summary["current_frontier_typed_bytes"],
        "duplicate_label_control_typed_bytes": DUPLICATE_LABEL_CONTROL_TYPED_BYTES,
        "compact_label_control_typed_bytes": COMPACT_LABEL_CONTROL_TYPED_BYTES,
        "label_control_saving_bytes": summary["best_reported_label_control_saving_bytes"],
        "direct_opening_value_saving_bytes": summary["label_control_direct_opening_value_saving_bytes"],
        "transcript_path_sensitive_saving_bytes": summary[
            "label_control_transcript_path_sensitive_saving_bytes"
        ],
        "path_sensitive_share": summary["label_control_transcript_path_sensitive_share"],
        "stable_promotable_comparison_count": summary["stable_promotable_comparison_count"],
        "nanozk_reported_d128_block_proof_bytes": summary["nanozk_reported_d128_block_proof_bytes"],
        "nanozk_win_claimed": False,
    }


def build_payload() -> dict[str, Any]:
    source_raw = read_regular_file(SOURCE_PATH, "native attention+MLP single proof source")
    transcript_payload, transcript_raw = read_json(TRANSCRIPT_STABLE_PATH, "transcript-stable comparison evidence")
    validate_source_hashes(source_raw, transcript_payload, transcript_raw)
    source_text = source_raw.decode("utf-8")
    source_preflight = validate_source_shape(source_text)
    stable_measurement = validate_transcript_stable_evidence(transcript_payload)
    backend_blockers = [
        "single proof source extends adapter_trace(input)? into both preprocessed and base traces",
        "input validation pins adapter_trace_cells to the duplicate 1536-cell constant",
        "current CLI/input/envelope surface has no duplicate-vs-compact adapter selector",
        "no per-variant compact proof envelope or query-inventory fingerprint exists yet",
    ]
    reprove_plan = {
        "next_required_pr": "source-backed compact adapter selector",
        "minimum_backend_changes": [
            "add explicit duplicate and compact adapter modes with versioned statement labels",
            "make compact mode prove only the non-public adapter witness columns while referencing fixed columns",
            "emit separate duplicate and compact proof envelopes",
            "emit per-variant local binary accounting and record-stream fingerprints",
            "compare either under a declared multi-transcript policy or a defensible variant-invariant transcript policy",
        ],
        "go_gate_after_backend_work": (
            "compact variant verifies, keeps attention-output-to-d128-input value binding, emits source artifacts "
            "and query fingerprints, and stays smaller than the duplicate variant under the declared policy"
        ),
        "no_go_gate_after_backend_work": (
            "compact variant fails verification, weakens value binding, or only wins through path-sensitive query churn"
        ),
    }
    summary = {
        "stable_reprove_supported_by_current_source": False,
        "compact_frontier_promoted": False,
        "current_frontier_typed_bytes": CURRENT_FRONTIER_TYPED_BYTES,
        "duplicate_label_control_typed_bytes": DUPLICATE_LABEL_CONTROL_TYPED_BYTES,
        "compact_label_control_typed_bytes": COMPACT_LABEL_CONTROL_TYPED_BYTES,
        "label_control_saving_bytes": LABEL_CONTROL_SAVING_BYTES,
        "direct_opening_value_saving_bytes": DIRECT_OPENING_VALUE_SAVING_BYTES,
        "transcript_path_sensitive_saving_bytes": TRANSCRIPT_PATH_SENSITIVE_SAVING_BYTES,
        "stable_floor_bytes": DIRECT_OPENING_VALUE_SAVING_BYTES,
        "path_sensitive_bytes_that_need_reprove": TRANSCRIPT_PATH_SENSITIVE_SAVING_BYTES,
        "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "nanozk_win_claimed": False,
        "backend_blocker_count": len(backend_blockers),
    }
    interpretation = {
        "human_result": (
            "The compact-adapter idea is not dead, but the current backend cannot honestly run the issue #636 "
            "experiment yet. The source still duplicates the adapter in both trace trees and exposes no "
            "compact/duplicate selector."
        ),
        "research_meaning": (
            "The only stable saving we can defend today is the 112-byte direct opened-value floor. The larger "
            "736-byte signal remains a live lead, but it needs source-backed compact and duplicate proof artifacts."
        ),
        "recommendation": (
            "Do not spend more comparison work on the current artifacts. Implement the source-backed selector next, "
            "then re-run the proof/accounting comparison."
        ),
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": [
            source_artifact("native_attention_mlp_single_proof_source", SOURCE_PATH, source_raw),
            source_artifact(
                "transcript_stable_comparison_gate",
                TRANSCRIPT_STABLE_PATH,
                transcript_raw,
                transcript_payload,
            ),
        ],
        "source_preflight": source_preflight,
        "stable_measurement": stable_measurement,
        "reprove_plan": reprove_plan,
        "summary": summary,
        "interpretation": interpretation,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_payload(payload: Any) -> None:
    data = _dict(payload, "payload")
    if set(data) not in (CORE_KEYS, FINAL_KEYS):
        raise VariantInvariantReprovePreflightError("payload key set drift")
    for key, expected in {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
    }.items():
        if data.get(key) != expected:
            raise VariantInvariantReprovePreflightError(f"{key} drift")
    if data.get("non_claims") != list(NON_CLAIMS):
        raise VariantInvariantReprovePreflightError("non-claims drift")
    if data.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise VariantInvariantReprovePreflightError("validation commands drift")
    summary = _dict(data.get("summary"), "summary")
    if _bool(summary.get("stable_reprove_supported_by_current_source"), "stable reprove supported") is not False:
        raise VariantInvariantReprovePreflightError("reprove support overclaim")
    if _bool(summary.get("compact_frontier_promoted"), "compact frontier promoted") is not False:
        raise VariantInvariantReprovePreflightError("compact frontier overclaim")
    if _bool(summary.get("nanozk_win_claimed"), "NANOZK win claimed") is not False:
        raise VariantInvariantReprovePreflightError("NANOZK overclaim")
    if summary.get("stable_floor_bytes") != DIRECT_OPENING_VALUE_SAVING_BYTES:
        raise VariantInvariantReprovePreflightError("stable floor drift")
    if summary.get("path_sensitive_bytes_that_need_reprove") != TRANSCRIPT_PATH_SENSITIVE_SAVING_BYTES:
        raise VariantInvariantReprovePreflightError("path-sensitive reprove budget drift")
    source_preflight = _dict(data.get("source_preflight"), "source preflight")
    if _bool(source_preflight.get("variant_selector_present"), "variant selector present") is not False:
        raise VariantInvariantReprovePreflightError("fake selector accepted")
    expected = build_payload()
    for key in CORE_KEYS - {"payload_commitment"}:
        if data.get(key) != expected.get(key):
            raise VariantInvariantReprovePreflightError(f"{key} drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise VariantInvariantReprovePreflightError("payload commitment drift")
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(MUTATION_NAMES):
            raise VariantInvariantReprovePreflightError("mutation inventory drift")
        if data.get("case_count") != len(MUTATION_NAMES) or len(cases) != len(MUTATION_NAMES):
            raise VariantInvariantReprovePreflightError("mutation case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise VariantInvariantReprovePreflightError("not all mutations rejected")
        for expected_name, case_value in zip(MUTATION_NAMES, cases, strict=True):
            case = _dict(case_value, "mutation case")
            if case.get("name") != expected_name:
                raise VariantInvariantReprovePreflightError("mutation case order drift")
            if case.get("accepted") is not False or case.get("rejected") is not True:
                raise VariantInvariantReprovePreflightError("mutation acceptance drift")


MutationFn = Callable[[dict[str, Any]], None]


def _source_artifact_hash_drift(payload: dict[str, Any]) -> None:
    payload["source_artifacts"][0]["sha256"] = "00" * 32


def _fake_selector_present(payload: dict[str, Any]) -> None:
    payload["source_preflight"]["variant_selector_present"] = True


def _reprove_promoted(payload: dict[str, Any]) -> None:
    payload["summary"]["stable_reprove_supported_by_current_source"] = True


def _compact_frontier_promoted(payload: dict[str, Any]) -> None:
    payload["summary"]["compact_frontier_promoted"] = True


def _stable_floor_inflated(payload: dict[str, Any]) -> None:
    payload["summary"]["stable_floor_bytes"] = LABEL_CONTROL_SAVING_BYTES


def _path_sensitive_budget_erased(payload: dict[str, Any]) -> None:
    payload["summary"]["path_sensitive_bytes_that_need_reprove"] = 0


def _payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "blake2b-256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("result_promoted", lambda p: p.__setitem__("result", "GO_VARIANT_INVARIANT_COMPACT_REPROVE"), True),
    ("reprove_support_promoted", _reprove_promoted, True),
    ("compact_frontier_promoted", _compact_frontier_promoted, True),
    ("nanozk_win_promoted", lambda p: p["summary"].__setitem__("nanozk_win_claimed", True), True),
    ("fake_selector_present", _fake_selector_present, True),
    ("stable_floor_inflated", _stable_floor_inflated, True),
    ("path_sensitive_budget_erased", _path_sensitive_budget_erased, True),
    ("source_artifact_hash_drift", _source_artifact_hash_drift, True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", _payload_commitment_drift, False),
)

MUTATION_NAMES = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutations(core: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = json.loads(json.dumps(core))
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated)
        except VariantInvariantReprovePreflightError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result() -> dict[str, Any]:
    core = build_payload()
    cases = run_mutations(core)
    final = json.loads(json.dumps(core))
    final["mutation_inventory"] = list(MUTATION_NAMES)
    final["cases"] = cases
    final["case_count"] = len(cases)
    final["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    refresh_payload_commitment(final)
    validate_payload(final)
    return final


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    summary = payload["summary"]
    row = {
        "decision": payload["decision"],
        "result": payload["result"],
        "next_required_pr": payload["reprove_plan"]["next_required_pr"],
        **{key: summary[key] for key in TSV_COLUMNS if key in summary},
    }
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, extrasaction="ignore", delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue()


PINNED_OUTPUTS_BY_CASEFOLD = {
    JSON_OUT.name.casefold(): JSON_OUT.name,
    TSV_OUT.name.casefold(): TSV_OUT.name,
}


def evidence_leaf_name(path: pathlib.Path, label: str) -> str:
    candidate = ROOT / path if not path.is_absolute() else path
    evidence_root = EVIDENCE_DIR.resolve()
    if candidate.parent.resolve() != evidence_root:
        raise VariantInvariantReprovePreflightError(
            f"{label} path must stay under docs/engineering/evidence as a direct child"
        )
    if candidate.name in {"", ".", ".."}:
        raise VariantInvariantReprovePreflightError(f"{label} path has invalid filename")
    return candidate.name


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    if path is None:
        return None
    leaf_name = evidence_leaf_name(path, "output")
    if pathlib.Path(leaf_name).suffix != suffix:
        raise VariantInvariantReprovePreflightError(f"output path must end with {suffix}")
    canonical_leaf_name = PINNED_OUTPUTS_BY_CASEFOLD.get(leaf_name.casefold())
    if canonical_leaf_name is None:
        raise VariantInvariantReprovePreflightError("output path must be the pinned preflight evidence path")
    if leaf_name != canonical_leaf_name:
        raise VariantInvariantReprovePreflightError("output path must use the exact pinned preflight filename")
    return EVIDENCE_DIR.resolve() / leaf_name


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    leaf_name = evidence_leaf_name(path, "output")
    directory_fd = -1
    temp_name: str | None = None
    fd = -1
    try:
        directory_fd = os.open(EVIDENCE_DIR, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            target_stat = os.stat(leaf_name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(target_stat.st_mode):
                raise VariantInvariantReprovePreflightError("refusing to write through symlink")
        temp_name = f".{leaf_name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
        fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory_fd)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, leaf_name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        temp_name = None
        os.fsync(directory_fd)
    except OSError as err:
        raise VariantInvariantReprovePreflightError(f"atomic write failed for {path}: {err}") from err
    finally:
        if fd != -1:
            os.close(fd)
        if temp_name is not None and directory_fd != -1:
            try:
                os.unlink(temp_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        if directory_fd != -1:
            os.close(directory_fd)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    out_json = require_output_path(json_path, ".json")
    out_tsv = require_output_path(tsv_path, ".tsv")
    if out_json is not None:
        write_text_atomic(out_json, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    if out_tsv is not None:
        write_text_atomic(out_tsv, to_tsv(payload))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
