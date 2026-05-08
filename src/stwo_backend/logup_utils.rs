use ark_ff::{One, Zero};
use stwo::core::fields::qm31::SecureField;
use stwo::prover::backend::simd::qm31::PackedSecureField;

pub(crate) fn selector_masked_lookup_fraction_terms(
    claimed_selector: PackedSecureField,
    table_selector: PackedSecureField,
    claimed_q: PackedSecureField,
    table_q: PackedSecureField,
) -> (PackedSecureField, PackedSecureField) {
    let claimed_denominator = selector_masked_denominator(claimed_selector, claimed_q);
    let table_denominator = selector_masked_denominator(table_selector, table_q);
    (
        claimed_selector * table_denominator - table_selector * claimed_denominator,
        claimed_denominator * table_denominator,
    )
}

pub(crate) fn selector_masked_denominator(
    selector: PackedSecureField,
    denominator: PackedSecureField,
) -> PackedSecureField {
    let selector_lanes = selector.to_array();
    if selector_lanes
        .iter()
        .all(|selector_lane| *selector_lane != SecureField::zero())
    {
        return denominator;
    }

    let mut denominator_lanes = denominator.to_array();
    for (selector_lane, denominator_lane) in selector_lanes.iter().zip(denominator_lanes.iter_mut())
    {
        if *selector_lane == SecureField::zero() {
            // Disabled lookup sides contribute zero. Pin their denominator to
            // one so an irrelevant challenge-derived zero cannot break proving.
            *denominator_lane = SecureField::one();
        }
    }
    PackedSecureField::from_array(denominator_lanes)
}

#[cfg(test)]
mod tests {
    use super::*;
    use stwo::core::fields::m31::BaseField;

    #[test]
    fn selector_masked_denominator_uses_one_for_inactive_lanes() {
        let guarded =
            selector_masked_denominator(PackedSecureField::zero(), PackedSecureField::zero());
        assert!(guarded
            .to_array()
            .iter()
            .all(|lane| *lane == SecureField::one()));
    }

    #[test]
    fn selector_masked_denominator_preserves_active_lanes() {
        let denominator = PackedSecureField::broadcast(SecureField::from(BaseField::from(7u32)));
        let guarded = selector_masked_denominator(PackedSecureField::one(), denominator);
        assert_eq!(guarded.to_array(), denominator.to_array());
    }

    #[test]
    fn selector_masked_lookup_fraction_terms_preserve_one_sided_contributions() {
        let one = PackedSecureField::one();
        let zero = PackedSecureField::zero();
        let claimed_q = PackedSecureField::broadcast(SecureField::from(BaseField::from(7u32)));
        let table_q_zero = PackedSecureField::zero();
        let (numerator, denominator) =
            selector_masked_lookup_fraction_terms(one, zero, claimed_q, table_q_zero);
        assert_eq!(numerator.to_array(), one.to_array());
        assert_eq!(denominator.to_array(), claimed_q.to_array());

        let table_q = PackedSecureField::broadcast(SecureField::from(BaseField::from(11u32)));
        let table_multiplicity =
            PackedSecureField::broadcast(SecureField::from(BaseField::from(3u32)));
        let (numerator, denominator) =
            selector_masked_lookup_fraction_terms(zero, table_multiplicity, zero, table_q);
        assert_eq!((-numerator).to_array(), table_multiplicity.to_array());
        assert_eq!(denominator.to_array(), table_q.to_array());
    }
}
