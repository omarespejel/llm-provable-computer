<identity>
vanillastark is a Rust port of aszepieniec/stark-anatomy — a minimalistic STARK (Scalable Transparent ARgument of Knowledge) proving system. Full feature parity with the Python reference in `stark-anatomy/code/`, minimal dependencies, production-grade quality.
</identity>

<stack>
| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language | Rust | edition 2024 | Requires rustc 1.85+ |
| Toolchain | stable | 1.91.1 | `rustup show` to verify |
| Package mgr | Cargo | 1.91.1 | Zero external deps — keep it that way |
| Testing | `cargo test` | built-in | Cross-validate against Python reference |
| Reference | Python 3 | stark-anatomy/code/ | The ground truth for all behavior |
| VCS | git | main | Subdirectory of transformer-vm-rs repo |
</stack>

<structure>
```text
vanillastark/
├── Cargo.toml                 # Crate manifest — edition 2024, no deps [agent: modify with care]
├── Cargo.lock                 # Lock file [agent: auto-generated]
├── README.md                  # Project description [agent: modify with care]
├── src/                       # Rust source [agent: create/modify]
│   ├── main.rs                # Binary entry point — currently placeholder
│   └── lib.rs                 # Library root — DOES NOT EXIST YET [create when starting]
├── stark-anatomy/             # Python reference implementation [READ ONLY]
│   ├── code/                  # Source + tests — THE GROUND TRUTH
│   │   ├── algebra.py         # Field, FieldElement, xgcd
│   │   ├── univariate.py      # Polynomial (univariate)
│   │   ├── multivariate.py    # MPolynomial (multivariate)
│   │   ├── merkle.py          # Merkle tree (blake2b)
│   │   ├── ip.py              # ProofStream (Fiat-Shamir)
│   │   ├── ntt.py             # NTT, fast polynomial ops
│   │   ├── fri.py             # FRI low-degree test protocol
│   │   ├── rescue_prime.py    # Rescue-Prime hash function
│   │   ├── stark.py           # STARK prover/verifier (basic)
│   │   ├── fast_stark.py      # STARK prover/verifier (NTT-optimized)
│   │   ├── rpsss.py           # Rescue-Prime STARK Signature Scheme
│   │   ├── fast_rpsss.py      # RPSSS (NTT-optimized)
│   │   └── test_*.py          # Test files — one per module
│   └── docs/                  # Tutorial docs (Jekyll site)
└── target/                    # Build artifacts [ignored]
```

### Planned Rust Module Tree (maps 1:1 to Python)
```text
src/
├── lib.rs                     # Re-exports all modules
├── field.rs                   # Field, FieldElement ← algebra.py
├── polynomial.rs              # Polynomial ← univariate.py
├── multivariate.rs            # MPolynomial ← multivariate.py
├── merkle.rs                  # Merkle ← merkle.py
├── proof_stream.rs            # ProofStream ← ip.py
├── ntt.rs                     # NTT functions ← ntt.py
├── fri.rs                     # Fri ← fri.py
├── rescue_prime.rs            # RescuePrime ← rescue_prime.py
├── stark.rs                   # Stark ← stark.py
├── fast_stark.rs              # FastStark ← fast_stark.py
├── rpsss.rs                   # RPSSS ← rpsss.py
├── fast_rpsss.rs              # FastRPSSS ← fast_rpsss.py
└── main.rs                    # CLI / demo entry
```
</structure>

<reference_implementation>
The Python reference in `stark-anatomy/code/` is authoritative. Before implementing any Rust module:
1. Read the corresponding `.py` file in full
2. Read its `test_*.py` file
3. Understand the API contract and invariants
4. Port behavior exactly — do not "improve" the math

### Module Dependency Graph (build order)
```
algebra.py ──→ Field, FieldElement, xgcd
    └── univariate.py ──→ Polynomial
            ├── multivariate.py ──→ MPolynomial
            └── ntt.py ──→ NTT, fast_multiply, fast_evaluate, etc.

merkle.py ──→ Merkle (blake2b)        [standalone]
ip.py ──→ ProofStream (shake_256)     [standalone]

fri.py ──→ Fri (uses: algebra, merkle, ip, ntt, univariate)
rescue_prime.py ──→ RescuePrime (uses: algebra, univariate, multivariate)
stark.py ──→ Stark (uses: fri, univariate, multivariate)
fast_stark.py ──→ FastStark (uses: fri, univariate, multivariate, ntt)
rpsss.py ──→ RPSSS (uses: rescue_prime, stark)
fast_rpsss.py ──→ FastRPSSS (uses: rescue_prime, fast_stark)
```

### Critical Constants
| Name | Value | Notes |
|------|-------|-------|
| Field prime `p` | `1 + 407 * 2^119` = `270497897142230380135924736767050121217` | 128-bit prime |
| Generator | `85408008396924667383611388730472331217` | Primitive root |
| Max NTT order | `2^119` | Smooth factor for NTT roots of unity |
| Hash (Merkle) | blake2b | Used in `merkle.py` |
| Hash (Fiat-Shamir) | shake_256 | Used in `ip.py` |
| Serialization | Python pickle | ProofStream uses pickle — Rust needs a compatible scheme |
</reference_implementation>

<commands>
| Task | Command | Notes |
|------|---------|-------|
| Build | `cargo build` | Should always succeed |
| Test | `cargo test` | Run after every module change |
| Test (verbose) | `cargo test -- --nocapture` | See println! output |
| Run | `cargo run` | Binary entry point |
| Check | `cargo check` | Fast type-check without codegen |
| Clippy | `cargo clippy` | Lint — fix all warnings |
| Format | `cargo fmt` | Apply rustfmt |
| Python tests | `cd stark-anatomy/code && python3 test_*.py` | Run reference tests |
| Python single | `cd stark-anatomy/code && python3 test_univariate.py` | Run one reference test |
</commands>

<conventions>
  <code_style>
    Naming: `snake_case` for functions/variables/modules, `CamelCase` for types/structs/enums.
    Files: One Rust file per Python module, `snake_case.rs`.
    Modules: All public, re-exported from `lib.rs`.
    Types: `FieldElement` wraps `u128`. `Polynomial` wraps `Vec<FieldElement>`.
    Arithmetic: Implement `Add`, `Sub`, `Mul`, `Div`, `Neg` via `std::ops` traits.
    Exponentiation: Use a `pow` method (not XOR operator like Python).
    Errors: Use `assert!` / `panic!` to match Python's assert behavior. No custom error types needed initially.
    Big integers: The field prime is 128-bit — `u128` native arithmetic suffices for single elements. Multiplication needs `u128 * u128 → u256` — use widening multiply or implement manually.
  </code_style>

  <patterns>
    <do>
      - Read the Python source before writing any Rust module.
      - Port test vectors from `test_*.py` into `#[cfg(test)]` modules.
      - Use `#[derive(Clone, Debug, PartialEq)]` on all core types.
      - Keep the API surface close to the Python names for traceability.
      - Implement `Display` for types that have `__str__` in Python.
      - Use `u128` for field element values — the prime fits in 128 bits.
      - Handle the 128-bit modular multiplication carefully (overflow).
    </do>
    <dont>
      - Don't add external dependencies without explicit approval. The project has a minimal-deps policy.
      - Don't rename Python APIs unless Rust idiom demands it (e.g., `__add__` → `impl Add`).
      - Don't optimize prematurely — correctness first, performance (NTT) second.
      - Don't implement `fast_stark.py` before `stark.py` works and passes tests.
      - Don't skip the `test_*.py` cross-validation — Python is the ground truth.
      - Don't use `BigUint` or `num` crate — stay with `u128` and manual widening.
    </dont>
  </patterns>

  <implementation_order>
    Phase 1 — Foundations (no dependencies between these):
      1. field.rs ← algebra.py (Field, FieldElement, xgcd)
      2. polynomial.rs ← univariate.py (Polynomial)

    Phase 2 — Extensions:
      3. multivariate.rs ← multivariate.py (MPolynomial)
      4. merkle.rs ← merkle.py (Merkle tree)
      5. proof_stream.rs ← ip.py (ProofStream)

    Phase 3 — Protocols:
      6. ntt.rs ← ntt.py (NTT operations)
      7. fri.rs ← fri.py (FRI protocol)
      8. rescue_prime.rs ← rescue_prime.py (hash function)

    Phase 4 — STARK:
      9. stark.rs ← stark.py (basic STARK)
      10. rpsss.rs ← rpsss.py (signature scheme)

    Phase 5 — Optimization:
      11. fast_stark.rs ← fast_stark.py (NTT-optimized STARK)
      12. fast_rpsss.rs ← fast_rpsss.py (NTT-optimized RPSSS)
  </implementation_order>

  <commit_conventions>
    Format: `type(scope): summary`
    Types: feat, fix, test, refactor, docs, chore
    Scope: module name (e.g., `field`, `polynomial`, `fri`, `stark`)
    Examples:
      - `feat(field): implement FieldElement with modular arithmetic`
      - `test(polynomial): port interpolation tests from Python`
      - `feat(fri): implement FRI prove and verify`
  </commit_conventions>
</conventions>

<workflows>
  <implement_module>
    1. Read the Python source file (e.g., `stark-anatomy/code/univariate.py`).
    2. Read its test file (e.g., `stark-anatomy/code/test_univariate.py`).
    3. Create `src/<module>.rs` with struct definitions and method stubs.
    4. Add `pub mod <module>;` to `src/lib.rs`.
    5. Implement methods one at a time, in dependency order within the file.
    6. Port test vectors from `test_*.py` into `#[cfg(test)] mod tests {}`.
    7. Run `cargo test` — all tests must pass.
    8. Run `cargo clippy` — fix all warnings.
    9. Run `cargo fmt`.
    10. Cross-validate: run Python test, run Rust test, compare outputs for same inputs.
  </implement_module>

  <cross_validate>
    For each module, ensure the Rust implementation produces identical outputs to Python:
    1. Pick a test case from `test_*.py`.
    2. Print intermediate values in both Python and Rust.
    3. Compare field element values, polynomial coefficients, Merkle roots.
    4. The field prime and generator must produce identical results.
    5. If outputs differ, the Rust implementation is wrong — Python is ground truth.
  </cross_validate>

  <add_dependency>
    Only if absolutely necessary (e.g., blake2b, shake_256):
    1. State the dependency name, version, and why it's needed.
    2. Confirm no pure-Rust std alternative exists.
    3. Get explicit approval before adding to Cargo.toml.
    4. Prefer `no_std`-compatible crates when possible.
  </add_dependency>
</workflows>

<boundaries>
  <forbidden>
    DO NOT modify under any circumstances:
    - `stark-anatomy/` — the entire Python reference is READ ONLY
    - `.git/` — VCS internals
    - `.env`, `*.pem`, `*.key` — secrets
  </forbidden>

  <gated>
    Modify only with explicit approval:
    - `Cargo.toml` — especially adding dependencies
    - `README.md`
  </gated>

  <safety_checks>
    Before any destructive operation:
    1. State what you're about to do.
    2. State what could go wrong.
    3. Wait for confirmation.
  </safety_checks>
</boundaries>

<troubleshooting>
  <known_issues>
  | Symptom | Cause | Fix |
  |---------|-------|-----|
  | `u128` overflow in multiplication | `a * b` can exceed 128 bits | Use widening: `(a as u128).wrapping_mul(b as u128)` with manual `u256` or `a.checked_mul(b)` pattern |
  | Field arithmetic gives wrong results | Modular reduction missing or wrong | Ensure every operation does `% p` where `p = 1 + 407 * (1 << 119)` |
  | Python `^` vs Rust `^` | Python `^` is XOR; Python code uses `^` for modular exponentiation via `__xor__` | In Rust, use a `pow(&self, exp: u128)` method, NOT the `BitXor` trait |
  | Polynomial division infinite loop | Off-by-one in degree check | Match Python's `divide()` logic exactly, especially the `while` condition |
  | Merkle root mismatch | Different hash or byte encoding | Ensure blake2b digest length and input encoding match Python exactly |
  | ProofStream Fiat-Shamir differs | Serialization format differs from Python pickle | The Fiat-Shamir hash must be deterministic; Rust serialization must produce identical bytes or use the same hash-of-objects approach |
  | `edition = "2024"` compile errors | Rust 2024 edition changes (e.g., `unsafe` in extern, lifetime elision) | Ensure rustc >= 1.85; check edition 2024 migration guide |
  </known_issues>

  <recovery_patterns>
    When stuck:
    1. Read the Python source — it's the answer key.
    2. Print intermediate values in both languages and compare.
    3. Check that `u128` arithmetic hasn't overflowed silently.
    4. Run `cargo test -- --nocapture` to see debug output.
    5. Simplify: test with small field (e.g., prime=97) before the full 128-bit prime.
  </recovery_patterns>
</troubleshooting>

<u128_arithmetic>
The field prime p = 270497897142230380135924736767050121217 fits in 128 bits.

Single-element operations:
- Addition: `(a + b) % p` — may overflow u128 if a + b > u128::MAX. Since p < 2^128, and a,b < p, a+b < 2p < 2^129. Use: `let sum = a.wrapping_add(b); if sum < a || sum >= p { sum.wrapping_sub(p) } else { sum }`
- Subtraction: `(p + a - b) % p` — safe since a,b < p.
- Multiplication: `a * b mod p` — requires 256-bit intermediate. Implement via: (1) split into hi/lo 64-bit, (2) or use `u128::widening_mul` on nightly, (3) or Barrett reduction.
- Inversion: Extended GCD (xgcd), ported directly from Python.
- Exponentiation: Square-and-multiply, ported from Python's `__xor__`.

This is the hardest part of the port. Get field arithmetic right first — everything else depends on it.
</u128_arithmetic>

<environment>
- Harness: Claude Code via terminal
- File system scope: full project access
- Network access: available
- Tool access: git, shell, cargo, python3
- Human interaction model: synchronous chat with explicit approval for gated work
- Working directory: /Users/abdel/dev/me/machine-learning/transformer-vm-rs/vanillastark
</environment>

<skills>
Modular skills live in `.codex/skills/` (with symlinks at `.claude/skills/` and `.agents/skills/`).

Available skills:
- `finite-field-arithmetic.md`: Implement Field/FieldElement with u128 modular arithmetic, xgcd, and all operator traits
- `polynomial-ops.md`: Implement Polynomial and MPolynomial with division, interpolation, evaluation, zerofier
- `fri-stark-protocol.md`: Implement FRI, Merkle, ProofStream, Stark, and the full prove/verify pipeline
- `cross-validation.md`: Cross-validate Rust output against Python reference using shared test vectors

Load only the skill relevant to the current task.
</skills>

<memory>
  <project_decisions>
    - 2026-03-18: Port stark-anatomy Python → Rust with exact feature parity — pedagogical clarity over performance
    - 2026-03-18: Use Rust edition 2024, zero external dependencies (unless hash functions require it)
    - 2026-03-18: Use u128 for field elements — the 128-bit prime fits, avoids BigInt dependency
    - 2026-03-18: Implementation order follows dependency graph: field → polynomial → multivariate → merkle/ip → ntt → fri → rescue_prime → stark → rpsss
  </project_decisions>

  <lessons_learned>
    - Python uses `__xor__` (`^`) for modular exponentiation — this is NOT bitwise XOR. Rust must use a `.pow()` method.
    - The field prime 1 + 407*2^119 is specifically chosen for NTT — it has 2^119 as a smooth factor, enabling roots of unity.
    - u128 multiplication overflow is the primary implementation hazard. Must use widening multiply.
    - Python `pickle` serialization in ProofStream affects Fiat-Shamir hashes. Rust needs a compatible approach or its own deterministic serialization.
  </lessons_learned>
</memory>
