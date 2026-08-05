"""Shared data contracts. Every phase reads/writes these — keep them stable.

See docs/01-architecture.md "Data contracts" for the source of truth.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Grade(StrEnum):
    SUPPORTS = "SUPPORTS"
    WEAK = "WEAK"
    NEUTRAL = "NEUTRAL"
    CONTRADICTS = "CONTRADICTS"
    NOT_FOUND = "NOT_FOUND"


class ExistenceStatus(StrEnum):
    EXISTS = "EXISTS"
    NOT_FOUND = "NOT_FOUND"
    RETRACTED = "RETRACTED"


class LimitationType(StrEnum):
    STATED = "stated"
    IMPLICIT = "implicit"


class Paper(BaseModel):
    id: str
    doi: str | None = None
    title: str
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    authors: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    retracted: bool = False


class Claim(BaseModel):
    text: str
    source_span: str | None = None
    extracted_from: str | None = None


class Candidate(BaseModel):
    paper: Paper
    score: float
    retrieved_passage: str | None = None


class Verdict(BaseModel):
    claim: Claim
    paper: Paper
    grade: Grade
    evidence_passage: str | None = None
    confidence: float
    justification: str


class Limitation(BaseModel):
    paper_id: str
    text: str
    type: LimitationType
    topic_embedding: list[float] | None = None


class Direction(BaseModel):
    label: str
    member_limitations: list[Limitation] = Field(default_factory=list)
    frequency: int
    still_open: bool
    solving_papers: list[str] = Field(default_factory=list)
