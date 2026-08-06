"""Tiny shared text helpers with no model/network dependency. Kept separate
from any one phase's module since both `audit/draft.py` (Phase 4, LaTeX
sentences) and `limitations/extract.py` (Phase 5, GROBID-sectioned plain
text) need the same punctuation-based sentence splitter.
"""

from __future__ import annotations

import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\])")


def split_sentences(text: str) -> list[str]:
    """Cheap heuristic, not a real sentence tokenizer: splits on
    `.`/`!`/`?` followed by whitespace and a capital letter (or a `\\`, so
    LaTeX commands right after a period don't get glued to the next
    sentence). Known failure mode: abbreviations like "e.g." or "et al."
    split early — acceptable for this project's "start with heuristics, note
    failures" approach (docs/03, docs/06).
    """
    return [s.strip() for s in _SENTENCE_SPLIT.split(" ".join(text.split())) if s.strip()]
