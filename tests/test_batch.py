import json
import csv
import io
import pytest
from unittest.mock import patch, MagicMock
from models import ArticleInput, Verdict, SourceResult
from batch import parse_file, stream_check


def _make_verdict(peer_reviewed=True):
    return Verdict(
        peer_reviewed=peer_reviewed,
        confidence=0.95,
        sources=[SourceResult("doaj", True, peer_reviewed, 0.95, "test")],
    )


def test_parse_csv(tmp_path):
    csv_file = tmp_path / "articles.csv"
    csv_file.write_text("title,doi\nSome Article,10.1234/test\n")
    articles = list(parse_file(str(csv_file)))
    assert len(articles) == 1
    assert articles[0].title == "Some Article"
    assert articles[0].doi == "10.1234/test"


def test_parse_json(tmp_path):
    json_file = tmp_path / "articles.json"
    json_file.write_text(json.dumps([{"title": "Test", "doi": "10.1/x"}]))
    articles = list(parse_file(str(json_file)))
    assert len(articles) == 1
    assert articles[0].title == "Test"


def test_parse_unsupported_format_raises(tmp_path):
    bad_file = tmp_path / "articles.txt"
    bad_file.write_text("content")
    with pytest.raises(ValueError, match="Unsupported"):
        list(parse_file(str(bad_file)))


def test_stream_check_yields_results():
    articles = [ArticleInput(doi="10.1/a"), ArticleInput(doi="10.1/b")]
    mock_verdict = _make_verdict()
    with patch("batch.check", return_value=mock_verdict):
        results = list(stream_check(articles))
    assert len(results) == 2
    assert all(r[1] is mock_verdict for r in results)


def test_stream_check_continues_on_error():
    articles = [ArticleInput(doi="10.1/a"), ArticleInput(doi="10.1/b")]
    call_count = 0
    def side_effect(article):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("source error")
        return _make_verdict()
    with patch("batch.check", side_effect=side_effect):
        results = list(stream_check(articles))
    assert len(results) == 2
    assert results[0][2] is not None   # error on first
    assert results[1][2] is None       # no error on second
