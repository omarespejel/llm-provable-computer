import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import zkai_d128_rmsnorm_mlp_fused_gate as gate


class D128RmsnormMlpFusedGateTests(unittest.TestCase):
    def test_payload_validates_expected_savings(self) -> None:
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["aggregate"]["fused_local_typed_bytes"], 24_832)
        self.assertEqual(payload["aggregate"]["separate_local_typed_bytes"], 56_976)
        self.assertEqual(payload["aggregate"]["typed_saving_vs_separate_bytes"], 32_144)
        self.assertEqual(payload["aggregate"]["typed_ratio_vs_separate"], 0.435833)
        self.assertEqual(payload["aggregate"]["json_saving_vs_separate_bytes"], 114_180)
        self.assertEqual(payload["aggregate"]["fused_total_row_count"], 197_504)

    def test_all_mutations_reject(self) -> None:
        payload = gate.build_payload()
        rejections = gate.run_mutations(payload)
        self.assertEqual(len(rejections), len(gate.mutation_cases(payload)))
        self.assertTrue(all(result == "rejected" for result in rejections.values()))

    def test_unknown_payload_field_rejects(self) -> None:
        payload = gate.build_payload()
        payload["extra"] = True
        with self.assertRaises(gate.RmsnormMlpFusedGateError):
            gate.validate_payload(payload)

    def test_statement_commitment_drift_rejects(self) -> None:
        payload = gate.build_payload()
        payload["statement_commitment"] = "blake2b-256:" + "1" * 64
        with self.assertRaisesRegex(gate.RmsnormMlpFusedGateError, "statement commitment drift"):
            gate.validate_payload(payload)

    def test_public_instance_commitment_drift_rejects(self) -> None:
        payload = gate.build_payload()
        payload["public_instance_commitment"] = "blake2b-256:" + "2" * 64
        with self.assertRaisesRegex(gate.RmsnormMlpFusedGateError, "public instance commitment drift"):
            gate.validate_payload(payload)

    def test_non_finite_json_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaises(gate.RmsnormMlpFusedGateError):
                gate.read_json(path, 1024, "bad json")

    def test_oversized_json_rejects_without_full_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large.json"
            path.write_bytes(b'{"value":"' + b"a" * 2048 + b'"}')
            with self.assertRaisesRegex(gate.RmsnormMlpFusedGateError, "exceeds max bytes"):
                gate.read_json(path, 64, "large json")

    @unittest.skipUnless(hasattr(__import__("os"), "symlink"), "symlink support required")
    def test_read_symlink_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.json"
            link = root / "link.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(gate.RmsnormMlpFusedGateError):
                gate.read_json(link, 1024, "linked json")

    def test_output_escape_rejects_before_mkdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside" / "gate.json"
            with self.assertRaises(gate.RmsnormMlpFusedGateError):
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

    def test_atomic_write_preserves_replace_error_when_cleanup_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as tmp:
            path = Path(tmp) / "replace-error.json"
            replace_error = OSError("replace failed")
            with mock.patch.object(gate.os, "replace", side_effect=replace_error):
                with mock.patch.object(
                    gate.pathlib.Path,
                    "unlink",
                    side_effect=OSError("unlink failed"),
                ):
                    with self.assertRaises(OSError) as ctx:
                        gate.atomic_write(path, b"abc")
            self.assertIs(ctx.exception, replace_error)

    def test_atomic_write_ignores_stale_deterministic_temp_name(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as tmp:
            root = Path(tmp)
            path = root / "stale.json"
            stale = root / f".{path.name}.{gate.os.getpid()}.tmp"
            stale.write_bytes(b"stale")
            gate.atomic_write(path, b"fresh")
            self.assertEqual(path.read_bytes(), b"fresh")
            self.assertEqual(stale.read_bytes(), b"stale")

    def test_atomic_write_cleans_temp_on_write_error(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as tmp:
            root = Path(tmp)
            path = root / "write-error.json"
            with mock.patch.object(gate.os, "write", side_effect=OSError("write failed")):
                with self.assertRaises(OSError):
                    gate.atomic_write(path, b"abc")
            self.assertEqual(list(root.glob(".write-error.json.*.tmp")), [])
            gate.atomic_write(path, b"ok")
            self.assertEqual(path.read_bytes(), b"ok")

    def test_atomic_write_cleans_temp_on_fsync_error(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as tmp:
            root = Path(tmp)
            path = root / "fsync-error.json"
            with mock.patch.object(gate.os, "fsync", side_effect=OSError("fsync failed")):
                with self.assertRaises(OSError):
                    gate.atomic_write(path, b"abc")
            self.assertEqual(list(root.glob(".fsync-error.json.*.tmp")), [])
            gate.atomic_write(path, b"ok")
            self.assertEqual(path.read_bytes(), b"ok")

    def test_build_payload_rejects_mismatched_envelope_input(self) -> None:
        accounting = gate.read_json(gate.ACCOUNTING_PATH, 8_388_608, "binary accounting")
        input_payload = gate.read_json(gate.FUSED_INPUT_PATH, 4_194_304, "fused input")
        envelope = gate.read_json(gate.FUSED_ENVELOPE_PATH, 8_388_608, "fused envelope")
        envelope["input"]["statement_commitment"] = "blake2b-256:" + "0" * 64

        def fake_read_json(path: Path, max_bytes: int, label: str) -> dict:
            if path == gate.ACCOUNTING_PATH:
                return accounting
            if path == gate.FUSED_INPUT_PATH:
                return input_payload
            if path == gate.FUSED_ENVELOPE_PATH:
                return envelope
            raise AssertionError(f"unexpected path: {path}")

        with mock.patch.object(gate, "read_json", side_effect=fake_read_json):
            with self.assertRaisesRegex(
                gate.RmsnormMlpFusedGateError,
                "envelope/input statement commitment drift",
            ):
                gate.build_payload()

    def test_written_gate_payload_validates(self) -> None:
        payload = gate.read_json(
            gate.EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json",
            1_048_576,
            "written gate payload",
        )
        gate.validate_payload(payload)


if __name__ == "__main__":
    unittest.main()
