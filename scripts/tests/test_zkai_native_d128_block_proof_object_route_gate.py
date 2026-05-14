from __future__ import annotations

import copy
import json
import pathlib
import tempfile
import unittest

from scripts import zkai_native_d128_block_proof_object_route_gate as gate


class NativeD128BlockProofObjectRouteGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_builds_bounded_no_go_route_without_promoting_package_bytes(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload)

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["decision"], gate.NATIVE_PROOF_OBJECT_STATUS)
        self.assertEqual(payload["result"], gate.RESULT)
        self.assertEqual(payload["issue"], 387)
        self.assertFalse(payload["claim_guard"]["matched_nanozk_claim_allowed"])
        self.assertFalse(payload["claim_guard"]["native_proof_size_claim_allowed"])
        self.assertFalse(payload["claim_guard"]["package_bytes_are_proof_bytes"])
        self.assertFalse(payload["claim_guard"]["native_d128_block_proof_object_exists"])
        self.assertEqual(payload["case_count"], len(gate.MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

        summary = payload["summary"]
        self.assertEqual(summary["native_block_proof_object_status"], gate.NATIVE_PROOF_OBJECT_STATUS)
        self.assertEqual(summary["d128_checked_rows"], 197504)
        self.assertEqual(summary["attention_derived_statement_chain_rows"], 199553)
        self.assertEqual(summary["attention_derived_statement_chain_extra_rows_vs_d128_receipt"], 2049)
        self.assertEqual(summary["two_slice_outer_target_rows"], 256)
        self.assertEqual(summary["compressed_statement_chain_bytes"], 2559)
        self.assertEqual(summary["package_without_vk_bytes"], 4752)
        self.assertEqual(summary["package_without_vk_vs_nanozk_reported_ratio"], 0.688696)
        self.assertEqual(summary["package_with_vk_bytes"], 10608)
        self.assertEqual(summary["package_with_vk_vs_nanozk_reported_ratio"], 1.537391)
        self.assertIn(gate.FIRST_BLOCKER_CATEGORY, summary["first_blocker"])
        self.assertIn("two-slice target is already NO-GO", summary["first_blocker"])
        self.assertIn("implement the smallest native two-slice outer proof backend", summary["next_minimal_experiment"])
        self.assertIn("not a NANOZK proof-size win", payload["non_claims"])

    def test_route_rows_separate_accumulator_input_contract_package_and_missing_proof(self) -> None:
        rows = {row["row_id"]: row for row in self.fresh_payload()["route_rows"]}
        self.assertEqual(rows["full_d128_verifier_accumulator"]["status"], gate.FULL_ACCUMULATOR_STATUS)
        self.assertEqual(rows["full_d128_verifier_accumulator"]["rows"], 197504)
        self.assertIsNone(rows["full_d128_verifier_accumulator"]["bytes"])
        self.assertEqual(rows["two_slice_outer_proof_target"]["status"], gate.TWO_SLICE_STATUS)
        self.assertEqual(rows["two_slice_outer_proof_target"]["rows"], 256)
        self.assertEqual(rows["attention_derived_outer_input_contract"]["bytes"], 2559)
        self.assertEqual(rows["external_package_without_vk"]["bytes"], 4752)
        self.assertEqual(rows["external_package_without_vk"]["ratio_vs_nanozk_reported"], 0.688696)
        self.assertEqual(rows["external_package_with_vk"]["status"], gate.PACKAGE_WITH_VK_STATUS)
        self.assertEqual(rows["external_package_with_vk"]["bytes"], 10608)
        self.assertEqual(rows["external_package_with_vk"]["ratio_vs_nanozk_reported"], 1.537391)
        self.assertEqual(rows["native_d128_block_proof_object"]["status"], gate.NATIVE_PROOF_OBJECT_STATUS)
        self.assertIsNone(rows["native_d128_block_proof_object"]["bytes"])
        self.assertEqual(rows["external_nanozk_context"]["bytes"], 6900)
        self.assertTrue(all(row["can_support_native_claim"] is False for row in rows.values()))

    def test_mutations_reject_overclaims_and_drift(self) -> None:
        cases = {case["mutation"]: case for case in self.fresh_payload()["cases"]}
        for name in gate.MUTATION_NAMES:
            self.assertIn(name, cases)
            self.assertTrue(cases[name]["rejected"], name)
            self.assertFalse(cases[name]["accepted"], name)
            self.assertTrue(cases[name]["error"], name)
        self.assertIn("claim_guard", cases["matched_nanozk_claim_enabled"]["error"])
        self.assertIn("route_rows", cases["native_proof_bytes_smuggled"]["error"])
        self.assertIn("non_claims", cases["non_claim_removed"]["error"])

    def test_mutation_plan_failures_do_not_count_as_rejections(self) -> None:
        original = gate.mutation_plan

        def broken_plan(_name):
            def apply(_payload):
                raise RuntimeError("broken mutation plan")

            return apply

        try:
            gate.mutation_plan = broken_plan
            with self.assertRaisesRegex(gate.NativeD128BlockProofObjectRouteError, "mutation plan failed"):
                gate.mutation_cases(gate.build_core_payload())
        finally:
            gate.mutation_plan = original

    def test_validate_payload_rejects_recommitted_overclaim(self) -> None:
        payload = self.fresh_payload()
        payload["claim_guard"]["native_proof_size_claim_allowed"] = True
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.NativeD128BlockProofObjectRouteError, "claim_guard|claim guard"):
            gate.validate_payload(payload)

        payload = self.fresh_payload()
        for row in payload["route_rows"]:
            if row["row_id"] == "native_d128_block_proof_object":
                row["bytes"] = 4752
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaisesRegex(gate.NativeD128BlockProofObjectRouteError, "route_rows|native proof bytes"):
            gate.validate_payload(payload)

        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.NativeD128BlockProofObjectRouteError, "payload commitment drift"):
            gate.validate_payload(payload)

    def test_loader_rejects_duplicate_json_keys(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=gate.EVIDENCE_DIR,
            prefix="native-d128-route-duplicate-key-",
            suffix=".json",
            delete=False,
        ) as handle:
            path = pathlib.Path(handle.name)
            handle.write('{"value": 1, "value": 2}\n')
        try:
            with self.assertRaisesRegex(gate.NativeD128BlockProofObjectRouteError, "duplicate JSON key"):
                gate.load_json(path)
        finally:
            path.unlink(missing_ok=True)

    def test_tsv_and_write_outputs(self) -> None:
        payload = self.fresh_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn("row_id\tsurface\tstatus\tobject_class", tsv)
        self.assertIn("native_d128_block_proof_object", tsv)
        self.assertIn("external_package_without_vk", tsv)
        self.assertIn("external_package_with_vk", tsv)

        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_path = tmp / "native-d128-route.json"
            tsv_path = tmp / "native-d128-route.tsv"
            gate.write_outputs(payload, json_path, tsv_path)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), payload)
            self.assertIn("native_d128_block_proof_object", tsv_path.read_text(encoding="utf-8"))

            with self.assertRaisesRegex(gate.NativeD128BlockProofObjectRouteError, "failed|output path"):
                gate.write_outputs(payload, tmp / "bad.txt", None)

        with tempfile.TemporaryDirectory() as raw_tmp:
            with self.assertRaisesRegex(gate.NativeD128BlockProofObjectRouteError, "failed|evidence"):
                gate.write_outputs(payload, pathlib.Path(raw_tmp) / "outside.json", None)


if __name__ == "__main__":
    unittest.main()
