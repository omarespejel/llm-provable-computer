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

## Table C1. Frozen vanilla baseline by scope
| Artifact | Backend | Bundle | Prove | Verify | Proof size | Semantic scope |
|---|---|---|---:|---:|---:|---|
| `addition` | vanilla | `production-v1` | `71s` | `2s` | `7,644,769` bytes | x |
| `dot_product` | vanilla | `production-v1` | `430s` | `5s` | `12,835,175` bytes | x |
| `single_neuron` | vanilla | `production-v1` | `390s` | `4s` | `11,767,989` bytes | x |

## Table C2. Frozen transformer-shaped `stwo` bundle
| Bundle | Backend | Prepare | Verify | Artifact size | Structural metrics | Semantic scope |
|---|---|---:|---:|---:|---|---|
| `stwo-transformer-shaped-v1` | `stwo` | `28s` | `9s` | `9,348,044` bytes | x | x |
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


def valid_transformer_index() -> str:
    artifact_bytes = valid_transformer_artifact_json().encode("utf-8")
    artifact_sha = MOD.hashlib.sha256(artifact_bytes).hexdigest()
    return """# Appendix Artifact Index (S-two Transformer-Shaped V1)

## Artifact Summary
| Field | Value |
|---|---|
| Artifact file | `transformer_shaped.stwo.bundle.json` |
| Artifact size (bytes) | `{artifact_size}` |
| SHA-256 | `{artifact_sha}` |

## Timing Summary (seconds)
| Label | Seconds |
|---|---:|
| prepare_transformer_shaped_bundle | 28 |
| verify_transformer_shaped_bundle | 9 |
""".format(artifact_size=len(artifact_bytes), artifact_sha=artifact_sha)


def valid_transformer_artifact_json() -> str:
    return '{"artifact":"transformer-shaped-bundle","version":1}\n'


def valid_shared_normalization_primitive_json() -> str:
    return '{"artifact":"shared-normalization-primitive","version":1}\n'


def valid_shared_normalization_primitive_index() -> str:
    artifact_bytes = valid_shared_normalization_primitive_json().encode("utf-8")
    artifact_sha = MOD.hashlib.sha256(artifact_bytes).hexdigest()
    return f"""# Appendix Artifact Index (S-two Shared-Normalization Primitive V1)

## Artifact Summary
| Field | Value |
|---|---|
| Artifact file | `shared-normalization-primitive.stwo.json` |
| Artifact size (bytes) | `{len(artifact_bytes)}` |
| SHA-256 | `{artifact_sha}` |

## Timing Summary (seconds)
| Label | Seconds |
|---|---:|
| prepare_shared_normalization_primitive | 1 |
| verify_shared_normalization_primitive | 1 |
"""


def write_valid_backend_fixture(
    repo: pathlib.Path,
    *,
    transformer_text: str | None = None,
    transformer_artifact_text: str | None = None,
    primitive_index_text: str | None = None,
    primitive_artifact_text: str | None = None,
) -> None:
    write_text(
        repo / "docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md",
        transformer_text or valid_transformer_index(),
    )
    write_text(
        repo
        / "docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/transformer_shaped.stwo.bundle.json",
        transformer_artifact_text or valid_transformer_artifact_json(),
    )
    write_text(
        repo
        / "docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md",
        primitive_index_text or valid_shared_normalization_primitive_index(),
    )
    write_text(
        repo
        / "docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/shared-normalization-primitive.stwo.json",
        primitive_artifact_text or valid_shared_normalization_primitive_json(),
    )


class PaperPreflightTests(unittest.TestCase):
    def test_active_paper_file_set_includes_alignment_paper(self):
        self.assertIn("docs/paper/stark-transformer-alignment-2026.md", MOD.PAPER_FILES)

    def test_parse_appendix_rows_handles_reordered_columns(self):
        variants = [
            ("Proof size", "`Artifact`", "backend"),
            ("Proof size (bytes)", "artifact", "Backend"),
            ("Size (bytes)", "ARTIFACT", "BACKEND"),
        ]
        for size_header, artifact_header, backend_header in variants:
            text = f"""## Table C1. Frozen vanilla baseline by scope
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
                repo
                / "docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md"
            )
            self.assertEqual(
                findings.errors[0],
                f"{expected_missing}: missing required file for active bundle consistency check.",
            )

    def test_check_backend_consistency_reports_read_failures_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_valid_backend_fixture(repo)
            findings = MOD.Findings()
            with mock.patch.object(pathlib.Path, "read_text", side_effect=OSError("boom")):
                MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertIn("failed to read active bundle consistency inputs", findings.errors[0])
            self.assertIn("boom", findings.errors[0])

    def test_check_backend_consistency_reports_decode_failures_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_valid_backend_fixture(repo)
            transformer_index = (
                repo
                / "docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md"
            )
            transformer_index.parent.mkdir(parents=True, exist_ok=True)
            transformer_index.write_bytes(b"\xff\xfe\xfa")
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertIn("failed to read active bundle consistency inputs", findings.errors[0])

    def test_check_backend_consistency_passes_for_valid_fixture_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_valid_backend_fixture(repo)
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertEqual(findings.errors, [])

    def test_check_backend_consistency_reports_missing_timing_keys_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            transformer_index_path = (
                repo
                / "docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md"
            )
            broken_stwo = valid_transformer_index().replace(
                "| verify_transformer_shaped_bundle | 9 |\n", ""
            )
            write_valid_backend_fixture(repo, transformer_text=broken_stwo)
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any(
                    str(transformer_index_path) in msg and "missing timing keys" in msg
                    for msg in findings.errors
                ),
                findings.errors,
            )

    def test_check_backend_consistency_reports_missing_size_keys_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            broken_stwo = valid_transformer_index().replace(
                f"| Artifact size (bytes) | `{len(valid_transformer_artifact_json().encode('utf-8'))}` |\n",
                "",
            )
            write_valid_backend_fixture(repo, transformer_text=broken_stwo)
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("missing artifact-summary fields" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_check_backend_consistency_reports_malformed_transformer_size_without_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            broken_stwo = valid_transformer_index().replace(
                f"| Artifact size (bytes) | `{len(valid_transformer_artifact_json().encode('utf-8'))}` |\n",
                "| Artifact size (bytes) | `N/A` |\n",
            )
            write_valid_backend_fixture(repo, transformer_text=broken_stwo)
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any(
                    "malformed transformer-shaped artifact-summary field 'Artifact size (bytes)'"
                    in msg
                    for msg in findings.errors
                ),
                findings.errors,
            )

    def test_check_backend_consistency_reports_transformer_artifact_file_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            broken_stwo = valid_transformer_index().replace(
                "| Artifact file | `transformer_shaped.stwo.bundle.json` |\n",
                "| Artifact file | `other.json` |\n",
            )
            write_valid_backend_fixture(repo, transformer_text=broken_stwo)
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("transformer-shaped index artifact file mismatch" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_check_backend_consistency_reports_transformer_artifact_size_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_valid_backend_fixture(
                repo,
                transformer_artifact_text='{"artifact":"too-small"}\n',
            )
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("transformer-shaped artifact size mismatch" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_check_backend_consistency_reports_transformer_artifact_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_valid_backend_fixture(
                repo,
                transformer_text=valid_transformer_index().replace(
                    MOD.hashlib.sha256(
                        valid_transformer_artifact_json().encode("utf-8")
                    ).hexdigest(),
                    "0" * 64,
                ),
            )
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("transformer-shaped SHA-256 mismatch" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_check_backend_consistency_reports_transformer_missing_summary_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            broken_stwo = valid_transformer_index().replace(
                f"| SHA-256 | `{MOD.hashlib.sha256(valid_transformer_artifact_json().encode('utf-8')).hexdigest()}` |\n",
                "",
            )
            write_valid_backend_fixture(repo, transformer_text=broken_stwo)
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("transformer-shaped index is missing artifact-summary fields" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_check_backend_consistency_reports_primitive_artifact_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_valid_backend_fixture(
                repo,
                primitive_index_text=valid_shared_normalization_primitive_index().replace(
                    MOD.hashlib.sha256(
                        valid_shared_normalization_primitive_json().encode("utf-8")
                    ).hexdigest(),
                    "0" * 64,
                ),
            )
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("shared-normalization primitive SHA-256 mismatch" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_check_backend_consistency_reports_primitive_missing_summary_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            broken_primitive = valid_shared_normalization_primitive_index().replace(
                "| SHA-256 |", "| Digest |"
            )
            write_valid_backend_fixture(repo, primitive_index_text=broken_primitive)
            findings = MOD.Findings()
            MOD.check_backend_appendix_consistency(repo, findings)
            self.assertTrue(findings.errors)
            self.assertTrue(
                any("shared-normalization primitive index is missing artifact-summary fields" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_parse_index_field_values_exposes_canonical_artifact_keys(self):
        fields = MOD.parse_index_field_values(valid_transformer_index())
        self.assertEqual(fields["artifact_file"], "transformer_shaped.stwo.bundle.json")
        self.assertEqual(
            fields["artifact_size_bytes"],
            str(len(valid_transformer_artifact_json().encode("utf-8"))),
        )
        self.assertIn("sha_256", fields)
        primitive_fields = MOD.parse_index_field_values(valid_shared_normalization_primitive_index())
        self.assertEqual(
            primitive_fields["artifact_file"], "shared-normalization-primitive.stwo.json"
        )
        self.assertIn("sha_256", primitive_fields)

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

    def test_paper3_claim_evidence_matrix_accepts_complete_record_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            for rel_path in (
                "docs/engineering/paper3-composition-prototype.md",
                "src/stwo_backend/recursion.rs",
            ):
                write_text(repo / rel_path, "")
            write_text(
                repo / "src/stwo_backend/recursion.rs",
                (
                    "struct Phase38Paper3CompositionSource;\n"
                    "fn phase38_prepare_paper3_composition_prototype() {}\n"
                    "fn verify_phase38_paper3_composition_prototype() {}\n"
                    "fn phase38_source_chain_matches() {}\n"
                    "fn phase38_execution_template_matches() {}\n"
                    "fn phase38_shared_lookup_identity_matches() {}\n"
                    "fn phase38_verify_segment_receipt_binding() {}\n"
                    "fn verify_phase37_recursive_artifact_chain_harness_receipt_against_sources() {}\n"
                    "let naive_per_step_package_count = 0;\n"
                    "let composed_segment_package_count = 0;\n"
                    "let package_count_delta = 0;\n"
                    "fn phase38_paper3_composition_prototype_accepts_contiguous_shared_lookup_segments() {}\n"
                    "fn phase38_paper3_composition_prototype_rejects_unbound_phase37_commitment_swap() {}\n"
                    "fn phase38_paper3_composition_prototype_rejects_boundary_gap() {}\n"
                    "fn phase38_paper3_composition_prototype_rejects_source_chain_drift() {}\n"
                    "fn phase38_paper3_composition_prototype_rejects_execution_template_drift() {}\n"
                    "fn phase38_paper3_composition_prototype_rejects_shared_lookup_identity_drift() {}\n"
                    "fn phase38_paper3_composition_prototype_rejects_tampered_baseline() {}\n"
                ),
            )
            write_text(
                repo / "docs/engineering/paper3-composition-prototype.md",
                "\n".join(
                    f"`evidence:{claim_id}`"
                    for claim_id in sorted(MOD.REQUIRED_PAPER3_CLAIM_IDS)
                ),
            )
            records = []
            for claim_id in sorted(MOD.REQUIRED_PAPER3_CLAIM_IDS):
                records.append(
                    f"""- id: {claim_id}
  claim: "Bounded Paper 3 claim for {claim_id}."
  paper_locations:
    - docs/engineering/paper3-composition-prototype.md
  implementation:
    - src/stwo_backend/recursion.rs:phase38_prepare_paper3_composition_prototype
  specs:
    - docs/engineering/paper3-composition-prototype.md
  positive_tests:
    - phase38_paper3_composition_prototype_accepts_contiguous_shared_lookup_segments
  negative_tests:
    - phase38_paper3_composition_prototype_rejects_boundary_gap
  schemas:
    - "Not applicable: no standalone schema."
  artifact_files:
    - docs/engineering/paper3-composition-prototype.md
  artifact_hashes:
    - "Not applicable: no frozen artifact hash."
  fuzz_or_formal:
    - "Not applicable: targeted negative tests only."
  evidence_commands:
    - cargo test -q phase38
  non_claims:
    - "Does not claim recursive proof closure."
"""
                )
            write_text(repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE, "\n".join(records))

            findings = MOD.Findings()
            MOD.check_paper3_claim_evidence_matrix(repo, findings)
            self.assertEqual(findings.errors, [])

    def test_claim_evidence_path_anchor_rejects_paths_outside_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            repo.mkdir()
            outside = pathlib.Path(tmp) / "outside.rs"
            write_text(outside, "fn escaped_anchor() {}\n")

            findings = MOD.Findings()
            MOD.check_claim_evidence_path_anchor(
                repo,
                repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE,
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
                repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE,
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
                    repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE,
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
                repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE,
                "phase37_artifact_chain_harness_receipt",
                "implementation",
                "inside-link.rs:escaped_anchor",
                findings,
            )
            self.assertTrue(
                any("path escapes repo root" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_evidence_path_anchor_allows_explicit_non_applicable_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            findings = MOD.Findings()

            MOD.check_claim_evidence_path_anchor(
                repo,
                repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE,
                "phase38_composition_continuity",
                "schemas",
                "Not applicable: no standalone schema.",
                findings,
            )

            self.assertEqual(findings.errors, [])

            findings = MOD.Findings()
            MOD.check_claim_evidence_path_anchor(
                repo,
                repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE,
                "phase38_composition_continuity",
                "schemas",
                "Not applicable:",
                findings,
            )
            self.assertTrue(
                any("empty `Not applicable:` note" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_evidence_path_anchor_rejects_non_applicable_for_required_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)

            for key, entry in (
                ("implementation", "Not applicable: implementation exists only in prose."),
                ("artifact_files", "Not applicable: no standalone artifact file."),
            ):
                findings = MOD.Findings()
                MOD.check_claim_evidence_path_anchor(
                    repo,
                    repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE,
                    "phase38_composition_continuity",
                    key,
                    entry,
                    findings,
                )

                self.assertTrue(
                    any("repo-relative path is required" in msg for msg in findings.errors),
                    findings.errors,
                )

    def test_experimental_boundary_ignores_paper_location_fragments(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            evidence_path = repo / MOD.TABLERO_CLAIM_EVIDENCE_FILE
            record = {
                "claim": "The theorem has a boundary section.",
                "paper_locations": [
                    "docs/paper/tablero-typed-verifier-boundaries-2026.md#Experimental-backend scope"
                ],
                "evidence_files": ["docs/paper/appendix-tablero-claim-boundary.md"],
                "non_claims": ["Does not claim recursive proof compression."],
            }
            findings = MOD.Findings()

            MOD.check_experimental_evidence_boundary(
                evidence_path, "tablero_statement_preservation_theorem", record, findings
            )

            self.assertEqual(findings.errors, [])

    def test_experimental_evidence_boundary_requires_scope_and_non_default_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            evidence_path = repo / MOD.TABLERO_CLAIM_EVIDENCE_FILE
            record = {
                "claim": "The checked grid has a growing ratio.",
                "evidence_files": ["docs/paper/evidence/example-experimental.tsv"],
                "non_claims": ["Does not claim an asymptotic theorem."],
            }
            findings = MOD.Findings()

            MOD.check_experimental_evidence_boundary(
                evidence_path, "tablero_scaling_law_fit", record, findings
            )

            self.assertTrue(
                any("experimental-scoped" in msg for msg in findings.errors),
                findings.errors,
            )
            self.assertTrue(
                any("non-default/non-publication" in msg for msg in findings.errors),
                findings.errors,
            )

    def test_claim_evidence_path_anchor_reports_resolution_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            findings = MOD.Findings()

            with mock.patch.object(pathlib.Path, "resolve", side_effect=OSError("loop")):
                MOD.check_claim_evidence_path_anchor(
                    repo,
                    repo / MOD.PAPER3_CLAIM_EVIDENCE_FILE,
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
            path = pathlib.Path(tmp) / MOD.PAPER3_CLAIM_EVIDENCE_FILE
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
    def test_primary_presentation_guardrails_reject_internal_phase_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            for rel_path in MOD.PRIMARY_PRESENTATION_FILES:
                write_text(repo / rel_path, "# Placeholder\n")
            write_text(
                repo / 'docs/paper/tablero-typed-verifier-boundaries-2026.md',
                "See [abstract](abstract-tablero-2026.md) and [method]"
                "(appendix-methodology-and-reproducibility.md) and "
                "![overview](figures/tablero-results-overview-2026-04.svg) and "
                "![scaling](figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg) and "
                "![breakdown](figures/tablero-replay-baseline-breakdown-2026-04.svg).\n"
                "Phase44D leaks here.\n",
            )
            findings = MOD.Findings()
            MOD.check_primary_presentation_guardrails(repo, findings)
            self.assertTrue(findings.errors)
            self.assertIn("internal phase-style terminology leaked", findings.errors[0])

    def test_primary_presentation_guardrails_require_core_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            for rel_path in MOD.PRIMARY_PRESENTATION_FILES:
                write_text(repo / rel_path, "# Placeholder\n")
            write_text(
                repo / "docs/paper/tablero-typed-verifier-boundaries-2026.md",
                "No required links here.\n",
            )
            findings = MOD.Findings()
            MOD.check_primary_presentation_guardrails(repo, findings)
            self.assertTrue(
                any(
                    "missing required presentation link" in error
                    for error in findings.errors
                )
            )

    def test_primary_presentation_guardrails_requires_scaling_law_figure_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            for rel_path in MOD.PRIMARY_PRESENTATION_FILES:
                write_text(repo / rel_path, "# Placeholder\n")
            write_text(
                repo / "docs/paper/tablero-typed-verifier-boundaries-2026.md",
                "See [abstract](abstract-tablero-2026.md) and "
                "[method](appendix-methodology-and-reproducibility.md) and "
                "![overview](figures/tablero-results-overview-2026-04.svg) and "
                "![breakdown](figures/tablero-replay-baseline-breakdown-2026-04.svg).\n",
            )
            findings = MOD.Findings()
            MOD.check_primary_presentation_guardrails(repo, findings)
            expected = (
                "missing required presentation link "
                "`figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg`"
            )
            self.assertTrue(any(expected in error for error in findings.errors), findings.errors)
            self.assertFalse(
                any(
                    "missing required presentation link `abstract-tablero-2026.md`" in error
                    or "missing required presentation link `appendix-methodology-and-reproducibility.md`" in error
                    or "missing required presentation link `figures/tablero-results-overview-2026-04.svg`" in error
                    or "missing required presentation link `figures/tablero-replay-baseline-breakdown-2026-04.svg`" in error
                    for error in findings.errors
                ),
                findings.errors,
            )

if __name__ == "__main__":
    unittest.main()
