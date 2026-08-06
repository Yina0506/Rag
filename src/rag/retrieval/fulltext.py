"""Full-text acquisition + sectioning (Phase 5): arXiv / Unpaywall -> GROBID
-> TEI -> a `{section_heading: text}` dict. Upgrades Phase 3's abstract-only
entailment evidence to passage-level, per docs/07-phase-5-limitation-extraction.md.

**Not live-tested**: depends on `retrieval.grobid_client`, which needs a
running GROBID instance (docker-compose's `grobid` service, `phase5`
profile) — same gap as `audit/grobid.py`. arXiv/Unpaywall fetching itself
only needs network access and could be live-tested independently of GROBID,
but wasn't as part of this phase (scope: get the pipeline code-complete;
live-validate together with the GROBID PDF path in one pass later).
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from rag.config import settings
from rag.http import cached_get
from rag.models import Paper
from rag.retrieval.grobid_client import TEI_NS, fetch_tei

ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
_ARXIV_DOI = re.compile(r"10\.48550/arxiv\.(.+)", re.IGNORECASE)


def _extract_arxiv_id(paper: Paper) -> str | None:
    if paper.doi:
        match = _ARXIV_DOI.match(paper.doi)
        if match:
            return match.group(1)
    return None


def _cache_path(paper_id: str) -> Path:
    safe_id = hashlib.sha256(paper_id.encode()).hexdigest()
    cache_dir: Path = settings.cache_path / "fulltext"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{safe_id}.json"


def fetch_arxiv_pdf(arxiv_id: str) -> bytes:
    resp = httpx.get(ARXIV_PDF_URL.format(arxiv_id=arxiv_id), timeout=60, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def find_oa_pdf_url(doi: str) -> str | None:
    """Unpaywall: legal open-access PDF location by DOI."""
    data = cached_get(
        f"{UNPAYWALL_BASE}/{doi}",
        params={"email": settings.contact_email or "unknown@example.com"},
        min_interval=0.2,
    )
    location = data.get("best_oa_location") or {}
    return location.get("url_for_pdf") or location.get("url")


def _fetch_pdf_bytes(paper: Paper) -> bytes | None:
    arxiv_id = _extract_arxiv_id(paper)
    if arxiv_id:
        return fetch_arxiv_pdf(arxiv_id)
    if paper.doi:
        pdf_url = find_oa_pdf_url(paper.doi)
        if pdf_url:
            resp = httpx.get(pdf_url, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            return resp.content
    return None


def parse_sections(tei_xml: str) -> dict[str, str]:
    """Each top-level `<div>` in the TEI body becomes one section, keyed by
    its `<head>` text (or "Untitled" if headless)."""
    root = ET.fromstring(tei_xml)
    sections: dict[str, str] = {}
    for div in root.iterfind(".//tei:body/tei:div", TEI_NS):
        head = div.find("tei:head", TEI_NS)
        heading = (head.text or "").strip() if head is not None and head.text else "Untitled"
        paragraphs = [
            " ".join("".join(p.itertext()).split()) for p in div.iterfind("tei:p", TEI_NS)
        ]
        text = " ".join(p for p in paragraphs if p)
        if text:
            prefix = f"{sections[heading]} " if heading in sections else ""
            sections[heading] = prefix + text
    return sections


def fetch_full_text(paper: Paper, *, use_cache: bool = True) -> dict[str, str] | None:
    """Best-effort: arXiv first (fast, reliable when applicable), then
    Unpaywall by DOI. Returns None if no open-access PDF could be found —
    a normal outcome (much of the literature isn't OA), not an error."""
    cache_file = _cache_path(paper.id)
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text())

    pdf_bytes = _fetch_pdf_bytes(paper)
    if pdf_bytes is None:
        return None

    tei_xml = fetch_tei(pdf_bytes)
    sections = parse_sections(tei_xml)

    if use_cache:
        cache_file.write_text(json.dumps(sections))
    return sections
