#!/usr/bin/env python3
"""Publication preflight checks for docs/paper artifacts.

Checks:
1) citation integrity (numeric in-text citations must exist in local references section),
2) immutable-link policy for this repository's GitHub links (commit-pinned only),
3) figure/link cross-reference existence for local file links,
4) source-note presence in appendix-system-comparison.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass, field
from urllib.parse import urlparse


PAPER_FILES = [
    "docs/paper/stark-transformer-alignment-2026.md",
    "docs/paper/proof-carrying-decoding-2026.md",
    "docs/paper/appendix-system-comparison.md",
    "docs/paper/appendix-scaling-companion.md",
    "docs/paper/appendix-backend-artifact-comparison.md",
    "docs/paper/PUBLICATION_RELEASE.md",
    "docs/paper/submission-v3-2026-04-09/BUNDLE_INDEX.md",
    "docs/paper/submission-v3-2026-04-09/REPRODUCIBILITY_NOTE.md",
]

LOCAL_REPOS = {
    ("omarespejel", "llm-provable-computer"),
    ("omarespejel", "provable-transformer-vm"),
}


@dataclass
class Findings:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def is_commitish(ref: str) -> bool:
    # GitHub short/long SHA references.
    return bool(re.fullmatch(r"[0-9a-f]{7,40}", ref))


def split_body_refs(text: str) -> tuple[str, str]:
    marker = "\n## References\n"
    if marker in text:
        return text.split(marker, 1)
    return text, ""


def parse_reference_ids(refs_text: str) -> set[int]:
    ids: set[int] = set()
    for line in refs_text.splitlines():
        m_num = re.match(r"^\s*(\d+)\.\s", line)
        if m_num:
            ids.add(int(m_num.group(1)))
            continue
        m_br = re.match(r"^\s*-\s*\[(\d+)\]\s", line)
        if m_br:
            ids.add(int(m_br.group(1)))
    return ids


def expand_citation_token(token: str) -> list[int]:
    out: list[int] = []
    for part in re.split(r"\s*,\s*", token):
        if "-" in part:
            a, b = re.split(r"\s*-\s*", part, 1)
            if a.isdigit() and b.isdigit():
                ai, bi = int(a), int(b)
                if ai <= bi:
                    out.extend(range(ai, bi + 1))
                else:
                    out.extend(range(bi, ai + 1))
            continue
        if part.isdigit():
            out.append(int(part))
    return out


def parse_citation_ids(body_text: str) -> set[int]:
    ids: set[int] = set()
    # Numeric citation styles: [1], [1, 2], [24-31]
    for m in re.finditer(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]", body_text):
        for n in expand_citation_token(m.group(1)):
            ids.add(n)
    return ids


def extract_markdown_links(text: str) -> list[str]:
    links: list[str] = []
    # Inline image + inline links.
    for pat in (
        r"!\[[^\]]*\]\(([^)]+)\)",
        r"(?<!!)\[[^\]]*\]\(([^)]+)\)",
        r"<(https?://[^>\s]+)>",
    ):
        for m in re.finditer(pat, text):
            links.append(m.group(1).strip())
    return links


def check_local_relative_links(
    file_path: pathlib.Path, links: list[str], findings: Findings
) -> None:
    for link in links:
        if link.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        # Skip title fragment.
        raw = link.split("#", 1)[0].strip()
        if not raw:
            continue
        target = (file_path.parent / raw).resolve()
        if not target.exists():
            findings.error(
                f"{file_path}: local link target does not exist: {link}"
            )


def local_repo_url_path(url: str) -> tuple[str, str, str] | None:
    """Return (kind, ref, path) for local repo GitHub/raw URL or None."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path_parts = [p for p in parsed.path.split("/") if p]

    if host == "github.com":
        if len(path_parts) < 5:
            return None
        owner, repo, kind, ref = path_parts[:4]
        if (owner, repo) not in LOCAL_REPOS or kind not in {"blob", "tree"}:
            return None
        rel_path = "/".join(path_parts[4:])
        return kind, ref, rel_path

    if host == "raw.githubusercontent.com":
        if len(path_parts) < 4:
            return None
        owner, repo, ref = path_parts[:3]
        if (owner, repo) not in LOCAL_REPOS:
            return None
        rel_path = "/".join(path_parts[3:])
        return "raw", ref, rel_path

    return None


def check_immutable_local_repo_links(
    source_file: pathlib.Path, links: list[str], repo_root: pathlib.Path, findings: Findings
) -> None:
    for link in links:
        if not link.startswith(("http://", "https://")):
            continue
        parsed = local_repo_url_path(link)
        if not parsed:
            continue
        _kind, ref, rel_path = parsed
        if not is_commitish(ref):
            findings.error(
                f"{source_file}: local repository link is not commit-pinned: {link}"
            )
        if rel_path:
            local_target = repo_root / rel_path
            if not local_target.exists():
                findings.error(
                    f"{source_file}: referenced local-repo path not found in workspace: {link}"
                )


def run_file_checks(file_path: pathlib.Path, repo_root: pathlib.Path, findings: Findings) -> None:
    text = file_path.read_text(encoding="utf-8")
    body, refs = split_body_refs(text)
    ref_ids = parse_reference_ids(refs)
    cite_ids = parse_citation_ids(body)

    # Only enforce citation-ID integrity when the file has a local References section.
    if ref_ids:
        missing = sorted(n for n in cite_ids if n not in ref_ids)
        if missing:
            findings.error(
                f"{file_path}: citations reference missing IDs in local References section: {missing}"
            )
        unused = sorted(n for n in ref_ids if n not in cite_ids)
        if unused:
            findings.warn(
                f"{file_path}: unused reference IDs (review for hygiene): {unused}"
            )

    links = extract_markdown_links(text)
    check_local_relative_links(file_path, links, findings)
    check_immutable_local_repo_links(file_path, links, repo_root, findings)


def check_appendix_source_note(repo_root: pathlib.Path, findings: Findings) -> None:
    path = repo_root / "docs/paper/appendix-system-comparison.md"
    text = path.read_text(encoding="utf-8")
    if "Sources:" not in text:
        findings.error(f"{path}: missing standalone source note (expected 'Sources: ...').")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run publication preflight checks for docs/paper.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root path (default: current directory).",
    )
    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo_root).resolve()
    findings = Findings()

    for rel in PAPER_FILES:
        path = repo_root / rel
        if not path.exists():
            findings.error(f"missing expected paper file: {path}")
            continue
        run_file_checks(path, repo_root, findings)

    check_appendix_source_note(repo_root, findings)

    if findings.warnings:
        print("Warnings:")
        for w in findings.warnings:
            print(f"  - {w}")

    if findings.errors:
        print("Errors:")
        for e in findings.errors:
            print(f"  - {e}")
        return 1

    print("paper preflight: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
