import copy
import hashlib
import unittest

from scripts import zkai_d128_component_compact_preprocessed_reprove_gate as gate


def record(path, count):
    spec = gate.accounting_base.EXPECTED_RECORD_SPECS[path]
    size = gate.EXPECTED_SIZE_CONSTANTS[spec["size_constant_key"]]
    return {
        "path": path,
        "scalar_kind": spec["scalar_kind"],
        "item_count": count,
        "item_size_bytes": size,
        "total_bytes": count * size,
    }


def local_accounting(counts, proof_json):
    records = [record(path, counts[path]) for path in gate.EXPECTED_RECORD_PATHS]
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
        "json_over_local_typed_ratio": gate.rounded_ratio(proof_json, total),
        "json_minus_local_typed_bytes": proof_json - total,
    }


def cli_row(role, counts, json_bytes):
    return {
        "path": str(gate.EVIDENCE_DIR / role["path"]),
        "evidence_relative_path": role["path"],
        "envelope_sha256": "11" * 32,
        "proof_sha256": "22" * 32,
        "proof_json_size_bytes": json_bytes,
        "envelope_metadata": {
            "proof_backend": "stwo",
            "proof_backend_version": role["proof_backend_version"],
            "statement_version": role["statement_version"],
            "verifier_domain": role["verifier_domain"],
            "proof_schema_version": role["proof_schema_version"],
            "target_id": role["target_id"],
        },
        "local_binary_accounting": local_accounting(counts, json_bytes),
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
            cli_row(
                gate.EXPECTED_COMPACT_ROLE,
                gate.EXPECTED_COMPACT_RECORD_COUNTS,
                gate.COMPACT_PROOF_JSON_BYTES,
            ),
            cli_row(
                gate.EXPECTED_BASELINE_ROLE,
                gate.EXPECTED_BASELINE_RECORD_COUNTS,
                gate.BASELINE_COMPONENT_JSON_BYTES,
            ),
        ],
    }


def prior_budget():
    return {
        "compression_budget": {
            "current_verifier_target_typed_bytes": gate.PREVIOUS_TARGET_TYPED_BYTES,
            "current_verifier_target_json_bytes": gate.PREVIOUS_TARGET_JSON_BYTES,
            "nanozk_paper_reported_d128_block_proof_bytes": gate.NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
            "typed_bytes_to_remove_to_equal_nanozk": gate.PREVIOUS_TARGET_GAP_TO_NANOZK_TYPED_BYTES,
        }
    }


def build_payload(summary=None, budget=None, **kwargs):
    return gate.build_payload(
        cli_summary() if summary is None else summary,
        prior_budget() if budget is None else budget,
        compact_envelope_size_bytes=kwargs.pop(
            "compact_envelope_size_bytes", gate.COMPACT_ENVELOPE_BYTES
        ),
        **kwargs,
    )


class D128CompactPreprocessedReproveGateTests(unittest.TestCase):
    def test_build_payload_records_below_nanozk_signal_without_overclaim(self):
        payload = build_payload()

        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertEqual(payload["aggregate"]["compact_local_typed_bytes"], 6_264)
        self.assertEqual(payload["aggregate"]["typed_saving_vs_component_baseline_bytes"], 2_792)
        self.assertEqual(payload["aggregate"]["typed_saving_ratio_vs_component_baseline"], 0.308304)
        self.assertEqual(payload["aggregate"]["typed_ratio_vs_nanozk_paper_row"], 0.907826)
        self.assertEqual(payload["aggregate"]["typed_saving_vs_nanozk_paper_row_bytes"], 636)
        self.assertEqual(
            payload["aggregate"]["comparison_status"],
            "below_nanozk_reported_row_under_local_typed_accounting_not_matched_benchmark",
        )
        self.assertIn("not a matched NANOZK benchmark", payload["non_claims"])
        self.assertEqual(payload["mutations_checked"], len(gate.MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_individual_mutations_reject(self):
        summary = cli_summary()
        budget = prior_budget()
        payload = build_payload(summary, budget, include_mutations=False)
        for name in gate.MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.CompactPreprocessedGateError, msg=name):
                gate.validate_payload(mutated, summary, budget, allow_missing_mutation_summary=True)

    def test_rejects_record_count_drift(self):
        summary = cli_summary()
        summary["rows"][0]["local_binary_accounting"]["records"][2]["item_count"] -= 1
        with self.assertRaisesRegex(gate.CompactPreprocessedGateError, "compact record counts drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_duplicate_or_unexpected_accounting_rows(self):
        summary = cli_summary()
        summary["rows"].append(copy.deepcopy(summary["rows"][0]))
        with self.assertRaisesRegex(gate.CompactPreprocessedGateError, "duplicate accounting row"):
            build_payload(summary, include_mutations=False)

        summary = cli_summary()
        extra = copy.deepcopy(summary["rows"][0])
        extra["evidence_relative_path"] = "unexpected-envelope.json"
        summary["rows"].append(extra)
        with self.assertRaisesRegex(gate.CompactPreprocessedGateError, "accounting row set drift"):
            build_payload(summary, include_mutations=False)

    def test_rejects_envelope_size_drift(self):
        with self.assertRaisesRegex(gate.CompactPreprocessedGateError, "compact envelope JSON size drift"):
            build_payload(
                include_mutations=False,
                compact_envelope_size_bytes=gate.COMPACT_ENVELOPE_BYTES + 1,
            )

    def test_rejects_bool_encoded_metrics(self):
        summary = cli_summary()
        payload = build_payload(summary, include_mutations=False)
        payload["aggregate"]["compact_local_typed_bytes"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaises(gate.CompactPreprocessedGateError):
            gate.validate_payload(payload, summary, prior_budget(), allow_missing_mutation_summary=True)

    def test_rejects_mutation_case_content_tamper(self):
        summary = cli_summary()
        budget = prior_budget()
        payload = build_payload(summary, budget)
        payload["mutation_cases"][0]["error"] = "tampered while counts stay fixed"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.CompactPreprocessedGateError, "mutation case evidence drift"):
            gate.validate_payload(payload, summary, budget)


if __name__ == "__main__":
    unittest.main()
