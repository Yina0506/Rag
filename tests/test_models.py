from rag.models import Candidate, ExistenceStatus, Grade, Paper


def test_paper_roundtrip(sample_paper: Paper) -> None:
    data = sample_paper.model_dump()
    assert Paper.model_validate(data) == sample_paper


def test_candidate_wraps_paper(sample_paper: Paper) -> None:
    candidate = Candidate(paper=sample_paper, score=0.87)
    assert candidate.paper.id == "s2:123"
    assert 0.0 <= candidate.score <= 1.0


def test_grade_and_existence_enums_have_expected_members() -> None:
    assert set(Grade) == {
        Grade.SUPPORTS,
        Grade.WEAK,
        Grade.NEUTRAL,
        Grade.CONTRADICTS,
        Grade.NOT_FOUND,
    }
    assert set(ExistenceStatus) == {
        ExistenceStatus.EXISTS,
        ExistenceStatus.NOT_FOUND,
        ExistenceStatus.RETRACTED,
    }
