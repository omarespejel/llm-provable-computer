# Obelyzk Sepolia Comparator Note (2026-04-25)

This note closes issue `#254` with the strongest honest outcome currently supported by
public primary sources:

- **GO** for a source-backed external calibration row, and
- **NO-GO** for a matched local verifier-time comparator row.

## Objective

The target was one public STARK-native comparator row that could survive scrutiny without
pretending the repo already has a same-workload, same-surface benchmark against an
external system.

The first candidate was the public Obelyzk Starknet Sepolia verifier-object path.

## Pinned public facts

Primary public source 1:

- docs.rs crate page:
  `https://docs.rs/crate/obelyzk/0.3.0`

Pinned facts from that page:

- recursive verifier contract:
  `0x1c208a5fe731c0d03b098b524f274c537587ea1d43d903838cc4a2bf90c40c7`
- verified Starknet Sepolia transaction:
  `0x276c6a448829c0f3975080914a89c2a9611fc41912aff1fddfe29d8f3364ddc`
- recursive calldata width:
  `942` felts
- reported performance row for the checked on-chain example:
  `SmolLM2-135M`, `30` layers, `A10G`, `102s` GKR prove,
  `3.55s` recursive compression, `~106s` total

Primary public source 2:

- paper PDF:
  `https://docs.rs/crate/obelyzk/0.3.0/source/obelyzk-paper.pdf`

Pinned facts from Table 9 and Section 10.3:

- one-layer GKR verify on Starknet Sepolia:
  `~280K` gas
- full `40`-layer Starknet Sepolia path:
  `~2.5M` gas and `~$0.01`
- full `40`-layer `Qwen3-14B` prove time on one `H100`:
  `~122s` end-to-end (`3.04s/layer`)

## Verification handles

The public verifier-object path exposes a concrete contract-call handle:

```bash
starkli call 0x1c208a5fe731c0d03b098b524f274c537587ea1d43d903838cc4a2bf90c40c7 \
  is_verified 0x276c6a448829c0f3975080914a89c2a9611fc41912aff1fddfe29d8f3364ddc
```

In the current local environment, direct live replay of that call was blocked by missing
working Starknet RPC configuration, so this note stays source-backed rather than claiming
fresh live verification. The current evidence posture is therefore:

- exact docs.rs contract and tx identifiers pinned,
- exact paper gas figures pinned, and
- live-call handle recorded, but not newly re-verified in this repo snapshot.

## Honest regime match

This public Obelyzk artifact is useful as a **deployment and verifier-object
calibration row**.

It is **not** a matched local comparator to this repo's current paper-facing rows:

- the public Obelyzk object is a recursive STARK settlement proof over a GKR stack,
- the local `Phase44D` row is a pre-recursive typed-boundary latency surface, and
- the local `Phase71` row is a pre-recursive compact handoff surface.

So the public row is stronger than the old README-only warm-cache proof anecdote, but it
does not justify a sentence like "our verifier is faster than Obelyzk's verifier" or
"our compact object beats Obelyzk's recursive proof" on an apples-to-apples basis.

## Decision

### GO: source-backed calibration row

The repo now updates `docs/paper/evidence/published-zkml-numbers-2026-04.tsv` with a
source-backed Obelyzk row anchored to:

- the docs.rs verifier-object page,
- the exact contract address,
- the exact verified transaction hash,
- the exact recursive calldata width, and
- the checked recursive compression timing on the public example.

### NO-GO: matched verifier-time row

The repo does **not** claim a matched local verifier-time comparison against this
Obelyzk row because the compared objects live at different layers of the stack and under
different workload envelopes.

## Paper-safe sentence

If the paper needs one sentence from this note, the safe version is:

> Obelyzk now provides a source-backed Starknet Sepolia recursive verifier object
> (`942` felts, exact contract and verified transaction pinned), which sharpens the
> public STARK-native deployment comparison, but it is still not a matched local
> verifier-time comparator to this repo's pre-recursive `Phase44D` or `Phase71`
> artifact surfaces.
