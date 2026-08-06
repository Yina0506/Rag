"""No real model calls — mock `get_llm()`/`_nli_model()` at the module
boundary. Live behavior (does qwen3:4b actually grade well?) is an eval-time
concern (docs/09-evaluation.md), not something a fast unit test can assert."""

from __future__ import annotations

from rag.models import Grade
from rag.verify import entailment


def _mock_llm(mocker, response_text: str):
    mock_client = mocker.Mock()
    mock_client.complete.return_value = response_text
    mocker.patch.object(entailment, "get_llm", return_value=mock_client)
    return mock_client


def test_llm_entail_parses_well_formed_response(mocker) -> None:
    _mock_llm(
        mocker,
        "GRADE: SUPPORTS\nCONFIDENCE: 0.9\n"
        'JUSTIFICATION: The evidence states "X causes Y" which directly supports the claim.',
    )

    grade, confidence, justification = entailment.llm_entail("claim", "evidence")

    assert grade == Grade.SUPPORTS
    assert confidence == 0.9
    assert "X causes Y" in justification


def test_llm_entail_clamps_out_of_range_confidence(mocker) -> None:
    _mock_llm(mocker, "GRADE: WEAK\nCONFIDENCE: 1.7\nJUSTIFICATION: partially related")

    _grade, confidence, _justification = entailment.llm_entail("claim", "evidence")

    assert confidence == 1.0


def test_llm_entail_falls_back_to_neutral_on_malformed_response(mocker) -> None:
    """Never guess a grade when the model doesn't follow the format — a
    silent default toward SUPPORTS would be exactly the failure mode this
    project exists to prevent."""
    _mock_llm(mocker, "I'm not sure how to answer that.")

    grade, confidence, justification = entailment.llm_entail("claim", "evidence")

    assert grade == Grade.NEUTRAL
    assert confidence == 0.0
    assert "could not be parsed" in justification


def test_llm_entail_prompt_never_leaks_outside_knowledge_instruction(mocker) -> None:
    """Guardrail (docs/05-phase-3): the prompt itself must instruct the model
    to reason only over the evidence — this is the enforcement mechanism
    since we can't inspect a real model's "knowledge" in a unit test."""
    mock_client = _mock_llm(mocker, "GRADE: NEUTRAL\nCONFIDENCE: 0.5\nJUSTIFICATION: n/a")

    entailment.llm_entail("some claim", "some evidence")

    sent_prompt = mock_client.complete.call_args[0][0]
    assert "Reason ONLY about the evidence" in sent_prompt
    assert "never use outside knowledge" in sent_prompt.lower()


def test_nli_entail_maps_high_entailment_to_supports(mocker) -> None:
    mock_model = mocker.Mock()
    # CrossEncoder.predict returns raw logits, not probabilities (live-caught
    # bug — see nli_entail's docstring). Mock with realistic logit magnitudes,
    # not pre-normalized values, so the test exercises the actual softmax path.
    mock_model.predict.return_value = [[-5.0, 5.0, -2.0]]  # [contradiction, entailment, neutral]
    mocker.patch.object(entailment, "_nli_model", return_value=mock_model)

    grade, confidence, _justification = entailment.nli_entail("claim", "evidence")

    assert grade == Grade.SUPPORTS
    assert confidence > 0.9


def test_nli_entail_maps_moderate_entailment_to_weak(mocker) -> None:
    mock_model = mocker.Mock()
    mock_model.predict.return_value = [[-1.0, 1.0, 0.5]]  # softmax -> entailment ~0.57, below 0.7
    mocker.patch.object(entailment, "_nli_model", return_value=mock_model)

    grade, confidence, _justification = entailment.nli_entail("claim", "evidence")

    assert grade == Grade.WEAK
    assert confidence < 0.7


def test_nli_entail_maps_high_contradiction_to_contradicts(mocker) -> None:
    mock_model = mocker.Mock()
    mock_model.predict.return_value = [[5.0, -3.0, -2.0]]
    mocker.patch.object(entailment, "_nli_model", return_value=mock_model)

    grade, _confidence, _justification = entailment.nli_entail("claim", "evidence")

    assert grade == Grade.CONTRADICTS


def test_entail_dispatches_to_configured_backend(mocker) -> None:
    llm_mock = mocker.patch.object(
        entailment, "llm_entail", return_value=(Grade.SUPPORTS, 0.8, "j")
    )
    nli_mock = mocker.patch.object(entailment, "nli_entail", return_value=(Grade.WEAK, 0.6, "j"))

    mocker.patch.object(entailment.settings, "entailment_backend", "llm")
    assert entailment.entail("c", "e") == (Grade.SUPPORTS, 0.8)
    llm_mock.assert_called_once()
    nli_mock.assert_not_called()

    mocker.patch.object(entailment.settings, "entailment_backend", "nli")
    assert entailment.entail("c", "e") == (Grade.WEAK, 0.6)
    nli_mock.assert_called_once()


def test_justify_ignores_stale_grade_argument_and_recomputes(mocker) -> None:
    """`grade` is accepted for interface stability but not trusted — justify
    always reflects what the configured backend actually says now."""
    mocker.patch.object(
        entailment, "llm_entail", return_value=(Grade.CONTRADICTS, 0.7, "real justification")
    )
    mocker.patch.object(entailment.settings, "entailment_backend", "llm")

    result = entailment.justify("claim", "evidence", grade=Grade.SUPPORTS)

    assert result == "real justification"
