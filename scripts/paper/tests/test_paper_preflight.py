import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


def load_preflight_module():
    root = pathlib.Path(__file__).resolve().parents[3]
    module_path = root / "scripts/paper/paper_preflight.py"
    spec = importlib.util.spec_from_file_location("paper_preflight", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load paper_preflight module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MOD = load_preflight_module()


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def valid_appendix_table() -> str:
    return """# Appendix: Frozen Backend Artifact Comparison

## Table C1. Frozen artifact comparison by backend and scope
| Artifact | Backend | Bundle | Prove | Verify | Proof size | Semantic scope |
|---|---|---|---:|---:|---:|---|
| `addition` | vanilla | `production-v1` | `71s` | `2s` | `7,644,769` bytes | x |
| `addition` | `stwo` | `stwo-experimental-v1` | `2s` | `1s` | `54,563` bytes | x |
| `dot_product` | vanilla | `production-v1` | `430s` | `5s` | `12,835,175` bytes | x |
| `single_neuron` | vanilla | `production-v1` | `390s` | `4s` | `11,767,989` bytes | x |
| `shared-normalization-demo` | `stwo` | `stwo-experimental-v1` | `1s` | `1s` | `74,074` bytes | x |
| `gemma_block_v4` | `stwo` | `stwo-experimental-v1` | `1s` | `1s` | `751,737` bytes | x |
| `decoding_demo` | `stwo` | `stwo-experimental-v1` | `1s` | `1s` | `4,032,182` bytes | x |
"""


def valid_prod_index() -> str:
    return """# Appendix Artifact Index (Production V1)

## Primary Artifacts
| Artifact | Purpose | Size (bytes) | SHA-256 |
|---|---|---:|---|
| addition.proof.json | x | 7644769 | a |
| dot_product.proof.json | x | 12835175 | b |
| single_neuron.proof.json | x | 11767989 | c |

## Timing Summary (seconds)
| Label | Seconds |
|---|---:|
| prove_addition | 71 |
| verify_addition | 2 |
| prove_dot_product | 430 |
| verify_dot_product | 5 |
| prove_single_neuron | 390 |
| verify_single_neuron | 4 |
"""


def valid_stwo_index() -> str:
    return """# Appendix Artifact Index (S-two Experimental V1)

## Primary Artifacts
| Artifact | Purpose | Semantic scope | Size (bytes) | SHA-256 |
|---|---|---|---:|---|
| addition.stwo.proof.json | x | arithmetic | 54563 | a |
| shared-normalization.stwo.proof.json | x | lookup-backed component | 74074 | b |
| gemma_block_v4.stwo.proof.json | x | transformer-shaped checksum fixture | 751737 | c |
| decoding.stwo.chain.json | x | proof-carrying decoding | 4032182 | d |

## Timing Summary (seconds)
| Label | Seconds |
|---|---:|
| prove_addition_stwo | 2 |
| verify_addition_stwo | 1 |
| prove_shared_normalization_stwo | 1 |
| verify_shared_normalization_stwo | 1 |
| prove_gemma_block_v4_stwo | 1 |
| verify_gemma_block_v4_stwo | 1 |
| prove_decoding_demo_stwo | 1 |
| verify_decoding_demo_stwo | 1 |
"""


class PaperPreflightTests(unittest.TestCase):
    def test_parse_appendix_rows_handles_reordered_columns(self):
        variants = [
            ("Proof size", "`Artifact`", "backend"),
            ("Proof size (bytes)", "artifact", "Backend"),
            ("Size (bytes)", "ARTIFACT", "BACKEND"),
        ]
        for size_header, artifact_header, backend_header in variants:
            text = f"""## Table C1. Frozen artifact comparison by backend and scope
| {backend_header} | {artifact_header} | Verify | Prove | Semantic Scope | {size_header} | Bundle |
|---|---|---:|---:|---|---:|---|
| vanilla | `addition` | `2s` | `71s` | x | `7,644,769` bytes | production-v1 |
"""
            rows = MOD.parse_appendix_backend_rows(text)
            self.assertEqual(rows[("addition", "vanilla")], (71, 2, 7644769))

    def test_check_backend_consistency_reports_missing_required_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            expected_missing = (
                repo / "docs/paper/appendix-backend-artifact-comparison.md"
            )
            self.assertEqual(
                findings.errors[0],
                f"{expected_missing}: missing required file for backend artifact consistency check.",
            )

    def test_check_backend_consistency_reports_read_failures_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(
                repo / "docs/paper/appendix-backend-artifact-comparison.md",
                valid_appendix_table(),
            )
            write_text(
                repo / "docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md",
                valid_prod_index(),
            )
            write_text(
                repo / "docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md",
                valid_stwo_index(),
            )
            findings = MOD.Findings()
            with mock.patch.object(pathlib.Path, "read_text", side_effect=OSError("boom")):
                MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertIn("failed to read backend artifact consistency inputs", findings.errors[0])
            self.assertIn("boom", findings.errors[0])

    def test_check_backend_consistency_passes_for_valid_fixture_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(
                repo / "docs/paper/appendix-backend-artifact-comparison.md",
                valid_appendix_table(),
            )
            write_text(
                repo / "docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md",
                valid_prod_index(),
            )
            write_text(
                repo / "docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md",
                valid_stwo_index(),
            )
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertEqual(findings.errors, [])

    def test_check_backend_consistency_reports_table_value_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            tampered_appendix = valid_appendix_table().replace(
                "| `addition` | `stwo` | `stwo-experimental-v1` | `2s` | `1s` | `54,563` bytes | x |\n",
                "| `addition` | `stwo` | `stwo-experimental-v1` | `52s` | `2s` | `54,563` bytes | x |\n",
            )
            write_text(
                repo / "docs/paper/appendix-backend-artifact-comparison.md",
                tampered_appendix,
            )
            write_text(
                repo / "docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md",
                valid_prod_index(),
            )
            write_text(
                repo / "docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md",
                valid_stwo_index(),
            )
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(
                any("Table C1 mismatch for ('addition', 'stwo')" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_check_backend_consistency_reports_unexpected_table_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            tampered_appendix = valid_appendix_table() + (
                "| `unexpected_artifact` | `stwo` | `stwo-experimental-v1` | `1s` | `1s` | `1,111` bytes | x |\n"
            )
            write_text(
                repo / "docs/paper/appendix-backend-artifact-comparison.md",
                tampered_appendix,
            )
            write_text(
                repo / "docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md",
                valid_prod_index(),
            )
            write_text(
                repo / "docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md",
                valid_stwo_index(),
            )
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(
                any(
                    "unexpected Table C1 row for artifact/backend ('unexpected_artifact', 'stwo')"
                    in msg
                    for msg in findings.errors
                ),
                findings.errors,
            )

    def test_check_backend_consistency_reports_missing_timing_keys_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(
                repo / "docs/paper/appendix-backend-artifact-comparison.md",
                valid_appendix_table(),
            )
            write_text(
                repo / "docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md",
                valid_prod_index(),
            )
            broken_stwo = valid_stwo_index().replace("| verify_decoding_demo_stwo | 1 |\n", "")
            write_text(
                repo / "docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md",
                broken_stwo,
            )
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("missing timing keys" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_check_backend_consistency_reports_missing_size_keys_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(
                repo / "docs/paper/appendix-backend-artifact-comparison.md",
                valid_appendix_table(),
            )
            write_text(
                repo / "docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md",
                valid_prod_index(),
            )
            broken_stwo = valid_stwo_index().replace(
                "| addition.stwo.proof.json | x | arithmetic | 54563 | a |\n",
                "",
            )
            write_text(
                repo / "docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md",
                broken_stwo,
            )
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("missing artifact-size keys" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_publication_snapshot_placeholders_fail_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(
                repo / "docs/paper/PUBLICATION_RELEASE.md",
                "Canonical publication snapshot commit:\nTBD_SNAPSHOT_SHA\n",
            )
            findings = MOD.Findings()
            MOD.check_publication_snapshot_placeholders(repo, findings)
            self.assertTrue(findings.errors)
            self.assertIn("TBD_SNAPSHOT_SHA", findings.errors[0])

    def test_publication_snapshot_placeholder_read_errors_are_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            path = repo / "docs/paper/PUBLICATION_RELEASE.md"
            write_text(path, "Canonical publication snapshot commit:\nvalid\n")
            findings = MOD.Findings()
            with mock.patch.object(pathlib.Path, "read_text", side_effect=OSError("boom")):
                MOD.check_publication_snapshot_placeholders(repo, findings)
            self.assertTrue(
                any(
                    "failed to read publication metadata for snapshot placeholder checks" in msg
                    for msg in findings.errors
                ),
                findings.errors,
            )

    def test_publication_snapshot_pending_field_fails_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(
                repo / "docs/paper/submission-v4-2026-04-11/BUNDLE_INDEX.md",
                "Canonical repository snapshot:\nPending. Fill after merge.\n",
            )
            findings = MOD.Findings()
            MOD.check_publication_snapshot_placeholders(repo, findings)
            self.assertTrue(
                any("Pending." in msg for msg in findings.errors),
                findings.errors,
            )

    def test_publication_snapshot_pending_prose_is_not_a_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(
                repo / "docs/paper/PUBLICATION_RELEASE.md",
                (
                    "A later publication may be Pending. That prose is not the field.\n\n"
                    "Canonical publication snapshot commit:\n"
                    "`paper-publication-v4-2026-04-11` once cut.\n"
                ),
            )
            findings = MOD.Findings()
            MOD.check_publication_snapshot_placeholders(repo, findings)
            self.assertEqual(findings.errors, [])

    def test_commit_tree_root_url_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            path = repo / "docs/paper/paper.md"
            write_text(
                path,
                "<https://github.com/omarespejel/provable-transformer-vm/tree/6ff972ddda4051d73dc65c92a88c0d00683ec8c7>\n",
            )
            findings = MOD.Findings()
            MOD.run_file_checks(path, repo, findings)
            self.assertEqual(findings.errors, [])

    def test_floating_tree_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            path = repo / "docs/paper/paper.md"
            write_text(
                path,
                "<https://github.com/omarespejel/provable-transformer-vm/tree/main>\n",
            )
            findings = MOD.Findings()
            MOD.run_file_checks(path, repo, findings)
            self.assertTrue(
                any("not commit-pinned" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_root_blob_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            path = repo / "docs/paper/paper.md"
            write_text(
                path,
                "<https://github.com/omarespejel/provable-transformer-vm/blob/6ff972ddda4051d73dc65c92a88c0d00683ec8c7>\n",
            )
            findings = MOD.Findings()
            MOD.run_file_checks(path, repo, findings)
            self.assertTrue(
                any("blob link has no file path" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_evidence_matrix_accepts_complete_record_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            for rel_path in (
                "docs/paper/paper2/appendix-artifact-map.md",
                "docs/paper/paper2/proof-carrying-decode-surfaces-2026.md",
                "src/stwo_backend/recursion.rs",
                "spec/stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json",
                "tests/phase37.rs",
            ):
                write_text(repo / rel_path, "")
            write_text(
                repo / "src/stwo_backend/recursion.rs",
                (
                    "fn phase37_prepare_recursive_artifact_chain_harness_receipt() {}\n"
                    "fn verify_phase37_recursive_artifact_chain_harness_receipt_against_sources() {}\n"
                ),
            )
            write_text(
                repo / "tests/phase37.rs",
                (
                    "fn phase37_recursive_artifact_chain_harness_receipt_accepts_matching_sources() {}\n"
                    "fn phase37_recursive_artifact_chain_harness_receipt_rejects_tampered_commitment() {}\n"
                ),
            )
            records = []
            for claim_id in sorted(MOD.REQUIRED_CLAIM_IDS):
                records.append(
                    f"""- id: {claim_id}
  claim: "Bounded claim for {claim_id}."
  paper_locations:
    - docs/paper/paper2/appendix-artifact-map.md
  implementation:
    - src/stwo_backend/recursion.rs:phase37_prepare_recursive_artifact_chain_harness_receipt
    - src/stwo_backend/recursion.rs:verify_phase37_recursive_artifact_chain_harness_receipt_against_sources
  specs:
    - spec/stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json
  positive_tests:
    - phase37_recursive_artifact_chain_harness_receipt_accepts_matching_sources
  negative_tests:
    - phase37_recursive_artifact_chain_harness_receipt_rejects_tampered_commitment
  evidence_commands:
    - cargo test -q phase37
  non_claims:
    - "Does not claim recursive proof closure."
"""
                )
            write_text(
                repo / "docs/paper/paper2/appendix-artifact-map.md",
                "\n".join(
                    f"`evidence:{claim_id}`"
                    for claim_id in sorted(MOD.REQUIRED_CLAIM_IDS)
                ),
            )
            write_text(
                repo / MOD.CLAIM_EVIDENCE_FILE,
                "\n".join(records),
            )

            findings = MOD.Findings()
            MOD.check_claim_evidence_matrix(repo, findings)
            self.assertEqual(findings.errors, [])

    def test_paper2_evidence_anchor_honors_fragment_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            path = repo / "docs/paper/paper2/paper.md"
            write_text(
                path,
                (
                    "`evidence:phase29_recursive_input_contract`\n\n"
                    "## Target Section\n"
                    "No scoped evidence here.\n\n"
                    "## Later Section\n"
                    "`evidence:phase29_recursive_input_contract`\n"
                ),
            )
            records = [
                {
                    "id": "phase29_recursive_input_contract",
                    "paper_locations": ["docs/paper/paper2/paper.md#Target Section"],
                }
            ]

            findings = MOD.Findings()
            MOD.check_paper2_evidence_anchors(
                repo, repo / MOD.CLAIM_EVIDENCE_FILE, records, findings
            )
            self.assertTrue(
                any("not explicitly cited" in msg for msg in findings.errors),
                findings.errors,
            )

            write_text(
                path,
                (
                    "  ## Target Section\n"
                    "Scoped evidence can live in this section.\n\n"
                    "### Evidence paragraph\n"
                    "`evidence:phase29_recursive_input_contract`\n\n"
                    "## Later Section\n"
                ),
            )
            findings = MOD.Findings()
            MOD.check_paper2_evidence_anchors(
                repo, repo / MOD.CLAIM_EVIDENCE_FILE, records, findings
            )
            self.assertEqual(findings.errors, [])

    def test_paper2_evidence_anchor_reports_missing_fragments_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(repo / "docs/paper/paper2/paper.md", "## Other Section\n")
            records = [
                {
                    "id": "phase29_recursive_input_contract",
                    "paper_locations": ["docs/paper/paper2/paper.md#Target Section"],
                }
            ]

            findings = MOD.Findings()
            MOD.check_paper2_evidence_anchors(
                repo, repo / MOD.CLAIM_EVIDENCE_FILE, records, findings
            )

            self.assertTrue(findings.errors)
            self.assertIn("missing fragments:", findings.errors[0])
            self.assertNotIn("skipped invalid paths:", findings.errors[0])

    def test_paper2_evidence_anchor_rejects_non_heading_fragment_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(
                repo / "docs/paper/paper2/paper.md",
                (
                    "# Paper\n"
                    "The phrase Target Section appears in body text.\n\n"
                    "## Later Section\n"
                    "`evidence:phase29_recursive_input_contract`\n"
                ),
            )
            records = [
                {
                    "id": "phase29_recursive_input_contract",
                    "paper_locations": ["docs/paper/paper2/paper.md#Target Section"],
                }
            ]

            findings = MOD.Findings()
            MOD.check_paper2_evidence_anchors(
                repo, repo / MOD.CLAIM_EVIDENCE_FILE, records, findings
            )

            self.assertTrue(findings.errors)
            self.assertIn("invalid fragments:", findings.errors[0])
            self.assertIn("does not identify a Markdown heading", findings.errors[0])

    def test_claim_evidence_matrix_rejects_missing_required_claim_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(repo / MOD.CLAIM_EVIDENCE_FILE, "")

            findings = MOD.Findings()
            MOD.check_claim_evidence_matrix(repo, findings)
            self.assertTrue(
                any("missing required paper-2 claim evidence ids" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_evidence_matrix_rejects_missing_anchor_and_test_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(repo / "docs/paper/paper2/appendix-artifact-map.md", "")
            write_text(repo / "src/stwo_backend/recursion.rs", "fn other_symbol() {}\n")
            write_text(
                repo / "spec/stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json",
                "{}\n",
            )
            records = []
            for claim_id in sorted(MOD.REQUIRED_CLAIM_IDS):
                records.append(
                    f"""- id: {claim_id}
  claim: "Bounded claim for {claim_id}."
  paper_locations:
    - docs/paper/paper2/appendix-artifact-map.md
  implementation:
    - src/stwo_backend/recursion.rs:missing_symbol
  specs:
    - spec/stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json
  positive_tests:
    - missing_positive_test
  negative_tests:
    - missing_negative_test
  evidence_commands:
    - cargo test -q phase37
  non_claims:
    - "Does not claim recursive proof closure."
"""
                )
            write_text(repo / MOD.CLAIM_EVIDENCE_FILE, "\n".join(records))

            findings = MOD.Findings()
            MOD.check_claim_evidence_matrix(repo, findings)
            self.assertTrue(
                any("anchor `missing_symbol` not found" in msg for msg in findings.errors),
                findings.errors,
            )
            self.assertTrue(
                any("references missing test token: missing_positive_test" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_evidence_path_anchor_rejects_paths_outside_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            repo.mkdir()
            outside = pathlib.Path(tmp) / "outside.rs"
            write_text(outside, "fn escaped_anchor() {}\n")

            findings = MOD.Findings()
            MOD.check_claim_evidence_path_anchor(
                repo,
                repo / MOD.CLAIM_EVIDENCE_FILE,
                "phase37_artifact_chain_harness_receipt",
                "implementation",
                f"{outside}:escaped_anchor",
                findings,
            )
            self.assertTrue(
                any("path must be repo-relative" in msg for msg in findings.errors),
                findings.errors,
            )

            findings = MOD.Findings()
            MOD.check_claim_evidence_path_anchor(
                repo,
                repo / MOD.CLAIM_EVIDENCE_FILE,
                "phase37_artifact_chain_harness_receipt",
                "implementation",
                "../outside.rs:escaped_anchor",
                findings,
            )
            self.assertTrue(
                any("path must be repo-relative" in msg for msg in findings.errors),
                findings.errors,
            )

            for windows_entry in (
                r"C:\tmp\outside.rs:escaped_anchor",
                r"\\server\share\file.txt:escaped_anchor",
            ):
                findings = MOD.Findings()
                MOD.check_claim_evidence_path_anchor(
                    repo,
                    repo / MOD.CLAIM_EVIDENCE_FILE,
                    "phase37_artifact_chain_harness_receipt",
                    "implementation",
                    windows_entry,
                    findings,
                )
                self.assertTrue(
                    any("path must be repo-relative" in msg for msg in findings.errors),
                    findings.errors,
                )

            link = repo / "inside-link.rs"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            findings = MOD.Findings()
            MOD.check_claim_evidence_path_anchor(
                repo,
                repo / MOD.CLAIM_EVIDENCE_FILE,
                "phase37_artifact_chain_harness_receipt",
                "implementation",
                "inside-link.rs:escaped_anchor",
                findings,
            )
            self.assertTrue(
                any("path escapes repo root" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_evidence_path_anchor_reports_resolution_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            findings = MOD.Findings()

            with mock.patch.object(pathlib.Path, "resolve", side_effect=OSError("loop")):
                MOD.check_claim_evidence_path_anchor(
                    repo,
                    repo / MOD.CLAIM_EVIDENCE_FILE,
                    "phase37_artifact_chain_harness_receipt",
                    "implementation",
                    "src/lib.rs:anchor",
                    findings,
                )

            self.assertTrue(
                any("failed to resolve path" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_find_repo_tokens_scans_for_all_tokens_in_one_pass_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(repo / "src/lib.rs", "fn alpha_token() {}\n")
            write_text(repo / "tests/smoke.rs", "fn beta_token() {}\n")

            found = MOD.find_repo_tokens(
                repo, {"alpha_token", "beta_token", "missing_token"}
            )
            self.assertEqual(found, {"alpha_token", "beta_token"})

    def test_parse_claim_evidence_records_reports_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / MOD.CLAIM_EVIDENCE_FILE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\xff")

            findings = MOD.Findings()
            records = MOD.parse_claim_evidence_records(path, findings)
            self.assertEqual(records, [])
            self.assertTrue(
                any("failed to read claim evidence matrix" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_language_linter_rejects_unbounded_semantic_equivalence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                "The artifact proves semantic equivalence across runtime frontends.\n",
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertTrue(
                any("semantic equivalence" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_language_linter_accepts_bounded_equivalence_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                (
                    "The artifact provides bounded semantic equivalence evidence "
                    "inside a stated claim boundary, not a general theorem.\n"
                ),
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertEqual(findings.errors, [])

    def test_claim_language_linter_splits_adjacent_list_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                (
                    "- bounded semantic equivalence evidence for a toy case\n"
                    "- The artifact proves semantic equivalence across runtimes.\n"
                ),
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertTrue(
                any(":2:" in msg and "semantic equivalence" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_language_linter_rejects_hyphenated_unbounded_equivalence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                "The artifact proves semantic-equivalence across runtime frontends.\n",
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertTrue(
                any("semantic equivalence" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_language_linter_accepts_hyphenated_bounded_equivalence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                "This is bounded semantic-equivalence evidence for one fixture.\n",
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertEqual(findings.errors, [])

    def test_claim_language_linter_rejects_accuracy_claim_without_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                "The quantized artifact preserves accuracy across model exports.\n",
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertTrue(
                any("preserves accuracy" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_language_linter_accepts_wrong_comparison_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                (
                    "The wrong comparison language is `already recursive "
                    "proof-carrying data`; the repository does not claim that.\n"
                ),
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertEqual(findings.errors, [])

    def test_claim_language_linter_rejects_attestation_verified_as_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                "The release provides supply-chain attestation with verified identity.\n",
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertTrue(
                any("supply-chain attestation" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_language_linter_rejects_complete_attestation_as_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                "The release provides complete supply-chain attestation.\n",
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertTrue(
                any("supply-chain attestation" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_language_linter_accepts_attestation_gap_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paper.md"
            write_text(
                path,
                "Supply-chain attestations remain a missing gap for future work.\n",
            )

            findings = MOD.Findings()
            MOD.check_claim_language_in_file(path, findings)
            self.assertEqual(findings.errors, [])

    def test_claim_language_linter_discovers_new_paper_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_text(repo / "docs/paper/existing.md", "Bounded claims only.\n")
            write_text(
                repo / "docs/paper/new-section/new-paper.md",
                "The artifact proves semantic equivalence across runtimes.\n",
            )

            findings = MOD.Findings()
            MOD.check_paper_claim_language(repo, findings)
            self.assertTrue(
                any(
                    "new-paper.md" in msg and "semantic equivalence" in msg
                    for msg in findings.errors
                ),
                findings.errors,
            )

    def test_claim_language_linter_reports_missing_paper_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)

            findings = MOD.Findings()
            MOD.check_paper_claim_language(repo, findings)
            self.assertTrue(
                any("missing docs/paper directory" in msg for msg in findings.errors),
                findings.errors,
            )


if __name__ == "__main__":
    unittest.main()
