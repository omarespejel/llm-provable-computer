from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_benchmarks.py"
SPEC = importlib.util.spec_from_file_location("run_benchmarks", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load benchmark harness module from {MODULE_PATH}")
harness = importlib.util.module_from_spec(SPEC)
sys.modules["run_benchmarks"] = harness
SPEC.loader.exec_module(harness)


class BenchmarkHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old_repo_root = harness.repo_root
        harness.repo_root = lambda: self.root

    def tearDown(self) -> None:
        harness.repo_root = self.old_repo_root
        self.tmp.cleanup()

    def write_manifest(self, payload: dict) -> Path:
        path = self.root / "cases.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def valid_case(self, **overrides: object) -> dict:
        case = {"name": "case-a", "command": [sys.executable, "--version"]}
        case.update(overrides)
        return case

    def test_rejects_unsupported_manifest_version(self) -> None:
        manifest = self.write_manifest({"version": 2, "cases": [self.valid_case()]})

        with self.assertRaisesRegex(ValueError, "unsupported case manifest version"):
            harness.load_case_manifest(manifest)

    def test_rejects_non_finite_timeout(self) -> None:
        manifest = self.write_manifest(
            {"version": 1, "cases": [self.valid_case(timeout_s=float("nan"))]}
        )

        with self.assertRaisesRegex(ValueError, "timeout_s must be finite and > 0"):
            harness.load_case_manifest(manifest)

    def test_rejects_non_boolean_allow_failure(self) -> None:
        manifest = self.write_manifest(
            {"version": 1, "cases": [self.valid_case(allow_failure="yes")]}
        )

        with self.assertRaisesRegex(ValueError, "allow_failure must be boolean"):
            harness.load_case_manifest(manifest)

    def test_rejects_paths_that_escape_repo_root(self) -> None:
        manifest = self.write_manifest(
            {
                "version": 1,
                "cases": [
                    self.valid_case(cwd="../outside", inputs=["benchmarks/cases.json"]),
                ],
            }
        )
        with self.assertRaisesRegex(ValueError, "cwd escapes repo root"):
            harness.load_case_manifest(manifest)

        manifest = self.write_manifest(
            {
                "version": 1,
                "cases": [
                    self.valid_case(inputs=[{"path": "../outside.txt"}]),
                ],
            }
        )
        with self.assertRaisesRegex(ValueError, "input escapes repo root"):
            harness.load_case_manifest(manifest)

    def test_dry_run_does_not_hash_or_require_declared_inputs(self) -> None:
        manifest = self.write_manifest(
            {
                "version": 1,
                "cases": [
                    self.valid_case(inputs=["missing/input.json"]),
                ],
            }
        )
        _, cases = harness.load_case_manifest(manifest)

        result = harness.run_case(cases[0], run_root=self.root / "logs", dry_run=True)

        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(result["inputs"][0]["exists"], None)
        self.assertEqual(result["inputs"][0]["sha256"], None)
        self.assertEqual(result["inputs"][0]["hashing"], "deferred-until-run")
        self.assertFalse((self.root / "logs").exists())

    def test_case_log_directories_are_collision_resistant(self) -> None:
        manifest = self.write_manifest(
            {
                "version": 1,
                "cases": [
                    self.valid_case(name="case@1"),
                    self.valid_case(name="case#1"),
                ],
            }
        )
        _, cases = harness.load_case_manifest(manifest)

        log_dirs = [case.log_dir_name for case in cases]

        self.assertEqual(len(set(log_dirs)), 2)
        self.assertTrue(log_dirs[0].startswith("001-case_1-"))
        self.assertTrue(log_dirs[1].startswith("002-case_1-"))

    def test_stream_copy_records_hash_and_size(self) -> None:
        payload = (b"abc123" * 200000) + b"tail"
        output = self.root / "out.bin"
        with tempfile.TemporaryFile() as handle:
            handle.write(payload)
            digest, size = harness.copy_temp_file_to_path_and_hash(handle, output)

        self.assertEqual(size, len(payload))
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
        self.assertEqual(output.read_bytes(), payload)

    def test_timeout_is_recorded_as_failed_run(self) -> None:
        case = harness.CaseSpec(
            name="timeout-case",
            command=[sys.executable, "-c", "import time; time.sleep(2)"],
            timeout_s=0.05,
            allow_failure=True,
            log_dir_name="timeout-case",
        )

        result = harness.run_case(case, run_root=self.root / "logs", dry_run=False)

        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["runs"][0]["timed_out"])
        self.assertNotEqual(result["runs"][0]["returncode"], 0)
        self.assertTrue(Path(result["runs"][0]["stdout_path"]).exists())


if __name__ == "__main__":
    unittest.main()
