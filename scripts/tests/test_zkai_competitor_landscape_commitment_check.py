from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_competitor_landscape_commitment_check.py"
EVIDENCE_PATH = ROOT / "docs" / "engineering" / "evidence" / "zkai-competitor-landscape-2026-05.json"
SPEC = importlib.util.spec_from_file_location("zkai_competitor_landscape_commitment_check", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load competitor landscape commitment checker from {SCRIPT_PATH}")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class ZkAiCompetitorLandscapeCommitmentCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with EVIDENCE_PATH.open("r", encoding="utf-8") as handle:
            cls.payload = json.load(handle)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_checked_in_evidence_commitment_matches_systems(self) -> None:
        self.assertEqual(
            CHECK.check_path(EVIDENCE_PATH),
            self.payload["systems_commitment"],
        )

    def test_rejects_stale_commitment_after_system_edit(self) -> None:
        payload = self.fresh_payload()
        payload["systems"][0]["name"] = "NANOZK drift"

        with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "systems commitment mismatch"):
            CHECK.validate_payload(payload)

    def test_rejects_malformed_commitment_fields(self) -> None:
        payload = self.fresh_payload()
        payload["systems_commitment_domain"] = ""
        with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "domain"):
            CHECK.validate_payload(payload)

        payload = self.fresh_payload()
        payload["systems_commitment"] = "sha256:" + "00" * 32
        with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "blake2b-256"):
            CHECK.validate_payload(payload)

    def test_rejects_schema_and_domain_drift_after_recommit(self) -> None:
        payload = self.fresh_payload()
        payload["schema_version"] = True
        with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "schema_version"):
            CHECK.validate_payload(payload)

        payload = self.fresh_payload()
        payload["schema"] = "zkai-competitor-landscape-v2"
        with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "schema"):
            CHECK.validate_payload(payload)

        payload = self.fresh_payload()
        payload["systems_commitment_domain"] = "ptvm:zkai:competitor-landscape:systems:v2"
        payload["systems_commitment"] = CHECK.systems_commitment(
            payload["systems"],
            payload["systems_commitment_domain"],
        )
        with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "domain"):
            CHECK.validate_payload(payload)

    def test_rejects_symlink_evidence_path(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            real = tmp / "real.json"
            link = tmp / "link.json"
            real.write_text(json.dumps(payload), encoding="utf-8")
            link.symlink_to(real)

            with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "must not traverse symlinks"):
                CHECK.check_path(link)
            self.assertEqual(CHECK.main(["--evidence", str(link)]), 1)

    def test_rejects_symlink_parent_path(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_dir:
            tmp = pathlib.Path(tmp_dir)
            real_dir = tmp / "real"
            real_dir.mkdir()
            real = real_dir / "landscape.json"
            link_dir = tmp / "linked"
            real.write_text(json.dumps(payload), encoding="utf-8")
            link_dir.symlink_to(real_dir, target_is_directory=True)

            with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "must not traverse symlinks"):
                CHECK.check_path(link_dir / "landscape.json")

    def test_main_returns_error_for_unreadable_or_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_dir:
            path = pathlib.Path(tmp_dir) / "bad.json"
            path.write_bytes(b"\xff")
            self.assertEqual(CHECK.main(["--evidence", str(path)]), 1)

    def test_rejects_oversized_evidence_before_json_decode(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_dir:
            path = pathlib.Path(tmp_dir) / "oversized.json"
            path.write_text(" " * (CHECK.MAX_EVIDENCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(CHECK.CompetitorLandscapeCommitmentError, "exceeds max size"):
                CHECK.check_path(path)

    def test_rejects_evidence_path_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir) / "landscape.json"
            path.write_text(json.dumps(self.fresh_payload()), encoding="utf-8")
            self.assertEqual(CHECK.main(["--evidence", str(path)]), 1)

    def test_cli_accepts_explicit_evidence_path(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_dir:
            path = pathlib.Path(tmp_dir) / "landscape.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(CHECK.main(["--evidence", str(path)]), 0)


if __name__ == "__main__":
    unittest.main()
