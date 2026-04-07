# Proof-Carrying Decoding and Mergeable Carried-State Layers over an Experimental S-two Backend

Omar Espejel  
Starknet Foundation  
Working draft, April 2026

## Abstract

This paper studies a narrower question than full zkML inference: how far a transformer-shaped proof stack can be pushed toward proof-carrying decoding before recursion or accumulation are introduced. We present an experimental S-two-backed extension of `llm-provable-computer` that preserves the existing `statement-v1` execution claim while adding a parameterized decoding relation, carried KV-cache state, cumulative and frontier KV-history commitments, and cumulative and frontier lookup commitments. The same base `decoding_step_v2` proofs are packaged into a chain, a segment bundle, a rollup-over-segments layer, and a multi-layout rollup matrix. The main contribution is therefore systems-level rather than cryptographic: a stable small-field proof-carrying decoding relation whose carried state becomes progressively more mergeable without yet claiming recursive compression, shared-table accumulation across steps, or full standard-softmax transformer proving. The resulting artifact is a stronger bridge between the earlier architecture thesis and a later transformer-specific accumulation paper.

## 1. Introduction

The previous paper in this repository argued that transformer workloads are structurally well aligned with STARK-style proof systems, especially when lookup-heavy non-arithmetic work dominates the proving burden at long context [1]. That paper was intentionally modest on the implementation side: it documented a semantics-hardened proof artifact, a narrow experimental `stwo` path, and a list of milestones needed to make the implementation story more compelling.

This paper is the next step in that sequence. Its question is not whether STARKs beat SNARKs in deployment today. It is not whether recursion is already integrated. It is not whether full standard-softmax transformer inference has been proved on S-two. The question here is smaller and more concrete:

> Can proof-carrying decoding be expressed as a stable experimental S-two relation with carried state that remains valid across multiple public layouts and progressively more mergeable packaging layers?

The answer implemented in the repository is yes, within a narrow but real scope. The repository now contains:

- a fixed-shape proof-carrying decoding demo over `decoding_step_v1`,
- a parameterized `decoding_step_v2` family,
- a validated three-layout matrix over that family,
- chunked cumulative KV-history commitments,
- explicit segment and rollup packaging over those chains,
- a multi-layout rollup matrix,
- explicit KV-history frontier commitments,
- a cumulative lookup transcript commitment, and
- a recent lookup frontier commitment.

The right claim is therefore a systems claim about carried-state discipline over a stable proof relation, not a broad proof-system claim.

## 2. Scope and Claim Boundary

This paper makes three claims.

1. A parameterized decode-step family can be proved on the current experimental `stwo` path while preserving the same `statement-v1` semantic contract used elsewhere in the repository.
2. The carried state for that family can be packaged into progressively more mergeable layers without changing the base decode-step relation.
3. Both arithmetic state and non-arithmetic lookup-related state can be carried through those layers in committed form.

This paper does **not** claim any of the following.

- It does not claim recursive compression.
- It does not claim a generic accumulation or folding construction.
- It does not claim full standard-softmax transformer proving on S-two.
- It does not claim production-scale decoder inference.
- It does not claim matched benchmark superiority over any external system.

That boundary is important. The artifact described here is best understood as a pre-recursive carried-state system for transformer-shaped decoding, not as a finished zkML prover.

## 3. Base Relation: Parameterized Proof-Carrying Decoding

### 3.1 From fixed-shape to parameterized decoding

The repository first exposed a fixed-shape proof-carrying decoding chain over `decoding_step_v1`. The more durable relation is now `decoding_step_v2`, a parameterized decode-step family indexed by a public layout.

A layout is currently defined by two integers:

- `rolling_kv_pairs`
- `pair_width`

The default public layout is `(4, 4)`. The shipped layout matrix currently validates three public layouts:

- `(2, 2)`
- `(3, 3)`
- `(4, 4)`

For each layout, the demo witness generator constructs a three-step decoding chain. That chain length is deliberately small; the point is to validate the carried-state semantics, not to maximize sequence length.

### 3.2 Statement boundary

The base proof boundary does not change. Each step remains a `statement-v1` execution proof on the experimental `stwo` backend. The claim is still an execution claim, not a new transformer-specific statement. The repository keeps that boundary explicit so the carried-state machinery cannot silently widen the semantic contract.

### 3.3 Carried step state

Each decoding step exposes a carried public state. By Phase 20, the Phase 14+ state includes at least:

- step index and decoding position,
- layout commitment,
- persistent state commitment,
- cumulative KV-history commitment and length,
- sealed/open chunk commitments for that history,
- KV-history frontier commitment and frontier pair count,
- cumulative lookup transcript commitment and entry count,
- lookup frontier commitment and frontier entry count,
- live KV-cache commitment,
- incoming token commitment,
- query commitment,
- output commitment,
- lookup-row commitment.

This state is intentionally redundant in places. The redundancy is not accidental. It exists to make boundary preservation and tamper detection explicit at every packaging layer.

## 4. Mergeable Carried-State Layers

The repository now exposes a sequence of layers over the same base `decoding_step_v2` proofs.

### 4.1 Phase 14: Chunked cumulative KV history

Phase 14 upgrades the carried state from a flat cumulative history to a chunked cumulative history. The default demo uses a chunk size of `2` KV pairs. The state separates:

- sealed history,
- open history chunk,
- total cumulative history,
- live KV frontier.

That split matters because later layers can consume explicit boundaries instead of one opaque hash.

### 4.2 Phase 15: Segment bundles

Phase 15 groups Phase 14 chains into explicit segments. The default demo uses a maximum of `2` steps per segment. Each segment carries:

- a global start step index,
- a global from-state,
- a global to-state,
- the local Phase 14 chain.

The verifier checks both the local chain and the global boundary states. This turns one monolithic chain into a collection of mergeable carried-state units.

### 4.3 Phase 16: Rollups over segments

Phase 16 groups Phase 15 segments into larger rollups. The default demo uses a maximum of `2` segments per rollup. A rollup therefore becomes a larger carried-state unit whose integrity is derived from the same underlying local proofs.

This is not recursion. It is only packaging plus replayed verification. But it is useful packaging, because it defines a higher-level unit that later recursive or accumulative systems could consume.

### 4.4 Phase 17: Multi-layout rollup matrix

Phase 17 lifts the rollup layer across multiple public layouts. Instead of validating only one layout family, the matrix manifest proves that the same packaging discipline survives across the three public layouts listed above.

This matters for the paper’s claim. Without the matrix layer, the implementation would still look too close to a single hand-tuned decode shape. With it, the claim becomes: one relation, several public layouts, same carried-state contract.

### 4.5 Phase 18: KV-history frontier

Phase 18 adds an explicit frontier commitment for the live suffix of the KV history and ties it directly to the live rolling KV-cache commitment. This is the KV-side analogue of the distinction between cumulative state and recent state.

The point is to make the carried-state boundary more reusable. A later accumulation layer should not need to reconstruct the meaning of the rolling cache from a single undifferentiated history digest.

### 4.6 Phase 19: Lookup transcript

Phase 19 adds a cumulative lookup transcript commitment. This is the first step in carrying a non-arithmetic signal through the same stack rather than treating lookup state as purely local metadata.

The implementation still does not claim shared-table accumulation across decode steps. It does something smaller and more defensible: it preserves a committed transcript of lookup-row commitments across chains, segments, rollups, and layout matrices.

### 4.7 Phase 20: Lookup frontier

Phase 20 adds the non-arithmetic analogue of the KV frontier: a recent lookup frontier commitment and entry count. The carried state therefore now distinguishes:

- cumulative lookup transcript,
- recent lookup frontier.

That distinction is useful for the same reason it is useful on the KV side. A later accumulation or folding layer will want both a cumulative summary and an immediately consumable boundary object.

## 5. Repository Artifact

### 5.1 Default demo parameters

The current public demo family is intentionally small.

| Layer | Default public setting |
|---|---|
| Base chain length | `3` decode steps |
| Layout matrix | `(2,2)`, `(3,3)`, `(4,4)` |
| KV-history chunk size | `2` KV pairs |
| Segment step limit | `2` |
| Rollup segment limit | `2` |

These numbers are not meant as optimized proving settings. They are chosen to make the carried-state structure inspectable and testable.

### 5.2 What the artifact demonstrates

The artifact demonstrates four things.

1. The experimental `stwo` backend can prove and verify a parameterized proof-carrying decoding relation under the same `statement-v1` claim family.
2. The same relation survives multiple public layouts.
3. The carried state can be packaged into chunked chains, segments, rollups, and a rollup matrix without losing boundary integrity.
4. Both KV-side state and lookup-side state can be preserved as cumulative and recent-window commitments.

### 5.3 What the artifact does not yet demonstrate

The artifact still does not demonstrate:

- standard-softmax decoding on S-two,
- shared-table lookup accumulation across decode steps,
- recursive compression of the segment or rollup layers,
- a production KV-cache commitment structure,
- a full transformer block relation with realistic model scale.

These are not small omissions. They are the reason this paper is a systems bridge rather than the later accumulation paper.

## 6. Why This Matters for the Next Paper

A later folding or accumulation paper needs more than a single decoding demo. It needs a relation and boundary structure that are stable enough to fold over.

The current repository state now supplies several of those prerequisites.

### 6.1 Stable relation

The base relation is no longer one fixed proof demo. It is a parameterized `decoding_step_v2` family with several public layouts.

### 6.2 Mergeable units

The carried state is no longer one flat chain. It is packaged into:

- chunked chains,
- segments,
- rollups,
- a multi-layout rollup matrix.

Those are exactly the kinds of units an eventual accumulation layer would want to consume.

### 6.3 Dual boundaries for arithmetic and non-arithmetic state

The system now carries both cumulative and recent-window boundaries for two different state families:

- KV history and live KV frontier,
- lookup transcript and lookup frontier.

That is a materially better starting point for a later transformer-specific accumulation paper than a system that carries only a flat history hash.

## 7. Limitations and Threats to Validity

The limitations here are straightforward.

### 7.1 Experimental backend narrowness

The `stwo` path remains narrow and fixture-driven. It is real, but not broad.

### 7.2 Decode relation narrowness

The decode relation remains a bounded research family, not a general production decoder interface.

### 7.3 Non-arithmetic state is carried, not yet accumulated

The lookup transcript and lookup frontier are committed and preserved, but they are not yet compressed by a shared-table accumulation mechanism.

### 7.4 No recursion

The rollup layers are structural packaging plus replayed verification. They are not recursive proof composition.

### 7.5 No claim about practical prover superiority

This paper makes no matched-benchmark claim against external systems. The contribution is structural and artifact-level.

## 8. Engineering Next Steps

The next repository milestone should not be another packaging layer by itself. The next high-leverage step is to move one transformer-relevant non-arithmetic path deeper into the main proved relation rather than keeping it only in carried transcript form.

A sensible order is:

1. merge the current Phase 18-20 stack cleanly,
2. preserve reproducible demos across the three public layouts,
3. push one lookup-relevant attention path deeper into the proved relation,
4. only then revisit recursive compression or accumulation.

That order keeps the implementation honest. Recursion before a broader proved relation would still be architecture theater.

## 9. Conclusion

This paper does not claim a new proof system. It does not claim recursion. It does not claim full transformer inference on S-two. What it does claim is narrower and, for that reason, stronger: the repository now contains a parameterized proof-carrying decoding relation whose carried state remains valid across multiple layouts and progressively more mergeable packaging layers, while preserving both arithmetic and non-arithmetic boundary commitments.

That is enough to justify a real systems paper. It is also enough to make the later accumulation paper technically serious instead of aspirational.

## Acknowledgments

This draft builds on the maintained `omarespejel/llm-provable-computer` research fork and the earlier architecture paper that motivated the current implementation path.

## References

- [1] Omar Espejel. *On the Alignment of Transformer Workloads and STARK Proof Systems*. Starknet Foundation, April 2026. `/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/docs/paper/stark-transformer-alignment-2026.md`
- [2] `omarespejel/llm-provable-computer`. Maintained research repository and artifact base for the implementation described here. `/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex`
- [3] Eli Ben-Sasson et al. *Scalable, Transparent, and Post-Quantum Secure Computational Integrity*. IACR ePrint 2018/046.
- [4] Ulrich Haböck, David Levit, and Valeria Papini. *Circle STARKs*. IACR ePrint 2024/278.
- [5] StarkWare Industries. *STWO Prover*. [https://github.com/starkware-libs/stwo](https://github.com/starkware-libs/stwo)
