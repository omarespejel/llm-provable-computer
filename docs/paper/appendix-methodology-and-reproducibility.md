# Appendix: Methodology and Reproducibility

This appendix states exactly how the paper's claims should be read and how the checked
numbers were produced.

## 1. Evidence categories

The paper combines four evidence categories.

1. **Formal claim surface.** The theorem in the main paper is a statement-preservation
   theorem for typed verifier boundaries under explicit assumptions.
2. **Empirical typed-boundary evidence.** The main measurements compare a typed-boundary
   verifier path against the heavier replay path it is designed to replace.
3. **Negative evidence.** One candidate boundary is reported as a no-go because the
   source side did not emit enough proof-native material and the eliminated dependency
   was not expensive enough to justify the pattern.
4. **External calibration.** Public external rows are used only to position the work by
   verifier-facing regime, not to claim a matched race against another system.

These categories should not be collapsed into one slogan. The paper is strongest when
formal, empirical, negative, and calibration evidence remain visibly distinct.

## 2. Timing policy

The primary replay-avoidance curves in the paper use checked median-of-five timing
capture from the local benchmark harness. The policy is intentionally stronger than a
single-run anecdote and intentionally narrower than a cross-lab benchmarking campaign.

The result should therefore be read as follows:

- the trend is strong enough to support a paper claim about curve shape,
- the constants are strong enough to support a paper claim about replay avoidance in the
  current implementation, and
- the numbers are not meant to stand in for every hardware target or every possible
  verifier implementation.

## 3. What the large ratios mean

The paper's large ratios are implementation grounded. They compare a typed verifier path
against the replay baseline that this codebase actually pays today.

That baseline performs ordered canonical serialization, hashing, and replay
reconstruction work. The typed boundary removes that work from the verifier path by
carrying the same public facts in a compact boundary object that is bound to the same
accepted statement.

That is a real verifier-side improvement. It is **not** a claim that cryptographic STARK
verification itself became hundreds of times faster, and it is **not** a universal lower
bound on all possible replay implementations.

## 4. What the cross-family result means

The strongest empirical result in the paper is not one frontier number. It is that the
same replay-avoidance mechanism reproduces across three checked layout families with the
same qualitative shape.

The families do **not** share the same constants. One family yields a much larger
frontier ratio than the others. That does not weaken the paper's main point. It clarifies
it:

- the **mechanism** is stable across the checked families,
- the **magnitude** of the gain depends on family structure, and
- the typed boundary's artifact size stays in a narrow band while verifier cost remains
  family dependent.

## 5. Reproducibility handles

The paper package is designed so that the exact public-facing numbers come from checked
machine-readable evidence and not from prose drift.

Use these directories as the canonical handles:

- `docs/paper/evidence/` for checked TSV and JSON values used in the paper package,
- `docs/paper/figures/` for generated paper figures,
- `scripts/paper/` for generation and preflight scripts.

The release gate for the paper package should always include:

- `python3 scripts/paper/paper_preflight.py --repo-root .`
- the unit tests for any paper-specific generation script that changed,
- `git diff --check`

## 6. Safe public wording

The safest public wording is:

> Tablero removes a verifier-side replay cost by replacing it with a typed,
> commitment-bound boundary object, while preserving the same accepted statement under
> explicit assumptions.

The safest public warning is:

> The large ratios in this paper are replay-avoidance results on the current
> implementation, not a claim that all STARK verification or all replay implementations
> would show the same constants.
