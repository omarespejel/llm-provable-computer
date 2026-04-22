# Richer Linear-block Window Family Scaling Bundle

This bundle freezes the first scaling sweep for the compact richer-family handoff introduced in Phase113.

## Headline metrics

- explicit Phase107 w4 bytes: 7524
- richer-family Phase113 w4 bytes: 3069
- explicit Phase107 w8 bytes: 11383
- richer-family Phase113 w8 bytes: 3071
- Phase113 w4 / explicit w4: 40.7895%
- Phase113 w8 / explicit w8: 26.9788%
- Phase113 overhead above Phase112 at w4: 762 bytes
- Phase113 overhead above Phase112 at w8: 762 bytes
- Phase113 absolute growth from w4 to w8: 2 bytes
- shared execution proof bytes: 734308

The key result is structural: the richer-family handoff stays compact at both supported scaling points, and its size changes by only 2 bytes while the explicit repeated-window source grows from 7524 bytes to 11383 bytes.

## Scope

- This is a verifier-bound artifact scaling sweep.
- It is not a recursion claim.
- It is not a matched benchmark against public zkML papers.
- It is not a production prover throughput claim.
