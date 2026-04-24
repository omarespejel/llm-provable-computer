# Phase44D Core-Proving Lane Decision Gate

Date: 2026-04-24

## Scope

This note closes the bounded exploratory lane that followed the merged overflow
provenance work.

Requested sequence:

1. `phase12-arithmetic-budget-map`
2. `phase44d-rescaled-exploratory-sweep`
3. `carry-aware-arithmetic-subset-design-note`
4. `carry-aware-arithmetic-subset-prototype`
5. `honest-4-step-proof-attempt`
6. `phase44d-honest-scaling-rerun`
7. decision gate

The goal was to answer one question cleanly:

> Is Phase44D scaling blocked only by the current i16 carry ceiling, or can a
> bounded rescaling unblock an honest higher-step result without opening a new
> proving lane?

## Artifacts

Checked evidence:

- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/evidence/phase12-arithmetic-budget-map-2026-04.tsv`
- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/evidence/phase12-arithmetic-budget-map-2026-04.json`
- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/evidence/phase44d-rescaling-frontier-2026-04.tsv`
- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/evidence/phase44d-rescaling-frontier-2026-04.json`

Figures:

- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/figures/phase12-arithmetic-budget-map-2026-04.svg`
- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/figures/phase44d-rescaling-frontier-2026-04.svg`

Supporting notes:

- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/phase44d-overflow-provenance-2026-04-24.md`

## Result

### 1. Default Phase12 arithmetic headroom has a real cliff, not a soft slope

The default-source arithmetic budget map confirms the previously identified
first blocked seed and shows that the failure is not a local one-off.

Key facts from
`phase12-arithmetic-budget-map-2026-04.tsv`:

- The first blocked seed appears at `steps=4`, `seed_step_index=3`.
- The first carry-bearing transition is still the same checked event:
  - runtime step `45`
  - instruction `MulMemory(28)`
  - raw accumulator `87872`
- At `steps=4`, the maximum absolute raw accumulator already reaches `180864`.
- By `steps=5`, the maximum absolute raw accumulator reaches `2659456`.
- From `steps=10` onward, the blocked set grows roughly linearly with the step
  count.
- At `steps=64`, `55` of `64` seeds are blocked by the current execution-proof
  surface.

The important point is not just that overflow happens; it is that the default
Phase12 family exits the carry-free regime almost immediately and then stays
far outside it.

### 2. Bounded benchmark-side rescaling does not rescue honest `4+` Phase44D

The exploratory Phase44D rescaling search used the same `decoding_step_v2`
program family and only changed seed magnitudes:

- incoming-value divisors in `{1, 2, 4, ..., 512}`
- lookup-seed divisors in `{1, 2, 4, ..., 512}`
- nonzero-preserving rounding for both surfaces

The resulting feasibility frontier is simple:

- `steps=2`: verified with the identity profile `incoming_divisor=1`,
  `lookup_divisor=1`
- `steps=4, 8, 16, 32, 64`: no feasible profile in the search grid

So the exploratory lane answered the central question decisively:

> shrinking incoming magnitudes alone is not enough, and even shrinking both
> incoming magnitudes and lookup-seed magnitudes across a broad bounded search
> grid does not recover an honest proof-checked `4`-step Phase12 chain.

That means the barrier is already deeper than a benchmark-only rescaling fix.

### 3. The carry-aware subset prototype is real, but it is only a witness surface

A narrow prototype was added in
`src/stwo_backend/arithmetic_subset_prover.rs`.

It does not claim a new proof system. It does one smaller thing:

- given a supported arithmetic-subset trace,
- extract per-step carry-aware rows containing:
  - instruction
  - operand
  - raw accumulator
  - wrapped accumulator
  - wrap delta
  - carry-after flag

On the honest failing `4`-step Phase12 seed, the prototype captures the first
carry-bearing row exactly:

- prototype row index `44`
- instruction `MulMemory(28)`
- `acc_before = 1373`
- `operand = 64`
- `raw_acc = 87872`
- `wrapped_acc = 22336`
- `wrap_delta = 1`
- `carry_after = true`

This is useful because it proves the trace can be described cleanly with an
explicit wrap witness.

It is **not** yet a proof.

### 4. Honest 4-step proof attempt: still blocked

The honest `4`-step proof attempt remains blocked on the current proof surface.

What changed in this spike is that the failure mode is now separated cleanly:

- default Phase12 path: blocked by the current carry-free execution-proof
  surface
- bounded rescaling path: still blocked, even after expanding the research-only
  profile to both incoming and lookup-seed divisors
- prototype path: a carry-aware witness description exists, but the active AIR
  does not consume it

### 5. Honest scaling rerun: no new higher-step Phase44D result

The honest Phase44D scaling rerun does **not** produce a new `4+` verified
curve.

The only verified point in the bounded exploratory search remains the existing
`2`-step point, which is the already published identity-profile result.

So there is no honest higher-step Phase44D scaling result to add to the current
paper.

## Why the current AIR is the blocker

The carry-aware prototype did not uncover a hidden easy patch.

The active arithmetic-subset proving surface still assumes carry-free rows in
multiple places:

1. witness validation rejects `carry_flag = true`
2. AIR constraints force both current and next carry columns to zero
3. next-acc constraints bind directly to the arithmetic result without an
   explicit wrap witness

So the prototype validates a design direction, but it also confirms that the
real next move is architectural, not cosmetic.

## Decision gate

### Verdict

**Do not treat this as a quick Phase44D benchmark extension.**

The bounded exploratory lane did useful work, but it did not unblock honest
higher-step Phase44D scaling.

### What this means

- **For the current paper:** keep the existing Phase44D result exactly where it
  is. The `2`-step verify-latency result is real. Do not overclaim beyond it.
- **For benchmark-side tweaks:** stop. Incoming-only rescaling failed. Expanded
  incoming-plus-lookup rescaling also failed.
- **For the next real research lane:** if we want `4+` honest Phase44D scaling,
  the next lane is a genuine carry-aware or wider execution-proof redesign.

### Recommended next move

If the goal is higher upside rather than immediate paper polish, open the new
lane explicitly with one hard gate:

> prove the honest default `4`-step Phase12 seed on a carry-aware or widened
> execution-proof surface

If that gate does not clear, stop.

## Reproduction

Generate the arithmetic map:

```bash
target/debug/tvm bench-stwo-phase12-arithmetic-budget-map \
  --output-tsv docs/engineering/evidence/phase12-arithmetic-budget-map-2026-04.tsv \
  --output-json docs/engineering/evidence/phase12-arithmetic-budget-map-2026-04.json \
  --max-steps 64
```

Probe the rescaling frontier:

```bash
. .venv/bin/activate
python scripts/engineering/generate_phase44d_rescaling_frontier.py \
  --tvm-binary target/debug/tvm \
  --output-tsv docs/engineering/evidence/phase44d-rescaling-frontier-2026-04.tsv \
  --output-json docs/engineering/evidence/phase44d-rescaling-frontier-2026-04.json
```

Render the figures:

```bash
. .venv/bin/activate
python scripts/engineering/generate_phase12_arithmetic_budget_map_figure.py
python scripts/engineering/generate_phase44d_rescaling_frontier_figure.py
```

Targeted regression checks:

```bash
cargo +nightly-2025-07-14 test --features stwo-backend --lib \
  phase12_arithmetic_budget_map_surfaces_first_blocked_four_step_seed -- --nocapture
cargo +nightly-2025-07-14 test --features stwo-backend --lib \
  phase44d_rescaled_exploratory_benchmark_still_cannot_clear_honest_four_steps -- --nocapture
cargo +nightly-2025-07-14 test --features stwo-backend --lib \
  carry_aware_subset_prototype_captures_honest_phase12_four_step_overflow_row -- --nocapture
```
