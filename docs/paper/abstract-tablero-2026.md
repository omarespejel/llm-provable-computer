# Short Abstract: Tablero

Use this version when a submission form or talk proposal asks for a compact abstract.

Tablero is a typed verifier-boundary pattern for layered STARK systems. The motivating
problem is common: a verifier may already have a compact cryptographic statement, yet
still spend most of its wall-clock budget replaying heavier source-side structure such
as ordered manifests, public-input summaries, or wrapper objects. Tablero replaces that
replay path with a compact boundary object whose fields are explicitly bound to the same
accepted statement. The paper's formal claim is narrow: under compact-proof soundness,
commitment binding, and complete source emission of the required public facts, accepting
a well-formed typed boundary preserves the same accepted statement set as replaying the
heavier source surface directly. This is not a new theorem about STARKs and not a
recursive-compression result. It is a criterion for when replay replacement is honest.

We study the pattern in one transformer-shaped STARK-zkML laboratory. On the explicitly
labeled carry-aware experimental backend, across three checked layout families, the same
typed-boundary mechanism exhibits a growing replay-avoidance curve: the typed verifier
path stays comparatively small while the replay baseline grows sharply with input length.
At the checked frontiers, the replay-avoidance ratio ranges from `917.8x` to `1066.6x`.
A log-log fit over the checked experimental grids gives replay-baseline slopes of
`0.9899-0.9921` and typed-path slopes of `0.3508-0.3567`, so the growing ratio is a
measured scaling effect in this regime rather than one isolated frontier point. A
replay-baseline breakdown shows that the
avoided work is distributed across repeated embedded-proof re-verification,
source-chain commitment rebuilds, per-step commitment rebuilds, and manifest
finalization rather than one dominant equality check. A second typed boundary on a
distinct emitted-source surface also clears as supporting positive evidence on the
conservative publication row. The broader engineering sweep on that surface remains
checked in the engineering lane and is not promoted here as a paper-facing claim. The
paper also includes one bounded compactness no-go: a narrower handoff object that
reduces bytes but not verifier latency because it compacts a replay-dependent path
rather than eliminating replay. The contribution is therefore a reusable
verifier-boundary pattern, a statement-preservation criterion for deploying it safely,
and an empirical study of when replay elimination materially changes verifier latency.
