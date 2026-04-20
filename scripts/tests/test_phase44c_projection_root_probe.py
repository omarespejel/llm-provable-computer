from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_phase44c_projection_root_probe.py"
MANIFEST = ROOT / "docs" / "engineering" / "design" / "phase44c-projection-root-manifest.json"
STWO_ROOT = pathlib.Path("/tmp/zkai-research/repos/stwo")

SPEC = importlib.util.spec_from_file_location("phase44c_checker", CHECKER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load Phase44C checker from {CHECKER}")
PHASE44C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PHASE44C)


class Phase44CProjectionRootProbeTests(unittest.TestCase):
    def test_manifest_shape_is_bounded_and_canonical(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], PHASE44C.SCHEMA)
        self.assertEqual(manifest["probe"], PHASE44C.PROBE)
        self.assertEqual(manifest["source_surface_version"], PHASE44C.PHASE43_SURFACE_VERSION)
        self.assertEqual(manifest["projection_row_count"], 8)
        self.assertEqual(manifest["projection_log_size"], 3)
        self.assertEqual(len(manifest["canonical_source_root_preimage"]["row_labels"]), 8)

    def test_probe_accepts_canonical_manifest_and_writes_evidence(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tempdir:
            output = pathlib.Path(tempdir) / "evidence.json"
            evidence = PHASE44C.probe_manifest(manifest, STWO_ROOT)
            PHASE44C.write_json(output, evidence)
            round_tripped = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(round_tripped["probe"], PHASE44C.PROBE)
            self.assertEqual(round_tripped["projection_row_count"], 8)
            self.assertEqual(round_tripped["projection_log_size"], 3)
            self.assertEqual(round_tripped["source_emitted_projection_root"], round_tripped["canonical_source_root"])
            self.assertEqual(len(round_tripped["kill_results"]), len(manifest["mutation_checks"]))


    def test_probe_rejects_tampered_source_emitted_root(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["source_emitted_projection_root"] = "0" * 64
        with self.assertRaises(PHASE44C.Phase44CError):
            PHASE44C.probe_manifest(manifest, STWO_ROOT)

    def test_each_kill_label_rejects(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for mutation in manifest["mutation_checks"]:
            with self.subTest(label=mutation["label"]):
                mutated = PHASE44C.apply_mutation(manifest, mutation["label"])
                trimmed = {
                    **mutated,
                    "kill_labels": [mutation["label"]],
                    "mutation_checks": [mutation],
                }
                with self.assertRaises(PHASE44C.Phase44CError):
                    PHASE44C.probe_manifest(trimmed, STWO_ROOT)

    def test_stwo_source_mechanics_are_verified(self) -> None:
        mechanics = PHASE44C.load_stwo_source_mechanics(STWO_ROOT)
        self.assertIn("pcs_mix_root", mechanics)
        self.assertIn("twiddle_root_coset", mechanics)
        self.assertIn("accumulation_root_coset", mechanics)
        self.assertTrue((STWO_ROOT / "crates/stwo/src/prover/pcs/mod.rs").exists())


if __name__ == "__main__":
    unittest.main()
