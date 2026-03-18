---
name: cross-validation
description: Cross-validate Rust implementations against the Python reference. Activate when testing, debugging mismatches, or verifying feature parity between Rust and Python outputs.
prerequisites: At least one Rust module implemented. Python 3 available on PATH.
---

# Cross-Validation

<purpose>
Ensure the Rust implementation produces identical results to the Python reference for all operations. Python is always the ground truth — if outputs differ, Rust is wrong.
</purpose>

<context>
The Python test suite in `stark-anatomy/code/test_*.py` provides test vectors. Each test can be run standalone:
```bash
cd stark-anatomy/code && python3 test_univariate.py
```

Cross-validation strategy:
1. For each module, identify 3-5 concrete test vectors from the Python tests.
2. Hardcode those exact inputs/outputs in Rust tests.
3. For complex operations (FRI, STARK), compare intermediate values.
</context>

<procedure>
### Per-Module Validation
1. **Field arithmetic**: Verify `Field.main().generator()` = `85408008396924667383611388730472331217`. Verify `generator^(p-1) = 1`. Verify `primitive_nth_root(n)^n = 1` for n = 2, 4, 8, ..., 2^119.

2. **Polynomial**: Use the test vectors from test_univariate.py:
   - a = [1, 0, 5, 2], b = [2, 2, 1], c = [0, 5, 2, 5, 5, 1]
   - Verify: a * (b + c) == a * b + a * c
   - Verify: divide(a*b, a) gives (b, zero)
   - Verify: interpolate on 5 points recovers the polynomial

3. **Merkle**: Compute Merkle root of known data, compare with Python.

4. **FRI**: Run FRI prove/verify with degree=63, expansion_factor=4, num_colinearity_tests=17. Valid codeword should verify; corrupted codeword should fail.

5. **STARK**: Use Rescue-Prime hash as computation. Input: `Field.main().sample(b'0xdeadbeef')`. Prove and verify should succeed. False boundary should fail.

### Debugging Mismatches
When Rust and Python outputs differ:
1. Identify the first point of divergence.
2. Print intermediate values in both languages.
3. Common causes:
   - Field arithmetic overflow (u128)
   - Different byte encoding for hashes
   - Serialization differences in ProofStream
   - Off-by-one in polynomial degree or array indexing

### Generating Python Reference Values
```bash
cd stark-anatomy/code && python3 -c "
from algebra import *
f = Field.main()
g = f.generator()
print('generator:', g.value)
print('g^2:', (g^2).value)
print('g^(p-1):', (g^(f.p-1)).value)
r = f.primitive_nth_root(1024)
print('root_1024:', r.value)
print('root_1024^1024:', (r^1024).value)
"
```
</procedure>

<patterns>
<do>
  - Run Python tests first to confirm they pass before comparing.
  - Use exact numeric values (not approximate) for all comparisons.
  - Test edge cases: zero polynomial, identity element, inverse of one.
  - For hash-dependent tests, ensure byte encoding matches exactly.
  - Document any intentional deviations from Python behavior.
</do>
<dont>
  - Don't assume Rust is correct when Python disagrees — Python is ground truth.
  - Don't skip intermediate value comparison — end-to-end mismatch is hard to debug.
  - Don't ignore serialization differences — they affect Fiat-Shamir and thus all proofs.
</dont>
</patterns>

<references>
- `stark-anatomy/code/test_univariate.py`: Polynomial test vectors
- `stark-anatomy/code/test_fri.py`: FRI test parameters and expected behavior
- `stark-anatomy/code/test_stark.py`: Full STARK prove/verify test
- `stark-anatomy/code/test_ntt.py`: NTT correctness tests
- `stark-anatomy/code/test_rescue_prime.py`: Hash function test vectors
- `stark-anatomy/code/test_merkle.py`: Merkle tree test vectors
</references>
