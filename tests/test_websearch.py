import requests
import responses
from models import ArticleInput
from checker.sources.websearch import lookup

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


@responses.activate
def test_pubmed_hit_signals_peer_reviewed():
    responses.add(
        responses.GET,
        BRAVE_URL,
        json={
            "web": {
                "results": [
                    {
                        "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                        "description": "Article on PubMed about clinical trial",
                    }
                ]
            }
        },
    )
    article = ArticleInput(title="Some Clinical Trial Article")
    result = lookup(article)
    assert result.source == "websearch"
    assert result.peer_reviewed is True
    assert result.confidence <= 0.5


@responses.activate
def test_peer_reviewed_in_snippet():
    responses.add(
        responses.GET,
        BRAVE_URL,
        json={
            "web": {
                "results": [
                    {
                        "url": "https://example.com/article",
                        "description": "This peer-reviewed study examines...",
                    }
                ]
            }
        },
    )
    article = ArticleInput(title="Some Study")
    result = lookup(article)
    assert result.peer_reviewed is True
    assert result.confidence <= 0.5


@responses.activate
def test_no_signals_returns_inconclusive():
    responses.add(
        responses.GET,
        BRAVE_URL,
        json={"web": {"results": [{"url": "https://blog.example.com", "description": "A blog post"}]}},
    )
    article = ArticleInput(title="Random Blog Post")
    result = lookup(article)
    assert result.peer_reviewed is None
    assert result.confidence == 0.0


@responses.activate
def test_empty_results_returns_not_found():
    responses.add(
        responses.GET,
        BRAVE_URL,
        json={"web": {"results": []}},
    )
    article = ArticleInput(title="Nonexistent Article")
    result = lookup(article)
    assert result.found is False


@responses.activate
def test_network_error_returns_safe_result():
    responses.add(responses.GET, BRAVE_URL, body=requests.exceptions.ConnectionError("timeout"))
    article = ArticleInput(title="Test")
    result = lookup(article)
    assert result.found is False
    assert result.confidence == 0.0
    assert "Network error" in result.evidence
