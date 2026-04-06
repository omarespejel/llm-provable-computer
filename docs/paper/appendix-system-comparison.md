# Appendix: Public System Comparison Snapshot

Snapshot date: **April 4, 2026**

This appendix is a compact comparison table for the three systems most relevant to the argument in the main paper. It inherits its source posture from Sections 6 and 7: archival papers, official engineering/product materials, and commit-pinned repository artifacts are used for different claim types and should not be read as a single matched benchmark class.

Sources: rows inherit the main paper’s source set from Sections 6 and 7, especially References 24-31 and 35-39.

It should be read with one rule in mind: these are **not** matched end-to-end benchmarks on identical workloads. They are a structured comparison of public claims, committed artifacts, and implementation scope.

## Table A1. DeepProve vs. BitSage stwo-ml vs. `llm-provable-computer`

| Dimension | Lagrange DeepProve | BitSage stwo-ml | `llm-provable-computer` |
|---|---|---|---|
| Primary role | Production-oriented zkML system | Public STARK-native zkML stack | Semantics-and-proof research artifact |
| Proof family | SNARK / SNARK-hybrid | STARK-native on S-two / STWO | Vanilla STARK by default; experimental S-two backend for a narrow fixture set |
| Public transformer scope | Public claims of full GPT-2 inference and later Gemma-class progress | Public repo claims transformer-block support plus aggressive single-block benchmarks | Deterministic transformer-shaped VM, not full learned transformer inference |
| Strongest public evidence | Official Lagrange product/blog materials | Public repo, verifier docs, audit notes, Starknet verification path | Committed reproducibility bundle and statement-versioned repo outputs |
| Non-arithmetic handling | Custom circuits and lookup-oriented techniques | LogUp-style lookup machinery on STWO | `average-hard` proof path only; `softmax` not yet in proved relation |
| Backend maturity | Strongest public deployment maturity of the three | Strongest public STARK-native zkML signal | Strongest semantics-portability story among the three |
| Public onchain posture | Production/prover maturity emphasized more than public Starknet verification demos | Starknet verification path and public demos emphasized | No onchain verifier integration yet |
| Public onchain evidence | Public materials emphasize production deployment more than named Starknet proof-demo identifiers | Public verifier docs name `D8`, `D9`, `D10`, and `D11` as accepted on Starknet Sepolia | No public onchain proof-verification artifact set |
| Recursion posture | Present in system architecture, but details vary by release | Publicly aligned with S-two / STWO recursion path | Not implemented; repo currently stops at experimental S-two execution proofs plus batching/preparation seams |
| Current paper relevance | Main anti-overclaim counterexample for SNARK skepticism | Closest STARK-native comparator to the paper thesis | Concrete artifact that the paper can describe precisely |
| Main caveat | Strong public claims, but not directly comparable to STARK systems on identical workloads | Public materials mix benchmark claims, verification demos, and roadmap claims | Narrow scope: vanilla backend remains primary, `average-hard` only in the main proved relation, no full learned-model proving |

## How to use this appendix

Use this appendix when the main paper needs one concise comparison object, but keep the stronger qualifications in the main text:

- DeepProve is the strongest counterexample to categorical anti-SNARK claims.
- BitSage is the strongest public STARK-native comparator, but public evidence should be separated into benchmark claims, onchain demos, and broader roadmap scope.
- `llm-provable-computer` is not a frontier zkML prover; it is a trace-semantics and proof-architecture artifact with reproducible evidence.
