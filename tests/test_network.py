import pytest
from models import ArticleInput
from checker.sources.crossref import lookup as crossref_lookup
from checker.sources.doaj import lookup as doaj_lookup
from checker.pipeline import check

# 10.1038/nature12373 = "Higgs boson" paper — well-known, peer-reviewed
KNOWN_DOI = "10.1038/nature12373"
KNOWN_TITLE = "Observation of a new boson at a mass of 125 GeV"


@pytest.mark.network
def test_crossref_real_doi():
    article = ArticleInput(doi=KNOWN_DOI)
    result = crossref_lookup(article)
    assert result.found is True
    assert result.peer_reviewed is True


@pytest.mark.network
def test_pipeline_real_doi():
    article = ArticleInput(doi=KNOWN_DOI)
    verdict = check(article)
    assert verdict.peer_reviewed is True
    assert verdict.confidence >= 0.6


# 10.1007/978-3-030-01234-2_1 = Springer book chapter — confirmed not a journal article
BOOK_CHAPTER_DOI = "10.1007/978-3-030-01234-2_1"

# Fake title that should not match any real article
FAKE_TITLE = "A Fake Article That Does Not Exist"


@pytest.mark.network
def test_pipeline_book_chapter_not_peer_reviewed():
    article = ArticleInput(doi=BOOK_CHAPTER_DOI)
    verdict = check(article)
    assert verdict.peer_reviewed is False
    assert verdict.confidence >= 0.6


@pytest.mark.network
def test_pipeline_fake_title_low_confidence():
    article = ArticleInput(title=FAKE_TITLE)
    verdict = check(article)
    assert verdict.confidence < 0.4
