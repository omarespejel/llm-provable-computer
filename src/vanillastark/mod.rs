//! Minimal vanilla STARK prover/verifier used as the Milestone 2 baseline.

pub mod field;
pub mod fri;
pub mod merkle;
pub mod multivariate;
pub mod ntt;
pub mod polynomial;
pub mod proof_stream;
pub mod rescue_prime;
pub mod stark;

pub use field::{FieldElement, P};
pub use fri::Fri;
pub use merkle::Merkle;
pub use multivariate::MPolynomial;
pub use polynomial::Polynomial;
pub use proof_stream::{ProofObject, ProofStream};
pub use rescue_prime::RescuePrime;
pub use stark::Stark;
