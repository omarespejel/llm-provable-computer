from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "collect_release_evidence.py"
SPEC = importlib.util.spec_from_file_location("collect_release_evidence", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load release evidence module from {MODULE_PATH}")
release = importlib.util.module_from_spec(SPEC)
sys.modules["collect_release_evidence"] = release
SPEC.loader.exec_module(release)


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "release-evidence.schema.json").write_text(
            '{"schema_version": 1}\n', encoding="utf-8"
        )
        (self.root / "target" / "local-hardening" / "pr-1").mkdir(parents=True)
        (self.root / "target" / "local-hardening" / "pr-1" / "logs").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_gate_evidence(self, *, head_sha: str = "a" * 40) -> Path:
        log_path = self.root / "target" / "local-hardening" / "pr-1" / "logs" / "smoke.log"
        log_path.write_text("smoke passed\n", encoding="utf-8")
        log_hash = release.sha256_file(log_path)
        evidence_path = self.root / "target" / "local-hardening" / "pr-1" / "evidence.json"
        payload = {
            "repo": "omarespejel/provable-transformer-vm",
            "pr_number": 1,
            "pr_url": "https://example.invalid/pr/1",
            "base_sha": "b" * 40,
            "head_sha": head_sha,
            "run_mode": "smoke",
            "quiet_seconds": 360,
            "review_gate": {"active_threads": 0},
            "local_commands": [
                {
                    "name": "smoke",
                    "command": "true",
                    "exit_code": 0,
                    "log_file": str(log_path.relative_to(self.root)),
                    "log_sha256": log_hash,
                }
            ],
        }
        evidence_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return evidence_path

    def valid_payload(self) -> dict:
        gate_path = self.write_gate_evidence()
        merge_gate = release.collect_merge_gate_evidence(gate_path, self.root)
        payload = {
            "schema_version": 1,
            "generated_at": "2026-04-18T00:00:00Z",
            "checkpoint": {"name": "unit", "kind": "paper-release"},
            "repo_root": str(self.root),
            "bundle_schema": release.file_record(
                self.root / "spec" / "release-evidence.schema.json",
                self.root,
                role="release_evidence_schema",
            ),
            "git": {
                "head_sha": "a" * 40,
                "branch": "test",
                "remote_origin": None,
                "remote_origin_had_credentials": False,
                "dirty": False,
                "status_sha256": release.sha256_bytes(b""),
                "clean_ignored_prefixes": [],
            },
            "toolchain": {
                "python": "3.test",
                "python_executable": sys.executable,
                "rustc": None,
                "cargo": None,
                "rustup_active_toolchain": None,
            },
            "host": {
                "system": "test",
                "release": "test",
                "machine": "test",
                "platform": "test",
                "processor": "test",
            },
            "merge_gate_evidence": [merge_gate],
            "benchmark_results": [],
            "artifacts": [],
            "schema_artifacts": [],
            "non_claims": ["Does not claim external attestation verification."],
        }
        return release.add_bundle_digest(payload)

    def write_bundle(self, payload: dict) -> Path:
        path = self.root / "release-evidence.json"
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return path

    def test_valid_bundle_passes_validation(self) -> None:
        path = self.write_bundle(self.valid_payload())

        self.assertEqual(release.validate_release_evidence(path), [])

    def test_rejects_tampered_command_log(self) -> None:
        path = self.write_bundle(self.valid_payload())
        log_path = self.root / "target" / "local-hardening" / "pr-1" / "logs" / "smoke.log"
        log_path.write_text("tampered\n", encoding="utf-8")

        errors = release.validate_release_evidence(path)

        self.assertTrue(any("sha256 does not match log bytes" in error for error in errors))

    def test_rejects_bundle_digest_drift(self) -> None:
        payload = self.valid_payload()
        payload["checkpoint"]["name"] = "changed-after-digest"
        path = self.write_bundle(payload)

        errors = release.validate_release_evidence(path)

        self.assertTrue(any("bundle_digest.sha256" in error for error in errors))

    def test_rejects_command_log_drift_from_evidence_json(self) -> None:
        payload = self.valid_payload()
        payload["merge_gate_evidence"][0]["command_logs"][0]["path"] = "different.log"
        payload = release.add_bundle_digest(payload)
        path = self.write_bundle(payload)

        errors = release.validate_release_evidence(path)

        self.assertTrue(
            any("does not match evidence local_commands log_file" in error for error in errors)
        )

    def test_rejects_base_sha_drift_from_evidence_json(self) -> None:
        payload = self.valid_payload()
        payload["merge_gate_evidence"][0]["base_sha"] = "c" * 40
        payload = release.add_bundle_digest(payload)
        path = self.write_bundle(payload)

        errors = release.validate_release_evidence(path)

        self.assertTrue(any("base_sha does not match evidence file" in error for error in errors))

    def test_collect_merge_gate_rejects_bad_recorded_log_hash(self) -> None:
        gate_path = self.write_gate_evidence()
        payload = json.loads(gate_path.read_text(encoding="utf-8"))
        payload["local_commands"][0]["log_sha256"] = "0" * 64
        gate_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaisesRegex(release.ReleaseEvidenceError, "log hash mismatch"):
            release.collect_merge_gate_evidence(gate_path, self.root)

    def test_rejects_relocated_bundle_without_evidence_sidecars(self) -> None:
        path = self.write_bundle(self.valid_payload())
        relocated = self.root / "relocated" / "release-evidence.json"
        relocated.parent.mkdir()
        shutil.copy2(path, relocated)
        shutil.rmtree(self.root / "target")

        errors = release.validate_release_evidence(relocated)

        self.assertTrue(any("path does not exist" in error for error in errors))

    def test_rejects_bundle_with_no_merge_gate_evidence(self) -> None:
        payload = self.valid_payload()
        payload["merge_gate_evidence"] = []
        payload = release.add_bundle_digest(payload)
        path = self.write_bundle(payload)

        errors = release.validate_release_evidence(path)

        self.assertTrue(any("merge_gate_evidence" in error for error in errors))

    def test_sanitizes_remote_url_credentials(self) -> None:
        sanitized, had_credentials = release.sanitize_remote_url(
            "https://token@example.com/org/repo.git"
        )

        self.assertEqual(sanitized, "https://example.com/org/repo.git")
        self.assertTrue(had_credentials)

    def test_live_benchmark_validation_does_not_execute_bundle_repo_root(self) -> None:
        payload = self.valid_payload()
        benchmark_path = self.root / "benchmark.json"
        benchmark_path.write_text('{"not": "a benchmark result"}\n', encoding="utf-8")
        marker_path = self.root / "validator-was-run"
        malicious_validator = self.root / "benchmarks" / "validate_benchmark_result.py"
        malicious_validator.parent.mkdir()
        malicious_validator.write_text(
            f"from pathlib import Path\nPath({str(marker_path)!r}).write_text('ran')\n",
            encoding="utf-8",
        )
        payload["benchmark_results"] = [
            {
                "result_file": release.file_record(
                    benchmark_path,
                    self.root,
                    role="benchmark_result",
                ),
                "validator": {
                    "command": [sys.executable, str(malicious_validator), str(benchmark_path)],
                    "exit_code": 0,
                    "stdout_sha256": "0" * 64,
                    "stderr_sha256": "0" * 64,
                    "passed": True,
                },
            }
        ]
        payload = release.add_bundle_digest(payload)
        path = self.write_bundle(payload)

        errors = release.validate_release_evidence(path, check_live_repo=True)

        self.assertTrue(any("cannot be live-validated safely" in error for error in errors))
        self.assertFalse(marker_path.exists())

    def test_live_repo_check_rejects_regular_file_repo_root(self) -> None:
        payload = self.valid_payload()
        fake_repo_root = self.root / "not-a-directory"
        fake_repo_root.write_text("not a directory\n", encoding="utf-8")
        payload["repo_root"] = str(fake_repo_root)
        payload = release.add_bundle_digest(payload)
        path = self.write_bundle(payload)

        errors = release.validate_release_evidence(path, check_live_repo=True)

        self.assertTrue(any("repo_root must be an existing directory" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
