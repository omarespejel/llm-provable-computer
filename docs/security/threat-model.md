# Threat Model

This document defines the security posture of the repository's public proof and
artifact surfaces as of April 22, 2026.

The scope is intentionally narrow. The repository exposes:

- tensor-native `stwo` lookup and transformer-shaped artifacts,
- decode / carried-state / manifest-binding artifacts,
- a legacy vanilla `statement-v1` proving baseline,
- differential-testing surfaces across transformer/native/Burn/ONNX engines.

These surfaces do **not** all make the same kind of claim. This document keeps that
boundary explicit.

## Security Objectives

For the surfaces treated as cryptographic or verifier-bound, the repository aims to:

- reject malformed, oversized, or schema-drifted inputs before expensive work when practical,
- bind each accepted artifact to its declared backend, backend version, statement version,
  and semantic scope,
- reject reordered, substituted, replayed, or cross-wired public inputs and nested artifacts,
- keep shared-table identity and carried-state continuity verifier-visible when the artifact
  claims those properties,
- fail closed when an input exceeds the implemented scope,
- keep public documentation aligned with what the verifier actually enforces.

## Claim Classes

The repository exposes four distinct claim classes.

### 1. Cryptographic proof

Examples:

- vanilla `statement-v1` execution proofs,
- direct `stwo` lookup proofs,
- direct fixed-shape `stwo` execution proofs.

Meaning:

- the verifier checks a proof object against the implemented backend relation,
- the verifier enforces the proof's declared backend and statement metadata,
- acceptance is intended to be infeasible for a probabilistic polynomial-time adversary
  except with the residual soundness error of the backend and profile.

### 2. Verifier-bound artifact

Examples:

- tensor-native chain artifacts,
- shared-table identity artifacts,
- repeated-window fold artifacts,
- accumulation-semantics artifacts,
- bounded decode / carried-state artifacts.

Meaning:

- the verifier recomputes commitments and structural relations from serialized fields and
  supplied source artifacts,
- acceptance implies the artifact is internally consistent with the implemented relation,
- this is **not** automatically a recursive proof or cryptographic compression claim.

### 3. Differential-testing artifact

Examples:

- `--verify-native`,
- `--verify-all`,
- `research-v2`,
- `research-v3`.

Meaning:

- independent execution engines are compared for semantic agreement,
- these checks are strong engineering oracles and regression guards,
- they are **not** themselves cryptographic proof claims.

### 4. Publication evidence bundle

Examples:

- frozen artifact directories under `docs/paper/artifacts/`.

Meaning:

- a bundle freezes commands, hashes, timings, and outputs for reproducibility,
- the bundle may contain cryptographic proofs, verifier-bound artifacts, or differential
  artifacts,
- the bundle's existence does **not** widen the underlying proof claim beyond what the
  embedded verifier actually checks.

## Adversary Model

Unless otherwise stated, the adversary is a probabilistic polynomial-time prover or
artifact producer who can:

- choose arbitrary serialized inputs,
- mutate nested proof payloads and manifests,
- reorder public inputs, lookup rows, or step members,
- substitute different backend/version labels,
- splice commitments from unrelated artifacts,
- replay stale artifacts or package-count summaries,
- craft documentation or publication metadata that overstates the verified scope.

The adversary cannot break the underlying hash functions, finite-field arithmetic, or
backend soundness assumptions outright, except with the residual error budget admitted by
those systems.

## In-Scope Adversaries

- `malformed artifact producer`: emits structurally invalid manifests, payloads, or nested proof envelopes.
- `oversized input producer`: attempts denial-of-service via large JSON, nested payloads, or excessive member counts.
- `backend confusion attacker`: mixes vanilla and `stwo` artifacts, versions, or proof families.
- `scope drift attacker`: rewrites statement version, semantic scope, or proof-family labels without matching source changes.
- `shared-table substitution attacker`: swaps the intended lookup table or registry while preserving surrounding structure.
- `carried-state splice attacker`: stitches together artifacts whose boundaries do not legitimately line up.
- `public-input ordering attacker`: reorders commitments or member lists while preserving the multiset of values.
- `replayed artifact producer`: reuses stale outputs for a new claimed execution.
- `provenance forgery attacker`: forges commit ids, labels, or bundle metadata to imply evidence that was not actually produced.
- `paper overclaim attacker`: states that a verifier-bound or differential-testing artifact proves more than it does.

## Trusted Inputs and Assumptions

The repository assumes the following are trusted at the level stated.

### Backend assumptions

- The vanilla backend and the upstream `stwo` stack are assumed sound only within their
  implemented and declared scope.
- The repository does **not** claim to re-prove backend soundness.
- `publication-v1` for the vanilla path is a repository-level verifier floor based on the
  current conjectured-security estimator; it should be treated as stronger than
  `production-v1`, but it does not by itself prove any external conservative-bit theorem.
- At the CLI layer, `publication-v1` is restricted to the vanilla backend; the CLI
  rejects `publication-v1` when invoked with non-vanilla backends.

### Environment assumptions

- Local machines, CI runners, and compilers are not adversarially compromised.
- File I/O, JSON parsers, and standard library behavior are trusted up to the hardening
  checks in this repository.

### Frozen-bundle assumptions

- Frozen bundle hashes and command logs are treated as provenance objects.
- They show reproducibility of the recorded run, not a theorem about every future run.

## Valid Input Classes

An input is only in scope when all of the following hold.

- The artifact parses under the expected schema and version.
- The backend and backend-version fields match the verifier surface being invoked.
- The statement version and semantic scope match the implemented verifier contract.
- Nested artifacts, lookup registries, and carried boundaries are supplied when the
  verifier requires them.
- Resource bounds are not exceeded.

Inputs outside those classes are intended to be rejected, not normalized into scope.

## What the Repository Intends to Prevent

For accepted inputs, the repository aims to prevent:

- acceptance of malformed or truncated artifacts,
- acceptance of backend-swapped or version-swapped proofs,
- silent drift between statement metadata and verifier semantics,
- reuse of a different shared table under the same descriptive label,
- carried-state continuity claims that do not actually line up,
- acceptance of reordered or cross-wired member families when order matters,
- paper or README text that implies recursive proof closure, cryptographic compression,
  or full standard-softmax transformer proving where those properties are not implemented.

## Explicit Non-Goals

This repository does **not** currently attempt to:

- prove full standard-softmax transformer inference end to end,
- prove recursive cryptographic accumulation or generic custom-AIR recursion closure,
- prove implementation equivalence of every runtime backend cryptographically,
- prove model correctness, truthfulness, or training-data properties,
- defend against compromise of the local machine, CI runner, or external package supply chain,
- establish universal STARK-over-SNARK wall-clock superiority.

## Residual Risks

The main residual risks are:

- undocumented over-interpretation of verifier-bound artifacts as recursive proofs,
- performance conclusions drawn from symbolic or artifact-size models without matched
  benchmark validation,
- stale documentation that continues to describe archival or local-baseline surfaces as if
  they were the main publication result,
- future widening of artifact schemas without matching negative-path tests or fuzz coverage.

## Operational Policy

Public-facing text in this repository should follow these rules.

- Treat tensor-native `stwo` artifacts as the main research line.
- Treat decode / carried-state artifacts as supporting evidence unless the verifier surface
  itself is the subject of the claim.
- Treat `--verify-all` and related multi-engine checks as differential testing, not proof.
- Treat vanilla artifacts at the `production-v1` profile as the local reproducibility
  baseline unless a document explicitly says it is using the stronger
  `publication-v1` vanilla tier.
- Do not describe folded, repeated-window, or accumulation-semantics artifacts as
  recursive cryptographic compression.
