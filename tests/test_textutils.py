from rag.textutils import split_sentences


def test_split_sentences_splits_on_terminal_punctuation() -> None:
    text = "This is one sentence. This is another! Is this a third?"
    assert split_sentences(text) == [
        "This is one sentence.",
        "This is another!",
        "Is this a third?",
    ]


def test_split_sentences_collapses_internal_whitespace() -> None:
    text = "Line one\nwraps here.   Extra   spaces here too."
    assert split_sentences(text) == ["Line one wraps here.", "Extra spaces here too."]


def test_split_sentences_empty_text_returns_empty_list() -> None:
    assert split_sentences("") == []


def test_split_sentences_known_limitation_abbreviation_splits_early() -> None:
    """Documented known failure mode, not a bug: an abbreviation followed by
    a capitalized word looks like a sentence boundary to this heuristic."""
    text = "Some methods work well, e.g. Transformers, for this task."
    result = split_sentences(text)
    assert len(result) > 1
