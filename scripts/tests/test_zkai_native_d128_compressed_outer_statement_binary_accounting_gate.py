import copy
import hashlib
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from scripts import zkai_native_d128_compressed_outer_statement_binary_accounting_gate as gate


ACTUAL_COUNTS = {
    "pcs.commitments": 3,
    "pcs.trace_decommitments.hash_witness": 4,
    "pcs.sampled_values": 60,
    "pcs.queried_values": 120,
    "pcs.fri.first_layer.fri_witness": 2,
    "pcs.fri.inner_layers.fri_witness": 0,
    "pcs.fri.last_layer_poly": 1,
    "pcs.fri.first_layer.commitment": 1,
    "pcs.fri.inner_layers.commitments": 0,
    "pcs.fri.first_layer.decommitment.hash_witness": 0,
    "pcs.fri.inner_layers.decommitment.hash_witness": 0,
    "pcs.proof_of_work": 1,
    "pcs.config": 1,
}


def record(path):
    spec = gate.accounting_base.EXPECTED_RECORD_SPECS[path]
    size = gate.EXPECTED_SIZE_CONSTANTS[spec["size_constant_key"]]
    count = ACTUAL_COUNTS[path]
    return {
        "path": path,
        "scalar_kind": spec["scalar_kind"],
        "item_count": count,
        "item_size_bytes": size,
        "total_bytes": count * size,
    }


def local_accounting():
    records = [record(path) for path in gate.EXPECTED_RECORD_PATHS]
    total = sum(item["total_bytes"] for item in records)
    grouped = gate.accounting_base.grouped_accounting_from_records(records)
    record_stream = gate.accounting_base.canonical_record_stream(records)
    return {
        "format_domain": gate.ACCOUNTING_DOMAIN,
        "format_version": gate.ACCOUNTING_FORMAT_VERSION,
        "upstream_stwo_serialization_status": gate.UPSTREAM_SERIALIZATION_STATUS,
        "records": records,
        "record_count": len(records),
        "component_sum_bytes": total,
        "typed_size_estimate_bytes": total,
        "grouped_reconstruction": copy.deepcopy(grouped),
        "stwo_grouped_breakdown": copy.deepcopy(grouped),
        "record_stream_bytes": len(record_stream),
        "record_stream_sha256": hashlib.sha256(record_stream).hexdigest(),
        "json_over_local_typed_ratio": gate.rounded_ratio(3516, total),
        "json_minus_local_typed_bytes": 3516 - total,
    }


def cli_summary():
    return {
        "schema": gate.CLI_SCHEMA,
        "accounting_domain": gate.ACCOUNTING_DOMAIN,
        "accounting_format_version": gate.ACCOUNTING_FORMAT_VERSION,
        "accounting_source": "fixture",
        "upstream_stwo_serialization_status": gate.UPSTREAM_SERIALIZATION_STATUS,
        "proof_payload_kind": gate.PROOF_PAYLOAD_KIND,
        "safety": dict(gate.EXPECTED_SAFETY),
        "size_constants": dict(gate.EXPECTED_SIZE_CONSTANTS),
        "rows": [
            {
                "path": str(gate.EVIDENCE_DIR / gate.EXPECTED_ROLE["path"]),
                "evidence_relative_path": gate.EXPECTED_ROLE["path"],
                "envelope_sha256": "07" * 32,
                "proof_sha256": "99" * 32,
                "proof_json_size_bytes": 3516,
                "envelope_metadata": {
                    "proof_backend": "stwo",
                    "proof_backend_version": gate.EXPECTED_ROLE["proof_backend_version"],
                    "statement_version": gate.EXPECTED_ROLE["statement_version"],
                    "verifier_domain": gate.EXPECTED_ROLE["verifier_domain"],
                    "proof_schema_version": gate.EXPECTED_ROLE["proof_schema_version"],
                    "target_id": gate.EXPECTED_ROLE["target_id"],
                },
                "local_binary_accounting": local_accounting(),
            }
        ],
    }


class NativeD128CompressedBinaryAccountingGateTests(unittest.TestCase):
    def assert_rejects(self, payload, summary, message):
        with self.assertRaises(gate.BinaryTypedProofAccountingGateError) as ctx:
            gate.validate_payload(payload, summary, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def test_build_payload_records_compressed_d128_accounting_boundary(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)

        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["comparison_status"], gate.COMPARISON_STATUS)
        self.assertEqual(payload["profile_row"]["role"], "compressed_outer_statement")
        self.assertEqual(payload["aggregate"]["proof_json_size_bytes"], 3516)
        self.assertEqual(payload["aggregate"]["local_typed_bytes"], 1792)
        self.assertEqual(payload["aggregate"]["json_ratio_vs_nanozk_paper_row"], 0.509565)
        self.assertEqual(payload["aggregate"]["typed_ratio_vs_nanozk_paper_row"], 0.25971)
        self.assertEqual(payload["mutations_checked"], len(gate.MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

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

    def test_rejects_bool_encoded_metrics(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_row"]["proof_json_size_bytes"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "proof_json_size_bytes drift")

        payload = gate.build_payload(summary)
        payload["profile_row"]["local_binary_accounting"]["records"][0]["item_count"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "item_count must be an integer")

    def test_rejects_record_stream_digest_drift(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_row"]["local_binary_accounting"]["record_stream_sha256"] = "11" * 32
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "record stream sha256 drift")

    def test_rejects_nanozk_baseline_drift(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["nanozk_paper_reported_d128_block_proof_bytes"] = 3_000
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "nanozk_paper_reported_d128_block_proof_bytes drift")

    def test_rejects_cli_summary_drift(self):
        summary = cli_summary()
        summary["rows"][0]["envelope_metadata"]["statement_version"] += "-mutated"
        with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "statement_version drift"):
            gate.validate_cli_summary(summary)

    def test_run_binary_accounting_cli_rejects_timeout(self):
        with mock.patch("subprocess.run") as run:
            run.side_effect = gate.subprocess.TimeoutExpired(
                cmd=["cargo"],
                timeout=gate.BINARY_ACCOUNTING_TIMEOUT_SECONDS,
                output="partial stdout",
                stderr="partial stderr",
            )
            with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "timed out"):
                gate.run_binary_accounting_cli()

    def test_tsv_contains_ratios_and_commitments(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        tsv = gate.to_tsv(payload)
        self.assertIn("typed_ratio_vs_nanozk_paper_row", tsv)
        self.assertIn("compressed_outer_statement", tsv)
        self.assertIn("0.25971", tsv)

    def test_rejects_output_path_outside_evidence_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "escapes evidence dir"):
                gate.validate_output_path(pathlib.Path(tmp) / "bad.json")

    def test_relative_output_path_is_repo_root_anchored(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = pathlib.Path.cwd()
            try:
                os.chdir(tmp)
                path = gate.validate_output_path(
                    pathlib.Path(
                        "docs/engineering/evidence/"
                        "zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json"
                    )
                )
            finally:
                os.chdir(cwd)
        self.assertEqual(path, gate.JSON_OUT.resolve())

    def test_write_json_validates_before_writing(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["decision"] = "bad"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        out = gate.EVIDENCE_DIR / "tmp-d128-compressed-binary-accounting-test.json"
        try:
            with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "decision drift"):
                gate.write_json(payload, summary, out)
            self.assertFalse(out.exists())
        finally:
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
