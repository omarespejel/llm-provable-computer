import json
import tempfile
import unittest
from pathlib import Path

from scripts import research_issue_lint


class ResearchIssueLintTests(unittest.TestCase):
    def valid_ledger_entry(self) -> dict[str, object]:
        return {
            "id": "valid-track",
            "status": "EXPLORE",
            "thesis": "x",
            "why_it_matters_for_serious_paper": "x",
            "smallest_falsifying_experiment": "x",
            "go_gate": "x",
            "no_go_gate": "x",
            "required_artifacts": ["gate"],
            "non_claims": ["timing"],
        }

    def test_frontier_ledger_rejects_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "frontier_ledger.jsonl").write_text(
                json.dumps({"id": "missing-fields", "status": "EXPLORE"}) + "\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(any("missing fields" in error for error in errors))

    def test_frontier_ledger_rejects_duplicate_ids(self) -> None:
        entry = self.valid_ledger_entry()
        entry["id"] = "duplicate-track"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "frontier_ledger.jsonl").write_text(
                json.dumps(entry) + "\n" + json.dumps(entry) + "\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(any("duplicate id duplicate-track" in error for error in errors))

    def test_frontier_ledger_rejects_empty_required_string(self) -> None:
        entry = self.valid_ledger_entry()
        entry["thesis"] = ""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "frontier_ledger.jsonl").write_text(
                json.dumps(entry) + "\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(any("thesis must be a non-empty string" in error for error in errors))

    def test_frontier_ledger_rejects_whitespace_only_strings(self) -> None:
        entry = self.valid_ledger_entry()
        entry["thesis"] = "   "
        entry["non_claims"] = ["timing", "   "]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "frontier_ledger.jsonl").write_text(
                json.dumps(entry) + "\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(any("thesis must be a non-empty string" in error for error in errors))
        self.assertTrue(any("non_claims entries must be non-empty strings" in error for error in errors))

    def test_frontier_ledger_rejects_non_string_list_items(self) -> None:
        entry = self.valid_ledger_entry()
        entry["required_artifacts"] = ["gate", ""]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "frontier_ledger.jsonl").write_text(
                json.dumps(entry) + "\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(
            any("required_artifacts entries must be non-empty strings" in error for error in errors)
        )

    def test_frontier_ledger_rejects_unknown_fields(self) -> None:
        entry = self.valid_ledger_entry()
        entry["surprise"] = "not in schema"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "frontier_ledger.jsonl").write_text(
                json.dumps(entry) + "\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(any("unknown fields: surprise" in error for error in errors))

    def test_frontier_ledger_rejects_invalid_optional_fields(self) -> None:
        entry = self.valid_ledger_entry()
        entry["owner_role"] = "publisher"
        entry["evidence_paths"] = ["docs/gate.md", ""]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "frontier_ledger.jsonl").write_text(
                json.dumps(entry) + "\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(any("invalid owner_role 'publisher'" in error for error in errors))
        self.assertTrue(
            any("evidence_paths entries must be non-empty strings" in error for error in errors)
        )

    def test_frontier_ledger_rejects_non_object_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "frontier_ledger.jsonl").write_text("[]\n", encoding="utf-8")

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(any("ledger entry must be a JSON object" in error for error in errors))

    def test_template_ids_accept_variable_indentation(self) -> None:
        text = "  - type: input\n      id: thesis\n        id: go_gate\n"

        found = research_issue_lint._template_ids(text)

        self.assertEqual(["thesis", "go_gate"], found)

    def test_template_ids_ignore_markdown_literal_block_content(self) -> None:
        text = (
            "- type: markdown\n"
            "  attributes:\n"
            "    value: |\n"
            "      id: thesis\n"
            "      id: go_gate\n"
            "- type: input\n"
            "  id: owner_role\n"
        )

        found = research_issue_lint._template_ids(text)

        self.assertEqual(["owner_role"], found)

    def test_issue_templates_reject_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template_dir = root / ".github" / "ISSUE_TEMPLATE"
            template_dir.mkdir(parents=True)
            (template_dir / "config.yml").write_text(
                "blank_issues_enabled: false\n",
                encoding="utf-8",
            )
            (template_dir / "research-frontier.yml").write_text(
                "body:\n"
                "  - type: input\n"
                "    id: owner_role\n"
                "  - type: input\n"
                "    id: owner_role\n"
                "Do not use GitHub CI as the research loop.\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_issue_templates(root)

        self.assertTrue(any("duplicate ids: owner_role" in error for error in errors))

    def test_issue_template_directory_returns_lint_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template_dir = root / ".github" / "ISSUE_TEMPLATE"
            template_dir.mkdir(parents=True)
            (template_dir / "config.yml").write_text(
                "blank_issues_enabled: false\n",
                encoding="utf-8",
            )
            (template_dir / "research-frontier.yml").mkdir()

            errors = research_issue_lint.lint_issue_templates(root)

        self.assertTrue(any("issue template must be a file" in error for error in errors))

    def test_issue_template_config_rejects_false_in_comment_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template_dir = root / ".github" / "ISSUE_TEMPLATE"
            template_dir.mkdir(parents=True)
            (template_dir / "config.yml").write_text(
                "blank_issues_enabled: true\n"
                "# blank_issues_enabled: false\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_issue_templates(root)

        self.assertTrue(any("blank issues must be disabled" in error for error in errors))

    def test_research_policy_directory_returns_lint_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research_dir = root / ".codex" / "research"
            (research_dir / "schemas").mkdir(parents=True)
            (research_dir / "north_star.yml").write_text("id: north-star\n", encoding="utf-8")
            (research_dir / "operating_model.yml").mkdir()
            (research_dir / "schemas" / "frontier_track.schema.json").write_text(
                "{}\n",
                encoding="utf-8",
            )

            errors = research_issue_lint.lint_research_policy(root)

        self.assertTrue(any("research policy path must be a file" in error for error in errors))

    def test_frontier_ledger_directory_returns_lint_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_dir = root / ".codex" / "research" / "frontier_ledger.jsonl"
            ledger_dir.mkdir(parents=True)

            errors = research_issue_lint.lint_frontier_ledger(root)

        self.assertTrue(any("frontier ledger must be a file" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
