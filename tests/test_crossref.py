import responses
import requests
from models import ArticleInput
from checker.sources.crossref import lookup


@responses.activate
def test_doi_lookup_peer_reviewed():
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test",
        json={
            "status": "ok",
            "message": {
                "type": "journal-article",
                "is-referenced-by-count": 5,
                "title": ["Some Article"],
                "container-title": ["Some Journal"],
            },
        },
    )
    article = ArticleInput(doi="10.1234/test")
    result = lookup(article)
    assert result.source == "crossref"
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence == 0.75


@responses.activate
def test_doi_lookup_not_journal_article():
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/book",
        json={
            "status": "ok",
            "message": {
                "type": "book-chapter",
                "is-referenced-by-count": 2,
                "title": ["A Book Chapter"],
                "container-title": [],
            },
        },
    )
    article = ArticleInput(doi="10.1234/book")
    result = lookup(article)
    assert result.found is True
    assert result.peer_reviewed is False


@responses.activate
def test_doi_not_found():
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.9999/missing",
        status=404,
    )
    article = ArticleInput(doi="10.9999/missing")
    result = lookup(article)
    assert result.found is False
    assert result.peer_reviewed is None
    assert result.confidence == 0.0


@responses.activate
def test_title_fallback_query():
    responses.add(
        responses.GET,
        "https://api.crossref.org/works",
        json={
            "status": "ok",
            "message": {
                "items": [
                    {
                        "type": "journal-article",
                        "is-referenced-by-count": 3,
                        "title": ["Some Article Title"],
                        "container-title": ["Some Journal"],
                    }
                ]
            },
        },
    )
    article = ArticleInput(title="Some Article Title")
    result = lookup(article)
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence <= 0.5


@responses.activate
def test_network_error_returns_safe_result():
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/err",
        body=requests.exceptions.ConnectionError("connection refused"),
    )
    article = ArticleInput(doi="10.1234/err")
    result = lookup(article)
    assert result.found is False
    assert result.confidence == 0.0
    assert "Network error" in result.evidence
