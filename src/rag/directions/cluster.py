"""Aggregate + HDBSCAN cluster limitations into candidate directions
(docs/08-phase-6-direction-discovery.md). This is the most novel part.

Each dense cluster = a candidate direction; frequency = cluster size weighted
by distinct papers (docs: "a gap raised by 30 papers >> one raised once", so
frequency counts distinct `paper_id`s, not raw limitation count — Phase 5
already dedups near-identical limitations *within* one paper, but a paper can
still contribute several distinct limitations landing in the same cluster).
Cluster labels are LLM-summarized but grounded ONLY on member limitations —
same "never invent beyond retrieved text" rule as elsewhere.

Requires the `cluster` optional-dependency group (HDBSCAN) — lazy-imported,
same pattern as the `ml` extra elsewhere.
"""

from __future__ import annotations

from rag.models import Direction, Limitation

_LABEL_PROMPT = """The following are limitation statements from different papers in the same \
research field. A clustering algorithm grouped them together because they describe a similar \
underlying gap. Summarize them into ONE concise research-direction statement (a single \
sentence, phrased as an open problem or gap) that captures what they share. Do not invent \
anything beyond what these statements say.

LIMITATIONS:
{items}

Respond with ONLY the one-sentence direction statement, nothing else — no preamble, no quotes.
"""


def cluster_limitations(
    limitations: list[Limitation], min_cluster_size: int = 2
) -> list[list[Limitation]]:
    """Embed (reusing each `Limitation.topic_embedding` if Phase 5 already
    set one, computing it otherwise) + HDBSCAN. No preset k — cluster count
    falls out of the data's actual density. HDBSCAN's noise label (-1,
    points too sparse to belong to any dense cluster) is dropped: a
    limitation raised by exactly one paper with nothing similar isn't a
    "direction" by this method's own definition (frequency-weighted gaps)."""
    if not limitations:
        return []

    import hdbscan
    import numpy as np

    from rag.retrieval.embed import embed_text

    vectors = [
        lim.topic_embedding if lim.topic_embedding is not None else embed_text(lim.text)
        for lim in limitations
    ]
    matrix = np.array(vectors)
    labels = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size).fit_predict(matrix)

    clusters: dict[int, list[Limitation]] = {}
    for label, limitation in zip(labels, limitations, strict=True):
        if label == -1:
            continue
        clusters.setdefault(int(label), []).append(limitation)
    return list(clusters.values())


def label_cluster(cluster: list[Limitation]) -> str:
    """LLM summarizes a cluster into one direction statement, grounded only
    on the member limitations' own text."""
    from rag.llm import get_llm

    items = "\n".join(f"- {limitation.text}" for limitation in cluster)
    response = get_llm().complete(_LABEL_PROMPT.format(items=items))
    return response.strip().strip('"')


def build_directions(limitations: list[Limitation]) -> list[Direction]:
    """Cluster -> label -> rank by frequency (distinct papers). `still_open`
    defaults to True pending `directions.openness.check_openness` — this
    function only does the aggregate+cluster+label moves, not the openness
    check (kept separate so each of Phase 6's "three moves" is independently
    testable, per docs/08)."""
    clusters = cluster_limitations(limitations)
    directions = [
        Direction(
            label=label_cluster(cluster),
            member_limitations=cluster,
            frequency=len({limitation.paper_id for limitation in cluster}),
            still_open=True,
            solving_papers=[],
        )
        for cluster in clusters
    ]
    directions.sort(key=lambda d: d.frequency, reverse=True)
    return directions
