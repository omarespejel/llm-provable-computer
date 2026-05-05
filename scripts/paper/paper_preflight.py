#!/usr/bin/env python3
"""Publication preflight checks for the active docs/paper artifacts.

The preflight covers the current two-paper presentation bundle, including the
Transformer/STARK alignment paper, the Tablero paper, supporting appendices, and
publication metadata files.  It fails closed on:

1) missing active paper or metadata files,
2) missing local numeric citation targets when a file has a References section,
3) unpinned GitHub links to this repository or its predecessor repository,
4) broken local Markdown links and figure references,
5) missing primary-presentation links to the Tablero abstract, appendices, and
   checked figures,
6) missing source-note text in the system-comparison appendix,
7) missing active S-two bundle indices or timing/size/hash drift inside those
   frozen artifact indices,
8) unresolved hard publication snapshot placeholders,
9) incomplete Paper 3 proof-carrying composition claim-evidence metadata, and
10) paper claim-language overreach around recursion, compression, PCS, and full
    inference claims.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import sys
from dataclasses import dataclass, field
from urllib.parse import urlparse


PUBLICATION_METADATA_FILES = [
    "docs/paper/PUBLICATION_RELEASE.md",
    "docs/paper/submission-v4-2026-04-11/BUNDLE_INDEX.md",
    "docs/paper/submission-v4-2026-04-11/REPRODUCIBILITY_NOTE.md",
]

PAPER_FILES = [
    "docs/paper/stark-transformer-alignment-2026.md",
    "docs/paper/abstract-tablero-2026.md",
    "docs/paper/tablero-typed-verifier-boundaries-2026.md",
    "docs/paper/appendix-tablero-claim-boundary.md",
    "docs/paper/appendix-methodology-and-reproducibility.md",
    "docs/paper/appendix-system-comparison.md",
    *PUBLICATION_METADATA_FILES,
]

PRIMARY_PRESENTATION_FILES = [
    "docs/paper/abstract-tablero-2026.md",
    "docs/paper/tablero-typed-verifier-boundaries-2026.md",
    "docs/paper/appendix-tablero-claim-boundary.md",
    "docs/paper/appendix-methodology-and-reproducibility.md",
    "docs/paper/appendix-system-comparison.md",
    "docs/paper/PUBLICATION_RELEASE.md",
    "docs/paper/README.md",
]

SNAPSHOT_FIELD_PREFIXES = (
    "Canonical publication snapshot",
    "Canonical repository snapshot",
)

HARD_SNAPSHOT_PLACEHOLDER_TOKENS = ("TBD_SNAPSHOT_SHA",)
SOFT_SNAPSHOT_PLACEHOLDER_TOKENS = (
    "PENDING_SNAPSHOT_SHA",
    "Pending.",
    "Pending:",
)

LOCAL_REPOS = {
    ("omarespejel", "llm-provable-computer"),
    ("omarespejel", "provable-transformer-vm"),
}

PAPER3_CLAIM_EVIDENCE_FILE = "docs/engineering/paper3-claim-evidence.yml"
TABLERO_CLAIM_EVIDENCE_FILE = "docs/engineering/tablero-claim-evidence.yml"

REQUIRED_PAPER3_CLAIM_IDS = {
    "phase38_source_validated_receipt_binding",
    "phase38_composition_continuity",
    "phase38_shared_lookup_source_chain_and_template_identity",
    "phase38_packaging_baseline",
}

REQUIRED_TABLERO_CLAIM_IDS = {
    "tablero_statement_preservation_theorem",
    "tablero_cross_family_replay_avoidance",
    "tablero_scaling_law_fit",
    "tablero_optimized_replay_redteam",
    "tablero_second_boundary_and_compactness_no_go",
    "tablero_statement_binding_extension",
}

CLAIM_EVIDENCE_REQUIRED_SCALARS = ("id", "claim")
CLAIM_EVIDENCE_REQUIRED_LISTS = (
    "paper_locations",
    "implementation",
    "specs",
    "positive_tests",
    "negative_tests",
    "evidence_commands",
    "non_claims",
)
PAPER3_CLAIM_EVIDENCE_REQUIRED_LISTS = CLAIM_EVIDENCE_REQUIRED_LISTS + (
    "schemas",
    "artifact_files",
    "artifact_hashes",
    "fuzz_or_formal",
)
TABLERO_CLAIM_EVIDENCE_REQUIRED_LISTS = (
    "paper_locations",
    "specs",
    "evidence_files",
    "evidence_commands",
    "non_claims",
)
# Tablero claims span theorem statements, measured results, red-team checks, and
# explicit no-go boundaries. Implementation/test keys are optional and still
# validated when present; forcing them onto theorem-only claims would create
# false precision rather than a stronger evidence ledger.
TABLERO_CLAIM_EVIDENCE_PATH_KEYS = (
    "paper_locations",
    "specs",
    "evidence_files",
)
NON_PATH_EVIDENCE_NOTE_PATH_KEYS = frozenset(("schemas", "artifact_files"))
EXPERIMENTAL_EVIDENCE_PATH_KEYS = (
    "paper_locations",
    "implementation",
    "specs",
    "schemas",
    "artifact_files",
    "evidence_files",
)
EXPERIMENTAL_NON_DEFAULT_TOKENS = (
    "does not claim default",
    "does not claim publication-default",
    "not default",
    "not a default",
    "non-default",
    "publication-default",
)

CLAIM_LANGUAGE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "recursive proof",
        (
            "not",
            "no",
            "without",
            "pre-recursive",
            "non-claim",
            "non-goal",
            "boundary",
            "wrong",
        ),
    ),
    (
        "proves model inference",
        (
            "bounded",
            "specific",
            "not",
            "does not",
            "non-claim",
            "boundary",
        ),
    ),
    (
        "semantic equivalence",
        ("bounded",),
    ),
    (
        "preserves accuracy",
        (
            "bounded",
            "budget",
            "evidence",
            "measured",
            "not",
            "does not",
        ),
    ),
    (
        "same model behavior",
        (
            "bounded",
            "budget",
            "evidence",
            "not",
            "does not",
            "non-claim",
        ),
    ),
    (
        "supply-chain attestation",
        (
            "not",
            "does not",
            "bounded",
            "gap",
            "boundary",
            "missing",
            "non-claim",
        ),
    ),
    (
        "supply-chain attestations",
        (
            "not",
            "does not",
            "bounded",
            "gap",
            "boundary",
            "missing",
            "non-claim",
        ),
    ),
)

# Match `Phase<N>` / `phase<N>` / `Phase<N><suffix>` (e.g., `Phase44D`) when it
# appears as standalone prose, but NOT when it appears inside a hyphenated or
# underscored technical identifier (e.g.,
# `stwo-phase12-decoding-family-v10-carry-aware-experimental` or
# `phase30_decoding_step_envelope_manifest`). The intent is to flag prose
# leaks of internal naming, not to ban exact crypto identifiers that
# paper-facing claims need to pin verbatim. The negative lookbehind/ahead
# excludes word characters and hyphen so identifiers stay intact.
INTERNAL_PHASE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9\-_])[Pp]hase\d+[A-Za-z]?(?![A-Za-z0-9\-_])"
)
REQUIRED_PRIMARY_LINKS = {
    "docs/paper/tablero-typed-verifier-boundaries-2026.md": [
        "abstract-tablero-2026.md",
        "appendix-methodology-and-reproducibility.md",
        "figures/tablero-results-overview-2026-04.svg",
        "figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg",
        "figures/tablero-replay-baseline-breakdown-2026-04.svg",
    ],
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
            a, b = re.split(r"\s*-\s*", part, maxsplit=1)
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
        if len(path_parts) < 4:
            return None
        owner, repo, kind, ref = path_parts[:4]
        if (owner, repo) not in LOCAL_REPOS or kind not in {"blob", "tree"}:
            return None
        rel_path = "/".join(path_parts[4:]) if len(path_parts) > 4 else ""
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
        kind, ref, rel_path = parsed
        if not is_commitish(ref):
            findings.error(
                f"{source_file}: local repository link is not commit-pinned: {link}"
            )
        if kind == "blob" and not rel_path:
            findings.error(
                f"{source_file}: local repository blob link has no file path: {link}"
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


def check_primary_presentation_guardrails(repo_root: pathlib.Path, findings: Findings) -> None:
    for rel_path in PRIMARY_PRESENTATION_FILES:
        path = repo_root / rel_path
        if not path.exists():
            findings.error(f"{path}: missing primary presentation file.")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.error(f"{path}: failed to read primary presentation file: {exc}")
            continue
        match = INTERNAL_PHASE_PATTERN.search(text)
        if match:
            findings.error(
                f"{path}: internal phase-style terminology leaked into primary presentation copy: {match.group(0)}"
            )
        for required_link in REQUIRED_PRIMARY_LINKS.get(rel_path, []):
            if required_link not in text:
                findings.error(
                    f"{path}: missing required presentation link `{required_link}`."
                )


def check_appendix_source_note(repo_root: pathlib.Path, findings: Findings) -> None:
    path = repo_root / "docs/paper/appendix-system-comparison.md"
    text = path.read_text(encoding="utf-8")
    if "Sources:" not in text:
        findings.error(f"{path}: missing standalone source note (expected 'Sources: ...').")


def check_publication_snapshot_placeholders(
    repo_root: pathlib.Path, findings: Findings
) -> None:
    for rel_path in PUBLICATION_METADATA_FILES:
        path = repo_root / rel_path
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.error(
                f"{path}: failed to read publication metadata for snapshot placeholder checks: {exc}"
            )
            continue
        for token in HARD_SNAPSHOT_PLACEHOLDER_TOKENS:
            if token in text:
                findings.error(
                    f"{path}: unresolved publication snapshot placeholder {token!r}; "
                    "replace it before paper preflight."
                )
        snapshot_field_text = "\n".join(iter_snapshot_field_lines(text))
        for token in SOFT_SNAPSHOT_PLACEHOLDER_TOKENS:
            if token in snapshot_field_text:
                findings.error(
                    f"{path}: unresolved publication snapshot placeholder {token!r}; "
                    "replace it before paper preflight."
                )


def unquote_claim_evidence_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_claim_evidence_records(
    path: pathlib.Path, findings: Findings
) -> list[dict[str, object]]:
    """Parse the restricted YAML shape used by paper-claim-evidence ledgers.

    This is intentionally not a general YAML parser. The evidence ledger uses a
    small stdlib-friendly subset so preflight does not grow a PyYAML dependency.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        findings.error(f"{path}: failed to read claim evidence matrix: {exc}")
        return []

    records: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    current_list_key: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- id:"):
            value = unquote_claim_evidence_scalar(stripped.split(":", 1)[1])
            current = {"id": value}
            records.append(current)
            current_list_key = None
            continue
        if current is None:
            findings.error(
                f"{path}:{line_number}: claim evidence content must start with `- id:`"
            )
            continue
        if stripped.startswith("- "):
            if current_list_key is None:
                findings.error(
                    f"{path}:{line_number}: list item has no active claim evidence key"
                )
                continue
            items = current.setdefault(current_list_key, [])
            if not isinstance(items, list):
                findings.error(
                    f"{path}:{line_number}: `{current_list_key}` cannot mix scalar and list values"
                )
                continue
            items.append(unquote_claim_evidence_scalar(stripped[2:]))
            continue
        match = re.match(r"^([a-z_]+):\s*(.*)$", stripped)
        if not match:
            findings.error(
                f"{path}:{line_number}: unsupported claim evidence syntax: {stripped}"
            )
            continue
        key, value = match.groups()
        if value:
            current[key] = unquote_claim_evidence_scalar(value)
            current_list_key = None
        else:
            current[key] = []
            current_list_key = key

    return records


def iter_code_and_test_files(repo_root: pathlib.Path):
    for rel_root in ("src", "tests", "scripts", "fuzz", "tools"):
        root = repo_root / rel_root
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".rs", ".py", ".md", ".sh", ".yml", ".json"}:
                yield path


def find_repo_tokens(repo_root: pathlib.Path, tokens: set[str]) -> set[str]:
    remaining = {token for token in tokens if token}
    found: set[str] = set()
    if not remaining:
        return found

    for path in iter_code_and_test_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeError):
            continue
        present = {token for token in remaining if token in text}
        if present:
            found.update(present)
            remaining.difference_update(present)
            if not remaining:
                break
    return found


def split_evidence_path_anchor(entry: str) -> tuple[str, str | None]:
    path_part, fragment = (
        entry.split("#", 1) if "#" in entry else (entry, None)
    )
    if ":" not in path_part:
        return path_part, fragment or None
    rel_path, anchor = path_part.rsplit(":", 1)
    if "/" not in rel_path and not rel_path.endswith((".rs", ".py", ".md", ".json", ".yml")):
        return path_part, fragment or None
    return rel_path, anchor or fragment or None


def is_explicit_non_applicable_entry(entry: str) -> bool:
    return entry.strip().lower().startswith("not applicable:")


def resolve_repo_relative_path(
    repo_root: pathlib.Path, rel_path: str
) -> tuple[pathlib.Path | None, str | None]:
    relative_path = pathlib.Path(rel_path)
    windows_path = pathlib.PureWindowsPath(rel_path)
    if relative_path.is_absolute() or windows_path.is_absolute():
        return None, "path must be repo-relative"
    if (
        ".." in relative_path.parts
        or ".." in windows_path.parts
    ):
        return None, "path must be repo-relative (must not contain `..`)"

    try:
        root = repo_root.resolve()
        target = (root / relative_path).resolve()
    except (OSError, RuntimeError) as exc:
        return None, f"failed to resolve path: {exc}"
    try:
        target.relative_to(root)
    except ValueError:
        return None, "path escapes repo root"
    return target, None


def check_claim_evidence_path_anchor(
    repo_root: pathlib.Path,
    evidence_path: pathlib.Path,
    claim_id: str,
    key: str,
    entry: str,
    findings: Findings,
) -> None:
    if is_explicit_non_applicable_entry(entry):
        if key not in NON_PATH_EVIDENCE_NOTE_PATH_KEYS:
            findings.error(
                f"{evidence_path}: claim `{claim_id}` `{key}` uses `Not applicable:` "
                "where a repo-relative path is required"
            )
            return
        if not entry.partition(":")[2].strip():
            findings.error(
                f"{evidence_path}: claim `{claim_id}` `{key}` has empty `Not applicable:` note"
            )
        return

    rel_path, anchor = split_evidence_path_anchor(entry)
    target, path_error = resolve_repo_relative_path(repo_root, rel_path)
    if target is None:
        findings.error(
            f"{evidence_path}: claim `{claim_id}` `{key}` invalid path `{entry}`: {path_error}"
        )
        return

    if not target.exists():
        findings.error(
            f"{evidence_path}: claim `{claim_id}` `{key}` references missing path: {entry}"
        )
        return
    if anchor is None:
        return
    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        findings.error(
            f"{evidence_path}: claim `{claim_id}` `{key}` failed to read anchor path {target}: {exc}"
        )
        return
    if anchor not in text:
        findings.error(
            f"{evidence_path}: claim `{claim_id}` `{key}` anchor `{anchor}` not found in {rel_path}"
        )


def list_field(record: dict[str, object], key: str) -> list[str]:
    value = record.get(key)
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def check_experimental_evidence_boundary(
    evidence_path: pathlib.Path,
    claim_id: str,
    record: dict[str, object],
    findings: Findings,
) -> None:
    experimental_entries = [
        entry
        for key in EXPERIMENTAL_EVIDENCE_PATH_KEYS
        for entry in list_field(record, key)
        if "experimental" in entry.lower()
    ]
    if not experimental_entries:
        return

    boundary_text = " ".join(
        [str(record.get("claim", "")), *list_field(record, "non_claims")]
    ).lower()
    if "experimental" not in boundary_text:
        findings.error(
            f"{evidence_path}: claim `{claim_id}` references experimental evidence "
            "without saying the claim is experimental-scoped"
        )
    if not any(token in boundary_text for token in EXPERIMENTAL_NON_DEFAULT_TOKENS):
        findings.error(
            f"{evidence_path}: claim `{claim_id}` references experimental evidence "
            "without an explicit non-default/non-publication boundary"
        )


def fragment_scoped_search_text(text: str, anchor_offset: int) -> str | None:
    """Return the text region governed by a declared paper fragment.

    For Markdown headings, the fragment owns that heading's section up to the
    next heading at the same or a higher level. Non-heading matches are invalid
    fragment references; returning None prevents broadening the search to EOF.
    """

    line_start = text.rfind("\n", 0, anchor_offset) + 1
    line_end = text.find("\n", anchor_offset)
    if line_end < 0:
        line_end = len(text)
    heading_line = text[line_start:line_end]
    heading_match = re.match(r"^[ \t]{0,3}(#{1,6})[ \t]+", heading_line)
    if heading_match is None:
        return None

    heading_level = len(heading_match.group(1))
    remainder_start = min(line_end + 1, len(text))
    remainder = text[remainder_start:]
    next_heading = re.search(rf"(?m)^[ \t]{{0,3}}#{{1,{heading_level}}}[ \t]+", remainder)
    section_end = (
        len(text) if next_heading is None else remainder_start + next_heading.start()
    )
    return text[line_start:section_end]


def markdown_heading_title(heading_line: str) -> str | None:
    heading_match = re.match(r"^[ \t]{0,3}#{1,6}[ \t]+(.*?)[ \t]*$", heading_line)
    if heading_match is None:
        return None
    # CommonMark permits optional closing hashes, e.g. "## Title ##".
    return re.sub(r"\s+#+\s*$", "", heading_match.group(1)).strip()


def fragment_scoped_search_texts(text: str, location_anchor: str) -> list[str]:
    """Return Markdown sections whose heading title exactly matches a fragment."""

    scoped_sections: list[str] = []
    for heading_match in re.finditer(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", text):
        heading_line = heading_match.group(0)
        if markdown_heading_title(heading_line) != location_anchor:
            continue
        scoped_text = fragment_scoped_search_text(text, heading_match.start())
        if scoped_text is not None:
            scoped_sections.append(scoped_text)
    return scoped_sections


def check_paper_evidence_anchors(
    repo_root: pathlib.Path,
    evidence_path: pathlib.Path,
    records: list[dict[str, object]],
    findings: Findings,
) -> None:
    """Require each evidence-ledger claim to be cited by paper prose.

    The evidence matrix says where a claim appears. The paper text must contain
    an explicit `evidence:<claim_id>` anchor in at least one declared location,
    otherwise a strong paper claim can drift away from its implementation,
    negative controls, evidence commands, and non-claim boundary.
    """

    for record in records:
        claim_id = str(record.get("id", "")).strip()
        if not claim_id:
            continue
        anchor = f"evidence:{claim_id}"
        locations = list_field(record, "paper_locations")
        if not locations:
            continue

        searched: list[str] = []
        invalid_paths: list[str] = []
        missing_fragments: list[str] = []
        invalid_fragments: list[str] = []
        unreadable: list[str] = []
        found = False
        for entry in locations:
            rel_path, location_anchor = split_evidence_path_anchor(entry)
            searched.append(entry)
            path, path_error = resolve_repo_relative_path(repo_root, rel_path)
            if path is None:
                invalid_paths.append(f"{rel_path} ({path_error})")
                continue
            if not path.exists() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeError) as exc:
                unreadable.append(f"{rel_path} ({exc})")
                continue
            search_texts = [text]
            if location_anchor is not None:
                search_texts = fragment_scoped_search_texts(text, location_anchor)
                if not search_texts:
                    missing_fragments.append(
                        f"{entry} (heading fragment `{location_anchor}` not found)"
                    )
                    continue
            if any(
                re.search(rf"{re.escape(anchor)}(?![A-Za-z0-9_])", search_text)
                for search_text in search_texts
            ):
                found = True
                break

        if not found:
            details = f"searched locations: {searched}"
            if invalid_paths:
                details += f"; skipped invalid paths: {invalid_paths}"
            if missing_fragments:
                details += f"; missing fragments: {missing_fragments}"
            if invalid_fragments:
                details += f"; invalid fragments: {invalid_fragments}"
            if unreadable:
                details += f"; unreadable locations: {unreadable}"
            findings.error(
                f"{evidence_path}: claim `{claim_id}` is not explicitly cited by "
                f"`{anchor}` in any declared paper location; {details}"
            )


def check_claim_evidence_matrix_file(
    repo_root: pathlib.Path,
    findings: Findings,
    evidence_file: str,
    required_claim_ids: set[str],
    paper_label: str,
    required_lists: tuple[str, ...] = CLAIM_EVIDENCE_REQUIRED_LISTS,
    path_keys: tuple[str, ...] = (
        "paper_locations",
        "implementation",
        "specs",
        "schemas",
        "artifact_files",
    ),
) -> None:
    evidence_path = repo_root / evidence_file
    if not evidence_path.exists():
        findings.error(f"{evidence_path}: missing {paper_label} claim evidence matrix.")
        return

    parse_findings = Findings()
    records = parse_claim_evidence_records(evidence_path, parse_findings)
    findings.errors.extend(parse_findings.errors)
    findings.warnings.extend(parse_findings.warnings)
    if parse_findings.errors:
        return

    test_tokens = {
        test_name
        for record in records
        for key in ("positive_tests", "negative_tests")
        for test_name in list_field(record, key)
    }
    found_test_tokens = find_repo_tokens(repo_root, test_tokens)

    seen_ids: set[str] = set()
    for record in records:
        claim_id = str(record.get("id", "")).strip()
        if not claim_id:
            findings.error(f"{evidence_path}: claim evidence record has empty `id`.")
            continue
        if claim_id in seen_ids:
            findings.error(f"{evidence_path}: duplicate claim evidence id `{claim_id}`.")
        seen_ids.add(claim_id)

        for key in CLAIM_EVIDENCE_REQUIRED_SCALARS:
            value = record.get(key)
            if not isinstance(value, str) or not value.strip():
                findings.error(
                    f"{evidence_path}: claim `{claim_id}` requires non-empty scalar `{key}`."
                )

        for key in required_lists:
            values = list_field(record, key)
            if not values:
                findings.error(
                    f"{evidence_path}: claim `{claim_id}` requires at least one `{key}` entry."
                )
                continue
            if any("TODO" in value or "TBD" in value for value in values):
                findings.error(
                    f"{evidence_path}: claim `{claim_id}` `{key}` contains unresolved placeholder text."
                )

        for key in path_keys:
            for entry in list_field(record, key):
                check_claim_evidence_path_anchor(
                    repo_root, evidence_path, claim_id, key, entry, findings
                )

        for key in ("positive_tests", "negative_tests"):
            for test_name in list_field(record, key):
                if test_name not in found_test_tokens:
                    findings.error(
                        f"{evidence_path}: claim `{claim_id}` `{key}` references missing test token: {test_name}"
                    )

        for non_claim in list_field(record, "non_claims"):
            lowered = non_claim.lower()
            if "not " not in lowered and "does not" not in lowered:
                findings.error(
                    f"{evidence_path}: claim `{claim_id}` non-claim must explicitly negate an overclaim: {non_claim}"
                )
        check_experimental_evidence_boundary(evidence_path, claim_id, record, findings)

    missing_ids = sorted(required_claim_ids - seen_ids)
    extra_ids = sorted(seen_ids - required_claim_ids)
    if missing_ids:
        findings.error(
            f"{evidence_path}: missing required {paper_label} claim evidence ids: {missing_ids}"
        )
    if extra_ids:
        findings.warn(
            f"{evidence_path}: extra {paper_label} claim evidence ids not in required set: {extra_ids}"
        )
    check_paper_evidence_anchors(repo_root, evidence_path, records, findings)


def check_paper3_claim_evidence_matrix(repo_root: pathlib.Path, findings: Findings) -> None:
    check_claim_evidence_matrix_file(
        repo_root,
        findings,
        PAPER3_CLAIM_EVIDENCE_FILE,
        REQUIRED_PAPER3_CLAIM_IDS,
        "paper-3",
        PAPER3_CLAIM_EVIDENCE_REQUIRED_LISTS,
    )


def check_tablero_claim_evidence_matrix(repo_root: pathlib.Path, findings: Findings) -> None:
    check_claim_evidence_matrix_file(
        repo_root,
        findings,
        TABLERO_CLAIM_EVIDENCE_FILE,
        REQUIRED_TABLERO_CLAIM_IDS,
        "Tablero",
        TABLERO_CLAIM_EVIDENCE_REQUIRED_LISTS,
        TABLERO_CLAIM_EVIDENCE_PATH_KEYS,
    )


def paragraph_start_line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def iter_markdown_paragraphs(text: str):
    start = 0
    lines: list[str] = []
    offset = 0

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if not stripped:
            if lines:
                yield start, "".join(lines)
                lines = []
            offset += len(line)
            continue
        starts_list_item = bool(re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line))
        if starts_list_item and lines:
            yield start, "".join(lines)
            lines = []
        if not lines:
            start = offset
        lines.append(line)
        offset += len(line)

    if lines:
        yield start, "".join(lines)


def normalized_claim_tokens(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


def contains_token_sequence(tokens: list[str], phrase: str) -> bool:
    phrase_tokens = normalized_claim_tokens(phrase)
    if not phrase_tokens or len(phrase_tokens) > len(tokens):
        return False
    width = len(phrase_tokens)
    return any(
        tokens[index : index + width] == phrase_tokens
        for index in range(len(tokens) - width + 1)
    )


def check_claim_language_in_file(path: pathlib.Path, findings: Findings) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        findings.error(f"{path}: failed to read paper claim language for linting: {exc}")
        return

    for paragraph_offset, paragraph in iter_markdown_paragraphs(text):
        paragraph_tokens = normalized_claim_tokens(paragraph)
        for phrase, required_context in CLAIM_LANGUAGE_RULES:
            if not contains_token_sequence(paragraph_tokens, phrase):
                continue
            if any(
                contains_token_sequence(paragraph_tokens, token)
                for token in required_context
            ):
                continue
            line_number = paragraph_start_line(text, paragraph_offset)
            findings.error(
                f"{path}:{line_number}: overclaim-prone phrase `{phrase}` lacks nearby "
                f"bounded/non-claim context. Add one of: {', '.join(required_context)}."
            )


def discover_paper_claim_lint_files(repo_root: pathlib.Path) -> list[pathlib.Path]:
    paper_root = repo_root / "docs/paper"
    if not paper_root.exists():
        return []
    return sorted(path for path in paper_root.rglob("*.md") if path.is_file())


def check_paper_claim_language(repo_root: pathlib.Path, findings: Findings) -> None:
    paper_root = repo_root / "docs/paper"
    if not paper_root.exists():
        findings.error(f"{paper_root}: missing docs/paper directory for claim-language linting.")
        return
    paths = discover_paper_claim_lint_files(repo_root)
    if not paths:
        findings.error(
            f"{paper_root}: no markdown files found for claim-language linting."
        )
        return
    for path in paths:
        check_claim_language_in_file(path, findings)


def iter_snapshot_field_lines(text: str):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not any(stripped.startswith(prefix) for prefix in SNAPSHOT_FIELD_PREFIXES):
            continue
        yield line
        for continuation in lines[index + 1 :]:
            continuation = continuation.strip()
            if not continuation or continuation.startswith("#"):
                break
            yield continuation


def parse_markdown_table_after_heading(text: str, heading: str) -> list[list[str]]:
    lines = text.splitlines()
    start = None
    normalized_heading = heading.strip().lower()
    for i, line in enumerate(lines):
        if line.strip().lower() == normalized_heading:
            start = i + 1
            break
    if start is None:
        raise ValueError(f"heading not found: {heading}")

    rows: list[list[str]] = []
    in_table = False
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if in_table:
                break
            continue
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        in_table = True
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows.append(cells)
    return rows


def normalize_table_header(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.strip().strip("`").lower())


def parse_index_sizes(index_text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        rows = parse_markdown_table_after_heading(index_text, "## Primary Artifacts")
    except ValueError:
        return out
    if len(rows) < 3:
        return out
    header_map = {
        normalize_table_header(name): idx for idx, name in enumerate(rows[0])
    }
    try:
        artifact_idx = header_map["artifact"]
        size_idx = header_map["size (bytes)"]
    except KeyError:
        return out
    # Skip header + separator.
    for row in rows[2:]:
        if len(row) <= max(artifact_idx, size_idx):
            continue
        artifact = row[artifact_idx].strip("`")
        size_cell = row[size_idx]
        digits = re.sub(r"[^0-9]", "", size_cell)
        if not digits:
            continue
        out[artifact] = int(digits)
    return out


def parse_index_timings(index_text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        rows = parse_markdown_table_after_heading(index_text, "## Timing Summary (seconds)")
    except ValueError:
        return out
    if len(rows) < 3:
        return out
    header_map = {
        normalize_table_header(name): idx for idx, name in enumerate(rows[0])
    }
    try:
        label_idx = header_map["label"]
        seconds_idx = header_map["seconds"]
    except KeyError:
        return out
    # Skip header + separator.
    for row in rows[2:]:
        if len(row) <= max(label_idx, seconds_idx):
            continue
        label = row[label_idx].strip("`")
        seconds_cell = row[seconds_idx]
        digits = re.sub(r"[^0-9]", "", seconds_cell)
        if not digits:
            continue
        out[label] = int(digits)
    return out


def parse_index_field_values(index_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        rows = parse_markdown_table_after_heading(index_text, "## Artifact Summary")
    except ValueError:
        return out
    if len(rows) < 3:
        return out
    header_map = {
        normalize_table_header(name): idx for idx, name in enumerate(rows[0])
    }
    try:
        field_idx = header_map["field"]
        value_idx = header_map["value"]
    except KeyError:
        return out
    # Skip header + separator.
    for row in rows[2:]:
        if len(row) <= max(field_idx, value_idx):
            continue
        field = row[field_idx].strip().strip("`")
        value = row[value_idx].strip().strip("`")
        if field:
            out[field] = value
            normalized_field = normalize_table_header(field)
            out[normalized_field] = value
            if normalized_field == "artifact file":
                out["artifact_file"] = value
            elif normalized_field == "artifact size (bytes)":
                out["artifact_size_bytes"] = value
            elif normalized_field in {"sha-256", "sha256"}:
                out["sha_256"] = value
    return out


def parse_appendix_backend_rows(appendix_text: str) -> dict[tuple[str, str], tuple[int, int, int]]:
    out: dict[tuple[str, str], tuple[int, int, int]] = {}
    try:
        rows = parse_markdown_table_after_heading(
            appendix_text, "## Table C1. Frozen vanilla baseline by scope"
        )
    except ValueError:
        return out
    if len(rows) < 3:
        return out
    header_map = {
        normalize_table_header(name): idx for idx, name in enumerate(rows[0])
    }

    def first_matching_header(*aliases: str) -> int:
        for alias in aliases:
            key = normalize_table_header(alias)
            if key in header_map:
                return header_map[key]
        raise KeyError(aliases[0])

    try:
        artifact_idx = first_matching_header("Artifact")
        backend_idx = first_matching_header("Backend")
        prove_idx = first_matching_header("Prove")
        verify_idx = first_matching_header("Verify")
        size_idx = first_matching_header("Proof size", "Proof size (bytes)", "Size (bytes)")
    except KeyError:
        return out
    # Skip header + separator.
    for row in rows[2:]:
        if len(row) <= max(artifact_idx, backend_idx, prove_idx, verify_idx, size_idx):
            continue
        artifact = row[artifact_idx].strip().strip("`")
        backend = row[backend_idx].strip().strip("`")
        prove_digits = re.sub(r"[^0-9]", "", row[prove_idx])
        verify_digits = re.sub(r"[^0-9]", "", row[verify_idx])
        size_digits = re.sub(r"[^0-9]", "", row[size_idx])
        if not (prove_digits and verify_digits and size_digits):
            continue
        out[(artifact, backend)] = (int(prove_digits), int(verify_digits), int(size_digits))
    return out


def parse_appendix_transformer_bundle_rows(
    appendix_text: str,
) -> dict[tuple[str, str], tuple[int, int, int]]:
    out: dict[tuple[str, str], tuple[int, int, int]] = {}
    try:
        rows = parse_markdown_table_after_heading(
            appendix_text, "## Table C2. Frozen transformer-shaped `stwo` bundle"
        )
    except ValueError:
        return out
    if len(rows) < 3:
        return out
    header_map = {
        normalize_table_header(name): idx for idx, name in enumerate(rows[0])
    }

    def first_matching_header(*aliases: str) -> int:
        for alias in aliases:
            key = normalize_table_header(alias)
            if key in header_map:
                return header_map[key]
        raise KeyError(aliases[0])

    try:
        bundle_idx = first_matching_header("Bundle")
        backend_idx = first_matching_header("Backend")
        prepare_idx = first_matching_header("Prepare")
        verify_idx = first_matching_header("Verify")
        size_idx = first_matching_header("Artifact size", "Artifact size (bytes)", "Size (bytes)")
    except KeyError:
        return out
    # Skip header + separator.
    for row in rows[2:]:
        if len(row) <= max(bundle_idx, backend_idx, prepare_idx, verify_idx, size_idx):
            continue
        bundle = row[bundle_idx].strip().strip("`")
        backend = row[backend_idx].strip().strip("`")
        prepare_digits = re.sub(r"[^0-9]", "", row[prepare_idx])
        verify_digits = re.sub(r"[^0-9]", "", row[verify_idx])
        size_digits = re.sub(r"[^0-9]", "", row[size_idx])
        if not (prepare_digits and verify_digits and size_digits):
            continue
        out[(bundle, backend)] = (
            int(prepare_digits),
            int(verify_digits),
            int(size_digits),
        )
    return out


def _validate_table_c1_consistency(
    appendix_rows: dict[tuple[str, str], tuple[int, int, int]],
    prod_timings: dict[str, int],
    prod_sizes: dict[str, int],
    prod_index_path: pathlib.Path,
    appendix_path: pathlib.Path,
    findings: Findings,
) -> bool:
    required_prod_timing_keys = [
        "prove_addition",
        "verify_addition",
        "prove_dot_product",
        "verify_dot_product",
        "prove_single_neuron",
        "verify_single_neuron",
    ]
    required_prod_size_keys = [
        "addition.proof.json",
        "dot_product.proof.json",
        "single_neuron.proof.json",
    ]

    missing_prod_timing = sorted(k for k in required_prod_timing_keys if k not in prod_timings)
    missing_prod_sizes = sorted(k for k in required_prod_size_keys if k not in prod_sizes)
    if missing_prod_timing:
        findings.error(
            f"{prod_index_path}: production-v1 index is missing timing keys required "
            f"for Appendix C consistency check: {missing_prod_timing}"
        )
    if missing_prod_sizes:
        findings.error(
            f"{prod_index_path}: production-v1 index is missing artifact-size keys "
            f"required for Appendix C consistency check: {missing_prod_sizes}"
        )
    if missing_prod_timing or missing_prod_sizes:
        return False

    # NOTE: This mapping is intentionally strict for frozen-artifact validation.
    # Table C1 artifact/backend labels (after backtick stripping) and frozen index
    # timing/size keys must match these entries exactly. If naming conventions or
    # compared artifact rows change, update this mapping explicitly.
    expected: dict[tuple[str, str], tuple[int, int, int]] = {
        ("addition", "vanilla"): (
            prod_timings["prove_addition"],
            prod_timings["verify_addition"],
            prod_sizes["addition.proof.json"],
        ),
        ("dot_product", "vanilla"): (
            prod_timings["prove_dot_product"],
            prod_timings["verify_dot_product"],
            prod_sizes["dot_product.proof.json"],
        ),
        ("single_neuron", "vanilla"): (
            prod_timings["prove_single_neuron"],
            prod_timings["verify_single_neuron"],
            prod_sizes["single_neuron.proof.json"],
        ),
    }

    for key, expected_values in expected.items():
        if key not in appendix_rows:
            findings.error(
                f"{appendix_path}: missing Table C1 row for artifact/backend {key!r}."
            )
            continue
        found_values = appendix_rows[key]
        if found_values != expected_values:
            findings.error(
                f"{appendix_path}: Table C1 mismatch for {key!r}: found prove/verify/size={found_values}, "
                f"expected={expected_values} from frozen artifact indices."
            )

    unexpected_keys = sorted(set(appendix_rows) - set(expected))
    for key in unexpected_keys:
        findings.error(
            f"{appendix_path}: unexpected Table C1 row for artifact/backend {key!r}; "
            "no matching frozen artifact index entry."
        )

    return not findings.errors


def _validate_table_c2_consistency(
    transformer_rows: dict[tuple[str, str], tuple[int, int, int]],
    transformer_timings: dict[str, int],
    transformer_fields: dict[str, str],
    transformer_index_path: pathlib.Path,
    appendix_path: pathlib.Path,
    findings: Findings,
) -> bool:
    required_transformer_timing_keys = [
        "prepare_transformer_shaped_bundle",
        "verify_transformer_shaped_bundle",
    ]
    required_transformer_field_keys = [
        "artifact_file",
        "artifact_size_bytes",
        "sha_256",
    ]

    missing_transformer_timing = sorted(
        k for k in required_transformer_timing_keys if k not in transformer_timings
    )
    missing_transformer_fields = sorted(
        k for k in required_transformer_field_keys if k not in transformer_fields
    )
    if missing_transformer_timing:
        findings.error(
            f"{transformer_index_path}: transformer-shaped index is missing timing keys "
            f"required for Appendix C consistency check: {missing_transformer_timing}"
        )
    if missing_transformer_fields:
        findings.error(
            f"{transformer_index_path}: transformer-shaped index is missing artifact-summary "
            f"fields required for Appendix C consistency check: {missing_transformer_fields}"
        )
    if missing_transformer_timing or missing_transformer_fields:
        return False

    transformer_artifact_size_digits = re.sub(
        r"[^0-9]", "", transformer_fields.get("artifact_size_bytes", "")
    )
    if not transformer_artifact_size_digits:
        findings.error(
            f"{transformer_index_path}: malformed transformer-shaped artifact-summary field "
            "'Artifact size (bytes)'; expected at least one digit."
        )
        return False
    if transformer_fields.get("artifact_file") != "transformer_shaped.stwo.bundle.json":
        findings.error(
            f"{transformer_index_path}: transformer-shaped index artifact file mismatch: "
            f"found {transformer_fields.get('artifact_file')!r}, expected "
            "'transformer_shaped.stwo.bundle.json'."
        )
        return False

    expected_transformer: dict[tuple[str, str], tuple[int, int, int]] = {
        ("stwo-transformer-shaped-v1", "stwo"): (
            transformer_timings["prepare_transformer_shaped_bundle"],
            transformer_timings["verify_transformer_shaped_bundle"],
            int(transformer_artifact_size_digits),
        ),
    }

    for key, expected_values in expected_transformer.items():
        if key not in transformer_rows:
            findings.error(
                f"{appendix_path}: missing Table C2 row for bundle/backend {key!r}."
            )
            continue
        found_values = transformer_rows[key]
        if found_values != expected_values:
            findings.error(
                f"{appendix_path}: Table C2 mismatch for {key!r}: found prepare/verify/size={found_values}, "
                f"expected={expected_values} from frozen artifact indices."
            )

    unexpected_transformer_keys = sorted(set(transformer_rows) - set(expected_transformer))
    for key in unexpected_transformer_keys:
        findings.error(
            f"{appendix_path}: unexpected Table C2 row for bundle/backend {key!r}; "
            "no matching frozen artifact index entry."
        )

    return not findings.errors


def _validate_shared_normalization_primitive_index(
    primitive_index_path: pathlib.Path,
    primitive_timings: dict[str, int],
    primitive_fields: dict[str, str],
    findings: Findings,
) -> bool:
    required_primitive_timing_keys = [
        "prepare_shared_normalization_primitive",
        "verify_shared_normalization_primitive",
    ]
    required_primitive_field_keys = [
        "artifact_file",
        "artifact_size_bytes",
        "sha_256",
    ]

    missing_primitive_timing = sorted(
        k for k in required_primitive_timing_keys if k not in primitive_timings
    )
    missing_primitive_fields = sorted(
        k for k in required_primitive_field_keys if not primitive_fields.get(k, "").strip()
    )
    if missing_primitive_timing:
        findings.error(
            f"{primitive_index_path}: shared-normalization primitive index is missing timing keys "
            f"required for publication consistency checks: {missing_primitive_timing}"
        )
    if missing_primitive_fields:
        findings.error(
            f"{primitive_index_path}: shared-normalization primitive index is missing artifact-summary "
            f"fields required for publication consistency checks: {missing_primitive_fields}"
        )
    if missing_primitive_timing or missing_primitive_fields:
        return False

    artifact_file = primitive_fields.get("artifact_file")
    if artifact_file != "shared-normalization-primitive.stwo.json":
        findings.error(
            f"{primitive_index_path}: shared-normalization primitive artifact file mismatch: "
            f"found {artifact_file!r}, expected 'shared-normalization-primitive.stwo.json'."
        )
        return False

    artifact_size_digits = re.sub(r"[^0-9]", "", primitive_fields.get("artifact_size_bytes", ""))
    if not artifact_size_digits:
        findings.error(
            f"{primitive_index_path}: malformed shared-normalization primitive artifact-summary field "
            "'Artifact size (bytes)'; expected at least one digit."
        )
        return False

    artifact_path = primitive_index_path.parent / artifact_file
    if not artifact_path.exists():
        findings.error(
            f"{artifact_path}: missing cited shared-normalization primitive artifact referenced by "
            f"{primitive_index_path}."
        )
        return False

    expected_size = int(artifact_size_digits)
    actual_size = artifact_path.stat().st_size
    if actual_size != expected_size:
        findings.error(
            f"{primitive_index_path}: shared-normalization primitive artifact size mismatch: "
            f"index={expected_size}, actual={actual_size} at {artifact_path}."
        )
        return False

    actual_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    expected_sha = primitive_fields.get("sha_256", "").lower()
    if actual_sha != expected_sha:
        findings.error(
            f"{primitive_index_path}: shared-normalization primitive SHA-256 mismatch: "
            f"index={expected_sha!r}, actual={actual_sha!r} for {artifact_path}."
        )
        return False

    return True


def _validate_transformer_bundle_index(
    transformer_index_path: pathlib.Path,
    transformer_timings: dict[str, int],
    transformer_fields: dict[str, str],
    findings: Findings,
) -> bool:
    required_transformer_timing_keys = [
        "prepare_transformer_shaped_bundle",
        "verify_transformer_shaped_bundle",
    ]
    required_transformer_field_keys = [
        "artifact_file",
        "artifact_size_bytes",
        "sha_256",
    ]

    missing_transformer_timing = sorted(
        k for k in required_transformer_timing_keys if k not in transformer_timings
    )
    missing_transformer_fields = sorted(
        k for k in required_transformer_field_keys if not transformer_fields.get(k, "").strip()
    )
    if missing_transformer_timing:
        findings.error(
            f"{transformer_index_path}: transformer-shaped index is missing timing keys "
            f"required for publication consistency checks: {missing_transformer_timing}"
        )
    if missing_transformer_fields:
        findings.error(
            f"{transformer_index_path}: transformer-shaped index is missing artifact-summary "
            f"fields required for publication consistency checks: {missing_transformer_fields}"
        )
    if missing_transformer_timing or missing_transformer_fields:
        return False

    artifact_file = transformer_fields.get("artifact_file")
    if artifact_file != "transformer_shaped.stwo.bundle.json":
        findings.error(
            f"{transformer_index_path}: transformer-shaped index artifact file mismatch: "
            f"found {artifact_file!r}, expected 'transformer_shaped.stwo.bundle.json'."
        )
        return False

    artifact_size_digits = re.sub(
        r"[^0-9]", "", transformer_fields.get("artifact_size_bytes", "")
    )
    if not artifact_size_digits:
        findings.error(
            f"{transformer_index_path}: malformed transformer-shaped artifact-summary field "
            "'Artifact size (bytes)'; expected at least one digit."
        )
        return False

    artifact_path = transformer_index_path.parent / artifact_file
    if not artifact_path.exists():
        findings.error(
            f"{artifact_path}: missing cited transformer-shaped artifact referenced by "
            f"{transformer_index_path}."
        )
        return False

    expected_size = int(artifact_size_digits)
    actual_size = artifact_path.stat().st_size
    if actual_size != expected_size:
        findings.error(
            f"{transformer_index_path}: transformer-shaped artifact size mismatch: "
            f"index={expected_size}, actual={actual_size} at {artifact_path}."
        )
        return False

    actual_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    expected_sha = transformer_fields.get("sha_256", "").lower()
    if actual_sha != expected_sha:
        findings.error(
            f"{transformer_index_path}: transformer-shaped SHA-256 mismatch: "
            f"index={expected_sha!r}, actual={actual_sha!r} for {artifact_path}."
        )
        return False

    return True


def check_backend_appendix_consistency(repo_root: pathlib.Path, findings: Findings) -> None:
    transformer_index_path = (
        repo_root
        / "docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md"
    )
    primitive_index_path = (
        repo_root
        / "docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md"
    )

    for required_path in (transformer_index_path, primitive_index_path):
        if not required_path.exists():
            findings.error(
                f"{required_path}: missing required file for active bundle consistency check."
            )
            return

    try:
        transformer_text = transformer_index_path.read_text(encoding="utf-8")
        primitive_text = primitive_index_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        findings.error(
            "failed to read active bundle consistency inputs "
            f"({transformer_index_path}, {primitive_index_path}): {exc}"
        )
        return

    transformer_timings = parse_index_timings(transformer_text)
    transformer_fields = parse_index_field_values(transformer_text)
    primitive_timings = parse_index_timings(primitive_text)
    primitive_fields = parse_index_field_values(primitive_text)

    transformer_ok = _validate_transformer_bundle_index(
        transformer_index_path,
        transformer_timings,
        transformer_fields,
        findings,
    )
    primitive_ok = _validate_shared_normalization_primitive_index(
        primitive_index_path,
        primitive_timings,
        primitive_fields,
        findings,
    )
    if not (transformer_ok and primitive_ok):
        return


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

    check_primary_presentation_guardrails(repo_root, findings)
    check_appendix_source_note(repo_root, findings)
    check_backend_appendix_consistency(repo_root, findings)
    check_publication_snapshot_placeholders(repo_root, findings)
    check_tablero_claim_evidence_matrix(repo_root, findings)
    check_paper3_claim_evidence_matrix(repo_root, findings)
    check_paper_claim_language(repo_root, findings)

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
