---
applyTo: "src/proof.rs,src/bin/tvm.rs,src/stwo_backend/**/*.rs,tests/**/*.rs,scripts/**/*.py,scripts/**/*.sh"
---

# Trusted-core instructions

- Preserve the explicit split between the shipped carry-free backend `stwo-phase12-decoding-family-v9` and the experimental carry-aware backend `stwo-phase12-decoding-family-v10-carry-aware-experimental`.
- Prefer the smallest sound patch. Avoid opportunistic cleanup in trusted-core PRs.
- If proof semantics, backend routing, manifest or boundary schemas, or benchmark verification logic change, add or update at least one negative, tamper-path, or compatibility test.
- Do not widen paper-facing or default CLI paths to the experimental backend unless the task is specifically about that promotion.
- Keep timing mode, backend version, and claim scope explicit in code and docs when touching benchmark or frontier logic.
