"""cluster_limitations needs the `cluster`/`ml` extras (HDBSCAN, embeddings)
for real use, but is fully testable with mocked embeddings/HDBSCAN. label_cluster
and build_directions mock the LLM and clustering respectively."""

from __future__ import annotations

# Must load before any test patches sys.modules — mock.patch.dict's restore
# wipes numpy's C-extension submodules, and a later `import numpy` trips
# numpy's "cannot load module more than once" guard.
import numpy  # noqa: F401

from rag.directions import cluster
from rag.models import Limitation, LimitationType


def _lim(paper_id: str, text: str, embedding: list[float] | None = None) -> Limitation:
    return Limitation(
        paper_id=paper_id, text=text, type=LimitationType.STATED, topic_embedding=embedding
    )


def _mock_hdbscan(mocker, labels: list[int]):
    instance = mocker.Mock()
    instance.fit_predict.return_value = labels
    fake_module = mocker.Mock(HDBSCAN=mocker.Mock(return_value=instance))
    mocker.patch.dict("sys.modules", {"hdbscan": fake_module})


def test_cluster_limitations_groups_by_embedding_and_drops_noise(mocker) -> None:
    limitations = [
        _lim("p1", "small dataset", [0.0, 0.0]),
        _lim("p2", "small dataset issue", [0.01, 0.01]),
        _lim("p3", "totally unrelated singleton limitation", [10.0, 10.0]),
    ]
    _mock_hdbscan(mocker, [0, 0, -1])  # third point is noise

    clusters = cluster.cluster_limitations(limitations, min_cluster_size=2)

    assert len(clusters) == 1
    assert {lim.paper_id for lim in clusters[0]} == {"p1", "p2"}


def test_cluster_limitations_computes_embedding_when_missing(mocker) -> None:
    limitations = [_lim("p1", "text one", None), _lim("p2", "text two", None)]
    embed_mock = mocker.patch("rag.retrieval.embed.embed_text", return_value=[0.0, 0.0])
    _mock_hdbscan(mocker, [0, 0])

    cluster.cluster_limitations(limitations)

    assert embed_mock.call_count == 2


def test_cluster_limitations_returns_empty_for_empty_input() -> None:
    assert cluster.cluster_limitations([]) == []


def test_label_cluster_grounds_prompt_in_member_limitations(mocker) -> None:
    mock_client = mocker.Mock()
    mock_client.complete.return_value = '"Small, non-diverse evaluation datasets."'
    mocker.patch("rag.llm.get_llm", return_value=mock_client)

    label = cluster.label_cluster([_lim("p1", "The dataset is small and homogeneous.")])

    assert label == "Small, non-diverse evaluation datasets."
    sent_prompt = mock_client.complete.call_args[0][0]
    assert "The dataset is small and homogeneous." in sent_prompt


def test_build_directions_ranks_by_distinct_paper_count(mocker) -> None:
    big_cluster = [_lim("p1", "a"), _lim("p2", "a"), _lim("p1", "a-dup")]  # p1 twice
    small_cluster = [_lim("p3", "b")]
    mocker.patch.object(cluster, "cluster_limitations", return_value=[small_cluster, big_cluster])
    mocker.patch.object(cluster, "label_cluster", side_effect=["small direction", "big direction"])

    directions = cluster.build_directions([])

    assert directions[0].label == "big direction"
    assert directions[0].frequency == 2  # distinct papers: p1, p2 — not 3 (raw count)
    assert directions[1].frequency == 1
    assert all(d.still_open is True for d in directions)
    assert all(d.solving_papers == [] for d in directions)
