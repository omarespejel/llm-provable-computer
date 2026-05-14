import copy
import hashlib
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import zkai_d128_component_native_two_slice_reprove_gate as gate


ACTUAL_COUNTS = {
    "pcs.commitments": 3,
    "pcs.trace_decommitments.hash_witness": 54,
    "pcs.sampled_values": 184,
    "pcs.queried_values": 552,
    "pcs.fri.first_layer.fri_witness": 3,
    "pcs.fri.inner_layers.fri_witness": 15,
    "pcs.fri.last_layer_poly": 1,
    "pcs.fri.first_layer.commitment": 1,
    "pcs.fri.inner_layers.commitments": 6,
    "pcs.fri.first_layer.decommitment.hash_witness": 15,
    "pcs.fri.inner_layers.decommitment.hash_witness": 32,
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
        "json_over_local_typed_ratio": gate.rounded_ratio(gate.EXPECTED_PROOF_JSON_BYTES, total),
        "json_minus_local_typed_bytes": gate.EXPECTED_PROOF_JSON_BYTES - total,
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
                "path": str(gate.ENVELOPE_PATH),
                "evidence_relative_path": gate.EXPECTED_ROLE["path"],
                "envelope_sha256": "07" * 32,
                "proof_sha256": "99" * 32,
                "proof_json_size_bytes": gate.EXPECTED_PROOF_JSON_BYTES,
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


def prior_budget():
    return {
        "schema": gate.EXPECTED_PRIOR_BUDGET_DESCRIPTOR["schema"],
        "decision": gate.EXPECTED_PRIOR_BUDGET_DESCRIPTOR["decision"],
        "payload_commitment": gate.EXPECTED_PRIOR_BUDGET_DESCRIPTOR["payload_commitment"],
        "compression_budget": {
            "current_verifier_target_typed_bytes": gate.PREVIOUS_TARGET_TYPED_BYTES,
            "current_verifier_target_json_bytes": gate.PREVIOUS_TARGET_JSON_BYTES,
            "nanozk_paper_reported_d128_block_proof_bytes": gate.NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        },
    }


def prior_descriptor():
    return dict(gate.EXPECTED_PRIOR_BUDGET_DESCRIPTOR)


def evidence_counts():
    with gate.JSON_OUT.open(encoding="utf-8") as handle:
        payload = gate.json.load(handle)
    records = payload["profile_row"]["local_binary_accounting"]["records"]
    return {record["path"]: record["item_count"] for record in records}


class D128ComponentNativeTwoSliceReproveGateTests(unittest.TestCase):
    def assert_rejects(self, payload, summary, budget, descriptor, message):
        with self.assertRaises(gate.ComponentNativeReproveGateError) as ctx:
            gate.validate_payload(
                payload,
                summary,
                budget,
                descriptor,
                allow_missing_mutation_summary=True,
            )
        self.assertIn(message, str(ctx.exception))

    def test_build_payload_records_real_reduction_without_overclaim(self):
        summary = cli_summary()
        budget = prior_budget()
        descriptor = prior_descriptor()
        payload = gate.build_payload(summary, budget, descriptor)

        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertEqual(payload["aggregate"]["local_typed_bytes"], 9_056)
        self.assertEqual(payload["aggregate"]["proof_json_size_bytes"], 22_139)
        self.assertEqual(payload["aggregate"]["typed_saving_vs_previous_target_bytes"], 3_632)
        self.assertEqual(payload["aggregate"]["typed_saving_ratio_vs_previous_target"], 0.286255)
        self.assertEqual(payload["aggregate"]["typed_gap_closed_vs_prior_budget"], 0.627505)
        self.assertEqual(payload["aggregate"]["typed_remaining_gap_to_nanozk_paper_row_bytes"], 2_156)
        self.assertEqual(payload["aggregate"]["typed_ratio_vs_nanozk_paper_row"], 1.312464)
        self.assertIn("not a NANOZK proof-size win", payload["non_claims"])
        self.assertEqual(payload["mutations_checked"], len(gate.MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_fixture_counts_match_checked_evidence(self):
        observed = evidence_counts()
        self.assertEqual(
            observed,
            ACTUAL_COUNTS,
            f"component-native reprove accounting counts drifted: expected {ACTUAL_COUNTS}, observed {observed}",
        )

    def test_individual_mutations_reject(self):
        summary = cli_summary()
        budget = prior_budget()
        descriptor = prior_descriptor()
        payload = gate.build_payload(summary, budget, descriptor)
        base = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            base.pop(key)
        for name in gate.MUTATION_NAMES:
            mutated = gate.mutate_payload(base, name)
            with self.assertRaises(gate.ComponentNativeReproveGateError, msg=name):
                gate.validate_payload(mutated, summary, budget, descriptor, allow_missing_mutation_summary=True)

    def test_rejects_bool_encoded_metrics(self):
        summary = cli_summary()
        budget = prior_budget()
        descriptor = prior_descriptor()
        payload = gate.build_payload(summary, budget, descriptor)
        payload["profile_row"]["proof_json_size_bytes"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, budget, descriptor, "profile row drift")

        payload = gate.build_payload(summary, budget, descriptor)
        payload["profile_row"]["local_binary_accounting"]["records"][0]["item_count"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, budget, descriptor, "item_count must be an integer")

    def test_tsv_contains_single_component_native_row(self):
        payload = gate.build_payload(cli_summary(), prior_budget(), prior_descriptor())
        tsv = gate.to_tsv(payload)
        self.assertEqual(len(tsv.strip().splitlines()), 2)
        self.assertIn("component_native_two_slice_reprove", tsv)
        self.assertIn("0.713745", tsv)
        self.assertIn("1.312464", tsv)

    def test_run_binary_accounting_cli_rejects_timeout(self):
        with mock.patch("subprocess.run") as run:
            run.side_effect = subprocess.TimeoutExpired(["cargo"], gate.BINARY_ACCOUNTING_TIMEOUT_SECONDS)
            with self.assertRaisesRegex(gate.ComponentNativeReproveGateError, "timed out"):
                gate.run_binary_accounting_cli()

    def test_output_path_rejects_escape(self):
        with self.assertRaisesRegex(
            gate.ComponentNativeReproveGateError,
            "under evidence dir|escapes repository|under repo root",
        ):
            gate.validate_output_path(pathlib.Path(tempfile.gettempdir()) / "outside.json")

    def test_output_path_rejects_symlink_parent(self):
        link = gate.EVIDENCE_DIR / ".tmp-component-reprove-symlink-parent"
        with tempfile.TemporaryDirectory() as target:
            try:
                link.symlink_to(target, target_is_directory=True)
                with self.assertRaisesRegex(gate.ComponentNativeReproveGateError, "component must not be a symlink"):
                    gate.validate_output_path(link / "out.json")
            finally:
                link.unlink(missing_ok=True)

    def test_output_path_rejects_missing_parent(self):
        out = gate.EVIDENCE_DIR / ".tmp-component-reprove-missing-parent" / "out.json"
        with self.assertRaisesRegex(gate.ComponentNativeReproveGateError, "output parent must be an existing directory"):
            gate.validate_output_path(out)

    def test_output_path_rejects_file_parent(self):
        parent = gate.EVIDENCE_DIR / ".tmp-component-reprove-file-parent"
        try:
            parent.write_text("not a directory", encoding="utf-8")
            with self.assertRaisesRegex(
                gate.ComponentNativeReproveGateError,
                "output parent must be an existing directory",
            ):
                gate.validate_output_path(parent / "out.json")
        finally:
            parent.unlink(missing_ok=True)

    def test_output_path_rejects_directory(self):
        out = gate.EVIDENCE_DIR / ".tmp-component-reprove-output-dir"
        try:
            out.mkdir(exist_ok=True)
            with self.assertRaisesRegex(gate.ComponentNativeReproveGateError, "output path must be a file"):
                gate.validate_output_path(out)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_atomic_write_roundtrip_under_evidence_dir(self):
        summary = cli_summary()
        budget = prior_budget()
        descriptor = prior_descriptor()
        payload = gate.build_payload(summary, budget, descriptor)
        out = gate.EVIDENCE_DIR / ".tmp-component-reprove-gate-test.json"
        try:
            gate.write_json(out, payload, summary, budget, descriptor)
            self.assertTrue(out.exists())
            loaded, _ = gate.load_json(out)
            gate.validate_payload(loaded, summary, budget, descriptor)
        finally:
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
