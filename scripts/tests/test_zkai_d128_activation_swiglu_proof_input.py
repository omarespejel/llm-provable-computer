from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "zkai_d128_activation_swiglu_proof_input.py"
SPEC = importlib.util.spec_from_file_location("zkai_d128_activation_swiglu_proof_input", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load activation/SwiGLU input generator from {SCRIPT_PATH}")
ACTIVATION_SWIGLU = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ACTIVATION_SWIGLU)


class ZkAiD128ActivationSwiGluProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = ACTIVATION_SWIGLU.build_payload()

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_builds_and_validates(self) -> None:
        payload = self.fresh_payload()
        ACTIVATION_SWIGLU.validate_payload(payload)
        self.assertEqual(payload["row_count"], ACTIVATION_SWIGLU.FF_DIM)
        self.assertEqual(payload["activation_lookup_rows"], ACTIVATION_SWIGLU.ACTIVATION_TABLE_ROWS)
        self.assertEqual(payload["swiglu_mix_rows"], ACTIVATION_SWIGLU.FF_DIM)
        self.assertEqual(
            payload["source_gate_value_projection_output_commitment"],
            ACTIVATION_SWIGLU.GATE_VALUE.output_commitment(
                payload["gate_projection_q8"], payload["value_projection_q8"]
            ),
        )
        self.assertEqual(
            payload["source_gate_value_projection_statement_commitment"],
            ACTIVATION_SWIGLU.SOURCE_GATE_VALUE_STATEMENT_COMMITMENT,
        )
        self.assertEqual(
            payload["source_gate_value_projection_public_instance_commitment"],
            ACTIVATION_SWIGLU.SOURCE_GATE_VALUE_PUBLIC_INSTANCE_COMMITMENT,
        )
        self.assertNotEqual(payload["hidden_activation_commitment"], ACTIVATION_SWIGLU.OUTPUT_ACTIVATION_COMMITMENT)

    def test_load_source_accepts_legacy_synthetic_gate_value_evidence(self) -> None:
        source = ACTIVATION_SWIGLU.load_source()
        self.assertEqual(
            source["source_bridge_statement_commitment"],
            ACTIVATION_SWIGLU.GATE_VALUE.SOURCE_BRIDGE_STATEMENT_COMMITMENT,
        )
        self.assertEqual(
            source["source_bridge_public_instance_commitment"],
            ACTIVATION_SWIGLU.GATE_VALUE.SOURCE_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
        )
        ACTIVATION_SWIGLU.validate_source(source)

    def test_builds_from_attention_derived_gate_value_evidence(self) -> None:
        source = ACTIVATION_SWIGLU.load_source(
            ROOT
            / "docs"
            / "engineering"
            / "evidence"
            / "zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json"
        )
        payload = ACTIVATION_SWIGLU.build_payload(source)
        self.assertEqual(
            payload["source_gate_value_projection_output_commitment"],
            ACTIVATION_SWIGLU.DERIVED_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        )
        self.assertEqual(
            payload["hidden_activation_commitment"],
            "blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4",
        )
        self.assertEqual(payload["validation_commands"], ACTIVATION_SWIGLU.DERIVED_VALIDATION_COMMANDS)

    def test_source_anchor_rejects_unknown_commitment_tuple(self) -> None:
        source = copy.deepcopy(ACTIVATION_SWIGLU.load_source())
        source["statement_commitment"] = "blake2b-256:" + "91" * 32
        source["public_instance_commitment"] = "blake2b-256:" + "92" * 32
        source["gate_projection_output_commitment"] = "blake2b-256:" + "93" * 32
        source["value_projection_output_commitment"] = "blake2b-256:" + "94" * 32
        source["gate_value_projection_output_commitment"] = "blake2b-256:" + "95" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "anchor is not approved"):
            ACTIVATION_SWIGLU.source_gate_value_anchor(source)

    def test_source_anchor_rejects_partial_anchor_match(self) -> None:
        source = copy.deepcopy(ACTIVATION_SWIGLU.load_source())
        source["gate_value_projection_output_commitment"] = ACTIVATION_SWIGLU.DERIVED_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "anchor is not approved"):
            ACTIVATION_SWIGLU.source_gate_value_anchor(source)

    def test_payload_rejects_validation_commands_from_wrong_anchor(self) -> None:
        source = ACTIVATION_SWIGLU.load_source(
            ROOT
            / "docs"
            / "engineering"
            / "evidence"
            / "zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json"
        )
        payload = ACTIVATION_SWIGLU.build_payload(source)
        payload["validation_commands"] = ACTIVATION_SWIGLU.VALIDATION_COMMANDS
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "validation_commands"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_hidden_relabeling_as_full_output(self) -> None:
        payload = self.fresh_payload()
        payload["hidden_activation_commitment"] = ACTIVATION_SWIGLU.OUTPUT_ACTIVATION_COMMITMENT
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "relabeled as full output"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_source_gate_value_commitment_drift(self) -> None:
        source = copy.deepcopy(ACTIVATION_SWIGLU.load_source())
        source["gate_value_projection_output_commitment"] = "blake2b-256:" + "66" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "gate/value"):
            ACTIVATION_SWIGLU.build_payload(source)

    def test_payload_rejects_source_statement_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_gate_value_projection_statement_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "source_gate_value_projection_statement_commitment"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_source_public_instance_drift(self) -> None:
        payload = self.fresh_payload()
        payload["source_gate_value_projection_public_instance_commitment"] = "blake2b-256:" + "22" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "source_gate_value_projection_public_instance_commitment"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_gate_projection_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["gate_projection_q8"][0] += 1
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "source gate projection output commitment"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_value_projection_vector_drift(self) -> None:
        payload = self.fresh_payload()
        payload["value_projection_q8"] = payload["value_projection_q8"][:-1]
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "value projection vector"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_activation_output_drift(self) -> None:
        payload = self.fresh_payload()
        payload["activated_gate_q8"][0] += 1
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "activation output drift"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_hidden_output_drift(self) -> None:
        payload = self.fresh_payload()
        payload["hidden_q8"][0] += 1
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "hidden activation output drift"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_activation_lookup_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["activation_lookup_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "activation_lookup_commitment|activation lookup"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_proof_native_parameter_drift(self) -> None:
        payload = self.fresh_payload()
        payload["proof_native_parameter_commitment"] = "blake2b-256:" + "33" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "proof_native_parameter_commitment|proof-native"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_statement_drift(self) -> None:
        payload = self.fresh_payload()
        payload["statement_commitment"] = "blake2b-256:" + "44" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "statement_commitment|statement commitment"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_public_instance_drift(self) -> None:
        payload = self.fresh_payload()
        payload["public_instance_commitment"] = "blake2b-256:" + "99" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "public_instance_commitment|public instance"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_payload_rejects_row_commitment_drift(self) -> None:
        payload = self.fresh_payload()
        payload["activation_swiglu_row_commitment"] = "blake2b-256:" + "77" * 32
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "activation_swiglu_row_commitment|activation/SwiGLU row"):
            ACTIVATION_SWIGLU.validate_payload(payload)

    def test_load_source_rejects_oversized_source_json(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            source_path = pathlib.Path(tmp) / "oversized-source.json"
            source_path.write_text(" " * (ACTIVATION_SWIGLU.MAX_SOURCE_JSON_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "exceeds max size"):
                ACTIVATION_SWIGLU.load_source(source_path)

    def test_load_source_rejects_non_file_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "regular file"):
                ACTIVATION_SWIGLU.load_source(pathlib.Path(tmp))

    def test_load_source_rejects_invalid_utf8_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            source_path = pathlib.Path(tmp) / "invalid-utf8.json"
            source_path.write_bytes(b"\xff")
            with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "failed to load"):
                ACTIVATION_SWIGLU.load_source(source_path)

    def test_load_source_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = pathlib.Path(tmp) / "source.json"
            source_path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "escapes repository"):
                ACTIVATION_SWIGLU.load_source(source_path)

    def test_load_source_rejects_symlink_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            real = pathlib.Path(tmp) / "source.json"
            real.write_text("{}", encoding="utf-8")
            symlink = pathlib.Path(tmp) / "source-link.json"
            symlink.symlink_to(real)
            with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "symlink"):
                ACTIVATION_SWIGLU.load_source(symlink)

    def test_load_source_rejects_swap_between_lstat_and_open(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            source_path = pathlib.Path(tmp) / "source.json"
            source_path.write_bytes(ACTIVATION_SWIGLU.SOURCE_JSON.read_bytes())
            original_open = ACTIVATION_SWIGLU.os.open

            def swapping_open(path: pathlib.Path, flags: int) -> int:
                source_path.unlink()
                source_path.write_text("{}", encoding="utf-8")
                return original_open(path, flags)

            ACTIVATION_SWIGLU.os.open = swapping_open
            try:
                with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "changed while reading"):
                    ACTIVATION_SWIGLU.load_source(source_path)
            finally:
                ACTIVATION_SWIGLU.os.open = original_open

    def test_write_outputs_round_trips(self) -> None:
        payload = self.fresh_payload()
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            json_path = pathlib.Path(tmp) / "activation-swiglu.json"
            tsv_path = pathlib.Path(tmp) / "activation-swiglu.tsv"
            ACTIVATION_SWIGLU.write_outputs(payload, json_path, tsv_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, payload)
            rows = ACTIVATION_SWIGLU.rows_for_tsv(loaded)
            self.assertEqual(len(rows), 1)
            tsv_text = tsv_path.read_text(encoding="utf-8")
            self.assertIn("hidden_activation_commitment", tsv_text)
            self.assertIn(payload["hidden_activation_commitment"], tsv_text)
            self.assertEqual(
                rows[0]["non_claims"],
                json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
            )

    def test_write_outputs_rejects_path_escape(self) -> None:
        payload = self.fresh_payload()
        outside = pathlib.Path(tempfile.gettempdir()) / "zkai-d128-activation-swiglu-escape.json"
        with self.assertRaisesRegex(ACTIVATION_SWIGLU.ActivationSwiGluInputError, "escapes repository"):
            ACTIVATION_SWIGLU.write_outputs(payload, outside, None)


if __name__ == "__main__":
    unittest.main()
