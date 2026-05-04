from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_snark_receipt_timing_setup_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_snark_receipt_timing_setup_gate", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load d128 SNARK timing gate from {SCRIPT_PATH}")
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


def fake_measurements() -> dict:
    public_hash = GATE.sha256_file(GATE.SOURCE_PUBLIC)
    public_payload_hash = GATE.sha256_bytes(GATE.canonical_json_bytes(GATE.load_json(GATE.SOURCE_PUBLIC)))
    return {
        "tool_versions": {
            "snarkjs": f"snarkjs@{GATE.SNARKJS_VERSION}",
            "circom": f"circom compiler {GATE.CIRCOM_VERSION}",
            "node": GATE.NODE_VERSION,
            "npm": GATE.NPM_VERSION,
        },
        "setup_metadata": {
            "setup_time_ms_single_run": 1234.567,
            "r1cs_sha256": "a" * 64,
            "wasm_sha256": "b" * 64,
            "verification_key_sha256": "c" * 64,
            "verification_key_file_sha256": "d" * 64,
            "verification_key_bytes": 5855,
        },
        "proof_generation": {
            "sample_count": 5,
            "median_ms": 3.0,
            "min_ms": 1.0,
            "max_ms": 5.0,
            "all_samples_ms": [1.0, 2.0, 3.0, 4.0, 5.0],
        },
        "verification": {
            "sample_count": 5,
            "median_ms": 8.0,
            "min_ms": 6.0,
            "max_ms": 10.0,
            "all_samples_ms": [6.0, 7.0, 8.0, 9.0, 10.0],
        },
        "artifact_binding": {
            "source_public_sha256": public_hash,
            "source_public_payload_sha256": public_payload_hash,
            "source_proof_bytes": GATE.SOURCE_PROOF.stat().st_size,
            "source_verification_key_bytes": GATE.SOURCE_VK.stat().st_size,
            "generated_public_payload_sha256_values": [public_payload_hash],
            "generated_proof_file_sha256_values": ["e" * 64, "f" * 64],
            "generated_proof_size_bytes_values": [802],
            "generated_verification_key_file_sha256": "d" * 64,
        },
    }


class D128SnarkReceiptTimingSetupGateTests(unittest.TestCase):
    def payload(self) -> dict:
        return GATE.build_payload(fake_measurements())

    def test_gate_records_go_with_timing_and_setup_scope(self) -> None:
        payload = self.payload()
        GATE.validate_payload(payload)

        self.assertEqual(payload["decision"], GATE.DECISION)
        self.assertEqual(payload["result"], "GO")
        self.assertEqual(payload["issue"], 430)
        self.assertEqual(payload["source_receipt"]["issue"], 428)
        self.assertFalse(payload["setup_policy"]["production_trusted_setup"])
        self.assertEqual(payload["timing_metrics"]["sample_count"], 5)
        self.assertEqual(payload["timing_metrics"]["proof_generation_time_ms_median"], 3.0)
        self.assertEqual(payload["timing_metrics"]["verifier_time_ms_median"], 8.0)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["case_count"], len(GATE.EXPECTED_MUTATION_INVENTORY))

    def test_rejects_source_receipt_relabeling(self) -> None:
        payload = self.payload()
        core = GATE._core_payload(payload)
        core["source_receipt"]["claim_boundary"] = "RECURSION_PROVEN"

        with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, "source receipt mismatch") as err:
            GATE.validate_core_payload(core)

        self.assertEqual(err.exception.layer, "source_receipt")

    def test_rejects_setup_policy_promotion(self) -> None:
        payload = self.payload()
        core = GATE._core_payload(payload)
        core["setup_policy"]["production_trusted_setup"] = True

        with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, "setup policy mismatch") as err:
            GATE.validate_core_payload(core)

        self.assertEqual(err.exception.layer, "setup_policy")

    def test_rejects_timing_metric_relabeling(self) -> None:
        payload = self.payload()
        core = GATE._core_payload(payload)
        core["timing_metrics"]["verifier_time_ms_median"] = 0.001

        with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, "verifier median mismatch") as err:
            GATE.validate_core_payload(core)

        self.assertEqual(err.exception.layer, "timing_metrics")
        cases = {case["mutation"]: case for case in payload["cases"]}
        self.assertTrue(cases["verifier_metric_smuggled"]["rejected"])
        self.assertEqual(cases["verifier_metric_smuggled"]["rejection_layer"], "timing_metrics")

    def test_rejects_node_and_npm_version_relabeling(self) -> None:
        payload = self.payload()
        for field in ("node", "npm"):
            with self.subTest(field=field):
                core = GATE._core_payload(payload)
                core["tool_versions"][field] = "tampered"
                with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, f"{field} version mismatch") as err:
                    GATE.validate_core_payload(core)
                self.assertEqual(err.exception.layer, "external_proof_tooling")

        cases = {case["mutation"]: case for case in payload["cases"]}
        self.assertTrue(cases["node_version_relabeling"]["rejected"])
        self.assertEqual(cases["node_version_relabeling"]["rejection_layer"], "external_proof_tooling")
        self.assertTrue(cases["npm_version_relabeling"]["rejected"])
        self.assertEqual(cases["npm_version_relabeling"]["rejection_layer"], "external_proof_tooling")

    def test_rejects_repro_command_relabeling(self) -> None:
        payload = self.payload()
        core = GATE._core_payload(payload)
        core["repro"]["command"] = "python3 scripts/fake.py"

        with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, "repro command mismatch") as err:
            GATE.validate_core_payload(core)

        self.assertEqual(err.exception.layer, "parser_or_schema")
        cases = {case["mutation"]: case for case in payload["cases"]}
        self.assertTrue(cases["repro_command_relabeling"]["rejected"])

    def test_rejects_artifact_binding_drift(self) -> None:
        payload = self.payload()
        core = GATE._core_payload(payload)
        core["artifact_binding"]["generated_public_payload_sha256_values"] = ["0" * 64]

        with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, "generated public hashes mismatch") as err:
            GATE.validate_core_payload(core)

        self.assertEqual(err.exception.layer, "artifact_binding")

    def test_tsv_contains_timing_rows(self) -> None:
        tsv = GATE.to_tsv(self.payload())
        self.assertIn("proof_generation", tsv)
        self.assertIn("verification", tsv)
        self.assertIn("setup", tsv)
        self.assertEqual(tsv.splitlines()[0].split("\t"), list(GATE.TSV_COLUMNS))
        rows = {line.split("\t")[0]: line.split("\t") for line in tsv.splitlines()[1:]}
        self.assertEqual(set(rows), {"setup", "proof_generation", "verification"})
        self.assertEqual(rows["setup"][1], "1")
        self.assertEqual(rows["setup"][2], "1234.567")

    def test_output_path_must_stay_under_evidence_dir(self) -> None:
        with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, "output path must stay"):
            GATE.write_text_checked(ROOT / "outside.json", "{}\n")

    def test_rejects_identical_output_paths(self) -> None:
        same = pathlib.Path("docs/engineering/evidence/same-output")
        with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, "outputs must be distinct") as err:
            GATE.resolve_output_paths(same, same)
        self.assertEqual(err.exception.layer, "output_path")

    def test_rejects_output_directory_paths(self) -> None:
        with self.assertRaisesRegex(GATE.D128SnarkTimingSetupError, "not a directory") as err:
            GATE.resolve_output_path(GATE.EVIDENCE_DIR)
        self.assertEqual(err.exception.layer, "output_path")

    def test_write_outputs_round_trip(self) -> None:
        payload = self.payload()
        with tempfile.TemporaryDirectory(dir=GATE.EVIDENCE_DIR) as raw_tmp:
            path = pathlib.Path(raw_tmp) / "timing.json"
            GATE.write_text_checked(path, json.dumps(payload, sort_keys=True))
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["decision"], GATE.DECISION)


if __name__ == "__main__":
    unittest.main()
