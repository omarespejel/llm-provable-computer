# zkAI snarkjs external-adapter gate - 2026-04-29

## Purpose

Test whether the zkAI statement-envelope result from the EZKL adapter repeats on
a second external proof stack with a different verifier and artifact shape.

The target is a tiny Circom/snarkjs Groth16 verifier surface:

- circuit: `square.circom`, proving `y = x * x`,
- public signals: `["49", "7"]`,
- verifier: `npx -y snarkjs@0.7.6 groth16 verify`,
- verifier-facing artifacts only: `proof.json`, `public.json`, and
  `verification_key.json`.

This is a statement-binding benchmark, not a performance benchmark and not a
snarkjs security audit.

## Checked artifacts

Artifact directory:

`docs/engineering/evidence/zkai-snarkjs-statement-envelope-2026-04/`

Checked files:

- `square.circom`
- `input.json`
- `verification_key.json`
- `proof.json`
- `public.json`
- `metadata.json`

Generated benchmark evidence:

- `docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.json`
- `docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.tsv`

Generator commit recorded in evidence:

`56c3cab80fee01f763a61a2a9f60ae9674a4331a`

## Result

Two adapters were tested against the same baseline proof and the same mutation
set.

| Adapter | Baseline | Mutations rejected | Gate |
|---|---:|---:|---|
| `snarkjs-proof-only` | accepted | 1 / 14 | NO-GO for statement-bound relabeling |
| `snarkjs-statement-envelope` | accepted | 14 / 14 | GO for external proof-backed statement envelope |

The raw proof-only path rejects the mutated public signal, as it should, but
accepts metadata-only relabeling because those labels are outside the raw
Groth16 proof acceptance path. This is not a snarkjs bug and not a snarkjs
security finding. It is the expected boundary between proof validity and
application statement binding.

The statement-envelope path first checks the statement commitment, artifact
hashes, label policy, verifier domain, verification-key binding, setup binding,
proof hash, and public-signal digest, and then delegates proof validity to
snarkjs. Under that adapter, all 14 mutations are rejected.

## Interpretation

This is the second useful external-adapter result for the zkAI relabeling line.
Together with the EZKL adapter, it supports the adapter-level verifier-boundary
claim:

> Proof validity and statement binding are distinct verifier layers.

The result is deliberately narrow. It does not say that raw snarkjs or raw EZKL
are wrong. Both raw verifiers validate the mathematical proof objects they are
given. The result says that a zkAI system needs an explicit statement-binding
receipt if it wants model/input/output/config/setup/domain relabeling rejection
to be a verifier-level property.

## Reproduction

Environment used:

- Python `3.12.11`
- circom `2.0.9` for artifact generation
- snarkjs `0.7.6` through `npx -y snarkjs@0.7.6`
- macOS arm64

Regenerate the benchmark evidence:

`ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON` is the portable command vector recorded in
the checked evidence.

```bash
export ZKAI_SNARKJS_BENCHMARK_COMMAND_JSON='["env","ZKAI_SNARKJS_BENCHMARK_GIT_COMMIT=56c3cab80fee01f763a61a2a9f60ae9674a4331a","python3","scripts/zkai_snarkjs_statement_envelope_benchmark.py","--write-json","docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.json","--write-tsv","docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.tsv"]'
ZKAI_SNARKJS_BENCHMARK_GIT_COMMIT=56c3cab80fee01f763a61a2a9f60ae9674a4331a \
  python3.12 scripts/zkai_snarkjs_statement_envelope_benchmark.py \
  --write-json docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.json \
  --write-tsv docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.tsv
```

The checked proof artifacts were generated with this local command shape:

```bash
circom square.circom --r1cs --wasm --sym -o .
npx -y snarkjs@0.7.6 powersoftau new bn128 8 pot8_0000.ptau -v
npx -y snarkjs@0.7.6 powersoftau contribute pot8_0000.ptau pot8_0001.ptau --name="ptvm test" -v -e="ptvm deterministic local test entropy"
npx -y snarkjs@0.7.6 powersoftau prepare phase2 pot8_0001.ptau pot8_final.ptau -v
npx -y snarkjs@0.7.6 groth16 setup square.r1cs pot8_final.ptau square_0000.zkey
npx -y snarkjs@0.7.6 zkey contribute square_0000.zkey square_final.zkey --name="ptvm test" -v -e="ptvm deterministic zkey entropy"
npx -y snarkjs@0.7.6 zkey export verificationkey square_final.zkey verification_key.json
node square_js/generate_witness.js square_js/square.wasm input.json witness.wtns
npx -y snarkjs@0.7.6 groth16 prove square_final.zkey witness.wtns proof.json public.json
npx -y snarkjs@0.7.6 groth16 verify verification_key.json public.json proof.json
```

Only verifier-facing artifacts are checked in. The proving key, witness, and
powers-of-tau files are intentionally omitted from this repository because they
are not needed to rerun the relabeling verifier benchmark.

Final validation used for this gate:

```bash
python3.12 -m unittest \
  scripts.tests.test_zkai_snarkjs_statement_envelope_benchmark \
  scripts.tests.test_zkai_ezkl_statement_envelope_benchmark \
  scripts.tests.test_zkai_relabeling_benchmark_suite \
  scripts.tests.test_agent_step_receipt_relabeling_harness
python3.12 scripts/zkai_snarkjs_statement_envelope_benchmark.py --json
python3.12 scripts/paper/paper_preflight.py --repo-root .
git diff --check
```

## Non-claims

- This is not a snarkjs security audit.
- This is not a system ranking.
- This is not a performance benchmark.
- The proof-only NO-GO is limited to metadata outside the raw snarkjs Groth16
  acceptance path.
- The statement-envelope GO is an adapter result, not a claim that raw snarkjs
  proves model/input/output labels by itself.
- This toy square circuit is not a transformer proof.

## Follow-up

The next useful extension is the Stwo-native statement-bound transformer
primitive tracked by #310. The external-adapter lesson should be applied there:
the proof must be accepted only under a receipt that binds model/primitive ID,
weights or circuit commitment, input commitment, output commitment, config,
backend version, verifier domain, and public-instance digest.
