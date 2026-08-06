"""Draft audit / Mode B (docs/06-phase-4-draft-audit.md).

Ingest a real draft (.bib/.tex, or PDF via GROBID), associate each in-text
claim with its cited reference(s), and run existence + entailment per pair.
This is the mode that directly serves the original thesis-writing pain point.

Per-pair symbol mapping (docs/06's "flagging mismatches, unsupported claims,
fabricated refs, and retractions"):
- ✅ SUPPORTS            — real paper, clearly supports the claim
- ⚠️ WEAK / NEUTRAL       — real paper, but a weak or no-real-relation citation
- ❌ CONTRADICTS          — real paper, actively contradicts the claim
- 🚫 NOT_FOUND / RETRACTED — existence gate rejected it; never reaches entailment

LangGraph note (docs/01-architecture.md gates it to "when Phase 4 needs
multi-step audit"): NOT introduced here. The per-pair flow (resolve ->
existence -> entail -> suggest) is a straight linear pipeline over
independent pairs, same shape as `pipeline.verify_claim` from Phase 3 — no
branching/cyclic control flow that would justify a graph framework. Revisit
if a later phase's audit logic genuinely needs multi-step planning.
"""

from __future__ import annotations

import re

import bibtexparser

from rag.models import AuditFinding, Claim, ExistenceStatus, Grade, Paper, Verdict
from rag.textutils import split_sentences

_CITE_COMMAND = re.compile(
    r"\\(?:cite|citep|citet|citeauthor|citeyear|parencite|textcite)\{([^}]*)\}"
)
_LATEX_COMMENT = re.compile(r"(?<!\\)%.*")

_SYMBOLS = {
    Grade.SUPPORTS: "✅",
    Grade.WEAK: "⚠️",
    Grade.NEUTRAL: "⚠️",
    Grade.CONTRADICTS: "❌",
    Grade.NOT_FOUND: "❌",
}


def _strip_braces(value: str) -> str:
    return re.sub(r"[{}]", "", value).strip()


def parse_bibtex(bib_text: str) -> dict[str, Paper]:
    """Parses a `.bib` file into `{citation_key: Paper}` stubs (no abstract —
    BibTeX doesn't carry one; `resolve_bib_paper` fetches it once existence
    is confirmed)."""
    library = bibtexparser.loads(bib_text)
    papers = {}
    for entry in library.entries:
        key = entry.get("ID", "")
        if not key:
            continue
        year_str = entry.get("year", "")
        year = int(year_str) if year_str.strip().isdigit() else None
        authors = [
            _strip_braces(a) for a in entry.get("author", "").split(" and ") if a.strip()
        ]
        papers[key] = Paper(
            id=f"bib:{key}",
            doi=entry.get("doi") or None,
            title=_strip_braces(entry.get("title", key)),
            year=year,
            authors=authors,
        )
    return papers


def parse_tex_citations(tex_text: str) -> list[tuple[str, str]]:
    """Sentence-level heuristic: split into sentences, find `\\cite`-family
    commands in each, strip them out of the sentence text, and pair the
    cleaned sentence with each citation key found in it (a sentence citing
    two papers yields two pairs — each citation is audited independently).

    Known limitation (per docs/06's "note failures"): sentence boundaries
    are punctuation-based and don't understand LaTeX math/abbreviations
    (e.g. "e.g." splits early); a citation spanning multiple sentences isn't
    associated with all of them, only the one it's textually inside.
    """
    text = _LATEX_COMMENT.sub("", tex_text)
    pairs: list[tuple[str, str]] = []
    for paragraph in re.split(r"\n\s*\n", text):
        for sentence in split_sentences(paragraph):
            keys_in_sentence = [
                key.strip()
                for match in _CITE_COMMAND.finditer(sentence)
                for key in match.group(1).split(",")
                if key.strip()
            ]
            if not keys_in_sentence:
                continue
            claim_text = " ".join(_CITE_COMMAND.sub("", sentence).split()).strip()
            claim_text = re.sub(r"\s+([.,!?;:])", r"\1", claim_text)
            for key in keys_in_sentence:
                pairs.append((claim_text, key))
    return pairs


def resolve_bib_paper(entry: Paper) -> tuple[ExistenceStatus, Paper]:
    """Runs a bib entry through the Phase 2 existence gate. DOI-present
    entries resolve directly; DOI-less ones go through
    `fuzzy_match_existence` (the exact case that function was built for —
    docs/04-phase-2). Returns the resolved `Paper` with an abstract attached
    when one could be fetched (needed as entailment evidence)."""
    from rag.verify import existence

    if entry.doi:
        verdict = existence.existence_verdict(entry)
        resolved = entry if verdict == ExistenceStatus.NOT_FOUND else _with_abstract(entry)
        return verdict, resolved

    matched = existence.fuzzy_match_existence(entry.title, entry.authors or None, entry.year)
    if matched is None:
        return ExistenceStatus.NOT_FOUND, entry

    verdict = existence.existence_verdict(matched)
    resolved = entry if verdict == ExistenceStatus.NOT_FOUND else _with_abstract(matched)
    return verdict, resolved


def _with_abstract(paper: Paper) -> Paper:
    """Best-effort abstract fetch. Tries Semantic Scholar's DOI-prefixed
    lookup first, then falls back to a title search — **live-caught bug**:
    a real paper can have multiple valid DOIs across registration systems
    (e.g. an arXiv preprint DOI vs. a proceedings DOI Crossref's fuzzy match
    returns), and S2 only indexes one of them. Relying on DOI lookup alone
    silently produced empty evidence for "Attention Is All You Need" during
    live testing — the paper unambiguously exists and is on-topic, but S2
    didn't have it under the Crossref-returned DOI. Missing abstract still
    isn't fatal even with the fallback — the entailer just gets no evidence
    and grades accordingly (honest NEUTRAL/low-confidence, not a crash)."""
    from rag.retrieval import sources
    from rag.verify.existence import _titles_match

    fetched = sources.get_paper(f"DOI:{paper.doi}") if paper.doi else None
    if not fetched or not fetched.abstract:
        candidates = sources.search_papers(paper.title, limit=3)
        fetched = next((c for c in candidates if _titles_match(paper.title, c.title)), None)
    if fetched and fetched.abstract:
        return paper.model_copy(update={"abstract": fetched.abstract})
    return paper


def audit_pair(claim_text: str, key: str, bib_entries: dict[str, Paper]) -> AuditFinding:
    """Resolve one (claim, citation_key) pair -> existence gate -> entailment
    -> AuditFinding. A citation key missing from the bibliography entirely
    (typo, or a \\cite to a key that was never defined) is treated the same
    as a fabricated reference — there's nothing to resolve."""
    entry = bib_entries.get(key)
    if entry is None:
        return AuditFinding(
            claim_text=claim_text,
            citation_key=key,
            existence=ExistenceStatus.NOT_FOUND,
            symbol="🚫",
        )

    existence_status, resolved = resolve_bib_paper(entry)
    if existence_status != ExistenceStatus.EXISTS:
        return AuditFinding(
            claim_text=claim_text, citation_key=key, existence=existence_status, symbol="🚫"
        )

    from rag.verify.entailment import _run_entailer

    grade, confidence, justification = _run_entailer(claim_text, resolved.abstract or "")
    verdict = Verdict(
        claim=Claim(text=claim_text),
        paper=resolved,
        grade=grade,
        evidence_passage=resolved.abstract,
        confidence=confidence,
        justification=justification,
    )
    symbol = _SYMBOLS[grade]

    suggested_citation = None
    if symbol == "❌":
        from rag.pipeline import verify_claim

        alternatives = verify_claim(claim_text, k=1)
        if alternatives and alternatives[0].grade != Grade.NOT_FOUND:
            suggested_citation = alternatives[0].paper

    return AuditFinding(
        claim_text=claim_text,
        citation_key=key,
        existence=existence_status,
        symbol=symbol,
        verdict=verdict,
        suggested_citation=suggested_citation,
    )


def _find_bib_path(tex_path: str, tex_text: str) -> str:
    import os

    match = re.search(r"\\bibliography\{([^}]*)\}", tex_text)
    directory = os.path.dirname(tex_path)
    if match:
        name = match.group(1).split(",")[0].strip()
        candidate = os.path.join(directory, name if name.endswith(".bib") else f"{name}.bib")
        if os.path.exists(candidate):
            return candidate
    fallback = os.path.splitext(tex_path)[0] + ".bib"
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError(
        f"Could not locate a .bib file for {tex_path} (no \\bibliography{{}} match, no "
        f"same-name .bib). Pass bib_path explicitly to audit()."
    )


def render_markdown_report(findings: list[AuditFinding]) -> str:
    lines = ["# Draft Audit Report", ""]
    for finding in findings:
        lines.append(f"## {finding.symbol} `{finding.citation_key}`")
        lines.append(f"> {finding.claim_text}")
        lines.append(f"- Existence: {finding.existence.value}")
        if finding.verdict:
            grade, confidence = finding.verdict.grade.value, finding.verdict.confidence
            lines.append(f"- Grade: {grade} ({confidence:.2f})")
            lines.append(f"- Justification: {finding.verdict.justification}")
        if finding.suggested_citation:
            lines.append(f"- Suggested instead: {finding.suggested_citation.title}")
        lines.append("")

    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.symbol] = counts.get(finding.symbol, 0) + 1
    summary = ", ".join(f"{symbol} {count}" for symbol, count in sorted(counts.items()))
    lines.insert(2, f"**Summary:** {summary or 'no citations found'}")
    lines.insert(3, "")
    return "\n".join(lines)


def audit(path: str, bib_path: str | None = None) -> dict:
    """Top-level entrypoint. `.tex` needs a companion `.bib` (found via
    `\\bibliography{}` or same-basename, or pass `bib_path` explicitly). A
    lone `.bib` with no `.tex` runs existence-only (no claim text to grade
    against, so no entailment — still useful as a "check my bibliography for
    fabricated/retracted entries" sweep)."""
    if path.endswith(".pdf"):
        from rag.audit.grobid import ingest_pdf

        pairs, bib_entries = ingest_pdf(path)
    elif path.endswith(".tex"):
        tex_text = _read(path)
        resolved_bib_path = bib_path or _find_bib_path(path, tex_text)
        bib_entries = parse_bibtex(_read(resolved_bib_path))
        pairs = parse_tex_citations(tex_text)
    elif path.endswith(".bib"):
        bib_entries = parse_bibtex(_read(path))
        pairs = [(entry.title, key) for key, entry in bib_entries.items()]
    else:
        raise ValueError(f"Unsupported draft format: {path} (expected .tex, .bib, or .pdf)")

    findings = [audit_pair(claim_text, key, bib_entries) for claim_text, key in pairs]
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.symbol] = counts.get(finding.symbol, 0) + 1

    return {
        "findings": [f.model_dump() for f in findings],
        "summary": counts,
        "markdown": render_markdown_report(findings),
    }


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()
