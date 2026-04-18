from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "collect_mutation_survivors.py"
SPEC = importlib.util.spec_from_file_location("collect_mutation_survivors", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load mutation survivor module from {MODULE_PATH}")
mutation = importlib.util.module_from_spec(SPEC)
sys.modules["collect_mutation_survivors"] = mutation
SPEC.loader.exec_module(mutation)


class MutationSurvivorTests(unittest.TestCase):
    def test_summarize_counts_outcome_files(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            mutants = root / "mutants.out"
            mutants.mkdir()
            (mutants / "caught.txt").write_text("src/a.rs:1 replace true with false\n", encoding="utf-8")
            (mutants / "missed.txt").write_text("src/a.rs:2 delete statement\n", encoding="utf-8")
            (mutants / "timeout.txt").write_text("src/a.rs:3 replace + with -\n", encoding="utf-8")
            (mutants / "unviable.txt").write_text("src/a.rs:4 invalid mutant\n", encoding="utf-8")

            summary = mutation.build_summary(
                SimpleNamespace(
                    repo_root=str(root),
                    mutants_dir=str(mutants),
                    output=str(root / "summary.json"),
                    target=["src/a.rs"],
                )
            )

            self.assertEqual(summary["counts"]["caught"], 1)
            self.assertEqual(summary["counts"]["survived"], 1)
            self.assertEqual(summary["counts"]["timeout"], 1)
            self.assertEqual(summary["counts"]["unviable"], 1)
            self.assertEqual(summary["counts"]["total_classified"], 4)
            self.assertEqual(summary["survived"], ["src/a.rs:2 delete statement"])
            self.assertEqual(summary["target_files"], ["src/a.rs"])
            self.assertEqual(len(summary["source_files"]), 4)

    def test_summarize_rejects_non_directory_output(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            not_dir = root / "mutants.out"
            not_dir.write_text("not a dir", encoding="utf-8")

            with self.assertRaisesRegex(mutation.MutationEvidenceError, "not a directory"):
                mutation.build_summary(
                    SimpleNamespace(
                        repo_root=str(root),
                        mutants_dir=str(not_dir),
                        output=str(root / "summary.json"),
                        target=[],
                    )
                )

    def test_ledger_accepts_empty_triage_lists(self) -> None:
        ledger = {
            "schema": "mutation-survivor-ledger-v1",
            "updated_at": "2026-04-18T00:00:00Z",
            "trusted_targets": ["src/stwo_backend/decoding.rs"],
            "milestone_commands": ["scripts/run_mutation_suite.sh"],
            "current_status": {"surviving_mutants": [], "timed_out_mutants": []},
            "non_claims": ["Does not claim exhaustive proof of correctness."],
        }

        self.assertEqual(mutation.validate_ledger(ledger), [])

    def test_ledger_rejects_untriaged_survivor(self) -> None:
        ledger = {
            "schema": "mutation-survivor-ledger-v1",
            "updated_at": "2026-04-18T00:00:00Z",
            "trusted_targets": ["src/stwo_backend/decoding.rs"],
            "milestone_commands": ["scripts/run_mutation_suite.sh"],
            "current_status": {
                "surviving_mutants": [
                    {
                        "mutant": "src/a.rs:1 replace true with false",
                        "target": "src/a.rs",
                        "outcome": "survived",
                        "classification": "untriaged",
                        "evidence": "target/mutation/run/survivors.json",
                        "next_action": "add a test",
                        "paper_blocker": True,
                    }
                ],
                "timed_out_mutants": [],
            },
            "non_claims": ["Does not claim exhaustive proof of correctness."],
        }

        errors = mutation.validate_ledger(ledger)

        self.assertTrue(any("classification must not be untriaged" in error for error in errors))

    def test_extract_ledger_json_from_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "mutation-survivors.md"
            payload = {
                "schema": "mutation-survivor-ledger-v1",
                "updated_at": "2026-04-18T00:00:00Z",
                "trusted_targets": ["src/a.rs"],
                "milestone_commands": ["scripts/run_mutation_suite.sh"],
                "current_status": {"surviving_mutants": [], "timed_out_mutants": []},
                "non_claims": ["Does not claim exhaustive proof of correctness."],
            }
            path.write_text(
                "# Ledger\n\n```json mutation-survivors-v1\n"
                + json.dumps(payload)
                + "\n```\n",
                encoding="utf-8",
            )

            self.assertEqual(mutation.extract_ledger_json(path), payload)


if __name__ == "__main__":
    unittest.main()
