use super::field::FieldElement;
/// Univariate polynomials over F_p.
/// Ported from the stark-anatomy Python reference implementation.
use std::ops::{Add, Div, Mul, Neg, Rem, Sub};

#[derive(Clone, Debug)]
pub struct Polynomial {
    pub coefficients: Vec<FieldElement>,
}

impl Polynomial {
    pub fn new(coefficients: Vec<FieldElement>) -> Self {
        Polynomial { coefficients }
    }

    pub fn zero() -> Self {
        Polynomial {
            coefficients: vec![],
        }
    }

    /// Degree of the polynomial. Returns -1 for the zero polynomial.
    pub fn degree(&self) -> isize {
        if self.coefficients.is_empty() {
            return -1;
        }
        let mut max_index: isize = -1;
        for (i, c) in self.coefficients.iter().enumerate() {
            if !c.is_zero() {
                max_index = i as isize;
            }
        }
        max_index
    }

    pub fn is_zero(&self) -> bool {
        if self.coefficients.is_empty() {
            return true;
        }
        self.coefficients.iter().all(|c| c.is_zero())
    }

    pub fn leading_coefficient(&self) -> FieldElement {
        let d = self.degree();
        assert!(d >= 0, "zero polynomial has no leading coefficient");
        self.coefficients[d as usize]
    }

    /// Polynomial long division. Returns (quotient, remainder).
    pub fn divide(numerator: &Polynomial, denominator: &Polynomial) -> (Polynomial, Polynomial) {
        assert!(
            denominator.degree() >= 0,
            "cannot divide by zero polynomial"
        );

        if numerator.degree() < denominator.degree() {
            return (Polynomial::zero(), numerator.clone());
        }

        let num_deg = numerator.degree();
        let den_deg = denominator.degree();
        let mut remainder = numerator.clone();
        let quo_len = (num_deg - den_deg + 1) as usize;
        let mut quotient_coefficients = vec![FieldElement::zero(); quo_len];

        for _ in 0..quo_len {
            if remainder.degree() < denominator.degree() {
                break;
            }
            let coefficient = remainder.leading_coefficient() / denominator.leading_coefficient();
            let shift = (remainder.degree() - denominator.degree()) as usize;
            let mut subtractee_coeffs = vec![FieldElement::zero(); shift];
            subtractee_coeffs.push(coefficient);
            let subtractee = Polynomial::new(subtractee_coeffs) * denominator.clone();
            quotient_coefficients[shift] = coefficient;
            remainder = remainder - subtractee;
        }

        (Polynomial::new(quotient_coefficients), remainder)
    }

    /// Lagrange interpolation over a domain.
    pub fn interpolate_domain(domain: &[FieldElement], values: &[FieldElement]) -> Polynomial {
        assert_eq!(
            domain.len(),
            values.len(),
            "domain and values must have same length"
        );
        assert!(!domain.is_empty(), "cannot interpolate zero points");

        let x = Polynomial::new(vec![FieldElement::zero(), FieldElement::one()]);
        let mut acc = Polynomial::zero();

        for i in 0..domain.len() {
            let mut prod = Polynomial::new(vec![values[i]]);
            for j in 0..domain.len() {
                if j == i {
                    continue;
                }
                prod = prod
                    * (x.clone() - Polynomial::new(vec![domain[j]]))
                    * Polynomial::new(vec![(domain[i] - domain[j]).inverse()]);
            }
            acc = acc + prod;
        }
        acc
    }

    /// Polynomial that vanishes on all points in the domain.
    pub fn zerofier_domain(domain: &[FieldElement]) -> Polynomial {
        let x = Polynomial::new(vec![FieldElement::zero(), FieldElement::one()]);
        let mut acc = Polynomial::new(vec![FieldElement::one()]);
        for &d in domain {
            acc = acc * (x.clone() - Polynomial::new(vec![d]));
        }
        acc
    }

    /// Evaluate the polynomial at a single point.
    pub fn evaluate(&self, point: FieldElement) -> FieldElement {
        let mut xi = FieldElement::one();
        let mut value = FieldElement::zero();
        for &c in &self.coefficients {
            value = value + c * xi;
            xi = xi * point;
        }
        value
    }

    /// Evaluate the polynomial at every point in the domain.
    pub fn evaluate_domain(&self, domain: &[FieldElement]) -> Vec<FieldElement> {
        domain.iter().map(|&d| self.evaluate(d)).collect()
    }

    /// Polynomial exponentiation via square-and-multiply.
    pub fn pow(&self, exponent: usize) -> Polynomial {
        if self.is_zero() {
            return Polynomial::zero();
        }
        if exponent == 0 {
            return Polynomial::new(vec![FieldElement::one()]);
        }
        let bits = usize::BITS - exponent.leading_zeros();
        let mut acc = Polynomial::new(vec![FieldElement::one()]);
        for i in (0..bits).rev() {
            acc = acc.clone() * acc;
            if (exponent >> i) & 1 == 1 {
                acc = acc * self.clone();
            }
        }
        acc
    }

    /// Scale: p(x) -> p(factor * x).
    /// Coefficients become [c_0, c_1*factor, c_2*factor^2, ...].
    pub fn scale(&self, factor: FieldElement) -> Polynomial {
        let coeffs: Vec<FieldElement> = self
            .coefficients
            .iter()
            .enumerate()
            .map(|(i, &c)| factor.pow(i as u128) * c)
            .collect();
        Polynomial::new(coeffs)
    }
}

/// Test whether 3 or more points are colinear (interpolating polynomial has degree exactly 1).
pub fn test_colinearity(points: &[(FieldElement, FieldElement)]) -> bool {
    let domain: Vec<FieldElement> = points.iter().map(|p| p.0).collect();
    let values: Vec<FieldElement> = points.iter().map(|p| p.1).collect();
    let polynomial = Polynomial::interpolate_domain(&domain, &values);
    polynomial.degree() == 1
}

// ── Operator trait implementations ──

impl PartialEq for Polynomial {
    fn eq(&self, other: &Self) -> bool {
        if self.degree() != other.degree() {
            return false;
        }
        if self.degree() == -1 {
            return true;
        }
        let max_len = self.coefficients.len().max(other.coefficients.len());
        for i in 0..max_len {
            let a = if i < self.coefficients.len() {
                self.coefficients[i]
            } else {
                FieldElement::zero()
            };
            let b = if i < other.coefficients.len() {
                other.coefficients[i]
            } else {
                FieldElement::zero()
            };
            if a != b {
                return false;
            }
        }
        true
    }
}

impl Neg for Polynomial {
    type Output = Self;
    fn neg(self) -> Self {
        Polynomial::new(self.coefficients.iter().map(|&c| -c).collect())
    }
}

impl Add for Polynomial {
    type Output = Self;
    fn add(self, other: Self) -> Self {
        if self.degree() == -1 {
            return other;
        }
        if other.degree() == -1 {
            return self;
        }
        let max_len = self.coefficients.len().max(other.coefficients.len());
        let mut coeffs = vec![FieldElement::zero(); max_len];
        for (i, &c) in self.coefficients.iter().enumerate() {
            coeffs[i] = coeffs[i] + c;
        }
        for (i, &c) in other.coefficients.iter().enumerate() {
            coeffs[i] = coeffs[i] + c;
        }
        Polynomial::new(coeffs)
    }
}

impl Sub for Polynomial {
    type Output = Self;
    fn sub(self, other: Self) -> Self {
        self + (-other)
    }
}

impl Mul for Polynomial {
    type Output = Self;
    fn mul(self, other: Self) -> Self {
        if self.coefficients.is_empty() || other.coefficients.is_empty() {
            return Polynomial::zero();
        }
        let buf_len = self.coefficients.len() + other.coefficients.len() - 1;
        let mut buf = vec![FieldElement::zero(); buf_len];
        for (i, &ci) in self.coefficients.iter().enumerate() {
            if ci.is_zero() {
                continue;
            }
            for (j, &cj) in other.coefficients.iter().enumerate() {
                buf[i + j] = buf[i + j] + ci * cj;
            }
        }
        Polynomial::new(buf)
    }
}

impl Div for Polynomial {
    type Output = Self;
    fn div(self, other: Self) -> Self {
        let (quo, rem) = Polynomial::divide(&self, &other);
        assert!(
            rem.is_zero(),
            "cannot perform polynomial division because remainder is not zero"
        );
        quo
    }
}

impl Rem for Polynomial {
    type Output = Self;
    fn rem(self, other: Self) -> Self {
        let (_, rem) = Polynomial::divide(&self, &other);
        rem
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fe(v: u128) -> FieldElement {
        FieldElement::new(v)
    }

    #[test]
    fn test_distributivity() {
        let zero = FieldElement::zero();
        let one = FieldElement::one();
        let two = fe(2);
        let five = fe(5);

        let a = Polynomial::new(vec![one, zero, five, two]);
        let b = Polynomial::new(vec![two, two, one]);
        let c = Polynomial::new(vec![zero, five, two, five, five, one]);

        let lhs = a.clone() * (b.clone() + c.clone());
        let rhs = a.clone() * b + a * c;
        assert_eq!(lhs, rhs, "distributivity fails for polynomials");
    }

    #[test]
    fn test_division() {
        let zero = FieldElement::zero();
        let one = FieldElement::one();
        let two = fe(2);
        let five = fe(5);

        let a = Polynomial::new(vec![one, zero, five, two]);
        let b = Polynomial::new(vec![two, two, one]);
        let c = Polynomial::new(vec![zero, five, two, five, five, one]);

        // a should divide a*b, quotient should be b
        let (quo, rem) = Polynomial::divide(&(a.clone() * b.clone()), &a);
        assert!(rem.is_zero(), "division test 1: remainder not zero");
        assert_eq!(quo, b, "division test 2: quotient != b");

        // b should divide a*b, quotient should be a
        let ab = a.clone() * b.clone();
        let (quo, rem) = Polynomial::divide(&ab, &b);
        assert!(rem.is_zero(), "division test 3");
        assert_eq!(quo, a, "division test 4");

        // c should not divide a*b
        let ab = a.clone() * b.clone();
        let (quo, rem) = Polynomial::divide(&ab, &c);
        assert!(!rem.is_zero(), "division test 5");

        // but quo * c + rem == a*b
        assert_eq!(quo * c + rem, a * b, "division test 6");
    }

    #[test]
    fn test_interpolate() {
        let zero = FieldElement::zero();
        let one = FieldElement::one();
        let two = fe(2);
        let five = fe(5);

        let values = [five, two, two, one, five];
        let domain: Vec<FieldElement> = (1..=5).map(fe).collect();

        let poly = Polynomial::interpolate_domain(&domain, &values);

        for (i, (&point, &expected)) in domain.iter().zip(values.iter()).enumerate() {
            assert_eq!(
                poly.evaluate(point),
                expected,
                "interpolate test 1 at i={}",
                i
            );
        }

        assert_ne!(poly.evaluate(fe(363)), zero, "interpolate test 2");
        assert_eq!(
            poly.degree(),
            domain.len() as isize - 1,
            "interpolate test 3"
        );
    }

    #[test]
    fn test_zerofier() {
        let domain = vec![fe(1), fe(2), fe(3), fe(4), fe(5)];
        let zerofier = Polynomial::zerofier_domain(&domain);

        assert_eq!(zerofier.degree(), domain.len() as isize);
        for &d in &domain {
            assert_eq!(zerofier.evaluate(d), FieldElement::zero());
        }
        assert_ne!(zerofier.evaluate(fe(363)), FieldElement::zero());
    }
}
