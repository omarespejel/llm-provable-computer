# RISC Zero d128 Statement Receipt Fixture

This fixture is intentionally small. The guest reads the #422 journal contract
bytes as private input and commits those exact bytes to the public RISC Zero
journal. The host proves or verifies that receipt against the generated image ID
and checks that the decoded journal bytes match the expected contract bytes.

This proves statement binding for the d128 two-slice receipt contract. It does
not recursively verify the underlying Stwo slice proofs inside RISC Zero.

## Toolchain Pin

This fixture is pinned to one zkVM route:

- `rustc 1.92.0`
- `rzup 0.5.0`
- `cargo-risczero 3.0.5`
- `r0vm 3.0.5`
- `risc0-zkvm =3.0.5`

Fresh environment setup:

```bash
curl -L https://risczero.com/install | bash
export PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH"
rzup --version  # must print 0.5.0 for this checked fixture
rzup install cargo-risczero 3.0.5
rzup install r0vm 3.0.5
rustup toolchain install 1.92.0 --component rustfmt --component rust-src
rzup show
cargo risczero --version
rustc +1.92.0 --version
```

The checked receipt is image-ID-bound, so changing any of these pins can change
the guest image and invalidate the checked receipt artifact.
