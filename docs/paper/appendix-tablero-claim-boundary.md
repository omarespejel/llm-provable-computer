# Appendix: Claim Boundary for the Presentation Draft

This appendix makes the paper's positive and negative claim surfaces explicit.

## Positive claim surface

The paper claims only the following.

| Surface | Honest claim |
| --- | --- |
| Typed verifier boundary | A verifier can replace an expensive replay surface with a typed boundary object when that object is complete, well formed, and commitment-bound to the same compact claim. |
| Formal guarantee | Under upstream compact-proof soundness, commitment binding, and source-emission completeness, Tablero preserves the same accepted statement set as the replay verifier. |
| Empirical evidence | In the current transformer-shaped empirical lab, the main typed boundary reproduces across three layout families with a growing-in-`N` replay-avoidance curve. |
| Supporting second boundary | A distinct emitted-source surface also clears as a real second typed boundary with smaller but still growing verifier-side gains. |
| Negative evidence | A narrower compact handoff object is reported honestly as a compactness-only surface rather than a replay-avoidance win. |
| Assurance posture | Deterministic tamper tests, bounded model checking, differential fuzzing, and fail-closed runtime guards materially reduce implementation-side self-deception risk. |

## Negative claim surface

The paper does **not** claim the following.

| Surface | Explicit non-claim |
| --- | --- |
| New STARK theorem | No new soundness theorem for STARKs or for S-two itself. |
| Backend independence | No empirical proof that the pattern is backend independent today. |
| Recursive compression | No recursive verifier, no proof-carrying data theorem, and no incrementally verifiable computation construction. |
| Universal speedup | No claim that typed boundaries always improve verifier performance. |
| Implementation-invariant baseline | No claim that every manifest implementation in every system would pay the same replay cost as this codebase. |
| Full zkML frontier result | No claim of full end-to-end transformer inference proving or a matched full-model benchmark against public competitors. |
| Onchain deployment | No claim that the typed-boundary path itself has already been deployed onchain. |

## Talk-safe summary

If this paper is presented orally, the safest one-sentence summary is:

> Tablero is a typed verifier-boundary pattern for layered STARK systems: when the
> source side emits the right proof-native facts, the verifier can replace an expensive
> replay path with a compact boundary object without widening what it accepts.

The safest one-sentence warning is:

> The large latency ratios in this paper are replay-avoidance results on the current
> implementation, not claims that cryptographic STARK verification itself became
> hundreds of times faster.
