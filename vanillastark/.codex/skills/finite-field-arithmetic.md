---
name: finite-field-arithmetic
description: Implement Field and FieldElement in Rust with u128 modular arithmetic, xgcd, and operator traits. Activate when working on field.rs, modular math, or any arithmetic bugs.
prerequisites: Read stark-anatomy/code/algebra.py first
---

# Finite Field Arithmetic

<purpose>
Port algebra.py to field.rs. This is the foundational module — every other module depends on correct field arithmetic. The prime is 128-bit, so u128 native arithmetic is used with careful overflow handling.
</purpose>

<context>
- Field prime: p = 1 + 407 * 2^119 = 270497897142230380135924736767050121217
- Generator: 85408008396924667383611388730472331217
- All arithmetic is mod p
- u128::MAX = 340282366920938463463374607431768211455 > p, so single values fit
- But a + b or a * b can overflow u128

Python classes to port:
- `FieldElement`: wraps value + field reference, operator overloads
- `Field`: the prime field, provides zero/one/generator/sample/primitive_nth_root
- `xgcd`: extended GCD for computing inverses
</context>

<procedure>
1. Create `src/field.rs`.
2. Implement `xgcd(x: i128, y: i128) -> (i128, i128, i128)` matching Python exactly.
3. Define `pub const P: u128 = 1 + 407 * (1u128 << 119)`.
4. Define `pub struct FieldElement(pub u128)` — single-field struct.
5. Implement modular addition with overflow check:
   ```rust
   fn add(a: u128, b: u128) -> u128 {
       let sum = a.wrapping_add(b);
       if sum >= P || sum < a { sum.wrapping_sub(P) } else { sum }
   }
   ```
6. Implement modular subtraction: `if a >= b { a - b } else { P - b + a }`.
7. Implement modular multiplication using 256-bit intermediate:
   - Split a and b into hi/lo 64-bit halves
   - Compute the four partial products
   - Reduce mod p
   - OR use repeated doubling for simplicity first
8. Implement `inverse` via xgcd.
9. Implement `pow` via square-and-multiply (port Python's `__xor__`).
10. Implement `std::ops` traits: `Add`, `Sub`, `Mul`, `Div`, `Neg`.
11. Implement `Field` struct or module-level functions for `zero()`, `one()`, `generator()`, `primitive_nth_root(n)`, `sample(bytes)`.
12. Port tests from `test_univariate.py` (which uses field ops) and verify.

Decision point: If u128 multiplication is too complex initially, implement with a simple `mulmod` using repeated addition/doubling, then optimize later.
</procedure>

<patterns>
<do>
  - Use `#[derive(Clone, Copy, Debug, PartialEq, Eq)]` — FieldElement should be Copy.
  - Keep FieldElement as a newtype `struct FieldElement(pub u128)` — no field reference needed since there's only one prime.
  - Use `const P: u128` and `const GENERATOR: u128` as module constants.
  - Test with known values from Python: `Field.main().generator()` should give `85408008396924667383611388730472331217`.
  - Test `primitive_nth_root(n)^n == one` for various n.
</do>
<dont>
  - Don't store a reference to Field in FieldElement — unlike Python, use a single global prime constant.
  - Don't use the `^` operator (BitXor) for exponentiation — use a `.pow()` method.
  - Don't forget that Python's xgcd uses arbitrary-precision integers — Rust needs i128 (signed) for the Bezout coefficients.
  - Don't skip the overflow handling for add/mul — it will silently produce wrong results.
</dont>
</patterns>

<examples>
Example: Modular multiplication via u128 widening

```rust
/// Compute (a * b) mod P without overflow.
/// Uses the identity: a*b = (a_hi * 2^64 + a_lo) * (b_hi * 2^64 + b_lo)
fn mulmod(a: u128, b: u128) -> u128 {
    // Simple approach: use Russian peasant multiplication
    let mut result: u128 = 0;
    let mut a = a % P;
    let mut b = b % P;
    while b > 0 {
        if b & 1 == 1 {
            result = addmod(result, a);
        }
        a = addmod(a, a);
        b >>= 1;
    }
    result
}
```

Note: Russian peasant is O(128) iterations — fine for correctness, optimize later if needed.
</examples>

<troubleshooting>
| Symptom | Cause | Fix |
|---------|-------|-----|
| inverse(x) * x != 1 | xgcd sign handling wrong | Use i128 for xgcd, convert back to u128 with `((a % p as i128) + p as i128) % p as i128` |
| pow(g, p-1) != 1 (Fermat) | mulmod overflow | Verify mulmod with small known values first |
| primitive_nth_root(n)^n != 1 | Wrong squaring in root computation | Port Python loop exactly: `root = root^2; order = order/2` |
| Different results than Python | Signed vs unsigned mismatch in xgcd | Python integers are arbitrary precision and signed; ensure i128 range suffices |
</troubleshooting>

<references>
- `stark-anatomy/code/algebra.py`: Field, FieldElement, xgcd — THE source of truth
- `stark-anatomy/code/test_univariate.py`: Uses `Field.main()`, `FieldElement(value, field)` — test vectors
- `stark-anatomy/docs/basic-tools.md`: Explains the mathematical background
</references>
