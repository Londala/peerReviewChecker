import os
import requests
from models import ArticleInput, SourceResult

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
PEER_REVIEW_SIGNALS = [
    "pubmed.ncbi.nlm.nih.gov",
    "scopus.com",
    "webofscience.com",
    "peer-reviewed",
    "peer reviewed",
]
MAX_CONFIDENCE = 0.5


def lookup(article: ArticleInput) -> SourceResult:
    if not article.title:
        return SourceResult(
            source="websearch", found=False, peer_reviewed=None,
            confidence=0.0, evidence="No title available for web search",
        )
    api_key = os.getenv("BRAVE_API_KEY", "")
    query = f'"{article.title}" peer reviewed journal site:pubmed.ncbi.nlm.nih.gov OR site:scholar.google.com'
    try:
        resp = requests.get(
            BRAVE_URL,
            params={"q": query, "count": 3},
            headers={"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": api_key},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return SourceResult(
            source="websearch", found=False, peer_reviewed=None,
            confidence=0.0, evidence=f"Network error: {e}",
        )

    results = resp.json().get("web", {}).get("results", [])
    if not results:
        return SourceResult(
            source="websearch", found=False, peer_reviewed=None,
            confidence=0.0, evidence="No web results found",
        )

    signals_found = []
    for r in results[:3]:
        text = (r.get("url", "") + " " + r.get("description", "")).lower()
        for signal in PEER_REVIEW_SIGNALS:
            if signal in text:
                signals_found.append(signal)

    if signals_found:
        return SourceResult(
            source="websearch", found=True, peer_reviewed=True,
            confidence=MAX_CONFIDENCE,
            evidence=f"Web signals found: {', '.join(set(signals_found))}",
        )
    return SourceResult(
        source="websearch", found=True, peer_reviewed=None,
        confidence=0.0, evidence="No peer-review signals in top web results",
    )
