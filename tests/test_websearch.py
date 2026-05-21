import os
import requests
import responses
from unittest.mock import patch
from models import ArticleInput
from checker.sources.websearch import lookup

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
FAKE_KEY = {"BRAVE_API_KEY": "test-key"}


@responses.activate
@patch.dict(os.environ, FAKE_KEY)
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
@patch.dict(os.environ, FAKE_KEY)
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
@patch.dict(os.environ, FAKE_KEY)
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
@patch.dict(os.environ, FAKE_KEY)
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
@patch.dict(os.environ, FAKE_KEY)
def test_network_error_returns_safe_result():
    responses.add(responses.GET, BRAVE_URL, body=requests.exceptions.ConnectionError("timeout"))
    article = ArticleInput(title="Test")
    result = lookup(article)
    assert result.found is False
    assert result.confidence == 0.0
    assert "Network error" in result.evidence


def test_missing_api_key_returns_skip_result():
    with patch.dict(os.environ, {"BRAVE_API_KEY": ""}):
        article = ArticleInput(title="Some Article")
        result = lookup(article)
        assert result.found is False
        assert result.confidence == 0.0
        assert "BRAVE_API_KEY not configured" in result.evidence
