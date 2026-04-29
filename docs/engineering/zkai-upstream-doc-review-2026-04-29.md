# zkAI upstream doc review: proof validity vs statement validity - 2026-04-29

## Purpose

Decide whether the `proof is not a statement` result should become upstream
issues against EZKL or snarkjs now.

Decision: **do not open vulnerability-style upstream issues from this result.**
The current evidence supports a constructive documentation/proposal thread about
statement-binding receipts, not a bug report against either verifier.

## Sources checked

- EZKL verification docs: <https://docs.ezkl.xyz/getting-started/verify/>
- snarkjs README / Groth16 verification docs: <https://github.com/iden3/snarkjs>

## What the docs say

EZKL documents verification as proof validation over the proof artifact,
verification key, settings file, and SRS, with on-chain verifier calls taking
proof data and public inputs. The page frames the result as proof validity.

snarkjs documents Groth16 proof creation as producing `proof.json` and
`public.json`, then verifies with `verification_key.json`, `public.json`, and
`proof.json`. The README states that `OK` means the proof is valid.

## What the docs do not appear to claim

The reviewed docs do not appear to claim that raw proof verification binds
external application metadata such as:

- model display name,
- product policy label,
- deployment domain,
- non-public input labels,
- off-circuit output descriptions,
- surrounding agent/action context.

That means our adapter result should not be framed as `EZKL is broken` or
`snarkjs is broken`.

## Constructive upstream framing

If we open upstream issues later, use documentation/proposal language:

> This is not a proof-system bug. We found that zkAI integrations can pass raw
> proof verification while relabeling model/input/output metadata unless that
> metadata is explicitly committed as part of the verified statement. We propose
> an optional statement-receipt wrapper that binds proof bytes, public inputs,
> model artifact commitment, input/output commitments, policy labels, verifier
> identity, and setup/verifying-key identity.

## Recommended upstream path

1. First finish the local Stwo-native receipt gate so the claim is not only about
   external systems.
2. Publish or circulate the paper section as an ecosystem note.
3. Then open upstream documentation issues only if they are scoped as optional
   integration guidance for zkAI applications.

## Current decision

Do not open upstream issues yet. Open one later only if the goal is a constructive
receipt/API documentation proposal, not a security report.
