import requests
import responses
from models import ArticleInput
from checker.sources.doaj import lookup


@responses.activate
def test_article_found_by_doi():
    responses.add(
        responses.GET,
        "https://doaj.org/api/search/articles/doi%3A10.1234%2Ftest",
        json={"results": [{"id": "abc123", "bibjson": {"journal": {"title": "Open Journal"}}}], "total": 1},
    )
    article = ArticleInput(doi="10.1234/test")
    result = lookup(article)
    assert result.source == "doaj"
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence == 0.95


@responses.activate
def test_article_not_found():
    responses.add(
        responses.GET,
        "https://doaj.org/api/search/articles/doi%3A10.9999%2Fmissing",
        json={"results": [], "total": 0},
    )
    article = ArticleInput(doi="10.9999/missing")
    result = lookup(article)
    assert result.found is False
    assert result.peer_reviewed is None
    assert result.confidence == 0.0


@responses.activate
def test_issn_journal_lookup():
    responses.add(
        responses.GET,
        "https://doaj.org/api/search/journals/issn%3A1234-5678",
        json={"results": [{"id": "j1", "bibjson": {"title": "Open Journal"}}], "total": 1},
    )
    article = ArticleInput(issn="1234-5678")
    result = lookup(article)
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence == 0.95


@responses.activate
def test_title_fallback():
    responses.add(
        responses.GET,
        "https://doaj.org/api/search/articles/title%3ASome+Article",
        json={"results": [{"id": "t1", "bibjson": {}}], "total": 1},
    )
    article = ArticleInput(title="Some Article")
    result = lookup(article)
    assert result.found is True
    assert result.peer_reviewed is True


@responses.activate
def test_network_error_returns_safe_result():
    responses.add(
        responses.GET,
        "https://doaj.org/api/search/articles/doi%3A10.1234%2Ferr",
        body=requests.exceptions.ConnectionError("timeout"),
    )
    article = ArticleInput(doi="10.1234/err")
    result = lookup(article)
    assert result.found is False
    assert result.confidence == 0.0
    assert "Network error" in result.evidence
