import copy
import pathlib
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_stwo_median_timing_gate as gate


def row(expected, seed):
    runs = [seed + 5, seed + 1, seed + 3, seed + 2, seed + 4]
    proof_size = 10_000 + seed
    envelope_size = proof_size + 1_000
    return {
        "profile_id": expected["profile_id"],
        "axis_role": expected["axis_role"],
        "key_width": expected["key_width"],
        "value_width": expected["value_width"],
        "head_count": expected["head_count"],
        "steps_per_head": expected["steps_per_head"],
        "role": expected["role"],
        "evidence_relative_path": expected["evidence_relative_path"],
        "envelope_sha256": f"{seed:064x}"[-64:],
        "proof_backend": "stwo",
        "proof_backend_version": f"{expected['profile_id']}-{expected['role']}-proof-v1",
        "statement_version": f"{expected['profile_id']}-{expected['role']}-statement-v1",
        "proof_schema_version": None if expected["role"] != "fused" else f"{expected['profile_id']}-schema-v1",
        "target_id": None if expected["role"] == "source_arithmetic" else f"{expected['profile_id']}-{expected['role']}",
        "verifier_domain": None if expected["role"] == "source_arithmetic" else f"ptvm:{expected['profile_id']}:{expected['role']}",
        "proof_size_bytes": proof_size,
        "envelope_size_bytes": envelope_size,
        "verify_runs_us": runs,
        "verify_median_us": sorted(runs)[len(runs) // 2],
        "verify_min_us": min(runs),
        "verify_max_us": max(runs),
        "verified": True,
    }


def profile_summary(rows):
    source, sidecar, fused = rows
    source_plus_sidecar = source["verify_median_us"] + sidecar["verify_median_us"]
    fused_median = fused["verify_median_us"]
    return {
        "profile_id": source["profile_id"],
        "axis_role": source["axis_role"],
        "key_width": source["key_width"],
        "value_width": source["value_width"],
        "head_count": source["head_count"],
        "steps_per_head": source["steps_per_head"],
        "source_plus_sidecar_verify_median_us": source_plus_sidecar,
        "fused_verify_median_us": fused_median,
        "fused_minus_source_plus_sidecar_verify_median_us": fused_median - source_plus_sidecar,
        "fused_to_source_plus_sidecar_verify_median_ratio": gate.round6(fused_median / source_plus_sidecar),
        "timing_status": gate.MEASUREMENT_STATUS,
    }


def cli_summary():
    rows = [row(expected, index + 10) for index, expected in enumerate(gate.EXPECTED_ROWS)]
    return {
        "schema": gate.CLI_SCHEMA,
        "decision": gate.DECISION,
        "route_family": gate.ROUTE_FAMILY,
        "timing_policy": gate.TIMING_POLICY,
        "timing_scope": gate.TIMING_SCOPE,
        "claim_boundary": gate.CLAIM_BOUNDARY,
        "runs_per_envelope": gate.RUNS_PER_ENVELOPE,
        "clock": "std_time_instant_elapsed_as_micros",
        "safety": dict(gate.EXPECTED_SAFETY),
        "non_claims": list(gate.NON_CLAIMS),
        "validation_commands": list(gate.VALIDATION_COMMANDS[:4]),
        "rows": rows,
        "profile_summaries": [profile_summary(chunk) for chunk in gate.chunks(rows, 3)],
    }


class StwoMedianTimingGateTests(unittest.TestCase):
    def assert_rejects(self, payload, summary, message):
        with self.assertRaises(gate.StwoMedianTimingGateError) as ctx:
            gate.validate_payload(payload, summary, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def test_build_payload_records_engineering_timing_boundary(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)

        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["timing_policy"], gate.TIMING_POLICY)
        self.assertEqual(payload["measurement_status"], gate.MEASUREMENT_STATUS)
        self.assertEqual(payload["aggregate"]["profiles_checked"], len(gate.EXPECTED_PROFILE_IDS))
        self.assertEqual(payload["aggregate"]["route_rows_checked"], len(gate.EXPECTED_ROWS))
        self.assertEqual(payload["aggregate"]["verifier_runs_captured"], len(gate.EXPECTED_ROWS) * 5)
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
            with self.assertRaises(gate.StwoMedianTimingGateError, msg=name):
                gate.validate_payload(mutated, summary, allow_missing_mutation_summary=True)

    def test_rejects_route_order_and_role_drift(self):
        summary = cli_summary()
        summary["rows"] = [summary["rows"][1], summary["rows"][0], *summary["rows"][2:]]
        with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "profile_id drift|role drift"):
            gate.validate_cli_summary(summary)

        summary = cli_summary()
        summary["rows"][0]["role"] = "fused"
        with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "role drift"):
            gate.validate_cli_summary(summary)

    def test_rejects_bool_float_and_digest_drift(self):
        summary = cli_summary()
        summary["rows"][0]["verify_median_us"] = True
        with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "verify_median_us must be an integer"):
            gate.validate_cli_summary(summary)

        summary = cli_summary()
        summary["profile_summaries"][0]["fused_to_source_plus_sidecar_verify_median_ratio"] = 1
        with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "fused ratio must be a float"):
            gate.validate_cli_summary(summary)

        summary = cli_summary()
        summary["rows"][0]["envelope_sha256"] = "z" * 64
        with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "envelope_sha256 digest invalid"):
            gate.validate_cli_summary(summary)

    def test_rejects_median_and_run_count_drift(self):
        summary = cli_summary()
        summary["rows"][0]["verify_runs_us"] = [1, 2, 3, 4]
        with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "verify run count drift"):
            gate.validate_cli_summary(summary)

        summary = cli_summary()
        summary["rows"][0]["verify_median_us"] += 1
        with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "verify median drift"):
            gate.validate_cli_summary(summary)

    def test_run_timing_cli_rejects_timeout(self):
        with mock.patch("subprocess.run") as run:
            run.side_effect = gate.subprocess.TimeoutExpired(
                cmd=["cargo"],
                timeout=gate.TIMING_CLI_TIMEOUT_SECONDS,
                output="partial stdout",
                stderr="partial stderr",
            )
            with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "timed out"):
                gate.run_timing_cli()

    def test_tsv_contains_rows_and_profile_metrics(self):
        payload = gate.build_payload(cli_summary())
        tsv = gate.to_tsv(payload)
        self.assertIn("d8_single_head_seq8", tsv)
        self.assertIn("source_plus_sidecar_verify_median_us", tsv)
        self.assertIn("fused_to_source_plus_sidecar_verify_median_ratio", tsv)

    def test_rejects_output_path_outside_evidence_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "escapes evidence dir"):
                gate.validate_output_path(pathlib.Path(tmp) / "bad.json")

    @unittest.skipUnless(hasattr(pathlib.Path, "symlink_to"), "symlinks unavailable")
    def test_rejects_output_path_symlink_before_resolve(self):
        target = gate.EVIDENCE_DIR / "tmp-stwo-median-timing-target.json"
        link = gate.EVIDENCE_DIR / "tmp-stwo-median-timing-link.json"
        try:
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "must not be a symlink"):
                gate.validate_output_path(link)
        finally:
            link.unlink(missing_ok=True)
            target.unlink(missing_ok=True)

    def test_write_json_validates_before_writing(self):
        summary = cli_summary()
        payload = gate.build_payload(summary)
        payload["decision"] = "bad"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        out = gate.EVIDENCE_DIR / "tmp-stwo-median-timing-test.json"
        try:
            with self.assertRaisesRegex(gate.StwoMedianTimingGateError, "decision drift"):
                gate.write_json(payload, summary, out)
            self.assertFalse(out.exists())
        finally:
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
