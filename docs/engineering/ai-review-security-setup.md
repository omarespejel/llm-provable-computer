# AI Review And Security Setup

This note records the first-party Anthropic and OpenAI setup that now backs this repository. It is intentionally narrow: it covers AI review and security tooling for ongoing engineering work, not publication claims.

As of 2026-04-21, the repository-side pieces checked into source control are:

- `AGENTS.md`: project instructions for OpenAI Codex.
- `.codex/config.toml`: shared Codex defaults for trusted project sessions.
- `CLAUDE.md`: shared project instructions for Claude Code.
- `REVIEW.md`: review-only instructions for Anthropic Code Review.
- `.claude/settings.json`: shared Claude Code deny rules for common secret paths and raw network-fetch commands.

## Anthropic: what is supported here

Anthropic’s official repository-facing control points are:

- `CLAUDE.md` for shared project context.
- `REVIEW.md` for review-only guidance in Claude Code Review.
- `.claude/settings.json` for shared project permissions.
- the Claude GitHub App / Claude Code Review admin flow for GitHub pull request reviews.

The checked-in files above give Claude local and review-time guidance immediately. The GitHub-side review product still requires organization-admin setup.

### Manual Anthropic admin steps

1. Open `claude.ai/admin-settings/claude-code` and go to the Code Review section.
2. Click `Setup` and install the Claude GitHub App for the organization.
3. Grant the app access to this repository. Anthropic documents `Contents`, `Issues`, and `Pull requests` read/write permissions for the app.
4. Set review behavior for this repository. For this codebase, `After every push` is the right default because proof and verifier changes are usually incremental and reviewer state should refresh on each push.
5. Set an organization spend cap for Code Review if you want a hard ceiling.

### Optional Anthropic local-policy rollout

If the team uses Claude Code broadly, add managed settings in Claude admin to mirror the repository policy:

- deny reads of `.env`, `secrets/**`, and similar secret paths
- deny raw fetch/exfiltration commands unless explicitly needed
- use fail-closed startup only if connectivity to `api.anthropic.com` is reliable

For stronger endpoint enforcement than server-managed settings provide, use Anthropic endpoint-managed settings on MDM-managed devices.

## OpenAI Codex: what is supported here

OpenAI’s official repository-facing control points are:

- `AGENTS.md` for persistent project instructions.
- `.codex/config.toml` for shared project defaults when the repo is trusted.
- ChatGPT workspace settings and GitHub connector setup for Codex cloud code review.
- Codex Security, which connects to GitHub repositories, builds a threat model, validates findings in isolation, and proposes patches for human review.

The checked-in Codex files now give local Codex sessions a shared default posture:

- `approval_policy = "on-request"`
- `sandbox_mode = "workspace-write"`
- `web_search = "cached"`
- `model = "gpt-5.4"`
- `model_reasoning_effort = "high"`

### Manual OpenAI admin steps

1. In ChatGPT workspace settings, enable Codex cloud and the ChatGPT GitHub Connector.
2. Connect this repository as a Codex environment.
3. In `Settings -> Code review`, enable repository-level Codex Code Review and choose the trigger policy.
4. For security review, go to `chatgpt.com/codex/security`, enable this repository, and let the first scan build the repo-specific threat model.
5. Refine the Codex Security threat model with the same trust boundaries we already track in `docs/security/threat-model.md`.

### Recommended OpenAI rollout for this repository

- Use Codex Code Review on pull requests that touch trusted-core paths.
- Use Codex Security on the default branch and on periodic rescans, not as a replacement for unit tests or local hardening evidence.
- Review all generated patches in the normal PR workflow. OpenAI’s documentation is explicit that Codex Security proposes patches for human review; it does not auto-modify code.

## Recommended operating model

For this repository, the strongest combined setup is:

- Keep CodeRabbit, Greptile, and Qodo as always-on broad PR reviewers.
- Use Anthropic Code Review as a repo-native inline reviewer with `REVIEW.md` tuned to proof-soundness and regression finding.
- Use OpenAI Codex Code Review as a second first-party reviewer on high-risk pull requests.
- Use OpenAI Codex Security for repository-level threat modeling, vulnerability validation, and patch proposals.
- Keep merge decisions gated by local evidence, CI, and the existing hardening policy rather than by any single AI reviewer.

## Why the checked-in configuration stays minimal

The repository files only express the controls that are both officially documented and safe to share in source control. Organization-level secrets, GitHub App installation, RBAC, spend caps, and cloud-review toggles remain admin-owned configuration outside the repository.
