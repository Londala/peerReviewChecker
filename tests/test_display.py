from models import SourceResult, Verdict
from checker.display import format_human, format_json
import json


def _verdict(peer_reviewed, confidence, sources=None):
    return Verdict(
        peer_reviewed=peer_reviewed,
        confidence=confidence,
        sources=sources or [],
    )


def _source(source, found, peer_reviewed, confidence, evidence):
    return SourceResult(
        source=source,
        found=found,
        peer_reviewed=peer_reviewed,
        confidence=confidence,
        evidence=evidence,
    )


def test_peer_reviewed_high_confidence():
    v = _verdict(True, 0.95)
    out = format_human(v)
    assert out.startswith("✓")
    assert "95%" in out


def test_not_peer_reviewed_high_confidence():
    v = _verdict(False, 0.70)
    out = format_human(v)
    assert out.startswith("✗")
    assert "70%" in out


def test_inconclusive_mid_confidence():
    v = _verdict(None, 0.50)
    out = format_human(v)
    assert out.startswith("?")
    assert "50%" in out


def test_likely_not_reviewed_low_confidence():
    v = _verdict(None, 0.25)
    out = format_human(v)
    assert out.startswith("~")
    assert "25%" in out


def test_article_label_prefix():
    v = _verdict(True, 0.80)
    out = format_human(v, article_label="Article 1")
    assert out.startswith("Article 1: ✓")


def test_found_sources_shown():
    src = _source("crossref", True, True, 0.75, "Journal article in 'Nature'")
    v = _verdict(True, 0.75, sources=[src])
    out = format_human(v)
    assert "[crossref]" in out
    assert "Nature" in out


def test_not_found_sources_hidden():
    src = _source("doaj", False, None, 0.0, "DOI not found in DOAJ")
    v = _verdict(None, 0.0, sources=[src])
    out = format_human(v)
    assert "[doaj]" not in out


def test_format_json_structure():
    src = _source("crossref", True, True, 0.75, "Journal article")
    v = _verdict(True, 0.75, sources=[src])
    data = json.loads(format_json(v))
    assert data["peer_reviewed"] is True
    assert data["confidence"] == 0.75
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source"] == "crossref"


def test_format_json_confidence_rounded():
    v = _verdict(True, 0.123456789)
    data = json.loads(format_json(v))
    assert data["confidence"] == 0.1235
