from dataclasses import dataclass, field


@dataclass
class ArticleInput:
    title: str | None = None
    doi: str | None = None
    issn: str | None = None
    author: str | None = None
    journal: str | None = None


@dataclass
class SourceResult:
    source: str
    found: bool
    peer_reviewed: bool | None
    confidence: float
    evidence: str
    title: str | None = None


@dataclass
class Verdict:
    peer_reviewed: bool | None
    confidence: float
    sources: list[SourceResult] = field(default_factory=list)
    title: str | None = None
