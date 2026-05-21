import os
import requests
import responses
from unittest.mock import patch
from models import ArticleInput
from checker.sources.openalex import lookup

BASE = "https://api.openalex.org/works"

JOURNAL_ARTICLE_RESPONSE = {
    "results": [{
        "id": "https://openalex.org/W123",
        "type": "article",
        "display_name": "Some Article",
        "primary_location": {
            "source": {
                "id": "https://openalex.org/S123",
                "type": "journal",
                "display_name": "Some Journal",
                "is_in_doaj": False,
            }
        },
    }],
    "meta": {"count": 1},
}

DOAJ_ARTICLE_RESPONSE = {
    "results": [{
        "id": "https://openalex.org/W456",
        "type": "article",
        "display_name": "OA Article",
        "primary_location": {
            "source": {
                "id": "https://openalex.org/S456",
                "type": "journal",
                "display_name": "Open Access Journal",
                "is_in_doaj": True,
            }
        },
    }],
    "meta": {"count": 1},
}

PREPRINT_RESPONSE = {
    "results": [{
        "id": "https://openalex.org/W789",
        "type": "article",
        "display_name": "A Preprint",
        "primary_location": {
            "source": {
                "id": "https://openalex.org/S789",
                "type": "repository",
                "display_name": "bioRxiv",
                "is_in_doaj": False,
            }
        },
    }],
    "meta": {"count": 1},
}


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_doi_journal_article_peer_reviewed():
    responses.add(responses.GET, BASE, json=JOURNAL_ARTICLE_RESPONSE)
    result = lookup(ArticleInput(doi="10.1234/test"))
    assert result.source == "openalex"
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence == 0.80


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_doi_doaj_journal_gets_higher_confidence():
    responses.add(responses.GET, BASE, json=DOAJ_ARTICLE_RESPONSE)
    result = lookup(ArticleInput(doi="10.1234/oa"))
    assert result.peer_reviewed is True
    assert result.confidence == 0.95


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_doi_preprint_inconclusive():
    responses.add(responses.GET, BASE, json=PREPRINT_RESPONSE)
    result = lookup(ArticleInput(doi="10.1234/pre"))
    assert result.found is True
    assert result.peer_reviewed is None
    assert result.confidence == 0.30


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_doi_not_found():
    responses.add(responses.GET, BASE, json={"results": [], "meta": {"count": 0}})
    result = lookup(ArticleInput(doi="10.9999/missing"))
    assert result.found is False
    assert result.peer_reviewed is None
    assert result.confidence == 0.0


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_title_fallback():
    responses.add(responses.GET, BASE, json=JOURNAL_ARTICLE_RESPONSE)
    result = lookup(ArticleInput(title="Some Article"))
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence <= 0.5


@responses.activate
@patch.dict(os.environ, {"CROSSREF_EMAIL": "test@example.com"})
def test_network_error_returns_safe_result():
    responses.add(responses.GET, BASE, body=requests.exceptions.ConnectionError("timeout"))
    result = lookup(ArticleInput(doi="10.1234/err"))
    assert result.found is False
    assert result.confidence == 0.0
    assert "Network error" in result.evidence


def test_no_doi_or_title_returns_not_found():
    result = lookup(ArticleInput(issn="1234-5678"))
    assert result.found is False
    assert result.confidence == 0.0
