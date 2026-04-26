# Tablero Hardening Packet (April 25, 2026)

This packet is the internal hardening entrypoint for reviewing the repository's
Tablero claim and the carry-aware execution-proof hardening that underpins the
experimental replay-avoidance line.

It is designed to answer the stricter internal question first: what can the
repository itself check, falsify, and bound before any external review matters?
The goal is to reduce fooling-ourselves risk, not to manufacture audit theater.

## Review objective

Answer four questions cleanly:

1. Does the current repository make an honest statement-preservation claim for
   the Phase44D typed boundary?
2. Are the carry-aware M31 `wrap_delta` witnesses range-bound inside the AIR,
   rather than only in host-side trace construction?
3. Do the higher wrapper objects (Phase45-48) stay boundary-width, or do they
   silently reintroduce replay dependencies or stale-commitment acceptance?
4. Does the local assurance stack exercise the right failure modes before any
   stronger claim is made?

## Read order

1. `docs/engineering/phase12-carry-aware-wrap-delta-witness-discipline-2026-04-26.md`
2. `docs/engineering/tablero-soundness-note-2026-04-25.md`
3. `docs/engineering/phase12-carry-aware-soundness-review-2026-04-25.md`
4. `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`
5. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
6. `docs/engineering/phase44d-carry-aware-experimental-2x2-scaling-gate-2026-04-25.md`
7. `docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`
8. `docs/engineering/phase44d-carry-aware-experimental-family-matrix-gate-2026-04-25.md`
9. `docs/paper/stark-transformer-alignment-2026.md`

## Exact code surfaces to review

### Carry-aware AIR and proof routing

- `src/stwo_backend/arithmetic_subset_prover.rs`
- `src/stwo_backend/decoding.rs`
- `src/proof.rs`

Key properties to confirm:

- `wrap_delta` range is AIR-constrained by magnitude bits, sign, square, and
  ADD/SUB unit-range checks.
- default/publication verifier still rejects experimental backend proofs.
- proof-checked Phase12 chain verification is safe-by-default.

### Tablero core boundary

- `src/stwo_backend/history_replay_projection_prover.rs`

Key properties to confirm:

- Phase44D typed boundary acceptance verifies the real compact proof and the
  source-root/public-output binding.
- boundary validation rejects replay reintroduction.
- serialized artifacts fail closed under stale-commitment and field-drift
  tampering.

### Higher wrapper surfaces

- `src/stwo_backend/recursion.rs`

Key properties to confirm:

- Phase45 bridge remains ordered-public-input binding, not replay.
- Phase46 adapter receipt remains a compact verifier-input receipt, not a new
  proof.
- Phase47 wrapper candidate remains boundary-width and explicitly non-recursive.
- Phase48 remains an explicit no-go wrapper attempt with blocker preservation.

## Claim boundary

### Strong claims supported today

1. The carry-aware experimental backend now range-binds `wrap_delta` inside the
   AIR.
2. The Phase44D typed boundary preserves the same source-bound compact statement
   as the replay baseline, under upstream S-two soundness and local hash-binding
   assumptions.
3. Default, `2x2`, and `3x3` layout families all reproduce the same
   replay-avoidance mechanism on the experimental lane.
4. Phase43 now clears as a real second boundary on the emitted proof-native
   source surface; the earlier prototype note remains only as a bounded
   historical partial result.

### Claims not supported today

1. No new STARK soundness theorem.
2. No recursive compression theorem.
3. No backend-independent empirical proof of Tablero.
4. No SNIP-36 deployment claim.
5. No claim that the large replay-avoidance ratios are implementation-independent
   lower bounds for all manifest replay designs.

## Tooling stack to run before stronger claims

The current strongest practical stack is:

| Tool | Role in this packet | Why it belongs here |
| --- | --- | --- |
| `cargo test` / `cargo-nextest` | deterministic regression and tamper checks | reproducible exact test filters and CI-friendly isolation |
| `cargo-fuzz` | bounded adversarial parser/verifier input exploration | exercises malformed or unexpected serialized surfaces under an explicit wall-clock smoke budget |
| `Kani` | bounded model checking | checks safety/correctness properties exhaustively within bounds |
| `Miri` | undefined-behavior detection | catches UB that ordinary tests can miss |
| `cargo-audit` + `cargo-deny` | dependency and policy drift | catches supply-chain issues before harder promotion |
| optional `cargo-careful` | faster extra UB-oriented runtime checking | complements Miri when FFI/full-speed execution matters |
| optional `cargo-llvm-cov` | coverage reporting | useful for audit packets, not a proof by itself |

The repo already ships the first five. The last two are worth enabling when a
deeper audit pass wants more artifacts, but they are not required for the
minimal honest packet.

For this packet, Kani is intentionally scoped to a narrow Tablero contract set
rather than the entire repository-wide formal suite. That keeps the command
disk-feasible and tied to the exact theorem surface instead of conflating it
with unrelated historical harnesses.

## Preflight commands

### Core packet

```bash
scripts/run_tablero_hardening_preflight.sh --mode core
```

This runs:

- formatting and diff hygiene,
- targeted carry-aware AIR and proof-route tests,
- targeted Phase44D/45/46/47/48 verifier and tamper tests,
- the narrow Tablero formal-contract suite,
- dependency audit.

### Deep packet

```bash
scripts/run_tablero_hardening_preflight.sh --mode deep
```

This adds:

- Tablero-focused fuzz smoke on Phase44D boundary binding and Phase45-48 wrapper
  verifiers, bounded by an outer wall-clock budget and treated as a pass only
  if no crash artifacts are emitted,
- the repo's Miri suite.

### Optional extras

If installed locally, the recommended extra checks are:

```bash
cargo +nightly careful test --features stwo-backend --lib phase45_public_input_bridge_
cargo llvm-cov --features stwo-backend --lib --lcov --output-path target/tablero-hardening/lcov.info
```

The fuzz suite accepts optional checked-in seed corpora under `fuzz/corpus/<target>/`,
but the default hardening packet does not require a corpus-refresh script or any
pre-generated accepted-chain bundle.

These are intentionally optional because the repository does not yet rely on
those tools in the default merge flow.

## Narrow formal-contract surface

The core packet uses:

```bash
scripts/run_tablero_formal_contract_suite.sh
```

This runs the Kani harnesses most directly tied to the theorem:

- Phase33 canonical public-input ordering
- Phase36 and Phase37 non-claim / source-bound receipt flag surfaces
- Phase45 boundary-width and canonical lane metadata
- Phase47 receipt-only / no-replay / no-false-compression wrapper surface
- Phase48 no-go / no-replay / no-false-recursion wrapper surface

The carry-aware `wrap_delta` witness/divisibility properties are enforced in
this packet by fast exhaustive Rust tests over the full supported `wrap_delta`
range and representative wrapped-accumulator anchors, not by the Kani slice.

The broader `scripts/run_formal_contract_suite.sh` still exists for repository-
wide work, but it is not required for this packet.

## New fuzz surfaces in this packet

This packet adds dedicated fuzz targets for:

- Phase44D source-chain public-output boundary binding
- Phase45 recursive-verifier public-input bridge
- Phase46 Stwo proof-adapter receipt
- Phase47 recursive-verifier wrapper candidate
- Phase48 recursive proof-wrapper attempt
- one raw serialized Phase44D→48 against-sources bundle fuzzer that parses
  an arbitrary artifact bundle and exercises every standalone and
  `*_against_sources` acceptance step in the chain
- one bounded differential mutator that starts from an accepted serialized
  Phase44D→48 chain artifact, applies a semantic post-serialization drift, and
  asserts verifier rejection at the mutated stage and its against-sources check

This closes the earlier gap where the newer Tablero-shaped surfaces had strong
deterministic tamper tests but no dedicated fuzz smoke.
The smoke contract is intentionally modest: the targets are exercised under a
bounded wall-clock budget, and timeout itself is treated as normal completion
as long as libFuzzer emits no crash artifact.

## Exact hardening questions

1. Is the theorem in `docs/engineering/tablero-soundness-note-2026-04-25.md`
   correctly scoped as a statement-preservation theorem rather than a new proof-
   system theorem?
2. Are the local binding assumptions explicit enough, especially around the
   Blake2b commitment surfaces?
3. Do the Phase44D/45/46/47/48 verifiers leave any replay-reintroduction or
   stale-commitment gaps that the current tests miss?
4. Are the carry-aware AIR constraints on `wrap_delta` complete enough for the
   current experimental claim boundary?
5. Is any additional bounded-model-checking harness obviously worth adding for
   the exact binding predicates that replace replay?

## Longer-term escalation path

If the current packet is still not enough, the next honest escalation is:

1. add more bounded Kani harnesses directly on Tablero binding predicates,
2. widen the fuzz corpus for the new artifact surfaces,
3. add optional `cargo-careful` and coverage artifacts into the hardening packet,
4. if theorem-grade certainty is still required, formalize the typed-boundary
   statement in Lean.

That is a real escalation ladder. It is stronger than saying “we tested it a
lot,” and it is more honest than pretending the repository already has proof-
assistant closure.

## External references for the tooling choices

- cargo-nextest: <https://nexte.st/>
- Rust Fuzz Book / cargo-fuzz: <https://rust-fuzz.github.io/book/>
- Kani Rust Verifier: <https://model-checking.github.io/kani/>
- Miri: <https://github.com/rust-lang/miri>
- cargo-careful: <https://docs.rs/crate/cargo-careful/latest>
- cargo-llvm-cov: <https://github.com/taiki-e/cargo-llvm-cov>
- RustSec / cargo-audit / cargo-deny: <https://rustsec.org/>
- StarkWare on proof assistants and S-two soundness work:
  <https://starkware.co/blog/starkwares-gold-standard-of-soundness-with-formal-verification/>
