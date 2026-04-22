from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "fuzz" / "generate_decoding_fuzz_corpus.py"
PHASE29_FIXTURE = (
    ROOT / "fuzz" / "corpus" / "phase29_recursive_compression_input_contract" / "valid_phase29.json"
)
PHASE30_FIXTURE = (
    ROOT / "fuzz" / "corpus" / "phase30_decoding_step_proof_envelope_manifest" / "valid_phase30.json"
)

SPEC = importlib.util.spec_from_file_location("generate_decoding_fuzz_corpus", GENERATOR)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load fuzz corpus generator from {GENERATOR}")
GEN = importlib.util.module_from_spec(SPEC)
sys.modules["generate_decoding_fuzz_corpus"] = GEN
SPEC.loader.exec_module(GEN)


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class DecodingFuzzCorpusGeneratorTests(unittest.TestCase):
    def write_phase113_source(self, root: pathlib.Path, raw: bytes) -> pathlib.Path:
        fixture = root / GEN.PHASE113_SOURCE_FIXTURE
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_bytes(raw)
        return fixture

    def test_phase29_commitment_mirror_matches_checked_in_fixture(self) -> None:
        contract = load_json(PHASE29_FIXTURE)
        self.assertEqual(
            GEN.commit_phase29_contract(contract),
            contract["input_contract_commitment"],
        )

    def test_generated_phase29_contract_is_bound_to_phase30_boundaries(self) -> None:
        phase30 = load_json(PHASE30_FIXTURE)["manifest"]
        contract = GEN.phase29_contract_for_phase30(phase30)

        self.assertEqual(contract["total_steps"], phase30["total_steps"])
        self.assertEqual(
            contract["global_start_state_commitment"],
            phase30["chain_start_boundary_commitment"],
        )
        self.assertEqual(
            contract["global_end_state_commitment"],
            phase30["chain_end_boundary_commitment"],
        )
        self.assertEqual(
            contract["input_contract_commitment"],
            GEN.commit_phase29_contract(contract),
        )

    def test_load_phase113_fixture_reads_checked_in_source(self) -> None:
        payload = GEN.load_phase113_fixture(ROOT)
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload)

    def test_load_phase113_fixture_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with self.assertRaises(FileNotFoundError):
                GEN.load_phase113_fixture(root)

    def test_load_phase113_fixture_digest_mismatch_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.write_phase113_source(root, b"{}")
            with self.assertRaises(ValueError):
                GEN.load_phase113_fixture(root)

    def test_load_phase113_fixture_invalid_json_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            raw = b"{not-json"
            self.write_phase113_source(root, raw)
            with self.assertRaises(ValueError):
                GEN.load_phase113_fixture(root)

    def test_load_phase113_fixture_non_object_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            raw = b"[1,2,3]\n"
            self.write_phase113_source(root, raw)
            with self.assertRaises(TypeError):
                GEN.load_phase113_fixture(root)

    def test_load_phase113_fixture_invalid_utf8_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            raw = b"\xff\xfe\xfd"
            self.write_phase113_source(root, raw)
            with self.assertRaises(ValueError):
                GEN.load_phase113_fixture(root)


if __name__ == "__main__":
    unittest.main()
