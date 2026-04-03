# AI Review Bots Playbook (April 2026)

This repo uses **CodeRabbit** and **Greptile** with repo-scoped configuration to improve review quality and reduce noise.

## Why these settings

### CodeRabbit

- Keep config in version control via `.coderabbit.yaml` at repo root.
- Use **targeted path instructions** as a supplement, not a replacement for default review behavior.
- Use **path filters** to exclude generated/artifact paths for faster, cleaner reviews.
- Keep auto-review enabled on incremental pushes; skip drafts and bot-authored PRs.

### Greptile

- Prefer `.greptile/` over single-file `greptile.json` for scalable, directory-scoped config.
- Start with balanced strictness (`strictness: 2`) and tune based on team feedback.
- Limit comment types to logic/syntax for higher signal (style noise reduced).
- Use `triggerOnUpdates: true` and status checks for consistent PR feedback.
- Use `rules.md` + structured `rules` + `files.json` references for context-aware reviews.

## Sources (official docs)

### CodeRabbit

- YAML config and precedence: https://docs.coderabbit.ai/getting-started/yaml-configuration
- Repository settings & precedence: https://docs.coderabbit.ai/guides/repository-settings
- Path instructions and filters: https://docs.coderabbit.ai/configuration/path-instructions
- Automatic review controls: https://docs.coderabbit.ai/configuration/auto-review
- AST-based instructions (optional advanced): https://docs.coderabbit.ai/configuration/ast-grep-instructions

### Greptile

- `.greptile/` configuration (recommended): https://www.greptile.com/docs/code-review/greptile-config
- `.greptile/` file reference: https://www.greptile.com/docs/code-review/greptile-config-reference
- `greptile.json` reference and parameters: https://www.greptile.com/docs/code-review-bot/greptile-json
- Nitpick controls / strictness / triggers: https://www.greptile.com/docs/code-review/controlling-nitpickiness
- Team learning and noise reduction behavior: https://www.greptile.com/docs/how-greptile-works/nitpicks
- Best-practices guide: https://www.greptile.com/docs/code-review-bot/best-practices

## Operational Notes

- Keep rule changes small and review their effect over 1-2 weeks.
- Prefer scoped rules over global blanket instructions.
- If review noise rises, increase Greptile strictness and narrow bot instructions.
- If critical issues are missed, add focused path/rule instructions + regression tests.
