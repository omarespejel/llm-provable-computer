# Release gates

This directory holds the machine-applicable repository policy that backs the
publication-grade release gate. None of the files here ship in the published
artifact; they exist to make the policy reviewable in code review and replayable
on any new fork.

GitHub Actions is intentionally disabled at the repository level for cost
reasons. The full policy lives in `local-only-policy.md`. The short version:

- The release gate runs locally via `scripts/local_release_gate.sh`.
- A pre-push hook (`pre-push-hook.sh` in this directory) refuses any push
  whose local gate fails.
- Server-side enforcement on `main` is reduced to repo policy that does not
  consume Actions minutes: a pull request must be opened before any merge,
  linear history, no force-push, no deletion.
- AI commenters (CodeRabbit, Greptile, pr-agent) run via webhooks and are
  unaffected.

## Branch-protection ruleset

`branch-protection-ruleset.json` is the GitHub Repository Ruleset that the
`main` branch is governed by. Create the ruleset with:

```bash
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  /repos/omarespejel/provable-transformer-vm/rulesets \
  --input docs/engineering/release-gates/branch-protection-ruleset.json
```

Update an existing ruleset (this repo uses id `15398447`):

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/omarespejel/provable-transformer-vm/rulesets/15398447 \
  --input docs/engineering/release-gates/branch-protection-ruleset.json
```

After applying, confirm with:

```bash
gh api /repos/omarespejel/provable-transformer-vm/rulesets
```

The ruleset enforces:

- no deletion of `main`
- no force-push / non-fast-forward updates
- linear history
- a pull request must be opened before any merge into `main` (so AI
  commenters fire), but no review approval is required to merge

`required_status_checks` and `required_signatures` are intentionally NOT in
the ruleset. Status checks would block on the now-disabled Actions; signed
commits would block every merge on a solo repo without adding meaningful
security. Both are easy to re-introduce later if the project picks up
external collaborators or re-enables Actions; the change is one rule entry
plus a re-apply of the JSON.
