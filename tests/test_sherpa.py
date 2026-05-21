import os
import requests
import responses
from unittest.mock import patch
from models import ArticleInput
from checker.sources.sherpa import lookup

BASE = "https://v2.sherpa.ac.uk/cgi/retrieve"

FOUND_RESPONSE = {
    "items": [{
        "id": 1234,
        "title": [{"title": "Some Journal", "language": "en"}],
        "issns": [{"issn": "1234-5678", "type": "print"}],
    }],
    "total_results": 1,
}

NOT_FOUND_RESPONSE = {"items": [], "total_results": 0}


@responses.activate
@patch.dict(os.environ, {"SHERPA_API_KEY": "test-key"})
def test_issn_found_returns_peer_reviewed():
    responses.add(responses.GET, BASE, json=FOUND_RESPONSE)
    result = lookup(ArticleInput(issn="1234-5678"))
    assert result.source == "sherpa"
    assert result.found is True
    assert result.peer_reviewed is True
    assert result.confidence == 0.80


@responses.activate
@patch.dict(os.environ, {"SHERPA_API_KEY": "test-key"})
def test_issn_not_found():
    responses.add(responses.GET, BASE, json=NOT_FOUND_RESPONSE)
    result = lookup(ArticleInput(issn="9999-9999"))
    assert result.found is False
    assert result.peer_reviewed is None
    assert result.confidence == 0.0


def test_no_issn_skips_lookup():
    result = lookup(ArticleInput(doi="10.1234/test"))
    assert result.found is False
    assert result.confidence == 0.0
    assert "No ISSN" in result.evidence


@patch.dict(os.environ, {"SHERPA_API_KEY": ""})
def test_missing_api_key_skips_lookup():
    result = lookup(ArticleInput(issn="1234-5678"))
    assert result.found is False
    assert result.confidence == 0.0
    assert "SHERPA_API_KEY" in result.evidence


@responses.activate
@patch.dict(os.environ, {"SHERPA_API_KEY": "test-key"})
def test_network_error_returns_safe_result():
    responses.add(responses.GET, BASE, body=requests.exceptions.ConnectionError("timeout"))
    result = lookup(ArticleInput(issn="1234-5678"))
    assert result.found is False
    assert result.confidence == 0.0
    assert "Network error" in result.evidence
