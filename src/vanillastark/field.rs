use ark_ff::{AdditiveGroup, BigInt, Field, Fp128, MontBackend, MontConfig, PrimeField, Zero};
/// Finite field arithmetic over the prime field F_p where p = 1 + 407 * 2^119.
/// Uses ark-ff Montgomery multiplication for fast field operations.
/// API-compatible wrapper preserving the interface from the manual implementation.
use std::fmt;
use std::ops::{Add, Div, Mul, Neg, Sub};

/// The field prime: p = 1 + 407 * 2^119
pub const P: u128 = 1 + 407 * (1u128 << 119);

/// The known root of order 2^119 used by the stark-anatomy reference.
const ROOT_OF_UNITY: u128 = 85408008396924667383611388730472331217;

/// ark-ff Montgomery configuration for our prime field.
#[derive(MontConfig)]
#[modulus = "270497897142230380135924736767050121217"]
#[generator = "3"]
pub struct FqConfig;

/// The inner ark-ff field type (128-bit prime, 2 limbs).
pub type Fq = Fp128<MontBackend<FqConfig, 2>>;

/// A field element in F_p. Wraps ark-ff's Montgomery-form representation
/// for fast arithmetic while preserving the original API.
#[derive(Clone, Copy, Debug, Eq)]
pub struct FieldElement(pub Fq);

// ── helpers ──

fn u128_to_fq(v: u128) -> Fq {
    let v = v % P;
    Fq::from_bigint(BigInt::new([v as u64, (v >> 64) as u64])).unwrap()
}

fn fq_to_u128(f: Fq) -> u128 {
    let bigint = f.into_bigint();
    (bigint.0[0] as u128) | ((bigint.0[1] as u128) << 64)
}

impl FieldElement {
    pub fn new(value: u128) -> Self {
        FieldElement(u128_to_fq(value))
    }

    pub fn zero() -> Self {
        FieldElement(Fq::ZERO)
    }

    pub fn one() -> Self {
        FieldElement(Fq::ONE)
    }

    pub fn is_zero(&self) -> bool {
        self.0.is_zero()
    }

    /// Get the canonical u128 value in [0, p).
    pub fn value(&self) -> u128 {
        fq_to_u128(self.0)
    }

    /// Multiplicative inverse.
    pub fn inverse(&self) -> Self {
        assert!(!self.is_zero(), "cannot invert zero");
        FieldElement(Field::inverse(&self.0).unwrap())
    }

    /// Modular exponentiation.
    pub fn pow(&self, exp: u128) -> Self {
        FieldElement(self.0.pow([exp as u64, (exp >> 64) as u64]))
    }

    /// The element used as coset offset and root-of-unity base in the
    /// stark-anatomy reference.
    /// This is a primitive 2^119-th root of unity (NOT a generator of the full
    /// multiplicative group).
    pub fn generator() -> Self {
        Self::new(ROOT_OF_UNITY)
    }

    /// Primitive n-th root of unity where n must be a power of two and n <= 2^119.
    pub fn primitive_nth_root(n: u128) -> Self {
        assert!(
            n <= (1u128 << 119) && (n & (n - 1)) == 0,
            "Field does not have nth root of unity where n > 2^119 or not power of two."
        );
        let mut root = Self::new(ROOT_OF_UNITY);
        let mut order = 1u128 << 119;
        while order != n {
            root = root.pow(2);
            order /= 2;
        }
        root
    }

    /// Sample a field element from a byte array (big-endian accumulation, reduce mod p).
    pub fn sample(bytes: &[u8]) -> Self {
        let two56 = u128_to_fq(256);
        let mut acc = Fq::ZERO;
        for &b in bytes {
            acc = acc * two56 + Fq::from(b as u64);
        }
        FieldElement(acc)
    }

    /// Convert to bytes via decimal string representation.
    /// Matches Python's `bytes(str(self).encode())`.
    pub fn to_bytes_str(&self) -> Vec<u8> {
        self.value().to_string().into_bytes()
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
        FieldElement(self.0 + rhs.0)
    }
}

impl Sub for FieldElement {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        FieldElement(self.0 - rhs.0)
    }
}

impl Mul for FieldElement {
    type Output = Self;
    fn mul(self, rhs: Self) -> Self {
        FieldElement(self.0 * rhs.0)
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
        FieldElement(-self.0)
    }
}

impl fmt::Display for FieldElement {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.value())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_field_constants() {
        assert_eq!(P, 270497897142230380135924736767050121217);
    }

    #[test]
    fn test_basic_arithmetic() {
        let a = FieldElement::new(42);
        let b = FieldElement::new(17);
        assert_eq!((a + b).value(), 59);
        assert_eq!((a - b).value(), 25);
        assert_eq!((a * b).value(), 714);
    }

    #[test]
    fn test_inverse() {
        let a = FieldElement::new(42);
        assert_eq!((a * a.inverse()).value(), 1);

        let g = FieldElement::generator();
        assert_eq!((g * g.inverse()).value(), 1);
    }

    #[test]
    fn test_generator_order() {
        let g = FieldElement::generator();
        // g is a primitive 2^119-th root of unity, so g^(2^119) = 1
        assert_eq!(g.pow(1u128 << 119), FieldElement::one());
        // But g^(p-1) should also equal 1 (any element satisfies Fermat)
        assert_eq!(g.pow(P - 1), FieldElement::one());
    }

    #[test]
    fn test_primitive_nth_root() {
        for &log_n in &[1, 2, 4, 8, 10] {
            let n = 1u128 << log_n;
            let root = FieldElement::primitive_nth_root(n);
            assert_eq!(root.pow(n), FieldElement::one(), "root^n != 1 for n={}", n);
            assert_ne!(
                root.pow(n / 2),
                FieldElement::one(),
                "root^(n/2) == 1 for n={}",
                n
            );
        }
    }

    #[test]
    fn test_sample() {
        let input = b"0xdeadbeef";
        let fe = FieldElement::sample(input);
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

    #[test]
    fn test_value_roundtrip() {
        let vals = [0u128, 1, 42, P - 1, 85408008396924667383611388730472331217];
        for &v in &vals {
            assert_eq!(
                FieldElement::new(v).value(),
                v,
                "roundtrip failed for {}",
                v
            );
        }
    }
}
