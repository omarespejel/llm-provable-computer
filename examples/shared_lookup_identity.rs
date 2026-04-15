//! Minimal shared-lookup identity example.
//!
//! This example keeps runtime tiny by using a small hardcoded shared-lookup row set.
//! It demonstrates the public commitment helper, then shows that a registry keyed
//! by the commitment can deduplicate identical row sets without ambiguity.

#[cfg(not(feature = "stwo-backend"))]
fn main() {
    eprintln!("This example requires the `stwo-backend` feature.");
    std::process::exit(1);
}

#[cfg(feature = "stwo-backend")]
use std::collections::BTreeMap;

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::commit_phase12_shared_lookup_rows;

#[cfg(feature = "stwo-backend")]
fn main() {
    let layout_commitment = "example-layout-commitment-v1";
    let shared_lookup_rows = vec![1, 0, 1, 1, 0, 1, 0, 0];

    let first_commitment =
        commit_phase12_shared_lookup_rows(layout_commitment, &shared_lookup_rows);
    let second_commitment =
        commit_phase12_shared_lookup_rows(layout_commitment, &shared_lookup_rows);

    assert_eq!(
        first_commitment, second_commitment,
        "the same shared-lookup rows must always produce the same commitment"
    );

    let mut registry: BTreeMap<String, Vec<i16>> = BTreeMap::new();
    let replaced = registry.insert(first_commitment.clone(), shared_lookup_rows.clone());
    assert!(
        replaced.is_none(),
        "first insertion should populate the registry"
    );

    let deduped = registry.insert(second_commitment.clone(), shared_lookup_rows.clone());
    assert!(
        deduped.is_some(),
        "a second insertion under the same commitment should be recognized as the same identity"
    );

    println!("shared_lookup_identity: ok");
    println!("layout_commitment: {}", layout_commitment);
    println!("shared_lookup_commitment: {}", first_commitment);
    println!("shared_lookup_row_count: {}", shared_lookup_rows.len());
    println!("registry_size: {}", registry.len());
}
