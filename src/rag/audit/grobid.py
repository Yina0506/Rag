"""PDF -> TEI via a running GROBID instance (docs/02-data-sources.md,
docs/06-phase-4-draft-audit.md). Split out from `draft.py` since this is the
heavy/optional ingestion path — `.bib`/`.tex` drafts never import this module.

**Not live-tested**: GROBID isn't running in this environment (it's the
`grobid` service behind docker-compose's `phase5` profile — see
docs/PROGRESS.md). The TEI parsing below follows GROBID's documented schema
but hasn't been run against a real GROBID response. Verify against a real
instance (`docker compose --profile phase5 up grobid`) before relying on it.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from rag.models import Paper
from rag.retrieval.grobid_client import TEI_NS as _TEI_NS
from rag.retrieval.grobid_client import fetch_tei as _fetch_tei


def _parse_bibliography(root: ET.Element) -> dict[str, Paper]:
    entries = {}
    for bibl_struct in root.iterfind(".//tei:back//tei:biblStruct", _TEI_NS):
        xml_id = bibl_struct.get("{http://www.w3.org/XML/1998/namespace}id")
        if not xml_id:
            continue
        title_el = bibl_struct.find(".//tei:title[@level='a']", _TEI_NS)
        if title_el is None or not title_el.text:
            title_el = bibl_struct.find(".//tei:title", _TEI_NS)
        title = (title_el.text or "").strip() if title_el is not None else xml_id
        doi_el = bibl_struct.find(".//tei:idno[@type='DOI']", _TEI_NS)
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None
        year_el = bibl_struct.find(".//tei:date[@type='published']", _TEI_NS)
        year = None
        if year_el is not None:
            when = year_el.get("when", "")
            if when[:4].isdigit():
                year = int(when[:4])
        authors = [
            " ".join(
                part.text.strip()
                for part in author.iterfind(".//tei:forename", _TEI_NS)
                or author.iterfind(".//tei:surname", _TEI_NS)
                if part.text
            )
            for author in bibl_struct.iterfind(".//tei:author", _TEI_NS)
        ]
        entries[xml_id] = Paper(
            id=f"grobid:{xml_id}",
            doi=doi,
            title=title,
            year=year,
            authors=[a for a in authors if a],
        )
    return entries


def _parse_sentences_with_refs(root: ET.Element) -> list[tuple[str, list[str]]]:
    """Each `<s>` (GROBID sentence, requires `segmentSentences=1`) becomes one
    claim; `<ref type="bibr" target="#b0">` markers inside it give the cited
    bibliography xml:ids (target has a leading `#` to strip)."""
    pairs = []
    for sentence in root.iterfind(".//tei:body//tei:s", _TEI_NS):
        text_parts = list(sentence.itertext())
        text = " ".join("".join(text_parts).split())
        ref_ids = [
            ref.get("target", "").lstrip("#")
            for ref in sentence.iterfind(".//tei:ref[@type='bibr']", _TEI_NS)
            if ref.get("target")
        ]
        if ref_ids and text:
            pairs.append((text, ref_ids))
    return pairs


def ingest_pdf(pdf_path: str) -> tuple[list[tuple[str, str]], dict[str, Paper]]:
    """Returns (claim_citation_pairs, bibliography) in the same shape
    `audit.draft.audit` expects from the `.tex`/`.bib` path."""
    tei_xml = _fetch_tei(pdf_path)
    root = ET.fromstring(tei_xml)
    bibliography = _parse_bibliography(root)
    sentence_pairs = _parse_sentences_with_refs(root)
    pairs = [(text, ref_id) for text, ref_ids in sentence_pairs for ref_id in ref_ids]
    return pairs, bibliography
