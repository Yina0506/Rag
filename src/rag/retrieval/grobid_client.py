"""Shared low-level GROBID client: POST a PDF (path or raw bytes) to a running
GROBID instance, get back TEI XML. Used by `audit/grobid.py` (Phase 4, PDF
draft ingestion) and `retrieval/fulltext.py` (Phase 5, full-text acquisition)
— factored out here instead of duplicated since both need the same call.

**Not live-tested**: no GROBID instance running in this environment (it's the
`grobid` service behind docker-compose's `phase5` profile — see
docs/PROGRESS.md). Verify against a real instance
(`docker compose --profile phase5 up grobid`) before relying on it.
"""

from __future__ import annotations

import httpx

from rag.config import settings

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def fetch_tei(pdf: str | bytes, *, segment_sentences: bool = True) -> str:
    """`pdf` is a file path or raw PDF bytes."""
    if isinstance(pdf, bytes):
        content = pdf
    else:
        with open(pdf, "rb") as f:
            content = f.read()

    files = {"input": ("document.pdf", content, "application/pdf")}
    resp = httpx.post(
        f"{settings.grobid_url}/api/processFulltextDocument",
        files=files,
        data={"segmentSentences": "1" if segment_sentences else "0"},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.text
