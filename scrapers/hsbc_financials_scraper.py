"""Discover and download HSBC quarterly Data Packs.

Design notes (verified against the live site):
  * The Data Pack *files* (PDF) download directly over plain HTTPS with a browser
    User-Agent -- no headless browser needed for the files themselves.
  * The investor *index* page is JavaScript-rendered, so link discovery there needs
    Playwright. To stay robust and offline-friendly we keep a curated registry of
    known Data Pack URLs (KNOWN_DATA_PACKS) and *optionally* augment it with a
    Playwright crawl when `--discover` is passed.
  * Refresh cadence: run DAILY. We only re-download a pack we don't already have
    (quarterly data never changes once published), satisfying the "check daily,
    re-process only on new document" design.

Usage:
    python -m scrapers.hsbc_financials_scraper            # download known packs
    python -m scrapers.hsbc_financials_scraper --discover # + crawl index for new ones
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = _ROOT / "data" / "downloads"
REGISTRY_FILE = _ROOT / "data" / "datapack_registry.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HSBC-FinOps-Project/1.0)"}

INDEX_URL = "https://www.hsbc.com/investors/results-and-announcements/all-reporting/group"

# Curated, verified Data Pack URLs. Each is a real published quarterly pack.
# `segments` records which segmentation the pack uses (changed Jan 2025).
KNOWN_DATA_PACKS: list[dict] = [
    {"quarter": "4Q2024", "period_end": "2024-12-31", "segments": "legacy",
     "url": "https://www.hsbc.com/-/files/hsbc/investors/hsbc-results/2024/annual/pdfs/hsbc-holdings-plc/sea-250219-4q-2024-data-pack.pdf"},
    {"quarter": "2Q2024", "period_end": "2024-06-30", "segments": "legacy",
     "url": "https://www.hsbc.com/-/files/hsbc/investors/hsbc-results/2024/interim/pdfs/hsbc-holdings-plc/sea-240731-hsbc-holdings-plc-interim-results-2024-data-pack-2q-2024-announcement.pdf"},
    {"quarter": "1Q2024", "period_end": "2024-03-31", "segments": "legacy",
     "url": "https://www.hsbc.com/-/files/hsbc/investors/hsbc-results/2024/1q/pdfs/hsbc-holdings-plc/240430-e-1q-2024-data-pack.pdf"},
]


@dataclass
class DownloadedPack:
    quarter: str
    period_end: str
    segments: str
    url: str
    local_path: str
    sha256: str
    content_type: str
    bytes: int


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_registry() -> dict:
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {}


def _save_registry(reg: dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2))


def download_pack(pack: dict, force: bool = False) -> DownloadedPack | None:
    """Download one pack unless we already have it (idempotent / daily-safe)."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    registry = _load_registry()
    key = pack["quarter"]

    fname = re.sub(r"[^A-Za-z0-9._-]", "_", pack["url"].split("/")[-1])
    dest = DOWNLOAD_DIR / fname

    if not force and key in registry and dest.exists():
        print(f"[scraper] {key}: already have it, skipping")
        return DownloadedPack(**registry[key])

    print(f"[scraper] downloading {key} ...")
    resp = requests.get(pack["url"], headers=HEADERS, timeout=90)
    resp.raise_for_status()
    data = resp.content
    dest.write_bytes(data)

    rec = DownloadedPack(
        quarter=pack["quarter"], period_end=pack["period_end"],
        segments=pack["segments"], url=pack["url"], local_path=str(dest),
        sha256=_sha256(data), content_type=resp.headers.get("content-type", ""),
        bytes=len(data),
    )
    registry[key] = asdict(rec)
    _save_registry(registry)
    print(f"[scraper] saved {dest.name} ({len(data):,} bytes)")
    return rec


def discover_from_index() -> list[dict]:
    """Crawl the JS-rendered investor index with Playwright for data-pack links.

    Optional: only used with --discover. Returns a list of {quarter?, url} dicts.
    Gracefully returns [] if Playwright isn't installed.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[scraper] Playwright not installed; skipping discovery. "
              "Run: pip install playwright && python -m playwright install chromium")
        return []

    found: list[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(INDEX_URL, wait_until="networkidle", timeout=60_000)
        hrefs = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.href)")
        browser.close()
    for h in hrefs:
        if re.search(r"data-pack", h, re.I) and h.lower().endswith(".pdf"):
            found.append({"url": h})
    print(f"[scraper] discovered {len(found)} candidate data-pack links")
    return found


def run(discover: bool = False) -> list[DownloadedPack]:
    packs = list(KNOWN_DATA_PACKS)
    if discover:
        for d in discover_from_index():
            if not any(d["url"] == p["url"] for p in packs):
                d.setdefault("quarter", d["url"].split("/")[-1][:12])
                d.setdefault("period_end", "")
                d.setdefault("segments", "unknown")
                packs.append(d)

    out: list[DownloadedPack] = []
    for p in packs:
        try:
            rec = download_pack(p)
            if rec:
                out.append(rec)
        except Exception as exc:
            print(f"[scraper] FAILED {p.get('quarter', p['url'])}: {exc}")
    print(f"\n[scraper] {len(out)} pack(s) available locally.")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true",
                    help="also crawl the investor index via Playwright")
    args = ap.parse_args()
    run(discover=args.discover)
