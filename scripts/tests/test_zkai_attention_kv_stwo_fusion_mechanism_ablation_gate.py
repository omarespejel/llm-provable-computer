import copy
import json
import math
import pathlib
import tempfile
import unittest

from scripts import zkai_attention_kv_stwo_fusion_mechanism_ablation_gate as gate


class AttentionKvStwoFusionMechanismAblationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload_base = gate.build_payload()

    def setUp(self) -> None:
        self.payload = copy.deepcopy(self.payload_base)

    def strip_mutation_summary(self, payload):
        payload = copy.deepcopy(payload)
        for key in (
            "mutation_cases",
            "mutations_checked",
            "mutations_rejected",
            "all_mutations_rejected",
            "payload_commitment",
        ):
            payload.pop(key, None)
        return payload

    def assert_rejects(self, payload, message):
        with self.assertRaises(gate.FusionMechanismAblationGateError) as ctx:
            gate.validate_payload(payload, require_mutation_summary=False)
        self.assertIn(message, str(ctx.exception))

    def test_builds_checked_mechanism_ablation_payload(self):
        payload = self.payload
        gate.validate_payload(payload)

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["mechanism_status"], gate.MECHANISM_STATUS)
        self.assertEqual(payload["backend_internal_split_status"], gate.BACKEND_INTERNAL_SPLIT_STATUS)
        self.assertEqual(payload["timing_policy"], gate.TIMING_POLICY)
        self.assertEqual(len(payload["source_artifacts"]), 5)

        route = payload["route_matrix"]
        self.assertEqual(route["matched_profiles_checked"], 11)
        self.assertEqual(route["source_plus_sidecar_raw_proof_bytes_total"], 930824)
        self.assertEqual(route["fused_proof_size_bytes_total"], 736727)
        self.assertEqual(route["fused_savings_bytes_total"], 194097)
        self.assertTrue(route["all_matched_profiles_save_json_bytes"])

        section = payload["section_delta"]
        self.assertEqual(section["profiles_checked"], 10)
        self.assertEqual(section["json_savings_bytes_total"], 184676)
        self.assertEqual(section["opening_bucket_savings_share"], 0.927722)
        self.assertEqual(section["largest_delta_section"], "fri_proof")

        typed = payload["typed_size_estimate"]
        self.assertEqual(typed["profiles_checked"], 9)
        self.assertEqual(typed["typed_savings_bytes_total"], 42492)
        self.assertEqual(typed["fri_trace_decommitment_savings_bytes"], 36896)
        self.assertEqual(typed["fri_trace_decommitment_savings_share"], 0.868305)

        controlled = payload["controlled_component_grid"]
        self.assertEqual(controlled["profiles_checked"], 10)
        self.assertEqual(controlled["typed_savings_bytes_total"], 51288)
        self.assertEqual(controlled["opening_plumbing_share_of_typed_savings"], 0.87537)

        binary = payload["binary_typed_accounting"]
        self.assertEqual(binary["profiles_checked"], 3)
        self.assertEqual(binary["fused_saves_vs_source_plus_sidecar_local_typed_bytes"], 2620)
        self.assertIn("not upstream Stwo verifier-facing binary proof serialization", payload["non_claims"])

    def test_declared_mutations_reject(self):
        self.assertEqual([item["name"] for item in self.payload["mutation_cases"]], gate.EXPECTED_MUTATION_NAMES)
        self.assertTrue(all(item["rejected"] is True for item in self.payload["mutation_cases"]))
        self.assertEqual(self.payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(self.payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(self.payload["all_mutations_rejected"])

    def test_rejects_claim_drift_after_recommit(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["route_matrix"]["fused_savings_bytes_total"] += 1
        self.assert_rejects(payload, "route matrix drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["section_delta"]["opening_bucket_savings_share"] = 0.5
        self.assert_rejects(payload, "section delta drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["typed_size_estimate"]["fri_trace_decommitment_savings_share"] = 0.1
        self.assert_rejects(payload, "typed size estimate drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["binary_typed_accounting"]["cli_upstream_stwo_serialization_status"] = "UPSTREAM_STWO_WIRE_FORMAT"
        self.assert_rejects(payload, "binary accounting overclaim")

        payload = self.strip_mutation_summary(self.payload)
        payload["non_claims"] = payload["non_claims"][1:]
        self.assert_rejects(payload, "non_claims drift")

    def test_rejects_commitment_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "payload commitment drift"):
            gate.validate_payload(payload)

    def test_tsv_summary_contains_core_metrics(self):
        tsv = gate.to_tsv(self.payload)
        self.assertIn("route_json_savings_bytes\t194097", tsv)
        self.assertIn("section_opening_share\t0.927722", tsv)
        self.assertIn("d32_local_typed_saving_bytes\t2620", tsv)

    def test_write_outputs_round_trip(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix="fusion-mechanism-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        absolute_json = json_path.with_name(json_path.stem + "-absolute.json")
        absolute_tsv = json_path.with_name(json_path.stem + "-absolute.tsv")
        try:
            gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, self.payload)
            self.assertIn("matched_profiles_checked", tsv_path.read_text(encoding="utf-8"))

            gate.write_outputs(self.payload, absolute_json, absolute_tsv)
            self.assertEqual(json.loads(absolute_json.read_text(encoding="utf-8")), self.payload)
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)
            absolute_json.unlink(missing_ok=True)
            absolute_tsv.unlink(missing_ok=True)

    def test_write_outputs_rejects_outside_or_symlinked_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = pathlib.Path(tmp) / "out.json"
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "docs/engineering/evidence"):
                gate.write_outputs(self.payload, outside, gate.TSV_OUT.relative_to(gate.ROOT))

        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as tmp:
            real_dir = pathlib.Path(tmp) / "real"
            real_dir.mkdir()
            link_dir = pathlib.Path(tmp) / "linked"
            try:
                link_dir.symlink_to(real_dir, target_is_directory=True)
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "symlink components"):
                gate.write_outputs(
                    self.payload,
                    (link_dir / "out.json").relative_to(gate.ROOT),
                    gate.TSV_OUT.relative_to(gate.ROOT),
                )

        with tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix="fusion-output-parent-",
            delete=False,
        ) as handle:
            parent_file = pathlib.Path(handle.name)
        try:
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "failed to write output path"):
                gate.write_outputs(
                    self.payload,
                    (parent_file / "out.json").relative_to(gate.ROOT),
                    gate.TSV_OUT.relative_to(gate.ROOT),
                )
        finally:
            parent_file.unlink(missing_ok=True)

    def test_write_outputs_rolls_back_when_second_replace_fails(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix="fusion-transaction-json-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
            handle.write(b"original-json")
        tsv_path = json_path.with_suffix(".tsv")
        tsv_path.unlink(missing_ok=True)

        original_replace = gate.os.replace
        try:
            def fail_on_tsv(src, dst):
                if pathlib.Path(dst) == tsv_path:
                    raise OSError("simulated second replace failure")
                return original_replace(src, dst)

            gate.os.replace = fail_on_tsv
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "failed to write output path"):
                gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json_path.read_text(encoding="utf-8"), "original-json")
            self.assertFalse(tsv_path.exists())
        finally:
            gate.os.replace = original_replace
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_json_helpers_reject_non_finite_values(self):
        payload = copy.deepcopy(self.payload)
        payload["section_delta"]["opening_bucket_savings_share"] = math.nan
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "invalid JSON value"):
            gate.canonical_json_bytes(payload)

        payload = copy.deepcopy(self.payload)
        payload["not_json_serializable"] = {1, 2, 3}
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "invalid JSON value"):
            gate.canonical_json_bytes(payload)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.EVIDENCE_DIR,
            prefix="fusion-non-finite-",
            suffix=".json",
            delete=False,
        ) as handle:
            bad_path = pathlib.Path(handle.name)
            handle.write('{"value": NaN}\n')
        try:
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "non-finite JSON constant"):
                gate.load_json(str(bad_path.relative_to(gate.ROOT)))
        finally:
            bad_path.unlink(missing_ok=True)

    def test_metric_extractors_fail_closed_on_empty_or_zero_inputs(self):
        route = gate.load_json(gate.EVIDENCE_INPUTS["route_matrix"])
        route["route_rows"] = []
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "matched source-plus-sidecar"):
            gate._route_metrics(route)

        route = gate.load_json(gate.EVIDENCE_INPUTS["route_matrix"])
        for row in route["route_rows"]:
            if "source_plus_sidecar_raw_proof_bytes" in row:
                row["source_plus_sidecar_raw_proof_bytes"] = 0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "source-plus-sidecar total"):
            gate._route_metrics(route)

        route = gate.load_json(gate.EVIDENCE_INPUTS["route_matrix"])
        route["route_rows"].insert(0, {"route_id": "unmatched-row"})
        del route["route_rows"][1]["fused_proof_size_bytes"]
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "route matrix row 1 missing"):
            gate._route_metrics(route)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["role_totals"]["fused_saves_vs_source_plus_sidecar_bytes"] = 0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section delta savings total"):
            gate._section_delta_metrics(section)

        typed = gate.load_json(gate.EVIDENCE_INPUTS["typed_size_estimate"])
        typed["aggregate"]["source_plus_sidecar_minus_fused_delta"]["typed_size_estimate_bytes"] = 0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "typed size savings total"):
            gate._typed_metrics(typed)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["section_totals_by_role"]["delta"] = None
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section delta totals must be object"):
            gate._section_delta_metrics(section)

        typed = gate.load_json(gate.EVIDENCE_INPUTS["typed_size_estimate"])
        typed["aggregate"]["source_plus_sidecar_minus_fused_delta"] = None
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "typed size delta must be object"):
            gate._typed_metrics(typed)

    def test_payload_field_helpers_reject_wrong_types(self):
        payload = copy.deepcopy(self.payload)
        payload["section_delta"]["opening_bucket_savings_share"] = "0.9"
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section opening share must be numeric"):
            gate._numeric_payload_field(
                payload,
                ("section_delta", "opening_bucket_savings_share"),
                "section opening share",
            )

        payload = copy.deepcopy(self.payload)
        payload["binary_typed_accounting"]["cli_upstream_stwo_serialization_status"] = 1
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "binary status must be string"):
            gate._string_payload_field(
                payload,
                ("binary_typed_accounting", "cli_upstream_stwo_serialization_status"),
                "binary status",
            )

        payload = copy.deepcopy(self.payload)
        payload["section_delta"]["opening_bucket_savings_share"] = math.inf
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section opening share must be finite"):
            gate._share_payload_field(
                payload,
                ("section_delta", "opening_bucket_savings_share"),
                "section opening share",
            )

        payload = copy.deepcopy(self.payload)
        payload["section_delta"]["opening_bucket_savings_share"] = math.nan
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section opening share must be finite"):
            gate._share_payload_field(
                payload,
                ("section_delta", "opening_bucket_savings_share"),
                "section opening share",
            )

        payload = copy.deepcopy(self.payload)
        payload["section_delta"]["opening_bucket_savings_share"] = 1.1
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "section opening share must be between 0 and 1",
        ):
            gate._share_payload_field(
                payload,
                ("section_delta", "opening_bucket_savings_share"),
                "section opening share",
            )

        payload = self.strip_mutation_summary(self.payload)
        payload["binary_typed_accounting"]["cli_upstream_stwo_serialization_status"] = "upstream_stwo_wire_format"
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "binary accounting overclaim"):
            gate.validate_payload(payload, require_mutation_summary=False)

    def test_base_payload_normalizes_malformed_source_evidence_errors(self):
        original = gate.load_json

        def malformed(path):
            if str(path).endswith("route-matrix-2026-05.json"):
                return {}
            return original(path)

        try:
            gate.load_json = malformed
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "malformed source evidence"):
                gate._base_payload()
        finally:
            gate.load_json = original

    def test_build_payload_reuses_precomputed_expected_payload(self):
        original = gate._base_payload
        calls = 0

        def counted_base_payload():
            nonlocal calls
            calls += 1
            return original()

        try:
            gate._base_payload = counted_base_payload
            gate.build_payload()
            self.assertEqual(calls, 1)
        finally:
            gate._base_payload = original


if __name__ == "__main__":
    unittest.main()
