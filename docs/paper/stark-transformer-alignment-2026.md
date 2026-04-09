# On the Structural Fit of Transformer Workloads and STARK Proof Systems

**Omar Espejel**  
Starknet Foundation  
April 2026

---

## Abstract

This paper gives a transformer-specific symbolic cost comparison between SNARK constraints and STARK trace rows for verifiable inference. Under the worked constants used throughout (`C_exp = 300`, `C_norm = 30`, `C_nonlin = 150`), GPT-2 small (`d = 768`, `T = 1024`, `H = 12`, `L = 12`) yields about `157.8B` symbolic SNARK constraints versus `106.5B` symbolic STARK rows across 12 layers (`1.48x`). Over practical context ranges, the ratio rises and then approaches a finite architecture-dependent ceiling.

We pair that analysis with a repository artifact, `provable-transformer-vm`, that now includes a frozen baseline tier, a frozen narrow experimental `stwo` tier, and a broader commit-pinned parameterized proof-carrying decoding path (`decoding_step_v2`) with carried-state commitments [30]. This paper does not claim full standard-softmax inference on S-two, shared-table accumulation, or recursive compression. The claim is narrower: transformer workloads emphasize dimensions where STARK-native systems may compound advantages while SNARK systems remain strong competitors.

---

## 1. Introduction

Verifiable inference matters because model outputs are operational inputs. Where outputs trigger trades or onchain actions, computational integrity is the core requirement.

The ecosystem already shows feasibility: modern systems can prove substantial inference workloads, and public materials report progress on both SNARK-heavy and STARK-native paths [13, 24, 25, 26, 28, 29, 33].

The question addressed here is therefore narrower and more useful than “can transformers be proved?” The question is: **which proof architecture compounds most cleanly as transformer workloads scale in model size, sequence length, and deployment complexity?**

This paper makes three claims:

1. **Analytic claim.** Under a stated transformer cost model, non-arithmetic operations such as softmax, LayerNorm, and GELU can shift prover economics in favor of STARK-native systems.
2. **Systems claim.** Deterministic execution of transformer-relevant programs can be compiled into traces that are directly consumable as AIR witnesses, and can be organized as a parameterized proof-carrying decoding relation with carried-state boundaries that survive chain, segment, rollup, and multi-layout matrix packaging.
3. **Infrastructure claim.** The S-two / Starknet stack makes this direction increasingly practical, even though the reference repository used here still relies on the vanilla backend for its default artifact bundle and primary transformer proof relation, while exposing `stwo` through a frozen narrow evidence tier and a broader experimental carried-state path.

The systems claim is directly artifact-backed. The analytic claim is model-based, not a matched benchmark on identical hardware. The infrastructure claim is supported by current public releases but extends beyond current repository breadth. This is an architecture-and-systems thesis, not a final empirical verdict.

The contributions are threefold: an exact symbolic model separating arithmetic from non-arithmetic work, a semantics-hardened artifact with parameterized proof-carrying decoding over explicit carried-state boundaries, and an infrastructure read of current S-two/Starknet signals without overclaiming present implementation maturity.

The rest of the paper follows that structure: Section 4 develops the analytic model, Section 5 anchors the systems claim in artifacts, and Sections 6-8 place those results in current infrastructure and future-work context.

---

## 2. Background

### 2.1 STARKs, AIR, and Circle STARKs

STARKs arithmetize computation as execution traces with low-degree transition constraints and FRI-style proximity testing [1, 2, 3, 4].

Circle STARKs specialize this direction to Mersenne-31 (`2^31 - 1`). StarkWare positions S-two for recursion and Starknet integration [17, 18, 20], with a March 31, 2026 update reporting verification-path reduction from roughly one minute to roughly three seconds [19]. These are engineering/product claims, not archival benchmark results.

### 2.2 SNARKs, GKR, and modern zkML

Modern zkML systems combine multiple techniques: GKR/sumcheck for large linear algebra, and lookups/custom circuits for non-polynomial functions [5, 6, 7, 10, 11]. The practical comparison is therefore whole-system architecture, not “R1CS vs AIR” in isolation.

The model below does **not** claim all SNARK stacks pay one naive non-arithmetic cost; it uses representative constants to isolate sensitivity to non-arithmetic handling.

### 2.3 LogUp and lookup-heavy workloads

Lookup arguments are central because transformer bottlenecks include non-polynomial components (softmax, LayerNorm, GELU), not only matrix multiplies [8, 10, 38, 39].

---

## 3. Transformer Operation Count

We consider a standard transformer block with model dimension `d`, sequence length `T`, number of heads `H`, head dimension `d_k = d / H`, and feedforward expansion `4d` [12].

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

The `8Td^2` feedforward term is the GPT-2-style dense-MLP case (`4d` expansion); Section 4.5 switches to the Gemma/GeGLU-style form `3Tdm`.

---

## 4. A Transformer-Specific Cost Model

This section is a **model-based** comparison of symbolic proving work, not a controlled benchmark of complete production systems. SNARK constraints and STARK rows are treated as symbolic proxies, not equal runtime units.

### 4.1 SNARK-side symbolic cost

Using stylized worked-example constants for non-arithmetic operations,

- `C_exp = 300`
- `C_norm = 30`
- `C_nonlin = 150`

we model the per-layer SNARK-side cost as:

```text
C_SNARK = 12Td^2 + 2T^2d + 2Td + T^2H * C_exp + 2Td * C_norm + 4Td * C_nonlin
```

This keeps the arithmetic term shared with the STARK side and makes explicit where the non-arithmetic amplification enters.

The constants `C_exp`, `C_norm`, and `C_nonlin` are **stylized worked-example constants**, not normalized measurements from one prover/hardware stack. Their role is to expose sensitivity; Appendix B sweeps `C_exp` across `50, 100, 300, 500`.

The model isolates softmax-related non-arithmetic cost; backend-specific lowerings are not modeled separately.

Because softmax dominates the non-arithmetic budget in this model, `C_exp` is the highest-leverage constant. On the GPT-2-small instantiation, moving `C_exp` from `50` to `500` changes the overall ratio from about `1.13x` to `1.77x`, while comparable sweeps over `C_norm` and `C_nonlin` move it only modestly. Full sensitivities are in Appendix B; this is a model stress test, not a deployed benchmark.

### 4.2 STARK-side symbolic cost

For the STARK side, we keep the exact expression:

```text
L_STARK = 12Td^2 + 2T^2d + T^2H + 8Td
```

A naive approximation such as `12Td^2 + 3T^2d` is not justified for GPT-2 small because `H << d` (`H = 12`, `d = 768`), which would materially inflate the STARK side.

This lookup treatment is also optimistic: real lookup-backed implementations pay overhead in auxiliary columns, interaction phases, and commitments. The one-row-per-symbolic-lookup abstraction is a modeling choice; higher lookup overhead would narrow the symbolic gap.

**Proposition 1.** Under the symbolic model of Sections 4.1 and 4.2, with `T, d, H > 0` and `C_exp, C_norm, C_nonlin >= 1`,

```text
C_SNARK - L_STARK = T^2H(C_exp - 1) + 2Td(C_norm - 1) + 4Td(C_nonlin - 1) >= 0.
```

Equality holds only when `C_exp = C_norm = C_nonlin = 1`. For fixed `d`, `H`, and constants with at least one strict inequality, the gap grows monotonically in `T`.

Rearranging the same expression gives the exact break-even surface:

```text
T^2H(C_exp - 1) + 2Td(C_norm - 1) + 4Td(C_nonlin - 1) = 0.
```

For fixed `C_norm` and `C_nonlin`, this yields

```text
C_exp^* = 1 - (2d / TH)[(C_norm - 1) + 2(C_nonlin - 1)].
```

If `C_norm = C_nonlin = 1`, the break-even reduces to `C_exp = 1`. On the GPT-2-small instantiation with `C_norm = 30` and `C_nonlin = 150`, the threshold is `C_exp^* = -39.875`, so no positive `C_exp` removes the modeled symbolic gap.

For the dense GPT-style case, the ratio also has a finite large-context asymptote. Writing

```text
R(T) = C_SNARK / L_STARK,
```

and keeping `d`, `H`, and the non-arithmetic constants fixed gives

```text
lim_{T -> ∞} R(T) = (2d + H C_exp) / (2d + H) = (2d_h + C_exp) / (2d_h + 1).
```

For GPT-2-small, `d_h = 64`, so under `C_exp = 300` the dense asymptote is approximately `3.32x`. The ratio rises over practical ranges and then saturates at a finite ceiling.

### 4.3 Concrete analysis: GPT-2 small

Instantiating the model with GPT-2 small parameters (`d = 768`, `T = 1024`, `H = 12`, `L = 12`) gives the following.

#### Table 2. GPT-2 small symbolic work under the stated cost model

| Component | SNARK (constraints) | STARK (trace rows) | Ratio |
|---|---:|---:|---:|
| Arithmetic | 8,859,942,912 | 8,859,942,912 | 1.00x |
| Softmax | 3,774,873,600 | 12,582,912 | 300x |
| LayerNorm | 47,185,920 | 1,572,864 | 30x |
| GELU | 471,859,200 | 3,145,728 | 150x |
| Total per layer | 13,153,861,632 | 8,877,244,416 | 1.48x |
| Total (12 layers) | 157,846,339,584 | 106,526,932,992 | 1.48x |

Under this cost model, the non-arithmetic overhead adds about `4.29B` SNARK constraints versus about `17.3M` STARK rows per layer at `T = 1024`. Softmax alone contributes about `87.9%` of the SNARK non-arithmetic overhead. Scaling the same model to `T = 4096` yields an overall ratio of about `2.13x`, so the qualitative claim that the gap widens with context length remains intact.

### 4.4 Interpretation

This analysis does **not** prove that every STARK system is faster than every SNARK system. It supports a narrower claim: once both sides handle large linear algebra efficiently, differences are increasingly driven by lookup handling, recursion, field arithmetic, and commitments.

The model also abstracts each activation/normalized value as one algebraic object; it does not model quantization layouts, packing strategies, or backend-specific decompositions.

Appendix B2 shows the same model on a wider Llama-2-7B-style dense reference [37]. Under the exact formula, a wider production-style dense model can remain near parity at shorter contexts under lower softmax constants while still widening materially at longer windows.

Recent implementation-level comparisons reinforce that boundary. A December 2025 Groth16-vs-STARK comparison on consumer ARM hardware reports faster proving and smaller proofs for the Groth16 side, alongside faster verification and transparency/post-quantum advantages for the STARK side [34].

Threats to validity concentrate in four places: quantization/packing strategy, lookup-table reuse and non-arithmetic lowering, recursion/compression strategy, and hardware parallelism.

These caveats do not remove the structural result; they bound its interpretation. In this paper, symbolic counts are used to locate architectural pressure points, not to predict wall-clock performance for any one deployed prover stack.

Figure 2 makes the symbolic-work decomposition behind that sensitivity visible for both the GPT-2-small worked example and a wider dense reference.

![Figure 2. Symbolic-work decomposition versus context for GPT-2-small and a Llama-2-7B-style dense reference.](figures/section4-decomposition-vs-context.svg)

**Figure 2.** Symbolic-work decomposition versus context. Each configuration is shown as paired SNARK and STARK stacked bars using the exact dense formulas from Sections 4.1 and 4.2. The GPT-2-small bars make the softmax-driven sensitivity of the model visually obvious, while the Llama-2-7B-style bars show the narrower short-context regime and the later widening discussed in Appendix B2.

### 4.5 Analytic extension to released Gemma 3 architectures

GPT-2-small keeps the algebra transparent, but newer deployments motivate a sparse long-context extension. Public materials report Gemma-3-class requirements including GQA, alternating local/global attention, RMSNorm, and GeGLU [14, 15, 16, 25].

This subsection asks whether the same symbolic logic still shows divergence under released sparse long-context patterns.

For Gemma-style layers, let `n_q` be query heads, `n_kv` key/value heads, `d_h` head dimension, `q = n_q d_h`, `k = n_kv d_h`, `m` MLP intermediate size, `L_g` global-attention layers, `L_l` local-attention layers, and `W_eff(T) = min(T, W)`. Using the same constants, the model becomes:

```text
A_Gemma(T) = L[Td(q + 2k) + Tdq + 3Tdm] + 2q[L_g T^2 + L_l T W_eff(T)]
S_Gemma(T) = n_q[L_g T^2 + L_l T W_eff(T)]
C_SNARK^Gemma(T) = A_Gemma(T) + S_Gemma(T) * C_exp + 2LTd * C_norm + LTm * C_nonlin
L_STARK^Gemma(T) = A_Gemma(T) + S_Gemma(T) + 2LTd + LTm
```

Gemma-style sparsity is a harder test for this thesis than GPT-2-small because local/global attention suppresses long-context cost. It tempers the gap but does not erase the direction: as context grows, non-arithmetic share remains structurally important.

With fixed local window `W` and nonzero global-layer fraction, the long-context ratio remains finite. In the representative `5:1` schedule used in Figure 1, the ratio still rises toward a finite ceiling.

**Corollary.** For a fixed positive global-attention fraction and fixed local window `W`, the representative sparse long-context ratio has the same large-context ceiling as the dense case:

```text
lim_{T -> ∞} R_sparse(T) = (2d_h + C_exp) / (2d_h + 1).
```

The local `T W_eff(T)` terms are lower order than global `T^2` terms at large `T`, so sparsity delays the approach to the ceiling rather than lowering it.

Figure 1 visualizes that distinction. The dense curve uses the GPT-2-small model from Sections 4.1-4.3, and the sparse curve is a representative Gemma-style `5:1` local/global schedule with `W = 1024` under the same constants.

![Figure 1. SNARK/STARK symbolic ratio versus context length for a dense GPT-style model and a representative 5:1 local/global sparse schedule.](figures/section4-ratio-vs-context.svg)

**Figure 1.** `SNARK/STARK` symbolic ratio versus context length. The sparse curve is representative, not tied to one exact checkpoint. The dashed line is the dense asymptotic ceiling from Section 4.2. Reproducibility metadata and exact point generation details are recorded in the supplementary scaling appendix and committed figure script/TSV.

With the analytic behavior established, we now turn to what the repository currently demonstrates and where the bridge to recursive accumulation begins.

---

## 5. Repository Artifact: From Trace-as-Witness to Parameterized Proof-Carrying Decoding

The implementation artifact is `omarespejel/provable-transformer-vm` [30]. In this paper it is treated as a **semantics-and-proof artifact**: deterministic transformer-relevant execution is compiled into AIR-consumable traces and packaged into carried-state proof objects for later recursion/accumulation work. Earlier phases of this line were developed under the `llm-provable-computer` project name.

### 5.1 What the repository demonstrates today

The snapshot provides:

- a deterministic transformer-shaped VM and statement-versioned claim (`statement-v1`),
- semantic lockstep/multi-engine agreement checks with ONNX validation,
- two frozen evidence tiers: `production-v1` (vanilla) and `stwo-experimental-v1` (narrow experimental),
- a parameterized proof-carrying decoding family (`decoding_step_v2`) over multiple public layouts,
- carried-state packaging (chain, segment, rollup, multi-layout matrix) with KV/lookup cumulative and frontier commitments,
- a verification-hardening stack: oracle/differential checks, fuzz smoke targets, mutation tests, Miri/ASAN, and bounded Kani contracts.

This supports a stronger systems statement than earlier drafts: the same decode relation survives progressively more composable manifest layers without changing statement boundaries.

### 5.2 What the repository does **not** yet demonstrate

The repository remains deliberately narrow:

- default reproducibility and primary transformer relation still use the vanilla backend,
- the experimental `stwo` path is bounded research scope, not broad production zkML scope,
- attention is currently `average-hard`, not full standard softmax,
- shared-table lookup state is carried but not yet accumulated/compressed across decode steps,
- recursive aggregation/compression is not yet public,
- learned-model end-to-end LLM proving, zero-knowledge hiding, and full-ISA AIR coverage remain out of scope.

These limits are intentional scope discipline: the artifact supports structural systems and pre-recursive carried-state claims, but not full softmax-plus-recursion closure.

### 5.3 Frozen reproducibility bundle

On April 4, 2026, we generated `production-v1` from execution/proof commit `58bb05f` and documented it in immutable artifact snapshot `8d435d5` with command logs, hashes, and proof artifacts [31]. Timings/sizes are kept in the artifact appendix as reproducibility evidence, not performance evidence.

### 5.4 Frozen experimental S-two tier and post-freeze bridge artifacts

On April 6, 2026, we generated `stwo-experimental-v1` (artifact-index commit `3970277`) with representative arithmetic, lookup-envelope, transformer-shaped, and decoding-chain artifacts [40]. This complements rather than replaces `production-v1`.

The `stwo-experimental-v1` bundle is dated April 6, 2026, and its frozen artifact index was generated on April 7, 2026 (UTC) in immutable repository snapshot commit `3970277`, with exact command logs, wall-clock timings, SHA-256 hashes, and proof artifacts for four representative outputs: an arithmetic `statement-v1` execution proof (`addition`), a shared-table normalization lookup proof envelope, a Gemma-inspired fixed-shape execution proof (`gemma_block_v4`) with embedded shared lookup bindings, and a three-step proof-carrying decoding chain over explicit carried-state commitments. This frozen `stwo-experimental-v1` bundle intentionally complements the vanilla `production-v1` bundle rather than replacing it [40]. Appendix C1 summarizes the two frozen backend-facing tiers in one compact comparison table.

Beyond that frozen tier, the same line carries the broader bridge artifact: parameterized `decoding_step_v2` proofs over multiple layouts, then carried-state packaging through chains, segments, rollups, multi-layout matrices, and lookup/KV frontier commitments. These are commit-pinned systems evidence for pre-recursive merge boundaries, not recursive compression evidence, and they do not yet implement cross-step shared-table accumulation [30, 40].

### 5.5 Why this artifact matters

This artifact narrows the gap between analytic and systems claims by showing:

1. transformer-relevant traces can be proved directly,
2. semantic equivalence can be checked across runtimes before proving,
3. one parameterized decode relation preserves carried state across layouts and packaging layers,
4. reproducibility can be anchored in immutable bundles and commit-pinned post-freeze artifacts.

---

## 6. Infrastructure Context: S-two and Starknet

The infrastructure argument is stronger than one year ago.

### 6.1 S-two is no longer merely prospective

StarkWare’s public materials position S-two as a next-generation open-source prover around Circle STARKs over M31. The March 31, 2026 recursion update matters because aggregation is required once workloads become large or modular [19].

For this paper, the key distinction is: **S-two progress strengthens the roadmap, while the repository still keeps its default artifact bundle and primary transformer relation on the vanilla backend.**

Verifier cost and proof size remain part of that roadmap. The frozen vanilla tier still produces multi-megabyte proofs for tiny fixtures, so aggregation/compression remains necessary for practical onchain use [19, 34].

The repository nevertheless exposes meaningful S-two evidence through a frozen experimental tier and a broader carried-state experimental path, which is why the paper frames the current stage as a bridge rather than a finished recursion system.

### 6.2 Starknet proof verification and privacy

Starknet `0.14.2` public materials list in-protocol S-two verification, and `SNIP-36` describes proof-carrying transaction structure (`proof_facts`) [22, 23]. Starknet’s account model remains relevant to this integration boundary [32]. Starknet’s March 10, 2026 STRK20 announcement adds privacy relevance by stating any ERC-20 on Starknet can now be private [21].

---

## 7. Related Systems and Competitive Landscape

### 7.1 DeepProve as a strong SNARK counterexample

DeepProve is a direct counterexample to sweeping anti-SNARK claims: public Lagrange materials report full GPT-2 inference and later Gemma-class progress with specialized non-arithmetic handling [24, 25]. The relevant conclusion is narrower: SNARK systems can prove transformer workloads, but with different prover-side economics.

### 7.2 Jolt Atlas and lookup-native SNARK convergence

Jolt Atlas reaches a lookup-centric architecture from the SNARK side, extending Jolt to ONNX tensor operations and emphasizing non-linear workload handling [38]. The main relevance is convergence around lookup-heavy non-arithmetic handling.
Related SNARK-side lines such as zkCNN and zkPyTorch reinforce that non-arithmetic handling remains a central systems concern even when benchmark setups differ [9, 35, 36].

### 7.3 NANOZK and zkLLM on layerwise and attention-specific specialization

NANOZK and zkLLM reinforce the same trend: layerwise decomposition and attention/nonlinearity specialization with lookup-heavy machinery [10, 39]. Here they are architectural evidence, not matched benchmarks.

### 7.4 BitSage stwo-ml as the closest public STARK-native comparator

BitSage stwo-ml is the closest public STARK-native comparator. Public materials show GKR/sumcheck/LogUp-style machinery on an S-two/STWO path with Starknet verification paths [26, 27]. These remain project-reported evidence, not normalized benchmarks.

### 7.5 LuminAIR and the custom-AIR path

LuminAIR shows a different STARK-native path: custom AIR compilation for computational graphs rather than a transformer-VM-first substrate [28, 29]. The contest is therefore also between STARK-native architectures.

### 7.6 A more defensible comparative claim

The most defensible comparative claim is therefore:

> Once large linear algebra is handled efficiently on both sides, the remaining contest is dominated by lookup handling, transparent recursion, field arithmetic, and commitment backend. On those axes, STARK-native stacks remain highly compelling.

This is stronger than “STARKs have already won” because it is narrower and better evidenced. A supplementary appendix summarizes comparison details.

Against that external landscape, the remaining question is practical sequencing: which engineering steps most directly strengthen the next paper without diluting scope discipline.

---

## 8. Discussion and Engineering Next Steps

### 8.1 What the paper supports, and what it does not

Taken together, the paper supports: a transformer-specific symbolic argument, a concrete semantics-and-proof artifact with parameterized carried-state decoding, and a live infrastructure roadmap.

It does **not** support stronger claims such as “STARKs have conclusively beaten SNARKs,” full standard-softmax end-to-end inference in this repository, or production-scale LLM proving evidence.

### 8.2 Highest-leverage repository milestones from this unified baseline

With the parameterized decoding bridge present, the next highest-leverage milestone is **carry-state compression and accumulation**.

Concretely, the strongest next move is to keep the same decode relation and statement discipline while adding:

- shared-table accumulation across decode steps for lookup-side state,
- recursive aggregation/compression over segment/rollup/matrix boundaries,
- one more faithful non-arithmetic attention path on the experimental `stwo` route.

This connects the current analytic bottleneck (lookup-heavy non-arithmetic pressure) to the next systems bottleneck (proof-size/verifier-cost compression).

Methodologically, this sequencing matters: it keeps the statement boundary fixed while changing only how repeated steps are carried and compressed. That makes each empirical gain attributable to accumulation/recursion decisions rather than to a moving execution relation.

The next supporting engineering moves remain:

- complete full-ISA AIR coverage,
- keep artifact generation and benchmark metadata machine-readable in CI,
- add a minimal learned-model fragment or quantized transformer block only once the accumulation path is stable.

### 8.3 Future work that would materially strengthen the next paper

The next-paper opportunity is narrower and more technical: transformer-specific accumulation, not another broad STARK-vs-SNARK framing.

Recent folding literature already covers generalized recursive arguments and CCS/AIR-compatible folding abstractions [41, 43, 44, 45]. Newer small-field and post-quantum folding directions further reduce the novelty space for generic claims [41]. Therefore, the strongest defensible future contribution is:

1. keep one fixed transformer-block relation and one decode transition relation,
2. accumulate repeated block/step instances with shared lookup tables,
3. preserve explicit KV/lookup boundary commitments under that accumulation,
4. measure flat vs carried vs accumulated modes on the same artifact family.

A second high-value track is trust-core assurance: maintain differential/oracle tests, fuzzing, and bounded model-checking around carried-state verifier kernels, then selectively formalize the smallest trust-critical binding layer [42].

This future-work split is deliberate. One track expands capability (accumulation/compression); the other reduces trust risk (verification-kernel assurance). Keeping them explicit helps avoid the common failure mode of adding feature breadth without maintaining explicit proof-binding guarantees.

---

## 9. Conclusion

This paper does not argue that SNARKs cannot prove transformers or that STARKs have already won. It argues a narrower point: transformer workloads emphasize lookup-heavy nonlinearities, recursion, and field/commitment design choices where STARK-native systems may compound advantages.

The repository contributes evidence at two layers: trace semantics and pre-recursive carried state. It shows direct proving of transformer-relevant traces, semantic checks across runtimes, and a parameterized decode relation that preserves commitments across chains, segments, rollups, and layout matrices.

The frontier is no longer “can transformers be proved?” It is: **which architecture scales most cleanly to long-context, production verifiable inference while preserving transparency/post-quantum properties and compressing repeated transformer structure without losing semantic discipline?**

---

## Acknowledgments

This paper uses the maintained repository `omarespejel/provable-transformer-vm`, which builds directly on Abdelhamid Bakhta’s upstream public repository `AbdelStark/llm-provable-computer` and earlier project phases developed under the `llm-provable-computer` name.

---

## References

1. Eli Ben-Sasson, Iddo Bentov, Yinon Horesh, and Michael Riabzev. “Scalable, Transparent, and Post-Quantum Secure Computational Integrity.” *IACR Cryptology ePrint Archive*, Paper 2018/046, 2018. <https://eprint.iacr.org/2018/046>
2. Eli Ben-Sasson, Iddo Bentov, Yinon Horesh, and Michael Riabzev. “Fast Reed-Solomon Interactive Oracle Proofs of Proximity.” In *Proceedings of the 45th International Colloquium on Automata, Languages, and Programming (ICALP)*, 2018.
3. Eli Ben-Sasson, Lior Goldberg, Swastik Kopparty, and Shubhangi Saraf. “DEEP-FRI: Sampling Outside the Box Improves Soundness.” In *Proceedings of the 11th Innovations in Theoretical Computer Science Conference (ITCS)*, 2020.
4. Ulrich Haböck, David Levit, and Shahar Papini. “Circle STARKs.” *IACR Cryptology ePrint Archive*, Paper 2024/278, 2024. <https://eprint.iacr.org/2024/278>
5. Jens Groth. “On the Size of Pairing-Based Non-interactive Arguments.” In *Advances in Cryptology - EUROCRYPT 2016*, 2016.
6. Ariel Gabizon, Zachary J. Williamson, and Oana Ciobotaru. “PLONK: Permutations over Lagrange-bases for Oecumenical Noninteractive Arguments of Knowledge.” *IACR Cryptology ePrint Archive*, Paper 2019/953, 2019. <https://eprint.iacr.org/2019/953>
7. Shafi Goldwasser, Yael Tauman Kalai, and Guy N. Rothblum. “Delegating Computation: Interactive Proofs for Muggles.” *Journal of the ACM* 62(4), 2015.
8. Ulrich Haböck. “Multivariate Lookups Based on Logarithmic Derivatives.” *IACR Cryptology ePrint Archive*, Paper 2022/1530, 2022. <https://eprint.iacr.org/2022/1530>
9. Tianxiang Liu, Xiang Xie, and Yupeng Zhang. “zkCNN: Zero Knowledge Proofs for Convolutional Neural Network Predictions and Accuracy.” In *Proceedings of the 2021 ACM SIGSAC Conference on Computer and Communications Security (CCS)*, 2021.
10. Haochen Sun, Jason Li, and Hongyang Zhang. “zkLLM: Zero Knowledge Proofs for Large Language Models.” *arXiv preprint* arXiv:2404.16109, 2024. <https://arxiv.org/abs/2404.16109>
11. Daniel Balbás, Dario Fiore, et al. “Modular Sumcheck Proofs with Applications to Machine Learning and Image Processing.” In *Proceedings of the 2023 ACM SIGSAC Conference on Computer and Communications Security (CCS)*, 2023.
12. Ashish Vaswani, Noam Shazeer, Niki Parmar, et al. “Attention Is All You Need.” In *Advances in Neural Information Processing Systems 30 (NeurIPS)*, 2017.
13. Percepta Labs. “Can LLMs Be Computers?” *Percepta Blog*, March 2026. <https://percepta.ai/blog/can-llms-be-computers>
14. Gemma Team. “Gemma 3 Technical Report.” Technical report, March 25, 2025. <https://storage.googleapis.com/deepmind-media/gemma/Gemma3Report.pdf>
15. Google AI for Developers. “Gemma 3 Model Card.” Official model documentation. Accessed April 6, 2026. <https://ai.google.dev/gemma/docs/core/model_card_3>
16. Google Developers Blog. “Gemma explained: An overview of Gemma model family architectures.” August 15, 2024. <https://developers.googleblog.com/en/gemma-explained-overview-gemma-model-family-architectures/>
17. StarkWare. “Introducing S-two: The Fastest Prover for Real-world ZK Applications.” *StarkWare Blog*, May 26, 2025. <https://starkware.co/blog/s-two-prover/>
18. StarkWare. “S-two 2.0.0 Is a Developer-Friendly, Fully Open-Source Toolkit.” *StarkWare Blog*, January 27, 2026. <https://starkware.co/blog/s-two-2-0-0-prover-for-developers/>
19. StarkWare. “Minutes to Seconds: Efficiency Gains with Recursive Circuit Proving.” *StarkWare Blog*, March 31, 2026. <https://starkware.co/blog/minutes-to-seconds-efficiency-gains-with-recursive-circuit-proving/>
20. Starknet Docs. “S-two Book: Introduction.” *Starknet Documentation*. Accessed April 5, 2026. <https://docs.starknet.io/learn/S-two-book/introduction>
21. Starknet. “Make All ERC-20 Tokens Private with STRK20.” *Starknet Blog*, March 10, 2026. <https://www.starknet.io/blog/make-all-erc-20-tokens-private-with-strk20/>
22. Starknet. “Version Releases.” *Starknet Documentation*. Accessed April 5, 2026. <https://www.starknet.io/developers/version-releases/>
23. Starknet Community Forum. “SNIP-36: In-protocol Proof Verification.” Specification discussion. Accessed April 5, 2026. <https://community.starknet.io/t/snip-36-in-protocol-proof-verification/116123>
24. Lagrange. “DeepProve-1.” *Lagrange Blog*, August 18, 2025. <https://www.lagrange.dev/blog/deepprove-1>
25. Lagrange. “Engineering Update: September 2025.” *Lagrange Engineering Update*, published October 20, 2025. <https://www.lagrange.dev/engineering-updates/september-2025>
26. BitSage Network. *stwo-ml*. GitHub repository. Accessed April 5, 2026. <https://github.com/Bitsage-Network/stwo-ml>
27. BitSage Network. “elo-cairo-verifier/README.md.” GitHub documentation file. Accessed April 5, 2026. <https://github.com/Bitsage-Network/stwo-ml/blob/main/elo-cairo-verifier/README.md>
28. Giza. *LuminAIR*. GitHub repository. Accessed April 5, 2026. <https://github.com/gizatechxyz/LuminAIR>
29. StarkWare. “Giza x S-two: Powering Verifiable ML with LuminAIR.” *StarkWare Blog*. Accessed April 5, 2026. <https://starkware.co/blog/giza-x-s-two-powering-verifiable-ml-with-luminair/>
30. `omarespejel/provable-transformer-vm`. “Repository Snapshot Discussed in Sections 5 and 8.” GitHub repository snapshot, release tag `paper-publication-v3-2026-04-09`. <https://github.com/omarespejel/provable-transformer-vm/tree/paper-publication-v3-2026-04-09>
31. `omarespejel/provable-transformer-vm`. “Appendix Artifact Index (Production V1).” GitHub artifact snapshot, commit `8d435d540b8e3cf33ec4381bb820a00b6fe7aae6`, documenting a bundle generated from execution/proof commit `58bb05fdd57ee9816e5935eb004396fea6a9fac3`. <https://github.com/omarespejel/provable-transformer-vm/blob/8d435d540b8e3cf33ec4381bb820a00b6fe7aae6/docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md>
32. Starknet Docs. “Accounts.” *Starknet Documentation*. Accessed April 5, 2026. <https://docs.starknet.io/architecture/accounts>
33. Zhizhi Peng, Chonghe Zhao, Taotao Wang, Guofu Liao, Zibin Lin, Yifeng Liu, Bin Cao, Long Shi, Qing Yang, and Shengli Zhang. “A Survey of Zero-Knowledge Proof-Based Verifiable Machine Learning.” *Artificial Intelligence Review* (accepted manuscript), arXiv:2502.18535v2, 2026. <https://arxiv.org/abs/2502.18535>
34. Ayush Nainwal, Atharva Kamble, and Nitin Awathare. “A Comparative Analysis of zk-SNARKs and zk-STARKs: Theory and Practice.” *arXiv preprint* arXiv:2512.10020, 2025. <https://arxiv.org/abs/2512.10020>
35. Jiajun Wang, Xiaowen Wang, Zekun Wen, Linyan Lyu, Wei Wang, Yuxin Wang, Yanjiang Yang, Jian Liu, Jiaheng Zhang, Chao Li, and Qianhui Wang. “zkPyTorch: Verifiable Training and Inference with Zero-Knowledge Proofs.” *IACR Cryptology ePrint Archive*, Paper 2025/535, 2025. <https://eprint.iacr.org/2025/535>
36. Polyhedra Network. “zkPyTorch.” *Polyhedra Product Page*. Accessed April 6, 2026. <https://polyhedra.network/zkPyTorch>
37. Hugo Touvron, Louis Martin, Kevin Stone, et al. “Llama 2: Open Foundation and Fine-Tuned Chat Models.” *arXiv preprint* arXiv:2307.09288, 2023. <https://arxiv.org/abs/2307.09288>
38. Wyatt Benno, Alberto Centelles, Antoine Douchet, and Khalil Gibran. “Jolt Atlas: Verifiable Inference via Lookup Arguments in Zero Knowledge.” *arXiv preprint* arXiv:2602.17452, 2026. <https://arxiv.org/abs/2602.17452>
39. Zhaohui Geoffrey Wang. “NANOZK: Layerwise Zero-Knowledge Proofs for Verifiable Large Language Model Inference.” *arXiv preprint* arXiv:2603.18046, 2026. <https://arxiv.org/abs/2603.18046>
40. `omarespejel/provable-transformer-vm`. “Appendix Artifact Index (S-two Experimental V1).” GitHub artifact snapshot, commit `3970277d964a0a9a5326b0db364cf16822c1ccd4`, at `docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md`. <https://github.com/omarespejel/provable-transformer-vm/blob/3970277d964a0a9a5326b0db364cf16822c1ccd4/docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md>
41. Wilson Nguyen and Srinath Setty. “Neo: Lattice-based folding scheme for CCS over small fields and pay-per-bit commitments.” *IACR Cryptology ePrint Archive*, Paper 2025/294, 2025. <https://eprint.iacr.org/2025/294>
42. StarkWare. “How StarkWare Uses Formal Verification to Prove Tech Soundness.” *StarkWare Blog*, March 5, 2026. <https://starkware.co/blog/starkwares-gold-standard-of-soundness-with-formal-verification/>
43. Abhiram Kothapalli and Srinath Setty. “HyperNova: Recursive Arguments for Customizable Constraint Systems.” *IACR Cryptology ePrint Archive*, Paper 2023/573, 2023. <https://eprint.iacr.org/2023/573>
44. Abhiram Kothapalli and Srinath Setty. “NeutronNova: Folding Everything that Reduces to Zero-Check.” *IACR Cryptology ePrint Archive*, Paper 2024/1606, 2024. <https://eprint.iacr.org/2024/1606>
45. Abhiram Kothapalli and Srinath Setty. “ProtoStar: Generic Efficient Accumulation/Folding for Special Sound Protocols.” *IACR Cryptology ePrint Archive*, Paper 2023/620, 2023. <https://eprint.iacr.org/2023/620>
