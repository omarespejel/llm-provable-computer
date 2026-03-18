/// Number Theoretic Transform and fast polynomial operations.
/// Ported from the stark-anatomy Python reference implementation.
use super::field::FieldElement;
use super::polynomial::Polynomial;

/// Forward NTT (Number Theoretic Transform).
pub fn ntt(primitive_root: FieldElement, values: &[FieldElement]) -> Vec<FieldElement> {
    assert!(
        values.len().is_power_of_two(),
        "cannot compute ntt of non-power-of-two sequence"
    );

    if values.len() <= 1 {
        return values.to_vec();
    }

    let n = values.len();
    assert_eq!(
        primitive_root.pow(n as u128),
        FieldElement::one(),
        "primitive root must be nth root of unity"
    );
    assert_ne!(
        primitive_root.pow((n / 2) as u128),
        FieldElement::one(),
        "primitive root is not primitive"
    );

    let half = n / 2;
    let root_sq = primitive_root.pow(2);

    // Split into even and odd indices
    let evens: Vec<FieldElement> = values.iter().step_by(2).copied().collect();
    let odds: Vec<FieldElement> = values.iter().skip(1).step_by(2).copied().collect();

    let evens_ntt = ntt(root_sq, &evens);
    let odds_ntt = ntt(root_sq, &odds);

    let mut result = vec![FieldElement::zero(); n];
    for i in 0..n {
        result[i] = evens_ntt[i % half] + primitive_root.pow(i as u128) * odds_ntt[i % half];
    }
    result
}

/// Inverse NTT.
pub fn intt(primitive_root: FieldElement, values: &[FieldElement]) -> Vec<FieldElement> {
    assert!(
        values.len().is_power_of_two(),
        "cannot compute intt of non-power-of-two sequence"
    );

    if values.len() == 1 {
        return values.to_vec();
    }

    let n = values.len();
    let ninv = FieldElement::new(n as u128).inverse();
    let transformed = ntt(primitive_root.inverse(), values);
    transformed.iter().map(|&tv| ninv * tv).collect()
}

/// Fast polynomial multiplication via NTT.
pub fn fast_multiply(
    lhs: &Polynomial,
    rhs: &Polynomial,
    primitive_root: FieldElement,
    root_order: usize,
) -> Polynomial {
    assert_eq!(primitive_root.pow(root_order as u128), FieldElement::one());
    assert_ne!(
        primitive_root.pow((root_order / 2) as u128),
        FieldElement::one()
    );

    if lhs.is_zero() || rhs.is_zero() {
        return Polynomial::zero();
    }

    let mut root = primitive_root;
    let mut order = root_order;
    let degree = (lhs.degree() + rhs.degree()) as usize;

    if degree < 8 {
        return lhs.clone() * rhs.clone();
    }

    while degree < order / 2 {
        root = root.pow(2);
        order /= 2;
    }

    let mut lhs_coeffs = lhs.coefficients[..=(lhs.degree() as usize)].to_vec();
    lhs_coeffs.resize(order, FieldElement::zero());
    let mut rhs_coeffs = rhs.coefficients[..=(rhs.degree() as usize)].to_vec();
    rhs_coeffs.resize(order, FieldElement::zero());

    let lhs_codeword = ntt(root, &lhs_coeffs);
    let rhs_codeword = ntt(root, &rhs_coeffs);

    let hadamard: Vec<FieldElement> = lhs_codeword
        .iter()
        .zip(rhs_codeword.iter())
        .map(|(&l, &r)| l * r)
        .collect();

    let product_coefficients = intt(root, &hadamard);
    Polynomial::new(product_coefficients[..=degree].to_vec())
}

/// Fast zerofier computation via divide-and-conquer.
pub fn fast_zerofier(
    domain: &[FieldElement],
    primitive_root: FieldElement,
    root_order: usize,
) -> Polynomial {
    if domain.is_empty() {
        return Polynomial::zero();
    }
    if domain.len() == 1 {
        return Polynomial::new(vec![-domain[0], FieldElement::one()]);
    }
    let half = domain.len() / 2;
    let left = fast_zerofier(&domain[..half], primitive_root, root_order);
    let right = fast_zerofier(&domain[half..], primitive_root, root_order);
    fast_multiply(&left, &right, primitive_root, root_order)
}

/// Fast polynomial evaluation via divide-and-conquer.
pub fn fast_evaluate(
    polynomial: &Polynomial,
    domain: &[FieldElement],
    primitive_root: FieldElement,
    root_order: usize,
) -> Vec<FieldElement> {
    if domain.is_empty() {
        return vec![];
    }
    if domain.len() == 1 {
        return vec![polynomial.evaluate(domain[0])];
    }
    let half = domain.len() / 2;
    let left_zerofier = fast_zerofier(&domain[..half], primitive_root, root_order);
    let right_zerofier = fast_zerofier(&domain[half..], primitive_root, root_order);

    let left = fast_evaluate(
        &(polynomial.clone() % left_zerofier),
        &domain[..half],
        primitive_root,
        root_order,
    );
    let right = fast_evaluate(
        &(polynomial.clone() % right_zerofier),
        &domain[half..],
        primitive_root,
        root_order,
    );

    [left, right].concat()
}

/// Fast polynomial interpolation via divide-and-conquer.
pub fn fast_interpolate(
    domain: &[FieldElement],
    values: &[FieldElement],
    primitive_root: FieldElement,
    root_order: usize,
) -> Polynomial {
    assert_eq!(domain.len(), values.len());

    if domain.is_empty() {
        return Polynomial::zero();
    }
    if domain.len() == 1 {
        return Polynomial::new(vec![values[0]]);
    }

    let half = domain.len() / 2;
    let left_zerofier = fast_zerofier(&domain[..half], primitive_root, root_order);
    let right_zerofier = fast_zerofier(&domain[half..], primitive_root, root_order);

    let left_offset = fast_evaluate(&right_zerofier, &domain[..half], primitive_root, root_order);
    let right_offset = fast_evaluate(&left_zerofier, &domain[half..], primitive_root, root_order);

    let left_targets: Vec<FieldElement> = values[..half]
        .iter()
        .zip(left_offset.iter())
        .map(|(&n, &d)| n / d)
        .collect();
    let right_targets: Vec<FieldElement> = values[half..]
        .iter()
        .zip(right_offset.iter())
        .map(|(&n, &d)| n / d)
        .collect();

    let left_interpolant =
        fast_interpolate(&domain[..half], &left_targets, primitive_root, root_order);
    let right_interpolant =
        fast_interpolate(&domain[half..], &right_targets, primitive_root, root_order);

    left_interpolant * right_zerofier + right_interpolant * left_zerofier
}

/// Fast coset evaluation: evaluate polynomial on coset offset * <generator>.
pub fn fast_coset_evaluate(
    polynomial: &Polynomial,
    offset: FieldElement,
    generator: FieldElement,
    order: usize,
) -> Vec<FieldElement> {
    let scaled = polynomial.scale(offset);
    let mut coeffs = scaled.coefficients;
    coeffs.resize(order, FieldElement::zero());
    ntt(generator, &coeffs)
}

/// Fast coset division (clean division only).
pub fn fast_coset_divide(
    lhs: &Polynomial,
    rhs: &Polynomial,
    offset: FieldElement,
    primitive_root: FieldElement,
    root_order: usize,
) -> Polynomial {
    assert!(!rhs.is_zero(), "cannot divide by zero polynomial");

    if lhs.is_zero() {
        return Polynomial::zero();
    }
    assert!(
        rhs.degree() <= lhs.degree(),
        "cannot divide by polynomial of larger degree"
    );

    let mut root = primitive_root;
    let mut order = root_order;
    let degree = lhs.degree().max(rhs.degree()) as usize;

    if degree < 8 {
        return lhs.clone() / rhs.clone();
    }

    while degree < order / 2 {
        root = root.pow(2);
        order /= 2;
    }

    let scaled_lhs = lhs.scale(offset);
    let scaled_rhs = rhs.scale(offset);

    let mut lhs_coefficients = scaled_lhs.coefficients[..=(lhs.degree() as usize)].to_vec();
    lhs_coefficients.resize(order, FieldElement::zero());
    let mut rhs_coefficients = scaled_rhs.coefficients[..=(rhs.degree() as usize)].to_vec();
    rhs_coefficients.resize(order, FieldElement::zero());

    let lhs_codeword = ntt(root, &lhs_coefficients);
    let rhs_codeword = ntt(root, &rhs_coefficients);

    let quotient_codeword: Vec<FieldElement> = lhs_codeword
        .iter()
        .zip(rhs_codeword.iter())
        .map(|(&l, &r)| l / r)
        .collect();
    let scaled_quotient_coefficients = intt(root, &quotient_codeword);
    let quo_deg = (lhs.degree() - rhs.degree() + 1) as usize;
    let scaled_quotient = Polynomial::new(scaled_quotient_coefficients[..quo_deg].to_vec());

    scaled_quotient.scale(offset.inverse())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ntt_matches_evaluate() {
        let n = 16usize; // small for speed
        let primitive_root = FieldElement::primitive_nth_root(n as u128);
        let coefficients: Vec<FieldElement> =
            (0..n).map(|i| FieldElement::new(i as u128 + 1)).collect();
        let poly = Polynomial::new(coefficients.clone());

        let values = ntt(primitive_root, &coefficients);
        let domain: Vec<FieldElement> = (0..n).map(|i| primitive_root.pow(i as u128)).collect();
        let values_eval = poly.evaluate_domain(&domain);

        assert_eq!(values, values_eval, "ntt does not match evaluate_domain");
    }

    #[test]
    fn test_intt_inverts_ntt() {
        let n = 16usize;
        let primitive_root = FieldElement::primitive_nth_root(n as u128);
        let values: Vec<FieldElement> = (0..n)
            .map(|i| FieldElement::new(i as u128 * 7 + 3))
            .collect();

        let coeffs = ntt(primitive_root, &values);
        let values_again = intt(primitive_root, &coeffs);
        assert_eq!(values, values_again, "intt does not invert ntt");
    }

    #[test]
    fn test_fast_multiply() {
        let n = 64usize;
        let primitive_root = FieldElement::primitive_nth_root(n as u128);

        let lhs = Polynomial::new(vec![
            FieldElement::new(1),
            FieldElement::new(2),
            FieldElement::new(3),
        ]);
        let rhs = Polynomial::new(vec![FieldElement::new(4), FieldElement::new(5)]);

        let fast_product = fast_multiply(&lhs, &rhs, primitive_root, n);
        let slow_product = lhs * rhs;
        assert_eq!(fast_product, slow_product);
    }
}
