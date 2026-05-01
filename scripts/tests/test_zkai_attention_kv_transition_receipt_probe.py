from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "zkai_attention_kv_transition_receipt_probe.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_kv_transition_receipt_probe", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load {SCRIPT}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class AttentionKvTransitionReceiptProbeTests(unittest.TestCase):
    def test_probe_is_go_and_rejects_all_relabels(self) -> None:
        payload = PROBE.run_probe()

        self.assertEqual(payload["decision"], PROBE.DECISION)
        self.assertTrue(payload["baseline_accepted"])
        self.assertEqual(payload["mutations_checked"], 8)
        self.assertEqual(payload["mutations_rejected"], 8)
        self.assertTrue(payload["all_mutations_rejected"])
        self.assertEqual(payload["summary"]["prior_kv_items"], 2)
        self.assertEqual(payload["summary"]["next_kv_items"], 3)

    def test_transition_is_deterministic(self) -> None:
        fixture = PROBE.canonical_transition_fixture()
        transition = PROBE.evaluate_transition(fixture)

        self.assertEqual(transition["selected_position"], 0)
        self.assertEqual(transition["attention_output"], [2, 1])
        self.assertEqual(len(transition["next_kv_cache"]), 3)

    def test_receipt_rejects_stale_prior_kv(self) -> None:
        receipt = PROBE.build_receipt()
        tampered = copy.deepcopy(receipt)
        tampered["prior_kv_cache_commitment"] = "blake2b-256:" + "11" * 32

        with self.assertRaisesRegex(PROBE.AttentionKvReceiptError, "prior_kv"):
            PROBE.verify_receipt(tampered)

    def test_receipt_rejects_proof_status_overclaim(self) -> None:
        receipt = PROBE.build_receipt()
        tampered = copy.deepcopy(receipt)
        tampered["proof_status"] = "PROVEN_BY_STWO"

        with self.assertRaisesRegex(PROBE.AttentionKvReceiptError, "proof_status"):
            PROBE.verify_receipt(tampered)

    def test_payload_validation_rejects_missing_rejection(self) -> None:
        payload = PROBE.run_probe()
        payload["mutations_rejected"] -= 1

        with self.assertRaisesRegex(PROBE.AttentionKvReceiptError, "mutation rejection"):
            PROBE.validate_payload(payload)

    def test_tsv_columns_are_stable(self) -> None:
        payload = PROBE.run_probe()

        self.assertEqual(PROBE.to_tsv(payload).splitlines()[0].split("\t"), list(PROBE.TSV_COLUMNS))

    def test_write_outputs_round_trips(self) -> None:
        payload = PROBE.run_probe()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_out = tmp / "out.json"
            tsv_out = tmp / "out.tsv"
            PROBE.write_outputs(payload, json_out, tsv_out)

            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            PROBE.validate_payload(loaded)
            self.assertTrue(tsv_out.read_text(encoding="utf-8").startswith("case_id\t"))


if __name__ == "__main__":
    unittest.main()
