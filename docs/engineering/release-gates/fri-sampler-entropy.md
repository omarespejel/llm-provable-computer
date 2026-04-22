# FRI top-level index sampler entropy

## Background

`Fri::sample_index` mirrors the Python stark-anatomy reference implementation:
it folds the digest into a `u128` accumulator by `acc = (acc << 8) ^ byte` for
every byte in the input. The Python original does the same operation against
arbitrary-precision integers, so every byte of a 64-byte Blake2b-512 digest
contributes uniformly. In Rust, the high-order bytes shift off the top of
`u128` silently, and only the structure of the trailing 16 bytes survives in
`acc`. The remaining bias is well below the field's 128-bit security level for
the sizes the production prover uses, but it is nonetheless a strict reduction
of the sampler's effective entropy versus the reference.

This is pinned by a regression test:

```text
vanillastark::fri::tests::legacy_sample_index_truncates_high_order_digest_bytes
```

## What is staged

`Fri::sample_index_full_entropy` (`pub(crate)`) is a sibling sampler that:

- XOR-folds the digest in 16-byte chunks before reduction, so every byte of
  the input contributes uniformly to the accumulator;
- reduces modulo `size`, which is bias-free when `size` is a power of two
  (the only sizes the FRI domain construction produces).

A regression test exercises the entropy improvement directly:

```text
vanillastark::fri::tests::full_entropy_sample_index_distinguishes_high_order_digest_bytes
vanillastark::fri::tests::full_entropy_sample_index_returns_in_range
```

## Why the legacy sampler is left wired

Switching to the new sampler changes the FRI top-level indices and therefore
the proof bytes. Frozen artifacts under `docs/paper/artifacts/` cite specific
byte hashes; flipping the sampler under those hashes would invalidate them.
The new sampler is staged in-tree and regression-tested so that:

- the entropy gap is documented and pinned;
- a future `vanilla-v2` backend can swap to the new sampler in a single,
  reviewable commit that also bumps `proof_backend_version` and regenerates
  every cited bundle.

Until that backend bump lands, frozen artifacts and the public proving path
both go through the legacy sampler, and the available conjectured security
bits are unaffected for the trace lengths used in the shipped fixtures.

## Integer-only omicron-domain length

A related portability concern: `Stark::new` originally derived
`omicron_domain_length` as `1 << (bits.log2().ceil() as usize + 1).max(1)` over
`f64`. That form is bit-stable on every input the existing fixtures use, but
`f64::log2` rounds slightly differently across CPU architectures near
power-of-two boundaries, which would produce divergent domain sizes (and
therefore divergent proofs) at the boundary. The integer routine
`stark_omicron_domain_length` replaces it with `next_power_of_two * 2` and is
pinned by a sweep that proves equivalence on every realistic input:

```text
vanillastark::stark::tests::omicron_domain_length_matches_legacy_f64_form_on_normal_inputs
vanillastark::stark::tests::omicron_domain_length_is_always_power_of_two
```

This swap is byte-stable for every existing fixture and the platform-rounding
class of bug it eliminates is now closed.
