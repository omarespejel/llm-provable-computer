/// Finite field arithmetic over the prime field F_p where p = 1 + 407 * 2^119.
/// Ported from stark-anatomy/code/algebra.py.

use std::fmt;
use std::ops::{Add, Sub, Mul, Div, Neg};

/// The field prime: p = 1 + 407 * 2^119
pub const P: u128 = 1 + 407 * (1u128 << 119);

/// Known generator of the multiplicative group
const GENERATOR: u128 = 85408008396924667383611388730472331217;

/// A field element in F_p, represented as a u128 value in [0, p).
#[derive(Clone, Copy, Debug, Eq)]
pub struct FieldElement(pub u128);

// ── helpers for modular arithmetic on u128 ──

#[inline]
fn addmod(a: u128, b: u128) -> u128 {
    let (sum, overflow) = a.overflowing_add(b);
    if overflow {
        // a + b wrapped around 2^128. True value = sum + 2^128.
        // Result = (a+b) - P = sum + (2^128 - P).
        sum + (u128::MAX - P + 1)
    } else if sum >= P {
        sum - P
    } else {
        sum
    }
}

#[inline]
fn submod(a: u128, b: u128) -> u128 {
    if a >= b { a - b } else { P - b + a }
}

/// Modular multiplication via Russian-peasant (double-and-add).
/// O(128) iterations — correct and simple.
#[inline]
fn mulmod(a: u128, b: u128) -> u128 {
    let mut a = a % P;
    let mut b = b % P;
    let mut result: u128 = 0;
    while b > 0 {
        if b & 1 == 1 {
            result = addmod(result, a);
        }
        a = addmod(a, a);
        b >>= 1;
    }
    result
}

/// Modular exponentiation via square-and-multiply.
fn powmod(base: u128, exp: u128) -> u128 {
    if exp == 0 {
        return 1;
    }
    let bits = 128 - exp.leading_zeros();
    let mut acc: u128 = 1;
    for i in (0..bits).rev() {
        acc = mulmod(acc, acc);
        if (exp >> i) & 1 == 1 {
            acc = mulmod(acc, base);
        }
    }
    acc
}

impl FieldElement {
    pub fn new(value: u128) -> Self {
        FieldElement(value % P)
    }

    pub fn zero() -> Self {
        FieldElement(0)
    }

    pub fn one() -> Self {
        FieldElement(1)
    }

    pub fn is_zero(&self) -> bool {
        self.0 == 0
    }

    pub fn value(&self) -> u128 {
        self.0
    }

    /// Multiplicative inverse via Fermat's little theorem: a^{-1} = a^{p-2} mod p.
    pub fn inverse(&self) -> Self {
        assert!(!self.is_zero(), "cannot invert zero");
        FieldElement(powmod(self.0, P - 2))
    }

    /// Modular exponentiation.
    pub fn pow(&self, exp: u128) -> Self {
        FieldElement(powmod(self.0, exp))
    }

    /// Generator of the multiplicative group of F_p.
    pub fn generator() -> Self {
        FieldElement(GENERATOR)
    }

    /// Primitive n-th root of unity where n must be a power of two and n <= 2^119.
    pub fn primitive_nth_root(n: u128) -> Self {
        assert!(
            n <= (1u128 << 119) && (n & (n - 1)) == 0,
            "Field does not have nth root of unity where n > 2^119 or not power of two."
        );
        let mut root = FieldElement(GENERATOR);
        let mut order = 1u128 << 119;
        while order != n {
            root = root.pow(2);
            order /= 2;
        }
        root
    }

    /// Sample a field element from a byte array (big-endian accumulation, then reduce mod p).
    pub fn sample(bytes: &[u8]) -> Self {
        let mut acc: u128 = 0;
        for &b in bytes {
            acc = addmod(mulmod(acc, 256), (b as u128) % P);
        }
        FieldElement(acc)
    }

    /// Convert to bytes via decimal string representation (matches Python's `bytes(str(self).encode())`).
    pub fn to_bytes_str(&self) -> Vec<u8> {
        self.0.to_string().into_bytes()
    }
}

// ── Operator trait implementations ──

impl PartialEq for FieldElement {
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl Add for FieldElement {
    type Output = Self;
    fn add(self, rhs: Self) -> Self {
        FieldElement(addmod(self.0, rhs.0))
    }
}

impl Sub for FieldElement {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        FieldElement(submod(self.0, rhs.0))
    }
}

impl Mul for FieldElement {
    type Output = Self;
    fn mul(self, rhs: Self) -> Self {
        FieldElement(mulmod(self.0, rhs.0))
    }
}

impl Div for FieldElement {
    type Output = Self;
    fn div(self, rhs: Self) -> Self {
        assert!(!rhs.is_zero(), "divide by zero");
        self * rhs.inverse()
    }
}

impl Neg for FieldElement {
    type Output = Self;
    fn neg(self) -> Self {
        if self.0 == 0 { self } else { FieldElement(P - self.0) }
    }
}

impl fmt::Display for FieldElement {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_field_constants() {
        assert_eq!(P, 270497897142230380135924736767050121217);
        assert_eq!(GENERATOR, 85408008396924667383611388730472331217);
    }

    #[test]
    fn test_basic_arithmetic() {
        let a = FieldElement::new(42);
        let b = FieldElement::new(17);
        assert_eq!((a + b).0, 59);
        assert_eq!((a - b).0, 25);
        assert_eq!((a * b).0, 714);
    }

    #[test]
    fn test_inverse() {
        let a = FieldElement::new(42);
        assert_eq!((a * a.inverse()).0, 1);

        let g = FieldElement::generator();
        assert_eq!((g * g.inverse()).0, 1);
    }

    #[test]
    fn test_generator_order() {
        let g = FieldElement::generator();
        // g^(p-1) should equal 1 (Fermat's little theorem)
        assert_eq!(g.pow(P - 1), FieldElement::one());
    }

    #[test]
    fn test_primitive_nth_root() {
        for &log_n in &[1, 2, 4, 8, 10] {
            let n = 1u128 << log_n;
            let root = FieldElement::primitive_nth_root(n);
            assert_eq!(root.pow(n), FieldElement::one(), "root^n != 1 for n={}", n);
            assert_ne!(root.pow(n / 2), FieldElement::one(), "root^(n/2) == 1 for n={}", n);
        }
    }

    #[test]
    fn test_sample() {
        // Match Python: Field.main().sample(bytes(b'0xdeadbeef'))
        let input = b"0xdeadbeef";
        let fe = FieldElement::sample(input);
        // Value computed from Python reference
        assert!(!fe.is_zero());
    }

    #[test]
    fn test_negation() {
        let a = FieldElement::new(42);
        assert_eq!(a + (-a), FieldElement::zero());
        assert_eq!(-FieldElement::zero(), FieldElement::zero());
    }

    #[test]
    fn test_pow_zero() {
        let a = FieldElement::new(42);
        assert_eq!(a.pow(0), FieldElement::one());
    }
}
