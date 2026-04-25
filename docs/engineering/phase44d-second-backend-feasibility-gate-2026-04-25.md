# Phase44D Second-Backend Feasibility Gate (April 25, 2026)

Date: 2026-04-25

## Scope

This note closes issue `#259`:

> does the Phase44D replay-avoidance pattern survive a second execution-proof
> backend, or are the current transferability claims still limited to multiple
> layout families on the same carry-aware backend?

The goal here is not to force a positive result. The goal is to record an
honest backend-transferability verdict without smoothing over the blocker.

## Evidence base

Checked evidence already in the repository:

- `docs/paper/evidence/stwo-phase44d-source-emission-2026-04.tsv`
- `docs/paper/evidence/stwo-phase44d-source-emission-2026-04.json`
- `docs/engineering/evidence/phase44d-rescaling-frontier-2026-04.tsv`
- `docs/engineering/evidence/phase44d-rescaling-frontier-2026-04.json`
- `docs/engineering/phase44d-core-proving-lane-decision-gate-2026-04-24.md`

Fresh spot checks on current `origin/main`:

```bash
cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  bench-stwo-phase44d-source-emission-reuse \
  --output-tsv target/issue259-default-2.tsv \
  --output-json target/issue259-default-2.json \
  --step-counts 2 \
  --capture-timings

cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  bench-stwo-phase44d-rescaled-exploratory \
  --output-tsv target/issue259-rescaled-2-4.tsv \
  --output-json target/issue259-rescaled-2-4.json \
  --step-counts 2,4 \
  --capture-timings
```

The first command reran the shipped carry-free Phase44D surface at the checked
`2`-step point. The second command reran the bounded carry-free rescaling probe
at `2,4` steps and reproduced the exact `4`-step blocker.

## What is real on the shipped carry-free backend

The shipped carry-free backend already shows the same Phase44D mechanism at the
checked `2`-step point. The checked median-of-5 publication evidence records:

| Surface | Verify time |
|---|---:|
| Typed Phase44D boundary + compact proof | `0.957 ms` |
| Phase30 manifest replay baseline + compact proof | `16.688 ms` |
| Compact Phase43 proof only | `0.456 ms` |
| Phase30 replay only | `15.856 ms` |
| Phase44D boundary binding only | `0.399 ms` |

So the mechanism itself is not experimental-only. Even on the shipped carry-free
backend, the typed boundary avoids a real verifier-side replay surface and the
causal split is the same one seen on the experimental lane:

- compact proof verification remains in both paths;
- the skipped work is the Phase30 replay surface;
- the saved work is not a faster FRI or faster cryptographic verifier.

The fresh single-run spot check on current `origin/main` reproduced the same
qualitative split with the current binary:

| Surface | Verify time |
|---|---:|
| Typed Phase44D boundary + compact proof | `15.238 ms` |
| Phase30 manifest replay baseline + compact proof | `269.882 ms` |
| Compact Phase43 proof only | `6.251 ms` |
| Phase30 replay only | `256.365 ms` |
| Phase44D boundary binding only | `6.237 ms` |

Those single-run timings are host-dependent and not paper-facing numbers.
They matter here only because they confirm that the mechanism still exists on
the current mainline checkout.

## What does not survive today

There is still no honest growing-in-`N` reproduction on the carry-free backend.

The checked rescaling frontier already records:

- `steps=2`: verified with the identity profile
- `steps=4,8,16,32,64`: blocked

The exact blocker is unchanged:

> `phase44d rescaled exploratory benchmark could not find a carry-free rescaling profile that supports a proof-checked 4-step Phase12 source chain`

The fresh `2,4` rerun on current `origin/main` reproduced that same blocker
verbatim.

So the honest cross-backend picture is:

- the carry-free backend does reproduce the Phase44D replay-avoidance mechanism
  at one narrow checked point;
- it does **not** currently reproduce the growing verifier-latency curve shape
  that makes the experimental carry-aware result interesting;
- the blocker is still the underlying carry-free Phase12 execution-proof
  surface, not the Phase44D typed-boundary logic.

## Honest read

### What this gate proves

- Phase44D replay avoidance is not unique to the carry-aware backend.
- The typed boundary is architecturally real on the shipped carry-free route.
- The causal story still holds on the second backend: compact proof stays,
  Phase30 replay goes away.

### What this gate does not prove

- It does **not** justify calling Tablero backend-independent today.
- It does **not** justify quoting the experimental growing-in-`N` curve as a
  second-backend result.
- It does **not** reopen the carry-free lane as a frontier-scaling program.

## Decision

### Verdict

**NO-GO for claiming Phase44D backend transferability today.**

### Reason

The second backend only clears the single checked `2`-step point. It does not
clear an honest `4+` proof-checked source chain, even under the bounded
carry-free rescaling search. Without that, the repo cannot support the real
backend-transferability claim that matters here:

> the same replay-avoidance mechanism opens a widening verifier-latency gap on
> a second execution-proof backend.

### Narrow positive result worth keeping

The carry-free `2`-step checkpoint is still useful. It shows that the typed
boundary mechanism itself is not tied to the experimental backend. What is tied
to the experimental backend today is the scalable `4+` source-chain family.

## Next move

Do not spend more time trying to squeeze a positive backend-transferability
claim out of the current carry-free Phase12 family.

Reopen this question only if one of these happens:

1. a new honest non-overflow carry-free source family lands and can drive the
   same Phase44D benchmark beyond `2` steps, or
2. another explicitly bounded execution-proof backend lands first.

Until then, treat the backend-transferability question as bounded and closed,
and keep the next wave pointed at:

- SNIP-36 deployment viability on a narrow proof object; and
- explanation of the already-landed family-matrix constants rather than more
  carry-free frontier chasing.
