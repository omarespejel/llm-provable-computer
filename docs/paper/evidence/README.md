This directory stores mutable external evidence that the paper freezes into repo-local snapshots.

Contents:

- `web-2026-04-06/`: HTML snapshots plus `manifest.json` and `manifest.tsv` for the public web pages cited in the paper's systems and infrastructure sections.
- `gemma-config-snapshots/`: extracted parameter fields used by Appendix B4 and Appendix B5, derived from commit-pinned public mirror configs together with their source URLs and SHA-256 digests.

Generation scripts:

- `scripts/paper/archive_supporting_web_evidence.py`
- `scripts/paper/extract_gemma_config_snapshots.py`

These files are supporting evidence only. The main paper continues to treat archival literature, official engineering/product materials, and commit-pinned repository artifacts as distinct evidence classes.
