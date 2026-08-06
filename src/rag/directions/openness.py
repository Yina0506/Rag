"""Citation-graph "still open?" check (docs/08-phase-6-direction-discovery.md).

Per cluster: gather later papers (year > cluster papers, topically similar or
citing the gap-raisers) -> entailment check "does this later paper's
contribution resolve this limitation?" -> set still_open + solving_papers.
Least-explored, most defensible novelty in the thesis — spend effort here.
"""

from __future__ import annotations

from rag.models import Direction, Grade

_RESOLVES_TEMPLATE = "This work addresses the following limitation: {label}"


def find_later_papers(direction: Direction) -> list[str]:
    """Two sources, unioned (docs: "citation graph ... + topically similar"):
    (1) papers citing any of the gap-raising papers — the actual citation
    graph; (2) a topical search on the direction's own label, for later work
    that addresses the gap without necessarily citing the original
    gap-raisers (a common case: a later paper solving a known problem in a
    field doesn't always cite every paper that merely mentioned it as future
    work). Both filtered to strictly after the latest gap-raising paper's
    year, when that's known."""
    from rag.retrieval.sources import get_citing_papers, get_paper, search_papers

    paper_ids = {limitation.paper_id for limitation in direction.member_limitations}
    bare_ids = [pid.removeprefix("s2:") for pid in paper_ids if pid.startswith("s2:")]

    member_papers = [get_paper(bare_id) for bare_id in bare_ids]
    years = [p.year for p in member_papers if p and p.year]
    cutoff_year = max(years) if years else None

    later_ids: set[str] = set()

    for bare_id in bare_ids:
        for citing in get_citing_papers(bare_id, limit=10):
            if cutoff_year is None or (citing.year and citing.year > cutoff_year):
                later_ids.add(citing.id)

    for candidate in search_papers(direction.label, limit=10):
        if cutoff_year is None or (candidate.year and candidate.year > cutoff_year):
            later_ids.add(candidate.id)

    return list(later_ids)


def check_openness(direction: Direction) -> Direction:
    """Returns `direction` with `still_open` and `solving_papers` populated.
    "Resolves this gap?" is framed as an entailment question: does the later
    paper's abstract SUPPORT the claim that it addresses this direction's
    gap statement? Grounded only in retrieved abstracts, same discipline as
    every other entailment call in this project — never assumes a paper
    solves something just because it's later or topically similar."""
    from rag.retrieval.sources import get_paper
    from rag.verify.entailment import _run_entailer

    claim = _RESOLVES_TEMPLATE.format(label=direction.label)
    solving_papers = []

    for paper_id in find_later_papers(direction):
        bare_id = paper_id.removeprefix("s2:")
        paper = get_paper(bare_id)
        if not paper or not paper.abstract:
            continue
        grade, _confidence, _justification = _run_entailer(claim, paper.abstract)
        if grade in (Grade.SUPPORTS, Grade.WEAK):
            solving_papers.append(paper_id)

    return direction.model_copy(
        update={"still_open": len(solving_papers) == 0, "solving_papers": solving_papers}
    )
