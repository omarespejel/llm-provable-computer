import copy
import json
import tempfile
import unittest

from scripts import zkai_paper_claim_pack_gate as gate


class PaperClaimPackGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = gate.build_payload()
        gate.validate_payload(self.payload)

    def test_binds_narrow_thesis_and_non_claims(self):
        self.assertEqual(self.payload["decision"], gate.DECISION)
        self.assertIn("STARK-native proof-architecture", self.payload["go_posture"][0])
        self.assertIn("not full inference", self.payload["non_claims"])
        self.assertIn("not public benchmark", self.payload["non_claims"])
        self.assertIn("not production-ready", self.payload["non_claims"])
        self.assertIn("not exact real-valued Softmax", self.payload["non_claims"])

    def test_referenced_evidence_paths_exist(self):
        paths = [gate.ROOT / ref["path"] for ref in self.payload["evidence_refs"]]
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            self.assertTrue(path.is_file(), path)

    def test_all_declared_mutations_reject(self):
        expected = set(gate.EXPECTED_MUTATION_NAMES)
        actual = {name for name, _ in gate.mutation_cases(self.payload)}
        self.assertEqual(actual, expected)
        for name, mutated in gate.mutation_cases(self.payload):
            with self.assertRaises(gate.ClaimPackGateError, msg=name):
                gate.validate_payload(mutated)

    def test_rejects_positive_overclaims_even_when_commitment_is_refreshed(self):
        for text in [
            "This proves full inference.",
            "This is exact Softmax.",
            "This is a public benchmark.",
            "This is production-ready.",
        ]:
            mutated = copy.deepcopy(self.payload)
            mutated["paper_claims"][0] = text
            mutated["payload_commitment"] = gate.payload_commitment(mutated)
            with self.assertRaisesRegex(gate.ClaimPackGateError, "positive claim overclaim"):
                gate.validate_payload(mutated)

    def test_rejects_missing_evidence_even_when_commitment_is_refreshed(self):
        mutated = copy.deepcopy(self.payload)
        mutated["evidence_refs"][0]["path"] = "docs/engineering/evidence/does-not-exist.json"
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaisesRegex(gate.ClaimPackGateError, "missing evidence path"):
            gate.validate_payload(mutated)

    def test_write_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = gate.pathlib.Path(tmp) / "claim-pack.json"
            gate.write_json(path, self.payload)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, self.payload)

    def test_write_json_rejects_symlink_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = gate.pathlib.Path(tmp)
            target = tmp_path / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = tmp_path / "link.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(gate.ClaimPackGateError, "output path must not be a symlink"):
                gate.write_json(link, self.payload)


if __name__ == "__main__":
    unittest.main()
