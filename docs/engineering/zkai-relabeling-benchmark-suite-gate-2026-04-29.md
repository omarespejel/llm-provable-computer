# zkAI Relabeling Benchmark Suite Gate

Status: engineering/public-conformance benchmark, not a performance benchmark.

Issue: #315

## Purpose

This gate promotes the agent-step relabeling oracle into a reusable zkAI
statement-binding benchmark suite.

The suite tests a verifier-facing failure mode that is broader than zkML:
accepting a valid proof or receipt object under a relabeled user-facing
statement. The checked mutations cover model identity, model/weights
commitments, input context, output/action, quantization/config, policy,
tool-output, prior/next state, proof-system version, verifier domain,
dependency-drop manifest, evidence manifest, and unsupported trust-class
upgrades.

This is a conformance and hardening benchmark. It does not rank systems by
performance and does not prove the soundness of an underlying proof system.

## Checked Artifacts

- Suite driver: `scripts/zkai_relabeling_benchmark_suite.py`
- Production verifier adapter: `examples/agent_step_receipt_verify.rs`
- Suite tests: `scripts/tests/test_zkai_relabeling_benchmark_suite.py`
- JSON evidence:
  `docs/engineering/evidence/zkai-relabeling-benchmark-suite-2026-04.json`
- TSV evidence:
  `docs/engineering/evidence/zkai-relabeling-benchmark-suite-2026-04.tsv`

Regeneration command:

```bash
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target/agent-relabeling-bench}"
ZKAI_RELABELING_BENCHMARK_GIT_COMMIT=9e65141b206d9dbfacd51cbc5c17d5f1225d8b59 \
ZKAI_RELABELING_BENCHMARK_COMMAND_JSON='["env","CARGO_TARGET_DIR=target/agent-relabeling-bench","python3.12","scripts/zkai_relabeling_benchmark_suite.py","--adapter","rust-production","--write-json","docs/engineering/evidence/zkai-relabeling-benchmark-suite-2026-04.json","--write-tsv","docs/engineering/evidence/zkai-relabeling-benchmark-suite-2026-04.tsv"]' \
python3.12 scripts/zkai_relabeling_benchmark_suite.py \
    --adapter rust-production \
    --write-json docs/engineering/evidence/zkai-relabeling-benchmark-suite-2026-04.json \
    --write-tsv docs/engineering/evidence/zkai-relabeling-benchmark-suite-2026-04.tsv
```

Validation commands:

```bash
python3.12 -m unittest \
  scripts.tests.test_agent_step_receipt_relabeling_harness \
  scripts.tests.test_zkai_relabeling_benchmark_suite
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target/agent-relabeling-bench}"
python3.12 scripts/zkai_relabeling_benchmark_suite.py --adapter rust-production --json
python3.12 scripts/paper/paper_preflight.py --repo-root .
git diff --check
```

The benchmark-suite command exercises the Rust production verifier adapter
against one accepted baseline plus all mutated fixture cases.

## Result

The Rust production verifier accepts the baseline `AgentStepReceiptV1` fixture
and rejects all `20 / 20` relabeling mutations.

The JSON evidence records:

- generation commit handle,
- exact regeneration command argv vector,
- verifier adapter/crate/schema metadata,
- canonical baseline artifact SHA-256 and inspectable artifact payload,
- canonical per-mutation artifact SHA-256 and inspectable artifact payload.

The artifact payloads are intentionally checked into the JSON evidence, not only
hashed, so an auditor can inspect the accepted baseline and each stale-evidence
relabeling mutation without rerunning the generator first. The SHA-256 values are
computed over the same canonical JSON bytes consumed by the verifier adapter.

Observed rejection layers:

- `14` cryptographic-binding rejections,
- `5` domain/version allowlist rejections,
- `1` trust-policy rejection.

The important result is not the count. The important result is that commitment
fields are now mutated to valid but different commitments, so the production
verifier rejects relabeling because the evidence no longer binds the statement,
not merely because the mutation produced malformed JSON or malformed commitment
syntax.

## Reviewer/Auditor Notes

During the first Rust-production evidence pass, several commitment-field
mutations were malformed strings. That would have produced a misleading result:
the verifier rejected those cases at parser/format validation rather than at
statement-binding validation. This gate fixes that by generating valid
`algorithm:hex` commitments for commitment-valued relabeling mutations.

This matters because a real attacker would relabel a statement with a syntactic
commitment to a different model, input, output, policy, or state, not with an
obviously malformed field.

## Adapter Contract

A benchmark adapter should report, for each case:

- whether the baseline object is accepted,
- whether the mutated object is accepted,
- the target statement field,
- the mutation category,
- the rejection layer,
- the verifier error string or rejection reason.

A system passes a case only if the baseline is accepted and the mutated object is
rejected. If the baseline does not verify, the adapter result is not a valid
conformance measurement for that system.

## Non-Claims

- This is not a throughput or latency benchmark.
- This is not a proof that an implementation's cryptographic backend is sound.
- This is not a claim about external systems until their adapters are checked in
  with reproducible artifacts.
- This does not prove that a verifier rejects every possible self-consistent
  forged evidence graph; it tests stale-evidence relabeling and trust-class
  upgrade attempts against a fixed accepted baseline.

## Follow-Up

The next useful step is one external or independent adapter, tracked in #318.
Good candidates are small statement-bound EZKL artifacts, another Stwo-native
verifier surface, or a carefully scoped BitSage/Obelyzk artifact only after its
verifier command and source/deployed-hash mapping are reproducible enough to
avoid unfair claims.
