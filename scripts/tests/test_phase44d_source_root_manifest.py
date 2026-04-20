from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_phase44d_source_root_manifest.py"
MANIFEST = ROOT / "docs" / "engineering" / "design" / "phase44d_source_root_manifest.json"

SPEC = importlib.util.spec_from_file_location("phase44d_checker", CHECKER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load Phase44D checker from {CHECKER}")
PHASE44D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PHASE44D)


class Phase44DSourceRootManifestTests(unittest.TestCase):
    def load_manifest(self) -> dict[str, object]:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_default_manifest_is_valid_and_binds_required_roots(self) -> None:
        manifest = self.load_manifest()
        validated = PHASE44D.validate_manifest(manifest)
        self.assertEqual(validated["issue_id"], 180)
        self.assertEqual(validated["source_surface_version"], PHASE44D.SOURCE_SURFACE_VERSION)
        self.assertEqual(validated["total_steps"], 8)
        self.assertEqual(validated["log_size"], 3)
        self.assertEqual(validated["source_root"], validated["source_emitted_root"])
        self.assertEqual(manifest["source_root_preimage"]["compact_root"], validated["compact_root"])

    def test_committed_manifest_is_canonical_json(self) -> None:
        manifest = self.load_manifest()
        raw = MANIFEST.read_text(encoding="utf-8")
        self.assertEqual(raw, PHASE44D.canonical_json(manifest) + "\n")

    def test_probe_accepts_manifest_and_all_internal_mutations_reject(self) -> None:
        manifest = self.load_manifest()
        evidence = PHASE44D.probe_manifest(manifest)
        self.assertEqual(evidence["schema"], PHASE44D.EVIDENCE_SCHEMA)
        self.assertEqual(evidence["probe"], PHASE44D.PROBE)
        self.assertEqual(evidence["source_root"], evidence["source_emitted_root"])
        self.assertEqual(len(evidence["mutation_results"]), len(PHASE44D.KILL_LABELS))
        self.assertTrue(all(result["rejected"] for result in evidence["mutation_results"]))

    def test_each_declared_kill_label_rejects(self) -> None:
        manifest = self.load_manifest()
        self.assertEqual(tuple(manifest["kill_labels"]), PHASE44D.KILL_LABELS)
        for label in manifest["kill_labels"]:
            with self.subTest(label=label):
                mutated = PHASE44D.apply_mutation(manifest, label)
                with self.assertRaises(PHASE44D.Phase44DError):
                    PHASE44D.validate_manifest(mutated)

    def test_missing_top_level_fields_reject(self) -> None:
        manifest = self.load_manifest()
        for field in PHASE44D.TOP_LEVEL_KEYS:
            with self.subTest(field=field):
                mutated = copy.deepcopy(manifest)
                mutated.pop(field, None)
                with self.assertRaises(PHASE44D.Phase44DError):
                    PHASE44D.validate_manifest(mutated)

    def test_extra_top_level_field_rejects(self) -> None:
        manifest = self.load_manifest()
        manifest["unbound_debug_field"] = "must-not-be-accepted"
        with self.assertRaises(PHASE44D.Phase44DError):
            PHASE44D.validate_manifest(manifest)

    def test_compact_and_source_row_reordering_reject(self) -> None:
        manifest = self.load_manifest()
        compact_reordered = copy.deepcopy(manifest)
        compact_reordered["compact_root_preimage"]["compact_rows"] = list(
            reversed(compact_reordered["compact_root_preimage"]["compact_rows"])
        )
        with self.assertRaises(PHASE44D.Phase44DError):
            PHASE44D.validate_manifest(compact_reordered)

        source_reordered = copy.deepcopy(manifest)
        source_reordered["source_root_preimage"]["source_rows"] = list(
            reversed(source_reordered["source_root_preimage"]["source_rows"])
        )
        with self.assertRaises(PHASE44D.Phase44DError):
            PHASE44D.validate_manifest(source_reordered)

    def test_build_default_manifest_rejects_non_power_of_two_steps(self) -> None:
        with self.assertRaises(PHASE44D.Phase44DError):
            PHASE44D.build_default_manifest(7)

    def test_larger_power_of_two_manifest_remains_canonical(self) -> None:
        manifest = PHASE44D.build_default_manifest(16)
        validated = PHASE44D.validate_manifest(manifest)
        self.assertEqual(validated["total_steps"], 16)
        self.assertEqual(validated["log_size"], 4)
        self.assertEqual(
            manifest["compact_root_preimage"]["compact_rows"],
            PHASE44D.expected_compact_rows(16),
        )
        self.assertEqual(
            manifest["source_root_preimage"]["source_rows"],
            PHASE44D.expected_source_rows(16),
        )

    def test_replayed_expected_rows_reject_for_larger_manifest(self) -> None:
        manifest = PHASE44D.build_default_manifest(16)
        compact_replayed = copy.deepcopy(manifest)
        compact_replayed["compact_root_preimage"]["compact_rows"][9] = "phase44d/compact/replayed-step-9"
        with self.assertRaises(PHASE44D.Phase44DError):
            PHASE44D.validate_manifest(compact_replayed)

        source_replayed = copy.deepcopy(manifest)
        source_replayed["source_root_preimage"]["source_rows"][9] = "phase44d/source/replayed-step-9"
        with self.assertRaises(PHASE44D.Phase44DError):
            PHASE44D.validate_manifest(source_replayed)

    def test_source_emitted_root_drift_rejects(self) -> None:
        manifest = self.load_manifest()
        manifest["source_emitted_root"] = "0" * 64
        with self.assertRaises(PHASE44D.Phase44DError):
            PHASE44D.validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
