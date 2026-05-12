# zkAI Production Path: Starknet/Stwo Backbone - 2026-05

## Purpose

This is the production path implied by the current paper claim pack. It keeps
the claim sequence explicit: the repo has checked STARK-native proof-architecture
evidence for bounded integer attention and Softmax-table membership fusion, but
it has not crossed into runtime, public benchmark, production, or Starknet
deployment claims.

## Phase 0 - Current Artifact Discipline

Status: `GO_ENGINEERING_EVIDENCE_DISCIPLINE`

- Keep every frontier claim backed by checked JSON/TSV evidence and a focused
  local gate.
- Keep artifact outputs in `docs/engineering/evidence/` and paper-facing claim
  packs in `docs/paper/`.
- Treat generated evidence as untrusted I/O: constrain paths, reject symlinks,
  write atomically, and validate schema/claim boundaries before citing.
- Continue separating proof-size evidence, timing evidence, runtime evidence,
  and deployment evidence.

Release gate:

- `just gate-fast`
- `python3 scripts/zkai_paper_claim_pack_gate.py --write-json docs/paper/evidence/stark-native-transformer-claim-pack-2026-05.json`
- `python3 -m unittest scripts.tests.test_zkai_paper_claim_pack_gate`
- `git diff --check`
- `just gate`

## Phase 1 - Binary Proof Accounting

Status: `GO_LOCAL_TYPED_ACCOUNTING`, `NO_GO_UPSTREAM_STWO_WIRE_FORMAT`

Current handle:

- `docs/engineering/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05-12.md`
- `docs/engineering/evidence/zkai-attention-kv-stwo-binary-typed-proof-accounting-2026-05.json`

Next gates:

1. Extend repo-owned typed accounting beyond the d32 matched slice to the full
   checked route matrix.
2. Add stable version pins for every typed component inventory.
3. Keep upstream Stwo proof serialization as a blocker until verifier-facing
   binary bytes are available and checked.

Exit criterion:

- A release candidate can explain exact local typed accounting bytes for every
  proof object it packages, with no claim that those bytes are upstream Stwo
  wire-format bytes.

## Phase 2 - Timing Discipline

Status: `GO_ENGINEERING_LOCAL_MEDIAN_OF_5_DISCIPLINE`, `NO_GO_PUBLIC_BENCHMARK`

Current handle:

- `docs/engineering/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05-12.md`
- `docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.json`

Next gates:

1. Keep median-of-5 verifier timing as engineering-local discipline.
2. Add host metadata, CPU pinning policy, thermal notes, and reproducibility
   constraints before any paper-facing performance claim.
3. Do not turn the current timing result into a fused verifier-time win; the
   measured fused routes were slower than source-plus-sidecar median sums on
   this host.

Exit criterion:

- Timing can be used as a release health metric, not as a public performance
  claim, until a stronger benchmark policy is adopted.

## Phase 3 - Model-Faithful Quantized Attention

Status: `GO_D8_TRACE_BOUNDARY_BRIDGE`, `NO_GO_FULL_RUNTIME`

Current handle:

- `docs/engineering/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.md`
- `docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.json`

Next gates:

1. Bind the quantized policy to a real model import path.
2. Add tokenizer, weights, and runtime configuration commitments.
3. Measure accuracy/perplexity delta against the quantized policy before model
   claims.
4. Extend beyond the checked d8 fixture trace without changing the Softmax
   claim boundary.

Exit criterion:

- A model artifact can state exactly which quantized attention policy it uses,
  which trace rows are checked, and which runtime/model commitments are bound.

## Phase 4 - Verifier and Proof Packaging

Status: `NO_GO_RELEASE_PACKAGING`

Next gates:

1. Package proof envelopes, typed accounting, evidence commitments, and
   non-claim metadata into one verifier-facing bundle.
2. Add compatibility tests for schema versions, backend versions, proof-backend
   inventory, and rejected overclaim fields.
3. Define the minimal verifier API: proof bytes, public statement, table
   commitment, route metadata, claim boundary, and evidence commitment.
4. Add replay and tamper tests for bundle relabeling, stale evidence, missing
   non-claims, backend-version drift, and route mismatch.

Exit criterion:

- A local verifier can reject malformed or overclaimed packages without relying
  on prose docs.

## Phase 5 - Starknet/Stwo Integration

Status: `NO_GO_STARKNET_DEPLOYMENT`

Next gates:

1. Decide whether Starknet integration verifies native Stwo proofs directly,
   verifies a wrapped proof, or records a settlement/attestation object for an
   off-chain verifier.
2. Account calldata, storage, verifier cost, and proof-object binary format.
3. Bind chain ID, verifier version, route ID, statement commitment, table
   commitment, and evidence commitment in the on-chain or settlement surface.
4. Add Sepolia rehearsal gates before any mainnet wording.

Exit criterion:

- A Starknet integration candidate has a checked verifier/settlement path,
  deployment artifacts, chain-specific addresses, and tamper-path tests.

## Phase 6 - Security Hardening

Status: `NO_GO_SECURITY_RELEASE`

Hardening gates:

- Reject symlinked or out-of-tree evidence inputs.
- Bound proof and evidence input sizes.
- Pin exact backend versions and proof backend inventories.
- Reject claim-boundary drift and non-claim removal.
- Add rollback-safe atomic writes for generated evidence.
- Add negative tests for stale proof envelopes, route relabeling, table
  commitment drift, model-policy drift, and backend-version drift.
- Separate publication/default-lane claims from experimental-lane results.

Exit criterion:

- The release candidate fails closed on malformed artifacts, stale evidence,
  relabeled claims, and missing non-claims.

## Phase 7 - Release Gates

Status: `NO_GO_PRODUCTION_RELEASE`

Minimum gates before production language:

1. Stable verifier-facing proof bytes, not only local typed accounting.
2. Checked package schema and local verifier with adversarial negative tests.
3. Reproducible timing policy with host metadata and release threshold.
4. Model import, runtime, tokenizer/weights, and accuracy/perplexity evidence.
5. Starknet integration path with network-specific deployment evidence.
6. Security review of artifact handling, verifier inputs, and claim-boundary
   enforcement.
7. Clear rollback and incident-response plan for bad evidence or verifier
   regressions.

Until those gates pass, the correct public posture remains:

> Bounded STARK-native proof-architecture evidence for fusing attention
> arithmetic and Softmax-table membership, with checked artifact discipline and
> an explicit production path.
