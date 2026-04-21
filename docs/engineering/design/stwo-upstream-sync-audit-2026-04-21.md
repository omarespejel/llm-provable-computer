# S-two Upstream Sync Audit

Snapshot date: **April 21, 2026**.

This note records the local-versus-upstream S-two status at the time the
Phase70-80 proof-checked decode bridge was frozen.

## Repository pin status

The repository currently pins the Rust proving crates in the repo-root
`Cargo.toml` to:

- `stwo = 2.2.0`
- `stwo-constraint-framework = 2.2.0`

These are the active backend crates consumed by the experimental `stwo-backend`
feature in this repository.

## Local clone drift observed

Local clone audited:

- `/Users/espejelomar/StarkNet/zk-ai/stwo-cairo`

Observed on April 21, 2026:

- local `HEAD`: `cf18bdf4710bd084dbcb0af90102e635d5de1935`
- local top commit: `2026-02-12 cf18bdf47 Bump stwo. (#1637)`
- `origin/main`: `01eb5d60767539b02466ec4163723a76ffec3481`
- upstream top commit: `2026-04-19 01eb5d607 Bump stwo and replaces panics with errors. (#1749)`

So the local `stwo-cairo` clone used for engineering inspection is behind the
current upstream branch and should not be treated as a complete representation
of the live upstream state.

## Practical implication for this repository

The experimental backend in `provable-transformer-vm` is pinned to published
`stwo` crates, not to the local `stwo-cairo` working tree. The current freeze
therefore remains valid for the repository's bounded claim surface, but local
clone drift matters for backend-widening decisions and for any claim about
current upstream recursion or tooling posture.

## Audit conclusion

1. Keep the repository's current `stwo = 2.2.0` crate pins explicit until a
   deliberate upgrade lands.
2. Do not block the bounded decode-bridge publication freeze on local
   `stwo-cairo` parity.
3. Before the next backend-widening sprint, refresh the local `stwo-cairo`
   clone and re-audit public recursion / proving-tool surfaces against the
   pinned crates rather than assuming the local clone is current.
4. Treat this note as a narrow engineering audit, not as a benchmark or proof
   of upstream recursion readiness.
