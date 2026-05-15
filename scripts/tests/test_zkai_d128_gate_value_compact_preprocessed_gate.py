import copy
import hashlib
import unittest

from scripts import zkai_d128_gate_value_compact_preprocessed_gate as gate


RECORD_SPECS = {
    "pcs.commitments": ("blake2s_hash", "blake2s_hash_bytes"),
    "pcs.trace_decommitments.hash_witness": ("blake2s_hash", "blake2s_hash_bytes"),
    "pcs.sampled_values": ("secure_field", "secure_field_bytes"),
    "pcs.queried_values": ("base_field", "base_field_bytes"),
    "pcs.fri.first_layer.fri_witness": ("secure_field", "secure_field_bytes"),
    "pcs.fri.inner_layers.fri_witness": ("secure_field", "secure_field_bytes"),
    "pcs.fri.last_layer_poly": ("secure_field", "secure_field_bytes"),
    "pcs.fri.first_layer.commitment": ("blake2s_hash", "blake2s_hash_bytes"),
    "pcs.fri.inner_layers.commitments": ("blake2s_hash", "blake2s_hash_bytes"),
    "pcs.fri.first_layer.decommitment.hash_witness": ("blake2s_hash", "blake2s_hash_bytes"),
    "pcs.fri.inner_layers.decommitment.hash_witness": ("blake2s_hash", "blake2s_hash_bytes"),
    "pcs.proof_of_work": ("u64_le", "proof_of_work_bytes"),
    "pcs.config": ("pcs_config", "pcs_config_bytes"),
}


def record(path, count):
    scalar_kind, size_key = RECORD_SPECS[path]
    size = gate.EXPECTED_SIZE_CONSTANTS[size_key]
    return {
        "path": path,
        "scalar_kind": scalar_kind,
        "item_count": count,
        "item_size_bytes": size,
        "total_bytes": count * size,
    }


def grouped(records):
    by_path = {item["path"]: item["total_bytes"] for item in records}
    return {
        "oods_samples": by_path["pcs.sampled_values"],
        "queries_values": by_path["pcs.queried_values"],
        "fri_samples": by_path["pcs.fri.first_layer.fri_witness"]
        + by_path["pcs.fri.inner_layers.fri_witness"]
        + by_path["pcs.fri.last_layer_poly"],
        "fri_decommitments": by_path["pcs.fri.first_layer.commitment"]
        + by_path["pcs.fri.inner_layers.commitments"]
        + by_path["pcs.fri.first_layer.decommitment.hash_witness"]
        + by_path["pcs.fri.inner_layers.decommitment.hash_witness"],
        "trace_decommitments": by_path["pcs.commitments"]
        + by_path["pcs.trace_decommitments.hash_witness"],
        "fixed_overhead": by_path["pcs.proof_of_work"] + by_path["pcs.config"],
    }


def local_accounting(counts, proof_json):
    records = [record(path, counts[path]) for path in gate.EXPECTED_RECORD_PATHS]
    total = sum(item["total_bytes"] for item in records)
    grouped_values = grouped(records)
    return {
        "format_domain": "zkai:stwo:local-binary-proof-accounting",
        "format_version": "v1",
        "upstream_stwo_serialization_status": "NOT_UPSTREAM_STWO_SERIALIZATION_LOCAL_ACCOUNTING_RECORD_STREAM_ONLY",
        "records": records,
        "record_count": len(records),
        "component_sum_bytes": total,
        "typed_size_estimate_bytes": total,
        "grouped_reconstruction": copy.deepcopy(grouped_values),
        "stwo_grouped_breakdown": copy.deepcopy(grouped_values),
        "record_stream_bytes": 1084,
        "record_stream_sha256": hashlib.sha256(str(records).encode()).hexdigest(),
        "json_over_local_typed_ratio": gate.rounded_ratio(proof_json, total),
        "json_minus_local_typed_bytes": proof_json - total,
    }


def cli_row(role, relative_path, proof_backend_version, statement_version, counts, json_bytes):
    return {
        "path": str(gate.EVIDENCE_DIR / relative_path),
        "evidence_relative_path": relative_path,
        "envelope_sha256": "11" * 32,
        "proof_sha256": "22" * 32,
        "proof_json_size_bytes": json_bytes,
        "envelope_metadata": {
            "proof_backend": "stwo",
            "proof_backend_version": proof_backend_version,
            "statement_version": statement_version,
            "verifier_domain": None,
            "proof_schema_version": None,
            "target_id": None,
        },
        "local_binary_accounting": local_accounting(counts, json_bytes),
    }


def cli_summary():
    return {
        "schema": "zkai-stwo-local-binary-proof-accounting-cli-v1",
        "accounting_domain": "zkai:stwo:local-binary-proof-accounting",
        "accounting_format_version": "v1",
        "accounting_source": "fixture",
        "upstream_stwo_serialization_status": "NOT_UPSTREAM_STWO_SERIALIZATION_LOCAL_ACCOUNTING_RECORD_STREAM_ONLY",
        "proof_payload_kind": "utf8_json_object_with_single_stark_proof_field",
        "safety": dict(gate.EXPECTED_SAFETY),
        "size_constants": dict(gate.EXPECTED_SIZE_CONSTANTS),
        "rows": [
            cli_row(
                gate.COMPACT_ROLE,
                gate.COMPACT_RELATIVE_PATH,
                gate.COMPACT_PROOF_BACKEND_VERSION,
                gate.COMPACT_STATEMENT_VERSION,
                gate.EXPECTED_COMPACT_RECORD_COUNTS,
                gate.COMPACT_PROOF_JSON_BYTES,
            ),
            cli_row(
                gate.BASELINE_ROLE,
                gate.BASELINE_RELATIVE_PATH,
                gate.BASELINE_PROOF_BACKEND_VERSION,
                gate.BASELINE_STATEMENT_VERSION,
                gate.EXPECTED_BASELINE_RECORD_COUNTS,
                gate.BASELINE_PROOF_JSON_BYTES,
            ),
        ],
    }


def build_payload(summary=None, **kwargs):
    return gate.build_payload(
        cli_summary() if summary is None else summary,
        compact_envelope_size_bytes=kwargs.pop("compact_envelope_size_bytes", gate.COMPACT_ENVELOPE_BYTES),
        baseline_envelope_size_bytes=kwargs.pop("baseline_envelope_size_bytes", gate.BASELINE_ENVELOPE_BYTES),
        **kwargs,
    )


class D128GateValueCompactPreprocessedGateTests(unittest.TestCase):
    def test_build_payload_records_checked_no_go(self):
        payload = build_payload()

        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertEqual(payload["aggregate"]["row_count"], 131_072)
        self.assertEqual(payload["aggregate"]["compact_local_typed_bytes"], 18_672)
        self.assertEqual(payload["aggregate"]["baseline_local_typed_bytes"], 16_360)
        self.assertEqual(payload["aggregate"]["typed_increase_vs_baseline_bytes"], 2_312)
        self.assertEqual(payload["aggregate"]["typed_ratio_vs_baseline"], 1.14132)
        self.assertEqual(payload["grouped_delta_bytes"]["queries_values"], -72)
        self.assertEqual(payload["grouped_delta_bytes"]["fri_decommitments"], 1_920)
        self.assertIn("not a NANOZK proof-size win", payload["non_claims"])
        self.assertEqual(payload["mutations_checked"], len(gate.MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_individual_mutations_reject(self):
        summary = cli_summary()
        payload = build_payload(summary, include_mutations=False)
        for name in gate.MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.GateValueCompactGateError, msg=name):
                gate.validate_payload(mutated, summary, allow_missing_mutation_summary=True)

    def test_rejects_record_item_count_drift(self):
        summary = cli_summary()
        record = summary["rows"][0]["local_binary_accounting"]["records"][1]
        record["item_count"] -= 1
        record["total_bytes"] = record["item_count"] * record["item_size_bytes"]
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "record counts drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_payload_route_question_and_next_step_drift(self):
        summary = cli_summary()
        payload = build_payload(summary, include_mutations=False)
        for field, value, expected_error in (
            ("route_id", "unexpected-route", "route id drift"),
            ("question", "Did this beat NANOZK?", "question drift"),
            ("next_research_step", "promote direct dense compaction", "next research step drift"),
        ):
            mutated = copy.deepcopy(payload)
            mutated[field] = value
            mutated["payload_commitment"] = gate.payload_commitment(mutated)
            with self.assertRaisesRegex(gate.GateValueCompactGateError, expected_error):
                gate.validate_payload(mutated, summary, allow_missing_mutation_summary=True)

    def test_rejects_statement_version_drift(self):
        summary = cli_summary()
        summary["rows"][0]["envelope_metadata"]["statement_version"] = "v0"
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "statement version drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_accounting_record_count_drift(self):
        summary = cli_summary()
        summary["rows"][0]["local_binary_accounting"]["record_count"] += 1
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "accounting record count drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_duplicate_record_path(self):
        summary = cli_summary()
        accounting = summary["rows"][0]["local_binary_accounting"]
        accounting["records"][-1] = copy.deepcopy(accounting["records"][-2])
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "duplicate record path"):
            build_payload(summary, include_mutations=False)

    def test_rejects_extra_record_path(self):
        summary = cli_summary()
        accounting = summary["rows"][0]["local_binary_accounting"]
        extra = copy.deepcopy(accounting["records"][-1])
        extra["path"] = "pcs.unexpected"
        accounting["records"][-1] = extra
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "unexpected record path"):
            build_payload(summary, include_mutations=False)

    def test_rejects_record_path_order_drift(self):
        summary = cli_summary()
        records = summary["rows"][0]["local_binary_accounting"]["records"]
        records[0], records[1] = records[1], records[0]
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "record path order drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_record_item_size_drift(self):
        summary = cli_summary()
        summary["rows"][0]["local_binary_accounting"]["records"][0]["item_size_bytes"] += 1
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "record item size drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_record_scalar_kind_drift(self):
        summary = cli_summary()
        summary["rows"][0]["local_binary_accounting"]["records"][0]["scalar_kind"] = "secure_field"
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "record scalar kind drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_record_total_bytes_drift(self):
        summary = cli_summary()
        summary["rows"][0]["local_binary_accounting"]["records"][0]["total_bytes"] += 1
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "record total bytes drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_grouped_reconstruction_drift(self):
        summary = cli_summary()
        summary["rows"][0]["local_binary_accounting"]["grouped_reconstruction"]["fixed_overhead"] += 1
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "compact grouped_reconstruction drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_stwo_grouped_breakdown_drift(self):
        summary = cli_summary()
        summary["rows"][1]["local_binary_accounting"]["stwo_grouped_breakdown"]["fixed_overhead"] += 1
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "baseline stwo_grouped_breakdown drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_duplicate_accounting_row(self):
        summary = cli_summary()
        summary["rows"].append(copy.deepcopy(summary["rows"][0]))
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "duplicate accounting row"):
            build_payload(summary, include_mutations=False)

    def test_rejects_envelope_size_drift(self):
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "compact envelope JSON size drift"):
            build_payload(
                include_mutations=False,
                compact_envelope_size_bytes=gate.COMPACT_ENVELOPE_BYTES + 1,
            )
        with self.assertRaisesRegex(gate.GateValueCompactGateError, "baseline envelope JSON size drift"):
            build_payload(
                include_mutations=False,
                baseline_envelope_size_bytes=gate.BASELINE_ENVELOPE_BYTES + 1,
            )

    def test_rejects_bool_encoded_metrics(self):
        summary = cli_summary()
        payload = build_payload(summary, include_mutations=False)
        payload["aggregate"]["compact_local_typed_bytes"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaises(gate.GateValueCompactGateError):
            gate.validate_payload(payload, summary, allow_missing_mutation_summary=True)


if __name__ == "__main__":
    unittest.main()
