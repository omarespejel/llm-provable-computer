# d128 RISC Zero Statement Receipt Gate (2026-05-05)

## Decision

`GO_D128_RISC0_STATEMENT_RECEIPT_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT`

Issue `#433` turns the issue `#422` zkVM journal contract into a real RISC Zero
receipt. The checked guest reads the canonical d128 two-slice journal bytes and
commits those bytes as its public journal. The host verifies the receipt against
the compiled RISC Zero image id and requires the decoded journal to match the
expected bytes exactly.

This is a statement-binding receipt. It is not recursive verification of the
underlying Stwo slice proofs inside RISC Zero.

## What Is Bound

- journal commitment:
  `blake2b-256:f5890b4cff1f1fba01caabe692af96e53a1c514b2f84201d17b2a793af298569`
- receipt commitment:
  `blake2b-256:3a5b4bd93282879ff42178b6115d483bfa0d95383485df88604fbdacb2ad2dfd`
- RISC Zero image id:
  `dd87546db470a99fa5b32dc6e9fbc39c7d0ef1b3475573f44d5ad984a98454e5`
- receipt artifact:
  `docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.bincode`

The receipt gate rejects `21 / 21` relabeling, metric-smuggling,
receipt-metadata, validation-command, and parser/schema mutations.

## Engineering Metrics

These are single local engineering measurements, not paper-facing benchmark
rows and not cross-system performance comparisons.

| Metric | Value |
|---|---:|
| Receipt size | `310234` bytes |
| Proof generation time | `178636.325 ms` |
| Receipt verification time | `25.972 ms` |
| Timing policy | `single_local_run_engineering_only` |

The proof-generation time is preserved from the original `--prove` run when the
gate is later regenerated with `--verify-existing`; regeneration should not
silently erase the expensive proof-generation measurement.

## Claim Boundary

What this result establishes:

- a real external zkVM receipt exists for the checked d128 two-slice statement
  envelope;
- the receipt binds the exact public journal, model/program identity, input,
  output, policy/action labels, verifier domain, and source hashes inherited
  from the issue `#422` journal contract;
- the same statement-envelope discipline now has both SNARK and zkVM external
  controls.

What this result does not establish:

- not recursive verification of the underlying Stwo slice proofs inside RISC
  Zero;
- not end-to-end zkML inference proving;
- not a public zkML benchmark row;
- not a Starknet deployment result;
- not evidence that RISC Zero is faster or slower than the native Stwo route.

## Reproduction

Toolchain pin for a fresh environment:

```bash
curl -L https://risczero.com/install | bash
export PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH"
rzup --version  # must print 0.5.0 for this checked fixture
rzup install cargo-risczero 3.0.5
rzup install r0vm 3.0.5
rustup toolchain install 1.92.0 --component rustfmt --component rust-src
rzup show
cargo risczero --version
rustc +1.92.0 --version
```

The fixture also checks in
`programs/risc0-d128-statement-receipt/rust-toolchain.toml` with
`channel = "1.92.0"` so the host/method build does not float with the local
stable channel.

```bash
export PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH"
export CARGO_TARGET_DIR=/tmp/rz433-risc0-target

python3 scripts/zkai_d128_risc0_statement_receipt_gate.py \
  --verify-existing \
  --receipt docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.bincode \
  --write-json docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-risc0-statement-receipt-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_risc0_statement_receipt_gate
```

To regenerate the receipt from scratch, replace `--verify-existing` with
`--prove`. That path is intentionally slower and should be treated as a fresh
engineering measurement, not a median benchmark.
