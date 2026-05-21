from urllib.parse import quote, quote_plus
import requests
from models import ArticleInput, SourceResult

BASE_URL = "https://doaj.org/api"


def lookup(article: ArticleInput) -> SourceResult:
    try:
        if article.doi:
            return _search_articles(f"doi:{article.doi}", f"DOI {article.doi}", use_plus=False)
        if article.issn:
            return _search_journals(f"issn:{article.issn}", f"ISSN {article.issn}")
        if article.title:
            return _search_articles(f"title:{article.title}", f"title '{article.title}'", use_plus=True)
    except requests.RequestException as e:
        return SourceResult(
            source="doaj", found=False, peer_reviewed=None,
            confidence=0.0, evidence=f"Network error: {e}",
        )
    return SourceResult(
        source="doaj", found=False, peer_reviewed=None,
        confidence=0.0, evidence="No identifier to query",
    )


def _search_articles(query: str, label: str, use_plus: bool = False) -> SourceResult:
    encoded = quote_plus(query) if use_plus else quote(query, safe="")
    resp = requests.get(
        f"{BASE_URL}/search/articles/{encoded}",
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("total", 0) > 0:
        return SourceResult(
            source="doaj", found=True, peer_reviewed=True,
            confidence=0.95, evidence=f"Article found in DOAJ by {label}",
        )
    return SourceResult(
        source="doaj", found=False, peer_reviewed=None,
        confidence=0.0, evidence=f"Not found in DOAJ by {label}",
    )


def _search_journals(query: str, label: str) -> SourceResult:
    resp = requests.get(
        f"{BASE_URL}/search/journals/{quote(query, safe='')}",
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("total", 0) > 0:
        return SourceResult(
            source="doaj", found=True, peer_reviewed=True,
            confidence=0.95, evidence=f"Journal found in DOAJ by {label}",
        )
    return SourceResult(
        source="doaj", found=False, peer_reviewed=None,
        confidence=0.0, evidence=f"Journal not found in DOAJ by {label}",
    )
