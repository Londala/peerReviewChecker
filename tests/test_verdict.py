from models import SourceResult, Verdict
from checker.verdict import aggregate


def _result(source, peer_reviewed, confidence):
    return SourceResult(
        source=source,
        found=peer_reviewed is not None,
        peer_reviewed=peer_reviewed,
        confidence=confidence,
        evidence="test",
    )


def test_returns_highest_confidence_conclusive():
    results = [
        _result("crossref", True, 0.85),
        _result("doaj", True, 0.95),
    ]
    verdict = aggregate(results)
    assert verdict.peer_reviewed is True
    assert verdict.confidence == 0.95


def test_inconclusive_when_all_below_threshold():
    results = [
        _result("crossref", None, 0.0),
        _result("websearch", True, 0.5),
    ]
    verdict = aggregate(results)
    assert verdict.peer_reviewed is None
    assert verdict.confidence == 0.5


def test_inconclusive_when_no_results():
    verdict = aggregate([])
    assert verdict.peer_reviewed is None
    assert verdict.confidence == 0.0


def test_sources_list_preserved():
    results = [_result("crossref", True, 0.85)]
    verdict = aggregate(results)
    assert len(verdict.sources) == 1
    assert verdict.sources[0].source == "crossref"


def test_not_peer_reviewed_verdict():
    results = [_result("crossref", False, 0.85)]
    verdict = aggregate(results)
    assert verdict.peer_reviewed is False
    assert verdict.confidence == 0.85
