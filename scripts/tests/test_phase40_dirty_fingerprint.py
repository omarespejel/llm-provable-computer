from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "phase40_dirty_fingerprint.py"


class Phase40DirtyFingerprintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_fingerprint(
        self, limit: int = 1024, cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(limit)],
            cwd=cwd or self.repo,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_reports_truncated_when_regular_dirty_file_exceeds_limit(self) -> None:
        (self.repo / "large.txt").write_bytes(b"x" * 128)

        result = self.run_fingerprint(limit=8)

        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertRegex(lines[0], r"^[0-9a-f]{64}$")
        self.assertEqual(lines[1], "true")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_hashes_symlink_text_without_following_target(self) -> None:
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_text("first outside content\n", encoding="utf-8")
        try:
            os.symlink(outside, self.repo / "outside-link")
        except OSError as error:
            self.skipTest(f"symlink creation not permitted: {error}")

        first = self.run_fingerprint()
        outside.write_text("changed outside content\n", encoding="utf-8")
        second = self.run_fingerprint()

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_git_errors_are_reported_without_traceback(self) -> None:
        not_repo = Path(self.tmp.name) / "not-repo"
        not_repo.mkdir()

        result = self.run_fingerprint(cwd=not_repo)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("git command failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unreadable_regular_dirty_file_fails_closed(self) -> None:
        unreadable = self.repo / "unreadable.txt"
        unreadable.write_text("secret\n", encoding="utf-8")
        unreadable.chmod(0)
        self.addCleanup(
            lambda: unreadable.exists() and unreadable.chmod(stat.S_IRUSR | stat.S_IWUSR)
        )
        if os.access(unreadable, os.R_OK):
            self.skipTest("test user can still read chmod 000 files")

        result = self.run_fingerprint()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed to read dirty file", result.stderr)


if __name__ == "__main__":
    unittest.main()
