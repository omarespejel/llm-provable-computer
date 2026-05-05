from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "zkai_attention_kv_proof_route_selector_gate.py"
SPEC = importlib.util.spec_from_file_location("zkai_attention_kv_proof_route_selector_gate", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"failed to load {SCRIPT}")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class AttentionKvProofRouteSelectorGateTests(unittest.TestCase):
    def test_gate_records_external_snark_go_and_source_contract_go(self) -> None:
        payload = GATE.build_payload()

        self.assertEqual(payload["decision"], "GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_ATTENTION_KV_SOURCE_CONTRACT")
        self.assertEqual(payload["first_blocker"], GATE.FIRST_BLOCKER)
        self.assertEqual(payload["claim_boundary"], GATE.CLAIM_BOUNDARY)
        self.assertEqual(payload["source_contract"]["source_decision"], GATE.SOURCE.DECISION)
        self.assertEqual(payload["source_contract"]["source_proof_status"], "SOURCE_BACKED_RECEIPT_NOT_PROVEN")
        self.assertEqual(payload["source_contract"]["present_public_fields"], list(GATE.REQUIRED_PUBLIC_FIELDS))
        self.assertEqual(payload["proof_backed_routes_available"], ["external_snark_attention_kv_statement_receipt"])
        self.assertEqual(payload["external_snark_receipt"]["decision"], GATE.SNARK.DECISION)
        self.assertEqual(payload["metrics"]["proof_size_bytes"], payload["external_snark_receipt"]["proof_size_bytes"])
        self.assertEqual(payload["mutations_checked"], len(GATE.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(GATE.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_gate_rejects_proof_backed_route_relabeling(self) -> None:
        payload = GATE.build_payload()
        payload.pop("mutation_cases")
        payload.pop("mutations_checked")
        payload.pop("mutations_rejected")
        payload.pop("all_mutations_rejected")
        payload["route_candidates"][1]["usable_today"] = True
        payload["route_candidates"][1]["proof_backed"] = True
        payload["route_candidates"][1]["status"] = "GO_NATIVE_STWO_ATTENTION_KV_PROOF"
        payload["proof_backed_routes_available"] = ["local_stwo_attention_kv_transition_proof"]

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "route inventory"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_gate_rejects_fake_metrics(self) -> None:
        payload = GATE.build_payload()
        payload.pop("mutation_cases")
        payload.pop("mutations_checked")
        payload.pop("mutations_rejected")
        payload.pop("all_mutations_rejected")
        payload["metrics"]["verifier_time_ms"] = 1.0

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "metric smuggling"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_gate_rejects_missing_required_public_field(self) -> None:
        payload = GATE.build_payload()
        payload.pop("mutation_cases")
        payload.pop("mutations_checked")
        payload.pop("mutations_rejected")
        payload.pop("all_mutations_rejected")
        payload["source_contract"]["present_public_fields"] = payload["source_contract"]["present_public_fields"][:-1]

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "present public field"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_gate_rejects_mutation_summary_drift(self) -> None:
        payload = GATE.build_payload()
        payload["mutation_cases"][0]["rejected"] = False

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "mutation rejection"):
            GATE.validate_payload(payload)

    def test_gate_rejects_malformed_next_go_criteria_as_gate_error(self) -> None:
        payload = GATE.build_payload()
        payload.pop("mutation_cases")
        payload.pop("mutations_checked")
        payload.pop("mutations_rejected")
        payload.pop("all_mutations_rejected")
        payload["next_go_criteria"] = None

        with self.assertRaisesRegex(GATE.AttentionKvRouteSelectorError, "next-go criteria drift"):
            GATE.validate_payload(payload, allow_missing_mutation_summary=True)

    def test_tsv_columns_are_stable(self) -> None:
        payload = GATE.build_payload()

        self.assertEqual(GATE.to_tsv(payload).splitlines()[0].split("\t"), list(GATE.TSV_COLUMNS))

    def test_write_outputs_round_trips(self) -> None:
        payload = GATE.build_payload()
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = pathlib.Path(raw_tmp)
            json_out = tmp / "out.json"
            tsv_out = tmp / "out.tsv"
            GATE.write_outputs(payload, json_out, tsv_out)

            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            GATE.validate_payload(loaded)
            self.assertTrue(tsv_out.read_text(encoding="utf-8").startswith("decision\t"))

    def test_individual_mutations_reject(self) -> None:
        payload = GATE.build_payload()

        for name in GATE.EXPECTED_MUTATION_NAMES:
            mutated = GATE.mutate_payload(payload, name)
            with self.assertRaises(GATE.AttentionKvRouteSelectorError):
                GATE.validate_payload(mutated, allow_missing_mutation_summary=True)


if __name__ == "__main__":
    unittest.main()
