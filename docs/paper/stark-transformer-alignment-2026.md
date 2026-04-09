# On the Structural Fit of Transformer Workloads and STARK Proof Systems

**Omar Espejel**  
Starknet Foundation  
April 2026

---

## Abstract

This paper presents a transformer-specific symbolic complexity analysis comparing SNARK circuit size and STARK trace length for verifiable inference. Arithmetic work in a standard transformer block maps similarly in both settings, but non-arithmetic primitives such as softmax, normalization, and activation functions stress the two proving families differently. Under the stylized worked-example constants used throughout this paper (`C_exp = 300`, `C_norm = 30`, `C_nonlin = 150`), GPT-2 small (`d = 768`, `T = 1024`, `H = 12`, `L = 12`) yields approximately `157.8B` symbolic SNARK constraints versus `106.5B` symbolic STARK trace rows across 12 layers, or about `1.48x` more symbolic proving work on the SNARK side under these assumptions. Over the practically relevant range studied here, the ratio rises with sequence length before approaching a finite architecture-dependent ceiling.

We complement this analysis with a concrete proof-stack artifact, `llm-provable-computer`, in which deterministic transformer-shaped execution traces are consumable as AIR witnesses [30]. The repository now includes a frozen baseline bundle, a frozen narrow experimental `stwo` bundle, and a broader commit-pinned parameterized proof-carrying decoding path (`decoding_step_v2`) with explicit carried-state commitments. The paper does not claim full standard-softmax transformer inference on S-two, shared-table accumulation across decode steps, or recursive proof compression. The resulting claim is intentionally narrower than “STARKs beat SNARKs”: transformer workloads emphasize dimensions where STARK-native systems may compound advantages, while modern SNARK systems remain serious and rapidly improving competitors.

---

## 1. Introduction

Verifiable inference matters because model outputs are now operational inputs. If a model score can trigger a trade or authorize an onchain action, then “trust me, the model ran” is not enough. The problem is one of computational integrity, not only privacy or provenance.

The zkML ecosystem has already shown that proving neural network inference is feasible. Sumcheck-based systems have made linear layers practical; lookup-based systems have made non-polynomial steps practical enough for real workloads. Public materials from Lagrange report DeepProve progress from full GPT-2 inference toward Gemma-class systems [24, 25], and public BitSage and Giza/StarkWare materials show increasingly concrete STARK-native development [26, 28, 29]. Recent surveys place this work in the inference-and-systems slice of verifiable ML [33].

The question addressed here is therefore narrower and more useful than “can transformers be proved?” The question is: **which proof architecture compounds most cleanly as transformer workloads scale in model size, sequence length, and deployment complexity?**

This paper makes three distinct claims:

1. **Analytic claim.** Under a stated transformer cost model, non-arithmetic operations such as softmax, LayerNorm, and GELU can shift prover economics in favor of STARK-native systems.
2. **Systems claim.** Deterministic execution of transformer-relevant programs can be compiled into traces that are directly consumable as AIR witnesses, and can be organized as a parameterized proof-carrying decoding relation with carried-state boundaries that survive chain, segment, rollup, and multi-layout matrix packaging.
3. **Infrastructure claim.** The S-two / Starknet stack makes this direction increasingly practical, even though the reference repository used here still relies on the vanilla backend for its default artifact bundle and primary transformer proof relation, while exposing `stwo` through a frozen narrow evidence tier and a broader experimental carried-state path.

The repository artifact supports the second claim directly. The first claim is model-based, not a matched end-to-end benchmark on identical hardware. The third claim is partially supported by recent StarkWare and Starknet releases but still ahead of current repository breadth. The paper therefore aims to be an architecture-and-systems thesis, not a final empirical verdict on STARK versus SNARK transformer proving.

This paper contributes three concrete things: an exact transformer-specific symbolic cost model that separates arithmetic from non-arithmetic proving work, a semantics-hardened repository artifact showing both trace-as-witness proving and parameterized proof-carrying decoding over explicit carried-state boundaries, and a current infrastructure analysis connecting that artifact to public S-two and Starknet developments without overstating present implementation maturity.

---

## 2. Background

### 2.1 STARKs, AIR, and Circle STARKs

STARKs arithmetize computation as execution traces with low-degree transition constraints and reduce soundness to proximity testing via FRI-style machinery [1, 2, 3, 4]. For prover-heavy workloads, the appeal is transparent setup and post-quantum security.

Circle STARKs specialize this direction to the Mersenne-31 field (`2^31 - 1`). StarkWare positions S-two as the flagship stack for recursion and Starknet integration [17, 18, 20], including a March 31, 2026 recursion update reporting verification-path reduction from roughly one minute to roughly three seconds [19]. These are engineering/product claims, not archival benchmark results.

### 2.2 SNARKs, GKR, and modern zkML

Modern zkML systems combine multiple techniques: GKR/sumcheck for large linear algebra, and lookups/custom circuits for non-polynomial functions [5, 6, 7, 10, 11]. The practical comparison is therefore whole-system architecture, not “R1CS vs AIR” in isolation.

The model below does **not** claim all SNARK stacks pay one naive non-arithmetic cost. It uses representative constants to show how transformer workloads amplify overhead when non-arithmetic primitives are handled less natively than on lookup-centric paths.

### 2.3 LogUp and lookup-heavy workloads

Lookup arguments are central because transformer bottlenecks are not only matrix multiplies. Softmax, LayerNorm, and GELU all introduce non-polynomial structure, and LogUp-style machinery makes these operations comparatively natural in lookup-centric designs [8, 10, 38, 39].

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

The `8Td^2` feedforward term is the GPT-2-style dense-MLP case with expansion factor `4d`; Section 4.5 switches to the architecture-specific Gemma/GeGLU-style form `3Tdm` when analyzing released sparse long-context models. The key structural point is not just that these terms exist, but that they become more important precisely in the regimes that matter for modern transformers: long contexts and repeated normalization / activation over wide hidden states.

---

## 4. A Transformer-Specific Cost Model

This section is the analytic core of the paper. It should be read as a **model-based comparison of symbolic proving work**, not as a controlled head-to-head benchmark of complete production systems. Throughout this section, raw SNARK constraint counts and raw STARK trace rows are used as symbolic proxies for prover-side work under the simplifying assumption that prover cost is dominated by algebraic operations that scale approximately linearly with these objects. That is a modeling assumption, not a claim that one constraint and one trace row are identical units of runtime cost in production systems.

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

The constants `C_exp`, `C_norm`, and `C_nonlin` are **stylized worked-example constants**, not normalized measurements extracted from one production prover stack running on one fixed hardware configuration. Their role is to make the model’s sensitivity to non-arithmetic work explicit, not to claim benchmark equivalence with any single deployed system. Appendix B sweeps `C_exp` across `50, 100, 300, 500` precisely so the argument does not rest on one fixed constant choice.

The model isolates the non-arithmetic component of softmax; row-wise reductions, max-subtraction for numerical stability, and backend-specific normalization lowerings are not modeled separately and are instead absorbed into the arithmetic proxy or left to the threats-to-validity discussion.

Because softmax dominates the non-arithmetic budget in this model, `C_exp` is the highest-leverage constant. On the GPT-2-small instantiation, moving `C_exp` from `50` to `500` changes the overall ratio from about `1.13x` to `1.77x`, while comparable sweeps over `C_norm` and `C_nonlin` move it only modestly. Full sensitivities are in Appendix B; this is a model stress test, not a deployed benchmark.

### 4.2 STARK-side symbolic cost

For the STARK side, we keep the exact expression:

```text
L_STARK = 12Td^2 + 2T^2d + T^2H + 8Td
```

A naive approximation such as `12Td^2 + 3T^2d` would not be justified for GPT-2 small because `H << d`. For GPT-2 small, `H = 12` and `d = 768`, so the `T^2H` term is `64x` smaller than a `T^2d` term. The asymptotic point remains valid, but that approximation materially inflates the STARK side numerically.

This STARK-side lookup treatment is also optimistic. Real LogUp-style or lookup-backed implementations do not get non-arithmetic operations “for free”: they pay additional overhead in auxiliary trace columns, interaction phases, logarithmic-derivative machinery, and commitment work. The one-row-per-symbolic-lookup abstraction is therefore a simplifying modeling choice, just as the SNARK-side constants are. Any multiplicative overhead on those STARK-side lookup rows would narrow the symbolic gap; the present model does not attempt to calibrate that overhead empirically.

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

For GPT-2-small, `d_h = 64`, so under `C_exp = 300` the dense asymptote is approximately `3.32x`. The right interpretation is therefore not that the symbolic ratio diverges without bound, but that over the practical ranges studied here it rises as non-arithmetic work becomes a larger share of total work before saturating at a finite architecture-dependent ceiling.

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

This analysis does **not** prove that every STARK system is faster than every SNARK system on every transformer workload. It supports a narrower claim: once both sides handle large linear algebra efficiently, the remaining battleground is dominated by lookup handling, recursion, field arithmetic, and commitment backend. Transformer workloads expose these differences more sharply than many standard proving benchmarks do.

One further scope boundary matters here: the model abstracts each activation or normalized value as one algebraic object. It does **not** model int8/int4 quantization layouts, packing strategies, or backend-specific decompositions. Practical zkML systems often rely heavily on quantization, and that can change absolute constraint counts differently across SNARK and STARK systems. The present model is therefore best read as a structural comparison of symbolic work, not as a quantization-aware production estimate.

Appendix B2 shows the same model on a wider Llama-2-7B-style dense reference. Under the exact formula, a wider production-style dense model can remain near parity at shorter contexts under lower softmax constants while still widening materially at longer windows.

Recent implementation-level comparisons reinforce that point. A December 2025 Groth16-vs-STARK comparison on consumer ARM hardware reports much faster proving and smaller proofs for the Groth16 side, alongside faster verification and transparency/post-quantum advantages for the STARK side [34]. This is a boundary condition on this model: symbolic rows and constraints are not runtime measurements.

Threats to validity concentrate in four places: quantization/packing strategy, lookup-table reuse and non-arithmetic lowering, recursion/compression strategy, and hardware parallelism.

Figure 2 makes the symbolic-work decomposition behind that sensitivity visible for both the GPT-2-small worked example and a wider dense reference.

![Figure 2. Symbolic-work decomposition versus context for GPT-2-small and a Llama-2-7B-style dense reference.](figures/section4-decomposition-vs-context.svg)

**Figure 2.** Symbolic-work decomposition versus context. Each configuration is shown as paired SNARK and STARK stacked bars using the exact dense formulas from Sections 4.1 and 4.2. The GPT-2-small bars make the softmax-driven sensitivity of the model visually obvious, while the Llama-2-7B-style bars show the narrower short-context regime and the later widening discussed in Appendix B2.

### 4.5 Analytic extension to released Gemma 3 architectures

The GPT-2-small analysis is useful because it keeps the algebra transparent, but it is no longer enough on its own. Public Lagrange engineering materials report DeepProve progress on Gemma 3-class inference, and that engineering update for **September 2025**, published on **October 20, 2025**, is explicit that supporting Gemma 3 required handling grouped-query attention (GQA), alternating local/global attention, RMSNorm, GeGLU, and RoPE [25]. Official Google Gemma 3 materials describe the family as a decoder-only transformer with GQA, RMSNorm, long-context support, and a `5:1` interleaving of local and global attention layers, with the 4B, 12B, and 27B variants supporting `128K` context and the smaller variants supporting shorter windows [14, 15].

This subsection is an analytic scaling extension. It asks: if the same symbolic logic is carried to released sparse long-context architecture patterns, does the qualitative divergence persist?

For Gemma-style layers, we refine the notation from the GPT-2-style dense-attention case. Let `n_q` be the number of query heads, `n_kv` the number of key/value heads, `d_h` the head dimension, `q = n_q d_h`, `k = n_kv d_h`, `m` the MLP intermediate size, `L_g` the number of global-attention layers, `L_l` the number of local-attention layers, `W` the local sliding-window span, and `W_eff(T) = min(T, W)`. Using the same stylized worked-example constants as above, the architecture-aware symbolic model becomes:

```text
A_Gemma(T) = L[Td(q + 2k) + Tdq + 3Tdm] + 2q[L_g T^2 + L_l T W_eff(T)]
S_Gemma(T) = n_q[L_g T^2 + L_l T W_eff(T)]
C_SNARK^Gemma(T) = A_Gemma(T) + S_Gemma(T) * C_exp + 2LTd * C_norm + LTm * C_nonlin
L_STARK^Gemma(T) = A_Gemma(T) + S_Gemma(T) + 2LTd + LTm
```

Gemma-style sparsity is a harder test for this thesis than GPT-2-small because local/global attention suppresses long-context cost. It tempers the gap but does not erase the direction: as context grows, non-arithmetic share remains structurally important.

The same asymptotic logic remains useful in the sparse case. With a fixed local window `W` and a nonzero fixed fraction of global layers, the long-context ratio remains finite rather than diverging. In the representative `5:1` schedule used in Figure 1, the global-attention fraction is constant, so the ratio still rises toward a finite ceiling rather than growing without bound.

**Corollary.** For a fixed positive global-attention fraction and fixed local window `W`, the representative sparse long-context ratio has the same large-context ceiling as the dense case:

```text
lim_{T -> ∞} R_sparse(T) = (2d_h + C_exp) / (2d_h + 1).
```

The reason is that the local `T W_eff(T)` terms are lower order than the global `T^2` terms once `T` grows large, so sparsity delays the approach to the ceiling rather than lowering the ceiling itself.

Figure 1 visualizes that distinction. The dense curve uses the GPT-2-small model from Sections 4.1-4.3, and the sparse curve is a representative Gemma-style `5:1` local/global schedule with `W = 1024` under the same constants.

![Figure 1. SNARK/STARK symbolic ratio versus context length for a dense GPT-style model and a representative 5:1 local/global sparse schedule.](figures/section4-ratio-vs-context.svg)

**Figure 1.** `SNARK/STARK` symbolic ratio versus context length. The sparse curve is representative, not tied to one exact checkpoint. The dashed line is the dense asymptotic ceiling from Section 4.2. Reproducibility metadata and exact point generation details are recorded in the supplementary scaling appendix and committed figure script/TSV.

---

## 5. Repository Artifact: From Trace-as-Witness to Parameterized Proof-Carrying Decoding

The implementation artifact used in this paper is the open repository `omarespejel/llm-provable-computer` [30]. The current fork extends the upstream prototype with reproducibility bundles, semantic agreement artifacts, an experimental `stwo` backend, shared-table lookup demos, transformer-shaped fixtures, and a parameterized proof-carrying decoding stack. In its current form, it is best understood as **a semantics-and-proof artifact**: deterministic transformer-relevant execution is compiled into AIR-consumable traces and then packaged into carried-state proof objects suitable for later recursive or accumulation work.

### 5.1 What the repository demonstrates today

The repository snapshot analyzed here provides:

- a deterministic transformer-shaped virtual machine,
- a statement-versioned proof claim (`statement-v1`) shared across backend paths,
- semantic lockstep and multi-engine agreement checks with ONNX validation,
- `research-v2` semantic artifacts for one-step, prefix-trace, and matrix agreement checks,
- a frozen vanilla reproducibility tier (`production-v1`) with commit-pinned artifact metadata,
- a frozen narrow experimental `stwo` tier (`stwo-experimental-v1`) with arithmetic, lookup-envelope, transformer-shaped, and decoding artifacts,
- a parameterized proof-carrying decoding family (`decoding_step_v2`) over multiple public layouts,
- composable carried-state packaging layers (chain, segment, rollup, multi-layout rollup matrix),
- explicit cumulative and frontier commitments for both KV-side and lookup-side state,
- a verification-hardening stack for this carried-state path: oracle/differential checks, structure-aware fuzz smoke targets, targeted mutation testing, Miri/address-sanitizer suites, and a bounded Kani formal-contract kernel.

These capabilities support a stronger systems statement than earlier drafts: not only that traces can be proved, but that the same base decode relation can be carried across progressively more composable manifest layers without changing the underlying statement boundary.

### 5.2 What the repository does **not** yet demonstrate

The repository remains deliberately narrow:

- the default reproducibility bundle and primary transformer proof relation still use the vanilla STARK backend,
- the experimental `stwo` path remains a bounded research surface rather than a broad production zkML prover,
- the proved attention mode is currently `average-hard`, not full standard softmax,
- shared-table lookup state is carried and bounded, but not yet accumulated/compressed across decode steps,
- recursive aggregation/compression is not implemented yet in the public path,
- learned/trained model proving and end-to-end full-LLM proving remain out of scope,
- zero-knowledge hiding is not implemented,
- full-ISA AIR coverage for all bitwise and compare instructions is not complete.

These limits are central to scope discipline. The artifact supports the structural systems claim and pre-recursive carried-state claim, but it does not close the full softmax-and-recursion loop.

### 5.3 Frozen reproducibility bundle

On April 4, 2026, we generated a `production-v1` reproducibility bundle from execution/proof commit `58bb05f` and documented it in immutable artifact snapshot commit `8d435d5` with command logs, hashes, and proof artifacts [31].

This tier proves small arithmetic fixtures plus semantic-agreement artifacts. Detailed timings and sizes remain in the artifact appendix and are treated as reproducibility evidence, not cross-system performance evidence.

### 5.4 Frozen experimental S-two tier and post-freeze bridge artifacts

On April 6, 2026, we generated a second immutable bundle for the experimental `stwo` path (artifact-index commit `3970277`) with representative arithmetic, lookup-envelope, transformer-shaped, and decoding-chain artifacts [40]. This `stwo-experimental-v1` tier complements rather than replaces `production-v1`.

Beyond that frozen tier, the same repository line carries the broader bridge artifact: parameterized `decoding_step_v2` proofs over multiple layouts, then carried-state packaging into chains, segments, rollups, and a layout matrix, plus KV/lookup cumulative and frontier commitments (Phase 13-20 in repository design materials). These are commit-pinned systems evidence, not recursive compression evidence.

### 5.5 Why this artifact matters

This artifact narrows the gap between analytic and systems claims by showing that:

1. transformer-relevant execution traces can be proved directly,
2. semantic equivalence can be checked across runtimes before proof generation,
3. one parameterized decode relation can preserve explicit carried state across multiple packaging layers and multiple public layouts,
4. reproducibility can be anchored in immutable bundles plus commit-pinned post-freeze bridge artifacts.

---

## 6. Infrastructure Context: S-two and Starknet

The infrastructure argument is stronger now than it was a year ago.

### 6.1 S-two is no longer merely prospective

StarkWare’s public materials position S-two as a next-generation open-source prover around Circle STARKs over M31. The March 31, 2026 recursion update is relevant because aggregation is required once workloads become large or modular [19].

For this paper, the key distinction is: **S-two progress strengthens the roadmap, while the repository still keeps its default artifact bundle and primary transformer proof relation on the vanilla backend.** It exposes `stwo` through a frozen narrow evidence tier plus a broader experimental carried-state path.

Verifier cost and proof size remain part of that roadmap. The frozen vanilla tier still produces multi-megabyte proofs for tiny fixtures, so aggregation/compression remains necessary for practical onchain use [19, 34].

### 6.2 Starknet proof verification and privacy

Starknet’s public version materials for `0.14.2` list in-protocol S-two proof verification as a network feature, and `SNIP-36` gives the corresponding technical shape for proof-carrying transactions and `proof_facts` [22, 23]. This is highly relevant to verifiable AI because it reduces the friction of taking a locally generated proof and making it legible to onchain execution. Where this paper discusses Starknet `0.14.2`, it relies on public release and specification materials rather than on a matched benchmark or archival systems paper.

Separately, Starknet’s March 10, 2026 STRK20 announcement states that any ERC-20 on Starknet can now be private, with client-side proof generation and unified Cairo-based logic [21]. That makes the privacy side of “private verifiable inference” more concrete in current public infrastructure terms.

---

## 7. Related Systems and Competitive Landscape

### 7.1 DeepProve as a strong SNARK counterexample

Any serious paper on this topic must treat Lagrange’s DeepProve as a counterexample to sweeping anti-SNARK claims. Public Lagrange materials report full GPT-2 inference and later Gemma-class progress, combining sumcheck-heavy linear handling with custom/lookup handling for non-arithmetic components [24, 25]. The conclusion is narrower: SNARK systems can prove transformer workloads, but may do so with different prover-side economics.

### 7.2 Jolt Atlas and lookup-native SNARK convergence

Jolt Atlas is a newer counterpoint because it reaches a lookup-centric architecture from the SNARK side, extending Jolt to ONNX tensor operations and emphasizing non-linear workload handling [38]. The main relevance here is convergence: independent systems are reorganizing around lookup-heavy non-arithmetic handling.

### 7.3 NANOZK and zkLLM on layerwise and attention-specific specialization

NANOZK and zkLLM reinforce the same trend from different directions: layerwise decomposition and attention/nonlinearity specialization with lookup-heavy machinery [10, 39]. For this paper they are architectural evidence, not matched benchmarks.

### 7.4 BitSage stwo-ml as the closest public STARK-native comparator

BitSage stwo-ml is the closest public STARK-native comparator to this paper’s architecture thesis. Public materials show GKR/sumcheck/LogUp-style machinery on an S-two/STWO path plus Starknet verification paths [26, 27]. These are treated as project-reported evidence rather than normalized benchmarks.

### 7.5 LuminAIR and the custom-AIR path

Giza and StarkWare’s LuminAIR shows a different STARK-native path: custom AIR compilation for computational graphs rather than a transformer-VM-first substrate [28, 29]. The contest is therefore not only SNARK vs STARK, but also which STARK-native architecture absorbs ML workloads best.

### 7.6 A more defensible comparative claim

The most defensible comparative claim is therefore:

> Once large linear algebra is handled efficiently on both sides, the remaining contest is dominated by lookup handling, transparent recursion, field arithmetic, and commitment backend. On those axes, STARK-native stacks remain highly compelling.

This is stronger than “STARKs have already won” because it is narrower and better evidenced. A supplementary appendix summarizes comparison details.

---

## 8. Discussion and Engineering Next Steps

### 8.1 What the paper supports, and what it does not

Taken together, the paper supports a transformer-specific analytic argument for why STARK-native systems may enjoy structural prover-side advantages, a concrete semantics-and-proof artifact showing both trace-as-witness proving and parameterized proof-carrying decoding over explicit carried-state boundaries, and a live infrastructure roadmap in which S-two recursion, Starknet proof verification, and privacy tooling make the direction increasingly practical.

It does **not** yet support stronger claims such as: that STARKs have conclusively beaten SNARKs for transformer proving, that the repository proves full standard-softmax transformer inference end-to-end, that the repository is already an S-two-based zkML system, or that the benchmark bundle is evidence of production-scale LLM proving.

### 8.2 Highest-leverage repository milestones from this unified baseline

With the parameterized proof-carrying decoding bridge now present, the next highest-leverage milestone is no longer “add carried-state packaging”; it is **carry-state compression and accumulation**.

Concretely, the strongest next move is to keep the same decode relation and statement discipline while adding:

- shared-table accumulation across decode steps for lookup-side state,
- recursive aggregation/compression over segment/rollup/matrix boundaries,
- one more faithful non-arithmetic attention path on the experimental `stwo` route.

That sequence connects the current analytic bottleneck diagnosis (lookup-heavy non-arithmetic pressure) to the next systems bottleneck (proof-size and verifier-cost compression) without overstating current maturity.

The next supporting engineering moves remain:

- complete full-ISA AIR coverage,
- keep artifact generation and benchmark metadata machine-readable in CI,
- add a minimal learned-model fragment or quantized transformer block only once the accumulation path is stable.

### 8.3 Future work that would materially strengthen the next paper

The next-paper opportunity is now narrower and more technical: transformer-specific accumulation, not another broad STARK-vs-SNARK framing.

Recent folding literature already covers generalized recursive arguments and CCS/AIR-compatible folding abstractions [41, 43, 44, 45]. Newer small-field and post-quantum folding directions further reduce the novelty space for generic claims [41]. Therefore, the strongest defensible future contribution is:

1. keep one fixed transformer-block relation and one decode transition relation,
2. accumulate repeated block/step instances with shared lookup tables,
3. preserve explicit KV/lookup boundary commitments under that accumulation,
4. measure flat vs carried vs accumulated modes on the same artifact family.

A second high-value future track is trust-core assurance rather than feature breadth: keep differential/oracle tests, fuzzing, and bounded model-checking around the carried-state verifier kernels, then selectively formalize only the smallest trust-critical binding layer [42].

---

## 9. Conclusion

This paper does not argue that SNARKs are incapable of proving transformers, nor that STARK-based systems have already won verifiable AI. It argues something more precise.

Transformer workloads expose exactly the dimensions on which STARK-native systems may compound advantages: lookup-heavy nonlinearities, transparent recursion, and fast M31-style field arithmetic. At the same time, modern SNARK systems continue to narrow the gap through custom circuits, lookup techniques, and increasingly sophisticated handling of non-polynomial functions.

The repository artifact contributes evidence at both the trace-semantics layer and the pre-recursive state-carrying layer. Execution traces can be proved directly. Semantic equivalence can be enforced across runtimes. A parameterized proof-carrying decoding relation can preserve explicit carried-state commitments across chains, segments, rollups, and multi-layout matrices. Portable artifacts can be generated and hashed. Reproducibility can be grounded in committed benchmark metadata. That is not the end state of verifiable AI, but it is a defensible and useful bridge toward it.

The frontier is therefore no longer “can transformers be proved?” The frontier is: **which proving architecture scales most cleanly to long-context, production verifiable inference while preserving practical deployment properties such as transparency, post-quantum security, and recursive aggregation, and can compress repeated transformer structure without losing semantic discipline?**

---

## Acknowledgments

This paper uses the maintained fork `omarespejel/llm-provable-computer`, which builds directly on Abdelhamid Bakhta’s upstream public repository `AbdelStark/llm-provable-computer`.

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
30. `omarespejel/llm-provable-computer`. “Repository Snapshot Discussed in Sections 5 and 8.” GitHub repository snapshot, release tag `paper-publication-v2-2026-04-07` (commit `bc9037296804914fe9ad799a8d494b27f4cafbeb`). <https://github.com/omarespejel/llm-provable-computer/tree/bc9037296804914fe9ad799a8d494b27f4cafbeb>
31. `omarespejel/llm-provable-computer`. “Appendix Artifact Index (Production V1).” GitHub artifact snapshot, commit `8d435d540b8e3cf33ec4381bb820a00b6fe7aae6`, documenting a bundle generated from execution/proof commit `58bb05fdd57ee9816e5935eb004396fea6a9fac3`. <https://github.com/omarespejel/llm-provable-computer/blob/8d435d540b8e3cf33ec4381bb820a00b6fe7aae6/docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md>
32. Starknet Docs. “Accounts.” *Starknet Documentation*. Accessed April 5, 2026. <https://docs.starknet.io/architecture/accounts>
33. Zhizhi Peng, Chonghe Zhao, Taotao Wang, Guofu Liao, Zibin Lin, Yifeng Liu, Bin Cao, Long Shi, Qing Yang, and Shengli Zhang. “A Survey of Zero-Knowledge Proof-Based Verifiable Machine Learning.” *Artificial Intelligence Review* (accepted manuscript), arXiv:2502.18535v2, 2026. <https://arxiv.org/abs/2502.18535>
34. Ayush Nainwal, Atharva Kamble, and Nitin Awathare. “A Comparative Analysis of zk-SNARKs and zk-STARKs: Theory and Practice.” *arXiv preprint* arXiv:2512.10020, 2025. <https://arxiv.org/abs/2512.10020>
35. Jiajun Wang, Xiaowen Wang, Zekun Wen, Linyan Lyu, Wei Wang, Yuxin Wang, Yanjiang Yang, Jian Liu, Jiaheng Zhang, Chao Li, and Qianhui Wang. “zkPyTorch: Verifiable Training and Inference with Zero-Knowledge Proofs.” *IACR Cryptology ePrint Archive*, Paper 2025/535, 2025. <https://eprint.iacr.org/2025/535>
36. Polyhedra Network. “zkPyTorch.” *Polyhedra Product Page*. Accessed April 6, 2026. <https://polyhedra.network/zkPyTorch>
37. Hugo Touvron, Louis Martin, Kevin Stone, et al. “Llama 2: Open Foundation and Fine-Tuned Chat Models.” *arXiv preprint* arXiv:2307.09288, 2023. <https://arxiv.org/abs/2307.09288>
38. Wyatt Benno, Alberto Centelles, Antoine Douchet, and Khalil Gibran. “Jolt Atlas: Verifiable Inference via Lookup Arguments in Zero Knowledge.” *arXiv preprint* arXiv:2602.17452, 2026. <https://arxiv.org/abs/2602.17452>
39. Zhaohui Geoffrey Wang. “NANOZK: Layerwise Zero-Knowledge Proofs for Verifiable Large Language Model Inference.” *arXiv preprint* arXiv:2603.18046, 2026. <https://arxiv.org/abs/2603.18046>
40. `omarespejel/llm-provable-computer`. “Appendix Artifact Index (S-two Experimental V1).” GitHub artifact snapshot, commit `3970277d964a0a9a5326b0db364cf16822c1ccd4`, at `docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md`. <https://github.com/omarespejel/llm-provable-computer/blob/3970277d964a0a9a5326b0db364cf16822c1ccd4/docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md>
41. Wilson Nguyen and Srinath Setty. “Neo: Lattice-based folding scheme for CCS over small fields and pay-per-bit commitments.” *IACR Cryptology ePrint Archive*, Paper 2025/294, 2025. <https://eprint.iacr.org/2025/294>
42. StarkWare. “How StarkWare Uses Formal Verification to Prove Tech Soundness.” *StarkWare Blog*, March 5, 2026. <https://starkware.co/blog/starkwares-gold-standard-of-soundness-with-formal-verification/>
43. Abhiram Kothapalli and Srinath Setty. “HyperNova: Recursive Arguments for Customizable Constraint Systems.” *IACR Cryptology ePrint Archive*, Paper 2023/573, 2023. <https://eprint.iacr.org/2023/573>
44. Abhiram Kothapalli and Srinath Setty. “NeutronNova: Folding Everything that Reduces to Zero-Check.” *IACR Cryptology ePrint Archive*, Paper 2024/1606, 2024. <https://eprint.iacr.org/2024/1606>
45. Abhiram Kothapalli and Srinath Setty. “ProtoStar: Generic Efficient Accumulation/Folding for Special Sound Protocols.” *IACR Cryptology ePrint Archive*, Paper 2023/620, 2023. <https://eprint.iacr.org/2023/620>
