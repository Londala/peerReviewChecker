import os
import time
from difflib import SequenceMatcher

import requests
from models import ArticleInput, SourceResult

TITLE_SIM_THRESHOLD = 0.5


def _title_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

BASE_URL = "https://api.crossref.org"
HEADERS = {"User-Agent": f"PeerReviewChecker/1.0 (mailto:{os.getenv('CROSSREF_EMAIL', 'user@example.com')})"}


def lookup(article: ArticleInput) -> SourceResult:
    try:
        if article.doi:
            return _lookup_by_doi(article.doi)
        if article.title:
            return _lookup_by_title(article.title)
    except requests.RequestException as e:
        return SourceResult(
            source="crossref", found=False, peer_reviewed=None,
            confidence=0.0, evidence=f"Network error: {e}",
        )
    return SourceResult(
        source="crossref", found=False, peer_reviewed=None,
        confidence=0.0, evidence="No DOI or title to query",
    )


def _get_with_retry(url: str, **kwargs) -> requests.Response:
    resp = requests.get(url, **kwargs)
    if resp.status_code == 429:
        time.sleep(2)
        resp = requests.get(url, **kwargs)
    return resp


def _lookup_by_doi(doi: str) -> SourceResult:
    resp = _get_with_retry(f"{BASE_URL}/works/{doi}", headers=HEADERS, timeout=10)
    if resp.status_code == 404:
        return SourceResult(
            source="crossref", found=False, peer_reviewed=None,
            confidence=0.0, evidence="DOI not found in Crossref",
        )
    resp.raise_for_status()
    return _parse_work(resp.json()["message"])


def _lookup_by_title(title: str) -> SourceResult:
    resp = _get_with_retry(
        f"{BASE_URL}/works",
        params={"query": title, "rows": 1},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json()["message"].get("items", [])
    if not items:
        return SourceResult(
            source="crossref", found=False, peer_reviewed=None,
            confidence=0.0, evidence="No results found in Crossref",
        )
    returned_title = (items[0].get("title") or [""])[0]
    if _title_sim(title, returned_title) < TITLE_SIM_THRESHOLD:
        return SourceResult(
            source="crossref", found=False, peer_reviewed=None,
            confidence=0.0, evidence="No sufficiently matching title found in Crossref",
        )
    result = _parse_work(items[0])
    return SourceResult(
        source=result.source, found=result.found, peer_reviewed=result.peer_reviewed,
        confidence=min(result.confidence, 0.5),
        evidence=result.evidence + " (title match — lower confidence)",
    )


def _parse_work(work: dict) -> SourceResult:
    work_type = work.get("type", "")
    ref_count = work.get("is-referenced-by-count", 0)
    journal = (work.get("container-title") or ["unknown journal"])[0]
    is_journal_article = work_type == "journal-article"

    if is_journal_article:
        confidence = 0.75 if ref_count > 0 else 0.55
        evidence = f"Journal article in '{journal}'"
        if ref_count > 0:
            evidence += f" with {ref_count} citations"
        evidence += " (peer-review inferred from type)"
        return SourceResult(
            source="crossref", found=True, peer_reviewed=True,
            confidence=confidence, evidence=evidence,
        )
    else:
        return SourceResult(
            source="crossref", found=True, peer_reviewed=False,
            confidence=0.7,
            evidence=f"Work type is '{work_type}', not a journal article",
        )
