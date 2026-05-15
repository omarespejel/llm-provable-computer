import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import zkai_d128_gate_value_activation_down_residual_fused_gate as gate


class D128GateValueActivationDownResidualFusedGateTests(unittest.TestCase):
    def test_payload_validates_expected_savings(self) -> None:
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["aggregate"]["fused_local_typed_bytes"], 19_344)
        self.assertEqual(payload["aggregate"]["separate_local_typed_bytes"], 44_288)
        self.assertEqual(payload["aggregate"]["typed_saving_vs_separate_bytes"], 24_944)
        self.assertEqual(payload["aggregate"]["typed_ratio_vs_separate"], 0.436777)
        self.assertEqual(payload["aggregate"]["json_saving_vs_separate_bytes"], 88_516)
        self.assertEqual(payload["aggregate"]["fused_total_row_count"], 197_248)

    def test_all_mutations_reject(self) -> None:
        payload = gate.build_payload()
        rejections = gate.run_mutations(payload)
        self.assertEqual(len(rejections), len(gate.MUTATION_NAMES))
        self.assertTrue(all(result == "rejected" for result in rejections.values()))

    def test_unknown_payload_field_rejects(self) -> None:
        payload = gate.build_payload()
        payload["extra"] = True
        with self.assertRaises(gate.FusedResidualGateError):
            gate.validate_payload(payload)

    def test_non_finite_json_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaises(gate.FusedResidualGateError):
                gate.read_json_with_size(path, 1024, "bad json")

    @unittest.skipUnless(hasattr(__import__("os"), "symlink"), "symlink support required")
    def test_read_symlink_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.json"
            link = root / "link.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(gate.FusedResidualGateError):
                gate.read_json_with_size(link, 1024, "linked json")

    def test_output_escape_rejects_before_mkdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside" / "gate.json"
            with self.assertRaises(gate.FusedResidualGateError):
                gate.assert_output_path(outside)
            self.assertFalse(outside.parent.exists())

    def test_atomic_write_retries_partial_write(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as tmp:
            path = Path(tmp) / "partial.json"
            real_write = gate.os.write

            def short_write(fd: int, data: bytes) -> int:
                if len(data) > 1:
                    return real_write(fd, data[:1])
                return real_write(fd, data)

            with mock.patch.object(gate.os, "write", side_effect=short_write):
                gate.atomic_write(path, b"abcdef")
            self.assertEqual(path.read_bytes(), b"abcdef")


if __name__ == "__main__":
    unittest.main()
