#!/usr/bin/env python3
"""Archive mutable web evidence used by the paper into repo-local snapshots."""

from __future__ import annotations

import hashlib
import json
import re
import socket
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "docs" / "paper" / "evidence" / "web-2026-04-06"
OUTDIR.mkdir(parents=True, exist_ok=True)

URLS = [
    ("gemma_3_model_card", "https://ai.google.dev/gemma/docs/core/model_card_3"),
    ("gemma_family_overview", "https://developers.googleblog.com/en/gemma-explained-overview-gemma-model-family-architectures/"),
    ("stwo_2_0_0", "https://starkware.co/blog/s-two-2-0-0-prover-for-developers/"),
    ("recursive_circuit_proving", "https://starkware.co/blog/minutes-to-seconds-efficiency-gains-with-recursive-circuit-proving/"),
    ("starknet_version_releases", "https://www.starknet.io/developers/version-releases/"),
    ("strk20", "https://www.starknet.io/blog/make-all-erc-20-tokens-private-with-strk20/"),
    ("deepprove_1", "https://www.lagrange.dev/blog/deepprove-1"),
    ("deepprove_update_sep_2025", "https://www.lagrange.dev/engineering-updates/september-2025"),
    ("luminair_post", "https://starkware.co/blog/giza-x-s-two-powering-verifiable-ml-with-luminair/"),
    ("zkpytorch_product", "https://polyhedra.network/zkPyTorch"),
    ("zkpytorch_blog", "https://blog.polyhedra.network/zkpytorch/"),
    ("paradex_stwo", "https://starkware.co/blog/paradex-s-two-the-fastest-prover-meets-the-fastest-appchain/"),
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def fetch(url: str) -> bytes:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "codex-paper-archiver"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout) as error:
        raise SystemExit(f"Failed to fetch {url}: {error}") from error
    except Exception as error:  # pragma: no cover - defensive fallback
        raise SystemExit(f"Unexpected error while fetching {url}: {error}") from error


def sanitize_html(payload: bytes) -> bytes:
    text = payload.decode("utf-8", errors="replace")
    if not text.lstrip().lower().startswith("<!doctype html>"):
        text = "<!DOCTYPE html>\n" + text.lstrip()

    patterns = [
        (
            r"<script[^>]*>.*?(?:googletagmanager|gtag\(|dataLayer|GTM-[A-Z0-9]+).*?</script>",
            "<!-- stripped telemetry script: Google Tag Manager / Analytics -->",
        ),
        (
            r"<script[^>]*src=[\"'][^\"']*googletagmanager[^\"']*[\"'][^>]*></script>",
            "<!-- stripped telemetry script: Google Tag Manager / Analytics -->",
        ),
        (
            r"<script[^>]*>.*?(?:_hjSettings|hotjar).*?</script>",
            "<!-- stripped telemetry script: Hotjar -->",
        ),
        (
            r"<script[^>]*>.*?(?:_fs_namespace|fullstory|_fs_script).*?</script>",
            "<!-- stripped telemetry script: FullStory -->",
        ),
        (
            r"<script[^>]*src=[\"'][^\"']*(?:recaptcha|cloudflareinsights)[^\"']*[\"'][^>]*></script>",
            "<!-- stripped telemetry script: external analytics -->",
        ),
        (
            r"<script[^>]*>.*?(?:hs-script-loader|hs-scripts\.com|HubSpot).*?</script>",
            "<!-- stripped telemetry script: HubSpot -->",
        ),
        (
            r"<script[^>]*src=[\"'][^\"']*hs-scripts\.com[^\"']*[\"'][^>]*></script>",
            "<!-- stripped telemetry script: HubSpot -->",
        ),
        (
            r"<noscript>\s*<iframe[^>]*googletagmanager\.com/ns\.html[^>]*></iframe>\s*</noscript>",
            "<!-- stripped telemetry noscript iframe: Google Tag Manager -->",
        ),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(
        r"<link[^>]*href=[\"'][^\"']*google-analytics\.com[^\"']*[\"'][^>]*>",
        "<!-- stripped telemetry preconnect: Google Analytics -->",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"<devsite-analytics\b[^>]*>.*?</devsite-analytics>",
        "<!-- stripped telemetry element: devsite-analytics -->",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return text.encode("utf-8")


def main() -> None:
    manifest = []
    for label, url in URLS:
        payload = sanitize_html(fetch(url))
        sha256 = hashlib.sha256(payload).hexdigest()
        filename = f"{slugify(label)}.html"
        path = OUTDIR / filename
        path.write_bytes(payload)
        manifest.append(
            {
                "label": label,
                "url": url,
                "file": filename,
                "sha256": sha256,
            }
        )

    (OUTDIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (OUTDIR / "manifest.tsv").open("w", encoding="utf-8") as f:
        f.write("label\turl\tfile\tsha256\n")
        for item in manifest:
            f.write(
                f"{item['label']}\t{item['url']}\t{item['file']}\t{item['sha256']}\n"
            )
    print(f"wrote {OUTDIR / 'manifest.json'}")
    print(f"wrote {OUTDIR / 'manifest.tsv'}")


if __name__ == "__main__":
    main()
