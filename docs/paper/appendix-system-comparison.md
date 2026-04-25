# Appendix: Public System Comparison Snapshot

Snapshot date: **April 24, 2026**

This appendix is a compact comparison table for the three systems most relevant to the
argument in the main paper. It inherits its source posture from Sections 6 and 7:
archival papers, official engineering/product materials, and commit-pinned repository
artifacts are used for different claim types and should not be read as a single matched
benchmark class.

Sources: rows inherit the main paper’s source set from Sections 6 and 7, especially
References 24-31, 35-40, 46, and 49.

It should be read with one rule in mind: these are **not** matched end-to-end benchmarks
on identical workloads. They are a structured comparison of public claims, committed
artifacts, and implementation scope.

## Table A1. DeepProve vs. BitSage Obelyzk (obelyzk.rs) vs. `provable-transformer-vm`

| Dimension                 | Lagrange DeepProve                                                                               | BitSage Obelyzk (obelyzk.rs)                                                                                                                                                        | `provable-transformer-vm`                                                                                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Primary role              | Production-oriented zkML system                                                                  | Public STARK-native zkML stack                                                                                                                                                      | Semantics-and-proof research artifact                                                                                                                                          |
| Proof family              | SNARK / SNARK-hybrid                                                                             | STARK-native on S-two / STWO                                                                                                                                                        | S-two / STWO only; narrow artifact-backed transformer and repeated-reuse research line                                                                                         |
| Public transformer scope  | Public claims of full GPT-2 inference and later Gemma-class progress                             | Public repo/verifier claims transformer-block support, recursive verifier milestones, and aggressive single-block benchmarks                                                        | Deterministic transformer-shaped VM, not full learned transformer inference                                                                                                    |
| Strongest public evidence | Official Lagrange product/blog materials                                                         | Docs.rs verifier page, Obelyzk paper, and Starknet Sepolia verification path                                                                                                        | Checked evidence files under `docs/paper/evidence/`, publication figures under `docs/paper/figures/`, and statement-versioned repo outputs                                  |
| Non-arithmetic handling   | Custom circuits and lookup-oriented techniques                                                   | LogUp-style lookup machinery on STWO                                                                                                                                                | Lookup-backed calibration rows now exist for normalization, softmax-exp, and binary-step activation; full learned softmax/inference remains out of scope                      |
| Backend maturity          | Strongest public deployment maturity of the three                                                | Strongest public STARK-native zkML signal                                                                                                                                           | Strongest semantics-portability story among the three                                                                                                                          |
| Public onchain posture    | Production/prover maturity emphasized more than public Starknet verification demos               | Starknet verification path and public demos emphasized                                                                                                                              | No onchain verifier integration yet                                                                                                                                            |
| Public onchain evidence   | Public materials emphasize production deployment more than named Starknet proof-demo identifiers | Docs.rs pins recursive verifier `0x1c208a5fe731c0d03b098b524f274c537587ea1d43d903838cc4a2bf90c40c7`, verified tx `0x276c6a448829c0f3975080914a89c2a9611fc41912aff1fddfe29d8f3364ddc`, and `942`-felt calldata; the paper reports `~280K` gas for one-layer verify and `~2.5M` gas for the full 40-layer Sepolia path | No public onchain proof-verification artifact set                                                                                                                              |
| Recursion posture         | Present in system architecture, but details vary by release                                      | Publicly aligned with S-two / STWO recursion path                                                                                                                                   | Recursive cryptographic compression not implemented; repo stops at frozen narrow S-two execution proofs, proof-carrying decoding demos, and a pre-recursive aggregation ladder |
| Paper relevance           | Main counterexample to categorical anti-SNARK claims                                             | Closest STARK-native comparator to the paper thesis                                                                                                                                 | Concrete local calibration and carried-state artifact surface that the paper can describe precisely                                                                             |
| Main caveat               | Strong public claims, but not directly comparable to STARK systems on identical workloads        | Public deployment evidence is stronger than the old README-only posture, but the public verifier object is still not a matched local comparator to this repo's pre-recursive artifacts; verifier docs still show uneven component maturity (`Attention` remains `Prover only`) | Narrow scope: local S-two wins now split by regime (`Phase12` proving, `Phase44D` typed-boundary latency, and `Phase71` handoff-receipt compactness), not a matched full-model benchmark or universal win |

## How to use this appendix

Use this appendix when the main paper needs one concise comparison object, but keep the
stronger qualifications in the main text:

- DeepProve is the strongest counterexample to categorical anti-SNARK claims.
- BitSage is the strongest public STARK-native comparator, and the pinned
  evidence is now a source-backed Starknet Sepolia recursive verifier object
  rather than a README-only benchmark line; it still needs to be separated into
  benchmark claims, onchain demos, and broader roadmap scope.
- `provable-transformer-vm` is not a frontier zkML prover; it is a trace-semantics and
  proof-architecture artifact with reproducible evidence and an explicit pre-recursive
  aggregation boundary.
- If you need one narrow verifier-object comparison rather than another full-model row,
  the only honest cross-system pairing in the pinned snapshot is `NANOZK`'s abstract
  `d <= 128` layer-proof row against this repo's `Phase71` handoff-receipt row. Use it
  as compact-object calibration only. It is explicitly not a matched benchmark.
