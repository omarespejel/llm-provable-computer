from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_block_statement_chain_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_derived_d128_block_statement_chain_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load derived block statement chain gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionDerivedD128BlockStatementChainGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = GATE.build_context()
        cls.payload = GATE.build_gate_result(copy.deepcopy(cls.context))

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_gate_result_binds_full_attention_derived_slice_chain(self) -> None:
        payload = self.fresh_payload()
        GATE.validate_payload(payload, context=copy.deepcopy(self.context))
        summary = payload["summary"]
        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], GATE.RESULT)
        self.assertEqual(summary["slice_count"], 6)
        self.assertEqual(summary["edge_count"], 11)
        self.assertTrue(summary["all_edges_match"])
        self.assertEqual(summary["accounted_relation_rows"], 199553)
        self.assertEqual(summary["projection_mul_rows"], 131072)
        self.assertEqual(summary["down_projection_mul_rows"], 65536)
        self.assertEqual(summary["activation_lookup_rows"], 2049)
        self.assertEqual(summary["residual_add_rows"], 128)
        self.assertEqual(payload["case_count"], 19)
        self.assertTrue(payload["all_mutations_rejected"])

    def test_statement_commitments_are_stable(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual(
            payload["block_statement_commitment"],
            "blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5",
        )
        self.assertEqual(
            payload["summary"]["derived_output_activation_commitment"],
            "blake2b-256:25feb3aa6a2a092602c86d10c767f71cdae3c60eade0254a2d121124b712bcf9",
        )
        self.assertEqual(
            payload["summary"]["source_attention_outputs_commitment"],
            "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
        )

    def test_source_artifacts_bind_expected_payload_commitments(self) -> None:
        payload = self.fresh_payload()
        by_id = {artifact["id"]: artifact for artifact in payload["source_artifacts"]}
        self.assertEqual(set(by_id), set(GATE.ARTIFACT_SPECS))
        self.assertEqual(
            by_id["input"]["payload_commitment"],
            "sha256:2ae84c02a4267c6e85786d1317fdd2c6d7921970169db09bd66dfbd9f34b7a77",
        )
        self.assertEqual(
            by_id["residual_add"]["payload_commitment"],
            "sha256:a82f94544eb2f7415fa0caec9605730a857e5a380bed0cbccb6ec2bd6f869861",
        )

    def test_sha_edges_store_the_matched_payload_commitment(self) -> None:
        payload = self.fresh_payload()
        edges = {edge["id"]: edge for edge in payload["block_statement"]["edges"]}
        self.assertEqual(
            edges["activation_statement_to_down_projection_source"]["commitment"],
            "sha256:bf058e95c387d536d85a2a9b455c0f211ecfc7bc1f71ba4df3b17aec9442b302",
        )
        self.assertEqual(
            edges["residual_source_payloads_bind_prior_slices"]["commitment"],
            "sha256:66dd7949ef35d6ddecf6ee0534dabe7e78ccb898776e7e1fa7bcbac2e2aaf150",
        )
        self.assertEqual(
            edges["activation_source_reuses_projection_boundary"]["commitment"],
            "sha256:627115a11d771a6da1c50407963efa5eb39c52226adf69deedc43083c05a0af6",
        )

    def test_mutation_errors_are_stable_markers(self) -> None:
        payload = self.fresh_payload()
        self.assertEqual({case["name"]: case["error"] for case in payload["cases"]}, GATE.EXPECTED_MUTATION_ERRORS)

    def test_mutation_errors_reject_unexpected_markers(self) -> None:
        original = GATE.EXPECTED_MUTATION_ERRORS["decision_overclaim"]
        GATE.EXPECTED_MUTATION_ERRORS["decision_overclaim"] = "impossible marker"
        try:
            with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "unexpected error"):
                GATE.run_mutation_cases(
                    GATE.build_core_payload(copy.deepcopy(self.context)),
                    copy.deepcopy(self.context),
                )
        finally:
            GATE.EXPECTED_MUTATION_ERRORS["decision_overclaim"] = original

    def test_payload_rejects_source_artifact_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_artifacts"][0]["sha256"] = "11" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "source artifact drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_edge_drift(self) -> None:
        payload = self.fresh_payload()
        payload["block_statement"]["edges"][0]["commitment"] = "blake2b-256:" + "22" * 32
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "block statement drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_output_relabeling_as_input(self) -> None:
        payload = self.fresh_payload()
        payload["block_statement"]["derived_output_activation_commitment"] = payload["block_statement"][
            "derived_input_activation_commitment"
        ]
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "block statement drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_relation_row_drift(self) -> None:
        payload = self.fresh_payload()
        payload["block_statement"]["relation_rows"]["accounted_relation_rows"] += 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "block statement drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_summary_overclaim(self) -> None:
        payload = self.fresh_payload()
        payload["summary"]["accounted_relation_rows"] = 1
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "summary drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_payload_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "33" * 32
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "payload commitment drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_payload_rejects_mutation_case_metadata_drift(self) -> None:
        payload = self.fresh_payload()
        payload["cases"][0]["name"] = "different"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "mutation case name drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

        payload = self.fresh_payload()
        payload["cases"][0]["error"] = "different"
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "mutation case error drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

        payload = self.fresh_payload()
        payload["cases"][0]["accepted"] = True
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "mutation accepted unexpectedly"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

        payload = self.fresh_payload()
        payload["cases"][0]["rejected"] = False
        GATE.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "mutation rejection flag drift"):
            GATE.validate_payload(payload, context=copy.deepcopy(self.context))

    def test_to_tsv_requires_final_payload(self) -> None:
        core = GATE.build_core_payload(copy.deepcopy(self.context))
        with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "finalized payload"):
            GATE.to_tsv(core, context=copy.deepcopy(self.context))

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "statement-chain.json"
            tsv_path = tmp / "statement-chain.tsv"
            GATE.write_outputs(payload, json_path, tsv_path, context=copy.deepcopy(self.context))
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn("accounted_relation_rows", tsv)
            self.assertIn("199553", tsv)

    def test_write_outputs_anchors_relative_paths_to_repo_root(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp, tempfile.TemporaryDirectory() as raw_cwd:
            tmp = pathlib.Path(raw_tmp)
            json_path = (tmp / "statement-chain.json").relative_to(GATE.ROOT)
            tsv_path = (tmp / "statement-chain.tsv").relative_to(GATE.ROOT)
            original_cwd = pathlib.Path.cwd()
            try:
                os.chdir(raw_cwd)
                GATE.write_outputs(payload, json_path, tsv_path, context=copy.deepcopy(self.context))
            finally:
                os.chdir(original_cwd)
            self.assertEqual(json.loads((tmp / "statement-chain.json").read_text(encoding="utf-8")), payload)
            self.assertIn("199553", (tmp / "statement-chain.tsv").read_text(encoding="utf-8"))

    def test_write_outputs_rejects_paths_outside_evidence_dir(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "docs/engineering/evidence"):
                GATE.write_outputs(payload, tmp / "statement-chain.json", None, context=copy.deepcopy(self.context))

    def test_write_outputs_rejects_wrong_suffix(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "end with .json"):
                GATE.write_outputs(payload, tmp / "statement-chain.txt", None, context=copy.deepcopy(self.context))

    def test_write_outputs_rejects_symlinked_leaf(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            target = tmp / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = tmp / "link.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "symlink"):
                GATE.write_outputs(payload, link, None, context=copy.deepcopy(self.context))

    def test_write_outputs_rejects_intermediate_symlink_parent(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            real_dir = tmp / "real"
            real_dir.mkdir()
            link_dir = tmp / "linkdir"
            link_dir.symlink_to(real_dir, target_is_directory=True)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "symlink"):
                GATE.write_outputs(payload, link_dir / "statement-chain.json", None, context=copy.deepcopy(self.context))

    def test_write_outputs_wraps_parent_resolve_race(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            output_path = pathlib.Path(raw_tmp) / "statement-chain.json"
            original_resolve = pathlib.Path.resolve

            def race_resolve(path: pathlib.Path, *args, **kwargs):
                if path == output_path.parent:
                    raise FileNotFoundError("simulated parent removal")
                return original_resolve(path, *args, **kwargs)

            try:
                pathlib.Path.resolve = race_resolve
                with self.assertRaisesRegex(
                    GATE.AttentionDerivedD128BlockStatementChainError,
                    "output parent cannot be resolved",
                ):
                    GATE.write_outputs(payload, output_path, None, context=copy.deepcopy(self.context))
            finally:
                pathlib.Path.resolve = original_resolve

    def test_load_json_rejects_unhardened_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            source = tmp / "source.json"
            source.write_text(json.dumps(GATE.build_core_payload(copy.deepcopy(self.context))), encoding="utf-8")
            link = tmp / "link.json"
            link.symlink_to(source)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "symlink"):
                GATE.load_json(link)
        with tempfile.TemporaryDirectory() as raw_tmp:
            outside = pathlib.Path(raw_tmp) / "source.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "inside repository|traverse"):
                GATE.load_json(outside)

    def test_load_json_rejects_intermediate_symlink_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            real_dir = tmp / "real"
            real_dir.mkdir()
            source = real_dir / "source.json"
            source.write_text(json.dumps(GATE.build_core_payload(copy.deepcopy(self.context))), encoding="utf-8")
            link_dir = tmp / "linkdir"
            link_dir.symlink_to(real_dir, target_is_directory=True)
            with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "symlink"):
                GATE.load_json(link_dir / "source.json")

    def test_load_json_rejects_oversized_source(self) -> None:
        original_max = GATE.MAX_SOURCE_BYTES
        try:
            GATE.MAX_SOURCE_BYTES = 8
            with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
                source = pathlib.Path(raw_tmp) / "oversized.json"
                source.write_text(" " * 9, encoding="utf-8")
                with self.assertRaisesRegex(GATE.AttentionDerivedD128BlockStatementChainError, "size limit"):
                    GATE.load_json(source)
        finally:
            GATE.MAX_SOURCE_BYTES = original_max


if __name__ == "__main__":
    unittest.main()
