import os
import requests
from models import ArticleInput, SourceResult

BASE_URL = "https://api.openalex.org/works"


def _email() -> str:
    return os.getenv("CROSSREF_EMAIL", "user@example.com")


def lookup(article: ArticleInput) -> SourceResult:
    try:
        if article.doi:
            return _lookup_by_doi(article.doi)
        if article.title:
            return _lookup_by_title(article.title)
    except requests.RequestException as e:
        return SourceResult(
            source="openalex", found=False, peer_reviewed=None,
            confidence=0.0, evidence=f"Network error: {e}",
        )
    return SourceResult(
        source="openalex", found=False, peer_reviewed=None,
        confidence=0.0, evidence="No DOI or title to query",
    )


def _lookup_by_doi(doi: str) -> SourceResult:
    resp = requests.get(
        BASE_URL,
        params={"filter": f"doi:{doi}", "mailto": _email()},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return SourceResult(
            source="openalex", found=False, peer_reviewed=None,
            confidence=0.0, evidence="DOI not found in OpenAlex",
        )
    return _parse_work(results[0])


def _lookup_by_title(title: str) -> SourceResult:
    resp = requests.get(
        BASE_URL,
        params={"search": title, "per-page": 1, "mailto": _email()},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return SourceResult(
            source="openalex", found=False, peer_reviewed=None,
            confidence=0.0, evidence="Title not found in OpenAlex",
        )
    result = _parse_work(results[0])
    return SourceResult(
        source=result.source, found=result.found, peer_reviewed=result.peer_reviewed,
        confidence=min(result.confidence, 0.5),
        evidence=result.evidence + " (title match — lower confidence)",
    )


def _parse_work(work: dict) -> SourceResult:
    work_type = work.get("type", "")
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    source_type = source.get("type", "")
    source_name = source.get("display_name", "unknown source")
    is_in_doaj = source.get("is_in_doaj", False)

    if work_type == "article" and source_type == "journal":
        confidence = 0.95 if is_in_doaj else 0.80
        doaj_note = " (DOAJ-indexed)" if is_in_doaj else ""
        return SourceResult(
            source="openalex", found=True, peer_reviewed=True,
            confidence=confidence,
            evidence=f"Journal article in '{source_name}'{doaj_note}",
        )
    if work_type == "article" and source_type != "journal":
        return SourceResult(
            source="openalex", found=True, peer_reviewed=None,
            confidence=0.30,
            evidence=f"Article hosted on '{source_name}' (type: {source_type}) — may be preprint",
        )
    return SourceResult(
        source="openalex", found=True, peer_reviewed=False,
        confidence=0.70,
        evidence=f"Work type is '{work_type}', not a journal article",
    )
