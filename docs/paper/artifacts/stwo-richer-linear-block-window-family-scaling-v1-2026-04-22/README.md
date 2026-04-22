# Richer Linear-block Window Family Scaling Bundle

This bundle freezes the first scaling sweep for the compact richer-family handoff introduced in Phase113.

## Headline metrics

- explicit Phase107 w4 bytes: 7484
- richer-family Phase113 w4 bytes: 3029
- explicit Phase107 w8 bytes: 11343
- richer-family Phase113 w8 bytes: 3031
- Phase113 w4 / explicit w4: 40.4730%
- Phase113 w8 / explicit w8: 26.7213%
- Phase113 overhead above Phase112 at w4: 748 bytes
- Phase113 overhead above Phase112 at w8: 748 bytes
- Phase113 absolute growth from w4 to w8: 2 bytes
- shared execution proof bytes: 734065

The key result is structural: the richer-family handoff stays compact at both supported scaling points, and its size changes by only 2 bytes while the explicit repeated-window source grows from 7484 bytes to 11343 bytes.

## Scope

- This is a verifier-bound artifact scaling sweep.
- It is not a recursion claim.
- It is not a matched benchmark against public zkML papers.
- It is not a production prover throughput claim.
