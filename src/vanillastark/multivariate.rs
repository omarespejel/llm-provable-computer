/// Multivariate polynomials over F_p.
/// Ported from the stark-anatomy Python reference implementation.
use std::collections::HashMap;
use std::ops::{Add, Mul, Neg, Sub};

use super::field::FieldElement;
use super::polynomial::Polynomial;

/// A multivariate polynomial represented as a dictionary mapping
/// exponent vectors to coefficients.
/// E.g., f(x,y,z) = 17 + 2xy + 42z is {(0,0,0):17, (1,1,0):2, (0,0,1):42}
#[derive(Clone, Debug)]
pub struct MPolynomial {
    pub dictionary: HashMap<Vec<usize>, FieldElement>,
}

impl MPolynomial {
    pub fn zero() -> Self {
        MPolynomial {
            dictionary: HashMap::new(),
        }
    }

    pub fn constant(element: FieldElement) -> Self {
        let mut dict = HashMap::new();
        dict.insert(vec![0], element);
        MPolynomial { dictionary: dict }
    }

    pub fn is_zero(&self) -> bool {
        if self.dictionary.is_empty() {
            return true;
        }
        self.dictionary.values().all(|v| v.is_zero())
    }

    /// Returns multivariate polynomials for each variable: [x0, x1, ..., x_{n-1}]
    pub fn variables(num_variables: usize) -> Vec<MPolynomial> {
        let mut vars = Vec::new();
        for i in 0..num_variables {
            let mut exponent = vec![0usize; num_variables];
            exponent[i] = 1;
            let mut dict = HashMap::new();
            dict.insert(exponent, FieldElement::one());
            vars.push(MPolynomial { dictionary: dict });
        }
        vars
    }

    /// Evaluate at a concrete point (vector of FieldElements).
    pub fn evaluate(&self, point: &[FieldElement]) -> FieldElement {
        let mut acc = FieldElement::zero();
        for (k, &v) in &self.dictionary {
            let mut prod = v;
            for i in 0..k.len() {
                prod = prod * point[i].pow(k[i] as u128);
            }
            acc = acc + prod;
        }
        acc
    }

    /// Evaluate symbolically: substitute Polynomials for variables, return a Polynomial.
    pub fn evaluate_symbolic(&self, point: &[Polynomial]) -> Polynomial {
        let mut acc = Polynomial::zero();
        for (k, &v) in &self.dictionary {
            let mut prod = Polynomial::new(vec![v]);
            for i in 0..k.len() {
                prod = prod * point[i].pow(k[i]);
            }
            acc = acc + prod;
        }
        acc
    }

    /// Polynomial exponentiation via square-and-multiply.
    pub fn pow(&self, exponent: usize) -> MPolynomial {
        if self.is_zero() {
            return MPolynomial::zero();
        }
        if exponent == 0 {
            return MPolynomial::constant(FieldElement::one());
        }
        let mut acc = MPolynomial::constant(FieldElement::one());
        let bits_str = format!("{:b}", exponent);
        for b in bits_str.chars() {
            acc = acc.clone() * acc;
            if b == '1' {
                acc = acc * self.clone();
            }
        }
        acc
    }

    /// Lift a univariate Polynomial into a MPolynomial in the given variable index.
    pub fn lift(polynomial: &Polynomial, variable_index: usize) -> MPolynomial {
        if polynomial.is_zero() {
            return MPolynomial::zero();
        }
        let variables = MPolynomial::variables(variable_index + 1);
        let x = &variables[variable_index];
        let mut acc = MPolynomial::zero();
        for (i, &c) in polynomial.coefficients.iter().enumerate() {
            acc = acc + MPolynomial::constant(c) * x.pow(i);
        }
        acc
    }
}

fn num_variables_from_keys<'a, I: Iterator<Item = &'a Vec<usize>>>(keys: I) -> usize {
    keys.map(|k| k.len()).max().unwrap_or(0)
}

fn pad_key(k: &[usize], num_variables: usize) -> Vec<usize> {
    let mut pad = k.to_vec();
    pad.resize(num_variables, 0);
    pad
}

impl Add for MPolynomial {
    type Output = Self;
    fn add(self, other: Self) -> Self {
        let num_variables =
            num_variables_from_keys(self.dictionary.keys().chain(other.dictionary.keys()));
        let mut dictionary = HashMap::new();
        for (k, v) in &self.dictionary {
            let pad = pad_key(k, num_variables);
            dictionary.insert(pad, *v);
        }
        for (k, v) in &other.dictionary {
            let pad = pad_key(k, num_variables);
            let entry = dictionary.entry(pad).or_insert(FieldElement::zero());
            *entry = *entry + *v;
        }
        MPolynomial { dictionary }
    }
}

impl Sub for MPolynomial {
    type Output = Self;
    fn sub(self, other: Self) -> Self {
        self + (-other)
    }
}

impl Neg for MPolynomial {
    type Output = Self;
    fn neg(self) -> Self {
        let mut dictionary = HashMap::new();
        for (k, v) in &self.dictionary {
            dictionary.insert(k.clone(), -*v);
        }
        MPolynomial { dictionary }
    }
}

impl Mul for MPolynomial {
    type Output = Self;
    fn mul(self, other: Self) -> Self {
        let num_variables =
            num_variables_from_keys(self.dictionary.keys().chain(other.dictionary.keys()));
        let mut dictionary: HashMap<Vec<usize>, FieldElement> = HashMap::new();
        for (k0, &v0) in &self.dictionary {
            for (k1, &v1) in &other.dictionary {
                let mut exponent = vec![0usize; num_variables];
                for i in 0..k0.len() {
                    exponent[i] += k0[i];
                }
                for i in 0..k1.len() {
                    exponent[i] += k1[i];
                }
                let entry = dictionary.entry(exponent).or_insert(FieldElement::zero());
                *entry = *entry + v0 * v1;
            }
        }
        MPolynomial { dictionary }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mpoly_basic() {
        let a = MPolynomial::constant(FieldElement::new(5));
        let b = MPolynomial::constant(FieldElement::new(3));
        let c = a + b;
        let point = vec![FieldElement::one()];
        assert_eq!(c.evaluate(&point), FieldElement::new(8));
    }

    #[test]
    fn test_mpoly_variables() {
        let vars = MPolynomial::variables(2);
        // x0 at point (3, 7) should give 3
        let point = vec![FieldElement::new(3), FieldElement::new(7)];
        assert_eq!(vars[0].evaluate(&point), FieldElement::new(3));
        assert_eq!(vars[1].evaluate(&point), FieldElement::new(7));
    }

    #[test]
    fn test_mpoly_multiply() {
        let vars = MPolynomial::variables(2);
        // x0 * x1 at (3, 7) = 21
        let prod = vars[0].clone() * vars[1].clone();
        let point = vec![FieldElement::new(3), FieldElement::new(7)];
        assert_eq!(prod.evaluate(&point), FieldElement::new(21));
    }

    #[test]
    fn test_mpoly_lift() {
        // Lift p(x) = 1 + 2x to MPolynomial in variable 0
        let p = Polynomial::new(vec![FieldElement::one(), FieldElement::new(2)]);
        let mp = MPolynomial::lift(&p, 0);
        let point = vec![FieldElement::new(5)];
        assert_eq!(mp.evaluate(&point), FieldElement::new(11)); // 1 + 2*5
    }
}
