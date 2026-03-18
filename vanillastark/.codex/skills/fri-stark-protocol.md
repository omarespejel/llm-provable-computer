---
name: fri-stark-protocol
description: Implement FRI low-degree test, Merkle tree, ProofStream, NTT, Rescue-Prime, STARK prover/verifier, and RPSSS signature scheme. Activate when working on fri.rs, merkle.rs, proof_stream.rs, ntt.rs, rescue_prime.rs, stark.rs, fast_stark.rs, rpsss.rs, or any proving/verification logic.
prerequisites: field.rs and polynomial.rs must be complete and tested. Read the corresponding Python files.
---

# FRI & STARK Protocol

<purpose>
Port the cryptographic protocol stack: Merkle trees, proof streams, FRI, NTT, Rescue-Prime hash, and the full STARK prover/verifier. This is the bulk of the project — 6+ modules with complex interdependencies.
</purpose>

<context>
Module build order within this skill:
1. `merkle.rs` ← merkle.py (standalone, uses blake2b)
2. `proof_stream.rs` ← ip.py (standalone, uses shake_256)
3. `ntt.rs` ← ntt.py (depends on polynomial.rs)
4. `fri.rs` ← fri.py (depends on all above + field + polynomial)
5. `rescue_prime.rs` ← rescue_prime.py (depends on field + polynomial + multivariate)
6. `stark.rs` ← stark.py (depends on fri + all polynomial types)
7. `fast_stark.rs` ← fast_stark.py (stark + ntt optimization)
8. `rpsss.rs` / `fast_rpsss.rs` ← signature schemes using stark

### Dependency Decision: Hash Functions
The Python reference uses:
- `blake2b` (from hashlib) for Merkle trees
- `shake_256` (from hashlib) for Fiat-Shamir
- `pickle` for ProofStream serialization

Rust options:
- `blake2` crate or implement manually
- Rust stdlib has no blake2b/shake_256 — external crates likely needed
- This MAY require adding dependencies to Cargo.toml (GATED — need approval)

Alternative: Use a pure-Rust implementation or a different hash that produces identical outputs.
</context>

<procedure>
### merkle.rs
1. Port `Merkle` class — static methods: `commit`, `open`, `verify`.
2. Commit: hash each leaf, build binary tree bottom-up.
3. Open: produce authentication path (list of sibling hashes).
4. Verify: recompute root from leaf + path.
5. Need blake2b — either add `blake2` crate or implement.

### proof_stream.rs
1. Port `ProofStream` class — push/pull objects, Fiat-Shamir.
2. `push(obj)` appends to list. `pull()` reads next.
3. `prover_fiat_shamir()` hashes ALL objects.
4. `verifier_fiat_shamir()` hashes objects up to read_index.
5. Serialization: Python uses pickle. Rust needs deterministic serialization.
   Decision: implement a simple custom binary serialization that's consistent.
6. Need shake_256 — either add `sha3` crate or implement.

### ntt.rs
1. Port NTT (Number Theoretic Transform) and inverse NTT.
2. Port `fast_multiply`, `fast_zerofier`, `fast_evaluate`, `fast_interpolate`.
3. Port `fast_coset_evaluate`, `fast_coset_divide`.
4. NTT works because the field has 2^119 smooth order.
5. These are performance optimizations — not needed for basic STARK but needed for fast_stark.

### fri.rs
1. Port `Fri` class with `prove` and `verify`.
2. `commit`: split-and-fold codeword, commit each layer via Merkle.
3. `query`: open pairs of positions across layers.
4. `prove`: orchestrate commit rounds + queries.
5. `verify`: check Merkle openings + colinearity.
6. Key parameters: offset, omega, domain_length, expansion_factor, num_colinearity_tests.

### rescue_prime.rs
1. Port `RescuePrime` class — custom hash function for STARK-friendly hashing.
2. Contains hardcoded round constants (274 lines in Python).
3. `hash(input) -> output` — the core hash function.
4. `trace(input) -> execution trace` — produces the algebraic execution trace for STARK.
5. `transition_constraints(omicron) -> [MPolynomial]` — the AIR constraints.
6. `boundary_constraints(output) -> [(cycle, register, value)]`.

### stark.rs
1. Port `Stark` class with `prove` and `verify`.
2. `prove(trace, transition_constraints, boundary) -> proof`
3. `verify(proof, transition_constraints, boundary) -> bool`
4. This is the capstone — orchestrates FRI, polynomials, Merkle, ProofStream.

### rpsss.rs
1. Port `RPSSS` (Rescue-Prime STARK Signature Scheme).
2. `keygen() -> (sk, pk)`, `sign(sk, doc) -> sig`, `verify(pk, doc, sig) -> bool`.
3. Uses STARK prove/verify internally.
</procedure>

<patterns>
<do>
  - Implement modules in dependency order: merkle → proof_stream → ntt → fri → rescue_prime → stark → rpsss.
  - For hash functions, propose adding `blake2` and `sha3` crates — these are well-audited, minimal crates.
  - Test FRI with the exact parameters from test_fri.py: degree=63, expansion_factor=4, num_colinearity_tests=17.
  - Test STARK with RescuePrime as the computation (matches test_stark.py).
  - Keep prove/verify APIs close to Python: same parameter names, same return types.
</do>
<dont>
  - Don't try to implement blake2b or shake_256 from scratch — use audited crates.
  - Don't change the FRI folding logic — it's subtle and the Python version is correct.
  - Don't skip the Rescue-Prime round constants — they must be identical to Python.
  - Don't optimize before the basic STARK works — implement stark.rs before fast_stark.rs.
</dont>
</patterns>

<troubleshooting>
| Symptom | Cause | Fix |
|---------|-------|-----|
| Merkle verify fails | Hash input ordering (left/right child) wrong | Check index parity: even index = leaf is left child |
| FRI verify rejects valid proof | Colinearity check fails due to wrong domain element | Verify omega^i computation matches Python |
| STARK verify rejects valid proof | Fiat-Shamir randomness differs | Serialization must be deterministic and match Python's output |
| Rescue-Prime hash differs from Python | Round constants wrong or s-box exponent wrong | Copy constants verbatim from Python; verify alpha/alphainv |
| ProofStream desync | push/pull order differs between prove and verify | The prove/verify must push/pull in identical order |
</troubleshooting>

<references>
- `stark-anatomy/code/merkle.py`: 44 lines — Merkle commit/open/verify
- `stark-anatomy/code/ip.py`: 31 lines — ProofStream with Fiat-Shamir
- `stark-anatomy/code/ntt.py`: 177 lines — NTT and fast polynomial operations
- `stark-anatomy/code/fri.py`: 232 lines — FRI low-degree test
- `stark-anatomy/code/rescue_prime.py`: 274 lines — Rescue-Prime hash
- `stark-anatomy/code/stark.py`: 270 lines — STARK prover/verifier
- `stark-anatomy/code/fast_stark.py`: 287 lines — NTT-optimized STARK
- `stark-anatomy/code/rpsss.py`: 65 lines — Signature scheme
- `stark-anatomy/docs/fri.md`: FRI tutorial explanation
- `stark-anatomy/docs/stark.md`: STARK tutorial explanation
</references>
