import copy
import hashlib
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_stwo_binary_typed_proof_accounting_gate as gate


def record(path, count):
    spec = gate.EXPECTED_RECORD_SPECS[path]
    size = gate.EXPECTED_SIZE_CONSTANTS[spec["size_constant_key"]]
    return {
        "path": path,
        "scalar_kind": spec["scalar_kind"],
        "item_count": count,
        "item_size_bytes": size,
        "total_bytes": count * size,
    }


def accounting(seed):
    records = [record(path, seed + index + 1) for index, path in enumerate(gate.EXPECTED_RECORD_PATHS)]
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
    record_stream = gate.canonical_record_stream(records)
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
        "record_stream_bytes": len(record_stream),
        "record_stream_sha256": hashlib.sha256(record_stream).hexdigest(),
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
        "safety": dict(gate.EXPECTED_SAFETY),
        "size_constants": dict(gate.EXPECTED_SIZE_CONSTANTS),
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

    def test_rejects_float_encoded_local_accounting_metrics(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_rows"][0]["local_binary_accounting"]["record_count"] = 1.5
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "record_count must be an integer")

        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_rows"][0]["local_binary_accounting"]["typed_size_estimate_bytes"] = 1.5
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "typed_size_estimate_bytes must be an integer")

    def test_rejects_non_hex_record_stream_digest(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_rows"][0]["local_binary_accounting"]["record_stream_sha256"] = "z" * 64
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "record_stream_sha256 digest invalid")

    def test_rejects_record_stream_digest_drift(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_rows"][0]["local_binary_accounting"]["record_stream_sha256"] = "11" * 32
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "record stream sha256 drift")

    def test_rejects_record_stream_byte_count_drift(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_rows"][0]["local_binary_accounting"]["record_stream_bytes"] += 1
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "record stream bytes drift")

    def test_rejects_grouped_bytes_not_derived_from_records(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        accounting = payload["profile_rows"][0]["local_binary_accounting"]
        accounting["grouped_reconstruction"]["fri_samples"] += 16
        accounting["stwo_grouped_breakdown"]["fri_samples"] += 16
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "grouped_reconstruction drift")

    def test_rejects_non_hex_cli_row_digests(self):
        summary = cli_summary()
        summary["rows"][0]["envelope_sha256"] = "z" * 64
        with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "envelope_sha256 digest invalid"):
            gate.validate_cli_summary(summary)

        summary = cli_summary()
        summary["rows"][0]["proof_sha256"] = "z" * 64
        with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "proof_sha256 digest invalid"):
            gate.validate_cli_summary(summary)

    def test_rejects_scalar_kind_and_size_drift(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_rows"][0]["local_binary_accounting"]["records"][0]["scalar_kind"] = "fixture_scalar"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "scalar_kind drift")

        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["profile_rows"][0]["local_binary_accounting"]["records"][0]["item_size_bytes"] += 1
        payload["profile_rows"][0]["local_binary_accounting"]["records"][0]["total_bytes"] += payload["profile_rows"][0][
            "local_binary_accounting"
        ]["records"][0]["item_count"]
        payload["payload_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, summary, "item_size_bytes drift")

    def test_rejects_cli_schema_drift(self):
        summary = cli_summary()
        summary["schema"] = "wrong"
        with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "CLI schema drift"):
            gate.validate_cli_summary(summary)

    def test_rejects_cli_size_constant_and_safety_drift(self):
        summary = cli_summary()
        summary["size_constants"]["pcs_config_bytes"] += 1
        with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "size constant pcs_config_bytes drift"):
            gate.validate_cli_summary(summary)

        summary = cli_summary()
        summary["safety"]["path_policy"] = "fixture"
        with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "safety path_policy drift"):
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

    def test_relative_output_path_is_repo_root_anchored(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = pathlib.Path.cwd()
            try:
                os.chdir(tmp)
                path = gate.validate_output_path(
                    pathlib.Path(
                        "docs/engineering/evidence/"
                        "zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json"
                    )
                )
            finally:
                os.chdir(cwd)
        self.assertEqual(path, gate.JSON_OUT.resolve())

    def test_rejects_evidence_directory_as_output_path(self):
        with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "must be a file"):
            gate.validate_output_path(gate.EVIDENCE_DIR)

    def symlink_or_skip(self, link: pathlib.Path, target: pathlib.Path) -> None:
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

    @unittest.skipUnless(hasattr(pathlib.Path, "symlink_to"), "symlinks unavailable")
    def test_rejects_output_path_symlink_before_resolve(self):
        target = gate.EVIDENCE_DIR / "tmp-binary-typed-proof-accounting-target.json"
        link = gate.EVIDENCE_DIR / "tmp-binary-typed-proof-accounting-link.json"
        try:
            target.write_text("{}", encoding="utf-8")
            self.symlink_or_skip(link, target)
            with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "must not be a symlink"):
                gate.validate_output_path(link)
        finally:
            link.unlink(missing_ok=True)
            target.unlink(missing_ok=True)

    @unittest.skipUnless(hasattr(pathlib.Path, "symlink_to"), "symlinks unavailable")
    def test_rejects_dangling_output_path_symlink(self):
        target = gate.EVIDENCE_DIR / "tmp-binary-typed-proof-accounting-missing-target.json"
        link = gate.EVIDENCE_DIR / "tmp-binary-typed-proof-accounting-dangling-link.json"
        try:
            target.unlink(missing_ok=True)
            self.symlink_or_skip(link, target)
            self.assertFalse(link.exists())
            self.assertTrue(link.is_symlink())
            with self.assertRaisesRegex(gate.BinaryTypedProofAccountingGateError, "must not be a symlink"):
                gate.validate_output_path(link)
        finally:
            link.unlink(missing_ok=True)
            target.unlink(missing_ok=True)

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
