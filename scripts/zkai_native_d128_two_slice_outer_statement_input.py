#!/usr/bin/env python3
"""Build the host-verified native d128 two-slice outer statement input.

This input deliberately stops short of recursive verifier execution.  It binds
the two selected d128 inner Stwo slice results into a native outer statement
surface so that the follow-up verifier-execution work has a checked target and
cannot relabel package bytes as native recursive proof bytes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

JSON_OUT = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv"

SCHEMA = "zkai-native-d128-two-slice-outer-statement-air-proof-input-v1"
DECISION = "NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_INPUT"
OPERATION = "d128_two_slice_outer_statement_binding"
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
WIDTH = 128
SELECTED_SLICE_COUNT = 2
SELECTED_CHECKED_ROWS = 256
TWO_SLICE_TARGET_COMMITMENT = "blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6"
ACCUMULATOR_COMMITMENT = "blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d"
VERIFIER_HANDLE_COMMITMENT = "blake2b-256:8dd18b7b5b8d0a5399535f0a02f9a1fe4128211bad8f3e69bb44c92cdf07a131"
PROOF_NATIVE_PARAMETER_KIND = "d128-two-slice-outer-statement-parameters-v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:d128-two-slice-outer-public-instance:v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:d128-two-slice-outer-proof-native-parameter:v1"

NON_CLAIMS = [
    "not native verifier execution of the selected inner Stwo proofs",
    "not recursion or proof-carrying data",
    "not a native d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not full transformer inference",
    "not production-ready zkML",
]

PROOF_VERIFIER_HARDENING = [
    "selected slice order checked before proof verification",
    "selected row count checked before proof verification",
    "two-slice target commitment bound into every outer statement row",
    "accumulator commitment bound into every outer statement row",
    "verifier-handle commitment bound into every outer statement row",
    "selected slice statement commitments bound as digest limbs",
    "selected source evidence hashes bound as digest limbs",
    "proof backend version labels bound as digest limbs",
    "verifier-domain label bound as digest limbs",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

NEXT_BACKEND_STEP = (
    "replace host-verified slice-result binding with native Stwo verifier-execution constraints "
    "for the selected inner slice proofs"
)

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_native_d128_two_slice_outer_statement_input.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv",
    "cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- prove docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- verify docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 test d128_native_two_slice_outer_statement_proof --lib --features stwo-backend",
    "python3 scripts/zkai_native_d128_two_slice_outer_statement_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.tsv",
    "git diff --check",
    "just gate-fast",
]

ROWS: list[dict[str, Any]] = [
    {
        "index": 0,
        "slice_id": "rmsnorm_public_rows",
        "slice_tag": 1,
        "row_count": 128,
        "verified": True,
        "proof_backend_version": "stwo-d128-rmsnorm-public-row-air-proof-v3",
        "verifier_domain": VERIFIER_DOMAIN,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "statement_commitment": "blake2b-256:de944915f2664ac7a893f4ba9a029323f7408eac58bf39170a0935d7832ccbd8",
        "public_instance_commitment": "blake2b-256:2dfa2ceffd67f95059b3d6cd639a82577f2bbd7be43e99c25814feb703a8fd72",
        "proof_native_parameter_commitment": "blake2b-256:8d8bded756f3290980eaab322ba986b02c5584bc8348c2ffcfa4e4860a80944c",
        "source_file_sha256": "d80f9f16e5f8aef3a8ec49271bb0616483cb6906731539aea2f73ba4678123ec",
        "source_payload_sha256": "19688310ba6001e16b80c15532f74b59097222a1aa9be132ea66b11a116ded05",
    },
    {
        "index": 1,
        "slice_id": "rmsnorm_projection_bridge",
        "slice_tag": 2,
        "row_count": 128,
        "verified": True,
        "proof_backend_version": "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1",
        "verifier_domain": VERIFIER_DOMAIN,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "statement_commitment": "blake2b-256:fe0a9e59560611ed5220fd25b082806977a66a7032f457fce2cd5c3a41856728",
        "public_instance_commitment": "blake2b-256:ca94d85cb0ed5e9001cd3def00817060745fa015bd8dda5f08732944f7418383",
        "proof_native_parameter_commitment": "blake2b-256:ff31d2b502dac1e7d9f9cca69c4bd31e93e068dab49884e61a300a99389d58c1",
        "source_file_sha256": "11f93a3ecee19c40ff14d154e054dab56a1b9c1a2dbb1d609a918e201e6fd849",
        "source_payload_sha256": "e6e46f2e35df3177790c7dbdc5c519f4a7d62e8ed6cba0501ffac94db73975f3",
    },
]


def blake2b_commitment_bytes(data: bytes, domain: str) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    hasher.update(domain.encode())
    hasher.update(b"\0")
    hasher.update(data)
    return f"blake2b-256:{hasher.hexdigest()}"


def compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def row_statement_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": row["index"],
        "proof_backend_version": row["proof_backend_version"],
        "proof_native_parameter_commitment": row["proof_native_parameter_commitment"],
        "public_instance_commitment": row["public_instance_commitment"],
        "required_backend_version": row["required_backend_version"],
        "row_count": row["row_count"],
        "slice_id": row["slice_id"],
        "slice_tag": row["slice_tag"],
        "source_file_sha256": row["source_file_sha256"],
        "source_payload_sha256": row["source_payload_sha256"],
        "statement_commitment": row["statement_commitment"],
        "verified": row["verified"],
        "verifier_domain": row["verifier_domain"],
    }


def row_statement_json(row: dict[str, Any]) -> str:
    return compact_json(row_statement_payload(row))


def statement_commitment(input_obj: dict[str, Any]) -> str:
    payload = {
        "accumulator_commitment": input_obj["accumulator_commitment"],
        "accumulator_verifier_handle_commitment": input_obj["accumulator_verifier_handle_commitment"],
        "operation": OPERATION,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "rows": [row_statement_payload(row) for row in input_obj["rows"]],
        "selected_checked_rows": input_obj["selected_checked_rows"],
        "selected_slice_count": input_obj["selected_slice_count"],
        "target_id": TARGET_ID,
        "two_slice_target_commitment": input_obj["two_slice_target_commitment"],
        "verifier_domain": VERIFIER_DOMAIN,
        "width": input_obj["width"],
    }
    return blake2b_commitment_bytes(compact_json(payload).encode(), VERIFIER_DOMAIN)


def public_instance_commitment(statement: str) -> str:
    payload = {
        "operation": OPERATION,
        "selected_checked_rows": SELECTED_CHECKED_ROWS,
        "statement_commitment": statement,
        "two_slice_target_commitment": TWO_SLICE_TARGET_COMMITMENT,
    }
    return blake2b_commitment_bytes(compact_json(payload).encode(), PUBLIC_INSTANCE_DOMAIN)


def proof_native_parameter_commitment(statement: str) -> str:
    payload = {
        "kind": PROOF_NATIVE_PARAMETER_KIND,
        "statement_commitment": statement,
    }
    return blake2b_commitment_bytes(compact_json(payload).encode(), PROOF_NATIVE_PARAMETER_DOMAIN)


def build_input() -> dict[str, Any]:
    input_obj: dict[str, Any] = {
        "schema": SCHEMA,
        "decision": DECISION,
        "operation": OPERATION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "selected_slice_count": SELECTED_SLICE_COUNT,
        "selected_checked_rows": SELECTED_CHECKED_ROWS,
        "selected_slice_ids": [row["slice_id"] for row in ROWS],
        "two_slice_target_commitment": TWO_SLICE_TARGET_COMMITMENT,
        "accumulator_commitment": ACCUMULATOR_COMMITMENT,
        "accumulator_verifier_handle_commitment": VERIFIER_HANDLE_COMMITMENT,
        "statement_commitment": "",
        "public_instance_commitment": "",
        "proof_native_parameter_commitment": "",
        "rows": ROWS,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    statement = statement_commitment(input_obj)
    input_obj["statement_commitment"] = statement
    input_obj["public_instance_commitment"] = public_instance_commitment(statement)
    input_obj["proof_native_parameter_commitment"] = proof_native_parameter_commitment(statement)
    return input_obj


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp_path = pathlib.Path(tmp.name)
    tmp_path.replace(path)


def write_tsv(path: pathlib.Path, input_obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as tmp:
        writer = csv.DictWriter(
            tmp,
            fieldnames=[
                "index",
                "slice_id",
                "row_count",
                "verified",
                "proof_backend_version",
                "statement_commitment",
                "public_instance_commitment",
                "source_file_sha256",
                "source_payload_sha256",
            ],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in input_obj["rows"]:
            writer.writerow(
                {
                    "index": row["index"],
                    "slice_id": row["slice_id"],
                    "row_count": row["row_count"],
                    "verified": str(row["verified"]).lower(),
                    "proof_backend_version": row["proof_backend_version"],
                    "statement_commitment": row["statement_commitment"],
                    "public_instance_commitment": row["public_instance_commitment"],
                    "source_file_sha256": row["source_file_sha256"],
                    "source_payload_sha256": row["source_payload_sha256"],
                }
            )
        tmp_path = pathlib.Path(tmp.name)
    tmp_path.replace(path)


def same_output_path(left: pathlib.Path, right: pathlib.Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    if same_output_path(args.write_json, args.write_tsv):
        raise SystemExit("write-json and write-tsv output paths must be distinct")
    input_obj = build_input()
    write_json(args.write_json, input_obj)
    write_tsv(args.write_tsv, input_obj)
    print(
        json.dumps(
            {
                "schema": "zkai-native-d128-two-slice-outer-statement-input-summary-v1",
                "json_path": str(args.write_json),
                "tsv_path": str(args.write_tsv),
                "statement_commitment": input_obj["statement_commitment"],
                "public_instance_commitment": input_obj["public_instance_commitment"],
                "selected_checked_rows": input_obj["selected_checked_rows"],
                "selected_slice_ids": input_obj["selected_slice_ids"],
                "claim_boundary": "host_verified_outer_statement_binding_not_native_verifier_execution",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
