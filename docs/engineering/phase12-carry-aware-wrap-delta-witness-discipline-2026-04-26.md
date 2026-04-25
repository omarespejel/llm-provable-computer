# Carry-Aware `wrap_delta` Witness Discipline (April 26, 2026)

This note narrows one specific soundness surface in the experimental
carry-aware Phase12 arithmetic-subset AIR: the witness discipline around
`wrap_delta`.

It is not a proof of the full execution proof. It states the smaller property
we actually need to avoid fooling ourselves about overflow handling:

- host-side trace construction emits only integer `wrap_delta` values whose
  quotient interpretation is well-defined;
- the AIR constrains the auxiliary witness columns so an accepted row cannot
  reinterpret that quotient as an arbitrary M31 field element;
- ADD/SUB rows are further pinned to the unit range `{ -1, 0, 1 }`.

## Scope

This note covers the experimental backend surface in
`src/stwo_backend/arithmetic_subset_prover.rs`:

- `carry_aware_wrap_delta`
- `carry_aware_wrap_delta_range_witness`
- the AIR constraints over
  `wrap_delta`, `wrap_delta_inv`, `wrap_delta_square`, `wrap_delta_abs`,
  `wrap_delta_sign`, and `wrap_delta_abs_bits[*]`

It does **not** claim:

- full correctness of the VM transition relation;
- soundness of unrelated witness columns;
- backend-independence;
- promotion of the experimental carry-aware lane into the default/publication
  lane.

## Notation

Let:

- `B = 2^16` be the carry wrap basis;
- `raw_acc` be the unwrapped active accumulator for a carry-sensitive row;
- `next_acc` be the wrapped `i16` accumulator stored in the next machine state;
- `delta` be the integer quotient `(raw_acc - next_acc) / B` when divisible.

The AIR stores this quotient as `wrap_delta` and introduces auxiliary columns:

- `wrap_delta_inv`
- `wrap_delta_square`
- `wrap_delta_abs`
- `wrap_delta_sign`
- `wrap_delta_abs_bits[0..N)` with `N = 15`

The maximum allowed magnitude is:

- `CARRY_AWARE_WRAP_DELTA_ABS_MAX = 2^14`

which matches the worst-case `i16 * i16` multiplication quotient under division
by `2^16`.

## Host-side discipline

The host-side quotient constructor is:

```text
carry_aware_wrap_delta(raw_acc, wrapped_acc)
```

It rejects any row where:

1. `raw_acc - wrapped_acc` is not divisible by `2^16`;
2. the quotient magnitude exceeds `2^14`;
3. the quotient does not fit in `i16`.

The host-side range witness constructor is:

```text
carry_aware_wrap_delta_range_witness(delta)
```

It rejects any `delta` whose magnitude exceeds `2^14`, and otherwise returns:

- `abs = |delta|`
- `sign = (delta < 0)`
- a little-endian bit decomposition of `abs`

## AIR discipline

For carry-sensitive rows, the AIR enforces all of the following:

1. **Arithmetic wrap relation**

```text
raw_acc - next_acc = wrap_delta * 2^16
```

over the field.

2. **Bitness of decomposition**

Each `wrap_delta_abs_bits[i]` is boolean.

3. **Magnitude reconstruction**

`wrap_delta_abs = sum_i wrap_delta_abs_bits[i] * 2^i`.

4. **High-bit exclusivity**

If the top bit is set, all lower bits must be zero. Combined with
reconstruction, this bounds `wrap_delta_abs <= 2^14`.

5. **Signed reconstruction**

`wrap_delta = wrap_delta_abs * (1 - 2 * wrap_delta_sign)`.

6. **Quadratic pin**

`wrap_delta_square = wrap_delta^2`.

7. **Carry-activity gating**

Non-carry rows must zero the carry witness surface.

8. **Inverse discipline**

`wrap_delta * wrap_delta_inv = next_carry_active`, so a non-zero active delta
must have a valid inverse witness and an inactive carry row cannot float an
arbitrary inverse.

9. **ADD/SUB unit-range discipline**

On ADD/SUB rows,

```text
wrap_delta_square = next_carry_active
```

so the only admissible active deltas are `-1` and `1`, while inactive rows pin
`delta = 0`.

## Statement

### Theorem (carry-aware `wrap_delta` witness discipline)

Assume a carry-sensitive experimental Phase12 row is accepted by the current
AIR and its witness columns satisfy the constraints above.

Then there exists an integer `delta` such that:

1. `delta = wrap_delta` under the signed reconstruction induced by
   `wrap_delta_abs`, `wrap_delta_sign`, and `wrap_delta_abs_bits`;
2. `|delta| <= 2^14`;
3. `raw_acc - next_acc = delta * 2^16` as an integer relation, not only as a
   field relation;
4. if the row is ADD or SUB, then `delta in { -1, 0, 1 }`.

### Proof sketch

- Bitness and reconstruction force `wrap_delta_abs_bits` to encode an actual
  non-negative integer `wrap_delta_abs`.
- High-bit exclusivity and the chosen bit width cap that magnitude at `2^14`.
- Signed reconstruction forces `wrap_delta` to be exactly either
  `wrap_delta_abs` or `-wrap_delta_abs`; it cannot float to another M31 value.
- The square pin prevents inconsistent sign/magnitude pairings from surviving.
- The arithmetic wrap relation then identifies the only admissible integer
  quotient between `raw_acc` and `next_acc`.
- On ADD/SUB rows, `wrap_delta_square = next_carry_active` collapses the active
  magnitude to `1`, while inactive carry rows already force `wrap_delta = 0`.

So the accepted witness surface cannot encode an arbitrary field solution to the
wrap equation. It must encode a bounded signed integer quotient.

## Executable checks tied to this note

Deterministic tests already cover:

- out-of-range `wrap_delta` witness rejection;
- ADD/SUB deltas outside `{ -1, 0, 1 }`;
- drift in `wrap_delta_abs_bits`, `wrap_delta_sign`, and `wrap_delta_square`;
- full supported-range witness canonicality for every `wrap_delta` in
  `[-2^14, 2^14]`;
- full supported-range divisibility checks for representative wrapped
  accumulators, including rejection of `+1` remainder drift on each supported
  quotient;
- honest positive, negative, and non-unit multiply/store carry patterns.

These checks do not replace the AIR proof. They make the host-side
range-witness constructor and quotient/divisibility helpers part of the
executable contract surface through exhaustive deterministic tests that finish
quickly enough to stay in the normal hardening loop.

## Practical conclusion

The April 24 range-hardening work did more than add tests. It closed the
specific gap where `raw_acc - next_acc = wrap_delta * 2^16` could otherwise be
satisfied by a spurious field element that was never bound back to an honest
integer quotient.

That is the property this repo now has stronger grounds to rely on when it says
its experimental carry-aware overflow witness is not merely host-checked but AIR
bound.
