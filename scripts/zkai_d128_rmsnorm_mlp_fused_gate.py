#!/usr/bin/env python3
"""Gate the d128 six-component RMSNorm-to-residual native Stwo proof result."""

from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

ACCOUNTING_PATH = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json"
FUSED_INPUT_PATH = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json"
FUSED_ENVELOPE_PATH = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json"

SCHEMA = "zkai-d128-rmsnorm-mlp-fused-gate-v1"
DECISION = "GO_D128_RMSNORM_MLP_FUSED_TYPED_PROOF_SAVING"
RESULT = "GO_SIX_COMPONENT_D128_RMSNORM_MLP_FUSION_SAVES_32144_TYPED_BYTES"
ROUTE_ID = (
    "native_stwo_d128_rmsnorm_public_row_plus_projection_bridge_plus_gate_value_plus_activation_"
    "swiglu_plus_down_projection_plus_residual_add_fused"
)
CLAIM_BOUNDARY = (
    "FUSED_D128_RMSNORM_TO_RESIDUAL_MLP_SURFACE_SAVES_TYPED_PROOF_BYTES_VS_SIX_SEPARATE_"
    "NATIVE_OBJECTS_NOT_ATTENTION_NOT_A_FULL_TRANSFORMER_BLOCK_NOT_A_NANOZK_BENCHMARK"
)
FIRST_BLOCKER = (
    "The fused proof now covers RMSNorm, projection bridge, gate/value, activation/SwiGLU, "
    "down-projection, and residual-add, but still does not include attention in the same native proof object."
)
STATEMENT_COMMITMENT = "blake2b-256:479c20eafd9780100686a5dca460be8a6ddc73c2c33721dbeead53ab622b17eb"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:efbbc7f8b650026986d508438a20f414ccab7670a50a315d8fb1154c939443b6"
EXPECTED_ROW_COUNTS = {
    "rmsnorm_row_count": 128,
    "projection_bridge_row_count": 128,
    "gate_value_row_count": 131_072,
    "activation_row_count": 512,
    "down_projection_row_count": 65_536,
    "residual_add_row_count": 128,
    "fused_total_row_count": 197_504,
}
EXPECTED_AGGREGATE = {
    "fused_proof_json_size_bytes": 77_181,
    "separate_proof_json_size_bytes": 191_361,
    "json_saving_vs_separate_bytes": 114_180,
    "json_ratio_vs_separate": 0.403327,
    "json_saving_ratio_vs_separate": 0.596673,
    "fused_local_typed_bytes": 24_832,
    "separate_local_typed_bytes": 56_976,
    "typed_saving_vs_separate_bytes": 32_144,
    "typed_ratio_vs_separate": 0.435833,
    "typed_saving_ratio_vs_separate": 0.564167,
}
EXPECTED_GROUPED_DELTA = {
    "fixed_overhead": -240,
    "fri_decommitments": -17_024,
    "fri_samples": -1_952,
    "oods_samples": -640,
    "queries_values": -480,
    "trace_decommitments": -11_808,
}
EXPECTED_PATHS = [
    "zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json",
    "zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json",
    "zkai-d128-gate-value-projection-proof-2026-05.envelope.json",
    "zkai-d128-activation-swiglu-proof-2026-05.envelope.json",
    "zkai-d128-down-projection-proof-2026-05.envelope.json",
    "zkai-d128-residual-add-proof-2026-05.envelope.json",
]
EXPECTED_NON_CLAIMS = [
    "not attention plus MLP in one proof object",
    "not a full transformer block",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not recursion or proof-carrying data",
    "not private parameter-opening proof",
    "not upstream Stwo proof serialization",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
]
EXPECTED_VALIDATION_COMMANDS = [
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- build-input docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- prove docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- verify docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.envelope.json",
    "python3 scripts/zkai_d128_rmsnorm_mlp_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_mlp_fused_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_rmsnorm_mlp_fused_proof --lib",
    "git diff --check",
    "just gate-fast",
    "just gate",
]
TSV_COLUMNS = [
    "schema",
    "decision",
    "route_id",
    "comparison_status",
    "fused_total_row_count",
    "fused_proof_json_size_bytes",
    "separate_proof_json_size_bytes",
    "json_saving_vs_separate_bytes",
    "json_ratio_vs_separate",
    "fused_local_typed_bytes",
    "separate_local_typed_bytes",
    "typed_saving_vs_separate_bytes",
    "typed_ratio_vs_separate",
]


class RmsnormMlpFusedGateError(Exception):
    pass


def read_json(path: pathlib.Path, max_bytes: int, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise RmsnormMlpFusedGateError(f"{label} must not be a symlink: {path}")
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except OSError as exc:
        raise RmsnormMlpFusedGateError(f"{label} cannot be read: {path}") from exc
    if len(raw) > max_bytes:
        raise RmsnormMlpFusedGateError(f"{label} exceeds max bytes: {len(raw)} > {max_bytes}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RmsnormMlpFusedGateError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RmsnormMlpFusedGateError(f"{label} must be a JSON object")
    try:
        json.dumps(value, allow_nan=False)
    except ValueError as exc:
        raise RmsnormMlpFusedGateError(f"{label} contains non-finite JSON") from exc
    return value


def require_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RmsnormMlpFusedGateError(f"{label} must be an integer")
    return value


def require_str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise RmsnormMlpFusedGateError(f"{label} must be a string")
    return value


def row_typed(row: dict[str, Any]) -> int:
    accounting = row.get("local_binary_accounting")
    if not isinstance(accounting, dict):
        raise RmsnormMlpFusedGateError("accounting row missing local_binary_accounting")
    return require_int(accounting.get("typed_size_estimate_bytes"), "typed size")


def row_group(row: dict[str, Any]) -> dict[str, int]:
    accounting = row.get("local_binary_accounting")
    if not isinstance(accounting, dict):
        raise RmsnormMlpFusedGateError("accounting row missing local_binary_accounting")
    group = accounting.get("grouped_reconstruction")
    if not isinstance(group, dict):
        raise RmsnormMlpFusedGateError("accounting row missing grouped reconstruction")
    return {key: require_int(group.get(key), f"grouped {key}") for key in EXPECTED_GROUPED_DELTA}


def build_payload() -> dict[str, Any]:
    accounting = read_json(ACCOUNTING_PATH, 8_388_608, "binary accounting")
    input_payload = read_json(FUSED_INPUT_PATH, 4_194_304, "fused input")
    envelope = read_json(FUSED_ENVELOPE_PATH, 8_388_608, "fused envelope")
    envelope_input = envelope.get("input")
    if not isinstance(envelope_input, dict):
        raise RmsnormMlpFusedGateError("fused envelope missing input payload")
    if require_str(envelope_input.get("statement_commitment"), "envelope statement commitment") != require_str(
        input_payload.get("statement_commitment"), "statement commitment"
    ):
        raise RmsnormMlpFusedGateError("envelope/input statement commitment drift")
    if require_str(
        envelope_input.get("public_instance_commitment"),
        "envelope public instance commitment",
    ) != require_str(input_payload.get("public_instance_commitment"), "public instance commitment"):
        raise RmsnormMlpFusedGateError("envelope/input public instance commitment drift")
    if require_str(envelope_input.get("route_id"), "envelope route id") != require_str(
        input_payload.get("route_id"), "input route id"
    ):
        raise RmsnormMlpFusedGateError("envelope/input route id drift")
    rows = accounting.get("rows")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_PATHS):
        raise RmsnormMlpFusedGateError("accounting row count drift")
    paths = [require_str(row.get("evidence_relative_path"), "evidence path") for row in rows]
    if paths != EXPECTED_PATHS:
        raise RmsnormMlpFusedGateError("accounting evidence path order drift")

    fused_row = rows[0]
    separate_rows = rows[1:]
    fused_json = require_int(fused_row.get("proof_json_size_bytes"), "fused proof JSON bytes")
    separate_json = sum(require_int(row.get("proof_json_size_bytes"), "separate proof JSON bytes") for row in separate_rows)
    fused_typed = row_typed(fused_row)
    separate_typed = sum(row_typed(row) for row in separate_rows)
    grouped_delta = {
        key: row_group(fused_row)[key] - sum(row_group(row)[key] for row in separate_rows)
        for key in EXPECTED_GROUPED_DELTA
    }
    aggregate = {
        **EXPECTED_ROW_COUNTS,
        "profiles_checked": 1,
        "fused_proof_json_size_bytes": fused_json,
        "separate_proof_json_size_bytes": separate_json,
        "json_saving_vs_separate_bytes": separate_json - fused_json,
        "json_ratio_vs_separate": round(fused_json / separate_json, 6),
        "json_saving_ratio_vs_separate": round((separate_json - fused_json) / separate_json, 6),
        "fused_local_typed_bytes": fused_typed,
        "separate_local_typed_bytes": separate_typed,
        "typed_saving_vs_separate_bytes": separate_typed - fused_typed,
        "typed_ratio_vs_separate": round(fused_typed / separate_typed, 6),
        "typed_saving_ratio_vs_separate": round((separate_typed - fused_typed) / separate_typed, 6),
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "comparison_status": "fused_six_component_native_proof_saves_typed_bytes_vs_separate_objects",
        "first_blocker": FIRST_BLOCKER,
        "aggregate": aggregate,
        "grouped_typed_delta_vs_separate": grouped_delta,
        "proof_backend_version": require_str(envelope.get("proof_backend_version"), "proof backend version"),
        "statement_version": require_str(envelope.get("statement_version"), "statement version"),
        "statement_commitment": require_str(input_payload.get("statement_commitment"), "statement commitment"),
        "public_instance_commitment": require_str(input_payload.get("public_instance_commitment"), "public instance commitment"),
        "non_claims": input_payload.get("non_claims"),
        "validation_commands": input_payload.get("validation_commands"),
        "source_artifacts": EXPECTED_PATHS,
    }
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    base_keys = {
        "schema",
        "decision",
        "result",
        "route_id",
        "claim_boundary",
        "comparison_status",
        "first_blocker",
        "aggregate",
        "grouped_typed_delta_vs_separate",
        "proof_backend_version",
        "statement_version",
        "statement_commitment",
        "public_instance_commitment",
        "non_claims",
        "validation_commands",
        "source_artifacts",
    }
    report_keys = base_keys | {"mutation_rejections", "payload_commitment"}
    actual_keys = set(payload)
    if actual_keys not in (base_keys, report_keys):
        raise RmsnormMlpFusedGateError("payload key drift")
    base_payload = {key: payload[key] for key in base_keys}
    if payload["schema"] != SCHEMA or payload["decision"] != DECISION or payload["route_id"] != ROUTE_ID:
        raise RmsnormMlpFusedGateError("identity drift")
    if payload["result"] != RESULT:
        raise RmsnormMlpFusedGateError("result drift")
    if payload["claim_boundary"] != CLAIM_BOUNDARY:
        raise RmsnormMlpFusedGateError("claim boundary drift")
    if payload["first_blocker"] != FIRST_BLOCKER:
        raise RmsnormMlpFusedGateError("first blocker drift")
    if payload["comparison_status"] != "fused_six_component_native_proof_saves_typed_bytes_vs_separate_objects":
        raise RmsnormMlpFusedGateError("comparison status drift")
    if payload["aggregate"] != {**EXPECTED_ROW_COUNTS, "profiles_checked": 1, **EXPECTED_AGGREGATE}:
        raise RmsnormMlpFusedGateError("aggregate metric drift")
    if payload["grouped_typed_delta_vs_separate"] != EXPECTED_GROUPED_DELTA:
        raise RmsnormMlpFusedGateError("grouped typed delta drift")
    if payload["proof_backend_version"] != "stwo-d128-rmsnorm-mlp-fused-air-proof-v1":
        raise RmsnormMlpFusedGateError("proof backend version drift")
    if payload["statement_version"] != "zkai-d128-rmsnorm-mlp-fused-statement-v1":
        raise RmsnormMlpFusedGateError("statement version drift")
    if payload["statement_commitment"] != STATEMENT_COMMITMENT:
        raise RmsnormMlpFusedGateError("statement commitment drift")
    if payload["public_instance_commitment"] != PUBLIC_INSTANCE_COMMITMENT:
        raise RmsnormMlpFusedGateError("public instance commitment drift")
    if payload["non_claims"] != EXPECTED_NON_CLAIMS:
        raise RmsnormMlpFusedGateError("non-claims drift")
    if payload["validation_commands"] != EXPECTED_VALIDATION_COMMANDS:
        raise RmsnormMlpFusedGateError("validation command drift")
    if payload["source_artifacts"] != EXPECTED_PATHS:
        raise RmsnormMlpFusedGateError("source artifact drift")
    if actual_keys == report_keys:
        expected_rejections = {name: "rejected" for name in mutation_cases(base_payload)}
        if payload["mutation_rejections"] != expected_rejections:
            raise RmsnormMlpFusedGateError("mutation rejection drift")
        report_payload = copy.deepcopy(base_payload)
        report_payload["mutation_rejections"] = expected_rejections
        if payload["payload_commitment"] != payload_commitment(report_payload):
            raise RmsnormMlpFusedGateError("payload commitment drift")


def mutation_cases(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = {}
    for name, path, value in [
        ("typed_saving_smuggling", ("aggregate", "typed_saving_vs_separate_bytes"), 1),
        ("typed_ratio_smuggling", ("aggregate", "typed_ratio_vs_separate"), 1.0),
        ("json_ratio_smuggling", ("aggregate", "json_ratio_vs_separate"), 1.0),
        ("row_count_smuggling", ("aggregate", "fused_total_row_count"), 1),
        ("claim_boundary_smuggling", ("claim_boundary",), "NANOZK_WIN"),
        ("proof_version_smuggling", ("proof_backend_version",), "stwo-drift"),
        ("statement_commitment_smuggling", ("statement_commitment",), "blake2b-256:" + "1" * 64),
        ("public_instance_commitment_smuggling", ("public_instance_commitment",), "blake2b-256:" + "2" * 64),
        ("non_claim_removal", ("non_claims",), []),
    ]:
        mutated = copy.deepcopy(payload)
        target = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        cases[name] = mutated
    return cases


def run_mutations(payload: dict[str, Any]) -> dict[str, str]:
    results = {}
    for name, mutated in mutation_cases(payload).items():
        try:
            validate_payload(mutated)
        except RmsnormMlpFusedGateError:
            results[name] = "rejected"
        else:
            results[name] = "accepted"
    return results


def payload_commitment(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def assert_output_path(path: pathlib.Path) -> pathlib.Path:
    parent = path.parent if path.parent != pathlib.Path("") else pathlib.Path(".")
    if path.exists() and path.is_symlink():
        raise RmsnormMlpFusedGateError(f"output path must not be a symlink: {path}")
    resolved_parent = parent.resolve()
    try:
        resolved_parent.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as exc:
        raise RmsnormMlpFusedGateError(f"output parent escapes evidence dir: {path}") from exc
    return resolved_parent


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    parent = assert_output_path(path)
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    tmp = pathlib.Path(tmp_name)
    write_completed = False
    try:
        written = 0
        while written < len(data):
            written += os.write(fd, data[written:])
        os.fsync(fd)
        write_completed = True
    finally:
        with contextlib.suppress(OSError):
            os.close(fd)
        if not write_completed:
            with contextlib.suppress(OSError):
                tmp.unlink()
    try:
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    row = {column: payload["aggregate"].get(column, payload.get(column)) for column in TSV_COLUMNS}
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    atomic_write(path, out.getvalue().encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    payload = build_payload()
    validate_payload(payload)
    payload["mutation_rejections"] = run_mutations(payload)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload)
    print(json.dumps(payload["aggregate"], sort_keys=True))
    print(f"mutations_rejected={sum(v == 'rejected' for v in payload['mutation_rejections'].values())}/{len(payload['mutation_rejections'])}")
    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
