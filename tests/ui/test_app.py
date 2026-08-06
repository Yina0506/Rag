"""Smoke tests via Streamlit's AppTest — confirms the app renders without
exceptions. Pipeline calls only fire inside `if st.button(...) and <input>`,
so the bare initial load never touches the network/LLM; the interactive
case mocks `rag.pipeline` so it doesn't either.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from rag.models import Claim, Grade, Paper, Verdict

APP_PATH = str(Path(__file__).parent.parent.parent / "src" / "rag" / "ui" / "app.py")


def test_app_loads_without_exceptions() -> None:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)

    assert not at.exception


def test_app_has_all_four_tabs() -> None:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)

    tab_labels = [tab.label for tab in at.tabs]
    assert "🔍 Verify a Claim" in tab_labels
    assert "📄 Audit a Draft" in tab_labels
    assert "🧩 Limitations" in tab_labels
    assert "🧭 Directions" in tab_labels


def test_verify_claim_flow_renders_verdict(mocker) -> None:
    verdict = Verdict(
        claim=Claim(text="some claim"),
        paper=Paper(id="s2:x", title="A Real Paper", authors=["A. Author"], year=2023),
        grade=Grade.SUPPORTS,
        confidence=0.9,
        justification="The evidence directly supports this.",
    )
    mocker.patch("rag.pipeline.verify_claim", return_value=[verdict])

    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    at.text_area[0].input("Transformers use attention instead of recurrence.")
    at.button(key="verify_btn").click()
    at.run(timeout=30)

    assert not at.exception
    assert any("A Real Paper" in md.value for md in at.markdown)


def test_verify_claim_handles_pipeline_exception_gracefully(mocker) -> None:
    mocker.patch("rag.pipeline.verify_claim", side_effect=RuntimeError("network exploded"))

    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    at.text_area[0].input("some claim")
    at.button(key="verify_btn").click()
    at.run(timeout=30)

    assert not at.exception  # caught and shown via st.error, not a crash
    assert any("network exploded" in e.value for e in at.error)
