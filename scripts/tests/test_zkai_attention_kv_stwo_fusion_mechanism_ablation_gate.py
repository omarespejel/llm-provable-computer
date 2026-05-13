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

    def test_rejects_route_savings_claim_drift_directly(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["route_matrix"]["fused_savings_bytes_total"] = 0
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "matched route savings below claim threshold",
        ):
            gate.validate_payload(payload, require_mutation_summary=False, expected=payload)

        payload = self.strip_mutation_summary(self.payload)
        payload["route_matrix"]["all_matched_profiles_save_json_bytes"] = False
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "matched route savings persistence drift",
        ):
            gate.validate_payload(payload, require_mutation_summary=False, expected=payload)

    def test_rejects_binary_local_typed_saving_claim_drift_directly(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["binary_typed_accounting"]["fused_saves_vs_source_plus_sidecar_local_typed_bytes"] = 0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "d32 local typed saving below claim"):
            gate.validate_payload(payload, require_mutation_summary=False, expected=payload)

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
        only_json = json_path.with_name(json_path.stem + "-only.json")
        implicit_tsv = only_json.with_suffix(".tsv")
        try:
            gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, self.payload)
            self.assertIn("matched_profiles_checked", tsv_path.read_text(encoding="utf-8"))

            gate.write_outputs(self.payload, absolute_json, absolute_tsv)
            self.assertEqual(json.loads(absolute_json.read_text(encoding="utf-8")), self.payload)

            gate.write_outputs(self.payload, only_json.relative_to(gate.ROOT), None)
            self.assertTrue(only_json.exists())
            self.assertFalse(implicit_tsv.exists())
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)
            absolute_json.unlink(missing_ok=True)
            absolute_tsv.unlink(missing_ok=True)
            only_json.unlink(missing_ok=True)
            implicit_tsv.unlink(missing_ok=True)

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
        original_write_bytes = pathlib.Path.write_bytes
        try:
            def fail_on_tsv(src, dst):
                if pathlib.Path(dst) == tsv_path:
                    raise OSError("simulated second replace failure")
                return original_replace(src, dst)

            def fail_direct_write(_path, _contents):
                raise AssertionError("rollback must restore through an atomic temp replace")

            gate.os.replace = fail_on_tsv
            pathlib.Path.write_bytes = fail_direct_write
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "failed to write output path"):
                gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
            self.assertEqual(json_path.read_text(encoding="utf-8"), "original-json")
            self.assertFalse(tsv_path.exists())
        finally:
            gate.os.replace = original_replace
            pathlib.Path.write_bytes = original_write_bytes
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_write_outputs_rollback_does_not_follow_swapped_symlink(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix="fusion-transaction-symlink-json-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
            handle.write(b"original-json")
        tsv_path = json_path.with_suffix(".tsv")
        tsv_path.unlink(missing_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            outside_target = pathlib.Path(tmp) / "outside-target.json"
            outside_target.write_text("outside-original", encoding="utf-8")
            original_replace = gate.os.replace
            try:
                def swap_json_target_on_tsv(src, dst):
                    if pathlib.Path(dst) == tsv_path:
                        json_path.unlink(missing_ok=True)
                        try:
                            json_path.symlink_to(outside_target)
                        except OSError as err:
                            self.skipTest(f"symlink creation is unavailable: {err}")
                        raise OSError("simulated second replace failure after target swap")
                    return original_replace(src, dst)

                gate.os.replace = swap_json_target_on_tsv
                with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "failed to write output path"):
                    gate.write_outputs(self.payload, json_path.relative_to(gate.ROOT), tsv_path.relative_to(gate.ROOT))
                self.assertEqual(outside_target.read_text(encoding="utf-8"), "outside-original")
                self.assertTrue(json_path.is_symlink())
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
                row["fused_proof_size_bytes"] = 0
                row["fused_saves_vs_source_plus_sidecar_bytes"] = 0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "source-plus-sidecar must be positive"):
            gate._route_metrics(route)

        route = gate.load_json(gate.EVIDENCE_INPUTS["route_matrix"])
        route["route_rows"].insert(0, {"route_id": "unmatched-row"})
        del route["route_rows"][1]["fused_proof_size_bytes"]
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "route matrix row 1 missing"):
            gate._route_metrics(route)

        route = gate.load_json(gate.EVIDENCE_INPUTS["route_matrix"])
        for row in route["route_rows"]:
            if "fused_proof_size_bytes" in row:
                row["fused_proof_size_bytes"] = 0.5
                break
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "fused proof must be integer bytes"):
            gate._route_metrics(route)

        route = gate.load_json(gate.EVIDENCE_INPUTS["route_matrix"])
        for row in route["route_rows"]:
            if "fused_to_source_plus_sidecar_ratio" in row:
                row["fused_to_source_plus_sidecar_ratio"] = 0.5
                break
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "ratio does not match byte totals"):
            gate._route_metrics(route)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["profiles_checked"] = 10.0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section profiles checked must be integer"):
            gate._section_delta_metrics(section)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["role_totals"]["fused_saves_vs_source_plus_sidecar_bytes"] = 0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section delta savings total"):
            gate._section_delta_metrics(section)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["role_totals"]["fused_saves_vs_source_plus_sidecar_bytes"] = 184676.25
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "integer bytes"):
            gate._section_delta_metrics(section)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["bucket_totals_by_role"]["delta"]["opening_bucket_bytes"] = 171328.25
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "integer bytes"):
            gate._section_delta_metrics(section)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["section_totals_by_role"]["delta"]["fri_proof"] = 102304.25
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "integer bytes"):
            gate._section_delta_metrics(section)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["opening_bucket_savings_share"] = 0.5
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "section opening share does not match byte totals",
        ):
            gate._section_delta_metrics(section)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["backend_internal_split_status"] = "GO_BACKEND_INTERNAL_SPLIT"
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section backend split status drift"):
            gate._section_delta_metrics(section)

        typed = gate.load_json(gate.EVIDENCE_INPUTS["typed_size_estimate"])
        typed["aggregate"]["profiles_checked"] = 9.0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "typed profiles checked must be integer"):
            gate._typed_metrics(typed)

        typed = gate.load_json(gate.EVIDENCE_INPUTS["typed_size_estimate"])
        typed["aggregate"]["source_plus_sidecar_minus_fused_delta"]["typed_size_estimate_bytes"] = 0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "typed size savings total"):
            gate._typed_metrics(typed)

        typed = gate.load_json(gate.EVIDENCE_INPUTS["typed_size_estimate"])
        typed["aggregate"]["source_plus_sidecar_minus_fused_delta"]["trace_decommitments"] = 17312.25
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "integer bytes"):
            gate._typed_metrics(typed)

        typed = gate.load_json(gate.EVIDENCE_INPUTS["typed_size_estimate"])
        typed["aggregate"]["typed_saving_share_vs_source_plus_sidecar"] = 0.5
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "typed saving share does not match byte totals",
        ):
            gate._typed_metrics(typed)

        typed = gate.load_json(gate.EVIDENCE_INPUTS["typed_size_estimate"])
        typed["stable_binary_serializer_status"] = 1
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "typed stable binary serializer status must be string",
        ):
            gate._typed_metrics(typed)

        section = gate.load_json(gate.EVIDENCE_INPUTS["section_delta"])
        section["aggregate"]["section_totals_by_role"]["delta"] = None
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "section delta totals must be object"):
            gate._section_delta_metrics(section)

        typed = gate.load_json(gate.EVIDENCE_INPUTS["typed_size_estimate"])
        typed["aggregate"]["source_plus_sidecar_minus_fused_delta"] = None
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "typed size delta must be object"):
            gate._typed_metrics(typed)

        controlled = gate.load_json(gate.EVIDENCE_INPUTS["controlled_component_grid"])
        controlled["aggregate"]["profiles_checked"] = 10.0
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "controlled profiles checked must be integer",
        ):
            gate._controlled_metrics(controlled)

        controlled = gate.load_json(gate.EVIDENCE_INPUTS["controlled_component_grid"])
        controlled["aggregate"]["opening_plumbing_share_of_typed_savings"] = 0.5
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "controlled opening plumbing share does not match byte totals",
        ):
            gate._controlled_metrics(controlled)

        controlled = gate.load_json(gate.EVIDENCE_INPUTS["controlled_component_grid"])
        controlled["aggregate"]["typed_savings_bytes_total"] = 0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "controlled typed savings total"):
            gate._controlled_metrics(controlled)

        controlled = gate.load_json(gate.EVIDENCE_INPUTS["controlled_component_grid"])
        controlled["aggregate"]["opening_plumbing_savings_bytes_total"] = 44896.25
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "integer bytes"):
            gate._controlled_metrics(controlled)

        controlled = gate.load_json(gate.EVIDENCE_INPUTS["controlled_component_grid"])
        controlled["aggregate"]["fri_trace_merkle_path_savings_bytes_total"] = 41312.25
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "integer bytes"):
            gate._controlled_metrics(controlled)

        controlled = gate.load_json(gate.EVIDENCE_INPUTS["controlled_component_grid"])
        controlled["aggregate"]["typed_saving_share_total"] = 0.5
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "controlled typed saving share does not match byte totals",
        ):
            gate._controlled_metrics(controlled)

        controlled = gate.load_json(gate.EVIDENCE_INPUTS["controlled_component_grid"])
        controlled["aggregate"]["fri_trace_merkle_path_share_of_typed_savings"] = 0.5
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "controlled FRI trace merkle path share does not match byte totals",
        ):
            gate._controlled_metrics(controlled)

        controlled = gate.load_json(gate.EVIDENCE_INPUTS["controlled_component_grid"])
        controlled["stable_binary_serializer_status"] = "GO_STABLE_BINARY_SERIALIZER"
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "controlled stable binary serializer status drift",
        ):
            gate._controlled_metrics(controlled)

        binary = gate.load_json(gate.EVIDENCE_INPUTS["binary_typed_accounting"])
        binary["aggregate"]["profiles_checked"] = 3.0
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "binary profiles checked must be integer"):
            gate._binary_metrics(binary)

        binary = gate.load_json(gate.EVIDENCE_INPUTS["binary_typed_accounting"])
        binary["aggregate"]["source_plus_sidecar_json_proof_bytes"] = 116682.25
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "integer bytes"):
            gate._binary_metrics(binary)

        binary = gate.load_json(gate.EVIDENCE_INPUTS["binary_typed_accounting"])
        binary["aggregate"]["fused_saves_vs_source_plus_sidecar_local_typed_bytes"] = 2620.25
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "integer bytes"):
            gate._binary_metrics(binary)

        binary = gate.load_json(gate.EVIDENCE_INPUTS["binary_typed_accounting"])
        binary["aggregate"]["fused_saves_vs_source_plus_sidecar_json_bytes"] += 1
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "binary JSON proof saving does not match byte totals",
        ):
            gate._binary_metrics(binary)

        binary = gate.load_json(gate.EVIDENCE_INPUTS["binary_typed_accounting"])
        binary["aggregate"]["fused_saves_vs_source_plus_sidecar_local_typed_bytes"] += 1
        with self.assertRaisesRegex(
            gate.FusionMechanismAblationGateError,
            "binary local typed saving does not match byte totals",
        ):
            gate._binary_metrics(binary)

        binary = gate.load_json(gate.EVIDENCE_INPUTS["binary_typed_accounting"])
        binary["binary_serialization_status"] = "GO_UPSTREAM_STWO_WIRE_FORMAT"
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "binary serialization status drift"):
            gate._binary_metrics(binary)

        binary = gate.load_json(gate.EVIDENCE_INPUTS["binary_typed_accounting"])
        binary["first_blocker"] = ""
        with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "binary first blocker must be non-empty"):
            gate._binary_metrics(binary)

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
        original = gate._load_json_with_sha256

        def malformed(path):
            if str(path).endswith("route-matrix-2026-05.json"):
                return {}, "0" * 64
            return original(path)

        try:
            gate._load_json_with_sha256 = malformed
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "malformed source evidence"):
                gate._base_payload()
        finally:
            gate._load_json_with_sha256 = original

        original_route_metrics = gate._route_metrics

        def malformed_metrics(_payload):
            raise ValueError("non-numeric share")

        try:
            gate._route_metrics = malformed_metrics
            with self.assertRaisesRegex(gate.FusionMechanismAblationGateError, "malformed source evidence"):
                gate._base_payload()
        finally:
            gate._route_metrics = original_route_metrics

    def test_base_payload_hard_fails_evidence_consistency_drift(self):
        original_section = gate._section_delta_metrics

        def wrong_scope(payload):
            result = original_section(payload)
            result["profiles_checked"] = 9
            return result

        try:
            gate._section_delta_metrics = wrong_scope
            with self.assertRaisesRegex(
                gate.FusionMechanismAblationGateError,
                "section_delta_scope_is_ten_profile_slice",
            ):
                gate._base_payload()
        finally:
            gate._section_delta_metrics = original_section

        original_controlled = gate._controlled_metrics

        def wrong_controlled_scope(payload):
            result = original_controlled(payload)
            result["profiles_checked"] = 9
            return result

        try:
            gate._controlled_metrics = wrong_controlled_scope
            with self.assertRaisesRegex(
                gate.FusionMechanismAblationGateError,
                "controlled_component_grid_scope_is_ten_profile_slice",
            ):
                gate._base_payload()
        finally:
            gate._controlled_metrics = original_controlled

    def test_base_payload_uses_single_read_for_payload_and_sha(self):
        original = gate._open_repo_regular_file
        calls = []

        def recording_open(path):
            calls.append(path)
            return original(path)

        try:
            gate._open_repo_regular_file = recording_open
            gate._base_payload()
        finally:
            gate._open_repo_regular_file = original

        expected_paths = [
            gate._full_repo_path(gate._repo_relative_path(path, "evidence path"))
            for path in gate.EVIDENCE_INPUTS.values()
        ]
        self.assertEqual(calls, expected_paths)
        self.assertEqual(len(calls), len(gate.EVIDENCE_INPUTS))

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
