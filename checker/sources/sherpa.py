import json
import os
import requests
from models import ArticleInput, SourceResult

BASE_URL = "https://v2.sherpa.ac.uk/cgi/retrieve"


def lookup(article: ArticleInput) -> SourceResult:
    if not article.issn:
        return SourceResult(
            source="sherpa", found=False, peer_reviewed=None,
            confidence=0.0, evidence="No ISSN available for Sherpa Romeo lookup",
        )
    api_key = os.getenv("SHERPA_API_KEY", "")
    if not api_key:
        return SourceResult(
            source="sherpa", found=False, peer_reviewed=None,
            confidence=0.0, evidence="SHERPA_API_KEY not configured — skipping Sherpa Romeo",
        )
    try:
        return _lookup_by_issn(article.issn, api_key)
    except requests.RequestException as e:
        return SourceResult(
            source="sherpa", found=False, peer_reviewed=None,
            confidence=0.0, evidence=f"Network error: {e}",
        )


def _lookup_by_issn(issn: str, api_key: str) -> SourceResult:
    filter_param = json.dumps([["issn", "equals", issn]])
    resp = requests.get(
        BASE_URL,
        params={
            "item-type": "publication",
            "api-key": api_key,
            "format": "Json",
            "filter": filter_param,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("total_results", 0) > 0:
        item = data["items"][0]
        titles = item.get("title", [])
        journal_name = titles[0]["title"] if titles else "unknown journal"
        return SourceResult(
            source="sherpa", found=True, peer_reviewed=True,
            confidence=0.80,
            evidence=f"Journal '{journal_name}' (ISSN {issn}) found in Sherpa Romeo",
        )
    return SourceResult(
        source="sherpa", found=False, peer_reviewed=None,
        confidence=0.0, evidence=f"ISSN {issn} not found in Sherpa Romeo",
    )
