import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate_bad_phase37_artifacts.py"


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_json(path: pathlib.Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def run_generator(receipt_path: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(receipt_path),
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest_path = pathlib.Path(completed.stdout.strip())
    return manifest_path


def build_receipt() -> dict[str, object]:
    return {
        "phase": 37,
        "receipt_version": 1,
        "claim_is_valid": False,
        "source_binding_verified": True,
        "total_steps": 3,
        "receipt_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "required_field": "must disappear",
        "source_commitment": "0x1111111111111111111111111111111111111111111111111111111111111111",
        "final_commitment": "0x2222222222222222222222222222222222222222222222222222222222222222",
        "final_commitment_material": {
            "lanes": [1, 2, 3],
            "salt": "phase37",
        },
        "nested": {
            "claim_is_valid": False,
            "source_binding_verified": True,
            "total_steps": 8,
            "source_commitment": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        },
    }


class GenerateBadPhase37ArtifactsTest(unittest.TestCase):
    def test_deterministic_file_names_and_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir_path = pathlib.Path(tempdir)
            receipt_path = tempdir_path / "receipt.json"
            write_json(receipt_path, build_receipt())

            first_out = tempdir_path / "out_first"
            second_out = tempdir_path / "out_second"
            first_manifest = run_generator(receipt_path, first_out)
            second_manifest = run_generator(receipt_path, second_out)

            first = load_json(first_manifest)
            second = load_json(second_manifest)

            expected_files = [
                "phase37_bad_01_flip_false_claim_flag.json",
                "phase37_bad_02_flip_true_source_binding_flag.json",
                "phase37_bad_03_uppercase_hash.json",
                "phase37_bad_04_remove_required_field.json",
                "phase37_bad_05_add_unknown_field.json",
                "phase37_bad_06_zero_total_steps.json",
                "phase37_bad_07_tamper_final_commitment.json",
                "phase37_bad_08_drift_source_commitment.json",
            ]

            self.assertEqual(first["schema"], "phase37-bad-artifact-manifest-v1")
            self.assertEqual(first["mutation_count"], 8)
            self.assertEqual(
                [item["file_name"] for item in first["mutations"]],
                expected_files,
            )
            self.assertEqual(
                [item["file_name"] for item in second["mutations"]],
                expected_files,
            )
            self.assertEqual(
                [item["name"] for item in first["mutations"]],
                [item["name"] for item in second["mutations"]],
            )
            self.assertEqual(first["source_receipt"]["sha256"], second["source_receipt"]["sha256"])
            self.assertEqual(
                pathlib.Path(first["source_receipt"]["path"]),
                receipt_path.resolve(),
            )
            self.assertEqual(pathlib.Path(first["output_dir"]), first_out.resolve())

    def test_representative_mutations_apply_expected_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir_path = pathlib.Path(tempdir)
            receipt_path = tempdir_path / "receipt.json"
            write_json(receipt_path, build_receipt())
            output_dir = tempdir_path / "mutations"
            manifest_path = run_generator(receipt_path, output_dir)
            manifest = load_json(manifest_path)

            mutation_paths = {
                item["name"]: output_dir / item["file_name"]
                for item in manifest["mutations"]
            }

            false_claim = load_json(mutation_paths["flip_false_claim_flag"])
            self.assertTrue(false_claim["claim_is_valid"])
            self.assertFalse(false_claim["nested"]["claim_is_valid"])

            source_binding = load_json(mutation_paths["flip_true_source_binding_flag"])
            self.assertFalse(source_binding["source_binding_verified"])
            self.assertTrue(source_binding["nested"]["source_binding_verified"])

            uppercased = load_json(mutation_paths["uppercase_hash"])
            self.assertEqual(
                uppercased["receipt_hash"],
                "0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF",
            )

            removed = load_json(mutation_paths["remove_required_field"])
            self.assertNotIn("required_field", removed)

            added = load_json(mutation_paths["add_unknown_field"])
            self.assertIn("__phase37_unknown_field__", added)
            self.assertEqual(added["__phase37_unknown_field__"]["kind"], "unexpected")

            zeroed = load_json(mutation_paths["zero_total_steps"])
            self.assertEqual(zeroed["total_steps"], 0)
            self.assertEqual(zeroed["nested"]["total_steps"], 8)

            tampered = load_json(mutation_paths["tamper_final_commitment"])
            self.assertEqual(
                tampered["final_commitment"],
                "0x2222222222222222222222222222222222222222222222222222222222222220",
            )

            drifted = load_json(mutation_paths["drift_source_commitment"])
            self.assertEqual(
                drifted["source_commitment"],
                "0x1111111111111111111111111111111111111111111111111111111111111110",
            )
            expected_digest = hashlib.sha256(
                json.dumps(
                    build_receipt()["final_commitment_material"],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            self.assertEqual(drifted["final_commitment"], f"0x{expected_digest}")
            drift_entry = next(item for item in manifest["mutations"] if item["name"] == "drift_source_commitment")
            self.assertTrue(drift_entry["recomputed_final_commitment"])
            self.assertEqual(drift_entry["recompute_basis_path"], ["final_commitment_material"])


if __name__ == "__main__":
    unittest.main()
