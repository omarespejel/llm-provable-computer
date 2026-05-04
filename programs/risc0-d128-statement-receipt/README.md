# RISC Zero d128 Statement Receipt Fixture

This fixture is intentionally small. The guest reads the #422 journal contract
bytes as private input and commits those exact bytes to the public RISC Zero
journal. The host proves or verifies that receipt against the generated image ID
and checks that the decoded journal bytes match the expected contract bytes.

This proves statement binding for the d128 two-slice receipt contract. It does
not recursively verify the underlying Stwo slice proofs inside RISC Zero.
