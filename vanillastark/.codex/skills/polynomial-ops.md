---
name: polynomial-ops
description: Implement Polynomial (univariate) and MPolynomial (multivariate) in Rust. Activate when working on polynomial.rs, multivariate.rs, interpolation, evaluation, division, or zerofier operations.
prerequisites: field.rs must be complete and tested. Read stark-anatomy/code/univariate.py and multivariate.py.
---

# Polynomial Operations

<purpose>
Port univariate.py to polynomial.rs and multivariate.py to multivariate.rs. Polynomials are represented as coefficient vectors. Multivariate polynomials use a dictionary (HashMap) from exponent tuples to coefficients.
</purpose>

<context>
Python module map:
- `univariate.py` → `polynomial.rs`: `Polynomial` class + `test_colinearity` function
- `multivariate.py` → `multivariate.rs`: `MPolynomial` class

Key types:
- `Polynomial`: coefficients are `Vec<FieldElement>`, index = degree. `[c0, c1, c2]` = c0 + c1*x + c2*x^2.
- `MPolynomial`: dictionary maps `Vec<usize>` (exponent vectors) → `FieldElement`. E.g., `{[1,0,2]: 5}` = 5 * x0^1 * x2^2.

Critical operations for STARK pipeline:
- `Polynomial::interpolate_domain` — Lagrange interpolation
- `Polynomial::zerofier_domain` — polynomial that vanishes on a set
- `Polynomial::divide` — polynomial long division, returns (quotient, remainder)
- `Polynomial::evaluate` / `evaluate_domain` — single point and batch eval
- `MPolynomial::evaluate` / `evaluate_symbolic` — multivariate evaluation
</context>

<procedure>
### Univariate (polynomial.rs)
1. Define `pub struct Polynomial { pub coefficients: Vec<FieldElement> }`.
2. Implement `degree()` — returns -1 for zero poly (use `Option<usize>` or sentinel).
   Python returns -1 for zero; Rust could use `None` or `isize`.
3. Implement `is_zero()`.
4. Implement arithmetic: `Add`, `Sub`, `Mul` via `std::ops`.
5. Implement `Polynomial::divide(num, den) -> (Polynomial, Polynomial)`.
   This is long division — port Python logic exactly:
   ```python
   while remainder.degree() >= denominator.degree():
       coefficient = remainder.leading_coefficient() / denominator.leading_coefficient()
       shift = remainder.degree() - denominator.degree()
       ...
   ```
6. Implement `interpolate_domain(domain, values) -> Polynomial` — Lagrange.
7. Implement `zerofier_domain(domain) -> Polynomial` — product of (x - d_i).
8. Implement `evaluate(point) -> FieldElement` — Horner's method.
9. Implement `evaluate_domain(domain) -> Vec<FieldElement>`.
10. Implement `scale(factor) -> Polynomial` — multiply variable by factor.
11. Implement `test_colinearity(points) -> bool` — degree-1 test.
12. Port all tests from `test_univariate.py`.

### Multivariate (multivariate.rs)
1. Define `pub struct MPolynomial { pub dictionary: HashMap<Vec<usize>, FieldElement> }`.
2. Implement `Add`, `Sub`, `Mul`, `Neg`.
3. Implement `evaluate(point: &[FieldElement]) -> FieldElement`.
4. Implement `evaluate_symbolic(point: &[Polynomial]) -> Polynomial` — substitutes polynomials for variables.
5. Implement `lift(polynomial, variable_index) -> MPolynomial` — promotes univariate to multivariate.
6. Implement `constant(element) -> MPolynomial` and `variables(n, field)`.
7. Port tests from `test_multivariate.py`.
</procedure>

<patterns>
<do>
  - Store coefficients with trailing zeros stripped (normalize after every operation).
  - Match Python's degree() semantics exactly: zero polynomial has degree -1.
  - Use `Vec<FieldElement>` for coefficients — index i = coefficient of x^i.
  - For MPolynomial, use `BTreeMap<Vec<usize>, FieldElement>` (ordered) or `HashMap` — Python uses dict.
  - Test division with the exact polynomials from test_univariate.py: a=[1,0,5,2], b=[2,2,1], c=[0,5,2,5,5,1].
</do>
<dont>
  - Don't forget to handle the zero polynomial edge cases in divide, degree, and arithmetic.
  - Don't assume polynomials are always non-zero — zero poly is common in remainder checks.
  - Don't skip the `evaluate_symbolic` method — it's critical for the STARK transition constraints.
  - Don't confuse coefficient index with degree — they're the same, but only after normalization.
</dont>
</patterns>

<troubleshooting>
| Symptom | Cause | Fix |
|---------|-------|-----|
| Division hangs | `degree()` returns wrong value for zero poly | Ensure zero poly has degree -1 / None |
| Interpolation gives wrong poly | Domain/values length mismatch or off-by-one | Match Python's Lagrange exactly |
| Zerofier doesn't vanish on domain | Accumulation error | Build incrementally: start with (x - d[0]), then multiply by (x - d[1]), etc. |
| MPolynomial multiply wrong | Exponent vector addition error | When multiplying terms, add exponent vectors element-wise, pad shorter vector with zeros |

</troubleshooting>

<references>
- `stark-anatomy/code/univariate.py`: Polynomial class, 161 lines
- `stark-anatomy/code/multivariate.py`: MPolynomial class, 123 lines
- `stark-anatomy/code/test_univariate.py`: distributivity, division, interpolation, zerofier tests
- `stark-anatomy/code/test_multivariate.py`: basic multivariate tests
</references>
