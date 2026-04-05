# On the Alignment of Transformer Workloads and STARK Proof Systems

**Omar Espejel**  
Starknet Foundation  
April 2026

---

## Abstract

This paper presents a transformer-specific complexity analysis comparing SNARK circuit size and STARK trace length for verifiable inference. Arithmetic work in a standard transformer block maps similarly in both settings, but non-arithmetic primitives such as softmax, normalization, and activation functions stress the two proving families differently. Under the representative cost model used throughout this paper (`C_exp = 300`, `C_norm = 30`, `C_nonlin = 150`), GPT-2 small (`d = 768`, `T = 1024`, `H = 12`, `L = 12`) yields approximately `157.8B` SNARK constraints versus `106.5B` STARK trace rows across 12 layers, or about `1.48x` more symbolic proving work on the SNARK side under these assumptions. The gap widens with sequence length because the softmax-related overhead scales quadratically in `T`.

We complement this analytic comparison with a concrete proof-stack prototype, [`llm-provable-computer`](https://github.com/omarespejel/llm-provable-computer), in which execution traces from a deterministic transformer-shaped virtual machine are directly consumable as AIR witnesses. The current repository strengthens this thesis with statement-versioned claims, transformer/native lockstep verification, multi-engine differential checks, ONNX export and validation, and research-oriented semantic certificates. The resulting claim is narrower and stronger than a generic “STARKs beat SNARKs” position: transformer workloads expose precisely the dimensions on which STARK-native systems may compound advantages, while modern SNARK systems remain serious and rapidly improving competitors. A compact public-system comparison is included in `docs/paper/appendix-system-comparison.md`.

---

## 1. Introduction

Verifiable inference matters because model outputs are now operational inputs. If a model score can trigger a trade, influence a diagnosis, decide a routing path, or authorize an onchain action, then “trust me, the model ran” is not enough. The problem is no longer only one of privacy or provenance; it is one of computational integrity.

The zkML ecosystem has already shown that proving neural network inference is feasible. Sumcheck-based systems have made linear layers practical. Lookup-based systems have shown that non-polynomial functions can be handled efficiently enough to support real workloads. Production-oriented stacks such as DeepProve have demonstrated that SNARK-based architectures can prove full transformer inference. STARK-native systems such as BitSage stwo-ml and Giza/StarkWare’s LuminAIR show that the alternative design space is no longer theoretical.

The question addressed here is therefore narrower and more useful than “can transformers be proved?” The question is: **which proof architecture compounds most cleanly as transformer workloads scale in model size, sequence length, and deployment complexity?**

This paper makes three distinct claims:

1. **Analytic claim.** Under a stated transformer cost model, non-arithmetic operations such as softmax, LayerNorm, and GELU can shift prover economics in favor of STARK-native systems.
2. **Systems claim.** Deterministic transformer-style execution can be compiled into traces that are directly consumable as AIR witnesses.
3. **Infrastructure claim.** The S-two / Starknet stack makes this direction increasingly practical, even though the reference repository used here does not yet implement a production S-two backend.

The repository artifact supports the second claim directly. The first claim is a model-based comparison, not an apples-to-apples end-to-end benchmark of production provers on identical hardware. The third claim is partially supported by recent StarkWare and Starknet releases, but remains ahead of the current repository implementation. The paper therefore aims to be a rigorous architecture-and-systems thesis, not a final empirical verdict on STARK versus SNARK transformer proving.

---

## 2. Background

### 2.1 STARKs, AIR, and Circle STARKs

STARKs arithmetize computation as an execution trace and a set of polynomial transition constraints. In AIR form, each row of the trace represents one machine step, and low-degree constraints express valid state evolution. Soundness is then reduced to polynomial proximity testing via FRI and related machinery. The core appeal for prover-heavy workloads is transparent setup, post-quantum security, and a prover dominated by field arithmetic, FFT-style operations, and hash commitments rather than elliptic-curve MSMs.

Circle STARKs adapt the STARK framework to the Mersenne-31 field (`2^31 - 1`), enabling highly efficient arithmetic over a chip-friendly field. StarkWare’s S-two prover is the current flagship implementation of this direction and is explicitly positioned for recursion, client-side proving, zkML, and Starknet integration. In this paper, **S-two** follows StarkWare’s current public naming, while **STWO** is used only when referring to repository, crate, or project names that retain the older capitalization. StarkWare’s January 27, 2026 S-two 2.0.0 announcement describes the prover suite as fully open source and developer-ready, and the public S-two materials state that recursive proving is supported out of the box ([StarkWare, January 27, 2026](https://starkware.co/blog/s-two-2-0-0-prover-for-developers/); [StarkWare, May 26, 2025](https://starkware.co/blog/s-two-prover/)). On March 31, 2026, StarkWare announced a further recursion upgrade from Cairo-based recursion to circuit-based recursion, reporting a reduction from roughly one minute to roughly three seconds for proving verification in the recursive path ([StarkWare, March 31, 2026](https://starkware.co/blog/minutes-to-seconds-efficiency-gains-with-recursive-circuit-proving/)). These improvements matter directly for any architecture that expects to aggregate many proofs or compress them for onchain verification.

### 2.2 SNARKs, GKR, and modern zkML

Modern zkML systems rarely rely on naive gate-by-gate circuits for the entire model. Instead, they combine multiple proof techniques. GKR and sumcheck handle large linear algebra blocks efficiently. Lookup arguments or custom circuits handle non-polynomial functions such as exponentials, normalization, and activation functions. The practical competition is therefore not “R1CS vs AIR” in isolation; it is a competition among system architectures that mix arithmetization strategies, commitment schemes, recursion mechanisms, and hardware assumptions.

That distinction matters for this paper. The model developed below does **not** claim that every modern SNARK implementation literally pays a naive `100–500` constraint cost for every non-arithmetic operation in the same way. It instead uses representative constants to show how transformer workloads can amplify overhead in proof systems whose handling of non-arithmetic primitives is less native than the lookup-centric STARK path.

### 2.3 LogUp and lookup-heavy workloads

Lookup arguments are central to the argument because the transformer bottlenecks of interest are not just matrix multiplies. Softmax requires exponentials and normalization. LayerNorm requires division and square-root-like structure. GELU requires nonlinear approximations. LogUp-style lookup arguments let a prover show that each quantized evaluation belongs to a precommitted table with low additional algebraic degree, making these operations comparatively natural in STARK-native designs.

---

## 3. Transformer Operation Count

We consider a standard transformer block with model dimension `d`, sequence length `T`, number of heads `H`, head dimension `d_k = d / H`, and feedforward expansion `4d`.

### 3.1 Arithmetic operations

Arithmetic work per layer is:

- QKV projection: `3Td^2`
- Attention scores: `T^2 d`
- Value aggregation: `T^2 d`
- Output projection: `Td^2`
- Feedforward network: `8Td^2`
- LayerNorm linear scaling: `2Td`

Summing the dominant arithmetic components gives:

```text
12Td^2 + 2T^2d + 2Td
```

### 3.2 Non-arithmetic operations

Non-arithmetic work per layer is:

- Softmax: `T^2 H`
- LayerNorm nonlinear component: `2Td`
- GELU: `4Td`

Summing these terms gives:

```text
T^2H + 6Td
```

The key structural point is not just that these terms exist, but that they become more important precisely in the regimes that matter for modern transformers: long contexts and repeated normalization / activation over wide hidden states.

---

## 4. A Transformer-Specific Cost Model

This section is the analytic core of the paper. It should be read as a **model-based comparison of symbolic proving work**, not as a controlled head-to-head benchmark of complete production systems.

### 4.1 SNARK-side symbolic cost

Using representative constants for non-arithmetic operations,

- `C_exp = 300`
- `C_norm = 30`
- `C_nonlin = 150`

we model the per-layer SNARK-side cost as:

```text
C_SNARK = 12Td^2 + 2T^2d + T^2H * C_exp + 2Td * C_norm + 4Td * C_nonlin
```

This keeps the arithmetic term shared with the STARK side and makes explicit where the non-arithmetic amplification enters.

The constants `C_exp`, `C_norm`, and `C_nonlin` are **stylized comparative constants**, not normalized measurements extracted from one production prover stack running on one fixed hardware configuration. Their role is to make the model’s sensitivity to non-arithmetic work explicit, not to claim benchmark equivalence with any single deployed system.

### 4.2 STARK-side symbolic cost

For the STARK side, we keep the exact expression:

```text
L_STARK = 12Td^2 + 2T^2d + T^2H + 6Td
```

The earlier draft approximated this as `12Td^2 + 3T^2d`, which is not justified for GPT-2 small because `H << d`. For GPT-2 small, `H = 12` and `d = 768`, so the `T^2H` term is `64x` smaller than a `T^2d` term. The asymptotic point remains valid, but the approximation materially inflated the STARK side numerically.

### 4.3 Concrete analysis: GPT-2 small

Instantiating the model with GPT-2 small parameters (`d = 768`, `T = 1024`, `H = 12`, `L = 12`) gives the following.

| Component | SNARK (constraints) | STARK (trace rows) | Ratio |
|---|---:|---:|---:|
| Arithmetic | 8,858,370,048 | 8,858,370,048 | 1.00x |
| Softmax | 3,774,873,600 | 12,582,912 | 300x |
| LayerNorm | 47,185,920 | 1,572,864 | 30x |
| GELU | 471,859,200 | 3,145,728 | 150x |
| Total per layer | 13,152,288,768 | 8,875,671,552 | 1.48x |
| Total (12 layers) | 157,827,465,216 | 106,508,058,624 | 1.48x |

Under this cost model, the non-arithmetic overhead adds about `4.29B` SNARK constraints versus about `17.3M` STARK rows per layer at `T = 1024`. Softmax alone contributes about `87.9%` of the SNARK non-arithmetic overhead. Scaling the same model to `T = 4096` yields an overall ratio of about `2.13x`, so the qualitative claim that the gap widens with context length remains intact.

### 4.4 Interpretation

This analysis does **not** prove that every STARK system is faster than every SNARK system on every transformer workload. It supports a narrower claim: once both sides handle large linear algebra efficiently, the remaining battleground is dominated by lookup handling, recursion, field arithmetic, and commitment backend. Transformer workloads expose these differences more sharply than many standard proving benchmarks do.

### 4.5 Scaling the symbolic model to released Gemma 3 architectures

The GPT-2-small analysis is useful because it keeps the algebra transparent, but it is no longer enough on its own. DeepProve has publicly reported proving inference for Gemma 3-class models, and Lagrange’s September 2025 engineering update is explicit that supporting Gemma 3 required new handling for grouped-query attention (GQA), alternating local/global attention, RMSNorm, GeGLU, and RoPE ([Lagrange, October 20, 2025](https://lagrange.dev/engineering-updates/september-2025)). Meanwhile, Hugging Face’s Gemma 3 documentation describes the released family as using **five local sliding-window self-attention layers for every global self-attention layer**, with long-context support up to `128K` in the larger variants ([Hugging Face Gemma 3 docs](https://huggingface.co/docs/transformers/en/model_doc/gemma3)).

For Gemma-style layers, we therefore refine the notation. Let `n_q` be the number of query heads, `n_kv` the number of key/value heads, `d_h` the head dimension, `q = n_q d_h`, `k = n_kv d_h`, `m` the MLP intermediate size, `L_g` the number of global-attention layers, `L_l` the number of local-attention layers, `W` the local sliding-window span, and `W_eff(T) = min(T, W)`. Using the same stylized comparative constants as above, the architecture-aware symbolic model becomes:

```text
A_Gemma(T) = L[Td(q + 2k) + Tdq + 3Tdm] + 2q[L_g T^2 + L_l T W_eff(T)]
S_Gemma(T) = n_q[L_g T^2 + L_l T W_eff(T)]
C_SNARK^Gemma(T) = A_Gemma(T) + S_Gemma(T) * C_exp + 2LTd * C_norm + LTm * C_nonlin
L_STARK^Gemma(T) = A_Gemma(T) + S_Gemma(T) + 2LTd + LTm
```

This keeps the paper’s original comparison logic intact while replacing the dense-attention surrogate with Gemma-aware GQA and local/global attention terms. It remains a symbolic cost model, not a matched benchmark.

For the released `Gemma 3 270M` checkpoint, public config mirrors expose `18` layers, hidden size `640`, `4` query heads, `1` KV head, head dimension `256`, intermediate size `2048`, `32K` maximum context, a `512`-token sliding window, and an explicit repeating pattern of five `sliding_attention` layers followed by one `full_attention` layer ([public config mirror](https://huggingface.co/HedronCreeper/gemma-3-270m-custom-hedron/raw/main/config.json)). Instantiating the architecture-aware model with `L = 18`, `L_g = 3`, `L_l = 15`, `d = 640`, `n_q = 4`, `n_kv = 1`, `d_h = 256`, `m = 2048`, and `W = 512` gives:

| Context (`T`) | SNARK symbolic work | STARK symbolic work | Ratio | Non-arithmetic share of SNARK |
|---:|---:|---:|---:|---:|
| 128 | 14.6B | 13.4B | 1.08x | 7.9% |
| 2,048 | 310.0B | 263.6B | 1.18x | 15.1% |
| 8,192 | 1.731T | 1.364T | 1.27x | 21.3% |
| 32,768 | 14.769T | 10.414T | 1.42x | 29.6% |

This is the right qualitative result. The gap persists, but it is more modest than one would get by pretending Gemma 3 is dense full attention in every layer. Gemma’s local/global sparsity dampens the quadratic attention burden in most layers, so the architecture-aware `32K` result is about `1.42x`, not an inflated `~3x` headline. Even so, the non-arithmetic share keeps rising with context, and within that non-arithmetic budget the softmax term becomes progressively dominant, increasing from about `30.8%` of non-arithmetic SNARK overhead at `T = 128` to about `95.3%` at `T = 32,768`.

The same conclusion survives at a larger frontier point. Public config mirrors for `Gemma 3 27B` expose `62` layers, hidden size `5376`, `32` query heads, `16` KV heads, head dimension `128`, intermediate size `21504`, `128K` maximum context, and a `1024`-token sliding window ([public config mirror](https://huggingface.co/Changgil/google-gemma-3-27b-it-text/raw/main/config.json)). Combining those values with the same `5:1` local/global attention schedule gives approximately `6.565 quadrillion` SNARK constraints versus `4.826 quadrillion` STARK rows at `128K` context, or about `1.36x` more symbolic work on the SNARK side. In that setting, the non-arithmetic component contributes about `26.6%` of total SNARK symbolic work, and softmax accounts for about `98.3%` of non-arithmetic overhead.

The main lesson is therefore narrower and stronger than the older dense-attention surrogate. Released long-context production architectures such as Gemma 3 already temper the attention burden through sparsity. Even after respecting that design, the symbolic divergence persists and the softmax-dominated non-arithmetic component becomes increasingly important as context grows. That is a better stress test for this paper’s thesis than GPT-2-small precisely because the architecture is already optimized to suppress long-context attention cost.

---

## 5. Repository Artifact: A Semantics-Hardened Transformer-VM Proof Stack

The implementation artifact used in this paper is the open repository [`omarespejel/llm-provable-computer`](https://github.com/omarespejel/llm-provable-computer). The right way to describe it is **not** “a production zkML stack for full transformer inference.” The right description is: **a semantics-and-proof artifact demonstrating that deterministic transformer-shaped execution can be compiled into traces that are directly usable as AIR witnesses**.

### 5.1 What the repository demonstrates today

The current mainline implementation provides:

- a deterministic transformer-shaped virtual machine,
- a statement-versioned proof claim (`statement-v1`),
- transformer/native lockstep verification,
- multi-engine differential checks across transformer, native, Burn, and ONNX paths,
- ONNX export and independent validation,
- `research-v2` semantic artifacts for one-step, prefix-trace, and matrix equivalence checks,
- a production-oriented local proving profile (`production-v1`), and
- a reproducibility bundle with artifact hashes and benchmark metadata.

These are materially stronger claims than the original draft made. They support the trace-as-witness thesis directly and move the repository beyond a minimal proof-of-concept interpreter.

### 5.2 What the repository does **not** yet demonstrate

The repository remains deliberately narrow in several important ways:

- the in-repo proof path still uses a custom vanilla STARK backend rather than S-two,
- the proved attention mode is currently `average-hard`, not standard softmax,
- learned/trained weights remain out of scope,
- zero-knowledge hiding is not implemented,
- full-ISA AIR coverage for all bitwise and compare instructions is not complete.

These limits matter because the paper’s strongest architectural claim is about lookup-heavy standard transformer nonlinearities on an S-two-style stack. The repository supports the structural trace thesis, but it does not yet close the loop on that full claim.

### 5.3 Reproducible artifact bundle

On April 4, 2026, we generated a `production-v1` reproducibility bundle from commit `58bb05f` with benchmark metadata, exact command logs, SHA-256 hashes, and proof artifacts. The committed appendix index and raw metadata are included in this repository under:

- `docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md`
- `docs/paper/artifacts/production-v1-2026-04-04/manifest.txt`
- `docs/paper/artifacts/production-v1-2026-04-04/benchmarks.tsv`
- `docs/paper/artifacts/production-v1-2026-04-04/sha256sums.txt`
- `docs/paper/artifacts/production-v1-2026-04-04/commands.log`

The artifact bundle includes STARK proofs for `addition`, `dot_product`, `single_neuron`, and `fibonacci`, along with `research-v2` semantic certificates. The large proof JSON files themselves are intentionally left out of the git repository; what is committed here is the stable metadata layer needed for reproducibility and citation.

#### Table 3. Production-v1 local artifact results (commit `58bb05f`)

| Artifact | Prove Time | Verify Time | Proof Size |
|---|---:|---:|---:|
| `addition.proof.json` | 71s | 2s | 7,644,769 bytes |
| `dot_product.proof.json` | 430s | 5s | 12,835,175 bytes |
| `single_neuron.proof.json` | 390s | 4s | 11,767,989 bytes |
| `fibonacci.proof.json` | 856s | 4s | 11,137,502 bytes |

Additional semantic-certificate timings from the same bundle:

- `research_v2_step_dot_product`: `3s`
- `research_v2_trace_dot_product`: `1s`
- `research_v2_matrix_default_suite`: `4s`

These measurements were produced on an `arm64` macOS host using `rustc 1.92.0`, `cargo 1.92.0`, `STARK_PROFILE=production-v1`, and `proof_max_steps=256`. They should be interpreted as **semantic/proof-stack evidence and reproducibility evidence**, not as frontier-model performance claims.

### 5.4 Why this artifact matters

The artifact matters because it narrows the gap between theory and system design. It shows that:

1. execution traces can be proved directly,
2. semantics can be checked across multiple runtimes before proof generation,
3. portable representations such as ONNX can be tied back to the same claimed computation, and
4. reproducibility can be anchored in concrete committed artifacts rather than narrative description alone.

---

## 6. Infrastructure Context: S-two and Starknet

The infrastructure argument is stronger now than it was a year ago.

### 6.1 S-two is no longer merely prospective

StarkWare’s public materials position S-two as its next-generation prover, fully open source and built around Circle STARKs over M31. The March 31, 2026 recursion update is particularly relevant to verifiable AI because proof aggregation is not optional once workloads become large or modular. If one wants many local proofs, batched proofs, or compressed proofs that can be checked cheaply onchain, recursion is the mechanism that keeps the system practical.

For this paper, however, the key distinction is: **S-two’s progress strengthens the architectural roadmap, but the repository analyzed here has not yet integrated an S-two backend.**

### 6.2 Starknet proof verification and privacy

Starknet’s public release materials for version `0.14.2` describe in-protocol S-two proof verification, allowing transactions to reference offchain execution proofs ([Starknet Community Forum, March 16, 2026](https://community.starknet.io/t/0-14-2-pre-release-notes/116146); [SNIP-36](https://community.starknet.io/t/snip-36-in-protocol-proof-verification/116123)). This is highly relevant to verifiable AI because it reduces the friction of taking a locally generated proof and making it legible to onchain execution.

Separately, Starknet’s March 10, 2026 STRK20 announcement states that any ERC-20 on Starknet can now be private, with client-side proof generation and unified Cairo-based logic ([Starknet, March 10, 2026](https://www.starknet.io/blog/make-all-erc-20-tokens-private-with-strk20/)). That makes the privacy side of “private verifiable inference” materially less hypothetical than it was in earlier drafts.

### 6.3 Native account abstraction

Starknet’s account model remains strategically important: accounts are smart contracts, not externally owned accounts. For agentic or AI-mediated systems, that matters because authorization, proof handling, policy logic, and asset movement can live inside the account abstraction itself rather than being bolted on externally. This is a systems-level advantage rather than a proof-theoretic one, but it affects how easily verifiable AI can be turned into deployable onchain workflows.

---

## 7. Related Systems and Competitive Landscape

### 7.1 DeepProve as the strongest anti-overclaim counterexample

Any serious paper on this topic must treat Lagrange’s DeepProve as a strong counterexample to sweeping anti-SNARK claims. DeepProve has publicly claimed full GPT-2 inference and later Gemma-class progress. Lagrange’s engineering materials describe a system that combines sumcheck-based treatment of linear layers with custom handling of softmax and lookup-based handling of LayerNorm and GELU ([Lagrange, August 18, 2025](https://lagrange.dev/blog/deepprove-1)). This is enough to reject simplistic claims such as “transformers are intrinsically ill-suited to SNARKs.”

The right conclusion is narrower: modern SNARK systems can clearly prove transformer workloads, but they may do so with different prover-side economics, especially once recursion, field size, and lookup handling become first-order bottlenecks.

### 7.2 BitSage stwo-ml as the closest public STARK-native comparator

BitSage stwo-ml is the closest public STARK-native system to the architectural thesis of this paper. It combines GKR, sumcheck, and LogUp-style machinery on an S-two/STWO backend and reports aggressive single-block transformer benchmarks together with Starknet verification paths ([BitSage `stwo-ml` repository](https://github.com/Bitsage-Network/stwo-ml); [BitSage verifier documentation](https://github.com/Bitsage-Network/stwo-ml/blob/main/elo-cairo-verifier/README.md)). For this paper, those claims should be treated as public repo- and project-reported evidence, not as independently normalized benchmarks.

The public record should still be described carefully. Repo-reported benchmark claims, publicly surfaced onchain demos, and full transformer-roadmap claims are not the same thing. The strongest defensible wording is that BitSage is the clearest public STARK-native development signal and a serious comparator, while the maturity across components is still uneven and rapidly evolving.

### 7.3 LuminAIR and the custom-AIR path

Giza and StarkWare’s LuminAIR points to a different STARK-native design path: compile ML graphs into custom AIR components rather than primarily leaning on a transformer-VM or GKR-style substrate. That matters because it shows there is more than one way to capitalize on the same architectural hypothesis. The contest is not just SNARK vs STARK; it is also **which STARK-native systems architecture best absorbs ML workloads**.

### 7.4 A more defensible comparative claim

The most defensible comparative claim is therefore:

> Once large linear algebra is handled efficiently on both sides, the remaining contest is dominated by lookup handling, transparent recursion, field arithmetic, and commitment backend. On those axes, STARK-native stacks remain highly compelling.

That is a stronger academic posture than “STARKs have already won.” It is narrower, better supported, and harder to dismiss. `docs/paper/appendix-system-comparison.md` summarizes this three-way comparison against DeepProve, BitSage stwo-ml, and this repository artifact.

---

## 8. Discussion and Engineering Next Steps

### 8.1 What this paper now supports

After tightening the arithmetic and aligning the implementation claims with the repository, the paper supports the following:

- a transformer-specific analytic argument for why STARK-native systems may enjoy structural prover-side advantages,
- a concrete semantics-and-proof artifact showing that transformer-shaped execution traces can already serve as AIR witnesses, and
- a live infrastructure roadmap in which S-two recursion, Starknet proof verification, and privacy tooling make the direction increasingly practical.

### 8.2 What it does not yet support

It does not yet support any of the following stronger claims:

- that STARKs have conclusively beaten SNARKs for transformer proving,
- that the repository proves full standard-softmax transformer inference end-to-end,
- that the repository is already an S-two-based zkML system,
- that the benchmark bundle is evidence of production-scale LLM proving.

### 8.3 Highest-leverage repository milestone

If the goal is to make the paper materially stronger with one next technical milestone, the highest-leverage move is:

1. add an S-two/STWO backend alongside the current vanilla backend, and
2. prove one lookup-backed nonlinearity path on that backend.

That combination would connect the paper’s strongest analytical claim to the strongest missing implementation piece. The corresponding repository migration plan is captured in `docs/design/stwo-backend-design.md`.

### 8.4 Secondary milestones

The next most valuable repository advances are:

- promote `research-v2` into a stable `statement-v2` contract,
- complete full-ISA AIR coverage,
- add a fixed benchmark harness that emits machine-readable metadata in CI,
- bridge from the current VM to a tiny real learned model fragment or quantized transformer block.

---

## 9. Conclusion

This paper does not argue that SNARKs are incapable of proving transformers, nor that STARK-based systems have already won verifiable AI. It argues something more precise.

Transformer workloads expose exactly the dimensions on which STARK-native systems may compound advantages: lookup-heavy nonlinearities, transparent recursion, and fast M31-style field arithmetic. At the same time, modern SNARK systems continue to narrow the gap through custom circuits, lookup techniques, and increasingly sophisticated handling of non-polynomial functions.

The repository artifact contributes evidence at the trace-semantics layer. Execution traces can be proved directly. Semantic equivalence can be enforced across runtimes. Portable artifacts can be generated and hashed. Reproducibility can be grounded in committed benchmark metadata. That is not the end state of verifiable AI, but it is a defensible and useful piece of the path toward it.

The frontier is therefore no longer “can transformers be proved?” The frontier is: **which proving architecture scales most cleanly to long-context, production verifiable inference while preserving practical deployment properties such as transparency, post-quantum security, and recursive aggregation?**

---

## References

1. Eli Ben-Sasson, Iddo Bentov, Yinon Horesh, Michael Riabzev. “Scalable, transparent, and post-quantum secure computational integrity.” *IACR ePrint 2018/046*. <https://eprint.iacr.org/2018/046>
2. Eli Ben-Sasson, Iddo Bentov, Yinon Horesh, Michael Riabzev. “Fast Reed-Solomon Interactive Oracle Proofs of Proximity.” *ICALP 2018*.
3. Eli Ben-Sasson, Lior Goldberg, Swastik Kopparty, Shubhangi Saraf. “DEEP-FRI: Sampling Outside the Box Improves Soundness.” *ITCS 2020*.
4. Ulrich Haböck, Daniel Levit, Shahar Papini. “Circle STARKs.” *IACR ePrint 2024/278*. <https://eprint.iacr.org/2024/278>
5. Jens Groth. “On the Size of Pairing-Based Non-interactive Arguments.” *EUROCRYPT 2016*.
6. Ariel Gabizon, Zachary J. Williamson, Oana Ciobotaru. “PLONK: Permutations over Lagrange-bases for Oecumenical Noninteractive Arguments of Knowledge.” *IACR ePrint 2019/953*. <https://eprint.iacr.org/2019/953>
7. Shafi Goldwasser, Yael Tauman Kalai, Guy N. Rothblum. “Delegating Computation: Interactive Proofs for Muggles.” *Journal of the ACM* 62(4), 2015.
8. Ulrich Haböck. “Multivariate lookups based on logarithmic derivatives.” *IACR ePrint 2022/1530*. <https://eprint.iacr.org/2022/1530>
9. Tianxiang Liu, Xiang Xie, Yupeng Zhang. “zkCNN: Zero Knowledge Proofs for Convolutional Neural Network Predictions and Accuracy.” *ACM CCS 2021*.
10. Haotian Sun, Jiaheng Li, Haichao Zhang. “zkLLM: Zero Knowledge Proofs for Large Language Models.” *arXiv:2404.16109*. <https://arxiv.org/abs/2404.16109>
11. Daniel Balbás, Dario Fiore, et al. “Modular Sumcheck Proofs with Applications to Machine Learning and Image Processing.” *ACM CCS 2023*.
12. Ashish Vaswani, Noam Shazeer, Niki Parmar, et al. “Attention Is All You Need.” *NeurIPS 2017*.
13. Percepta Labs. “Can LLMs Be Computers?” March 2026. <https://percepta.ai/blog/can-llms-be-computers>
14. StarkWare. “Introducing S-two: The fastest prover for real-world ZK applications.” July 2025. <https://starkware.co/blog/s-two-prover/>
15. StarkWare. “StarkWare's S-two: Unlocking Efficiency with Recursive Circuit Proving.” March 31, 2026. <https://starkware.co/blog/minutes-to-seconds-efficiency-gains-with-recursive-circuit-proving/>
16. Starknet documentation. “S-two Book: Introduction.” Accessed April 4, 2026. <https://docs.starknet.io/learn/S-two-book/introduction>
17. Starknet. “Make all ERC-20 tokens private with STRK20.” March 10, 2026. <https://www.starknet.io/blog/make-all-erc-20-tokens-private-with-strk20/>
18. Starknet. “Version releases.” Accessed April 4, 2026. <https://www.starknet.io/developers/version-releases/>
19. Lagrange. “DeepProve-1.” Accessed April 4, 2026. <https://www.lagrange.dev/blog/deepprove-1>
20. BitSage Network. “stwo-ml.” <https://github.com/Bitsage-Network/stwo-ml>
21. StarkWare. “Giza x S-two: Powering verifiable ML with LuminAIR.” <https://starkware.co/blog/giza-x-s-two-powering-verifiable-ml-with-luminair/>
22. EZKL documentation. <https://docs.ezkl.xyz>
23. `omarespejel/llm-provable-computer`. Repository snapshot analyzed in the paper discussion (commit `ad7982912cbbc709df85a446564c83dfd568e657`). <https://github.com/omarespejel/llm-provable-computer/tree/ad7982912cbbc709df85a446564c83dfd568e657>
24. `omarespejel/llm-provable-computer`. “Appendix Artifact Index (Production V1).” Repository artifact index committed in the paper artifact pass (commit `8d435d540b8e3cf33ec4381bb820a00b6fe7aae6`), documenting a bundle generated from execution/proof commit `58bb05fdd57ee9816e5935eb004396fea6a9fac3`. <https://github.com/omarespejel/llm-provable-computer/blob/8d435d540b8e3cf33ec4381bb820a00b6fe7aae6/docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md>
25. Starknet documentation. “Accounts.” Accessed April 4, 2026. <https://docs.starknet.io/architecture/accounts>
