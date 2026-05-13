import copy
import json
import tempfile
import unittest

from scripts import zkai_paper_claim_pack_gate as gate


class PaperClaimPackGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = gate.build_payload()
        gate.validate_payload(self.payload)

    def test_binds_narrow_thesis_and_non_claims(self):
        self.assertEqual(self.payload["decision"], gate.DECISION)
        self.assertIn("STARK-native proof-architecture", self.payload["go_posture"][0])
        self.assertIn("not full inference", self.payload["non_claims"])
        self.assertIn("not public benchmark", self.payload["non_claims"])
        self.assertIn("not production-ready", self.payload["non_claims"])
        self.assertIn("not exact real-valued Softmax", self.payload["non_claims"])
        self.assertEqual(self.payload["no_go_posture"], gate.NO_GO_POSTURE)

    def test_referenced_evidence_paths_exist(self):
        paths = [gate.ROOT / ref["path"] for ref in self.payload["evidence_refs"]]
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            self.assertTrue(path.is_file(), path)

    def test_all_declared_mutations_reject(self):
        expected = set(gate.EXPECTED_MUTATION_NAMES)
        actual = {name for name, _ in gate.mutation_cases(self.payload)}
        self.assertEqual(actual, expected)
        self.assertIn("no_go_posture_removed", actual)
        for name, mutated in gate.mutation_cases(self.payload):
            with self.assertRaises(gate.ClaimPackGateError, msg=name):
                gate.validate_payload(mutated)

    def test_rejects_no_go_posture_drift_even_when_commitment_is_refreshed(self):
        mutated = copy.deepcopy(self.payload)
        mutated["no_go_posture"] = mutated["no_go_posture"][1:]
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(gate.ClaimPackGateError, "no_go_posture drift"):
            gate.validate_payload(mutated)

    def test_rejects_positive_overclaims_even_when_commitment_is_refreshed(self):
        for text in [
            "This proves full inference.",
            "This is exact Softmax.",
            "This is a public benchmark.",
            "This is production-ready.",
        ]:
            mutated = copy.deepcopy(self.payload)
            mutated["paper_claims"][0] = text
            mutated["payload_commitment"] = gate.payload_commitment(mutated)
            with self.assertRaisesRegex(gate.ClaimPackGateError, "positive claim overclaim"):
                gate.validate_payload(mutated)

    def test_rejects_missing_evidence_even_when_commitment_is_refreshed(self):
        mutated = copy.deepcopy(self.payload)
        mutated["evidence_refs"][0]["path"] = "docs/engineering/evidence/does-not-exist.json"
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(gate.ClaimPackGateError, "missing evidence path"):
            gate.validate_payload(mutated)

    def test_rejects_symlinked_evidence_parent_even_when_commitment_is_refreshed(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside_dir = gate.pathlib.Path(tmp) / "outside"
            outside_dir.mkdir()
            (outside_dir / "ok.json").write_text("{}", encoding="utf-8")
            with tempfile.NamedTemporaryFile(
                dir=gate.ROOT / "docs" / "engineering",
                prefix="claim-pack-evidence-link-",
                delete=False,
            ) as handle:
                link = gate.pathlib.Path(handle.name)
            link.unlink()
            try:
                link.symlink_to(outside_dir, target_is_directory=True)
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            try:
                mutated = copy.deepcopy(self.payload)
                mutated["evidence_refs"][0]["path"] = (link.relative_to(gate.ROOT) / "ok.json").as_posix()
                mutated["payload_commitment"] = gate.payload_commitment(mutated)
                with self.assertRaisesRegex(gate.ClaimPackGateError, "symlink components"):
                    gate.validate_payload(mutated)
            finally:
                link.unlink(missing_ok=True)

    def test_write_json_round_trip(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.ALLOWED_OUTPUT_DIR,
            prefix="claim-pack-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            path = gate.pathlib.Path(handle.name)
        path.unlink()
        try:
            gate.write_json(path.relative_to(gate.ROOT), self.payload)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, self.payload)
        finally:
            path.unlink(missing_ok=True)

    def test_write_json_rejects_symlink_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = gate.pathlib.Path(tmp)
            target = tmp_path / "target.json"
            target.write_text("{}", encoding="utf-8")
            with tempfile.NamedTemporaryFile(
                dir=gate.ALLOWED_OUTPUT_DIR,
                prefix="claim-pack-link-",
                suffix=".json",
                delete=False,
            ) as handle:
                link = gate.pathlib.Path(handle.name)
            link.unlink()
            try:
                link.symlink_to(target)
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            try:
                with self.assertRaisesRegex(gate.ClaimPackGateError, "output path must not be a symlink"):
                    gate.write_json(link.relative_to(gate.ROOT), self.payload)
            finally:
                link.unlink(missing_ok=True)

    def test_write_json_rejects_outside_repo_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.ClaimPackGateError, "output path must be repo-relative"):
                gate.write_json(gate.pathlib.Path(tmp) / "claim-pack.json", self.payload)

    def test_write_json_rejects_drive_qualified_output(self):
        with self.assertRaisesRegex(gate.ClaimPackGateError, "output path must be repo-relative"):
            gate.write_json(gate.pathlib.Path(r"C:\tmp\claim-pack.json"), self.payload)

    def test_write_json_accepts_backslash_relative_output(self):
        with tempfile.NamedTemporaryFile(
            dir=gate.ALLOWED_OUTPUT_DIR,
            prefix="claim-pack-backslash-test-",
            suffix=".json",
            delete=False,
        ) as handle:
            path = gate.pathlib.Path(handle.name)
        path.unlink()
        relative = path.relative_to(gate.ROOT)
        backslash_relative = gate.pathlib.Path("\\".join(relative.parts))
        try:
            gate.write_json(backslash_relative, self.payload)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, self.payload)
        finally:
            path.unlink(missing_ok=True)

    def test_write_json_rejects_outside_allowed_output_dir(self):
        with self.assertRaisesRegex(gate.ClaimPackGateError, "output path must stay under docs/paper/evidence"):
            gate.write_json(gate.pathlib.Path("docs/engineering/evidence/claim-pack.json"), self.payload)

    def test_write_json_rejects_symlink_output_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside_dir = gate.pathlib.Path(tmp) / "outside"
            outside_dir.mkdir()
            with tempfile.NamedTemporaryFile(
                dir=gate.ALLOWED_OUTPUT_DIR,
                prefix="claim-pack-parent-link-",
                delete=False,
            ) as handle:
                link = gate.pathlib.Path(handle.name)
            link.unlink()
            try:
                link.symlink_to(outside_dir, target_is_directory=True)
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            try:
                with self.assertRaisesRegex(gate.ClaimPackGateError, "symlink components"):
                    gate.write_json((link / "claim-pack.json").relative_to(gate.ROOT), self.payload)
            finally:
                link.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
