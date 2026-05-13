from __future__ import annotations

import copy
import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_block_statement_bridge_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_block_statement_bridge_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load attention block statement bridge gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class AttentionBlockStatementBridgeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = GATE.build_gate_result()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_builds_statement_bridge_without_value_equality_overclaim(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload)
        self.assertEqual(payload["schema"], GATE.SCHEMA)
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertEqual(payload["non_claims"], GATE.NON_CLAIMS)
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATIONS))
        self.assertTrue(payload["all_mutations_rejected"])

        summary = payload["summary"]
        self.assertEqual(summary["attention_mutations_rejected"], 20)
        self.assertEqual(summary["block_mutations_rejected"], 52)
        self.assertEqual(summary["combined_source_mutation_floor"], 72)
        self.assertFalse(summary["current_commitments_equal"])
        self.assertTrue(summary["adapter_required"])
        self.assertEqual(summary["attention_value_width"], 8)
        self.assertEqual(summary["block_width"], 128)

    def test_bridge_statement_binds_attention_output_and_d128_block_input_handles(self) -> None:
        payload = self.fresh_payload()
        statement = payload["bridge_statement"]
        expected_commitment = GATE.blake2b_commitment(statement, GATE.BRIDGE_DOMAIN)
        self.assertEqual(payload["bridge_statement_commitment"], expected_commitment)
        self.assertEqual(payload["summary"]["bridge_statement_commitment"], expected_commitment)

        feed = statement["feed_edge"]
        self.assertEqual(feed["from_commitment"], statement["attention_output"]["outputs_commitment"])
        self.assertEqual(feed["to_commitment"], statement["d128_block_input"]["input_activation_commitment"])
        self.assertEqual(
            statement["attention_output"]["outputs_commitment"],
            "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
        )
        self.assertEqual(
            statement["d128_block_input"]["input_activation_commitment"],
            "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78",
        )

    def test_source_artifacts_are_hash_bound(self) -> None:
        artifacts = {artifact["id"]: artifact for artifact in self.fresh_payload()["source_artifacts"]}
        self.assertEqual(
            set(artifacts),
            {"model_faithful_attention_bridge", "d128_full_block_accumulator", "one_transformer_block_surface"},
        )
        for artifact in artifacts.values():
            self.assertTrue(artifact["path"].startswith("docs/engineering/evidence/"))
            self.assertEqual(len(artifact["sha256"]), 64)
            self.assertEqual(len(artifact["payload_sha256"]), 64)

    def test_rejects_malformed_source_artifacts(self) -> None:
        payload = self.fresh_payload()
        payload["source_artifacts"][0]["sha256"] = "nothex"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "sha256"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        payload["source_artifacts"][0]["path"] = "../outside.json"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "source artifact path"):
            GATE.validate_payload(payload)

        payload = self.fresh_payload()
        del payload["source_artifacts"][0]["payload_sha256"]
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "keys drift"):
            GATE.validate_payload(payload)

    def test_rejects_missing_or_empty_attention_comparisons(self) -> None:
        attention, accumulator, surface, _ = GATE._load_sources()
        attention["bridge_contract"]["metrics"]["comparisons"] = {}
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "comparison keys drift"):
            GATE.build_bridge_statement(attention, accumulator, surface)

        attention, accumulator, surface, _ = GATE._load_sources()
        del attention["bridge_contract"]["metrics"]["comparisons"]["score_rows_match"]
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "score_rows_match"):
            GATE.build_bridge_statement(attention, accumulator, surface)

        attention, accumulator, surface, _ = GATE._load_sources()
        attention["bridge_contract"]["metrics"]["comparisons"]["score_rows_match"] = False
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "score_rows_match"):
            GATE.build_bridge_statement(attention, accumulator, surface)

    def test_missing_nested_source_fields_use_gate_errors(self) -> None:
        attention, accumulator, surface, _ = GATE._load_sources()
        del attention["route_id"]
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "attention bridge drift: route_id"):
            GATE.build_bridge_statement(attention, accumulator, surface)

        attention, accumulator, surface, _ = GATE._load_sources()
        del accumulator["summary"]
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "d128 summary"):
            GATE.build_bridge_statement(attention, accumulator, surface)

        attention, accumulator, surface, _ = GATE._load_sources()
        del surface["summary"]
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "one-block surface summary"):
            GATE.build_bridge_statement(attention, accumulator, surface)

    def test_rejects_summary_drift_and_tsv_derives_from_statement(self) -> None:
        payload = self.fresh_payload()
        forged = "blake2b-256:" + "77" * 32
        actual = payload["bridge_statement"]["attention_output"]["outputs_commitment"]
        payload["summary"]["attention_outputs_commitment"] = forged
        GATE.refresh_payload_commitment(payload)

        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "summary drift"):
            GATE.validate_payload(payload)
        tsv = GATE.to_tsv(payload)
        self.assertIn(actual, tsv)
        self.assertNotIn(forged, tsv)

    def test_read_source_bytes_rejects_oversize_sources(self) -> None:
        old_limit = GATE.MAX_SOURCE_BYTES
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-block-bridge-source-limit-",
            suffix=".json",
            delete=False,
        ) as handle:
            source_path = pathlib.Path(handle.name)
            handle.write(b"12345")
        try:
            GATE.MAX_SOURCE_BYTES = 4
            with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "size limit"):
                GATE.read_source_bytes(source_path)
        finally:
            GATE.MAX_SOURCE_BYTES = old_limit
            source_path.unlink(missing_ok=True)

    def test_mutation_inventory_rejects_claim_drift(self) -> None:
        payload = self.fresh_payload()
        case_by_name = {case["name"]: case for case in payload["cases"]}
        self.assertEqual(list(case_by_name), list(GATE.EXPECTED_MUTATIONS))
        for name in (
            "attention_output_commitment_drift",
            "block_input_activation_commitment_drift",
            "feed_equality_overclaim",
            "adapter_requirement_removed",
            "source_artifact_sha_drift",
            "summary_attention_output_commitment_drift",
            "payload_commitment_drift",
        ):
            with self.subTest(name=name):
                self.assertTrue(case_by_name[name]["rejected"])
                self.assertFalse(case_by_name[name]["accepted"])

    def test_rejects_feed_edge_and_non_claim_relabeling(self) -> None:
        payload = self.fresh_payload()
        payload["bridge_statement"]["feed_edge"]["current_commitments_equal"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "bridge statement commitment drift"):
            GATE.validate_payload(payload, expected=self.payload)

        payload = self.fresh_payload()
        payload["non_claims"] = payload["non_claims"][1:]
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "non-claims drift"):
            GATE.validate_payload(payload, expected=self.payload)

    def test_tsv_records_no_go_feed_edge(self) -> None:
        tsv = GATE.to_tsv(self.fresh_payload())
        self.assertIn("GO_STATEMENT_BRIDGE_NO_GO_ATTENTION_TO_BLOCK_VALUE_EQUALITY", tsv)
        self.assertIn("NO_GO_CURRENT_FIXTURES_DO_NOT_BIND_VALUE_EQUALITY", tsv)
        self.assertIn("\tfalse\t", tsv)

    def test_write_outputs_round_trip_and_rejects_outside_path(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-block-bridge-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            json_path = pathlib.Path(handle.name)
        json_path.unlink()
        tsv_path = json_path.with_suffix(".tsv")
        try:
            GATE.write_outputs(self.fresh_payload(), json_path.relative_to(GATE.ROOT), tsv_path.relative_to(GATE.ROOT))
            self.assertTrue(json_path.exists())
            self.assertTrue(tsv_path.exists())
            with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "output path must stay"):
                GATE.write_outputs(self.fresh_payload(), pathlib.Path("/tmp/out.json"), None)
            with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "output path must end"):
                GATE.write_outputs(self.fresh_payload(), None, json_path)
        finally:
            json_path.unlink(missing_ok=True)
            tsv_path.unlink(missing_ok=True)

    def test_rejects_malformed_commitments_and_parent_symlink_outputs(self) -> None:
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "lowercase hex digest"):
            GATE._commitment("blake2b-256:not-hex", "bad commitment")
        with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "lowercase hex digest"):
            GATE._commitment("sha256:" + "AA" * 32, "uppercase commitment")

        with tempfile.TemporaryDirectory() as outside_dir:
            link_path = GATE.EVIDENCE_DIR / "attention-block-bridge-symlink-parent-test"
            try:
                os.symlink(outside_dir, link_path)
                with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "output parent must stay"):
                    GATE.require_output_path(link_path / "out.json", ".json")
            finally:
                link_path.unlink(missing_ok=True)

    def test_write_outputs_rejects_leaf_symlink_at_write_time(self) -> None:
        if getattr(os, "O_NOFOLLOW", 0) == 0:
            self.skipTest("O_NOFOLLOW is unavailable on this platform")

        with tempfile.NamedTemporaryFile(delete=False) as outside_handle:
            outside_path = pathlib.Path(outside_handle.name)
        link_path = GATE.EVIDENCE_DIR / "attention-block-bridge-leaf-symlink-test.json"
        original_require_output_path = GATE.require_output_path

        def stale_validation(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
            if path is None:
                return None
            self.assertEqual(suffix, ".json")
            return link_path

        try:
            link_path.unlink(missing_ok=True)
            os.symlink(outside_path, link_path)
            GATE.require_output_path = stale_validation
            with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "must not become a symlink"):
                GATE.write_outputs(self.fresh_payload(), pathlib.Path("stale-validation.json"), None)
        finally:
            GATE.require_output_path = original_require_output_path
            link_path.unlink(missing_ok=True)
            outside_path.unlink(missing_ok=True)

    def test_atomic_write_preserves_existing_output_on_replace_failure(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-block-bridge-atomic-write-",
            suffix=".json",
            delete=False,
        ) as handle:
            output_path = pathlib.Path(handle.name)
            handle.write(b"original\n")
        original_replace = GATE.os.replace

        def failing_replace(*args, **kwargs) -> None:
            raise OSError("simulated replace failure")

        try:
            GATE.os.replace = failing_replace
            with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "failed writing json output"):
                GATE.write_text_no_follow(output_path, "replacement\n", "json output")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "original\n")
            self.assertEqual(list(GATE.EVIDENCE_DIR.glob(f".{output_path.name}.*.tmp")), [])
        finally:
            GATE.os.replace = original_replace
            output_path.unlink(missing_ok=True)

    def test_atomic_write_cleanup_error_does_not_mask_replace_failure(self) -> None:
        with tempfile.NamedTemporaryFile(
            dir=GATE.EVIDENCE_DIR,
            prefix="attention-block-bridge-cleanup-write-",
            suffix=".json",
            delete=False,
        ) as handle:
            output_path = pathlib.Path(handle.name)
            handle.write(b"original\n")
        original_replace = GATE.os.replace
        original_unlink = GATE.os.unlink

        def failing_replace(*args, **kwargs) -> None:
            raise OSError("simulated replace failure")

        def failing_unlink(*args, **kwargs) -> None:
            raise OSError("simulated cleanup failure")

        try:
            GATE.os.replace = failing_replace
            GATE.os.unlink = failing_unlink
            with self.assertRaisesRegex(GATE.AttentionBlockStatementBridgeError, "simulated replace failure"):
                GATE.write_text_no_follow(output_path, "replacement\n", "json output")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "original\n")
        finally:
            GATE.os.replace = original_replace
            GATE.os.unlink = original_unlink
            for temp_path in GATE.EVIDENCE_DIR.glob(f".{output_path.name}.*.tmp"):
                temp_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
