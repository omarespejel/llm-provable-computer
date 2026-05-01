# zkAI DeepProve-1 / NANOZK adapter feasibility - 2026-05-01

## Question

Can DeepProve-1 or NANOZK be run through the same zkAI
statement-relabeling benchmark used for the checked EZKL, snarkjs, and native
Stwo adapters?

## Decision

**NO-GO for a public relabeling-adapter benchmark today.**

Both systems are relevant field context. Neither currently exposes the public
proof artifact plus verifier inputs needed for this repo's relabeling benchmark.
That means they should stay in the paper as source-backed related-system context,
not as empirical adapter rows.

## Adapter bar

For this benchmark, a candidate system must expose all of the following:

- a runnable public verifier command or API for the claimed proof object,
- public proof bytes plus verifier inputs sufficient to reproduce baseline
  acceptance,
- a statement surface with model/input/output/config/setup/domain labels that can
  be mutated, and
- a checked command that reproduces baseline verification and the relabeling
  mutation suite.

If any of these are missing, the honest result is not "adapter failed"; it is
"adapter benchmark not runnable from public artifacts."

## Candidate matrix

| System | Gate | Public verifier | Public proof artifact | Baseline reproducible | Relabeling benchmark |
|---|---|---:|---:|---:|---:|
| DeepProve-1 | `NO_GO_PUBLIC_GPT2_ARTIFACT_NOT_REPRODUCIBLE` | partial public repo API, not matched to DeepProve-1 GPT-2 artifact | no | no | not run |
| NANOZK | `NO_GO_NO_PUBLIC_VERIFIER_OR_PROOF_ARTIFACT` | no public verifier found | no | no | not run |

## DeepProve-1 inspection

Source-backed claim context:

- Lagrange's DeepProve-1 blog reports a full GPT-2 inference proof and describes
  transformer graph/layer work including graph structure, transformer-specific
  layers, softmax, LayerNorm, GELU, QKV, and LLM inference state.
- The public repository checked by this probe is
  `https://github.com/Lagrange-Labs/deep-prove` at
  `7d21c35e5e1cb006e413f4a9676333e9e1506a87`.

Inspection result:

- The public repo has proof/verifier code paths and MLP/CNN benchmark examples.
- The public `zkml` README still describes the supported public benchmark surface
  as dense, ReLU, maxpool, and convolution.
- The repo contains a nearby GPT-2 internals script at
  `zkml/assets/scripts/llms/gpt2_internal.py`.
- This probe did not find public DeepProve-1 GPT-2 proof bytes, verifier inputs,
  verification key/setup material, or a reproducible verification command for
  the blog-level GPT-2 claim.

Conclusion: DeepProve-1 is strong related-system context, but not a runnable
public adapter benchmark for our relabeling suite today.

## NANOZK inspection

Source-backed claim context:

- arXiv `2603.18046` reports layerwise transformer proofs and, in the abstract,
  constant-size layer proofs up to `d=128` with `5.5 KB` proof size and `24 ms`
  verification time.
- The arXiv source bundle checked by this probe has SHA-256
  `c505715f18d2bbb8dc01852a764b171984eb51f54a74d03790e29294e78ef2b4`.

Inspection result:

- The arXiv source exposes `main.tex`, bibliography, and style files.
- The only direct GitHub URLs found in the source are dependency/reference links
  for EZKL and Halo2.
- This probe did not find a NANOZK repository, public proof artifact, verifier
  command, or benchmark reproduction package.

Conclusion: NANOZK remains useful as a compact-object and layerwise-proof
calibration point, but not as an empirical relabeling-adapter row today.

## Paper usage

Use these systems conservatively:

- **DeepProve-1:** related-system context showing that transformer proving is
  being pursued seriously outside the local STARK lane.
- **NANOZK:** source-backed compact/layerwise proof context, not a locally
  reproduced verifier-time or statement-binding row.

Do not write:

- "DeepProve-1 failed the relabeling benchmark."
- "NANOZK failed the relabeling benchmark."
- "DeepProve-1/NANOZK are vulnerable to relabeling."

Write instead:

> DeepProve-1 and NANOZK are important related systems, but no public proof
> artifact plus verifier-input bundle was available for the same relabeling
> adapter benchmark, so they are kept as source-backed context rather than
> empirical adapter rows.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-deepprove-nanozk-adapter-feasibility-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-deepprove-nanozk-adapter-feasibility-2026-05.tsv`
- Probe:
  `scripts/zkai_deepprove_nanozk_adapter_feasibility.py`
- Tests:
  `scripts/tests/test_zkai_deepprove_nanozk_adapter_feasibility.py`

## Reproduce

```bash
python3 scripts/zkai_deepprove_nanozk_adapter_feasibility.py \
  --write-json docs/engineering/evidence/zkai-deepprove-nanozk-adapter-feasibility-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-deepprove-nanozk-adapter-feasibility-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_deepprove_nanozk_adapter_feasibility

python3 -m py_compile \
  scripts/zkai_deepprove_nanozk_adapter_feasibility.py \
  scripts/tests/test_zkai_deepprove_nanozk_adapter_feasibility.py

python3 scripts/paper/paper_preflight.py --repo-root .

git diff --check
```

## Non-claims

- This is not a DeepProve-1 soundness finding.
- This is not a NANOZK soundness finding.
- This is not evidence that either system is insecure.
- This is not evidence that either system lacks statement binding internally.
- This is not a matched performance benchmark.
- This is not a claim that future public artifacts will fail the relabeling
  benchmark.
