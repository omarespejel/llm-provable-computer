# Proof-Carrying Decoding over an Experimental S-two Backend

Omar Espejel  
Starknet Foundation  
Working draft, April 2026

## Abstract

This paper studies a narrower question than full zkML inference: how far an
experimental small-field transformer proof stack can be pushed toward
proof-carrying decoding before recursion or accumulation are introduced. We
present an extension of `provable-transformer-vm` that preserves the existing
`statement-v1` execution claim while adding a parameterized decoding relation,
multi-layout carried state, cumulative and frontier KV-history commitments, and
cumulative and frontier lookup commitments. The same base `decoding_step_v2`
proofs are then packaged into chains, segments, rollups, and a multi-layout
rollup matrix. The contribution is systems-level rather than cryptographic: a
stable proof-carrying decoding relation whose carried state becomes
progressively more composable without claiming recursive compression,
shared-table accumulation across decode steps, or full standard-softmax
transformer proving. The result is a concrete pre-recursive bridge between the
earlier architecture thesis and a later transformer-specific accumulation
paper.

## 1. Introduction

The previous paper in this repository argued that transformer workloads are
structurally well aligned with STARK-style proof systems, especially when
lookup-heavy non-arithmetic work dominates the proving burden at long context
[1, 4, 5, 6]. That paper was intentionally modest on the implementation side: it
documented a semantics-hardened proof artifact, a narrow experimental `stwo`
path, and a list of milestones needed to make the implementation story more
compelling.

This paper is the next step in that sequence. Its question is not whether
STARKs beat SNARKs in deployment today. It is not whether recursion is already
integrated. It is not whether full standard-softmax transformer inference has
been proved on S-two. The question here is smaller and more concrete:

> Can proof-carrying decoding be expressed as a stable experimental S-two relation with carried state that remains valid across multiple public layouts and progressively more composable packaging layers?

The answer implemented in the repository is yes, within a narrow but real
scope. The right claim is therefore a systems claim about carried-state
discipline over a stable proof relation, not a broad proof-system claim.

This paper makes three contributions.

1. It exposes a parameterized proof-carrying decoding relation,
   `decoding_step_v2`, that remains inside the existing `statement-v1`
   execution claim rather than inventing a new statement family prematurely.
2. It shows that the same base proofs can be repackaged into progressively more
   composable carried-state units: chunked chains, segments, rollups, and a
   multi-layout rollup matrix.
3. It carries two distinct state families through that stack:
   arithmetic/KV-side state and lookup-side non-arithmetic state, each with
   both cumulative and frontier boundaries.

## 2. Scope and Claim Boundary

This paper makes three narrow claims.

1. A parameterized decode-step family can be proved on the current experimental `stwo` path while preserving the same `statement-v1` semantic contract used elsewhere in the repository.
2. The carried state for that family can be packaged into progressively more composable layers without changing the base decode-step relation.
3. Both arithmetic state and non-arithmetic lookup-related state can be carried through those layers in committed form.

This paper does **not** claim any of the following.

- It does not claim recursive compression.
- It does not claim a generic accumulation or folding construction.
- It does not claim full standard-softmax transformer proving on S-two.
- It does not claim production-scale decoder inference.
- It does not claim matched benchmark superiority over any external system.

That boundary is important. The artifact described here is best understood as a pre-recursive carried-state system for transformer-shaped decoding, not as a finished zkML prover.

By "composable" we mean boundary-compatible and suitable for later recursive or
accumulative consumption. We do **not** mean cryptographically compressed or
already folded.

### 2.1 Positioning relative to PCD, IVC, and folding

This paper sits below proof-carrying data, incrementally verifiable
computation, and folding-based systems in ambition. Prior work already covers
recursive composition and proof-carrying data [7], recursive arguments for
customizable constraint systems [8], folding for zero-check/CCS relations that
generalize Plonkish, AIR, and R1CS [9], and generic accumulation/folding for
special-sound protocols with lookup support [10]. The contribution here is not
to compete with those systems at the cryptographic layer. It is to build the
decode-state discipline and boundary objects that a later recursive or
accumulative transformer paper would need.

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

For each layout, the demo witness generator constructs a three-step decoding
chain. That chain length is deliberately small; the point is to validate the
carried-state semantics, not to maximize sequence length.

### 3.2 Statement boundary

The base proof boundary does not change. Each step remains a `statement-v1` execution proof on the experimental `stwo` backend. The claim is still an execution claim, not a new transformer-specific statement. The repository keeps that boundary explicit so the carried-state machinery cannot silently widen the semantic contract.

### 3.3 Carried step state

Each decoding step exposes a carried public state. By Phase 20, the carried
state includes at least:

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

### 3.4 Formal system model

Let the public decoding state at step `t` under layout `\ell` be

\[
\Sigma_t^{(\ell)} =
(\ell, p_t, C_t^{state}, C_t^{kv}, C_t^{kv,front}, n_t^{kv}, n_t^{kv,front},
 C_t^{look}, C_t^{look,front}, n_t^{look}, n_t^{look,front},
 C_t^{in}, C_t^{qry}, C_t^{out}, C_t^{row}),
\]

where:

- `p_t` is the public decoding position,
- `C_t^{state}` is the persistent-state commitment,
- `C_t^{kv}` and `C_t^{kv,front}` are cumulative and frontier KV-side commitments,
- `C_t^{look}` and `C_t^{look,front}` are cumulative and frontier lookup-side commitments,
- `n_t^{kv}, n_t^{kv,front}, n_t^{look}, n_t^{look,front}` are the corresponding public lengths or counts,
- `C_t^{in}, C_t^{qry}, C_t^{out}, C_t^{row}` are the input-token, query, output, and lookup-row commitments.

For each public layout `\ell`, define the base decode relation

\[
\mathcal{R}_{decode}^{(\ell)}(\Sigma_t^{(\ell)}, w_t) \to \Sigma_{t+1}^{(\ell)},
\]

where `w_t` is the private witness for one `decoding_step_v2` execution proof.
The repository realizes `\mathcal{R}_{decode}^{(\ell)}` by a `statement-v1`
proof plus explicit boundary checks over the carried public state.

We then define three higher-level validity predicates:

- `SegmentVerify`: every base step proof verifies and all adjacent segment-local
  boundary states match,
- `RollupVerify`: every contained segment verifies and all segment boundary
  states match globally,
- `MatrixVerify`: every contained rollup verifies under its declared public
  layout and the matrix-level counts/layout commitments match.

**Proposition 1.** If every base proof in a packaged object verifies under
`statement-v1` and all required adjacent boundary states match, then the
packaged object preserves the same start-state to end-state relation as the
underlying decode chain.

This is a systems proposition rather than a new cryptographic theorem. The
higher layers do not add compression; they preserve the same relation while
making its boundary objects explicit and reusable.

## 4. Composable Carried-State Layers

The repository now exposes a sequence of layers over the same base
`decoding_step_v2` proofs.

```text
decode_step_v2 proofs
        │
        ▼
    chain layer
        │
        ▼
   segment layer
        │
        ▼
    rollup layer
        │
        ▼
 multi-layout matrix

KV lane:      cumulative history  + frontier
Lookup lane:  cumulative transcript + frontier
```

### 4.1 Chunked cumulative KV history (Phase 14)

Phase 14 upgrades the carried state from a flat cumulative history to a chunked cumulative history. The default demo uses a chunk size of `2` KV pairs. The state separates:

- sealed history,
- open history chunk,
- total cumulative history,
- live KV frontier.

That split matters because later layers can consume explicit boundaries instead of one opaque hash.

### 4.2 Segment bundles (Phase 15)

Phase 15 groups Phase 14 chains into explicit segments. The default demo uses a maximum of `2` steps per segment. Each segment carries:

- a global start step index,
- a global from-state,
- a global to-state,
- the local Phase 14 chain.

The verifier checks both the local chain and the global boundary states. This
turns one monolithic chain into a collection of composable carried-state units.

### 4.3 Rollups over segments (Phase 16)

Phase 16 groups Phase 15 segments into larger rollups. The default demo uses a maximum of `2` segments per rollup. A rollup therefore becomes a larger carried-state unit whose integrity is derived from the same underlying local proofs.

This is not recursion. It is only packaging plus replayed verification. But it is useful packaging, because it defines a higher-level unit that later recursive or accumulative systems could consume.

### 4.4 Multi-layout rollup matrix (Phase 17)

Phase 17 lifts the rollup layer across multiple public layouts. Instead of validating only one layout family, the matrix manifest proves that the same packaging discipline survives across the three public layouts listed above.

This matters for the paper’s claim. Without the matrix layer, the implementation would still look too close to a single hand-tuned decode shape. With it, the claim becomes: one relation, several public layouts, same carried-state contract.

### 4.5 KV-history frontier (Phase 18)

Phase 18 adds an explicit frontier commitment for the live suffix of the KV history and ties it directly to the live rolling KV-cache commitment. This is the KV-side analogue of the distinction between cumulative state and recent state.

The point is to make the carried-state boundary more reusable. A later accumulation layer should not need to reconstruct the meaning of the rolling cache from a single undifferentiated history digest.

### 4.6 Lookup transcript (Phase 19)

Phase 19 adds a cumulative lookup transcript commitment. This is the first step in carrying a non-arithmetic signal through the same stack rather than treating lookup state as purely local metadata.

The implementation still does not claim shared-table accumulation across decode steps. It does something smaller and more defensible: it preserves a committed transcript of lookup-row commitments across chains, segments, rollups, and layout matrices.

### 4.7 Lookup frontier (Phase 20)

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

### 5.2 Public artifact stack

The public artifact surface is easier to understand as one stack over the same
base decode-step proofs.

| Layer | Public artifact | Adds |
|---|---|---|
| Base chain | `prove-stwo-decoding-family-demo` | Parameterized `decoding_step_v2` relation |
| Layout matrix | `prove-stwo-decoding-layout-matrix-demo` | Same relation across three public layouts |
| Chunked history | `prove-stwo-decoding-chunked-history-demo` | Chunked cumulative KV-history |
| Segments | `prove-stwo-decoding-history-segments-demo` | Segment boundaries over local chains |
| Rollups | `prove-stwo-decoding-history-rollup-demo` | Larger carried-state units over segments |
| Rollup matrix | `prove-stwo-decoding-history-rollup-matrix-demo` | Rollups across multiple public layouts |
| KV frontier | Phase 18 state extension | Recent KV boundary in addition to cumulative history |
| Lookup transcript | Phase 19 state extension | Cumulative non-arithmetic transcript |
| Lookup frontier | Phase 20 state extension | Recent non-arithmetic boundary |

### 5.3 Frozen artifact facts

The current frozen `stwo-experimental-v1` bundle already contains four concrete
artifacts that matter for this paper's scope [3].

| Artifact | Scope | Size (bytes) | Prove (s) | Verify (s) |
|---|---|---:|---:|---:|
| `addition.stwo.proof.json` | arithmetic execution proof | 54,563 | 2 | 1 |
| `shared-normalization.stwo.proof.json` | shared-table normalization envelope | 74,074 | 1 | 1 |
| `gemma_block_v4.stwo.proof.json` | transformer-shaped fixed-shape execution proof | 751,737 | 1 | 1 |
| `decoding.stwo.chain.json` | three-step proof-carrying decoding chain | 4,032,182 | 1 | 1 |

These are artifact facts from one frozen bundle, not a normalized backend
benchmark study.

### 5.4 What the artifact demonstrates

The artifact demonstrates four things.

1. The experimental `stwo` backend can prove and verify a parameterized proof-carrying decoding relation under the same `statement-v1` claim family.
2. The same relation survives multiple public layouts.
3. The carried state can be packaged into chunked chains, segments, rollups, and a rollup matrix without losing boundary integrity.
4. Both KV-side state and lookup-side state can be preserved as cumulative and recent-window commitments.

Before cross-step accumulation exists, the repository already proves some
shared-table lookup components directly. The frozen bundle includes a
shared-table normalization proof envelope, and `gemma_block_v4` already binds
shared-table normalization and activation rows inside a top-level `stwo`
execution proof [2,3]. This paper relies on that component-level evidence, but
it does **not** claim those lookup envelopes are yet accumulated across decode
steps.

### 5.5 What the artifact does not yet demonstrate

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

### 6.2 Composable units

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

The next repository milestone should not be another packaging layer by itself.
The next high-leverage step is to move one transformer-relevant non-arithmetic
path deeper into the main proved relation rather than keeping it only in
carried transcript form.

A sensible order is:

1. merge the current Phase 18-20 stack cleanly,
2. preserve reproducible demos across the three public layouts,
3. push one lookup-relevant attention path deeper into the proved relation,
4. only then revisit recursive compression or accumulation.

That order keeps the implementation honest. Recursion before a broader proved relation would still be architecture theater.

## 9. Conclusion

This paper does not claim a new proof system. It does not claim recursion. It
does not claim full transformer inference on S-two. What it does claim is
narrower and, for that reason, stronger: the repository now contains a
parameterized proof-carrying decoding relation whose carried state remains
valid across multiple layouts and progressively more composable packaging
layers, while preserving both arithmetic and non-arithmetic boundary
commitments.

That is enough to justify a real systems paper. It is also enough to make the later accumulation paper technically serious instead of aspirational.

## Acknowledgments

This draft builds on the maintained `omarespejel/provable-transformer-vm`
repository (earlier phases developed under the `llm-provable-computer`
project name) and the earlier architecture paper that motivated the current
implementation path.

## References

- [1] Omar Espejel. *On the Structural Fit of Transformer Workloads and STARK Proof Systems*. Starknet Foundation, April 2026. Submission-prep snapshot commit `49004aea27a5e02c3732a798d32a32675f0a08b9`. <https://github.com/omarespejel/provable-transformer-vm/blob/49004aea27a5e02c3732a798d32a32675f0a08b9/docs/paper/stark-transformer-alignment-2026.md>
- [2] `omarespejel/provable-transformer-vm`. Maintained research repository and implementation base for the system described here (earlier phases used the `llm-provable-computer` project name). Submission-prep snapshot commit `49004aea27a5e02c3732a798d32a32675f0a08b9`. <https://github.com/omarespejel/provable-transformer-vm/tree/49004aea27a5e02c3732a798d32a32675f0a08b9>
- [3] `omarespejel/provable-transformer-vm`. *Appendix Artifact Index (S-two Experimental V1).* Commit `3970277d964a0a9a5326b0db364cf16822c1ccd4`. <https://github.com/omarespejel/provable-transformer-vm/blob/3970277d964a0a9a5326b0db364cf16822c1ccd4/docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md>
- [4] Eli Ben-Sasson, Iddo Bentov, Yinon Horesh, and Michael Riabzev. *Scalable, Transparent, and Post-Quantum Secure Computational Integrity*. IACR ePrint 2018/046. <https://eprint.iacr.org/2018/046>
- [5] Ulrich Haböck, David Levit, and Valeria Papini. *Circle STARKs*. IACR ePrint 2024/278. <https://eprint.iacr.org/2024/278>
- [6] StarkWare Industries. *STWO Prover*. <https://github.com/starkware-libs/stwo>
- [7] Nir Bitansky, Ran Canetti, Alessandro Chiesa, and Eran Tromer. *Recursive Composition and Bootstrapping for SNARKs and Proof-Carrying Data*. IACR ePrint 2012/095. <https://eprint.iacr.org/2012/095>
- [8] Abhiram Kothapalli and Srinath Setty. *HyperNova: Recursive Arguments for Customizable Constraint Systems*. IACR ePrint 2023/573. <https://eprint.iacr.org/2023/573>
- [9] Abhiram Kothapalli and Srinath Setty. *NeutronNova: Folding Everything that Reduces to Zero-Check*. IACR ePrint 2024/1606. <https://eprint.iacr.org/2024/1606>
- [10] Abhiram Kothapalli and Srinath Setty. *ProtoStar: Generic Efficient Accumulation/Folding for Special Sound Protocols*. IACR ePrint 2023/620. <https://eprint.iacr.org/2023/620>
