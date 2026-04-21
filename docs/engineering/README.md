# Engineering Docs

This directory contains engineering-facing material that supports implementation work but is not part of the paper package.

Contents:

- `ai-review-security-setup.md`: first-party Anthropic and OpenAI review/security setup for this repository
- `design/`: implementation and artifact-line design notes
- `design/engineering-timeline.md`: detailed internal phase chronology moved out of the public README
- `design/stwo-upstream-sync-audit-2026-04-21.md`: refreshed `stwo` / `stwo-cairo` upstream audit and pinning note
- `hardening-policy.md`: local CI, hardening, and merge-gate policy
- `paper2-claim-evidence.yml`: machine-readable claim-to-evidence ledger enforced by paper preflight
- `paper2-roadmap.md`: engineering roadmap for bounded paper-2 implementation hardening and provenance/reproducibility work
- `stark-vs-snark-transformer-answer-2026-04-21.md`: exact current answer to the transformer/STARK-versus-SNARK question with current metrics
- `tensor-native-phase89-95-roadmap.md`: post-freeze roadmap that shifts the main breakthrough route to tensor-native, lookup-aware S-two proofs
- [`../security/`](../security/): threat model and red-team matrix for artifact binding, provenance, and `backend-confusion`
- `reproducibility.md`: broader engineering reproducibility guidance, including non-paper artifact flows

These files may use repository-internal terminology and phase labels because they document implementation sequencing rather than publication claims.
