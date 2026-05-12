import copy
import pathlib
import tempfile
import unittest

from scripts import zkai_attention_kv_stwo_binary_typed_proof_accounting_gate as gate


def record(path, count, size):
    return {
        "path": path,
        "scalar_kind": "fixture_scalar",
        "item_count": count,
        "item_size_bytes": size,
        "total_bytes": count * size,
    }


def accounting(seed):
    records = [
        record(path, seed + index + 1, 4 + (index % 3))
        for index, path in enumerate(gate.EXPECTED_RECORD_PATHS)
    ]
    total = sum(item["total_bytes"] for item in records)
    grouped = {
        "oods_samples": records[2]["total_bytes"],
        "queries_values": records[3]["total_bytes"],
        "fri_samples": records[4]["total_bytes"] + records[5]["total_bytes"] + records[6]["total_bytes"],
        "fri_decommitments": records[7]["total_bytes"]
        + records[8]["total_bytes"]
        + records[9]["total_bytes"]
        + records[10]["total_bytes"],
        "trace_decommitments": records[0]["total_bytes"] + records[1]["total_bytes"],
        "fixed_overhead": records[11]["total_bytes"] + records[12]["total_bytes"],
    }
    proof_json_size = total + 100 + seed
    return proof_json_size, {
        "format_domain": gate.ACCOUNTING_DOMAIN,
        "format_version": gate.ACCOUNTING_FORMAT_VERSION,
        "upstream_stwo_serialization_status": gate.UPSTREAM_SERIALIZATION_STATUS,
        "records": records,
        "record_count": len(records),
        "component_sum_bytes": total,
        "typed_size_estimate_bytes": total,
        "grouped_reconstruction": grouped,
        "stwo_grouped_breakdown": copy.deepcopy(grouped),
        "record_stream_bytes": 900 + seed,
        "record_stream_sha256": f"{seed:064x}"[-64:],
        "json_over_local_typed_ratio": round(proof_json_size / total, 6),
        "json_minus_local_typed_bytes": proof_json_size - total,
    }


def cli_summary():
    rows = []
    for index, expected in enumerate(gate.EXPECTED_ROLES):
        proof_json_size, local_accounting = accounting(index + 1)
        rows.append(
            {
                "path": str(gate.EVIDENCE_DIR / expected["path"]),
                "evidence_relative_path": expected["path"],
                "envelope_sha256": f"{index + 10:064x}"[-64:],
                "proof_sha256": f"{index + 20:064x}"[-64:],
                "proof_json_size_bytes": proof_json_size,
                "envelope_metadata": {
                    "proof_backend": "stwo",
                    "proof_backend_version": expected["proof_backend_version"],
                    "statement_version": expected["statement_version"],
                    "verifier_domain": expected["verifier_domain"],
                    "proof_schema_version": expected["proof_schema_version"],
                    "target_id": expected["target_id"],
                },
                "local_binary_accounting": local_accounting,
            }
        )
    return {
        "schema": gate.CLI_SCHEMA,
        "accounting_domain": gate.ACCOUNTING_DOMAIN,
        "accounting_format_version": gate.ACCOUNTING_FORMAT_VERSION,
        "accounting_source": "fixture",
        "upstream_stwo_serialization_status": gate.UPSTREAM_SERIALIZATION_STATUS,
        "proof_payload_kind": gate.PROOF_PAYLOAD_KIND,
        "safety": {"path_policy": "fixture"},
        "size_constants": {
            "base_field_bytes": 4,
            "secure_field_bytes": 16,
            "blake2s_hash_bytes": 32,
            "proof_of_work_bytes": 8,
            "pcs_config_bytes": 4,
        },
        "rows": rows,
    }


class BinaryTypedProofAccountingGateTests(unittest.TestCase):
    def assert_rejects(self, payload, summary, message):
        with self.assertRaises(gate.BinaryTypedProofAccountingGateError) as ctx:
            gate.validate_payload(payload, summary, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def test_build_payload_records_d32_local_accounting_boundary(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)

        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["accounting_status"], gate.ACCOUNTING_STATUS)
        self.assertEqual(payload["binary_serialization_status"], gate.BINARY_SERIALIZATION_STATUS)
        self.assertEqual(payload["profile_rows"][0]["role"], "source_arithmetic")
        self.assertEqual(payload["profile_rows"][1]["role"], "logup_sidecar")
        self.assertEqual(payload["profile_rows"][2]["role"], "fused")
        self.assertEqual(payload["aggregate"]["profiles_checked"], 3)
        self.assertEqual(payload["mutations_checked"], len(gate.MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertTrue(payload["payload_commitment"].startswith("blake2b-256:"))

    def test_individual_mutations_reject(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        base = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            base.pop(key)
        for name in gate.MUTATION_NAMES:
            mutated = gate.mutate_payload(base, name)
            with self.assertRaises(gate.BinaryTypedProofAccountingGateError, msg=name):
                gate.validate_payload(mutated, summary, allow_missing_mutation_summary=True)

    def test_rejects_bool_encoded_metric(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_rows"][0]["local_binary_accounting"]["records"][0]["item_count"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "item_count must be an integer")

    def test_rejects_cli_schema_drift(self):
        summary = cli_summary()
        summary["schema"] = "wrong"
        with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "CLI schema drift"):
            gate.validate_cli_summary(summary)

    def test_tsv_contains_rows_and_commitments(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        tsv = gate.to_tsv(payload)
        self.assertIn("source_arithmetic", tsv)
        self.assertIn("logup_sidecar", tsv)
        self.assertIn("fused", tsv)
        self.assertIn("record_stream_sha256", tsv)

    def test_rejects_output_path_outside_evidence_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "escapes evidence dir"):
                gate.validate_output_path(pathlib.Path(tmp) / "bad.json")

    def test_write_json_validates_before_writing(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["decision"] = "bad"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        out = gate.EVIDENCE_DIR / "tmp-binary-typed-proof-accounting-test.json"
        try:
            with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "decision drift"):
                gate.write_json(payload, summary, out)
            self.assertFalse(out.exists())
        finally:
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
