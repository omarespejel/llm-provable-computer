# Release gates

This directory holds the machine-applicable repository policy that backs the
publication-grade release gate. None of the files here ship in the published
artifact; they exist to make the policy reviewable in code review and replayable
on any new fork.

## Branch-protection ruleset

`branch-protection-ruleset.json` is the GitHub Repository Ruleset that the
`main` branch is governed by. Apply or update it with:

```bash
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  /repos/omarespejel/provable-transformer-vm/rulesets \
  --input docs/engineering/release-gates/branch-protection-ruleset.json
```

After applying, confirm with:

```bash
gh api /repos/omarespejel/provable-transformer-vm/rulesets
gh api /repos/omarespejel/provable-transformer-vm/rules/branches/main
```

The ruleset enforces:

- no deletion of `main`
- no force-push / non-fast-forward updates
- linear history
- signed commits
- required pull request before merge, with review-thread resolution
- required status checks: `lightweight PR lib smoke`, `hardening contract`,
  and `paper preflight`

If a check name in `.github/workflows/` changes, update both the workflow and
this file in the same commit so the ruleset stays in lockstep with CI.
