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

We study the pattern in one transformer-shaped STARK-zkML laboratory. Across three
checked layout families, the same typed-boundary mechanism exhibits a growing replay-
avoidance curve: the typed verifier path stays comparatively small while the replay
baseline grows sharply with input length. At the checked frontiers, the replay-avoidance
ratio ranges from `250.6x` to `925.1x`, with the dominant avoided cost coming from the
verifier-side replay path itself rather than faster cryptographic verification. The
paper also includes a bounded negative result showing that the pattern does not apply
honestly when the source side emits too little proof-native material or when the
candidate replay surface is already cheap. The contribution is therefore a reusable
verifier-boundary pattern, a statement-preservation criterion for deploying it safely,
and an empirical study of when replay elimination materially changes verifier latency.
