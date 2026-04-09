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


if __name__ == "__main__":
    unittest.main()
