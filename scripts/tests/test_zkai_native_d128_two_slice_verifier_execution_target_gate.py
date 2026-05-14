import copy
import pathlib
import tempfile
import unittest

from scripts import zkai_native_d128_two_slice_verifier_execution_target_gate as gate


def cli_row(role: str) -> dict:
    expected = gate.EXPECTED_ROWS[role]
    return {
        "path": str(gate.EVIDENCE_DIR / expected["path"]),
        "evidence_relative_path": expected["path"],
        "envelope_sha256": expected["envelope_sha256"],
        "proof_sha256": expected["proof_sha256"],
        "proof_json_size_bytes": expected["proof_json_size_bytes"],
        "envelope_metadata": {
            "proof_backend": "stwo",
            "proof_backend_version": expected["proof_backend_version"],
            "statement_version": expected["statement_version"],
            "verifier_domain": None,
            "proof_schema_version": None,
            "target_id": None,
        },
        "local_binary_accounting": {
            "typed_size_estimate_bytes": expected["local_typed_bytes"],
            "record_stream_bytes": expected["record_stream_bytes"],
            "record_stream_sha256": expected["record_stream_sha256"],
            "grouped_reconstruction": expected["grouped_reconstruction"],
        },
    }


def cli_summary() -> dict:
    return {
        "schema": "zkai-stwo-local-binary-proof-accounting-cli-v1",
        "rows": [
            cli_row("rmsnorm_public_rows_inner_stwo_proof"),
            cli_row("rmsnorm_projection_bridge_inner_stwo_proof"),
            cli_row("compressed_outer_statement_binding_proof"),
        ],
    }


class VerifierExecutionTargetGateTests(unittest.TestCase):
    def test_build_payload_validates(self) -> None:
        payload = gate.build_payload(cli_summary())
        gate.validate_payload(payload)
        self.assertEqual(payload["mutations_checked"], len(gate.MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["aggregate"]["selected_inner_local_typed_bytes"], 12688)
        self.assertEqual(payload["aggregate"]["inner_typed_over_outer_statement_typed_ratio"], 7.080357)

    def test_rejects_cli_path_drift(self) -> None:
        summary = cli_summary()
        summary["rows"][0]["evidence_relative_path"] = "tampered.json"
        with self.assertRaisesRegex(gate.VerifierExecutionTargetGateError, "path drift|binary accounting"):
            gate.build_payload(summary)

    def test_rejects_cli_typed_byte_drift(self) -> None:
        summary = cli_summary()
        summary["rows"][1]["local_binary_accounting"]["typed_size_estimate_bytes"] += 1
        with self.assertRaisesRegex(gate.VerifierExecutionTargetGateError, "local_typed_bytes drift"):
            gate.build_payload(summary)

    def test_rejects_outer_promotion(self) -> None:
        payload = gate.build_payload(cli_summary())
        mutated = copy.deepcopy(payload)
        mutated["proof_objects"][2]["object_class"] = "native_outer_verifier_execution_proof"
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(gate.VerifierExecutionTargetGateError, "object_class drift"):
            gate.validate_payload(mutated)

    def test_rejects_unpinned_row_field_drift(self) -> None:
        payload = gate.build_payload(cli_summary())
        mutated = copy.deepcopy(payload)
        mutated["proof_objects"][2]["native_verifier_execution_status"] = "native_outer_verifier_execution_ready"
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(
            gate.VerifierExecutionTargetGateError, "native_verifier_execution_status drift"
        ):
            gate.validate_payload(mutated)

    def test_rejects_partial_mutation_summary(self) -> None:
        payload = gate.build_payload(cli_summary())
        del payload["mutation_cases"]
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.VerifierExecutionTargetGateError, "partial mutation summary"):
            gate.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_tsv_contains_three_rows(self) -> None:
        payload = gate.build_payload(cli_summary())
        tsv = gate.to_tsv(payload)
        self.assertEqual(len(tsv.strip().splitlines()), 4)
        self.assertIn("rmsnorm_public_rows_inner_stwo_proof", tsv)
        self.assertIn("compressed_outer_statement_binding_proof", tsv)

    def test_output_path_rejects_escape(self) -> None:
        with self.assertRaisesRegex(gate.VerifierExecutionTargetGateError, "under evidence dir|escapes repository"):
            gate.validate_output_path(pathlib.Path(tempfile.gettempdir()) / "outside.json")

    def test_atomic_write_roundtrip_under_evidence_dir(self) -> None:
        payload = gate.build_payload(cli_summary())
        out = gate.EVIDENCE_DIR / ".tmp-verifier-execution-target-test.json"
        try:
            gate.write_json(out, payload)
            self.assertTrue(out.exists())
            loaded, _ = gate.load_json(out)
            gate.validate_payload(loaded)
        finally:
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
