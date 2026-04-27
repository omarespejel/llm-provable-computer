# Mutation Survivor Ledger

This file is the paper-facing mutation-testing control point.

Mutation testing is useful only if survivors are not silently ignored. A killed
mutant is evidence that at least one test noticed the injected change. A
surviving mutant is evidence that either the tests are weak, the mutation is
semantically equivalent, or the target is outside the claim surface. Those cases
must be separated before a paper milestone.

## Milestone Rule

Before a Paper 2 or Paper 3 evidence checkpoint that depends on the trusted
`stwo` verifier surface, run the targeted mutation suite locally and keep the
survivor report with the release evidence bundle.

Use a dedicated output root so the run can be hashed and referenced later:

```bash
MUTATION_OUTPUT_ROOT=target/mutation/tablero-checkpoint \
MUTATION_SURVIVOR_REPORT=target/mutation/tablero-checkpoint/survivors.json \
scripts/run_mutation_suite.sh
```

The wrapper runs `cargo mutants` on the trusted verifier files and then writes a
JSON summary containing killed, survived, timed-out, and unviable counts. If a
run produces a survivor or timeout, do one of two things:

- Add or strengthen a test so the mutant is killed, rerun the mutation slice, and
  keep the new report.
- Record the survivor below with a concrete classification, evidence path, next
  action, and whether it blocks paper claims.

The default is strict: untriaged survivors and untriaged timeouts block paper
claims. Equivalent mutants are allowed only when the reason is written down and
kept narrow.

## Checked Ledger

The following JSON block is validated by
`scripts/collect_mutation_survivors.py check-doc`. Keep it machine-readable; put
human explanation around it, not inside comments.

```json mutation-survivors-v1
{
  "schema": "mutation-survivor-ledger-v1",
  "updated_at": "2026-04-18T00:00:00Z",
  "trusted_targets": [
    "src/stwo_backend/decoding.rs",
    "src/stwo_backend/shared_lookup_artifact.rs",
    "src/stwo_backend/arithmetic_subset_prover.rs"
  ],
  "milestone_commands": [
    "MUTATION_OUTPUT_ROOT=target/mutation/<checkpoint> MUTATION_SURVIVOR_REPORT=target/mutation/<checkpoint>/survivors.json scripts/run_mutation_suite.sh",
    "python3 scripts/collect_mutation_survivors.py check-doc docs/engineering/mutation-survivors.md"
  ],
  "current_status": {
    "surviving_mutants": [],
    "timed_out_mutants": []
  },
  "non_claims": [
    "Does not claim exhaustive proof of correctness.",
    "Does not claim mutation testing covers code outside the trusted target list.",
    "Does not claim a survivor-free run proves the implementation is sound."
  ]
}
```

## Triage Template

When a survivor or timeout exists, add an object to the appropriate list:

```json
{
  "mutant": "src/stwo_backend/decoding.rs:123 replace == with !=",
  "target": "src/stwo_backend/decoding.rs",
  "outcome": "survived",
  "classification": "weak-test | equivalent | out-of-scope | tool-limitation",
  "evidence": "target/mutation/tablero-checkpoint/survivors.json",
  "next_action": "add rejection test for boundary mismatch",
  "paper_blocker": true
}
```

A `paper_blocker: false` survivor must be justified by `classification` and must
not support a paper-facing claim. If the classification is `weak-test`, it stays
a blocker until a new test kills it.
