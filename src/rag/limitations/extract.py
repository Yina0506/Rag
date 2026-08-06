"""Stated + implicit limitation extraction (docs/07-phase-5-limitation-extraction.md).

Stated: locate Limitations / Future Work / Conclusion sections in a
sectioned full-text dump, extract sentence-level spans.

Implicit (the valuable part, per BAGELS): for a paper lacking/underreporting
stated limitations, retrieve similar papers and (a) surface limitations they
raise about themselves that plausibly apply here too, using their full text
via `retrieval.fulltext.fetch_full_text` — the Phase 5 full-text upgrade this
phase introduces; and (b) detect later papers whose abstract CONTRADICTS one
of this paper's own claims (reuses `verify.entailment`).

Both mechanisms are code-complete but depend on pieces that aren't live-
tested yet: (a) needs a running GROBID instance (see `retrieval/fulltext.py`,
`retrieval/grobid_client.py`); (b) reuses `verify.entailment`, which *is*
live-verified (Phase 3), so only the "later paper" retrieval side is unproven.
"""

from __future__ import annotations

import difflib
import re

from rag.models import Grade, Limitation, LimitationType, Paper
from rag.textutils import split_sentences

_SECTION_HEADING = re.compile(
    r"^\s*(?:\d+[.\)]?\s*)?"
    r"(limitations?(?:\s+(?:and|&)\s+future\s+work)?|future\s+work|conclusions?|discussion)\s*$",
    re.IGNORECASE,
)


def _looks_like_heading(line: str) -> bool:
    """Generic "is this line a section title" heuristic, used to find where
    a Limitations/Future Work/Conclusion section *ends* (at the next heading
    of any kind — e.g. "References" — not just another limitation-flavored
    one)."""
    stripped = line.strip()
    if not stripped or len(stripped) > 80 or stripped[-1] in ".!?,;:":
        return False
    if len(stripped.split()) > 8:
        return False
    return bool(re.match(r"^\d+[.\)]?\s+\S", stripped)) or stripped.isupper() or stripped.istitle()


def extract_stated(paper: Paper, full_text: str) -> list[Limitation]:
    """`full_text` is expected to have section headings on their own line
    (e.g. `retrieval.fulltext.fetch_full_text`'s sections joined as
    `f"{heading}\\n{text}"`). Sentences under a matched heading, up to the
    next heading-looking line, become one `Limitation` each."""
    lines = full_text.splitlines()
    limitations: list[Limitation] = []
    i = 0
    while i < len(lines):
        if _SECTION_HEADING.match(lines[i]):
            section_lines: list[str] = []
            i += 1
            while i < len(lines) and not _looks_like_heading(lines[i]):
                section_lines.append(lines[i])
                i += 1
            for sentence in split_sentences(" ".join(section_lines)):
                if len(sentence) > 15:  # skip stray fragments / figure captions
                    limitations.append(
                        Limitation(paper_id=paper.id, text=sentence, type=LimitationType.STATED)
                    )
        else:
            i += 1
    return limitations


def extract_implicit(paper: Paper, similar_papers: list[Paper]) -> list[Limitation]:
    """(a) limitations similar papers raise about themselves, that plausibly
    apply here; (b) later similar papers whose abstract contradicts one of
    this paper's own claims."""
    from rag.retrieval.fulltext import fetch_full_text
    from rag.verify.entailment import _run_entailer

    limitations: list[Limitation] = []
    target_claims = split_sentences(paper.abstract or "")[:5]  # cap: entailment isn't free

    for similar in similar_papers:
        if similar.id == paper.id:
            continue

        sections = fetch_full_text(similar)
        if sections:
            full_text = "\n".join(f"{heading}\n{text}" for heading, text in sections.items())
            for stated in extract_stated(similar, full_text):
                limitations.append(
                    Limitation(
                        paper_id=paper.id,
                        text=f"(raised by similar paper {similar.id}) {stated.text}",
                        type=LimitationType.IMPLICIT,
                    )
                )

        is_later = similar.year and paper.year and similar.year > paper.year
        if is_later and similar.abstract:
            for claim in target_claims:
                grade, _confidence, justification = _run_entailer(claim, similar.abstract)
                if grade == Grade.CONTRADICTS:
                    limitations.append(
                        Limitation(
                            paper_id=paper.id,
                            text=(
                                f"Later work ({similar.id}, {similar.year}) contradicts: "
                                f'"{claim}" — {justification}'
                            ),
                            type=LimitationType.IMPLICIT,
                        )
                    )
    return limitations


def _find_similar_papers(paper: Paper, k: int = 3) -> list[Paper]:
    from rag.retrieval.sources import search_papers

    candidates = search_papers(paper.title, limit=k + 1)
    return [c for c in candidates if c.id != paper.id][:k]


def _dedupe(limitations: list[Limitation]) -> list[Limitation]:
    """Near-identical-text dedup within a paper (docs/07). Text-similarity
    based (difflib, no new dependency) rather than embedding-based, so this
    doesn't require the `ml` extra just to dedupe — embeddings are added
    afterward, only for the survivors."""
    kept: list[Limitation] = []
    for limitation in limitations:
        if not any(
            difflib.SequenceMatcher(None, limitation.text.lower(), k.text.lower()).ratio() > 0.85
            for k in kept
        ):
            kept.append(limitation)
    return kept


def _with_topic_embedding(limitation: Limitation) -> Limitation:
    from rag.retrieval.embed import embed_text

    vector = embed_text(limitation.text)
    return limitation.model_copy(update={"topic_embedding": vector})


def extract_limitations(paper: Paper, full_text: str) -> list[Limitation]:
    """Stated + implicit (only pursued when stated looks sparse — the
    "underreporting" case per docs/07), deduped, each normalized with a
    topic embedding."""
    stated = extract_stated(paper, full_text)

    implicit: list[Limitation] = []
    if len(stated) < 2:
        implicit = extract_implicit(paper, _find_similar_papers(paper))

    deduped = _dedupe(stated + implicit)
    return [_with_topic_embedding(limitation) for limitation in deduped]
